#!/usr/bin/env python3
"""Fail-closed aggregation for the S04-E017 four-state sampling ratio comparison."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_s04_e017_alpha_screen import (  # noqa: E402
    ALLOCATIONS, BATCH_NODES, DAMAGE_THRESHOLD, EXPECTED, MONITOR_STEPS,
    PROTOCOL_REVISION, SAMPLE_SEED_OFFSET, SEEDS, STEPS, US, validate_reference,
)

THRESHOLDS = {
    "essential_bc_max_abs_error": 1e-12,
    "displacement_mass_rms_over_abs_Us": 1e-3,
    "strain_relative_l2": 1e-2,
    "predicted_rho_u": 1e-3,
}
GATE_KEYS = {
    "essential_bc_max_abs_error": "gate_essential_bc",
    "displacement_mass_rms_over_abs_Us": "gate_displacement_fit",
    "strain_relative_l2": "gate_strain_fit",
    "predicted_rho_u": "gate_rho_u",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def strict_bool(value, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a JSON boolean")
    return value


def finite_number(value, label: str) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{label} must be finite")
    return value


def validate_record(path: Path, expected_commit: str, reference_data: dict) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    state, seed = record.get("state"), record.get("seed")
    alpha = record.get("alpha")
    if alpha not in ALLOCATIONS:
        raise ValueError("unexpected sampling alpha")
    n_damage, n_background = ALLOCATIONS[alpha]
    pair = (state, seed, alpha)
    if state not in EXPECTED or seed not in SEEDS:
        raise ValueError(f"unexpected state-seed pair {pair}")
    if record.get("protocol_revision") != PROTOCOL_REVISION:
        raise ValueError("protocol mismatch")
    if record.get("status") != "COMPLETED" or strict_bool(record.get("training"), "training") is not True:
        raise ValueError("run is not a completed training run")
    if record.get("reference_sha256") != EXPECTED[state]:
        raise ValueError("reference identity mismatch")
    if record.get("reference_sha256_after") != EXPECTED[state]:
        raise ValueError("reference before/after identity mismatch")
    if record.get("steps") != STEPS or record.get("batch_nodes") != BATCH_NODES:
        raise ValueError("training budget mismatch")
    final_lr = finite_number(record.get("final_scheduler_lr"), "final_scheduler_lr")
    if not math.isclose(final_lr, 1e-5, rel_tol=0.0, abs_tol=1e-15):
        raise ValueError("final scheduler learning rate mismatch")

    run_dir = path.parent
    checkpoint = run_dir / "final_step_10000.pt"
    prediction = run_dir / "prediction.npz"
    monitoring = run_dir / "monitoring.json"
    receipt_path = run_dir / "RUN_RECEIPT.json"
    for asset in (checkpoint, prediction, monitoring, receipt_path):
        if not asset.is_file():
            raise ValueError(f"missing required asset {asset.name}")
    if sha256(checkpoint) != record.get("checkpoint_sha256"):
        raise ValueError("checkpoint SHA mismatch")
    if sha256(prediction) != record.get("prediction_sha256"):
        raise ValueError("prediction SHA mismatch")
    if sha256(monitoring) != record.get("monitoring_sha256"):
        raise ValueError("monitoring SHA mismatch")
    checkpoint_data = torch.load(checkpoint, map_location="cpu", weights_only=True)
    expected_checkpoint = {
        "protocol_revision": PROTOCOL_REVISION,
        "state": state,
        "seed": seed,
        "alpha": alpha,
        "step": STEPS,
    }
    if any(checkpoint_data.get(key) != value for key, value in expected_checkpoint.items()):
        raise ValueError("checkpoint final-step identity mismatch")
    expected_sampler = {
        "damage_threshold": DAMAGE_THRESHOLD, "n_damage": n_damage,
        "n_background": n_background, "sample_seed": seed + SAMPLE_SEED_OFFSET,
        "order": "damage_then_background_no_shuffle",
    }
    if checkpoint_data.get("sampler") != expected_sampler:
        raise ValueError("checkpoint sampler identity mismatch")
    if not isinstance(checkpoint_data.get("model_state_dict"), dict):
        raise ValueError("checkpoint lacks model_state_dict")
    with np.load(prediction) as pred:
        if set(pred.files) != {"uv"} or pred["uv"].shape != (86_756, 2):
            raise ValueError("prediction schema mismatch")
        if not np.isfinite(pred["uv"]).all():
            raise ValueError("prediction contains nonfinite values")
        saved_uv = pred["uv"].copy()

    trace = json.loads(monitoring.read_text(encoding="utf-8"))
    if not isinstance(trace, list) or [entry.get("step") for entry in trace] != list(MONITOR_STEPS):
        raise ValueError("monitoring steps mismatch")
    for entry in trace:
        for key in ("full_field_loss", "displacement_mass_rms_over_abs_Us",
                    "active_contribution", "background_contribution"):
            finite_number(entry.get(key), f"monitoring.{key}")
        if not math.isclose(entry["full_field_loss"],
                            entry["active_contribution"] + entry["background_contribution"],
                            rel_tol=1e-12, abs_tol=1e-15):
            raise ValueError("monitoring contribution mismatch")
        if not math.isclose(entry["displacement_mass_rms_over_abs_Us"] ** 2,
                            entry["full_field_loss"], rel_tol=1e-12, abs_tol=1e-15):
            raise ValueError("monitoring RMS mismatch")

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    required_receipt = {
        "status": "COMPLETED", "protocol_revision": PROTOCOL_REVISION,
        "state": state, "seed": seed, "alpha": alpha, "producer_alias": "taobo",
        "code_commit": expected_commit, "dirty": False,
        "checkpoint_sha256": record["checkpoint_sha256"],
        "prediction_sha256": record["prediction_sha256"],
        "monitoring_sha256": record["monitoring_sha256"],
        "metrics_sha256": sha256(path),
        "reference_sha256": EXPECTED[state],
        "archive_status": "VERIFIED_COPY",
    }
    if any(receipt.get(key) != value for key, value in required_receipt.items()):
        raise ValueError("run receipt identity mismatch")
    for key in ("run_id", "hostname", "command", "gpu", "cuda_visible_devices",
                "output_root", "archive_root",
                "log_path", "started_utc", "finished_utc"):
        if not isinstance(receipt.get(key), str) or not receipt[key].strip():
            raise ValueError(f"run receipt missing {key}")
    archive_hashes = receipt.get("archive_file_hashes")
    expected_archive_hashes = {
        checkpoint.name: record["checkpoint_sha256"],
        prediction.name: record["prediction_sha256"],
        monitoring.name: record["monitoring_sha256"],
        path.name: sha256(path),
    }
    if archive_hashes != expected_archive_hashes:
        raise ValueError("archive hash manifest mismatch")
    run_id = receipt["run_id"]
    for key, prefix in {
        "output_root": "/mnt/data2/drtao/wennie/",
        "archive_root": "/mnt/data2/drtao/pidl_archives/",
        "log_path": "/mnt/data2/drtao/wennie/",
    }.items():
        if not receipt[key].startswith(prefix) or run_id not in receipt[key]:
            raise ValueError(f"run receipt has invalid {key}")

    for key, expected in {
        "n_damage": n_damage, "n_background": n_background,
        "damage_threshold": DAMAGE_THRESHOLD, "sample_seed": seed + SAMPLE_SEED_OFFSET,
        "sample_order": "damage_then_background_no_shuffle",
    }.items():
        if record.get(key) != expected:
            raise ValueError(f"sampler field mismatch: {key}")
    if record.get("damage_node_count", 0) <= 0 or record.get("background_node_count", 0) <= 0:
        raise ValueError("invalid stratum node counts")
    p_damage = finite_number(record.get("p_damage"), "p_damage")
    p_background = finite_number(record.get("p_background"), "p_background")
    if not math.isclose(p_damage + p_background, 1.0, rel_tol=0.0, abs_tol=1e-14):
        raise ValueError("stratum masses do not sum to one")

    metrics = record.get("metrics")
    if not isinstance(metrics, dict):
        raise ValueError("metrics must be an object")
    recomputed = {}
    for metric, threshold in THRESHOLDS.items():
        value = finite_number(metrics.get(metric), metric)
        passed = value <= threshold
        stored_key = GATE_KEYS[metric]
        if strict_bool(metrics.get(stored_key), stored_key) != passed:
            raise ValueError(f"stored {stored_key} is inconsistent with {metric}")
        recomputed[stored_key] = passed
    for metric in ("strain_error_norm", "strain_reference_norm", "reference_rho_u"):
        value = finite_number(metrics.get(metric), metric)
        if metric == "strain_reference_norm" and value <= 0.0:
            raise ValueError("strain_reference_norm must be positive")
    if strict_bool(metrics.get("gate_finite"), "gate_finite") is not True:
        raise ValueError("gate_finite must pass for a completed valid run")
    joint = all(recomputed.values())
    if strict_bool(metrics.get("joint_pass"), "joint_pass") != joint:
        raise ValueError("stored joint_pass is inconsistent with recomputed gates")
    final_displacement = float(metrics["displacement_mass_rms_over_abs_Us"])
    if not math.isclose(
        trace[-1]["displacement_mass_rms_over_abs_Us"], final_displacement,
        rel_tol=0.0, abs_tol=1e-14,
    ):
        raise ValueError("final monitoring displacement does not match decision metric")
    for entry in trace:
        for label, p_key, contribution_key in (
            ("damage", "p_damage", "active_contribution"),
            ("background", "p_background", "background_contribution"),
        ):
            p_value = finite_number(entry.get(p_key), p_key)
            rms = finite_number(entry.get(label + "_conditional_rms_over_abs_Us"), label)
            if not 0 < p_value < 1 or rms < 0:
                raise ValueError("invalid regional metric")
            expected_p = p_damage if label == "damage" else p_background
            if not math.isclose(p_value, expected_p, rel_tol=0, abs_tol=1e-14):
                raise ValueError("regional probability mismatch")
            if not math.isclose(p_value * rms**2, entry[contribution_key], rel_tol=1e-12, abs_tol=1e-15):
                raise ValueError("regional RMS/contribution mismatch")
    data = reference_data[state]
    probability = data["mass"] / np.sum(data["mass"])
    active = data["damage"] > DAMAGE_THRESHOLD
    squared = np.sum((saved_uv - data["equilibrated_uv"])**2, axis=1) / abs(US)**2
    c_active = float(np.sum(probability[active] * squared[active]))
    c_background = float(np.sum(probability[~active] * squared[~active]))
    independently_computed = {
        "full_field_loss": c_active + c_background,
        "displacement_mass_rms_over_abs_Us": float(np.sqrt(c_active+c_background)),
        "active_contribution": c_active, "background_contribution": c_background,
        "damage_conditional_rms_over_abs_Us": float(np.sqrt(c_active/probability[active].sum())),
        "background_conditional_rms_over_abs_Us": float(np.sqrt(c_background/probability[~active].sum())),
        "p_damage": float(probability[active].sum()),
        "p_background": float(probability[~active].sum()),
    }
    if not math.isclose(independently_computed["displacement_mass_rms_over_abs_Us"],
                        final_displacement, rel_tol=0, abs_tol=1e-14):
        raise ValueError("saved prediction displacement disagrees with reported metric")
    for key, value in independently_computed.items():
        if not math.isclose(value, trace[-1][key], rel_tol=0, abs_tol=1e-14):
            raise ValueError(f"saved prediction regional metric mismatch: {key}")
    if record["damage_node_count"] != int(active.sum()) or record["background_node_count"] != int((~active).sum()):
        raise ValueError("saved reference stratum count mismatch")
    return {
        "state": state,
        "seed": seed,
        "alpha": alpha,
        "reference_sha256": record["reference_sha256"],
        "checkpoint_sha256": record["checkpoint_sha256"],
        **{metric: float(metrics[metric]) for metric in THRESHOLDS},
        "reference_rho_u": float(metrics["reference_rho_u"]),
        "joint_pass": joint,
        "final_damage_conditional_rms": trace[-1]["damage_conditional_rms_over_abs_Us"],
        "final_background_conditional_rms": trace[-1]["background_conditional_rms_over_abs_Us"],
        "final_active_contribution": trace[-1]["active_contribution"],
        "final_background_contribution": trace[-1]["background_contribution"],
        "monitor_initial_displacement": float(trace[0]["displacement_mass_rms_over_abs_Us"]),
        "monitor_final_displacement": float(trace[-1]["displacement_mass_rms_over_abs_Us"]),
    }


def aggregate(input_root: Path, expected_commit: str, reference_root: Path | None = None) -> tuple[list[dict], dict]:
    expected = {(state, alpha) for state in EXPECTED for alpha in ALLOCATIONS}
    rows, errors, seen = [], [], set()
    reference_root = reference_root if reference_root is not None else input_root / "inputs"
    reference_data = {}
    for state in EXPECTED:
        try:
            reference_data[state] = validate_reference(state, reference_root / f"{state}.npz")
        except Exception as exc:
            errors.append({"path": str(reference_root / f"{state}.npz"), "error": str(exc)})
    for path in sorted(input_root.glob("**/metrics.json")):
        try:
            row = validate_record(path, expected_commit, reference_data)
            pair = (row["state"], row["alpha"])
            if pair in seen:
                raise ValueError(f"duplicate state-alpha pair {pair}")
            seen.add(pair)
            rows.append(row)
        except Exception as exc:
            errors.append({"path": str(path), "error": str(exc)})
    missing = sorted(expected - seen)
    rows.sort(key=lambda r: (tuple(EXPECTED).index(r["state"]), r["alpha"]))
    arms = {}
    complete = not errors and not missing
    if complete:
        for alpha in ALLOCATIONS:
            arm = [row for row in rows if row["alpha"] == alpha]
            primary = [r for r in arm if r["state"] != "c40s4"]
            worst = max(r["displacement_mass_rms_over_abs_Us"] for r in primary)
            arms[alpha] = {
                "primary_max_displacement": worst,
                "primary_pass": worst <= 1e-3,
                "sentinel_displacement": next(r["displacement_mass_rms_over_abs_Us"] for r in arm if r["state"] == "c40s4"),
                "all_four_max_displacement": max(r["displacement_mass_rms_over_abs_Us"] for r in arm),
            }
        minimum = min(v["all_four_max_displacement"] for v in arms.values())
        selected = min((a for a in arms if arms[a]["all_four_max_displacement"] <= minimum + 1e-12), key=float)
        common_floor = all(r["displacement_mass_rms_over_abs_Us"] >= .0025 for r in rows if r["state"] != "c40s4")
    else:
        selected, common_floor = None, None
    verdict = ("INADMISSIBLE" if errors else "INCONCLUSIVE" if missing else
               "THREE_STATE_SUPERVISED_FIT_SCREEN_PASS" if any(a["primary_pass"] for a in arms.values()) else
               "NO_ALPHA_RECOVERS_THREE_STATE_DISPLACEMENT_GATE")
    return rows, {
        "protocol_revision": PROTOCOL_REVISION, "code_commit": expected_commit,
        "expected_runs": 12, "valid_completed_runs": len(rows),
        "missing": [{"state": s, "alpha": a} for s,a in missing],
        "integrity_errors": errors, "verdict": verdict, "arms": arms,
        "selected_development_alpha": selected, "descriptive_common_floor": common_floor,
        "selection_is_independent_validation": False, "stage2_authorized": False,
        "full_fem_reproduction": "NOT_QUALIFIED", "qualified_fem_teacher": "NOT_QUALIFIED",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reference-root", type=Path, required=True)
    args = parser.parse_args()
    if len(args.code_commit) != 40 or any(c not in "0123456789abcdef" for c in args.code_commit):
        parser.error("--code-commit must be a lowercase 40-character git SHA")
    if args.out.exists():
        parser.error("--out must not already exist")
    rows, summary = aggregate(args.input_root, args.code_commit, args.reference_root)
    args.out.mkdir(parents=True)
    fields = list(rows[0]) if rows else [
        "state", "seed", "reference_sha256", "checkpoint_sha256",
        *THRESHOLDS, "reference_rho_u", "joint_pass",
    ]
    with (args.out / "metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if summary["verdict"] == "INADMISSIBLE":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
