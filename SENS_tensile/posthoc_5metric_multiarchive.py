#!/usr/bin/env python3
"""
posthoc_5metric_multiarchive.py — 5-metric trajectory analysis across multiple PIDL archives.

Per external expert recommendation (May-3): evaluate PIDL vs FEM at TRAJECTORY level
(N_f, ᾱ_max(N), α_zone(N), ψ⁺_zone(N), a(N)/x_tip(N)) instead of single-point N_f match.

Inputs (per archive):
  - PIDL log file (per-cycle ᾱ_max, f_min, f_mean, x_tip, L_inf, α_max@bdy, N_bdy)
  - FEM CSV (per-cycle alpha_max, alpha_bar_mean, psi_peak, psi_tip, a_ell, d_max, f_min, f_mean)

Outputs:
  - posthoc_5metric_<label>.csv (per-archive merged trajectory)
  - posthoc_5metric_consolidated.png (multi-archive overlay, 6 panels)
  - posthoc_5metric_consolidated.csv (cross-archive verdict table)

Derived metrics:
  - PIDL ᾱ_zone_mean: from f_mean via Carrara Eq. 41 inversion: ᾱ ≈ α_T·(2/√f - 1)
  - PIDL ψ⁺_zone (NOT directly available — log doesn't capture; TODO via NN reload)
  - da/dN: numerical derivative of a(N) trajectory

Ablations consistency check:
  - Pattern A: PIDL boundary α step-jump at N_f (vs gradual saturation)
  - Pattern B: PIDL crack tip leads FEM by 30-50% at N_f
  - Pattern C: ᾱ_max ratio FEM/PIDL ~10-100× field-level divergence yet N_f match within 10%
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

    Handles two log formats:
    - New format (Path C, baseline_umax): has Kt + α_max@bdy + N_bdy
    - Old format (training_8x400_*): has only ᾱ_max + f_min + f_mean + crack_tip
    """
    text = log_path.read_text()

    fatigue_pat_new = re.compile(
        r"\[Fatigue step (\d+)\] ᾱ_max=([0-9.eE+\-]+) \| f_min=([0-9.eE+\-]+) \| f_mean=([0-9.eE+\-]+) \| Kt=([0-9.eE+\-]+)"
    )
    fatigue_pat_old = re.compile(
        r"\[Fatigue step (\d+)\] ᾱ_max=([0-9.eE+\-]+) \| f_min=([0-9.eE+\-]+) \| f_mean=([0-9.eE+\-]+)"
    )
    tip_pat_new = re.compile(
        r"\[crack_tip\]\s+= \(([0-9.eE+\-]+), ([0-9.eE+\-]+)\)\s+L∞_length = ([0-9.eE+\-]+)\s+α_max@bdy=([\-0-9.eE+\-]+)\s+N_bdy>0\.95=(\d+)"
    )
    tip_pat_old = re.compile(
        r"\[crack_tip\]\s+= \(([0-9.eE+\-]+), ([0-9.eE+\-]+)\)\s+L∞_length = ([0-9.eE+\-]+)"
    )

    fatigue_matches = fatigue_pat_new.findall(text)
    new_format = bool(fatigue_matches)
    if not new_format:
        fatigue_matches = fatigue_pat_old.findall(text)
    tip_matches = tip_pat_new.findall(text) if new_format else tip_pat_old.findall(text)

    n = min(len(fatigue_matches), len(tip_matches))
    rows = []
    for i in range(n):
        if new_format:
            cyc, alpha_max, f_min, f_mean, Kt = fatigue_matches[i]
            x, y, L_inf, alpha_bdy, n_bdy = tip_matches[i]
            rows.append({
                "N": int(cyc),
                "alpha_max_pidl": float(alpha_max),
                "f_min_pidl": float(f_min),
                "f_mean_pidl": float(f_mean),
                "Kt_pidl": float(Kt),
                "tip_x_pidl": float(x),
                "L_inf_pidl": float(L_inf),
                "alpha_bdy_pidl": float(alpha_bdy),
                "n_bdy_pidl": int(n_bdy),
            })
        else:
            cyc, alpha_max, f_min, f_mean = fatigue_matches[i]
            x, y, L_inf = tip_matches[i]
            rows.append({
                "N": int(cyc),
                "alpha_max_pidl": float(alpha_max),
                "f_min_pidl": float(f_min),
                "f_mean_pidl": float(f_mean),
                "Kt_pidl": np.nan,
                "tip_x_pidl": float(x),
                "L_inf_pidl": float(L_inf),
                "alpha_bdy_pidl": np.nan,
                "n_bdy_pidl": np.nan,
            })

    return pd.DataFrame(rows)


