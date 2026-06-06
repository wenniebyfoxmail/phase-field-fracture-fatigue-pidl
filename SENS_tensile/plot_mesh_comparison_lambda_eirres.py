#!/usr/bin/env python3
"""Mesh comparison for FEM, strict PIDL baseline, and adaptive lambda_hist baseline."""
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
FEM_MESH = PROJECT_ROOT / "Alignment check" / "FEM preparation" / "nstep2" / "mesh_geometry.mat"
STRICT_PIDL_MESH = ROOT / "SENS_tensile" / "meshed_geom_fem_soft_hist0.msh"
LAMBDA_EIRRES_PIDL_MESH = ROOT / "SENS_tensile" / "meshed_geom2.msh"
OUT_DIR = ROOT / "_analysis_fem_mechanism_20260528" / "mesh_lambda_eirres_comparison_20260603"


@dataclass
class Mesh:
    name: str
    nodes: np.ndarray
    elements: np.ndarray
    element_type: str
    source_path: Path


def read_gmsh41(path: Path, name: str) -> Mesh:
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
                _entity_dim, _entity_tag, _parametric, n_block_nodes = map(int, lines[i].split())
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
                _entity_dim, _entity_tag, elem_type, n_block_elements = map(int, lines[i].split())
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
            if not elements:
                raise ValueError(f"No 2D triangle/quad elements found in {path}")
        else:
            i += 1

    node_array = np.empty((max(nodes), 2), dtype=float)
    for tag, xy in nodes.items():
        node_array[tag - 1] = xy
    return Mesh(name, node_array, np.asarray(elements, dtype=int) - 1, elem_type_name, path)


def read_fem_mat(path: Path) -> Mesh:
    mat = loadmat(path)
    nodes = np.asarray(mat["node_coords"], dtype=float)
    conn = np.asarray(mat["connectivity"], dtype=int)
    if conn.min() == 1:
        conn = conn - 1
    if nodes[:, 0].min() >= -1e-12 and nodes[:, 0].max() > 0.75:
        nodes = nodes.copy()
        nodes[:, 0] -= 0.5
    if nodes[:, 1].min() >= -1e-12 and nodes[:, 1].max() > 0.75:
        nodes = nodes.copy()
        nodes[:, 1] -= 0.5
    return Mesh("FEM nstep2 baseline", nodes, conn, "quad4", path)


def polygon_area(points: np.ndarray) -> np.ndarray:
    x = points[:, :, 0]
    y = points[:, :, 1]
    return 0.5 * np.abs(np.sum(x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1), axis=1))


def centroids(mesh: Mesh) -> np.ndarray:
    return mesh.nodes[mesh.elements].mean(axis=1)


def edge_segments(mesh: Mesh) -> np.ndarray:
    pts = mesh.nodes[mesh.elements]
    segs = []
    for k in range(pts.shape[1]):
        segs.append(np.stack([pts[:, k], pts[:, (k + 1) % pts.shape[1]]], axis=1))
    return np.concatenate(segs, axis=0)


def summarize(mesh: Mesh) -> dict[str, object]:
    areas = polygon_area(mesh.nodes[mesh.elements])
    return {
        "comparison": "mesh_stats",
        "mesh": mesh.name,
        "source_path": str(mesh.source_path),
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


def nearest_summary(reference: Mesh, target: Mesh, label: str) -> dict[str, object]:
    distances, _ = cKDTree(reference.nodes).query(target.nodes, k=1)
    return {
        "comparison": label,
        "mesh": f"{target.name} to {reference.name}",
        "source_path": "",
        "element_type": "nearest_node_distance",
        "n_nodes": int(len(target.nodes)),
        "n_elements": "",
        "x_min": "",
        "x_max": "",
        "y_min": "",
        "y_max": "",
        "total_area": "",
        "area_min": float(distances.min()),
        "area_mean": float(distances.mean()),
        "area_median": float(np.median(distances)),
        "area_max": float(distances.max()),
    }


def centroid_summary(reference: Mesh, target: Mesh, label: str) -> dict[str, object]:
    distances, _ = cKDTree(centroids(reference)).query(centroids(target), k=1)
    return {
        "comparison": label,
        "mesh": f"{target.name} to {reference.name}",
        "source_path": "",
        "element_type": "nearest_centroid_distance",
        "n_nodes": "",
        "n_elements": int(len(target.elements)),
        "x_min": "",
        "x_max": "",
        "y_min": "",
        "y_max": "",
        "total_area": "",
        "area_min": float(distances.min()),
        "area_mean": float(distances.mean()),
        "area_median": float(np.median(distances)),
        "area_max": float(distances.max()),
    }


def plot_meshes(meshes: list[Mesh]) -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 3, figsize=(14.8, 8.2), constrained_layout=True)
    for col, mesh in enumerate(meshes):
        for row, crop in enumerate([None, 0.08]):
            ax = axes[row, col]
            segs = edge_segments(mesh)
            lc = LineCollection(
                segs,
                colors="0.12",
                linewidths=0.025 if crop is None else 0.13,
                alpha=0.35 if crop is None else 0.75,
            )
            ax.add_collection(lc)
            ax.set_aspect("equal", adjustable="box")
            ax.axhline(0, color="#0072B2", lw=0.45, alpha=0.75)
            ax.axvline(0, color="#D55E00", lw=0.45, alpha=0.75)
            if crop is None:
                ax.set_xlim(-0.52, 0.52)
                ax.set_ylim(-0.52, 0.52)
                view = "full domain"
            else:
                ax.set_xlim(-crop, crop)
                ax.set_ylim(-crop, crop)
                view = "near-tip crop"
            ax.set_title(f"{mesh.name}\n{mesh.element_type}, {view}", fontsize=9)
            ax.set_xlabel("x")
            ax.set_ylabel("y")
    fig.suptitle("Mesh comparison: FEM baseline, strict PIDL baseline, and adaptive lambda/E_irres PIDL baseline", fontsize=12)
    png = OUT_DIR / "fem_strict_pidl_lambda_eirres_mesh_comparison.png"
    pdf = OUT_DIR / "fem_strict_pidl_lambda_eirres_mesh_comparison.pdf"
    fig.savefig(png, dpi=300)
    fig.savefig(pdf)
    plt.close(fig)
    return png, pdf


