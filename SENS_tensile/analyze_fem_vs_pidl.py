#!/usr/bin/env python3
"""analyze_fem_vs_pidl.py — Phase 1 toy (Umax=0.12) FEM ref vs PIDL baseline vs SDF v1

Per user request (May 16):
  1. x_tip(N) vs FEM a_ell(N) — RMS + lead-lag (inverse-interpolated)
  2. ψ_peak / ψ_tip log-scale error vs FEM
  3. α-related scalars (α_max, alpha_bar_mean) vs FEM
  4. (separate script render_fem_vs_pidl_alpha.py) visual α at FEM snapshot cycles

CAUTION on definitions:
  - FEM 'a_ell' is an integrated crack-length-like measure (CSV col).
  - PIDL 'x_tip' is the ψ⁺ centroid tracker (frozen at fracture detection by design).
  - PIDL 'x_tip_alpha' is the α-front position tracker (jumps to 0.5 at fracture).
  These are NOT identical definitions. We plot all three side-by-side; RMS is
  a coarse summary only, never the headline.

FEM data:
  ~/Downloads/_pidl_handoff_v2/post_process/SENT_PIDL_12_timeseries.csv
  (82 cycles, columns include a_ell, alpha_max, psi_peak, psi_tip, Kt, ...)

Outputs:
  references_local/sdf_ribbon_smoke/fem_vs_pidl_4panel.png
"""
from __future__ import annotations
import csv
from pathlib import Path
import numpy as np
import scipy.io as sio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
FEM_CSV = Path.home() / "Downloads" / "_pidl_handoff_v2" / "post_process" / "SENT_PIDL_12_timeseries.csv"
FEM_SNAP_DIR = Path.home() / "Downloads" / "_pidl_handoff_v2" / "psi_snapshots_for_agent"
FEM_SNAP_CYCLES = [1, 40, 70, 82]   # cycles for which we have .mat snapshot ᾱ_max ground truth
BASE_REL = ("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
            "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
            "N300_R0.0_Umax0.12")
SDF_S1_REL = ("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
              "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
              "N100_R0.0_Umax0.12_sdfRibbon_eps0.001_uv_only")
SDF_S2_REL = ("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_2_"
              "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
              "N100_R0.0_Umax0.12_sdfRibbon_eps0.001_uv_only")


def find_baseline() -> Path:
    for n in range(0, 7):
        cand = HERE.parents[n] / "SENS_tensile" / BASE_REL if n > 0 else HERE / BASE_REL
        if (cand / "best_models").is_dir() and (cand / "best_models" / "alpha_bar_vs_cycle.npy").exists():
            return cand
    raise FileNotFoundError(f"baseline {BASE_REL} not found")


def load_pidl(archive: Path) -> dict:
    bm = archive / "best_models"
    ab = np.load(bm / "alpha_bar_vs_cycle.npy")        # (N, 3)
    kt = np.load(bm / "Kt_vs_cycle.npy")               # (N,)
    psi_p = bm / "psi_peak_vs_cycle.npy"
    psi = np.load(psi_p) if psi_p.exists() else None   # (N, 5) col1=max, col4=nominal
    # x_tip preference: alpha (physical front) over psi (tracker, freezes)
    xta_p = bm / "x_tip_alpha_vs_cycle.npy"
    xtp_p = bm / "x_tip_psi_vs_cycle.npy"
    xt_p  = bm / "x_tip_vs_cycle.npy"
    xta = np.load(xta_p) if xta_p.exists() else None
    xtp = np.load(xtp_p) if xtp_p.exists() else None
    xt  = np.load(xt_p)  if xt_p.exists()  else None
    return dict(alpha_bar_max=ab[:, 0], alpha_bar_mean=ab[:, 1],
                Kt=kt,
                psi_max=(psi[:, 1] if psi is not None else None),
                psi_nominal=(psi[:, 4] if psi is not None else None),
                x_tip_alpha=xta, x_tip_psi=xtp, x_tip=xt)