def derive_alpha_zone_mean_pidl(f_mean: float, alpha_T: float = 0.5) -> float:
    """Invert Carrara Eq. 41: f = [2α_T / (ᾱ + α_T)]² with α_T=0.5.
    f → ᾱ = α_T·(2/√f − 1).
    Used to derive PIDL's domain-mean ᾱ from logged f_mean.

    NOTE: this is DOMAIN-mean, NOT zone-mean. PIDL log doesn't give zone-mean directly.
    For trajectory shape comparison this should still be useful.
    """
    if f_mean <= 0 or f_mean > 1:
        return np.nan
    return alpha_T * (2.0 / np.sqrt(f_mean) - 1.0)


def merge_trajectories(pidl_df: pd.DataFrame, fem_df: pd.DataFrame) -> pd.DataFrame:
    """Inner join on N + add derived columns."""
    merged = pd.merge(pidl_df, fem_df, on="N", how="outer", suffixes=("", "_fem"))
    merged = merged.sort_values("N").reset_index(drop=True)

    # Derive PIDL ᾱ_domain_mean from f_mean (Carrara Eq. 41 inverse)
    if "f_mean_pidl" in merged.columns:
        merged["alpha_bar_domain_pidl"] = merged["f_mean_pidl"].apply(derive_alpha_zone_mean_pidl)

    # da/dN derivative
    if "L_inf_pidl" in merged.columns:
        merged["da_dN_pidl"] = merged["L_inf_pidl"].diff()
    if "a_ell" in merged.columns:
        merged["da_dN_fem_extracted"] = merged["a_ell"].diff()

    return merged


def detect_n_f_pidl(df: pd.DataFrame, mode: str = "n_bdy") -> int | None:
    """First-detect N_f from PIDL trajectory.
    mode='n_bdy' uses n_bdy_pidl >= 3 (canonical); 'L_inf' uses L_inf >= 0.46 (proxy)."""
    if mode == "n_bdy" and "n_bdy_pidl" in df.columns:
        sub = df[df["n_bdy_pidl"] >= 3]
        if len(sub):
            return int(sub["N"].iloc[0])
    if mode == "L_inf" and "L_inf_pidl" in df.columns:
        sub = df[df["L_inf_pidl"] >= 0.46]
        if len(sub):
            return int(sub["N"].iloc[0])
    return None


def detect_n_f_fem_csv_endpoint(df: pd.DataFrame) -> int | None:
    """FEM N_f is the last cycle in CSV (CSV stops at N_f trigger)."""
    fem_rows = df.dropna(subset=["a_ell"])
    if len(fem_rows):
        return int(fem_rows["N"].iloc[-1])
    return None


