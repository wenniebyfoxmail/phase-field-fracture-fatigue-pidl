#!/usr/bin/env python3
"""Train one frozen data-only transition-aware GNO LOCO fold/seed.

Training is disabled on Mac.  This runner uses only archived FEM field and
transition labels from the three training trajectories; it contains no physics
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
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from fem_mechanism_operator import StateStatistics, mechanism_loss  # noqa: E402
from train_fem_mechanism_mesh_operator import field_metrics  # noqa: E402
from transition_aware_mesh_operator import (  # noqa: E402
    TransitionAwareMeshOperator,
    supervised_transition_loss,
)


CONTEXT = 3
ROLLOUT = 3
EXPECTED_DATASET_ID = "factorial_loco_fem_states_v1"
EXPECTED_DATASET_MANIFEST_SHA256 = "b9723d613e7b7a5e33b4fb7c9a9cc65ef6d1ae6c4e9b971f64dc74ad0f955648"
EXPECTED_CASE_ID = "at1_fatigue_mesh_pino_d1_transition_aware_gno_20260826"
PRIMARY_WARNING_THRESHOLD = 0.5
GRAPH_FEATURE_KEYS = (
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
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split(maxsplit=1)
        target = root / relative.lstrip("*")
        if not target.is_file() or sha256_file(target) != expected:
            raise ValueError(f"dataset hash mismatch: {relative}")


def load_and_verify_matrix_lock(path: Path) -> dict:
    lock = json.loads(path.read_text(encoding="utf-8"))
    if lock.get("case_id") != EXPECTED_CASE_ID:
        raise ValueError("unexpected D1 matrix lock case_id")
    if lock.get("dataset", {}).get("manifest_sha256") != EXPECTED_DATASET_MANIFEST_SHA256:
        raise ValueError("matrix lock does not contain the frozen dataset manifest SHA")
    if lock.get("optimization", {}).get("physics_loss_weight") != 0.0:
        raise ValueError("D1 must keep physics_loss_weight exactly zero")
    evaluation = lock.get("evaluation", {})
    if evaluation.get("primary_warning_output") != "transition_score_ge_0p5":
        raise ValueError("matrix lock does not freeze the primary warning output")
    if evaluation.get("transition_score_threshold") != PRIMARY_WARNING_THRESHOLD:
        raise ValueError("matrix lock does not freeze transition threshold 0.5")
    return lock


def git_provenance(root: Path) -> dict[str, object]:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    commit = run("rev-parse", "HEAD")
    dirty_lines = run("status", "--porcelain").splitlines()
    if dirty_lines:
        raise RuntimeError("D1 producer checkout must be clean")
    return {"git_commit": commit, "git_dirty": False}


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty table: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def trajectory_metadata(trajectory_id: str, device: torch.device) -> torch.Tensor:
    hard = float("_hard_" in trajectory_id)
    soft = float("_soft_" in trajectory_id)
    step5 = float("_5step_" in trajectory_id)
    step8 = float("_8step_" in trajectory_id)
    if hard + soft != 1 or step5 + step8 != 1:
        raise ValueError(f"cannot decode factorial metadata from {trajectory_id}")
    return torch.tensor([hard, soft, step5, step8], dtype=torch.float32, device=device)


def load_graph(path: Path, device: torch.device) -> tuple[dict[str, torch.Tensor], dict[str, np.ndarray], list[str]]:
    data = np.load(path, allow_pickle=False)
    missing = sorted(set(GRAPH_FEATURE_KEYS) - set(data.files))
    if missing:
        raise ValueError(f"graph packet lacks required keys: {missing}")
    ignored = sorted(set(data.files) - set(GRAPH_FEATURE_KEYS))
    arrays = {name: np.asarray(data[name]) for name in GRAPH_FEATURE_KEYS}
    graph = {name: torch.from_numpy(value).to(device) for name, value in arrays.items()}
    for name in ("edge_index", "cluster_index", "coarse_edge_index"):
        graph[name] = graph[name].long()
    if set(graph) != set(GRAPH_FEATURE_KEYS):
        raise AssertionError("non-allowlisted graph payload entered model features")
    return graph, arrays, ignored


def load_trajectory(path: Path, device: torch.device) -> dict:
    data = np.load(path, allow_pickle=False)
    trajectory_id = str(np.asarray(data["trajectory_id"]).item())
    cycles = np.asarray(data["cycles"], dtype=int)
    if not np.array_equal(cycles, np.arange(1, len(cycles) + 1)):
        raise ValueError(f"nonconsecutive cycles in {path}")
    return {
        "trajectory_id": trajectory_id,
        "states": torch.from_numpy(np.asarray(data["states"], dtype=np.float32)).to(device),
        "first_hit": int(np.asarray(data["first_hit_cycle"]).item()),
        "confirmed": int(np.asarray(data["confirmed_cycle"]).item()),
        "metadata": trajectory_metadata(trajectory_id, device),
    }


def load_dataset(
    root: Path, heldout_id: str, device: torch.device
) -> tuple[list[dict], dict, dict[str, torch.Tensor], dict[str, np.ndarray], dict, list[str]]:
    verify_hash_manifest(root)
    manifest_sha = sha256_file(root / "RUN_MANIFEST.json")
    if manifest_sha != EXPECTED_DATASET_MANIFEST_SHA256:
        raise ValueError(
            f"frozen dataset manifest mismatch: {manifest_sha} != {EXPECTED_DATASET_MANIFEST_SHA256}"
        )
    manifest = json.loads((root / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
    if manifest.get("dataset_id") != EXPECTED_DATASET_ID or manifest.get("trajectory_count") != 4:
        raise ValueError("unexpected dataset identity or trajectory count")
    paths = {
        row["trajectory_id"]: root / "trajectories" / row["data_file"]
        for row in manifest["trajectories"]
    }
    if heldout_id not in paths:
        raise ValueError(f"heldout trajectory not found: {heldout_id}")
    graph, graph_arrays, ignored_graph_keys = load_graph(root / manifest["graph_file"], device)
    loaded = {key: load_trajectory(path, device) for key, path in paths.items()}
    heldout = loaded.pop(heldout_id)
    training = [loaded[key] for key in sorted(loaded)]
    if heldout_id in {item["trajectory_id"] for item in training}:
        raise AssertionError("heldout trajectory leaked into training")
    return training, heldout, graph, graph_arrays, manifest, ignored_graph_keys


def training_statistics(items: list[dict], device: torch.device) -> StateStatistics:
    states = np.concatenate([item["states"].cpu().numpy() for item in items], axis=0).astype(np.float64)
    residuals = np.concatenate(
        [np.diff(item["states"].cpu().numpy(), axis=0) for item in items], axis=0
    ).astype(np.float64)
    arrays = (
        states.mean(axis=(0, 1)),
        np.maximum(states.std(axis=(0, 1)), 1e-6),
        residuals.mean(axis=(0, 1)),
        np.maximum(residuals.std(axis=(0, 1)), 1e-6),
    )
    return StateStatistics(
        *(torch.tensor(array, dtype=torch.float32, device=device).reshape(1, -1) for array in arrays)
    )


@dataclass(frozen=True)
class Window:
    trajectory_index: int
    origin_cycle: int
    contains_transition: bool


def build_training_windows(items: list[dict], context: int = CONTEXT, rollout: int = ROLLOUT) -> tuple[list[Window], list[Window]]:
    positive: list[Window] = []
    negative: list[Window] = []
    for item_index, item in enumerate(items):
        for origin in range(context, len(item["states"]) - rollout + 1):
            targets = range(origin + 1, origin + rollout + 1)
            window = Window(
                trajectory_index=item_index,
                origin_cycle=origin,
                contains_transition=any(cycle >= item["first_hit"] for cycle in targets),
            )
            (positive if window.contains_transition else negative).append(window)
    if not positive or not negative:
        raise ValueError("training split needs both transition and ordinary windows")
    return positive, negative


def choose_balanced_window(
    positive: list[Window], negative: list[Window], step: int, rng: random.Random
) -> Window:
    """Alternate positive/negative buckets; randomness stays within the bucket."""
    bucket = positive if step % 2 else negative
    return rng.choice(bucket)


def transition_target(target_cycle: int, first_hit: int, device: torch.device) -> torch.Tensor:
    return torch.tensor(float(target_cycle >= first_hit), device=device)


def retrospective_warning_origins(first_hit: int) -> range:
    """Three frozen event-centred origins; never used during optimization."""
    return range(first_hit - 3, first_hit)


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


def event_hit(state: np.ndarray, centroids: np.ndarray) -> bool:
    return int(np.count_nonzero((centroids[:, 0] >= 0.48) & (state[:, 0] >= 0.95))) >= 3


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
    for origin in retrospective_warning_origins(heldout["first_hit"]):
        horizon = min(3, len(heldout["states"]) - origin)
        predictions, logits = predict_rollout(
            model, heldout, origin, horizon, graph, statistics
        )
        for cycle, prediction in predictions.items():
            prediction_array = prediction.cpu().numpy()
            target_array = heldout["states"][cycle - 1].cpu().numpy()
            rows.append(
                {
                    "trajectory_id": heldout["trajectory_id"],
                    "origin_cycle": origin,
                    "target_cycle": cycle,
                    "horizon": cycle - origin,
                    **field_metrics(prediction_array, target_array, areas),
                }
            )
            score = float(torch.sigmoid(logits[cycle]).cpu())
            truth = int(cycle >= heldout["first_hit"])
            warning_rows.append(
                {
                    "trajectory_id": heldout["trajectory_id"],
                    "origin_cycle": origin,
                    "target_cycle": cycle,
                    "horizon": cycle - origin,
                    "truth_transition": truth,
                    "transition_score_uncalibrated": score,
                    "primary_warning_transition_score_ge_0p5": int(
                        score >= PRIMARY_WARNING_THRESHOLD
                    ),
                    "diagnostic_predicted_field_hit": int(event_hit(prediction_array, centroids)),
                }
            )
            if origin == heldout["first_hit"] - 3:
                assets[f"prediction_c{cycle}"] = prediction_array
                assets[f"fem_c{cycle}"] = target_array
        if origin == heldout["first_hit"] - 3:
            assets["origin_state"] = heldout["states"][origin - 1].cpu().numpy()
    write_csv(out / "fem_centred_metrics.csv", rows)
    write_csv(out / "transition_warning_metrics.csv", warning_rows)
    np.savez_compressed(out / "locked_transition_predictions.npz", **assets)


def train(args: argparse.Namespace) -> None:
    if sys.platform == "darwin":
        raise RuntimeError("training is disabled on Mac; use the approved PIDL producer")
    set_seed(args.seed)
    device = torch.device(args.device)
    matrix_lock = load_and_verify_matrix_lock(args.matrix_lock)
    repo_root = HERE.parent
    provenance = git_provenance(repo_root)
    training, heldout, graph, graph_arrays, manifest, ignored_graph_keys = load_dataset(
        args.data_root, args.heldout, device
    )
    statistics = training_statistics(training, device)
    positive, negative = build_training_windows(training)
    model = TransitionAwareMeshOperator(context=CONTEXT, hidden_dim=args.hidden).to(device)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    if not 250_000 <= parameter_count <= 450_000:
        raise ValueError(f"unexpected model capacity: {parameter_count}")
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-6)
    rng = random.Random(args.seed)
    area = graph["areas"].reshape(-1)
    history_rows: list[dict] = []
    args.out.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    for step in range(1, args.steps + 1):
        window = choose_balanced_window(positive, negative, step, rng)
        item = training[window.trajectory_index]
        history = [state for state in item["states"][window.origin_cycle - CONTEXT : window.origin_cycle]]
        optimizer.zero_grad(set_to_none=True)
        losses = []
        field_values = []
        transition_values = []
        for target_cycle in range(window.origin_cycle + 1, window.origin_cycle + ROLLOUT + 1):
            prediction, logit = model(
                torch.stack(history[-CONTEXT:]), graph, statistics, item["metadata"]
            )
            field, _ = mechanism_loss(
                prediction,
                item["states"][target_cycle - 1],
                area,
                graph["edge_index"],
            )
            combined = supervised_transition_loss(
                field,
                logit,
                transition_target(target_cycle, item["first_hit"], device),
                transition_weight=args.transition_weight,
            )
            losses.append(combined.total)
            field_values.append(combined.field.detach())
            transition_values.append(combined.transition.detach())
            history.append(prediction)
        total = torch.stack(losses).mean()
        if not torch.isfinite(total):
            raise FloatingPointError(f"non-finite loss at step {step}")
        total.backward()
        gradient_norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0).cpu())
        optimizer.step()
        if step == 1 or step % 100 == 0 or step == args.steps:
            row = {
                "step": step,
                "sample_bucket": "transition" if window.contains_transition else "ordinary",
                "trajectory_id": item["trajectory_id"],
                "origin_cycle": window.origin_cycle,
                "total_loss": float(total.detach().cpu()),
                "field_loss": float(torch.stack(field_values).mean().cpu()),
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
            "args": vars(args),
        },
        args.out / "final_model.pt",
    )
    write_csv(args.out / "training_history.csv", history_rows)
    evaluate(model, heldout, graph, graph_arrays, statistics, args.out)
    run_manifest = {
        "status": "complete",
        "claim_class": "synthetic_fem_imitation_only",
        "physics_loss_weight": 0.0,
        "physical_validation": False,
        "teacher_qualified": False,
        "damage_fixed_point_gate": "fail",
        "target_semantics": "processed archived GRIPHFiTH cycle-peak outputs",
        "heldout_trajectory_id": heldout["trajectory_id"],
        "training_trajectory_ids": [item["trajectory_id"] for item in training],
        "heldout_first_hit_used_in_training": False,
        "context": CONTEXT,
        "rollout": ROLLOUT,
        "balanced_sampling": "alternate transition-containing and ordinary training windows",
        "steps": args.steps,
        "seed": args.seed,
        "parameter_count": parameter_count,
        "dataset_manifest_sha256": sha256_file(args.data_root / "RUN_MANIFEST.json"),
        "dataset_id": manifest["dataset_id"],
        "matrix_lock_sha256": sha256_file(args.matrix_lock),
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "model_sha256": sha256_file(repo_root / "source" / "transition_aware_mesh_operator.py"),
        "loss_sha256": sha256_file(repo_root / "source" / "fem_mechanism_operator.py"),
        "metrics_sha256": sha256_file(repo_root / "SENS_tensile" / "train_fem_mechanism_mesh_operator.py"),
        "primary_warning_output": matrix_lock["evaluation"]["primary_warning_output"],
        "transition_score_threshold": PRIMARY_WARNING_THRESHOLD,
        "transition_score_calibrated": False,
        "evaluation_scope": "retrospective_event_centred_holdout",
        "ignored_graph_payload_keys": ignored_graph_keys,
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
        "cuda_runtime": torch.version.cuda,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "gpu_name": torch.cuda.get_device_name(device) if device.type == "cuda" else None,
        "command": [sys.executable, *sys.argv],
        "output_root": str(args.out.resolve()),
        "archive_root": os.environ.get("PIDL_ARCHIVE_DIR"),
        **provenance,
        "primary_assets": [
            "fem_centred_metrics.csv",
            "transition_warning_metrics.csv",
            "locked_transition_predictions.npz",
            "final_model.pt",
        ],
    }
    (args.out / "RUN_MANIFEST.json").write_text(
        json.dumps(run_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(run_manifest, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--matrix-lock", type=Path, required=True)
    parser.add_argument("--heldout", required=True)
    parser.add_argument("--seed", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--hidden", type=int, default=96)
    parser.add_argument("--transition-weight", type=float, default=0.25)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--allow-data-only-d1", action="store_true")
    args = parser.parse_args()
    if not args.allow_data_only_d1:
        parser.error("--allow-data-only-d1 is required; this run is FEM imitation only")
    if args.steps != 3000 or args.hidden != 96 or args.transition_weight != 0.25:
        parser.error("D1 hyperparameters are frozen at steps=3000, hidden=96, transition-weight=0.25")
    return args


if __name__ == "__main__":
    train(parse_args())
