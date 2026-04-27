#!/usr/bin/env python3
"""
plot_J_integral_comparison.py — A1 cross-archive J / K_I figures.

Reads `J_integral.npy` from each archive and produces:

  1. figures/audit/J_method_comparison_Umax012.png
       2-panel: J(N), K_I(N) vs cycle, lines per method @ Umax=0.12.
       Path-independence: line per radius lightly shaded; bold line = r_2 (mid).

  2. figures/audit/J_umax_sweep_baseline.png
       Same 2-panel but lines = baseline coeff=1.0 Umax sweep.
       Demonstrates K_I ∝ Umax LEFM scaling (pristine regime).

  3. figures/audit/K_vs_Umax_LEFM.png
       1 panel: pristine-cycle K_I vs Umax. Linear regression line. R².
       Test the LEFM prediction K_I ∝ σ_∞ ∝ Umax.

  4. J_integral_summary.csv
       Per-archive row: archive | umax | n_pristine_cyc | K_I@c10 (r=0.08) | K_I@c30
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))


# Column index map (matches OUT_COLUMNS in compute_J_integral.py)
# ["cycle", "x_tip", "r_eff_0..r_eff_(R-1)", "J_r0..J_r(R-1)", "K_r0..K_r(R-1)"]
N_RADII = 3


def col_idx_J(ri):  return 2 + N_RADII + ri
def col_idx_K(ri):  return 2 + 2 * N_RADII + ri


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
    ("Umax=0.09", "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N400_R0.0_Umax0.09", "#9467BD"),
    ("Umax=0.10", "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N350_R0.0_Umax0.1",  "#2CA02C"),
    ("Umax=0.11", "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N250_R0.0_Umax0.11", "#17BECF"),
    ("Umax=0.12", "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12", "k"),
]


def load(archive_dir: Path):
    f = archive_dir / "best_models" / "J_integral.npy"
    return np.load(str(f)) if f.is_file() else None


def filter_pristine(arr):
    """Return rows where all three radii agree within 30% (path-independent regime).
    Excludes negative J (NN-damage artifact)."""
    if arr is None or len(arr) == 0:
        return arr
    Js = np.stack([arr[:, col_idx_J(i)] for i in range(N_RADII)], axis=1)
    valid = np.all(Js > 0, axis=1)
    if valid.sum() < 1:
        return arr[:0]
    # path-independence test on mid radius
    spread = np.abs(Js.max(axis=1) - Js.min(axis=1)) / np.maximum(Js.mean(axis=1), 1e-12)
    pristine = valid & (spread < 0.3)
    return arr[pristine]


def make_method_comparison(group, title, fname):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.0), tight_layout=True)
    for label, archive, color, ls in group:
        arr = load(HERE / archive)
        if arr is None:
            print(f"  [missing data] {label}")
            continue
        cyc = arr[:, 0]
        # Plot J(r0=0.05) faint, J(r1=0.08) bold (median radius)
        for ri, alpha in zip(range(N_RADII), [0.3, 1.0, 0.3]):
            J = arr[:, col_idx_J(ri)]
            K = arr[:, col_idx_K(ri)]
            mask = J > 0
            axes[0].plot(cyc[mask], J[mask], color=color, linestyle=ls,
                         linewidth=(2.0 if ri == 1 else 1.0),
                         alpha=alpha, label=label if ri == 1 else None)
            axes[1].plot(cyc[mask], K[mask], color=color, linestyle=ls,
                         linewidth=(2.0 if ri == 1 else 1.0),
                         alpha=alpha, label=label if ri == 1 else None)
    axes[0].set_xlabel("cycle N"); axes[0].set_ylabel(r"$J$  (path: r=0.08 bold; r=0.05/0.12 faint)")
    axes[0].set_yscale("log"); axes[0].grid(alpha=0.3); axes[0].legend(fontsize=9)
    axes[1].set_xlabel("cycle N"); axes[1].set_ylabel(r"$K_I = \sqrt{E\,J}$  (plane stress, $E=1$)")
    axes[1].grid(alpha=0.3); axes[1].legend(fontsize=9)
    fig.suptitle(title, fontsize=12)
    out_dir = HERE / "figures" / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / fname
    fig.savefig(p, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {p.relative_to(HERE.parent)}")


def make_umax_sweep_LEFM():
    """K_I @ early-cycle vs Umax — linear regression test of LEFM scaling."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), tight_layout=True)
    Umax_list, K_pristine = [], []
    for label, archive, color in UMAX_SWEEP:
        arr = load(HERE / archive)
        if arr is None:
            continue
        umax = float(label.split("=")[1])
        Umax_list.append(umax)
        # Take median K @ r=0.08 over first 5 pristine cycles (where x_tip <~ 0.05)
        pristine = filter_pristine(arr)
        first5 = pristine[:5] if len(pristine) >= 5 else pristine
        K_med = np.median(first5[:, col_idx_K(1)]) if len(first5) > 0 else np.nan
        K_pristine.append(K_med)
        # left panel: trajectory
        cyc = arr[:, 0]; K = arr[:, col_idx_K(1)]
        mask = K > 0
        axes[0].plot(cyc[mask], K[mask], color=color, linewidth=2.0, label=label)

    axes[0].set_xlabel("cycle N"); axes[0].set_ylabel(r"$K_I$ at r=0.08")
    axes[0].grid(alpha=0.3); axes[0].legend(fontsize=9)
    axes[0].set_title("$K_I(N)$ trajectory — baseline coeff=1.0, all Umax")

    Umax_arr = np.array(Umax_list)
    K_arr = np.array(K_pristine)
    valid = np.isfinite(K_arr)
    if valid.sum() >= 2:
        m, b = np.polyfit(Umax_arr[valid], K_arr[valid], 1)
        pred = m * Umax_arr[valid] + b
        ss_res = np.sum((K_arr[valid] - pred) ** 2)
        ss_tot = np.sum((K_arr[valid] - K_arr[valid].mean()) ** 2)
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
        # Through-origin slope (LEFM K_I = c·Umax exact)
        m_origin = float(np.dot(Umax_arr[valid], K_arr[valid])
                         / np.dot(Umax_arr[valid], Umax_arr[valid]))
        u_grid = np.linspace(0, max(Umax_arr) * 1.05, 50)
        axes[1].plot(u_grid, m * u_grid + b, "k--", alpha=0.5,
                     label=f"linear fit  K = {m:.2f}·U + {b:+.3f}  R²={r2:.3f}")
        axes[1].plot(u_grid, m_origin * u_grid, "k:",
                     label=f"through-origin  K = {m_origin:.2f}·U")
    for u, K, (label, _, color) in zip(Umax_arr, K_arr, UMAX_SWEEP):
        if np.isfinite(K):
            axes[1].scatter([u], [K], color=color, s=80, zorder=5, label=label)
    axes[1].set_xlabel(r"$U_{max}$"); axes[1].set_ylabel(r"$K_I$ (median, first 5 pristine cycles)")
    axes[1].set_title("LEFM scaling test:  $K_I \\propto U_{max}$ ?")
    axes[1].grid(alpha=0.3); axes[1].legend(fontsize=8, loc="best")
    out_dir = HERE / "figures" / "audit"
    p = out_dir / "K_vs_Umax_LEFM.png"
    fig.savefig(p, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {p.relative_to(HERE.parent)}")


def write_summary_csv():
    fout = HERE / "J_integral_summary.csv"
    cols = ["archive", "umax", "n_pristine_cyc", "K_first5_med",
            "K_first5_max", "K_last_pristine"]
    rows = []
    for f in sorted(HERE.glob("*/best_models/J_integral.npy")):
        name = f.parts[-3]
        arr = np.load(str(f))
        umax = ""
        for tok in name.split("_"):
            if tok.startswith("Umax"):
                umax = tok[4:]
                break
        pristine = filter_pristine(arr)
        if len(pristine) > 0:
            K = pristine[:, col_idx_K(1)]
            first5 = K[:min(5, len(K))]
            row = [name, umax, len(pristine), float(np.median(first5)),
                   float(first5.max()), float(K[-1])]
        else:
            row = [name, umax, 0, np.nan, np.nan, np.nan]
        rows.append(row)
    with open(fout, "w") as fh:
        fh.write(",".join(cols) + "\n")
        for r in rows:
            fh.write(",".join(f"{v:.6e}" if isinstance(v, float) else str(v) for v in r) + "\n")
    print(f"\n→ {fout.relative_to(HERE.parent)}  ({len(rows)} archives)")


def main():
    print("Building method-comparison J figure (Umax=0.12)…")
    make_method_comparison(METHOD_GROUP_U012,
                           "J / K_I — method comparison @ Umax=0.12",
                           "J_method_comparison_Umax012.png")
    print("Building Umax-sweep + LEFM-scaling figure…")
    make_umax_sweep_LEFM()
    print("Writing summary CSV…")
    write_summary_csv()
    return 0


if __name__ == "__main__":
    sys.exit(main())
