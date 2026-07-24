from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from fem_mechanism_operator import StateStatistics  # noqa: E402
from road_closed_loop_forecaster import (  # noqa: E402
    AGENT1_TO_FORECAST_FIELD,
    Agent2TriggerEvaluator,
    RoadClosedLoopForecaster,
    TriggerEvidence,
    adapt_agent1_to_observation_sequence,
    assert_graph_compatibility,
    load_agent1_assimilated_state,
    load_agent2_contracts,
)
from road_observation_aware_operator import (  # noqa: E402
    RoadFeatureLayout,
    RoadFeatureStatistics,
    RoadFutureScenario,
    RoadObservationAwareForecaster,
)


def layout() -> RoadFeatureLayout:
    return RoadFeatureLayout(
        node_observation_dim=4,
        global_observation_dim=0,
        traffic_dim=2,
        environment_dim=2,
        maintenance_dim=1,
    )


def graph() -> dict[str, torch.Tensor]:
    coordinates = torch.tensor(
        [[0.0, 0.0], [0.25, 0.0], [0.5, 0.0], [0.75, 0.0], [1.0, 0.0], [1.25, 0.0]]
    )
    src = torch.tensor([0, 1, 1, 2, 2, 3, 3, 4, 4, 5])
    dst = torch.tensor([1, 0, 2, 1, 3, 2, 4, 3, 5, 4])
    delta = coordinates[dst] - coordinates[src]
    coarse_delta = torch.tensor([[0.75, 0.0], [-0.75, 0.0]])
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


def history(length: int = 3) -> torch.Tensor:
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


def statistics() -> StateStatistics:
    return StateStatistics(
        state_mean=torch.tensor([[0.2, 0.4, 0.8, -3.0]]),
        state_std=torch.tensor([[0.2, 0.3, 0.1, 1.0]]),
        residual_mean=torch.tensor([[0.0, 0.0, 0.0, 0.01]]),
        residual_std=torch.tensor([[0.02, 0.03, 0.01, 0.2]]),
    )


