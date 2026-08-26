#!/usr/bin/env python3
"""Fail-closed aggregate analysis for the frozen Hard5 LOAO 3x3 matrix."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

FOLD_ROLES = {"hard5_u011": "endpoint_extrapolation_secondary", "hard5_u012": "interpolation_primary", "hard5_u013": "endpoint_extrapolation_secondary"}
FIRST_HITS = {"hard5_u011": 122, "hard5_u012": 83, "hard5_u013": 59}
FOLD_UMAX = {"hard5_u011": 0.11, "hard5_u012": 0.12, "hard5_u013": 0.13}
TARGET_CYCLES = {"hard5_u011": 121, "hard5_u012": 82, "hard5_u013": 55}
SEEDS = (1, 2, 3)
PRIMARY_CONTROLS = ("persistence", "constrained_linear")
EVENT_METHODS = ("gno_data", *PRIMARY_CONTROLS)
METRICS = ("derived_active_log_mae", "absolute_p99_iou", "absolute_support_area_ratio")
CLAIMS = {"claim_class": "processed_griphfith_archive_imitation_only", "teacher_qualified": False, "damage_fixed_point_gate": "fail", "physics_loss_weight": 0.0, "physical_validation": False}


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
        raise ValueError(f"empty metrics table: {path}")
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
        raise ValueError("cannot aggregate an empty list")
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def validate_claims(payload: dict, source: Path) -> None:
    for key, expected in CLAIMS.items():
        if payload.get(key) != expected:
            raise ValueError(f"claim mismatch in {source}: {key}")


def validate_payload_hashes(job_dir: Path, receipt: dict) -> None:
    payload = receipt.get("payload_sha256")
    if not isinstance(payload, dict) or not payload:
        raise ValueError(f"missing payload hashes: {job_dir}")
    actual = {str(path.relative_to(job_dir)): sha256_file(path) for path in job_dir.rglob("*") if path.is_file() and path.name != "LAUNCH_RECEIPT.json"}
    if actual != payload:
        raise ValueError(f"payload file set or hash mismatch: {job_dir}")


def expected_opportunities(fold: str) -> set[tuple[int, int, int]]:
    hit = FIRST_HITS[fold]
    return {(origin, target, target - origin) for origin in range(hit - 3, hit) for target in range(origin + 1, origin + 4)}


def validate_identity(row: dict[str, str], fold: str, role: str, domain: str) -> None:
    if row.get("trajectory_id") != fold:
        raise ValueError(f"metric trajectory mismatch: {fold}")
    if row.get("fold_role") != FOLD_ROLES[fold]:
        raise ValueError(f"metric fold role mismatch: {fold}")
    if row.get("evaluation_role") != role:
        raise ValueError(f"metric evaluation role mismatch: {fold}")
    if row.get("mapping_domain") != domain:
        raise ValueError(f"metric mapping domain mismatch: {fold}")


def validate_event_fields(path: Path, fold: str) -> list[dict]:
    rows = read_csv(path)
    if len(rows) != 27:
        raise ValueError(f"event field table must have exactly 27 rows: {path}")
    expected = expected_opportunities(fold)
    counts, clean = Counter(), []
    for row in rows:
        validate_identity(row, fold, "primary_event_centred", "native_full_mesh")
        method = row.get("method")
        if method not in EVENT_METHODS:
            raise ValueError(f"unexpected event field method: {method!r}")
        opportunity = (exact_int(row.get("origin_cycle"), "origin_cycle"), exact_int(row.get("target_cycle"), "target_cycle"), exact_int(row.get("horizon"), "horizon"))
        if opportunity not in expected:
            raise ValueError(f"unexpected event field opportunity: {opportunity}")
        counts[(method, *opportunity)] += 1
        clean.append({"method": method, **{metric: finite_float(row.get(metric), f"{fold}/{method}/{metric}") for metric in METRICS}})
    expected_keys = {(method, *opportunity) for method in EVENT_METHODS for opportunity in expected}
    if set(counts) != expected_keys or any(value != 1 for value in counts.values()):
        raise ValueError(f"missing, duplicate, or extra event field rows: {path}")
    return clean


def classification_summary(rows: list[dict]) -> dict:
    truth = [row["truth_transition"] for row in rows]
    predicted = [row["predicted_transition"] for row in rows]
    probability = [row["predicted_transition_probability"] for row in rows]
    tp = sum(t == 1 and p == 1 for t, p in zip(truth, predicted)); tn = sum(t == 0 and p == 0 for t, p in zip(truth, predicted))
    fp = sum(t == 0 and p == 1 for t, p in zip(truth, predicted)); fn = sum(t == 1 and p == 0 for t, p in zip(truth, predicted))
    ece = 0.0
    for index in range(10):
        selected = [i for i, value in enumerate(probability) if min(int(value * 10), 9) == index]
        if selected:
            ece += len(selected) / len(rows) * abs(sum(probability[i] for i in selected) / len(selected) - sum(truth[i] for i in selected) / len(selected))
    recall_valid, precision_valid, fpr_valid = bool(tp + fn), bool(tp + fp), bool(fp + tn)
    return {"evaluated_rows": len(rows), "positive_rows": sum(truth), "negative_rows": len(rows) - sum(truth), "true_positive": tp, "true_negative": tn, "false_positive": fp, "false_negative": fn, "recall": tp / (tp + fn) if recall_valid else None, "recall_denominator": tp + fn, "recall_valid": recall_valid, "precision": tp / (tp + fp) if precision_valid else None, "precision_denominator": tp + fp, "precision_valid": precision_valid, "false_positive_rate": fp / (fp + tn) if fpr_valid else None, "false_positive_rate_denominator": fp + tn, "false_positive_rate_valid": fpr_valid, "brier_score": sum((p - t) ** 2 for p, t in zip(probability, truth)) / len(rows), "ece_10_bin": ece, "ece_10_bin_valid": True, "threshold": 0.5}


def _summary_equal(actual: object, expected: object) -> bool:
    if isinstance(actual, dict) and isinstance(expected, dict):
        return set(actual) == set(expected) and all(_summary_equal(actual[key], expected[key]) for key in actual)
    if isinstance(actual, (int, float)) and not isinstance(actual, bool) and isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return math.isfinite(float(actual)) and math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-12)
    return actual == expected


def validate_warnings(path: Path, summary_path: Path, fold: str) -> dict:
    rows = read_csv(path)
    if len(rows) != 9:
        raise ValueError(f"warning table must have exactly 9 rows: {path}")
    expected, counts, clean = expected_opportunities(fold), Counter(), []
    for row in rows:
        if (
            row.get("trajectory_id") != fold
            or row.get("fold_role") != FOLD_ROLES[fold]
            or row.get("evaluation_role") != "primary_transition"
            or row.get("method") != "gno_data"
        ):
            raise ValueError(f"warning identity/role mismatch: {fold}")
        opportunity = (exact_int(row.get("origin_cycle"), "origin_cycle"), exact_int(row.get("target_cycle"), "target_cycle"), exact_int(row.get("horizon"), "horizon"))
        if opportunity not in expected:
            raise ValueError(f"unexpected warning opportunity: {opportunity}")
        truth = exact_int(row.get("truth_transition"), "truth_transition"); predicted = exact_int(row.get("predicted_transition"), "predicted_transition")
        probability = finite_float(row.get("predicted_transition_probability"), "predicted_transition_probability")
        if truth != int(opportunity[1] >= FIRST_HITS[fold]) or truth not in (0, 1) or predicted not in (0, 1):
            raise ValueError(f"invalid warning label: {fold}/{opportunity}")
        if not 0 <= probability <= 1 or predicted != int(probability >= 0.5):
            raise ValueError(f"warning probability/decision mismatch: {fold}/{opportunity}")
        counts[opportunity] += 1
        clean.append({"horizon": opportunity[2], "truth_transition": truth, "predicted_transition": predicted, "predicted_transition_probability": probability})
    if set(counts) != expected or any(value != 1 for value in counts.values()):
        raise ValueError(f"missing, duplicate, or extra warning rows: {path}")
    if sum(row["truth_transition"] for row in clean) != 6:
        raise ValueError(f"warning truth composition must be 6 positive and 3 negative: {path}")
    recomputed = {"distribution_unit": "retrospective_event_aligned_forecast_opportunity", "overall": classification_summary(clean), "by_horizon": {f"h{horizon}": classification_summary([row for row in clean if row["horizon"] == horizon]) for horizon in (1, 2, 3)}}
    if not _summary_equal(read_json(summary_path), recomputed):
        raise ValueError(f"warning summary does not match recomputed rows: {summary_path}")
    return recomputed["overall"]


def validate_secondary(path: Path, fold: str, methods: tuple[str, ...], role: str, domain: str) -> None:
    rows = read_csv(path); counts = Counter(row.get("method", "") for row in rows)
    if len(rows) != len(methods) or set(counts) != set(methods) or any(value != 1 for value in counts.values()):
        raise ValueError(f"secondary method set mismatch: {path}")
    for row in rows:
        validate_identity(row, fold, role, domain)
        if finite_float(row.get("umax"), "umax") != FOLD_UMAX[fold]:
            raise ValueError(f"secondary Umax mismatch: {path}")
        target, origin = exact_int(row.get("target_cycle"), "target_cycle"), exact_int(row.get("origin_cycle"), "origin_cycle")
        if target != TARGET_CYCLES[fold] or origin != target - 1:
            raise ValueError(f"secondary cycle mismatch: {path}")
        for metric in METRICS:
            finite_float(row.get(metric), f"{fold}/{row['method']}/{metric}")


def validate_job(job_dir: Path, lock_sha256: str) -> tuple[tuple[str, int], dict]:
    names = ("LAUNCH_RECEIPT.json", "RUN_MANIFEST.json", "fem_centred_metrics.csv", "transition_warning_metrics.csv", "transition_warning_summary.json", "matched_cycle_baseline_metrics.csv", "matched_pidl_fem_metrics.csv")
    paths = {name: job_dir / name for name in names}
    for path in paths.values():
        if not path.is_file():
            raise ValueError(f"missing required job asset: {path}")
    receipt, manifest = read_json(paths["LAUNCH_RECEIPT.json"]), read_json(paths["RUN_MANIFEST.json"])
    if receipt.get("status") != "complete" or receipt.get("training_complete") is not True or receipt.get("archive_verified") is not True or manifest.get("status") != "complete":
        raise ValueError(f"noncomplete or unverified job: {job_dir}")
    validate_claims(receipt, paths["LAUNCH_RECEIPT.json"]); validate_claims(manifest, paths["RUN_MANIFEST.json"]); validate_payload_hashes(job_dir, receipt)
    if receipt.get("run_manifest_sha256") != sha256_file(paths["RUN_MANIFEST.json"]):
        raise ValueError(f"run manifest hash mismatch: {job_dir}")
    provenance = receipt.get("provenance", {})
    if provenance != manifest.get("provenance", {}) or provenance.get("release_matrix_sha256") != lock_sha256:
        raise ValueError(f"provenance or matrix lock mismatch: {job_dir}")
    fold, seed = manifest.get("heldout_trajectory_id"), manifest.get("seed")
    if fold not in FOLD_ROLES or seed not in SEEDS or manifest.get("fold_role") != FOLD_ROLES.get(fold):
        raise ValueError(f"unexpected fold/seed/role: {fold!r}/{seed!r}")
    result = {"event": validate_event_fields(paths["fem_centred_metrics.csv"], fold), "warning": validate_warnings(paths["transition_warning_metrics.csv"], paths["transition_warning_summary.json"], fold)}
    validate_secondary(paths["matched_cycle_baseline_metrics.csv"], fold, EVENT_METHODS, "secondary_diagnostic", "native_full_mesh")
    validate_secondary(paths["matched_pidl_fem_metrics.csv"], fold, ("gno_data", "pidl_mapped"), "secondary", "pidl_containing_triangle_cells_only")
    return (fold, seed), result


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def analyze(jobs_root: Path, matrix_lock: Path, output: Path) -> dict:
    lock_sha256 = sha256_file(matrix_lock); receipts = sorted(jobs_root.glob("*/LAUNCH_RECEIPT.json"))
    if len(receipts) != 9:
        raise ValueError(f"expected exactly 9 immediate job directories, found {len(receipts)}")
    jobs = {}
    for receipt in receipts:
        key, result = validate_job(receipt.parent, lock_sha256)
        if key in jobs:
            raise ValueError(f"duplicate fold/seed job: {key}")
        jobs[key] = result
    if set(jobs) != {(fold, seed) for fold in FOLD_ROLES for seed in SEEDS}:
        raise ValueError("missing or unexpected fold/seed jobs")
    seed_rows, fold_rows = [], []
    for fold, fold_role in FOLD_ROLES.items():
        for method in EVENT_METHODS:
            for seed in SEEDS:
                rows = [row for row in jobs[(fold, seed)]["event"] if row["method"] == method]
                seed_rows.append({"fold": fold, "fold_role": fold_role, "seed": seed, "method": method, **{f"median_{metric}": median([row[metric] for row in rows]) for metric in METRICS}})
            selected = [row for row in seed_rows if row["fold"] == fold and row["method"] == method]
            fold_rows.append({"fold": fold, "fold_role": fold_role, "method": method, **{f"median_{metric}": median([row[f"median_{metric}"] for row in selected]) for metric in METRICS}})
    transition_seed_rows, transition_fold_rows = [], []
    for fold, fold_role in FOLD_ROLES.items():
        for seed in SEEDS:
            summary = jobs[(fold, seed)]["warning"]
            transition_seed_rows.append({"fold": fold, "fold_role": fold_role, "seed": seed, "recall": finite_float(summary["recall"], "recall"), "false_warnings": exact_int(summary["false_positive"], "false_positive")})
        selected = [row for row in transition_seed_rows if row["fold"] == fold]
        recall, false_warnings = median([row["recall"] for row in selected]), median([float(row["false_warnings"]) for row in selected])
        transition_fold_rows.append({"fold": fold, "fold_role": fold_role, "median_recall": recall, "median_false_warnings": false_warnings, "pass": recall >= 4 / 6 and false_warnings <= 1})
    primary = {row["method"]: row for row in fold_rows if row["fold"] == "hard5_u012"}; gno = primary["gno_data"]
    comparisons = {control: {"gno_lower_derived_active_log_mae": gno["median_derived_active_log_mae"] < primary[control]["median_derived_active_log_mae"], "gno_higher_absolute_p99_iou": gno["median_absolute_p99_iou"] > primary[control]["median_absolute_p99_iou"]} for control in PRIMARY_CONTROLS}
    support_pass = 0.5 <= gno["median_absolute_support_area_ratio"] <= 2.0
    field_pass = support_pass and all(all(item.values()) for item in comparisons.values())
    transition_pass_count = sum(row["pass"] for row in transition_fold_rows); overall_pass = field_pass and transition_pass_count >= 2
    decision = {"status": "PASS" if overall_pass else "FAIL", "job_count": 9, "field_aggregation": "per_seed_median_over_9_event_rows_then_median_over_3_seeds", "transition_aggregation": "per_seed_recall_and_false_warnings_then_fold_median_over_3_seeds", "primary_fold": "hard5_u012", "primary_fold_role": FOLD_ROLES["hard5_u012"], "secondary_folds": ["hard5_u011", "hard5_u013"], "primary_controls": list(PRIMARY_CONTROLS), "matched_cycle_role": "secondary_diagnostic_non_gating", "pidl_role": "secondary_non_gating", "event_field_gate": {"pass": field_pass, "support_ratio_inclusive_bounds": [0.5, 2.0], "support_ratio_pass": support_pass, "comparisons": comparisons}, "transition_gate": {"required_passing_folds": 2, "passing_folds": transition_pass_count, "pass": transition_pass_count >= 2, "folds": transition_fold_rows}, **CLAIMS, "matrix_lock_sha256": lock_sha256}
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "event_field_seed_medians.csv", seed_rows); write_csv(output / "event_field_fold_medians.csv", fold_rows); write_csv(output / "transition_seed_metrics.csv", transition_seed_rows); write_csv(output / "transition_fold_medians.csv", transition_fold_rows)
    (output / "decision.json").write_text(json.dumps(decision, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return decision


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--jobs-root", type=Path, required=True); parser.add_argument("--matrix-lock", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); return parser.parse_args()


if __name__ == "__main__":
    args = parse_args(); print(json.dumps(analyze(args.jobs_root, args.matrix_lock, args.output), indent=2, sort_keys=True, allow_nan=False))
