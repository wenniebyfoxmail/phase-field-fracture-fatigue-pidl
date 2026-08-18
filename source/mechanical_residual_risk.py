"""Opt-in mechanical-equilibrium tail risk for PIDL.

The disabled path returns the original loss tensor unchanged.  The enabled
path detaches damage and computes an interior free-node mean-excess utility.
"""
from __future__ import annotations

import math
import json
import os
import tempfile
import ctypes
import errno
import hashlib
import platform
import shutil
from pathlib import Path

import numpy as np
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


def mechanical_residual_fields_from_fields(
    inp, u, v, damage, matprop, pffmodel, element_area, connectivity,
    *, node_mask, dual_area, scale, element_mask=None,
    g_stiffness_override=None,
):
    """Return the true autograd mechanical residual before history refresh."""
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
    return {
        "residual_u": residual_u,
        "residual_v": residual_v,
        "intensive": intensive,
        "dual_area": dual_area,
        "node_mask": node_mask,
        "scale": float(scale),
    }


def mechanical_mean_excess_from_fields(
    inp, u, v, damage, matprop, pffmodel, element_area, connectivity,
    *, node_mask, dual_area, scale, alpha=0.85, element_mask=None,
    g_stiffness_override=None,
):
    """Build the differentiable mechanical residual risk from physical fields."""
    fields = mechanical_residual_fields_from_fields(
        inp, u, v, damage, matprop, pffmodel, element_area, connectivity,
        node_mask=node_mask, dual_area=dual_area, scale=scale,
        element_mask=element_mask,
        g_stiffness_override=g_stiffness_override,
    )
    selected = fields["intensive"][node_mask]
    weights = fields["dual_area"][node_mask]
    utility, threshold = weighted_mean_excess(selected, weights, alpha=alpha)
    diagnostics = {
        "threshold": threshold,
        "risk_mean_excess": utility,
        "population_nodes": int(torch.sum(node_mask).item()),
        "scale": float(scale),
        "alpha": float(alpha),
    }
    return utility, diagnostics


def weighted_tail_summary(values, weights):
    """Exact weighted quantiles and upper-tail means with fractional boundary mass."""
    values = np.asarray(values, dtype=np.float64).reshape(-1)
    weights = np.asarray(weights, dtype=np.float64).reshape(-1)
    if values.shape != weights.shape or values.size == 0:
        raise ValueError("tail-summary values and weights must be aligned and non-empty")
    if not np.all(np.isfinite(values)) or not np.all(np.isfinite(weights)):
        raise ValueError("tail-summary values and weights must be finite")
    if np.any(weights <= 0.0):
        raise ValueError("tail-summary weights must be positive")
    total_weight = float(weights.sum())

    def quantile(q):
        order = np.argsort(values, kind="stable")
        idx = np.searchsorted(np.cumsum(weights[order]), q * total_weight, side="left")
        return float(values[order[min(int(idx), values.size - 1)]])

    def upper_tail(fraction):
        order = np.argsort(-values, kind="stable")
        remaining = fraction * total_weight
        weighted_sum = 0.0
        selected_weight = 0.0
        selected_mass = 0.0
        total_mass = float(np.sum(values * weights))
        for idx in order:
            take = min(float(weights[idx]), remaining)
            weighted_sum += take * float(values[idx])
            selected_mass += take * float(values[idx])
            selected_weight += take
            remaining -= take
            if remaining <= max(1e-15 * total_weight, 0.0):
                break
        if selected_weight <= 0.0:
            raise ValueError("tail-summary selected no positive area")
        return {
            "mean": weighted_sum / selected_weight,
            "selected_area_fraction": selected_weight / total_weight,
            "residual_mass_fraction": selected_mass / total_mass if total_mass > 0 else 0.0,
        }

    tail95 = upper_tail(0.05)
    tail99 = upper_tail(0.01)
    return {
        "mean": float(np.average(values, weights=weights)),
        "p95": quantile(0.95),
        "p99": quantile(0.99),
        "cvar95": float(tail95["mean"]),
        "cvar99": float(tail99["mean"]),
        "worst_1pct_area_residual_mass_fraction": float(tail99["residual_mass_fraction"]),
        "worst_1pct_selected_area_fraction": float(tail99["selected_area_fraction"]),
    }


