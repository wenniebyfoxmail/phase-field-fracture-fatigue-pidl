#!/usr/bin/env python3
"""Detect paired printed map frames only on owner-confirmed LTPP map pages."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np


CONFIRMED_PAGE_RANGES = {
    "19910610": tuple(range(6, 11)),
    "19951024": tuple(range(4, 9)),
    "19970228": tuple(range(4, 9)),
    "19980407": tuple(range(4, 9)),
    "20010913": tuple(range(4, 9)),
    "20030514": tuple(range(4, 9)),
    "20071106": tuple(range(4, 9)),
    "20120417": tuple(range(3, 8)),
}


@dataclass(frozen=True)
class Rect:
    x0: int
    y0: int
    x1: int
    y1: int
    component_pixels: int

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def printed_grid_components(gray: np.ndarray) -> tuple[np.ndarray, list[Rect]]:
    page_height, page_width = gray.shape
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    horizontal_closed = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((1, 11), np.uint8))
    horizontal = cv2.morphologyEx(
        horizontal_closed,
        cv2.MORPH_OPEN,
        np.ones((1, max(45, round(page_width * 0.055))), np.uint8),
    )
    vertical_closed = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((11, 1), np.uint8))
    vertical = cv2.morphologyEx(
        vertical_closed,
        cv2.MORPH_OPEN,
        np.ones((max(110, round(page_height * 0.10)), 1), np.uint8),
    )

    grid_lines = cv2.bitwise_or(horizontal, vertical)
    connected = cv2.morphologyEx(
        cv2.dilate(grid_lines, np.ones((7, 7), np.uint8), iterations=1),
        cv2.MORPH_CLOSE,
        np.ones((15, 15), np.uint8),
    )
    count, _, stats, _ = cv2.connectedComponentsWithStats(connected, connectivity=8)
    candidates: list[Rect] = []
    for label in range(1, count):
        x, y, width, height, area = (int(value) for value in stats[label])
        if not (0.13 * page_width <= width <= 0.48 * page_width):
            continue
        if not (0.38 * page_height <= height <= 0.90 * page_height):
            continue
        if not (1.55 <= height / width <= 5.0):
            continue
        candidates.append(Rect(x, y, x + width - 1, y + height - 1, area))
    return grid_lines, candidates


def select_pair(candidates: list[Rect], page_height: int) -> tuple[Rect, Rect] | None:
    pairs: list[tuple[float, Rect, Rect]] = []
    for index, first in enumerate(candidates):
        for second in candidates[index + 1:]:
            left, right = sorted((first, second), key=lambda rect: rect.x0)
            if left.x1 >= right.x0:
                continue
            width_ratio = max(left.width, right.width) / min(left.width, right.width)
            height_ratio = max(left.height, right.height) / min(left.height, right.height)
            y_delta = max(abs(left.y0 - right.y0), abs(left.y1 - right.y1))
            if width_ratio > 1.35 or height_ratio > 1.20 or y_delta > 0.10 * page_height:
                continue
            score = float(left.component_pixels + right.component_pixels - 8 * y_delta)
            pairs.append((score, left, right))
    if not pairs:
        return None
    pairs.sort(key=lambda item: (-item[0], item[1].x0, item[2].x0))
    return pairs[0][1], pairs[0][2]


def annotate(gray: np.ndarray, pair: tuple[Rect, Rect] | None, date_id: str, page: int) -> np.ndarray:
    canvas = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    status = "NO_PAIR" if pair is None else "candidate pair only"
    label = f"{date_id} p{page:02d}: {status}"
    cv2.rectangle(canvas, (12, 12), (min(520, canvas.shape[1] - 12), 46), (255, 255, 255), -1)
    cv2.putText(canvas, label, (19, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 0), 2, cv2.LINE_AA)
    if pair:
        for number, (rect, color) in enumerate(zip(pair, ((0, 190, 0), (255, 0, 255))), start=1):
            cv2.rectangle(canvas, (rect.x0, rect.y0), (rect.x1, rect.y1), color, 4)
            cv2.putText(canvas, f"P{number}", (rect.x0 + 6, rect.y0 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.72, color, 2, cv2.LINE_AA)
    return canvas


def review_sheet(items: list[tuple[int, np.ndarray]]) -> np.ndarray:
    tiles = []
    for page, image in items:
        tile = cv2.resize(image, (340, 440), interpolation=cv2.INTER_AREA)
        cv2.putText(tile, f"PDF p{page:02d}", (8, 428), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 0), 2, cv2.LINE_AA)
        tiles.append(tile)
    top = np.hstack(tiles[:3])
    blank = np.full_like(tiles[0], 255)
    bottom = np.hstack(tiles[3:] + [blank])
    return np.vstack((top, bottom))


def first_page_overview(items: list[np.ndarray]) -> np.ndarray:
    thumbs = [cv2.resize(image, (340, 440), interpolation=cv2.INTER_AREA) for image in items]
    return np.vstack((np.hstack(thumbs[:4]), np.hstack(thumbs[4:])))


def find_rendered_page(date_root: Path, page: int) -> Path:
    matches = sorted(set(date_root.glob(f"page-{page}.png")) | set(date_root.glob(f"page-{page:02d}.png")))
    if len(matches) != 1:
        raise FileNotFoundError(f"expected one page {page:02d} in {date_root}, got {matches}")
    return matches[0]


def write_manifest(root: Path) -> None:
    lines = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "manifest.sha256"):
        lines.append(f"{sha256_path(path)}  {path.relative_to(root)}")
    (root / "manifest.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(input_root: Path, output_root: Path) -> dict[str, object]:
    if output_root.exists():
        raise FileExistsError(f"output root must be new: {output_root}")
    overlays_root = output_root / "overlays"
    sheets_root = output_root / "per_date_review"
    overlays_root.mkdir(parents=True)
    sheets_root.mkdir()
    date_results: list[dict[str, object]] = []
    first_pages: list[np.ndarray] = []
    for date_id, pages in CONFIRMED_PAGE_RANGES.items():
        date_overlays: list[tuple[int, np.ndarray]] = []
        page_results = []
        for page in pages:
            source_path = find_rendered_page(input_root / "rendered_pages" / date_id, page)
            gray = cv2.imread(str(source_path), cv2.IMREAD_GRAYSCALE)
            if gray is None:
                raise RuntimeError(f"could not read {source_path}")
            _, candidates = printed_grid_components(gray)
            pair = select_pair(candidates, gray.shape[0])
            overlay = annotate(gray, pair, date_id, page)
            output_path = overlays_root / f"{date_id}_p{page:02d}_panel_overlay.png"
            if not cv2.imwrite(str(output_path), overlay):
                raise RuntimeError(f"could not write {output_path}")
            date_overlays.append((page, overlay))
            page_results.append({
                "page": page,
                "source_relative": str(source_path.relative_to(input_root)),
                "source_sha256": sha256_path(source_path),
                "candidate_component_count": len(candidates),
                "status": "PANEL_PAIR_CANDIDATE" if pair else "NO_PAIR",
                "panels": [asdict(rect) for rect in pair] if pair else [],
            })
        review_path = sheets_root / f"{date_id}_five_confirmed_pages_review.png"
        if not cv2.imwrite(str(review_path), review_sheet(date_overlays)):
            raise RuntimeError(f"could not write {review_path}")
        first_pages.append(date_overlays[0][1])
        date_results.append({"date_id": date_id, "confirmed_pages": list(pages), "pages": page_results})

    overview_path = output_root / "eight_date_first_confirmed_page_overview.png"
    if not cv2.imwrite(str(overview_path), first_page_overview(first_pages)):
        raise RuntimeError(f"could not write {overview_path}")
    payload = {
        "status": "EXPLORATORY_CONFIRMED_MAP_PANEL_MVP_V2__NOT_REGISTRATION",
        "input_root": str(input_root),
        "input_manifest_sha256": sha256_path(input_root / "manifest.sha256"),
        "owner_confirmed_page_ranges": {key: list(value) for key, value in CONFIRMED_PAGE_RANGES.items()},
        "method": "orthogonal long-line morphology; tall connected grid components; similar left-right pair",
        "prohibited": ["manual box completion", "crop use", "controls", "transforms", "crack semantics"],
        "dates": date_results,
        "script_sha256": sha256_path(Path(__file__).resolve()),
    }
    (output_root / "panel_mvp_v2_result.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(output_root)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.input_root, args.output_root)
    page_count = sum(len(date["pages"]) for date in result["dates"])
    print(json.dumps({"status": result["status"], "pages": page_count}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
