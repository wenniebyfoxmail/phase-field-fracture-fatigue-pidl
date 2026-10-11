#!/usr/bin/env python3
"""Read-only S04-E014 diagnosis of completed S04-E013 predictions and logs."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from run_s04_e013_stage1_supervised import US, q4_strain, residual_metrics


STATES = ("c20s4", "c60s4", "c82s4", "c83s4")
SEEDS = (1, 7, 19)
RUN_RE = re.compile(r"R(?P<rid>\d+)-stage1b-(?P<state>c\d+s4)-seed(?P<seed>\d+)")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def parse_log(path: Path) -> tuple[str, int, list[dict]]:
    match = RUN_RE.search(path.name)
    if not match:
        raise ValueError(f"cannot parse log identity: {path}")
    points = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and {"step", "loss", "lr"} <= set(item):
            points.append(item)
    if not points or points[-1]["step"] != 10_000:
        raise ValueError(f"incomplete log trace: {path}")
    return match.group("state"), int(match.group("seed")), points


def prediction_map(root: Path) -> dict[tuple[str, int], Path]:
    result = {}
    for path in root.rglob("prediction.npz"):
        match = RUN_RE.search(str(path))
        if not match:
            continue
        key = match.group("state"), int(match.group("seed"))
        if key in result:
            raise ValueError(f"duplicate prediction {key}")
        result[key] = path
    expected = set(itertools.product(STATES, SEEDS))
    if set(result) != expected:
        raise ValueError(f"prediction matrix mismatch: {sorted(expected - set(result))}")
    return result


def load_reference(path: Path) -> dict[str, np.ndarray]:
    required = (
        "xy", "conn", "equilibrated_uv", "damage", "strain_after",
        "gp_weights", "original_p99_mask",
    )
    with np.load(path) as source:
        data = {name: source[name].copy() for name in required}
    weak = residual_metrics(data["xy"], data["conn"], data["equilibrated_uv"], data["damage"])
    data["mass"] = weak["mass"]
    return data


def weighted_mse(error: np.ndarray, mass: np.ndarray) -> float:
    return float(np.sum(mass[:, None] * error**2) / abs(US) ** 2)


def node_mask_from_elements(conn: np.ndarray, element_gp_mask: np.ndarray) -> np.ndarray:
    mask = np.zeros(int(conn.max()) + 1, dtype=bool)
    elements = np.any(element_gp_mask, axis=1)
    mask[np.unique(conn[elements])] = True
    return mask


def fraction(values: np.ndarray, mask: np.ndarray) -> float:
    total = float(values.sum())
    return float(values[mask].sum() / total) if total > 0 else float("nan")


def analyse(args: argparse.Namespace) -> None:
    args.output.mkdir(parents=True, exist_ok=True)
    predictions = prediction_map(args.predictions)
    refs = {state: load_reference(args.references / f"{state}.npz") for state in STATES}

    traces: dict[tuple[str, int], list[dict]] = {}
    for path in sorted(args.logs.glob("*.log")):
        state, seed, points = parse_log(path)
        traces[state, seed] = points
    if set(traces) != set(itertools.product(STATES, SEEDS)):
        raise ValueError("log matrix mismatch")

    convergence = []
    localisation = []
    sampling_variance = []
    all_pred: dict[tuple[str, int], np.ndarray] = {}
    for state, seed in itertools.product(STATES, SEEDS):
        ref = refs[state]
        with np.load(predictions[state, seed]) as source:
            predicted = source["uv"].copy()
        all_pred[state, seed] = predicted
        error = predicted - ref["equilibrated_uv"]
        full_loss = weighted_mse(error, ref["mass"])

        points = traces[state, seed]
        tail = np.array([p["loss"] for p in points if p["step"] >= 8000], dtype=float)
        steps = np.array([p["step"] for p in points if p["step"] >= 8000], dtype=float)
        slope = float(np.polyfit(steps, np.log10(np.maximum(tail, 1e-300)), 1)[0] * 1000)
        convergence.append({
            "state": state,
            "seed": seed,
            "full_field_loss": full_loss,
            "full_field_rms_over_Us": np.sqrt(full_loss),
            "final_sampled_loss": points[-1]["loss"],
            "final_sampled_over_full": points[-1]["loss"] / full_loss,
            "tail_sampled_median": float(np.median(tail)),
            "tail_sampled_p10": float(np.quantile(tail, 0.1)),
            "tail_sampled_p90": float(np.quantile(tail, 0.9)),
            "tail_p90_over_p10": float(np.quantile(tail, 0.9) / np.quantile(tail, 0.1)),
            "tail_log10_slope_per_1000_steps": slope,
        })

        node_energy = ref["mass"] * np.sum(error**2, axis=1)
        damage01 = ref["damage"] > 0.1
        damage05 = ref["damage"] > 0.5
        p99_nodes = node_mask_from_elements(ref["conn"], ref["original_p99_mask"])
        order = np.argsort(node_energy)[::-1]
        top_n = max(1, int(np.ceil(0.01 * len(order))))
        top_mask = np.zeros(len(order), dtype=bool)
        top_mask[order[:top_n]] = True

        pred_strain = q4_strain(ref["xy"], ref["conn"], predicted)
        component = np.array([1.0, 1.0, 0.5])[None, None, :]
        strain_energy = np.sum(
            ref["gp_weights"][:, :, None] * component
            * (pred_strain - ref["strain_after"]) ** 2,
            axis=2,
        )
        localisation.append({
            "state": state,
            "seed": seed,
            "displacement_error_fraction_damage_gt_0p1": fraction(node_energy, damage01),
            "displacement_error_fraction_damage_gt_0p5": fraction(node_energy, damage05),
            "displacement_error_fraction_active_p99_nodes": fraction(node_energy, p99_nodes),
            "displacement_error_fraction_top_1pct_nodes": fraction(node_energy, top_mask),
            "strain_error_fraction_original_active_p99": fraction(strain_energy, ref["original_p99_mask"]),
            "damage_gt_0p1_mass_fraction": float(ref["mass"][damage01].sum() / ref["mass"].sum()),
            "active_p99_node_mass_fraction": float(ref["mass"][p99_nodes].sum() / ref["mass"].sum()),
        })

        probability = ref["mass"] / ref["mass"].sum()
        point_loss = np.sum(error**2, axis=1) / abs(US) ** 2
        stratum = damage01
        p_a = float(probability[stratum].sum())
        mean = float(np.sum(probability * point_loss))
        var_simple = float(np.sum(probability * (point_loss - mean) ** 2) / 16_384)
        conditional = []
        for mask in (stratum, ~stratum):
            prob_h = probability[mask] / probability[mask].sum()
            values_h = point_loss[mask]
            mean_h = float(np.sum(prob_h * values_h))
            conditional.append(float(np.sum(prob_h * (values_h - mean_h) ** 2)))
        sigma_a, sigma_b = np.sqrt(conditional)
        alpha_opt = float((p_a * sigma_a) / (p_a * sigma_a + (1 - p_a) * sigma_b))
        row = {
            "state": state,
            "seed": seed,
            "damage_stratum_mass_probability": p_a,
            "neyman_optimal_damage_sample_fraction": alpha_opt,
            "simple_mass_sampling_loss_estimator_variance": var_simple,
        }
        for alpha in (0.5, 0.75, 0.9):
            n_a = 16_384 * alpha
            n_b = 16_384 * (1 - alpha)
            var_strat = p_a**2 * conditional[0] / n_a + (1 - p_a) ** 2 * conditional[1] / n_b
            row[f"stratified_alpha_{str(alpha).replace('.', 'p')}_variance"] = float(var_strat)
            row[f"stratified_alpha_{str(alpha).replace('.', 'p')}_over_simple"] = float(var_strat / var_simple)
        sampling_variance.append(row)

    state_rows = []
    for state in STATES:
        ref = refs[state]
        stack = np.stack([all_pred[state, seed] for seed in SEEDS])
        target = ref["equilibrated_uv"]
        mean_pred = stack.mean(axis=0)
        individual = np.array([weighted_mse(p - target, ref["mass"]) for p in stack])
        bias = weighted_mse(mean_pred - target, ref["mass"])
        variance = float(np.mean([weighted_mse(p - mean_pred, ref["mass"]) for p in stack]))
        pairwise = [np.sqrt(weighted_mse(stack[i] - stack[j], ref["mass"]))
                    for i, j in itertools.combinations(range(3), 2)]
        affine = np.column_stack((np.zeros(len(ref["xy"])), (ref["xy"][:, 1] + 0.5) * US))
        affine_mse = weighted_mse(affine - target, ref["mass"])
        state_rows.append({
            "state": state,
            "mean_individual_mse": float(individual.mean()),
            "mean_individual_rms_over_Us": float(np.sqrt(individual).mean()),
            "ensemble_bias_mse": bias,
            "between_seed_variance_mse": variance,
            "bias_fraction_of_mean_mse": bias / float(individual.mean()),
            "variance_fraction_of_mean_mse": variance / float(individual.mean()),
            "mean_pairwise_prediction_rms_over_Us": float(np.mean(pairwise)),
            "affine_baseline_rms_over_Us": float(np.sqrt(affine_mse)),
            "network_over_affine_rms_ratio": float(np.sqrt(individual.mean() / affine_mse)),
        })

    correlations = []
    for seed in SEEDS:
        for state_a, state_b in itertools.combinations(STATES, 2):
            a = np.array([p["loss"] for p in traces[state_a, seed]])
            b = np.array([p["loss"] for p in traces[state_b, seed]])
            correlations.append({
                "seed": seed,
                "state_a": state_a,
                "state_b": state_b,
                "sampled_loss_trace_correlation": float(np.corrcoef(a, b)[0, 1]),
            })

    write_csv(args.output / "convergence.csv", convergence)
    write_csv(args.output / "state_decomposition.csv", state_rows)
    write_csv(args.output / "localisation.csv", localisation)
    write_csv(args.output / "same_seed_trace_correlations.csv", correlations)
    write_csv(args.output / "sampling_variance_proxy.csv", sampling_variance)
    summary = {
        "experiment_id": "S04-E014",
        "run_id": "S04-E014-R001-stage1-posthoc",
        "source_experiment": "S04-E013 Attempt B R016-R027",
        "runs_analysed": len(convergence),
        "tail_p90_over_p10_range": [
            min(row["tail_p90_over_p10"] for row in convergence),
            max(row["tail_p90_over_p10"] for row in convergence),
        ],
        "same_seed_trace_correlation_range": [
            min(row["sampled_loss_trace_correlation"] for row in correlations),
            max(row["sampled_loss_trace_correlation"] for row in correlations),
        ],
        "same_seed_trace_correlation_mean": float(np.mean([
            row["sampled_loss_trace_correlation"] for row in correlations
        ])),
        "shared_bias_fraction_range": [
            min(row["bias_fraction_of_mean_mse"] for row in state_rows),
            max(row["bias_fraction_of_mean_mse"] for row in state_rows),
        ],
        "damage_zone_displacement_error_fraction_range": [
            min(row["displacement_error_fraction_damage_gt_0p1"] for row in localisation),
            max(row["displacement_error_fraction_damage_gt_0p1"] for row in localisation),
        ],
        "damage_zone_mass_fraction_range": [
            min(row["damage_gt_0p1_mass_fraction"] for row in localisation),
            max(row["damage_gt_0p1_mass_fraction"] for row in localisation),
        ],
        "alpha_0p9_loss_variance_over_simple_range": [
            min(row["stratified_alpha_0p9_over_simple"] for row in sampling_variance),
            max(row["stratified_alpha_0p9_over_simple"] for row in sampling_variance),
        ],
        "repair_selection": "UNBIASED_DAMAGE_STRATIFIED_SAMPLING_SCREEN",
        "producer_training_authorized": False,
        "limitations": [
            "loss-estimator variance is a final-field proxy, not gradient-variance measurement",
            "no intermediate full-field checkpoints exist",
            "damage stratum is available only in the fixed-damage conditional problem",
        ],
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.2), constrained_layout=True)
    colors = {1: "#0072B2", 7: "#D55E00", 19: "#009E73"}
    for (state, seed), points in traces.items():
        axes[0, 0].plot([p["step"] for p in points], [p["loss"] for p in points],
                        color=colors[seed], alpha=0.36, linewidth=0.9)
    axes[0, 0].set_yscale("log")
    axes[0, 0].set_xlabel("optimizer step")
    axes[0, 0].set_ylabel("sampled displacement loss")
    axes[0, 0].set_title("A  Logged minibatch loss (12 runs)")

    for seed in SEEDS:
        rows = [row for row in convergence if row["seed"] == seed]
        axes[0, 1].scatter([r["full_field_loss"] for r in rows],
                           [r["final_sampled_loss"] for r in rows],
                           color=colors[seed], label=f"seed {seed}")
    limits = [min(r["full_field_loss"] for r in convergence) * 0.5,
              max(r["final_sampled_loss"] for r in convergence) * 1.5]
    axes[0, 1].plot(limits, limits, "--", color="#333333", linewidth=1)
    axes[0, 1].set_xscale("log"); axes[0, 1].set_yscale("log")
    axes[0, 1].set_xlabel("exact full-field loss")
    axes[0, 1].set_ylabel("final logged minibatch loss")
    axes[0, 1].set_title("B  Final minibatch is not the full objective")
    axes[0, 1].legend(frameon=False)

    x = np.arange(len(STATES))
    bias_values = [r["bias_fraction_of_mean_mse"] for r in state_rows]
    var_values = [r["variance_fraction_of_mean_mse"] for r in state_rows]
    axes[1, 0].bar(x, bias_values, color="#0072B2", label="shared bias")
    axes[1, 0].bar(x, var_values, bottom=bias_values, color="#E69F00", label="seed variance")
    axes[1, 0].set_xticks(x, [s[:-2] for s in STATES])
    axes[1, 0].set_ylim(0, 1.02)
    axes[1, 0].set_ylabel("fraction of mean weighted MSE")
    axes[1, 0].set_title("C  Error shared across seeds")
    axes[1, 0].legend(frameon=False)

    loc_means = []
    for state in STATES:
        rows = [r for r in localisation if r["state"] == state]
        loc_means.append(np.mean([r["displacement_error_fraction_active_p99_nodes"] for r in rows]))
    support = []
    for state in STATES:
        rows = [r for r in localisation if r["state"] == state]
        support.append(np.mean([r["active_p99_node_mass_fraction"] for r in rows]))
    width = 0.36
    axes[1, 1].bar(x - width / 2, loc_means, width, color="#CC79A7", label="error fraction")
    axes[1, 1].bar(x + width / 2, support, width, color="#999999", label="domain-mass fraction")
    axes[1, 1].set_xticks(x, [s[:-2] for s in STATES])
    axes[1, 1].set_ylabel("fraction")
    axes[1, 1].set_title("D  Displacement error on active-p99 nodes")
    axes[1, 1].legend(frameon=False)
    for ax in axes.flat:
        ax.grid(axis="y", color="#dddddd", linewidth=0.6)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("S04-E014 R001: selecting a controllable repair from S04-E013")
    fig.savefig(args.output / "repair_diagnostic.png", dpi=220)
    fig.savefig(args.output / "repair_diagnostic.pdf")
    plt.close(fig)

    state, seed = "c20s4", 7
    ref = refs[state]
    pred = all_pred[state, seed]
    affine = np.column_stack((np.zeros(len(ref["xy"])), (ref["xy"][:, 1] + 0.5) * US))
    target_corr = np.linalg.norm(ref["equilibrated_uv"] - affine, axis=1) / abs(US)
    pred_corr = np.linalg.norm(pred - affine, axis=1) / abs(US)
    err = np.linalg.norm(pred - ref["equilibrated_uv"], axis=1) / abs(US)
    vmax = float(max(target_corr.max(), pred_corr.max()))
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.25), constrained_layout=True)
    for ax, values, title, limit in (
        (axes[0], target_corr, "target correction from affine", vmax),
        (axes[1], pred_corr, "network correction from affine", vmax),
        (axes[2], err, "absolute displacement error", float(np.quantile(err, 0.999))),
    ):
        sc = ax.scatter(ref["xy"][:, 0], ref["xy"][:, 1], c=np.minimum(values, limit),
                        s=0.7, cmap="magma", vmin=0, vmax=limit, rasterized=True)
        ax.set_aspect("equal"); ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_title(title)
        fig.colorbar(sc, ax=ax, shrink=0.82, label="magnitude / |Us|")
    fig.suptitle("c20s4 seed 7 (median final displacement error); all nodes shown")
    fig.savefig(args.output / "c20_spatial_error.png", dpi=220)
    fig.savefig(args.output / "c20_spatial_error.pdf")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    analyse(parser.parse_args())


if __name__ == "__main__":
    main()
