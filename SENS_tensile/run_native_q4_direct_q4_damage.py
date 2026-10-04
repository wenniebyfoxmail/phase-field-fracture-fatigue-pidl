#!/usr/bin/env python3
"""One-step native-Q4 Picard discriminator with direct nodal damage.

Arm A removes the damage network and solves the identical Q4 physical energy
over nodal ``d in [0,1]`` with analytic-gradient L-BFGS-B.  Arm B is a
conditional, stronger nodal-irreversibility problem and requires an Arm-A
trigger receipt.  Library convergence is diagnostic only: scaled physical KKT
and the outer fixed-point contract decide convergence.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "source")]

import run_native_q4_bounded_picard as picard
import run_native_q4_one_step_matrix as base
from compute_energy import compute_energy_per_elem, strain_energy_with_split
from fatigue_history import compute_fatigue_degrad
from input_data_from_mesh import prep_input_data
from material_properties import MaterialProperties
from pff_model import PFFModel
from q4_quadrature import q4_gradient, q4_interpolate, q4_shape_data


ARM_A = "direct_q4_box_penalty"
ARM_B = "direct_q4_nodal_monotone"


class EvaluationBudgetExceeded(RuntimeError):
    pass


class PhysicalConvergenceReached(RuntimeError):
    pass


class AcceptedIterationCapReached(RuntimeError):
    pass


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("mesh-file", "checkpoint", "network", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--arm", choices=(ARM_A, ARM_B), default=ARM_A)
    p.add_argument("--arm-a-trigger-json", type=Path)
    p.add_argument("--fixed-uv-f-smoke", action="store_true")
    p.add_argument("--comparator-npz", type=Path)
    p.add_argument("--comparator-label")
    p.add_argument("--peak-displacement", type=float, default=0.11999988)
    p.add_argument("--max-outer", type=int, default=12)
    p.add_argument("--uv-chunk-updates", type=int, default=100)
    p.add_argument("--uv-max-block-updates", type=int, default=800)
    p.add_argument("--uv-max-total-updates", type=int, default=4800)
    p.add_argument("--damage-max-block-evaluations", type=int, default=800)
    p.add_argument("--damage-max-total-evaluations", type=int, default=4800)
    p.add_argument("--damage-check-iterations", type=int, default=20)
    p.add_argument("--inner-k-floor", type=float, default=1e-3)
    p.add_argument("--inner-entry-ratio", type=float, default=0.1)
    p.add_argument("--inner-required-consecutive", type=int, default=2)
    p.add_argument("--outer-k-tol", type=float, default=1e-3)
    p.add_argument("--outer-rho-uv-tol", type=float, default=1e-3)
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


def projected_kkt_map(
    damage: torch.Tensor,
    gradient: torch.Tensor,
    scale: float,
    lower: torch.Tensor | float = 0.0,
    upper: float = 1.0,
) -> torch.Tensor:
    """Return d-Pi_[lower,upper](d-grad/scale), the frozen scaled KKT map."""
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("KKT scale must be positive and finite")
    lo = torch.as_tensor(lower, dtype=damage.dtype, device=damage.device)
    if bool(torch.any(lo > upper)):
        raise ValueError("lower damage bound exceeds upper bound")
    projected = torch.maximum(torch.minimum(damage - gradient / scale,
                                            torch.as_tensor(upper, dtype=damage.dtype,
                                                            device=damage.device)), lo)
    return damage - projected


def kkt_metrics(damage, gradient, scale, lower=0.0):
    kmap = projected_kkt_map(damage, gradient, scale, lower)
    return {
        "k_inf": float(kmap.abs().max().detach().cpu()),
        "k_rms": float(torch.sqrt(torch.mean(kmap.square())).detach().cpu()),
        "gradient_rms_raw": float(torch.sqrt(torch.mean(gradient.square())).detach().cpu()),
        "gradient_max_abs_raw": float(gradient.abs().max().detach().cpu()),
    }


def weighted_relative_gap(new, old, weights, symmetric=False, floor=1e-30):
    weights = weights.to(device=new.device, dtype=new.dtype)
    numerator = torch.sqrt(torch.sum(weights * (new - old).square()))
    old_norm = torch.sqrt(torch.sum(weights * old.square()))
    if symmetric:
        new_norm = torch.sqrt(torch.sum(weights * new.square()))
        denominator = torch.maximum(new_norm, old_norm).clamp(min=floor)
    else:
        denominator = old_norm.clamp(min=floor)
    return float((numerator / denominator).detach().cpu())


def raw_physical_energy(inp, cells, area, u, v, damage, accepted, fatigue, mat, model):
    parts = compute_energy_per_elem(
        inp, u, v, damage, accepted, mat, model, area, cells,
        f_fatigue=fatigue,
        irreversibility_penalty_cfg={"enable": True, "mode": "fem_gp_q4"},
    )
    return sum(x.sum() for x in parts), tuple(x.sum() for x in parts)


def analytic_damage_gradient(inp, cells, u, v, damage, accepted, fatigue, mat, model):
    """Assemble the exact nodal derivative of the fixed-u/f native-Q4 energy."""
    shape, dshape, det = q4_shape_data(inp, cells)
    dgp = q4_interpolate(damage, cells, shape)
    d0gp = q4_interpolate(accepted, cells, shape)
    gd = q4_gradient(damage, cells, dshape)
    gu = q4_gradient(u, cells, dshape)
    gv = q4_gradient(v, cells, dshape)
    exx, eyy = gu[:, :, 0], gv[:, :, 1]
    exy = 0.5 * (gu[:, :, 1] + gv[:, :, 0])
    _, psi_positive = strain_energy_with_split(exx, eyy, exy, dgp, mat, model)
    ff = fatigue[:, None] if fatigue.ndim == 1 else fatigue
    ff = ff.expand_as(dgp)
    _, _, cw = model.damageFun(dgp)
    coeff = mat.w1 / cw

    # g'(d)=2(d-1), w'(d)=1 for the frozen AT1 model.
    elastic_local = torch.einsum(
        "eg,gn->en", det * (2.0 * (dgp - 1.0) * psi_positive), shape
    )
    fracture_local = torch.einsum("eg,gn->en", det * ff * coeff, shape)
    fracture_gradient = 2.0 * coeff * mat.l0**2 * torch.einsum(
        "eg,egxn,egx->en", det * ff, dshape, gd
    )
    healing = torch.relu(d0gp - dgp)
    history_local = torch.einsum(
        "eg,gn->en", -mat.w1 * model.irrPenalty() * det * healing, shape
    )
    local = elastic_local + fracture_local + fracture_gradient + history_local
    gradient = torch.zeros_like(damage).scatter_add(
        0, cells.reshape(-1), local.reshape(-1)
    )
    return gradient


@dataclass
class FixedDamageProblem:
    inp: torch.Tensor
    cells: torch.Tensor
    area: torch.Tensor
    u: torch.Tensor
    v: torch.Tensor
    accepted: torch.Tensor
    fatigue: torch.Tensor
    mat: Any
    model: Any
    scale: float
    lower: torch.Tensor
    max_evaluations: int

    def __post_init__(self):
        tensors = (self.inp, self.area, self.u, self.v, self.accepted, self.fatigue,
                   self.lower)
        if any(x.dtype != torch.float64 for x in tensors):
            raise TypeError("direct damage evaluator requires float64 physical tensors")
        self.evaluations = 0
        self.records: list[dict[str, Any]] = []
        self._last_x: np.ndarray | None = None
        self._last_value: float | None = None
        self._last_gradient: np.ndarray | None = None

    def value_gradient(self, x: np.ndarray):
        if self.evaluations >= self.max_evaluations:
            raise EvaluationBudgetExceeded("damage objective-gradient evaluation cap reached")
        d = torch.as_tensor(np.asarray(x), dtype=torch.float64,
                            device=self.inp.device).clone()
        total, parts = raw_physical_energy(
            self.inp, self.cells, self.area, self.u, self.v, d, self.accepted,
            self.fatigue, self.mat, self.model,
        )
        if not torch.isfinite(total) or float(total.detach().cpu()) <= 0:
            raise RuntimeError("direct damage energy is non-positive or non-finite")
        gradient = analytic_damage_gradient(
            self.inp, self.cells, self.u, self.v, d, self.accepted,
            self.fatigue, self.mat, self.model,
        )
        if not torch.isfinite(gradient).all():
            raise RuntimeError("direct damage gradient is non-finite")
        value = float(total.detach().cpu())
        grad_np = gradient.detach().cpu().numpy().astype(np.float64, copy=False)
        x_np = d.detach().cpu().numpy().astype(np.float64, copy=False)
        metrics = kkt_metrics(d.detach(), gradient.detach(), self.scale, self.lower)
        self.evaluations += 1
        row = {
            "evaluation": self.evaluations,
            "accepted": False,
            "objective": value,
            "E_el": float(parts[0].detach().cpu()),
            "E_frac": float(parts[1].detach().cpu()),
            "E_hist": float(parts[2].detach().cpu()),
            **metrics,
        }
        self.records.append(row)
        self._last_x, self._last_value, self._last_gradient = x_np.copy(), value, grad_np.copy()
        return value, grad_np

    def cached_or_evaluate(self, x):
        x = np.asarray(x, dtype=np.float64)
        if self._last_x is not None and np.array_equal(x, self._last_x):
            return self._last_value, self._last_gradient
        return self.value_gradient(x)


def audit_arm_b_feasibility(inp, cells, initial_damage, lower, history_gp_lower,
                            tolerance=1e-12):
    shape, _, _ = q4_shape_data(inp, cells)
    lower_gp = q4_interpolate(lower, cells, shape)
    initial_gap = float((lower - initial_damage).max().detach().cpu())
    gp_gap = float((history_gp_lower - lower_gp).max().detach().cpu())
    report = {
        "initial_minus_lower_min": float((initial_damage - lower).min().detach().cpu()),
        "lower_gp_minus_history_gp_min": float((lower_gp - history_gp_lower).min().detach().cpu()),
        "initial_feasible": initial_gap <= tolerance,
        "gp_lower_feasible": gp_gap <= tolerance,
    }
    if not report["initial_feasible"] or not report["gp_lower_feasible"]:
        raise RuntimeError("Arm B NO-GO: d_h0/lower or N_Q4 lower/history GP audit failed")
    return report


def validate_arm_b_trigger(path: Path | None, tol=1e-3, irr_tol=1e-6):
    if path is None:
        raise ValueError("Arm B requires --arm-a-trigger-json")
    data = json.loads(path.read_text())
    required = ("arm", "used_K0", "candidate_K0", "irreversibility_gp_max",
                "implementation_or_state_error")
    missing = [x for x in required if x not in data]
    if missing:
        raise ValueError(f"Arm A trigger receipt missing {missing}")
    allowed = (
        data["arm"] == ARM_A
        and not bool(data["implementation_or_state_error"])
        and float(data["used_K0"]) <= tol
        and float(data["candidate_K0"]) <= tol
        and float(data["irreversibility_gp_max"]) > irr_tol
    )
    if not allowed:
        raise RuntimeError("Arm B trigger is not satisfied")
    return data


def solve_damage_block(problem, initial, *, check_iterations=20, k_floor=1e-3,
                       entry_ratio=0.1, required_consecutive=2,
                       max_accepted_iterations=None):
    """Fresh-history L-BFGS-B block with strict evaluation accounting."""
    try:
        from scipy.optimize import minimize
    except ImportError as exc:  # keep static/unit paths usable without SciPy
        raise RuntimeError("SciPy with L-BFGS-B is required for a damage block") from exc

    initial = np.asarray(initial, dtype=np.float64)
    lo = problem.lower.detach().cpu().numpy().astype(np.float64, copy=False)
    initial_value, initial_gradient = problem.cached_or_evaluate(initial)
    entry = kkt_metrics(
        torch.from_numpy(initial), torch.from_numpy(initial_gradient), problem.scale,
        torch.from_numpy(lo),
    )["k_inf"]
    target = max(k_floor, entry_ratio * entry)
    accepted_iterations = 0
    consecutive = 0
    accepted_x = initial.copy()
    accepted_value = initial_value
    accepted_gradient = initial_gradient.copy()
    accepted_rows = []
    termination = "LIBRARY_EXIT_NOT_PHYSICAL_CLOSE"
    library_result = None

    def callback(intermediate):
        nonlocal accepted_iterations, consecutive, accepted_x, accepted_value, accepted_gradient
        x = np.asarray(getattr(intermediate, "x", intermediate), dtype=np.float64)
        value, gradient = problem.cached_or_evaluate(x)
        if value > accepted_value * (1.0 + 1e-10):
            raise RuntimeError("accepted L-BFGS-B objective increased")
        accepted_iterations += 1
        accepted_x, accepted_value, accepted_gradient = x.copy(), value, gradient.copy()
        for row in reversed(problem.records):
            if row["evaluation"] <= problem.evaluations:
                row["accepted"] = True
                break
        if accepted_iterations % check_iterations == 0:
            k = kkt_metrics(torch.from_numpy(x), torch.from_numpy(gradient),
                            problem.scale, torch.from_numpy(lo))["k_inf"]
            consecutive = consecutive + 1 if k <= target else 0
            accepted_rows.append({"iteration": accepted_iterations, "evaluation": problem.evaluations,
                                  "objective": value, "K_lb": k, "target": target,
                                  "consecutive": consecutive})
            if consecutive >= required_consecutive:
                raise PhysicalConvergenceReached
        if (max_accepted_iterations is not None
                and accepted_iterations >= max_accepted_iterations):
            raise AcceptedIterationCapReached

    try:
        library_result = minimize(
            problem.value_gradient,
            initial,
            method="L-BFGS-B",
            jac=True,
            bounds=list(zip(lo.tolist(), np.ones_like(lo).tolist())),
            callback=callback,
            options={
                "maxcor": 10,
                "maxls": 20,
                "ftol": 1e-12,
                "gtol": 0.0,
                "maxfun": problem.max_evaluations,
                "maxiter": max(problem.max_evaluations, 1),
            },
        )
        accepted_x = np.asarray(library_result.x, dtype=np.float64)
        accepted_value, final_gradient = problem.cached_or_evaluate(accepted_x)
    except PhysicalConvergenceReached:
        termination = "PHYSICAL_KKT_DONE"
        final_gradient = accepted_gradient
    except EvaluationBudgetExceeded:
        termination = "EVALUATION_CAP_NOT_PHYSICAL_CLOSE"
        final_gradient = accepted_gradient
    except AcceptedIterationCapReached:
        termination = "ACCEPTED_ITERATION_CAP"
        final_gradient = accepted_gradient
    final_k = kkt_metrics(torch.from_numpy(accepted_x), torch.from_numpy(final_gradient),
                          problem.scale, torch.from_numpy(lo))["k_inf"]
    if final_k <= target and termination == "LIBRARY_EXIT_NOT_PHYSICAL_CLOSE":
        # A library exit is never promoted without the two-check contract.
        termination = "LIBRARY_EXIT_KKT_SINGLE_CHECK_ONLY"
    return {
        "damage": accepted_x,
        "objective": accepted_value,
        "gradient": final_gradient,
        "entry_K_lb": entry,
        "target_K_lb": target,
        "final_K_lb": final_k,
        "accepted_iterations": accepted_iterations,
        "evaluations": problem.evaluations,
        "termination": termination,
        "library_success": None if library_result is None else bool(library_result.success),
        "library_message": None if library_result is None else str(library_result.message),
        "checks": accepted_rows,
        "evaluation_trace": problem.records,
    }


def _to64(x):
    return x.detach().to(dtype=torch.float64)


def direct_gradient(inp, cells, area, u, v, damage, accepted, fatigue, mat, model):
    dd = damage.detach().clone().requires_grad_(True)
    total, parts = raw_physical_energy(inp, cells, area, u, v, dd, accepted, fatigue,
                                       mat, model)
    (gradient,) = torch.autograd.grad(total, (dd,))
    return gradient.detach(), float(total.detach().cpu()), tuple(float(x.detach().cpu()) for x in parts)


def main():
    a = parse_args()
    torch.manual_seed(a.seed)
    np.random.seed(a.seed)
    device = torch.device(a.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    if a.out.exists():
        raise FileExistsError(a.out)
    if not a.fixed_uv_f_smoke:
        if a.comparator_npz is None or a.comparator_label is None:
            raise ValueError("production requires a pre-frozen --comparator-npz and --comparator-label")
        if not a.comparator_npz.is_file():
            raise FileNotFoundError(a.comparator_npz)
    if a.arm == ARM_B:
        trigger = validate_arm_b_trigger(a.arm_a_trigger_json, a.outer_k_tol,
                                         a.irreversibility_gp_max_tol)
    else:
        if a.arm_a_trigger_json is not None:
            raise ValueError("Arm A must not receive an Arm-B trigger receipt")
        trigger = None
    a.out.mkdir(parents=True)

    mat = MaterialProperties(1.0, 0.3, 1.0, 0.01)
    model = PFFModel("AT1", "volumetric", 5e-3, residual_stiffness=0.0)
    crack = {"x_init": [-0.5], "y_init": [0.0], "L_crack": [0.5], "angle_crack": [0.0]}
    numr = {"alpha_constraint": "nonsmooth", "gradient_type": "numerical",
            "irreversibility_penalty": {"enable": True, "mode": "fem_gp_q4"}}
    inp, cells, area, _ = prep_input_data(mat, model, crack, numr,
                                           mesh_file=str(a.mesh_file), device=device)
    if cells.ndim != 2 or cells.shape[1] != 4:
        raise ValueError("direct damage runner requires native Q4 connectivity")
    ck = torch.load(a.checkpoint, map_location=device, weights_only=False)
    if a.checkpoint.name != "checkpoint_step_412.pt" or a.network.name != "trained_1NN_412.pt":
        raise ValueError("target step413 requires exact accepted step412 checkpoint/network")
    d0_raw = ck["hist_alpha"].to(device).detach()
    d0 = d0_raw.clamp(0.0, 1.0)
    h0 = ck["hist_fat"].to(device).detach()
    driver = ck["psi_plus_prev"].to(device).detach()
    if h0.shape != (len(cells), 4):
        raise ValueError("q4_gp4 history shape contract failed")
    state = {k: v.to(device) for k, v in torch.load(
        a.network, map_location=device, weights_only=True).items()}
    cfg = base.fatigue_cfg()
    f0 = compute_fatigue_degrad(h0, cfg).detach()
    uv = base.make_field(state, device, a.peak_displacement, "bounded_nonsmooth")
    initial_field = base.make_field(state, device, a.peak_displacement, "bounded_nonsmooth")
    with torch.no_grad():
        u, v, _ = uv.fieldCalculation(inp)
        _, _, d_initial = initial_field.fieldCalculation(inp)
    if bool((d_initial < 0).any()) or bool((d_initial > 1).any()):
        raise RuntimeError("B0 direct damage is outside [0,1]")
    accepted = (d0, h0, driver, f0)
    accepted_clones = tuple(x.clone() for x in accepted)
    h_used, f_used = base.trial(inp, cells, area, u, v, d_initial, h0, driver,
                                mat, model, cfg)

    # Freeze the exact hard-comparator scales in its original float32 path.
    b0_res = picard.physical_residuals(inp, cells, area, u, v, d_initial, d0,
                                       f_used, mat, model)
    scale = max(b0_res["damage_kkt_rms_raw"], 1e-30)
    uv_scale = max(b0_res["weak_uv_free_rms_raw"], 1e-30)

    # Float64 direct problem and B0 scale; cross-dtype energy is part of the receipt.
    fixed64 = tuple(_to64(x) for x in (inp, area, u, v, d_initial, d0, f_used))
    inp64, area64, u64, v64, d64, d064, f64 = fixed64
    g64_ad, e64, _ = direct_gradient(inp64, cells, area64, u64, v64, d64, d064,
                                     f64, mat, model)
    g64 = analytic_damage_gradient(inp64, cells, u64, v64, d64, d064,
                                   f64, mat, model).detach()
    gradient_relmax = float((g64 - g64_ad).abs().max().cpu()) / max(
        float(g64_ad.abs().max().cpu()), 1e-30
    )
    if gradient_relmax > 1e-8:
        raise RuntimeError(f"analytic/AD damage gradient mismatch: {gradient_relmax}")
    e32 = float(sum(base.energies(inp, cells, area, u, v, d_initial, d0, f_used,
                                  mat, model)).detach().cpu())
    dtype_rel = abs(e64 - e32) / max(abs(e64), abs(e32), 1e-30)
    if dtype_rel > 1e-5:
        raise RuntimeError(f"B0 float32/float64 physical energy mismatch: {dtype_rel}")
    shape64, _, _ = q4_shape_data(inp64, cells)
    hgp_lower = q4_interpolate(d064, cells, shape64)
    if a.arm == ARM_A:
        lower64 = torch.zeros_like(d64)
        arm_b_audit = None
    else:
        lower64 = d064.clamp(0.0, 1.0)  # frozen d_proj^- in this aligned checkpoint
        arm_b_audit = audit_arm_b_feasibility(inp64, cells, d64, lower64, hgp_lower)

    b0 = {
        "arm": a.arm,
        "source_state": "exact step412 accepted state",
        "target_state": "step413 / FEM c83 peak / U=0.11999988",
        "initial_damage_max_abs_copy_error": 0.0,
        "float32_float64_energy_relative_difference": dtype_rel,
        "raw_energy_float32": e32,
        "raw_energy_float64": e64,
        "analytic_vs_independent_AD_gradient_relmax": gradient_relmax,
        "hard_B0_damage_scale": scale,
        "hard_B0_uv_scale": uv_scale,
        "K_lb_B0": kkt_metrics(d64, g64, scale, lower64)["k_inf"],
        "fixed_damage_dof_count": 0,
        "arm_b_trigger": trigger,
        "arm_b_feasibility": arm_b_audit,
    }
    (a.out / "b0_contract.json").write_text(json.dumps(b0, indent=2) + "\n")

    if a.fixed_uv_f_smoke:
        if a.arm != ARM_A:
            raise ValueError("fixed-UV/f smoke is the Arm-A preflight only")
        smoke_problem = FixedDamageProblem(
            inp64, cells, area64, u64, v64, d064, f64, mat, model, scale,
            lower64, min(a.damage_max_block_evaluations, 200),
        )
        smoke = solve_damage_block(
            smoke_problem, d64.detach().cpu().numpy(),
            check_iterations=a.damage_check_iterations,
            k_floor=a.inner_k_floor, entry_ratio=a.inner_entry_ratio,
            required_consecutive=a.inner_required_consecutive,
            max_accepted_iterations=50,
        )
        final_d = torch.as_tensor(smoke["damage"], dtype=torch.float64, device=device)
        bounds_ok = bool(torch.all((final_d >= 0.0) & (final_d <= 1.0)))
        energy_nonincrease = smoke["objective"] <= e64 * (1.0 + 1e-10)
        final_ad, _, _ = direct_gradient(inp64, cells, area64, u64, v64, final_d,
                                         d064, f64, mat, model)
        final_analytic = analytic_damage_gradient(
            inp64, cells, u64, v64, final_d, d064, f64, mat, model
        ).detach()
        final_gradient_relmax = float((final_analytic - final_ad).abs().max().cpu()) / max(
            float(final_ad.abs().max().cpu()), 1e-30
        )
        gradient_ok = final_gradient_relmax <= 1e-8
        abnormal_line_search = "ABNORMAL" in str(smoke["library_message"] or "").upper()
        smoke_pass = (
            smoke["accepted_iterations"] >= 1
            and energy_nonincrease
            and bounds_ok
            and gradient_ok
            and not abnormal_line_search
            and math.isfinite(smoke["objective"])
        )
        smoke_receipt = {
            "label": "FULL_MESH_FIXED_UV_F_SMOKE_PASS" if smoke_pass else
                     "FULL_MESH_FIXED_UV_F_SMOKE_FAIL",
            "accepted_iterations": smoke["accepted_iterations"],
            "evaluations": smoke["evaluations"],
            "initial_objective": e64,
            "final_objective": smoke["objective"],
            "energy_nonincrease": energy_nonincrease,
            "bounds_ok": bounds_ok,
            "analytic_vs_independent_AD_gradient_relmax": final_gradient_relmax,
            "gradient_ok": gradient_ok,
            "abnormal_line_search": abnormal_line_search,
            "entry_K0": smoke["entry_K_lb"],
            "final_K0": smoke["final_K_lb"],
            "termination": smoke["termination"],
        }
        (a.out / "smoke_result.json").write_text(
            json.dumps(smoke_receipt, indent=2) + "\n"
        )
        with (a.out / "damage_solver_trace.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(smoke["evaluation_trace"][0]))
            writer.writeheader(); writer.writerows(smoke["evaluation_trace"])
        final_export = base.export(
            inp, cells, u, v, final_d.to(inp.dtype), h_used, f_used, mat, model
        )
        np.savez_compressed(a.out / "fixed_uv_f_smoke_final.npz", **final_export)
        picard.assert_accepted(accepted, accepted_clones)
        if not smoke_pass:
            raise RuntimeError(f"fixed-UV/f smoke failed: {smoke_receipt}")
        print(json.dumps(smoke_receipt, indent=2), flush=True)
        return

    uvopt = torch.optim.Rprop(uv.parameters(), lr=1e-5, step_sizes=(1e-10, 50.0))
    d_current = d64.clone()
    rows, uv_trace, damage_trace = [], [], []
    total_uv = total_deval = consecutive = 0
    previous_history_increment = None
    merit_history = []
    final_label = "MAX_OUTER_NOT_CLOSED"
    started = time.perf_counter()

    for outer in range(1, a.max_outer + 1):
        if total_uv >= a.uv_max_total_updates or total_deval >= a.damage_max_total_evaluations:
            final_label = "FIELD_BUDGET_NOT_CLOSED"
            break
        with torch.no_grad():
            start_u, start_v, _ = uv.fieldCalculation(inp)
        start_d = d_current.clone()
        start_export = base.export(inp, cells, start_u, start_v,
                                   d_current.to(inp.dtype), h_used, f_used, mat, model)
        start_active = torch.as_tensor(start_export["psi_active_gp"], device=device)
        start_integral = float(np.sum(start_export["det_j"] * start_export["psi_active_gp"]))
        start_energy = float(sum(base.energies(
            inp, cells, area, start_u, start_v, d_current.to(inp.dtype), d0,
            f_used, mat, model)).detach().cpu())
        f_solve, h_solve = f_used.detach(), h_used.detach()
        frozen_d32 = d_current.to(dtype=inp.dtype).detach()

        def uclosure():
            cu, cv, _ = uv.fieldCalculation(inp)
            physical = sum(base.energies(inp, cells, area, cu, cv, frozen_d32,
                                         d0, f_solve, mat, model))
            if not torch.isfinite(physical) or physical <= 0:
                raise RuntimeError("UV physical energy is invalid")
            return torch.log10(physical) + 5e-6 * base.reg(uv)

        def uv_reader():
            cu, cv, _ = uv.fieldCalculation(inp)
            return cu, cv

        def uv_residual():
            cu, cv, _ = uv.fieldCalculation(inp)
            raw = picard.physical_residuals(inp, cells, area, cu, cv, frozen_d32,
                                            d0, f_solve, mat, model)
            raw["rho_uv"] = raw["weak_uv_free_rms_raw"] / uv_scale
            return raw

        uv_cap = min(a.uv_max_block_updates, a.uv_max_total_updates - total_uv)
        uv_block = picard.block_solve(
            label="uv", optimizer=uvopt, closure=uclosure, field_reader=uv_reader,
            residual_reader=uv_residual, residual_key="rho_uv",
            chunk=a.uv_chunk_updates, maximum=uv_cap, rho_floor=1e-3,
            entry_ratio=0.1, required_consecutive=2, trace=uv_trace,
        )
        total_uv += uv_block["updates"]
        with torch.no_grad():
            u, v, _ = uv.fieldCalculation(inp)

        deval_cap = min(a.damage_max_block_evaluations,
                        a.damage_max_total_evaluations - total_deval)
        problem = FixedDamageProblem(
            _to64(inp), cells, _to64(area), _to64(u), _to64(v), _to64(d0),
            _to64(f_solve), mat, model, scale, lower64, deval_cap,
        )
        dblock = solve_damage_block(
            problem, d_current.detach().cpu().numpy(),
            check_iterations=a.damage_check_iterations,
            k_floor=a.inner_k_floor, entry_ratio=a.inner_entry_ratio,
            required_consecutive=a.inner_required_consecutive,
        )
        if "ABNORMAL" in str(dblock["library_message"] or "").upper():
            raise RuntimeError(f"damage L-BFGS-B abnormal line search: {dblock['library_message']}")
        if (dblock["accepted_iterations"] == 0
                and dblock["final_K_lb"] > dblock["target_K_lb"]):
            raise RuntimeError("damage block stopped without physical progress")
        d_current = torch.as_tensor(dblock["damage"], dtype=torch.float64, device=device)
        total_deval += dblock["evaluations"]
        for item in dblock["evaluation_trace"]:
            damage_trace.append({"outer": outer, **item})

        d32 = d_current.to(dtype=inp.dtype)
        bound_tol = 64 * torch.finfo(d_current.dtype).eps
        node_lower_violation = float(torch.relu(lower64 - d_current).max().cpu())
        node_upper_violation = float(torch.relu(d_current - 1.0).max().cpu())
        if max(node_lower_violation, node_upper_violation) > bound_tol:
            raise RuntimeError("direct damage nodal bound contract failed")
        h_candidate, f_candidate = base.trial(inp, cells, area, u, v, d32, h0,
                                               driver, mat, model, cfg)
        inp_d, area_d, u_d, v_d, d0_d = (_to64(inp), _to64(area), _to64(u),
                                         _to64(v), _to64(d0))
        gu = analytic_damage_gradient(inp_d, cells, u_d, v_d, d_current, d0_d,
                                      _to64(f_solve), mat, model).detach()
        gc = analytic_damage_gradient(inp_d, cells, u_d, v_d, d_current, d0_d,
                                      _to64(f_candidate), mat, model).detach()
        candidate_total, candidate_part_tensors = raw_physical_energy(
            inp_d, cells, area_d, u_d, v_d, d_current, d0_d,
            _to64(f_candidate), mat, model,
        )
        used_total, used_part_tensors = raw_physical_energy(
            inp_d, cells, area_d, u_d, v_d, d_current, d0_d,
            _to64(f_solve), mat, model,
        )
        candidate_parts = tuple(float(x.detach().cpu()) for x in candidate_part_tensors)
        used_parts = tuple(float(x.detach().cpu()) for x in used_part_tensors)
        used_k = kkt_metrics(d_current, gu, scale, lower64)["k_inf"]
        candidate_k = kkt_metrics(d_current, gc, scale, lower64)["k_inf"]
        used_k0 = kkt_metrics(d_current, gu, scale, 0.0)["k_inf"]
        candidate_k0 = kkt_metrics(d_current, gc, scale, 0.0)["k_inf"]
        uv_raw = picard.physical_residuals(inp, cells, area, u, v, d32, d0,
                                           f_solve, mat, model)
        uv_candidate_raw = picard.physical_residuals(inp, cells, area, u, v, d32,
                                                     d0, f_candidate, mat, model)
        rho_uv = uv_raw["weak_uv_free_rms_raw"] / uv_scale
        candidate_rho_uv = uv_candidate_raw["weak_uv_free_rms_raw"] / uv_scale
        shape, _, det_j = q4_shape_data(inp, cells)
        f_rel = weighted_relative_gap(f_candidate, f_solve, det_j)
        f_abs = float((f_candidate - f_solve).abs().max().cpu())
        history_increment = h_candidate - h0
        history_rel = math.inf if previous_history_increment is None else weighted_relative_gap(
            history_increment, previous_history_increment, det_j, symmetric=True
        )
        previous_history_increment = history_increment.detach().clone()
        uv_change = max(float((u - start_u).abs().max().cpu()),
                        float((v - start_v).abs().max().cpu())) / max(abs(a.peak_displacement), 1e-30)
        d_change = float((d_current - start_d).abs().max().cpu())
        exported = base.export(inp, cells, u, v, d32, h_candidate, f_candidate,
                               mat, model)
        active = torch.as_tensor(exported["psi_active_gp"], device=device)
        active_rel = picard.symmetric_rel_change(active, start_active, 1e-30)
        active_integral = float(np.sum(exported["det_j"] * exported["psi_active_gp"]))
        active_integral_rel = abs(active_integral - start_integral) / max(
            abs(active_integral), abs(start_integral), 1e-30
        )
        used_energy = float(used_total.detach().cpu())
        same_f_energy_rel = abs(used_energy - start_energy) / max(
            abs(used_energy), abs(start_energy), 1e-30
        )
        dgp = q4_interpolate(d32, cells, shape)
        d0gp = q4_interpolate(d0, cells, shape)
        gp_lower = q4_interpolate(lower64.to(inp.dtype), cells, shape)
        gp_lower_violation = float(torch.relu(gp_lower - dgp).max().cpu())
        gp_upper_violation = float(torch.relu(dgp - 1.0).max().cpu())
        if max(gp_lower_violation, gp_upper_violation) > 1e-6:
            raise RuntimeError("direct damage Q4-GP bound contract failed")
        irr_max = float(torch.relu(d0gp - dgp).max().cpu())
        ratios = [rho_uv / a.outer_rho_uv_tol,
                  candidate_rho_uv / a.outer_rho_uv_tol,
                  used_k / a.outer_k_tol, candidate_k / a.outer_k_tol,
                  f_rel / a.outer_f_rel_tol, f_abs / a.outer_f_abs_tol,
                  uv_change / a.outer_field_max_tol, d_change / a.outer_field_max_tol,
                  active_rel / a.outer_active_rel_tol,
                  active_integral_rel / a.outer_active_integral_rel_tol,
                  same_f_energy_rel / a.outer_energy_rel_tol,
                  irr_max / a.irreversibility_gp_max_tol]
        if math.isfinite(history_rel):
            ratios.append(history_rel / a.outer_history_increment_rel_tol)
        merit = max(ratios)
        merit_history.append(merit)
        passed = merit <= 1.0 and math.isfinite(history_rel)
        consecutive = consecutive + 1 if passed else 0
        row = {
            "arm": a.arm, "outer": outer, "uv_updates": total_uv,
            "damage_evaluations": total_deval, "damage_block_termination": dblock["termination"],
            "fatigue_refreshes": outer,
            "used_rho_uv": rho_uv, "candidate_rho_uv": candidate_rho_uv,
            "used_K_lb": used_k, "candidate_K_lb": candidate_k,
            "used_K0": used_k0, "candidate_K0": candidate_k0,
            "trial_f_rel_gap": f_rel, "trial_f_abs_gap": f_abs,
            "history_increment_rel_change": history_rel,
            "uv_max_change_over_U": uv_change, "damage_max_change": d_change,
            "active_field_rel_change": active_rel,
            "active_integral": active_integral,
            "active_integral_rel_change": active_integral_rel,
            "same_f_energy_rel_change": same_f_energy_rel,
            "E_el_used": used_parts[0], "E_frac_used": used_parts[1],
            "E_hist_used": used_parts[2],
            "E_el_candidate": candidate_parts[0], "E_frac_candidate": candidate_parts[1],
            "E_hist_candidate": candidate_parts[2],
            "irreversibility_gp_max": irr_max, "max_gate_ratio": merit,
            "node_lower_violation": node_lower_violation,
            "node_upper_violation": node_upper_violation,
            "gp_lower_violation": gp_lower_violation,
            "gp_upper_violation": gp_upper_violation,
            "outer_pass": passed, "consecutive_passes": consecutive,
            "elapsed_seconds": time.perf_counter() - started,
        }
        rows.append(row)
        snapshot = dict(exported)
        snapshot.update({
            "hist_solve_gp": h_solve.cpu().numpy().astype(np.float32),
            "f_solve_gp": f_solve.cpu().numpy().astype(np.float32),
            "hist_candidate_gp": h_candidate.cpu().numpy().astype(np.float32),
            "f_candidate_gp": f_candidate.cpu().numpy().astype(np.float32),
        })
        np.savez_compressed(a.out / f"trial_{a.arm}_outer{outer:02d}.npz", **snapshot)
        (a.out / f"trial_{a.arm}_outer{outer:02d}.json").write_text(
            json.dumps(row, indent=2) + "\n")
        picard.assert_accepted(accepted, accepted_clones)
        h_used, f_used = h_candidate.detach(), f_candidate.detach()
        if consecutive >= a.required_consecutive:
            final_label = "PHYSICAL_FIXED_POINT_CLOSED"
            break
        if len(merit_history) >= a.stagnation_window:
            window = merit_history[-a.stagnation_window:]
            improvement = (window[0] - window[-1]) / max(abs(window[0]), 1e-30)
            if max(window) > 1.0 and improvement < a.stagnation_min_improvement:
                final_label = "STALLED_OR_OSCILLATORY_NOT_CLOSED"
                break

    with (a.out / "outer_summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    with (a.out / "damage_solver_trace.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(damage_trace[0]))
        writer.writeheader(); writer.writerows(damage_trace)
    final = rows[-1]
    receipt = {
        "arm": a.arm,
        "final_label": final_label,
        "used_K0": final["used_K0"],
        "candidate_K0": final["candidate_K0"],
        "irreversibility_gp_max": final["irreversibility_gp_max"],
        "implementation_or_state_error": False,
    }
    (a.out / "arm_result.json").write_text(json.dumps(receipt, indent=2) + "\n")
    manifest = {
        "schema": "hard5-native-q4-direct-damage-v1",
        "arm": a.arm,
        "operator": "native Q4 2x2 GP; q4_gp4; fem_gp_q4; eta=0; current_active",
        "damage_objective": "raw Eel+Efrac+Ehist at fixed u,f",
        "uv_objective": "log10(Eel+Efrac+Ehist)+5e-6*Ruv",
        "optimizer": "fresh scipy L-BFGS-B per damage block; maxcor=10; maxls=20; ftol=1e-12",
        "KKT": "K_lb=||d-Pi_[lb,1](d-grad(E)/s_d)||_inf; physical gates override scipy status",
        "evaluation_accounting": "all objective-gradient evaluations, including rejected line-search trials",
        "final_label": final_label,
        "inputs": {
            "mesh": str(a.mesh_file), "mesh_sha256": base.digest(a.mesh_file),
            "checkpoint": str(a.checkpoint), "checkpoint_sha256": base.digest(a.checkpoint),
            "network": str(a.network), "network_sha256": base.digest(a.network),
            "comparator": None if a.comparator_npz is None else str(a.comparator_npz),
            "comparator_sha256": None if a.comparator_npz is None else base.digest(a.comparator_npz),
            "comparator_label": a.comparator_label,
        },
    }
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"manifest": manifest, "result": receipt}, indent=2), flush=True)


if __name__ == "__main__":
    main()
