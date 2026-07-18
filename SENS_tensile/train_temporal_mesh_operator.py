#!/usr/bin/env python3
"""Train a leakage-audited temporal FEM mesh-operator diagnostic.

Real optimisation belongs on Taobo, CSD3, or Windows-PIDL.  Mac use is limited
to imports, unit tests, parameter planning, and static validation.  The runner
supports variable training contexts and chooses the inference context using
only a c67-origin recurrent validation rollout through c76.

The c76-origin c77-c89 interval is a reused evaluation benchmark, not a fresh
statistically locked test.  Outputs remain within-trajectory and quarantined.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
import time
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from fem_mechanism_operator import StateStatistics, derived_active_log10  # noqa: E402
from temporal_mesh_operator import (  # noqa: E402
    TEMPORAL_FAMILIES,
    TemporalMeshOperator,
    apply_directional_state_update,
    count_parameters,
    parameter_breakdown,
    temporal_mechanism_loss,
)


TRAIN_END = 67
VALIDATION_END = 76
EVALUATION_END = 89
DEFAULT_CONTEXTS = (1, 3, 5, 10, 20)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def choose_device(name: str) -> torch.device:
    if name != "auto":
        return torch.device(name)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def parse_int_list(text: str) -> tuple[int, ...]:
    values = tuple(sorted({int(value.strip()) for value in text.split(",") if value.strip()}))
    if not values or values[0] < 1:
        raise argparse.ArgumentTypeError("context lengths must be positive integers")
    return values


def validate_dataset_scope(data) -> tuple[str, str]:
    required = {"trajectory_id", "physics_family", "trajectory_count"}
    available = set(data.files) if hasattr(data, "files") else set(data)
    missing = sorted(required - available)
    if missing:
        raise ValueError(f"dataset lacks provenance/scope fields: {missing}")
    if int(np.asarray(data["trajectory_count"]).reshape(-1)[0]) != 1:
        raise ValueError("this runner currently accepts exactly one quarantined trajectory")
    trajectory_id = str(np.asarray(data["trajectory_id"]).item()).strip()
    physics_family = str(np.asarray(data["physics_family"]).item()).strip()
    if not trajectory_id or not physics_family:
        raise ValueError("trajectory_id and physics_family must be non-empty")
    return trajectory_id, physics_family


def load_dataset(
    path: Path,
    device: torch.device,
    *,
    use_loading_metadata: bool,
) -> tuple[np.lib.npyio.NpzFile, torch.Tensor, dict[str, torch.Tensor], torch.Tensor | None]:
    data = np.load(path, allow_pickle=False)
    validate_dataset_scope(data)
    cycles = np.asarray(data["cycles"], dtype=int)
    if not np.array_equal(cycles, np.arange(1, EVALUATION_END + 1)):
        raise ValueError("dataset must contain an ordered c1-c89 trajectory")
    states = torch.from_numpy(np.asarray(data["states"], dtype=np.float32)).to(device)
    graph = {
        name: torch.from_numpy(np.asarray(data[name])).to(device)
        for name in (
            "coordinates",
            "log_area",
            "areas",
            "edge_index",
            "edge_attr",
            "cluster_index",
            "coarse_edge_index",
            "coarse_edge_attr",
        )
    }
    graph["edge_index"] = graph["edge_index"].long()
    graph["cluster_index"] = graph["cluster_index"].long()
    graph["coarse_edge_index"] = graph["coarse_edge_index"].long()

    metadata = None
    if use_loading_metadata:
        if "loading_metadata" not in data.files:
            raise ValueError(
                "--use-loading-metadata requested, but the sealed dataset has no "
                "forecast-time loading_metadata; do not substitute cycle index"
            )
        metadata_values = np.asarray(data["loading_metadata"], dtype=np.float32)
        if metadata_values.ndim != 2 or len(metadata_values) != len(states):
            raise ValueError("loading_metadata must have shape [cycles, channels]")
        metadata = torch.from_numpy(metadata_values).to(device)
    return data, states, graph, metadata


def compute_statistics(states: np.ndarray, train_end: int = TRAIN_END) -> StateStatistics:
    """Compute every normalisation quantity from c1-c67 only."""
    selected = states[:train_end].astype(np.float64)
    residuals = np.diff(selected, axis=0)
    state_mean = selected.mean(axis=(0, 1))
    state_std = np.maximum(selected.std(axis=(0, 1)), 1.0e-6)
    residual_mean = residuals.mean(axis=(0, 1))
    residual_std = np.maximum(residuals.std(axis=(0, 1)), 1.0e-6)
    return StateStatistics(*(
        torch.tensor(array, dtype=torch.float32).reshape(1, -1)
        for array in (state_mean, state_std, residual_mean, residual_std)
    ))


def training_origins(
    context_length: int,
    rollout_steps: int,
    *,
    train_end: int = TRAIN_END,
) -> list[int]:
    """Return origin cycles whose history and targets lie wholly in training."""
    if context_length < 1 or rollout_steps < 1:
        raise ValueError("context_length and rollout_steps must be positive")
    return list(range(context_length, train_end - rollout_steps + 1))


def history_slice(
    states: torch.Tensor,
    origin_cycle: int,
    context_length: int,
) -> torch.Tensor:
    start = origin_cycle - context_length
    if start < 0 or origin_cycle > len(states):
        raise ValueError("history slice crosses the available trajectory boundary")
    result = states[start:origin_cycle]
    if len(result) != context_length:
        raise AssertionError("history slice has the wrong length")
    return result


def metadata_slice(
    metadata: torch.Tensor | None,
    origin_cycle: int,
    context_length: int,
) -> torch.Tensor | None:
    if metadata is None:
        return None
    return metadata[origin_cycle - context_length:origin_cycle]


def predict_next(
    model: TemporalMeshOperator,
    history: torch.Tensor,
    graph: Mapping[str, torch.Tensor],
    statistics: StateStatistics,
    metadata_history: torch.Tensor | None,
) -> torch.Tensor:
    raw_update = model(
        history,
        graph,
        statistics,
        metadata_history,
        recurrent_ssm=not model.training,
    )
    return apply_directional_state_update(history[-1], raw_update, statistics)


def apply_observation_reset(
    prediction: torch.Tensor,
    observation: torch.Tensor,
    mode: str,
) -> torch.Tensor:
    if mode == "none":
        return prediction
    result = prediction.clone()
    if mode == "raw":
        result[:, 3] = observation[:, 3]
    elif mode == "full":
        result = observation.clone()
    else:
        raise ValueError(f"unknown observation reset mode {mode}")
    return result


def rollout(
    model: TemporalMeshOperator,
    states: torch.Tensor,
    origin_cycle: int,
    end_cycle: int,
    context_length: int,
    graph: Mapping[str, torch.Tensor],
    statistics: StateStatistics,
    metadata: torch.Tensor | None,
    *,
    reset_cycle: int | None = None,
    reset_mode: str = "none",
) -> dict[int, torch.Tensor]:
    if end_cycle <= origin_cycle:
        raise ValueError("rollout end must be after origin")
    history = [state for state in history_slice(states, origin_cycle, context_length)]
    predictions: dict[int, torch.Tensor] = {origin_cycle: history[-1]}
    model.eval()
    with torch.no_grad():
        for target_cycle in range(origin_cycle + 1, end_cycle + 1):
            current_history = torch.stack(history[-context_length:], dim=0)
            current_metadata = None
            if metadata is not None:
                current_metadata = metadata[target_cycle - context_length - 1:target_cycle - 1]
                if len(current_metadata) != context_length:
                    raise ValueError("metadata context crosses a split boundary")
            prediction = predict_next(
                model, current_history, graph, statistics, current_metadata
            )
            if reset_cycle == target_cycle:
                prediction = apply_observation_reset(
                    prediction, states[target_cycle - 1], reset_mode
                )
            predictions[target_cycle] = prediction
            history.append(prediction)
    return predictions


def area_weighted_quantile(
    values: np.ndarray,
    areas: np.ndarray,
    quantile: float,
) -> float:
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


def support_morphology(
    mask: np.ndarray,
    coordinates: np.ndarray,
    areas: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    selected = areas * mask.astype(float)
    if selected.sum() <= 0:
        return np.full(2, np.nan), np.full(2, np.nan)
    weights = selected / selected.sum()
    centroid = np.sum(weights[:, None] * coordinates, axis=0)
    width = np.sqrt(np.sum(weights[:, None] * (coordinates - centroid) ** 2, axis=0))
    return centroid, width


def field_metrics(
    prediction: np.ndarray,
    target: np.ndarray,
    areas: np.ndarray,
    coordinates: np.ndarray,
    edge_index: np.ndarray,
) -> dict[str, float]:
    weights = areas / areas.sum()
    names = ("damage", "alpha_bar", "fatigue_degradation", "log10_psi_raw")
    result: dict[str, float] = {}
    for index, name in enumerate(names):
        error = prediction[:, index] - target[:, index]
        result[f"{name}_mae"] = float(np.sum(weights * np.abs(error)))
        result[f"{name}_rmse"] = float(np.sqrt(np.sum(weights * error**2)))
        result[f"{name}_correlation"] = weighted_correlation(
            prediction[:, index], target[:, index], areas
        )

    pred_active = derived_active_log10(torch.from_numpy(prediction)).numpy()
    target_active = derived_active_log10(torch.from_numpy(target)).numpy()
    error = pred_active - target_active
    result["active_log_mae"] = float(np.sum(weights * np.abs(error)))
    result["active_log_rmse"] = float(np.sqrt(np.sum(weights * error**2)))
    result["active_correlation"] = weighted_correlation(pred_active, target_active, areas)

    fem_threshold = area_weighted_quantile(target_active, areas, 0.99)
    target_mask = target_active >= fem_threshold
    pred_absolute = pred_active >= fem_threshold
    intersection = float(areas[target_mask & pred_absolute].sum())
    union = float(areas[target_mask | pred_absolute].sum())
    target_area = float(areas[target_mask].sum())
    result["absolute_p99_iou"] = intersection / union if union else float("nan")
    result["support_area_ratio"] = (
        float(areas[pred_absolute].sum()) / target_area if target_area else float("nan")
    )
    own_threshold = area_weighted_quantile(pred_active, areas, 0.99)
    pred_own = pred_active >= own_threshold
    own_intersection = float(areas[target_mask & pred_own].sum())
    own_union = float(areas[target_mask | pred_own].sum())
    result["own_p99_iou"] = own_intersection / own_union if own_union else float("nan")

    pred_centroid, pred_width = support_morphology(pred_own, coordinates, areas)
    target_centroid, target_width = support_morphology(target_mask, coordinates, areas)
    result["centroid_offset"] = float(np.linalg.norm(pred_centroid - target_centroid))
    result["width_x_error"] = float(abs(pred_width[0] - target_width[0]))
    result["width_y_error"] = float(abs(pred_width[1] - target_width[1]))

    src, dst = edge_index
    pred_jump = np.abs(pred_active[dst] - pred_active[src])
    target_jump = np.abs(target_active[dst] - target_active[src])
    result["active_neighbour_jump"] = float(np.mean(pred_jump))
    result["active_neighbour_jump_error"] = float(np.mean(np.abs(pred_jump - target_jump)))
    return result


def selection_composite(metrics: Mapping[str, float]) -> float:
    correlation = float(np.clip(metrics["active_correlation"], -1.0, 1.0))
    ratio = max(float(metrics["support_area_ratio"]), 1.0e-8)
    return float(
        metrics["active_log_mae"]
        + 0.5 * (1.0 - correlation)
        + (1.0 - metrics["absolute_p99_iou"])
        + 0.5 * abs(math.log(ratio))
        + 0.25 * metrics["centroid_offset"]
        + 0.25 * (metrics["width_x_error"] + metrics["width_y_error"])
    )


def metrics_for_rollout(
    predictions: Mapping[int, torch.Tensor],
    states: torch.Tensor,
    data,
    graph: Mapping[str, torch.Tensor],
    *,
    comparison: str,
    origin_cycle: int,
    context_length: int,
) -> list[dict[str, float | int | str]]:
    areas = np.asarray(data["areas"], dtype=np.float64).reshape(-1)
    coordinates = np.asarray(data["coordinates"], dtype=np.float64)
    edge_index = np.asarray(data["edge_index"], dtype=np.int64)
    rows = []
    for cycle, prediction in predictions.items():
        if cycle == origin_cycle:
            continue
        metrics = field_metrics(
            prediction.detach().cpu().numpy(),
            states[cycle - 1].detach().cpu().numpy(),
            areas,
            coordinates,
            edge_index,
        )
        rows.append(
            {
                "comparison": comparison,
                "origin_cycle": origin_cycle,
                "cycle": cycle,
                "horizon": cycle - origin_cycle,
                "context_length": context_length,
                "selection_composite": selection_composite(metrics),
                **metrics,
            }
        )
    return rows


def validation_context_scores(
    model: TemporalMeshOperator,
    states: torch.Tensor,
    graph: Mapping[str, torch.Tensor],
    statistics: StateStatistics,
    metadata: torch.Tensor | None,
    data,
    contexts: Iterable[int],
) -> dict[int, float]:
    scores: dict[int, float] = {}
    for context in contexts:
        predictions = rollout(
            model,
            states,
            TRAIN_END,
            VALIDATION_END,
            context,
            graph,
            statistics,
            metadata,
        )
        rows = metrics_for_rollout(
            predictions,
            states,
            data,
            graph,
            comparison="validation_rollout_c67_c76",
            origin_cycle=TRAIN_END,
            context_length=context,
        )
        values = np.asarray([float(row["selection_composite"]) for row in rows])
        # Give terminal validation localisation equal weight to the full path.
        scores[context] = float((values.mean() + values[-1]) / 2.0)
    return scores


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty table {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_model(args: argparse.Namespace, metadata_dim: int) -> TemporalMeshOperator:
    return TemporalMeshOperator(
        temporal_family=args.temporal_model,
        metadata_dim=metadata_dim,
        local_dim=args.local_dim,
        token_dim=args.token_dim,
        temporal_width=args.temporal_width,
        local_layers=args.local_layers,
        coarse_layers=args.coarse_layers,
        graph_enabled=args.spatial_encoder == "graph",
        max_context=max(args.context_lengths),
        transformer_heads=args.transformer_heads,
    )


def validate_capacity(model: TemporalMeshOperator, args: argparse.Namespace) -> None:
    parameters = count_parameters(model)
    relative_error = abs(parameters - args.parameter_target) / args.parameter_target
    if relative_error > args.parameter_tolerance:
        raise ValueError(
            f"capacity gate failed: {parameters} parameters differs from "
            f"target {args.parameter_target} by {relative_error:.2%}"
        )


def train(args: argparse.Namespace) -> None:
    if sys.platform == "darwin":
        raise RuntimeError(
            "training is disabled on Mac; use Taobo, CSD3, or Windows-PIDL"
        )
    set_seed(args.seed)
    device = choose_device(args.device)
    data, states, graph, metadata = load_dataset(
        args.dataset,
        device,
        use_loading_metadata=args.use_loading_metadata,
    )
    statistics = compute_statistics(np.asarray(data["states"], dtype=np.float32)).to(device)
    metadata_dim = 0 if metadata is None else int(metadata.shape[1])
    model = build_model(args, metadata_dim).to(device)
    validate_capacity(model, args)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.lr, weight_decay=args.weight_decay
    )
    generator = random.Random(args.seed)
    contexts = (1,) if args.temporal_model == "markov" else args.context_lengths
    origin_lookup = {
        context: training_origins(context, args.rollout_steps)
        for context in contexts
    }

    args.out.mkdir(parents=True, exist_ok=True)
    best_path = args.out / "best_model.pt"
    history_rows: list[dict] = []
    best_score = float("inf")
    stale = 0
    train_started = time.perf_counter()
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)

    for step in range(1, args.steps + 1):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        context = generator.choice(contexts)
        origin = generator.choice(origin_lookup[context])
        history = [state for state in history_slice(states, origin, context)]
        losses = []
        parts_sum: dict[str, float] = {}
        for target_cycle in range(origin + 1, origin + args.rollout_steps + 1):
            current_history = torch.stack(history[-context:], dim=0)
            current_metadata = None
            if metadata is not None:
                # The state history at this point ends at target_cycle - 1.
                # Forecast-time metadata follows that same moving window.
                current_metadata = metadata[
                    target_cycle - context - 1:target_cycle - 1
                ]
                if len(current_metadata) != context:
                    raise ValueError("training metadata context crosses a boundary")
            prediction = predict_next(
                model, current_history, graph, statistics, current_metadata
            )
            target = states[target_cycle - 1]
            loss, parts = temporal_mechanism_loss(
                prediction,
                target,
                graph,
                active_weight=args.active_weight,
                support_weight=args.support_weight,
                gradient_weight=args.gradient_weight,
                morphology_weight=args.morphology_weight,
                active_roughness_weight=args.active_roughness_weight,
            )
            losses.append(loss)
            for key, value in parts.items():
                parts_sum[key] = parts_sum.get(key, 0.0) + float(value.cpu())
            teacher_force = generator.random() < args.teacher_forcing_ratio
            history.append(target if teacher_force else prediction)

        total = torch.stack(losses).mean()
        if not torch.isfinite(total):
            raise FloatingPointError(f"non-finite loss at step {step}")
        total.backward()
        gradient_norm = float(
            torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip).cpu()
        )
        optimizer.step()

        if step == 1 or step % args.eval_every == 0 or step == args.steps:
            scores = validation_context_scores(
                model,
                states,
                graph,
                statistics,
                metadata,
                data,
                contexts,
            )
            selected_context = min(scores, key=scores.get)
            score = scores[selected_context]
            row = {
                "step": step,
                "train_origin_cycle": origin,
                "train_context_length": context,
                "train_loss": float(total.detach().cpu()),
                "gradient_norm": gradient_norm,
                "selected_validation_context": selected_context,
                "validation_selection_composite": score,
                "elapsed_seconds": time.perf_counter() - train_started,
            }
            row.update({f"validation_context_{key}": value for key, value in scores.items()})
            row.update(
                {
                    f"loss_{key}": value / args.rollout_steps
                    for key, value in parts_sum.items()
                }
            )
            history_rows.append(row)
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
                        "selected_context": selected_context,
                        "validation_context_scores": scores,
                        "best_validation_selection_composite": score,
                    },
                    best_path,
                )
            else:
                stale += 1
                if stale >= args.patience:
                    print(f"early stop after {stale} validation checks", flush=True)
                    break

    training_seconds = time.perf_counter() - train_started
    write_csv(args.out / "training_history.csv", history_rows)
    checkpoint = torch.load(best_path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model"])
    evaluate(
        model,
        states,
        graph,
        statistics,
        metadata,
        data,
        args,
        checkpoint,
        training_seconds=training_seconds,
    )


def evaluate(
    model: TemporalMeshOperator,
    states: torch.Tensor,
    graph: Mapping[str, torch.Tensor],
    statistics: StateStatistics,
    metadata: torch.Tensor | None,
    data,
    args: argparse.Namespace,
    checkpoint: Mapping,
    *,
    training_seconds: float,
) -> None:
    context = int(checkpoint["selected_context"])
    rows: list[dict] = []

    validation = rollout(
        model,
        states,
        TRAIN_END,
        VALIDATION_END,
        context,
        graph,
        statistics,
        metadata,
    )
    rows.extend(
        metrics_for_rollout(
            validation,
            states,
            data,
            graph,
            comparison="validation_rollout_c67_c76",
            origin_cycle=TRAIN_END,
            context_length=context,
        )
    )

    reused = rollout(
        model,
        states,
        VALIDATION_END,
        EVALUATION_END,
        context,
        graph,
        statistics,
        metadata,
    )
    rows.extend(
        metrics_for_rollout(
            reused,
            states,
            data,
            graph,
            comparison="reused_evaluation_rollout_c76_c89",
            origin_cycle=VALIDATION_END,
            context_length=context,
        )
    )

    # A 20-cycle post-selection diagnostic is possible only by starting at
    # c69, inside the already-used validation interval.  It is therefore
    # labelled reused and cannot support a held-out generalisation claim.
    reused_twenty = rollout(
        model,
        states,
        69,
        EVALUATION_END,
        context,
        graph,
        statistics,
        metadata,
    )
    rows.extend(
        metrics_for_rollout(
            reused_twenty,
            states,
            data,
            graph,
            comparison="reused_twenty_cycle_rollout_c69_c89",
            origin_cycle=69,
            context_length=context,
        )
    )

    for reset_mode in ("raw", "full"):
        reset = rollout(
            model,
            states,
            VALIDATION_END,
            EVALUATION_END,
            context,
            graph,
            statistics,
            metadata,
            reset_cycle=87,
            reset_mode=reset_mode,
        )
        rows.extend(
            metrics_for_rollout(
                reset,
                states,
                data,
                graph,
                comparison=f"oracle_c87_{reset_mode}_reset_c76_c89",
                origin_cycle=VALIDATION_END,
                context_length=context,
            )
        )

    true_history_restart = rollout(
        model,
        states,
        87,
        EVALUATION_END,
        context,
        graph,
        statistics,
        metadata,
    )
    rows.extend(
        metrics_for_rollout(
            true_history_restart,
            states,
            data,
            graph,
            comparison="oracle_true_history_restart_c87_c89",
            origin_cycle=87,
            context_length=context,
        )
    )

    # Teacher-forced next-cycle diagnostics are reported but never used for selection.
    for target_cycle in range(VALIDATION_END + 1, EVALUATION_END + 1):
        one_step = rollout(
            model,
            states,
            target_cycle - 1,
            target_cycle,
            context,
            graph,
            statistics,
            metadata,
        )
        rows.extend(
            metrics_for_rollout(
                one_step,
                states,
                data,
                graph,
                comparison="teacher_forced_reused_next_cycle",
                origin_cycle=target_cycle - 1,
                context_length=context,
            )
        )

    write_csv(args.out / "fem_centred_metrics.csv", rows)
    np.savez_compressed(
        args.out / "reused_evaluation_predictions.npz",
        c76=states[VALIDATION_END - 1].detach().cpu().numpy(),
        c87=reused[87].detach().cpu().numpy(),
        c89=reused[89].detach().cpu().numpy(),
        c89_raw_reset=rollout(
            model,
            states,
            VALIDATION_END,
            EVALUATION_END,
            context,
            graph,
            statistics,
            metadata,
            reset_cycle=87,
            reset_mode="raw",
        )[89].detach().cpu().numpy(),
        selected_context=np.asarray(context),
    )

    # Seek-safe inference timing after one warm-up rollout.
    rollout(
        model,
        states,
        TRAIN_END,
        min(TRAIN_END + 2, VALIDATION_END),
        context,
        graph,
        statistics,
        metadata,
    )
    if next(model.parameters()).is_cuda:
        torch.cuda.synchronize()
    timing_started = time.perf_counter()
    timed = rollout(
        model,
        states,
        TRAIN_END,
        VALIDATION_END,
        context,
        graph,
        statistics,
        metadata,
    )
    if next(model.parameters()).is_cuda:
        torch.cuda.synchronize()
    inference_seconds = time.perf_counter() - timing_started
    predicted_cycles = len(timed) - 1
    peak_memory = (
        int(torch.cuda.max_memory_allocated(next(model.parameters()).device))
        if next(model.parameters()).is_cuda
        else 0
    )

    breakdown = parameter_breakdown(model)
    cost = {
        "training_wall_seconds": training_seconds,
        "inference_rollout_seconds": inference_seconds,
        "inference_seconds_per_cycle": inference_seconds / predicted_cycles,
        "peak_cuda_memory_bytes": peak_memory,
        "parameter_breakdown": breakdown,
    }
    (args.out / "cost_metrics.json").write_text(
        json.dumps(cost, indent=2) + "\n", encoding="utf-8"
    )

    trajectory_id, physics_family = validate_dataset_scope(data)
    manifest = {
        "claim_class": "tooling-only",
        "trajectory_generalization": False,
        "assimilation_eligible": False,
        "quarantine_reason": (
            "single physical trajectory and reused c77-c89 evaluation benchmark"
        ),
        "temporal_model": args.temporal_model,
        "spatial_encoder": args.spatial_encoder,
        "dataset": str(args.dataset.resolve()),
        "trajectory_id": trajectory_id,
        "physics_family": physics_family,
        "seed": args.seed,
        "parameter_target": args.parameter_target,
        "parameter_tolerance": args.parameter_tolerance,
        "parameter_breakdown": breakdown,
        "context_candidates": list(args.context_lengths),
        "selected_context_validation_only": context,
        "split": {
            "normalization": "c1-c67 only",
            "training_windows": "history and targets wholly within c1-c67",
            "validation": "c67-origin recurrent rollout through c76",
            "evaluation": "c76-origin c77-c89 reused benchmark; not virgin locked test",
            "twenty_cycle_diagnostic": (
                "c69-origin c70-c89 reused validation/evaluation interval"
            ),
            "observation_reset": "c87 raw/full oracle diagnostics, separately labelled",
        },
        "features": {
            "state": ["d", "alpha_bar", "f_fatigue", "log10_psi_raw"],
            "cycle_index": False,
            "cycle_to_failure": False,
            "loading_metadata": args.use_loading_metadata,
            "derived_active": "eta0 (1-d)^2 psi_raw",
        },
        "optimization": {
            "steps": args.steps,
            "rollout_steps": args.rollout_steps,
            "teacher_forcing_ratio": args.teacher_forcing_ratio,
            "lr": args.lr,
            "weight_decay": args.weight_decay,
        },
        "best_validation_selection_composite": checkpoint[
            "best_validation_selection_composite"
        ],
        "cost": cost,
        "primary_assets": [
            "best_model.pt",
            "training_history.csv",
            "fem_centred_metrics.csv",
            "reused_evaluation_predictions.npz",
            "cost_metrics.json",
        ],
    }
    (args.out / "RUN_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--temporal-model", choices=TEMPORAL_FAMILIES, required=True)
    parser.add_argument("--spatial-encoder", choices=("graph", "pointwise"), default="graph")
    parser.add_argument("--context-lengths", type=parse_int_list, default=DEFAULT_CONTEXTS)
    parser.add_argument("--local-dim", type=int, default=48)
    parser.add_argument("--token-dim", type=int, default=48)
    parser.add_argument("--temporal-width", type=int, required=True)
    parser.add_argument("--local-layers", type=int, default=2)
    parser.add_argument("--coarse-layers", type=int, default=1)
    parser.add_argument("--transformer-heads", type=int, default=4)
    parser.add_argument("--parameter-target", type=int, default=329000)
    parser.add_argument("--parameter-tolerance", type=float, default=0.05)
    parser.add_argument("--rollout-steps", type=int, default=3)
    parser.add_argument("--teacher-forcing-ratio", type=float, default=0.0)
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--eval-every", type=int, default=100)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--lr", type=float, default=3.0e-4)
    parser.add_argument("--weight-decay", type=float, default=1.0e-6)
    parser.add_argument("--active-weight", type=float, default=1.0)
    parser.add_argument("--support-weight", type=float, default=0.25)
    parser.add_argument("--gradient-weight", type=float, default=0.1)
    parser.add_argument("--morphology-weight", type=float, default=0.25)
    parser.add_argument("--active-roughness-weight", type=float, default=0.05)
    parser.add_argument("--grad-clip", type=float, default=5.0)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--use-loading-metadata", action="store_true")
    parser.add_argument(
        "--allow-single-trajectory-diagnostic",
        action="store_true",
        help="Required acknowledgement that all outputs remain quarantined.",
    )
    args = parser.parse_args()
    if not args.allow_single_trajectory_diagnostic:
        parser.error(
            "single-trajectory training is quarantined; explicitly pass "
            "--allow-single-trajectory-diagnostic on a producer"
        )
    if max(args.context_lengths) > 20:
        parser.error("sealed protocol limits context to at most 20 cycles")
    if args.rollout_steps < 1 or args.steps < 1 or args.eval_every < 1:
        parser.error("rollout-steps, steps, and eval-every must be positive")
    if not 0.0 <= args.teacher_forcing_ratio <= 1.0:
        parser.error("teacher-forcing-ratio must lie in [0, 1]")
    if args.parameter_target < 1 or not 0.0 <= args.parameter_tolerance <= 0.2:
        parser.error("invalid parameter matching gate")
    return args


if __name__ == "__main__":
    train(parse_args())
