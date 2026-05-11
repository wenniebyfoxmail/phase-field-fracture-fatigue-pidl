#!/usr/bin/env python3
"""plot_fig_B_soft_sym_mirror.py — α field + mirror residual visualization for soft-sym run.

Loads the α snapshot (x, y, α centroids) from a soft-symmetry-penalty production
archive at the fracture cycle, then produces a 2-panel figure:

  (a) α field at fracture cycle (tricontour over element centroids)
  (b) mirror residual α(x,y) − α(x,−y) (signed, diverging colormap)

The (b) panel visualises what V4 RMS=0.0219 looks like in space — i.e. where the
soft penalty fails to enforce exact mirror parity.

Defaults to the seed1 N=300 u=0.12 soft-sym archive shipped to
`_data_for_figB/softsym_seed1_alpha_cycle_0088.npy`.

Usage:
  python plot_fig_B_soft_sym_mirror.py
  python plot_fig_B_soft_sym_mirror.py --snap path/to/alpha_cycle_NNNN.npy --cycle NNNN
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation
from scipy.spatial import cKDTree

HERE = Path(__file__).parent
DEFAULT_SNAP = HERE.parent / "_data_for_figB" / "softsym_seed1_alpha_cycle_0088.npy"


def compute_mirror_residual(x, y, a):
    """For each (x_i, y_i), find element with centroid nearest to (x_i, -y_i)
    and return α(x,y) − α(x,−y). Uses KDTree NN — for soft-sym points exactly on
    the y=0 line this gives ~0 by construction.
    """
    tree = cKDTree(np.c_[x, y])
    _, mirror_idx = tree.query(np.c_[x, -y], k=1)
    return a - a[mirror_idx]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snap", default=str(DEFAULT_SNAP))
    parser.add_argument("--out", default=str(HERE / "fig_B_soft_sym_mirror.pdf"))
    parser.add_argument("--cycle", type=int, default=88)
    parser.add_argument("--label", default="soft-sym λ=1.0, u=0.12, seed 1")
    args = parser.parse_args()

    data = np.load(args.snap).astype(np.float64)
    if data.ndim != 2 or data.shape[1] != 3:
        raise ValueError(f"Expected (N,3) snapshot, got shape {data.shape}")
    x, y, a = data[:, 0], data[:, 1], data[:, 2]

    err = compute_mirror_residual(x, y, a)
    rms = float(np.sqrt(np.mean(err ** 2)))
    max_abs = float(np.max(np.abs(err)))

    tri = Triangulation(x, y)

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.0), constrained_layout=True)

    # ---- Panel (a): α field ----
    a_clip = np.clip(a, 0.0, 1.0)
    cf1 = axes[0].tricontourf(tri, a_clip, levels=np.linspace(0.0, 1.0, 21),
                              cmap="hot", extend="neither")
    axes[0].set_aspect("equal")
    axes[0].set_xlim(-0.5, 0.5)
    axes[0].set_ylim(-0.5, 0.5)
    axes[0].set_xlabel("x")
    axes[0].set_ylabel("y")
    axes[0].set_title(f"(a) α field @ cycle {args.cycle}")
    axes[0].plot([-0.5, 0.0], [0.0, 0.0], "c-", lw=1.5, label="initial slit")
    axes[0].legend(loc="upper right", fontsize=8)
    cb1 = fig.colorbar(cf1, ax=axes[0], shrink=0.85)
    cb1.set_label("α")

    # ---- Panel (b): mirror residual ----
    vmax = max(abs(err.min()), abs(err.max()))
    cf2 = axes[1].tricontourf(tri, err, levels=np.linspace(-vmax, vmax, 21),
                              cmap="RdBu_r")
    axes[1].set_aspect("equal")
    axes[1].set_xlim(-0.5, 0.5)
    axes[1].set_ylim(-0.5, 0.5)
    axes[1].set_xlabel("x")
    axes[1].set_ylabel("y")
    axes[1].set_title(
        f"(b) Mirror residual α(x,y) − α(x,−y)\n"
        f"RMS = {rms:.4f},  max|·| = {max_abs:.4f}"
    )
    axes[1].plot([-0.5, 0.0], [0.0, 0.0], "k-", lw=1.5)
    cb2 = fig.colorbar(cf2, ax=axes[1], shrink=0.85)
    cb2.set_label("Δα (signed)")

    fig.suptitle(f"Soft mirror-symmetry penalty — {args.label}", y=1.02)
    fig.savefig(args.out, bbox_inches="tight", dpi=150)
    print(f"saved: {args.out}")
    print(f"  N_centroids: {len(x)}")
    print(f"  RMS mirror residual:  {rms:.6f}")
    print(f"  max|·| mirror residual: {max_abs:.6f}")
    print(f"  α range: [{a.min():.4f}, {a.max():.4f}]")


if __name__ == "__main__":
    main()
