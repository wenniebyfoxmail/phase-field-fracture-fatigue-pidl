"""Deterministic, treatment-blind field analysis for the RRaPINN G4 pilot.

The analyzer accepts only opaque, hash-bound analysis manifests.  It never
loads producer settings, training logs, an arm map, or a treatment label.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from rrapinn_g4_blind_contract import BLIND_METRICS_COLUMNS, REQUIRED_METRIC_KEYS


ANALYSIS_INPUT_SCHEMA = "rrapinn-g4-blind-analysis-input-v1"
PROJECTOR_SCHEMA = "rrapinn-g4-contained-projector-v2"
PROJECTOR_METHOD = "centroid_containment_assignment"
LOG_FLOOR = 1.0e-12
MIRROR_GRID_SIZE = 64
MIRROR_DOMAIN_MIN = -0.5
MIRROR_DOMAIN_MAX = 0.5
MIRROR_MIN_PAIRED_AREA_COVERAGE = 0.50
EXPECTED_STATES = {76: 379, 82: 409}
_OPAQUE_ARM_RE = re.compile(r"^arm_[0-9a-f]{8,64}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ANALYSIS_KEYS = {"schema", "opaque_arm", "development_case", "states", "event"}
_STATE_KEYS = {"cycle", "raw_step", "residual_fields", "element_fields"}
_ARTIFACT_KEYS = {"path", "sha256"}
_PROJECTOR_KEYS = {
    "schema_version", "method", "headline_policy", "artifact",
    "deterministic_sha256", "fem_sha256", "n_fem_rows",
    "n_headline_rows", "pidl_triangle_count",
}
_PROJECTOR_ARRAY_KEYS = {
    "source_fem_row_index", "pidl_triangle_assignment", "fem_centroids",
    "fem_element_area",
}
_RESIDUAL_KEYS = {
    "intensive", "dual_area", "interior_free_mask", "raw_step",
    "physical_cycle", "substep_index", "displacement",
}
_FIELD_KEYS = {
    "alpha_elem", "hist_fat_elem", "f_fatigue_elem", "psi_raw_elem",
    "psi_active_elem", "elem_x", "elem_y", "raw_step", "physical_cycle",
    "substep_index", "displacement",
}


class AnalysisError(ValueError):
    """Raised when blind analysis cannot prove its frozen input contract."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise AnalysisError(f"{label} is not a regular file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AnalysisError(f"{label} is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise AnalysisError(f"{label} must contain a JSON object")
    return payload


def _artifact(record: object, base: Path, label: str) -> Path:
    if not isinstance(record, dict) or set(record) != _ARTIFACT_KEYS:
        raise AnalysisError(f"{label} must be exactly a path/SHA256 record")
    expected = record.get("sha256")
    if not isinstance(expected, str) or not _SHA256_RE.fullmatch(expected):
        raise AnalysisError(f"{label} has an invalid SHA256")
    raw_path = record.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        raise AnalysisError(f"{label} has an invalid path")
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = (base / path).resolve()
    if not path.is_file() or sha256_file(path) != expected:
        raise AnalysisError(f"{label} is missing or its SHA256 does not match")
    return path


def _npz_snapshot(path: Path, label: str) -> dict[str, np.ndarray]:
    try:
        snapshot = path.read_bytes()
        with np.load(io.BytesIO(snapshot), allow_pickle=False) as archive:
            return {name: np.asarray(archive[name]) for name in archive.files}
    except Exception as exc:
        raise AnalysisError(f"cannot decode {label} NPZ: {path}") from exc


def _scalar(array: np.ndarray, label: str, cast: type[int] | type[float]):
    value = np.asarray(array)
    if value.size != 1:
        raise AnalysisError(f"{label} must be scalar")
    try:
        result = cast(value.reshape(-1)[0])
    except (TypeError, ValueError, OverflowError) as exc:
        raise AnalysisError(f"{label} has an invalid scalar value") from exc
    if cast is float and not math.isfinite(result):
        raise AnalysisError(f"{label} must be finite")
    return result


def _finite_vector(array: np.ndarray, label: str, *, nonnegative: bool = False) -> np.ndarray:
    result = np.asarray(array, dtype=np.float64).reshape(-1)
    if result.size == 0 or not np.all(np.isfinite(result)):
        raise AnalysisError(f"{label} must be a non-empty finite vector")
    if nonnegative and np.any(result < 0.0):
        raise AnalysisError(f"{label} must be non-negative")
    return result


def _validate_state_scalars(data: Mapping[str, np.ndarray], cycle: int, label: str) -> None:
    expected_step = EXPECTED_STATES[cycle]
    if _scalar(data["raw_step"], f"{label}.raw_step", int) != expected_step:
        raise AnalysisError(f"{label} raw_step does not match c{cycle} peak")
    if _scalar(data["physical_cycle"], f"{label}.physical_cycle", int) != cycle:
        raise AnalysisError(f"{label} physical_cycle mismatch")
    if _scalar(data["substep_index"], f"{label}.substep_index", int) != 3:
        raise AnalysisError(f"{label} must be Hard5 zero-based peak substep 3")
    if not np.isclose(
        _scalar(data["displacement"], f"{label}.displacement", float),
        0.12, rtol=0.0, atol=1.0e-12,
    ):
        raise AnalysisError(f"{label} must have peak displacement 0.12")


def _load_residual(path: Path, cycle: int) -> tuple[np.ndarray, np.ndarray]:
    data = _npz_snapshot(path, f"c{cycle} residual")
    if not _RESIDUAL_KEYS.issubset(data):
        raise AnalysisError(f"c{cycle} residual NPZ schema mismatch")
    _validate_state_scalars(data, cycle, f"c{cycle} residual")
    values = _finite_vector(data["intensive"], "residual intensive", nonnegative=True)
    weights = _finite_vector(data["dual_area"], "residual dual_area")
    mask = np.asarray(data["interior_free_mask"])
    if mask.dtype != np.dtype(bool) or mask.shape != values.shape or weights.shape != values.shape:
        raise AnalysisError("residual values, dual areas and boolean mask must align")
    if np.any(weights <= 0.0) or not np.any(mask):
        raise AnalysisError("residual dual areas must be positive and mask non-empty")
    return values[mask], weights[mask]


def _load_fields(path: Path, cycle: int) -> dict[str, np.ndarray]:
    data = _npz_snapshot(path, f"c{cycle} element fields")
    if not _FIELD_KEYS.issubset(data):
        raise AnalysisError(f"c{cycle} element-field NPZ schema mismatch")
    _validate_state_scalars(data, cycle, f"c{cycle} element fields")
    result = {
        key: _finite_vector(data[key], f"c{cycle}.{key}", nonnegative=True)
        for key in (
            "alpha_elem", "hist_fat_elem", "f_fatigue_elem",
            "psi_raw_elem", "psi_active_elem",
        )
    }
    result["elem_x"] = _finite_vector(data["elem_x"], f"c{cycle}.elem_x")
    result["elem_y"] = _finite_vector(data["elem_y"], f"c{cycle}.elem_y")
    lengths = {value.size for value in result.values()}
    if len(lengths) != 1:
        raise AnalysisError(f"c{cycle} element fields are not row-aligned")
    if np.any(result["alpha_elem"] > 1.0 + 1.0e-8):
        raise AnalysisError(f"c{cycle} damage lies outside [0,1]")
    if np.any(result["f_fatigue_elem"] > 1.0 + 1.0e-8):
        raise AnalysisError(f"c{cycle} fatigue factor lies outside [0,1]")
    return result


def weighted_tail_summary(values: np.ndarray, weights: np.ndarray) -> dict[str, float]:
    """Exact area summaries with fractional mass at both upper-tail boundaries."""
    values = _finite_vector(values, "tail values", nonnegative=True)
    weights = _finite_vector(weights, "tail weights")
    if values.shape != weights.shape or np.any(weights <= 0.0):
        raise AnalysisError("tail values and positive weights must align")
    total_weight = float(np.sum(weights))
    order_asc = np.argsort(values, kind="stable")
    cumulative = np.cumsum(weights[order_asc])

    def quantile(q: float) -> float:
        index = int(np.searchsorted(cumulative, q * total_weight, side="left"))
        return float(values[order_asc[min(index, values.size - 1)]])

    order_desc = np.argsort(-values, kind="stable")

    def upper_tail(fraction: float) -> tuple[float, float]:
        remaining = fraction * total_weight
        selected_mass = 0.0
        selected_weight = 0.0
        for index in order_desc:
            take = min(float(weights[index]), remaining)
            selected_mass += take * float(values[index])
            selected_weight += take
            remaining -= take
            if remaining <= 1.0e-15 * total_weight:
                break
        if selected_weight <= 0.0:
            raise AnalysisError("upper-tail selection has zero area")
        total_mass = float(np.sum(values * weights))
        return selected_mass / selected_weight, (
            selected_mass / total_mass if total_mass > 0.0 else 0.0
        )

    cvar95, _ = upper_tail(0.05)
    cvar99, mass99 = upper_tail(0.01)
    return {
        "mean": float(np.average(values, weights=weights)),
        "p95": quantile(0.95),
        "p99": quantile(0.99),
        "cvar95": cvar95,
        "cvar99": cvar99,
        "worst_1pct_area_mass": mass99,
    }


def _weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values, kind="stable")
    cumulative = np.cumsum(weights[order])
    index = int(np.searchsorted(cumulative, q * float(np.sum(weights)), side="left"))
    return float(values[order[min(index, values.size - 1)]])


