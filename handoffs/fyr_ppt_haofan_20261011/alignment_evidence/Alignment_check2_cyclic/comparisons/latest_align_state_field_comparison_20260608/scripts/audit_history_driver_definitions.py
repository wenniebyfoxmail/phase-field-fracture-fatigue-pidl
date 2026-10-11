#!/usr/bin/env python3
"""Audit FEM/PIDL fatigue-history driver definitions on aligned fields."""

from __future__ import annotations

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
    ROOT / "FEM cyclic 012/cases/standard/raw_data/state_field_exports"
    / "latest_align_soft_hist0_state_field_export_20260608"
)
FEM_MAT = FEM_DIR / "latest_align_soft_hist0_state_fields.mat"
FEM_INDEX = FEM_DIR / "latest_align_soft_hist0_state_index.csv"
PIDL_FIELDS = (
    ROOT / "PIDL cyclic 012/cases/stateTiming_substeps025_untilFrac_Nphys120_Nstep600"
    / "analysis/mapped_state_fields_20260608/fields"
)

STATE_TO_PIDL = {
    "state0_initial_unloaded_prehistory": "pidl_state0_initial_unloaded_prehistory.npz",
    "c1_peak": "fem_c0001_peak_pidl_step_0003.npz",
    "c20_peak": "fem_c0020_peak_pidl_step_0098.npz",
    "c40_peak": "fem_c0040_peak_pidl_step_0198.npz",
    "c60_peak": "fem_c0060_peak_pidl_step_0298.npz",
    "c69_peak": "fem_c0069_peak_pidl_step_0343.npz",
}
PEAK_STATES = ["c1_peak", "c20_peak", "c40_peak", "c69_peak"]
INTERVALS = [
    ("state0_initial_unloaded_prehistory", "c1_peak"),
    ("c1_peak", "c20_peak"),
    ("c20_peak", "c40_peak"),
    ("c40_peak", "c60_peak"),
    ("c60_peak", "c69_peak"),
]


