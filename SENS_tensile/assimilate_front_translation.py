#!/usr/bin/env python3
"""Select a low-dimensional c86 process-zone translation from DIC.

The sealed crack core and the previously selected global background mode are
held fixed. Only the non-core front-local degradation-depth increment may
translate in x. Selection uses c86 peak reaction and synthetic DIC, never c86
diffuse damage or downstream c87/c89 mechanism targets.
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
from scipy.spatial import cKDTree


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from damage_conditioned_equilibrium import build_q4_kinematics  # noqa: E402
from evaluate_spatial_degradation_reconstruction_gate import (  # noqa: E402
    solve_candidate,
)
from spatial_degradation_reconstruction import (  # noqa: E402
    damage_to_z,
    z_to_damage,
)


REACTION_GATE = 0.01
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
    parser.add_argument("--background-candidate", type=Path, required=True)
    parser.add_argument("--local-candidate", type=Path, required=True)
    parser.add_argument("--sealed-c86-observation", type=Path, required=True)
    parser.add_argument("--synthetic-dic", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--shift-grid", type=float, nargs="+", default=(0.0, 0.005, 0.01)
    )
    parser.add_argument("--neighbors", type=int, default=4)
    parser.add_argument("--youngs-modulus", type=float, default=1.0)
    parser.add_argument("--poisson-ratio", type=float, default=0.3)
    parser.add_argument("--max-equilibrium-iterations", type=int, default=50)
    parser.add_argument("--equilibrium-tolerance", type=float, default=1.0e-9)
    parser.add_argument(
        "--equilibrium-residual-tolerance", type=float, default=1.0e-8
    )
    parser.add_argument("--minimum-pivot-ratio", type=float, default=1.0e-14)
    args = parser.parse_args()
    if not args.shift_grid or min(args.shift_grid) < 0.0:
        parser.error("--shift-grid must contain non-negative values")
    if args.neighbors < 1:
        parser.error("--neighbors must be positive")
    return args


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
    prior_z = np.asarray(damage_to_z(prior_damage), dtype=np.float64)
    kinematics = build_q4_kinematics(points, connectivity)

    with np.load(args.background_candidate, allow_pickle=False) as background_file:
        background_damage = np.asarray(
            background_file["nodal_damage"], dtype=np.float64
        )
        front_mask = np.asarray(background_file["nodal_front_mask"], dtype=bool)
        visible_core = np.asarray(background_file["visible_core"], dtype=bool)
    with np.load(args.local_candidate, allow_pickle=False) as local_file:
        local_damage = np.asarray(local_file["nodal_damage"], dtype=np.float64)
    for name, value in (
        ("background damage", background_damage),
        ("local damage", local_damage),
        ("front mask", front_mask),
        ("visible core", visible_core),
    ):
        if value.shape != prior_damage.shape:
            raise ValueError(f"{name} shape mismatch")

    with np.load(args.sealed_c86_observation, allow_pickle=False) as sealed:
        observed_reaction = float(np.asarray(sealed["peak_reaction"]).item())
        peak_displacement = float(np.asarray(sealed["peak_displacement"]).item())
    # NPZ access is lazy: deliberately read displacement only.
    with np.load(args.synthetic_dic, allow_pickle=False) as dic_file:
        observed_displacement = np.asarray(
            dic_file["displacement"], dtype=np.float64
        ).reshape(-1)

    movable = front_mask & ~visible_core
    movable_nodes = np.flatnonzero(movable)
    if not len(movable_nodes):
        raise ValueError("front mask contains no non-core movable nodes")
    tree = cKDTree(points[movable_nodes])
    local_increment = np.maximum(
        np.asarray(damage_to_z(local_damage), dtype=np.float64) - prior_z, 0.0
    )[movable_nodes]

    def candidate(shift: float) -> np.ndarray:
        if shift == 0.0:
            return background_damage.copy()
        query = points[movable_nodes].copy()
        query[:, 0] -= shift
        distances, neighbors = tree.query(query, k=args.neighbors)
        if args.neighbors == 1:
            shifted_increment = local_increment[np.asarray(neighbors)]
        else:
            weights = 1.0 / np.maximum(np.asarray(distances), 1.0e-9)
            shifted_increment = np.sum(
                weights * local_increment[np.asarray(neighbors)], axis=1
            ) / np.sum(weights, axis=1)
        damage = background_damage.copy()
        damage[movable_nodes] = z_to_damage(
            prior_z[movable_nodes] + shifted_increment
        )
        return np.clip(np.maximum(damage, prior_damage), 0.0, 1.0)

    rows: list[dict[str, object]] = []
    candidates: dict[float, np.ndarray] = {}
    for shift in sorted(set(args.shift_grid)):
        damage = candidate(float(shift))
        result, reaction, wall = solve_candidate(
            kinematics, damage, peak_displacement, args
        )
        reaction_error = abs(reaction - observed_reaction) / max(
            abs(observed_reaction), np.finfo(float).eps
        )
        dic_error = float(
            np.linalg.norm(result.displacement - observed_displacement)
            / max(np.linalg.norm(observed_displacement), np.finfo(float).eps)
        )
        rows.append(
            {
                "shift_x": shift,
                "predicted_reaction": reaction,
                "observed_reaction": observed_reaction,
                "reaction_relative_error": reaction_error,
                "dic_relative_l2": dic_error,
                "iterations": result.iterations,
                "active_set_stable": result.active_set_stable,
                "normalized_residual": result.normalized_residual,
                "minimum_pivot_ratio": result.minimum_pivot_ratio,
                "wall_seconds": wall,
            }
        )
        candidates[float(shift)] = damage

    feasible = [
        row
        for row in rows
        if bool(row["active_set_stable"])
        and float(row["reaction_relative_error"]) <= REACTION_GATE
        and float(row["dic_relative_l2"]) <= DIC_GATE
    ]
    if not feasible:
        raise RuntimeError("no translation passed reaction, DIC, and stability gates")
    best = min(
        feasible,
        key=lambda row: (float(row["dic_relative_l2"]), float(row["shift_x"])),
    )
    selected_shift = float(best["shift_x"])
    selected_damage = candidates[selected_shift]

    curve_path = args.out / "front_translation_selection_curve.csv"
    write_rows(curve_path, rows)
    candidate_path = args.out / "front_translated_nodal_damage.npz"
    np.savez_compressed(
        candidate_path,
        nodal_damage=selected_damage,
        background_nodal_damage=background_damage,
        local_nodal_damage=local_damage,
        prior_c84_nodal_damage=prior_damage,
        nodal_front_mask=front_mask.astype(np.uint8),
        visible_core=visible_core.astype(np.uint8),
        selected_shift_x=np.asarray(selected_shift),
        c86_truth_firewall=np.asarray(
            "c86 diffuse damage is not loaded; selection uses reaction and DIC only"
        ),
    )
    manifest = {
        "scope": "sealed_noncore_front_translation_assimilation",
        "observation_cycle": 86,
        "c86_diffuse_damage_truth_loaded": False,
        "c87_c89_targets_loaded": False,
        "parameterization": "x-translation of noncore front-local z increment",
        "selection_observations": ["c86 peak reaction", "synthetic c86 peak DIC"],
        "inverse_crime_warning": (
            "synthetic DIC was generated by the same AMOR model used in selection"
        ),
        "shift_grid": sorted(set(args.shift_grid)),
        "neighbors": args.neighbors,
        "selected_shift_x": selected_shift,
        "selected_reaction_relative_error": float(best["reaction_relative_error"]),
        "selected_dic_relative_l2": float(best["dic_relative_l2"]),
        "reaction_gate": REACTION_GATE,
        "dic_gate": DIC_GATE,
        "input_sha256": {
            "prior_damage_vtk": sha256(args.prior_damage_vtk),
            "background_candidate": sha256(args.background_candidate),
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
