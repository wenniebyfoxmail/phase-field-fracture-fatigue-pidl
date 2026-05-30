#!/usr/bin/env python3
"""Summarize strict FEM-mesh LBFGS polish audits."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "_analysis_fem_mechanism_20260528"
AUDIT_DIR = ANALYSIS / "lbfgs_polish_audit_20260530"
FIG_DIR = ANALYSIS / "figures"
OUT_CSV = ANALYSIS / "lbfgs_polish_audit_summary_20260530.csv"
OUT_FIG = FIG_DIR / "lbfgs_polish_audit_20260530.png"


def load_rows() -> pd.DataFrame:
    frames = []
    for path in sorted(AUDIT_DIR.glob("cycle_*_lbfgs80/lbfgs_polish_metrics.csv")):
        df = pd.read_csv(path)
        df["audit_dir"] = str(path.parent)
        frames.append(df)
    if not frames:
        raise FileNotFoundError(f"No polish metrics under {AUDIT_DIR}")
    return pd.concat(frames, ignore_index=True)


def add_changes(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cycle, g in df.groupby("cycle", sort=True):
        before = g[g["stage"] == "before"].iloc[0]
        after = g[g["stage"] == "after"].iloc[0]
        row = {"cycle": int(cycle), "closure_calls": int(after["closure_calls"])}
        for col in [
            "loss_total",
            "grad_norm",
            "E_el",
            "E_d",
            "E_hist",
            "psi_plus_tip_2l0_mean",
            "psi_plus_p99",
            "psi_plus_right_band_mean",
            "alpha_tip_2l0_mean",
            "alpha_p99",
            "alpha_right_band_mean",
        ]:
            b = float(before[col])
            a = float(after[col])
            row[f"{col}_before"] = b
            row[f"{col}_after"] = a
            row[f"{col}_ratio_after_before"] = a / b if np.isfinite(b) and abs(b) > 1e-30 else np.nan
            row[f"{col}_delta"] = a - b
        rows.append(row)
    return pd.DataFrame(rows)


def plot(summary: pd.DataFrame) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    panels = [
        ("grad_norm_ratio_after_before", "gradient norm\nafter/before", False),
        ("loss_total_delta", "loss delta", False),
        ("psi_plus_tip_2l0_mean_ratio_after_before", "active psi tip2\nafter/before", False),
        ("psi_plus_p99_ratio_after_before", "active psi p99\nafter/before", False),
        ("alpha_tip_2l0_mean_ratio_after_before", "damage tip2\nafter/before", False),
        ("E_d_ratio_after_before", "E_d\nafter/before", False),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(12.4, 6.8), constrained_layout=True)
    for ax, (col, title, logy) in zip(axes.ravel(), panels):
        ax.bar(summary["cycle"].astype(str), summary[col], color="#0072B2", alpha=0.86)
        if "ratio" in col:
            ax.axhline(1.0, color="0.35", lw=1.0, ls="--")
        else:
            ax.axhline(0.0, color="0.35", lw=1.0, ls="--")
        ax.set_title(title)
        ax.set_xlabel("PIDL saved index")
        ax.grid(axis="y", alpha=0.25)
        if logy:
            ax.set_yscale("log")
        for i, value in enumerate(summary[col]):
            ax.text(i, value, f"{value:.3g}", ha="center", va="bottom", fontsize=8)
    fig.suptitle("Strict FEM-mesh PIDL LBFGS polish audit: same frozen history state")
    fig.savefig(OUT_FIG, dpi=220)
    plt.close(fig)


def main() -> int:
    summary = add_changes(load_rows())
    summary.to_csv(OUT_CSV, index=False)
    plot(summary)
    keep = [
        "cycle",
        "closure_calls",
        "grad_norm_ratio_after_before",
        "psi_plus_tip_2l0_mean_ratio_after_before",
        "psi_plus_p99_ratio_after_before",
        "alpha_tip_2l0_mean_ratio_after_before",
        "E_d_ratio_after_before",
    ]
    print(summary[keep].to_string(index=False))
    print(f"wrote {OUT_CSV}")
    print(f"wrote {OUT_FIG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
