#!/usr/bin/env python3
# ruff: noqa: E402,E501
"""Run the read-only S09-E016 factorisation readiness audit."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e016_factorisation import (  # noqa: E402
    CAPACITY_EPS,
    EXPECTED_CYCLES,
    FIELD_VALIDITY_TOL,
    FRACTION_EPS,
    ROUNDTRIP_ATOL,
    ROUNDTRIP_RTOL,
    SUPPORT_THRESHOLD,
    ZERO_AMPLITUDE_TOL,
    factorise_increment,
    numerical_readiness,
    pair_score,
    shape_metrics,
    support_contrast,
)


RUN_ID = "S09-E016-R001-factorisation-readiness"
SOURCE_FIELD_KEY = "B25_step0__predicted_peak"
A25_ARM = "A25_exact_e009_replay"
A25_UPDATE = 500
SELECTED_CYCLES = (1, 69, 73)
EXPECTED_FIELDS_SHA256 = (
    "e95ddb5ac14f93f76ddbfb05c83bfebf38c406d380c957bd7812ddacccbc6fe4"
)
EXPECTED_A25_TABLE_SHA256 = (
    "2f38ead95c9596418f42a7d8aaaa2050fac938040ebd3804209f196c1ebc247e"
)
ANALYSIS_FILES = (
    "source/s09_e016_factorisation.py",
    "scripts/analyse_s09_e016_factorisation.py",
    "docs/research/S09/S09-E016/experiment.md",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _analysis_files_clean() -> bool:
    dirty = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *ANALYSIS_FILES], cwd=ROOT
    )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", *ANALYSIS_FILES],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return dirty.returncode == 0 and not untracked.stdout.strip()


def _load_a25(path: Path) -> dict[int, dict[str, float]]:
    with path.open(newline="") as stream:
        rows = [
            row
            for row in csv.DictReader(stream)
            if row["arm"] == A25_ARM and int(row["update"]) == A25_UPDATE
        ]
    _require(len(rows) == len(EXPECTED_CYCLES), "A25 update-500 row count drift")
    values: dict[int, dict[str, float]] = {}
    for row in rows:
        cycle = int(row["cycle"])
        _require(cycle not in values, "duplicate A25 cycle")
        values[cycle] = {
            "weighted_mean_increment": float(
                row["predicted_damage_increment_abs_mean"]
            ),
            "fem_weighted_mean_increment": float(row["true_damage_increment_abs_mean"]),
        }
    _require(
        tuple(sorted(values)) == tuple(sorted(EXPECTED_CYCLES)),
        "A25 cycle identity drift",
    )
    return values


def _json_dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def _finite_ratio(numerator: float, denominator: float) -> float | None:
    if denominator <= 0.0:
        return None
    value = numerator / denominator
    return value if math.isfinite(value) else None


def _finite_log_ratio(numerator: float, denominator: float) -> float | None:
    if numerator <= 0.0 or denominator <= 0.0:
        return None
    value = math.log(numerator / denominator)
    return value if math.isfinite(value) else None


def _optional_pair_score(values: dict[int, float | None]) -> dict[str, Any]:
    required = set(EXPECTED_CYCLES)
    missing = sorted(cycle for cycle in required if values.get(cycle) is None)
    if missing:
        return {
            "available": False,
            "reason": "UNDEFINED_SUPPORT_CONTRAST_FOR_ZERO_OR_FULL_SUPPORT_FEM_EVENT",
            "missing_cycles": missing,
        }
    score = pair_score({cycle: float(values[cycle]) for cycle in required})
    return {"available": True, **score}


def _metric_text(value: Any) -> str:
    return "NA" if value is None else f"{float(value):.3f}"


def _plot_summary(
    path: Path,
    cycles: np.ndarray,
    xy: np.ndarray,
    fem: list,
    b25: list,
    a25: dict[int, dict[str, float]],
    rows: list[dict[str, Any]],
) -> None:
    figure = plt.figure(figsize=(14, 13), constrained_layout=True)
    grid = figure.add_gridspec(5, 3, height_ratios=[1.05, 1.05, 1, 1, 1])
    ax_bridge = figure.add_subplot(grid[0, :])
    ax_hazard = figure.add_subplot(grid[1, :])

    bridge = {
        "FEM": [row["fem_weighted_mean_absolute_increment"] for row in rows],
        "A25": [a25[int(c)]["weighted_mean_increment"] for c in cycles],
        "B25": [row["b25_weighted_mean_absolute_increment"] for row in rows],
    }
    for label, values in bridge.items():
        ax_bridge.plot(cycles, values, marker="o", linewidth=1.6, label=label)
    ax_bridge.set_yscale("log")
    ax_bridge.set_ylabel(r"weighted mean absolute $\Delta d$")
    ax_bridge.set_title("Same-unit amplitude bridge (A25 is scalar-only evidence)")
    ax_bridge.grid(alpha=0.25)
    ax_bridge.legend(ncol=3)

    ax_hazard.plot(
        cycles, [item.amplitude for item in fem], marker="o", label="FEM hazard A"
    )
    ax_hazard.plot(
        cycles, [item.amplitude for item in b25], marker="o", label="B25 hazard A"
    )
    ax_hazard.set_yscale("log")
    ax_hazard.set_xlabel("cycle")
    ax_hazard.set_ylabel("weighted hazard amplitude A")
    ax_hazard.set_title("Exact factorised amplitude (raw A25 node field unavailable)")
    ax_hazard.grid(alpha=0.25)
    ax_hazard.legend(ncol=2)

    triangulation = mtri.Triangulation(xy[:, 0], xy[:, 1])
    row_by_cycle = {int(row["cycle"]): row for row in rows}
    cycle_to_index = {int(value): index for index, value in enumerate(cycles)}
    for plot_row, cycle in enumerate(SELECTED_CYCLES, start=2):
        index = cycle_to_index[cycle]
        shapes = (fem[index].shape, b25[index].shape)
        maxima = [float(value.max(initial=0.0)) for value in shapes]
        for column, (label, value, maximum) in enumerate(
            zip(("FEM", "B25"), shapes, maxima)
        ):
            ax = figure.add_subplot(grid[plot_row, column])
            display = value / maximum if maximum > 0.0 else value
            image = ax.tripcolor(
                triangulation,
                display,
                shading="gouraud",
                vmin=0.0,
                vmax=1.0,
                cmap="viridis",
            )
            ax.set_aspect("equal")
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title(
                f"cycle {cycle} | {label} normalised shape\n(displayed as S/max(S))"
            )
            figure.colorbar(image, ax=ax, fraction=0.046, pad=0.02)
        metric = row_by_cycle[cycle]
        ax_text = figure.add_subplot(grid[plot_row, 2])
        ax_text.axis("off")
        ax_text.text(
            0.03,
            0.95,
            "\n".join(
                [
                    f"cycle {cycle}",
                    f"half-L1 = {_metric_text(metric['b25_shape_half_l1'])}",
                    f"cosine = {_metric_text(metric['b25_shape_cosine'])}",
                    f"support capture = {_metric_text(metric['b25_target_support_capture'])}",
                    f"background spill = {_metric_text(metric['b25_background_spill'])}",
                    f"centroid offset = {_metric_text(metric['b25_centroid_offset'])}",
                    "A25 shape: unavailable",
                ]
            ),
            va="top",
            fontsize=11,
        )

    figure.suptitle(
        f"{RUN_ID} | exposed synthetic development data | selected cycles fixed ex ante",
        fontsize=14,
    )
    figure.savefig(path, dpi=180)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fields", type=Path, required=True)
    parser.add_argument("--a25-table", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-commit")
    args = parser.parse_args()

    commit = _git_commit()
    if args.expected_commit is not None:
        _require(commit == args.expected_commit, "analysis commit identity mismatch")
    _require(_analysis_files_clean(), "analysis dependency is dirty")
    _require(
        args.fields.is_file() and args.a25_table.is_file(), "missing frozen source"
    )
    _require(
        _sha256(args.fields) == EXPECTED_FIELDS_SHA256, "field source identity drift"
    )
    _require(
        _sha256(args.a25_table) == EXPECTED_A25_TABLE_SHA256,
        "A25 scalar source identity drift",
    )
    _require(not args.output.exists(), "fresh output root required")
    args.output.mkdir(parents=True)

    with np.load(args.fields, allow_pickle=False) as archive:
        required = {
            "cycles",
            "xy",
            "nodal_weight",
            "d_pre",
            "target_peak",
            SOURCE_FIELD_KEY,
        }
        _require(required <= set(archive.files), "field archive schema drift")
        cycles = np.asarray(archive["cycles"], dtype=np.int64)
        xy = np.asarray(archive["xy"], dtype=np.float64)
        weights = np.asarray(archive["nodal_weight"], dtype=np.float64)
        d_pre = np.asarray(archive["d_pre"], dtype=np.float64)
        target = np.asarray(archive["target_peak"], dtype=np.float64)
        predicted = np.asarray(archive[SOURCE_FIELD_KEY], dtype=np.float64)

    _require(tuple(cycles.tolist()) == EXPECTED_CYCLES, "cycle order drift")
    _require(xy.shape == (weights.size, 2), "xy/weight shape drift")
    _require(
        d_pre.shape == target.shape == predicted.shape == (cycles.size, weights.size),
        "field shape drift",
    )
    _require(np.isfinite(xy).all(), "nonfinite coordinates")
    a25 = _load_a25(args.a25_table)

    fem = [factorise_increment(pre, peak, weights) for pre, peak in zip(d_pre, target)]
    b25 = [
        factorise_increment(pre, peak, weights) for pre, peak in zip(d_pre, predicted)
    ]
    readiness = numerical_readiness(fem, b25)
    positive_fem_amplitudes = [item.amplitude for item in fem if item.shape_valid]
    _require(positive_fem_amplitudes, "no positive FEM hazard amplitude")
    amplitude_scale = float(np.median(positive_fem_amplitudes))

    rows: list[dict[str, Any]] = []
    fem_hazard = {}
    b25_hazard = {}
    fem_bridge = {}
    a25_bridge = {}
    b25_bridge = {}
    fem_local: dict[int, float | None] = {}
    b25_local: dict[int, float | None] = {}
    normalised_weight = weights / weights.sum(dtype=np.float64)
    for index, cycle_raw in enumerate(cycles):
        cycle = int(cycle_raw)
        support = fem[index].increment > SUPPORT_THRESHOLD
        metrics = (
            shape_metrics(fem[index], b25[index], weights, xy, support)
            if fem[index].shape_valid and b25[index].shape_valid
            else None
        )
        support_has_both_classes = bool(np.any(support) and np.any(~support))
        if support_has_both_classes:
            fem_local[cycle] = support_contrast(
                fem[index].increment, fem[index].increment, weights
            )
            b25_local[cycle] = support_contrast(
                b25[index].increment, fem[index].increment, weights
            )
        else:
            fem_local[cycle] = None
            b25_local[cycle] = None
        fem_hazard[cycle] = fem[index].amplitude
        b25_hazard[cycle] = b25[index].amplitude
        fem_bridge[cycle] = float(
            np.dot(normalised_weight, np.abs(target[index] - d_pre[index]))
        )
        a25_bridge[cycle] = a25[cycle]["weighted_mean_increment"]
        b25_bridge[cycle] = float(
            np.dot(normalised_weight, np.abs(predicted[index] - d_pre[index]))
        )
        _require(
            abs(a25[cycle]["fem_weighted_mean_increment"] - fem_bridge[cycle])
            <= 1.0e-15,
            f"A25/FEM scalar alignment drift at cycle {cycle}",
        )
        rows.append(
            {
                "cycle": cycle,
                "fem_hazard_amplitude": fem[index].amplitude,
                "b25_hazard_amplitude": b25[index].amplitude,
                "b25_to_fem_hazard_ratio": _finite_ratio(
                    b25[index].amplitude, fem[index].amplitude
                ),
                "b25_hazard_log_ratio": _finite_log_ratio(
                    b25[index].amplitude, fem[index].amplitude
                ),
                "fem_log1p_scaled_hazard": math.log1p(
                    fem[index].amplitude / amplitude_scale
                ),
                "b25_log1p_scaled_hazard": math.log1p(
                    b25[index].amplitude / amplitude_scale
                ),
                "fem_shape_valid": fem[index].shape_valid,
                "b25_shape_valid": b25[index].shape_valid,
                "fem_positive_nodes": fem[index].positive_node_count,
                "b25_positive_nodes": b25[index].positive_node_count,
                "fem_weighted_mean_absolute_increment": fem_bridge[cycle],
                "a25_weighted_mean_absolute_increment": a25_bridge[cycle],
                "b25_weighted_mean_absolute_increment": b25_bridge[cycle],
                "fem_weighted_mean_positive_increment": fem[
                    index
                ].weighted_mean_increment,
                "b25_weighted_mean_positive_increment": b25[
                    index
                ].weighted_mean_increment,
                "a25_to_fem_bridge_ratio": _finite_ratio(
                    a25_bridge[cycle], fem_bridge[cycle]
                ),
                "b25_to_fem_bridge_ratio": _finite_ratio(
                    b25_bridge[cycle], fem_bridge[cycle]
                ),
                "a25_bridge_log_ratio": _finite_log_ratio(
                    a25_bridge[cycle], fem_bridge[cycle]
                ),
                "b25_bridge_log_ratio": _finite_log_ratio(
                    b25_bridge[cycle], fem_bridge[cycle]
                ),
                "fem_maximum_increment": fem[index].maximum_increment,
                "b25_maximum_increment": b25[index].maximum_increment,
                "fem_maximum_roundtrip_error": fem[index].maximum_roundtrip_error,
                "b25_maximum_roundtrip_error": b25[index].maximum_roundtrip_error,
                "fem_maximum_roundtrip_relative_error": fem[
                    index
                ].maximum_roundtrip_relative_error,
                "b25_maximum_roundtrip_relative_error": b25[
                    index
                ].maximum_roundtrip_relative_error,
                "fem_maximum_saturation_clipping_residual": fem[
                    index
                ].maximum_clipping_residual,
                "b25_maximum_saturation_clipping_residual": b25[
                    index
                ].maximum_clipping_residual,
                "fem_saturated_fraction_nodes": fem[index].saturated_fraction_count,
                "b25_saturated_fraction_nodes": b25[index].saturated_fraction_count,
                "b25_shape_na_reason": (
                    ""
                    if metrics is not None
                    else "FEM_OR_B25_ZERO_EVENT_SHAPE_UNDEFINED"
                ),
                "b25_shape_half_l1": (
                    metrics["weighted_half_l1"] if metrics is not None else None
                ),
                "b25_shape_cosine": (
                    metrics["weighted_cosine"] if metrics is not None else None
                ),
                "b25_target_support_capture": (
                    metrics["target_support_capture"] if metrics is not None else None
                ),
                "b25_background_spill": (
                    metrics["background_spill"] if metrics is not None else None
                ),
                "b25_centroid_offset": (
                    metrics["centroid_offset"] if metrics is not None else None
                ),
                "fem_support_contrast": fem_local[cycle],
                "b25_support_contrast": b25_local[cycle],
            }
        )

    csv_path = args.output / "factorisation_cycle_table.csv"
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    pair_scores = {
        "hazard_amplitude": {
            "FEM": pair_score(fem_hazard),
            "B25": pair_score(b25_hazard),
        },
        "weighted_mean_absolute_increment": {
            "FEM": pair_score(fem_bridge),
            "A25": pair_score(a25_bridge),
            "B25": pair_score(b25_bridge),
        },
        "support_contrast": {
            "FEM": _optional_pair_score(fem_local),
            "B25": _optional_pair_score(b25_local),
        },
    }

    arrays_path = args.output / "factorisation_arrays.npz"
    np.savez_compressed(
        arrays_path,
        cycles=cycles,
        fem_amplitude=np.asarray([item.amplitude for item in fem]),
        b25_amplitude=np.asarray([item.amplitude for item in b25]),
        fem_shape=np.stack([item.shape for item in fem]),
        b25_shape=np.stack([item.shape for item in b25]),
        fem_source_increment=np.stack([item.increment for item in fem]),
        b25_source_increment=np.stack([item.increment for item in b25]),
        fem_encoded_increment=np.stack([item.encoded_increment for item in fem]),
        b25_encoded_increment=np.stack([item.encoded_increment for item in b25]),
        fem_reconstructed_increment=np.stack(
            [item.reconstructed_increment for item in fem]
        ),
        b25_reconstructed_increment=np.stack(
            [item.reconstructed_increment for item in b25]
        ),
        fem_residual=np.stack([item.residual for item in fem]),
        b25_residual=np.stack([item.residual for item in b25]),
        fem_clipping_residual=np.stack([item.clipping_residual for item in fem]),
        b25_clipping_residual=np.stack([item.clipping_residual for item in b25]),
        fem_shape_valid=np.asarray([item.shape_valid for item in fem]),
        b25_shape_valid=np.asarray([item.shape_valid for item in b25]),
    )

    figure_path = args.output / "factorisation_readiness.png"
    _plot_summary(figure_path, cycles, xy, fem, b25, a25, rows)

    half_l1 = np.asarray(
        [
            row["b25_shape_half_l1"]
            for row in rows
            if row["b25_shape_half_l1"] is not None
        ]
    )
    b25_shape_summary = {
        "valid_cycle_count": int(half_l1.size),
        "minimum": float(half_l1.min()) if half_l1.size else None,
        "median": float(np.median(half_l1)) if half_l1.size else None,
        "maximum": float(half_l1.max()) if half_l1.size else None,
    }
    fem_pairwise = []
    norm_weights = normalised_weight
    fem_valid_indices = [index for index, item in enumerate(fem) if item.shape_valid]
    for left_offset, left in enumerate(fem_valid_indices):
        for right in fem_valid_indices[left_offset + 1 :]:
            fem_pairwise.append(
                0.5
                * float(
                    np.dot(norm_weights, np.abs(fem[left].shape - fem[right].shape))
                )
            )
    fem_pairwise_summary = {
        "valid_pair_count": len(fem_pairwise),
        "minimum": float(np.min(fem_pairwise)) if fem_pairwise else None,
        "median": float(np.median(fem_pairwise)) if fem_pairwise else None,
        "maximum": float(np.max(fem_pairwise)) if fem_pairwise else None,
    }
    route = (
        "SEPARATE_AMPLITUDE_AND_SPATIAL_HEADS_WITH_AMPLITUDE_ONLY_ABLATION"
        if readiness["ready"]
        else "REPAIR_NUMERICAL_REPRESENTATION_BEFORE_PILOT"
    )
    decision = {
        "run_id": RUN_ID,
        "analysis_commit": commit,
        "readiness": readiness,
        "coverage": {
            "C_F_fem_nonzero_target_cycles": readiness["fem_nonzero_cycles"],
            "C_B_b25_nonzero_baseline_cycles": readiness["b25_nonzero_cycles"],
            "C_J_joint_nonzero_comparison_cycles": readiness["joint_nonzero_cycles"],
        },
        "recommended_pilot_route": route,
        "route_basis": (
            "The user-authorised central intervention is explicit amplitude/shape separation, "
            "and E015 already identified both amplitude and localisation bottlenecks. The "
            "dual-head candidate therefore tests the binding representation hypothesis at "
            "decision scale; amplitude-only is retained as the strong ablation. This route "
            "does not use a post-hoc shape-distance threshold."
        ),
        "amplitude_scale_rule": "median positive FEM hazard amplitude on the exposed 16-cycle set",
        "amplitude_scale": amplitude_scale,
        "fem_pairwise_shape_half_l1": fem_pairwise_summary,
        "b25_shape_half_l1": b25_shape_summary,
        "pair_scores": pair_scores,
        "numerical_constants": {
            "capacity_eps": CAPACITY_EPS,
            "fraction_eps": FRACTION_EPS,
            "zero_amplitude_tol": ZERO_AMPLITUDE_TOL,
            "field_validity_tol": FIELD_VALIDITY_TOL,
            "roundtrip_atol": ROUNDTRIP_ATOL,
            "roundtrip_rtol": ROUNDTRIP_RTOL,
            "support_threshold": SUPPORT_THRESHOLD,
        },
        "claim_boundary": (
            "This exposed-set audit establishes numerical readiness of the representation only. "
            "It does not establish training success, holdout generalisation, rollout stability, "
            "damage stationarity, history complementarity, or physical-teacher truth."
        ),
    }
    _json_dump(args.output / "factorisation_decision.json", decision)

    decision_md = f"""# S09-E016 factorisation decision

