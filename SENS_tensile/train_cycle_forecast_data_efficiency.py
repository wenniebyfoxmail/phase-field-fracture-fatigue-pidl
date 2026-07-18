#!/usr/bin/env python3
"""Train one leakage-safe FEM cycle-forecast matrix cell on a producer GPU.

The runner deliberately separates training/nonlocked evaluation from the final
c89 unlock.  Mac use is limited to imports, unit tests, and ``--inspect-only``.
All conclusions remain within one physical FEM trajectory.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
import time
from collections import deque
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from fem_mechanism_operator import (  # noqa: E402
    MultiScaleMeshResidualOperator,
    PointwiseResidualOperator,
    STATE_NAMES,
    StateStatistics,
    apply_state_constraints,
    mechanism_loss,
)
from train_fem_mechanism_mesh_operator import (  # noqa: E402
    choose_device,
    field_metrics,
    set_seed,
    validate_dataset_scope,
)

ALLOWED_TRAIN_ENDS = (20, 40, 60, 67)
ALLOWED_CONTEXTS = (1, 3, 5, 10)
NONLOCKED_HORIZONS = (1, 3, 5, 10)
NEAR_EVENT_ORIGIN = 76
LOCKED_CYCLE = 89


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_prefix_statistics(states: np.ndarray, train_end: int) -> StateStatistics:
    prefix = states[:train_end].astype(np.float64)
    residuals = np.diff(prefix, axis=0)
    arrays = (
        prefix.mean(axis=(0, 1)),
        np.maximum(prefix.std(axis=(0, 1)), 1.0e-6),
        residuals.mean(axis=(0, 1)),
        np.maximum(residuals.std(axis=(0, 1)), 1.0e-6),
    )
    return StateStatistics(*(torch.tensor(a, dtype=torch.float32).reshape(1, -1) for a in arrays))


def admissible_targets(train_end: int, context: int) -> list[int]:
    """One-based targets whose complete context and target lie in the prefix."""
    return list(range(context + 1, train_end + 1))


def input_dim(context: int) -> int:
    # k state levels, k-1 increments, xy, log-area, and three cycle features.
    return 4 * context + 4 * (context - 1) + 2 + 1 + 3


def normalized_temporal_features(
    context_states: torch.Tensor, coordinates: torch.Tensor, log_area: torch.Tensor,
    target_cycle: int | torch.Tensor, statistics: StateStatistics, max_cycle: int = 89,
) -> torch.Tensor:
    """Use only the declared oldest-to-newest context levels and increments."""
    if context_states.ndim != 3 or context_states.shape[-1] != len(STATE_NAMES):
        raise ValueError("context_states must have shape [k, n_elements, 4]")
    if context_states.shape[0] < 1:
        raise ValueError("temporal context must contain at least one cycle")
    normalized = (context_states - statistics.state_mean) / statistics.state_std
    levels = normalized.permute(1, 0, 2).reshape(len(coordinates), -1)
    temporal = levels
    if len(context_states) > 1:
        increments = ((context_states[1:] - context_states[:-1]) - statistics.residual_mean) / statistics.residual_std
        temporal = torch.cat([levels, increments.permute(1, 0, 2).reshape(len(coordinates), -1)], dim=-1)
    if not isinstance(target_cycle, torch.Tensor): target_cycle = context_states.new_tensor(float(target_cycle))
    phase = target_cycle.reshape(1, 1).expand(len(coordinates), 1) / float(max_cycle)
    return torch.cat([temporal, coordinates, log_area, phase,
                      torch.sin(2.0 * torch.pi * phase), torch.cos(2.0 * torch.pi * phase)], dim=-1)


def build_model(args: argparse.Namespace) -> torch.nn.Module:
    if args.model == "pointwise":
        if args.context != 1:
            raise ValueError("pointwise baseline is defined only for k=1")
        return PointwiseResidualOperator(input_dim(1), args.pointwise_hidden, 4)
    return MultiScaleMeshResidualOperator(
        input_dim(args.context), args.hidden, 4, args.local_layers, args.coarse_layers
    )


def load_dataset(path: Path, device: torch.device):
    data = np.load(path, allow_pickle=False)
    validate_dataset_scope(data)
    cycles = np.asarray(data["cycles"], dtype=int)
    if not np.array_equal(cycles, np.arange(1, LOCKED_CYCLE + 1)):
        raise ValueError("dataset must contain ordered c1-c89")
    states = torch.from_numpy(np.asarray(data["states"], dtype=np.float32)).to(device)
    graph = {name: torch.from_numpy(np.asarray(data[name])).to(device) for name in (
        "coordinates", "log_area", "areas", "edge_index", "edge_attr",
        "cluster_index", "coarse_edge_index", "coarse_edge_attr",
    )}
    for name in ("edge_index", "cluster_index", "coarse_edge_index"):
        graph[name] = graph[name].long()
    return data, states, graph


def predict_next(model, context_states, target_cycle, graph, statistics):
    features = normalized_temporal_features(
        context_states, graph["coordinates"], graph["log_area"], target_cycle, statistics
    )
    residual = model(features, graph["edge_index"], graph["edge_attr"], graph["cluster_index"],
                     graph["coarse_edge_index"], graph["coarse_edge_attr"])
    return apply_state_constraints(context_states[-1], residual, statistics)


def rollout(model, known_context, origin_cycle, horizon, graph, statistics):
    history = deque((state for state in known_context), maxlen=len(known_context))
    predictions = {}
    model.eval()
    with torch.no_grad():
        for target_cycle in range(origin_cycle + 1, origin_cycle + horizon + 1):
            current = predict_next(model, torch.stack(tuple(history)), target_cycle, graph, statistics)
            predictions[target_cycle] = current
            history.append(current)
    return predictions


def write_rows(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def metric_row(model_name, train_end, context, origin, target_cycle, prediction, target, areas, phase):
    row = {
        "model": model_name, "train_end": train_end, "context_k": context,
        "origin_cycle": origin, "target_cycle": target_cycle,
        "horizon": target_cycle - origin, "phase": phase,
    }
    row.update(field_metrics(prediction, target, areas))
    weights = areas / areas.sum()
    pred_hist = np.log10(np.maximum(prediction[:, 1], 1.0e-12))
    target_hist = np.log10(np.maximum(target[:, 1], 1.0e-12))
    hist_error = pred_hist - target_hist
    row["history_log_mae"] = float(np.sum(weights * np.abs(hist_error)))
    row["history_log_rmse"] = float(np.sqrt(np.sum(weights * hist_error**2)))
    from train_fem_mechanism_mesh_operator import weighted_correlation
    row["history_log_correlation"] = weighted_correlation(pred_hist, target_hist, areas)
    return row


def evaluate_nonlocked(model, data, states, graph, statistics, args, runtime, parameter_count):
    areas = np.asarray(data["areas"], dtype=np.float64)
    state_np = np.asarray(data["states"], dtype=np.float32)
    rows = []
    predictions = {}
    origins = [(args.train_end, "cutoff_rollout"), (NEAR_EVENT_ORIGIN, "near_event_rollout")]
    for origin, phase in origins:
        max_horizon = min(10, LOCKED_CYCLE - 1 - origin)
        if max_horizon < 1:
            continue
        known = states[origin - args.context:origin]
        rolled = rollout(model, known, origin, max_horizon, graph, statistics)
        for horizon in range(1, max_horizon + 1):
            cycle = origin + horizon
            pred = rolled[cycle].cpu().numpy()
            row = metric_row(args.model, args.train_end, args.context, origin, cycle,
                             pred, state_np[cycle - 1], areas, phase)
            row["headline_horizon"] = horizon in NONLOCKED_HORIZONS
            rows.append(row)
            predictions[f"origin_c{origin}_h{horizon}"] = pred
    for row in rows:
        row["runtime_seconds"] = runtime
        row["parameter_count"] = parameter_count
    write_rows(args.out / "nonlocked_metrics.csv", rows)
    np.savez_compressed(args.out / "nonlocked_predictions.npz", **predictions)


def base_manifest(args, data, parameter_count, runtime):
    return {
        "schema": "fem_cycle_forecast_data_efficiency_v1",
        "claim_class": "trajectory-sufficiency",
        "trajectory_generalization": False,
        "assimilation_eligible": False,
        "quarantine_reason": "one physical FEM trajectory; within-trajectory temporal holdout only",
        "model": args.model,
        "train_end": args.train_end,
        "context_k": args.context,
        "seed": args.seed,
        "fixed_training_steps": args.steps,
        "parameter_count": parameter_count,
        "runtime_seconds": runtime,
        "dataset": str(args.dataset.resolve()),
        "dataset_sha256": sha256(args.dataset),
        "code_commit": args.code_commit,
        "trajectory_id": str(np.asarray(data["trajectory_id"]).item()),
        "physics_family": str(np.asarray(data["physics_family"]).item()),
        "split": {
            "normalization_cycles": f"c1-c{args.train_end}",
            "training_targets": f"c{args.context + 1}-c{args.train_end}",
            "model_selection": "none; architecture, seed, optimizer, and fixed step budget predeclared",
            "cutoff_evaluation_origin": args.train_end,
            "near_event_origin": NEAR_EVENT_ORIGIN,
            "locked_final_cycle": LOCKED_CYCLE,
        },
        "firewall": {
            "future_used_for_training": False,
            "future_used_for_normalization": False,
            "future_used_for_model_selection": False,
            "threshold_selection": "per-target FEM area-weighted p99 metric definition; not tuned",
            "c89_opened_during_training_or_nonlocked_evaluation": False,
            "architecture_tuned_on_c89": False,
        },
        "semantics": {
            "state": list(STATE_NAMES),
            "raw_driver": "FEM cycle-peak raw tensile driver",
            "derived_active": "eta0 diagnostic: (1-damage)^2 * psi_raw",
            "fem_is_reference": True,
        },
    }


def train(args):
    set_seed(args.seed)
    device = choose_device(args.device)
    data, states, graph = load_dataset(args.dataset, device)
    if args.inspect_only:
        print(json.dumps({"dataset": str(args.dataset), "shape": list(states.shape),
                          "targets": admissible_targets(args.train_end, args.context),
                          "input_dim": input_dim(args.context)}, indent=2))
        return
    if device.type != "cuda" and not args.allow_non_cuda_training:
        raise RuntimeError("training is producer-GPU only; use --inspect-only on Mac")
    statistics = compute_prefix_statistics(np.asarray(data["states"]), args.train_end).to(device)
    model = build_model(args).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    targets = admissible_targets(args.train_end, args.context)
    generator = random.Random(args.seed)
    area = graph["areas"].reshape(-1)
    args.out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    history = []
    for step in range(1, args.steps + 1):
        target_cycle = generator.choice(targets)
        context_states = states[target_cycle - args.context - 1:target_cycle - 1]
        model.train(); optimizer.zero_grad(set_to_none=True)
        prediction = predict_next(model, context_states, target_cycle, graph, statistics)
        loss, parts = mechanism_loss(prediction, states[target_cycle - 1], area, graph["edge_index"],
                                     active_weight=args.active_weight,
                                     support_weight=args.support_weight,
                                     gradient_weight=args.gradient_weight)
        loss.backward()
        grad = float(torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip).cpu())
        optimizer.step()
        if not torch.isfinite(loss):
            raise FloatingPointError(f"non-finite loss at step {step}")
        if step == 1 or step % args.log_every == 0 or step == args.steps:
            row = {"step": step, "target_cycle": target_cycle, "loss": float(loss.detach().cpu()),
                   "gradient_norm": grad, "elapsed_seconds": time.time() - started}
            row.update({f"loss_{key}": float(value.cpu()) for key, value in parts.items()})
            history.append(row); print(json.dumps(row), flush=True)
    runtime = time.time() - started
    parameter_count = sum(p.numel() for p in model.parameters())
    checkpoint = {"model": model.state_dict(), "statistics": {
        key: getattr(statistics, key).cpu() for key in
        ("state_mean", "state_std", "residual_mean", "residual_std")},
        "args": vars(args), "runtime_seconds": runtime, "parameter_count": parameter_count}
    torch.save(checkpoint, args.out / "final_model.pt")
    write_rows(args.out / "training_history.csv", history)
    evaluate_nonlocked(model, data, states, graph, statistics, args, runtime, parameter_count)
    manifest = base_manifest(args, data, parameter_count, runtime)
    manifest["primary_assets"] = ["final_model.pt", "training_history.csv",
                                   "nonlocked_metrics.csv", "nonlocked_predictions.npz"]
    (args.out / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", choices=("pointwise", "temporal_mesh"), required=True)
    parser.add_argument("--train-end", type=int, choices=ALLOWED_TRAIN_ENDS, required=True)
    parser.add_argument("--context", type=int, choices=ALLOWED_CONTEXTS, required=True)
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--hidden", type=int, default=96)
    parser.add_argument("--pointwise-hidden", type=int, default=400)
    parser.add_argument("--local-layers", type=int, default=3)
    parser.add_argument("--coarse-layers", type=int, default=2)
    parser.add_argument("--lr", type=float, default=2.0e-4)
    parser.add_argument("--weight-decay", type=float, default=1.0e-5)
    parser.add_argument("--active-weight", type=float, default=1.0)
    parser.add_argument("--support-weight", type=float, default=0.25)
    parser.add_argument("--gradient-weight", type=float, default=0.1)
    parser.add_argument("--grad-clip", type=float, default=1.0)
    parser.add_argument("--log-every", type=int, default=100)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--inspect-only", action="store_true")
    parser.add_argument("--allow-non-cuda-training", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.model == "pointwise" and args.context != 1:
        parser.error("pointwise requires --context 1")
    return args


if __name__ == "__main__":
    train(parse_args())
