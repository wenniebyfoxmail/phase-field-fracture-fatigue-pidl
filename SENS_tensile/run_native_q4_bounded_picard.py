#!/usr/bin/env python3
"""Bounded native-Q4 step-413 Picard convergence discriminator.

This runner is intentionally separate from ``run_native_q4_one_step_matrix.py``:
the archived finite-budget matrix keeps its exact trajectory semantics, while
this experiment adds adaptive block stopping and an outer fixed-point test.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "source")]

import run_native_q4_one_step_matrix as base
from fatigue_history import compute_fatigue_degrad
from input_data_from_mesh import prep_input_data
from material_properties import MaterialProperties
from pff_model import PFFModel
from q4_quadrature import q4_interpolate, q4_shape_data


METHODS = ("alternating_picard",)


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("mesh-file", "checkpoint", "network", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--peak-displacement", type=float, default=0.11999988)
    p.add_argument("--methods", default="alternating_picard")
    p.add_argument("--max-outer", type=int, default=12)
    p.add_argument("--chunk-updates", type=int, default=100)
    p.add_argument("--max-block-updates", type=int, default=800)
    p.add_argument("--max-updates-per-field", type=int, default=4800)
    p.add_argument("--common-prefix-calls", type=int, default=4800)
    p.add_argument("--inner-rho-floor", type=float, default=1e-3)
    p.add_argument("--inner-entry-ratio", type=float, default=0.1)
    p.add_argument("--inner-required-consecutive", type=int, default=2)
    p.add_argument("--outer-rho-tol", type=float, default=1e-3)
    p.add_argument("--outer-f-rel-tol", type=float, default=1e-3)
    p.add_argument("--outer-f-abs-tol", type=float, default=1e-3)
    p.add_argument("--outer-field-max-tol", type=float, default=1e-3)
    p.add_argument("--outer-active-rel-tol", type=float, default=1e-2)
    p.add_argument("--outer-active-integral-rel-tol", type=float, default=1e-3)
    p.add_argument("--outer-energy-rel-tol", type=float, default=1e-4)
    p.add_argument("--outer-history-increment-rel-tol", type=float, default=1e-3)
    p.add_argument("--irreversibility-gp-max-tol", type=float, default=1e-6)
    p.add_argument("--required-consecutive", type=int, default=3)
    p.add_argument("--stagnation-window", type=int, default=5)
    p.add_argument("--stagnation-min-improvement", type=float, default=1e-2)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--device", default="cuda")
    return p.parse_args()


def rel_change(new, old):
    return float((torch.linalg.vector_norm(new - old) /
                  torch.linalg.vector_norm(old).clamp(min=1e-30)).detach().cpu())


def combined_change(new_fields, old_fields):
    return max(rel_change(n, o) for n, o in zip(new_fields, old_fields))


def symmetric_rel_change(new, old, floor):
    denominator = max(float(torch.linalg.vector_norm(new).detach().cpu()),
                      float(torch.linalg.vector_norm(old).detach().cpu()), floor)
    return float(torch.linalg.vector_norm(new - old).detach().cpu()) / denominator


def rms(value):
    return float(torch.sqrt(torch.mean(value.square())).detach().cpu())


def project_box_kkt_gradient(damage, gradient, tolerance):
    """Keep only feasible descent violations for the hard box 0 <= d <= 1."""
    at_lower = damage <= tolerance
    at_upper = damage >= 1.0 - tolerance
    projected = gradient.clone()
    projected[at_lower] = torch.minimum(projected[at_lower], torch.zeros_like(projected[at_lower]))
    projected[at_upper] = torch.maximum(projected[at_upper], torch.zeros_like(projected[at_upper]))
    return projected


def clamp_autograd_contract(device):
    values = torch.tensor([-2.0, -0.1, 0.0, 0.5, 1.0, 1.1, 2.0], device=device,
                          requires_grad=True)
    values.clamp(0.0, 1.0).sum().backward()
    gradients = values.grad.detach()
    if not torch.equal(gradients[[0, 1, 5, 6]], torch.zeros(4, device=device)):
        raise RuntimeError("installed clamp does not have zero derivative on strict tails")
    if float(gradients[3].cpu()) != 1.0:
        raise RuntimeError("installed clamp does not have unit derivative in the open interval")
    return {"inputs": values.detach().cpu().tolist(), "derivatives": gradients.cpu().tolist()}


def physical_residuals(inp, cells, area, u, v, d, accepted, fatigue, mat, model,
                       dead_mask=None):
    """Assemble nodal weak residuals from independent fields, bypassing clamp AD."""
    uu = u.detach().clone().requires_grad_(True)
    vv = v.detach().clone().requires_grad_(True)
    dd = d.detach().clone().requires_grad_(True)
    total = sum(base.energies(inp, cells, area, uu, vv, dd, accepted, fatigue, mat, model))
    gu, gv, gd = torch.autograd.grad(total, (uu, vv, dd))
    y = inp[:, 1]
    free = (y > y.min() + 1e-7) & (y < y.max() - 1e-7)
    bound_tol = 32 * torch.finfo(dd.dtype).eps
    feasible_gd = project_box_kkt_gradient(dd.detach(), gd.detach(), bound_tol)
    shape, _, _ = q4_shape_data(inp, cells)
    dgp = q4_interpolate(dd, cells, shape)
    d0gp = q4_interpolate(accepted, cells, shape)
    irr = torch.relu(d0gp - dgp)
    feasible_norm = float(torch.linalg.vector_norm(feasible_gd).detach().cpu())
    dead_ratio = 0.0
    if dead_mask is not None:
        dead_violation = feasible_gd * dead_mask.to(feasible_gd.dtype)
        dead_ratio = float(torch.linalg.vector_norm(dead_violation).detach().cpu()) / max(feasible_norm, 1e-30)
    return {
        "weak_uv_free_rms_raw": rms(torch.cat((gu[free], gv[free]))),
        "weak_damage_rms_raw": rms(gd),
        "damage_kkt_rms_raw": rms(feasible_gd),
        "damage_kkt_max_abs_raw": float(feasible_gd.abs().max().cpu()),
        "irreversibility_gp_rms": rms(irr),
        "irreversibility_gp_max": float(irr.max().detach().cpu()),
        "dead_zone_feasible_residual_fraction": dead_ratio,
    }


def normalized_residuals(raw, scales):
    out = dict(raw)
    out["rho_uv"] = raw["weak_uv_free_rms_raw"] / scales["uv"]
    out["rho_damage"] = raw["damage_kkt_rms_raw"] / scales["damage"]
    return out


@torch.no_grad()
def split_fields(uv, damage, inp):
    u, v, _ = uv.fieldCalculation(inp)
    _, _, d = damage.fieldCalculation(inp)
    return u, v, d


@torch.no_grad()
def legacy_projection_diagnostics(field, inp):
    """Measure the hard-clamp tail using the same network and legacy map."""
    legacy = base.make_field(field.net.state_dict(), inp.device, float(field.lmbda.item()), "legacy_nonsmooth")
    _, _, raw = legacy.fieldCalculation(inp)
    _, _, bounded = field.fieldCalculation(inp)
    clipped = (raw < 0) | (raw > 1)
    return {
        "legacy_damage_min": float(raw.min().cpu()),
        "legacy_damage_max": float(raw.max().cpu()),
        "hard_clamp_fraction": float(clipped.float().mean().cpu()),
        "hard_clamp_lower_fraction": float((raw < 0).float().mean().cpu()),
        "hard_clamp_upper_fraction": float((raw > 1).float().mean().cpu()),
        "bounded_damage_min": float(bounded.min().cpu()),
        "bounded_damage_max": float(bounded.max().cpu()),
    }


@torch.no_grad()
def legacy_dead_mask(field, inp):
    legacy = base.make_field(field.net.state_dict(), inp.device, float(field.lmbda.item()), "legacy_nonsmooth")
    _, _, raw = legacy.fieldCalculation(inp)
    return ((raw < 0) | (raw > 1)).detach()


def full_loss(uv, damage, inp, cells, area, d0, fatigue, mat, model,
              frozen_uv=None, frozen_damage=None):
    if frozen_uv is None:
        u, v, _ = uv.fieldCalculation(inp)
    else:
        u, v = frozen_uv
    if frozen_damage is None:
        _, _, d = damage.fieldCalculation(inp)
    else:
        d = frozen_damage
    parts = base.energies(inp, cells, area, u, v, d, d0, fatigue, mat, model)
    uv_reg = base.reg(uv)
    damage_reg = base.reg(damage)
    if frozen_uv is not None:
        uv_reg = uv_reg.detach()
    if frozen_damage is not None:
        damage_reg = damage_reg.detach()
    return base.strict_loss(parts, 0.5 * (uv_reg + damage_reg))


def block_solve(*, label, optimizer, closure, field_reader, residual_reader,
                residual_key, chunk, maximum, rho_floor, entry_ratio,
                required_consecutive, trace, after_chunk=None):
    """Exit on normalized physical residual only; field change remains diagnostic."""
    updates = 0
    previous = tuple(x.detach().clone() for x in field_reader())
    checks = []
    entry_residuals = residual_reader()
    entry_rho = entry_residuals[residual_key]
    target = max(rho_floor, entry_ratio * entry_rho)
    consecutive = 0
    status = "BLOCK_CAP"
    while updates < maximum:
        n = min(chunk, maximum - updates)
        base.step(optimizer, closure, n, trace)
        updates += n
        if after_chunk is not None:
            after_chunk(updates)
        current = tuple(x.detach().clone() for x in field_reader())
        change = combined_change(current, previous)
        residuals = residual_reader()
        residual = residuals[residual_key]
        checks.append({
            "updates": updates,
            "field_rel_change": change,
            "residual": residual,
            "target": target,
            "consecutive_passes": consecutive + 1 if residual <= target else 0,
        })
        previous = current
        consecutive = consecutive + 1 if residual <= target else 0
        if consecutive >= required_consecutive:
            status = "INEXACT_BLOCK_DONE" if target > rho_floor else "PHYSICAL_TOL_DONE"
            break
    return {
        "label": label,
        "updates": updates,
        "status": status,
        "entry_rho": entry_rho,
        "target_rho": target,
        "checks": checks,
    }


def assert_accepted(accepted, clones):
    labels = ("damage_lower_bound", "history", "previous_driver", "committed_f")
    for original, clone, label in zip(accepted, clones, labels):
        if not torch.equal(original, clone):
            raise RuntimeError(f"accepted state mutated: {label}")


def snapshot(*, out, method, outer, uv, damage, inp, cells, area, d0, h_used,
             f_used, h_candidate, f_candidate, mat, model, trace, row):
    u, v, d = split_fields(uv, damage, inp)
    shape, _, _ = q4_shape_data(inp, cells)
    dgp = q4_interpolate(d, cells, shape)
    if bool((d < 0).any()) or bool((d > 1).any()) or bool((dgp < 0).any()) or bool((dgp > 1).any()):
        raise RuntimeError("bounded damage-map contract violated at node or Q4 GP")
    data = base.export(inp, cells, u, v, d, h_candidate, f_candidate, mat, model)
    data.update({
        "hist_solve_gp": h_used.detach().cpu().numpy().astype(np.float32),
        "f_solve_gp": f_used.detach().cpu().numpy().astype(np.float32),
        "hist_candidate_gp": h_candidate.detach().cpu().numpy().astype(np.float32),
        "f_candidate_gp": f_candidate.detach().cpu().numpy().astype(np.float32),
        "loss_trace": np.asarray(trace, dtype=np.float64),
    })
    np.savez_compressed(out / f"trial_{method}_outer{outer:02d}.npz", **data)
    (out / f"trial_{method}_outer{outer:02d}.json").write_text(json.dumps(row, indent=2) + "\n")


def run_method(method, a, state, inp, cells, area, d0, h0, driver, f0, mat, model, cfg, out):
    if method != "alternating_picard":
        raise ValueError("this minimal experiment runs only alternating_picard")
    uv = base.make_field(state, inp.device, a.peak_displacement, "bounded_nonsmooth")
    damage = base.make_field(state, inp.device, a.peak_displacement, "bounded_nonsmooth")
    uopt = torch.optim.Rprop(uv.parameters(), lr=1e-5, step_sizes=(1e-10, 50.0))
    dopt = torch.optim.Rprop(damage.parameters(), lr=1e-5, step_sizes=(1e-10, 50.0))
    u, v, d = split_fields(uv, damage, inp)
    h_used, f_used = base.trial(inp, cells, area, u, v, d, h0, driver, mat, model, cfg)
    dead0 = legacy_dead_mask(damage, inp)
    b0_raw = physical_residuals(inp, cells, area, u, v, d, d0, f_used, mat, model, dead0)
    scales = {"uv": max(b0_raw["weak_uv_free_rms_raw"], 1e-30),
              "damage": max(b0_raw["damage_kkt_rms_raw"], 1e-30)}
    grad_contract = base.split_gradient_contract(uv, damage, inp, cells, area, d0, f_used, mat, model)
    accepted = (d0, h0, driver, f0)
    accepted_clones = tuple(x.clone() for x in accepted)
    trace, rows, merit_history = [], [], []
    total_calls = total_uv_updates = total_damage_updates = consecutive = 0
    previous_history_increment = None
    common_prefix_saved = False
    final_label = "MAX_OUTER_BUDGET_EXHAUSTED"
    base.sync(inp.device)
    started = time.perf_counter()

    for outer in range(1, a.max_outer + 1):
        if total_uv_updates >= a.max_updates_per_field or total_damage_updates >= a.max_updates_per_field:
            final_label = "FIELD_UPDATE_CAP_NOT_CLOSED"
            break
        outer_start = tuple(x.detach().clone() for x in split_fields(uv, damage, inp))
        start_export = base.export(inp, cells, *outer_start, h_used, f_used, mat, model)
        start_active = torch.as_tensor(start_export["psi_active_gp"], device=inp.device)
        start_integral = float(np.sum(start_export["det_j"] * start_export["psi_active_gp"]))
        start_energy = float(sum(base.energies(inp, cells, area, *outer_start, d0, f_used, mat, model)).detach().cpu())
        f_solve, h_solve = f_used.detach(), h_used.detach()

        def save_common_prefix(block_label, calls):
            nonlocal common_prefix_saved
            if common_prefix_saved or calls != a.common_prefix_calls:
                return
            pu, pv, pd = split_fields(uv, damage, inp)
            ph, pf = base.trial(inp, cells, area, pu, pv, pd, h0, driver, mat, model, cfg)
            pdead = legacy_dead_mask(damage, inp)
            pres_used = normalized_residuals(
                physical_residuals(inp, cells, area, pu, pv, pd, d0, f_solve,
                                   mat, model, pdead), scales)
            pres_candidate = normalized_residuals(
                physical_residuals(inp, cells, area, pu, pv, pd, d0, pf,
                                   mat, model, pdead), scales)
            pdata = base.export(inp, cells, pu, pv, pd, ph, pf, mat, model)
            pdata.update({"hist_solve_gp": h_solve.cpu().numpy().astype(np.float32),
                          "f_solve_gp": f_solve.cpu().numpy().astype(np.float32),
                          "hist_candidate_gp": ph.cpu().numpy().astype(np.float32),
                          "f_candidate_gp": pf.cpu().numpy().astype(np.float32)})
            np.savez_compressed(out / f"trial_{method}_common_prefix_C{calls}.npz", **pdata)
            prefix_row = {"method": method, "outer": outer, "block": block_label,
                          "optimizer_calls": calls,
                          "trial_f_fixed_point_rel_gap": rel_change(pf, f_solve),
                          **{f"used_{k}": value for k, value in pres_used.items()},
                          **{f"candidate_{k}": value for k, value in pres_candidate.items()}}
            (out / f"trial_{method}_common_prefix_C{calls}.json").write_text(
                json.dumps(prefix_row, indent=2) + "\n")
            common_prefix_saved = True

        def used_residual():
            cu, cv, cd = split_fields(uv, damage, inp)
            raw = physical_residuals(inp, cells, area, cu, cv, cd, d0, f_solve,
                                     mat, model, legacy_dead_mask(damage, inp))
            return normalized_residuals(raw, scales)

        with torch.no_grad():
            _, _, frozen_d = damage.fieldCalculation(inp)
            frozen_d = frozen_d.detach()
            frozen_d_before = frozen_d.clone()

        def uclosure():
            return full_loss(uv, damage, inp, cells, area, d0, f_solve, mat, model,
                             frozen_damage=frozen_d)

        def uv_reader():
            cu, cv, _ = uv.fieldCalculation(inp)
            return cu, cv

        uv_cap = min(a.max_block_updates, a.max_updates_per_field - total_uv_updates)
        uv_block = block_solve(label="uv", optimizer=uopt, closure=uclosure,
                               field_reader=uv_reader, residual_reader=used_residual,
                               residual_key="rho_uv", chunk=a.chunk_updates, maximum=uv_cap,
                               rho_floor=a.inner_rho_floor, entry_ratio=a.inner_entry_ratio,
                               required_consecutive=a.inner_required_consecutive, trace=trace,
                               after_chunk=lambda local: save_common_prefix("uv", total_calls + local))
        with torch.no_grad():
            _, _, frozen_d_after = damage.fieldCalculation(inp)
            if not torch.equal(frozen_d_before, frozen_d_after):
                raise RuntimeError("damage field changed during UV block")
            frozen_u, frozen_v, _ = uv.fieldCalculation(inp)
            frozen_u, frozen_v = frozen_u.detach(), frozen_v.detach()
            frozen_u_before, frozen_v_before = frozen_u.clone(), frozen_v.clone()

        def dclosure():
            return full_loss(uv, damage, inp, cells, area, d0, f_solve, mat, model,
                             frozen_uv=(frozen_u, frozen_v))

        def d_reader():
            _, _, cd = damage.fieldCalculation(inp)
            return (cd,)

        damage_cap = min(a.max_block_updates, a.max_updates_per_field - total_damage_updates)
        damage_block = block_solve(label="damage", optimizer=dopt, closure=dclosure,
                                   field_reader=d_reader, residual_reader=used_residual,
                                   residual_key="rho_damage", chunk=a.chunk_updates,
                                   maximum=damage_cap, rho_floor=a.inner_rho_floor,
                                   entry_ratio=a.inner_entry_ratio,
                                   required_consecutive=a.inner_required_consecutive, trace=trace,
                                   after_chunk=lambda local: save_common_prefix(
                                       "damage", total_calls + uv_block["updates"] + local))
        with torch.no_grad():
            frozen_u_after, frozen_v_after, _ = uv.fieldCalculation(inp)
            if not torch.equal(frozen_u_before, frozen_u_after) or not torch.equal(frozen_v_before, frozen_v_after):
                raise RuntimeError("UV field changed during damage block")

        uv_updates, damage_updates = uv_block["updates"], damage_block["updates"]
        total_uv_updates += uv_updates
        total_damage_updates += damage_updates
        total_calls += uv_updates + damage_updates
        u, v, d = split_fields(uv, damage, inp)
        dead = legacy_dead_mask(damage, inp)
        used_res = normalized_residuals(
            physical_residuals(inp, cells, area, u, v, d, d0, f_solve, mat, model, dead), scales)
        h_candidate, f_candidate = base.trial(inp, cells, area, u, v, d, h0, driver, mat, model, cfg)
        candidate_res = normalized_residuals(
            physical_residuals(inp, cells, area, u, v, d, d0, f_candidate, mat, model, dead), scales)
        used_parts = base.energies(inp, cells, area, u, v, d, d0, f_solve, mat, model)
        candidate_parts = base.energies(inp, cells, area, u, v, d, d0, f_candidate, mat, model)
        f_gap = rel_change(f_candidate, f_solve)
        f_abs = float((f_candidate - f_solve).abs().max().cpu())
        uv_change = max(float((u - outer_start[0]).abs().max().cpu()),
                        float((v - outer_start[1]).abs().max().cpu())) / max(abs(a.peak_displacement), 1e-30)
        d_change = float((d - outer_start[2]).abs().max().cpu())
        exported = base.export(inp, cells, u, v, d, h_candidate, f_candidate, mat, model)
        active = torch.as_tensor(exported["psi_active_gp"], device=inp.device)
        active_integral = float(np.sum(exported["det_j"] * exported["psi_active_gp"]))
        active_rel = symmetric_rel_change(active, start_active, 1e-30)
        active_integral_rel = abs(active_integral - start_integral) / max(abs(active_integral), abs(start_integral), 1e-30)
        end_energy_same_f = float(sum(used_parts).detach().cpu())
        energy_rel = abs(end_energy_same_f - start_energy) / max(abs(end_energy_same_f), abs(start_energy), 1e-30)
        history_increment = h_candidate - h0
        history_rel = (math.inf if previous_history_increment is None else
                       symmetric_rel_change(history_increment, previous_history_increment, 1e-30))
        previous_history_increment = history_increment.detach().clone()
        clamp = legacy_projection_diagnostics(damage, inp)
        assert_accepted(accepted, accepted_clones)
        base.sync(inp.device)
        elapsed = time.perf_counter() - started

        ratios = [used_res["rho_uv"] / a.outer_rho_tol,
                  used_res["rho_damage"] / a.outer_rho_tol,
                  candidate_res["rho_uv"] / a.outer_rho_tol,
                  candidate_res["rho_damage"] / a.outer_rho_tol,
                  uv_change / a.outer_field_max_tol, d_change / a.outer_field_max_tol,
                  f_gap / a.outer_f_rel_tol, f_abs / a.outer_f_abs_tol,
                  active_rel / a.outer_active_rel_tol,
                  active_integral_rel / a.outer_active_integral_rel_tol,
                  energy_rel / a.outer_energy_rel_tol,
                  used_res["irreversibility_gp_max"] / a.irreversibility_gp_max_tol,
                  candidate_res["irreversibility_gp_max"] / a.irreversibility_gp_max_tol]
        if math.isfinite(history_rel):
            ratios.append(history_rel / a.outer_history_increment_rel_tol)
        merit = max(ratios)
        merit_history.append(merit)
        converged_now = merit <= 1.0 and math.isfinite(history_rel)
        consecutive = consecutive + 1 if converged_now else 0
        fixed_label = "CONVERGED_FIXED_POINT" if consecutive >= a.required_consecutive else "NOT_CONVERGED"
        row = {
            "method": method, "outer": outer,
            "uv_updates_this_outer": uv_updates, "damage_updates_this_outer": damage_updates,
            "uv_updates_total": total_uv_updates, "damage_updates_total": total_damage_updates,
            "optimizer_calls_total": total_calls, "f_refreshes": outer,
            "uv_block_status": uv_block["status"], "damage_block_status": damage_block["status"],
            "uv_outer_max_over_U": uv_change, "damage_outer_max_change": d_change,
            "trial_f_fixed_point_rel_gap": f_gap, "trial_f_fixed_point_abs_max": f_abs,
            "history_increment_outer_rel_change": history_rel,
            "active_outer_rel_change": active_rel,
            "active_integral_outer_rel_change": active_integral_rel,
            "same_f_total_energy_outer_rel_change": energy_rel,
            "acceptance_merit_max_ratio": merit,
            "consecutive_outer_passes": consecutive, "fixed_point_label": fixed_label,
            "E_el_used": float(used_parts[0].detach().cpu()),
            "E_d_used": float(used_parts[1].detach().cpu()),
            "E_hist_used": float(used_parts[2].detach().cpu()),
            "E_el_candidate": float(candidate_parts[0].detach().cpu()),
            "E_d_candidate": float(candidate_parts[1].detach().cpu()),
            "E_hist_candidate": float(candidate_parts[2].detach().cpu()),
            "active_integral": active_integral, "gpu_wall_seconds": elapsed,
            "uv_block": uv_block, "damage_block": damage_block,
            "split_gradient_contract": grad_contract,
            **{f"used_{k}": value for k, value in used_res.items()},
            **{f"candidate_{k}": value for k, value in candidate_res.items()}, **clamp,
        }
        snapshot(out=out, method=method, outer=outer, uv=uv, damage=damage, inp=inp,
                 cells=cells, area=area, d0=d0, h_used=h_solve, f_used=f_solve,
                 h_candidate=h_candidate, f_candidate=f_candidate, mat=mat, model=model,
                 trace=trace, row=row)
        rows.append(row)
        print(f"[Picard] {method} outer={outer} label={fixed_label} "
              f"rho_uv={used_res['rho_uv']:.6e} rho_d={used_res['rho_damage']:.6e} "
              f"fgap={f_gap:.6e} dead={used_res['dead_zone_feasible_residual_fraction']:.6f}", flush=True)
        f_used, h_used = f_candidate.detach(), h_candidate.detach()
        if fixed_label == "CONVERGED_FIXED_POINT":
            final_label = fixed_label
            break
        if len(merit_history) >= a.stagnation_window:
            window = merit_history[-a.stagnation_window:]
            improvement = (window[0] - min(window)) / max(abs(window[0]), 1e-30)
            if improvement < a.stagnation_min_improvement and min(window) > 1.0:
                final_label = "STALLED_OR_OSCILLATORY_NOT_CLOSED"
                break

    return rows, final_label, scales, b0_raw


def main():
    a = parse_args()
    torch.manual_seed(a.seed)
    np.random.seed(a.seed)
    device = torch.device(a.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    if a.checkpoint.name != "checkpoint_step_412.pt" or a.network.name != "trained_1NN_412.pt":
        raise ValueError("target step 413 must start from exact accepted step-412 checkpoint and network")
    if min(a.max_outer, a.chunk_updates, a.max_block_updates, a.max_updates_per_field,
           a.common_prefix_calls,
           a.inner_required_consecutive, a.required_consecutive, a.stagnation_window) <= 0:
        raise ValueError("iteration counts must be positive")
    if (a.max_block_updates % a.chunk_updates or
            a.max_updates_per_field % a.chunk_updates or
            a.common_prefix_calls % a.chunk_updates):
        raise ValueError("block, field, and common-prefix caps must be multiples of chunk-updates")
    methods = [x.strip() for x in a.methods.split(",") if x.strip()]
    if not methods or len(set(methods)) != len(methods) or any(x not in METHODS for x in methods):
        raise ValueError(f"methods must be unique members of {METHODS}")
    a.out.mkdir(parents=True, exist_ok=False)

    mat = MaterialProperties(1.0, 0.3, 1.0, 0.01)
    model = PFFModel("AT1", "volumetric", 5e-3, residual_stiffness=0.0)
    numr = {"alpha_constraint": "nonsmooth", "gradient_type": "numerical",
            "irreversibility_penalty": {"enable": True, "mode": "fem_gp_q4"}}
    crack = {"x_init": [-0.5], "y_init": [0.0], "L_crack": [0.5], "angle_crack": [0.0]}
    inp, cells, area, _ = prep_input_data(mat, model, crack, numr,
                                           mesh_file=str(a.mesh_file), device=device)
    if cells.ndim != 2 or cells.shape[1] != 4:
        raise ValueError(f"expected native Q4 connectivity, got {tuple(cells.shape)}")
    ck = torch.load(a.checkpoint, map_location=device, weights_only=False)
    d0_raw = ck["hist_alpha"].to(device).detach()
    d0 = d0_raw.clamp(0.0, 1.0)
    h0 = ck["hist_fat"].to(device).detach()
    driver = ck["psi_plus_prev"].to(device).detach()
    if h0.shape != (len(cells), 4):
        raise ValueError(f"unexpected hist_fat shape {tuple(h0.shape)}")
    state = {k: v.to(device) for k, v in torch.load(a.network, map_location=device,
                                                     weights_only=True).items()}
    cfg = base.fatigue_cfg()
    f0 = compute_fatigue_degrad(h0, cfg).detach()

    b0_field = base.make_field(state, device, a.peak_displacement, "bounded_nonsmooth")
    b0 = legacy_projection_diagnostics(b0_field, inp)
    b0.update({
        "accepted_damage_projection_max_abs": float((d0 - d0_raw).abs().max().cpu()),
        "accepted_history_unchanged": True,
        "accepted_previous_driver_unchanged": True,
        "installed_clamp_autograd_contract": clamp_autograd_contract(device),
    })
    (a.out / "b0_contract.json").write_text(json.dumps(b0, indent=2) + "\n")

    all_rows = []
    labels = {}
    residual_scales = {}
    b0_residuals = {}
    for method in methods:
        print(f"[Picard] start {method}", flush=True)
        rows, label, scales, raw_b0 = run_method(method, a, state, inp, cells, area, d0,
                                                 h0, driver, f0, mat, model, cfg, a.out)
        all_rows.extend(rows)
        labels[method] = label
        residual_scales[method] = scales
        b0_residuals[method] = raw_b0

    b0["physical_residual_scales"] = residual_scales
    b0["physical_residuals_raw"] = b0_residuals
    (a.out / "b0_contract.json").write_text(json.dumps(b0, indent=2) + "\n")

    flat = [{k: v for k, v in row.items() if not isinstance(v, (dict, list))}
            for row in all_rows]
    with (a.out / "picard_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)
    manifest = {
        "schema": "hard5-native-q4-bounded-picard-v1",
        "source_state": "exact PIDL step-412 accepted checkpoint/network",
        "target_state": "step 413 / c83 peak displacement 0.11999988",
        "methods": methods,
        "fatigue_mode": "trial; rebuilt from frozen accepted state after each outer round",
        "damage_map": "bounded_nonsmooth = clamp(legacy central affine map, 0, 1)",
        "operator": "native Q4 2x2 GP; q4_gp4 Carrara state; fem_gp_q4 irreversibility; eta=0; current_active",
        "optimizer": "fresh torch Rprop; lr=1e-5; default etas; step_sizes=(1e-10,50); persistent within each method",
        "objective": "alternating_picard uses the prior split full loss: log10(Eel+Ed+Ehist)+1e-5*0.5*(Ruv+Rd)",
        "stopping": {
            "max_outer": a.max_outer,
            "chunk_updates": a.chunk_updates,
            "max_block_updates": a.max_block_updates,
            "max_updates_per_field": a.max_updates_per_field,
            "common_prefix_calls": a.common_prefix_calls,
            "inner_rho_floor": a.inner_rho_floor,
            "inner_entry_ratio": a.inner_entry_ratio,
            "inner_required_consecutive": a.inner_required_consecutive,
            "outer_rho_tol": a.outer_rho_tol,
            "outer_f_rel_tol": a.outer_f_rel_tol,
            "outer_f_abs_tol": a.outer_f_abs_tol,
            "outer_field_max_tol": a.outer_field_max_tol,
            "outer_active_rel_tol": a.outer_active_rel_tol,
            "outer_active_integral_rel_tol": a.outer_active_integral_rel_tol,
            "outer_energy_rel_tol": a.outer_energy_rel_tol,
            "outer_history_increment_rel_tol": a.outer_history_increment_rel_tol,
            "irreversibility_gp_max_tol": a.irreversibility_gp_max_tol,
            "required_consecutive": a.required_consecutive,
            "stagnation_window": a.stagnation_window,
            "stagnation_min_improvement": a.stagnation_min_improvement,
            "rule": "inner early exit requires normalized physical residual target at two consecutive 100-update checks; outer closure requires used/candidate UV and bounds-aware damage KKT residuals, f/history closure, max field change, active field/integral stability, same-f energy stability, GP irreversibility, and three consecutive complete rounds",
        },
        "residual_normalization": {"rule": "nonzero target-load B0 physical residual scales", "scales": residual_scales},
        "hard_clamp_diagnostic": "damage residual is assembled from independent nodal d and projected for [0,1] KKT feasibility; legacy pre-clamp dead-zone share and its feasible-residual fraction are recorded",
        "fair_control": "reuse the archived bounded alternating fixed-block trajectory at the common 4800 optimizer-call prefix; joint_shared is background only; joint_split and smooth-bounded are conditional follow-ups",
        "final_labels": labels,
        "inputs": {
            "mesh": str(a.mesh_file), "mesh_sha256": base.digest(a.mesh_file),
            "checkpoint": str(a.checkpoint), "checkpoint_sha256": base.digest(a.checkpoint),
            "network": str(a.network), "network_sha256": base.digest(a.network),
        },
    }
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
