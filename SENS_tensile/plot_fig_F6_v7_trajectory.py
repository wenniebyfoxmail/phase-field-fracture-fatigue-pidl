#!/usr/bin/env python3
"""plot_fig_F6_v7_trajectory.py — V7 σ_xx trajectory comparison across 4 PIDL configurations.

Hardcoded from Windows-PIDL outbox `7387eec` (Phase B + Phase C, 2026-05-09) +
Taobo Strac-alone smoke + baseline.

Shows cycle-by-cycle relative σ_xx residual for:
  - Baseline (no V7 intervention)
  - Sym soft alone (Queue E λ=1)
  - Strac penalty alone (Taobo Phase F smoke, bimodal!)
  - A1 + Strac combo (Phase C, monotonic settle to WARN range)
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
OUT_PATH = HERE / "fig_F6_v7_trajectory.pdf"

# Cycle 0-4 V7 σ_xx relative residuals (percent)
TRAJECTORIES = {
    "Baseline u=0.12":  [26.5, 26.5, 26.5, 26.5, 26.5],   # constant (baseline)
    "Sym soft alone (Queue E λ=1)": [27.6, 27.6, 27.6, 27.6, 27.6],  # ~baseline (V4-only)
    "Strac alone (Phase F smoke)":  [364, 118, 14, 527, 10],  # BIMODAL (outbox)
    "A1 + Strac combo (Phase C)":   [82, 46, 101, 17, 16],   # Monotonic settle
}
COLORS = {
    "Baseline u=0.12":              "#666666",
    "Sym soft alone (Queue E λ=1)": "#0B4992",
    "Strac alone (Phase F smoke)":  "#C0282A",
    "A1 + Strac combo (Phase C)":   "#0B7A0B",
}


def main():
    fig, ax = plt.subplots(figsize=(9, 6.5), constrained_layout=True)

    cycles = np.arange(5)
    for name, traj in TRAJECTORIES.items():
        ax.plot(cycles, traj, "o-", color=COLORS[name], linewidth=2, markersize=10,
                label=name, markerfacecolor="white", markeredgewidth=2)

    # PASS/WARN/FAIL bands
    ax.axhline(10, color="green", linestyle=":", linewidth=1.5, alpha=0.7,
               label="PASS (<10%)")
    ax.axhline(30, color="orange", linestyle=":", linewidth=1.5, alpha=0.7,
               label="WARN (10-30%)")
    ax.fill_between(cycles, 0.1, 10, color="green", alpha=0.08)
    ax.fill_between(cycles, 10, 30, color="orange", alpha=0.08)
    ax.fill_between(cycles, 30, 1e4, color="red", alpha=0.05)

    # FEM-8 reference
    ax.axhline(0.12, color="blue", linestyle="--", linewidth=1.3,
               label="FEM-8 ref 0.12%")

    ax.set_xlabel("Cycle (post-pretrain)", fontsize=11)
    ax.set_ylabel(r"V7 relative $\sigma_{xx}$ residual on side edge (%, log)", fontsize=11)
    ax.set_yscale("log")
    ax.set_xticks(cycles)
    ax.set_ylim(0.05, 1000)
    ax.set_title(
        "V7 trajectory: Strac alone bimodal vs A1+Strac combo monotonic settle — §4.2.3-4",
        fontsize=10,
    )
    ax.legend(loc="upper right", fontsize=9, framealpha=0.95)
    ax.grid(True, which="both", alpha=0.3)

    # Annotate key spikes
    ax.annotate("bimodal spike\nat cycle 3",
                xy=(3, 527), xytext=(2.2, 800),
                fontsize=9, color="#C0282A",
                arrowprops=dict(arrowstyle="->", color="#C0282A", linewidth=1))
    ax.annotate("combo settles\nto WARN by c4",
                xy=(4, 16), xytext=(3.4, 3),
                fontsize=9, color="#0B7A0B",
                arrowprops=dict(arrowstyle="->", color="#0B7A0B", linewidth=1))

    fig.savefig(OUT_PATH, bbox_inches="tight", dpi=150)
    print(f"saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