Run: `{RUN_ID}`

Analysis commit: `{commit}`

Status: `{readiness['status']}`

## Decision

The capacity-aware hazard factorisation is numerically ready for an E017 pilot card when the validity record below passes. Zero events remain valid amplitude observations with undefined shape; FEM shape supervision is defined on `C_F`, and B25-vs-FEM shape diagnostics only on `C_J`. Numerical round-trip is checked against the encoded increment with `rtol={ROUNDTRIP_RTOL:.3e}`, `atol=0`; saturation-clipping residual is reported separately.

The recommended decision-scale pilot uses **separate amplitude and spatial heads**, with amplitude-only as the strong ablation. This follows the user-authorised representation hypothesis and the already measured E015 amplitude-plus-localisation bottleneck; it is not selected by a post-hoc E016 shape threshold. FEM pairwise shape variation is reported continuously (valid pairs `{fem_pairwise_summary['valid_pair_count']}`, half-L1 min/median/max = `{_metric_text(fem_pairwise_summary['minimum'])}` / `{_metric_text(fem_pairwise_summary['median'])}` / `{_metric_text(fem_pairwise_summary['maximum'])}`).

## What the baseline says

- Weighted-mean absolute increment 2W+T: FEM `{pair_scores['weighted_mean_absolute_increment']['FEM']['score_2W_plus_T']}`, A25 `{pair_scores['weighted_mean_absolute_increment']['A25']['score_2W_plus_T']}`, B25 `{pair_scores['weighted_mean_absolute_increment']['B25']['score_2W_plus_T']}`.
- Hazard-amplitude 2W+T: FEM `{pair_scores['hazard_amplitude']['FEM']['score_2W_plus_T']}`, B25 `{pair_scores['hazard_amplitude']['B25']['score_2W_plus_T']}`.
- B25 shape half-L1 valid cycles: `{b25_shape_summary['valid_cycle_count']}`; min/median/max: `{_metric_text(b25_shape_summary['minimum'])}` / `{_metric_text(b25_shape_summary['median'])}` / `{_metric_text(b25_shape_summary['maximum'])}`. Zero B25 events retain amplitude evidence and carry NA shape metrics.

