#!/usr/bin/env python3
"""Post-hoc augmentation-sensitivity audit for frozen S03-E002 predictions.

This script never trains or performs model inference.  It joins the immutable
S03-E002 test outputs to the released CrackMNIST augmentation metadata and
estimates within-lineage associations across the eight released views.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import h5py
import numpy as np


EXPERIMENT_ID = "S03-E003"
PROTOCOL_REVISION = "v2"
EXPECTED_DATA_MD5 = "26bb0aa814f2e3ed467879844222c46c"
EXPECTED_PREDICTIONS_SHA256 = "e1371987d06c2e7e215dd8561947d0589fdfbc85d50657f3220d31186c939e58"
EXPECTED_LINEAGES = 743
VIEWS_PER_LINEAGE = 8
BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_SEED = 20261008
SEVERITY_SCALES = np.asarray([10.0, 20.0, 10.0], dtype=np.float64)
SUPPORT_BOUNDS = np.asarray([[0.0, 10.0], [-20.0, 20.0], [-10.0, 10.0], [0.0, 1.0]])
SUPPORT_TOLERANCE = 1.0e-3
LOADER_COLUMN_ORDER = ("shift_x_mm", "shift_y_mm", "rotation_deg", "vertical_flip")
SOURCE_SEMANTICS_STATUS = "loader_order_confirmed; nominal_support_conflict"
LOADER_SOURCE = "dlr-wf/crackmnist tags 2.0.0 and 2.0.1, crackmnist/dataset.py:get_augmentations"
PAPER_NOMINAL_RANGES = {
    "shift_x_mm": "up to 10",
    "shift_y_mm": "-10 to 10",
    "rotation_deg": "-10 to 10",
    "vertical_flip": "boolean, 50% chance",
}
TARGET_NAMES = ("KI", "KII", "T")


def file_hash(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def payload_is_finite(value: Any) -> bool:
    if isinstance(value, dict):
        return all(payload_is_finite(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(payload_is_finite(item) for item in value)
    if isinstance(value, (float, np.floating)):
        return bool(np.isfinite(value))
    if isinstance(value, np.ndarray) and np.issubdtype(value.dtype, np.number):
        return bool(np.isfinite(value).all())
    return True


def git_value(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def augmentation_severity(augmentations: np.ndarray) -> np.ndarray:
    """Continuous amplitude excluding the binary vertical-flip flag."""
    augmentations = np.asarray(augmentations, dtype=np.float64)
    if augmentations.ndim != 2 or augmentations.shape[1] != 4:
        raise ValueError("augmentations must have shape (n, 4)")
    normalized = augmentations[:, :3] / SEVERITY_SCALES[None, :]
    return np.sqrt(np.mean(normalized**2, axis=1))


def _cluster_contributions(
    outcome: np.ndarray,
    severity: np.ndarray,
    flip: np.ndarray,
    lineage_ids: np.ndarray,
    mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if mask is None:
        mask = np.ones(len(outcome), dtype=bool)
    mask = np.asarray(mask, dtype=bool)
    cluster_a: list[np.ndarray] = []
    cluster_b: list[np.ndarray] = []
    kept: list[int] = []
    centered_x: list[np.ndarray] = []
    centered_y: list[np.ndarray] = []
    for lineage in np.unique(lineage_ids[mask]):
        idx = np.flatnonzero(mask & (lineage_ids == lineage))
        if len(idx) < 2:
            continue
        x = np.column_stack([severity[idx], flip[idx]]).astype(np.float64)
        y = outcome[idx].astype(np.float64)
        x = x - x.mean(axis=0, keepdims=True)
        y = y - y.mean()
        cluster_a.append(x.T @ x)
        cluster_b.append(x.T @ y)
        kept.append(int(lineage))
        centered_x.append(x)
        centered_y.append(y)
    if not cluster_a:
        raise ValueError("no evaluable lineages")
    return (
        np.stack(cluster_a),
        np.stack(cluster_b),
        np.asarray(kept, dtype=np.int64),
        np.concatenate(centered_x, axis=0),
        np.concatenate(centered_y, axis=0),
    )


def fixed_effect_association(
    outcome: np.ndarray,
    severity: np.ndarray,
    flip: np.ndarray,
    lineage_ids: np.ndarray,
    *,
    mask: np.ndarray | None = None,
    bootstrap_draws: int = BOOTSTRAP_DRAWS,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    a, b, kept, centered_x, centered_y = _cluster_contributions(
        outcome, severity, flip, lineage_ids, mask
    )
    rank = int(np.linalg.matrix_rank(centered_x))
    if rank != 2:
        raise ValueError(f"fixed-effect design rank is {rank}, expected 2")
    beta = np.linalg.solve(a.sum(axis=0), b.sum(axis=0))
    rng = np.random.default_rng(seed)
    boot = np.empty((bootstrap_draws, 2), dtype=np.float64)
    for draw in range(bootstrap_draws):
        sampled = rng.integers(0, len(kept), size=len(kept))
        boot[draw] = np.linalg.solve(a[sampled].sum(axis=0), b[sampled].sum(axis=0))
    if not np.isfinite(boot).all():
        raise ValueError("non-finite cluster-bootstrap coefficient")
    # Explicit two-term evaluation avoids a reproducible macOS/NumPy matmul
    # RuntimeWarning while preserving the exact rank-two linear predictor.
    fitted = centered_x[:, 0] * beta[0] + centered_x[:, 1] * beta[1]
    residual = centered_y - fitted
    result = {
        "beta_severity": float(beta[0]),
        "beta_severity_ci95": np.quantile(boot[:, 0], [0.025, 0.975]).tolist(),
        "beta_vertical_flip": float(beta[1]),
        "beta_vertical_flip_ci95": np.quantile(boot[:, 1], [0.025, 0.975]).tolist(),
        "bootstrap_draws": int(bootstrap_draws),
        "bootstrap_seed": int(seed),
        "design_rank": rank,
        "n_lineages": int(len(kept)),
        "n_rows": int(len(centered_y)),
        "centered_r2": float(1.0 - np.sum(residual**2) / np.sum(centered_y**2))
        if np.sum(centered_y**2) > 0
        else 0.0,
    }
    if not payload_is_finite(result):
        raise ValueError("non-finite fixed-effect result")
    return result


def lineage_contrasts(
    outcome: np.ndarray,
    severity: np.ndarray,
    lineage_ids: np.ndarray,
    row_idx: np.ndarray,
    tip_visible: np.ndarray,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lineage in np.unique(lineage_ids):
        idx = np.flatnonzero(lineage_ids == lineage)
        low = idx[int(np.argmin(severity[idx]))]
        high = idx[int(np.argmax(severity[idx]))]
        rows.append(
            {
                "lineage_id": int(lineage),
                "low_row_idx": int(row_idx[low]),
                "high_row_idx": int(row_idx[high]),
                "low_observed_severity": float(severity[low]),
                "high_observed_severity": float(severity[high]),
                "low_reconstruction_mse_z": float(outcome[low]),
                "high_reconstruction_mse_z": float(outcome[high]),
                "high_minus_low_reconstruction_mse_z": float(outcome[high] - outcome[low]),
                "reconstruction_mse_z_range": float(np.ptp(outcome[idx])),
                "visible_tip_views": int(tip_visible[idx].sum()),
            }
        )
    return rows


def bootstrap_median(values: np.ndarray, draws: int, seed: int) -> tuple[float, list[float]]:
    values = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(seed)
    sampled = rng.integers(0, len(values), size=(draws, len(values)))
    boot = np.median(values[sampled], axis=1)
    return float(np.median(values)), np.quantile(boot, [0.025, 0.975]).tolist()


def binned_centered_trend(
    outcome: np.ndarray,
    severity: np.ndarray,
    lineage_ids: np.ndarray,
    *,
    draws: int,
    seed: int,
) -> dict[str, Any]:
    centered = np.empty_like(outcome, dtype=np.float64)
    for lineage in np.unique(lineage_ids):
        idx = lineage_ids == lineage
        centered[idx] = outcome[idx] - outcome[idx].mean()
    edges = np.quantile(severity, [0.0, 0.25, 0.5, 0.75, 1.0])
    if len(np.unique(edges)) != 5:
        raise ValueError("severity quantile edges are not unique")
    bins = np.digitize(severity, edges[1:-1], right=True)
    lineages = np.unique(lineage_ids)
    per_lineage = np.full((len(lineages), 4), np.nan, dtype=np.float64)
    for i, lineage in enumerate(lineages):
        for bin_id in range(4):
            idx = (lineage_ids == lineage) & (bins == bin_id)
            if idx.any():
                per_lineage[i, bin_id] = centered[idx].mean()
    means = np.nanmean(per_lineage, axis=0)
    rng = np.random.default_rng(seed)
    boot = np.empty((draws, 4), dtype=np.float64)
    for draw in range(draws):
        sampled = rng.integers(0, len(lineages), size=len(lineages))
        boot[draw] = np.nanmean(per_lineage[sampled], axis=0)
    return {
        "edges": edges.tolist(),
        "centers": ((edges[:-1] + edges[1:]) / 2.0).tolist(),
        "mean_centered_error": means.tolist(),
        "ci95_low": np.quantile(boot, 0.025, axis=0).tolist(),
        "ci95_high": np.quantile(boot, 0.975, axis=0).tolist(),
        "lineages_per_bin": np.sum(np.isfinite(per_lineage), axis=0).astype(int).tolist(),
    }


def validate_and_join(data_path: Path, predictions_path: Path) -> dict[str, Any]:
    data_md5 = file_hash(data_path, "md5")
    predictions_sha256 = file_hash(predictions_path, "sha256")
    if data_md5 != EXPECTED_DATA_MD5:
        raise ValueError(f"data MD5 mismatch: {data_md5}")
    if predictions_sha256 != EXPECTED_PREDICTIONS_SHA256:
        raise ValueError(f"prediction SHA256 mismatch: {predictions_sha256}")

    with np.load(predictions_path) as loaded:
        required = {
            "row_idx", "lineage_ids", "reconstruction_mse_z_row",
            "reconstruction_mae_row", "tip_error_row_px", "tip_visible",
            "sif_prediction", "sif_true",
        }
        missing = sorted(required - set(loaded.files))
        if missing:
            raise ValueError(f"missing prediction arrays: {missing}")
        predictions = {name: loaded[name].copy() for name in required}

    support_by_split: dict[str, dict[str, list[float]]] = {}
    all_augmentations: list[np.ndarray] = []
    with h5py.File(data_path, "r") as handle:
        train_n = int(handle["train_images"].shape[0])
        val_n = int(handle["val_images"].shape[0])
        test_n = int(handle["test_images"].shape[0])
        test_offset = train_n + val_n
        test_augs = handle["test_augs"][...].astype(np.float64)
        test_sifs = handle["test_SIFs"][...].astype(np.float64)
        for split in ("train", "val", "test"):
            split_augs = handle[f"{split}_augs"][...].astype(np.float64)
            if split_augs.ndim != 2 or split_augs.shape[1] != 4:
                raise ValueError(f"{split}_augs does not have four columns")
            if not np.isfinite(split_augs).all():
                raise ValueError(f"non-finite {split}_augs metadata")
            for column in range(4):
                low, high = SUPPORT_BOUNDS[column]
                if split_augs[:, column].min() < low - SUPPORT_TOLERANCE or split_augs[:, column].max() > high + SUPPORT_TOLERANCE:
                    raise ValueError(f"{split}_augs column {column} exceeds frozen v2 support")
            if not np.isin(split_augs[:, 3], [0.0, 1.0]).all():
                raise ValueError(f"{split}_augs vertical_flip is not binary")
            support_by_split[split] = {
                name: [float(split_augs[:, i].min()), float(split_augs[:, i].max())]
                for i, name in enumerate(LOADER_COLUMN_ORDER)
            }
            all_augmentations.append(split_augs)
    stacked_augmentations = np.concatenate(all_augmentations, axis=0)
    global_support = {
        name: [float(stacked_augmentations[:, i].min()), float(stacked_augmentations[:, i].max())]
        for i, name in enumerate(LOADER_COLUMN_ORDER)
    }

    n = len(predictions["row_idx"])
    if any(len(value) != n for value in predictions.values()):
        raise ValueError("prediction arrays have inconsistent row counts")
    row_idx = predictions["row_idx"].astype(np.int64)
    if len(np.unique(row_idx)) != n:
        raise ValueError("row_idx is not unique")
    local_idx = row_idx - test_offset
    if n != test_n or not np.array_equal(np.sort(local_idx), np.arange(test_n)):
        raise ValueError("row_idx does not map exactly once to the released test split")
    augmentations = test_augs[local_idx]
    joined_sifs = test_sifs[local_idx]
    if not np.allclose(joined_sifs, predictions["sif_true"], rtol=0, atol=1e-6):
        raise ValueError("joined SIF truth does not match frozen predictions")
    if not np.isfinite(augmentations).all():
        raise ValueError("non-finite augmentation metadata")
    flip = augmentations[:, 3]
    if not np.isin(flip, [0.0, 1.0]).all():
        raise ValueError("vertical_flip is not binary")
    lineages, counts = np.unique(predictions["lineage_ids"], return_counts=True)
    if len(lineages) != EXPECTED_LINEAGES or not np.all(counts == VIEWS_PER_LINEAGE):
        raise ValueError("expected 743 lineages with exactly eight rows each")
    for lineage in lineages:
        truth = predictions["sif_true"][predictions["lineage_ids"] == lineage]
        if not np.allclose(truth, truth[0], rtol=0, atol=1e-6):
            raise ValueError(f"SIF truth varies within lineage {lineage}")
    numeric = [value for value in predictions.values() if np.issubdtype(value.dtype, np.number)]
    if not all(np.isfinite(value).all() for value in numeric):
        raise ValueError("non-finite frozen prediction array")
    return {
        **predictions,
        "augmentations": augmentations,
        "data_md5": data_md5,
        "predictions_sha256": predictions_sha256,
        "test_offset": test_offset,
        "test_rows": test_n,
        "support_by_split": support_by_split,
        "global_support": global_support,
    }


def render_figure(output: Path, trend: dict[str, Any], contrasts: np.ndarray, contrast_ci: list[float]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    centers = np.asarray(trend["centers"])
    means = np.asarray(trend["mean_centered_error"])
    low = np.asarray(trend["ci95_low"])
    high = np.asarray(trend["ci95_high"])
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.1), constrained_layout=True)
    axes[0].errorbar(centers, means, yerr=np.vstack([means - low, high - means]), fmt="o-", capsize=3)
    axes[0].axhline(0.0, color="0.45", linewidth=0.8)
    axes[0].set(xlabel="observed continuous augmentation amplitude", ylabel="lineage-centered reconstruction MSE", title="(a) Within-lineage trend")
    axes[0].grid(color="0.9", linewidth=0.7)
    axes[1].hist(contrasts, bins=32, color="#4477AA", alpha=0.85)
    axes[1].axvline(0.0, color="0.25", linewidth=0.9)
    axes[1].axvspan(contrast_ci[0], contrast_ci[1], color="#EE6677", alpha=0.18, label="median 95% lineage bootstrap CI")
    axes[1].set(xlabel="highest minus lowest observed-view MSE", ylabel="physical lineages", title="(b) Observed-extrema contrast")
    axes[1].legend(frameon=False, fontsize=8)
    axes[1].grid(axis="y", color="0.9", linewidth=0.7)
    output.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf"):
        fig.savefig(output / f"augmentation_sensitivity.{suffix}", dpi=220 if suffix == "png" else None, bbox_inches="tight")
    plt.close(fig)


def write_lineage_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    joined = validate_and_join(args.data.resolve(), args.predictions.resolve())
    lineage_ids = joined["lineage_ids"].astype(np.int64)
    row_idx = joined["row_idx"].astype(np.int64)
    augmentations = joined["augmentations"]
    severity = augmentation_severity(augmentations)
    flip = augmentations[:, 3]
    lineages = np.unique(lineage_ids)
    variable = np.asarray([np.ptp(severity[lineage_ids == value]) > 1e-12 for value in lineages])
    variation_fraction = float(variable.mean())
    if variation_fraction < 0.5:
        raise ValueError("fewer than 50% of lineages have continuous augmentation variation")

    primary = fixed_effect_association(
        joined["reconstruction_mse_z_row"], severity, flip, lineage_ids
    )
    primary["outcome"] = "standardized_reconstruction_mse"
    primary["estimand"] = "joint within-lineage association across released augmented views"
    primary["severity_definition"] = "sqrt(mean((col0/10)^2,(col1/20)^2,(col2/10)^2)); empirical frozen-release support scaling"
    primary["independent_units"] = EXPECTED_LINEAGES
    primary["repeated_rows"] = int(len(row_idx))
    primary["lineages_with_nonzero_severity_variation_fraction"] = variation_fraction

    contrast_rows = lineage_contrasts(
        joined["reconstruction_mse_z_row"], severity, lineage_ids, row_idx, joined["tip_visible"]
    )
    contrast_values = np.asarray([row["high_minus_low_reconstruction_mse_z"] for row in contrast_rows])
    contrast_median, contrast_ci = bootstrap_median(contrast_values, BOOTSTRAP_DRAWS, BOOTSTRAP_SEED + 1)
    primary["lowest_vs_highest_observed_severity_contrast"] = {
        "median": contrast_median,
        "median_ci95": contrast_ci,
        "label": "secondary; not an identity baseline",
    }

    secondary_outcomes = {
        "reconstruction_mae_original_units": (joined["reconstruction_mae_row"], np.ones(len(row_idx), dtype=bool)),
        "abs_error_KI": (np.abs(joined["sif_prediction"][:, 0] - joined["sif_true"][:, 0]), np.ones(len(row_idx), dtype=bool)),
        "abs_error_KII": (np.abs(joined["sif_prediction"][:, 1] - joined["sif_true"][:, 1]), np.ones(len(row_idx), dtype=bool)),
        "abs_error_T": (np.abs(joined["sif_prediction"][:, 2] - joined["sif_true"][:, 2]), np.ones(len(row_idx), dtype=bool)),
        "tip_visibility": (joined["tip_visible"].astype(np.float64), np.ones(len(row_idx), dtype=bool)),
        "tip_error_px_conditional_on_visible": (joined["tip_error_row_px"], joined["tip_visible"].astype(bool)),
    }
    secondary: dict[str, Any] = {}
    for offset, (name, (values, mask)) in enumerate(secondary_outcomes.items(), start=10):
        result = fixed_effect_association(
            values, severity, flip, lineage_ids, mask=mask, seed=BOOTSTRAP_SEED + offset
        )
        result["lineage_coverage_fraction"] = result["n_lineages"] / EXPECTED_LINEAGES
        secondary[name] = result
    secondary["tip_visibility_note"] = "Tip error is conditional on released tip_visible; invisibility is analysed separately and is never imputed as zero error."

    trend = binned_centered_trend(
        joined["reconstruction_mse_z_row"], severity, lineage_ids,
        draws=BOOTSTRAP_DRAWS, seed=BOOTSTRAP_SEED + 2,
    )
    secondary["four_bin_centered_reconstruction_trend"] = trend
    if not payload_is_finite(secondary):
        raise ValueError("non-finite secondary diagnostic")

    audit_checks = {
        "data_md5_matches": joined["data_md5"] == EXPECTED_DATA_MD5,
        "predictions_sha256_matches": joined["predictions_sha256"] == EXPECTED_PREDICTIONS_SHA256,
        "test_row_join_is_one_to_one": True,
        "lineage_count_is_743": len(lineages) == EXPECTED_LINEAGES,
        "all_lineages_have_eight_views": all(np.sum(lineage_ids == value) == VIEWS_PER_LINEAGE for value in lineages),
        "augmentation_columns_confirmed": True,
        "full_release_support_within_v2_bounds": True,
        "nominal_support_conflict_acknowledged": True,
        "vertical_flip_binary": bool(np.isin(flip, [0.0, 1.0]).all()),
        "primary_design_rank_two": primary["design_rank"] == 2,
        "at_least_90pct_lineages_vary": variation_fraction >= 0.9,
        "whole_lineage_bootstrap": True,
        "all_primary_outputs_finite": bool(np.isfinite([primary["beta_severity"], primary["beta_vertical_flip"], *primary["beta_severity_ci95"], *primary["beta_vertical_flip_ci95"], contrast_median, *contrast_ci]).all()),
        "all_secondary_outputs_finite": payload_is_finite(secondary),
    }
    gate_pass = all(audit_checks.values())
    if not gate_pass:
        raise ValueError(f"strict audit gate failed: {[key for key, value in audit_checks.items() if not value]}")
    secondary_coverages = [value["lineage_coverage_fraction"] for value in secondary.values() if isinstance(value, dict) and "lineage_coverage_fraction" in value]
    decision = "MIXED_DIAGNOSTIC" if any(value < 0.9 for value in secondary_coverages) else "PASS_AUGMENTATION_AUDIT_MVP"

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    figures = output / "figures"
    render_figure(figures, trend, contrast_values, contrast_ci)
    write_lineage_csv(output / "lineage_contrasts.csv", contrast_rows)
    write_json(output / "primary_estimand.json", primary)
    write_json(output / "secondary_metrics.json", secondary)
    audit = {
        "experiment_id": EXPERIMENT_ID,
        "protocol_revision": PROTOCOL_REVISION,
        "decision": decision,
        "gate_pass": gate_pass,
        "checks": audit_checks,
        "data_path": str(args.data.resolve()),
        "data_md5": joined["data_md5"],
        "predictions_path": str(args.predictions.resolve()),
        "predictions_sha256": joined["predictions_sha256"],
        "n_rows": int(len(row_idx)),
        "n_physical_lineages": int(len(lineages)),
        "views_per_lineage": VIEWS_PER_LINEAGE,
        "independent_unit": "physical lineage",
        "augmentation_column_order": list(LOADER_COLUMN_ORDER),
        "augmentation_ranges": {
            name: [float(augmentations[:, i].min()), float(augmentations[:, i].max())]
            for i, name in enumerate(LOADER_COLUMN_ORDER)
        },
        "source_semantics_status": SOURCE_SEMANTICS_STATUS,
        "identity_baseline_available": False,
        "chronology_available": False,
    }
    write_json(output / "augmentation_audit.json", audit)
    write_json(output / "augmentation_support_audit.json", {
        "experiment_id": EXPERIMENT_ID,
        "protocol_revision": PROTOCOL_REVISION,
        "loader_declared_column_order": list(LOADER_COLUMN_ORDER),
        "loader_source": LOADER_SOURCE,
        "paper_nominal_ranges": PAPER_NOMINAL_RANGES,
        "nominal_support_conflict": True,
        "source_semantics_status": SOURCE_SEMANTICS_STATUS,
        "observed_bounds_by_split": joined["support_by_split"],
        "observed_global_bounds": joined["global_support"],
        "v2_empirical_scales": SEVERITY_SCALES.tolist(),
        "v2_allowed_bounds": {
            name: SUPPORT_BOUNDS[i].tolist() for i, name in enumerate(LOADER_COLUMN_ORDER)
        },
        "bound_tolerance": SUPPORT_TOLERANCE,
        "interpretation_block": "Empirical scales describe this frozen release and are not asserted to be the nominal augmentation design reported by the paper.",
    })
    write_json(output / "analysis_receipt.json", {
        "experiment_id": EXPERIMENT_ID,
        "protocol_revision": PROTOCOL_REVISION,
        "execution": "deterministic local post-hoc analysis; no training or inference",
        "python": sys.version,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_dirty": git_value("status", "--porcelain"),
        "command": " ".join(sys.argv),
    })

    readme = f"""# Analysis: S03-E003 augmentation sensitivity

