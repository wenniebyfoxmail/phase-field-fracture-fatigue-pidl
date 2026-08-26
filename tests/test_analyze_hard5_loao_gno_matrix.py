from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "SENS_tensile"))
from analyze_hard5_loao_gno_matrix import (  # noqa: E402
    EVENT_METHODS,
    FIRST_HITS,
    FOLD_ROLES,
    FOLD_UMAX,
    TARGET_CYCLES,
    EXPECTED_JOB_PAYLOADS,
    analyze,
    classification_summary,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_rows(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def event_rows(fold: str) -> list[dict]:
    values = {"gno_data": (0.1, 0.8, 1.0), "persistence": (0.3, 0.3, 1.0), "constrained_linear": (0.2, 0.5, 1.0)}
    hit, rows = FIRST_HITS[fold], []
    for origin in range(hit - 3, hit):
        for target in range(origin + 1, origin + 4):
            for method in EVENT_METHODS:
                mae, iou, ratio = values[method]
                rows.append({"trajectory_id": fold, "fold_role": FOLD_ROLES[fold], "evaluation_role": "primary_event_centred", "mapping_domain": "native_full_mesh", "method": method, "origin_cycle": origin, "target_cycle": target, "horizon": target - origin, "derived_active_log_mae": mae, "absolute_p99_iou": iou, "absolute_support_area_ratio": ratio})
    return rows


def warning_rows(fold: str, pass_transition: bool = True) -> list[dict]:
    hit, rows = FIRST_HITS[fold], []
    for origin in range(hit - 3, hit):
        for target in range(origin + 1, origin + 4):
            truth = int(target >= hit)
            predicted = truth if pass_transition else 0
            rows.append({"trajectory_id": fold, "fold_role": FOLD_ROLES[fold], "evaluation_role": "primary_transition", "method": "gno_data", "origin_cycle": origin, "target_cycle": target, "horizon": target - origin, "truth_transition": truth, "predicted_transition_probability": 0.9 if predicted else 0.1, "predicted_transition": predicted, "predicted_field_hit": predicted})
    return rows


def warning_summary(rows: list[dict]) -> dict:
    clean = [{"horizon": int(row["horizon"]), "truth_transition": int(row["truth_transition"]), "predicted_transition": int(row["predicted_transition"]), "predicted_transition_probability": float(row["predicted_transition_probability"])} for row in rows]
    return {"distribution_unit": "retrospective_event_aligned_forecast_opportunity", "overall": classification_summary(clean), "by_horizon": {f"h{h}": classification_summary([row for row in clean if row["horizon"] == h]) for h in (1, 2, 3)}}


def secondary_rows(fold: str, methods: tuple[str, ...], role: str, domain: str) -> list[dict]:
    return [{"trajectory_id": fold, "umax": FOLD_UMAX[fold], "target_cycle": TARGET_CYCLES[fold], "origin_cycle": TARGET_CYCLES[fold] - 1, "fold_role": FOLD_ROLES[fold], "evaluation_role": role, "mapping_domain": domain, "method": method, "timing_semantics": "timing_unverified_secondary" if role == "secondary" else "", "derived_active_log_mae": 0.01, "absolute_p99_iou": 0.99, "absolute_support_area_ratio": 1.0} for method in methods]


def rehash(job: Path) -> None:
    receipt_path = job / "LAUNCH_RECEIPT.json"; receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    receipt["run_manifest_sha256"] = sha256(job / "RUN_MANIFEST.json")
    receipt["payload_sha256"] = {str(path.relative_to(job)): sha256(path) for path in job.rglob("*") if path.is_file() and path.name != "LAUNCH_RECEIPT.json"}
    receipt_path.write_text(json.dumps(receipt, allow_nan=False) + "\n")


def make_matrix(tmp_path: Path, failing_transition_folds: set[str] | None = None) -> tuple[Path, Path, Path, str]:
    jobs = tmp_path / "jobs"; jobs.mkdir(parents=True)
    code_hashes = {"runner": "locked-runner", "aggregate_analyzer": "locked-analyzer"}
    lock_payload = {"schema_version": "hard5_loao_matrix_lock_v3", "experiment_id": "hard5_loao_gno_v3_20260826", "status": "frozen_pending_external_release_authorization", "dataset": {"dataset_id": "hard5_loao_fem_states_v1", "manifest_sha256": "9267a102a38375ebc815404a5ae81b2d3b23622448b5b178a2c4c1a5696e202a", "hash_file_sha256": "7bff035eaa618a7517335a3adb436e14d8bf606c6fa4e202497355518e82a55e", "trajectory_ids": sorted(FOLD_ROLES)}, "matrix": {"folds": sorted(FOLD_ROLES), "seeds": [1, 2, 3], "job_count": 9, "producer": "taobo_only"}, "required_job_payloads": sorted(EXPECTED_JOB_PAYLOADS), "code_sha256": code_hashes}
    lock = tmp_path / "lock.json"; lock.write_text(json.dumps(lock_payload, sort_keys=True) + "\n"); lock_hash = sha256(lock)
    claims = {"claim_class": "processed_griphfith_archive_imitation_only", "teacher_qualified": False, "damage_fixed_point_gate": "fail", "physics_loss_weight": 0.0, "physical_validation": False}
    auth_payload = {"schema_version": "hard5_loao_release_authorization_v1", "authorization_status": "AUTHORIZED", "authorization_id": "synthetic-test-auth", "experiment_id": "hard5_loao_gno_v3_20260826", "matrix_experiment_id": "hard5_loao_gno_v3_20260826", "run_id": "pf_hard5_loao_gno_v3_test", "matrix_lock_sha256": lock_hash, "release_commit": "a" * 40, "dataset_manifest_sha256": lock_payload["dataset"]["manifest_sha256"], "dataset_hash_file_sha256": lock_payload["dataset"]["hash_file_sha256"], "authorization_scope": "hard5_only_three_fold_three_seed_data_only_loao", "producer": "taobo", "max_gpu_count": 2, "code_sha256": code_hashes, "independent_review": {"verdict": "PASS", "reviewed_commit": "a" * 40, "review_note_sha256": "b" * 64}, "jobs": [{"job_id": f"{fold}_s{seed}", "heldout": fold, "seed": seed} for fold in FOLD_ROLES for seed in (1, 2, 3)], "claims": claims}
    auth = tmp_path / "RELEASE_AUTHORIZATION.json"; auth.write_text(json.dumps(auth_payload, sort_keys=True) + "\n"); auth_hash = sha256(auth)
    for fold in FOLD_ROLES:
        for seed in (1, 2, 3):
            job = jobs / f"{fold}_s{seed}"; job.mkdir()
            provenance = {"producer": "taobo", "producer_id": "taobo-172.16.100.2", "hostname": "GPUServer8", "user": "drtao", "cuda_visible_devices": "3", "gpu_name": "NVIDIA GeForce RTX 4090", "launcher_session": "systemd:pf-h5loao-test", "run_id": auth_payload["run_id"], "job_id": job.name, "heldout_trajectory_id": fold, "seed": seed, "release_commit": auth_payload["release_commit"], "release_matrix_sha256": lock_hash, "release_authorization_sha256": auth_hash, "release_authorization": auth_payload, "authorization_id": auth_payload["authorization_id"], "source_mode": "clean_git_checkout", "runtime_source_commit": auth_payload["release_commit"], "snapshot_manifest_sha256": None, "git_commit": auth_payload["release_commit"], "git_status_short": "", "code_sha256": {**code_hashes, "matrix_lock": lock_hash}}
            training_ids = sorted(set(FOLD_ROLES) - {fold})
            manifest = {"status": "complete", **claims, "experiment_id": auth_payload["experiment_id"], "run_id": auth_payload["run_id"], "job_id": job.name, "heldout_trajectory_id": fold, "fold_role": FOLD_ROLES[fold], "seed": seed, "training_trajectory_ids": training_ids, "heldout_first_hit_used_in_training": False, "statistics": "trajectory_equal_pre_hit_first_and_second_moments", "balanced_sampling": "alternate bucket then equal-probability trajectory then pre-hit origin", "training_origins": "strictly_less_than_training_first_hit", "positive_training_windows_per_trajectory": {item: 3 for item in training_ids}, "sampling_contract": {"bucket": "alternate_transition_and_ordinary", "trajectory": "uniform_within_bucket", "origin": "uniform_pre_hit_origin_within_trajectory_and_bucket", "post_hit_origins": 0}, "steps": 3000, "parameter_count": 339461, "dataset_id": "hard5_loao_fem_states_v1", "dataset_manifest_sha256": lock_payload["dataset"]["manifest_sha256"], "dataset_hash_file_sha256": lock_payload["dataset"]["hash_file_sha256"], "required_job_payloads": sorted(EXPECTED_JOB_PAYLOADS), "release_authorization_sha256": auth_hash, "release_authorization": auth_payload, "provenance": provenance}
            (job / "RUN_MANIFEST.json").write_text(json.dumps(manifest) + "\n")
            (job / "RUN_PROVENANCE.json").write_text(json.dumps(provenance) + "\n")
            (job / "RELEASE_AUTHORIZATION.json").write_bytes(auth.read_bytes())
            write_rows(job / "fem_centred_metrics.csv", event_rows(fold))
            warnings = warning_rows(fold, fold not in (failing_transition_folds or set()))
            write_rows(job / "transition_warning_metrics.csv", warnings)
            (job / "transition_warning_summary.json").write_text(json.dumps(warning_summary(warnings), allow_nan=False) + "\n")
            write_rows(job / "matched_cycle_baseline_metrics.csv", secondary_rows(fold, EVENT_METHODS, "secondary_diagnostic", "native_full_mesh"))
            write_rows(job / "matched_pidl_fem_metrics.csv", secondary_rows(fold, ("gno_data", "pidl_mapped"), "secondary", "pidl_containing_triangle_cells_only"))
            for name in EXPECTED_JOB_PAYLOADS - {path.name for path in job.iterdir()}:
                (job / name).write_bytes(b"synthetic locked payload\n")
            receipt = {"status": "complete", "training_complete": True, "archive_verified": True, **claims, "experiment_id": auth_payload["experiment_id"], "run_id": auth_payload["run_id"], "job_id": job.name, "heldout_trajectory_id": fold, "seed": seed, "release_authorization_sha256": auth_hash, "release_authorization": auth_payload, "provenance": provenance}
            (job / "LAUNCH_RECEIPT.json").write_text(json.dumps(receipt) + "\n"); rehash(job)
    return jobs, lock, auth, auth_hash


def test_complete_matrix_passes_two_stage_event_and_transition_gate(tmp_path):
    jobs, lock, auth, auth_hash = make_matrix(tmp_path); decision = analyze(jobs, lock, auth, auth_hash, tmp_path / "analysis")
    assert decision["status"] == "PASS"
    assert decision["event_field_gate"]["pass"] is True
    assert decision["transition_gate"]["passing_folds"] == 3
    assert "NaN" not in (tmp_path / "analysis" / "decision.json").read_text()


def test_matched_cycle_can_pass_while_transition_failure_forces_overall_fail(tmp_path):
    jobs, lock, auth, auth_hash = make_matrix(tmp_path, set(FOLD_ROLES)); decision = analyze(jobs, lock, auth, auth_hash, tmp_path / "analysis")
    assert decision["event_field_gate"]["pass"] is True
    assert decision["transition_gate"]["pass"] is False
    assert decision["status"] == "FAIL"


def test_u012_event_support_ratio_failure_forces_overall_fail(tmp_path):
    jobs, lock, auth, auth_hash = make_matrix(tmp_path)
    for seed in (1, 2, 3):
        job = jobs / f"hard5_u012_s{seed}"
        path = job / "fem_centred_metrics.csv"
        rows = list(csv.DictReader(path.open()))
        for row in rows:
            if row["method"] == "gno_data":
                row["absolute_support_area_ratio"] = "2.1"
        write_rows(path, rows); rehash(job)
    decision = analyze(jobs, lock, auth, auth_hash, tmp_path / "analysis")
    assert decision["event_field_gate"]["support_ratio_pass"] is False
    assert decision["status"] == "FAIL"


@pytest.mark.parametrize("filename", ["fem_centred_metrics.csv", "transition_warning_metrics.csv"])
@pytest.mark.parametrize("mutation", ["missing", "duplicate"])
def test_missing_or_duplicate_event_and_warning_rows_are_rejected(tmp_path, filename, mutation):
    jobs, lock, auth, auth_hash = make_matrix(tmp_path); job = jobs / "hard5_u012_s1"; path = job / filename
    rows = list(csv.DictReader(path.open()))
    rows = rows[:-1] if mutation == "missing" else rows + [rows[0]]
    write_rows(path, rows); rehash(job)
    with pytest.raises(ValueError, match="exactly|missing, duplicate"):
        analyze(jobs, lock, auth, auth_hash, tmp_path / "analysis")


def test_warning_summary_mismatch_is_rejected(tmp_path):
    jobs, lock, auth, auth_hash = make_matrix(tmp_path); job = jobs / "hard5_u011_s1"; path = job / "transition_warning_summary.json"
    summary = json.loads(path.read_text()); summary["overall"]["false_positive"] = 3
    path.write_text(json.dumps(summary) + "\n"); rehash(job)
    with pytest.raises(ValueError, match="summary does not match"):
        analyze(jobs, lock, auth, auth_hash, tmp_path / "analysis")


def test_missing_job_and_payload_hash_mismatch_are_rejected(tmp_path):
    jobs, lock, auth, auth_hash = make_matrix(tmp_path); job = jobs / "hard5_u013_s3"
    for path in job.iterdir(): path.unlink()
    job.rmdir()
    with pytest.raises(ValueError, match="exactly 9"):
        analyze(jobs, lock, auth, auth_hash, tmp_path / "analysis")
    jobs, lock, auth, auth_hash = make_matrix(tmp_path / "second"); path = jobs / "hard5_u011_s1" / "fem_centred_metrics.csv"; path.write_text(path.read_text() + "tamper")
    with pytest.raises(ValueError, match="hash mismatch"):
        analyze(jobs, lock, auth, auth_hash, tmp_path / "analysis2")


@pytest.mark.parametrize("nonfinite", ["nan", "inf"])
def test_nonfinite_primary_metric_fails_closed(tmp_path, nonfinite):
    jobs, lock, auth, auth_hash = make_matrix(tmp_path)
    job = jobs / "hard5_u012_s1"; path = job / "fem_centred_metrics.csv"
    rows = list(csv.DictReader(path.open())); rows[0]["derived_active_log_mae"] = nonfinite
    write_rows(path, rows); rehash(job)
    with pytest.raises(ValueError, match="non-finite"):
        analyze(jobs, lock, auth, auth_hash, tmp_path / "analysis")


def test_warning_truth_composition_not_exactly_three_negative_six_positive_fails(tmp_path):
    jobs, lock, auth, auth_hash = make_matrix(tmp_path)
    job = jobs / "hard5_u012_s1"; path = job / "transition_warning_metrics.csv"
    rows = list(csv.DictReader(path.open()))
    positive = next(row for row in rows if row["truth_transition"] == "1")
    positive["truth_transition"] = "0"; positive["predicted_transition_probability"] = "0.1"; positive["predicted_transition"] = "0"; positive["predicted_field_hit"] = "0"
    write_rows(path, rows)
    (job / "transition_warning_summary.json").write_text(json.dumps(warning_summary(rows), allow_nan=False) + "\n")
    rehash(job)
    with pytest.raises(ValueError, match="invalid warning label|truth composition"):
        analyze(jobs, lock, auth, auth_hash, tmp_path / "analysis")


def test_authorization_provenance_and_manifest_contracts_fail_closed(tmp_path):
    jobs, lock, auth, auth_hash = make_matrix(tmp_path)
    with pytest.raises(ValueError, match="authorization hash mismatch"):
        analyze(jobs, lock, auth, "0" * 64, tmp_path / "bad-auth")
    job = jobs / "hard5_u011_s1"; provenance_path = job / "RUN_PROVENANCE.json"
    provenance = json.loads(provenance_path.read_text()); provenance["git_status_short"] = " M runner.py"
    provenance_path.write_text(json.dumps(provenance) + "\n")
    manifest_path = job / "RUN_MANIFEST.json"; manifest = json.loads(manifest_path.read_text()); manifest["provenance"] = provenance; manifest_path.write_text(json.dumps(manifest) + "\n")
    receipt_path = job / "LAUNCH_RECEIPT.json"; receipt = json.loads(receipt_path.read_text()); receipt["provenance"] = provenance; receipt_path.write_text(json.dumps(receipt) + "\n"); rehash(job)
    with pytest.raises(ValueError, match="dirty or wrong git runtime source"):
        analyze(jobs, lock, auth, auth_hash, tmp_path / "dirty")


def test_training_complement_pidl_timing_and_exact_payload_fail_closed(tmp_path):
    jobs, lock, auth, auth_hash = make_matrix(tmp_path)
    job = jobs / "hard5_u013_s1"; manifest_path = job / "RUN_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text()); manifest["training_trajectory_ids"] = ["hard5_u011"]
    manifest_path.write_text(json.dumps(manifest) + "\n"); rehash(job)
    with pytest.raises(ValueError, match="exact heldout complement"):
        analyze(jobs, lock, auth, auth_hash, tmp_path / "bad-complement")

    jobs, lock, auth, auth_hash = make_matrix(tmp_path / "pidl")
    job = jobs / "hard5_u012_s1"; pidl_path = job / "matched_pidl_fem_metrics.csv"
    rows = list(csv.DictReader(pidl_path.open())); rows[0]["timing_semantics"] = ""
    write_rows(pidl_path, rows); rehash(job)
    with pytest.raises(ValueError, match="timing semantics"):
        analyze(jobs, lock, auth, auth_hash, tmp_path / "bad-pidl")

    jobs, lock, auth, auth_hash = make_matrix(tmp_path / "payload")
    job = jobs / "hard5_u011_s1"; (job / "unexpected.txt").write_text("extra\n"); rehash(job)
    with pytest.raises(ValueError, match="payload file set"):
        analyze(jobs, lock, auth, auth_hash, tmp_path / "bad-payload")
