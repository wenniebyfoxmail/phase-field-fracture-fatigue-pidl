#!/usr/bin/env python3
"""Plot soft-hist0 FEM vs PIDL residual fields on common PIDL probes.

Each figure uses the same PIDL element probes for FEM and PIDL:

    column 1: FEM fields projected to PIDL triangles
    column 2: PIDL fields on the same triangles
    column 3: raw residual, PIDL - FEM

The residual is only meaningful because the FEM coordinates are shifted into
PIDL's centred frame and projected to the same PIDL element probes.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from posthoc_mesh_probe_alignment import (  # noqa: E402
    build_assignment,
    load_combined_handoff,
    load_fem_snapshot,
    pidl_model_and_mesh,
    project_to_pidl,
)
from pidl_fem_alignment_protocol import (  # noqa: E402
    FEM_SOFT_HIST0_FIELDS,
    PIDL_FEMMESH_ARCHIVE,
    PIDL_FEMMESH_MESH,
    PIDL_SAVED_INDEX_OFFSET_FOR_FEM_CYCLE,
)

DEFAULT_FEM_MAT = FEM_SOFT_HIST0_FIELDS

FIELD_SPECS = {
    "damage_alpha": {
        "label": "damage",
        "fem": lambda fem: np.asarray(fem["d_elem"], dtype=float).reshape(-1),
        "pidl": lambda pidl: pidl["alpha"],
        "cmap": "viridis",
    },
    "alpha_bar": {
        "label": "fatigue history",
        "fem": lambda fem: np.asarray(fem["alpha_bar_elem"], dtype=float).reshape(-1),
        "pidl": lambda pidl: pidl["alpha_bar"],
        "cmap": "magma",
    },
    "fatigue_f": {
        "label": "fatigue factor f",
        "fem": lambda fem: np.asarray(fem["f_alpha_elem"], dtype=float).reshape(-1),
        "pidl": lambda pidl: pidl["f"],
        "cmap": "viridis",
    },
    "psi_plus_active": {
        "label": "active tensile driver",
        "fem": lambda fem: ((1.0 - np.asarray(fem["d_elem"], dtype=float).reshape(-1)) ** 2 + 1e-6)
        * np.asarray(fem["psi_elem"], dtype=float).reshape(-1),
        "pidl": lambda pidl: pidl["psi_plus_active"],
        "cmap": "magma",
    },
}


def robust_limits(*arrays: np.ndarray, q: float = 99.5) -> tuple[float, float]:
    values = np.concatenate([np.asarray(a)[np.isfinite(a)].reshape(-1) for a in arrays])
    if values.size == 0:
        return 0.0, 1.0
    lo, hi = np.nanpercentile(values, [100.0 - q, q])
    if np.isclose(lo, hi):
        hi = lo + 1.0
    return float(lo), float(hi)


def signed_limit(values: np.ndarray, q: float = 99.0) -> float:
    finite = np.abs(values[np.isfinite(values)])
    if finite.size == 0:
        return 1.0
    return max(float(np.nanpercentile(finite, q)), 1e-12)


def fill_nan_from_nearest(values: np.ndarray, centroids: np.ndarray) -> np.ndarray:
    """Fill visual-only projection gaps from nearest valid projected value."""
    out = np.asarray(values, dtype=float).copy()
    valid = np.isfinite(out)
    if valid.all() or not valid.any():
        return out
    tree = cKDTree(centroids[valid])
    _, idx = tree.query(centroids[~valid], k=1)
    out[~valid] = out[valid][idx]
    return out


def plot_field(field: str, rows: list[dict], triang: mtri.Triangulation, out_dir: Path, prefix: str) -> None:
    spec = FIELD_SPECS[field]
    n = len(rows)
    fig, axes = plt.subplots(n, 3, figsize=(10.8, 2.65 * n), constrained_layout=True)
    if n == 1:
        axes = np.asarray([axes])

    for row_i, row in enumerate(rows):
        fem = row[f"{field}_fem_plot"]
        pidl = row[f"{field}_pidl"]
        residual = pidl - fem
        vmin, vmax = robust_limits(fem, pidl, q=99.5)
        rlim = signed_limit(residual, q=99.0)

        panels = [
            (f"FEM c{row['cycle']}", fem, spec["cmap"], vmin, vmax),
            (f"PIDL j{row['pidl_saved_index']}", pidl, spec["cmap"], vmin, vmax),
            (f"PIDL j{row['pidl_saved_index']} - FEM c{row['cycle']}", residual, "RdBu_r", -rlim, rlim),
        ]
        for ax, (title, values, cmap, lo, hi) in zip(axes[row_i], panels):
            im = ax.tripcolor(triang, facecolors=values, shading="flat", cmap=cmap, vmin=lo, vmax=hi)
            ax.set_title(title, fontsize=9)
            ax.set_aspect("equal")
            ax.set_xlim(-0.52, 0.52)
            ax.set_ylim(-0.52, 0.52)
            ax.set_xticks([])
            ax.set_yticks([])
            fig.colorbar(im, ax=ax, fraction=0.044, pad=0.015)

    fig.suptitle(f"Soft-hist0 FEM vs PIDL common-probe residual: {spec['label']}", fontsize=12)
    out_png = out_dir / f"{prefix}_{field}.png"
    fig.savefig(out_png, dpi=220)
    plt.close(fig)


def summarize_field(values: np.ndarray, areas: np.ndarray) -> dict[str, float]:
    finite = values[np.isfinite(values)]
    return {
        "mean": float(np.nanmean(finite)),
        "abs_mean": float(np.nanmean(np.abs(finite))),
        "abs_p99": float(np.nanpercentile(np.abs(finite), 99.0)),
        "abs_p999": float(np.nanpercentile(np.abs(finite), 99.9)),
        "integral": float(np.nansum(values * areas)),
        "abs_integral": float(np.nansum(np.abs(values) * areas)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=PIDL_FEMMESH_ARCHIVE)
    parser.add_argument("--fem-mat", type=Path, default=DEFAULT_FEM_MAT)
    parser.add_argument("--cycles", default="1,40,69")
    parser.add_argument("--pidl-cycle-offset", type=int, default=PIDL_SAVED_INDEX_OFFSET_FOR_FEM_CYCLE)
    parser.add_argument("--pidl-mesh", type=Path, default=PIDL_FEMMESH_MESH)
    parser.add_argument("--prefix", default="femmesh_j0map_common_probe_residual")
    parser.add_argument("--out-dir", type=Path, default=HERE.parent / "_analysis_fem_mechanism_20260528/figures")
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=HERE.parent / "_analysis_fem_mechanism_20260528/femmesh_j0map_common_probe_residual_summary.csv",
    )
    args = parser.parse_args()

    cycles = [int(x) for x in args.cycles.split(",") if x.strip()]
    combined = load_combined_handoff(args.fem_mat)
    fem_centroids = combined["centroids"].copy()
    fem_centroids[:, :2] -= 0.5
    first_pidl_cycle = cycles[0] + args.pidl_cycle_offset
    if first_pidl_cycle < 0:
        raise ValueError(f"PIDL checkpoint index would be negative for FEM cycle {cycles[0]}")
    first = pidl_model_and_mesh(args.archive, 0.12, first_pidl_cycle, str(args.pidl_mesh))
    assignment = build_assignment(fem_centroids, first["centroids"], first["inp"], first["conn"])
    triang = mtri.Triangulation(first["inp"][:, 0], first["inp"][:, 1], first["conn"])

    rows_for_plot = []
    summary_rows = []
    for cycle in cycles:
        fem = load_fem_snapshot(cycle, 0.12, combined)
        pidl_cycle = cycle + args.pidl_cycle_offset
        if pidl_cycle < 0:
            raise ValueError(f"PIDL checkpoint index would be negative for FEM cycle {cycle}")
        pidl = first if pidl_cycle == first_pidl_cycle else pidl_model_and_mesh(
            args.archive, 0.12, pidl_cycle, str(args.pidl_mesh)
        )
        row = {"cycle": cycle, "pidl_saved_index": pidl_cycle}
        for field, spec in FIELD_SPECS.items():
            fem_native = spec["fem"](fem)
            pidl_native = spec["pidl"](pidl)
            fem_proj = project_to_pidl(fem_native, combined["areas"], assignment, len(pidl_native))
            row[f"{field}_fem"] = fem_proj
            row[f"{field}_fem_plot"] = fill_nan_from_nearest(fem_proj, pidl["centroids"])
            row[f"{field}_pidl"] = pidl_native
            residual = pidl_native - fem_proj
            summary = summarize_field(residual, pidl["areas"])
            summary_rows.append({
                "cycle": cycle,
                "fem_cycle": cycle,
                "pidl_saved_index": pidl_cycle,
                "pidl_cycle_offset": args.pidl_cycle_offset,
                "field": field,
                **summary,
            })
        rows_for_plot.append(row)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for field in FIELD_SPECS:
        plot_field(field, rows_for_plot, triang, args.out_dir, args.prefix)

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summary_rows).to_csv(args.out_csv, index=False)
    print(f"saved figures in {args.out_dir}")
    print(f"saved {args.out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
