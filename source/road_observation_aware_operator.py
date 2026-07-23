"""Observation-aware graph forecasting contract for road fracture digital twins.

This module is deliberately a *contract and model interface*, not evidence that
the current single FEM trajectory generalises to roads.  It keeps three data
classes separate throughout the computation:

* analysed latent state (FEM/PIDL state or an assimilated estimate),
* observable node/global measurements with explicit missingness masks, and
* known exogenous traffic, environment, elapsed-time, and maintenance inputs.

The formal backbones are Markov graph, TCN, and diagonal SSM.  Transformer is
retained only as a secondary candidate.  The model exposes both direct
short-horizon state forecasts and longer-horizon probabilistic risk outputs so
that long-range road prognosis is not silently implemented as unlimited
one-step recursion.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import torch
import torch.nn as nn
import torch.nn.functional as F

from fem_mechanism_operator import StateStatistics
from temporal_mesh_operator import (
    DiagonalSSMTemporal,
    FactorizedMeshEncoder,
    TemporalMeshOperator,
    apply_directional_state_update,
    build_temporal_module,
)


FORMAL_ROAD_FAMILIES = ("markov", "tcn", "diagonal_ssm")
SECONDARY_ROAD_FAMILIES = ("transformer",)
ROAD_PROVENANCE = ("synthetic", "real", "oracle")


def _mlp(sizes: list[int]) -> nn.Sequential:
    layers: list[nn.Module] = []
    for index, (input_dim, output_dim) in enumerate(zip(sizes[:-1], sizes[1:])):
        layers.append(nn.Linear(input_dim, output_dim))
        if index < len(sizes) - 2:
            layers.append(nn.GELU())
    return nn.Sequential(*layers)


def _require_shape(name: str, value: torch.Tensor, expected: tuple[int, ...]) -> None:
    if tuple(value.shape) != expected:
        raise ValueError(f"{name} must have shape {expected}, got {tuple(value.shape)}")


def _require_mask(name: str, values: torch.Tensor, mask: torch.Tensor) -> None:
    if mask.dtype != torch.bool:
        raise ValueError(f"{name} mask must be boolean")
    if values.shape != mask.shape:
        raise ValueError(f"{name} values and mask must have the same shape")
    if mask.any() and not torch.isfinite(values[mask]).all():
        raise ValueError(f"{name} contains non-finite observed values")


@dataclass(frozen=True)
class RoadFeatureLayout:
    """Versioned channel counts shared by Agent 1/2 and the forecaster."""

    node_observation_dim: int
    global_observation_dim: int
    traffic_dim: int
    environment_dim: int
    maintenance_dim: int
    observation_space_version: str = "road_obs_v1"

    def __post_init__(self) -> None:
        dimensions = (
            self.node_observation_dim,
            self.global_observation_dim,
            self.traffic_dim,
            self.environment_dim,
            self.maintenance_dim,
        )
        if any(dimension < 0 for dimension in dimensions):
            raise ValueError("road feature dimensions must be non-negative")
        if not self.observation_space_version:
            raise ValueError("observation_space_version must be non-empty")

    @property
    def history_node_dim(self) -> int:
        return 2 * self.node_observation_dim

    @property
    def history_global_dim(self) -> int:
        # elapsed time + value/mask pairs + maintenance + explicit reset flag
        return (
            1
            + 2 * self.global_observation_dim
            + 2 * self.traffic_dim
            + 2 * self.environment_dim
            + self.maintenance_dim
            + 1
        )

    @property
    def future_context_dim(self) -> int:
        return (
            1
            + 2 * self.traffic_dim
            + 2 * self.environment_dim
            + self.maintenance_dim
        )


@dataclass(frozen=True)
class RoadObservationSequence:
    """History available at forecast time.

    Missing values may be NaN only where the corresponding mask is false.  A
    `real` provenance label means the observation operator has already mapped
    raw sensor data into the declared observation space; it does not imply that
    latent phase-field channels were measured directly.
    """

    analysis_states: torch.Tensor
    node_observations: torch.Tensor
    node_observation_mask: torch.Tensor
    global_observations: torch.Tensor
    global_observation_mask: torch.Tensor
    delta_t: torch.Tensor
    traffic: torch.Tensor
    traffic_mask: torch.Tensor
    environment: torch.Tensor
    environment_mask: torch.Tensor
    maintenance: torch.Tensor
    maintenance_state_reset: torch.Tensor
    provenance: str
    observation_space_version: str
    asset_id: str

    def validate(self, layout: RoadFeatureLayout) -> None:
        if self.analysis_states.ndim != 3 or self.analysis_states.shape[-1] != 4:
            raise ValueError("analysis_states must have shape [time, elements, 4]")
        if not torch.isfinite(self.analysis_states).all():
            raise ValueError("analysis_states must be finite")
        time, elements, _ = self.analysis_states.shape
        _require_shape(
            "node_observations",
            self.node_observations,
            (time, elements, layout.node_observation_dim),
        )
        _require_shape(
            "global_observations",
            self.global_observations,
            (time, layout.global_observation_dim),
        )
        _require_shape("delta_t", self.delta_t, (time, 1))
        _require_shape("traffic", self.traffic, (time, layout.traffic_dim))
        _require_shape(
            "environment", self.environment, (time, layout.environment_dim)
        )
        _require_shape(
            "maintenance", self.maintenance, (time, layout.maintenance_dim)
        )
        _require_shape(
            "maintenance_state_reset", self.maintenance_state_reset, (time, 1)
        )
        _require_mask(
            "node observations", self.node_observations, self.node_observation_mask
        )
        _require_mask(
            "global observations",
            self.global_observations,
            self.global_observation_mask,
        )
        _require_mask("traffic", self.traffic, self.traffic_mask)
        _require_mask("environment", self.environment, self.environment_mask)
        if not torch.isfinite(self.delta_t).all() or (self.delta_t < 0).any():
            raise ValueError("delta_t must be finite and non-negative")
        if time > 1 and (self.delta_t[1:] <= 0).any():
            raise ValueError("delta_t must be positive after the first inspection")
        if not torch.isfinite(self.maintenance).all():
            raise ValueError("maintenance features must be finite")
        if self.maintenance_state_reset.dtype != torch.bool:
            raise ValueError("maintenance_state_reset must be boolean")
        maintenance_event = self.maintenance.abs().sum(dim=-1) > 0
        if (
            maintenance_event.any()
            and not self.maintenance_state_reset[maintenance_event].all()
        ):
            raise ValueError(
                "a historical maintenance event requires an explicit "
                "post-maintenance state reset"
            )
        if self.provenance not in ROAD_PROVENANCE:
            raise ValueError(f"provenance must be one of {ROAD_PROVENANCE}")
        if self.observation_space_version != layout.observation_space_version:
            raise ValueError(
                "observation-space version does not match the model layout"
            )
        if not self.asset_id:
            raise ValueError("asset_id must be non-empty")


@dataclass(frozen=True)
class RoadFutureScenario:
    """Known or hypothesised future traffic/environment scenario."""

    delta_t: torch.Tensor
    traffic: torch.Tensor
    traffic_mask: torch.Tensor
    environment: torch.Tensor
    environment_mask: torch.Tensor
    maintenance: torch.Tensor
    scenario_id: str
    maintenance_model_id: str = ""

    def validate(self, layout: RoadFeatureLayout) -> None:
        if self.delta_t.ndim != 2 or self.delta_t.shape[1] != 1:
            raise ValueError("future delta_t must have shape [horizon, 1]")
        horizon = len(self.delta_t)
        _require_shape("future traffic", self.traffic, (horizon, layout.traffic_dim))
        _require_shape(
            "future environment",
            self.environment,
            (horizon, layout.environment_dim),
        )
        _require_shape(
            "future maintenance",
            self.maintenance,
            (horizon, layout.maintenance_dim),
        )
        _require_mask("future traffic", self.traffic, self.traffic_mask)
        _require_mask(
            "future environment", self.environment, self.environment_mask
        )
        if horizon == 0:
            raise ValueError("future scenario must contain at least one interval")
        if not torch.isfinite(self.delta_t).all() or (self.delta_t <= 0).any():
            raise ValueError("future delta_t must be finite and positive")
        if not torch.isfinite(self.maintenance).all():
            raise ValueError("future maintenance features must be finite")
        if self.maintenance.abs().sum() > 0 and not self.maintenance_model_id:
            raise ValueError(
                "a non-zero future maintenance scenario needs maintenance_model_id"
            )
        if not self.scenario_id:
            raise ValueError("scenario_id must be non-empty")


@dataclass(frozen=True)
class RoadFeatureStatistics:
    """Training-only feature statistics; identity statistics support smoke tests."""

    node_mean: torch.Tensor
    node_std: torch.Tensor
    global_mean: torch.Tensor
    global_std: torch.Tensor
    traffic_mean: torch.Tensor
    traffic_std: torch.Tensor
    environment_mean: torch.Tensor
    environment_std: torch.Tensor
    log_delta_t_mean: torch.Tensor
    log_delta_t_std: torch.Tensor

    @classmethod
    def identity(cls, layout: RoadFeatureLayout) -> "RoadFeatureStatistics":
        def zeros(size: int) -> torch.Tensor:
            return torch.zeros(size)

        def ones(size: int) -> torch.Tensor:
            return torch.ones(size)

        return cls(
            node_mean=zeros(layout.node_observation_dim),
            node_std=ones(layout.node_observation_dim),
            global_mean=zeros(layout.global_observation_dim),
            global_std=ones(layout.global_observation_dim),
            traffic_mean=zeros(layout.traffic_dim),
            traffic_std=ones(layout.traffic_dim),
            environment_mean=zeros(layout.environment_dim),
            environment_std=ones(layout.environment_dim),
            log_delta_t_mean=torch.zeros(1),
            log_delta_t_std=torch.ones(1),
        )

    def validate(self, layout: RoadFeatureLayout) -> None:
        pairs = (
            ("node", self.node_mean, self.node_std, layout.node_observation_dim),
            (
                "global",
                self.global_mean,
                self.global_std,
                layout.global_observation_dim,
            ),
            ("traffic", self.traffic_mean, self.traffic_std, layout.traffic_dim),
            (
                "environment",
                self.environment_mean,
                self.environment_std,
                layout.environment_dim,
            ),
            ("log_delta_t", self.log_delta_t_mean, self.log_delta_t_std, 1),
        )
        for name, mean, std, size in pairs:
            _require_shape(f"{name}_mean", mean, (size,))
            _require_shape(f"{name}_std", std, (size,))
            if not torch.isfinite(mean).all() or not torch.isfinite(std).all():
                raise ValueError(f"{name} statistics must be finite")
            if (std <= 0).any():
                raise ValueError(f"{name} standard deviations must be positive")


def _masked_normalize(
    values: torch.Tensor,
    mask: torch.Tensor,
    mean: torch.Tensor,
    std: torch.Tensor,
) -> torch.Tensor:
    safe = torch.where(mask, values, torch.zeros_like(values))
    normalized = (safe - mean.to(values)) / std.to(values).clamp_min(1.0e-8)
    return torch.where(mask, normalized, torch.zeros_like(normalized))


def prepare_history_features(
    sequence: RoadObservationSequence,
    layout: RoadFeatureLayout,
    statistics: RoadFeatureStatistics,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Return leakage-safe global and node metadata with explicit masks."""
    sequence.validate(layout)
    statistics.validate(layout)
    log_delta_t = torch.log1p(sequence.delta_t)
    log_delta_t = (
        log_delta_t - statistics.log_delta_t_mean.to(log_delta_t)
    ) / statistics.log_delta_t_std.to(log_delta_t).clamp_min(1.0e-8)
    global_observation = _masked_normalize(
        sequence.global_observations,
        sequence.global_observation_mask,
        statistics.global_mean,
        statistics.global_std,
    )
    traffic = _masked_normalize(
        sequence.traffic,
        sequence.traffic_mask,
        statistics.traffic_mean,
        statistics.traffic_std,
    )
    environment = _masked_normalize(
        sequence.environment,
        sequence.environment_mask,
        statistics.environment_mean,
        statistics.environment_std,
    )
    global_metadata = torch.cat(
        [
            log_delta_t,
            global_observation,
            sequence.global_observation_mask.to(sequence.analysis_states.dtype),
            traffic,
            sequence.traffic_mask.to(sequence.analysis_states.dtype),
            environment,
            sequence.environment_mask.to(sequence.analysis_states.dtype),
            sequence.maintenance,
            sequence.maintenance_state_reset.to(sequence.analysis_states.dtype),
        ],
        dim=-1,
    )
    node_observation = _masked_normalize(
        sequence.node_observations,
        sequence.node_observation_mask,
        statistics.node_mean,
        statistics.node_std,
    )
    node_metadata = torch.cat(
        [
            node_observation,
            sequence.node_observation_mask.to(sequence.analysis_states.dtype),
        ],
        dim=-1,
    )
    return global_metadata, node_metadata


