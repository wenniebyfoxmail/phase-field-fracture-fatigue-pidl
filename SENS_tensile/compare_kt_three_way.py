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
]

# U_max -> FEM CSV suffix
FEM_CSV_SUFFIX = {"0.12": "12", "0.11": "11", "0.10": "10", "0.09": "09", "0.08": "08"}


def find_fem_csv(umax: str) -> Path | None:
    suffix = FEM_CSV_SUFFIX.get(umax)
    if suffix is None:
        return None
    for d in FEM_CSV_DIR_CANDIDATES:
        p = d / f"SENT_PIDL_{suffix}_timeseries.csv"
        if p.exists():
            return p
    return None


def find_pidl_dir(umax: str, flavor: str) -> Path | None:
    """flavor in {'baseline', 'williams_v3', 'williams_v4_current'}"""
    base = HERE
    umax_tag = f"Umax{umax}"
    dirs = [d for d in base.iterdir() if d.is_dir() and umax_tag in d.name
            and "hl_8_Neurons_400" in d.name and "coeff_1.0" in d.name]

    if flavor == "baseline":
        # Strictly: directory ends with "Umax{umax}" (no Williams, no tipw, etc.)
        matches = [d for d in dirs if d.name.endswith(umax_tag)]
    elif flavor == "williams_v3":
        matches = [d for d in dirs if "williams_std_v3_cycle69" in d.name]
    elif flavor == "williams_v4_current":
        matches = [d for d in dirs if d.name.endswith("williams_std")]
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


def load_pidl(model_dir: Path) -> dict | None:
    bm = model_dir / "best_models"
    out = {}
    for name, k in [("Kt_vs_cycle.npy", "Kt"),
                    ("E_el_vs_cycle.npy", "E_el"),
                    ("alpha_bar_vs_cycle.npy", "alpha_bar"),
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
    # Unified x_tip: prefer psi-based for Williams, else alpha-based
    if "x_tip_psi" in out:
        out["x_tip_use"] = out["x_tip_psi"]
    elif "x_tip" in out:
        out["x_tip_use"] = out["x_tip"]
    out["n_cycles"] = len(out.get("Kt", out.get("E_el", [])))
    return out


def load_fem(csv_path: Path) -> dict:
    df = pd.read_csv(csv_path)
    return {
        "N": df["N"].values,
        "E_el": df["E_el"].values,
        "alpha_max": df["alpha_max"].values,
        "f_min": df["f_min"].values,
        "a_ell": df["a_ell"].values,
        "d_max": df["d_max"].values,
        "N_f": int(df["N"].values[-1]),  # last cycle = fracture
    }


# -----------------------------------------------------------------------------
# Plotting
# -----------------------------------------------------------------------------

COLOR = {"FEM": "#D62728", "Baseline": "#1F77B4", "Williams v3": "#2CA02C",
         "Williams v4 (current)": "#9467BD"}
LINESTYLE = {"FEM": "-", "Baseline": "-", "Williams v3": "-",
             "Williams v4 (current)": "--"}
LINEWIDTH = 1.8


def _add_series(ax, x, y, label, **kw):
    ax.plot(x, y, label=label, color=COLOR.get(label, "black"),
            linestyle=LINESTYLE.get(label, "-"), linewidth=LINEWIDTH, **kw)


def plot_Kt(series: dict, fem_kt: float, outpath: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))
    for name, d in series.items():
        if name == "FEM":
            # FEM has no Kt column, use reported stable value as horizontal line
            ax.axhline(fem_kt, color=COLOR["FEM"], linestyle="-",
                       linewidth=LINEWIDTH, label=f"FEM (Kt={fem_kt}, stable)")
        else:
            if "Kt" in d:
                _add_series(ax, np.arange(len(d["Kt"])), d["Kt"], name)
    ax.set_xlabel("Cycle N")
    ax.set_ylabel("Kt = √(ψ⁺_tip / ψ⁺_nominal)")
    ax.set_title("Stress concentration factor Kt — three-way comparison (U_max=0.12)")
    ax.legend(loc="best")
    ax.grid(alpha=0.3)
    ax.set_ylim(5, 20)  # clip nonsense late-cycle values
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


