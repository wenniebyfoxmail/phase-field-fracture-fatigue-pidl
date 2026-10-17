from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd


METHODS = ("freeze_then_select", "single_shot", "joint_training")
IDENTITY_KEYS = (
    "dataset_snapshot_sha256",
    "observation_ids_sha256",
    "split_manifest_sha256",
    "candidate_library_sha256",
    "weak_windows_sha256",
    "forecast_cutoff_index",
)
PROVENANCE_REQUIRED = IDENTITY_KEYS + (
    "method_id",
    "code_commit",
    "dirty_status",
    "producer_machine",
    "log_path",
    "future_damage_used_for_selection",
    "holdout_trajectory_ids",
)
TRIAL_COLUMNS = (
    "trial_id",
    "term",
    "selected",
    "coefficient",
    "seed",
    "time_window_id",
    "spatial_section_id",
    "test_function_id",
)
SECTION_COLUMNS = (
    "trajectory_id",
    "method",
    "final_iou_d050",
    "final_tip_error",
    "event_time_error",
    "forecast_rmse",
    "fixed_final_iou_d050",
    "fixed_tip_error",
    "fixed_event_time_error",
)


@dataclass(frozen=True)
class ComparisonGateReport:
    package_valid: bool
    freeze_then_select_reliability_improved: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    method_metrics: dict[str, dict[str, float | bool | list[str]]]
    comparison_metrics: dict[str, float | bool]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_hash(value: object) -> bool:
    text = str(value)
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text.lower())


def _support_metrics(support: set[str], truth: set[str]) -> dict[str, float | bool]:
    intersection = len(support & truth)
    union = len(support | truth)
    return {
        "support_precision": intersection / max(len(support), 1),
        "support_recall": intersection / max(len(truth), 1),
        "support_jaccard": intersection / max(union, 1),
        "exact_support": support == truth,
    }


def _trial_metrics(
    trials: pd.DataFrame,
    term_names: tuple[str, ...],
    truth: set[str],
) -> dict[str, float]:
    table = trials.copy()
    table["selected"] = table["selected"].astype(bool)
    supports: list[set[str]] = []
    for _, group in table.groupby("trial_id", sort=True):
        supports.append(set(group.loc[group["selected"], "term"].astype(str)))
    pairwise: list[float] = []
    for left in range(len(supports)):
        for right in range(left + 1, len(supports)):
            union = supports[left] | supports[right]
            pairwise.append(len(supports[left] & supports[right]) / max(len(union), 1))
    frequency = table.groupby("term")["selected"].mean().reindex(term_names, fill_value=0.0)
    true_frequency = min(float(frequency[term]) for term in truth)
    false_terms = set(term_names) - truth
    false_frequency = max((float(frequency[term]) for term in false_terms), default=0.0)
    sign_values: list[float] = []
    for term in truth:
        coefficients = table.loc[
            (table["term"] == term) & table["selected"], "coefficient"
        ].to_numpy(float)
        if coefficients.size == 0:
            sign_values.append(0.0)
        else:
            sign_values.append(
                max(float(np.mean(coefficients > 0.0)), float(np.mean(coefficients < 0.0)))
            )
    return {
        "support_stability": float(np.mean(pairwise)) if pairwise else 1.0,
        "minimum_true_term_frequency": true_frequency,
        "maximum_false_term_frequency": false_frequency,
        "minimum_true_term_sign_consistency": min(sign_values),
    }


def _load_package(path: Path, expected_method: str) -> tuple[dict[str, object], dict[str, object], pd.DataFrame, pd.DataFrame, list[str]]:
    errors: list[str] = []
    required_files = {
        "provenance": path / "RUN_PROVENANCE.json",
        "selection": path / "selection_result.json",
        "trials": path / "support_trials.csv",
        "sections": path / "section_metrics.csv",
    }
    missing = [name for name, file in required_files.items() if not file.is_file()]
    if missing:
        return {}, {}, pd.DataFrame(), pd.DataFrame(), [f"{expected_method}: missing files {missing}"]
    provenance = json.loads(required_files["provenance"].read_text(encoding="utf-8"))
    selection = json.loads(required_files["selection"].read_text(encoding="utf-8"))
    trials = pd.read_csv(required_files["trials"])
    sections = pd.read_csv(required_files["sections"])
    missing_provenance = [name for name in PROVENANCE_REQUIRED if name not in provenance]
    if missing_provenance:
        errors.append(f"{expected_method}: missing provenance keys {missing_provenance}")
    if provenance.get("method_id") != expected_method:
        errors.append(f"{expected_method}: method_id mismatch")
    if provenance.get("future_damage_used_for_selection") is not False:
        errors.append(f"{expected_method}: future damage leakage")
    for key in IDENTITY_KEYS[:-1]:
        if key in provenance and not _is_hash(provenance[key]):
            errors.append(f"{expected_method}: {key} is not a SHA-256")
    if not set(TRIAL_COLUMNS) <= set(trials.columns):
        errors.append(f"{expected_method}: support_trials columns incomplete")
    if not set(SECTION_COLUMNS) <= set(sections.columns):
        errors.append(f"{expected_method}: section_metrics columns incomplete")
    if expected_method == "freeze_then_select":
        if provenance.get("field_frozen_before_selection") is not True:
            errors.append("freeze_then_select: field_frozen_before_selection must be true")
        if not _is_hash(provenance.get("frozen_field_sha256")):
            errors.append("freeze_then_select: frozen_field_sha256 missing or invalid")
    elif expected_method == "single_shot":
        if provenance.get("single_sparse_solve") is not True:
            errors.append("single_shot: single_sparse_solve must be true")
    else:
        field_provenance = path / "FIELD_MODEL_PROVENANCE.json"
        if provenance.get("joint_optimization") is not True:
            errors.append("joint_training: joint_optimization must be true")
        if not _is_hash(provenance.get("checkpoint_sha256")):
            errors.append("joint_training: checkpoint_sha256 missing or invalid")
        if not field_provenance.is_file():
            errors.append("joint_training: FIELD_MODEL_PROVENANCE.json missing")
        elif provenance.get("field_model_provenance_sha256") != _sha256_file(field_provenance):
            errors.append("joint_training: FIELD_MODEL_PROVENANCE.json hash mismatch")
    return provenance, selection, trials, sections, errors


