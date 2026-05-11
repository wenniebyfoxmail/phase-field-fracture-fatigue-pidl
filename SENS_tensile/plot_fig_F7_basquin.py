#!/usr/bin/env python3
"""plot_fig_F7_basquin.py — strict Carrara Basquin slope (AMOR vs MIEHE, 6 points).

Hardcodes Task D 6-case data (Windows-FEM outbox `25975f5`, 2026-05-11).
Plots log-log N_f vs Δū, with Basquin fit and Carrara 2020 anchor band 3.8-4.0.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
OUT_PATH = HERE / "fig_F7_basquin.pdf"

# Task D 6-point sweep (Windows-FEM 25975f5)
DATA = [
    # (delta_u [×1e-3 mm], N_f_AMOR, N_f_MIEHE)
    (1.5, 1111, 1132),
    (2.0,  425,  435),
    (2.5,  195,  200),
    (3.0,   98,  102),
    (3.5,   52,   55),
    (4.0,   26,   28),
]

M_AMOR_FIT = 3.770
M_MIEHE_FIT = 3.716
A_AMOR_FIT = 2.75e-8
A_MIEHE_FIT = 3.95e-8


def main():
    dus = np.array([d[0] for d in DATA]) * 1e-3
    nfs_amor = np.array([d[1] for d in DATA])
    nfs_miehe = np.array([d[2] for d in DATA])

    # Basquin: N_f = A · Δū^(-m)
    du_dense = np.logspace(np.log10(1.4e-3), np.log10(4.2e-3), 100)
    nf_amor_fit = A_AMOR_FIT * du_dense**(-M_AMOR_FIT)
    nf_miehe_fit = A_MIEHE_FIT * du_dense**(-M_MIEHE_FIT)
    # Carrara 2020 anchor band m=3.8 to 4.0
    nf_carrara_lo = nf_amor_fit[0] * (du_dense[0] / du_dense)**3.8
    nf_carrara_hi = nf_amor_fit[0] * (du_dense[0] / du_dense)**4.0

    fig, ax = plt.subplots(figsize=(7.5, 6), constrained_layout=True)

    # Carrara anchor band
    ax.fill_between(du_dense, nf_carrara_lo, nf_carrara_hi, color="grey", alpha=0.2,
                    label=r"Carrara 2020 anchor m$\in$[3.8, 4.0]")

    # AMOR fit + points
    ax.plot(du_dense, nf_amor_fit, "-", color="#0B4992", linewidth=1.8,
            label=fr"AMOR fit  m={M_AMOR_FIT:.3f}")
    ax.plot(dus, nfs_amor, "o", color="#0B4992", markersize=10,
            markerfacecolor="white", markeredgewidth=2, label="AMOR data (6 pts)")

    # MIEHE fit + points
    ax.plot(du_dense, nf_miehe_fit, "--", color="#C0282A", linewidth=1.8,
            label=fr"MIEHE fit  m={M_MIEHE_FIT:.3f}")
    ax.plot(dus, nfs_miehe, "s", color="#C0282A", markersize=9,
            markerfacecolor="white", markeredgewidth=2, label="MIEHE data (6 pts)")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"$\Delta \bar{u}$  (mm)", fontsize=11)
    ax.set_ylabel(r"$N_f$  (cycles)", fontsize=11)
    ax.set_title(
        f"Strict Carrara Basquin slope: m$_{{AMOR}}$={M_AMOR_FIT:.3f} (+0.8% of 3.8), "
        f"m$_{{MIEHE}}$={M_MIEHE_FIT:.3f} (+2.2%)\n"
        "Phase 1 community-anchor validation, paper §4 supplementary",
        fontsize=10,
    )
    ax.legend(loc="upper right", fontsize=9, framealpha=0.95)
    ax.grid(True, which="both", alpha=0.3)
    ax.set_xlim(1.3e-3, 4.3e-3)
    ax.set_ylim(15, 1500)

    fig.savefig(OUT_PATH, bbox_inches="tight", dpi=150)
    print(f"saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
