#!/usr/bin/env python3
"""Fail-closed observation-state gate for frozen LTPP 06-1253 line fields."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy import stats


DEFAULT_INPUT = Path(
    "/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/"
    "real_road_acquisition/ltpp_06_1253_single_annotator_fields_v1_20260805/"
    "frozen_observation_fields.npz"
)
DEFAULT_OUTPUT = Path(
    "/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/"
    "real_road_acquisition/ltpp_06_1253_observation_state_gate_v1_20260805"
)
SEED = 20260805
N_SAMPLES = 96
N_BOOT = 2000
ACTIVE_THRESHOLD = 0.1
SMOOTH_FACTORS = (0.25, 0.5, 1.0)
LATENT_FACTORS = (0.0, 0.5, 1.0)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def dates_to_years(values: np.ndarray) -> np.ndarray:
    dates = [datetime.strptime(str(v), "%Y%m%d") for v in values]
    origin = dates[0]
    return np.asarray([(d - origin).days / 365.2425 for d in dates], dtype=float)


def balanced_mean(values: np.ndarray, active: np.ndarray) -> float:
    if not np.any(active) or np.all(active):
        return float("nan")
    return 0.5 * float(np.mean(values[active])) + 0.5 * float(np.mean(values[~active]))


def balanced_mae(pred: np.ndarray, target: np.ndarray) -> float:
    return balanced_mean(np.abs(pred - target), target >= ACTIVE_THRESHOLD)


def soft_dice(pred: np.ndarray, target: np.ndarray) -> float:
    numerator = 2.0 * float(np.sum(pred * target)) + 1e-12
    denominator = float(np.sum(pred * pred) + np.sum(target * target)) + 1e-12
    return numerator / denominator


def pava_rows(values: np.ndarray) -> np.ndarray:
    """Unweighted PAVA along axis 1 for a small number of dates."""
    result = np.empty_like(values, dtype=float)
    for row_index, row in enumerate(values):
        levels: list[float] = []
        weights: list[int] = []
        for value in row:
            levels.append(float(value))
            weights.append(1)
            while len(levels) >= 2 and levels[-2] > levels[-1]:
                weight = weights[-2] + weights[-1]
                level = (levels[-2] * weights[-2] + levels[-1] * weights[-1]) / weight
                levels[-2:] = [level]
                weights[-2:] = [weight]
        expanded: list[float] = []
        for level, weight in zip(levels, weights):
            expanded.extend([level] * weight)
        result[row_index] = expanded
    return result


def infer_latent(history: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Estimate nondecreasing pixel states and zero-mean survey bias."""
    bias = np.zeros(history.shape[0], dtype=float)
    latent = history.copy()
    for _ in range(5):
        adjusted = np.clip(history - bias[:, None], 0.0, 1.0)
        latent = pava_rows(adjusted.T).T
        residual = history - latent
        new_bias = np.median(residual, axis=1)
        new_bias -= np.mean(new_bias)
        bias = np.clip(new_bias, -0.2, 0.2)
    return np.clip(latent, 0.0, 1.0), bias


def predict_persistence(history: np.ndarray) -> np.ndarray:
    return history[-1].copy()


def predict_smooth(history: np.ndarray, times: np.ndarray, target_time: float, factor: float) -> np.ndarray:
    dt_previous = max(times[-1] - times[-2], 1e-9)
    dt_forecast = max(target_time - times[-1], 0.0)
    slope = (history[-1] - history[-2]) / dt_previous
    return np.clip(history[-1] + factor * slope * dt_forecast, 0.0, 1.0)


def predict_latent(history: np.ndarray, times: np.ndarray, target_time: float, factor: float) -> np.ndarray:
    latent, _ = infer_latent(history)
    increments = np.maximum(np.diff(latent, axis=0), 0.0)
    durations = np.maximum(np.diff(times), 1e-9)[:, None]
    annual_rate = np.mean(increments / durations, axis=0)
    dt_forecast = max(target_time - times[-1], 0.0)
    return np.clip(latent[-1] + factor * annual_rate * dt_forecast, 0.0, 1.0)


def select_factor(history: np.ndarray, times: np.ndarray, candidates: tuple[float, ...], model: str) -> float:
    scores: dict[float, list[float]] = {factor: [] for factor in candidates}
    for target_index in range(2, history.shape[0]):
        inner_history = history[:target_index]
        inner_times = times[:target_index]
        target = history[target_index]
        for factor in candidates:
            if model == "S":
                pred = predict_smooth(inner_history, inner_times, times[target_index], factor)
            else:
                pred = predict_latent(inner_history, inner_times, times[target_index], factor)
            scores[factor].append(balanced_mae(pred, target))
    ranked = []
    for factor in candidates:
        finite = [score for score in scores[factor] if np.isfinite(score)]
        ranked.append((float(np.mean(finite)) if finite else float("inf"), factor))
    return min(ranked, key=lambda item: (item[0], item[1]))[1]