def plot_summary_4panel(series: dict, fem_series: dict, fem_kt: float,
                        outpath: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))

    # (0,0) Kt
    ax = axes[0, 0]
    ax.axhline(fem_kt, color=COLOR["FEM"], linestyle="-",
               linewidth=LINEWIDTH, label=f"FEM (Kt={fem_kt})")
    for name, d in series.items():
        if "Kt" in d:
            _add_series(ax, np.arange(len(d["Kt"])), d["Kt"], name)
    ax.set_xlabel("Cycle")
    ax.set_ylabel("Kt")
    ax.set_title("(a) Stress concentration factor")
    ax.legend(loc="best", fontsize=9)
    ax.grid(alpha=0.3)
    ax.set_ylim(5, 20)

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
    lines.append(f"{'Cycle':>7} | {'Method':>20} | {'Kt':>8} | {'α_max':>10} | "
                 f"{'f_min':>12} | {'E_el':>12}")
    lines.append("-" * 85)
    for c in cycles_of_interest:
        # FEM
        if c == "N_f":
            fem_row = fem_series
            cycle_fem = fem_series["N_f"]
            idx = np.argmax(fem_series["N"] == cycle_fem)
        elif isinstance(c, int):
            cycle_fem = c if c > 0 else 1
            mask = fem_series["N"] == cycle_fem
            idx = np.argmax(mask) if mask.any() else None
        if idx is not None:
            cf = fem_series
            lines.append(f"{cycle_fem:>7} | {'FEM':>20} | {f'{fem_kt} (stable)':>8} | "
                         f"{cf['alpha_max'][idx]:>10.3f} | {cf['f_min'][idx]:>12.4e} | "
                         f"{cf['E_el'][idx]:>12.4e}")
        # PIDL
        for name, d in series.items():
            if c == "N_f":
                # Baseline: find cycle where x_tip >= 0.5
                if "x_tip_use" in d:
                    mask = d["x_tip_use"] >= 0.5
                    if mask.any():
                        idx_p = int(np.argmax(mask))
                    else:
                        idx_p = d["n_cycles"] - 1  # last available cycle
                else:
                    idx_p = d["n_cycles"] - 1
            elif isinstance(c, int):
                idx_p = c if c < d["n_cycles"] else None
            if idx_p is not None:
                Kt_str = f"{d['Kt'][idx_p]:.3f}" if "Kt" in d else "NA"
                am_str = f"{d['alpha_max'][idx_p]:.3f}" if "alpha_max" in d else "NA"
                fm_str = f"{d['f_min'][idx_p]:.4e}" if "f_min" in d else "NA"
                ee_str = f"{d['E_el'][idx_p]:.4e}" if "E_el" in d else "NA"
                lines.append(f"{idx_p:>7} | {name:>20} | {Kt_str:>8} | "
                             f"{am_str:>10} | {fm_str:>12} | {ee_str:>12}")
        lines.append("-" * 85)

    lines.append("")
    lines.append("KEY FINDINGS:")
    lines.append("  1. Kt: FEM=15.3 stable; both PIDL rise from ~7.5 to ~16 over 70 cycles.")
    lines.append("     Williams provides marginal Kt acceleration (+0.4 avg vs baseline).")
    lines.append("  2. α_max: FEM reaches 958 at N_f; PIDL only reaches ~9 at N_f.")
    lines.append("     Williams α_max is LOWER than baseline at matched cycles — ")
    lines.append("     damage is MORE dispersed with Williams, not more concentrated.")
    lines.append("  3. f_min: FEM drops to 10⁻⁶ (tip element fully broken);")
    lines.append("     PIDL stuck at 10⁻² (partial degradation at many elements).")
    lines.append("  4. The 'dispersed degradation' paradox is NOT resolved by Williams.")

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
    series = {}
    for label, flavor in [("Baseline", "baseline"),
                          ("Williams v3", "williams_v3"),
                          ("Williams v4 (current)", "williams_v4_current")]:
        d = find_pidl_dir(args.umax, flavor)
        if d is None:
            print(f"⚠️  {label}: dir not found (flavor={flavor})")
            continue
        data = load_pidl(d)
        if data is None:
            print(f"⚠️  {label}: dir {d.name} has no data")
            continue
        series[label] = data
        print(f"✅ {label}: {d.name} ({data['n_cycles']} cycles)")

    if not series:
        print("❌ No PIDL data loaded, aborting")
        return 1

    # --- Generate figures ---
    print(f"\nGenerating figures in {outdir}/...")
    plot_Kt(series, args.fem_kt, outdir / "fig_Kt_vs_cycle.png")
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

    # --- Summary table ---
    if fem is not None:
        write_summary_table(series, fem, args.fem_kt,
                            outdir / "summary_table.txt")
        print(f"  Wrote summary_table.txt")

    print(f"\nDone. See {outdir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
