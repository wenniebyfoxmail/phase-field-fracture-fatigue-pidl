#!/usr/bin/env python3
"""Apply the frozen solid-road-frame review rule to the eight LTPP dates.

This is a source-range diagnostic only.  It does not crop an image, extract
control points, estimate a registration transform, or evaluate a final gate.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np


DATES = ("19910610", "19951024", "19970228", "19980407", "20010913", "20030514", "20071106", "20120417")
STATUS = "EXPLORATORY_SOLID_OUTER_BOUNDARY_INVENTORY__NOT_QUALIFIED"
BOUNDARY_SCRIPT = Path(__file__).with_name("ltpp_review_1991_solid_outer_boundary.py")
SPEC = importlib.util.spec_from_file_location("ltpp_solid_outer_boundary", BOUNDARY_SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load frozen boundary rule: {BOUNDARY_SCRIPT}")
BOUNDARY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOUNDARY)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def render_review(date: str, deskewed: np.ndarray, rectangle: tuple[int, int, int, int]) -> np.ndarray:
    """Render the same orange-range-only review for each date."""
    left, top, right, bottom = rectangle
    view = cv2.cvtColor(deskewed, cv2.COLOR_GRAY2BGR)
    cv2.rectangle(view, (left, top), (right, bottom), (0, 140, 255), 5, cv2.LINE_AA)
    for label, point in (("O1", (left, top)), ("O2", (right, top)), ("O3", (right, bottom)), ("O4", (left, bottom))):
        cv2.circle(view, point, 14, (0, 140, 255), -1, cv2.LINE_AA)
        cv2.putText(view, label, (point[0] + 12, point[1] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 140, 255), 2, cv2.LINE_AA)
    header = np.full((95, view.shape[1], 3), 250, dtype=np.uint8)
    cv2.putText(header, f"{date} solid outer-boundary review: confirm range before clipping", (18, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (20, 20, 20), 2, cv2.LINE_AA)
    cv2.putText(header, "orange O1-O4 = frozen outer solid-rectangle rule; no controls or crop shown", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (20, 20, 20), 1, cv2.LINE_AA)
    cv2.putText(header, "Check: covers the road grid and nearby cracks; excludes page headers and side table.", (18, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (20, 20, 20), 1, cv2.LINE_AA)
    return np.vstack((header, view))


def render_no_candidate_review(date: str, deskewed: np.ndarray, error: str) -> np.ndarray:
    """Render an explicit fail-closed page when the frozen rule finds no frame."""
    view = cv2.cvtColor(deskewed, cv2.COLOR_GRAY2BGR)
    header = np.full((95, view.shape[1], 3), 250, dtype=np.uint8)
    cv2.putText(header, f"{date} solid outer-boundary review: NO CANDIDATE", (18, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 0, 190), 2, cv2.LINE_AA)
    cv2.putText(header, "frozen rule found no aspect-compatible solid rectangle; no fallback or tuning applied", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (20, 20, 20), 1, cv2.LINE_AA)
    cv2.putText(header, error[:140], (18, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (20, 20, 20), 1, cv2.LINE_AA)
    return np.vstack((header, view))


def sidecar(date: str, has_candidate: bool) -> str:
    candidate_text = "Orange is the proposed outer road range only." if has_candidate else "No orange rectangle is shown because the frozen rule returned no candidate."
    return f"""# {date} solid outer-boundary review\n\n## Question\n\nDoes the frozen, non-damage outer-solid-rectangle rule locate the road-map range on this date's original 0–50 ft LTPP page?\n\n## Data provenance\n\nInput is `{date}/segment_0_50_white.png`, a white composite of the official transparent PNG. An orange O1–O4 rectangle, if present, is found after deskew using continuous solid ink and the fixed aspect range already accepted on 1991.\n\n## How to read\n\n{candidate_text} It is not a crop and does not denote controls, registration residuals, or crack labels. The reviewer should check that an orange candidate encloses the printed road grid and any nearby crack ink while excluding header/side-table paper content.\n\n## Main takeaway\n\nThis is the frozen-rule range candidate or its explicit no-candidate result for one date.\n\n## Limitation\n\nThe image is a source-range diagnostic only; a visible candidate has not yet passed human review and is not suitable for crop, registration, or control-point claims.\n\n## Claim boundary\n\n`EXPLORATORY_SOLID_OUTER_BOUNDARY_INVENTORY__NOT_QUALIFIED`: this figure does not qualify 2-D registration or a 2-D model.\n"""


