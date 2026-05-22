"""
Phase 3 Step 1 (FEM version): FEM d(x,y) → binary crack mask → skeleton

Data source: ~/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent/
  mesh_geometry.mat  — element_centroids (77730×2)
  u{UU}_cycle_{CCCC}.mat — d_elem (77730×1), alpha_bar_elem, f_alpha_elem, psi_elem

FEM d field: 0=intact, 1=fully broken. Threshold d > D_THRESH (default 0.5).

Usage:
  python phase3_fem_pipeline.py                   # all available cases
  python phase3_fem_pipeline.py --umax 12         # only Umax=0.12 cases
  python phase3_fem_pipeline.py --stats           # also compute morphology stats
"""

import argparse, os, glob
import numpy as np
import scipy.io as sio
from scipy.interpolate import griddata
from scipy.ndimage import binary_closing
from skimage.morphology import skeletonize
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HANDOFF  = os.path.expanduser("~/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent")
D_THRESH = 0.5
GRID_RES = 512
DOMAIN   = (-0.5, 0.5)
PX_MM    = 1.0 / GRID_RES


def load_mesh():
    mat  = sio.loadmat(os.path.join(HANDOFF, "mesh_geometry.mat"))
    xy   = mat["element_centroids"].astype(np.float32)
    return xy[:, 0], xy[:, 1]


def load_fem(umax_str, cycle):
    path = os.path.join(HANDOFF, f"u{umax_str}_cycle_{cycle:04d}.mat")
    mat  = sio.loadmat(path)
    return {k: mat[k].ravel().astype(np.float32)
            for k in ("d_elem", "alpha_bar_elem", "f_alpha_elem", "psi_elem")}


def to_grid(x, y, vals, res=GRID_RES):
    xi = np.linspace(DOMAIN[0], DOMAIN[1], res)
    yi = np.linspace(DOMAIN[0], DOMAIN[1], res)
    xi2d, yi2d = np.meshgrid(xi, yi)
    grid = griddata((x, y), vals, (xi2d, yi2d), method="linear", fill_value=0.0)
    return np.clip(grid, 0.0, None)


def grid_to_mask(grid_d):
    mask = (grid_d > D_THRESH).astype(np.uint8)
    return binary_closing(mask, iterations=2).astype(np.uint8)


def morphology_stats(mask, skel):
    skel_px  = int(skel.sum())
    mask_px  = int(mask.sum())
    total_px = GRID_RES * GRID_RES
    width_px = mask_px / skel_px if skel_px > 0 else float("nan")
    area_frac = mask_px / total_px
    ys, xs = np.where(skel > 0)
    if len(xs) > 1:
        x_span = int(xs.max()) - int(xs.min())
        tort = skel_px / x_span if x_span > 0 else float("nan")
        idx  = xs.argmax()
        tip_x = xs[idx] * PX_MM + DOMAIN[0]
        tip_y = ys[idx] * PX_MM + DOMAIN[0]
    else:
        tort = tip_x = tip_y = float("nan")
    return {
        "skel_px": skel_px, "skel_mm": round(skel_px * PX_MM, 4),
        "mask_px": mask_px, "width_px": round(width_px, 2),
        "width_mm": round(width_px * PX_MM, 5) if not np.isnan(width_px) else float("nan"),
        "area_frac": round(area_frac, 5),
        "tortuosity": round(tort, 4) if not np.isnan(tort) else float("nan"),
        "tip_x": round(tip_x, 4) if not np.isnan(tip_x) else float("nan"),
        "tip_y": round(tip_y, 4) if not np.isnan(tip_y) else float("nan"),
    }


