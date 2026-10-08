#!/usr/bin/env python3
"""Current-state CrackMNIST tokenizer MVP.

This runner closes one deliberately narrow pipeline:

    DIC displacement -> 32-dimensional latent -> reconstruction / tip / SIF

It has no temporal target and must not be used for future prediction or RUL.
Mac usage is limited to ``audit`` plus import/unit/forward sanity.  ``train``
requires a clean Git checkout and CUDA on the authorised producer.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from crackmnist_mechanics_cv import audit_dataset, git_value, load_dataset, write_json


EPOCHS = 20
BATCH_SIZE = 256
LATENT_DIM = 32
SEED = 17
LEARNING_RATE = 1.0e-3
WEIGHT_DECAY = 1.0e-4
SIF_LOSS_WEIGHT = 0.5
TARGET_NAMES = ("KI", "KII", "T")
AUTHORIZED_PRODUCER_HOSTNAME = "GPUServer8"


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    import torch

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def build_model(latent_dim: int = LATENT_DIM):
    import torch.nn as nn

    class CurrentStateTokenizer(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.encoder = nn.Sequential(
                nn.Flatten(),
                nn.Linear(2 * 28 * 28, 256),
                nn.SiLU(),
                nn.Linear(256, latent_dim),
            )
            self.reconstruction_head = nn.Sequential(
                nn.Linear(latent_dim, 256),
                nn.SiLU(),
                nn.Linear(256, 2 * 28 * 28),
            )
            self.tip_head = nn.Linear(latent_dim, 28 * 28)
            self.sif_head = nn.Linear(latent_dim, 3)

        def forward(self, x):
            z = self.encoder(x)
            reconstruction = self.reconstruction_head(z).reshape(-1, 2, 28, 28)
            return z, reconstruction, self.tip_head(z), self.sif_head(z)

    return CurrentStateTokenizer()


def batch_losses(model, images, tip_target, tip_visible, sif_target):
    import torch.nn.functional as functional

    latent, reconstruction, tip_logits, sif_prediction = model(images)
    reconstruction_loss = functional.mse_loss(reconstruction, images)
    if bool(tip_visible.any()):
        tip_loss = functional.cross_entropy(tip_logits[tip_visible], tip_target[tip_visible])
    else:
        tip_loss = tip_logits.sum() * 0.0
    sif_loss = functional.mse_loss(sif_prediction, sif_target)
    total = reconstruction_loss + tip_loss + SIF_LOSS_WEIGHT * sif_loss
    return total, reconstruction_loss, tip_loss, sif_loss, latent


def split_indices(data) -> dict[str, np.ndarray]:
    return {split: np.flatnonzero(data.split_names == split) for split in ("train", "val", "test")}


def prepare_arrays(data, train_idx: np.ndarray) -> dict[str, np.ndarray]:
    channel_mean = data.images[train_idx].mean(axis=(0, 2, 3)).astype(np.float32)
    channel_std = data.images[train_idx].std(axis=(0, 2, 3)).astype(np.float32)
    channel_std[channel_std < 1.0e-12] = 1.0
    sif_mean = data.sifs[train_idx].mean(axis=0).astype(np.float32)
    sif_std = data.sifs[train_idx].std(axis=0).astype(np.float32)
    sif_std[sif_std < 1.0e-8] = 1.0
    masks = data.masks.reshape(len(data.masks), -1)
    return {
        "images_z": ((data.images - channel_mean[None, :, None, None]) / channel_std[None, :, None, None]).astype(np.float32),
        "tip_target": np.argmax(masks, axis=1).astype(np.int64),
        "tip_visible": masks.any(axis=1),
        "sifs_z": ((data.sifs - sif_mean[None]) / sif_std[None]).astype(np.float32),
        "channel_mean": channel_mean,
        "channel_std": channel_std,
        "sif_mean": sif_mean,
        "sif_std": sif_std,
    }


def make_loader(arrays: dict[str, np.ndarray], idx: np.ndarray, batch_size: int, shuffle: bool, seed: int):
    import torch
    from torch.utils.data import DataLoader, TensorDataset

    dataset = TensorDataset(
        torch.from_numpy(arrays["images_z"][idx]),
        torch.from_numpy(arrays["tip_target"][idx]),
        torch.from_numpy(arrays["tip_visible"][idx]),
        torch.from_numpy(arrays["sifs_z"][idx]),
        torch.from_numpy(idx.astype(np.int64)),
    )
    generator = torch.Generator().manual_seed(seed)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        generator=generator if shuffle else None,
        num_workers=0,
    )


def epoch_pass(model, loader, device: str, optimizer=None) -> dict[str, float]:
    import torch

    training = optimizer is not None
    model.train(training)
    totals = np.zeros(5, dtype=np.float64)
    context = torch.enable_grad() if training else torch.no_grad()
    with context:
        for images, tip_target, tip_visible, sif_target, _ in loader:
            images = images.to(device)
            tip_target = tip_target.to(device)
            tip_visible = tip_visible.to(device)
            sif_target = sif_target.to(device)
            losses = batch_losses(model, images, tip_target, tip_visible, sif_target)
            total, reconstruction, tip, sif = losses[:4]
            if training:
                optimizer.zero_grad(set_to_none=True)
                total.backward()
                optimizer.step()
            batch_n = len(images)
            totals += [
                float(total.detach()) * batch_n,
                float(reconstruction.detach()) * batch_n,
                float(tip.detach()) * batch_n,
                float(sif.detach()) * batch_n,
                batch_n,
            ]
    if not np.isfinite(totals).all() or totals[4] <= 0:
        raise RuntimeError("non-finite or empty epoch")
    return {
        "loss": totals[0] / totals[4],
        "reconstruction_mse_z": totals[1] / totals[4],
        "tip_ce": totals[2] / totals[4],
        "sif_mse_z": totals[3] / totals[4],
    }


def collect_predictions(model, loader, device: str) -> dict[str, np.ndarray]:
    import torch

    model.eval()
    parts: dict[str, list[np.ndarray]] = {
        key: [] for key in ("row_idx", "latent", "reconstruction_z", "tip_probability", "sif_z")
    }
    with torch.no_grad():
        for images, _, _, _, row_idx in loader:
            latent, reconstruction, tip_logits, sif_prediction = model(images.to(device))
            parts["row_idx"].append(row_idx.numpy())
            parts["latent"].append(latent.cpu().numpy())
            parts["reconstruction_z"].append(reconstruction.cpu().numpy())
            parts["tip_probability"].append(torch.softmax(tip_logits, dim=1).cpu().numpy())
            parts["sif_z"].append(sif_prediction.cpu().numpy())
    return {key: np.concatenate(value, axis=0) for key, value in parts.items()}


def lineage_average(values: np.ndarray, lineage_ids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    unique = np.unique(lineage_ids)
    averaged = np.asarray([values[lineage_ids == lineage].mean(axis=0) for lineage in unique])
    return unique, averaged


def select_representative_visible_row(
    lineage_ids: np.ndarray,
    reconstruction_error: np.ndarray,
    tip_visible: np.ndarray,
) -> int:
    """Select a median-error row without inventing a tip for an empty mask."""
    visible_rows = np.flatnonzero(tip_visible)
    if len(visible_rows) == 0:
        raise RuntimeError("no visible crack-tip row is available for the required figure")
    visible_lineages = np.unique(lineage_ids[visible_rows])
    lineage_error = np.asarray([
        reconstruction_error[(lineage_ids == value) & tip_visible].mean()
        for value in visible_lineages
    ])
    selected_lineage = visible_lineages[int(np.argmin(np.abs(lineage_error - np.median(lineage_error))))]
    candidates = np.flatnonzero((lineage_ids == selected_lineage) & tip_visible)
    row_error = reconstruction_error[candidates]
    return int(candidates[int(np.argmin(np.abs(row_error - np.median(row_error))))])


def producer_violations(
    *, audit_pass: bool, epochs: int, batch_size: int, latent_dim: int,
    seed: int, device: str, git_commit: str, git_dirty: str,
    reviewed_commit: str, hostname: str,
) -> list[str]:
    violations: list[str] = []
    if not audit_pass:
        violations.append("dataset identity/lineage gate failed")
    if epochs != EPOCHS:
        violations.append(f"epochs must equal {EPOCHS}")
    if batch_size != BATCH_SIZE:
        violations.append(f"batch size must equal {BATCH_SIZE}")
    if latent_dim != LATENT_DIM:
        violations.append(f"latent dimension must equal {LATENT_DIM}")
    if seed != SEED:
        violations.append(f"seed must equal {SEED}")
    if not device.startswith("cuda"):
        violations.append("formal training requires CUDA on the authorised producer")
    if git_commit == "unavailable":
        violations.append("git commit unavailable")
    if not reviewed_commit or git_commit != reviewed_commit:
        violations.append("HEAD must equal the independently reviewed commit")
    if hostname != AUTHORIZED_PRODUCER_HOSTNAME:
        violations.append(f"formal training requires authorised producer {AUTHORIZED_PRODUCER_HOSTNAME}")
    if git_dirty:
        violations.append("git checkout is dirty")
    return violations


def evaluate(data, arrays: dict[str, np.ndarray], predictions: dict[str, np.ndarray]) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    idx = predictions["row_idx"].astype(np.int64)
    reconstruction_z = predictions["reconstruction_z"]
    reconstruction = reconstruction_z * arrays["channel_std"][None, :, None, None] + arrays["channel_mean"][None, :, None, None]
    reconstruction_mse_z_row = np.mean((reconstruction_z - arrays["images_z"][idx]) ** 2, axis=(1, 2, 3))
    reconstruction_mae_row = np.mean(np.abs(reconstruction - data.images[idx]), axis=(1, 2, 3))

    tip_argmax = np.argmax(predictions["tip_probability"], axis=1)
    tip_y, tip_x = np.divmod(tip_argmax, 28)
    true_y, true_x = np.divmod(arrays["tip_target"][idx], 28)
    tip_error_row = np.hypot(tip_x - true_x, tip_y - true_y)
    visible = arrays["tip_visible"][idx]

    sif_prediction = predictions["sif_z"] * arrays["sif_std"][None] + arrays["sif_mean"][None]
    lineage_ids = data.lineage_ids[idx]
    unique_lineages, reconstruction_mse_z = lineage_average(reconstruction_mse_z_row[:, None], lineage_ids)
    _, reconstruction_mae = lineage_average(reconstruction_mae_row[:, None], lineage_ids)
    visible_lineages = np.unique(lineage_ids[visible])
    tip_error = np.asarray([tip_error_row[(lineage_ids == lineage) & visible].mean() for lineage in visible_lineages])
    _, sif_pred_lineage = lineage_average(sif_prediction, lineage_ids)
    _, sif_true_lineage = lineage_average(data.sifs[idx], lineage_ids)
    sif_mae = np.mean(np.abs(sif_pred_lineage - sif_true_lineage), axis=0)

    metrics = {
        "decision": "PASS_CURRENT_STATE_TOKENIZER_MVP",
        "claim_class": "tooling-only current-state representation",
        "performance_gate": "none in protocol v1",
        "n_test_rows": int(len(idx)),
        "n_test_lineages": int(len(unique_lineages)),
        "n_visible_tip_rows": int(visible.sum()),
        "n_visible_tip_lineages": int(len(visible_lineages)),
        "reconstruction_mse_standardized_lineage_mean": float(reconstruction_mse_z.mean()),
        "reconstruction_mae_original_units_lineage_mean": float(reconstruction_mae.mean()),
        "tip_error_px_lineage_mean": float(tip_error.mean()),
        "tip_error_px_lineage_median": float(np.median(tip_error)),
        "sif_mae": {name: float(value) for name, value in zip(TARGET_NAMES, sif_mae)},
        "blocked_claims": [
            "physical or dynamic sufficiency",
            "future crack prediction",
            "RUL or time-to-failure",
            "phase-field hidden-state recovery",
            "road-domain transfer",
            "improvement over S03-E001",
        ],
    }
    numeric = np.asarray([
        metrics["reconstruction_mse_standardized_lineage_mean"],
        metrics["reconstruction_mae_original_units_lineage_mean"],
        metrics["tip_error_px_lineage_mean"],
        metrics["tip_error_px_lineage_median"],
        *sif_mae,
    ])
    if not np.isfinite(numeric).all():
        raise RuntimeError("non-finite evaluation metric")
    output_arrays = {
        "row_idx": idx,
        "lineage_ids": lineage_ids,
        "latent": predictions["latent"],
        "reconstruction": reconstruction,
        "tip_probability": predictions["tip_probability"],
        "sif_prediction": sif_prediction,
        "sif_true": data.sifs[idx],
        "tip_error_row_px": tip_error_row,
        "tip_visible": visible,
        "reconstruction_mse_z_row": reconstruction_mse_z_row,
        "reconstruction_mae_row": reconstruction_mae_row,
    }
    return metrics, output_arrays


def render_figures(output: Path, data, history: list[dict[str, Any]], arrays: dict[str, np.ndarray]) -> None:
    import matplotlib.pyplot as plt

    figure_dir = output / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    epochs = np.asarray([row["epoch"] for row in history])
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6), constrained_layout=True)
    axes[0].plot(epochs, [row["train_loss"] for row in history], label="train", color="#0072B2")
    axes[0].plot(epochs, [row["val_loss"] for row in history], label="validation", color="#D55E00")
    axes[0].set_xlabel("epoch")
    axes[0].set_ylabel("total objective")
    axes[0].set_title("(a) Fixed MVP optimization")
    axes[0].grid(color="0.9", linewidth=0.7)
    axes[0].legend(frameon=False)
    for key, label, color in (
        ("val_reconstruction_mse_z", "reconstruction", "#009E73"),
        ("val_tip_ce", "tip", "#CC79A7"),
        ("val_sif_mse_z", "SIF", "#E69F00"),
    ):
        axes[1].plot(epochs, [row[key] for row in history], label=label, color=color)
    axes[1].set_xlabel("epoch")
    axes[1].set_ylabel("validation loss component")
    axes[1].set_title("(b) Diagnostic heads")
    axes[1].grid(color="0.9", linewidth=0.7)
    axes[1].legend(frameon=False)
    for suffix in ("png", "pdf"):
        fig.savefig(figure_dir / f"training_history.{suffix}", dpi=220 if suffix == "png" else None, bbox_inches="tight")
    plt.close(fig)

    lineage_ids = arrays["lineage_ids"]
    selected = select_representative_visible_row(
        lineage_ids,
        arrays["reconstruction_mse_z_row"],
        arrays["tip_visible"],
    )
    selected_lineage = lineage_ids[selected]
    source_row = int(arrays["row_idx"][selected])
    true_tip = np.argmax(data.masks[source_row].reshape(-1))
    true_y, true_x = np.divmod(true_tip, 28)
    pred_tip = int(np.argmax(arrays["tip_probability"][selected]))
    pred_y, pred_x = np.divmod(pred_tip, 28)

    fig, axes = plt.subplots(2, 3, figsize=(10.0, 6.3), constrained_layout=True)
    vmin = [min(float(data.images[source_row, c].min()), float(arrays["reconstruction"][selected, c].min())) for c in range(2)]
    vmax = [max(float(data.images[source_row, c].max()), float(arrays["reconstruction"][selected, c].max())) for c in range(2)]
    for channel, label in enumerate(("ux [mm]", "uy [mm]")):
        im = axes[channel, 0].imshow(data.images[source_row, channel], cmap="viridis", vmin=vmin[channel], vmax=vmax[channel])
        axes[channel, 0].set_title(f"released {label}")
        axes[channel, 1].imshow(arrays["reconstruction"][selected, channel], cmap="viridis", vmin=vmin[channel], vmax=vmax[channel])
        axes[channel, 1].set_title(f"reconstructed {label}")
        fig.colorbar(im, ax=[axes[channel, 0], axes[channel, 1]], fraction=0.035, pad=0.02)
    probability = arrays["tip_probability"][selected].reshape(28, 28)
    axes[0, 2].imshow(probability, cmap="magma")
    axes[0, 2].scatter([true_x], [true_y], marker="x", s=60, linewidths=2, color="#00FF66", label="released tip")
    axes[0, 2].scatter([pred_x], [pred_y], marker="+", s=70, linewidths=2, color="white", label="argmax")
    axes[0, 2].set_title("tip probability")
    axes[0, 2].legend(frameon=True, fontsize=7, loc="lower right")
    axes[1, 2].axis("off")
    axes[1, 2].text(
        0.02,
        0.95,
        "Mechanically selected test example\n"
        f"lineage: {int(selected_lineage)}\n"
        f"row: {source_row}\n"
        f"latent dimension: {LATENT_DIM}\n"
        "No chronology or future target",
        va="top",
        fontsize=10,
    )
    for axis in axes.flat:
        axis.set_xticks([])
        axis.set_yticks([])
    fig.suptitle("CrackMNIST current-state tokenizer MVP: representative test lineage")
    for suffix in ("png", "pdf"):
        fig.savefig(figure_dir / f"representative_reconstruction_and_tip.{suffix}", dpi=220 if suffix == "png" else None, bbox_inches="tight")
    plt.close(fig)


def write_history(path: Path, history: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(history[0]))
        writer.writeheader()
        writer.writerows(history)


def write_interpretation_assets(output: Path, metrics: dict[str, Any], best_epoch: int) -> None:
    sif = metrics["sif_mae"]
    decision = f"""# S03-E002-R001 decision

