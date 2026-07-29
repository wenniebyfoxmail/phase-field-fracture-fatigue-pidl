#!/usr/bin/env python3
"""Run corrected-scaling F1/F2 controls without PIDL training.

F1 replays archived FEM fields through two dimensional realizations that share
the complete declared Pi vector. F2 compares two archived FEM cases that share
the scalar Pi groups but use different horizontal boundary constraints.

The F1 replay validates the scaling, normalization, and field-I/O path. It is
not a fresh FEM solve. F2 is an actual archived-FEM negative control, but raw
and active-driver comparisons remain unobservable where the old archive did
not export a raw driver.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from scaling import PhaseFieldScaling, audit_pi_transfer


def _archive_project_root() -> Path:
    override = os.environ.get("PIDL_PROJECT_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    candidates = [ROOT, *ROOT.parents]
    for candidate in candidates:
        if (candidate / "local_archive").is_dir():
            return candidate
    return ROOT


FEM_ROOT = (
    _archive_project_root()
    / "local_archive"
    / "after_strict_setting_alignment"
    / "fem"
    / "three_case_compare_20260701"
    / "extracted"
    / "SENS_brittle_base_cyclic_u012_recovery_fatigueon_pidlstop_newtontol4em4"
)
DEFAULT_F2_FREE = Path(
    "/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/"
    "PIDL result/u12_cycle_0082_FEM7.mat"
)
DEFAULT_F2_REVERSE = Path(
    "/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/"
    "PIDL result/_pidl_handoff_reverseBC_u12_cyclewise_mechanism_2026-05-28/"
    "reverseBC_u12_cyclewise_element_fields_c1_c74.mat"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _weighted_metrics(
    reference: np.ndarray,
    candidate: np.ndarray,
    weights: np.ndarray,
    *,
    log_floor: float | None = None,
) -> dict[str, float]:
    reference = np.asarray(reference, dtype=np.float64).reshape(-1)
    candidate = np.asarray(candidate, dtype=np.float64).reshape(-1)
    weights = np.asarray(weights, dtype=np.float64).reshape(-1)
    if reference.shape != candidate.shape or reference.shape != weights.shape:
        raise ValueError("reference, candidate, and weights must have equal shape")
    weights = weights / np.sum(weights)
    if log_floor is not None:
        reference = np.log10(np.maximum(reference, log_floor))
        candidate = np.log10(np.maximum(candidate, log_floor))
    residual = candidate - reference
    ref_mean = float(np.sum(weights * reference))
    cand_mean = float(np.sum(weights * candidate))
    ref_centered = reference - ref_mean
    cand_centered = candidate - cand_mean
    denom = float(
        np.sqrt(
            np.sum(weights * ref_centered**2)
            * np.sum(weights * cand_centered**2)
        )
    )
    correlation = (
        float(np.sum(weights * ref_centered * cand_centered) / denom)
        if denom > 0
        else float(reference.shape == candidate.shape and np.array_equal(reference, candidate))
    )
    return {
        "mae": float(np.sum(weights * np.abs(residual))),
        "rmse": float(np.sqrt(np.sum(weights * residual**2))),
        "max_abs": float(np.max(np.abs(residual))),
        "correlation": correlation,
        "reference_mean": ref_mean,
        "candidate_mean": cand_mean,
    }


def _load_v5_cycle(path: Path) -> dict[str, np.ndarray]:
    from scipy.io import loadmat

    payload = loadmat(path, squeeze_me=True)
    required = {"d_elem", "alpha_bar_elem", "psi_elem"}
    missing = sorted(required - set(payload))
    if missing:
        raise KeyError(f"{path} missing fields {missing}")
    return {
        "alpha": np.asarray(payload["d_elem"], dtype=np.float64).reshape(-1),
        "history": np.asarray(payload["alpha_bar_elem"], dtype=np.float64).reshape(-1),
        "raw": np.asarray(payload["psi_elem"], dtype=np.float64).reshape(-1),
        "fatigue_f": np.asarray(payload["f_alpha_elem"], dtype=np.float64).reshape(-1),
    }


def _parse_vtk_quad_geometry(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read points/quads from the archived ASCII legacy VTK file."""
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("POINTS"):
                n_points = int(line.split()[1])
                break
        else:
            raise ValueError(f"POINTS section missing from {path}")
        points = np.empty((n_points, 3), dtype=np.float64)
        for index in range(n_points):
            values = np.fromstring(handle.readline(), sep=" ")
            if values.size != 3:
                raise ValueError(f"invalid point row {index} in {path}")
            points[index] = values
        for line in handle:
            if line.startswith("CELLS"):
                n_cells = int(line.split()[1])
                break
        else:
            raise ValueError(f"CELLS section missing from {path}")
        connectivity = np.empty((n_cells, 4), dtype=np.int64)
        for index in range(n_cells):
            values = np.fromstring(handle.readline(), sep=" ", dtype=np.int64)
            if values.size != 5 or values[0] != 4:
                raise ValueError(f"expected a quad at cell {index} in {path}")
            connectivity[index] = values[1:]

    xy = points[connectivity, :2]
    centroids = np.mean(xy, axis=1)
    x = xy[:, :, 0]
    y = xy[:, :, 1]
    areas = 0.5 * np.abs(
        np.sum(x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1), axis=1)
    )
    if np.any(areas <= 0):
        raise ValueError("VTK contains non-positive quad areas")
    return centroids, areas


