#!/usr/bin/env python3
"""Join frozen adjudicated geometry to leakage-safe climate intervals."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path


CRACK_FAMILIES = {
    "transverse_crack",
    "longitudinal_crack",
    "fatigue_or_alligator_crack",
    "block_crack",
    "other_crack",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def line_length(coordinates: list[list[float]]) -> float:
    return sum(
        math.hypot(second[0] - first[0], second[1] - first[1])
        for first, second in zip(coordinates, coordinates[1:])
    )


def polygon_area(ring: list[list[float]]) -> float:
    return abs(
        sum(
            first[0] * second[1] - second[0] * first[1]
            for first, second in zip(ring, ring[1:])
        )
    ) / 2.0


def geometry_summary(payload: dict) -> dict:
    families = Counter()
    crack_line_length = 0.0
    crack_area = 0.0
    crack_line_count = 0
    crack_area_count = 0
    uncertain_line_length = 0.0
    uncertain_area = 0.0
    for feature in payload.get("features", []):
        family = feature["properties"]["distress_family"]
        families[family] += 1
        geometry = feature["geometry"]
        if geometry["type"] == "LineString":
            length = line_length(geometry["coordinates"])
            if family in CRACK_FAMILIES:
                crack_line_length += length
                crack_line_count += 1
            elif family == "uncertain":
                uncertain_line_length += length
        elif geometry["type"] == "Polygon":
            area = polygon_area(geometry["coordinates"][0])
            if family in CRACK_FAMILIES:
                crack_area += area
                crack_area_count += 1
            elif family == "uncertain":
                uncertain_area += area
        else:
            raise ValueError(f"Unsupported geometry type: {geometry['type']}")
    return {
        "crack_line_count": crack_line_count,
        "crack_area_count": crack_area_count,
        "crack_line_length_m": crack_line_length,
        "crack_area_m2": crack_area,
        "uncertain_line_length_m": uncertain_line_length,
        "uncertain_area_m2": uncertain_area,
        "family_counts": dict(sorted(families.items())),
    }


def parse_event_date(value: str) -> date:
    return datetime.strptime(value, "%b %d %Y").date()


def section_timeline_flags(gate_root: Path, section: str) -> dict:
    path = gate_root / section / "timeline_pages.json"
    pages = load_json(path)
    events = [event for page in pages for event in page.get("timelineData", [])]
    dates = []
    for event in events:
        text = " ".join(
            str(event.get(key) or "")
            for key in ("EVENT_TYPE", "EVENT_TITLE", "EVENT_DESCRIPTION")
        ).lower()
        if "out-of-study" in text or "out of study" in text:
            dates.append(parse_event_date(event["EVENT_DATE"]))
    return {
        "timeline_path": str(path),
        "timeline_sha256": sha256(path),
        "out_of_study_date": min(dates).isoformat() if dates else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adjudicated-root", type=Path, required=True)
    parser.add_argument("--climate", type=Path, required=True)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    adjudicated_root = args.adjudicated_root.resolve()
    manifest_path = adjudicated_root / "adjudicated_manifest.json"
    if not manifest_path.exists():
        print(json.dumps({"status": "BLOCKED_NO_ADJUDICATED_MANIFEST"}))
        return 42
    manifest = load_json(manifest_path)
    if manifest.get("status") != "PASS_ADJUDICATED_LABELS_FROZEN":
        raise ValueError("Adjudicated manifest is not qualified")
    climate_path = args.climate.resolve()
    climate = load_json(climate_path)
    if climate.get("status") != "PASS_31_LEAKAGE_SAFE_CLIMATE_INTERVALS":
        raise ValueError("Climate interval package is not qualified")
    gate_path = args.gate.resolve()
    gate = load_json(gate_path)
    gate_root = gate_path.parent
    candidate_by_section = {row["section"]: row for row in gate["candidates"]}

    states = {}
    for row in manifest["files"]:
        path = adjudicated_root / row["file"]
        payload = load_json(path)
        props = payload["properties"]
        key = (props["section"], props["survey_date"])
        if key in states:
            raise ValueError(f"Duplicate adjudicated state: {key}")
        states[key] = {
            "path": path,
            "sha256": sha256(path),
            "payload": payload,
            "summary": geometry_summary(payload),
        }
    if len(states) != 37:
        raise ValueError(f"Expected 37 adjudicated states, found {len(states)}")

    transitions = []
    for climate_row in climate["intervals"]:
        section = climate_row["section"]
        source_key = (section, climate_row["source_survey"])
        target_key = (section, climate_row["target_survey"])
        if source_key not in states or target_key not in states:
            raise ValueError(f"Missing state for transition {climate_row['transition_id']}")
        source = states[source_key]
        target = states[target_key]
        source_summary = source["summary"]
        target_summary = target["summary"]
        timeline = section_timeline_flags(gate_root, section)
        out_date = date.fromisoformat(timeline["out_of_study_date"]) if timeline["out_of_study_date"] else None
        source_date = date.fromisoformat(climate_row["source_survey"])
        target_date = date.fromisoformat(climate_row["target_survey"])
        candidate = candidate_by_section[section]
        transition = {
            "transition_id": climate_row["transition_id"],
            "section": section,
            "construction_number": climate_row["construction_number"],
            "panel_start_ft": 0,
            "source_survey": climate_row["source_survey"],
            "target_survey": climate_row["target_survey"],
            "duration_days": climate_row["duration_days"],
            "duration_years": climate_row["duration_years"],
            "source_geojson": str(source["path"]),
            "source_geojson_sha256": source["sha256"],
            "target_geojson": str(target["path"]),
            "target_geojson_sha256": target["sha256"],
            "source_geometry": source_summary,
            "target_geometry": target_summary,
            "raw_total_crack_length_change_m": target_summary["crack_line_length_m"] - source_summary["crack_line_length_m"],
            "positive_total_crack_length_increment_m": max(0.0, target_summary["crack_line_length_m"] - source_summary["crack_line_length_m"]),
            "raw_crack_area_change_m2": target_summary["crack_area_m2"] - source_summary["crack_area_m2"],
            "climate": {
                key: climate_row[key]
                for key in (
                    "endpoint_rule",
                    "boundary_month_rule",
                    "temperature_coverage_fraction",
                    "precipitation_coverage_fraction",
                    "temperature_change_coverage_fraction",
                    "mean_temperature_C",
                    "low_temp_exposure_5_C_day_per_year",
                    "low_temp_exposure_10_C_day_per_year",
                    "low_temp_exposure_15_C_day_per_year",
                    "abs_temperature_change_C_per_year",
                    "precipitation_mm_per_year",
                )
            },
            "traffic_observation": None,
            "traffic_missing": True,
            "fwd_observation": None,
            "fwd_missing": True,
            "humidity_observation": None,
            "humidity_missing": True,
            "pavement_moisture_observation": None,
            "pavement_moisture_missing": True,
            "maintenance_reset_candidate_count": len(candidate["reset_candidates_within_climate_complete_prefix"]),
            "maintenance_reset_detected": bool(candidate["reset_candidates_within_climate_complete_prefix"]),
            "out_of_study_date": timeline["out_of_study_date"],
            "out_of_study_within_interval": bool(out_date and source_date < out_date <= target_date),
            "target_after_out_of_study": bool(out_date and target_date >= out_date),
            "timeline_path": timeline["timeline_path"],
            "timeline_sha256": timeline["timeline_sha256"],
            "development_transition": climate_row["development_transition"],
            "future_time_test": climate_row["future_time_test"],
        }
        transitions.append(transition)
    if len(transitions) != 31:
        raise ValueError(f"Expected 31 joined transitions, found {len(transitions)}")

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    transitions_path = output / "transitions.json"
    transitions_path.write_text(json.dumps(transitions, indent=2) + "\n", encoding="utf-8")
    scalar_rows = []
    for row in transitions:
        scalar_rows.append(
            {
                "transition_id": row["transition_id"],
                "section": row["section"],
                "source_survey": row["source_survey"],
                "target_survey": row["target_survey"],
                "duration_days": row["duration_days"],
                "source_crack_length_m": row["source_geometry"]["crack_line_length_m"],
                "target_crack_length_m": row["target_geometry"]["crack_line_length_m"],
                "raw_total_crack_length_change_m": row["raw_total_crack_length_change_m"],
                "source_crack_area_m2": row["source_geometry"]["crack_area_m2"],
                "target_crack_area_m2": row["target_geometry"]["crack_area_m2"],
                "mean_temperature_C": row["climate"]["mean_temperature_C"],
                "low_temp_exposure_10_C_day_per_year": row["climate"]["low_temp_exposure_10_C_day_per_year"],
                "abs_temperature_change_C_per_year": row["climate"]["abs_temperature_change_C_per_year"],
                "precipitation_mm_per_year": row["climate"]["precipitation_mm_per_year"],
                "development_transition": row["development_transition"],
                "future_time_test": row["future_time_test"],
            }
        )
    csv_path = output / "transition_scalars.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(scalar_rows[0]))
        writer.writeheader();writer.writerows(scalar_rows)
    package = {
        "status": "PASS_31_ADJUDICATED_LEAKAGE_SAFE_TRANSITIONS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "adjudicated_manifest": str(manifest_path),
        "adjudicated_manifest_sha256": sha256(manifest_path),
        "climate_intervals": str(climate_path),
        "climate_intervals_sha256": sha256(climate_path),
        "multisection_gate": str(gate_path),
        "multisection_gate_sha256": sha256(gate_path),
        "section_count": 6,
        "state_count": 37,
        "transition_count": 31,
        "development_transition_count": sum(row["development_transition"] for row in transitions),
        "future_time_test_transition_count": sum(row["future_time_test"] for row in transitions),
        "transitions_sha256": sha256(transitions_path),
        "transition_scalars_sha256": sha256(csv_path),
        "model_input_boundary": "source geometry plus source-exclusive target-inclusive forcing and explicit missingness only",
        "target_only_boundary": "target geometry and all derived target changes are unavailable to model fitting or feature construction",
        "claim_boundary": "Transition package is eligible for frozen baselines; it is not forecasting evidence by itself.",
    }
    manifest_out = output / "transition_manifest.json"
    manifest_out.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": package["status"], "transitions": 31, "manifest_sha256": sha256(manifest_out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