def shared_noise_scales(history: np.ndarray) -> tuple[float, float]:
    changes = np.diff(history, axis=0)
    union = np.any(history >= 0.01, axis=0)
    sample = changes[:, union].ravel() if np.any(union) else changes.ravel()
    center = float(np.median(sample))
    mad = float(np.median(np.abs(sample - center)))
    sigma_observation = max(0.01, mad / 0.67448975 / np.sqrt(2.0))
    survey_means = np.mean(changes[:, union], axis=1) if np.any(union) else np.mean(changes, axis=1)
    sigma_bias = max(0.0025, float(np.std(survey_means, ddof=1)) if survey_means.size > 1 else 0.0025)
    return min(sigma_observation, 0.35), min(sigma_bias, 0.20)


def predictive_samples(
    mean: np.ndarray,
    sigma_observation: float,
    sigma_bias: float,
    standard_t: np.ndarray,
    standard_bias: np.ndarray,
) -> np.ndarray:
    noise = sigma_observation * standard_t + sigma_bias * standard_bias[:, None]
    return np.clip(mean[None, :] + noise, 0.0, 1.0).astype(np.float32)


def crps_from_samples(samples: np.ndarray, target: np.ndarray) -> np.ndarray:
    n = samples.shape[0]
    first = np.mean(np.abs(samples - target[None, :]), axis=0)
    ordered = np.sort(samples, axis=0)
    coefficients = 2.0 * np.arange(1, n + 1, dtype=float) - n - 1.0
    half_pairwise = np.sum(coefficients[:, None] * ordered, axis=0) / (n * n)
    return first - half_pairwise


def tile_ids(height: int, width: int) -> np.ndarray:
    result = np.empty((height, width), dtype=int)
    tile = 0
    for rows in np.array_split(np.arange(height), 6):
        for cols in np.array_split(np.arange(width), 10):
            result[np.ix_(rows, cols)] = tile
            tile += 1
    return result.ravel()


def tile_class_summaries(values: np.ndarray, active: np.ndarray, tiles: np.ndarray) -> dict[str, list[float]]:
    summary = {"active_sum": [], "active_n": [], "background_sum": [], "background_n": []}
    for tile in range(60):
        selected = tiles == tile
        active_selected = selected & active
        background_selected = selected & ~active
        summary["active_sum"].append(float(np.sum(values[active_selected])))
        summary["active_n"].append(int(np.sum(active_selected)))
        summary["background_sum"].append(float(np.sum(values[background_selected])))
        summary["background_n"].append(int(np.sum(background_selected)))
    return summary


def sampled_balanced(summary: dict[str, list[float]], indices: np.ndarray) -> float:
    active_n = sum(summary["active_n"][i] for i in indices)
    background_n = sum(summary["background_n"][i] for i in indices)
    if active_n == 0 or background_n == 0:
        return float("nan")
    active = sum(summary["active_sum"][i] for i in indices) / active_n
    background = sum(summary["background_sum"][i] for i in indices) / background_n
    return 0.5 * (active + background)


def bootstrap_improvement(
    fold_summaries: list[dict[str, dict[str, list[float]]]], baseline: str, rng: np.random.Generator
) -> tuple[float, float, float]:
    values = []
    for _ in range(N_BOOT):
        baseline_scores = []
        latent_scores = []
        for fold in fold_summaries:
            indices = rng.integers(0, 60, size=60)
            baseline_scores.append(sampled_balanced(fold[baseline], indices))
            latent_scores.append(sampled_balanced(fold["L"], indices))
        base = float(np.nanmean(baseline_scores))
        latent = float(np.nanmean(latent_scores))
        values.append((base - latent) / max(base, 1e-12))
    return tuple(float(v) for v in np.quantile(values, [0.05, 0.5, 0.95]))


@dataclass
class FoldOutput:
    row: dict[str, object]
    crps_tiles: dict[str, dict[str, list[float]]]


