"""Single-shot STLSQ and grouped stability-validated weak selection."""

from __future__ import annotations

from dataclasses import dataclass
import itertools

import numpy as np
import pandas as pd

from .weak_system import WeakSystem


@dataclass(frozen=True)
class SelectionResult:
    stable_support: tuple[str, ...]
    final_coefficients: pd.Series
    support_summary: pd.DataFrame
    trial_coefficients: pd.DataFrame
    metrics: dict[str, float | int | str | list[str]]


@dataclass(frozen=True)
class ValidationSelectionResult:
    support: tuple[str, ...]
    coefficients: pd.Series
    trace: pd.DataFrame
    validation_rmse: float
    null_validation_rmse: float


def _ridge(A: np.ndarray, b: np.ndarray, l2: float) -> np.ndarray:
    gram = np.einsum("ni,nj->ij", A, A)
    rhs = np.einsum("ni,n->i", A, b)
    return np.linalg.solve(gram + l2 * np.eye(A.shape[1]), rhs)


def fit_stlsq(
    A: np.ndarray,
    b: np.ndarray,
    *,
    relative_threshold: float = 0.08,
    l2: float = 1e-8,
    max_iter: int = 12,
) -> np.ndarray:
    """Fit sequentially thresholded ridge regression with column normalization."""

    A = np.asarray(A, dtype=float)
    b = np.asarray(b, dtype=float).reshape(-1)
    if A.ndim != 2 or A.shape[0] != b.size:
        raise ValueError("A and b have incompatible shapes")
    scales = np.linalg.norm(A, axis=0)
    scales[scales <= np.finfo(float).eps] = 1.0
    X = A / scales
    active = np.ones(A.shape[1], dtype=bool)
    beta_scaled = np.zeros(A.shape[1], dtype=float)
    for _ in range(max_iter):
        beta_active = _ridge(X[:, active], b, l2)
        beta_scaled[:] = 0.0
        beta_scaled[active] = beta_active
        peak = float(np.max(np.abs(beta_scaled)))
        if peak <= np.finfo(float).eps:
            break
        new_active = np.abs(beta_scaled) >= relative_threshold * peak
        if not new_active.any():
            new_active[int(np.argmax(np.abs(beta_scaled)))] = True
        if np.array_equal(new_active, active):
            break
        active = new_active
    beta_scaled[:] = 0.0
    beta_scaled[active] = _ridge(X[:, active], b, l2)
    return beta_scaled / scales


def _rmse(y: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(np.asarray(y) - np.asarray(predicted)))))


def _predict(A: np.ndarray, beta: np.ndarray) -> np.ndarray:
    return np.einsum("ni,i->n", A, beta)


def _support(coefficients: np.ndarray, tolerance: float = 1e-12) -> np.ndarray:
    return np.abs(coefficients) > tolerance


def _mean_pairwise_jaccard(supports: np.ndarray) -> float:
    values: list[float] = []
    for i in range(len(supports)):
        for j in range(i + 1, len(supports)):
            union = np.logical_or(supports[i], supports[j]).sum()
            intersection = np.logical_and(supports[i], supports[j]).sum()
            values.append(1.0 if union == 0 else float(intersection / union))
    return 1.0 if not values else float(np.mean(values))


