#!/usr/bin/env python3
"""Build FEM-centred figures for the c86 reaction-conditioned inversion gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import meshio
import numpy as np
import pandas as pd

from analyze_damage_observation_equilibrium_gate import (
    add_field,
    derived,
    element_average,
    plot_c89_residuals,
    plot_mechanism_decomposition,
    plot_support_matrix,
    support_metrics,
)


PRIMARY = "reaction_inferred_aligned_skeleton"
BASELINE = "beta1_aligned_skeleton"
SHIFTED = "reaction_inferred_shifted_skeleton_control"
ORACLE = "full_damage_oracle"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--vtk", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def plot_reaction_curve(curve: pd.DataFrame, manifest: dict, out: Path) -> None:
    observed = float(manifest["oracle_reaction"]["observed"])
    fig, ax = plt.subplots(figsize=(7.2, 4.8), constrained_layout=True)
    colors = {"aligned_skeleton": "#277da1", "shifted_skeleton_control": "#f8961e"}
    for geometry, group in curve.groupby("geometry"):
        feasible = group.feasible.astype(str).str.lower().eq("true")
        clean = group[feasible & np.isfinite(group.predicted_reaction)].sort_values("beta")
        ax.plot(
            clean.beta,
            clean.predicted_reaction,
            marker="o",
            markersize=3,
            linewidth=1.4,
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
    ax.axhline(observed, color="black", linestyle="--", linewidth=1.2, label="FEM c86 reaction")
    ax.axvline(float(manifest["locked_beta"]), color="#277da1", linestyle=":", linewidth=1.2)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"degradation amplitude exponent $\beta$")
    ax.set_ylabel("top vertical reaction")
    ax.set_title("C86 reaction identifies amplitude but not crack location")
    ax.grid(True, which="both", alpha=0.2)
    ax.legend(fontsize=8)
    fig.savefig(out / "c86_reaction_beta_identifiability.png", dpi=220)
    plt.close(fig)


def plot_c86_damage_and_degradation(
    polygons: np.ndarray,
    connectivity: np.ndarray,
    true_nodal_damage: np.ndarray,
    locked: dict[str, np.ndarray],
    names: list[str],
    out: Path,
) -> None:
    true_damage = element_average(true_nodal_damage, connectivity)
    true_g_log = 2.0 * np.log10(np.maximum(1.0 - true_damage, 1.0e-12))
    fig, axes = plt.subplots(2, len(names) + 1, figsize=(3.0 * (len(names) + 1), 5.2), constrained_layout=True)
    columns = [("FEM c86", true_damage)] + [
        (name, element_average(locked[f"damage_{name}"], connectivity)) for name in names
    ]
    for column, (name, damage) in enumerate(columns):
        damage_plot = add_field(
            axes[0, column], polygons, damage, cmap="viridis", vmin=0.0, vmax=1.0
        )
        g_log = 2.0 * np.log10(np.maximum(1.0 - damage, 1.0e-12))
        degradation_plot = add_field(
            axes[1, column], polygons, g_log, cmap="viridis", vmin=-12.0, vmax=0.0
        )
        axes[0, column].set_title(name.replace("_", "\n"), fontsize=8)
        if column == 0:
            axes[0, column].set_ylabel("damage")
            axes[1, column].set_ylabel(r"$\log_{10} g(d)$")
        if column > 0:
            axes[1, column].text(
                0.02,
                0.02,
                f"g-log MAE={np.mean(np.abs(g_log - true_g_log)):.2f}",
                transform=axes[1, column].transAxes,
                fontsize=7,
                bbox={"facecolor": "white", "alpha": 0.7, "edgecolor": "none"},
            )
    fig.colorbar(damage_plot, ax=axes[0, :], shrink=0.65, pad=0.01)
    fig.colorbar(degradation_plot, ax=axes[1, :], shrink=0.65, pad=0.01)
    fig.suptitle("C86 observed geometry and reaction-inferred degradation", fontsize=14)
    fig.savefig(out / "c86_damage_and_degradation_inversion.png", dpi=220)
    plt.close(fig)


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
    with np.load(args.raw / "phase_a_locked_damage_inversion.npz", allow_pickle=False) as archive:
        locked = {name: np.asarray(archive[name]).copy() for name in archive.files}
    with np.load(args.raw / "reaction_inversion_predictions.npz", allow_pickle=False) as archive:
        predictions = {name: np.asarray(archive[name]).copy() for name in archive.files}
    manifest = json.loads((args.raw / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
    curve = pd.read_csv(args.raw / "phase_a_reaction_objective_curve.csv")
    metrics = pd.read_csv(args.raw / "reaction_inversion_metrics.csv")

    plot_reaction_curve(curve, manifest, args.out)
    c86_names = [BASELINE, PRIMARY, SHIFTED]
    plot_c86_damage_and_degradation(
        polygons, connectivity, true_nodal_damage, locked, c86_names, args.out
    )

    display = {
        ORACLE: "full damage oracle",
        BASELINE: "beta1 skeleton",
        PRIMARY: "reaction inferred aligned",
        SHIFTED: "reaction inferred shifted",
        "initial_precrack_control": "initial precrack",
        "untouched_c86_rollout": "untouched rollout",
    }
    candidate_order = [
        ORACLE,
        BASELINE,
        PRIMARY,
        SHIFTED,
        "initial_precrack_control",
        "untouched_c86_rollout",
    ]
    c87_candidates = {
        display[name]: predictions[f"{name}_c87"] for name in candidate_order
    }
    c89_candidates = {
        display[name]: predictions[f"{name}_c89"] for name in candidate_order
    }
    plot_mechanism_decomposition(polygons, states[86], c87_candidates, 87, args.out)
    plot_support_matrix(polygons, states[86], c87_candidates, areas, 87, args.out)
    plot_mechanism_decomposition(polygons, states[88], c89_candidates, 89, args.out)
    plot_support_matrix(polygons, states[88], c89_candidates, areas, 89, args.out)
    plot_c89_residuals(polygons, states[88], c89_candidates, args.out)

    support_rows: list[dict[str, float | int | str]] = []
    for cycle, candidates in ((87, c87_candidates), (89, c89_candidates)):
        target_fields = derived(states[cycle - 1])
        for label, prediction in candidates.items():
            prediction_fields = derived(prediction)
            _, raw_iou, raw_ratio, raw_threshold = support_metrics(
                target_fields["raw_log"], prediction_fields["raw_log"], areas
            )
            _, active_iou, active_ratio, active_threshold = support_metrics(
                target_fields["active_log"], prediction_fields["active_log"], areas
            )
            support_rows.append(
                {
                    "method_label": label,
                    "cycle": cycle,
                    "raw_absolute_p99_iou": raw_iou,
                    "raw_support_area_ratio": raw_ratio,
                    "raw_log_p99_threshold": raw_threshold,
                    "active_absolute_p99_iou": active_iou,
                    "active_support_area_ratio": active_ratio,
                    "active_log_p99_threshold": active_threshold,
                }
            )
    support = pd.DataFrame(support_rows)
    support.to_csv(args.out / "raw_and_active_support_metrics.csv", index=False)
    metrics.to_csv(args.out / "gate_summary.csv", index=False)

    primary_c87 = metrics[(metrics.method == PRIMARY) & (metrics.cycle == 87)].iloc[0]
    primary_c89 = metrics[(metrics.method == PRIMARY) & (metrics.cycle == 89)].iloc[0]
    baseline_c89 = metrics[(metrics.method == BASELINE) & (metrics.cycle == 89)].iloc[0]
    shifted_c89 = metrics[(metrics.method == SHIFTED) & (metrics.cycle == 89)].iloc[0]
    oracle_c89 = metrics[(metrics.method == ORACLE) & (metrics.cycle == 89)].iloc[0]
    c87_pass = bool(
        primary_c87.log10_psi_raw_mae <= 0.30
        and primary_c87.log10_psi_raw_correlation >= 0.90
        and primary_c87.absolute_p99_iou >= 0.70
        and 0.5 <= primary_c87.absolute_support_area_ratio <= 2.0
    )
    c89_pass = bool(
        primary_c89.derived_active_log_mae <= 0.30
        and primary_c89.derived_active_correlation >= 0.90
        and primary_c89.absolute_p99_iou >= 0.70
        and 0.5 <= primary_c89.absolute_support_area_ratio <= 2.0
    )
    decision = {
        "primary_candidate": PRIMARY,
        "locked_beta": manifest["locked_beta"],
        "c86_reaction_identifiable": manifest["inversion"]["aligned"]["identifiable"],
        "c86_reaction_relative_error": manifest["inversion"]["aligned"][
            "relative_reaction_error"
        ],
        "c86_postpeak_max_relative_error": manifest[
            "maximum_postpeak_reaction_relative_error"
        ],
        "c87_raw_gate_pass": c87_pass,
        "c89_active_gate_pass": c89_pass,
        "full_gate_pass": bool(c87_pass and c89_pass),
        "c87": {
            "raw_log_mae": float(primary_c87.log10_psi_raw_mae),
            "raw_correlation": float(primary_c87.log10_psi_raw_correlation),
            "absolute_p99_iou": float(primary_c87.absolute_p99_iou),
            "support_area_ratio": float(primary_c87.absolute_support_area_ratio),
        },
        "c89": {
            "active_log_mae": float(primary_c89.derived_active_log_mae),
            "active_correlation": float(primary_c89.derived_active_correlation),
            "absolute_p99_iou": float(primary_c89.absolute_p99_iou),
            "support_area_ratio": float(primary_c89.absolute_support_area_ratio),
        },
        "beta1_c89_active_log_mae": float(baseline_c89.derived_active_log_mae),
        "shifted_c89_active_correlation": float(shifted_c89.derived_active_correlation),
        "shifted_c89_absolute_p99_iou": float(shifted_c89.absolute_p99_iou),
        "oracle_c89_active_log_mae": float(oracle_c89.derived_active_log_mae),
        "oracle_c89_absolute_p99_iou": float(oracle_c89.absolute_p99_iou),
        "interpretation": (
            "Reaction identifies global degradation amplitude and removes most of the "
            "energetic scale error, but one scalar cannot recover the spatially varying "
            "near-core degradation/process-zone distribution."
        ),
    }
    (args.out / "analysis_manifest.json").write_text(
        json.dumps(decision, indent=2) + "\n", encoding="utf-8"
    )
    readme = f"""# Reaction-Conditioned Damage Inversion Analysis

