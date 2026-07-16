#!/usr/bin/env python3
"""Infer a c86 visible-profile update on the known c84 damage history.

The c86 VTK is opened before locking only to seal its notch-connected binary
core.  Its diffuse damage, the operator dataset targets, and the frozen model
are not reopened until the observation, reaction objective, postpeak table,
candidate fields, and lock record have all been written and hashed.
"""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import sys
import time

import meshio
import numpy as np


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from damage_conditioned_equilibrium import (  # noqa: E402
    EquilibriumResult,
    Q4Kinematics,
    build_q4_kinematics,
    equilibrium_internal_force,
    sens_displacement_boundary_conditions,
    solve_amor_equilibrium,
)
from damage_observation_reconstruction import (  # noqa: E402
    at1_from_raster_skeleton,
    notch_connected_core,
)
from damage_state_inversion import (  # noqa: E402
    feasible_reaction_brackets,
    log_midpoint,
    merge_irreversible_damage,
    parse_load_displacement_cycles,
    relative_reaction_error,
)
from run_damage_conditioned_equilibrium_gate import (  # noqa: E402
    metric_row,
    rollout,
    sha256,
    write_rows,
)
from run_damage_observation_equilibrium_gate import (  # noqa: E402
    build_observation_assimilated_state,
)
from run_fem_mechanism_assimilation_gate import checkpoint_model  # noqa: E402
from train_fem_mechanism_mesh_operator import (  # noqa: E402
    area_weighted_quantile,
    choose_device,
    derived_active_log10,
    load_dataset,
)