def compute_5metric_verdict(merged: pd.DataFrame, label: str) -> dict:
    """5 trajectory metrics + 3 patterns verdict per archive."""
    # Metric 1: N_f
    nf_pidl = detect_n_f_pidl(merged, "n_bdy")
    if nf_pidl is None:
        nf_pidl = detect_n_f_pidl(merged, "L_inf")
    nf_fem = detect_n_f_fem_csv_endpoint(merged)

    # Metric 2: ᾱ_max(N) — at N_f if available
    last_pidl_alpha = merged["alpha_max_pidl"].dropna().iloc[-1] if len(merged["alpha_max_pidl"].dropna()) else np.nan
    last_fem_alpha = merged["alpha_max"].dropna().iloc[-1] if len(merged["alpha_max"].dropna()) else np.nan
    alpha_max_ratio = last_fem_alpha / last_pidl_alpha if last_pidl_alpha and not np.isnan(last_pidl_alpha) else np.nan

    # Metric 3: α_zone(N) — domain-mean from PIDL f_mean inversion vs FEM alpha_bar_mean
    last_pidl_alpha_bar = merged["alpha_bar_domain_pidl"].dropna().iloc[-1] if "alpha_bar_domain_pidl" in merged and len(merged["alpha_bar_domain_pidl"].dropna()) else np.nan
    last_fem_alpha_bar = merged["alpha_bar_mean"].dropna().iloc[-1] if "alpha_bar_mean" in merged and len(merged["alpha_bar_mean"].dropna()) else np.nan
    alpha_bar_ratio = last_fem_alpha_bar / last_pidl_alpha_bar if last_pidl_alpha_bar and not np.isnan(last_pidl_alpha_bar) else np.nan

    # Metric 4: ψ⁺_zone(N) — only FEM available (PIDL not logged)
    last_fem_psi = merged["psi_tip"].dropna().iloc[-1] if "psi_tip" in merged and len(merged["psi_tip"].dropna()) else np.nan

    # Metric 5: a(N)/x_tip(N) — RMS over common cycles
    common = merged.dropna(subset=["L_inf_pidl", "a_ell"])
    a_rms = float(np.sqrt(((common["L_inf_pidl"] - common["a_ell"]) ** 2).mean())) if len(common) else np.nan

    # Pattern A: boundary α step-jump (only Path C / baseline format)
    if "alpha_bdy_pidl" in merged.columns and not merged["alpha_bdy_pidl"].isna().all():
        bdy_max_pre_nf = merged.loc[merged["N"] < nf_pidl, "alpha_bdy_pidl"].max() if nf_pidl else np.nan
        bdy_at_nf = merged.loc[merged["N"] == nf_pidl, "alpha_bdy_pidl"].iloc[0] if nf_pidl and not merged.loc[merged["N"] == nf_pidl, "alpha_bdy_pidl"].empty else np.nan
        pattern_A_jump = (bdy_at_nf - bdy_max_pre_nf) if not (np.isnan(bdy_max_pre_nf) or np.isnan(bdy_at_nf)) else np.nan
    else:
        bdy_max_pre_nf = bdy_at_nf = pattern_A_jump = np.nan

    # Pattern B: crack tip lead at N_f (PIDL L_inf vs FEM a_ell)
    if nf_pidl and len(merged.loc[merged["N"] == nf_pidl]):
        nf_row = merged.loc[merged["N"] == nf_pidl].iloc[0]
        pattern_B_lead_pct = (
            100.0 * (nf_row["L_inf_pidl"] - nf_row["a_ell"]) / nf_row["a_ell"]
            if not pd.isna(nf_row.get("a_ell")) and nf_row["a_ell"] > 0
            else np.nan
        )
    else:
        pattern_B_lead_pct = np.nan

    return {
        "label": label,
        "N_f_pidl": nf_pidl,
        "N_f_fem": nf_fem,
        "Nf_diff_pct": (100 * (nf_pidl - nf_fem) / nf_fem) if (nf_pidl and nf_fem) else np.nan,
        "PIDL_alpha_max_end": last_pidl_alpha,
        "FEM_alpha_max_end": last_fem_alpha,
        "alpha_max_ratio_FEM_over_PIDL": alpha_max_ratio,
        "PIDL_alpha_bar_domain_end": last_pidl_alpha_bar,
        "FEM_alpha_bar_mean_end": last_fem_alpha_bar,
        "alpha_bar_ratio_FEM_over_PIDL": alpha_bar_ratio,
        "FEM_psi_tip_end": last_fem_psi,
        "a_trajectory_rms_diff": a_rms,
        "Pattern_A_bdy_pre_Nf_max": bdy_max_pre_nf,
        "Pattern_A_bdy_at_Nf": bdy_at_nf,
        "Pattern_A_jump_magnitude": pattern_A_jump,
        "Pattern_B_pidl_lead_pct_at_Nf": pattern_B_lead_pct,
    }


