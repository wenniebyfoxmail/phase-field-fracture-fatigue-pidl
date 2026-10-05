#!/usr/bin/env python3
"""Fully non-neural native-Q4 staggered equation-closure discriminator.

The runner is fail-closed behind the lineage-qualified S04-E003 A1 admission
receipt.  It solves mechanics by sparse AMOR equilibrium and fixed-``u,f`` AT1
damage by a constrained sparse QP.  Trial fatigue is an outer Picard state
rebuilt from one immutable accepted state and committed once only after the
complete load-step equation-closure gate passes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "source")]

from damage_conditioned_equilibrium import (
    sens_displacement_boundary_conditions,
    solve_amor_equilibrium,
)
from input_data_from_mesh import prep_input_data
from material_properties import MaterialProperties
from native_q4_damage_qp import (
    assemble_at1_damage_qp,
    build_native_q4_kinematics,
    gauss_interpolation_matrix,
    osqp_certificate,
    solve_with_osqp,
    validate_a1_admission_receipt,
    validate_qp_contract,
)
from pff_model import PFFModel


SCHEMA = "s04-e004-direct-native-q4-reference-v1"
FROZEN = {
    "displacements": [0.08999988, 0.11999988],
    "equation_closure_tolerance": 1.0e-3,
    "required_consecutive": 2,
    "max_outer": 50,
    "mechanics_residual_tolerance": 1.0e-10,
    "mechanics_update_tolerance": 1.0e-11,
    "osqp_eps_abs": 1.0e-8,
    "osqp_eps_rel": 1.0e-8,
    "osqp_max_iter": 200_000,
    "mat_E": 1.0,
    "mat_nu": 0.3,
    "w1": 1.0,
    "l0": 0.01,
    "c_w": 8.0 / 3.0,
    "residual_stiffness": 0.0,
    "alpha_T": 0.5,
    "gp_order": "(+,+),(-,+),(+,-),(-,-)",
}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh-file", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--a1-receipt", type=Path, required=True)
    parser.add_argument("--a1-receipt-sha256", required=True)
    parser.add_argument("--native-capture-sha256", required=True)
    parser.add_argument("--mesh-signature", required=True)
    parser.add_argument("--branch", choices=("committed", "trial"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    return parser.parse_args()


def runtime_mesh_signature(inp: torch.Tensor, connectivity: torch.Tensor) -> str:
    """Match the checkpoint's exact coordinate/connectivity identity hash."""
    value = hashlib.sha256()
    for tensor in (inp, connectivity):
        array = tensor.detach().cpu().contiguous().numpy()
        value.update(str(array.dtype).encode("ascii"))
        value.update(np.asarray(array.shape, dtype=np.int64).tobytes())
        value.update(array.tobytes())
    return value.hexdigest()


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _finite(value, label):
    array = np.asarray(value)
    if not np.all(np.isfinite(array)):
        raise RuntimeError(f"non-finite {label}")
    return array


def fatigue_degradation(history: np.ndarray, alpha_t: float = 0.5) -> np.ndarray:
    history = _finite(history, "fatigue history").astype(np.float64, copy=False)
    if np.any(history < 0.0):
        raise ValueError("fatigue history must be non-negative")
    result = np.ones_like(history)
    mask = history > alpha_t
    result[mask] = (2.0 * alpha_t / (history[mask] + alpha_t)) ** 2
    return result


