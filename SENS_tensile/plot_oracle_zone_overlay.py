#!/usr/bin/env python3
"""plot_oracle_zone_overlay.py — α field with FEM-override zone (circle) overlaid.

For Oracle (fem_oracle) runs: re-renders α-field PNGs with a dashed circle of
radius `zone_radius` (default 0.02) at the current crack-tip (x_tip, 0). This
makes the spatial extent of the FEM-supervised override visible on the same
plot as the resulting α field.

Defaults to the oracle_zone0.02 archive. x_tip per cycle is read from
best_models/J_integral.csv with linear interpolation for missing cycles.

Usage:
    python plot_oracle_zone_overlay.py                                      # default archive, c0/20/40/60/80
    python plot_oracle_zone_overlay.py --archive <path> --cycles 0 40 80
    python plot_oracle_zone_overlay.py --archive <path> --radius 0.05
"""
from __future__ import annotations
import argparse
import re
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.tri import Triangulation

HERE = Path(__file__).parent.resolve()

DEFAULT_ARCHIVE = HERE / (
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
    "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
    "N300_R0.0_Umax0.12_oracle_zone0.02")


def parse_radius_from_name(archive: Path, fallback=0.02) -> float:
    m = re.search(r"_zone([\d.]+)", archive.name)
    return float(m.group(1)) if m else fallback


def load_xtip_table(archive: Path) -> pd.DataFrame | None:
    f = archive / "best_models" / "J_integral.csv"
    return pd.read_csv(f) if f.exists() else None


def xtip_at_cycle(table: pd.DataFrame | None, cyc: int) -> float:
    if table is None:
        return 0.0
    return float(np.interp(cyc, table["cycle"], table["x_tip"],
                           left=table["x_tip"].iloc[0],
                           right=table["x_tip"].iloc[-1]))


def render_one(snap_npy: Path, x_tip: float, radius: float,
               cyc: int, out_png: Path, title_extra: str = ""):
    data = np.load(snap_npy).astype(np.float64)
    if data.shape[1] != 3:
        print(f"[skip] {snap_npy.name} unexpected shape {data.shape}")
        return
    x, y, a = data[:, 0], data[:, 1], data[:, 2]
    a_clip = np.clip(a, 0.0, 1.0)
    tri = Triangulation(x, y)

    fig, ax = plt.subplots(figsize=(5, 4.5), constrained_layout=True)
    ax.set_aspect("equal")
    ax.set_xlim(-0.5, 0.5); ax.set_ylim(-0.5, 0.5)
    cf = ax.tricontourf(tri, a_clip, levels=np.linspace(0, 1, 21),
                        cmap="hot", extend="neither")
    fig.colorbar(cf, ax=ax, shrink=0.85, label="α")
    ax.plot([-0.5, 0.0], [0.0, 0.0], "c-", lw=1.2, label="initial slit")

    circ = Circle((x_tip, 0.0), radius, fill=False,
                  edgecolor="lime", linestyle="--", linewidth=1.6,
                  label=f"override zone r={radius}")
    ax.add_patch(circ)
    ax.plot([x_tip], [0.0], "go", ms=5, label=f"x_tip={x_tip:.3f}")
    ax.legend(loc="upper right", fontsize=7, framealpha=0.85)
    ax.set_title(f"α + override zone @ c={cyc}  α_max={a.max():.3f}{title_extra}")
    fig.savefig(out_png, dpi=200)
    plt.close(fig)
    print(f"[saved] {out_png.name}  x_tip={x_tip:.3f}  α_max={a.max():.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    ap.add_argument("--cycles", type=int, nargs="*",
                    default=[0, 20, 40, 60, 80])
    ap.add_argument("--radius", type=float, default=None)
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()

    archive = args.archive
    if not archive.is_dir():
        print(f"[error] archive not found: {archive}")
        return 1

    radius = args.radius if args.radius is not None else parse_radius_from_name(archive)
    out_dir = args.out_dir or (archive / "oracle_zone_snapshots")
    out_dir.mkdir(parents=True, exist_ok=True)

    table = load_xtip_table(archive)
    snap_dir = archive / "alpha_snapshots"

    print(f"[setup] archive={archive.name}")
    print(f"[setup] radius={radius}  cycles={args.cycles}")

    for cyc in args.cycles:
        snap = snap_dir / f"alpha_cycle_{cyc:04d}.npy"
        if not snap.is_file():
            print(f"[skip] {snap.name} missing")
            continue
        xt = xtip_at_cycle(table, cyc)
        out = out_dir / f"oracle_zone_c{cyc:04d}.png"
        render_one(snap, xt, radius, cyc, out)


if __name__ == "__main__":
    main()