def evaluate_fold(
    fields: np.ndarray,
    times: np.ndarray,
    target_index: int,
    shape: tuple[int, int],
    rng: np.random.Generator,
) -> FoldOutput:
    history = fields[:target_index]
    target = fields[target_index]
    previous = fields[target_index - 1]
    smooth_factor = select_factor(history, times[:target_index], SMOOTH_FACTORS, "S")
    latent_factor = select_factor(history, times[:target_index], LATENT_FACTORS, "L")
    means = {
        "P": predict_persistence(history),
        "S": predict_smooth(history, times[:target_index], times[target_index], smooth_factor),
        "L": predict_latent(history, times[:target_index], times[target_index], latent_factor),
    }
    sigma_observation, sigma_bias = shared_noise_scales(history)
    standard_t = stats.t.rvs(df=4, size=(N_SAMPLES, target.size), random_state=rng).astype(np.float32)
    standard_bias = rng.standard_normal(N_SAMPLES).astype(np.float32)
    active = target >= ACTIVE_THRESHOLD
    tiles = tile_ids(*shape)
    row: dict[str, object] = {
        "fold": f"F{target_index - 2}",
        "train_surveys": target_index,
        "target_index": target_index,
        "smooth_factor": smooth_factor,
        "latent_factor": latent_factor,
        "sigma_observation": sigma_observation,
        "sigma_survey_bias": sigma_bias,
        "active_fraction": float(np.mean(active)),
        "mean_abs_change": float(np.mean(np.abs(target - previous))),
        "informative": bool(np.mean(active) >= 0.001 and np.mean(np.abs(target - previous)) > 1e-4),
    }
    crps_tiles: dict[str, dict[str, list[float]]] = {}
    for name, mean in means.items():
        samples = predictive_samples(mean, sigma_observation, sigma_bias, standard_t, standard_bias)
        crps = crps_from_samples(samples, target)
        lower, upper = np.quantile(samples, [0.1, 0.9], axis=0)
        row[f"{name}_bmae"] = balanced_mae(mean, target)
        row[f"{name}_bcrps"] = balanced_mean(crps, active)
        row[f"{name}_soft_dice"] = soft_dice(mean, target)
        row[f"{name}_coverage80"] = float(np.mean((target >= lower) & (target <= upper)))
        row[f"{name}_interval_width"] = float(np.mean(upper - lower))
        row[f"{name}_all_zero"] = bool(np.all(mean <= 1e-8))
        row[f"{name}_all_one"] = bool(np.all(mean >= 1.0 - 1e-8))
        row[f"{name}_equals_persistence"] = bool(np.allclose(mean, means["P"], atol=1e-10, rtol=0.0))
        crps_tiles[name] = tile_class_summaries(crps, active, tiles)
    return FoldOutput(row=row, crps_tiles=crps_tiles)


