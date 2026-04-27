#!/usr/bin/env python3
"""
make_alpha1_mesh.py — Generate `meshed_geom_corridor_v1.msh` for α-1 Variant A.

Why this script (not just `gmsh -2 .geo`): the gmsh Box field with VIn /
VOut didn't actually drive in-corridor refinement in our gmsh 4.15.2 build
(VIn was effectively ignored). Instead we build the mesh via OCC kernel +
BooleanFragments + per-point `setSize()`, which works reliably.

Run once after `git pull` to materialize the binary mesh (which is in
.gitignore via `*.msh`). Output: `meshed_geom_corridor_v1.msh` next to
this script. Windows + Mac produce byte-identical output (deterministic).

Usage:
    python make_alpha1_mesh.py [--variant corridor_v1] [--h-c 0.001] [--h-f 0.020]
                               [--y-corridor 0.04] [--x-max 0.5]
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

import gmsh

HERE = Path(__file__).parent


def make_corridor_mesh(out_path: Path, h_c: float, h_f: float,
                       y_corridor: float, x_max_corr: float, L: float = 0.5,
                       verbose: int = 2) -> tuple[int, int]:
    """Generate refined-corridor mesh; return (n_nodes, n_triangles)."""
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Verbosity", verbose)
        gmsh.model.add("alpha1_corridor")

        # Outer rectangle + inner corridor rectangle
        outer = gmsh.model.occ.addRectangle(-L, -L, 0, 2 * L, 2 * L)
        inner = gmsh.model.occ.addRectangle(0.0, -y_corridor, 0,
                                            x_max_corr, 2 * y_corridor)
        # Boolean fragment splits the outer at the inner boundary so we get
        # 2 surfaces sharing edges; per-point sizing then drives mesh density
        gmsh.model.occ.fragment([(2, outer)], [(2, inner)])
        gmsh.model.occ.synchronize()

        # Per-point sizing: h_c inside corridor box, h_f outside
        for dim, tag in gmsh.model.getEntities(0):
            x, y, _ = gmsh.model.getValue(0, tag, [])
            in_corridor = (-1e-6 <= x <= x_max_corr + 1e-6) \
                          and (-y_corridor - 1e-6 <= y <= y_corridor + 1e-6)
            gmsh.model.mesh.setSize([(0, tag)], h_c if in_corridor else h_f)

        gmsh.option.setNumber("Mesh.Algorithm", 6)            # Frontal-Delaunay
        gmsh.option.setNumber("Mesh.MshFileVersion", 4.1)     # match legacy
        gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 1)
        gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 1)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
        gmsh.model.mesh.generate(2)

        n_nodes = len(gmsh.model.mesh.getNodes()[0])
        n_tri = len(gmsh.model.mesh.getElementsByType(2)[0])
        gmsh.write(str(out_path))
        return n_nodes, n_tri
    finally:
        gmsh.finalize()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="corridor_v1",
                    help="Mesh tag → output file `meshed_geom_<tag>.msh`. "
                         "v1 default uses h_c=0.001 to match FEM tip refinement.")
    ap.add_argument("--h-c", type=float, default=0.001,
                    help="Element size inside corridor (default 0.001 = "
                         "matches FEM tip per α-0).")
    ap.add_argument("--h-f", type=float, default=0.020,
                    help="Element size in far field (default 0.020).")
    ap.add_argument("--y-corridor", type=float, default=0.04,
                    help="Corridor half-width along y (default 0.04 = 4ℓ₀).")
    ap.add_argument("--x-max", type=float, default=0.5,
                    help="Corridor max x (default 0.5 = right edge).")
    args = ap.parse_args()

    out_path = HERE / f"meshed_geom_{args.variant}.msh"
    print(f"Generating {out_path.name}…")
    print(f"  h_c={args.h_c}  h_f={args.h_f}  "
          f"y_corridor=±{args.y_corridor}  x_max={args.x_max}")
    n_nodes, n_tri = make_corridor_mesh(
        out_path, h_c=args.h_c, h_f=args.h_f,
        y_corridor=args.y_corridor, x_max_corr=args.x_max,
    )
    print(f"→ {out_path.name}  ({n_nodes} nodes, {n_tri} triangles)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
