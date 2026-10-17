from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
import pandas as pd

from .selectors import fit_stlsq
from .weak_system import WeakSystem


@dataclass(frozen=True)
class LibraryDiagnostics:
    max_abs_correlation: float
    condition_number: float
    effective_rank: int
    max_environment_leverage: float
    per_environment_max_abs_correlation: tuple[float, ...]
    per_environment_condition_number: tuple[float, ...]


@dataclass(frozen=True)
class SharedSupportResult:
    support: tuple[str, ...]
    coefficients: pd.Series
    support_summary: pd.DataFrame
    trial_coefficients: pd.DataFrame
    validation_trace: pd.DataFrame
    diagnostics: LibraryDiagnostics
    metrics: dict[str, float | int | list[str]]


def active_measure_normalize(
    system: WeakSystem,
    *,
    floor_fraction: float = 0.10,
) -> WeakSystem:
    if "active_measure" not in system.metadata:
        raise ValueError("weak metadata does not contain active_measure")
    if not 0.0 < floor_fraction <= 1.0:
        raise ValueError("floor_fraction must lie in (0, 1]")
    measure = system.metadata["active_measure"].to_numpy(float)
    positive = measure[np.isfinite(measure) & (measure > 0.0)]
    if positive.size == 0:
        raise ValueError("active_measure has no positive finite values")
    floor = max(1e-12, floor_fraction * float(np.median(positive)))
    divisor = np.maximum(measure, floor)
    scale = 1.0 / divisor
    metadata = system.metadata.copy()
    metadata["active_measure_floor"] = floor
    metadata["active_measure_row_scale"] = scale
    return WeakSystem(
        A=system.A * scale[:, None],
        b=system.b * scale,
        term_names=system.term_names,
        metadata=metadata,
    )


