#!/usr/bin/env python3
"""Compare the precrack-fatigue-mask PIDL run against aligned FEM states."""

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
OUT = ROOT / "comparisons/precrack_fatigue_mask_vs_fem_state_fields_20260609"
FIG = OUT / "figures"
TAB = OUT / "tables"

FEM_DIR = (
    ROOT
    / "FEM cyclic 012/cases/standard/raw_data/state_field_exports"
    / "latest_align_soft_hist0_state_field_export_20260608"
)
FEM_MAT = FEM_DIR / "latest_align_soft_hist0_state_fields.mat"
FEM_INDEX = FEM_DIR / "latest_align_soft_hist0_state_index.csv"
FEM_CYCLE = (
    ROOT
    / "FEM cyclic 012/cases/standard/raw_data"
    / "reverseBC_u12_diffuse_precrack_soft_hist0_cyclewise_mechanism_metrics.csv"
)

PIDL_CASE = ROOT / "PIDL cyclic 012/cases/precrack_fatigue_mask_ad085f3_20260608"
PIDL_RUN = next((PIDL_CASE / "raw_archive").glob("pfmask_*"))
PIDL_DIAG = PIDL_RUN / "element_diagnostics_precrack_fatigue_mask"
PIDL_BEST = PIDL_RUN / "best_models"
PIDL_LOG = PIDL_CASE / "logs/precrack_fatigue_mask_current_active_u012.log"


STATE_TO_STEP = {
    "state0_initial_unloaded_prehistory": 0,
    "c1_peak": 3,
    "c1_unloaded": 4,
    "c2_peak": 8,
    "c2_unloaded": 9,
    "c3_peak": 13,
    "c3_unloaded": 14,
    "c20_peak": 98,
    "c20_unloaded": 99,
    "c40_peak": 198,
    "c40_unloaded": 199,
    "c60_peak": 298,
    "c60_unloaded": 299,
    "c69_peak": 343,
    "c69_unloaded": 344,
}
PEAK_STATES = ["c1_peak", "c20_peak", "c40_peak", "c69_peak"]


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    fem_source: str
    pidl_source: str
    cmap: str = "viridis"


FIELDS = [
    FieldSpec("damage", "damage d / PIDL alpha", "d_elem", "alpha_elem"),
    FieldSpec("alpha_bar", "fatigue history alpha_bar", "alpha_bar_elem", "hist_fat_elem"),
    FieldSpec("f_fatigue", "fatigue degradation f", "f_fatigue_elem", "f_fatigue_elem"),
    FieldSpec("g_stiffness", "stiffness degradation g", "g_stiffness_elem", "g_alpha_elem"),
    FieldSpec("psi_raw", "raw tensile energy psi+", "psi_plus_elem", "psi_raw_elem", "magma"),
    FieldSpec("psi_active", "active driver g psi+", "g_psi_plus_elem", "psi_active_elem", "magma"),
    FieldSpec("history_driver", "PIDL history driver", "g_psi_plus_elem", "psi_history_driver_elem", "magma"),
]


def ensure_dirs() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)


def load_npz_for_state(state: str) -> np.lib.npyio.NpzFile:
    return np.load(PIDL_DIAG / f"element_fields_cycle_{STATE_TO_STEP[state]:04d}.npz")


def squeeze_fem(h5: h5py.File, name: str, state_i: int) -> np.ndarray:
    arr = np.asarray(h5[f"fields/{name}"])
    if arr.ndim == 3 and arr.shape[1] == 1:
        return arr[state_i, 0].astype(float)
    if arr.ndim == 2:
        return arr[state_i].astype(float)
    raise ValueError(f"Unsupported FEM field shape for {name}: {arr.shape}")


def aggregate_to_fem(npz: np.lib.npyio.NpzFile, key: str, nearest: np.ndarray, weights: np.ndarray, n: int) -> np.ndarray:
    values = np.asarray(npz[key], dtype=float)
    num = np.bincount(nearest, weights=values * weights, minlength=n)
    den = np.bincount(nearest, weights=weights, minlength=n)
    out = np.full(n, np.nan)
    np.divide(num, den, out=out, where=den > 0)
    return out


def stats(values: np.ndarray) -> dict[str, float]:
    v = values[np.isfinite(values)]
    if v.size == 0:
        return {k: np.nan for k in ["min", "mean", "max", "p99", "p999"]}
    return {
        "min": float(np.min(v)),
        "mean": float(np.mean(v)),
        "max": float(np.max(v)),
        "p99": float(np.percentile(v, 99.0)),
        "p999": float(np.percentile(v, 99.9)),
    }


