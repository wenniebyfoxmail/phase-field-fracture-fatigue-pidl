#!/usr/bin/env python3
"""
compute_multi_objective_J.py — Multi-objective calibration target J
(2nd-expert-review Apr 25 §3 / §7)

For each PIDL archive, computes a multi-objective error functional that
penalizes deviation from FEM in three quantities sampled at normalized
lifetime points s = N/N_f:

  Err_phys(s) = (ᾱ_max_PIDL(s)/ᾱ_max_FEM(s) − 1)²
              + (f_min_PIDL(s)/f_min_FEM(s) − 1)²
              + (A_ψ_PIDL(s)/A_ψ_FEM(s) − 1)²    [optional, only if
                                                  trajectory_*.npz with G1
                                                  process-zone cols exists]

  J = λ_N · log(N_f_PIDL / N_f_FEM)²  +  λ_phys · mean_s Err_phys

Recommended weights: λ_N = 1, λ_phys = 2-5 (physical trajectories matter
more than absolute lifetime per expert review).

Usage:
    python compute_multi_objective_J.py [--lambda_N 1 --lambda_phys 3]
        [--filter Umax0.12]

FEM CSVs assumed at:
    ~/Downloads/_pidl_handoff_v2/post_process/SENT_PIDL_<NN>_timeseries.csv
"""
from __future__ import annotations
import argparse
import csv
import re
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
FEM_CSV_DIR = Path("/Users/wenxiaofang/Downloads/_pidl_handoff_v2/post_process")

# Reasonable normalized-lifetime sample points
S_GRID = np.array([0.25, 0.50, 0.75, 1.00])


def parse_umax(name: str) -> float | None:
    m = re.search(r"_Umax(\d+\.\d+)", name)
    if m:
        return float(m.group(1))
    return None


def load_fem_for_umax(umax: float) -> dict | None:
    """Load FEM timeseries CSV for given Umax. Return dict or None."""
    fname = FEM_CSV_DIR / f"SENT_PIDL_{int(round(umax * 100)):02d}_timeseries.csv"
    if not fname.is_file():
        return None
    cycles, alpha_max, f_min, psi_peak, psi_tip = [], [], [], [], []
    with open(fname) as f:
        reader = csv.DictReader(f)
        for row in reader:
            cycles.append(int(row["N"]))
            alpha_max.append(float(row["alpha_max"]))
            f_min.append(float(row["f_min"]))
            psi_peak.append(float(row.get("psi_peak", 0.0)))
            psi_tip.append(float(row.get("psi_tip", 0.0)))
    return {
        "cycles": np.array(cycles),
        "alpha_max": np.array(alpha_max),
        "f_min": np.array(f_min),
        "psi_peak": np.array(psi_peak),
        "psi_tip": np.array(psi_tip),
        "N_f": int(cycles[-1]),
    }


def load_pidl_archive(archive_dir: Path) -> dict | None:
    """Load alpha_bar_vs_cycle.npy → cycles + ᾱ_max + ᾱ_mean + f_min."""
    abar_p = archive_dir / "best_models" / "alpha_bar_vs_cycle.npy"
    if not abar_p.exists():
        return None
    abar = np.load(str(abar_p))
    if abar.ndim != 2 or abar.shape[1] < 3:
        return None
    n = abar.shape[0]
    cycles = np.arange(n)
    return {
        "cycles": cycles,
        "alpha_max": abar[:, 0],
        "alpha_mean": abar[:, 1],
        "f_min": abar[:, 2],
        "N_f": n - 1,   # last cycle saved is taken as N_f proxy
    }


def linear_interp(target_cycle: float, cycles: np.ndarray, values: np.ndarray) -> float:
    """Linear interpolation at target_cycle. Clamp at endpoints."""
    if target_cycle <= cycles[0]:
        return float(values[0])
    if target_cycle >= cycles[-1]:
        return float(values[-1])
    return float(np.interp(target_cycle, cycles, values))