def relative_improvement(baseline: float, candidate: float) -> float:
    return (baseline - candidate) / max(baseline, 1e-12)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    with np.load(args.input, allow_pickle=False) as archive:
        fields_3d = np.asarray(archive["line_damage"][:7], dtype=float)
        dates = np.asarray(archive["survey_dates"][:7])
    if fields_3d.shape != (7, 126, 382):
        raise ValueError(f"unexpected line_damage shape: {fields_3d.shape}")
    if not np.all(np.isfinite(fields_3d)) or np.min(fields_3d) < 0.0 or np.max(fields_3d) > 1.0:
        raise ValueError("line_damage must be finite and bounded in [0, 1]")

    args.output.mkdir(parents=True, exist_ok=True)
    fields = fields_3d.reshape(7, -1)
    times = dates_to_years(dates)
    rng = np.random.default_rng(SEED)
    folds = [evaluate_fold(fields, times, target, fields_3d.shape[1:], rng) for target in range(3, 7)]
    rows = [fold.row for fold in folds]
    tile_summaries = [fold.crps_tiles for fold in folds]

    medians: dict[str, float] = {}
    for model in ("P", "S", "L"):
        for metric in ("bmae", "bcrps", "soft_dice", "coverage80", "interval_width"):
            medians[f"{model}_{metric}"] = float(np.median([float(r[f"{model}_{metric}"]) for r in rows]))

    bmae_improvement = {
        baseline: relative_improvement(medians[f"{baseline}_bmae"], medians["L_bmae"])
        for baseline in ("P", "S")
    }
    bcrps_improvement = {
        baseline: relative_improvement(medians[f"{baseline}_bcrps"], medians["L_bcrps"])
        for baseline in ("P", "S")
    }
    bmae_wins = {
        baseline: sum(float(r["L_bmae"]) < float(r[f"{baseline}_bmae"]) for r in rows)
        for baseline in ("P", "S")
    }
    worst_regression = max(
        (float(r["L_bmae"]) - min(float(r["P_bmae"]), float(r["S_bmae"])))
        / max(min(float(r["P_bmae"]), float(r["S_bmae"])), 1e-12)
        for r in rows
    )
    bootstrap = {
        baseline: dict(zip(("q05", "q50", "q95"), bootstrap_improvement(tile_summaries, baseline, rng)))
        for baseline in ("P", "S")
    }
    dice_guard = all(
        float(r["L_soft_dice"]) >= max(float(r["P_soft_dice"]), float(r["S_soft_dice"])) - 0.02
        for r in rows
    )
    coverage_guard = all(0.70 <= float(r["L_coverage80"]) <= 0.90 for r in rows)
    width_guard = all(
        float(r["L_interval_width"]) <= 1.5 * float(r["S_interval_width"]) + 1e-12 for r in rows
    )
    finite_guard = all(
        np.isfinite(float(value))
        for row in rows
        for key, value in row.items()
        if key.endswith(("bmae", "bcrps", "soft_dice", "coverage80", "interval_width"))
    )
    informative_guard = sum(bool(r["informative"]) for r in rows) >= 3
    degenerate_guard = not all(bool(r["L_equals_persistence"]) for r in rows) and not any(
        bool(r["L_all_zero"]) or bool(r["L_all_one"]) for r in rows
    )

    gates = {
        "bmae_median_improvement_ge_10pct_both": all(v >= 0.10 for v in bmae_improvement.values()),
        "bmae_wins_ge_3_of_4_both": all(v >= 3 for v in bmae_wins.values()),
        "worst_fold_regression_le_5pct": worst_regression <= 0.05,
        "bcrps_median_improvement_ge_5pct_both": all(v >= 0.05 for v in bcrps_improvement.values()),
        "bcrps_bootstrap_q05_positive_both": all(v["q05"] > 0.0 for v in bootstrap.values()),
        "soft_dice_guard_all_folds": dice_guard,
        "coverage80_in_70_90_all_folds": coverage_guard,
        "interval_width_le_1_5x_s_all_folds": width_guard,
        "all_metrics_finite": finite_guard,
        "at_least_3_informative_folds": informative_guard,
        "latent_not_degenerate": degenerate_guard,
    }
    decision = "PASS_L_AS_NEXT_FIELD_ADAPTER" if all(gates.values()) else "FAIL_L_NOT_QUALIFIED"

    result = {
        "decision": decision,
        "claim_class": "state-semantics / trajectory-sufficiency diagnostic",
        "input": str(args.input),
        "input_sha256": sha256(args.input),
        "script_sha256": sha256(Path(__file__)),
        "survey_dates": [str(v) for v in dates],
        "seed": SEED,
        "n_predictive_samples": N_SAMPLES,
        "n_cluster_bootstrap": N_BOOT,
        "models": ["P_persistence", "S_smooth_nonmonotone", "L_latent_irreversible_noisy_observation"],
        "medians": medians,
        "bmae_improvement_L_vs_baseline": bmae_improvement,
        "bcrps_improvement_L_vs_baseline": bcrps_improvement,
        "bmae_wins_L_vs_baseline": bmae_wins,
        "worst_fold_bmae_regression_vs_best_baseline": worst_regression,
        "bcrps_cluster_bootstrap_improvement": bootstrap,
        "gates": gates,
        "folds": rows,
        "evidence_boundary": (
            "Single-section, single-annotator line proxy only. A pass qualifies the representation for "
            "multisection testing; it does not establish physical damage truth, PDE terms, causality, or generalization."
        ),
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

    with (args.output / "fold_metrics.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    failed = [name for name, passed in gates.items() if not passed]
    decision_lines = [
        "# LTPP 06-1253 Observation-State Gate v1",
        "",
        f"**Decision:** `{decision}`",
        "",
        "## Gate results",
        "",
    ]
    decision_lines.extend(f"- `{name}`: {'PASS' if passed else 'FAIL'}" for name, passed in gates.items())
    decision_lines.extend(
        [
            "",
            "## Key quantities",
            "",
            f"- Median bMAE improvement L vs P: {bmae_improvement['P']:.2%}",
            f"- Median bMAE improvement L vs S: {bmae_improvement['S']:.2%}",
            f"- Median bCRPS improvement L vs P: {bcrps_improvement['P']:.2%}",
            f"- Median bCRPS improvement L vs S: {bcrps_improvement['S']:.2%}",
            f"- Failed gates: {', '.join(failed) if failed else 'none'}",
            "",
            "## Interpretation boundary",
            "",
            result["evidence_boundary"],
            "",
        ]
    )
    (args.output / "decision.md").write_text("\n".join(decision_lines))
    print(json.dumps({"decision": decision, "failed_gates": failed, "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
