"""Observation-innovation packets and leakage-safe road trigger decisions.

The runtime decision surface accepts only model diagnostics, declared
observation innovations, exogenous OOD flags, and operational data-quality
flags. FEM fields and audit metrics belong to a separate post-hoc join.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

import numpy as np


CHANNELS = (
    "registered_crack_geometry_image",
    "fwd_deflection_basin",
    "strain_localization",
)
EVIDENCE_CLASSES = {"real_observation", "synthetic_sensor", "oracle_derived_proxy"}
RUNTIME_KEYS = {
    "integration_step_index",
    "model_warning",
    "model_stop",
    "observation_warning_count",
    "observation_hard_count",
    "max_observation_z",
    "traffic_environment_ood_warning",
    "traffic_environment_ood_hard",
    "data_quality_warning",
    "data_quality_hard",
    "inspection_overdue",
    "maintenance_event",
}
PROHIBITED_RUNTIME_FRAGMENTS = (
    "audit",
    "fem",
    "ground_truth",
    "target_cycle",
    "failure_cycle",
    "cycle_to_failure",
    "known_failure",
)


@dataclass(frozen=True)
class InnovationEnvelope:
    centre: float
    scale: float
    warn_z: float = 3.0
    hard_z: float = 5.0


def observation_innovation_packet_spec() -> dict[str, object]:
    channel_contract = {
        "required": [
            "feature_names",
            "values",
            "predicted_values",
            "mask",
            "uncertainty",
            "provenance",
            "registration",
            "time",
        ],
        "values": "Observed feature vector in declared physical or normalized units.",
        "predicted_values": "Observation-operator prediction at the same registration and time.",
        "mask": "Boolean feature mask; missing is false and never interpreted as zero evidence.",
        "uncertainty": {
            "observation_std": "Positive finite standard deviation for observed features, null when masked.",
            "prediction_std": "Positive finite ensemble/operator standard deviation, null when masked.",
            "semantics": "Must state whether calibrated, diagnostic floor, or unavailable.",
        },
        "provenance": {
            "evidence_class": sorted(EVIDENCE_CLASSES),
            "source_id": "Immutable observation asset or synthetic operator identifier.",
            "observation_operator_id": "Versioned H mapping latent state to this observation.",
            "source_hashes": "SHA-256 map for source assets.",
            "real_road_compatible": "False for synthetic/oracle-derived diagnostics.",
        },
        "registration": {
            "coordinate_frame_id": "Road/mesh/image coordinate frame.",
            "registration_id": "Versioned transform or survey registration.",
            "quality_score": "Optional [0,1] quality score.",
            "uncertainty": "Registration uncertainty in declared units.",
        },
        "time": {
            "timestamp": "ISO-8601 for real observations; null only for declared synthetic diagnostics.",
            "equivalent_load_index": "Calibrated exposure index or null when unavailable.",
            "inspection_epoch_id": "Stable observation visit identifier.",
            "integration_step_index": "Ordering index, never a cycle-to-failure feature.",
        },
    }
    return {
        "schema_version": "observation_innovation_packet_v1",
        "status": "provisional_reality_facing_interface",
        "required_top_level": ["packet_id", "time", "channels", "operational_context"],
        "channels": {name: channel_contract for name in CHANNELS},
        "operational_context": {
            "traffic_environment_ood": ["warning", "hard", "score", "provenance"],
            "data_quality": ["warning", "hard", "missing_fraction", "sensor_drift", "registration_failure"],
            "inspection_overdue": "Boolean from a declared inspection policy.",
            "maintenance_event": "Boolean; true changes state semantics and forces reassimilation.",
        },
        "agent_contract_alignment": {
            "agent1": "road_observation_operator_v1 and road_assimilated_state_v1",
            "agent3": "road_forecast_input_contract_v1 node/global observations and known history",
        },
        "hard_rules": [
            "FEM audit metrics are never packet decision features",
            "hidden phase-field fields are not relabelled as road measurements",
            "missing channels use mask=false and are never zero evidence",
            "synthetic/oracle-derived packets are not real-road validation",
        ],
    }


def _numeric_vector(value: object, *, name: str) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64).reshape(-1)
    if array.ndim != 1:
        raise ValueError(f"{name} must be a vector")
    return array


def validate_observation_innovation_packet(packet: Mapping[str, object]) -> None:
    if packet.get("schema_version") != "observation_innovation_packet_v1":
        raise ValueError("unsupported observation innovation packet schema")
    channels = packet.get("channels")
    if not isinstance(channels, Mapping) or set(channels) != set(CHANNELS):
        raise ValueError("packet must declare exactly the three frozen channels")
    for name in CHANNELS:
        channel = channels[name]
        if not isinstance(channel, Mapping):
            raise ValueError(f"{name} must be an object")
        required = {
            "feature_names", "values", "predicted_values", "mask", "uncertainty",
            "provenance", "registration", "time",
        }
        if not required.issubset(channel):
            raise ValueError(f"{name} lacks required packet fields")
        feature_names = list(channel["feature_names"])
        values = _numeric_vector(channel["values"], name=f"{name}.values")
        predicted = _numeric_vector(channel["predicted_values"], name=f"{name}.predicted_values")
        mask = np.asarray(channel["mask"], dtype=bool).reshape(-1)
        uncertainty = channel["uncertainty"]
        if not isinstance(uncertainty, Mapping):
            raise ValueError(f"{name}.uncertainty must be an object")
        observation_std = _numeric_vector(uncertainty["observation_std"], name=f"{name}.observation_std")
        prediction_std = _numeric_vector(uncertainty["prediction_std"], name=f"{name}.prediction_std")
        lengths = {len(feature_names), len(values), len(predicted), len(mask), len(observation_std), len(prediction_std)}
        if len(lengths) != 1:
            raise ValueError(f"{name} feature arrays have inconsistent lengths")
        if np.any(mask):
            finite = np.isfinite(values[mask]) & np.isfinite(predicted[mask])
            positive = (observation_std[mask] > 0) & (prediction_std[mask] >= 0)
            if not np.all(finite & np.isfinite(observation_std[mask]) & np.isfinite(prediction_std[mask]) & positive):
                raise ValueError(f"{name} observed features require finite values and valid uncertainty")
        provenance = channel["provenance"]
        if not isinstance(provenance, Mapping) or provenance.get("evidence_class") not in EVIDENCE_CLASSES:
            raise ValueError(f"{name} has invalid evidence class")
        if provenance.get("evidence_class") != "real_observation" and provenance.get("real_road_compatible") is not False:
            raise ValueError(f"{name} synthetic/oracle provenance must set real_road_compatible=false")
        if not isinstance(channel["registration"], Mapping) or not isinstance(channel["time"], Mapping):
            raise ValueError(f"{name} registration and time must be objects")
    if not isinstance(packet.get("operational_context"), Mapping):
        raise ValueError("packet lacks operational context")


def normalized_feature_residuals(packet: Mapping[str, object]) -> dict[str, float]:
    validate_observation_innovation_packet(packet)
    result: dict[str, float] = {}
    for channel_name in CHANNELS:
        channel = packet["channels"][channel_name]
        values = np.asarray(channel["values"], dtype=np.float64)
        predicted = np.asarray(channel["predicted_values"], dtype=np.float64)
        mask = np.asarray(channel["mask"], dtype=bool)
        obs_std = np.asarray(channel["uncertainty"]["observation_std"], dtype=np.float64)
        pred_std = np.asarray(channel["uncertainty"]["prediction_std"], dtype=np.float64)
        denominator = np.sqrt(obs_std**2 + pred_std**2)
        for index, feature_name in enumerate(channel["feature_names"]):
            if bool(mask[index]):
                result[f"{channel_name}.{feature_name}"] = float(
                    abs(values[index] - predicted[index]) / denominator[index]
                )
    return result


def fit_innovation_envelopes(
    packets: Iterable[Mapping[str, object]],
    calibration_steps: Iterable[int],
) -> dict[str, InnovationEnvelope]:
    calibration = set(int(step) for step in calibration_steps)
    selected = [
        packet for packet in packets
        if int(packet["time"]["integration_step_index"]) in calibration
    ]
    if len(selected) < 3:
        raise ValueError("at least three frozen calibration packets are required")
    residuals = [normalized_feature_residuals(packet) for packet in selected]
    feature_names = set(residuals[0])
    if any(set(item) != feature_names for item in residuals):
        raise ValueError("calibration packets must share one observed feature mask")
    envelopes: dict[str, InnovationEnvelope] = {}
    for feature_name in sorted(feature_names):
        values = np.asarray([item[feature_name] for item in residuals], dtype=np.float64)
        centre = float(np.median(values))
        mad = float(np.median(np.abs(values - centre)))
        scale = max(1.4826 * mad, 0.05 * abs(centre), 1.0e-6)
        envelopes[feature_name] = InnovationEnvelope(centre=centre, scale=scale)
    return envelopes


def score_observation_packet(
    packet: Mapping[str, object],
    envelopes: Mapping[str, InnovationEnvelope],
) -> dict[str, object]:
    residuals = normalized_feature_residuals(packet)
    unknown = set(residuals) - set(envelopes)
    if unknown:
        raise ValueError(f"packet contains uncalibrated observed features: {sorted(unknown)}")
    channel_scores: dict[str, float] = {name: 0.0 for name in CHANNELS}
    feature_scores: dict[str, float] = {}
    for feature_name, residual in residuals.items():
        envelope = envelopes[feature_name]
        z = max(0.0, (residual - envelope.centre) / envelope.scale)
        feature_scores[feature_name] = z
        channel_name = feature_name.split(".", 1)[0]
        channel_scores[channel_name] = max(channel_scores[channel_name], z)
    observed_channels = {
        name for name in CHANNELS
        if any(key.startswith(f"{name}.") for key in residuals)
    }
    warning_count = sum(channel_scores[name] >= 3.0 for name in observed_channels)
    hard_count = sum(channel_scores[name] >= 5.0 for name in observed_channels)
    return {
        "feature_z": feature_scores,
        "channel_z": channel_scores,
        "observed_channels": sorted(observed_channels),
        "observation_warning_count": int(warning_count),
        "observation_hard_count": int(hard_count),
        "max_observation_z": max(feature_scores.values(), default=0.0),
    }


def validate_runtime_trigger_input(payload: Mapping[str, object]) -> None:
    extra = set(payload) - RUNTIME_KEYS
    missing = RUNTIME_KEYS - set(payload)
    if extra or missing:
        raise ValueError(f"runtime trigger keys mismatch; extra={sorted(extra)}, missing={sorted(missing)}")
    for key in payload:
        lowered = key.lower()
        if any(fragment in lowered for fragment in PROHIBITED_RUNTIME_FRAGMENTS):
            raise ValueError(f"prohibited runtime trigger key: {key}")


def _as_bool(value: object, *, name: str) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)) and int(value) in (0, 1):
        return bool(value)
    if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
        return value.strip().lower() == "true"
    raise ValueError(f"{name} must be an explicit boolean")


def runtime_input_from_model_and_packet(
    model_row: Mapping[str, object],
    packet_score: Mapping[str, object],
    operational_context: Mapping[str, object],
) -> dict[str, object]:
    ood = operational_context["traffic_environment_ood"]
    quality = operational_context["data_quality"]
    payload = {
        "integration_step_index": int(model_row["cycle"]),
        "model_warning": _as_bool(
            model_row["candidate_request_inspection"], name="model_warning"
        ),
        "model_stop": _as_bool(
            model_row["candidate_stop_recursive"], name="model_stop"
        ),
        "observation_warning_count": int(packet_score["observation_warning_count"]),
        "observation_hard_count": int(packet_score["observation_hard_count"]),
        "max_observation_z": float(packet_score["max_observation_z"]),
        "traffic_environment_ood_warning": _as_bool(
            ood["warning"], name="traffic_environment_ood_warning"
        ),
        "traffic_environment_ood_hard": _as_bool(
            ood["hard"], name="traffic_environment_ood_hard"
        ),
        "data_quality_warning": _as_bool(
            quality["warning"], name="data_quality_warning"
        ),
        "data_quality_hard": _as_bool(
            quality["hard"], name="data_quality_hard"
        ),
        "inspection_overdue": _as_bool(
            operational_context["inspection_overdue"], name="inspection_overdue"
        ),
        "maintenance_event": _as_bool(
            operational_context["maintenance_event"], name="maintenance_event"
        ),
    }
    validate_runtime_trigger_input(payload)
    return payload


def apply_innovation_aware_rule(
    runtime_rows: list[Mapping[str, object]],
    calibration_steps: Iterable[int],
) -> list[dict[str, object]]:
    calibration = set(int(step) for step in calibration_steps)
    consecutive_soft = 0
    decisions: list[dict[str, object]] = []
    for source in runtime_rows:
        validate_runtime_trigger_input(source)
        row = dict(source)
        model_warning = _as_bool(row["model_warning"], name="model_warning")
        model_stop = _as_bool(row["model_stop"], name="model_stop")
        ood_warning = _as_bool(
            row["traffic_environment_ood_warning"],
            name="traffic_environment_ood_warning",
        )
        ood_hard = _as_bool(
            row["traffic_environment_ood_hard"],
            name="traffic_environment_ood_hard",
        )
        quality_warning = _as_bool(
            row["data_quality_warning"], name="data_quality_warning"
        )
        quality_hard = _as_bool(
            row["data_quality_hard"], name="data_quality_hard"
        )
        inspection_overdue = _as_bool(
            row["inspection_overdue"], name="inspection_overdue"
        )
        maintenance_event = _as_bool(
            row["maintenance_event"], name="maintenance_event"
        )
        observation_warning = int(row["observation_warning_count"]) >= 1
        observation_hard = int(row["observation_hard_count"]) >= 1
        corroborated = model_warning and (
            observation_warning
            or ood_warning
            or quality_warning
        )
        hard_gate = (
            observation_hard
            or ood_hard
            or quality_hard
            or inspection_overdue
            or maintenance_event
        )
        soft_gate = (
            model_warning
            or observation_warning
            or ood_warning
            or quality_warning
        )
        if int(row["integration_step_index"]) in calibration:
            request = stop = False
            consecutive_soft = 0
        else:
            consecutive_soft = consecutive_soft + 1 if soft_gate else 0
            request = hard_gate or corroborated
            stop = hard_gate or model_stop or consecutive_soft >= 2
            request = request or stop
        row["innovation_aware_request_inspection"] = bool(request)
        row["innovation_aware_stop_recursive"] = bool(stop)
        row["runtime_decision_status"] = "diagnostic_only_single_synthetic_trajectory"
        decisions.append(row)
    return decisions
