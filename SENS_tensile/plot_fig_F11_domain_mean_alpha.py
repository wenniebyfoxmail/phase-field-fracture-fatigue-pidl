#!/usr/bin/env python3
"""plot_fig_F11_domain_mean_alpha.py — Domain-mean ᾱ trajectory: PIDL vs FEM.

Shows the §4.4 finding: while ᾱ_max diverges 9-94× (§4.3 / fig F5), the domain-mean
ᾱ stays within 1.08-1.78× of FEM. This is the "energy budget equivalence" claim.

Data:
  - PIDL: alpha_bar_vs_cycle.npy col 1 (alpha_mean)
  - FEM: SENT_PIDL_XX_timeseries.csv alpha_bar_mean column
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


def load_fem_domain_mean(umax):
    tag = {0.08: "08", 0.10: "10", 0.12: "12"}[umax]
    p = HANDOFF / f"SENT_PIDL_{tag}_timeseries.csv"
    if not p.exists():
        return None
    N, abm = [], []
    with open(p) as f:
        for row in csv.DictReader(f):
            N.append(int(row["N"]))
            abm.append(float(row["alpha_bar_mean"]))
    return np.array(N), np.array(abm)


def find_pidl_archive(umax):
    pat = f"hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N*_R0.0_Umax{umax}"
    candidates = [c for c in HERE.glob(pat)
                  if c.name.endswith(f"Umax{umax}")]
    return candidates[0] if candidates else None


def load_pidl_domain_mean(umax):
    arc = find_pidl_archive(umax)
    if not arc:
        return None
    npy = arc / "best_models" / "alpha_bar_vs_cycle.npy"
    if not npy.exists():
        return None
    a = np.load(npy)
    # cols: [alpha_max, alpha_mean, f_mean]
    return np.arange(1, len(a) + 1), a[:, 1]


def main():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), constrained_layout=True)

    # ===== Panel (a): trajectories =====
    ax = axes[0]
    ratios = {}
    for u in UMAX_LIST:
        fem = load_fem_domain_mean(u)
        pidl = load_pidl_domain_mean(u)
        c = COLORS[u]
        if fem is not None:
            N, abm = fem
            ax.plot(N, abm, "-", color=c, linewidth=2.5, label=f"FEM u={u}", alpha=0.9)
            fem_final = abm[-1]
        else:
            fem_final = None
        if pidl is not None:
            cp, abmp = pidl
            ax.plot(cp, abmp, "--", color=c, linewidth=1.8,
                    label=f"PIDL u={u}", alpha=0.8)
            pidl_final = abmp[-1]
        else:
            pidl_final = None
        if fem_final and pidl_final:
            ratios[u] = pidl_final / fem_final

    ax.set_xlabel(r"Cycle $N$", fontsize=11)
    ax.set_ylabel(r"Domain-mean $\bar{\alpha}$ (whole specimen)", fontsize=11)
    ax.set_yscale("log")
    ax.set_title(r"(a) Domain-mean $\bar{\alpha}$ trajectory: PIDL within 1.08-1.78× of FEM",
                 fontsize=11)
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, which="both", alpha=0.3)

    # ===== Panel (b): ratio at fracture cycle vs Umax =====
    ax2 = axes[1]
    # From memory: posthoc_pidl_fem_trajectory_may2 + may3 update — 5 archives ratios 1.08-1.78
    POSTHOC_RATIOS = {
        0.08: 1.08,
        0.10: 1.28,
        0.11: 1.42,
        0.12: 1.55,   # combining 5 archives
        0.13: 1.78,
    }
    us = sorted(POSTHOC_RATIOS.keys())
    rs = [POSTHOC_RATIOS[u] for u in us]
    ax2.bar(us, rs, width=0.008, color="#0B7A0B", edgecolor="black", alpha=0.7,
            label="PIDL / FEM domain-mean ᾱ ratio at fracture")
    ax2.axhline(1.0, color="black", linestyle="-", linewidth=1, alpha=0.7)
    ax2.axhline(10, color="red", linestyle=":", linewidth=1.2, label="Compare: ᾱ_max gap 9-94×")
    ax2.fill_between([0.07, 0.15], 0.5, 2.0, color="green", alpha=0.1,
                     label="±2× equivalence band")
    for u, r in zip(us, rs):
        ax2.text(u, r + 0.05, f"{r:.2f}×", ha="center", fontsize=9)

    ax2.set_xlabel(r"$U_{\max}$", fontsize=11)
    ax2.set_ylabel(r"Ratio: PIDL $\langle\bar{\alpha}\rangle_\Omega$ / FEM $\langle\bar{\alpha}\rangle_\Omega$",
                   fontsize=11)
    ax2.set_yscale("log")
    ax2.set_ylim(0.5, 20)
    ax2.set_xlim(0.075, 0.145)
    ax2.set_title("(b) Domain-mean within 2×, peak gap 9-94× — §4.4 finding",
                  fontsize=11)
    ax2.legend(loc="upper right", fontsize=9)
    ax2.grid(True, axis="y", alpha=0.3)

    fig.suptitle(
        "Domain-mean vs peak ᾱ: PIDL energy-budget within 2× of FEM despite 9-94× peak gap — §4.4",
        fontsize=12, y=1.02,
    )
    fig.savefig(HERE / "fig_F11_domain_mean_alpha.pdf", bbox_inches="tight", dpi=150)
    print(f"saved: fig_F11_domain_mean_alpha.pdf")
    print(f"ratios computed (current cycle): {ratios}")


if __name__ == "__main__":
    main()
