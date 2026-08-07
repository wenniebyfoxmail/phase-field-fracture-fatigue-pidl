#!/usr/bin/env python3
"""Evaluate the frozen hierarchical probabilistic LTPP crack-growth challenger."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ltpp_run_frozen_baselines import (
    crack_lines,
    evaluation_splits,
    extend_line,
    geometry_metrics,
    load_json,
)


FIXED_RIDGE = 1.0
RANDOM_INTERCEPT_PSEUDO_COUNT = 3.0
Z90 = 1.6448536269514722
FEATURES = (
    "log1p_source_crack_length_m",
    "mean_temperature_C",
    "low_temp_exposure_10_C_day_per_year",
    "abs_temperature_change_C_per_year",
    "precipitation_mm_per_year",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def feature_vector(row: dict) -> list[float]:
    return [
        math.log1p(row["source_geometry"]["crack_line_length_m"]),
        row["climate"]["mean_temperature_C"],
        row["climate"]["low_temp_exposure_10_C_day_per_year"],
        row["climate"]["abs_temperature_change_C_per_year"],
        row["climate"]["precipitation_mm_per_year"],
    ]


def fit_model(rows: list[dict]) -> dict:
    raw_x = np.asarray([feature_vector(row) for row in rows], dtype=float)
    means = raw_x.mean(axis=0)
    scales = raw_x.std(axis=0, ddof=0)
    scales[scales < 1e-12] = 1.0
    standardized = (raw_x - means) / scales
    x = np.column_stack([np.ones(len(rows)), standardized])
    y = np.asarray(
        [row["raw_total_crack_length_change_m"] / row["duration_years"] for row in rows],
        dtype=float,
    )
    sections = [row["section"] for row in rows]
    random = {section: 0.0 for section in sorted(set(sections))}
    penalty = np.diag([0.0] + [FIXED_RIDGE] * standardized.shape[1])
    beta = np.zeros(x.shape[1])
    for _ in range(100):
        offsets = np.asarray([random[section] for section in sections])
        new_beta = np.linalg.solve(x.T @ x + penalty, x.T @ (y - offsets))
        residual = y - x @ new_beta
        new_random = {
            section: float(
                residual[np.asarray([value == section for value in sections])].sum()
                / (sum(value == section for value in sections) + RANDOM_INTERCEPT_PSEUDO_COUNT)
            )
            for section in random
        }
        weighted_mean = sum(
            new_random[section] * sum(value == section for value in sections)
            for section in new_random
        ) / len(sections)
        new_random = {section: value - weighted_mean for section, value in new_random.items()}
        change = max(
            float(np.max(np.abs(new_beta - beta))),
            max(abs(new_random[key] - random[key]) for key in random),
        )
        beta, random = new_beta, new_random
        if change < 1e-10:
            break
    fitted = x @ beta + np.asarray([random[section] for section in sections])
    residual = y - fitted
    degrees = max(1, len(y) - x.shape[1])
    sigma_rate = float(math.sqrt(float(np.dot(residual, residual)) / degrees))
    inverse = np.linalg.inv(x.T @ x + penalty)
    return {
        "means": means,
        "scales": scales,
        "beta": beta,
        "random": random,
        "sigma_rate": sigma_rate,
        "inverse": inverse,
        "training_rows": len(rows),
    }


def predict(model: dict, row: dict) -> tuple[float, float]:
    raw = np.asarray(feature_vector(row), dtype=float)
    vector = np.concatenate([[1.0], (raw - model["means"]) / model["scales"]])
    rate = float(vector @ model["beta"] + model["random"].get(row["section"], 0.0))
    leverage = max(0.0, float(vector @ model["inverse"] @ vector))
    source = row["source_geometry"]["crack_line_length_m"]
    mean = max(0.0, source + rate * row["duration_years"])
    sd = model["sigma_rate"] * row["duration_years"] * math.sqrt(1.0 + leverage)
    return mean, max(sd, 1e-9)


def gaussian_crps(mean: float, sd: float, observation: float) -> float:
    if sd <= 1e-12:
        return abs(mean - observation)
    z = (observation - mean) / sd
    phi = math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)
    cdf = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return sd * (z * (2 * cdf - 1) + 2 * phi - 1 / math.sqrt(math.pi))


def read_baselines(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        result = []
        for row in csv.DictReader(stream):
            for key in (
                "crack_length_absolute_error_m",
                "new_geometry_symmetric_difference_m2",
                "buffered_f1",
                "buffered_iou",
            ):
                row[key] = float(row[key])
            result.append(row)
        return result


def percent_improvement(challenger: float, baseline: float) -> float:
    if baseline <= 1e-12:
        return 0.0 if challenger <= baseline + 1e-12 else -math.inf
    return 100.0 * (baseline - challenger) / baseline


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transitions-root", type=Path, required=True)
    parser.add_argument("--baselines-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    transition_root = args.transitions_root.resolve()
    baseline_root = args.baselines_root.resolve()
    transition_manifest_path = transition_root / "transition_manifest.json"
    baseline_manifest_path = baseline_root / "baseline_manifest.json"
    if not transition_manifest_path.exists() or not baseline_manifest_path.exists():
        print(json.dumps({"status": "BLOCKED_NO_FROZEN_TRANSITIONS_OR_BASELINES"}))
        return 42
    transition_manifest = load_json(transition_manifest_path)
    baseline_manifest = load_json(baseline_manifest_path)
    if transition_manifest.get("status") != "PASS_31_ADJUDICATED_LEAKAGE_SAFE_TRANSITIONS":
        raise ValueError("Transitions not qualified")
    if baseline_manifest.get("status") != "PASS_FROZEN_BASELINES_COMPLETE":
        raise ValueError("Baselines not qualified")
    rows = load_json(transition_root / "transitions.json")
    payload_cache = {}
    def payload(path: str) -> dict:
        if path not in payload_cache:
            payload_cache[path] = load_json(Path(path))
        return payload_cache[path]

    predictions = []
    model_receipts = []
    for split in evaluation_splits(rows):
        model = fit_model(split["train"])
        model_receipts.append(
            {
                "axis": split["axis"],
                "fold": split["fold"],
                "held_out_section": split["held_out_section"],
                "training_transition_ids": [row["transition_id"] for row in split["train"]],
                "test_transition_ids": [row["transition_id"] for row in split["test"]],
                "feature_means": dict(zip(FEATURES, model["means"].tolist())),
                "feature_scales": dict(zip(FEATURES, model["scales"].tolist())),
                "fixed_coefficients": {"intercept": float(model["beta"][0]), **dict(zip(FEATURES, model["beta"][1:].tolist()))},
                "section_random_intercepts": model["random"],
                "sigma_rate_m_per_year": model["sigma_rate"],
            }
        )
        for row in split["test"]:
            mean, sd = predict(model, row)
            source_length = row["source_geometry"]["crack_line_length_m"]
            target_length = row["target_geometry"]["crack_line_length_m"]
            positive_increment = max(0.0, mean - source_length)
            source_payload = payload(row["source_geojson"])
            target_payload = payload(row["target_geojson"])
            lines = crack_lines(source_payload)
            extension = positive_increment / (2 * len(lines)) if lines else 0.0
            predicted_lines = [extend_line(line, extension) for line in lines]
            geometry = geometry_metrics(source_payload, target_payload, predicted_lines)
            lower = max(0.0, mean - Z90 * sd)
            upper = mean + Z90 * sd
            predictions.append(
                {
                    "axis": split["axis"],
                    "fold": split["fold"],
                    "held_out_section": split["held_out_section"],
                    "transition_id": row["transition_id"],
                    "section": row["section"],
                    "target_crack_length_m": target_length,
                    "predicted_mean_crack_length_m": mean,
                    "predicted_sd_crack_length_m": sd,
                    "lower_90_m": lower,
                    "upper_90_m": upper,
                    "covered_90": lower <= target_length <= upper,
                    "interval_width_90_m": upper - lower,
                    "crps_m": gaussian_crps(mean, sd, target_length),
                    "crack_length_absolute_error_m": abs(mean - target_length),
                    **geometry,
                }
            )

    baseline_rows = read_baselines(baseline_root / "baseline_predictions.csv")
    persistence = {
        (row["axis"], row["fold"], row["transition_id"]): row
        for row in baseline_rows
        if row["model"] == "persistence"
    }
    loso = [row for row in predictions if row["axis"] == "leave_one_section_out"]
    persistence_loso = [persistence[(row["axis"], row["fold"], row["transition_id"])] for row in loso]
    challenger_length = float(np.mean([row["crack_length_absolute_error_m"] for row in loso]))
    baseline_length = float(np.mean([row["crack_length_absolute_error_m"] for row in persistence_loso]))
    challenger_geometry = float(np.mean([row["new_geometry_symmetric_difference_m2"] for row in loso]))
    baseline_geometry = float(np.mean([row["new_geometry_symmetric_difference_m2"] for row in persistence_loso]))
    section_results = []
    for section in sorted({row["section"] for row in loso}):
        challenge = [row for row in loso if row["section"] == section]
        control = [persistence[(row["axis"], row["fold"], row["transition_id"])] for row in challenge]
        c_length = float(np.mean([row["crack_length_absolute_error_m"] for row in challenge]))
        p_length = float(np.mean([row["crack_length_absolute_error_m"] for row in control]))
        c_geom = float(np.mean([row["new_geometry_symmetric_difference_m2"] for row in challenge]))
        p_geom = float(np.mean([row["new_geometry_symmetric_difference_m2"] for row in control]))
        section_results.append(
            {
                "section": section,
                "growth_improvement_percent": percent_improvement(c_length, p_length),
                "geometry_improvement_percent": percent_improvement(c_geom, p_geom),
                "improves_both": c_length < p_length and c_geom < p_geom,
            }
        )
    growth_improvement = percent_improvement(challenger_length, baseline_length)
    geometry_improvement = percent_improvement(challenger_geometry, baseline_geometry)
    section_wins = sum(row["improves_both"] for row in section_results)
    coverage = float(np.mean([row["covered_90"] for row in loso]))
    gates = {
        "growth_improvement_at_least_10_percent": growth_improvement >= 10.0,
        "geometry_improvement_at_least_10_percent": geometry_improvement >= 10.0,
        "improves_both_in_at_least_four_sections": section_wins >= 4,
        "coverage_between_85_and_95_percent": 0.85 <= coverage <= 0.95,
    }
    reliability_positive = all(gates.values())

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    prediction_path = output / "state_space_predictions.csv"
    with prediction_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(predictions[0]))
        writer.writeheader();writer.writerows(predictions)
    decision = {
        "status": "RELIABILITY_POSITIVE" if reliability_positive else "RELIABILITY_NEGATIVE",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": "hierarchical_probabilistic_state_space_crack_growth_v1",
        "fixed_ridge": FIXED_RIDGE,
        "random_intercept_pseudo_count": RANDOM_INTERCEPT_PSEUDO_COUNT,
        "predictive_distribution": "Gaussian change-rate residual propagated over interval duration",
        "features": list(FEATURES),
        "unseen_section_growth_improvement_percent": growth_improvement,
        "unseen_section_new_geometry_improvement_percent": geometry_improvement,
        "unseen_section_90_interval_coverage": coverage,
        "section_wins": section_wins,
        "section_results": section_results,
        "gates": gates,
        "model_receipts": model_receipts,
        "transition_manifest_sha256": sha256(transition_manifest_path),
        "baseline_manifest_sha256": sha256(baseline_manifest_path),
        "predictions_sha256": sha256(prediction_path),
        "claim_boundary": "A positive status supports only this six-section observation-conditioned benchmark; a negative status forbids architecture sweeping as a rescue.",
    }
    decision_path = output / "decision.json"
    decision_path.write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": decision["status"], "growth_improvement_percent": growth_improvement, "geometry_improvement_percent": geometry_improvement, "coverage": coverage, "section_wins": section_wins, "decision_sha256": sha256(decision_path)}))
    return 0 if reliability_positive else 3


if __name__ == "__main__":
    raise SystemExit(main())