def _weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    return float(np.average(values, weights=weights))


def _weighted_correlation(a: np.ndarray, b: np.ndarray, weights: np.ndarray) -> float:
    normalized = weights / float(np.sum(weights))
    a_centered = a - float(np.sum(normalized * a))
    b_centered = b - float(np.sum(normalized * b))
    denominator = math.sqrt(
        float(np.sum(normalized * a_centered * a_centered))
        * float(np.sum(normalized * b_centered * b_centered))
    )
    if denominator <= 0.0:
        raise AnalysisError("active-driver correlation is undefined for a constant field")
    result = float(np.sum(normalized * a_centered * b_centered) / denominator)
    if not math.isfinite(result):
        raise AnalysisError("active-driver correlation is non-finite")
    return max(-1.0, min(1.0, result))


def _area_iou(a: np.ndarray, b: np.ndarray, areas: np.ndarray) -> float:
    union = float(np.sum(areas[a | b]))
    if union <= 0.0:
        raise AnalysisError("support IoU union is empty")
    return float(np.sum(areas[a & b])) / union


def mirror_grid_asymmetry(
    values: np.ndarray, centroids: np.ndarray, areas: np.ndarray,
) -> tuple[float, float]:
    """Return damage asymmetry and paired-area coverage on a frozen grid.

    The exact Q4 mesh and contained-projector domain are not elementwise
    mirror-closed.  Element-nearest-neighbour matching would therefore mix
    sampling geometry into the morphology result.  We instead area-average
    the field into a fixed square grid and compare only occupied reflected
    cell pairs about y=0.  Pair weights are the lesser area in each reflected
    cell, so neither side can dominate merely because it is more finely
    sampled.
    """
    values = _finite_vector(values, "mirror values", nonnegative=True)
    areas = _finite_vector(areas, "mirror areas")
    centroids = np.asarray(centroids, dtype=np.float64)
    if (
        centroids.shape != (values.size, 2) or areas.shape != values.shape
        or np.any(areas <= 0.0) or not np.all(np.isfinite(centroids))
    ):
        raise AnalysisError("mirror values, centroids and positive areas must align")
    lower, upper, size = MIRROR_DOMAIN_MIN, MIRROR_DOMAIN_MAX, MIRROR_GRID_SIZE
    tolerance = 1.0e-10
    if np.any(centroids < lower - tolerance) or np.any(centroids > upper + tolerance):
        raise AnalysisError("mirror centroids lie outside the frozen square domain")
    indices = np.floor((centroids - lower) * size / (upper - lower)).astype(np.int64)
    indices = np.clip(indices, 0, size - 1)
    flat = indices[:, 0] * size + indices[:, 1]
    cell_area = np.bincount(flat, weights=areas, minlength=size * size).reshape(size, size)
    cell_mass = np.bincount(
        flat, weights=areas * values, minlength=size * size,
    ).reshape(size, size)
    occupied = cell_area > 0.0
    cell_mean = np.zeros_like(cell_mass)
    cell_mean[occupied] = cell_mass[occupied] / cell_area[occupied]
    reflected_area = cell_area[:, ::-1]
    pair_weight = np.minimum(cell_area, reflected_area)
    paired_weight = float(np.sum(pair_weight))
    coverage = paired_weight / float(np.sum(cell_area))
    if coverage < MIRROR_MIN_PAIRED_AREA_COVERAGE:
        raise AnalysisError(
            "mirror paired-area coverage is below the frozen 50% minimum"
        )
    delta = cell_mean - cell_mean[:, ::-1]
    asymmetry = math.sqrt(float(np.sum(pair_weight * delta * delta)) / paired_weight)
    return asymmetry, coverage