Poor A25/B25 agreement is a measured baseline and does not invalidate the factorisation. A25 remains scalar-only because its raw node field was not persisted; this audit makes no A25 shape claim and performs no checkpoint forward.

## Claim boundary and next action

This is exposed-development representation readiness only. It does not establish training success, holdout generalisation, rollout stability, damage stationarity, history complementarity, or physical-teacher truth. Prepare an E017 short-pilot final run card with separate amplitude/spatial objectives, bounded reconstruction, beta=0.25 equilibrium as limited PINO physics, and explicit multi-objective gradient diagnostics. Do not launch training from this result alone.
"""
    (args.output / "factorisation_decision.md").write_text(decision_md)

    readme = f"""# S09-E016 analysis reading guide

## Scientific question

Can the existing exposed FEM and B25 increments be represented as a stable nonnegative capacity-aware hazard amplitude times a weighted-normalised spatial shape, so a short factorised-head pilot is well posed?

## Evidence source and order

1. `factorisation_decision.md` gives the numerical-readiness verdict and next route.
2. `factorisation_readiness.png` shows the same-unit FEM/A25/B25 amplitude bridge, exact FEM/B25 hazard amplitude, and fixed cycles 1, 69 and 73.
3. `factorisation_cycle_table.csv` is the authoritative per-cycle metric table.
4. `factorisation_arrays.npz` preserves the exact factorised shapes and round-trip residuals.

