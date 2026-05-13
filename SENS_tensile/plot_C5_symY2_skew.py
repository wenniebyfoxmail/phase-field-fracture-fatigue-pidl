#!/usr/bin/env python3
"""plot_C5_symY2_skew.py — α field + mirror residual for C5 (hard-sym y² input + odd-parity output).

Thin wrapper around plot_fig_B_soft_sym_mirror.compute_mirror_residual; expected
to show **machine-precision V4** (residual ~ 1e-7) because C5 enforces α(x,y)=α(x,−y)
by construction, in contrast to soft-sym (Fig B) where penalty leaves V4≈0.022.

Usage:
    python plot_C5_symY2_skew.py                          # uses local N=10 archive c0
    python plot_C5_symY2_skew.py --archive <path>  --cycle <NNNN>
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation

HERE = Path(__file__).parent.resolve()
sys.path.insert(0, str(HERE))
from plot_fig_B_soft_sym_mirror import compute_mirror_residual

DEFAULT_ARCHIVE = HERE / (
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
    "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
    "N10_R0.0_Umax0.12_symY2")


def latest_cycle_npy(archive: Path) -> Path | None:
    snap = archive / "alpha_snapshots"
    npys = sorted(snap.glob("alpha_cycle_*.npy"),
                  key=lambda p: int(re.findall(r"\d+", p.stem)[-1]))
    return npys[-1] if npys else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    ap.add_argument("--cycle", type=int, default=None,
                    help="Cycle index (default: latest available)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--label", default=None)
    args = ap.parse_args()

    archive = args.archive
    if args.cycle is None:
        snap = latest_cycle_npy(archive)
        if snap is None:
            print(f"[error] no alpha_cycle_*.npy in {archive}/alpha_snapshots")
            return 1
        cyc = int(re.findall(r"\d+", snap.stem)[-1])
    else:
        cyc = args.cycle
        snap = archive / "alpha_snapshots" / f"alpha_cycle_{cyc:04d}.npy"
        if not snap.is_file():
            print(f"[error] missing {snap}")
            return 1

    label = args.label or f"C5 (y² hard sym) — {archive.name.split('_Umax')[-1]}"
    out = args.out or (HERE / f"fig_C5_symY2_skew_cycle{cyc:04d}.pdf")

    data = np.load(snap).astype(np.float64)
    x, y, a = data[:, 0], data[:, 1], data[:, 2]

    err = compute_mirror_residual(x, y, a)
    rms = float(np.sqrt(np.mean(err ** 2)))
    max_abs = float(np.max(np.abs(err)))

    tri = Triangulation(x, y)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.0), constrained_layout=True)

    a_clip = np.clip(a, 0.0, 1.0)
    cf1 = axes[0].tricontourf(tri, a_clip, levels=np.linspace(0.0, 1.0, 21),
                              cmap="hot", extend="neither")
    axes[0].set_aspect("equal")
    axes[0].set_xlim(-0.5, 0.5); axes[0].set_ylim(-0.5, 0.5)
    axes[0].set_xlabel("x"); axes[0].set_ylabel("y")
    axes[0].set_title(f"(a) α field @ cycle {cyc}  (α_max={a.max():.3f})")
    axes[0].plot([-0.5, 0.0], [0.0, 0.0], "c-", lw=1.5, label="initial slit")
    axes[0].legend(loc="upper right", fontsize=8)
    fig.colorbar(cf1, ax=axes[0], shrink=0.85).set_label("α")

    vmax = max(1e-12, max(abs(err.min()), abs(err.max())))
    cf2 = axes[1].tricontourf(tri, err, levels=np.linspace(-vmax, vmax, 21),
                              cmap="RdBu_r")
    axes[1].set_aspect("equal")
    axes[1].set_xlim(-0.5, 0.5); axes[1].set_ylim(-0.5, 0.5)
    axes[1].set_xlabel("x"); axes[1].set_ylabel("y")
    axes[1].set_title(f"(b) Mirror residual α(x,y) − α(x,−y)\n"
                      f"RMS = {rms:.3e},  max|·| = {max_abs:.3e}")
    axes[1].plot([-0.5, 0.0], [0.0, 0.0], "k-", lw=1.5)
    fig.colorbar(cf2, ax=axes[1], shrink=0.85).set_label("Δα (signed)")

    fig.suptitle(f"C5 hard-sym (y² input + odd output) — {label}", y=1.02)
    fig.savefig(out, bbox_inches="tight", dpi=150)
    print(f"saved: {out}")
    print(f"  archive: {archive.name}")
    print(f"  cycle: {cyc}, α_max: {a.max():.3f}")
    print(f"  V4 RMS:    {rms:.6e}  (expect machine precision for C5)")
    print(f"  V4 max|·|: {max_abs:.6e}")


if __name__ == "__main__":
    main()