def _damage_morphology(
    predicted: np.ndarray, truth: np.ndarray, centroids: np.ndarray, areas: np.ndarray,
) -> dict[str, float]:
    """Frozen c82 damage-support diagnostics on the same 64x64 grid."""
    result = {
        f"damage_iou_{int(threshold * 100):03d}": _area_iou(
            predicted >= threshold, truth >= threshold, areas,
        )
        for threshold in (0.25, 0.50, 0.75)
    }
    lower, upper, size = MIRROR_DOMAIN_MIN, MIRROR_DOMAIN_MAX, MIRROR_GRID_SIZE
    indices = np.floor((centroids - lower) * size / (upper - lower)).astype(np.int64)
    indices = np.clip(indices, 0, size - 1)
    flat = indices[:, 0] * size + indices[:, 1]
    cell_area = np.bincount(flat, weights=areas, minlength=size * size).reshape(size, size)
    cell_mass = np.bincount(
        flat, weights=areas * predicted, minlength=size * size,
    ).reshape(size, size)
    cell_mean = np.zeros_like(cell_mass)
    occupied = cell_area > 0.0
    cell_mean[occupied] = cell_mass[occupied] / cell_area[occupied]
    support = occupied & (cell_mean >= 0.25)
    if not np.any(support):
        raise AnalysisError("predicted c82 damage support at 0.25 is empty")
    seen = np.zeros_like(support, dtype=bool)
    components = 0
    for x_index, y_index in np.argwhere(support):
        if seen[x_index, y_index]:
            continue
        components += 1
        stack = [(int(x_index), int(y_index))]
        seen[x_index, y_index] = True
        while stack:
            x_value, y_value = stack.pop()
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = x_value + dx, y_value + dy
                if (
                    0 <= nx < size and 0 <= ny < size
                    and support[nx, ny] and not seen[nx, ny]
                ):
                    seen[nx, ny] = True
                    stack.append((nx, ny))
    x_centers = lower + (np.arange(size) + 0.5) * (upper - lower) / size
    y_centers = x_centers.copy()
    x_grid, y_grid = np.meshgrid(x_centers, y_centers, indexing="ij")
    support_weight = cell_area * support
    total = float(np.sum(support_weight))
    x_values, y_values = x_grid[support], y_grid[support]
    upper_mass = float(np.sum(support_weight[y_grid > 0.0]))
    lower_mass = float(np.sum(support_weight[y_grid < 0.0]))
    result.update({
        "damage_components_025": float(components),
        "damage_crack_tip_x_025": float(np.max(x_values)),
        "damage_centroid_x_025": float(np.sum(support_weight * x_grid) / total),
        "damage_centroid_y_025": float(np.sum(support_weight * y_grid) / total),
        "damage_forward_extent_025": float(np.max(x_values) - np.min(x_values)),
        "damage_width_025": float(np.max(y_values) - np.min(y_values)),
        "damage_one_sided_support_025": float(upper_mass == 0.0 or lower_mass == 0.0),
    })
    return result


