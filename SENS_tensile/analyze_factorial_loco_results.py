#!/usr/bin/env python3
"""Validate and aggregate the sealed 4-fold factorial LOCO result matrix."""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


FAMILIES = ("markov", "tcn", "transformer")
TASKS = (
    "observed_state_same_regime_h1_h3",
    "autonomous_transition_warning",
    "observation_reset_conditional_propagation",
)
PRIMARY = (
    ("active_log_mae", "lower"),
    ("absolute_p99_iou", "higher"),
    ("support_area_ratio_log_error", "lower"),
    ("centroid_offset", "lower"),
    ("width_y_error", "lower"),
)
T_CRIT_DF11 = 2.200985


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--producer-manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"empty result table: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_runs(root: Path, producer: dict) -> list[dict]:
    expected = {job["job_id"]: job for job in producer["jobs"]}
    runs = []
    for job_id, job in expected.items():
        run_dir = root / "runs" / job_id
        manifest_path = run_dir / "RUN_MANIFEST.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"missing completed run: {job_id}")
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("status") != "complete":
            raise ValueError(f"incomplete run manifest: {job_id}")
        identity = (
            manifest.get("heldout_trajectory_id"),
            manifest.get("family"),
            int(manifest.get("seed", -1)),
        )
        expected_identity = (
            job["held_out_trajectory_id"], job["family"], int(job["seed"])
        )
        if identity != expected_identity:
            raise ValueError(f"run identity drift: {job_id}")
        metrics = read_csv(run_dir / "fem_centred_metrics.csv")
        warnings = read_csv(run_dir / "transition_warning_metrics.csv")
        runs.append({"job": job, "manifest": manifest, "metrics": metrics, "warnings": warnings})
    if len(runs) != 36:
        raise ValueError("sealed matrix requires exactly 36 runs")
    return runs


def aggregate_runs(runs: list[dict]) -> list[dict]:
    output = []
    for run in runs:
        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in run["metrics"]:
            grouped[row["task"]].append(row)
        if set(grouped) != set(TASKS):
            raise ValueError("run does not cover all three sealed tasks")
        for task, rows in grouped.items():
            item = {
                "heldout_trajectory_id": run["manifest"]["heldout_trajectory_id"],
                "family": run["manifest"]["family"],
                "seed": int(run["manifest"]["seed"]),
                "task": task,
                "evaluated_states": len(rows),
            }
            numeric = (
                "damage_mae", "damage_rmse", "damage_correlation",
                "history_log10_mae", "history_log10_rmse", "history_log10_correlation",
                "log10_psi_raw_mae", "log10_psi_raw_rmse", "log10_psi_raw_correlation",
                "active_log_mae", "active_log_rmse", "active_correlation",
                "absolute_p99_iou", "own_p99_iou", "support_area_ratio",
                "centroid_offset", "width_x_error", "width_y_error",
            )
            for metric in numeric:
                values = np.asarray([float(row[metric]) for row in rows])
                item[metric] = float(np.nanmean(values))
            item["support_area_ratio_log_error"] = float(
                np.mean(np.abs(np.log(np.maximum(
                    [float(row["support_area_ratio"]) for row in rows], 1e-8
                ))))
            )
            output.append(item)
    return output


def paired(candidate_rows: list[dict]) -> list[dict]:
    lookup = {
        (row["heldout_trajectory_id"], row["family"], row["seed"], row["task"]): row
        for row in candidate_rows
    }
    output = []
    for family in ("tcn", "transformer"):
        for task in TASKS:
            for metric, direction in PRIMARY:
                values = []
                for heldout in sorted({row["heldout_trajectory_id"] for row in candidate_rows}):
                    for seed in (1, 2, 3):
                        candidate = lookup[(heldout, family, seed, task)][metric]
                        control = lookup[(heldout, "markov", seed, task)][metric]
                        values.append(float(candidate) - float(control))
                array = np.asarray(values)
                mean = float(array.mean())
                sd = float(array.std(ddof=1))
                half = T_CRIT_DF11 * sd / math.sqrt(len(array))
                wins = int(np.sum(array < 0 if direction == "lower" else array > 0))
                output.append(
                    {
                        "family": family,
                        "reference": "markov",
                        "task": task,
                        "metric": metric,
                        "favorable_direction": direction,
                        "paired_n": len(array),
                        "mean_candidate_minus_markov": mean,
                        "ci95_low": mean - half,
                        "ci95_high": mean + half,
                        "favorable_pairs": wins,
                        "ci_excludes_zero_favorably": bool(
                            mean + half < 0 if direction == "lower" else mean - half > 0
                        ),
                    }
                )
    return output


