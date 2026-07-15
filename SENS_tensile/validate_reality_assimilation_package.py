#!/usr/bin/env python3
"""Validate reality-assimilation package invariants without changing claims."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_ASSETS = (
    "manifest.json",
    "decision.md",
    "reality_assimilation_predictions.csv",
    "reality_assimilation_summary.csv",
    "reality_assimilation_parameter_summary.csv",
    "sensor_observability_catalog.csv",
    "transition_model_comparison.csv",
)


def validate_package(package: Path) -> list[str]:
    errors: list[str] = []
    missing = [name for name in REQUIRED_ASSETS if not (package / name).is_file()]
    if missing:
        return [f"missing required assets: {missing}"]

    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    predictions = pd.read_csv(package / "reality_assimilation_predictions.csv")
    summary = pd.read_csv(package / "reality_assimilation_summary.csv")
    parameters = pd.read_csv(package / "reality_assimilation_parameter_summary.csv")
    comparison = pd.read_csv(package / "transition_model_comparison.csv")
    decision = (package / "decision.md").read_text(encoding="utf-8")

    if manifest.get("training_launched") is not False:
        errors.append("manifest must state training_launched=false")
    families = list(manifest.get("physics_families", []))
    mixed = len(families) > 1
    if bool(manifest.get("mixed_physics_family")) != mixed:
        errors.append("mixed_physics_family is inconsistent with physics_families")
    if mixed and manifest.get("claim_quarantined") is not True:
        errors.append("mixed physics family package must set claim_quarantined=true")
    if mixed and "**Quarantine:**" not in decision:
        errors.append("mixed physics family decision must contain an explicit Quarantine line")
    if not mixed and manifest.get("claim_quarantined") is True:
        errors.append("single-family package is unexpectedly claim_quarantined")
    if manifest.get("sensor_calibration_status") == "synthetic_only" and manifest.get(
        "sensor_approved_for_inference"
    ) is not False:
        errors.append("synthetic_only sensor model cannot be approved for inference")
    comparison_models = set(comparison.get("transition_model", pd.Series(dtype=str)).astype(str))
    if "direct_fem_library" not in comparison_models:
        errors.append("transition comparison lacks direct_fem_library")
    if manifest.get("observable_growth_baseline") is True:
        growth_assets = (
            "observable_growth_predictions.csv",
            "observable_growth_summary.csv",
            "observable_growth_stage_summary.csv",
        )
        missing_growth = [name for name in growth_assets if not (package / name).is_file()]
        if missing_growth:
            errors.append(f"observable growth baseline misses assets: {missing_growth}")
        else:
            growth_predictions = pd.read_csv(package / "observable_growth_predictions.csv")
            growth_required = {
                "rul_q05",
                "rul_q50",
                "rul_q95",
                "future_tip_q05",
                "future_tip_q95",
                "rul_interval_covers",
            }
            growth_missing_columns = sorted(growth_required - set(growth_predictions.columns))
            if growth_missing_columns:
                errors.append(
                    f"observable growth predictions miss columns: {growth_missing_columns}"
                )
            else:
                if not (
                    (growth_predictions["rul_q05"] <= growth_predictions["rul_q50"])
                    & (growth_predictions["rul_q50"] <= growth_predictions["rul_q95"])
                ).all():
                    errors.append("observable growth RUL quantiles are not ordered")
                if not (
                    growth_predictions["future_tip_q05"]
                    <= growth_predictions["future_tip_q95"]
                ).all():
                    errors.append("observable growth future-tip interval is not ordered")
                if not growth_predictions["rul_interval_covers"].isin([0.0, 1.0]).all():
                    errors.append("observable growth coverage indicator must be binary")
        if "observable_growth_particles" not in comparison_models:
            errors.append("transition comparison lacks observable_growth_particles")
    if "observation_contract" in comparison and comparison["observation_contract"].nunique() != 1:
        errors.append("transition comparison mixes observation contracts")

    prediction_columns = {
        "tier",
        "rul_q05",
        "rul_q50",
        "rul_q95",
        "future_tip_q05",
        "future_tip_q95",
        "rul_interval_covers",
    }
    missing_prediction = sorted(prediction_columns - set(predictions.columns))
    if missing_prediction:
        errors.append(f"prediction table misses columns: {missing_prediction}")
    else:
        if not (
            (predictions["rul_q05"] <= predictions["rul_q50"])
            & (predictions["rul_q50"] <= predictions["rul_q95"])
        ).all():
            errors.append("RUL quantiles are not ordered")
        if not (predictions["future_tip_q05"] <= predictions["future_tip_q95"]).all():
            errors.append("future-tip interval is not ordered")
        if not predictions["rul_interval_covers"].isin([0.0, 1.0]).all():
            errors.append("rul_interval_covers must be binary")

    if "heldout_trajectory" not in summary or "ALL" not in set(summary["heldout_trajectory"]):
        errors.append("summary lacks aggregate ALL rows")
    if "rul_90_coverage" in summary and not summary["rul_90_coverage"].between(0.0, 1.0).all():
        errors.append("summary coverage lies outside [0, 1]")

    required_parameter = {
        "n_unique_truth",
        "identifiable_from_holdout",
        "mae",
        "rmse",
        "90_coverage",
        "90_width",
    }
    if not parameters.empty and not required_parameter.issubset(parameters.columns):
        errors.append(f"parameter summary misses columns: {sorted(required_parameter - set(parameters.columns))}")
    elif not parameters.empty:
        constant = parameters["n_unique_truth"] < 2
        identifiable = parameters["identifiable_from_holdout"].astype(str).str.lower().eq("true")
        if (constant & identifiable).any():
            errors.append("constant parameter is incorrectly marked identifiable")
        metric_columns = ["mae", "rmse", "90_coverage", "90_width"]
        if np.isfinite(parameters.loc[constant, metric_columns].to_numpy(float)).any():
            errors.append("constant parameter has scientific recovery metrics instead of NA")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=Path)
    args = parser.parse_args()
    errors = validate_package(args.package)
    result = {"package": str(args.package.resolve()), "valid": not errors, "errors": errors}
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