def _projector_content_hash(arrays: Mapping[str, np.ndarray]) -> str:
    digest = hashlib.sha256()
    digest.update((PROJECTOR_SCHEMA + "\0" + PROJECTOR_METHOD).encode("ascii"))
    for name in sorted(_PROJECTOR_ARRAY_KEYS):
        array = np.ascontiguousarray(arrays[name])
        digest.update(name.encode("ascii") + b"\0")
        digest.update(array.dtype.str.encode("ascii") + b"\0")
        digest.update(json.dumps(array.shape, separators=(",", ":")).encode("ascii") + b"\0")
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _load_projector(
    manifest_path: Path, fem_paths: Mapping[int, Path]
) -> dict[str, np.ndarray]:
    manifest = _load_json(manifest_path, "projector manifest")
    if set(manifest) != _PROJECTOR_KEYS:
        raise AnalysisError("projector v2 manifest schema/keys mismatch")
    if (
        manifest["schema_version"] != PROJECTOR_SCHEMA
        or manifest["method"] != PROJECTOR_METHOD
        or manifest["headline_policy"] != "mapping_contained_true_only"
    ):
        raise AnalysisError("projector v2 semantic schema mismatch")
    expected_fem = manifest["fem_sha256"]
    if not isinstance(expected_fem, dict) or set(expected_fem) != {"76", "82"}:
        raise AnalysisError("projector must bind exact c76/c82 FEM hashes")
    for cycle, path in fem_paths.items():
        expected = expected_fem[str(cycle)]
        if not isinstance(expected, str) or sha256_file(path) != expected:
            raise AnalysisError(f"FEM c{cycle} SHA256 does not match projector v2")
    artifact = _artifact(manifest["artifact"], manifest_path.parent, "projector artifact")
    arrays = _npz_snapshot(artifact, "projector")
    if set(arrays) != _PROJECTOR_ARRAY_KEYS:
        raise AnalysisError("projector NPZ array schema mismatch")
    rows = np.asarray(arrays["source_fem_row_index"])
    assignment = np.asarray(arrays["pidl_triangle_assignment"])
    centroids = np.asarray(arrays["fem_centroids"], dtype=np.float64)
    areas = np.asarray(arrays["fem_element_area"], dtype=np.float64).reshape(-1)
    if (
        rows.ndim != 1 or assignment.ndim != 1
        or not np.issubdtype(rows.dtype, np.integer)
        or not np.issubdtype(assignment.dtype, np.integer)
        or rows.size == 0 or assignment.shape != rows.shape
        or centroids.shape != (rows.size, 2) or areas.shape != rows.shape
        or np.any(rows < 0) or np.any(assignment < 0)
        or len(np.unique(rows)) != rows.size
        or not np.all(np.isfinite(centroids))
        or not np.all(np.isfinite(areas)) or np.any(areas <= 0.0)
    ):
        raise AnalysisError("projector arrays violate the contained assignment contract")
    if int(manifest["n_headline_rows"]) != rows.size:
        raise AnalysisError("projector headline row count mismatch")
    if int(manifest["pidl_triangle_count"]) <= int(np.max(assignment)):
        raise AnalysisError("projector assignment exceeds declared PIDL triangle count")
    if int(manifest["n_fem_rows"]) <= int(np.max(rows)):
        raise AnalysisError("projector FEM row index exceeds declared geometry")
    if _projector_content_hash(arrays) != manifest["deterministic_sha256"]:
        raise AnalysisError("projector deterministic content hash mismatch")
    return {
        "source_fem_row_index": rows.astype(np.int64, copy=False),
        "pidl_triangle_assignment": assignment.astype(np.int64, copy=False),
        "fem_centroids": centroids,
        "fem_element_area": areas,
    }