def plot_consolidated(archives: list[dict], out_png: Path) -> None:
    """6-panel multi-archive overlay.
    Each panel shows all archives as PIDL solid + FEM dashed colored by archive."""
    fig, axes = plt.subplots(3, 2, figsize=(14, 13))
    colors = plt.cm.tab10(np.linspace(0, 1, len(archives)))

    metric_specs = [
        ("L_inf_pidl", "a_ell", "crack length / x_tip", False, axes[0, 0]),
        ("alpha_bdy_pidl", "d_max", "boundary damage (PIDL α_bdy / FEM d_max)", False, axes[0, 1]),
        ("alpha_max_pidl", "alpha_max", "ᾱ_max accumulator", True, axes[1, 0]),
        ("alpha_bar_domain_pidl", "alpha_bar_mean", "α_zone mean (PIDL via f_mean inversion / FEM direct)", False, axes[1, 1]),
        (None, "psi_tip", "ψ⁺_tip (FEM only — PIDL not logged)", True, axes[2, 0]),
        ("Kt_pidl", "Kt", "Kt", True, axes[2, 1]),
    ]

    for pidl_col, fem_col, title, log_scale, ax in metric_specs:
        for i, arch in enumerate(archives):
            df = arch["df"]
            label = arch["label"]
            color = colors[i]
            if pidl_col and pidl_col in df.columns:
                m = df.dropna(subset=[pidl_col])
                ax.plot(m["N"], m[pidl_col], "-", color=color, lw=1.3,
                        label=f"PIDL {label}" if pidl_col == "L_inf_pidl" else None)
            if fem_col and fem_col in df.columns:
                m = df.dropna(subset=[fem_col])
                ax.plot(m["N"], m[fem_col], "--", color=color, lw=1.0, alpha=0.7,
                        label=f"FEM {label}" if pidl_col == "L_inf_pidl" else None)
        ax.set_xlabel("Cycle N")
        ax.set_ylabel(title)
        ax.set_title(title)
        if log_scale:
            ax.set_yscale("log")
        ax.grid(True, alpha=0.3, which="both" if log_scale else "major")
        if pidl_col == "L_inf_pidl":
            ax.legend(fontsize=8, loc="best")

    fig.suptitle(
        "PIDL vs FEM trajectory — multi-archive overlay (May-3, 5-metric eval per external expert)\n"
        "Solid = PIDL, Dashed = FEM (matched colors per archive)",
        fontsize=12,
    )
    plt.tight_layout()
    plt.savefig(out_png, dpi=120, bbox_inches="tight")
    print(f"saved {out_png}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--archives", required=True, help="comma-sep list of label:pidl_log:fem_csv triples (each ;-separated)")
    p.add_argument("--out-prefix", default="posthoc_5metric")
    args = p.parse_args()

    # Parse archive specs
    archives = []
    for spec in args.archives.split(","):
        label, pidl_log, fem_csv = spec.split(";")
        archives.append({"label": label.strip(), "pidl_log": pidl_log.strip(), "fem_csv": fem_csv.strip()})

    # Process each
    verdicts = []
    archives_for_plot = []
    for arch in archives:
        print(f"\n=== {arch['label']} ===")
        pidl_df = parse_pidl_log(Path(arch["pidl_log"]))
        fem_df = pd.read_csv(arch["fem_csv"])
        merged = merge_trajectories(pidl_df, fem_df)

        out_csv = Path(f"{args.out_prefix}_{arch['label']}.csv")
        merged.to_csv(out_csv, index=False)
        print(f"  saved {out_csv}")

        verdict = compute_5metric_verdict(merged, arch["label"])
        for k, v in verdict.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                if pd.notna(v):
                    print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
                else:
                    print(f"  {k}: nan")
            else:
                print(f"  {k}: {v}")
        verdicts.append(verdict)
        archives_for_plot.append({"label": arch["label"], "df": merged})

    # Consolidated verdict CSV
    vdf = pd.DataFrame(verdicts)
    out_csv = Path(f"{args.out_prefix}_consolidated.csv")
    vdf.to_csv(out_csv, index=False)
    print(f"\nsaved consolidated verdict: {out_csv}")
    print("\n=== CONSOLIDATED VERDICT ===")
    print(vdf.to_string(index=False))

    # Multi-archive overlay plot
    out_png = Path(f"{args.out_prefix}_consolidated.png")
    plot_consolidated(archives_for_plot, out_png)


if __name__ == "__main__":
    main()
