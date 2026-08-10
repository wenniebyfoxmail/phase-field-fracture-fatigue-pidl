#!/usr/bin/env python3
"""Find and review the 1991 outer solid road-grid rectangle before clipping."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np


LATTICE_PATH = Path(__file__).with_name("ltpp_detect_native_lattice_grid_mvp.py")
SPEC = importlib.util.spec_from_file_location("ltpp_native_lattice", LATTICE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load lattice helper: {LATTICE_PATH}")
LATTICE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LATTICE)

STATUS = "EXPLORATORY_SOLID_OUTER_BOUNDARY_REVIEW__NOT_QUALIFIED"
INK_THRESHOLD = 128
BAND_RADIUS_PX = 2
MIN_VERTICAL_CONTINUOUS_FRACTION = 0.25
MIN_HORIZONTAL_CONTINUOUS_FRACTION = 0.25
ROAD_ASPECT_RANGE = (3.0, 3.6)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def longest_run(active: np.ndarray) -> int:
    changes = np.diff(np.r_[False, active, False].astype(np.int8))
    starts, ends = np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)
    return int(np.max(ends - starts)) if len(starts) else 0


def continuous_support_profiles(gray: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ink = gray < INK_THRESHOLD
    vertical = np.array([longest_run(np.mean(ink[:, max(0, x - BAND_RADIUS_PX):x + BAND_RADIUS_PX + 1], axis=1) >= 0.20) for x in range(gray.shape[1])])
    horizontal = np.array([longest_run(np.mean(ink[max(0, y - BAND_RADIUS_PX):y + BAND_RADIUS_PX + 1, :], axis=0) >= 0.20) for y in range(gray.shape[0])])
    return vertical, horizontal


def outer_solid_rectangle(gray: np.ndarray) -> tuple[tuple[int, int, int, int], dict]:
    """Choose the outer solid rectangle enclosing the regular road-grid region."""
    height, width = gray.shape
    vertical, horizontal = continuous_support_profiles(gray)
    x_candidates = np.flatnonzero((vertical >= int(round(MIN_VERTICAL_CONTINUOUS_FRACTION * height))) & (np.arange(width) >= int(0.05 * width)) & (np.arange(width) <= int(0.90 * width)))
    y_candidates = np.flatnonzero((horizontal >= int(round(MIN_HORIZONTAL_CONTINUOUS_FRACTION * width))) & (np.arange(height) >= int(0.05 * height)) & (np.arange(height) <= int(0.95 * height)))
    if len(x_candidates) < 2 or len(y_candidates) < 2:
        raise ValueError("insufficient continuous solid-boundary candidates")
    # Candidate sides may occupy a few adjacent pixels. Keep only extrema after
    # grouping adjacent runs, then choose the aspect-compatible outer pair.
    def groups(points: np.ndarray) -> list[int]:
        chunks = np.split(points, np.flatnonzero(np.diff(points) > 1) + 1)
        return [int(chunk[np.argmax((vertical if points is x_candidates else horizontal)[chunk])]) for chunk in chunks]
    xs, ys = groups(x_candidates), groups(y_candidates)
    options = []
    for left_index, left in enumerate(xs):
        for right in xs[left_index + 1:]:
            for top_index, top in enumerate(ys):
                for bottom in ys[top_index + 1:]:
                    aspect = (right - left) / max(1, bottom - top)
                    if ROAD_ASPECT_RANGE[0] <= aspect <= ROAD_ASPECT_RANGE[1]:
                        support = vertical[left] + vertical[right] + horizontal[top] + horizontal[bottom]
                        area = (right - left) * (bottom - top)
                        options.append((support, area, left, top, right, bottom, aspect))
    if not options:
        raise ValueError("no aspect-compatible solid boundary rectangle")
    _, _, left, top, right, bottom, aspect = max(options)
    return (left, top, right, bottom), {"vertical_continuous_support_px": {"left": int(vertical[left]), "right": int(vertical[right])}, "horizontal_continuous_support_px": {"top": int(horizontal[top]), "bottom": int(horizontal[bottom])}, "aspect": float(aspect)}


def write_manifest(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "manifest.sha256")
    (root / "manifest.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in files), encoding="utf-8")


def run(input_image: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite output: {output}")
    source = cv2.imread(str(input_image), cv2.IMREAD_GRAYSCALE)
    if source is None:
        raise ValueError(f"cannot read {input_image}")
    angle = LATTICE.estimate_deskew(source)
    deskewed = LATTICE.rotate_bound(source, angle)
    rectangle, details = outer_solid_rectangle(deskewed)
    left, top, right, bottom = rectangle
    view = cv2.cvtColor(deskewed, cv2.COLOR_GRAY2BGR)
    cv2.rectangle(view, (left, top), (right, bottom), (0, 140, 255), 5, cv2.LINE_AA)
    for label, point in (("O1", (left, top)), ("O2", (right, top)), ("O3", (right, bottom)), ("O4", (left, bottom))):
        cv2.circle(view, point, 14, (0, 140, 255), -1, cv2.LINE_AA)
        cv2.putText(view, label, (point[0] + 12, point[1] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 140, 255), 2, cv2.LINE_AA)
    header = np.full((95, view.shape[1], 3), 250, dtype=np.uint8)
    cv2.putText(header, "1991 solid outer-boundary review: confirm range before clipping", (18, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (20, 20, 20), 2, cv2.LINE_AA)
    cv2.putText(header, "orange O1-O4 = strongest aspect-compatible outer solid rectangle; no controls shown", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (20, 20, 20), 1, cv2.LINE_AA)
    cv2.putText(header, "Check: does this contain all road-grid/crack content, but no side summary table?", (18, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (20, 20, 20), 1, cv2.LINE_AA)
    output.mkdir(parents=True)
    if not cv2.imwrite(str(output / "1991_solid_outer_boundary_review.png"), np.vstack((header, view))):
        raise ValueError("cannot write review")
    result = {"status": STATUS, "input_sha256": sha256(input_image), "script_sha256": sha256(Path(__file__).resolve()), "deskew_angle_deg": angle, "outer_rectangle_deskewed_px": {"left": left, "top": top, "right": right, "bottom": bottom}, "support": details, "prohibited_claims": ["control_extraction", "registration_transform", "v2_final_gate", "2d_model_authorization"]}
    (output / "outer_boundary_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output / "decision.md").write_text("# 1991 solid outer-boundary review\n\n`EXPLORATORY_SOLID_OUTER_BOUNDARY_REVIEW__NOT_QUALIFIED`\n\nThe orange rectangle comes solely from continuous solid strokes after rotation. Human range confirmation is required before clipping or control extraction.\n", encoding="utf-8")
    write_manifest(output)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-image", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.input_image.resolve(), args.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