def _load_fem_mat(path: Path, cycle: int) -> dict[str, np.ndarray]:
    # Deliberately lazy: importing this module and residual-only helpers does
    # not require h5py.  Only a real v7.3 MAT analysis imports it.
    try:
        import h5py  # type: ignore
    except ImportError as exc:
        raise AnalysisError("h5py is required to read MATLAB v7.3 FEM inputs") from exc
    before = path.stat()
    try:
        with h5py.File(path, "r") as handle:
            if "cycle_state" not in handle:
                raise AnalysisError(f"FEM c{cycle} lacks cycle_state")
            state = handle["cycle_state"]
            required = {
                "cycle", "substep", "effective_load_factor", "damage_committed",
                "history_committed", "cyclemax_updated", "d_elem", "alpha_bar_elem",
                "f_alpha_elem", "psi_raw_peak_elem", "psi_active_peak_elem",
                "element_area", "element_centroid", "first_detect",
            }
            if not required.issubset(state.keys()):
                raise AnalysisError(f"FEM c{cycle} normalized MAT schema mismatch")
            scalar = lambda name: np.asarray(state[name]).reshape(-1)
            if (
                int(scalar("cycle")[0]) != cycle
                or int(scalar("substep")[0]) != 4
                or not np.isclose(float(scalar("effective_load_factor")[0]), 0.999999,
                                  rtol=0.0, atol=2.0e-12)
                or any(int(scalar(name)[0]) != 1 for name in (
                    "damage_committed", "history_committed", "cyclemax_updated"
                ))
            ):
                raise AnalysisError(f"FEM c{cycle} exact-peak committed state mismatch")
            first = state["first_detect"]
            if int(np.asarray(first["triggered"]).reshape(-1)[0]) != 0:
                raise AnalysisError(f"FEM c{cycle} must precede FEM first-detect c83")
            result = {
                "damage": _finite_vector(state["d_elem"], f"FEM c{cycle} damage", nonnegative=True),
                "history": _finite_vector(state["alpha_bar_elem"], f"FEM c{cycle} history", nonnegative=True),
                "fatigue": _finite_vector(state["f_alpha_elem"], f"FEM c{cycle} fatigue", nonnegative=True),
                "raw": _finite_vector(state["psi_raw_peak_elem"], f"FEM c{cycle} raw", nonnegative=True),
                "active": _finite_vector(state["psi_active_peak_elem"], f"FEM c{cycle} active", nonnegative=True),
                "area": _finite_vector(state["element_area"], f"FEM c{cycle} area"),
            }
            centroids_raw = np.asarray(state["element_centroid"], dtype=np.float64)
            result["centroids"] = centroids_raw.T if centroids_raw.shape[0] == 2 else centroids_raw
    except AnalysisError:
        raise
    except Exception as exc:
        raise AnalysisError(f"cannot decode FEM c{cycle} MATLAB v7.3 file") from exc
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_ino, after.st_size, after.st_mtime_ns
    ):
        raise AnalysisError(f"FEM c{cycle} changed while being read")
    sizes = {result[name].size for name in ("damage", "history", "fatigue", "raw", "active", "area")}
    n_rows = next(iter(sizes)) if len(sizes) == 1 else -1
    if (
        n_rows <= 0 or result["centroids"].shape != (n_rows, 2)
        or np.any(result["area"] <= 0.0)
        or np.any(result["damage"] > 1.0 + 1.0e-8)
        or np.any(result["fatigue"] > 1.0 + 1.0e-8)
        or not np.all(np.isfinite(result["centroids"]))
    ):
        raise AnalysisError(f"FEM c{cycle} field geometry/range mismatch")
    return result


