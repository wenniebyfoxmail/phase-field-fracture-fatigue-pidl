#!/usr/bin/env python3
"""Train one sealed model/seed/fold of the four-trajectory FEM LOCO study."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import time
from typing import Mapping

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from fem_mechanism_operator import StateStatistics  # noqa: E402
from temporal_mesh_operator import (  # noqa: E402
    TemporalMeshOperator,
    count_parameters,
    parameter_breakdown,
    temporal_mechanism_loss,
)
from train_temporal_mesh_operator import (  # noqa: E402
    field_metrics,
    predict_next,
    selection_composite,
    weighted_correlation,
)


FAMILIES = ("markov", "tcn", "transformer")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty table: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_graph(path: Path, device: torch.device) -> tuple[dict[str, torch.Tensor], dict[str, np.ndarray]]:
    data = np.load(path, allow_pickle=False)
    names = (
        "coordinates", "centroids", "log_area", "areas", "edge_index",
        "edge_attr", "cluster_index", "coarse_edge_index", "coarse_edge_attr",
    )
    arrays = {name: np.asarray(data[name]) for name in names}
    graph = {name: torch.from_numpy(value).to(device) for name, value in arrays.items()}
    for name in ("edge_index", "cluster_index", "coarse_edge_index"):
        graph[name] = graph[name].long()
    return graph, arrays


def load_trajectory(path: Path, device: torch.device) -> dict:
    data = np.load(path, allow_pickle=False)
    states = torch.from_numpy(np.asarray(data["states"], dtype=np.float32)).to(device)
    metadata = torch.from_numpy(
        np.asarray(data["loading_metadata"], dtype=np.float32)
    ).to(device)
    return {
        "trajectory_id": str(np.asarray(data["trajectory_id"]).item()),
        "states": states,
        "metadata": metadata,
        "first_hit": int(np.asarray(data["first_hit_cycle"]).item()),
        "confirmed": int(np.asarray(data["confirmed_cycle"]).item()),
        "event_phase": str(np.asarray(data["event_phase"]).item()),
    }


def training_statistics(trajectories: list[dict], device: torch.device) -> StateStatistics:
    states = np.concatenate(
        [item["states"].detach().cpu().numpy() for item in trajectories], axis=0
    ).astype(np.float64)
    residuals = np.concatenate(
        [np.diff(item["states"].detach().cpu().numpy(), axis=0) for item in trajectories],
        axis=0,
    ).astype(np.float64)
    arrays = (
        states.mean(axis=(0, 1)),
        np.maximum(states.std(axis=(0, 1)), 1e-6),
        residuals.mean(axis=(0, 1)),
        np.maximum(residuals.std(axis=(0, 1)), 1e-6),
    )
    return StateStatistics(
        *(torch.tensor(value, dtype=torch.float32, device=device).reshape(1, -1) for value in arrays)
    )


def forecast(
    model: TemporalMeshOperator,
    item: dict,
    origin: int,
    horizon: int,
    context: int,
    graph: Mapping[str, torch.Tensor],
    statistics: StateStatistics,
) -> dict[int, torch.Tensor]:
    history = [state for state in item["states"][origin - context:origin]]
    output: dict[int, torch.Tensor] = {}
    model.eval()
    with torch.no_grad():
        for cycle in range(origin + 1, origin + horizon + 1):
            metadata = item["metadata"][cycle - context - 1:cycle - 1]
            prediction = predict_next(
                model, torch.stack(history[-context:]), graph, statistics, metadata
            )
            output[cycle] = prediction
            history.append(prediction)
    return output


def event_hit(state: np.ndarray, centroids: np.ndarray) -> bool:
    return int(np.count_nonzero((centroids[:, 0] >= 0.48) & (state[:, 0] >= 0.95))) >= 3


def evaluate(
    model: TemporalMeshOperator,
    heldout: dict,
    context: int,
    graph: Mapping[str, torch.Tensor],
    graph_arrays: Mapping[str, np.ndarray],
    statistics: StateStatistics,
    out: Path,
) -> tuple[list[dict], list[dict]]:
    areas = np.asarray(graph_arrays["areas"], dtype=np.float64)
    coordinates = np.asarray(graph_arrays["coordinates"], dtype=np.float64)
    centroids = np.asarray(graph_arrays["centroids"], dtype=np.float64)
    edge_index = np.asarray(graph_arrays["edge_index"], dtype=np.int64)
    rows: list[dict] = []
    warning_rows: list[dict] = []

    def append_task(task: str, origin: int, predictions: Mapping[int, torch.Tensor]) -> None:
        for cycle, prediction in predictions.items():
            prediction_array = prediction.detach().cpu().numpy()
            target_array = heldout["states"][cycle - 1].detach().cpu().numpy()
            metrics = field_metrics(
                prediction_array,
                target_array,
                areas, coordinates, edge_index,
            )
            weights = areas / areas.sum()
            prediction_history_log = np.log10(
                np.maximum(prediction_array[:, 1], 1.0e-12)
            )
            target_history_log = np.log10(
                np.maximum(target_array[:, 1], 1.0e-12)
            )
            history_error = prediction_history_log - target_history_log
            metrics.update(
                {
                    "history_log10_mae": float(
                        np.sum(weights * np.abs(history_error))
                    ),
                    "history_log10_rmse": float(
                        np.sqrt(np.sum(weights * history_error**2))
                    ),
                    "history_log10_correlation": weighted_correlation(
                        prediction_history_log, target_history_log, areas
                    ),
                }
            )
            rows.append(
                {
                    "task": task,
                    "trajectory_id": heldout["trajectory_id"],
                    "origin_cycle": origin,
                    "target_cycle": cycle,
                    "horizon": cycle - origin,
                    "event_phase": heldout["event_phase"],
                    "selection_composite": selection_composite(metrics),
                    **metrics,
                }
            )

    # Task 1: every observed origin whose h1-h3 targets remain pre-transition.
    for origin in range(context, heldout["first_hit"] - 3 + 1):
        append_task(
            "observed_state_same_regime_h1_h3",
            origin,
            forecast(model, heldout, origin, 3, context, graph, statistics),
        )

    # Task 2: autonomous warning from pre-transition observed origins only.
    representative: dict[str, np.ndarray] = {}
    for origin in range(heldout["first_hit"] - 3, heldout["first_hit"]):
        horizon = min(3, len(heldout["states"]) - origin)
        predictions = forecast(model, heldout, origin, horizon, context, graph, statistics)
        append_task("autonomous_transition_warning", origin, predictions)
        for cycle, prediction in predictions.items():
            predicted_hit = event_hit(prediction.detach().cpu().numpy(), centroids)
            truth_hit = cycle >= heldout["first_hit"]
            warning_rows.append(
                {
                    "trajectory_id": heldout["trajectory_id"],
                    "origin_cycle": origin,
                    "target_cycle": cycle,
                    "horizon": cycle - origin,
                    "truth_transition": int(truth_hit),
                    "predicted_warning": int(predicted_hit),
                    "missed_transition": int(truth_hit and not predicted_hit),
                    "false_warning": int(predicted_hit and not truth_hit),
                    "warning_lead_intervals": heldout["first_hit"] - cycle if predicted_hit else "unavailable",
                    "calibrated_probability": "unavailable",
                    "brier_score": "unavailable",
                    "calibration_error": "unavailable",
                }
            )
        if origin == heldout["first_hit"] - 3:
            representative["transition_origin_state"] = heldout["states"][origin - 1].detach().cpu().numpy()
            for cycle, prediction in predictions.items():
                representative[f"transition_prediction_c{cycle}"] = prediction.detach().cpu().numpy()
                representative[f"transition_fem_c{cycle}"] = heldout["states"][cycle - 1].detach().cpu().numpy()

    # Task 3: a true observed-state reset at first hit, then conditional h1-h3.
    reset_origin = heldout["first_hit"]
    reset_horizon = min(3, len(heldout["states"]) - reset_origin)
    reset_predictions = forecast(
        model, heldout, reset_origin, reset_horizon, context, graph, statistics
    )
    append_task(
        "observation_reset_conditional_propagation",
        reset_origin,
        reset_predictions,
    )
    representative["reset_origin_state"] = heldout["states"][reset_origin - 1].detach().cpu().numpy()
    for cycle, prediction in reset_predictions.items():
        representative[f"reset_prediction_c{cycle}"] = prediction.detach().cpu().numpy()
        representative[f"reset_fem_c{cycle}"] = heldout["states"][cycle - 1].detach().cpu().numpy()
    np.savez_compressed(out / "representative_fields.npz", **representative)
    return rows, warning_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--heldout", required=True)
    parser.add_argument("--family", choices=FAMILIES, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--context", type=int, required=True)
    parser.add_argument("--temporal-width", type=int, required=True)
    parser.add_argument("--local-dim", type=int, default=49)
    parser.add_argument("--token-dim", type=int, default=50)
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if sys.platform == "darwin":
        raise RuntimeError("training is disabled on Mac; use an approved producer")
    if args.family == "markov" and args.context != 1:
        raise ValueError("sealed Markov context is 1")
    if args.family != "markov" and args.context != 3:
        raise ValueError("sealed TCN/Transformer context is 3")
    set_seed(args.seed)
    device = torch.device(args.device)
    manifest = json.loads((args.data_root / "RUN_MANIFEST.json").read_text())
    trajectory_paths = {
        row["trajectory_id"]: args.data_root / "trajectories" / row["data_file"]
        for row in manifest["trajectories"]
    }
    if args.heldout not in trajectory_paths or len(trajectory_paths) != 4:
        raise ValueError("held-out trajectory or four-trajectory inventory missing")
    graph, graph_arrays = load_graph(args.data_root / manifest["graph_file"], device)
    trajectories = {
        key: load_trajectory(path, device) for key, path in trajectory_paths.items()
    }
    train_ids = sorted(set(trajectories) - {args.heldout})
    training = [trajectories[key] for key in train_ids]
    heldout = trajectories[args.heldout]
    statistics = training_statistics(training, device)
    model = TemporalMeshOperator(
        temporal_family=args.family,
        metadata_dim=2,
        local_dim=args.local_dim,
        token_dim=args.token_dim,
        temporal_width=args.temporal_width,
        max_context=args.context,
        transformer_heads=4,
    ).to(device)
    parameter_count = count_parameters(model)
    if abs(parameter_count - 329000) / 329000 > 0.01:
        raise ValueError("model failed frozen 1% capacity gate")
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-6)
    rng = random.Random(args.seed)
    windows = [
        (item, origin)
        for item in training
        for origin in range(args.context, len(item["states"]) - 3 + 1)
    ]
    args.out.mkdir(parents=True, exist_ok=True)
    history_rows = []
    started = time.perf_counter()
    for step in range(1, args.steps + 1):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        item, origin = rng.choice(windows)
        history = [state for state in item["states"][origin - args.context:origin]]
        losses = []
        gradient_norm = float("nan")
        for cycle in range(origin + 1, origin + 4):
            metadata = item["metadata"][cycle - args.context - 1:cycle - 1]
            prediction = predict_next(
                model, torch.stack(history[-args.context:]), graph, statistics, metadata
            )
            loss, _ = temporal_mechanism_loss(
                prediction, item["states"][cycle - 1], graph
            )
            losses.append(loss)
            history.append(prediction)
        total = torch.stack(losses).mean()
        if not torch.isfinite(total):
            raise FloatingPointError(f"non-finite loss at step {step}")
        total.backward()
        gradient_norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0).cpu())
        optimizer.step()
        if step == 1 or step % 100 == 0 or step == args.steps:
            row = {
                "step": step,
                "trajectory_id": item["trajectory_id"],
                "origin_cycle": origin,
                "loss": float(total.detach().cpu()),
                "gradient_norm": gradient_norm,
                "elapsed_seconds": time.perf_counter() - started,
            }
            history_rows.append(row)
            print(json.dumps(row), flush=True)

    torch.save(
        {
            "model": model.state_dict(),
            "statistics": {name: getattr(statistics, name).cpu() for name in (
                "state_mean", "state_std", "residual_mean", "residual_std"
            )},
            "args": vars(args),
        },
        args.out / "final_model.pt",
    )
    metrics, warnings = evaluate(
        model, heldout, args.context, graph, graph_arrays, statistics, args.out
    )
    write_csv(args.out / "fem_centred_metrics.csv", metrics)
    write_csv(args.out / "transition_warning_metrics.csv", warnings)
    write_csv(args.out / "training_history.csv", history_rows)
    run = {
        "status": "complete",
        "claim_scope": "within-Hard5 held-out factorial combination only",
        "synthetic_not_real_road": True,
        "heldout_trajectory_id": args.heldout,
        "training_trajectory_ids": train_ids,
        "family": args.family,
        "seed": args.seed,
        "context": args.context,
        "steps": args.steps,
        "parameter_count": parameter_count,
        "parameter_breakdown": parameter_breakdown(model),
        "data_manifest_sha256": sha256_file(args.data_root / "RUN_MANIFEST.json"),
        "risk": {
            "calibrated_hazard": "unavailable",
            "rul_distribution": "unavailable",
            "reason": "no per-fold event/right-censor diversity or calibrated uncertainty",
        },
        "tasks": [
            "observed_state_same_regime_h1_h3",
            "autonomous_transition_warning",
            "observation_reset_conditional_propagation",
        ],
        "training_seconds": time.perf_counter() - started,
    }
    (args.out / "RUN_MANIFEST.json").write_text(
        json.dumps(run, indent=2, sort_keys=True, default=str) + "\n"
    )
    print(json.dumps(run, indent=2, default=str))


if __name__ == "__main__":
    main()
