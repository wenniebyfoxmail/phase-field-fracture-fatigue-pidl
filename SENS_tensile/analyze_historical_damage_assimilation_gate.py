#!/usr/bin/env python3
"""Build FEM-centred figures for the c84-prior c86 assimilation gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import meshio  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from analyze_damage_observation_equilibrium_gate import (  # noqa: E402
    add_field,
    element_average,
    plot_c89_residuals,
    plot_mechanism_decomposition,
    plot_support_matrix,
)


PRIMARY = "inferred_aligned_merged_c84_prior"
BASELINE = "beta1_merged_c84_prior"
SHIFTED = "inferred_shifted_merged_c84_prior"
ORACLE = "full_c86_damage_oracle"
HISTORY_ORACLE = "inferred_aligned_true_c86_history_oracle_replay"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--vtk", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def plot_reaction_curve(curve: pd.DataFrame, manifest: dict, out: Path) -> None:
    observed = float(manifest["oracle_reaction"]["observed"])
    fig, ax = plt.subplots(figsize=(7.4, 4.8), constrained_layout=True)
    colors = {
        "aligned_visible_profile": "#277da1",
        "shifted_visible_profile_control": "#f8961e",
    }
    for geometry, group in curve.groupby("geometry"):
        if geometry == "c84_prior_only":
            continue
        feasible = group.feasible.astype(str).str.lower().eq("true")
        clean = group[feasible & np.isfinite(group.predicted_reaction)].sort_values(
            "beta"
        )
        ax.plot(
            clean.beta,
            clean.predicted_reaction,
            marker="o",
            markersize=3,
            linewidth=1.3,
            label=geometry.replace("_", " "),
            color=colors.get(geometry),
        )
        failed = group[~feasible]
        if len(failed):
            ax.scatter(
                failed.beta,
                np.full(len(failed), observed / 5.0),
                marker="x",
                color=colors.get(geometry),
                alpha=0.75,
            )
    ax.axhline(
        observed,
        color="black",
        linestyle="--",
        linewidth=1.2,
        label="FEM c86 reaction",
    )
    ax.axvline(
        float(manifest["locked_aligned_beta"]),
        color=colors["aligned_visible_profile"],
        linestyle=":",
        linewidth=1.2,
    )
    ax.axvline(
        float(manifest["locked_shifted_beta"]),
        color=colors["shifted_visible_profile_control"],
        linestyle=":",
        linewidth=1.2,
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"visible-profile degradation exponent $\beta$")
    ax.set_ylabel("top vertical reaction")
    ax.set_title("C86 reaction identifies amplitude for two different geometries")
    ax.grid(True, which="both", alpha=0.2)
    ax.legend(fontsize=8)
    fig.savefig(out / "c86_reaction_beta_identifiability.png", dpi=220)
    plt.close(fig)


def plot_postpeak_reaction(table: pd.DataFrame, out: Path) -> None:
    primary = table[table.method == PRIMARY].sort_values("step")
    fig, ax = plt.subplots(figsize=(6.8, 4.4), constrained_layout=True)
    ax.plot(
        primary.step,
        primary.observed_reaction,
        marker="o",
        linewidth=1.5,
        label="FEM c86",
        color="black",
    )
    ax.plot(
        primary.step,
        primary.predicted_reaction,
        marker="s",
        linewidth=1.5,
        label="historical assimilation",
        color="#277da1",
    )
    for row in primary.itertuples():
        ax.annotate(
            f"{row.relative_reaction_error:.2%}",
            (row.step, row.predicted_reaction),
            xytext=(0, 7),
            textcoords="offset points",
            ha="center",
            fontsize=8,
        )
    ax.set_xlabel("c86 load step")
    ax.set_ylabel("top vertical reaction")
    ax.set_title("Locked c86 postpeak reaction validation")
    ax.grid(True, alpha=0.2)
    ax.legend()
    fig.savefig(out / "c86_postpeak_reaction_validation.png", dpi=220)
    plt.close(fig)


def plot_c86_damage_and_degradation(
    polygons: np.ndarray,
    connectivity: np.ndarray,
    true_nodal_damage: np.ndarray,
    locked: dict[str, np.ndarray],
    out: Path,
) -> None:
    names = ["c84_prior_only", BASELINE, PRIMARY, SHIFTED]
    columns = [("FEM c86", true_nodal_damage)] + [
        (name, locked[f"damage_{name}"]) for name in names
    ]
    true_damage = element_average(true_nodal_damage, connectivity)
    true_g = 2.0 * np.log10(np.maximum(1.0 - true_damage, 1.0e-12))
    fig, axes = plt.subplots(
        2,
        len(columns),
        figsize=(3.0 * len(columns), 5.3),
        constrained_layout=True,
    )
    for column, (name, nodal_damage) in enumerate(columns):
        damage = element_average(nodal_damage, connectivity)
        damage_plot = add_field(
            axes[0, column], polygons, damage, cmap="viridis", vmin=0.0, vmax=1.0
        )
        g_log = 2.0 * np.log10(np.maximum(1.0 - damage, 1.0e-12))
        g_plot = add_field(
            axes[1, column], polygons, g_log, cmap="viridis", vmin=-12.0, vmax=0.0
        )
        axes[0, column].set_title(name.replace("_", "\n"), fontsize=8)
        if column == 0:
            axes[0, column].set_ylabel("damage")
            axes[1, column].set_ylabel(r"$\log_{10}g(d)$")
        else:
            axes[1, column].text(
                0.02,
                0.02,
                f"g-log MAE={np.mean(np.abs(g_log - true_g)):.2f}",
                transform=axes[1, column].transAxes,
                fontsize=7,
                bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none"},
            )
    fig.colorbar(damage_plot, ax=axes[0, :], shrink=0.65, pad=0.01)
    fig.colorbar(g_plot, ax=axes[1, :], shrink=0.65, pad=0.01)
    fig.suptitle("C84-prior c86 damage assimilation versus FEM", fontsize=14)
    fig.savefig(out / "c86_damage_and_degradation_assimilation.png", dpi=220)
    plt.close(fig)


def metric_view(metrics: pd.DataFrame, method: str, cycle: int) -> pd.Series:
    return metrics[(metrics.method == method) & (metrics.cycle == cycle)].iloc[0]


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with np.load(args.dataset, allow_pickle=False) as dataset:
        states = np.asarray(dataset["states"]).copy()
        areas = np.asarray(dataset["areas"], dtype=np.float64).copy()
    mesh = meshio.read(args.vtk)
    points = np.asarray(mesh.points)[:, :2]
    connectivity = np.asarray(mesh.cells_dict["quad"], dtype=np.int32)
    polygons = points[connectivity]
    true_nodal_damage = np.asarray(mesh.point_data["d"]).reshape(-1)
    with np.load(
        args.raw / "phase_a_locked_historical_assimilation.npz",
        allow_pickle=False,
    ) as archive:
        locked = {name: np.asarray(archive[name]).copy() for name in archive.files}
    with np.load(
        args.raw / "historical_damage_assimilation_predictions.npz",
        allow_pickle=False,
    ) as archive:
        predictions = {
            name: np.asarray(archive[name]).copy() for name in archive.files
        }
    manifest = json.loads(
        (args.raw / "RUN_MANIFEST.json").read_text(encoding="utf-8")
    )
    curve = pd.read_csv(args.raw / "phase_a_reaction_objective_curve.csv")
    postpeak = pd.read_csv(args.raw / "phase_a_postpeak_reaction_table.csv")
    metrics = pd.read_csv(args.raw / "historical_damage_assimilation_metrics.csv")

    plot_reaction_curve(curve, manifest, args.out)
    plot_postpeak_reaction(postpeak, args.out)
    plot_c86_damage_and_degradation(
        polygons, connectivity, true_nodal_damage, locked, args.out
    )

    display = {
        ORACLE: "full c86 diffuse oracle",
        BASELINE: "beta1 c84-prior merge",
        PRIMARY: "reaction-inferred c84-prior merge",
        SHIFTED: "shifted-geometry control",
        HISTORY_ORACLE: "primary + true c86 history",
    }
    order = [ORACLE, BASELINE, PRIMARY, SHIFTED, HISTORY_ORACLE]
    for cycle in (87, 89):
        candidates = {
            display[name]: predictions[f"{name}_c{cycle}"] for name in order
        }
        plot_mechanism_decomposition(
            polygons, states[cycle - 1], candidates, cycle, args.out
        )
        plot_support_matrix(
            polygons, states[cycle - 1], candidates, areas, cycle, args.out
        )
        if cycle == 89:
            plot_c89_residuals(polygons, states[cycle - 1], candidates, args.out)

    primary_c87 = metric_view(metrics, PRIMARY, 87)
    primary_c89 = metric_view(metrics, PRIMARY, 89)
    baseline_c89 = metric_view(metrics, BASELINE, 89)
    shifted_c89 = metric_view(metrics, SHIFTED, 89)
    oracle_c89 = metric_view(metrics, ORACLE, 89)
    history_oracle_c89 = metric_view(metrics, HISTORY_ORACLE, 89)
    decision = {
        "primary_candidate": PRIMARY,
        "aligned_beta": manifest["locked_aligned_beta"],
        "shifted_beta": manifest["locked_shifted_beta"],
        "peak_reaction_relative_error": manifest["aligned_inversion"][
            "relative_reaction_error"
        ],
        "postpeak_max_relative_error": manifest[
            "primary_postpeak_max_relative_error"
        ],
        "primary_full_gate_pass": manifest["primary_full_gate_pass"],
        "primary_c87_raw": {
            "log_mae": float(primary_c87.gate_log_mae),
            "correlation": float(primary_c87.gate_correlation),
            "absolute_p99_iou": float(primary_c87.gate_absolute_p99_iou),
            "support_area_ratio": float(primary_c87.gate_support_area_ratio),
        },
        "primary_c89_active": {
            "log_mae": float(primary_c89.gate_log_mae),
            "correlation": float(primary_c89.gate_correlation),
            "absolute_p99_iou": float(primary_c89.gate_absolute_p99_iou),
            "support_area_ratio": float(primary_c89.gate_support_area_ratio),
            "own_p99_iou": float(primary_c89.own_p99_iou),
        },
        "beta1_c89_active_log_mae": float(baseline_c89.gate_log_mae),
        "shifted_c89_active_log_mae": float(shifted_c89.gate_log_mae),
        "shifted_c89_active_iou": float(shifted_c89.gate_absolute_p99_iou),
        "true_history_replay_c89_active_log_mae": float(
            history_oracle_c89.gate_log_mae
        ),
        "oracle_c89_active": {
            "log_mae": float(oracle_c89.gate_log_mae),
            "correlation": float(oracle_c89.gate_correlation),
            "absolute_p99_iou": float(oracle_c89.gate_absolute_p99_iou),
            "support_area_ratio": float(oracle_c89.gate_support_area_ratio),
        },
        "interpretation": (
            "A recent diffuse prior plus visible crack geometry and reaction closes "
            "global stiffness but not the c86 spatial damage/degradation state. True "
            "c86 history alone does not rescue the inferred damage, while the full "
            "c86 diffuse-state oracle closes both c87 and c89 gates."
        ),
    }
    (args.out / "analysis_manifest.json").write_text(
        json.dumps(decision, indent=2) + "\n", encoding="utf-8"
    )
    metrics.to_csv(args.out / "gate_summary.csv", index=False)
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
