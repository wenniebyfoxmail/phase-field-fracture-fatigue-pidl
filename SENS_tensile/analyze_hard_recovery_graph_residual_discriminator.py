#!/usr/bin/env python3
"""State-safe graph-vs-MLP discriminator for the hard-recovery raw-driver gap.

This is an offline supervised diagnostic. It never enters the PIDL training
loop. PIDL element diagnostics are projected to the archived FEM cells with the
polygon-overlap map, and the graph is the exact FEM cell dual graph. The only
primary target is the cycle-peak raw-driver residual:

    log10(psi_raw_FEM + eps) - log10(psi_raw_PIDL + eps)

The script deliberately does not synthesize a FEM active driver from peak raw
psi and unloaded damage. That combination has mixed state semantics.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import meshio
import numpy as np
import torch
import torch.nn as nn
from scipy.io import loadmat


EPS = 1.0e-12
HERE = Path(__file__).resolve().parent
REPO = HERE.parent
PROJECT = REPO.parent

DEFAULT_COMPARE_ROOT = (
    PROJECT
    / "local_archive"
    / "after_strict_setting_alignment"
    / "fem"
    / "three_case_compare_20260701"
)
DEFAULT_FEM_ROOT = (
    DEFAULT_COMPARE_ROOT
    / "extracted"
    / "SENS_brittle_base_cyclic_u012_recovery_fatigueon_pidlstop_newtontol4em4"
)
DEFAULT_PROJECTION = (
    DEFAULT_COMPARE_ROOT
    / "analysis"
    / "state_mechanism_compare_20260701"
    / "projected_residuals"
    / "projected_npz"
    / "projection_map_polygon_overlap.npz"
)
DEFAULT_PIDL_DIAG = (
    Path.home()
    / "Library"
    / "CloudStorage"
    / "OneDrive-UniversityofCambridge"
    / "hard_d1_u0_recovery_5step_0630_formal"
    / "raw"
    / "run"
    / "element_diagnostics_probe_driver"
)
DEFAULT_OUT = (
    DEFAULT_COMPARE_ROOT
    / "analysis"
    / "hard_recovery_graph_residual_v2_20260710"
)


FEATURE_SPECS = (
    ("alpha_elem", "linear"),
    ("hist_alpha_elem", "linear"),
    ("hist_fat_elem", "log1p"),
    ("f_fatigue_elem", "linear"),
    ("g_alpha_elem", "log10"),
    ("psi_raw_elem", "log10"),
    ("psi_active_elem", "log10"),
    ("psi_plus_prev_elem", "log10"),
    ("delta_alpha_bar_input_elem", "log1p"),
    ("E_el_elem", "signed_log1p"),
    ("E_d_elem", "signed_log1p"),
    ("E_hist_elem", "signed_log1p"),
    ("eps_xx_elem", "signed_log1p"),
    ("eps_yy_elem", "signed_log1p"),
    ("eps_xy_elem", "signed_log1p"),
    ("sigma_raw_xx_elem", "signed_log1p"),
    ("sigma_raw_yy_elem", "signed_log1p"),
    ("sigma_raw_xy_elem", "signed_log1p"),
)


@dataclass(frozen=True)
class ProjectionMap:
    src: np.ndarray
    dst: np.ndarray
    weight: np.ndarray
    denominator: np.ndarray


@dataclass(frozen=True)
class CellGraph:
    centroids: np.ndarray
    area: np.ndarray
    cells: np.ndarray
    src: np.ndarray
    dst: np.ndarray


@dataclass
class CycleSample:
    cycle: int
    pidl_step: int
    features: np.ndarray
    target: np.ndarray
    fem_raw: np.ndarray
    pidl_raw: np.ndarray
    valid: np.ndarray
    weights: np.ndarray


@dataclass
class FeatureScaler:
    mean: np.ndarray
    std: np.ndarray
    target_mean: float
    target_std: float


@dataclass
class TensorSample:
    cycle: int
    pidl_step: int
    features: torch.Tensor
    target: torch.Tensor
    valid: torch.Tensor
    weights: torch.Tensor
    edge_src: torch.Tensor
    edge_dst: torch.Tensor


def parse_ints(text: str) -> list[int]:
    return [int(item.strip()) for item in str(text).split(",") if item.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_provenance(repo: Path) -> dict[str, object]:
    def run(*args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.stdout.strip()

    try:
        return {
            "commit": run("rev-parse", "HEAD"),
            "branch": run("branch", "--show-current"),
            "dirty": bool(run("status", "--porcelain")),
        }
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "branch": None, "dirty": None}


def hard_recovery_peak_step(cycle: int) -> int:
    if cycle < 1:
        raise ValueError("hard-recovery physical cycles start at 1")
    return 1 + 5 * (int(cycle) - 1) + 3


def transform_feature(values: np.ndarray, mode: str) -> np.ndarray:
    x = np.asarray(values, dtype=np.float64)
    if mode == "linear":
        return x
    if mode == "log10":
        return np.log10(np.maximum(x, 0.0) + EPS)
    if mode == "log1p":
        return np.log1p(np.maximum(x, 0.0))
    if mode == "signed_log1p":
        return np.sign(x) * np.log1p(np.abs(x))
    raise ValueError(f"unknown feature transform {mode!r}")


def raw_log(values: np.ndarray) -> np.ndarray:
    return np.log10(np.maximum(np.asarray(values, dtype=np.float64), 0.0) + EPS)


def load_projection_map(path: Path, n_fem: int) -> ProjectionMap:
    with np.load(path) as z:
        src = np.asarray(z["src"], dtype=np.int64).reshape(-1)
        dst = np.asarray(z["dst"], dtype=np.int64).reshape(-1)
        weight = np.asarray(z["weight"], dtype=np.float64).reshape(-1)
    if not (src.shape == dst.shape == weight.shape):
        raise ValueError("projection src/dst/weight shapes differ")
    if src.size == 0 or np.any(src < 0) or np.any(dst < 0) or np.any(dst >= n_fem):
        raise ValueError("projection map has invalid indices")
    if np.any(~np.isfinite(weight)) or np.any(weight < 0):
        raise ValueError("projection weights must be finite and non-negative")
    denominator = np.bincount(dst, weights=weight, minlength=n_fem)
    return ProjectionMap(src=src, dst=dst, weight=weight, denominator=denominator)


def project_to_fem(values: np.ndarray, projection: ProjectionMap, n_fem: int) -> np.ndarray:
    source = np.asarray(values, dtype=np.float64).reshape(-1)
    if projection.src.max(initial=-1) >= source.size:
        raise ValueError(
            f"projection references PIDL element {projection.src.max()}, "
            f"but field has {source.size} elements"
        )
    numerator = np.bincount(
        projection.dst,
        weights=source[projection.src] * projection.weight,
        minlength=n_fem,
    )
    out = np.full(n_fem, np.nan, dtype=np.float64)
    covered = projection.denominator > 0
    out[covered] = numerator[covered] / projection.denominator[covered]
    return out


def polygon_area(points: np.ndarray) -> np.ndarray:
    x = points[..., 0]
    y = points[..., 1]
    return 0.5 * np.abs(
        np.sum(x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1), axis=1)
    )


def build_cell_dual_edges(cells: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return directed cell adjacency for cells sharing a complete mesh edge."""
    conn = np.asarray(cells, dtype=np.int64)
    if conn.ndim != 2 or conn.shape[1] < 3:
        raise ValueError(f"expected polygon connectivity, got {conn.shape}")
    edge_pairs = np.stack([conn, np.roll(conn, -1, axis=1)], axis=-1).reshape(-1, 2)
    edge_pairs.sort(axis=1)
    owners = np.repeat(np.arange(conn.shape[0], dtype=np.int64), conn.shape[1])
    order = np.lexsort((edge_pairs[:, 1], edge_pairs[:, 0]))
    sorted_edges = edge_pairs[order]
    sorted_owners = owners[order]
    change = np.ones(sorted_edges.shape[0], dtype=bool)
    change[1:] = np.any(sorted_edges[1:] != sorted_edges[:-1], axis=1)
    starts = np.flatnonzero(change)
    counts = np.diff(np.append(starts, sorted_edges.shape[0]))
    if np.any(counts > 2):
        bad = sorted_edges[starts[np.flatnonzero(counts > 2)[0]]]
        raise ValueError(f"non-manifold mesh edge {bad.tolist()} has >2 owner cells")
    internal = starts[counts == 2]
    left = sorted_owners[internal]
    right = sorted_owners[internal + 1]
    src = np.concatenate([left, right])
    dst = np.concatenate([right, left])
    return src.astype(np.int64), dst.astype(np.int64)


