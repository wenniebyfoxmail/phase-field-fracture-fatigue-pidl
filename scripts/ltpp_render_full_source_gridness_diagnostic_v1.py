#!/usr/bin/env python3
"""Render a display-only printed-gridness heatmap for full LTPP source pages."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np


DATE_IDS = (
    "19910610", "19951024", "19970228", "19980407",
    "20010913", "20030514", "20071106", "20120417",
)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gridness(gray: np.ndarray) -> np.ndarray:
    """Large-scale co-occurrence of short horizontal and vertical printed strokes."""
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    horizontal = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((1, 11), np.uint8))
    vertical = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((11, 1), np.uint8))
    intersections = cv2.bitwise_and(horizontal, vertical)
    response = cv2.boxFilter(intersections.astype(np.float32) / 255.0, -1, (121, 121), normalize=True)
    return response


def heatmap_overlay(gray: np.ndarray, response: np.ndarray, date_id: str) -> np.ndarray:
    scale = np.quantile(response, 0.995)
    if scale <= 0:
        scale = 1.0
    normal = np.uint8(np.clip(response / scale, 0, 1) * 255)
    color = cv2.applyColorMap(normal, cv2.COLORMAP_TURBO)
    base = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    overlay = cv2.addWeighted(base, 0.62, color, 0.38, 0)
    cv2.rectangle(overlay, (14, 14), (495, 50), (255, 255, 255), -1)
    cv2.putText(overlay, f"{date_id}: gridness diagnostic only", (22, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2, cv2.LINE_AA)
    return overlay


def build_overview(items: list[np.ndarray]) -> np.ndarray:
    thumbs = [cv2.resize(image, (340, 437), interpolation=cv2.INTER_AREA) for image in items]
    return np.vstack([np.hstack(thumbs[:4]), np.hstack(thumbs[4:])])


def write_manifest(root: Path) -> None:
    entries = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "manifest.sha256"):
        entries.append(f"{sha256_path(path)}  {path.relative_to(root)}")
    (root / "manifest.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")


def run(input_root: Path, output_root: Path) -> dict[str, object]:
    if output_root.exists():
        raise FileExistsError(f"output root must be new: {output_root}")
    output_root.mkdir(parents=True)
    per_date = output_root / "per_date"
    per_date.mkdir()
    report: list[dict[str, object]] = []
    overlays: list[np.ndarray] = []
    for date_id in DATE_IDS:
        source_path = input_root / "visuals" / f"{date_id}_full_source_page_4.png"
        gray = cv2.imread(str(source_path), cv2.IMREAD_GRAYSCALE)
        if gray is None:
            raise FileNotFoundError(source_path)
        response = gridness(gray)
        overlay = heatmap_overlay(gray, response, date_id)
        target = per_date / f"{date_id}_gridness_overlay.png"
        if not cv2.imwrite(str(target), overlay):
            raise RuntimeError(f"could not write {target}")
        report.append({
            "date_id": date_id,
            "source_sha256": sha256_path(source_path),
            "response_median": float(np.median(response)),
            "response_p995": float(np.quantile(response, 0.995, method="linear")),
            "response_max": float(np.max(response)),
        })
        overlays.append(overlay)
    overview = output_root / "eight_date_gridness_overview.png"
    if not cv2.imwrite(str(overview), build_overview(overlays)):
        raise RuntimeError(f"could not write {overview}")
    payload = {
        "status": "GRIDNESS_DIAGNOSTIC_ONLY__NO_PANEL_SELECTION_OR_REGISTRATION",
        "source_root": str(input_root),
        "source_manifest_sha256": sha256_path(input_root / "manifest.sha256"),
        "method": "Otsu ink threshold; 11-pixel horizontal/vertical closing; intersection; 121x121 mean response",
        "prohibited": ["panel selection", "cropping", "control points", "transform fitting", "crack semantics"],
        "dates": report,
        "script_sha256": sha256_path(Path(__file__).resolve()),
    }
    (output_root / "gridness_result.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(output_root)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    payload = run(args.input_root, args.output_root)
    print(json.dumps({"status": payload["status"], "dates": len(payload["dates"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
