#!/usr/bin/env python3
"""Compare FEM/PIDL candidate fatigue drivers on the same mapped states.

The FEM state-field package is on 45,000 quadrilateral element means. The PIDL
state package is on 90,000 triangular elements. This script shifts PIDL element
centroids by +0.5 and area-averages the two triangles onto the FEM cell grid,
then compares the same driver definitions on the same states and regions.
"""

from __future__ import annotations

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
FEM_INDEX = FEM_DIR / "latest_align_soft_hist0_state_index.csv"

PIDL_FIELDS = (
    ROOT
    / "PIDL cyclic 012/cases/stateTiming_substeps025_untilFrac_Nphys120_Nstep600"
    / "analysis/mapped_state_fields_20260608/fields"
)

STATE_TO_PIDL = {
    "state0_initial_unloaded_prehistory": "pidl_state0_initial_unloaded_prehistory.npz",
    "c1_peak": "fem_c0001_peak_pidl_step_0003.npz",
    "c1_unloaded": "fem_c0001_unloaded_pidl_step_0004.npz",
    "c2_peak": "fem_c0002_peak_pidl_step_0008.npz",
    "c2_unloaded": "fem_c0002_unloaded_pidl_step_0009.npz",
    "c3_peak": "fem_c0003_peak_pidl_step_0013.npz",
    "c3_unloaded": "fem_c0003_unloaded_pidl_step_0014.npz",
    "c20_peak": "fem_c0020_peak_pidl_step_0098.npz",
    "c20_unloaded": "fem_c0020_unloaded_pidl_step_0099.npz",
    "c40_peak": "fem_c0040_peak_pidl_step_0198.npz",
    "c40_unloaded": "fem_c0040_unloaded_pidl_step_0199.npz",
    "c60_peak": "fem_c0060_peak_pidl_step_0298.npz",
    "c60_unloaded": "fem_c0060_unloaded_pidl_step_0299.npz",
    "c69_peak": "fem_c0069_peak_pidl_step_0343.npz",
    "c69_unloaded": "fem_c0069_unloaded_pidl_step_0344.npz",
}

TEMPORAL_STATES = list(STATE_TO_PIDL)
PEAK_FIELD_STATES = ["c1_peak", "c20_peak", "c69_peak"]


@dataclass(frozen=True)
class Quantity:
    key: str
    label: str
    kind: str


QUANTITIES = [
    Quantity("raw_driver", "raw psi+", "driver"),
    Quantity("active_driver", "g * psi+", "driver"),
    Quantity("fatigue_effective_driver", "f * g * psi+", "driver"),
    Quantity("g_direct", "g(alpha)", "degradation"),
    Quantity("g_from_driver_ratio", "(g * psi+) / psi+", "degradation"),
    Quantity("f_direct", "f(alpha_bar)", "degradation"),
    Quantity("f_from_driver_ratio", "(f * g * psi+) / (g * psi+)", "degradation"),
    Quantity("alpha_bar", "alpha_bar", "history"),
    Quantity("damage", "damage d/alpha", "damage"),
]


def squeeze_state_field(h5: h5py.File, name: str, state_i: int) -> np.ndarray:
    arr = np.asarray(h5[f"fields/{name}"])
    if arr.ndim == 3 and arr.shape[1] == 1:
        return arr[state_i, 0].astype(float)
    if arr.ndim == 2:
        return arr[state_i].astype(float)
    raise ValueError(f"Unsupported FEM field shape for {name}: {arr.shape}")


def ratio(num: np.ndarray, den: np.ndarray, eps: float = 1e-30) -> np.ndarray:
    out = np.full_like(num, np.nan, dtype=float)
    np.divide(num, den, out=out, where=np.isfinite(num) & np.isfinite(den) & (np.abs(den) > eps))
    return out


def aggregate_pidl(
    npz: np.lib.npyio.NpzFile,
    key: str,
    nearest: np.ndarray,
    weights: np.ndarray,
    n_fem: int,
) -> np.ndarray:
    values = np.asarray(npz[key], dtype=float)
    num = np.bincount(nearest, weights=values * weights, minlength=n_fem)
    den = np.bincount(nearest, weights=weights, minlength=n_fem)
    out = np.full(n_fem, np.nan, dtype=float)
    np.divide(num, den, out=out, where=den > 0)
    return out


