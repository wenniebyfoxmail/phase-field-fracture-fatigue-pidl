#!/usr/bin/env python3
"""Non-damage, 1991-only projective-rectification preview; never a final fit."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import cv2
import numpy as np


LATTICE_PATH = Path(__file__).with_name("ltpp_detect_native_lattice_grid_mvp.py")
SPEC = importlib.util.spec_from_file_location("ltpp_native_lattice", LATTICE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load lattice detector: {LATTICE_PATH}")
LATTICE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LATTICE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def line_homogeneous(segment: np.ndarray) -> np.ndarray:
    x1, y1, x2, y2 = map(float, segment)
    return np.cross(np.array([x1, y1, 1.0]), np.array([x2, y2, 1.0]))


def intersection(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    point = np.cross(first, second)
    if abs(point[2]) < 1e-9:
        raise ValueError("parallel frame lines")
    return point[:2] / point[2]


def frame_corners(gray: np.ndarray) -> np.ndarray:
    """Derive four page-grid frame corners from long printed frame strokes."""
    height, width = gray.shape
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 1800.0, threshold=max(80, width // 24), minLineLength=max(280, width // 6), maxLineGap=max(20, width // 70))
    if lines is None:
        raise ValueError("no Hough frame candidates")
    vertical, horizontal = [], []
    for segment in lines[:, 0, :]:
        x1, y1, x2, y2 = map(float, segment)
        length = math.hypot(x2 - x1, y2 - y1)
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        mid_x, mid_y = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        if length >= 0.50 * height and abs(abs(angle) - 90.0) <= 8.0 and 0.04 * width <= mid_x <= 0.88 * width:
            vertical.append((mid_x, length, segment.astype(float)))
        if length >= 0.60 * width and abs(angle) <= 8.0 and 0.04 * height <= mid_y <= 0.95 * height:
            horizontal.append((mid_y, length, segment.astype(float)))
    if len(vertical) < 2:
        raise ValueError("insufficient vertical frame candidates")
    left_x, right_x = min(row[0] for row in vertical), max(row[0] for row in vertical)
    left = max((row for row in vertical if row[0] <= left_x + 0.02 * width), key=lambda row: row[1])[2]
    right = max((row for row in vertical if row[0] >= right_x - 0.02 * width), key=lambda row: row[1])[2]
    span = right_x - left_x
    full_width = []
    for mid_y, length, segment in horizontal:
        lo, hi = sorted((segment[0], segment[2]))
        if length >= 0.88 * span and lo <= left_x + 0.03 * width and hi >= right_x - 0.03 * width:
            full_width.append((mid_y, length, segment))
    if len(full_width) < 2:
        raise ValueError("insufficient horizontal frame candidates")
    top_y, bottom_y = min(row[0] for row in full_width), max(row[0] for row in full_width)
    top = max((row for row in full_width if row[0] <= top_y + 0.02 * height), key=lambda row: row[1])[2]
    bottom = max((row for row in full_width if row[0] >= bottom_y - 0.02 * height), key=lambda row: row[1])[2]
    top_line, bottom_line, left_line, right_line = map(line_homogeneous, (top, bottom, left, right))
    return np.array([intersection(top_line, left_line), intersection(top_line, right_line), intersection(bottom_line, right_line), intersection(bottom_line, left_line)], dtype=np.float32)


def draw_lattice(image: np.ndarray, evidence: dict) -> np.ndarray:
    view = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    for x in evidence["vertical_lattice"]["positions_px"]:
        cv2.line(view, (x, 0), (x, view.shape[0] - 1), (255, 210, 0), 1, cv2.LINE_AA)
    for y in evidence["horizontal_lattice"]["positions_px"]:
        cv2.line(view, (0, y), (view.shape[1] - 1, y), (255, 210, 0), 1, cv2.LINE_AA)
    for x, y in evidence["intersections_px"]:
        cv2.circle(view, (x, y), 10, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(view, (x, y), 7, (0, 0, 0), -1, cv2.LINE_AA)
        cv2.circle(view, (x, y), 5, (0, 220, 0), -1, cv2.LINE_AA)
    return view


def write_manifest(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "manifest.sha256")
    (root / "manifest.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in files), encoding="utf-8")


def run(input_image: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite output: {output}")
    gray = cv2.imread(str(input_image), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise ValueError(f"cannot read image: {input_image}")
    corners = frame_corners(gray)
    top, right, bottom, left = (np.linalg.norm(corners[1] - corners[0]), np.linalg.norm(corners[2] - corners[1]), np.linalg.norm(corners[2] - corners[3]), np.linalg.norm(corners[3] - corners[0]))
    destination = np.array([[0, 0], [round((top + bottom) / 2), 0], [round((top + bottom) / 2), round((left + right) / 2)], [0, round((left + right) / 2)]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(corners, destination)
    warped = cv2.warpPerspective(gray, matrix, (int(destination[2, 0]) + 1, int(destination[2, 1]) + 1), flags=cv2.INTER_CUBIC, borderValue=255)
    evidence = LATTICE.detect(warped)
    source_marked = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    for point in corners.astype(int):
        cv2.circle(source_marked, tuple(point), 14, (255, 0, 255), -1, cv2.LINE_AA)
    warped_marked = draw_lattice(warped, evidence)
    header_left = np.full((75, source_marked.shape[1], 3), 250, dtype=np.uint8)
    header_right = np.full((75, warped_marked.shape[1], 3), 250, dtype=np.uint8)
    cv2.putText(header_left, "1991 original: magenta = printed page-grid frame corners", (18, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 20), 1, cv2.LINE_AA)
    cv2.putText(header_right, "1991 twist preview: cyan grid family, large green intersections", (18, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 20), 1, cv2.LINE_AA)
    left_panel, right_panel = np.vstack((header_left, source_marked)), np.vstack((header_right, warped_marked))
    height = max(left_panel.shape[0], right_panel.shape[0])
    if left_panel.shape[0] < height:
        left_panel = cv2.copyMakeBorder(left_panel, 0, height - left_panel.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    if right_panel.shape[0] < height:
        right_panel = cv2.copyMakeBorder(right_panel, 0, height - right_panel.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    output.mkdir(parents=True)
    if not cv2.imwrite(str(output / "1991_projective_twist_preview.png"), np.hstack((left_panel, right_panel))):
        raise ValueError("cannot write preview")
    result = {"input_sha256": sha256(input_image), "script_sha256": sha256(Path(__file__).resolve()), "source_frame_corners_px": corners.tolist(), "source_frame_edge_lengths_px": {"top": float(top), "right": float(right), "bottom": float(bottom), "left": float(left)}, "warped_shape": list(warped.shape), "status": "EXPLORATORY_PROJECTIVE_TWIST_PREVIEW__NOT_QUALIFIED"}
    (output / "preview_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output / "decision.md").write_text("# 1991 projective twist preview\n\n`EXPLORATORY_PROJECTIVE_TWIST_PREVIEW__NOT_QUALIFIED`\n\nThis visualization uses only long printed page-grid frame strokes to form a quadrilateral. It is a geometric preview, not a selected registration model, control set, residual audit, or v2 final result.\n", encoding="utf-8")
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
