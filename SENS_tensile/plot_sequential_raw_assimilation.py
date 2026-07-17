#!/usr/bin/env python3
"""Plot FEM-centred evidence for c87-raw sequential assimilation."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
import meshio  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from analyze_damage_observation_equilibrium_gate import (  # noqa: E402
    add_field,
)
from train_fem_mechanism_mesh_operator import (  # noqa: E402
    area_weighted_quantile,
    derived_active_log10,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--reference-vtk", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def robust_limits(values: list[np.ndarray]) -> tuple[float, float]:
    joined = np.concatenate([np.asarray(value).reshape(-1) for value in values])
    return float(np.quantile(joined, 0.01)), float(np.quantile(joined, 0.995))


def support_code(model: np.ndarray, fem: np.ndarray, threshold: float) -> np.ndarray:
    fem_mask = fem >= threshold
    model_mask = model >= threshold
    return fem_mask.astype(np.uint8) + 2 * model_mask.astype(np.uint8)


def active_log(state: np.ndarray) -> np.ndarray:
    return derived_active_log10(torch.from_numpy(np.asarray(state))).numpy()


def plot_fields(
    polygons: np.ndarray,
    target_c87: np.ndarray,
    target_c89: np.ndarray,
    generated_c87: np.ndarray,
    analysis_c87: np.ndarray,
    upstream_c89: np.ndarray,
    sequential_c89: np.ndarray,
    out: Path,
) -> None:
    fem_raw = target_c87[:, 3]
    generated_raw = generated_c87[:, 3]
    observed_raw = analysis_c87[:, 3]
    fem_active = active_log(target_c89)
    upstream_active = active_log(upstream_c89)
    sequential_active = active_log(sequential_c89)
    raw_limits = robust_limits([fem_raw, generated_raw])
    active_limits = robust_limits([fem_active, upstream_active, sequential_active])
    raw_residual_limit = max(
        float(np.quantile(np.abs(generated_raw - fem_raw), 0.995)), 0.05
    )
    active_residual_limit = max(
        float(
            np.quantile(
                np.abs(
                    np.concatenate(
                        (upstream_active - fem_active, sequential_active - fem_active)
                    )
                ),
                0.995,
            )
        ),
        0.05,
    )

    fig, axes = plt.subplots(2, 4, figsize=(12.8, 5.6), constrained_layout=True)
    raw_fields = (
        ("FEM c87 raw observation", fem_raw, "viridis", *raw_limits),
        ("Generated c87 raw", generated_raw, "viridis", *raw_limits),
        ("Assimilated c87 raw", observed_raw, "viridis", *raw_limits),
        (
            "Generated - FEM",
            generated_raw - fem_raw,
            "coolwarm",
            -raw_residual_limit,
            raw_residual_limit,
        ),
    )
    active_fields = (
        ("FEM c89 active", fem_active, "viridis", *active_limits),
        ("Without c87 assimilation", upstream_active, "viridis", *active_limits),
        ("Sequential forecast", sequential_active, "viridis", *active_limits),
        (
            "Sequential - FEM",
            sequential_active - fem_active,
            "coolwarm",
            -active_residual_limit,
            active_residual_limit,
        ),
    )
    for row, fields in enumerate((raw_fields, active_fields)):
        collections = []
        for column, (title, values, cmap, vmin, vmax) in enumerate(fields):
            collections.append(
                add_field(
                    axes[row, column],
                    polygons,
                    values,
                    cmap=cmap,
                    vmin=vmin,
                    vmax=vmax,
                )
            )
            axes[row, column].set_title(title, fontsize=9)
        fig.colorbar(collections[0], ax=axes[row, :3], shrink=0.68, pad=0.01)
        fig.colorbar(collections[3], ax=axes[row, 3], shrink=0.68, pad=0.01)
    axes[0, 0].set_ylabel(r"c87 $\log_{10}\psi_{raw}$")
    axes[1, 0].set_ylabel(r"c89 $\log_{10}\psi_{active}$")
    fig.suptitle(
        "Sequential c87 raw-driver assimilation closes the c89 mechanism gap",
        fontsize=14,
    )
    for suffix in ("png", "pdf"):
        fig.savefig(out / f"sequential_mechanism_closure.{suffix}", dpi=240)
    plt.close(fig)


def plot_support(
    polygons: np.ndarray,
    target_c89: np.ndarray,
    upstream_c89: np.ndarray,
    sequential_c89: np.ndarray,
    areas: np.ndarray,
    out: Path,
) -> None:
    fem_active = active_log(target_c89)
    upstream_active = active_log(upstream_c89)
    sequential_active = active_log(sequential_c89)
    fem_threshold = area_weighted_quantile(fem_active, areas, 0.99)
    overlap_cmap = ListedColormap(("#e6e6e6", "#3b82c4", "#f28e2b", "#f1ce3e"))
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.5), constrained_layout=True)
    for ax, title, prediction in (
        (axes[0], "Without c87 assimilation", upstream_active),
        (axes[1], "Sequential c87 raw assimilation", sequential_active),
    ):
        add_field(
            ax,
            polygons,
            support_code(prediction, fem_active, fem_threshold),
            cmap=overlap_cmap,
            vmin=0.0,
            vmax=3.0,
        )
        ax.set_title(title, fontsize=10)
    fig.legend(
        handles=(
            Patch(color="#3b82c4", label="FEM only"),
            Patch(color="#f28e2b", label="model only"),
            Patch(color="#f1ce3e", label="overlap"),
        ),
        loc="lower center",
        ncol=3,
        frameon=False,
    )
    fig.suptitle("C89 active support at the fixed FEM area-weighted p99 threshold")
    for suffix in ("png", "pdf"):
        fig.savefig(out / f"sequential_active_support_overlap.{suffix}", dpi=240)
    plt.close(fig)


def plot_gate_table(metrics: pd.DataFrame, out: Path) -> None:
    columns = (
        ("derived_active_log_mae", "log-MAE", "<= 0.30"),
        ("derived_active_correlation", "correlation", ">= 0.90"),
        ("absolute_p99_iou", "FEM-p99 IoU", ">= 0.70"),
        ("absolute_support_area_ratio", "area ratio", "0.50-2.00"),
        ("own_p99_iou", "own-p99 IoU", "diagnostic"),
    )
    display = []
    method_labels = {
        "upstream_without_c87_raw_assimilation": "No c87 assimilation",
        "sequential_c87_raw_assimilation": "c87 raw assimilated",
    }
    for row in metrics.itertuples():
        values = [method_labels.get(row.method, row.method.replace("_", " "))]
        values.extend(f"{getattr(row, key):.3f}" for key, _, _ in columns)
        values.append("PASS" if bool(row.gate_pass) else "FAIL")
        display.append(values)
    labels = ["method", *[f"{label}\n{gate}" for _, label, gate in columns], "gate"]
    fig, ax = plt.subplots(figsize=(11.8, 2.25), constrained_layout=True)
    ax.axis("off")
    table = ax.table(cellText=display, colLabels=labels, cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(1.0, 1.75)
    for column in range(len(labels)):
        table[0, column].set_facecolor("#d9e8f5")
        table[0, column].set_text_props(weight="bold")
    for row in range(1, len(display) + 1):
        gate_cell = table[row, len(labels) - 1]
        color = "#d9ead3" if display[row - 1][-1] == "PASS" else "#f4cccc"
        gate_cell.set_facecolor(color)
        gate_cell.set_text_props(weight="bold")
    ax.set_title("Held-out c89 active-driver mechanism gate", fontsize=13, pad=8)
    for suffix in ("png", "pdf"):
        fig.savefig(out / f"sequential_gate_summary.{suffix}", dpi=240)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with np.load(args.dataset, allow_pickle=False) as dataset:
        target_c87 = np.asarray(dataset["states"][86], dtype=np.float64)
        target_c89 = np.asarray(dataset["states"][88], dtype=np.float64)
        areas = np.asarray(dataset["areas"], dtype=np.float64)
    mesh = meshio.read(args.reference_vtk)
    points = np.asarray(mesh.points, dtype=np.float64)[:, :2]
    connectivity = np.asarray(mesh.cells_dict["quad"], dtype=np.int32)
    polygons = points[connectivity]
    with np.load(args.predictions, allow_pickle=False) as predictions:
        generated_c87 = np.asarray(predictions["generated_c87"], dtype=np.float64)
        analysis_c87 = np.asarray(predictions["analysis_c87"], dtype=np.float64)
        upstream_c89 = np.asarray(predictions["upstream_c89"], dtype=np.float64)
        sequential_c89 = np.asarray(predictions["sequential_c89"], dtype=np.float64)
    metrics = pd.read_csv(args.metrics)
    plot_fields(
        polygons,
        target_c87,
        target_c89,
        generated_c87,
        analysis_c87,
        upstream_c89,
        sequential_c89,
        args.out,
    )
    plot_support(polygons, target_c89, upstream_c89, sequential_c89, areas, args.out)
    plot_gate_table(metrics, args.out)


if __name__ == "__main__":
    main()
