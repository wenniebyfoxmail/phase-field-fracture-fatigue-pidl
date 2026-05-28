#!/usr/bin/env python3
"""Compare cyclewise FEM and PIDL mechanism metrics.

This script keeps definition traps visible: FEM monitor max is retained
separately from FEM element-field max, and PIDL scalar diagnostics are read from
post-hoc element-energy recomputation rather than inferred from plots.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def load_pidl_series(archive: Path, pidl_diag_csv: Path) -> pd.DataFrame:
    best = archive / "best_models"
    diag = pd.read_csv(pidl_diag_csv)
    diag = diag.rename(columns={
        "alpha_max": "pidl_alpha_max",
        "hist_max": "pidl_hist_max",
        "hist_mean": "pidl_hist_mean",
        "f_min": "pidl_f_min",
        "psi_max": "pidl_psi_max",
        "E_el": "pidl_E_el",
        "E_d": "pidl_E_d",
        "E_hist": "pidl_E_hist",
    })

    cycles = diag["cycle"].astype(int).to_numpy()
    out = diag[[
        "cycle", "pidl_E_el", "pidl_E_d", "pidl_E_hist", "pidl_alpha_max",
        "pidl_hist_max", "pidl_hist_mean", "pidl_f_min", "pidl_psi_max",
    ]].copy()

    optional = {
        "pidl_Kt": best / "Kt_vs_cycle.npy",
        "pidl_x_tip": best / "x_tip_vs_cycle.npy",
    }
    for col, path in optional.items():
        if path.exists():
            arr = np.load(path, allow_pickle=True)
            out[col] = [float(arr[c]) if c < len(arr) else np.nan for c in cycles]

    ab_path = best / "alpha_bar_vs_cycle.npy"
    if ab_path.exists():
        ab = np.load(ab_path, allow_pickle=True)
        out["pidl_alpha_bar_saved_max"] = [float(ab[c, 0]) if c < len(ab) else np.nan for c in cycles]
        out["pidl_alpha_bar_saved_mean"] = [float(ab[c, 1]) if c < len(ab) else np.nan for c in cycles]
        out["pidl_saved_f_min"] = [float(ab[c, 2]) if c < len(ab) else np.nan for c in cycles]

    return out


def safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    return num / den.replace(0.0, np.nan)


def build_comparison(fem_csv: Path, archive: Path, pidl_diag_csv: Path) -> pd.DataFrame:
    fem = pd.read_csv(fem_csv).rename(columns={
        "E_el": "fem_E_el",
        "E_d": "fem_E_d",
        "total_energy": "fem_total_energy",
        "d_max": "fem_d_max",
        "d_mean": "fem_d_mean",
        "alpha_bar_elem_max": "fem_alpha_bar_elem_max",
        "alpha_bar_elem_mean": "fem_alpha_bar_elem_mean",
        "alpha_bar_monitor_max": "fem_alpha_bar_monitor_max",
        "f_fatigue_min": "fem_f_min",
        "psi_plus_elem_max": "fem_psi_max",
        "Kt_proxy": "fem_Kt_proxy",
        "x_tip_d095": "fem_x_tip_d095",
        "right_boundary_d095_count": "fem_right_boundary_d095_count",
    })
    pidl = load_pidl_series(archive, pidl_diag_csv)
    merged = fem.merge(pidl, on="cycle", how="inner")

    merged["ratio_E_el_pidl_over_fem"] = safe_ratio(merged["pidl_E_el"], merged["fem_E_el"])
    merged["ratio_E_d_pidl_over_fem"] = safe_ratio(merged["pidl_E_d"], merged["fem_E_d"])
    merged["ratio_hist_max_pidl_over_fem_elem"] = safe_ratio(
        merged["pidl_hist_max"], merged["fem_alpha_bar_elem_max"],
    )
    merged["ratio_hist_mean_pidl_over_fem_elem"] = safe_ratio(
        merged["pidl_hist_mean"], merged["fem_alpha_bar_elem_mean"],
    )
    merged["ratio_f_min_pidl_over_fem"] = safe_ratio(merged["pidl_f_min"], merged["fem_f_min"])
    if "pidl_x_tip" in merged:
        merged["delta_x_tip_pidl_minus_fem_d095"] = merged["pidl_x_tip"] - merged["fem_x_tip_d095"]
    if "pidl_Kt" in merged:
        merged["ratio_Kt_pidl_over_fem_proxy"] = safe_ratio(merged["pidl_Kt"], merged["fem_Kt_proxy"])
    return merged


def plot_comparison(df: pd.DataFrame, out_png: Path, out_pdf: Path | None) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(11, 10), constrained_layout=True)
    cycle = df["cycle"]

    ax = axes[0, 0]
    ax.plot(cycle, df["fem_E_el"], label="FEM E_el", lw=1.8)
    ax.plot(cycle, df["pidl_E_el"], label="PIDL E_el", lw=1.8)
    ax.plot(cycle, df["fem_E_d"], label="FEM E_d", lw=1.8)
    ax.plot(cycle, df["pidl_E_d"], label="PIDL E_d", lw=1.8)
    ax.set_title("Integrated Energies")
    ax.set_xlabel("cycle")
    ax.set_ylabel("energy")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    ax = axes[0, 1]
    ax.semilogy(cycle, df["ratio_E_el_pidl_over_fem"], label="E_el ratio")
    ax.semilogy(cycle, df["ratio_E_d_pidl_over_fem"], label="E_d ratio")
    ax.axhline(1.0, color="0.3", lw=1, ls="--")
    ax.set_title("PIDL / FEM Energy Ratio")
    ax.set_xlabel("cycle")
    ax.set_ylabel("ratio")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    ax = axes[1, 0]
    ax.semilogy(cycle, df["fem_alpha_bar_elem_max"], label="FEM history elem max")
    ax.semilogy(cycle, df["pidl_hist_max"], label="PIDL history max")
    ax.semilogy(cycle, df["fem_alpha_bar_elem_mean"], label="FEM history mean", ls="--")
    ax.semilogy(cycle, df["pidl_hist_mean"], label="PIDL history mean", ls="--")
    ax.set_title("Fatigue-History Level")
    ax.set_xlabel("cycle")
    ax.set_ylabel("history")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    ax = axes[1, 1]
    ax.semilogy(cycle, df["fem_f_min"], label="FEM min f")
    ax.semilogy(cycle, df["pidl_f_min"], label="PIDL min f")
    ax.set_title("Local Fatigue Degradation")
    ax.set_xlabel("cycle")
    ax.set_ylabel("min f")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    ax = axes[2, 0]
    ax.plot(cycle, df["fem_x_tip_d095"], label="FEM x_tip d>=0.95")
    if "pidl_x_tip" in df:
        ax.plot(cycle, df["pidl_x_tip"], label="PIDL x_tip saved")
    ax.set_title("Crack-Tip Position")
    ax.set_xlabel("cycle")
    ax.set_ylabel("x")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    ax = axes[2, 1]
    ax.semilogy(cycle, df["fem_Kt_proxy"], label="FEM Kt proxy")
    if "pidl_Kt" in df:
        ax.semilogy(cycle, df["pidl_Kt"], label="PIDL Kt")
    ax.set_title("Kt Proxy, Definition-Sensitive")
    ax.set_xlabel("cycle")
    ax.set_ylabel("Kt proxy")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)
    if out_pdf is not None:
        fig.savefig(out_pdf)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fem-csv", type=Path, required=True)
    parser.add_argument("--pidl-archive", type=Path, required=True)
    parser.add_argument("--pidl-diag-csv", type=Path, required=True)
    parser.add_argument("--out-csv", type=Path, required=True)
    parser.add_argument("--out-png", type=Path, required=True)
    parser.add_argument("--out-pdf", type=Path, default=None)
    args = parser.parse_args()

    df = build_comparison(args.fem_csv, args.pidl_archive, args.pidl_diag_csv)
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out_csv, index=False)
    plot_comparison(df, args.out_png, args.out_pdf)
    print(f"Wrote {args.out_csv}")
    print(f"Wrote {args.out_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