def prepare_future_context(
    scenario: RoadFutureScenario,
    layout: RoadFeatureLayout,
    statistics: RoadFeatureStatistics,
) -> torch.Tensor:
    scenario.validate(layout)
    log_delta_t = torch.log1p(scenario.delta_t)
    log_delta_t = (
        log_delta_t - statistics.log_delta_t_mean.to(log_delta_t)
    ) / statistics.log_delta_t_std.to(log_delta_t).clamp_min(1.0e-8)
    traffic = _masked_normalize(
        scenario.traffic,
        scenario.traffic_mask,
        statistics.traffic_mean,
        statistics.traffic_std,
    )
    environment = _masked_normalize(
        scenario.environment,
        scenario.environment_mask,
        statistics.environment_mean,
        statistics.environment_std,
    )
    return torch.cat(
        [
            log_delta_t,
            traffic,
            scenario.traffic_mask.to(scenario.delta_t.dtype),
            environment,
            scenario.environment_mask.to(scenario.delta_t.dtype),
            scenario.maintenance,
        ],
        dim=-1,
    )


@dataclass(frozen=True)
class RoadForecastOutput:
    state_predictions: torch.Tensor
    raw_state_updates: torch.Tensor
    hazard_probability: torch.Tensor
    cumulative_event_probability: torch.Tensor
    rul_location: torch.Tensor
    rul_scale: torch.Tensor