def _standardized_matrix(A: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    scale = np.linalg.norm(A, axis=0)
    scale = np.where(scale > 1e-14, scale, 1.0)
    return A / scale, scale


def _max_abs_correlation(A: np.ndarray) -> float:
    standardized, _ = _standardized_matrix(A)
    centered = standardized - np.mean(standardized, axis=0, keepdims=True)
    norms = np.sqrt(np.sum(np.square(centered), axis=0))
    covariance = np.einsum("ni,nj->ij", centered, centered, optimize=False)
    denominator = norms[:, None] * norms[None, :]
    correlation = np.divide(
        covariance,
        denominator,
        out=np.zeros_like(covariance),
        where=denominator > 1e-14,
    )
    np.fill_diagonal(correlation, 0.0)
    return float(np.max(np.abs(correlation)))


def _condition_and_rank(A: np.ndarray) -> tuple[float, int]:
    standardized, _ = _standardized_matrix(A)
    singular = np.linalg.svd(standardized, compute_uv=False)
    if singular.size == 0 or singular[0] <= 0.0:
        return float("inf"), 0
    rank = int(np.sum(singular > singular[0] * 1e-8))
    condition = float(singular[0] / max(singular[-1], np.finfo(float).eps))
    return condition, rank


def balanced_stack(systems: list[WeakSystem]) -> WeakSystem:
    if not systems:
        raise ValueError("at least one environment is required")
    terms = systems[0].term_names
    if any(system.term_names != terms for system in systems):
        raise ValueError("all environments must use the same ordered terms")
    blocks_A: list[np.ndarray] = []
    blocks_b: list[np.ndarray] = []
    metadata: list[pd.DataFrame] = []
    for environment, system in enumerate(systems):
        if system.A.shape[0] == 0:
            raise ValueError("empty weak environment")
        weight = 1.0 / np.sqrt(float(system.A.shape[0]))
        blocks_A.append(system.A * weight)
        blocks_b.append(system.b * weight)
        meta = system.metadata.copy()
        meta["environment_index"] = environment
        metadata.append(meta)
    return WeakSystem(
        A=np.vstack(blocks_A),
        b=np.concatenate(blocks_b),
        term_names=terms,
        metadata=pd.concat(metadata, ignore_index=True),
    )


def library_diagnostics(systems: list[WeakSystem]) -> LibraryDiagnostics:
    stacked = balanced_stack(systems)
    condition, rank = _condition_and_rank(stacked.A)
    per_corr = tuple(_max_abs_correlation(system.A) for system in systems)
    per_condition = tuple(_condition_and_rank(system.A)[0] for system in systems)
    standardized, _ = _standardized_matrix(stacked.A)
    leverage = []
    env = stacked.metadata["environment_index"].to_numpy(int)
    total = float(np.square(standardized).sum())
    for environment in range(len(systems)):
        leverage.append(float(np.square(standardized[env == environment]).sum()) / total)
    return LibraryDiagnostics(
        max_abs_correlation=_max_abs_correlation(stacked.A),
        condition_number=condition,
        effective_rank=rank,
        max_environment_leverage=max(leverage),
        per_environment_max_abs_correlation=per_corr,
        per_environment_condition_number=per_condition,
    )


def forcing_correlation(frame: pd.DataFrame) -> float:
    grouped = frame.groupby(["trajectory_id", "cycle"], sort=True).agg(
        traffic=("traffic_esal_rate", "mean"),
        cold=("temperature", lambda values: max(0.0, 10.0 - float(np.mean(values)))),
        moisture=("moisture", "mean"),
    )
    correlation = grouped.corr().to_numpy(float)
    np.fill_diagonal(correlation, 0.0)
    return float(np.max(np.abs(correlation)))


def _ridge(A: np.ndarray, b: np.ndarray, columns: np.ndarray, l2: float = 1e-8) -> np.ndarray:
    beta = np.zeros(A.shape[1], dtype=float)
    if columns.size:
        selected = A[:, columns]
        gram = np.einsum("ni,nj->ij", selected, selected, optimize=False)
        rhs = np.einsum("ni,n->i", selected, b, optimize=False)
        beta[columns] = np.linalg.solve(gram + l2 * np.eye(columns.size), rhs)
    return beta


def _fit_scaled_stlsq(A: np.ndarray, b: np.ndarray, threshold: float) -> np.ndarray:
    scaled, scale = _standardized_matrix(A)
    beta_scaled = fit_stlsq(scaled, b, relative_threshold=threshold)
    return beta_scaled / scale


def _rmse(A: np.ndarray, b: np.ndarray, beta: np.ndarray) -> float:
    predicted = np.sum(A * beta[None, :], axis=1)
    return float(np.sqrt(np.mean(np.square(b - predicted))))


def shared_support_select(
    train_systems: list[WeakSystem],
    validation_system: WeakSystem,
    *,
    n_trials: int = 24,
    seed: int = 0,
    relative_threshold: float = 0.08,
    stable_frequency: float = 0.75,
    minimum_sign_consistency: float = 0.90,
    minimum_snr: float = 2.0,
    near_best_tolerance: float = 0.05,
) -> SharedSupportResult:
    stacked = balanced_stack(train_systems)
    if validation_system.term_names != stacked.term_names:
        raise ValueError("validation terms do not match training terms")
    rng = np.random.default_rng(seed)
    trial_beta = np.zeros((n_trials, stacked.A.shape[1]), dtype=float)
    for trial in range(n_trials):
        sampled_A: list[np.ndarray] = []
        sampled_b: list[np.ndarray] = []
        for system in train_systems:
            size = max(12, int(np.ceil(0.70 * system.A.shape[0])))
            idx = rng.choice(system.A.shape[0], size=size, replace=True)
            weight = 1.0 / np.sqrt(float(size))
            sampled_A.append(system.A[idx] * weight)
            sampled_b.append(system.b[idx] * weight)
        trial_beta[trial] = _fit_scaled_stlsq(
            np.vstack(sampled_A), np.concatenate(sampled_b), relative_threshold
        )
    active = np.abs(trial_beta) > 1e-12
    frequency = active.mean(axis=0)
    signs = np.sign(trial_beta)
    sign_consistency = np.zeros(stacked.A.shape[1], dtype=float)
    snr = np.zeros(stacked.A.shape[1], dtype=float)
    positive_environments = np.zeros(stacked.A.shape[1], dtype=int)
    for column in range(stacked.A.shape[1]):
        nonzero = trial_beta[active[:, column], column]
        if nonzero.size:
            sign_consistency[column] = max(
                np.mean(nonzero > 0.0), np.mean(nonzero < 0.0)
            )
            snr[column] = abs(float(np.median(nonzero))) / max(
                float(np.median(np.abs(nonzero - np.median(nonzero)))), 1e-12
            )
        for system in train_systems:
            null = _rmse(system.A, system.b, np.zeros(system.A.shape[1]))
            one = _ridge(system.A, system.b, np.array([column]))
            if _rmse(system.A, system.b, one) < null:
                positive_environments[column] += 1
    accepted = np.flatnonzero(
        (frequency >= stable_frequency)
        & (sign_consistency >= minimum_sign_consistency)
        & (snr >= minimum_snr)
        & (positive_environments >= min(3, len(train_systems)))
    )
    candidates: list[np.ndarray] = [np.array([], dtype=int)]
    for size in range(1, accepted.size + 1):
        candidates.extend(np.asarray(choice, dtype=int) for choice in combinations(accepted, size))
    trace_rows: list[dict[str, object]] = []
    fits: list[tuple[np.ndarray, np.ndarray, float]] = []
    for columns in candidates:
        beta = _ridge(stacked.A, stacked.b, columns)
        validation_rmse = _rmse(validation_system.A, validation_system.b, beta)
        fits.append((columns, beta, validation_rmse))
        trace_rows.append(
            {
                "support": ",".join(stacked.term_names[index] for index in columns),
                "support_size": int(columns.size),
                "validation_rmse": validation_rmse,
                "max_environment_rmse": max(
                    _rmse(system.A, system.b, beta) for system in train_systems
                ),
            }
        )
    best = min(value[2] for value in fits)
    eligible = [
        value for value in fits if value[2] <= best * (1.0 + near_best_tolerance)
    ]
    columns, beta, validation_rmse = min(
        eligible,
        key=lambda value: (
            value[0].size,
            max(_rmse(system.A, system.b, value[1]) for system in train_systems),
        ),
    )
    summary = pd.DataFrame(
        {
            "term": stacked.term_names,
            "frequency": frequency,
            "sign_consistency": sign_consistency,
            "robust_snr": snr,
            "positive_environment_count": positive_environments,
            "accepted_before_validation": [index in accepted for index in range(len(stacked.term_names))],
            "selected": [index in columns for index in range(len(stacked.term_names))],
        }
    )
    diagnostics = library_diagnostics(train_systems)
    return SharedSupportResult(
        support=tuple(stacked.term_names[index] for index in columns),
        coefficients=pd.Series(beta, index=stacked.term_names),
        support_summary=summary,
        trial_coefficients=pd.DataFrame(trial_beta, columns=stacked.term_names),
        validation_trace=pd.DataFrame(trace_rows),
        diagnostics=diagnostics,
        metrics={
            "validation_rmse": validation_rmse,
            "null_validation_rmse": _rmse(
                validation_system.A,
                validation_system.b,
                np.zeros(validation_system.A.shape[1]),
            ),
            "selected_support": list(tuple(stacked.term_names[index] for index in columns)),
            "n_train_environments": len(train_systems),
        },
    )