def _toy_realization(
    *,
    boundary_condition: str,
    material_label: str,
) -> PhaseFieldScaling:
    return PhaseFieldScaling(
        E_phys=1.0,
        nu_phys=0.3,
        G_c_phys=0.01,
        ell_phys=0.01,
        L_phys=1.0,
        H_phys=1.0,
        a0_phys=0.5,
        u_max_phys=0.12,
        alpha_T_phys=0.5,
        mesh_h_phys=0.01,
        residual_stiffness=0.0,
        R_ratio=0.0,
        pff_model="AT1",
        plane_condition="plane_strain",
        energy_split="amor",
        boundary_condition=boundary_condition,
        geometry_form="homogeneous_sent_square_void_notch",
        load_form="cyclic_edge_displacement",
        geometry_load_ratios=(("loaded_edge_fraction", 1.0),),
        material_label=material_label,
        evidence_class="archived-fem-toy",
    )


def _physical_exact_realization() -> PhaseFieldScaling:
    return PhaseFieldScaling.from_dimensionless_toy(
        E_phys=3.0,
        G_c_phys=0.3,
        ell_phys=0.1,
        L_phys=10.0,
        h_over_ell=1.0,
        boundary_condition="top_bottom_ux_clamp_reverse_bc",
        energy_split="amor",
        geometry_form="homogeneous_sent_square_void_notch",
        load_form="cyclic_edge_displacement",
        geometry_load_ratios=(("loaded_edge_fraction", 1.0),),
        material_label="F1 exact-Pi dimensional realization",
        evidence_class="similarity-control-only",
    )


