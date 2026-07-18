#!/usr/bin/env python3
"""Aggregate seed metrics and render FEM-centred temporal-study figures."""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap


CORE_COMPARISON = "reused_evaluation_rollout_c76_c89"
VALIDATION_COMPARISON = "validation_rollout_c67_c76"
METRICS = (
    "damage_mae",
    "alpha_bar_mae",
    "log10_psi_raw_mae",
    "active_log_mae",
    "active_correlation",
    "absolute_p99_iou",
    "own_p99_iou",
    "support_area_ratio",
    "centroid_offset",
    "active_neighbour_jump_error",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path)
    parser.add_argument("--include-smoke", action="store_true")
    return parser.parse_args()


def numeric_row(row: dict[str, str]) -> dict[str, str | float]:
    converted: dict[str, str | float] = {}
    for key, value in row.items():
        if key == "comparison":
            converted[key] = value
            continue
        try:
            converted[key] = float(value)
        except ValueError:
            converted[key] = value
    return converted


def discover_runs(root: Path, include_smoke: bool) -> list[tuple[Path, dict]]:
    runs = []
    for manifest_path in sorted(root.rglob("RUN_MANIFEST.json")):
        if not include_smoke and "smoke" in manifest_path.parts:
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if "temporal_model" not in manifest:
            continue
        runs.append((manifest_path.parent, manifest))
    return runs


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(rows[0])
    extras = sorted(set().union(*(row.keys() for row in rows)) - set(keys))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys + extras)
        writer.writeheader()
        writer.writerows(rows)


def find_row(rows: list[dict], comparison: str, horizon: int) -> dict | None:
    for row in rows:
        if row["comparison"] == comparison and int(row["horizon"]) == horizon:
            return row
    return None


def active_log(state: np.ndarray) -> np.ndarray:
    damage = np.clip(state[:, 0], 0.0, 1.0)
    return np.maximum(state[:, 3] + 2.0 * np.log10(np.maximum(1.0 - damage, 1.0e-12)), -12.0)


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values)
    cumulative = np.cumsum(weights[order])
    index = np.searchsorted(cumulative, q * cumulative[-1], side="left")
    return float(values[order[min(index, len(order) - 1)]])


