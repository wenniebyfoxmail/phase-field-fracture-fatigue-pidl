#!/usr/bin/env python3
"""Compare two cyclewise FEM mechanism exports.

The intended use is a FEM-to-FEM reference check before judging PIDL against a
new FEM payload. Inputs must be the scalar mechanism CSV files produced by the
FEM exporter with aligned column definitions.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    return num / den.replace(0.0, np.nan)


def _first_cycle(df: pd.DataFrame, mask: pd.Series) -> float:
    vals = df.loc[mask.fillna(False), "cycle"]
    if vals.empty:
        return np.nan
    return float(vals.iloc[0])


def build_comparison(old_csv: Path, fine_csv: Path) -> tuple[pd.DataFrame, dict[str, float]]:
    old = pd.read_csv(old_csv)
    fine = pd.read_csv(fine_csv)
    old = old.add_prefix("old_").rename(columns={"old_cycle": "cycle"})
    fine = fine.add_prefix("fine_").rename(columns={"fine_cycle": "cycle"})
    df = old.merge(fine, on="cycle", how="inner")

    for col in [
        "E_el",
        "E_d",
        "alpha_bar_elem_max",
        "alpha_bar_elem_mean",
        "alpha_bar_monitor_max",
        "f_fatigue_min",
        "psi_plus_elem_max",
        "Kt_proxy",
        "width_y_d050_near_tip",
    ]:
        df[f"ratio_fine_over_old_{col}"] = _safe_ratio(df[f"fine_{col}"], df[f"old_{col}"])

    df["old_E_d_increment_from_c1"] = df["old_E_d"] - df["old_E_d"].iloc[0]
    df["fine_E_d_increment_from_c1"] = df["fine_E_d"] - df["fine_E_d"].iloc[0]
    df["ratio_fine_over_old_E_d_increment"] = _safe_ratio(
        df["fine_E_d_increment_from_c1"],
        df["old_E_d_increment_from_c1"],
    )
    df["delta_x_tip_d095_fine_minus_old"] = df["fine_x_tip_d095"] - df["old_x_tip_d095"]
    df["delta_E_el_fine_minus_old"] = df["fine_E_el"] - df["old_E_el"]
    df["delta_E_d_fine_minus_old"] = df["fine_E_d"] - df["old_E_d"]

    summary = {
        "n_common_cycles": float(len(df)),
        "old_last_cycle": float(old["cycle"].max()),
        "fine_last_cycle": float(fine["cycle"].max()),
        "old_first_right_boundary_d095": _first_cycle(old.rename(columns=lambda c: c.removeprefix("old_")), old["old_right_boundary_d095_count"] > 0),
        "fine_first_right_boundary_d095": _first_cycle(fine.rename(columns=lambda c: c.removeprefix("fine_")), fine["fine_right_boundary_d095_count"] > 0),
        "old_first_x_tip_d095_ge_0p49": _first_cycle(old.rename(columns=lambda c: c.removeprefix("old_")), old["old_x_tip_d095"] >= 0.49),
        "fine_first_x_tip_d095_ge_0p49": _first_cycle(fine.rename(columns=lambda c: c.removeprefix("fine_")), fine["fine_x_tip_d095"] >= 0.49),
    }
    for col in [
        "ratio_fine_over_old_E_el",
        "ratio_fine_over_old_E_d",
        "ratio_fine_over_old_E_d_increment",
        "ratio_fine_over_old_alpha_bar_elem_max",
        "ratio_fine_over_old_alpha_bar_elem_mean",
        "ratio_fine_over_old_f_fatigue_min",
        "ratio_fine_over_old_psi_plus_elem_max",
        "ratio_fine_over_old_Kt_proxy",
    ]:
        useful = df.loc[df["cycle"] >= 10, col].replace([np.inf, -np.inf], np.nan).dropna()
        summary[f"median_c10_common_{col}"] = float(useful.median()) if not useful.empty else np.nan
    return df, summary


def plot_comparison(df: pd.DataFrame, out_png: Path, out_pdf: Path | None) -> None:
    palette = {
        "old": "#0072B2",
        "fine": "#D55E00",
        "ratio": "#009E73",
        "ref": "0.35",
    }
    fig, axes = plt.subplots(3, 2, figsize=(11, 10), constrained_layout=True)
    cycle = df["cycle"]

    ax = axes[0, 0]
    ax.plot(cycle, df["old_E_el"], color=palette["old"], lw=1.7, label="old FEM E_el")
    ax.plot(cycle, df["fine_E_el"], color=palette["fine"], lw=1.7, label="fine FEM E_el")
    ax.plot(cycle, df["old_E_d"], color=palette["old"], lw=1.7, ls="--", label="old FEM E_d")
    ax.plot(cycle, df["fine_E_d"], color=palette["fine"], lw=1.7, ls="--", label="fine FEM E_d")
    ax.set_title("Integrated Energies")
    ax.set_xlabel("cycle")
    ax.set_ylabel("energy")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[0, 1]
    ax.semilogy(cycle, df["ratio_fine_over_old_E_el"], color=palette["old"], lw=1.7, label="E_el fine/old")
    ax.semilogy(cycle, df["ratio_fine_over_old_E_d_increment"], color=palette["fine"], lw=1.7, label="incremental E_d fine/old")
    ax.axhline(1.0, color=palette["ref"], lw=1, ls=":")
    ax.set_title("Energy Ratios")
    ax.set_xlabel("cycle")
    ax.set_ylabel("ratio")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[1, 0]
    ax.semilogy(cycle, df["old_alpha_bar_elem_max"], color=palette["old"], lw=1.7, label="old hist max")
    ax.semilogy(cycle, df["fine_alpha_bar_elem_max"], color=palette["fine"], lw=1.7, label="fine hist max")
    ax.semilogy(cycle, df["old_alpha_bar_elem_mean"], color=palette["old"], lw=1.3, ls="--", label="old hist mean")
    ax.semilogy(cycle, df["fine_alpha_bar_elem_mean"], color=palette["fine"], lw=1.3, ls="--", label="fine hist mean")
    ax.set_title("Fatigue History")
    ax.set_xlabel("cycle")
    ax.set_ylabel("history")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[1, 1]
    ax.semilogy(cycle, df["old_f_fatigue_min"], color=palette["old"], lw=1.7, label="old min f")
    ax.semilogy(cycle, df["fine_f_fatigue_min"], color=palette["fine"], lw=1.7, label="fine min f")
    ax.set_title("Local Fatigue Degradation")
    ax.set_xlabel("cycle")
    ax.set_ylabel("min f")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[2, 0]
    ax.plot(cycle, df["old_x_tip_d095"], color=palette["old"], lw=1.7, label="old x_tip d>=0.95")
    ax.plot(cycle, df["fine_x_tip_d095"], color=palette["fine"], lw=1.7, label="fine x_tip d>=0.95")
    ax.set_title("Crack-Tip Position")
    ax.set_xlabel("cycle")
    ax.set_ylabel("x")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[2, 1]
    ax.semilogy(cycle, df["old_Kt_proxy"], color=palette["old"], lw=1.7, label="old Kt proxy")
    ax.semilogy(cycle, df["fine_Kt_proxy"], color=palette["fine"], lw=1.7, label="fine Kt proxy")
    ax.set_title("Kt Proxy")
    ax.set_xlabel("cycle")
    ax.set_ylabel("Kt proxy")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)
    if out_pdf is not None:
        fig.savefig(out_pdf)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-fem-csv", type=Path, required=True)
    parser.add_argument("--fine-fem-csv", type=Path, required=True)
    parser.add_argument("--out-csv", type=Path, required=True)
    parser.add_argument("--out-summary-csv", type=Path, required=True)
    parser.add_argument("--out-png", type=Path, required=True)
    parser.add_argument("--out-pdf", type=Path, default=None)
    args = parser.parse_args()

    df, summary = build_comparison(args.old_fem_csv, args.fine_fem_csv)
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out_csv, index=False)
    pd.DataFrame([summary]).to_csv(args.out_summary_csv, index=False)
    plot_comparison(df, args.out_png, args.out_pdf)
    print(f"Wrote {args.out_csv}")
    print(f"Wrote {args.out_summary_csv}")
    print(f"Wrote {args.out_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
