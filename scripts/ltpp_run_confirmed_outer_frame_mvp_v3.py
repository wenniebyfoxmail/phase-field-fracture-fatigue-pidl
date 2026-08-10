#!/usr/bin/env python3
"""Outer-border Hough diagnostic on owner-confirmed LTPP map pages."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np

try:
    from scripts.ltpp_run_confirmed_map_panel_mvp_v2 import (
        CONFIRMED_PAGE_RANGES,
        find_rendered_page,
        first_page_overview,
        review_sheet,
        sha256_path,
        write_manifest,
    )
except ModuleNotFoundError:  # pragma: no cover - direct CLI path
    from ltpp_run_confirmed_map_panel_mvp_v2 import (
        CONFIRMED_PAGE_RANGES,
        find_rendered_page,
        first_page_overview,
        review_sheet,
        sha256_path,
        write_manifest,
    )


@dataclass(frozen=True)
class Frame:
    x0: int
    y0: int
    x1: int
    y1: int
    score: float
    perimeter_support: float
    interior_vertical_lines: int
    interior_horizontal_lines: int

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0


def cluster_lines(lines: list[tuple[int, int]], tolerance: int = 8, limit: int = 28) -> list[tuple[int, int]]:
    if not lines:
        return []
    groups: list[list[tuple[int, int]]] = [[item] for item in sorted(lines)]
    merged: list[list[tuple[int, int]]] = []
    for group in groups:
        if merged and group[0][0] - merged[-1][-1][0] <= tolerance:
            merged[-1].extend(group)
        else:
            merged.append(group)
    representatives = [
        (round(sum(coord for coord, _ in group) / len(group)), max(length for _, length in group))
        for group in merged
    ]
    return sorted(sorted(representatives, key=lambda item: (-item[1], item[0]))[:limit])


def axis_lines(gray: np.ndarray) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    height, width = gray.shape
    edges = cv2.Canny(gray, 40, 130, apertureSize=3)
    raw = cv2.HoughLinesP(edges, 1, np.pi / 720, threshold=45, minLineLength=70, maxLineGap=22)
    vertical: list[tuple[int, int]] = []
    horizontal: list[tuple[int, int]] = []
    if raw is None:
        return [], []
    for x0, y0, x1, y1 in raw[:, 0]:
        dx, dy = int(x1 - x0), int(y1 - y0)
        length = int(round(float(np.hypot(dx, dy))))
        if abs(dx) <= 7 and abs(dy) >= 0.22 * height:
            vertical.append((round((x0 + x1) / 2), length))
        elif abs(dy) <= 7 and abs(dx) >= 0.10 * width:
            horizontal.append((round((y0 + y1) / 2), length))
    return cluster_lines(vertical), cluster_lines(horizontal)


def strip_support(ink: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> float:
    height, width = ink.shape
    x0, x1 = max(0, x0), min(width - 1, x1)
    y0, y1 = max(0, y0), min(height - 1, y1)
    strips = (
        ink[y0:y1 + 1, max(0, x0 - 3):min(width, x0 + 4)],
        ink[y0:y1 + 1, max(0, x1 - 3):min(width, x1 + 4)],
        ink[max(0, y0 - 3):min(height, y0 + 4), x0:x1 + 1],
        ink[max(0, y1 - 3):min(height, y1 + 4), x0:x1 + 1],
    )
    return float(sum(np.mean(strip > 0) for strip in strips) / len(strips))


def frame_candidates(gray: np.ndarray) -> list[Frame]:
    height, width = gray.shape
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    vertical, horizontal = axis_lines(gray)
    candidates: list[Frame] = []
    for i, (x0, _) in enumerate(vertical):
        for x1, _ in vertical[i + 1:]:
            panel_width = x1 - x0
            if not (0.13 * width <= panel_width <= 0.42 * width):
                continue
            inside_vertical = sum(x0 < x < x1 for x, _ in vertical)
            if inside_vertical < 4:
                continue
            for j, (y0, _) in enumerate(horizontal):
                for y1, _ in horizontal[j + 1:]:
                    panel_height = y1 - y0
                    if not (0.38 * height <= panel_height <= 0.90 * height):
                        continue
                    if not (1.55 <= panel_height / panel_width <= 5.0):
                        continue
                    inside_horizontal = sum(y0 < y < y1 for y, _ in horizontal)
                    if inside_horizontal < 4:
                        continue
                    support = strip_support(ink, x0, y0, x1, y1)
                    area_fraction = panel_width * panel_height / (width * height)
                    score = 200.0 * area_fraction + 500.0 * support + inside_vertical + inside_horizontal
                    candidates.append(Frame(
                        x0, y0, x1, y1, score, support,
                        inside_vertical, inside_horizontal,
                    ))
    candidates.sort(key=lambda frame: (-frame.score, frame.x0, frame.y0))
    return candidates[:120]


def select_pair(candidates: list[Frame], page_height: int) -> tuple[Frame, Frame] | None:
    pairs: list[tuple[float, Frame, Frame]] = []
    for index, first in enumerate(candidates):
        for second in candidates[index + 1:]:
            left, right = sorted((first, second), key=lambda frame: frame.x0)
            if left.x1 >= right.x0:
                continue
            if max(left.width, right.width) / min(left.width, right.width) > 1.35:
                continue
            if max(left.height, right.height) / min(left.height, right.height) > 1.15:
                continue
            y_delta = max(abs(left.y0 - right.y0), abs(left.y1 - right.y1))
            if y_delta > 0.08 * page_height:
                continue
            pairs.append((left.score + right.score - 5.0 * y_delta, left, right))
    if not pairs:
        return None
    pairs.sort(key=lambda item: (-item[0], item[1].x0, item[2].x0))
    return pairs[0][1], pairs[0][2]


def annotate(gray: np.ndarray, pair: tuple[Frame, Frame] | None, date_id: str, page: int) -> np.ndarray:
    canvas = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    label = f"{date_id} p{page:02d}: " + ("NO_PAIR" if pair is None else "outer-frame candidate")
    cv2.rectangle(canvas, (12, 12), (min(560, canvas.shape[1] - 12), 46), (255, 255, 255), -1)
    cv2.putText(canvas, label, (19, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 0), 2, cv2.LINE_AA)
    if pair:
        for number, (frame, color) in enumerate(zip(pair, ((0, 190, 0), (255, 0, 255))), start=1):
            cv2.rectangle(canvas, (frame.x0, frame.y0), (frame.x1, frame.y1), color, 4)
            cv2.putText(canvas, f"P{number}", (frame.x0 + 6, frame.y0 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.72, color, 2, cv2.LINE_AA)
    return canvas


def run(input_root: Path, output_root: Path) -> dict[str, object]:
    if output_root.exists():
        raise FileExistsError(f"output root must be new: {output_root}")
    overlays_root = output_root / "overlays"
    sheets_root = output_root / "per_date_review"
    overlays_root.mkdir(parents=True)
    sheets_root.mkdir()
    dates = []
    first_pages = []
    for date_id, pages in CONFIRMED_PAGE_RANGES.items():
        date_overlays = []
        page_rows = []
        for page in pages:
            source = find_rendered_page(input_root / "rendered_pages" / date_id, page)
            gray = cv2.imread(str(source), cv2.IMREAD_GRAYSCALE)
            if gray is None:
                raise RuntimeError(f"could not read {source}")
            candidates = frame_candidates(gray)
            pair = select_pair(candidates, gray.shape[0])
            overlay = annotate(gray, pair, date_id, page)
            target = overlays_root / f"{date_id}_p{page:02d}_outer_frame_overlay.png"
            if not cv2.imwrite(str(target), overlay):
                raise RuntimeError(f"could not write {target}")
            date_overlays.append((page, overlay))
            page_rows.append({
                "page": page,
                "source_relative": str(source.relative_to(input_root)),
                "source_sha256": sha256_path(source),
                "candidate_count": len(candidates),
                "status": "OUTER_FRAME_PAIR_CANDIDATE" if pair else "NO_PAIR",
                "frames": [asdict(frame) for frame in pair] if pair else [],
            })
        review = sheets_root / f"{date_id}_outer_frame_review.png"
        if not cv2.imwrite(str(review), review_sheet(date_overlays)):
            raise RuntimeError(f"could not write {review}")
        first_pages.append(date_overlays[0][1])
        dates.append({"date_id": date_id, "confirmed_pages": list(pages), "pages": page_rows})
    overview = output_root / "eight_date_first_page_outer_frame_overview.png"
    if not cv2.imwrite(str(overview), first_page_overview(first_pages)):
        raise RuntimeError(f"could not write {overview}")
    payload = {
        "status": "EXPLORATORY_CONFIRMED_OUTER_FRAME_MVP_V3__NOT_REGISTRATION",
        "input_root": str(input_root),
        "input_manifest_sha256": sha256_path(input_root / "manifest.sha256"),
        "owner_confirmed_page_ranges": {key: list(value) for key, value in CONFIRMED_PAGE_RANGES.items()},
        "method": "Hough outer-border candidates plus interior orthogonal-line support",
        "prohibited": ["manual completion", "crop use", "controls", "transforms", "crack semantics"],
        "dates": dates,
        "script_sha256": sha256_path(Path(__file__).resolve()),
    }
    (output_root / "outer_frame_mvp_v3_result.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(output_root)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.input_root, args.output_root)
    print(json.dumps({"status": result["status"], "pages": sum(len(d["pages"]) for d in result["dates"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
