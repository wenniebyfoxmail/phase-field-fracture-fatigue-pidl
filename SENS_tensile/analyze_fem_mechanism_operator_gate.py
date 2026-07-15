#!/usr/bin/env python3
"""Build FEM-centred figures for the locked mechanism-operator gate.

The FEM archive stores cycle-peak raw tensile energy.  The active-like field in
this analysis is therefore derived consistently for FEM and every prediction as
``(1-damage)^2 * psi_raw`` with eta=0.  It is never labelled as an archived FEM
active field.
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
from matplotlib.collections import PolyCollection
from matplotlib.colors import ListedColormap


CYCLES = (20, 40, 76, 89)
MODELS = ("pointwise", "multiscale")
MODEL_LABELS = {
    "pointwise": "Pointwise residual MLP",
    "multiscale": "Multiscale mesh operator",
}
COMPARISON_LABELS = {
    20: "masked one-step audit",
    40: "masked one-step audit",
    76: "validation rollout c67->c76",
    89: "locked rollout c76->c89",
}
OVERLAP_CMAP = ListedColormap(["#d9d9d9", "#277da1", "#f8961e", "#f9c74f"])


def area_weighted_quantile(values: np.ndarray, areas: np.ndarray, quantile: float) -> float:
    order = np.argsort(values)
    cumulative = np.cumsum(areas[order])
    target = quantile * cumulative[-1]
    index = min(int(np.searchsorted(cumulative, target, side="left")), len(order) - 1)
    return float(values[order[index]])


def derived_fields(state: np.ndarray, floor: float) -> dict[str, np.ndarray]:
    damage = np.clip(state[:, 0], 0.0, 1.0)
    history_log = np.log10(np.maximum(state[:, 1], floor))
    raw_log = state[:, 3]
    g_log = 2.0 * np.log10(np.maximum(1.0 - damage, floor))
    active_log = np.maximum(raw_log + g_log, np.log10(floor))
    return {
        "damage": damage,
        "history_log": history_log,
        "raw_log": raw_log,
        "g_log": g_log,
        "active_log": active_log,
    }


def support_masks(
    target_active: np.ndarray,
    prediction_active: np.ndarray,
    areas: np.ndarray,
) -> dict[str, np.ndarray | float]:
    threshold = area_weighted_quantile(target_active, areas, 0.99)
    own_threshold = area_weighted_quantile(prediction_active, areas, 0.99)
    fem = target_active >= threshold
    absolute = prediction_active >= threshold
    own = prediction_active >= own_threshold

    def overlap(model: np.ndarray) -> np.ndarray:
        result = np.zeros(fem.shape, dtype=np.uint8)
        result[fem & ~model] = 1
        result[~fem & model] = 2
        result[fem & model] = 3
        return result

    intersection = float(areas[fem & absolute].sum())
    union = float(areas[fem | absolute].sum())
    own_intersection = float(areas[fem & own].sum())
    own_union = float(areas[fem | own].sum())
    fem_area = float(areas[fem].sum())
    return {
        "fem_threshold": threshold,
        "model_own_threshold": own_threshold,
        "absolute_overlap": overlap(absolute),
        "own_overlap": overlap(own),
        "absolute_iou": intersection / union,
        "own_iou": own_intersection / own_union,
        "absolute_area_ratio": float(areas[absolute].sum()) / fem_area,
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


def load_inputs(
    root: Path,
) -> tuple[dict[str, np.ndarray], dict[str, dict[int, np.ndarray]], np.ndarray]:
    data = np.load(root / "data" / "fem_cycle_peak_mechanism_graph.npz")
    base = {name: np.asarray(data[name]) for name in data.files}
    manifest = json.loads(
        (root / "data" / "fem_cycle_peak_mechanism_graph.manifest.json").read_text(
            encoding="utf-8"
        )
    )
    reference_vtk = Path(manifest["reference_vtk"])
    mesh = meshio.read(reference_vtk)
    polygons = np.asarray(mesh.points)[:, :2][np.asarray(base["connectivity"], dtype=np.int64)]
    predictions: dict[str, dict[int, np.ndarray]] = {}
    for model in MODELS:
        archive = np.load(root / "raw" / model / "locked_predictions.npz")
        predictions[model] = {cycle: np.asarray(archive[f"c{cycle}"]) for cycle in CYCLES}
    return base, predictions, polygons


def plot_active_fields(
    output: Path,
    polygons: np.ndarray,
    fem: dict[int, dict[str, np.ndarray]],
    predicted: dict[str, dict[int, dict[str, np.ndarray]]],
) -> None:
    all_values = [fem[cycle]["active_log"] for cycle in CYCLES]
    all_values.extend(predicted[model][cycle]["active_log"] for model in MODELS for cycle in CYCLES)
    vmax = max(float(np.nanpercentile(value, 99.995)) for value in all_values)
    vmin = -12.0
    figure, axes = plt.subplots(len(CYCLES), 3, figsize=(13.5, 8.4), constrained_layout=True)
    columns = ("FEM eta0 derived active", MODEL_LABELS["pointwise"], MODEL_LABELS["multiscale"])
    last = None
    for row, cycle in enumerate(CYCLES):
        fields = (fem[cycle], predicted["pointwise"][cycle], predicted["multiscale"][cycle])
        for column, field in enumerate(fields):
            last = add_field(
                axes[row, column], polygons, field["active_log"], cmap="magma", vmin=vmin, vmax=vmax
            )
            if row == 0:
                axes[row, column].set_title(columns[column], fontsize=10)
            if column == 0:
                axes[row, column].set_ylabel(f"c{cycle}\n{COMPARISON_LABELS[cycle]}", fontsize=9)
    assert last is not None
    figure.colorbar(last, ax=axes, label=r"$\log_{10}[(1-d)^2\psi_{raw}]$", shrink=0.75)
    figure.suptitle("FEM-centred derived active-driver fields (common scale)", fontsize=13)
    figure.savefig(output / "active_driver_fields.png", dpi=220)
    plt.close(figure)


def plot_support_overlap(
    output: Path,
    polygons: np.ndarray,
    areas: np.ndarray,
    fem: dict[int, dict[str, np.ndarray]],
    predicted: dict[str, dict[int, dict[str, np.ndarray]]],
) -> list[dict[str, float | int | str]]:
    figure, axes = plt.subplots(len(CYCLES), 4, figsize=(15.2, 8.5), constrained_layout=True)
    rows: list[dict[str, float | int | str]] = []
    columns = (
        "Pointwise: FEM-p99",
        "Pointwise: own-p99",
        "Multiscale: FEM-p99",
        "Multiscale: own-p99",
    )
    for row, cycle in enumerate(CYCLES):
        for model_index, model in enumerate(MODELS):
            metrics = support_masks(
                fem[cycle]["active_log"], predicted[model][cycle]["active_log"], areas
            )
            rows.append(
                {
                    "cycle": cycle,
                    "comparison": COMPARISON_LABELS[cycle],
                    "model": model,
                    "fem_log10_p99": metrics["fem_threshold"],
                    "model_log10_p99": metrics["model_own_threshold"],
                    "absolute_p99_iou": metrics["absolute_iou"],
                    "own_p99_iou": metrics["own_iou"],
                    "absolute_support_area_ratio": metrics["absolute_area_ratio"],
                }
            )
            for own_index, key in enumerate(("absolute_overlap", "own_overlap")):
                column = 2 * model_index + own_index
                add_field(
                    axes[row, column],
                    polygons,
                    np.asarray(metrics[key]),
                    cmap=OVERLAP_CMAP,
                    vmin=0,
                    vmax=3,
                )
                if row == 0:
                    axes[row, column].set_title(columns[column], fontsize=10)
                if own_index == 0:
                    axes[row, column].text(
                        0.01,
                        0.01,
                        f"IoU={float(metrics['absolute_iou']):.3f}\nR={float(metrics['absolute_area_ratio']):.2f}",
                        transform=axes[row, column].transAxes,
                        fontsize=7.5,
                        va="bottom",
                        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none"},
                    )
                else:
                    axes[row, column].text(
                        0.01,
                        0.01,
                        f"IoU={float(metrics['own_iou']):.3f}",
                        transform=axes[row, column].transAxes,
                        fontsize=7.5,
                        va="bottom",
                        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none"},
                    )
        axes[row, 0].set_ylabel(f"c{cycle}\n{COMPARISON_LABELS[cycle]}", fontsize=9)
    figure.suptitle(
        "Derived active-support overlap: grey neither, blue FEM-only, orange model-only, yellow overlap",
        fontsize=12,
    )
    figure.savefig(output / "active_support_overlap.png", dpi=220)
    plt.close(figure)
    return rows


def plot_c89_residuals(
    output: Path,
    polygons: np.ndarray,
    fem: dict[int, dict[str, np.ndarray]],
    predicted: dict[str, dict[int, dict[str, np.ndarray]]],
) -> None:
    field_specs = (
        ("damage", "damage", "viridis", 0.0, 1.0),
        ("history_log", "log10 history", "viridis", None, None),
        ("raw_log", "log10 raw driver", "magma", None, None),
        ("active_log", "log10 derived active", "magma", -12.0, None),
    )
    for model in MODELS:
        figure, axes = plt.subplots(4, 3, figsize=(12.5, 10.0), constrained_layout=True)
        for row, (key, label, cmap, lower, upper) in enumerate(field_specs):
            target = fem[89][key]
            estimate = predicted[model][89][key]
            residual = estimate - target
            vmin = float(np.nanpercentile(np.concatenate([target, estimate]), 0.2)) if lower is None else lower
            vmax = float(np.nanpercentile(np.concatenate([target, estimate]), 99.8)) if upper is None else upper
            magnitude = max(abs(float(np.nanpercentile(residual, 0.2))), abs(float(np.nanpercentile(residual, 99.8))))
            add_field(axes[row, 0], polygons, target, cmap=cmap, vmin=vmin, vmax=vmax)
            add_field(axes[row, 1], polygons, estimate, cmap=cmap, vmin=vmin, vmax=vmax)
            residual_collection = add_field(
                axes[row, 2], polygons, residual, cmap="coolwarm", vmin=-magnitude, vmax=magnitude
            )
            axes[row, 0].set_ylabel(label)
            figure.colorbar(residual_collection, ax=axes[row, 2], shrink=0.72)
        for column, title in enumerate(("FEM c89", f"{MODEL_LABELS[model]} c89", "prediction - FEM")):
            axes[0, column].set_title(title, fontsize=10)
        figure.suptitle(
            f"Locked c76->c89 FEM residual decomposition: {MODEL_LABELS[model]}", fontsize=13
        )
        figure.savefig(output / f"fem_residual_decomposition_{model}_c89.png", dpi=220)
        plt.close(figure)


def read_metric_rows(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for model in MODELS:
        with (root / "raw" / model / "fem_centred_metrics.csv").open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                row["model"] = model
                rows.append(row)
    return rows


def plot_metric_trajectory(output: Path, rows: list[dict[str, str]]) -> None:
    metrics = (
        ("derived_active_log_mae", "Active log-MAE", None),
        ("derived_active_correlation", "Active correlation", None),
        ("absolute_p99_iou", "Absolute FEM-p99 IoU", (0.0, 1.0)),
        ("absolute_support_area_ratio", "Absolute support area ratio", (0.0, 5.0)),
    )
    figure, axes = plt.subplots(2, 2, figsize=(10.8, 7.2), constrained_layout=True)
    locked_names = {"validation_rollout_from_c67", "locked_rollout_from_c76"}
    for ax, (metric, label, limits) in zip(axes.flat, metrics):
        for model, color in zip(MODELS, ("#3a86ff", "#e76f51")):
            selected = [row for row in rows if row["model"] == model and row["comparison"] in locked_names]
            selected.sort(key=lambda row: int(row["cycle"]))
            ax.plot(
                [int(row["cycle"]) for row in selected],
                [float(row[metric]) for row in selected],
                "o-",
                color=color,
                label=MODEL_LABELS[model],
            )
        ax.axvline(76, color="#555555", linestyle="--", linewidth=1.0)
        ax.set_xlabel("Physical cycle")
        ax.set_ylabel(label)
        if limits is not None:
            ax.set_ylim(*limits)
        ax.grid(alpha=0.25)
        if metric == "absolute_support_area_ratio":
            for model, color, x_offset in zip(MODELS, ("#3a86ff", "#e76f51"), (-0.2, 0.2)):
                c89 = next(
                    row
                    for row in rows
                    if row["model"] == model
                    and row["comparison"] == "locked_rollout_from_c76"
                    and int(row["cycle"]) == 89
                )
                ax.text(
                    89 + x_offset,
                    4.88,
                    f"{float(c89[metric]):.1f}x",
                    color=color,
                    ha="center",
                    va="top",
                    fontsize=8,
                    fontweight="bold",
                )
    axes[0, 0].legend(frameon=False, fontsize=8)
    axes[1, 1].text(
        0.98,
        0.95,
        "Values above 5 are clipped\nfor readability",
        transform=axes[1, 1].transAxes,
        ha="right",
        va="top",
        fontsize=8,
    )
    figure.suptitle("FEM-centred rollout trajectory; dashed line starts the locked c76->c89 test")
    figure.savefig(output / "same_cycle_metric_trajectory.png", dpi=220)
    plt.close(figure)


def write_event_map(output: Path) -> None:
    lines = [
        "# Operator Gate State Map",
        "",
        "FEM eta=0 cycle-peak fields are the physical reference in every row.",
        "The active-like field is derived as `(1-damage)^2 * psi_raw`; it is not an archived FEM active field.",
        "",
        "| Cycle | Comparison class | Pointwise state | Multiscale state |",
        "|---:|---|---|---|",
    ]
    for cycle in CYCLES:
        lines.append(
            f"| c{cycle} | {COMPARISON_LABELS[cycle]} | cycle-peak prediction | cycle-peak prediction |"
        )
    lines.extend(
        [
            "",
            "The operator has no independent penetration event; an own-event comparison is therefore not applicable.",
            "c89 is a locked rollout from the observed FEM c76 state, not a teacher-forced c89 reconstruction.",
        ]
    )
    (output / "event_state_map.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = (args.output or root / "analysis").resolve()
    output.mkdir(parents=True, exist_ok=True)

    data, predictions, polygons = load_inputs(root)
    floor = float(np.asarray(data["log_floor"]).item())
    areas = np.asarray(data["areas"], dtype=np.float64)
    states = np.asarray(data["states"])
    fem = {cycle: derived_fields(states[cycle - 1], floor) for cycle in CYCLES}
    predicted = {
        model: {cycle: derived_fields(predictions[model][cycle], floor) for cycle in CYCLES}
        for model in MODELS
    }

    write_event_map(output)
    plot_active_fields(output, polygons, fem, predicted)
    support_rows = plot_support_overlap(output, polygons, areas, fem, predicted)
    plot_c89_residuals(output, polygons, fem, predicted)
    metric_rows = read_metric_rows(root)
    plot_metric_trajectory(output, metric_rows)

    with (output / "active_support_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(support_rows[0]))
        writer.writeheader()
        writer.writerows(support_rows)
    summary = {
        "fem_reference": "eta0 cycle-peak",
        "derived_active": "eta0 diagnostic: (1-damage)^2 * psi_raw",
        "cycles": list(CYCLES),
        "models": list(MODELS),
        "own_event_applicable": False,
        "support_metrics": support_rows,
    }
    (output / "analysis_manifest.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
