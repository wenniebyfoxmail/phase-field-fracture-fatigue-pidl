#!/usr/bin/env python3
"""
plot_process_zone_comparison.py — A2 cross-archive comparison figures.

Reads `process_zone_metrics.npy` from each archive and produces:

  1. figures/audit/pz_method_comparison_Umax012.png
       4-panel: ᾱ_max, ψ⁺_max, ∫g·ψ⁺_l0, ∫f·ψ⁺_l0 vs cycle.
       Lines: baseline + enriched + spAlphaT(b0.5,b0.8) + psiHack at Umax=0.12.

  2. figures/audit/pz_umax_sweep_baseline.png
       Same 4 panels but lines = baseline coeff=1.0 at Umax 0.09/0.10/0.11/0.12.

  3. process_zone_summary.csv
       Per-archive row: archive | umax | N_cyc | ᾱ_max@last | ψ⁺_max@last
                       | int_psi_l0@last | int_gpsi_l0@last | int_fpsi_l0@last
                       | int_psi_2l0@last | int_gpsi_2l0@last | int_fpsi_2l0@last
                       | pz_alpha_area@last | pz_alphabar_area@last
                       | psi_top1pct@last | gpsi_top1pct@last | fpsi_top1pct@last
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

# Column index map (matches OUT_COLUMNS in compute_process_zone_metrics.py)
COLS = {
    "cycle": 0,
    "alpha_bar_max": 1, "alpha_bar_mean": 2, "alpha_max": 3, "alpha_mean": 4,
    "psi_max": 5, "psi_p99": 6, "psi_top1pct": 7, "psi_top5pct": 8,
    "gpsi_max": 9, "gpsi_p99": 10, "gpsi_top1pct": 11, "gpsi_top5pct": 12,
    "fpsi_max": 13, "fpsi_p99": 14, "fpsi_top1pct": 15, "fpsi_top5pct": 16,
    "int_psi_l0": 17, "int_gpsi_l0": 18, "int_fpsi_l0": 19,
    "int_psi_2l0": 20, "int_gpsi_2l0": 21, "int_fpsi_2l0": 22,
    "int_psi_full": 23, "int_gpsi_full": 24, "int_fpsi_full": 25,
    "pz_alpha_area": 26, "pz_alphabar_area": 27,
}


def load_archive(archive_dir: Path):
    f = archive_dir / "best_models" / "process_zone_metrics.npy"
    if not f.is_file():
        return None
    arr = np.load(str(f))
    return arr


def short_name(archive: str) -> str:
    s = archive.replace("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_", "")
    s = s.replace("_R0.0", "")
    s = s.split("_cycle")[0]
    return s


# ---------------- archive groups ----------------
METHOD_GROUP_U012 = [
    ("baseline (2D NN)",
     "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12",
     "k", "-"),
    ("Enriched-ansatz v1",
     "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_enriched_ansatz_modeI_v1_cycle94_Nf84_real_fracture",
     "#D62728", "-"),
    ("spAlphaT b=0.5",
     "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_spAlphaT_b0.5_r0.1_cycle86_Nf76_real_fracture",
     "#FF7F0E", "--"),
    ("spAlphaT b=0.8",
     "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_spAlphaT_b0.8_r0.03_cycle90_Nf80_real_fracture",
     "#FF7F0E", "-"),
    ("E2 ψ⁺-hack ×1000",
     "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_psiHack_m1000_r0.02_cycle91_Nf81_real_fracture",
     "#1F77B4", "-"),
]

UMAX_SWEEP = [
    ("Umax=0.09",
     "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N400_R0.0_Umax0.09",
     "#9467BD", "-"),
    ("Umax=0.10",
     "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N350_R0.0_Umax0.1",
     "#2CA02C", "-"),
    ("Umax=0.11",
     "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N250_R0.0_Umax0.11",
     "#17BECF", "-"),
    ("Umax=0.12",
     "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12",
     "k", "-"),
]


def make_4panel(group, title, fname, log_y_psi=False):
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), tight_layout=True)
    panels = [
        (axes[0, 0], "alpha_bar_max",  r"$\bar{\alpha}_{\max}$",                    True),
        (axes[0, 1], "psi_max",        r"$\psi^+_{\max}$ (raw, single-elem peak)", log_y_psi),
        (axes[1, 0], "int_gpsi_l0",    r"$\int_{B_{\ell_0}} g(\alpha)\,\psi^+\,d\Omega$  (active driver)", True),
        (axes[1, 1], "int_fpsi_l0",    r"$\int_{B_{\ell_0}} f(\bar{\alpha})\,\psi^+\,d\Omega$  (fatigue-weighted)", True),
    ]
    for label, archive, color, ls in group:
        arr = load_archive(HERE / archive)
        if arr is None:
            print(f"  [missing data] {label}")
            continue
        cyc = arr[:, COLS["cycle"]]
        for ax, key, _, _ in panels:
            y = arr[:, COLS[key]]
            mask = np.isfinite(y) & (y > 0 if key.startswith("int_") else True)
            ax.plot(cyc[mask], y[mask], color=color, linestyle=ls,
                    linewidth=1.6, label=label, alpha=0.9)
    for ax, _, ylabel, log_y in panels:
        ax.set_xlabel("cycle N")
        ax.set_ylabel(ylabel)
        if log_y:
            ax.set_yscale("log")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, loc="best")
    fig.suptitle(title, fontsize=12)
    out_dir = HERE / "figures" / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / fname
    fig.savefig(p, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {p.relative_to(HERE.parent)}")


def write_summary_csv():
    fout = HERE / "process_zone_summary.csv"
    cols = ["archive", "umax", "n_cyc", "last_cyc",
            "alpha_bar_max", "alpha_max", "psi_max",
            "int_psi_l0", "int_gpsi_l0", "int_fpsi_l0",
            "int_psi_2l0", "int_gpsi_2l0", "int_fpsi_2l0",
            "psi_top1pct", "gpsi_top1pct", "fpsi_top1pct",
            "pz_alpha_area", "pz_alphabar_area"]
    rows = []
    for f in sorted(HERE.glob("*/best_models/process_zone_metrics.npy")):
        name = f.parts[-3]
        arr = np.load(str(f))
        last = arr[-1]
        umax = ""
        for tok in name.split("_"):
            if tok.startswith("Umax"):
                umax = tok[4:]
                break
        rows.append([name, umax, len(arr), int(last[COLS["cycle"]]),
                     last[COLS["alpha_bar_max"]], last[COLS["alpha_max"]],
                     last[COLS["psi_max"]],
                     last[COLS["int_psi_l0"]], last[COLS["int_gpsi_l0"]],
                     last[COLS["int_fpsi_l0"]],
                     last[COLS["int_psi_2l0"]], last[COLS["int_gpsi_2l0"]],
                     last[COLS["int_fpsi_2l0"]],
                     last[COLS["psi_top1pct"]], last[COLS["gpsi_top1pct"]],
                     last[COLS["fpsi_top1pct"]],
                     last[COLS["pz_alpha_area"]], last[COLS["pz_alphabar_area"]]])
    with open(fout, "w") as fh:
        fh.write(",".join(cols) + "\n")
        for r in rows:
            fh.write(",".join(f"{v:.6e}" if isinstance(v, float) else str(v) for v in r) + "\n")
    print(f"\n→ {fout.relative_to(HERE.parent)}  ({len(rows)} archives)")


def main() -> int:
    print("Building method-comparison figure (Umax=0.12)…")
    make_4panel(METHOD_GROUP_U012,
                "Process-zone metrics — method comparison at Umax=0.12",
                "pz_method_comparison_Umax012.png")
    print("Building Umax-sweep figure (baseline coeff=1.0)…")
    make_4panel(UMAX_SWEEP,
                "Process-zone metrics — baseline coeff=1.0 Umax sweep",
                "pz_umax_sweep_baseline.png")
    print("Writing summary CSV…")
    write_summary_csv()
    return 0


if __name__ == "__main__":
    sys.exit(main())
