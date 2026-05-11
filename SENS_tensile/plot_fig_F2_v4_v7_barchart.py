#!/usr/bin/env python3
"""plot_fig_F2_v4_v7_barchart.py — V4 + V7 cross-method comparison bar chart.

Loads `validation_v4_v7_all_methods.csv` and plots two side-by-side bar charts:
  (a) V4 mirror RMS (log scale, sorted)
  (b) V7 σ_xx relative residual (sorted)

PASS thresholds shown as horizontal reference lines.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import csv

HERE = Path(__file__).parent
CSV_PATH = HERE / "validation_v4_v7_all_methods.csv"
OUT_PATH = HERE / "fig_F2_v4_v7_barchart.pdf"


def load_data():
    rows = []
    with open(CSV_PATH) as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows


def main():
    rows = load_data()

    # Extract: method, V4_rms, V7_rxx
    methods = []
    v4_rms = []
    v7_rxx = []
    v7_status = []
    for r in rows:
        m = r["method"]
        try:
            rms = float(r["V4_rms_alpha"]) if r["V4_rms_alpha"] else None
            rxx = float(r["V7_rel_sxx"]) if r["V7_rel_sxx"] else None
        except (ValueError, KeyError):
            continue
        if rms is None:
            continue
        methods.append(m)
        v4_rms.append(rms)
        v7_rxx.append(rxx if rxx is not None else np.nan)
        v7_status.append(r.get("V7_status", "—"))

    # Sort by V4 RMS ascending
    order = np.argsort(v4_rms)
    methods = [methods[i] for i in order]
    v4_rms = [v4_rms[i] for i in order]
    v7_rxx = [v7_rxx[i] for i in order]
    v7_status = [v7_status[i] for i in order]

    # Color scheme: by V4 status
    v4_colors = []
    for rms in v4_rms:
        if rms < 2e-4:
            v4_colors.append("#0B7A0B")  # PASS green
        elif rms < 0.05:
            v4_colors.append("#1A8B6C")  # near-PASS teal
        elif rms < 0.1:
            v4_colors.append("#E8B41A")  # WARN yellow
        else:
            v4_colors.append("#C0282A")  # FAIL red

    # V7 colors
    v7_colors = []
    for rxx, st in zip(v7_rxx, v7_status):
        if np.isnan(rxx):
            v7_colors.append("#BBBBBB")  # SKIP grey
        elif rxx < 0.10:
            v7_colors.append("#0B7A0B")
        elif rxx < 0.30:
            v7_colors.append("#E8B41A")
        else:
            v7_colors.append("#C0282A")

    fig, axes = plt.subplots(1, 2, figsize=(13, 6.5), constrained_layout=True)

    # ===== Panel (a): V4 RMS bar (log scale) =====
    ax = axes[0]
    y_pos = np.arange(len(methods))
    # Replace zeros (by-construction PASS) with a small floor for log display
    v4_plot = [max(v, 1e-5) for v in v4_rms]
    bars = ax.barh(y_pos, v4_plot, color=v4_colors, edgecolor="black", linewidth=0.5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(methods, fontsize=8)
    ax.set_xscale("log")
    ax.set_xlim(1e-5, 1.0)
    ax.set_xlabel(r"V4 mirror RMS of $\bar{\alpha}$  (lower = better)", fontsize=10)
    ax.set_title("(a) V4 symmetry mirror RMS", fontsize=11)
    # PASS threshold (Mandal 2019 = 2e-4)
    ax.axvline(2e-4, color="green", linestyle=":", linewidth=1.5, label="PASS (Mandal 2019)")
    ax.axvline(0.05, color="orange", linestyle=":", linewidth=1.0, label="5× baseline")
    ax.legend(loc="lower right", fontsize=8)
    # Annotate by-construction PASS
    for i, (rms, m) in enumerate(zip(v4_rms, methods)):
        if rms == 0:
            ax.text(1.2e-5, i, "0 (by construction)", fontsize=7, va="center",
                    color="grey", style="italic")
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.3)

    # ===== Panel (b): V7 σ_xx relative residual =====
    ax2 = axes[1]
    v7_plot_raw = []
    for rxx in v7_rxx:
        if np.isnan(rxx):
            v7_plot_raw.append(0)
        else:
            v7_plot_raw.append(rxx * 100)  # to percent
    bars = ax2.barh(y_pos, v7_plot_raw, color=v7_colors, edgecolor="black", linewidth=0.5)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(methods, fontsize=8)
    ax2.set_xscale("log")
    ax2.set_xlim(0.05, 1e6)
    ax2.set_xlabel(r"V7 $\sigma_{xx}$ relative residual (%, log)", fontsize=10)
    ax2.set_title("(b) V7 BC residual on side edges", fontsize=11)
    # PASS / WARN bands
    ax2.axvline(10, color="green", linestyle=":", linewidth=1.5, label="PASS (<10%)")
    ax2.axvline(30, color="orange", linestyle=":", linewidth=1.5, label="WARN (10-30%)")
    ax2.axvline(0.12, color="blue", linestyle="--", linewidth=1.2, label="FEM-8 ref (0.12%)")
    ax2.legend(loc="lower right", fontsize=8)
    # Annotate SKIP
    for i, (rxx, m) in enumerate(zip(v7_rxx, methods)):
        if np.isnan(rxx):
            ax2.text(0.06, i, "SKIP / no V7", fontsize=7, va="center", color="grey",
                     style="italic")
    ax2.invert_yaxis()
    ax2.grid(axis="x", alpha=0.3)

    fig.suptitle("V4 + V7 across PIDL methods (sorted by V4 RMS) — paper §4.2.1",
                 fontsize=12, y=1.02)
    fig.savefig(OUT_PATH, bbox_inches="tight", dpi=150)
    print(f"saved: {OUT_PATH}")
    print(f"  {len(methods)} methods plotted")
    print(f"  V4 PASS by construction: {sum(1 for v in v4_rms if v == 0)}")
    print(f"  V4 best learned: {min(v for v in v4_rms if v > 0):.4f}")
    print(f"  V7 best (excluding NaN): {min((v*100 for v in v7_rxx if not np.isnan(v)), default=None):.1f}%")


if __name__ == "__main__":
    main()
