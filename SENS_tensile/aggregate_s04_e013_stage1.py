#!/usr/bin/env python3
"""Fail-closed aggregation for the S04-E013 Stage 1 4x3 matrix."""
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
from run_s04_e013_stage1_supervised import (  # noqa: E402
    BATCH_NODES, EXPECTED, PROTOCOL_REVISION, SEEDS, STEPS,
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


def validate_record(path: Path, expected_commit: str) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    state, seed = record.get("state"), record.get("seed")
    pair = (state, seed)
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
    receipt_path = run_dir / "RUN_RECEIPT.json"
    for asset in (checkpoint, prediction, receipt_path):
        if not asset.is_file():
            raise ValueError(f"missing required asset {asset.name}")
    if sha256(checkpoint) != record.get("checkpoint_sha256"):
        raise ValueError("checkpoint SHA mismatch")
    if sha256(prediction) != record.get("prediction_sha256"):
        raise ValueError("prediction SHA mismatch")
    checkpoint_data = torch.load(checkpoint, map_location="cpu", weights_only=True)
    expected_checkpoint = {
        "protocol_revision": PROTOCOL_REVISION,
        "state": state,
        "seed": seed,
        "step": STEPS,
    }
    if any(checkpoint_data.get(key) != value for key, value in expected_checkpoint.items()):
        raise ValueError("checkpoint final-step identity mismatch")
    if not isinstance(checkpoint_data.get("model_state_dict"), dict):
        raise ValueError("checkpoint lacks model_state_dict")
    with np.load(prediction) as pred:
        if set(pred.files) != {"uv"} or pred["uv"].shape != (86_756, 2):
            raise ValueError("prediction schema mismatch")
        if not np.isfinite(pred["uv"]).all():
            raise ValueError("prediction contains nonfinite values")

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    required_receipt = {
        "status": "COMPLETED", "protocol_revision": PROTOCOL_REVISION,
        "state": state, "seed": seed, "producer_alias": "taobo",
        "code_commit": expected_commit, "dirty": False,
        "checkpoint_sha256": record["checkpoint_sha256"],
        "prediction_sha256": record["prediction_sha256"],
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
    return {
        "state": state,
        "seed": seed,
        "reference_sha256": record["reference_sha256"],
        "checkpoint_sha256": record["checkpoint_sha256"],
        **{metric: float(metrics[metric]) for metric in THRESHOLDS},
        "reference_rho_u": float(metrics["reference_rho_u"]),
        "joint_pass": joint,
    }


def aggregate(input_root: Path, expected_commit: str) -> tuple[list[dict], dict]:
    expected_pairs = {(state, seed) for state in EXPECTED for seed in SEEDS}
    rows, errors, seen = [], [], set()
    for path in sorted(input_root.glob("**/metrics.json")):
        try:
            row = validate_record(path, expected_commit)
            pair = (row["state"], row["seed"])
            if pair in seen:
                raise ValueError(f"duplicate state-seed pair {pair}")
            seen.add(pair)
            rows.append(row)
        except Exception as exc:
            errors.append({"path": str(path), "error": str(exc)})
    missing = sorted(expected_pairs - seen)
    rows.sort(key=lambda row: (tuple(EXPECTED).index(row["state"]), SEEDS.index(row["seed"])))
    passes = sum(row["joint_pass"] for row in rows)
    if errors:
        verdict = "INADMISSIBLE"
    elif missing:
        verdict = "INCONCLUSIVE"
    elif passes == len(expected_pairs):
        verdict = "SUPERVISED_CAPACITY_PASS"
    else:
        verdict = "SUPERVISED_CAPACITY_FAIL_FIXED_PROCEDURE"
    summary = {
        "protocol_revision": PROTOCOL_REVISION,
        "code_commit": expected_commit,
        "expected_runs": len(expected_pairs),
        "valid_completed_runs": len(rows),
        "joint_passes": passes,
        "missing": [{"state": state, "seed": seed} for state, seed in missing],
        "integrity_errors": errors,
        "verdict": verdict,
        "architecture_representability": (
            "NOT_A_THEORETICAL_CLAIM" if verdict == "SUPERVISED_CAPACITY_PASS" else "UNRESOLVED"
        ),
        "stage2_authorized": False,
        "full_fem_reproduction": "NOT_QUALIFIED",
        "qualified_fem_teacher": "NOT_QUALIFIED",
    }
    return rows, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if len(args.code_commit) != 40 or any(c not in "0123456789abcdef" for c in args.code_commit):
        parser.error("--code-commit must be a lowercase 40-character git SHA")
    if args.out.exists():
        parser.error("--out must not already exist")
    rows, summary = aggregate(args.input_root, args.code_commit)
    args.out.mkdir(parents=True)
    fields = list(rows[0]) if rows else [
        "state", "seed", "reference_sha256", "checkpoint_sha256",
        *THRESHOLDS, "reference_rho_u", "joint_pass",
    ]
    with (args.out / "metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if summary["verdict"] == "INADMISSIBLE":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
