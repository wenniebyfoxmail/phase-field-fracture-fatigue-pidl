#!/usr/bin/env python3
"""Aggregate and plot the matched multi-origin temporal reanalysis."""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
from matplotlib.colors import ListedColormap

from train_temporal_mesh_operator import area_weighted_quantile, derived_active_log10


FAMILIES = ("markov", "gru", "lstm", "tcn", "transformer", "diagonal_ssm")
DISPLAY = {
    "markov": "Markov graph",
    "gru": "GRU",
    "lstm": "LSTM",
    "tcn": "TCN",
    "transformer": "Transformer",
    "diagonal_ssm": "diagonal SSM",
}
METRICS = (
    "damage_mae",
    "damage_rmse",
    "damage_correlation",
    "alpha_bar_mae",
    "alpha_bar_rmse",
    "alpha_bar_correlation",
    "fatigue_degradation_mae",
    "fatigue_degradation_rmse",
    "fatigue_degradation_correlation",
    "log10_psi_raw_mae",
    "log10_psi_raw_rmse",
    "log10_psi_raw_correlation",
    "active_log_mae",
    "active_log_rmse",
    "active_correlation",
    "absolute_p99_iou",
    "support_area_ratio",
    "own_p99_iou",
    "centroid_offset",
    "width_x_error",
    "width_y_error",
    "active_neighbour_jump",
    "active_neighbour_jump_error",
    "support_log_distance",
)
PAIRED_METRICS = (
    ("active_log_mae", "lower"),
    ("absolute_p99_iou", "higher"),
    ("support_log_distance", "lower"),
    ("log10_psi_raw_mae", "lower"),
    ("damage_mae", "lower"),
    ("centroid_offset", "lower"),
)
T_CRIT_DF2 = 4.302652729911275


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--historical-multiscale-root", type=Path)
    return parser.parse_args()


