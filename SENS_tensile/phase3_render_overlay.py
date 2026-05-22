"""
Phase 3 Step B (Route A): FEM d(x,y) → composite crack photo
Loads FEM .mat files directly — no PNG intermediary for skeleton.

Pipeline:
  FEM d_elem (.mat) → grid → threshold → skeleton → dilate → blend onto texture

Output:
  phase3_output/fem/rendered_{surface}_u{UU}_cycle_{CCCC}.png
  phase3_output/fem/composite_{surface}_u{UU}.png

Usage:
  python phase3_render_overlay.py           # all cases
  python phase3_render_overlay.py --umax 12
"""

import argparse, os, glob
import numpy as np
import scipy.io as sio
from scipy.interpolate import griddata
from scipy.ndimage import binary_closing
from skimage.morphology import skeletonize
from PIL import Image
import cv2

HANDOFF  = os.path.expanduser("~/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent")
D_THRESH = 0.5
GRID_RES = 512
DOMAIN   = (-0.5, 0.5)

_mesh_cache = None

def load_mesh():
    global _mesh_cache
    if _mesh_cache is None:
        mat = sio.loadmat(os.path.join(HANDOFF, "mesh_geometry.mat"))
        xy  = mat["element_centroids"].astype(np.float32)
        _mesh_cache = xy[:, 0], xy[:, 1]
    return _mesh_cache


def fem_to_skeleton(ustr, cycle):
    """Load FEM .mat → binary skeleton (512×512 uint8 array, 1=crack)."""
    x, y = load_mesh()
    mat  = sio.loadmat(os.path.join(HANDOFF, f"u{ustr}_cycle_{cycle:04d}.mat"))
    d    = mat["d_elem"].ravel().astype(np.float32)

    xi  = np.linspace(DOMAIN[0], DOMAIN[1], GRID_RES)
    yi  = np.linspace(DOMAIN[0], DOMAIN[1], GRID_RES)
    xi2d, yi2d = np.meshgrid(xi, yi)
    grid = griddata((x, y), d, (xi2d, yi2d), method="linear", fill_value=0.0)
    grid = np.clip(grid, 0.0, None)

    mask = (grid > D_THRESH).astype(np.uint8)
    mask = binary_closing(mask, iterations=2).astype(np.uint8)
    skel = skeletonize(mask.astype(bool)).astype(np.uint8)
    return skel, mask


def make_texture(kind="concrete", size=GRID_RES, seed=42):
    rng  = np.random.default_rng(seed)
    if kind == "concrete":
        base = rng.integers(65, 105, (size, size), dtype=np.uint8)
        amps = [(4, 30), (8, 20), (16, 12)]
        tint = (0.95, 0.97, 1.02)
    else:
        base = rng.integers(25, 55, (size, size), dtype=np.uint8)
        amps = [(4, 25), (8, 15), (16, 10)]
        tint = (1.0, 1.0, 1.0)

    for scale, amp in amps:
        s   = rng.integers(0, 255, (size // scale, size // scale)).astype(np.float32)
        up  = cv2.resize(s, (size, size), interpolation=cv2.INTER_LINEAR)
        base = np.clip(base.astype(np.float32) + up * amp / 255, 0, 255).astype(np.uint8)

    channels = [np.clip(base.astype(np.float32) * t, 0, 255).astype(np.uint8) for t in tint]
    return Image.fromarray(np.stack(channels, axis=2))


def render(bg_img, skel, crack_w_px=5, darkness=0.30):
    """Blend dilated crack skeleton onto background texture."""
    kernel  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (crack_w_px, crack_w_px))
    dilated = cv2.dilate(skel, kernel, iterations=1).astype(np.float32)
    smooth  = cv2.GaussianBlur(dilated, (0, 0), sigmaX=1.2).clip(0, 1)

    bg  = np.array(bg_img, dtype=np.float32)
    m3  = smooth[..., None]
    rng = np.random.default_rng(7)
    noise = rng.standard_normal(bg.shape).astype(np.float32) * 4
    result = bg * (1 - m3 * darkness) + noise * m3
    return Image.fromarray(result.clip(0, 255).astype(np.uint8))


def run(umax_filter=None):
    mat_files = sorted(glob.glob(os.path.join(HANDOFF, "u??_cycle_????.mat")))
    cases = []
    for p in mat_files:
        fn   = os.path.basename(p)
        ustr = fn[1:3]
        cyc  = int(fn.split("_cycle_")[1].replace(".mat", ""))
        if umax_filter and ustr != umax_filter.zfill(2):
            continue
        cases.append((ustr, cyc))

    base    = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "..", "phase3_output", "fem")
    os.makedirs(out_dir, exist_ok=True)

    textures = {k: make_texture(k) for k in ("concrete", "asphalt")}

    groups = {}
    for ustr, cyc in cases:
        groups.setdefault(ustr, []).append(cyc)

    for ustr, cycles in sorted(groups.items()):
        renders = {k: [] for k in textures}
        for cyc in sorted(cycles):
            print(f"  u={ustr} N={cyc:04d} ...", end=" ", flush=True)
            skel, mask = fem_to_skeleton(ustr, cyc)
            skel_px    = int(skel.sum())
            if skel_px == 0:
                print("no crack, skip")
                continue
            # crack width scales with crack length (longer crack → slightly wider opening)
            w_px = max(4, min(10, int(skel_px / 30)))
            print(f"skel={skel_px}px  w={w_px}px")

            for kind, bg in textures.items():
                img = render(bg, skel, crack_w_px=w_px, darkness=0.35)
                path = os.path.join(out_dir, f"rendered_{kind}_u{ustr}_cycle_{cyc:04d}.png")
                img.save(path)
                renders[kind].append(img)

        # composite strip per Umax
        for kind, imgs in renders.items():
            if not imgs:
                continue
            n     = len(imgs)
            strip = Image.new("RGB", (GRID_RES * n, GRID_RES), (180, 180, 180))
            for j, im in enumerate(imgs):
                strip.paste(im, (j * GRID_RES, 0))
            sp = os.path.join(out_dir, f"composite_{kind}_u{ustr}.png")
            strip.save(sp)
            print(f"  strip → {sp}")

    print("Done.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--umax", default=None)
    args = p.parse_args()
    run(umax_filter=args.umax)
