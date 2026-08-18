"""Opt-in mechanical-equilibrium tail risk for PIDL.

The disabled path returns the original loss tensor unchanged.  The enabled
path detaches damage and computes an interior free-node mean-excess utility.
"""
from __future__ import annotations

import math
import torch

from compute_energy import compute_energy_per_elem


def _require_finite(name, value):
    if not bool(torch.all(torch.isfinite(value))):
        raise ValueError(f"{name} must be finite")


def weighted_quantile_detached(values, weights, quantile):
    """Return a detached weighted left quantile used only as a threshold."""
    if not 0.0 < float(quantile) < 1.0:
        raise ValueError("quantile must lie strictly between zero and one")
    if values.ndim != 1 or weights.ndim != 1 or values.shape != weights.shape:
        raise ValueError("values and weights must be aligned one-dimensional tensors")
    if values.numel() == 0:
        raise ValueError("weighted quantile population must be non-empty")
    _require_finite("values", values)
    _require_finite("weights", weights)
    if not bool(torch.all(weights > 0)):
        raise ValueError("weights must be strictly positive")

    detached_values = values.detach()
    detached_weights = weights.detach()
    order = torch.argsort(detached_values, stable=True)
    sorted_values = detached_values[order]
    cumulative = torch.cumsum(detached_weights[order], dim=0)
    target = float(quantile) * torch.sum(detached_weights)
    index = torch.searchsorted(cumulative, target, right=False)
    index = torch.clamp(index, max=sorted_values.numel() - 1)
    return sorted_values[index].detach()


def weighted_mean_excess(values, weights, alpha=0.85):
    """Area-weighted mean excess above a detached weighted quantile."""
    threshold = weighted_quantile_detached(values, weights, alpha)
    denominator = (1.0 - float(alpha)) * torch.sum(weights)
    utility = torch.sum(weights * torch.relu(values - threshold)) / denominator
    return utility, threshold


def nodal_lumped_dual_area(connectivity, element_area, n_nodes):
    if connectivity.ndim != 2 or connectivity.shape[1] != 3:
        raise ValueError("mechanical residual risk requires triangle connectivity")
    _require_finite("element_area", element_area)
    if not bool(torch.all(element_area > 0)):
        raise ValueError("element areas must be strictly positive")
    dual = torch.zeros(n_nodes, dtype=element_area.dtype, device=element_area.device)
    for local in range(3):
        dual.index_add_(0, connectivity[:, local], element_area / 3.0)
    if not bool(torch.all(dual > 0)):
        raise ValueError("every node in the risk geometry must have positive dual area")
    return dual


def interior_free_node_mask(inp, domain_extrema, atol=1e-7):
    """Exclude all outer boundaries; top/bottom are Dirichlet, sides separate."""
    if inp.ndim != 2 or inp.shape[1] != 2:
        raise ValueError("inp must have shape (n_nodes, 2)")
    x, y = inp[:, 0], inp[:, 1]
    xmin, xmax = domain_extrema[0, 0], domain_extrema[0, 1]
    ymin, ymax = domain_extrema[1, 0], domain_extrema[1, 1]
    on_outer = (
        torch.isclose(x, xmin, atol=atol, rtol=0)
        | torch.isclose(x, xmax, atol=atol, rtol=0)
        | torch.isclose(y, ymin, atol=atol, rtol=0)
        | torch.isclose(y, ymax, atol=atol, rtol=0)
    )
    mask = ~on_outer
    if not bool(torch.any(mask)):
        raise ValueError("interior free-node population is empty")
    return mask


def mechanical_mean_excess_from_fields(
    inp, u, v, damage, matprop, pffmodel, element_area, connectivity,
    *, node_mask, dual_area, scale, alpha=0.85, element_mask=None,
    g_stiffness_override=None,
):
    """Build the differentiable mechanical residual risk from physical fields."""
    if connectivity is None:
        raise ValueError("mechanical residual risk requires numerical triangle gradients")
    if not math.isfinite(float(scale)) or not float(scale) > 0:
        raise ValueError("mechanical residual scale must be positive")
    if element_mask is not None:
        raise ValueError(
            "mechanical residual risk is incompatible with element_mask in G2; "
            "an active-domain dual area and internal-boundary measure are required"
        )
    if node_mask.dtype != torch.bool or node_mask.ndim != 1 or len(node_mask) != len(inp):
        raise ValueError("node_mask must be a boolean tensor aligned with inp")
    if not bool(torch.any(node_mask)):
        raise ValueError("mechanical residual risk mask must be non-empty")
    if dual_area.ndim != 1 or len(dual_area) != len(inp):
        raise ValueError("dual_area must be aligned with inp")
    _require_finite("dual_area", dual_area)
    if not bool(torch.all(dual_area > 0)):
        raise ValueError("dual_area must be strictly positive")

    damage_fixed = damage.detach()
    eel, _, _ = compute_energy_per_elem(
        inp, u, v, damage_fixed, damage_fixed,
        matprop, pffmodel, element_area, connectivity,
        f_fatigue=1.0,
        g_stiffness_override=g_stiffness_override,
    )
    mechanical_energy = torch.sum(eel)
    residual_u, residual_v = torch.autograd.grad(
        mechanical_energy, (u, v), create_graph=True, retain_graph=True,
    )
    intensive = torch.sqrt(
        (residual_u / (dual_area * float(scale))) ** 2
        + (residual_v / (dual_area * float(scale))) ** 2
        + torch.as_tensor(1e-24, dtype=u.dtype, device=u.device)
    )
    selected = intensive[node_mask]
    weights = dual_area[node_mask]
    utility, threshold = weighted_mean_excess(selected, weights, alpha=alpha)
    diagnostics = {
        "threshold": threshold,
        "risk_mean_excess": utility,
        "population_nodes": int(torch.sum(node_mask).item()),
        "scale": float(scale),
        "alpha": float(alpha),
    }
    return utility, diagnostics


def add_mechanical_residual_risk(
    base_loss, *, config, inp=None, u=None, v=None, damage=None,
    matprop=None, pffmodel=None, element_area=None, connectivity=None,
    element_mask=None, g_stiffness_override=None,
):
    """Return base_loss unchanged unless the risk intervention is enabled."""
    if config is None or not bool(config.get("enable", False)):
        return base_loss, None

    required = {
        "node_mask": config.get("node_mask"),
        "dual_area": config.get("dual_area"),
        "scale": config.get("scale"),
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise ValueError(f"mechanical residual risk missing config keys: {missing}")
    coefficient = float(config.get("lambda", 0.0))
    if not math.isfinite(coefficient) or coefficient < 0:
        raise ValueError("mechanical residual risk lambda must be non-negative")
    risk, diagnostics = mechanical_mean_excess_from_fields(
        inp, u, v, damage, matprop, pffmodel, element_area, connectivity,
        node_mask=required["node_mask"], dual_area=required["dual_area"],
        scale=required["scale"], alpha=config.get("alpha", 0.85),
        element_mask=element_mask,
        g_stiffness_override=g_stiffness_override,
    )
    return base_loss + coefficient * risk, diagnostics