def _load_arm_manifest(path: Path) -> dict[str, Any]:
    payload = _load_json(path, "opaque-arm analysis manifest")
    if set(payload) != _ANALYSIS_KEYS or payload.get("schema") != ANALYSIS_INPUT_SCHEMA:
        raise AnalysisError("opaque-arm analysis manifest schema/keys mismatch")
    arm = payload.get("opaque_arm")
    if not isinstance(arm, str) or not _OPAQUE_ARM_RE.fullmatch(arm):
        raise AnalysisError("analysis manifest arm ID is not opaque")
    if payload.get("development_case") != "U0.12":
        raise AnalysisError("analysis input is not the frozen U0.12 case")
    states = payload.get("states")
    if not isinstance(states, dict) or set(states) != {"76", "82"}:
        raise AnalysisError("analysis manifest must contain exactly c76 and c82")
    loaded_states: dict[int, dict[str, Any]] = {}
    for cycle, expected_step in EXPECTED_STATES.items():
        record = states[str(cycle)]
        if not isinstance(record, dict) or set(record) != _STATE_KEYS:
            raise AnalysisError(f"analysis manifest c{cycle} state schema mismatch")
        if int(record["cycle"]) != cycle or int(record["raw_step"]) != expected_step:
            raise AnalysisError(f"analysis manifest c{cycle} state mapping mismatch")
        loaded_states[cycle] = {
            "residual": _artifact(record["residual_fields"], path.parent, f"{arm} c{cycle} residual"),
            "fields": _artifact(record["element_fields"], path.parent, f"{arm} c{cycle} fields"),
        }
    event = payload.get("event")
    if not isinstance(event, dict) or set(event) != {"kind", "receipt"}:
        raise AnalysisError("analysis event schema mismatch")
    if event["kind"] not in {"first_detect", "right_censored"}:
        raise AnalysisError("analysis event must be first_detect or right_censored")
    return {
        "opaque_arm": arm,
        "states": loaded_states,
        "event_kind": event["kind"],
        "event_receipt": _artifact(event["receipt"], path.parent, f"{arm} event receipt"),
    }


def _event_result(kind: str, receipt_path: Path) -> tuple[float, int, str]:
    receipt = _load_json(receipt_path, "event receipt")
    if kind == "first_detect":
        required = {
            "schema", "raw_step", "physical_cycle", "substep_index",
            "substep_displacement", "qualifying_nodes", "boundary_nodes",
            "boundary_max_damage", "x_min_exclusive",
            "damage_threshold_exclusive", "minimum_nodes", "criterion",
            "trigger_source",
        }
        if set(receipt) != required or receipt.get("schema") != "boundary-first-detect-v1":
            raise AnalysisError("first-detect receipt schema mismatch")
        raw_step = int(receipt["raw_step"])
        adjusted = raw_step - 1
        expected_cycle, expected_substep = adjusted // 5 + 1, adjusted % 5
        displacements = (0.03, 0.06, 0.09, 0.12, 0.0)
        if (
            raw_step < 380 or raw_step > 460
            or int(receipt["physical_cycle"]) != expected_cycle
            or int(receipt["substep_index"]) != expected_substep
            or not np.isclose(float(receipt["substep_displacement"]), displacements[expected_substep])
            or int(receipt["qualifying_nodes"]) < 3
            or int(receipt["minimum_nodes"]) != 3
            or float(receipt["x_min_exclusive"]) != 0.48
            or float(receipt["damage_threshold_exclusive"]) != 0.95
            or receipt["criterion"] != "right_boundary_nodes_gt_damage_threshold"
            or receipt["trigger_source"] != "boundary_only"
        ):
            raise AnalysisError("receipt is not the frozen boundary first-detect event")
        return float(expected_cycle), raw_step, "measured"
    if set(receipt) != {"schema", "physical_cycle", "last_raw_step", "boundary_triggered"}:
        raise AnalysisError("right-censor receipt schema mismatch")
    if receipt != {
        "schema": "rrapinn-g4-right-censor-v1", "physical_cycle": 92,
        "last_raw_step": 460, "boundary_triggered": False,
    }:
        raise AnalysisError("right-censor receipt does not prove no first-detect through c92")
    return 92.0, 460, "right_censored"


