#!/usr/bin/env python3
"""plot_fig_F8_mesh_convergence.py — h-convergence comparison: strict Carrara vs AT1+PENALTY.

Hardcoded from:
  - AT1+PENALTY: FEM-D 2x4 matrix (Windows-FEM outbox `9094c1d` and earlier)
  - Strict Carrara: Task E ℓ/h=5 vs 10 (outbox `25975f5`, 2026-05-11)

Shows N_f vs ℓ/h on the same plot, demonstrating strict Carrara is mesh-stable (1%)
while AT1+PENALTY is non-monotonic (+26% over ℓ/h=5→20).
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
OUT_PATH = HERE / "fig_F8_mesh_convergence.pdf"

# AT1+PENALTY (Phase 1 PIDL-series reference, Δū=0.12, Windows-FEM FEM-D matrix)
# narrow band Lref_y=0.05 row (wide & narrow are bit-identical)
AT1_LH = np.array([5, 10, 15, 20])
AT1_NF = np.array([77, 79, 86, 97])

# Strict Carrara MIEHE+AT2+HISTORY (Task E, Δū=2.5e-3)
SC_LH = np.array([5, 10])
SC_NF = np.array([200, 202])


def main():
    fig, ax = plt.subplots(figsize=(8, 6), constrained_layout=True)

    # Reference: AT1+PENALTY baseline at ℓ/h≈2.5 (Abaqus uniform) = N_f=82
    ax.axhline(82, color="#0B4992", linestyle=":", linewidth=1.3,
               alpha=0.7, label="AT1+PENALTY Abaqus uniform ℓ/h≈2.5, N_f=82")

    # AT1+PENALTY h-sweep
    ax.plot(AT1_LH, AT1_NF, "o-", color="#0B4992", linewidth=2, markersize=10,
            markerfacecolor="white", markeredgewidth=2,
            label=f"AT1+PENALTY (Phase 1)  N_f: 77→97 (+26%)")
    for x, y in zip(AT1_LH, AT1_NF):
        ax.annotate(f"{y}", (x, y), textcoords="offset points", xytext=(5, 5),
                    fontsize=9, color="#0B4992")

    # Strict Carrara h-sweep (different Δū so different absolute N_f; normalize on right axis)
    ax2 = ax.twinx()
    ax2.plot(SC_LH, SC_NF, "s-", color="#0B7A0B", linewidth=2, markersize=10,
             markerfacecolor="white", markeredgewidth=2,
             label=f"Strict Carrara MIEHE+AT2+HISTORY  N_f: 200→202 (+1%)")
    for x, y in zip(SC_LH, SC_NF):
        ax2.annotate(f"{y}", (x, y), textcoords="offset points", xytext=(5, -12),
                     fontsize=9, color="#0B7A0B")

    ax.set_xlabel(r"$\ell_0 / h_{tip}$  (mesh refinement ratio)", fontsize=11)
    ax.set_ylabel(r"$N_f$  (AT1+PENALTY, Δū=$1.2\times 10^{-3}$)",
                  fontsize=11, color="#0B4992")
    ax2.set_ylabel(r"$N_f$  (strict Carrara, Δū=$2.5\times 10^{-3}$)",
                   fontsize=11, color="#0B7A0B")
    ax.tick_params(axis="y", labelcolor="#0B4992")
    ax2.tick_params(axis="y", labelcolor="#0B7A0B")

    ax.set_xlim(3, 22)
    ax.set_ylim(70, 105)
    ax2.set_ylim(195, 215)

    # Combined legend
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower right", fontsize=9, framealpha=0.95)

    ax.set_title(
        "h-convergence: strict Carrara mesh-converged at 1% (vs AT1+PENALTY +26% non-monotonic)\n"
        "Paper §FEM caveats — Mandal et al. 2019 EFM 217 anchor",
        fontsize=10,
    )
    ax.grid(True, alpha=0.3)

    fig.savefig(OUT_PATH, bbox_inches="tight", dpi=150)
    print(f"saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
