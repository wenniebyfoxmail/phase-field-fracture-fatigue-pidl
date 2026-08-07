#!/usr/bin/env python3
"""Build leakage-safe interval climate features for the six-section LTPP packet."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

from ltpp_build_interval_climate_features import build_interval, read_monthly


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw_root = args.raw_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest_path = raw_root / "climate_raw_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "PASS_OFFICIAL_MONTHLY_CLIMATE_FROZEN":
        raise ValueError("Raw climate manifest is not qualified")

    intervals = []
    raw_provenance = []
    for section_row in manifest["sections"]:
        section = section_row["section"]
        section_root = raw_root / section
        temperature, temperature_files = read_monthly(section_root, "temp")
        precipitation, precipitation_files = read_monthly(section_root, "precip")
        surveys = [date.fromisoformat(value) for value in section_row["survey_dates"]]
        for local_index, (start, end) in enumerate(zip(surveys, surveys[1:]), start=1):
            row = build_interval(local_index, start, end, temperature, precipitation)
            row = {
                "transition_id": f"{section}-T{local_index:02d}",
                "section": section,
                "construction_number": section_row["construction_number"],
                **{key: value for key, value in row.items() if key != "interval_id"},
                "section_transition_index": local_index,
                "future_time_test": local_index == len(surveys) - 1,
                "development_transition": local_index < len(surveys) - 1,
            }
            if row["confirmatory_forcing_authorized"] is not True:
                raise ValueError(f"Incomplete climate interval: {row['transition_id']}")
            intervals.append(row)
        raw_provenance.append(
            {
                "section": section,
                "temperature_files": temperature_files,
                "precipitation_files": precipitation_files,
            }
        )
    if len(intervals) != 31:
        raise ValueError(f"Expected 31 transitions, found {len(intervals)}")
    if sum(row["future_time_test"] for row in intervals) != 6:
        raise ValueError("Expected one future-time test transition per section")

    csv_path = output / "interval_climate_features.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(intervals[0]))
        writer.writeheader()
        writer.writerows(intervals)
    contract = {
        "status": "PASS_31_LEAKAGE_SAFE_CLIMATE_INTERVALS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_manifest": str(manifest_path),
        "raw_manifest_sha256": sha256(manifest_path),
        "endpoint_rule": "source_exclusive_target_inclusive",
        "boundary_month_rule": "uniform_within_month_prorated_by_overlap_days",
        "section_count": 6,
        "transition_count": 31,
        "development_transition_count": 25,
        "future_time_test_transition_count": 6,
        "leave_one_section_out_folds": [
            {"fold": index, "held_out_section": section}
            for index, section in enumerate(sorted({row["section"] for row in intervals}), start=1)
        ],
        "raw_provenance": raw_provenance,
        "intervals": intervals,
        "prohibitions": [
            "do_not_fill_missing_months_with_zero",
            "do_not_use_target_or_future_geometry_in_climate_aggregation",
            "do_not_infer_pavement_moisture_from_precipitation",
            "do_not_treat_sections_as_independent_monthly_weather_stations_without_provenance",
        ],
    }
    json_path = output / "interval_climate_features.json"
    json_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    (output / "derived_files.sha256").write_text(
        f"{sha256(csv_path)}  {csv_path.name}\n{sha256(json_path)}  {json_path.name}\n",
        encoding="ascii",
    )
    print(
        json.dumps(
            {
                "status": contract["status"],
                "transitions": len(intervals),
                "future_time_tests": sum(row["future_time_test"] for row in intervals),
                "manifest_sha256": sha256(json_path),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
