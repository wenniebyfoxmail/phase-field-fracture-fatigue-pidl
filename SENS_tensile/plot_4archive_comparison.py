#!/usr/bin/env python3
"""
plot_4archive_comparison.py — D-framework α-segment dose-response figure.

Loads 4 trajectory_*.npz files (baseline, Enriched v1, Enriched v2, E2 hack)
and plots active-driver and ᾱ_max trajectories in a 2x2 panel.

Headline finding to show:
  Panel A — active-driver g·ψ⁺_raw vs cycle: ALL 4 archives cluster around
            ~0.4 (method-invariant), confirming α-rep + ψ⁺ interventions
            don't change the active-driver dynamics.
  Panel B — ᾱ_max vs cycle: baseline ~9, Enriched ~10-11, E2 jumps to 457
            (frozen accumulator artifact at hack center).
  Panel C — active-driver x-coord vs cycle: all 4 track the advancing
            crack front (PIDL has spatial redistribution).
  Panel D — active-driver α vs cycle: stays ~0.7 throughout active fatigue
            (partially damaged element doing the accumulation).

Run after `run_mit4_all_archives.sh`.
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

# Try to use canonical paper style; fall back to defaults if unavailable.
try:
    from paper_style import apply_style, COLORS
    apply_style()
    METHOD_COLORS = {
        "baseline":     COLORS.get("Baseline", "#0B4992"),
        "enriched_v1":  COLORS.get("Enriched", "#C0282A"),
        "enriched_v2":  "#7E2A8A",  # purple - distinct from v1 red
        "e2_hack":      "#1A8B6C",  # teal
    }
except ImportError:
    METHOD_COLORS = {
        "baseline":    "tab:blue",
        "enriched_v1": "tab:red",
        "enriched_v2": "tab:purple",
        "e2_hack":     "tab:green",
    }

# Map method label → (display name, archive name suffix used by analyze_e2_trajectory)
ARCHIVES = [
    ("baseline",    "Baseline (no hack, no enrich)",
     "_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12"),
    ("enriched_v1", "Enriched Ansatz v1 (c_init=0.01)",
     "_enriched_ansatz_modeI_v1_cycle94_Nf84_real_fracture"),
    ("enriched_v2", "Enriched v2 STRONGER (c_init=0.1)",
     "_enriched_ansatz_modeI_v2_cinit0.1_rcut0.05"),
    ("e2_hack",     "E2 hack ψ⁺×1000 (warm-start)",
     "_psiHack_m1000_r0.02_cycle91_Nf81_real_fracture"),
]

# Column indices in the trajectory.npz `data` array
COL = {
    "cycle":       0,
    "A_psi_raw":   1, "A_psi_deg":   2, "A_alpha":   3, "A_g":   4, "A_psi_hack":  5,
    "B_psi_raw":   6, "B_psi_deg":   7, "B_alpha":   8, "B_g":   9, "B_psi_hack": 10,
    "C_psi_raw":  11, "C_psi_deg":  12, "C_alpha":  13, "C_g":  14, "C_psi_hack": 15,
    "near0_psi_raw": 16, "near0_psi_deg": 17, "near0_alpha": 18,
    "psi_raw_max": 19, "psi_deg_max": 20, "psi_with_hack_max": 21,
    "A_x": 22, "A_y": 23, "B_x": 24, "B_y": 25, "C_x": 26, "C_y": 27,
}


def find_npz(suffix: str) -> Path:
    """Find a trajectory_*.npz file whose name ends with the given suffix."""
    candidates = list(HERE.glob(f"trajectory_*{suffix}.npz"))
    if not candidates:
        # try matching the last-80-char tag
        tag = suffix[-80:]
        candidates = list(HERE.glob(f"trajectory_*{tag}.npz"))
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.stat().st_mtime)[-1]


def main():
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), tight_layout=True)
    panels = {
        (0, 0): {"title": "(A) Active-driver g·ψ⁺_raw — METHOD-INVARIANT ≈ 0.4",
                 "ylabel": "g(α)·ψ⁺_raw at active driver", "log": True},
        (0, 1): {"title": "(B) ᾱ_max accumulation",
                 "ylabel": "ᾱ_max (whole field)", "log": True},
        (1, 0): {"title": "(C) Active-driver x-coord — tracks crack front",
                 "ylabel": "x of active driver", "log": False},
        (1, 1): {"title": "(D) α at active driver — partial damage zone",
                 "ylabel": "α at active driver", "log": False},
    }

    skipped = []
    for label, display, suffix in ARCHIVES:
        npz_path = find_npz(suffix)
        if npz_path is None:
            print(f"  WARN: no trajectory file for {label} (suffix='{suffix[-50:]}')")
            skipped.append(label)
            continue
        print(f"  loading {label}: {npz_path.name}")
        z = np.load(str(npz_path))
        arr = z["data"]
        abar = z["alpha_bar_vs_cycle"]
        cycles = arr[:, COL["cycle"]]
        color = METHOD_COLORS[label]

        # Panel A: active-driver g·ψ⁺_raw
        ax = axes[0, 0]
        ax.semilogy(cycles, arr[:, COL["B_psi_deg"]], "-o",
                    color=color, label=display, markersize=3, linewidth=1.5)
        # Panel B: ᾱ_max
        ax = axes[0, 1]
        if abar.ndim == 1:
            ax.semilogy(np.arange(len(abar)), abar, "-o",
                        color=color, label=display, markersize=3, linewidth=1.5)
        else:
            ax.semilogy(np.arange(len(abar)), abar[:, 0], "-o",
                        color=color, label=display, markersize=3, linewidth=1.5)
        # Panel C: B_x (active driver x-coord)
        ax = axes[1, 0]
        ax.plot(cycles, arr[:, COL["B_x"]], "-o",
                color=color, label=display, markersize=3, linewidth=1.5)
        # Panel D: B_alpha
        ax = axes[1, 1]
        ax.plot(cycles, arr[:, COL["B_alpha"]], "-o",
                color=color, label=display, markersize=3, linewidth=1.5)

    # FEM reference lines
    axes[0, 0].axhline(0.4, color="gray", ls=":", alpha=0.6,
                       label="method-invariant ~0.4")
    axes[0, 1].axhline(958, color="black", ls="--", alpha=0.6,
                       label="FEM ᾱ_max = 958")
    axes[1, 0].axhline(0.0, color="gray", ls=":", alpha=0.4)
    axes[1, 1].axhline(0.7, color="gray", ls=":", alpha=0.4,
                       label="α ≈ 0.7 zone")

    for (i, j), cfg in panels.items():
        ax = axes[i, j]
        ax.set_xlabel("cycle N")
        ax.set_ylabel(cfg["ylabel"])
        ax.set_title(cfg["title"])
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, loc="best")

    out_dir = HERE / "figures" / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_path = out_dir / "framework_4archive_active_driver.png"
    fig.savefig(fig_path, dpi=140)
    print(f"\n→ saved {fig_path}")
    if skipped:
        print(f"  (skipped: {skipped})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