def load_fem(path: Path) -> dict:
    """Load FEM CSV time-series."""
    if not path.is_file():
        raise FileNotFoundError(path)
    rows = []
    with open(path, newline="") as f:
        rd = csv.DictReader(f)
        for row in rd:
            rows.append(row)
    out = {}
    for k in rows[0].keys():
        out[k] = np.array([float(r[k]) for r in rows])
    return out


def cycle_to_reach(arr: np.ndarray, target: float) -> float:
    bm = np.maximum.accumulate(arr)
    if target < bm[0] or target > bm[-1]:
        return float("nan")
    i = int(np.searchsorted(bm, target))
    if i == 0: return 0.0
    if i >= len(bm): return float(len(bm) - 1)
    x0, x1 = bm[i-1], bm[i]
    if x1 == x0: return float(i - 1)
    return float(i - 1 + (target - x0) / (x1 - x0))


def main():
    fem = load_fem(FEM_CSV)
    print(f"FEM: {len(fem['N'])} cycles, fracture at c{int(fem['N'][-1])}")

    base = load_pidl(find_baseline())
    sdf_s1 = load_pidl(HERE / SDF_S1_REL)
    sdf_s2 = load_pidl(HERE / SDF_S2_REL)

    # Truncate baseline view to ~max(FEM, SDF) = 90 cycles for visualization
    N_MAX = 90
    fem_n   = fem['N'].astype(int) - 1                 # FEM cycle index starts at N=1; rebase to 0
    fem_n_show = fem_n[fem_n < N_MAX]
    n_show     = N_MAX

    # ─── FIGURE: 2 × 2 panels ──────────────────────────────────────────
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))

    # ─── Panel 1: x_tip(N) vs FEM a_ell(N) ─────────────────────────────
    ax = axes[0, 0]
    ax.plot(fem_n, fem['a_ell'], "r-", lw=2.5, label="FEM a_ell")
    if base['x_tip_alpha'] is not None:
        ax.plot(np.arange(min(n_show, len(base['x_tip_alpha']))),
                base['x_tip_alpha'][:n_show], "k-", lw=2, label="baseline PIDL x_tip_alpha")
    elif base['x_tip'] is not None:
        ax.plot(np.arange(min(n_show, len(base['x_tip']))),
                base['x_tip'][:n_show], "k-", lw=2, label="baseline PIDL x_tip")
    for sdf, color, label in [(sdf_s1, "tab:blue", "SDF v1 s1"),
                              (sdf_s2, "tab:cyan", "SDF v1 s2")]:
        xt = sdf['x_tip_alpha'] if sdf['x_tip_alpha'] is not None else sdf['x_tip']
        ax.plot(np.arange(min(n_show, len(xt))), xt[:n_show], "-o",
                color=color, ms=3, lw=1.4, label=label)
    ax.set_xlabel("cycle N")
    ax.set_ylabel("crack length / tip position")
    ax.set_title("x_tip(N) vs FEM a_ell(N)\n"
                 "(definitions differ — visual side-by-side, see caveat)")
    ax.set_xlim(0, n_show)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9, loc="best")

    # RMS + lead-lag summary (caveat: different definitions)
    base_xt = base['x_tip_alpha'] if base['x_tip_alpha'] is not None else base['x_tip']
    sdf_xt  = sdf_s1['x_tip_alpha'] if sdf_s1['x_tip_alpha'] is not None else sdf_s1['x_tip']
    n_overlap = min(len(fem_n), len(base_xt), len(sdf_xt))
    if n_overlap > 0:
        x_b = base_xt[:n_overlap]
        x_s = sdf_xt[:n_overlap]
        a_fem = np.interp(np.arange(n_overlap), fem_n, fem['a_ell'])
        rms_b = float(np.sqrt(((x_b - a_fem)**2).mean()))
        rms_s = float(np.sqrt(((x_s - a_fem)**2).mean()))
        print(f"\n[Panel 1] RMS (caveat: different definitions)")
        print(f"  baseline x_tip vs FEM a_ell, c0..c{n_overlap-1}: RMS = {rms_b:.4f}")
        print(f"  SDF s1   x_tip vs FEM a_ell                  : RMS = {rms_s:.4f}")
        # lead-lag at intermediate cycles
        print(f"\n[Panel 1] lead-lag: cycle at which PIDL reaches FEM_a_ell(c)")
        for c in [20, 40, 60, 70]:
            if c < n_overlap:
                tgt = a_fem[c]
                cb = cycle_to_reach(x_b, tgt)
                cs = cycle_to_reach(x_s, tgt)
                print(f"  FEM c{c}: a_ell={tgt:.3f}  | baseline PIDL reaches at c{cb:.2f}  "
                      f"| SDF s1 PIDL reaches at c{cs:.2f}")

    # ─── Panel 2: ψ_peak log-scale vs FEM ──────────────────────────────
    ax = axes[0, 1]
    ax.plot(fem_n, fem['psi_peak'], "r-", lw=2.5, label="FEM ψ_peak (max)")
    ax.plot(fem_n, fem['psi_tip'],  "r--", lw=1.2, alpha=0.6, label="FEM ψ_tip")
    if base['psi_max'] is not None:
        ax.plot(np.arange(min(n_show, len(base['psi_max']))),
                base['psi_max'][:n_show], "k-", lw=2, label="baseline ψ_max")
    for sdf, color, label in [(sdf_s1, "tab:blue", "SDF s1"), (sdf_s2, "tab:cyan", "SDF s2")]:
        if sdf['psi_max'] is not None:
            ax.plot(np.arange(min(n_show, len(sdf['psi_max']))),
                    sdf['psi_max'][:n_show], "-o", color=color, ms=3, lw=1.4,
                    label=f"{label} ψ_max")
    ax.set_yscale("log")
    ax.set_xlabel("cycle N")
    ax.set_ylabel("ψ⁺ peak / tip")
    ax.set_title("ψ⁺ peak vs FEM (log scale)")
    ax.set_xlim(0, n_show)
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=8, loc="lower right")

    # log-error summary
    n_overlap = min(len(fem_n), len(base['psi_max']) if base['psi_max'] is not None else 0)
    if n_overlap > 0:
        fem_psi = np.interp(np.arange(n_overlap), fem_n, fem['psi_peak'])
        # element-switching noise at early cycles → restrict to c10..c60 healthy window
        c_lo, c_hi = 10, min(60, n_overlap)
        b_log = np.log10(np.clip(base['psi_max'][c_lo:c_hi], 1e-6, None))
        s_log = np.log10(np.clip(sdf_s1['psi_max'][c_lo:c_hi], 1e-6, None))
        f_log = np.log10(np.clip(fem_psi[c_lo:c_hi], 1e-6, None))
        print(f"\n[Panel 2] log10 ψ_peak gap to FEM (c10..c{c_hi-1} healthy window)")
        print(f"  baseline mean(log10 FEM/PIDL) = {(f_log - b_log).mean():.2f}  "
              f"(≈ {10**(f_log - b_log).mean():.0f}× under FEM)")
        print(f"  SDF s1   mean(log10 FEM/PIDL) = {(f_log - s_log).mean():.2f}  "
              f"(≈ {10**(f_log - s_log).mean():.0f}× under FEM)")
        print(f"  GAP CLOSURE: SDF brings ratio from {10**(f_log - b_log).mean():.0f}× → "
              f"{10**(f_log - s_log).mean():.0f}×")

    # ─── Panel 3: ᾱ_max (accumulated Carrara fatigue var) — apples-to-apples ──
    ax = axes[1, 0]
    # FEM ᾱ_max ground-truth scatter from per-cycle .mat snapshots (the variable that
    # PIDL's `alpha_bar_vs_cycle.npy[:,0]` is the analog of). CSV.alpha_max is NOT used:
    # that column holds the *instantaneous* α (Gauss-point max), a different Carrara
    # variable from the accumulated history ᾱ.
    fem_abar_max = []
    fem_abar_cyc = []
    for c in FEM_SNAP_CYCLES:
        p = FEM_SNAP_DIR / f"u12_cycle_{c:04d}.mat"
        if p.is_file():
            m = sio.loadmat(p)
            fem_abar_max.append(float(m['alpha_bar_elem'].max()))
            fem_abar_cyc.append(c - 1)   # rebase to 0-indexed cycle
    ax.scatter(fem_abar_cyc, fem_abar_max, marker="*", color="red", s=180,
               zorder=5, label="FEM ᾱ_max (mat snapshots)", edgecolors="darkred", lw=1)
    # FEM CSV alpha_bar_mean (per-cycle mean of ᾱ across domain) — different scalar
    # (mean vs max), shown as secondary reference for FEM trajectory shape.
    ax.plot(fem_n, fem['alpha_bar_mean'], "r--", lw=1.2, alpha=0.55,
            label="FEM ᾱ_mean (CSV, domain avg)")
    ax.plot(np.arange(min(n_show, len(base['alpha_bar_max']))),
            base['alpha_bar_max'][:n_show], "k-", lw=1.6, label="baseline ᾱ_max (PIDL)")
    for sdf, color, label in [(sdf_s1, "tab:blue", "SDF s1"), (sdf_s2, "tab:cyan", "SDF s2")]:
        ax.plot(np.arange(min(n_show, len(sdf['alpha_bar_max']))),
                sdf['alpha_bar_max'][:n_show], "-o", color=color, ms=3, lw=1.4,
                label=f"{label} ᾱ_max")
    ax.set_yscale("log")
    ax.set_xlabel("cycle N")
    ax.set_ylabel("ᾱ (accumulated Carrara fatigue var)")
    ax.set_title("ᾱ_max trajectory — APPLES-TO-APPLES\n"
                 "(α ≠ ᾱ: CSV.alpha_max is instantaneous; mat.alpha_bar is accumulated)")
    ax.set_xlim(0, n_show)
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=8, loc="best")

    # ᾱ_max gap summary at snapshot cycles
    if fem_abar_max:
        print(f"\n[Panel 3] ᾱ_max gap FEM vs PIDL (apples-to-apples, mat snapshot cycles)")
        base_ab = base['alpha_bar_max']
        sdf_ab  = sdf_s1['alpha_bar_max']
        for c, fa in zip(FEM_SNAP_CYCLES, fem_abar_max):
            i = c - 1
            b_val = float(base_ab[i]) if i < len(base_ab) else float("nan")
            s_val = float(sdf_ab[i])  if i < len(sdf_ab)  else float("nan")
            print(f"  c{c:02d}: FEM={fa:.2f}  baseline={b_val:.3f} (gap {fa/max(b_val,1e-9):.1f}×)  "
                  f"SDF s1={s_val:.3f} (gap {fa/max(s_val,1e-9):.1f}×)")

    # ─── Panel 4: Kt vs FEM Kt (log scale) ──────────────────────────────
    ax = axes[1, 1]
    ax.plot(fem_n, fem['Kt'], "r-", lw=2.5, label="FEM Kt")
    ax.plot(np.arange(min(n_show, len(base['Kt']))),
            base['Kt'][:n_show], "k-", lw=2, label="baseline Kt")
    for sdf, color, label in [(sdf_s1, "tab:blue", "SDF s1"), (sdf_s2, "tab:cyan", "SDF s2")]:
        ax.plot(np.arange(min(n_show, len(sdf['Kt']))),
                sdf['Kt'][:n_show], "-o", color=color, ms=3, lw=1.4,
                label=f"{label} Kt")
    ax.set_yscale("log")
    ax.set_xlabel("cycle N")
    ax.set_ylabel("Kt = max σ_xx / σ_far")
    ax.set_title("Kt vs FEM (log scale)\n"
                 "Note: PIDL c79-c89 are post-fracture cycles, see Audit Caveat 1")
    ax.set_xlim(0, n_show)
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=8, loc="lower right")

    fig.suptitle("Phase 1 toy Umax=0.12 — FEM ref vs PIDL baseline vs SDF v1 (uv_only ε=1e-3)",
                 fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.96))

    out_dir = HERE.parent / "references_local" / "sdf_ribbon_smoke"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_png = out_dir / "fem_vs_pidl_4panel.png"
    fig.savefig(out_png, dpi=130)
    print(f"\nsaved: {out_png}")


if __name__ == "__main__":
    main()