**Pipeline decision:** `PASS_CURRENT_STATE_TOKENIZER_MVP`  
**Claim class:** tooling-only current-state representation  
**Performance gate:** none in protocol v1

All locked data, split, lineage, finiteness and artifact-completeness gates
passed. The fixed 32-dimensional encoder produced finite reconstruction, tip
and SIF outputs; the best checkpoint was selected at epoch {best_epoch} using
the released validation experiment only.

Diagnostics on the untouched released test experiment:

- standardized reconstruction MSE: `{metrics['reconstruction_mse_standardized_lineage_mean']:.6g}`;
- original-unit reconstruction MAE: `{metrics['reconstruction_mae_original_units_lineage_mean']:.6g}`;
- lineage-mean tip error: `{metrics['tip_error_px_lineage_mean']:.6g} px`;
- SIF MAE: `KI={sif['KI']:.6g}`, `KII={sif['KII']:.6g}`, `T={sif['T']:.6g}`.

These values are diagnostic and do not pass or fail a scientific-performance
criterion. This result does not change S03-E001's frozen NO-GO and does not
support chronology, future prediction, RUL, physical/dynamic sufficiency,
phase-field state recovery or road transfer.
"""
    (output / "decision.md").write_text(decision)

    readme = """# Analysis: S03-E002

