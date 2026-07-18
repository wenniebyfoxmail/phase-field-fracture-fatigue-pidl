#!/usr/bin/env python3
"""Deterministically validate a completed FEM cycle-forecast result package."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

REQUIRED_ASSETS = {
    "RUN_MANIFEST.json", "PRE_C89_SELECTION.json", "data_efficiency_matrix.csv",
    "context_length_x_rollout_horizon_heatmap.png", "near_event_rollout_error_growth.png",
    "fem_field_residual_panel_c89.png", "fem_active_support_panel_c89.png", "decision.md",
}


def digest(path: Path) -> str:
    h=hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()


def validate(package: Path, runs: Path) -> list[str]:
    errors=[]
    for name in REQUIRED_ASSETS:
        if not (package/name).is_file() or (package/name).stat().st_size == 0: errors.append(f"missing/empty asset: {name}")
    if errors: return errors
    manifest=json.loads((package/"RUN_MANIFEST.json").read_text())
    if manifest.get("cell_count") != 20: errors.append("matrix must contain 20 trained cells")
    if manifest.get("trajectory_count") != 1 or manifest.get("leave_one_trajectory_out") is not False:
        errors.append("single-trajectory limitation not explicit")
    if manifest.get("c89_opened_once_after_selection") is not True: errors.append("c89 unlock flag missing")
    if digest(package/"PRE_C89_SELECTION.json") != manifest.get("selection_file_sha256_before_c89"):
        errors.append("pre-c89 selection hash mismatch")
    selection=json.loads((package/"PRE_C89_SELECTION.json").read_text())
    if selection.get("c89_opened") is not False: errors.append("selection file must be frozen before c89")
    cell_manifests=list(runs.glob("**/RUN_MANIFEST.json"))
    if len(cell_manifests) != 20: errors.append(f"expected 20 cell manifests, found {len(cell_manifests)}")
    for path in cell_manifests:
        cell=json.loads(path.read_text()); firewall=cell.get("firewall",{})
        for key in ("future_used_for_training","future_used_for_normalization","future_used_for_model_selection","c89_opened_during_training_or_nonlocked_evaluation","architecture_tuned_on_c89"):
            if firewall.get(key) is not False: errors.append(f"firewall violation/missing {key}: {path.parent.name}")
        if cell.get("fixed_training_steps") != 3000: errors.append(f"nonmatched budget: {path.parent.name}")
        if cell.get("dataset_sha256") != manifest.get("dataset_sha256"): errors.append(f"dataset hash mismatch: {path.parent.name}")
    with (package/"data_efficiency_matrix.csv").open(newline="",encoding="utf-8") as handle: rows=list(csv.DictReader(handle))
    required_columns={"model","train_end","context_k","origin_cycle","target_cycle","horizon","phase",
        "damage_mae","damage_rmse","damage_correlation","history_log_mae","history_log_rmse","history_log_correlation",
        "log10_psi_raw_mae","log10_psi_raw_rmse","log10_psi_raw_correlation","derived_active_log_mae",
        "derived_active_log_rmse","derived_active_correlation","absolute_p99_iou","own_p99_iou",
        "absolute_support_area_ratio","runtime_seconds","parameter_count"}
    if not rows or not required_columns.issubset(rows[0]): errors.append("data-efficiency CSV lacks required FEM-centred columns")
    locked=[r for r in rows if r.get("phase")=="locked_c89_final"]
    expected_locked=20+4  # trained models plus persistence per cutoff
    if len(locked) != expected_locked: errors.append(f"expected {expected_locked} locked rows, found {len(locked)}")
    if any(int(r["target_cycle"]) != 89 for r in locked): errors.append("locked rows must target c89")
    return errors


if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("--package",type=Path,required=True); p.add_argument("--runs",type=Path,required=True); a=p.parse_args()
    failures=validate(a.package,a.runs)
    if failures:
        for failure in failures: print(f"ERROR: {failure}")
        raise SystemExit(1)
    print("cycle forecast package validation: PASS")
