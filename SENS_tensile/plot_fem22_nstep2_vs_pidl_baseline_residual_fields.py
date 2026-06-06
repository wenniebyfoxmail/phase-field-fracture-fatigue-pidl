#!/usr/bin/env python3
"""Residual field montages for FEM22 nstep2 c1-c5 vs strict PIDL baseline."""
from __future__ import annotations

from pathlib import Path
import sys

import h5py
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import CenteredNorm, LogNorm
import numpy as np
import pandas as pd
from scipy.io import loadmat
from scipy.spatial import cKDTree


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROJECT_ROOT = ROOT.parent
sys.path.insert(0, str(HERE))

from posthoc_mesh_probe_alignment import mesh_from_settings, pidl_model_and_mesh  # noqa: E402


PIDL_ARCHIVE = (
    HERE
    / "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
    "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
    "N100_R0.0_Umax0.12_femmesh_softHist0"
)
FEM_FIELDS = (
    PROJECT_ROOT
    / "Alignment check"
    / "FEM preparation"
    / "nstep2"
    / "fem22_nstep2_c0_c5_whole_fields.mat"
)
FEM_MESH = PROJECT_ROOT / "Alignment check" / "FEM preparation" / "nstep2" / "mesh_geometry.mat"
OUT = ROOT / "_analysis_fem_mechanism_20260528" / "residual_fields_fem22_nstep2_vs_pidl_baseline_20260603"


FIELDS = [
    ("alpha", "damage alpha / d", "linear"),
    ("psi_raw", "psi_raw", "log"),
    ("damage_degradation", "damage degradation g(alpha)", "linear01"),
    ("psi_active", "psi_active = g(alpha) psi_raw", "log"),
    ("alpha_bar", "alpha_bar", "linear"),
    ("f_fatigue", "fatigue degradation f", "linear01"),
]


def load_fem_mesh() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    m = loadmat(FEM_MESH)
    nodes = np.asarray(m["node_coords"], dtype=float)
    conn = np.asarray(m["connectivity"], dtype=int)
    if conn.min() == 1:
        conn = conn - 1
    if nodes[:, 0].min() >= -1e-12 and nodes[:, 0].max() > 0.75:
        nodes = nodes.copy()
        nodes[:, 0] -= 0.5
    if nodes[:, 1].min() >= -1e-12 and nodes[:, 1].max() > 0.75:
        nodes = nodes.copy()
        nodes[:, 1] -= 0.5
    pts = nodes[conn]
    x = pts[:, :, 0]
    y = pts[:, :, 1]
    areas = 0.5 * np.abs(np.sum(x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1), axis=1))
    return nodes, conn, areas


def load_fem_peak_post_history_states() -> dict[int, dict[str, np.ndarray]]:
    """Return FEM cycle c1-c5 peak post-history-refresh states.

    The whole-field handoff stores c0 plus duplicate pre/post states at peak
    and unload for each cycle. For PIDL one-peak saved states, use the second
    peak row: c1/c2/c3/c4/c5 -> indices 2/6/10/14/18.
    """
    idx_by_cycle = {1: 2, 2: 6, 3: 10, 4: 14, 5: 18}
    out: dict[int, dict[str, np.ndarray]] = {}
    with h5py.File(FEM_FIELDS, "r") as h5:
        for cycle, idx in idx_by_cycle.items():
            alpha = np.asarray(h5["fields/d_elem"][idx], dtype=float)
            psi_raw = np.asarray(h5["fields/psi_raw_elem"][idx], dtype=float)
            damage_degradation = np.asarray(h5["fields/damage_degradation_elem"][idx], dtype=float)
            psi_active = np.asarray(h5["fields/active_psi_positive_elem"][idx], dtype=float)
            alpha_bar = np.asarray(h5["fields/alpha_bar_elem"][idx], dtype=float)
            f_fatigue = np.asarray(h5["fields/f_fatigue_elem"][idx], dtype=float)
            out[cycle] = {
                "alpha": alpha,
                "psi_raw": psi_raw,
                "damage_degradation": damage_degradation,
                "psi_active": psi_active,
                "alpha_bar": alpha_bar,
                "f_fatigue": f_fatigue,
            }
    return out


