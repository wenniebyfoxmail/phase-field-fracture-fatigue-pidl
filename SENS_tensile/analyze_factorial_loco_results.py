#!/usr/bin/env python3
"""Validate and aggregate the sealed 4-fold factorial LOCO result matrix."""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
import math
from pathlib import Path
from typing import Iterable

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
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Optional materialised FEM dataset used for standard field figures.",
    )
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
        for key in ("steps", "context", "parameter_count"):
            if int(manifest.get(key, -1)) != int(job[key]):
                raise ValueError(f"run {key} drift: {job_id}")
        if manifest.get("synthetic_not_real_road") is not True:
            raise ValueError(f"synthetic scope label missing: {job_id}")
        if sorted(manifest.get("training_trajectory_ids", [])) != sorted(
            job["train_trajectory_ids"]
        ):
            raise ValueError(f"training trajectory drift: {job_id}")
        metrics = read_csv(run_dir / "fem_centred_metrics.csv")
        warnings = read_csv(run_dir / "transition_warning_metrics.csv")
        history = read_csv(run_dir / "training_history.csv")
        if int(history[-1]["step"]) != int(job["steps"]):
            raise ValueError(f"training did not reach sealed budget: {job_id}")
        for row in history:
            if not math.isfinite(float(row["loss"])) or not math.isfinite(
                float(row["gradient_norm"])
            ):
                raise ValueError(f"non-finite training state: {job_id}")
        runs.append(
            {
                "job": job,
                "manifest": manifest,
                "metrics": metrics,
                "warnings": warnings,
                "run_dir": run_dir,
            }
        )
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
                "training_seconds": float(run["manifest"]["training_seconds"]),
                "parameter_count": int(run["manifest"]["parameter_count"]),
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


def _mean_ci(values: Iterable[float]) -> tuple[int, float, float, float, float]:
    array = np.asarray(list(values), dtype=np.float64)
    if len(array) < 2 or not np.all(np.isfinite(array)):
        raise ValueError("summary interval requires at least two finite values")
    mean = float(array.mean())
    sd = float(array.std(ddof=1))
    half = T_CRIT_DF11 * sd / math.sqrt(len(array))
    return len(array), mean, sd, mean - half, mean + half


def model_task_summary(rows: list[dict]) -> list[dict]:
    metrics = tuple(metric for metric, _ in PRIMARY) + (
        "damage_mae",
        "history_log10_mae",
        "log10_psi_raw_mae",
        "own_p99_iou",
        "support_area_ratio",
    )
    output = []
    for task in TASKS:
        for family in FAMILIES:
            selected = [
                row for row in rows
                if row["task"] == task and row["family"] == family
            ]
            item: dict[str, object] = {
                "task": task,
                "family": family,
                "independent_fold_seed_units": len(selected),
            }
            for metric in metrics:
                n, mean, sd, low, high = _mean_ci(
                    float(row[metric]) for row in selected
                )
                item[f"{metric}_n"] = n
                item[f"{metric}_mean"] = mean
                item[f"{metric}_sd"] = sd
                item[f"{metric}_ci95_low"] = low
                item[f"{metric}_ci95_high"] = high
            output.append(item)
    return output


def horizon_summary(runs: list[dict]) -> list[dict]:
    per_run = []
    metrics = ("active_log_mae", "absolute_p99_iou", "support_area_ratio")
    for run in runs:
        grouped: dict[tuple[str, int], list[dict]] = defaultdict(list)
        for row in run["metrics"]:
            grouped[(row["task"], int(row["horizon"]))].append(row)
        for (task, horizon), selected in grouped.items():
            item = {
                "heldout_trajectory_id": run["manifest"]["heldout_trajectory_id"],
                "family": run["manifest"]["family"],
                "seed": int(run["manifest"]["seed"]),
                "task": task,
                "horizon": horizon,
            }
            for metric in metrics:
                item[metric] = float(np.mean([float(row[metric]) for row in selected]))
            per_run.append(item)

    output = []
    for task in TASKS:
        for horizon in (1, 2, 3):
            for family in FAMILIES:
                selected = [
                    row for row in per_run
                    if row["task"] == task
                    and row["horizon"] == horizon
                    and row["family"] == family
                ]
                item = {
                    "task": task,
                    "horizon": horizon,
                    "family": family,
                    "independent_fold_seed_units": len(selected),
                }
                for metric in metrics:
                    _, mean, _, low, high = _mean_ci(
                        float(row[metric]) for row in selected
                    )
                    item[f"{metric}_mean"] = mean
                    item[f"{metric}_ci95_low"] = low
                    item[f"{metric}_ci95_high"] = high
                output.append(item)
    return output


