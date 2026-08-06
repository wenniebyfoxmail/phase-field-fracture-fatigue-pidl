#!/usr/bin/env python3
"""Inventory historical LTPP registration candidates without fitting a transform.

This script is deliberately diagnostic-only. It reuses the frozen v1 grid
receipt to expose candidate multiplicity and missing references, but labels all
such candidates as non-independent of v1. It never reads crack labels and never
produces a registration transform or qualification decision.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


DATES = (
    "19910610", "19951024", "19970228", "19980407",
    "20010913", "20030514", "20071106", "20120417",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory_row(row: dict) -> dict:
    records = []
    for axis, key, count in (
        ("x", "detected_vertical_positions", 11),
        ("y", "detected_horizontal_positions", 6),
    ):
        start = float(row[f"{axis}0"])
        end = float(row[f"{axis}1"])
        spacing = (end - start) / (count - 1)
        tolerance = 0.18 * spacing
        positions = [float(value) for value in row[key]]
        for index in range(count):
            nominal = start + index * spacing
            candidates = sorted(
                value for value in positions if abs(value - nominal) <= tolerance
            )
            records.append({
                "axis": axis,
                "index": index,
                "nominal_pixel": nominal,
                "candidate_count": len(candidates),
                "candidate_pixels": candidates,
                "historical_v1_status": "non_independent_of_v1",
                "final_v2_eligibility": "not_eligible_without_independent_adjudication",
            })
    missing = sum(item["candidate_count"] == 0 for item in records)
    ambiguous = sum(item["candidate_count"] > 1 for item in records)
    unique = sum(item["candidate_count"] == 1 for item in records)
    return {
        "survey_date": row["survey_date"],
        "qualification_mode_v1": row["qualification_mode"],
        "source_sha256": row["source_sha256"],
        "source_shape_px": [row["source_height"], row["source_width"]],
        "crop_shape_px": [row["y1"] - row["y0"], row["x1"] - row["x0"]],
        "v1_detected_line_count": len(records),
        "candidate_lines_missing": missing,
        "candidate_lines_unique": unique,
        "candidate_lines_ambiguous": ambiguous,
        "independent_final_controls_available": False,
        "reason": "v1 candidate receipt was observed before v2; independent Tier A/B adjudication is required",
        "line_candidates": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid-results", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    grid_path = args.grid_results.resolve()
    preregistration_path = args.preregistration.resolve()
    payload = json.loads(grid_path.read_text(encoding="utf-8"))
    rows = {row["survey_date"]: row for row in payload["results"]}
    if tuple(sorted(rows))[:8] != DATES or any(date not in rows for date in DATES):
        raise ValueError("the frozen eight-date v1 receipt is required")
    inventories = [inventory_row(rows[date]) for date in DATES]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    receipt = {
        "status": "EXPLORATORY_REGISTRATION_IMPROVEMENT",
        "diagnostic_kind": "historical_v1_candidate_inventory_only",
        "grid_results": str(grid_path),
        "grid_results_sha256": sha256(grid_path),
        "preregistration": str(preregistration_path),
        "preregistration_sha256": sha256(preregistration_path),
        "script": str(Path(__file__).resolve()),
        "script_sha256": sha256(Path(__file__).resolve()),
        "date_count": len(inventories),
        "independent_final_controls_available": False,
        "termination": "no transform fitting, no final gate, no 2-D model authorization",
        "inventories": inventories,
    }
    (output / "control_inventory.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    with (output / "control_inventory.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "survey_date", "qualification_mode_v1", "candidate_lines_missing",
            "candidate_lines_unique", "candidate_lines_ambiguous",
            "independent_final_controls_available", "reason",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in inventories:
            writer.writerow({key: item[key] for key in fields})
    decision = (
        "# v2 control-point availability diagnostic\n\n"
        "## Decision\n\n"
        "`EXPLORATORY_REGISTRATION_IMPROVEMENT`\n\n"
        "The inventory reuses historical v1 detector candidates only to expose "
        "missing and ambiguous references. These candidates are not independent "
        "final v2 controls. No transform was fitted and no 2-D model route was "
        "opened. Independent Tier A/B adjudication is still required for every date.\n"
    )
    (output / "decision.md").write_text(decision, encoding="utf-8")
    files = sorted(
        path for path in output.iterdir()
        if path.is_file() and path.name != "manifest.sha256"
    )
    (output / "manifest.sha256").write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in files),
        encoding="utf-8",
    )
    print(json.dumps({
        "status": receipt["status"],
        "date_count": receipt["date_count"],
        "independent_final_controls_available": False,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
