#!/usr/bin/env python3
"""
plot_oracle_umax_sweep.py — Apr 28 placeholder paper figure
                             (cross-Umax oracle trajectories vs FEM)

Two-panel figure for paper Ch2:

  Panel A: ᾱ_max(N) trajectories (log-y) for
            - FEM 0.10/0.11/0.12  (3 reference curves, black/grey gradient)
            - static oracle 0.10/0.11/0.12  (3 oracle curves)
            - Variant A oracle 0.12 moving-zone  (1 ablation curve)

  Panel B: Same data with x normalized by N_f (cycle-fraction view) — shows
           the three trajectory shapes (plateau / linear / sub-linear / explosive)
           on a unified scale.

PLACEHOLDER status: oracle 0.10 is a RESUMED run (resumed from c60 after
Mac swap kill). True 0.10 may differ if re-run fresh. This figure is
suitable for in-progress reports + paper draft revisions; final version
should swap in fresh 0.10 trajectory after Windows P3 re-run completes.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "source"))

from paper_style import apply_style, method_style, LANCET_PALETTE  # noqa: E402

# -------- archive registry --------------------------------------------------

BASE_DIR = HERE
FEM_DIR = Path("/Users/wenxiaofang/Downloads/_pidl_handoff_v2/post_process")

ORACLE_STATIC = {
    0.12: BASE_DIR / "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_oracle_zone0.02",
    0.11: BASE_DIR / "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.11_oracle_zone0.02",
    0.10: BASE_DIR / "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.1_oracle_zone0.02",
}
ORACLE_VA_012 = BASE_DIR / "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N10_R0.0_Umax0.12_oracle_zone0.02_movingzone"

# Per-Umax FEM N_f from earlier handoff_v2
FEM_NF = {0.08: 396, 0.09: 254, 0.10: 170, 0.11: 117, 0.12: 82}
ORACLE_NF = {0.12: 83, 0.11: 117, 0.10: 156}    # static oracle


def load_oracle_trajectory(archive: Path) -> np.ndarray:
    """Load alpha_bar_vs_cycle.npy[:,0] (ᾱ_max per cycle)."""
    f = archive / "best_models" / "alpha_bar_vs_cycle.npy"
    if not f.is_file():
        return None
    arr = np.load(str(f))
    return arr[:, 0]    # ᾱ_max column


def load_fem_trajectory(umax: float) -> np.ndarray:
    """Read SENT_PIDL_NN_timeseries.csv 'alpha_max' column → numpy."""
    u_tag = f"{int(round(umax * 100)):02d}"
    f = FEM_DIR / f"SENT_PIDL_{u_tag}_timeseries.csv"
    if not f.is_file():
        return None
    with open(f) as fh:
        reader = csv.DictReader(fh)
        return np.array([float(r["alpha_max"]) for r in reader])


# -------- color scheme (placeholder; not in paper_style canonical map) ------

UMAX_COLORS = {
    0.08: LANCET_PALETTE["dark_red"],
    0.09: LANCET_PALETTE["red"],
    0.10: LANCET_PALETTE["peach"],
    0.11: LANCET_PALETTE["teal"],
    0.12: LANCET_PALETTE["deep_blue"],
}


def main():
    apply_style()

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.0), tight_layout=True)
    axA, axB = axes

    # --- Panel A: raw cycle vs ᾱ_max (log-y) -------------------------------
    for umax in [0.10, 0.11, 0.12]:
        # FEM (lighter, dashed)
        fem = load_fem_trajectory(umax)
        if fem is not None:
            cyc = np.arange(1, len(fem) + 1)
            axA.semilogy(cyc, fem, "--",
                         color=UMAX_COLORS[umax], linewidth=1.2, alpha=0.7,
                         label=f"FEM U={umax}")

        # Static oracle (color, solid bold)
        ora = load_oracle_trajectory(ORACLE_STATIC[umax])
        if ora is not None:
            cyc = np.arange(len(ora))
            axA.semilogy(cyc[ora > 0], ora[ora > 0], "-",
                         color=UMAX_COLORS[umax], linewidth=2.2,
                         label=f"static oracle U={umax}")

    # Variant A 0.12
    va = load_oracle_trajectory(ORACLE_VA_012)
    if va is not None:
        cyc = np.arange(len(va))
        axA.semilogy(cyc[va > 0], va[va > 0], ":", marker="^", markersize=6,
                     color=LANCET_PALETTE["dark_red"], linewidth=2.0,
                     label="Variant A oracle Umax=0.12 (moving zone, c0-9)")

    axA.set_xlabel("cycle N")
    axA.set_ylabel(r"$\bar{\alpha}_{\max}$")
    axA.set_title("Cross-Umax oracle trajectories vs FEM (raw cycles)")
    axA.grid(alpha=0.3, which="both")
    axA.legend(fontsize=7, loc="lower right", ncol=2)

    # --- Panel B: x normalized by N_f --------------------------------------
    for umax in [0.10, 0.11, 0.12]:
        fem = load_fem_trajectory(umax)
        if fem is not None:
            n = FEM_NF[umax]
            x = np.arange(1, len(fem) + 1) / n
            axB.semilogy(x, fem, "-",
                         color=UMAX_COLORS[umax], linewidth=1.2, alpha=0.5)

        ora = load_oracle_trajectory(ORACLE_STATIC[umax])
        if ora is not None:
            nf = ORACLE_NF[umax]
            x = np.arange(len(ora)) / nf
            mask = ora > 0
            axB.semilogy(x[mask], ora[mask], "-",
                         color=UMAX_COLORS[umax], linewidth=2.2)

    if va is not None:
        # V-A only goes to c9; mark x = c/83 where 83 is static-oracle-0.12 N_f
        x = np.arange(len(va)) / 83
        mask = va > 0
        axB.semilogy(x[mask], va[mask], ":", marker="^", markersize=6,
                     color=LANCET_PALETTE["dark_red"], linewidth=2.0)

    axB.axvline(1.0, color="grey", linestyle="--", alpha=0.4)
    axB.text(1.01, axB.get_ylim()[0] * 2 if axB.get_ylim()[0] > 0 else 1e-1,
             r"$N_f$", fontsize=9, color="grey")
    axB.set_xlim(0, 1.3)
    axB.set_xlabel(r"$N / N_f$ (normalized cycle)")
    axB.set_ylabel(r"$\bar{\alpha}_{\max}$")
    axB.set_title("Same data, x normalized by N_f (cycle-fraction view)")
    axB.grid(alpha=0.3, which="both")

    # Annotations on Panel A
    axA.annotate(
        "static 0.12 plateau\n(saturation cliff)",
        xy=(40, 88), xytext=(50, 250),
        fontsize=8, color=UMAX_COLORS[0.12],
        arrowprops=dict(arrowstyle="->", color=UMAX_COLORS[0.12], alpha=0.6),
    )
    axA.annotate(
        "static 0.11 linear runaway",
        xy=(80, 4500), xytext=(20, 9000),
        fontsize=8, color=UMAX_COLORS[0.11],
        arrowprops=dict(arrowstyle="->", color=UMAX_COLORS[0.11], alpha=0.6),
    )
    axA.annotate(
        "Variant A: explosive\n(moving zone, c0-9 only)",
        xy=(8, 4000), xytext=(15, 0.8),
        fontsize=8, color=LANCET_PALETTE["dark_red"],
        arrowprops=dict(arrowstyle="->", color=LANCET_PALETTE["dark_red"], alpha=0.6),
    )

    fig.suptitle("Oracle Umax sweep — three trajectory regimes (PLACEHOLDER)", fontsize=11)

    out = HERE / "figures" / "audit" / "oracle_umax_sweep_placeholder.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"→ {out.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
