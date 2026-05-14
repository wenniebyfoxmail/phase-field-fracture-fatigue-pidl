#!/usr/bin/env python3
"""plot_sdf_ribbon_trajectories.py — c0..c4 trajectory comparison plot

Renders a 2x2 panel comparing baseline (c0..c5) vs 4 SDF ribbon variants:
  - α_bar_max(c)
  - Kt(c)
  - ψ_tip(c)   (= psi_peak_vs_cycle.npy col 1, "max")
  - x_tip(c)

Saves PNG to references_local/sdf_ribbon_N5_trajectories.png (gitignored).

Usage:
    python3 plot_sdf_ribbon_trajectories.py
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
BASE_REL = ("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
            "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
            "N300_R0.0_Umax0.12")
TAG = ("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_{seed}_"
       "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
       "N5_R0.0_Umax0.12_sdfRibbon_eps{eps}_uv_only")


def find_baseline(here: Path) -> Path:
    for n in range(0, 7):
        cand = here.parents[n] / "SENS_tensile" / BASE_REL if n > 0 else here / BASE_REL
        if (cand / "best_models").is_dir() and (cand / "best_models" / "alpha_bar_vs_cycle.npy").exists():
            return cand
    raise FileNotFoundError(f"baseline {BASE_REL!r} not found from {here}")


def load_archive(path: Path):
    bm = path / "best_models"
    ab = np.load(bm / "alpha_bar_vs_cycle.npy")
    kt = np.load(bm / "Kt_vs_cycle.npy")
    psi_p = bm / "psi_peak_vs_cycle.npy"
    psi = np.load(psi_p) if psi_p.exists() else None
    xt_p = (bm / "x_tip_psi_vs_cycle.npy")
    if not xt_p.exists():
        xt_p = bm / "x_tip_alpha_vs_cycle.npy"
    if not xt_p.exists():
        xt_p = bm / "x_tip_vs_cycle.npy"
    xt = np.load(xt_p) if xt_p.exists() else None
    return dict(alpha_bar_max=ab[:, 0], Kt=kt,
                psi_tip=(psi[:, 1] if psi is not None else None),
                x_tip=xt)


def main():
    here = HERE
    base_path = find_baseline(here)
    print(f"baseline: {base_path.name}")

    # Define the 4 ribbon runs
    runs = [
        dict(label="ε=5e-4 s1",  color="tab:purple",   eps="0.0005", seed=1),
        dict(label="ε=1e-3 s1",  color="tab:blue",     eps="0.001",  seed=1),
        dict(label="ε=1e-3 s2",  color="tab:cyan",     eps="0.001",  seed=2),
        dict(label="ε=2e-3 s1",  color="tab:orange",   eps="0.002",  seed=1),
    ]
    for r in runs:
        p = here / TAG.format(seed=r["seed"], eps=r["eps"])
        r["path"] = p
        r["data"] = load_archive(p) if p.is_dir() else None
        if r["data"] is None:
            print(f"  MISSING {p.name}")

    base = load_archive(base_path)
    N_BASE = 6                                # show c0..c5 of baseline

    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    metrics = [
        ("alpha_bar_max", "α̅_max  (peak element history)",  axes[0, 0]),
        ("Kt",            "Kt = max σxx / σfar",             axes[0, 1]),
        ("psi_tip",       "ψ⁺ peak (max over elements)",     axes[1, 0]),
        ("x_tip",         "x_tip  (crack tip x)",            axes[1, 1]),
    ]
    for key, title, ax in metrics:
        # Baseline first (thick black)
        if base[key] is not None:
            ax.plot(range(N_BASE), base[key][:N_BASE], "k-",
                    label="baseline", lw=2.4)
        for r in runs:
            if r["data"] is None or r["data"][key] is None:
                continue
            y = r["data"][key]
            ax.plot(range(len(y)), y, "-o", color=r["color"],
                    label=r["label"], lw=1.6, ms=4)
        ax.set_title(title)
        ax.set_xlabel("cycle")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, loc="best")

    fig.suptitle("SDF ribbon (uv_only) v1 — N=5 smoke trajectory vs baseline  "
                 "[u=0.12, seed=1 unless noted]", fontsize=12)
    fig.tight_layout()

    out_dir = here.parents[0] / "references_local" / "sdf_ribbon_smoke"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_png = out_dir / "trajectories_N5.png"
    fig.savefig(out_png, dpi=120)
    print(f"saved: {out_png}")

    # Also print numeric end-of-run table for inclusion in handover docs
    print()
    print(f"{'archive':<28} | α̅_max(c4) | Kt(c4) | ψ_tip(c4) | x_tip(c4)")
    print("-" * 80)
    base_end = (
        base["alpha_bar_max"][4], base["Kt"][4],
        (base["psi_tip"][4] if base["psi_tip"] is not None else None),
        base["x_tip"][4],
    )
    print(f"{'baseline (c4)':<28} | {base_end[0]:8.4f}  | {base_end[1]:6.4f} | "
          f"{base_end[2]:8.4f}  | {base_end[3]:8.4f}")
    for r in runs:
        if r["data"] is None: continue
        d = r["data"]
        print(f"{r['label']:<28} | {d['alpha_bar_max'][-1]:8.4f}  | "
              f"{d['Kt'][-1]:6.4f} | "
              f"{(d['psi_tip'][-1] if d['psi_tip'] is not None else float('nan')):8.4f}  | "
              f"{d['x_tip'][-1]:8.4f}")


if __name__ == "__main__":
    main()
