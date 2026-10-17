#!/usr/bin/env python3
"""S04-E013: no-training three-Umax residual-sufficiency audit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


LOG_FLOOR = 1.0e-12
PRIMARY_CHANNELS = ("damage", "history", "raw_log10")
POD_RANKS = (1, 2, 4, 8, 16, 20)
SUPPORT_QUANTILES = (0.95, 0.99, 0.995)
BOOTSTRAP_SEED = 20261008
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_BLOCK = 5
PRIMARY_RATIO_THRESHOLD = 0.90
RUNTIME_RELATIVE_TOLERANCE = 0.01


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty table: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(dict.fromkeys(key for row in rows for key in row))
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values)
    sorted_values = values[order]
    cumulative = np.cumsum(weights[order], dtype=np.float64)
    cutoff = q * cumulative[-1]
    return float(sorted_values[min(np.searchsorted(cumulative, cutoff), len(values) - 1)])


def weighted_rmse(values: np.ndarray, weights: np.ndarray, mask: np.ndarray | None = None) -> float:
    if mask is not None:
        values, weights = values[mask], weights[mask]
    denominator = float(np.sum(weights))
    if denominator <= 0 or len(values) == 0:
        return float("nan")
    return float(np.sqrt(np.sum(weights * values * values) / denominator))


def weighted_mae(values: np.ndarray, weights: np.ndarray, mask: np.ndarray | None = None) -> float:
    if mask is not None:
        values, weights = values[mask], weights[mask]
    denominator = float(np.sum(weights))
    return float(np.sum(weights * np.abs(values)) / denominator) if denominator > 0 else float("nan")


def weighted_corr(a: np.ndarray, b: np.ndarray, weights: np.ndarray) -> float:
    total = float(weights.sum())
    ma, mb = float(np.sum(weights * a) / total), float(np.sum(weights * b) / total)
    da, db = a - ma, b - mb
    denominator = math.sqrt(float(np.sum(weights * da * da) * np.sum(weights * db * db)))
    return float(np.sum(weights * da * db) / denominator) if denominator > 0 else float("nan")


def support_metrics(reference: np.ndarray, candidate: np.ndarray, areas: np.ndarray, q: float) -> dict[str, float]:
    threshold = weighted_quantile(reference, areas, q)
    own_threshold = weighted_quantile(candidate, areas, q)
    ref_mask = reference >= threshold
    candidate_absolute = candidate >= threshold
    candidate_own = candidate >= own_threshold

    def area(mask: np.ndarray) -> float:
        return float(areas[mask].sum())

    def iou(left: np.ndarray, right: np.ndarray) -> float:
        union = area(left | right)
        return area(left & right) / union if union else float("nan")

    ref_area = area(ref_mask)
    return {
        "threshold": threshold,
        "iou_absolute": iou(ref_mask, candidate_absolute),
        "absolute_area_ratio": area(candidate_absolute) / ref_area if ref_area else float("nan"),
        "iou_own_quantile": iou(ref_mask, candidate_own),
    }


def phase_label(cycle: int, event_cycle: int) -> str:
    tau = (cycle - 1) / (event_cycle - 1)
    if cycle == event_cycle:
        return "event"
    if cycle <= 20:
        return "early_c1_c20"
    if tau < 0.8:
        return "middle"
    return "late_pre_event"


def load_and_validate(lock: dict[str, object]) -> tuple[dict[str, dict[str, object]], np.ndarray, np.ndarray, dict[str, object]]:
    locked_files = [lock["graph"], lock["fem_manifest"]]
    for spec in lock["trajectories"]:
        locked_files.extend(
            [
                {"path": spec["fem_path"], "sha256": spec["fem_sha256"]},
                {"path": spec["pidl_path"], "sha256": spec["pidl_sha256"]},
                {"path": spec["locked_spot_path"], "sha256": spec["locked_spot_sha256"]},
            ]
        )
    hash_rows = []
    for record in locked_files:
        path = Path(record["path"])
        actual = sha256(path)
        if actual != record["sha256"]:
            raise ValueError(f"hash mismatch: {path}: {actual} != {record['sha256']}")
        hash_rows.append({"path": str(path), "sha256": actual, "bytes": path.stat().st_size})

    manifest = json.loads(Path(lock["fem_manifest"]["path"]).read_text())
    if manifest["teacher_qualified"] or manifest["physical_validation"]:
        raise ValueError("FEM manifest scope unexpectedly promoted")
    if manifest["state_channels"] != [
        "damage_clipped_0_1",
        "alpha_bar_nonnegative",
        "fatigue_degradation_clipped_0_1",
        "log10_peak_raw_tensile_driver",
    ]:
        raise ValueError("unexpected FEM channel order")

    with np.load(lock["graph"]["path"], allow_pickle=False) as graph:
        centroids = np.asarray(graph["centroids"], dtype=np.float64)
        areas = np.asarray(graph["areas"], dtype=np.float64)
    if centroids.shape != (86408, 2) or areas.shape != (86408,) or np.any(areas <= 0):
        raise ValueError("invalid common FEM grid")

    cases: dict[str, dict[str, object]] = {}
    for spec in lock["trajectories"]:
        tid, event = spec["trajectory_id"], int(spec["event_cycle"])
        with np.load(spec["fem_path"], allow_pickle=False) as fem, np.load(
            spec["pidl_path"], allow_pickle=False
        ) as pidl:
            fem_cycles = np.asarray(fem["cycles"], dtype=int)
            pidl_cycles = np.asarray(pidl["cycles"], dtype=int)
            expected = np.arange(1, event + 1)
            if str(fem["trajectory_id"]) != tid or str(pidl["trajectory_id"]) != tid:
                raise ValueError(f"{tid}: trajectory identity mismatch")
            if str(fem["physics_family"]) != "hard_eta0_5step":
                raise ValueError(f"{tid}: unexpected FEM physics family")
            if not np.isclose(float(fem["umax"]), float(spec["umax"])) or not np.isclose(
                float(pidl["umax"]), float(spec["umax"])
            ):
                raise ValueError(f"{tid}: Umax mismatch")
            if int(fem["first_hit_cycle"]) != event:
                raise ValueError(f"{tid}: FEM first-hit mismatch")
            if not np.array_equal(fem_cycles[:event], expected) or not np.array_equal(pidl_cycles, expected):
                raise ValueError(f"{tid}: cycle mismatch")
            if not np.array_equal(np.asarray(pidl["raw_steps"]), 5 * expected - 1):
                raise ValueError(f"{tid}: peak step mapping mismatch")
            if not np.array_equal(np.asarray(pidl["fem_centroids"], dtype=np.float64), centroids):
                raise ValueError(f"{tid}: centroid mismatch")
            if not np.array_equal(np.asarray(pidl["fem_areas"], dtype=np.float64), areas):
                raise ValueError(f"{tid}: area mismatch")
            fs = np.asarray(fem["states"][:event], dtype=np.float32)
            damage = np.asarray(pidl["damage"], dtype=np.float32)
            history = np.asarray(pidl["alpha_bar"], dtype=np.float32)
            fatigue = np.asarray(pidl["fatigue_f"], dtype=np.float32)
            raw = np.asarray(pidl["psi_raw_direct"], dtype=np.float32)
            active = np.asarray(pidl["psi_active_direct"], dtype=np.float32)
            expected_shape = (event, len(areas))
            if fs.shape != (event, len(areas), 4) or any(
                array.shape != expected_shape for array in (damage, history, fatigue, raw, active)
            ):
                raise ValueError(f"{tid}: field shape mismatch")
            labels = np.asarray(pidl["state_labels"])
            if not np.array_equal(labels, np.asarray([f"c{cycle}_peak" for cycle in expected])):
                raise ValueError(f"{tid}: state-label peak semantics mismatch")
        arrays = (fs, damage, history, fatigue, raw, active)
        if any(np.any(~np.isfinite(array)) for array in arrays):
            raise ValueError(f"{tid}: non-finite input")
        fem_raw_log = fs[:, :, 3]
        fem_active = ((1.0 - fs[:, :, 0]) ** 2 * np.power(10.0, fem_raw_log)).astype(np.float32)
        cases[tid] = {
            "spec": spec,
            "cycles": expected,
            "tau": (expected - 1) / (event - 1),
            "residuals": {
                "damage": (fs[:, :, 0] - damage).astype(np.float32),
                "history": (fs[:, :, 1] - history).astype(np.float32),
                "raw_log10": (fem_raw_log - np.log10(np.maximum(raw, LOG_FLOOR))).astype(np.float32),
            },
            "fem_fields": {
                "damage": fs[:, :, 0], "history": fs[:, :, 1],
                "fatigue_f": fs[:, :, 2], "raw_log10": fem_raw_log, "active": fem_active,
            },
            "pidl_fields": {
                "damage": damage, "history": history, "fatigue_f": fatigue,
                "raw_log10": np.log10(np.maximum(raw, LOG_FLOOR)).astype(np.float32),
                "active": active,
            },
        }
    return cases, centroids, areas, {"hashes": hash_rows, "fem_manifest": manifest}


def oracle_projection(
    residual: np.ndarray,
    mean: np.ndarray,
    sqrtw: np.ndarray,
    basis: np.ndarray,
    areas: np.ndarray,
    mask: np.ndarray | None,
) -> tuple[np.ndarray, int]:
    rank = len(basis)
    if mask is None:
        coefficients = np.einsum(
            "i,ki->k", (residual - mean) * sqrtw, basis, optimize=False
        )
        effective_rank = rank
    else:
        physical_basis = basis[:, mask] / sqrtw[mask]
        design = physical_basis.T * np.sqrt(areas[mask])[:, None]
        target = (residual[mask] - mean[mask]) * np.sqrt(areas[mask])
        coefficients, _, effective_rank, _ = np.linalg.lstsq(design, target, rcond=None)
    reconstructed_weighted = np.einsum("k,ki->i", coefficients, basis, optimize=False)
    return mean + reconstructed_weighted / sqrtw, int(effective_rank)


def oracle_error_ratio(
    residual: np.ndarray,
    mean: np.ndarray,
    sqrtw: np.ndarray,
    basis: np.ndarray,
    areas: np.ndarray,
    mask: np.ndarray | None,
) -> tuple[float, float, float, int]:
    reconstructed, effective_rank = oracle_projection(residual, mean, sqrtw, basis, areas, mask)
    baseline = weighted_rmse(residual, areas, mask)
    error = weighted_rmse(residual - reconstructed, areas, mask)
    ratio = error / baseline if baseline > np.finfo(float).tiny else float("nan")
    return baseline, error, ratio, effective_rank


def runtime_sensitivity(cases: dict[str, dict[str, object]], areas: np.ndarray) -> tuple[list[dict[str, object]], str]:
    rows = []
    tids = list(cases)
    for tid, case in cases.items():
        spec, idx = case["spec"], int(case["spec"]["spot_cycle"]) - 1
        with np.load(spec["locked_spot_path"], allow_pickle=False) as locked:
            locked_residuals = {
                "damage": case["fem_fields"]["damage"][idx] - locked["damage"],
                "history": case["fem_fields"]["history"][idx] - locked["alpha_bar"],
                "raw_log10": case["fem_fields"]["raw_log10"][idx]
                - np.log10(np.maximum(locked["psi_raw_direct"], LOG_FLOOR)),
            }
        support = case["fem_fields"]["active"][idx] >= weighted_quantile(
            case["fem_fields"]["active"][idx], areas, 0.99
        )
        for channel in PRIMARY_CHANNELS:
            mask = support if channel == "raw_log10" else None
            train = np.concatenate(
                [cases[train_id]["residuals"][channel] for train_id in tids if train_id != tid], axis=0
            )
            try:
                mean, sqrtw, basis, _, _ = pod_basis(train, areas, max(POD_RANKS))
            except ValueError as error:
                rows.append({"trajectory_id": tid, "umax": spec["umax"], "cycle": idx + 1,
                             "channel": channel, "status": "UNIDENTIFIED", "reason": str(error)})
                continue
            if len(basis) < max(POD_RANKS):
                rows.append({"trajectory_id": tid, "umax": spec["umax"], "cycle": idx + 1,
                             "channel": channel, "status": "UNIDENTIFIED",
                             "reason": f"numerical POD rank {len(basis)} below 20"})
                continue
            current, current_error, current_ratio, current_effective_rank = oracle_error_ratio(
                case["residuals"][channel][idx], mean, sqrtw, basis, areas, mask
            )
            reference, reference_error, reference_ratio, reference_effective_rank = oracle_error_ratio(
                np.asarray(locked_residuals[channel]), mean, sqrtw, basis, areas, mask
            )
            if not np.all(np.isfinite([current, current_error, current_ratio, reference,
                                       reference_error, reference_ratio])):
                rows.append({"trajectory_id": tid, "umax": spec["umax"], "cycle": idx + 1,
                             "channel": channel, "status": "UNIDENTIFIED",
                             "reason": "non-finite baseline or oracle ratio"})
                continue
            relative = abs(current - reference) / max(abs(reference), np.finfo(float).tiny)
            ratio_relative = abs(current_ratio - reference_ratio) / max(
                abs(reference_ratio), np.finfo(float).tiny
            )
            rows.append(
                {"trajectory_id": tid, "umax": spec["umax"], "cycle": idx + 1,
                 "channel": channel, "taobo_rmse": current, "locked_rmse": reference,
                 "relative_change": relative, "taobo_oracle_rmse": current_error,
                 "locked_oracle_rmse": reference_error, "taobo_error_ratio": current_ratio,
                 "locked_error_ratio": reference_ratio, "ratio_relative_change": ratio_relative,
                 "taobo_effective_rank": current_effective_rank,
                 "locked_effective_rank": reference_effective_rank,
                 "threshold_side_stable": (current_ratio < PRIMARY_RATIO_THRESHOLD)
                 == (reference_ratio < PRIMARY_RATIO_THRESHOLD), "status": "PENDING", "reason": ""}
            )
    for channel in PRIMARY_CHANNELS:
        locally_identified = [row for row in rows if row["channel"] == channel and row["status"] == "PENDING"]
        for row in locally_identified:
            row["baseline_within_1pct"] = row["relative_change"] <= RUNTIME_RELATIVE_TOLERANCE
            row["oracle_ratio_within_1pct"] = row["ratio_relative_change"] <= RUNTIME_RELATIVE_TOLERANCE
            if not (
                row["baseline_within_1pct"]
                and row["oracle_ratio_within_1pct"]
                and row["threshold_side_stable"]
            ):
                row["status"] = "FAIL"
                row["reason"] = "locked-spot runtime sensitivity exceeded frozen gate"
        identified = [
            row for row in rows if row["channel"] == channel and row["status"] in {"PENDING", "FAIL"}
        ]
        if len(identified) != len(cases):
            for row in identified:
                if row["status"] != "FAIL":
                    row["status"] = "UNIDENTIFIED"
                    row["reason"] = "Umax rank order unavailable because another spot metric is unidentified"
            continue
        selected = identified
        taobo_order = [row["trajectory_id"] for row in sorted(selected, key=lambda row: row["taobo_rmse"])]
        locked_order = [row["trajectory_id"] for row in sorted(selected, key=lambda row: row["locked_rmse"])]
        rank_stable = taobo_order == locked_order
        for row in selected:
            row["taobo_rank_order"] = ">".join(taobo_order)
            row["locked_rank_order"] = ">".join(locked_order)
            row["rank_stable"] = rank_stable
            if not rank_stable:
                row["status"] = "FAIL"
                row["reason"] = "locked-spot Umax rank order changed"
            elif row["status"] == "PENDING":
                row["status"] = "PASS"
    statuses = {row["status"] for row in rows}
    status = status_priority(statuses)
    return rows, status


def status_priority(statuses) -> str:
    statuses = set(statuses)
    if "FAIL" in statuses:
        return "FAIL"
    if "UNIDENTIFIED" in statuses or "PENDING" in statuses:
        return "UNIDENTIFIED"
    return "PASS"


def cycle_and_support_metrics(cases: dict[str, dict[str, object]], areas: np.ndarray):
    cycle_rows, support_rows = [], []
    for tid, case in cases.items():
        event = int(case["spec"]["event_cycle"])
        for idx, cycle in enumerate(case["cycles"]):
            for channel in PRIMARY_CHANNELS:
                residual = case["residuals"][channel][idx]
                cycle_rows.append(
                    {"trajectory_id": tid, "umax": case["spec"]["umax"], "cycle": int(cycle),
                     "tau": float(case["tau"][idx]), "phase": phase_label(int(cycle), event),
                     "channel": channel, "area_mae": weighted_mae(residual, areas),
                     "area_rmse": weighted_rmse(residual, areas),
                     "area_correlation": weighted_corr(
                         case["fem_fields"][channel][idx], case["pidl_fields"][channel][idx], areas
                     )}
                )
            for q in SUPPORT_QUANTILES:
                metrics = support_metrics(
                    case["fem_fields"]["active"][idx], case["pidl_fields"]["active"][idx], areas, q
                )
                support_rows.append(
                    {"trajectory_id": tid, "umax": case["spec"]["umax"], "cycle": int(cycle),
                     "tau": float(case["tau"][idx]), "phase": phase_label(int(cycle), event),
                     "quantile": q, **metrics}
                )
    return cycle_rows, support_rows


def pod_basis(train: np.ndarray, areas: np.ndarray, max_rank: int = 20):
    train64 = np.asarray(train, dtype=np.float64)
    mean = train64.mean(axis=0)
    sqrtw = np.sqrt(np.asarray(areas, dtype=np.float64) / np.sum(areas))
    centered = (train64 - mean) * sqrtw
    _, all_singular, right = np.linalg.svd(centered, full_matrices=False)
    if not len(all_singular) or all_singular[0] <= 0:
        raise ValueError("POD training residual has zero energy")
    tolerance = max(centered.shape) * np.finfo(np.float64).eps * all_singular[0]
    retained = all_singular[all_singular > tolerance]
    total_energy = float(np.sum(retained * retained))
    singular = retained[:max_rank]
    basis = right[: len(singular)]
    orthogonality_error = float(np.max(np.abs(basis @ basis.T - np.eye(len(basis)))))
    if orthogonality_error > 1.0e-10:
        raise ValueError(f"POD basis orthogonality failure: {orthogonality_error:.3e}")
    return mean, sqrtw, basis, singular, total_energy


def moving_block_upper(values: np.ndarray, seed: int) -> tuple[float, float]:
    values = np.asarray(values, dtype=np.float64)
    if len(values) < 20 or np.any(~np.isfinite(values)):
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    medians = np.empty(BOOTSTRAP_REPLICATES)
    blocks = math.ceil(len(values) / BOOTSTRAP_BLOCK)
    offsets = np.arange(BOOTSTRAP_BLOCK)
    for idx in range(BOOTSTRAP_REPLICATES):
        starts = rng.integers(0, len(values) - BOOTSTRAP_BLOCK + 1, size=blocks)
        sample_idx = (starts[:, None] + offsets).ravel()[: len(values)]
        medians[idx] = np.median(values[sample_idx])
    return float(np.median(values)), float(np.quantile(medians, 0.975))


def pod_holdouts(cases: dict[str, dict[str, object]], areas: np.ndarray):
    rows, primary_rows, spectra = [], [], []
    tids = list(cases)
    for fold_index, heldout in enumerate(tids):
        train_ids = [tid for tid in tids if tid != heldout]
        test_case = cases[heldout]
        for channel_index, channel in enumerate(PRIMARY_CHANNELS):
            train = np.concatenate([cases[tid]["residuals"][channel] for tid in train_ids], axis=0)
            mean, sqrtw, basis, singular, total_energy = pod_basis(train, areas, max(POD_RANKS))
            cumulative = np.cumsum(singular * singular) / total_energy
            for rank, captured in enumerate(cumulative, start=1):
                spectra.append({"heldout": heldout, "channel": channel, "rank": rank,
                                "training_energy_fraction": float(captured)})
            test = test_case["residuals"][channel]
            for rank in POD_RANKS:
                ratios = []
                for idx, cycle in enumerate(test_case["cycles"]):
                    if channel == "raw_log10":
                        active = test_case["fem_fields"]["active"][idx]
                        mask = active >= weighted_quantile(active, areas, 0.99)
                    else:
                        mask = None
                    if len(basis) < rank:
                        baseline, error, ratio = weighted_rmse(test[idx], areas, mask), float("nan"), float("nan")
                    else:
                        try:
                            baseline, error, ratio, effective_rank = oracle_error_ratio(
                                test[idx], mean, sqrtw, basis[:rank], areas, mask
                            )
                        except ValueError:
                            baseline, error, ratio = (
                                weighted_rmse(test[idx], areas, mask), float("nan"), float("nan")
                            )
                            effective_rank = 0
                    ratios.append(ratio)
                    rows.append({"heldout": heldout, "train_ids": "+".join(train_ids),
                                 "channel": channel, "rank": rank, "cycle": int(cycle),
                                 "tau": float(test_case["tau"][idx]), "baseline_rmse": baseline,
                                 "oracle_pod_rmse": error, "error_ratio": ratio,
                                 "effective_projection_rank": effective_rank if len(basis) >= rank else 0})
                if rank == 20:
                    median, upper = moving_block_upper(
                        np.asarray(ratios), BOOTSTRAP_SEED + fold_index * 10 + channel_index
                    )
                    primary_rows.append(
                        {"heldout": heldout, "train_ids": "+".join(train_ids), "channel": channel,
                         "rank": rank, "valid_cycles": int(np.isfinite(ratios).sum()),
                         "median_error_ratio": median, "bootstrap_upper97p5": upper,
                         "identified": bool(np.isfinite(upper)),
                         "pass_upper975_lt_0p90": bool(
                             np.isfinite(upper) and upper < PRIMARY_RATIO_THRESHOLD
                         )}
                    )
    return rows, primary_rows, spectra


def landmark_similarity(cases: dict[str, dict[str, object]], areas: np.ndarray):
    rows, tids = [], list(cases)
    for channel in PRIMARY_CHANNELS:
        for tau in (0.0, 0.25, 0.5, 0.75, 1.0):
            selected = {}
            for tid, case in cases.items():
                idx = int(np.argmin(np.abs(case["tau"] - tau)))
                selected[tid] = (idx, case["residuals"][channel][idx])
            for i, left in enumerate(tids):
                for right in tids[i + 1 :]:
                    rows.append({"channel": channel, "target_tau": tau, "left": left, "right": right,
                                 "left_cycle": int(cases[left]["cycles"][selected[left][0]]),
                                 "right_cycle": int(cases[right]["cycles"][selected[right][0]]),
                                 "area_correlation": weighted_corr(selected[left][1], selected[right][1], areas)})
    return rows


def make_figures(out: Path, cases, cycle_rows, support_rows, pod_rows) -> None:
    figures = out / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    colors = {"hard5_u011": "#0072B2", "hard5_u012": "#E69F00", "hard5_u013": "#009E73"}
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), constrained_layout=True)
    for ax, channel in zip(axes, PRIMARY_CHANNELS):
        for tid in cases:
            rows = [row for row in cycle_rows if row["trajectory_id"] == tid and row["channel"] == channel]
            ax.plot([r["tau"] for r in rows], [r["area_rmse"] for r in rows], color=colors[tid], label=tid)
        ax.set(title=channel, xlabel="normalized progress tau", ylabel="area RMSE")
        ax.set_yscale("log")
    axes[0].legend(frameon=False)
    fig.savefig(figures / "residual_magnitude_by_progress.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.5, 4.2), constrained_layout=True)
    for tid in cases:
        rows = [r for r in support_rows if r["trajectory_id"] == tid and r["quantile"] == 0.99]
        ax.plot([r["tau"] for r in rows], [r["iou_absolute"] for r in rows], color=colors[tid], label=tid)
    ax.set(xlabel="normalized progress tau", ylabel="absolute-threshold IoU", title="FEM-p99 active support")
    ax.legend(frameon=False)
    fig.savefig(figures / "active_support_iou_by_progress.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), constrained_layout=True)
    for ax, channel in zip(axes, PRIMARY_CHANNELS):
        for heldout in cases:
            rows = [r for r in pod_rows if r["heldout"] == heldout and r["channel"] == channel]
            grouped = {rank: np.nanmedian([r["error_ratio"] for r in rows if r["rank"] == rank]) for rank in POD_RANKS}
            ax.plot(list(grouped), list(grouped.values()), marker="o", color=colors[heldout], label=heldout)
        ax.axhline(1.0, color="black", linestyle=":", linewidth=1)
        ax.axhline(PRIMARY_RATIO_THRESHOLD, color="black", linestyle="--", linewidth=1)
        ax.set(title=channel, xlabel="POD rank", ylabel="median oracle error ratio", xscale="log")
    axes[0].legend(frameon=False, title="held out")
    fig.savefig(figures / "pod_holdout_error_ratio.png", dpi=180)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-lock", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out = args.output_dir.resolve()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError(f"output directory is not empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "tables").mkdir()
    lock = json.loads(args.input_lock.read_text())
    cases, centroids, areas, validation = load_and_validate(lock)
    validation.update({"status": "PASS", "cell_count": len(areas), "trajectory_count": len(cases)})
    (out / "input_validation.json").write_text(json.dumps(validation, indent=2) + "\n")

    sensitivity_rows, sensitivity_status = runtime_sensitivity(cases, areas)
    write_csv(out / "tables" / "runtime_sensitivity.csv", sensitivity_rows)
    if sensitivity_status != "PASS":
        verdict = "inadmissible" if sensitivity_status == "FAIL" else "inconclusive"
        decision = {"experiment_id": "S04-E013", "run_id": args.run_id,
                    "verdict": verdict, "runtime_sensitivity_gate": sensitivity_status,
                    "reason": "runtime sensitivity exceeded frozen gate" if verdict == "inadmissible"
                    else "runtime sensitivity metric was unidentified"}
        (out / "decision.json").write_text(json.dumps(decision, indent=2) + "\n")
        print(json.dumps(decision, indent=2))
        return

    cycle_rows, support_rows = cycle_and_support_metrics(cases, areas)
    pod_rows, primary_rows, spectra = pod_holdouts(cases, areas)
    landmark_rows = landmark_similarity(cases, areas)
    write_csv(out / "tables" / "per_cycle_residual_metrics.csv", cycle_rows)
    write_csv(out / "tables" / "active_support_metrics.csv", support_rows)
    write_csv(out / "tables" / "pod_holdout_metrics.csv", pod_rows)
    write_csv(out / "tables" / "pod_primary_summary.csv", primary_rows)
    write_csv(out / "tables" / "pod_training_spectrum.csv", spectra)
    write_csv(out / "tables" / "cross_umax_landmark_similarity.csv", landmark_rows)
    make_figures(out, cases, cycle_rows, support_rows, pod_rows)

    all_identified = all(row["identified"] for row in primary_rows)
    any_identified_fail = any(
        row["identified"] and not row["pass_upper975_lt_0p90"] for row in primary_rows
    )
    all_primary_pass = all_identified and not any_identified_fail
    verdict = "negative" if any_identified_fail else (
        "supports" if all_primary_pass else "inconclusive"
    )
    decision = {
        "experiment_id": "S04-E013", "run_id": args.run_id,
        "execution_status": "succeeded", "retrieval_status": "verified",
        "scientific_verdict": verdict, "runtime_sensitivity_gate": "PASS",
        "primary_gate": "FAIL" if any_identified_fail else (
            "PASS" if all_primary_pass else "UNIDENTIFIED"
        ),
        "primary_clause_count": len(primary_rows),
        "primary_pass_count": sum(bool(row["pass_upper975_lt_0p90"]) for row in primary_rows),
        "allowed_conclusion": (
            "the specified rank-20 POD bases achieve the frozen practical oracle reduction and support a separate offline coefficient-prediction experiment"
            if verdict == "supports" else (
                "the specified centered rank-20 POD construction does not achieve the frozen practical oracle reduction in every fold and channel"
                if verdict == "negative" else
                "the frozen primary result is unidentified; no route decision is authorised"
            )
        ),
        "blocked_conclusions": ["all Delta-network failure", "neural corrector success", "online PIDL coupling", "FEM physical truth", "real-road validity"],
        "runtime": {"python": sys.version, "numpy": np.__version__, "platform": platform.platform()},
    }
    (out / "decision.json").write_text(json.dumps(decision, indent=2) + "\n")
    (out / "decision.md").write_text(
        f"# {args.run_id} decision\n\nVerdict: **{verdict}**\n\n"
        f"Runtime-sensitivity spot gate: PASS. Primary rank-20 clauses: "
        f"{decision['primary_pass_count']}/{decision['primary_clause_count']} PASS.\n\n"
        f"Allowed: {decision['allowed_conclusion']}.\n\n"
        "Blocked: all-Delta-network failure, neural success, online coupling, FEM physical truth, and real-road validity.\n"
    )
    (out / "README_analysis.md").write_text(
        "# S04-E013 analysis\n\nQuestion: do specified two-Umax rank-20 residual bases reduce complete held-out-Umax residual RMSE by at least 10% under the frozen metric?\n\n"
        "Read `runtime_sensitivity.csv`, then `pod_primary_summary.csv`, then the residual/support diagnostics. "
        "The POD coefficients use held-out residuals and are an oracle compressibility ceiling, not a predictor.\n\n"
        f"Verdict: **{verdict}**. See `decision.md`.\n\n"
        "Allowed conclusion is limited to the frozen specified-basis oracle-reduction claim. No training or online coupling occurred.\n"
    )
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