def _field_metrics(
    pidl: Mapping[str, np.ndarray], fem: Mapping[str, np.ndarray],
    projector: Mapping[str, np.ndarray], cycle: int,
) -> dict[str, float]:
    rows = projector["source_fem_row_index"]
    assignment = projector["pidl_triangle_assignment"]
    if max(value.size for value in pidl.values()) <= int(np.max(assignment)):
        raise AnalysisError(f"c{cycle} PIDL fields are shorter than projector assignment")
    if fem["damage"].size != int(np.max(rows)) + 1 and fem["damage"].size <= int(np.max(rows)):
        raise AnalysisError(f"c{cycle} FEM fields are shorter than projector rows")
    area = projector["fem_element_area"]
    predicted = {
        "damage": pidl["alpha_elem"][assignment],
        "history": pidl["hist_fat_elem"][assignment],
        "fatigue": pidl["f_fatigue_elem"][assignment],
        "raw": pidl["psi_raw_elem"][assignment],
        "active": pidl["psi_active_elem"][assignment],
    }
    truth = {name: fem[name][rows] for name in predicted}
    active_pred_log = np.log10(np.maximum(predicted["active"], LOG_FLOOR))
    active_true_log = np.log10(np.maximum(truth["active"], LOG_FLOOR))
    active_error = np.abs(active_pred_log - active_true_log)
    active_tail = weighted_tail_summary(active_error, area)
    result = {
        "active_log_mean": active_tail["mean"],
        "active_log_cvar99": active_tail["cvar99"],
    }
    if cycle == 76:
        return result
    raw_error = np.abs(
        np.log10(np.maximum(predicted["raw"], LOG_FLOOR))
        - np.log10(np.maximum(truth["raw"], LOG_FLOOR))
    )
    history_error = np.abs(
        np.log10(np.maximum(predicted["history"], LOG_FLOOR))
        - np.log10(np.maximum(truth["history"], LOG_FLOOR))
    )
    fem_threshold = _weighted_quantile(truth["active"], area, 0.99)
    own_threshold = _weighted_quantile(predicted["active"], area, 0.99)
    fem_support = truth["active"] >= fem_threshold
    absolute_support = predicted["active"] >= fem_threshold
    own_support = predicted["active"] >= own_threshold
    fem_support_area = float(np.sum(area[fem_support]))
    if fem_support_area <= 0.0:
        raise AnalysisError("FEM p99 support has zero area")
    mirror_asymmetry, _mirror_coverage = mirror_grid_asymmetry(
        predicted["damage"], projector["fem_centroids"], area,
    )
    result.update({
        "raw_log_cvar99": weighted_tail_summary(raw_error, area)["cvar99"],
        "absolute_support_iou": _area_iou(fem_support, absolute_support, area),
        "absolute_support_area_ratio": float(np.sum(area[absolute_support])) / fem_support_area,
        "own_top1_support_iou": _area_iou(fem_support, own_support, area),
        "active_correlation": _weighted_correlation(active_pred_log, active_true_log, area),
        "damage_mae": _weighted_mean(np.abs(predicted["damage"] - truth["damage"]), area),
        "history_log_mae": _weighted_mean(history_error, area),
        "fatigue_factor_mae": _weighted_mean(np.abs(predicted["fatigue"] - truth["fatigue"]), area),
        "mirror_asymmetry": mirror_asymmetry,
    })
    result.update(_damage_morphology(
        predicted["damage"], truth["damage"], projector["fem_centroids"], area,
    ))
    return result