## Question and evidence

This figure set audits the frozen S03-E002-R001 test predictions against the
released augmentation metadata. The independent unit is the physical lineage
(`n={len(lineages)}`); the {len(row_idx)} rows are repeated views.

The official loader defines the column order, but the frozen HDF5 second-column
support conflicts with the paper's nominal range. Protocol v2 therefore uses
empirical frozen-release scales `[10,20,10]`; see
`augmentation_support_audit.json`.

## Reading order

1. Panel (a) shows binned lineage-centered reconstruction MSE across observed
   continuous augmentation amplitude. Error bars are 95% whole-lineage
   bootstrap intervals.
2. Panel (b) shows, for every lineage, the reconstruction-MSE difference
   between its highest and lowest *observed* continuous-severity views.

## Allowed conclusion

The fixed tokenizer has measurable within-lineage associations across the
released augmented views. Exact coefficients and intervals are in
`primary_estimand.json`.

## Blocked conclusion

There is no identity/unaugmented baseline. The figure does not establish causal
augmentation effects, invariance, chronology, future/RUL prediction, dynamic or
phase-field sufficiency, road transfer, the nominal cause of the support
conflict, or reversal of S03-E001.

## Storyline impact

This is a diagnostic observation-level audit. It does not promote S03-E002's
tooling-only tokenizer to scientific sufficiency.
"""
    (output / "README_analysis.md").write_text(readme, encoding="utf-8")
    decision_note = f"""# S03-E003 decision

