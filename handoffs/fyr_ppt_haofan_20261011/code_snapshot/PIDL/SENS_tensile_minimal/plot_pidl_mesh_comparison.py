#!/usr/bin/env python3
"""Plot old PIDL geom mesh against the FEM-derived soft-hist0 PIDL mesh."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from utils import parse_mesh  # noqa: E402


DEFAULT_OUT = HERE.parent / "_analysis_fem_mechanism_20260528" / "figures" / "pidl_mesh_geom2_vs_fem_soft_hist0.png"


def load_mesh(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    x, y, conn, area = parse_mesh(str(path), gradient_type="numerical")
    nodes = np.column_stack([x, y])
    centroids = nodes[conn].mean(axis=1)
    return nodes, conn, np.abs(area), centroids


def summarize(name: str, path: Path) -> dict[str, float | str]:
    nodes, conn, area, centroids = load_mesh(path)
    r_tip = np.sqrt(centroids[:, 0] ** 2 + centroids[:, 1] ** 2)
    near = r_tip <= 0.04
    crack_strip = (centroids[:, 0] <= 0.0) & (np.abs(centroids[:, 1]) <= 0.02)
    return {
        "mesh": name,
        "path": str(path),
        "n_nodes": int(len(nodes)),
        "n_triangles": int(len(conn)),
        "area_min": float(np.min(area)),
        "area_median": float(np.median(area)),
        "area_p99": float(np.percentile(area, 99.0)),
        "n_tip_r4l0": int(np.sum(near)),
        "n_precrack_strip": int(np.sum(crack_strip)),
    }


def plot_mesh(ax, nodes: np.ndarray, conn: np.ndarray, area: np.ndarray, title: str) -> None:
    tri = mtri.Triangulation(nodes[:, 0], nodes[:, 1], conn)
    log_area = np.log10(np.maximum(area, 1e-16))
    ax.tripcolor(tri, facecolors=log_area, shading="flat", cmap="viridis")
    ax.triplot(tri, color="k", lw=0.08, alpha=0.18)
    ax.set_aspect("equal")
    ax.set_xlim(-0.52, 0.52)
    ax.set_ylim(-0.52, 0.52)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("x")
    ax.set_ylabel("y")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-mesh", type=Path, default=HERE / "meshed_geom2.msh")
    parser.add_argument("--fem-mesh", type=Path, default=HERE / "meshed_geom_fem_soft_hist0.msh")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    old_nodes, old_conn, old_area, _ = load_mesh(args.old_mesh)
    fem_nodes, fem_conn, fem_area, _ = load_mesh(args.fem_mesh)

    fig, axes = plt.subplots(1, 2, figsize=(11.2, 5.0), constrained_layout=True)
    plot_mesh(axes[0], old_nodes, old_conn, old_area, f"old PIDL geom2\n{len(old_conn):,} triangles")
    plot_mesh(axes[1], fem_nodes, fem_conn, fem_area, f"FEM-derived soft-hist0\n{len(fem_conn):,} triangles")
    fig.suptitle("PIDL mesh comparison: old geom.msh vs FEM-derived soft-hist0 mesh")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=260)
    plt.close(fig)

    import csv

    csv_path = args.out.with_suffix(".csv")
    rows = [
        summarize("old_geom2", args.old_mesh),
        summarize("fem_soft_hist0", args.fem_mesh),
    ]
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {args.out}")
    print(f"Wrote {csv_path}")
    for row in rows:
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
