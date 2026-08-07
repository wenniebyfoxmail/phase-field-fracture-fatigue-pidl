#!/usr/bin/env python3
"""Audit repeatability and pressure linearity before Ferrite inversion."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path


def median(values: list[float]) -> float:
    return statistics.median(values)


def robust_relative_dispersion(values: list[float]) -> float:
    center = median(values)
    if center == 0:
        return float("inf")
    mad = median([abs(value - center) for value in values])
    return 1.4826 * mad / abs(center)


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("quantile of empty sequence")
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_rows(path: Path, rows: list[dict]) -> None:
    fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        if fields:
            writer.writeheader()
            writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualified-long-table", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    with args.qualified_long_table.open(newline="", encoding="utf-8") as stream:
        source = [
            row for row in csv.DictReader(stream)
            if row["SPLIT"] == "calibration_candidate"
            and row["USE_FOR_CALIBRATION"] == "true"
        ]

    repeat_groups: dict[tuple, list[float]] = defaultdict(list)
    for row in source:
        key = (
            row["TEST_DATE"], row["POINT_LOC_m"], row["LANE_NO"],
            row["DROP_HEIGHT"], row["CENTER_OFFSET_mm"],
        )
        normalized = float(row["DEFLECTION_microns"]) / float(row["DROP_PRESSURE_kPa"])
        repeat_groups[key].append(normalized)

    repeat_rows = []
    for key, values in sorted(repeat_groups.items()):
        repeat_rows.append(
            {
                "TEST_DATE": key[0],
                "POINT_LOC_m": key[1],
                "LANE_NO": key[2],
                "DROP_HEIGHT": key[3],
                "CENTER_OFFSET_mm": key[4],
                "repeat_count": len(values),
                "median_deflection_per_pressure": f"{median(values):.12g}",
                "robust_relative_dispersion": f"{robust_relative_dispersion(values):.12g}",
            }
        )

    load_source: dict[tuple, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in source:
        key = (
            row["TEST_DATE"], row["POINT_LOC_m"], row["LANE_NO"],
            row["CENTER_OFFSET_mm"],
        )
        normalized = float(row["DEFLECTION_microns"]) / float(row["DROP_PRESSURE_kPa"])
        load_source[key][row["DROP_HEIGHT"]].append(normalized)

    load_rows = []
    for key, by_height in sorted(load_source.items()):
        height_medians = [median(values) for _, values in sorted(by_height.items())]
        load_rows.append(
            {
                "TEST_DATE": key[0],
                "POINT_LOC_m": key[1],
                "LANE_NO": key[2],
                "CENTER_OFFSET_mm": key[3],
                "load_height_count": len(height_medians),
                "median_deflection_per_pressure": f"{median(height_medians):.12g}",
                "robust_relative_dispersion_across_heights": f"{robust_relative_dispersion(height_medians):.12g}",
            }
        )

    repeat_values = [float(row["robust_relative_dispersion"]) for row in repeat_rows]
    load_values = [float(row["robust_relative_dispersion_across_heights"]) for row in load_rows]
    repeat_p50, repeat_p90 = quantile(repeat_values, 0.5), quantile(repeat_values, 0.9)
    load_p50, load_p90 = quantile(load_values, 0.5), quantile(load_values, 0.9)
    group_integrity = (
        min(int(row["repeat_count"]) for row in repeat_rows) >= 3
        and min(int(row["load_height_count"]) for row in load_rows) >= 3
    )
    repeat_pass = repeat_p50 <= 0.05 and repeat_p90 <= 0.10
    load_pass = load_p50 <= 0.05 and load_p90 <= 0.10
    decision = (
        "PASS_OBSERVED_LOAD_LINEARITY"
        if group_integrity and repeat_pass and load_pass
        else "FAIL_OBSERVED_LOAD_LINEARITY"
    )
    report = {
        "decision": decision,
        "source": str(args.qualified_long_table),
        "source_sha256": sha256(args.qualified_long_table),
        "holdout_used": False,
        "calibration_sensor_rows": len(source),
        "group_integrity_passed": group_integrity,
        "thresholds": {"median_max": 0.05, "p90_max": 0.10},
        "repeatability": {
            "group_count": len(repeat_rows), "median": repeat_p50, "p90": repeat_p90,
            "passed": repeat_pass,
        },
        "cross_load_height_linearity": {
            "group_count": len(load_rows), "median": load_p50, "p90": load_p90,
            "passed": load_pass,
        },
        "interpretation": (
            "Passing authorizes numerical solver gates only, not inversion."
            if decision.startswith("PASS")
            else "Static linear-elastic inversion remains locked; do not add nonlinear parameters after seeing this result."
        ),
    }
    write_rows(args.output / "repeatability_groups.csv", repeat_rows)
    write_rows(args.output / "cross_load_height_linearity_groups.csv", load_rows)
    (args.output / "observation_linearity_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output / "decision.md").write_text(
        "# LTPP 06-1253 observed FWD linearity gate\n\n"
        f"Decision: `{decision}`\n\n"
        f"Repeatability dispersion: median `{repeat_p50:.4%}`, p90 `{repeat_p90:.4%}`.\n\n"
        f"Cross-load-height dispersion: median `{load_p50:.4%}`, p90 `{load_p90:.4%}`.\n\n"
        f"Holdout used: `False`. {report['interpretation']}\n",
        encoding="utf-8",
    )
    files = sorted(path for path in args.output.iterdir() if path.is_file())
    (args.output / "derived_files.sha256").write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in files), encoding="ascii"
    )


if __name__ == "__main__":
    main()

