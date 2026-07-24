from __future__ import annotations

import sys
from pathlib import Path

import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from fem_mechanism_operator import StateStatistics  # noqa: E402
from road_observation_aware_operator import (  # noqa: E402
    FORMAL_ROAD_FAMILIES,
    SECONDARY_ROAD_FAMILIES,
    RoadFeatureLayout,
    RoadFeatureStatistics,
    RoadFutureScenario,
    RoadObservationAwareForecaster,
    RoadObservationSequence,
    cumulative_event_probability,
    discrete_hazard_nll,
    expected_lognormal_rul,
    initialize_from_legacy_temporal_operator,
    lognormal_rul_nll,
    prepare_history_features,
)
from temporal_mesh_operator import TemporalMeshOperator  # noqa: E402


def tiny_statistics() -> StateStatistics:
    return StateStatistics(
        state_mean=torch.tensor([[0.2, 0.4, 0.8, -3.0]]),
        state_std=torch.tensor([[0.2, 0.3, 0.1, 1.0]]),
        residual_mean=torch.tensor([[0.0, 0.0, 0.0, 0.01]]),
        residual_std=torch.tensor([[0.02, 0.03, 0.01, 0.2]]),
    )


def tiny_graph() -> dict[str, torch.Tensor]:
    coordinates = torch.tensor(
        [[0.0, 0.0], [0.2, 0.0], [0.4, 0.0], [0.6, 0.0], [0.8, 0.0], [1.0, 0.0]]
    )
    src = torch.tensor([0, 1, 1, 2, 2, 3, 3, 4, 4, 5])
    dst = torch.tensor([1, 0, 2, 1, 3, 2, 4, 3, 5, 4])
    delta = coordinates[dst] - coordinates[src]
    coarse_delta = torch.tensor([[0.6, 0.0], [-0.6, 0.0]])
    return {
        "coordinates": coordinates,
        "areas": torch.ones(6),
        "log_area": torch.zeros(6, 1),
        "edge_index": torch.stack([src, dst]),
        "edge_attr": torch.cat([delta, delta.abs()], dim=1),
        "cluster_index": torch.tensor([0, 0, 0, 1, 1, 1]),
        "coarse_edge_index": torch.tensor([[0, 1], [1, 0]]),
        "coarse_edge_attr": torch.cat([coarse_delta, coarse_delta.abs()], dim=1),
    }


def tiny_history(length: int = 3) -> torch.Tensor:
    base = torch.tensor(
        [
            [0.1, 0.2, 0.9, -3.5],
            [0.15, 0.25, 0.88, -3.2],
            [0.2, 0.3, 0.86, -3.0],
            [0.25, 0.35, 0.84, -2.8],
            [0.3, 0.4, 0.82, -2.6],
            [0.35, 0.45, 0.8, -2.4],
        ]
    )
    return torch.stack(
        [
            base + torch.tensor([0.01 * i, 0.02 * i, -0.01 * i, 0.03 * i])
            for i in range(length)
        ]
    )


def layout() -> RoadFeatureLayout:
    return RoadFeatureLayout(
        node_observation_dim=2,
        global_observation_dim=2,
        traffic_dim=2,
        environment_dim=2,
        maintenance_dim=1,
    )


def sequence(*, provenance: str = "synthetic") -> RoadObservationSequence:
    time, elements = 3, 6
    node_values = torch.randn(time, elements, 2)
    node_mask = torch.ones_like(node_values, dtype=torch.bool)
    node_mask[0, 0, 0] = False
    node_values[0, 0, 0] = torch.nan
    global_values = torch.randn(time, 2)
    global_mask = torch.ones_like(global_values, dtype=torch.bool)
    traffic = torch.tensor([[1.0, 0.1], [1.2, 0.2], [1.1, 0.3]])
    environment = torch.tensor([[20.0, 0.3], [22.0, 0.4], [19.0, 0.5]])
    return RoadObservationSequence(
        analysis_states=tiny_history(time),
        node_observations=node_values,
        node_observation_mask=node_mask,
        global_observations=global_values,
        global_observation_mask=global_mask,
        delta_t=torch.tensor([[0.0], [1.0], [2.0]]),
        traffic=traffic,
        traffic_mask=torch.ones_like(traffic, dtype=torch.bool),
        environment=environment,
        environment_mask=torch.ones_like(environment, dtype=torch.bool),
        maintenance=torch.zeros(time, 1),
        maintenance_state_reset=torch.zeros(time, 1, dtype=torch.bool),
        provenance=provenance,
        observation_space_version="road_obs_v1",
        asset_id="synthetic_coupon_01",
    )


def scenario(horizon: int = 5) -> RoadFutureScenario:
    traffic = torch.ones(horizon, 2)
    environment = torch.ones(horizon, 2)
    return RoadFutureScenario(
        delta_t=torch.ones(horizon, 1),
        traffic=traffic,
        traffic_mask=torch.ones_like(traffic, dtype=torch.bool),
        environment=environment,
        environment_mask=torch.ones_like(environment, dtype=torch.bool),
        maintenance=torch.zeros(horizon, 1),
        scenario_id="constant_synthetic_scenario",
    )


def test_layout_keeps_values_and_missingness_masks_separate() -> None:
    feature_layout = layout()
    assert feature_layout.history_node_dim == 4
    assert feature_layout.history_global_dim == 18
    assert feature_layout.future_context_dim == 10
    global_features, node_features = prepare_history_features(
        sequence(), feature_layout, RoadFeatureStatistics.identity(feature_layout)
    )
    assert global_features.shape == (3, 18)
    assert node_features.shape == (3, 6, 4)
    assert node_features[0, 0, 0] == 0
    assert node_features[0, 0, 2] == 0
    assert node_features[0, 1, 2] == 1


