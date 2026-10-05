#!/usr/bin/env python3
"""Leakage-safe CrackMNIST mechanics-aware CV feasibility pilot.

The runner has two explicit modes:

* ``audit`` performs no fitting and verifies dataset identity, physical groups,
  augmentation lineage, and label conventions.
* ``train`` executes the frozen four-fold physical-experiment holdout protocol.

Rows are never treated as independent samples.  The exact tuple
``(experiment-side, force, KI, KII, T)`` identifies one physical DIC field and
its eight released augmentations; all uncertainty summaries and bootstrap
tests are therefore lineage blocked.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import random
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import h5py
import numpy as np


EXPECTED_MD5 = "26bb0aa814f2e3ed467879844222c46c"
SEEDS = (17, 29, 41)
EXPECTED_AUGMENTATIONS = 8
TIP_FAILURE_PX = 3.0


def file_hash(path: Path, algorithm: str = "md5") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_value(args: list[str]) -> str:
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unavailable"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


@dataclass
class Dataset:
    images: np.ndarray
    masks: np.ndarray
    sifs: np.ndarray
    forces: np.ndarray
    augs: np.ndarray
    exp_ids: np.ndarray
    exp_names: np.ndarray
    split_names: np.ndarray
    lineage_ids: np.ndarray
    lineage_keys: list[tuple[Any, ...]]
    metadata: dict[str, dict[str, Any]]


def _decode(values: Iterable[Any]) -> np.ndarray:
    return np.asarray([x.decode() if isinstance(x, bytes) else str(x) for x in values])


def load_dataset(path: Path, metadata_path: Path) -> Dataset:
    pieces: dict[str, list[np.ndarray]] = {
        key: [] for key in ("images", "masks", "sifs", "forces", "augs", "exp_ids", "split_names")
    }
    with h5py.File(path, "r") as handle:
        exp_names = _decode(handle["experiments"][:])
        for split in ("train", "val", "test"):
            n = len(handle[f"{split}_images"])
            pieces["images"].append(handle[f"{split}_images"][:])
            pieces["masks"].append(handle[f"{split}_masks"][:])
            pieces["sifs"].append(handle[f"{split}_SIFs"][:])
            pieces["forces"].append(handle[f"{split}_forces"][:, 0])
            pieces["augs"].append(handle[f"{split}_augs"][:])
            pieces["exp_ids"].append(handle[f"{split}_exp_ids"][:])
            pieces["split_names"].append(np.repeat(split, n))
    arrays = {key: np.concatenate(value, axis=0) for key, value in pieces.items()}

    # Float32 bit patterns are intentionally retained.  The released file uses
    # identical force/SIF labels for all eight views of a physical field.
    key_to_id: dict[tuple[Any, ...], int] = {}
    lineage_keys: list[tuple[Any, ...]] = []
    lineage_ids = np.empty(len(arrays["images"]), dtype=np.int64)
    for i in range(len(lineage_ids)):
        key = (
            int(arrays["exp_ids"][i]),
            np.float32(arrays["forces"][i]).tobytes().hex(),
            *(np.float32(x).tobytes().hex() for x in arrays["sifs"][i]),
        )
        if key not in key_to_id:
            key_to_id[key] = len(lineage_keys)
            lineage_keys.append(key)
        lineage_ids[i] = key_to_id[key]

    return Dataset(
        images=arrays["images"], masks=arrays["masks"], sifs=arrays["sifs"],
        forces=arrays["forces"], augs=arrays["augs"], exp_ids=arrays["exp_ids"],
        exp_names=exp_names, split_names=arrays["split_names"],
        lineage_ids=lineage_ids, lineage_keys=lineage_keys,
        metadata=json.loads(metadata_path.read_text()),
    )


def audit_dataset(data: Dataset, source: Path) -> dict[str, Any]:
    counts = np.bincount(data.lineage_ids)
    unique_experiments = sorted(np.unique(data.exp_ids).tolist())
    experiment_rows = []
    for exp_id in unique_experiments:
        idx = data.exp_ids == exp_id
        name = str(data.exp_names[exp_id])
        meta = data.metadata[name]
        experiment_rows.append({
            "exp_id": exp_id,
            "experiment_side": name,
            "physical_experiment": meta["experiment"],
            "side": meta["side"],
            "released_split": sorted(set(data.split_names[idx].tolist())),
            "rows": int(idx.sum()),
            "lineages": int(len(np.unique(data.lineage_ids[idx]))),
        })
    physical_names = [row["physical_experiment"] for row in experiment_rows]
    mask_sums = data.masks.reshape(len(data.masks), -1).sum(axis=1)

    groups_contiguous = True
    duplicate_aug_groups = 0
    for lineage_id in range(len(counts)):
        positions = np.flatnonzero(data.lineage_ids == lineage_id)
        groups_contiguous &= bool(np.all(np.diff(positions) == 1))
        duplicate_aug_groups += int(len(np.unique(data.augs[positions], axis=0)) != len(positions))

    split_phys: dict[str, set[str]] = {}
    for split in ("train", "val", "test"):
        split_phys[split] = {
            data.metadata[str(data.exp_names[int(exp_id)])]["experiment"]
            for exp_id in np.unique(data.exp_ids[data.split_names == split])
        }
    overlap = {
        "train_val": sorted(split_phys["train"] & split_phys["val"]),
        "train_test": sorted(split_phys["train"] & split_phys["test"]),
        "val_test": sorted(split_phys["val"] & split_phys["test"]),
    }
    checks = {
        "md5_matches_release": file_hash(source, "md5") == EXPECTED_MD5,
        "four_experiment_side_ids": len(unique_experiments) == 4,
        "physical_experiments_unique_within_subset": len(set(physical_names)) == 4,
        "no_physical_experiment_overlap_across_released_splits": not any(overlap.values()),
        "exactly_eight_rows_per_lineage": bool(np.all(counts == EXPECTED_AUGMENTATIONS)),
        "lineages_are_contiguous": groups_contiguous,
        "augmentation_tuples_unique_within_lineage": duplicate_aug_groups == 0,
        "mask_is_empty_or_one_255_pixel": bool(np.all(np.isin(mask_sums, [0, 255]))),
        "sif_constant_within_lineage": True,
        "force_constant_within_lineage": True,
    }
    for lineage_id in range(len(counts)):
        idx = data.lineage_ids == lineage_id
        checks["sif_constant_within_lineage"] &= bool(np.all(data.sifs[idx] == data.sifs[idx][0]))
        checks["force_constant_within_lineage"] &= bool(np.all(data.forces[idx] == data.forces[idx][0]))

    return {
        "source": str(source.resolve()),
        "source_md5": file_hash(source, "md5"),
        "expected_md5": EXPECTED_MD5,
        "checks": checks,
        "gate_pass": all(checks.values()),
        "n_rows": int(len(data.images)),
        "n_lineages": int(len(counts)),
        "lineage_size_distribution": {str(k): int(v) for k, v in zip(*np.unique(counts, return_counts=True))},
        "empty_tip_masks": int(np.sum(mask_sums == 0)),
        "experiments": experiment_rows,
        "released_split_physical_overlap": overlap,
        "label_convention": "one pixel with value 255; empty means augmented tip cropped out",
        "lineage_definition": "exact (experiment-side, force, KI, KII, T) tuple",
        "side_identity_rule": "left/right share physical specimen identity when metadata experiment matches",
    }


def lineage_representatives(data: Dataset, row_idx: np.ndarray) -> np.ndarray:
    ids = np.unique(data.lineage_ids[row_idx])
    return np.asarray([np.flatnonzero(data.lineage_ids == lineage)[0] for lineage in ids], dtype=np.int64)


def shortcut_raw_features(data: Dataset, row_idx: np.ndarray) -> np.ndarray:
    rows = []
    for i in row_idx:
        meta = data.metadata[str(data.exp_names[int(data.exp_ids[i])])]
        log_force = math.log(max(float(data.forces[i]), 1e-6))
        r = float(meta["R"])
        tl = float(meta["orientation"].startswith("TL"))
        right = float(meta["side"] == "right")
        rows.append([log_force, log_force**2, r, tl, right, log_force * r, log_force * tl, r * tl])
    return np.asarray(rows, dtype=np.float64)


@dataclass
class RidgeShortcut:
    mean: np.ndarray
    scale: np.ndarray
    coef: np.ndarray

    def predict(self, x: np.ndarray) -> np.ndarray:
        z = (x - self.mean) / self.scale
        return np.column_stack([np.ones(len(z)), z]) @ self.coef


def fit_shortcut(data: Dataset, row_idx: np.ndarray, alpha: float = 1e-3) -> RidgeShortcut:
    reps = lineage_representatives(data, row_idx)
    x = shortcut_raw_features(data, reps)
    y = data.sifs[reps].astype(np.float64)
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale < 1e-9] = 1.0
    z = (x - mean) / scale
    design = np.column_stack([np.ones(len(z)), z])
    penalty = np.eye(design.shape[1]) * alpha
    penalty[0, 0] = 0.0
    coef = np.linalg.solve(design.T @ design + penalty, design.T @ y)
    return RidgeShortcut(mean=mean, scale=scale, coef=coef)


def tensile_energy(images: np.ndarray) -> np.ndarray:
    e = 70.0e9
    nu = 0.33
    lam = e * nu / (1.0 - nu**2)
    mu = e / (2.0 * (1.0 + nu))
    u = images.astype(np.float64, copy=False)
    ux, uy = u[:, 0], u[:, 1]
    dux_dy, dux_dx = np.gradient(ux, axis=(1, 2))
    duy_dy, duy_dx = np.gradient(uy, axis=(1, 2))
    exx, eyy = dux_dx, duy_dy
    exy = 0.5 * (dux_dy + duy_dx)
    trace = exx + eyy
    radius = np.sqrt((0.5 * (exx - eyy)) ** 2 + exy**2)
    eig1, eig2 = 0.5 * trace + radius, 0.5 * trace - radius
    return 0.5 * lam * np.maximum(trace, 0.0) ** 2 + mu * (
        np.maximum(eig1, 0.0) ** 2 + np.maximum(eig2, 0.0) ** 2
    )


def tip_xy(masks: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    flat = masks.reshape(len(masks), -1)
    visible = flat.any(axis=1)
    target = np.argmax(flat, axis=1)
    y, x = np.divmod(target, 28)
    return np.column_stack([x, y]).astype(np.float64), visible


def energy_coordinates(images: np.ndarray) -> np.ndarray:
    maximum = np.argmax(tensile_energy(images).reshape(len(images), -1), axis=1)
    y, x = np.divmod(maximum, 28)
    return np.column_stack([x, y]).astype(np.float64)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    import torch
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def build_model():
    import torch.nn as nn

    class TinyMechanicsNet(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.encoder = nn.Sequential(
                nn.Conv2d(2, 16, 3, padding=1), nn.GroupNorm(4, 16), nn.SiLU(),
                nn.Conv2d(16, 32, 3, padding=1), nn.GroupNorm(8, 32), nn.SiLU(),
                nn.Conv2d(32, 32, 3, padding=2, dilation=2), nn.GroupNorm(8, 32), nn.SiLU(),
            )
            self.tip_head = nn.Conv2d(32, 1, 1)
            self.sif_head = nn.Sequential(nn.AdaptiveAvgPool2d(1), nn.Flatten(), nn.Linear(32, 32), nn.SiLU(), nn.Linear(32, 3))

        def forward(self, x):
            z = self.encoder(x)
            return self.tip_head(z).flatten(1), self.sif_head(z)

    return TinyMechanicsNet()


def train_one(
    data: Dataset,
    train_idx: np.ndarray,
    seed: int,
    shortcut: RidgeShortcut,
    epochs: int,
    batch_size: int,
    device: str,
    checkpoint: Path,
) -> dict[str, Any]:
    import torch
    import torch.nn.functional as f
    from torch.utils.data import DataLoader, TensorDataset

    set_seed(seed)
    channel_mean = data.images[train_idx].mean(axis=(0, 2, 3)).astype(np.float32)
    channel_std = data.images[train_idx].std(axis=(0, 2, 3)).astype(np.float32)
    channel_std[channel_std < 1e-12] = 1.0
    x = (data.images[train_idx] - channel_mean[None, :, None, None]) / channel_std[None, :, None, None]
    mask_flat = data.masks[train_idx].reshape(len(train_idx), -1)
    visible = mask_flat.any(axis=1)
    tip_target = np.argmax(mask_flat, axis=1).astype(np.int64)
    shortcut_pred = shortcut.predict(shortcut_raw_features(data, train_idx))
    residual = data.sifs[train_idx].astype(np.float64) - shortcut_pred
    residual_scale = residual.std(axis=0).astype(np.float32)
    residual_scale[residual_scale < 1e-8] = 1.0
    residual_z = (residual / residual_scale).astype(np.float32)

    dataset = TensorDataset(
        torch.from_numpy(x.astype(np.float32)), torch.from_numpy(tip_target),
        torch.from_numpy(visible), torch.from_numpy(residual_z),
    )
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, generator=generator, num_workers=0)
    model = build_model().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    history = []
    for epoch in range(epochs):
        model.train()
        totals = np.zeros(4, dtype=np.float64)
        for xb, tip, valid, sif in loader:
            xb, tip, valid, sif = xb.to(device), tip.to(device), valid.to(device), sif.to(device)
            logits, residual_pred = model(xb)
            if bool(valid.any()):
                tip_loss = f.cross_entropy(logits[valid], tip[valid])
            else:
                tip_loss = logits.sum() * 0.0
            sif_loss = f.mse_loss(residual_pred, sif)
            loss = tip_loss + 0.5 * sif_loss
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            totals += [float(loss.detach()), float(tip_loss.detach()), float(sif_loss.detach()), len(xb)]
        history.append({"epoch": epoch + 1, "loss": totals[0] / len(loader), "tip_ce": totals[1] / len(loader), "sif_mse": totals[2] / len(loader)})
        if not np.isfinite(totals[:3]).all():
            raise RuntimeError(f"non-finite loss at epoch {epoch + 1}")
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "state_dict": model.state_dict(), "channel_mean": channel_mean,
        "channel_std": channel_std, "residual_scale": residual_scale,
        "seed": seed, "epochs": epochs,
    }, checkpoint)
    return {"seed": seed, "epochs": epochs, "history": history, "parameters": sum(p.numel() for p in model.parameters())}


def predict_checkpoint(data: Dataset, idx: np.ndarray, shortcut: RidgeShortcut, checkpoint: Path, device: str, batch_size: int) -> tuple[np.ndarray, np.ndarray]:
    import torch
    from torch.utils.data import DataLoader, TensorDataset

    try:
        state = torch.load(checkpoint, map_location=device, weights_only=False)
    except TypeError:  # PyTorch before the weights_only keyword.
        state = torch.load(checkpoint, map_location=device)
    x = (data.images[idx] - state["channel_mean"][None, :, None, None]) / state["channel_std"][None, :, None, None]
    loader = DataLoader(TensorDataset(torch.from_numpy(x.astype(np.float32))), batch_size=batch_size, shuffle=False)
    model = build_model().to(device)
    model.load_state_dict(state["state_dict"])
    model.eval()
    probs, residuals = [], []
    with torch.no_grad():
        for (xb,) in loader:
            logits, residual = model(xb.to(device))
            probs.append(torch.softmax(logits, dim=1).cpu().numpy())
            residuals.append(residual.cpu().numpy())
    probability = np.concatenate(probs)
    residual = np.concatenate(residuals) * state["residual_scale"][None]
    sif = shortcut.predict(shortcut_raw_features(data, idx)) + residual
    return probability, sif


def weighted_coordinate(probability: np.ndarray) -> np.ndarray:
    grid_y, grid_x = np.divmod(np.arange(28 * 28), 28)
    return np.column_stack([probability @ grid_x, probability @ grid_y])


def lineage_mean(values: np.ndarray, lineages: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ids = np.unique(lineages)
    return ids, np.asarray([values[lineages == lineage].mean(axis=0) for lineage in ids])


def quantile_higher(values: np.ndarray, q: float) -> float:
    try:
        return float(np.quantile(values, q, method="higher"))
    except TypeError:
        return float(np.quantile(values, q, interpolation="higher"))


def failure_auroc(confidence: np.ndarray, failure: np.ndarray) -> float | None:
    # Higher -confidence means more likely to fail. Mann-Whitney form, with ties.
    pos = -confidence[failure]
    neg = -confidence[~failure]
    if len(pos) == 0 or len(neg) == 0:
        return None
    return float((sum((p > neg).sum() + 0.5 * (p == neg).sum() for p in pos)) / (len(pos) * len(neg)))


def prediction_set_stats(probability: np.ndarray, target_flat: np.ndarray, calibration_mass: float) -> tuple[float, float]:
    order = np.argsort(-probability, axis=1)
    sorted_prob = np.take_along_axis(probability, order, axis=1)
    cumulative = np.cumsum(sorted_prob, axis=1)
    ranks = np.argmax(order == target_flat[:, None], axis=1)
    required = cumulative[np.arange(len(probability)), ranks]
    sizes = np.sum(cumulative < calibration_mass, axis=1) + 1
    return float(np.mean(required <= calibration_mass)), float(np.mean(sizes))


def evaluate_fold(
    data: Dataset,
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    test_idx: np.ndarray,
    shortcut: RidgeShortcut,
    val_prob_seeds: np.ndarray,
    val_sif_seeds: np.ndarray,
    test_prob_seeds: np.ndarray,
    test_sif_seeds: np.ndarray,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    train_xy, train_visible = tip_xy(data.masks[train_idx])
    spatial = train_xy[train_visible].mean(axis=0)
    test_xy, test_visible = tip_xy(data.masks[test_idx])
    val_xy, val_visible = tip_xy(data.masks[val_idx])
    test_prob = test_prob_seeds.mean(axis=0)
    val_prob = val_prob_seeds.mean(axis=0)
    model_xy = weighted_coordinate(test_prob)
    energy_xy = energy_coordinates(data.images[test_idx])
    model_error = np.linalg.norm(model_xy[test_visible] - test_xy[test_visible], axis=1)
    spatial_error = np.linalg.norm(spatial[None] - test_xy[test_visible], axis=1)
    energy_error = np.linalg.norm(energy_xy[test_visible] - test_xy[test_visible], axis=1)
    confidence = test_prob[test_visible].max(axis=1)
    full_risk = float(model_error.mean())
    order = np.argsort(-confidence)
    risk = {}
    for coverage in (1.0, 0.8, 0.5):
        k = max(1, int(math.ceil(coverage * len(order))))
        risk[str(coverage)] = float(model_error[order[:k]].mean())
    aurc = float(np.mean([model_error[order[:k]].mean() for k in range(1, len(order) + 1)]))
    auroc = failure_auroc(confidence, model_error > TIP_FAILURE_PX)

    # Calibrate a heatmap prediction-set mass on the separate validation experiment.
    val_flat = np.argmax(data.masks[val_idx][val_visible].reshape(val_visible.sum(), -1), axis=1)
    order_val = np.argsort(-val_prob[val_visible], axis=1)
    cumulative_val = np.cumsum(np.take_along_axis(val_prob[val_visible], order_val, axis=1), axis=1)
    rank_val = np.argmax(order_val == val_flat[:, None], axis=1)
    calibration_mass = quantile_higher(cumulative_val[np.arange(len(rank_val)), rank_val], 0.90)
    test_flat = np.argmax(data.masks[test_idx][test_visible].reshape(test_visible.sum(), -1), axis=1)
    tip_coverage, tip_set_size = prediction_set_stats(test_prob[test_visible], test_flat, calibration_mass)

    test_lineages = data.lineage_ids[test_idx]
    val_lineages = data.lineage_ids[val_idx]
    test_sif_mean = test_sif_seeds.mean(axis=0)
    val_sif_mean = val_sif_seeds.mean(axis=0)
    test_ids, test_lineage_pred = lineage_mean(test_sif_mean, test_lineages)
    _, test_lineage_true = lineage_mean(data.sifs[test_idx], test_lineages)
    val_ids, val_lineage_pred = lineage_mean(val_sif_mean, val_lineages)
    _, val_lineage_true = lineage_mean(data.sifs[val_idx], val_lineages)
    _, shortcut_test = lineage_mean(shortcut.predict(shortcut_raw_features(data, test_idx)), test_lineages)

    # Ensemble spread is computed after averaging each seed over augmentations.
    test_seed_lineage = []
    val_seed_lineage = []
    for seed_pred in test_sif_seeds:
        _, pred = lineage_mean(seed_pred, test_lineages)
        test_seed_lineage.append(pred)
    for seed_pred in val_sif_seeds:
        _, pred = lineage_mean(seed_pred, val_lineages)
        val_seed_lineage.append(pred)
    test_seed_lineage = np.asarray(test_seed_lineage)
    val_seed_lineage = np.asarray(val_seed_lineage)
    test_std = test_seed_lineage.std(axis=0, ddof=1)
    val_std = val_seed_lineage.std(axis=0, ddof=1)
    floor = np.maximum(np.std(data.sifs[train_idx], axis=0) * 0.02, 1e-6)
    scale_q = np.asarray([
        quantile_higher(np.abs(val_lineage_true[:, j] - val_lineage_pred[:, j]) / (val_std[:, j] + floor[j]), 0.90)
        for j in range(3)
    ])
    half_width = scale_q[None] * (test_std + floor[None])
    sif_coverage = np.mean(np.abs(test_lineage_true - test_lineage_pred) <= half_width, axis=0)
    width = 2.0 * half_width.mean(axis=0)
    train_scale = np.std(data.sifs[train_idx], axis=0)
    train_scale[train_scale < 1e-8] = 1.0
    model_mae = np.mean(np.abs(test_lineage_true - test_lineage_pred), axis=0)
    shortcut_mae = np.mean(np.abs(test_lineage_true - shortcut_test), axis=0)
    model_nmae = float(np.mean(model_mae / train_scale))
    shortcut_nmae = float(np.mean(shortcut_mae / train_scale))

    result = {
        "n_test_rows": int(len(test_idx)),
        "n_test_lineages": int(len(test_ids)),
        "n_visible_tip_rows": int(test_visible.sum()),
        "tip": {
            "model_error_mean_px": full_risk,
            "model_error_median_px": float(np.median(model_error)),
            "spatial_error_mean_px": float(spatial_error.mean()),
            "spatial_error_median_px": float(np.median(spatial_error)),
            "energy_error_mean_px": float(energy_error.mean()),
            "energy_error_median_px": float(np.median(energy_error)),
            "risk_at_coverage": risk,
            "aurc_px": aurc,
            "failure_auroc_at_3px": auroc,
            "prediction_region_coverage": tip_coverage,
            "prediction_region_size_px": tip_set_size,
            "calibration_mass": calibration_mass,
        },
        "sif": {
            "targets": ["KI", "KII", "T"],
            "model_mae": model_mae.tolist(),
            "shortcut_mae": shortcut_mae.tolist(),
            "model_nmae": model_nmae,
            "shortcut_nmae": shortcut_nmae,
            "interval_90_coverage": sif_coverage.tolist(),
            "interval_mean_width": width.tolist(),
            "calibration_scale": scale_q.tolist(),
        },
    }
    arrays = {
        "test_idx": test_idx, "test_visible": test_visible, "test_model_xy": model_xy,
        "test_true_xy": test_xy, "test_energy_xy": energy_xy,
        "test_lineage_ids": test_ids, "test_sif_true": test_lineage_true,
        "test_sif_model": test_lineage_pred, "test_sif_shortcut": shortcut_test,
        "test_sif_half_width": half_width, "tip_confidence": confidence,
        "tip_error": model_error, "tip_spatial_error": spatial_error,
        "tip_energy_error": energy_error,
        "tip_visible_lineages": data.lineage_ids[test_idx][test_visible],
    }
    return result, arrays


def bootstrap_ci(values_by_experiment: list[np.ndarray], seed: int = 20261005, n_boot: int = 2000) -> list[float]:
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n_boot):
        exp_means = []
        for values in values_by_experiment:
            exp_means.append(float(rng.choice(values, size=len(values), replace=True).mean()))
        draws.append(float(np.mean(exp_means)))
    return [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))]


def render_figures(output: Path, fold_results: list[dict[str, Any]], fold_arrays: list[dict[str, np.ndarray]]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = [row["test_experiment"] for row in fold_results]
    x = np.arange(len(names))
    width = 0.25
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].bar(x - width, [r["tip"]["model_error_median_px"] for r in fold_results], width, label="DIC model")
    axes[0].bar(x, [r["tip"]["spatial_error_median_px"] for r in fold_results], width, label="spatial prior")
    axes[0].bar(x + width, [r["tip"]["energy_error_median_px"] for r in fold_results], width, label="energy argmax")
    axes[0].set_ylabel("median tip error (pixels)")
    axes[0].set_xticks(x, names, rotation=25, ha="right")
    axes[0].legend(frameon=False)
    axes[0].set_title("Physical-experiment holdout: localization")
    axes[1].bar(x - width / 2, [r["sif"]["model_nmae"] for r in fold_results], width, label="shortcut + DIC residual")
    axes[1].bar(x + width / 2, [r["sif"]["shortcut_nmae"] for r in fold_results], width, label="force + metadata")
    axes[1].set_ylabel("mean normalized SIF MAE")
    axes[1].set_xticks(x, names, rotation=25, ha="right")
    axes[1].legend(frameon=False)
    axes[1].set_title("Incremental mechanics information")
    fig.tight_layout()
    fig.savefig(output / "figures" / "per_experiment_baseline_comparison.png", dpi=220)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for name, arrays in zip(names, fold_arrays):
        order = np.argsort(-arrays["tip_confidence"])
        error = arrays["tip_error"][order]
        risk = np.asarray([error[:k].mean() for k in range(1, len(error) + 1)])
        axes[0].plot(np.arange(1, len(error) + 1) / len(error), risk, label=name)
    axes[0].set_xlabel("coverage")
    axes[0].set_ylabel("mean tip error (pixels)")
    axes[0].set_title("Risk-coverage")
    axes[0].legend(frameon=False, fontsize=7)
    coverages = np.asarray([r["sif"]["interval_90_coverage"] for r in fold_results])
    for j, target in enumerate(("KI", "KII", "T")):
        axes[1].plot(x, coverages[:, j], marker="o", label=target)
    axes[1].axhline(0.9, color="black", linestyle="--", linewidth=1)
    axes[1].set_ylim(0, 1.02)
    axes[1].set_xticks(x, names, rotation=25, ha="right")
    axes[1].set_ylabel("90% interval empirical coverage")
    axes[1].set_title("Held-out SIF calibration")
    axes[1].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output / "figures" / "uncertainty_and_abstention.png", dpi=220)
    plt.close(fig)


def run_training(data: Dataset, output: Path, epochs: int, batch_size: int, device: str) -> dict[str, Any]:
    unique_experiments = sorted(np.unique(data.exp_ids).tolist())
    if len(unique_experiments) != 4:
        raise RuntimeError("frozen protocol requires exactly four experiment-side IDs")
    fold_results: list[dict[str, Any]] = []
    fold_arrays: list[dict[str, np.ndarray]] = []
    run_rows = []
    for position, test_exp in enumerate(unique_experiments):
        val_exp = unique_experiments[(position + 1) % len(unique_experiments)]
        train_exp = [x for x in unique_experiments if x not in (test_exp, val_exp)]
        train_idx = np.flatnonzero(np.isin(data.exp_ids, train_exp))
        val_idx = np.flatnonzero(data.exp_ids == val_exp)
        test_idx = np.flatnonzero(data.exp_ids == test_exp)
        shortcut = fit_shortcut(data, train_idx)
        fold_dir = output / "checkpoints" / f"holdout_{test_exp}"
        start = time.time()
        for seed in SEEDS:
            checkpoint = fold_dir / f"seed_{seed}.pt"
            record = train_one(data, train_idx, seed, shortcut, epochs, batch_size, device, checkpoint)
            write_json(fold_dir / f"seed_{seed}_history.json", record)
            run_rows.append({"test_exp": test_exp, "val_exp": val_exp, "train_exp": train_exp, "seed": seed, "checkpoint": str(checkpoint), "parameters": record["parameters"]})
        val_prob, val_sif, test_prob, test_sif = [], [], [], []
        for seed in SEEDS:
            checkpoint = fold_dir / f"seed_{seed}.pt"
            p, s = predict_checkpoint(data, val_idx, shortcut, checkpoint, device, batch_size)
            val_prob.append(p); val_sif.append(s)
            p, s = predict_checkpoint(data, test_idx, shortcut, checkpoint, device, batch_size)
            test_prob.append(p); test_sif.append(s)
        result, arrays = evaluate_fold(
            data, train_idx, val_idx, test_idx, shortcut,
            np.asarray(val_prob), np.asarray(val_sif), np.asarray(test_prob), np.asarray(test_sif),
        )
        result.update({
            "test_exp_id": test_exp,
            "test_experiment": str(data.exp_names[test_exp]),
            "validation_experiment": str(data.exp_names[val_exp]),
            "training_experiments": [str(data.exp_names[x]) for x in train_exp],
            "elapsed_seconds": time.time() - start,
        })
        fold_results.append(result)
        fold_arrays.append(arrays)
        (output / "predictions").mkdir(parents=True, exist_ok=True)
        np.savez_compressed(output / "predictions" / f"holdout_{test_exp}.npz", **arrays)

    rows = []
    for result in fold_results:
        row = {
            "experiment": result["test_experiment"],
            "n_lineages": result["n_test_lineages"],
            "tip_model_median_px": result["tip"]["model_error_median_px"],
            "tip_spatial_median_px": result["tip"]["spatial_error_median_px"],
            "tip_energy_median_px": result["tip"]["energy_error_median_px"],
            "tip_prediction_region_coverage": result["tip"]["prediction_region_coverage"],
            "tip_prediction_region_size_px": result["tip"]["prediction_region_size_px"],
            "tip_failure_auroc_3px": result["tip"]["failure_auroc_at_3px"],
            "tip_risk_50pct": result["tip"]["risk_at_coverage"]["0.5"],
            "tip_risk_100pct": result["tip"]["risk_at_coverage"]["1.0"],
            "sif_model_nmae": result["sif"]["model_nmae"],
            "sif_shortcut_nmae": result["sif"]["shortcut_nmae"],
        }
        for j, target in enumerate(("KI", "KII", "T")):
            row[f"{target}_model_mae"] = result["sif"]["model_mae"][j]
            row[f"{target}_shortcut_mae"] = result["sif"]["shortcut_mae"][j]
            row[f"{target}_interval_coverage"] = result["sif"]["interval_90_coverage"][j]
            row[f"{target}_interval_width"] = result["sif"]["interval_mean_width"][j]
        rows.append(row)
    table_path = output / "tables" / "per_experiment_metrics.csv"
    table_path.parent.mkdir(parents=True, exist_ok=True)
    with table_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

    loc_passes, sif_passes, uncertainty_passes = 0, 0, 0
    loc_differences, sif_differences = [], []
    for result, arrays in zip(fold_results, fold_arrays):
        best_baseline = min(result["tip"]["spatial_error_median_px"], result["tip"]["energy_error_median_px"])
        loc_gain = 1.0 - result["tip"]["model_error_median_px"] / best_baseline
        sif_gain = 1.0 - result["sif"]["model_nmae"] / result["sif"]["shortcut_nmae"]
        result["tip_gain_over_best_baseline"] = loc_gain
        result["sif_gain_over_shortcut"] = sif_gain
        loc_passes += int(loc_gain >= 0.10)
        sif_passes += int(sif_gain >= 0.10)
        risk_ok = result["tip"]["risk_at_coverage"]["0.5"] <= 0.8 * result["tip"]["risk_at_coverage"]["1.0"]
        auroc = result["tip"]["failure_auroc_at_3px"]
        uncertainty_passes += int(risk_ok and auroc is not None and auroc >= 0.65)
        # Aggregate signed localization improvement within each physical-field
        # lineage before bootstrap; augmentations are never pseudo-replicates.
        lineage = arrays["tip_visible_lineages"]
        per_row_gain = np.minimum(arrays["tip_spatial_error"], arrays["tip_energy_error"]) - arrays["tip_error"]
        loc_differences.append(np.asarray([per_row_gain[lineage == value].mean() for value in np.unique(lineage)]))
        per_l_model = np.mean(np.abs(arrays["test_sif_true"] - arrays["test_sif_model"]), axis=1)
        per_l_short = np.mean(np.abs(arrays["test_sif_true"] - arrays["test_sif_shortcut"]), axis=1)
        sif_differences.append(per_l_short - per_l_model)

    loc_ci = bootstrap_ci(loc_differences)
    sif_ci = bootstrap_ci(sif_differences)
    coverages = np.asarray([r["sif"]["interval_90_coverage"] for r in fold_results])
    sif_coverage_ok = bool(np.all((coverages.mean(axis=0) >= 0.80) & (coverages.mean(axis=0) <= 0.98)))
    gates = {
        "localization": {"pass_folds": loc_passes, "required": 3, "equal_experiment_gain_ci95": loc_ci, "pass": loc_passes >= 3 and loc_ci[0] > 0},
        "sif_increment": {"pass_folds": sif_passes, "required": 3, "equal_experiment_mae_difference_ci95": sif_ci, "pass": sif_passes >= 3 and sif_ci[0] > 0},
        "uncertainty_abstention": {"abstention_pass_folds": uncertainty_passes, "required": 3, "sif_mean_coverage_by_target": coverages.mean(axis=0).tolist(), "sif_coverage_ok": sif_coverage_ok, "pass": uncertainty_passes >= 3 and sif_coverage_ok},
    }
    decision = "GO_BOUNDED_CRACKMNIST_MECHANICS_CV" if all(gate["pass"] for gate in gates.values()) else "NO_GO_CRACKMNIST_MECHANICS_CV"
    summary = {"decision": decision, "gates": gates, "folds": fold_results, "runs": run_rows}
    write_json(output / "summary.json", summary)
    render_figures(output, fold_results, fold_arrays)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("audit", "train"), default="audit")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    data = load_dataset(args.data, args.metadata)
    audit = audit_dataset(data, args.data)
    write_json(args.output / "data_audit.json", audit)
    receipt = {
        "mode": args.mode,
        "command": " ".join(sys.argv),
        "started_unix": time.time(),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python": sys.version,
        "git_commit": git_value(["git", "rev-parse", "HEAD"]),
        "git_branch": git_value(["git", "branch", "--show-current"]),
        "git_dirty": git_value(["git", "status", "--porcelain"]),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", "unset"),
        "data_md5": audit["source_md5"],
        "seeds": list(SEEDS),
        "epochs": args.epochs,
        "batch_size": args.batch_size,
    }
    if args.mode == "audit":
        receipt["execution_status"] = "audit_pass" if audit["gate_pass"] else "audit_fail"
        write_json(args.output / "run_receipt.json", receipt)
        if not audit["gate_pass"]:
            raise SystemExit(2)
        return
    if not audit["gate_pass"]:
        receipt["execution_status"] = "blocked_by_data_gate"
        write_json(args.output / "run_receipt.json", receipt)
        raise SystemExit("NO-GO: dataset identity/lineage gate failed")
    if args.device.startswith("cuda"):
        import torch
        if not torch.cuda.is_available():
            raise SystemExit("CUDA requested but unavailable; formal training is producer-only")
        receipt["torch"] = torch.__version__
        receipt["gpu"] = torch.cuda.get_device_name(0)
    summary = run_training(data, args.output, args.epochs, args.batch_size, args.device)
    receipt["execution_status"] = "succeeded"
    receipt["completed_unix"] = time.time()
    receipt["scientific_decision"] = summary["decision"]
    write_json(args.output / "run_receipt.json", receipt)


if __name__ == "__main__":
    main()
