"""
Phase 3 Step 1 pilot: phase-field α(x,y) → binary crack mask → skeleton

Pipeline:
  α(x,y) scattered points
    → interpolate to regular grid
    → threshold → binary mask
    → skeletonize → crack centerline
    → save panel figure (α field | mask | skeleton)

Usage:
  python phase3_crack_image_pipeline.py                  # default: Umax=0.08 all cycles
  python phase3_crack_image_pipeline.py --umax 0.12      # choose experiment
  python phase3_crack_image_pipeline.py --cycle 349      # single cycle
  python phase3_crack_image_pipeline.py --gif            # also write animated gif

Output:
  phase3_output/
    panel_cycle_XXXX.png   — 4-panel figure per timestep
    skeleton_cycle_XXXX.png — skeleton only (for downstream diffusion conditioning)
    summary_strip.png      — 5-column evolution strip
    crack_evolution.gif    — (optional)
"""

import argparse
import os
import glob
import numpy as np
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter, binary_dilation, binary_closing
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# ── optional: skimage for morphological skeleton ──────────────────────────────
try:
    from skimage.morphology import skeletonize, binary_closing as sk_closing
    HAS_SKIMAGE = True
except ImportError:
    HAS_SKIMAGE = False
    print("[warn] scikit-image not found — skeleton step will use simple erosion fallback")

# ── config ────────────────────────────────────────────────────────────────────
ALPHA_T   = 0.5          # toy Phase-1 fatigue threshold
THRESHOLD = 0.5          # fraction of α_T above which a pixel is "cracked"
                         # so crack mask = α > THRESHOLD * ALPHA_T = 0.25
GRID_RES  = 512          # output image size (pixels)
DOMAIN    = (-0.5, 0.5)  # domain extent in x and y

# ── helpers ───────────────────────────────────────────────────────────────────

def load_alpha(path):
    """Load .npy → (N,3) [x, y, α] and return x, y, α arrays."""
    data = np.load(path).astype(np.float32)
    return data[:, 0], data[:, 1], data[:, 2]


def to_grid(x, y, vals, res=GRID_RES):
    """Scattered (x,y,vals) → regular grid via linear interpolation."""
    xi = np.linspace(DOMAIN[0], DOMAIN[1], res)
    yi = np.linspace(DOMAIN[0], DOMAIN[1], res)
    xi2d, yi2d = np.meshgrid(xi, yi)
    grid = griddata((x, y), vals, (xi2d, yi2d), method="linear", fill_value=0.0)
    return np.clip(grid, 0.0, None)   # α ≥ 0


def alpha_to_mask(grid_alpha, threshold_abs):
    """Continuous α field → binary crack mask."""
    mask = (grid_alpha > threshold_abs).astype(np.uint8)
    # small closing to fill isolated interior holes
    mask = binary_closing(mask, iterations=2).astype(np.uint8)
    return mask


def mask_to_skeleton(mask):
    """Binary mask → 1-pixel-wide skeleton (crack centreline)."""
    if HAS_SKIMAGE:
        return skeletonize(mask.astype(bool)).astype(np.uint8)
    else:
        # fallback: iterative erosion until thin
        from scipy.ndimage import binary_erosion
        skel = np.zeros_like(mask)
        tmp  = mask.copy().astype(bool)
        while tmp.any():
            eroded = binary_erosion(tmp)
            skel  |= (tmp & ~eroded)
            tmp    = eroded
        return skel.astype(np.uint8)