def cumulative_event_probability(hazard_probability: torch.Tensor) -> torch.Tensor:
    survival = torch.cumprod((1.0 - hazard_probability).clamp_min(1.0e-7), dim=0)
    return 1.0 - survival


def decode_direct_state_forecast(
    current_state: torch.Tensor,
    raw_updates: torch.Tensor,
    statistics: StateStatistics,
) -> torch.Tensor:
    """Decode direct horizon heads as monotone step increments."""
    state = current_state
    predictions: list[torch.Tensor] = []
    for update in raw_updates:
        state = apply_directional_state_update(state, update, statistics)
        predictions.append(state)
    return torch.stack(predictions)


class RoadObservationAwareForecaster(nn.Module):
    """Graph forecaster with direct state horizons and probabilistic risk heads."""

    def __init__(
        self,
        *,
        temporal_family: str,
        layout: RoadFeatureLayout,
        local_dim: int = 48,
        token_dim: int = 48,
        temporal_width: int = 64,
        local_layers: int = 2,
        coarse_layers: int = 1,
        graph_enabled: bool = True,
        max_context: int = 20,
        max_state_horizon: int = 3,
        max_risk_horizon: int = 32,
        horizon_dim: int = 8,
        transformer_heads: int = 4,
    ) -> None:
        super().__init__()
        allowed = FORMAL_ROAD_FAMILIES + SECONDARY_ROAD_FAMILIES
        if temporal_family not in allowed:
            raise ValueError(f"road forecaster family must be one of {allowed}")
        if max_state_horizon < 1 or max_risk_horizon < max_state_horizon:
            raise ValueError("risk horizon must be at least the state horizon")
        self.temporal_family = temporal_family
        self.layout = layout
        self.max_state_horizon = max_state_horizon
        self.max_risk_horizon = max_risk_horizon
        self.core_feature_dim = 7
        input_dim = (
            self.core_feature_dim
            + layout.history_global_dim
            + layout.history_node_dim
        )
        self.encoder = FactorizedMeshEncoder(
            input_dim,
            local_dim,
            token_dim,
            local_layers=local_layers,
            coarse_layers=coarse_layers,
            graph_enabled=graph_enabled,
        )
        self.temporal = build_temporal_module(
            temporal_family,
            token_dim,
            temporal_width,
            max_context=max_context,
            transformer_heads=transformer_heads,
        )
        self.state_horizon_embedding = nn.Parameter(
            torch.zeros(max_state_horizon, horizon_dim)
        )
        self.risk_horizon_embedding = nn.Parameter(
            torch.zeros(max_risk_horizon, horizon_dim)
        )
        legacy_decoder_dim = self.core_feature_dim + local_dim + token_dim
        extra_history_dim = layout.history_global_dim + layout.history_node_dim
        state_decoder_dim = (
            legacy_decoder_dim
            + extra_history_dim
            + layout.future_context_dim
            + horizon_dim
        )
        self.state_decoder = _mlp(
            [state_decoder_dim, local_dim + token_dim, local_dim, 4]
        )
        risk_input_dim = token_dim + layout.future_context_dim + horizon_dim
        self.hazard_head = _mlp([risk_input_dim, token_dim, 1])
        self.rul_head = _mlp([token_dim + layout.future_context_dim, token_dim, 2])

    def forward(
        self,
        sequence: RoadObservationSequence,
        scenario: RoadFutureScenario,
        graph: Mapping[str, torch.Tensor],
        state_statistics: StateStatistics,
        road_statistics: RoadFeatureStatistics,
        *,
        state_horizon: int = 3,
        recurrent_ssm: bool = False,
    ) -> RoadForecastOutput:
        if state_horizon < 1 or state_horizon > self.max_state_horizon:
            raise ValueError("state_horizon is outside the configured range")
        if len(scenario.delta_t) > self.max_risk_horizon:
            raise ValueError("future scenario exceeds max_risk_horizon")
        if state_horizon > len(scenario.delta_t):
            raise ValueError("future scenario is shorter than state_horizon")
        global_history, node_history = prepare_history_features(
            sequence, self.layout, road_statistics
        )
        future_context = prepare_future_context(
            scenario, self.layout, road_statistics
        )
        latest_features, local, token_history = self.encoder(
            sequence.analysis_states,
            graph,
            state_statistics,
            global_history,
            node_history,
        )
        if isinstance(self.temporal, DiagonalSSMTemporal):
            predicted_token = self.temporal(token_history, recurrent=recurrent_ssm)
        else:
            predicted_token = self.temporal(token_history)
        broadcast = predicted_token[graph["cluster_index"]]
        core = latest_features[:, : self.core_feature_dim]
        road_history = latest_features[:, self.core_feature_dim :]
        legacy_features = torch.cat([core, local, broadcast], dim=-1)
        raw_updates: list[torch.Tensor] = []
        for horizon in range(state_horizon):
            context = future_context[horizon].reshape(1, -1).expand(len(core), -1)
            embedding = self.state_horizon_embedding[horizon].reshape(1, -1)
            embedding = embedding.expand(len(core), -1)
            raw_updates.append(
                self.state_decoder(
                    torch.cat(
                        [legacy_features, road_history, context, embedding], dim=-1
                    )
                )
            )
        raw_state_updates = torch.stack(raw_updates)
        state_predictions = decode_direct_state_forecast(
            sequence.analysis_states[-1], raw_state_updates, state_statistics
        )

        cluster_count = predicted_token.shape[0]
        cluster_area = graph["areas"].new_zeros(cluster_count)
        cluster_area.index_add_(0, graph["cluster_index"], graph["areas"].reshape(-1))
        global_token = (
            predicted_token * cluster_area[:, None]
        ).sum(dim=0) / cluster_area.sum().clamp_min(1.0e-8)
        hazard_logits: list[torch.Tensor] = []
        for horizon, context in enumerate(future_context):
            hazard_input = torch.cat(
                [global_token, context, self.risk_horizon_embedding[horizon]], dim=-1
            )
            hazard_logits.append(self.hazard_head(hazard_input).squeeze(-1))
        hazard_probability = torch.sigmoid(torch.stack(hazard_logits))
        scenario_summary = future_context.mean(dim=0)
        rul_raw = self.rul_head(torch.cat([global_token, scenario_summary], dim=-1))
        rul_location = rul_raw[0]
        rul_scale = F.softplus(rul_raw[1]) + 1.0e-6
        return RoadForecastOutput(
            state_predictions=state_predictions,
            raw_state_updates=raw_state_updates,
            hazard_probability=hazard_probability,
            cumulative_event_probability=cumulative_event_probability(
                hazard_probability
            ),
            rul_location=rul_location,
            rul_scale=rul_scale,
        )