def write_manifest(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "manifest.sha256")
    (root / "manifest.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in files), encoding="utf-8")


def contact_sheet(reviews: list[tuple[str, np.ndarray]]) -> np.ndarray:
    """Make a legible two-column overview; full-size individual reviews remain primary."""
    cell_width, cell_height = 1100, 480
    sheet = np.full((cell_height * 4, cell_width * 2, 3), 235, dtype=np.uint8)
    for index, (date, review) in enumerate(reviews):
        scale = min(cell_width / review.shape[1], cell_height / review.shape[0])
        resized = cv2.resize(review, (round(review.shape[1] * scale), round(review.shape[0] * scale)), interpolation=cv2.INTER_AREA)
        row, column = divmod(index, 2)
        x = column * cell_width + (cell_width - resized.shape[1]) // 2
        y = row * cell_height + (cell_height - resized.shape[0]) // 2
        sheet[y:y + resized.shape[0], x:x + resized.shape[1]] = resized
        cv2.putText(sheet, date, (column * cell_width + 14, row * cell_height + 34), cv2.FONT_HERSHEY_SIMPLEX, 0.84, (20, 20, 20), 2, cv2.LINE_AA)
    return sheet


def run(input_root: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite output: {output}")
    output.mkdir(parents=True)
    records: list[dict] = []
    reviews: list[tuple[str, np.ndarray]] = []
    receipts: list[str] = [f"{sha256(Path(__file__).resolve())}  script/{Path(__file__).name}\n", f"{sha256(BOUNDARY_SCRIPT)}  script/{BOUNDARY_SCRIPT.name}\n"]
    for date in DATES:
        image_path = input_root / date / "segment_0_50_white.png"
        source = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if source is None:
            raise ValueError(f"cannot read {image_path}")
        receipts.append(f"{sha256(image_path)}  input/{date}/segment_0_50_white.png\n")
        angle = BOUNDARY.LATTICE.estimate_deskew(source)
        deskewed = BOUNDARY.LATTICE.rotate_bound(source, angle)
        base = {"date": date, "input": str(image_path), "input_sha256": sha256(image_path), "deskew_angle_deg": angle}
        try:
            rectangle, details = BOUNDARY.outer_solid_rectangle(deskewed)
            left, top, right, bottom = rectangle
            review = render_review(date, deskewed, rectangle)
            record = base | {"left_px": left, "top_px": top, "right_px": right, "bottom_px": bottom, "width_px": right - left, "height_px": bottom - top, "aspect": details["aspect"], "left_support_px": details["vertical_continuous_support_px"]["left"], "right_support_px": details["vertical_continuous_support_px"]["right"], "top_support_px": details["horizontal_continuous_support_px"]["top"], "bottom_support_px": details["horizontal_continuous_support_px"]["bottom"], "review_status": "REQUIRES_HUMAN_RANGE_REVIEW", "error": ""}
            has_candidate = True
        except ValueError as error:
            review = render_no_candidate_review(date, deskewed, str(error))
            record = base | {"left_px": "", "top_px": "", "right_px": "", "bottom_px": "", "width_px": "", "height_px": "", "aspect": "", "left_support_px": "", "right_support_px": "", "top_support_px": "", "bottom_support_px": "", "review_status": "NO_CANDIDATE__FAIL_CLOSED", "error": str(error)}
            has_candidate = False
        image_name = f"{date}_solid_outer_boundary_review.png"
        if not cv2.imwrite(str(output / image_name), review):
            raise ValueError(f"cannot write {image_name}")
        (output / f"{date}_solid_outer_boundary_review.md").write_text(sidecar(date, has_candidate), encoding="utf-8")
        records.append(record)
        reviews.append((date, review))
    if not cv2.imwrite(str(output / "eight_date_solid_outer_boundary_overview.png"), contact_sheet(reviews)):
        raise ValueError("cannot write contact-sheet overview")
    (output / "eight_date_solid_outer_boundary_overview.md").write_text("# Eight-date solid outer-boundary overview\n\n## Question\n\nWhich dates have a plausible orange source-range candidate under the fixed outer-solid-rectangle rule?\n\n## Data provenance\n\nThe eight panels are reduced renderings of the full-size date-specific reviews generated from the official source pages using the frozen boundary script.\n\n## How to read\n\nEach panel is a reduced copy of its full-size review. Orange denotes a proposed range; a `NO CANDIDATE` panel deliberately has no rectangle. The full-size per-date PNG is the review authority.\n\n## Main takeaway\n\nThe overview lets a reviewer compare candidate extent across the full eight-date set before any later control-point work.\n\n## Limitation\n\nThe reduced overview cannot settle edge placement; it is only a navigation aid to the full-resolution date-specific review PNGs.\n\n## Claim boundary\n\nThis is an exploratory source-range diagnostic, not registration, a control-point set, or a 2-D model qualification.\n", encoding="utf-8")
    with (output / "per_date_boundary_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    result = {"status": STATUS, "date_count": len(records), "segment": "0-50 feet", "frozen_rule_source": str(BOUNDARY_SCRIPT), "records": records, "prohibited_claims": ["cropping_authorization", "control_extraction", "registration_transform", "v2_final_gate", "2d_model_authorization"]}
    (output / "outer_boundary_inventory_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output / "decision.md").write_text("# LTPP eight-date solid outer-boundary inventory\n\n`EXPLORATORY_SOLID_OUTER_BOUNDARY_INVENTORY__NOT_QUALIFIED`\n\nThe exact 1991-accepted solid-rectangle rule was applied once, unchanged, to each original 0–50 ft source page. Each resulting orange-frame review requires human range confirmation before any crop or grid-control candidate extraction. No registration transform or final audit was run.\n", encoding="utf-8")
    (output / "input_and_code_receipt.sha256").write_text("".join(receipts), encoding="utf-8")
    write_manifest(output)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.input_root.resolve(), args.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
