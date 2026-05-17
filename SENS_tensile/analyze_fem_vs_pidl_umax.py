#!/usr/bin/env python3
"""analyze_fem_vs_pidl_umax.py — umax-parametrized FEM vs PIDL baseline vs SDF v1

Usage: python3 analyze_fem_vs_pidl_umax.py 0.08
       python3 analyze_fem_vs_pidl_umax.py 0.12

Inherits 4-panel layout + α≠ᾱ correction from analyze_fem_vs_pidl.py (May 17).
Differences:
  - umax-parametrized FEM CSV (`SENT_PIDL_{XX}_timeseries.csv`)
  - umax-parametrized snapshot cycles (mapped per available .mat)
  - baseline archive search EXTENDED to main-repo SENS_tensile (not just worktree)
  - psi_peak panel: if PIDL psi_peak_vs_cycle.npy missing, plots FEM-only with note
  - Kt panel: if PIDL Kt_vs_cycle.npy missing, plots FEM-only with note
"""
from __future__ import annotations
import argparse, csv, sys
from pathlib import Path
import numpy as np
import scipy.io as sio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
FEM_BASE = Path.home() / "Downloads" / "_pidl_handoff_v2"


# ─── umax-specific config ────────────────────────────────────────────────────
UMAX_CFG = {
    0.08: dict(
        fem_csv_tag="08",
        snap_cycles=[1, 150, 350, 396],
        baseline_rel=("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
                      "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
                      "N700_R0.0_Umax0.08"),
        sdf_rel=("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
                 "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
                 "N400_R0.0_Umax0.08_sdfRibbon_eps0.001_uv_only"),
        sdf_s2_rel=None,
        n_show=400,
    ),
    0.12: dict(
        fem_csv_tag="12",
        snap_cycles=[1, 40, 70, 82],
        baseline_rel=("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
                      "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
                      "N300_R0.0_Umax0.12"),
        sdf_rel=("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
                 "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
                 "N100_R0.0_Umax0.12_sdfRibbon_eps0.001_uv_only"),
        sdf_s2_rel=("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_2_"
                    "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
                    "N100_R0.0_Umax0.12_sdfRibbon_eps0.001_uv_only"),
        n_show=90,
    ),
}


def find_archive(rel: str) -> Path | None:
    """Search worktree SENS_tensile, then main-repo SENS_tensile."""
    candidates = [
        HERE / rel,
        Path("/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/SENS_tensile") / rel,
    ]
    for c in candidates:
        if (c / "best_models" / "alpha_bar_vs_cycle.npy").is_file():
            return c
    return None


def load_pidl(archive: Path | None) -> dict:
    if archive is None:
        return dict(alpha_bar_max=None, alpha_bar_mean=None, Kt=None,
                    psi_max=None, psi_nominal=None,
                    x_tip_alpha=None, x_tip_psi=None, x_tip=None)
    bm = archive / "best_models"
    def _opt(name):
        p = bm / name
        return np.load(p) if p.exists() else None
    ab = _opt("alpha_bar_vs_cycle.npy")
    psi = _opt("psi_peak_vs_cycle.npy")
    return dict(
        alpha_bar_max=(ab[:, 0] if ab is not None else None),
        alpha_bar_mean=(ab[:, 1] if ab is not None and ab.shape[1] > 1 else None),
        Kt=_opt("Kt_vs_cycle.npy"),
        psi_max=(psi[:, 1] if psi is not None else None),
        psi_nominal=(psi[:, 4] if psi is not None and psi.shape[1] > 4 else None),
        x_tip_alpha=_opt("x_tip_alpha_vs_cycle.npy"),
        x_tip_psi=_opt("x_tip_psi_vs_cycle.npy"),
        x_tip=_opt("x_tip_vs_cycle.npy"),
    )


def load_fem(path: Path) -> dict:
    rows = list(csv.DictReader(open(path)))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}


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


