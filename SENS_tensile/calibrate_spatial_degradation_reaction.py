#!/usr/bin/env python3
"""Calibrate a sealed c86 GNN degradation increment from reaction only.

This exploratory post-lock gate preserves the selected GNN spatial ranking and
fits one scalar amplification inside a geometry-only crack-front band. It does
not open c86 diffuse damage or c87/c89 field targets.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import meshio
import numpy as np


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from damage_conditioned_equilibrium import build_q4_kinematics  # noqa: E402
from evaluate_spatial_degradation_reconstruction_gate import (  # noqa: E402
    CORE_DAMAGE,
    element_z_to_nodal_damage,
    solve_candidate,
)
from spatial_degradation_reconstruction import Z_MAX, damage_to_z  # noqa: E402


AMPLIFICATION_GRID = (
    0.125,
    0.25,
    0.5,
    1.0,
    2.0,
    4.0,
    8.0,
    16.0,
    32.0,
    64.0,
    128.0,
)
LENGTH_SCALE = 0.01


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-lock", type=Path, required=True)
    parser.add_argument("--prelock-dataset", type=Path, required=True)
    parser.add_argument("--prior-damage-vtk", type=Path, required=True)
    parser.add_argument("--sealed-c86-observation", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--youngs-modulus", type=float, default=1.0)
    parser.add_argument("--poisson-ratio", type=float, default=0.3)
    parser.add_argument("--max-equilibrium-iterations", type=int, default=50)
    parser.add_argument("--equilibrium-tolerance", type=float, default=1.0e-9)
    parser.add_argument("--equilibrium-residual-tolerance", type=float, default=1.0e-8)
    parser.add_argument("--minimum-pivot-ratio", type=float, default=1.0e-14)
    parser.add_argument("--bisection-iterations", type=int, default=10)
    parser.add_argument("--outside-policy", choices=("keep", "prior"), default="keep")
    parser.add_argument("--power", type=float, default=1.0)
    parser.add_argument("--allow-postlock-exploratory", action="store_true")
    args = parser.parse_args()
    if not args.allow_postlock_exploratory:
        parser.error("pass --allow-postlock-exploratory to acknowledge scope")
    if not 0.0 < args.power <= 1.0:
        parser.error("--power must lie in (0, 1]")
    return args


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    selection = json.loads(args.selection_lock.read_text(encoding="utf-8"))
    reconstruction_path = Path(selection["primary_reconstruction"])
    if not reconstruction_path.is_absolute():
        reconstruction_path = args.selection_lock.parent / reconstruction_path
    if sha256(reconstruction_path) != selection["primary_reconstruction_sha256"]:
        raise RuntimeError("selected reconstruction hash mismatch")

    reconstruction = np.load(reconstruction_path, allow_pickle=False)
    data = np.load(args.prelock_dataset, allow_pickle=False)
    connectivity = np.asarray(data["connectivity"], dtype=np.int32)
    areas = np.asarray(data["areas"], dtype=np.float64)
    centroids = np.asarray(data["centroids"], dtype=np.float64)
    prior_element_damage = np.asarray(data["sealed_c86_prior_damage"], dtype=float)
    prior_element_z = np.asarray(damage_to_z(prior_element_damage), dtype=float)
    predicted_element_z = np.asarray(reconstruction["element_z"], dtype=float)
    capacity = np.maximum(Z_MAX - prior_element_z, np.finfo(float).eps)
    predicted_fraction = np.clip(
        (predicted_element_z - prior_element_z) / capacity, 0.0, 1.0
    )

    prior_mesh = meshio.read(args.prior_damage_vtk)
    points = np.asarray(prior_mesh.points, dtype=float)[:, :2]
    prior_nodal_damage = np.clip(
        np.asarray(prior_mesh.point_data["d"], dtype=float).reshape(-1), 0.0, 1.0
    )
    if not np.array_equal(
        np.asarray(prior_mesh.cells_dict["quad"], dtype=np.int32), connectivity
    ):
        raise ValueError("prior VTK and prelock connectivity differ")

    sealed = np.load(args.sealed_c86_observation, allow_pickle=False)
    visible_nodal_core = np.asarray(sealed["core95"], dtype=bool)
    observed_reaction = float(np.asarray(sealed["peak_reaction"]).item())
    peak_displacement = float(np.asarray(sealed["peak_displacement"]).item())

    prior_core = prior_element_damage >= CORE_DAMAGE
    prior_tip_x = float(centroids[prior_core, 0].max())
    visible_element_core = visible_nodal_core[connectivity].all(axis=1)
    new_front = visible_element_core & (centroids[:, 0] > prior_tip_x)
    if not np.any(new_front):
        raise ValueError("sealed core does not extend beyond the c84 prior tip")
    front_y = float(np.median(centroids[new_front, 1]))
    front_mask = (centroids[:, 0] >= prior_tip_x - 4.0 * LENGTH_SCALE) & (
        np.abs(centroids[:, 1] - front_y) <= 6.0 * LENGTH_SCALE
    )
    nodal_front_mask = (points[:, 0] >= prior_tip_x - 4.0 * LENGTH_SCALE) & (
        np.abs(points[:, 1] - front_y) <= 6.0 * LENGTH_SCALE
    )

    kinematics = build_q4_kinematics(points, connectivity)

    def evaluate(amplification: float) -> tuple[dict[str, object], np.ndarray]:
        calibrated_fraction = (
            predicted_fraction.copy()
            if args.outside_policy == "keep"
            else np.zeros_like(predicted_fraction)
        )
        calibrated_fraction[front_mask] = np.clip(
            amplification * predicted_fraction[front_mask] ** args.power,
            0.0,
            1.0,
        )
        element_z = prior_element_z + capacity * calibrated_fraction
        nodal_damage = element_z_to_nodal_damage(
            element_z,
            connectivity,
            areas,
            prior_nodal_damage,
            visible_nodal_core,
        )
        if args.outside_policy == "prior":
            restore_prior = ~nodal_front_mask & ~visible_nodal_core
            nodal_damage[restore_prior] = prior_nodal_damage[restore_prior]
        result, reaction, wall = solve_candidate(
            kinematics, nodal_damage, peak_displacement, args
        )
        row = {
            "amplification": amplification,
            "predicted_reaction": reaction,
            "observed_reaction": observed_reaction,
            "relative_reaction_error": abs(reaction - observed_reaction)
            / abs(observed_reaction),
            "log_reaction_error": abs(
                np.log((abs(reaction) + 1.0e-15) / (abs(observed_reaction) + 1.0e-15))
            ),
            "iterations": result.iterations,
            "active_set_stable": result.active_set_stable,
            "normalized_residual": result.normalized_residual,
            "minimum_pivot_ratio": result.minimum_pivot_ratio,
            "wall_seconds": wall,
        }
        return row, nodal_damage

    rows: list[dict[str, object]] = []
    fields: dict[float, np.ndarray] = {}
    for amplification in AMPLIFICATION_GRID:
        row, damage = evaluate(amplification)
        rows.append(row)
        fields[amplification] = damage

    feasible = [
        row
        for row in rows
        if np.isfinite(float(row["predicted_reaction"]))
        and bool(row["active_set_stable"])
    ]
    bracket = None
    ordered = sorted(feasible, key=lambda row: float(row["amplification"]))
    for lower, upper in zip(ordered[:-1], ordered[1:]):
        lower_residual = float(lower["predicted_reaction"]) - observed_reaction
        upper_residual = float(upper["predicted_reaction"]) - observed_reaction
        if lower_residual * upper_residual <= 0.0:
            bracket = [float(lower["amplification"]), float(upper["amplification"])]
            break
    if bracket is not None:
        lower, upper = bracket
        for _ in range(args.bisection_iterations):
            middle = float(np.sqrt(lower * upper))
            row, damage = evaluate(middle)
            rows.append(row)
            fields[middle] = damage
            residual = float(row["predicted_reaction"]) - observed_reaction
            lower_row = min(
                rows,
                key=lambda item: abs(float(item["amplification"]) - lower),
            )
            lower_residual = float(lower_row["predicted_reaction"]) - observed_reaction
            if lower_residual * residual <= 0.0:
                upper = middle
            else:
                lower = middle

    best = min(
        rows,
        key=lambda row: (float(row["log_reaction_error"]), float(row["amplification"])),
    )
    best_amplification = float(best["amplification"])
    calibrated_damage = fields[best_amplification]
    curve_path = args.out / "reaction_amplification_curve.csv"
    write_rows(curve_path, sorted(rows, key=lambda row: float(row["amplification"])))
    field_path = args.out / "reaction_calibrated_c86_damage.npz"
    np.savez_compressed(
        field_path,
        nodal_damage=calibrated_damage,
        amplification=np.asarray(best_amplification),
        front_mask=front_mask.astype(np.uint8),
        nodal_front_mask=nodal_front_mask.astype(np.uint8),
        predicted_fraction=predicted_fraction,
        prior_element_damage=prior_element_damage,
    )
    lock = {
        "scope": "postlock_exploratory_reaction_only",
        "parameterization": (
            "tip-local scalar amplification of sealed GNN capacity fraction"
        ),
        "outside_policy": args.outside_policy,
        "power": args.power,
        "selection_input": "c86 peak reaction only",
        "postpeak_independence_note": (
            "postpeak reactions are displacement-scaled for fixed damage and are not "
            "an independent identification signal"
        ),
        "amplification_grid": list(AMPLIFICATION_GRID),
        "best_amplification": best_amplification,
        "best_reaction_error": float(best["relative_reaction_error"]),
        "front_mask_rule": "x>=c84_tip-4l and abs(y-new_visible_core_y)<=6l",
        "front_mask_element_count": int(front_mask.sum()),
        "source_selection_lock_sha256": sha256(args.selection_lock),
        "source_reconstruction_sha256": selection["primary_reconstruction_sha256"],
        "curve_sha256": sha256(curve_path),
        "field_sha256": sha256(field_path),
        "c86_diffuse_truth_used_for_selection": False,
        "c87_c89_fields_used_for_selection": False,
        "confirmatory_status": False,
    }
    (args.out / "REACTION_CALIBRATION_LOCK.json").write_text(
        json.dumps(lock, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(lock, indent=2))


if __name__ == "__main__":
    main()
