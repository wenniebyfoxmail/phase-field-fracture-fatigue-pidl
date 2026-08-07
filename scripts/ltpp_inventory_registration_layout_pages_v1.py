#!/usr/bin/env python3
"""Inventory printed-grid observability over all official pages per survey date.

This is a read-only acquisition diagnostic.  It composites transparent source
PNGs onto white only for detection, finds the same printed layout candidates as
the frozen rectification receipt, and never fits a cross-date transform.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np


DATES = ("19910610", "19951024", "19970228", "19980407", "20010913", "20030514", "20071106", "20120417")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_rectifier(script: Path):
    spec = importlib.util.spec_from_file_location("ltpp_rectifier_layout_inventory", script)
    if spec is None or spec.loader is None:
        raise ValueError("cannot import rectifier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def white_gray(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"cannot read {path}")
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"expected RGBA source image: {path}")
    alpha = image[:, :, 3:4].astype(np.float32) / 255.0
    bgr = image[:, :, :3].astype(np.float32)
    composited = (bgr * alpha + 255.0 * (1.0 - alpha)).astype(np.uint8)
    return cv2.cvtColor(composited, cv2.COLOR_BGR2GRAY)


def page_quality(path: Path, rectifier) -> dict:
    gray = white_gray(path)
    angle = rectifier.estimate_deskew(gray)
    deskewed = rectifier.rotate_bound(gray, angle)
    _, binary = cv2.threshold(deskewed, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    vertical = rectifier.line_positions(binary, "vertical")
    horizontal = rectifier.line_positions(binary, "horizontal")
    try:
        x_item, y_item = rectifier.choose_rectangle(vertical, horizontal, deskewed.shape[1], deskewed.shape[0])
        _, x0, x1, vertical_matches, vertical_rmse = x_item
        _, y0, y1, horizontal_matches, horizontal_rmse = y_item
        support = rectifier.border_support(binary, x0, y0, x1, y1)
        status = "DENSE_PRINTED_GRID" if vertical_matches >= 8 and horizontal_matches >= 5 else "PARTIAL_PRINTED_GRID"
    except ValueError:
        vertical_matches = horizontal_matches = 0
        vertical_rmse = horizontal_rmse = support = None
        status = "NO_REGULAR_LAYOUT"
    return {
        "source_path": str(path.resolve()), "source_sha256": sha256(path),
        "page": path.stem, "deskew_angle_deg": angle,
        "vertical_grid_matches": vertical_matches, "horizontal_grid_matches": horizontal_matches,
        "vertical_grid_rmse_px": vertical_rmse, "horizontal_grid_rmse_px": horizontal_rmse,
        "border_ink_support": support, "status": status,
    }


def date_summary(date: str, pages: list[dict]) -> dict:
    dense = [row for row in pages if row["status"] == "DENSE_PRINTED_GRID"]
    vertical_any = [row for row in pages if row["vertical_grid_matches"] >= 8]
    if not vertical_any:
        conclusion = "NO_DATE_LEVEL_VERTICAL_GRID_SUPPORT"
    elif len(dense) == len(pages):
        conclusion = "CONSISTENT_PRINTED_LAYOUT_CANDIDATE"
    else:
        conclusion = "PARTIAL_DATE_LAYOUT_CANDIDATE"
    return {
        "survey_date": date, "page_count": len(pages), "dense_grid_page_count": len(dense),
        "vertical_grid_page_count": len(vertical_any), "max_vertical_matches": max(row["vertical_grid_matches"] for row in pages),
        "max_horizontal_matches": max(row["horizontal_grid_matches"] for row in pages),
        "conclusion": conclusion,
        "claim_boundary": "same-date layout observability only; does not validate a 0-50 transform or cross-date physical registration",
    }


def write_manifest(root: Path) -> None:
    paths = sorted(path for path in root.iterdir() if path.is_file() and path.name != "manifest.sha256")
    (root / "manifest.sha256").write_text("".join(f"{sha256(path)}  {path.name}\n" for path in paths), encoding="utf-8")


def run(source_root: Path, rectifier_script: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite output: {output}")
    rectifier = load_rectifier(rectifier_script)
    per_page, summaries = [], []
    for date in DATES:
        pages = sorted(path for path in (source_root / date).glob("segment_*.png") if not path.name.endswith("_white.png"))
        if len(pages) != 10:
            raise ValueError(f"expected ten official pages for {date}, found {len(pages)}")
        rows = [page_quality(path, rectifier) for path in pages]
        for row in rows:
            row["survey_date"] = date
        per_page.extend(rows)
        summaries.append(date_summary(date, rows))
    output.mkdir(parents=True)
    with (output / "per_page_grid_quality.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(per_page[0])); writer.writeheader(); writer.writerows(per_page)
    with (output / "per_date_layout_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0])); writer.writeheader(); writer.writerows(summaries)
    result = {
        "status": "EXPLORATORY_REGISTRATION_LAYOUT_AVAILABILITY_ONLY",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": str(source_root.resolve()), "rectifier_script": str(rectifier_script.resolve()),
        "rectifier_script_sha256": sha256(rectifier_script), "date_count": len(summaries), "page_count": len(per_page),
        "per_date": summaries,
        "prohibited": ["cross_date_transform_fit", "crack_control", "v2_final_control_claim", "2d_model_authorization"],
    }
    (output / "layout_inventory_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output / "decision.md").write_text(
        "# LTPP same-date printed-layout availability diagnostic\n\n"
        "## Status\n\n`EXPLORATORY_REGISTRATION_LAYOUT_AVAILABILITY_ONLY`\n\n"
        "## Result\n\nThe diagnostic inventories 10 official 50-ft pages for each of the eight dates. It distinguishes page-level grid loss from dates whose whole official page set lacks a usable vertical printed grid. It does not fit a transform or establish cross-date physical correspondence.\n\n"
        "## Consequence\n\nA future exploratory same-date layout template is potentially supportable only where the summary records vertical-grid support. Dates without such support require a different non-damage reference source; no control may be manufactured from cracks or annotations.\n",
        encoding="utf-8",
    )
    write_manifest(output)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--rectifier-script", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.source_root.resolve(), args.rectifier_script.resolve(), args.output.resolve())
    print(json.dumps({"status": result["status"], "summaries": result["per_date"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
