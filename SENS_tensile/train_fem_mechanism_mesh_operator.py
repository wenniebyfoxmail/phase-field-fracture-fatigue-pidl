#!/usr/bin/env python3
"""Train and evaluate a single-trajectory FEM mechanism-operator diagnostic.

Real training belongs on a producer GPU.  Mac use is limited to imports and
unit tests.  The locked test is a recurrent c76->c89 rollout; random element
splits and teacher-forced c89 evaluation are intentionally unsupported.

This runner cannot establish trajectory generalisation or enter the reality
assimilation model library. It requires an explicit diagnostic-only flag.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
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
    derived_active_log10,
    mechanism_loss,
    normalized_node_features,
)


AUDIT_CYCLES = frozenset({20, 40})
TRAIN_END = 67
VALIDATION_END = 76
TEST_END = 89


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def choose_device(name: str) -> torch.device:
    if name != "auto":
        return torch.device(name)
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def training_window_starts(
    rollout_steps: int,
    train_end: int = TRAIN_END,
    audit_cycles: frozenset[int] = AUDIT_CYCLES,
) -> list[int]:
    """Cycles usable as rollout inputs without touching masked audit states."""
    starts = []
    for start in range(1, train_end - rollout_steps + 1):
        window = set(range(start, start + rollout_steps + 1))
        if window.isdisjoint(audit_cycles):
            starts.append(start)
    return starts


def compute_statistics(states: np.ndarray) -> StateStatistics:
    allowed_cycles = [cycle for cycle in range(1, TRAIN_END + 1) if cycle not in AUDIT_CYCLES]
    selected = states[np.asarray(allowed_cycles) - 1].astype(np.float64)
    state_mean = selected.mean(axis=(0, 1))
    state_std = selected.std(axis=(0, 1))

    transition_cycles = [
        cycle for cycle in range(1, TRAIN_END)
        if cycle not in AUDIT_CYCLES and cycle + 1 not in AUDIT_CYCLES
    ]
    residuals = np.stack(
        [states[cycle] - states[cycle - 1] for cycle in transition_cycles], axis=0
    ).astype(np.float64)
    residual_mean = residuals.mean(axis=(0, 1))
    residual_std = residuals.std(axis=(0, 1))
    state_std = np.maximum(state_std, 1.0e-6)
    residual_std = np.maximum(residual_std, 1.0e-6)
    return StateStatistics(*(
        torch.tensor(array, dtype=torch.float32).reshape(1, -1)
        for array in (state_mean, state_std, residual_mean, residual_std)
    ))


def area_weighted_quantile(values: np.ndarray, areas: np.ndarray, quantile: float) -> float:
    order = np.argsort(values)
    cumulative = np.cumsum(areas[order])
    index = int(np.searchsorted(cumulative, quantile * cumulative[-1], side="left"))
    return float(values[order[min(index, len(order) - 1)]])


def weighted_correlation(a: np.ndarray, b: np.ndarray, weights: np.ndarray) -> float:
    weights = weights / weights.sum()
    a0 = a - np.sum(weights * a)
    b0 = b - np.sum(weights * b)
    denominator = np.sqrt(np.sum(weights * a0 * a0) * np.sum(weights * b0 * b0))
    return float(np.sum(weights * a0 * b0) / denominator) if denominator > 0 else float("nan")


def field_metrics(
    prediction: np.ndarray,
    target: np.ndarray,
    areas: np.ndarray,
) -> dict[str, float]:
    weights = areas / areas.sum()
    result: dict[str, float] = {}
    for index, name in enumerate(STATE_NAMES):
        error = prediction[:, index] - target[:, index]
        result[f"{name}_mae"] = float(np.sum(weights * np.abs(error)))
        result[f"{name}_rmse"] = float(np.sqrt(np.sum(weights * error * error)))
        result[f"{name}_correlation"] = weighted_correlation(
            prediction[:, index], target[:, index], areas
        )

    pred_active = derived_active_log10(torch.from_numpy(prediction)).numpy()
    target_active = derived_active_log10(torch.from_numpy(target)).numpy()
    active_error = pred_active - target_active
    result["derived_active_log_mae"] = float(np.sum(weights * np.abs(active_error)))
    result["derived_active_log_rmse"] = float(np.sqrt(np.sum(weights * active_error**2)))
    result["derived_active_correlation"] = weighted_correlation(pred_active, target_active, areas)

    threshold = area_weighted_quantile(target_active, areas, 0.99)
    target_mask = target_active >= threshold
    pred_mask = pred_active >= threshold
    intersection = float(areas[target_mask & pred_mask].sum())
    union = float(areas[target_mask | pred_mask].sum())
    result["absolute_p99_iou"] = intersection / union if union else float("nan")
    target_area = float(areas[target_mask].sum())
    result["absolute_support_area_ratio"] = (
        float(areas[pred_mask].sum()) / target_area if target_area else float("nan")
    )

    pred_threshold = area_weighted_quantile(pred_active, areas, 0.99)
    pred_own = pred_active >= pred_threshold
    own_intersection = float(areas[target_mask & pred_own].sum())
    own_union = float(areas[target_mask | pred_own].sum())
    result["own_p99_iou"] = own_intersection / own_union if own_union else float("nan")
    return result


def rollout(
    model: torch.nn.Module,
    initial_state: torch.Tensor,
    start_cycle: int,
    end_cycle: int,
    graph: dict[str, torch.Tensor],
    statistics: StateStatistics,
) -> dict[int, torch.Tensor]:
    current = initial_state
    predictions: dict[int, torch.Tensor] = {start_cycle: current}
    model.eval()
    with torch.no_grad():
        for target_cycle in range(start_cycle + 1, end_cycle + 1):
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
            current = apply_state_constraints(current, residual, statistics)
            predictions[target_cycle] = current
    return predictions


def validation_score(
    model: torch.nn.Module,
    states: torch.Tensor,
    graph: dict[str, torch.Tensor],
    statistics: StateStatistics,
) -> float:
    predictions = rollout(
        model, states[TRAIN_END - 1], TRAIN_END, VALIDATION_END, graph, statistics
    )
    scores = []
    for cycle in range(TRAIN_END + 1, VALIDATION_END + 1):
        error = predictions[cycle] - states[cycle - 1]
        scores.append(float(error.square().mean().cpu()))
    return float(np.mean(scores))


def build_model(args: argparse.Namespace, input_dim: int) -> torch.nn.Module:
    if args.model == "pointwise":
        return PointwiseResidualOperator(input_dim, args.hidden, 4)
    return MultiScaleMeshResidualOperator(
        input_dim,
        hidden_dim=args.hidden,
        output_dim=4,
        local_layers=args.local_layers,
        coarse_layers=args.coarse_layers,
    )


def validate_dataset_scope(data) -> tuple[str, str]:
    required_scope = {"trajectory_id", "physics_family", "trajectory_count"}
    available = set(data.files) if hasattr(data, "files") else set(data)
    missing_scope = sorted(required_scope - available)
    if missing_scope:
        raise ValueError(f"dataset lacks provenance/scope fields: {missing_scope}")
    if int(np.asarray(data["trajectory_count"]).reshape(-1)[0]) != 1:
        raise ValueError("this diagnostic runner accepts exactly one trajectory")
    trajectory_id = str(np.asarray(data["trajectory_id"]).item()).strip()
    physics_family = str(np.asarray(data["physics_family"]).item()).strip()
    if not trajectory_id or not physics_family:
        raise ValueError("dataset trajectory_id and physics_family must be non-empty")
    return trajectory_id, physics_family


def load_dataset(path: Path, device: torch.device) -> tuple[np.lib.npyio.NpzFile, torch.Tensor, dict[str, torch.Tensor]]:
    data = np.load(path, allow_pickle=False)
    validate_dataset_scope(data)
    cycles = np.asarray(data["cycles"], dtype=int)
    if not np.array_equal(cycles, np.arange(1, 90)):
        raise ValueError("dataset must contain a complete ordered cycle 1..89 trajectory")
    states = torch.from_numpy(np.asarray(data["states"], dtype=np.float32)).to(device)
    graph = {
        name: torch.from_numpy(np.asarray(data[name])).to(device)
        for name in (
            "coordinates", "log_area", "areas", "edge_index", "edge_attr",
            "cluster_index", "coarse_edge_index", "coarse_edge_attr",
        )
    }
    graph["edge_index"] = graph["edge_index"].long()
    graph["cluster_index"] = graph["cluster_index"].long()
    graph["coarse_edge_index"] = graph["coarse_edge_index"].long()
    return data, states, graph


def train(args: argparse.Namespace) -> None:
    set_seed(args.seed)
    device = choose_device(args.device)
    data, states, graph = load_dataset(args.dataset, device)
    statistics = compute_statistics(np.asarray(data["states"], dtype=np.float32)).to(device)
    input_dim = 4 + 2 + 1 + 3
    model = build_model(args, input_dim).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    starts = training_window_starts(args.rollout_steps)
    generator = random.Random(args.seed)
    area = graph["areas"].reshape(-1)

    args.out.mkdir(parents=True, exist_ok=True)
    best_path = args.out / "best_model.pt"
    history: list[dict[str, float | int]] = []
    best_score = float("inf")
    stale = 0
    started = time.time()
    for step in range(1, args.steps + 1):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        start_cycle = generator.choice(starts)
        current = states[start_cycle - 1]
        losses = []
        parts_accumulator: dict[str, float] = {}
        for target_cycle in range(start_cycle + 1, start_cycle + args.rollout_steps + 1):
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
            current = apply_state_constraints(current, residual, statistics)
            loss, parts = mechanism_loss(
                current,
                states[target_cycle - 1],
                area,
                graph["edge_index"],
                active_weight=args.active_weight,
                support_weight=args.support_weight,
                gradient_weight=args.gradient_weight,
            )
            losses.append(loss)
            for key, value in parts.items():
                parts_accumulator[key] = parts_accumulator.get(key, 0.0) + float(value.cpu())
        total = torch.stack(losses).mean()
        total.backward()
        gradient_norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip).cpu())
        optimizer.step()

        if not torch.isfinite(total):
            raise FloatingPointError(f"non-finite loss at step {step}")
        if step == 1 or step % args.eval_every == 0 or step == args.steps:
            score = validation_score(model, states, graph, statistics)
            row: dict[str, float | int] = {
                "step": step,
                "train_start_cycle": start_cycle,
                "train_loss": float(total.detach().cpu()),
                "gradient_norm": gradient_norm,
                "validation_rollout_mse": score,
                "elapsed_seconds": time.time() - started,
            }
            row.update({f"loss_{key}": value / args.rollout_steps for key, value in parts_accumulator.items()})
            history.append(row)
            print(json.dumps(row), flush=True)
            if score < best_score:
                best_score = score
                stale = 0
                torch.save(
                    {
                        "model": model.state_dict(),
                        "args": vars(args),
                        "statistics": {
                            "state_mean": statistics.state_mean.cpu(),
                            "state_std": statistics.state_std.cpu(),
                            "residual_mean": statistics.residual_mean.cpu(),
                            "residual_std": statistics.residual_std.cpu(),
                        },
                        "best_validation_rollout_mse": best_score,
                    },
                    best_path,
                )
            else:
                stale += 1
                if stale >= args.patience:
                    print(f"early stop after {stale} validation checks without improvement")
                    break

    with (args.out / "training_history.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(history[0]))
        writer.writeheader()
        writer.writerows(history)

    checkpoint = torch.load(best_path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model"])
    evaluate(model, states, graph, statistics, data, args, checkpoint)


def evaluate(
    model: torch.nn.Module,
    states: torch.Tensor,
    graph: dict[str, torch.Tensor],
    statistics: StateStatistics,
    data: np.lib.npyio.NpzFile,
    args: argparse.Namespace,
    checkpoint: dict,
) -> None:
    areas = np.asarray(data["areas"], dtype=np.float64).reshape(-1)
    rows: list[dict[str, float | int | str]] = []

    def add_row(label: str, cycle: int, prediction: torch.Tensor) -> None:
        metrics = field_metrics(
            prediction.detach().cpu().numpy(),
            states[cycle - 1].detach().cpu().numpy(),
            areas,
        )
        rows.append({"comparison": label, "cycle": cycle, **metrics})

    # Masked one-step audits. These transitions were excluded from training.
    for audit_cycle in sorted(AUDIT_CYCLES):
        predicted = rollout(
            model,
            states[audit_cycle - 2],
            audit_cycle - 1,
            audit_cycle,
            graph,
            statistics,
        )[audit_cycle]
        add_row("masked_one_step_audit", audit_cycle, predicted)

    validation = rollout(model, states[TRAIN_END - 1], TRAIN_END, VALIDATION_END, graph, statistics)
    for cycle in (69, 73, 76):
        add_row("validation_rollout_from_c67", cycle, validation[cycle])

    locked = rollout(model, states[VALIDATION_END - 1], VALIDATION_END, TEST_END, graph, statistics)
    for cycle in (78, 80, 84, 89):
        add_row("locked_rollout_from_c76", cycle, locked[cycle])

    long_rollout = rollout(model, states[TRAIN_END - 1], TRAIN_END, TEST_END, graph, statistics)
    add_row("stress_rollout_from_c67", 89, long_rollout[89])

    persistence = states[VALIDATION_END - 1]
    add_row("persistence_from_c76", 89, persistence)

    metrics_path = args.out / "fem_centred_metrics.csv"
    with metrics_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    np.savez_compressed(
        args.out / "locked_predictions.npz",
        c20=rollout(model, states[18], 19, 20, graph, statistics)[20].cpu().numpy(),
        c40=rollout(model, states[38], 39, 40, graph, statistics)[40].cpu().numpy(),
        c76=validation[76].cpu().numpy(),
        c89=locked[89].cpu().numpy(),
        c89_from_c67=long_rollout[89].cpu().numpy(),
        state_names=np.asarray(STATE_NAMES),
    )

    run_manifest = {
        "claim_class": "tooling-only",
        "trajectory_generalization": False,
        "assimilation_eligible": False,
        "quarantine_reason": "within-trajectory cycle holdout cannot validate unseen physical trajectories",
        "model": args.model,
        "dataset": str(args.dataset.resolve()),
        "seed": args.seed,
        "device": str(next(model.parameters()).device),
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "trajectory_id": str(np.asarray(data["trajectory_id"]).item()),
        "physics_family": str(np.asarray(data["physics_family"]).item()),
        "split": {
            "train_targets": "c2-c67 excluding c20/c40 and touching transitions",
            "masked_audits": [20, 40],
            "validation_rollout": "c67->c76",
            "locked_test_rollout": "c76->c89",
            "stress_rollout": "c67->c89",
        },
        "semantics": {
            "psi_target": "FEM cycle-peak raw tensile driver",
            "derived_active": "eta0 diagnostic: (1-damage)^2 * psi_raw",
            "fem_reference": True,
        },
        "best_validation_rollout_mse": checkpoint["best_validation_rollout_mse"],
        "primary_assets": [str(metrics_path.name), "locked_predictions.npz", "best_model.pt"],
    }
    (args.out / "RUN_MANIFEST.json").write_text(
        json.dumps(run_manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(run_manifest, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", choices=("pointwise", "multiscale"), default="multiscale")
    parser.add_argument("--hidden", type=int, default=96)
    parser.add_argument("--local-layers", type=int, default=3)
    parser.add_argument("--coarse-layers", type=int, default=2)
    parser.add_argument("--rollout-steps", type=int, default=3)
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--eval-every", type=int, default=100)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--lr", type=float, default=3.0e-4)
    parser.add_argument("--weight-decay", type=float, default=1.0e-6)
    parser.add_argument("--active-weight", type=float, default=1.0)
    parser.add_argument("--support-weight", type=float, default=0.25)
    parser.add_argument("--gradient-weight", type=float, default=0.1)
    parser.add_argument("--grad-clip", type=float, default=5.0)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--device", default="auto")
    parser.add_argument(
        "--allow-single-trajectory-diagnostic",
        action="store_true",
        help="Required acknowledgement: output is tooling-only and assimilation-ineligible.",
    )
    args = parser.parse_args()
    if args.rollout_steps < 1:
        parser.error("--rollout-steps must be positive")
    if args.steps < 1 or args.eval_every < 1:
        parser.error("--steps and --eval-every must be positive")
    if not args.allow_single_trajectory_diagnostic:
        parser.error(
            "single-trajectory training is quarantined; pass "
            "--allow-single-trajectory-diagnostic only for a producer-side tooling diagnostic"
        )
    return args


if __name__ == "__main__":
    train(parse_args())