def error_stats(fem: np.ndarray, pidl: np.ndarray) -> dict[str, float]:
    m = np.isfinite(fem) & np.isfinite(pidl)
    if np.sum(m) < 3:
        return {"bias": np.nan, "mae": np.nan, "rmse": np.nan, "rel_l2": np.nan, "corr": np.nan}
    diff = pidl[m] - fem[m]
    denom = np.linalg.norm(fem[m])
    corr = np.corrcoef(fem[m], pidl[m])[0, 1]
    return {
        "bias": float(np.mean(diff)),
        "mae": float(np.mean(np.abs(diff))),
        "rmse": float(np.sqrt(np.mean(diff**2))),
        "rel_l2": float(np.linalg.norm(diff) / denom) if denom > 0 else np.nan,
        "corr": float(corr) if np.isfinite(corr) else np.nan,
    }


def grid_image(values: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    ux = np.unique(np.round(x, 10))
    uy = np.unique(np.round(y, 10))
    xi = {v: i for i, v in enumerate(ux)}
    yi = {v: i for i, v in enumerate(uy)}
    grid = np.full((len(uy), len(ux)), np.nan)
    for val, xv, yv in zip(values, np.round(x, 10), np.round(y, 10)):
        grid[yi[yv], xi[xv]] = val
    return grid


def plot_energy_histories(fem_cycle: pd.DataFrame, scalar: pd.DataFrame) -> None:
    cycles = [1, 2, 3, 20, 40, 60, 69]
    peak = scalar[(scalar["state_kind"].eq("peak")) & (scalar["stat"].eq("integral"))]
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.8), constrained_layout=True)

    fem_pick = fem_cycle[fem_cycle["cycle"].isin(cycles)]
    for ax, metric, title in [
        (axes[0], "E_el", "Elastic energy"),
        (axes[1], "E_d", "Crack surface energy"),
        (axes[2], "E_hist", "PIDL irreversibility/history penalty"),
    ]:
        if metric in fem_pick:
            ax.plot(fem_pick["cycle"], fem_pick[metric], "o-", label="FEM cycle metric", lw=1.5)
        sub = peak[peak["metric"].eq(metric)]
        if not sub.empty:
            ax.plot(sub["cycle"], sub["pidl_value"], "s-", label="PIDL precrack-mask peak", lw=1.5)
        ax.set_title(title)
        ax.set_xlabel("FEM cycle")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
    fig.suptitle("Precrack-fatigue-mask PIDL vs FEM energy history")
    for ext in ["png", "pdf"]:
        fig.savefig(FIG / f"precrack_mask_energy_histories.{ext}", dpi=220)
    plt.close(fig)


def plot_scalar_reductions(scalar: pd.DataFrame) -> None:
    pick = {
        "damage": "max",
        "alpha_bar": "max",
        "f_fatigue": "min",
        "g_stiffness": "p99",
        "psi_raw": "p99",
        "psi_active": "p99",
        "history_driver": "p99",
    }
    states = list(STATE_TO_STEP)
    labels = [s.replace("state0_initial_unloaded_prehistory", "state0").replace("_", "\n") for s in states]
    x = np.arange(len(states))
    fig, axes = plt.subplots(4, 2, figsize=(15, 11), constrained_layout=True)
    for ax, (metric, stat) in zip(axes.flat, pick.items()):
        sub = scalar[(scalar["metric"].eq(metric)) & (scalar["stat"].eq(stat))].set_index("state").reindex(states)
        ax.plot(x, sub["fem_value"], "o-", label="FEM", lw=1.3, ms=3)
        ax.plot(x, sub["pidl_value"], "s-", label="PIDL precrack-mask", lw=1.3, ms=3)
        ax.set_title(f"{metric}: {stat}")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=55, ha="right", fontsize=7)
        ax.grid(alpha=0.25)
    axes.flat[0].legend(fontsize=8)
    axes.flat[-1].axis("off")
    fig.suptitle("State-by-state scalar reductions")
    for ext in ["png", "pdf"]:
        fig.savefig(FIG / f"precrack_mask_state_scalar_reductions.{ext}", dpi=220)
    plt.close(fig)


