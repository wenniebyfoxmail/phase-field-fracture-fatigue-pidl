#!/usr/bin/env python3
"""Reusable local crack-tip diagnostics for the femlike irreversible-penalty case.

Default inputs are the current ``femlike_irr_penalty_b70cdf3`` archive and the
latest quiet FEM projected state export.  The script reads existing post-hoc
PIDL step fields, projects the two PIDL triangles associated with each FEM
quadrilateral onto the FEM element grid, and writes a compact crack-tip
diagnostic package under the case ``analysis/`` directory.

State convention used here is explicit and intentionally duplicated in the
outputs:

* state0 is the true unloaded prehistory, not PIDL step 0.
* C1 retained substeps map to PIDL steps 0..4.
* C1 peak is PIDL step 3.
* C1 unload is PIDL step 4.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import h5py
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]

DEFAULT_CASE = (
    PROJECT_ROOT
    / "local_archive/after_strict_setting_alignment/pidl_result"
    / "Alignment_check2_cyclic/PIDL_cyclic_012/cases"
    / "femlike_irr_penalty_b70cdf3_20260626"
)
DEFAULT_FEM_DIR = (
    PROJECT_ROOT
    / "local_archive/after_strict_setting_alignment/fem"
    / "FEM_cyclic_u012_projected_quiet_20260627_MAT_ONLY"
)
DEFAULT_FEM_GEOMETRY_DIR = (
    PROJECT_ROOT
    / "local_archive/after_strict_setting_alignment/fem"
    / "Alignment_check2_cyclic/FEM cyclic 012/cases/standard/raw_data"
    / "state_field_exports/latest_align_soft_hist0_state_field_export_20260608"
)


@dataclass(frozen=True)
class StateSpec:
    order: int
    state: str
    fem_label: str
    cycle: int
    fem_step: int
    load_factor: float
    pidl_step: int | None
    note: str


STATE_SEQUENCE: tuple[StateSpec, ...] = (
    StateSpec(
        0,
        "state0_initial_unloaded_prehistory",
        "state0_initial_unloaded_prehistory",
        0,
        0,
        0.0,
        None,
        "true prehistory; no PIDL saved step",
    ),
    StateSpec(1, "c1_step1_load_0.25", "c1_step1", 1, 1, 0.25, 0, "PIDL C1 retained substep 0"),
    StateSpec(2, "c1_step2_load_0.50", "c1_step2", 1, 2, 0.50, 1, "PIDL C1 retained substep 1"),
    StateSpec(3, "c1_step3_load_0.75", "c1_step3", 1, 3, 0.75, 2, "PIDL C1 retained substep 2"),
    StateSpec(4, "c1_peak_load_1.00", "c1_peak", 1, 4, 1.00, 3, "C1 peak is PIDL step 3"),
    StateSpec(5, "c1_unloaded_load_0.00", "c1_unloaded", 1, 5, 0.00, 4, "C1 unload is PIDL step 4"),
)


@dataclass(frozen=True)
class FieldSpec:
    key: str
    csv_label: str
    fem_name: str | None
    pidl_name: str | None
    plot_label: str
    residual_mode: str = "raw"


FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec("damage_alpha", "damage_alpha", "d_elem", "alpha_elem", "damage alpha"),
    FieldSpec("history_fatigue", "history_fatigue", "alpha_bar_elem", "hist_fat_elem", "history / alpha_bar"),
    FieldSpec(
        "delta_alpha_bar_current_step",
        "delta_alpha_bar_current_step",
        None,
        "delta_alpha_bar_input_elem",
        "current-step delta alpha_bar",
    ),
    FieldSpec("f_fatigue", "f_fatigue", "f_fatigue_elem", "f_fatigue_elem", "fatigue degradation f"),
    FieldSpec("rawY", "rawY", "psi_plus_elem", "psi_raw_elem", "raw Y = undegraded psi+", "logratio"),
    FieldSpec("activeY", "activeY", "g_psi_plus_elem", "psi_history_driver_elem", "active Y = g psi+", "logratio"),
    FieldSpec("g_alpha", "g_alpha", "g_stiffness_elem", "g_alpha_elem", "g(alpha)"),
)
FIELD_BY_KEY = {field.key: field for field in FIELDS}


PLOT_COMPARE_FIELDS = ("delta_alpha_bar_current_step", "rawY", "history_fatigue")
SELECTION_STATE = "c1_peak_load_1.00"
SELECTION_FIELD = "delta_alpha_bar_current_step"


def np_flat(values: Any) -> np.ndarray:
    return np.asarray(values, dtype=float).reshape(-1)


def scalar_or_blank(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float) and not np.isfinite(value):
        return ""
    return value


def finite_percentile(values: np.ndarray, q: float, fallback: float = 1.0) -> float:
    vals = np.asarray(values, dtype=float)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return fallback
    return float(np.nanpercentile(vals, q))


def safe_weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    vals = np_flat(values)
    w = np_flat(weights)
    mask = np.isfinite(vals) & np.isfinite(w) & (w > 0.0)
    if not np.any(mask):
        return float("nan")
    return float(np.sum(vals[mask] * w[mask]) / np.sum(w[mask]))


def safe_nan_stat(values: np.ndarray, stat: str) -> float:
    vals = np.asarray(values, dtype=float)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return float("nan")
    if stat == "min":
        return float(np.nanmin(vals))
    if stat == "max":
        return float(np.nanmax(vals))
    if stat == "mean":
        return float(np.nanmean(vals))
    if stat == "std":
        return float(np.nanstd(vals))
    raise ValueError(stat)


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        return {key: np.asarray(data[key]) for key in data.files}


def find_single_mat(fem_dir: Path) -> Path:
    candidates = [
        fem_dir / "latest_align_soft_hist0_state_fields.mat",
        *sorted(fem_dir.glob("*state_fields*.mat")),
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(f"No FEM state-fields .mat file found under {fem_dir}")


def find_single_index(fem_dir: Path) -> Path:
    candidates = [
        fem_dir / "latest_align_soft_hist0_state_index.csv",
        *sorted(fem_dir.glob("*state_index*.csv")),
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(f"No FEM state-index CSV found under {fem_dir}")


def load_fem_hdf5(fem_dir: Path) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    mat_path = find_single_mat(fem_dir)
    index_path = find_single_index(fem_dir)
    index = pd.read_csv(index_path)
    data: dict[str, np.ndarray] = {
        "_mat_path": np.asarray(str(mat_path)),
        "_index_path": np.asarray(str(index_path)),
    }
    with h5py.File(mat_path, "r") as handle:
        data["centroids"] = np.asarray(handle["element_centroids"], dtype=float).T
        data["area"] = np.asarray(handle["element_area"], dtype=float).reshape(-1)
        fields = handle["fields"]
        for name in fields:
            if isinstance(fields[name], h5py.Dataset):
                data[name] = np.asarray(fields[name])
    return index, data


def load_fem_geometry(geometry_dir: Path) -> dict[str, np.ndarray]:
    _, geom = load_fem_hdf5(geometry_dir)
    return {
        "centroids": np.asarray(geom["centroids"], dtype=float),
        "area": np.asarray(geom["area"], dtype=float),
        "_geometry_source": np.asarray(str(find_single_mat(geometry_dir))),
    }


def audit_state_file_from_manifest(fem_dir: Path, row: pd.Series) -> Path:
    raw_file = str(row["file"]).replace("\\", "/")
    name = Path(raw_file).name
    path = fem_dir / "audit_states" / name
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def manifest_row_for_state(manifest: pd.DataFrame, spec: StateSpec) -> pd.Series:
    if spec.order == 0:
        hits = manifest[manifest["state_label"] == "state0_initial_unloaded_prehistory"]
    else:
        hits = manifest[(manifest["cycle"] == spec.cycle) & (manifest["step"] == spec.fem_step)]
    if hits.empty:
        raise KeyError(f"MAT-only manifest row not found for {spec.state}")
    return hits.iloc[0]


def h5_scalar(path: Path, dataset: str) -> np.ndarray:
    with h5py.File(path, "r") as handle:
        values = np.asarray(handle[dataset], dtype=float)
    return values.reshape(-1)


def fem_g_from_mat_state(path: Path, damage: np.ndarray) -> np.ndarray:
    raw_y = h5_scalar(path, "element/psi_raw_elem")
    active_y = h5_scalar(path, "element/psi_active_elem")
    fallback = (1.0 - np.asarray(damage, dtype=float)) ** 2
    out = np.full_like(fallback, np.nan, dtype=float)
    mask = np.isfinite(raw_y) & (np.abs(raw_y) > 1e-30) & np.isfinite(active_y)
    out[mask] = active_y[mask] / raw_y[mask]
    out[~mask] = fallback[~mask]
    return out


def load_fem_mat_only(fem_dir: Path, geometry_dir: Path) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    manifest_path = fem_dir / "state_manifest.csv"
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    manifest = pd.read_csv(manifest_path)
    geom = load_fem_geometry(geometry_dir)
    rows: list[dict[str, Any]] = []
    field_lists: dict[str, list[np.ndarray]] = {
        "d_elem": [],
        "alpha_bar_elem": [],
        "f_fatigue_elem": [],
        "psi_plus_elem": [],
        "g_psi_plus_elem": [],
        "g_stiffness_elem": [],
    }
    for spec in STATE_SEQUENCE:
        row = manifest_row_for_state(manifest, spec)
        path = audit_state_file_from_manifest(fem_dir, row)
        damage = h5_scalar(path, "element/d_elem_clipped")
        raw_y = h5_scalar(path, "element/psi_raw_elem")
        active_y = h5_scalar(path, "element/psi_active_elem")
        field_lists["d_elem"].append(damage)
        field_lists["alpha_bar_elem"].append(h5_scalar(path, "element/alpha_bar_elem"))
        field_lists["f_fatigue_elem"].append(h5_scalar(path, "element/f_alpha_elem"))
        field_lists["psi_plus_elem"].append(raw_y)
        field_lists["g_psi_plus_elem"].append(active_y)
        field_lists["g_stiffness_elem"].append(fem_g_from_mat_state(path, damage))
        rows.append(
            {
                "state_label": spec.fem_label,
                "source_state_label": row["state_label"],
                "cycle": int(row["cycle"]),
                "step": int(row["step"]),
                "load_factor": spec.load_factor,
                "uy": float(row["uy"]),
                "file": path.name,
            }
        )

    data: dict[str, np.ndarray] = {
        "centroids": geom["centroids"],
        "area": geom["area"],
        "_mat_path": np.asarray(str(fem_dir)),
        "_index_path": np.asarray(str(manifest_path)),
        "_geometry_source": geom["_geometry_source"],
        "_field_source": np.asarray(str(fem_dir)),
    }
    for key, values in field_lists.items():
        data[key] = np.stack(values, axis=0)[:, None, :]
    return pd.DataFrame(rows), data


def load_fem(fem_dir: Path, geometry_dir: Path) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    if (fem_dir / "audit_states").exists() and (fem_dir / "state_manifest.csv").exists():
        return load_fem_mat_only(fem_dir, geometry_dir)
    return load_fem_hdf5(fem_dir)


def fem_state_row(fem_index: pd.DataFrame, label: str) -> int:
    hits = fem_index.index[fem_index["state_label"] == label].tolist()
    if not hits:
        raise KeyError(f"FEM state label not found: {label}")
    return int(hits[0])


def fem_scalar(fem: dict[str, np.ndarray], key: str, state_i: int) -> np.ndarray:
    arr = np.asarray(fem[key])
    if arr.ndim == 3 and arr.shape[1] == 1:
        return np.asarray(arr[state_i, 0, :], dtype=float)
    if arr.ndim == 2 and arr.shape[0] == 1:
        return np.asarray(arr[0, state_i], dtype=float).reshape(1)
    raise ValueError(f"Unexpected FEM scalar shape for {key}: {arr.shape}")


def discover_pidl_step_dir(case_dir: Path) -> Path:
    preferred = [
        case_dir / "analysis/new_fem_projected_quiet_20260627_C1_C2/pidl_posthoc_step_fields",
        case_dir / "analysis/healthcheck_C1_all_steps/pidl_posthoc_step_fields",
    ]
    candidates = [path for path in preferred if path.exists()]
    candidates.extend(sorted((case_dir / "analysis").glob("**/pidl_posthoc_step_fields"), key=lambda p: p.stat().st_mtime, reverse=True))
    for path in candidates:
        if all((path / f"element_fields_step_{step:04d}.npz").exists() for step in range(5)):
            return path
    raise FileNotFoundError(
        "Could not find PIDL posthoc step fields for steps 0..4. "
        "Pass --pidl-step-dir to a directory containing element_fields_step_0000..0004.npz."
    )


def discover_initial_pidl(case_dir: Path) -> Path:
    preferred = case_dir / "analysis/healthcheck_C0_C1_C60/posthoc_true_initial_state/pidl_baseline_initial_state_fields.npz"
    if preferred.exists():
        return preferred
    candidates = sorted(
        (case_dir / "analysis").glob("**/pidl_baseline_initial_state_fields.npz"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if candidates:
        return candidates[0]
    raise FileNotFoundError(
        "Could not find true PIDL state0 prehistory export. "
        "Pass --initial-pidl to pidl_baseline_initial_state_fields.npz."
    )


def load_pidl_steps(step_dir: Path) -> dict[int, dict[str, np.ndarray]]:
    out: dict[int, dict[str, np.ndarray]] = {}
    for step in range(5):
        path = step_dir / f"element_fields_step_{step:04d}.npz"
        if not path.exists():
            raise FileNotFoundError(path)
        out[step] = load_npz(path)
    return out


def build_projection(
    pidl_centroids_centered: np.ndarray,
    pidl_area: np.ndarray,
    fem_centroids: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    pidl_centroids_fem = np.asarray(pidl_centroids_centered, dtype=float) + 0.5
    tree = cKDTree(fem_centroids)
    distances, nearest = tree.query(pidl_centroids_fem, k=1)
    counts = np.bincount(nearest, minlength=fem_centroids.shape[0])
    summary = {
        "n_pidl_triangles": int(len(nearest)),
        "n_fem_elements": int(fem_centroids.shape[0]),
        "min_pidl_per_fem": int(counts.min()),
        "max_pidl_per_fem": int(counts.max()),
        "mean_pidl_per_fem": float(counts.mean()),
        "nearest_distance_max": float(np.max(distances)),
        "nearest_distance_p99": float(np.percentile(distances, 99)),
        "total_pidl_area": float(np.sum(pidl_area)),
    }
    return nearest, distances, summary


def project_pidl_to_fem(values: np.ndarray, areas: np.ndarray, nearest: np.ndarray, n_fem: int) -> np.ndarray:
    vals = np_flat(values)
    weights = np_flat(areas)
    num = np.bincount(nearest, weights=vals * weights, minlength=n_fem)
    den = np.bincount(nearest, weights=weights, minlength=n_fem)
    out = np.full(n_fem, np.nan, dtype=float)
    mask = den > 0.0
    out[mask] = num[mask] / den[mask]
    return out


def state_mapping_rows(fem_index: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in STATE_SEQUENCE:
        rows.append(
            {
                "order": spec.order,
                "state": spec.state,
                "fem_label": spec.fem_label,
                "fem_row": fem_state_row(fem_index, spec.fem_label),
                "cycle": spec.cycle,
                "fem_step": spec.fem_step,
                "load_factor": spec.load_factor,
                "pidl_step": "" if spec.pidl_step is None else spec.pidl_step,
                "mapping_note": spec.note,
            }
        )
    return rows


def build_fem_state_fields(
    fem_index: pd.DataFrame,
    fem: dict[str, np.ndarray],
) -> dict[str, dict[str, np.ndarray]]:
    out: dict[str, dict[str, np.ndarray]] = {}
    prev_history: np.ndarray | None = None
    for spec in STATE_SEQUENCE:
        state_i = fem_state_row(fem_index, spec.fem_label)
        history = fem_scalar(fem, "alpha_bar_elem", state_i)
        if prev_history is None:
            delta = np.zeros_like(history)
        else:
            delta = np.maximum(history - prev_history, 0.0)
        out[spec.state] = {
            "damage_alpha": fem_scalar(fem, "d_elem", state_i),
            "history_fatigue": history,
            "delta_alpha_bar_current_step": delta,
            "f_fatigue": fem_scalar(fem, "f_fatigue_elem", state_i),
            "rawY": fem_scalar(fem, "psi_plus_elem", state_i),
            "activeY": fem_scalar(fem, "g_psi_plus_elem", state_i),
            "g_alpha": fem_scalar(fem, "g_stiffness_elem", state_i),
        }
        prev_history = history
    return out


def pidl_raw_field_dict(step_data: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {
        "damage_alpha": np_flat(step_data["alpha_elem"]),
        "history_fatigue": np_flat(step_data["hist_fat_elem"]),
        "delta_alpha_bar_current_step": np_flat(step_data["delta_alpha_bar_input_elem"]),
        "f_fatigue": np_flat(step_data["f_fatigue_elem"]),
        "rawY": np_flat(step_data["psi_raw_elem"]),
        "activeY": np_flat(step_data["psi_history_driver_elem"]),
        "g_alpha": np_flat(step_data["g_alpha_elem"]),
    }


def build_pidl_state_fields(
    pidl_steps: dict[int, dict[str, np.ndarray]],
    initial_pidl: dict[str, np.ndarray],
    fem_centroids: np.ndarray,
) -> tuple[
    dict[str, dict[str, np.ndarray]],
    dict[str, dict[str, np.ndarray]],
    dict[str, np.ndarray],
    dict[str, Any],
]:
    n_fem = fem_centroids.shape[0]
    step0 = pidl_steps[0]
    step_centroids = np.column_stack([np_flat(step0["elem_x"]), np_flat(step0["elem_y"])])
    step_area = np_flat(step0["area_elem"])
    nearest, distances, projection_summary = build_projection(step_centroids, step_area, fem_centroids)

    init_centroids = np.asarray(initial_pidl["element_centroids"], dtype=float)
    init_area = np_flat(initial_pidl["element_area"])
    nearest_init, init_distances, init_summary = build_projection(init_centroids, init_area, fem_centroids)
    projection_summary["state0_nearest_distance_max"] = init_summary["nearest_distance_max"]
    projection_summary["state0_nearest_distance_p99"] = init_summary["nearest_distance_p99"]

    projected: dict[str, dict[str, np.ndarray]] = {}
    raw_by_state: dict[str, dict[str, np.ndarray]] = {}

    init_raw = {
        "damage_alpha": np_flat(initial_pidl["hist_alpha_init_elem"]),
        "history_fatigue": np_flat(initial_pidl["hist_fat0_elem"]),
        "delta_alpha_bar_current_step": np.zeros_like(init_area, dtype=float),
        "f_fatigue": np_flat(initial_pidl["f_fatigue0_elem"]),
        "rawY": np.zeros_like(init_area, dtype=float),
        "activeY": np.zeros_like(init_area, dtype=float),
        "g_alpha": np.full_like(init_area, np.nan, dtype=float),
    }
    projected[STATE_SEQUENCE[0].state] = {
        key: project_pidl_to_fem(value, init_area, nearest_init, n_fem)
        for key, value in init_raw.items()
    }
    raw_by_state[STATE_SEQUENCE[0].state] = init_raw

    for spec in STATE_SEQUENCE[1:]:
        assert spec.pidl_step is not None
        raw = pidl_raw_field_dict(pidl_steps[spec.pidl_step])
        area = np_flat(pidl_steps[spec.pidl_step]["area_elem"])
        projected[spec.state] = {
            key: project_pidl_to_fem(value, area, nearest, n_fem)
            for key, value in raw.items()
        }
        raw_by_state[spec.state] = raw

    projection = {
        "regular_nearest": nearest,
        "regular_distances": distances,
        "regular_area": step_area,
        "regular_centroids_shifted": step_centroids + 0.5,
        "state0_nearest": nearest_init,
        "state0_distances": init_distances,
        "state0_area": init_area,
        "state0_centroids_shifted": init_centroids + 0.5,
    }
    return projected, raw_by_state, projection, projection_summary


def select_top_elements(
    fem_fields: dict[str, dict[str, np.ndarray]],
    top_n: int,
) -> np.ndarray:
    values = np_flat(fem_fields[SELECTION_STATE][SELECTION_FIELD])
    finite = np.where(np.isfinite(values))[0]
    if finite.size == 0:
        raise ValueError(f"No finite values in {SELECTION_STATE}/{SELECTION_FIELD}")
    order = finite[np.argsort(values[finite])[::-1]]
    return order[:top_n]


def nearest_region(fem_centroids: np.ndarray, center_elem: int, n: int) -> np.ndarray:
    center = fem_centroids[center_elem]
    distances = np.linalg.norm(fem_centroids - center[None, :], axis=1)
    return np.argsort(distances)[:n]


def logratio(pidl_value: float, fem_value: float) -> float:
    if not np.isfinite(pidl_value) or not np.isfinite(fem_value):
        return float("nan")
    return float(np.log10((max(pidl_value, 0.0) + 1e-12) / (max(fem_value, 0.0) + 1e-12)))


def element_state_row(
    selection_name: str,
    rank: int,
    fem_elem: int,
    spec: StateSpec,
    fem_centroids: np.ndarray,
    fem_fields: dict[str, dict[str, np.ndarray]],
    pidl_fields: dict[str, dict[str, np.ndarray]],
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "selection": selection_name,
        "rank": rank,
        "fem_elem_0based": int(fem_elem),
        "fem_elem_1based": int(fem_elem + 1),
        "x": float(fem_centroids[fem_elem, 0]),
        "y": float(fem_centroids[fem_elem, 1]),
        "state_order": spec.order,
        "state": spec.state,
        "cycle": spec.cycle,
        "fem_step": spec.fem_step,
        "load_factor": spec.load_factor,
        "pidl_step": "" if spec.pidl_step is None else int(spec.pidl_step),
    }
    for field in FIELDS:
        fv = float(fem_fields[spec.state][field.key][fem_elem])
        pv = float(pidl_fields[spec.state][field.key][fem_elem])
        row[f"fem_{field.csv_label}"] = fv
        row[f"pidl_{field.csv_label}"] = pv
        row[f"diff_{field.csv_label}_pidl_minus_fem"] = pv - fv if np.isfinite(pv) and np.isfinite(fv) else float("nan")
        if field.residual_mode == "logratio":
            row[f"log10_pidl_over_fem_{field.csv_label}"] = logratio(pv, fv)
    return row


def make_state_sequence_rows(
    top_elements: np.ndarray,
    fem_centroids: np.ndarray,
    fem_fields: dict[str, dict[str, np.ndarray]],
    pidl_fields: dict[str, dict[str, np.ndarray]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rank, elem in enumerate(top_elements, start=1):
        for spec in STATE_SEQUENCE:
            rows.append(
                element_state_row(
                    "top_by_FEM_C1_peak_delta",
                    rank,
                    int(elem),
                    spec,
                    fem_centroids,
                    fem_fields,
                    pidl_fields,
                )
            )
    return rows


def make_top_compact_rows(
    top_elements: np.ndarray,
    fem_centroids: np.ndarray,
    fem_fields: dict[str, dict[str, np.ndarray]],
    pidl_fields: dict[str, dict[str, np.ndarray]],
) -> list[dict[str, Any]]:
    peak_spec = next(spec for spec in STATE_SEQUENCE if spec.state == SELECTION_STATE)
    rows: list[dict[str, Any]] = []
    for rank, elem in enumerate(top_elements, start=1):
        row = element_state_row(
            "top_by_FEM_C1_peak_delta",
            rank,
            int(elem),
            peak_spec,
            fem_centroids,
            fem_fields,
            pidl_fields,
        )
        rows.append(row)
    return rows


def make_underlying_triangle_rows(
    top_elements: np.ndarray,
    fem_centroids: np.ndarray,
    raw_by_state: dict[str, dict[str, np.ndarray]],
    projection: dict[str, np.ndarray],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    raw = raw_by_state[SELECTION_STATE]
    nearest = np.asarray(projection["regular_nearest"], dtype=int)
    centroids = np.asarray(projection["regular_centroids_shifted"], dtype=float)
    for rank, elem in enumerate(top_elements, start=1):
        tri_indices = np.where(nearest == elem)[0]
        for tri in tri_indices:
            row: dict[str, Any] = {
                "rank": rank,
                "fem_elem_0based": int(elem),
                "fem_elem_1based": int(elem + 1),
                "pidl_triangle_index": int(tri),
                "fem_x": float(fem_centroids[elem, 0]),
                "fem_y": float(fem_centroids[elem, 1]),
                "pidl_x_shifted": float(centroids[tri, 0]),
                "pidl_y_shifted": float(centroids[tri, 1]),
            }
            for field in FIELDS:
                row[f"pidl_{field.csv_label}"] = float(raw[field.key][tri])
            rows.append(row)
    return rows


def make_subtriangle_spread_rows(
    top_elements: np.ndarray,
    fem_fields: dict[str, dict[str, np.ndarray]],
    pidl_fields: dict[str, dict[str, np.ndarray]],
    raw_by_state: dict[str, dict[str, np.ndarray]],
    projection: dict[str, np.ndarray],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    nearest_regular = np.asarray(projection["regular_nearest"], dtype=int)
    nearest_state0 = np.asarray(projection["state0_nearest"], dtype=int)
    area_regular = np_flat(projection["regular_area"])
    area_state0 = np_flat(projection["state0_area"])
    for rank, elem in enumerate(top_elements, start=1):
        for spec in STATE_SEQUENCE:
            if spec.pidl_step is None:
                nearest = nearest_state0
                areas = area_state0
            else:
                nearest = nearest_regular
                areas = area_regular
            tri_indices = np.where(nearest == elem)[0]
            tri_areas = areas[tri_indices]
            for field in FIELDS:
                tri_values = raw_by_state[spec.state][field.key][tri_indices]
                fem_value = float(fem_fields[spec.state][field.key][elem])
                pidl_projected = float(pidl_fields[spec.state][field.key][elem])
                rows.append(
                    {
                        "selection": "top_by_FEM_C1_peak_delta",
                        "rank": rank,
                        "fem_elem_0based": int(elem),
                        "fem_elem_1based": int(elem + 1),
                        "state_order": spec.order,
                        "state": spec.state,
                        "pidl_step": "" if spec.pidl_step is None else int(spec.pidl_step),
                        "field": field.csv_label,
                        "n_triangles": int(len(tri_indices)),
                        "fem_value": fem_value,
                        "pidl_projected_value": pidl_projected,
                        "pidl_tri_area_weighted_mean": safe_weighted_mean(tri_values, tri_areas),
                        "pidl_tri_mean": safe_nan_stat(tri_values, "mean"),
                        "pidl_tri_std": safe_nan_stat(tri_values, "std"),
                        "pidl_tri_min": safe_nan_stat(tri_values, "min"),
                        "pidl_tri_max": safe_nan_stat(tri_values, "max"),
                        "pidl_tri_spread_max_minus_min": safe_nan_stat(tri_values, "max") - safe_nan_stat(tri_values, "min"),
                    }
                )
    return rows


def make_region_aggregate_rows(
    regions: dict[str, np.ndarray],
    fem_area: np.ndarray,
    fem_fields: dict[str, dict[str, np.ndarray]],
    pidl_fields: dict[str, dict[str, np.ndarray]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for region_name, elems in regions.items():
        elem_idx = np.asarray(elems, dtype=int)
        weights = np_flat(fem_area)[elem_idx]
        for spec in STATE_SEQUENCE:
            row: dict[str, Any] = {
                "region": region_name,
                "n_elements": int(len(elem_idx)),
                "state_order": spec.order,
                "state": spec.state,
                "cycle": spec.cycle,
                "fem_step": spec.fem_step,
                "pidl_step": "" if spec.pidl_step is None else int(spec.pidl_step),
                "load_factor": spec.load_factor,
            }
            for field in FIELDS:
                fv = fem_fields[spec.state][field.key][elem_idx]
                pv = pidl_fields[spec.state][field.key][elem_idx]
                diff = pv - fv
                row[f"fem_{field.csv_label}_wmean"] = safe_weighted_mean(fv, weights)
                row[f"pidl_{field.csv_label}_wmean"] = safe_weighted_mean(pv, weights)
                row[f"absdiff_{field.csv_label}_wmean"] = safe_weighted_mean(np.abs(diff), weights)
                row[f"signeddiff_{field.csv_label}_wmean"] = safe_weighted_mean(diff, weights)
                row[f"fem_{field.csv_label}_max"] = safe_nan_stat(fv, "max")
                row[f"pidl_{field.csv_label}_max"] = safe_nan_stat(pv, "max")
                row[f"fem_{field.csv_label}_min"] = safe_nan_stat(fv, "min")
                row[f"pidl_{field.csv_label}_min"] = safe_nan_stat(pv, "min")
                if field.residual_mode == "logratio":
                    ratios = np.log10((np.maximum(pv, 0.0) + 1e-12) / (np.maximum(fv, 0.0) + 1e-12))
                    row[f"logratio_abs_{field.csv_label}_wmean"] = safe_weighted_mean(np.abs(ratios), weights)
            rows.append(row)
    return rows


def robust_lims(values: list[np.ndarray], lower_q: float = 1.0, upper_q: float = 99.0) -> tuple[float, float]:
    finite = []
    for arr in values:
        vals = np.asarray(arr, dtype=float)
        vals = vals[np.isfinite(vals)]
        if vals.size:
            finite.append(vals)
    if not finite:
        return 0.0, 1.0
    all_values = np.concatenate(finite)
    vmin = float(np.nanpercentile(all_values, lower_q))
    vmax = float(np.nanpercentile(all_values, upper_q))
    if not np.isfinite(vmin) or not np.isfinite(vmax) or abs(vmax - vmin) < 1e-14:
        center = float(np.nanmean(all_values)) if all_values.size else 0.0
        return center - 0.5, center + 0.5
    return vmin, vmax


def centered_limit(values: list[np.ndarray], q: float = 99.0) -> float:
    finite = []
    for arr in values:
        vals = np.asarray(arr, dtype=float)
        vals = vals[np.isfinite(vals)]
        if vals.size:
            finite.append(np.abs(vals))
    if not finite:
        return 1.0
    limit = float(np.nanpercentile(np.concatenate(finite), q))
    return max(limit, 1e-12)


def plot_cracktip_comparison_zoom(
    out_path: Path,
    top_elements: np.ndarray,
    fem_centroids: np.ndarray,
    fem_fields: dict[str, dict[str, np.ndarray]],
    pidl_fields: dict[str, dict[str, np.ndarray]],
    zoom_half_width: float,
) -> None:
    center = fem_centroids[top_elements[0]]
    x = fem_centroids[:, 0]
    y = fem_centroids[:, 1]
    mask = (np.abs(x - center[0]) <= zoom_half_width) & (np.abs(y - center[1]) <= zoom_half_width)
    if np.count_nonzero(mask) < 10:
        radius = np.linalg.norm(fem_centroids - center[None, :], axis=1)
        mask[np.argsort(radius)[:200]] = True

    fig, axes = plt.subplots(
        len(PLOT_COMPARE_FIELDS),
        3,
        figsize=(11.8, 8.8),
        constrained_layout=True,
    )
    for row_i, field_key in enumerate(PLOT_COMPARE_FIELDS):
        field = FIELD_BY_KEY[field_key]
        fem_vals = np_flat(fem_fields[SELECTION_STATE][field_key])
        pidl_vals = np_flat(pidl_fields[SELECTION_STATE][field_key])
        if field.residual_mode == "logratio":
            fem_plot = np.log10(np.maximum(fem_vals, 0.0) + 1e-12)
            pidl_plot = np.log10(np.maximum(pidl_vals, 0.0) + 1e-12)
            residual = np.log10((np.maximum(pidl_vals, 0.0) + 1e-12) / (np.maximum(fem_vals, 0.0) + 1e-12))
            first_title = f"FEM log10 {field.plot_label}"
            second_title = f"PIDL log10 {field.plot_label}"
            third_title = "log10(PIDL/FEM)"
        else:
            fem_plot = fem_vals
            pidl_plot = pidl_vals
            residual = pidl_vals - fem_vals
            first_title = f"FEM {field.plot_label}"
            second_title = f"PIDL {field.plot_label}"
            third_title = "PIDL - FEM"

        vmin, vmax = robust_lims([fem_plot[mask], pidl_plot[mask]])
        rlim = centered_limit([residual[mask]])
        panels = [
            (fem_plot, first_title, "viridis", vmin, vmax),
            (pidl_plot, second_title, "viridis", vmin, vmax),
            (residual, third_title, "RdBu_r", -rlim, rlim),
        ]
        for col_i, (values, title, cmap, panel_vmin, panel_vmax) in enumerate(panels):
            ax = axes[row_i, col_i]
            scatter = ax.scatter(
                x[mask],
                y[mask],
                c=values[mask],
                s=8.0,
                cmap=cmap,
                vmin=panel_vmin,
                vmax=panel_vmax,
                linewidths=0,
                rasterized=True,
            )
            ax.scatter(
                x[top_elements],
                y[top_elements],
                s=32,
                facecolors="none",
                edgecolors="black",
                linewidths=0.75,
            )
            for rank, elem in enumerate(top_elements, start=1):
                if rank > 12:
                    break
                ax.text(x[elem], y[elem], str(rank), fontsize=5.5, ha="center", va="center", color="black")
            ax.set_aspect("equal", adjustable="box")
            ax.set_xlim(center[0] - zoom_half_width, center[0] + zoom_half_width)
            ax.set_ylim(center[1] - zoom_half_width, center[1] + zoom_half_width)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title(title, fontsize=9)
            fig.colorbar(scatter, ax=ax, fraction=0.046, pad=0.01)

    fig.suptitle(
        "Crack-tip C1 peak zoom: FEM vs PIDL-projected delta / rawY / history "
        "(C1 peak -> PIDL step 3)",
        fontsize=11,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=240)
    plt.close(fig)


def plot_top_element_sequence_lines(
    out_path: Path,
    top_elements: np.ndarray,
    fem_fields: dict[str, dict[str, np.ndarray]],
    pidl_fields: dict[str, dict[str, np.ndarray]],
    n_lines: int,
) -> None:
    fields = ("delta_alpha_bar_current_step", "rawY", "history_fatigue", "damage_alpha")
    states = [spec.state for spec in STATE_SEQUENCE]
    x = np.arange(len(states))
    labels = ["state0", "p0 0.25", "p1 0.50", "p2 0.75", "peak p3", "unload p4"]
    colors = plt.cm.tab10(np.linspace(0, 1, max(n_lines, 1)))
    fig, axes = plt.subplots(len(fields), 1, figsize=(11.6, 10.0), sharex=True, constrained_layout=True)
    elems_to_plot = top_elements[:n_lines]
    for ax, field_key in zip(axes, fields):
        field = FIELD_BY_KEY[field_key]
        for i, elem in enumerate(elems_to_plot):
            fem_vals = [float(fem_fields[state][field_key][elem]) for state in states]
            pidl_vals = [float(pidl_fields[state][field_key][elem]) for state in states]
            ax.plot(x, fem_vals, color=colors[i], marker="o", lw=1.5, label=f"rank {i + 1} FEM")
            ax.plot(x, pidl_vals, color=colors[i], marker="s", lw=1.3, ls="--", label=f"rank {i + 1} PIDL")
        ax.set_ylabel(field.plot_label, fontsize=9)
        ax.grid(True, color="0.88", lw=0.7)
    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels(labels, rotation=20, ha="right")
    axes[0].set_title("Top crack-tip element state sequences with explicit C1 PIDL step mapping", fontsize=11)
    handles, labels_all = axes[0].get_legend_handles_labels()
    axes[0].legend(handles[: min(len(handles), 12)], labels_all[: min(len(labels_all), 12)], fontsize=7, ncol=2)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def write_readme(
    out_dir: Path,
    case_dir: Path,
    fem_dir: Path,
    fem_geometry_dir: Path,
    pidl_step_dir: Path,
    initial_pidl_path: Path,
    projection_summary: dict[str, Any],
    files: dict[str, Path],
    top_n: int,
    nearest_n: int,
) -> None:
    lines = [
        "# Posthoc crack-tip local diagnostics",
        "",
        "This package was generated by `posthoc_cracktip_local_diagnostics.py`.",
        "",
        "Inputs:",
        f"- PIDL case: `{case_dir}`",
        f"- FEM quiet projected state export: `{fem_dir}`",
        f"- FEM geometry source: `{fem_geometry_dir}`",
        f"- PIDL C1 step fields: `{pidl_step_dir}`",
        f"- PIDL true state0 prehistory: `{initial_pidl_path}`",
        "",
        "Coordinate convention:",
        "- FEM element centroids are in the FEM `[0, 1]` frame.",
        "- PIDL element centroids are shifted by `+0.5` before nearest-element projection.",
        "- PIDL triangle values are area-averaged onto FEM elements.",
        "",
        "State mapping:",
        "- `state0_initial_unloaded_prehistory`: true unloaded prehistory; no PIDL saved step.",
        "- `c1_step1_load_0.25`: PIDL step 0.",
        "- `c1_step2_load_0.50`: PIDL step 1.",
        "- `c1_step3_load_0.75`: PIDL step 2.",
        "- `c1_peak_load_1.00`: PIDL step 3.",
        "- `c1_unloaded_load_0.00`: PIDL step 4.",
        "",
        f"Selection rule: top {top_n} FEM elements by `delta_alpha_bar_current_step` at C1 peak.",
        f"Region aggregate companion: nearest {nearest_n} FEM elements to the top selected element.",
        "",
        "Projection summary:",
        "```json",
        json.dumps(projection_summary, indent=2),
        "```",
        "",
        "Generated files:",
    ]
    for label, path in files.items():
        lines.append(f"- {label}: `{path.relative_to(out_dir)}`")
    (out_dir / "README_cracktip_local_diagnostics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, default=DEFAULT_CASE, help="PIDL case folder.")
    parser.add_argument("--fem-dir", type=Path, default=DEFAULT_FEM_DIR, help="Latest quiet FEM projected state export folder.")
    parser.add_argument("--fem-geometry-dir", type=Path, default=DEFAULT_FEM_GEOMETRY_DIR, help="FEM geometry export with element centroids/areas.")
    parser.add_argument("--pidl-step-dir", type=Path, default=None, help="Directory with element_fields_step_0000..0004.npz.")
    parser.add_argument("--initial-pidl", type=Path, default=None, help="True state0 PIDL prehistory npz.")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output analysis directory. Defaults to a new timestamped case analysis subdir.")
    parser.add_argument("--analysis-name", default=None, help="Name for the new output subdir under CASE/analysis.")
    parser.add_argument("--top-n", type=int, default=12, help="Number of top FEM crack-tip elements to export.")
    parser.add_argument("--nearest-n", type=int, default=50, help="Nearest-element region size around the top element.")
    parser.add_argument("--zoom-half-width", type=float, default=0.018, help="Half-width of the crack-tip zoom figure in FEM coordinates.")
    parser.add_argument("--plot-top-lines", type=int, default=6, help="Number of ranked elements shown in sequence-line figure.")
    parser.add_argument("--force", action="store_true", help="Allow writing into an existing output directory.")
    parser.add_argument("--dry-run", action="store_true", help="Resolve inputs and print plan without writing outputs.")
    return parser


def resolve_out_dir(args: argparse.Namespace) -> Path:
    if args.out_dir is not None:
        return args.out_dir
    if args.analysis_name:
        name = args.analysis_name
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"posthoc_cracktip_local_diagnostics_{stamp}"
    return args.case / "analysis" / name


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    case_dir = args.case.resolve()
    fem_dir = args.fem_dir.resolve()
    fem_geometry_dir = args.fem_geometry_dir.resolve()
    pidl_step_dir = (args.pidl_step_dir.resolve() if args.pidl_step_dir else discover_pidl_step_dir(case_dir).resolve())
    initial_pidl_path = (args.initial_pidl.resolve() if args.initial_pidl else discover_initial_pidl(case_dir).resolve())
    out_dir = resolve_out_dir(args).resolve()

    if args.dry_run:
        print("Resolved posthoc crack-tip diagnostics inputs:")
        print(f"  case: {case_dir}")
        print(f"  fem_dir: {fem_dir}")
        print(f"  fem_geometry_dir: {fem_geometry_dir}")
        print(f"  pidl_step_dir: {pidl_step_dir}")
        print(f"  initial_pidl: {initial_pidl_path}")
        print(f"  out_dir: {out_dir}")
        print("State mapping: state0 true prehistory; C1 PIDL steps 0..4; peak step3; unload step4.")
        return 0

    if out_dir.exists() and any(out_dir.iterdir()) and not args.force:
        raise FileExistsError(f"Output directory already exists and is not empty: {out_dir}. Use --force or choose --out-dir.")

    tables_dir = out_dir / "tables"
    figures_dir = out_dir / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    fem_index, fem = load_fem(fem_dir, fem_geometry_dir)
    pidl_steps = load_pidl_steps(pidl_step_dir)
    initial_pidl = load_npz(initial_pidl_path)

    fem_fields = build_fem_state_fields(fem_index, fem)
    pidl_fields, raw_by_state, projection, projection_summary = build_pidl_state_fields(
        pidl_steps,
        initial_pidl,
        np.asarray(fem["centroids"], dtype=float),
    )

    top_elements = select_top_elements(fem_fields, args.top_n)
    nearest_elements = nearest_region(np.asarray(fem["centroids"], dtype=float), int(top_elements[0]), args.nearest_n)
    regions = {
        "top_by_FEM_C1_peak_delta": top_elements,
        "nearest_to_top_delta_element": nearest_elements,
    }

    state_mapping_path = tables_dir / "cracktip_state_mapping_explicit.csv"
    top_compact_path = tables_dir / "cracktip_top_elements_compact.csv"
    underlying_path = tables_dir / "cracktip_underlying_pidl_triangles.csv"
    spread_path = tables_dir / "cracktip_subtriangle_spread.csv"
    sequences_path = tables_dir / "cracktip_state_sequences.csv"
    aggregates_path = tables_dir / "cracktip_region_aggregates.csv"
    projection_path = tables_dir / "projection_summary.json"

    write_csv(state_mapping_path, state_mapping_rows(fem_index))
    write_csv(top_compact_path, make_top_compact_rows(top_elements, fem["centroids"], fem_fields, pidl_fields))
    write_csv(underlying_path, make_underlying_triangle_rows(top_elements, fem["centroids"], raw_by_state, projection))
    write_csv(spread_path, make_subtriangle_spread_rows(top_elements, fem_fields, pidl_fields, raw_by_state, projection))
    write_csv(sequences_path, make_state_sequence_rows(top_elements, fem["centroids"], fem_fields, pidl_fields))
    write_csv(aggregates_path, make_region_aggregate_rows(regions, fem["area"], fem_fields, pidl_fields))
    projection_path.write_text(json.dumps(projection_summary, indent=2) + "\n", encoding="utf-8")

    zoom_path = figures_dir / "cracktip_delta_rawY_hist_comparison_zoom.png"
    sequence_fig_path = figures_dir / "cracktip_top_element_sequence_lines.png"
    plot_cracktip_comparison_zoom(
        zoom_path,
        top_elements,
        np.asarray(fem["centroids"], dtype=float),
        fem_fields,
        pidl_fields,
        args.zoom_half_width,
    )
    plot_top_element_sequence_lines(
        sequence_fig_path,
        top_elements,
        fem_fields,
        pidl_fields,
        min(args.plot_top_lines, len(top_elements)),
    )

    generated_files = {
        "state mapping": state_mapping_path,
        "top elements compact": top_compact_path,
        "underlying PIDL triangles": underlying_path,
        "subtriangle spread": spread_path,
        "state sequences": sequences_path,
        "region aggregates": aggregates_path,
        "projection summary": projection_path,
        "delta/rawY/hist zoom figure": zoom_path,
        "top element sequence-lines figure": sequence_fig_path,
    }
    write_readme(
        out_dir,
        case_dir,
        fem_dir,
        fem_geometry_dir,
        pidl_step_dir,
        initial_pidl_path,
        projection_summary,
        generated_files,
        args.top_n,
        args.nearest_n,
    )

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "case": str(case_dir),
        "fem_dir": str(fem_dir),
        "fem_geometry_dir": str(fem_geometry_dir),
        "pidl_step_dir": str(pidl_step_dir),
        "initial_pidl": str(initial_pidl_path),
        "out_dir": str(out_dir),
        "state_mapping_statement": "state0 true prehistory; C1 steps PIDL 0..4; peak step3; unload step4",
        "selection_state": SELECTION_STATE,
        "selection_field": SELECTION_FIELD,
        "top_elements_0based": [int(x) for x in top_elements],
        "top_elements_1based": [int(x + 1) for x in top_elements],
        "files": {label: str(path) for label, path in generated_files.items()},
        "readme": str(out_dir / "README_cracktip_local_diagnostics.md"),
    }
    (out_dir / "generation_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote crack-tip local diagnostics to: {out_dir}")
    print("State mapping: state0 true prehistory; C1 PIDL steps 0..4; peak step3; unload step4.")
    for label, path in generated_files.items():
        print(f"  {label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
