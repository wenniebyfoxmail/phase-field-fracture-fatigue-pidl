#!/usr/bin/env python3
"""
plot_hero_fem_d_evolution.py — Paper hero figure: FEM structural damage (d_elem)
evolution across cycles for two U_max regimes.

2 rows x 4 cols grid:
    row 1: U_max=0.12, cycles [1, 40, 70, 82 (N_f)]
    row 2: U_max=0.08, cycles [1, 150, 350, 396 (N_f)]
Field shown: d_elem (phase-field structural damage, linear [0, 1]).

Purpose: show that structural fracture (d >= 0.95) is a narrow ~2% band in
both regimes, while the *path* differs — the 6%->88% figure belongs to
fatigue weakening (f < 0.5), not structural damage.

Data source: ~/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent/
    u{08,12}_cycle_*.mat  (keys: alpha_bar_elem, d_elem, f_alpha_elem, psi_elem)
    mesh_geometry.mat     (node_coords, connectivity)
"""
from __future__ import annotations
from pathlib import Path
import sys

import numpy as np
import scipy.io as sio
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.colors import Normalize

FEM_DIR = Path.home() / "Downloads" / "_pidl_handoff_v2" / "psi_snapshots_for_agent"
HERE = Path(__file__).parent
OUT_DIR = HERE / "figures" / "fem_fields"

CASES = [
    ("12", [1, 40, 70, 82],  82),   # N_f=82
    ("08", [1, 150, 350, 396], 396), # N_f=396
]


def load_mesh():
    m = sio.loadmat(FEM_DIR / "mesh_geometry.mat")
    nodes = m["node_coords"]
    conn = m["connectivity"].astype(int) - 1
    tri = np.vstack([conn[:, [0, 1, 2]], conn[:, [0, 2, 3]]])
    return nodes, tri


def load_cycle(u_tag: str, cycle: int) -> np.ndarray:
    m = sio.loadmat(FEM_DIR / f"u{u_tag}_cycle_{cycle:04d}.mat")
    return m["d_elem"].flatten()


def panel_stats(d: np.ndarray) -> tuple[float, float]:
    return float(d.max()), float((d >= 0.95).mean() * 100.0)


def plot_panel(ax, nodes, tri, d_quad, title):
    d_tri = np.concatenate([d_quad, d_quad])       # quad -> 2 triangles
    triang = mtri.Triangulation(nodes[:, 0], nodes[:, 1], tri)
    d_clip = np.clip(d_tri, 0.0, 1.0)              # hide L2 overshoot >1
    tpc = ax.tripcolor(triang, facecolors=d_clip, cmap="hot_r",
                       norm=Normalize(vmin=0.0, vmax=1.0),
                       shading="flat", edgecolors="none")
    ax.set_aspect("equal")
    ax.set_xlim(-0.5, 0.5); ax.set_ylim(-0.5, 0.5)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, fontsize=10)
    # precrack reference line (left half of x-axis, y=0)
    ax.plot([-0.5, 0.0], [0.0, 0.0], "k-", lw=0.6, alpha=0.5)
    return tpc


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading mesh ...")
    nodes, tri = load_mesh()

    print("Loading d_elem snapshots ...")
    rows_data = []
    for u_tag, cycles, nf in CASES:
        row = []
        for c in cycles:
            d = load_cycle(u_tag, c)
            row.append((c, d, *panel_stats(d)))
        rows_data.append((u_tag, nf, row))

    # === Plot ===
    fig, axes = plt.subplots(2, 4, figsize=(13, 6.6))
    tpc = None
    for r, (u_tag, nf, row) in enumerate(rows_data):
        for c, (cycle, d, d_max, pct) in enumerate(row):
            is_nf = (cycle == nf)
            cycle_lbl = f"cycle {cycle}" + (f" = N_f" if is_nf else "")
            title = (f"U_max=0.{u_tag}  |  {cycle_lbl}\n"
                     f"d_max={d_max:.2f}   d≥0.95: {pct:.2f}%")
            tpc = plot_panel(axes[r, c], nodes, tri, d, title)

    # Row labels on the left
    for r, (u_tag, nf, _) in enumerate(rows_data):
        axes[r, 0].set_ylabel(f"$U_{{max}}=0.{u_tag}$\n($N_f$={nf})",
                              fontsize=11, fontweight="bold", labelpad=8)
        axes[r, 0].yaxis.set_label_coords(-0.05, 0.5)

    fig.subplots_adjust(right=0.91, top=0.90, bottom=0.06,
                        left=0.05, hspace=0.30, wspace=0.06)
    cax = fig.add_axes([0.93, 0.1, 0.015, 0.78])
    cb = fig.colorbar(tpc, cax=cax)
    cb.set_label(r"Structural damage  $d$  (phase-field)",
                 fontsize=11)
    cb.ax.axhline(0.95, color="black", lw=1.0, ls="--")
    cb.ax.text(1.8, 0.95, "0.95\n(fracture)", va="center", fontsize=8,
               transform=cb.ax.get_yaxis_transform())

    fig.suptitle("FEM structural-damage evolution: narrow fracture band "
                 "(~2%) in both regimes; path-to-fracture differs",
                 fontsize=12.5, fontweight="bold", y=0.975)

    out = OUT_DIR / "fig_hero_FEM_d_evolution.png"
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"\n[OK] {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