def _copy_padded_linear(target: nn.Linear, source: nn.Linear) -> None:
    if target.out_features != source.out_features:
        raise ValueError("linear output dimensions are incompatible")
    if target.in_features < source.in_features:
        raise ValueError("target linear layer cannot hold the source inputs")
    with torch.no_grad():
        target.weight.zero_()
        target.weight[:, : source.in_features].copy_(source.weight)
        target.bias.copy_(source.bias)


def initialize_from_legacy_temporal_operator(
    target: RoadObservationAwareForecaster,
    source: TemporalMeshOperator,
) -> dict[str, object]:
    """Load a legacy matched checkpoint with all new conditioning weights zero.

    This supports a strict no-observation equivalence smoke for the first direct
    horizon.  It does not calibrate the new observation, scenario, hazard, or
    RUL pathways.
    """
    if source.metadata_dim != 0 or source.node_metadata_dim != 0:
        raise ValueError("strict legacy transfer requires a seven-feature source")
    if source.temporal_family != target.temporal_family:
        raise ValueError("legacy source and road target must use the same family")
    _copy_padded_linear(
        target.encoder.local_projection[0], source.encoder.local_projection[0]
    )
    target.encoder.local_projection[2].load_state_dict(
        source.encoder.local_projection[2].state_dict()
    )
    _copy_padded_linear(
        target.encoder.token_projection[0], source.encoder.token_projection[0]
    )
    target.encoder.token_projection[2].load_state_dict(
        source.encoder.token_projection[2].state_dict()
    )
    target.encoder.local_blocks.load_state_dict(
        source.encoder.local_blocks.state_dict()
    )
    target.encoder.coarse_blocks.load_state_dict(
        source.encoder.coarse_blocks.state_dict()
    )
    target.temporal.load_state_dict(source.temporal.state_dict())
    _copy_padded_linear(target.state_decoder[0], source.decoder[0])
    target.state_decoder[2].load_state_dict(source.decoder[2].state_dict())
    target.state_decoder[4].load_state_dict(source.decoder[4].state_dict())
    with torch.no_grad():
        target.state_horizon_embedding.zero_()
    return {
        "status": "legacy_state_path_loaded",
        "strict_equivalence_scope": (
            "first raw state horizon with no trained road conditioning"
        ),
        "risk_heads": "random_untrained",
        "road_conditioning_columns": "zero_initialized",
    }


