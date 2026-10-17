#!/usr/bin/env python3
"""Generate the frozen S02-E002 G1 analytic image fixture.

This module verifies construction of a camera-like observation.  It does not
contain an image estimator and must not be used to claim crack recoverability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


HEIGHT = 128
WIDTH = 128
TEXTURE_SEEDS = (1701, 1702)
START_X = 32.0
TIP_X = 96.0
SLIT_Y = 64.0

CASES: tuple[dict[str, Any], ...] = (
    {"case": "zero", "kind": "affine", "matrix": [[1.0, 0.0], [0.0, 1.0]], "offset": [0.0, 0.0], "status": "closed"},
    {"case": "translation", "kind": "affine", "matrix": [[1.0, 0.0], [0.0, 1.0]], "offset": [3.0, -2.0], "status": "closed"},
    {"case": "affine_strain", "kind": "affine", "matrix": [[1.02, 0.01], [0.0, 0.98]], "offset": [-1.0, 1.0], "status": "closed"},
    {"case": "opening_2px", "kind": "slit", "opening_px": 2.0, "status": "resolved"},
    {"case": "opening_4px", "kind": "slit", "opening_px": 4.0, "status": "resolved"},
    {"case": "closed_slit", "kind": "slit", "opening_px": 0.0, "status": "closed"},
    {"case": "opening_0p25px", "kind": "slit", "opening_px": 0.25, "status": "ambiguous"},
)

MANIFEST_FIELDS = (
    "trajectory_id", "lineage_id", "simulator", "simulator_version",
    "state_id", "state_order", "coordinate_name", "coordinate_value", "units",
    "displacement_path", "geometry_path", "image_path", "image_label_path",
    "reference_texture_id", "renderer_config_id", "camera_config_id",
    "load_available_by_state", "reaction_available_by_state", "event_rule_id",
    "event_first_detect", "censored", "censor_state", "split_group", "split",
    "provenance",
)


def make_reference_texture(seed: int, height: int = HEIGHT, width: int = WIDTH) -> np.ndarray:
    """Return a temporally fixed, deterministic uint8 speckle texture."""
    rng = np.random.default_rng(seed)
    base = rng.normal(127.0, 38.0, size=(height, width))
    # Add low-frequency material contrast without external filtering libraries.
    coarse = rng.normal(0.0, 14.0, size=(height // 8 + 1, width // 8 + 1))
    low = np.repeat(np.repeat(coarse, 8, axis=0), 8, axis=1)[:height, :width]
    return np.clip(np.rint(base + low), 0, 255).astype(np.uint8)


def inverse_affine_coordinates(
    matrix: np.ndarray, offset: np.ndarray, height: int = HEIGHT, width: int = WIDTH
) -> tuple[np.ndarray, np.ndarray]:
    """Map output pixel centres to source coordinates for x'=A x+b."""
    yy, xx = np.indices((height, width), dtype=np.float64)
    target = np.stack((xx.ravel(), yy.ravel()), axis=0)
    source = np.linalg.solve(np.asarray(matrix, dtype=np.float64), target - np.asarray(offset, dtype=np.float64)[:, None])
    return source[0].reshape(height, width), source[1].reshape(height, width)


def bilinear_sample(image: np.ndarray, source_x: np.ndarray, source_y: np.ndarray) -> np.ndarray:
    """Sample a grayscale image with one frozen edge-replication policy."""
    h, w = image.shape
    clipped_x = np.clip(source_x, 0.0, float(w - 1))
    clipped_y = np.clip(source_y, 0.0, float(h - 1))
    x0 = np.floor(clipped_x).astype(np.int64)
    y0 = np.floor(clipped_y).astype(np.int64)
    x1 = np.minimum(x0 + 1, w - 1)
    y1 = np.minimum(y0 + 1, h - 1)
    wx = clipped_x - x0
    wy = clipped_y - y0
    out = (
        image[y0, x0] * (1.0 - wx) * (1.0 - wy)
        + image[y0, x1] * wx * (1.0 - wy)
        + image[y1, x0] * (1.0 - wx) * wy
        + image[y1, x1] * wx * wy
    )
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def rasterise_slit_support(opening_px: float) -> np.ndarray:
    """Return fractional pixel coverage for the prescribed horizontal slit."""
    yy, xx = np.indices((HEIGHT, WIDTH), dtype=np.float64)
    x_centres = xx + 0.5
    y_centres = yy + 0.5
    horizontal = (x_centres >= START_X) & (x_centres < TIP_X)
    half = opening_px / 2.0
    vertical = np.clip(half + 0.5 - np.abs(y_centres - SLIT_Y), 0.0, 1.0)
    return horizontal.astype(np.float64) * vertical


