#!/usr/bin/env python3
"""Analyze a fresh F1b dimensional FEM solve against the normalized reference."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path, PureWindowsPath
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from SENS_tensile.run_pi_transfer_controls import (
    _archive_project_root,
    _load_v5_cycle,
    _parse_vtk_quad_geometry,
    _weighted_metrics,
)

REFERENCE_ROOT = (
    _archive_project_root()
    / "local_archive"
    / "after_strict_setting_alignment"
    / "fem"
    / "three_case_compare_20260701"
    / "extracted"
    / "SENS_brittle_base_cyclic_u012_recovery_fatigueon_pidlstop_newtontol4em4"
)
HANDOFF = ROOT / "producer_handoffs" / "f1b_exact_pi_20260729"
SAME_CYCLES = (20, 40, 60)
REFERENCE_FIRST_HIT = 86
REFERENCE_CONFIRMED = 89
W1_CANDIDATE = 3.0
FIELD_GATES = {
    "alpha": {"mae": 0.002, "rmse": 0.005, "correlation": 0.995},
    "history": {"mae": 0.05, "rmse": 0.10, "correlation": 0.99},
    "raw": {"mae": 0.05, "rmse": 0.10, "correlation": 0.99},
    "active": {"mae": 0.05, "rmse": 0.10, "correlation": 0.99},
}
SUPPORT_IOU_MIN = 0.90
SUPPORT_AREA_RATIO_MIN = 0.90
SUPPORT_AREA_RATIO_MAX = 1.10
EVENT_CYCLE_ERROR_MAX = 1


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values)
    sorted_values = np.asarray(values, dtype=np.float64)[order]
    sorted_weights = np.asarray(weights, dtype=np.float64)[order]
    cumulative = np.cumsum(sorted_weights)
    cutoff = q * float(cumulative[-1])
    return float(sorted_values[np.searchsorted(cumulative, cutoff, side="left")])


def _support_metrics(
    reference: np.ndarray,
    candidate: np.ndarray,
    xy: np.ndarray,
    areas: np.ndarray,
) -> dict[str, float]:
    threshold = _weighted_quantile(reference, areas, 0.99)
    reference_mask = reference >= threshold
    candidate_mask = candidate >= threshold
    intersection = float(np.sum(areas[reference_mask & candidate_mask]))
    union = float(np.sum(areas[reference_mask | candidate_mask]))
    reference_area = float(np.sum(areas[reference_mask]))
    candidate_area = float(np.sum(areas[candidate_mask]))
    if reference_area <= 0 or candidate_area <= 0 or union <= 0:
        return {
            "threshold": threshold,
            "iou": 0.0,
            "area_ratio": candidate_area / reference_area if reference_area else np.nan,
            "centroid_offset": np.inf,
            "cell_diameter": np.nan,
        }
    reference_centroid = np.sum(
        xy[reference_mask] * areas[reference_mask, None], axis=0
    ) / reference_area
    candidate_centroid = np.sum(
        xy[candidate_mask] * areas[candidate_mask, None], axis=0
    ) / candidate_area
    support_areas = areas[reference_mask]
    cell_diameter = float(
        np.sqrt(_weighted_quantile(support_areas, support_areas, 0.50))
    )
    return {
        "threshold": threshold,
        "iou": intersection / union,
        "area_ratio": candidate_area / reference_area,
        "centroid_offset": float(np.linalg.norm(candidate_centroid - reference_centroid)),
        "cell_diameter": cell_diameter,
    }


def _load_candidate_cycle(path: Path) -> dict[str, np.ndarray]:
    payload = loadmat(path, squeeze_me=True)
    required = {"d_elem", "alpha_elem", "psi_elem"}
    missing = sorted(required - set(payload))
    if missing:
        raise KeyError(f"{path} missing {missing}")
    alpha = np.asarray(payload["d_elem"], dtype=np.float64).reshape(-1)
    history = np.asarray(payload["alpha_elem"], dtype=np.float64).reshape(-1)
    raw = np.asarray(payload["psi_elem"], dtype=np.float64).reshape(-1)
    return {
        "alpha": alpha,
        "history": history / W1_CANDIDATE,
        "raw": raw / W1_CANDIDATE,
        "active": ((1.0 - alpha) ** 2 * raw) / W1_CANDIDATE,
    }


def _load_reference_cycle(path: Path) -> dict[str, np.ndarray]:
    fields = _load_v5_cycle(path)
    fields["active"] = (1.0 - fields["alpha"]) ** 2 * fields["raw"]
    return fields


def _validate_provenance(candidate_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if candidate_root.resolve() == REFERENCE_ROOT.resolve():
        raise ValueError("candidate output root is not independent of the reference")
    snapshot = _json(candidate_root / "F1B_INPUT_SNAPSHOT.json")
    producer = _json(candidate_root / "F1B_PRODUCER_PROVENANCE.json")
    event = _json(candidate_root / "F1B_EVENT_METADATA.json")
    for label, payload in (("snapshot", snapshot), ("producer", producer), ("event", event)):
        if payload.get("fresh_fem_solve") is not True:
            raise ValueError(f"{label} does not prove fresh_fem_solve=true")
    lock_hash = _sha256(HANDOFF / "INPUT_LOCK.json")
    if snapshot.get("input_lock_sha256") != lock_hash:
        raise ValueError("candidate input-lock hash differs from the committed handoff")
    if producer.get("input_lock_sha256") != lock_hash:
        raise ValueError("producer provenance input-lock hash differs from the committed handoff")
    if snapshot.get("source_commit") != producer.get("source_commit"):
        raise ValueError("snapshot and producer provenance use different commits")
    if snapshot.get("output_root") != producer.get("output_root"):
        raise ValueError("snapshot and producer provenance use different output roots")
    if producer.get("gripfith_sources_clean") is not True:
        raise ValueError("producer does not prove immutable GRIPHFiTH sources")
    if not producer.get("gripfith_commit"):
        raise ValueError("producer does not record the GRIPHFiTH solver commit")
    remote_name = PureWindowsPath(producer["output_root"]).name
    if candidate_root.name != remote_name:
        raise ValueError("downloaded candidate folder was renamed after producer execution")
    lock = _json(HANDOFF / "INPUT_LOCK.json")
    for key in ("E", "nu", "Gc", "ell", "L", "H", "thickness", "Umax", "alpha_T", "w1", "eta", "R"):
        if not np.isclose(float(snapshot[key]), float(lock["candidate"][key]), rtol=0, atol=1e-14):
            raise ValueError(f"candidate snapshot violates locked {key}")
    for key in ("plane_state", "pff_model", "energy_split", "boundary_condition"):
        if snapshot[key] != lock["candidate"][key]:
            raise ValueError(f"candidate snapshot violates locked {key}")
    numerical = lock["numerical_contract"]
    numerical_checks = {
        "force_residual_scale": numerical["candidate_force_residual_scale"],
        "energy_residual_scale": numerical["candidate_energy_residual_scale"],
        "tol_displ": numerical["candidate_tol_displ_dimensional"],
        "tol_p_field": numerical["candidate_tol_phase_field_dimensional"],
        "tol_displ_dimensionless": numerical["tol_displ_dimensionless"],
        "tol_p_field_dimensionless": numerical["tol_phase_field_dimensionless"],
        "tol_staggered_dimensionless": numerical["tol_staggered_dimensionless"],
        "regularization_floor_dimensionless": numerical["regularization_floor_dimensionless"],
        "regularization_floor_dimensional": numerical["candidate_regularization_floor_dimensional"],
    }
    for key, expected in numerical_checks.items():
        if not np.isclose(float(snapshot[key]), float(expected), rtol=0, atol=1e-14):
            raise ValueError(f"candidate snapshot violates locked numerical control {key}")
    return snapshot, producer, event


def _mesh(candidate_root: Path) -> tuple[np.ndarray, np.ndarray]:
    reference_centroids, reference_areas = _parse_vtk_quad_geometry(
        REFERENCE_ROOT / "fields_000089_008.vtk"
    )
    payload = loadmat(candidate_root / "f1b_mesh_geometry.mat", squeeze_me=True)
    candidate_centroids = np.asarray(payload["element_centroids"], dtype=np.float64)
    candidate_areas = np.asarray(payload["area_per_elem"], dtype=np.float64).reshape(-1)
    if candidate_centroids.shape != reference_centroids.shape:
        raise ValueError("candidate/reference centroid shape mismatch")
    if not np.allclose(candidate_centroids / 10.0, reference_centroids, rtol=0, atol=1e-12):
        raise ValueError("candidate coordinates are not the locked tenfold mesh transform")
    if not np.allclose(candidate_areas / 100.0, reference_areas, rtol=1e-12, atol=1e-14):
        raise ValueError("candidate areas are not the locked hundredfold area transform")
    return reference_centroids, reference_areas


def _field_rows(
    candidate_root: Path,
    xy: np.ndarray,
    areas: np.ndarray,
    first_hit: int,
    confirmed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, np.ndarray]]:
    rows: list[dict[str, Any]] = []
    support_rows: list[dict[str, Any]] = []
    event_arrays: dict[str, np.ndarray] = {}
    comparisons = [
        ("same-cycle", cycle, cycle) for cycle in SAME_CYCLES
    ] + [
        ("first-hit own-event", REFERENCE_FIRST_HIT, first_hit),
        ("confirmed own-event", REFERENCE_CONFIRMED, confirmed),
    ]
    for comparison_class, reference_cycle, candidate_cycle in comparisons:
        reference = _load_reference_cycle(
            REFERENCE_ROOT / "psi_fields" / f"cycle_{reference_cycle:04d}.mat"
        )
        candidate = _load_candidate_cycle(
            candidate_root / "psi_fields" / f"cycle_{candidate_cycle:04d}.mat"
        )
        for field in ("alpha", "history", "raw", "active"):
            if reference[field].shape != candidate[field].shape:
                raise ValueError(
                    f"{field} shape mismatch at reference c{reference_cycle} "
                    f"and candidate c{candidate_cycle}"
                )
            log_floor = None
            metric_space = "linear"
            if field != "alpha":
                log_floor = max(1e-16, float(np.max(reference[field])) * 1e-12)
                metric_space = "log10"
            metrics = _weighted_metrics(
                reference[field], candidate[field], areas, log_floor=log_floor
            )
            gate = FIELD_GATES[field]
            passed = (
                metrics["mae"] <= gate["mae"]
                and metrics["rmse"] <= gate["rmse"]
                and metrics["correlation"] >= gate["correlation"]
            )
            rows.append(
                {
                    "comparison_class": comparison_class,
                    "reference_cycle": reference_cycle,
                    "candidate_cycle": candidate_cycle,
                    "state_label": "cycle-peak raw plus cycle-output damage/history",
                    "field": field,
                    "metric_space": metric_space,
                    **metrics,
                    "mae_max": gate["mae"],
                    "rmse_max": gate["rmse"],
                    "correlation_min": gate["correlation"],
                    "pass": passed,
                }
            )
            if comparison_class == "confirmed own-event":
                event_arrays[f"reference_{field}"] = reference[field]
                event_arrays[f"candidate_{field}"] = candidate[field]
        support = _support_metrics(reference["active"], candidate["active"], xy, areas)
        support_pass = (
            support["iou"] >= SUPPORT_IOU_MIN
            and SUPPORT_AREA_RATIO_MIN <= support["area_ratio"] <= SUPPORT_AREA_RATIO_MAX
            and support["centroid_offset"] <= support["cell_diameter"]
        )
        support_rows.append(
            {
                "comparison_class": comparison_class,
                "reference_cycle": reference_cycle,
                "candidate_cycle": candidate_cycle,
                **support,
                "iou_min": SUPPORT_IOU_MIN,
                "area_ratio_min": SUPPORT_AREA_RATIO_MIN,
                "area_ratio_max": SUPPORT_AREA_RATIO_MAX,
                "centroid_offset_max": support["cell_diameter"],
                "pass": support_pass,
            }
        )
    return rows, support_rows, event_arrays


def _figure(output: Path, xy: np.ndarray, arrays: dict[str, np.ndarray]) -> None:
    fields = ("alpha", "history", "raw", "active")
    fig, axes = plt.subplots(4, 3, figsize=(13, 12), constrained_layout=True)
    for row, field in enumerate(fields):
        reference = arrays[f"reference_{field}"]
        candidate = arrays[f"candidate_{field}"]
        if field == "alpha":
            ref_plot = reference
            cand_plot = candidate
            residual = candidate - reference
        else:
            floor = max(1e-16, float(np.max(reference)) * 1e-12)
            ref_plot = np.log10(np.maximum(reference, floor))
            cand_plot = np.log10(np.maximum(candidate, floor))
            residual = cand_plot - ref_plot
        common_min = min(float(np.min(ref_plot)), float(np.min(cand_plot)))
        common_max = max(float(np.max(ref_plot)), float(np.max(cand_plot)))
        for col, (values, title) in enumerate(
            ((ref_plot, "normalized reference"), (cand_plot, "fresh dimensional"), (residual, "candidate-reference"))
        ):
            kwargs: dict[str, Any] = {"s": 1.0, "rasterized": True}
            if col < 2:
                kwargs.update(vmin=common_min, vmax=common_max, cmap="viridis")
            else:
                limit = max(float(np.max(np.abs(residual))), 1e-16)
                kwargs.update(vmin=-limit, vmax=limit, cmap="coolwarm")
            scatter = axes[row, col].scatter(xy[:, 0], xy[:, 1], c=values, **kwargs)
            axes[row, col].set_aspect("equal")
            axes[row, col].set_title(f"{field}: {title}", fontsize=9)
            axes[row, col].set_xticks([])
            axes[row, col].set_yticks([])
            fig.colorbar(scatter, ax=axes[row, col], fraction=0.046)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def analyze(candidate_root: Path, output: Path) -> bool:
    candidate_root = candidate_root.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    snapshot, producer, event = _validate_provenance(candidate_root)
    xy, areas = _mesh(candidate_root)
    first_hit = event.get("first_hit_cycle")
    confirmed = event.get("confirmed_cycle")
    if first_hit is None or confirmed is None:
        raise ValueError("candidate did not report both first-hit and confirmed event cycles")
    first_hit = int(first_hit)
    confirmed = int(confirmed)
    rows, support_rows, arrays = _field_rows(
        candidate_root, xy, areas, first_hit, confirmed
    )
    first_hit_pass = abs(first_hit - REFERENCE_FIRST_HIT) <= EVENT_CYCLE_ERROR_MAX
    confirmed_pass = abs(confirmed - REFERENCE_CONFIRMED) <= EVENT_CYCLE_ERROR_MAX
    fields_pass = all(bool(row["pass"]) for row in rows)
    support_pass = all(bool(row["pass"]) for row in support_rows)
    passed = first_hit_pass and confirmed_pass and fields_pass and support_pass

    _write_csv(output / "f1b_fem_centred_field_metrics.csv", rows)
    _write_csv(output / "f1b_active_support_metrics.csv", support_rows)
    _write_csv(
        output / "event_state_map.csv",
        [
            {
                "model": "normalized FEM reference",
                "first_hit_cycle": REFERENCE_FIRST_HIT,
                "confirmed_cycle": REFERENCE_CONFIRMED,
                "fresh_fem_solve": False,
                "state_label": "cycle-peak raw plus cycle-output damage/history",
            },
            {
                "model": "F1b exact-Pi dimensional FEM",
                "first_hit_cycle": first_hit,
                "confirmed_cycle": confirmed,
                "fresh_fem_solve": True,
                "state_label": event["state_phase"],
            },
        ],
    )
    _figure(output / "f1b_event_fields_and_residuals.png", xy, arrays)

    verdict = "PASS" if passed else "FAIL"
    decision = f"""# F1b Fresh Dimensional Solver-Invariance Decision

