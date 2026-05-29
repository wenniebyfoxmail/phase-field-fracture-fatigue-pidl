#!/usr/bin/env python3
"""Analyze FEM soft-hist0 state timing against PIDL cycle-0 fields.

This script consumes the FEM Request 20 handoff and the PIDL initial-state
export produced by `export_pidl_initial_state.py`.  Its main purpose is to
avoid calling the old FEM c1 export an "initial-state" comparison: Request 20
shows that old c1 mixed end-cycle damage/history with peak-over-cycle psi.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm
from scipy.spatial import cKDTree

HERE = Path(__file__).parent.resolve()
sys.path.insert(0, str(HERE))

from posthoc_mesh_probe_alignment import metrics

DEFAULT_FEM_DIR = Path(
    "/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/"
    "PIDL result/_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_state_timing_2026-05-29"
)
DEFAULT_ANALYSIS_DIR = HERE.parent / "_analysis_fem_mechanism_20260528"


def load_fem_state_handoff(fem_dir: Path) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    csv_path = fem_dir / "state_timing_metrics.csv"
    mat_path = fem_dir / "state_timing_element_fields.mat"
    df = pd.read_csv(csv_path)
    with h5py.File(mat_path, "r") as f:
        data = {
            "centroids": np.asarray(f["element_centroids"], dtype=float).T,
            "areas": np.asarray(f["element_area"], dtype=float).reshape(-1),
            "d": np.asarray(f["d_elem"], dtype=float),
            "alpha_bar": np.asarray(f["alpha_bar_elem"], dtype=float),
            "f": np.asarray(f["f_fatigue_elem"], dtype=float),
            "psi": np.asarray(f["psi_plus_elem"], dtype=float),
            "psi_peak": np.asarray(f["psi_plus_peak_to_date_elem"], dtype=float),
        }
    data["centroids"][:, :2] -= 0.5
    return df, data


def load_pidl_initial(npz_path: Path) -> dict[str, np.ndarray]:
    npz = np.load(npz_path)
    return {
        "nodes": npz["nodes"],
        "conn": npz["connectivity"],
        "centroids": npz["element_centroids"],
        "areas": npz["element_area"],
        "hist_alpha": npz["hist_alpha_init_elem"],
        "pretrain_alpha": npz["alpha_pretrain_elem"],
        "hist_fat0": npz["hist_fat0_elem"],
        "f0": npz["f_fatigue0_elem"],
    }


def comparison_rows(
    fem_name: str,
    fem_values: np.ndarray,
    pidl_name: str,
    pidl_values: np.ndarray,
    pidl: dict[str, np.ndarray],
) -> list[dict[str, float | str]]:
    fem_m = metrics(fem_values, pidl["areas"], pidl["centroids"])
    pidl_m = metrics(pidl_values, pidl["areas"], pidl["centroids"])
    rows = []
    for metric_name in sorted(set(fem_m) & set(pidl_m)):
        fv = fem_m[metric_name]
        pv = pidl_m[metric_name]
        rows.append(
            {
                "comparison": f"{fem_name} vs {pidl_name}",
                "metric": metric_name,
                "FEM_projected": fv,
                "PIDL": pv,
                "PIDL_minus_FEM": pv - fv,
                "PIDL_over_FEM": pv / fv if np.isfinite(fv) and abs(fv) > 1e-30 else np.nan,
            }
        )
    return rows


def project_nearest_to_pidl(
    fem_centroids: np.ndarray,
    fem_values: np.ndarray,
    pidl_centroids: np.ndarray,
) -> np.ndarray:
    """Sample FEM element means at each PIDL element centroid.

    Request 20 FEM has one value per Q4 element, while PIDL uses triangles.  A
    FEM-element-to-PIDL area bucket leaves unfilled PIDL triangles near refined
    regions, so for state timing visuals we use a full common-probe comparison:
    every PIDL triangle centroid queries its nearest FEM element centroid.
    """
    tree = cKDTree(fem_centroids)
    _, idx = tree.query(pidl_centroids, k=1)
    return np.asarray(fem_values, dtype=float).reshape(-1)[idx]


def plot_state0_damage(
    pidl: dict[str, np.ndarray],
    fem_state0_d_projected: np.ndarray,
    out_path: Path,
) -> None:
    tri = mtri.Triangulation(pidl["nodes"][:, 0], pidl["nodes"][:, 1], pidl["conn"])
    hist = pidl["hist_alpha"]
    pretrain = pidl["pretrain_alpha"]
    diff_hist = hist - fem_state0_d_projected
    diff_pretrain = pretrain - fem_state0_d_projected
    vmax = float(np.nanmax(np.abs(np.concatenate([diff_hist, diff_pretrain]))))
    if not np.isfinite(vmax) or vmax == 0.0:
        vmax = 1e-6

    fig, axes = plt.subplots(2, 3, figsize=(12.2, 7.3), constrained_layout=True)
    panels = [
        ("FEM state0 d -> PIDL mesh", fem_state0_d_projected, "viridis", None, 0.0, 1.0),
        ("PIDL hist_alpha_init", hist, "viridis", None, 0.0, 1.0),
        ("PIDL pretrain alpha", pretrain, "viridis", None, 0.0, 1.0),
        ("PIDL hist - FEM state0", diff_hist, "RdBu_r", TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax), None, None),
        ("PIDL pretrain - FEM state0", diff_pretrain, "RdBu_r", TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax), None, None),
        ("pretrain - hist", pretrain - hist, "RdBu_r", TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax), None, None),
    ]
    for ax, (title, values, cmap, norm, vmin, vmax_panel) in zip(axes.flat, panels):
        im = ax.tripcolor(tri, values, shading="flat", cmap=cmap, norm=norm, vmin=vmin, vmax=vmax_panel)
        ax.set_title(title, fontsize=10)
        ax.set_aspect("equal")
        ax.set_xlim(-0.52, 0.52)
        ax.set_ylim(-0.52, 0.52)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def plot_timing_scalars(df: pd.DataFrame, out_path: Path) -> None:
    labels = df["state_label"].astype(str).tolist()
    x = np.arange(len(labels))
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 7.6), constrained_layout=True)
    series = [
        ("d_max", "damage max"),
        ("alpha_bar_max", "alpha_bar max"),
        ("psi_plus_max", "current psi+ max"),
        ("psi_plus_peak_to_date_max", "peak-to-date psi+ max"),
    ]
    for ax, (col, title) in zip(axes.flat, series):
        ax.plot(x, df[col], marker="o", lw=1.6)
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=65, ha="right", fontsize=7)
        ax.grid(True, color="0.88", lw=0.7)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fem-dir", type=Path, default=DEFAULT_FEM_DIR)
    ap.add_argument("--pidl-initial", type=Path, default=DEFAULT_ANALYSIS_DIR / "pidl_baseline_initial_state_fields.npz")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_ANALYSIS_DIR)
    args = ap.parse_args()

    df, fem = load_fem_state_handoff(args.fem_dir)
    pidl = load_pidl_initial(args.pidl_initial)

    state0_idx = int(df.index[df["state_label"] == "state0_initial_preload_prehistory"][0])
    peak_pre_idx = int(df.index[df["state_label"] == "cycle1_peak_pre_history_refresh"][0])
    peak_post_idx = int(df.index[df["state_label"] == "cycle1_peak_post_history_refresh"][0])
    unloaded_post_idx = int(df.index[df["state_label"] == "cycle1_unloaded_post_history_refresh"][0])

    fem_state0_d = project_nearest_to_pidl(fem["centroids"], fem["d"][state0_idx], pidl["centroids"])
    fem_state0_ab = project_nearest_to_pidl(fem["centroids"], fem["alpha_bar"][state0_idx], pidl["centroids"])
    fem_state0_f = project_nearest_to_pidl(fem["centroids"], fem["f"][state0_idx], pidl["centroids"])

    rows = []
    rows += comparison_rows("FEM state0 d", fem_state0_d, "PIDL hist_alpha_init", pidl["hist_alpha"], pidl)
    rows += comparison_rows("FEM state0 d", fem_state0_d, "PIDL pretrain alpha", pidl["pretrain_alpha"], pidl)
    rows += comparison_rows("FEM state0 alpha_bar", fem_state0_ab, "PIDL hist_fat0", pidl["hist_fat0"], pidl)
    rows += comparison_rows("FEM state0 f", fem_state0_f, "PIDL f0", pidl["f0"], pidl)

    # Timing deltas on native FEM rows: these explain why old c1 is not initial.
    timing_pairs = [
        ("state0_to_step1_pre", state0_idx, int(df.index[df["state_label"] == "cycle1_step1_pre_history_refresh"][0])),
        ("peak_pre_to_peak_post", peak_pre_idx, peak_post_idx),
        ("peak_post_to_unloaded_post", peak_post_idx, unloaded_post_idx),
    ]
    for name, i0, i1 in timing_pairs:
        for field_key, field_label in [
            ("d", "d"),
            ("alpha_bar", "alpha_bar"),
            ("f", "f_fatigue"),
            ("psi", "psi_plus_current"),
            ("psi_peak", "psi_plus_peak_to_date"),
        ]:
            delta = fem[field_key][i1] - fem[field_key][i0]
            rows.append(
                {
                    "comparison": name,
                    "metric": f"{field_label}_native_delta_max_abs",
                    "FEM_projected": np.nan,
                    "PIDL": np.nan,
                    "PIDL_minus_FEM": float(np.nanmax(np.abs(delta))),
                    "PIDL_over_FEM": np.nan,
                }
            )

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "soft_hist0_state_timing_pidl_initial_comparison.csv"
    pd.DataFrame(rows).to_csv(summary_path, index=False)

    plot_state0_damage(
        pidl,
        fem_state0_d,
        out_dir / "figures" / "soft_hist0_state0_fem_vs_pidl_initial_damage.png",
    )
    plot_timing_scalars(
        df,
        out_dir / "figures" / "soft_hist0_fem_state_timing_scalars.png",
    )

    selected_cols = [
        "state_label",
        "load_factor",
        "u_y",
        "d_max",
        "alpha_bar_max",
        "f_fatigue_min",
        "psi_plus_max",
        "psi_plus_peak_to_date_max",
        "E_el",
        "E_d",
    ]
    df[selected_cols].to_csv(out_dir / "soft_hist0_fem_state_timing_selected_metrics.csv", index=False)
    print(f"saved {summary_path}")
    print(f"saved {out_dir / 'soft_hist0_fem_state_timing_selected_metrics.csv'}")
    print(f"saved {out_dir / 'figures' / 'soft_hist0_state0_fem_vs_pidl_initial_damage.png'}")
    print(f"saved {out_dir / 'figures' / 'soft_hist0_fem_state_timing_scalars.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
