"""Closed-loop road fracture forecast API and frozen-contract adapters.

The API connects three independently versioned interfaces without renaming
their fields in place:

* Agent 1 ``road_assimilated_state_v1`` analysis bundles;
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


AGENT1_SCHEMA = "road_assimilated_state_v1"
AGENT2_TIME_SCHEMA = "road_time_mapping_v1"
AGENT2_HORIZON_SCHEMA = "road_forecast_horizon_v1"
AGENT2_TRIGGER_SCHEMA = "road_observation_trigger_v1"
FORECAST_CONTRACT = "road_forecast_input_contract_v1"
AGENT1_FIELD_ORDER = (
    "damage",
    "alpha_bar",
    "fatigue_degradation",
    "log10_psi_raw",
)
FORECAST_FIELD_ORDER = (
    "damage",
    "fatigue_history",
    "fatigue_degradation",
    "log10_psi_raw",
)
AGENT1_TO_FORECAST_FIELD = {
    "damage": "damage",
    "alpha_bar": "fatigue_history",
    "fatigue_degradation": "fatigue_degradation",
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
class Agent1AssimilatedState:
    """Validated Agent 1 analysis bundle in Agent 3 canonical field order."""

    path: Path
    package_sha256: str
    cycle: int
    state_mean: torch.Tensor
    state_std: torch.Tensor
    observed_channel_mask: torch.Tensor
    source_code: torch.Tensor
    graph: Mapping[str, torch.Tensor]
    metadata: Mapping[str, Any]
    source_field_order: tuple[str, ...]
    forecast_field_order: tuple[str, ...]
    uncertainty_available: bool

    @property
    def mask_sha256(self) -> str:
        return tensor_sha256(self.observed_channel_mask)

    @property
    def origin_id(self) -> str:
        return f"{self.metadata['trajectory_id']}:c{self.cycle}"


def _scalar(data: np.lib.npyio.NpzFile, name: str) -> Any:
    return np.asarray(data[name]).reshape(-1)[0].item()


def load_agent1_assimilated_state(
    path: Path,
    *,
    expected_sha256: str | None = None,
    device: torch.device | str = "cpu",
) -> Agent1AssimilatedState:
    """Load and strictly validate a frozen Agent 1 v1 NPZ package."""
    path = Path(path)
    actual_sha = sha256_file(path)
    if expected_sha256 is not None and actual_sha != expected_sha256:
        raise ValueError("Agent 1 assimilated-state SHA-256 mismatch")
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
            "state_std",
            "observed_channel_mask",
            "source_code",
        }
        missing = sorted(required - set(data.files))
        if missing:
            raise ValueError(f"Agent 1 package lacks arrays: {missing}")
        schema = str(_scalar(data, "schema_version"))
        if schema != AGENT1_SCHEMA:
            raise ValueError(f"unsupported Agent 1 schema {schema!r}")
        source_fields = tuple(str(value) for value in np.asarray(data["state_fields"]))
        if source_fields != AGENT1_FIELD_ORDER:
            raise ValueError(
                "Agent 1 state_fields changed; use an explicit versioned adapter"
            )
        metadata = json.loads(str(_scalar(data, "metadata_json")))
        cycle = int(_scalar(data, "cycle"))
        arrays = {
            name: np.asarray(data[name])
            for name in required
            if name not in {"schema_version", "metadata_json", "cycle", "state_fields"}
        }

    coordinates = arrays["coordinates"]
    areas = arrays["areas"]
    edge_index = arrays["edge_index"]
    edge_attr = arrays["edge_attr"]
    state_mean = arrays["state_mean"]
    state_std = arrays["state_std"]
    observed = arrays["observed_channel_mask"]
    source_code = arrays["source_code"]
    elements = len(coordinates)
    expected_shapes = {
        "coordinates": (elements, 2),
        "areas": (elements,),
        "state_mean": (elements, 4),
        "state_std": (elements, 4),
        "observed_channel_mask": (elements, 4),
        "source_code": (elements, 4),
    }
    for name, shape in expected_shapes.items():
        if arrays[name].shape != shape:
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
        "trajectory_id",
        "source_evidence_class",
        "observation_operator_id",
        "prior_id",
        "physics_family",
        "fem_eta",
        "uncertainty_status",
        "real_road_compatible",
        "input_sha256",
    }
    missing_metadata = sorted(metadata_required - set(metadata))
    if missing_metadata:
        raise ValueError(f"Agent 1 metadata missing: {missing_metadata}")
    if float(metadata["fem_eta"]) != 0.0:
        raise ValueError("this compatibility smoke requires FEM eta=0")
    uncertainty_available = bool(np.isfinite(state_std).any())
    if not uncertainty_available:
        if metadata["uncertainty_status"] != "uncalibrated_not_available":
            raise ValueError("all-NaN state_std needs explicit unavailable semantics")
    elif not np.isfinite(state_std).all():
        raise ValueError("partially finite state_std is not supported by v1 adapter")

    target = torch.device(device)
    graph = {
        "coordinates": torch.from_numpy(coordinates.astype(np.float32)).to(target),
        "areas": torch.from_numpy(areas.astype(np.float32)).to(target),
        "edge_index": torch.from_numpy(edge_index.astype(np.int64)).to(target),
        "edge_attr": torch.from_numpy(edge_attr.astype(np.float32)).to(target),
    }
    return Agent1AssimilatedState(
        path=path,
        package_sha256=actual_sha,
        cycle=cycle,
        state_mean=torch.from_numpy(state_mean.astype(np.float32)).to(target),
        state_std=torch.from_numpy(state_std.astype(np.float32)).to(target),
        observed_channel_mask=torch.from_numpy(observed).to(target),
        source_code=torch.from_numpy(source_code.astype(np.uint8)).to(target),
        graph=graph,
        metadata=metadata,
        source_field_order=source_fields,
        forecast_field_order=FORECAST_FIELD_ORDER,
        uncertainty_available=uncertainty_available,
    )


@dataclass(frozen=True)
class Agent2Contracts:
    road_time: Mapping[str, Any]
    horizon: Mapping[str, Any]
    trigger: Mapping[str, Any]
    hashes: Mapping[str, str]


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
    analysis: Agent1AssimilatedState,
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


def adapt_agent1_to_observation_sequence(
    analysis: Agent1AssimilatedState,
    history_states: torch.Tensor,
    *,
    layout: RoadFeatureLayout,
    delta_t: torch.Tensor,
    asset_id: str,
    provenance: str = "oracle",
    maintenance: torch.Tensor | None = None,
    maintenance_state_reset: torch.Tensor | None = None,
) -> RoadObservationSequence:
    """Create the Agent 3 sequence through an explicit Agent 1 adapter.

    The last history state is replaced by the frozen analysis state.  Directly
    observed Agent 1 channels are passed as node observations; missing channels
    remain NaN with a false mask.  No latent field is relabelled as a road
    sensor measurement.
    """
    if layout.node_observation_dim != 4:
        raise ValueError("Agent 1 v1 adapter requires four node observation channels")
    if history_states.ndim != 3 or history_states.shape[-1] != 4:
        raise ValueError("history_states must have shape [time, elements, 4]")
    if history_states.shape[1:] != analysis.state_mean.shape:
        raise ValueError("history mesh differs from Agent 1 analysis mesh")
    history = history_states.clone()
    history[-1] = analysis.state_mean.to(history)
    time, elements, _ = history.shape
    if delta_t.shape != (time, 1):
        raise ValueError("delta_t must match history length")
    node = history.new_full((time, elements, 4), torch.nan)
    node_mask = torch.zeros_like(node, dtype=torch.bool)
    last_mask = analysis.observed_channel_mask.to(node.device)
    node[-1][last_mask] = analysis.state_mean.to(node)[last_mask]
    node_mask[-1] = last_mask
    global_values = history.new_empty((time, layout.global_observation_dim))
    global_mask = torch.zeros_like(global_values, dtype=torch.bool)
    traffic = history.new_full((time, layout.traffic_dim), torch.nan)
    traffic_mask = torch.zeros_like(traffic, dtype=torch.bool)
    environment = history.new_full((time, layout.environment_dim), torch.nan)
    environment_mask = torch.zeros_like(environment, dtype=torch.bool)
    if maintenance is None:
        maintenance = history.new_zeros((time, layout.maintenance_dim))
    if maintenance_state_reset is None:
        maintenance_state_reset = torch.zeros((time, 1), dtype=torch.bool)
    return RoadObservationSequence(
        analysis_states=history,
        node_observations=node,
        node_observation_mask=node_mask,
        global_observations=global_values,
        global_observation_mask=global_mask,
        delta_t=delta_t.to(history),
        traffic=traffic,
        traffic_mask=traffic_mask,
        environment=environment,
        environment_mask=environment_mask,
        maintenance=maintenance.to(history),
        maintenance_state_reset=maintenance_state_reset.to(history.device),
        provenance=provenance,
        observation_space_version=layout.observation_space_version,
        asset_id=asset_id,
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
        self.analysis: Agent1AssimilatedState | None = None

    def assimilate(self, analysis: Agent1AssimilatedState) -> None:
        assert_graph_compatibility(analysis, self.graph)
        self.analysis = analysis
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
            self.analysis.state_mean.detach().cpu().to(sequence.analysis_states.dtype),
        ):
            raise ValueError("forecast origin is not the frozen assimilated state")
        evidence = trigger_evidence or TriggerEvidence()
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

    def re_assimilate(self, analysis: Agent1AssimilatedState) -> None:
        self.assimilate(analysis)


def contract_compatibility_rows() -> Sequence[Mapping[str, str]]:
    """Machine-readable compatibility matrix used by docs and tests."""
    return (
        {
            "producer": "Agent1",
            "source_field": "state_mean[:,damage]",
            "adapter": "identity",
            "forecast_field": "z_analysis[:,damage]",
            "status": "compatible_v1",
        },
        {
            "producer": "Agent1",
            "source_field": "state_mean[:,alpha_bar]",
            "adapter": "explicit alpha_bar_to_fatigue_history",
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
            "adapter": "identity plus explicit missing values",
            "forecast_field": "node_observation_mask",
            "status": "compatible_v1",
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
