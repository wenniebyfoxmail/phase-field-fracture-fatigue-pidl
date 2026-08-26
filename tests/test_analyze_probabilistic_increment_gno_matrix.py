from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "SENS_tensile"))

import analyze_probabilistic_increment_gno_matrix as analyzer  # noqa: E402


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def make_matrix(tmp_path: Path, *, gno_factor: float = 0.5):
    archive_root = tmp_path / "archive"
    archive_root.mkdir()
    out = tmp_path / "analysis"
    code_sha = {"runner": "1" * 64, "model": "2" * 64}
    lock = {
        "schema_version": "hard5_probabilistic_increment_matrix_lock_v1",
        "experiment_id": analyzer.EXPERIMENT_ID,
        "status": "frozen_pending_external_release_authorization",
        "dataset": {
            "dataset_id": analyzer.DATASET_ID,
            "manifest_sha256": analyzer.DATASET_MANIFEST_SHA256,
            "hash_file_sha256": analyzer.DATASET_HASH_FILE_SHA256,
            "trajectory_ids": list(analyzer.FOLDS),
        },
        "matrix": {
            "folds": sorted(analyzer.FOLDS),
            "seeds": list(analyzer.SEEDS),
            "job_count": 9,
            "producer": "taobo_only",
        },
        "required_job_payloads": sorted(analyzer.EXPECTED_JOB_PAYLOADS),
        "code_sha256": code_sha,
    }
    lock_path = tmp_path / "matrix.json"
    lock_path.write_text(json.dumps(lock, sort_keys=True) + "\n")
    lock_sha = analyzer.sha256_file(lock_path)
    commit = "a" * 40
    authorization = {
        "schema_version": "hard5_probabilistic_increment_release_authorization_v1",
        "authorization_status": "AUTHORIZED",
        "experiment_id": analyzer.EXPERIMENT_ID,
        "matrix_experiment_id": analyzer.EXPERIMENT_ID,
        "run_id": "pf_prob_increment_test",
        "matrix_lock_sha256": lock_sha,
        "dataset_manifest_sha256": analyzer.DATASET_MANIFEST_SHA256,
        "dataset_hash_file_sha256": analyzer.DATASET_HASH_FILE_SHA256,
        "authorization_scope": "hard5_three_fold_three_seed_probabilistic_increment_gno",
        "producer": "taobo",
        "max_gpu_count": 1,
        "release_commit": commit,
        "code_sha256": code_sha,
        "independent_review": {
            "verdict": "PASS",
            "reviewed_commit": commit,
            "review_note_sha256": "b" * 64,
        },
        "jobs": [
            {"job_id": f"{fold}_s{seed}", "heldout": fold, "seed": seed}
            for fold in analyzer.FOLDS
            for seed in analyzer.SEEDS
        ],
        "claims": analyzer.CLAIMS,
    }
    auth_path = tmp_path / "RELEASE_AUTHORIZATION.json"
    auth_path.write_text(json.dumps(authorization, sort_keys=True) + "\n")
    auth_sha = analyzer.sha256_file(auth_path)

    for fold in analyzer.FOLDS:
        for seed in analyzer.SEEDS:
            job_id = f"{fold}_s{seed}"
            job = archive_root / job_id
            job.mkdir()
            (job / "RELEASE_AUTHORIZATION.json").write_bytes(auth_path.read_bytes())
            (job / "final_model.pt").write_bytes(b"model")
            write_csv(job / "training_history.csv", [{"phase": "mean", "loss": 1.0}])
            point_rows = []
            for origin in range(3, analyzer.FIRST_HITS[fold]):
                for method, factor in (
                    ("gno_increment", gno_factor),
                    ("persistence", 1.0),
                    ("constrained_linear", 0.8),
                ):
                    point_rows.append(
                        {
                            "trajectory_id": fold,
                            "method": method,
                            "origin_cycle": origin,
                            "target_cycle": origin + 1,
                            **{
                                f"{channel}_increment_mae": factor * (index + 1)
                                for index, channel in enumerate(analyzer.CHANNELS)
                            },
                        }
                    )
            write_csv(job / "heldout_increment_metrics.csv", point_rows)
            uncertainty_rows = []
            for origin in range(3, analyzer.FIRST_HITS[fold]):
                for channel in analyzer.CHANNELS:
                    uncertainty_rows.append(
                        {
                            "trajectory_id": fold,
                            "origin_cycle": origin,
                            "target_cycle": origin + 1,
                            "channel": channel,
                            "area_weighted_laplace_nll": 0.2,
                            "uncalibrated_central_90_coverage": 0.85,
                            "area_weighted_normalized_interval_width": 0.4,
                            "area_weighted_normalized_abs_error": 0.1,
                            "area_weighted_normalized_scale": 0.2,
                            "coverage_claim": "uncalibrated_diagnostic_only",
                        }
                    )
            write_csv(job / "heldout_uncertainty_metrics.csv", uncertainty_rows)
            arrays = {
                "centroids": np.zeros((4, 2), dtype=np.float32),
                "areas": np.asarray([1.0, 2.0, 1.0, 2.0]),
                "residual_mean": np.zeros((1, 4), dtype=np.float32),
                "residual_std": np.ones((1, 4), dtype=np.float32),
            }
            for origin in analyzer.SELECTED_ORIGINS[fold]:
                prefix = f"origin_c{origin}__target_c{origin + 1}"
                target = np.tile(np.arange(4, dtype=np.float32)[:, None], (1, 4)) / 10
                location = target + (seed * 0.005)
                arrays.update(
                    {
                        f"{prefix}__context": np.zeros((3, 4, 4), dtype=np.float32),
                        f"{prefix}__fem": np.zeros((4, 4), dtype=np.float32),
                        f"{prefix}__mean": np.zeros((4, 4), dtype=np.float32),
                        f"{prefix}__normalized_location": location,
                        f"{prefix}__normalized_log_scale": np.log(
                            np.tile(np.asarray([0.1, 0.2, 0.3, 0.4])[:, None], (1, 4))
                        ),
                        f"{prefix}__normalized_target": target,
                        f"{prefix}__persistence": np.zeros((4, 4), dtype=np.float32),
                        f"{prefix}__constrained_linear": np.zeros((4, 4), dtype=np.float32),
                    }
                )
            np.savez_compressed(job / "selected_increment_fields.npz", **arrays)
            provenance = {
                "producer": "taobo",
                "producer_id": "taobo-172.16.100.2",
                "hostname": "GPUServer8",
                "user": "drtao",
                "cuda_visible_devices": "3",
                "gpu_name": "NVIDIA GeForce RTX 4090",
                "launcher_session": "systemd:pf_prob_increment_test",
                "release_commit": commit,
                "runtime_source_commit": commit,
                "source_mode": "clean_git_checkout",
                "git_commit": commit,
                "git_status_short": "",
                "snapshot_manifest_sha256": None,
                "release_matrix_sha256": lock_sha,
                "release_authorization_sha256": auth_sha,
                "release_authorization": authorization,
                "code_sha256": {**code_sha, "matrix_lock": lock_sha},
            }
            (job / "RUN_PROVENANCE.json").write_text(json.dumps(provenance) + "\n")
            manifest = {
                "status": "complete",
                **analyzer.CLAIMS,
                "experiment_id": analyzer.EXPERIMENT_ID,
                "job_id": job_id,
                "run_id": authorization["run_id"],
                "heldout_trajectory_id": fold,
                "training_trajectory_ids": list(set(analyzer.FOLDS) - {fold}),
                "heldout_first_hit_used_in_training": False,
                "context": 3,
                "rollout": 1,
                "mean_steps": 3000,
                "scale_steps": 500,
                "seed": seed,
                "parameter_count": 367400,
                "dataset_id": analyzer.DATASET_ID,
                "dataset_manifest_sha256": analyzer.DATASET_MANIFEST_SHA256,
                "dataset_hash_file_sha256": analyzer.DATASET_HASH_FILE_SHA256,
                "required_job_payloads": sorted(analyzer.EXPECTED_JOB_PAYLOADS),
                "event_windows_per_training_trajectory": {
                    training: 1 for training in set(analyzer.FOLDS) - {fold}
                },
                "sampling_contract": {"post_hit_origins": 0},
                "release_authorization": authorization,
                "provenance": provenance,
            }
            (job / "RUN_MANIFEST.json").write_text(json.dumps(manifest) + "\n")
            payload = {
                str(path.relative_to(job)): analyzer.sha256_file(path)
                for path in job.rglob("*")
                if path.is_file()
            }
            receipt = {
                "status": "complete",
                **analyzer.CLAIMS,
                "training_complete": True,
                "archive_verified": True,
                "experiment_id": analyzer.EXPERIMENT_ID,
                "run_id": authorization["run_id"],
                "job_id": job_id,
                "heldout_trajectory_id": fold,
                "seed": seed,
                "release_authorization_sha256": auth_sha,
                "release_authorization": authorization,
                "provenance": provenance,
                "run_manifest_sha256": analyzer.sha256_file(job / "RUN_MANIFEST.json"),
                "payload_sha256": payload,
            }
            (job / "LAUNCH_RECEIPT.json").write_text(json.dumps(receipt) + "\n")
    args = SimpleNamespace(
        archive_root=archive_root,
        matrix_lock=lock_path,
        matrix_lock_sha256=lock_sha,
        release_authorization=auth_path,
        release_authorization_sha256=auth_sha,
        out=out,
    )
    return args


