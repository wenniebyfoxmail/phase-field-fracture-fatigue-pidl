#!/usr/bin/env python3
"""
compare_umax_sweep.py — Cross-U_max comparison: FEM vs PIDL baseline across
all 5 U_max (0.08, 0.09, 0.10, 0.11, 0.12), plus Williams/Fourier/Enriched
as single markers at U_max=0.12.

Figures generated (in figures/compare_umax/):
    fig_SN_curve.png              — N_f vs U_max (log-log), power-law fit
    fig_Kt_cycle1_vs_Umax.png     — Kt at cycle 1 (geometry-driven constancy check)
    fig_f_mean_at_Nf_vs_Umax.png  — degradation mean at fracture (FEM trend)
    fig_alpha_max_at_Nf_vs_Umax.png — peak damage at fracture (log scale)
    fig_summary_4panel_umax.png   — 2x2 combined
Plus summary_umax_sweep.txt with the numerical table.

Data sources:
    FEM: ~/Downloads/post_process/SENT_PIDL_{08..12}_timeseries.csv (14-col)
    PIDL baseline: hl_8_Neurons_400_*_Umax0.{08,09,11,12}/  (0.10 missing)
    PIDL Williams v4, Fourier v1, Enriched v1: all at U_max=0.12 only
"""
from __future__ import annotations
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
U_MAX_LIST = [0.08, 0.09, 0.10, 0.11, 0.12]

FEM_CSV_DIR = Path.home() / "Downloads" / "post_process"
FEM_CSV_FMT = "SENT_PIDL_{:02d}_timeseries.csv"


# -----------------------------------------------------------------------------
# Loaders
# -----------------------------------------------------------------------------

def load_fem_at(umax: float) -> dict | None:
    suffix = int(round(umax * 100))
    p = FEM_CSV_DIR / FEM_CSV_FMT.format(suffix)
    if not p.exists():
        return None
    df = pd.read_csv(p)
    # N_f = cycle of max da_dN
    if "da_dN" in df.columns:
        nf_idx = df["da_dN"].idxmax()
    else:
        nf_idx = len(df) - 1
    nf = int(df["N"].iloc[nf_idx])
    row_nf = df.iloc[nf_idx]
    row_c1 = df[df["N"] == 1].iloc[0] if (df["N"] == 1).any() else df.iloc[0]
    out = {
        "U_max": umax, "N_f": nf,
        "Kt_cycle1": float(row_c1.get("Kt", np.nan)),
        "alpha_max_Nf": float(row_nf["alpha_max"]),
        "alpha_bar_mean_Nf": float(row_nf.get("alpha_bar_mean", np.nan)),
        "f_min_Nf": float(row_nf["f_min"]),
        "f_mean_Nf": float(row_nf.get("f_mean", np.nan)),
        "E_el_Nf": float(row_nf["E_el"]),
        "a_ell_Nf": float(row_nf["a_ell"]),
    }
    return out


def _find_baseline_dir(umax: float) -> Path | None:
    """Find baseline 8x400 dir for given U_max. Prefer coeff_1.0, exclude
    williams / fourier / enriched / tipw / mono variants."""
    u_tag = f"Umax{umax}"
    candidates = []
    for d in HERE.iterdir():
        if not d.is_dir() or "hl_8_Neurons_400" not in d.name:
            continue
        if "coeff_1.0" not in d.name:
            continue
        if not d.name.endswith(u_tag):
            continue
        candidates.append(d)
    if not candidates:
        return None
    # Prefer one with full data
    for c in candidates:
        if (c / "best_models" / "alpha_bar_vs_cycle.npy").exists():
            return c
    return candidates[0]