def render_case(
    texture: np.ndarray,
    case: dict[str, Any],
    *,
    inert_metadata: dict[str, Any] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Render one analytic case and return image plus optical support.

    ``inert_metadata`` is accepted only to make the pre-render independence
    intervention test explicit.  It is deliberately outside the rendering
    inputs and cannot affect coordinates, support or pixels.
    """
    del inert_metadata
    support = np.zeros_like(texture, dtype=np.float64)
    if case["kind"] == "affine":
        sx, sy = inverse_affine_coordinates(np.asarray(case["matrix"]), np.asarray(case["offset"]))
        return bilinear_sample(texture, sx, sy), support

    opening = float(case["opening_px"])
    yy, xx = np.indices(texture.shape, dtype=np.float64)
    active_x = (xx + 0.5 >= START_X) & (xx + 0.5 < TIP_X)
    # The two faces separate symmetrically.  This is a prescribed construction,
    # not an inferred opening or an image-based measurement.  The imposed
    # displacement is compactly supported around the slit so its endpoints are
    # not copied onto a far image border.
    source_y = yy.copy()
    local_band = np.abs(yy + 0.5 - SLIT_Y) <= 8.0
    source_y[active_x & local_band & (yy + 0.5 < SLIT_Y)] += opening / 2.0
    source_y[active_x & local_band & (yy + 0.5 >= SLIT_Y)] -= opening / 2.0
    warped = bilinear_sample(texture, xx, source_y)
    support = rasterise_slit_support(opening)
    image = np.rint(warped.astype(np.float64) * (1.0 - support)).astype(np.uint8)
    return image, support


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def generate_fixture(output_dir: Path) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in ("images", "mechanics", "geometry", "optical_support", "textures"):
        (output_dir / name).mkdir(exist_ok=True)

    manifest: list[dict[str, Any]] = []
    trajectory_id = "analytic-straight-slit-v1"
    lineage_id = "analytic-straight-slit-lineage-v1"
    for seed in TEXTURE_SEEDS:
        texture = make_reference_texture(seed)
        texture_path = output_dir / "textures" / f"texture_{seed}.png"
        Image.fromarray(texture, mode="L").save(texture_path, optimize=False, compress_level=9)
        for order, case in enumerate(CASES):
            render_id = f"seed{seed}_{case['case']}"
            image, support = render_case(texture, case)
            image_path = output_dir / "images" / f"{render_id}.png"
            mechanics_path = output_dir / "mechanics" / f"{case['case']}.json"
            geometry_path = output_dir / "geometry" / f"{case['case']}.json"
            support_path = output_dir / "optical_support" / f"{render_id}.npy"
            Image.fromarray(image, mode="L").save(image_path, optimize=False, compress_level=9)
            np.save(support_path, support, allow_pickle=False)
            if not mechanics_path.exists():
                _write_json(mechanics_path, {"case": case["case"], "kind": case["kind"], "matrix": case.get("matrix"), "offset_px": case.get("offset"), "opening_px": case.get("opening_px"), "coordinate_calibration": "1 synthetic unit per pixel"})
                _write_json(geometry_path, {"centreline_start_px": [START_X, SLIT_Y], "tip_px": [TIP_X, SLIT_Y], "length_px": TIP_X - START_X, "opening_px": case.get("opening_px", 0.0), "target_status": case["status"]})
            relative = lambda p: str(p.relative_to(output_dir))
            record = {
                "trajectory_id": trajectory_id,
                "lineage_id": lineage_id,
                "render_id": render_id,
                "simulator": "analytic_prescribed_field",
                "simulator_version": "S02-E002-G1-v0.2",
                "state_id": case["case"],
                "state_order": order,
                "coordinate_name": "analytic_case_index",
                "coordinate_value": order,
                "units": {"length": "synthetic_px", "displacement": "synthetic_px"},
                "displacement_path": relative(mechanics_path),
                "geometry_path": relative(geometry_path),
                "image_path": relative(image_path),
                "image_label_path": relative(support_path),
                "reference_texture_id": f"texture_{seed}",
                "renderer_config_id": "analytic_renderer_v0.2",
                "camera_config_id": "orthographic_128_no_effects_v0.2",
                "target_status": case["status"],
                "load_available_by_state": False,
                "reaction_available_by_state": False,
                "event_rule_id": "not_applicable_g1",
                "event_first_detect": None,
                "censored": False,
                "censor_state": None,
                "split_group": lineage_id,
                "split": "verification_only",
                "provenance": "S02-E002 v0.2 prescribed analytic fixture",
                "image_sha256": _sha256(image_path),
            }
            manifest.append(record)
    _write_json(output_dir / "manifest.json", manifest)
    _write_json(output_dir / "renderer_config.json", {"height": HEIGHT, "width": WIDTH, "texture_seeds": list(TEXTURE_SEEDS), "frame_count": len(manifest), "camera": "orthographic", "camera_effects": "disabled", "cases": list(CASES)})
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = generate_fixture(args.output_dir)
    print(json.dumps({"status": "generated", "frames": len(manifest), "output_dir": str(args.output_dir)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
