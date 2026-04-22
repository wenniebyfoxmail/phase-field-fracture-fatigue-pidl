#!/usr/bin/env python3
"""
compare_kt_three_way.py — Three-way comparison: FEM vs Baseline PIDL vs Williams PIDL

Loads per-cycle data from all three sources and generates comparison figures
for Kt, alpha_max (fatigue damage accumulator), f_min, and E_el.

Usage:
    cd "upload code/SENS_tensile"
    python compare_kt_three_way.py [--umax 0.12] [--output figures/compare_kt/]

Outputs:
    figures/compare_kt/fig_Kt_vs_cycle.png       — 3-curve Kt trajectory
    figures/compare_kt/fig_alpha_max_vs_cycle.png — 3-curve damage accumulator
    figures/compare_kt/fig_f_min_vs_cycle.png    — 3-curve degradation at max point
    figures/compare_kt/fig_E_el_vs_cycle.png     — 3-curve elastic energy
    figures/compare_kt/fig_summary_4panel.png    — 2x2 combined figure
    figures/compare_kt/summary_table.txt         — numerical comparison at key cycles
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# -----------------------------------------------------------------------------
# Data sources
# -----------------------------------------------------------------------------

HERE = Path(__file__).parent

FEM_CSV_DIR_CANDIDATES = [
    Path.home() / "Downloads" / "post_process",
    Path.home() / "Downloads" / "post_process 2",
    Path.home() / "Downloads",
]

# U_max -> FEM CSV suffix
FEM_CSV_SUFFIX = {"0.12": "12", "0.11": "11", "0.10": "10", "0.09": "09", "0.08": "08"}


def find_fem_csv(umax: str) -> Path | None:
    suffix = FEM_CSV_SUFFIX.get(umax)
    if suffix is None:
        return None
    # Prefer "_full" variant (has Kt, f_mean, psi_peak columns) over basic one
    for d in FEM_CSV_DIR_CANDIDATES:
        p = d / f"SENT_PIDL_{suffix}_timeseries_full.csv"
        if p.exists():
            return p
    for d in FEM_CSV_DIR_CANDIDATES:
        p = d / f"SENT_PIDL_{suffix}_timeseries.csv"
        if p.exists():
            return p
    return None


def find_pidl_dir(umax: str, flavor: str) -> Path | None:
    """flavor in {'baseline', 'williams_v3', 'williams_v4', 'williams_v4_current',
                  'fourier_v1', 'enriched_v1',
                  'spAlphaT_broad', 'spAlphaT_narrow'}"""
    base = HERE
    umax_tag = f"Umax{umax}"
    dirs = [d for d in base.iterdir() if d.is_dir() and umax_tag in d.name
            and "hl_8_Neurons_400" in d.name and "coeff_1.0" in d.name]

    if flavor == "baseline":
        # Strictly: directory ends with "Umax{umax}" (no Williams, no tipw, etc.)
        matches = [d for d in dirs if d.name.endswith(umax_tag)]
    elif flavor == "williams_v3":
        matches = [d for d in dirs if "williams_std_v3_cycle69" in d.name]
    elif flavor == "williams_v4":
        matches = [d for d in dirs if "williams_std_v4_" in d.name]
    elif flavor == "williams_v4_current":
        # fall back: in-progress run (not yet archived)
        matches = [d for d in dirs if d.name.endswith("williams_std")]
    elif flavor == "fourier_v1":
        # Fourier random-features Run #1 (n_freq=16, sigma=1.0, NN input dim 34)
        matches = [d for d in dirs if "fourier_nf16" in d.name]
    elif flavor == "enriched_v1":
        # ★ Direction 5: Enriched Ansatz Mode-I output enrichment
        # (c·χ(r)·F^I added to NN displacement output, x_tip FIXED at (0,0))
        matches = [d for d in dirs if "enriched_ansatz_modeI_v1" in d.name]
    elif flavor == "spAlphaT_broad":
        # ★ Direction 6.1 broad (β=0.5, r_T=0.1)
        # NEGATIVE: ᾱ_max=7.04 < baseline 9.09, N_f=76 < 80
        matches = [d for d in dirs if "spAlphaT_b0.5_r0.1" in d.name]
    elif flavor == "spAlphaT_narrow":
        # ★ Direction 6.1-narrow (β=0.8, r_T=0.03, element-scale)
        # NEGATIVE-but-better: ᾱ_max=7.55 (still < 9.09), N_f=80 ✓ recovered,
        # Peak Kt=30.2 top-10 / 35.2 max (close to Enriched 28.9)
        matches = [d for d in dirs if "spAlphaT_b0.8_r0.03" in d.name]
    else:
        matches = []
    if not matches:
        return None
    # Prefer the match that has Kt_vs_cycle.npy (full data for comparison)
    for m in matches:
        if (m / "best_models" / "Kt_vs_cycle.npy").exists():
            return m
    # Fallback: first match
    return matches[0]


def _detect_n_f(out: dict, dirname: str) -> tuple[int, str]:
    """Detect fracture cycle N_f for a PIDL run.

    Priority:
      1. Parse "_Nf{NN}_" from archived directory name (exact)
      2. First cycle where x_tip_use >= 0.5 (reached boundary)
      3. First cycle where E_el drops below 20% of early max (E_el collapse)
      4. Last available cycle (no fracture detected, e.g. false-stop run)
    """
    import re
    # 1. Archive name hint
    m = re.search(r"_Nf(\d+)_", dirname)
    if m:
        return int(m.group(1)), f"dir name _Nf{m.group(1)}_"
    # 2. x_tip boundary hit
    x = out.get("x_tip_use")
    if x is not None and len(x) > 0:
        mask = x >= 0.5
        if mask.any():
            return int(np.argmax(mask)), "x_tip≥0.5"
    # 3. E_el collapse (drop below 20% of 1st-quarter max)
    E = out.get("E_el")
    if E is not None and len(E) > 10:
        e_ref = float(E[:max(1, len(E)//4)].max())
        mask = E < 0.2 * e_ref
        # find the first drop after cycle 5 (avoid cycle-1 transients)
        idx_list = np.where(mask)[0]
        idx_list = idx_list[idx_list > 5]
        if len(idx_list) > 0:
            return int(idx_list[0]), "E_el drop"
    # 4. Fallback: last saved cycle
    return out.get("n_cycles", 1) - 1, "end of data"


def load_pidl(model_dir: Path, truncate_at_Nf: bool = True) -> dict | None:
    bm = model_dir / "best_models"
    out = {}
    for name, k in [("Kt_vs_cycle.npy", "Kt"),
                    ("E_el_vs_cycle.npy", "E_el"),
                    ("alpha_bar_vs_cycle.npy", "alpha_bar"),
                    ("f_mean_vs_cycle.npy", "f_mean_raw"),
                    ("psi_peak_vs_cycle.npy", "psi_peak_raw"),
                    ("x_tip_vs_cycle.npy", "x_tip"),
                    ("x_tip_psi_vs_cycle.npy", "x_tip_psi")]:
        f = bm / name
        if f.exists():
            out[k] = np.load(f)
    if not out:
        return None
    # alpha_bar has shape (N, 3): [max, mean, f_min]
    if "alpha_bar" in out and out["alpha_bar"].ndim == 2:
        out["alpha_max"] = out["alpha_bar"][:, 0]
        out["alpha_mean"] = out["alpha_bar"][:, 1]
        out["f_min"] = out["alpha_bar"][:, 2]
    # f_mean_raw shape (N, 4): [cycle_idx, f_mean, alpha_max, alpha_mean]
    if "f_mean_raw" in out and out["f_mean_raw"].ndim == 2:
        out["f_mean"] = out["f_mean_raw"][:, 1]
    # psi_peak_raw shape (N, 5): [cycle, max, top3, top10, nominal]
    if "psi_peak_raw" in out and out["psi_peak_raw"].ndim == 2:
        out["psi_peak"] = out["psi_peak_raw"][:, 1]
        out["psi_top3"] = out["psi_peak_raw"][:, 2]
        out["psi_top10"] = out["psi_peak_raw"][:, 3]
        out["psi_nominal"] = out["psi_peak_raw"][:, 4]
    # Unified x_tip: prefer psi-based for Williams, else alpha-based
    if "x_tip_psi" in out:
        out["x_tip_use"] = out["x_tip_psi"]
    elif "x_tip" in out:
        out["x_tip_use"] = out["x_tip"]
    out["n_cycles"] = len(out.get("Kt", out.get("E_el", [])))

    # Detect N_f and (optionally) truncate all array-valued fields at N_f (inclusive)
    n_f, src = _detect_n_f(out, model_dir.name)
    out["n_f"] = n_f
    out["n_f_source"] = src
    if truncate_at_Nf:
        keep = n_f + 1  # inclusive of fracture cycle
        for key, val in list(out.items()):
            if isinstance(val, np.ndarray) and val.ndim == 1 and len(val) > keep:
                out[key] = val[:keep]
            elif isinstance(val, np.ndarray) and val.ndim == 2 and val.shape[0] > keep:
                out[key] = val[:keep]
        out["n_cycles_truncated"] = keep
    return out


def load_fem(csv_path: Path, truncate_at_Nf: bool = True) -> dict:
    df = pd.read_csv(csv_path)
    # FEM CSV already ends at N_f (data collection stops at fracture).
    # max(da_dN) gives the fracture cycle.
    n_f = int(df["N"].iloc[df["da_dN"].idxmax()]) if "da_dN" in df.columns \
          else int(df["N"].iloc[-1])
    if truncate_at_Nf:
        df = df[df["N"] <= n_f].copy()
    out = {
        "N": df["N"].values,
        "E_el": df["E_el"].values,
        "alpha_max": df["alpha_max"].values,
        "f_min": df["f_min"].values,
        "a_ell": df["a_ell"].values,
        "d_max": df["d_max"].values,
        "N_f": n_f,
    }
    # New columns from "_full" CSV (Apr 18)
    for col in ["Kt", "f_mean", "alpha_bar_mean", "psi_peak", "psi_tip", "psi_nominal"]:
        if col in df.columns:
            out[col] = df[col].values
    return out


# -----------------------------------------------------------------------------
# Plotting
# -----------------------------------------------------------------------------

COLOR = {"FEM": "#D62728", "Baseline": "#1F77B4", "Williams v3": "#2CA02C",
         "Williams v4": "#9467BD", "Williams v4 (current)": "#8C564B",
         "Fourier v1": "#FF7F0E",     # orange — distinct from blue (Baseline) & purple (W v4)
         "Enriched v1": "#17BECF"}    # cyan — ★ Direction 5: output enrichment
LINESTYLE = {"FEM": "-", "Baseline": "-", "Williams v3": ":",
             "Williams v4": "-", "Williams v4 (current)": "--",
             "Fourier v1": "-.",      # dash-dot
             "Enriched v1": (0, (3, 1, 1, 1))}  # dash-dot-dot — Dir 5
LINEWIDTH = 1.8


def _add_series(ax, x, y, label, **kw):
    ax.plot(x, y, label=label, color=COLOR.get(label, "black"),
            linestyle=LINESTYLE.get(label, "-"), linewidth=LINEWIDTH, **kw)


def plot_Kt(series: dict, fem_series: dict, outpath: Path) -> None:
    """Kt(N) comparison — now uses real FEM Kt column if available."""
    fig, ax = plt.subplots(figsize=(8, 5.5))
    if fem_series is not None and "Kt" in fem_series:
        _add_series(ax, fem_series["N"], fem_series["Kt"], "FEM")
    for name, d in series.items():
        if "Kt" in d:
            _add_series(ax, np.arange(len(d["Kt"])), d["Kt"], name)
    ax.set_yscale("log")
    ax.set_xlabel("Cycle N")
    ax.set_ylabel("Kt = √(ψ⁺_tip / ψ⁺_nominal)   [log]")
    ax.set_title("Stress concentration factor Kt — three-way comparison (U_max=0.12)\n"
                 "(late-cycle explosion in all three is a numerical artifact "
                 "of ψ⁺_nominal → 0)")
    ax.legend(loc="best")
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(outpath, dpi=200)
    plt.close(fig)


def plot_log_metric(series: dict, fem_series: dict, key: str, ylabel: str,
                    title: str, outpath: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))
    # FEM
    if fem_series is not None and key in fem_series:
        _add_series(ax, fem_series["N"], np.abs(fem_series[key]) + 1e-20, "FEM")
    for name, d in series.items():
        if key in d:
            _add_series(ax, np.arange(len(d[key])), np.abs(d[key]) + 1e-20, name)
    ax.set_yscale("log")
    ax.set_xlabel("Cycle N")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(loc="best")
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(outpath, dpi=200)
    plt.close(fig)


def _panel_pidl_fem(ax, fem_series, fem_col, series, pidl_key,
                    ylabel, title, log=False):
    """Helper: plot FEM + all PIDL variants on one axis."""
    if fem_series is not None and fem_col in fem_series:
        _add_series(ax, fem_series["N"], fem_series[fem_col], "FEM")
    for name, d in series.items():
        if pidl_key in d:
            _add_series(ax, np.arange(len(d[pidl_key])), d[pidl_key], name)
    if log:
        ax.set_yscale("log")
    ax.set_xlabel("Cycle N")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=10)
    ax.legend(loc="best", fontsize=8)
    ax.grid(alpha=0.3, which="both" if log else "major")


def plot_summary_6panel(series: dict, fem_series: dict, outpath: Path) -> None:
    """2×3 layout with Kt, alpha_max, psi_peak, alpha_mean, f_min, f_mean.

    All series have been pre-truncated at their respective N_f in load_pidl /
    load_fem, so curves cleanly end at penetration point with no post-fracture
    numerical artifacts.
    """
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))

    # (a) Kt — all rise to similar values before fracture; curves end at N_f
    _panel_pidl_fem(axes[0, 0], fem_series, "Kt", series, "Kt",
                    "Kt  [log]",
                    "(a) Kt = √(ψ⁺_tip / ψ⁺_nom)\nall three rise; "
                    "curves truncated at N_f",
                    log=True)

    # (b) alpha_max — damage concentration at tip
    _panel_pidl_fem(axes[0, 1], fem_series, "alpha_max", series, "alpha_max",
                    r"$\bar{\alpha}_{\max}$  [log]",
                    "(b) Max damage accumulator\nFEM ≫ PIDL "
                    "(100× tip concentration)",
                    log=True)

    # (c) psi_peak — peak stress on 1 element (new Apr 17 metric)
    _panel_pidl_fem(axes[0, 2], fem_series, "psi_peak", series, "psi_peak",
                    "peak ψ⁺  [log]",
                    "(c) Peak ψ⁺ over all elements\n"
                    "Williams v4 has highest peak at mid-cycles",
                    log=True)

    # (d) alpha_mean — domain-average damage
    _panel_pidl_fem(axes[1, 0], fem_series, "alpha_bar_mean", series, "alpha_mean",
                    r"$\bar{\alpha}_{\mathrm{mean}}$",
                    "(d) Domain-avg damage accumulator\n"
                    "FEM accumulates ~2× more",
                    log=False)

    # (e) f_min — degradation at most damaged element
    _panel_pidl_fem(axes[1, 1], fem_series, "f_min", series, "f_min",
                    r"$f_{\min}$  [log]",
                    "(e) Degradation min (most broken)\n"
                    "FEM reaches 10⁻⁶ (complete break)",
                    log=True)

    # (f) f_mean — domain-average degradation (KEY corrected metric)
    _panel_pidl_fem(axes[1, 2], fem_series, "f_mean", series, "f_mean",
                    r"$f_{\mathrm{mean}}$",
                    "(f) Domain-avg degradation\n"
                    "FEM=0.74 at N_f (NOT 0.99) — more degraded than PIDL",
                    log=False)

    # N_f vertical markers on (d) and (f)
    for ax in [axes[1, 0], axes[1, 2]]:
        if fem_series is not None:
            ax.axvline(fem_series["N_f"], color=COLOR["FEM"], ls=":", alpha=0.4)
        for name, d in series.items():
            if "n_f" in d:
                ax.axvline(d["n_f"], color=COLOR.get(name, "black"),
                           ls=":", alpha=0.4)

    fig.suptitle("Three-way comparison at U_max=0.12 — "
                 "curves truncated at each method's N_f (penetration)",
                 y=1.00, fontsize=13, fontweight='bold')
    fig.tight_layout()
    fig.savefig(outpath, dpi=200)
    plt.close(fig)


def plot_summary_4panel(series: dict, fem_series: dict, fem_kt: float,
                        outpath: Path) -> None:
    """Legacy 4-panel (keep for backward compatibility)."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))

    # (0,0) Kt — now uses real FEM Kt if available
    ax = axes[0, 0]
    if fem_series is not None and "Kt" in fem_series:
        _add_series(ax, fem_series["N"], fem_series["Kt"], "FEM")
    else:
        ax.axhline(fem_kt, color=COLOR["FEM"], linestyle="-",
                   linewidth=LINEWIDTH, label=f"FEM (Kt={fem_kt}, quoted)")
    for name, d in series.items():
        if "Kt" in d:
            _add_series(ax, np.arange(len(d["Kt"])), d["Kt"], name)
    ax.set_xlabel("Cycle")
    ax.set_ylabel("Kt")
    ax.set_yscale("log")
    ax.set_title("(a) Stress concentration factor Kt [log]")
    ax.legend(loc="best", fontsize=9)
    ax.grid(alpha=0.3, which="both")

    # (0,1) alpha_max (log)
    ax = axes[0, 1]
    if fem_series is not None:
        _add_series(ax, fem_series["N"], fem_series["alpha_max"], "FEM")
    for name, d in series.items():
        if "alpha_max" in d:
            _add_series(ax, np.arange(len(d["alpha_max"])), d["alpha_max"], name)
    ax.set_yscale("log")
    ax.set_xlabel("Cycle")
    ax.set_ylabel(r"$\bar{\alpha}_{max}$ (damage accumulator)")
    ax.set_title("(b) Fatigue damage accumulation — FEM vs PIDL differ by 100x")
    ax.legend(loc="best", fontsize=9)
    ax.grid(alpha=0.3, which="both")

    # (1,0) f_min (log)
    ax = axes[1, 0]
    if fem_series is not None:
        _add_series(ax, fem_series["N"], fem_series["f_min"], "FEM")
    for name, d in series.items():
        if "f_min" in d:
            _add_series(ax, np.arange(len(d["f_min"])),
                        np.maximum(d["f_min"], 1e-10), name)
    ax.set_yscale("log")
    ax.set_xlabel("Cycle")
    ax.set_ylabel(r"$f_{min}$ (degradation at most-damaged element)")
    ax.set_title("(c) Degradation function minimum")
    ax.legend(loc="best", fontsize=9)
    ax.grid(alpha=0.3, which="both")

    # (1,1) E_el (log)
    ax = axes[1, 1]
    if fem_series is not None:
        _add_series(ax, fem_series["N"], fem_series["E_el"], "FEM")
    for name, d in series.items():
        if "E_el" in d:
            _add_series(ax, np.arange(len(d["E_el"])), d["E_el"], name)
    ax.set_yscale("log")
    ax.set_xlabel("Cycle")
    ax.set_ylabel(r"$E_{el}$ (elastic energy)")
    ax.set_title("(d) Elastic energy evolution")
    ax.legend(loc="best", fontsize=9)
    ax.grid(alpha=0.3, which="both")

    fig.suptitle(f"Three-way comparison at U_max=0.12 — FEM vs Baseline vs Williams PIDL",
                 fontsize=13, y=1.00)
    fig.tight_layout()
    fig.savefig(outpath, dpi=200)
    plt.close(fig)


