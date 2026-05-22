"""
Phase 3 Step A: PIDL crack morphology statistics
Re-computes mask + skeleton directly from alpha .npy files (avoids PNG anti-aliasing).

Metrics per cycle:
  skel_px        — skeleton pixel count (crack centreline length in pixels)
  skel_mm        — skel_px × pixel_size_mm  (physical crack length estimate)
  mask_px        — binary mask pixel count
  width_mean_px  — mask_px / skel_px  (mean diffuse band width)
  width_mean_mm  — same in mm
  area_fraction  — mask_px / total_pixels
  tortuosity     — skel_px / straight-line x-span (≥1, 1=straight)
  tip_x_mm       — crack tip x coordinate (mm), rightmost skel pixel
  tip_y_mm       — crack tip y coordinate (mm)

Usage:
  python phase3_morphology_stats.py            # Umax=0.08
  python phase3_morphology_stats.py --umax 0.12
"""

import argparse, os, glob, sys
import numpy as np
import csv
from scipy.interpolate import griddata
from scipy.ndimage import binary_closing
from skimage.morphology import skeletonize

ALPHA_T   = 0.5
THRESHOLD = 0.5          # crack = α > THRESHOLD × α_T
GRID_RES  = 512
DOMAIN    = (-0.5, 0.5)
PX_MM     = 1.0 / GRID_RES   # mm per pixel

def load_and_grid(npy_path):
    data = np.load(npy_path).astype(np.float32)
    x, y, alpha = data[:, 0], data[:, 1], data[:, 2]
    xi = np.linspace(DOMAIN[0], DOMAIN[1], GRID_RES)
    yi = np.linspace(DOMAIN[0], DOMAIN[1], GRID_RES)
    xi2d, yi2d = np.meshgrid(xi, yi)
    grid = griddata((x, y), alpha, (xi2d, yi2d), method="linear", fill_value=0.0)
    return np.clip(grid, 0.0, None)

def grid_to_mask(grid):
    mask = (grid > THRESHOLD * ALPHA_T).astype(np.uint8)
    return binary_closing(mask, iterations=2).astype(np.uint8)

def compute_metrics(npy_path):
    grid  = load_and_grid(npy_path)
    mask  = grid_to_mask(grid)
    skel  = skeletonize(mask.astype(bool)).astype(np.uint8)

    skel_px  = int(skel.sum())
    mask_px  = int(mask.sum())
    total_px = GRID_RES * GRID_RES

    width_px = mask_px / skel_px if skel_px > 0 else float("nan")
    area_frac = mask_px / total_px

    # tortuosity: path length / straight-line x-span
    ys, xs = np.where(skel > 0)
    if len(xs) > 1:
        x_span = int(xs.max()) - int(xs.min())
        tort = skel_px / x_span if x_span > 0 else float("nan")
        tip_idx = xs.argmax()
        tip_x = xs[tip_idx] * PX_MM + DOMAIN[0]
        tip_y = ys[tip_idx] * PX_MM + DOMAIN[0]
    else:
        tort = float("nan")
        tip_x = tip_y = float("nan")

    return {
        "skel_px":       skel_px,
        "skel_mm":       round(skel_px * PX_MM, 4),
        "mask_px":       mask_px,
        "width_mean_px": round(width_px, 2) if not np.isnan(width_px) else "",
        "width_mean_mm": round(width_px * PX_MM, 5) if not np.isnan(width_px) else "",
        "area_fraction": round(area_frac, 5),
        "tortuosity":    round(tort, 4) if not np.isnan(tort) else "",
        "tip_x_mm":      round(tip_x, 4) if not np.isnan(tip_x) else "",
        "tip_y_mm":      round(tip_y, 4) if not np.isnan(tip_y) else "",
    }

def run(umax="0.08"):
    base = os.path.dirname(os.path.abspath(__file__))
    pattern = os.path.join(
        base,
        f"hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
        f"PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_*"
        f"_R0.0_Umax{umax}",
        "alpha_snapshots",
        "alpha_cycle_*.npy"
    )
    npy_files = sorted(glob.glob(pattern))
    if not npy_files:
        raise FileNotFoundError(f"No npy snapshots found for Umax={umax}")

    out_dir = os.path.join(base, "..", "phase3_output", f"umax{umax}")
    os.makedirs(out_dir, exist_ok=True)

    rows = []
    for npy_path in npy_files:
        cycle = int(os.path.basename(npy_path).replace("alpha_cycle_", "").replace(".npy", ""))
        m = compute_metrics(npy_path)
        m["cycle"] = cycle
        rows.append(m)
        print(f"  cycle {cycle:04d}: skel={m['skel_px']}px ({m['skel_mm']}mm)  "
              f"width={m['width_mean_px']}px ({m['width_mean_mm']}mm)  "
              f"tort={m['tortuosity']}  tip=({m['tip_x_mm']},{m['tip_y_mm']})mm")

    cols = ["cycle", "skel_px", "skel_mm", "mask_px", "width_mean_px",
            "width_mean_mm", "area_fraction", "tortuosity", "tip_x_mm", "tip_y_mm"]
    csv_path = os.path.join(out_dir, "morphology_stats.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved → {csv_path}")

    skel_vals  = [r["skel_px"] for r in rows]
    skel_mm    = [r["skel_mm"] for r in rows]
    w_vals     = [float(r["width_mean_px"]) for r in rows if r["width_mean_px"] != ""]
    w_mm       = [float(r["width_mean_mm"]) for r in rows if r["width_mean_mm"] != ""]
    t_vals     = [float(r["tortuosity"])    for r in rows if r["tortuosity"] != ""]
    af         = [r["area_fraction"] for r in rows]

    print("\n── PIDL morphology summary (Umax={}) ──".format(umax))
    print(f"  Crack length (skeleton): {min(skel_vals)}–{max(skel_vals)} px  "
          f"= {min(skel_mm):.3f}–{max(skel_mm):.3f} mm")
    print(f"  Mean crack width:        {min(w_vals):.1f}–{max(w_vals):.1f} px  "
          f"= {min(w_mm):.4f}–{max(w_mm):.4f} mm")
    print(f"  Tortuosity:              {min(t_vals):.3f}–{max(t_vals):.3f}  (1.0 = straight)")
    print(f"  Area fraction:           {min(af):.5f}–{max(af):.5f}")
    print("─" * 55)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--umax", default="0.08")
    args = parser.parse_args()
    run(umax=args.umax)
