#!/usr/bin/env python3
"""Render magnitude-honest and shape-only diagnostics for S09-E011 fields."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import matplotlib.tri as mtri
import numpy as np


METHODS = (
    ("target_peak", "FEM reference"),
    ("control_peak", "B25 continuation"),
    ("ranking_peak", "B25 + ranking"),
)
SELECTED_CYCLES = (1, 58, 69, 70, 73)
ARM_LOGS = (
    ("C25_pair_batched_B25_continuation", "B25 continuation", "#0072B2"),
    ("R25_pairwise_ranking_beta0p25", "B25 + ranking", "#D55E00"),
)


def _increments(data: np.lib.npyio.NpzFile) -> dict[str, np.ndarray]:
    return {key: np.asarray(data[key]) - np.asarray(data["d_pre"])
            for key, _ in METHODS}


def _save_selected_log(
    *, tri: mtri.Triangulation, cycles: np.ndarray,
    increments: dict[str, np.ndarray], output: Path,
) -> None:
    indices = [int(np.flatnonzero(cycles == cycle)[0]) for cycle in SELECTED_CYCLES]
    positive = np.concatenate([
        increments[key][indices].reshape(-1) for key, _ in METHODS
    ])
    positive = positive[positive > 0]
    vmax = float(positive.max())
    vmin = 1e-6
    norm = LogNorm(vmin=vmin, vmax=vmax)
    fig, axes = plt.subplots(
        len(indices), len(METHODS), figsize=(10.2, 13.2),
        constrained_layout=True,
    )
    image = None
    for row, (index, cycle) in enumerate(zip(indices, SELECTED_CYCLES)):
        for column, (key, label) in enumerate(METHODS):
            values = np.ma.masked_less_equal(increments[key][index], 0)
            axis = axes[row, column]
            image = axis.tripcolor(
                tri, values, shading="gouraud", cmap="magma", norm=norm,
                rasterized=True,
            )
            axis.set_title(f"cycle {cycle}: {label}", fontsize=9)
            axis.set_aspect("equal")
            axis.set_xticks([])
            axis.set_yticks([])
    fig.colorbar(
        image, ax=axes.ravel().tolist(), shrink=.56,
        label=f"positive Δd, shared log scale [{vmin:.0e}, {vmax:.2g}]",
    )
    fig.suptitle(
        "S09-E011 selected damage increments: shared logarithmic magnitude scale",
        fontsize=13,
    )
    fig.savefig(output, dpi=180, facecolor="white")
    plt.close(fig)


def _save_selected_shape(
    *, tri: mtri.Triangulation, cycles: np.ndarray,
    increments: dict[str, np.ndarray], output: Path,
) -> None:
    indices = [int(np.flatnonzero(cycles == cycle)[0]) for cycle in SELECTED_CYCLES]
    fig, axes = plt.subplots(
        len(indices), len(METHODS), figsize=(10.2, 13.2),
        constrained_layout=True,
    )
    image = None
    for row, (index, cycle) in enumerate(zip(indices, SELECTED_CYCLES)):
        for column, (key, label) in enumerate(METHODS):
            raw = increments[key][index]
            scale = float(np.max(np.abs(raw)))
            values = np.zeros_like(raw) if scale == 0 else raw / scale
            axis = axes[row, column]
            image = axis.tripcolor(
                tri, values, shading="gouraud", cmap="viridis",
                vmin=0, vmax=1, rasterized=True,
            )
            axis.set_title(
                f"cycle {cycle}: {label}\nmax Δd={scale:.3e}", fontsize=8.5)
            axis.set_aspect("equal")
            axis.set_xticks([])
            axis.set_yticks([])
    fig.colorbar(
        image, ax=axes.ravel().tolist(), shrink=.56,
        label="Δd / panel maximum (shape only; magnitude removed)",
    )
    fig.suptitle(
        "S09-E011 selected damage-increment shapes: per-panel normalization",
        fontsize=13,
    )
    fig.savefig(output, dpi=180, facecolor="white")
    plt.close(fig)


def _save_final_cycle(
    *, tri: mtri.Triangulation, cycles: np.ndarray, data: np.lib.npyio.NpzFile,
    increments: dict[str, np.ndarray], output: Path,
) -> None:
    cycle = 73
    index = int(np.flatnonzero(cycles == cycle)[0])
    vmax_increment = max(float(increments[key][index].max()) for key, _ in METHODS)
    fig, axes = plt.subplots(2, 3, figsize=(11, 7.4), constrained_layout=True)
    top = bottom = None
    for column, (key, label) in enumerate(METHODS):
        top = axes[0, column].tripcolor(
            tri, np.asarray(data[key])[index], shading="gouraud", cmap="viridis",
            vmin=0, vmax=1, rasterized=True,
        )
        axes[0, column].set_title(f"{label}: total d_peak", fontsize=9)
        values = np.ma.masked_less_equal(increments[key][index], 0)
        bottom = axes[1, column].tripcolor(
            tri, values, shading="gouraud", cmap="magma",
            norm=LogNorm(vmin=1e-6, vmax=vmax_increment), rasterized=True,
        )
        axes[1, column].set_title(
            f"{label}: Δd\nmax={float(increments[key][index].max()):.3e}",
            fontsize=9,
        )
        for row in (0, 1):
            axes[row, column].set_aspect("equal")
            axes[row, column].set_xticks([])
            axes[row, column].set_yticks([])
    fig.colorbar(top, ax=axes[0, :].tolist(), shrink=.8, label="total d_peak [0, 1]")
    fig.colorbar(
        bottom, ax=axes[1, :].tolist(), shrink=.8,
        label="positive Δd, shared log scale",
    )
    fig.suptitle(
        "S09-E011 cycle 73: total field can hide increment error", fontsize=13)
    fig.savefig(output, dpi=180, facecolor="white")
    plt.close(fig)


def _write_summary(
    *, data: np.lib.npyio.NpzFile, cycles: np.ndarray,
    increments: dict[str, np.ndarray], output: Path,
) -> None:
    weights = np.asarray(data["nodal_weight"]).reshape(-1)
    with output.open("w", newline="", encoding="utf-8") as stream:
        fields = [
            "cycle", "method", "weighted_mean_abs_increment", "max_increment",
            "positive_node_fraction_gt_1e-6",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for index, cycle in enumerate(cycles):
            for key, label in METHODS:
                values = increments[key][index]
                writer.writerow({
                    "cycle": int(cycle),
                    "method": label,
                    "weighted_mean_abs_increment": float(
                        np.dot(np.abs(values), weights) / weights.sum()),
                    "max_increment": float(values.max()),
                    "positive_node_fraction_gt_1e-6": float(
                        np.mean(values > 1e-6)),
                })


def _save_metric_trajectories(*, run_dir: Path, output: Path) -> None:
    records = {}
    for arm, label, color in ARM_LOGS:
        rows = []
        for line in (run_dir / arm / "diagnostic_metrics.jsonl").read_text(
            encoding="utf-8"
        ).splitlines():
            aggregate = json.loads(line)["aggregate"]
            auc = aggregate["amplitude_auc"]
            rows.append({
                "update": aggregate["update"],
                "pair_score": 2 * auc["wins"] + auc["ties"],
                "G": aggregate["G"],
                "F": aggregate["F"],
                "L_P": aggregate["L_P"],
                "L_judge": aggregate["L_judge"],
                "spatial": aggregate["spatial"]["primary_median"],
            })
        records[arm] = (label, color, rows)

    panels = (
        ("pair_score", "pair score = 2W + T", False),
        ("G", "growth-cycle field-increment MAE, G", True),
        ("F", "near-stagnant false growth, F", True),
        ("L_P", "mechanical-equilibrium cost, L_P", True),
        ("L_judge", "fixed judgement loss", False),
        ("spatial", "median spatial correlation", False),
    )
    fig, axes = plt.subplots(2, 3, figsize=(12.4, 7.2), constrained_layout=True)
    for axis, (metric, ylabel, log_scale) in zip(axes.ravel(), panels):
        for _, (label, color, rows) in records.items():
            axis.plot(
                [row["update"] for row in rows],
                [row[metric] for row in rows],
                "o-", color=color, linewidth=1.6, markersize=4, label=label,
            )
        if log_scale:
            axis.set_yscale("log")
        axis.set_xlabel("continuation update")
        axis.set_ylabel(ylabel)
        axis.grid(alpha=.25)
    axes[0, 0].legend(frameon=False)
    fig.suptitle("S09-E011 exposed-development metric trajectories", fontsize=13)
    fig.savefig(output, dpi=180, facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with np.load(args.input) as data:
        cycles = np.asarray(data["cycles"])
        if not set(SELECTED_CYCLES).issubset(set(map(int, cycles))):
            raise ValueError("selected cycles absent from field archive")
        xy = np.asarray(data["xy"])
        tri = mtri.Triangulation(xy[:, 0], xy[:, 1])
        increments = _increments(data)
        _save_selected_log(
            tri=tri, cycles=cycles, increments=increments,
            output=args.output_dir / "selected_delta_d_log_shared.png",
        )
        _save_selected_shape(
            tri=tri, cycles=cycles, increments=increments,
            output=args.output_dir / "selected_delta_d_shape_only.png",
        )
        _save_final_cycle(
            tri=tri, cycles=cycles, data=data, increments=increments,
            output=args.output_dir / "cycle73_total_and_increment.png",
        )
        _write_summary(
            data=data, cycles=cycles, increments=increments,
            output=args.output_dir / "field_diagnostic_summary.csv",
        )
    _save_metric_trajectories(
        run_dir=args.input.parent,
        output=args.output_dir / "metric_trajectories.png",
    )


if __name__ == "__main__":
    main()