def write_summary_table(series: dict, fem_series: dict, fem_kt: float,
                        outpath: Path) -> None:
    lines = []
    lines.append("=" * 85)
    lines.append(f"Three-way comparison summary @ U_max=0.12")
    lines.append("=" * 85)
    lines.append("")
    lines.append("Data sources:")
    for name, d in series.items():
        lines.append(f"  {name}: {d['n_cycles']} cycles, "
                     f"Kt final = {d.get('Kt', [float('nan')])[-1]:.3f}")
    lines.append(f"  FEM: {len(fem_series['N'])} cycles, "
                 f"N_f = {fem_series['N_f']}, Kt = {fem_kt} (stable)")
    lines.append("")

    # At matched cycles
    cycles_of_interest = [0, 10, 30, 50, 60, 70, "N_f"]
    lines.append("-" * 85)
    header = (f"{'Cycle':>5} | {'Method':>18} | {'Kt':>10} | {'α_max':>9} | "
              f"{'α_mean':>7} | {'f_min':>11} | {'f_mean':>7} | {'E_el':>11}")
    lines.append(header)
    lines.append("-" * len(header))
    for c in cycles_of_interest:
        # FEM
        idx = None
        if c == "N_f":
            cycle_fem = fem_series["N_f"]
            idx = np.argmax(fem_series["N"] == cycle_fem)
        elif isinstance(c, int):
            cycle_fem = c if c > 0 else 1
            mask = fem_series["N"] == cycle_fem
            idx = np.argmax(mask) if mask.any() else None
        if idx is not None:
            cf = fem_series
            kt_v = f"{cf['Kt'][idx]:.2f}" if 'Kt' in cf else f"{fem_kt}(q)"
            fmean_v = f"{cf['f_mean'][idx]:.4f}" if 'f_mean' in cf else "—"
            amean_v = f"{cf['alpha_bar_mean'][idx]:.3f}" if 'alpha_bar_mean' in cf else "—"
            lines.append(f"{cycle_fem:>5} | {'FEM':>18} | {kt_v:>10} | "
                         f"{cf['alpha_max'][idx]:>9.2f} | {amean_v:>7} | "
                         f"{cf['f_min'][idx]:>11.3e} | {fmean_v:>7} | "
                         f"{cf['E_el'][idx]:>11.3e}")
        # PIDL variants
        for name, d in series.items():
            idx_p = None
            # "effective" length after truncation
            n_eff = d.get("n_cycles_truncated", d["n_cycles"])
            if c == "N_f":
                # Prefer recorded N_f (from truncation logic)
                if "n_f" in d:
                    idx_p = min(d["n_f"], n_eff - 1)
                elif "x_tip_use" in d:
                    mask = d["x_tip_use"] >= 0.5
                    if mask.any():
                        idx_p = int(np.argmax(mask))
                    else:
                        idx_p = n_eff - 1
                else:
                    idx_p = n_eff - 1
            elif isinstance(c, int):
                idx_p = c if c < n_eff else None
            if idx_p is not None:
                kt_v = f"{d['Kt'][idx_p]:.2f}" if "Kt" in d else "NA"
                am_v = f"{d['alpha_max'][idx_p]:.2f}" if "alpha_max" in d else "NA"
                amean_v = f"{d['alpha_mean'][idx_p]:.3f}" if "alpha_mean" in d else "—"
                fmin_v = f"{d['f_min'][idx_p]:.3e}" if "f_min" in d else "NA"
                fmean_v = (f"{d['f_mean'][idx_p]:.4f}"
                           if "f_mean" in d and idx_p < len(d['f_mean']) else "—")
                ee_v = f"{d['E_el'][idx_p]:.3e}" if "E_el" in d else "NA"
                lines.append(f"{idx_p:>5} | {name:>18} | {kt_v:>10} | "
                             f"{am_v:>9} | {amean_v:>7} | {fmin_v:>11} | "
                             f"{fmean_v:>7} | {ee_v:>11}")
        lines.append("-" * len(header))

    lines.append("")
    lines.append("KEY FINDINGS (revised Apr 18 with new FEM 'full' CSV):")
    lines.append("")
    lines.append("  1. Kt is NOT stable in FEM. It rises from 11 (c1) to thousands")
    lines.append("     (c50+) — same numerical artifact as PIDL (ψ⁺_nominal → 0 as")
    lines.append("     far field degrades). The 'FEM Kt stable 15.3' memory claim")
    lines.append("     was incorrect; it's only ~11-15 for cycles 1-4.")
    lines.append("")
    lines.append("  2. α_max at N_f: FEM 958, Baseline 9.1, Williams 5.1.")
    lines.append("     FEM's peak damage is 100× higher — real concentration at tip.")
    lines.append("")
    lines.append("  3. f_mean at N_f: FEM 0.74, Baseline 0.85, Williams 0.86.")
    lines.append("     Contrary to the old 'FEM f_mean ≈ 0.99' claim, FEM has")
    lines.append("     MORE bulk degradation than PIDL (26% avg vs 14%).")
    lines.append("")
    lines.append("  4. N_f: FEM 82, Baseline 80 (-2.4%), Williams 77 (-6.1%),")
    lines.append("     Fourier 84 (+2.4%). Fourier has the smallest |ΔN_f| from FEM")
    lines.append("     among PIDL methods, but with opposite sign vs baseline.")
    lines.append("")
    lines.append("  5. The true paradox (not the old one): FEM has both high α_max")
    lines.append("     (tip concentration) AND low f_mean (bulk degradation).")
    lines.append("     PIDL has low α_max AND high f_mean (less concentrated at tip,")
    lines.append("     less accumulated overall). Different mechanisms reaching")
    lines.append("     similar N_f by coincidence.")
    lines.append("")
    lines.append("  6. Fourier random features (Tancik 2020, n_freq=16, NN dim 34):")
    lines.append("     damage profile (α_max≈9.07, α_mean≈0.385) ≈ baseline; peak ψ⁺")
    lines.append("     stability ≈ baseline (top10 Jaccard 0.140 vs 0.106 for BL,")
    lines.append("     0.255 for W). Three-way ablation: input feature enrichment")
    lines.append("     (physics-prior OR random spectral) cannot bridge the FEM-PIDL")
    lines.append("     α_max 100× gap. The N_f shift Fourier vs baseline (+4 cycles)")
    lines.append("     comes from boundary-criterion timing, not damage mechanism.")

    outpath.write_text("\n".join(lines))


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--umax", default="0.12",
                        help="U_max value to compare (default 0.12)")
    parser.add_argument("--output", default="figures/compare_kt",
                        help="Output directory relative to SENS_tensile/")
    parser.add_argument("--fem-kt", type=float, default=15.3,
                        help="FEM stable Kt value (from offline extraction)")
    args = parser.parse_args()

    outdir = HERE / args.output
    outdir.mkdir(parents=True, exist_ok=True)

    # --- Load FEM ---
    fem_path = find_fem_csv(args.umax)
    if fem_path is None:
        print(f"⚠️  FEM CSV not found for U_max={args.umax}")
        fem = None
    else:
        fem = load_fem(fem_path)
        print(f"✅ FEM: loaded {fem_path.name}, N_f = {fem['N_f']}")

    # --- Load PIDL flavors ---
    # NOTE: Williams v3 (false-stop run, no real fracture) intentionally excluded
    # from comparison plots. v4 is the publication baseline for Williams.
    series = {}
    for label, flavor in [("Baseline", "baseline"),
                          ("Williams v4", "williams_v4"),
                          ("Williams v4 (current)", "williams_v4_current"),
                          ("Fourier v1", "fourier_v1"),
                          ("Enriched v1", "enriched_v1"),         # ★ Direction 5
                          ("Dir 6.1 broad",  "spAlphaT_broad"),   # ★ Dir 6.1 broad
                          ("Dir 6.1 narrow", "spAlphaT_narrow")]: # ★ Dir 6.1 narrow
        d = find_pidl_dir(args.umax, flavor)
        if d is None:
            print(f"⚠️  {label}: dir not found (flavor={flavor})")
            continue
        data = load_pidl(d)
        if data is None:
            print(f"⚠️  {label}: dir {d.name} has no data")
            continue
        series[label] = data
        nf_info = f"N_f={data.get('n_f', '?')} ({data.get('n_f_source', '?')})"
        trunc = data.get("n_cycles_truncated", data["n_cycles"])
        print(f"✅ {label}: {data['n_cycles']}→{trunc} cycles, {nf_info}")

    if not series:
        print("❌ No PIDL data loaded, aborting")
        return 1

    # --- Generate figures ---
    print(f"\nGenerating figures in {outdir}/...")
    plot_Kt(series, fem, outdir / "fig_Kt_vs_cycle.png")
    if fem is not None:
        plot_log_metric(series, fem, "alpha_max", r"$\bar{\alpha}_{max}$ (log)",
                        "Fatigue damage accumulator — FEM concentrates 100x more",
                        outdir / "fig_alpha_max_vs_cycle.png")
        plot_log_metric(series, fem, "f_min", r"$f_{min}$ (log)",
                        "Degradation function at most-damaged element",
                        outdir / "fig_f_min_vs_cycle.png")
        plot_log_metric(series, fem, "E_el", r"$E_{el}$ (log)",
                        "Elastic energy per cycle",
                        outdir / "fig_E_el_vs_cycle.png")
        plot_summary_4panel(series, fem, args.fem_kt,
                            outdir / "fig_summary_4panel.png")
        plot_summary_6panel(series, fem, outdir / "fig_summary_6panel.png")
        print(f"  Wrote fig_summary_6panel.png")

    # --- Summary table ---
    if fem is not None:
        write_summary_table(series, fem, args.fem_kt,
                            outdir / "summary_table.txt")
        print(f"  Wrote summary_table.txt")

    print(f"\nDone. See {outdir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
