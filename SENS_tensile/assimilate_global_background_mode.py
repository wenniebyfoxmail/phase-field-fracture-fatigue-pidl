#!/usr/bin/env python3
"""Assimilate a sealed global damage mode around a local c86 GNN estimate.

The local process-zone field is held to the reaction-calibrated GNN candidate.
Outside that band, the only admissible correction is the latest pre-lock
two-cycle damage increment (c83 -> c85), scaled by c86 reaction and synthetic
DIC.  No c86 diffuse damage or c87/c89 mechanism target is opened.
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


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from damage_conditioned_equilibrium import build_q4_kinematics  # noqa: E402
from evaluate_spatial_degradation_reconstruction_gate import (  # noqa: E402
    solve_candidate,
)


MODE_TARGET_CYCLE = 85
MODE_PRIOR_CYCLE = 83
DIC_GATE = 0.01


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior-damage-vtk", type=Path, required=True)
    parser.add_argument("--prelock-dataset", type=Path, required=True)
    parser.add_argument("--local-candidate", type=Path, required=True)
    parser.add_argument("--sealed-c86-observation", type=Path, required=True)
    parser.add_argument("--synthetic-dic", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--scale-grid",
        type=float,
        nargs="+",
        default=(0.0, 0.5, 1.0, 1.5, 2.0),
    )
    parser.add_argument("--bisection-iterations", type=int, default=4)
    parser.add_argument("--youngs-modulus", type=float, default=1.0)
    parser.add_argument("--poisson-ratio", type=float, default=0.3)
    parser.add_argument("--max-equilibrium-iterations", type=int, default=50)
    parser.add_argument("--equilibrium-tolerance", type=float, default=1.0e-9)
    parser.add_argument(
        "--equilibrium-residual-tolerance", type=float, default=1.0e-8
    )
    parser.add_argument("--minimum-pivot-ratio", type=float, default=1.0e-14)
    args = parser.parse_args()
    if args.bisection_iterations < 0:
        parser.error("--bisection-iterations must be non-negative")
    if not args.scale_grid or min(args.scale_grid) < 0.0:
        parser.error("--scale-grid must contain non-negative values")
    return args


def area_project_element_to_node(
    element_value: np.ndarray,
    connectivity: np.ndarray,
    areas: np.ndarray,
    node_count: int,
) -> np.ndarray:
    numerator = np.zeros(node_count, dtype=np.float64)
    denominator = np.zeros(node_count, dtype=np.float64)
    weighted = np.asarray(element_value, dtype=np.float64) * areas
    for local in range(connectivity.shape[1]):
        nodes = connectivity[:, local]
        np.add.at(numerator, nodes, weighted)
        np.add.at(denominator, nodes, areas)
    return np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator),
        where=denominator > 0.0,
    )


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    mesh = meshio.read(args.prior_damage_vtk)
    points = np.asarray(mesh.points, dtype=np.float64)[:, :2]
    connectivity = np.asarray(mesh.cells_dict["quad"], dtype=np.int32)
    prior_damage = np.clip(
        np.asarray(mesh.point_data["d"], dtype=np.float64).reshape(-1), 0.0, 1.0
    )
    kinematics = build_q4_kinematics(points, connectivity)

    with np.load(args.prelock_dataset, allow_pickle=False) as prelock:
        cycles = np.asarray(prelock["target_cycles"], dtype=int)
        target_damage = np.asarray(prelock["target_damage"], dtype=np.float64)
        feature_names = np.asarray(prelock["feature_names"]).tolist()
        features = np.asarray(prelock["features"], dtype=np.float64)
        areas = np.asarray(prelock["areas"], dtype=np.float64)
        prelock_connectivity = np.asarray(prelock["connectivity"], dtype=np.int32)
        hidden_target_max_cycle = int(
            np.asarray(prelock["hidden_target_max_cycle"]).item()
        )
    if hidden_target_max_cycle != MODE_TARGET_CYCLE:
        raise ValueError("prelock dataset does not stop at c85")
    if not np.array_equal(prelock_connectivity, connectivity):
        raise ValueError("prelock and VTK connectivity differ")
    prior_feature = feature_names.index("prior_damage_cminus2")
    row = int(np.flatnonzero(cycles == MODE_TARGET_CYCLE)[0])
    element_mode = np.maximum(
        target_damage[row] - features[row, :, prior_feature], 0.0
    )
    nodal_mode = area_project_element_to_node(
        element_mode, connectivity, areas, len(points)
    )

    with np.load(args.local_candidate, allow_pickle=False) as local_file:
        local_damage = np.asarray(local_file["nodal_damage"], dtype=np.float64)
        nodal_front_mask = np.asarray(local_file["nodal_front_mask"], dtype=bool)
    if local_damage.shape != prior_damage.shape:
        raise ValueError("local candidate nodal damage shape mismatch")
    if nodal_front_mask.shape != prior_damage.shape:
        raise ValueError("local candidate front mask shape mismatch")

    with np.load(args.sealed_c86_observation, allow_pickle=False) as sealed:
        observed_reaction = float(np.asarray(sealed["peak_reaction"]).item())
        peak_displacement = float(np.asarray(sealed["peak_displacement"]).item())
        visible_core = np.asarray(sealed["core95"], dtype=bool)
    # NPZ access is lazy: deliberately read displacement only.
    with np.load(args.synthetic_dic, allow_pickle=False) as dic_file:
        observed_displacement = np.asarray(
            dic_file["displacement"], dtype=np.float64
        ).reshape(-1)
    if observed_displacement.shape != (2 * len(points),):
        raise ValueError("synthetic DIC displacement shape mismatch")

    def candidate(scale: float) -> np.ndarray:
        damage = local_damage.copy()
        outside = ~nodal_front_mask
        background = prior_damage + scale * nodal_mode
        damage[outside] = np.maximum(damage[outside], background[outside])
        damage[visible_core] = np.maximum(damage[visible_core], 0.95)
        return np.clip(damage, 0.0, 1.0)

    def evaluate(scale: float) -> tuple[dict[str, object], np.ndarray]:
        damage = candidate(scale)
        result, reaction, wall = solve_candidate(
            kinematics, damage, peak_displacement, args
        )
        reaction_signed = (reaction - observed_reaction) / max(
            abs(observed_reaction), np.finfo(float).eps
        )
        dic_error = float(
            np.linalg.norm(result.displacement - observed_displacement)
            / max(np.linalg.norm(observed_displacement), np.finfo(float).eps)
        )
        return (
            {
                "scale": scale,
                "predicted_reaction": reaction,
                "observed_reaction": observed_reaction,
                "reaction_signed_relative_error": reaction_signed,
                "reaction_relative_error": abs(reaction_signed),
                "dic_relative_l2": dic_error,
                "iterations": result.iterations,
                "active_set_stable": result.active_set_stable,
                "normalized_residual": result.normalized_residual,
                "minimum_pivot_ratio": result.minimum_pivot_ratio,
                "wall_seconds": wall,
            },
            damage,
        )

    rows: list[dict[str, object]] = []
    fields: dict[float, np.ndarray] = {}
    for scale in sorted(set(args.scale_grid)):
        result, damage = evaluate(float(scale))
        rows.append(result)
        fields[float(scale)] = damage

    ordered = sorted(rows, key=lambda item: float(item["scale"]))
    bracket: tuple[float, float] | None = None
    for lower, upper in zip(ordered[:-1], ordered[1:]):
        low_residual = float(lower["reaction_signed_relative_error"])
        high_residual = float(upper["reaction_signed_relative_error"])
        if low_residual * high_residual <= 0.0:
            bracket = (float(lower["scale"]), float(upper["scale"]))
            break
    if bracket is not None:
        lower, upper = bracket
        residual_by_scale = {
            float(item["scale"]): float(item["reaction_signed_relative_error"])
            for item in rows
        }
        for _ in range(args.bisection_iterations):
            middle = 0.5 * (lower + upper)
            result, damage = evaluate(middle)
            rows.append(result)
            fields[middle] = damage
            residual_by_scale[middle] = float(
                result["reaction_signed_relative_error"]
            )
            if residual_by_scale[lower] * residual_by_scale[middle] <= 0.0:
                upper = middle
            else:
                lower = middle

    feasible = [
        item
        for item in rows
        if bool(item["active_set_stable"])
        and float(item["dic_relative_l2"]) <= DIC_GATE
        and np.isfinite(float(item["reaction_relative_error"]))
    ]
    if not feasible:
        raise RuntimeError("no candidate passed the DIC and equilibrium gates")
    best = min(
        feasible,
        key=lambda item: (
            float(item["reaction_relative_error"]), float(item["scale"])
        ),
    )
    best_scale = float(best["scale"])
    best_damage = fields[best_scale]

    curve_path = args.out / "background_mode_selection_curve.csv"
    write_rows(curve_path, sorted(rows, key=lambda item: float(item["scale"])))
    candidate_path = args.out / "background_mode_assimilated_nodal_damage.npz"
    np.savez_compressed(
        candidate_path,
        nodal_damage=best_damage,
        local_nodal_damage=local_damage,
        prior_c84_nodal_damage=prior_damage,
        historical_background_mode=nodal_mode,
        nodal_front_mask=nodal_front_mask.astype(np.uint8),
        visible_core=visible_core.astype(np.uint8),
        selected_scale=np.asarray(best_scale),
        c86_truth_firewall=np.asarray(
            "c86 diffuse damage is not loaded; selection uses reaction and DIC only"
        ),
    )
    manifest = {
        "scope": "sealed_local_gnn_plus_global_historical_mode_assimilation",
        "observation_cycle": 86,
        "c86_diffuse_damage_truth_loaded": False,
        "c87_c89_targets_loaded": False,
        "local_component": "reaction-calibrated one-ring GNN in nodal front mask",
        "global_component": "area-projected c83-to-c85 damage increment outside mask",
        "selection_observations": ["c86 peak reaction", "synthetic c86 peak DIC"],
        "inverse_crime_warning": (
            "synthetic DIC was generated by the same AMOR model used in selection"
        ),
        "mode_target_cycle": MODE_TARGET_CYCLE,
        "mode_prior_cycle": MODE_PRIOR_CYCLE,
        "selected_scale": best_scale,
        "selected_reaction_relative_error": float(best["reaction_relative_error"]),
        "selected_dic_relative_l2": float(best["dic_relative_l2"]),
        "dic_gate": DIC_GATE,
        "input_sha256": {
            "prior_damage_vtk": sha256(args.prior_damage_vtk),
            "prelock_dataset": sha256(args.prelock_dataset),
            "local_candidate": sha256(args.local_candidate),
            "sealed_c86_observation": sha256(args.sealed_c86_observation),
            "synthetic_dic": sha256(args.synthetic_dic),
        },
        "output_sha256": {
            candidate_path.name: sha256(candidate_path),
            curve_path.name: sha256(curve_path),
        },
        "wall_seconds": time.perf_counter() - started,
    }
    manifest_path = args.out / "RUN_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), **manifest}, indent=2))


if __name__ == "__main__":
    main()
