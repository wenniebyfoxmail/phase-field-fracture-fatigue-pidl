#!/usr/bin/env python3
"""Rectify LTPP hand-drawn distress maps to a shared physical grid.

This script deliberately stops before crack extraction.  Its ``ink`` output
still contains the survey grid, lane boundaries, labels, and distress codes.
Only maps that pass the explicit regular-grid gate are written as qualified
rectified inputs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np


DEFAULT_DATES = (
    "19910610",
    "19951024",
    "19970228",
    "19980407",
    "20010913",
    "20030514",
    "20071106",
    "20120417",
    "20150302",
)
EXPECTED_ASPECT = 15.24 / 5.0
CANONICAL_WIDTH = 1524
CANONICAL_HEIGHT = 500


@dataclass
class GateResult:
    survey_date: str
    source_path: str
    source_sha256: str
    source_width: int
    source_height: int
    deskew_angle_deg: float
    x0: int
    y0: int
    x1: int
    y1: int
    detected_vertical_positions: list[int]
    detected_horizontal_positions: list[int]
    vertical_grid_matches: int
    horizontal_grid_matches: int
    vertical_grid_rmse_px: float
    horizontal_grid_rmse_px: float
    crop_aspect: float
    relative_aspect_error: float
    border_ink_support: float
    qualification_mode: str
    passed: bool
    failure_reasons: list[str]
    rectified_path: str | None
    ink_path: str | None
    overlay_path: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cluster_positions(indices: np.ndarray) -> list[int]:
    if indices.size == 0:
        return []
    groups: list[list[int]] = [[int(indices[0])]]
    for value in indices[1:]:
        value = int(value)
        if value <= groups[-1][-1] + 2:
            groups[-1].append(value)
        else:
            groups.append([value])
    return [int(round(float(np.mean(group)))) for group in groups]


def estimate_deskew(gray: np.ndarray) -> float:
    scale = min(1.0, 2200.0 / gray.shape[1])
    small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    edges = cv2.Canny(small, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 1800.0,
        threshold=max(80, small.shape[1] // 18),
        minLineLength=max(120, small.shape[1] // 5),
        maxLineGap=max(10, small.shape[1] // 80),
    )
    angles: list[float] = []
    if lines is not None:
        for x0, y0, x1, y1 in lines[:, 0, :]:
            angle = math.degrees(math.atan2(float(y1 - y0), float(x1 - x0)))
            while angle <= -90.0:
                angle += 180.0
            while angle > 90.0:
                angle -= 180.0
            if abs(angle) <= 12.0:
                angles.append(angle)
    return float(np.median(angles)) if angles else 0.0


def rotate_bound(image: np.ndarray, angle_deg: float) -> np.ndarray:
    height, width = image.shape[:2]
    center = (width / 2.0, height / 2.0)
    matrix = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    cosine = abs(matrix[0, 0])
    sine = abs(matrix[0, 1])
    new_width = int(math.ceil(height * sine + width * cosine))
    new_height = int(math.ceil(height * cosine + width * sine))
    matrix[0, 2] += new_width / 2.0 - center[0]
    matrix[1, 2] += new_height / 2.0 - center[1]
    return cv2.warpAffine(
        image,
        matrix,
        (new_width, new_height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    )


def line_positions(binary: np.ndarray, axis: str) -> list[int]:
    height, width = binary.shape
    if axis == "vertical":
        connector = cv2.getStructuringElement(
            cv2.MORPH_RECT, (1, max(5, height // 80))
        )
        connected = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, connector)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(35, height // 7)))
        opened = cv2.morphologyEx(connected, cv2.MORPH_OPEN, kernel)
        profile = np.count_nonzero(opened, axis=0)
        threshold = max(20, int(height * 0.22))
    else:
        connector = cv2.getStructuringElement(
            cv2.MORPH_RECT, (max(7, width // 120), 1)
        )
        connected = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, connector)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(80, width // 7), 1))
        opened = cv2.morphologyEx(connected, cv2.MORPH_OPEN, kernel)
        profile = np.count_nonzero(opened, axis=1)
        threshold = max(40, int(width * 0.22))
    return cluster_positions(np.flatnonzero(profile >= threshold))


def score_bounds(
    positions: list[int], expected_count: int, minimum_span: float, full_size: int
) -> list[tuple[float, int, int, int, float]]:
    candidates: list[tuple[float, int, int, int, float]] = []
    for start_index, start in enumerate(positions):
        for end in positions[start_index + 1 :]:
            span = end - start
            if span < full_size * minimum_span:
                continue
            expected = np.linspace(start, end, expected_count)
            tolerance = max(4.0, span / (expected_count - 1) * 0.18)
            residuals = np.array([min(abs(value - p) for p in positions) for value in expected])
            matched = int(np.count_nonzero(residuals <= tolerance))
            rmse = float(np.sqrt(np.mean(np.minimum(residuals, tolerance * 2.0) ** 2)))
            span_reward = span / full_size
            score = matched * 4.0 + span_reward - rmse / max(tolerance, 1.0)
            candidates.append((score, start, end, matched, rmse))
    return sorted(candidates, reverse=True)


def choose_rectangle(
    vertical: list[int], horizontal: list[int], width: int, height: int
) -> tuple[tuple[float, int, int, int, float], tuple[float, int, int, int, float]]:
    x_candidates = score_bounds(vertical, 11, 0.35, width)[:80]
    y_candidates = score_bounds(horizontal, 6, 0.25, height)[:80]
    if not x_candidates or not y_candidates:
        raise ValueError("insufficient regular line candidates")
    best = None
    for x_item in x_candidates:
        for y_item in y_candidates:
            crop_aspect = (x_item[2] - x_item[1]) / max(1.0, y_item[2] - y_item[1])
            aspect_penalty = abs(math.log(max(crop_aspect, 1e-6) / EXPECTED_ASPECT))
            joint_score = x_item[0] + y_item[0] - 14.0 * aspect_penalty
            if best is None or joint_score > best[0]:
                best = (joint_score, x_item, y_item)
    assert best is not None
    return best[1], best[2]


def border_support(binary: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> float:
    pad = max(2, int(round(min(x1 - x0, y1 - y0) * 0.008)))
    strips = (
        binary[max(0, y0 - pad) : min(binary.shape[0], y0 + pad + 1), x0 : x1 + 1],
        binary[max(0, y1 - pad) : min(binary.shape[0], y1 + pad + 1), x0 : x1 + 1],
        binary[y0 : y1 + 1, max(0, x0 - pad) : min(binary.shape[1], x0 + pad + 1)],
        binary[y0 : y1 + 1, max(0, x1 - pad) : min(binary.shape[1], x1 + pad + 1)],
    )
    return float(np.mean([np.count_nonzero(strip) / max(1, strip.size) for strip in strips]))


def process_map(source: Path, output_root: Path) -> GateResult:
    survey_date = source.parent.name
    gray = cv2.imread(str(source), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise ValueError(f"cannot read {source}")
    source_height, source_width = gray.shape
    angle = estimate_deskew(gray)
    deskewed = rotate_bound(gray, angle)
    _, binary = cv2.threshold(deskewed, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    vertical = line_positions(binary, "vertical")
    horizontal = line_positions(binary, "horizontal")

    date_root = output_root / survey_date
    date_root.mkdir(parents=True, exist_ok=True)
    overlay_path = date_root / "grid_detection_overlay.png"
    failure_reasons: list[str] = []
    rectified_relative = None
    ink_relative = None

    try:
        x_item, y_item = choose_rectangle(
            vertical, horizontal, deskewed.shape[1], deskewed.shape[0]
        )
        _, x0, x1, x_matches, x_rmse = x_item
        _, y0, y1, y_matches, y_rmse = y_item
        crop_aspect = (x1 - x0) / max(1.0, y1 - y0)
        aspect_error = abs(crop_aspect - EXPECTED_ASPECT) / EXPECTED_ASPECT
        support = border_support(binary, x0, y0, x1, y1)
        dense_grid_pass = (
            abs(angle) <= 5.0
            and x_matches >= 8
            and y_matches >= 5
            and aspect_error <= 0.20
            and support >= 0.10
        )
        outer_border_pass = (
            abs(angle) <= 5.0
            and x_matches >= 2
            and y_matches >= 5
            and aspect_error <= 0.05
            and support >= 0.25
        )
        if dense_grid_pass:
            qualification_mode = "dense_internal_grid"
        elif outer_border_pass:
            qualification_mode = "outer_border_pair"
        else:
            qualification_mode = "failed"
            if abs(angle) > 5.0:
                failure_reasons.append("deskew_angle_gt_5_deg")
            if x_matches < 8:
                failure_reasons.append("fewer_than_8_of_11_vertical_grid_matches")
            if y_matches < 5:
                failure_reasons.append("fewer_than_5_of_6_horizontal_grid_matches")
            if aspect_error > 0.20:
                failure_reasons.append("relative_grid_aspect_error_gt_0.20")
            if support < 0.10:
                failure_reasons.append("border_ink_support_lt_0.10")
            failure_reasons.append("outer_border_pair_gate_not_satisfied")
        passed = qualification_mode != "failed"

        overlay = cv2.cvtColor(deskewed, cv2.COLOR_GRAY2BGR)
        for x in vertical:
            cv2.line(overlay, (x, 0), (x, overlay.shape[0] - 1), (220, 210, 0), 1)
        for y in horizontal:
            cv2.line(overlay, (0, y), (overlay.shape[1] - 1, y), (220, 210, 0), 1)
        cv2.rectangle(overlay, (x0, y0), (x1, y1), (0, 0, 255), max(3, source_width // 900))
        cv2.putText(
            overlay,
            f"{survey_date} {'PASS' if passed else 'FAIL'} x={x_matches}/11 y={y_matches}/6 aspect_err={aspect_error:.3f}",
            (max(10, x0), max(30, y0 - 15)),
            cv2.FONT_HERSHEY_SIMPLEX,
            max(0.6, source_width / 4200.0),
            (0, 110, 0) if passed else (0, 0, 220),
            2,
            cv2.LINE_AA,
        )
        cv2.imwrite(str(overlay_path), overlay)

        if passed:
            crop = deskewed[y0 : y1 + 1, x0 : x1 + 1]
            rectified = cv2.resize(
                crop, (CANONICAL_WIDTH, CANONICAL_HEIGHT), interpolation=cv2.INTER_AREA
            )
            _, ink = cv2.threshold(
                rectified, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )
            rectified_path = date_root / "rectified_grid.png"
            ink_path = date_root / "rectified_ink_not_crack_mask.png"
            cv2.imwrite(str(rectified_path), rectified)
            cv2.imwrite(str(ink_path), ink)
            rectified_relative = str(rectified_path.relative_to(output_root))
            ink_relative = str(ink_path.relative_to(output_root))
    except ValueError as exc:
        x0 = y0 = x1 = y1 = -1
        x_matches = y_matches = 0
        x_rmse = y_rmse = None
        crop_aspect = aspect_error = support = None
        passed = False
        qualification_mode = "failed"
        failure_reasons.append(str(exc).replace(" ", "_"))
        overlay = cv2.cvtColor(deskewed, cv2.COLOR_GRAY2BGR)
        cv2.putText(
            overlay,
            f"{survey_date} FAIL: no qualified regular grid",
            (20, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 0, 220),
            2,
            cv2.LINE_AA,
        )
        cv2.imwrite(str(overlay_path), overlay)

    return GateResult(
        survey_date=survey_date,
        source_path=str(source),
        source_sha256=sha256(source),
        source_width=source_width,
        source_height=source_height,
        deskew_angle_deg=angle,
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
        detected_vertical_positions=vertical,
        detected_horizontal_positions=horizontal,
        vertical_grid_matches=x_matches,
        horizontal_grid_matches=y_matches,
        vertical_grid_rmse_px=x_rmse,
        horizontal_grid_rmse_px=y_rmse,
        crop_aspect=crop_aspect,
        relative_aspect_error=aspect_error,
        border_ink_support=support,
        qualification_mode=qualification_mode,
        passed=passed,
        failure_reasons=failure_reasons,
        rectified_path=rectified_relative,
        ink_path=ink_relative,
        overlay_path=str(overlay_path.relative_to(output_root)),
    )


def make_contact_sheet(results: list[GateResult], output_root: Path) -> None:
    tiles = []
    for result in results:
        overlay = cv2.imread(str(output_root / result.overlay_path), cv2.IMREAD_COLOR)
        if overlay is None:
            continue
        scale = min(1.0, 640.0 / overlay.shape[1])
        tile = cv2.resize(overlay, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        canvas = np.full((260, 640, 3), 255, dtype=np.uint8)
        height = min(canvas.shape[0], tile.shape[0])
        width = min(canvas.shape[1], tile.shape[1])
        canvas[:height, :width] = tile[:height, :width]
        tiles.append(canvas)
    if tiles:
        columns = 3
        rows = math.ceil(len(tiles) / columns)
        blank = np.full_like(tiles[0], 255)
        tiles.extend([blank] * (rows * columns - len(tiles)))
        sheet = np.vstack([np.hstack(tiles[i : i + columns]) for i in range(0, len(tiles), columns)])
        cv2.imwrite(str(output_root / "grid_gate_contact_sheet.png"), sheet)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--map-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--section", default="06-1253")
    parser.add_argument("--source-filename", default="segment_0_50_white.png")
    parser.add_argument(
        "--dates",
        help="Comma-separated YYYYMMDD dates; default preserves the 06-1253 protocol",
    )
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)

    dates = tuple(args.dates.split(",")) if args.dates else DEFAULT_DATES
    sources = [args.map_root / date / args.source_filename for date in dates]
    missing = [str(path) for path in sources if not path.is_file()]
    if missing:
        raise SystemExit("missing frozen inputs:\n" + "\n".join(missing))

    results = [process_map(source, args.output_root) for source in sources]
    payload = {
        "gate_name": "ltpp_regular_physical_grid_v1",
        "section": args.section,
        "physical_extent_m": [15.24, 5.0],
        "canonical_shape_px": [CANONICAL_HEIGHT, CANONICAL_WIDTH],
        "expected_grid_lines": {"vertical": 11, "horizontal": 6},
        "pass_rule": {
            "dense_internal_grid": {
                "max_abs_deskew_angle_deg": 5.0,
                "min_vertical_matches": 8,
                "min_horizontal_matches": 5,
                "max_relative_aspect_error": 0.20,
                "min_border_ink_support": 0.10,
            },
            "outer_border_pair": {
                "max_abs_deskew_angle_deg": 5.0,
                "min_vertical_matches": 2,
                "min_horizontal_matches": 5,
                "max_relative_aspect_error": 0.05,
                "min_border_ink_support": 0.25,
            },
        },
        "semantic_boundary": "ink outputs are not crack masks",
        "passed": sum(result.passed for result in results),
        "total": len(results),
        "all_passed": all(result.passed for result in results),
        "results": [asdict(result) for result in results],
    }
    with (args.output_root / "grid_gate_results.json").open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)

    fieldnames = list(asdict(results[0]).keys())
    with (args.output_root / "grid_gate_results.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            row = asdict(result)
            row["detected_vertical_positions"] = json.dumps(row["detected_vertical_positions"])
            row["detected_horizontal_positions"] = json.dumps(row["detected_horizontal_positions"])
            row["failure_reasons"] = json.dumps(row["failure_reasons"])
            writer.writerow(row)
    make_contact_sheet(results, args.output_root)

    with (args.output_root / "derived_files.sha256").open("w", encoding="ascii") as handle:
        for path in sorted(args.output_root.rglob("*")):
            if path.is_file() and path.name != "derived_files.sha256":
                handle.write(f"{sha256(path)}  {path.relative_to(args.output_root)}\n")

    print(json.dumps({"passed": payload["passed"], "total": payload["total"]}))
    return 0 if payload["all_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
