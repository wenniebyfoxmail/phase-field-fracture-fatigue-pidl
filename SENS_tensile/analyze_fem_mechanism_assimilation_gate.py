#!/usr/bin/env python3
"""Build FEM-centred evidence for the mechanism-assimilation gate.

The FEM archive stores cycle-peak raw tensile energy.  The active-like field is
derived consistently for FEM and every forecast as ``(1-damage)^2 * psi_raw``
with eta=0.  Assimilation at c87 is post-detection reconstruction: FEM first
reaches the right boundary at c86, while c87 is the first post-event mechanics
regime represented in the archived cycle-peak fields.
"""

from __future__ import annotations

import argparse
import csv
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


MODELS = ("pointwise", "multiscale")
MODEL_LABELS = {
    "pointwise": "Pointwise residual MLP",
    "multiscale": "Multiscale mesh operator",
}
SCENARIO_LABELS = {
    "none": "No observation",
    "damage_visible": "Visible damage",
    "raw_fixed_probes": "192 fixed raw probes",
    "damage_visible_raw_fixed_probes": "Damage + fixed probes",
    "damage_visible_raw_fixed_probes_permuted": "Permuted control",
    "raw_full": "Full raw-driver oracle",
    "history_fatigue_full": "History/fatigue oracle",
    "damage_raw_full": "Damage + raw oracle",
    "full_state_oracle": "Full-state oracle",
}
RESTART_CYCLES = (67, 76, 80, 84, 86, 87, 88)
OVERLAP_CMAP = ListedColormap(["#d9d9d9", "#277da1", "#f8961e", "#f9c74f"])


def derived_fields(state: np.ndarray, floor: float) -> dict[str, np.ndarray]:
    damage = np.clip(state[:, 0], 0.0, 1.0)
    raw_log = state[:, 3]
    g_log = 2.0 * np.log10(np.maximum(1.0 - damage, floor))
    return {
        "damage": damage,
        "history_log": np.log10(np.maximum(state[:, 1], floor)),
        "raw_log": raw_log,
        "g_log": g_log,
        "active_log": np.maximum(raw_log + g_log, np.log10(floor)),
    }


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


def overlap_mask(target: np.ndarray, estimate: np.ndarray, areas: np.ndarray) -> tuple[np.ndarray, float, float]:
    order = np.argsort(target)
    cumulative = np.cumsum(areas[order])
    index = min(int(np.searchsorted(cumulative, 0.99 * cumulative[-1])), len(order) - 1)
    threshold = float(target[order[index]])
    fem = target >= threshold
    model = estimate >= threshold
    overlap = np.zeros(fem.shape, dtype=np.uint8)
    overlap[fem & ~model] = 1
    overlap[~fem & model] = 2
    overlap[fem & model] = 3
    union = float(areas[fem | model].sum())
    iou = float(areas[fem & model].sum()) / union
    ratio = float(areas[model].sum()) / float(areas[fem].sum())
    return overlap, iou, ratio


def load_geometry(operator_root: Path) -> tuple[dict[str, np.ndarray], np.ndarray]:
    data_path = operator_root / "data" / "fem_cycle_peak_mechanism_graph.npz"
    data = np.load(data_path, allow_pickle=True)
    base = {name: np.asarray(data[name]) for name in data.files}
    manifest = json.loads(
        (operator_root / "data" / "fem_cycle_peak_mechanism_graph.manifest.json").read_text(
            encoding="utf-8"
        )
    )
    mesh = meshio.read(Path(manifest["reference_vtk"]))
    polygons = np.asarray(mesh.points)[:, :2][np.asarray(base["connectivity"], dtype=np.int64)]
    return base, polygons


def load_metrics(root: Path, raw_folder: str) -> pd.DataFrame:
    frames = []
    for model in MODELS:
        frame = pd.read_csv(root / raw_folder / model / "assimilation_metrics.csv")
        frame["model"] = model
        frame["assimilation_set"] = raw_folder
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def load_predictions(root: Path, raw_folder: str) -> dict[str, dict[str, np.ndarray]]:
    result: dict[str, dict[str, np.ndarray]] = {}
    for model in MODELS:
        archive = np.load(root / raw_folder / model / "assimilation_predictions.npz")
        result[model] = {name: np.asarray(archive[name]) for name in archive.files if name != "state_names"}
    return result


def write_c87_table(output: Path, c87_metrics: pd.DataFrame) -> pd.DataFrame:
    table = c87_metrics[(c87_metrics["cycle"] == 89) & (c87_metrics["phase"] == "forecast_prior")].copy()
    keep = [
        "model",
        "scenario",
        "damage_mae",
        "alpha_bar_mae",
        "log10_psi_raw_mae",
        "derived_active_log_mae",
        "derived_active_correlation",
        "absolute_p99_iou",
        "absolute_support_area_ratio",
        "own_p99_iou",
    ]
    table = table[keep]
    table.to_csv(output / "c87_channel_ablation_c89_metrics.csv", index=False)
    return table


