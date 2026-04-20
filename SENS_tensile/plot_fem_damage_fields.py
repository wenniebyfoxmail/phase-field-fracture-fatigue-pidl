#!/usr/bin/env python3
"""
plot_fem_damage_fields.py — Spatial visualization of FEM damage fields
from psi_snapshots_for_agent/*.mat files.

Produces:
    fig_FEM_damage_field.png    — 2 rows (U_max=0.12, 0.08) × 4 cols (cycles)
        showing alpha_elem (fatigue accumulator ᾱ per element)
    fig_FEM_psi_field.png       — same layout for psi_elem (elastic energy density)
    fig_FEM_f_field.png         — same layout for f_alpha_elem (degradation)

Usage:
    cd "upload code/SENS_tensile"
    python plot_fem_damage_fields.py

Data source:
    ~/Downloads/post_process/psi_snapshots_for_agent/
        mesh_geometry.mat       connectivity (77730,4), element_centroids (77730,2),
                                node_coords (77900,2)
        u{08,12}_cycle_NNNN.mat alpha_elem, f_alpha_elem, psi_elem (77730,1 each)
"""
from __future__ import annotations
from pathlib import Path
import sys

import numpy as np
import scipy.io as sio
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, Normalize
import matplotlib.tri as mtri

HERE = Path(__file__).parent
DATA_DIR = Path.home() / "Downloads" / "post_process" / "psi_snapshots_for_agent"

CYCLES = {
    "0.12": [1, 40, 70, 82],       # Last = N_f
    "0.08": [1, 150, 350, 396],    # Last = N_f
}


def load_mesh():
    """Load mesh. Connectivity is 4-node QUADS. Split each into 2 triangles
    so we can use tripcolor."""
    m = sio.loadmat(DATA_DIR / "mesh_geometry.mat")
    node_coords = m["node_coords"]                    # (77900, 2)
    conn = m["connectivity"].astype(int) - 1          # (77730, 4), 1→0 indexed
    # Split each quad (a,b,c,d) into 2 triangles (a,b,c) and (a,c,d)
    quads = conn
    tri1 = quads[:, [0, 1, 2]]
    tri2 = quads[:, [0, 2, 3]]
    tri_conn = np.vstack([tri1, tri2])                # (2 × 77730, 3)
    return node_coords, tri_conn


def load_cycle(u_max: str, cycle: int) -> dict:
    u_tag = u_max.split(".")[1]        # "0.12" → "12"
    p = DATA_DIR / f"u{u_tag}_cycle_{cycle:04d}.mat"
    m = sio.loadmat(p)
    return {
        "alpha": m["alpha_elem"].flatten(),
        "f":     m["f_alpha_elem"].flatten(),
        "psi":   m["psi_elem"].flatten(),
    }