def write_agent1_bundle(path: Path) -> str:
    current_graph = graph()
    state = history()[-1].numpy().astype(np.float32)
    observed = np.zeros_like(state, dtype=np.bool_)
    observed[::2, 3] = True
    source = np.zeros_like(state, dtype=np.uint8)
    source[observed] = 1
    metadata = {
        "trajectory_id": "synthetic_trajectory",
        "source_evidence_class": "fem_oracle",
        "observation_operator_id": (
            "road_observation_operator_v1:fem_raw_energy_upper_bound"
        ),
        "prior_id": "prior_c86",
        "physics_family": "FEM_eta0",
        "fem_eta": 0.0,
        "uncertainty_status": "uncalibrated_not_available",
        "real_road_compatible": False,
        "input_sha256": {"operator_dataset": "test"},
    }
    np.savez_compressed(
        path,
        schema_version=np.asarray("road_assimilated_state_v1"),
        metadata_json=np.asarray(json.dumps(metadata, sort_keys=True)),
        cycle=np.asarray(87, dtype=np.int64),
        state_fields=np.asarray(
            ["damage", "alpha_bar", "fatigue_degradation", "log10_psi_raw"]
        ),
        coordinates=current_graph["coordinates"].numpy().astype(np.float32),
        areas=current_graph["areas"].numpy().astype(np.float32),
        edge_index=current_graph["edge_index"].numpy().astype(np.int64),
        edge_attr=current_graph["edge_attr"].numpy().astype(np.float32),
        state_mean=state,
        state_std=np.full_like(state, np.nan),
        observed_channel_mask=observed,
        source_code=source,
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_agent2_specs(path: Path) -> None:
    path.mkdir()
    (path / "road_time_mapping_spec.json").write_text(
        json.dumps({"schema": "road_time_mapping_v1"})
    )
    (path / "road_forecast_horizon_spec.json").write_text(
        json.dumps({"schema": "road_forecast_horizon_v1"})
    )
    trigger = {
        "schema": "road_observation_trigger_v1",
        "current_offline_rule": {
            "envelopes": {
                "signal_a": {"centre": 0.0, "scale": 1.0, "warn_z": 3.0, "hard_z": 5.0},
                "signal_b": {"centre": 0.0, "scale": 1.0, "warn_z": 3.0, "hard_z": 5.0},
            }
        },
    }
    (path / "observation_trigger_spec.json").write_text(json.dumps(trigger))


def future_scenario(*, maintenance: bool = False) -> RoadFutureScenario:
    traffic = torch.full((3, 2), torch.nan)
    environment = torch.full((3, 2), torch.nan)
    maintenance_values = torch.zeros(3, 1)
    if maintenance:
        maintenance_values[1, 0] = 1.0
    return RoadFutureScenario(
        delta_t=torch.tensor([[0.5], [1.5], [0.75]]),
        traffic=traffic,
        traffic_mask=torch.zeros_like(traffic, dtype=torch.bool),
        environment=environment,
        environment_mask=torch.zeros_like(environment, dtype=torch.bool),
        maintenance=maintenance_values,
        scenario_id="irregular_missing_scenario",
        maintenance_model_id="declared_reset" if maintenance else "",
    )


def test_agent1_adapter_is_explicit_and_preserves_missing_uncertainty(
    tmp_path: Path
) -> None:
    path = tmp_path / "analysis.npz"
    digest = write_agent1_bundle(path)
    analysis = load_agent1_assimilated_state(path, expected_sha256=digest)
    assert analysis.cycle == 87
    assert not analysis.uncertainty_available
    assert torch.isnan(analysis.state_std).all()
    assert AGENT1_TO_FORECAST_FIELD["alpha_bar"] == "fatigue_history"
    assert analysis.mask_sha256
    assert_graph_compatibility(analysis, graph())

    sequence = adapt_agent1_to_observation_sequence(
        analysis,
        history(),
        layout=layout(),
        delta_t=torch.tensor([[0.0], [0.7], [1.6]]),
        asset_id="synthetic_asset",
    )
    sequence.validate(layout())
    assert torch.equal(sequence.analysis_states[-1], analysis.state_mean)
    assert torch.equal(
        sequence.node_observation_mask[-1], analysis.observed_channel_mask
    )
    assert torch.isnan(sequence.node_observations[0]).all()
    assert torch.isnan(
        sequence.node_observations[-1][~analysis.observed_channel_mask]
    ).all()


def test_agent2_contract_loader_and_trigger_handoff(tmp_path: Path) -> None:
    write_agent2_specs(tmp_path / "agent2")
    contracts = load_agent2_contracts(tmp_path / "agent2")
    evaluator = Agent2TriggerEvaluator(contracts.trigger)
    missing = evaluator.evaluate(TriggerEvidence())
    assert missing.action == "continue"
    assert missing.unavailable_signals == ("signal_a", "signal_b")

    candidate = evaluator.evaluate(
        TriggerEvidence(model_internal={"signal_a": 3.1, "signal_b": 3.2})
    )
    assert candidate.candidate_model_warning
    assert candidate.action == "continue"
    corroborated = Agent2TriggerEvaluator(contracts.trigger).evaluate(
        TriggerEvidence(
            model_internal={"signal_a": 3.1, "signal_b": 3.2},
            exogenous_ood_warning=True,
        )
    )
    assert corroborated.action == "request_observation"
    hard = Agent2TriggerEvaluator(contracts.trigger).evaluate(
        TriggerEvidence(observation_innovation_hard=True)
    )
    assert hard.stop_forecast
    assert hard.request_observation


def test_closed_loop_separates_short_fields_and_untrained_risk(tmp_path: Path) -> None:
    agent1_path = tmp_path / "analysis.npz"
    write_agent1_bundle(agent1_path)
    analysis = load_agent1_assimilated_state(agent1_path)
    agent2_dir = tmp_path / "agent2"
    write_agent2_specs(agent2_dir)
    contracts = load_agent2_contracts(agent2_dir)
    torch.manual_seed(9)
    model = RoadObservationAwareForecaster(
        temporal_family="markov",
        layout=layout(),
        local_dim=12,
        token_dim=8,
        temporal_width=16,
        local_layers=1,
        coarse_layers=1,
        max_context=5,
        max_state_horizon=3,
        max_risk_horizon=8,
    )
    orchestrator = RoadClosedLoopForecaster(
        model,
        graph=graph(),
        state_statistics=statistics(),
        road_statistics=RoadFeatureStatistics.identity(layout()),
        trigger_contract=contracts.trigger,
        state_heads_trained=False,
        risk_heads_trained=False,
        evidence_class="synthetic_tooling_smoke",
    )
    orchestrator.assimilate(analysis)
    sequence = adapt_agent1_to_observation_sequence(
        analysis,
        history(),
        layout=layout(),
        delta_t=torch.tensor([[0.0], [0.6], [1.4]]),
        asset_id="synthetic_asset",
    )
    result = orchestrator.forecast(sequence, future_scenario())
    assert result.state_predictions is not None
    assert result.state_predictions.shape == (3, 6, 4)
    assert result.state_output_status == "tooling_only_untrained_direct_heads"
    assert result.long_horizon_risk.status == "unavailable_untrained"
    assert result.long_horizon_risk.hazard_probability is None
    assert result.analysis_sha256 == analysis.package_sha256
    assert result.observation_mask_sha256 == analysis.mask_sha256
    assert result.scenario_sha256
    with pytest.raises(ValueError, match="h1-h3"):
        orchestrator.forecast(sequence, future_scenario(), state_horizon=4)


def test_maintenance_or_hard_trigger_withholds_field_and_reassimilation_resets(
    tmp_path: Path,
) -> None:
    agent1_path = tmp_path / "analysis.npz"
    write_agent1_bundle(agent1_path)
    analysis = load_agent1_assimilated_state(agent1_path)
    agent2_dir = tmp_path / "agent2"
    write_agent2_specs(agent2_dir)
    contracts = load_agent2_contracts(agent2_dir)
    model = RoadObservationAwareForecaster(
        temporal_family="markov",
        layout=layout(),
        local_dim=12,
        token_dim=8,
        temporal_width=16,
        local_layers=1,
        coarse_layers=1,
        max_context=5,
        max_state_horizon=3,
        max_risk_horizon=8,
    )
    orchestrator = RoadClosedLoopForecaster(
        model,
        graph=graph(),
        state_statistics=statistics(),
        road_statistics=RoadFeatureStatistics.identity(layout()),
        trigger_contract=contracts.trigger,
        state_heads_trained=False,
        risk_heads_trained=False,
        evidence_class="synthetic_tooling_smoke",
    )
    orchestrator.assimilate(analysis)
    sequence = adapt_agent1_to_observation_sequence(
        analysis,
        history(),
        layout=layout(),
        delta_t=torch.tensor([[0.0], [1.0], [1.0]]),
        asset_id="synthetic_asset",
    )
    stopped = orchestrator.forecast(
        sequence,
        future_scenario(maintenance=True),
    )
    assert stopped.trigger.stop_forecast
    assert stopped.state_predictions is None
    assert stopped.state_output_status == "withheld_trigger_stop"
    orchestrator.re_assimilate(analysis)
    continued = orchestrator.forecast(sequence, future_scenario())
    assert continued.trigger.consecutive_model_warnings == 0
    assert continued.state_predictions is not None


def test_historical_maintenance_requires_reset(tmp_path: Path) -> None:
    path = tmp_path / "analysis.npz"
    write_agent1_bundle(path)
    analysis = load_agent1_assimilated_state(path)
    maintenance = torch.tensor([[0.0], [1.0], [0.0]])
    reset = torch.tensor([[False], [True], [False]])
    accepted = adapt_agent1_to_observation_sequence(
        analysis,
        history(),
        layout=layout(),
        delta_t=torch.tensor([[0.0], [1.0], [2.0]]),
        asset_id="synthetic_asset",
        maintenance=maintenance,
        maintenance_state_reset=reset,
    )
    accepted.validate(layout())
    rejected = adapt_agent1_to_observation_sequence(
        analysis,
        history(),
        layout=layout(),
        delta_t=torch.tensor([[0.0], [1.0], [2.0]]),
        asset_id="synthetic_asset",
        maintenance=maintenance,
    )
    with pytest.raises(ValueError, match="state reset"):
        rejected.validate(layout())
