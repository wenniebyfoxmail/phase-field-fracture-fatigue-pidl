#!/usr/bin/env python3
"""Run the frozen Hard5 t+1/t+2 development-only forecast gate.

This command performs deterministic offline regression on existing FEM files.
It does not train PIDL, launch FEM, or use confirmed-cycle/event-relative input.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import meshio
import numpy as np
from scipy.io import loadmat


UMAX = {"u011": 0.11, "u012": 0.12, "u013": 0.13}
FIRST_DETECT = {"u011": 122, "u012": 83, "u013": 59}
CASE_DIR = {
    "u011": "SENS_hard5_u011_eta0_canonical_v1",
    "u012": "SENS_hard5_u012_eta0_formal_pidl_native_q4_v1",
    "u013": "SENS_hard5_u013_eta0_canonical_v1",
}
LOAD_FILE = {
    "u011": "load_displ_SENS_hard5_u011_eta0_canonical_v1.out",
    "u012": "load_displ_SENS_hard5_u012_eta0_formal_pidl_native_q4_v1.out",
    "u013": "load_displ_SENS_hard5_u013_eta0_canonical_v1.out",
}
ALPHA_FLOOR = 1.0e-8
PSI_FLOOR = 1.0e-12
RIDGE_LAMBDA = 1.0
START_CYCLE = 20
PRIMARY = ("damage_mae", "history_log_mae", "degradation_mae", "raw_log_mae")


@dataclass
class Case:
    name: str
    umax: float
    first_detect: int
    state: np.ndarray  # cycle, element, transformed channel
    stiffness: np.ndarray


@dataclass
class LinearMap:
    x_mean: np.ndarray
    x_scale: np.ndarray
    y_mean: np.ndarray
    y_scale: np.ndarray
    coefficient: np.ndarray
    stiffness: bool


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fem-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def read_areas(vtk: Path) -> tuple[np.ndarray, str]:
    mesh = meshio.read(vtk)
    connectivity = np.asarray(mesh.cells_dict["quad"], dtype=np.int64)
    xy = np.asarray(mesh.points, dtype=np.float64)[connectivity, :2]
    x, y = xy[:, :, 0], xy[:, :, 1]
    areas = 0.5 * np.abs(
        np.sum(x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1), axis=1)
    )
    if np.any(areas <= 0.0):
        raise ValueError("invalid quad areas")
    geometry_hash = hashlib.sha256(
        np.asarray(mesh.points, dtype=np.float64).tobytes() + connectivity.tobytes()
    ).hexdigest()
    return areas, geometry_hash


def parse_stiffness(path: Path, umax: float, cycles: int) -> np.ndarray:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if not fields or fields[0].lower() == "step":
            continue
        if len(fields) != 5:
            raise ValueError(f"bad load row: {line}")
        rows.append([float(value) for value in fields])
    table = np.asarray(rows, dtype=np.float64)
    if len(table) != cycles * 5:
        raise ValueError(f"{path} has {len(table)} rows, expected {cycles * 5}")
    blocks = table.reshape(cycles, 5, 5)
    if not np.all(np.rint(blocks[:, :, 0]).astype(int) == np.arange(1, 6)[None, :]):
        raise ValueError("five-step load sequence mismatch")
    stiffness = np.abs(blocks[:, 3, 4]) / umax
    if np.any(~np.isfinite(stiffness)) or np.any(stiffness <= 0.0):
        raise ValueError("invalid peak stiffness")
    return stiffness


def load_case(root: Path, name: str) -> Case:
    case_root = root / name / CASE_DIR[name]
    first = FIRST_DETECT[name]
    rows = []
    for cycle in range(1, first + 1):
        path = case_root / "psi_fields" / f"cycle_{cycle:04d}.mat"
        data = loadmat(
            path,
            variable_names=("d_elem", "alpha_bar_elem", "f_alpha_elem", "psi_elem"),
        )
        damage = np.asarray(data["d_elem"], dtype=np.float32).reshape(-1)
        alpha = np.asarray(data["alpha_bar_elem"], dtype=np.float32).reshape(-1)
        degradation = np.asarray(data["f_alpha_elem"], dtype=np.float32).reshape(-1)
        psi = np.asarray(data["psi_elem"], dtype=np.float32).reshape(-1)
        state = np.column_stack(
            [
                np.clip(damage, 0.0, 1.0),
                np.log10(np.maximum(alpha, ALPHA_FLOOR)),
                np.clip(degradation, 0.0, 1.0),
                np.log10(np.maximum(psi, PSI_FLOOR)),
            ]
        ).astype(np.float32)
        if not np.all(np.isfinite(state)):
            raise ValueError(f"non-finite state in {path}")
        rows.append(state)
    stiffness = parse_stiffness(case_root / LOAD_FILE[name], UMAX[name], cycles=len(list((case_root / "psi_fields").glob("cycle_*.mat"))))
    return Case(name, UMAX[name], first, np.stack(rows), stiffness[:first])


def stiffness_features(case: Case, t_index: int) -> np.ndarray:
    k = case.stiffness
    logk = np.log(k[t_index - 2 : t_index + 1])
    return np.asarray(
        [
            k[t_index] / k[0],
            logk[2] - logk[1],
            logk[2] - 2.0 * logk[1] + logk[0],
        ],
        dtype=np.float64,
    )


def feature_block(case: Case, t_index: int, use_stiffness: bool) -> tuple[np.ndarray, np.ndarray]:
    current = case.state[t_index].astype(np.float64)
    delta = current - case.state[t_index - 1].astype(np.float64)
    columns = [np.full((len(current), 1), case.umax), current, delta]
    if use_stiffness:
        sf = stiffness_features(case, t_index)
        columns.append(np.broadcast_to(sf, (len(current), len(sf))))
    x = np.concatenate(columns, axis=1)
    y = case.state[t_index + 1].astype(np.float64) - current
    return x, y


def training_indices(case: Case) -> range:
    # Zero-based t: c20 through c(first_detect-1), target no later than first detect.
    return range(START_CYCLE - 1, case.first_detect - 1)


def equal_trajectory_moments(cases: list[Case], use_stiffness: bool) -> tuple[np.ndarray, ...]:
    per_case = []
    for case in cases:
        sx = sy = sx2 = sy2 = None
        count = 0
        for t in training_indices(case):
            x, y = feature_block(case, t, use_stiffness)
            if sx is None:
                sx = np.zeros(x.shape[1]); sx2 = np.zeros(x.shape[1])
                sy = np.zeros(y.shape[1]); sy2 = np.zeros(y.shape[1])
            sx += x.sum(axis=0); sx2 += np.square(x).sum(axis=0)
            sy += y.sum(axis=0); sy2 += np.square(y).sum(axis=0)
            count += len(x)
        assert sx is not None and sy is not None and sx2 is not None and sy2 is not None
        per_case.append((sx / count, sx2 / count, sy / count, sy2 / count))
    x_mean = np.mean([row[0] for row in per_case], axis=0)
    x_second = np.mean([row[1] for row in per_case], axis=0)
    y_mean = np.mean([row[2] for row in per_case], axis=0)
    y_second = np.mean([row[3] for row in per_case], axis=0)
    x_variance = np.maximum(x_second - x_mean * x_mean, 0.0)
    y_variance = np.maximum(y_second - y_mean * y_mean, 0.0)
    x_scale = np.sqrt(x_variance)
    y_scale = np.sqrt(y_variance)
    # A single-trajectory ensemble member cannot identify between-trajectory
    # forcing variation. Keep constant columns inert instead of magnifying
    # roundoff through an arbitrarily tiny divisor.
    x_scale[x_scale < 1.0e-8] = 1.0
    y_scale[y_scale < 1.0e-10] = 1.0
    return x_mean, x_scale, y_mean, y_scale


def fit_map(cases: list[Case], use_stiffness: bool) -> LinearMap:
    x_mean, x_scale, y_mean, y_scale = equal_trajectory_moments(cases, use_stiffness)
    dimension = len(x_mean) + 1
    xtx = np.zeros((dimension, dimension), dtype=np.float64)
    xty = np.zeros((dimension, len(y_mean)), dtype=np.float64)
    for case in cases:
        local_xx = np.zeros_like(xtx); local_xy = np.zeros_like(xty); count = 0
        for t in training_indices(case):
            x, y = feature_block(case, t, use_stiffness)
            z = (x - x_mean) / x_scale
            z = np.column_stack([np.ones(len(z)), z])
            q = (y - y_mean) / y_scale
            if not np.all(np.isfinite(z)) or not np.all(np.isfinite(q)):
                raise FloatingPointError("non-finite standardized training block")
            local_xx += np.einsum("ni,nj->ij", z, z, optimize=True)
            local_xy += np.einsum("ni,nk->ik", z, q, optimize=True)
            count += len(z)
        xtx += local_xx / count / len(cases)
        xty += local_xy / count / len(cases)
    penalty = np.eye(dimension) * RIDGE_LAMBDA
    penalty[0, 0] = 0.0
    coefficient = np.linalg.solve(xtx + penalty, xty)
    return LinearMap(x_mean, x_scale, y_mean, y_scale, coefficient, use_stiffness)


def project(candidate: np.ndarray, previous: np.ndarray) -> np.ndarray:
    result = np.asarray(candidate, dtype=np.float64).copy()
    result[:, 0] = np.maximum(previous[:, 0], np.clip(result[:, 0], 0.0, 1.0))
    result[:, 1] = np.maximum(previous[:, 1], np.clip(result[:, 1], -8.0, 6.0))
    result[:, 2] = np.minimum(previous[:, 2], np.clip(result[:, 2], 0.0, 1.0))
    result[:, 3] = np.clip(result[:, 3], -12.0, 8.0)
    if not np.all(np.isfinite(result)):
        raise FloatingPointError("projection produced non-finite state")
    return result


def predict_one(model: LinearMap, case: Case, current: np.ndarray, delta: np.ndarray, sf: np.ndarray) -> np.ndarray:
    columns = [np.full((len(current), 1), case.umax), current, delta]
    if model.stiffness:
        columns.append(np.broadcast_to(sf, (len(current), len(sf))))
    x = np.concatenate(columns, axis=1)
    z = (x - model.x_mean) / model.x_scale
    z = np.column_stack([np.ones(len(z)), z])
    if not np.all(np.isfinite(z)) or not np.all(np.isfinite(model.coefficient)):
        raise FloatingPointError("non-finite forecast design or coefficient")
    increment = np.einsum("ni,io->no", z, model.coefficient, optimize=True)
    increment = increment * model.y_scale + model.y_mean
    return project(current + increment, current)


def forecast(model: LinearMap, case: Case, t: int, horizon: int) -> np.ndarray:
    current = case.state[t].astype(np.float64)
    delta = current - case.state[t - 1].astype(np.float64)
    sf = stiffness_features(case, t)
    for _ in range(horizon):
        nxt = predict_one(model, case, current, delta, sf)
        delta, current = nxt - current, nxt
    return current


def control_forecast(name: str, case: Case, t: int, horizon: int) -> np.ndarray:
    current = case.state[t].astype(np.float64)
    if name == "persistence":
        return current.copy()
    if name == "secant":
        delta = current - case.state[t - 1].astype(np.float64)
        return project(current + horizon * delta, current)
    raise KeyError(name)


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values)
    cumulative = np.cumsum(weights[order])
    index = min(int(np.searchsorted(cumulative, q * cumulative[-1], side="left")), len(order) - 1)
    return float(values[order[index]])


def weighted_corr(a: np.ndarray, b: np.ndarray, weights: np.ndarray) -> float:
    total = weights.sum(); ma = float(np.sum(a * weights) / total); mb = float(np.sum(b * weights) / total)
    da, db = a - ma, b - mb
    denominator = np.sqrt(np.sum(weights * da * da) * np.sum(weights * db * db))
    return float(np.sum(weights * da * db) / denominator) if denominator > 0.0 else float("nan")


def metrics(pred: np.ndarray, target: np.ndarray, areas: np.ndarray) -> dict[str, float]:
    weights = areas / areas.sum()
    absolute = np.abs(pred - target)
    active_pred = np.maximum(pred[:, 3] + 2.0 * np.log10(np.maximum(1.0 - pred[:, 0], 1.0e-6)), -12.0)
    active_target = np.maximum(target[:, 3] + 2.0 * np.log10(np.maximum(1.0 - target[:, 0], 1.0e-6)), -12.0)
    tau = weighted_quantile(active_target, areas, 0.99)
    own_tau = weighted_quantile(active_pred, areas, 0.99)
    truth = active_target >= tau; common = active_pred >= tau; own = active_pred >= own_tau
    def iou(mask: np.ndarray) -> float:
        union = areas[truth | mask].sum()
        return float(areas[truth & mask].sum() / union) if union > 0 else float("nan")
    return {
        "damage_mae": float(np.sum(weights * absolute[:, 0])),
        "history_log_mae": float(np.sum(weights * absolute[:, 1])),
        "degradation_mae": float(np.sum(weights * absolute[:, 2])),
        "raw_log_mae": float(np.sum(weights * absolute[:, 3])),
        "active_log_mae": float(np.sum(weights * np.abs(active_pred - active_target))),
        "active_correlation": weighted_corr(active_pred, active_target, areas),
        "absolute_p99_iou": iou(common),
        "own_p99_iou": iou(own),
        "support_area_ratio": float(areas[common].sum() / areas[truth].sum()),
    }


def uncertainty_metrics(predictions: list[np.ndarray], target: np.ndarray, areas: np.ndarray) -> dict[str, float]:
    stack = np.stack(predictions)
    lower = np.quantile(stack, 0.05, axis=0)
    upper = np.quantile(stack, 0.95, axis=0)
    weights = areas / areas.sum()
    result = {}
    labels = ("damage", "history_log", "degradation", "raw_log")
    for index, label in enumerate(labels):
        covered = (target[:, index] >= lower[:, index]) & (target[:, index] <= upper[:, index])
        result[f"uncalibrated90_{label}_coverage"] = float(np.sum(weights * covered))
        result[f"uncalibrated90_{label}_width"] = float(np.sum(weights * (upper[:, index] - lower[:, index])))
    return result


def average_rows(rows: list[dict[str, float | int | str]]) -> list[dict[str, float | int | str]]:
    keys = ("model", "holdout", "horizon", "stratum")
    grouped: dict[tuple, list[dict]] = {}
    for row in rows:
        grouped.setdefault(tuple(row[key] for key in keys), []).append(row)
    output = []
    for group, members in grouped.items():
        row = dict(zip(keys, group)); row["origins"] = len(members)
        numeric = [key for key in members[0] if key not in keys and key != "origin_cycle"]
        for key in numeric:
            row[key] = float(np.nanmean([float(member[key]) for member in members]))
        output.append(row)
    return sorted(output, key=lambda row: (row["holdout"], row["horizon"], row["stratum"], row["model"]))


def decide(summary: list[dict]) -> list[dict[str, object]]:
    lookup = {(r["model"], r["holdout"], int(r["horizon"]), r["stratum"]): r for r in summary}
    decisions = []
    for horizon in (1, 2):
        ridge_improved = 0; ridge_max_ratio = 0.0; absolute_all = True
        stiffness_all = True; stiffness_max_ratio = 0.0
        for holdout in UMAX:
            p = lookup[("persistence", holdout, horizon, "ordinary")]
            r = lookup[("ridge", holdout, horizon, "ordinary")]
            s = lookup[("ridge_stiffness", holdout, horizon, "ordinary")]
            ratios_r = [r[key] / max(p[key], 1.0e-15) for key in PRIMARY]
            ratios_s = [s[key] / max(r[key], 1.0e-15) for key in PRIMARY]
            ridge_improved += sum(value < 1.0 for value in ratios_r) >= 3
            ridge_max_ratio = max(ridge_max_ratio, *ratios_r)
            stiffness_all &= sum(value < 1.0 for value in ratios_s) >= 3
            stiffness_max_ratio = max(stiffness_max_ratio, *ratios_s)
            absolute_all &= (
                r["damage_mae"] <= 0.020 and r["history_log_mae"] <= 0.030
                and r["active_log_mae"] <= 0.50 and r["active_correlation"] >= 0.80
                and r["absolute_p99_iou"] >= 0.50 and r["own_p99_iou"] >= 0.50
                and 0.67 <= r["support_area_ratio"] <= 1.50
            )
        decisions.append(
            {
                "horizon": horizon,
                "ridge_absolute_all_3": bool(absolute_all),
                "ridge_incremental_pass": bool(ridge_improved >= 2 and ridge_max_ratio <= 1.25),
                "ridge_trajectories_improving_3of4": int(ridge_improved),
                "ridge_max_primary_ratio": ridge_max_ratio,
                "stiffness_incremental_pass": bool(stiffness_all and stiffness_max_ratio <= 1.10),
                "stiffness_max_primary_ratio": stiffness_max_ratio,
            }
        )
    return decisions


def write_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = list(rows[0])
    for row in rows[1:]:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader(); writer.writerows(rows)


def main() -> None:
    args = parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    args.output.mkdir(parents=True)
    cases = {name: load_case(args.fem_root, name) for name in UMAX}
    reference_vtk = next((args.fem_root / "u011" / CASE_DIR["u011"]).glob("fields_*_005.vtk"))
    areas, geometry_hash = read_areas(reference_vtk)
    if any(case.state.shape[1] != len(areas) for case in cases.values()):
        raise ValueError("field/mesh element count mismatch")

    rows = []
    coefficient_receipts = {}
    for holdout, challenge in cases.items():
        training = [case for name, case in cases.items() if name != holdout]
        models = {}
        ensembles = {}
        for use_stiffness, label in ((False, "ridge"), (True, "ridge_stiffness")):
            pooled = fit_map(training, use_stiffness)
            solo = [fit_map([case], use_stiffness) for case in training]
            models[label] = pooled; ensembles[label] = [*solo, pooled]
            coefficient_receipts[f"{holdout}_{label}"] = {
                "coefficient": pooled.coefficient.tolist(),
                "x_mean": pooled.x_mean.tolist(), "x_scale": pooled.x_scale.tolist(),
                "y_mean": pooled.y_mean.tolist(), "y_scale": pooled.y_scale.tolist(),
            }
        for horizon in (1, 2):
            last_t = challenge.first_detect - horizon - 1
            for t in range(START_CYCLE - 1, last_t + 1):
                target = challenge.state[t + horizon].astype(np.float64)
                target_cycle = t + horizon + 1
                stratum = "stress" if target_cycle == challenge.first_detect else "ordinary"
                for label in ("persistence", "secant"):
                    pred = control_forecast(label, challenge, t, horizon)
                    rows.append({"model": label, "holdout": holdout, "horizon": horizon, "stratum": stratum, "origin_cycle": t + 1, **metrics(pred, target, areas)})
                for label, model in models.items():
                    pred = forecast(model, challenge, t, horizon)
                    members = [forecast(member, challenge, t, horizon) for member in ensembles[label]]
                    rows.append({"model": label, "holdout": holdout, "horizon": horizon, "stratum": stratum, "origin_cycle": t + 1, **metrics(pred, target, areas), **uncertainty_metrics(members, target, areas)})

    summary = average_rows(rows)
    decisions = decide(summary)
    write_csv(args.output / "origin_metrics.csv", rows)
    write_csv(args.output / "fold_summary.csv", summary)
    write_csv(args.output / "gate_decisions.csv", decisions)
    (args.output / "coefficients.json").write_text(json.dumps(coefficient_receipts, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "status": "development_only",
        "fem_root": str(args.fem_root.resolve()),
        "first_detect": FIRST_DETECT,
        "confirmed_cycles_used": False,
        "start_cycle": START_CYCLE,
        "ridge_lambda": RIDGE_LAMBDA,
        "geometry_hash": geometry_hash,
        "reference_vtk": str(reference_vtk),
        "uncertainty_label": "uncalibrated descriptive ensemble",
        "outputs": ["origin_metrics.csv", "fold_summary.csv", "gate_decisions.csv", "coefficients.json"],
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    verdict = "DEVELOPMENT_FEASIBILITY_POSITIVE" if all(row["ridge_absolute_all_3"] and row["ridge_incremental_pass"] for row in decisions) else "DIAGNOSTIC_NEGATIVE__NO_ARCHITECTURE_EXPANSION"
    stiffness = "STIFFNESS_INCREMENTAL_POSITIVE" if all(row["stiffness_incremental_pass"] for row in decisions) else "STIFFNESS_INCREMENTAL_NEGATIVE"
    decision_text = f"""# Cross-Umax short-horizon forecast decision\n\n- Primary verdict: `{verdict}`\n- Stiffness ablation: `{stiffness}`\n- Scope: development-only FEM-state oracle within one matched Hard5 family.\n- Event: first detect only; confirmed cycles were not used.\n- Uncertainty: uncalibrated descriptive ensemble only.\n\nSee `gate_decisions.csv` and `fold_summary.csv`. A positive result authorizes only a sealed unseen-trajectory request, never a deployment or calibrated-uncertainty claim.\n"""
    (args.output / "decision.md").write_text(decision_text, encoding="utf-8")
    manifest["outputs"].append("decision.md")
    manifest["output_sha256"] = {name: sha256(args.output / name) for name in manifest["outputs"]}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": verdict, "stiffness": stiffness, "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
