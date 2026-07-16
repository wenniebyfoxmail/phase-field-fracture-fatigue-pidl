#!/usr/bin/env python3
"""Build FEM-centred figures for the visible-crack equilibrium gate."""

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
from matplotlib.collections import PolyCollection
from matplotlib.colors import ListedColormap


FLOOR = 1.0e-12
OVERLAP_CMAP = ListedColormap(["#d9d9d9", "#277da1", "#f8961e", "#f9c74f"])
PRIMARY = "core95_skeleton_at1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--vtk", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def derived(state: np.ndarray) -> dict[str, np.ndarray]:
    damage = np.clip(state[:, 0], 0.0, 1.0)
    history_log = np.log10(np.maximum(state[:, 1], FLOOR))
    raw_log = state[:, 3]
    g_log = 2.0 * np.log10(np.maximum(1.0 - damage, FLOOR))
    active_log = np.maximum(raw_log + g_log, np.log10(FLOOR))
    return {
        "damage": damage,
        "history_log": history_log,
        "raw_log": raw_log,
        "g_log": g_log,
        "active_log": active_log,
    }


def area_weighted_quantile(values: np.ndarray, areas: np.ndarray, quantile: float) -> float:
    order = np.argsort(values)
    cumulative = np.cumsum(areas[order])
    index = min(int(np.searchsorted(cumulative, quantile * cumulative[-1])), len(order) - 1)
    return float(values[order[index]])


def support_metrics(
    target: np.ndarray,
    estimate: np.ndarray,
    areas: np.ndarray,
) -> tuple[np.ndarray, float, float, float]:
    threshold = area_weighted_quantile(target, areas, 0.99)
    fem = target >= threshold
    model = estimate >= threshold
    codes = np.zeros(len(target), dtype=np.uint8)
    codes[fem & ~model] = 1
    codes[~fem & model] = 2
    codes[fem & model] = 3
    intersection = float(areas[fem & model].sum())
    union = float(areas[fem | model].sum())
    target_area = float(areas[fem].sum())
    iou = intersection / union if union else float("nan")
    ratio = float(areas[model].sum()) / target_area if target_area else float("nan")
    return codes, iou, ratio, threshold


def add_field(
    ax: plt.Axes,
    polygons: np.ndarray,
    values: np.ndarray,
    *,
    cmap: str | ListedColormap,
    vmin: float,
    vmax: float,
) -> PolyCollection:
    collection = PolyCollection(
        polygons,
        array=np.asarray(values),
        cmap=cmap,
        edgecolors="none",
        linewidths=0.0,
        rasterized=True,
    )
    collection.set_clim(vmin, vmax)
    ax.add_collection(collection)
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    return collection


def robust_limits(arrays: list[np.ndarray], low: float = 0.01, high: float = 0.995) -> tuple[float, float]:
    joined = np.concatenate([np.asarray(array).reshape(-1) for array in arrays])
    return float(np.quantile(joined, low)), float(np.quantile(joined, high))


def symmetric_limit(arrays: list[np.ndarray], quantile: float = 0.995) -> float:
    joined = np.concatenate([np.abs(np.asarray(array).reshape(-1)) for array in arrays])
    return max(float(np.quantile(joined, quantile)), 1.0e-12)


def element_average(nodal: np.ndarray, connectivity: np.ndarray) -> np.ndarray:
    return np.asarray(nodal)[connectivity].mean(axis=1)


def plot_c86_damage(
    polygons: np.ndarray,
    connectivity: np.ndarray,
    true_nodal_damage: np.ndarray,
    phase_a: dict[str, np.ndarray],
    names: list[str],
    out: Path,
) -> None:
    true_element = element_average(true_nodal_damage, connectivity)
    fields = [true_element] + [element_average(phase_a[f"damage_{name}"], connectivity) for name in names]
    titles = ["FEM c86 damage"] + names
    fig, axes = plt.subplots(2, len(fields), figsize=(3.0 * len(fields), 5.2), constrained_layout=True)
    for column, (title, field) in enumerate(zip(titles, fields)):
        first = add_field(axes[0, column], polygons, field, cmap="viridis", vmin=0.0, vmax=1.0)
        residual = field - true_element
        second = add_field(axes[1, column], polygons, residual, cmap="coolwarm", vmin=-0.25, vmax=0.25)
        axes[0, column].set_title(title.replace("_", "\n"), fontsize=9)
        if column == 0:
            axes[0, column].set_ylabel("damage")
            axes[1, column].set_ylabel("candidate - FEM")
    fig.colorbar(first, ax=axes[0, :], shrink=0.65, pad=0.01)
    fig.colorbar(second, ax=axes[1, :], shrink=0.65, pad=0.01)
    fig.suptitle("c86 binary-observation damage reconstructions", fontsize=15)
    fig.savefig(out / "c86_damage_reconstruction_and_residual.png", dpi=220)
    plt.close(fig)