def plot_residual_montage(cache: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]], x: np.ndarray, y: np.ndarray) -> None:
    field_keys = ["damage", "alpha_bar", "f_fatigue", "g_stiffness", "psi_raw", "psi_active", "history_driver"]
    n_rows = len(field_keys)
    n_cols = len(PEAK_STATES) * 3
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(3.05 * n_cols, 2.35 * n_rows), constrained_layout=True)
    extent = [x.min(), x.max(), y.min(), y.max()]
    for r, key in enumerate(field_keys):
        spec = next(f for f in FIELDS if f.key == key)
        fem_all = [cache[(s, key)][0] for s in PEAK_STATES]
        pidl_all = [cache[(s, key)][1] for s in PEAK_STATES]
        diff_all = [p - f for f, p in zip(fem_all, pidl_all)]
        finite = np.concatenate([v[np.isfinite(v)] for v in fem_all + pidl_all])
        vmin, vmax = np.percentile(finite, [1, 99]) if finite.size else (0.0, 1.0)
        if vmin == vmax:
            vmin, vmax = float(np.nanmin(finite)), float(np.nanmax(finite))
        dmax = max(float(np.nanpercentile(np.abs(d), 99.0)) for d in diff_all)
        dmax = max(dmax, 1e-12)
        for c, state in enumerate(PEAK_STATES):
            fem, pidl = cache[(state, key)]
            panels = [("FEM", fem, spec.cmap, vmin, vmax), ("PIDL", pidl, spec.cmap, vmin, vmax), ("PIDL-FEM", pidl - fem, "RdBu_r", -dmax, dmax)]
            for j, (title, values, cmap, lo, hi) in enumerate(panels):
                ax = axes[r, 3 * c + j]
                im = ax.imshow(grid_image(values, x, y), origin="lower", extent=extent, aspect="auto", cmap=cmap, vmin=lo, vmax=hi, interpolation="nearest")
                ax.set_xticks([])
                ax.set_yticks([])
                if r == 0:
                    ax.set_title(f"{state}\n{title}", fontsize=8)
                if j == 0:
                    ax.set_ylabel(spec.label, fontsize=8)
                if j == 2:
                    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
                    cb.ax.tick_params(labelsize=6)
    fig.suptitle("Residual field comparison: PIDL precrack-mask minus FEM")
    for ext in ["png", "pdf"]:
        fig.savefig(FIG / f"precrack_mask_residual_fields_peak_states.{ext}", dpi=220)
    plt.close(fig)


