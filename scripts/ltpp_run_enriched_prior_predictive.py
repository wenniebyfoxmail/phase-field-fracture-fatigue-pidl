#!/usr/bin/env python3
"""Run the frozen no-outcome prior-predictive gate for LTPP enriched inputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import random
import sys
from datetime import datetime, timezone
from pathlib import Path


PRIOR_DRAWS = 500
PRIOR_CAP_M = 100.189733
EXCEEDANCE_LIMIT = 0.01
NU = 4.0

MODELS = {
    "M0": (
        "G1_source_crack_length_m",
        "G2_source_crack_area_m2",
        "G3_forecast_horizon_years",
        "C1_trailing_temperature_C",
        "C2_trailing_precipitation_mm",
    ),
    "M1": (
        "G1_source_crack_length_m",
        "G2_source_crack_area_m2",
        "G3_forecast_horizon_years",
        "C1_trailing_temperature_C",
        "C2_trailing_precipitation_mm",
        "T1_annual_esal_trend",
        "T2_aadtt_all_trucks_trend",
    ),
    "M2": (
        "G1_source_crack_length_m",
        "G2_source_crack_area_m2",
        "G3_forecast_horizon_years",
        "C1_trailing_temperature_C",
        "C2_trailing_precipitation_mm",
        "T1_annual_esal_trend",
        "T2_aadtt_all_trucks_trend",
        "S1_top_layer_thickness_mm",
        "S2_total_non_subgrade_thickness_mm",
    ),
    "M3": (
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
    ),
}

LOG1P_FEATURES = {
    "G1_source_crack_length_m",
    "G2_source_crack_area_m2",
    "C2_trailing_precipitation_mm",
    "T1_annual_esal_trend",
    "T2_aadtt_all_trucks_trend",
    "F1_D0_566_micrometres",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def quantile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("Cannot summarize empty predictions")
    position = probability * (len(sorted_values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def transform(name: str, value: float) -> float:
    if not math.isfinite(value):
        raise ValueError(f"Non-finite feature {name}")
    if name in LOG1P_FEATURES:
        if value < 0:
            raise ValueError(f"Negative value for log1p feature {name}")
        return math.log1p(value)
    return value


def standardized_eval(
    all_rows: dict[str, dict[str, str]],
    train_ids: list[str],
    eval_ids: list[str],
    features: tuple[str, ...],
) -> tuple[dict[str, list[float]], list[str]]:
    transformed_train = {
        feature: [transform(feature, float(all_rows[row_id][feature])) for row_id in train_ids]
        for feature in features
    }
    zero_variance = []
    parameters = {}
    for feature, values in transformed_train.items():
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        standard_deviation = math.sqrt(variance)
        if math.isclose(standard_deviation, 0.0, abs_tol=1e-15):
            zero_variance.append(feature)
            standard_deviation = 0.0
        parameters[feature] = (mean, standard_deviation)
    standardized = {}
    for row_id in eval_ids:
        vector = []
        for feature in features:
            mean, standard_deviation = parameters[feature]
            value = transform(feature, float(all_rows[row_id][feature]))
            vector.append(0.0 if standard_deviation == 0.0 else (value - mean) / standard_deviation)
        standardized[row_id] = vector
    return standardized, zero_variance


def student_t(rng: random.Random, nu: float) -> float:
    numerator = rng.gauss(0.0, 1.0)
    chi_square = rng.gammavariate(nu / 2.0, 2.0)
    return numerator / math.sqrt(chi_square / nu)


def inverse_growth(value: float) -> float:
    if value <= 0:
        return 0.0
    try:
        return math.expm1(value)
    except OverflowError:
        return math.inf


def finite_or_string(value: float) -> float | str:
    return value if math.isfinite(value) else "Infinity"


def run_fold(
    rows_by_id: dict[str, dict[str, str]],
    train_ids: list[str],
    eval_ids: list[str],
    features: tuple[str, ...],
    seed: int,
) -> dict:
    standardized, zero_variance = standardized_eval(
        rows_by_id, train_ids, eval_ids, features
    )
    active_indices = [
        index for index, feature in enumerate(features) if feature not in zero_variance
    ]
    rng = random.Random(seed)
    predictions = []
    for _ in range(PRIOR_DRAWS):
        alpha = rng.gauss(0.0, 2.5)
        beta = [rng.gauss(0.0, 1.0) if index in active_indices else 0.0 for index in range(len(features))]
        sigma = abs(rng.gauss(0.0, 1.0))
        sigma_section = abs(rng.gauss(0.0, 1.0))
        evaluation_sections = sorted(
            {rows_by_id[row_id]["section"] for row_id in eval_ids}
        )
        section_effects = {
            section: rng.gauss(0.0, sigma_section)
            for section in evaluation_sections
        }
        for row_id in eval_ids:
            mean = alpha + section_effects[rows_by_id[row_id]["section"]]
            mean += sum(
                coefficient * value
                for coefficient, value in zip(beta, standardized[row_id])
            )
            predictions.append(inverse_growth(mean + sigma * student_t(rng, NU)))
    predictions.sort()
    exceedance_count = sum(value > PRIOR_CAP_M for value in predictions)
    exceedance_fraction = exceedance_count / len(predictions)
    return {
        "seed": seed,
        "train_count": len(train_ids),
        "evaluation_count": len(eval_ids),
        "joint_prior_draw_count": PRIOR_DRAWS,
        "row_level_prediction_count": len(predictions),
        "zero_variance_features": zero_variance,
        "median_m": finite_or_string(quantile(predictions, 0.50)),
        "p05_m": finite_or_string(quantile(predictions, 0.05)),
        "p95_m": finite_or_string(quantile(predictions, 0.95)),
        "maximum_m": finite_or_string(predictions[-1]),
        "zero_fraction": sum(value == 0.0 for value in predictions) / len(predictions),
        "above_cap_count": exceedance_count,
        "above_cap_fraction": exceedance_fraction,
        "gate": "PASS" if exceedance_fraction <= EXCEEDANCE_LIMIT else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    script_path = Path(__file__).resolve()
    manifest_path = args.feature_manifest.resolve()
    input_root = manifest_path.parent
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "PASS_30_BY_11_ENRICHED_INPUTS_FROZEN__NO_OUTCOMES__NO_FIT":
        raise ValueError("Feature manifest is not the approved 30x11 no-fit freeze")
    protocol = manifest.get("protocol", {})
    if protocol.get("excluded_transition_ids") != ["06-2041-T01"]:
        raise ValueError("Feature manifest does not contain the exact approved exclusion")
    feature_path = input_root / manifest["feature_table"]
    split_path = input_root / manifest["split_receipt"]
    if sha256(feature_path) != manifest["feature_table_sha256"]:
        raise ValueError("Feature table hash mismatch")
    if sha256(split_path) != manifest["split_receipt_sha256"]:
        raise ValueError("Split receipt hash mismatch")
    rows = read_rows(feature_path)
    if len(rows) != 30 or len({row["transition_id"] for row in rows}) != 30:
        raise ValueError("Expected 30 unique frozen rows")
    unexpected_outcomes = sorted(
        name
        for name in rows[0]
        if name.lower().startswith(("outcome", "delta_l", "target_geometry"))
    )
    if unexpected_outcomes or manifest.get("outcome_columns_present"):
        raise ValueError(f"Outcome fields are forbidden: {unexpected_outcomes}")
    rows_by_id = {row["transition_id"]: row for row in rows}
    split = json.loads(split_path.read_text(encoding="utf-8"))
    if split.get("status") != "PASS_FIXED_OUTCOME_FREE_SPLITS":
        raise ValueError("Split receipt is not qualified")
    if split.get("transition_ids") != sorted(rows_by_id):
        raise ValueError("Split receipt and feature table row sets differ")

    results = []
    for model_index, (model, features) in enumerate(MODELS.items()):
        if len(features) != 5 + 2 * model_index:
            raise ValueError(f"Unexpected feature count for {model}")
        for fold_index, fold in enumerate(split["loso"]):
            receipt = run_fold(
                rows_by_id,
                fold["train_transition_ids"],
                fold["test_transition_ids"],
                features,
                260807 + 100 * model_index + fold_index,
            )
            results.append(
                {
                    "model": model,
                    "design": "LOSO",
                    "fold_index": fold_index,
                    "held_out_section": fold["held_out_section"],
                    **receipt,
                }
            )
        future = split["future_time"]
        receipt = run_fold(
            rows_by_id,
            future["train_transition_ids"],
            future["test_transition_ids"],
            features,
            260807 + 100 * model_index + 6,
        )
        results.append(
            {
                "model": model,
                "design": "future_time",
                "fold_index": 6,
                "held_out_section": None,
                **receipt,
            }
        )

    failed = [
        f"{row['model']}:{row['design']}:{row['fold_index']}"
        for row in results
        if row["gate"] != "PASS"
    ]
    status = (
        "PASS_PRIOR_PREDICTIVE_PREFLIGHT__NO_OUTCOME_FIT"
        if not failed
        else "PRIOR_PREDICTIVE_REVIEW_REQUIRED__NO_OUTCOME_FIT"
    )
    report = {
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "feature_manifest": str(manifest_path),
        "feature_manifest_sha256": sha256(manifest_path),
        "feature_table_sha256": sha256(feature_path),
        "split_receipt_sha256": sha256(split_path),
        "model_feature_counts": {name: len(features) for name, features in MODELS.items()},
        "prior_contract": {
            "joint_draws": PRIOR_DRAWS,
            "alpha": "Normal(0,2.5)",
            "beta": "Normal(0,1)",
            "sigma": "HalfNormal(1)",
            "sigma_section": "HalfNormal(1)",
            "likelihood": "StudentT(nu=4,mu,sigma)",
            "inverse": "max(0, exp(y)-1)",
            "prior_cap_m": PRIOR_CAP_M,
            "maximum_allowed_above_cap_fraction": EXCEEDANCE_LIMIT,
        },
        "failed_model_folds": failed,
        "results": results,
        "outcome_fields_read": [],
        "fit_performed": False,
        "code_environment_receipt": {
            "script": str(script_path),
            "script_sha256": sha256(script_path),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "argv": sys.argv,
        },
        "claim_boundary": "Prior-scale sanity only; no outcomes were read and no posterior or ablation was fitted.",
    }
    report_path = output / "prior_predictive_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (output / "derived_files.sha256").write_text(
        f"{sha256(report_path)}  {report_path.name}\n", encoding="ascii"
    )
    print(
        json.dumps(
            {
                "status": status,
                "failed_model_folds": failed,
                "report_sha256": sha256(report_path),
            }
        )
    )
    return 0 if not failed else 3


if __name__ == "__main__":
    raise SystemExit(main())
