"""Versioned handoff from road observations to assimilated fracture state.

The bundle is deliberately an interface layer. It does not perform an inverse
solve and it keeps hidden FEM fields out of deployable observation channels.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


BUNDLE_VERSION = "road_observation_state_bundle_v1"
AGENT3_SKELETON_VERSION = "road_forecast_history_sequence_skeleton_v1"
AGENT2_PACKET_VERSION = "road_observation_innovation_packet_v1"

STATE_FIELDS = (
    "damage",
    "fatigue_history",
    "fatigue_degradation",
    "log10_psi_raw",
)
LEGACY_STATE_FIELDS = (
    "damage",
    "alpha_bar",
    "fatigue_degradation",
    "log10_psi_raw",
)
EVIDENCE_CLASSES = ("oracle", "synthetic", "real")
UNCERTAINTY_KINDS = ("std", "covariance", "ensemble")

NODE_OBSERVATION_CHANNELS = (
    "registered_crack_probability",
    "strain_axial",
    "log10_psi_raw_oracle",
)
NODE_OBSERVATION_EVIDENCE = ("synthetic", "synthetic", "oracle")
GLOBAL_OBSERVATION_CHANNELS = (
    "crack_tip_x",
    "crack_width_mean",
    "fwd_deflection_center",
    "fwd_deflection_offset_300mm",
)
TRAFFIC_CHANNELS = (
    "equivalent_standard_axle_load_increment",
    "heavy_axle_count",
    "mean_axle_load",
)
ENVIRONMENT_CHANNELS = (
    "air_temperature",
    "pavement_temperature",
    "layer_moisture",
)

_FORBIDDEN_SENSOR_NAMES = {
    "damage",
    "alpha",
    "alpha_bar",
    "fatigue_history",
    "fatigue_degradation",
    "g_alpha",
    "psi_raw",
    "log10_psi_raw",
    "raw_driver",
    "log10_raw_driver",
    "psi_active",
    "active_driver",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_sha256(path: Path, expected: str) -> None:
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch for {path}: expected {expected}, got {actual}")


def bundle_schema() -> dict[str, Any]:
    """Return the normative v1 bundle schema."""
    return {
        "schema_version": BUNDLE_VERSION,
        "purpose": "predictor-independent observation-to-state handoff",
        "claim_boundary": "interface validation is not real-road state inversion validation",
        "state_fields": list(STATE_FIELDS),
        "arrays": {
            "state_mean": {"shape": ["T", "N", "C"], "dtype": "float32"},
            "state_std": {
                "shape": ["T", "N", "C"],
                "dtype": "float32",
                "optional": True,
                "rule": "all NaN is permitted only when uncertainty_status is uncalibrated",
            },
            "state_covariance": {
                "shape": ["T", "N", "C", "C"],
                "dtype": "float32",
                "optional": True,
            },
            "state_ensemble": {
                "shape": ["M", "T", "N", "C"],
                "dtype": "float32",
                "optional": True,
            },
            "observed_channel_mask": {
                "shape": ["T", "N", "C"],
                "dtype": "bool",
                "meaning": "latent-state channels directly constrained by the declared assimilation",
            },
            "node_observation_values": {
                "shape": ["T", "N", "P"],
                "dtype": "float32",
                "meaning": "measurement-space node channels, distinct from latent-state channels",
            },
            "node_observation_mask": {"shape": ["T", "N", "P"], "dtype": "bool"},
            "global_observation_values": {"shape": ["T", "G"], "dtype": "float32"},
            "global_observation_mask": {"shape": ["T", "G"], "dtype": "bool"},
            "timestamp": {"shape": ["T"], "dtype": "unicode"},
            "timestamp_mask": {"shape": ["T"], "dtype": "bool"},
            "equivalent_load_index": {"shape": ["T"], "dtype": "float64"},
            "equivalent_load_index_mask": {"shape": ["T"], "dtype": "bool"},
            "delta_t": {"shape": ["T"], "dtype": "float64"},
            "delta_t_mask": {"shape": ["T"], "dtype": "bool"},
            "traffic_values": {"shape": ["T", "L"], "dtype": "float32"},
            "traffic_mask": {"shape": ["T", "L"], "dtype": "bool"},
            "environment_values": {"shape": ["T", "Q"], "dtype": "float32"},
            "environment_mask": {"shape": ["T", "Q"], "dtype": "bool"},
            "maintenance_reset": {"shape": ["T"], "dtype": "bool"},
            "maintenance_reset_declared": {"shape": ["T"], "dtype": "bool"},
            "maintenance_event_id": {"shape": ["T"], "dtype": "unicode"},
            "state_segment_id": {"shape": ["T"], "dtype": "int32"},
        },
        "uncertainty_compatibility": {
            "exclusive_representation": list(UNCERTAINTY_KINDS),
            "std_from_covariance": "sqrt(max(diag(covariance), 0))",
            "std_from_ensemble": "sample standard deviation over M (ddof=1)",
            "uncalibrated": "state_std must be NaN, never zero-filled certainty",
        },
        "mask_semantics": {
            "observed_channel_mask": "assimilation attribution in latent-state space",
            "node_observation_mask": "availability in node measurement space",
            "global_observation_mask": "availability in asset/global measurement space",
            "missing_values": "NaN with mask=false; normalization may zero-fill only after retaining mask",
        },
        "required_metadata": [
            "schema_version",
            "evidence_class",
            "coordinate_frame",
            "registration_id",
            "uncertainty_kind",
            "uncertainty_status",
            "source_sha256",
            "source_schema_versions",
            "real_road_compatible",
        ],
        "evidence_classes": {
            "oracle": "hidden FEM access, audit/upper-bound only",
            "synthetic": "declared sensor rendering from a physical/simulation state",
            "real": "measured road/laboratory observation with provenance",
        },
        "maintenance_rule": "a reset requires declared metadata, event id, and a new state segment",
        "fairness_rule": "all predictors consume a byte-identical bundle and prior",
    }


def validate_observation_channels(
    names: Sequence[str], evidence_classes: Sequence[str]
) -> list[str]:
    errors: list[str] = []
    if len(names) != len(evidence_classes):
        return ["observation channel and evidence-class counts differ"]
    for name, evidence in zip(names, evidence_classes):
        normalized = name.strip().lower()
        if evidence not in EVIDENCE_CLASSES:
            errors.append(f"invalid evidence class for observation channel {name}")
            continue
        oracle_suffix = normalized.endswith("_oracle")
        base = normalized[: -len("_oracle")] if oracle_suffix else normalized
        if base in _FORBIDDEN_SENSOR_NAMES:
            if not (oracle_suffix and evidence == "oracle"):
                errors.append(f"latent field cannot be a deployable sensor channel: {name}")
        if oracle_suffix and evidence != "oracle":
            errors.append(f"oracle-labelled channel must have oracle evidence: {name}")
    return errors


def _validate_missing(values: np.ndarray, mask: np.ndarray, label: str) -> list[str]:
    errors: list[str] = []
    if values.shape != mask.shape:
        return [f"{label} values and mask shapes differ"]
    if mask.dtype != np.bool_:
        errors.append(f"{label} mask must be boolean")
    boolean_mask = mask.astype(bool, copy=False)
    if np.any(boolean_mask & ~np.isfinite(values)):
        errors.append(f"{label} observed entries must be finite")
    if np.any(~boolean_mask & ~np.isnan(values)):
        errors.append(f"{label} missing entries must be NaN with mask=false")
    return errors


def uncertainty_std(package: Mapping[str, np.ndarray], metadata: Mapping[str, Any]) -> np.ndarray:
    kind = metadata.get("uncertainty_kind")
    if kind == "std":
        return np.asarray(package["state_std"], dtype=np.float32)
    if kind == "covariance":
        covariance = np.asarray(package["state_covariance"], dtype=np.float32)
        return np.sqrt(np.maximum(np.diagonal(covariance, axis1=-2, axis2=-1), 0.0))
    if kind == "ensemble":
        ensemble = np.asarray(package["state_ensemble"], dtype=np.float32)
        if ensemble.shape[0] < 2:
            raise ValueError("state_ensemble requires at least two members")
        return np.std(ensemble, axis=0, ddof=1).astype(np.float32)
    raise ValueError(f"unsupported uncertainty_kind: {kind}")


def build_bundle_from_legacy(
    *,
    legacy_path: Path,
    output_path: Path,
    expected_legacy_sha256: str,
    source_sha256: Mapping[str, str],
    source_schema_versions: Mapping[str, str],
) -> dict[str, Any]:
    """Adapt the frozen c87 v1 state without inventing road observations."""
    verify_sha256(legacy_path, expected_legacy_sha256)
    with np.load(legacy_path, allow_pickle=False) as legacy:
        legacy_fields = tuple(str(value) for value in legacy["state_fields"].tolist())
        if legacy_fields != LEGACY_STATE_FIELDS:
            raise ValueError(f"unexpected legacy state order: {legacy_fields}")
        legacy_metadata = json.loads(str(legacy["metadata_json"].item()))
        state_mean = np.asarray(legacy["state_mean"], dtype=np.float32)[None, ...]
        state_std = np.asarray(legacy["state_std"], dtype=np.float32)[None, ...]
        observed_channel_mask = np.asarray(legacy["observed_channel_mask"], dtype=bool)[None, ...]
        source_code = np.asarray(legacy["source_code"], dtype=np.uint8)[None, ...]
        coordinates = np.asarray(legacy["coordinates"], dtype=np.float32)
        areas = np.asarray(legacy["areas"], dtype=np.float32)
        edge_index = np.asarray(legacy["edge_index"], dtype=np.int64)
        edge_attr = np.asarray(legacy["edge_attr"], dtype=np.float32)
        cycle = int(np.asarray(legacy["cycle"]).item())

    t_count, node_count, _ = state_mean.shape
    node_values = np.full((t_count, node_count, len(NODE_OBSERVATION_CHANNELS)), np.nan, dtype=np.float32)
    node_mask = np.zeros_like(node_values, dtype=bool)
    raw_index = STATE_FIELDS.index("log10_psi_raw")
    oracle_index = NODE_OBSERVATION_CHANNELS.index("log10_psi_raw_oracle")
    oracle_mask = observed_channel_mask[:, :, raw_index]
    node_values[:, :, oracle_index][oracle_mask] = state_mean[:, :, raw_index][oracle_mask]
    node_mask[:, :, oracle_index] = oracle_mask

    global_values = np.full((t_count, len(GLOBAL_OBSERVATION_CHANNELS)), np.nan, dtype=np.float32)
    global_mask = np.zeros_like(global_values, dtype=bool)
    traffic_values = np.full((t_count, len(TRAFFIC_CHANNELS)), np.nan, dtype=np.float32)
    traffic_mask = np.zeros_like(traffic_values, dtype=bool)
    environment_values = np.full((t_count, len(ENVIRONMENT_CHANNELS)), np.nan, dtype=np.float32)
    environment_mask = np.zeros_like(environment_values, dtype=bool)

    metadata = {
        "schema_version": BUNDLE_VERSION,
        "bundle_id": "c87_fem_oracle_upper_bound_adapter",
        "evidence_class": "oracle",
        "evidence_detail": "fem_oracle",
        "state_fields": list(STATE_FIELDS),
        "coordinate_frame": "synthetic_fem_mesh_xy",
        "registration_id": "fem_mesh_identity",
        "uncertainty_kind": "std",
        "uncertainty_status": "uncalibrated_not_available",
        "source_sha256": dict(source_sha256),
        "source_schema_versions": dict(source_schema_versions),
        "legacy_metadata": legacy_metadata,
        "real_road_compatible": False,
        "training_run": False,
        "fem_eta": 0.0,
        "claim": "interface-only synthetic/oracle handoff; not a real-road inversion",
        "missingness_rule": "NaN plus explicit false mask",
        "oracle_channels_decision_eligible": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        schema_version=np.asarray(BUNDLE_VERSION),
        metadata_json=np.asarray(json.dumps(metadata, sort_keys=True)),
        cycle=np.asarray([cycle], dtype=np.int32),
        state_fields=np.asarray(STATE_FIELDS),
        coordinates=coordinates,
        areas=areas,
        edge_index=edge_index,
        edge_attr=edge_attr,
        state_mean=state_mean,
        state_std=state_std,
        observed_channel_mask=observed_channel_mask,
        source_code=source_code,
        node_observation_channels=np.asarray(NODE_OBSERVATION_CHANNELS),
        node_observation_evidence=np.asarray(NODE_OBSERVATION_EVIDENCE),
        node_observation_values=node_values,
        node_observation_mask=node_mask,
        global_observation_channels=np.asarray(GLOBAL_OBSERVATION_CHANNELS),
        global_observation_evidence=np.asarray(["synthetic"] * len(GLOBAL_OBSERVATION_CHANNELS)),
        global_observation_values=global_values,
        global_observation_mask=global_mask,
        timestamp=np.asarray([""]),
        timestamp_mask=np.asarray([False]),
        equivalent_load_index=np.asarray([np.nan], dtype=np.float64),
        equivalent_load_index_mask=np.asarray([False]),
        delta_t=np.asarray([np.nan], dtype=np.float64),
        delta_t_mask=np.asarray([False]),
        traffic_channels=np.asarray(TRAFFIC_CHANNELS),
        traffic_values=traffic_values,
        traffic_mask=traffic_mask,
        environment_channels=np.asarray(ENVIRONMENT_CHANNELS),
        environment_values=environment_values,
        environment_mask=environment_mask,
        maintenance_reset=np.asarray([False]),
        maintenance_reset_declared=np.asarray([False]),
        maintenance_event_id=np.asarray([""]),
        state_segment_id=np.asarray([0], dtype=np.int32),
    )
    return metadata


def validate_bundle(path: Path) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version", "metadata_json", "state_fields", "coordinates", "areas",
        "edge_index", "edge_attr", "state_mean", "observed_channel_mask", "source_code",
        "node_observation_channels", "node_observation_evidence", "node_observation_values",
        "node_observation_mask", "global_observation_channels", "global_observation_evidence",
        "global_observation_values", "global_observation_mask", "timestamp", "timestamp_mask",
        "equivalent_load_index", "equivalent_load_index_mask", "delta_t", "delta_t_mask",
        "traffic_channels", "traffic_values", "traffic_mask", "environment_channels",
        "environment_values", "environment_mask", "maintenance_reset",
        "maintenance_reset_declared", "maintenance_event_id", "state_segment_id",
    }
    with np.load(path, allow_pickle=False) as package:
        missing = sorted(required - set(package.files))
        if missing:
            return [f"missing arrays: {missing}"]
        metadata = json.loads(str(package["metadata_json"].item()))
        if str(package["schema_version"].item()) != BUNDLE_VERSION:
            errors.append("unexpected bundle schema version")
        if metadata.get("schema_version") != BUNDLE_VERSION:
            errors.append("metadata schema version differs from bundle")
        fields = tuple(str(value) for value in package["state_fields"].tolist())
        if fields != STATE_FIELDS:
            errors.append("state field order differs from canonical contract")
        state = np.asarray(package["state_mean"])
        if state.ndim != 3 or state.shape[-1] != len(STATE_FIELDS) or not np.all(np.isfinite(state)):
            errors.append("state_mean must be finite with shape [T,N,C]")
            return errors
        t_count, node_count, channel_count = state.shape
        coordinates = np.asarray(package["coordinates"])
        areas = np.asarray(package["areas"])
        if coordinates.shape != (node_count, 2):
            errors.append("coordinates must have shape [N,2]")
        if areas.shape != (node_count,) or np.any(~np.isfinite(areas)) or np.any(areas <= 0):
            errors.append("areas must be finite and positive with shape [N]")
        observed = np.asarray(package["observed_channel_mask"])
        if observed.shape != state.shape or observed.dtype != np.bool_:
            errors.append("observed_channel_mask must be boolean [T,N,C]")

        available_uncertainty = {
            "std": "state_std" in package.files,
            "covariance": "state_covariance" in package.files,
            "ensemble": "state_ensemble" in package.files,
        }
        if sum(available_uncertainty.values()) != 1:
            errors.append("exactly one uncertainty representation must be present")
        kind = metadata.get("uncertainty_kind")
        if kind not in UNCERTAINTY_KINDS or not available_uncertainty.get(kind, False):
            errors.append("uncertainty_kind does not match stored representation")
        else:
            try:
                std = uncertainty_std(package, metadata)
                if std.shape != (t_count, node_count, channel_count):
                    errors.append("derived state uncertainty must have shape [T,N,C]")
                status = metadata.get("uncertainty_status")
                if status == "uncalibrated_not_available":
                    if not np.isnan(std).all():
                        errors.append("uncalibrated uncertainty must be all NaN")
                elif np.any(~np.isfinite(std)) or np.any(std < 0):
                    errors.append("calibrated uncertainty must be finite and nonnegative")
            except (KeyError, ValueError) as exc:
                errors.append(str(exc))

        node_names = tuple(str(value) for value in package["node_observation_channels"].tolist())
        node_evidence = tuple(str(value) for value in package["node_observation_evidence"].tolist())
        errors.extend(validate_observation_channels(node_names, node_evidence))
        errors.extend(_validate_missing(
            np.asarray(package["node_observation_values"]),
            np.asarray(package["node_observation_mask"]),
            "node observations",
        ))
        global_names = tuple(str(value) for value in package["global_observation_channels"].tolist())
        global_evidence = tuple(str(value) for value in package["global_observation_evidence"].tolist())
        errors.extend(validate_observation_channels(global_names, global_evidence))
        errors.extend(_validate_missing(
            np.asarray(package["global_observation_values"]),
            np.asarray(package["global_observation_mask"]),
            "global observations",
        ))
        for label in ("traffic", "environment"):
            errors.extend(_validate_missing(
                np.asarray(package[f"{label}_values"]),
                np.asarray(package[f"{label}_mask"]),
                label,
            ))
        for value_key, mask_key, label in (
            ("equivalent_load_index", "equivalent_load_index_mask", "equivalent load index"),
            ("delta_t", "delta_t_mask", "delta_t"),
        ):
            errors.extend(_validate_missing(
                np.asarray(package[value_key]), np.asarray(package[mask_key]), label
            ))

        for key in ("timestamp", "timestamp_mask", "maintenance_reset", "maintenance_reset_declared", "maintenance_event_id", "state_segment_id"):
            if np.asarray(package[key]).shape != (t_count,):
                errors.append(f"{key} must have shape [T]")
        timestamps = np.asarray(package["timestamp"]).astype(str)
        timestamp_mask = np.asarray(package["timestamp_mask"])
        if timestamp_mask.dtype != np.bool_:
            errors.append("timestamp_mask must be boolean")
        else:
            if np.any(timestamp_mask & (np.char.str_len(timestamps) == 0)):
                errors.append("available timestamps must be non-empty")
            if np.any(~timestamp_mask & (np.char.str_len(timestamps) != 0)):
                errors.append("missing timestamps must be empty with mask=false")
        reset = np.asarray(package["maintenance_reset"], dtype=bool)
        declared = np.asarray(package["maintenance_reset_declared"], dtype=bool)
        event_id = np.asarray(package["maintenance_event_id"]).astype(str)
        segment = np.asarray(package["state_segment_id"], dtype=np.int32)
        for index in np.flatnonzero(reset):
            if not declared[index] or not event_id[index].strip():
                errors.append("maintenance reset requires declared metadata and event id")
            if (index == 0 and segment[index] <= 0) or (index > 0 and segment[index] == segment[index - 1]):
                errors.append("maintenance reset must start a new state segment")
        if metadata.get("evidence_class") not in EVIDENCE_CLASSES:
            errors.append("invalid bundle evidence class")
        if metadata.get("evidence_class") == "oracle" and metadata.get("real_road_compatible") is not False:
            errors.append("oracle bundle cannot be marked real-road compatible")
        if not isinstance(metadata.get("source_sha256"), dict) or not metadata["source_sha256"]:
            errors.append("source_sha256 provenance is required")
    return errors


def write_agent3_history_skeleton(bundle_path: Path, output_path: Path) -> dict[str, Any]:
    """Write Agent3's history input without model-specific normalization."""
    errors = validate_bundle(bundle_path)
    if errors:
        raise ValueError(f"invalid source bundle: {errors}")
    with np.load(bundle_path, allow_pickle=False) as package:
        metadata = json.loads(str(package["metadata_json"].item()))
        std = uncertainty_std(package, metadata)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            output_path,
            contract_version=np.asarray(AGENT3_SKELETON_VERSION),
            source_bundle_sha256=np.asarray(sha256(bundle_path)),
            metadata_json=np.asarray(json.dumps({
                "contract_version": AGENT3_SKELETON_VERSION,
                "source_bundle_version": BUNDLE_VERSION,
                "source_evidence_class": metadata["evidence_class"],
                "zero_fill_before_normalization": False,
                "normalization_rule": "consumer may zero-fill only after retaining masks",
                "decision_eligible": metadata["evidence_class"] != "oracle",
            }, sort_keys=True)),
            state_fields=np.asarray(package["state_fields"]),
            z_analysis=np.asarray(package["state_mean"], dtype=np.float32),
            z_uncertainty_std=std,
            observed_channel_mask=np.asarray(package["observed_channel_mask"], dtype=bool),
            coordinates=np.asarray(package["coordinates"], dtype=np.float32),
            areas=np.asarray(package["areas"], dtype=np.float32),
            edge_index=np.asarray(package["edge_index"], dtype=np.int64),
            edge_attr=np.asarray(package["edge_attr"], dtype=np.float32),
            node_observation_channels=np.asarray(package["node_observation_channels"]),
            node_observation_values=np.asarray(package["node_observation_values"], dtype=np.float32),
            node_observation_mask=np.asarray(package["node_observation_mask"], dtype=bool),
            global_observation_channels=np.asarray(package["global_observation_channels"]),
            global_observation_values=np.asarray(package["global_observation_values"], dtype=np.float32),
            global_observation_mask=np.asarray(package["global_observation_mask"], dtype=bool),
            timestamp=np.asarray(package["timestamp"]),
            timestamp_mask=np.asarray(package["timestamp_mask"], dtype=bool),
            equivalent_load_index=np.asarray(package["equivalent_load_index"], dtype=np.float64),
            equivalent_load_index_mask=np.asarray(package["equivalent_load_index_mask"], dtype=bool),
            delta_t=np.asarray(package["delta_t"], dtype=np.float64),
            delta_t_mask=np.asarray(package["delta_t_mask"], dtype=bool),
            traffic_channels=np.asarray(package["traffic_channels"]),
            traffic_values=np.asarray(package["traffic_values"], dtype=np.float32),
            traffic_mask=np.asarray(package["traffic_mask"], dtype=bool),
            environment_channels=np.asarray(package["environment_channels"]),
            environment_values=np.asarray(package["environment_values"], dtype=np.float32),
            environment_mask=np.asarray(package["environment_mask"], dtype=bool),
            maintenance_reset=np.asarray(package["maintenance_reset"], dtype=bool),
            maintenance_reset_declared=np.asarray(package["maintenance_reset_declared"], dtype=bool),
            maintenance_event_id=np.asarray(package["maintenance_event_id"]),
            state_segment_id=np.asarray(package["state_segment_id"], dtype=np.int32),
        )
    return {"contract_version": AGENT3_SKELETON_VERSION, "source_bundle_sha256": sha256(bundle_path)}