def stability_validated_select(
    system: WeakSystem,
    *,
    n_trials: int = 64,
    train_fraction: float = 0.7,
    relative_threshold: float = 0.08,
    stable_frequency: float = 0.75,
    minimum_sign_consistency: float = 0.85,
    seed: int = 0,
) -> SelectionResult:
    """Repeat grouped weak selection and retain frequent, sign-consistent terms."""

    if n_trials < 8:
        raise ValueError("n_trials must be at least 8")
    groups = np.asarray(sorted(system.metadata["split_group"].unique()))
    if len(groups) < 3:
        raise ValueError("At least three trajectory/time-block groups are required")
    n_train = min(len(groups) - 1, max(2, int(round(train_fraction * len(groups)))))
    rng = np.random.default_rng(seed)
    trial_rows: list[dict[str, object]] = []
    holdout_rmse: list[float] = []
    null_rmse: list[float] = []
    condition_numbers: list[float] = []
    for trial in range(n_trials):
        train_groups = set(rng.choice(groups, size=n_train, replace=False).tolist())
        train_mask = system.metadata["split_group"].isin(train_groups).to_numpy()
        holdout_mask = ~train_mask
        beta = fit_stlsq(
            system.A[train_mask],
            system.b[train_mask],
            relative_threshold=relative_threshold,
        )
        holdout_rmse.append(_rmse(system.b[holdout_mask], _predict(system.A[holdout_mask], beta)))
        null_rmse.append(_rmse(system.b[holdout_mask], np.zeros(int(holdout_mask.sum()))))
        norms = np.linalg.norm(system.A[train_mask], axis=0)
        variable = norms > np.finfo(float).eps
        normalized = system.A[train_mask][:, variable] / norms[variable]
        condition_numbers.append(
            float(np.linalg.cond(normalized)) if int(variable.sum()) else float("inf")
        )
        row: dict[str, object] = {
            "trial": trial,
            "train_groups": "|".join(sorted(train_groups)),
            "holdout_groups": "|".join(sorted(set(groups).difference(train_groups))),
            "holdout_rmse": holdout_rmse[-1],
            "null_holdout_rmse": null_rmse[-1],
        }
        row.update({name: float(beta[j]) for j, name in enumerate(system.term_names)})
        trial_rows.append(row)

    trials = pd.DataFrame(trial_rows)
    summaries: list[dict[str, object]] = []
    for name in system.term_names:
        values = trials[name].to_numpy(float)
        selected = np.abs(values) > 1e-12
        frequency = float(np.mean(selected))
        if selected.any():
            nonzero = values[selected]
            positive = float(np.mean(nonzero > 0.0))
            sign_consistency = max(positive, 1.0 - positive)
            median = float(np.median(nonzero))
        else:
            sign_consistency = 0.0
            median = 0.0
        stable = frequency >= stable_frequency and sign_consistency >= minimum_sign_consistency
        summaries.append(
            {
                "term": name,
                "selection_frequency": frequency,
                "sign_consistency": sign_consistency,
                "median_selected_coefficient": median,
                "stable": stable,
            }
        )
    summary = pd.DataFrame(summaries)
    stable_names = tuple(summary.loc[summary["stable"], "term"].astype(str))
    final = np.zeros(len(system.term_names), dtype=float)
    if stable_names:
        columns = [system.term_names.index(name) for name in stable_names]
        final[np.asarray(columns)] = _ridge(system.A[:, columns], system.b, 1e-8)
    final_series = pd.Series(final, index=system.term_names, name="coefficient")

    first_train = trials.iloc[0]["train_groups"].split("|")
    first_mask = system.metadata["split_group"].isin(first_train).to_numpy()
    baseline_beta = fit_stlsq(
        system.A[first_mask], system.b[first_mask], relative_threshold=relative_threshold
    )
    baseline_holdout = ~first_mask
    baseline_rmse = _rmse(
        system.b[baseline_holdout], _predict(system.A[baseline_holdout], baseline_beta)
    )
    mean_holdout = float(np.mean(holdout_rmse))
    mean_null = float(np.mean(null_rmse))
    trial_supports = np.abs(trials.loc[:, system.term_names].to_numpy(float)) > 1e-12
    correlation = np.full((len(system.term_names), len(system.term_names)), np.nan)
    variable = np.std(system.A, axis=0) > np.finfo(float).eps
    if int(variable.sum()) >= 2:
        correlation[np.ix_(variable, variable)] = np.corrcoef(
            system.A[:, variable], rowvar=False
        )
    correlation_warnings = []
    for i, left in enumerate(system.term_names):
        for j in range(i + 1, len(system.term_names)):
            value = float(correlation[i, j])
            if np.isfinite(value) and abs(value) >= 0.95:
                correlation_warnings.append(f"{left}|{system.term_names[j]}|{value:.6f}")
    metrics: dict[str, float | int | str | list[str]] = {
        "n_trials": n_trials,
        "n_weak_rows": int(system.A.shape[0]),
        "stable_frequency_threshold": stable_frequency,
        "minimum_sign_consistency": minimum_sign_consistency,
        "stable_support": list(stable_names),
        "single_shot_support": [
            name for name, chosen in zip(system.term_names, _support(baseline_beta)) if chosen
        ],
        "mean_grouped_holdout_rmse": mean_holdout,
        "single_shot_holdout_rmse": baseline_rmse,
        "mean_null_holdout_rmse": mean_null,
        "mean_holdout_improvement_vs_null": 0.0 if mean_null == 0.0 else 1.0 - mean_holdout / mean_null,
        "mean_pairwise_trial_support_jaccard": _mean_pairwise_jaccard(trial_supports),
        "median_normalized_condition_number": float(np.median(condition_numbers)),
        "condition_warning_fraction_gt_1e6": float(np.mean(np.asarray(condition_numbers) > 1e6)),
        "candidate_correlation_warnings_abs_ge_0p95": correlation_warnings,
    }
    return SelectionResult(stable_names, final_series, summary, trials, metrics)