def test_sequence_rejects_unversioned_or_unknown_provenance() -> None:
    valid = sequence()
    invalid_version = RoadObservationSequence(
        **{**valid.__dict__, "observation_space_version": "unknown"}
    )
    with pytest.raises(ValueError, match="version"):
        invalid_version.validate(layout())
    invalid_provenance = RoadObservationSequence(
        **{**valid.__dict__, "provenance": "probably_real"}
    )
    with pytest.raises(ValueError, match="provenance"):
        invalid_provenance.validate(layout())


def test_maintenance_requires_explicit_state_semantics() -> None:
    valid = sequence()
    maintenance = valid.maintenance.clone()
    maintenance[1, 0] = 1.0
    missing_reset = RoadObservationSequence(
        **{**valid.__dict__, "maintenance": maintenance}
    )
    with pytest.raises(ValueError, match="state reset"):
        missing_reset.validate(layout())
    reset = valid.maintenance_state_reset.clone()
    reset[1, 0] = True
    accepted = RoadObservationSequence(
        **{
            **valid.__dict__,
            "maintenance": maintenance,
            "maintenance_state_reset": reset,
        }
    )
    accepted.validate(layout())

    future = scenario()
    future_maintenance = future.maintenance.clone()
    future_maintenance[2, 0] = 1.0
    unmodelled = RoadFutureScenario(
        **{**future.__dict__, "maintenance": future_maintenance}
    )
    with pytest.raises(ValueError, match="maintenance_model_id"):
        unmodelled.validate(layout())


@pytest.mark.parametrize("family", FORMAL_ROAD_FAMILIES + SECONDARY_ROAD_FAMILIES)
def test_observation_aware_families_produce_state_and_risk_outputs(family: str) -> None:
    torch.manual_seed(7)
    feature_layout = layout()
    model = RoadObservationAwareForecaster(
        temporal_family=family,
        layout=feature_layout,
        local_dim=12,
        token_dim=8,
        temporal_width=16,
        local_layers=1,
        coarse_layers=1,
        max_context=5,
        max_state_horizon=3,
        max_risk_horizon=8,
        transformer_heads=4,
    )
    output = model(
        sequence(),
        scenario(),
        tiny_graph(),
        tiny_statistics(),
        RoadFeatureStatistics.identity(feature_layout),
    )
    assert output.state_predictions.shape == (3, 6, 4)
    assert output.raw_state_updates.shape == (3, 6, 4)
    assert output.hazard_probability.shape == (5,)
    assert output.cumulative_event_probability.shape == (5,)
    assert output.rul_location.ndim == 0
    assert output.rul_scale > 0
    assert torch.all(
        output.state_predictions[1:, :, 0] >= output.state_predictions[:-1, :, 0]
    )
    assert torch.all(
        output.state_predictions[1:, :, 1] >= output.state_predictions[:-1, :, 1]
    )
    assert torch.all(
        output.state_predictions[1:, :, 2] <= output.state_predictions[:-1, :, 2]
    )
    loss = (
        output.state_predictions.mean()
        + output.hazard_probability.mean()
        + output.rul_scale
    )
    loss.backward()
    assert all(parameter.grad is not None for parameter in model.parameters())


@pytest.mark.parametrize("family", FORMAL_ROAD_FAMILIES)
def test_legacy_transfer_preserves_first_raw_forecast_without_trained_conditioning(
    family: str,
) -> None:
    torch.manual_seed(13)
    kwargs = dict(
        local_dim=12,
        token_dim=8,
        temporal_width=16,
        local_layers=1,
        coarse_layers=1,
        max_context=5,
        transformer_heads=4,
    )
    legacy = TemporalMeshOperator(temporal_family=family, **kwargs)
    target = RoadObservationAwareForecaster(
        temporal_family=family,
        layout=layout(),
        max_state_horizon=3,
        max_risk_horizon=8,
        **kwargs,
    )
    report = initialize_from_legacy_temporal_operator(target, legacy)
    expected = legacy(tiny_history(), tiny_graph(), tiny_statistics())
    actual = target(
        sequence(),
        scenario(),
        tiny_graph(),
        tiny_statistics(),
        RoadFeatureStatistics.identity(layout()),
    ).raw_state_updates[0]
    torch.testing.assert_close(actual, expected)
    assert report["risk_heads"] == "random_untrained"


def test_hazard_outputs_are_monotone_and_support_censoring_loss() -> None:
    hazard = torch.tensor([0.1, 0.2, 0.4])
    cumulative = cumulative_event_probability(hazard)
    assert torch.all(cumulative[1:] >= cumulative[:-1])
    event_loss = discrete_hazard_nll(hazard, 1, censored=False)
    censored_loss = discrete_hazard_nll(hazard, 1, censored=True)
    assert event_loss == pytest.approx(
        float(-torch.log1p(-hazard[0]) - torch.log(hazard[1]))
    )
    assert censored_loss == pytest.approx(float(-torch.log1p(-hazard[:2]).sum()))


def test_rul_distribution_supports_events_and_right_censoring() -> None:
    location = torch.tensor(2.0, requires_grad=True)
    scale = torch.tensor(0.3, requires_grad=True)
    remaining_life = torch.tensor(8.0)
    event_loss = lognormal_rul_nll(location, scale, remaining_life, censored=False)
    censored_loss = lognormal_rul_nll(location, scale, remaining_life, censored=True)
    assert torch.isfinite(event_loss)
    assert torch.isfinite(censored_loss)
    assert expected_lognormal_rul(location, scale) > 0
    (event_loss + censored_loss).backward()
    assert location.grad is not None
    assert scale.grad is not None