def make_panel(grid_alpha, mask, skeleton, cycle, alpha_t=ALPHA_T, out_path=None):
    """4-panel figure: α field | normalised α | binary mask | skeleton."""
    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    extent = [DOMAIN[0], DOMAIN[1], DOMAIN[0], DOMAIN[1]]

    # panel 1 — raw α field
    im0 = axes[0].imshow(grid_alpha, origin="lower", extent=extent,
                         cmap="hot_r", vmin=0, vmax=alpha_t * 20)
    fig.colorbar(im0, ax=axes[0], fraction=0.046)
    axes[0].set_title(f"α field  (cycle {cycle})")

    # panel 2 — normalised α / α_T (log scale helps see subcritical accumulation)
    ratio = grid_alpha / alpha_t
    ratio_log = np.log10(np.clip(ratio, 1e-4, None))
    im1 = axes[1].imshow(ratio_log, origin="lower", extent=extent,
                         cmap="viridis", vmin=-2, vmax=2)
    fig.colorbar(im1, ax=axes[1], fraction=0.046, label="log10(α/α_T)")
    axes[1].set_title("log₁₀(α / α_T)")

    # panel 3 — binary crack mask
    axes[2].imshow(mask, origin="lower", extent=extent,
                   cmap="Greys", vmin=0, vmax=1)
    axes[2].set_title(f"Binary mask  (α > {THRESHOLD}·α_T)")

    # panel 4 — skeleton overlaid on mask
    axes[3].imshow(mask, origin="lower", extent=extent,
                   cmap="Greys", vmin=0, vmax=1, alpha=0.4)
    # overlay skeleton in red
    skel_rgba = np.zeros((*skeleton.shape, 4))
    skel_rgba[skeleton > 0] = [1, 0, 0, 1]
    axes[3].imshow(skel_rgba, origin="lower", extent=extent)
    axes[3].set_title("Skeleton (crack centreline)")

    for ax in axes:
        ax.set_xlabel("x [mm]")
        ax.set_ylabel("y [mm]")

    plt.tight_layout()
    if out_path:
        plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def make_skeleton_png(skeleton, out_path):
    """Save skeleton-only PNG (white on black) for downstream conditioning."""
    fig, ax = plt.subplots(figsize=(4, 4))
    extent = [DOMAIN[0], DOMAIN[1], DOMAIN[0], DOMAIN[1]]
    ax.imshow(1 - skeleton, origin="lower", extent=extent, cmap="Greys", vmin=0, vmax=1)
    ax.axis("off")
    plt.tight_layout(pad=0)
    plt.savefig(out_path, dpi=120, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


def make_summary_strip(panel_paths, out_path):
    """5-column strip from evenly-spaced panel PNGs."""
    from PIL import Image
    indices = np.linspace(0, len(panel_paths) - 1, min(5, len(panel_paths)), dtype=int)
    imgs = [Image.open(panel_paths[i]) for i in indices]
    w, h = imgs[0].size
    strip = Image.new("RGB", (w * len(imgs), h), (255, 255, 255))
    for j, im in enumerate(imgs):
        strip.paste(im, (j * w, 0))
    strip.save(out_path)
    print(f"  summary strip → {out_path}")

# ── main ──────────────────────────────────────────────────────────────────────

def run(umax="0.08", cycle=None, make_gif=False):
    # find experiment directory
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
        raise FileNotFoundError(f"No npy files found for Umax={umax}\nPattern: {pattern}")

    if cycle is not None:
        npy_files = [f for f in npy_files if f"alpha_cycle_{int(cycle):04d}.npy" in f]
        if not npy_files:
            raise FileNotFoundError(f"cycle {cycle} not found for Umax={umax}")

    out_dir = os.path.join(base, "..", "phase3_output", f"umax{umax}")
    os.makedirs(out_dir, exist_ok=True)
    print(f"Processing {len(npy_files)} snapshots → {out_dir}")

    threshold_abs = THRESHOLD * ALPHA_T
    panel_paths = []

    for npy_path in npy_files:
        cyc = int(os.path.basename(npy_path).replace("alpha_cycle_", "").replace(".npy", ""))
        print(f"  cycle {cyc:04d} ...", end=" ")

        x, y, alpha = load_alpha(npy_path)
        grid  = to_grid(x, y, alpha)
        mask  = alpha_to_mask(grid, threshold_abs)
        skel  = mask_to_skeleton(mask)

        panel_p = os.path.join(out_dir, f"panel_cycle_{cyc:04d}.png")
        make_panel(grid, mask, skel, cyc, out_path=panel_p)
        panel_paths.append(panel_p)

        skel_p = os.path.join(out_dir, f"skeleton_cycle_{cyc:04d}.png")
        make_skeleton_png(skel, skel_p)

        # quick stats
        crack_px = mask.sum()
        skel_px  = skel.sum()
        print(f"crack_px={crack_px}  skel_px={skel_px}")

    # summary strip
    try:
        make_summary_strip(panel_paths, os.path.join(out_dir, "summary_strip.png"))
    except ImportError:
        print("  [skip] PIL not available — install Pillow for summary strip")

    # animated gif
    if make_gif:
        try:
            from PIL import Image as PILImage
            frames = [PILImage.open(p) for p in panel_paths]
            gif_path = os.path.join(out_dir, "crack_evolution.gif")
            frames[0].save(gif_path, save_all=True, append_images=frames[1:],
                           duration=300, loop=0)
            print(f"  gif → {gif_path}")
        except ImportError:
            print("  [skip] PIL not available — install Pillow for gif")

    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--umax",  default="0.08", help="Umax value string, e.g. 0.08")
    parser.add_argument("--cycle", default=None,   type=int, help="Single cycle to process")
    parser.add_argument("--gif",   action="store_true",      help="Also generate animated gif")
    args = parser.parse_args()
    run(umax=args.umax, cycle=args.cycle, make_gif=args.gif)