def load_cell_graph(vtk_path: Path) -> CellGraph:
    mesh = meshio.read(vtk_path)
    points = np.asarray(mesh.points[:, :2], dtype=np.float64)
    blocks = [block for block in mesh.cells if block.type in {"quad", "triangle"}]
    if len(blocks) != 1:
        raise ValueError(
            f"expected exactly one triangle/quad cell block in {vtk_path}, "
            f"found {[block.type for block in blocks]}"
        )
    cells = np.asarray(blocks[0].data, dtype=np.int64)
    polygons = points[cells]
    centroids = polygons.mean(axis=1)
    area = polygon_area(polygons)
    if np.any(area <= 0) or np.any(~np.isfinite(area)):
        raise ValueError("FEM mesh contains invalid cell areas")
    src, dst = build_cell_dual_edges(cells)
    return CellGraph(centroids=centroids, area=area, cells=cells, src=src, dst=dst)


def load_fem_raw(path: Path, n_fem: int) -> np.ndarray:
    data = loadmat(path)
    if "psi_elem" not in data:
        raise KeyError(f"{path} does not contain psi_elem")
    values = np.asarray(data["psi_elem"], dtype=np.float64).reshape(-1)
    if values.size != n_fem:
        raise ValueError(f"{path} has {values.size} elements, expected {n_fem}")
    if np.nanmin(values) < -1.0e-10:
        raise ValueError(f"{path} has materially negative raw-driver values")
    return np.maximum(values, 0.0)


