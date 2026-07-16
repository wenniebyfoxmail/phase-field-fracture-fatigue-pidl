#!/usr/bin/env python3
"""Test visible-crack damage reconstructions in the locked c87/c89 mechanics gate."""

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
    build_q4_kinematics,
    sens_displacement_boundary_conditions,
    solve_amor_equilibrium,
)
from damage_observation_reconstruction import (  # noqa: E402
    at1_from_binary_core_points,
    at1_from_binary_straight_extent,
    at1_from_line_segment,
    at1_from_raster_skeleton,
    notch_connected_core,
)
from run_damage_conditioned_equilibrium_gate import (  # noqa: E402
    metric_row,
    rollout,
    sha256,
    write_rows,
)
from run_fem_mechanism_assimilation_gate import checkpoint_model  # noqa: E402
from train_fem_mechanism_mesh_operator import choose_device, load_dataset  # noqa: E402


SOURCE_CYCLE = 86
PROJECTED_CYCLE = 87
TEST_CYCLE = 89


def build_observation_assimilated_state(
    source_state: np.ndarray,
    candidate_element_damage: np.ndarray,
    generated_raw: np.ndarray,
    floor: float,
) -> np.ndarray:
    """Replace damage and raw mechanics while retaining declared history channels."""
    source_state = np.asarray(source_state)
    candidate_element_damage = np.asarray(candidate_element_damage).reshape(-1)
    generated_raw = np.asarray(generated_raw).reshape(-1)
    if source_state.ndim != 2 or source_state.shape[1] != 4:
        raise ValueError("source state must have shape [elements, 4]")
    if len(candidate_element_damage) != len(source_state) or len(generated_raw) != len(
        source_state
    ):
        raise ValueError("assimilated fields must match the source-state element count")
    if floor <= 0.0 or not np.all(np.isfinite(generated_raw)):
        raise ValueError("raw field and positive log floor are required")
    if np.min(candidate_element_damage) < 0.0 or np.max(candidate_element_damage) > 1.0:
        raise ValueError("candidate element damage must lie in [0, 1]")
    assimilated = source_state.copy()
    assimilated[:, 0] = candidate_element_damage
    assimilated[:, 3] = np.log10(np.maximum(generated_raw, floor))
    return assimilated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--damage-vtk", type=Path, required=True)
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
    parser.add_argument("--max-equilibrium-iterations", type=int, default=25)
    parser.add_argument("--equilibrium-tolerance", type=float, default=1.0e-9)
    parser.add_argument("--equilibrium-residual-tolerance", type=float, default=1.0e-8)
    parser.add_argument("--minimum-pivot-ratio", type=float, default=1.0e-14)
    parser.add_argument("--allow-single-trajectory-diagnostic", action="store_true")
    return parser.parse_args()