Source fields: `{args.fields}`. A25 scalar evidence: `{args.a25_table}`. Both are pre-existing exposed-development artifacts; no model forward or training was performed.

## How to read the figure

The first plot is the only direct three-arm amplitude comparison because all three values share the weighted-mean positive-increment unit. The second plot uses the new hazard amplitude and therefore contains FEM and B25 only. Shape panels show weighted-normalised `S`, displayed as `S/max(S)` for legibility; the table retains the exact weighted half-L1, cosine, support capture and centroid metrics.

## Allowed and blocked conclusions

Allowed: the representation is numerically well posed on the 16 exposed cycles, and the observed shape variation supports preparing a separate amplitude/spatial-head pilot. Blocked: A25 nodewise shape quality, any training or generalisation claim, rollout stability, and full phase-field physics closure.

## Storyline impact

E016 replaces another loss-weight scan with a representation-level repair: separate how much damage grows from where it grows. E017 remains a separately reviewed and authorised run.
"""
    (args.output / "README_analysis.md").write_text(readme)

    with csv_path.open(newline="") as stream:
        reread_rows = list(csv.DictReader(stream))
    _require(len(reread_rows) == len(EXPECTED_CYCLES), "CSV row count drift")
    _require(
        tuple(int(row["cycle"]) for row in reread_rows) == EXPECTED_CYCLES,
        "CSV cycle identity drift",
    )
    parsed_decision = json.loads((args.output / "factorisation_decision.json").read_text())
    _require(parsed_decision["readiness"]["ready"] == readiness["ready"], "decision reread drift")
    with np.load(arrays_path, allow_pickle=False) as saved_arrays:
        required_arrays = {
            "cycles",
            "fem_shape",
            "b25_shape",
            "fem_source_increment",
            "b25_source_increment",
            "fem_encoded_increment",
            "b25_encoded_increment",
            "fem_reconstructed_increment",
            "b25_reconstructed_increment",
            "fem_residual",
            "b25_residual",
        }
        _require(required_arrays <= set(saved_arrays.files), "saved array schema drift")
        _require(
            all(np.isfinite(saved_arrays[key]).all() for key in required_arrays - {"cycles"}),
            "nonfinite saved factorisation array",
        )
    rendered = plt.imread(figure_path)
    _require(rendered.size > 0 and np.isfinite(rendered).all(), "invalid rendered figure")
    _require((args.output / "factorisation_decision.md").stat().st_size > 0, "empty decision")
    _require((args.output / "README_analysis.md").stat().st_size > 0, "empty reading guide")

    generated = sorted(path for path in args.output.iterdir() if path.is_file())
    receipt = {
        "run_id": RUN_ID,
        "execution_status": "SUCCEEDED",
        "retrieval_status": "LOCAL_EXISTING_SOURCES",
        "analysis_commit": commit,
        "source_files": {
            str(args.fields): {
                "size": args.fields.stat().st_size,
                "sha256": _sha256(args.fields),
            },
            str(args.a25_table): {
                "size": args.a25_table.stat().st_size,
                "sha256": _sha256(args.a25_table),
            },
        },
        "generated_file_count_before_receipt": len(generated),
        "generated_files": {path.name: path.stat().st_size for path in generated},
        "optimizer_steps": 0,
        "model_forwards": 0,
        "new_data_access": False,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "matplotlib": matplotlib.__version__,
        },
        "output_validation": "PASSED",
        "status": readiness["status"],
    }
    _json_dump(args.output / "analysis_receipt.json", receipt)
    print(
        json.dumps(
            {"status": readiness["status"], "output": str(args.output)}, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
