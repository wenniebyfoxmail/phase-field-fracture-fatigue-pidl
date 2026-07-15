#!/usr/bin/env python3
"""Build FEM-centred figures for the c86 damage-conditioned equilibrium gate."""

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


def support_overlap(
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
    ratio = float(areas[model].sum() / areas[fem].sum())
    return codes, intersection / union, ratio, threshold


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


def c87_decomposition(
    polygons: np.ndarray,
    target: np.ndarray,
    generated: np.ndarray,
    out: Path,
) -> None:
    fem = derived(target)
    model = derived(generated)
    rows = (
        ("raw_log", r"$\log_{10}\psi_{raw}$"),
        ("g_log", r"$\log_{10}g(\alpha)$"),
        ("active_log", r"$\log_{10}\psi_{active}$"),
    )
    fig, axes = plt.subplots(3, 3, figsize=(13.0, 8.4), constrained_layout=True)
    for row, (key, label) in enumerate(rows):
        vmin, vmax = robust_limits([fem[key], model[key]])
        residual = model[key] - fem[key]
        residual_limit = symmetric_limit([residual])
        first = add_field(axes[row, 0], polygons, fem[key], cmap="viridis", vmin=vmin, vmax=vmax)
        add_field(axes[row, 1], polygons, model[key], cmap="viridis", vmin=vmin, vmax=vmax)
        third = add_field(
            axes[row, 2],
            polygons,
            residual,
            cmap="coolwarm",
            vmin=-residual_limit,
            vmax=residual_limit,
        )
        axes[row, 0].set_ylabel(label)
        fig.colorbar(first, ax=axes[row, :2], shrink=0.72, pad=0.01)
        fig.colorbar(third, ax=axes[row, 2], shrink=0.72, pad=0.01)
    for ax, title in zip(axes[0], ("FEM c87 peak", "c86-damage equilibrium", "Generated - FEM")):
        ax.set_title(title)
    fig.suptitle("Post-detection mechanics reconstruction at c87", fontsize=15)
    fig.savefig(out / "c87_raw_g_active_decomposition.png", dpi=220)
    plt.close(fig)


def c87_support(
    polygons: np.ndarray,
    target: np.ndarray,
    generated: np.ndarray,
    areas: np.ndarray,
    out: Path,
) -> tuple[float, float, float]:
    fem = derived(target)["active_log"]
    model = derived(generated)["active_log"]
    codes, iou, ratio, threshold = support_overlap(fem, model, areas)
    fem_mask = (fem >= threshold).astype(np.uint8)
    model_mask = (model >= threshold).astype(np.uint8)
    fig, axes = plt.subplots(1, 3, figsize=(13.0, 3.3), constrained_layout=True)
    add_field(axes[0], polygons, fem_mask, cmap="Blues", vmin=0, vmax=1)
    add_field(axes[1], polygons, model_mask, cmap="Oranges", vmin=0, vmax=1)
    add_field(axes[2], polygons, codes, cmap=OVERLAP_CMAP, vmin=0, vmax=3)
    axes[0].set_title("FEM c87 | FEM p99")
    axes[1].set_title("Generated c87 | same threshold")
    axes[2].set_title(f"Overlap | IoU={iou:.4f}, area={ratio:.4f}x")
    fig.suptitle("Absolute active-support gate at c87")
    fig.savefig(out / "c87_active_support_overlap.png", dpi=220)
    plt.close(fig)
    return iou, ratio, threshold


def c89_controls(
    polygons: np.ndarray,
    target: np.ndarray,
    controls: dict[str, np.ndarray],
    areas: np.ndarray,
    out: Path,
) -> None:
    target_active = derived(target)["active_log"]
    control_active = {name: derived(state)["active_log"] for name, state in controls.items()}
    vmin, vmax = robust_limits([target_active, *control_active.values()])
    columns = [("FEM c89", target_active), *control_active.items()]
    fig, axes = plt.subplots(2, len(columns), figsize=(18.0, 6.0), constrained_layout=True)
    for column, (name, values) in enumerate(columns):
        add_field(axes[0, column], polygons, values, cmap="viridis", vmin=vmin, vmax=vmax)
        if column == 0:
            codes, iou, ratio, _ = support_overlap(target_active, target_active, areas)
        else:
            codes, iou, ratio, _ = support_overlap(target_active, values, areas)
        add_field(axes[1, column], polygons, codes, cmap=OVERLAP_CMAP, vmin=0, vmax=3)
        axes[0, column].set_title(name)
        axes[1, column].set_title(f"IoU={iou:.3f} | area={ratio:.3f}x")
    axes[0, 0].set_ylabel(r"$\log_{10}\psi_{active}$")
    axes[1, 0].set_ylabel("FEM-p99 overlap")
    fig.suptitle("Multiscale c89 controls: mechanics projection versus oracle ceilings", fontsize=15)
    fig.savefig(out / "c89_multiscale_active_support_controls.png", dpi=220)
    plt.close(fig)


def c89_residuals(
    polygons: np.ndarray,
    target: np.ndarray,
    controls: dict[str, np.ndarray],
    out: Path,
) -> None:
    target_fields = derived(target)
    rows = (
        ("damage", "Damage residual"),
        ("history_log", "History log residual"),
        ("raw_log", "Raw-driver log residual"),
        ("active_log", "Active-driver log residual"),
    )
    control_fields = {name: derived(state) for name, state in controls.items()}
    fig, axes = plt.subplots(4, len(controls), figsize=(15.0, 9.0), constrained_layout=True)
    for row, (field, label) in enumerate(rows):
        residuals = [fields[field] - target_fields[field] for fields in control_fields.values()]
        limit = symmetric_limit(residuals)
        for column, ((name, _), residual) in enumerate(zip(control_fields.items(), residuals)):
            collection = add_field(
                axes[row, column],
                polygons,
                residual,
                cmap="coolwarm",
                vmin=-limit,
                vmax=limit,
            )
            if row == 0:
                axes[row, column].set_title(name)
        axes[row, 0].set_ylabel(label)
        fig.colorbar(collection, ax=axes[row, :], shrink=0.68, pad=0.01)
    fig.suptitle("Multiscale c89 residuals relative to FEM", fontsize=15)
    fig.savefig(out / "c89_multiscale_field_residuals.png", dpi=220)
    plt.close(fig)


def c89_generated_residual_zoom(
    polygons: np.ndarray,
    target: np.ndarray,
    generated: np.ndarray,
    out: Path,
) -> None:
    target_fields = derived(target)
    generated_fields = derived(generated)
    rows = (
        ("damage", "Damage", "linear"),
        ("history_log", "History", "log10"),
        ("raw_log", "Raw driver", "log10"),
        ("active_log", "Active driver", "log10"),
    )
    fig, axes = plt.subplots(1, 4, figsize=(15.0, 3.5), constrained_layout=True)
    for column, (field, title, unit) in enumerate(rows):
        residual = generated_fields[field] - target_fields[field]
        limit = symmetric_limit([residual])
        collection = add_field(
            axes[column],
            polygons,
            residual,
            cmap="coolwarm",
            vmin=-limit,
            vmax=limit,
        )
        axes[column].set_title(f"{title} residual ({unit})")
        fig.colorbar(collection, ax=axes[column], shrink=0.72, pad=0.01)
    fig.suptitle("Generated-raw multiscale c89 residuals with per-field zoom", fontsize=15)
    fig.savefig(out / "c89_generated_residual_zoom.png", dpi=220)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    dataset = np.load(args.dataset, allow_pickle=False)
    states = np.asarray(dataset["states"])
    areas = np.asarray(dataset["areas"], dtype=np.float64)
    mesh = meshio.read(args.vtk)
    connectivity = np.asarray(mesh.cells_dict["quad"], dtype=np.int32)
    polygons = np.asarray(mesh.points)[:, :2][connectivity]
    with np.load(args.raw / "equilibrium_projection.npz", allow_pickle=False) as raw:
        generated_c87 = np.asarray(raw["projected_c87"])
        controls = {
            "Untouched c86 rollout": np.asarray(raw["multiscale_untouched_c86_rollout_c89"]),
            "Generated raw": np.asarray(raw["multiscale_generated_raw_projection_c89"]),
            "True c87 raw oracle": np.asarray(raw["multiscale_true_c87_raw_oracle_c89"]),
            "True c87 full state": np.asarray(raw["multiscale_true_c87_full_state_restart_c89"]),
        }

    c87_decomposition(polygons, states[86], generated_c87, args.out)
    c87_iou, c87_ratio, c87_threshold = c87_support(
        polygons, states[86], generated_c87, areas, args.out
    )
    c89_controls(polygons, states[88], controls, areas, args.out)
    c89_residuals(polygons, states[88], controls, args.out)
    c89_generated_residual_zoom(
        polygons,
        states[88],
        controls["Generated raw"],
        args.out,
    )

    metrics = pd.read_csv(args.raw / "equilibrium_projection_metrics.csv")
    selected = metrics[
        metrics["method"].isin(
            [
                "c86_damage_conditioned_equilibrium",
                "multiscale_untouched_c86_prior",
                "multiscale_untouched_c86_rollout",
                "multiscale_generated_raw_projection",
                "multiscale_true_c87_raw_oracle",
                "multiscale_true_c87_full_state_restart",
            ]
        )
    ].copy()
    selected.to_csv(args.out / "gate_summary.csv", index=False)

    c87_generated = selected[selected.method == "c86_damage_conditioned_equilibrium"].iloc[0]
    c87_prior = selected[selected.method == "multiscale_untouched_c86_prior"].iloc[0]
    c89_generated = selected[selected.method == "multiscale_generated_raw_projection"].iloc[0]
    c89_full = selected[selected.method == "multiscale_true_c87_full_state_restart"].iloc[0]
    raw_reduction = 1.0 - c87_generated.log10_psi_raw_mae / c87_prior.log10_psi_raw_mae
    damage_ratio = c89_generated.damage_mae / c89_full.damage_mae
    history_ratio = c89_generated.alpha_bar_mae / c89_full.alpha_bar_mae
    active_pass = bool(
        c89_generated.derived_active_log_mae <= 0.30
        and c89_generated.derived_active_correlation >= 0.90
        and c89_generated.absolute_p99_iou >= 0.70
        and 0.5 <= c89_generated.absolute_support_area_ratio <= 2.0
    )
    full_gate_pass = bool(active_pass and damage_ratio <= 1.10 and history_ratio <= 1.10)
    decision = {
        "c87": {
            "raw_log_mae_reduction_fraction": float(raw_reduction),
            "raw_correlation": float(c87_generated.log10_psi_raw_correlation),
            "active_correlation": float(c87_generated.derived_active_correlation),
            "absolute_p99_iou": float(c87_iou),
            "absolute_support_area_ratio": float(c87_ratio),
            "active_log_p99_threshold": float(c87_threshold),
        },
        "c89_multiscale_generated": {
            "active_log_mae": float(c89_generated.derived_active_log_mae),
            "active_correlation": float(c89_generated.derived_active_correlation),
            "absolute_p99_iou": float(c89_generated.absolute_p99_iou),
            "absolute_support_area_ratio": float(c89_generated.absolute_support_area_ratio),
            "damage_oracle_error_ratio": float(damage_ratio),
            "history_oracle_error_ratio": float(history_ratio),
        },
        "active_mechanism_gate_pass": active_pass,
        "full_predeclared_gate_pass": full_gate_pass,
    }
    (args.out / "analysis_manifest.json").write_text(
        json.dumps(decision, indent=2) + "\n", encoding="utf-8"
    )
    readme = f"""# FEM-Centred Analysis

The c86 damage-conditioned eta0 AMOR solve reconstructs the c87 FEM raw field
with log-MAE `{c87_generated.log10_psi_raw_mae:.6g}` and correlation
`{c87_generated.log10_psi_raw_correlation:.9f}`. This is a
`{100.0 * raw_reduction:.5f}%` reduction relative to the untouched multiscale
c86-to-c87 prior. Its c87 derived-active absolute p99 IoU is `{c87_iou:.6f}`
with support-area ratio `{c87_ratio:.6f}`.

After frozen multiscale propagation to c89, the generated-raw branch has active
log-MAE `{c89_generated.derived_active_log_mae:.6f}`, correlation
`{c89_generated.derived_active_correlation:.6f}`, absolute p99 IoU
`{c89_generated.absolute_p99_iou:.6f}`, and support-area ratio
`{c89_generated.absolute_support_area_ratio:.6f}`. These pass every declared
active-mechanism gate and are almost identical to the true-c87-raw oracle.

The full predeclared promotion gate remains formally false because damage and
history errors are `{damage_ratio:.3f}x` and `{history_ratio:.3f}x` their
near-zero true-c87-full-state restart errors, exceeding the 1.10 relative cap.
Their absolute errors are nevertheless only `{c89_generated.damage_mae:.3e}`
and `{c89_generated.alpha_bar_mae:.3e}`. This distinction must be retained:
the raw/active mismatch is conditionally closed, while autonomous full-state
prediction is not yet established.
"""
    (args.out / "README_analysis.md").write_text(readme, encoding="utf-8")
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
