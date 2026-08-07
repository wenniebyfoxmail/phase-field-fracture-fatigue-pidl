#!/usr/bin/env python3
"""Freeze candidate climate availability/timelines and apply the minimum gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


BASE = "https://infopave.fhwa.dot.gov"
TRAFFIC_ENDPOINT = "/Data/GetTrafficData"
TIMELINE_ENDPOINT = "/Data/GetTimelineData"
RESET_WORDS = (
    "maintenance",
    "rehabilitation",
    "overlay",
    "seal",
    "patch",
    "mill",
    "reconstruction",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def post_json(endpoint: str, payload: dict[str, Any], timeout: float) -> Any:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        BASE + endpoint,
        data=body,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "ltpp-geo-forecast-forcing-timeline-audit/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def timeline_all_pages(section_id: int, timeout: float) -> tuple[list[Any], list[Any]]:
    pages = []
    events = []
    seen_batches = set()
    for page in range(1, 101):
        payload = post_json(
            TIMELINE_ENDPOINT,
            {
                "sectionIDs": section_id,
                "spageNo": str(page),
                "spageSize": "100",
                "eventTitle": "",
            },
            timeout,
        )
        batch = payload.get("timelineData") or []
        batch_signature = hashlib.sha256(
            json.dumps(batch, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if batch_signature in seen_batches:
            break
        seen_batches.add(batch_signature)
        pages.append(payload)
        events.extend(batch)
        if len(batch) < 100:
            break
        time.sleep(0.05)
    else:
        raise RuntimeError(f"Timeline pagination did not terminate: {section_id}")
    return pages, events


def parse_event_date(value: str) -> date:
    return datetime.strptime(value, "%b %d %Y").date()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    minimum = int(config["minimum_climate_complete_surveys"])
    results = []

    for candidate in config["candidates"]:
        section = candidate["section"]
        section_root = args.output / section
        section_root.mkdir()
        traffic = post_json(
            TRAFFIC_ENDPOINT,
            {"stateCode": 6, "SectionID": candidate["ldw_section_id"]},
            args.timeout_seconds,
        )
        traffic_path = section_root / "traffic_climate_availability.json"
        traffic_path.write_text(
            json.dumps(traffic, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        pages, events = timeline_all_pages(
            candidate["ldw_section_id"], args.timeout_seconds
        )
        timeline_path = section_root / "timeline_pages.json"
        timeline_path.write_text(
            json.dumps(pages, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        temp_years = {int(row["Year"]) for row in traffic.get("tempRecord") or []}
        precip_years = {int(row["Year"]) for row in traffic.get("precpRecord") or []}
        survey_dates = [date.fromisoformat(value) for value in candidate["survey_dates"]]
        climate_dates = [
            value
            for value in survey_dates
            if value.year in temp_years and value.year in precip_years
        ]
        climate_complete_prefix = []
        for value in survey_dates:
            if all(
                year in temp_years and year in precip_years
                for year in range(survey_dates[0].year, value.year + 1)
            ):
                climate_complete_prefix.append(value)
            else:
                break

        first = survey_dates[0]
        last = climate_complete_prefix[-1] if climate_complete_prefix else first
        reset_candidates = []
        for event in events:
            raw_date = event.get("EVENT_DATE")
            if not raw_date:
                continue
            event_date = parse_event_date(raw_date)
            text = " ".join(
                str(event.get(key) or "")
                for key in ("EVENT_TYPE", "EVENT_TITLE", "EVENT_DESCRIPTION")
            ).lower()
            if first < event_date < last and any(word in text for word in RESET_WORDS):
                reset_candidates.append(
                    {
                        "event_date": event_date.isoformat(),
                        "event_type": event.get("EVENT_TYPE"),
                        "event_title": event.get("EVENT_TITLE"),
                        "event_description": event.get("EVENT_DESCRIPTION"),
                    }
                )

        rectification_path = args.repo_root / candidate["rectification_result"]
        rectification = json.loads(rectification_path.read_text(encoding="utf-8"))
        geometry_pass = bool(rectification.get("all_passed"))
        station_pass = str(candidate["manual_station_review"]).startswith("PASS_")
        minimum_pass = (
            geometry_pass
            and station_pass
            and len(climate_complete_prefix) >= minimum
        )
        results.append(
            {
                **candidate,
                "geometry_all_dates_passed": geometry_pass,
                "manual_station_passed": station_pass,
                "has_temperature": bool(traffic.get("hasTempData")),
                "has_precipitation": bool(traffic.get("hasPrecpData")),
                "has_humidity": bool(traffic.get("hasHumidData")),
                "has_traffic_daily_record": bool(
                    traffic.get("hasTrafficDailyRecordData")
                ),
                "climate_complete_prefix_dates": [
                    value.isoformat() for value in climate_complete_prefix
                ],
                "climate_complete_prefix_count": len(climate_complete_prefix),
                "survey_dates_with_climate_in_same_year": [
                    value.isoformat() for value in climate_dates
                ],
                "timeline_event_count": len(events),
                "reset_candidates_within_climate_complete_prefix": reset_candidates,
                "reset_review_required": bool(reset_candidates),
                "passes_minimum_geometry_climate_gate": minimum_pass,
                "claim_boundary": (
                    "Minimum pass does not clear reset candidates, map semantics, independent "
                    "vector annotation, exact interval climate extraction, or cross-section training."
                ),
            }
        )

    passing = [row for row in results if row["passes_minimum_geometry_climate_gate"]]
    summary = {
        "protocol_id": config["protocol_id"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": str(args.config.resolve()),
        "config_sha256": sha256(args.config),
        "official_sources": [BASE + TRAFFIC_ENDPOINT, BASE + TIMELINE_ENDPOINT],
        "minimum_climate_complete_surveys": minimum,
        "candidate_count": len(results),
        "minimum_gate_pass_count": len(passing),
        "minimum_gate_pass_sections": [row["section"] for row in passing],
        "decision": (
            "PASS_AT_LEAST_FIVE_MINIMUM_GEOMETRY_CLIMATE_CANDIDATES"
            if len(passing) >= 5
            else "FAIL_FEWER_THAN_FIVE_MINIMUM_GEOMETRY_CLIMATE_CANDIDATES"
        ),
        "excluded_after_visual_station_review": config.get(
            "excluded_after_visual_station_review", []
        ),
        "candidates": results,
    }
    summary_path = args.output / "multisection_gate.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    files = sorted(path for path in args.output.rglob("*") if path.is_file())
    (args.output / "raw_files.sha256").write_text(
        "".join(
            f"{sha256(path)}  {path.relative_to(args.output)}\n" for path in files
        ),
        encoding="ascii",
    )
    print(
        json.dumps(
            {
                "decision": summary["decision"],
                "minimum_gate_pass_count": len(passing),
                "sections": summary["minimum_gate_pass_sections"],
                "reset_review_sections": [
                    row["section"] for row in passing if row["reset_review_required"]
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
