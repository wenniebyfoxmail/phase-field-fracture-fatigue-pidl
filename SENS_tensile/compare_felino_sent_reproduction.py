#!/usr/bin/env python3
"""Compare PIDL scalar observables with the locked Felino SENT trajectory."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


MAPPING = {
    "crack_area_integral_d": "crack_area",
    "max_d": "max_d",
    "alpha_bar_max": "max_accumulate",
    "top_stress_yy": "top_stress_yy",
}


def _read(path: Path, cycle_column: str) -> dict[int, dict[str, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = {}
        for row in csv.DictReader(handle):
            cycle = int(round(float(row[cycle_column])))
            rows[cycle] = {key: float(value) for key, value in row.items()}
    return rows


def compare(pidl_csv: Path, reference_csv: Path) -> dict:
    pidl = _read(pidl_csv, "physical_cycle")
    reference = _read(reference_csv, "cycle_current")
    common = sorted(set(pidl) & set(reference))
    if not common:
        raise ValueError("no common physical cycles")
    metrics = {}
    for pidl_name, ref_name in MAPPING.items():
        errors = [pidl[c][pidl_name] - reference[c][ref_name] for c in common]
        abs_errors = [abs(value) for value in errors]
        ref_values = [reference[c][ref_name] for c in common]
        scale = max(ref_values) - min(ref_values)
        metrics[pidl_name] = {
            "reference_column": ref_name,
            "mae": sum(abs_errors) / len(abs_errors),
            "rmse": math.sqrt(sum(value * value for value in errors) / len(errors)),
            "max_abs_error": max(abs_errors),
            "range_normalized_mae": (
                (sum(abs_errors) / len(abs_errors)) / scale if scale > 0 else None
            ),
            "final_error": errors[-1],
        }

    def first_cycle(rows, column, threshold):
        return next((c for c in sorted(rows) if rows[c][column] >= threshold), None)

    return {
        "status": "DIAGNOSTIC_ONLY_NO_PROMOTION_GATE",
        "common_cycle_count": len(common),
        "cycle_min": common[0],
        "cycle_max": common[-1],
        "metrics": metrics,
        "event_d_ge_0_95": {
            "pidl_cycle": first_cycle(pidl, "max_d", 0.95),
            "felino_cycle": first_cycle(reference, "max_d", 0.95),
        },
        "claim_boundary": (
            "Agreement measures numerical reproduction of the locked Felino run; "
            "it does not establish physical validation or teacher status."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pidl_csv", type=Path)
    parser.add_argument("reference_csv", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = compare(args.pidl_csv, args.reference_csv)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