**Audit decision:** `{decision}`  
**Primary claim class:** observation/tooling diagnostic  
**Independent units:** {len(lineages)} physical lineages; {len(row_idx)} repeated views

All frozen input, join, lineage, rank, variation, finiteness and whole-lineage
bootstrap gates passed. The primary coefficients describe association across
the released augmented views only:

- continuous augmentation amplitude: `{primary['beta_severity']:.8g}`
  (95% lineage-bootstrap CI `{primary['beta_severity_ci95'][0]:.8g}` to
  `{primary['beta_severity_ci95'][1]:.8g}`);
- vertical flip: `{primary['beta_vertical_flip']:.8g}`
  (95% lineage-bootstrap CI `{primary['beta_vertical_flip_ci95'][0]:.8g}` to
  `{primary['beta_vertical_flip_ci95'][1]:.8g}`).

The lowest-versus-highest *observed* severity contrast has median
`{contrast_median:.8g}` (95% lineage-bootstrap CI `{contrast_ci[0]:.8g}` to
`{contrast_ci[1]:.8g}`). It is not an unaugmented-versus-augmented comparison.

This result does not establish causal augmentation effects, identity
degradation, invariance, scientific representation sufficiency, chronology,
future/RUL prediction, dynamic or phase-field sufficiency, road transfer, or
reversal of S03-E001. The `[10,20,10]` scales are empirical supports of this
frozen release, not a claim that the paper's nominal augmentation description
is wrong. No new training was performed or selected by this audit.
"""
    (output / "decision.md").write_text(decision_note, encoding="utf-8")
    print(json.dumps({"decision": decision, "output": str(output), "primary": primary}, indent=2))


if __name__ == "__main__":
    main()
