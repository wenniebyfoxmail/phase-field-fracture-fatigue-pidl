#!/usr/bin/env python3
"""Infer c86 degradation amplitude from reaction, then lock c87/c89 validation."""

from __future__ import annotations

import argparse
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
    at1_from_line_segment,
    at1_from_raster_skeleton,
    notch_connected_core,
)
from damage_state_inversion import (  # noqa: E402
    amplify_damage,
    feasible_reaction_brackets,
    log_midpoint,
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
from train_fem_mechanism_mesh_operator import choose_device, load_dataset  # noqa: E402


SOURCE_CYCLE = 86
PROJECTED_CYCLE = 87
TEST_CYCLE = 89


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--damage-vtk", type=Path, required=True)
    parser.add_argument("--load-displacement", type=Path, required=True)
    parser.add_argument("--multiscale-checkpoint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--youngs-modulus", type=float, default=1.0)
    parser.add_argument("--poisson-ratio", type=float, default=0.3)
    parser.add_argument("--peak-displacement", type=float, default=0.12)
    parser.add_argument("--length-scale", type=float, default=0.01)
    parser.add_argument("--observation-resolution", type=float, default=0.002)
    parser.add_argument("--negative-control-shift", type=float, default=0.05)
    parser.add_argument("--residual-stiffness", type=float, default=0.0)
    parser.add_argument("--steps-per-cycle", type=int, default=8)
    parser.add_argument("--peak-step", type=int, default=4)
    parser.add_argument("--postpeak-steps", default="5,6,7")
    parser.add_argument(
        "--coarse-betas",
        default="0.25,0.5,0.75,1,1.5,2,3,4,6,8,12,16",
    )
    parser.add_argument("--bisection-iterations", type=int, default=14)
    parser.add_argument("--reaction-relative-tolerance", type=float, default=0.02)
    parser.add_argument("--maximum-final-bracket-factor", type=float, default=1.25)
    parser.add_argument("--max-equilibrium-iterations", type=int, default=25)
    parser.add_argument("--equilibrium-tolerance", type=float, default=1.0e-9)
    parser.add_argument("--equilibrium-residual-tolerance", type=float, default=1.0e-8)
    parser.add_argument("--minimum-pivot-ratio", type=float, default=1.0e-14)
    parser.add_argument("--allow-single-trajectory-diagnostic", action="store_true")
    return parser.parse_args()


def top_vertical_reaction(
    kinematics: Q4Kinematics,
    nodal_damage: np.ndarray,
    result: EquilibriumResult,
    *,
    youngs_modulus: float,
    poisson_ratio: float,
    residual_stiffness: float,
) -> tuple[float, float]:
    force = equilibrium_internal_force(
        kinematics,
        nodal_damage,
        result.displacement,
        youngs_modulus=youngs_modulus,
        poisson_ratio=poisson_ratio,
        residual_stiffness=residual_stiffness,
    )
    points = kinematics.points
    top = np.flatnonzero(np.isclose(points[:, 1], points[:, 1].max()))
    bottom = np.flatnonzero(np.isclose(points[:, 1], points[:, 1].min()))
    top_reaction = float(force[2 * top + 1].sum())
    bottom_reaction = float(force[2 * bottom + 1].sum())
    return top_reaction, bottom_reaction


def solve_damage(
    kinematics: Q4Kinematics,
    damage: np.ndarray,
    peak_displacement: float,
    args: argparse.Namespace,
) -> tuple[EquilibriumResult, float, float, float]:
    dofs, values = sens_displacement_boundary_conditions(
        kinematics.points, peak_displacement
    )
    started = time.perf_counter()
    result = solve_amor_equilibrium(
        kinematics,
        damage,
        dofs,
        values,
        youngs_modulus=args.youngs_modulus,
        poisson_ratio=args.poisson_ratio,
        residual_stiffness=args.residual_stiffness,
        max_iterations=args.max_equilibrium_iterations,
        tolerance=args.equilibrium_tolerance,
        residual_tolerance=args.equilibrium_residual_tolerance,
        minimum_pivot_ratio=args.minimum_pivot_ratio,
    )
    top, bottom = top_vertical_reaction(
        kinematics,
        damage,
        result,
        youngs_modulus=args.youngs_modulus,
        poisson_ratio=args.poisson_ratio,
        residual_stiffness=args.residual_stiffness,
    )
    return result, top, bottom, time.perf_counter() - started


def evaluate_beta(
    label: str,
    base_damage: np.ndarray,
    beta: float,
    observed_reaction: float,
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
            kinematics,
            amplify_damage(base_damage, beta),
            args.peak_displacement,
            args,
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
            "relative_reaction_error": relative_reaction_error(top, observed_reaction),
            "iterations": result.iterations,
            "normalized_free_residual": result.normalized_residual,
            "minimum_pivot_ratio": result.minimum_pivot_ratio,
            "wall_seconds": wall,
        }
    )
    print(json.dumps({"phase": "beta_evaluation", **row}), flush=True)
    return row


