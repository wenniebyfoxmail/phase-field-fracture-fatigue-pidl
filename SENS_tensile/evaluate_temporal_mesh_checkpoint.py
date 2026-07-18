#!/usr/bin/env python3
"""Re-evaluate a completed temporal checkpoint without changing its weights."""
from __future__ import annotations

import argparse
import json
from argparse import Namespace
from pathlib import Path

import torch

from train_temporal_mesh_operator import (
    build_model,
    choose_device,
    evaluate,
    load_dataset,
)
from fem_mechanism_operator import StateStatistics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--device", default="auto")
    parser.add_argument(
        "--peak-memory-floor",
        type=int,
        default=0,
        help="Preserve a known training-process CUDA peak during reevaluation.",
    )
    return parser.parse_args()


def main() -> None:
    cli = parse_args()
    device = choose_device(cli.device)
    checkpoint_path = cli.run_dir / "best_model.pt"
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    saved_args = dict(checkpoint["args"])
    saved_args["dataset"] = cli.dataset
    saved_args["out"] = cli.run_dir
    saved_args["device"] = str(device)
    args = Namespace(**saved_args)
    data, states, graph, metadata = load_dataset(
        cli.dataset,
        device,
        use_loading_metadata=bool(args.use_loading_metadata),
    )
    stored = checkpoint["statistics"]
    statistics = StateStatistics(
        stored["state_mean"].to(device),
        stored["state_std"].to(device),
        stored["residual_mean"].to(device),
        stored["residual_std"].to(device),
    )
    metadata_dim = 0 if metadata is None else int(metadata.shape[1])
    model = build_model(args, metadata_dim).to(device)
    model.load_state_dict(checkpoint["model"])
    cost_path = cli.run_dir / "cost_metrics.json"
    previous_cost = json.loads(cost_path.read_text(encoding="utf-8"))
    evaluate(
        model,
        states,
        graph,
        statistics,
        metadata,
        data,
        args,
        checkpoint,
        training_seconds=float(previous_cost["training_wall_seconds"]),
        peak_memory_floor=max(
            int(previous_cost["peak_cuda_memory_bytes"]), cli.peak_memory_floor
        ),
    )


if __name__ == "__main__":
    main()
