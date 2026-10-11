#!/usr/bin/env python3
"""Next-stage FEM M2S feasibility package.

This runner builds two controlled FYR-facing checks:

1. Multi-trajectory leave-one-trajectory-out prediction from FEM truth
   reductions, excluding cycle index from the inputs.
2. Sparse/noisy observation degradation on the full-field strict soft-hist0
   FEM handoffs.

The package is deliberately framed as a feasibility benchmark.  It does not
claim field deployment, and it does not claim state-driver superiority unless
the holdout metrics support it.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from run_m2s_synthetic_validation import (
    feature_row,
    feature_sets,
    finite_design,
    load_fem_handoff,
    metrics,
    write_csv,
)


DEFAULT_FIELD_ROOT = (
    Path(__file__).resolve().parents[1]
    / "_analysis_fem_mechanism_20260528"
    / "request21_fem_nstep"
    / "source_handoff"
)
DEFAULT_LEGACY_SCALAR_ROOT = Path.home() / "Downloads" / "_pidl_handoff_v2" / "post_process"
DEFAULT_OUT_DIR = Path(__file__).resolve().parents[1] / "_analysis_m2s_next_stage_20260531"

RIDGE_GRID = (0.01, 0.1, 1.0, 10.0, 100.0, 1000.0)
METADATA_COLUMNS = {
    "trajectory_id",
    "source_family",
    "source_path",
    "cycle",
    "nf",
    "umax",
    "nstep",
    "row_kind",
}
TARGET_COLUMNS = {"remaining_life", "crack_extension", "alpha_bar_severity"}


@dataclass
class FieldTrajectory:
    trajectory_id: str
    source_path: Path
    nf: int
    umax: float
    nstep: float
    cycles: np.ndarray
    centroids: np.ndarray
    damage: np.ndarray
    rows: list[dict[str, float | str]]


def stable_seed(*parts: object) -> int:
    h = hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def infer_nstep(path: Path) -> float:
    match = re.search(r"nstep(\d+)", str(path))
    return float(match.group(1)) if match else float("nan")


def discover_field_handoffs(root: Path) -> list[Path]:
    return sorted(root.glob("*/reverseBC*_element_fields_c1_c*.mat"))


def load_field_trajectory(path: Path, *, l0: float, crack_strip_y: float, boundary_x: float) -> FieldTrajectory:
    fem = load_fem_handoff(path)
    cycles = fem["cycles"].astype(int)
    nf = int(cycles.max())
    nstep = infer_nstep(path)
    trajectory_id = f"strict_u12_nstep{int(nstep):02d}" if math.isfinite(nstep) else path.stem
    rows: list[dict[str, float | str]] = []
    for k, cycle in enumerate(cycles):
        if cycle > nf:
            continue
        row = feature_row(
            int(cycle),
            nf,
            fem["centroids"],
            fem["areas"],
            fem["damage"][k],
            fem["alpha_bar"][k],
            fem["fatigue_f"][k],
            fem["psi_raw"][k],
            l0=l0,
            crack_strip_y=crack_strip_y,
            boundary_x=boundary_x,
        )
        row.update(
            {
                "trajectory_id": trajectory_id,
                "source_family": "strict_soft_hist0_cadence_field",
                "source_path": str(path),
                "nf": float(nf),
                "umax": 0.12,
                "nstep": nstep,
                "row_kind": "field_reduction",
                "crack_extension": float(row["crack_tip_x_d09"]),
                "alpha_bar_severity": float(row.get("alpha_bar_mean", np.nan)),
            }
        )
        rows.append(row)
    return FieldTrajectory(
        trajectory_id=trajectory_id,
        source_path=path,
        nf=nf,
        umax=0.12,
        nstep=nstep,
        cycles=cycles,
        centroids=fem["centroids"],
        damage=fem["damage"],
        rows=rows,
    )


def scalar_row(source_path: Path, df: pd.DataFrame, idx: int, umax: float, nf: int) -> dict[str, float | str]:
    r = df.iloc[idx]
    cycle = int(r["N"])
    crack_extension = max(0.0, float(r.get("delta_a", 0.0)))
    dmax = float(r.get("d_max", np.nan))
    p99_proxy = dmax
    damage_area_01 = crack_extension * min(max(dmax, 0.0), 1.0)
    damage_area_05 = crack_extension if dmax >= 0.5 else 0.0
    damage_area_09 = crack_extension if dmax >= 0.9 else 0.0
    f_mean = float(r.get("f_mean", np.nan))
    f_min = float(r.get("f_min", np.nan))
    psi_peak = float(r.get("psi_peak", np.nan))
    psi_tip = float(r.get("psi_tip", np.nan))
    psi_nominal = float(r.get("psi_nominal", np.nan))
    row: dict[str, float | str] = {
        "trajectory_id": f"legacy_umax_{int(round(umax * 100)):02d}",
        "source_family": "legacy_umax_scalar_reduction",
        "source_path": str(source_path),
        "cycle": float(cycle),
        "nf": float(nf),
        "umax": umax,
        "nstep": float("nan"),
        "row_kind": "scalar_timeseries",
        "remaining_life": float(nf - cycle),
        "crack_extension": crack_extension,
        "alpha_bar_severity": float(r.get("alpha_bar_mean", np.nan)),
        "crack_tip_x_d09": crack_extension,
        "damage_area_gt_0p1": damage_area_01,
        "damage_area_gt_0p5": damage_area_05,
        "damage_area_gt_0p9": damage_area_09,
        "damage_right_band_mean": damage_area_09,
        "damage_crack_strip_mean": damage_area_01,
        "damage_tip_2l0_mean": min(max(dmax, 0.0), 1.0),
        "damage_max": dmax,
        "damage_p99": p99_proxy,
        "damage_global_max": dmax,
        "damage_kt_proxy": float(r.get("Kt", np.nan)),
        "damage_da_dN": float(r.get("da_dN", np.nan)),
        "alpha_bar_max": float(r.get("alpha_max", np.nan)),
        "alpha_bar_mean": float(r.get("alpha_bar_mean", np.nan)),
        "fatigue_f_min": f_min,
        "fatigue_f_mean": f_mean,
        "psi_raw_peak": psi_peak,
        "psi_raw_tip": psi_tip,
        "psi_raw_nominal": psi_nominal,
        "psi_active_peak_est": f_min * psi_peak if np.isfinite(f_min) else np.nan,
        "psi_active_tip_est": f_mean * psi_tip if np.isfinite(f_mean) else np.nan,
        "psi_active_nominal_est": f_mean * psi_nominal if np.isfinite(f_mean) else np.nan,
        "energy_elastic": float(r.get("E_el", np.nan)),
        "energy_damage_cum": float(r.get("E_d_cum", np.nan)),
        "energy_damage_increment": float(r.get("dE_d", np.nan)),
    }
    return row


def load_legacy_scalar_rows(root: Path) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for path in sorted(root.glob("SENT_PIDL_*_timeseries.csv")):
        match = re.search(r"SENT_PIDL_(\d+)_timeseries", path.name)
        if not match:
            continue
        umax = int(match.group(1)) / 100.0
        df = pd.read_csv(path)
        nf = int(df["N"].max())
        for i in range(len(df)):
            rows.append(scalar_row(path, df, i, umax, nf))
    return rows


def numeric_feature_names(df: pd.DataFrame, target: str) -> dict[str, list[str]]:
    excluded = set(METADATA_COLUMNS) | TARGET_COLUMNS | {"pred"}
    all_names = [
        c
        for c in df.columns
        if c not in excluded and pd.api.types.is_numeric_dtype(df[c])
        and np.isfinite(df[c].to_numpy(dtype=float)).any()
    ]
    groups = feature_sets(all_names)
    if target == "crack_extension":
        leak = {"crack_tip_x_d09", "crack_extension", "damage_crack_length"}
        groups = {k: [c for c in v if c not in leak] for k, v in groups.items()}
    if target == "alpha_bar_severity":
        groups = {k: [c for c in v if not c.startswith("alpha_bar")] for k, v in groups.items()}
    return {k: v for k, v in groups.items() if v}


def fit_ridge_predict(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    ridge_alpha: float,
) -> np.ndarray:
    mean = x_train.mean(axis=0)
    scale = x_train.std(axis=0)
    scale[scale < 1e-12] = 1.0
    z_train = (x_train - mean) / scale
    z_test = (x_test - mean) / scale
    design = np.column_stack([np.ones(z_train.shape[0]), z_train])
    penalty = np.eye(design.shape[1]) * ridge_alpha
    penalty[0, 0] = 0.0
    beta = np.linalg.solve(design.T @ design + penalty, design.T @ y_train)
    return np.column_stack([np.ones(z_test.shape[0]), z_test]) @ beta


def select_alpha_group_cv(
    x: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    candidate_alphas: Iterable[float] = RIDGE_GRID,
) -> float:
    unique = np.unique(groups)
    if unique.size < 2:
        return 1.0
    best_alpha = None
    best_key = None
    for alpha in candidate_alphas:
        preds = np.zeros_like(y, dtype=float)
        for heldout in unique:
            train = groups != heldout
            test = groups == heldout
            preds[test] = fit_ridge_predict(x[train], y[train], x[test], alpha)
        m = metrics(y, preds)
        key = (m["mae_cycles"], m["rmse_cycles"])
        if best_key is None or key < best_key:
            best_key = key
            best_alpha = alpha
    return float(best_alpha)


def loto_predict(
    df: pd.DataFrame,
    *,
    suite: str,
    target: str,
    feature_set_name: str,
    feature_names: list[str],
) -> tuple[list[dict[str, float | str]], pd.DataFrame]:
    rows = df.dropna(subset=[target]).copy()
    y_all = rows[target].to_numpy(dtype=float)
    groups_all = rows["trajectory_id"].to_numpy(str)
    x_all = finite_design(rows.to_dict("records"), feature_names)
    pred_all = np.zeros_like(y_all, dtype=float)
    summary_rows: list[dict[str, float | str]] = []
    for heldout in np.unique(groups_all):
        train = groups_all != heldout
        test = groups_all == heldout
        alpha = select_alpha_group_cv(x_all[train], y_all[train], groups_all[train])
        pred_all[test] = fit_ridge_predict(x_all[train], y_all[train], x_all[test], alpha)
        m = metrics(y_all[test], pred_all[test])
        summary_rows.append(
            {
                "suite": suite,
                "target": target,
                "feature_set": feature_set_name,
                "heldout_trajectory": heldout,
                "n_features": float(len(feature_names)),
                "ridge_alpha": alpha,
                "n_train": float(train.sum()),
                "n_test": float(test.sum()),
                "mae": m["mae_cycles"],
                "rmse": m["rmse_cycles"],
                "r2": m["r2"],
                "max_abs_error": m["max_abs_error_cycles"],
            }
        )
    m_all = metrics(y_all, pred_all)
    summary_rows.append(
        {
            "suite": suite,
            "target": target,
            "feature_set": feature_set_name,
            "heldout_trajectory": "ALL",
            "n_features": float(len(feature_names)),
            "ridge_alpha": float("nan"),
            "n_train": float("nan"),
            "n_test": float(len(y_all)),
            "mae": m_all["mae_cycles"],
            "rmse": m_all["rmse_cycles"],
            "r2": m_all["r2"],
            "max_abs_error": m_all["max_abs_error_cycles"],
        }
    )
    pred_cols = [
        c
        for c in ["trajectory_id", "source_family", "cycle", "nf", "umax", "nstep", target]
        if c in rows.columns
    ]
    pred_df = rows[pred_cols].copy()
    pred_df["suite"] = suite
    pred_df["target"] = target
    pred_df["feature_set"] = feature_set_name
    pred_df["prediction"] = pred_all
    pred_df["error"] = pred_all - y_all
    return summary_rows, pred_df


def run_holdout_study(all_rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    suites = {
        "combined_all": all_rows,
        "legacy_umax_scalar": all_rows[all_rows["source_family"] == "legacy_umax_scalar_reduction"],
        "strict_soft_hist0_cadence_field": all_rows[
            all_rows["source_family"] == "strict_soft_hist0_cadence_field"
        ],
    }
    targets = ["remaining_life", "crack_extension", "alpha_bar_severity"]
    summaries: list[dict[str, float | str]] = []
    predictions: list[pd.DataFrame] = []
    for suite, df in suites.items():
        if df["trajectory_id"].nunique() < 2:
            continue
        for target in targets:
            groups = numeric_feature_names(df, target)
            for feature_set_name, names in groups.items():
                out_rows, pred_df = loto_predict(
                    df,
                    suite=suite,
                    target=target,
                    feature_set_name=feature_set_name,
                    feature_names=names,
                )
                summaries.extend(out_rows)
                predictions.append(pred_df)
    return pd.DataFrame(summaries), pd.concat(predictions, ignore_index=True)


def nearest_indices(centroids: np.ndarray, points: np.ndarray) -> np.ndarray:
    idx = []
    for p in points:
        dist2 = np.sum((centroids - p[None, :]) ** 2, axis=1)
        idx.append(int(np.argmin(dist2)))
    return np.array(idx, dtype=int)


def sensor_points(count: int, mode: str) -> np.ndarray:
    if mode == "near_crack":
        y_levels = np.array([-0.035, -0.0175, 0.0, 0.0175, 0.035])
    elif mode == "off_path":
        y_levels = np.array([-0.22, -0.14, 0.14, 0.22])
    else:
        y_levels = np.array([-0.18, -0.08, 0.0, 0.08, 0.18])
    nx = max(1, int(math.ceil(count / len(y_levels))))
    xs = np.linspace(0.0, 0.5, nx)
    pts = np.array([(x, y) for x in xs for y in y_levels], dtype=float)
    return pts[:count]


def sensor_feature_rows(
    trajectories: list[FieldTrajectory],
    *,
    sensor_count: int,
    mode: str,
    noise_std: float,
    missing_rate: float,
) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for traj in trajectories:
        pts = sensor_points(sensor_count, mode)
        idx = nearest_indices(traj.centroids, pts)
        rng = np.random.default_rng(stable_seed(traj.trajectory_id, sensor_count, mode, noise_std, missing_rate))
        for k, base in enumerate(traj.rows):
            values = traj.damage[k, idx].astype(float).copy()
            if noise_std > 0.0:
                values = np.clip(values + rng.normal(0.0, noise_std, size=values.shape), 0.0, 1.0)
            if missing_rate > 0.0:
                missing = rng.random(values.shape) < missing_rate
                values[missing] = np.nan
            row: dict[str, float | str] = {
                "trajectory_id": traj.trajectory_id,
                "remaining_life": float(base["remaining_life"]),
            }
            for i, value in enumerate(values):
                row[f"sensor_damage_{i:03d}"] = float(value) if np.isfinite(value) else np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def aggregate_observation_rows(
    rows: list[dict[str, float | str]],
    *,
    suite: str,
    tier: str,
    sensor_mode: str,
    sensor_count: int,
    noise_std: float,
    missing_rate: float,
) -> list[dict[str, float | str]]:
    out = []
    df = pd.DataFrame(rows)
    for _, r in df.iterrows():
        item = r.to_dict()
        item.update(
            {
                "suite": suite,
                "observation_tier": tier,
                "sensor_mode": sensor_mode,
                "n_sensors": float(sensor_count),
                "noise_std": float(noise_std),
                "missing_rate": float(missing_rate),
            }
        )
        out.append(item)
    return out


def run_observation_config(
    df: pd.DataFrame,
    *,
    tier: str,
    sensor_mode: str,
    sensor_count: int,
    noise_std: float,
    missing_rate: float,
) -> tuple[list[dict[str, float | str]], pd.DataFrame]:
    feature_names = [
        c for c in df.columns if c not in {"trajectory_id", "remaining_life"} and pd.api.types.is_numeric_dtype(df[c])
    ]
    rows, pred = loto_predict(
        df,
        suite="strict_field_sparse_noisy",
        target="remaining_life",
        feature_set_name=tier,
        feature_names=feature_names,
    )
    rows = aggregate_observation_rows(
        rows,
        suite="strict_field_sparse_noisy",
        tier=tier,
        sensor_mode=sensor_mode,
        sensor_count=sensor_count,
        noise_std=noise_std,
        missing_rate=missing_rate,
    )
    pred["observation_tier"] = tier
    pred["sensor_mode"] = sensor_mode
    pred["n_sensors"] = float(sensor_count)
    pred["noise_std"] = float(noise_std)
    pred["missing_rate"] = float(missing_rate)
    return rows, pred


def run_sparse_noisy_study(trajectories: list[FieldTrajectory]) -> tuple[pd.DataFrame, pd.DataFrame]:
    field_df = pd.DataFrame([row for traj in trajectories for row in traj.rows])
    summary_rows: list[dict[str, float | str]] = []
    pred_frames: list[pd.DataFrame] = []

    groups = numeric_feature_names(field_df, "remaining_life")
    for tier, feature_set_name in [
        ("image_crack_geometry_only", "figure_damage"),
        ("full_damage_reductions", "damage_field"),
    ]:
        base = field_df[["trajectory_id", "remaining_life"] + groups[feature_set_name]].copy()
        rows, pred = run_observation_config(
            base,
            tier=tier,
            sensor_mode="none",
            sensor_count=0,
            noise_std=0.0,
            missing_rate=0.0,
        )
        summary_rows.extend(rows)
        pred_frames.append(pred)

    for sensor_mode in ["near_crack", "mixed", "off_path"]:
        for sensor_count in [4, 8, 16, 32, 64]:
            for noise_std in [0.0, 0.02, 0.05, 0.10]:
                for missing_rate in ([0.0, 0.25] if noise_std in (0.0, 0.05) else [0.0]):
                    df = sensor_feature_rows(
                        trajectories,
                        sensor_count=sensor_count,
                        mode=sensor_mode,
                        noise_std=noise_std,
                        missing_rate=missing_rate,
                    )
                    tier = "sparse_damage_sensors" if noise_std == 0.0 and missing_rate == 0.0 else "sparse_noisy_sensors"
                    rows, pred = run_observation_config(
                        df,
                        tier=tier,
                        sensor_mode=sensor_mode,
                        sensor_count=sensor_count,
                        noise_std=noise_std,
                        missing_rate=missing_rate,
                    )
                    summary_rows.extend(rows)
                    pred_frames.append(pred)
    return pd.DataFrame(summary_rows), pd.concat(pred_frames, ignore_index=True)


def plot_holdout_predictions(pred: pd.DataFrame, summary: pd.DataFrame, out_dir: Path) -> None:
    df = pred[
        (pred["suite"] == "combined_all")
        & (pred["target"] == "remaining_life")
        & (pred["feature_set"].isin(["figure_damage", "damage_field", "state_driver_raw_active"]))
    ].copy()
    if df.empty:
        return
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 3.8), sharex=True, sharey=True)
    true_max = float(df["remaining_life"].max())
    pred_min = float(df["prediction"].min())
    pred_max = float(df["prediction"].max())
    for ax, feature_set_name in zip(axes, ["figure_damage", "damage_field", "state_driver_raw_active"]):
        sub = df[df["feature_set"] == feature_set_name]
        ax.scatter(sub["remaining_life"], sub["prediction"], s=9, alpha=0.42, linewidths=0)
        ax.plot([0.0, true_max], [0.0, true_max], color="0.25", lw=1.0)
        agg = summary[
            (summary["suite"] == "combined_all")
            & (summary["target"] == "remaining_life")
            & (summary["feature_set"] == feature_set_name)
            & (summary["heldout_trajectory"] == "ALL")
        ]
        mae = float(agg["mae"].iloc[0]) if not agg.empty else float("nan")
        ax.set_title(f"{feature_set_name}\nMAE={mae:.2f} cycles", fontsize=9)
        ax.grid(True, color="0.9", linewidth=0.6)
        ax.set_xlim(-0.02 * true_max, true_max * 1.04)
        ax.set_ylim(min(-5.0, pred_min * 1.05), max(true_max * 1.04, pred_max * 1.04))
    axes[0].set_ylabel("Predicted RUL (cycles)")
    for ax in axes:
        ax.set_xlabel("True RUL (cycles)")
    fig.suptitle("Leave-one-trajectory-out RUL prediction", fontsize=11)
    fig.tight_layout()
    fig.savefig(out_dir / "m2s_holdout_rul_true_vs_pred.png", dpi=220)
    fig.savefig(out_dir / "m2s_holdout_rul_true_vs_pred.pdf")
    plt.close(fig)


def plot_observation_quality(summary: pd.DataFrame, out_dir: Path) -> None:
    agg = summary[summary["heldout_trajectory"] == "ALL"].copy()
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    colors = {0.0: "#0072B2", 0.02: "#009E73", 0.05: "#D55E00", 0.10: "#CC79A7"}
    sub = agg[
        (agg["sensor_mode"] == "mixed")
        & (agg["missing_rate"] == 0.0)
        & (agg["observation_tier"].isin(["sparse_damage_sensors", "sparse_noisy_sensors"]))
    ]
    for noise_std, g in sub.groupby("noise_std"):
        g = g.sort_values("n_sensors")
        ax.plot(
            g["n_sensors"],
            g["mae"],
            marker="o",
            lw=1.4,
            color=colors.get(float(noise_std), None),
            label=f"mixed sensors, noise={float(noise_std):.2f}",
        )
    for tier, style in [
        ("image_crack_geometry_only", ("0.35", "--")),
        ("full_damage_reductions", ("0.15", "-.")),
    ]:
        base = agg[agg["observation_tier"] == tier]
        if not base.empty:
            ax.axhline(float(base["mae"].iloc[0]), color=style[0], ls=style[1], lw=1.1, label=tier)
    ax.set_xscale("log", base=2)
    ax.set_xticks([4, 8, 16, 32, 64])
    ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
    ax.set_xlabel("Number of virtual damage sensors")
    ax.set_ylabel("RUL MAE (cycles)")
    ax.set_ylim(bottom=0.0)
    ax.set_title("Observation-quality degradation on strict full-field FEM subset", fontsize=10)
    ax.grid(True, which="both", color="0.9", linewidth=0.6)
    ax.legend(fontsize=7.5, frameon=False)
    fig.tight_layout()
    fig.savefig(out_dir / "m2s_observation_quality_mae.png", dpi=220)
    fig.savefig(out_dir / "m2s_observation_quality_mae.pdf")
    plt.close(fig)


def write_report(
    path: Path,
    *,
    rows: pd.DataFrame,
    holdout_summary: pd.DataFrame,
    obs_summary: pd.DataFrame,
    field_paths: list[Path],
    scalar_root: Path,
) -> None:
    def agg_line(suite: str, feature_set_name: str) -> str:
        r = holdout_summary[
            (holdout_summary["suite"] == suite)
            & (holdout_summary["target"] == "remaining_life")
            & (holdout_summary["feature_set"] == feature_set_name)
            & (holdout_summary["heldout_trajectory"] == "ALL")
        ]
        if r.empty:
            return "n/a"
        row = r.iloc[0]
        return f"MAE {row['mae']:.2f}, RMSE {row['rmse']:.2f}, R2 {row['r2']:.3f}, max {row['max_abs_error']:.2f}"

    obs_best = obs_summary[
        (obs_summary["heldout_trajectory"] == "ALL")
        & (obs_summary["sensor_mode"] == "mixed")
        & (obs_summary["missing_rate"] == 0.0)
    ].copy()
    obs_best = obs_best.sort_values(["noise_std", "n_sensors"])
    lines = [
        "# M2S Next-Stage Feasibility Package",
        "",
        "Date: 2026-05-31",
        "",
        "## Method",
        "",
        "This package tests measurement-to-state prediction using leave-one-trajectory-out splits. "
        "Cycle index is excluded from every input feature. Ridge regression is fitted on complete "
        "training trajectories and evaluated on the held-out trajectory.",
        "",
        "## Data",
        "",
        f"- Strict full-field soft-hist0 cadence handoffs: {len(field_paths)} files.",
        f"- Legacy five-Umax scalar FEM reductions: `{scalar_root}`.",
        f"- Total rows used for holdout feasibility: {len(rows)} across {rows['trajectory_id'].nunique()} trajectories.",
        "",
        "The strict field subset keeps the soft-hist0/reverseBC reference style. "
        "The five-Umax scalar subset is older but provides the local multi-load feasibility stress test.",
        "",
        "## Feature Sets",
        "",
        "- `figure_damage`: crack geometry and compact visible-damage reductions.",
        "- `damage_field`: richer damage-field reductions where available.",
        "- `state_driver_raw_active`: damage plus fatigue history, fatigue degradation, raw driver, and active/degraded driver proxies.",
        "",
        "## Multi-Trajectory Holdout Results",
        "",
        "| suite | figure_damage | damage_field | state_driver_raw_active |",
        "|---|---|---|---|",
    ]
    for suite in ["combined_all", "legacy_umax_scalar", "strict_soft_hist0_cadence_field"]:
        lines.append(
            f"| `{suite}` | {agg_line(suite, 'figure_damage')} | "
            f"{agg_line(suite, 'damage_field')} | {agg_line(suite, 'state_driver_raw_active')} |"
        )
    lines.extend(
        [
            "",
            "## Sparse/Noisy Observation Results",
            "",
            "The sparse/noisy test uses the strict full-field FEM subset because those handoffs contain "
            "cycle-wise element damage fields. Virtual damage sensors are placed near the crack path, "
            "off the crack path, or in a mixed layout; Gaussian noise and missing observations are added "
            "before the same trajectory holdout protocol.",
            "",
            "| observation | sensors | noise | missing | MAE | RMSE | R2 |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for _, r in obs_best[
        obs_best["observation_tier"].isin(["image_crack_geometry_only", "full_damage_reductions"])
        | ((obs_best["sensor_mode"] == "mixed") & (obs_best["n_sensors"].isin([4, 16, 64])))
    ].iterrows():
        lines.append(
            f"| `{r['observation_tier']}` | {int(r['n_sensors'])} | {float(r['noise_std']):.2f} | "
            f"{float(r['missing_rate']):.2f} | {float(r['mae']):.2f} | {float(r['rmse']):.2f} | {float(r['r2']):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Key Interpretation",
            "",
            "This is a next validation rung, not final deployment evidence. The main safe claim is that "
            "multi-trajectory FEM holdout splits expose whether M2S generalises beyond one monotonic "
            "damage path, and sparse/noisy tests quantify how much observation quality is needed for "
            "useful RUL inference.",
            "",
            "Do not claim hidden state-driver fields are superior unless the holdout table shows a clear "
            "improvement for the relevant suite. In this package, the correct reading is empirical and "
            "suite-specific.",
            "",
            "## Limitations",
            "",
            "- The five-Umax trajectories are scalar reductions, not the newer strict full-field soft-hist0 family.",
            "- The strict full-field subset varies cadence at fixed `Umax=0.12`; it is useful for sparse/noisy tests but not a broad material/load generalisation proof.",
            "- Sparse sensors are virtual samples from FEM fields, not real pavement measurements.",
            "",
            "## Recommended Next Step",
            "",
            "Run the same exporter for several strict soft-hist0/reverseBC trajectories with different `Umax`, "
            "`alpha_T`, and precrack severity, then repeat this exact leave-one-trajectory-out package on the "
            "strict full-field family.",
            "",
            "## Artifacts",
            "",
            "- `m2s_multitrajectory_holdout_summary.csv`",
            "- `m2s_sparse_noisy_observation_summary.csv`",
            "- `m2s_holdout_rul_true_vs_pred.png/.pdf`",
            "- `m2s_observation_quality_mae.png/.pdf`",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--field-root", type=Path, default=DEFAULT_FIELD_ROOT)
    parser.add_argument("--legacy-scalar-root", type=Path, default=DEFAULT_LEGACY_SCALAR_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--l0", type=float, default=0.01)
    parser.add_argument("--crack-strip-y", type=float, default=0.05)
    parser.add_argument("--boundary-x", type=float, default=0.45)
    args = parser.parse_args()

    field_paths = discover_field_handoffs(args.field_root)
    if len(field_paths) < 2:
        raise RuntimeError(f"Need at least two field handoffs in {args.field_root}")
    field_trajectories = [
        load_field_trajectory(
            path,
            l0=args.l0,
            crack_strip_y=args.crack_strip_y,
            boundary_x=args.boundary_x,
        )
        for path in field_paths
    ]
    rows = pd.DataFrame([row for traj in field_trajectories for row in traj.rows] + load_legacy_scalar_rows(args.legacy_scalar_root))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows.to_csv(args.out_dir / "m2s_next_stage_cycle_features.csv", index=False)

    holdout_summary, holdout_pred = run_holdout_study(rows)
    obs_summary, obs_pred = run_sparse_noisy_study(field_trajectories)

    holdout_summary.to_csv(args.out_dir / "m2s_multitrajectory_holdout_summary.csv", index=False)
    holdout_pred.to_csv(args.out_dir / "m2s_multitrajectory_holdout_predictions.csv", index=False)
    obs_summary.to_csv(args.out_dir / "m2s_sparse_noisy_observation_summary.csv", index=False)
    obs_pred.to_csv(args.out_dir / "m2s_sparse_noisy_observation_predictions.csv", index=False)

    plot_holdout_predictions(holdout_pred, holdout_summary, args.out_dir)
    plot_observation_quality(obs_summary, args.out_dir)
    write_report(
        args.out_dir / "m2s_next_stage_feasibility_report.md",
        rows=rows,
        holdout_summary=holdout_summary,
        obs_summary=obs_summary,
        field_paths=field_paths,
        scalar_root=args.legacy_scalar_root,
    )

    print(f"Wrote next-stage M2S package to {args.out_dir}")
    for suite in ["combined_all", "legacy_umax_scalar", "strict_soft_hist0_cadence_field"]:
        sub = holdout_summary[
            (holdout_summary["suite"] == suite)
            & (holdout_summary["target"] == "remaining_life")
            & (holdout_summary["heldout_trajectory"] == "ALL")
        ]
        if sub.empty:
            continue
        print(f"\n{suite}")
        for _, row in sub.iterrows():
            print(
                f"  {row['feature_set']}: MAE={row['mae']:.3g}, "
                f"RMSE={row['rmse']:.3g}, R2={row['r2']:.3g}, max={row['max_abs_error']:.3g}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