def weighted_stats(values: np.ndarray, area: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    m = mask & np.isfinite(values)
    if not np.any(m):
        return {
            "area_mean": np.nan,
            "integral": np.nan,
            "mean": np.nan,
            "p99": np.nan,
            "p999": np.nan,
            "max": np.nan,
        }
    v = values[m]
    a = area[m]
    return {
        "area_mean": float(np.sum(v * a) / np.sum(a)),
        "integral": float(np.sum(v * a)),
        "mean": float(np.mean(v)),
        "p99": float(np.percentile(v, 99.0)),
        "p999": float(np.percentile(v, 99.9)),
        "max": float(np.max(v)),
    }


def corr(a: np.ndarray, b: np.ndarray, mask: np.ndarray) -> float:
    m = mask & np.isfinite(a) & np.isfinite(b)
    if np.sum(m) < 3 or np.std(a[m]) == 0 or np.std(b[m]) == 0:
        return np.nan
    return float(np.corrcoef(a[m], b[m])[0, 1])


def grid_image(values: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    ux = np.unique(np.round(x, 10))
    uy = np.unique(np.round(y, 10))
    xi = {v: i for i, v in enumerate(ux)}
    yi = {v: i for i, v in enumerate(uy)}
    grid = np.full((len(uy), len(ux)), np.nan)
    for value, xv, yv in zip(values, np.round(x, 10), np.round(y, 10)):
        grid[yi[yv], xi[xv]] = value
    return grid


def make_regions(x: np.ndarray, y: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "whole": np.ones_like(x, dtype=bool),
        "left_precrack_band": (x <= 0.50) & (np.abs(y - 0.50) <= 0.014),
        "tip_column": (x >= 0.49) & (x <= 0.53) & (np.abs(y - 0.50) <= 0.08),
        "right_process_zone": (x >= 0.50) & (np.abs(y - 0.50) <= 0.20),
    }


def load_fields() -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray, dict, dict, dict]:
    index = pd.read_csv(FEM_INDEX)
    index_by_state = {r.state_label: i for i, r in index.iterrows()}

    fem: dict[str, dict[str, np.ndarray]] = {}
    pidl: dict[str, dict[str, np.ndarray]] = {}

    with h5py.File(FEM_MAT, "r") as h5:
        x = np.asarray(h5["element_centroids"])[0].astype(float)
        y = np.asarray(h5["element_centroids"])[1].astype(float)
        area = np.asarray(h5["element_area"]).squeeze().astype(float)
        fem_xy = np.column_stack([x, y])

        first = np.load(PIDL_FIELDS / STATE_TO_PIDL["c1_peak"])
        pidl_xy = np.column_stack([first["elem_x"] + 0.5, first["elem_y"] + 0.5])
        nearest = cKDTree(fem_xy).query(pidl_xy)[1]
        pidl_weights = first["area_elem"].astype(float)

        for state, filename in STATE_TO_PIDL.items():
            state_i = index_by_state[state]
            z = np.load(PIDL_FIELDS / filename)

            fem_raw = squeeze_state_field(h5, "psi_plus_elem", state_i)
            fem_active = squeeze_state_field(h5, "g_psi_plus_elem", state_i)
            fem_factive = squeeze_state_field(h5, "f_g_psi_plus_elem", state_i)
            fem_g = squeeze_state_field(h5, "g_stiffness_elem", state_i)
            fem_f = squeeze_state_field(h5, "f_fatigue_elem", state_i)

            pidl_raw = aggregate_pidl(z, "psi_raw_elem", nearest, pidl_weights, len(x))
            pidl_active = aggregate_pidl(z, "psi_active_elem", nearest, pidl_weights, len(x))
            pidl_f = aggregate_pidl(z, "f_fatigue_elem", nearest, pidl_weights, len(x))
            pidl_g = aggregate_pidl(z, "g_alpha_elem", nearest, pidl_weights, len(x))
            pidl_factive = pidl_f * pidl_active

            fem[state] = {
                "raw_driver": fem_raw,
                "active_driver": fem_active,
                "fatigue_effective_driver": fem_factive,
                "g_direct": fem_g,
                "g_from_driver_ratio": ratio(fem_active, fem_raw),
                "f_direct": fem_f,
                "f_from_driver_ratio": ratio(fem_factive, fem_active),
                "alpha_bar": squeeze_state_field(h5, "alpha_bar_elem", state_i),
                "damage": squeeze_state_field(h5, "d_elem", state_i),
            }
            pidl[state] = {
                "raw_driver": pidl_raw,
                "active_driver": pidl_active,
                "fatigue_effective_driver": pidl_factive,
                "g_direct": pidl_g,
                "g_from_driver_ratio": ratio(pidl_active, pidl_raw),
                "f_direct": pidl_f,
                "f_from_driver_ratio": ratio(pidl_factive, pidl_active),
                "alpha_bar": aggregate_pidl(z, "alpha_bar_elem", nearest, pidl_weights, len(x)),
                "damage": aggregate_pidl(z, "alpha_elem", nearest, pidl_weights, len(x)),
            }

    return index, x, y, area, make_regions(x, y), fem, pidl


def write_tables(
    index: pd.DataFrame,
    area: np.ndarray,
    regions: dict[str, np.ndarray],
    fem: dict[str, dict[str, np.ndarray]],
    pidl: dict[str, dict[str, np.ndarray]],
) -> None:
    meta = index.set_index("state_label").to_dict("index")
    rows = []
    for state in TEMPORAL_STATES:
        for q in QUANTITIES:
            for region, mask in regions.items():
                fs = weighted_stats(fem[state][q.key], area, mask)
                ps = weighted_stats(pidl[state][q.key], area, mask)
                for stat, fem_v in fs.items():
                    pidl_v = ps[stat]
                    rows.append({
                        "state": state,
                        "cycle": int(meta[state]["cycle"]),
                        "step": int(meta[state]["step"]),
                        "load_factor": float(meta[state]["load_factor"]),
                        "region": region,
                        "quantity": q.key,
                        "quantity_label": q.label,
                        "quantity_kind": q.kind,
                        "stat": stat,
                        "fem": fem_v,
                        "pidl": pidl_v,
                        "pidl_minus_fem": pidl_v - fem_v,
                        "pidl_over_fem": pidl_v / fem_v if abs(fem_v) > 1e-30 else np.nan,
                    })
    pd.DataFrame(rows).to_csv(TAB / "same_driver_same_fields_reductions.csv", index=False)

    delta_rows = []
    for prev, cur in zip(TEMPORAL_STATES[:-1], TEMPORAL_STATES[1:]):
        for solver, fields in [("FEM", fem), ("PIDL", pidl)]:
            delta_ab = fields[cur]["alpha_bar"] - fields[prev]["alpha_bar"]
            for driver in ["raw_driver", "active_driver", "fatigue_effective_driver"]:
                for region, mask in regions.items():
                    ss = weighted_stats(delta_ab, area, mask)
                    ds = weighted_stats(fields[cur][driver], area, mask)
                    delta_rows.append({
                        "solver": solver,
                        "from_state": prev,
                        "to_state": cur,
                        "to_cycle": int(meta[cur]["cycle"]),
                        "to_step": int(meta[cur]["step"]),
                        "to_load_factor": float(meta[cur]["load_factor"]),
                        "region": region,
                        "driver": driver,
                        "driver_area_mean": ds["area_mean"],
                        "driver_integral": ds["integral"],
                        "delta_alpha_bar_area_mean": ss["area_mean"],
                        "delta_alpha_bar_integral": ss["integral"],
                        "corr_driver_delta_alpha_bar": corr(fields[cur][driver], delta_ab, mask),
                    })
    pd.DataFrame(delta_rows).to_csv(TAB / "same_driver_same_fields_delta_alpha.csv", index=False)


def plot_area_means() -> None:
    df = pd.read_csv(TAB / "same_driver_same_fields_reductions.csv")
    sub = df[
        df["stat"].eq("area_mean")
        & df["quantity"].isin(["raw_driver", "active_driver", "fatigue_effective_driver"])
        & df["region"].isin(["left_precrack_band", "tip_column", "right_process_zone"])
        & df["state"].str.contains("peak")
    ].copy()
    quantities = ["raw_driver", "active_driver", "fatigue_effective_driver"]
    regions = ["left_precrack_band", "tip_column", "right_process_zone"]
    fig, axes = plt.subplots(len(regions), len(quantities), figsize=(13.5, 8.5), constrained_layout=True)
    for r, region in enumerate(regions):
        for c, quantity in enumerate(quantities):
            ax = axes[r, c]
            s = sub[sub["region"].eq(region) & sub["quantity"].eq(quantity)]
            ax.plot(s["cycle"], s["fem"], "o-", lw=1.5, label="FEM")
            ax.plot(s["cycle"], s["pidl"], "s-", lw=1.5, label="PIDL")
            ax.set_title(f"{region}\n{quantity}")
            ax.set_yscale("symlog", linthresh=1e-8)
            ax.grid(alpha=0.25)
            if r == len(regions) - 1:
                ax.set_xlabel("cycle")
            if c == 0:
                ax.set_ylabel("area mean")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Same driver definitions on the same mapped peak states")
    for ext in ["png", "pdf"]:
        fig.savefig(FIG / f"same_driver_same_fields_area_means.{ext}", dpi=220)
    plt.close(fig)


def plot_effective_degradation() -> None:
    df = pd.read_csv(TAB / "same_driver_same_fields_reductions.csv")
    sub = df[
        df["stat"].eq("area_mean")
        & df["quantity"].isin(["g_direct", "g_from_driver_ratio", "f_direct", "f_from_driver_ratio"])
        & df["region"].isin(["left_precrack_band", "tip_column", "right_process_zone"])
        & df["state"].str.contains("peak")
    ].copy()
    quantities = ["g_direct", "g_from_driver_ratio", "f_direct", "f_from_driver_ratio"]
    regions = ["left_precrack_band", "tip_column", "right_process_zone"]
    fig, axes = plt.subplots(len(regions), len(quantities), figsize=(15, 8.5), constrained_layout=True)
    for r, region in enumerate(regions):
        for c, quantity in enumerate(quantities):
            ax = axes[r, c]
            s = sub[sub["region"].eq(region) & sub["quantity"].eq(quantity)]
            ax.plot(s["cycle"], s["fem"], "o-", lw=1.5, label="FEM")
            ax.plot(s["cycle"], s["pidl"], "s-", lw=1.5, label="PIDL")
            ax.set_ylim(-0.03, 1.05)
            ax.set_title(f"{region}\n{quantity}")
            ax.grid(alpha=0.25)
            if r == len(regions) - 1:
                ax.set_xlabel("cycle")
            if c == 0:
                ax.set_ylabel("area mean")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Degradation factors and driver-ratio closure on mapped peak states")
    for ext in ["png", "pdf"]:
        fig.savefig(FIG / f"same_driver_same_fields_effective_degradation.{ext}", dpi=220)
    plt.close(fig)


def plot_delta_alpha() -> None:
    df = pd.read_csv(TAB / "same_driver_same_fields_delta_alpha.csv")
    sub = df[
        df["driver"].eq("active_driver")
        & df["region"].isin(["left_precrack_band", "tip_column", "right_process_zone"])
        & df["to_state"].str.contains("peak")
    ].copy()
    regions = ["left_precrack_band", "tip_column", "right_process_zone"]
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.8), constrained_layout=True)
    for ax, region in zip(axes, regions):
        s = sub[sub["region"].eq(region)]
        for solver, marker in [("FEM", "o"), ("PIDL", "s")]:
            d = s[s["solver"].eq(solver)]
            ax.plot(d["to_cycle"], d["delta_alpha_bar_area_mean"], marker + "-", lw=1.5, label=solver)
        ax.set_title(region)
        ax.set_yscale("symlog", linthresh=1e-8)
        ax.set_xlabel("to cycle")
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("area mean Delta alpha_bar")
    axes[0].legend(fontsize=8)
    fig.suptitle("History increments between mapped states")
    for ext in ["png", "pdf"]:
        fig.savefig(FIG / f"same_driver_same_fields_delta_alpha.{ext}", dpi=220)
    plt.close(fig)


