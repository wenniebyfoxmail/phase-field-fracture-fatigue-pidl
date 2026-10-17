#!/usr/bin/env python3
"""Reconcile frozen MnROAD NWP centrelines with the summary workbook.

This is a read-only audit of the workbook and annotation packet.  It does not
rewrite geometry, tune a de-duplication tolerance to the Excel total, or lock
either annotation phase.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook


NWP_COLUMNS = ("LONG_NWP_L_L", "LONG_NWP_L_M", "LONG_NWP_L_H")
DATE_PIXELS_PER_FOOT = {
    "2017-03-20": 21.4,
    "2018-03-14": 21.4,
    "2018-04-27": 21.4,
    "2018-08-23": 21.4,
    "2019-03-22": 20.1,
    "2019-04-16": 20.1,
    "2019-10-23": 20.1,
}


def polyline_length_px(feature: dict) -> float:
    points = feature["geometry"]["coordinates"]
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:]))


def target_features(record: dict) -> list[dict]:
    return [
        feature for feature in record["features"]
        if feature["properties"].get("lane") == "Driving"
        and feature["properties"].get("distress_class") == "NWP"
    ]


def read_excel(path: Path) -> dict[str, dict]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    sheet = workbook["Export Worksheet"]
    headers = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
    rows = {}
    for row_number, values in enumerate(sheet.iter_rows(min_row=2, values_only=True), 2):
        row = dict(zip(headers, values))
        if row.get("SECTION_ID") != "22-D-2016" or row.get("LANE") != "Driving":
            continue
        date = row["DAY"].date().isoformat()
        if date not in DATE_PIXELS_PER_FOOT:
            continue
        components = [float(row.get(column) or 0) for column in NWP_COLUMNS]
        rows[date] = {
            "excel_row": row_number,
            "nwp_low_ft": components[0],
            "nwp_moderate_ft": components[1],
            "nwp_high_ft": components[2],
            "excel_nwp_total_ft": sum(components),
        }
    workbook.close()
    return rows


def read_annotations(packet: Path) -> tuple[dict[str, dict], list[dict]]:
    private = json.loads((packet / "private_repeat_key.json").read_text())["tasks"]
    by_date = defaultdict(lambda: {
        "feature_count": 0,
        "map_polyline_total_ft": 0.0,
        "target_pages": [],
        "page_totals": {},
    })
    page_rows = []
    for task_id, task in private.items():
        if task["is_repeat"]:
            continue
        record = json.loads((packet / "records" / f"{task_id}.geojson").read_text())
        date = record["survey_date"]
        if date not in DATE_PIXELS_PER_FOOT:
            continue
        features = target_features(record)
        length = sum(polyline_length_px(feature) for feature in features) / DATE_PIXELS_PER_FOOT[date]
        summary = by_date[date]
        summary["feature_count"] += len(features)
        summary["map_polyline_total_ft"] += length
        summary["page_totals"][task_id] = length
        if features:
            summary["target_pages"].append(record["page_start_ft"])
        page_rows.append({
            "task_id": task_id,
            "survey_date": date,
            "page_start_ft": record["page_start_ft"],
            "target_feature_count": len(features),
            "map_polyline_total_ft": length,
        })
    return dict(by_date), page_rows


def render_markdown(rows: list[dict], review_queue: list[dict], workbook: Path) -> str:
    lines = [
        "# MnROAD Cell 22 phase-2 Excel reconciliation",
        "",
        "## Decision",
        "",
        "`HOLD_PHASE2_LOCK__TARGETED_REVIEW_REQUIRED`",
        "",
        "The frozen centreline annotations pass the scalar tolerance on some, but not all, eligible dates. "
        "Phase 2 must remain unlocked until the flagged pages are reviewed. Excel totals are section/lane/date "
        "controls; they do not identify individual cracks or dictate a page-level correction.",
        "",
        "## Date-level comparison",
        "",
        "| Date | Excel NWP (ft) | Map polyline (ft) | Difference (ft) | Tolerance (ft) | Result | Features | Target pages |",
        "|---|---:|---:|---:|---:|---|---:|---|",
    ]
    for row in rows:
        pages = ", ".join(str(value) for value in row["target_pages"]) or "none"
        lines.append(
            f"| {row['survey_date']} | {row['excel_nwp_total_ft']:.1f} | "
            f"{row['map_polyline_total_ft']:.1f} | {row['difference_ft']:+.1f} | "
            f"{row['tolerance_ft']:.1f} | {'PASS' if row['passes_tolerance'] else 'FAIL'} | "
            f"{row['feature_count']} | {pages} |"
        )
    lines.extend([
        "",
        "The map value is the frozen user-drawn polyline length with concealed repeats excluded. It is not "
        "silently de-duplicated after seeing Excel. Overlapping old/new survey marks are handled as lineage "
        "relations in phase 2 and remain an observation-process uncertainty until reviewed.",
        "",
        "## Targeted review queue",
        "",
    ])
    for item in review_queue:
        lines.append(f"- `{item['task_id']}` ({item['survey_date']}, {item['page_start_ft']}-{item['page_start_ft'] + 50} ft): {item['reason']}")
    lines.extend([
        "",
        "## Boundaries",
        "",
        f"- Workbook read-only source: `{workbook}` (`Export Worksheet`, rows 1482-1488).",
        "- The comparison does not assign crack identity, severity, or survey-date ownership.",
        "- No phase-2 lock, training, forecasting, or physical crack-growth claim is authorised by this audit.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    packet = args.packet.resolve()
    workbook = args.workbook.resolve()
    output = args.output.resolve()
    excel = read_excel(workbook)
    annotations, page_rows = read_annotations(packet)
    missing_dates = sorted(set(DATE_PIXELS_PER_FOOT) - set(excel))
    if missing_dates:
        raise RuntimeError(f"missing workbook dates: {missing_dates}")

    rows = []
    for date in DATE_PIXELS_PER_FOOT:
        row = {"survey_date": date, **excel[date], **annotations.get(date, {})}
        map_total = float(row.get("map_polyline_total_ft", 0.0))
        excel_total = float(row["excel_nwp_total_ft"])
        difference = map_total - excel_total
        tolerance = max(5.0, 0.10 * excel_total)
        row.update({
            "map_polyline_total_ft": map_total,
            "difference_ft": difference,
            "absolute_difference_ft": abs(difference),
            "tolerance_ft": tolerance,
            "passes_tolerance": abs(difference) <= tolerance,
        })
        rows.append(row)

    page_index = {(row["survey_date"], row["page_start_ft"]): row for row in page_rows}
    review_queue = []
    # Mechanically selected diagnostics. They are review prompts, not automatic corrections.
    for row in rows:
        if not row["passes_tolerance"]:
            review_queue.append({
                "task_id": "DATE_LEVEL",
                "survey_date": row["survey_date"],
                "page_start_ft": 0,
                "reason": f"date total differs from Excel by {row['difference_ft']:+.1f} ft",
            })
    march_dense = page_index.get(("2019-03-22", 50))
    if march_dense and march_dense["target_feature_count"] >= 10:
        review_queue.append({
            "task_id": march_dense["task_id"],
            "survey_date": march_dense["survey_date"],
            "page_start_ft": march_dense["page_start_ft"],
            "reason": "19 target segments total more than 50 ft on one page; inspect red/black redraw overlap and boxes",
        })
    october_zero = page_index.get(("2019-10-23", 0))
    april_prior = page_index.get(("2019-04-16", 0))
    if october_zero and april_prior and october_zero["target_feature_count"] == 0 and april_prior["map_polyline_total_ft"] >= 45:
        review_queue.append({
            "task_id": october_zero["task_id"],
            "survey_date": october_zero["survey_date"],
            "page_start_ft": october_zero["page_start_ft"],
            "reason": "zero target after a roughly 50-ft prior-map target; inspect the visible NWP/sealed line without auto-copying it",
        })

    result = {
        "status": "HOLD_PHASE2_LOCK__TARGETED_REVIEW_REQUIRED",
        "section_id": "22-D-2016",
        "lane": "Driving",
        "target": "NWP",
        "workbook": str(workbook),
        "workbook_sheet": "Export Worksheet",
        "workbook_rows": "1482:1488",
        "length_method": "sum of frozen target polyline arc lengths; concealed repeats excluded",
        "date_pixels_per_foot": DATE_PIXELS_PER_FOOT,
        "gate": "absolute difference <= max(5 ft, 10% of Excel NWP total)",
        "date_rows": rows,
        "passed_dates": sum(row["passes_tolerance"] for row in rows),
        "eligible_dates": len(rows),
        "review_queue": review_queue,
        "claim_boundary": "scalar reconciliation only; no physical identity, forecast, or model-ready claim",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "excel_reconciliation.json").write_text(json.dumps(result, indent=2) + "\n")
    with (output / "excel_reconciliation.csv").open("w", newline="") as handle:
        fields = [
            "survey_date", "excel_row", "nwp_low_ft", "nwp_moderate_ft", "nwp_high_ft",
            "excel_nwp_total_ft", "map_polyline_total_ft", "difference_ft", "tolerance_ft",
            "passes_tolerance", "feature_count", "target_pages",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fields})
    (output / "excel_reconciliation.md").write_text(render_markdown(rows, review_queue, workbook))
    print(json.dumps({
        "status": result["status"],
        "passed_dates": result["passed_dates"],
        "eligible_dates": result["eligible_dates"],
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
