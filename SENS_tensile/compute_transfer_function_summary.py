#!/usr/bin/env python3
"""
compute_transfer_function_summary.py — B2 (Apr 27 2026)

Per-archive transfer-function chain summary table. For each archive, extract
the end-of-trajectory values along the Carrara fatigue chain:

  link 0:  ψ⁺_raw_max          (NN single-element peak; A2 if available)
  link 1:  g(α)·ψ⁺_max          (active driver into accumulator; A2 if avail)
  link 2:  ᾱ_max                 (Carrara fatigue history; cached .npy)
  link 3:  f_min                 (degradation function value at tip; cached)
  link 4:  K_I                   (J-integral; A1 if available)
  link 5:  N_f via C1=C2         (geometric/energy criterion; A3)

Combines:
  - multi_objective_J.csv      (already-computed N_f and J score per archive)
  - <archive>/best_models/process_zone_metrics.npy  (A2; if exists)
  - <archive>/best_models/J_integral.npy            (A1; if exists)
  - <archive>/best_models/alpha_bar_vs_cycle.npy    (always)
  - <archive>/best_models/Kt_vs_cycle.npy           (always)

Output:
  transfer_function_summary.csv     master row-per-archive table
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
ALPHA_T = 0.5  # Carrara default


def load_npy(p):
    return np.load(str(p)) if p.is_file() else None


def carrara_f(alpha_bar, alpha_T=ALPHA_T):
    if alpha_bar <= alpha_T:
        return 1.0
    return float((2.0 * alpha_T / (alpha_bar + alpha_T)) ** 2)


def find_Nf_C1_C2(bm: Path):
    """N_f via x_tip≥0.5 (C1) — falls back to argmax|dE_el/dN| (C2)."""
    x = load_npy(bm / "x_tip_vs_cycle.npy")
    if x is not None:
        idx = np.where(x >= 0.5)[0]
        if len(idx) > 0:
            return int(idx[0])
    E = load_npy(bm / "E_el_vs_cycle.npy")
    if E is not None and len(E) >= 3:
        return int(np.argmax(np.abs(np.diff(E))) + 1)
    return None


def per_archive_summary(adir: Path):
    bm = adir / "best_models"
    if not bm.is_dir():
        return None

    out = {"archive": adir.name}

    # Umax from name
    out["umax"] = ""
    for tok in adir.name.split("_"):
        if tok.startswith("Umax"):
            out["umax"] = tok[4:]
            break

    # link 5: N_f
    out["Nf_C1C2"] = find_Nf_C1_C2(bm)

    # link 2 + 3: alpha_bar_max, f_min trajectory at last cycle
    ab = load_npy(bm / "alpha_bar_vs_cycle.npy")
    if ab is not None and ab.ndim == 2 and ab.shape[1] >= 3:
        end_c = (out["Nf_C1C2"] if out["Nf_C1C2"] is not None
                 and out["Nf_C1C2"] < len(ab) else len(ab) - 1)
        out["ab_max_endN"] = float(ab[end_c, 0])
        out["ab_mean_endN"] = float(ab[end_c, 1])
        out["f_min_endN"] = float(ab[end_c, 2])
        out["f_min_traj_min"] = float(ab[:end_c + 1, 2].min())
        out["ab_max_traj_max"] = float(ab[:end_c + 1, 0].max())
    else:
        out["ab_max_endN"] = out["ab_mean_endN"] = out["f_min_endN"] = np.nan
        out["f_min_traj_min"] = out["ab_max_traj_max"] = np.nan

    # link 0/1: process_zone_metrics (A2 result)
    pz = load_npy(bm / "process_zone_metrics.npy")
    if pz is not None and len(pz) > 0:
        last = pz[-1]
        # Column index map per A2 OUT_COLUMNS
        out["psi_max_endN"] = float(last[5])      # psi_max
        out["psi_top1pct_endN"] = float(last[7])  # psi_top1pct
        out["gpsi_max_endN"] = float(last[9])     # gpsi_max
        out["gpsi_top1pct_endN"] = float(last[11])
        out["fpsi_top1pct_endN"] = float(last[15])
        out["int_gpsi_l0_endN"] = float(last[18])
        out["int_fpsi_l0_endN"] = float(last[19])
        out["pz_alpha_area_endN"] = float(last[26])
        out["pz_alphabar_area_endN"] = float(last[27])
    else:
        for k in ["psi_max_endN", "psi_top1pct_endN", "gpsi_max_endN",
                  "gpsi_top1pct_endN", "fpsi_top1pct_endN", "int_gpsi_l0_endN",
                  "int_fpsi_l0_endN", "pz_alpha_area_endN",
                  "pz_alphabar_area_endN"]:
            out[k] = np.nan

    # link 4: K_I (A1)
    Ji = load_npy(bm / "J_integral.npy")
    if Ji is not None and len(Ji) > 0:
        # Use median of all pristine cycles where J(r=0.05) and J(r=0.08) and J(r=0.12) all > 0
        # Per A1 column layout: [cycle, x_tip, r_eff_0..2, J_r0..2, K_r0..2]
        Js = Ji[:, 5:8]
        Ks = Ji[:, 8:11]
        valid = np.all(Js > 0, axis=1)
        if valid.sum() > 0:
            K_med = float(np.median(Ks[valid, 1]))   # mid radius
            out["K_I_pristine_med"] = K_med
            # LEFM theoretical: K_theo = U_max·sqrt(πa)·F  for a/W=0.5, F=2.83
            try:
                U = float(out["umax"])
                K_theo = U * (np.pi * 0.5) ** 0.5 * 2.83
                out["K_I_theo_LEFM"] = K_theo
                out["K_I_PIDL_over_theo"] = K_med / K_theo if K_theo > 0 else np.nan
            except (ValueError, TypeError):
                out["K_I_theo_LEFM"] = np.nan
                out["K_I_PIDL_over_theo"] = np.nan
        else:
            out["K_I_pristine_med"] = np.nan
            out["K_I_theo_LEFM"] = np.nan
            out["K_I_PIDL_over_theo"] = np.nan
    else:
        out["K_I_pristine_med"] = np.nan
        out["K_I_theo_LEFM"] = np.nan
        out["K_I_PIDL_over_theo"] = np.nan

    # Kt from cached
    Kt = load_npy(bm / "Kt_vs_cycle.npy")
    if Kt is not None and len(Kt) > 0:
        out["Kt_endN"] = float(Kt[-1])
        out["Kt_traj_max"] = float(Kt.max())
    else:
        out["Kt_endN"] = out["Kt_traj_max"] = np.nan

    return out


def main():
    print("Scanning archives matching multi_objective_J.csv list…")
    moj_path = HERE / "multi_objective_J.csv"
    if moj_path.is_file():
        with open(moj_path) as f:
            reader = csv.DictReader(f)
            moj_archives = [row["archive"] for row in reader]
        print(f"  multi_objective_J.csv: {len(moj_archives)} archives listed")
    else:
        moj_archives = []

    # Also include any priority A2/A1 archives even if not in moj
    extra = sorted(p.parent.parent.name for p in
                   HERE.glob("*/best_models/process_zone_metrics.npy"))
    all_archives = sorted(set(moj_archives) | set(extra))
    print(f"  total to summarize: {len(all_archives)}")

    rows = []
    for name in all_archives:
        adir = HERE / name
        if not adir.is_dir():
            continue
        s = per_archive_summary(adir)
        if s is not None:
            rows.append(s)

    cols = ["archive", "umax", "Nf_C1C2",
            "psi_max_endN", "psi_top1pct_endN",
            "gpsi_max_endN", "gpsi_top1pct_endN",
            "fpsi_top1pct_endN", "int_gpsi_l0_endN", "int_fpsi_l0_endN",
            "ab_max_endN", "ab_max_traj_max",
            "f_min_endN", "f_min_traj_min",
            "pz_alpha_area_endN", "pz_alphabar_area_endN",
            "Kt_endN", "Kt_traj_max",
            "K_I_pristine_med", "K_I_theo_LEFM", "K_I_PIDL_over_theo"]
    out_csv = HERE / "transfer_function_summary.csv"
    with open(out_csv, "w") as fh:
        fh.write(",".join(cols) + "\n")
        for r in rows:
            fh.write(",".join(
                "" if r.get(c) is None
                else (f"{r[c]:.6e}" if isinstance(r[c], float) else str(r[c]))
                for c in cols) + "\n")
    print(f"\n→ {out_csv.relative_to(HERE.parent)}  ({len(rows)} archives)")

    # Print a compact subset for terminal viewing
    print()
    print(f"{'archive_short':<60} {'Umax':>5} {'N_f':>4} {'ᾱ_max':>7} "
          f"{'ψ⁺_max':>9} {'K_I':>6} {'PIDL/LEFM':>9}")
    for r in rows:
        sn = r["archive"].replace(
            "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_", "").replace("_R0.0", "")[:60]
        psi = r["psi_max_endN"]
        ki = r["K_I_pristine_med"]
        ratio = r["K_I_PIDL_over_theo"]
        print(f"{sn:<60} {r['umax']:>5} {r['Nf_C1C2']!s:>4} "
              f"{r['ab_max_endN']:>7.2f} "
              f"{psi if not np.isnan(psi) else 0:>9.2e} "
              f"{ki if not np.isnan(ki) else 0:>6.3f} "
              f"{ratio if not np.isnan(ratio) else 0:>9.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