def warning_summary(runs: list[dict]) -> list[dict]:
    output = []
    for run in runs:
        rows = run["warnings"]
        output.append(
            {
                "heldout_trajectory_id": run["manifest"]["heldout_trajectory_id"],
                "family": run["manifest"]["family"],
                "seed": int(run["manifest"]["seed"]),
                "evaluated_warning_states": len(rows),
                "missed_transition_count": sum(int(row["missed_transition"]) for row in rows),
                "false_warning_count": sum(int(row["false_warning"]) for row in rows),
                "calibrated_probability": "unavailable",
                "rul_distribution": "unavailable",
            }
        )
    return output


def plot_summary(rows: list[dict], out: Path) -> None:
    fig, axes = plt.subplots(3, 3, figsize=(13, 10), constrained_layout=True)
    metrics = (
        ("active_log_mae", "Active log-MAE"),
        ("absolute_p99_iou", "FEM-p99 IoU"),
        ("support_area_ratio_log_error", "|log support ratio|"),
    )
    for row_index, task in enumerate(TASKS):
        for col, (metric, label) in enumerate(metrics):
            axis = axes[row_index, col]
            for index, family in enumerate(FAMILIES):
                values = [float(row[metric]) for row in rows if row["task"] == task and row["family"] == family]
                axis.scatter(np.full(len(values), index), values, alpha=0.65, s=24)
                axis.plot(index, np.mean(values), marker="_", markersize=18, color="black")
            axis.set_xticks(range(3), FAMILIES, rotation=20)
            axis.set_ylabel(label)
            if col == 0:
                axis.set_title(task.replace("_", " "), loc="left", fontsize=9)
            axis.grid(alpha=0.2)
    fig.suptitle("Held-out factorial LOCO: every fold and seed")
    fig.savefig(out / "factorial_loco_task_summary.png", dpi=220)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    producer = json.loads(args.producer_manifest.read_text())
    runs = load_runs(args.runs, producer)
    args.out.mkdir(parents=True, exist_ok=True)
    summary = aggregate_runs(runs)
    paired_rows = paired(summary)
    warnings = warning_summary(runs)
    write_csv(args.out / "per_run_task_summary.csv", summary)
    write_csv(args.out / "paired_vs_markov.csv", paired_rows)
    write_csv(args.out / "transition_warning_summary.csv", warnings)
    plot_summary(summary, args.out)

    promotions = {}
    for family in ("tcn", "transformer"):
        required = [
            row for row in paired_rows
            if row["family"] == family
            and row["task"] in {
                "observed_state_same_regime_h1_h3",
                "observation_reset_conditional_propagation",
            }
            and row["metric"] in {"active_log_mae", "absolute_p99_iou"}
        ]
        promotions[family] = bool(required) and all(
            row["ci_excludes_zero_favorably"] for row in required
        )
    decision = {
        "status": "complete",
        "run_count": len(runs),
        "promotion_rule": (
            "both active log-MAE and absolute-p99 IoU must have favorable paired "
            "95% intervals for same-regime and reset tasks"
        ),
        "promotions": promotions,
        "calibrated_hazard_rul": "unavailable",
        "claim_scope": "within-Hard5 shared-geometry numerical factorial only",
        "claims_forbidden": [
            "road-like LOTO", "real-road validation", "geometry generalization",
            "material generalization", "calibrated hazard/RUL",
        ],
    }
    (args.out / "decision.json").write_text(json.dumps(decision, indent=2) + "\n")
    (args.out / "decision.md").write_text(
        "# Factorial LOCO decision\n\n"
        f"Completed {len(runs)}/36 fixed runs. Promotion results: "
        f"`{json.dumps(promotions, sort_keys=True)}`.\n\n"
        "These are synthetic shared-geometry within-Hard5 results. Calibrated "
        "hazard/RUL, roads, geometry and material generalization remain blocked.\n"
    )
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()