def calibrate_geometry(
    label: str,
    base_damage: np.ndarray,
    observed_reaction: float,
    coarse_betas: np.ndarray,
    kinematics: Q4Kinematics,
    args: argparse.Namespace,
) -> tuple[dict[str, object], list[dict[str, float | int | bool | str]]]:
    rows = [
        evaluate_beta(label, base_damage, float(beta), observed_reaction, kinematics, args)
        for beta in coarse_betas
    ]
    reaction = np.asarray([row["predicted_reaction"] for row in rows], dtype=float)
    feasible = np.asarray([row["feasible"] for row in rows], dtype=bool)
    brackets = feasible_reaction_brackets(
        coarse_betas, reaction, observed_reaction, feasible
    )
    status: dict[str, object] = {
        "geometry": label,
        "coarse_brackets": [list(bracket) for bracket in brackets],
        "identifiable": False,
    }
    if len(brackets) != 1:
        status["failure"] = f"expected one feasible reaction root, found {len(brackets)}"
        return status, rows

    lower, upper = brackets[0]
    if lower == upper:
        best = min(rows, key=lambda row: float(row["relative_reaction_error"]))
        status.update(
            {
                "beta": float(best["beta"]),
                "relative_reaction_error": float(best["relative_reaction_error"]),
                "final_bracket": [lower, upper],
            }
        )
    else:
        lower_row = next(row for row in rows if float(row["beta"]) == lower)
        upper_row = next(row for row in rows if float(row["beta"]) == upper)
        lower_residual = float(lower_row["predicted_reaction"]) - observed_reaction
        upper_residual = float(upper_row["predicted_reaction"]) - observed_reaction
        best = min(
            (lower_row, upper_row),
            key=lambda row: float(row["relative_reaction_error"]),
        )
        for _ in range(args.bisection_iterations):
            midpoint = log_midpoint(lower, upper)
            middle_row = evaluate_beta(
                label, base_damage, midpoint, observed_reaction, kinematics, args
            )
            rows.append(middle_row)
            if not bool(middle_row["feasible"]):
                status["failure"] = "reaction root refinement touched a numerical failure"
                return status, rows
            middle_residual = float(middle_row["predicted_reaction"]) - observed_reaction
            if float(middle_row["relative_reaction_error"]) < float(
                best["relative_reaction_error"]
            ):
                best = middle_row
            if lower_residual * middle_residual <= 0.0:
                upper = midpoint
                upper_residual = middle_residual
            else:
                lower = midpoint
                lower_residual = middle_residual
            if (
                float(best["relative_reaction_error"])
                <= args.reaction_relative_tolerance / 10.0
                and upper / lower <= 1.01
            ):
                break
        status.update(
            {
                "beta": float(best["beta"]),
                "relative_reaction_error": float(best["relative_reaction_error"]),
                "final_bracket": [lower, upper],
            }
        )

    best_beta = float(status["beta"])
    best_row = min(
        (row for row in rows if bool(row["feasible"])),
        key=lambda row: abs(float(row["beta"]) - best_beta),
    )
    final_lower, final_upper = status["final_bracket"]
    bracket_factor = (
        1.0 if final_lower == final_upper else float(final_upper) / float(final_lower)
    )
    at_coarse_boundary = np.isclose(best_beta, coarse_betas[0]) or np.isclose(
        best_beta, coarse_betas[-1]
    )
    pivot_gate = 10.0 * args.minimum_pivot_ratio
    status.update(
        {
            "predicted_reaction": float(best_row["predicted_reaction"]),
            "minimum_pivot_ratio": float(best_row["minimum_pivot_ratio"]),
            "final_bracket_factor": bracket_factor,
            "at_coarse_boundary": bool(at_coarse_boundary),
            "pivot_gate": pivot_gate,
        }
    )
    status["identifiable"] = bool(
        float(status["relative_reaction_error"])
        <= args.reaction_relative_tolerance
        and bracket_factor <= args.maximum_final_bracket_factor
        and not at_coarse_boundary
        and float(status["minimum_pivot_ratio"]) >= pivot_gate
    )
    if not status["identifiable"]:
        status["failure"] = "locked reaction-identifiability gates did not all pass"
    return status, rows


