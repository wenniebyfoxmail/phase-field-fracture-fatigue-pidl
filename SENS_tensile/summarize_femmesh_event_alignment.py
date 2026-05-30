#!/usr/bin/env python3
"""Summarize FEM-mesh PIDL fixed-cycle vs matched-event field alignment."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "_analysis_fem_mechanism_20260528"
FIG_DIR = ANALYSIS / "figures"

FIXED = ANALYSIS / "aligned_fem_pidl_reference_tier_summary.csv"
EVENT_INPUTS = [
    ("standard", "event_detected_j84", ANALYSIS / "femmesh_pidl_event_j84_vs_standard_fem_c69.csv"),
    ("standard", "event_confirmed_j85", ANALYSIS / "femmesh_pidl_event_j85_vs_standard_fem_c69.csv"),
    ("n_step10", "event_detected_j84", ANALYSIS / "femmesh_pidl_event_j84_vs_nstep10_fem_c69.csv"),
    ("n_step10", "event_confirmed_j85", ANALYSIS / "femmesh_pidl_event_j85_vs_nstep10_fem_c69.csv"),
]
OUT_CSV = ANALYSIS / "femmesh_pidl_fixed_vs_event_alignment_summary.csv"
OUT_FIG = FIG_DIR / "femmesh_pidl_fixed_vs_event_alignment_20260530.png"


PANEL_METRICS = [
    ("damage_alpha", "tip_2l0_mean", "damage tip2"),
    ("alpha_bar", "tip_2l0_mean", "alpha_bar tip2"),
    ("alpha_bar", "p99", "alpha_bar p99"),
    ("psi_plus_raw", "tip_2l0_mean", "raw psi tip2"),
    ("psi_plus_active", "tip_2l0_mean", "active psi tip2"),
    ("psi_plus_active", "p99", "active psi p99"),
]


def load_fixed() -> pd.DataFrame:
    fixed = pd.read_csv(FIXED)
    fixed = fixed[fixed["cycle"] == 69].copy()
    fixed["fem_reference"] = fixed["reference"].map(
        {"FEM standard": "standard", "FEM n_step10": "n_step10"}
    )
    fixed["comparison_state"] = "fixed_c69_j68"
    fixed["ratio"] = fixed["PIDL_over_FEM_projected"]
    return fixed[["fem_reference", "comparison_state", "field", "metric", "ratio"]]


def load_event() -> pd.DataFrame:
    rows = []
    for reference, state, path in EVENT_INPUTS:
        table = pd.read_csv(path)
        table = table.copy()
        table["fem_reference"] = reference
        table["comparison_state"] = state
        table["ratio"] = table["PIDL_over_FEM_projected"]
        rows.append(table[["fem_reference", "comparison_state", "field", "metric", "ratio"]])
    return pd.concat(rows, ignore_index=True)


def plot(summary: pd.DataFrame) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    state_order = ["fixed_c69_j68", "event_detected_j84", "event_confirmed_j85"]
    ref_order = ["standard", "n_step10"]
    colors = {"standard": "#000000", "n_step10": "#0072B2"}
    markers = {"fixed_c69_j68": "o", "event_detected_j84": "s", "event_confirmed_j85": "^"}

    fig, axes = plt.subplots(2, 3, figsize=(13.0, 7.0), constrained_layout=True)
    for ax, (field, metric, title) in zip(axes.ravel(), PANEL_METRICS):
        for ref in ref_order:
            values = []
            for state in state_order:
                row = summary[
                    (summary["fem_reference"] == ref)
                    & (summary["comparison_state"] == state)
                    & (summary["field"] == field)
                    & (summary["metric"] == metric)
                ]
                values.append(float(row["ratio"].iloc[0]) if not row.empty else np.nan)
            x = np.arange(len(state_order))
            ax.plot(x, values, color=colors[ref], lw=1.3, label=ref)
            for xi, state, value in zip(x, state_order, values):
                ax.scatter([xi], [value], marker=markers[state], color=colors[ref], s=42)
        ax.axhline(1.0, color="0.5", ls="--", lw=1.0)
        ax.set_xticks(np.arange(len(state_order)), ["fixed\nj68", "detect\nj84", "confirm\nj85"])
        ax.set_ylabel("PIDL / FEM")
        ax.set_title(title)
        ax.grid(alpha=0.25)
        if field == "psi_plus_active":
            ax.set_yscale("log")
    axes[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle("FEM-mesh PIDL: fixed-cycle vs matched-event field ratios")
    fig.savefig(OUT_FIG, dpi=220)
    plt.close(fig)


def main() -> int:
    summary = pd.concat([load_fixed(), load_event()], ignore_index=True)
    summary.to_csv(OUT_CSV, index=False)
    plot(summary)
    key = summary[
        summary["comparison_state"].isin(["event_detected_j84", "event_confirmed_j85"])
        & (
            ((summary["field"] == "alpha_bar") & summary["metric"].isin(["tip_2l0_mean", "p99"]))
            | ((summary["field"] == "psi_plus_active") & summary["metric"].isin(["tip_2l0_mean", "p99"]))
        )
    ]
    print(key.to_string(index=False))
    print(f"wrote {OUT_CSV}")
    print(f"wrote {OUT_FIG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