## Verdict

**{verdict}.** This is a fresh FEM solver-invariance control, not road validation.

- Fresh solve provenance: `true`
- Independent output root: `{candidate_root}`
- First hit: reference c{REFERENCE_FIRST_HIT}, candidate `{first_hit}`
- Confirmed event: reference c{REFERENCE_CONFIRMED}, candidate `{confirmed}`
- All locked normalized field gates passed: `{str(fields_pass).lower()}`
- All locked active-support gates passed: `{str(support_pass).lower()}`

The immutable fresh-solve gate is not floating-point identity. Linear damage
must pass MAE/RMSE/correlation `0.002/0.005/0.995`; normalized history, raw and
active fields in log10 space must pass `0.05/0.10/0.99`. Active support must
pass FEM-p99 IoU `>=0.90`, area ratio `[0.90,1.10]`, and a centroid offset no
larger than one local support-cell diameter. These gates apply at same-cycle
c20/c40/c60 and at first-hit and confirmed own-event states. Event-cycle errors
must each be at most one explicitly resolved cycle. Failure is retained as
evidence of solver/implementation non-invariance; thresholds are not relaxed
after observing the result.

No road, layered-pavement, temperature/rate, traffic-cycle, forecasting, inverse,
or PIDL-training claim follows from this control.
"""
    (output / "decision.md").write_text(decision, encoding="utf-8")
    manifest = {
        "analysis": "F1b_exact_pi_solver_invariance_v2",
        "status": verdict.lower(),
        "fresh_fem_solve": True,
        "candidate_output_root": str(candidate_root),
        "candidate_source_commit": producer["source_commit"],
        "input_lock_sha256": snapshot["input_lock_sha256"],
        "first_hit_pass": first_hit_pass,
        "confirmed_event_pass": confirmed_pass,
        "normalized_fields_pass": fields_pass,
        "active_support_pass": support_pass,
        "same_cycle_comparisons": list(SAME_CYCLES),
        "own_event_reference_cycles": [REFERENCE_FIRST_HIT, REFERENCE_CONFIRMED],
        "road_validation": False,
        "pidl_training": False,
    }
    (output / "RUN_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    assets = sorted(path for path in output.iterdir() if path.name != "HASHES.sha256")
    (output / "HASHES.sha256").write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in assets if path.is_file()),
        encoding="utf-8",
    )
    return passed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    passed = analyze(args.candidate_root, args.output)
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
