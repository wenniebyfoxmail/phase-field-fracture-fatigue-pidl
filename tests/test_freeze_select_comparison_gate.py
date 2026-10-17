import hashlib
import json

import pandas as pd

from SENS_tensile.freeze_select.comparison_gate import evaluate_comparison


def _write_package(root, method, *, identity_override=None):
    path = root / method
    path.mkdir()
    identity = {
        "dataset_snapshot_sha256": "a" * 64,
        "observation_ids_sha256": "b" * 64,
        "split_manifest_sha256": "c" * 64,
        "candidate_library_sha256": "d" * 64,
        "weak_windows_sha256": "e" * 64,
        "forecast_cutoff_index": 24,
    }
    if identity_override:
        identity.update(identity_override)
    provenance = {
        **identity,
        "method_id": method,
        "code_commit": "deadbeef",
        "dirty_status": "clean",
        "producer_machine": "test",
        "log_path": "test.log",
        "future_damage_used_for_selection": False,
        "holdout_trajectory_ids": ["h0", "h1", "h2"],
    }
    if method == "freeze_then_select":
        provenance.update(field_frozen_before_selection=True, frozen_field_sha256="f" * 64)
        support = ["t0", "t2"]
        trial_supports = [["t0", "t2"]] * 4
        ious, tips, events = [0.76, 0.78, 0.80], [0.07, 0.08, 0.08], [1, 1, 1]
    elif method == "single_shot":
        provenance["single_sparse_solve"] = True
        support = ["t0", "t1"]
        trial_supports = [["t0", "t1"], ["t0"], ["t0", "t3"], ["t0", "t1"]]
        ious, tips, events = [0.65, 0.66, 0.67], [0.12, 0.13, 0.12], [2, 2, 2]
    else:
        field = path / "FIELD_MODEL_PROVENANCE.json"
        field.write_text(json.dumps({"architecture": "joint-test"}) + "\n")
        provenance.update(
            joint_optimization=True,
            checkpoint_sha256="1" * 64,
            field_model_provenance_sha256=hashlib.sha256(field.read_bytes()).hexdigest(),
        )
        support = ["t0", "t3"]
        trial_supports = [["t0", "t3"], ["t0"], ["t0", "t1"], ["t0", "t3"]]
        ious, tips, events = [0.66, 0.67, 0.68], [0.11, 0.12, 0.11], [2, 2, 2]
    (path / "RUN_PROVENANCE.json").write_text(json.dumps(provenance) + "\n")
    (path / "selection_result.json").write_text(
        json.dumps(
            {
                "term_names": ["t0", "t1", "t2", "t3"],
                "selected_support": support,
                "holdout_weak_rmse": 0.4 if method == "freeze_then_select" else 0.6,
                "null_holdout_weak_rmse": 1.0,
            }
        )
        + "\n"
    )
    trial_rows = []
    for trial_id, selected in enumerate(trial_supports):
        for term in ["t0", "t1", "t2", "t3"]:
            trial_rows.append(
                {
                    "trial_id": trial_id,
                    "term": term,
                    "selected": term in selected,
                    "coefficient": 0.5 if term in selected else 0.0,
                    "seed": trial_id,
                    "time_window_id": f"tw{trial_id}",
                    "spatial_section_id": f"s{trial_id}",
                    "test_function_id": "quartic" if trial_id % 2 == 0 else "cosine",
                }
            )
    pd.DataFrame(trial_rows).to_csv(path / "support_trials.csv", index=False)
    pd.DataFrame(
        {
            "trajectory_id": ["h0", "h1", "h2"],
            "method": method,
            "final_iou_d050": ious,
            "final_tip_error": tips,
            "event_time_error": events,
            "forecast_rmse": [0.05, 0.05, 0.05],
            "fixed_final_iou_d050": [0.50, 0.52, 0.51],
            "fixed_tip_error": [0.20, 0.20, 0.20],
            "fixed_event_time_error": [3, 3, 3],
        }
    ).to_csv(path / "section_metrics.csv", index=False)
    return path


def _truth(tmp_path):
    path = tmp_path / "SEALED_TRUTH.json"
    path.write_text(json.dumps({"term_names": ["t0", "t1", "t2", "t3"], "declared_support": ["t0", "t2"]}) + "\n")
    return path


def test_fair_complete_packages_can_prove_improvement(tmp_path):
    directories = {
        method: _write_package(tmp_path, method)
        for method in ("freeze_then_select", "single_shot", "joint_training")
    }
    report = evaluate_comparison(directories, _truth(tmp_path))
    assert report.package_valid
    assert report.freeze_then_select_reliability_improved


def test_identity_mismatch_rejects_unfair_comparison(tmp_path):
    directories = {
        "freeze_then_select": _write_package(tmp_path, "freeze_then_select"),
        "single_shot": _write_package(tmp_path, "single_shot", identity_override={"weak_windows_sha256": "9" * 64}),
        "joint_training": _write_package(tmp_path, "joint_training"),
    }
    report = evaluate_comparison(directories, _truth(tmp_path))
    assert not report.package_valid
    assert any("weak_windows_sha256" in error for error in report.errors)


def test_joint_package_requires_genuine_field_provenance(tmp_path):
    directories = {
        method: _write_package(tmp_path, method)
        for method in ("freeze_then_select", "single_shot", "joint_training")
    }
    (directories["joint_training"] / "FIELD_MODEL_PROVENANCE.json").unlink()
    report = evaluate_comparison(directories, _truth(tmp_path))
    assert not report.package_valid
    assert any("FIELD_MODEL_PROVENANCE" in error for error in report.errors)