def make_panel(grids, mask, skel, umax_str, cycle, out_path):
    d_grid, abar_grid, psi_grid = grids
    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    ext = [DOMAIN[0], DOMAIN[1], DOMAIN[0], DOMAIN[1]]

    im0 = axes[0].imshow(d_grid, origin="lower", extent=ext, cmap="hot_r", vmin=0, vmax=1)
    fig.colorbar(im0, ax=axes[0], fraction=0.046)
    axes[0].set_title(f"FEM d field  (U={umax_str}, N={cycle})")

    im1 = axes[1].imshow(np.log10(np.clip(abar_grid, 1e-2, None)),
                         origin="lower", extent=ext, cmap="viridis", vmin=-1, vmax=3)
    fig.colorbar(im1, ax=axes[1], fraction=0.046, label="log₁₀(ᾱ)")
    axes[1].set_title("log₁₀(ᾱ)")

    axes[2].imshow(mask, origin="lower", extent=ext, cmap="Greys", vmin=0, vmax=1)
    axes[2].set_title(f"Binary mask  (d > {D_THRESH})")

    axes[3].imshow(mask, origin="lower", extent=ext, cmap="Greys", vmin=0, vmax=1, alpha=0.4)
    skel_rgba = np.zeros((*skel.shape, 4))
    skel_rgba[skel > 0] = [1, 0, 0, 1]
    axes[3].imshow(skel_rgba, origin="lower", extent=ext)
    axes[3].set_title("Skeleton (crack centreline)")

    for ax in axes:
        ax.set_xlabel("x [mm]"); ax.set_ylabel("y [mm]")
    plt.tight_layout()
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def make_skeleton_png(skel, out_path):
    fig, ax = plt.subplots(figsize=(4, 4))
    ext = [DOMAIN[0], DOMAIN[1], DOMAIN[0], DOMAIN[1]]
    display = np.ones_like(skel, dtype=np.float32)
    display[skel > 0] = 0.0
    ax.imshow(display, origin="lower", extent=ext, cmap="Greys", vmin=0, vmax=1)
    ax.axis("off")
    plt.tight_layout(pad=0)
    plt.savefig(out_path, dpi=120, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


def run(umax_filter=None, do_stats=False):
    x, y = load_mesh()
    print(f"Mesh loaded: {len(x)} elements, x=[{x.min():.3f},{x.max():.3f}]")

    # discover available files
    mat_files = sorted(glob.glob(os.path.join(HANDOFF, "u??_cycle_????.mat")))
    cases = []
    for p in mat_files:
        fn   = os.path.basename(p)
        ustr = fn[1:3]    # e.g. "08"
        cyc  = int(fn.split("_cycle_")[1].replace(".mat", ""))
        if umax_filter and ustr != umax_filter.zfill(2):
            continue
        cases.append((ustr, cyc, p))

    base    = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "..", "phase3_output", "fem")
    os.makedirs(out_dir, exist_ok=True)

    stat_rows = []
    for ustr, cyc, _ in cases:
        print(f"  u={ustr} cycle={cyc:04d} ...", end=" ")
        fields = load_fem(ustr, cyc)
        d_grid    = to_grid(x, y, fields["d_elem"])
        abar_grid = to_grid(x, y, fields["alpha_bar_elem"])
        psi_grid  = to_grid(x, y, fields["psi_elem"])

        mask = grid_to_mask(d_grid)
        skel = skeletonize(mask.astype(bool)).astype(np.uint8)

        panel_p = os.path.join(out_dir, f"panel_u{ustr}_cycle_{cyc:04d}.png")
        make_panel((d_grid, abar_grid, psi_grid), mask, skel, ustr, cyc, panel_p)

        skel_p = os.path.join(out_dir, f"skeleton_u{ustr}_cycle_{cyc:04d}.png")
        make_skeleton_png(skel, skel_p)

        m = morphology_stats(mask, skel)
        print(f"skel={m['skel_px']}px ({m['skel_mm']}mm)  "
              f"width={m['width_px']}px  tort={m['tortuosity']}  "
              f"tip=({m['tip_x']},{m['tip_y']})mm")

        if do_stats:
            stat_rows.append({"umax": ustr, "cycle": cyc, **m})

    if do_stats and stat_rows:
        import csv
        csv_path = os.path.join(out_dir, "fem_morphology_stats.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=stat_rows[0].keys())
            writer.writeheader(); writer.writerows(stat_rows)
        print(f"\nStats → {csv_path}")

    print(f"Done. Output in {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--umax",  default=None, help="Filter by umax, e.g. 08 or 12")
    parser.add_argument("--stats", action="store_true")
    args = parser.parse_args()
    run(umax_filter=args.umax, do_stats=args.stats)
