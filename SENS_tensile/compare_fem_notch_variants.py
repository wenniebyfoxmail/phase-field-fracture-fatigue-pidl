#!/usr/bin/env python3
"""Compare void-notch and diffuse-precrack FEM cyclewise exports."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SERIES = {
    "old_void": {"label": "old void FEM", "color": "#0072B2", "ls": "-"},
    "fine_void": {"label": "fine void FEM", "color": "#E69F00", "ls": "-"},
    "diffuse": {"label": "diffuse precrack FEM", "color": "#009E73", "ls": "-"},
}


def load_series(path: Path, prefix: str, x_shift: float = 0.0, y_shift: float = 0.0) -> pd.DataFrame:
    df = pd.read_csv(path)
    for col in [
        "x_max_d",
        "x_max_alpha_bar_elem",
        "x_min_f_fatigue_elem",
        "x_max_psi_plus_elem",
        "x_tip_d095",
        "x_tip_d090",
        "x_tip_d050",
    ]:
        if col in df:
            df[f"{col}_centered"] = df[col] + x_shift
    for col in [
        "y_max_d",
        "y_max_alpha_bar_elem",
        "y_min_f_fatigue_elem",
        "y_max_psi_plus_elem",
        "y_tip_d095",
        "y_tip_d090",
        "y_tip_d050",
    ]:
        if col in df:
            df[f"{col}_centered"] = df[col] + y_shift
    df = df.add_prefix(f"{prefix}_").rename(columns={f"{prefix}_cycle": "cycle"})
    df[f"{prefix}_E_d_increment_from_c1"] = df[f"{prefix}_E_d"] - df[f"{prefix}_E_d"].iloc[0]
    return df


def build_comparison(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    old = load_series(args.old_void_csv, "old_void")
    fine = load_series(args.fine_void_csv, "fine_void")
    diffuse = load_series(
        args.diffuse_csv,
        "diffuse",
        x_shift=args.diffuse_x_shift,
        y_shift=args.diffuse_y_shift,
    )
    df = old.merge(fine, on="cycle", how="inner").merge(diffuse, on="cycle", how="inner")

    rows: list[dict[str, float | str]] = []
    for prefix in SERIES:
        row: dict[str, float | str] = {
            "series": prefix,
            "n_common_cycles": float(len(df)),
            "last_common_cycle": float(df["cycle"].max()),
            "E_el_c1": float(df[f"{prefix}_E_el"].iloc[0]),
            "E_el_last": float(df[f"{prefix}_E_el"].iloc[-1]),
            "E_d_c1": float(df[f"{prefix}_E_d"].iloc[0]),
            "E_d_last": float(df[f"{prefix}_E_d"].iloc[-1]),
            "E_d_increment_last": float(df[f"{prefix}_E_d_increment_from_c1"].iloc[-1]),
            "hist_max_c10": _value_at(df, f"{prefix}_alpha_bar_elem_max", 10),
            "hist_max_c40": _value_at(df, f"{prefix}_alpha_bar_elem_max", 40),
            "hist_max_last": float(df[f"{prefix}_alpha_bar_elem_max"].iloc[-1]),
            "f_min_c10": _value_at(df, f"{prefix}_f_fatigue_min", 10),
            "f_min_c40": _value_at(df, f"{prefix}_f_fatigue_min", 40),
            "f_min_last": float(df[f"{prefix}_f_fatigue_min"].iloc[-1]),
            "psi_max_c40": _value_at(df, f"{prefix}_psi_plus_elem_max", 40),
            "psi_max_last": float(df[f"{prefix}_psi_plus_elem_max"].iloc[-1]),
            "Kt_c40": _value_at(df, f"{prefix}_Kt_proxy", 40),
            "Kt_last": float(df[f"{prefix}_Kt_proxy"].iloc[-1]),
        }
        xtip_col = f"{prefix}_x_tip_d095_centered" if prefix == "diffuse" else f"{prefix}_x_tip_d095"
        row["x_tip_d095_c40_centered"] = _value_at(df, xtip_col, 40)
        row["x_tip_d095_last_centered"] = float(df[xtip_col].iloc[-1])
        rows.append(row)
    summary = pd.DataFrame(rows)
    return df, summary


def _value_at(df: pd.DataFrame, col: str, cycle: int) -> float:
    row = df.loc[df["cycle"] == cycle, col]
    if row.empty:
        return np.nan
    return float(row.iloc[0])


def plot_comparison(df: pd.DataFrame, out_png: Path, out_pdf: Path | None) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(11, 10), constrained_layout=True)
    cycle = df["cycle"]

    ax = axes[0, 0]
    for prefix, meta in SERIES.items():
        ax.plot(cycle, df[f"{prefix}_E_el"], color=meta["color"], lw=1.7, label=meta["label"])
    ax.set_title("Elastic Energy")
    ax.set_xlabel("cycle")
    ax.set_ylabel("E_el")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[0, 1]
    for prefix, meta in SERIES.items():
        ax.plot(
            cycle,
            df[f"{prefix}_E_d_increment_from_c1"],
            color=meta["color"],
            lw=1.7,
            label=meta["label"],
        )
    ax.set_title("Incremental Damage Energy From c1")
    ax.set_xlabel("cycle")
    ax.set_ylabel("Delta E_d")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[1, 0]
    for prefix, meta in SERIES.items():
        ax.semilogy(
            cycle,
            df[f"{prefix}_alpha_bar_elem_max"],
            color=meta["color"],
            lw=1.7,
            label=meta["label"],
        )
    ax.set_title("History Element Max")
    ax.set_xlabel("cycle")
    ax.set_ylabel("alpha_bar elem max")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[1, 1]
    for prefix, meta in SERIES.items():
        ax.semilogy(cycle, df[f"{prefix}_f_fatigue_min"], color=meta["color"], lw=1.7, label=meta["label"])
    ax.set_title("Minimum Fatigue Degradation")
    ax.set_xlabel("cycle")
    ax.set_ylabel("min f")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[2, 0]
    for prefix, meta in SERIES.items():
        col = f"{prefix}_x_tip_d095_centered" if prefix == "diffuse" else f"{prefix}_x_tip_d095"
        ax.plot(cycle, df[col], color=meta["color"], lw=1.7, label=meta["label"])
    ax.set_title("Crack-Tip Position d>=0.95")
    ax.set_xlabel("cycle")
    ax.set_ylabel("centered x")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[2, 1]
    for prefix, meta in SERIES.items():
        ax.semilogy(cycle, df[f"{prefix}_Kt_proxy"], color=meta["color"], lw=1.7, label=meta["label"])
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
    parser.add_argument("--old-void-csv", type=Path, required=True)
    parser.add_argument("--fine-void-csv", type=Path, required=True)
    parser.add_argument("--diffuse-csv", type=Path, required=True)
    parser.add_argument("--diffuse-x-shift", type=float, default=-0.5)
    parser.add_argument("--diffuse-y-shift", type=float, default=-0.5)
    parser.add_argument("--out-csv", type=Path, required=True)
    parser.add_argument("--out-summary-csv", type=Path, required=True)
    parser.add_argument("--out-png", type=Path, required=True)
    parser.add_argument("--out-pdf", type=Path, default=None)
    args = parser.parse_args()

    df, summary = build_comparison(args)
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out_csv, index=False)
    summary.to_csv(args.out_summary_csv, index=False)
    plot_comparison(df, args.out_png, args.out_pdf)
    print(f"Wrote {args.out_csv}")
    print(f"Wrote {args.out_summary_csv}")
    print(f"Wrote {args.out_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
