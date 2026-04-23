#!/usr/bin/env python3
"""
plot_fem_mode_shift.py — Paper motivation figure: FEM's own concentration→dispersion
transition across loading magnitude.

Shows that even FEM (our ground truth) exhibits qualitatively different fracture
patterns at high vs low U_max:
    - High U_max (0.12): damage CONCENTRATES at tip (narrow red band at N_f)
    - Low U_max (0.08): damage DISPERSES across wider band (larger red zone)

This is the PHENOMENON we want PIDL to reproduce.

Usage:
    cd "upload code/SENS_tensile"
    python plot_fem_mode_shift.py

Outputs:
    figures/fem_fields/fig_FEM_mode_shift_motivation.png    — 2×4 focused on f field
    figures/fem_fields/fig_FEM_mode_shift_extremes.png      — 2×1 comparison at N_f
"""
from __future__ import annotations
from pathlib import Path
import sys

import numpy as np
import scipy.io as sio
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import matplotlib.tri as mtri

HERE = Path(__file__).parent
DATA_DIR = Path.home() / "Downloads" / "post_process" / "psi_snapshots_for_agent"

CYCLES = {
    "0.12": [1, 40, 70, 82],
    "0.08": [1, 150, 350, 396],
}


def load_mesh():
    m = sio.loadmat(DATA_DIR / "mesh_geometry.mat")
    nodes = m["node_coords"]
    conn = m["connectivity"].astype(int) - 1
    tri = np.vstack([conn[:, [0, 1, 2]], conn[:, [0, 2, 3]]])
    return nodes, tri


def load_f(u_tag: str, cycle: int) -> np.ndarray:
    p = DATA_DIR / f"u{u_tag}_cycle_{cycle:04d}.mat"
    return sio.loadmat(p)["f_alpha_elem"].flatten()


def frac_damaged(f_vals: np.ndarray, threshold: float = 0.5) -> float:
    """Fraction of elements with f < threshold (i.e. > 50% degraded)."""
    return float((f_vals < threshold).sum() / len(f_vals))


