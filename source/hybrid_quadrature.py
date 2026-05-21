"""Hybrid mesh/autograd quadrature diagnostics for sidecar S2.

This module keeps the mesh as the persistent history carrier, but lets the
training loss evaluate elastic/damage energy in a small tip patch with
mesh-free Sobol points and autograd gradients.  It is deliberately optional:
when disabled, the historical mesh-only Deep Ritz loss is unchanged.
"""

import math

import torch

from compute_energy import compute_energy_per_elem


def prepare_hybrid_patch(hybrid_quad, inp, area_elem):
    """Create deterministic patch points for one training cycle."""
    if hybrid_quad is None or not hybrid_quad.get("enable", False):
        return None

    radius = float(hybrid_quad.get("radius", 0.03))
    n_points = int(hybrid_quad.get("n_points", 512))
    if radius <= 0.0 or n_points <= 0:
        raise ValueError("hybrid_quad requires radius > 0 and n_points > 0")

    tip_x, tip_y = hybrid_quad.get("tip_xy", (0.0, 0.0))
    seed = int(hybrid_quad.get("seed", 0))

    engine = torch.quasirandom.SobolEngine(dimension=2, scramble=True, seed=seed)
    uv = engine.draw(n_points).to(device=inp.device, dtype=inp.dtype)
    # Uniform disk sampling: r = R sqrt(u), theta = 2*pi*v.
    rr = radius * torch.sqrt(uv[:, 0].clamp(min=1e-12))
    th = (2.0 * math.pi) * uv[:, 1]
    pts = torch.stack(
        [
            torch.as_tensor(float(tip_x), device=inp.device, dtype=inp.dtype) + rr * torch.cos(th),
            torch.as_tensor(float(tip_y), device=inp.device, dtype=inp.dtype) + rr * torch.sin(th),
        ],
        dim=1,
    )

    # Approximate disk clipped by the current mesh bounding box by zeroing points
    # outside the domain while keeping the full-disk Monte Carlo weight.
    x_min, x_max = inp[:, 0].min(), inp[:, 0].max()
    y_min, y_max = inp[:, 1].min(), inp[:, 1].max()
    in_domain = (
        (pts[:, 0] >= x_min) & (pts[:, 0] <= x_max) &
        (pts[:, 1] >= y_min) & (pts[:, 1] <= y_max)
    )
    if not bool(in_domain.any()):
        raise ValueError(
            "hybrid_quad patch has no points inside the current mesh bounding box"
        )

    return {
        "enable": True,
        "tip_xy": (float(tip_x), float(tip_y)),
        "radius": radius,
        "points": pts.detach(),
        "in_domain": in_domain.detach(),
        "point_weight": torch.as_tensor(
            math.pi * radius * radius / float(n_points),
            device=area_elem.device,
            dtype=area_elem.dtype,
        ),
        "replace_mesh_patch": bool(hybrid_quad.get("replace_mesh_patch", True)),
        "include_elastic": bool(hybrid_quad.get("include_elastic", True)),
        "include_damage": bool(hybrid_quad.get("include_damage", True)),
        "hist_mode": str(hybrid_quad.get("hist_mode", "mesh")),
    }


def compute_hybrid_patch_energy(field_comp, inp, hist_alpha, matprop, pffmodel,
                                area_elem, T_conn, prepared_patch,
                                f_fatigue=1.0, crack_tip_weights=None):
    """Return E_el/E_d/E_hist with optional tip patch autograd quadrature."""
    if prepared_patch is None or T_conn is None:
        u, v, alpha = field_comp.fieldCalculation(inp)
        from compute_energy import compute_energy
        return compute_energy(
            inp, u, v, alpha, hist_alpha, matprop, pffmodel, area_elem, T_conn,
            f_fatigue=f_fatigue, crack_tip_weights=crack_tip_weights,
        )

    u, v, alpha = field_comp.fieldCalculation(inp)
    E_el, E_d, E_hist = compute_energy_per_elem(
        inp, u, v, alpha, hist_alpha, matprop, pffmodel, area_elem, T_conn,
        f_fatigue=f_fatigue,
    )

    cx = (inp[T_conn[:, 0], 0] + inp[T_conn[:, 1], 0] + inp[T_conn[:, 2], 0]) / 3.0
    cy = (inp[T_conn[:, 0], 1] + inp[T_conn[:, 1], 1] + inp[T_conn[:, 2], 1]) / 3.0
    tip_x, tip_y = prepared_patch["tip_xy"]
    in_patch = torch.sqrt((cx - tip_x) ** 2 + (cy - tip_y) ** 2 + 1e-12) < prepared_patch["radius"]

    if prepared_patch["replace_mesh_patch"]:
        mesh_energy_mask = ~in_patch
    else:
        mesh_energy_mask = torch.ones_like(in_patch, dtype=torch.bool)

    if crack_tip_weights is not None:
        E_el_sum = torch.sum(crack_tip_weights[mesh_energy_mask] * E_el[mesh_energy_mask])
        E_d_sum = torch.sum(crack_tip_weights[mesh_energy_mask] * E_d[mesh_energy_mask])
        # Keep irreversibility on the full mesh history carrier.
        E_hist_sum = torch.sum(crack_tip_weights * E_hist)
    else:
        E_el_sum = torch.sum(E_el[mesh_energy_mask])
        E_d_sum = torch.sum(E_d[mesh_energy_mask])
        E_hist_sum = torch.sum(E_hist)

    pts = prepared_patch["points"][prepared_patch["in_domain"]].detach().clone()
    pts.requires_grad_(True)
    u_p, v_p, alpha_p = field_comp.fieldCalculation(pts)

    if torch.is_tensor(f_fatigue):
        if bool(in_patch.any()):
            f_patch = f_fatigue[in_patch].detach().mean()
        else:
            f_patch = torch.ones((), device=area_elem.device, dtype=area_elem.dtype)
    else:
        f_patch = f_fatigue

    patch_area = torch.full(
        (pts.shape[0],), float(prepared_patch["point_weight"].item()),
        device=area_elem.device, dtype=area_elem.dtype,
    )
    # First diagnostic version: alpha irreversibility remains mesh-carried.
    hist_alpha_patch = alpha_p.detach()
    E_el_p, E_d_p, _ = compute_energy_per_elem(
        pts, u_p, v_p, alpha_p, hist_alpha_patch, matprop, pffmodel,
        patch_area, T_conn=None, f_fatigue=f_patch,
    )

    if prepared_patch["include_elastic"]:
        E_el_sum = E_el_sum + torch.sum(E_el_p)
    if prepared_patch["include_damage"]:
        E_d_sum = E_d_sum + torch.sum(E_d_p)

    return E_el_sum, E_d_sum, E_hist_sum
