#!/usr/bin/env python3
"""Synthetic M2S framework validation on a FEM truth trajectory.

This script treats a cycle-resolved FEM handoff as the hidden truth trajectory
and asks how much remaining-life information is visible from increasingly rich
observation sets:

1. figure_damage: crack/figure-like reductions derived only from damage.
2. damage_field: richer damage-field reductions, still no hidden drivers.
3. state_driver: damage plus alpha_bar, fatigue factor, raw psi, and active
   degraded psi = g(d) * raw psi.

It is an observability benchmark for the closed-loop M2S framework, not a field
deployment claim.  It intentionally excludes cycle index as a feature so the
score reflects state information rather than a trivial clock.
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import h5py
import numpy as np


def orient_points(arr: np.ndarray, n_cols: int) -> np.ndarray:
    arr = np.asarray(arr)
    if arr.ndim == 2 and arr.shape[0] == n_cols and arr.shape[1] != n_cols:
        return arr.T
    return arr


def orient_conn(arr: np.ndarray) -> np.ndarray:
    conn = np.asarray(arr, dtype=int)
    if conn.ndim == 2 and conn.shape[0] in (3, 4) and conn.shape[1] > conn.shape[0]:
        conn = conn.T
    if conn.min() == 1:
        conn = conn - 1
    return conn


def polygon_areas(nodes: np.ndarray, conn: np.ndarray) -> np.ndarray:
    pts = nodes[conn]
    x = pts[:, :, 0]
    y = pts[:, :, 1]
    return 0.5 * np.abs(
        np.sum(x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1), axis=1)
    )


def cycles_by_elem(arr: np.ndarray, n_cycles: int, name: str) -> np.ndarray:
    arr = np.asarray(arr, dtype=float)
    if arr.ndim != 2:
        raise ValueError(f"{name} must be a 2D cycle/element array, got {arr.shape}")
    if arr.shape[0] == n_cycles:
        return arr
    if arr.shape[1] == n_cycles:
        return arr.T
    raise ValueError(f"{name} has shape {arr.shape}, cannot align with {n_cycles} cycles")


def load_fem_handoff(path: Path) -> dict[str, np.ndarray]:
    aliases = {
        "damage": ("d_elem", "alpha_elem"),
        "psi_raw": ("psi_elem", "psi_plus_elem"),
        "alpha_bar": ("alpha_bar_elem",),
        "fatigue_f": ("f_alpha_elem", "f_fatigue_elem"),
    }
    with h5py.File(path, "r") as h5:
        cycles = np.asarray(h5["cycles"], dtype=int).reshape(-1)
        centroids = orient_points(np.asarray(h5["element_centroids"], dtype=float), 2)
        nodes = orient_points(np.asarray(h5["node_coords"], dtype=float), 2)
        conn = orient_conn(np.asarray(h5["connectivity"], dtype=int))
        if "area_per_elem" in h5:
            areas = np.asarray(h5["area_per_elem"], dtype=float).reshape(-1)
        else:
            areas = polygon_areas(nodes, conn)

        fields: dict[str, np.ndarray] = {}
        for out_name, candidates in aliases.items():
            found = next((candidate for candidate in candidates if candidate in h5), None)
            if found is None:
                raise KeyError(f"Missing FEM field {out_name}; tried {candidates}")
            fields[out_name] = cycles_by_elem(np.asarray(h5[found]), len(cycles), found)

    # Older handoffs sometimes store unit-square coordinates.  The PIDL/FEM
    # crack probes in this project use the centred domain [-0.5, 0.5].
    if np.nanmin(centroids[:, 0]) >= -1e-9 and np.nanmax(centroids[:, 0]) > 0.9:
        centroids = centroids.copy()
        centroids[:, 0] -= 0.5
        centroids[:, 1] -= 0.5

    n_elem = centroids.shape[0]
    if areas.shape[0] != n_elem:
        raise ValueError(f"area count {areas.shape[0]} does not match centroids {n_elem}")
    for name, arr in fields.items():
        if arr.shape[1] != n_elem:
            raise ValueError(f"{name} element count {arr.shape[1]} does not match centroids {n_elem}")

    return {"cycles": cycles, "centroids": centroids, "areas": areas, **fields}


def weighted_mean(values: np.ndarray, weights: np.ndarray, mask: np.ndarray | None = None) -> float:
    if mask is not None:
        values = values[mask]
        weights = weights[mask]
    if values.size == 0 or float(np.sum(weights)) <= 0.0:
        return float("nan")
    return float(np.sum(values * weights) / np.sum(weights))


def top_fraction_mean(values: np.ndarray, weights: np.ndarray, fraction: float = 0.01) -> float:
    if values.size == 0:
        return float("nan")
    n = max(1, int(math.ceil(values.size * fraction)))
    idx = np.argpartition(values, -n)[-n:]
    return weighted_mean(values[idx], weights[idx])


def stats(prefix: str, values: np.ndarray, areas: np.ndarray, masks: dict[str, np.ndarray]) -> dict[str, float]:
    out = {
        f"{prefix}_mean": weighted_mean(values, areas),
        f"{prefix}_max": float(np.max(values)),
        f"{prefix}_p95": float(np.quantile(values, 0.95)),
        f"{prefix}_p99": float(np.quantile(values, 0.99)),
        f"{prefix}_p999": float(np.quantile(values, 0.999)),
        f"{prefix}_top1_mean": top_fraction_mean(values, areas),
    }
    for mask_name, mask in masks.items():
        out[f"{prefix}_{mask_name}_mean"] = weighted_mean(values, areas, mask)
        if bool(np.any(mask)):
            out[f"{prefix}_{mask_name}_max"] = float(np.max(values[mask]))
        else:
            out[f"{prefix}_{mask_name}_max"] = float("nan")
    return out


def crack_tip_x(damage: np.ndarray, x: np.ndarray, y: np.ndarray, *, threshold: float, strip_y: float) -> float:
    mask = (damage >= threshold) & (x >= 0.0) & (np.abs(y) <= strip_y)
    if not bool(np.any(mask)):
        return 0.0
    return float(np.max(x[mask]))


def area_fraction(damage: np.ndarray, areas: np.ndarray, threshold: float) -> float:
    total = float(np.sum(areas))
    if total <= 0.0:
        return float("nan")
    return float(np.sum(areas[damage >= threshold]) / total)


def feature_row(
    cycle: int,
    nf: int,
    centroids: np.ndarray,
    areas: np.ndarray,
    damage: np.ndarray,
    alpha_bar: np.ndarray,
    fatigue_f: np.ndarray,
    psi_raw: np.ndarray,
    *,
    l0: float,
    crack_strip_y: float,
    boundary_x: float,
) -> dict[str, float]:
    x = centroids[:, 0]
    y = centroids[:, 1]
    tip_x = crack_tip_x(damage, x, y, threshold=0.9, strip_y=crack_strip_y)
    dist_tip = np.sqrt((x - tip_x) ** 2 + y**2)
    masks = {
        "crack_strip": (x >= 0.0) & (np.abs(y) <= crack_strip_y),
        "right_band": x >= boundary_x,
        "tip_l0": dist_tip <= l0,
        "tip_2l0": dist_tip <= 2.0 * l0,
        "tip_4l0": dist_tip <= 4.0 * l0,
    }
    psi_active = ((1.0 - damage) ** 2 + 1e-6) * psi_raw

    row: dict[str, float] = {
        "cycle": float(cycle),
        "remaining_life": float(nf - cycle),
        "crack_tip_x_d09": tip_x,
        "damage_area_gt_0p1": area_fraction(damage, areas, 0.1),
        "damage_area_gt_0p5": area_fraction(damage, areas, 0.5),
        "damage_area_gt_0p9": area_fraction(damage, areas, 0.9),
        "damage_right_band_mean": weighted_mean(damage, areas, masks["right_band"]),
        "damage_crack_strip_mean": weighted_mean(damage, areas, masks["crack_strip"]),
        "damage_tip_2l0_mean": weighted_mean(damage, areas, masks["tip_2l0"]),
        "damage_max": float(np.max(damage)),
        "damage_p99": float(np.quantile(damage, 0.99)),
    }

    row.update(stats("damage", damage, areas, masks))
    row.update(stats("alpha_bar", alpha_bar, areas, masks))
    row.update(stats("fatigue_f", fatigue_f, areas, masks))
    row.update(stats("psi_raw", psi_raw, areas, masks))
    row.update(stats("psi_active", psi_active, areas, masks))
    raw_tip = row["psi_raw_tip_2l0_mean"]
    row["psi_active_over_raw_tip_2l0"] = (
        row["psi_active_tip_2l0_mean"] / raw_tip
        if np.isfinite(raw_tip) and abs(raw_tip) > 1e-30 else float("nan")
    )
    return row


def finite_design(rows: list[dict[str, float]], names: list[str]) -> np.ndarray:
    x = np.array([[row.get(name, float("nan")) for name in names] for row in rows], dtype=float)
    col_mean = np.nanmean(x, axis=0)
    col_mean = np.where(np.isfinite(col_mean), col_mean, 0.0)
    inds = np.where(~np.isfinite(x))
    x[inds] = np.take(col_mean, inds[1])
    return x


def loocv_ridge_predict(x: np.ndarray, y: np.ndarray, ridge_alpha: float) -> np.ndarray:
    preds = np.zeros_like(y, dtype=float)
    for i in range(len(y)):
        train = np.arange(len(y)) != i
        x_train = x[train]
        y_train = y[train]
        mean = x_train.mean(axis=0)
        scale = x_train.std(axis=0)
        scale[scale < 1e-12] = 1.0
        z_train = (x_train - mean) / scale
        z_test = (x[i : i + 1] - mean) / scale
        design = np.column_stack([np.ones(z_train.shape[0]), z_train])
        penalty = np.eye(design.shape[1]) * ridge_alpha
        penalty[0, 0] = 0.0
        beta = np.linalg.solve(design.T @ design + penalty, design.T @ y_train)
        preds[i] = float((np.column_stack([np.ones(1), z_test]) @ beta)[0])
    return preds


def loocv_nearest_neighbor(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    preds = np.zeros_like(y, dtype=float)
    for i in range(len(y)):
        train = np.arange(len(y)) != i
        x_train = x[train]
        mean = x_train.mean(axis=0)
        scale = x_train.std(axis=0)
        scale[scale < 1e-12] = 1.0
        z_train = (x_train - mean) / scale
        z_test = (x[i] - mean) / scale
        j = int(np.argmin(np.sum((z_train - z_test) ** 2, axis=1)))
        preds[i] = y[train][j]
    return preds


def metrics(y: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    err = pred - y
    denom = float(np.sum((y - y.mean()) ** 2))
    return {
        "mae_cycles": float(np.mean(np.abs(err))),
        "rmse_cycles": float(np.sqrt(np.mean(err**2))),
        "max_abs_error_cycles": float(np.max(np.abs(err))),
        "r2": float(1.0 - np.sum(err**2) / denom) if denom > 0.0 else float("nan"),
    }


def parse_alpha_grid(single_alpha: float | None, alpha_grid: str) -> list[float]:
    if single_alpha is not None:
        return [float(single_alpha)]
    out = [float(item.strip()) for item in alpha_grid.split(",") if item.strip()]
    if not out:
        raise ValueError("ridge alpha grid is empty")
    return out


def feature_sets(all_names: list[str]) -> dict[str, list[str]]:
    figure = [
        "crack_tip_x_d09",
        "damage_area_gt_0p5",
        "damage_area_gt_0p9",
        "damage_right_band_mean",
        "damage_crack_strip_mean",
        "damage_tip_2l0_mean",
        "damage_max",
        "damage_p99",
    ]
    damage = [name for name in all_names if name.startswith("damage") or name == "crack_tip_x_d09"]
    state = [
        name for name in all_names
        if name == "crack_tip_x_d09"
        or name.startswith("damage")
        or name.startswith("alpha_bar")
        or name.startswith("fatigue_f")
        or name.startswith("psi_raw")
        or name.startswith("psi_active")
    ]
    return {
        "figure_damage": [name for name in figure if name in all_names],
        "damage_field": damage,
        "state_driver_raw_active": state,
    }


def write_csv(path: Path, rows: list[dict[str, float]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_markdown(
    path: Path,
    args: argparse.Namespace,
    cycles: np.ndarray,
    summaries: list[dict[str, float | str]],
    feature_counts: dict[str, int],
) -> None:
    best = min(summaries, key=lambda row: float(row["ridge_mae_cycles"]))
    lines = [
        "# M2S Synthetic Framework Validation",
        "",
        f"FEM handoff: `{args.fem_combined_mat}`",
        f"Truth failure cycle `N_f`: {args.nf}",
        f"Cycles used: {int(cycles.min())} to {int(cycles.max())} ({len(cycles)} snapshots)",
        "",
        "This is a controlled observability test for the measurement-to-state framework. "
        "The FEM trajectory is treated as truth, and the model predicts remaining life "
        "from state reductions without using cycle index as an input feature.",
        "",
        "## Feature Sets",
        "",
        "- `figure_damage`: figure-like crack/damage geometry only.",
        "- `damage_field`: richer reductions of the full damage field.",
        "- `state_driver_raw_active`: damage plus `alpha_bar`, fatigue factor, raw `psi`, "
        "and active degraded `g(d) * psi`.",
        "",
        "## Remaining-Life Prediction",
        "",
        "| feature set | n features | best alpha | ridge LOOCV MAE | ridge RMSE | ridge R2 | NN MAE | max abs error |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['feature_set']} | {feature_counts[str(row['feature_set'])]} | "
            f"{float(row['ridge_alpha']):.3g} | "
            f"{float(row['ridge_mae_cycles']):.3g} | {float(row['ridge_rmse_cycles']):.3g} | "
            f"{float(row['ridge_r2']):.3g} | {float(row['nn_mae_cycles']):.3g} | "
            f"{float(row['ridge_max_abs_error_cycles']):.3g} |"
        )
    lines.extend([
        "",
        "## Interpretation Guardrails",
        "",
        f"- Best ridge score in this single-trajectory benchmark: `{best['feature_set']}` "
        f"with MAE {float(best['ridge_mae_cycles']):.3g} cycles "
        f"at alpha {float(best['ridge_alpha']):.3g}.",
        "- A good score here supports the framework's M2S observability step on synthetic FEM data; "
        "it does not prove material identifiability or field deployment robustness.",
        "- If `state_driver_raw_active` improves over damage-only inputs, that is evidence that "
        "hidden energetic/history fields add prognostic value beyond visible crack geometry.",
        "- If damage-only is already strong, the correct caveat is that one monotonic trajectory can "
        "make RUL easy; the next validation must add multiple loading/material trajectories.",
        "- Raw and active psi are intentionally separated because previous inverse tests showed that "
        "raw psi can look high while the active degraded driver remains deficient.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fem-combined-mat", required=True, type=Path)
    p.add_argument("--nf", required=True, type=int)
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--l0", type=float, default=0.01)
    p.add_argument("--crack-strip-y", type=float, default=0.05)
    p.add_argument("--boundary-x", type=float, default=0.45)
    p.add_argument("--ridge-alpha", type=float, default=None,
                   help="Use a single ridge alpha instead of the default alpha grid.")
    p.add_argument("--ridge-alpha-grid", default="0.01,0.1,1,10,100",
                   help="Comma-separated ridge alphas; best LOOCV MAE is reported per feature set.")
    args = p.parse_args()

    fem = load_fem_handoff(args.fem_combined_mat)
    cycles = fem["cycles"].astype(int)
    rows: list[dict[str, float]] = []
    for k, cycle in enumerate(cycles):
        if cycle > args.nf:
            continue
        rows.append(
            feature_row(
                int(cycle),
                args.nf,
                fem["centroids"],
                fem["areas"],
                fem["damage"][k],
                fem["alpha_bar"][k],
                fem["fatigue_f"][k],
                fem["psi_raw"][k],
                l0=args.l0,
                crack_strip_y=args.crack_strip_y,
                boundary_x=args.boundary_x,
            )
        )

    if len(rows) < 5:
        raise RuntimeError(f"Need at least 5 snapshots for LOOCV, got {len(rows)}")

    all_feature_names = sorted(name for name in rows[0] if name not in {"cycle", "remaining_life"})
    feature_groups = feature_sets(all_feature_names)
    y = np.array([row["remaining_life"] for row in rows], dtype=float)
    alpha_grid = parse_alpha_grid(args.ridge_alpha, args.ridge_alpha_grid)

    summaries: list[dict[str, float | str]] = []
    for set_name, names in feature_groups.items():
        x = finite_design(rows, names)
        ridge_candidates = []
        for alpha in alpha_grid:
            pred = loocv_ridge_predict(x, y, alpha)
            ridge_candidates.append((metrics(y, pred), alpha, pred))
        ridge, best_alpha, ridge_pred = min(
            ridge_candidates,
            key=lambda item: (item[0]["mae_cycles"], item[0]["rmse_cycles"]),
        )
        nn_pred = loocv_nearest_neighbor(x, y)
        nn = metrics(y, nn_pred)
        for row, pred in zip(rows, ridge_pred):
            row[f"pred_rul_{set_name}"] = float(pred)
        summaries.append(
            {
                "feature_set": set_name,
                "n_features": float(len(names)),
                "ridge_alpha": float(best_alpha),
                "ridge_mae_cycles": ridge["mae_cycles"],
                "ridge_rmse_cycles": ridge["rmse_cycles"],
                "ridge_r2": ridge["r2"],
                "ridge_max_abs_error_cycles": ridge["max_abs_error_cycles"],
                "nn_mae_cycles": nn["mae_cycles"],
                "nn_rmse_cycles": nn["rmse_cycles"],
                "nn_r2": nn["r2"],
                "nn_max_abs_error_cycles": nn["max_abs_error_cycles"],
            }
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    row_fields = ["cycle", "remaining_life"] + all_feature_names + [
        f"pred_rul_{name}" for name in feature_groups
    ]
    write_csv(args.out_dir / "m2s_validation_cycle_features.csv", rows, row_fields)
    summary_fields = [
        "feature_set",
        "n_features",
        "ridge_alpha",
        "ridge_mae_cycles",
        "ridge_rmse_cycles",
        "ridge_r2",
        "ridge_max_abs_error_cycles",
        "nn_mae_cycles",
        "nn_rmse_cycles",
        "nn_r2",
        "nn_max_abs_error_cycles",
    ]
    write_csv(args.out_dir / "m2s_validation_summary.csv", summaries, summary_fields)
    write_markdown(
        args.out_dir / "m2s_validation_summary.md",
        args,
        cycles[: len(rows)],
        summaries,
        {name: len(features) for name, features in feature_groups.items()},
    )

    print(f"Wrote {args.out_dir / 'm2s_validation_summary.md'}")
    for row in summaries:
        print(
            f"{row['feature_set']}: ridge alpha={float(row['ridge_alpha']):.3g}, "
            f"MAE={float(row['ridge_mae_cycles']):.3g} cycles, "
            f"NN MAE={float(row['nn_mae_cycles']):.3g} cycles"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
