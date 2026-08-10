#!/usr/bin/env python3
"""One-shot, display-only panel-pair diagnostic for full LTPP source pages.

It locates two similarly shaped long printed rectangles on a full page using
only long, nearly axis-aligned line segments and rectangle geometry.  It is not
a registration transform and it does not read a crack/damage label.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np


DATE_IDS = (
    "19910610", "19951024", "19970228", "19980407",
    "20010913", "20030514", "20071106", "20120417",
)


@dataclass(frozen=True)
class Rect:
    x0: int
    y0: int
    x1: int
    y1: int
    score: float

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


def cluster_lines(lines: list[tuple[int, int, int]], tolerance: int) -> list[tuple[int, int]]:
    """Return (mean coordinate, max length) groups from (coordinate,length,_)."""
    if not lines:
        return []
    ordered = sorted(lines)
    groups: list[list[tuple[int, int, int]]] = [[ordered[0]]]
    for line in ordered[1:]:
        if line[0] - groups[-1][-1][0] <= tolerance:
            groups[-1].append(line)
        else:
            groups.append([line])
    return [
        (round(sum(item[0] for item in group) / len(group)), max(item[1] for item in group))
        for group in groups
    ]


def cap_lines(lines: list[tuple[int, int]], limit: int = 24) -> list[tuple[int, int]]:
    """Keep a deterministic bounded set before geometric enumeration."""
    return sorted(sorted(lines, key=lambda item: (-item[1], item[0]))[:limit])


def long_axis_lines(gray: np.ndarray) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    edges = cv2.Canny(gray, 40, 130, apertureSize=3)
    raw = cv2.HoughLinesP(
        edges, rho=1, theta=np.pi / 720, threshold=85, minLineLength=170, maxLineGap=14
    )
    vertical: list[tuple[int, int, int]] = []
    horizontal: list[tuple[int, int, int]] = []
    if raw is None:
        return [], []
    for x0, y0, x1, y1 in raw[:, 0]:
        dx, dy = int(x1 - x0), int(y1 - y0)
        length = int(round(float(np.hypot(dx, dy))))
        if length < 170:
            continue
        if abs(dx) <= 8 and abs(dy) >= 170:
            vertical.append((round((x0 + x1) / 2), length, 0))
        elif abs(dy) <= 8 and abs(dx) >= 170:
            horizontal.append((round((y0 + y1) / 2), length, 0))
    return cap_lines(cluster_lines(vertical, tolerance=10)), cap_lines(cluster_lines(horizontal, tolerance=10))


def rectangle_candidates(gray: np.ndarray) -> list[Rect]:
    height, width = gray.shape
    vertical, horizontal = long_axis_lines(gray)
    candidates: list[Rect] = []
    for x0, left_length in vertical:
        for x1, right_length in vertical:
            if x1 <= x0:
                continue
            panel_width = x1 - x0
            if not (0.13 * width <= panel_width <= 0.47 * width):
                continue
            for y0, top_length in horizontal:
                for y1, bottom_length in horizontal:
                    if y1 <= y0:
                        continue
                    panel_height = y1 - y0
                    aspect = panel_height / panel_width
                    if not (1.9 <= aspect <= 4.6):
                        continue
                    if not (0.35 * height <= panel_height <= 0.85 * height):
                        continue
                    score = float(left_length + right_length + top_length + bottom_length)
                    candidates.append(Rect(x0, y0, x1, y1, score))
    # Exact duplicates occur when the two edges of a printed stroke are each detected.
    selected: list[Rect] = []
    for candidate in sorted(candidates, key=lambda item: (-item.score, item.x0, item.y0)):
        if any(
            max(abs(candidate.x0 - prior.x0), abs(candidate.y0 - prior.y0),
                abs(candidate.x1 - prior.x1), abs(candidate.y1 - prior.y1)) <= 16
            for prior in selected
        ):
            continue
        selected.append(candidate)
    return selected


def select_panel_pair(candidates: list[Rect]) -> tuple[Rect, Rect] | None:
    pairs: list[tuple[float, Rect, Rect]] = []
    for i, left in enumerate(candidates):
        for right in candidates[i + 1:]:
            first, second = sorted((left, right), key=lambda rect: rect.x0)
            if first.x1 >= second.x0:
                continue
            width_ratio = max(first.width, second.width) / min(first.width, second.width)
            height_ratio = max(first.height, second.height) / min(first.height, second.height)
            y_delta = max(abs(first.y0 - second.y0), abs(first.y1 - second.y1))
            if width_ratio > 1.20 or height_ratio > 1.10 or y_delta > 42:
                continue
            pair_score = first.score + second.score - 6.0 * y_delta
            pairs.append((pair_score, first, second))
    if not pairs:
        return None
    pairs.sort(key=lambda item: (-item[0], item[1].x0, item[2].x0))
    _, first, second = pairs[0]
    return first, second


def annotate(source: np.ndarray, pair: tuple[Rect, Rect] | None, date_id: str) -> np.ndarray:
    canvas = cv2.cvtColor(source, cv2.COLOR_GRAY2BGR)
    label = f"{date_id}: NO_PANEL_PAIR" if pair is None else f"{date_id}: pair candidate only"
    cv2.rectangle(canvas, (14, 14), (min(canvas.shape[1] - 14, 560), 50), (255, 255, 255), -1)
    cv2.putText(canvas, label, (22, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2, cv2.LINE_AA)
    if pair is not None:
        colors = ((0, 185, 0), (255, 0, 255))  # BGR: green / magenta
        for index, (rect, color) in enumerate(zip(pair, colors), start=1):
            cv2.rectangle(canvas, (rect.x0, rect.y0), (rect.x1, rect.y1), color, 5)
            cv2.putText(canvas, f"P{index}", (rect.x0 + 8, rect.y0 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 3, cv2.LINE_AA)
    return canvas


def build_overview(items: list[tuple[str, np.ndarray]]) -> np.ndarray:
    tiles = []
    for date_id, image in items:
        thumb = cv2.resize(image, (340, 437), interpolation=cv2.INTER_AREA)
        tiles.append(thumb)
    rows = [np.hstack(tiles[index:index + 4]) for index in range(0, len(tiles), 4)]
    return np.vstack(rows)


def write_manifest(output_root: Path) -> None:
    lines = []
    for path in sorted(p for p in output_root.rglob("*") if p.is_file() and p.name != "manifest.sha256"):
        lines.append(f"{sha256_path(path)}  {path.relative_to(output_root)}")
    (output_root / "manifest.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(input_root: Path, output_root: Path) -> dict[str, object]:
    if output_root.exists():
        raise FileExistsError(f"output root must be new: {output_root}")
    output_root.mkdir(parents=True)
    overlays = output_root / "overlays"
    overlays.mkdir()
    rows: list[dict[str, object]] = []
    overview_items: list[tuple[str, np.ndarray]] = []
    for date_id in DATE_IDS:
        source_path = input_root / "visuals" / f"{date_id}_full_source_page_4.png"
        source = cv2.imread(str(source_path), cv2.IMREAD_GRAYSCALE)
        if source is None:
            raise FileNotFoundError(source_path)
        pair = select_panel_pair(rectangle_candidates(source))
        overlay = annotate(source, pair, date_id)
        overlay_path = overlays / f"{date_id}_panel_pair_overlay.png"
        if not cv2.imwrite(str(overlay_path), overlay):
            raise RuntimeError(f"could not write {overlay_path}")
        rows.append({
            "date_id": date_id,
            "source_file": str(source_path),
            "source_sha256": sha256_path(source_path),
            "status": "PANEL_PAIR_CANDIDATE" if pair else "NO_PANEL_PAIR",
            "panels": [asdict(rect) for rect in pair] if pair else [],
        })
        overview_items.append((date_id, overlay))
    overview_path = output_root / "eight_date_full_source_panel_overview.png"
    if not cv2.imwrite(str(overview_path), build_overview(overview_items)):
        raise RuntimeError(f"could not write {overview_path}")
    result = {
        "status": "EXPLORATORY_FULL_SOURCE_PANEL_MVP__NOT_REGISTRATION",
        "source_root": str(input_root),
        "source_manifest_sha256": sha256_path(input_root / "manifest.sha256"),
        "method": "long axis-aligned printed-line geometry; no semantic damage parsing",
        "dates": rows,
        "script_sha256": sha256_path(Path(__file__).resolve()),
    }
    (output_root / "panel_mvp_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(output_root)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.input_root, args.output_root)
    print(json.dumps({"status": result["status"], "dates": len(result["dates"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