def plot_residual_fields(
    x: np.ndarray,
    y: np.ndarray,
    fem: dict[str, dict[str, np.ndarray]],
    pidl: dict[str, dict[str, np.ndarray]],
) -> None:
    quantities = ["raw_driver", "active_driver", "fatigue_effective_driver"]
    labels = ["raw psi+", "g psi+", "f g psi+"]
    fig, axes = plt.subplots(len(PEAK_FIELD_STATES), len(quantities), figsize=(12, 8.5), constrained_layout=True)
    for c, quantity in enumerate(quantities):
        all_diff = []
        for state in PEAK_FIELD_STATES:
            diff = pidl[state][quantity] - fem[state][quantity]
            all_diff.append(diff[np.isfinite(diff)])
        joined = np.concatenate(all_diff)
        vmax = np.percentile(np.abs(joined), 99.5) if joined.size else 1.0
        vmax = max(vmax, 1e-12)
        for r, state in enumerate(PEAK_FIELD_STATES):
            ax = axes[r, c]
            diff_grid = grid_image(pidl[state][quantity] - fem[state][quantity], x, y)
            im = ax.imshow(
                diff_grid,
                origin="lower",
                extent=[x.min(), x.max(), y.min(), y.max()],
                cmap="RdBu_r",
                vmin=-vmax,
                vmax=vmax,
                interpolation="nearest",
                aspect="auto",
            )
            ax.set_title(f"{state}: PIDL - FEM\n{labels[c]}")
            ax.set_xlabel("x")
            if c == 0:
                ax.set_ylabel("y")
            fig.colorbar(im, ax=ax, shrink=0.75)
    fig.suptitle("Residual fields for identical driver definitions on common FEM grid")
    for ext in ["png", "pdf"]:
        fig.savefig(FIG / f"same_driver_same_fields_residual_fields.{ext}", dpi=220)
    plt.close(fig)