def export_mechanical_residual_fields(
    output_dir, *, raw_step, physical_cycle, substep_index, displacement,
    inp, u, v, damage, matprop, pffmodel, element_area, connectivity,
    node_mask, dual_area, scale, g_stiffness_override=None,
):
    """Write one optimizer-post, pre-history-refresh true-residual receipt."""
    fields = mechanical_residual_fields_from_fields(
        inp, u, v, damage, matprop, pffmodel, element_area, connectivity,
        node_mask=node_mask, dual_area=dual_area, scale=scale,
        g_stiffness_override=g_stiffness_override,
    )
    mask_np = fields["node_mask"].detach().cpu().numpy().astype(bool)
    intensive_np = fields["intensive"].detach().cpu().numpy()
    dual_np = fields["dual_area"].detach().cpu().numpy()
    summary = weighted_tail_summary(intensive_np[mask_np], dual_np[mask_np])
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"mechanical_residual_step_{int(raw_step):04d}"
    step_dir = output_dir / stem
    if step_dir.exists():
        raise FileExistsError(f"refusing to overwrite mechanical residual receipt: {stem}")
    temporary = Path(tempfile.mkdtemp(prefix=f".{stem}.build-", dir=output_dir))
    npz_path = temporary / "fields.npz"
    json_path = temporary / "receipt.json"
    payload = {
        "schema": "rrapinn-true-mechanical-residual-v1",
        "definition": "autograd_dEelastic_duv_per_nodal_dual_area",
        "state_timing": "optimizer_post_pre_history_refresh",
        "raw_step": int(raw_step),
        "physical_cycle": int(physical_cycle),
        "substep_index": int(substep_index),
        "displacement": float(displacement),
        "scale": float(scale),
        "npz": "fields.npz",
        "summary": summary,
    }
    try:
        with npz_path.open("xb") as handle:
            np.savez_compressed(
                handle,
                residual_u=fields["residual_u"].detach().cpu().numpy(),
                residual_v=fields["residual_v"].detach().cpu().numpy(),
                intensive=intensive_np,
                dual_area=dual_np,
                interior_free_mask=mask_np,
                coordinates=inp.detach().cpu().numpy(),
                connectivity=connectivity.detach().cpu().numpy(),
                damage=damage.detach().cpu().numpy(),
                raw_step=np.asarray(int(raw_step)),
                physical_cycle=np.asarray(int(physical_cycle)),
                substep_index=np.asarray(int(substep_index)),
                displacement=np.asarray(float(displacement)),
                scale=np.asarray(float(scale)),
            )
        payload["npz_sha256"] = hashlib.sha256(npz_path.read_bytes()).hexdigest()
        with json_path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        _publish_directory_exclusive(temporary, step_dir)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return payload


def _publish_directory_exclusive(source: Path, destination: Path) -> None:
    """Atomic no-clobber directory publication for one residual receipt pair."""
    libc = ctypes.CDLL(None, use_errno=True)
    system = platform.system()
    if system == "Darwin" and hasattr(libc, "renamex_np"):
        result = libc.renamex_np(
            os.fsencode(source), os.fsencode(destination), ctypes.c_uint(0x00000004)
        )
    elif system == "Linux" and hasattr(libc, "renameat2"):
        result = libc.renameat2(
            ctypes.c_int(-100), os.fsencode(source),
            ctypes.c_int(-100), os.fsencode(destination), ctypes.c_uint(1),
        )
    else:
        raise RuntimeError("exclusive atomic directory publication is unsupported")
    if result != 0:
        error = ctypes.get_errno()
        if error in (errno.EEXIST, errno.ENOTEMPTY):
            raise FileExistsError(f"refusing to replace existing receipt: {destination}")
        raise OSError(error, os.strerror(error), str(destination))


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