def plot_field_grid(field_name: str, data_key: str, use_log: bool,
                    cmap: str, title_suffix: str, outpath: Path,
                    vmin: float = None, vmax: float = None,
                    clip_low: float = None) -> None:
    """Create 2×4 grid of FEM fields over U_max ∈ {0.12, 0.08} × 4 cycles."""
    node_coords, tri_conn = load_mesh()
    # Create Triangulation for tripcolor
    triang = mtri.Triangulation(node_coords[:, 0], node_coords[:, 1], tri_conn)

    fig, axes = plt.subplots(2, 4, figsize=(14, 6.5))

    # Determine global vmin/vmax if not provided (across all 8 snapshots)
    if vmin is None or vmax is None:
        all_vals = []
        for u_max, cycles in CYCLES.items():
            for c in cycles:
                all_vals.append(load_cycle(u_max, c)[data_key])
        all_vals = np.concatenate(all_vals)
        if clip_low is not None:
            all_vals = np.where(all_vals > clip_low, all_vals, clip_low)
        if vmin is None:
            vmin = float(np.percentile(all_vals, 1)) if use_log else float(all_vals.min())
        if vmax is None:
            vmax = float(all_vals.max())
    if use_log:
        vmin = max(vmin, 1e-12)
        norm = LogNorm(vmin=vmin, vmax=vmax)
    else:
        norm = Normalize(vmin=vmin, vmax=vmax)

    for row, (u_max, cycles) in enumerate(CYCLES.items()):
        for col, c in enumerate(cycles):
            ax = axes[row, col]
            v_quad = load_cycle(u_max, c)[data_key]       # (77730,)
            if clip_low is not None:
                v_quad = np.maximum(v_quad, clip_low)
            # Each quad's value applies to BOTH triangles from the split
            v_tri = np.concatenate([v_quad, v_quad])      # (2×77730,)
            tpc = ax.tripcolor(triang, facecolors=v_tri, cmap=cmap, norm=norm,
                               shading='flat', edgecolors='none')
            # N_f marker
            marker = " (N_f)" if c == cycles[-1] else ""
            ax.set_title(f"U={u_max}  cycle={c}{marker}", fontsize=10)
            ax.set_aspect('equal')
            ax.set_xlim(-0.5, 0.5)
            ax.set_ylim(-0.5, 0.5)
            ax.set_xticks([])
            ax.set_yticks([])
            # Crack initial line for reference
            ax.plot([-0.5, 0], [0, 0], 'k-', lw=0.8, alpha=0.6)

    # Add shared colorbar
    cbar = fig.colorbar(tpc, ax=axes, orientation='vertical', fraction=0.03, pad=0.02)
    cbar.set_label(title_suffix, rotation=270, labelpad=15)

    fig.suptitle(f"FEM {field_name} across cycles — "
                 f"row 1: $U_{{max}}=0.12$ (concentration), "
                 f"row 2: $U_{{max}}=0.08$ (dispersion)",
                 y=1.00, fontsize=12)
    # Don't tight_layout after colorbar added — use subplots_adjust
    fig.savefig(outpath, dpi=180, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✅ {outpath.name}")


def main() -> int:
    outdir = HERE / "figures" / "fem_fields"
    outdir.mkdir(parents=True, exist_ok=True)

    if not DATA_DIR.exists():
        print(f"❌ Data dir not found: {DATA_DIR}")
        return 1

    print(f"Reading from: {DATA_DIR}")
    node_coords, tri_conn = load_mesh()
    print(f"  mesh: {len(node_coords)} nodes, {len(tri_conn)} triangles")
    print()

    # 1. alpha_elem (fatigue accumulator ᾱ) — log scale (spans 1e-7 to ~400)
    print("Plotting alpha_elem (ᾱ fatigue accumulator) ...")
    plot_field_grid(
        field_name="fatigue accumulator " + r"$\bar{\alpha}_\mathrm{elem}$",
        data_key="alpha",
        use_log=True, cmap="plasma",
        title_suffix=r"$\bar{\alpha}_\mathrm{elem}$ (log)",
        clip_low=1e-5,
        outpath=outdir / "fig_FEM_alpha_field.png",
    )

    # 2. psi_elem (elastic energy density) — log scale
    print("Plotting psi_elem (ψ⁺ elastic energy density) ...")
    plot_field_grid(
        field_name=r"elastic energy density $\psi^+_\mathrm{elem}$",
        data_key="psi",
        use_log=True, cmap="viridis",
        title_suffix=r"$\psi^+_\mathrm{elem}$ (log)",
        clip_low=1e-7,
        outpath=outdir / "fig_FEM_psi_field.png",
    )

    # 3. f_alpha_elem (degradation function value) — linear [0,1]
    print("Plotting f_alpha_elem (degradation function) ...")
    plot_field_grid(
        field_name=r"degradation function $f(\bar{\alpha})$",
        data_key="f",
        use_log=False, cmap="RdYlGn",     # red=broken, green=intact
        title_suffix=r"$f(\bar{\alpha})$",
        vmin=0.0, vmax=1.0,
        outpath=outdir / "fig_FEM_f_field.png",
    )

    print(f"\n✅ All 3 figures in: {outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
