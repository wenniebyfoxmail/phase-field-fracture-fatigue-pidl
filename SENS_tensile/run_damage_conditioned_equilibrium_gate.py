#!/usr/bin/env python3
"""Project the final c86 damage state through equilibrium and forecast c89.

Phase A reads only the c86 final-damage VTK and writes a hashed equilibrium
projection.  Phase B then opens the operator dataset and checkpoints to score
the generated transition and frozen-operator rollouts against FEM c87/c89.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import time

import meshio
import numpy as np
import torch


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from damage_conditioned_equilibrium import (  # noqa: E402
    build_q4_kinematics,
    sens_displacement_boundary_conditions,
    solve_amor_equilibrium,
)
from run_fem_mechanism_assimilation_gate import (  # noqa: E402
    checkpoint_model,
    forecast_step,
)
from train_fem_mechanism_mesh_operator import (  # noqa: E402
    choose_device,
    field_metrics,
    load_dataset,
)


SOURCE_CYCLE = 86
PROJECTED_CYCLE = 87
TEST_CYCLE = 89


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--damage-vtk", type=Path, required=True)
    parser.add_argument("--pointwise-checkpoint", type=Path, required=True)
    parser.add_argument("--multiscale-checkpoint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--youngs-modulus", type=float, default=1.0)
    parser.add_argument("--poisson-ratio", type=float, default=0.3)
    parser.add_argument("--peak-displacement", type=float, default=0.12)
    parser.add_argument("--residual-stiffness", type=float, default=0.0)
    parser.add_argument("--max-equilibrium-iterations", type=int, default=25)
    parser.add_argument("--equilibrium-tolerance", type=float, default=1.0e-9)
    parser.add_argument("--equilibrium-residual-tolerance", type=float, default=1.0e-8)
    parser.add_argument("--minimum-pivot-ratio", type=float, default=1.0e-14)
    parser.add_argument("--allow-single-trajectory-diagnostic", action="store_true")
    return parser.parse_args()


def metric_row(
    label: str,
    cycle: int,
    prediction: np.ndarray,
    target: np.ndarray,
    areas: np.ndarray,
) -> dict[str, str | int | float]:
    row: dict[str, str | int | float] = {"method": label, "cycle": cycle}
    row.update(field_metrics(prediction, target, areas))
    return row


def write_rows(path: Path, rows: list[dict[str, str | int | float]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@torch.inference_mode()
def rollout(
    model: torch.nn.Module,
    statistics: object,
    initial: np.ndarray,
    initial_cycle: int,
    final_cycle: int,
    graph: dict[str, torch.Tensor],
    device: torch.device,
    dtype: torch.dtype,
) -> np.ndarray:
    current = torch.from_numpy(initial).to(device=device, dtype=dtype)
    for cycle in range(initial_cycle + 1, final_cycle + 1):
        current = forecast_step(model, current, cycle, graph, statistics)
    return current.detach().cpu().numpy()


def main() -> None:
    args = parse_args()
    if not args.allow_single_trajectory_diagnostic:
        raise ValueError("single-trajectory scope requires --allow-single-trajectory-diagnostic")
    if args.residual_stiffness != 0.0:
        raise ValueError("the primary FEM-matched gate requires residual_stiffness=0")

    args.out.mkdir(parents=True, exist_ok=True)

    # Phase A is structurally sealed: no operator dataset or late-cycle target
    # is opened until the c86-damage-conditioned mechanics field is persisted.
    mesh = meshio.read(args.damage_vtk)
    points = np.asarray(mesh.points)[:, :2]
    connectivity = np.asarray(mesh.cells_dict["quad"], dtype=np.int32)
    nodal_damage = np.clip(np.asarray(mesh.point_data["d"]).reshape(-1), 0.0, 1.0)

    started = time.perf_counter()
    kinematics = build_q4_kinematics(points, connectivity)
    prescribed_dofs, prescribed_values = sens_displacement_boundary_conditions(
        points, args.peak_displacement
    )
    equilibrium = solve_amor_equilibrium(
        kinematics,
        nodal_damage,
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
    equilibrium_seconds = time.perf_counter() - started
    phase_a_path = args.out / "phase_a_c86_damage_equilibrium.npz"
    np.savez_compressed(
        phase_a_path,
        points=points,
        connectivity=connectivity,
        nodal_damage=nodal_damage,
        displacement=equilibrium.displacement,
        tensile_energy_gauss=equilibrium.tensile_energy_gauss,
        tensile_energy_element=equilibrium.tensile_energy_element,
    )
    phase_a_hash = sha256(phase_a_path)
    with np.load(phase_a_path, allow_pickle=False) as phase_a:
        generated_tensile_energy = np.asarray(
            phase_a["tensile_energy_element"], dtype=np.float64
        ).copy()
    if sha256(phase_a_path) != phase_a_hash:
        raise RuntimeError("Phase-A artifact changed while being bound to Phase B")

    # Phase B opens c87/c89 only after the generated raw mechanics is frozen.
    device = choose_device(args.device)
    data, states, graph = load_dataset(args.dataset, device)
    state_np = states.detach().cpu().numpy()
    dataset_connectivity = np.asarray(data["connectivity"], dtype=np.int32)
    areas = np.asarray(data["areas"], dtype=np.float64)
    floor = float(np.asarray(data["log_floor"]).item())
    if not np.array_equal(dataset_connectivity, connectivity):
        raise ValueError("c86 VTK connectivity does not match the operator dataset")
    vtk_centroids = points[connectivity].mean(axis=1)
    geometry_error = float(
        np.max(np.abs(vtk_centroids - np.asarray(data["centroids"], dtype=np.float64)))
    )
    if geometry_error > 5.0e-7:
        raise ValueError(f"c86 VTK/dataset geometry mismatch is too large: {geometry_error}")
    element_damage = nodal_damage[connectivity].mean(axis=1)
    dataset_damage_error = float(
        np.max(np.abs(element_damage - state_np[SOURCE_CYCLE - 1, :, 0]))
    )
    if dataset_damage_error > 5.0e-5:
        raise ValueError(f"c86 VTK/dataset damage mismatch is too large: {dataset_damage_error}")

    projected_c87 = state_np[SOURCE_CYCLE - 1].copy()
    projected_c87[:, 3] = np.log10(np.maximum(generated_tensile_energy, floor))
    true_c87_raw = state_np[SOURCE_CYCLE - 1].copy()
    true_c87_raw[:, 3] = state_np[PROJECTED_CYCLE - 1, :, 3]
    rows = [
        metric_row(
            "c86_damage_conditioned_equilibrium",
            PROJECTED_CYCLE,
            projected_c87,
            state_np[PROJECTED_CYCLE - 1],
            areas,
        ),
        metric_row(
            "true_c87_raw_persistence_control",
            PROJECTED_CYCLE,
            true_c87_raw,
            state_np[PROJECTED_CYCLE - 1],
            areas,
        ),
    ]
    predictions: dict[str, np.ndarray] = {
        "projected_c87": projected_c87,
        "equilibrium_displacement": equilibrium.displacement,
        "equilibrium_tensile_energy_gauss": equilibrium.tensile_energy_gauss,
        "true_c87_raw_persistence_control": true_c87_raw,
    }

    for model_name, checkpoint_path in (
        ("pointwise", args.pointwise_checkpoint),
        ("multiscale", args.multiscale_checkpoint),
    ):
        model, statistics, checkpoint = checkpoint_model(checkpoint_path, device)
        checkpoint_args = checkpoint.get("args", {})
        if checkpoint_args.get("model") != model_name:
            raise ValueError(
                f"checkpoint label mismatch: expected {model_name}, "
                f"found {checkpoint_args.get('model')}"
            )
        checkpoint_dataset = Path(str(checkpoint_args.get("dataset", ""))).name
        if checkpoint_dataset != args.dataset.name:
            raise ValueError(
                f"checkpoint dataset mismatch: expected {args.dataset.name}, "
                f"found {checkpoint_dataset}"
            )
        c86_prior_c87 = rollout(
            model,
            statistics,
            state_np[SOURCE_CYCLE - 1],
            SOURCE_CYCLE,
            PROJECTED_CYCLE,
            graph,
            device,
            states.dtype,
        )
        rows.append(
            metric_row(
                f"{model_name}_untouched_c86_prior",
                PROJECTED_CYCLE,
                c86_prior_c87,
                state_np[PROJECTED_CYCLE - 1],
                areas,
            )
        )
        controls = {
            "untouched_c86_rollout": (state_np[SOURCE_CYCLE - 1], SOURCE_CYCLE),
            "generated_raw_projection": (projected_c87, PROJECTED_CYCLE),
            "true_c87_raw_oracle": (true_c87_raw, PROJECTED_CYCLE),
            "true_c87_full_state_restart": (state_np[PROJECTED_CYCLE - 1], PROJECTED_CYCLE),
        }
        for control_name, (initial, initial_cycle) in controls.items():
            prediction = rollout(
                model,
                statistics,
                initial,
                initial_cycle,
                TEST_CYCLE,
                graph,
                device,
                states.dtype,
            )
            label = f"{model_name}_{control_name}"
            predictions[f"{label}_c89"] = prediction
            rows.append(metric_row(label, TEST_CYCLE, prediction, state_np[TEST_CYCLE - 1], areas))

    write_rows(args.out / "equilibrium_projection_metrics.csv", rows)
    predictions["state_names"] = np.asarray(
        ["damage", "alpha_bar", "fatigue_degradation", "log10_psi_raw"]
    )
    np.savez_compressed(args.out / "equilibrium_projection.npz", **predictions)

    right_layer = points[:, 0] > 0.48
    manifest = {
        "claim_class": "trajectory-sufficiency / event-transition diagnostic",
        "fem_reference": "eta0 cycle-peak raw tensile energy",
        "source_state": "c86 final unloaded damage after first right-boundary detection",
        "generated_state": "synthetic c87 peak raw mechanics from c86 damage-conditioned equilibrium",
        "locked_target": "c87/c89; not opened until the Phase-A equilibrium artifact was written and hashed",
        "trajectory_count": int(np.asarray(data["trajectory_count"]).item()),
        "trajectory_generalization": False,
        "damage_vtk": str(args.damage_vtk.resolve()),
        "input_sha256": {
            "damage_vtk": sha256(args.damage_vtk),
            "dataset": sha256(args.dataset),
            "pointwise_checkpoint": sha256(args.pointwise_checkpoint),
            "multiscale_checkpoint": sha256(args.multiscale_checkpoint),
        },
        "phase_a_artifact": {
            "path": phase_a_path.name,
            "sha256": phase_a_hash,
            "late_cycle_target_loaded_before_write": False,
        },
        "dataset_centroid_max_abs_error": geometry_error,
        "dataset_damage_max_abs_error": dataset_damage_error,
        "constitutive": {
            "split": "AMOR volumetric-deviatoric",
            "stress_state": "plane strain",
            "E": args.youngs_modulus,
            "nu": args.poisson_ratio,
            "residual_stiffness": args.residual_stiffness,
        },
        "boundary_conditions": {
            "fix_x": "top and bottom edges",
            "fix_y": "bottom edge",
            "disp_y": "top edge",
            "peak_displacement": args.peak_displacement,
        },
        "c86_right_layer_damage": {
            "threshold": 0.95,
            "node_count": int(np.count_nonzero(nodal_damage[right_layer] > 0.95)),
            "max": float(nodal_damage[right_layer].max()),
        },
        "equilibrium": {
            "converged": equilibrium.converged,
            "iterations": equilibrium.iterations,
            "relative_update": equilibrium.relative_update,
            "sign_changes": equilibrium.sign_changes,
            "negative_trace_fraction": equilibrium.negative_trace_fraction,
            "free_residual_norm": equilibrium.residual_norm,
            "normalized_free_residual": equilibrium.normalized_residual,
            "minimum_pivot_ratio": equilibrium.minimum_pivot_ratio,
            "wall_seconds": equilibrium_seconds,
        },
        "controls": [
            "untouched c86 rollout",
            "generated c87 raw projection",
            "true c87 raw oracle with c86 damage/history persistence",
            "true c87 full-state restart",
        ],
        "primary_assets": [
            "phase_a_c86_damage_equilibrium.npz",
            "equilibrium_projection_metrics.csv",
            "equilibrium_projection.npz",
        ],
        "quarantine": "single trajectory; true FEM c86 damage supplied",
    }
    (args.out / "RUN_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