def plot_mechanism_decomposition(
    polygons: np.ndarray,
    target: np.ndarray,
    candidates: dict[str, np.ndarray],
    cycle: int,
    out: Path,
) -> None:
    target_fields = derived(target)
    candidate_fields = {name: derived(state) for name, state in candidates.items()}
    rows = (
        ("raw_log", r"$\log_{10}\psi_{raw}$"),
        ("g_log", r"$\log_{10}g(d)$"),
        ("active_log", r"$\log_{10}\psi_{active}$"),
    )
    columns = [(f"FEM c{cycle}", target_fields), *candidate_fields.items()]
    fig, axes = plt.subplots(3, len(columns), figsize=(3.0 * len(columns), 7.5), constrained_layout=True)
    for row, (key, label) in enumerate(rows):
        arrays = [fields[key] for _, fields in columns]
        vmin, vmax = robust_limits(arrays)
        for column, (name, fields) in enumerate(columns):
            collection = add_field(
                axes[row, column], polygons, fields[key], cmap="viridis", vmin=vmin, vmax=vmax
            )
            if row == 0:
                axes[row, column].set_title(name.replace("_", "\n"), fontsize=9)
        axes[row, 0].set_ylabel(label)
        fig.colorbar(collection, ax=axes[row, :], shrink=0.65, pad=0.01)
    fig.suptitle(f"FEM-centred raw -> degradation -> active decomposition at c{cycle}", fontsize=15)
    fig.savefig(out / f"c{cycle}_raw_g_active_decomposition.png", dpi=220)
    plt.close(fig)


def plot_support_matrix(
    polygons: np.ndarray,
    target: np.ndarray,
    candidates: dict[str, np.ndarray],
    areas: np.ndarray,
    cycle: int,
    out: Path,
) -> None:
    target_fields = derived(target)
    rows = (("raw_log", "raw p99"), ("active_log", "active p99"))
    fig, axes = plt.subplots(2, len(candidates), figsize=(3.0 * len(candidates), 5.0), constrained_layout=True)
    for row, (field, label) in enumerate(rows):
        for column, (name, state) in enumerate(candidates.items()):
            codes, iou, ratio, _ = support_metrics(
                target_fields[field], derived(state)[field], areas
            )
            add_field(axes[row, column], polygons, codes, cmap=OVERLAP_CMAP, vmin=0, vmax=3)
            axes[row, column].set_title(
                f"{name.replace('_', ' ')}\nIoU={iou:.3f} | area={ratio:.2f}x",
                fontsize=8,
            )
        axes[row, 0].set_ylabel(label)
    fig.suptitle(
        f"c{cycle} FEM absolute-p99 support overlap: blue FEM-only, orange model-only, yellow overlap",
        fontsize=14,
    )
    fig.savefig(out / f"c{cycle}_absolute_support_overlap.png", dpi=220)
    plt.close(fig)


