#!/usr/bin/env python3
"""Plot and compare the strict PIDL baseline mesh against the FEM baseline mesh."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np
import pandas as pd
from scipy.io import loadmat
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
PIDL_MESH = ROOT / "SENS_tensile" / "meshed_geom_fem_soft_hist0.msh"
FEM_MESH = (
    PROJECT_ROOT
    / "Alignment check"
    / "FEM preparation"
    / "nstep2"
    / "mesh_geometry.mat"
)
OUT_DIR = ROOT / "_analysis_fem_mechanism_20260528" / "mesh_baseline_comparison_20260603"


@dataclass
class Mesh:
    name: str
    nodes: np.ndarray
    elements: np.ndarray
    element_type: str


def read_gmsh41(path: Path) -> Mesh:
    lines = path.read_text().splitlines()
    i = 0
    nodes: dict[int, tuple[float, float]] = {}
    elements: list[list[int]] = []
    elem_type_name = "mixed"

    while i < len(lines):
        token = lines[i].strip()
        if token == "$Nodes":
            i += 1
            n_blocks, n_nodes, *_ = map(int, lines[i].split())
            i += 1
            for _ in range(n_blocks):
                entity_dim, entity_tag, parametric, n_block_nodes = map(int, lines[i].split())
                i += 1
                tags = [int(lines[i + j].strip()) for j in range(n_block_nodes)]
                i += n_block_nodes
                for tag in tags:
                    vals = list(map(float, lines[i].split()))
                    nodes[tag] = (vals[0], vals[1])
                    i += 1
            assert len(nodes) == n_nodes
        elif token == "$Elements":
            i += 1
            n_blocks, n_elements, *_ = map(int, lines[i].split())
            i += 1
            for _ in range(n_blocks):
                entity_dim, entity_tag, elem_type, n_block_elements = map(int, lines[i].split())
                i += 1
                if elem_type == 2:
                    elem_type_name = "tri3"
                    nodes_per_elem = 3
                elif elem_type == 3:
                    elem_type_name = "quad4"
                    nodes_per_elem = 4
                else:
                    nodes_per_elem = None
                for _ in range(n_block_elements):
                    parts = list(map(int, lines[i].split()))
                    if nodes_per_elem is not None:
                        elements.append(parts[1 : 1 + nodes_per_elem])
                    i += 1
            assert len(elements) == n_elements
        else:
            i += 1

    max_tag = max(nodes)
    node_array = np.empty((max_tag, 2), dtype=float)
    for tag, xy in nodes.items():
        node_array[tag - 1] = xy
    return Mesh("PIDL strict baseline", node_array, np.asarray(elements, dtype=int) - 1, elem_type_name)


def read_fem_mat(path: Path) -> Mesh:
    mat = loadmat(path)
    nodes = np.asarray(mat["node_coords"], dtype=float)
    conn = np.asarray(mat["connectivity"], dtype=int)
    if conn.min() == 1:
        conn = conn - 1
    if float(np.nanmax(nodes[:, 0])) > 0.75 and float(np.nanmin(nodes[:, 0])) >= -1e-12:
        nodes = nodes.copy()
        nodes[:, 0] -= 0.5
    if float(np.nanmax(nodes[:, 1])) > 0.75 and float(np.nanmin(nodes[:, 1])) >= -1e-12:
        nodes = nodes.copy()
        nodes[:, 1] -= 0.5
    return Mesh("FEM nstep2 baseline", nodes, conn, "quad4")


def polygon_area(points: np.ndarray) -> np.ndarray:
    x = points[:, :, 0]
    y = points[:, :, 1]
    return 0.5 * np.abs(np.sum(x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1), axis=1))


def edge_segments(mesh: Mesh, max_edges: int | None = None) -> np.ndarray:
    elems = mesh.elements
    if max_edges and len(elems) > max_edges:
        idx = np.linspace(0, len(elems) - 1, max_edges).astype(int)
        elems = elems[idx]
    pts = mesh.nodes[elems]
    segs = []
    for k in range(pts.shape[1]):
        segs.append(np.stack([pts[:, k], pts[:, (k + 1) % pts.shape[1]]], axis=1))
    return np.concatenate(segs, axis=0)


def summarize(mesh: Mesh) -> dict[str, float | int | str]:
    pts = mesh.nodes[mesh.elements]
    areas = polygon_area(pts)
    return {
        "mesh": mesh.name,
        "element_type": mesh.element_type,
        "n_nodes": int(len(mesh.nodes)),
        "n_elements": int(len(mesh.elements)),
        "x_min": float(mesh.nodes[:, 0].min()),
        "x_max": float(mesh.nodes[:, 0].max()),
        "y_min": float(mesh.nodes[:, 1].min()),
        "y_max": float(mesh.nodes[:, 1].max()),
        "total_area": float(areas.sum()),
        "area_min": float(areas.min()),
        "area_mean": float(areas.mean()),
        "area_median": float(np.median(areas)),
        "area_max": float(areas.max()),
    }


def comparison_rows(pidl: Mesh, fem: Mesh) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    rows.append(summarize(pidl))
    rows.append(summarize(fem))

    pidl_tree = cKDTree(pidl.nodes)
    fem_to_pidl, _ = pidl_tree.query(fem.nodes, k=1)
    fem_tree = cKDTree(fem.nodes)
    pidl_to_fem, _ = fem_tree.query(pidl.nodes, k=1)

    pidl_centroids = pidl.nodes[pidl.elements].mean(axis=1)
    fem_centroids = fem.nodes[fem.elements].mean(axis=1)
    tri_to_quad_dist, _ = cKDTree(fem_centroids).query(pidl_centroids, k=1)
    quad_to_tri_dist, _ = cKDTree(pidl_centroids).query(fem_centroids, k=1)

    rows.append(
        {
            "mesh": "nearest-node FEM_to_PIDL",
            "element_type": "diagnostic",
            "n_nodes": len(fem.nodes),
            "n_elements": "",
            "x_min": "",
            "x_max": "",
            "y_min": "",
            "y_max": "",
            "total_area": "",
            "area_min": float(fem_to_pidl.min()),
            "area_mean": float(fem_to_pidl.mean()),
            "area_median": float(np.median(fem_to_pidl)),
            "area_max": float(fem_to_pidl.max()),
        }
    )
    rows.append(
        {
            "mesh": "nearest-node PIDL_to_FEM",
            "element_type": "diagnostic",
            "n_nodes": len(pidl.nodes),
            "n_elements": "",
            "x_min": "",
            "x_max": "",
            "y_min": "",
            "y_max": "",
            "total_area": "",
            "area_min": float(pidl_to_fem.min()),
            "area_mean": float(pidl_to_fem.mean()),
            "area_median": float(np.median(pidl_to_fem)),
            "area_max": float(pidl_to_fem.max()),
        }
    )
    rows.append(
        {
            "mesh": "nearest-centroid PIDL_tri_to_FEM_quad",
            "element_type": "diagnostic",
            "n_nodes": "",
            "n_elements": "",
            "x_min": "",
            "x_max": "",
            "y_min": "",
            "y_max": "",
            "total_area": "",
            "area_min": float(tri_to_quad_dist.min()),
            "area_mean": float(tri_to_quad_dist.mean()),
            "area_median": float(np.median(tri_to_quad_dist)),
            "area_max": float(tri_to_quad_dist.max()),
        }
    )
    rows.append(
        {
            "mesh": "nearest-centroid FEM_quad_to_PIDL_tri",
            "element_type": "diagnostic",
            "n_nodes": "",
            "n_elements": "",
            "x_min": "",
            "x_max": "",
            "y_min": "",
            "y_max": "",
            "total_area": "",
            "area_min": float(quad_to_tri_dist.min()),
            "area_mean": float(quad_to_tri_dist.mean()),
            "area_median": float(np.median(quad_to_tri_dist)),
            "area_max": float(quad_to_tri_dist.max()),
        }
    )
    return rows


def plot_meshes(pidl: Mesh, fem: Mesh) -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.0), constrained_layout=True)
    panels = [
        (axes[0, 0], fem, "FEM baseline mesh: quads, full domain", None),
        (axes[0, 1], pidl, "PIDL strict baseline mesh: triangles, full domain", None),
        (axes[1, 0], fem, "FEM near-tip crop", 0.08),
        (axes[1, 1], pidl, "PIDL near-tip crop", 0.08),
    ]
    for ax, mesh, title, crop in panels:
        segs = edge_segments(mesh)
        lc = LineCollection(segs, colors="0.15", linewidths=0.15 if crop else 0.025, alpha=0.55 if crop else 0.35)
        ax.add_collection(lc)
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(title, fontsize=10)
        if crop:
            ax.set_xlim(-crop, crop)
            ax.set_ylim(-crop, crop)
        else:
            ax.set_xlim(-0.52, 0.52)
            ax.set_ylim(-0.52, 0.52)
        ax.axhline(0, color="#0072B2", lw=0.6, alpha=0.7)
        ax.axvline(0, color="#D55E00", lw=0.6, alpha=0.7)
        ax.set_xlabel("x")
        ax.set_ylabel("y")

    png = OUT_DIR / "pidl_strict_baseline_vs_fem_nstep2_mesh.png"
    pdf = OUT_DIR / "pidl_strict_baseline_vs_fem_nstep2_mesh.pdf"
    fig.suptitle("Mesh used for strict PIDL baseline and updated FEM nstep2 baseline", fontsize=12)
    fig.savefig(png, dpi=300)
    fig.savefig(pdf)
    plt.close(fig)
    return png, pdf


def plot_node_overlay(pidl: Mesh, fem: Mesh) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.0, 7.0), constrained_layout=True)
    ax.scatter(fem.nodes[:, 0], fem.nodes[:, 1], s=0.35, c="#0072B2", alpha=0.5, label="FEM nodes")
    ax.scatter(pidl.nodes[:, 0], pidl.nodes[:, 1], s=0.08, c="#D55E00", alpha=0.35, label="PIDL nodes")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-0.52, 0.52)
    ax.set_ylim(-0.52, 0.52)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title("Node overlay: FEM baseline vs PIDL strict baseline")
    ax.legend(markerscale=8, frameon=False, loc="upper right")
    path = OUT_DIR / "pidl_strict_baseline_vs_fem_nstep2_node_overlay.png"
    fig.savefig(path, dpi=300)
    plt.close(fig)
    return path


def main() -> None:
    pidl = read_gmsh41(PIDL_MESH)
    fem = read_fem_mat(FEM_MESH)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = comparison_rows(pidl, fem)
    csv_path = OUT_DIR / "pidl_strict_baseline_vs_fem_nstep2_mesh_comparison.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    png, pdf = plot_meshes(pidl, fem)
    overlay = plot_node_overlay(pidl, fem)
    print(f"CSV: {csv_path}")
    print(f"PNG: {png}")
    print(f"PDF: {pdf}")
    print(f"Overlay: {overlay}")


if __name__ == "__main__":
    main()
