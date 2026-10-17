"""Uncertainty-aware selection across independently frozen field adapters."""

from __future__ import annotations

from dataclasses import dataclass
import itertools

import numpy as np
import pandas as pd

from .selectors import fit_stlsq
from .weak_system import WeakSystem


@dataclass(frozen=True)
class UncertaintySelectionResult:
    support: tuple[str, ...]
    coefficients: pd.Series
    support_summary: pd.DataFrame
    replicate_coefficients: pd.DataFrame
    validation_trace: pd.DataFrame
    uncertainty_table: pd.DataFrame
    metrics: dict[str, object]


def _check_aligned(systems: list[WeakSystem]) -> None:
    if len(systems) < 2:
        raise ValueError("Uncertainty-aware selection needs at least two adapters")
    reference = systems[0]
    reference_windows = reference.metadata["window_id"].tolist()
    for system in systems[1:]:
        if system.term_names != reference.term_names:
            raise ValueError("Adapter weak systems use different candidate libraries")
        if system.metadata["window_id"].tolist() != reference_windows:
            raise ValueError("Adapter weak systems do not share the same weak-window pool")


def _predict(A: np.ndarray, beta: np.ndarray) -> np.ndarray:
    return np.einsum("ni,i->n", A, beta)


def _weighted_ridge(A: np.ndarray, b: np.ndarray, weight: np.ndarray, l2: float = 1e-8) -> np.ndarray:
    root = np.sqrt(np.asarray(weight, dtype=float))
    X = A * root[:, None]
    y = b * root
    gram = np.einsum("ni,nj->ij", X, X)
    rhs = np.einsum("ni,n->i", X, y)
    return np.linalg.solve(gram + l2 * np.eye(A.shape[1]), rhs)


def _uncertainty_weights(
    A_stack: np.ndarray,
    b_stack: np.ndarray,
    beta: np.ndarray,
    tip_mask: np.ndarray,
    *,
    minimum_weight: float = 0.20,
    maximum_weight: float = 5.0,
    tip_weight_floor: float = 0.50,
) -> tuple[np.ndarray, np.ndarray]:
    residual = b_stack - np.einsum("kni,i->kn", A_stack, beta)
    variance = np.var(residual, axis=0, ddof=1)
    positive = variance[variance > np.finfo(float).eps]
    scale = float(np.median(positive)) if positive.size else 1.0
    raw = scale / np.maximum(variance, np.finfo(float).eps)
    weight = np.clip(raw, minimum_weight, maximum_weight)
    weight[tip_mask] = np.maximum(weight[tip_mask], tip_weight_floor)
    return weight, variance


