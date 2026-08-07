#!/usr/bin/env python3
"""Apply the frozen dashed-grid evidence rule to all eight LTPP MVP maps.

This is a tooling-only availability inventory.  It calls the 1995-frozen
dashed-line detector unchanged, makes no cross-date correspondences, and fits
no registration transform.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np


DATES = ("19910610", "19951024", "19970228", "19980407", "20010913", "20030514", "20071106", "20120417")
STATUS = "EXPLORATORY_DASHED_GRID_EVIDENCE_INVENTORY__NOT_QUALIFIED"
DETECTOR_PATH = Path(__file__).with_name("ltpp_detect_dashed_grid_intersections.py")
SPEC = importlib.util.spec_from_file_location("ltpp_dashed_grid_detector", DETECTOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load frozen detector: {DETECTOR_PATH}")
DETECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DETECTOR)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def coverage(values: list[int], extent: int) -> float:
    return 0.0 if len(values) < 2 else float((max(values) - min(values)) / (extent - 1))


def contact_sheet(panels: list[tuple[str, np.ndarray]]) -> np.ndarray:
    rendered = []
    for date, image in panels:
        panel = cv2.resize(image, (762, 289), interpolation=cv2.INTER_AREA)
        bar = np.full((26, 762, 3), 250, dtype=np.uint8)
        cv2.putText(bar, date, (10, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (20, 20, 20), 1, cv2.LINE_AA)
        rendered.append(np.vstack((bar, panel)))
    return np.vstack([np.hstack((rendered[index], rendered[index + 1])) for index in range(0, len(rendered), 2)])


def write_manifest(root: Path) -> None:
    paths = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "manifest.sha256")
    (root / "manifest.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in paths), encoding="utf-8")


def run(mvp_root: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite inventory output: {output}")
    output.mkdir(parents=True)
    review_dir = output / "per_date_review"
    review_dir.mkdir()
    all_evidence, rows, panels = {}, [], []
    for date in DATES:
        image_path = mvp_root / "registered" / f"{date}.png"
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"cannot read upstream MVP image: {image_path}")
        evidence = DETECTOR.detect_dashed_grid(image)
        xs = [row["position_px"] for row in evidence["x_lines"] if row["accepted_dashed_grid_line"]]
        ys = [row["position_px"] for row in evidence["y_lines"] if row["accepted_dashed_grid_line"]]
        view = DETECTOR.render_review(image, evidence, f"{date}: frozen dashed-grid evidence (cyan) and accepted intersections (green)")
        review_path = review_dir / f"{date}.png"
        if not cv2.imwrite(str(review_path), view):
            raise ValueError(f"cannot write review image: {review_path}")
        panels.append((date, view))
        all_evidence[date] = evidence
        rows.append({
            "survey_date": date,
            "accepted_vertical_dashed_lines": len(xs),
            "accepted_horizontal_dashed_lines": len(ys),
            "candidate_intersection_count": len(evidence["intersections_px"]),
            "vertical_coverage_fraction": coverage(xs, image.shape[1]),
            "horizontal_coverage_fraction": coverage(ys, image.shape[0]),
            "accepted_for_next_logical_grid_matching": len(xs) >= 2 and len(ys) >= 2,
        })
    with (output / "dashed_grid_evidence.json").open("w", encoding="utf-8") as handle:
        json.dump(all_evidence, handle, indent=2)
        handle.write("\n")
    with (output / "per_date_dashed_grid_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    if not cv2.imwrite(str(output / "dashed_grid_evidence_contact_sheet.png"), contact_sheet(panels)):
        raise ValueError("cannot write contact sheet")
    result = {
        "status": STATUS,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "upstream_mvp_root": str(mvp_root.resolve()),
        "frozen_detector": str(DETECTOR_PATH.resolve()),
        "frozen_detector_sha256": sha256(DETECTOR_PATH),
        "dates": rows,
        "prohibited_claims": ["cross_date_control_correspondence", "registration_transform", "v2_final_gate", "2d_model_authorization"],
    }
    (output / "inventory_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output / "decision.md").write_text(
        "# Eight-date dashed-grid evidence inventory\n\n"
        f"## Status\n\n`{STATUS}`\n\n"
        "## Scope\n\nThe 1995-frozen dashed-line rule was applied unchanged to every date. `accepted_for_next_logical_grid_matching` means only that a date has at least two accepted horizontal and vertical line candidates. It is not a physical-coordinate, registration, or qualification decision.\n\n"
        "## Boundary\n\nNo cross-date correspondence, transform fitting, residual evaluation, or final audit is performed. v1 and v2 status remain unchanged.\n",
        encoding="utf-8",
    )
    write_manifest(output)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mvp-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.mvp_root.resolve(), args.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