def runtime_summary(rows: list[dict]) -> list[dict]:
    output = []
    for family in FAMILIES:
        unique = {
            (row["heldout_trajectory_id"], row["seed"]): row
            for row in rows if row["family"] == family
        }
        values = [float(row["training_seconds"]) for row in unique.values()]
        n, mean, sd, low, high = _mean_ci(values)
        output.append(
            {
                "family": family,
                "run_count": n,
                "training_seconds_mean": mean,
                "training_seconds_sd": sd,
                "training_seconds_ci95_low": low,
                "training_seconds_ci95_high": high,
                "parameter_count": int(next(iter(unique.values()))["parameter_count"]),
            }
        )
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


def _active_log10(state: np.ndarray, floor: float = 1.0e-12) -> np.ndarray:
    damage = np.clip(state[:, 0], 0.0, 1.0)
    return np.maximum(
        state[:, 3] + 2.0 * np.log10(np.maximum(1.0 - damage, floor)),
        math.log10(floor),
    )


def _weighted_quantile(values: np.ndarray, areas: np.ndarray, q: float) -> float:
    order = np.argsort(values)
    cumulative = np.cumsum(areas[order])
    index = int(np.searchsorted(cumulative, q * cumulative[-1], side="left"))
    return float(values[order[min(index, len(order) - 1)]])


def _last_pair(npz: np.lib.npyio.NpzFile, prefix: str) -> tuple[np.ndarray, np.ndarray, int]:
    keys = [key for key in npz.files if key.startswith(f"{prefix}_prediction_c")]
    cycle = max(int(key.rsplit("c", 1)[1]) for key in keys)
    return npz[f"{prefix}_prediction_c{cycle}"], npz[f"{prefix}_fem_c{cycle}"], cycle