def plot_delta_history(cache: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]], area: np.ndarray) -> None:
    rows = []
    prev = "state0_initial_unloaded_prehistory"
    for state in PEAK_STATES:
        fem_prev, pidl_prev = cache[(prev, "alpha_bar")]
        fem_cur, pidl_cur = cache[(state, "alpha_bar")]
        fd = fem_cur - fem_prev
        pd_ = pidl_cur - pidl_prev
        fem_zone = cache[(state, "damage")][0] > 0.95
        pidl_top = pd_ >= np.nanpercentile(pd_, 99)
        fem_top = fd >= np.nanpercentile(fd, 99)
        rows.append({
            "interval": f"{prev}->{state}",
            "cycle": int(state.split("_")[0][1:]),
            "fem_delta_integral": float(np.nansum(fd * area)),
            "pidl_delta_integral": float(np.nansum(pd_ * area)),
            "pidl_over_fem": float(np.nansum(pd_ * area) / np.nansum(fd * area)) if abs(np.nansum(fd * area)) > 1e-30 else np.nan,
            "pidl_top1pct_overlap_fem_damage_gt_095": float(np.sum(pidl_top & fem_zone) / max(np.sum(pidl_top), 1)),
            "pidl_top1pct_overlap_fem_top1pct": float(np.sum(pidl_top & fem_top) / max(np.sum(pidl_top), 1)),
        })
        prev = state
    df = pd.DataFrame(rows)
    df.to_csv(TAB / "precrack_mask_delta_history_overlap.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), constrained_layout=True)
    axes[0].plot(df["cycle"], df["fem_delta_integral"], "o-", label="FEM")
    axes[0].plot(df["cycle"], df["pidl_delta_integral"], "s-", label="PIDL precrack-mask")
    axes[0].set_title("Incremental alpha_bar integral")
    axes[0].set_xlabel("cycle")
    axes[0].grid(alpha=0.25)
    axes[0].legend(fontsize=8)
    axes[1].plot(df["cycle"], df["pidl_top1pct_overlap_fem_damage_gt_095"], "o-", label="overlap FEM d>0.95")
    axes[1].plot(df["cycle"], df["pidl_top1pct_overlap_fem_top1pct"], "s-", label="overlap FEM top 1% delta")
    axes[1].set_title("PIDL top history increment overlap")
    axes[1].set_xlabel("cycle")
    axes[1].set_ylim(-0.02, 1.02)
    axes[1].grid(alpha=0.25)
    axes[1].legend(fontsize=8)
    for ext in ["png", "pdf"]:
        fig.savefig(FIG / f"precrack_mask_delta_history_overlap.{ext}", dpi=220)
    plt.close(fig)


def main() -> None:
    ensure_dirs()
    fem_index = pd.read_csv(FEM_INDEX)
    fem_cycle = pd.read_csv(FEM_CYCLE)
    state_i = {r.state_label: i for i, r in fem_index.iterrows()}
    field_cache: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]] = {}
    scalar_rows = []
    error_rows = []

    with h5py.File(FEM_MAT, "r") as h5:
        fem_x = np.asarray(h5["element_centroids"])[0].astype(float)
        fem_y = np.asarray(h5["element_centroids"])[1].astype(float)
        fem_area = np.asarray(h5["element_area"]).squeeze().astype(float)
        n_fem = len(fem_x)
        fem_xy = np.column_stack([fem_x, fem_y])

        first = load_npz_for_state("c1_peak")
        pidl_xy = np.column_stack([first["elem_x"] + 0.5, first["elem_y"] + 0.5])
        dist, nearest = cKDTree(fem_xy).query(pidl_xy, k=1)
        weights = np.asarray(first["area_elem"], dtype=float)
        map_diag = {
            "distance_min": float(dist.min()),
            "distance_mean": float(dist.mean()),
            "distance_p99": float(np.percentile(dist, 99)),
            "distance_max": float(dist.max()),
            "pidl_triangles": int(len(pidl_xy)),
            "fem_elements": int(n_fem),
        }
        pd.DataFrame([map_diag]).to_csv(TAB / "precrack_mask_mapping_diagnostics.csv", index=False)

        for state in STATE_TO_STEP:
            z = load_npz_for_state(state)
            cycle = 0 if state.startswith("state0") else int(state.split("_")[0][1:])
            kind = "state0" if cycle == 0 else ("peak" if "peak" in state else "unloaded")
            fem_state = state_i[state]

            energy_pairs = [
                ("E_el", np.nan, float(np.nansum(z["E_el_elem"]))),
                ("E_d", np.nan, float(np.nansum(z["E_d_elem"]))),
                ("E_hist", np.nan, float(np.nansum(z["E_hist_elem"]))),
            ]
            for metric, fem_value, pidl_value in energy_pairs:
                scalar_rows.append({
                    "state": state,
                    "cycle": cycle,
                    "step": STATE_TO_STEP[state],
                    "state_kind": kind,
                    "metric": metric,
                    "stat": "integral",
                    "fem_value": fem_value,
                    "pidl_value": pidl_value,
                    "pidl_minus_fem": np.nan,
                    "pidl_over_fem": np.nan,
                })

            for spec in FIELDS:
                fem = squeeze_fem(h5, spec.fem_source, fem_state)
                pidl = aggregate_to_fem(z, spec.pidl_source, nearest, weights, n_fem)
                field_cache[(state, spec.key)] = (fem, pidl)
                fs = stats(fem)
                ps = stats(pidl)
                for stat, fem_value in fs.items():
                    pidl_value = ps[stat]
                    scalar_rows.append({
                        "state": state,
                        "cycle": cycle,
                        "step": STATE_TO_STEP[state],
                        "state_kind": kind,
                        "metric": spec.key,
                        "stat": stat,
                        "fem_value": fem_value,
                        "pidl_value": pidl_value,
                        "pidl_minus_fem": pidl_value - fem_value,
                        "pidl_over_fem": pidl_value / fem_value if abs(fem_value) > 1e-30 else np.nan,
                    })
                erow = {"state": state, "cycle": cycle, "step": STATE_TO_STEP[state], "state_kind": kind, "metric": spec.key}
                erow.update(error_stats(fem, pidl))
                error_rows.append(erow)

        scalar = pd.DataFrame(scalar_rows)
        errors = pd.DataFrame(error_rows)
        scalar.to_csv(TAB / "precrack_mask_state_scalar_reductions.csv", index=False)
        errors.to_csv(TAB / "precrack_mask_field_error_metrics.csv", index=False)

        plot_energy_histories(fem_cycle, scalar)
        plot_scalar_reductions(scalar)
        plot_residual_montage(field_cache, fem_x, fem_y)
        plot_delta_history(field_cache, fem_area)

    manifest = {
        "comparison": "precrack_fatigue_mask_vs_fem_state_fields_20260609",
        "pidl_case": str(PIDL_CASE),
        "pidl_run": str(PIDL_RUN),
        "pidl_log": str(PIDL_LOG),
        "fem_state_field_export": str(FEM_MAT),
        "fem_state_index": str(FEM_INDEX),
        "state_to_pidl_step": STATE_TO_STEP,
        "note": "PIDL hist_fat_elem is used as fatigue-history alpha_bar for this diagnostic.",
    }
    (OUT / "comparison_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
