#!/usr/bin/env python3
"""Qualify frozen LTPP 06-1253 FWD data for a minimal Ferrite diagnostic."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


EXPECTED_DATES = {
    "11/14/1989",
    "6/10/1991",
    "7/14/1993",
    "10/24/1995",
    "2/28/1997",
    "4/7/1998",
    "5/15/2003",
}
HOLDOUT_DATE = "5/15/2003"


def read_csv(root: Path, table: str) -> list[dict[str, str]]:
    with (root / f"{table}.csv").open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_manifest(root: Path) -> tuple[bool, list[dict[str, str | bool]]]:
    results = []
    for line in (root / "raw_files.sha256").read_text(encoding="ascii").splitlines():
        expected, name = line.split("  ", 1)
        path = root / name
        actual = sha256(path) if path.is_file() else "missing"
        results.append(
            {"file": name, "expected": expected, "actual": actual, "passed": actual == expected}
        )
    return all(bool(item["passed"]) for item in results), results


def index_unique(rows: list[dict[str, str]], fields: tuple[str, ...], label: str):
    result = {}
    duplicates = 0
    for row in rows:
        key = tuple(row[field] for field in fields)
        if key in result:
            duplicates += 1
        result[key] = row
    if duplicates:
        raise RuntimeError(f"{label}: {duplicates} duplicate keys")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    manifest_passed, manifest_results = verify_manifest(args.raw_root)
    drops = read_csv(args.raw_root, "MON_DEFL_DROP_DATA")
    locations = read_csv(args.raw_root, "MON_DEFL_LOC_INFO")
    configs = read_csv(args.raw_root, "MON_DEFL_DEV_CONFIG")
    sensors = read_csv(args.raw_root, "MON_DEFL_DEV_SENSORS")
    temp_depths = read_csv(args.raw_root, "MON_DEFL_TEMP_DEPTHS")
    temp_values = read_csv(args.raw_root, "MON_DEFL_TEMP_VALUES")
    backcal_pass = read_csv(args.raw_root, "BAKCAL_PASS")
    backcal_master = read_csv(args.raw_root, "BAKCAL_MODULUS_SECTION_MASTER")

    location_key = (
        "STATE_CODE", "SHRP_ID", "TEST_DATE", "TEST_TIME", "DEFL_UNIT_ID",
        "POINT_LOC", "LANE_NO",
    )
    location_index = index_unique(locations, location_key, "MON_DEFL_LOC_INFO")
    config_index = index_unique(configs, ("CONFIGURATION_NO",), "MON_DEFL_DEV_CONFIG")
    sensor_by_config: dict[str, list[dict[str, str]]] = defaultdict(list)
    for sensor in sensors:
        sensor_by_config[sensor["CONFIGURATION_NO"]].append(sensor)
    for values in sensor_by_config.values():
        values.sort(key=lambda row: int(row["SENSOR_NO"]))

    panel_drops = [drop for drop in drops if 0.0 <= float(drop["POINT_LOC"]) <= 15.24]
    joined = []
    missing_location = 0
    missing_config = 0
    sensor_count_mismatch = 0
    incomplete_active_basin = 0
    for drop in panel_drops:
        loc = location_index.get(tuple(drop[field] for field in location_key))
        if loc is None:
            missing_location += 1
            continue
        config = config_index.get((loc["CONFIGURATION_NO"],))
        if config is None:
            missing_config += 1
            continue
        active = int(config["NO_ACTIVE_DEFLECTORS"])
        sensor_rows = sensor_by_config.get(config["CONFIGURATION_NO"], [])
        if len(sensor_rows) != active:
            sensor_count_mismatch += 1
            continue
        if any(not drop.get(f"PEAK_DEFL_{number}") for number in range(1, active + 1)):
            incomplete_active_basin += 1
        radius_m = float(config["PLATE_RADIUS"]) / 1000.0
        pressure_kpa = float(drop["DROP_LOAD"])
        force_kn = pressure_kpa * math.pi * radius_m * radius_m
        for sensor in sensor_rows:
            number = int(sensor["SENSOR_NO"])
            deflection = drop.get(f"PEAK_DEFL_{number}", "")
            reasons = []
            if drop["RECORD_STATUS"] != "E": reasons.append("drop_record_status_not_E")
            if loc["RECORD_STATUS"] != "E": reasons.append("location_record_status_not_E")
            if config["RECORD_STATUS"] != "E": reasons.append("config_record_status_not_E")
            if sensor["RECORD_STATUS"] != "E": reasons.append("sensor_record_status_not_E")
            if drop.get("NON_DECREASING_DEFL"): reasons.append("non_decreasing_basin_flag")
            if sensor.get("CENTER_OFFSET_FLAG"): reasons.append("center_offset_flag")
            if not deflection: reasons.append("missing_active_sensor_deflection")
            split = "holdout_2003" if drop["TEST_DATE"] == HOLDOUT_DATE else "calibration_candidate"
            joined.append(
                {
                    "STATE_CODE": drop["STATE_CODE"],
                    "SHRP_ID": drop["SHRP_ID"],
                    "TEST_DATE": drop["TEST_DATE"],
                    "TEST_TIME": drop["TEST_TIME"],
                    "POINT_LOC_m": drop["POINT_LOC"],
                    "LANE_NO": drop["LANE_NO"],
                    "DROP_NO": drop["DROP_NO"],
                    "DROP_HEIGHT": drop["DROP_HEIGHT"],
                    "DROP_PRESSURE_kPa": drop["DROP_LOAD"],
                    "PLATE_RADIUS_mm": config["PLATE_RADIUS"],
                    "DERIVED_TOTAL_FORCE_kN": f"{force_kn:.9g}",
                    "CONFIGURATION_NO": config["CONFIGURATION_NO"],
                    "SENSOR_NO": sensor["SENSOR_NO"],
                    "CENTER_OFFSET_mm": sensor["CENTER_OFFSET"],
                    "DEFLECTION_microns": deflection,
                    "PVMT_SURF_TEMP_degC": loc["PVMT_SURF_TEMP"],
                    "AIR_TEMP_TEST_degC": loc["AIR_TEMP_TEST"],
                    "SPLIT": split,
                    "USE_FOR_CALIBRATION": str(split == "calibration_candidate" and not reasons).lower(),
                    "USE_FOR_HOLDOUT": str(split == "holdout_2003" and not reasons).lower(),
                    "EXCLUSION_REASONS": "|".join(reasons),
                    "MAP_LEAKAGE_RULE": (
                        "forbidden_for_2003-05-14_map_prediction"
                        if drop["TEST_DATE"] == HOLDOUT_DATE else "use_only_after_observation_time"
                    ),
                }
            )

    output_fields = list(joined[0]) if joined else []
    with (args.output / "panel_basin_observations_long.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows(joined)

    panel_dates = Counter(drop["TEST_DATE"] for drop in panel_drops)
    panel_points = sorted({float(drop["POINT_LOC"]) for drop in panel_drops})
    panel_status = Counter(drop["RECORD_STATUS"] for drop in panel_drops)
    non_decreasing = Counter(drop.get("NON_DECREASING_DEFL", "") for drop in panel_drops)
    exclusion_reasons = Counter()
    for row in joined:
        for reason in filter(None, row["EXCLUSION_REASONS"].split("|")):
            exclusion_reasons[reason] += 1
    usable_by_split = Counter()
    for row in joined:
        if row["USE_FOR_CALIBRATION"] == "true": usable_by_split["calibration_sensor_values"] += 1
        if row["USE_FOR_HOLDOUT"] == "true": usable_by_split["holdout_sensor_values"] += 1

    config_gate = all(
        row["RECORD_STATUS"] == "E"
        and float(row["PLATE_RADIUS"]) > 0
        and len(sensor_by_config[row["CONFIGURATION_NO"]]) == int(row["NO_ACTIVE_DEFLECTORS"])
        for row in configs
    )
    minimum_unflagged = min(
        sum(not sensor.get("CENTER_OFFSET_FLAG") for sensor in sensor_by_config[c["CONFIGURATION_NO"]])
        for c in configs
    )
    backcal_status = Counter(row["RECORD_STATUS"] for row in backcal_master)
    backcal_dates = Counter(row["TEST_DATE"] for row in backcal_pass)
    direct_gate = all(
        (
            manifest_passed,
            set(panel_dates) == EXPECTED_DATES,
            panel_status == {"E": len(panel_drops)},
            missing_location == 0,
            missing_config == 0,
            sensor_count_mismatch == 0,
            incomplete_active_basin == 0,
            config_gate,
            minimum_unflagged >= 6,
            usable_by_split["calibration_sensor_values"] > 0,
            usable_by_split["holdout_sensor_values"] > 0,
        )
    )
    decision = (
        "QUALIFIED_FOR_LAYERED_ELASTIC_DIAGNOSTIC_ONLY"
        if direct_gate else "STOP_BEFORE_FERRITE"
    )
    report = {
        "decision": decision,
        "section": "06-1253",
        "evidence_label_if_later_simulated": "ltpp_observation_plus_ferrite_prior",
        "raw_root": str(args.raw_root),
        "raw_manifest_sha256": sha256(args.raw_root / "raw_files.sha256"),
        "raw_manifest_verified": manifest_passed,
        "raw_manifest_entries": len(manifest_results),
        "panel": {
            "station_range_m": [0.0, 15.24],
            "drop_rows": len(panel_drops),
            "dates": dict(sorted(panel_dates.items())),
            "point_locations_m": panel_points,
            "record_status": dict(panel_status),
            "non_decreasing_flag_values": dict(non_decreasing),
        },
        "joins": {
            "missing_location": missing_location,
            "missing_configuration": missing_config,
            "sensor_count_mismatch": sensor_count_mismatch,
            "incomplete_active_basin": incomplete_active_basin,
        },
        "configuration": {
            "configuration_count": len(configs),
            "plate_radii_mm": sorted({float(row["PLATE_RADIUS"]) for row in configs}),
            "active_sensor_counts": sorted({int(row["NO_ACTIVE_DEFLECTORS"]) for row in configs}),
            "minimum_unflagged_sensors_per_configuration": minimum_unflagged,
            "gate_passed": config_gate,
        },
        "split": {
            "calibration_dates": sorted(EXPECTED_DATES - {HOLDOUT_DATE}),
            "holdout_date": HOLDOUT_DATE,
            "usable_long_rows": dict(usable_by_split),
            "map_leakage_rule": "2003-05-15 FWD is forbidden for 2003-05-14 map prediction",
        },
        "exclusions": dict(exclusion_reasons),
        "temperature": {
            "location_surface_and_air_fields_available": True,
            "gradient_depth_rows": len(temp_depths),
            "gradient_value_rows": len(temp_values),
        },
        "backcalculation": {
            "section_master_rows": len(backcal_master),
            "record_status": dict(backcal_status),
            "pass_dates": dict(sorted(backcal_dates.items())),
            "use_boundary": "initialization_or_comparison_only; never truth",
            "unmatched_2012_warning": "2012 backcal passes exist without matching frozen MON_DEFL drop rows",
        },
        "authorization": {
            "allowed": [
                "design and run the smallest layered-elastic Ferrite basin diagnostic",
                "calibrate only on predeclared calibration dates and evaluate the full 2003 holdout",
                "report modulus non-identifiability and uncertainty ensemble",
            ],
            "not_allowed": [
                "phase-field teacher qualification",
                "claiming Ferrite fields are observed road mechanics",
                "constructing u, energy, history, degradation, or damage labels for PIDL",
                "starting real-road Freeze-Then-Select before adjudicated crack geometry passes",
                "using 2003-05-15 FWD to predict the 2003-05-14 map",
                "using D-status backcalculated moduli as ground truth",
            ],
        },
    }
    (args.output / "fwd_qualification_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    md = f"""# LTPP 06-1253 FWD qualification report