def compute_J(pidl: dict, fem: dict, lambda_N: float, lambda_phys: float
              ) -> dict:
    """Compute multi-objective J for one PIDL archive vs FEM reference."""
    Nf_pidl = pidl["N_f"]
    Nf_fem = fem["N_f"]
    log_ratio = np.log(max(Nf_pidl, 1) / max(Nf_fem, 1))
    err_phys_terms = []
    per_s_breakdown = []

    eps = 1e-12
    for s in S_GRID:
        c_pidl = s * Nf_pidl
        c_fem = s * Nf_fem
        a_pidl = linear_interp(c_pidl, pidl["cycles"], pidl["alpha_max"])
        a_fem = linear_interp(c_fem, fem["cycles"], fem["alpha_max"])
        f_pidl = linear_interp(c_pidl, pidl["cycles"], pidl["f_min"])
        f_fem = linear_interp(c_fem, fem["cycles"], fem["f_min"])

        # relative errors (use log-ratio for ᾱ_max / f_min since they
        # span orders of magnitude)
        e_amax = (np.log10(max(a_pidl, eps)) - np.log10(max(a_fem, eps))) ** 2
        e_fmin = (np.log10(max(f_pidl, eps)) - np.log10(max(f_fem, eps))) ** 2
        err_s = e_amax + e_fmin
        err_phys_terms.append(err_s)
        per_s_breakdown.append({
            "s": s,
            "a_pidl": a_pidl, "a_fem": a_fem,
            "f_pidl": f_pidl, "f_fem": f_fem,
            "err_amax": e_amax, "err_fmin": e_fmin,
        })
    err_phys = float(np.mean(err_phys_terms))
    err_nf = float(log_ratio ** 2)
    J = lambda_N * err_nf + lambda_phys * err_phys
    return {
        "Nf_pidl": Nf_pidl, "Nf_fem": Nf_fem,
        "log_ratio": float(log_ratio),
        "err_nf": err_nf,
        "err_phys_mean": err_phys,
        "J": J,
        "per_s": per_s_breakdown,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lambda_N", type=float, default=1.0)
    parser.add_argument("--lambda_phys", type=float, default=3.0)
    parser.add_argument("--filter", default="",
                        help="Only include archives whose name contains this")
    parser.add_argument("--csv", default="multi_objective_J.csv")
    args = parser.parse_args()

    # Find candidate PIDL archives (skip BUG_, _failed, _mono, _v1_incomplete)
    SKIP_TOKENS = ["BUG_", "_failed", "_mono", "_incomplete", "_initTraining",
                   "fatigue_off"]
    archives = []
    for d in HERE.iterdir():
        if not d.is_dir():
            continue
        if any(tok in d.name for tok in SKIP_TOKENS):
            continue
        if "Umax" not in d.name:
            continue
        if args.filter and args.filter not in d.name:
            continue
        if (d / "best_models" / "alpha_bar_vs_cycle.npy").exists():
            archives.append(d)
    archives = sorted(archives)
    print(f"Archives found: {len(archives)}")

    # Cache FEM data per Umax
    fem_cache = {}

    rows = []
    for d in archives:
        umax = parse_umax(d.name)
        if umax is None:
            continue
        if umax not in fem_cache:
            fem_data = load_fem_for_umax(umax)
            fem_cache[umax] = fem_data
        fem_data = fem_cache[umax]
        if fem_data is None:
            print(f"  SKIP (no FEM CSV) Umax={umax}: {d.name[-50:]}")
            continue
        pidl_data = load_pidl_archive(d)
        if pidl_data is None:
            continue
        result = compute_J(pidl_data, fem_data,
                          lambda_N=args.lambda_N, lambda_phys=args.lambda_phys)
        rows.append({"archive": d.name, "umax": umax, **result})

    # Sort by J ascending
    rows.sort(key=lambda r: r["J"])

    # Print table
    print()
    print(f"Multi-objective J = {args.lambda_N}·log(Nf ratio)² + "
          f"{args.lambda_phys}·mean_s Err_phys")
    print(f"Sampled at s ∈ {S_GRID.tolist()} (normalized lifetime)")
    print()
    print(f"{'Archive (last 60)':<60} {'Umax':>6} "
          f"{'Nf_P':>5} {'Nf_F':>5} "
          f"{'log_r':>7} {'err_Nf':>8} {'err_phys':>10} {'J':>10}")
    print("=" * 130)
    for r in rows:
        print(f"{r['archive'][-60:]:<60} {r['umax']:>6.2f} "
              f"{r['Nf_pidl']:>5} {r['Nf_fem']:>5} "
              f"{r['log_ratio']:>+7.3f} {r['err_nf']:>8.3f} "
              f"{r['err_phys_mean']:>10.3f} {r['J']:>10.3f}")

    # Per-Umax best result
    print("\nBest J (lowest = closest to FEM) per Umax:")
    print(f"{'Umax':>6} {'best archive':<60} {'J':>8}")
    print("=" * 80)
    by_umax: dict[float, list] = {}
    for r in rows:
        by_umax.setdefault(r["umax"], []).append(r)
    for u in sorted(by_umax):
        best = min(by_umax[u], key=lambda r: r["J"])
        print(f"{u:>6.2f} {best['archive'][-60:]:<60} {best['J']:>8.3f}")

    # Save CSV
    csv_path = HERE / args.csv
    with open(csv_path, "w") as f:
        f.write("archive,umax,Nf_pidl,Nf_fem,log_ratio,err_nf,err_phys_mean,J\n")
        for r in rows:
            f.write(f"{r['archive']},{r['umax']},{r['Nf_pidl']},{r['Nf_fem']},"
                    f"{r['log_ratio']:.4f},{r['err_nf']:.4f},"
                    f"{r['err_phys_mean']:.4f},{r['J']:.4f}\n")
    print(f"\n→ saved {csv_path.name}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
