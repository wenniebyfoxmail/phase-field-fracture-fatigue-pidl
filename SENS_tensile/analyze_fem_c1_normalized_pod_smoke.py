#!/usr/bin/env python3
"""Area-weighted normalized-displacement POD smoke for three FEM c1/s4 fields.

The smoke intentionally omits elastic-baseline subtraction because no matched
healthy peak field is present.  With three centered snapshots, rank two is an
algebraic ceiling rather than evidence for a two-coordinate forecast state.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import meshio
import numpy as np


def parse_case(text: str) -> tuple[str, float, Path]:
    label, umax, path = text.split(":", 2)
    return label, float(umax), Path(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", required=True, type=parse_case)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def nodal_lumped_areas(xy: np.ndarray, quads: np.ndarray) -> np.ndarray:
    pts = xy[quads]
    x = pts[:, :, 0]
    y = pts[:, :, 1]
    areas = 0.5 * np.abs(
        np.sum(x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1), axis=1)
    )
    weights = np.zeros(xy.shape[0], dtype=np.float64)
    np.add.at(weights, quads.reshape(-1), np.repeat(areas / 4.0, 4))
    if np.any(weights <= 0.0) or not np.all(np.isfinite(weights)):
        raise ValueError("invalid lumped nodal weights")
    return weights


def relative_weighted_l2(a: np.ndarray, b: np.ndarray, weights: np.ndarray) -> float:
    diff2 = np.sum((a - b) ** 2, axis=1)
    ref2 = np.sum(b ** 2, axis=1)
    return float(np.sqrt(np.sum(weights * diff2) / max(np.sum(weights * ref2), 1.0e-30)))


def main() -> None:
    args = parse_args()
    if len(args.case) != 3:
        raise ValueError("this preregistered smoke requires exactly three c1/s4 cases")
    args.out.mkdir(parents=True, exist_ok=True)
    tables = args.out / "tables"
    tables.mkdir(exist_ok=True)

    labels: list[str] = []
    normalized: list[np.ndarray] = []
    sources: list[dict[str, object]] = []
    reference_xy = None
    reference_quads = None
    weights = None
    for label, umax, path in args.case:
        mesh = meshio.read(path)
        xy = np.asarray(mesh.points[:, :2], dtype=np.float64)
        quads = np.asarray(mesh.cells_dict["quad"], dtype=np.int64)
        displacement = np.asarray(mesh.point_data["u"][:, :2], dtype=np.float64)
        if reference_xy is None:
            reference_xy = xy
            reference_quads = quads
            weights = nodal_lumped_areas(xy, quads)
        elif not np.array_equal(xy, reference_xy) or not np.array_equal(quads, reference_quads):
            raise ValueError(f"mesh mismatch for {label}")
        labels.append(label)
        normalized.append(displacement / umax)
        sources.append({"label": label, "umax": umax, "vtk": str(path.resolve())})

    assert weights is not None
    pairwise = []
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            pairwise.append({
                "case_a": labels[i],
                "case_b": labels[j],
                "quantity": "u_c1_s4_divided_by_umax",
                "relative_area_weighted_l2_a_minus_b_over_b": relative_weighted_l2(
                    normalized[i], normalized[j], weights
                ),
            })
    with (tables / "normalized_pairwise_distance.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(pairwise[0]))
        writer.writeheader()
        writer.writerows(pairwise)

    snapshots = np.stack([field.reshape(-1) for field in normalized], axis=0)
    centered = snapshots - snapshots.mean(axis=0, keepdims=True)
    dof_weights = np.repeat(weights, 2)
    weighted = centered * np.sqrt(dof_weights)[None, :]
    left, singular, right_t = np.linalg.svd(weighted, full_matrices=False)
    energy = singular ** 2
    energy_fraction = energy / max(float(np.sum(energy)), 1.0e-30)
    rows = []
    for index, (value, fraction) in enumerate(zip(singular, energy_fraction), start=1):
        rows.append({
            "mode": index,
            "singular_value": float(value),
            "centered_energy_fraction": float(fraction),
            "cumulative_energy_fraction": float(np.sum(energy_fraction[:index])),
        })
    with (tables / "pod_singular_values.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "claim_class": "tooling_only_normalized_c1_pod_smoke",
        "state": "FEM_c1_s4_peak_same_state",
        "sources": sources,
        "mesh_identical": True,
        "area_weighting": "Q4 area lumped equally to four nodes and repeated for ux,uy",
        "normalization": "u_node / Umax",
        "elastic_baseline_subtracted": False,
        "forecast_target_available": False,
        "rank_two_interpretation": "tautological ceiling after centering exactly three snapshots",
    }
    (args.out / "comparison_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    decision = f"""# Decision — FEM c1 normalized-displacement POD smoke

Verdict: **tooling pass; scientific gate blocked by missing trajectory peak states**.

Purpose: verify common mesh, Umax normalization, area weighting and SVD/POD plumbing before Request 28 trajectory states arrive.

Available data: only the three canonical `c1/s4` peak VTK files for U0.11, U0.12 and U0.13. A matched healthy elastic peak field was not supplied, so this smoke divides by Umax but does not perform the preregistered elastic-baseline subtraction.

Result:

- normalized pairwise relative area-weighted L2 distances are `{pairwise[0]['relative_area_weighted_l2_a_minus_b_over_b']:.6f}`, `{pairwise[1]['relative_area_weighted_l2_a_minus_b_over_b']:.6f}`, and `{pairwise[2]['relative_area_weighted_l2_a_minus_b_over_b']:.6f}`;
- POD mode 1 contains `{energy_fraction[0]:.6f}` of centered weighted energy;
- POD mode 2 brings the cumulative fraction to `{np.sum(energy_fraction[:2]):.6f}`.

Interpretation: rank two reconstructing these centered data is guaranteed because there are only three snapshots. It is not evidence that two coordinates are sufficient for early first-detect prediction. The smoke validates the calculation path only.

Required next data: same-state FEM s4 peak displacement across multiple early forecast origins on each trajectory, plus a declared healthy elastic reference or a separately frozen elastic-fit rule. Request 28's current shared smoke contains only U0.13 c1/s4 and c1/s5; the full three replays have not yet been uploaded.

Next action: wait for the authorized Request 28 P0+P1 replays, then fit POD modes using training trajectories only and evaluate rank-1/rank-2 reconstruction and first-detect RUL on a whole held-out trajectory.
"""
    (args.out / "decision.md").write_text(decision, encoding="utf-8")


if __name__ == "__main__":
    main()