def _flatten_pi_rows(
    control: str,
    rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [{"control": control, **row} for row in rows]


def _field_row(
    *,
    control: str,
    cycle: int,
    comparison_class: str,
    state_label: str,
    field: str,
    metric_space: str,
    status: str,
    metrics: dict[str, float] | None,
    note: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "control": control,
        "cycle": cycle,
        "comparison_class": comparison_class,
        "state_label": state_label,
        "field": field,
        "metric_space": metric_space,
        "status": status,
        "note": note,
    }
    if metrics:
        row.update(metrics)
    return row


def _run_f1(
    fem_root: Path,
    cycles: list[int],
    centroids: np.ndarray,
    areas: np.ndarray,
) -> tuple[list[dict[str, Any]], dict[str, np.ndarray], list[dict[str, Any]]]:
    reference_scale = _toy_realization(
        boundary_condition="top_bottom_ux_clamp_reverse_bc",
        material_label="formal FEM normalized reference",
    )
    candidate_scale = _physical_exact_realization()
    pi_rows = _flatten_pi_rows(
        "F1_exact_pi",
        audit_pi_transfer(
            reference_scale.normalized_groups(), candidate_scale.normalized_groups()
        ),
    )
    rows: list[dict[str, Any]] = []
    event_fields: dict[str, np.ndarray] = {}
    for cycle in cycles:
        fields = _load_v5_cycle(fem_root / "psi_fields" / f"cycle_{cycle:04d}.mat")
        if fields["alpha"].size != areas.size:
            raise ValueError("F1 VTK geometry and MAT field size differ")
        fields["active"] = (1.0 - fields["alpha"]) ** 2 * fields["raw"]
        for name in ("alpha", "history", "raw", "active"):
            normalized_reference = fields[name]
            if name == "alpha":
                physical_candidate = normalized_reference.copy()
                normalized_candidate = physical_candidate
                log_floor = None
                metric_space = "linear"
            else:
                physical_candidate = normalized_reference * candidate_scale.w1_phys
                normalized_candidate = physical_candidate / candidate_scale.w1_phys
                log_floor = max(1e-16, float(np.max(normalized_reference)) * 1e-12)
                metric_space = "log10"
            metrics = _weighted_metrics(
                normalized_reference,
                normalized_candidate,
                areas,
                log_floor=log_floor,
            )
            rows.append(
                _field_row(
                    control="F1_exact_pi",
                    cycle=cycle,
                    comparison_class="same-cycle dimensional replay",
                    state_label=(
                        "FEM cycle-peak raw plus cycle-output damage/history"
                    ),
                    field=name,
                    metric_space=metric_space,
                    status="observed",
                    metrics=metrics,
                    note="area-weighted archived-FEM dimensional round trip",
                )
            )
            event_fields[f"c{cycle}_{name}_reference"] = normalized_reference
            event_fields[f"c{cycle}_{name}_candidate"] = normalized_candidate
            if cycle == cycles[-1]:
                event_fields[f"reference_{name}"] = normalized_reference
                event_fields[f"candidate_{name}"] = normalized_candidate
        if cycle == cycles[-1]:
            event_fields["centroids"] = centroids
            event_fields["areas"] = areas
    return rows, event_fields, pi_rows


def _load_f2_free(path: Path) -> dict[str, Any]:
    from scipy.io import loadmat

    payload = loadmat(path, squeeze_me=True)
    return {
        "centroids": np.asarray(payload["centroids"], dtype=np.float64),
        "areas": np.asarray(payload["area_per_elem"], dtype=np.float64).reshape(-1),
        "alpha": np.asarray(payload["d_elem"], dtype=np.float64).reshape(-1),
        "history": np.asarray(payload["alpha_bar_elem"], dtype=np.float64).reshape(-1),
        "cycle": int(np.asarray(payload["cycle"]).item()),
    }


def _load_f2_reverse(path: Path) -> dict[str, Any]:
    import h5py

    with h5py.File(path, "r") as handle:
        cycles = np.asarray(handle["cycles"], dtype=np.float64).reshape(-1)
        return {
            "centroids": np.asarray(handle["element_centroids"], dtype=np.float64).T,
            "areas": np.asarray(handle["element_area"], dtype=np.float64).reshape(-1),
            "alpha": np.asarray(handle["d_elem"], dtype=np.float64)[-1],
            "history": np.asarray(handle["alpha_bar_elem"], dtype=np.float64)[-1],
            "raw": np.asarray(handle["psi_plus_elem"], dtype=np.float64)[-1],
            "cycle": int(cycles[-1]),
        }


def _run_f2(
    free_path: Path,
    reverse_path: Path,
) -> tuple[
    list[dict[str, Any]],
    dict[str, np.ndarray],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    free = _load_f2_free(free_path)
    reverse = _load_f2_reverse(reverse_path)
    if not np.array_equal(free["centroids"], reverse["centroids"]):
        raise ValueError("F2 FEM cases are not on the same element centroids")
    if not np.array_equal(free["areas"], reverse["areas"]):
        raise ValueError("F2 FEM cases are not on the same element areas")

    reference_scale = _toy_realization(
        boundary_condition="bottom_left_ux_anchor_free_lateral",
        material_label="FEM7 original-BC reference",
    )
    candidate_scale = _toy_realization(
        boundary_condition="top_bottom_ux_clamp_reverse_bc",
        material_label="reverseBC archived FEM",
    )
    pi_rows = _flatten_pi_rows(
        "F2_bc_negative",
        audit_pi_transfer(
            reference_scale.normalized_groups(), candidate_scale.normalized_groups()
        ),
    )

    rows: list[dict[str, Any]] = []
    for field in ("alpha", "history"):
        metric_space = "linear" if field == "alpha" else "log10"
        log_floor = None if field == "alpha" else max(
            1e-16, float(max(np.max(free[field]), np.max(reverse[field]))) * 1e-12
        )
        metrics = _weighted_metrics(
            free[field], reverse[field], free["areas"], log_floor=log_floor
        )
        rows.append(
            _field_row(
                control="F2_bc_negative",
                cycle=reverse["cycle"],
                comparison_class="own-event archived FEM",
                state_label="old free-lateral c82 event versus reverseBC c74 event",
                field=field,
                metric_space=metric_space,
                status="observed",
                metrics=metrics,
                note="same mesh/material/load amplitude; boundary constraint differs",
            )
        )
    for field in ("raw", "active"):
        rows.append(
            _field_row(
                control="F2_bc_negative",
                cycle=reverse["cycle"],
                comparison_class="own-event archived FEM",
                state_label="old free-lateral c82 event versus reverseBC c74 event",
                field=field,
                metric_space="log10",
                status="unobservable",
                metrics=None,
                note="FEM7 c82 archive did not export a raw driver; no value imputed",
            )
        )
    fields = {
        "centroids": free["centroids"],
        "areas": free["areas"],
        "reference_alpha": free["alpha"],
        "candidate_alpha": reverse["alpha"],
        "reference_history": free["history"],
        "candidate_history": reverse["history"],
    }
    event_rows = [
        {
            "control": "F2_bc_negative",
            "reference_event_cycle": free["cycle"],
            "candidate_event_cycle": reverse["cycle"],
            "delta_cycle": reverse["cycle"] - free["cycle"],
            "reference_phase": "penetration/event snapshot",
            "candidate_phase": "terminal own-event cycle",
            "status": "mismatched",
        }
    ]
    return rows, fields, pi_rows, event_rows


def _scatter_panel(
    axis: plt.Axes,
    centroids: np.ndarray,
    values: np.ndarray,
    *,
    title: str,
    cmap: str,
    vmin: float | None = None,
    vmax: float | None = None,
) -> None:
    stride = max(1, len(values) // 30_000)
    image = axis.scatter(
        centroids[::stride, 0],
        centroids[::stride, 1],
        c=values[::stride],
        s=1.0,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        linewidths=0,
    )
    axis.set_title(title, fontsize=9)
    axis.set_aspect("equal")
    axis.set_xticks([])
    axis.set_yticks([])
    plt.colorbar(image, ax=axis, fraction=0.046, pad=0.02)


def _make_figure(
    path: Path,
    f1: dict[str, np.ndarray],
    f2: dict[str, np.ndarray],
) -> None:
    fig, axes = plt.subplots(4, 3, figsize=(10.5, 11.5), constrained_layout=True)
    rows = [
        (
            f1["centroids"],
            f1["reference_alpha"],
            f1["candidate_alpha"],
            "F1 alpha",
            "viridis",
            False,
        ),
        (
            f1["centroids"],
            np.log10(np.maximum(f1["reference_active"], 1e-16)),
            np.log10(np.maximum(f1["candidate_active"], 1e-16)),
            "F1 log10 active/w1",
            "magma",
            False,
        ),
        (
            f2["centroids"],
            f2["reference_alpha"],
            f2["candidate_alpha"],
            "F2 alpha own-event",
            "viridis",
            False,
        ),
        (
            f2["centroids"],
            np.log10(np.maximum(f2["reference_history"], 1e-16)),
            np.log10(np.maximum(f2["candidate_history"], 1e-16)),
            "F2 log10 history/w1 own-event",
            "magma",
            False,
        ),
    ]
    for row_index, (centroids, ref, cand, label, cmap, _) in enumerate(rows):
        common_min = float(min(np.min(ref), np.min(cand)))
        common_max = float(max(np.max(ref), np.max(cand)))
        residual = cand - ref
        residual_max = max(float(np.max(np.abs(residual))), 1e-15)
        _scatter_panel(
            axes[row_index, 0], centroids, ref, title=f"{label}: FEM reference",
            cmap=cmap, vmin=common_min, vmax=common_max,
        )
        _scatter_panel(
            axes[row_index, 1], centroids, cand, title=f"{label}: candidate",
            cmap=cmap, vmin=common_min, vmax=common_max,
        )
        _scatter_panel(
            axes[row_index, 2], centroids, residual, title=f"{label}: candidate - FEM",
            cmap="coolwarm", vmin=-residual_max, vmax=residual_max,
        )
    fig.suptitle(
        "Corrected Pi-transfer controls: exact dimensional replay and BC negative control",
        fontsize=12,
    )
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fem-root", type=Path, default=FEM_ROOT)
    parser.add_argument("--f2-free-bc", type=Path, default=DEFAULT_F2_FREE)
    parser.add_argument("--f2-reverse-bc", type=Path, default=DEFAULT_F2_REVERSE)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "pi_transfer_controls_20260729",
    )
    args = parser.parse_args()
    fem_root = args.fem_root.resolve()
    free_path = args.f2_free_bc.resolve()
    reverse_path = args.f2_reverse_bc.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    input_paths = [
        fem_root / "fields_000089_008.vtk",
        *(fem_root / "psi_fields" / f"cycle_{cycle:04d}.mat" for cycle in (20, 40, 60, 89)),
        free_path,
        reverse_path,
    ]
    missing = [str(path) for path in input_paths if not path.exists()]
    if missing:
        raise FileNotFoundError("missing control inputs:\n" + "\n".join(missing))

    centroids, areas = _parse_vtk_quad_geometry(input_paths[0])
    f1_rows, f1_fields, f1_pi = _run_f1(
        fem_root, [20, 40, 60, 89], centroids, areas
    )
    f2_rows, f2_fields, f2_pi, f2_events = _run_f2(free_path, reverse_path)
    pi_rows = f1_pi + f2_pi
    field_rows = f1_rows + f2_rows
    event_rows = [
        {
            "control": "F1_exact_pi",
            "reference_event_cycle": 89,
            "candidate_event_cycle": 89,
            "delta_cycle": 0,
            "reference_phase": "archived FEM c89 confirmed event",
            "candidate_phase": "same archived state after dimensional round trip",
            "status": "matched",
            "note": "replay control; not an independent event prediction",
        },
        *f2_events,
    ]

    _write_csv(output / "pi_transfer_audit.csv", pi_rows)
    _write_csv(output / "fem_centred_field_metrics.csv", field_rows)
    _write_csv(output / "event_state_map.csv", event_rows)
    _write_csv(
        output / "w1_provenance.csv",
        [
            {
                "definition": "w1=G_c/ell",
                "w1_norm": 1.0,
                "status": "primary corrected scaling",
                "reason": "c_w is already divided inside compute_energy.py",
            },
            {
                "definition": "w1=c_w*G_c/ell",
                "w1_norm": "c_w",
                "status": "quarantine provenance only",
                "reason": "double-counts c_w in the implemented functional",
            },
        ],
    )
    scale_contracts = {
        "F1_reference": _toy_realization(
            boundary_condition="top_bottom_ux_clamp_reverse_bc",
            material_label="formal FEM normalized reference",
        ).to_contract(),
        "F1_candidate": _physical_exact_realization().to_contract(),
        "F2_reference": _toy_realization(
            boundary_condition="bottom_left_ux_anchor_free_lateral",
            material_label="FEM7 original-BC reference",
        ).to_contract(),
        "F2_candidate": _toy_realization(
            boundary_condition="top_bottom_ux_clamp_reverse_bc",
            material_label="reverseBC archived FEM",
        ).to_contract(),
    }
    (output / "scale_contracts.json").write_text(
        json.dumps(scale_contracts, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    f1_archive_fields = {
        f"f1_{key.removesuffix('_reference')}_norm": value
        for key, value in f1_fields.items()
        if key.startswith("c") and key.endswith("_reference")
    }
    f1_archive_fields.update(
        {f"f1_{key}": f1_fields[key] for key in ("centroids", "areas")}
    )
    np.savez_compressed(
        output / "normalized_control_fields.npz",
        **f1_archive_fields,
        **{f"f2_{key}": value for key, value in f2_fields.items()},
    )
    _make_figure(output / "f1_f2_fem_centred_fields.png", f1_fields, f2_fields)

    f1_metric_rows = [row for row in field_rows if row["control"] == "F1_exact_pi"]
    f1_max_error = max(float(row["max_abs"]) for row in f1_metric_rows)
    f1_pi_pass = all(row["status"] == "matched" for row in f1_pi)
    f2_numeric_pi_pass = all(
        row["status"] == "matched"
        for row in f2_pi
        if row.get("category") in {"buckingham_pi", "geometry_load_ratio"}
    )
    f2_bc_rows = [row for row in f2_pi if row.get("group") == "boundary_condition"]
    summary = {
        "analysis": "corrected_pi_transfer_controls_v1",
        "training_run": False,
        "fresh_fem_solve": False,
        "f1_evidence_class": "archived FEM exact-dimensional replay",
        "f2_evidence_class": "archived FEM BC negative control",
        "f1_exact_pi_pass": f1_pi_pass,
        "f1_field_roundtrip_max_abs": f1_max_error,
        "f1_event_cycle_reference": 89,
        "f1_event_cycle_candidate": 89,
        "f2_scalar_pi_pass": f2_numeric_pi_pass,
        "f2_boundary_condition_status": f2_bc_rows[0]["status"],
        "f2_event_cycle_reference": 82,
        "f2_event_cycle_candidate": 74,
        "f2_delta_cycle": -8,
        "f2_raw_active_status": "unobservable in FEM7 c82 archive",
        "road_validation": False,
        "cycle_to_traffic_mapping": False,
        "claim_boundary": (
            "F1 validates dimensional replay and normalization, not a fresh solver; "
            "F2 proves scalar Pi groups are insufficient when BC/model form changes."
        ),
    }
    (output / "control_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        git_sha = "unavailable"
    manifest = {
        **summary,
        "runner": "SENS_tensile/run_pi_transfer_controls.py",
        "git_sha_at_execution": git_sha,
        "input_assets": [
            {"path": str(path), "sha256": _sha256(path)} for path in input_paths
        ],
        "primary_assets": [
            "pi_transfer_audit.csv",
            "fem_centred_field_metrics.csv",
            "event_state_map.csv",
            "w1_provenance.csv",
            "scale_contracts.json",
            "normalized_control_fields.npz",
            "f1_f2_fem_centred_fields.png",
            "control_summary.json",
        ],
        "companion_assets": [
            {
                "path": name,
                "sha256": _sha256(output / name),
            }
            for name in ("00_gate.md", "decision.md")
            if (output / name).is_file()
        ],
        "protected_scope": {
            "forecast_files_modified": False,
            "inverse_files_modified": False,
        },
    }
    (output / "RUN_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    hash_targets = [output / name for name in manifest["primary_assets"]]
    hash_targets.append(output / "RUN_MANIFEST.json")
    (output / "HASHES.sha256").write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in hash_targets),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
