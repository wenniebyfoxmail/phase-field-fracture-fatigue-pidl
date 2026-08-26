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
    return [{"trajectory_id": fold, "umax": FOLD_UMAX[fold], "target_cycle": TARGET_CYCLES[fold], "origin_cycle": TARGET_CYCLES[fold] - 1, "fold_role": FOLD_ROLES[fold], "evaluation_role": role, "mapping_domain": domain, "method": method, "derived_active_log_mae": 0.01, "absolute_p99_iou": 0.99, "absolute_support_area_ratio": 1.0} for method in methods]


def rehash(job: Path) -> None:
    receipt_path = job / "LAUNCH_RECEIPT.json"; receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    receipt["run_manifest_sha256"] = sha256(job / "RUN_MANIFEST.json")
    receipt["payload_sha256"] = {str(path.relative_to(job)): sha256(path) for path in job.rglob("*") if path.is_file() and path.name != "LAUNCH_RECEIPT.json"}
    receipt_path.write_text(json.dumps(receipt, allow_nan=False) + "\n")


def make_matrix(tmp_path: Path, failing_transition_folds: set[str] | None = None) -> tuple[Path, Path]:
    jobs = tmp_path / "jobs"; jobs.mkdir(parents=True)
    lock = tmp_path / "lock.json"; lock.write_text('{"frozen":true}\n'); lock_hash = sha256(lock)
    for fold in FOLD_ROLES:
        for seed in (1, 2, 3):
            job = jobs / f"{fold}_s{seed}"; job.mkdir()
            provenance = {"release_matrix_sha256": lock_hash}
            manifest = {"status": "complete", **{"claim_class": "processed_griphfith_archive_imitation_only", "teacher_qualified": False, "damage_fixed_point_gate": "fail", "physics_loss_weight": 0.0, "physical_validation": False}, "heldout_trajectory_id": fold, "fold_role": FOLD_ROLES[fold], "seed": seed, "provenance": provenance}
            (job / "RUN_MANIFEST.json").write_text(json.dumps(manifest) + "\n")
            write_rows(job / "fem_centred_metrics.csv", event_rows(fold))
            warnings = warning_rows(fold, fold not in (failing_transition_folds or set()))
            write_rows(job / "transition_warning_metrics.csv", warnings)
            (job / "transition_warning_summary.json").write_text(json.dumps(warning_summary(warnings), allow_nan=False) + "\n")
            write_rows(job / "matched_cycle_baseline_metrics.csv", secondary_rows(fold, EVENT_METHODS, "secondary_diagnostic", "native_full_mesh"))
            write_rows(job / "matched_pidl_fem_metrics.csv", secondary_rows(fold, ("gno_data", "pidl_mapped"), "secondary", "pidl_containing_triangle_cells_only"))
            receipt = {"status": "complete", "training_complete": True, "archive_verified": True, "claim_class": "processed_griphfith_archive_imitation_only", "teacher_qualified": False, "damage_fixed_point_gate": "fail", "physics_loss_weight": 0.0, "physical_validation": False, "provenance": provenance}
            (job / "LAUNCH_RECEIPT.json").write_text(json.dumps(receipt) + "\n"); rehash(job)
    return jobs, lock


def test_complete_matrix_passes_two_stage_event_and_transition_gate(tmp_path):
    jobs, lock = make_matrix(tmp_path); decision = analyze(jobs, lock, tmp_path / "analysis")
    assert decision["status"] == "PASS"
    assert decision["event_field_gate"]["pass"] is True
    assert decision["transition_gate"]["passing_folds"] == 3
    assert "NaN" not in (tmp_path / "analysis" / "decision.json").read_text()


def test_matched_cycle_can_pass_while_transition_failure_forces_overall_fail(tmp_path):
    jobs, lock = make_matrix(tmp_path, set(FOLD_ROLES)); decision = analyze(jobs, lock, tmp_path / "analysis")
    assert decision["event_field_gate"]["pass"] is True
    assert decision["transition_gate"]["pass"] is False
    assert decision["status"] == "FAIL"


def test_u012_event_support_ratio_failure_forces_overall_fail(tmp_path):
    jobs, lock = make_matrix(tmp_path)
    for seed in (1, 2, 3):
        job = jobs / f"hard5_u012_s{seed}"
        path = job / "fem_centred_metrics.csv"
        rows = list(csv.DictReader(path.open()))
        for row in rows:
            if row["method"] == "gno_data":
                row["absolute_support_area_ratio"] = "2.1"
        write_rows(path, rows); rehash(job)
    decision = analyze(jobs, lock, tmp_path / "analysis")
    assert decision["event_field_gate"]["support_ratio_pass"] is False
    assert decision["status"] == "FAIL"


@pytest.mark.parametrize("filename", ["fem_centred_metrics.csv", "transition_warning_metrics.csv"])
@pytest.mark.parametrize("mutation", ["missing", "duplicate"])
def test_missing_or_duplicate_event_and_warning_rows_are_rejected(tmp_path, filename, mutation):
    jobs, lock = make_matrix(tmp_path); job = jobs / "hard5_u012_s1"; path = job / filename
    rows = list(csv.DictReader(path.open()))
    rows = rows[:-1] if mutation == "missing" else rows + [rows[0]]
    write_rows(path, rows); rehash(job)
    with pytest.raises(ValueError, match="exactly|missing, duplicate"):
        analyze(jobs, lock, tmp_path / "analysis")


def test_warning_summary_mismatch_is_rejected(tmp_path):
    jobs, lock = make_matrix(tmp_path); job = jobs / "hard5_u011_s1"; path = job / "transition_warning_summary.json"
    summary = json.loads(path.read_text()); summary["overall"]["false_positive"] = 3
    path.write_text(json.dumps(summary) + "\n"); rehash(job)
    with pytest.raises(ValueError, match="summary does not match"):
        analyze(jobs, lock, tmp_path / "analysis")


def test_missing_job_and_payload_hash_mismatch_are_rejected(tmp_path):
    jobs, lock = make_matrix(tmp_path); job = jobs / "hard5_u013_s3"
    for path in job.iterdir(): path.unlink()
    job.rmdir()
    with pytest.raises(ValueError, match="exactly 9"):
        analyze(jobs, lock, tmp_path / "analysis")
    jobs, lock = make_matrix(tmp_path / "second"); path = jobs / "hard5_u011_s1" / "fem_centred_metrics.csv"; path.write_text(path.read_text() + "tamper")
    with pytest.raises(ValueError, match="hash mismatch"):
        analyze(jobs, lock, tmp_path / "analysis2")
