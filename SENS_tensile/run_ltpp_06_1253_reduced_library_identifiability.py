#!/usr/bin/env python3
"""Post-v1 reduced-library identifiability audit for frozen LTPP weak systems."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path

import numpy as np
import pandas as pd


BASELINE = ("constant", "damage", "damage_sq")
FAMILIES = {
    "low_temp": ("low_temp_exposure", "damage_x_low_temp_exposure"),
    "temperature_change": ("temp_variation_rate", "damage_x_temp_variation_rate"),
    "precipitation": ("precipitation_rate", "damage_x_precipitation_rate"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_condition(matrix: np.ndarray) -> tuple[int, float]:
    norms = np.linalg.norm(matrix, axis=0)
    active = norms > np.finfo(float).eps
    normalized = matrix[:, active] / norms[active]
    return int(np.linalg.matrix_rank(normalized)), float(np.linalg.cond(normalized))


def decimal_inverse(matrix: list[list[Decimal]]) -> list[list[Decimal]]:
    size = len(matrix)
    augmented = [
        row[:] + [Decimal(int(i == j)) for j in range(size)]
        for i, row in enumerate(matrix)
    ]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if augmented[pivot][column] == 0:
            raise ArithmeticError("singular correlation matrix")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                left - factor * right
                for left, right in zip(augmented[row], augmented[column])
            ]
    return [row[size:] for row in augmented]


def vif_values(matrix: np.ndarray, names: list[str]) -> dict[str, float]:
    variable_indices = [index for index, name in enumerate(names) if name != "constant"]
    columns = []
    kept_names = []
    for index in variable_indices:
        values = matrix[:, index].astype(float)
        centered = values - float(np.mean(values))
        scale = float(np.std(centered))
        if scale <= max(float(np.max(np.abs(values))) * 1e-12, np.finfo(float).eps):
            continue
        columns.append(centered / scale)
        kept_names.append(names[index])
    output = {name: float("nan") for name in names}
    if not columns:
        return output
    with localcontext() as context:
        context.prec = 60
        count = len(columns[0])
        correlation = []
        for left in columns:
            row = []
            for right in columns:
                value = math.fsum(float(a) * float(b) for a, b in zip(left, right)) / count
                row.append(Decimal(str(value)))
            correlation.append(row)
        try:
            inverse = decimal_inverse(correlation)
        except ArithmeticError:
            for name in kept_names:
                output[name] = float("inf")
            return output
        for index, name in enumerate(kept_names):
            output[name] = max(float(inverse[index][index]), 1.0)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    result_path = args.result_root / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("protocol_id") != "ltpp_06_1253_single_annotator_freeze_select_v1":
        raise SystemExit("unexpected frozen v1 result")
    systems = sorted(args.result_root.glob("weak_system__*.csv"))
    if len(systems) != 48:
        raise SystemExit(f"expected 48 frozen weak systems, found {len(systems)}")

    detail_rows = []
    vif_rows = []
    for path in systems:
        frame = pd.read_csv(path)
        for family, additions in FAMILIES.items():
            names = list(BASELINE + additions)
            matrix = frame[[f"theta__{name}" for name in names]].to_numpy(float)
            rank, condition = normalized_condition(matrix)
            detail_rows.append(
                {
                    "system": path.name,
                    "family": family,
                    "rank": rank,
                    "candidate_count": len(names),
                    "full_rank": rank == len(names),
                    "normalized_condition_number": condition,
                }
            )
            for name, value in vif_values(matrix, names).items():
                if name != "constant":
                    vif_rows.append(
                        {"system": path.name, "family": family, "term": name, "vif": value}
                    )

    detail = pd.DataFrame(detail_rows)
    vif = pd.DataFrame(vif_rows)
    term_summary = (
        vif.groupby(["family", "term"], as_index=False)
        .agg(
            median_vif=("vif", "median"),
            p90_vif=("vif", lambda values: float(np.quantile(values, 0.90))),
        )
    )
    family_results = {}
    for family in FAMILIES:
        family_detail = detail[detail["family"] == family]
        family_terms = term_summary[term_summary["family"] == family]
        metrics = {
            "full_rank_system_fraction": float(family_detail["full_rank"].mean()),
            "median_normalized_condition_number": float(
                family_detail["normalized_condition_number"].median()
            ),
            "p90_normalized_condition_number": float(
                family_detail["normalized_condition_number"].quantile(0.90)
            ),
            "maximum_term_median_vif": float(family_terms["median_vif"].max()),
            "maximum_term_p90_vif": float(family_terms["p90_vif"].max()),
        }
        checks = {
            "full_rank_fraction_ge_0p90": metrics["full_rank_system_fraction"] >= 0.90,
            "median_condition_le_1e3": metrics["median_normalized_condition_number"] <= 1e3,
            "p90_condition_le_1e4": metrics["p90_normalized_condition_number"] <= 1e4,
            "all_variable_term_median_vif_le_20": metrics["maximum_term_median_vif"] <= 20,
            "all_variable_term_p90_vif_le_50": metrics["maximum_term_p90_vif"] <= 50,
        }
        family_results[family] = {
            "decision": (
                "IDENTIFIABLE_POST_V1_DIAGNOSTIC"
                if all(checks.values())
                else "NOT_IDENTIFIABLE_POST_V1_DIAGNOSTIC"
            ),
            "checks": checks,
            "metrics": metrics,
        }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    detail_path = args.output_dir / "system_family_conditioning.csv"
    vif_path = args.output_dir / "family_term_vif.csv"
    detail.to_csv(detail_path, index=False)
    term_summary.to_csv(vif_path, index=False)
    payload = {
        "protocol_id": "ltpp_06_1253_post_v1_reduced_library_identifiability_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_grade": "post_v1_exploratory_diagnostic",
        "family_results": family_results,
        "boundary": (
            "Numerical identifiability does not imply selection, prediction, mechanism, or causality; "
            "this result cannot overwrite the frozen v1 result."
        ),
        "inputs": {
            "frozen_v1_result": str(result_path.resolve()),
            "frozen_v1_result_sha256": sha256(result_path),
            "weak_system_count": len(systems),
        },
        "outputs": {
            "system_family_conditioning": str(detail_path.resolve()),
            "system_family_conditioning_sha256": sha256(detail_path),
            "family_term_vif": str(vif_path.resolve()),
            "family_term_vif_sha256": sha256(vif_path),
        },
    }
    output_path = args.output_dir / "reduced_library_identifiability_result.json"
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(family_results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
