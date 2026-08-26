#!/usr/bin/env python3
"""Train one Hard5 LOAO t+1 probabilistic-increment GNO fold/seed.

The runner is data-only processed-GRIPHFiTH imitation. Mac execution is blocked
before dataset loading or output creation; producer release/provenance wrapping
is added only after the core code and data contract pass review.
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

from probabilistic_increment_mesh_operator import (  # noqa: E402
    ProbabilisticIncrementMeshOperator,
    conditional_laplace_scale_loss,
    normalized_increment_target,
    normalized_laplace_interval,
)
from train_fem_mechanism_mesh_operator import field_metrics  # noqa: E402
from train_transition_aware_loco_gno import (  # noqa: E402
    _single_gpu_processes,
    _snapshot_commit,
    _under,
    baseline_rollout,
    clip_finite_gradients,
    finalize_completed_archive,
    load_dataset,
    set_seed,
    sha256_file,
    training_active_residual_scale,
    training_statistics,
    verify_hash_manifest,
)
from transition_aware_mesh_operator import normalized_field_loss  # noqa: E402


EXPERIMENT_ID = "hard5_probabilistic_increment_gno_v1_20260827"
DATASET_ID = "hard5_loao_fem_states_v1"
DATASET_MANIFEST_SHA256 = "9267a102a38375ebc815404a5ae81b2d3b23622448b5b178a2c4c1a5696e202a"
DATASET_HASH_FILE_SHA256 = "7bff035eaa618a7517335a3adb436e14d8bf606c6fa4e202497355518e82a55e"
RELEASE_AUTHORIZATION_SCHEMA = "hard5_probabilistic_increment_release_authorization_v1"
CONTEXT = 3
MEAN_STEPS = 3000
SCALE_STEPS = 500
HIDDEN_DIM = 96
EXPECTED_PARAMETER_COUNT = 367_400
MATRIX_LOCK_PATH = (
    HERE.parent
    / "docs"
    / "experiments"
    / "hard5_probabilistic_increment_gno_matrix_lock_20260827.json"
)
EXPECTED_JOB_PAYLOADS = frozenset(
    {
        "RELEASE_AUTHORIZATION.json",
        "RUN_MANIFEST.json",
        "RUN_PROVENANCE.json",
        "final_model.pt",
        "training_history.csv",
        "heldout_increment_metrics.csv",
        "heldout_uncertainty_metrics.csv",
        "selected_increment_fields.npz",
    }
)
SELECTED_ORIGINS = {
    "hard5_u011": (20, 40, 60, 120),
    "hard5_u012": (20, 40, 60, 80),
    "hard5_u013": (20, 30, 45, 58),
}
CHANNELS = ("damage", "alpha_bar", "fatigue_f", "log10_psi_raw")
TRAJECTORY_IDS = frozenset(SELECTED_ORIGINS)
CLAIMS = {
    "claim_class": "processed_griphfith_archive_imitation_only",
    "teacher_qualified": False,
    "physics_loss_weight": 0.0,
    "physical_validation": False,
    "uncertainty_claim": "uncalibrated_diagnostic_only",
}


def locked_code_paths() -> dict[str, Path]:
    repo = HERE.parent
    return {
        "runner": Path(__file__).resolve(),
        "model": repo / "source" / "probabilistic_increment_mesh_operator.py",
        "operator_dependency": repo / "source" / "fem_mechanism_operator.py",
        "feature_dependency": repo / "source" / "transition_aware_mesh_operator.py",
        "data_dependency": repo / "SENS_tensile" / "train_transition_aware_loco_gno.py",
        "metric_dependency": repo / "SENS_tensile" / "train_fem_mechanism_mesh_operator.py",
        "tests": repo / "tests" / "test_probabilistic_increment_mesh_operator.py",
        "runner_tests": repo / "tests" / "test_probabilistic_increment_loao_gno.py",
        "aggregate_analyzer": repo / "SENS_tensile" / "analyze_probabilistic_increment_gno_matrix.py",
        "aggregate_tests": repo / "tests" / "test_analyze_probabilistic_increment_gno_matrix.py",
        "preregistration": repo / "docs" / "experiments" / "hard5_probabilistic_increment_gno_preregistration_20260827.md",
    }


def validate_matrix_lock(lock: dict) -> None:
    if lock.get("schema_version") != "hard5_probabilistic_increment_matrix_lock_v1":
        raise RuntimeError("unexpected probabilistic-increment matrix lock schema")
    if lock.get("experiment_id") != EXPERIMENT_ID:
        raise RuntimeError("unexpected probabilistic-increment experiment id")
    if lock.get("status") != "frozen_pending_external_release_authorization":
        raise RuntimeError("matrix lock is not frozen for external authorization")
    dataset = lock.get("dataset", {})
    if (
        dataset.get("dataset_id") != DATASET_ID
        or dataset.get("manifest_sha256") != DATASET_MANIFEST_SHA256
        or dataset.get("hash_file_sha256") != DATASET_HASH_FILE_SHA256
        or set(dataset.get("trajectory_ids", [])) != TRAJECTORY_IDS
    ):
        raise RuntimeError("matrix dataset contract mismatch")
    matrix = lock.get("matrix", {})
    if (
        matrix.get("folds") != sorted(TRAJECTORY_IDS)
        or matrix.get("seeds") != [1, 2, 3]
        or matrix.get("job_count") != 9
        or matrix.get("producer") != "taobo_only"
    ):
        raise RuntimeError("matrix fold/seed/producer contract mismatch")
    if set(lock.get("required_job_payloads", [])) != EXPECTED_JOB_PAYLOADS:
        raise RuntimeError("matrix required payload contract mismatch")
    protocol = lock.get("protocol", {})
    if protocol != {
        "context": CONTEXT,
        "rollout": 1,
        "mean_steps": MEAN_STEPS,
        "scale_steps": SCALE_STEPS,
        "hidden_dim": HIDDEN_DIM,
        "selected_origins": {key: list(value) for key, value in SELECTED_ORIGINS.items()},
    }:
        raise RuntimeError("matrix model/evaluation protocol mismatch")


def load_release_authorization(
    args: argparse.Namespace, lock: dict, lock_sha256: str, code_sha256: dict
) -> dict:
    path = args.release_authorization
    if not path.is_file() or sha256_file(path) != args.release_authorization_sha256:
        raise RuntimeError("release authorization file hash mismatch")
    authorization = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "schema_version": RELEASE_AUTHORIZATION_SCHEMA,
        "authorization_status": "AUTHORIZED",
        "experiment_id": EXPERIMENT_ID,
        "matrix_experiment_id": EXPERIMENT_ID,
        "run_id": args.run_id,
        "matrix_lock_sha256": lock_sha256,
        "dataset_manifest_sha256": DATASET_MANIFEST_SHA256,
        "dataset_hash_file_sha256": DATASET_HASH_FILE_SHA256,
        "authorization_scope": "hard5_three_fold_three_seed_probabilistic_increment_gno",
        "producer": "taobo",
        "max_gpu_count": 1,
    }
    for key, value in expected.items():
        if authorization.get(key) != value:
            raise RuntimeError(f"release authorization mismatch for {key}")
    release_commit = authorization.get("release_commit", "")
    if not re.fullmatch(r"[0-9a-f]{40}", release_commit):
        raise RuntimeError("release authorization commit must be a full SHA")
    if authorization.get("code_sha256") != code_sha256:
        raise RuntimeError("release authorization code hashes mismatch")
    review = authorization.get("independent_review", {})
    if (
        review.get("verdict") != "PASS"
        or review.get("reviewed_commit") != release_commit
        or not re.fullmatch(r"[0-9a-f]{64}", review.get("review_note_sha256", ""))
    ):
        raise RuntimeError("release authorization lacks a locked independent PASS")
    jobs = authorization.get("jobs", [])
    actual_jobs = {
        (job.get("job_id"), job.get("heldout"), job.get("seed"))
        for job in jobs
        if isinstance(job, dict)
    }
    expected_jobs = {
        (f"{fold}_s{seed}", fold, seed)
        for fold in sorted(TRAJECTORY_IDS)
        for seed in (1, 2, 3)
    }
    if len(jobs) != 9 or actual_jobs != expected_jobs:
        raise RuntimeError("release authorization job matrix mismatch")
    if (args.out.name, args.heldout, args.seed) not in actual_jobs:
        raise RuntimeError("requested fold/seed is not release-authorized")
    if authorization.get("claims") != CLAIMS:
        raise RuntimeError("release authorization claim boundary mismatch")
    return authorization


def _git_output(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=repo, text=True, capture_output=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def enforce_taobo_preflight(args: argparse.Namespace) -> None:
    """Fail closed before dataset load or any output/archive mutation."""
    if sys.platform == "darwin":
        raise RuntimeError("Mac is code/sanity only; train on authorized Taobo producer")
    if (
        args.producer != "taobo"
        or os.environ.get("PIDL_PRODUCER_ID") != "taobo-172.16.100.2"
        or os.environ.get("USER") != "drtao"
    ):
        raise RuntimeError("probabilistic increment run requires explicit Taobo identity")
    gpu_index = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    if not re.fullmatch(r"[0-7]", gpu_index):
        raise RuntimeError("CUDA_VISIBLE_DEVICES must contain exactly one GPU index 0..7")
    if args.device != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("production training requires CUDA on Taobo")
    if "RTX 4090" not in torch.cuda.get_device_name(0):
        raise RuntimeError("frozen producer expects a Taobo RTX 4090")
    foreign = [pid for pid in _single_gpu_processes(gpu_index) if pid != os.getpid()]
    if foreign:
        raise RuntimeError(f"selected GPU is already occupied by PIDs {foreign}")

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
        raise RuntimeError("job archive must be under the declared archive root")
    if not _under(args.log_path, run_root / "logs"):
        raise RuntimeError("job log must be under the declared run-root logs directory")
    if args.out.exists() or args.archive_root.exists():
        raise RuntimeError("job output and archive paths must both be fresh")
    if not _under(args.data_root, Path("/mnt/data2/drtao")):
        raise RuntimeError("frozen data must be staged under /mnt/data2/drtao")
    for name, expected in {
        "PIDL_ARCHIVE_DIR": args.archive_root,
        "PIDL_LOG_PATH": args.log_path,
    }.items():
        value = os.environ.get(name)
        if not value or Path(value).resolve() != expected.resolve():
            raise RuntimeError(f"{name} must equal {expected}")
    for name in ("TMPDIR", "XDG_CACHE_HOME", "TORCH_EXTENSIONS_DIR"):
        value = os.environ.get(name)
        if not value or not _under(Path(value), run_root):
            raise RuntimeError(f"{name} must be task-owned under {run_root}")

    if not MATRIX_LOCK_PATH.is_file():
        raise RuntimeError("probabilistic-increment matrix lock is missing")
    if sha256_file(MATRIX_LOCK_PATH) != args.release_matrix_sha256:
        raise RuntimeError("matrix lock does not match owner-authorized hash")
    lock = json.loads(MATRIX_LOCK_PATH.read_text(encoding="utf-8"))
    validate_matrix_lock(lock)
    code_sha256 = {name: sha256_file(path) for name, path in locked_code_paths().items()}
    if code_sha256 != lock.get("code_sha256"):
        raise RuntimeError("runtime code does not match matrix code lock")
    authorization = load_release_authorization(
        args, lock, args.release_matrix_sha256, code_sha256
    )
    args.release_authorization_payload = authorization
    release_commit = authorization["release_commit"]
    repo = HERE.parent
    commit = _git_output(repo, "rev-parse", "HEAD")
    dirty = _git_output(repo, "status", "--short")
    if commit != "unavailable":
        if dirty:
            raise RuntimeError("training refuses a dirty Taobo checkout")
        if commit != release_commit:
            raise RuntimeError("Taobo HEAD does not match authorized release commit")
        args.runtime_source_mode = "clean_git_checkout"
        args.runtime_source_commit = commit
        args.snapshot_manifest_sha256 = None
    else:
        snapshot = repo / "RUN_PROVENANCE.txt"
        if _snapshot_commit(snapshot) != release_commit:
            raise RuntimeError("rsync snapshot does not match authorized release commit")
        args.runtime_source_mode = "verified_rsync_snapshot"
        args.runtime_source_commit = release_commit
        args.snapshot_manifest_sha256 = sha256_file(snapshot)
    verify_hash_manifest(args.data_root)


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
        "job_id": args.out.name,
        "heldout_trajectory_id": args.heldout,
        "seed": args.seed,
        "output_root": str(args.out),
        "archive_root": str(args.archive_root),
        "log_path": str(args.log_path),
        "launcher_session": args.launcher_session,
        "runner_pid": os.getpid(),
        "parent_pid": os.getppid(),
        "launch_time_utc": datetime.now(timezone.utc).isoformat(),
        "cwd": str(Path.cwd()),
        "argv": sys.argv,
        "release_commit": args.release_authorization_payload["release_commit"],
        "release_matrix_sha256": args.release_matrix_sha256,
        "release_authorization_sha256": args.release_authorization_sha256,
        "release_authorization": args.release_authorization_payload,
        "source_mode": args.runtime_source_mode,
        "runtime_source_commit": args.runtime_source_commit,
        "snapshot_manifest_sha256": args.snapshot_manifest_sha256,
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
        "git_status_short": _git_output(repo, "status", "--short"),
        "code_sha256": {
            name: sha256_file(path) if path.is_file() else "missing"
            for name, path in code_paths.items()
        },
        "reproducibility_level": "seeded_statistical_not_byte_deterministic",
    }


@dataclass(frozen=True)
class IncrementWindow:
    trajectory_index: int
    origin_cycle: int
    targets_first_hit: bool


@dataclass(frozen=True)
class BucketCalibration:
    gradient_scales: dict[str, torch.Tensor]
    raw_gradient_means: dict[str, torch.Tensor]
    normalized_gradient_means: dict[str, float]


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


def build_increment_windows(
    items: list[dict], context: int = CONTEXT
) -> tuple[list[IncrementWindow], list[IncrementWindow]]:
    event: list[IncrementWindow] = []
    ordinary: list[IncrementWindow] = []
    for trajectory_index, item in enumerate(items):
        stop = min(item["first_hit"], len(item["states"]))
        for origin in range(context, stop):
            target_cycle = origin + 1
            window = IncrementWindow(
                trajectory_index=trajectory_index,
                origin_cycle=origin,
                targets_first_hit=target_cycle == item["first_hit"],
            )
            (event if window.targets_first_hit else ordinary).append(window)
    if not event or not ordinary:
        raise ValueError("training split needs first-hit-target and ordinary windows")
    return event, ordinary


def choose_balanced_window(
    event: list[IncrementWindow],
    ordinary: list[IncrementWindow],
    step: int,
    rng: random.Random,
) -> IncrementWindow:
    bucket = event if step % 2 else ordinary
    trajectory_indices = sorted({window.trajectory_index for window in bucket})
    trajectory_index = rng.choice(trajectory_indices)
    candidates = [
        window for window in bucket if window.trajectory_index == trajectory_index
    ]
    return rng.choice(candidates)


def calibrate_mean_bucket_gradients(
    items: list[dict],
    event: list[IncrementWindow],
    ordinary: list[IncrementWindow],
    graph: dict[str, torch.Tensor],
    statistics,
    active_residual_scale: torch.Tensor,
) -> BucketCalibration:
    """Equalize persistence prediction-gradient norms for t+1 buckets."""
    area = graph["areas"].reshape(-1)
    raw: dict[str, torch.Tensor] = {}
    for name, windows in (("event", event), ("ordinary", ordinary)):
        trajectory_means = []
        for trajectory_index in sorted({window.trajectory_index for window in windows}):
            norms = []
            for window in (
                candidate
                for candidate in windows
                if candidate.trajectory_index == trajectory_index
            ):
                item = items[trajectory_index]
                prediction = (
                    item["states"][window.origin_cycle - 1]
                    .detach()
                    .clone()
                    .requires_grad_(True)
                )
                target = item["states"][window.origin_cycle]
                loss = normalized_field_loss(
                    prediction,
                    target,
                    area,
                    graph["edge_index"],
                    statistics,
                    active_residual_scale,
                ).total
                (gradient,) = torch.autograd.grad(loss, prediction)
                norms.append(torch.linalg.vector_norm(gradient).detach())
            trajectory_means.append(torch.stack(norms).mean())
        raw[name] = torch.stack(trajectory_means).mean().clamp_min(1.0e-8)
    normalized = {name: float((value / raw[name]).cpu()) for name, value in raw.items()}
    if not all(np.isfinite(value) and 0.99 <= value <= 1.01 for value in normalized.values()):
        raise ValueError("invalid t+1 bucket gradient calibration")
    return BucketCalibration(
        gradient_scales=raw,
        raw_gradient_means=raw,
        normalized_gradient_means=normalized,
    )


def area_weighted_mean(values: np.ndarray, areas: np.ndarray) -> float:
    return float(np.sum(values * areas) / np.sum(areas))


def increment_mae(
    prediction: np.ndarray,
    current: np.ndarray,
    target: np.ndarray,
    areas: np.ndarray,
) -> dict[str, float]:
    error = np.abs((prediction - current) - (target - current))
    return {
        f"{channel}_increment_mae": area_weighted_mean(error[:, index], areas)
        for index, channel in enumerate(CHANNELS)
    }


def predict_one(
    model: ProbabilisticIncrementMeshOperator,
    item: dict,
    origin: int,
    graph: dict[str, torch.Tensor],
    statistics,
):
    history = item["states"][origin - CONTEXT : origin]
    model.eval()
    with torch.no_grad():
        return model(history, graph, statistics, item["metadata"])


def evaluate_heldout(
    model: ProbabilisticIncrementMeshOperator,
    heldout: dict,
    graph: dict[str, torch.Tensor],
    graph_arrays: dict[str, np.ndarray],
    statistics,
    out: Path,
) -> None:
    areas = np.asarray(graph_arrays["areas"], dtype=np.float64)
    point_rows: list[dict] = []
    uncertainty_rows: list[dict] = []
    assets: dict[str, np.ndarray] = {
        "centroids": np.asarray(graph_arrays["centroids"], dtype=np.float32),
        "areas": areas,
        "residual_mean": statistics.residual_mean.cpu().numpy(),
        "residual_std": statistics.residual_std.cpu().numpy(),
    }
    selected = set(SELECTED_ORIGINS[heldout["trajectory_id"]])
    for origin in range(CONTEXT, heldout["first_hit"]):
        target_cycle = origin + 1
        current_tensor = heldout["states"][origin - 1]
        target_tensor = heldout["states"][origin]
        output = predict_one(model, heldout, origin, graph, statistics)
        lower, upper = normalized_laplace_interval(output, 0.90)
        target_normalized = normalized_increment_target(
            current_tensor, target_tensor, statistics
        )
        current = current_tensor.cpu().numpy()
        target = target_tensor.cpu().numpy()
        mean = output.mean_state.cpu().numpy()
        baselines = {
            method: baseline_rollout(heldout, origin, 1, statistics, method)[
                target_cycle
            ].cpu().numpy()
            for method in ("persistence", "constrained_linear")
        }
        for method, prediction in {"gno_increment": mean, **baselines}.items():
            point_rows.append(
                {
                    "trajectory_id": heldout["trajectory_id"],
                    "method": method,
                    "origin_cycle": origin,
                    "target_cycle": target_cycle,
                    "targets_first_hit": target_cycle == heldout["first_hit"],
                    **increment_mae(prediction, current, target, areas),
                    **field_metrics(prediction, target, areas),
                }
            )

        normalized_error = (
            target_normalized - output.normalized_location
        ).abs().cpu().numpy()
        normalized_scale = torch.exp(output.normalized_log_scale).cpu().numpy()
        lower_array = lower.cpu().numpy()
        upper_array = upper.cpu().numpy()
        target_array = target_normalized.cpu().numpy()
        log_scale_array = output.normalized_log_scale.cpu().numpy()
        for index, channel in enumerate(CHANNELS):
            nll = (
                normalized_error[:, index] / normalized_scale[:, index]
                + log_scale_array[:, index]
                + math.log(2.0)
            )
            covered = (
                (target_array[:, index] >= lower_array[:, index])
                & (target_array[:, index] <= upper_array[:, index])
            ).astype(np.float64)
            uncertainty_rows.append(
                {
                    "trajectory_id": heldout["trajectory_id"],
                    "origin_cycle": origin,
                    "target_cycle": target_cycle,
                    "channel": channel,
                    "area_weighted_laplace_nll": area_weighted_mean(nll, areas),
                    "uncalibrated_central_90_coverage": area_weighted_mean(covered, areas),
                    "area_weighted_normalized_interval_width": area_weighted_mean(
                        upper_array[:, index] - lower_array[:, index], areas
                    ),
                    "area_weighted_normalized_abs_error": area_weighted_mean(
                        normalized_error[:, index], areas
                    ),
                    "area_weighted_normalized_scale": area_weighted_mean(
                        normalized_scale[:, index], areas
                    ),
                    "coverage_claim": "uncalibrated_diagnostic_only",
                }
            )

        if origin in selected:
            key = f"origin_c{origin}__target_c{target_cycle}"
            assets[f"{key}__context"] = heldout["states"][
                origin - CONTEXT : origin
            ].cpu().numpy()
            assets[f"{key}__fem"] = target
            assets[f"{key}__mean"] = mean
            assets[f"{key}__normalized_location"] = output.normalized_location.cpu().numpy()
            assets[f"{key}__normalized_log_scale"] = log_scale_array
            assets[f"{key}__normalized_target"] = target_array
            for method, prediction in baselines.items():
                assets[f"{key}__{method}"] = prediction

    if any(row["origin_cycle"] >= heldout["first_hit"] for row in point_rows):
        raise AssertionError("post-hit origin entered heldout t+1 evaluation")
    if {row["origin_cycle"] for row in point_rows} & selected != selected:
        raise AssertionError("selected heldout origin missing")
    if not all(
        np.isfinite(value)
        for row in point_rows + uncertainty_rows
        for value in row.values()
        if isinstance(value, float)
    ):
        raise FloatingPointError("non-finite heldout metric")
    write_csv(out / "heldout_increment_metrics.csv", point_rows)
    write_csv(out / "heldout_uncertainty_metrics.csv", uncertainty_rows)
    np.savez_compressed(out / "selected_increment_fields.npz", **assets)


def train(args: argparse.Namespace) -> None:
    enforce_taobo_preflight(args)
    args.out.mkdir(parents=True, exist_ok=False)
    args.archive_root.mkdir(parents=True, exist_ok=False)
    shutil.copy2(args.release_authorization, args.out / "RELEASE_AUTHORIZATION.json")
    provenance = runtime_provenance(args)
    write_json(args.out / "RUN_PROVENANCE.json", provenance)
    write_json(
        args.out / "LAUNCH_RECEIPT.json",
        {
            "status": "runner_started_after_frozen_data_preflight",
            **CLAIMS,
            "training_complete": False,
            "archive_verified": False,
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
    event, ordinary = build_increment_windows(training)
    event_counts = {
        item["trajectory_id"]: sum(
            window.trajectory_index == index for window in event
        )
        for index, item in enumerate(training)
    }
    if set(event_counts.values()) != {1}:
        raise RuntimeError("each training trajectory must have one t+1 first-hit window")

    model = ProbabilisticIncrementMeshOperator(
        context=CONTEXT, hidden_dim=args.hidden
    ).to(device)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    if parameter_count != EXPECTED_PARAMETER_COUNT:
        raise ValueError(f"unexpected probabilistic increment model capacity: {parameter_count}")
    calibration = calibrate_mean_bucket_gradients(
        training, event, ordinary, graph, statistics, active_residual_scale
    )
    rng = random.Random(args.seed)
    history_rows: list[dict] = []
    started = time.perf_counter()

    model.set_mean_training()
    mean_optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=3.0e-4,
        weight_decay=1.0e-6,
    )
    for step in range(1, args.mean_steps + 1):
        window = choose_balanced_window(event, ordinary, step, rng)
        item = training[window.trajectory_index]
        history = item["states"][window.origin_cycle - CONTEXT : window.origin_cycle]
        target = item["states"][window.origin_cycle]
        mean_optimizer.zero_grad(set_to_none=True)
        output = model(history, graph, statistics, item["metadata"])
        field = normalized_field_loss(
            output.mean_state,
            target,
            graph["areas"].reshape(-1),
            graph["edge_index"],
            statistics,
            active_residual_scale,
        )
        bucket = "event" if window.targets_first_hit else "ordinary"
        loss = field.total / calibration.gradient_scales[bucket]
        if not torch.isfinite(loss):
            raise FloatingPointError(f"non-finite mean loss at step {step}")
        loss.backward()
        gradient_norm = clip_finite_gradients(model.parameters())
        mean_optimizer.step()
        if step == 1 or step % 100 == 0 or step == args.mean_steps:
            history_rows.append(
                {
                    "phase": "mean",
                    "step": step,
                    "sample_bucket": bucket,
                    "trajectory_id": item["trajectory_id"],
                    "origin_cycle": window.origin_cycle,
                    "loss": float(loss.detach().cpu()),
                    "gradient_norm": gradient_norm,
                    "elapsed_seconds": time.perf_counter() - started,
                }
            )

    model.set_scale_training()
    scale_optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=3.0e-4,
        weight_decay=1.0e-6,
    )
    frozen_mean_state = {
        name: parameter.detach().clone()
        for name, parameter in model.named_parameters()
        if not name.startswith("scale_decoder.")
    }
    for step in range(1, args.scale_steps + 1):
        window = choose_balanced_window(event, ordinary, step, rng)
        item = training[window.trajectory_index]
        history = item["states"][window.origin_cycle - CONTEXT : window.origin_cycle]
        target = item["states"][window.origin_cycle]
        scale_optimizer.zero_grad(set_to_none=True)
        output = model(history, graph, statistics, item["metadata"])
        scale = conditional_laplace_scale_loss(
            output, history[-1], target, graph["areas"], statistics
        )
        if not torch.isfinite(scale.total):
            raise FloatingPointError(f"non-finite scale loss at step {step}")
        scale.total.backward()
        gradient_norm = clip_finite_gradients(model.parameters())
        scale_optimizer.step()
        if step == 1 or step % 100 == 0 or step == args.scale_steps:
            history_rows.append(
                {
                    "phase": "scale",
                    "step": step,
                    "sample_bucket": "event" if window.targets_first_hit else "ordinary",
                    "trajectory_id": item["trajectory_id"],
                    "origin_cycle": window.origin_cycle,
                    "loss": float(scale.total.detach().cpu()),
                    "gradient_norm": gradient_norm,
                    "elapsed_seconds": time.perf_counter() - started,
                }
            )
    for name, parameter in model.named_parameters():
        if name in frozen_mean_state and not torch.equal(parameter.detach(), frozen_mean_state[name]):
            raise AssertionError(f"scale phase changed frozen point predictor: {name}")

    torch.save(
        {
            "model": model.state_dict(),
            "statistics": {
                name: getattr(statistics, name).cpu()
                for name in ("state_mean", "state_std", "residual_mean", "residual_std")
            },
            "active_residual_scale": active_residual_scale.cpu(),
            "args": vars(args),
        },
        args.out / "final_model.pt",
    )
    write_csv(args.out / "training_history.csv", history_rows)
    evaluate_heldout(model, heldout, graph, graph_arrays, statistics, args.out)
    write_json(
        args.out / "RUN_MANIFEST.json",
        {
            "status": "complete",
            "experiment_id": EXPERIMENT_ID,
            **CLAIMS,
            "job_id": args.out.name,
            "run_id": args.run_id,
            "heldout_trajectory_id": heldout["trajectory_id"],
            "training_trajectory_ids": [item["trajectory_id"] for item in training],
            "heldout_first_hit_used_in_training": False,
            "context": CONTEXT,
            "rollout": 1,
            "mean_steps": args.mean_steps,
            "scale_steps": args.scale_steps,
            "seed": args.seed,
            "parameter_count": parameter_count,
            "event_windows_per_training_trajectory": event_counts,
            "training_origins": "strictly_less_than_training_first_hit",
            "statistics": "trajectory_equal_pre_hit_first_and_second_moments",
            "sampling_contract": {
                "bucket": "alternate_first_hit_target_and_ordinary",
                "trajectory": "uniform_within_bucket",
                "origin": "uniform_within_trajectory_and_bucket",
                "post_hit_origins": 0,
            },
            "dataset_id": manifest["dataset_id"],
            "dataset_manifest_sha256": sha256_file(args.data_root / "RUN_MANIFEST.json"),
            "dataset_hash_file_sha256": sha256_file(args.data_root / "HASHES.sha256"),
            "uncertainty_semantics": "uncalibrated_conditional_laplace_scale",
            "bucket_gradient_scales": {
                name: float(value.cpu()) for name, value in calibration.gradient_scales.items()
            },
            "release_authorization_sha256": args.release_authorization_sha256,
            "release_authorization": args.release_authorization_payload,
            "provenance": provenance,
            "required_job_payloads": sorted(EXPECTED_JOB_PAYLOADS),
        },
    )
    complete_receipt = {
        "status": "complete",
        **CLAIMS,
        "training_complete": True,
        "archive_verified": True,
        "experiment_id": EXPERIMENT_ID,
        "run_id": args.run_id,
        "job_id": args.out.name,
        "heldout_trajectory_id": args.heldout,
        "seed": args.seed,
        "provenance": provenance,
        "release_authorization_sha256": args.release_authorization_sha256,
        "release_authorization": args.release_authorization_payload,
        "run_manifest_sha256": sha256_file(args.out / "RUN_MANIFEST.json"),
    }
    write_json(
        args.out / "LAUNCH_RECEIPT.json",
        {
            **complete_receipt,
            "status": "outputs_complete_archive_pending",
            "archive_verified": False,
        },
    )
    finalize_completed_archive(
        args.out, args.archive_root, complete_receipt, EXPECTED_JOB_PAYLOADS
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--heldout", choices=tuple(SELECTED_ORIGINS), required=True)
    parser.add_argument("--seed", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--mean-steps", type=int, default=MEAN_STEPS)
    parser.add_argument("--scale-steps", type=int, default=SCALE_STEPS)
    parser.add_argument("--hidden", type=int, default=HIDDEN_DIM)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--producer", choices=("taobo",), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--log-path", type=Path, required=True)
    parser.add_argument("--launcher-session", required=True)
    parser.add_argument("--release-matrix-sha256", required=True)
    parser.add_argument("--release-authorization", type=Path, required=True)
    parser.add_argument("--release-authorization-sha256", required=True)
    args = parser.parse_args()
    if (
        args.mean_steps != MEAN_STEPS
        or args.scale_steps != SCALE_STEPS
        or args.hidden != HIDDEN_DIM
    ):
        parser.error("v1 hyperparameters are frozen at mean=3000, scale=500, hidden=96")
    return args


if __name__ == "__main__":
    train(parse_args())