def load_pidl_fields(path: Path) -> dict[str, np.ndarray]:
    with np.load(path) as z:
        required = {"psi_raw_elem", *(name for name, _ in FEATURE_SPECS)}
        missing = sorted(required.difference(z.files))
        if missing:
            raise KeyError(f"{path} is missing required fields: {missing}")
        return {name: np.asarray(z[name], dtype=np.float64).reshape(-1) for name in required}


def geometry_features(graph: CellGraph, cycle: int, cycle_scale: float) -> tuple[list[str], np.ndarray]:
    x = graph.centroids[:, 0]
    y = graph.centroids[:, 1]
    radius = np.sqrt(x * x + y * y)
    names = [
        "x",
        "y",
        "abs_y",
        "radius_from_notch",
        "distance_to_right_boundary",
        "log10_cell_area",
        "cycle_fraction",
    ]
    values = np.column_stack(
        [
            x,
            y,
            np.abs(y),
            radius,
            np.nanmax(x) - x,
            np.log10(graph.area + EPS),
            np.full_like(x, float(cycle) / float(cycle_scale)),
        ]
    )
    return names, values


def build_cycle_sample(
    cycle: int,
    graph: CellGraph,
    projection: ProjectionMap,
    pidl_diag_dir: Path,
    fem_psi_dir: Path,
    cycle_scale: float,
    residual_clip: float,
    focus_weight: float,
) -> tuple[CycleSample, list[str]]:
    pidl_step = hard_recovery_peak_step(cycle)
    pidl_path = pidl_diag_dir / f"element_fields_cycle_{pidl_step:04d}.npz"
    fem_path = fem_psi_dir / f"cycle_{cycle:04d}.mat"
    if not pidl_path.exists():
        raise FileNotFoundError(pidl_path)
    if not fem_path.exists():
        raise FileNotFoundError(fem_path)

    pidl = load_pidl_fields(pidl_path)
    n_fem = graph.cells.shape[0]
    fem_raw = load_fem_raw(fem_path, n_fem)
    pidl_projected = {
        name: project_to_fem(values, projection, n_fem) for name, values in pidl.items()
    }
    pidl_raw = pidl_projected["psi_raw_elem"]

    feature_names, geom = geometry_features(graph, cycle, cycle_scale)
    columns = [geom]
    for name, mode in FEATURE_SPECS:
        feature_names.append(f"{mode}:{name}")
        columns.append(transform_feature(pidl_projected[name], mode)[:, None])
    features = np.column_stack(columns)

    valid = (
        (projection.denominator > 0)
        & np.isfinite(fem_raw)
        & np.isfinite(pidl_raw)
        & np.all(np.isfinite(features), axis=1)
    )
    if not np.any(valid):
        raise ValueError(f"cycle {cycle} has no valid projected FEM cells")
    target = raw_log(fem_raw) - raw_log(pidl_raw)
    target = np.clip(target, -float(residual_clip), float(residual_clip))

    finite_fem = fem_raw[valid]
    p99 = float(np.percentile(finite_fem, 99.0))
    relative_floor = 0.01 * float(np.max(finite_fem))
    focus = valid & (fem_raw >= max(p99, relative_floor, EPS))
    weights = graph.area / float(np.mean(graph.area[valid]))
    weights = weights * (1.0 + float(focus_weight) * focus.astype(np.float64))
    weights[~valid] = 0.0
    return (
        CycleSample(
            cycle=cycle,
            pidl_step=pidl_step,
            features=features,
            target=target,
            fem_raw=fem_raw,
            pidl_raw=pidl_raw,
            valid=valid,
            weights=weights,
        ),
        feature_names,
    )