def evaluate_comparison(
    method_directories: dict[str, Path],
    sealed_truth_path: Path,
) -> ComparisonGateReport:
    errors: list[str] = []
    warnings: list[str] = []
    if set(method_directories) != set(METHODS):
        return ComparisonGateReport(
            False,
            False,
            (f"method directories must be exactly {METHODS}",),
            (),
            {},
            {},
        )
    if not sealed_truth_path.is_file():
        return ComparisonGateReport(False, False, ("sealed truth file missing",), (), {}, {})
    truth_payload = json.loads(sealed_truth_path.read_text(encoding="utf-8"))
    if not {"declared_support", "term_names"} <= set(truth_payload):
        return ComparisonGateReport(False, False, ("sealed truth keys incomplete",), (), {}, {})
    term_names = tuple(map(str, truth_payload["term_names"]))
    truth = set(map(str, truth_payload["declared_support"]))
    if not truth <= set(term_names):
        errors.append("declared support is not a subset of term_names")

    packages: dict[str, tuple[dict[str, object], dict[str, object], pd.DataFrame, pd.DataFrame]] = {}
    for method in METHODS:
        provenance, selection, trials, sections, package_errors = _load_package(
            method_directories[method], method
        )
        errors.extend(package_errors)
        packages[method] = (provenance, selection, trials, sections)
    if errors:
        return ComparisonGateReport(False, False, tuple(errors), tuple(warnings), {}, {})

    reference = packages["freeze_then_select"][0]
    for method in METHODS[1:]:
        provenance = packages[method][0]
        for key in IDENTITY_KEYS:
            if provenance[key] != reference[key]:
                errors.append(f"fairness_identity_mismatch: {method}.{key}")
        if set(map(str, provenance["holdout_trajectory_ids"])) != set(
            map(str, reference["holdout_trajectory_ids"])
        ):
            errors.append(f"fairness_identity_mismatch: {method}.holdout_trajectory_ids")
    method_metrics: dict[str, dict[str, float | bool | list[str]]] = {}
    holdouts = set(map(str, reference["holdout_trajectory_ids"]))
    fixed_reference: pd.DataFrame | None = None
    for method in METHODS:
        provenance, selection, trials, sections = packages[method]
        if set(map(str, selection.get("term_names", []))) != set(term_names):
            errors.append(f"{method}: selection term_names mismatch sealed truth")
        support = set(map(str, selection.get("selected_support", [])))
        if not support <= set(term_names):
            errors.append(f"{method}: selected support contains unknown terms")
        if set(sections["trajectory_id"].astype(str)) != holdouts:
            errors.append(f"{method}: section metrics do not cover exact holdout ids")
        if set(sections["method"].astype(str)) != {method}:
            errors.append(f"{method}: section metric method labels mismatch")
        fixed_columns = sections[
            ["trajectory_id", "fixed_final_iou_d050", "fixed_tip_error", "fixed_event_time_error"]
        ].sort_values("trajectory_id").reset_index(drop=True)
        if fixed_reference is None:
            fixed_reference = fixed_columns
        elif not np.allclose(
            fixed_reference.drop(columns="trajectory_id").to_numpy(float),
            fixed_columns.drop(columns="trajectory_id").to_numpy(float),
        ):
            errors.append(f"{method}: fixed-physics section metrics mismatch")
        support_values = _support_metrics(support, truth)
        trial_values = _trial_metrics(trials, term_names, truth)
        null_rmse = float(selection.get("null_holdout_weak_rmse", np.nan))
        weak_rmse = float(selection.get("holdout_weak_rmse", np.nan))
        weak_improvement = (null_rmse - weak_rmse) / max(null_rmse, 1e-12)
        method_metrics[method] = {
            **support_values,
            **trial_values,
            "selected_support": sorted(support),
            "holdout_weak_improvement": weak_improvement,
            "median_final_iou_d050": float(sections["final_iou_d050"].median()),
            "median_final_tip_error": float(sections["final_tip_error"].median()),
            "median_event_time_error": float(sections["event_time_error"].median()),
            "median_forecast_rmse": float(sections["forecast_rmse"].median()),
        }
    if errors:
        return ComparisonGateReport(False, False, tuple(errors), tuple(warnings), method_metrics, {})

    fts = method_metrics["freeze_then_select"]
    single = method_metrics["single_shot"]
    joint = method_metrics["joint_training"]
    fts_sections = packages["freeze_then_select"][3].set_index("trajectory_id")
    single_sections = packages["single_shot"][3].set_index("trajectory_id")
    joint_sections = packages["joint_training"][3].set_index("trajectory_id")
    win_single = float(np.mean(fts_sections["final_iou_d050"] > single_sections["final_iou_d050"]))
    win_joint = float(np.mean(fts_sections["final_iou_d050"] > joint_sections["final_iou_d050"]))
    fixed_iou = float(fts_sections["fixed_final_iou_d050"].median())
    fixed_tip = float(fts_sections["fixed_tip_error"].median())
    catastrophic = bool(
        np.any(fts_sections["final_iou_d050"] < fts_sections["fixed_final_iou_d050"] - 0.10)
        or np.any(fts_sections["event_time_error"] > fts_sections["fixed_event_time_error"] + 3.0)
    )
    comparison = {
        "fts_minus_single_support_jaccard": float(fts["support_jaccard"] - single["support_jaccard"]),
        "fts_minus_joint_support_jaccard": float(fts["support_jaccard"] - joint["support_jaccard"]),
        "fts_minus_single_stability": float(fts["support_stability"] - single["support_stability"]),
        "fts_minus_joint_stability": float(fts["support_stability"] - joint["support_stability"]),
        "fts_minus_fixed_iou": float(fts["median_final_iou_d050"] - fixed_iou),
        "fts_minus_single_iou": float(fts["median_final_iou_d050"] - single["median_final_iou_d050"]),
        "fts_minus_joint_iou": float(fts["median_final_iou_d050"] - joint["median_final_iou_d050"]),
        "fts_iou_win_rate_vs_single": win_single,
        "fts_iou_win_rate_vs_joint": win_joint,
        "catastrophic_section_regression": catastrophic,
    }
    improved = bool(
        float(fts["support_jaccard"]) >= 0.75
        and float(fts["support_jaccard"]) > max(float(single["support_jaccard"]), float(joint["support_jaccard"]))
        and float(fts["support_stability"]) >= 0.70
        and float(fts["support_stability"]) >= max(float(single["support_stability"]), float(joint["support_stability"])) + 0.05
        and float(fts["minimum_true_term_frequency"]) >= 0.75
        and float(fts["maximum_false_term_frequency"]) <= 0.45
        and float(fts["minimum_true_term_sign_consistency"]) >= 0.85
        and float(fts["holdout_weak_improvement"]) >= 0.05
        and comparison["fts_minus_fixed_iou"] >= 0.08
        and comparison["fts_minus_single_iou"] >= 0.04
        and comparison["fts_minus_joint_iou"] >= 0.04
        and win_single >= 0.60
        and win_joint >= 0.60
        and float(fts["median_final_tip_error"]) <= 0.85 * fixed_tip + 1e-12
        and float(fts["median_final_tip_error"]) <= 0.90 * float(single["median_final_tip_error"]) + 1e-12
        and float(fts["median_final_tip_error"]) <= 0.90 * float(joint["median_final_tip_error"]) + 1e-12
        and float(fts["median_event_time_error"]) <= min(
            2.0,
            float(single["median_event_time_error"]),
            float(joint["median_event_time_error"]),
        )
        and not catastrophic
    )
    return ComparisonGateReport(True, improved, (), tuple(warnings), method_metrics, comparison)


def run_comparison_gate(
    method_directories: dict[str, Path],
    sealed_truth_path: Path,
    output_dir: Path,
) -> ComparisonGateReport:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = evaluate_comparison(method_directories, sealed_truth_path)
    (output_dir / "comparison_gate_report.json").write_text(
        json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "decision.md").write_text(
        "# Freeze-Then-Select fair comparison decision\n\n"
        f"- Package validity: **{'PASS' if report.package_valid else 'FAIL'}**\n"
        f"- Reliability improved: **{'YES' if report.freeze_then_select_reliability_improved else 'NO'}**\n"
        "- Boundary: this decision applies only to the declared dataset, support truth, and holdout sections.\n",
        encoding="utf-8",
    )
    return report
