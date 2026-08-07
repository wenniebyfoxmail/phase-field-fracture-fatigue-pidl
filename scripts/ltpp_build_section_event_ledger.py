#!/usr/bin/env python3
"""Build a section event ledger from frozen InfoPave timeline and map manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path


OUT_OF_STUDY = date(2011, 6, 1)
RESET_EVENT_TYPES = {
    "CONSTRUCTION",
    "MAINTENANCE",
    "REHABILITATION",
    "M_AND_R",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--map-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    timeline = json.loads(args.timeline.read_text(encoding="utf-8"))
    events = timeline.get("timelineData") or []
    map_dates = set()
    with args.map_manifest.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            map_dates.add(datetime.strptime(row["survey_date"], "%m/%d/%Y").date())

    rows = []
    for event in events:
        event_date = datetime.strptime(event["EVENT_DATE"], "%b %d %Y").date()
        event_type = str(event.get("EVENT_TYPE") or "")
        rows.append(
            {
                "event_date": event_date.isoformat(),
                "event_type": event_type,
                "event_title": event.get("EVENT_TITLE") or "",
                "event_description": event.get("EVENT_DESCRIPTION") or "",
                "data_type": event.get("DATA_TYPE") or "",
                "source_view_table": event.get("SOURCE_VIEW_TABLE_NAME") or "",
                "distress_file_id": event.get("DISTRESS_FILE_ID") or "",
                "is_selected_map_date": event_date in map_dates,
                "is_reset_candidate": event_type in RESET_EVENT_TYPES,
                "is_post_out_of_study": event_date > OUT_OF_STUDY,
                "evidence_boundary": (
                    "post_out_of_study_geometry"
                    if event_date > OUT_OF_STUDY
                    else "within_monitoring_history"
                ),
            }
        )
    rows.sort(key=lambda row: (row["event_date"], row["event_type"], row["event_title"]))
    args.output.parent.mkdir(parents=True, exist_ok=False)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    selected_timeline_dates = {
        date.fromisoformat(row["event_date"])
        for row in rows
        if row["event_type"] == "DISTRESS"
    }
    payload = {
        "protocol_id": "ltpp_06_1253_section_event_ledger_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "section": "06-1253",
        "out_of_study_date": OUT_OF_STUDY.isoformat(),
        "timeline_event_count": len(rows),
        "selected_map_dates": sorted(value.isoformat() for value in map_dates),
        "selected_map_dates_found_as_distress_events": sorted(
            value.isoformat() for value in map_dates & selected_timeline_dates
        ),
        "selected_map_dates_missing_from_distress_events": sorted(
            value.isoformat() for value in map_dates - selected_timeline_dates
        ),
        "reset_candidate_event_count": sum(row["is_reset_candidate"] for row in rows),
        "boundary": (
            "Viewer absence of maintenance or rehabilitation is not proof of no unrecorded work; "
            "post-2011-06-01 maps are retained as post-out-of-study geometry only."
        ),
        "inputs": {
            "timeline": str(args.timeline.resolve()),
            "timeline_sha256": sha256(args.timeline),
            "map_manifest": str(args.map_manifest.resolve()),
            "map_manifest_sha256": sha256(args.map_manifest),
        },
        "output": str(args.output.resolve()),
        "output_sha256": sha256(args.output),
    }
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
