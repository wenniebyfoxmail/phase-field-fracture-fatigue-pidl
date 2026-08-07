#!/usr/bin/env python3
"""Build leakage-safe interval climate features for LTPP 06-1253."""

from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path


SURVEYS = (
    date(1991, 6, 10), date(1995, 10, 24), date(1997, 2, 28),
    date(1998, 4, 7), date(2001, 9, 13), date(2003, 5, 14),
    date(2007, 11, 6), date(2012, 4, 17), date(2015, 3, 2),
)
MONTHS = {name.upper(): number for number, name in enumerate(calendar.month_name) if name}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_monthly(root: Path, prefix: str) -> tuple[dict[tuple[int, int], float], list[dict]]:
    values = {}
    provenance = []
    for path in sorted(root.glob(f"{prefix}_*.json")):
        if path.name.endswith(".request.json"):
            continue
        year = int(path.stem.split("_")[-1])
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("Message") != "success" or int(payload.get("records", 0)) != 12:
            raise ValueError(f"incomplete monthly response: {path}")
        seen = set()
        for row in payload.get("rows") or []:
            month_name, raw_value = row["cell"]
            month = MONTHS[month_name.strip().upper()]
            if month in seen:
                raise ValueError(f"duplicate month in {path}")
            seen.add(month)
            values[(year, month)] = float(raw_value)
        if seen != set(range(1, 13)):
            raise ValueError(f"missing month in {path}")
        provenance.append({"path": str(path), "sha256": sha256(path), "year": year})
    return values, provenance


def next_month(day: date) -> date:
    return date(day.year + (day.month == 12), 1 if day.month == 12 else day.month + 1, 1)


def iter_month_overlap(start_exclusive: date, end_inclusive: date):
    interval_start = start_exclusive + timedelta(days=1)
    interval_end = end_inclusive + timedelta(days=1)
    cursor = interval_start.replace(day=1)
    while cursor < interval_end:
        following = next_month(cursor)
        overlap_start = max(cursor, interval_start)
        overlap_end = min(following, interval_end)
        overlap_days = max(0, (overlap_end - overlap_start).days)
        if overlap_days:
            yield cursor.year, cursor.month, overlap_days, (following - cursor).days
        cursor = following


def temperature_change_inside_interval(
    temperature: dict[tuple[int, int], float], start: date, end: date
) -> tuple[float, int, int]:
    total = 0.0
    observed = 0
    expected = 0
    boundary = next_month((start + timedelta(days=1)).replace(day=1))
    final = end + timedelta(days=1)
    while boundary < final:
        expected += 1
        current = (boundary.year, boundary.month)
        previous_day = boundary - timedelta(days=1)
        previous = (previous_day.year, previous_day.month)
        if current in temperature and previous in temperature:
            total += abs(temperature[current] - temperature[previous])
            observed += 1
        boundary = next_month(boundary)
    return total, observed, expected


def build_interval(index, start, end, temperature, precipitation) -> dict:
    duration_days = (end - start).days
    years = duration_days / 365.2425
    expected_days = temp_days = precip_days = 0
    weighted_temp = weighted_precip = 0.0
    low_exposure = {threshold: 0.0 for threshold in (5.0, 10.0, 15.0)}
    for year, month, overlap_days, days_in_month in iter_month_overlap(start, end):
        expected_days += overlap_days
        key = (year, month)
        if key in temperature:
            value = temperature[key]
            temp_days += overlap_days
            weighted_temp += value * overlap_days
            for threshold in low_exposure:
                low_exposure[threshold] += max(0.0, threshold - value) * overlap_days
        if key in precipitation:
            precip_days += overlap_days
            weighted_precip += precipitation[key] * overlap_days / days_in_month
    variation, variation_observed, variation_expected = temperature_change_inside_interval(
        temperature, start, end
    )
    coverage_temp = temp_days / expected_days if expected_days else 0.0
    coverage_precip = precip_days / expected_days if expected_days else 0.0
    coverage_variation = variation_observed / variation_expected if variation_expected else 1.0
    complete = min(coverage_temp, coverage_precip, coverage_variation) == 1.0
    return {
        "interval_id": index,
        "source_survey": start.isoformat(),
        "target_survey": end.isoformat(),
        "duration_days": duration_days,
        "duration_years": years,
        "endpoint_rule": "source_exclusive_target_inclusive",
        "boundary_month_rule": "uniform_within_month_prorated_by_overlap_days",
        "temperature_coverage_fraction": coverage_temp,
        "precipitation_coverage_fraction": coverage_precip,
        "temperature_change_coverage_fraction": coverage_variation,
        "mean_temperature_C": weighted_temp / temp_days if temp_days else None,
        "low_temp_exposure_5_C_day_per_year": low_exposure[5.0] / years if temp_days else None,
        "low_temp_exposure_10_C_day_per_year": low_exposure[10.0] / years if temp_days else None,
        "low_temp_exposure_15_C_day_per_year": low_exposure[15.0] / years if temp_days else None,
        "abs_temperature_change_C_per_year": variation / years if variation_observed else None,
        "precipitation_mm_per_year": weighted_precip / years if precip_days else None,
        "confirmatory_forcing_authorized": complete,
        "missing_values_are_zero": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--climate-root", type=Path, required=True)
    parser.add_argument("--raw-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    temperature, temperature_files = read_monthly(args.climate_root, "temp")
    precipitation, precipitation_files = read_monthly(args.climate_root, "precip")
    rows = [
        build_interval(index, SURVEYS[index], SURVEYS[index + 1], temperature, precipitation)
        for index in range(len(SURVEYS) - 1)
    ]
    with (args.output / "interval_climate_features.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    contract = {
        "section": "06-1253",
        "source_raw_manifest": str(args.raw_manifest),
        "source_raw_manifest_sha256": sha256(args.raw_manifest),
        "temperature_files": temperature_files,
        "precipitation_files": precipitation_files,
        "survey_dates": [value.isoformat() for value in SURVEYS],
        "endpoint_rule": "source_exclusive_target_inclusive",
        "boundary_month_rule": "uniform_within_month_prorated_by_overlap_days",
        "primary_candidates": {
            "low_temp_exposure": {"column": "low_temp_exposure_10_C_day_per_year", "unit": "C day/year"},
            "temp_variation_rate": {"column": "abs_temperature_change_C_per_year", "unit": "C/year"},
            "precipitation_rate": {"column": "precipitation_mm_per_year", "unit": "mm/year"},
        },
        "low_temperature_sensitivity_thresholds_C": [5.0, 10.0, 15.0],
        "prohibitions": [
            "do_not_fill_missing_months_with_zero",
            "do_not_use_2012_to_2015_as_confirmatory_climate_transition",
            "do_not_relabel_monthly_precipitation_as_rain_7d",
            "do_not_infer_moisture_from_precipitation",
        ],
        "intervals": rows,
    }
    (args.output / "interval_climate_features.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    files = sorted(path for path in args.output.iterdir() if path.is_file())
    (args.output / "derived_files.sha256").write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in files), encoding="ascii"
    )


if __name__ == "__main__":
    main()
