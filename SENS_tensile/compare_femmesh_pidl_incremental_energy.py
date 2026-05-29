#!/usr/bin/env python3
"""Compare FEM-mesh PIDL and soft-hist0 FEM energy trajectories.

Absolute damage energy includes the diffuse pre-crack contribution, so this
script reports both absolute terms and cycle-1-referenced increments.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
DEFAULT_FEM = Path(
    "/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/"
    "PIDL result/_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28/"
    "reverseBC_u12_diffuse_precrack_soft_hist0_cyclewise_mechanism_metrics.csv"
)
DEFAULT_PIDL = (
    HERE.parent
    / "_analysis_fem_mechanism_20260528"
    / "femmesh_pidl_energy_terms_c1_c69"
    / "element_diagnostics_summary.csv"
)
DEFAULT_OUT = (
    HERE.parent
    / "_analysis_fem_mechanism_20260528"
    / "femmesh_pidl_vs_soft_hist0_incremental_energy_c1_ref.csv"
)
DEFAULT_FIG = (
    HERE.parent
    / "_analysis_fem_mechanism_20260528"
    / "figures"
    / "femmesh_pidl_vs_soft_hist0_incremental_energy.png"
)


def safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    out = num / den.replace(0.0, np.nan)
    return out.replace([np.inf, -np.inf], np.nan)


def load_compare(fem_csv: Path, pidl_csv: Path) -> pd.DataFrame:
    fem = pd.read_csv(fem_csv)[["cycle", "E_el", "E_d", "total_energy"]].rename(
        columns={
            "E_el": "fem_E_el",
            "E_d": "fem_E_d",
            "total_energy": "fem_total_energy",
        }
    )
    pidl = pd.read_csv(pidl_csv)[
        ["cycle", "E_el", "E_d", "E_hist", "E_el_outside_precrack", "E_d_outside_precrack"]
    ].rename(
        columns={
            "E_el": "pidl_E_el",
            "E_d": "pidl_E_d",
            "E_hist": "pidl_E_hist",
            "E_el_outside_precrack": "pidl_E_el_outside_precrack",
            "E_d_outside_precrack": "pidl_E_d_outside_precrack",
        }
    )
    df = fem.merge(pidl, on="cycle", how="inner")
    df["pidl_total_energy"] = df["pidl_E_el"] + df["pidl_E_d"] + df["pidl_E_hist"]

    for col in [
        "fem_E_el",
        "fem_E_d",
        "fem_total_energy",
        "pidl_E_el",
        "pidl_E_d",
        "pidl_E_hist",
        "pidl_total_energy",
        "pidl_E_el_outside_precrack",
        "pidl_E_d_outside_precrack",
    ]:
        df[f"delta_{col}_from_c1"] = df[col] - float(df[col].iloc[0])

    df["ratio_abs_E_d_pidl_over_fem"] = safe_ratio(df["pidl_E_d"], df["fem_E_d"])
    df["ratio_delta_E_d_pidl_over_fem"] = safe_ratio(
        df["delta_pidl_E_d_from_c1"], df["delta_fem_E_d_from_c1"]
    )
    df["ratio_delta_E_d_outside_precrack_pidl_over_fem"] = safe_ratio(
        df["delta_pidl_E_d_outside_precrack_from_c1"], df["delta_fem_E_d_from_c1"]
    )
    return df


def plot(df: pd.DataFrame, fig_path: Path) -> None:
    palette = {
        "fem": "#0072B2",
        "pidl": "#D55E00",
        "pidl_out": "#009E73",
        "ratio": "#CC79A7",
    }
    cycle = df["cycle"]
    fig, axes = plt.subplots(2, 2, figsize=(10.8, 7.2), constrained_layout=True)

    ax = axes[0, 0]
    ax.plot(cycle, df["fem_E_el"], color=palette["fem"], lw=1.7, label="FEM")
    ax.plot(cycle, df["pidl_E_el"], color=palette["pidl"], lw=1.7, label="PIDL FEM-mesh")
    ax.set_title("Elastic energy")
    ax.set_xlabel("cycle")
    ax.set_ylabel("E_el")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)

    ax = axes[0, 1]
    ax.plot(cycle, df["fem_E_d"], color=palette["fem"], lw=1.7, label="FEM total")
    ax.plot(cycle, df["pidl_E_d"], color=palette["pidl"], lw=1.7, label="PIDL total")
    ax.plot(cycle, df["pidl_E_d_outside_precrack"], color=palette["pidl_out"], lw=1.4,
            ls="--", label="PIDL outside pre-crack")
    ax.set_title("Absolute damage energy")
    ax.set_xlabel("cycle")
    ax.set_ylabel("E_d")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)

    ax = axes[1, 0]
    ax.plot(cycle, df["delta_fem_E_d_from_c1"], color=palette["fem"], lw=1.7,
            label="FEM total")
    ax.plot(cycle, df["delta_pidl_E_d_from_c1"], color=palette["pidl"], lw=1.7,
            label="PIDL total")
    ax.plot(cycle, df["delta_pidl_E_d_outside_precrack_from_c1"],
            color=palette["pidl_out"], lw=1.4, ls="--", label="PIDL outside pre-crack")
    ax.set_title("Damage-energy growth from c1")
    ax.set_xlabel("cycle")
    ax.set_ylabel("Delta E_d")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)

    ax = axes[1, 1]
    ax.plot(cycle, df["ratio_abs_E_d_pidl_over_fem"], color=palette["pidl"], lw=1.4,
            label="absolute")
    ax.plot(cycle, df["ratio_delta_E_d_pidl_over_fem"], color=palette["ratio"], lw=1.6,
            label="Delta total")
    ax.plot(cycle, df["ratio_delta_E_d_outside_precrack_pidl_over_fem"],
            color=palette["pidl_out"], lw=1.4, ls="--", label="Delta outside")
    ax.axhline(1.0, color="0.25", lw=0.9, ls=":")
    ax.set_title("PIDL / FEM damage-energy ratio")
    ax.set_xlabel("cycle")
    ax.set_ylabel("ratio")
    ax.set_ylim(bottom=0)
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)

    fig.suptitle("FEM-mesh PIDL vs soft-hist0 FEM: absolute and c1-referenced energies")
    fig_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_path, dpi=220)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fem-csv", type=Path, default=DEFAULT_FEM)
    parser.add_argument("--pidl-csv", type=Path, default=DEFAULT_PIDL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--fig", type=Path, default=DEFAULT_FIG)
    args = parser.parse_args()

    df = load_compare(args.fem_csv, args.pidl_csv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    plot(df, args.fig)

    selected = df[df["cycle"].isin([1, 20, 40, 69])][[
        "cycle",
        "fem_E_d",
        "pidl_E_d",
        "delta_fem_E_d_from_c1",
        "delta_pidl_E_d_from_c1",
        "ratio_delta_E_d_pidl_over_fem",
        "ratio_delta_E_d_outside_precrack_pidl_over_fem",
    ]]
    print(selected.to_string(index=False))
    print(f"Wrote {args.out}")
    print(f"Wrote {args.fig}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
