#!/usr/bin/env python3
"""plot_sdf_ribbon_N30_5panel.py — 5-panel mechanism evidence figure

Per user May 14: don't just report c29 numbers; build the ΔN(c) lead curve
by inverse-interpolating each SDF x_tip(c) against baseline x_tip(c) trajectory.

5 panels:
  1. α̅_max(c)                   — primary fatigue signal
  2. Kt(c)                       — stress concentration ratio
  3. ψ⁺_max(c)                   — peak elastic energy density (mechanism indicator)
  4. x_tip(c)                    — crack tip x-position (propagation)
  5. ΔN(c) = baseline_cycle_to_reach( SDF x_tip(c) ) − c
                                 — cycles SDF is AHEAD of baseline

Usage:
    python3 plot_sdf_ribbon_N30_5panel.py <baseline> <sdf_archive>
"""
from __future__ import annotations
import sys, argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load(archive: Path) -> dict:
    bm = archive / "best_models"
    ab = np.load(bm / "alpha_bar_vs_cycle.npy")[:, 0]   # col 0 = max
    kt = np.load(bm / "Kt_vs_cycle.npy")
    psi_p = bm / "psi_peak_vs_cycle.npy"
    psi = np.load(psi_p)[:, 1] if psi_p.exists() else None    # col 1 = max
    for fn in ("x_tip_psi_vs_cycle.npy", "x_tip_alpha_vs_cycle.npy",
               "x_tip_vs_cycle.npy"):
        if (bm / fn).exists():
            xt = np.load(bm / fn)
            break
    return dict(alpha_bar=ab, Kt=kt, psi_tip=psi, x_tip=xt)


def cycle_to_reach(base_xtip: np.ndarray, target: float) -> float:
    """Linear-interpolate baseline cycle at which x_tip == target.
    Returns NaN if target outside [base_xtip[0], base_xtip[-1]].
    """
    # base_xtip is generally monotone non-decreasing (with clamping); ensure
    # strictly monotone by taking cummax (latest value once reached).
    bm = np.maximum.accumulate(base_xtip)
    if target < bm[0] or target > bm[-1]:
        return float("nan")
    # find first index where bm > target, interpolate between i-1 and i
    i = int(np.searchsorted(bm, target))
    if i == 0:
        return 0.0
    if i >= len(bm):
        return float(len(bm) - 1)
    x0, x1 = bm[i - 1], bm[i]
    if x1 == x0:
        return float(i - 1)
    return float(i - 1 + (target - x0) / (x1 - x0))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("baseline", type=Path)
    p.add_argument("sdf",      type=Path)
    p.add_argument("-o", "--out", type=Path, default=None)
    args = p.parse_args()

    base = load(args.baseline)
    sdf  = load(args.sdf)

    n_sdf = len(sdf["alpha_bar"])
    n_base_show = min(60, len(base["alpha_bar"]))      # show up to c60 of baseline for context

    fig, axes_grid = plt.subplots(2, 3, figsize=(15, 9))
    axes = axes_grid.flatten()           # 6 slots; 6th will be hidden

    def two_lines(ax, key, title, ylabel=None):
        if base[key] is None or sdf[key] is None:
            ax.text(0.5, 0.5, f"{key} missing", ha="center", va="center",
                    transform=ax.transAxes); ax.set_title(title); return
        ax.plot(np.arange(n_base_show), base[key][:n_base_show], "k-",
                lw=2.2, label="baseline (N=300, c0..c60 shown)")
        ax.plot(np.arange(n_sdf), sdf[key], "b-o", ms=4, lw=1.5,
                label="SDF v1 (ε=1e-3 seed=1)")
        ax.set_xlabel("cycle"); ax.set_title(title)
        if ylabel: ax.set_ylabel(ylabel)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, loc="best")

    two_lines(axes[0], "alpha_bar", "α̅_max(c)", "α̅_max at peak elem")
    two_lines(axes[1], "Kt",        "Kt(c)",     "max σ_xx / σ_far")
    two_lines(axes[2], "psi_tip",   "ψ⁺ peak(c)","ψ⁺ at peak elem")
    two_lines(axes[3], "x_tip",     "x_tip(c)",  "crack tip x")

    # ── Panel 5: ΔN(c) lead curve ────────────────────────────────────────
    ax = axes[4]
    sdf_xt = np.maximum.accumulate(sdf["x_tip"])
    base_xt = np.maximum.accumulate(base["x_tip"])
    cs = np.arange(n_sdf)
    delta_N = np.array([cycle_to_reach(base_xt, float(sdf_xt[c])) - c
                        for c in cs])
    ax.plot(cs, delta_N, "g-o", ms=4, lw=1.5)
    ax.axhline(0, color="k", ls="--", alpha=0.5, lw=0.8)
    ax.set_xlabel("SDF cycle  c")
    ax.set_ylabel("ΔN = baseline_cyc(x_tip_sdf(c)) − c")
    ax.set_title("ΔN(c)  — cycles SDF is AHEAD")
    ax.grid(alpha=0.3)
    # annotate end value
    if not np.isnan(delta_N[-1]):
        ax.annotate(f"ΔN(c{n_sdf-1}) = {delta_N[-1]:.2f}",
                    xy=(n_sdf-1, delta_N[-1]),
                    xytext=(n_sdf-1, delta_N[-1] + 0.3),
                    fontsize=9, ha="right",
                    bbox=dict(boxstyle="round,pad=0.2",
                              fc="lightyellow", ec="gray", alpha=0.85))

    # Hide the unused 6th subplot
    axes[5].axis("off")

    fig.suptitle("SDF ribbon (uv_only, ε=1e-3, seed=1) vs baseline — "
                 "N=30 mechanism evidence (5-panel)", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.96))

    if args.out is None:
        out_dir = Path(__file__).resolve().parent.parent / "references_local" / "sdf_ribbon_smoke"
        out_dir.mkdir(parents=True, exist_ok=True)
        args.out = out_dir / "N30_5panel_mechanism.png"

    fig.savefig(args.out, dpi=140)
    print(f"saved: {args.out}")

    # ── Numeric summary print ───────────────────────────────────────────
    print("\n=== summary ===")
    print(f"{'c':>3} | {'α̅_b':>6} {'α̅_s':>6} | {'Kt_b':>5} {'Kt_s':>5} | "
          f"{'ψ_b':>6} {'ψ_s':>6} | {'xt_b':>6} {'xt_s':>6} | {'ΔN':>5}")
    print("-" * 92)
    for c in [0, 4, 5, 10, 15, 20, 25, 29]:
        if c >= n_sdf or c >= len(base["alpha_bar"]):
            continue
        psi_b_str = f"{base['psi_tip'][c]:6.3f}" if base['psi_tip'] is not None else "  N/A"
        psi_s_str = f"{sdf['psi_tip'][c]:6.3f}" if sdf['psi_tip'] is not None else "  N/A"
        print(f"c{c:>2} | {base['alpha_bar'][c]:6.3f} {sdf['alpha_bar'][c]:6.3f} | "
              f"{base['Kt'][c]:5.3f} {sdf['Kt'][c]:5.3f} | "
              f"{psi_b_str} {psi_s_str} | "
              f"{base['x_tip'][c]:6.4f} {sdf['x_tip'][c]:6.4f} | "
              f"{delta_N[c]:5.2f}")


if __name__ == "__main__":
    main()