def build_blind_metric_rows(
    *, arm_manifests: Sequence[Path], fem_c76: Path, fem_c82: Path,
    projector_manifest: Path,
) -> list[dict[str, str]]:
    """Validate all inputs and return the exact frozen blind metric grid."""
    if len(arm_manifests) != 2:
        raise AnalysisError("exactly two opaque-arm manifests are required")
    fem_paths = {76: Path(fem_c76).resolve(), 82: Path(fem_c82).resolve()}
    if any(not path.is_file() for path in fem_paths.values()):
        raise AnalysisError("both exact FEM normalized MAT files must exist")
    projector = _load_projector(Path(projector_manifest).resolve(), fem_paths)
    fem = {cycle: _load_fem_mat(path, cycle) for cycle, path in fem_paths.items()}
    for cycle in (76, 82):
        rows = projector["source_fem_row_index"]
        if fem[cycle]["damage"].size != int(_load_json(Path(projector_manifest), "projector")["n_fem_rows"]):
            raise AnalysisError(f"FEM c{cycle} row count does not match projector")
        if not np.array_equal(fem[cycle]["centroids"][rows], projector["fem_centroids"]):
            raise AnalysisError(f"FEM c{cycle} centroids do not exactly match projector v2")
        if not np.array_equal(fem[cycle]["area"][rows], projector["fem_element_area"]):
            raise AnalysisError(f"FEM c{cycle} areas do not exactly match projector v2")
    arms = [_load_arm_manifest(Path(path).resolve()) for path in arm_manifests]
    arm_ids = [arm["opaque_arm"] for arm in arms]
    if len(set(arm_ids)) != 2:
        raise AnalysisError("opaque-arm manifests must identify two distinct arms")
    rows_out: list[dict[str, str]] = []
    for arm in sorted(arms, key=lambda item: item["opaque_arm"]):
        event_value, event_step, event_status = _event_result(
            arm["event_kind"], arm["event_receipt"]
        )
        values: dict[tuple[str, str, str], float] = {}
        for cycle in (76, 82):
            residual, residual_area = _load_residual(arm["states"][cycle]["residual"], cycle)
            for metric, value in weighted_tail_summary(residual, residual_area).items():
                values[("residual", str(cycle), metric)] = value
            pidl = _load_fields(arm["states"][cycle]["fields"], cycle)
            if pidl["alpha_elem"].size != int(_load_json(Path(projector_manifest), "projector")["pidl_triangle_count"]):
                raise AnalysisError(f"{arm['opaque_arm']} c{cycle} PIDL triangle count mismatch")
            for metric, value in _field_metrics(pidl, fem[cycle], projector, cycle).items():
                values[("field", str(cycle), metric)] = value
        values[("event", "headline", "first_detect_cycle")] = event_value
        if set(values) != REQUIRED_METRIC_KEYS:
            raise AnalysisError("computed metric grid differs from frozen blind contract")
        c82_status = "post_first_detect" if event_step <= 409 else "pre_first_detect"
        for endpoint, cycle, metric in sorted(values):
            if endpoint == "event":
                raw_step, status, unit = event_step, event_status, "cycle"
            else:
                raw_step = EXPECTED_STATES[int(cycle)]
                status = "pre_first_detect" if cycle == "76" else c82_status
                unit = "scaled_residual" if endpoint == "residual" else "dimensionless"
            value = float(values[(endpoint, cycle, metric)])
            if not math.isfinite(value):
                raise AnalysisError(f"computed non-finite metric: {endpoint}/{cycle}/{metric}")
            rows_out.append({
                "opaque_arm": arm["opaque_arm"], "endpoint": endpoint,
                "cycle": cycle, "raw_step": str(raw_step), "metric": metric,
                "value": format(value, ".17g"), "unit": unit, "status": status,
            })
    return rows_out


def write_blind_metrics_csv(rows: Sequence[Mapping[str, str]], output: Path) -> None:
    """Write exact contract columns with atomic exclusive installation."""
    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=BLIND_METRICS_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(buffer.getvalue().encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, output)
        except FileExistsError as exc:
            raise FileExistsError(f"refusing concurrent overwrite: {output}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def analyze_blind_pair(
    *, arm_manifests: Sequence[Path], fem_c76: Path, fem_c82: Path,
    projector_manifest: Path, output_csv: Path,
) -> list[dict[str, str]]:
    rows = build_blind_metric_rows(
        arm_manifests=arm_manifests, fem_c76=fem_c76, fem_c82=fem_c82,
        projector_manifest=projector_manifest,
    )
    write_blind_metrics_csv(rows, output_csv)
    return rows