def refresh_job_receipt(job: Path) -> None:
    receipt_path = job / "LAUNCH_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["run_manifest_sha256"] = analyzer.sha256_file(job / "RUN_MANIFEST.json")
    receipt["payload_sha256"] = {
        str(path.relative_to(job)): analyzer.sha256_file(path)
        for path in job.rglob("*")
        if path.is_file() and path.name != "LAUNCH_RECEIPT.json"
    }
    receipt_path.write_text(json.dumps(receipt) + "\n")


def test_complete_matrix_passes_fixed_u012_point_gate_and_writes_uncertainty(tmp_path):
    args = make_matrix(tmp_path)
    decision = analyzer.analyze(args)
    assert decision["status"] == "PASS"
    assert decision["gno_better_than_persistence_channels"] == 4
    assert decision["gno_better_than_constrained_linear_channels"] == 4
    with (args.out / "selected_uncertainty_diagnostics.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 3 * 4 * 4
    assert {row["uncertainty_claim"] for row in rows} == {
        "uncalibrated_diagnostic_only"
    }


def test_point_gate_failure_is_not_rescued_by_uncertainty(tmp_path):
    args = make_matrix(tmp_path, gno_factor=1.2)
    decision = analyzer.analyze(args)
    assert decision["status"] == "FAIL"
    assert decision["uncertainty_can_rescue_point_gate"] is False


def test_nonfinite_point_metric_fails_closed(tmp_path):
    args = make_matrix(tmp_path)
    job = args.archive_root / "hard5_u012_s1"
    text = (job / "heldout_increment_metrics.csv").read_text()
    (job / "heldout_increment_metrics.csv").write_text(text.replace("0.5", "nan", 1))
    receipt = json.loads((job / "LAUNCH_RECEIPT.json").read_text())
    receipt["payload_sha256"]["heldout_increment_metrics.csv"] = analyzer.sha256_file(
        job / "heldout_increment_metrics.csv"
    )
    (job / "LAUNCH_RECEIPT.json").write_text(json.dumps(receipt) + "\n")
    with pytest.raises(ValueError, match="non-finite"):
        analyzer.analyze(args)


def test_training_complement_mismatch_fails_closed(tmp_path):
    args = make_matrix(tmp_path)
    job = args.archive_root / "hard5_u012_s1"
    manifest_path = job / "RUN_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["training_trajectory_ids"] = ["hard5_u011"]
    manifest_path.write_text(json.dumps(manifest) + "\n")
    receipt_path = job / "LAUNCH_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["run_manifest_sha256"] = analyzer.sha256_file(manifest_path)
    receipt["payload_sha256"]["RUN_MANIFEST.json"] = analyzer.sha256_file(manifest_path)
    receipt_path.write_text(json.dumps(receipt) + "\n")
    with pytest.raises(ValueError, match="manifest contract"):
        analyzer.analyze(args)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("gpu_name", "not-a-gpu", "producer provenance"),
        ("cuda_visible_devices", "0,1", "producer provenance"),
        ("launcher_session", "manual", "producer provenance"),
        ("source_mode", "unknown", "source mode"),
        ("git_status_short", " M runner.py", "clean-git"),
    ],
)
def test_self_consistent_bad_runtime_provenance_fails_closed(
    tmp_path, field, value, message
):
    args = make_matrix(tmp_path)
    job = args.archive_root / "hard5_u012_s1"
    provenance_path = job / "RUN_PROVENANCE.json"
    provenance = json.loads(provenance_path.read_text())
    provenance[field] = value
    provenance_path.write_text(json.dumps(provenance) + "\n")
    manifest_path = job / "RUN_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["provenance"] = provenance
    manifest_path.write_text(json.dumps(manifest) + "\n")
    receipt_path = job / "LAUNCH_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["provenance"] = provenance
    receipt_path.write_text(json.dumps(receipt) + "\n")
    refresh_job_receipt(job)
    with pytest.raises(ValueError, match=message):
        analyzer.analyze(args)


