#!/usr/bin/env python3
"""Render 1991 inner versus outer printed-frame candidates; no registration."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import cv2
import numpy as np


TWIST_PATH = Path(__file__).with_name("ltpp_preview_1991_projective_rectification.py")
SPEC = importlib.util.spec_from_file_location("ltpp_1991_twist", TWIST_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load frame-preview code: {TWIST_PATH}")
TWIST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TWIST)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def outer_frame_corners(gray: np.ndarray) -> np.ndarray:
    """Choose the outermost long solid frame candidates that span the grid."""
    height, width = gray.shape
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 1800.0, threshold=max(45, width // 35), minLineLength=max(250, width // 12), maxLineGap=max(20, width // 50))
    if lines is None:
        raise ValueError("no outer-frame Hough candidates")
    vertical, horizontal = [], []
    for segment in lines[:, 0, :]:
        x1, y1, x2, y2 = map(float, segment)
        length = math.hypot(x2 - x1, y2 - y1)
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        mid_x, mid_y = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        if length >= 0.45 * height and abs(abs(angle) - 90.0) <= 10.0 and 0.04 * width <= mid_x <= 0.90 * width:
            vertical.append((mid_x, length, segment.astype(float)))
        if length >= 0.45 * width and abs(angle) <= 10.0 and 0.04 * height <= mid_y <= 0.95 * height:
            horizontal.append((mid_y, length, segment.astype(float)))
    if len(vertical) < 2:
        raise ValueError("insufficient outer vertical candidates")
    left_x, right_x = min(row[0] for row in vertical), max(row[0] for row in vertical)
    left = max((row for row in vertical if row[0] <= left_x + 0.02 * width), key=lambda row: row[1])[2]
    right = max((row for row in vertical if row[0] >= right_x - 0.02 * width), key=lambda row: row[1])[2]
    span = right_x - left_x
    full_width = []
    for mid_y, length, segment in horizontal:
        lo, hi = sorted((segment[0], segment[2]))
        if length >= 0.88 * span and lo <= left_x + 0.04 * width and hi >= right_x - 0.04 * width:
            full_width.append((mid_y, length, segment))
    if len(full_width) < 2:
        raise ValueError("insufficient outer horizontal candidates")
    top_y, bottom_y = min(row[0] for row in full_width), max(row[0] for row in full_width)
    top = max((row for row in full_width if row[0] <= top_y + 0.02 * height), key=lambda row: row[1])[2]
    bottom = max((row for row in full_width if row[0] >= bottom_y - 0.02 * height), key=lambda row: row[1])[2]
    top_line, bottom_line, left_line, right_line = map(TWIST.line_homogeneous, (top, bottom, left, right))
    return np.array([TWIST.intersection(top_line, left_line), TWIST.intersection(top_line, right_line), TWIST.intersection(bottom_line, right_line), TWIST.intersection(bottom_line, left_line)], dtype=np.float32)


def draw_polygon(image: np.ndarray, corners: np.ndarray, colour: tuple[int, int, int], prefix: str) -> None:
    cv2.polylines(image, [corners.astype(int)], True, colour, 5, cv2.LINE_AA)
    for index, point in enumerate(corners.astype(int), 1):
        cv2.circle(image, tuple(point), 13, colour, -1, cv2.LINE_AA)
        cv2.putText(image, f"{prefix}{index}", tuple(point + (12, -12)), cv2.FONT_HERSHEY_SIMPLEX, 0.65, colour, 2, cv2.LINE_AA)


def write_manifest(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "manifest.sha256")
    (root / "manifest.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in files), encoding="utf-8")


def run(input_image: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite output: {output}")
    gray = cv2.imread(str(input_image), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise ValueError(f"cannot read {input_image}")
    inner, outer = TWIST.frame_corners(gray), outer_frame_corners(gray)
    canvas = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    draw_polygon(canvas, inner, (255, 0, 255), "I")
    draw_polygon(canvas, outer, (0, 140, 255), "O")
    header = np.full((102, canvas.shape[1], 3), 250, dtype=np.uint8)
    cv2.putText(header, "1991 road-frame range review: no points, no registration", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (20, 20, 20), 2, cv2.LINE_AA)
    cv2.putText(header, "purple I1-I4 = prior inner frame; orange O1-O4 = outer long-solid-line candidate", (18, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.53, (20, 20, 20), 1, cv2.LINE_AA)
    cv2.putText(header, "choose the polygon that includes all road-grid content/cracks but excludes side summary tables", (18, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.53, (20, 20, 20), 1, cv2.LINE_AA)
    output.mkdir(parents=True)
    if not cv2.imwrite(str(output / "1991_frame_range_candidates.png"), np.vstack((header, canvas))):
        raise ValueError("cannot write candidate review")
    result = {"status": "EXPLORATORY_FRAME_RANGE_REVIEW__NOT_QUALIFIED", "input_sha256": sha256(input_image), "script_sha256": sha256(Path(__file__).resolve()), "inner_corners_px": inner.tolist(), "outer_corners_px": outer.tolist(), "prohibited_claims": ["control_extraction", "registration_transform", "v2_final_gate", "2d_model_authorization"]}
    (output / "frame_range_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output / "decision.md").write_text("# 1991 frame-range review\n\n`EXPLORATORY_FRAME_RANGE_REVIEW__NOT_QUALIFIED`\n\nThis compares two source-page frame candidates using only long solid printed strokes. It requests human confirmation of the valid road-map extent before any control extraction.\n", encoding="utf-8")
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