def project_pidl_to_fem(pidl: dict[str, np.ndarray], fem_centroids: np.ndarray) -> dict[str, np.ndarray]:
    tree = cKDTree(pidl["centroids"])
    _, idx = tree.query(fem_centroids, k=1)
    return {
        "alpha": pidl["alpha"][idx],
        "psi_raw": pidl["psi_plus_raw"][idx],
        "damage_degradation": ((1.0 - pidl["alpha"][idx]) ** 2),
        "psi_active": pidl["psi_plus_active"][idx],
        "alpha_bar": pidl["alpha_bar"][idx],
        "f_fatigue": pidl["f"][idx],
    }


def reductions(values: np.ndarray, areas: np.ndarray) -> dict[str, float]:
    finite = np.isfinite(values)
    x = values[finite]
    w = areas[finite]
    return {
        "min": float(np.nanmin(x)),
        "max": float(np.nanmax(x)),
        "mean": float(np.nanmean(x)),
        "area_mean": float(np.sum(x * w) / np.sum(w)),
        "p95": float(np.nanpercentile(x, 95)),
        "p99": float(np.nanpercentile(x, 99)),
        "p999": float(np.nanpercentile(x, 99.9)),
    }


def add_metric_rows(rows: list[dict[str, object]], cycle: int, field: str, source: str, values: np.ndarray, areas: np.ndarray) -> None:
    for metric, value in reductions(values, areas).items():
        rows.append({"cycle": cycle, "field": field, "source": source, "metric": metric, "value": value})


def panel_values(field: str, fem: np.ndarray, pidl: np.ndarray, mode: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, object, object]:
    eps = 1e-12
    if mode == "log":
        fem_plot = np.maximum(fem, eps)
        pidl_plot = np.maximum(pidl, eps)
        both = np.concatenate([fem_plot[np.isfinite(fem_plot)], pidl_plot[np.isfinite(pidl_plot)]])
        positive = both[both > 0]
        vmin = max(np.nanpercentile(positive, 1), eps) if positive.size else eps
        vmax = max(np.nanpercentile(positive, 99.5), vmin * 10.0) if positive.size else 1.0
        residual = np.log10((fem_plot + eps) / (pidl_plot + eps))
        norm = LogNorm(vmin=vmin, vmax=vmax)
        rnorm = CenteredNorm(vcenter=0.0, halfrange=max(1e-6, np.nanpercentile(np.abs(residual), 99)))
        return fem_plot, pidl_plot, residual, norm, rnorm

    residual = fem - pidl
    if mode == "linear01":
        norm = plt.Normalize(vmin=0.0, vmax=1.0)
    else:
        both = np.concatenate([fem[np.isfinite(fem)], pidl[np.isfinite(pidl)]])
        vmin = float(np.nanpercentile(both, 1)) if both.size else 0.0
        vmax = float(np.nanpercentile(both, 99.5)) if both.size else 1.0
        if abs(vmax - vmin) < 1e-12:
            vmax = vmin + 1.0
        norm = plt.Normalize(vmin=vmin, vmax=vmax)
    rnorm = CenteredNorm(vcenter=0.0, halfrange=max(1e-12, np.nanpercentile(np.abs(residual), 99)))
    return fem, pidl, residual, norm, rnorm