def agent2_innovation_packet(bundle_path: Path) -> dict[str, Any]:
    """Create a missing-aware Agent2 trigger packet, excluding oracle fields."""
    errors = validate_bundle(bundle_path)
    if errors:
        raise ValueError(f"invalid source bundle: {errors}")
    with np.load(bundle_path, allow_pickle=False) as package:
        metadata = json.loads(str(package["metadata_json"].item()))
        oracle_count = int(np.asarray(package["node_observation_mask"], dtype=bool)[:, :, NODE_OBSERVATION_CHANNELS.index("log10_psi_raw_oracle")].sum())
        return {
            "packet_version": AGENT2_PACKET_VERSION,
            "source_bundle_version": BUNDLE_VERSION,
            "source_bundle_sha256": sha256(bundle_path),
            "evidence_class": metadata["evidence_class"],
            "decision_eligible": False,
            "decision_eligibility_reason": "only an oracle upper-bound state is present; deployable road innovations are missing",
            "timestamp": {"value": None, "available": False},
            "equivalent_load_index": {"value": None, "available": False},
            "innovations": {
                "registered_crack_image": {"value": None, "available": False, "mask": False},
                "fwd_deflection_basin": {"value": None, "available": False, "mask": False},
                "strain_sensor": {"value": None, "available": False, "mask": False},
            },
            "forcing": {
                "wim_axle_spectrum": {"value": None, "available": False, "mask": False},
                "temperature_moisture": {"value": None, "available": False, "mask": False},
            },
            "maintenance": {"reset": False, "declared": False, "event_id": None},
            "audit_only_oracle": {
                "channel": "log10_psi_raw_oracle",
                "observed_node_count": oracle_count,
                "values_exported_to_trigger": False,
            },
            "missingness_rule": "null plus mask=false; missing never means zero innovation",
        }


def validate_agent2_packet(packet: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if packet.get("packet_version") != AGENT2_PACKET_VERSION:
        errors.append("unexpected Agent2 packet version")
    for group in ("innovations", "forcing"):
        for name, item in packet.get(group, {}).items():
            available = bool(item.get("available"))
            if not available and (item.get("value") is not None or item.get("mask") is not False):
                errors.append(f"missing Agent2 channel must be null with mask=false: {name}")
    audit = packet.get("audit_only_oracle", {})
    if audit.get("values_exported_to_trigger") is not False:
        errors.append("oracle values cannot enter the Agent2 trigger packet")
    if packet.get("evidence_class") == "oracle" and packet.get("decision_eligible") is not False:
        errors.append("oracle packet cannot be decision eligible")
    return errors
