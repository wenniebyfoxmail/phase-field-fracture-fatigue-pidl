#!/usr/bin/env python3
"""Compare FEM/PIDL fields after excluding the initial pre-crack corridor."""
from __future__ import annotations

import argparse
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def masked_stats(values: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    selected = values[mask]
    if selected.size == 0:
        return {"max": np.nan, "mean": np.nan, "min": np.nan, "sum": 0.0}
    return {
        "max": float(np.nanmax(selected)),
        "mean": float(np.nanmean(selected)),
        "min": float(np.nanmin(selected)),
        "sum": float(np.nansum(selected)),
    }


def load_fem_masked(mat_path: Path, half_width: float, x_max: float) -> pd.DataFrame:
    rows = []
    with h5py.File(mat_path, "r") as handle:
        cycles = np.asarray(handle["cycles"]).reshape(-1).astype(int)
        centroids = np.asarray(handle["element_centroids"]).T
        x = centroids[:, 0]
        y = centroids[:, 1]
        precrack = (x <= x_max) & (np.abs(y) <= half_width)
        outside = ~precrack
        for i, cycle in enumerate(cycles):
            d = np.asarray(handle["d_elem"][i]).reshape(-1)
            hist = np.asarray(handle["alpha_bar_elem"][i]).reshape(-1)
            f = np.asarray(handle["f_fatigue_elem"][i]).reshape(-1)
            psi = np.asarray(handle["psi_plus_elem"][i]).reshape(-1)
            d_out = masked_stats(d, outside)
            hist_out = masked_stats(hist, outside)
            f_out = masked_stats(f, outside)
            psi_out = masked_stats(psi, outside)
            rows.append({
                "cycle": int(cycle),
                "precrack_half_width": half_width,
                "precrack_x_max": x_max,
                "fem_n_elem_precrack_mask": int(precrack.sum()),
                "fem_n_elem_outside_precrack": int(outside.sum()),
                "fem_d_max_outside_precrack": d_out["max"],
                "fem_d_mean_outside_precrack": d_out["mean"],
                "fem_hist_max_outside_precrack": hist_out["max"],
                "fem_hist_mean_outside_precrack": hist_out["mean"],
                "fem_f_min_outside_precrack": f_out["min"],
                "fem_f_mean_outside_precrack": f_out["mean"],
                "fem_psi_max_outside_precrack": psi_out["max"],
                "fem_psi_mean_outside_precrack": psi_out["mean"],
            })
    return pd.DataFrame(rows)


def load_pidl_masked(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    return df.rename(columns={
        "n_elem_precrack_mask": "pidl_n_elem_precrack_mask",
        "n_elem_outside_precrack": "pidl_n_elem_outside_precrack",
        "hist_max_outside_precrack": "pidl_hist_max_outside_precrack",
        "hist_mean_outside_precrack": "pidl_hist_mean_outside_precrack",
        "f_min_outside_precrack": "pidl_f_min_outside_precrack",
        "f_mean_outside_precrack": "pidl_f_mean_outside_precrack",
        "psi_max_outside_precrack": "pidl_psi_max_outside_precrack",
        "psi_mean_outside_precrack": "pidl_psi_mean_outside_precrack",
        "E_el_outside_precrack": "pidl_E_el_outside_precrack",
        "E_d_outside_precrack": "pidl_E_d_outside_precrack",
        "E_hist_outside_precrack": "pidl_E_hist_outside_precrack",
    })


def safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    return num / den.replace(0.0, np.nan)


def build_comparison(fem_mat: Path, pidl_csv: Path, fem_csv: Path,
                     half_width: float, x_max: float) -> pd.DataFrame:
    fem_masked = load_fem_masked(fem_mat, half_width, x_max)
    fem_energy = pd.read_csv(fem_csv)[["cycle", "E_el", "E_d"]].rename(
        columns={"E_el": "fem_E_el", "E_d": "fem_E_d"},
    )
    pidl = load_pidl_masked(pidl_csv)
    cols = [
        "cycle",
        "pidl_n_elem_precrack_mask",
        "pidl_n_elem_outside_precrack",
        "pidl_hist_max_outside_precrack",
        "pidl_hist_mean_outside_precrack",
        "pidl_f_min_outside_precrack",
        "pidl_f_mean_outside_precrack",
        "pidl_psi_max_outside_precrack",
        "pidl_psi_mean_outside_precrack",
        "pidl_E_el_outside_precrack",
        "pidl_E_d_outside_precrack",
        "pidl_E_hist_outside_precrack",
    ]
    merged = fem_masked.merge(fem_energy, on="cycle", how="inner").merge(
        pidl[cols], on="cycle", how="inner",
    )
    merged["fem_E_d_increment_from_first"] = merged["fem_E_d"] - merged["fem_E_d"].iloc[0]
    merged["pidl_E_d_outside_increment_from_first"] = (
        merged["pidl_E_d_outside_precrack"] - merged["pidl_E_d_outside_precrack"].iloc[0]
    )
    merged["ratio_E_d_outside_increment_pidl_over_fem"] = safe_ratio(
        merged["pidl_E_d_outside_increment_from_first"],
        merged["fem_E_d_increment_from_first"],
    )
    merged["ratio_hist_max_outside_pidl_over_fem"] = safe_ratio(
        merged["pidl_hist_max_outside_precrack"],
        merged["fem_hist_max_outside_precrack"],
    )
    merged["ratio_hist_mean_outside_pidl_over_fem"] = safe_ratio(
        merged["pidl_hist_mean_outside_precrack"],
        merged["fem_hist_mean_outside_precrack"],
    )
    merged["ratio_f_min_outside_pidl_over_fem"] = safe_ratio(
        merged["pidl_f_min_outside_precrack"],
        merged["fem_f_min_outside_precrack"],
    )
    merged["ratio_psi_max_outside_pidl_over_fem"] = safe_ratio(
        merged["pidl_psi_max_outside_precrack"],
        merged["fem_psi_max_outside_precrack"],
    )
    return merged


def plot(df: pd.DataFrame, out_png: Path, out_pdf: Path | None) -> None:
    cycle = df["cycle"]
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.5), constrained_layout=True)

    ax = axes[0, 0]
    ax.semilogy(cycle, df["fem_hist_max_outside_precrack"], label="FEM outside hist max")
    ax.semilogy(cycle, df["pidl_hist_max_outside_precrack"], label="PIDL outside hist max")
    ax.semilogy(cycle, df["fem_hist_mean_outside_precrack"], label="FEM outside hist mean", ls="--")
    ax.semilogy(cycle, df["pidl_hist_mean_outside_precrack"], label="PIDL outside hist mean", ls="--")
    ax.set_title("Outside Pre-Crack History")
    ax.set_xlabel("cycle")
    ax.set_ylabel("history")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    ax = axes[0, 1]
    ax.semilogy(cycle, df["fem_f_min_outside_precrack"], label="FEM outside min f")
    ax.semilogy(cycle, df["pidl_f_min_outside_precrack"], label="PIDL outside min f")
    ax.set_title("Outside Pre-Crack Degradation")
    ax.set_xlabel("cycle")
    ax.set_ylabel("min f")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    ax = axes[1, 0]
    ax.plot(cycle, df["fem_E_d_increment_from_first"], label="FEM Delta E_d")
    ax.plot(cycle, df["pidl_E_d_outside_increment_from_first"], label="PIDL outside Delta E_d")
    ax.set_title("Incremental Damage Energy")
    ax.set_xlabel("cycle")
    ax.set_ylabel("Delta E_d")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    ax = axes[1, 1]
    ax.semilogy(cycle, df["ratio_hist_max_outside_pidl_over_fem"], label="outside hist max ratio")
    ax.semilogy(cycle, df["ratio_f_min_outside_pidl_over_fem"], label="outside f_min ratio")
    ax.semilogy(cycle, df["ratio_E_d_outside_increment_pidl_over_fem"], label="outside Delta E_d ratio")
    ax.axhline(1.0, color="0.3", ls="--", lw=1)
    ax.set_title("PIDL / FEM Outside-Mask Ratios")
    ax.set_xlabel("cycle")
    ax.set_ylabel("ratio")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)
    if out_pdf is not None:
        fig.savefig(out_pdf)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fem-mat", type=Path, required=True)
    parser.add_argument("--fem-csv", type=Path, required=True)
    parser.add_argument("--pidl-diag-csv", type=Path, required=True)
    parser.add_argument("--precrack-half-width", type=float, default=0.02)
    parser.add_argument("--precrack-x-max", type=float, default=0.0)
    parser.add_argument("--out-csv", type=Path, required=True)
    parser.add_argument("--out-png", type=Path, required=True)
    parser.add_argument("--out-pdf", type=Path, default=None)
    args = parser.parse_args()

    df = build_comparison(
        args.fem_mat, args.pidl_diag_csv, args.fem_csv,
        args.precrack_half_width, args.precrack_x_max,
    )
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out_csv, index=False)
    plot(df, args.out_png, args.out_pdf)
    print(f"Wrote {args.out_csv}")
    print(f"Wrote {args.out_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
