#!/usr/bin/env python3
"""
plot_umax_init_coeff_sweep.py — D-framework dose-response figure
across (init_coeff, Umax) pair.

After `run_mit4_umax_sweep.sh` produces 10 trajectory_*.npz files
(5 coeff=1.0 baseline × 5 Umax + 5 coeff=3.0 × 5 Umax), this script
builds:

  Panel A: ᾱ_max final vs Umax (2 lines: coeff=1, coeff=3)
            shows ᾱ_max NOT a flat ceiling but Umax-dependent.
  Panel B: active-driver g·ψ⁺_raw (mid-N_f mean) vs Umax
            tests whether "method-invariant 0.4" holds.
  Panel C: N_f vs Umax (S-N curve), with FEM reference.
  Panel D: ratio ᾱ_max(coeff=3) / ᾱ_max(coeff=1) vs Umax
            quantifies init_coeff sensitivity (Hit 1 reframe).
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).parent

# Map Umax → (coeff=1 archive suffix, coeff=3 archive suffix)
ARCHIVE_MAP = {
    0.08: ("_N700_R0.0_Umax0.08", "_N600_R0.0_Umax0.08"),
    0.09: ("_N400_R0.0_Umax0.09", "_N500_R0.0_Umax0.09"),
    0.10: ("_N350_R0.0_Umax0.1",  "_N400_R0.0_Umax0.1"),
    0.11: ("_N250_R0.0_Umax0.11", "_N300_R0.0_Umax0.11"),
    0.12: ("_N300_R0.0_Umax0.12", "_N300_R0.0_Umax0.12"),
}

# FEM reference (per memory: SENT_PIDL_12_timeseries_full.csv + sweep summary)
FEM_NF = {0.08: 396, 0.09: 254, 0.10: 170, 0.11: 117, 0.12: 82}

COL = {"cycle": 0, "B_psi_deg": 7, "B_psi_raw": 6, "B_alpha": 8}


def find_npz(suffix: str, coeff_prefix: str = "") -> Path:
    """Find trajectory npz file. coeff_prefix can be 'coeff1' or 'coeff3' to
    disambiguate same-Umax cases that share suffix tail."""
    if coeff_prefix:
        candidates = list(HERE.glob(f"trajectory_{coeff_prefix}_*{suffix[-30:]}.npz"))
        if candidates:
            return sorted(candidates, key=lambda p: p.stat().st_mtime)[-1]
    # fallback: any matching trajectory_* with that suffix that ISN'T the
    # opposite-coeff variant
    other = "coeff3" if coeff_prefix == "coeff1" else "coeff1"
    candidates = [p for p in HERE.glob(f"trajectory_*{suffix[-30:]}.npz")
                  if other not in p.name]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.stat().st_mtime)[-1]


def load_archive(coeff: str, umax: float):
    suffix = ARCHIVE_MAP[umax][0 if coeff == "1.0" else 1]
    coeff_prefix = "coeff1" if coeff == "1.0" else "coeff3"
    npz_path = find_npz(suffix, coeff_prefix)
    if npz_path is None:
        return None
    z = np.load(str(npz_path))
    arr = z["data"]
    abar = z["alpha_bar_vs_cycle"]
    return {
        "cycles": arr[:, COL["cycle"]],
        "B_psi_deg": arr[:, COL["B_psi_deg"]],
        "B_psi_raw": arr[:, COL["B_psi_raw"]],
        "B_alpha": arr[:, COL["B_alpha"]],
        "abar_max": abar[:, 0] if abar.ndim > 1 else abar,
        "n_cycles_saved": len(arr),
        "abar_final_max": float((abar[:, 0] if abar.ndim > 1 else abar).max()),
    }


def main():
    umaxes = sorted(ARCHIVE_MAP.keys())
    results = {coeff: {} for coeff in ("1.0", "3.0")}
    for coeff in ("1.0", "3.0"):
        for u in umaxes:
            d = load_archive(coeff, u)
            if d is not None:
                results[coeff][u] = d
                print(f"  coeff={coeff} Umax={u}: ᾱ_max={d['abar_final_max']:.2f}, "
                      f"n_save={d['n_cycles_saved']}")
            else:
                print(f"  coeff={coeff} Umax={u}: NPZ NOT FOUND")

    fig, axes = plt.subplots(2, 2, figsize=(13, 9), tight_layout=True)

    # Panel A: ᾱ_max final vs Umax (semilog y)
    ax = axes[0, 0]
    for coeff, marker, color in [("1.0", "o-", "#0B4992"), ("3.0", "s--", "#C0282A")]:
        xs, ys = [], []
        for u in umaxes:
            if u in results[coeff]:
                xs.append(u)
                ys.append(results[coeff][u]["abar_final_max"])
        ax.semilogy(xs, ys, marker, color=color, linewidth=2, markersize=8,
                    label=f"PIDL coeff={coeff}")
    ax.axhline(958, color="black", ls=":", alpha=0.5, label="FEM ᾱ_max(82)=958")
    ax.set_xlabel("U_max"); ax.set_ylabel("ᾱ_max final (log)")
    ax.set_title("(A) ᾱ_max vs U_max — NOT a flat ceiling")
    ax.legend(fontsize=9, loc="best"); ax.grid(alpha=0.3)
    ax.invert_xaxis()  # S-N convention: low Umax = right side

    # Panel B: active-driver g·ψ⁺_raw mid-N_f mean
    ax = axes[0, 1]
    for coeff, marker, color in [("1.0", "o-", "#0B4992"), ("3.0", "s--", "#C0282A")]:
        xs, ys = [], []
        for u in umaxes:
            if u in results[coeff]:
                d = results[coeff][u]
                # mean of B_psi_deg across mid-cycle (skip first/last 10%)
                n = len(d["B_psi_deg"])
                mid = d["B_psi_deg"][n // 10: 9 * n // 10]
                xs.append(u)
                ys.append(float(mid.mean()))
        ax.plot(xs, ys, marker, color=color, linewidth=2, markersize=8,
                label=f"PIDL coeff={coeff}")
    ax.axhline(0.4, color="gray", ls=":", alpha=0.6, label="invariant ~0.4 (claim)")
    ax.set_xlabel("U_max"); ax.set_ylabel("g·ψ⁺_raw at active driver (mean mid-life)")
    ax.set_title("(B) Active driver — does method-invariance hold across U_max?")
    ax.legend(fontsize=9, loc="best"); ax.grid(alpha=0.3)
    ax.invert_xaxis()

    # Panel C: S-N curve (N_f vs Umax)
    ax = axes[1, 0]
    fem_xs = [u for u in umaxes if u in FEM_NF]
    fem_ys = [FEM_NF[u] for u in fem_xs]
    ax.semilogy(fem_xs, fem_ys, "k^-", linewidth=2, markersize=10,
                label="FEM (reference)")
    for coeff, marker, color in [("1.0", "o-", "#0B4992"), ("3.0", "s--", "#C0282A")]:
        xs, ys = [], []
        for u in umaxes:
            if u in results[coeff]:
                xs.append(u)
                ys.append(results[coeff][u]["n_cycles_saved"])
        ax.semilogy(xs, ys, marker, color=color, linewidth=2, markersize=8,
                    label=f"PIDL coeff={coeff}")
    ax.set_xlabel("U_max"); ax.set_ylabel("N_f (log)")
    ax.set_title("(C) S-N curves — PIDL vs FEM")
    ax.legend(fontsize=9, loc="best"); ax.grid(alpha=0.3)
    ax.invert_xaxis()

    # Panel D: init_coeff ratio
    ax = axes[1, 1]
    xs, ratios = [], []
    for u in umaxes:
        if u in results["1.0"] and u in results["3.0"]:
            r = results["3.0"][u]["abar_final_max"] / results["1.0"][u]["abar_final_max"]
            xs.append(u)
            ratios.append(r)
    ax.plot(xs, ratios, "o-", color="purple", linewidth=2, markersize=10)
    ax.axhline(1.0, color="black", ls="--", alpha=0.5, label="no change")
    ax.set_xlabel("U_max")
    ax.set_ylabel("ᾱ_max(coeff=3) / ᾱ_max(coeff=1)")
    ax.set_title("(D) init_coeff sensitivity on ᾱ_max — Hit 1 reframe")
    ax.legend(fontsize=9, loc="best"); ax.grid(alpha=0.3)
    ax.invert_xaxis()

    out_dir = HERE / "figures" / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_path = out_dir / "framework_umax_init_coeff_sweep.png"
    fig.savefig(fig_path, dpi=140)
    print(f"\n→ saved {fig_path}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