def load_pidl_at(umax: float) -> dict | None:
    d = _find_baseline_dir(umax)
    if d is None:
        return None
    bm = d / "best_models"
    ab = np.load(bm / "alpha_bar_vs_cycle.npy") if (bm / "alpha_bar_vs_cycle.npy").exists() else None
    ee = np.load(bm / "E_el_vs_cycle.npy") if (bm / "E_el_vs_cycle.npy").exists() else None
    xtip = np.load(bm / "x_tip_vs_cycle.npy") if (bm / "x_tip_vs_cycle.npy").exists() else None
    kt = np.load(bm / "Kt_vs_cycle.npy") if (bm / "Kt_vs_cycle.npy").exists() else None
    fmean = np.load(bm / "f_mean_vs_cycle.npy") if (bm / "f_mean_vs_cycle.npy").exists() else None

    # N_f: first cycle where x_tip >= 0.5, else last saved
    if xtip is not None and (xtip >= 0.5).any():
        nf = int(np.argmax(xtip >= 0.5))
    elif ee is not None and len(ee) > 10:
        e_ref = ee[:len(ee) // 4].max()
        mask = ee < 0.2 * e_ref
        idx = np.where(mask)[0]
        idx = idx[idx > 5]
        nf = int(idx[0]) if len(idx) > 0 else len(ee) - 1
    else:
        nf = len(ee) - 1 if ee is not None else 0

    # f_mean @ N_f (from file, col 1). Row = f_mean[:,0]==nf
    f_mean_nf = np.nan
    if fmean is not None:
        row = fmean[fmean[:, 0].astype(int) == nf]
        if len(row) > 0:
            f_mean_nf = float(row[0, 1])
        elif nf < len(fmean):
            f_mean_nf = float(fmean[nf, 1])

    return {
        "U_max": umax,
        "dir": d.name,
        "N_f": nf,
        "Kt_cycle1": float(kt[0]) if kt is not None and len(kt) > 0 else np.nan,
        "alpha_max_Nf": float(ab[nf, 0]) if ab is not None and nf < len(ab) else np.nan,
        "alpha_mean_Nf": float(ab[nf, 1]) if ab is not None and nf < len(ab) else np.nan,
        "f_min_Nf": float(ab[nf, 2]) if ab is not None and nf < len(ab) else np.nan,
        "f_mean_Nf": f_mean_nf,
        "E_el_Nf": float(ee[nf]) if ee is not None and nf < len(ee) else np.nan,
    }


def load_archive_at_012(tag_substr: str, label: str) -> dict | None:
    """Load archived Williams v4 / Fourier / Enriched at U_max=0.12."""
    for d in HERE.iterdir():
        if d.is_dir() and tag_substr in d.name and "Umax0.12" in d.name:
            bm = d / "best_models"
            if not bm.exists():
                continue
            ab = np.load(bm / "alpha_bar_vs_cycle.npy") if (bm / "alpha_bar_vs_cycle.npy").exists() else None
            ee = np.load(bm / "E_el_vs_cycle.npy") if (bm / "E_el_vs_cycle.npy").exists() else None
            kt = np.load(bm / "Kt_vs_cycle.npy") if (bm / "Kt_vs_cycle.npy").exists() else None
            fmean = np.load(bm / "f_mean_vs_cycle.npy") if (bm / "f_mean_vs_cycle.npy").exists() else None
            # Parse _NfXX_
            import re
            m = re.search(r"_Nf(\d+)_", d.name)
            nf = int(m.group(1)) if m else (len(ee) - 1 if ee is not None else 0)

            f_mean_nf = np.nan
            if fmean is not None:
                row = fmean[fmean[:, 0].astype(int) == nf]
                if len(row) > 0:
                    f_mean_nf = float(row[0, 1])

            return {
                "label": label,
                "U_max": 0.12,
                "dir": d.name,
                "N_f": nf,
                "Kt_cycle1": float(kt[0]) if kt is not None and len(kt) > 0 else np.nan,
                "alpha_max_Nf": float(ab[nf, 0]) if ab is not None and nf < len(ab) else np.nan,
                "alpha_mean_Nf": float(ab[nf, 1]) if ab is not None and nf < len(ab) else np.nan,
                "f_min_Nf": float(ab[nf, 2]) if ab is not None and nf < len(ab) else np.nan,
                "f_mean_Nf": f_mean_nf,
                "E_el_Nf": float(ee[nf]) if ee is not None and nf < len(ee) else np.nan,
            }
    return None


# -----------------------------------------------------------------------------
# Plotting helpers
# -----------------------------------------------------------------------------

COLOR = {
    "FEM": "#D62728", "Baseline": "#1F77B4",
    "Williams v4": "#9467BD", "Fourier v1": "#FF7F0E",
    "Enriched v1": "#2CA02C",
}
MARKER_012 = {"Williams v4": "s", "Fourier v1": "^", "Enriched v1": "D"}


def _fit_power_law(umaxs, nfs):
    """Fit N_f = C * U_max^p, return (C, p)."""
    log_u = np.log(np.array(umaxs))
    log_nf = np.log(np.array(nfs))
    p, logC = np.polyfit(log_u, log_nf, 1)
    return np.exp(logC), p


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> int:
    outdir = HERE / "figures" / "compare_umax"
    outdir.mkdir(parents=True, exist_ok=True)

    # Load all
    fem_list = []
    pidl_list = []
    for u in U_MAX_LIST:
        f = load_fem_at(u)
        if f is not None:
            fem_list.append(f)
            print(f"✅ FEM  @ {u}: N_f={f['N_f']}, Kt_c1={f['Kt_cycle1']:.2f}, "
                  f"α_max={f['alpha_max_Nf']:.1f}, f_mean={f['f_mean_Nf']:.3f}")
        p = load_pidl_at(u)
        if p is not None:
            pidl_list.append(p)
            kt1 = f"{p['Kt_cycle1']:.2f}" if not np.isnan(p['Kt_cycle1']) else "—"
            print(f"✅ PIDL @ {u}: N_f={p['N_f']}, Kt_c1={kt1}, "
                  f"α_max={p['alpha_max_Nf']:.1f}, f_mean={p['f_mean_Nf']:.3f}")
        else:
            print(f"⚠️  PIDL @ {u}: no data")

    extras = []
    for tag, label in [("williams_std_v4_", "Williams v4"),
                       ("fourier_nf16", "Fourier v1"),
                       ("enriched_ansatz_modeI_v1", "Enriched v1")]:
        e = load_archive_at_012(tag, label)
        if e is not None:
            extras.append(e)
            print(f"✅ {label} @ 0.12: N_f={e['N_f']}, α_max={e['alpha_max_Nf']:.2f}, "
                  f"f_mean={e['f_mean_Nf']:.3f}")

    # ----- Figure 1: S-N curve (log-log) -----
    fig, ax = plt.subplots(figsize=(7, 5))
    if fem_list:
        us = [d["U_max"] for d in fem_list]
        nf = [d["N_f"] for d in fem_list]
        ax.loglog(us, nf, "o-", color=COLOR["FEM"], lw=2, ms=7, label="FEM")
        C, p = _fit_power_law(us, nf)
        u_fit = np.logspace(np.log10(min(us)), np.log10(max(us)), 50)
        ax.loglog(u_fit, C * u_fit**p, "--", color=COLOR["FEM"], alpha=0.4,
                  label=f"FEM fit: $N_f = {C:.3f} \\cdot U_{{max}}^{{{p:.2f}}}$")
    if pidl_list:
        us = [d["U_max"] for d in pidl_list]
        nf = [d["N_f"] for d in pidl_list]
        ax.loglog(us, nf, "s-", color=COLOR["Baseline"], lw=2, ms=7,
                  label="PIDL baseline 8x400")
        C, p = _fit_power_law(us, nf)
        ax.loglog(u_fit, C * u_fit**p, "--", color=COLOR["Baseline"], alpha=0.4,
                  label=f"PIDL fit: $N_f = {C:.3f} \\cdot U_{{max}}^{{{p:.2f}}}$")
    for e in extras:
        ax.loglog([e["U_max"]], [e["N_f"]], MARKER_012[e["label"]],
                  color=COLOR[e["label"]], ms=10, label=e["label"])
    ax.set_xlabel("$U_{max}$")
    ax.set_ylabel("$N_f$ (cycles to fracture)")
    ax.set_title("S-N curve — FEM vs PIDL baseline\n(Williams/Fourier/Enriched at U_max=0.12 only)")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(outdir / "fig_SN_curve.png", dpi=200)
    plt.close(fig)

    # ----- Figure 2: Kt @ cycle 1 vs U_max -----
    fig, ax = plt.subplots(figsize=(7, 5))
    if fem_list:
        us = [d["U_max"] for d in fem_list]
        k1 = [d["Kt_cycle1"] for d in fem_list]
        ax.plot(us, k1, "o-", color=COLOR["FEM"], lw=2, ms=7, label="FEM")
    if pidl_list:
        us = [d["U_max"] for d in pidl_list if not np.isnan(d["Kt_cycle1"])]
        k1 = [d["Kt_cycle1"] for d in pidl_list if not np.isnan(d["Kt_cycle1"])]
        if us:
            ax.plot(us, k1, "s-", color=COLOR["Baseline"], lw=2, ms=7,
                    label="PIDL baseline (where Kt saved)")
    for e in extras:
        if not np.isnan(e["Kt_cycle1"]):
            ax.plot([e["U_max"]], [e["Kt_cycle1"]], MARKER_012[e["label"]],
                    color=COLOR[e["label"]], ms=10, label=e["label"])
    ax.set_xlabel("$U_{max}$")
    ax.set_ylabel("$K_t$ at cycle 1")
    ax.set_title("Initial stress concentration (cycle 1) — geometry vs load magnitude\n"
                 "FEM: ~constant ≈ 11 (geometry-driven)")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(outdir / "fig_Kt_cycle1_vs_Umax.png", dpi=200)
    plt.close(fig)

    # ----- Figure 3: f_mean @ N_f vs U_max -----
    fig, ax = plt.subplots(figsize=(7, 5))
    if fem_list:
        us = [d["U_max"] for d in fem_list]
        fm = [d["f_mean_Nf"] for d in fem_list]
        ax.plot(us, fm, "o-", color=COLOR["FEM"], lw=2, ms=7, label="FEM")
    if pidl_list:
        us = [d["U_max"] for d in pidl_list if not np.isnan(d["f_mean_Nf"])]
        fm = [d["f_mean_Nf"] for d in pidl_list if not np.isnan(d["f_mean_Nf"])]
        ax.plot(us, fm, "s-", color=COLOR["Baseline"], lw=2, ms=7, label="PIDL baseline")
    for e in extras:
        if not np.isnan(e["f_mean_Nf"]):
            ax.plot([e["U_max"]], [e["f_mean_Nf"]], MARKER_012[e["label"]],
                    color=COLOR[e["label"]], ms=10, label=e["label"])
    ax.set_xlabel("$U_{max}$")
    ax.set_ylabel("$f_{mean}$ at $N_f$")
    ax.set_title("Domain-avg degradation at fracture\n"
                 "FEM: dispersion-to-concentration trend (low $U_{max}$ → more dispersed)")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(outdir / "fig_f_mean_at_Nf_vs_Umax.png", dpi=200)
    plt.close(fig)

    # ----- Figure 4: α_max @ N_f vs U_max (log) -----
    fig, ax = plt.subplots(figsize=(7, 5))
    if fem_list:
        us = [d["U_max"] for d in fem_list]
        am = [d["alpha_max_Nf"] for d in fem_list]
        ax.semilogy(us, am, "o-", color=COLOR["FEM"], lw=2, ms=7, label="FEM")
    if pidl_list:
        us = [d["U_max"] for d in pidl_list]
        am = [d["alpha_max_Nf"] for d in pidl_list]
        ax.semilogy(us, am, "s-", color=COLOR["Baseline"], lw=2, ms=7,
                    label="PIDL baseline")
    for e in extras:
        ax.semilogy([e["U_max"]], [e["alpha_max_Nf"]], MARKER_012[e["label"]],
                    color=COLOR[e["label"]], ms=10, label=e["label"])
    ax.set_xlabel("$U_{max}$")
    ax.set_ylabel(r"$\bar{\alpha}_{\max}$ at $N_f$  [log]")
    ax.set_title("Peak damage accumulator at fracture (log scale)\n"
                 "FEM 100× PIDL at high U_max, gap shrinks at low U_max")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(outdir / "fig_alpha_max_at_Nf_vs_Umax.png", dpi=200)
    plt.close(fig)

    # ----- Figure 5: 4-panel combined -----
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))

    # (0,0) S-N
    ax = axes[0, 0]
    if fem_list:
        us = [d["U_max"] for d in fem_list]; nf = [d["N_f"] for d in fem_list]
        ax.loglog(us, nf, "o-", color=COLOR["FEM"], lw=2, ms=6, label="FEM")
        C, p = _fit_power_law(us, nf)
        ax.loglog(us, [C * u**p for u in us], "--", color=COLOR["FEM"], alpha=0.3)
    if pidl_list:
        us = [d["U_max"] for d in pidl_list]; nf = [d["N_f"] for d in pidl_list]
        ax.loglog(us, nf, "s-", color=COLOR["Baseline"], lw=2, ms=6, label="PIDL baseline")
        C, p = _fit_power_law(us, nf)
        ax.loglog(us, [C * u**p for u in us], "--", color=COLOR["Baseline"], alpha=0.3)
    for e in extras:
        ax.loglog([e["U_max"]], [e["N_f"]], MARKER_012[e["label"]],
                  color=COLOR[e["label"]], ms=9, label=e["label"])
    ax.set_xlabel("$U_{max}$"); ax.set_ylabel("$N_f$"); ax.set_title("(a) S-N curve")
    ax.legend(fontsize=7); ax.grid(alpha=0.3, which="both")

    # (0,1) Kt cycle 1
    ax = axes[0, 1]
    if fem_list:
        us = [d["U_max"] for d in fem_list]; k1 = [d["Kt_cycle1"] for d in fem_list]
        ax.plot(us, k1, "o-", color=COLOR["FEM"], lw=2, ms=6, label="FEM")
    for e in extras:
        if not np.isnan(e["Kt_cycle1"]):
            ax.plot([e["U_max"]], [e["Kt_cycle1"]], MARKER_012[e["label"]],
                    color=COLOR[e["label"]], ms=9, label=e["label"])
    ax.set_xlabel("$U_{max}$"); ax.set_ylabel("$K_t$ @ cycle 1")
    ax.set_title("(b) Initial Kt — geometry-driven")
    ax.legend(fontsize=7); ax.grid(alpha=0.3)

    # (1,0) f_mean @ N_f
    ax = axes[1, 0]
    if fem_list:
        us = [d["U_max"] for d in fem_list]; fm = [d["f_mean_Nf"] for d in fem_list]
        ax.plot(us, fm, "o-", color=COLOR["FEM"], lw=2, ms=6, label="FEM")
    if pidl_list:
        us = [d["U_max"] for d in pidl_list if not np.isnan(d["f_mean_Nf"])]
        fm = [d["f_mean_Nf"] for d in pidl_list if not np.isnan(d["f_mean_Nf"])]
        ax.plot(us, fm, "s-", color=COLOR["Baseline"], lw=2, ms=6, label="PIDL baseline")
    for e in extras:
        if not np.isnan(e["f_mean_Nf"]):
            ax.plot([e["U_max"]], [e["f_mean_Nf"]], MARKER_012[e["label"]],
                    color=COLOR[e["label"]], ms=9, label=e["label"])
    ax.set_xlabel("$U_{max}$"); ax.set_ylabel("$f_{mean}$ @ $N_f$")
    ax.set_title("(c) Bulk degradation at fracture")
    ax.legend(fontsize=7); ax.grid(alpha=0.3)

    # (1,1) α_max @ N_f (log)
    ax = axes[1, 1]
    if fem_list:
        us = [d["U_max"] for d in fem_list]; am = [d["alpha_max_Nf"] for d in fem_list]
        ax.semilogy(us, am, "o-", color=COLOR["FEM"], lw=2, ms=6, label="FEM")
    if pidl_list:
        us = [d["U_max"] for d in pidl_list]; am = [d["alpha_max_Nf"] for d in pidl_list]
        ax.semilogy(us, am, "s-", color=COLOR["Baseline"], lw=2, ms=6, label="PIDL baseline")
    for e in extras:
        ax.semilogy([e["U_max"]], [e["alpha_max_Nf"]], MARKER_012[e["label"]],
                    color=COLOR[e["label"]], ms=9, label=e["label"])
    ax.set_xlabel("$U_{max}$"); ax.set_ylabel(r"$\bar{\alpha}_{\max}$ @ $N_f$  [log]")
    ax.set_title("(d) Peak damage at fracture (log)")
    ax.legend(fontsize=7); ax.grid(alpha=0.3, which="both")

    fig.suptitle("Cross-U_max sweep: FEM vs PIDL — all methods at $N_f$",
                 y=1.00, fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(outdir / "fig_summary_4panel_umax.png", dpi=200)
    plt.close(fig)

    # ----- Summary table -----
    lines = []
    lines.append("=" * 95)
    lines.append("Cross-U_max summary — all methods at N_f")
    lines.append("=" * 95)
    header = (f"{'Method':<15s} {'U_max':>6} {'N_f':>5} {'Kt@c1':>8} {'α_max':>10} "
              f"{'α_mean':>8} {'f_mean':>8} {'f_min':>12}")
    lines.append(header)
    lines.append("-" * len(header))
    for d in fem_list:
        lines.append(f"{'FEM':<15s} {d['U_max']:>6.2f} {d['N_f']:>5} "
                     f"{d['Kt_cycle1']:>8.2f} {d['alpha_max_Nf']:>10.2f} "
                     f"{d['alpha_bar_mean_Nf']:>8.3f} {d['f_mean_Nf']:>8.4f} "
                     f"{d['f_min_Nf']:>12.4e}")
    lines.append("")
    for d in pidl_list:
        kt1 = f"{d['Kt_cycle1']:>8.2f}" if not np.isnan(d['Kt_cycle1']) else f"{'—':>8}"
        fm = f"{d['f_mean_Nf']:>8.4f}" if not np.isnan(d['f_mean_Nf']) else f"{'—':>8}"
        lines.append(f"{'PIDL baseline':<15s} {d['U_max']:>6.2f} {d['N_f']:>5} "
                     f"{kt1} {d['alpha_max_Nf']:>10.2f} "
                     f"{d['alpha_mean_Nf']:>8.3f} {fm} "
                     f"{d['f_min_Nf']:>12.4e}")
    lines.append("")
    for e in extras:
        kt1 = f"{e['Kt_cycle1']:>8.2f}" if not np.isnan(e['Kt_cycle1']) else f"{'—':>8}"
        fm = f"{e['f_mean_Nf']:>8.4f}" if not np.isnan(e['f_mean_Nf']) else f"{'—':>8}"
        lines.append(f"{e['label']:<15s} {e['U_max']:>6.2f} {e['N_f']:>5} "
                     f"{kt1} {e['alpha_max_Nf']:>10.2f} "
                     f"{e['alpha_mean_Nf']:>8.3f} {fm} "
                     f"{e['f_min_Nf']:>12.4e}")

    # Power law fits
    if fem_list:
        us = [d["U_max"] for d in fem_list]; nf = [d["N_f"] for d in fem_list]
        C, p = _fit_power_law(us, nf)
        lines.append("")
        lines.append(f"FEM S-N fit:  N_f = {C:.4f} * U_max ^ {p:.3f}")
    if pidl_list and len(pidl_list) >= 2:
        us = [d["U_max"] for d in pidl_list]; nf = [d["N_f"] for d in pidl_list]
        C, p = _fit_power_law(us, nf)
        lines.append(f"PIDL S-N fit: N_f = {C:.4f} * U_max ^ {p:.3f}")

    lines.append("")
    lines.append("KEY OBSERVATIONS:")
    lines.append("  1. FEM Kt @ cycle 1 ~ constant (~11) across U_max")
    lines.append("     → confirms stress concentration is GEOMETRY-driven, not load-driven")
    lines.append("  2. FEM f_mean @ N_f: 0.74 (U=0.12) → 0.33 (U=0.08)")
    lines.append("     Low U_max → more cycles → damage accumulates more uniformly → lower f_mean")
    lines.append("     High U_max → fewer cycles → concentrated at tip → higher f_mean")
    lines.append("  3. FEM α_max 100× PIDL at U=0.12, gap shrinks at low U_max (~24× at U=0.08)")
    lines.append("     Both accumulate more damage at low U_max but PIDL stays more dispersed")
    lines.append("  4. PIDL S-N exponent is SHALLOWER than FEM → underestimates more at low U_max")
    lines.append("  5. Williams v4 / Fourier / Enriched markers at U=0.12 show different N_f")
    lines.append("     but similar α_max floor (5-10), confirming input/output enrichment")
    lines.append("     alone cannot close the damage-accumulation gap (→ Direction 6).")

    (outdir / "summary_umax_sweep.txt").write_text("\n".join(lines))

    print(f"\n✅ Figures + summary: {outdir.name}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
