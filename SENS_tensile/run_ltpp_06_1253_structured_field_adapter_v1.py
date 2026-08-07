#!/usr/bin/env python3
"""Qualify a minimal monotone continuous field adapter for the LTPP pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator


PRIMARY_DATES = (
    "19910610",
    "19951024",
    "19970228",
    "19980407",
    "20010913",
    "20030514",
    "20071106",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pava_equal(values: np.ndarray) -> np.ndarray:
    levels: list[float] = []
    weights: list[int] = []
    for value in values:
        levels.append(float(value))
        weights.append(1)
        while len(levels) >= 2 and levels[-2] > levels[-1]:
            weight = weights[-2] + weights[-1]
            level = (
                levels[-2] * weights[-2] + levels[-1] * weights[-1]
            ) / weight
            levels[-2:] = [level]
            weights[-2:] = [weight]
    return np.asarray(
        [level for level, weight in zip(levels, weights) for _ in range(weight)],
        dtype=np.float64,
    )


def isotonic_matrix(fields: np.ndarray) -> np.ndarray:
    shape = fields.shape
    flat = fields.reshape(shape[0], -1).astype(np.float64)
    projected = np.empty_like(flat)
    for column in range(flat.shape[1]):
        projected[:, column] = pava_equal(flat[:, column])
    return projected.reshape(shape)


def elapsed_days(dates: tuple[str, ...] | list[str]) -> np.ndarray:
    parsed = np.asarray([np.datetime64(datetime.strptime(value, "%Y%m%d").date()) for value in dates])
    return (parsed - parsed[0]).astype("timedelta64[D]").astype(float)


def rmse(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(left.astype(float) - right.astype(float)))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fields", type=Path, required=True)
    parser.add_argument("--scope-contract", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    scope = json.loads(args.scope_contract.read_text(encoding="utf-8"))
    if scope.get("protocol_id") != "ltpp_06_1253_pilot_scope_decision_v1":
        raise SystemExit("unexpected pilot scope contract")
    if scope.get("spatial_scope_ft") != [0, 50]:
        raise SystemExit("pilot spatial scope is not frozen at 0-50 ft")

    with np.load(args.fields, allow_pickle=False) as source:
        all_dates = [str(value) for value in source["survey_dates"]]
        indices = [all_dates.index(value) for value in PRIMARY_DATES]
        proxy = source["combined_damage"][indices].astype(np.float64)
        x_m = source["x_m"].copy()
        y_m = source["y_m"].copy()
    times = elapsed_days(list(PRIMARY_DATES))
    adapted = np.clip(isotonic_matrix(proxy), 0.0, 1.0)
    spline = PchipInterpolator(times, adapted.reshape(len(times), -1), axis=0, extrapolate=False)

    dense_times = np.linspace(times[0], times[-1], 25 * (len(times) - 1) + 1)
    dense = spline(dense_times)
    dense_min = float(np.min(dense))
    dense_max = float(np.max(dense))
    minimum_increment = float(np.min(np.diff(dense, axis=0)))

    per_date_rows = []
    for index, date_value in enumerate(PRIMARY_DATES):
        per_date_rows.append(
            {
                "survey_date": date_value,
                "projection_rmse": rmse(adapted[index], proxy[index]),
                "projection_mae": float(np.mean(np.abs(adapted[index] - proxy[index]))),
                "proxy_mean": float(np.mean(proxy[index])),
                "adapted_mean": float(np.mean(adapted[index])),
            }
        )
    per_date = pd.DataFrame(per_date_rows)

    holdout_rows = []
    for held_out in range(1, len(PRIMARY_DATES) - 1):
        keep = [index for index in range(len(PRIMARY_DATES)) if index != held_out]
        train = isotonic_matrix(proxy[keep])
        held_spline = PchipInterpolator(
            times[keep], train.reshape(len(keep), -1), axis=0, extrapolate=False
        )
        prediction = np.clip(held_spline(times[held_out]), 0.0, 1.0).reshape(proxy.shape[1:])
        persistence = proxy[held_out - 1]
        adapter_rmse = rmse(prediction, proxy[held_out])
        persistence_rmse = rmse(persistence, proxy[held_out])
        holdout_rows.append(
            {
                "held_out_date": PRIMARY_DATES[held_out],
                "adapter_rmse": adapter_rmse,
                "persistence_rmse": persistence_rmse,
                "adapter_wins": adapter_rmse < persistence_rmse,
                "relative_rmse_improvement": (
                    persistence_rmse - adapter_rmse
                ) / max(persistence_rmse, np.finfo(float).eps),
            }
        )
    holdout = pd.DataFrame(holdout_rows)

    global_projection_rmse = rmse(adapted, proxy)
    maximum_per_date_rmse = float(per_date["projection_rmse"].max())
    holdout_win_count = int(holdout["adapter_wins"].sum())
    median_holdout_improvement = float(holdout["relative_rmse_improvement"].median())
    checks = {
        "range_within_0_1": dense_min >= -1e-7 and dense_max <= 1.0 + 1e-7,
        "dense_irreversibility": minimum_increment >= -1e-7,
        "global_projection_rmse_le_0p15": global_projection_rmse <= 0.15,
        "max_per_date_projection_rmse_le_0p25": maximum_per_date_rmse <= 0.25,
        "holdout_wins_at_least_3_of_5": holdout_win_count >= 3,
        "median_holdout_improvement_ge_0p05": median_holdout_improvement >= 0.05,
    }
    decision = "STRUCTURED_FIELD_ADAPTER_QUALIFIED" if all(checks.values()) else "STRUCTURED_FIELD_ADAPTER_NOT_QUALIFIED"

    args.output_dir.mkdir(parents=True, exist_ok=False)
    fields_path = args.output_dir / "adapted_primary_fields.npz"
    np.savez_compressed(
        fields_path,
        x_m=x_m,
        y_m=y_m,
        survey_dates=np.asarray(PRIMARY_DATES),
        elapsed_days=times.astype(np.float32),
        proxy_damage=proxy.astype(np.float32),
        adapted_damage=adapted.astype(np.float32),
        pchip_coefficients=spline.c.astype(np.float32),
        pchip_breaks=spline.x.astype(np.float32),
    )
    per_date_path = args.output_dir / "projection_by_date.csv"
    holdout_path = args.output_dir / "leave_one_date_out.csv"
    per_date.to_csv(per_date_path, index=False)
    holdout.to_csv(holdout_path, index=False)
    payload = {
        "protocol_id": "ltpp_06_1253_minimal_structured_field_adapter_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_grade": "single_annotator_post_pilot_exploratory_field_qualification",
        "decision": decision,
        "checks": checks,
        "metrics": {
            "dense_min": dense_min,
            "dense_max": dense_max,
            "minimum_dense_temporal_increment": minimum_increment,
            "global_projection_rmse": global_projection_rmse,
            "maximum_per_date_projection_rmse": maximum_per_date_rmse,
            "holdout_win_count": holdout_win_count,
            "holdout_fold_count": int(len(holdout)),
            "median_holdout_relative_rmse_improvement": median_holdout_improvement,
        },
        "boundary": (
            "A pass authorizes only regeneration of climate-free exploratory weak systems; "
            "this artifact is not physical phase-field ground truth."
        ),
        "inputs": {
            "frozen_fields": str(args.fields.resolve()),
            "frozen_fields_sha256": sha256(args.fields),
            "scope_contract": str(args.scope_contract.resolve()),
            "scope_contract_sha256": sha256(args.scope_contract),
        },
        "outputs": {
            "adapted_fields": str(fields_path.resolve()),
            "adapted_fields_sha256": sha256(fields_path),
            "projection_by_date": str(per_date_path.resolve()),
            "projection_by_date_sha256": sha256(per_date_path),
            "leave_one_date_out": str(holdout_path.resolve()),
            "leave_one_date_out_sha256": sha256(holdout_path),
        },
    }
    result_path = args.output_dir / "qualification_result.json"
    result_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "checks": checks, "metrics": payload["metrics"]}))
    return 0 if all(checks.values()) else 3


if __name__ == "__main__":
    raise SystemExit(main())
