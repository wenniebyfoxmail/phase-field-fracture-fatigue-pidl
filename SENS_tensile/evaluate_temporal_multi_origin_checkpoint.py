#!/usr/bin/env python3
"""Checkpoint-only, task-separated temporal mesh evaluation.

This evaluator never changes weights, context selection, or architecture.  It
separates observed-history short-horizon propagation from autonomous transition
stress and from post-c87 observation/assimilation continuation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from argparse import Namespace
from pathlib import Path
from typing import Mapping

import numpy as np
import torch

from evaluate_temporal_mesh_checkpoint import StateStatistics
from train_temporal_mesh_operator import (
    EVALUATION_END,
    VALIDATION_END,
    build_model,
    choose_device,
    history_slice,
    load_dataset,
    metrics_for_rollout,
    predict_next,
    rollout,
    write_csv,
)


SAME_REGIME_ORIGINS: dict[int, int] = {76: 3, 79: 3, 82: 3, 84: 2}
EXPECTED_SPARSE_KEYS = {"analysis_c87", "observed_mask", "predicted_c89"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--checkpoint-run-dir", type=Path, required=True)
    parser.add_argument("--sparse-c87", type=Path, required=True)
    parser.add_argument("--sparse-c87-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", default="auto")
    return parser.parse_args()


def load_sparse_c87(
    path: Path,
    expected_sha256: str,
    expected_shape: torch.Size,
    device: torch.device,
) -> tuple[torch.Tensor, np.ndarray]:
    actual_sha256 = sha256(path)
    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"sparse c87 hash mismatch: expected {expected_sha256}, got {actual_sha256}"
        )
    payload = np.load(path, allow_pickle=False)
    missing = sorted(EXPECTED_SPARSE_KEYS - set(payload.files))
    if missing:
        raise ValueError(f"sparse c87 asset lacks keys: {missing}")
    analysis = np.asarray(payload["analysis_c87"], dtype=np.float32)
    observed_mask = np.asarray(payload["observed_mask"], dtype=bool)
    if analysis.shape != tuple(expected_shape):
        raise ValueError(
            f"sparse c87 state shape {analysis.shape} != dataset state {tuple(expected_shape)}"
        )
    if observed_mask.shape != (analysis.shape[0],):
        raise ValueError("sparse c87 observed mask has incompatible shape")
    if not np.isfinite(analysis).all():
        raise ValueError("sparse c87 state contains non-finite values")
    if analysis[:, 0].min() < -1.0e-6 or analysis[:, 0].max() > 1.0 + 1.0e-6:
        raise ValueError("sparse c87 damage lies outside [0,1]")
    if analysis[:, 1].min() < -1.0e-6:
        raise ValueError("sparse c87 irreversible history is negative")
    if analysis[:, 2].min() < -1.0e-6 or analysis[:, 2].max() > 1.0 + 1.0e-6:
        raise ValueError("sparse c87 degradation lies outside [0,1]")
    return torch.from_numpy(analysis).to(device), observed_mask


def continue_from_history(
    model,
    history: list[torch.Tensor],
    origin_cycle: int,
    end_cycle: int,
    context_length: int,
    graph: Mapping[str, torch.Tensor],
    statistics: StateStatistics,
) -> dict[int, torch.Tensor]:
    """Continue recurrently from an explicitly declared history."""
    if not history:
        raise ValueError("history must not be empty")
    predictions = {origin_cycle: history[-1]}
    model.eval()
    with torch.no_grad():
        for target_cycle in range(origin_cycle + 1, end_cycle + 1):
            current_history = torch.stack(history[-context_length:], dim=0)
            prediction = predict_next(
                model,
                current_history,
                graph,
                statistics,
                metadata_history=None,
            )
            predictions[target_cycle] = prediction
            history.append(prediction)
    return predictions


def free_history_through_c86(
    model,
    states: torch.Tensor,
    context_length: int,
    graph: Mapping[str, torch.Tensor],
    statistics: StateStatistics,
) -> tuple[list[torch.Tensor], dict[int, torch.Tensor]]:
    history = [state for state in history_slice(states, VALIDATION_END, context_length)]
    free = continue_from_history(
        model,
        history,
        VALIDATION_END,
        86,
        context_length,
        graph,
        statistics,
    )
    return history, free


def post_reset_rows(
    predictions: Mapping[int, torch.Tensor],
    states: torch.Tensor,
    data,
    graph: Mapping[str, torch.Tensor],
    comparison: str,
    context_length: int,
) -> list[dict]:
    post = {cycle: predictions[cycle] for cycle in (87, 88, 89)}
    return metrics_for_rollout(
        post,
        states,
        data,
        graph,
        comparison=comparison,
        origin_cycle=87,
        context_length=context_length,
    )


def main() -> None:
    cli = parse_args()
    device = choose_device(cli.device)
    checkpoint_path = cli.checkpoint_run_dir / "best_model.pt"
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    saved_args = dict(checkpoint["args"])
    saved_args["dataset"] = cli.dataset
    saved_args["out"] = cli.out
    saved_args["device"] = str(device)
    args = Namespace(**saved_args)
    data, states, graph, metadata = load_dataset(
        cli.dataset,
        device,
        use_loading_metadata=bool(args.use_loading_metadata),
    )
    if metadata is not None:
        raise ValueError("sealed multi-origin protocol forbids loading metadata")
    stored = checkpoint["statistics"]
    statistics = StateStatistics(
        stored["state_mean"].to(device),
        stored["state_std"].to(device),
        stored["residual_mean"].to(device),
        stored["residual_std"].to(device),
    )
    model = build_model(args, metadata_dim=0).to(device)
    model.load_state_dict(checkpoint["model"])
    context = int(checkpoint["selected_context"])
    sparse_c87, observed_mask = load_sparse_c87(
        cli.sparse_c87,
        cli.sparse_c87_sha256,
        states[0].shape,
        device,
    )

    rows: list[dict] = []
    representative: dict[str, np.ndarray] = {}
    for origin_cycle, max_horizon in SAME_REGIME_ORIGINS.items():
        predictions = rollout(
            model,
            states,
            origin_cycle,
            origin_cycle + max_horizon,
            context,
            graph,
            statistics,
            metadata=None,
        )
        task_rows = metrics_for_rollout(
            predictions,
            states,
            data,
            graph,
            comparison="observed_fem_history_same_regime",
            origin_cycle=origin_cycle,
            context_length=context,
        )
        for row in task_rows:
            row["conditioning"] = "identical_true_FEM_history_to_origin"
        rows.extend(task_rows)
        if origin_cycle == 76:
            representative["c78_from_c76_h2"] = predictions[78].detach().cpu().numpy()
        if origin_cycle == 79:
            representative["c80_from_c79_h1"] = predictions[80].detach().cpu().numpy()

    autonomous = rollout(
        model,
        states,
        VALIDATION_END,
        EVALUATION_END,
        context,
        graph,
        statistics,
        metadata=None,
    )
    autonomous_rows = metrics_for_rollout(
        autonomous,
        states,
        data,
        graph,
        comparison="autonomous_transition_stress_c76_c89",
        origin_cycle=VALIDATION_END,
        context_length=context,
    )
    for row in autonomous_rows:
        row["conditioning"] = "true_FEM_history_to_c76_then_model_free_rollout"
    rows.extend(autonomous_rows)

    reset_predictions: dict[str, dict[int, torch.Tensor]] = {}
    for mode in ("raw", "full"):
        predictions = rollout(
            model,
            states,
            VALIDATION_END,
            EVALUATION_END,
            context,
            graph,
            statistics,
            metadata=None,
            reset_cycle=87,
            reset_mode=mode,
        )
        reset_predictions[mode] = predictions
        comparison = f"free_history_c87_{mode}_reset"
        task_rows = post_reset_rows(
            predictions,
            states,
            data,
            graph,
            comparison,
            context,
        )
        for row in task_rows:
            row["conditioning"] = (
                f"model_native_c76_c86_history_plus_FEM_c87_{mode}_state_channel"
            )
        rows.extend(task_rows)

    oracle_history = [state for state in history_slice(states, 86, context)]
    oracle_history.append(sparse_c87)
    sparse_oracle = continue_from_history(
        model,
        oracle_history,
        87,
        89,
        context,
        graph,
        statistics,
    )
    oracle_rows = metrics_for_rollout(
        sparse_oracle,
        states,
        data,
        graph,
        comparison="oracle_history_shared_sparse_c87_assimilation",
        origin_cycle=87,
        context_length=context,
    )
    for row in oracle_rows:
        row["conditioning"] = "identical_true_FEM_history_to_c86_plus_shared_sparse_c87"
    rows.extend(oracle_rows)

    free_history, free_to_c86 = free_history_through_c86(
        model,
        states,
        context,
        graph,
        statistics,
    )
    free_history.append(sparse_c87)
    sparse_free = continue_from_history(
        model,
        free_history,
        87,
        89,
        context,
        graph,
        statistics,
    )
    free_rows = metrics_for_rollout(
        sparse_free,
        states,
        data,
        graph,
        comparison="free_history_shared_sparse_c87_assimilation",
        origin_cycle=87,
        context_length=context,
    )
    for row in free_rows:
        row["conditioning"] = "model_native_c76_c86_history_plus_shared_sparse_c87"
    rows.extend(free_rows)

    cli.out.mkdir(parents=True, exist_ok=True)
    # Keep the conditioning label near the task identifiers in the CSV.
    ordered_rows = []
    for row in rows:
        ordered_rows.append(
            {
                "comparison": row.pop("comparison"),
                "conditioning": row.pop("conditioning"),
                **row,
            }
        )
    write_csv(cli.out / "multi_origin_metrics.csv", ordered_rows)
    np.savez_compressed(
        cli.out / "multi_origin_predictions.npz",
        **representative,
        free_c86=free_to_c86[86].detach().cpu().numpy(),
        free_c87=autonomous[87].detach().cpu().numpy(),
        free_c89=autonomous[89].detach().cpu().numpy(),
        raw_reset_c89=reset_predictions["raw"][89].detach().cpu().numpy(),
        full_reset_c89=reset_predictions["full"][89].detach().cpu().numpy(),
        sparse_oracle_history_c89=sparse_oracle[89].detach().cpu().numpy(),
        sparse_free_history_c89=sparse_free[89].detach().cpu().numpy(),
        sparse_c87=sparse_c87.detach().cpu().numpy(),
        sparse_observed_mask=observed_mask,
    )
    source_manifest = json.loads(
        (cli.checkpoint_run_dir / "RUN_MANIFEST.json").read_text(encoding="utf-8")
    )
    manifest = {
        "protocol_id": "temporal_multi_origin_reanalysis_v1_20260720",
        "checkpoint_run_dir": str(cli.checkpoint_run_dir),
        "temporal_model": source_manifest["temporal_model"],
        "seed": int(source_manifest["seed"]),
        "selected_context": context,
        "dataset_sha256": sha256(cli.dataset),
        "checkpoint_sha256": sha256(checkpoint_path),
        "sparse_c87_sha256": sha256(cli.sparse_c87),
        "sparse_c87_observed_fraction": float(observed_mask.mean()),
        "weights_changed": False,
        "selection_changed": False,
        "historical_multiscale_ranking_eligible": False,
        "tasks": [
            "observed_fem_history_same_regime",
            "autonomous_transition_stress_c76_c89",
            "free_history_c87_raw_reset",
            "free_history_c87_full_reset",
            "oracle_history_shared_sparse_c87_assimilation",
            "free_history_shared_sparse_c87_assimilation",
        ],
        "primary_assets": [
            "multi_origin_metrics.csv",
            "multi_origin_predictions.npz",
        ],
    }
    (cli.out / "MULTI_ORIGIN_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
