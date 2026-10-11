#!/usr/bin/env python3
"""Create the decision table and figure from an S09-E006 producer output."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle


ARMS = ("data_only_replay", "balanced_beta_0p25", "balanced_beta_1p0")
LABELS = {"data_only_replay": "data only", "balanced_beta_0p25": "beta=0.25",
          "balanced_beta_1p0": "beta=1.0"}
COLORS = {"data_only_replay": "#6B7280", "balanced_beta_0p25": "#0072B2",
          "balanced_beta_1p0": "#D55E00"}


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    args = parser.parse_args()
    metrics = json.loads((args.output / "metrics.json").read_text())
    receipt = json.loads((args.output / "receipt.json").read_text())
    updates = list(csv.DictReader((args.output / "updates.csv").open()))
    args.analysis.mkdir(parents=True, exist_ok=True)

    data_states = metrics["final"]["data_only_replay"]["states"]
    cycles = [int(item["cycle"]) for item in data_states]
    rows = []
    summary = {
        "run_id": receipt["run_id"], "commit": receipt["commit"],
        "execution_status": receipt["execution_status"],
        "primary": metrics["primary"], "arms": {},
    }
    for arm in ARMS:
        states = metrics["final"][arm]["states"]
        displacement_ratio = np.array([
            item["relative_to_affine"] / base["relative_to_affine"]
            for item, base in zip(states, data_states)
        ])
        residual_ratio = np.array([
            item["free_force_rms_ratio_to_affine"] /
            base["free_force_rms_ratio_to_affine"]
            for item, base in zip(states, data_states)
        ])
        mean_residual_ratio = float(np.mean([
            item["free_force_rms_ratio_to_affine"] for item in states
        ]) / np.mean([
            item["free_force_rms_ratio_to_affine"] for item in data_states
        ]))
        arm_updates = [item for item in updates if item["arm"] == arm]
        conflicts = sum(item.get("conflict") == "True" for item in arm_updates)
        clipped = sum(item.get("clip_applied") == "True" for item in arm_updates)
        arm_summary = {
            "aggregate_R": metrics["final"][arm]["R"],
            "max_per_state_displacement_ratio_to_data_only": float(displacement_ratio.max()),
            "mean_residual_ratio_to_data_only": mean_residual_ratio,
            "conflicting_updates": conflicts, "clipped_updates": clipped,
            "updates": len(arm_updates),
        }
        if arm != "data_only_replay":
            arm_summary.update(metrics["feasibility"][arm])
        summary["arms"][arm] = arm_summary
        for index, cycle in enumerate(cycles):
            rows.append({
                "arm": arm, "cycle": cycle,
                "R_u": states[index]["relative_to_affine"],
                "R_f": states[index]["free_force_rms_ratio_to_affine"],
                "R_u_ratio_to_data_only": displacement_ratio[index],
                "R_f_ratio_to_data_only": residual_ratio[index],
                "arm_mean_R_f_ratio_to_data_only": mean_residual_ratio,
            })
    dump(args.analysis / "summary.json", summary)
    with (args.analysis / "decision_table.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

    fig, axes = plt.subplots(1, 3, figsize=(12.2, 3.7))
    x = np.arange(len(cycles))
    width = 0.34
    for offset, arm in zip((-width / 2, width / 2), ARMS[1:]):
        values = [row["R_u_ratio_to_data_only"] for row in rows if row["arm"] == arm]
        axes[0].bar(x + offset, values, width, color=COLORS[arm], label=LABELS[arm])
    axes[0].axhline(1.10, color="black", linestyle="--", linewidth=1.2,
                    label="per-state limit 1.10")
    axes[0].set_xticks(x, [f"c{cycle}" for cycle in cycles])
    axes[0].set_ylabel("displacement error / data only")
    axes[0].set_title("A  Accuracy guard")
    axes[0].set_ylim(0.9, 1.45)
    axes[0].legend(fontsize=8)

    for offset, arm in zip((-width / 2, width / 2), ARMS[1:]):
        values = [row["R_f_ratio_to_data_only"] for row in rows if row["arm"] == arm]
        axes[1].bar(x + offset, values, width, color=COLORS[arm], label=LABELS[arm])
        mean_value = summary["arms"][arm]["mean_residual_ratio_to_data_only"]
        axes[1].scatter([x[-1] + offset], [mean_value], marker="D", s=32,
                        color="black", zorder=3)
    axes[1].axhline(0.50, color="black", linestyle="--", linewidth=1.2,
                    label="mean limit 0.50")
    axes[1].set_xticks(x, [f"c{cycle}" for cycle in cycles])
    axes[1].set_ylabel("force residual / data only")
    axes[1].set_title("B  Residual reduction")
    axes[1].set_ylim(0, 0.55)
    axes[1].text(0.02, 0.03, "diamond = arm mean", transform=axes[1].transAxes,
                 fontsize=8)

    axes[2].add_patch(Rectangle((1.0, 0.0), 0.10, 0.50,
                                color="#009E73", alpha=0.12, zorder=0))
    axes[2].axvline(1.10, color="black", linestyle="--", linewidth=1.2)
    axes[2].axhline(0.50, color="black", linestyle="--", linewidth=1.2)
    for arm in ARMS[1:]:
        xx = summary["arms"][arm]["max_per_state_displacement_ratio_to_data_only"]
        yy = summary["arms"][arm]["mean_residual_ratio_to_data_only"]
        axes[2].scatter(xx, yy, s=75, color=COLORS[arm], label=LABELS[arm], zorder=3)
    axes[2].set_xlim(1.0, 1.42); axes[2].set_ylim(0, 0.55)
    axes[2].set_xlabel("worst-state displacement ratio")
    axes[2].set_ylabel("mean residual ratio")
    axes[2].set_title("C  Joint feasibility")
    axes[2].legend(fontsize=8)
    axes[2].text(1.005, 0.02, "feasible", fontsize=8, color="#007A55")

    fig.suptitle(
        "S09-E006-R002 | fixed-damage development states | final step 700",
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(args.analysis / "pareto_rescue_decision.png", dpi=220)
    fig.savefig(args.analysis / "pareto_rescue_decision.pdf")


if __name__ == "__main__":
    main()