def _iterative_fit(
    A_stack: np.ndarray,
    b_stack: np.ndarray,
    tip_mask: np.ndarray,
    *,
    relative_threshold: float = 0.08,
    iterations: int = 3,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean_A = np.mean(A_stack, axis=0)
    mean_b = np.mean(b_stack, axis=0)
    beta = fit_stlsq(mean_A, mean_b, relative_threshold=relative_threshold)
    weight = np.ones(len(mean_b), dtype=float)
    variance = np.zeros(len(mean_b), dtype=float)
    for _ in range(iterations):
        weight, variance = _uncertainty_weights(A_stack, b_stack, beta, tip_mask)
        root = np.sqrt(weight)
        beta = fit_stlsq(
            mean_A * root[:, None],
            mean_b * root,
            relative_threshold=relative_threshold,
        )
    return beta, weight, variance


def _selection_frequency(values: np.ndarray) -> tuple[float, float, float]:
    selected = np.abs(values) > 1e-12
    frequency = float(np.mean(selected))
    if not selected.any():
        return frequency, 0.0, 0.0
    nonzero = values[selected]
    positive = float(np.mean(nonzero > 0.0))
    sign_consistency = max(positive, 1.0 - positive)
    scale = float(np.std(nonzero, ddof=1)) if len(nonzero) > 1 else 0.0
    signal_to_uncertainty = float(abs(np.median(nonzero)) / max(scale, 1e-12))
    return frequency, sign_consistency, signal_to_uncertainty


def uncertainty_aware_select(
    train_systems: list[WeakSystem],
    validation_systems: list[WeakSystem],
    *,
    n_replicates: int = 128,
    seed: int = 0,
    overall_frequency_threshold: float = 0.70,
    sign_consistency_threshold: float = 0.90,
    stratum_frequency_threshold: float = 0.50,
    signal_to_uncertainty_threshold: float = 2.0,
) -> UncertaintySelectionResult:
    _check_aligned(train_systems)
    _check_aligned(validation_systems)
    terms = train_systems[0].term_names
    A_stack = np.stack([system.A for system in train_systems])
    b_stack = np.stack([system.b for system in train_systems])
    metadata = train_systems[0].metadata.reset_index(drop=True)
    stratum = metadata["stratum"].astype(str).to_numpy()
    tip_mask = stratum == "tip"
    low_noise_reference = np.ones(len(metadata), dtype=bool)
    rng = np.random.default_rng(seed)
    groups = np.asarray(sorted(metadata["split_group"].unique()))
    replicate_rows: list[dict[str, object]] = []
    for replicate in range(n_replicates):
        adapter_draw = rng.choice(len(train_systems), size=len(train_systems), replace=True)
        drawn_A = A_stack[adapter_draw]
        drawn_b = b_stack[adapter_draw]
        selected_groups = set(
            rng.choice(groups, size=max(2, int(round(0.70 * len(groups)))), replace=False)
        )
        group_mask = metadata["split_group"].isin(selected_groups).to_numpy()
        pool = np.flatnonzero(group_mask)
        tip_pool = pool[tip_mask[pool]]
        non_tip_pool = pool[~tip_mask[pool]]
        target_size = max(24, len(pool))
        tip_quota = min(len(tip_pool), max(4, int(round(0.20 * target_size))))
        sampled_tip = (
            rng.choice(tip_pool, size=tip_quota, replace=True)
            if tip_quota
            else np.asarray([], dtype=int)
        )
        sampled_other = rng.choice(
            non_tip_pool if len(non_tip_pool) else pool,
            size=target_size - len(sampled_tip),
            replace=True,
        )
        sampled = np.concatenate([sampled_tip, sampled_other])
        local_tip = tip_mask[sampled]
        beta, weight, variance = _iterative_fit(
            drawn_A[:, sampled], drawn_b[:, sampled], local_tip
        )
        full_weight, full_variance = _uncertainty_weights(
            drawn_A, drawn_b, beta, tip_mask
        )
        low_noise_reference = full_variance <= np.median(full_variance)
        low_idx = np.flatnonzero(group_mask & low_noise_reference)
        tip_idx = np.flatnonzero(group_mask & tip_mask)
        beta_low = (
            _iterative_fit(drawn_A[:, low_idx], drawn_b[:, low_idx], tip_mask[low_idx])[0]
            if len(low_idx) >= 24
            else np.zeros(len(terms))
        )
        beta_tip = (
            _iterative_fit(drawn_A[:, tip_idx], drawn_b[:, tip_idx], tip_mask[tip_idx])[0]
            if len(tip_idx) >= 24
            else np.zeros(len(terms))
        )
        row: dict[str, object] = {
            "replicate": replicate,
            "tip_row_fraction": float(np.mean(local_tip)),
            "tip_weight_fraction": float(
                np.sum(weight[local_tip]) / max(np.sum(weight), np.finfo(float).eps)
            ),
        }
        for j, name in enumerate(terms):
            row[name] = float(beta[j])
            row[f"low_noise__{name}"] = float(beta_low[j])
            row[f"tip__{name}"] = float(beta_tip[j])
        replicate_rows.append(row)
    replicates = pd.DataFrame(replicate_rows)
    summary_rows = []
    for name in terms:
        frequency, sign_consistency, snr = _selection_frequency(
            replicates[name].to_numpy(float)
        )
        low_frequency, _, _ = _selection_frequency(
            replicates[f"low_noise__{name}"].to_numpy(float)
        )
        tip_frequency, _, _ = _selection_frequency(
            replicates[f"tip__{name}"].to_numpy(float)
        )
        stable = (
            frequency >= overall_frequency_threshold
            and sign_consistency >= sign_consistency_threshold
            and snr >= signal_to_uncertainty_threshold
            and low_frequency >= stratum_frequency_threshold
            and tip_frequency >= stratum_frequency_threshold
        )
        summary_rows.append(
            {
                "term": name,
                "selection_frequency": frequency,
                "sign_consistency": sign_consistency,
                "coefficient_signal_to_uncertainty": snr,
                "low_noise_selection_frequency": low_frequency,
                "tip_selection_frequency": tip_frequency,
                "stable": stable,
            }
        )
    summary = pd.DataFrame(summary_rows)
    candidates = tuple(summary.loc[summary["stable"], "term"].astype(str))

    mean_train_A = np.mean(A_stack, axis=0)
    mean_train_b = np.mean(b_stack, axis=0)
    train_tip = tip_mask
    initial, train_weight, train_variance = _iterative_fit(A_stack, b_stack, train_tip)
    validation_A_stack = np.stack([system.A for system in validation_systems])
    validation_b_stack = np.stack([system.b for system in validation_systems])
    mean_validation_A = np.mean(validation_A_stack, axis=0)
    mean_validation_b = np.mean(validation_b_stack, axis=0)
    validation_tip = (
        validation_systems[0].metadata["stratum"].astype(str).to_numpy() == "tip"
    )
    validation_weight, validation_variance = _uncertainty_weights(
        validation_A_stack, validation_b_stack, initial, validation_tip
    )
    null_rmse = float(
        np.sqrt(np.average(np.square(mean_validation_b), weights=validation_weight))
    )
    trace_rows = []
    coefficients_by_support: dict[tuple[str, ...], np.ndarray] = {}
    for size in range(len(candidates) + 1):
        for support in itertools.combinations(candidates, size):
            indices = [terms.index(name) for name in support]
            beta = np.zeros(len(terms), dtype=float)
            if indices:
                beta[np.asarray(indices)] = _weighted_ridge(
                    mean_train_A[:, indices], mean_train_b, train_weight
                )
            residual = mean_validation_b - _predict(mean_validation_A, beta)
            rmse = float(np.sqrt(np.average(np.square(residual), weights=validation_weight)))
            coefficients_by_support[support] = beta
            trace_rows.append(
                {
                    "support": "|".join(support),
                    "support_size": len(support),
                    "validation_rmse": rmse,
                    "improvement_over_null": 0.0 if null_rmse == 0.0 else 1.0 - rmse / null_rmse,
                }
            )
    trace = pd.DataFrame(trace_rows)
    best = float(trace["validation_rmse"].min())
    eligible = trace[
        (trace["validation_rmse"] <= 1.05 * best)
        & (trace["improvement_over_null"] >= 0.05)
    ].sort_values(["support_size", "validation_rmse", "support"])
    if eligible.empty:
        support = ()
    else:
        encoded = str(eligible.iloc[0]["support"])
        support = () if not encoded else tuple(encoded.split("|"))
    beta = coefficients_by_support[support]
    uncertainty_table = metadata[["window_id", "trajectory_id", "stratum"]].copy()
    uncertainty_table["residual_variance"] = train_variance
    uncertainty_table["uncertainty_weight"] = train_weight
    uncertainty_table["low_noise"] = low_noise_reference
    metrics = {
        "n_adapters": len(train_systems),
        "n_replicates": n_replicates,
        "tip_row_fraction": float(np.mean(tip_mask)),
        "tip_total_weight_fraction": float(
            np.sum(train_weight[tip_mask]) / max(np.sum(train_weight), np.finfo(float).eps)
        ),
        "minimum_uncertainty_weight": float(train_weight.min()),
        "minimum_tip_weight": float(train_weight[tip_mask].min()) if tip_mask.any() else None,
        "stable_candidates_before_validation": list(candidates),
        "validation_selected_support": list(support),
        "validation_null_rmse": null_rmse,
    }
    return UncertaintySelectionResult(
        support=support,
        coefficients=pd.Series(beta, index=terms, name="coefficient"),
        support_summary=summary,
        replicate_coefficients=replicates,
        validation_trace=trace.sort_values(["validation_rmse", "support_size"]),
        uncertainty_table=uncertainty_table,
        metrics=metrics,
    )
