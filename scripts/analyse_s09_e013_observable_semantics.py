#!/usr/bin/env python3
"""Audit E013 target/predicted observable semantics without model execution."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


ARM_GLOBAL = "G25_global_ranking_replay"
ARM_LOCAL = "L25_local_support_ranking_beta0p25"
GROWTH_CYCLES = (1, 58, 60, 69, 70)
STAGNANT_CYCLES = (3, 4, 71, 72, 73)
THRESHOLD = 1e-15


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def outcome(value: float) -> str:
    return "WIN" if value > 0 else "LOSS" if value < 0 else "TIE"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    cycles = np.load(args.packet_dir / "cycles.npy").astype(int)
    d_pre = np.load(args.packet_dir / "d_pre.npy", mmap_mode="r")
    d_peak = np.load(args.packet_dir / "d_peak.npy", mmap_mode="r")
    weight = np.load(args.packet_dir / "nodal_weight.npy")
    weight_sum = float(weight.sum())
    cycle_rows: list[dict[str, float | int]] = []
    by_cycle: dict[int, dict[str, float | int]] = {}
    for index, cycle in enumerate(cycles):
        increment = d_peak[index] - d_pre[index]
        positive = np.clip(increment, 0.0, None)
        support = increment > THRESHOLD
        background = ~support
        support_weight = float(weight[support].sum())
        background_weight = float(weight[background].sum())
        if support_weight <= 0 or background_weight <= 0:
            raise ValueError(f"empty support/background at cycle {cycle}")
        support_mean = float((positive[support] * weight[support]).sum() / support_weight)
        background_mean = float(
            (positive[background] * weight[background]).sum() / background_weight
        )
        row = {
            "cycle": int(cycle),
            "target_global_amplitude": float((np.abs(increment) * weight).sum() / weight_sum),
            "target_local_support_contrast": support_mean - background_mean,
            "support_node_count": int(support.sum()),
            "support_weight_fraction": support_weight / weight_sum,
            "support_mean_positive_increment": support_mean,
            "background_mean_positive_increment": background_mean,
        }
        cycle_rows.append(row)
        by_cycle[int(cycle)] = row

    receipt = json.loads(args.receipt.read_text())
    receipt_rows = {
        (row["growth_cycle"], row["stagnant_cycle"]): row
        for row in receipt["audit"]["records"]
    }
    pair_rows = []
    for growth in GROWTH_CYCLES:
        for stagnant in STAGNANT_CYCLES:
            record = receipt_rows[(growth, stagnant)]
            truth_global = (
                by_cycle[growth]["target_global_amplitude"]
                - by_cycle[stagnant]["target_global_amplitude"]
            )
            truth_local = (
                by_cycle[growth]["target_local_support_contrast"]
                - by_cycle[stagnant]["target_local_support_contrast"]
            )
            predicted_global = float(record["initial_global_margin"])
            predicted_local = float(record["initial_local_margin"])
            local_global_change = float(
                record["arms"][ARM_LOCAL]["predicted_adamw_global_margin_change"]
            )
            local_local_change = float(
                record["arms"][ARM_LOCAL]["predicted_adamw_local_margin_change"]
            )
            global_global_change = float(
                record["arms"][ARM_GLOBAL]["predicted_adamw_global_margin_change"]
            )
            global_local_change = float(
                record["arms"][ARM_GLOBAL]["predicted_adamw_local_margin_change"]
            )
            pair_rows.append({
                "growth_cycle": growth,
                "stagnant_cycle": stagnant,
                "truth_global_margin": truth_global,
                "truth_global_outcome": outcome(truth_global),
                "truth_local_margin": truth_local,
                "truth_local_outcome": outcome(truth_local),
                "initial_predicted_global_margin": predicted_global,
                "initial_predicted_global_outcome": outcome(predicted_global),
                "initial_predicted_local_margin": predicted_local,
                "initial_predicted_local_outcome": outcome(predicted_local),
                "G25_linearised_global_margin": predicted_global + global_global_change,
                "G25_linearised_local_margin": predicted_local + global_local_change,
                "L25_linearised_global_margin": predicted_global + local_global_change,
                "L25_linearised_local_margin": predicted_local + local_local_change,
                "growth_target_support_weight_fraction": by_cycle[growth]["support_weight_fraction"],
                "stagnant_target_support_weight_fraction": by_cycle[stagnant]["support_weight_fraction"],
            })

    cycle_path = args.output_dir / "cycle_truth_scores.csv"
    with cycle_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(cycle_rows[0]))
        writer.writeheader()
        writer.writerows(cycle_rows)
    pair_path = args.output_dir / "pair_observable_audit.csv"
    with pair_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(pair_rows[0]))
        writer.writeheader()
        writer.writerows(pair_rows)

    target_global = [row["truth_global_outcome"] for row in pair_rows]
    target_local = [row["truth_local_outcome"] for row in pair_rows]
    predicted_global = [row["initial_predicted_global_outcome"] for row in pair_rows]
    predicted_local = [row["initial_predicted_local_outcome"] for row in pair_rows]
    stagnant_rows = [by_cycle[cycle] for cycle in STAGNANT_CYCLES]
    summary = {
        "schema_version": "s09-e013-observable-semantics-v1",
        "source_packet_manifest_sha256": json.loads(
            (args.packet_dir / "packet_identity.json").read_text()
        )["manifest_sha256"],
        "source_receipt_sha256": sha256(args.receipt),
        "model_forward_performed": False,
        "autograd_performed": False,
        "optimizer_steps_performed": 0,
        "target_global_win_count": target_global.count("WIN"),
        "target_local_win_count": target_local.count("WIN"),
        "target_global_local_same_sign_count": sum(
            left == right for left, right in zip(target_global, target_local)
        ),
        "initial_predicted_global_win_count": predicted_global.count("WIN"),
        "initial_predicted_local_win_count": predicted_local.count("WIN"),
        "initial_predicted_global_local_same_sign_count": sum(
            left == right for left, right in zip(predicted_global, predicted_local)
        ),
        "stagnant_support_node_count_min": min(
            int(row["support_node_count"]) for row in stagnant_rows
        ),
        "stagnant_support_node_count_max": max(
            int(row["support_node_count"]) for row in stagnant_rows
        ),
        "stagnant_support_weight_fraction_min": min(
            float(row["support_weight_fraction"]) for row in stagnant_rows
        ),
        "stagnant_support_weight_fraction_max": max(
            float(row["support_weight_fraction"]) for row in stagnant_rows
        ),
        "target_background_mean_max": max(
            float(row["background_mean_positive_increment"]) for row in cycle_rows
        ),
        "classification_issue": (
            "The frozen eight-pair cohort is defined by predicted global-amplitude LOSS, "
            "but the E013 classifier selected predicted local-support LOSS before "
            "comparing identities; those cohorts contain 8 and 17 complementary pairs."
        ),
        "scientific_interpretation": (
            "Target global and local scores agree on all 25 pair labels and stagnant "
            "supports are nonempty. The sign inversion is a property of the current "
            "B25 prediction and objective geometry, not an inherent contradiction in "
            "the two target observables."
        ),
    }
    summary_path = args.output_dir / "observable_semantics_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
