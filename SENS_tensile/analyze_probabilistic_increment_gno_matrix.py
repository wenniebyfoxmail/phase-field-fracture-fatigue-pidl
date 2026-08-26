#!/usr/bin/env python3
"""Fail-closed analysis of the frozen Hard5 probabilistic-increment 3x3 matrix."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np


EXPERIMENT_ID = "hard5_probabilistic_increment_gno_v1_20260827"
DATASET_ID = "hard5_loao_fem_states_v1"
DATASET_MANIFEST_SHA256 = "9267a102a38375ebc815404a5ae81b2d3b23622448b5b178a2c4c1a5696e202a"
DATASET_HASH_FILE_SHA256 = "7bff035eaa618a7517335a3adb436e14d8bf606c6fa4e202497355518e82a55e"
FOLDS = ("hard5_u011", "hard5_u012", "hard5_u013")
SEEDS = (1, 2, 3)
FIRST_HITS = {"hard5_u011": 122, "hard5_u012": 83, "hard5_u013": 59}
SELECTED_ORIGINS = {
    "hard5_u011": (20, 40, 60, 120),
    "hard5_u012": (20, 40, 60, 80),
    "hard5_u013": (20, 30, 45, 58),
}
CHANNELS = ("damage", "alpha_bar", "fatigue_f", "log10_psi_raw")
METHODS = ("gno_increment", "persistence", "constrained_linear")
CLAIMS = {
    "claim_class": "processed_griphfith_archive_imitation_only",
    "teacher_qualified": False,
    "physics_loss_weight": 0.0,
    "physical_validation": False,
    "uncertainty_claim": "uncalibrated_diagnostic_only",
}
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"empty table: {path}")
    return rows


def finite_float(value: object, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"non-numeric {label}: {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError(f"non-finite {label}: {value!r}")
    return result


def exact_int(value: object, label: str) -> int:
    result = finite_float(value, label)
    if result != int(result):
        raise ValueError(f"non-integral {label}: {value!r}")
    return int(result)


def median(values: list[float]) -> float:
    if not values:
        raise ValueError("cannot aggregate empty values")
    return float(np.median(np.asarray(values, dtype=np.float64)))


def validate_claims(payload: dict, source: Path) -> None:
    for key, expected in CLAIMS.items():
        if payload.get(key) != expected:
            raise ValueError(f"claim mismatch in {source}: {key}")


def validate_lock(lock: dict) -> None:
    if (
        lock.get("schema_version") != "hard5_probabilistic_increment_matrix_lock_v1"
        or lock.get("experiment_id") != EXPERIMENT_ID
        or lock.get("status") != "frozen_pending_external_release_authorization"
    ):
        raise ValueError("matrix schema/experiment/status mismatch")
    dataset = lock.get("dataset", {})
    matrix = lock.get("matrix", {})
    if (
        dataset.get("dataset_id") != DATASET_ID
        or dataset.get("manifest_sha256") != DATASET_MANIFEST_SHA256
        or dataset.get("hash_file_sha256") != DATASET_HASH_FILE_SHA256
        or set(dataset.get("trajectory_ids", [])) != set(FOLDS)
    ):
        raise ValueError("matrix dataset contract mismatch")
    if (
        matrix.get("folds") != sorted(FOLDS)
        or matrix.get("seeds") != list(SEEDS)
        or matrix.get("job_count") != 9
        or matrix.get("producer") != "taobo_only"
    ):
        raise ValueError("matrix job contract mismatch")
    if set(lock.get("required_job_payloads", [])) != EXPECTED_JOB_PAYLOADS:
        raise ValueError("matrix payload contract mismatch")


def validate_authorization(path: Path, expected_sha: str, lock: dict, lock_sha: str) -> dict:
    if not path.is_file() or sha256_file(path) != expected_sha:
        raise ValueError("release authorization hash mismatch")
    authorization = read_json(path)
    expected = {
        "schema_version": "hard5_probabilistic_increment_release_authorization_v1",
        "authorization_status": "AUTHORIZED",
        "experiment_id": EXPERIMENT_ID,
        "matrix_experiment_id": EXPERIMENT_ID,
        "matrix_lock_sha256": lock_sha,
        "dataset_manifest_sha256": DATASET_MANIFEST_SHA256,
        "dataset_hash_file_sha256": DATASET_HASH_FILE_SHA256,
        "authorization_scope": "hard5_three_fold_three_seed_probabilistic_increment_gno",
        "producer": "taobo",
        "max_gpu_count": 1,
    }
    for key, value in expected.items():
        if authorization.get(key) != value:
            raise ValueError(f"release authorization mismatch for {key}")
    commit = authorization.get("release_commit", "")
    review = authorization.get("independent_review", {})
    if (
        not re.fullmatch(r"[0-9a-f]{40}", commit)
        or review.get("verdict") != "PASS"
        or review.get("reviewed_commit") != commit
        or not re.fullmatch(r"[0-9a-f]{64}", review.get("review_note_sha256", ""))
    ):
        raise ValueError("release authorization lacks locked independent PASS")
    if authorization.get("code_sha256") != lock.get("code_sha256"):
        raise ValueError("authorization code hashes mismatch")
    expected_jobs = {
        (f"{fold}_s{seed}", fold, seed) for fold in FOLDS for seed in SEEDS
    }
    jobs = authorization.get("jobs", [])
    actual_jobs = {
        (job.get("job_id"), job.get("heldout"), job.get("seed"))
        for job in jobs
        if isinstance(job, dict)
    }
    if len(jobs) != 9 or actual_jobs != expected_jobs:
        raise ValueError("authorization job matrix mismatch")
    if authorization.get("claims") != CLAIMS:
        raise ValueError("authorization claim boundary mismatch")
    return authorization


def validate_payloads(job_dir: Path, receipt: dict) -> None:
    actual = {
        str(path.relative_to(job_dir)): sha256_file(path)
        for path in job_dir.rglob("*")
        if path.is_file() and path.name != "LAUNCH_RECEIPT.json"
    }
    payload = receipt.get("payload_sha256")
    if (
        set(actual) != EXPECTED_JOB_PAYLOADS
        or not isinstance(payload, dict)
        or set(payload) != EXPECTED_JOB_PAYLOADS
        or actual != payload
    ):
        raise ValueError(f"payload file set or hash mismatch: {job_dir}")


def validate_point_rows(path: Path, fold: str) -> list[dict]:
    rows = read_csv(path)
    expected_origins = set(range(3, FIRST_HITS[fold]))
    counts: Counter = Counter()
    clean: list[dict] = []
    for row in rows:
        if row.get("trajectory_id") != fold or row.get("method") not in METHODS:
            raise ValueError(f"point identity/method mismatch: {path}")
        origin = exact_int(row.get("origin_cycle"), "origin_cycle")
        target = exact_int(row.get("target_cycle"), "target_cycle")
        if origin not in expected_origins or target != origin + 1:
            raise ValueError(f"point t+1 opportunity mismatch: {path}")
        values = {
            channel: finite_float(
                row.get(f"{channel}_increment_mae"), f"{fold}/{origin}/{channel}"
            )
            for channel in CHANNELS
        }
        counts[(row["method"], origin)] += 1
        clean.append({"method": row["method"], "origin": origin, **values})
    expected = {(method, origin) for method in METHODS for origin in expected_origins}
    if set(counts) != expected or any(count != 1 for count in counts.values()):
        raise ValueError(f"point rows missing, duplicate, or extra: {path}")
    return clean


def validate_uncertainty_rows(path: Path, fold: str) -> list[dict]:
    rows = read_csv(path)
    expected_origins = set(range(3, FIRST_HITS[fold]))
    counts: Counter = Counter()
    clean: list[dict] = []
    fields = (
        "area_weighted_laplace_nll",
        "uncalibrated_central_90_coverage",
        "area_weighted_normalized_interval_width",
        "area_weighted_normalized_abs_error",
        "area_weighted_normalized_scale",
    )
    for row in rows:
        if (
            row.get("trajectory_id") != fold
            or row.get("channel") not in CHANNELS
            or row.get("coverage_claim") != "uncalibrated_diagnostic_only"
        ):
            raise ValueError(f"uncertainty identity/claim mismatch: {path}")
        origin = exact_int(row.get("origin_cycle"), "origin_cycle")
        target = exact_int(row.get("target_cycle"), "target_cycle")
        if origin not in expected_origins or target != origin + 1:
            raise ValueError(f"uncertainty t+1 opportunity mismatch: {path}")
        values = {field: finite_float(row.get(field), field) for field in fields}
        coverage = values["uncalibrated_central_90_coverage"]
        if not 0.0 <= coverage <= 1.0:
            raise ValueError(f"coverage outside [0,1]: {path}")
        counts[(row["channel"], origin)] += 1
        clean.append({"channel": row["channel"], "origin": origin, **values})
    expected = {(channel, origin) for channel in CHANNELS for origin in expected_origins}
    if set(counts) != expected or any(count != 1 for count in counts.values()):
        raise ValueError(f"uncertainty rows missing, duplicate, or extra: {path}")
    return clean


def weighted_correlation(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float:
    weights = weights / weights.sum()
    x_centered = x - np.sum(weights * x)
    y_centered = y - np.sum(weights * y)
    denominator = math.sqrt(
        float(np.sum(weights * x_centered**2) * np.sum(weights * y_centered**2))
    )
    return float(np.sum(weights * x_centered * y_centered) / denominator) if denominator else 0.0


def risk_at_coverage(error: np.ndarray, scale: np.ndarray, areas: np.ndarray, coverage: float) -> float:
    order = np.argsort(scale, kind="stable")
    cumulative = np.cumsum(areas[order])
    keep = cumulative <= coverage * areas.sum()
    if not np.any(keep):
        keep[0] = True
    selected = order[keep]
    return float(np.sum(error[selected] * areas[selected]) / np.sum(areas[selected]))


def validate_selected_npz(path: Path, fold: str) -> dict[int, dict[str, np.ndarray]]:
    with np.load(path, allow_pickle=False) as archive:
        arrays = {name: np.asarray(archive[name]) for name in archive.files}
    areas = arrays.get("areas")
    if areas is None or areas.ndim != 1 or np.any(~np.isfinite(areas)) or np.any(areas <= 0):
        raise ValueError(f"invalid selected-field areas: {path}")
    expected_global = {"centroids", "areas", "residual_mean", "residual_std"}
    expected = set(expected_global)
    result: dict[int, dict[str, np.ndarray]] = {}
    suffixes = (
        "context",
        "fem",
        "mean",
        "normalized_location",
        "normalized_log_scale",
        "normalized_target",
        "persistence",
        "constrained_linear",
    )
    for origin in SELECTED_ORIGINS[fold]:
        prefix = f"origin_c{origin}__target_c{origin + 1}"
        keys = {suffix: f"{prefix}__{suffix}" for suffix in suffixes}
        expected.update(keys.values())
        result[origin] = {suffix: arrays[key] for suffix, key in keys.items()}
        for suffix, value in result[origin].items():
            if np.any(~np.isfinite(value)):
                raise ValueError(f"non-finite selected field {fold}/{origin}/{suffix}")
        if result[origin]["normalized_location"].shape != (len(areas), 4):
            raise ValueError(f"selected-field shape mismatch: {fold}/{origin}")
        expected_shapes = {
            "context": (3, len(areas), 4),
            "fem": (len(areas), 4),
            "mean": (len(areas), 4),
            "normalized_location": (len(areas), 4),
            "normalized_log_scale": (len(areas), 4),
            "normalized_target": (len(areas), 4),
            "persistence": (len(areas), 4),
            "constrained_linear": (len(areas), 4),
        }
        if any(
            result[origin][suffix].shape != shape
            for suffix, shape in expected_shapes.items()
        ):
            raise ValueError(f"selected-field shape mismatch: {fold}/{origin}")
    if set(arrays) != expected:
        raise ValueError(f"selected-field key set mismatch: {path}")
    result[-1] = {"areas": areas}
    return result


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"refusing empty aggregate table: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def analyze(args: argparse.Namespace) -> dict:
    if sha256_file(args.matrix_lock) != args.matrix_lock_sha256:
        raise ValueError("matrix lock hash mismatch")
    lock = read_json(args.matrix_lock)
    validate_lock(lock)
    authorization = validate_authorization(
        args.release_authorization,
        args.release_authorization_sha256,
        lock,
        args.matrix_lock_sha256,
    )
    run_id = authorization.get("run_id")
    point_by_job: dict[tuple[str, int], list[dict]] = {}
    uncertainty_by_job: dict[tuple[str, int], list[dict]] = {}
    selected_by_job: dict[tuple[str, int], dict[int, dict[str, np.ndarray]]] = {}
    for fold in FOLDS:
        for seed in SEEDS:
            job_id = f"{fold}_s{seed}"
            job_dir = args.archive_root / job_id
            receipt = read_json(job_dir / "LAUNCH_RECEIPT.json")
            validate_claims(receipt, job_dir / "LAUNCH_RECEIPT.json")
            if (
                receipt.get("status") != "complete"
                or receipt.get("training_complete") is not True
                or receipt.get("archive_verified") is not True
                or receipt.get("experiment_id") != EXPERIMENT_ID
                or receipt.get("run_id") != run_id
                or receipt.get("job_id") != job_id
                or receipt.get("heldout_trajectory_id") != fold
                or receipt.get("seed") != seed
                or receipt.get("release_authorization_sha256")
                != args.release_authorization_sha256
                or receipt.get("release_authorization") != authorization
            ):
                raise ValueError(f"incomplete or mismatched receipt: {job_dir}")
            validate_payloads(job_dir, receipt)
            if sha256_file(job_dir / "RELEASE_AUTHORIZATION.json") != args.release_authorization_sha256:
                raise ValueError(f"job authorization differs: {job_dir}")
            provenance = read_json(job_dir / "RUN_PROVENANCE.json")
            if (
                provenance.get("producer") != "taobo"
                or provenance.get("producer_id") != "taobo-172.16.100.2"
                or provenance.get("user") != "drtao"
                or provenance.get("release_commit") != authorization["release_commit"]
                or provenance.get("release_matrix_sha256") != args.matrix_lock_sha256
                or provenance.get("release_authorization_sha256")
                != args.release_authorization_sha256
                or provenance.get("runtime_source_commit") != authorization["release_commit"]
                or provenance.get("code_sha256", {}).get("matrix_lock")
                != args.matrix_lock_sha256
                or provenance.get("release_authorization") != authorization
            ):
                raise ValueError(f"runtime provenance mismatch: {job_dir}")
            for name, expected_hash in lock.get("code_sha256", {}).items():
                if provenance.get("code_sha256", {}).get(name) != expected_hash:
                    raise ValueError(f"runtime code hash mismatch {name}: {job_dir}")
            manifest = read_json(job_dir / "RUN_MANIFEST.json")
            validate_claims(manifest, job_dir / "RUN_MANIFEST.json")
            if (
                manifest.get("status") != "complete"
                or manifest.get("experiment_id") != EXPERIMENT_ID
                or manifest.get("job_id") != job_id
                or manifest.get("run_id") != run_id
                or manifest.get("heldout_trajectory_id") != fold
                or set(manifest.get("training_trajectory_ids", [])) != set(FOLDS) - {fold}
                or manifest.get("heldout_first_hit_used_in_training") is not False
                or manifest.get("context") != 3
                or manifest.get("rollout") != 1
                or manifest.get("mean_steps") != 3000
                or manifest.get("scale_steps") != 500
                or manifest.get("seed") != seed
                or manifest.get("parameter_count") != 367400
                or manifest.get("dataset_id") != DATASET_ID
                or manifest.get("dataset_manifest_sha256") != DATASET_MANIFEST_SHA256
                or manifest.get("dataset_hash_file_sha256") != DATASET_HASH_FILE_SHA256
                or set(manifest.get("required_job_payloads", [])) != EXPECTED_JOB_PAYLOADS
                or manifest.get("release_authorization") != authorization
                or manifest.get("provenance") != provenance
            ):
                raise ValueError(f"run manifest contract mismatch: {job_dir}")
            sampling = manifest.get("sampling_contract", {})
            if sampling.get("post_hit_origins") != 0 or set(
                manifest.get("event_windows_per_training_trajectory", {}).values()
            ) != {1}:
                raise ValueError(f"training origin/sampling contract mismatch: {job_dir}")
            if receipt.get("run_manifest_sha256") != sha256_file(job_dir / "RUN_MANIFEST.json"):
                raise ValueError(f"run manifest receipt hash mismatch: {job_dir}")
            point_by_job[(fold, seed)] = validate_point_rows(
                job_dir / "heldout_increment_metrics.csv", fold
            )
            uncertainty_by_job[(fold, seed)] = validate_uncertainty_rows(
                job_dir / "heldout_uncertainty_metrics.csv", fold
            )
            selected_by_job[(fold, seed)] = validate_selected_npz(
                job_dir / "selected_increment_fields.npz", fold
            )

    point_rows: list[dict] = []
    for channel in CHANNELS:
        method_seed_values: dict[str, list[float]] = {method: [] for method in METHODS}
        for seed in SEEDS:
            rows = point_by_job[("hard5_u012", seed)]
            for method in METHODS:
                values = [
                    row[channel]
                    for row in rows
                    if row["method"] == method
                    and row["origin"] in SELECTED_ORIGINS["hard5_u012"]
                ]
                if len(values) != 4:
                    raise ValueError(f"U0.12 fixed origin set missing: {seed}/{method}/{channel}")
                method_seed_values[method].append(median(values))
        aggregate = {method: median(values) for method, values in method_seed_values.items()}
        point_rows.append(
            {
                "channel": channel,
                "gno_increment_mae": aggregate["gno_increment"],
                "persistence_mae": aggregate["persistence"],
                "constrained_linear_mae": aggregate["constrained_linear"],
                "gno_better_than_persistence": aggregate["gno_increment"] < aggregate["persistence"],
                "gno_better_than_constrained_linear": aggregate["gno_increment"] < aggregate["constrained_linear"],
                "within_10pct_of_persistence": aggregate["gno_increment"] <= 1.10 * aggregate["persistence"],
            }
        )
    better_persistence = sum(row["gno_better_than_persistence"] for row in point_rows)
    better_linear = sum(row["gno_better_than_constrained_linear"] for row in point_rows)
    no_large_regression = all(row["within_10pct_of_persistence"] for row in point_rows)
    point_gate = better_persistence >= 3 and better_linear >= 2 and no_large_regression

    diagnostic_rows: list[dict] = []
    for fold in FOLDS:
        for origin in SELECTED_ORIGINS[fold]:
            areas = selected_by_job[(fold, 1)][-1]["areas"]
            for channel_index, channel in enumerate(CHANNELS):
                locations, scales, targets = [], [], []
                correlations, risks = [], {1.0: [], 0.9: [], 0.75: [], 0.5: []}
                for seed in SEEDS:
                    asset = selected_by_job[(fold, seed)][origin]
                    location = asset["normalized_location"][:, channel_index]
                    scale = np.exp(asset["normalized_log_scale"][:, channel_index])
                    target = asset["normalized_target"][:, channel_index]
                    error = np.abs(target - location)
                    correlations.append(weighted_correlation(scale, error, areas))
                    for coverage in risks:
                        risks[coverage].append(risk_at_coverage(error, scale, areas, coverage))
                    locations.append(location)
                    scales.append(scale)
                    targets.append(target)
                if not all(np.allclose(targets[0], target) for target in targets[1:]):
                    raise ValueError(f"FEM normalized target differs across seeds: {fold}/{origin}")
                location_stack = np.stack(locations)
                scale_stack = np.stack(scales)
                total_variance = 2.0 * np.mean(scale_stack**2, axis=0) + np.var(
                    location_stack, axis=0, ddof=0
                )
                diagnostic_rows.append(
                    {
                        "trajectory_id": fold,
                        "origin_cycle": origin,
                        "channel": channel,
                        "median_seed_area_weighted_scale_error_correlation": median(correlations),
                        "median_seed_normalized_risk_at_100pct_area": median(risks[1.0]),
                        "median_seed_normalized_risk_at_90pct_area": median(risks[0.9]),
                        "median_seed_normalized_risk_at_75pct_area": median(risks[0.75]),
                        "median_seed_normalized_risk_at_50pct_area": median(risks[0.5]),
                        "area_weighted_ensemble_location_variance": float(
                            np.sum(np.var(location_stack, axis=0) * areas) / areas.sum()
                        ),
                        "area_weighted_total_predictive_variance": float(
                            np.sum(total_variance * areas) / areas.sum()
                        ),
                        "uncertainty_claim": "uncalibrated_diagnostic_only",
                    }
                )
    for row in point_rows + diagnostic_rows:
        for value in row.values():
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("non-finite aggregate output")
    args.out.mkdir(parents=True, exist_ok=False)
    write_csv(args.out / "u012_fixed_point_gate.csv", point_rows)
    write_csv(args.out / "selected_uncertainty_diagnostics.csv", diagnostic_rows)
    decision = {
        "experiment_id": EXPERIMENT_ID,
        **CLAIMS,
        "status": "PASS" if point_gate else "FAIL",
        "point_gate_pass": point_gate,
        "u012_development_fold_only": True,
        "reduction": "median_four_fixed_origins_within_seed_then_median_three_seeds",
        "gno_better_than_persistence_channels": better_persistence,
        "gno_better_than_constrained_linear_channels": better_linear,
        "no_channel_more_than_10pct_worse_than_persistence": no_large_regression,
        "uncertainty_can_rescue_point_gate": False,
        "matrix_lock_sha256": args.matrix_lock_sha256,
        "release_authorization_sha256": args.release_authorization_sha256,
        "release_commit": authorization["release_commit"],
        "run_id": run_id,
    }
    (args.out / "decision.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return decision


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--matrix-lock", type=Path, required=True)
    parser.add_argument("--matrix-lock-sha256", required=True)
    parser.add_argument("--release-authorization", type=Path, required=True)
    parser.add_argument("--release-authorization-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(analyze(parse_args()), indent=2, allow_nan=False))