def plot_node_overlay(meshes: list[Mesh]) -> Path:
    colors = ["#0072B2", "#D55E00", "#009E73"]
    sizes = [1.8, 0.26, 0.26]
    fig, ax = plt.subplots(figsize=(7.4, 7.4), constrained_layout=True)
    for mesh, color, size in zip(meshes, colors, sizes):
        ax.scatter(mesh.nodes[:, 0], mesh.nodes[:, 1], s=size, c=color, alpha=0.42, label=mesh.name)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-0.52, 0.52)
    ax.set_ylim(-0.52, 0.52)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title("Node overlay for mesh provenance check")
    ax.legend(markerscale=8, frameon=False, loc="upper right")
    path = OUT_DIR / "fem_strict_pidl_lambda_eirres_node_overlay.png"
    fig.savefig(path, dpi=300)
    plt.close(fig)
    return path


def main() -> None:
    fem = read_fem_mat(FEM_MESH)
    strict = read_gmsh41(STRICT_PIDL_MESH, "PIDL strict FEM-mesh baseline")
    lam = read_gmsh41(LAMBDA_EIRRES_PIDL_MESH, "PIDL adaptive lambda/E_irres baseline")
    meshes = [fem, strict, lam]

    rows: list[dict[str, object]] = [summarize(mesh) for mesh in meshes]
    for mesh in [strict, lam]:
        rows.append(nearest_summary(fem, mesh, "nearest_node_to_FEM"))
        rows.append(centroid_summary(fem, mesh, "nearest_centroid_to_FEM"))
    rows.append(nearest_summary(strict, lam, "lambda_mesh_nearest_node_to_strict_PIDL"))
    rows.append(centroid_summary(strict, lam, "lambda_mesh_nearest_centroid_to_strict_PIDL"))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv = OUT_DIR / "fem_strict_pidl_lambda_eirres_mesh_comparison.csv"
    pd.DataFrame(rows).to_csv(csv, index=False)
    png, pdf = plot_meshes(meshes)
    overlay = plot_node_overlay(meshes)
    readme = OUT_DIR / "README.md"
    readme.write_text(
        "# Mesh Comparison: FEM, Strict PIDL, Adaptive Lambda/E_irres PIDL\n\n"
        "Adaptive lambda/E_irres baseline source is documented as baseline geometry "
        "(`baseline mesh/sampling plus adaptive lambda_hist`), so this audit uses "
        "`SENS_tensile/meshed_geom2.msh` for that run.\n\n"
        f"- FEM mesh: `{FEM_MESH}`\n"
        f"- Strict PIDL FEM-mesh baseline: `{STRICT_PIDL_MESH}`\n"
        f"- Adaptive lambda/E_irres PIDL baseline: `{LAMBDA_EIRRES_PIDL_MESH}`\n"
        f"- Figure PNG: `{png.name}`\n"
        f"- Figure PDF: `{pdf.name}`\n"
        f"- Node overlay: `{overlay.name}`\n"
        f"- Comparison CSV: `{csv.name}`\n",
        encoding="utf-8",
    )
    print(f"CSV: {csv}")
    print(f"PNG: {png}")
    print(f"PDF: {pdf}")
    print(f"Overlay: {overlay}")


if __name__ == "__main__":
    main()