def aggregate(args: argparse.Namespace) -> tuple[list[dict], list[dict], list[tuple[Path, dict]]]:
    runs = discover_runs(args.runs_root, args.include_smoke)
    if not runs:
        raise ValueError(f"no completed temporal runs under {args.runs_root}")
    all_rows: list[dict] = []
    summaries: list[dict] = []
    for run_dir, manifest in runs:
        with (run_dir / "fem_centred_metrics.csv").open(newline="", encoding="utf-8") as handle:
            rows = [numeric_row(row) for row in csv.DictReader(handle)]
        family = manifest["temporal_model"]
        seed = int(manifest["seed"])
        stage = run_dir.parent.name
        variant = "core"
        if stage == "ablations":
            prefix = f"{family}_"
            suffix = f"_seed{seed}"
            variant = run_dir.name
            if variant.startswith(prefix):
                variant = variant[len(prefix):]
            if variant.endswith(suffix):
                variant = variant[:-len(suffix)]
        model_label = family if variant == "core" else f"{family}:{variant}"
        for row in rows:
            all_rows.append(
                {
                    "stage": stage,
                    "family": family,
                    "variant": variant,
                    "model_label": model_label,
                    "seed": seed,
                    **row,
                }
            )

        cost = manifest["cost"]
        summary = {
            "stage": stage,
            "family": family,
            "variant": variant,
            "model_label": model_label,
            "seed": seed,
            "selected_context": manifest["selected_context_validation_only"],
            "parameters": manifest["parameter_breakdown"]["total"],
            "training_wall_seconds": cost["training_wall_seconds"],
            "peak_cuda_memory_bytes": cost["peak_cuda_memory_bytes"],
            "inference_seconds_per_cycle": cost["inference_seconds_per_cycle"],
            "best_validation_selection_composite": manifest[
                "best_validation_selection_composite"
            ],
        }
        event_path = run_dir / "event_timing.json"
        if event_path.exists():
            event = json.loads(event_path.read_text(encoding="utf-8"))
            summary["true_transition_cycle"] = event["true_event_cycle"]
            summary["predicted_transition_cycle"] = event["predicted_event_cycle"]
            summary["transition_cycle_absolute_error"] = event["absolute_cycle_error"]
        for label, comparison, horizon in (
            ("validation_h9", VALIDATION_COMPARISON, 9),
            ("evaluation_h1", CORE_COMPARISON, 1),
            ("evaluation_h3", CORE_COMPARISON, 3),
            ("evaluation_h5", CORE_COMPARISON, 5),
            ("evaluation_h10", CORE_COMPARISON, 10),
            ("evaluation_h13", CORE_COMPARISON, 13),
        ):
            row = find_row(rows, comparison, horizon)
            if row is not None:
                for metric in METRICS:
                    summary[f"{label}_{metric}"] = row[metric]
        summaries.append(summary)

    if args.baseline_root is not None:
        manifest = json.loads(
            (args.baseline_root / "RUN_MANIFEST.json").read_text(encoding="utf-8")
        )
        with (args.baseline_root / "fem_centred_metrics.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            baseline_rows = [numeric_row(row) for row in csv.DictReader(handle)]
        mapped_rows = []
        for row in baseline_rows:
            comparison = str(row["comparison"])
            if comparison == "validation_rollout_from_c67":
                origin = 67
                mapped_comparison = VALIDATION_COMPARISON
            elif comparison == "locked_rollout_from_c76":
                origin = 76
                mapped_comparison = CORE_COMPARISON
            else:
                continue
            mapped = {
                **row,
                "comparison": mapped_comparison,
                "origin_cycle": origin,
                "horizon": int(float(row["cycle"])) - origin,
                "active_log_mae": row["derived_active_log_mae"],
                "active_correlation": row["derived_active_correlation"],
                "support_area_ratio": row["absolute_support_area_ratio"],
                "stage": "legacy_baseline",
                "family": "current_multiscale",
                "variant": "legacy_baseline",
                "model_label": "current_multiscale",
                "seed": int(manifest["seed"]),
            }
            mapped_rows.append(mapped)
            all_rows.append(mapped)
        baseline_summary = {
            "stage": "legacy_baseline",
            "family": "current_multiscale",
            "variant": "legacy_baseline",
            "model_label": "current_multiscale",
            "seed": int(manifest["seed"]),
            "selected_context": 1,
            "parameters": int(manifest["parameter_count"]),
        }
        for label, comparison, horizon in (
            ("validation_h9", VALIDATION_COMPARISON, 9),
            ("evaluation_h13", CORE_COMPARISON, 13),
        ):
            row = find_row(mapped_rows, comparison, horizon)
            if row is not None:
                for metric in METRICS:
                    if metric in row:
                        baseline_summary[f"{label}_{metric}"] = row[metric]
        summaries.append(baseline_summary)
    return all_rows, summaries, runs


def architecture_table(summaries: list[dict]) -> list[dict]:
    by_family: dict[str, list[dict]] = defaultdict(list)
    for row in summaries:
        by_family[str(row["model_label"])].append(row)
    markov_by_seed = {
        int(row["seed"]): row
        for row in by_family.get("markov", [])
        if row["variant"] == "core"
    }
    columns = [
        "best_validation_selection_composite",
        "validation_h9_active_log_mae",
        "validation_h9_absolute_p99_iou",
        "evaluation_h5_active_log_mae",
        "evaluation_h10_active_log_mae",
        "evaluation_h13_active_log_mae",
        "evaluation_h13_absolute_p99_iou",
        "evaluation_h13_support_area_ratio",
        "evaluation_h13_centroid_offset",
        "training_wall_seconds",
        "peak_cuda_memory_bytes",
        "inference_seconds_per_cycle",
        "transition_cycle_absolute_error",
    ]
    table = []
    for family, rows in sorted(by_family.items()):
        result: dict[str, str | int | float] = {
            "family": family,
            "seeds": len(rows),
            "parameters_mean": float(np.mean([float(row["parameters"]) for row in rows])),
            "selected_contexts": ";".join(str(row["selected_context"]) for row in sorted(rows, key=lambda item: item["seed"])),
        }
        for column in columns:
            values = np.asarray([float(row[column]) for row in rows if column in row])
            if len(values):
                result[f"{column}_mean"] = float(values.mean())
                result[f"{column}_std"] = float(values.std(ddof=1)) if len(values) > 1 else float("nan")
        paired = [
            (row, markov_by_seed[int(row["seed"])])
            for row in rows
            if int(row["seed"]) in markov_by_seed and family != "markov"
        ]
        result["validation_composite_wins_vs_markov"] = sum(
            float(row["best_validation_selection_composite"])
            < float(markov["best_validation_selection_composite"])
            for row, markov in paired
            if "best_validation_selection_composite" in row
        )
        result["c89_active_mae_wins_vs_markov"] = sum(
            float(row["evaluation_h13_active_log_mae"])
            < float(markov["evaluation_h13_active_log_mae"])
            for row, markov in paired
            if "evaluation_h13_active_log_mae" in row
        )
        table.append(result)
    return table


def plot_horizons(rows: list[dict], path: Path) -> None:
    selected = [
        row for row in rows
        if row["comparison"] == CORE_COMPARISON
        and row["variant"] in {"core", "legacy_baseline"}
    ]
    families = sorted({str(row["family"]) for row in selected})
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), constrained_layout=True)
    specs = (
        ("active_log_mae", "active log MAE", False),
        ("absolute_p99_iou", "FEM p99 absolute IoU", True),
        ("support_area_ratio", "support area ratio", False),
    )
    for family in families:
        family_rows = [row for row in selected if row["family"] == family]
        horizons = sorted({int(row["horizon"]) for row in family_rows})
        for axis, (metric, label, higher_better) in zip(axes, specs):
            means, stds = [], []
            for horizon in horizons:
                values = np.asarray(
                    [float(row[metric]) for row in family_rows if int(row["horizon"]) == horizon]
                )
                means.append(values.mean())
                stds.append(values.std(ddof=1) if len(values) > 1 else 0.0)
            linestyle = "--" if family == "current_multiscale" else "-"
            line = axis.plot(
                horizons, means, marker="o", markersize=3,
                linestyle=linestyle, label=family,
            )[0]
            axis.fill_between(
                horizons,
                np.asarray(means) - stds,
                np.asarray(means) + stds,
                color=line.get_color(),
                alpha=0.12,
            )
            axis.set_xlabel("rollout horizon (cycles)")
            axis.set_ylabel(label)
            axis.grid(alpha=0.25)
            if metric == "support_area_ratio":
                axis.axhline(1.0, color="black", linewidth=0.8, linestyle="--")
            if higher_better:
                axis.set_ylim(bottom=0.0)
    axes[0].legend(fontsize=7, ncol=2)
    fig.suptitle("c76-origin reused evaluation; bands are seed standard deviation")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def median_run_per_family(runs: list[tuple[Path, dict]]) -> list[tuple[Path, dict]]:
    grouped: dict[str, list[tuple[Path, dict]]] = defaultdict(list)
    for run in runs:
        if run[0].parent.name == "ablations":
            continue
        grouped[str(run[1]["temporal_model"])].append(run)
    selected = []
    for family, candidates in sorted(grouped.items()):
        candidates.sort(key=lambda item: float(item[1]["best_validation_selection_composite"]))
        selected.append(candidates[len(candidates) // 2])
    return selected


def plot_fields(
    runs: list[tuple[Path, dict]],
    dataset_path: Path,
    output: Path,
    baseline_root: Path | None,
) -> None:
    data = np.load(dataset_path, allow_pickle=False)
    coordinates = np.asarray(data["coordinates"])
    areas = np.asarray(data["areas"]).reshape(-1)
    target = np.asarray(data["states"])[88]
    target_active = active_log(target)
    threshold = weighted_quantile(target_active, areas, 0.99)
    target_support = target_active >= threshold
    support_cmap = ListedColormap(["#f2f2f2", "#2166ac", "#b2182b", "#1a9850"])
    candidates: list[tuple[str, np.ndarray]] = [("FEM", target)]
    if baseline_root is not None:
        baseline_npz = np.load(baseline_root / "locked_predictions.npz")
        candidates.append(("current multiscale", np.asarray(baseline_npz["c89"])))
    for run_dir, manifest in median_run_per_family(runs):
        prediction = np.load(run_dir / "reused_evaluation_predictions.npz")["c89"]
        candidates.append((str(manifest["temporal_model"]), np.asarray(prediction)))

    vmin, vmax = np.quantile(target_active, [0.02, 0.995])
    fig, axes = plt.subplots(len(candidates), 4, figsize=(12, 2.05 * len(candidates)), constrained_layout=True)
    for row_index, (label, state) in enumerate(candidates):
        prediction_active = active_log(state)
        own_threshold = weighted_quantile(prediction_active, areas, 0.99)
        pred_support = prediction_active >= threshold
        overlap = target_support.astype(np.uint8) + 2 * pred_support.astype(np.uint8)
        fields = (
            (prediction_active, "active log10", "viridis", vmin, vmax),
            (prediction_active - target_active, "signed residual", "coolwarm", -4.0, 4.0),
            (np.abs(prediction_active - target_active), "absolute residual", "magma", 0.0, 4.0),
            (
                overlap,
                "support: blue FEM, red pred, green overlap",
                support_cmap,
                0.0,
                3.0,
            ),
        )
        for column, (values, title, cmap, low, high) in enumerate(fields):
            axis = axes[row_index, column]
            axis.scatter(
                coordinates[:, 0], coordinates[:, 1], c=values, s=0.12,
                cmap=cmap, vmin=low, vmax=high, linewidths=0, rasterized=True,
            )
            axis.set_aspect("equal")
            axis.set_xticks([])
            axis.set_yticks([])
            if row_index == 0:
                axis.set_title(title, fontsize=9)
            if column == 0:
                axis.set_ylabel(label, fontsize=8)
        axes[row_index, 3].text(
            0.02, 0.02, f"own p99={own_threshold:.2f}", transform=axes[row_index, 3].transAxes,
            fontsize=6, color="white", bbox={"facecolor": "black", "alpha": 0.45, "pad": 1},
        )
    fig.suptitle("c89 FEM field, residual, and absolute-threshold support (median validation seed)")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220)
    plt.close(fig)


def plot_transition_timing(
    runs: list[tuple[Path, dict]],
    output: Path,
) -> None:
    selected = median_run_per_family(runs)
    available = [
        (run_dir, manifest)
        for run_dir, manifest in selected
        if (run_dir / "event_timing.json").exists()
    ]
    if not available:
        return
    fig, axis = plt.subplots(figsize=(8.2, 4.2), constrained_layout=True)
    first_event = json.loads(
        (available[0][0] / "event_timing.json").read_text(encoding="utf-8")
    )
    true_cycles = [row["cycle"] for row in first_event["true_signal"]]
    true_values = [row["raw_log_redistribution_rms"] for row in first_event["true_signal"]]
    axis.plot(true_cycles, true_values, color="black", linewidth=2.5, label="FEM")
    for run_dir, manifest in available:
        event = json.loads((run_dir / "event_timing.json").read_text(encoding="utf-8"))
        cycles = [row["cycle"] for row in event["predicted_signal"]]
        values = [row["raw_log_redistribution_rms"] for row in event["predicted_signal"]]
        axis.plot(cycles, values, marker="o", markersize=2.5, label=manifest["temporal_model"])
    axis.axvline(first_event["true_event_cycle"], color="black", linestyle="--", linewidth=0.9)
    axis.set_yscale("log")
    axis.set_xlabel("target cycle")
    axis.set_ylabel("area-weighted raw-log redistribution RMS")
    axis.set_title("Secondary regime-transition timing diagnostic")
    axis.grid(alpha=0.25)
    axis.legend(fontsize=7, ncol=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    rows, summaries, runs = aggregate(args)
    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "tables" / "seed_level_metrics.csv", rows)
    write_csv(args.out / "tables" / "seed_run_summary.csv", summaries)
    write_csv(args.out / "tables" / "architecture_ablation_table.csv", architecture_table(summaries))
    plot_horizons(rows, args.out / "figures" / "rollout_horizon_curves.png")
    plot_fields(
        runs,
        args.dataset,
        args.out / "figures" / "fem_field_residual_support_c89.png",
        args.baseline_root,
    )
    plot_transition_timing(
        runs,
        args.out / "figures" / "transition_timing_signals.png",
    )
    manifest = {
        "runs": len(runs),
        "families": sorted({manifest["temporal_model"] for _, manifest in runs}),
        "claim_scope": "within-trajectory temporal diagnostic",
        "c89_status": "reused evaluation benchmark",
        "outputs": [
            "tables/seed_level_metrics.csv",
            "tables/seed_run_summary.csv",
            "tables/architecture_ablation_table.csv",
            "figures/rollout_horizon_curves.png",
            "figures/fem_field_residual_support_c89.png",
            "figures/transition_timing_signals.png",
        ],
    }
    (args.out / "analysis_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
