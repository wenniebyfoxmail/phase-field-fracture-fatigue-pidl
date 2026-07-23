#!/usr/bin/env python3
"""Offline stage-1 audit for legacy-to-road observation-aware transfer.

The audit does not train a model and does not evaluate road generalisation.  It
loads existing matched FEM checkpoints, zero-initialises every new road-input
column, and verifies that the first raw state forecast remains unchanged.
"""
from __future__ import annotations

import argparse
from argparse import Namespace
import csv
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from fem_mechanism_operator import StateStatistics  # noqa: E402
from road_observation_aware_operator import (  # noqa: E402
    FORMAL_ROAD_FAMILIES,
    RoadFeatureLayout,
    RoadFeatureStatistics,
    RoadFutureScenario,
    RoadObservationAwareForecaster,
    RoadObservationSequence,
    initialize_from_legacy_temporal_operator,
)
from temporal_mesh_operator import count_parameters  # noqa: E402
from train_temporal_mesh_operator import build_model, history_slice, load_dataset  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--origin-cycle", type=int, default=76)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checkpoint_statistics(checkpoint: dict[str, Any]) -> StateStatistics:
    stored = checkpoint["statistics"]
    return StateStatistics(
        stored["state_mean"],
        stored["state_std"],
        stored["residual_mean"],
        stored["residual_std"],
    )


def absent_road_inputs(
    history: torch.Tensor,
    layout: RoadFeatureLayout,
) -> tuple[RoadObservationSequence, RoadFutureScenario]:
    time, elements, _ = history.shape
    node = history.new_zeros((time, elements, layout.node_observation_dim))
    global_observation = history.new_zeros((time, layout.global_observation_dim))
    traffic = history.new_zeros((time, layout.traffic_dim))
    environment = history.new_zeros((time, layout.environment_dim))
    delta_t = history.new_ones((time, 1))
    delta_t[0] = 0.0
    sequence = RoadObservationSequence(
        analysis_states=history,
        node_observations=node,
        node_observation_mask=torch.zeros_like(node, dtype=torch.bool),
        global_observations=global_observation,
        global_observation_mask=torch.zeros_like(global_observation, dtype=torch.bool),
        delta_t=delta_t,
        traffic=traffic,
        traffic_mask=torch.zeros_like(traffic, dtype=torch.bool),
        environment=environment,
        environment_mask=torch.zeros_like(environment, dtype=torch.bool),
        maintenance=history.new_zeros((time, layout.maintenance_dim)),
        maintenance_state_reset=torch.zeros((time, 1), dtype=torch.bool),
        provenance="synthetic",
        observation_space_version=layout.observation_space_version,
        asset_id="single_eta0_fem_transfer_audit",
    )
    future_traffic = history.new_zeros((3, layout.traffic_dim))
    future_environment = history.new_zeros((3, layout.environment_dim))
    scenario = RoadFutureScenario(
        delta_t=history.new_ones((3, 1)),
        traffic=future_traffic,
        traffic_mask=torch.zeros_like(future_traffic, dtype=torch.bool),
        environment=future_environment,
        environment_mask=torch.zeros_like(future_environment, dtype=torch.bool),
        maintenance=history.new_zeros((3, layout.maintenance_dim)),
        scenario_id="absent_exogenous_stage1_audit",
    )
    return sequence, scenario


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cpu")
    _, states, graph, _ = load_dataset(
        args.dataset, device, use_loading_metadata=False
    )
    layout = RoadFeatureLayout(
        node_observation_dim=2,
        global_observation_dim=2,
        traffic_dim=2,
        environment_dim=2,
        maintenance_dim=1,
    )
    rows: list[dict[str, object]] = []
    checkpoint_assets: list[dict[str, str]] = []
    for checkpoint_path in args.checkpoint:
        checkpoint = torch.load(
            checkpoint_path, map_location=device, weights_only=False
        )
        saved_args = Namespace(**dict(checkpoint["args"]))
        family = str(saved_args.temporal_model)
        if family not in FORMAL_ROAD_FAMILIES:
            raise ValueError(
                f"stage-1 formal audit accepts {FORMAL_ROAD_FAMILIES}, got {family}"
            )
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
        history = history_slice(states, args.origin_cycle, context)
        sequence, scenario = absent_road_inputs(history, layout)
        statistics = checkpoint_statistics(checkpoint)
        with torch.no_grad():
            legacy_raw = legacy(
                history,
                graph,
                statistics,
                recurrent_ssm=family == "diagonal_ssm",
            )
            road_output = road(
                sequence,
                scenario,
                graph,
                statistics,
                RoadFeatureStatistics.identity(layout),
                recurrent_ssm=family == "diagonal_ssm",
            )
        difference = (legacy_raw - road_output.raw_state_updates[0]).abs()
        max_error = float(difference.max())
        rows.append(
            {
                "family": family,
                "seed": int(saved_args.seed),
                "selected_context": context,
                "origin_cycle": args.origin_cycle,
                "legacy_parameters": count_parameters(legacy),
                "road_parameters": count_parameters(road),
                "first_raw_horizon_max_abs_error": max_error,
                "strict_transfer_pass": max_error <= 1.0e-6,
                "road_observations": "absent",
                "future_scenario": "absent",
                "risk_head_status": transfer["risk_heads"],
                "scientific_status": "tooling_only",
            }
        )
        checkpoint_assets.append(
            {"path": str(checkpoint_path), "sha256": sha256(checkpoint_path)}
        )
    csv_path = args.out / "legacy_transfer_audit.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        "status": "tooling_only",
        "training_launched": False,
        "dataset": {"path": str(args.dataset), "sha256": sha256(args.dataset)},
        "checkpoints": checkpoint_assets,
        "origin_cycle": args.origin_cycle,
        "formal_families": list(FORMAL_ROAD_FAMILIES),
        "road_feature_layout": layout.__dict__,
        "claims_allowed": [
            "legacy first-state path can be preserved when new inputs are absent"
        ],
        "claims_forbidden": [
            "road generalisation",
            "observation benefit",
            "RUL calibration",
            "transition prediction",
        ],
        "outputs": [csv_path.name],
    }
    (args.out / "RUN_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not all(bool(row["strict_transfer_pass"]) for row in rows):
        raise SystemExit("legacy transfer audit failed")
    print(f"PASS: {len(rows)} formal legacy checkpoints preserve first raw horizon")


if __name__ == "__main__":
    main()
