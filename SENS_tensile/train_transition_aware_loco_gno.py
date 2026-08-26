#!/usr/bin/env python3
"""Train one frozen data-only transition-aware GNO Hard-5 LOAO fold/seed.

Training is disabled on Mac.  This runner uses only archived FEM field and
transition labels from the two training amplitudes; it contains no physics
residual and never reads the held-out first-hit cycle during optimization.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import random
import re
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from fem_mechanism_operator import (  # noqa: E402
    StateStatistics,
    apply_state_constraints,
    derived_active_log10,
)
from train_fem_mechanism_mesh_operator import field_metrics  # noqa: E402
from transition_aware_mesh_operator import (  # noqa: E402
    TransitionAwareMeshOperator,
    normalized_field_loss,
    supervised_transition_loss,
)


CONTEXT = 3
ROLLOUT = 3
EXPECTED_DATASET_ID = "hard5_loao_fem_states_v1"
EXPECTED_MANIFEST_SHA256 = (
    "9267a102a38375ebc815404a5ae81b2d3b23622448b5b178a2c4c1a5696e202a"
)
EXPECTED_HASH_FILE_SHA256 = (
    "7bff035eaa618a7517335a3adb436e14d8bf606c6fa4e202497355518e82a55e"
)
EXPECTED_PARAMETER_COUNT = 339_461
EXPECTED_FILES = {
    "RUN_MANIFEST.json": EXPECTED_MANIFEST_SHA256,
    "graph.npz": "bd5b731daeb0718368309cd50c44fa7422e49096b495f619eba429d1c6bde419",
    "trajectories/hard5_u011.npz": "367b851a1814734d5e122f91477826850375149a108476ef6fab44245cfbe878",
    "trajectories/hard5_u012.npz": "e80b32675876444888b7d50d3df1f250009770d6b8b45d5dc1f3992197ebbe95",
    "trajectories/hard5_u013.npz": "c91287af619de1dd2ed8b07da680f7d1bc0d06d500441e23887fd031077b253b",
    "pidl_matches/hard5_u011.npz": "2b8c98a0b3854c716e3018c1f3ced8c91f8ef74788fa83477b96a5fa8753f9f0",
    "pidl_matches/hard5_u012.npz": "1860972b3fca6a44db0158aabf1d8df5719c2d620f0b3b35c61a85d9da7769d5",
    "pidl_matches/hard5_u013.npz": "727b4152548d40a8d9e37db8cf6940d439887abee39438a83f0453831fb29662",
}
EXPECTED_TRAJECTORY_IDS = frozenset(
    path.removeprefix("trajectories/").removesuffix(".npz")
    for path in EXPECTED_FILES
    if path.startswith("trajectories/")
)
MATRIX_LOCK_PATH = (
    HERE.parent
    / "docs"
    / "experiments"
    / "hard5_loao_gno_matrix_lock_20260826.json"
)


def locked_code_paths() -> dict[str, Path]:
    repo = HERE.parent
    return {
        "runner": Path(__file__).resolve(),
        "model": repo / "source" / "transition_aware_mesh_operator.py",
        "operator_dependency": repo / "source" / "fem_mechanism_operator.py",
        "metric_dependency": repo
        / "SENS_tensile"
        / "train_fem_mechanism_mesh_operator.py",
        "tests": repo / "tests" / "test_transition_aware_loco_gno.py",
        "dataset_builder": repo
        / "SENS_tensile"
        / "prepare_hard5_loao_gno_dataset.py",
        "aggregate_analyzer": repo
        / "SENS_tensile"
        / "analyze_hard5_loao_gno_matrix.py",
        "aggregate_tests": repo
        / "tests"
        / "test_analyze_hard5_loao_gno_matrix.py",
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_hash_manifest(root: Path) -> None:
    path = root / "HASHES.sha256"
    if not path.is_file():
        raise FileNotFoundError(path)
    if sha256_file(path) != EXPECTED_HASH_FILE_SHA256:
        raise ValueError("HASHES.sha256 does not match the frozen D1 lock")
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split(maxsplit=1)
        relative = relative.strip().lstrip("*")
        if relative in entries:
            raise ValueError(f"duplicate dataset hash entry: {relative}")
        entries[relative] = expected
        target = root / relative
        if not target.is_file() or sha256_file(target) != expected:
            raise ValueError(f"dataset hash mismatch: {relative}")
    if entries != EXPECTED_FILES:
        raise ValueError("dataset file set or frozen file hashes changed")


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def clip_finite_gradients(parameters, max_norm: float = 5.0) -> float:
    norm = torch.nn.utils.clip_grad_norm_(parameters, max_norm, error_if_nonfinite=True)
    return float(norm.detach().cpu())


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty table: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_json_atomic(path: Path, payload: dict) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        write_json(temporary, payload)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def trajectory_metadata(trajectory_id: str, umax: float, device: torch.device) -> torch.Tensor:
    expected_umax = {"hard5_u011": 0.11, "hard5_u012": 0.12, "hard5_u013": 0.13}
    if trajectory_id not in expected_umax or not np.isclose(
        umax, expected_umax[trajectory_id], rtol=0.0, atol=1.0e-8
    ):
        raise ValueError(f"cannot decode Hard-5 amplitude metadata from {trajectory_id}")
    design_scaled_umax = (expected_umax[trajectory_id] - 0.12) / 0.01
    return torch.tensor(
        [1.0, 0.0, 1.0, design_scaled_umax],
        dtype=torch.float32,
        device=device,
    )


def load_graph(
    path: Path, device: torch.device
) -> tuple[dict[str, torch.Tensor], dict[str, np.ndarray]]:
    data = np.load(path, allow_pickle=False)
    names = (
        "coordinates",
        "centroids",
        "log_area",
        "areas",
        "edge_index",
        "edge_attr",
        "cluster_index",
        "coarse_edge_index",
        "coarse_edge_attr",
    )
    arrays = {name: np.asarray(data[name]) for name in names}
    graph = {name: torch.from_numpy(value).to(device) for name, value in arrays.items()}
    for name in ("edge_index", "cluster_index", "coarse_edge_index"):
        graph[name] = graph[name].long()
    return graph, arrays


def load_trajectory(path: Path, device: torch.device) -> dict:
    data = np.load(path, allow_pickle=False)
    trajectory_id = str(np.asarray(data["trajectory_id"]).item())
    umax = float(np.asarray(data["umax"]).item())
    cycles = np.asarray(data["cycles"], dtype=int)
    if not np.array_equal(cycles, np.arange(1, len(cycles) + 1)):
        raise ValueError(f"nonconsecutive cycles in {path}")
    return {
        "trajectory_id": trajectory_id,
        "states": torch.from_numpy(np.asarray(data["states"], dtype=np.float32)).to(
            device
        ),
        "first_hit": int(np.asarray(data["first_hit_cycle"]).item()),
        "confirmed": int(np.asarray(data["confirmed_cycle"]).item()),
        "umax": umax,
        "metadata": trajectory_metadata(trajectory_id, umax, device),
    }


def load_dataset(
    root: Path, heldout_id: str, device: torch.device
) -> tuple[list[dict], dict, dict[str, torch.Tensor], dict[str, np.ndarray], dict]:
    verify_hash_manifest(root)
    manifest = json.loads((root / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
    if (
        manifest.get("dataset_id") != EXPECTED_DATASET_ID
        or manifest.get("trajectory_count") != 3
    ):
        raise ValueError("unexpected dataset identity or trajectory count")
    rows = manifest.get("trajectories", [])
    manifest_ids = [row["trajectory_id"] for row in rows]
    if (
        len(manifest_ids) != len(set(manifest_ids))
        or set(manifest_ids) != EXPECTED_TRAJECTORY_IDS
    ):
        raise ValueError("trajectory IDs do not match the frozen three-amplitude split")
    paths: dict[str, Path] = {}
    for row in rows:
        expected_file = f"{row['trajectory_id']}.npz"
        if row["data_file"] != expected_file:
            raise ValueError(f"trajectory filename/ID mismatch: {row['trajectory_id']}")
        if row.get("data_sha256") != EXPECTED_FILES[f"trajectories/{expected_file}"]:
            raise ValueError(
                f"trajectory manifest hash mismatch: {row['trajectory_id']}"
            )
        paths[row["trajectory_id"]] = root / "trajectories" / expected_file
    if heldout_id not in paths:
        raise ValueError(f"heldout trajectory not found: {heldout_id}")
    graph, graph_arrays = load_graph(root / manifest["graph_file"], device)
    loaded = {key: load_trajectory(path, device) for key, path in paths.items()}
    for key, item in loaded.items():
        if item["trajectory_id"] != key:
            raise ValueError(f"NPZ internal trajectory ID mismatch: {key}")
        row = next(candidate for candidate in rows if candidate["trajectory_id"] == key)
        if (
            item["first_hit"] != row["first_hit_cycle"]
            or item["confirmed"] != row["confirmed_cycle"]
        ):
            raise ValueError(f"event metadata mismatch: {key}")
    heldout = loaded.pop(heldout_id)
    training = [loaded[key] for key in sorted(loaded)]
    if heldout_id in {item["trajectory_id"] for item in training}:
        raise AssertionError("heldout trajectory leaked into training")
    return training, heldout, graph, graph_arrays, manifest


def training_statistics(items: list[dict], device: torch.device) -> StateStatistics:
    def equal_trajectory_moments(arrays: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
        means = np.stack([array.mean(axis=(0, 1)) for array in arrays])
        second_moments = np.stack([(array * array).mean(axis=(0, 1)) for array in arrays])
        mean = means.mean(axis=0)
        variance = np.maximum(second_moments.mean(axis=0) - mean * mean, 0.0)
        return mean, np.maximum(np.sqrt(variance), 1.0e-6)

    prehit_states = []
    prehit_residuals = []
    for item in items:
        states = item["states"][: item["first_hit"] - 1].cpu().numpy().astype(np.float64)
        if len(states) < 2:
            raise ValueError("training trajectory needs at least two pre-hit states")
        prehit_states.append(states)
        prehit_residuals.append(np.diff(states, axis=0))
    state_mean, state_std = equal_trajectory_moments(prehit_states)
    residual_mean, residual_std = equal_trajectory_moments(prehit_residuals)
    arrays = (state_mean, state_std, residual_mean, residual_std)
    return StateStatistics(
        *(
            torch.tensor(array, dtype=torch.float32, device=device).reshape(1, -1)
            for array in arrays
        )
    )


def training_active_residual_scale(
    items: list[dict], device: torch.device
) -> torch.Tensor:
    """Trajectory-equal pre-hit scale for one-cycle active-log changes."""
    means = []
    second_moments = []
    for item in items:
        states = item["states"][: item["first_hit"] - 1]
        active = derived_active_log10(states.reshape(-1, 4)).reshape(states.shape[:2])
        changes = (active[1:] - active[:-1]).reshape(-1).double()
        means.append(changes.mean())
        second_moments.append((changes * changes).mean())
    mean = torch.stack(means).mean()
    variance = (torch.stack(second_moments).mean() - mean * mean).clamp_min(0.0)
    scale = torch.sqrt(variance).clamp_min(1.0e-6)
    return scale.to(device)


@dataclass(frozen=True)
class Window:
    trajectory_index: int
    origin_cycle: int
    contains_transition: bool


@dataclass(frozen=True)
class BucketCalibration:
    gradient_scales: dict[str, torch.Tensor]
    raw_loss_means: dict[str, torch.Tensor]
    raw_gradient_means: dict[str, torch.Tensor]
    normalized_gradient_means: dict[str, float]


def build_training_windows(
    items: list[dict], context: int = CONTEXT, rollout: int = ROLLOUT
) -> tuple[list[Window], list[Window]]:
    positive: list[Window] = []
    negative: list[Window] = []
    for item_index, item in enumerate(items):
        stop = min(item["first_hit"], len(item["states"]) - rollout + 1)
        for origin in range(context, stop):
            targets = range(origin + 1, origin + rollout + 1)
            window = Window(
                trajectory_index=item_index,
                origin_cycle=origin,
                contains_transition=any(
                    cycle >= item["first_hit"] for cycle in targets
                ),
            )
            (positive if window.contains_transition else negative).append(window)
    if not positive or not negative:
        raise ValueError("training split needs both transition and ordinary windows")
    return positive, negative


def choose_balanced_window(
    positive: list[Window], negative: list[Window], step: int, rng: random.Random
) -> Window:
    """Alternate buckets, then sample trajectories equally, then an origin."""
    bucket = positive if step % 2 else negative
    trajectory_indices = sorted({window.trajectory_index for window in bucket})
    trajectory_index = rng.choice(trajectory_indices)
    trajectory_windows = [
        window for window in bucket if window.trajectory_index == trajectory_index
    ]
    return rng.choice(trajectory_windows)


def calibrate_bucket_gradient_scales(
    items: list[dict],
    positive: list[Window],
    negative: list[Window],
    graph: dict[str, torch.Tensor],
    statistics: StateStatistics,
    active_residual_scale: torch.Tensor,
) -> BucketCalibration:
    """Equalize persistence prediction-gradient norms across training buckets."""
    area = graph["areas"].reshape(-1)
    loss_means: dict[str, torch.Tensor] = {}
    gradient_means: dict[str, torch.Tensor] = {}
    for name, windows in (("transition", positive), ("ordinary", negative)):
        trajectory_losses = []
        trajectory_gradients = []
        for trajectory_index in sorted({window.trajectory_index for window in windows}):
            losses = []
            gradient_norms = []
            for window in (
                candidate
                for candidate in windows
                if candidate.trajectory_index == trajectory_index
            ):
                item = items[window.trajectory_index]
                prediction = (
                    item["states"][window.origin_cycle - 1]
                    .detach()
                    .clone()
                    .requires_grad_(True)
                )
                per_target = []
                for target_cycle in range(
                    window.origin_cycle + 1, window.origin_cycle + ROLLOUT + 1
                ):
                    loss = normalized_field_loss(
                        prediction,
                        item["states"][target_cycle - 1],
                        area,
                        graph["edge_index"],
                        statistics,
                        active_residual_scale,
                    )
                    per_target.append(loss.total)
                window_loss = torch.stack(per_target).mean()
                (gradient,) = torch.autograd.grad(window_loss, prediction)
                losses.append(window_loss.detach())
                gradient_norms.append(torch.linalg.vector_norm(gradient).detach())
            trajectory_losses.append(torch.stack(losses).mean())
            trajectory_gradients.append(torch.stack(gradient_norms).mean())
        loss_means[name] = torch.stack(trajectory_losses).mean()
        gradient_means[name] = torch.stack(trajectory_gradients).mean().clamp_min(1.0e-8)
    normalized = {
        name: float((gradient_means[name] / gradient_means[name]).cpu())
        for name in gradient_means
    }
    if not all(
        np.isfinite(value) and 0.99 <= value <= 1.01 for value in normalized.values()
    ):
        raise ValueError("invalid training-fold gradient calibration")
    return BucketCalibration(
        gradient_scales=gradient_means,
        raw_loss_means=loss_means,
        raw_gradient_means=gradient_means,
        normalized_gradient_means=normalized,
    )


def transition_target(
    target_cycle: int, first_hit: int, device: torch.device
) -> torch.Tensor:
    return torch.tensor(float(target_cycle >= first_hit), device=device)


def predict_rollout(
    model: TransitionAwareMeshOperator,
    item: dict,
    origin: int,
    horizon: int,
    graph: dict[str, torch.Tensor],
    statistics: StateStatistics,
) -> tuple[dict[int, torch.Tensor], dict[int, torch.Tensor]]:
    history = [state for state in item["states"][origin - CONTEXT : origin]]
    predictions: dict[int, torch.Tensor] = {}
    logits: dict[int, torch.Tensor] = {}
    model.eval()
    with torch.no_grad():
        for cycle in range(origin + 1, origin + horizon + 1):
            prediction, logit = model(
                torch.stack(history[-CONTEXT:]), graph, statistics, item["metadata"]
            )
            predictions[cycle] = prediction
            logits[cycle] = logit
            history.append(prediction)
    return predictions, logits


def baseline_rollout(
    item: dict,
    origin: int,
    horizon: int,
    statistics: StateStatistics,
    method: str,
) -> dict[int, torch.Tensor]:
    """Frozen observation-only persistence or constrained-linear rollout."""
    if method not in {"persistence", "constrained_linear"}:
        raise ValueError(f"unknown primary baseline: {method}")
    previous = item["states"][origin - 2]
    current = item["states"][origin - 1]
    predictions: dict[int, torch.Tensor] = {}
    for cycle in range(origin + 1, origin + horizon + 1):
        if method == "persistence":
            prediction = current.clone()
        else:
            physical_residual = current - previous
            normalized_residual = (
                physical_residual - statistics.residual_mean
            ) / statistics.residual_std
            prediction = apply_state_constraints(
                current, normalized_residual, statistics
            )
        predictions[cycle] = prediction
        previous, current = current, prediction
    return predictions


def fold_role(trajectory_id: str) -> str:
    roles = {
        "hard5_u011": "endpoint_extrapolation_secondary",
        "hard5_u012": "interpolation_primary",
        "hard5_u013": "endpoint_extrapolation_secondary",
    }
    try:
        return roles[trajectory_id]
    except KeyError as exc:
        raise ValueError(f"unknown Hard5 fold: {trajectory_id}") from exc


def event_hit(state: np.ndarray, centroids: np.ndarray) -> bool:
    return int(np.count_nonzero((centroids[:, 0] >= 0.48) & (state[:, 0] >= 0.95))) >= 3


def classification_summary(rows: list[dict]) -> dict[str, float | int | bool | None]:
    truth = np.asarray([row["truth_transition"] for row in rows], dtype=int)
    predicted = np.asarray([row["predicted_transition"] for row in rows], dtype=int)
    probability = np.asarray(
        [row["predicted_transition_probability"] for row in rows], dtype=float
    )
    tp = int(np.count_nonzero((truth == 1) & (predicted == 1)))
    tn = int(np.count_nonzero((truth == 0) & (predicted == 0)))
    fp = int(np.count_nonzero((truth == 0) & (predicted == 1)))
    fn = int(np.count_nonzero((truth == 1) & (predicted == 0)))
    bins = np.minimum((probability * 10).astype(int), 9)
    ece: float | None = 0.0 if len(rows) else None
    for index in range(10):
        mask = bins == index
        if np.any(mask):
            assert ece is not None
            ece += float(mask.mean()) * abs(
                float(probability[mask].mean() - truth[mask].mean())
            )
    precision_valid = tp + fp > 0
    recall_valid = tp + fn > 0
    fpr_valid = fp + tn > 0
    return {
        "evaluated_rows": len(rows),
        "positive_rows": int(truth.sum()),
        "negative_rows": int((1 - truth).sum()),
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "recall": tp / (tp + fn) if recall_valid else None,
        "recall_denominator": tp + fn,
        "recall_valid": recall_valid,
        "precision": tp / (tp + fp) if precision_valid else None,
        "precision_denominator": tp + fp,
        "precision_valid": precision_valid,
        "false_positive_rate": fp / (fp + tn) if fpr_valid else None,
        "false_positive_rate_denominator": fp + tn,
        "false_positive_rate_valid": fpr_valid,
        "brier_score": float(np.mean((probability - truth) ** 2))
        if len(rows)
        else None,
        "ece_10_bin": ece,
        "ece_10_bin_valid": bool(rows),
        "threshold": 0.5,
    }


def pre_event_forecast_opportunities_evaluation(
    model: TransitionAwareMeshOperator,
    heldout: dict,
    graph: dict[str, torch.Tensor],
    statistics: StateStatistics,
    out: Path,
) -> None:
    """Score all legal pre-hit origins without held-out model selection."""
    rows: list[dict] = []
    for origin in range(CONTEXT, heldout["first_hit"]):
        horizon = min(ROLLOUT, len(heldout["states"]) - origin)
        predictions, logits = predict_rollout(
            model, heldout, origin, horizon, graph, statistics
        )
        for cycle in predictions:
            probability = float(torch.sigmoid(logits[cycle]).cpu())
            truth = int(cycle >= heldout["first_hit"])
            rows.append(
                {
                    "trajectory_id": heldout["trajectory_id"],
                    "origin_cycle": origin,
                    "target_cycle": cycle,
                    "horizon": cycle - origin,
                    "event_distance_posthoc": cycle - heldout["first_hit"],
                    "truth_transition": truth,
                    "predicted_transition_probability": probability,
                    "predicted_transition": int(probability >= 0.5),
                }
            )
    if any(row["origin_cycle"] >= heldout["first_hit"] for row in rows):
        raise AssertionError("post-hit origin entered pre-event evaluation")
    write_csv(out / "pre_event_forecast_opportunities_metrics.csv", rows)
    report = {
        "distribution_unit": "overlapping_pre_event_origin_horizon_opportunity",
        "overall": classification_summary(rows),
        "by_horizon": {
            f"h{horizon}": classification_summary(
                [row for row in rows if row["horizon"] == horizon]
            )
            for horizon in range(1, ROLLOUT + 1)
        },
        "unique_cycle_h1": classification_summary(
            [row for row in rows if row["horizon"] == 1]
        ),
        "used_for_model_selection": False,
        "threshold_tuned_on_heldout": False,
    }
    write_json(out / "pre_event_forecast_opportunities_summary.json", report)


def evaluate(
    model: TransitionAwareMeshOperator,
    heldout: dict,
    graph: dict[str, torch.Tensor],
    graph_arrays: dict[str, np.ndarray],
    statistics: StateStatistics,
    out: Path,
) -> None:
    areas = np.asarray(graph_arrays["areas"], dtype=np.float64)
    centroids = np.asarray(graph_arrays["centroids"], dtype=np.float64)
    rows: list[dict] = []
    warning_rows: list[dict] = []
    assets: dict[str, np.ndarray] = {}
    for origin in range(heldout["first_hit"] - 3, heldout["first_hit"]):
        horizon = min(3, len(heldout["states"]) - origin)
        predictions, logits = predict_rollout(
            model, heldout, origin, horizon, graph, statistics
        )
        baseline_predictions = {
            method: baseline_rollout(heldout, origin, horizon, statistics, method)
            for method in ("persistence", "constrained_linear")
        }
        for cycle, prediction in predictions.items():
            prediction_array = prediction.cpu().numpy()
            target_array = heldout["states"][cycle - 1].cpu().numpy()
            method_predictions = {
                "gno_data": prediction_array,
                **{
                    method: values[cycle].cpu().numpy()
                    for method, values in baseline_predictions.items()
                },
            }
            for method, method_prediction in method_predictions.items():
                rows.append(
                    {
                        "trajectory_id": heldout["trajectory_id"],
                        "fold_role": fold_role(heldout["trajectory_id"]),
                        "evaluation_role": "primary_event_centred",
                        "mapping_domain": "native_full_mesh",
                        "method": method,
                        "origin_cycle": origin,
                        "target_cycle": cycle,
                        "horizon": cycle - origin,
                        **field_metrics(method_prediction, target_array, areas),
                    }
                )
            probability = float(torch.sigmoid(logits[cycle]).cpu())
            truth = int(cycle >= heldout["first_hit"])
            warning_rows.append(
                {
                    "trajectory_id": heldout["trajectory_id"],
                    "fold_role": fold_role(heldout["trajectory_id"]),
                    "evaluation_role": "primary_transition",
                    "method": "gno_data",
                    "origin_cycle": origin,
                    "target_cycle": cycle,
                    "horizon": cycle - origin,
                    "truth_transition": truth,
                    "predicted_transition_probability": probability,
                    "predicted_transition": int(probability >= 0.5),
                    "predicted_field_hit": int(event_hit(prediction_array, centroids)),
                }
            )
            key = f"origin_c{origin}__target_c{cycle}"
            assets[f"{key}__prediction"] = prediction_array
            for method, values in baseline_predictions.items():
                assets[f"{key}__{method}"] = values[cycle].cpu().numpy()
            assets[f"{key}__fem"] = target_array
            assets[f"{key}__transition_logit"] = np.asarray(float(logits[cycle].cpu()))
            assets[f"{key}__transition_probability"] = np.asarray(probability)
        assets[f"origin_c{origin}__context"] = (
            heldout["states"][origin - CONTEXT : origin].cpu().numpy()
        )
    write_csv(out / "fem_centred_metrics.csv", rows)
    if (
        len(rows) != 27
        or {row["method"] for row in rows}
        != {"gno_data", "persistence", "constrained_linear"}
    ):
        raise AssertionError("event-centred primary field population is incomplete")
    truth_counts = {
        truth: sum(row["truth_transition"] == truth for row in warning_rows)
        for truth in (0, 1)
    }
    if len(warning_rows) != 9 or truth_counts != {0: 3, 1: 6}:
        raise AssertionError("event-centred transition population must be 3 negative and 6 positive")
    write_csv(out / "transition_warning_metrics.csv", warning_rows)
    write_json(
        out / "transition_warning_summary.json",
        {
            "distribution_unit": "retrospective_event_aligned_forecast_opportunity",
            "overall": classification_summary(warning_rows),
            "by_horizon": {
                f"h{horizon}": classification_summary(
                    [row for row in warning_rows if row["horizon"] == horizon]
                )
                for horizon in range(1, ROLLOUT + 1)
            },
        },
    )
    np.savez_compressed(out / "locked_transition_predictions.npz", **assets)
    pre_event_forecast_opportunities_evaluation(
        model, heldout, graph, statistics, out
    )


def matched_pidl_evaluation(
    model: TransitionAwareMeshOperator,
    heldout: dict,
    graph: dict[str, torch.Tensor],
    graph_arrays: dict[str, np.ndarray],
    statistics: StateStatistics,
    data_root: Path,
    out: Path,
) -> None:
    """Write primary observation-only controls and secondary PIDL context."""
    target_cycles = {"hard5_u011": 121, "hard5_u012": 82, "hard5_u013": 55}
    target_cycle = target_cycles[heldout["trajectory_id"]]
    origin_cycle = target_cycle - 1
    predictions, _ = predict_rollout(
        model, heldout, origin_cycle, 1, graph, statistics
    )
    gno = predictions[target_cycle].cpu().numpy()
    fem = heldout["states"][target_cycle - 1].cpu().numpy()
    primary_predictions = {
        "gno_data": gno,
        **{
            method: baseline_rollout(
                heldout, origin_cycle, 1, statistics, method
            )[target_cycle]
            .cpu()
            .numpy()
            for method in ("persistence", "constrained_linear")
        },
    }
    areas = np.asarray(graph_arrays["areas"], dtype=np.float64)
    primary_rows = [
        {
            "trajectory_id": heldout["trajectory_id"],
            "umax": heldout["umax"],
            "target_cycle": target_cycle,
            "origin_cycle": origin_cycle,
            "fold_role": fold_role(heldout["trajectory_id"]),
            "evaluation_role": "secondary_diagnostic",
            "mapping_domain": "native_full_mesh",
            "method": method,
            **field_metrics(prediction, fem, areas),
        }
        for method, prediction in primary_predictions.items()
    ]
    write_csv(out / "matched_cycle_baseline_metrics.csv", primary_rows)

    pidl_asset = np.load(
        data_root / "pidl_matches" / f"{heldout['trajectory_id']}.npz",
        allow_pickle=False,
    )
    required_pidl_keys = {
        "fem_centroids",
        "fem_areas",
        "damage",
        "alpha_bar",
        "fatigue_f",
        "psi_raw_direct",
        "mapping_contained",
    }
    if not required_pidl_keys.issubset(pidl_asset.files):
        raise ValueError("PIDL secondary asset is missing frozen mapping fields")
    expected_centroids = np.asarray(graph_arrays["centroids"])
    pidl_centroids = np.asarray(pidl_asset["fem_centroids"])
    pidl_areas = np.asarray(pidl_asset["fem_areas"])
    if (
        pidl_centroids.shape != expected_centroids.shape
        or not np.array_equal(pidl_centroids, expected_centroids)
        or pidl_areas.shape != areas.shape
        or not np.array_equal(pidl_areas, areas)
    ):
        raise ValueError("PIDL secondary mesh metadata does not match frozen FEM mesh")
    pidl = np.column_stack(
        [
            np.clip(np.asarray(pidl_asset["damage"]), 0.0, 1.0),
            np.maximum(np.asarray(pidl_asset["alpha_bar"]), 0.0),
            np.clip(np.asarray(pidl_asset["fatigue_f"]), 0.0, 1.0),
            np.log10(np.maximum(np.asarray(pidl_asset["psi_raw_direct"]), 1.0e-12)),
        ]
    ).astype(np.float32)
    contained = np.asarray(pidl_asset["mapping_contained"], dtype=bool)
    if (
        pidl.shape != fem.shape
        or contained.shape != (len(fem),)
        or not contained.any()
        or not np.isfinite(pidl).all()
    ):
        raise ValueError("PIDL secondary field shape, mask, or finiteness is invalid")
    rows = []
    for method, prediction in (
        ("gno_data", gno),
        ("pidl_mapped", pidl),
    ):
        rows.append(
            {
                "trajectory_id": heldout["trajectory_id"],
                "umax": heldout["umax"],
                "target_cycle": target_cycle,
                "origin_cycle": origin_cycle,
                "method": method,
                "fold_role": fold_role(heldout["trajectory_id"]),
                "evaluation_role": "secondary",
                "timing_semantics": "timing_unverified_secondary",
                "comparison_class": "nominal_same_cycle_pre_event_not_primary",
                "mapping_domain": "pidl_containing_triangle_cells_only",
                "mapping_contained_cells": int(contained.sum()),
                **field_metrics(prediction[contained], fem[contained], areas[contained]),
            }
        )
    write_csv(out / "matched_pidl_fem_metrics.csv", rows)
    np.savez_compressed(
        out / "matched_pidl_fem_fields.npz",
        centroids=np.asarray(graph_arrays["centroids"]),
        areas=areas,
        mapping_contained=contained,
        fem=fem,
        gno=gno,
        persistence=primary_predictions["persistence"],
        constrained_linear=primary_predictions["constrained_linear"],
        pidl=pidl,
        target_cycle=np.asarray(target_cycle),
    )


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root)
        return True
    except ValueError:
        return False


def _single_gpu_processes(gpu_index: str) -> list[int]:
    result = subprocess.run(
        [
            "nvidia-smi",
            "-i",
            gpu_index,
            "--query-compute-apps=pid",
            "--format=csv,noheader,nounits",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"nvidia-smi preflight failed: {result.stderr.strip()}")
    return [int(line.strip()) for line in result.stdout.splitlines() if line.strip()]


def _snapshot_commit(path: Path) -> str | None:
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("commit="):
            return line.split("=", 1)[1].strip()
    return None


def enforce_taobo_preflight(args: argparse.Namespace) -> None:
    """Fail closed before dataset load, archive mutation, or output creation."""
    if sys.platform == "darwin":
        raise RuntimeError(
            "training is disabled on Mac; use the approved PIDL producer"
        )
    if (
        args.producer != "taobo"
        or os.environ.get("PIDL_PRODUCER_ID") != "taobo-172.16.100.2"
    ):
        raise RuntimeError("D1 requires explicit Taobo producer identity")
    if os.environ.get("USER") != "drtao":
        raise RuntimeError("D1 Taobo run must use the drtao account")
    gpu_index = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    if not re.fullmatch(r"[0-7]", gpu_index):
        raise RuntimeError(
            "CUDA_VISIBLE_DEVICES must contain exactly one GPU index 0..7"
        )
    if not torch.cuda.is_available() or args.device != "cuda":
        raise RuntimeError("D1 requires an available CUDA device and --device cuda")
    if "RTX 4090" not in torch.cuda.get_device_name(0):
        raise RuntimeError("D1 frozen producer expects a Taobo RTX 4090")
    foreign_gpu_pids = [
        pid for pid in _single_gpu_processes(gpu_index) if pid != os.getpid()
    ]
    if foreign_gpu_pids:
        raise RuntimeError(
            f"selected GPU is already occupied by PIDs {foreign_gpu_pids}"
        )

    mount = Path("/mnt/data2")
    if not os.path.ismount(mount):
        raise RuntimeError("/mnt/data2 is not mounted")
    if shutil.disk_usage(mount).free < 50 * 1024**3:
        raise RuntimeError("/mnt/data2 has less than 50 GiB free")
    if not re.fullmatch(r"pf_[A-Za-z0-9_.-]+", args.run_id):
        raise RuntimeError("run_id must be an attributable pf_* identifier")
    run_root = Path("/mnt/data2/drtao/wennie") / args.run_id
    archive_base = Path("/mnt/data2/drtao/pidl_archives") / args.run_id
    if not _under(args.out, run_root) or args.out == run_root:
        raise RuntimeError("job output must be a fresh child of the declared run root")
    if not _under(args.archive_root, archive_base):
        raise RuntimeError("job archive must be under the declared Taobo archive root")
    if not _under(args.log_path, run_root / "logs"):
        raise RuntimeError("job log must be under the declared run root logs directory")
    if args.out.exists() or args.archive_root.exists():
        raise RuntimeError("job output and archive paths must both be fresh")
    if not _under(args.data_root, Path("/mnt/data2/drtao")):
        raise RuntimeError("D1 data must be staged under /mnt/data2/drtao")
    exact_environment = {
        "PIDL_ARCHIVE_DIR": args.archive_root,
        "PIDL_LOG_PATH": args.log_path,
    }
    for name, expected in exact_environment.items():
        value = os.environ.get(name)
        if not value or Path(value).resolve() != expected.resolve():
            raise RuntimeError(f"{name} must equal {expected}")
    for name in ("TMPDIR", "XDG_CACHE_HOME", "TORCH_EXTENSIONS_DIR"):
        value = os.environ.get(name)
        if not value or not _under(Path(value), run_root):
            raise RuntimeError(f"{name} must be task-owned under {run_root}")

    if not MATRIX_LOCK_PATH.is_file():
        raise RuntimeError("D1 matrix lock is missing")
    if sha256_file(MATRIX_LOCK_PATH) != args.release_matrix_sha256:
        raise RuntimeError("matrix lock does not match owner-authorized release hash")
    lock = json.loads(MATRIX_LOCK_PATH.read_text(encoding="utf-8"))
    actual_hashes = {
        name: sha256_file(path) for name, path in locked_code_paths().items()
    }
    if actual_hashes != lock.get("code_sha256"):
        raise RuntimeError(
            "runner and direct dependencies do not match the D1 code lock"
        )
    if not re.fullmatch(r"[0-9a-f]{40}", args.release_commit):
        raise RuntimeError("release commit must be a full 40-character SHA")
    repo = HERE.parent
    commit = _git_output(repo, "rev-parse", "HEAD")
    dirty = _git_output(repo, "status", "--short")
    if commit != "unavailable":
        if dirty:
            raise RuntimeError("D1 refuses a dirty Taobo git checkout")
        if commit != args.release_commit:
            raise RuntimeError(
                "Taobo HEAD does not match owner-authorized release commit"
            )
    else:
        snapshot_commit = _snapshot_commit(repo / "RUN_PROVENANCE.txt")
        if snapshot_commit != args.release_commit:
            raise RuntimeError(
                "rsync snapshot provenance does not match release commit"
            )


def _git_output(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=repo, text=True, capture_output=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def runtime_provenance(args: argparse.Namespace) -> dict:
    repo = HERE.parent
    code_paths = {**locked_code_paths(), "matrix_lock": MATRIX_LOCK_PATH}
    return {
        "producer": args.producer,
        "producer_id": os.environ.get("PIDL_PRODUCER_ID"),
        "hostname": socket.gethostname(),
        "user": os.environ.get("USER"),
        "platform": platform.platform(),
        "python": sys.version,
        "torch": torch.__version__,
        "cuda_runtime": torch.version.cuda,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "gpu_name": torch.cuda.get_device_name(0),
        "run_id": args.run_id,
        "output_root": str(args.out),
        "archive_root": str(args.archive_root),
        "log_path": str(args.log_path),
        "launcher_session": args.launcher_session,
        "runner_pid": os.getpid(),
        "parent_pid": os.getppid(),
        "launch_time_utc": datetime.now(timezone.utc).isoformat(),
        "cwd": str(Path.cwd()),
        "argv": sys.argv,
        "release_commit": args.release_commit,
        "release_matrix_sha256": args.release_matrix_sha256,
        "task_environment": {
            name: os.environ.get(name)
            for name in (
                "PIDL_ARCHIVE_DIR",
                "PIDL_LOG_PATH",
                "TMPDIR",
                "XDG_CACHE_HOME",
                "TORCH_EXTENSIONS_DIR",
            )
        },
        "git_commit": _git_output(repo, "rev-parse", "HEAD"),
        "git_branch": _git_output(repo, "branch", "--show-current"),
        "git_status_short": _git_output(repo, "status", "--short"),
        "code_sha256": {
            name: sha256_file(path) if path.is_file() else "missing"
            for name, path in code_paths.items()
        },
        "reproducibility_level": "seeded_statistical_not_byte_deterministic",
        "determinism_boundary": (
            "cuDNN deterministic mode is enabled, but CUDA index_add graph aggregation "
            "is not promised byte-identical; three locked seeds are the inference unit"
        ),
    }


def _payload_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): sha256_file(path)
        for path in root.rglob("*")
        if path.is_file() and path.name != "LAUNCH_RECEIPT.json"
    }


def mirror_completed_output_to_archive(
    out: Path, archive_root: Path
) -> dict[str, str]:
    """Mirror non-receipt payload and fail if the archive differs byte-for-byte."""
    for source in sorted(out.rglob("*")):
        relative = source.relative_to(out)
        destination = archive_root / relative
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        elif source.is_file() and source.name != "LAUNCH_RECEIPT.json":
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    output_files = _payload_hashes(out)
    archive_files = _payload_hashes(archive_root)
    if not output_files or archive_files != output_files:
        raise RuntimeError("completed Taobo output archive is missing or hash-mismatched")
    return output_files


def finalize_completed_archive(
    out: Path, archive_root: Path, complete_receipt: dict
) -> None:
    receipt_paths = (
        archive_root / "LAUNCH_RECEIPT.json",
        out / "LAUNCH_RECEIPT.json",
    )
    try:
        payload_hashes = mirror_completed_output_to_archive(out, archive_root)
        final_receipt = {**complete_receipt, "payload_sha256": payload_hashes}
        for receipt_path in receipt_paths:
            write_json_atomic(receipt_path, final_receipt)
        if sha256_file(receipt_paths[0]) != sha256_file(receipt_paths[1]):
            raise RuntimeError("output and archive completion receipts differ")
        if (
            _payload_hashes(out) != payload_hashes
            or _payload_hashes(archive_root) != payload_hashes
        ):
            raise RuntimeError("payload changed during archive finalization")
    except Exception:
        failure_receipt = {
            **complete_receipt,
            "status": "archive_finalization_failed",
            "archive_verified": False,
            "training_complete": False,
        }
        for receipt_path in receipt_paths:
            try:
                write_json_atomic(receipt_path, failure_receipt)
            except Exception:
                pass
        raise


def train(args: argparse.Namespace) -> None:
    enforce_taobo_preflight(args)
    args.out.mkdir(parents=True, exist_ok=False)
    args.archive_root.mkdir(parents=True, exist_ok=False)
    provenance = runtime_provenance(args)
    write_json(args.out / "RUN_PROVENANCE.json", provenance)
    write_json(
        args.out / "LAUNCH_RECEIPT.json",
        {
            "status": "runner_started_before_dataset_load",
            "claim_class": "processed_griphfith_archive_imitation_only",
            "teacher_qualified": False,
            "damage_fixed_point_gate": "fail",
            "physics_loss_weight": 0.0,
            "physical_validation": False,
            "training_complete": False,
            "provenance": provenance,
        },
    )
    set_seed(args.seed)
    device = torch.device(args.device)
    training, heldout, graph, graph_arrays, manifest = load_dataset(
        args.data_root, args.heldout, device
    )
    statistics = training_statistics(training, device)
    active_residual_scale = training_active_residual_scale(training, device)
    positive, negative = build_training_windows(training)
    model = TransitionAwareMeshOperator(context=CONTEXT, hidden_dim=args.hidden).to(
        device
    )
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    if parameter_count != EXPECTED_PARAMETER_COUNT:
        raise ValueError(f"unexpected model capacity: {parameter_count}")
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-6)
    rng = random.Random(args.seed)
    area = graph["areas"].reshape(-1)
    bucket_calibration = calibrate_bucket_gradient_scales(
        training, positive, negative, graph, statistics, active_residual_scale
    )
    bucket_gradient_scales = bucket_calibration.gradient_scales
    history_rows: list[dict] = []
    started = time.perf_counter()
    for step in range(1, args.steps + 1):
        window = choose_balanced_window(positive, negative, step, rng)
        item = training[window.trajectory_index]
        history = [
            state
            for state in item["states"][
                window.origin_cycle - CONTEXT : window.origin_cycle
            ]
        ]
        optimizer.zero_grad(set_to_none=True)
        losses = []
        field_values = []
        transition_values = []
        for target_cycle in range(
            window.origin_cycle + 1, window.origin_cycle + ROLLOUT + 1
        ):
            prediction, logit = model(
                torch.stack(history[-CONTEXT:]), graph, statistics, item["metadata"]
            )
            field = normalized_field_loss(
                prediction,
                item["states"][target_cycle - 1],
                area,
                graph["edge_index"],
                statistics,
                active_residual_scale,
            )
            bucket_name = "transition" if window.contains_transition else "ordinary"
            balanced_field = field.total / bucket_gradient_scales[bucket_name]
            combined = supervised_transition_loss(
                balanced_field,
                logit,
                transition_target(target_cycle, item["first_hit"], device),
                transition_weight=args.transition_weight,
            )
            losses.append(combined.total)
            field_values.append(field.total.detach())
            transition_values.append(combined.transition.detach())
            history.append(prediction)
        total = torch.stack(losses).mean()
        if not torch.isfinite(total):
            raise FloatingPointError(f"non-finite loss at step {step}")
        total.backward()
        gradient_norm = clip_finite_gradients(model.parameters())
        optimizer.step()
        if step == 1 or step % 100 == 0 or step == args.steps:
            row = {
                "step": step,
                "sample_bucket": "transition"
                if window.contains_transition
                else "ordinary",
                "trajectory_id": item["trajectory_id"],
                "origin_cycle": window.origin_cycle,
                "total_loss": float(total.detach().cpu()),
                "field_loss": float(torch.stack(field_values).mean().cpu()),
                "balanced_field_loss": float(
                    (
                        torch.stack(field_values).mean()
                        / bucket_gradient_scales[bucket_name]
                    ).cpu()
                ),
                "transition_loss": float(torch.stack(transition_values).mean().cpu()),
                "gradient_norm": gradient_norm,
                "elapsed_seconds": time.perf_counter() - started,
            }
            history_rows.append(row)
            print(json.dumps(row), flush=True)

    torch.save(
        {
            "model": model.state_dict(),
            "statistics": {
                name: getattr(statistics, name).cpu()
                for name in ("state_mean", "state_std", "residual_mean", "residual_std")
            },
            "active_residual_scale": active_residual_scale.cpu(),
            "bucket_gradient_scales": {
                name: value.cpu() for name, value in bucket_gradient_scales.items()
            },
            "args": vars(args),
        },
        args.out / "final_model.pt",
    )
    write_csv(args.out / "training_history.csv", history_rows)
    evaluate(model, heldout, graph, graph_arrays, statistics, args.out)
    matched_pidl_evaluation(
        model, heldout, graph, graph_arrays, statistics, args.data_root, args.out
    )
    run_manifest = {
        "status": "complete",
        "claim_class": "processed_griphfith_archive_imitation_only",
        "teacher_qualified": False,
        "damage_fixed_point_gate": "fail",
        "physics_loss_weight": 0.0,
        "physical_validation": False,
        "trajectory_metadata": "[hard=1, soft=0, five_step=1, design_scaled_umax]",
        "heldout_trajectory_id": heldout["trajectory_id"],
        "fold_role": fold_role(heldout["trajectory_id"]),
        "training_trajectory_ids": [item["trajectory_id"] for item in training],
        "heldout_first_hit_used_in_training": False,
        "context": CONTEXT,
        "rollout": ROLLOUT,
        "statistics": "trajectory_equal_pre_hit_first_and_second_moments",
        "balanced_sampling": "alternate bucket then equal-probability trajectory then pre-hit origin",
        "training_origins": "strictly_less_than_training_first_hit",
        "pidl_values": "secondary_evaluation_only_after_training",
        "pidl_bytes": "preflight_hash_verified",
        "bucket_gradient_scales": {
            name: float(value.cpu()) for name, value in bucket_gradient_scales.items()
        },
        "bucket_persistence_raw_loss_means": {
            name: float(value.cpu())
            for name, value in bucket_calibration.raw_loss_means.items()
        },
        "bucket_persistence_raw_gradient_means": {
            name: float(value.cpu())
            for name, value in bucket_calibration.raw_gradient_means.items()
        },
        "bucket_persistence_normalized_gradient_means": (
            bucket_calibration.normalized_gradient_means
        ),
        "active_residual_scale": float(active_residual_scale.cpu()),
        "field_loss": "training-fold residual-scaled SmoothL1 plus stable support logits, bucket-calibrated by persistence prediction-gradient norm",
        "steps": args.steps,
        "seed": args.seed,
        "parameter_count": parameter_count,
        "dataset_manifest_sha256": sha256_file(args.data_root / "RUN_MANIFEST.json"),
        "dataset_id": manifest["dataset_id"],
        "dataset_hash_file_sha256": sha256_file(args.data_root / "HASHES.sha256"),
        "provenance": provenance,
        "primary_assets": [
            "fem_centred_metrics.csv",
            "transition_warning_metrics.csv",
            "transition_warning_summary.json",
            "pre_event_forecast_opportunities_metrics.csv",
            "pre_event_forecast_opportunities_summary.json",
            "locked_transition_predictions.npz",
            "matched_cycle_baseline_metrics.csv",
            "matched_pidl_fem_metrics.csv",
            "matched_pidl_fem_fields.npz",
            "final_model.pt",
            "RUN_PROVENANCE.json",
            "LAUNCH_RECEIPT.json",
        ],
    }
    write_json(args.out / "RUN_MANIFEST.json", run_manifest)
    complete_receipt = {
        "status": "complete",
        "claim_class": "processed_griphfith_archive_imitation_only",
        "teacher_qualified": False,
        "damage_fixed_point_gate": "fail",
        "physics_loss_weight": 0.0,
        "physical_validation": False,
        "training_complete": True,
        "archive_verified": True,
        "provenance": provenance,
        "run_manifest_sha256": sha256_file(args.out / "RUN_MANIFEST.json"),
    }
    write_json(
        args.out / "LAUNCH_RECEIPT.json",
        {**complete_receipt, "status": "outputs_complete_archive_pending", "archive_verified": False},
    )
    finalize_completed_archive(args.out, args.archive_root, complete_receipt)
    print(json.dumps(run_manifest, indent=2, allow_nan=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--heldout", required=True)
    parser.add_argument("--seed", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--hidden", type=int, default=96)
    parser.add_argument("--transition-weight", type=float, default=0.25)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--producer", choices=("taobo",), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--log-path", type=Path, required=True)
    parser.add_argument("--launcher-session", required=True)
    parser.add_argument("--release-commit", required=True)
    parser.add_argument("--release-matrix-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--allow-data-only-d1", action="store_true")
    args = parser.parse_args()
    if not args.allow_data_only_d1:
        parser.error("--allow-data-only-d1 is required; this run is FEM imitation only")
    if args.steps != 3000 or args.hidden != 96 or args.transition_weight != 0.25:
        parser.error(
            "D1 hyperparameters are frozen at steps=3000, hidden=96, transition-weight=0.25"
        )
    return args


if __name__ == "__main__":
    train(parse_args())
