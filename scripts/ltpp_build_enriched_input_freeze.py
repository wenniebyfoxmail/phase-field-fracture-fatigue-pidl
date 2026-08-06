#!/usr/bin/env python3
"""Build the preregistered LTPP enriched input table without outcomes."""

from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
import math
import platform
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from statistics import median

from ltpp_build_interval_climate_features import read_monthly


FEATURE_COLUMNS = (
    "G1_source_crack_length_m",
    "G2_source_crack_area_m2",
    "G3_forecast_horizon_years",
    "C1_trailing_temperature_C",
    "C2_trailing_precipitation_mm",
    "T1_annual_esal_trend",
    "T2_aadtt_all_trucks_trend",
    "S1_top_layer_thickness_mm",
    "S2_total_non_subgrade_thickness_mm",
    "F1_D0_566_micrometres",
    "F2_fwd_age_years",
)

V3_AMENDMENT_SHA256 = (
    "f2490cd99b07912567ab52aabcf2ba9472b9514de3dd0fe1c1b1bba4e85ec70d"
)
V3_EXCLUDED_TRANSITION_IDS = ("06-2041-T01",)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_date(value: str) -> date:
    value = value.strip()
    for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            pass
    raise ValueError(f"Unsupported date: {value!r}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def next_month(value: datetime) -> datetime:
    if value.month == 12:
        return value.replace(year=value.year + 1, month=1, day=1)
    return value.replace(month=value.month + 1, day=1)


def trailing_climate(
    source: date,
    temperature: dict[tuple[int, int], float],
    precipitation: dict[tuple[int, int], float],
) -> dict:
    end = datetime.combine(source, time.min)
    start = end - timedelta(days=365.25)
    cursor = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    weighted_temperature = 0.0
    temperature_days = 0.0
    precipitation_mm = 0.0
    expected_days = 0.0
    missing = []
    while cursor < end:
        following = next_month(cursor)
        overlap_start = max(cursor, start)
        overlap_end = min(following, end)
        overlap_days = (overlap_end - overlap_start).total_seconds() / 86400.0
        if overlap_days > 0:
            key = (cursor.year, cursor.month)
            expected_days += overlap_days
            if key not in temperature or key not in precipitation:
                missing.append(f"{cursor.year:04d}-{cursor.month:02d}")
            else:
                weighted_temperature += temperature[key] * overlap_days
                temperature_days += overlap_days
                days_in_month = calendar.monthrange(cursor.year, cursor.month)[1]
                precipitation_mm += precipitation[key] * overlap_days / days_in_month
        cursor = following
    if missing or not math.isclose(expected_days, 365.25, abs_tol=1e-9):
        raise ValueError(
            f"Trailing climate incomplete at {source}: missing={missing}, days={expected_days}"
        )
    return {
        "temperature_C": weighted_temperature / temperature_days,
        "precipitation_mm": precipitation_mm,
        "window_start": start.isoformat(),
        "window_end_exclusive": end.isoformat(),
        "coverage_days": temperature_days,
    }


def exact_one(rows: list[dict], description: str) -> dict:
    if len(rows) != 1:
        raise ValueError(f"Expected one {description}, found {len(rows)}")
    return rows[0]


def active_traffic(rows: list[dict[str, str]], construction: int, year: int) -> dict:
    match = exact_one(
        [
            row
            for row in rows
            if int(row["CONSTRUCTION_NO"]) == construction and int(row["YEAR"]) == year
        ],
        f"TRF_TREND row for construction={construction}, year={year}",
    )
    esal = float(match["ANNUAL_ESAL_TREND"])
    aadtt = float(match["AADTT_ALL_TRUCKS_TREND"])
    if esal < 0 or aadtt < 0:
        raise ValueError("Traffic features must be non-negative")
    return {
        "esal": esal,
        "aadtt": aadtt,
        "esal_source": match["ESAL_SOURCE"],
        "aadtt_source": match["AADTT_SOURCE"],
    }


def active_structure(
    rows: list[dict[str, str]], construction: int, millimetres_per_stored_unit: float
) -> dict:
    valid = [
        row
        for row in rows
        if int(row["CONSTRUCTION_NO"]) == construction
        and row["RECORD_STATUS"].strip().upper() != "D"
        and row["REPR_THICKNESS"].strip()
        and float(row["REPR_THICKNESS"]) > 0
    ]
    if not valid:
        raise ValueError(f"No valid structure rows for construction={construction}")
    layer_numbers = [int(row["LAYER_NO"]) for row in valid]
    top_number = max(layer_numbers)
    top = exact_one(
        [row for row in valid if int(row["LAYER_NO"]) == top_number],
        f"top layer for construction={construction}",
    )
    return {
        "top_mm": float(top["REPR_THICKNESS"]) * millimetres_per_stored_unit,
        "total_non_subgrade_mm": sum(
            float(row["REPR_THICKNESS"]) * millimetres_per_stored_unit
            for row in valid
            if int(row["LAYER_NO"]) > 1
        ),
        "top_layer_no": top_number,
        "valid_layer_count": len(valid),
    }


def fwd_feature(
    source: date,
    construction: int,
    masters: list[dict[str, str]],
    locations: list[dict[str, str]],
    drops: list[dict[str, str]],
    sensors: list[dict[str, str]],
) -> dict:
    eligible_master = [
        row
        for row in masters
        if int(row["CONSTRUCTION_NO"]) == construction
        and row["RECORD_STATUS"].strip().upper() != "D"
        and parse_date(row["TEST_DATE"]) <= source
    ]
    if not eligible_master:
        raise ValueError(f"No source-prior FWD master for construction={construction}")
    latest_date = max(parse_date(row["TEST_DATE"]) for row in eligible_master)
    latest_units = {
        row["DEFL_UNIT_ID"]
        for row in eligible_master
        if parse_date(row["TEST_DATE"]) == latest_date
    }

    def location_key(row: dict[str, str]) -> tuple[str, ...]:
        return (
            parse_date(row["TEST_DATE"]).isoformat(),
            row["TEST_TIME"],
            row["DEFL_UNIT_ID"],
            row["POINT_LOC"],
            row["LANE_NO"],
            row["CONSTRUCTION_NO"],
        )

    configs_by_location: dict[tuple[str, ...], set[str]] = defaultdict(set)
    for row in locations:
        if (
            int(row["CONSTRUCTION_NO"]) == construction
            and parse_date(row["TEST_DATE"]) == latest_date
            and row["DEFL_UNIT_ID"] in latest_units
            and row["RECORD_STATUS"].strip().upper() != "D"
            and 0.0 <= float(row["POINT_LOC"]) <= 15.24
        ):
            configs_by_location[location_key(row)].add(row["CONFIGURATION_NO"])
    sensor_one = {
        row["CONFIGURATION_NO"]: row
        for row in sensors
        if row["SENSOR_NO"] == "1" and row["RECORD_STATUS"].strip().upper() != "D"
    }
    values = []
    configurations = set()
    rejected_non_decreasing = 0
    for row in drops:
        if (
            int(row["CONSTRUCTION_NO"]) != construction
            or parse_date(row["TEST_DATE"]) != latest_date
            or row["DEFL_UNIT_ID"] not in latest_units
            or row["RECORD_STATUS"].strip().upper() == "D"
            or not 0.0 <= float(row["POINT_LOC"]) <= 15.24
        ):
            continue
        key = location_key(row)
        configs = configs_by_location.get(key, set())
        if len(configs) != 1:
            continue
        configuration = next(iter(configs))
        sensor = sensor_one.get(configuration)
        if sensor is None or not math.isclose(float(sensor["CENTER_OFFSET"]), 0.0):
            continue
        if row["NON_DECREASING_DEFL"].strip():
            rejected_non_decreasing += 1
            continue
        if not row["DROP_LOAD"].strip() or not row["PEAK_DEFL_1"].strip():
            continue
        load = float(row["DROP_LOAD"])
        deflection = float(row["PEAK_DEFL_1"])
        if load <= 0 or deflection <= 0:
            continue
        values.append(deflection * 566.0 / load)
        configurations.add(configuration)
    if not values:
        raise ValueError(
            f"Latest FWD date {latest_date} has no valid mapped drops for construction={construction}"
        )
    return {
        "d0_566_micrometres": median(values),
        "age_years": (source - latest_date).days / 365.25,
        "test_date": latest_date.isoformat(),
        "valid_drop_count": len(values),
        "configuration_numbers": sorted(configurations),
        "rejected_non_decreasing_count": rejected_non_decreasing,
    }


def structure_conversion(dictionary_path: Path) -> float:
    dictionary = json.loads(dictionary_path.read_text(encoding="utf-8"))
    field = exact_one(
        [
            row
            for row in dictionary["tableDictionary"]
            if row["FIELD_NAME"] == "REPR_THICKNESS"
        ],
        "REPR_THICKNESS dictionary field",
    )
    if field.get("UNITS") != "in" or field.get("CONVERTED_UNIT") != "mm":
        raise ValueError(f"Unexpected thickness units: {field}")
    factor = float(field["CONVERSION_FACTOR"])
    if not math.isclose(factor, 25.4):
        raise ValueError(f"Unexpected thickness conversion factor: {factor}")
    return factor


def select_transition_set(
    transitions: list[dict],
    exclude_transition_ids: list[str],
    amendment_path: Path | None,
) -> tuple[list[dict], dict]:
    """Apply the only externally approved v3 transition-set amendment."""
    if not exclude_transition_ids:
        if amendment_path is not None:
            raise ValueError("--amendment is only valid with the approved exclusion")
        return transitions, {
            "protocol": "v2_31_row",
            "excluded_transition_ids": [],
            "amendment": None,
            "amendment_sha256": None,
        }
    if tuple(exclude_transition_ids) != V3_EXCLUDED_TRANSITION_IDS:
        raise ValueError(
            "Only the exact approved exclusion 06-2041-T01 is permitted"
        )
    if amendment_path is None:
        raise ValueError("The approved v3 amendment is required for row exclusion")
    amendment_path = amendment_path.resolve()
    amendment_hash = sha256(amendment_path)
    if amendment_hash != V3_AMENDMENT_SHA256:
        raise ValueError(
            f"V3 amendment hash mismatch: {amendment_hash} != {V3_AMENDMENT_SHA256}"
        )
    transition_ids = [row["transition_id"] for row in transitions]
    if len(transition_ids) != len(set(transition_ids)):
        raise ValueError("Original transition IDs are not unique")
    if set(exclude_transition_ids) - set(transition_ids):
        raise ValueError("Approved excluded transition is absent from source set")
    selected = [
        row for row in transitions if row["transition_id"] not in exclude_transition_ids
    ]
    if len(selected) != 30:
        raise ValueError(f"Approved v3 set must contain 30 rows, found {len(selected)}")
    return selected, {
        "protocol": "v3_30_row_complete_input_sensitivity",
        "excluded_transition_ids": list(exclude_transition_ids),
        "amendment": str(amendment_path),
        "amendment_sha256": amendment_hash,
    }


def build_split_receipt(transitions: list[dict], protocol: dict) -> dict:
    """Create deterministic outcome-free LOSO and future-time split assignments."""
    ordered = sorted(transitions, key=lambda row: row["transition_id"])
    ids = [row["transition_id"] for row in ordered]
    sections = sorted({row["section"] for row in ordered})
    loso = []
    for section in sections:
        test_ids = [row["transition_id"] for row in ordered if row["section"] == section]
        train_ids = [row["transition_id"] for row in ordered if row["section"] != section]
        loso.append(
            {
                "held_out_section": section,
                "train_transition_ids": train_ids,
                "test_transition_ids": test_ids,
                "train_count": len(train_ids),
                "test_count": len(test_ids),
            }
        )
    development_ids = [
        row["transition_id"] for row in ordered if bool(row["development_transition"])
    ]
    future_ids = [
        row["transition_id"] for row in ordered if bool(row["future_time_test"])
    ]
    if set(development_ids) & set(future_ids) or set(development_ids + future_ids) != set(ids):
        raise ValueError("Development/future split is not a disjoint partition")
    if protocol["protocol"] == "v3_30_row_complete_input_sensitivity":
        expected_loso = {
            "06-1253": 7,
            "06-2041": 6,
            "06-2647": 4,
            "06-8149": 5,
            "06-8150": 4,
            "06-8201": 4,
        }
        actual_loso = {row["held_out_section"]: row["test_count"] for row in loso}
        if actual_loso != expected_loso:
            raise ValueError(f"Unexpected v3 LOSO counts: {actual_loso}")
        if len(development_ids) != 24 or len(future_ids) != 6:
            raise ValueError(
                f"Expected v3 future split 24+6, found {len(development_ids)}+{len(future_ids)}"
            )
    return {
        "status": "PASS_FIXED_OUTCOME_FREE_SPLITS",
        "protocol": protocol["protocol"],
        "transition_count": len(ids),
        "transition_ids": ids,
        "excluded_transition_ids": protocol["excluded_transition_ids"],
        "loso": loso,
        "future_time": {
            "train_transition_ids": development_ids,
            "test_transition_ids": future_ids,
            "train_count": len(development_ids),
            "test_count": len(future_ids),
        },
        "outcome_fields_used": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transitions", type=Path, required=True)
    parser.add_argument("--transition-manifest", type=Path, required=True)
    parser.add_argument("--baseline-manifest", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--climate-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--exclude-transition-id", action="append", default=[])
    parser.add_argument("--amendment", type=Path)
    args = parser.parse_args()
    builder_path = Path(__file__).resolve()
    transitions_path = args.transitions.resolve()
    transition_manifest_path = args.transition_manifest.resolve()
    baseline_path = args.baseline_manifest.resolve()
    raw_root = args.raw_root.resolve()
    climate_root = args.climate_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)

    transition_manifest = json.loads(transition_manifest_path.read_text(encoding="utf-8"))
    if transition_manifest.get("status") != "PASS_31_ADJUDICATED_LEAKAGE_SAFE_TRANSITIONS":
        raise ValueError("Transition manifest is not qualified")
    if sha256(transitions_path) != transition_manifest["transitions_sha256"]:
        raise ValueError("Transition JSON does not match the frozen manifest")
    source_transitions = json.loads(transitions_path.read_text(encoding="utf-8"))
    if len(source_transitions) != 31:
        raise ValueError(f"Expected 31 source transitions, found {len(source_transitions)}")
    transitions, protocol = select_transition_set(
        source_transitions, args.exclude_transition_id, args.amendment
    )
    required_transition_count = len(transitions)
    raw_manifest_path = raw_root / "raw_data_manifest.json"
    raw_manifest = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
    if raw_manifest.get("status") != "PASS_OFFICIAL_ENRICHED_TABLES_FROZEN":
        raise ValueError("Enriched raw manifest is not qualified")
    climate_manifest_path = climate_root / "climate_raw_manifest.json"
    climate_manifest = json.loads(climate_manifest_path.read_text(encoding="utf-8"))
    if climate_manifest.get("status") != "PASS_OFFICIAL_MONTHLY_CLIMATE_FROZEN":
        raise ValueError("Climate raw manifest is not qualified")
    if int(climate_manifest.get("lookback_years", 0)) < 1:
        raise ValueError("Climate package does not contain the required source lookback")

    climate_by_section = {}
    for section_row in climate_manifest["sections"]:
        section_root = climate_root / section_row["section"]
        temperature, temperature_files = read_monthly(section_root, "temp")
        precipitation, precipitation_files = read_monthly(section_root, "precip")
        climate_by_section[section_row["section"]] = {
            "temperature": temperature,
            "precipitation": precipitation,
            "files": temperature_files + precipitation_files,
        }

    source_cache = {}
    for section in sorted({row["section"] for row in transitions}):
        section_root = raw_root / section
        source_cache[section] = {
            "traffic": read_csv(section_root / "TRF_TREND.csv"),
            "structure": read_csv(section_root / "SECTION_LAYER_STRUCTURE.csv"),
            "masters": read_csv(section_root / "MON_DEFL_MASTER.csv"),
            "locations": read_csv(section_root / "MON_DEFL_LOC_INFO.csv"),
            "drops": read_csv(section_root / "MON_DEFL_DROP_DATA.csv"),
            "sensors": read_csv(section_root / "MON_DEFL_DEV_SENSORS.csv"),
            "thickness_factor": structure_conversion(
                section_root / "SECTION_LAYER_STRUCTURE.dictionary.json"
            ),
        }

    rows = []
    coverage_rows = []
    errors = []
    for transition in transitions:
        transition_id = transition["transition_id"]
        section = transition["section"]
        source = date.fromisoformat(transition["source_survey"])
        target = date.fromisoformat(transition["target_survey"])
        construction = int(transition["construction_number"])
        try:
            climate = trailing_climate(
                source,
                climate_by_section[section]["temperature"],
                climate_by_section[section]["precipitation"],
            )
            traffic_year = source.year - 1
            traffic = active_traffic(
                source_cache[section]["traffic"], construction, traffic_year
            )
            structure = active_structure(
                source_cache[section]["structure"],
                construction,
                source_cache[section]["thickness_factor"],
            )
            fwd = fwd_feature(
                source,
                construction,
                source_cache[section]["masters"],
                source_cache[section]["locations"],
                source_cache[section]["drops"],
                source_cache[section]["sensors"],
            )
            row = {
                "transition_id": transition_id,
                "section": section,
                "construction_number": construction,
                "source_cutoff_date": source.isoformat(),
                "target_survey_date": target.isoformat(),
                "development_transition": transition["development_transition"],
                "future_time_test": transition["future_time_test"],
                "G1_source_crack_length_m": transition["source_geometry"][
                    "crack_line_length_m"
                ],
                "G2_source_crack_area_m2": transition["source_geometry"]["crack_area_m2"],
                "G3_forecast_horizon_years": (target - source).days / 365.25,
                "C1_trailing_temperature_C": climate["temperature_C"],
                "C2_trailing_precipitation_mm": climate["precipitation_mm"],
                "T1_annual_esal_trend": traffic["esal"],
                "T2_aadtt_all_trucks_trend": traffic["aadtt"],
                "S1_top_layer_thickness_mm": structure["top_mm"],
                "S2_total_non_subgrade_thickness_mm": structure[
                    "total_non_subgrade_mm"
                ],
                "F1_D0_566_micrometres": fwd["d0_566_micrometres"],
                "F2_fwd_age_years": fwd["age_years"],
                "climate_window_start": climate["window_start"],
                "climate_window_end_exclusive": climate["window_end_exclusive"],
                "climate_coverage_days": climate["coverage_days"],
                "traffic_year": traffic_year,
                "traffic_data_through": f"{traffic_year}-12-31",
                "ESAL_SOURCE": traffic["esal_source"],
                "AADTT_SOURCE": traffic["aadtt_source"],
                "structure_top_layer_no": structure["top_layer_no"],
                "structure_valid_layer_count": structure["valid_layer_count"],
                "fwd_test_date": fwd["test_date"],
                "fwd_valid_drop_count": fwd["valid_drop_count"],
                "fwd_configuration_numbers": ";".join(fwd["configuration_numbers"]),
                "fwd_rejected_non_decreasing_count": fwd[
                    "rejected_non_decreasing_count"
                ],
            }
            for feature in FEATURE_COLUMNS:
                value = float(row[feature])
                if not math.isfinite(value):
                    raise ValueError(f"Non-finite feature {feature}")
            if any(float(row[name]) < 0 for name in FEATURE_COLUMNS if name != "C1_trailing_temperature_C"):
                raise ValueError("Unexpected negative non-temperature feature")
            if date.fromisoformat(row["traffic_data_through"]) >= source:
                raise ValueError("Traffic timestamp is not strictly before source cutoff")
            if date.fromisoformat(row["fwd_test_date"]) > source:
                raise ValueError("FWD timestamp is after source cutoff")
            rows.append(row)
            coverage_rows.append(
                {
                    "transition_id": transition_id,
                    "status": "PASS",
                    "feature_count": len(FEATURE_COLUMNS),
                    "source_cutoff_date": source.isoformat(),
                    "latest_dated_confirmatory_input": max(
                        date.fromisoformat(row["traffic_data_through"]),
                        date.fromisoformat(row["fwd_test_date"]),
                    ).isoformat(),
                }
            )
        except Exception as exc:
            errors.append({"transition_id": transition_id, "error": str(exc)})
            coverage_rows.append(
                {"transition_id": transition_id, "status": "FAIL", "error": str(exc)}
            )

    coverage_path = output / "coverage_report.json"
    coverage = {
        "status": (
            f"PASS_{required_transition_count}_BY_11_SOURCE_CUTOFF_COVERAGE"
            if not errors
            else "BLOCKED_INPUT_COVERAGE"
        ),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": protocol,
        "required_transition_count": required_transition_count,
        "required_feature_count": 11,
        "complete_transition_count": len(rows),
        "errors": errors,
        "rows": coverage_rows,
    }
    coverage_path.write_text(json.dumps(coverage, indent=2) + "\n", encoding="utf-8")
    if errors:
        print(json.dumps({"status": coverage["status"], "errors": errors}, indent=2))
        return 2
    if len(rows) != required_transition_count or len({row["transition_id"] for row in rows}) != required_transition_count:
        raise ValueError(
            f"Feature table does not have {required_transition_count} unique transitions"
        )
    rows.sort(key=lambda row: row["transition_id"])
    feature_path = output / f"enriched_input_features_{required_transition_count}x11.csv"
    with feature_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    split_receipt = build_split_receipt(transitions, protocol)
    split_receipt.update(
        {
            "source_transition_manifest": str(transition_manifest_path),
            "source_transition_manifest_sha256": sha256(transition_manifest_path),
            "source_baseline_manifest": str(baseline_path),
            "source_baseline_manifest_sha256": sha256(baseline_path),
        }
    )
    split_path = output / "split_receipt.json"
    split_path.write_text(json.dumps(split_receipt, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "status": f"PASS_{required_transition_count}_BY_11_ENRICHED_INPUTS_FROZEN__NO_OUTCOMES__NO_FIT",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": protocol,
        "feature_columns": list(FEATURE_COLUMNS),
        "transition_count": len(rows),
        "feature_count": len(FEATURE_COLUMNS),
        "feature_table": feature_path.name,
        "feature_table_sha256": sha256(feature_path),
        "coverage_report": coverage_path.name,
        "coverage_report_sha256": sha256(coverage_path),
        "split_receipt": split_path.name,
        "split_receipt_sha256": sha256(split_path),
        "transition_manifest": str(transition_manifest_path),
        "transition_manifest_sha256": sha256(transition_manifest_path),
        "transitions_sha256": sha256(transitions_path),
        "raw_data_manifest": str(raw_manifest_path),
        "raw_data_manifest_sha256": sha256(raw_manifest_path),
        "climate_raw_manifest": str(climate_manifest_path),
        "climate_raw_manifest_sha256": sha256(climate_manifest_path),
        "source_baseline_manifest_sha256": sha256(baseline_path),
        "code_environment_receipt": {
            "builder": str(builder_path),
            "builder_sha256": sha256(builder_path),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "argv": sys.argv,
        },
        "trailing_climate_window": "[source_timestamp-365.25 days, source_timestamp)",
        "thickness_conversion": "stored inches multiplied by official dictionary factor 25.4 to mm",
        "outcome_columns_present": [],
        "claim_boundary": "Source-available input freeze only; outcome fitting and ablation scoring remain prohibited.",
    }
    manifest_path = output / "feature_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    hashed = sorted(path for path in output.iterdir() if path.is_file())
    (output / "derived_files.sha256").write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in hashed), encoding="ascii"
    )
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "rows": len(rows),
                "features": len(FEATURE_COLUMNS),
                "feature_table_sha256": manifest["feature_table_sha256"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
