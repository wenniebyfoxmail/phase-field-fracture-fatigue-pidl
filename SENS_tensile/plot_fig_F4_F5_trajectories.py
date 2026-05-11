#!/usr/bin/env python3
"""plot_fig_F4_F5_trajectories.py — a(N) and ᾱ_max(N) trajectories: PIDL vs FEM.

Two figs:
  F4: crack length x_tip vs cycle (3 Umax)
  F5: ᾱ_max vs cycle (3 Umax)

Data:
  FEM: ~/Downloads/_pidl_handoff_v2/post_process/SENT_PIDL_{08,10,12}_timeseries.csv
  PIDL: SENS_tensile/hl_8_Neurons_400_..._N300_Umax{0.08,0.10,0.12}/best_models/
        {alpha_bar_vs_cycle.npy, J_integral.csv}
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import csv

HERE = Path(__file__).parent
HANDOFF = Path.home() / "Downloads" / "_pidl_handoff_v2" / "post_process"

UMAX_LIST = [0.08, 0.10, 0.12]
COLORS = {0.08: "#0B4992", 0.10: "#E8B41A", 0.12: "#C0282A"}


def load_fem(umax):
    """Return cycle (N), a_ell (~crack length), alpha_max from FEM CSV."""
    if abs(umax - 0.08) < 1e-6: tag = "08"
    elif abs(umax - 0.10) < 1e-6: tag = "10"
    elif abs(umax - 0.12) < 1e-6: tag = "12"
    else: return None
    p = HANDOFF / f"SENT_PIDL_{tag}_timeseries.csv"
    if not p.exists():
        return None
    N, a, alpha = [], [], []
    with open(p) as f:
        for row in csv.DictReader(f):
            N.append(int(row["N"]))
            a.append(float(row["a_ell"]))
            alpha.append(float(row["alpha_max"]))
    return np.array(N), np.array(a), np.array(alpha)


def find_pidl_archive(umax):
    """Find baseline PIDL archive for given Umax."""
    pat = f"hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N*_R0.0_Umax{umax}"
    candidates = list(HERE.glob(pat))
    candidates = [c for c in candidates if "_" + str(umax) in c.name.split("Umax")[1].split("_")[0:1] or c.name.endswith(f"Umax{umax}")]
    # Filter to clean baseline (no method tag)
    clean = [c for c in candidates if c.name.endswith(f"Umax{umax}")]
    return clean[0] if clean else (candidates[0] if candidates else None)


def load_pidl(umax):
    """Return cycle, x_tip, alpha_max from PIDL archive."""
    arc = find_pidl_archive(umax)
    if not arc:
        return None
    j_csv = arc / "best_models" / "J_integral.csv"
    ab_npy = arc / "best_models" / "alpha_bar_vs_cycle.npy"
    if not (j_csv.exists() and ab_npy.exists()):
        return None
    # alpha_bar_vs_cycle.npy shape (N_cyc, 3) = [alpha_max, alpha_mean, f_mean]
    ab = np.load(ab_npy)
    cycle_pidl = np.arange(1, len(ab) + 1)
    alpha_max = ab[:, 0]
    # J_integral.csv has x_tip per cycle
    j_cycles, x_tips = [], []
    with open(j_csv) as f:
        for row in csv.DictReader(f):
            j_cycles.append(int(float(row["cycle"])))
            x_tips.append(float(row["x_tip"]))
    return cycle_pidl, alpha_max, np.array(j_cycles), np.array(x_tips)


def fig_F4():
    """a(N) trajectory."""
    fig, ax = plt.subplots(figsize=(8.5, 6), constrained_layout=True)
    for u in UMAX_LIST:
        fem = load_fem(u)
        pidl = load_pidl(u)
        c = COLORS[u]
        if fem is not None:
            N, a, _ = fem
            ax.plot(N, a, "-", color=c, linewidth=2.5,
                    label=f"FEM u={u}", alpha=0.9)
        if pidl is not None:
            _, _, jc, xt = pidl
            # x_tip relative to slit endpoint at x=0
            a_pidl = xt - 0.0  # x_tip = a-x distance from slit endpoint
            ax.plot(jc, a_pidl, "--o", color=c, linewidth=1.5, markersize=5,
                    label=f"PIDL u={u}", markevery=10, alpha=0.7)

    ax.set_xlabel(r"Cycle $N$", fontsize=11)
    ax.set_ylabel(r"Crack length $a$  (mm, from notch endpoint)", fontsize=11)
    ax.set_title(r"a(N) crack-tip trajectory: PIDL ahead of FEM at given $N$ (Pattern B)",
                 fontsize=11)
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 420)
    ax.set_ylim(-0.02, 0.55)
    fig.savefig(HERE / "fig_F4_a_vs_N.pdf", bbox_inches="tight", dpi=150)
    plt.close()
    print(f"saved: fig_F4_a_vs_N.pdf")


def fig_F5():
    """ᾱ_max(N) trajectory."""
    fig, ax = plt.subplots(figsize=(8.5, 6), constrained_layout=True)
    for u in UMAX_LIST:
        fem = load_fem(u)
        pidl = load_pidl(u)
        c = COLORS[u]
        if fem is not None:
            N, _, alpha = fem
            ax.plot(N, alpha, "-", color=c, linewidth=2.5,
                    label=f"FEM u={u}", alpha=0.9)
        if pidl is not None:
            cp, amax_p, _, _ = pidl
            ax.plot(cp, amax_p, "--o", color=c, linewidth=1.5, markersize=5,
                    label=f"PIDL u={u}", markevery=10, alpha=0.7)

    # α_T threshold (0.5 in Phase 1 toy units)
    ax.axhline(0.5, color="grey", linestyle=":", linewidth=1.5, label=r"$\alpha_T=0.5$")

    ax.set_xlabel(r"Cycle $N$", fontsize=11)
    ax.set_ylabel(r"$\bar{\alpha}_{\max}$  (peak fatigue accumulator)", fontsize=11)
    ax.set_yscale("log")
    ax.set_title(r"$\bar{\alpha}_{\max}$ vs cycle: PIDL field-level peak 9-94× lower than FEM (Pattern C)",
                 fontsize=11)
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, which="both", alpha=0.3)
    ax.set_xlim(0, 420)
    ax.set_ylim(0.01, 1e3)
    fig.savefig(HERE / "fig_F5_alpha_max_vs_N.pdf", bbox_inches="tight", dpi=150)
    plt.close()
    print(f"saved: fig_F5_alpha_max_vs_N.pdf")


def main():
    fig_F4()
    fig_F5()


if __name__ == "__main__":
    main()
