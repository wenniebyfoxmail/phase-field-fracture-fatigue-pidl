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
    Agent1InnovationPacket,
    Agent2TriggerEvaluator,
    RoadClosedLoopForecaster,
    TriggerEvidence,
    adapt_bundle_to_observation_sequence,
    assert_graph_compatibility,
    load_agent1_innovation_packet,
    load_agent2_contracts,
    load_road_observation_state_bundle,
)
from road_observation_aware_operator import (  # noqa: E402
    RoadFeatureLayout,
    RoadFeatureStatistics,
    RoadFutureScenario,
    RoadObservationAwareForecaster,
)


CANONICAL_ROOT = ROOT / "analysis" / "road_observation_state_bundle_v1_20260724"
CANONICAL_SHA = "e94027542484431d3a53222d930c81e9ed6c655b86a822ced1452fa8c4c0f253"


def layout() -> RoadFeatureLayout:
    return RoadFeatureLayout(
        node_observation_dim=2,
        global_observation_dim=1,
        traffic_dim=2,
        environment_dim=2,
        maintenance_dim=1,
    )


def graph() -> dict[str, torch.Tensor]:
    coordinates = torch.tensor(
        [
            [0.0, 0.0],
            [0.25, 0.0],
            [0.5, 0.0],
            [0.75, 0.0],
            [1.0, 0.0],
            [1.25, 0.0],
        ]
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


def write_bundle(
    path: Path,
    *,
    decision_eligible: bool = False,
    uncertainty_kind: str = "std",
) -> str:
    current_graph = graph()
    state = history()[-1].numpy().astype(np.float32)[None, ...]
    latent_attribution = np.zeros_like(state, dtype=np.bool_)
    latent_attribution[:, ::2, 3] = True
    source = np.zeros_like(state, dtype=np.uint8)
    source[latent_attribution] = 1
    node_values = np.full((1, 6, 2), np.nan, dtype=np.float32)
    node_mask = np.zeros_like(node_values, dtype=np.bool_)
    global_values = np.full((1, 1), np.nan, dtype=np.float32)
    global_mask = np.zeros_like(global_values, dtype=np.bool_)
    metadata = {
        "bundle_id": "synthetic_bundle",
        "claim": "test only",
        "coordinate_frame": "test_xy",
        "evidence_class": "synthetic" if decision_eligible else "oracle",
        "fem_eta": 0.0,
        "oracle_channels_decision_eligible": decision_eligible,
        "real_road_compatible": False,
        "registration_id": "identity",
        "schema_version": "road_observation_state_bundle_v1",
        "source_schema_versions": {"test": "v1"},
        "source_sha256": {"test": "abc"},
        "state_fields": [
            "damage",
            "fatigue_history",
            "fatigue_degradation",
            "log10_psi_raw",
        ],
        "training_run": False,
        "uncertainty_kind": uncertainty_kind,
        "uncertainty_status": (
            "calibrated" if decision_eligible else "uncalibrated_not_available"
        ),
    }
    uncertainty_payload: dict[str, np.ndarray]
    if uncertainty_kind == "std":
        uncertainty_payload = {
            "state_std": (
                np.full_like(state, 0.1)
                if decision_eligible
                else np.full_like(state, np.nan)
            )
        }
    elif uncertainty_kind == "covariance":
        covariance = np.zeros((1, 6, 4, 4), dtype=np.float32)
        diagonal = 0.01 if decision_eligible else np.nan
        covariance[..., np.arange(4), np.arange(4)] = diagonal
        uncertainty_payload = {"state_covariance": covariance}
    elif uncertainty_kind == "ensemble":
        if decision_eligible:
            uncertainty_payload = {
                "state_ensemble": np.stack([state - 0.1, state + 0.1])
            }
        else:
            uncertainty_payload = {
                "state_ensemble": np.full((2, *state.shape), np.nan, dtype=np.float32)
            }
    else:
        raise ValueError("unknown test uncertainty kind")
    np.savez_compressed(
        path,
        schema_version=np.asarray("road_observation_state_bundle_v1"),
        metadata_json=np.asarray(json.dumps(metadata, sort_keys=True)),
        cycle=np.asarray([87], dtype=np.int32),
        state_fields=np.asarray(metadata["state_fields"]),
        coordinates=current_graph["coordinates"].numpy().astype(np.float32),
        areas=current_graph["areas"].numpy().astype(np.float32),
        edge_index=current_graph["edge_index"].numpy().astype(np.int64),
        edge_attr=current_graph["edge_attr"].numpy().astype(np.float32),
        state_mean=state,
        observed_channel_mask=latent_attribution,
        source_code=source,
        node_observation_channels=np.asarray(["crack_probability", "strain_axial"]),
        node_observation_evidence=np.asarray(["synthetic", "synthetic"]),
        node_observation_values=node_values,
        node_observation_mask=node_mask,
        global_observation_channels=np.asarray(["fwd_center"]),
        global_observation_evidence=np.asarray(["synthetic"]),
        global_observation_values=global_values,
        global_observation_mask=global_mask,
        timestamp=np.asarray([""]),
        timestamp_mask=np.asarray([False]),
        equivalent_load_index=np.asarray([np.nan], dtype=np.float64),
        equivalent_load_index_mask=np.asarray([False]),
        delta_t=np.asarray([np.nan], dtype=np.float64),
        delta_t_mask=np.asarray([False]),
        traffic_channels=np.asarray(["esal_increment", "heavy_axle_count"]),
        traffic_values=np.full((1, 2), np.nan, dtype=np.float32),
        traffic_mask=np.zeros((1, 2), dtype=np.bool_),
        environment_channels=np.asarray(["temperature", "moisture"]),
        environment_values=np.full((1, 2), np.nan, dtype=np.float32),
        environment_mask=np.zeros((1, 2), dtype=np.bool_),
        maintenance_reset=np.asarray([False]),
        maintenance_reset_declared=np.asarray([False]),
        maintenance_event_id=np.asarray([""]),
        state_segment_id=np.asarray([0], dtype=np.int32),
        **uncertainty_payload,
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
                "signal_a": {
                    "centre": 0.0,
                    "scale": 1.0,
                    "warn_z": 3.0,
                    "hard_z": 5.0,
                },
                "signal_b": {
                    "centre": 0.0,
                    "scale": 1.0,
                    "warn_z": 3.0,
                    "hard_z": 5.0,
                },
            }
        },
    }
    (path / "observation_trigger_spec.json").write_text(json.dumps(trigger))