## Scientific question

Can one fixed current-state tokenizer mechanically produce finite DIC
reconstruction, released-tip and provided-SIF outputs under strict split and
lineage validity?

## Evidence identity

- Experiment: S03-E002, protocol v1.
- Run: S03-E002-R001.
- Data: locked CrackMNIST-28/S and adjacent metadata.
- Analysis: generated by `scripts/crackmnist_tokenizer_mvp.py`.
- Missing fields: cycle, timestamp, stage and source-frame identity.

## Reading order

1. Inspect `training_history` for finite fixed optimization.
2. Inspect `representative_reconstruction_and_tip` for the mechanically chosen
   median reconstruction-error test lineage.
3. Read `metrics.json` and `decision.md` for exact diagnostics and boundaries.

## Figure guide

### F01 — Training history

- Supports: all three output paths ran with finite losses.
- Does not support: convergence optimality, comparison superiority or scientific
  performance.

### F02 — Representative reconstruction and tip

- Supports: the saved checkpoint emits the declared outputs on an untouched
  experiment-side using shared field colour limits.
- Does not support: chronology, future prediction, physical sufficiency or
  generalisation beyond the released S subset.

## Cross-figure interpretation

The figures jointly verify pipeline mechanics only. Weak or strong diagnostic
metrics do not change the v1 pass decision because performance thresholds were
prospectively declared non-blocking.