def discrete_hazard_nll(
    hazard_probability: torch.Tensor,
    event_index: int,
    *,
    censored: bool,
) -> torch.Tensor:
    """Discrete-time survival loss for a declared event/censor interval."""
    if event_index < 0 or event_index >= len(hazard_probability):
        raise ValueError("event_index lies outside the hazard horizon")
    hazard = hazard_probability.clamp(1.0e-7, 1.0 - 1.0e-7)
    survived = -torch.log1p(-hazard[: event_index + int(censored)]).sum()
    if censored:
        return survived
    return survived - torch.log(hazard[event_index])


def lognormal_rul_nll(
    location: torch.Tensor,
    scale: torch.Tensor,
    remaining_life: torch.Tensor,
    *,
    censored: bool,
) -> torch.Tensor:
    """Log-normal RUL loss with right-censor support.

    `location` is the log-space location parameter.  This likelihood is only a
    training primitive; calibration still requires trajectory-held-out event
    and censor diversity.
    """
    if (remaining_life <= 0).any():
        raise ValueError("remaining_life must be positive")
    distribution = torch.distributions.LogNormal(
        location, scale.clamp_min(1.0e-6)
    )
    if censored:
        survival = (1.0 - distribution.cdf(remaining_life)).clamp_min(1.0e-7)
        return -torch.log(survival).mean()
    return -distribution.log_prob(remaining_life).mean()


def expected_lognormal_rul(location: torch.Tensor, scale: torch.Tensor) -> torch.Tensor:
    return torch.exp(location + 0.5 * scale.square())