def validation_select_support(
    stability_result: SelectionResult,
    train_system: WeakSystem,
    validation_system: WeakSystem,
    *,
    near_best_tolerance: float = 0.05,
    minimum_improvement_over_null: float = 0.05,
) -> ValidationSelectionResult:
    """Choose the smallest stable support within 5% of best validation RMSE."""

    if train_system.term_names != validation_system.term_names:
        raise ValueError("Train and validation systems use different term libraries")
    candidates = tuple(stability_result.stable_support)
    candidate_indices = [train_system.term_names.index(name) for name in candidates]
    null_rmse = _rmse(validation_system.b, np.zeros_like(validation_system.b))
    rows: list[dict[str, object]] = []
    fitted: dict[tuple[str, ...], np.ndarray] = {}
    for size in range(len(candidates) + 1):
        for names in itertools.combinations(candidates, size):
            indices = [train_system.term_names.index(name) for name in names]
            full_beta = np.zeros(len(train_system.term_names), dtype=float)
            if indices:
                full_beta[np.asarray(indices)] = _ridge(
                    train_system.A[:, indices], train_system.b, 1e-8
                )
            rmse = _rmse(validation_system.b, _predict(validation_system.A, full_beta))
            fitted[names] = full_beta
            rows.append(
                {
                    "support": "|".join(names),
                    "support_size": len(names),
                    "validation_rmse": rmse,
                    "improvement_over_null": 0.0 if null_rmse == 0.0 else 1.0 - rmse / null_rmse,
                }
            )
    trace = pd.DataFrame(rows)
    best_rmse = float(trace["validation_rmse"].min())
    eligible = trace[
        (trace["validation_rmse"] <= best_rmse * (1.0 + near_best_tolerance))
        & (trace["improvement_over_null"] >= minimum_improvement_over_null)
    ].sort_values(["support_size", "validation_rmse", "support"])
    if eligible.empty:
        chosen_names: tuple[str, ...] = ()
    else:
        encoded = str(eligible.iloc[0]["support"])
        chosen_names = () if not encoded else tuple(encoded.split("|"))
    beta = fitted[chosen_names]
    validation_rmse = _rmse(validation_system.b, _predict(validation_system.A, beta))
    return ValidationSelectionResult(
        support=chosen_names,
        coefficients=pd.Series(beta, index=train_system.term_names, name="coefficient"),
        trace=trace.sort_values(["validation_rmse", "support_size"]).reset_index(drop=True),
        validation_rmse=validation_rmse,
        null_validation_rmse=null_rmse,
    )