def fit_scaler(train_samples: Sequence[CycleSample]) -> FeatureScaler:
    train_features = np.concatenate([sample.features[sample.valid] for sample in train_samples])
    mean = np.mean(train_features, axis=0)
    std = np.std(train_features, axis=0)
    std[std < 1.0e-8] = 1.0
    targets = np.concatenate([sample.target[sample.valid] for sample in train_samples])
    target_mean = float(np.mean(targets))
    target_std = float(np.std(targets))
    if target_std < 1.0e-8:
        target_std = 1.0
    return FeatureScaler(mean=mean, std=std, target_mean=target_mean, target_std=target_std)


def apply_scaler(samples: Iterable[CycleSample], scaler: FeatureScaler) -> None:
    for sample in samples:
        sample.features = (sample.features - scaler.mean) / scaler.std
        sample.features = np.nan_to_num(sample.features, nan=0.0, posinf=0.0, neginf=0.0)


def to_tensor_sample(
    sample: CycleSample,
    graph: CellGraph,
    scaler: FeatureScaler,
    device: torch.device,
) -> TensorSample:
    return TensorSample(
        cycle=sample.cycle,
        pidl_step=sample.pidl_step,
        features=torch.as_tensor(sample.features, dtype=torch.float32, device=device),
        target=torch.as_tensor(
            (sample.target - scaler.target_mean) / scaler.target_std,
            dtype=torch.float32,
            device=device,
        ),
        valid=torch.as_tensor(sample.valid, dtype=torch.bool, device=device),
        weights=torch.as_tensor(sample.weights, dtype=torch.float32, device=device),
        edge_src=torch.as_tensor(graph.src, dtype=torch.long, device=device),
        edge_dst=torch.as_tensor(graph.dst, dtype=torch.long, device=device),
    )


class ResidualLayer(nn.Module):
    """Parameter-matched pointwise or neighbourhood residual layer."""

    def __init__(self, hidden: int, dropout: float) -> None:
        super().__init__()
        self.self_linear = nn.Linear(hidden, hidden)
        self.context_linear = nn.Linear(hidden, hidden)
        self.norm = nn.LayerNorm(hidden)
        self.dropout = nn.Dropout(dropout)

    def forward(self, h: torch.Tensor, context: torch.Tensor) -> torch.Tensor:
        update = torch.nn.functional.silu(
            self.self_linear(h) + self.context_linear(context)
        )
        return self.norm(h + self.dropout(update))


class MeshResidualNet(nn.Module):
    def __init__(
        self,
        n_features: int,
        hidden: int,
        n_layers: int,
        dropout: float,
        use_graph: bool,
    ) -> None:
        super().__init__()
        self.use_graph = bool(use_graph)
        self.encoder = nn.Sequential(
            nn.Linear(n_features, hidden),
            nn.SiLU(),
            nn.LayerNorm(hidden),
        )
        self.layers = nn.ModuleList(
            ResidualLayer(hidden, dropout) for _ in range(int(n_layers))
        )
        self.output = nn.Linear(hidden, 1)

    @staticmethod
    def neighbour_mean(
        h: torch.Tensor, src: torch.Tensor, dst: torch.Tensor
    ) -> torch.Tensor:
        aggregate = torch.zeros_like(h)
        aggregate.index_add_(0, dst, h[src])
        degree = torch.zeros(h.shape[0], dtype=h.dtype, device=h.device)
        degree.index_add_(0, dst, torch.ones(dst.shape[0], dtype=h.dtype, device=h.device))
        return aggregate / degree.clamp_min(1.0).unsqueeze(1)

    def forward(self, sample: TensorSample) -> torch.Tensor:
        h = self.encoder(sample.features)
        for layer in self.layers:
            context = (
                self.neighbour_mean(h, sample.edge_src, sample.edge_dst)
                if self.use_graph
                else h
            )
            h = layer(h, context)
        return self.output(h).squeeze(-1)


def model_parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())


def weighted_huber(
    prediction: torch.Tensor,
    target: torch.Tensor,
    weights: torch.Tensor,
    valid: torch.Tensor,
    delta: float,
) -> torch.Tensor:
    error = prediction[valid] - target[valid]
    absolute = torch.abs(error)
    loss = torch.where(
        absolute <= delta,
        0.5 * error * error,
        delta * (absolute - 0.5 * delta),
    )
    selected_weights = weights[valid]
    return torch.sum(selected_weights * loss) / selected_weights.sum().clamp_min(EPS)


def predict_residual(
    model: MeshResidualNet,
    sample: TensorSample,
    scaler: FeatureScaler,
) -> np.ndarray:
    model.eval()
    with torch.no_grad():
        standardized = model(sample).detach().cpu().numpy()
    return standardized * scaler.target_std + scaler.target_mean


