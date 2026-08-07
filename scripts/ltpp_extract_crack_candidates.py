#!/usr/bin/env python3
"""Create conservative crack candidates from rectified LTPP distress maps.

The output is intentionally not a ground-truth crack mask.  Long rectilinear
survey-grid and lane-boundary ink is removed, elongated residual components
are proposed as high-confidence candidates, and every other residual pixel is
retained as uncertain for independent review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np
from skimage.morphology import skeletonize


DATES = (
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


def trace_horizontal_boundary(
    ink: np.ndarray, start_fraction: float, end_fraction: float
) -> np.ndarray:
    """Trace one smooth, mostly horizontal survey/lane boundary."""
    height, width = ink.shape
    y0 = int(round(height * start_fraction))
    y1 = int(round(height * end_fraction))
    band = (ink[y0:y1] > 0).astype(np.float32)
    local_support = cv2.GaussianBlur(band, (9, 3), 0)
    pixel_score = 3.0 * band + 2.0 * local_support
    band_height = band.shape[0]
    dynamic = np.empty_like(pixel_score)
    predecessor = np.zeros((band_height, width), dtype=np.int8)
    dynamic[:, 0] = pixel_score[:, 0]
    max_step = 4
    offsets = np.arange(-max_step, max_step + 1, dtype=np.int16)
    for x in range(1, width):
        previous = dynamic[:, x - 1]
        alternatives = np.full((offsets.size, band_height), -1e9, dtype=np.float32)
        for index, offset in enumerate(offsets):
            if offset < 0:
                alternatives[index, :offset] = previous[-offset:] - 0.18 * abs(offset)
            elif offset > 0:
                alternatives[index, offset:] = previous[:-offset] - 0.18 * offset
            else:
                alternatives[index] = previous
        selected = np.argmax(alternatives, axis=0)
        dynamic[:, x] = pixel_score[:, x] + alternatives[selected, np.arange(band_height)]
        predecessor[:, x] = offsets[selected]
    path = np.empty(width, dtype=np.int32)
    path[-1] = int(np.argmax(dynamic[:, -1]))
    for x in range(width - 1, 0, -1):
        path[x - 1] = path[x] - int(predecessor[path[x], x])
        path[x - 1] = int(np.clip(path[x - 1], 0, band_height - 1))
    path += y0
    mask = np.zeros_like(ink)
    points = np.column_stack((np.arange(width, dtype=np.int32), path))
    cv2.polylines(mask, [points], False, 255, thickness=max(9, height // 42))
    return mask


def periodic_vertical_grid_mask(ink: np.ndarray) -> np.ndarray:
    """Detect a globally supported regular vertical survey grid."""
    height, width = ink.shape
    connected = cv2.morphologyEx(
        ink,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(5, height // 80))),
    )
    profile = np.count_nonzero(connected, axis=0).astype(np.float64)
    best = None
    for intervals in (30, 50):
        positions = np.rint(np.linspace(0, width - 1, intervals + 1)).astype(int)
        supports = []
        adjusted = []
        for position in positions:
            left = max(0, position - 4)
            right = min(width, position + 5)
            local_offset = int(np.argmax(profile[left:right]))
            adjusted_position = left + local_offset
            adjusted.append(adjusted_position)
            supports.append(profile[adjusted_position])
        supports_array = np.asarray(supports)
        supported_fraction = float(np.mean(supports_array >= height * 0.12))
        median_support = float(np.median(supports_array) / height)
        score = supported_fraction + median_support * math.sqrt(intervals)
        candidate = (score, intervals, supported_fraction, median_support, adjusted)
        if best is None or candidate[0] > best[0]:
            best = candidate
    assert best is not None
    _, _, supported_fraction, median_support, positions = best
    mask = np.zeros_like(ink)
    if supported_fraction >= 0.70 and median_support >= 0.12:
        for position in positions:
            cv2.line(mask, (position, 0), (position, height - 1), 255, 9)
    return mask


@dataclass
class ComponentMetric:
    label: int
    area_px: int
    bbox_x: int
    bbox_y: int
    bbox_width: int
    bbox_height: int
    skeleton_length_px: int
    elongation: float
    fill_ratio: float
    touches_boundary: bool
    high_confidence: bool


@dataclass
class MapMetric:
    survey_date: str
    source_path: str
    source_sha256: str
    ink_pixels: int
    static_line_pixels: int
    residual_pixels: int
    high_confidence_pixels: int
    uncertain_pixels: int
    high_confidence_components: int
    uncertain_components: int
    high_confidence_skeleton_length_px: int
    static_line_fraction_of_ink: float
    high_confidence_fraction_of_residual: float
    semantic_status: str
    candidate_mask_path: str
    candidate_skeleton_path: str
    uncertain_mask_path: str
    static_line_mask_path: str
    overlay_path: str
    components: list[ComponentMetric]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def static_line_mask(ink: np.ndarray) -> np.ndarray:
    height, width = ink.shape
    vertical_connected = cv2.morphologyEx(
        ink,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(7, height // 55))),
    )
    vertical = cv2.morphologyEx(
        vertical_connected,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(80, int(height * 0.72)))),
    )
    horizontal_connected = cv2.morphologyEx(
        ink,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(9, width // 130), 1)),
    )
    horizontal = cv2.morphologyEx(
        horizontal_connected,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(180, int(width * 0.72)), 1)),
    )
    mask = cv2.bitwise_or(vertical, horizontal)
    mask = cv2.bitwise_or(mask, periodic_vertical_grid_mask(ink))
    upper_boundary = trace_horizontal_boundary(ink, 0.10, 0.38)
    lower_boundary = trace_horizontal_boundary(ink, 0.62, 0.92)
    mask = cv2.bitwise_or(mask, upper_boundary)
    mask = cv2.bitwise_or(mask, lower_boundary)

    edges = cv2.Canny(ink, 50, 150)
    segments = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 1800.0,
        threshold=90,
        minLineLength=min(width, height) // 2,
        maxLineGap=max(12, width // 80),
    )
    if segments is not None:
        for x0, y0, x1, y1 in segments[:, 0, :]:
            dx = x1 - x0
            dy = y1 - y0
            length = math.hypot(dx, dy)
            horizontal_line = abs(dy) <= max(2, abs(dx) * 0.015) and length >= width * 0.65
            vertical_line = abs(dx) <= max(2, abs(dy) * 0.015) and length >= height * 0.65
            if horizontal_line or vertical_line:
                cv2.line(mask, (x0, y0), (x1, y1), 255, 3)
    return cv2.dilate(mask, np.ones((3, 3), dtype=np.uint8), iterations=1)


def component_elongation(xs: np.ndarray, ys: np.ndarray) -> float:
    if xs.size < 3:
        return 1.0
    points = np.column_stack((xs, ys)).astype(np.float64)
    covariance = np.cov(points, rowvar=False)
    eigenvalues = np.linalg.eigvalsh(covariance)
    return float(math.sqrt(max(eigenvalues[-1], 1e-9) / max(eigenvalues[0], 1e-9)))


def classify_components(residual: np.ndarray) -> tuple[np.ndarray, np.ndarray, list[ComponentMetric]]:
    height, width = residual.shape
    connected = cv2.morphologyEx(
        residual, cv2.MORPH_CLOSE, np.ones((9, 9), dtype=np.uint8)
    )
    count, labels, stats, _ = cv2.connectedComponentsWithStats(connected, connectivity=8)
    high = np.zeros_like(residual)
    uncertain = np.zeros_like(residual)
    metrics: list[ComponentMetric] = []
    for label in range(1, count):
        x, y, box_width, box_height, area = [int(v) for v in stats[label]]
        component = labels == label
        ys, xs = np.nonzero(component)
        local = component[y : y + box_height, x : x + box_width]
        skeleton_length = int(np.count_nonzero(skeletonize(local)))
        elongation = component_elongation(xs, ys)
        fill_ratio = area / max(1, box_width * box_height)
        touches = x <= 4 or y <= 4 or x + box_width >= width - 4 or y + box_height >= height - 4
        long_enough = skeleton_length >= 45 and box_height >= 50
        slender = elongation >= 3.0 and fill_ratio <= 0.35
        transverse_orientation = box_height >= 1.5 * box_width
        is_high = long_enough and slender and transverse_orientation and not touches
        original_component = np.logical_and(component, residual > 0)
        if is_high:
            high[original_component] = 255
        else:
            uncertain[original_component] = 255
        metrics.append(
            ComponentMetric(
                label=label,
                area_px=area,
                bbox_x=x,
                bbox_y=y,
                bbox_width=box_width,
                bbox_height=box_height,
                skeleton_length_px=skeleton_length,
                elongation=elongation,
                fill_ratio=fill_ratio,
                touches_boundary=touches,
                high_confidence=is_high,
            )
        )
    return high, uncertain, metrics


def process(source: Path, output_root: Path) -> MapMetric:
    survey_date = source.parent.name
    gray = cv2.imread(str(source), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise ValueError(f"cannot read {source}")
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    lines = static_line_mask(ink)
    residual = cv2.bitwise_and(ink, cv2.bitwise_not(lines))
    residual[:5, :] = 0
    residual[-5:, :] = 0
    residual[:, :5] = 0
    residual[:, -5:] = 0
    high, uncertain, components = classify_components(residual)
    high_skeleton = (skeletonize(high > 0).astype(np.uint8) * 255)

    date_root = output_root / survey_date
    date_root.mkdir(parents=True, exist_ok=True)
    paths = {
        "candidate_mask": date_root / "high_confidence_candidate_not_ground_truth.png",
        "candidate_skeleton": date_root / "high_confidence_candidate_skeleton.png",
        "uncertain": date_root / "uncertain_residual_ink.png",
        "static": date_root / "removed_static_line_ink.png",
        "overlay": date_root / "candidate_qc_overlay.png",
    }
    cv2.imwrite(str(paths["candidate_mask"]), high)
    cv2.imwrite(str(paths["candidate_skeleton"]), high_skeleton)
    cv2.imwrite(str(paths["uncertain"]), uncertain)
    cv2.imwrite(str(paths["static"]), lines)

    overlay = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    overlay[lines > 0] = (220, 200, 0)
    overlay[uncertain > 0] = (0, 170, 255)
    overlay[high > 0] = (0, 0, 255)
    cv2.putText(
        overlay,
        f"{survey_date}: red=candidate orange=uncertain cyan=static lines",
        (15, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (20, 20, 20),
        2,
        cv2.LINE_AA,
    )
    cv2.imwrite(str(paths["overlay"]), overlay)

    ink_pixels = int(np.count_nonzero(ink))
    residual_pixels = int(np.count_nonzero(residual))
    high_pixels = int(np.count_nonzero(high))
    high_components = sum(component.high_confidence for component in components)
    return MapMetric(
        survey_date=survey_date,
        source_path=str(source),
        source_sha256=file_sha256(source),
        ink_pixels=ink_pixels,
        static_line_pixels=int(np.count_nonzero(cv2.bitwise_and(ink, lines))),
        residual_pixels=residual_pixels,
        high_confidence_pixels=high_pixels,
        uncertain_pixels=int(np.count_nonzero(uncertain)),
        high_confidence_components=high_components,
        uncertain_components=len(components) - high_components,
        high_confidence_skeleton_length_px=int(np.count_nonzero(high_skeleton)),
        static_line_fraction_of_ink=float(
            np.count_nonzero(cv2.bitwise_and(ink, lines)) / max(1, ink_pixels)
        ),
        high_confidence_fraction_of_residual=float(high_pixels / max(1, residual_pixels)),
        semantic_status="transverse_candidate_only_requires_independent_review",
        candidate_mask_path=str(paths["candidate_mask"].relative_to(output_root)),
        candidate_skeleton_path=str(paths["candidate_skeleton"].relative_to(output_root)),
        uncertain_mask_path=str(paths["uncertain"].relative_to(output_root)),
        static_line_mask_path=str(paths["static"].relative_to(output_root)),
        overlay_path=str(paths["overlay"].relative_to(output_root)),
        components=components,
    )


def contact_sheet(metrics: list[MapMetric], output_root: Path) -> None:
    tiles = []
    for metric in metrics:
        image = cv2.imread(str(output_root / metric.overlay_path), cv2.IMREAD_COLOR)
        scale = min(1.0, 640.0 / image.shape[1])
        tile = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        canvas = np.full((230, 640, 3), 255, dtype=np.uint8)
        canvas[: min(230, tile.shape[0]), : min(640, tile.shape[1])] = tile[
            : min(230, tile.shape[0]), : min(640, tile.shape[1])
        ]
        tiles.append(canvas)
    blank = np.full_like(tiles[0], 255)
    tiles.extend([blank] * (9 - len(tiles)))
    sheet = np.vstack([np.hstack(tiles[index : index + 3]) for index in range(0, 9, 3)])
    cv2.imwrite(str(output_root / "candidate_qc_contact_sheet.png"), sheet)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rectified-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)
    sources = [args.rectified_root / date / "rectified_grid.png" for date in DATES]
    missing = [str(path) for path in sources if not path.is_file()]
    if missing:
        raise SystemExit("missing qualified rectified inputs:\n" + "\n".join(missing))

    metrics = [process(source, args.output_root) for source in sources]
    payload = {
        "stage": "transverse_semantic_candidate_generation_v2",
        "input_gate": "ltpp_06_1253_regular_physical_grid_v1 all_passed=true",
        "semantic_boundary": "No output in this package is a ground-truth or complete crack mask. Longitudinal cracking remains uncertain.",
        "candidate_rule": {
            "min_skeleton_length_px": 45,
            "min_bbox_height_px": 50,
            "min_elongation": 3.0,
            "max_fill_ratio": 0.35,
            "min_height_to_width_ratio": 1.5,
            "boundary_touching_components_allowed": False,
        },
        "review_status": "not_reviewed",
        "maps": [asdict(metric) for metric in metrics],
    }
    with (args.output_root / "candidate_metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    contact_sheet(metrics, args.output_root)
    with (args.output_root / "derived_files.sha256").open("w", encoding="ascii") as handle:
        for path in sorted(args.output_root.rglob("*")):
            if path.is_file() and path.name != "derived_files.sha256":
                handle.write(f"{file_sha256(path)}  {path.relative_to(args.output_root)}\n")
    print(
        json.dumps(
            {
                "maps": len(metrics),
                "candidate_components": sum(m.high_confidence_components for m in metrics),
                "review_status": "not_reviewed",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
