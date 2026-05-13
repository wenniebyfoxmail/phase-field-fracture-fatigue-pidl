#!/usr/bin/env python3
"""plot_FEM_alpha_field.py — render FEM α / d / ᾱ fields at a chosen cycle
from the Mac handoff .mat files (figure (b) for the PPT report).

Loads:
  ~/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent/u<UU>_cycle_<NNNN>.mat
  ~/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent/mesh_geometry.mat

The .mat has 4 per-element fields (77730 elements):
  alpha_bar_elem  Carrara accumulator (0 .. O(100))
  d_elem          damage  (0..1)  ← directly comparable to PIDL α
  psi_elem        ψ⁺
  f_alpha_elem    f(ᾱ) ∈ [f_min, 1]

Output: 4-panel PDF showing all four fields side-by-side.

Usage:
    python plot_FEM_alpha_field.py                   # default u12 c0082 (FEM-7)
    python plot_FEM_alpha_field.py --umax 0.10 --cycle 140
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from scipy.io import loadmat

HANDOFF = Path.home() / "Downloads/_pidl_handoff_v2/psi_snapshots_for_agent"
SCRIPT_DIR = Path(__file__).parent.resolve()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--umax", type=float, default=0.12)
    ap.add_argument("--cycle", type=int, default=82)
    ap.add_argument("--mat", type=Path, default=None,
                    help="Override .mat path (default: handoff folder)")
    ap.add_argument("--mesh", type=Path,
                    default=HANDOFF / "mesh_geometry.mat")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    uu = int(round(args.umax * 100))
    mat_path = args.mat or HANDOFF / f"u{uu:02d}_cycle_{args.cycle:04d}.mat"
    out = args.out or (SCRIPT_DIR / f"fig_b_FEM_alpha_u{uu:02d}_c{args.cycle:04d}.pdf")

    if not mat_path.is_file():
        print(f"[error] {mat_path} missing")
        return 1
    if not args.mesh.is_file():
        print(f"[error] {args.mesh} missing")
        return 1

    print(f"[load] {mat_path.name}")
    M = loadmat(mat_path)
    G = loadmat(args.mesh)

    centroids = G["element_centroids"]   # (n_elem, 2)
    cx, cy = centroids[:, 0], centroids[:, 1]
    nodes = G["node_coords"]              # (n_nodes, 2)
    conn = G["connectivity"]              # (n_elem, 4) 1-indexed quad

    alpha_bar = M["alpha_bar_elem"].flatten()
    d_elem    = M["d_elem"].flatten()
    psi_elem  = M["psi_elem"].flatten()
    f_alpha   = M["f_alpha_elem"].flatten()
    d_clip = np.clip(d_elem, 0.0, 1.0)

    print(f"[stats] n_elem={len(alpha_bar)}")
    print(f"  d:        min={d_elem.min():.3e}  max={d_elem.max():.3e}")
    print(f"  ᾱ:        min={alpha_bar.min():.3e}  max={alpha_bar.max():.3e}")
    print(f"  ψ⁺:       min={psi_elem.min():.3e}  max={psi_elem.max():.3e}")
    print(f"  f(ᾱ):     min={f_alpha.min():.3e}  max={f_alpha.max():.3e}")

    # Build triangulation from quad connectivity (split each quad into 2 tris)
    conn0 = (conn - 1).astype(int)   # to 0-indexed
    # For tripcolor per-element (flat) we use the QUAD centroid as scatter
    # but tricontourf needs node-based field. Easiest: use tripcolor with
    # triangulated mesh splitting quads → 2 tris, copy per-quad value.
    tris = np.vstack([conn0[:, [0, 1, 2]], conn0[:, [0, 2, 3]]])
    val_per_tri_d   = np.concatenate([d_clip, d_clip])
    val_per_tri_a   = np.concatenate([alpha_bar, alpha_bar])
    val_per_tri_psi = np.concatenate([psi_elem, psi_elem])
    val_per_tri_f   = np.concatenate([f_alpha, f_alpha])

    fig, axes = plt.subplots(1, 4, figsize=(18, 5), constrained_layout=True)
    titles = [
        rf"(b1) FEM damage $d$ @ c{args.cycle}  max={d_elem.max():.3f}",
        rf"(b2) FEM Carrara $\bar\alpha$ @ c{args.cycle}  max={alpha_bar.max():.1f}",
        rf"(b3) FEM $\psi^+$ @ c{args.cycle}  max={psi_elem.max():.2e}",
        rf"(b4) FEM $f(\bar\alpha)$ @ c{args.cycle}  min={f_alpha.min():.3f}",
    ]
    fields = [
        (val_per_tri_d, "plasma", None, "$d$"),
        (val_per_tri_a, "viridis", mcolors.LogNorm(vmin=max(1e-3, alpha_bar.min()), vmax=alpha_bar.max()), r"$\bar\alpha$ (log)"),
        (val_per_tri_psi, "magma", mcolors.LogNorm(vmin=max(1e-8, psi_elem[psi_elem>0].min()), vmax=psi_elem.max()), r"$\psi^+$ (log)"),
        (val_per_tri_f, "Greens_r", None, r"$f(\bar\alpha)$"),
    ]

    for ax, (v, cmap, norm, clabel), title in zip(axes, fields, titles):
        if norm is None:
            tpc = ax.tripcolor(nodes[:, 0], nodes[:, 1], tris, v,
                               shading="flat", cmap=cmap)
        else:
            tpc = ax.tripcolor(nodes[:, 0], nodes[:, 1], tris, v,
                               shading="flat", cmap=cmap, norm=norm)
        ax.set_aspect("equal")
        ax.set_xlim(-0.5, 0.5); ax.set_ylim(-0.5, 0.5)
        ax.set_xlabel("x"); ax.set_ylabel("y")
        ax.set_title(title, fontsize=9)
        ax.plot([-0.5, 0.0], [0.0, 0.0], "c-", lw=1.2)
        fig.colorbar(tpc, ax=ax, shrink=0.85, label=clabel)

    fig.suptitle(f"FEM-7 reference fields — u_max={args.umax} cycle {args.cycle}",
                 y=1.02, fontsize=10)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    fig.savefig(out.with_suffix(".png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved: {out}")
    print(f"saved: {out.with_suffix('.png')}")


if __name__ == "__main__":
    main()