def candidate_damage_fields(
    points: np.ndarray,
    true_damage_oracle: np.ndarray,
    core95: np.ndarray,
    core99: np.ndarray,
    *,
    length_scale: float,
    observation_resolution: float,
    negative_control_shift: float,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Build the candidate matrix after binary observations have been sealed."""
    skeleton_damage, skeleton = at1_from_raster_skeleton(
        points,
        core95,
        length_scale=length_scale,
        resolution=observation_resolution,
    )
    shifted_damage, shifted_skeleton = at1_from_raster_skeleton(
        points,
        core95,
        length_scale=length_scale,
        resolution=observation_resolution,
        vertical_shift=negative_control_shift,
    )
    candidates = {
        "full_damage_oracle": np.clip(true_damage_oracle, 0.0, 1.0),
        "binary_core95": core95.astype(np.float64),
        "core95_mask_at1": at1_from_binary_core_points(
            points,
            core95,
            length_scale=length_scale,
        ),
        "core99_mask_at1": at1_from_binary_core_points(
            points,
            core99,
            length_scale=length_scale,
        ),
        "core95_skeleton_at1": skeleton_damage,
        "core95_straight_at1": at1_from_binary_straight_extent(
            points,
            core95,
            length_scale=length_scale,
        ),
        "core95_skeleton_shifted": shifted_damage,
        "initial_precrack_at1": at1_from_line_segment(
            points,
            xmin=float(points[:, 0].min()),
            xmax=0.0,
            y_center=0.0,
            length_scale=length_scale,
        ),
    }
    auxiliaries = {
        "core95_skeleton_points": skeleton,
        "core95_shifted_skeleton_points": shifted_skeleton,
    }
    return candidates, auxiliaries


def main() -> None:
    args = parse_args()
    if not args.allow_single_trajectory_diagnostic:
        raise ValueError("single-trajectory scope requires --allow-single-trajectory-diagnostic")
    if args.residual_stiffness != 0.0:
        raise ValueError("the FEM-matched gate requires residual_stiffness=0")
    args.out.mkdir(parents=True, exist_ok=True)

    # Phase A1 converts the c86 diffuse field into a binary observation and
    # seals it before any deployable reconstruction is evaluated.
    mesh = meshio.read(args.damage_vtk)
    points = np.asarray(mesh.points)[:, :2]
    connectivity = np.asarray(mesh.cells_dict["quad"], dtype=np.int32)
    true_nodal_damage = np.clip(np.asarray(mesh.point_data["d"]).reshape(-1), 0.0, 1.0)
    core95 = notch_connected_core(
        points,
        connectivity,
        true_nodal_damage,
        threshold=0.95,
    )
    core99 = notch_connected_core(
        points,
        connectivity,
        true_nodal_damage,
        threshold=0.99,
    )
    observation_path = args.out / "phase_a_binary_crack_observation.npz"
    np.savez_compressed(
        observation_path,
        core95=core95.astype(np.uint8),
        core99=core99.astype(np.uint8),
        source_cycle=np.asarray(SOURCE_CYCLE, dtype=np.int32),
        threshold95=np.asarray(0.95, dtype=np.float64),
        threshold99=np.asarray(0.99, dtype=np.float64),
        observation_resolution=np.asarray(args.observation_resolution, dtype=np.float64),
    )
    observation_hash = sha256(observation_path)
    with np.load(observation_path, allow_pickle=False) as observation:
        sealed_core95 = np.asarray(observation["core95"])
        sealed_core99 = np.asarray(observation["core99"])
    for label, sealed_core in (("core95", sealed_core95), ("core99", sealed_core99)):
        if sealed_core.dtype != np.uint8:
            raise TypeError(f"{label} observation must be uint8, got {sealed_core.dtype}")
        if not set(np.unique(sealed_core)).issubset({0, 1}):
            raise ValueError(f"{label} observation contains non-binary values")
        if not np.any(sealed_core):
            raise ValueError(f"{label} observation is empty")
    if sha256(observation_path) != observation_hash:
        raise RuntimeError("binary observation artifact changed before reconstruction")
    candidates, auxiliaries = candidate_damage_fields(
        points,
        true_nodal_damage,
        sealed_core95.astype(bool),
        sealed_core99.astype(bool),
        length_scale=args.length_scale,
        observation_resolution=args.observation_resolution,
        negative_control_shift=args.negative_control_shift,
    )
    for name, damage in candidates.items():
        if damage.shape != true_nodal_damage.shape:
            raise ValueError(f"{name} damage shape does not match the c86 mesh")
        if not np.all(np.isfinite(damage)):
            raise ValueError(f"{name} damage contains non-finite values")
        if np.min(damage) < 0.0 or np.max(damage) > 1.0:
            raise ValueError(f"{name} damage lies outside [0, 1]")

    # Phase A2 computes matched eta0 equilibrium mechanics without c87/c89.
    kinematics = build_q4_kinematics(points, connectivity)
    prescribed_dofs, prescribed_values = sens_displacement_boundary_conditions(
        points, args.peak_displacement
    )

    phase_a: dict[str, np.ndarray] = {
        "candidate_names": np.asarray(list(candidates)),
        **auxiliaries,
    }
    numerical: dict[str, dict[str, float | int | bool | str]] = {}
    successful_candidates: list[str] = []
    for name, damage in candidates.items():
        started = time.perf_counter()
        phase_a[f"damage_{name}"] = damage
        try:
            result = solve_amor_equilibrium(
                kinematics,
                damage,
                prescribed_dofs,
                prescribed_values,
                youngs_modulus=args.youngs_modulus,
                poisson_ratio=args.poisson_ratio,
                residual_stiffness=args.residual_stiffness,
                max_iterations=args.max_equilibrium_iterations,
                tolerance=args.equilibrium_tolerance,
                residual_tolerance=args.equilibrium_residual_tolerance,
                minimum_pivot_ratio=args.minimum_pivot_ratio,
            )
        except RuntimeError as error:
            phase_a[f"raw_{name}"] = np.full(len(connectivity), np.nan)
            numerical[name] = {
                "converged": False,
                "failure": str(error),
                "wall_seconds": time.perf_counter() - started,
            }
            continue
        phase_a[f"raw_{name}"] = result.tensile_energy_element
        numerical[name] = {
            "converged": result.converged,
            "iterations": result.iterations,
            "relative_update": result.relative_update,
            "sign_changes": result.sign_changes,
            "normalized_free_residual": result.normalized_residual,
            "minimum_pivot_ratio": result.minimum_pivot_ratio,
            "wall_seconds": time.perf_counter() - started,
        }
        if not result.converged:
            phase_a[f"raw_{name}"] = np.full(len(connectivity), np.nan)
            numerical[name]["failure"] = "equilibrium iteration did not converge"
            continue
        successful_candidates.append(name)

    phase_a["successful_candidate_names"] = np.asarray(successful_candidates)

    phase_a_path = args.out / "phase_a_damage_observation_equilibria.npz"
    np.savez_compressed(phase_a_path, **phase_a)
    phase_a_hash = sha256(phase_a_path)
    with np.load(phase_a_path, allow_pickle=False) as sealed:
        sealed_damage = {name: np.asarray(sealed[f"damage_{name}"]).copy() for name in candidates}
        sealed_raw = {name: np.asarray(sealed[f"raw_{name}"]).copy() for name in candidates}
    if sha256(phase_a_path) != phase_a_hash:
        raise RuntimeError("Phase-A observation artifact changed before Phase B")
    required_equilibria = {"full_damage_oracle", "core95_skeleton_at1"}
    missing_required = sorted(required_equilibria - set(successful_candidates))
    if missing_required:
        raise RuntimeError(
            "required equilibrium candidates failed: " + ", ".join(missing_required)
        )

    # Phase B loads the locked c87/c89 trajectory only after all reconstructions
    # and mechanics fields have been persisted and hashed.
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
        raise ValueError("checkpoint and runner dataset filenames differ")

    rows: list[dict[str, str | int | float]] = [
        {
            "method": name,
            "cycle": PROJECTED_CYCLE,
            "phase": "equilibrium_failure",
            "failure": str(numerical[name].get("failure", "unknown")),
        }
        for name in candidates
        if name not in successful_candidates
    ]
    predictions: dict[str, np.ndarray] = {}
    true_c86_element_damage = true_nodal_damage[connectivity].mean(axis=1)
    for name in successful_candidates:
        candidate_element_damage = sealed_damage[name][connectivity].mean(axis=1)
        generated_c87 = build_observation_assimilated_state(
            state_np[SOURCE_CYCLE - 1],
            candidate_element_damage,
            sealed_raw[name],
            floor,
        )
        c87_row = metric_row(name, PROJECTED_CYCLE, generated_c87, state_np[86], areas)
        c87_row.update(
            {
                "phase": "generated_c87",
                "damage_observation_node_mae": float(
                    np.mean(np.abs(sealed_damage[name] - true_nodal_damage))
                ),
                "damage_observation_element_mae": float(
                    np.sum(
                        areas * np.abs(candidate_element_damage - true_c86_element_damage)
                    )
                    / areas.sum()
                ),
            }
        )
        rows.append(c87_row)
        prediction = rollout(
            model,
            statistics,
            generated_c87,
            PROJECTED_CYCLE,
            TEST_CYCLE,
            graph,
            device,
            states.dtype,
        )
        c89_row = metric_row(name, TEST_CYCLE, prediction, state_np[88], areas)
        c89_row["phase"] = "multiscale_c89"
        rows.append(c89_row)
        predictions[f"{name}_c87"] = generated_c87
        predictions[f"{name}_c89"] = prediction

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
        row = metric_row("untouched_c86_rollout", cycle, prediction, state_np[cycle - 1], areas)
        row["phase"] = "control"
        rows.append(row)
    predictions["untouched_c86_rollout_c87"] = untouched_c87
    predictions["untouched_c86_rollout_c89"] = untouched_c89
    predictions["state_names"] = np.asarray(
        ["damage", "alpha_bar", "fatigue_degradation", "log10_psi_raw"]
    )

    write_rows(args.out / "damage_observation_metrics.csv", rows)
    np.savez_compressed(args.out / "damage_observation_predictions.npz", **predictions)
    core_counts = {
        "notch_connected_d>=0.95": int(np.count_nonzero(sealed_core95)),
        "notch_connected_d>=0.99": int(np.count_nonzero(sealed_core99)),
    }
    manifest = {
        "claim_class": "inspection-limited field-mechanism data assimilation",
        "fem_reference": "eta0 SENS c87/c89 cycle-peak raw tensile energy",
        "source_observation": (
            "sealed uint8 notch-connected binary c86 crack geometry; only the "
            "full_damage_oracle ceiling retains diffuse c86 values"
        ),
        "late_cycle_target_loaded_before_phase_a": False,
        "trajectory_count": int(np.asarray(data["trajectory_count"]).item()),
        "trajectory_generalization": False,
        "assimilated_channels": [
            "c86 damage reconstructed from the declared observation candidate",
            "c87 peak raw tensile energy from matched eta0 equilibrium",
        ],
        "oracle_channels_retained": [
            "c86 fatigue history",
            "c86 fatigue degradation",
        ],
        "candidate_definitions": {
            "full_damage_oracle": "true diffuse c86 damage; ceiling only",
            "binary_core95": "sealed binary d>=0.95 observation; lower control",
            "core95_mask_at1": "full-resolution binary mask plus known AT1 ell; geometry ceiling",
            "core99_mask_at1": "d>=0.99 threshold robustness for the mask ceiling",
            "core95_skeleton_at1": (
                "primary inspection candidate: fixed-resolution raster skeleton plus AT1 profile"
            ),
            "core95_straight_at1": "visible x extent and median y plus AT1 profile",
            "core95_skeleton_shifted": (
                "negative control: primary skeleton shifted vertically before AT1 reconstruction"
            ),
            "initial_precrack_at1": "negative control: initial left-half precrack only",
        },
        "promotion_eligible_candidates": ["core95_skeleton_at1"],
        "observation": {
            "artifact": observation_path.name,
            "sha256": observation_hash,
            "dtype": "uint8",
            "threshold_primary": 0.95,
            "threshold_robustness": 0.99,
            "resolution": args.observation_resolution,
            "negative_control_shift": args.negative_control_shift,
            "raster_occupancy_rule": (
                "pixel is occupied when its centre lies within "
                "sqrt(2)*observation_resolution of a binary core node"
            ),
            "raster_rule_frozen_before_target_evaluation": True,
        },
        "core_counts": core_counts,
        "phase_a_artifact": {"path": phase_a_path.name, "sha256": phase_a_hash},
        "input_sha256": {
            "damage_vtk": sha256(args.damage_vtk),
            "dataset": sha256(args.dataset),
            "multiscale_checkpoint": sha256(args.multiscale_checkpoint),
        },
        "dataset_centroid_max_abs_error": centroid_error,
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
        "numerical": numerical,
        "successful_equilibrium_candidates": successful_candidates,
        "failed_equilibrium_candidates": [
            name for name in candidates if name not in successful_candidates
        ],
        "primary_assets": [
            "phase_a_binary_crack_observation.npz",
            "phase_a_damage_observation_equilibria.npz",
            "damage_observation_metrics.csv",
            "damage_observation_predictions.npz",
        ],
        "quarantine": (
            "single trajectory; synthetic full-domain binary crack segmentation; "
            "true c86 fatigue history and fatigue degradation remain supplied"
        ),
    }
    (args.out / "RUN_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