def stats(values: np.ndarray, area: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    m = mask & np.isfinite(values)
    if not np.any(m):
        return {"mean": np.nan, "area_mean": np.nan, "max": np.nan, "p99": np.nan, "integral": np.nan}
    v = values[m]
    a = area[m]
    return {
        "mean": float(np.mean(v)),
        "area_mean": float(np.sum(v * a) / np.sum(a)),
        "max": float(np.max(v)),
        "p99": float(np.percentile(v, 99.0)),
        "integral": float(np.sum(v * a)),
    }


def corr(a: np.ndarray, b: np.ndarray, mask: np.ndarray) -> float:
    m = mask & np.isfinite(a) & np.isfinite(b)
    if np.sum(m) < 3 or np.std(a[m]) == 0 or np.std(b[m]) == 0:
        return np.nan
    return float(np.corrcoef(a[m], b[m])[0, 1])


def aggregate_pidl(npz: np.lib.npyio.NpzFile, key: str, nearest: np.ndarray, weights: np.ndarray, n: int) -> np.ndarray:
    v = np.asarray(npz[key], dtype=float)
    num = np.bincount(nearest, weights=v * weights, minlength=n)
    den = np.bincount(nearest, weights=weights, minlength=n)
    out = np.full(n, np.nan)
    np.divide(num, den, out=out, where=den > 0)
    return out


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    fem_index = pd.read_csv(FEM_INDEX)
    state_i = {r.state_label: i for i, r in fem_index.iterrows()}

    with h5py.File(FEM_MAT, "r") as h5:
        x = np.asarray(h5["element_centroids"])[0].astype(float)
        y = np.asarray(h5["element_centroids"])[1].astype(float)
        area = np.asarray(h5["element_area"]).squeeze().astype(float)
        fem_xy = np.column_stack([x, y])
        first = np.load(PIDL_FIELDS / STATE_TO_PIDL["c1_peak"])
        pidl_xy = np.column_stack([first["elem_x"] + 0.5, first["elem_y"] + 0.5])
        nearest = cKDTree(fem_xy).query(pidl_xy)[1]
        pidl_weights = first["area_elem"].astype(float)

        regions = {
            "whole": np.ones_like(x, dtype=bool),
            "left_precrack_band": (x <= 0.50) & (np.abs(y - 0.50) <= 0.014),
            "tip_column": (x >= 0.49) & (x <= 0.53) & (np.abs(y - 0.50) <= 0.08),
            "right_process_zone": (x >= 0.50) & (np.abs(y - 0.50) <= 0.20),
        }

        fem_fields: dict[str, dict[str, np.ndarray]] = {}
        pidl_fields: dict[str, dict[str, np.ndarray]] = {}
        rows = []

        for state in STATE_TO_PIDL:
            i = state_i[state]
            z = np.load(PIDL_FIELDS / STATE_TO_PIDL[state])

            fem_raw = np.asarray(h5["fields/psi_plus_elem"])[i, 0].astype(float)
            fem_active = np.asarray(h5["fields/g_psi_plus_elem"])[i, 0].astype(float)
            fem_factive = np.asarray(h5["fields/f_g_psi_plus_elem"])[i, 0].astype(float)
            fem_ab = np.asarray(h5["fields/alpha_bar_elem"])[i, 0].astype(float)
            fem_f = np.asarray(h5["fields/f_fatigue_elem"])[i, 0].astype(float)

            pidl_raw = aggregate_pidl(z, "psi_raw_elem", nearest, pidl_weights, len(x))
            pidl_active = aggregate_pidl(z, "psi_active_elem", nearest, pidl_weights, len(x))
            pidl_f = aggregate_pidl(z, "f_fatigue_elem", nearest, pidl_weights, len(x))
            pidl_factive = pidl_f * pidl_active
            pidl_ab = aggregate_pidl(z, "alpha_bar_elem", nearest, pidl_weights, len(x))

            fem_fields[state] = {
                "raw": fem_raw,
                "active_g": fem_active,
                "fatigue_active": fem_factive,
                "alpha_bar": fem_ab,
                "f": fem_f,
            }
            pidl_fields[state] = {
                "raw": pidl_raw,
                "active_g": pidl_active,
                "fatigue_active": pidl_factive,
                "alpha_bar": pidl_ab,
                "f": pidl_f,
            }

            if state == "state0_initial_unloaded_prehistory":
                continue
            cycle = int(state.split("_")[0][1:])
            for driver in ["raw", "active_g", "fatigue_active"]:
                for region, mask in regions.items():
                    fs = stats(fem_fields[state][driver], area, mask)
                    ps = stats(pidl_fields[state][driver], area, mask)
                    for stat in fs:
                        fem_v = fs[stat]
                        pidl_v = ps[stat]
                        rows.append({
                            "state": state,
                            "cycle": cycle,
                            "region": region,
                            "driver": driver,
                            "stat": stat,
                            "fem": fem_v,
                            "pidl": pidl_v,
                            "pidl_minus_fem": pidl_v - fem_v,
                            "pidl_over_fem": pidl_v / fem_v if abs(fem_v) > 1e-30 else np.nan,
                        })

        pd.DataFrame(rows).to_csv(TAB / "history_driver_definition_reductions.csv", index=False)

        interval_rows = []
        for prev, cur in INTERVALS:
            cycle = int(cur.split("_")[0][1:])
            for solver, fields in [("FEM", fem_fields), ("PIDL", pidl_fields)]:
                delta_ab = fields[cur]["alpha_bar"] - fields[prev]["alpha_bar"]
                for driver in ["raw", "active_g", "fatigue_active"]:
                    drv = fields[cur][driver]
                    for region, mask in regions.items():
                        ss = stats(delta_ab, area, mask)
                        interval_rows.append({
                            "solver": solver,
                            "interval": f"{prev}->{cur}",
                            "cycle": cycle,
                            "region": region,
                            "driver": driver,
                            "driver_delta_alpha_bar_corr": corr(drv, delta_ab, mask),
                            "delta_alpha_bar_area_mean": ss["area_mean"],
                            "delta_alpha_bar_integral": ss["integral"],
                            "driver_area_mean": stats(drv, area, mask)["area_mean"],
                            "driver_integral": stats(drv, area, mask)["integral"],
                        })
        intervals = pd.DataFrame(interval_rows)
        intervals.to_csv(TAB / "history_driver_vs_delta_alpha_bar.csv", index=False)

    plot_reductions()
    plot_interval_correlations()
    write_report()


def plot_reductions() -> None:
    df = pd.read_csv(TAB / "history_driver_definition_reductions.csv")
    sub = df[
        df["stat"].eq("area_mean")
        & df["region"].isin(["left_precrack_band", "tip_column", "right_process_zone"])
    ].copy()
    drivers = ["raw", "active_g", "fatigue_active"]
    regions = ["left_precrack_band", "tip_column", "right_process_zone"]
    fig, axes = plt.subplots(len(regions), len(drivers), figsize=(13, 8.5), constrained_layout=True)
    for r, region in enumerate(regions):
        for c, driver in enumerate(drivers):
            ax = axes[r, c]
            d = sub[(sub["region"].eq(region)) & (sub["driver"].eq(driver))]
            ax.plot(d["cycle"], d["fem"], "o-", label="FEM", lw=1.5)
            ax.plot(d["cycle"], d["pidl"], "s-", label="PIDL", lw=1.5)
            ax.set_title(f"{region}\n{driver}")
            ax.set_yscale("symlog", linthresh=1e-8)
            ax.grid(alpha=0.25)
            if r == len(regions) - 1:
                ax.set_xlabel("cycle")
            if c == 0:
                ax.set_ylabel("area mean driver")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Candidate fatigue-history drivers by region")
    for ext in ["png", "pdf"]:
        fig.savefig(FIG / f"history_driver_definition_reductions.{ext}", dpi=220)
    plt.close(fig)


def plot_interval_correlations() -> None:
    df = pd.read_csv(TAB / "history_driver_vs_delta_alpha_bar.csv")
    sub = df[df["region"].isin(["left_precrack_band", "tip_column", "right_process_zone"])].copy()
    drivers = ["raw", "active_g", "fatigue_active"]
    regions = ["left_precrack_band", "tip_column", "right_process_zone"]
    fig, axes = plt.subplots(len(regions), len(drivers), figsize=(13, 8.5), constrained_layout=True)
    for r, region in enumerate(regions):
        for c, driver in enumerate(drivers):
            ax = axes[r, c]
            d = sub[(sub["region"].eq(region)) & (sub["driver"].eq(driver))]
            for solver, marker in [("FEM", "o"), ("PIDL", "s")]:
                s = d[d["solver"].eq(solver)]
                ax.plot(s["cycle"], s["driver_delta_alpha_bar_corr"], marker + "-", label=solver, lw=1.5)
            ax.axhline(0, color="0.4", lw=0.8)
            ax.set_ylim(-1.05, 1.05)
            ax.set_title(f"{region}\n{driver}")
            ax.grid(alpha=0.25)
            if r == len(regions) - 1:
                ax.set_xlabel("cycle")
            if c == 0:
                ax.set_ylabel("corr(driver, Delta alpha_bar)")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Driver colocation with fatigue-history increments")
    for ext in ["png", "pdf"]:
        fig.savefig(FIG / f"history_driver_delta_alpha_bar_correlations.{ext}", dpi=220)
    plt.close(fig)


def write_report() -> None:
    red = pd.read_csv(TAB / "history_driver_definition_reductions.csv")
    left = red[
        red["region"].eq("left_precrack_band")
        & red["stat"].eq("area_mean")
        & red["cycle"].isin([1, 20, 40, 69])
    ]
    pivot = left.pivot_table(index=["cycle", "driver"], values=["fem", "pidl", "pidl_over_fem"], aggfunc="first")
    corr_df = pd.read_csv(TAB / "history_driver_vs_delta_alpha_bar.csv")
    corr_left = corr_df[
        corr_df["region"].eq("left_precrack_band")
        & corr_df["cycle"].isin([1, 20, 40, 69])
    ][["solver", "cycle", "driver", "driver_delta_alpha_bar_corr", "delta_alpha_bar_area_mean", "driver_area_mean"]]

    report = [
        "# History Driver Definition Audit",
        "",
        "This audit compares candidate fatigue-history drivers on the latest aligned FEM/PIDL mapped states:",
        "",
        "- `raw`: undegraded tensile energy, FEM `psi_plus_elem`, PIDL `psi_raw_elem`.",
        "- `active_g`: stiffness-degraded tensile energy, FEM `g_psi_plus_elem`, PIDL `psi_active_elem`.",
        "- `fatigue_active`: `f * g * psi_plus`, FEM `f_g_psi_plus_elem`, PIDL `f_fatigue_elem * psi_active_elem`.",
        "",
        "The archived strict PIDL state-timing run used `history_driver_mode: active_degraded`, i.e. `active_g`.",
        "The FEM export stores all three candidates, but the GRIPHFiTH history update is driven inside the phase-field assembly rather than by the PIDL post-fit helper.",
        "",
        "## Left Precrack Band Area-Mean Drivers",
        "",
        pivot.reset_index().to_markdown(index=False),
        "",
        "## Driver vs Delta Alpha-Bar Correlation In Left Precrack Band",
        "",
        corr_left.to_markdown(index=False),
        "",
        "## Outputs",
        "",
        "- `tables/history_driver_definition_reductions.csv`",
        "- `tables/history_driver_vs_delta_alpha_bar.csv`",
        "- `figures/history_driver_definition_reductions.png`",
        "- `figures/history_driver_delta_alpha_bar_correlations.png`",
        "",
        "## Preliminary Interpretation",
        "",
        "If PIDL is compared to FEM using the current strict run, PIDL is closest to the `active_g` driver by construction. FEM has substantial raw and active driver in/near the retained precrack band after loading, so allowing history everywhere lets FEM accumulate fatigue there. A fatigue-only precrack mask is the clean next discriminator: keep the soft retained mechanical precrack, but freeze fatigue history in the old crack band.",
    ]
    (OUT / "README_history_driver_definition_audit.md").write_text("\n".join(report) + "\n")


if __name__ == "__main__":
    main()
