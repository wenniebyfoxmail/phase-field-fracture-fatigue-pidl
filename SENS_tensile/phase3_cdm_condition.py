"""
Phase 3 Step 1b: prepare CDM-ready condition images.

Pipeline:
  FEM .mat → d-grid → binary mask → DILATE → crop to bbox + pad → rescale 512×512
  Output: white crack on black background, matching CRACK500 area-fraction 0.5-2%.

Why:
  Phase 3 v1 (skeleton-only) gave CDM a 0.095% area-fraction condition,
  way below CRACK500's 0.3-3%. CDM had no useful signal and output a
  near-empty image. Fix: dilate to ~8 px width, then crop+rescale so the
  crack fills the frame the way CRACK500 cracks do.

Usage:
  python phase3_cdm_condition.py --umax 12 --cycle 82
  python phase3_cdm_condition.py --all
"""

import argparse, os, glob
import numpy as np
import scipy.io as sio
from scipy.interpolate import griddata
from scipy.ndimage import binary_closing, binary_dilation
from PIL import Image

HANDOFF  = os.path.expanduser("~/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent")
D_THRESH = 0.5
GRID_RES = 512
DOMAIN   = (-0.5, 0.5)

# Tuning knobs --- target CRACK500-like distribution
DILATE_ITERS = 4         # mask width 5-6 px → ~13-14 px after 4 iters
PADDING_FRAC = 0.12      # 12% padding around bbox before rescale
TARGET_RES   = 512       # CDM resolution


def load_mesh():
    mat = sio.loadmat(os.path.join(HANDOFF, "mesh_geometry.mat"))
    xy  = mat["element_centroids"].astype(np.float32)
    return xy[:, 0], xy[:, 1]


def load_d(umax_str, cycle):
    path = os.path.join(HANDOFF, f"u{umax_str}_cycle_{cycle:04d}.mat")
    mat  = sio.loadmat(path)
    return mat["d_elem"].ravel().astype(np.float32)


def d_to_mask(x, y, d, res=GRID_RES):
    xi = np.linspace(DOMAIN[0], DOMAIN[1], res)
    yi = np.linspace(DOMAIN[0], DOMAIN[1], res)
    xi2d, yi2d = np.meshgrid(xi, yi)
    grid = griddata((x, y), d, (xi2d, yi2d), method="linear", fill_value=0.0)
    mask = (grid > D_THRESH).astype(np.uint8)
    return binary_closing(mask, iterations=2).astype(np.uint8)


def crop_to_bbox(mask, pad_frac=PADDING_FRAC):
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return mask  # nothing to crop
    y0, y1 = ys.min(), ys.max()
    x0, x1 = xs.min(), xs.max()
    h, w   = y1 - y0 + 1, x1 - x0 + 1
    # keep aspect square: pad to max(h,w)
    side = max(h, w)
    cy   = (y0 + y1) / 2
    cx   = (x0 + x1) / 2
    pad  = int(side * (1 + 2 * pad_frac))
    half = pad // 2
    y0n  = max(0, int(cy - half))
    y1n  = min(mask.shape[0], int(cy + half))
    x0n  = max(0, int(cx - half))
    x1n  = min(mask.shape[1], int(cx + half))
    return mask[y0n:y1n, x0n:x1n]


def mask_to_cdm_png(mask, out_path, target_res=TARGET_RES,
                    dilate_iters=DILATE_ITERS, do_crop=True):
    # 1) dilate to thicken
    if dilate_iters > 0:
        mask = binary_dilation(mask.astype(bool),
                                iterations=dilate_iters).astype(np.uint8)
    # 2) crop+rescale to fill frame
    if do_crop:
        mask = crop_to_bbox(mask)
    # 3) resize to target_res (nearest-neighbor preserves binary)
    pil = Image.fromarray((mask * 255).astype(np.uint8), mode="L")
    pil = pil.resize((target_res, target_res), Image.NEAREST)
    # 4) save as 3-channel RGB (CDM expects 3-ch)
    rgb = Image.merge("RGB", (pil, pil, pil))
    rgb.save(out_path)
    # stats
    arr = np.array(pil)
    area_frac = (arr > 127).sum() / (target_res * target_res)
    return area_frac


def run_one(umax_str, cycle, out_dir):
    x, y = load_mesh()
    d    = load_d(umax_str, cycle)
    mask = d_to_mask(x, y, d)
    out  = os.path.join(out_dir, f"cdm_cond_u{umax_str}_cycle_{cycle:04d}.png")
    af   = mask_to_cdm_png(mask, out)
    print(f"  u={umax_str} cycle={cycle:04d}: area_frac={af*100:.2f}%  →  {out}")
    return out, af


def run_all(out_dir):
    files = sorted(glob.glob(os.path.join(HANDOFF, "u??_cycle_????.mat")))
    for p in files:
        fn   = os.path.basename(p)
        ustr = fn[1:3]
        cyc  = int(fn.split("_cycle_")[1].replace(".mat", ""))
        run_one(ustr, cyc, out_dir)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--umax", default=None, help="e.g. 12")
    p.add_argument("--cycle", type=int, default=None)
    p.add_argument("--all", action="store_true")
    args = p.parse_args()

    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "..", "phase3_output", "cdm_conditions")
    os.makedirs(out_dir, exist_ok=True)

    if args.all:
        run_all(out_dir)
    elif args.umax and args.cycle is not None:
        run_one(args.umax.zfill(2), args.cycle, out_dir)
    else:
        print("Use --all  OR  --umax 12 --cycle 82")