def scenario(*, maintenance: bool = False) -> RoadFutureScenario:
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


def make_orchestrator(
    bundle,
    contracts,
    innovation_packet: Agent1InnovationPacket | None = None,
) -> RoadClosedLoopForecaster:
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
    result = RoadClosedLoopForecaster(
        model,
        graph=graph(),
        state_statistics=statistics(),
        road_statistics=RoadFeatureStatistics.identity(layout()),
        trigger_contract=contracts.trigger,
        state_heads_trained=False,
        risk_heads_trained=False,
        evidence_class="synthetic_tooling_smoke",
    )
    result.assimilate(bundle, innovation_packet)
    return result


def test_latent_attribution_cannot_create_sensor_measurement(tmp_path: Path) -> None:
    path = tmp_path / "bundle.npz"
    digest = write_bundle(path)
    bundle = load_road_observation_state_bundle(path, expected_sha256=digest)
    assert bundle.observed_channel_mask.any()
    assert not bundle.node_observation_mask.any()
    sequence = adapt_bundle_to_observation_sequence(
        bundle,
        history(),
        layout=layout(),
        asset_id="synthetic_asset",
        history_delta_t=torch.tensor([[0.0], [0.7], [1.6]]),
    )
    sequence.validate(layout())
    assert not sequence.node_observation_mask.any()
    assert torch.isnan(sequence.node_observations).all()
    assert not torch.equal(
        sequence.node_observation_mask[..., :1],
        bundle.observed_channel_mask[..., :1],
    )


def test_new_canonical_bundle_hash_loads() -> None:
    path = CANONICAL_ROOT / "road_observation_state_bundle_c87_oracle.npz"
    if not path.exists():
        pytest.skip("canonical Agent1 package is not mounted")
    bundle = load_road_observation_state_bundle(path, expected_sha256=CANONICAL_SHA)
    assert bundle.package_sha256 == CANONICAL_SHA
    assert bundle.state_mean.shape == (1, 86408, 4)
    assert bundle.source_field_order == bundle.forecast_field_order
    assert not bundle.decision_eligible
    assert not bundle.uncertainty_available


@pytest.mark.parametrize("uncertainty_kind", ["std", "covariance", "ensemble"])
def test_calibrated_uncertainty_representations_derive_eligible_std(
    tmp_path: Path, uncertainty_kind: str
) -> None:
    path = tmp_path / f"bundle_{uncertainty_kind}.npz"
    write_bundle(
        path,
        decision_eligible=True,
        uncertainty_kind=uncertainty_kind,
    )
    bundle = load_road_observation_state_bundle(path)
    assert bundle.uncertainty_available
    assert bundle.uncertainty_trigger_eligible
    assert torch.isfinite(bundle.state_std).all()


def test_decision_ineligible_packet_cannot_trigger_request_or_stop() -> None:
    packet_path = CANONICAL_ROOT / "agent2_observation_innovation_packet.json"
    if not packet_path.exists():
        pytest.skip("canonical Agent1 packet is not mounted")
    packet = load_agent1_innovation_packet(
        packet_path, expected_bundle_sha256=CANONICAL_SHA
    )
    contract = {
        "schema": "road_observation_trigger_v1",
        "current_offline_rule": {
            "envelopes": {
                "signal": {
                    "centre": 0.0,
                    "scale": 1.0,
                    "warn_z": 3.0,
                    "hard_z": 5.0,
                }
            }
        },
    }
    decision = Agent2TriggerEvaluator(contract).evaluate(
        TriggerEvidence(
            model_internal={"signal": 100.0},
            observation_innovation_hard=True,
            decision_eligible=packet.decision_eligible,
            eligibility_reason=packet.decision_eligibility_reason,
        )
    )
    assert decision.action == "continue"
    assert not decision.request_observation
    assert not decision.stop_forecast
    assert decision.status == "rejected_ineligible_operational_evidence"