## Decision

`{decision}`

This passes only the direct-basin input gate for a smallest layered-elastic
Ferrite diagnostic. It does not qualify a phase-field teacher, a mechanical
field manifest, PIDL training, or real-road Freeze-Then-Select.

## Decisive evidence

- Raw manifest verified: `{manifest_passed}` across `{len(manifest_results)}` files.
- Panel drop rows: `{len(panel_drops)}` across all seven expected dates.
- Panel point locations: `{panel_points}` m.
- Drop/location/configuration joins missing: `{missing_location}/{missing_config}`.
- Active-basin incompleteness: `{incomplete_active_basin}`.
- Minimum unflagged sensors per configuration: `{minimum_unflagged}`.
- Calibration sensor observations: `{usable_by_split['calibration_sensor_values']}`.
- Held-out 2003 sensor observations: `{usable_by_split['holdout_sensor_values']}`.
- Exclusions by reason: `{dict(exclusion_reasons)}`.

`DROP_LOAD` is plate pressure in kPa. The prepared long table derives total
force as `pressure * pi * radius^2` with radius converted from mm to m and
retains both values.

## Backcalculation boundary

The current section-level backcalculation rows have status distribution
`{dict(backcal_status)}`. They may initialize or compare a diagnostic but are
not ground truth. Backcalculation passes also expose a 2012 date without matching
raw `MON_DEFL_DROP_DATA` in this frozen package; 2012 is therefore excluded from
direct-basin calibration and validation.

## Frozen split

- Calibration candidate dates: `{sorted(EXPECTED_DATES - {HOLDOUT_DATE})}`.
- Full future FWD holdout: `{HOLDOUT_DATE}`.
- The holdout is forbidden for prediction of the `2003-05-14` distress map.
- Every road-map fold must additionally enforce observation-time causality.

## Next gate

Predeclare the Ferrite layered-elastic domain, symmetry, boundary conditions,
pressure footprint, parameter bounds, objective, uncertainty ensemble, and
holdout metrics. No phase-field or PIDL field generation is authorized by this
report.
"""
    (args.output / "fwd_qualification_report.md").write_text(md, encoding="utf-8")
    files = sorted(path for path in args.output.iterdir() if path.is_file())
    (args.output / "derived_files.sha256").write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in files), encoding="ascii"
    )


if __name__ == "__main__":
    main()