The real c86 peak reaction identifies a unique aligned-skeleton amplitude at
`beta={manifest['locked_beta']:.6f}`. Peak reaction error is
`{manifest['inversion']['aligned']['relative_reaction_error']:.4%}` and the
maximum c86 postpeak error is
`{manifest['maximum_postpeak_reaction_relative_error']:.4%}`.

This removes most of the geometry-only energetic error. At c89, active log-MAE
falls from `{baseline_c89.derived_active_log_mae:.4f}` to
`{primary_c89.derived_active_log_mae:.4f}` decades, absolute-p99 IoU rises from
`{baseline_c89.absolute_p99_iou:.4f}` to `{primary_c89.absolute_p99_iou:.4f}`,
and support area falls from `{baseline_c89.absolute_support_area_ratio:.2f}x`
to `{primary_c89.absolute_support_area_ratio:.2f}x` FEM.

The locked mechanism gate nevertheless fails: c89 active correlation is only
`{primary_c89.derived_active_correlation:.4f}` and absolute-p99 IoU is
`{primary_c89.absolute_p99_iou:.4f}`. The shifted skeleton can also match the
same global reaction but gives c89 IoU `{shifted_c89.absolute_p99_iou:.4f}`.
Therefore reaction identifies global stiffness amplitude, while observed crack
geometry supplies location; the remaining mismatch requires a spatially
varying degradation/process-zone state rather than another scalar beta.
"""
    (args.out / "README_analysis.md").write_text(readme, encoding="utf-8")
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
