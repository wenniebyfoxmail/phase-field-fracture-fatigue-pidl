#!/usr/bin/env python3
"""Audit InfoPave sections for repeated, fixed-panel distress-map trajectories."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE = "https://infopave.fhwa.dot.gov"
SECTION_LIST_ENDPOINT = "/Filter/getSectionListGroupByState"
DISTRESS_ENDPOINT = "/DynamicView/GetDistressImages"
ASPHALT_MARKERS = ("asphalt", "bituminous")


def post_json(endpoint: str, payload: dict[str, Any], timeout: float) -> Any:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        BASE + endpoint,
        data=body,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "ltpp-geo-forecast-candidate-audit/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    return json.loads(raw)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_panel_labels(items: list[dict[str, Any]]) -> tuple[str, ...]:
    return tuple(str(item.get("ImageDescription") or "").strip() for item in items)


def audit_section(section: dict[str, Any], payload: dict[str, Any], min_surveys: int) -> dict[str, Any]:
    constructions = payload.get("ConstructionDateList") or []
    construction_rows = []
    for construction in constructions:
        description = str(construction.get("ConstructionDescription") or "")
        surveys = construction.get("Surveys") or []
        usable = []
        for survey in surveys:
            items = survey.get("DistressItems") or []
            if items:
                usable.append(
                    {
                        "date": survey.get("SurveyDate"),
                        "event_description": survey.get("SurveyEventDescription"),
                        "panel_count": len(items),
                        "panel_labels": normalize_panel_labels(items),
                    }
                )
        label_sets = {row["panel_labels"] for row in usable}
        panel_counts = {row["panel_count"] for row in usable}
        construction_rows.append(
            {
                "construction_number": construction.get("ConstructionNumber"),
                "construction_description": description,
                "is_asphalt": any(marker in description.lower() for marker in ASPHALT_MARKERS),
                "survey_count": len(usable),
                "survey_dates": [row["date"] for row in usable],
                "panel_counts": sorted(panel_counts),
                "fixed_panel_labels": len(label_sets) == 1 and bool(usable),
                "panel_labels": list(usable[0]["panel_labels"]) if usable else [],
                "event_descriptions": sorted(
                    {str(row["event_description"] or "") for row in usable}
                ),
                "passes_geometry_inventory": (
                    any(marker in description.lower() for marker in ASPHALT_MARKERS)
                    and len(usable) >= min_surveys
                    and len(label_sets) == 1
                    and bool(usable)
                ),
            }
        )
    passing = [row for row in construction_rows if row["passes_geometry_inventory"]]
    return {
        "section": section["sectionName"],
        "ldw_section_id": int(section["sectionId"]),
        "state_code": int(section["stateCode"]),
        "construction_count": len(construction_rows),
        "constructions": construction_rows,
        "passes_geometry_inventory": bool(passing),
        "passing_construction_numbers": [row["construction_number"] for row in passing],
        "max_passing_survey_count": max(
            (row["survey_count"] for row in passing), default=0
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-code", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-surveys", type=int, default=5)
    parser.add_argument("--delay-seconds", type=float, default=0.05)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    sections = post_json(
        SECTION_LIST_ENDPOINT, {"STATE_CODE": args.state_code}, args.timeout_seconds
    )
    section_list_path = args.output / "section_list.json"
    section_list_path.write_text(
        json.dumps(sections, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    raw_dir = args.output / "distress_viewer"
    raw_dir.mkdir()
    audit_rows = []
    failures = []
    for index, section in enumerate(sections):
        section_name = str(section["sectionName"])
        try:
            payload = post_json(
                DISTRESS_ENDPOINT,
                {"LDW_SECTION_ID": str(section["sectionId"])},
                args.timeout_seconds,
            )
            raw_path = raw_dir / f"{section_name}.json"
            raw_path.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            audit_rows.append(audit_section(section, payload, args.min_surveys))
        except Exception as exc:  # fail visibly while preserving completed receipts
            failures.append(
                {
                    "section": section_name,
                    "ldw_section_id": section.get("sectionId"),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
        if index + 1 < len(sections):
            time.sleep(args.delay_seconds)

    passing = sorted(
        (row for row in audit_rows if row["passes_geometry_inventory"]),
        key=lambda row: (-row["max_passing_survey_count"], row["section"]),
    )
    summary = {
        "protocol_id": "ltpp_distress_map_candidate_audit_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "official_source": BASE + "/Media/ManualDistressSurveyViewer",
        "official_endpoints": [SECTION_LIST_ENDPOINT, DISTRESS_ENDPOINT],
        "source_release": "SDR 39",
        "state_code": args.state_code,
        "minimum_surveys": args.min_surveys,
        "criteria": {
            "asphalt_marker_in_construction_description": list(ASPHALT_MARKERS),
            "minimum_nonempty_surveys_within_one_construction": args.min_surveys,
            "identical_ordered_panel_labels_across_accepted_surveys": True,
            "not_yet_checked": [
                "pixel coordinate registration",
                "distress semantic compatibility",
                "maintenance completeness",
                "climate coverage",
                "traffic coverage",
                "FWD coverage",
            ],
        },
        "section_count": len(sections),
        "audited_count": len(audit_rows),
        "failure_count": len(failures),
        "geometry_inventory_pass_count": len(passing),
        "geometry_inventory_pass_sections": [row["section"] for row in passing],
        "decision": (
            "PASS_AT_LEAST_FIVE_GEOMETRY_INVENTORY_CANDIDATES"
            if len(passing) >= 5
            else "FAIL_FEWER_THAN_FIVE_GEOMETRY_INVENTORY_CANDIDATES"
        ),
        "claim_boundary": (
            "Inventory pass proves only repeated non-empty map availability with fixed panel labels "
            "within one asphalt construction. Every candidate still requires map registration, "
            "semantic, reset, and forcing audits."
        ),
        "passing_candidates": passing,
        "failures": failures,
    }
    summary_path = args.output / "candidate_audit.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    csv_path = args.output / "candidate_audit.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "section",
                "ldw_section_id",
                "state_code",
                "construction_count",
                "passes_geometry_inventory",
                "passing_construction_numbers",
                "max_passing_survey_count",
            ],
        )
        writer.writeheader()
        for row in sorted(audit_rows, key=lambda value: value["section"]):
            writer.writerow(
                {
                    **{key: row[key] for key in writer.fieldnames if key not in {"passing_construction_numbers"}},
                    "passing_construction_numbers": ";".join(
                        str(value) for value in row["passing_construction_numbers"]
                    ),
                }
            )

    files = sorted(path for path in args.output.rglob("*") if path.is_file())
    hash_path = args.output / "raw_files.sha256"
    hash_path.write_text(
        "".join(
            f"{sha256(path)}  {path.relative_to(args.output)}\n" for path in files
        ),
        encoding="ascii",
    )
    print(
        json.dumps(
            {
                "decision": summary["decision"],
                "section_count": len(sections),
                "audited_count": len(audit_rows),
                "failure_count": len(failures),
                "geometry_inventory_pass_count": len(passing),
                "top_candidates": [
                    [row["section"], row["max_passing_survey_count"]]
                    for row in passing[:10]
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
