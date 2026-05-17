#!/usr/bin/env python3
"""plot_cross_umax_synthesis.py — N_f and gap_to_FEM across Umax = {0.08, 0.12, 0.13}

Single deliverable for the May 17-18 Umax sweep:
  - top:    N_f vs Umax (FEM / baseline PIDL / SDF v1)
  - bottom: gap to FEM (%) vs Umax for baseline and SDF

Confirms the May 17 finding: SDF uniformly shifts PIDL N_f down 1-6%;
this LANDS on FEM at u=0.13 (where baseline was +7% over) but AMPLIFIES
the under-FEM gap at u=0.08 and u=0.12.
"""
from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent

# Data from May 17-18 analysis
DATA = [
    # (Umax, FEM_Nf, baseline_Nf, SDF_Nf)
    (0.08, 396, 341, 323),
    (0.12, 82,  80,  79),
    (0.13, 57,  61,  57),
]

def main():
    u   = [d[0] for d in DATA]
    fem = [d[1] for d in DATA]
    bas = [d[2] for d in DATA]
    sdf = [d[3] for d in DATA]
    gap_bas = [100*(b-f)/f for b,f in zip(bas, fem)]
    gap_sdf = [100*(s-f)/f for s,f in zip(sdf, fem)]

    fig, axes = plt.subplots(2, 1, figsize=(7.5, 8))

    # ─── top: N_f vs Umax ───────────────────────────────────────────────
    ax = axes[0]
    ax.plot(u, fem, "rs-", lw=2, ms=12, label="FEM N_f", mfc="red", mec="darkred")
    ax.plot(u, bas, "ko-", lw=1.8, ms=10, label="baseline PIDL N_f", mfc="black")
    ax.plot(u, sdf, "^-", color="tab:blue", lw=1.8, ms=11,
            label="SDF v1 PIDL N_f", mec="navy")
    for ui, fi, bi, si in zip(u, fem, bas, sdf):
        ax.annotate(f"{fi}", (ui, fi), xytext=(8, 5), textcoords="offset points",
                    color="darkred", fontsize=9)
        ax.annotate(f"{bi}", (ui, bi), xytext=(8, -12), textcoords="offset points",
                    color="black", fontsize=9)
        ax.annotate(f"{si}", (ui, si), xytext=(-25, -12), textcoords="offset points",
                    color="navy", fontsize=9)
    ax.set_yscale("log")
    ax.set_xlabel("Umax")
    ax.set_ylabel("N_f (cycles)")
    ax.set_title("N_f vs Umax — FEM ground truth vs PIDL baseline vs SDF v1")
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=10, loc="upper right")
    ax.set_xticks(u)
    ax.set_xlim(0.07, 0.14)

    # ─── bottom: gap-to-FEM percentage ───────────────────────────────────
    ax = axes[1]
    ax.axhline(0, color="red", lw=2.5, alpha=0.6, label="FEM (zero gap)")
    ax.plot(u, gap_bas, "ko-", lw=1.8, ms=10, label="baseline PIDL", mfc="black")
    ax.plot(u, gap_sdf, "^-", color="tab:blue", lw=1.8, ms=11,
            label="SDF v1 PIDL", mec="navy")
    for ui, gb, gs in zip(u, gap_bas, gap_sdf):
        ax.annotate(f"{gb:+.0f}%", (ui, gb), xytext=(8, 5), textcoords="offset points",
                    color="black", fontsize=10)
        ax.annotate(f"{gs:+.0f}%", (ui, gs), xytext=(8, -12), textcoords="offset points",
                    color="navy", fontsize=10)
    # arrows: how SDF shifts baseline
    for ui, gb, gs in zip(u, gap_bas, gap_sdf):
        ax.annotate("", xy=(ui, gs), xytext=(ui, gb),
                    arrowprops=dict(arrowstyle="->", color="gray", lw=1.4, alpha=0.6))
    ax.set_xlabel("Umax")
    ax.set_ylabel("N_f gap to FEM (%)")
    ax.set_title("Gap-to-FEM(%) — SDF closes baseline overshoot at u=0.13, "
                 "amplifies undershoot at u≤0.12")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=10, loc="best")
    ax.set_xticks(u)
    ax.set_xlim(0.07, 0.14)

    fig.suptitle("Cross-Umax SDF v1 sensitivity (seed=1)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))

    out_dir = HERE.parent / "references_local" / "sdf_ribbon_smoke"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_png = out_dir / "cross_umax_Nf_synthesis.png"
    fig.savefig(out_png, dpi=140)
    print(f"saved: {out_png}")


if __name__ == "__main__":
    main()