PRIOR_CYCLE = 84
OBSERVATION_CYCLE = 86
PROJECTED_CYCLE = 87
TEST_CYCLE = 89
CORE_THRESHOLD = 0.95
DAMAGE_INPUT_TOLERANCE = 1.0e-4
VERTICAL_CONTROL_SHIFT = 0.05
STEPS_PER_CYCLE = 8
PEAK_STEP = 4
POSTPEAK_STEPS = (5, 6, 7)
FIXED_BETA_GRID = np.asarray(
    [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0],
    dtype=np.float64,
)
REACTION_RELATIVE_TOLERANCE = 0.02
MAXIMUM_FINAL_BRACKET_FACTOR = 1.25
LOCKED_FIELD_GATES = {
    "log_mae_max": 0.30,
    "correlation_min": 0.90,
    "absolute_p99_iou_min": 0.70,
    "support_area_ratio_min": 0.50,
    "support_area_ratio_max": 2.00,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--prior-damage-vtk", type=Path, required=True)
    parser.add_argument("--damage-vtk", type=Path, required=True)
    parser.add_argument("--load-displacement", type=Path, required=True)
    parser.add_argument("--multiscale-checkpoint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--youngs-modulus", type=float, default=1.0)
    parser.add_argument("--poisson-ratio", type=float, default=0.3)
    parser.add_argument("--length-scale", type=float, default=0.01)
    parser.add_argument("--observation-resolution", type=float, default=0.002)
    parser.add_argument("--bisection-iterations", type=int, default=14)
    parser.add_argument("--max-equilibrium-iterations", type=int, default=25)
    parser.add_argument("--equilibrium-tolerance", type=float, default=1.0e-9)
    parser.add_argument("--equilibrium-residual-tolerance", type=float, default=1.0e-8)
    parser.add_argument("--minimum-pivot-ratio", type=float, default=1.0e-14)
    parser.add_argument("--allow-single-trajectory-diagnostic", action="store_true")
    return parser.parse_args()


def clip_damage_with_tolerance(
    damage: np.ndarray,
    *,
    label: str,
) -> np.ndarray:
    damage = np.asarray(damage, dtype=np.float64)
    if not np.all(np.isfinite(damage)):
        raise ValueError(f"{label} contains non-finite nodal damage")
    minimum = float(np.min(damage))
    maximum = float(np.max(damage))
    if minimum < -DAMAGE_INPUT_TOLERANCE or maximum > 1.0 + DAMAGE_INPUT_TOLERANCE:
        raise ValueError(
            f"{label} nodal damage lies outside the allowed "
            f"[-{DAMAGE_INPUT_TOLERANCE}, {1.0 + DAMAGE_INPUT_TOLERANCE}] range: "
            f"min={minimum}, max={maximum}"
        )
    return np.clip(damage, 0.0, 1.0)


def read_damage_vtk(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mesh = meshio.read(path)
    if "quad" not in mesh.cells_dict or "d" not in mesh.point_data:
        raise ValueError(f"{path} must contain quad cells and nodal point_data['d']")
    points = np.asarray(mesh.points, dtype=np.float64)[:, :2].copy()
    connectivity = np.asarray(mesh.cells_dict["quad"], dtype=np.int32).copy()
    damage = np.asarray(mesh.point_data["d"], dtype=np.float64).reshape(-1).copy()
    if len(damage) != len(points):
        raise ValueError(f"{path} contains an invalid nodal damage field")
    return points, connectivity, clip_damage_with_tolerance(damage, label=str(path))


def require_matching_mesh(
    reference_points: np.ndarray,
    reference_connectivity: np.ndarray,
    points: np.ndarray,
    connectivity: np.ndarray,
    *,
    label: str,
) -> float:
    if not np.array_equal(reference_connectivity, connectivity):
        raise ValueError(f"{label} connectivity does not match the c84 prior VTK")
    if reference_points.shape != points.shape:
        raise ValueError(f"{label} point shape does not match the c84 prior VTK")
    error = float(np.max(np.abs(reference_points - points)))
    if error > 5.0e-7:
        raise ValueError(f"{label} point geometry mismatch is too large: {error}")
    return error


def top_vertical_reaction(
    kinematics: Q4Kinematics,
    nodal_damage: np.ndarray,
    result: EquilibriumResult,
    args: argparse.Namespace,
) -> tuple[float, float]:
    force = equilibrium_internal_force(
        kinematics,
        nodal_damage,
        result.displacement,
        youngs_modulus=args.youngs_modulus,
        poisson_ratio=args.poisson_ratio,
        residual_stiffness=0.0,
    )
    top = np.flatnonzero(
        np.isclose(kinematics.points[:, 1], kinematics.points[:, 1].max())
    )
    bottom = np.flatnonzero(
        np.isclose(kinematics.points[:, 1], kinematics.points[:, 1].min())
    )
    return float(force[2 * top + 1].sum()), float(force[2 * bottom + 1].sum())


def solve_damage(
    kinematics: Q4Kinematics,
    damage: np.ndarray,
    displacement: float,
    args: argparse.Namespace,
) -> tuple[EquilibriumResult, float, float, float]:
    dofs, values = sens_displacement_boundary_conditions(
        kinematics.points, displacement
    )
    started = time.perf_counter()
    result = solve_amor_equilibrium(
        kinematics,
        damage,
        dofs,
        values,
        youngs_modulus=args.youngs_modulus,
        poisson_ratio=args.poisson_ratio,
        residual_stiffness=0.0,
        max_iterations=args.max_equilibrium_iterations,
        tolerance=args.equilibrium_tolerance,
        residual_tolerance=args.equilibrium_residual_tolerance,
        minimum_pivot_ratio=args.minimum_pivot_ratio,
    )
    top, bottom = top_vertical_reaction(kinematics, damage, result, args)
    return result, top, bottom, time.perf_counter() - started


def evaluate_damage(
    label: str,
    damage: np.ndarray,
    beta: float,
    observed_reaction: float,
    peak_displacement: float,
    kinematics: Q4Kinematics,
    args: argparse.Namespace,
) -> dict[str, float | int | bool | str]:
    row: dict[str, float | int | bool | str] = {
        "geometry": label,
        "beta": float(beta),
        "observed_reaction": float(observed_reaction),
    }
    try:
        result, top, bottom, wall = solve_damage(
            kinematics, damage, peak_displacement, args
        )
    except RuntimeError as error:
        row.update(
            {
                "feasible": False,
                "failure": str(error),
                "predicted_reaction": np.nan,
                "relative_reaction_error": np.inf,
            }
        )
        print(json.dumps({"phase": "beta_evaluation", **row}), flush=True)
        return row
    balance = abs(top + bottom) / max(abs(top), abs(bottom), np.finfo(float).eps)
    row.update(
        {
            "feasible": True,
            "predicted_reaction": top,
            "bottom_reaction": bottom,
            "force_balance_relative": balance,
            "relative_reaction_error": relative_reaction_error(
                top, observed_reaction
            ),
            "iterations": result.iterations,
            "normalized_free_residual": result.normalized_residual,
            "minimum_pivot_ratio": result.minimum_pivot_ratio,
            "wall_seconds": wall,
        }
    )
    print(json.dumps({"phase": "beta_evaluation", **row}), flush=True)
    return row


def evaluate_beta(
    label: str,
    prior_damage: np.ndarray,
    observed_profile: np.ndarray,
    beta: float,
    observed_reaction: float,
    peak_displacement: float,
    kinematics: Q4Kinematics,
    args: argparse.Namespace,
) -> dict[str, float | int | bool | str]:
    return evaluate_damage(
        label,
        merge_irreversible_damage(prior_damage, observed_profile, beta),
        beta,
        observed_reaction,
        peak_displacement,
        kinematics,
        args,
    )


def calibrate_geometry(
    label: str,
    prior_damage: np.ndarray,
    observed_profile: np.ndarray,
    observed_reaction: float,
    peak_displacement: float,
    kinematics: Q4Kinematics,
    args: argparse.Namespace,
) -> tuple[dict[str, object], list[dict[str, float | int | bool | str]]]:
    rows = [
        evaluate_beta(
            label,
            prior_damage,
            observed_profile,
            float(beta),
            observed_reaction,
            peak_displacement,
            kinematics,
            args,
        )
        for beta in FIXED_BETA_GRID
    ]
    reaction = np.asarray([row["predicted_reaction"] for row in rows], dtype=float)
    feasible = np.asarray([row["feasible"] for row in rows], dtype=bool)
    brackets = feasible_reaction_brackets(
        FIXED_BETA_GRID, reaction, observed_reaction, feasible
    )
    status: dict[str, object] = {
        "geometry": label,
        "fixed_beta_grid": FIXED_BETA_GRID.tolist(),
        "coarse_brackets": [list(bracket) for bracket in brackets],
        "identifiable": False,
    }
    if len(brackets) != 1:
        status["failure"] = (
            f"expected one feasible reaction root, found {len(brackets)}"
        )
        return status, rows

    lower, upper = brackets[0]
    feasible_rows = [row for row in rows if bool(row["feasible"])]
    best = min(feasible_rows, key=lambda row: float(row["relative_reaction_error"]))
    if lower != upper:
        lower_row = next(row for row in rows if float(row["beta"]) == lower)
        lower_residual = float(lower_row["predicted_reaction"]) - observed_reaction
        for _ in range(args.bisection_iterations):
            midpoint = log_midpoint(lower, upper)
            middle = evaluate_beta(
                label,
                prior_damage,
                observed_profile,
                midpoint,
                observed_reaction,
                peak_displacement,
                kinematics,
                args,
            )
            rows.append(middle)
            if not bool(middle["feasible"]):
                status["failure"] = "log-bisection touched a numerical failure"
                return status, rows
            middle_residual = float(middle["predicted_reaction"]) - observed_reaction
            if float(middle["relative_reaction_error"]) < float(
                best["relative_reaction_error"]
            ):
                best = middle
            if lower_residual * middle_residual <= 0.0:
                upper = midpoint
            else:
                lower = midpoint
                lower_residual = middle_residual
            if (
                float(best["relative_reaction_error"])
                <= REACTION_RELATIVE_TOLERANCE / 10.0
                and upper / lower <= 1.01
            ):
                break
    bracket_factor = 1.0 if lower == upper else upper / lower
    best_beta = float(best["beta"])
    at_grid_boundary = bool(
        np.isclose(best_beta, FIXED_BETA_GRID[0])
        or np.isclose(best_beta, FIXED_BETA_GRID[-1])
    )
    pivot_gate = 10.0 * args.minimum_pivot_ratio
    status.update(
        {
            "beta": best_beta,
            "predicted_reaction": float(best["predicted_reaction"]),
            "relative_reaction_error": float(best["relative_reaction_error"]),
            "minimum_pivot_ratio": float(best["minimum_pivot_ratio"]),
            "final_bracket": [float(lower), float(upper)],
            "final_bracket_factor": float(bracket_factor),
            "at_fixed_grid_boundary": at_grid_boundary,
            "pivot_gate": pivot_gate,
        }
    )
    status["identifiable"] = bool(
        float(status["relative_reaction_error"]) <= REACTION_RELATIVE_TOLERANCE
        and bracket_factor <= MAXIMUM_FINAL_BRACKET_FACTOR
        and not at_grid_boundary
        and float(status["minimum_pivot_ratio"]) >= pivot_gate
    )
    if not status["identifiable"]:
        status["failure"] = "locked reaction-identifiability gates did not all pass"
    return status, rows


def absolute_p99_support(
    prediction: np.ndarray,
    target: np.ndarray,
    areas: np.ndarray,
) -> tuple[float, float, float]:
    prediction = np.asarray(prediction, dtype=np.float64).reshape(-1)
    target = np.asarray(target, dtype=np.float64).reshape(-1)
    areas = np.asarray(areas, dtype=np.float64).reshape(-1)
    if prediction.shape != target.shape or prediction.shape != areas.shape:
        raise ValueError("support fields and areas must have matching shapes")
    threshold = area_weighted_quantile(target, areas, 0.99)
    target_mask = target >= threshold
    prediction_mask = prediction >= threshold
    intersection = float(areas[target_mask & prediction_mask].sum())
    union = float(areas[target_mask | prediction_mask].sum())
    target_area = float(areas[target_mask].sum())
    return (
        intersection / union if union else float("nan"),
        float(areas[prediction_mask].sum()) / target_area
        if target_area
        else float("nan"),
        threshold,
    )


def gate_pass(log_mae: float, correlation: float, iou: float, ratio: float) -> bool:
    return bool(
        log_mae <= LOCKED_FIELD_GATES["log_mae_max"]
        and correlation >= LOCKED_FIELD_GATES["correlation_min"]
        and iou >= LOCKED_FIELD_GATES["absolute_p99_iou_min"]
        and LOCKED_FIELD_GATES["support_area_ratio_min"]
        <= ratio
        <= LOCKED_FIELD_GATES["support_area_ratio_max"]
    )


def main() -> None:
    args = parse_args()
    if not args.allow_single_trajectory_diagnostic:
        raise ValueError(
            "single-trajectory scope requires --allow-single-trajectory-diagnostic"
        )
    if args.length_scale <= 0.0 or args.observation_resolution <= 0.0:
        raise ValueError("length scale and observation resolution must be positive")
    args.out.mkdir(parents=True, exist_ok=True)

    cycles = parse_load_displacement_cycles(
        args.load_displacement, steps_per_cycle=STEPS_PER_CYCLE
    )
    if len(cycles) < OBSERVATION_CYCLE:
        raise ValueError(
            f"load-displacement file does not contain c{OBSERVATION_CYCLE}"
        )
    observed_cycle = cycles[OBSERVATION_CYCLE - 1]
    peak_matches = np.flatnonzero(observed_cycle.step == PEAK_STEP)
    if len(peak_matches) != 1:
        raise ValueError("c86 reaction table does not contain one declared peak step")
    peak_index = int(peak_matches[0])
    postpeak_indices = []
    for step in POSTPEAK_STEPS:
        matches = np.flatnonzero(observed_cycle.step == step)
        if len(matches) != 1:
            raise ValueError(f"c86 reaction table does not contain step {step}")
        postpeak_indices.append(int(matches[0]))
    observed_peak_reaction = float(observed_cycle.fy[peak_index])
    observed_peak_displacement = float(observed_cycle.uy[peak_index])

    # Phase A1: the c84 nodal field is the irreversible historical prior.
    points, connectivity, prior_damage = read_damage_vtk(args.prior_damage_vtk)
    kinematics = build_q4_kinematics(points, connectivity)

    # The c86 VTK exists in pre-lock memory only long enough to derive the mask.
    c86_points, c86_connectivity, c86_hidden_damage = read_damage_vtk(args.damage_vtk)
    prelock_mesh_error = require_matching_mesh(
        points,
        connectivity,
        c86_points,
        c86_connectivity,
        label="c86 observation VTK",
    )
    core95 = notch_connected_core(
        c86_points,
        c86_connectivity,
        c86_hidden_damage,
        threshold=CORE_THRESHOLD,
    )
    observation_path = args.out / "phase_a_c86_observation.npz"
    np.savez_compressed(
        observation_path,
        core95=core95.astype(np.uint8),
        observation_cycle=np.asarray(OBSERVATION_CYCLE, dtype=np.int32),
        threshold=np.asarray(CORE_THRESHOLD),
        peak_step=np.asarray(PEAK_STEP, dtype=np.int32),
        peak_displacement=np.asarray(observed_peak_displacement),
        peak_reaction=np.asarray(observed_peak_reaction),
        postpeak_steps=np.asarray(POSTPEAK_STEPS, dtype=np.int32),
        postpeak_displacement=observed_cycle.uy[postpeak_indices],
        postpeak_reaction=observed_cycle.fy[postpeak_indices],
    )
    observation_hash = sha256(observation_path)
    del c86_hidden_damage, c86_points, c86_connectivity, core95
    gc.collect()

    with np.load(observation_path, allow_pickle=False) as sealed:
        sealed_core = np.asarray(sealed["core95"], dtype=np.uint8).copy()
        sealed_peak_reaction = float(np.asarray(sealed["peak_reaction"]).item())
        sealed_peak_displacement = float(
            np.asarray(sealed["peak_displacement"]).item()
        )
        sealed_postpeak_u = np.asarray(
            sealed["postpeak_displacement"], dtype=np.float64
        ).copy()
        sealed_postpeak_f = np.asarray(
            sealed["postpeak_reaction"], dtype=np.float64
        ).copy()
    if not set(np.unique(sealed_core)).issubset({0, 1}):
        raise ValueError("sealed c86 crack core is not binary")
    if sha256(observation_path) != observation_hash:
        raise RuntimeError("c86 observation changed before inversion")

    aligned_profile, aligned_skeleton = at1_from_raster_skeleton(
        points,
        sealed_core.astype(bool),
        length_scale=args.length_scale,
        resolution=args.observation_resolution,
    )
    shifted_profile, shifted_skeleton = at1_from_raster_skeleton(
        points,
        sealed_core.astype(bool),
        length_scale=args.length_scale,
        resolution=args.observation_resolution,
        vertical_shift=VERTICAL_CONTROL_SHIFT,
    )
    aligned_status, aligned_rows = calibrate_geometry(
        "aligned_visible_profile",
        prior_damage,
        aligned_profile,
        sealed_peak_reaction,
        sealed_peak_displacement,
        kinematics,
        args,
    )
    shifted_status, shifted_rows = calibrate_geometry(
        "shifted_visible_profile_control",
        prior_damage,
        shifted_profile,
        sealed_peak_reaction,
        sealed_peak_displacement,
        kinematics,
        args,
    )
    prior_row = evaluate_damage(
        "c84_prior_only",
        prior_damage,
        0.0,
        sealed_peak_reaction,
        sealed_peak_displacement,
        kinematics,
        args,
    )
    objective_path = args.out / "phase_a_reaction_objective_curve.csv"
    write_rows(objective_path, [prior_row, *aligned_rows, *shifted_rows])
    objective_hash = sha256(objective_path)
    if not bool(aligned_status["identifiable"]):
        raise RuntimeError("aligned historical-damage update is not identifiable")
    if not bool(shifted_status["identifiable"]):
        raise RuntimeError("shifted historical-damage control is not identifiable")

    aligned_beta = float(aligned_status["beta"])
    shifted_beta = float(shifted_status["beta"])
    candidate_damage = {
        "c84_prior_only": prior_damage.copy(),
        "beta1_merged_c84_prior": merge_irreversible_damage(
            prior_damage, aligned_profile, 1.0
        ),
        "inferred_aligned_merged_c84_prior": merge_irreversible_damage(
            prior_damage, aligned_profile, aligned_beta
        ),
        "inferred_shifted_merged_c84_prior": merge_irreversible_damage(
            prior_damage, shifted_profile, shifted_beta
        ),
    }
    candidate_results: dict[
        str, tuple[np.ndarray, EquilibriumResult, float, float, float]
    ] = {}
    for name, damage in candidate_damage.items():
        result, top, bottom, wall = solve_damage(
            kinematics, damage, sealed_peak_displacement, args
        )
        candidate_results[name] = (damage, result, top, bottom, wall)

    postpeak_rows: list[dict[str, float | int | str]] = []
    for name, damage in candidate_damage.items():
        for step, displacement, observed in zip(
            POSTPEAK_STEPS, sealed_postpeak_u, sealed_postpeak_f
        ):
            result, top, bottom, wall = solve_damage(
                kinematics, damage, float(displacement), args
            )
            postpeak_rows.append(
                {
                    "method": name,
                    "cycle": OBSERVATION_CYCLE,
                    "step": step,
                    "displacement": float(displacement),
                    "observed_reaction": float(observed),
                    "predicted_reaction": top,
                    "relative_reaction_error": relative_reaction_error(
                        top, float(observed)
                    ),
                    "bottom_reaction": bottom,
                    "minimum_pivot_ratio": result.minimum_pivot_ratio,
                    "wall_seconds": wall,
                }
            )
    postpeak_path = args.out / "phase_a_postpeak_reaction_table.csv"
    write_rows(postpeak_path, postpeak_rows)
    postpeak_hash = sha256(postpeak_path)
    primary_postpeak_error = max(
        float(row["relative_reaction_error"])
        for row in postpeak_rows
        if row["method"] == "inferred_aligned_merged_c84_prior"
    )
    if primary_postpeak_error > REACTION_RELATIVE_TOLERANCE:
        raise RuntimeError(
            "locked primary failed the c86 postpeak reaction gate: "
            f"{primary_postpeak_error:.3%}"
        )

    locked_arrays: dict[str, np.ndarray] = {
        "prior_damage_c84": prior_damage,
        "aligned_visible_profile": aligned_profile,
        "shifted_visible_profile": shifted_profile,
        "aligned_skeleton_points": aligned_skeleton,
        "shifted_skeleton_points": shifted_skeleton,
        "fixed_beta_grid": FIXED_BETA_GRID,
        "locked_aligned_beta": np.asarray(aligned_beta),
        "locked_shifted_beta": np.asarray(shifted_beta),
    }
    for name, (damage, result, top, bottom, wall) in candidate_results.items():
        locked_arrays[f"damage_{name}"] = damage
        locked_arrays[f"raw_{name}"] = result.tensile_energy_element
        locked_arrays[f"displacement_{name}"] = result.displacement
        locked_arrays[f"top_reaction_{name}"] = np.asarray(top)
        locked_arrays[f"bottom_reaction_{name}"] = np.asarray(bottom)
        locked_arrays[f"wall_seconds_{name}"] = np.asarray(wall)
    locked_path = args.out / "phase_a_locked_historical_assimilation.npz"
    np.savez_compressed(locked_path, **locked_arrays)
    locked_hash = sha256(locked_path)
    lock_record = {
        "prior_cycle": PRIOR_CYCLE,
        "prior_semantics": "true nodal c84 final damage from fields_000084_008.vtk",
        "observation_cycle": OBSERVATION_CYCLE,
        "observation_sha256": observation_hash,
        "prior_damage_vtk_sha256": sha256(args.prior_damage_vtk),
        "load_displacement_sha256": sha256(args.load_displacement),
        "objective_curve_sha256": objective_hash,
        "postpeak_table_sha256": postpeak_hash,
        "locked_candidates_sha256": locked_hash,
        "aligned": aligned_status,
        "shifted_control": shifted_status,
        "primary_postpeak_max_relative_error": primary_postpeak_error,
        "c86_diffuse_damage_reopened": False,
        "c87_c89_targets_opened": False,
        "multiscale_checkpoint_opened": False,
    }
    lock_record_path = args.out / "PHASE_A_LOCK.json"
    lock_record_path.write_text(
        json.dumps(lock_record, indent=2) + "\n", encoding="utf-8"
    )
    lock_record_hash = sha256(lock_record_path)
    if (
        sha256(locked_path) != locked_hash
        or sha256(observation_path) != observation_hash
    ):
        raise RuntimeError("a sealed Phase-A artifact changed before oracle reopening")

    # Phase B1: only now may the diffuse c86 damage be reopened for the oracle.
    oracle_points, oracle_connectivity, oracle_damage = read_damage_vtk(args.damage_vtk)
    postlock_mesh_error = require_matching_mesh(
        points,
        connectivity,
        oracle_points,
        oracle_connectivity,
        label="reopened c86 oracle VTK",
    )
    oracle_result, oracle_top, oracle_bottom, oracle_wall = solve_damage(
        kinematics, oracle_damage, sealed_peak_displacement, args
    )
    oracle_reaction_error = relative_reaction_error(
        oracle_top, sealed_peak_reaction
    )
    if oracle_reaction_error > 0.01:
        raise RuntimeError(
            "post-lock full-damage equilibrium does not reproduce c86 reaction: "
            f"{oracle_reaction_error:.3%}"
        )
    oracle_path = args.out / "phase_b_full_c86_damage_oracle.npz"
    np.savez_compressed(
        oracle_path,
        damage=oracle_damage,
        raw=oracle_result.tensile_energy_element,
        displacement=oracle_result.displacement,
        top_reaction=np.asarray(oracle_top),
        bottom_reaction=np.asarray(oracle_bottom),
    )
    oracle_hash = sha256(oracle_path)

    # Phase B2: c87/c89 targets and the frozen operator are opened after locking.
    device = choose_device(args.device)
    data, states, graph = load_dataset(args.dataset, device)
    state_np = states.detach().cpu().numpy()
    areas = np.asarray(data["areas"], dtype=np.float64)
    floor = float(np.asarray(data["log_floor"]).item())
    dataset_connectivity = np.asarray(data["connectivity"], dtype=np.int32)
    if not np.array_equal(dataset_connectivity, connectivity):
        raise ValueError("operator dataset connectivity does not match the VTK mesh")
    dataset_centroids = np.asarray(data["centroids"], dtype=np.float64)
    centroid_error = float(
        np.max(np.abs(points[connectivity].mean(axis=1) - dataset_centroids))
    )
    if centroid_error > 5.0e-7:
        raise ValueError(
            f"operator dataset centroid mismatch is too large: {centroid_error}"
        )
    c84_element_damage = prior_damage[connectivity].mean(axis=1)
    c84_dataset_damage_error = float(
        np.max(np.abs(c84_element_damage - state_np[PRIOR_CYCLE - 1, :, 0]))
    )
    c84_dataset_damage_mae = float(
        np.mean(np.abs(c84_element_damage - state_np[PRIOR_CYCLE - 1, :, 0]))
    )
    c86_element_damage = oracle_damage[connectivity].mean(axis=1)
    c86_dataset_damage_error = float(
        np.max(
            np.abs(c86_element_damage - state_np[OBSERVATION_CYCLE - 1, :, 0])
        )
    )
    c86_dataset_damage_mae = float(
        np.mean(
            np.abs(c86_element_damage - state_np[OBSERVATION_CYCLE - 1, :, 0])
        )
    )
    if c84_dataset_damage_error > 5.0e-5 or c86_dataset_damage_error > 5.0e-5:
        raise ValueError(
            "VTK and operator-dataset damage semantics are inconsistent: "
            f"c84={c84_dataset_damage_error:.3e}, "
            f"c86={c86_dataset_damage_error:.3e}"
        )

    model, statistics, checkpoint = checkpoint_model(
        args.multiscale_checkpoint, device
    )
    checkpoint_args = checkpoint.get("args", {})
    if checkpoint_args.get("model") != "multiscale":
        raise ValueError("the supplied checkpoint is not the multiscale operator")
    if Path(str(checkpoint_args.get("dataset", ""))).name != args.dataset.name:
        raise ValueError("checkpoint and dataset filenames differ")

    with np.load(locked_path, allow_pickle=False) as locked:
        locked_candidates = {
            name: (
                np.asarray(locked[f"damage_{name}"], dtype=np.float64).copy(),
                np.asarray(locked[f"raw_{name}"], dtype=np.float64).copy(),
            )
            for name in candidate_damage
        }
    evaluation_specs: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, str]] = {
        name: (damage, raw, state_np[PRIOR_CYCLE - 1], "c84_history_fatigue")
        for name, (damage, raw) in locked_candidates.items()
    }
    evaluation_specs["full_c86_damage_oracle"] = (
        oracle_damage,
        oracle_result.tensile_energy_element,
        state_np[OBSERVATION_CYCLE - 1],
        "true_c86_history_fatigue_oracle",
    )
    primary_damage, primary_raw = locked_candidates[
        "inferred_aligned_merged_c84_prior"
    ]
    evaluation_specs["inferred_aligned_true_c86_history_oracle_replay"] = (
        primary_damage,
        primary_raw,
        state_np[OBSERVATION_CYCLE - 1],
        "true_c86_history_fatigue_oracle",
    )

    rows: list[dict[str, str | int | float | bool]] = []
    predictions: dict[str, np.ndarray] = {}
    gate_results: dict[str, dict[str, object]] = {}
    for name, (
        damage,
        raw,
        history_state,
        history_semantics,
    ) in evaluation_specs.items():
        element_damage = damage[connectivity].mean(axis=1)
        generated_c87 = build_observation_assimilated_state(
            history_state, element_damage, raw, floor
        )
        c87_row = metric_row(
            name, PROJECTED_CYCLE, generated_c87, state_np[PROJECTED_CYCLE - 1], areas
        )
        raw_iou, raw_ratio, raw_threshold = absolute_p99_support(
            generated_c87[:, 3], state_np[PROJECTED_CYCLE - 1, :, 3], areas
        )
        c87_pass = gate_pass(
            float(c87_row["log10_psi_raw_mae"]),
            float(c87_row["log10_psi_raw_correlation"]),
            raw_iou,
            raw_ratio,
        )
        c87_row.update(
            {
                "phase": "generated_c87",
                "history_semantics": history_semantics,
                "gate_field": "raw",
                "gate_log_mae": c87_row["log10_psi_raw_mae"],
                "gate_correlation": c87_row["log10_psi_raw_correlation"],
                "gate_absolute_p99_iou": raw_iou,
                "gate_support_area_ratio": raw_ratio,
                "gate_absolute_p99_threshold": raw_threshold,
                "gate_pass": c87_pass,
            }
        )
        rows.append(c87_row)
        predicted_c89 = rollout(
            model,
            statistics,
            generated_c87,
            PROJECTED_CYCLE,
            TEST_CYCLE,
            graph,
            device,
            states.dtype,
        )
        c89_row = metric_row(
            name, TEST_CYCLE, predicted_c89, state_np[TEST_CYCLE - 1], areas
        )
        active_iou = float(c89_row["absolute_p99_iou"])
        active_ratio = float(c89_row["absolute_support_area_ratio"])
        active_threshold = area_weighted_quantile(
            derived_active_log10(
                states[TEST_CYCLE - 1].detach().cpu()
            ).numpy(),
            areas,
            0.99,
        )
        c89_pass = gate_pass(
            float(c89_row["derived_active_log_mae"]),
            float(c89_row["derived_active_correlation"]),
            active_iou,
            active_ratio,
        )
        c89_row.update(
            {
                "phase": "multiscale_c89",
                "history_semantics": history_semantics,
                "gate_field": "active",
                "gate_log_mae": c89_row["derived_active_log_mae"],
                "gate_correlation": c89_row["derived_active_correlation"],
                "gate_absolute_p99_iou": active_iou,
                "gate_support_area_ratio": active_ratio,
                "gate_absolute_p99_threshold": active_threshold,
                "gate_pass": c89_pass,
            }
        )
        rows.append(c89_row)
        gate_results[name] = {
            "c87_raw_pass": c87_pass,
            "c89_active_pass": c89_pass,
            "full_gate_pass": bool(c87_pass and c89_pass),
        }
        predictions[f"{name}_c87"] = generated_c87
        predictions[f"{name}_c89"] = predicted_c89

    metrics_path = args.out / "historical_damage_assimilation_metrics.csv"
    write_rows(metrics_path, rows)
    predictions["state_names"] = np.asarray(
        ["damage", "alpha_bar", "fatigue_degradation", "log10_psi_raw"]
    )
    predictions_path = args.out / "historical_damage_assimilation_predictions.npz"
    np.savez_compressed(predictions_path, **predictions)

    primary_name = "inferred_aligned_merged_c84_prior"
    manifest = {
        "claim_class": (
            "observable-conditioned historical-damage assimilation diagnostic"
        ),
        "fem_reference": "eta0 SENS FEM",
        "prior_cycle": PRIOR_CYCLE,
        "prior_semantics": "true nodal c84 final damage from required prior VTK",
        "observation_cycle": OBSERVATION_CYCLE,
        "observation_semantics": (
            "notch-connected c86 binary core at d>=0.95 plus real c86 "
            "peak/postpeak reactions"
        ),
        "primary_candidate": primary_name,
        "primary_history_semantics": "c84 operator-state history and fatigue channels",
        "trajectory_count": int(np.asarray(data["trajectory_count"]).item()),
        "trajectory_generalization": False,
        "training_performed": False,
        "target_retuning_performed": False,
        "inversion_family": "max(d_prior_c84, 1-(1-d_visible_AT1)^beta)",
        "fixed_beta_grid": FIXED_BETA_GRID.tolist(),
        "aligned_inversion": aligned_status,
        "shifted_control_inversion": shifted_status,
        "locked_aligned_beta": aligned_beta,
        "locked_shifted_beta": shifted_beta,
        "primary_postpeak_max_relative_error": primary_postpeak_error,
        "execution_firewall": {
            "c86_prelock_use": "derive and persist binary core only, then delete",
            "c86_diffuse_damage_reopened_after_lock": True,
            "c87_c89_targets_opened_after_lock": True,
            "multiscale_checkpoint_opened_after_lock": True,
            "phase_a_lock_record": lock_record_path.name,
            "phase_a_lock_record_sha256": lock_record_hash,
        },
        "oracle_reaction": {
            "predicted": oracle_top,
            "observed": sealed_peak_reaction,
            "relative_error": oracle_reaction_error,
            "bottom": oracle_bottom,
            "wall_seconds": oracle_wall,
        },
        "mesh_and_state_audits": {
            "prelock_c84_c86_point_max_abs_error": prelock_mesh_error,
            "postlock_c84_c86_point_max_abs_error": postlock_mesh_error,
            "dataset_centroid_max_abs_error": centroid_error,
            "c84_vtk_to_dataset_element_damage_max_abs_error": c84_dataset_damage_error,
            "c84_vtk_to_dataset_element_damage_mae": c84_dataset_damage_mae,
            "c86_vtk_to_dataset_element_damage_max_abs_error": c86_dataset_damage_error,
            "c86_vtk_to_dataset_element_damage_mae": c86_dataset_damage_mae,
        },
        "constitutive": {
            "split": "AMOR volumetric-deviatoric",
            "stress_state": "plane strain",
            "E": args.youngs_modulus,
            "nu": args.poisson_ratio,
            "residual_stiffness": 0.0,
            "length_scale": args.length_scale,
        },
        "candidate_definitions": {
            "c84_prior_only": "known true nodal c84 damage without c86 update",
            "beta1_merged_c84_prior": "max(c84 prior, nominal c86 visible AT1 profile)",
            "inferred_aligned_merged_c84_prior": (
                "max(c84 prior, reaction-inferred aligned c86 visible AT1 profile)"
            ),
            "inferred_shifted_merged_c84_prior": (
                "same inference with visible geometry shifted vertically by 0.05"
            ),
            "full_c86_damage_oracle": (
                "true diffuse c86 damage and true c86 history/fatigue, opened only "
                "after lock as the oracle ceiling"
            ),
            "inferred_aligned_true_c86_history_oracle_replay": (
                "locked primary damage/raw replayed with hidden true c86 "
                "history/fatigue"
            ),
        },
        "locked_field_gates": {
            "c87_raw": LOCKED_FIELD_GATES,
            "c89_active": LOCKED_FIELD_GATES,
        },
        "gate_results": gate_results,
        "primary_full_gate_pass": gate_results[primary_name]["full_gate_pass"],
        "input_sha256": {
            "prior_damage_vtk": sha256(args.prior_damage_vtk),
            "damage_vtk": sha256(args.damage_vtk),
            "load_displacement": sha256(args.load_displacement),
            "dataset": sha256(args.dataset),
            "multiscale_checkpoint": sha256(args.multiscale_checkpoint),
        },
        "artifacts": {
            "observation": {"path": observation_path.name, "sha256": observation_hash},
            "objective_curve": {"path": objective_path.name, "sha256": objective_hash},
            "postpeak_table": {"path": postpeak_path.name, "sha256": postpeak_hash},
            "locked_candidates": {"path": locked_path.name, "sha256": locked_hash},
            "lock_record": {"path": lock_record_path.name, "sha256": lock_record_hash},
            "c86_oracle": {"path": oracle_path.name, "sha256": oracle_hash},
            "metrics": {"path": metrics_path.name, "sha256": sha256(metrics_path)},
            "predictions": {
                "path": predictions_path.name,
                "sha256": sha256(predictions_path),
            },
        },
        "quarantine": (
            "single trajectory; c84 nodal damage is a known hidden prior; c86 mask is "
            "synthetically derived from hidden FEM damage; no independent DIC"
        ),
    }
    manifest_path = args.out / "RUN_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