def rebuild_trial_history(
    accepted_history: np.ndarray,
    accepted_driver: np.ndarray,
    current_active: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Rebuild, never accumulate, a Carrara trial from accepted state."""
    h0 = _finite(accepted_history, "accepted history").astype(np.float64, copy=False)
    driver0 = _finite(accepted_driver, "accepted driver").astype(np.float64, copy=False)
    active = _finite(current_active, "current active driver").astype(np.float64, copy=False)
    if h0.shape != driver0.shape or h0.shape != active.shape:
        raise ValueError("trial history arrays must share the Q4 GP shape")
    trial = h0 + np.maximum(active - driver0, 0.0)
    return trial, fatigue_degradation(trial, FROZEN["alpha_T"])


def relative_inf(new: np.ndarray, old: np.ndarray, scale: float = 1.0) -> float:
    new = np.asarray(new, dtype=np.float64)
    old = np.asarray(old, dtype=np.float64)
    denominator = max(float(scale), float(np.max(np.abs(new))), float(np.max(np.abs(old))), 1.0e-30)
    return float(np.max(np.abs(new - old)) / denominator)


def solve_load_step(*, kinematics, accepted_damage, accepted_history,
                    accepted_driver, displacement, branch):
    gp_matrix = gauss_interpolation_matrix(kinematics)
    previous_gp = np.asarray(gp_matrix @ accepted_damage).reshape(len(kinematics.cells), 4)
    committed_f = fatigue_degradation(accepted_history, FROZEN["alpha_T"])
    current_damage = np.asarray(accepted_damage, dtype=np.float64).copy()
    previous_u = previous_d = previous_trial_h = previous_trial_f = None
    rows = []
    consecutive = 0
    final = None

    prescribed_dofs, prescribed_values = sens_displacement_boundary_conditions(
        kinematics.points, displacement
    )
    for outer in range(1, FROZEN["max_outer"] + 1):
        equilibrium = solve_amor_equilibrium(
            kinematics,
            current_damage,
            prescribed_dofs,
            prescribed_values,
            youngs_modulus=FROZEN["mat_E"],
            poisson_ratio=FROZEN["mat_nu"],
            residual_stiffness=FROZEN["residual_stiffness"],
            max_iterations=50,
            tolerance=FROZEN["mechanics_update_tolerance"],
            residual_tolerance=FROZEN["mechanics_residual_tolerance"],
        )
        current_u = equilibrium.displacement
        damage_gp_before = np.asarray(gp_matrix @ current_damage).reshape(previous_gp.shape)
        active_before = (
            (1.0 - damage_gp_before) ** 2 + FROZEN["residual_stiffness"]
        ) * equilibrium.tensile_energy_gauss
        trial_h_before, trial_f_before = rebuild_trial_history(
            accepted_history, accepted_driver, active_before
        )
        f_solve = committed_f if branch == "committed" else trial_f_before

        problem = assemble_at1_damage_qp(
            kinematics,
            equilibrium.tensile_energy_gauss,
            f_solve,
            previous_gp,
            w1=FROZEN["w1"],
            length_scale=FROZEN["l0"],
            c_w=FROZEN["c_w"],
        )
        qp_contract = validate_qp_contract(problem, accepted_damage)
        new_damage, dual, osqp_info = solve_with_osqp(
            problem,
            current_damage,
            eps_abs=FROZEN["osqp_eps_abs"],
            eps_rel=FROZEN["osqp_eps_rel"],
            max_iter=FROZEN["osqp_max_iter"],
        )
        certificate = osqp_certificate(problem, new_damage, dual)
        if "solved" not in osqp_info["status"].lower():
            raise RuntimeError(f"OSQP did not solve the damage QP: {osqp_info}")

        final_equilibrium = solve_amor_equilibrium(
            kinematics,
            new_damage,
            prescribed_dofs,
            prescribed_values,
            youngs_modulus=FROZEN["mat_E"],
            poisson_ratio=FROZEN["mat_nu"],
            residual_stiffness=FROZEN["residual_stiffness"],
            max_iterations=50,
            tolerance=FROZEN["mechanics_update_tolerance"],
            residual_tolerance=FROZEN["mechanics_residual_tolerance"],
        )
        new_u = final_equilibrium.displacement
        new_damage_gp = np.asarray(gp_matrix @ new_damage).reshape(previous_gp.shape)
        new_active = (
            (1.0 - new_damage_gp) ** 2 + FROZEN["residual_stiffness"]
        ) * final_equilibrium.tensile_energy_gauss
        trial_h, trial_f = rebuild_trial_history(
            accepted_history, accepted_driver, new_active
        )

        if previous_u is None:
            rho_field = math.inf
            rho_fatigue = math.inf
        else:
            rho_field = max(
                relative_inf(new_u, previous_u, max(abs(displacement), 1.0e-12)),
                relative_inf(new_damage, previous_d, 1.0),
            )
            rho_fatigue = max(
                relative_inf(trial_h, previous_trial_h, 1.0),
                relative_inf(trial_f, previous_trial_f, 1.0),
            )
        rho_u = final_equilibrium.normalized_residual
        rho_d = certificate.rho_damage
        gate = max(rho_u, rho_d, rho_field, rho_fatigue)
        passed = math.isfinite(gate) and gate <= FROZEN["equation_closure_tolerance"]
        consecutive = consecutive + 1 if passed else 0
        row = {
            "displacement": displacement,
            "branch": branch,
            "outer": outer,
            "rho_u": rho_u,
            "rho_d": rho_d,
            "rho_field_fixed_point": rho_field,
            "rho_fatigue_fixed_point": rho_fatigue,
            "equation_closure": gate,
            "pass_1e-3": passed,
            "pass_1e-4": math.isfinite(gate) and gate <= 1.0e-4,
            "pass_1e-5": math.isfinite(gate) and gate <= 1.0e-5,
            "consecutive": consecutive,
            "qp_status": osqp_info["status"],
            "qp_iterations": osqp_info["iterations"],
            "qp_stationarity_scaled": certificate.stationarity_scaled,
            "qp_primal_inf": certificate.primal_inf,
            "qp_dual_sign_inf": certificate.dual_sign_inf,
            "qp_complementarity_inf": certificate.complementarity_inf,
            "mechanics_active_set_stable": final_equilibrium.active_set_stable,
            "mechanics_iterations": final_equilibrium.iterations,
            "minimum_local_qp_eigenvalue": qp_contract["minimum_local_eigenvalue"],
            "gp_irreversibility_min_margin": float(np.min(new_damage_gp - previous_gp)),
            "damage_min": float(np.min(new_damage)),
            "damage_max": float(np.max(new_damage)),
        }
        rows.append(row)
        final = {
            "damage": new_damage,
            "displacement_vector": new_u,
            "history": trial_h,
            "fatigue": trial_f,
            "active_driver": new_active,
            "tensile_energy": final_equilibrium.tensile_energy_gauss,
            "damage_gp": new_damage_gp,
            "certificate": certificate,
            "qp_info": osqp_info,
            "qp_contract": qp_contract,
        }
        previous_u, previous_d = new_u.copy(), new_damage.copy()
        previous_trial_h, previous_trial_f = trial_h.copy(), trial_f.copy()
        current_damage = new_damage
        if consecutive >= FROZEN["required_consecutive"]:
            return final, rows, True
    return final, rows, False


def run_solver_qualification() -> dict:
    """Exercise mechanics, constrained QP, fixed point and commit gate on 4 Q4s."""
    axis = np.array([0.0, 0.5, 1.0])
    points = np.array([(x, y) for y in axis for x in axis], dtype=np.float64)
    cells = np.array([
        [0, 1, 4, 3], [1, 2, 5, 4],
        [3, 4, 7, 6], [4, 5, 8, 7],
    ], dtype=np.int32)
    kinematics = build_native_q4_kinematics(points, cells)
    accepted_damage = np.zeros(len(points), dtype=np.float64)
    accepted_history = np.zeros((len(cells), 4), dtype=np.float64)
    accepted_driver = np.zeros_like(accepted_history)
    result, rows, closed = solve_load_step(
        kinematics=kinematics,
        accepted_damage=accepted_damage,
        accepted_history=accepted_history,
        accepted_driver=accepted_driver,
        displacement=1.0e-3,
        branch="trial",
    )
    if result is None or not closed:
        raise RuntimeError("synthetic direct-Q4 solver qualification did not close")
    return {
        "label": "DIRECT_Q4_SOLVER_QUALIFIED",
        "mesh": "synthetic regular 2x2 Q4 patch",
        "branch": "trial",
        "closed": True,
        "outer_iterations": len(rows),
        "final_equation_closure": rows[-1]["equation_closure"],
        "qp_certificate": result["certificate"].__dict__,
        "accepted_state_commit_count": 0,
        "scientific_claim": False,
    }


def main():
    args = parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    if args.checkpoint.name != "checkpoint_step_412.pt":
        raise ValueError("true-path direct reference requires checkpoint_step_412.pt")
    if args.device != "cpu":
        raise ValueError("direct sparse reference is frozen to CPU float64")
    admission = validate_a1_admission_receipt(
        args.a1_receipt,
        args.a1_receipt_sha256,
        native_capture_sha256=args.native_capture_sha256,
        mesh_signature=args.mesh_signature,
    )

    device = torch.device("cpu")
    mat = MaterialProperties(FROZEN["mat_E"], FROZEN["mat_nu"],
                             FROZEN["w1"], FROZEN["l0"])
    model = PFFModel("AT1", "volumetric", tol_ir=0.005,
                     residual_stiffness=FROZEN["residual_stiffness"])
    inp, cells, _, _ = prep_input_data(
        mat, model,
        {"x_init": [-0.5], "y_init": [0.0], "L_crack": [0.5],
         "angle_crack": [0.0]},
        {"alpha_constraint": "nonsmooth", "gradient_type": "numerical",
         "irreversibility_penalty": {"enable": True, "mode": "fem_gp_q4"}},
        mesh_file=str(args.mesh_file),
        device=device,
    )
    if cells.ndim != 2 or cells.shape[1] != 4:
        raise ValueError(f"expected native Q4 connectivity, got {tuple(cells.shape)}")
    actual_mesh_signature = runtime_mesh_signature(inp, cells)
    if actual_mesh_signature != args.mesh_signature:
        raise RuntimeError(
            f"runtime mesh signature mismatch: {actual_mesh_signature} != {args.mesh_signature}"
        )
    points = inp.detach().cpu().numpy().astype(np.float64)
    cell_array = cells.detach().cpu().numpy().astype(np.int32)
    kinematics = build_native_q4_kinematics(points, cell_array)

    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    required_checkpoint = {
        "mesh_state_signature": args.mesh_signature,
        "mesh_connectivity_arity": 4,
        "history_storage": "q4_gp4",
        "damage_history_storage": "previous_accepted_nodal",
        "gauss_order": FROZEN["gp_order"],
        "history_driver_mode": "current_active",
    }
    mismatches = {
        key: {"expected": value, "actual": checkpoint.get(key)}
        for key, value in required_checkpoint.items() if checkpoint.get(key) != value
    }
    if mismatches:
        raise RuntimeError(f"checkpoint contract mismatch: {mismatches}")
    accepted_damage_raw = checkpoint["hist_alpha"].detach().cpu().numpy().astype(np.float64)
    accepted_damage = np.clip(accepted_damage_raw, 0.0, 1.0)
    accepted_projection = {
        "rule": "clip checkpoint step412 accepted nodal damage to [0,1] once",
        "raw_min": float(np.min(accepted_damage_raw)),
        "raw_max": float(np.max(accepted_damage_raw)),
        "negative_fraction": float(np.mean(accepted_damage_raw < 0.0)),
        "above_one_fraction": float(np.mean(accepted_damage_raw > 1.0)),
        "projection_max_abs": float(np.max(np.abs(accepted_damage - accepted_damage_raw))),
        "history_and_previous_driver_unchanged": True,
    }
    accepted_history = checkpoint["hist_fat"].detach().cpu().numpy().astype(np.float64)
    accepted_driver = checkpoint["psi_plus_prev"].detach().cpu().numpy().astype(np.float64)
    if accepted_history.shape != (len(cell_array), 4) or accepted_driver.shape != accepted_history.shape:
        raise RuntimeError("checkpoint Q4 GP history shape contract failed")

    args.out.mkdir(parents=True)
    qualification = run_solver_qualification()
    (args.out / "solver_qualification.json").write_text(
        json.dumps(qualification, indent=2, allow_nan=False) + "\n"
    )
    provenance = {
        "schema": SCHEMA,
        "branch": args.branch,
        "mesh": str(args.mesh_file),
        "mesh_sha256": digest(args.mesh_file),
        "checkpoint": str(args.checkpoint),
        "checkpoint_sha256": digest(args.checkpoint),
        "a1_admission": admission,
        "frozen_contract": FROZEN,
        "runtime_mesh_signature": actual_mesh_signature,
        "accepted_damage_projection": accepted_projection,
        "accepted_state_mutation_before_gate": False,
        "solver_qualification": qualification,
    }
    (args.out / "run_contract.json").write_text(json.dumps(provenance, indent=2,
                                                             allow_nan=False) + "\n")

    all_rows = []
    snapshots = {}
    accepted_states = {
        "step_412_damage_node": accepted_damage.copy(),
        "step_412_hist_fat_gp": accepted_history.copy(),
        "step_412_driver_gp": accepted_driver.copy(),
    }
    closed_all = True
    for step, displacement in zip((413, 414), FROZEN["displacements"]):
        result, rows, closed = solve_load_step(
            kinematics=kinematics,
            accepted_damage=accepted_damage,
            accepted_history=accepted_history,
            accepted_driver=accepted_driver,
            displacement=displacement,
            branch=args.branch,
        )
        for row in rows:
            row["step"] = step
        all_rows.extend(rows)
        if result is None:
            raise RuntimeError("direct reference returned no candidate state")
        np.savez_compressed(
            args.out / f"candidate_step_{step}.npz",
            damage_node=result["damage"],
            displacement_vector=result["displacement_vector"],
            damage_gp=result["damage_gp"],
            hist_fat_gp=result["history"],
            f_fatigue_gp=result["fatigue"],
            psi_raw_gp=result["tensile_energy"],
            psi_active_gp=result["active_driver"],
            closed=np.array(closed),
        )
        snapshots[str(step)] = {
            "closed": closed,
            "outer_iterations": len(rows),
            "final_gate": rows[-1]["equation_closure"],
            "qp_info": result["qp_info"],
            "qp_contract": result["qp_contract"],
            "qp_certificate": result["certificate"].__dict__,
        }
        if not closed:
            closed_all = False
            break
        # Atomic accepted-state commit after the complete load-step gate only.
        accepted_damage = result["damage"].copy()
        accepted_history = result["history"].copy()
        accepted_driver = result["active_driver"].copy()
        accepted_states[f"step_{step}_damage_node"] = accepted_damage.copy()
        accepted_states[f"step_{step}_hist_fat_gp"] = accepted_history.copy()
        accepted_states[f"step_{step}_driver_gp"] = accepted_driver.copy()

    with (args.out / "equation_closure.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)
    decision = {
        "schema": SCHEMA,
        "label": "TRUE_PATH_EQUATION_CLOSED" if closed_all else "TRUE_PATH_NOT_CLOSED",
        "branch": args.branch,
        "closed_all_steps": closed_all,
        "steps": snapshots,
        "history_commit_rule": "once after complete per-step equation closure",
        "fem_proximity_used_for_stopping_or_selection": False,
        "allows_120_cycle": False,
    }
    (args.out / "decision.json").write_text(json.dumps(decision, indent=2,
                                                        allow_nan=False) + "\n")
    final_certificate = {
        "schema": SCHEMA,
        "branch": args.branch,
        "closed_all_steps": closed_all,
        "steps": {
            step: {
                "closed": value["closed"],
                "qp_contract": value["qp_contract"],
                "qp_certificate": value["qp_certificate"],
                "qp_info": value["qp_info"],
            }
            for step, value in snapshots.items()
        },
    }
    (args.out / "qp_certificate.json").write_text(
        json.dumps(final_certificate, indent=2, allow_nan=False) + "\n"
    )
    if closed_all:
        np.savez_compressed(args.out / "accepted_states.npz", **accepted_states)
    print(json.dumps(decision, indent=2, allow_nan=False), flush=True)
    if not closed_all:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