def validation_mae(
    model: MeshResidualNet,
    samples: Sequence[TensorSample],
    scaler: FeatureScaler,
) -> float:
    errors: list[float] = []
    for sample in samples:
        prediction = predict_residual(model, sample, scaler)
        target = sample.target.detach().cpu().numpy() * scaler.target_std + scaler.target_mean
        valid = sample.valid.detach().cpu().numpy()
        weights = sample.weights.detach().cpu().numpy()
        errors.append(weighted_mean(np.abs(target - prediction), weights, valid))
    return float(np.mean(errors))


def train_model(
    model: MeshResidualNet,
    train_samples: Sequence[TensorSample],
    val_samples: Sequence[TensorSample],
    scaler: FeatureScaler,
    epochs: int,
    learning_rate: float,
    weight_decay: float,
    huber_delta: float,
    patience: int,
    eval_every: int,
) -> tuple[MeshResidualNet, dict[str, float]]:
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=learning_rate, weight_decay=weight_decay
    )
    best_state = copy.deepcopy(model.state_dict())
    best_val = math.inf
    best_epoch = 0
    stale_evaluations = 0
    final_loss = math.nan

    for epoch in range(1, int(epochs) + 1):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        losses = [
            weighted_huber(
                model(sample),
                sample.target,
                sample.weights,
                sample.valid,
                huber_delta,
            )
            for sample in train_samples
        ]
        loss = torch.stack(losses).mean()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
        optimizer.step()
        final_loss = float(loss.detach().cpu())

        should_evaluate = epoch == 1 or epoch == epochs or epoch % eval_every == 0
        if should_evaluate:
            val = validation_mae(model, val_samples, scaler)
            if val < best_val - 1.0e-5:
                best_val = val
                best_epoch = epoch
                best_state = copy.deepcopy(model.state_dict())
                stale_evaluations = 0
            else:
                stale_evaluations += 1
            if stale_evaluations >= patience:
                break

    model.load_state_dict(best_state)
    return model, {
        "best_epoch": float(best_epoch),
        "best_val_log_mae": float(best_val),
        "last_train_loss": float(final_loss),
    }


def weighted_mean(values: np.ndarray, weights: np.ndarray, mask: np.ndarray) -> float:
    selected = mask & np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    if not np.any(selected):
        return float("nan")
    return float(np.sum(values[selected] * weights[selected]) / np.sum(weights[selected]))


def safe_masks(sample: CycleSample) -> dict[str, np.ndarray]:
    valid = sample.valid
    finite = sample.fem_raw[valid]
    p99 = float(np.percentile(finite, 99.0))
    return {
        "all_valid": valid,
        "fem_support_500": valid & (sample.fem_raw >= 500.0),
        "fem_top1_clean": valid & (sample.fem_raw >= max(p99, 500.0)),
        "fem_pz_1200": valid & (sample.fem_raw >= 1200.0),
        "fem_core_2400": valid & (sample.fem_raw >= 2400.0),
    }


def centroid(values: np.ndarray, area: np.ndarray, xy: np.ndarray, mask: np.ndarray) -> np.ndarray:
    selected = mask & np.isfinite(values) & (values > 0)
    if not np.any(selected):
        return np.array([np.nan, np.nan])
    weights = values[selected] * area[selected]
    return np.sum(xy[selected] * weights[:, None], axis=0) / np.sum(weights)


def jaccard(a: np.ndarray, b: np.ndarray) -> float:
    union = np.count_nonzero(a | b)
    return float(np.count_nonzero(a & b) / union) if union else float("nan")