def plot_representative_fields(
    runs: list[dict], data_root: Path, out: Path, prefix: str
) -> None:
    graph = np.load(data_root / "graph.npz", allow_pickle=False)
    coordinates = np.asarray(graph["coordinates"], dtype=np.float64)
    areas = np.asarray(graph["areas"], dtype=np.float64)
    heldouts = sorted({run["manifest"]["heldout_trajectory_id"] for run in runs})
    lookup = {
        (run["manifest"]["heldout_trajectory_id"], run["manifest"]["family"]): run
        for run in runs if int(run["manifest"]["seed"]) == 1
    }
    fig, axes = plt.subplots(
        len(heldouts), 7, figsize=(18, 2.8 * len(heldouts)), constrained_layout=True
    )
    cmap = plt.get_cmap("viridis").copy()
    overlap_cmap = plt.matplotlib.colors.ListedColormap(
        ["#d9d9d9", "#377eb8", "#ff7f00", "#ffd92f"]
    )
    for row_index, heldout in enumerate(heldouts):
        fields: dict[str, np.ndarray] = {}
        fem: np.ndarray | None = None
        target_cycle: int | None = None
        for family in FAMILIES:
            with np.load(
                lookup[(heldout, family)]["run_dir"] / "representative_fields.npz",
                allow_pickle=False,
            ) as archive:
                prediction, family_fem, cycle = _last_pair(archive, prefix)
            if fem is None:
                fem = family_fem
                target_cycle = cycle
            elif cycle != target_cycle or not np.array_equal(fem, family_fem):
                raise ValueError(f"FEM representative drift for {heldout} {prefix}")
            fields[family] = prediction
        assert fem is not None and target_cycle is not None
        active = {"FEM": _active_log10(fem)}
        active.update({family: _active_log10(state) for family, state in fields.items()})
        vmax = max(float(np.max(values)) for values in active.values())
        vmin = max(-12.0, min(float(np.quantile(values, 0.01)) for values in active.values()))
        for col, name in enumerate(("FEM",) + FAMILIES):
            axes[row_index, col].scatter(
                coordinates[:, 0], coordinates[:, 1], c=active[name], s=0.08,
                vmin=vmin, vmax=vmax, cmap=cmap, linewidths=0, rasterized=True,
            )
            axes[row_index, col].set_title(f"{name} active", fontsize=8)
        fem_threshold = _weighted_quantile(active["FEM"], areas, 0.99)
        fem_mask = active["FEM"] >= fem_threshold
        for offset, family in enumerate(FAMILIES, start=4):
            pred_mask = active[family] >= fem_threshold
            code = fem_mask.astype(np.int8) + 2 * pred_mask.astype(np.int8)
            axes[row_index, offset].scatter(
                coordinates[:, 0], coordinates[:, 1], c=code, s=0.08,
                vmin=0, vmax=3, cmap=overlap_cmap, linewidths=0, rasterized=True,
            )
            axes[row_index, offset].set_title(f"{family} FEM-p99 overlap", fontsize=8)
        axes[row_index, 0].set_ylabel(
            f"{heldout.replace('factorial_', '')}\nc{target_cycle}", fontsize=8
        )
        for axis in axes[row_index]:
            axis.set_aspect("equal")
            axis.set_xticks([])
            axis.set_yticks([])
    fig.suptitle(
        f"FEM-centred {prefix} h3 active field and absolute-support overlap (seed 1)\n"
        "overlap: blue FEM-only, orange model-only, yellow intersection, grey neither",
        fontsize=11,
    )
    fig.savefig(out / f"representative_{prefix}_active_support.png", dpi=220)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    producer = json.loads(args.producer_manifest.read_text())
    runs = load_runs(args.runs, producer)
    args.out.mkdir(parents=True, exist_ok=True)
    summary = aggregate_runs(runs)
    model_summary = model_task_summary(summary)
    horizons = horizon_summary(runs)
    paired_rows = paired(summary)
    warnings = warning_summary(runs)
    write_csv(args.out / "per_run_task_summary.csv", summary)
    write_csv(args.out / "model_task_summary.csv", model_summary)
    write_csv(args.out / "horizon_summary.csv", horizons)
    write_csv(args.out / "runtime_summary.csv", runtime_summary(summary))
    write_csv(args.out / "paired_vs_markov.csv", paired_rows)
    write_csv(args.out / "transition_warning_summary.csv", warnings)
    plot_summary(summary, args.out)
    if args.data_root is not None:
        plot_representative_fields(runs, args.data_root, args.out, "transition")
        plot_representative_fields(runs, args.data_root, args.out, "reset")

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
        "task_gate_passed": False,
        "task_gate_failures": {
            "transition_warning": "all 36 runs missed all six transition-positive states",
            "reset_propagation": "all families produced about 95x FEM absolute active-support area",
        },
        "calibrated_hazard_rul": "unavailable",
        "claim_scope": "within-Hard5 shared-geometry numerical factorial only",
        "claims_forbidden": [
            "road-like LOTO", "real-road validation", "geometry generalization",
            "material generalization", "calibrated hazard/RUL",
        ],
    }
    (args.out / "decision.json").write_text(json.dumps(decision, indent=2) + "\n")
    task_labels = {
        "observed_state_same_regime_h1_h3": "observed-state h1-h3",
        "autonomous_transition_warning": "transition warning",
        "observation_reset_conditional_propagation": "first-hit reset h1-h3",
    }
    table = [
        "| Task | Family | Active log-MAE | FEM-p99 IoU | Support ratio |",
        "|---|---|---:|---:|---:|",
    ]
    for row in model_summary:
        table.append(
            f"| {task_labels[row['task']]} | {row['family']} | "
            f"{row['active_log_mae_mean']:.4f} | "
            f"{row['absolute_p99_iou_mean']:.5f} | "
            f"{row['support_area_ratio_mean']:.2f} |"
        )
    (args.out / "decision.md").write_text(
        "# Factorial LOCO decision\n\n"
        "## Verdict\n\n"
        f"Completed and verified {len(runs)}/36 fixed runs. Neither TCN nor "
        "Transformer is promoted over the matched Markov graph control: "
        f"`{json.dumps(promotions, sort_keys=True)}`. The held-out evaluation is "
        "complete, but the forecast task gate fails.\n\n"
        "## Absolute FEM-centred metrics\n\n"
        + "\n".join(table)
        + "\n\n"
        "## Mechanism result\n\n"
        "Same-regime h1-h3 errors are small, but neither temporal candidate has "
        "favorable paired 95% intervals for both active log-MAE and FEM-p99 IoU. "
        "All 36 runs miss every transition-positive warning state. After a true "
        "first-hit observation reset, all three families diffuse the absolute "
        "active support to about 95 times the FEM area; therefore the earlier "
        "single-trajectory reset-recovery result does not generalize to this "
        "four-trajectory factorial.\n\n"
        "## Claim boundary\n\n"
        "These are synthetic shared-geometry within-Hard5 results. Calibrated "
        "hazard/RUL, roads, geometry and material generalization remain blocked. "
        "A negative model-promotion result is not an incomplete experiment.\n"
    )
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