def test_final_packet_rejects_values_hidden_behind_false_mask(tmp_path: Path) -> None:
    source = CANONICAL_ROOT / "agent2_observation_innovation_packet.json"
    document = json.loads(source.read_text(encoding="utf-8"))
    channel = document["channels"]["registered_crack_geometry_image"]
    assert channel["mask"][0] is False
    channel["values"][0] = 0.0
    invalid = tmp_path / "invalid_packet.json"
    invalid.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="masked innovation values"):
        load_agent1_innovation_packet(
            invalid,
            expected_bundle_sha256=CANONICAL_SHA,
        )


def test_closed_loop_rejects_ineligible_packet_even_for_eligible_bundle(
    tmp_path: Path,
) -> None:
    bundle_path = tmp_path / "eligible_bundle.npz"
    write_bundle(bundle_path, decision_eligible=True)
    bundle = load_road_observation_state_bundle(bundle_path)
    packet = Agent1InnovationPacket(
        path=tmp_path / "packet.json",
        packet_sha256="packet-sha",
        source_bundle_sha256=bundle.package_sha256,
        decision_eligible=False,
        decision_eligibility_reason="audit-only packet",
        evidence_class="oracle",
        document={},
    )
    agent2 = tmp_path / "agent2"
    write_agent2_specs(agent2)
    contracts = load_agent2_contracts(agent2)
    sequence = adapt_bundle_to_observation_sequence(
        bundle,
        history(),
        layout=layout(),
        asset_id="synthetic_asset",
        history_delta_t=torch.tensor([[0.0], [0.6], [1.4]]),
    )
    result = make_orchestrator(bundle, contracts, packet).forecast(
        sequence,
        scenario(),
        trigger_evidence=TriggerEvidence(
            model_internal={"signal_a": 100.0, "signal_b": 100.0},
            observation_innovation_hard=True,
        ),
    )
    assert result.trigger.action == "continue"
    assert not result.trigger.request_observation
    assert not result.trigger.stop_forecast
    assert result.trigger.status == "rejected_ineligible_operational_evidence"


def test_missing_observations_remain_missing_end_to_end(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle.npz"
    write_bundle(bundle_path)
    bundle = load_road_observation_state_bundle(bundle_path)
    agent2 = tmp_path / "agent2"
    write_agent2_specs(agent2)
    contracts = load_agent2_contracts(agent2)
    sequence = adapt_bundle_to_observation_sequence(
        bundle,
        history(),
        layout=layout(),
        asset_id="synthetic_asset",
        history_delta_t=torch.tensor([[0.0], [0.6], [1.4]]),
    )
    assert torch.isnan(sequence.node_observations).all()
    assert torch.isnan(sequence.global_observations).all()
    result = make_orchestrator(bundle, contracts).forecast(sequence, scenario())
    assert result.state_predictions is not None
    assert result.state_predictions.shape == (3, 6, 4)
    assert result.long_horizon_risk.status == "unavailable_untrained"
    assert result.trigger.status == "rejected_ineligible_operational_evidence"


def test_short_field_limit_and_system_maintenance_stop(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle.npz"
    write_bundle(bundle_path)
    bundle = load_road_observation_state_bundle(bundle_path)
    agent2 = tmp_path / "agent2"
    write_agent2_specs(agent2)
    contracts = load_agent2_contracts(agent2)
    sequence = adapt_bundle_to_observation_sequence(
        bundle,
        history(),
        layout=layout(),
        asset_id="synthetic_asset",
        history_delta_t=torch.tensor([[0.0], [1.0], [2.0]]),
    )
    orchestrator = make_orchestrator(bundle, contracts)
    stopped = orchestrator.forecast(sequence, scenario(maintenance=True))
    assert stopped.trigger.stop_forecast
    assert stopped.trigger.request_observation
    assert stopped.state_predictions is None
    orchestrator.re_assimilate(bundle)
    resumed = orchestrator.forecast(sequence, scenario())
    assert resumed.state_predictions is not None
    with pytest.raises(ValueError, match="h1-h3"):
        orchestrator.forecast(sequence, scenario(), state_horizon=4)


def test_graph_mismatch_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bundle.npz"
    write_bundle(path)
    bundle = load_road_observation_state_bundle(path)
    bad_graph = graph()
    bad_graph["coordinates"] = bad_graph["coordinates"].clone()
    bad_graph["coordinates"][0, 0] = 9.0
    with pytest.raises(ValueError, match="coordinates"):
        assert_graph_compatibility(bundle, bad_graph)