## Gate result

- Validity gates: PASS.
- Primary gate: `PASS_CURRENT_STATE_TOKENIZER_MVP`.
- Scientific verdict: not promoted; tooling-only.

## Allowed conclusion

The fixed current-state DIC tokenizer pipeline executed reproducibly and
produced all required outputs.

## Blocked conclusion

Do not claim learned fracture mechanics, dynamic sufficiency, future crack
forecasting, RUL, phase-field hidden-state recovery, S03-E001 rescue or road
transfer.

## Storyline impact and next action

No S03 claim is reopened. The next scientific step requires either a separately
reviewed representation comparison or lineage-certified temporal data.
"""
    (output / "README_analysis.md").write_text(readme)


def run_training(data, output: Path, device: str) -> dict[str, Any]:
    import torch

    set_seed(SEED)
    splits = split_indices(data)
    arrays = prepare_arrays(data, splits["train"])
    train_loader = make_loader(arrays, splits["train"], BATCH_SIZE, True, SEED)
    val_loader = make_loader(arrays, splits["val"], BATCH_SIZE, False, SEED)
    test_loader = make_loader(arrays, splits["test"], BATCH_SIZE, False, SEED)
    model = build_model().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    history: list[dict[str, Any]] = []
    best_loss = math.inf
    best_epoch = -1
    best_state = None
    for epoch in range(1, EPOCHS + 1):
        train_metrics = epoch_pass(model, train_loader, device, optimizer)
        val_metrics = epoch_pass(model, val_loader, device)
        row = {
            "epoch": epoch,
            "train_loss": train_metrics["loss"],
            "train_reconstruction_mse_z": train_metrics["reconstruction_mse_z"],
            "train_tip_ce": train_metrics["tip_ce"],
            "train_sif_mse_z": train_metrics["sif_mse_z"],
            "val_loss": val_metrics["loss"],
            "val_reconstruction_mse_z": val_metrics["reconstruction_mse_z"],
            "val_tip_ce": val_metrics["tip_ce"],
            "val_sif_mse_z": val_metrics["sif_mse_z"],
        }
        if not np.isfinite(np.asarray(list(row.values()), dtype=np.float64)).all():
            raise RuntimeError(f"non-finite history at epoch {epoch}")
        history.append(row)
        if val_metrics["loss"] < best_loss:
            best_loss = val_metrics["loss"]
            best_epoch = epoch
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    if best_state is None:
        raise RuntimeError("no finite best checkpoint")
    model.load_state_dict(best_state)
    checkpoint = {
        "state_dict": best_state,
        "latent_dim": LATENT_DIM,
        "seed": SEED,
        "best_epoch": best_epoch,
        "channel_mean": arrays["channel_mean"],
        "channel_std": arrays["channel_std"],
        "sif_mean": arrays["sif_mean"],
        "sif_std": arrays["sif_std"],
        "protocol_revision": "v1",
    }
    torch.save(checkpoint, output / "checkpoint.pt")
    write_history(output / "history.csv", history)
    predictions = collect_predictions(model, test_loader, device)
    metrics, saved_arrays = evaluate(data, arrays, predictions)
    metrics.update({
        "best_epoch": best_epoch,
        "latent_dim": LATENT_DIM,
        "seed": SEED,
        "epochs": EPOCHS,
        "batch_size": BATCH_SIZE,
        "parameters": int(sum(parameter.numel() for parameter in model.parameters())),
    })
    write_json(output / "metrics.json", metrics)
    nonfinite = [name for name, value in saved_arrays.items() if not np.isfinite(value).all()]
    if nonfinite:
        raise RuntimeError(f"non-finite saved prediction arrays: {nonfinite}")
    np.savez_compressed(output / "test_predictions.npz", **saved_arrays)
    render_figures(output, data, history, saved_arrays)
    write_interpretation_assets(output, metrics, best_epoch)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("audit", "train"), default="audit")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--latent-dim", type=int, default=LATENT_DIM)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--reviewed-commit", default="")
    args = parser.parse_args()

    expected_metadata = args.data.parent / "experiments_metadata.json"
    if args.metadata.resolve() != expected_metadata.resolve():
        raise SystemExit(f"metadata must be adjacent locked file: {expected_metadata}")
    args.output.mkdir(parents=True, exist_ok=True)
    data = load_dataset(args.data, args.metadata)
    audit = audit_dataset(data, args.data)
    audit["chronology_exposed"] = False
    audit["allowed_task"] = "current-state representation only"
    write_json(args.output / "data_audit.json", audit)

    receipt = {
        "experiment_id": "S03-E002",
        "run_id": "S03-E002-R001",
        "protocol_revision": "v1",
        "mode": args.mode,
        "command": " ".join(sys.argv),
        "started_unix": time.time(),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python": sys.version,
        "git_commit": git_value(["git", "rev-parse", "HEAD"]),
        "git_branch": git_value(["git", "branch", "--show-current"]),
        "git_dirty": git_value(["git", "status", "--porcelain"]),
        "reviewed_commit": args.reviewed_commit,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", "unset"),
        "data_md5": audit["source_md5"],
        "metadata_md5": audit["metadata_md5"],
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "latent_dim": args.latent_dim,
        "seed": args.seed,
        "claim_class": "tooling-only current-state representation",
    }

    if args.mode == "audit":
        receipt["execution_status"] = "audit_pass" if audit["gate_pass"] else "audit_fail"
        write_json(args.output / "run_receipt.json", receipt)
        if not audit["gate_pass"]:
            raise SystemExit(2)
        return

    violations = producer_violations(
        audit_pass=audit["gate_pass"],
        epochs=args.epochs,
        batch_size=args.batch_size,
        latent_dim=args.latent_dim,
        seed=args.seed,
        device=args.device,
        git_commit=receipt["git_commit"],
        git_dirty=receipt["git_dirty"],
        reviewed_commit=args.reviewed_commit,
        hostname=receipt["hostname"],
    )
    if violations:
        receipt["execution_status"] = "blocked_by_protocol"
        receipt["blocking_findings"] = violations
        write_json(args.output / "run_receipt.json", receipt)
        raise SystemExit("; ".join(violations))

    try:
        import torch

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA requested but unavailable; formal training is producer-only")
        receipt["torch"] = torch.__version__
        receipt["gpu"] = torch.cuda.get_device_name(0)
        metrics = run_training(data, args.output, args.device)
        required = [
            "data_audit.json", "run_receipt.json", "checkpoint.pt", "history.csv",
            "metrics.json", "test_predictions.npz", "decision.md", "README_analysis.md",
            "figures/training_history.png", "figures/training_history.pdf",
            "figures/representative_reconstruction_and_tip.png",
            "figures/representative_reconstruction_and_tip.pdf",
        ]
        missing = [name for name in required if name != "run_receipt.json" and not (args.output / name).exists()]
        if missing:
            raise RuntimeError(f"missing required artifacts: {missing}")
        receipt["execution_status"] = "succeeded"
        receipt["pipeline_decision"] = metrics["decision"]
        receipt["completed_unix"] = time.time()
    except Exception as exc:
        receipt["execution_status"] = "failed"
        receipt["failure_type"] = type(exc).__name__
        receipt["failure_message"] = str(exc)
        write_json(args.output / "run_receipt.json", receipt)
        raise
    write_json(args.output / "run_receipt.json", receipt)


if __name__ == "__main__":
    main()