def plot_restart_horizon(output: Path, metrics: pd.DataFrame) -> None:
    restart = metrics[
        (metrics["cycle"] == 89)
        & (metrics["phase"] == "forecast")
        & metrics["scenario"].str.startswith("true_c")
    ].copy()
    restart["restart_cycle"] = restart["scenario"].str.extract(r"true_c(\d+)").astype(int)
    specs = (
        ("derived_active_log_mae", "Active log-MAE", None),
        ("derived_active_correlation", "Active correlation", (-0.5, 1.05)),
        ("absolute_p99_iou", "Absolute p99 IoU", (-0.02, 1.02)),
        ("absolute_support_area_ratio", "Support-area ratio", (0.0, 105.0)),
    )
    figure, axes = plt.subplots(2, 2, figsize=(11.5, 7.2), constrained_layout=True)
    for ax, (metric, label, ylim) in zip(axes.ravel(), specs):
        for model in MODELS:
            rows = restart[restart["model"] == model].sort_values("restart_cycle")
            ax.plot(rows["restart_cycle"], rows[metric], marker="o", label=MODEL_LABELS[model])
        ax.axvline(86, color="#d62828", linestyle="--", linewidth=1.4, label="FEM first detection c86")
        ax.axvspan(86.5, 87.5, color="#fcbf49", alpha=0.2)
        ax.set_xlabel("True FEM restart cycle supplied to frozen operator")
        ax.set_ylabel(label)
        ax.grid(alpha=0.25)
        if ylim is not None:
            ax.set_ylim(*ylim)
    axes[0, 0].legend(fontsize=8, loc="best")
    figure.suptitle("c89 forecastability changes across the c86->c87 mechanics transition", fontsize=13)
    figure.savefig(output / "restart_horizon_c89.png", dpi=220)
    plt.close(figure)


def plot_assimilation_cycle_gate(output: Path, early: pd.DataFrame, c87: pd.DataFrame) -> None:
    rows = []
    for cycle_label, frame in (("c80+c84", early), ("c87", c87)):
        subset = frame[
            (frame["model"] == "multiscale")
            & (frame["cycle"] == 89)
            & (frame["phase"] == "forecast_prior")
            & frame["scenario"].isin(("none", "raw_full", "damage_raw_full", "full_state_oracle"))
        ]
        for _, row in subset.iterrows():
            rows.append({"observation_cycle": cycle_label, **row.to_dict()})
    frame = pd.DataFrame(rows)
    specs = (
        ("derived_active_log_mae", "Active log-MAE"),
        ("derived_active_correlation", "Active correlation"),
        ("absolute_p99_iou", "Absolute p99 IoU"),
        ("absolute_support_area_ratio", "Support-area ratio"),
    )
    figure, axes = plt.subplots(2, 2, figsize=(12, 7.6), constrained_layout=True)
    x = np.arange(4)
    width = 0.36
    scenarios = ("none", "raw_full", "damage_raw_full", "full_state_oracle")
    for ax, (metric, label) in zip(axes.ravel(), specs):
        for offset, cycle_label in ((-width / 2, "c80+c84"), (width / 2, "c87")):
            values = []
            for scenario in scenarios:
                selected = frame[
                    (frame["observation_cycle"] == cycle_label) & (frame["scenario"] == scenario)
                ]
                values.append(float(selected.iloc[0][metric]))
            ax.bar(x + offset, values, width, label=cycle_label)
        ax.set_xticks(x, [SCENARIO_LABELS[name] for name in scenarios], rotation=18, ha="right")
        ax.set_ylabel(label)
        ax.grid(axis="y", alpha=0.25)
    axes[0, 0].legend(title="Assimilation schedule", fontsize=8)
    figure.suptitle("Early assimilation fails; post-detection c87 raw mechanics closes c89", fontsize=13)
    figure.savefig(output / "assimilation_timing_gate_c89.png", dpi=220)
    plt.close(figure)