def test_missing_receipt_provenance_fails_closed(tmp_path):
    args = make_matrix(tmp_path)
    job = args.archive_root / "hard5_u012_s1"
    receipt_path = job / "LAUNCH_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text())
    receipt.pop("provenance")
    receipt_path.write_text(json.dumps(receipt) + "\n")
    with pytest.raises(ValueError, match="producer provenance"):
        analyzer.analyze(args)


@pytest.mark.parametrize("field", ["centroids", "residual_mean", "residual_std"])
def test_nonfinite_npz_global_arrays_fail_closed(tmp_path, field):
    args = make_matrix(tmp_path)
    job = args.archive_root / "hard5_u012_s1"
    path = job / "selected_increment_fields.npz"
    with np.load(path, allow_pickle=False) as archive:
        arrays = {name: np.asarray(archive[name]) for name in archive.files}
    arrays[field] = arrays[field].copy()
    arrays[field].flat[0] = np.nan
    np.savez_compressed(path, **arrays)
    refresh_job_receipt(job)
    with pytest.raises(ValueError, match="global arrays"):
        analyzer.analyze(args)


def test_missing_point_row_fails_closed(tmp_path):
    args = make_matrix(tmp_path)
    job = args.archive_root / "hard5_u012_s1"
    path = job / "heldout_increment_metrics.csv"
    rows = analyzer.read_csv(path)
    write_csv(path, rows[:-1])
    refresh_job_receipt(job)
    with pytest.raises(ValueError, match="missing, duplicate, or extra"):
        analyzer.analyze(args)


def test_self_consistent_extra_payload_fails_closed(tmp_path):
    args = make_matrix(tmp_path)
    job = args.archive_root / "hard5_u012_s1"
    (job / "extra.bin").write_bytes(b"unexpected")
    refresh_job_receipt(job)
    with pytest.raises(ValueError, match="payload file set"):
        analyzer.analyze(args)
