"""Closed-loop road fracture forecast API and frozen-contract adapters.

The API connects three independently versioned interfaces without renaming
their fields in place:

* Agent 1 ``road_observation_state_bundle_v1`` analysis/observation bundles;
* Agent 2 road-time, forecast-horizon, and observation-trigger contracts; and
* Agent 3 observation-aware short-horizon graph forecasters.

This module is intentionally conservative.  Field forecasts stop at h1-h3.
Longer-range outputs are only exposed when scenario-conditioned risk heads are
explicitly declared trained.  Missing uncertainty remains unavailable rather
than being converted into false zero variance.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch

from fem_mechanism_operator import StateStatistics
from road_observation_aware_operator import (
    RoadFeatureLayout,
    RoadFeatureStatistics,
    RoadForecastOutput,
    RoadFutureScenario,
    RoadObservationAwareForecaster,
    RoadObservationSequence,
)


AGENT1_SCHEMA = "road_observation_state_bundle_v1"
AGENT2_TIME_SCHEMA = "road_time_mapping_v1"
AGENT2_HORIZON_SCHEMA = "road_forecast_horizon_v1"
AGENT2_TRIGGER_SCHEMA = "road_observation_trigger_v1"
FORECAST_CONTRACT = "road_forecast_input_contract_v1"
FORECAST_FIELD_ORDER = (
    "damage",
    "fatigue_history",
    "fatigue_degradation",
    "log10_psi_raw",
)
STATE_FIELD_ALIASES = {
    "damage": "damage",
    "alpha_bar": "fatigue_history",
    "fatigue_history": "fatigue_history",
    "fatigue_degradation": "fatigue_degradation",
    "log10_raw_driver": "log10_psi_raw",
    "log10_psi_raw": "log10_psi_raw",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_json_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def tensor_sha256(value: torch.Tensor) -> str:
    array = value.detach().cpu().contiguous().numpy()
    return hashlib.sha256(array.tobytes()).hexdigest()


@dataclass(frozen=True)
class RoadObservationStateBundle:
    """Validated Agent 1 v1 analysis and independent observation bundle."""

    path: Path
    package_sha256: str
    cycles: torch.Tensor
    state_mean: torch.Tensor
    state_std: torch.Tensor
    state_covariance: torch.Tensor | None
    state_ensemble: torch.Tensor | None
    observed_channel_mask: torch.Tensor
    source_code: torch.Tensor
    node_observation_channels: tuple[str, ...]
    node_observation_evidence: tuple[str, ...]
    node_observation_values: torch.Tensor
    node_observation_mask: torch.Tensor
    global_observation_channels: tuple[str, ...]
    global_observation_evidence: tuple[str, ...]
    global_observation_values: torch.Tensor
    global_observation_mask: torch.Tensor
    timestamp: tuple[str, ...]
    timestamp_mask: torch.Tensor
    equivalent_load_index: torch.Tensor
    equivalent_load_index_mask: torch.Tensor
    delta_t: torch.Tensor
    delta_t_mask: torch.Tensor
    traffic_channels: tuple[str, ...]
    traffic_values: torch.Tensor
    traffic_mask: torch.Tensor
    environment_channels: tuple[str, ...]
    environment_values: torch.Tensor
    environment_mask: torch.Tensor
    maintenance_reset: torch.Tensor
    maintenance_reset_declared: torch.Tensor
    maintenance_event_id: tuple[str, ...]
    state_segment_id: torch.Tensor
    graph: Mapping[str, torch.Tensor]
    metadata: Mapping[str, Any]
    source_field_order: tuple[str, ...]
    forecast_field_order: tuple[str, ...]
    uncertainty_available: bool
    uncertainty_trigger_eligible: bool
    decision_eligible: bool

    @property
    def mask_sha256(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.node_observation_mask.cpu().contiguous().numpy().tobytes())
        digest.update(self.global_observation_mask.cpu().contiguous().numpy().tobytes())
        return digest.hexdigest()

    @property
    def assimilation_mask_sha256(self) -> str:
        return tensor_sha256(self.observed_channel_mask)

    @property
    def origin_id(self) -> str:
        return f"{self.metadata['bundle_id']}:c{int(self.cycles[-1])}"


def _scalar(data: np.lib.npyio.NpzFile, name: str) -> Any:
    return np.asarray(data[name]).reshape(-1)[0].item()


def _require_missing_aware(name: str, values: np.ndarray, mask: np.ndarray) -> None:
    if mask.dtype != np.bool_ or values.shape != mask.shape:
        raise ValueError(f"{name} values/mask mismatch")
    if mask.any() and not np.isfinite(values[mask]).all():
        raise ValueError(f"{name} has non-finite available values")
    if (~mask).any() and not np.isnan(values[~mask]).all():
        raise ValueError(f"{name} missing values must be NaN")


def load_road_observation_state_bundle(
    path: Path,
    *,
    expected_sha256: str | None = None,
    device: torch.device | str = "cpu",
) -> RoadObservationStateBundle:
    """Load Agent 1 v1 T,N,C state and independent measurement arrays."""
    path = Path(path)
    actual_sha = sha256_file(path)
    if expected_sha256 is not None and actual_sha != expected_sha256:
        raise ValueError("Agent 1 observation-state bundle SHA-256 mismatch")
    with np.load(path, allow_pickle=False) as data:
        required = {
            "schema_version",
            "metadata_json",
            "cycle",
            "state_fields",
            "coordinates",
            "areas",
            "edge_index",
            "edge_attr",
            "state_mean",
            "observed_channel_mask",
            "source_code",
            "node_observation_channels",
            "node_observation_evidence",
            "node_observation_values",
            "node_observation_mask",
            "global_observation_channels",
            "global_observation_evidence",
            "global_observation_values",
            "global_observation_mask",
            "timestamp",
            "timestamp_mask",
            "equivalent_load_index",
            "equivalent_load_index_mask",
            "delta_t",
            "delta_t_mask",
            "traffic_channels",
            "traffic_values",
            "traffic_mask",
            "environment_channels",
            "environment_values",
            "environment_mask",
            "maintenance_reset",
            "maintenance_reset_declared",
            "maintenance_event_id",
            "state_segment_id",
        }
        missing = sorted(required - set(data.files))
        if missing:
            raise ValueError(f"Agent 1 package lacks arrays: {missing}")
        schema = str(_scalar(data, "schema_version"))
        if schema != AGENT1_SCHEMA:
            raise ValueError(f"unsupported Agent 1 schema {schema!r}")
        source_fields = tuple(str(value) for value in np.asarray(data["state_fields"]))
        canonical_fields = tuple(
            STATE_FIELD_ALIASES.get(value, "") for value in source_fields
        )
        if set(canonical_fields) != set(FORECAST_FIELD_ORDER):
            raise ValueError(
                "Agent 1 state fields cannot map to the canonical registry"
            )
        canonical_order = [
            canonical_fields.index(name) for name in FORECAST_FIELD_ORDER
        ]
        metadata = json.loads(str(_scalar(data, "metadata_json")))
        arrays = {
            name: np.asarray(data[name])
            for name in data.files
            if name not in {"schema_version", "metadata_json", "state_fields"}
        }

    coordinates = arrays["coordinates"]
    areas = arrays["areas"]
    edge_index = arrays["edge_index"]
    edge_attr = arrays["edge_attr"]
    state_mean = arrays["state_mean"]
    observed = arrays["observed_channel_mask"]
    source_code = arrays["source_code"]
    if state_mean.ndim != 3:
        raise ValueError("Agent 1 state_mean must have shape [T, N, C]")
    time, elements, channels = state_mean.shape
    if channels != 4:
        raise ValueError("Agent 1 v1 requires four canonical state channels")
    state_mean = state_mean[..., canonical_order]
    observed = observed[..., canonical_order]
    source_code = source_code[..., canonical_order]
    uncertainty_kind = str(metadata["uncertainty_kind"])
    covariance = arrays.get("state_covariance")
    ensemble = arrays.get("state_ensemble")
    provided = {
        "std": "state_std" in arrays,
        "covariance": covariance is not None,
        "ensemble": ensemble is not None,
    }
    if uncertainty_kind not in provided or not provided[uncertainty_kind]:
        raise ValueError("declared uncertainty representation is missing")
    if sum(provided.values()) != 1:
        raise ValueError("Agent 1 uncertainty must use exactly one representation")
    if uncertainty_kind == "std":
        state_std = arrays["state_std"][..., canonical_order]
    elif uncertainty_kind == "covariance":
        if covariance.shape != (time, elements, 4, 4):
            raise ValueError("state_covariance must have shape [T, N, C, C]")
        covariance = covariance[..., canonical_order, :][..., :, canonical_order]
        state_std = np.sqrt(np.maximum(np.diagonal(covariance, axis1=-2, axis2=-1), 0))
    else:
        if ensemble.ndim != 4 or ensemble.shape[1:] != (time, elements, 4):
            raise ValueError("state_ensemble must have shape [M, T, N, C]")
        if len(ensemble) < 2:
            raise ValueError("state_ensemble needs at least two members")
        ensemble = ensemble[..., canonical_order]
        state_std = ensemble.std(axis=0, ddof=1)
    expected_shapes = {
        "coordinates": (elements, 2),
        "areas": (elements,),
        "state_mean": (time, elements, 4),
        "state_std": (time, elements, 4),
        "observed_channel_mask": (time, elements, 4),
        "source_code": (time, elements, 4),
    }
    for name, shape in expected_shapes.items():
        derived = {
            "state_mean": state_mean,
            "state_std": state_std,
            "observed_channel_mask": observed,
            "source_code": source_code,
        }
        candidate = derived[name] if name in derived else arrays[name]
        if candidate.shape != shape:
            raise ValueError(f"Agent 1 {name} must have shape {shape}")
    if edge_index.ndim != 2 or edge_index.shape[0] != 2:
        raise ValueError("Agent 1 edge_index must have shape [2, E]")
    if edge_attr.ndim != 2 or len(edge_attr) != edge_index.shape[1]:
        raise ValueError("Agent 1 edge_attr must align with edge_index")
    if not np.isfinite(state_mean).all():
        raise ValueError("Agent 1 state_mean must be finite")
    if not np.isfinite(coordinates).all() or not np.isfinite(areas).all():
        raise ValueError("Agent 1 graph geometry must be finite")
    if np.any(areas <= 0):
        raise ValueError("Agent 1 areas must be positive")
    if edge_index.min() < 0 or edge_index.max() >= elements:
        raise ValueError("Agent 1 edge_index is out of bounds")
    if observed.dtype != np.bool_:
        raise ValueError("Agent 1 observed_channel_mask must be boolean")
    if not np.isin(source_code, [0, 1, 2]).all():
        raise ValueError("Agent 1 source_code contains an unknown value")
    metadata_required = {
        "bundle_id",
        "coordinate_frame",
        "evidence_class",
        "registration_id",
        "schema_version",
        "source_sha256",
        "source_schema_versions",
        "uncertainty_kind",
        "uncertainty_status",
        "real_road_compatible",
    }
    missing_metadata = sorted(metadata_required - set(metadata))
    if missing_metadata:
        raise ValueError(f"Agent 1 metadata missing: {missing_metadata}")
    if metadata.get("fem_eta") is not None and float(metadata["fem_eta"]) != 0.0:
        raise ValueError("this compatibility smoke requires FEM eta=0")
    if metadata["schema_version"] != AGENT1_SCHEMA:
        raise ValueError("metadata schema_version disagrees with the payload")

    cycles = arrays["cycle"].reshape(-1)
    if cycles.shape != (time,):
        raise ValueError("cycle must have shape [T]")
    node_values = arrays["node_observation_values"]
    node_mask = arrays["node_observation_mask"]
    global_values = arrays["global_observation_values"]
    global_mask = arrays["global_observation_mask"]
    if node_values.ndim != 3 or node_values.shape[:2] != (time, elements):
        raise ValueError("node observations must have shape [T, N, P]")
    if global_values.ndim != 2 or global_values.shape[0] != time:
        raise ValueError("global observations must have shape [T, G]")
    if (
        len(arrays["node_observation_channels"]) != node_values.shape[-1]
        or len(arrays["node_observation_evidence"]) != node_values.shape[-1]
    ):
        raise ValueError("node observation registry does not match P")
    if (
        len(arrays["global_observation_channels"]) != global_values.shape[-1]
        or len(arrays["global_observation_evidence"]) != global_values.shape[-1]
    ):
        raise ValueError("global observation registry does not match G")
    _require_missing_aware("node observations", node_values, node_mask)
    _require_missing_aware("global observations", global_values, global_mask)
    for name in ("traffic", "environment"):
        values = arrays[f"{name}_values"]
        mask = arrays[f"{name}_mask"]
        if values.ndim != 2 or values.shape[0] != time:
            raise ValueError(f"{name} must have shape [T, channels]")
        if len(arrays[f"{name}_channels"]) != values.shape[-1]:
            raise ValueError(f"{name} registry does not match its channel dimension")
        _require_missing_aware(name, values, mask)
    for name in ("equivalent_load_index", "delta_t"):
        values = arrays[name].reshape(-1)
        mask = arrays[f"{name}_mask"].reshape(-1)
        if values.shape != (time,) or mask.shape != (time,):
            raise ValueError(f"{name} must have shape [T]")
        _require_missing_aware(name, values, mask)
    timestamps = tuple(str(value) for value in arrays["timestamp"].reshape(-1))
    timestamp_mask = arrays["timestamp_mask"].reshape(-1)
    if len(timestamps) != time or timestamp_mask.dtype != np.bool_:
        raise ValueError("timestamp values/mask must have shape [T]")
    for value, available in zip(timestamps, timestamp_mask):
        if available and not value:
            raise ValueError("available timestamp cannot be empty")
        if not available and value:
            raise ValueError("missing timestamp must be empty")
    reset = arrays["maintenance_reset"].reshape(-1)
    declared = arrays["maintenance_reset_declared"].reshape(-1)
    event_ids = tuple(
        str(value) for value in arrays["maintenance_event_id"].reshape(-1)
    )
    segment = arrays["state_segment_id"].reshape(-1)
    if (
        reset.shape != (time,)
        or declared.shape != (time,)
        or len(event_ids) != time
        or segment.shape != (time,)
        or reset.dtype != np.bool_
        or declared.dtype != np.bool_
    ):
        raise ValueError("maintenance arrays must share the T dimension and dtypes")
    for index in np.flatnonzero(reset):
        if not declared[index] or not event_ids[index]:
            raise ValueError("maintenance reset requires declaration and event id")
        if index == 0 or segment[index] == segment[index - 1]:
            raise ValueError("maintenance reset must start a new state segment")

    uncertainty_available = bool(np.isfinite(state_std).any())
    if not uncertainty_available:
        if metadata["uncertainty_status"] != "uncalibrated_not_available":
            raise ValueError("all-NaN state_std needs explicit unavailable semantics")
    elif not np.isfinite(state_std).all():
        raise ValueError("partially finite state_std is not supported by v1 adapter")
    decision_eligible = bool(metadata.get("oracle_channels_decision_eligible", True))
    if metadata["evidence_class"] == "oracle":
        decision_eligible = False
    uncertainty_trigger_eligible = (
        uncertainty_available
        and metadata["uncertainty_status"] in {"calibrated", "eligible_calibrated"}
        and decision_eligible
    )

    target = torch.device(device)
    graph = {
        "coordinates": torch.from_numpy(coordinates.astype(np.float32)).to(target),
        "areas": torch.from_numpy(areas.astype(np.float32)).to(target),
        "edge_index": torch.from_numpy(edge_index.astype(np.int64)).to(target),
        "edge_attr": torch.from_numpy(edge_attr.astype(np.float32)).to(target),
    }

    def tensor(name: str, dtype: np.dtype | None = None) -> torch.Tensor:
        value = arrays[name]
        if dtype is not None:
            value = value.astype(dtype)
        return torch.from_numpy(value).to(target)

    return RoadObservationStateBundle(
        path=path,
        package_sha256=actual_sha,
        cycles=tensor("cycle", np.int32),
        state_mean=torch.from_numpy(state_mean.astype(np.float32)).to(target),
        state_std=torch.from_numpy(state_std.astype(np.float32)).to(target),
        state_covariance=(
            torch.from_numpy(covariance.astype(np.float32)).to(target)
            if covariance is not None
            else None
        ),
        state_ensemble=(
            torch.from_numpy(ensemble.astype(np.float32)).to(target)
            if ensemble is not None
            else None
        ),
        observed_channel_mask=torch.from_numpy(observed).to(target),
        source_code=torch.from_numpy(source_code.astype(np.uint8)).to(target),
        node_observation_channels=tuple(
            str(value) for value in arrays["node_observation_channels"]
        ),
        node_observation_evidence=tuple(
            str(value) for value in arrays["node_observation_evidence"]
        ),
        node_observation_values=tensor("node_observation_values", np.float32),
        node_observation_mask=tensor("node_observation_mask"),
        global_observation_channels=tuple(
            str(value) for value in arrays["global_observation_channels"]
        ),
        global_observation_evidence=tuple(
            str(value) for value in arrays["global_observation_evidence"]
        ),
        global_observation_values=tensor("global_observation_values", np.float32),
        global_observation_mask=tensor("global_observation_mask"),
        timestamp=timestamps,
        timestamp_mask=torch.from_numpy(timestamp_mask).to(target),
        equivalent_load_index=tensor("equivalent_load_index", np.float64),
        equivalent_load_index_mask=tensor("equivalent_load_index_mask"),
        delta_t=tensor("delta_t", np.float64),
        delta_t_mask=tensor("delta_t_mask"),
        traffic_channels=tuple(str(value) for value in arrays["traffic_channels"]),
        traffic_values=tensor("traffic_values", np.float32),
        traffic_mask=tensor("traffic_mask"),
        environment_channels=tuple(
            str(value) for value in arrays["environment_channels"]
        ),
        environment_values=tensor("environment_values", np.float32),
        environment_mask=tensor("environment_mask"),
        maintenance_reset=torch.from_numpy(reset).to(target),
        maintenance_reset_declared=torch.from_numpy(declared).to(target),
        maintenance_event_id=event_ids,
        state_segment_id=torch.from_numpy(segment.astype(np.int32)).to(target),
        graph=graph,
        metadata=metadata,
        source_field_order=source_fields,
        forecast_field_order=FORECAST_FIELD_ORDER,
        uncertainty_available=uncertainty_available,
        uncertainty_trigger_eligible=uncertainty_trigger_eligible,
        decision_eligible=decision_eligible,
    )


@dataclass(frozen=True)
class Agent2Contracts:
    road_time: Mapping[str, Any]
    horizon: Mapping[str, Any]
    trigger: Mapping[str, Any]
    hashes: Mapping[str, str]


@dataclass(frozen=True)
class Agent1InnovationPacket:
    path: Path
    packet_sha256: str
    source_bundle_sha256: str
    decision_eligible: bool
    decision_eligibility_reason: str
    evidence_class: str
    document: Mapping[str, Any]


def load_agent1_innovation_packet(
    path: Path,
    *,
    expected_bundle_sha256: str,
) -> Agent1InnovationPacket:
    """Load the Agent1-to-Agent2 packet and enforce operational eligibility."""
    path = Path(path)
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("packet_version") != "road_observation_innovation_packet_v1":
        raise ValueError("unsupported Agent 1 innovation packet")
    if document.get("source_bundle_sha256") != expected_bundle_sha256:
        raise ValueError("innovation packet points to a different state bundle")
    for channel in document.get("innovations", {}).values():
        if not channel.get("available", False):
            if channel.get("mask") is not False or channel.get("value") is not None:
                raise ValueError("missing innovation must be null with mask=false")
    oracle = document.get("audit_only_oracle", {})
    if oracle.get("values_exported_to_trigger") is not False:
        raise ValueError("oracle latent values cannot enter an operational trigger")
    return Agent1InnovationPacket(
        path=path,
        packet_sha256=sha256_file(path),
        source_bundle_sha256=expected_bundle_sha256,
        decision_eligible=bool(document.get("decision_eligible", False)),
        decision_eligibility_reason=str(
            document.get("decision_eligibility_reason", "")
        ),
        evidence_class=str(document.get("evidence_class", "")),
        document=document,
    )


def load_agent2_contracts(
    directory: Path,
    *,
    expected_hashes: Mapping[str, str] | None = None,
) -> Agent2Contracts:
    """Load Agent 2 v1 contracts without modifying their field names."""
    directory = Path(directory)
    files = {
        "road_time_mapping_spec.json": AGENT2_TIME_SCHEMA,
        "road_forecast_horizon_spec.json": AGENT2_HORIZON_SCHEMA,
        "observation_trigger_spec.json": AGENT2_TRIGGER_SCHEMA,
    }
    documents: dict[str, Mapping[str, Any]] = {}
    hashes: dict[str, str] = {}
    for name, schema in files.items():
        path = directory / name
        hashes[name] = sha256_file(path)
        if expected_hashes and hashes[name] != expected_hashes.get(name):
            raise ValueError(f"Agent 2 contract hash mismatch for {name}")
        document = json.loads(path.read_text(encoding="utf-8"))
        if document.get("schema") != schema:
            raise ValueError(f"unsupported Agent 2 schema in {name}")
        documents[name] = document
    return Agent2Contracts(
        road_time=documents["road_time_mapping_spec.json"],
        horizon=documents["road_forecast_horizon_spec.json"],
        trigger=documents["observation_trigger_spec.json"],
        hashes=hashes,
    )


def assert_graph_compatibility(
    analysis: RoadObservationStateBundle,
    graph: Mapping[str, torch.Tensor],
) -> None:
    """Require byte-equivalent common graph arrays before prediction."""
    for name in ("coordinates", "areas", "edge_index", "edge_attr"):
        if name not in graph:
            raise ValueError(f"forecast graph lacks {name}")
        left = analysis.graph[name].detach().cpu()
        right = graph[name].detach().cpu().to(left.dtype)
        if left.shape != right.shape or not torch.equal(left, right):
            raise ValueError(f"forecast graph differs from Agent 1 {name}")


def adapt_bundle_to_observation_sequence(
    analysis: RoadObservationStateBundle,
    history_states: torch.Tensor,
    *,
    layout: RoadFeatureLayout,
    asset_id: str,
    history_delta_t: torch.Tensor | None = None,
    history_delta_t_mask: torch.Tensor | None = None,
) -> RoadObservationSequence:
    """Align an Agent 1 bundle to a model history without inventing sensors.

    ``observed_channel_mask`` is deliberately absent from this mapping.  It is
    latent assimilation attribution and remains diagnostic metadata on the
    bundle.  Only independent node/global observation arrays populate the
    measurement tensors.
    """
    if history_states.ndim != 3 or history_states.shape[-1] != 4:
        raise ValueError("history_states must have shape [time, elements, 4]")
    bundle_time, elements, _ = analysis.state_mean.shape
    if history_states.shape[1:] != analysis.state_mean.shape[1:]:
        raise ValueError("history mesh differs from Agent 1 analysis mesh")
    if bundle_time > len(history_states):
        raise ValueError("bundle history is longer than the model history")
    dimensions = (
        (layout.node_observation_dim, analysis.node_observation_values.shape[-1]),
        (layout.global_observation_dim, analysis.global_observation_values.shape[-1]),
        (layout.traffic_dim, analysis.traffic_values.shape[-1]),
        (layout.environment_dim, analysis.environment_values.shape[-1]),
        (layout.maintenance_dim, 1),
    )
    if any(expected != actual for expected, actual in dimensions):
        raise ValueError("RoadFeatureLayout does not match Agent 1 channel registry")
    history = history_states.clone()
    history[-bundle_time:] = analysis.state_mean.to(history)
    time = len(history)
    tail = slice(time - bundle_time, time)
    node = history.new_full((time, elements, layout.node_observation_dim), torch.nan)
    node_mask = torch.zeros_like(node, dtype=torch.bool)
    node[tail] = analysis.node_observation_values.to(node)
    node_mask[tail] = analysis.node_observation_mask.to(node.device)
    global_values = history.new_full((time, layout.global_observation_dim), torch.nan)
    global_mask = torch.zeros_like(global_values, dtype=torch.bool)
    global_values[tail] = analysis.global_observation_values.to(global_values)
    global_mask[tail] = analysis.global_observation_mask.to(global_mask.device)
    traffic = history.new_full((time, layout.traffic_dim), torch.nan)
    traffic_mask = torch.zeros_like(traffic, dtype=torch.bool)
    traffic[tail] = analysis.traffic_values.to(traffic)
    traffic_mask[tail] = analysis.traffic_mask.to(traffic_mask.device)
    environment = history.new_full((time, layout.environment_dim), torch.nan)
    environment_mask = torch.zeros_like(environment, dtype=torch.bool)
    environment[tail] = analysis.environment_values.to(environment)
    environment_mask[tail] = analysis.environment_mask.to(environment_mask.device)
    delta_t = history.new_full((time, 1), torch.nan)
    delta_t_mask = torch.zeros_like(delta_t, dtype=torch.bool)
    if history_delta_t is not None:
        if history_delta_t.shape != (time, 1):
            raise ValueError("history_delta_t must have shape [history, 1]")
        delta_t = history_delta_t.to(history).clone()
        if history_delta_t_mask is None:
            delta_t_mask = torch.ones_like(delta_t, dtype=torch.bool)
        else:
            if history_delta_t_mask.shape != (time, 1):
                raise ValueError("history_delta_t_mask must match history_delta_t")
            delta_t_mask = history_delta_t_mask.to(history.device).clone()
    delta_t[tail, 0] = analysis.delta_t.to(delta_t)
    delta_t_mask[tail, 0] = analysis.delta_t_mask.to(delta_t_mask.device)
    equivalent_load = history.new_full((time, 1), torch.nan)
    equivalent_load_mask = torch.zeros_like(equivalent_load, dtype=torch.bool)
    equivalent_load[tail, 0] = analysis.equivalent_load_index.to(equivalent_load)
    equivalent_load_mask[tail, 0] = analysis.equivalent_load_index_mask.to(
        equivalent_load_mask.device
    )
    maintenance = history.new_zeros((time, 1))
    maintenance_state_reset = torch.zeros((time, 1), dtype=torch.bool)
    maintenance_reset_declared = torch.zeros((time, 1), dtype=torch.bool)
    maintenance[tail, 0] = analysis.maintenance_reset.to(maintenance)
    maintenance_state_reset[tail, 0] = analysis.maintenance_reset.to(
        maintenance_state_reset.device
    )
    maintenance_reset_declared[tail, 0] = analysis.maintenance_reset_declared.to(
        maintenance_reset_declared.device
    )
    timestamp = [""] * time
    timestamp[time - bundle_time :] = analysis.timestamp
    timestamp_mask = torch.zeros((time, 1), dtype=torch.bool)
    timestamp_mask[tail, 0] = analysis.timestamp_mask.to(timestamp_mask.device)
    event_ids = [""] * time
    event_ids[time - bundle_time :] = analysis.maintenance_event_id
    segment = torch.zeros(time, dtype=torch.int32)
    segment[tail] = analysis.state_segment_id.to(segment.device)
    provenance = {
        "oracle": "oracle",
        "synthetic": "synthetic",
        "real": "real",
    }.get(str(analysis.metadata["evidence_class"]))
    if provenance is None:
        raise ValueError("unknown Agent 1 evidence class")
    return RoadObservationSequence(
        analysis_states=history,
        node_observations=node,
        node_observation_mask=node_mask,
        global_observations=global_values,
        global_observation_mask=global_mask,
        delta_t=delta_t,
        traffic=traffic,
        traffic_mask=traffic_mask,
        environment=environment,
        environment_mask=environment_mask,
        maintenance=maintenance,
        maintenance_state_reset=maintenance_state_reset,
        provenance=provenance,
        observation_space_version=layout.observation_space_version,
        asset_id=asset_id,
        delta_t_mask=delta_t_mask,
        equivalent_load_index=equivalent_load,
        equivalent_load_index_mask=equivalent_load_mask,
        timestamp=tuple(timestamp),
        timestamp_mask=timestamp_mask,
        maintenance_reset_declared=maintenance_reset_declared,
        maintenance_event_id=tuple(event_ids),
        state_segment_id=segment,
    )


@dataclass(frozen=True)
class TriggerEvidence:
    model_internal: Mapping[str, float | None] = field(default_factory=dict)
    observation_innovation_warning: bool = False
    observation_innovation_hard: bool = False
    exogenous_ood_warning: bool = False
    exogenous_ood_hard: bool = False
    data_quality_warning: bool = False
    data_quality_hard: bool = False
    inspection_overdue: bool = False
    maintenance_changes_state: bool = False
    decision_eligible: bool = True
    eligibility_reason: str = ""


@dataclass(frozen=True)
class TriggerDecision:
    action: str
    request_observation: bool
    stop_forecast: bool
    candidate_model_warning: bool
    consecutive_model_warnings: int
    warning_signals: tuple[str, ...]
    hard_signals: tuple[str, ...]
    unavailable_signals: tuple[str, ...]
    status: str = "candidate_diagnostic_not_road_validated"


class Agent2TriggerEvaluator:
    """Stateful implementation of the frozen Agent 2 diagnostic trigger."""

    def __init__(self, trigger_contract: Mapping[str, Any]) -> None:
        if trigger_contract.get("schema") != AGENT2_TRIGGER_SCHEMA:
            raise ValueError("trigger contract is not road_observation_trigger_v1")
        self.contract = trigger_contract
        self.consecutive_model_warnings = 0

    def reset(self) -> None:
        self.consecutive_model_warnings = 0

    def evaluate(self, evidence: TriggerEvidence) -> TriggerDecision:
        envelopes = self.contract["current_offline_rule"]["envelopes"]
        if not evidence.decision_eligible:
            self.consecutive_model_warnings = 0
            system_stop = (
                evidence.maintenance_changes_state or evidence.inspection_overdue
            )
            return TriggerDecision(
                action=("stop_and_request_observation" if system_stop else "continue"),
                request_observation=system_stop,
                stop_forecast=system_stop,
                candidate_model_warning=False,
                consecutive_model_warnings=0,
                warning_signals=(),
                hard_signals=(),
                unavailable_signals=tuple(sorted(envelopes)),
                status="rejected_ineligible_operational_evidence",
            )
        warnings: list[str] = []
        hard: list[str] = []
        unavailable: list[str] = []
        for name, envelope in envelopes.items():
            value = evidence.model_internal.get(name)
            if value is None:
                unavailable.append(name)
                continue
            scale = float(envelope["scale"])
            if scale <= 0:
                raise ValueError(f"invalid frozen trigger scale for {name}")
            z = abs(float(value) - float(envelope["centre"])) / scale
            if z >= float(envelope["hard_z"]):
                hard.append(name)
            if z >= float(envelope["warn_z"]):
                warnings.append(name)
        candidate = len(warnings) >= 2 or len(hard) >= 1
        self.consecutive_model_warnings = (
            self.consecutive_model_warnings + 1 if candidate else 0
        )
        observation_warning = (
            evidence.observation_innovation_warning
            or evidence.exogenous_ood_warning
            or evidence.data_quality_warning
        )
        hard_gate = (
            evidence.observation_innovation_hard
            or evidence.exogenous_ood_hard
            or evidence.data_quality_hard
            or evidence.inspection_overdue
            or evidence.maintenance_changes_state
        )
        model_stop = len(hard) >= 2 or self.consecutive_model_warnings >= 2
        stop = hard_gate or model_stop
        request = hard_gate or (candidate and observation_warning) or model_stop
        if stop:
            action = "stop_and_request_observation"
        elif request:
            action = "request_observation"
        else:
            action = "continue"
        return TriggerDecision(
            action=action,
            request_observation=request,
            stop_forecast=stop,
            candidate_model_warning=candidate,
            consecutive_model_warnings=self.consecutive_model_warnings,
            warning_signals=tuple(sorted(warnings)),
            hard_signals=tuple(sorted(hard)),
            unavailable_signals=tuple(sorted(unavailable)),
        )


@dataclass(frozen=True)
class LongHorizonRisk:
    status: str
    hazard_probability: torch.Tensor | None
    cumulative_event_probability: torch.Tensor | None
    rul_location: torch.Tensor | None
    rul_scale: torch.Tensor | None


@dataclass(frozen=True)
class ClosedLoopForecast:
    contract_id: str
    origin_id: str
    analysis_sha256: str
    observation_mask_sha256: str
    scenario_id: str
    scenario_sha256: str
    state_horizon: int
    state_predictions: torch.Tensor | None
    state_output_status: str
    trigger: TriggerDecision
    long_horizon_risk: LongHorizonRisk
    evidence_class: str


class RoadClosedLoopForecaster:
    """Orchestrate analysis, h1-h3 forecast, trigger, and re-assimilation."""

    def __init__(
        self,
        model: RoadObservationAwareForecaster,
        *,
        graph: Mapping[str, torch.Tensor],
        state_statistics: StateStatistics,
        road_statistics: RoadFeatureStatistics,
        trigger_contract: Mapping[str, Any],
        state_heads_trained: bool,
        risk_heads_trained: bool,
        evidence_class: str,
    ) -> None:
        self.model = model
        self.graph = graph
        self.state_statistics = state_statistics
        self.road_statistics = road_statistics
        self.trigger_evaluator = Agent2TriggerEvaluator(trigger_contract)
        self.state_heads_trained = state_heads_trained
        self.risk_heads_trained = risk_heads_trained
        self.evidence_class = evidence_class
        self.analysis: RoadObservationStateBundle | None = None
        self.innovation_packet: Agent1InnovationPacket | None = None
        self.operational_evidence_eligible = False

    def assimilate(
        self,
        analysis: RoadObservationStateBundle,
        innovation_packet: Agent1InnovationPacket | None = None,
    ) -> None:
        assert_graph_compatibility(analysis, self.graph)
        if (
            innovation_packet is not None
            and innovation_packet.source_bundle_sha256 != analysis.package_sha256
        ):
            raise ValueError("innovation packet does not match the analysis bundle")
        self.analysis = analysis
        self.innovation_packet = innovation_packet
        packet_eligible = (
            innovation_packet.decision_eligible
            if innovation_packet is not None
            else analysis.decision_eligible
        )
        self.operational_evidence_eligible = (
            analysis.decision_eligible and packet_eligible
        )
        self.trigger_evaluator.reset()

    def forecast(
        self,
        sequence: RoadObservationSequence,
        scenario: RoadFutureScenario,
        *,
        trigger_evidence: TriggerEvidence | None = None,
        state_horizon: int = 3,
        recurrent_ssm: bool = False,
    ) -> ClosedLoopForecast:
        if self.analysis is None:
            raise RuntimeError("assimilate a frozen Agent 1 state before forecasting")
        if state_horizon < 1 or state_horizon > 3:
            raise ValueError("field forecasts are restricted to direct h1-h3")
        sequence.validate(self.model.layout)
        scenario.validate(self.model.layout)
        if not torch.equal(
            sequence.analysis_states[-1].detach().cpu(),
            self.analysis.state_mean[-1]
            .detach()
            .cpu()
            .to(sequence.analysis_states.dtype),
        ):
            raise ValueError("forecast origin is not the frozen assimilated state")
        evidence = trigger_evidence or TriggerEvidence()
        if not self.operational_evidence_eligible:
            evidence = replace(
                evidence,
                decision_eligible=False,
                eligibility_reason=(
                    "Agent1 bundle/innovation packet is not operationally eligible"
                ),
            )
        if (
            scenario.maintenance.abs().sum() > 0
            and not evidence.maintenance_changes_state
        ):
            evidence = replace(evidence, maintenance_changes_state=True)
        trigger = self.trigger_evaluator.evaluate(evidence)
        scenario_document = {
            "scenario_id": scenario.scenario_id,
            "delta_t": scenario.delta_t.detach().cpu().tolist(),
            "traffic_mask": scenario.traffic_mask.detach().cpu().tolist(),
            "environment_mask": scenario.environment_mask.detach().cpu().tolist(),
            "maintenance": scenario.maintenance.detach().cpu().tolist(),
            "maintenance_model_id": scenario.maintenance_model_id,
        }
        if trigger.stop_forecast:
            state_predictions = None
            state_status = "withheld_trigger_stop"
            raw_output = None
        else:
            with torch.no_grad():
                raw_output = self.model(
                    sequence,
                    scenario,
                    self.graph,
                    self.state_statistics,
                    self.road_statistics,
                    state_horizon=state_horizon,
                    recurrent_ssm=recurrent_ssm,
                )
            state_predictions = raw_output.state_predictions
            state_status = (
                "available_trained_direct_h1_h3"
                if self.state_heads_trained
                else "tooling_only_untrained_direct_heads"
            )
        risk = self._risk_output(raw_output)
        return ClosedLoopForecast(
            contract_id=FORECAST_CONTRACT,
            origin_id=self.analysis.origin_id,
            analysis_sha256=self.analysis.package_sha256,
            observation_mask_sha256=self.analysis.mask_sha256,
            scenario_id=scenario.scenario_id,
            scenario_sha256=stable_json_sha256(scenario_document),
            state_horizon=state_horizon,
            state_predictions=state_predictions,
            state_output_status=state_status,
            trigger=trigger,
            long_horizon_risk=risk,
            evidence_class=self.evidence_class,
        )

    def _risk_output(self, output: RoadForecastOutput | None) -> LongHorizonRisk:
        if not self.risk_heads_trained or output is None:
            return LongHorizonRisk(
                status="unavailable_untrained",
                hazard_probability=None,
                cumulative_event_probability=None,
                rul_location=None,
                rul_scale=None,
            )
        return LongHorizonRisk(
            status="available_trained_scenario_conditioned",
            hazard_probability=output.hazard_probability,
            cumulative_event_probability=output.cumulative_event_probability,
            rul_location=output.rul_location,
            rul_scale=output.rul_scale,
        )

    def re_assimilate(
        self,
        analysis: RoadObservationStateBundle,
        innovation_packet: Agent1InnovationPacket | None = None,
    ) -> None:
        self.assimilate(analysis, innovation_packet)


def contract_compatibility_rows() -> Sequence[Mapping[str, str]]:
    """Machine-readable compatibility matrix used by docs and tests."""
    return (
        {
            "producer": "Agent1",
            "source_field": "state_mean[:,:,damage]",
            "adapter": "identity",
            "forecast_field": "z_analysis[:,damage]",
            "status": "compatible_v1",
        },
        {
            "producer": "Agent1",
            "source_field": "state_mean[:,:,fatigue_history]",
            "adapter": "canonical identity; legacy alpha_bar is an explicit alias",
            "forecast_field": "z_analysis[:,fatigue_history]",
            "status": "compatible_v1",
        },
        {
            "producer": "Agent1",
            "source_field": "state_std all NaN",
            "adapter": "preserve unavailable; never zero-fill",
            "forecast_field": "analysis_uncertainty",
            "status": "unavailable_uncalibrated",
        },
        {
            "producer": "Agent1",
            "source_field": "observed_channel_mask",
            "adapter": "retain as latent assimilation provenance only",
            "forecast_field": "assimilation diagnostics",
            "status": "not_a_measurement_mask",
        },
        {
            "producer": "Agent1",
            "source_field": "node/global_observation_values and masks",
            "adapter": "identity with NaN plus false-mask preservation",
            "forecast_field": "node/global observations",
            "status": "compatible_v1",
        },
        {
            "producer": "Agent1",
            "source_field": "decision_eligible=false",
            "adapter": "reject as operational trigger evidence",
            "forecast_field": "TriggerDecision",
            "status": "audit_only",
        },
        {
            "producer": "Agent2",
            "source_field": "calibrated_equivalent_load_block_with_caps",
            "adapter": "delta_t and scenario context",
            "forecast_field": "RoadFutureScenario",
            "status": "interface_only_uncalibrated",
        },
        {
            "producer": "Agent2",
            "source_field": "current_offline_rule.envelopes",
            "adapter": "Agent2TriggerEvaluator",
            "forecast_field": "TriggerDecision",
            "status": "candidate_diagnostic_not_road_validated",
        },
    )
