#!/usr/bin/env python3
"""Prepare a checkpoint-cloned archive for branch-restart diagnostics.

The branch-restart test asks whether a different optimization path can escape a
thin-band solution under the same physical history.  This helper copies a
single cycle checkpoint into a fresh archive while preserving
hist_alpha/hist_fat/psi_plus_prev/S2 state exactly.  Optional variants edit only
the saved NN weights before the normal runner resumes from that checkpoint.
"""
from __future__ import annotations

import argparse
import csv
import math
import shutil
from pathlib import Path

import numpy as np
import torch


def _copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _copy_truncated_csv(src: Path, dst: Path, cycle: int) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open("r", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        has_header = csv.Sniffer().has_header(sample) if sample.strip() else False
        if not has_header:
            shutil.copy2(src, dst)
            return
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        cycle_key = "cycle" if "cycle" in fields else fields[0] if fields else None
        rows = []
        for row in reader:
            if cycle_key is None:
                rows.append(row)
                continue
            try:
                row_cycle = int(float(row[cycle_key]))
            except (TypeError, ValueError):
                rows.append(row)
                continue
            if row_cycle <= cycle:
                rows.append(row)
    with dst.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _xavier_like_(tensor: torch.Tensor, init_coeff: float) -> None:
    if tensor.ndim < 2:
        tensor.zero_()
        return
    gain = torch.nn.init.calculate_gain(
        "leaky_relu", math.sqrt(max(init_coeff * init_coeff - 1.0, 0.0))
    )
    torch.nn.init.xavier_uniform_(tensor, gain=gain)


def _reinit_tip_state(state: dict[str, torch.Tensor], init_coeff: float) -> list[str]:
    changed = []
    with torch.no_grad():
        for key, value in state.items():
            if not key.startswith("tip_net."):
                continue
            if not torch.is_tensor(value):
                continue
            if key.endswith(".weight"):
                _xavier_like_(value, init_coeff)
                changed.append(key)
            elif key.endswith(".bias"):
                value.zero_()
                changed.append(key)
            elif key.endswith(".coeff"):
                value.fill_(init_coeff)
                changed.append(key)
    return changed


def _reinit_tip_alpha_row(state: dict[str, torch.Tensor], init_coeff: float,
                          alpha_channel: int) -> list[str]:
    output_weight_keys = [
        key for key, value in state.items()
        if key.startswith("tip_net.")
        and key.endswith("output_layer.weight")
        and torch.is_tensor(value)
        and value.ndim == 2
        and value.shape[0] > alpha_channel
    ]
    output_bias_keys = [
        key for key, value in state.items()
        if key.startswith("tip_net.")
        and key.endswith("output_layer.bias")
        and torch.is_tensor(value)
        and value.ndim == 1
        and value.shape[0] > alpha_channel
    ]
    if not output_weight_keys:
        raise RuntimeError("Could not find tip-local output_layer.weight for alpha-row reset")

    changed = []
    with torch.no_grad():
        for key in output_weight_keys:
            candidate = torch.empty_like(state[key])
            _xavier_like_(candidate, init_coeff)
            state[key][alpha_channel].copy_(candidate[alpha_channel])
            changed.append(f"{key}[{alpha_channel}]")
        for key in output_bias_keys:
            state[key][alpha_channel].zero_()
            changed.append(f"{key}[{alpha_channel}]")
    return changed


def _copy_history_files(src_best: Path, dst_best: Path, cycle: int) -> None:
    for path in src_best.iterdir():
        if path.name.startswith(("checkpoint_step_", "trained_1NN_", "trainLoss_1NN_")):
            continue
        if path.suffix == ".npy":
            _copy_if_exists(path, dst_best / path.name)
        elif path.suffix == ".csv":
            _copy_truncated_csv(path, dst_best / path.name, cycle)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-archive", type=Path, required=True)
    p.add_argument("--target-archive", type=Path, required=True)
    p.add_argument("--cycle", type=int, required=True)
    p.add_argument("--variant", choices=("normal", "reinit_tip", "reinit_tip_alpha"),
                   default="normal")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--init-coeff", type=float, default=1.0)
    p.add_argument("--alpha-channel", type=int, default=2)
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args()

    source = args.source_archive.expanduser().resolve()
    target = args.target_archive.expanduser().resolve()
    src_best = source / "best_models"
    dst_best = target / "best_models"
    if not src_best.exists():
        raise FileNotFoundError(src_best)
    if target.exists() and any(target.iterdir()) and not args.overwrite:
        raise FileExistsError(f"{target} already exists; pass --overwrite")

    target.mkdir(parents=True, exist_ok=True)
    dst_best.mkdir(parents=True, exist_ok=True)
    (target / "intermediate_models").mkdir(parents=True, exist_ok=True)
    (target / "alpha_snapshots").mkdir(parents=True, exist_ok=True)

    _copy_if_exists(source / "model_settings.txt", target / "model_settings.source.txt")
    _copy_history_files(src_best, dst_best, args.cycle)

    ckpt_name = f"checkpoint_step_{args.cycle}.pt"
    net_name = f"trained_1NN_{args.cycle}.pt"
    loss_name = f"trainLoss_1NN_{args.cycle}.npy"
    _copy_if_exists(src_best / "trained_1NN_initTraining.pt", dst_best / "trained_1NN_initTraining.pt")
    _copy_if_exists(src_best / "trainLoss_1NN_initTraining.npy", dst_best / "trainLoss_1NN_initTraining.npy")
    _copy_if_exists(src_best / ckpt_name, dst_best / ckpt_name)
    _copy_if_exists(src_best / loss_name, dst_best / loss_name)

    if not (src_best / ckpt_name).exists():
        raise FileNotFoundError(src_best / ckpt_name)
    if not (src_best / net_name).exists():
        raise FileNotFoundError(src_best / net_name)

    torch.manual_seed(int(args.seed))
    state = torch.load(src_best / net_name, map_location="cpu")
    changed: list[str] = []
    if args.variant == "reinit_tip":
        changed = _reinit_tip_state(state, args.init_coeff)
    elif args.variant == "reinit_tip_alpha":
        changed = _reinit_tip_alpha_row(state, args.init_coeff, args.alpha_channel)
    torch.save(state, dst_best / net_name)

    manifest = target / "BRANCH_RESTART_MANIFEST.txt"
    manifest.write_text(
        "\n".join([
            "branch_restart_archive",
            f"source_archive={source}",
            f"target_archive={target}",
            f"cycle={args.cycle}",
            f"variant={args.variant}",
            f"seed={args.seed}",
            f"init_coeff={args.init_coeff}",
            f"changed_keys={len(changed)}",
            *changed,
            "",
        ]),
        encoding="utf-8",
    )
    print(f"Prepared {target}")
    print(f"  cycle={args.cycle} variant={args.variant} changed={len(changed)}")


if __name__ == "__main__":
    main()
