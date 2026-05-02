#!/usr/bin/env python3
"""
Post-hoc PIDL vs FEM trajectory comparison.

Tests the May-2 user critique: "if PIDL ᾱ_max is 3× short of FEM but N_f matches
EXACT, is the N_f match mechanism or coincidence?"

Three analyses on existing archives (no new compute):
  Task 1: Boundary α evolution — when does each method's boundary reach 0.95?
  Task 2: a-N curve full extraction — same trajectory or just same endpoint?
  Task 3: Per-cycle ψ⁺ at tip element — peak amplitude trajectory

Inputs:
  - PIDL log file (per-cycle ᾱ_max, crack_tip x, N_bdy>0.95, α_max@bdy)
  - FEM CSV (per-cycle alpha_max, a_ell, psi_peak, psi_tip, d_max)

Outputs:
  - posthoc_trajectory_<umax>.csv (combined trajectory, side-by-side)
  - posthoc_trajectory_<umax>.png (4-panel comparison plot)
  - Console: numerical mechanism-vs-coincidence verdict
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def parse_pidl_log(log_path: Path) -> pd.DataFrame:
    """Parse PIDL log into per-cycle DataFrame.

    Lines of interest:
      [Fatigue step N] ᾱ_max=X | f_min=X | f_mean=X | Kt=X
      [crack_tip] = (X, Y)  L∞_length = X  α_max@bdy=X  N_bdy>0.95=N
    """
    text = log_path.read_text()

    # Extract per-cycle data via regex
    fatigue_pat = re.compile(
        r"\[Fatigue step (\d+)\] ᾱ_max=([0-9.eE+\-]+) \| f_min=([0-9.eE+\-]+) \| f_mean=([0-9.eE+\-]+) \| Kt=([0-9.eE+\-]+)"
    )
    tip_pat = re.compile(
        r"\[crack_tip\]\s+= \(([0-9.eE+\-]+), ([0-9.eE+\-]+)\)\s+L∞_length = ([0-9.eE+\-]+)\s+α_max@bdy=([\-0-9.eE+\-]+)\s+N_bdy>0\.95=(\d+)"
    )

    fatigue_matches = fatigue_pat.findall(text)
    tip_matches = tip_pat.findall(text)

    # Pair them up by order of appearance
    n = min(len(fatigue_matches), len(tip_matches))
    rows = []
    for i in range(n):
        cyc, alpha_max, f_min, f_mean, Kt = fatigue_matches[i]
        x, y, L_inf, alpha_bdy, n_bdy = tip_matches[i]
        rows.append({
            "N": int(cyc),
            "alpha_max_pidl": float(alpha_max),
            "f_min_pidl": float(f_min),
            "f_mean_pidl": float(f_mean),
            "Kt_pidl": float(Kt),
            "tip_x_pidl": float(x),
            "tip_y_pidl": float(y),
            "L_inf_pidl": float(L_inf),
            "alpha_bdy_pidl": float(alpha_bdy),
            "n_bdy_pidl": int(n_bdy),
        })

    df = pd.DataFrame(rows)
    return df


def load_fem_csv(csv_path: Path) -> pd.DataFrame:
    """Load FEM timeseries CSV."""
    return pd.read_csv(csv_path)


def merge_trajectories(pidl_df: pd.DataFrame, fem_df: pd.DataFrame) -> pd.DataFrame:
    """Inner join on N (cycle number)."""
    return pd.merge(pidl_df, fem_df, on="N", how="outer").sort_values("N").reset_index(drop=True)


def detect_n_f_pidl(df: pd.DataFrame, n_bdy_threshold: int = 3) -> int | None:
    """First cycle where n_bdy_pidl >= threshold."""
    over = df[df["n_bdy_pidl"] >= n_bdy_threshold]
    return int(over["N"].iloc[0]) if len(over) else None


def detect_n_f_fem(df: pd.DataFrame, d_threshold: float = 0.95) -> int | None:
    """First cycle where d_max_fem >= threshold."""
    if "d_max" not in df.columns:
        return None
    over = df[df["d_max"] >= d_threshold]
    return int(over["N"].iloc[0]) if len(over) else None


def compute_verdict(merged: pd.DataFrame, umax: float) -> dict:
    """Compute mechanism-vs-coincidence verdict numbers."""
    nf_pidl = detect_n_f_pidl(merged)
    nf_fem = detect_n_f_fem(merged)

    # Crack length match — at common cycles, how close is a_ell (FEM) vs L_inf (PIDL)?
    common = merged.dropna(subset=["L_inf_pidl", "a_ell"])
    if len(common):
        # PIDL L∞ length is from origin (0,0); FEM a_ell is also crack length from precrack tip (0,0).
        # Both should be on same scale (0 to ~0.5 for full propagation)
        a_diff = (common["L_inf_pidl"] - common["a_ell"]).abs()
        a_rms = float(np.sqrt((a_diff ** 2).mean()))
        a_max_diff = float(a_diff.max())
    else:
        a_rms = a_max_diff = float("nan")

    # alpha_max ratio (FEM/PIDL) at end
    last_pidl_alpha = float(merged["alpha_max_pidl"].dropna().iloc[-1]) if len(merged["alpha_max_pidl"].dropna()) else float("nan")
    last_fem_alpha = float(merged["alpha_max"].dropna().iloc[-1]) if len(merged["alpha_max"].dropna()) else float("nan")
    alpha_ratio = last_fem_alpha / last_pidl_alpha if last_pidl_alpha else float("nan")

    # psi_tip ratio
    if "psi_tip" in merged.columns:
        last_psi_fem = float(merged["psi_tip"].dropna().iloc[-1])
    else:
        last_psi_fem = float("nan")

    return {
        "umax": umax,
        "N_f_pidl_n_bdy>=3": nf_pidl,
        "N_f_fem_d>=0.95": nf_fem,
        "Nf_diff": (nf_pidl - nf_fem) if (nf_pidl and nf_fem) else None,
        "Nf_rel_diff_pct": (100 * (nf_pidl - nf_fem) / nf_fem) if (nf_pidl and nf_fem) else None,
        "a_trajectory_rms_diff": a_rms,
        "a_trajectory_max_diff": a_max_diff,
        "PIDL_alpha_max_end": last_pidl_alpha,
        "FEM_alpha_max_end": last_fem_alpha,
        "alpha_ratio_FEM_over_PIDL": alpha_ratio,
        "FEM_psi_tip_end": last_psi_fem,
    }


def plot_4panel(merged: pd.DataFrame, umax: float, out_png: Path) -> None:
    """4-panel: a-N, boundary α evolution, ᾱ_max trajectory, ψ⁺ trajectory."""
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))

    # Panel 1: a-N curve
    ax = axes[0, 0]
    if "L_inf_pidl" in merged.columns:
        m = merged.dropna(subset=["L_inf_pidl"])
        ax.plot(m["N"], m["L_inf_pidl"], "b-", label="PIDL crack tip x (L∞)", lw=1.5)
    if "a_ell" in merged.columns:
        m = merged.dropna(subset=["a_ell"])
        ax.plot(m["N"], m["a_ell"], "r--", label="FEM a_ell (crack length)", lw=1.5)
    ax.set_xlabel("Cycle N")
    ax.set_ylabel("Crack length")
    ax.set_title(f"Task 2: a-N curve @ Umax={umax}")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Panel 2: Boundary damage evolution
    ax = axes[0, 1]
    if "alpha_bdy_pidl" in merged.columns:
        m = merged.dropna(subset=["alpha_bdy_pidl"])
        ax.plot(m["N"], m["alpha_bdy_pidl"], "b-", label="PIDL α_max@bdy", lw=1.5)
    if "d_max" in merged.columns:
        m = merged.dropna(subset=["d_max"])
        ax.plot(m["N"], m["d_max"], "r--", label="FEM d_max (boundary)", lw=1.5)
    ax.axhline(0.95, color="k", linestyle=":", label="threshold 0.95")
    ax.set_xlabel("Cycle N")
    ax.set_ylabel("Max boundary damage")
    ax.set_title(f"Task 1: Boundary damage evolution @ Umax={umax}")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Panel 3: ᾱ_max in zone (full vs PIDL)
    ax = axes[1, 0]
    if "alpha_max_pidl" in merged.columns:
        m = merged.dropna(subset=["alpha_max_pidl"])
        ax.plot(m["N"], m["alpha_max_pidl"], "b-", label="PIDL ᾱ_max", lw=1.5)
    if "alpha_max" in merged.columns:
        m = merged.dropna(subset=["alpha_max"])
        ax.plot(m["N"], m["alpha_max"], "r--", label="FEM ᾱ_max (psi)", lw=1.5)
    ax.set_xlabel("Cycle N")
    ax.set_ylabel("ᾱ_max accumulator")
    ax.set_yscale("log")
    ax.set_title(f"ᾱ_max trajectory @ Umax={umax} (log scale)")
    ax.legend()
    ax.grid(True, alpha=0.3, which="both")

    # Panel 4: Task 3 — ψ⁺ at tip per cycle
    ax = axes[1, 1]
    if "psi_tip" in merged.columns:
        m = merged.dropna(subset=["psi_tip"])
        ax.plot(m["N"], m["psi_tip"], "r--", label="FEM ψ_tip", lw=1.5)
    if "psi_peak" in merged.columns:
        m = merged.dropna(subset=["psi_peak"])
        ax.plot(m["N"], m["psi_peak"], "m:", label="FEM ψ_peak", lw=1.0)
    # PIDL doesn't log per-cycle psi+ in the same field; can derive from alpha_max + Carrara
    # but for now leave as FEM-only
    ax.set_xlabel("Cycle N")
    ax.set_ylabel("ψ⁺")
    ax.set_yscale("log")
    ax.set_title(f"Task 3: FEM ψ⁺ trajectory @ Umax={umax}\n(PIDL psi not logged per-cycle, see CSV for indirect)")
    ax.legend()
    ax.grid(True, alpha=0.3, which="both")

    fig.suptitle(f"PIDL vs FEM trajectory comparison @ Umax={umax}\nTesting mechanism vs coincidence (May-2 user critique)", fontsize=13)
    plt.tight_layout()
    plt.savefig(out_png, dpi=120, bbox_inches="tight")
    print(f"saved {out_png}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pidl-log", required=True, help="Path to PIDL log file (with cycle-by-cycle output)")
    p.add_argument("--fem-csv", required=True, help="Path to FEM SENT_PIDL_<UMAX>_timeseries.csv")
    p.add_argument("--umax", type=float, required=True, help="Load amplitude for labeling")
    p.add_argument("--out-prefix", default="posthoc_trajectory", help="Output filename prefix")
    args = p.parse_args()

    pidl_df = parse_pidl_log(Path(args.pidl_log))
    print(f"PIDL log parsed: {len(pidl_df)} cycles, max N = {pidl_df['N'].max() if len(pidl_df) else 0}")

    fem_df = load_fem_csv(Path(args.fem_csv))
    print(f"FEM CSV loaded: {len(fem_df)} cycles, max N = {fem_df['N'].max() if len(fem_df) else 0}, columns = {list(fem_df.columns)}")

    merged = merge_trajectories(pidl_df, fem_df)
    out_csv = Path(f"{args.out_prefix}_u{args.umax:.2f}.csv")
    merged.to_csv(out_csv, index=False)
    print(f"merged trajectory saved: {out_csv}")

    verdict = compute_verdict(merged, args.umax)
    print("\n=== VERDICT ===")
    for k, v in verdict.items():
        print(f"  {k}: {v}")

    out_png = Path(f"{args.out_prefix}_u{args.umax:.2f}.png")
    plot_4panel(merged, args.umax, out_png)


if __name__ == "__main__":
    main()
