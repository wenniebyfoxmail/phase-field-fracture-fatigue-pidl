#!/usr/bin/env python3
"""Render and rank full-source PDF pages by nonsemantic printed-grid coverage."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

try:  # Supports both pytest package import and direct script execution.
    from scripts.ltpp_render_full_source_gridness_diagnostic_v1 import gridness
except ModuleNotFoundError:  # pragma: no cover - direct CLI path
    from ltpp_render_full_source_gridness_diagnostic_v1 import gridness


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


def page_count(pdf_path: Path) -> int:
    process = subprocess.run(["pdfinfo", str(pdf_path)], check=True, capture_output=True, text=True)
    match = re.search(r"^Pages:\s+(\d+)\s*$", process.stdout, flags=re.MULTILINE)
    if not match:
        raise RuntimeError(f"could not read page count from {pdf_path}")
    return int(match.group(1))


def render_pdf_pages(pdf_path: Path, destination_prefix: Path) -> list[Path]:
    subprocess.run(
        ["pdftoppm", "-png", "-r", "100", str(pdf_path), str(destination_prefix)],
        check=True, capture_output=True, text=True,
    )
    pages = sorted(destination_prefix.parent.glob(f"{destination_prefix.name}-*.png"))
    if not pages:
        raise RuntimeError(f"pdftoppm rendered no pages for {pdf_path}")
    return pages


def grid_coverage(gray: np.ndarray) -> tuple[float, float]:
    response = gridness(gray)
    # Fixed absolute response; no comparison across dates selects a source page.
    return float(np.mean(response >= 0.030)), float(np.quantile(response, 0.995, method="linear"))


def tile(image: np.ndarray, label: str) -> np.ndarray:
    resized = cv2.resize(image, (204, 264), interpolation=cv2.INTER_AREA)
    canvas = cv2.copyMakeBorder(resized, 30, 0, 0, 0, cv2.BORDER_CONSTANT, value=255)
    cv2.putText(canvas, label, (5, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.42, 0, 1, cv2.LINE_AA)
    return canvas


def contact_sheet(items: list[tuple[np.ndarray, str]]) -> np.ndarray:
    rows = []
    for start in range(0, len(items), 3):
        row = [tile(image, label) for image, label in items[start:start + 3]]
        while len(row) < 3:
            row.append(np.full_like(row[0], 255))
        rows.append(np.hstack(row))
    return np.vstack(rows)


def write_manifest(root: Path) -> None:
    lines = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "manifest.sha256"):
        lines.append(f"{sha256_path(path)}  {path.relative_to(root)}")
    (root / "manifest.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(input_root: Path, output_root: Path) -> dict[str, object]:
    if output_root.exists():
        raise FileExistsError(f"output root must be new: {output_root}")
    pages_root = output_root / "rendered_pages"
    sheets_root = output_root / "contact_sheets"
    pages_root.mkdir(parents=True)
    sheets_root.mkdir()
    dates: list[dict[str, object]] = []
    for date_id in DATE_IDS:
        pdfs = sorted((input_root / "pdfs").glob(f"{date_id}_*.PDF"))
        if len(pdfs) != 1:
            raise FileNotFoundError(f"expected exactly one PDF for {date_id}, got {pdfs}")
        pdf = pdfs[0]
        expected_pages = page_count(pdf)
        date_root = pages_root / date_id
        date_root.mkdir()
        raw_pages = render_pdf_pages(pdf, date_root / "page")
        if len(raw_pages) != expected_pages:
            raise RuntimeError(f"render count mismatch for {date_id}: {len(raw_pages)} != {expected_pages}")
        page_rows = []
        visuals: list[tuple[np.ndarray, str]] = []
        for index, path in enumerate(raw_pages, start=1):
            gray = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if gray is None:
                raise RuntimeError(f"could not read rendered page {path}")
            coverage, p995 = grid_coverage(gray)
            page_rows.append({
                "page": index,
                "file": str(path.relative_to(output_root)),
                "sha256": sha256_path(path),
                "grid_coverage_ge_0_030": coverage,
                "gridness_p995": p995,
            })
            visuals.append((gray, f"p{index} coverage={coverage:.3f}"))
        ranked = sorted(page_rows, key=lambda row: (-row["grid_coverage_ge_0_030"], row["page"]))
        sheet = contact_sheet(visuals)
        sheet_path = sheets_root / f"{date_id}_all_pages.png"
        if not cv2.imwrite(str(sheet_path), sheet):
            raise RuntimeError(f"could not write {sheet_path}")
        dates.append({
            "date_id": date_id,
            "pdf_sha256": sha256_path(pdf),
            "page_count": expected_pages,
            "pages": page_rows,
            "ranking_by_grid_coverage_only": [row["page"] for row in ranked],
        })
    payload = {
        "status": "FULL_SOURCE_PAGE_DISCOVERY_ONLY__NO_PANEL_SELECTION_OR_REGISTRATION",
        "source_root": str(input_root),
        "source_manifest_sha256": sha256_path(input_root / "manifest.sha256"),
        "method": "render every PDF page at 100 dpi; Otsu/orthogonal-stroke gridness; fixed coverage rank",
        "prohibited": ["page acceptance", "panel selection", "cropping", "controls", "transforms", "crack semantics"],
        "dates": dates,
        "script_sha256": sha256_path(Path(__file__).resolve()),
    }
    (output_root / "page_discovery_result.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(output_root)
    return payload


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
