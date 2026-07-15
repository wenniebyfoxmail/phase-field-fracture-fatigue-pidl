#!/usr/bin/env python3
"""Run sparse-observation and restart-horizon gates on a trained FEM operator.

This is a single-trajectory diagnostic.  It never assimilates c89 and cannot
support trajectory-generalisation claims.  Its purpose is to identify which
late-cycle observations, if any, allow a locked c89 mechanism forecast.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from fem_mechanism_assimilation import (  # noqa: E402
    SCENARIOS,
    assimilate_state,
    fixed_crack_corridor_probes,
    scenario_by_name,
)
from fem_mechanism_operator import (  # noqa: E402
    StateStatistics,
    apply_state_constraints,
    normalized_node_features,
)
from train_fem_mechanism_mesh_operator import (  # noqa: E402
    build_model,
    choose_device,
    field_metrics,
    load_dataset,
)


TEST_CYCLE = 89


def checkpoint_model(
    checkpoint_path: Path,
    device: torch.device,
    input_dim: int = 10,
) -> tuple[torch.nn.Module, StateStatistics, dict[str, object]]:
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model_args = SimpleNamespace(**checkpoint["args"])
    model = build_model(model_args, input_dim).to(device)
    model.load_state_dict(checkpoint["model"])
    model.eval()
    statistics = StateStatistics(
        *(checkpoint["statistics"][name].to(device) for name in (
            "state_mean", "state_std", "residual_mean", "residual_std"
        ))
    )
    return model, statistics, checkpoint


@torch.inference_mode()
def forecast_step(
    model: torch.nn.Module,
    current: torch.Tensor,
    target_cycle: int,
    graph: dict[str, torch.Tensor],
    statistics: StateStatistics,
) -> torch.Tensor:
    features = normalized_node_features(
        current,
        graph["coordinates"],
        graph["log_area"],
        target_cycle,
        statistics,
    )
    residual = model(
        features,
        graph["edge_index"],
        graph["edge_attr"],
        graph["cluster_index"],
        graph["coarse_edge_index"],
        graph["coarse_edge_attr"],
    )
    return apply_state_constraints(current, residual, statistics)


def metric_row(
    *,
    experiment: str,
    scenario: str,
    cycle: int,
    phase: str,
    prediction: torch.Tensor,
    target: torch.Tensor,
    areas: np.ndarray,
    diagnostics: dict[str, int | float] | None = None,
) -> dict[str, int | float | str]:
    row: dict[str, int | float | str] = {
        "experiment": experiment,
        "scenario": scenario,
        "cycle": cycle,
        "phase": phase,
    }
    if diagnostics:
        row.update(diagnostics)
    else:
        row.update({"observed_values": 0, "observed_elements": 0, "analysis_rms_increment": 0.0})
    row.update(field_metrics(prediction.detach().cpu().numpy(), target.detach().cpu().numpy(), areas))
    return row


def assimilated_forecast(
    model: torch.nn.Module,
    statistics: StateStatistics,
    states: torch.Tensor,
    graph: dict[str, torch.Tensor],
    areas: np.ndarray,
    fixed_probes: torch.Tensor,
    scenario_name: str,
    observation_cycles: tuple[int, ...],
    start_cycle: int,
    visible_damage_threshold: float,
) -> tuple[list[dict[str, int | float | str]], torch.Tensor]:
    scenario = scenario_by_name(scenario_name)
    current = states[start_cycle - 1].clone()
    rows: list[dict[str, int | float | str]] = []
    report_cycles = set(observation_cycles) | {78, TEST_CYCLE}
    for cycle in range(start_cycle + 1, TEST_CYCLE + 1):
        previous = current
        forecast = forecast_step(model, current, cycle, graph, statistics)
        if cycle in report_cycles:
            rows.append(
                metric_row(
                    experiment="sequential_assimilation",
                    scenario=scenario.name,
                    cycle=cycle,
                    phase="forecast_prior",
                    prediction=forecast,
                    target=states[cycle - 1],
                    areas=areas,
                )
            )
        if cycle in observation_cycles and scenario.channel_masks:
            current, diagnostics = assimilate_state(
                forecast,
                states[cycle - 1],
                previous,
                scenario,
                fixed_probes,
                visible_damage_threshold=visible_damage_threshold,
            )
            rows.append(
                metric_row(
                    experiment="sequential_assimilation",
                    scenario=scenario.name,
                    cycle=cycle,
                    phase="analysis_post",
                    prediction=current,
                    target=states[cycle - 1],
                    areas=areas,
                    diagnostics=diagnostics,
                )
            )
        else:
            current = forecast
    return rows, current


def restart_horizon_audit(
    model: torch.nn.Module,
    statistics: StateStatistics,
    states: torch.Tensor,
    graph: dict[str, torch.Tensor],
    areas: np.ndarray,
    restart_cycles: tuple[int, ...],
) -> tuple[list[dict[str, int | float | str]], dict[str, np.ndarray]]:
    rows: list[dict[str, int | float | str]] = []
    predictions: dict[str, np.ndarray] = {}
    for restart_cycle in restart_cycles:
        current = states[restart_cycle - 1].clone()
        for cycle in range(restart_cycle + 1, TEST_CYCLE + 1):
            current = forecast_step(model, current, cycle, graph, statistics)
        label = f"true_c{restart_cycle}_restart"
        rows.append(
            metric_row(
                experiment="true_state_restart_horizon",
                scenario=label,
                cycle=TEST_CYCLE,
                phase="forecast",
                prediction=current,
                target=states[TEST_CYCLE - 1],
                areas=areas,
            )
        )
        predictions[f"restart_c{restart_cycle}_to_c89"] = current.detach().cpu().numpy()
    return rows, predictions


def write_rows(path: Path, rows: list[dict[str, int | float | str]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--start-cycle", type=int, default=76)
    parser.add_argument("--observation-cycles", type=int, nargs="+", default=[80, 84])
    parser.add_argument("--restart-cycles", type=int, nargs="+", default=[67, 76, 80, 84, 86, 87, 88])
    parser.add_argument(
        "--scenarios",
        nargs="+",
        default=[scenario.name for scenario in SCENARIOS],
    )
    parser.add_argument("--probe-x-count", type=int, default=64)
    parser.add_argument("--visible-damage-threshold", type=float, default=0.25)
    parser.add_argument("--allow-single-trajectory-diagnostic", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.allow_single_trajectory_diagnostic:
        raise ValueError("single-trajectory scope requires --allow-single-trajectory-diagnostic")
    observation_cycles = tuple(sorted(set(args.observation_cycles)))
    restart_cycles = tuple(sorted(set(args.restart_cycles)))
    if not observation_cycles or min(observation_cycles) <= args.start_cycle:
        raise ValueError("observation cycles must be strictly after the start cycle")
    if max(observation_cycles) >= TEST_CYCLE:
        raise ValueError("c89 is locked and cannot be assimilated")
    if min(restart_cycles) < 1 or max(restart_cycles) >= TEST_CYCLE:
        raise ValueError("restart cycles must lie in c1..c88")
    for name in args.scenarios:
        scenario_by_name(name)

    device = choose_device(args.device)
    data, states, graph = load_dataset(args.dataset, device)
    areas = np.asarray(data["areas"], dtype=np.float64)
    probe_mask_np = fixed_crack_corridor_probes(
        np.asarray(data["centroids"]), x_count=args.probe_x_count
    )
    fixed_probes = torch.from_numpy(probe_mask_np).to(device)
    model, statistics, checkpoint = checkpoint_model(args.checkpoint, device)

    args.out.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, int | float | str]] = []
    predictions: dict[str, np.ndarray] = {}
    for scenario_name in args.scenarios:
        scenario_rows, prediction = assimilated_forecast(
            model,
            statistics,
            states,
            graph,
            areas,
            fixed_probes,
            scenario_name,
            observation_cycles,
            args.start_cycle,
            args.visible_damage_threshold,
        )
        rows.extend(scenario_rows)
        predictions[f"{scenario_name}_c89"] = prediction.detach().cpu().numpy()

    restart_rows, restart_predictions = restart_horizon_audit(
        model,
        statistics,
        states,
        graph,
        areas,
        restart_cycles,
    )
    rows.extend(restart_rows)
    predictions.update(restart_predictions)
    predictions["state_names"] = np.asarray(
        ["damage", "alpha_bar", "fatigue_degradation", "log10_psi_raw"]
    )

    write_rows(args.out / "assimilation_metrics.csv", rows)
    np.savez_compressed(args.out / "assimilation_predictions.npz", **predictions)
    manifest = {
        "claim_class": "field-mechanism diagnostic",
        "fem_reference": "eta0 cycle-peak",
        "derived_active": "eta0 diagnostic: (1-damage)^2 * psi_raw",
        "trajectory_count": int(np.asarray(data["trajectory_count"]).item()),
        "trajectory_generalization": False,
        "assimilation_cycles": list(observation_cycles),
        "locked_test_cycle": TEST_CYCLE,
        "c89_assimilated": False,
        "restart_cycles": list(restart_cycles),
        "fixed_probe_definition": {
            "geometry_only": True,
            "x_count": args.probe_x_count,
            "y_offsets": [-0.025, 0.0, 0.025],
            "element_count": int(probe_mask_np.sum()),
            "element_fraction": float(probe_mask_np.mean()),
        },
        "visible_damage_threshold": args.visible_damage_threshold,
        "scenarios": [
            {
                "name": scenario_by_name(name).name,
                "description": scenario_by_name(name).description,
                "channel_masks": dict(scenario_by_name(name).channel_masks),
                "observation_class": scenario_by_name(name).observation_class,
                "permuted_observations": scenario_by_name(name).permute_observations,
            }
            for name in args.scenarios
        ],
        "checkpoint": str(args.checkpoint.resolve()),
        "checkpoint_validation_mse": checkpoint["best_validation_rollout_mse"],
        "device": str(device),
        "primary_assets": ["assimilation_metrics.csv", "assimilation_predictions.npz"],
        "quarantine": "single FEM trajectory and noiseless synthetic observations",
    }
    (args.out / "RUN_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