def plot_c89_residuals(
    polygons: np.ndarray,
    target: np.ndarray,
    candidates: dict[str, np.ndarray],
    out: Path,
) -> None:
    target_fields = derived(target)
    candidate_fields = {name: derived(state) for name, state in candidates.items()}
    rows = (
        ("damage", "damage residual"),
        ("history_log", "history log residual"),
        ("raw_log", "raw log residual"),
        ("active_log", "active log residual"),
    )
    fig, axes = plt.subplots(4, len(candidates), figsize=(3.0 * len(candidates), 9.0), constrained_layout=True)
    for row, (field, label) in enumerate(rows):
        residuals = [fields[field] - target_fields[field] for fields in candidate_fields.values()]
        limit = symmetric_limit(residuals)
        for column, ((name, _), residual) in enumerate(zip(candidate_fields.items(), residuals)):
            collection = add_field(
                axes[row, column], polygons, residual, cmap="coolwarm", vmin=-limit, vmax=limit
            )
            if row == 0:
                axes[row, column].set_title(name.replace("_", "\n"), fontsize=9)
        axes[row, 0].set_ylabel(label)
        fig.colorbar(collection, ax=axes[row, :], shrink=0.65, pad=0.01)
    fig.suptitle("c89 frozen-operator residuals relative to FEM", fontsize=15)
    fig.savefig(out / "c89_field_residuals.png", dpi=220)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    dataset = np.load(args.dataset, allow_pickle=False)
    states = np.asarray(dataset["states"])
    areas = np.asarray(dataset["areas"], dtype=np.float64)
    mesh = meshio.read(args.vtk)
    points = np.asarray(mesh.points)[:, :2]
    connectivity = np.asarray(mesh.cells_dict["quad"], dtype=np.int32)
    polygons = points[connectivity]
    true_nodal_damage = np.asarray(mesh.point_data["d"]).reshape(-1)
    with np.load(args.raw / "phase_a_damage_observation_equilibria.npz", allow_pickle=False) as archive:
        phase_a = {name: np.asarray(archive[name]).copy() for name in archive.files}
    with np.load(args.raw / "damage_observation_predictions.npz", allow_pickle=False) as archive:
        predictions = {name: np.asarray(archive[name]).copy() for name in archive.files}

    damage_names = [
        "binary_core95",
        "core95_mask_at1",
        PRIMARY,
        "core95_straight_at1",
        "core95_skeleton_shifted",
        "initial_precrack_at1",
    ]
    plot_c86_damage(
        polygons, connectivity, true_nodal_damage, phase_a, damage_names, args.out
    )

    display_names = {
        "full_damage_oracle": "full damage oracle",
        PRIMARY: "skeleton AT1 primary",
        "core95_straight_at1": "straight extent AT1",
        "core95_skeleton_shifted": "shifted skeleton",
        "initial_precrack_at1": "initial precrack",
        "untouched_c86_rollout": "untouched c86 rollout",
    }
    c87_candidates = {
        display_names[name]: predictions[f"{name}_c87"]
        for name in (
            "full_damage_oracle",
            PRIMARY,
            "core95_straight_at1",
            "core95_skeleton_shifted",
            "initial_precrack_at1",
            "untouched_c86_rollout",
        )
    }
    c89_candidates = {
        display_names[name]: predictions[f"{name}_c89"]
        for name in (
            "full_damage_oracle",
            PRIMARY,
            "core95_straight_at1",
            "core95_skeleton_shifted",
            "initial_precrack_at1",
            "untouched_c86_rollout",
        )
    }
    plot_mechanism_decomposition(polygons, states[86], c87_candidates, 87, args.out)
    plot_support_matrix(polygons, states[86], c87_candidates, areas, 87, args.out)
    plot_mechanism_decomposition(polygons, states[88], c89_candidates, 89, args.out)
    plot_support_matrix(polygons, states[88], c89_candidates, areas, 89, args.out)
    plot_c89_residuals(polygons, states[88], c89_candidates, args.out)

    metrics = pd.read_csv(args.raw / "damage_observation_metrics.csv")
    raw_support_rows: list[dict[str, float | int | str]] = []
    for cycle, candidates in ((87, c87_candidates), (89, c89_candidates)):
        target = states[cycle - 1]
        for label, prediction in candidates.items():
            _, raw_iou, raw_ratio, raw_threshold = support_metrics(
                derived(target)["raw_log"], derived(prediction)["raw_log"], areas
            )
            _, active_iou, active_ratio, active_threshold = support_metrics(
                derived(target)["active_log"], derived(prediction)["active_log"], areas
            )
            raw_support_rows.append(
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
    support = pd.DataFrame(raw_support_rows)
    support.to_csv(args.out / "raw_and_active_support_metrics.csv", index=False)
    metrics.to_csv(args.out / "gate_summary.csv", index=False)

    manifest = json.loads((args.raw / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
    numerical_rows = []
    for name, record in manifest["numerical"].items():
        numerical_rows.append({"candidate": name, **record})
    pd.DataFrame(numerical_rows).to_csv(args.out / "candidate_numerical_status.csv", index=False)

    primary_c87 = metrics[(metrics.method == PRIMARY) & (metrics.cycle == 87)].iloc[0]
    primary_c89 = metrics[(metrics.method == PRIMARY) & (metrics.cycle == 89)].iloc[0]
    oracle_c87 = metrics[(metrics.method == "full_damage_oracle") & (metrics.cycle == 87)].iloc[0]
    oracle_c89 = metrics[(metrics.method == "full_damage_oracle") & (metrics.cycle == 89)].iloc[0]
    primary_c87_support = support[
        (support.method_label == display_names[PRIMARY]) & (support.cycle == 87)
    ].iloc[0]
    c87_pass = bool(
        primary_c87.log10_psi_raw_mae <= 0.30
        and primary_c87.log10_psi_raw_correlation >= 0.90
        and primary_c87_support.raw_absolute_p99_iou >= 0.70
        and 0.5 <= primary_c87_support.raw_support_area_ratio <= 2.0
    )
    c89_pass = bool(
        primary_c89.derived_active_log_mae <= 0.30
        and primary_c89.derived_active_correlation >= 0.90
        and primary_c89.absolute_p99_iou >= 0.70
        and 0.5 <= primary_c89.absolute_support_area_ratio <= 2.0
    )
    oracle_reproduced = bool(
        oracle_c87.log10_psi_raw_mae <= 0.001
        and oracle_c89.derived_active_log_mae <= 0.03
        and oracle_c89.absolute_p99_iou >= 0.90
    )
    decision = {
        "primary_candidate": PRIMARY,
        "primary_c87_raw_gate_pass": c87_pass,
        "primary_c89_active_gate_pass": c89_pass,
        "primary_full_gate_pass": bool(c87_pass and c89_pass),
        "full_damage_oracle_reproduced": oracle_reproduced,
        "primary_c87": {
            "raw_log_mae": float(primary_c87.log10_psi_raw_mae),
            "raw_correlation": float(primary_c87.log10_psi_raw_correlation),
            "raw_absolute_p99_iou": float(primary_c87_support.raw_absolute_p99_iou),
            "raw_support_area_ratio": float(primary_c87_support.raw_support_area_ratio),
            "active_log_mae": float(primary_c87.derived_active_log_mae),
            "active_correlation": float(primary_c87.derived_active_correlation),
        },
        "primary_c89": {
            "active_log_mae": float(primary_c89.derived_active_log_mae),
            "active_correlation": float(primary_c89.derived_active_correlation),
            "absolute_p99_iou": float(primary_c89.absolute_p99_iou),
            "support_area_ratio": float(primary_c89.absolute_support_area_ratio),
        },
        "oracle_c87_raw_log_mae": float(oracle_c87.log10_psi_raw_mae),
        "oracle_c89_active_log_mae": float(oracle_c89.derived_active_log_mae),
        "failed_equilibrium_candidates": manifest["failed_equilibrium_candidates"],
    }
    (args.out / "analysis_manifest.json").write_text(
        json.dumps(decision, indent=2) + "\n", encoding="utf-8"
    )
    readme = f"""# FEM-Centred Visible-Crack Analysis

The fixed-resolution skeleton reconstructs c86 damage well in ordinary field
metrics, but it does not recover the equilibrium mechanics. At c87 its raw
driver log-MAE is `{primary_c87.log10_psi_raw_mae:.4f}` decades, correlation is
`{primary_c87.log10_psi_raw_correlation:.4f}`, raw absolute-p99 IoU is
`{primary_c87_support.raw_absolute_p99_iou:.4f}`, and raw support area is
`{primary_c87_support.raw_support_area_ratio:.2f}x` FEM. The c87 gate fails.

After the frozen operator reaches c89, active log-MAE is
`{primary_c89.derived_active_log_mae:.4f}`, correlation is
`{primary_c89.derived_active_correlation:.4f}`, absolute-p99 IoU is
`{primary_c89.absolute_p99_iou:.4f}`, and support area is
`{primary_c89.absolute_support_area_ratio:.2f}x` FEM. The c89 gate also fails.

The full diffuse c86 damage ceiling reproduces the previous conditional
closure: c87 raw log-MAE `{oracle_c87.log10_psi_raw_mae:.6f}` and c89 active
log-MAE `{oracle_c89.derived_active_log_mae:.6f}`. Therefore the failure is not
the equilibrium implementation or frozen operator. Binary crack location plus
a nominal AT1 profile is insufficient: near-saturated diffuse damage amplitudes
control residual stiffness and topology-conditioned stress redistribution.
"""
    (args.out / "README_analysis.md").write_text(readme, encoding="utf-8")
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
