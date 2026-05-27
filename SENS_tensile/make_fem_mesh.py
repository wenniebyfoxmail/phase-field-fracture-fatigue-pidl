#!/usr/bin/env python3
"""Convert a GRIPHFiTH FEM mesh_geometry.mat into a PIDL triangular .msh.

PIDL's current numerical-gradient path expects a Gmsh triangular mesh.  The
GRIPHFiTH SENT reference mesh is stored as quadrilateral connectivity in
mesh_geometry.mat, so this script splits every quad into two triangles and
writes a lightweight Gmsh 4.1 ASCII file compatible with the project's
gmshparser dependency.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import scipy.io as sio


HERE = Path(__file__).resolve().parent
DEFAULT_MESH_MAT = (
    Path.home() / "Downloads" / "_pidl_handoff_v2"
    / "psi_snapshots_for_agent" / "mesh_geometry.mat"
)


def _tri_area(nodes: np.ndarray, tri: np.ndarray) -> np.ndarray:
    a = nodes[tri[:, 0]]
    b = nodes[tri[:, 1]]
    c = nodes[tri[:, 2]]
    return 0.5 * (
        (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1])
        - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1])
    )


def load_and_split(mesh_mat: Path, diagonal: str) -> tuple[np.ndarray, np.ndarray]:
    data = sio.loadmat(str(mesh_mat))
    nodes = np.asarray(data["node_coords"], dtype=np.float64)
    conn = np.asarray(data["connectivity"], dtype=np.int64)
    if conn.min() == 1:
        conn = conn - 1

    if conn.shape[1] == 3:
        tri = conn.copy()
    elif conn.shape[1] == 4:
        if diagonal == "13":
            tri = np.vstack((conn[:, [0, 1, 2]], conn[:, [0, 2, 3]]))
        elif diagonal == "24":
            tri = np.vstack((conn[:, [0, 1, 3]], conn[:, [1, 2, 3]]))
        else:
            raise ValueError(f"Unsupported diagonal: {diagonal}")
    else:
        raise ValueError(f"Expected triangular/quad connectivity, got {conn.shape[1]} nodes")

    signed_area = _tri_area(nodes, tri)
    flipped = signed_area < 0
    if np.any(flipped):
        tri[flipped, [1, 2]] = tri[flipped, [2, 1]]
        signed_area = _tri_area(nodes, tri)
    if np.any(signed_area <= 0):
        raise ValueError("Non-positive triangle area after FEM mesh split")

    return nodes, tri


def write_gmsh41(path: Path, nodes: np.ndarray, tri: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii") as f:
        f.write("$MeshFormat\n4.1 0 8\n$EndMeshFormat\n")
        f.write("$Nodes\n")
        f.write(f"1 {len(nodes)} 1 {len(nodes)}\n")
        f.write(f"2 1 0 {len(nodes)}\n")
        for i in range(1, len(nodes) + 1):
            f.write(f"{i}\n")
        for i, (x, y) in enumerate(nodes, start=1):
            f.write(f"{x:.16g} {y:.16g} 0\n")
        f.write("$EndNodes\n")
        f.write("$Elements\n")
        f.write(f"1 {len(tri)} 1 {len(tri)}\n")
        f.write(f"2 1 2 {len(tri)}\n")
        for i, (a, b, c) in enumerate(tri, start=1):
            f.write(f"{i} {a + 1} {b + 1} {c + 1}\n")
        f.write("$EndElements\n")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mesh-mat", type=Path, default=DEFAULT_MESH_MAT,
                   help="Path to GRIPHFiTH mesh_geometry.mat")
    p.add_argument("--out", type=Path,
                   default=HERE / "meshed_geom_fem_baseline.msh",
                   help="Output .msh path")
    p.add_argument("--diagonal", choices=("13", "24"), default="13",
                   help="Quad split diagonal: 13 means nodes [1,3], 24 means [2,4]")
    args = p.parse_args()

    nodes, tri = load_and_split(args.mesh_mat.expanduser(), args.diagonal)
    area = _tri_area(nodes, tri)
    write_gmsh41(args.out, nodes, tri)
    print(f"Wrote {args.out}")
    print(f"  nodes     : {len(nodes)}")
    print(f"  triangles : {len(tri)}")
    print(f"  area sum  : {area.sum():.12g}")
    print(f"  area range: [{area.min():.6g}, {area.max():.6g}]")
    print(f"  x range   : [{nodes[:, 0].min():.6g}, {nodes[:, 0].max():.6g}]")
    print(f"  y range   : [{nodes[:, 1].min():.6g}, {nodes[:, 1].max():.6g}]")


if __name__ == "__main__":
    main()