def numeric_row(row: dict[str, str]) -> dict:
    result: dict = {}
    for key, value in row.items():
        if key in {"comparison", "conditioning"}:
            result[key] = value
            continue
        try:
            result[key] = float(value)
        except (TypeError, ValueError):
            result[key] = value
    ratio = float(result["support_area_ratio"])
    result["support_log_distance"] = abs(math.log(max(ratio, 1.0e-12)))
    return result


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty table {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def discover_runs(root: Path) -> list[tuple[Path, dict]]:
    runs = []
    for manifest_path in sorted(root.rglob("MULTI_ORIGIN_MANIFEST.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["temporal_model"] not in FAMILIES:
            raise ValueError(f"unexpected formal family {manifest['temporal_model']}")
        if manifest.get("historical_multiscale_ranking_eligible") is not False:
            raise ValueError("formal manifest must explicitly exclude historical multiscale")
        runs.append((manifest_path.parent, manifest))
    keys = {(run[1]["temporal_model"], int(run[1]["seed"])) for run in runs}
    expected = {(family, seed) for family in FAMILIES for seed in (1, 2, 3)}
    if keys != expected:
        raise ValueError(f"formal run matrix mismatch: missing={sorted(expected-keys)} extra={sorted(keys-expected)}")
    return runs


def load_rows(runs: list[tuple[Path, dict]]) -> list[dict]:
    rows = []
    for run_dir, manifest in runs:
        with (run_dir / "multi_origin_metrics.csv").open(newline="", encoding="utf-8") as handle:
            for raw in csv.DictReader(handle):
                rows.append(
                    {
                        "family": manifest["temporal_model"],
                        "seed": int(manifest["seed"]),
                        "selected_context": int(manifest["selected_context"]),
                        **numeric_row(raw),
                    }
                )
    return rows


def per_seed_task_rows(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        key = (
            row["family"],
            int(row["seed"]),
            row["comparison"],
            int(row["horizon"]),
        )
        grouped[key].append(row)
    output = []
    for (family, seed, comparison, horizon), group in sorted(grouped.items()):
        item = {
            "family": family,
            "seed": seed,
            "comparison": comparison,
            "horizon": horizon,
            "origins": ";".join(str(int(row["origin_cycle"])) for row in group),
            "origin_count": len(group),
            "conditioning": group[0]["conditioning"],
        }
        for metric in METRICS:
            item[metric] = float(np.mean([float(row[metric]) for row in group]))
        output.append(item)
    return output


def aggregate_summary(seed_rows: list[dict]) -> list[dict]:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in seed_rows:
        grouped[(row["family"], row["comparison"], int(row["horizon"]))].append(row)
    output = []
    for (family, comparison, horizon), group in sorted(grouped.items()):
        if len(group) != 3:
            raise ValueError(f"expected three seeds for {family} {comparison} h{horizon}")
        item = {
            "family": family,
            "comparison": comparison,
            "horizon": horizon,
            "seeds": len(group),
            "origin_count_per_seed": int(group[0]["origin_count"]),
            "conditioning": group[0]["conditioning"],
        }
        for metric in METRICS:
            values = np.asarray([float(row[metric]) for row in group])
            item[f"{metric}_mean"] = float(values.mean())
            item[f"{metric}_std"] = float(values.std(ddof=1))
        output.append(item)
    return output


def pooled_same_regime_seed_rows(rows: list[dict]) -> list[dict]:
    """Average the 11 observed-origin h1--h3 tasks within each model/seed."""
    grouped: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in rows:
        if row["comparison"] == "observed_fem_history_same_regime":
            grouped[(row["family"], int(row["seed"]))].append(row)
    output = []
    for (family, seed), group in sorted(grouped.items()):
        if len(group) != 11:
            raise ValueError(f"expected 11 same-regime tasks for {family} seed{seed}")
        item = {
            "family": family,
            "seed": seed,
            "comparison": "observed_fem_history_same_regime",
            "horizon": "pooled_h1_h3",
            "task_count": len(group),
            "conditioning": "identical_true_FEM_history_to_each_origin",
        }
        for metric in METRICS:
            item[metric] = float(np.mean([float(row[metric]) for row in group]))
        output.append(item)
    return output


def aggregate_pooled_same_regime(pooled_seed_rows: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in pooled_seed_rows:
        grouped[row["family"]].append(row)
    output = []
    for family, group in sorted(grouped.items()):
        if len(group) != 3:
            raise ValueError(f"expected three pooled seeds for {family}")
        item = {
            "family": family,
            "comparison": "observed_fem_history_same_regime",
            "horizon": "pooled_h1_h3",
            "seeds": len(group),
            "task_count_per_seed": int(group[0]["task_count"]),
            "conditioning": group[0]["conditioning"],
        }
        for metric in METRICS:
            values = np.asarray([float(row[metric]) for row in group])
            item[f"{metric}_mean"] = float(values.mean())
            item[f"{metric}_std"] = float(values.std(ddof=1))
        output.append(item)
    return output


def paired_pooled_same_regime(pooled_seed_rows: list[dict]) -> list[dict]:
    lookup = {
        (row["family"], int(row["seed"])): row
        for row in pooled_seed_rows
    }
    output = []
    for family in FAMILIES:
        if family == "markov":
            continue
        for metric, favorable in PAIRED_METRICS:
            differences = np.asarray([
                float(lookup[(family, seed)][metric])
                - float(lookup[("markov", seed)][metric])
                for seed in (1, 2, 3)
            ])
            mean = float(differences.mean())
            sd = float(differences.std(ddof=1))
            half = T_CRIT_DF2 * sd / math.sqrt(3.0)
            wins = int(np.sum(differences < 0.0)) if favorable == "lower" else int(np.sum(differences > 0.0))
            output.append(
                {
                    "family": family,
                    "reference": "markov",
                    "comparison": "observed_fem_history_same_regime",
                    "horizon": "pooled_h1_h3",
                    "metric": metric,
                    "difference_definition": "candidate_minus_same_seed_markov",
                    "favorable_direction": favorable,
                    "seed1_difference": float(differences[0]),
                    "seed2_difference": float(differences[1]),
                    "seed3_difference": float(differences[2]),
                    "mean_paired_difference": mean,
                    "paired_sd": sd,
                    "descriptive_95_t_ci_low": mean - half,
                    "descriptive_95_t_ci_high": mean + half,
                    "wins_out_of_3": wins,
                    "inference_note": "n=3 descriptive interval; not a significance test",
                }
            )
    return output


def paired_differences(seed_rows: list[dict]) -> list[dict]:
    lookup = {
        (row["family"], int(row["seed"]), row["comparison"], int(row["horizon"])): row
        for row in seed_rows
    }
    output = []
    comparisons = sorted({(row["comparison"], int(row["horizon"])) for row in seed_rows})
    for family in FAMILIES:
        if family == "markov":
            continue
        for comparison, horizon in comparisons:
            candidate_rows = [
                lookup[(family, seed, comparison, horizon)] for seed in (1, 2, 3)
                if (family, seed, comparison, horizon) in lookup
            ]
            markov_rows = [
                lookup[("markov", seed, comparison, horizon)] for seed in (1, 2, 3)
                if ("markov", seed, comparison, horizon) in lookup
            ]
            if len(candidate_rows) != 3 or len(markov_rows) != 3:
                continue
            for metric, favorable in PAIRED_METRICS:
                differences = np.asarray([
                    float(candidate_rows[index][metric]) - float(markov_rows[index][metric])
                    for index in range(3)
                ])
                mean = float(differences.mean())
                sd = float(differences.std(ddof=1))
                half = T_CRIT_DF2 * sd / math.sqrt(3.0)
                wins = int(np.sum(differences < 0.0)) if favorable == "lower" else int(np.sum(differences > 0.0))
                output.append(
                    {
                        "family": family,
                        "reference": "markov",
                        "comparison": comparison,
                        "horizon": horizon,
                        "metric": metric,
                        "difference_definition": "candidate_minus_same_seed_markov",
                        "favorable_direction": favorable,
                        "seed1_difference": float(differences[0]),
                        "seed2_difference": float(differences[1]),
                        "seed3_difference": float(differences[2]),
                        "mean_paired_difference": mean,
                        "paired_sd": sd,
                        "descriptive_95_t_ci_low": mean - half,
                        "descriptive_95_t_ci_high": mean + half,
                        "wins_out_of_3": wins,
                        "inference_note": "n=3 descriptive interval; not a significance test",
                    }
                )
    return output


def historical_rows(root: Path | None) -> list[dict]:
    if root is None:
        return []
    manifest = json.loads((root / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
    rows = []
    with (root / "fem_centred_metrics.csv").open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            if raw["comparison"] != "locked_rollout_from_c76":
                continue
            rows.append(
                {
                    "reference": "current_multiscale",
                    "ranking_eligible": False,
                    "privileged_inputs": "target_cycle/89;sin(2pi*phase);cos(2pi*phase)",
                    "seed_count": 1,
                    "different_implementation": True,
                    "training_steps": 3000,
                    "rollout_steps": 3,
                    "origin_cycle": 76,
                    "cycle": int(float(raw["cycle"])),
                    "horizon": int(float(raw["cycle"])) - 76,
                    "active_log_mae": float(raw["derived_active_log_mae"]),
                    "absolute_p99_iou": float(raw["absolute_p99_iou"]),
                    "support_area_ratio": float(raw["absolute_support_area_ratio"]),
                    "parameter_count": int(manifest["parameter_count"]),
                    "interpretation": "historical cycle-conditioned single-seed reference; not a matched baseline",
                }
            )
    return rows


def plot_figure_a(summary: list[dict], output: Path) -> None:
    selected = [row for row in summary if row["comparison"] == "observed_fem_history_same_regime"]
    specs = (
        ("active_log_mae", "active log MAE", False),
        ("absolute_p99_iou", "FEM-p99 absolute IoU", True),
        ("support_area_ratio", "support-area ratio", False),
    )
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 3.8), constrained_layout=True)
    for family in FAMILIES:
        family_rows = sorted(
            [row for row in selected if row["family"] == family],
            key=lambda row: int(row["horizon"]),
        )
        horizons = np.asarray([int(row["horizon"]) for row in family_rows])
        for axis, (metric, label, _) in zip(axes, specs):
            means = np.asarray([float(row[f"{metric}_mean"]) for row in family_rows])
            stds = np.asarray([float(row[f"{metric}_std"]) for row in family_rows])
            line = axis.plot(horizons, means, marker="o", label=DISPLAY[family])[0]
            axis.fill_between(horizons, means - stds, means + stds, color=line.get_color(), alpha=0.12)
            axis.set_xticks([1, 2, 3])
            axis.set_xlabel("forecast horizon from observed FEM origin")
            axis.set_ylabel(label)
            axis.grid(alpha=0.25)
            if metric == "support_area_ratio":
                axis.axhline(1.0, color="black", linewidth=0.8, linestyle="--")
    axes[0].legend(fontsize=7, ncol=2)
    fig.suptitle("Figure A: matched multi-origin same-regime propagation; bands are seed SD")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220)
    plt.close(fig)


def active_log(state: np.ndarray) -> np.ndarray:
    return derived_active_log10(torch.from_numpy(state)).numpy()


def area_overlap(
    prediction_active: np.ndarray,
    target_active: np.ndarray,
    areas: np.ndarray,
) -> tuple[np.ndarray, float, float]:
    threshold = area_weighted_quantile(target_active, areas, 0.99)
    target_mask = target_active >= threshold
    prediction_mask = prediction_active >= threshold
    overlap = target_mask.astype(np.uint8) + 2 * prediction_mask.astype(np.uint8)
    intersection = float(areas[target_mask & prediction_mask].sum())
    union = float(areas[target_mask | prediction_mask].sum())
    ratio = float(areas[prediction_mask].sum() / areas[target_mask].sum())
    return overlap, intersection / union if union else float("nan"), ratio


def median_run_by_same_regime(runs: list[tuple[Path, dict]], rows: list[dict], family: str) -> tuple[Path, dict]:
    by_seed = {}
    for seed in (1, 2, 3):
        values = [
            float(row["selection_composite"]) for row in rows
            if row["family"] == family
            and int(row["seed"]) == seed
            and row["comparison"] == "observed_fem_history_same_regime"
        ]
        by_seed[seed] = float(np.mean(values))
    selected_seed = sorted(by_seed, key=by_seed.get)[1]
    return next(run for run in runs if run[1]["temporal_model"] == family and int(run[1]["seed"]) == selected_seed)


def plot_representative_fields(
    runs: list[tuple[Path, dict]],
    rows: list[dict],
    dataset_path: Path,
    families: tuple[str, ...],
    output: Path,
    title: str,
) -> None:
    data = np.load(dataset_path, allow_pickle=False)
    coordinates = np.asarray(data["coordinates"])
    areas = np.asarray(data["areas"]).reshape(-1)
    states = np.asarray(data["states"])
    targets = {78: states[77], 80: states[79]}
    target_active_all = np.concatenate([active_log(targets[78]), active_log(targets[80])])
    vmin, vmax = np.quantile(target_active_all, [0.02, 0.995])
    residual_limit = 0.6
    support_cmap = ListedColormap(["#eeeeee", "#2166ac", "#d6604d", "#1a9850"])
    rows_to_plot = []
    for cycle, prediction_key, origin, horizon in (
        (78, "c78_from_c76_h2", 76, 2),
        (80, "c80_from_c79_h1", 79, 1),
    ):
        rows_to_plot.append((f"FEM c{cycle}", cycle, targets[cycle], origin, horizon))
        for family in families:
            run_dir, manifest = median_run_by_same_regime(runs, rows, family)
            prediction = np.load(run_dir / "multi_origin_predictions.npz")[prediction_key]
            rows_to_plot.append((f"{DISPLAY[family]} seed{manifest['seed']} c{cycle}", cycle, prediction, origin, horizon))
    fig, axes = plt.subplots(len(rows_to_plot), 3, figsize=(9.6, 2.0 * len(rows_to_plot)), constrained_layout=True)
    for row_index, (label, cycle, state, origin, horizon) in enumerate(rows_to_plot):
        target_active = active_log(targets[cycle])
        prediction_active = active_log(state)
        overlap, iou, ratio = area_overlap(prediction_active, target_active, areas)
        fields = (
            (prediction_active, "active log10", "viridis", vmin, vmax),
            (prediction_active - target_active, "prediction - FEM", "coolwarm", -residual_limit, residual_limit),
            (overlap, "support overlap", support_cmap, 0.0, 3.0),
        )
        for column, (values, panel_title, cmap, low, high) in enumerate(fields):
            axis = axes[row_index, column]
            axis.scatter(coordinates[:, 0], coordinates[:, 1], c=values, s=0.12, cmap=cmap, vmin=low, vmax=high, linewidths=0, rasterized=True)
            axis.set_aspect("equal")
            axis.set_xticks([])
            axis.set_yticks([])
            if row_index == 0:
                axis.set_title(panel_title, fontsize=9)
        axes[row_index, 0].set_ylabel(f"{label}\norigin c{origin}, h{horizon}", fontsize=7)
        axes[row_index, 2].text(0.02, 0.03, f"IoU={iou:.3f}  R={ratio:.3f}", transform=axes[row_index, 2].transAxes, fontsize=6, bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none"})
    fig.suptitle(title, fontsize=12)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220)
    plt.close(fig)


def plot_figure_c_metrics(summary: list[dict], output: Path) -> None:
    conditions = (
        ("autonomous_transition_stress_c76_c89", 13, "free c76→c89"),
        ("free_history_c87_raw_reset", 2, "raw reset"),
        ("free_history_c87_full_reset", 2, "full reset"),
        ("oracle_history_shared_sparse_c87_assimilation", 2, "sparse + oracle history"),
        ("free_history_shared_sparse_c87_assimilation", 2, "sparse + free history"),
    )
    lookup = {(row["family"], row["comparison"], int(row["horizon"])): row for row in summary}
    specs = (
        ("active_log_mae", "c89 active log MAE", "log"),
        ("absolute_p99_iou", "c89 FEM-p99 IoU", "linear"),
        ("support_area_ratio", "c89 support-area ratio", "log"),
    )
    fig, axes = plt.subplots(1, 3, figsize=(14.2, 4.3), constrained_layout=True)
    x = np.arange(len(conditions))
    for family in FAMILIES:
        for axis, (metric, label, scale) in zip(axes, specs):
            means = np.asarray([float(lookup[(family, comp, horizon)][f"{metric}_mean"]) for comp, horizon, _ in conditions])
            stds = np.asarray([float(lookup[(family, comp, horizon)][f"{metric}_std"]) for comp, horizon, _ in conditions])
            axis.errorbar(x, means, yerr=stds, marker="o", capsize=2, linewidth=1.2, label=DISPLAY[family])
            axis.set_ylabel(label)
            axis.set_yscale(scale)
            axis.grid(alpha=0.25)
            if metric == "support_area_ratio":
                axis.axhline(1.0, color="black", linewidth=0.8, linestyle="--")
    labels = [label for _, _, label in conditions]
    for axis in axes:
        axis.set_xticks(x, labels=labels, rotation=24, ha="right", fontsize=7)
    axes[0].legend(fontsize=7, ncol=2)
    fig.suptitle("Figure C: autonomous transition failure versus c87 reset/assimilation continuation")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220)
    plt.close(fig)


def plot_figure_c_fields(
    runs: list[tuple[Path, dict]],
    rows: list[dict],
    dataset_path: Path,
    output: Path,
) -> None:
    data = np.load(dataset_path, allow_pickle=False)
    coordinates = np.asarray(data["coordinates"])
    states = np.asarray(data["states"])
    fem_active = {cycle: active_log(states[cycle - 1]) for cycle in (86, 87, 89)}
    limits = np.quantile(np.concatenate(list(fem_active.values())), [0.02, 0.995])
    families = ("markov", "tcn", "transformer")
    fig, axes = plt.subplots(len(families), 4, figsize=(11.5, 5.8), constrained_layout=True)
    for row_index, family in enumerate(families):
        run_dir, manifest = median_run_by_same_regime(runs, rows, family)
        predictions = np.load(run_dir / "multi_origin_predictions.npz")
        panels = (
            (predictions["free_c86"], "c86 free rollout"),
            (states[86], "FEM c87 transition"),
            (predictions["free_c89"], "c89 free rollout"),
            (predictions["sparse_free_history_c89"], "c89 after shared sparse c87"),
        )
        for column, (state, title) in enumerate(panels):
            axis = axes[row_index, column]
            axis.scatter(coordinates[:, 0], coordinates[:, 1], c=active_log(state), s=0.12, cmap="viridis", vmin=limits[0], vmax=limits[1], linewidths=0, rasterized=True)
            axis.set_aspect("equal")
            axis.set_xticks([])
            axis.set_yticks([])
            if row_index == 0:
                axis.set_title(title, fontsize=8)
        axes[row_index, 0].set_ylabel(f"{DISPLAY[family]} seed{manifest['seed']}", fontsize=8)
    fig.suptitle("Figure C fields: free transition miss and recovery after the same sparse c87 state")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    runs = discover_runs(args.results_root)
    rows = load_rows(runs)
    seed_rows = per_seed_task_rows(rows)
    summary = aggregate_summary(seed_rows)
    paired = paired_differences(seed_rows)
    pooled_seed_rows = pooled_same_regime_seed_rows(rows)
    pooled_summary = aggregate_pooled_same_regime(pooled_seed_rows)
    pooled_paired = paired_pooled_same_regime(pooled_seed_rows)
    historical = historical_rows(args.historical_multiscale_root)
    tables = args.out / "tables"
    figures = args.out / "figures"
    write_csv(tables / "seed_level_multi_origin_metrics.csv", rows)
    write_csv(tables / "per_seed_task_metrics.csv", seed_rows)
    write_csv(tables / "matched_multi_origin_summary.csv", summary)
    write_csv(tables / "paired_seed_differences_vs_markov.csv", paired)
    write_csv(tables / "pooled_same_regime_summary.csv", pooled_summary)
    write_csv(tables / "paired_pooled_same_regime_vs_markov.csv", pooled_paired)
    if historical:
        write_csv(tables / "historical_cycle_conditioned_multiscale.csv", historical)
    plot_figure_a(summary, figures / "figure_a_multi_origin_h1_h3.png")
    plot_representative_fields(
        runs,
        rows,
        args.dataset,
        ("markov", "tcn", "transformer"),
        figures / "figure_b_representative_c78_c80_fields.png",
        "Figure B: observed-origin pre-transition fields (median same-regime seed)",
    )
    plot_representative_fields(
        runs,
        rows,
        args.dataset,
        FAMILIES,
        figures / "supplementary_all_models_c78_c80_fields.png",
        "Supplementary: all matched families at observed-origin c78/c80",
    )
    plot_figure_c_metrics(summary, figures / "figure_c_transition_reset_metrics.png")
    plot_figure_c_fields(runs, rows, args.dataset, figures / "figure_c_transition_reset_fields.png")
    manifest = {
        "protocol_id": "temporal_multi_origin_reanalysis_v1_20260720",
        "formal_run_count": len(runs),
        "formal_families": list(FAMILIES),
        "formal_baseline": "markov graph",
        "historical_multiscale_ranking_eligible": False,
        "historical_reference_in_separate_table": bool(historical),
        "outputs": [
            "tables/seed_level_multi_origin_metrics.csv",
            "tables/per_seed_task_metrics.csv",
            "tables/matched_multi_origin_summary.csv",
            "tables/paired_seed_differences_vs_markov.csv",
            "tables/pooled_same_regime_summary.csv",
            "tables/paired_pooled_same_regime_vs_markov.csv",
            "tables/historical_cycle_conditioned_multiscale.csv",
            "figures/figure_a_multi_origin_h1_h3.png",
            "figures/figure_b_representative_c78_c80_fields.png",
            "figures/supplementary_all_models_c78_c80_fields.png",
            "figures/figure_c_transition_reset_metrics.png",
            "figures/figure_c_transition_reset_fields.png",
        ],
        "claim_scope": "single-trajectory conditional propagation diagnostic",
        "paired_interval_note": "n=3 descriptive t intervals, not significance tests",
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "analysis_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