def final_candidate(
    name: str,
    damage: np.ndarray,
    kinematics: Q4Kinematics,
    args: argparse.Namespace,
) -> tuple[str, np.ndarray, EquilibriumResult, float, float, float]:
    result, top, bottom, wall = solve_damage(
        kinematics, damage, args.peak_displacement, args
    )
    return name, damage, result, top, bottom, wall


def main() -> None:
    args = parse_args()
    if not args.allow_single_trajectory_diagnostic:
        raise ValueError("single-trajectory scope requires --allow-single-trajectory-diagnostic")
    if args.residual_stiffness != 0.0:
        raise ValueError("FEM-matched inversion requires residual_stiffness=0")
    args.out.mkdir(parents=True, exist_ok=True)
    coarse_betas = np.asarray(
        [float(value) for value in args.coarse_betas.split(",")], dtype=np.float64
    )
    if len(coarse_betas) < 3 or np.any(np.diff(coarse_betas) <= 0.0):
        raise ValueError("coarse betas must contain at least three increasing values")
    postpeak_steps = [int(value) for value in args.postpeak_steps.split(",")]

    cycles = parse_load_displacement_cycles(
        args.load_displacement, steps_per_cycle=args.steps_per_cycle
    )
    if len(cycles) < SOURCE_CYCLE:
        raise ValueError(f"load-displacement file does not contain c{SOURCE_CYCLE}")
    source_reaction = cycles[SOURCE_CYCLE - 1]
    peak_index = int(np.flatnonzero(source_reaction.step == args.peak_step)[0])
    postpeak_indices = [
        int(np.flatnonzero(source_reaction.step == step)[0]) for step in postpeak_steps
    ]
    observed_peak_reaction = float(source_reaction.fy[peak_index])
    observed_peak_displacement = float(source_reaction.uy[peak_index])
    if not np.isclose(observed_peak_displacement, args.peak_displacement, rtol=0.0, atol=2e-7):
        raise ValueError("declared peak displacement does not match the c86 reaction row")

    mesh = meshio.read(args.damage_vtk)
    points = np.asarray(mesh.points, dtype=np.float64)[:, :2]
    connectivity = np.asarray(mesh.cells_dict["quad"], dtype=np.int32)
    true_damage = np.clip(
        np.asarray(mesh.point_data["d"], dtype=np.float64).reshape(-1), 0.0, 1.0
    )
    core95 = notch_connected_core(points, connectivity, true_damage, threshold=0.95)
    observation_path = args.out / "phase_a_c86_reaction_observation.npz"
    np.savez_compressed(
        observation_path,
        core95=core95.astype(np.uint8),
        source_cycle=np.asarray(SOURCE_CYCLE, dtype=np.int32),
        threshold=np.asarray(0.95),
        observation_resolution=np.asarray(args.observation_resolution),
        peak_step=np.asarray(args.peak_step, dtype=np.int32),
        peak_displacement=np.asarray(observed_peak_displacement),
        peak_reaction=np.asarray(observed_peak_reaction),
        postpeak_steps=np.asarray(postpeak_steps, dtype=np.int32),
        postpeak_displacement=source_reaction.uy[postpeak_indices],
        postpeak_reaction=source_reaction.fy[postpeak_indices],
    )
    observation_hash = sha256(observation_path)

    kinematics = build_q4_kinematics(points, connectivity)
    oracle_result, oracle_top, oracle_bottom, oracle_wall = solve_damage(
        kinematics, true_damage, args.peak_displacement, args
    )
    oracle_path = args.out / "phase_a0_full_damage_oracle.npz"
    np.savez_compressed(
        oracle_path,
        damage=true_damage,
        raw=oracle_result.tensile_energy_element,
        displacement=oracle_result.displacement,
        top_reaction=np.asarray(oracle_top),
        bottom_reaction=np.asarray(oracle_bottom),
        minimum_pivot_ratio=np.asarray(oracle_result.minimum_pivot_ratio),
    )
    oracle_hash = sha256(oracle_path)
    oracle_reaction_error = relative_reaction_error(oracle_top, observed_peak_reaction)
    del true_damage, mesh, oracle_result

    with np.load(observation_path, allow_pickle=False) as sealed:
        sealed_core = np.asarray(sealed["core95"], dtype=np.uint8)
        sealed_peak_reaction = float(np.asarray(sealed["peak_reaction"]).item())
        sealed_postpeak_u = np.asarray(sealed["postpeak_displacement"], dtype=float)
        sealed_postpeak_f = np.asarray(sealed["postpeak_reaction"], dtype=float)
    if sealed_core.dtype != np.uint8 or not set(np.unique(sealed_core)).issubset({0, 1}):
        raise ValueError("sealed crack observation is not binary uint8")
    if sha256(observation_path) != observation_hash:
        raise RuntimeError("c86 observation changed before inversion")
    aligned_base, aligned_skeleton = at1_from_raster_skeleton(
        points,
        sealed_core.astype(bool),
        length_scale=args.length_scale,
        resolution=args.observation_resolution,
    )
    shifted_base, shifted_skeleton = at1_from_raster_skeleton(
        points,
        sealed_core.astype(bool),
        length_scale=args.length_scale,
        resolution=args.observation_resolution,
        vertical_shift=args.negative_control_shift,
    )

    aligned_status, aligned_rows = calibrate_geometry(
        "aligned_skeleton",
        aligned_base,
        sealed_peak_reaction,
        coarse_betas,
        kinematics,
        args,
    )
    shifted_status, shifted_rows = calibrate_geometry(
        "shifted_skeleton_control",
        shifted_base,
        sealed_peak_reaction,
        coarse_betas,
        kinematics,
        args,
    )
    objective_rows = aligned_rows + shifted_rows
    objective_path = args.out / "phase_a_reaction_objective_curve.csv"
    write_rows(objective_path, objective_rows)
    objective_hash = sha256(objective_path)

    calibration_status_path = args.out / "phase_a_calibration_status.json"
    calibration_status = {
        "aligned": aligned_status,
        "shifted_control": shifted_status,
        "oracle_reaction_relative_error": oracle_reaction_error,
        "oracle_reaction_gate": 0.01,
        "observation_sha256": observation_hash,
        "oracle_sha256": oracle_hash,
        "objective_curve_sha256": objective_hash,
        "target_cycles_loaded": False,
    }
    calibration_status_path.write_text(
        json.dumps(calibration_status, indent=2) + "\n", encoding="utf-8"
    )
    if oracle_reaction_error > 0.01:
        raise RuntimeError("full-damage equilibrium does not reproduce the c86 reaction")
    if not bool(aligned_status["identifiable"]):
        raise RuntimeError("aligned degradation amplitude is not identifiable from c86 reaction")

    locked_beta = float(aligned_status["beta"])
    with np.load(oracle_path, allow_pickle=False) as oracle:
        sealed_oracle_damage = np.asarray(oracle["damage"]).copy()
    candidate_specs: list[tuple[str, np.ndarray]] = [
        ("full_damage_oracle", sealed_oracle_damage),
        ("beta1_aligned_skeleton", amplify_damage(aligned_base, 1.0)),
        (
            "reaction_inferred_aligned_skeleton",
            amplify_damage(aligned_base, locked_beta),
        ),
    ]
    if bool(shifted_status["identifiable"]):
        candidate_specs.append(
            (
                "reaction_inferred_shifted_skeleton_control",
                amplify_damage(shifted_base, float(shifted_status["beta"])),
            )
        )
    candidate_specs.append(
        (
            "initial_precrack_control",
            at1_from_line_segment(
                points,
                xmin=float(points[:, 0].min()),
                xmax=0.0,
                y_center=0.0,
                length_scale=args.length_scale,
            ),
        )
    )

    final_results: dict[str, tuple[np.ndarray, EquilibriumResult, float, float, float]] = {}
    for name, damage in candidate_specs:
        _, damage, result, top, bottom, wall = final_candidate(
            name, damage, kinematics, args
        )
        final_results[name] = (damage, result, top, bottom, wall)
        print(
            json.dumps(
                {
                    "phase": "locked_candidate_equilibrium",
                    "candidate": name,
                    "reaction": top,
                    "minimum_pivot_ratio": result.minimum_pivot_ratio,
                    "wall_seconds": wall,
                }
            ),
            flush=True,
        )

    inferred_damage, inferred_result, _, _, _ = final_results[
        "reaction_inferred_aligned_skeleton"
    ]
    postpeak_rows: list[dict[str, float | int | str]] = []
    for step, displacement, observed in zip(
        postpeak_steps, sealed_postpeak_u, sealed_postpeak_f
    ):
        result, predicted, bottom, wall = solve_damage(
            kinematics, inferred_damage, float(displacement), args
        )
        postpeak_rows.append(
            {
                "cycle": SOURCE_CYCLE,
                "step": step,
                "displacement": float(displacement),
                "observed_reaction": float(observed),
                "predicted_reaction": predicted,
                "relative_reaction_error": relative_reaction_error(predicted, float(observed)),
                "bottom_reaction": bottom,
                "minimum_pivot_ratio": result.minimum_pivot_ratio,
                "wall_seconds": wall,
            }
        )
    postpeak_path = args.out / "phase_a_postpeak_reaction_validation.csv"
    write_rows(postpeak_path, postpeak_rows)
    postpeak_hash = sha256(postpeak_path)
    maximum_postpeak_error = max(
        float(row["relative_reaction_error"]) for row in postpeak_rows
    )
    if maximum_postpeak_error > args.reaction_relative_tolerance:
        raise RuntimeError("locked c86 postpeak reaction validation failed")

    locked_arrays: dict[str, np.ndarray] = {
        "aligned_skeleton_points": aligned_skeleton,
        "shifted_skeleton_points": shifted_skeleton,
        "coarse_betas": coarse_betas,
        "locked_beta": np.asarray(locked_beta),
    }
    for name, (damage, result, top, bottom, _) in final_results.items():
        locked_arrays[f"damage_{name}"] = damage
        locked_arrays[f"raw_{name}"] = result.tensile_energy_element
        locked_arrays[f"top_reaction_{name}"] = np.asarray(top)
        locked_arrays[f"bottom_reaction_{name}"] = np.asarray(bottom)
    locked_path = args.out / "phase_a_locked_damage_inversion.npz"
    np.savez_compressed(locked_path, **locked_arrays)
    locked_hash = sha256(locked_path)
    with np.load(locked_path, allow_pickle=False) as locked:
        locked_candidates = {
            name: (
                np.asarray(locked[f"damage_{name}"]).copy(),
                np.asarray(locked[f"raw_{name}"]).copy(),
            )
            for name in final_results
        }
    if sha256(locked_path) != locked_hash:
        raise RuntimeError("locked inversion artifact changed before target evaluation")
    calibration_status.update(
        {
            "postpeak_validation_sha256": postpeak_hash,
            "maximum_postpeak_reaction_relative_error": maximum_postpeak_error,
            "locked_inversion_sha256": locked_hash,
            "target_cycles_loaded": False,
        }
    )
    calibration_status_path.write_text(
        json.dumps(calibration_status, indent=2) + "\n", encoding="utf-8"
    )
    calibration_status_hash = sha256(calibration_status_path)

    # Phase B begins only after the inferred beta and every candidate field are sealed.
    device = choose_device(args.device)
    data, states, graph = load_dataset(args.dataset, device)
    state_np = states.detach().cpu().numpy()
    areas = np.asarray(data["areas"], dtype=np.float64)
    floor = float(np.asarray(data["log_floor"]).item())
    if not np.array_equal(np.asarray(data["connectivity"], dtype=np.int32), connectivity):
        raise ValueError("VTK connectivity does not match the operator dataset")
    centroid_error = float(
        np.max(
            np.abs(
                points[connectivity].mean(axis=1)
                - np.asarray(data["centroids"], dtype=np.float64)
            )
        )
    )
    if centroid_error > 5.0e-7:
        raise ValueError(f"VTK/dataset geometry mismatch: {centroid_error}")
    model, statistics, checkpoint = checkpoint_model(args.multiscale_checkpoint, device)
    checkpoint_args = checkpoint.get("args", {})
    if checkpoint_args.get("model") != "multiscale":
        raise ValueError("the supplied checkpoint is not the multiscale operator")
    if Path(str(checkpoint_args.get("dataset", ""))).name != args.dataset.name:
        raise ValueError("checkpoint and dataset filenames differ")

    rows: list[dict[str, str | int | float]] = []
    predictions: dict[str, np.ndarray] = {}
    for name, (damage, raw) in locked_candidates.items():
        element_damage = damage[connectivity].mean(axis=1)
        generated_c87 = build_observation_assimilated_state(
            state_np[SOURCE_CYCLE - 1], element_damage, raw, floor
        )
        c87_row = metric_row(name, PROJECTED_CYCLE, generated_c87, state_np[86], areas)
        c87_row["phase"] = "generated_c87"
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
        c89_row = metric_row(name, TEST_CYCLE, predicted_c89, state_np[88], areas)
        c89_row["phase"] = "multiscale_c89"
        rows.append(c89_row)
        predictions[f"{name}_c87"] = generated_c87
        predictions[f"{name}_c89"] = predicted_c89

    untouched_c87 = rollout(
        model,
        statistics,
        state_np[SOURCE_CYCLE - 1],
        SOURCE_CYCLE,
        PROJECTED_CYCLE,
        graph,
        device,
        states.dtype,
    )
    untouched_c89 = rollout(
        model,
        statistics,
        state_np[SOURCE_CYCLE - 1],
        SOURCE_CYCLE,
        TEST_CYCLE,
        graph,
        device,
        states.dtype,
    )
    for cycle, prediction in ((PROJECTED_CYCLE, untouched_c87), (TEST_CYCLE, untouched_c89)):
        row = metric_row(
            "untouched_c86_rollout", cycle, prediction, state_np[cycle - 1], areas
        )
        row["phase"] = "control"
        rows.append(row)
    predictions["untouched_c86_rollout_c87"] = untouched_c87
    predictions["untouched_c86_rollout_c89"] = untouched_c89
    predictions["state_names"] = np.asarray(
        ["damage", "alpha_bar", "fatigue_degradation", "log10_psi_raw"]
    )
    write_rows(args.out / "reaction_inversion_metrics.csv", rows)
    np.savez_compressed(args.out / "reaction_inversion_predictions.npz", **predictions)

    manifest = {
        "claim_class": "observable-conditioned hidden-state identification",
        "fem_reference": "eta0 SENS c86 reaction and c87/c89 fields",
        "source_observation": (
            "notch-connected uint8 c86 crack core plus real c86 peak/postpeak "
            "load-displacement reactions"
        ),
        "source_cycle": SOURCE_CYCLE,
        "late_cycle_target_loaded_before_lock": False,
        "trajectory_count": int(np.asarray(data["trajectory_count"]).item()),
        "trajectory_generalization": False,
        "inversion_family": "d_beta = 1 - (1 - d_skeleton_AT1)^beta",
        "inversion": calibration_status,
        "locked_beta": locked_beta,
        "maximum_postpeak_reaction_relative_error": maximum_postpeak_error,
        "oracle_reaction": {
            "predicted": oracle_top,
            "observed": observed_peak_reaction,
            "relative_error": oracle_reaction_error,
            "wall_seconds": oracle_wall,
        },
        "input_sha256": {
            "damage_vtk": sha256(args.damage_vtk),
            "load_displacement": sha256(args.load_displacement),
            "dataset": sha256(args.dataset),
            "multiscale_checkpoint": sha256(args.multiscale_checkpoint),
        },
        "sealed_artifacts": {
            "observation": {"path": observation_path.name, "sha256": observation_hash},
            "full_damage_oracle": {"path": oracle_path.name, "sha256": oracle_hash},
            "objective_curve": {"path": objective_path.name, "sha256": objective_hash},
            "postpeak_validation": {"path": postpeak_path.name, "sha256": postpeak_hash},
            "locked_inversion": {"path": locked_path.name, "sha256": locked_hash},
            "calibration_status": {
                "path": calibration_status_path.name,
                "sha256": calibration_status_hash,
            },
        },
        "constitutive": {
            "split": "AMOR volumetric-deviatoric",
            "stress_state": "plane strain",
            "E": args.youngs_modulus,
            "nu": args.poisson_ratio,
            "ell": args.length_scale,
            "residual_stiffness": args.residual_stiffness,
        },
        "boundary_conditions": {
            "fix_x": "top and bottom edges",
            "fix_y": "bottom edge",
            "prescribed_y": "top edge",
            "peak_displacement": args.peak_displacement,
        },
        "candidate_definitions": {
            "full_damage_oracle": "true diffuse c86 damage; ceiling only",
            "beta1_aligned_skeleton": "unmodified visible-crack AT1 reconstruction",
            "reaction_inferred_aligned_skeleton": "sole promotion candidate",
            "reaction_inferred_shifted_skeleton_control": (
                "same reaction inversion after a 0.05 vertical geometry shift"
            ),
            "initial_precrack_control": "initial left-half precrack only",
            "untouched_c86_rollout": "frozen operator without observation assimilation",
        },
        "oracle_channels_retained": ["c86 fatigue history", "c86 fatigue degradation"],
        "dataset_centroid_max_abs_error": centroid_error,
        "locked_promotion_gates": {
            "c87_raw_log_mae_max": 0.30,
            "c87_raw_correlation_min": 0.90,
            "c87_raw_absolute_p99_iou_min": 0.70,
            "c87_raw_support_area_ratio": [0.5, 2.0],
            "c89_active_log_mae_max": 0.30,
            "c89_active_correlation_min": 0.90,
            "c89_active_absolute_p99_iou_min": 0.70,
            "c89_active_support_area_ratio": [0.5, 2.0],
        },
        "primary_assets": [
            observation_path.name,
            "phase_a_reaction_objective_curve.csv",
            "phase_a_postpeak_reaction_validation.csv",
            locked_path.name,
            "reaction_inversion_metrics.csv",
            "reaction_inversion_predictions.npz",
        ],
        "quarantine": (
            "single trajectory; synthetic full-domain binary crack segmentation; "
            "true c86 history/degradation retained; no independent DIC"
        ),
    }
    (args.out / "RUN_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