def main(umax: float):
    cfg = UMAX_CFG[umax]
    fem_csv = FEM_BASE / "post_process" / f"SENT_PIDL_{cfg['fem_csv_tag']}_timeseries.csv"
    fem_snap_dir = FEM_BASE / "psi_snapshots_for_agent"

    fem = load_fem(fem_csv)
    fem_n_raw = fem['N'].astype(int)
    fem_n = fem_n_raw - 1     # rebase 0-indexed
    print(f"FEM u={umax}: {len(fem_n)} cycles, last N={fem_n_raw[-1]}")

    base_path = find_archive(cfg["baseline_rel"])
    sdf_path  = find_archive(cfg["sdf_rel"])
    sdf_s2_path = find_archive(cfg["sdf_s2_rel"]) if cfg["sdf_s2_rel"] else None
    print(f"baseline: {base_path}")
    print(f"SDF s1:   {sdf_path}")
    if sdf_s2_path: print(f"SDF s2:   {sdf_s2_path}")

    base   = load_pidl(base_path)
    sdf_s1 = load_pidl(sdf_path)
    sdf_s2 = load_pidl(sdf_s2_path) if sdf_s2_path else None

    n_show = cfg["n_show"]
    snap_cycles = cfg["snap_cycles"]

    fig, axes = plt.subplots(2, 2, figsize=(15, 10))

    # ─── Panel 1: x_tip vs FEM a_ell ────────────────────────────────────────
    ax = axes[0, 0]
    ax.plot(fem_n, fem['a_ell'], "r-", lw=2.5, label="FEM a_ell")
    base_xt = base['x_tip_alpha'] if base['x_tip_alpha'] is not None else base['x_tip']
    sdf_xt  = sdf_s1['x_tip_alpha'] if sdf_s1['x_tip_alpha'] is not None else sdf_s1['x_tip']
    if base_xt is not None:
        ax.plot(np.arange(min(n_show, len(base_xt))), base_xt[:n_show], "k-", lw=2,
                label="baseline PIDL x_tip")
    if sdf_xt is not None:
        ax.plot(np.arange(min(n_show, len(sdf_xt))), sdf_xt[:n_show], "-o",
                color="tab:blue", ms=3, lw=1.4, label="SDF v1 s1")
    if sdf_s2 and (sdf_s2['x_tip_alpha'] is not None or sdf_s2['x_tip'] is not None):
        s2xt = sdf_s2['x_tip_alpha'] if sdf_s2['x_tip_alpha'] is not None else sdf_s2['x_tip']
        ax.plot(np.arange(min(n_show, len(s2xt))), s2xt[:n_show], "-o",
                color="tab:cyan", ms=3, lw=1.4, label="SDF v1 s2")
    ax.set_xlabel("cycle N"); ax.set_ylabel("crack length / tip position")
    ax.set_title(f"x_tip(N) vs FEM a_ell(N) — Umax={umax}")
    ax.set_xlim(0, n_show); ax.grid(alpha=0.3); ax.legend(fontsize=9, loc="best")

    # lead-lag summary
    if base_xt is not None and sdf_xt is not None:
        n_ov = min(len(fem_n), len(base_xt), len(sdf_xt))
        if n_ov > 0:
            a_fem = np.interp(np.arange(n_ov), fem_n, fem['a_ell'])
            x_b, x_s = base_xt[:n_ov], sdf_xt[:n_ov]
            rms_b = float(np.sqrt(((x_b - a_fem)**2).mean()))
            rms_s = float(np.sqrt(((x_s - a_fem)**2).mean()))
            print(f"\n[Panel 1 u={umax}] RMS x_tip vs FEM a_ell, c0..c{n_ov-1}")
            print(f"  baseline: RMS = {rms_b:.4f}")
            print(f"  SDF s1:   RMS = {rms_s:.4f}")
            n_fem_last = len(fem_n) - 1
            print(f"[Panel 1] lead-lag at FEM cycles:")
            sample_cycles = [int(0.25*n_fem_last), int(0.5*n_fem_last),
                             int(0.75*n_fem_last), n_fem_last]
            for c in sample_cycles:
                if 0 <= c < n_ov:
                    tgt = a_fem[c]
                    cb = cycle_to_reach(x_b, tgt)
                    cs = cycle_to_reach(x_s, tgt)
                    print(f"  FEM c{c}: a_ell={tgt:.3f}  | baseline @ c{cb:.1f}  | SDF s1 @ c{cs:.1f}")

    # ─── Panel 2: ψ_peak log scale ──────────────────────────────────────────
    ax = axes[0, 1]
    ax.plot(fem_n, fem['psi_peak'], "r-", lw=2.5, label="FEM ψ_peak")
    ax.plot(fem_n, fem['psi_tip'],  "r--", lw=1.2, alpha=0.6, label="FEM ψ_tip")
    plotted_pidl = False
    if base['psi_max'] is not None:
        ax.plot(np.arange(min(n_show, len(base['psi_max']))),
                base['psi_max'][:n_show], "k-", lw=2, label="baseline ψ_max")
        plotted_pidl = True
    if sdf_s1['psi_max'] is not None:
        ax.plot(np.arange(min(n_show, len(sdf_s1['psi_max']))),
                sdf_s1['psi_max'][:n_show], "-o", color="tab:blue", ms=3, lw=1.4,
                label="SDF s1 ψ_max")
        plotted_pidl = True
    if not plotted_pidl:
        ax.text(0.5, 0.5, "(PIDL ψ_peak .npy not yet computed —\nrun recompute_psi_peak.py first)",
                ha="center", va="center", transform=ax.transAxes, color="gray", fontsize=10)
    ax.set_yscale("log"); ax.set_xlabel("cycle N"); ax.set_ylabel("ψ⁺ peak / tip")
    ax.set_title(f"ψ⁺ peak vs FEM (log scale) — Umax={umax}")
    ax.set_xlim(0, n_show); ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8, loc="lower right")

    # log-error summary
    if base['psi_max'] is not None and sdf_s1['psi_max'] is not None:
        n_ov = min(len(fem_n), len(base['psi_max']), len(sdf_s1['psi_max']))
        if n_ov > 0:
            fem_psi = np.interp(np.arange(n_ov), fem_n, fem['psi_peak'])
            c_lo = 10
            c_hi = min(int(0.7 * fem_n[-1]), n_ov)
            b_log = np.log10(np.clip(base['psi_max'][c_lo:c_hi], 1e-6, None))
            s_log = np.log10(np.clip(sdf_s1['psi_max'][c_lo:c_hi], 1e-6, None))
            f_log = np.log10(np.clip(fem_psi[c_lo:c_hi], 1e-6, None))
            print(f"\n[Panel 2 u={umax}] log10 ψ_peak gap (c{c_lo}..c{c_hi-1}, healthy)")
            print(f"  baseline mean(log FEM/PIDL) = {(f_log - b_log).mean():.2f}  (≈ {10**(f_log - b_log).mean():.0f}×)")
            print(f"  SDF s1   mean(log FEM/PIDL) = {(f_log - s_log).mean():.2f}  (≈ {10**(f_log - s_log).mean():.0f}×)")

    # ─── Panel 3: ᾱ_max apples-to-apples ────────────────────────────────────
    ax = axes[1, 0]
    fem_abar_max, fem_abar_cyc = [], []
    for c in snap_cycles:
        p = fem_snap_dir / f"u{cfg['fem_csv_tag']}_cycle_{c:04d}.mat"
        if p.is_file():
            m = sio.loadmat(p)
            fem_abar_max.append(float(m['alpha_bar_elem'].max()))
            fem_abar_cyc.append(c - 1)
    if fem_abar_max:
        ax.scatter(fem_abar_cyc, fem_abar_max, marker="*", color="red", s=180, zorder=5,
                   label="FEM ᾱ_max (mat)", edgecolors="darkred", lw=1)
    ax.plot(fem_n, fem['alpha_bar_mean'], "r--", lw=1.2, alpha=0.55,
            label="FEM ᾱ_mean (CSV)")
    if base['alpha_bar_max'] is not None:
        ax.plot(np.arange(min(n_show, len(base['alpha_bar_max']))),
                base['alpha_bar_max'][:n_show], "k-", lw=1.6, label="baseline ᾱ_max")
    if sdf_s1['alpha_bar_max'] is not None:
        ax.plot(np.arange(min(n_show, len(sdf_s1['alpha_bar_max']))),
                sdf_s1['alpha_bar_max'][:n_show], "-o", color="tab:blue", ms=3, lw=1.4,
                label="SDF s1 ᾱ_max")
    if sdf_s2 and sdf_s2['alpha_bar_max'] is not None:
        ax.plot(np.arange(min(n_show, len(sdf_s2['alpha_bar_max']))),
                sdf_s2['alpha_bar_max'][:n_show], "-o", color="tab:cyan", ms=3, lw=1.4,
                label="SDF s2 ᾱ_max")
    ax.set_yscale("log"); ax.set_xlabel("cycle N"); ax.set_ylabel("ᾱ (accumulated Carrara)")
    ax.set_title(f"ᾱ_max apples-to-apples — Umax={umax}\n(α ≠ ᾱ caveat: CSV.α is instantaneous, mat.ᾱ is accumulated)")
    ax.set_xlim(0, n_show); ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8, loc="best")

    if fem_abar_max and base['alpha_bar_max'] is not None and sdf_s1['alpha_bar_max'] is not None:
        print(f"\n[Panel 3 u={umax}] ᾱ_max gap FEM vs PIDL (mat snapshot cycles)")
        for c, fa in zip(snap_cycles, fem_abar_max):
            i = c - 1
            b_val = float(base['alpha_bar_max'][i]) if i < len(base['alpha_bar_max']) else float("nan")
            s_val = float(sdf_s1['alpha_bar_max'][i]) if i < len(sdf_s1['alpha_bar_max']) else float("nan")
            print(f"  c{c:03d}: FEM={fa:.2f}  base={b_val:.3f} ({fa/max(b_val,1e-9):.1f}×)  "
                  f"SDF={s_val:.3f} ({fa/max(s_val,1e-9):.1f}×)")

    # ─── Panel 4: Kt log scale ──────────────────────────────────────────────
    ax = axes[1, 1]
    ax.plot(fem_n, fem['Kt'], "r-", lw=2.5, label="FEM Kt")
    if base['Kt'] is not None:
        ax.plot(np.arange(min(n_show, len(base['Kt']))),
                base['Kt'][:n_show], "k-", lw=2, label="baseline Kt")
    if sdf_s1['Kt'] is not None:
        ax.plot(np.arange(min(n_show, len(sdf_s1['Kt']))),
                sdf_s1['Kt'][:n_show], "-o", color="tab:blue", ms=3, lw=1.4, label="SDF s1 Kt")
    if sdf_s2 and sdf_s2['Kt'] is not None:
        ax.plot(np.arange(min(n_show, len(sdf_s2['Kt']))),
                sdf_s2['Kt'][:n_show], "-o", color="tab:cyan", ms=3, lw=1.4, label="SDF s2 Kt")
    ax.set_yscale("log"); ax.set_xlabel("cycle N"); ax.set_ylabel("Kt")
    ax.set_title(f"Kt vs FEM (log scale) — Umax={umax}")
    ax.set_xlim(0, n_show); ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8, loc="lower right")

    fig.suptitle(f"FEM ref vs PIDL baseline vs SDF v1 — Umax = {umax}", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.96))

    out_dir = HERE.parent / "references_local" / "sdf_ribbon_smoke"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_png = out_dir / f"fem_vs_pidl_4panel_u{int(umax*100):02d}.png"
    fig.savefig(out_png, dpi=130)
    print(f"\nsaved: {out_png}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("umax", type=float, choices=sorted(UMAX_CFG.keys()))
    args = p.parse_args()
    main(args.umax)