def make_motivation_figure(outpath: Path) -> None:
    """2 rows (U_max=0.12, 0.08) × 4 cols (cycles) — f field progression."""
    nodes, tri = load_mesh()
    triang = mtri.Triangulation(nodes[:, 0], nodes[:, 1], tri)

    fig, axes = plt.subplots(2, 4, figsize=(13, 6.5))
    norm = Normalize(vmin=0.0, vmax=1.0)

    row_labels = {"0.12": "High load\n$U_{max}=0.12$  ($N_f=82$)",
                  "0.08": "Low load\n$U_{max}=0.08$  ($N_f=396$)"}

    last_tpc = None
    for row, (u_max, cycles) in enumerate(CYCLES.items()):
        for col, c in enumerate(cycles):
            ax = axes[row, col]
            f_quad = load_f(u_max.split(".")[1], c)
            f_tri = np.concatenate([f_quad, f_quad])
            last_tpc = ax.tripcolor(triang, facecolors=f_tri, cmap="RdYlGn",
                                    norm=norm, shading='flat', edgecolors='none')
            # Frac damaged annotation
            frac = frac_damaged(f_quad, 0.5)
            ax.text(0.04, 0.96, f"{frac*100:.0f}%\n(f<0.5)",
                    transform=ax.transAxes, va='top', fontsize=8,
                    bbox=dict(boxstyle='round,pad=0.3',
                              facecolor='white', alpha=0.75, edgecolor='none'))

            # Top labels on row 0
            if row == 0:
                nf_tag = " (N_f)" if c == cycles[-1] else ""
                ax.set_title(f"cycle {c}{nf_tag}", fontsize=11)
            # Initial crack line
            ax.plot([-0.5, 0], [0, 0], 'k-', lw=1, alpha=0.7)
            ax.set_aspect('equal')
            ax.set_xlim(-0.5, 0.5); ax.set_ylim(-0.5, 0.5)
            ax.set_xticks([]); ax.set_yticks([])

        # Row label on left
        axes[row, 0].text(-0.18, 0.5, row_labels[u_max],
                           transform=axes[row, 0].transAxes,
                           va='center', ha='center', rotation=90,
                           fontsize=11, fontweight='bold')

    # Shared colorbar
    cbar_ax = fig.add_axes([0.92, 0.15, 0.015, 0.7])
    cbar = fig.colorbar(last_tpc, cax=cbar_ax)
    cbar.set_label(r"$f(\bar{\alpha})$   (1=intact, 0=broken)",
                   rotation=270, labelpad=20, fontsize=10)

    fig.suptitle("FEM damage evolution — "
                 "high load concentrates at tip, low load disperses across domain",
                 fontsize=13, fontweight='bold', y=0.97)
    fig.subplots_adjust(left=0.08, right=0.90, top=0.88, bottom=0.04,
                        hspace=0.15, wspace=0.05)
    fig.savefig(outpath, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✅ {outpath.name}")


def make_extremes_figure(outpath: Path) -> None:
    """2×1 focused comparison: U=0.12 at N_f vs U=0.08 at N_f.
    For quick "at a glance" paper figure."""
    nodes, tri = load_mesh()
    triang = mtri.Triangulation(nodes[:, 0], nodes[:, 1], tri)

    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    norm = Normalize(vmin=0.0, vmax=1.0)

    cases = [("0.12", 82), ("0.08", 396)]
    labels = ["$U_{max}=0.12$, $N_f=82$\n(concentrated fracture)",
              "$U_{max}=0.08$, $N_f=396$\n(dispersed fracture)"]

    last_tpc = None
    for i, ((u_max, cycle), label) in enumerate(zip(cases, labels)):
        ax = axes[i]
        f_quad = load_f(u_max.split(".")[1], cycle)
        f_tri = np.concatenate([f_quad, f_quad])
        last_tpc = ax.tripcolor(triang, facecolors=f_tri, cmap="RdYlGn",
                                norm=norm, shading='flat', edgecolors='none')
        frac = frac_damaged(f_quad, 0.5)
        ax.text(0.04, 0.96,
                f"f_mean = {f_quad.mean():.3f}\n{frac*100:.1f}% elem damaged (f<0.5)",
                transform=ax.transAxes, va='top', fontsize=9,
                bbox=dict(boxstyle='round,pad=0.4',
                          facecolor='white', alpha=0.85, edgecolor='gray'))
        ax.set_title(label, fontsize=12, fontweight='bold')
        ax.plot([-0.5, 0], [0, 0], 'k-', lw=1.2, alpha=0.7)
        ax.set_aspect('equal')
        ax.set_xlim(-0.5, 0.5); ax.set_ylim(-0.5, 0.5)
        ax.set_xticks([]); ax.set_yticks([])

    cbar_ax = fig.add_axes([0.92, 0.15, 0.018, 0.7])
    cbar = fig.colorbar(last_tpc, cax=cbar_ax)
    cbar.set_label(r"$f(\bar{\alpha})$  (degradation; 1=intact, 0=broken)",
                   rotation=270, labelpad=20, fontsize=10)

    fig.suptitle("FEM damage-mode shift with loading magnitude",
                 fontsize=14, fontweight='bold', y=0.99)
    fig.subplots_adjust(left=0.03, right=0.89, top=0.88, bottom=0.04, wspace=0.08)
    fig.savefig(outpath, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✅ {outpath.name}")


def main() -> int:
    outdir = HERE / "figures" / "fem_fields"
    outdir.mkdir(parents=True, exist_ok=True)
    print("Generating FEM mode-shift motivation figures ...")

    make_motivation_figure(outdir / "fig_FEM_mode_shift_motivation.png")
    make_extremes_figure(outdir / "fig_FEM_mode_shift_extremes.png")

    # Stats summary
    print("\nFraction of elements damaged (f < 0.5) at N_f:")
    for u_max, cycles in CYCLES.items():
        c_nf = cycles[-1]
        f_vals = load_f(u_max.split(".")[1], c_nf)
        print(f"  U_max={u_max}, cycle {c_nf}: "
              f"f_mean={f_vals.mean():.3f}  "
              f"%damaged(f<0.5)={frac_damaged(f_vals, 0.5)*100:.1f}%  "
              f"%broken(f<0.1)={frac_damaged(f_vals, 0.1)*100:.1f}%")

    print(f"\n✅ All figures in {outdir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
