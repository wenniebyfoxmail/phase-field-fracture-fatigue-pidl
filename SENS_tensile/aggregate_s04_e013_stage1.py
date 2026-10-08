#!/usr/bin/env python3
"""Aggregate the frozen S04-E013 Stage 1 4-state x 3-seed matrix."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_s04_e013_stage1_supervised import EXPECTED, PROTOCOL_REVISION, SEEDS


def aggregate(input_root: Path) -> tuple[list[dict], dict]:
    expected_pairs = {(state, seed) for state in EXPECTED for seed in SEEDS}
    rows = []
    seen = set()
    for path in sorted(input_root.glob("**/metrics.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        pair = (record.get("state"), record.get("seed"))
        if pair not in expected_pairs:
            raise ValueError(f"unexpected state-seed pair in {path}: {pair}")
        if pair in seen:
            raise ValueError(f"duplicate state-seed pair: {pair}")
        if record.get("protocol_revision") != PROTOCOL_REVISION:
            raise ValueError(f"protocol mismatch in {path}")
        if record.get("reference_sha256") != EXPECTED[pair[0]]:
            raise ValueError(f"reference identity mismatch in {path}")
        if record.get("status") != "COMPLETED" or record.get("training") is not True:
            raise ValueError(f"invalid completed-run status in {path}")
        metrics = record.get("metrics", {})
        required_metrics = {
            "essential_bc_max_abs_error", "displacement_mass_rms_over_abs_Us",
            "strain_relative_l2", "reference_rho_u", "predicted_rho_u", "joint_pass",
        }
        if not required_metrics.issubset(metrics):
            raise ValueError(f"missing metrics in {path}")
        rows.append({
            "state": pair[0],
            "seed": pair[1],
            "reference_sha256": record["reference_sha256"],
            "checkpoint_sha256": record["checkpoint_sha256"],
            "essential_bc_max_abs_error": metrics["essential_bc_max_abs_error"],
            "displacement_mass_rms_over_abs_Us": metrics["displacement_mass_rms_over_abs_Us"],
            "strain_relative_l2": metrics["strain_relative_l2"],
            "reference_rho_u": metrics["reference_rho_u"],
            "predicted_rho_u": metrics["predicted_rho_u"],
            "joint_pass": bool(metrics["joint_pass"]),
        })
        seen.add(pair)
    missing = sorted(expected_pairs - seen)
    rows.sort(key=lambda row: (tuple(EXPECTED).index(row["state"]), SEEDS.index(row["seed"])))
    valid = len(rows)
    passes = sum(row["joint_pass"] for row in rows)
    if missing:
        verdict = "INCONCLUSIVE"
    elif passes == len(expected_pairs):
        verdict = "SUPERVISED_CAPACITY_PASS"
    else:
        verdict = "SUPERVISED_CAPACITY_FAIL_FIXED_PROCEDURE"
    summary = {
        "protocol_revision": PROTOCOL_REVISION,
        "expected_runs": len(expected_pairs),
        "valid_completed_runs": valid,
        "joint_passes": passes,
        "missing": [{"state": state, "seed": seed} for state, seed in missing],
        "verdict": verdict,
        "architecture_representability": "UNRESOLVED" if verdict != "SUPERVISED_CAPACITY_PASS" else "NOT_A_THEORETICAL_CLAIM",
        "stage2_authorized": False,
        "full_fem_reproduction": "NOT_QUALIFIED",
        "qualified_fem_teacher": "NOT_QUALIFIED",
    }
    return rows, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("--out must not already exist")
    rows, summary = aggregate(args.input_root)
    args.out.mkdir(parents=True)
    fields = list(rows[0]) if rows else [
        "state", "seed", "reference_sha256", "checkpoint_sha256",
        "essential_bc_max_abs_error", "displacement_mass_rms_over_abs_Us",
        "strain_relative_l2", "reference_rho_u", "predicted_rho_u", "joint_pass",
    ]
    with (args.out / "metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
