#!/usr/bin/env python3
"""Observation-only probabilistic crack-growth baseline.

This model uses only registered crack-tip positions and inspection spacing. It
is a deliberately simple data baseline for the direct-FEM library, not a Paris
law and not a claim of physical mechanism closure.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from reality_assimilation import (
    Trajectory,
    empirical_crps,
    summarize_predictions,
    validate_physics_library,
    weighted_quantile,
)


def observed_positive_rates(trajectories: Sequence[Trajectory]) -> np.ndarray:
    rates: list[float] = []
    for trajectory in trajectories:
        rows = trajectory.rows.sort_values("cycle")
        cycles = rows["cycle"].to_numpy(float)
        tips = rows["crack_tip_x_d09"].to_numpy(float)
        valid = np.isfinite(cycles) & np.isfinite(tips)
        cycles = cycles[valid]
        tips = tips[valid]
        if len(cycles) < 2:
            continue
        dc = np.diff(cycles)
        da = np.diff(tips)
        local = da[dc > 0.0] / dc[dc > 0.0]
        rates.extend(local[np.isfinite(local) & (local > 0.0)].tolist())
        total_dc = cycles[-1] - cycles[0]
        total_da = tips[-1] - tips[0]
        if total_dc > 0.0 and total_da > 0.0:
            rates.append(float(total_da / total_dc))
    if not rates:
        raise ValueError("Observable growth baseline needs at least one positive crack-tip increment")
    return np.asarray(rates, dtype=float)


class SequentialObservableGrowthBaseline:
    """Tempered particle posterior over a local monotone crack-growth rate."""

    def __init__(
        self,
        library: Sequence[Trajectory],
        *,
        rate_particles: int = 101,
        tip_sigma: float = 0.002,
        process_relative_sigma: float = 0.35,
        forgetting: float = 0.5,
        min_rate: float = 1.0e-6,
        max_rul: float | None = None,
    ) -> None:
        validate_physics_library(library)
        if rate_particles < 21:
            raise ValueError("rate_particles must be at least 21")
        if tip_sigma <= 0.0 or process_relative_sigma < 0.0:
            raise ValueError("tip_sigma must be positive and process_relative_sigma non-negative")
        if not 0.0 <= forgetting <= 1.0:
            raise ValueError("forgetting must lie in [0, 1]")
        empirical = observed_positive_rates(library)
        low = max(float(min_rate), float(np.quantile(empirical, 0.05)) / 4.0)
        high = max(low * 10.0, float(np.quantile(empirical, 0.95)) * 4.0)
        self.rates = np.geomspace(low, high, int(rate_particles))
        log_rates = np.log(self.rates)
        empirical_log = np.log(np.maximum(empirical, low))
        centre = float(np.median(empirical_log))
        spread = max(float(np.std(empirical_log)), 0.5)
        self.log_weights = -0.5 * ((log_rates - centre) / spread) ** 2
        self.log_weights -= np.max(self.log_weights)
        terminal_tips = [
            float(t.rows["crack_tip_x_d09"].dropna().iloc[-1])
            for t in library
            if t.rows["crack_tip_x_d09"].notna().any()
        ]
        if not terminal_tips:
            raise ValueError("Observable growth baseline lacks terminal crack-tip observations")
        self.failure_tip_x = float(np.median(terminal_tips))
        self.tip_sigma = float(tip_sigma)
        self.process_relative_sigma = float(process_relative_sigma)
        self.forgetting = float(forgetting)
        self.max_rul = float(max_rul or 3.0 * max(t.terminal_cycle for t in library))
        self.previous_cycle: float | None = None
        self.previous_tip: float | None = None

    @property
    def weights(self) -> np.ndarray:
        shifted = self.log_weights - np.max(self.log_weights)
        weights = np.exp(shifted)
        return weights / np.sum(weights)

    def update(self, cycle: float, crack_tip_x: float) -> np.ndarray:
        cycle = float(cycle)
        crack_tip_x = float(crack_tip_x)
        if not (np.isfinite(cycle) and np.isfinite(crack_tip_x)):
            return self.weights.copy()
        if self.previous_cycle is None:
            self.previous_cycle = cycle
            self.previous_tip = crack_tip_x
            return self.weights.copy()
        dc = cycle - float(self.previous_cycle)
        if dc <= 0.0:
            raise ValueError("Inspection cycles must increase for observable growth updating")
        observed_increment = crack_tip_x - float(self.previous_tip)
        prior = np.maximum(self.weights, 1.0e-300) ** self.forgetting
        prior /= np.sum(prior)
        expected_increment = self.rates * dc
        sigma = np.sqrt(
            self.tip_sigma**2
            + (self.process_relative_sigma * np.maximum(expected_increment, self.tip_sigma)) ** 2
        )
        log_like = -0.5 * ((observed_increment - expected_increment) / sigma) ** 2 - np.log(sigma)
        self.log_weights = np.log(prior) + log_like
        self.log_weights -= np.max(self.log_weights)
        self.previous_cycle = cycle
        self.previous_tip = crack_tip_x
        return self.weights.copy()

    def posterior_prediction(self, current_tip: float, horizon: int) -> dict[str, object]:
        weights = self.weights
        distance = max(0.0, self.failure_tip_x - float(current_tip))
        if distance <= 0.0:
            rul = np.zeros_like(self.rates)
        else:
            rul = np.minimum(distance / self.rates, self.max_rul)
        future_tip = np.minimum(
            self.failure_tip_x,
            float(current_tip) + self.rates * int(horizon),
        )
        entropy = -float(np.sum(weights * np.log(np.maximum(weights, 1.0e-300))))
        return {
            "rul_mean": float(np.sum(weights * rul)),
            "rul_q05": weighted_quantile(rul, weights, 0.05),
            "rul_q50": weighted_quantile(rul, weights, 0.50),
            "rul_q95": weighted_quantile(rul, weights, 0.95),
            "future_tip_mean": float(np.sum(weights * future_tip)),
            "future_tip_q05": weighted_quantile(future_tip, weights, 0.05),
            "future_tip_q95": weighted_quantile(future_tip, weights, 0.95),
            "posterior_entropy": entropy,
            "effective_models": float(np.exp(entropy)),
            "rul_crps_support": rul,
            "rul_crps_weights": weights,
            "max_particle_weight": float(np.max(weights)),
            "failure_tip_x": self.failure_tip_x,
        }


def assimilate_observable_growth_holdout(
    holdout: Trajectory,
    library: Sequence[Trajectory],
    *,
    inspection_stride: int = 5,
    forecast_horizon: int = 5,
    rate_particles: int = 101,
    tip_sigma: float = 0.002,
    process_relative_sigma: float = 0.35,
    forgetting: float = 0.5,
) -> pd.DataFrame:
    if holdout.censored:
        raise ValueError("Censored holdout has no exact RUL truth")
    model = SequentialObservableGrowthBaseline(
        library,
        rate_particles=rate_particles,
        tip_sigma=tip_sigma,
        process_relative_sigma=process_relative_sigma,
        forgetting=forgetting,
    )
    source_rows = holdout.rows.iloc[:: max(1, int(inspection_stride))].copy()
    if source_rows.index[-1] != holdout.rows.index[-1]:
        source_rows = pd.concat([source_rows, holdout.rows.iloc[[-1]]])
    output: list[dict[str, float | str]] = []
    for _, row in source_rows.iterrows():
        cycle = float(row["cycle"])
        tip = float(row["crack_tip_x_d09"])
        weights = model.update(cycle, tip)
        pred = model.posterior_prediction(tip, forecast_horizon)
        true_rul = float(row["remaining_life"])
        true_future_tip = float(holdout.future_row(cycle, forecast_horizon)["crack_tip_x_d09"])
        output.append(
            {
                "transition_model": "observable_growth_particles",
                "tier": "observable_tip_growth",
                "heldout_trajectory": holdout.trajectory_id,
                "cycle": cycle,
                "observed_crack_tip_x": tip,
                "true_rul": true_rul,
                "rul_mean": pred["rul_mean"],
                "rul_q05": pred["rul_q05"],
                "rul_q50": pred["rul_q50"],
                "rul_q95": pred["rul_q95"],
                "rul_crps": empirical_crps(
                    np.asarray(pred["rul_crps_support"], dtype=float),
                    np.asarray(pred["rul_crps_weights"], dtype=float),
                    true_rul,
                ),
                "rul_interval_covers": float(pred["rul_q05"] <= true_rul <= pred["rul_q95"]),
                "true_future_tip": true_future_tip,
                "future_tip_mean": pred["future_tip_mean"],
                "future_tip_q05": pred["future_tip_q05"],
                "future_tip_q95": pred["future_tip_q95"],
                "posterior_entropy": pred["posterior_entropy"],
                "effective_models": pred["effective_models"],
                "max_model_weight": float(np.max(weights)),
                "censored_posterior_mass": 0.0,
                "censor_tail_scale": float("nan"),
                "failure_tip_x": pred["failure_tip_x"],
            }
        )
    return pd.DataFrame(output)


def summarize_observable_growth_stages(predictions: pd.DataFrame) -> pd.DataFrame:
    """Separate the initiation-blind phase from detected surface propagation."""
    stages = np.where(
        predictions["observed_crack_tip_x"].to_numpy(float) > 0.0,
        "detected_extension",
        "no_detected_extension",
    )
    work = predictions.copy()
    work["observation_stage"] = stages
    rows = []
    for stage, frame in work.groupby("observation_stage", sort=False):
        rul_error = frame["rul_mean"].to_numpy(float) - frame["true_rul"].to_numpy(float)
        tip_error = frame["future_tip_mean"].to_numpy(float) - frame["true_future_tip"].to_numpy(float)
        rows.append(
            {
                "observation_stage": stage,
                "n_updates": float(len(frame)),
                "rul_mae": float(np.mean(np.abs(rul_error))),
                "rul_rmse": float(np.sqrt(np.mean(rul_error**2))),
                "rul_crps": float(frame["rul_crps"].mean()),
                "rul_90_coverage": float(frame["rul_interval_covers"].mean()),
                "rul_90_width": float((frame["rul_q95"] - frame["rul_q05"]).mean()),
                "future_tip_mae": float(np.mean(np.abs(tip_error))),
            }
        )
    return pd.DataFrame(rows)


def run_observable_growth_leave_one_out(
    trajectories: Sequence[Trajectory],
    *,
    inspection_stride: int = 5,
    forecast_horizon: int = 5,
    rate_particles: int = 101,
    tip_sigma: float = 0.002,
    process_relative_sigma: float = 0.35,
    forgetting: float = 0.5,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    validate_physics_library(trajectories)
    if len(trajectories) < 3:
        raise ValueError("Observable growth leave-one-out needs at least three trajectories")
    frames = []
    for holdout in (trajectory for trajectory in trajectories if not trajectory.censored):
        library = [t for t in trajectories if t.trajectory_id != holdout.trajectory_id]
        frames.append(
            assimilate_observable_growth_holdout(
                holdout,
                library,
                inspection_stride=inspection_stride,
                forecast_horizon=forecast_horizon,
                rate_particles=rate_particles,
                tip_sigma=tip_sigma,
                process_relative_sigma=process_relative_sigma,
                forgetting=forgetting,
            )
        )
    predictions = pd.concat(frames, ignore_index=True)
    return predictions, summarize_predictions(predictions)
