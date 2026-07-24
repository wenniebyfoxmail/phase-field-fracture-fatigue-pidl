#!/usr/bin/env python3
"""Run the no-training Agent1/Agent2/Agent3 closed-loop compatibility smoke."""
from __future__ import annotations

import argparse
from argparse import Namespace
import csv
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from fem_mechanism_operator import StateStatistics  # noqa: E402
from road_closed_loop_forecaster import (  # noqa: E402
    RoadClosedLoopForecaster,
    adapt_bundle_to_observation_sequence,
    assert_graph_compatibility,
    load_agent1_innovation_packet,
    load_agent2_contracts,
    load_road_observation_state_bundle,
    sha256_file,
)
from road_observation_aware_operator import (  # noqa: E402
    RoadFeatureLayout,
    RoadFeatureStatistics,
    RoadFutureScenario,
    RoadObservationAwareForecaster,
    initialize_from_legacy_temporal_operator,
)
from train_temporal_mesh_operator import build_model, history_slice, load_dataset  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent1-state", type=Path, required=True)
    parser.add_argument("--agent1-sha256", required=True)
    parser.add_argument("--agent1-skeleton", type=Path, required=True)
    parser.add_argument("--agent1-skeleton-sha256", required=True)
    parser.add_argument("--agent1-trigger-packet", type=Path, required=True)
    parser.add_argument("--agent2-contracts", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def checkpoint_statistics(checkpoint: dict[str, Any]) -> StateStatistics:
    stored = checkpoint["statistics"]
    return StateStatistics(
        stored["state_mean"],
        stored["state_std"],
        stored["residual_mean"],
        stored["residual_std"],
    )


def scenario(history: torch.Tensor, layout: RoadFeatureLayout) -> RoadFutureScenario:
    traffic = history.new_full((3, layout.traffic_dim), torch.nan)
    environment = history.new_full((3, layout.environment_dim), torch.nan)
    return RoadFutureScenario(
        delta_t=history.new_tensor([[0.5], [1.5], [0.75]]),
        traffic=traffic,
        traffic_mask=torch.zeros_like(traffic, dtype=torch.bool),
        environment=environment,
        environment_mask=torch.zeros_like(environment, dtype=torch.bool),
        maintenance=history.new_zeros((3, layout.maintenance_dim)),
        scenario_id="c87_synthetic_irregular_dt_missing_exogenous",
    )


def maintenance_scenario(
    history: torch.Tensor, layout: RoadFeatureLayout
) -> RoadFutureScenario:
    result = scenario(history, layout)
    maintenance = result.maintenance.clone()
    maintenance[1, 0] = 1.0
    return RoadFutureScenario(
        **{
            **result.__dict__,
            "maintenance": maintenance,
            "scenario_id": "c87_synthetic_maintenance_reset",
            "maintenance_model_id": "declared_reassimilation_required",
        }
    )


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cpu")
    analysis = load_road_observation_state_bundle(
        args.agent1_state,
        expected_sha256=args.agent1_sha256,
        device=device,
    )
    if sha256_file(args.agent1_skeleton) != args.agent1_skeleton_sha256:
        raise ValueError("Agent 1 Agent3 skeleton SHA-256 mismatch")
    with np.load(args.agent1_skeleton, allow_pickle=False) as skeleton:
        if (
            str(np.asarray(skeleton["source_bundle_sha256"]).item())
            != analysis.package_sha256
        ):
            raise ValueError("Agent3 skeleton points to a different bundle")
        if not np.array_equal(
            np.asarray(skeleton["z_analysis"]), analysis.state_mean.cpu().numpy()
        ):
            raise ValueError("Agent3 skeleton state differs from canonical bundle")
        for name, expected in (
            ("node_observation_values", analysis.node_observation_values),
            ("node_observation_mask", analysis.node_observation_mask),
            ("global_observation_values", analysis.global_observation_values),
            ("global_observation_mask", analysis.global_observation_mask),
        ):
            actual = torch.from_numpy(np.asarray(skeleton[name])).to(expected)
            matches = (
                torch.equal(actual, expected)
                if expected.dtype == torch.bool
                else torch.allclose(actual, expected, equal_nan=True)
            )
            if not matches:
                raise ValueError(f"Agent3 skeleton {name} differs from bundle")
    packet = load_agent1_innovation_packet(
        args.agent1_trigger_packet,
        expected_bundle_sha256=analysis.package_sha256,
    )
    contracts = load_agent2_contracts(args.agent2_contracts)
    data, states, graph, _ = load_dataset(
        args.dataset, device, use_loading_metadata=False
    )
    expected_dataset_hash = analysis.metadata["legacy_metadata"]["input_sha256"][
        "operator_dataset"
    ]
    actual_dataset_hash = sha256_file(args.dataset)
    if actual_dataset_hash != expected_dataset_hash:
        raise ValueError("forecast dataset differs from Agent 1 operator dataset")
    assert_graph_compatibility(analysis, graph)
    origin_cycle = int(analysis.cycles[-1])
    if origin_cycle != 87:
        raise ValueError("stage-2 compatibility smoke is frozen at c87")

    layout = RoadFeatureLayout(
        node_observation_dim=len(analysis.node_observation_channels),
        global_observation_dim=len(analysis.global_observation_channels),
        traffic_dim=len(analysis.traffic_channels),
        environment_dim=len(analysis.environment_channels),
        maintenance_dim=1,
    )
    rows: list[dict[str, Any]] = []
    for checkpoint_path in args.checkpoint:
        checkpoint = torch.load(
            checkpoint_path, map_location=device, weights_only=False
        )
        saved_args = Namespace(**dict(checkpoint["args"]))
        family = str(saved_args.temporal_model)
        if family not in {"markov", "tcn", "diagonal_ssm"}:
            raise ValueError(f"stage-2 smoke excludes non-formal family {family}")
        legacy = build_model(saved_args, metadata_dim=0)
        legacy.load_state_dict(checkpoint["model"])
        legacy.eval()
        road = RoadObservationAwareForecaster(
            temporal_family=family,
            layout=layout,
            local_dim=saved_args.local_dim,
            token_dim=saved_args.token_dim,
            temporal_width=saved_args.temporal_width,
            local_layers=saved_args.local_layers,
            coarse_layers=saved_args.coarse_layers,
            graph_enabled=saved_args.spatial_encoder == "graph",
            max_context=max(saved_args.context_lengths),
            max_state_horizon=3,
            max_risk_horizon=8,
            transformer_heads=saved_args.transformer_heads,
        )
        transfer = initialize_from_legacy_temporal_operator(road, legacy)
        road.eval()
        context = int(checkpoint["selected_context"])
        original_history = history_slice(states, origin_cycle, context)
        history_delta_t = torch.cat(
            [
                torch.zeros(1, 1),
                torch.tensor(
                    [[0.6 + 0.1 * (index % 3)] for index in range(context - 1)]
                ),
            ]
        )
        sequence = adapt_bundle_to_observation_sequence(
            analysis,
            original_history,
            layout=layout,
            asset_id="single_eta0_fem_c87_agent1_upper_bound",
            history_delta_t=history_delta_t,
        )
        expected_node_count = int(analysis.node_observation_mask.sum())
        bundle_time = len(analysis.state_mean)
        node_mask_exact = torch.equal(
            sequence.node_observation_mask[-bundle_time:],
            analysis.node_observation_mask,
        )
        node_values_exact = torch.allclose(
            sequence.node_observations[-bundle_time:],
            analysis.node_observation_values,
            equal_nan=True,
        )
        if (
            int(sequence.node_observation_mask.sum()) != expected_node_count
            or not node_mask_exact
            or not node_values_exact
        ):
            raise ValueError("latent attribution leaked into node observation mask")
        statistics = checkpoint_statistics(checkpoint)
        with torch.no_grad():
            legacy_raw = legacy(
                sequence.analysis_states,
                graph,
                statistics,
                recurrent_ssm=family == "diagonal_ssm",
            )
            direct = road(
                sequence,
                scenario(original_history, layout),
                graph,
                statistics,
                RoadFeatureStatistics.identity(layout),
                recurrent_ssm=family == "diagonal_ssm",
            )
        transfer_error = float((legacy_raw - direct.raw_state_updates[0]).abs().max())
        orchestrator = RoadClosedLoopForecaster(
            road,
            graph=graph,
            state_statistics=statistics,
            road_statistics=RoadFeatureStatistics.identity(layout),
            trigger_contract=contracts.trigger,
            state_heads_trained=False,
            risk_heads_trained=False,
            evidence_class="synthetic_fem_oracle_tooling_smoke",
        )
        orchestrator.assimilate(analysis, packet)
        result = orchestrator.forecast(
            sequence,
            scenario(original_history, layout),
            recurrent_ssm=family == "diagonal_ssm",
        )
        stopped = orchestrator.forecast(
            sequence,
            maintenance_scenario(original_history, layout),
            recurrent_ssm=family == "diagonal_ssm",
        )
        orchestrator.re_assimilate(analysis, packet)
        resumed = orchestrator.forecast(
            sequence,
            scenario(original_history, layout),
            recurrent_ssm=family == "diagonal_ssm",
        )
        rows.append(
            {
                "family": family,
                "seed": int(saved_args.seed),
                "selected_context": context,
                "origin_cycle": origin_cycle,
                "analysis_sha256": result.analysis_sha256,
                "observation_mask_sha256": result.observation_mask_sha256,
                "scenario_sha256": result.scenario_sha256,
                "legacy_h1_raw_max_abs_error": transfer_error,
                "legacy_h1_transfer_pass": transfer_error <= 1.0e-6,
                "irregular_dt_available_count": int(sequence.delta_t_mask.sum()),
                "missing_node_values": int(
                    torch.isnan(sequence.node_observations).sum()
                ),
                "observed_node_values": int(sequence.node_observation_mask.sum()),
                "latent_attribution_values": int(analysis.observed_channel_mask.sum()),
                "latent_to_sensor_leak_count": 0,
                "missing_global_values": int(
                    torch.isnan(sequence.global_observations).sum()
                ),
                "missing_traffic_values": int(torch.isnan(sequence.traffic).sum()),
                "risk_status": result.long_horizon_risk.status,
                "state_status": result.state_output_status,
                "maintenance_action": stopped.trigger.action,
                "maintenance_withheld_fields": stopped.state_predictions is None,
                "reassimilation_action": resumed.trigger.action,
                "trigger_missing_signal_count": len(result.trigger.unavailable_signals),
                "trigger_decision_eligible": packet.decision_eligible,
                "trigger_status": result.trigger.status,
                "transfer_scope": transfer["strict_equivalence_scope"],
                "scientific_status": "tooling_only_no_training",
            }
        )

    csv_path = args.out / "closed_loop_compatibility_smoke.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    unique_analysis = {row["analysis_sha256"] for row in rows}
    unique_mask = {row["observation_mask_sha256"] for row in rows}
    unique_scenario = {row["scenario_sha256"] for row in rows}
    summary = {
        "status": "pass_tooling_only",
        "training_launched": False,
        "families": [row["family"] for row in rows],
        "same_analysis_hash": len(unique_analysis) == 1,
        "same_mask_hash": len(unique_mask) == 1,
        "same_scenario_hash": len(unique_scenario) == 1,
        "all_legacy_h1_transfer_pass": all(
            row["legacy_h1_transfer_pass"] for row in rows
        ),
        "all_risk_unavailable": all(
            row["risk_status"] == "unavailable_untrained" for row in rows
        ),
        "all_maintenance_stops": all(
            row["maintenance_withheld_fields"] for row in rows
        ),
        "all_reassimilation_resumes": all(
            row["reassimilation_action"] == "continue" for row in rows
        ),
        "no_latent_to_sensor_leak": all(
            row["latent_to_sensor_leak_count"] == 0 for row in rows
        ),
        "all_trigger_packets_rejected": all(
            not row["trigger_decision_eligible"]
            and row["trigger_status"] == "rejected_ineligible_operational_evidence"
            for row in rows
        ),
        "agent1": {
            "path": str(args.agent1_state),
            "sha256": analysis.package_sha256,
            "origin_id": analysis.origin_id,
            "uncertainty_available": analysis.uncertainty_available,
            "uncertainty_trigger_eligible": analysis.uncertainty_trigger_eligible,
            "decision_eligible": analysis.decision_eligible,
            "real_road_compatible": analysis.metadata["real_road_compatible"],
            "skeleton": {
                "path": str(args.agent1_skeleton),
                "sha256": args.agent1_skeleton_sha256,
            },
            "innovation_packet": {
                "path": str(args.agent1_trigger_packet),
                "sha256": packet.packet_sha256,
                "decision_eligible": packet.decision_eligible,
            },
        },
        "agent2_hashes": contracts.hashes,
        "dataset": {"path": str(args.dataset), "sha256": actual_dataset_hash},
        "claims_allowed": [
            "Agent1 canonical observation-state bundle executes through Agent3",
            "legacy first raw state path is unchanged after zero-column transfer",
            (
                "independent measurement missingness, irregular dt, maintenance "
                "stop, and re-assimilation paths execute"
            ),
        ],
        "claims_forbidden": [
            "forecast performance improvement",
            "road generalisation",
            "calibrated uncertainty",
            "hazard or RUL availability",
            "transition prediction",
        ],
    }
    if not all(
        summary[key]
        for key in (
            "same_analysis_hash",
            "same_mask_hash",
            "same_scenario_hash",
            "all_legacy_h1_transfer_pass",
            "all_risk_unavailable",
            "all_maintenance_stops",
            "all_reassimilation_resumes",
            "no_latent_to_sensor_leak",
            "all_trigger_packets_rejected",
        )
    ):
        raise SystemExit("closed-loop compatibility smoke failed")
    (args.out / "compatibility_smoke_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"PASS: {len(rows)} formal families completed the tooling-only smoke")


if __name__ == "__main__":
    main()
