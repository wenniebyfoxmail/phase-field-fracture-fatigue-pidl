#!/usr/bin/env python3
"""Paired climate-free A/B comparison on frozen LTPP weak systems."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


MODELS = {
    "null": ("constant",),
    "A_damage": ("constant", "damage"),
    "B_damage_sq": ("constant", "damage_sq"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fit_and_score(train: pd.DataFrame, test: pd.DataFrame, terms: tuple[str, ...]) -> tuple[float, list[float]]:
    columns = [f"theta__{term}" for term in terms]
    x_train = train[columns].to_numpy(float)
    y_train = train["lhs_b"].to_numpy(float)
    x_test = test[columns].to_numpy(float)
    y_test = test["lhs_b"].to_numpy(float)
    coefficients, *_ = np.linalg.lstsq(x_train, y_train, rcond=None)
    prediction = x_test @ coefficients
    rmse = float(np.sqrt(np.mean(np.square(y_test - prediction))))
    return rmse, [float(value) for value in coefficients]


def comparison(frame: pd.DataFrame, challenger: str, reference: str) -> dict:
    left = frame[f"rmse__{challenger}"].to_numpy(float)
    right = frame[f"rmse__{reference}"].to_numpy(float)
    relative = (right - left) / np.maximum(right, np.finfo(float).eps)
    win_fraction = float(np.mean(left < right))
    median_improvement = float(np.median(relative))
    return {
        "challenger": challenger,
        "reference": reference,
        "paired_fold_count": int(len(frame)),
        "win_fraction": win_fraction,
        "median_relative_rmse_improvement": median_improvement,
        "clears_frozen_rule": win_fraction >= 0.75 and median_improvement >= 0.05,
    }


def coefficient_summary(folds: pd.DataFrame, model: str, coefficient_index: int) -> dict:
    values = np.asarray(
        [row[coefficient_index] for row in folds[f"coefficients__{model}"]], dtype=float
    )
    nonzero = values[np.abs(values) > np.finfo(float).eps]
    if len(nonzero) == 0:
        sign_consistency = 0.0
    else:
        sign_consistency = float(max(np.mean(nonzero > 0), np.mean(nonzero < 0)))
    mean = float(np.mean(values))
    return {
        "mean": mean,
        "standard_deviation": float(np.std(values)),
        "coefficient_of_variation_abs": float(np.std(values) / max(abs(mean), np.finfo(float).eps)),
        "sign_consistency": sign_consistency,
    }


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

    fold_rows = []
    for path in systems:
        frame = pd.read_csv(path)
        for axis, group_column in (
            ("spatial_holdout", "spatial_section"),
            ("trajectory_holdout", "trajectory_id"),
        ):
            for held_out in sorted(frame[group_column].unique()):
                test = frame[frame[group_column] == held_out]
                train = frame[frame[group_column] != held_out]
                if len(train) < 2 or len(test) < 1:
                    continue
                row = {
                    "system": path.name,
                    "axis": axis,
                    "group_column": group_column,
                    "held_out": str(held_out),
                    "train_rows": int(len(train)),
                    "test_rows": int(len(test)),
                }
                for model, terms in MODELS.items():
                    rmse, coefficients = fit_and_score(train, test, terms)
                    row[f"rmse__{model}"] = rmse
                    row[f"coefficients__{model}"] = coefficients
                fold_rows.append(row)

    folds = pd.DataFrame(fold_rows)
    comparisons = {}
    for axis in ("spatial_holdout", "trajectory_holdout"):
        axis_frame = folds[folds["axis"] == axis]
        comparisons[axis] = {
            "A_vs_null": comparison(axis_frame, "A_damage", "null"),
            "B_vs_null": comparison(axis_frame, "B_damage_sq", "null"),
            "B_vs_A": comparison(axis_frame, "B_damage_sq", "A_damage"),
            "mean_rmse": {
                model: float(axis_frame[f"rmse__{model}"].mean()) for model in MODELS
            },
            "median_rmse": {
                model: float(axis_frame[f"rmse__{model}"].median()) for model in MODELS
            },
        }

    b_beats_a = all(
        comparisons[axis]["B_vs_A"]["clears_frozen_rule"]
        for axis in comparisons
    )
    b_beats_null = all(
        comparisons[axis]["B_vs_null"]["clears_frozen_rule"]
        for axis in comparisons
    )
    a_beats_null = all(
        comparisons[axis]["A_vs_null"]["clears_frozen_rule"]
        for axis in comparisons
    )
    if b_beats_a and b_beats_null:
        decision = "SELECT_B_DAMAGE_SQ_EXPLORATORY"
    elif a_beats_null:
        decision = "SELECT_A_DAMAGE_EXPLORATORY"
    else:
        decision = "NO_DAMAGE_MODEL_CLEARS_NULL"

    coefficient_stability = {
        "A_damage": coefficient_summary(folds, "A_damage", 1),
        "B_damage_sq": coefficient_summary(folds, "B_damage_sq", 1),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    folds_path = args.output_dir / "paired_folds.csv"
    serializable_folds = folds.copy()
    for model in MODELS:
        serializable_folds[f"coefficients__{model}"] = serializable_folds[
            f"coefficients__{model}"
        ].map(json.dumps)
    serializable_folds.to_csv(folds_path, index=False)
    payload = {
        "protocol_id": "ltpp_06_1253_climate_free_ab_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_grade": "post_v1_single_annotator_exploratory_model_comparison",
        "models": {name: list(terms) for name, terms in MODELS.items()},
        "decision": decision,
        "comparisons": comparisons,
        "coefficient_stability": coefficient_stability,
        "boundary": (
            "This paired empirical comparison does not establish a PDE, mechanism, causality, "
            "ground truth, or physical irrelevance of climate."
        ),
        "inputs": {
            "frozen_v1_result": str(result_path.resolve()),
            "frozen_v1_result_sha256": sha256(result_path),
            "weak_system_count": len(systems),
        },
        "outputs": {
            "paired_folds": str(folds_path.resolve()),
            "paired_folds_sha256": sha256(folds_path),
        },
    }
    output_path = args.output_dir / "climate_free_ab_result.json"
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "comparisons": comparisons, "coefficient_stability": coefficient_stability}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