def plot_c87_support(
    output: Path,
    polygons: np.ndarray,
    areas: np.ndarray,
    target: dict[str, np.ndarray],
    predictions: dict[str, dict[str, np.ndarray]],
    floor: float,
) -> None:
    scenarios = ("none", "damage_visible", "raw_fixed_probes", "raw_full", "damage_raw_full")
    figure, axes = plt.subplots(2, len(scenarios), figsize=(16, 5.5), constrained_layout=True)
    for row, model in enumerate(MODELS):
        for column, scenario in enumerate(scenarios):
            estimate = derived_fields(predictions[model][f"{scenario}_c89"], floor)["active_log"]
            overlap, iou, ratio = overlap_mask(target["active_log"], estimate, areas)
            add_field(axes[row, column], polygons, overlap, cmap=OVERLAP_CMAP, vmin=0, vmax=3)
            if row == 0:
                axes[row, column].set_title(SCENARIO_LABELS[scenario], fontsize=9)
            if column == 0:
                axes[row, column].set_ylabel(MODEL_LABELS[model], fontsize=9)
            axes[row, column].text(
                0.01,
                0.01,
                f"IoU={iou:.3f}\nR={ratio:.2f}",
                transform=axes[row, column].transAxes,
                fontsize=7.5,
                bbox={"facecolor": "white", "alpha": 0.82, "edgecolor": "none"},
            )
    figure.suptitle(
        "c89 active support after c87 assimilation (grey neither, blue FEM, orange model, yellow overlap)",
        fontsize=12,
    )
    figure.savefig(output / "c87_active_support_overlap.png", dpi=220)
    plt.close(figure)


def plot_raw_g_active(
    output: Path,
    polygons: np.ndarray,
    target: dict[str, np.ndarray],
    predictions: dict[str, dict[str, np.ndarray]],
    floor: float,
) -> None:
    model = "multiscale"
    scenarios = ("none", "raw_full", "damage_raw_full")
    columns = [("FEM c89", target)]
    columns.extend(
        (SCENARIO_LABELS[scenario], derived_fields(predictions[model][f"{scenario}_c89"], floor))
        for scenario in scenarios
    )
    specs = (
        ("raw_log", r"$\log_{10}\psi_{raw}$", "magma"),
        ("g_log", r"$\log_{10}g(d)$", "viridis"),
        ("active_log", r"$\log_{10}[g(d)\psi_{raw}]$", "magma"),
    )
    figure, axes = plt.subplots(3, 4, figsize=(13.5, 7.7), constrained_layout=True)
    for row, (key, label, cmap) in enumerate(specs):
        values = [field[key] for _, field in columns]
        vmin = float(np.nanpercentile(np.concatenate(values), 0.2))
        vmax = float(np.nanpercentile(np.concatenate(values), 99.8))
        for column, (title, field) in enumerate(columns):
            collection = add_field(
                axes[row, column], polygons, field[key], cmap=cmap, vmin=vmin, vmax=vmax
            )
            if row == 0:
                axes[row, column].set_title(title, fontsize=9)
            if column == 0:
                axes[row, column].set_ylabel(label, fontsize=9)
        figure.colorbar(collection, ax=axes[row, :], shrink=0.66)
    figure.suptitle("Multiscale c87 assimilation: raw -> degradation -> derived active at c89", fontsize=13)
    figure.savefig(output / "c87_raw_g_active_decomposition.png", dpi=220)
    plt.close(figure)


def write_manifest(output: Path, root: Path, operator_root: Path) -> None:
    manifest = {
        "analysis": "FEM-centred mechanism-assimilation gate",
        "fem_reference": "eta0 cycle-peak fields",
        "derived_active": "eta0 diagnostic: (1-damage)^2 * archived FEM raw tensile energy",
        "state_semantics": {
            "c86": "FEM first right-boundary detection / penetration state",
            "c87": "first archived post-detection mechanics regime",
            "c89": "confirmed terminal/export state and locked forecast target",
        },
        "primary_caveat": "c87 assimilation is post-detection reconstruction, not prediction of c86 first hit",
        "support_threshold": "native full-domain area-weighted p99; not the established projected clean-domain headline threshold",
        "source_root": str(root),
        "operator_root": str(operator_root),
    }
    (output / "analysis_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--operator-root", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    operator_root = args.operator_root.resolve()
    output = root / "analysis"
    output.mkdir(parents=True, exist_ok=True)

    base, polygons = load_geometry(operator_root)
    cycles = np.asarray(base["cycles"], dtype=int)
    target_state = np.asarray(base["states"])[int(np.where(cycles == 89)[0][0])]
    floor = float(np.asarray(base["log_floor"]).item())
    target = derived_fields(target_state, floor)
    areas = np.asarray(base["areas"], dtype=float)

    early = load_metrics(root, "raw")
    c87 = load_metrics(root, "raw_c87")
    all_metrics = pd.concat([early, c87], ignore_index=True)
    all_metrics.to_csv(output / "all_assimilation_metrics.csv", index=False)
    write_c87_table(output, c87)

    predictions = load_predictions(root, "raw_c87")
    plot_restart_horizon(output, c87)
    plot_assimilation_cycle_gate(output, early, c87)
    plot_c87_support(output, polygons, areas, target, predictions, floor)
    plot_raw_g_active(output, polygons, target, predictions, floor)
    write_manifest(output, root, operator_root)


if __name__ == "__main__":
    main()
