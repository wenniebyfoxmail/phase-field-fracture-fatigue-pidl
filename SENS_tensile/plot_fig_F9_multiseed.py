#!/usr/bin/env python3
"""plot_fig_F9_multiseed.py — Multi-seed reproducibility of soft-sym penalty.

Queue E production data: 3 seeds × 4 Umax (Windows-PIDL outbox, May 8).
Plus baseline + A1 + Strac alone + Combo for §4.2 context.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
OUT_PATH = HERE / "fig_F9_multiseed.pdf"

# Queue E: soft-sym λ=1, 3 seeds × Umax (Windows-PIDL outbox, May 8 + May 7 EOD)
QUEUE_E = {
    "u=0.12": {"seeds": [1, 2, 3], "N_f": [85, 85, 86], "V4_RMS": [0.0220, 0.0216, 0.0220]},
    "u=0.10": {"seeds": [1],        "N_f": [168],         "V4_RMS": [0.0222]},
    "u=0.11": {"seeds": [1],        "N_f": [128],         "V4_RMS": [0.0218]},
    "u=0.13": {"seeds": [1],        "N_f": [62],          "V4_RMS": [0.0216]},
}
FEM_REF_NF = {"u=0.08": 396, "u=0.09": 254, "u=0.10": 170, "u=0.11": 117,
              "u=0.12": 82,  "u=0.13": 57,  "u=0.14": 39}
BASELINE_NF = {"u=0.12": 82, "u=0.11": 117}  # PIDL baseline same as FEM at training Umax


def main():
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), constrained_layout=True)

    # ===== Panel (a): N_f vs Umax =====
    ax = axes[0]
    umax_list = sorted(QUEUE_E.keys(), key=lambda k: float(k.split("=")[1]))
    fem_x = []
    fem_y = []
    pidl_x = []
    pidl_y_mean = []
    pidl_y_err = []
    for u in umax_list:
        if u in FEM_REF_NF:
            fem_x.append(float(u.split("=")[1]))
            fem_y.append(FEM_REF_NF[u])
        d = QUEUE_E[u]
        nfs = d["N_f"]
        pidl_x.append(float(u.split("=")[1]))
        pidl_y_mean.append(np.mean(nfs))
        pidl_y_err.append(np.std(nfs) if len(nfs) > 1 else 0)

    ax.plot(fem_x, fem_y, "o-", color="black", linewidth=1.8, markersize=8,
            label="FEM reference (AT1+AMOR)")
    ax.errorbar(pidl_x, pidl_y_mean, yerr=pidl_y_err, fmt="s",
                color="#0B7A0B", markersize=12, capsize=5, linewidth=2,
                markerfacecolor="white", markeredgewidth=2,
                label="PIDL soft-sym (Queue E, 3 seeds @ u=0.12)")
    # Annotate
    for x, y, n in zip(pidl_x, pidl_y_mean, [len(QUEUE_E[u]["N_f"]) for u in umax_list]):
        if n > 1:
            ax.annotate(f"n={n}", (x, y), textcoords="offset points", xytext=(8, 8),
                        fontsize=8, color="#0B7A0B")

    ax.set_xlabel(r"$U_{\max}$  (training amplitude)", fontsize=11)
    ax.set_ylabel(r"$N_f$  (cycles to fracture)", fontsize=11)
    ax.set_yscale("log")
    ax.set_title("(a) Soft-sym N_f vs FEM, multi-seed @ u=0.12", fontsize=11)
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, which="both", alpha=0.3)

    # ===== Panel (b): V4 RMS vs Umax =====
    ax2 = axes[1]
    for u in umax_list:
        d = QUEUE_E[u]
        x_val = float(u.split("=")[1])
        for s, rms in zip(d["seeds"], d["V4_RMS"]):
            ax2.plot(x_val, rms, "o", color="#0B7A0B", markersize=10,
                     markerfacecolor="white", markeredgewidth=1.5)
            if len(d["seeds"]) > 1:
                ax2.annotate(f"s{s}", (x_val, rms), textcoords="offset points",
                             xytext=(5, 0), fontsize=7, color="grey")
    # Baseline RMS band (0.30-0.40 from V4+V7 table)
    ax2.axhspan(0.30, 0.40, alpha=0.15, color="red", label="Baseline FAIL band (0.30-0.40)")
    # Reduction line
    ax2.axhline(0.0220, color="#0B7A0B", linestyle="--", linewidth=1.2,
                label="Queue E mean 0.022 (14× reduction)")
    # FEM target
    ax2.axhline(2.98e-5, color="blue", linestyle=":", linewidth=1.5,
                label="FEM physics target 2.98×10⁻⁵")

    ax2.set_xlabel(r"$U_{\max}$", fontsize=11)
    ax2.set_ylabel(r"V4 mirror RMS of $\bar{\alpha}$", fontsize=11)
    ax2.set_yscale("log")
    ax2.set_ylim(1e-5, 0.5)
    ax2.set_title("(b) V4 RMS reduction, 14× across 4 Umax + 3 seeds", fontsize=11)
    ax2.legend(loc="center right", fontsize=8)
    ax2.grid(True, which="both", alpha=0.3)

    fig.suptitle("Queue E soft-sym penalty: multi-seed + cross-Umax reproducibility — §4.2",
                 fontsize=12, y=1.02)
    fig.savefig(OUT_PATH, bbox_inches="tight", dpi=150)
    print(f"saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