def evaluate_prediction(
    sample: CycleSample,
    predicted_residual: np.ndarray,
    graph: CellGraph,
    seed: int,
    model_kind: str,
    split: str,
    training_info: dict[str, float],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    true_residual = sample.target
    corrected_log = raw_log(sample.pidl_raw) + predicted_residual
    corrected_raw = np.power(10.0, np.clip(corrected_log, -12.0, 12.0)) - EPS
    corrected_raw = np.maximum(corrected_raw, 0.0)
    rows: list[dict[str, object]] = []
    for mask_name, mask in safe_masks(sample).items():
        count = int(np.count_nonzero(mask))
        before = weighted_mean(np.abs(true_residual), sample.weights, mask)
        after = weighted_mean(
            np.abs(true_residual - predicted_residual), sample.weights, mask
        )
        rows.append(
            {
                "seed": seed,
                "model": model_kind,
                "split": split,
                "cycle": sample.cycle,
                "pidl_step": sample.pidl_step,
                "mask": mask_name,
                "n_cells": count,
                "log_mae_before": before,
                "log_mae_after": after,
                "relative_improvement": (
                    1.0 - after / before if count and np.isfinite(before) and before > 0 else np.nan
                ),
                **training_info,
            }
        )

    support_rows: list[dict[str, object]] = []
    for threshold in (500.0, 1200.0, 2400.0):
        fem_support = sample.valid & (sample.fem_raw >= threshold)
        pidl_support = sample.valid & (sample.pidl_raw >= threshold)
        corrected_support = sample.valid & (corrected_raw >= threshold)
        fem_count = int(np.count_nonzero(fem_support))
        fem_center = centroid(sample.fem_raw, graph.area, graph.centroids, fem_support)
        for source, values, support in (
            ("pidl", sample.pidl_raw, pidl_support),
            ("corrected", corrected_raw, corrected_support),
        ):
            source_center = centroid(values, graph.area, graph.centroids, support)
            support_rows.append(
                {
                    "seed": seed,
                    "model": model_kind,
                    "split": split,
                    "cycle": sample.cycle,
                    "pidl_step": sample.pidl_step,
                    "threshold": threshold,
                    "source": source,
                    "fem_support_cells": fem_count,
                    "source_support_cells": int(np.count_nonzero(support)),
                    "fem_coverage": (
                        float(np.count_nonzero(fem_support & support) / fem_count)
                        if fem_count
                        else np.nan
                    ),
                    "jaccard": jaccard(fem_support, support),
                    "centroid_distance": float(np.linalg.norm(source_center - fem_center)),
                }
            )
    return rows, support_rows


def write_csv(path: Path, rows: Sequence[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def aggregate_seed_metrics(rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[object, ...], list[dict[str, object]]] = {}
    keys = ("model", "split", "cycle", "pidl_step", "mask")
    for row in rows:
        groups.setdefault(tuple(row[key] for key in keys), []).append(row)
    output: list[dict[str, object]] = []
    for group_key, group in sorted(groups.items(), key=lambda item: str(item[0])):
        record = dict(zip(keys, group_key))
        record["n_seeds"] = len(group)
        for metric in ("log_mae_before", "log_mae_after", "relative_improvement"):
            values = np.asarray([float(row[metric]) for row in group], dtype=float)
            record[f"{metric}_mean"] = float(np.nanmean(values))
            record[f"{metric}_std"] = float(np.nanstd(values))
        output.append(record)
    return output


def graph_advantage_rows(rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    lookup = {
        (row["seed"], row["split"], row["cycle"], row["mask"], row["model"]): row
        for row in rows
    }
    output: list[dict[str, object]] = []
    base_keys = sorted(
        {(row["seed"], row["split"], row["cycle"], row["mask"]) for row in rows},
        key=str,
    )
    for seed, split, cycle, mask in base_keys:
        graph = lookup.get((seed, split, cycle, mask, "graph"))
        mlp = lookup.get((seed, split, cycle, mask, "mlp"))
        if graph is None or mlp is None:
            continue
        output.append(
            {
                "seed": seed,
                "split": split,
                "cycle": cycle,
                "mask": mask,
                "mlp_log_mae_after": mlp["log_mae_after"],
                "graph_log_mae_after": graph["log_mae_after"],
                "graph_advantage": float(mlp["log_mae_after"])
                - float(graph["log_mae_after"]),
            }
        )
    return output


def plot_test_fields(
    path: Path,
    sample: CycleSample,
    graph: CellGraph,
    predictions: dict[str, list[np.ndarray]],
) -> None:
    panels: list[tuple[str, np.ndarray]] = [
        ("FEM peak raw", raw_log(sample.fem_raw)),
        ("PIDL peak raw", raw_log(sample.pidl_raw)),
    ]
    for model_kind in ("mlp", "graph"):
        if predictions.get(model_kind):
            mean_residual = np.mean(predictions[model_kind], axis=0)
            panels.append(
                (
                    f"{model_kind.upper()} corrected",
                    raw_log(sample.pidl_raw) + mean_residual,
                )
            )
    if predictions.get("graph") and predictions.get("mlp"):
        graph_residual = np.mean(predictions["graph"], axis=0)
        mlp_residual = np.mean(predictions["mlp"], axis=0)
        panels.append(("Graph - MLP correction", graph_residual - mlp_residual))

    fig, axes = plt.subplots(1, len(panels), figsize=(3.3 * len(panels), 3.0), constrained_layout=True)
    axes = np.atleast_1d(axes)
    common = np.concatenate([values[sample.valid] for _, values in panels[:-1]])
    vmin, vmax = np.percentile(common[np.isfinite(common)], [1.0, 99.5])
    for index, (axis, (title, values)) in enumerate(zip(axes, panels)):
        if index == len(panels) - 1 and "Graph - MLP" in title:
            limit = max(float(np.nanpercentile(np.abs(values[sample.valid]), 99.0)), EPS)
            image = axis.scatter(
                graph.centroids[:, 0], graph.centroids[:, 1], c=values,
                s=1.0, cmap="RdBu_r", vmin=-limit, vmax=limit, rasterized=True,
            )
        else:
            image = axis.scatter(
                graph.centroids[:, 0], graph.centroids[:, 1], c=values,
                s=1.0, cmap="magma", vmin=vmin, vmax=vmax, rasterized=True,
            )
        axis.set_title(title, fontsize=9)
        axis.set_aspect("equal")
        axis.set_xticks([])
        axis.set_yticks([])
        fig.colorbar(image, ax=axis, fraction=0.046, pad=0.02)
    fig.suptitle(f"Hard-recovery c{sample.cycle} peak raw-driver discriminator", fontsize=10)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pidl-diag-dir", type=Path, default=DEFAULT_PIDL_DIAG)
    parser.add_argument("--fem-psi-dir", type=Path, default=DEFAULT_FEM_ROOT / "psi_fields")
    parser.add_argument("--fem-vtk", type=Path, default=DEFAULT_FEM_ROOT / "fields_000001_008.vtk")
    parser.add_argument("--projection-map", type=Path, default=DEFAULT_PROJECTION)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--train-cycles", default="20,40,60")
    parser.add_argument("--val-cycles", default="69")
    parser.add_argument("--test-cycles", default="89")
    parser.add_argument("--seeds", default="1,7,19")
    parser.add_argument("--models", default="mlp,graph")
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--layers", type=int, default=3)
    parser.add_argument("--dropout", type=float, default=0.05)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--learning-rate", type=float, default=1.0e-3)
    parser.add_argument("--weight-decay", type=float, default=1.0e-4)
    parser.add_argument("--huber-delta", type=float, default=1.0)
    parser.add_argument("--patience", type=int, default=12)
    parser.add_argument("--eval-every", type=int, default=5)
    parser.add_argument("--focus-weight", type=float, default=4.0)
    parser.add_argument("--residual-clip", type=float, default=8.0)
    parser.add_argument("--cycle-scale", type=float, default=100.0)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--dry-run", action="store_true", help="Load and validate assets without fitting models.")
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args()

    train_cycles = parse_ints(args.train_cycles)
    val_cycles = parse_ints(args.val_cycles)
    test_cycles = parse_ints(args.test_cycles)
    if not train_cycles or not val_cycles or not test_cycles:
        raise ValueError("train, validation, and test cycles must all be non-empty")
    overlap = (set(train_cycles) & set(val_cycles)) | (set(train_cycles) & set(test_cycles)) | (set(val_cycles) & set(test_cycles))
    if overlap:
        raise ValueError(f"cycle split leakage: {sorted(overlap)}")
    models = [item.strip() for item in args.models.split(",") if item.strip()]
    if any(model not in {"mlp", "graph"} for model in models):
        raise ValueError("models must be a subset of mlp,graph")
    seeds = parse_ints(args.seeds)
    if not seeds:
        raise ValueError("at least one seed is required")

    graph = load_cell_graph(args.fem_vtk)
    projection = load_projection_map(args.projection_map, graph.cells.shape[0])
    all_cycles = train_cycles + val_cycles + test_cycles
    samples: dict[int, CycleSample] = {}
    feature_names: list[str] | None = None
    for cycle in all_cycles:
        sample, current_names = build_cycle_sample(
            cycle=cycle,
            graph=graph,
            projection=projection,
            pidl_diag_dir=args.pidl_diag_dir,
            fem_psi_dir=args.fem_psi_dir,
            cycle_scale=args.cycle_scale,
            residual_clip=args.residual_clip,
            focus_weight=args.focus_weight,
        )
        if feature_names is None:
            feature_names = current_names
        elif feature_names != current_names:
            raise RuntimeError("feature schema changed between cycles")
        samples[cycle] = sample

    scaler = fit_scaler([samples[cycle] for cycle in train_cycles])
    apply_scaler(samples.values(), scaler)
    out_dir = args.out_dir
    (out_dir / "tables").mkdir(parents=True, exist_ok=True)
    (out_dir / "figures").mkdir(parents=True, exist_ok=True)
    manifest = {
        "claim_class": "field-mechanism diagnostic",
        "target_semantics": "FEM cycle-peak raw psi minus PIDL cycle-peak raw psi in log10 space",
        "forbidden_interpretation": "No FEM active-driver target and no claim of online mechanism closure",
        "train_cycles": train_cycles,
        "val_cycles": val_cycles,
        "test_cycles": test_cycles,
        "cycle_to_pidl_peak_step": {str(cycle): hard_recovery_peak_step(cycle) for cycle in all_cycles},
        "features": feature_names,
        "n_fem_cells": int(graph.cells.shape[0]),
        "n_directed_dual_edges": int(graph.src.size),
        "projection_coverage_fraction": float(np.mean(projection.denominator > 0)),
        "model_config": {
            "hidden": args.hidden,
            "layers": args.layers,
            "dropout": args.dropout,
            "epochs": args.epochs,
            "seeds": seeds,
            "models": models,
        },
        "inputs": {
            "pidl_diag_dir": str(args.pidl_diag_dir),
            "fem_psi_dir": str(args.fem_psi_dir),
            "fem_vtk": str(args.fem_vtk),
            "projection_map": str(args.projection_map),
        },
        "input_checksums_sha256": {
            "runner": sha256_file(Path(__file__).resolve()),
            "fem_vtk": sha256_file(args.fem_vtk),
            "projection_map": sha256_file(args.projection_map),
            "pidl_peak_npz": {
                str(cycle): sha256_file(
                    args.pidl_diag_dir
                    / f"element_fields_cycle_{hard_recovery_peak_step(cycle):04d}.npz"
                )
                for cycle in all_cycles
            },
            "fem_peak_raw_mat": {
                str(cycle): sha256_file(args.fem_psi_dir / f"cycle_{cycle:04d}.mat")
                for cycle in all_cycles
            },
        },
        "git": git_provenance(REPO),
        "runtime": {
            "python": sys.version,
            "numpy": np.__version__,
            "torch": torch.__version__,
            "meshio": meshio.__version__,
        },
    }
    with (out_dir / "analysis_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    if args.dry_run:
        print(json.dumps(manifest, indent=2))
        return 0

    device = torch.device(args.device)
    tensor_samples = {
        cycle: to_tensor_sample(sample, graph, scaler, device)
        for cycle, sample in samples.items()
    }
    metric_rows: list[dict[str, object]] = []
    support_rows: list[dict[str, object]] = []
    test_predictions: dict[int, dict[str, list[np.ndarray]]] = {
        cycle: {"mlp": [], "graph": []} for cycle in test_cycles
    }

    for seed in seeds:
        for model_kind in models:
            # Paired initialization keeps graph-vs-MLP differences attributable
            # to neighbourhood aggregation rather than a different random draw.
            torch.manual_seed(seed)
            np.random.seed(seed)
            model = MeshResidualNet(
                n_features=len(feature_names or []),
                hidden=args.hidden,
                n_layers=args.layers,
                dropout=args.dropout,
                use_graph=(model_kind == "graph"),
            ).to(device)
            model, training_info = train_model(
                model=model,
                train_samples=[tensor_samples[cycle] for cycle in train_cycles],
                val_samples=[tensor_samples[cycle] for cycle in val_cycles],
                scaler=scaler,
                epochs=args.epochs,
                learning_rate=args.learning_rate,
                weight_decay=args.weight_decay,
                huber_delta=args.huber_delta,
                patience=args.patience,
                eval_every=args.eval_every,
            )
            training_info["parameter_count"] = float(model_parameter_count(model))
            for split, cycles in (
                ("train", train_cycles),
                ("validation", val_cycles),
                ("test", test_cycles),
            ):
                for cycle in cycles:
                    prediction = predict_residual(model, tensor_samples[cycle], scaler)
                    rows, supports = evaluate_prediction(
                        sample=samples[cycle],
                        predicted_residual=prediction,
                        graph=graph,
                        seed=seed,
                        model_kind=model_kind,
                        split=split,
                        training_info=training_info,
                    )
                    metric_rows.extend(rows)
                    support_rows.extend(supports)
                    if split == "test":
                        test_predictions[cycle][model_kind].append(prediction)

    write_csv(out_dir / "tables" / "seed_metrics.csv", metric_rows)
    write_csv(out_dir / "tables" / "support_metrics.csv", support_rows)
    write_csv(out_dir / "tables" / "aggregate_metrics.csv", aggregate_seed_metrics(metric_rows))
    write_csv(out_dir / "tables" / "graph_advantage_by_seed.csv", graph_advantage_rows(metric_rows))

    if not args.no_plot:
        for cycle in test_cycles:
            plot_test_fields(
                out_dir / "figures" / f"c{cycle}_graph_vs_mlp.pdf",
                samples[cycle],
                graph,
                test_predictions[cycle],
            )
            plot_test_fields(
                out_dir / "figures" / f"c{cycle}_graph_vs_mlp.png",
                samples[cycle],
                graph,
                test_predictions[cycle],
            )

    test_rows = [
        row for row in metric_rows if row["split"] == "test" and row["mask"] in {"all_valid", "fem_top1_clean", "fem_pz_1200", "fem_core_2400"}
    ]
    for row in test_rows:
        print(
            f"seed={row['seed']} model={row['model']} c{row['cycle']} "
            f"mask={row['mask']} logMAE={float(row['log_mae_after']):.4g} "
            f"improve={float(row['relative_improvement']):.2%}"
        )
    print(f"wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
