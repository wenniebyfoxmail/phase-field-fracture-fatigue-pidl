#!/usr/bin/env python3
"""Compare latest aligned FEM state fields with mapped PIDL states.

The FEM field export is on 45,000 quadrilateral element means. The PIDL mapped
state export is on 90,000 triangular elements. The meshes share the same
underlying grid, but PIDL uses an origin centered at (0, 0). This script shifts
PIDL centroids by +0.5 and averages the two PIDL triangles associated with each
FEM quadrilateral before computing residual fields.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import h5py
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


ROOT = Path("/Users/wenxiaofang/phase-field-fracture-with-pidl/Alignment check 2")
OUT = ROOT / "comparisons/latest_align_state_field_comparison_20260608"
FIG = OUT / "figures"
TAB = OUT / "tables"

FEM_DIR = (
    ROOT
    / "FEM cyclic 012/cases/standard/raw_data/state_field_exports"
    / "latest_align_soft_hist0_state_field_export_20260608"
)
FEM_MAT = FEM_DIR / "latest_align_soft_hist0_state_fields.mat"
FEM_STATE_INDEX = FEM_DIR / "latest_align_soft_hist0_state_index.csv"
FEM_CYCLE_METRICS = (
    ROOT
    / "FEM cyclic 012/cases/standard/raw_data"
    / "reverseBC_u12_diffuse_precrack_soft_hist0_cyclewise_mechanism_metrics.csv"
)

PIDL_DIR = (
    ROOT
    / "PIDL cyclic 012/cases/stateTiming_substeps025_untilFrac_Nphys120_Nstep600"
    / "analysis/mapped_state_fields_20260608"
)
PIDL_SUMMARY = PIDL_DIR / "pidl_mapped_state_summary.csv"
PIDL_FIELDS = PIDL_DIR / "fields"


COMMON_STATES = [
    ("state0_initial_unloaded_prehistory", "pidl_state0_initial_unloaded_prehistory.npz"),
    ("c1_peak", "fem_c0001_peak_pidl_step_0003.npz"),
    ("c1_unloaded", "fem_c0001_unloaded_pidl_step_0004.npz"),
    ("c2_peak", "fem_c0002_peak_pidl_step_0008.npz"),
    ("c2_unloaded", "fem_c0002_unloaded_pidl_step_0009.npz"),
    ("c3_peak", "fem_c0003_peak_pidl_step_0013.npz"),
    ("c3_unloaded", "fem_c0003_unloaded_pidl_step_0014.npz"),
    ("c20_peak", "fem_c0020_peak_pidl_step_0098.npz"),
    ("c20_unloaded", "fem_c0020_unloaded_pidl_step_0099.npz"),
    ("c40_peak", "fem_c0040_peak_pidl_step_0198.npz"),
    ("c40_unloaded", "fem_c0040_unloaded_pidl_step_0199.npz"),
    ("c60_peak", "fem_c0060_peak_pidl_step_0298.npz"),
    ("c60_unloaded", "fem_c0060_unloaded_pidl_step_0299.npz"),
    ("c69_peak", "fem_c0069_peak_pidl_step_0343.npz"),
    ("c69_unloaded", "fem_c0069_unloaded_pidl_step_0344.npz"),
]

PEAK_STATES_FOR_FIELDS = ["c1_peak", "c20_peak", "c40_peak", "c69_peak"]


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    fem_source: str
    pidl_source: str
    cmap: str = "viridis"
    signed: bool = False


FIELD_SPECS = [
    FieldSpec("damage", "damage d / PIDL alpha", "d_elem", "alpha_elem"),
    FieldSpec("alpha_bar", "history alpha_bar", "alpha_bar_elem", "alpha_bar_elem"),
    FieldSpec("f_fatigue", "fatigue degradation f", "f_fatigue_elem", "f_fatigue_elem"),
    FieldSpec("g_stiffness", "stiffness degradation g", "g_stiffness_elem", "g_alpha_elem"),
    FieldSpec("psi_raw", "raw tensile energy psi+", "psi_plus_elem", "psi_raw_elem", "magma"),
    FieldSpec("psi_active_g", "g(alpha) psi+", "g_psi_plus_elem", "psi_active_elem", "magma"),
    FieldSpec("eps_eq", "equivalent strain", "eps_eq_derived", "eps_eq_elem", "magma"),
    FieldSpec("sigma_raw_p1", "principal raw stress 1", "principal_stress_raw_elem:0", "sigma_raw_principal_1_elem", "magma"),
    FieldSpec(
        "sigma_eff_p1",
        "principal degraded/effective stress 1",
        "principal_stress_degraded_effective_elem:0",
        "sigma_effective_principal_1_elem",
        "magma",
    ),
]


def ensure_dirs() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)


def squeeze_fem(h5: h5py.File, name: str, state_i: int) -> np.ndarray:
    """Read one FEM element field for a state."""
    if name == "eps_eq_derived":
        eps = np.asarray(h5["fields/epsilon_elem"])[state_i]
        eps_xy = np.asarray(h5["fields/epsilon_xy_tensor_elem"])[state_i, 0]
        eps_xx = eps[0]
        eps_yy = eps[1]
        return np.sqrt(eps_xx**2 + eps_yy**2 + 2.0 * eps_xy**2)

    comp = None
    base = name
    if ":" in name:
        base, comp_s = name.split(":", 1)
        comp = int(comp_s)

    arr = np.asarray(h5[f"fields/{base}"])
    if arr.ndim == 3 and arr.shape[1] == 1:
        return arr[state_i, 0]
    if arr.ndim == 3 and comp is not None:
        return arr[state_i, comp]
    if arr.ndim == 2:
        return arr[state_i]
    raise ValueError(f"Unsupported FEM field shape for {name}: {arr.shape}")


def field_stats(values: np.ndarray) -> dict[str, float]:
    finite = np.asarray(values)[np.isfinite(values)]
    if finite.size == 0:
        return {k: np.nan for k in ["min", "max", "mean", "p001", "p01", "p99", "p999"]}
    return {
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
        "mean": float(np.mean(finite)),
        "p001": float(np.percentile(finite, 0.1)),
        "p01": float(np.percentile(finite, 1.0)),
        "p99": float(np.percentile(finite, 99.0)),
        "p999": float(np.percentile(finite, 99.9)),
    }


def error_stats(fem: np.ndarray, pidl: np.ndarray) -> dict[str, float]:
    mask = np.isfinite(fem) & np.isfinite(pidl)
    if mask.sum() < 3:
        return {
            "bias": np.nan,
            "mae": np.nan,
            "rmse": np.nan,
            "rel_l2": np.nan,
            "corr": np.nan,
            "p99_abs": np.nan,
            "max_abs": np.nan,
        }
    diff = pidl[mask] - fem[mask]
    denom = np.linalg.norm(fem[mask])
    corr = np.corrcoef(fem[mask], pidl[mask])[0, 1]
    if not np.isfinite(corr):
        corr = np.nan
    return {
        "bias": float(np.mean(diff)),
        "mae": float(np.mean(np.abs(diff))),
        "rmse": float(np.sqrt(np.mean(diff**2))),
        "rel_l2": float(np.linalg.norm(diff) / denom) if denom > 0 else np.nan,
        "corr": float(corr),
        "p99_abs": float(np.percentile(np.abs(diff), 99.0)),
        "max_abs": float(np.max(np.abs(diff))),
    }


def build_pidl_to_fem_map(fem_xy: np.ndarray, pidl_npz: np.lib.npyio.NpzFile) -> tuple[np.ndarray, np.ndarray, dict]:
    pidl_xy = np.column_stack([pidl_npz["elem_x"] + 0.5, pidl_npz["elem_y"] + 0.5])
    tree = cKDTree(fem_xy)
    distances, nearest = tree.query(pidl_xy, k=1)
    counts = np.bincount(nearest, minlength=fem_xy.shape[0])
    diagnostics = {
        "distance_min": float(distances.min()),
        "distance_mean": float(distances.mean()),
        "distance_p99": float(np.percentile(distances, 99.0)),
        "distance_max": float(distances.max()),
        "count_min": int(counts.min()),
        "count_max": int(counts.max()),
        "count_unique": json.dumps({int(k): int(v) for k, v in zip(*np.unique(counts, return_counts=True))}),
    }
    return nearest, pidl_npz["area_elem"].astype(float), diagnostics


def aggregate_pidl(npz: np.lib.npyio.NpzFile, key: str, nearest: np.ndarray, weights: np.ndarray, n_fem: int) -> np.ndarray:
    values = np.asarray(npz[key], dtype=float)
    num = np.bincount(nearest, weights=values * weights, minlength=n_fem)
    den = np.bincount(nearest, weights=weights, minlength=n_fem)
    out = np.full(n_fem, np.nan, dtype=float)
    np.divide(num, den, out=out, where=den > 0)
    return out


def grid_image(values: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    ux = np.unique(np.round(x, 10))
    uy = np.unique(np.round(y, 10))
    xi = {v: i for i, v in enumerate(ux)}
    yi = {v: i for i, v in enumerate(uy)}
    grid = np.full((len(uy), len(ux)), np.nan)
    xr = np.round(x, 10)
    yr = np.round(y, 10)
    for value, xv, yv in zip(values, xr, yr):
        grid[yi[yv], xi[xv]] = value
    return grid


def plot_scalar_histories(pidl_summary: pd.DataFrame, fem_cycle: pd.DataFrame, field_scalar: pd.DataFrame) -> None:
    peak_pidl = pidl_summary[pidl_summary["state_kind"].eq("peak")].copy()
    peak_pidl = peak_pidl[peak_pidl["fem_cycle"].isin([1, 2, 3, 20, 40, 60, 69])]
    fem_pick = fem_cycle[fem_cycle["cycle"].isin(peak_pidl["fem_cycle"])].copy()

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.8), constrained_layout=True)
    axes[0].plot(fem_pick["cycle"], fem_pick["E_el"], "o-", label="FEM cycle metric", lw=1.6)
    axes[0].plot(peak_pidl["fem_cycle"], peak_pidl["E_el"], "s-", label="PIDL mapped peak", lw=1.6)
    fem_field_peak = field_scalar[
        field_scalar["metric"].eq("E_el_field") & field_scalar["state_kind"].eq("peak")
    ]
    axes[0].plot(
        fem_field_peak["cycle"],
        fem_field_peak["fem_value"],
        "x--",
        label="FEM field integral",
        lw=1.1,
    )
    axes[0].set_title("Elastic energy")
    axes[0].set_xlabel("FEM cycle")
    axes[0].set_ylabel("energy")
    axes[0].grid(alpha=0.25)
    axes[0].legend(fontsize=7)

    axes[1].plot(fem_pick["cycle"], fem_pick["E_d"], "o-", label="FEM cycle metric", lw=1.6)
    axes[1].plot(peak_pidl["fem_cycle"], peak_pidl["E_d"], "s-", label="PIDL mapped peak", lw=1.6)
    axes[1].set_title("Crack surface energy")
    axes[1].set_xlabel("FEM cycle")
    axes[1].grid(alpha=0.25)
    axes[1].legend(fontsize=7)

    axes[2].plot(peak_pidl["fem_cycle"], peak_pidl["E_hist"], "s-", label="PIDL E_hist", lw=1.6)
    axes[2].set_title("PIDL irreversibility penalty")
    axes[2].set_xlabel("FEM cycle")
    axes[2].set_ylabel("energy")
    axes[2].grid(alpha=0.25)
    axes[2].legend(fontsize=7)
    fig.suptitle("Energy comparison at mapped peak states")
    for ext in ["png", "pdf"]:
        fig.savefig(FIG / f"energy_histories_latest_aligned.{ext}", dpi=220)
    plt.close(fig)


def plot_state_scalar_panel(scalars: pd.DataFrame) -> None:
    rows = scalars[scalars["stat"].isin(["max", "p99", "mean", "min"])].copy()
    key_stats = {
        "damage": "max",
        "alpha_bar": "max",
        "f_fatigue": "min",
        "psi_raw": "p99",
        "psi_active_g": "p99",
        "eps_eq": "p99",
        "sigma_raw_p1": "p99",
        "sigma_eff_p1": "p99",
    }
    states = [s for s, _ in COMMON_STATES]
    x = np.arange(len(states))
    short = [s.replace("state0_initial_unloaded_prehistory", "state0").replace("_", "\n") for s in states]

    fig, axes = plt.subplots(4, 2, figsize=(15, 12), constrained_layout=True)
    for ax, (metric, stat) in zip(axes.flat, key_stats.items()):
        sub = rows[(rows["metric"].eq(metric)) & (rows["stat"].eq(stat))]
        sub = sub.set_index("state_label").reindex(states)
        ax.plot(x, sub["fem_value"], "o-", label="FEM", lw=1.4, ms=3.5)
        ax.plot(x, sub["pidl_value"], "s-", label="PIDL mapped", lw=1.4, ms=3.5)
        ax.set_title(f"{metric}: {stat}")
        ax.grid(alpha=0.25)
        ax.set_xticks(x)
        ax.set_xticklabels(short, rotation=55, ha="right", fontsize=7)
    axes.flat[0].legend(fontsize=8)
    fig.suptitle("State-by-state scalar reductions")
    for ext in ["png", "pdf"]:
        fig.savefig(FIG / f"state_scalar_reductions_latest_aligned.{ext}", dpi=220)
    plt.close(fig)


def plot_residual_montage(
    field_cache: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]],
    fem_x: np.ndarray,
    fem_y: np.ndarray,
    field_keys: list[str],
    out_name: str,
    title: str,
) -> None:
    n_rows = len(field_keys)
    n_cols = len(PEAK_STATES_FOR_FIELDS) * 3
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(3.05 * n_cols, 2.55 * n_rows), constrained_layout=True)
    if n_rows == 1:
        axes = np.asarray([axes])
    extent = [fem_x.min(), fem_x.max(), fem_y.min(), fem_y.max()]

    for r, key in enumerate(field_keys):
        spec = next(s for s in FIELD_SPECS if s.key == key)
        fem_all = []
        pidl_all = []
        diff_all = []
        for state in PEAK_STATES_FOR_FIELDS:
            fem, pidl = field_cache[(state, key)]
            fem_all.append(fem)
            pidl_all.append(pidl)
            diff_all.append(pidl - fem)
        finite_values = np.concatenate([np.ravel(v[np.isfinite(v)]) for v in fem_all + pidl_all])
        if finite_values.size:
            vmin, vmax = np.percentile(finite_values, [1, 99])
            if vmin == vmax:
                vmin, vmax = float(finite_values.min()), float(finite_values.max())
        else:
            vmin = vmax = 0.0
        max_abs = max(float(np.nanpercentile(np.abs(d), 99.0)) for d in diff_all)
        max_abs = max(max_abs, 1e-12)

        for c, state in enumerate(PEAK_STATES_FOR_FIELDS):
            fem, pidl = field_cache[(state, key)]
            diff = pidl - fem
            panels = [
                ("FEM", fem, spec.cmap, vmin, vmax),
                ("PIDL", pidl, spec.cmap, vmin, vmax),
                ("PIDL-FEM", diff, "RdBu_r", -max_abs, max_abs),
            ]
            for k, (panel_name, values, cmap, lo, hi) in enumerate(panels):
                ax = axes[r, 3 * c + k]
                im = ax.imshow(
                    grid_image(values, fem_x, fem_y),
                    origin="lower",
                    extent=extent,
                    aspect="auto",
                    cmap=cmap,
                    vmin=lo,
                    vmax=hi,
                    interpolation="nearest",
                )
                ax.set_xticks([])
                ax.set_yticks([])
                if r == 0:
                    ax.set_title(f"{state}\n{panel_name}", fontsize=8)
                if k == 0:
                    ax.set_ylabel(spec.label, fontsize=8)
                if k == 2:
                    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
                    cbar.ax.tick_params(labelsize=6)
    fig.suptitle(title)
    for ext in ["png", "pdf"]:
        fig.savefig(FIG / f"{out_name}.{ext}", dpi=220)
    plt.close(fig)


def plot_c1_substeps_fem_only(h5: h5py.File, fem_index: pd.DataFrame, fem_x: np.ndarray, fem_y: np.ndarray) -> None:
    states = ["state0_initial_unloaded_prehistory", "c1_step1", "c1_step2", "c1_step3", "c1_peak", "c1_unloaded"]
    fields = [
        ("d_elem", "damage d", "viridis"),
        ("psi_plus_elem", "raw psi+", "magma"),
        ("g_psi_plus_elem", "g psi+", "magma"),
        ("alpha_bar_elem", "alpha_bar", "viridis"),
    ]
    state_to_i = {row.state_label: i for i, row in fem_index.iterrows()}
    extent = [fem_x.min(), fem_x.max(), fem_y.min(), fem_y.max()]
    fig, axes = plt.subplots(len(fields), len(states), figsize=(3.0 * len(states), 2.4 * len(fields)), constrained_layout=True)
    for r, (field, label, cmap) in enumerate(fields):
        vals = [squeeze_fem(h5, field, state_to_i[s]) for s in states]
        finite = np.concatenate([v[np.isfinite(v)] for v in vals])
        vmin, vmax = np.percentile(finite, [1, 99]) if finite.size else (0, 0)
        for c, state in enumerate(states):
            ax = axes[r, c]
            im = ax.imshow(
                grid_image(vals[c], fem_x, fem_y),
                origin="lower",
                extent=extent,
                aspect="auto",
                cmap=cmap,
                vmin=vmin,
                vmax=vmax,
                interpolation="nearest",
            )
            ax.set_xticks([])
            ax.set_yticks([])
            if r == 0:
                ax.set_title(state.replace("_", "\n"), fontsize=8)
            if c == 0:
                ax.set_ylabel(label, fontsize=8)
            if c == len(states) - 1:
                cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
                cb.ax.tick_params(labelsize=6)
    fig.suptitle("FEM cycle-1 state timing fields")
    for ext in ["png", "pdf"]:
        fig.savefig(FIG / f"fem_c1_state_timing_fields.{ext}", dpi=220)
    plt.close(fig)


def plot_state0_c1_alignment_audit(
    field_cache: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]],
    fem_x: np.ndarray,
    fem_y: np.ndarray,
) -> None:
    states = ["state0_initial_unloaded_prehistory", "c1_peak"]
    field_keys = ["damage", "alpha_bar", "f_fatigue", "eps_eq", "sigma_eff_p1"]
    n_rows = len(field_keys)
    n_cols = len(states) * 3
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(3.1 * n_cols, 2.45 * n_rows), constrained_layout=True)
    extent = [fem_x.min(), fem_x.max(), fem_y.min(), fem_y.max()]

    for r, key in enumerate(field_keys):
        spec = next(s for s in FIELD_SPECS if s.key == key)
        fem_all = []
        pidl_all = []
        diff_all = []
        for state in states:
            fem, pidl = field_cache[(state, key)]
            fem_all.append(fem)
            pidl_all.append(pidl)
            diff_all.append(pidl - fem)
        finite = np.concatenate([v[np.isfinite(v)] for v in fem_all + pidl_all])
        vmin, vmax = np.percentile(finite, [1, 99]) if finite.size else (0.0, 0.0)
        if vmin == vmax:
            vmin, vmax = float(np.nanmin(finite)), float(np.nanmax(finite))
        diff_scale = max(float(np.nanpercentile(np.abs(d), 99.0)) for d in diff_all)
        diff_scale = max(diff_scale, 1e-12)

        for c, state in enumerate(states):
            fem, pidl = field_cache[(state, key)]
            diff = pidl - fem
            panels = [
                ("FEM", fem, spec.cmap, vmin, vmax),
                ("PIDL", pidl, spec.cmap, vmin, vmax),
                ("PIDL-FEM", diff, "RdBu_r", -diff_scale, diff_scale),
            ]
            for p, (panel, values, cmap, lo, hi) in enumerate(panels):
                ax = axes[r, 3 * c + p]
                im = ax.imshow(
                    grid_image(values, fem_x, fem_y),
                    origin="lower",
                    extent=extent,
                    aspect="auto",
                    cmap=cmap,
                    vmin=lo,
                    vmax=hi,
                    interpolation="nearest",
                )
                ax.set_xticks([])
                ax.set_yticks([])
                if r == 0:
                    ax.set_title(f"{state}\n{panel}", fontsize=8)
                if p == 0:
                    ax.set_ylabel(spec.label, fontsize=8)
                if p == 2:
                    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
                    cb.ax.tick_params(labelsize=6)
    fig.suptitle("State0 and first peak alignment audit")
    for ext in ["png", "pdf"]:
        fig.savefig(FIG / f"state0_c1_alignment_audit.{ext}", dpi=220)
    plt.close(fig)


def main() -> None:
    ensure_dirs()
    fem_index = pd.read_csv(FEM_STATE_INDEX)
    fem_cycle = pd.read_csv(FEM_CYCLE_METRICS)
    pidl_summary = pd.read_csv(PIDL_SUMMARY)

    with h5py.File(FEM_MAT, "r") as h5:
        fem_x = np.asarray(h5["element_centroids"])[0].astype(float)
        fem_y = np.asarray(h5["element_centroids"])[1].astype(float)
        fem_area = np.asarray(h5["element_area"]).squeeze().astype(float)
        fem_xy = np.column_stack([fem_x, fem_y])
        n_fem = len(fem_x)

        first_npz = np.load(PIDL_FIELDS / COMMON_STATES[1][1])
        nearest, weights, map_diag = build_pidl_to_fem_map(fem_xy, first_npz)
        pd.DataFrame([map_diag]).to_csv(TAB / "pidl_to_fem_mapping_diagnostics.csv", index=False)

        state_to_i = {row.state_label: i for i, row in fem_index.iterrows()}
        scalar_rows = []
        error_rows = []
        field_cache: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]] = {}

        for state_label, pidl_file in COMMON_STATES:
            state_i = state_to_i[state_label]
            row = fem_index.iloc[state_i]
            npz = np.load(PIDL_FIELDS / pidl_file)
            cycle = int(row["cycle"])
            kind = "state0" if cycle == 0 else ("peak" if "peak" in state_label else "unloaded")

            fem_e_el_field = np.sum(
                (
                    squeeze_fem(h5, "g_psi_plus_elem", state_i)
                    + squeeze_fem(h5, "psi_minus_elem", state_i)
                )
                * fem_area
            )
            pidl_e_el = float(np.sum(npz["E_el_elem"]))
            pidl_e_d = float(np.sum(npz["E_d_elem"]))
            pidl_e_hist = float(np.sum(npz["E_hist_elem"]))
            for metric, fem_value, pidl_value in [
                ("E_el_field", fem_e_el_field, pidl_e_el),
                ("E_d", np.nan, pidl_e_d),
                ("E_hist", np.nan, pidl_e_hist),
            ]:
                scalar_rows.append(
                    {
                        "state_label": state_label,
                        "cycle": cycle,
                        "state_kind": kind,
                        "metric": metric,
                        "stat": "integral",
                        "fem_value": fem_value,
                        "pidl_value": pidl_value,
                        "pidl_minus_fem": pidl_value - fem_value if np.isfinite(fem_value) else np.nan,
                        "pidl_over_fem": pidl_value / fem_value if fem_value not in (0, np.nan) and np.isfinite(fem_value) else np.nan,
                    }
                )

            for spec in FIELD_SPECS:
                fem_values = squeeze_fem(h5, spec.fem_source, state_i).astype(float)
                pidl_values = aggregate_pidl(npz, spec.pidl_source, nearest, weights, n_fem)
                field_cache[(state_label, spec.key)] = (fem_values, pidl_values)
                fstats = field_stats(fem_values)
                pstats = field_stats(pidl_values)
                for stat in fstats:
                    fem_value = fstats[stat]
                    pidl_value = pstats[stat]
                    scalar_rows.append(
                        {
                            "state_label": state_label,
                            "cycle": cycle,
                            "state_kind": kind,
                            "metric": spec.key,
                            "stat": stat,
                            "fem_value": fem_value,
                            "pidl_value": pidl_value,
                            "pidl_minus_fem": pidl_value - fem_value,
                            "pidl_over_fem": pidl_value / fem_value if abs(fem_value) > 1e-30 else np.nan,
                        }
                    )
                erow = {
                    "state_label": state_label,
                    "cycle": cycle,
                    "state_kind": kind,
                    "metric": spec.key,
                }
                erow.update(error_stats(fem_values, pidl_values))
                error_rows.append(erow)

        scalars = pd.DataFrame(scalar_rows)
        errors = pd.DataFrame(error_rows)
        scalars.to_csv(TAB / "state_scalar_reductions_latest_aligned.csv", index=False)
        errors.to_csv(TAB / "field_error_metrics_latest_aligned.csv", index=False)

        peak_energy_rows = []
        for cycle in [1, 2, 3, 20, 40, 60, 69]:
            fem_row = fem_cycle[fem_cycle["cycle"].eq(cycle)].iloc[0]
            pidl_row = pidl_summary[
                pidl_summary["state_label"].str.contains(f"c{cycle:04d}_peak", regex=False)
            ]
            if pidl_row.empty:
                continue
            pidl_row = pidl_row.iloc[0]
            peak_energy_rows.append(
                {
                    "cycle": cycle,
                    "fem_E_el_cycle_metric": fem_row["E_el"],
                    "fem_E_d_cycle_metric": fem_row["E_d"],
                    "pidl_E_el_peak": pidl_row["E_el"],
                    "pidl_E_d_peak": pidl_row["E_d"],
                    "pidl_E_hist_peak": pidl_row["E_hist"],
                    "pidl_E_el_over_fem": pidl_row["E_el"] / fem_row["E_el"],
                    "pidl_E_d_over_fem": pidl_row["E_d"] / fem_row["E_d"],
                }
            )
        peak_energy = pd.DataFrame(peak_energy_rows)
        peak_energy.to_csv(TAB / "peak_energy_comparison_latest_aligned.csv", index=False)

        # Delta alpha_bar overlap: compare cycle-to-cycle history increments.
        delta_rows = []
        peak_states = ["c1_peak", "c20_peak", "c40_peak", "c60_peak", "c69_peak"]
        prev_state = "state0_initial_unloaded_prehistory"
        for state in peak_states:
            fem_prev, pidl_prev = field_cache[(prev_state, "alpha_bar")]
            fem_cur, pidl_cur = field_cache[(state, "alpha_bar")]
            fem_delta = fem_cur - fem_prev
            pidl_delta = pidl_cur - pidl_prev
            fem_damage = field_cache[(state, "damage")][0]
            fem_zone = fem_damage > 0.95
            pidl_top = pidl_delta >= np.percentile(pidl_delta, 99.0)
            fem_top = fem_delta >= np.percentile(fem_delta, 99.0)
            delta_rows.append(
                {
                    "interval": f"{prev_state}->{state}",
                    "cycle": int(state.split("_")[0][1:]),
                    "pidl_top1pct_overlap_fem_d_gt_095": float((pidl_top & fem_zone).sum() / max(pidl_top.sum(), 1)),
                    "fem_top1pct_overlap_fem_d_gt_095": float((fem_top & fem_zone).sum() / max(fem_top.sum(), 1)),
                    "pidl_top1pct_overlap_fem_top1pct": float((pidl_top & fem_top).sum() / max(pidl_top.sum(), 1)),
                    "pidl_delta_sum": float(np.sum(pidl_delta * fem_area)),
                    "fem_delta_sum": float(np.sum(fem_delta * fem_area)),
                }
            )
            prev_state = state
        pd.DataFrame(delta_rows).to_csv(TAB / "delta_alpha_bar_overlap_latest_aligned.csv", index=False)

        plot_scalar_histories(pidl_summary, fem_cycle, scalars)
        plot_state_scalar_panel(scalars)
        plot_c1_substeps_fem_only(h5, fem_index, fem_x, fem_y)
        plot_state0_c1_alignment_audit(field_cache, fem_x, fem_y)
        plot_residual_montage(
            field_cache,
            fem_x,
            fem_y,
            ["damage", "alpha_bar", "f_fatigue", "g_stiffness"],
            "residual_fields_damage_history_degradation_peak_states",
            "Damage/history/degradation residuals at mapped peak states",
        )
        plot_residual_montage(
            field_cache,
            fem_x,
            fem_y,
            ["psi_raw", "psi_active_g"],
            "residual_fields_energy_drivers_peak_states",
            "Raw and degraded tensile-energy residuals at mapped peak states",
        )
        plot_residual_montage(
            field_cache,
            fem_x,
            fem_y,
            ["eps_eq", "sigma_raw_p1", "sigma_eff_p1"],
            "residual_fields_strain_stress_peak_states",
            "Strain and stress residuals at mapped peak states",
        )

    manifest = {
        "fem_mat": str(FEM_MAT),
        "fem_state_index": str(FEM_STATE_INDEX),
        "fem_cycle_metrics": str(FEM_CYCLE_METRICS),
        "pidl_mapped_state_dir": str(PIDL_DIR),
        "output_dir": str(OUT),
        "common_state_count": len(COMMON_STATES),
        "field_mapping": "PIDL centroids shifted by +0.5,+0.5; two PIDL triangles area-averaged to each FEM quadrilateral element.",
        "energy_note": "FEM E_d comes from cyclewise metrics; latest FEM field MAT lacks phase-field gradient data needed to recompute E_d.",
    }
    (OUT / "comparison_manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
