"""Road-facing time and inspection-trigger utilities for fracture forecasts.

The module deliberately separates deployable trigger inputs from FEM-only audit
metrics.  It does not map one FEM cycle to one axle passage or to calendar time.
That mapping requires a calibrated traffic/environment exposure model.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

import numpy as np


STATE_NAMES = ("damage", "fatigue_history", "fatigue_degradation", "log10_psi_raw")
TRIGGER_SIGNALS = (
    "active_log_ensemble_std",
    "raw_log_ensemble_std",
    "damage_ensemble_std",
    "support_fraction_std",
    "support_log_distance_from_origin",
    "active_log_step_change",
    "raw_log_step_change",
    "damage_step_change",
    "top1_centroid_step",
)


def normalized_weights(weights: np.ndarray) -> np.ndarray:
    values = np.asarray(weights, dtype=np.float64).reshape(-1)
    if values.size == 0 or not np.all(np.isfinite(values)) or np.any(values < 0):
        raise ValueError("weights must be finite, non-negative, and non-empty")
    total = float(values.sum())
    if total <= 0:
        raise ValueError("weights must have positive total")
    return values / total


def weighted_quantile(values: np.ndarray, weights: np.ndarray, quantile: float) -> float:
    if not 0.0 <= quantile <= 1.0:
        raise ValueError("quantile must lie in [0, 1]")
    values = np.asarray(values, dtype=np.float64).reshape(-1)
    weights = normalized_weights(weights)
    if values.shape != weights.shape or not np.all(np.isfinite(values)):
        raise ValueError("values and weights must be finite vectors of equal length")
    order = np.argsort(values, kind="mergesort")
    cumulative = np.cumsum(weights[order])
    index = int(np.searchsorted(cumulative, quantile, side="left"))
    return float(values[order[min(index, len(order) - 1)]])


def derived_active_log10(state: np.ndarray, floor: float = 1.0e-12) -> np.ndarray:
    state = np.asarray(state, dtype=np.float64)
    if state.shape[-1] != 4:
        raise ValueError("state must end with four channels")
    damage = np.clip(state[..., 0], 0.0, 1.0)
    log_g = 2.0 * np.log10(np.maximum(1.0 - damage, floor))
    return np.maximum(state[..., 3] + log_g, np.log10(floor))


def top_fraction_centroid(
    log_field: np.ndarray,
    coordinates: np.ndarray,
    areas: np.ndarray,
    fraction: float = 0.01,
) -> np.ndarray:
    threshold = weighted_quantile(log_field, areas, 1.0 - fraction)
    mask = np.asarray(log_field) >= threshold
    weights = np.asarray(areas, dtype=np.float64)[mask]
    if not np.any(mask) or float(weights.sum()) <= 0:
        return np.full(2, np.nan)
    return np.sum(np.asarray(coordinates, dtype=np.float64)[mask] * weights[:, None], axis=0) / weights.sum()


def _weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    return float(np.sum(np.asarray(values, dtype=np.float64) * normalized_weights(weights)))


def _support_fraction(log_field: np.ndarray, threshold: float, weights: np.ndarray) -> float:
    return _weighted_mean(np.asarray(log_field) >= threshold, weights)


def _centroid_spread(centroids: np.ndarray) -> float:
    centroids = np.asarray(centroids, dtype=np.float64)
    centre = np.nanmean(centroids, axis=0)
    return float(np.nanmean(np.linalg.norm(centroids - centre, axis=1)))


def _absolute_support_audit(
    prediction_active: np.ndarray,
    fem_active: np.ndarray,
    areas: np.ndarray,
) -> tuple[float, float, float]:
    threshold = weighted_quantile(fem_active, areas, 0.99)
    fem_mask = fem_active >= threshold
    pred_mask = prediction_active >= threshold
    weights = np.asarray(areas, dtype=np.float64)
    intersection = float(weights[fem_mask & pred_mask].sum())
    union = float(weights[fem_mask | pred_mask].sum())
    fem_area = float(weights[fem_mask].sum())
    pred_area = float(weights[pred_mask].sum())
    iou = intersection / union if union > 0 else 1.0
    ratio = pred_area / fem_area if fem_area > 0 else float("nan")
    mae = _weighted_mean(np.abs(prediction_active - fem_active), weights)
    return iou, ratio, mae


def compute_trigger_trajectory(
    cycles: np.ndarray,
    predictions: np.ndarray,
    fem_states: np.ndarray,
    coordinates: np.ndarray,
    areas: np.ndarray,
    *,
    family: str,
) -> list[dict[str, float | int | str | bool]]:
    """Compute model-only signals and separately labelled FEM audit metrics.

    ``predictions`` is ``[ensemble, cycle, element, channel]``.  Trigger
    decisions must use only columns without the ``audit_only_`` prefix.
    """
    cycles = np.asarray(cycles, dtype=int)
    predictions = np.asarray(predictions, dtype=np.float64)
    if predictions.ndim != 4 or predictions.shape[1] != len(cycles):
        raise ValueError("predictions must have shape [ensemble, cycle, element, 4]")
    if predictions.shape[-1] != 4 or predictions.shape[2] != len(areas):
        raise ValueError("prediction state or element dimension mismatch")
    if np.asarray(fem_states).shape != predictions.shape[1:]:
        raise ValueError("fem_states must match [cycle, element, channel]")

    weights = normalized_weights(areas)
    active = derived_active_log10(predictions)
    mean_state = predictions.mean(axis=0)
    mean_active = active.mean(axis=0)
    origin_threshold = weighted_quantile(mean_active[0], areas, 0.99)
    origin_fraction = _support_fraction(mean_active[0], origin_threshold, weights)
    previous_active = mean_active[0]
    previous_state = mean_state[0]
    previous_centroid = top_fraction_centroid(previous_active, coordinates, areas)
    rows: list[dict[str, float | int | str | bool]] = []

    for index, cycle in enumerate(cycles):
        active_std = np.std(active[:, index], axis=0, ddof=0)
        state_std = np.std(predictions[:, index], axis=0, ddof=0)
        seed_support = np.array([
            _support_fraction(field, origin_threshold, weights)
            for field in active[:, index]
        ])
        centroids = np.stack([
            top_fraction_centroid(field, coordinates, areas)
            for field in active[:, index]
        ])
        centroid = top_fraction_centroid(mean_active[index], coordinates, areas)
        support_fraction = _support_fraction(mean_active[index], origin_threshold, weights)
        support_ratio = support_fraction / max(origin_fraction, np.finfo(float).eps)

        if index == 0:
            active_step = raw_step = damage_step = centroid_step = 0.0
        else:
            active_step = _weighted_mean(np.abs(mean_active[index] - previous_active), weights)
            raw_step = _weighted_mean(np.abs(mean_state[index, :, 3] - previous_state[:, 3]), weights)
            damage_step = _weighted_mean(np.maximum(mean_state[index, :, 0] - previous_state[:, 0], 0.0), weights)
            centroid_step = float(np.linalg.norm(centroid - previous_centroid))

        fem_active = derived_active_log10(np.asarray(fem_states[index]))
        audit_iou, audit_ratio, audit_mae = _absolute_support_audit(
            mean_active[index], fem_active, areas
        )
        row: dict[str, float | int | str | bool] = {
            "family": family,
            "cycle": int(cycle),
            "ensemble_size": int(predictions.shape[0]),
            "active_log_ensemble_std": _weighted_mean(active_std, weights),
            "raw_log_ensemble_std": _weighted_mean(state_std[:, 3], weights),
            "damage_ensemble_std": _weighted_mean(state_std[:, 0], weights),
            "support_fraction_mean": float(seed_support.mean()),
            "support_fraction_std": float(seed_support.std(ddof=0)),
            "support_area_ratio_to_origin": support_ratio,
            "support_log_distance_from_origin": abs(float(np.log(max(support_ratio, 1.0e-12)))),
            "top1_centroid_spread": _centroid_spread(centroids),
            "top1_centroid_step": centroid_step,
            "active_log_step_change": active_step,
            "raw_log_step_change": raw_step,
            "damage_step_change": damage_step,
            "audit_only_fem_absolute_p99_iou": audit_iou,
            "audit_only_fem_support_area_ratio": audit_ratio,
            "audit_only_fem_active_log_mae": audit_mae,
            "audit_only_support_gate_failed": bool(audit_iou < 0.50),
        }
        rows.append(row)
        previous_active = mean_active[index]
        previous_state = mean_state[index]
        previous_centroid = centroid
    return rows


@dataclass(frozen=True)
class SignalEnvelope:
    centre: float
    scale: float
    warn_z: float = 3.0
    hard_z: float = 5.0


def fit_signal_envelopes(
    rows: Iterable[Mapping[str, object]],
    calibration_cycles: Iterable[int],
) -> dict[str, SignalEnvelope]:
    selected = [row for row in rows if int(row["cycle"]) in set(calibration_cycles)]
    if len(selected) < 3:
        raise ValueError("at least three predeclared calibration cycles are required")
    envelopes: dict[str, SignalEnvelope] = {}
    for signal in TRIGGER_SIGNALS:
        values = np.asarray([float(row[signal]) for row in selected], dtype=np.float64)
        centre = float(np.median(values))
        mad = float(np.median(np.abs(values - centre)))
        scale = max(1.4826 * mad, 0.05 * abs(centre), 1.0e-8)
        envelopes[signal] = SignalEnvelope(centre=centre, scale=scale)
    return envelopes


def apply_trigger_rule(
    rows: list[dict[str, object]],
    envelopes: Mapping[str, SignalEnvelope],
    calibration_cycles: Iterable[int],
) -> list[dict[str, object]]:
    """Apply a candidate rule using only model-derived signal columns."""
    calibration = set(int(cycle) for cycle in calibration_cycles)
    consecutive_warning = 0
    for row in rows:
        z_values: dict[str, float] = {}
        for signal, envelope in envelopes.items():
            value = float(row[signal])
            z_values[signal] = max(0.0, (value - envelope.centre) / envelope.scale)
            row[f"z_{signal}"] = z_values[signal]
        warn_count = sum(value >= 3.0 for value in z_values.values())
        hard_count = sum(value >= 5.0 for value in z_values.values())
        risk_score = max(z_values.values(), default=0.0)
        candidate_warning = hard_count >= 1 or warn_count >= 2
        if int(row["cycle"]) in calibration:
            candidate_warning = False
            consecutive_warning = 0
        else:
            consecutive_warning = consecutive_warning + 1 if candidate_warning else 0
        row["trigger_risk_score"] = risk_score
        row["trigger_warn_signal_count"] = warn_count
        row["trigger_hard_signal_count"] = hard_count
        row["candidate_request_inspection"] = bool(candidate_warning)
        row["candidate_stop_recursive"] = bool(hard_count >= 2 or consecutive_warning >= 2)
        row["trigger_status"] = "diagnostic_only_single_trajectory"
    return rows


def road_time_mapping_spec() -> dict[str, object]:
    return {
        "schema": "road_time_mapping_v1",
        "status": "interface_only_uncalibrated",
        "prohibited_equivalences": [
            "FEM fatigue cycle != axle passage",
            "FEM fatigue cycle != ESAL",
            "FEM fatigue cycle != calendar interval",
            "inspection epoch != model integration step",
        ],
        "time_axes": {
            "fem_fatigue_cycle": "Numerical state update under one declared benchmark loading protocol; simulation-only index.",
            "axle_cycle": "Observed axle or axle-group passage from WIM/traffic records.",
            "equivalent_load_index": "Cumulative calibrated traffic-damage exposure; ESAL is one possible convention, not a universal state clock.",
            "load_block": "Forecast integration interval containing a declared axle spectrum and environment history.",
            "calendar_time": "UTC or local civil time used for ageing, weather, drainage, and inspection scheduling.",
            "inspection_epoch": "Time at which image, FWD, strain, or other observations update the latent state.",
        },
        "required_road_inputs": {
            "timestamp": {"type": "datetime", "units": "ISO-8601 UTC"},
            "cumulative_equivalent_load": {"type": "float", "units": "calibrated ESAL or exposure index"},
            "axle_spectrum": {"type": "array", "units": "counts by axle/load bin"},
            "load_distribution": {"type": "array", "units": "declared force or strain proxy bins"},
            "temperature": {"type": "series", "units": "degC"},
            "moisture": {"type": "series", "units": "declared volumetric or proxy scale"},
            "distance_from_last_inspection": {"type": "float", "units": "calendar time and equivalent load"},
            "maintenance_history": {"type": "events", "units": "typed intervention records"},
        },
        "recommended_step": {
            "name": "calibrated_equivalent_load_block_with_caps",
            "definition": "Close a block at a calibrated exposure increment, a maximum calendar duration, a material environment shift, an inspection, or maintenance, whichever occurs first.",
            "why_not_fixed_calendar_only": "Traffic and environmental exposure can differ materially between equal calendar intervals.",
            "why_not_fixed_esal_only": "Ageing, moisture, temperature, and maintenance are not represented by traffic count alone.",
            "fallback_without_wim": "Use inspection-to-inspection epochs and do not claim sub-inspection field timing.",
        },
        "selection_rule": {
            "development_only": "Compare candidate block definitions on physically diverse training trajectories.",
            "tests": [
                "h1-h3 field/support gate at identical observed origins",
                "stability when each block is subdivided",
                "no hidden maintenance or observation event inside a block",
                "calibrated uncertainty under load/environment shift",
            ],
            "choose": "The simplest block definition passing all tests without future failure information.",
        },
        "current_benchmark": {
            "available": ["FEM fatigue cycle", "one fixed loading/material trajectory"],
            "missing": ["WIM/axle spectrum", "ESAL calibration", "calendar timestamps", "temperature", "moisture", "maintenance"],
            "mapping_claim": "No road-time conversion is supported by the current c1-c89 trajectory.",
        },
        "leakage_prohibitions": ["cycle/89", "known failure cycle", "cycle-to-failure", "future load or observation not available at forecast issue time"],
    }


def road_forecast_horizon_spec() -> dict[str, object]:
    return {
        "schema": "road_forecast_horizon_v1",
        "status": "road_interface_with_single_trajectory_diagnostic_evidence",
        "short_horizon": {
            "definition": "Predict latent/field state for the next one to three calibrated load blocks after an assimilated inspection state.",
            "outputs": ["state ensemble", "crack geometry distribution", "active-support diagnostic", "observation predictions", "uncertainty"],
            "evidence": "Matched FEM operators support same-regime h1-h3 conditional propagation on one trajectory only.",
        },
        "long_horizon": {
            "definition": "Predict scenario-conditioned threshold-crossing probability, event hazard, and RUL distribution.",
            "required_conditioning": ["future traffic scenarios", "temperature/moisture scenarios", "maintenance policy", "transition-model uncertainty"],
            "preferred_methods": ["direct multi-horizon distribution", "hazard/survival head", "particle or scenario ensemble"],
            "not_allowed_as_primary": "Unlimited deterministic recursion of one short-horizon field operator.",
            "survival_identity": "S(h)=product_{j=1..h}(1-hazard_j); RUL is derived from the scenario-conditioned survival distribution.",
        },
        "rolling_operation": [
            "assimilate observations at t_n",
            "forecast h1-h3 load blocks",
            "propagate scenario and model uncertainty",
            "evaluate trigger before each next block",
            "request inspection or stop recursion when trigger fires",
            "update latent state and RUL posterior after inspection",
        ],
        "stop_recursive_when": [
            "hard observation innovation or data-quality gate",
            "two consecutive model-uncertainty warnings",
            "traffic/environment outside calibrated support",
            "inspection overdue under the declared risk policy",
            "maintenance changes the state semantics",
        ],
        "evaluation_tasks": {
            "conditional_short_horizon": "multi-origin observed-state h1-h3",
            "autonomous_transition": "sealed stress test only",
            "post_transition": "same assimilated transition state for every model",
            "road_generalization": "leave-one-trajectory/load/road-section-out; not currently available",
        },
        "agent1_assimilation_contract": {
            "observation_spec_file": "road_observation_operator_spec.json",
            "required_state_arrays": ["state_mean", "state_ensemble_or_covariance", "coordinates", "areas", "observation_mask"],
            "required_metadata": ["timestamp", "equivalent_load_index", "coordinate_frame", "registration_id", "source_hashes", "uncertainty_semantics"],
            "state_channels": list(STATE_NAMES),
        },
    }


def observation_trigger_spec(
    calibration_cycles: Iterable[int],
    envelopes: Mapping[str, SignalEnvelope],
) -> dict[str, object]:
    return {
        "schema": "road_observation_trigger_v1",
        "status": "candidate_diagnostic_not_road_validated",
        "decision_inputs": {
            "model_internal": [
                "ensemble disagreement",
                "latent/support uncertainty",
                "predicted support and crack-growth drift",
            ],
            "observation_innovation": [
                "predicted-versus-measured crack geometry",
                "predicted-versus-measured FWD deflection basin",
                "predicted-versus-measured strain localization",
            ],
            "exogenous_ood": ["axle/load spectrum", "temperature", "moisture", "maintenance"],
            "data_quality": ["missingness", "registration uncertainty", "sensor drift"],
        },
        "agent1_interface": {
            "read": "road_observation_operator_spec.json",
            "assimilated_state": "Agent1 must provide a common state mean and uncertainty object to every forecast model.",
            "innovation_channels": ["image", "FWD", "strain"],
            "missing_channel_policy": "missing channels are NA, never zero; a model-only trigger cannot be presented as observation validation.",
        },
        "current_offline_rule": {
            "calibration_cycles": [int(cycle) for cycle in calibration_cycles],
            "selection_firewall": "Signal centres/scales are frozen from these predeclared cycles before c80-c89 audit.",
            "warning": "at least two signals at z>=3 or one signal at z>=5",
            "stop_recursive": "at least two signals at z>=5 or two consecutive candidate warnings",
            "limitations": "Three calibration cycles from one trajectory are insufficient for an operational threshold.",
            "envelopes": {
                name: {"centre": value.centre, "scale": value.scale, "warn_z": value.warn_z, "hard_z": value.hard_z}
                for name, value in envelopes.items()
            },
        },
        "operational_promotion_rule": {
            "calibration": "Freeze thresholds on physically independent non-event trajectories.",
            "validation": ["false inspection rate", "missed transition rate", "lead time", "cost-weighted utility", "uncertainty coverage"],
            "request_inspection": "one model warning plus one observation/OOD warning, or a predeclared hard safety gate",
            "road_sensors": ["registered image", "FWD", "strain", "WIM/load", "temperature/moisture"],
        },
        "audit_columns_prohibited_from_decision": [
            "audit_only_fem_absolute_p99_iou",
            "audit_only_fem_support_area_ratio",
            "audit_only_fem_active_log_mae",
            "audit_only_support_gate_failed",
        ],
    }