def write_report() -> None:
    red = pd.read_csv(TAB / "same_driver_same_fields_reductions.csv")
    delta = pd.read_csv(TAB / "same_driver_same_fields_delta_alpha.csv")

    key = red[
        red["stat"].eq("area_mean")
        & red["state"].isin(["c1_peak", "c20_peak", "c40_peak", "c69_peak"])
        & red["region"].eq("left_precrack_band")
        & red["quantity"].isin(["raw_driver", "active_driver", "fatigue_effective_driver", "g_direct", "f_direct"])
    ][["state", "quantity", "fem", "pidl", "pidl_over_fem"]]

    tip = red[
        red["stat"].eq("area_mean")
        & red["state"].isin(["c1_peak", "c20_peak", "c40_peak", "c69_peak"])
        & red["region"].eq("tip_column")
        & red["quantity"].isin(["raw_driver", "active_driver", "fatigue_effective_driver", "g_direct", "f_direct"])
    ][["state", "quantity", "fem", "pidl", "pidl_over_fem"]]

    dkey = delta[
        delta["to_state"].isin(["c1_peak", "c20_peak", "c40_peak", "c69_peak"])
        & delta["region"].isin(["left_precrack_band", "tip_column"])
        & delta["driver"].eq("active_driver")
    ][[
        "solver",
        "from_state",
        "to_state",
        "region",
        "driver_area_mean",
        "delta_alpha_bar_area_mean",
        "corr_driver_delta_alpha_bar",
    ]]

    report = OUT / "README_same_driver_same_fields_20260609.md"
    report.write_text(
        "# Same Driver Same Fields Audit - 2026-06-09\n\n"
        "## Purpose\n\n"
        "Compare FEM and PIDL fatigue-history driver candidates on the same mapped "
        "states and common FEM element grid. PIDL triangles are area-averaged onto "
        "the FEM quadrilateral cells before reduction.\n\n"
        "## Driver Definitions\n\n"
        "- `raw_driver`: undegraded tensile energy `psi+`.\n"
        "- `active_driver`: degraded tensile energy `g(alpha) * psi+`.\n"
        "- `fatigue_effective_driver`: `f(alpha_bar) * g(alpha) * psi+`.\n"
        "- `g_from_driver_ratio`: closure check `(g*psi+)/psi+`.\n"
        "- `f_from_driver_ratio`: closure check `(f*g*psi+)/(g*psi+)`.\n\n"
        "FEM's actual fatigue update is Gauss-point and substep based, so the "
        "element-level fields here are post-hoc comparable reductions, not a "
        "replacement for the internal GP update trace.\n\n"
        "## Left Precrack Band Key Rows\n\n"
        + key.to_markdown(index=False)
        + "\n\n## Tip Column Key Rows\n\n"
        + tip.to_markdown(index=False)
        + "\n\n## Active Driver vs Delta Alpha-Bar\n\n"
        + dkey.to_markdown(index=False)
        + "\n\n## Outputs\n\n"
        "- `tables/same_driver_same_fields_reductions.csv`\n"
        "- `tables/same_driver_same_fields_delta_alpha.csv`\n"
        "- `figures/same_driver_same_fields_area_means.png/pdf`\n"
        "- `figures/same_driver_same_fields_effective_degradation.png/pdf`\n"
        "- `figures/same_driver_same_fields_delta_alpha.png/pdf`\n"
        "- `figures/same_driver_same_fields_residual_fields.png/pdf`\n",
        encoding="utf-8",
    )


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    index, x, y, area, regions, fem, pidl = load_fields()
    write_tables(index, area, regions, fem, pidl)
    plot_area_means()
    plot_effective_degradation()
    plot_delta_alpha()
    plot_residual_fields(x, y, fem, pidl)
    write_report()
    print(f"wrote {TAB / 'same_driver_same_fields_reductions.csv'}")
    print(f"wrote {TAB / 'same_driver_same_fields_delta_alpha.csv'}")
    print(f"wrote {OUT / 'README_same_driver_same_fields_20260609.md'}")


if __name__ == "__main__":
    main()