def plot_cycle(
    cycle: int,
    fem_fields: dict[str, np.ndarray],
    pidl_fields: dict[str, np.ndarray],
    nodes: np.ndarray,
    conn: np.ndarray,
    view: str,
) -> Path:
    polys = nodes[conn]
    fig, axes = plt.subplots(len(FIELDS), 3, figsize=(9.8, 14.5), constrained_layout=True)
    if view == "full":
        xlim = (-0.52, 0.52)
        ylim = (-0.52, 0.52)
        view_label = "full-domain"
    else:
        xlim = (-0.08, 0.08)
        ylim = (-0.08, 0.08)
        view_label = "near-tip"
    for row, (field, label, mode) in enumerate(FIELDS):
        fem, pidl, residual, norm, rnorm = panel_values(field, fem_fields[field], pidl_fields[field], mode)
        panels = [
            (fem, "FEM reference", "viridis", norm),
            (pidl, "PIDL baseline", "viridis", norm),
            (residual, "Residual: FEM - PIDL" if mode != "log" else "Residual: log10(FEM/PIDL)", "RdBu_r", rnorm),
        ]
        for col, (vals, title, cmap, this_norm) in enumerate(panels):
            ax = axes[row, col]
            pc = PolyCollection(polys, array=vals, cmap=cmap, norm=this_norm, linewidths=0.0, rasterized=True)
            ax.add_collection(pc)
            ax.set_xlim(*xlim)
            ax.set_ylim(*ylim)
            ax.set_aspect("equal", adjustable="box")
            ax.axhline(0, color="white", lw=0.4, alpha=0.8)
            ax.axvline(0, color="white", lw=0.4, alpha=0.8)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title(f"{label}\n{title}", fontsize=8)
            cb = fig.colorbar(pc, ax=ax, fraction=0.046, pad=0.01)
            cb.ax.tick_params(labelsize=6)
    fig.suptitle(
        f"FEM22 nstep2 peak post-history c{cycle} vs PIDL strict baseline j{cycle - 1} {view_label} residual fields",
        fontsize=11,
    )
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"fem22_nstep2_c{cycle:02d}_vs_pidl_j{cycle-1:02d}_all_variable_residuals_{view}.png"
    fig.savefig(path, dpi=240)
    plt.close(fig)
    return path


def main() -> None:
    nodes, conn, areas = load_fem_mesh()
    centroids = nodes[conn].mean(axis=1)
    fem_by_cycle = load_fem_peak_post_history_states()
    pidl_mesh = mesh_from_settings(PIDL_ARCHIVE, None)
    rows: list[dict[str, object]] = []
    fig_paths = []
    for cycle in [1, 2, 3, 4, 5]:
        pidl_index = cycle - 1
        print(f"cycle c{cycle}: FEM peak post-history -> PIDL j{pidl_index}")
        pidl_native = pidl_model_and_mesh(PIDL_ARCHIVE, 0.12, pidl_index, pidl_mesh)
        pidl_projected = project_pidl_to_fem(pidl_native, centroids)
        fem_fields = fem_by_cycle[cycle]
        for field, _, mode in FIELDS:
            residual = (
                np.log10((np.maximum(fem_fields[field], 1e-12) + 1e-12) / (np.maximum(pidl_projected[field], 1e-12) + 1e-12))
                if mode == "log"
                else fem_fields[field] - pidl_projected[field]
            )
            add_metric_rows(rows, cycle, field, "FEM", fem_fields[field], areas)
            add_metric_rows(rows, cycle, field, "PIDL_projected_to_FEM", pidl_projected[field], areas)
            add_metric_rows(rows, cycle, field, "residual_FEM_minus_PIDL" if mode != "log" else "residual_log10_FEM_over_PIDL", residual, areas)
        fig_paths.append(plot_cycle(cycle, fem_fields, pidl_projected, nodes, conn, view="neartip"))
        fig_paths.append(plot_cycle(cycle, fem_fields, pidl_projected, nodes, conn, view="full"))
    metrics_path = OUT / "fem22_nstep2_c1_c5_vs_pidl_j0_j4_all_variable_residual_metrics.csv"
    pd.DataFrame(rows).to_csv(metrics_path, index=False)
    manifest = OUT / "README.md"
    manifest.write_text(
        "# FEM22 nstep2 vs PIDL strict baseline residual fields\n\n"
        "Cycles: FEM c1-c5 peak post-history-refresh states compared with PIDL saved indices j0-j4.\n"
        "Residual convention: linear fields use FEM - PIDL; psi fields use log10(FEM/PIDL).\n"
        "Views: near-tip crop x,y in [-0.08,0.08] and full domain x,y in [-0.52,0.52].\n\n"
        "Figures:\n"
        + "".join(f"- `{p.name}`\n" for p in fig_paths)
        + f"\nMetrics: `{metrics_path.name}`\n",
        encoding="utf-8",
    )
    print(f"saved metrics: {metrics_path}")
    for p in fig_paths:
        print(f"saved figure: {p}")


if __name__ == "__main__":
    main()
