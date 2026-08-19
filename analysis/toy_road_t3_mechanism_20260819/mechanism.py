from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import h5py
import numpy as np


GP_FIELDS = (
    "d_gp",
    "alpha_bar_gp",
    "f_alpha_gp",
    "g_gp",
    "psi_raw_gp",
    "psi_active_gp",
)


@dataclass(frozen=True)
class Mesh:
    node_coords: np.ndarray
    connectivity: np.ndarray
    identities: dict[str, str]


@dataclass(frozen=True)
class ElementGeometry:
    centroids: np.ndarray
    areas: np.ndarray


@dataclass(frozen=True)
class PeakFields:
    cycle: int
    substep_ordinal: int
    load_factor: float
    d_node: np.ndarray
    gp_fields: dict[str, np.ndarray]
    identities: dict[str, str]


def _decode_matlab_string(dataset: h5py.Dataset) -> str:
    values = np.asarray(dataset)
    if values.dtype.kind not in "ui":
        raise ValueError(f"MATLAB string dataset must be integer: {dataset.name}")
    return "".join(chr(int(value)) for value in values.ravel() if int(value) != 0)


def _finite(name: str, values: np.ndarray) -> np.ndarray:
    result = np.asarray(values, dtype=np.float64)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"non-finite dataset: {name}")
    return result


def load_mesh(path: Path) -> Mesh:
    with h5py.File(path, "r") as handle:
        if "mesh_geometry" not in handle:
            raise ValueError("missing mesh_geometry group")
        group = handle["mesh_geometry"]
        required = (
            "node_coords",
            "connectivity",
            "mesh_sha256",
            "connectivity_sha256",
            "element_ordering_id",
            "gp_ordering_id",
        )
        missing = [name for name in required if name not in group]
        if missing:
            raise ValueError(f"missing mesh datasets: {', '.join(missing)}")
        nodes = _finite("node_coords", group["node_coords"]).T
        stored_connectivity = _finite("connectivity", group["connectivity"]).T
        identities = {name: _decode_matlab_string(group[name]) for name in required[2:]}
    if nodes.ndim != 2 or nodes.shape[1] != 2:
        raise ValueError("node_coords must be N x 2")
    if stored_connectivity.ndim != 2 or stored_connectivity.shape[1] != 4:
        raise ValueError("connectivity must be E x 4 Q4")
    rounded = np.rint(stored_connectivity)
    if not np.array_equal(stored_connectivity, rounded):
        raise ValueError("connectivity must contain exact integer indices")
    connectivity = rounded.astype(np.int64) - 1
    if connectivity.min(initial=0) < 0 or connectivity.max(initial=-1) >= len(nodes):
        raise ValueError("connectivity index is outside node range")
    return Mesh(nodes, connectivity, identities)


def load_peak_fields(
    path: Path,
    expected_cycle: int,
    expected_identities: Mapping[str, str] | None = None,
) -> PeakFields:
    with h5py.File(path, "r") as handle:
        if "shard" not in handle:
            raise ValueError("missing shard group")
        group = handle["shard"]
        required = (
            "cycle",
            "substep_ordinal",
            "load_factor",
            "d_node",
            *GP_FIELDS,
            "psi_raw_cyclemax_gp",
            "mesh_sha256",
            "element_ordering_id",
            "gp_ordering_id",
            "runtime_lock_sha256",
            "family_contract_sha256",
            "case_physics_contract_sha256",
            "execution_input_lock_sha256",
        )
        missing = [name for name in required if name not in group]
        if missing:
            raise ValueError(f"missing shard datasets: {', '.join(missing)}")
        cycle_values = _finite("cycle", group["cycle"]).ravel()
        if cycle_values.size != 1 or int(cycle_values[0]) != expected_cycle:
            raise ValueError(f"cycle identity mismatch: expected {expected_cycle}")
        ordinals = _finite("substep_ordinal", group["substep_ordinal"]).ravel()
        indices = np.flatnonzero(ordinals == 4)
        if indices.size != 1:
            raise ValueError("expected exactly one stored substep ordinal 4")
        index = int(indices[0])
        loads = _finite("load_factor", group["load_factor"]).ravel()
        if loads.size != ordinals.size:
            raise ValueError("load_factor/substep shape mismatch")
        d_node_all = _finite("d_node", group["d_node"])
        if d_node_all.ndim != 2 or d_node_all.shape[0] != ordinals.size:
            raise ValueError("d_node/substep shape mismatch")
        d_node = d_node_all[index].copy()
        gp_fields: dict[str, np.ndarray] = {}
        for name in GP_FIELDS:
            all_values = _finite(name, group[name])
            if all_values.ndim != 3 or all_values.shape[0] != ordinals.size or all_values.shape[1] != 4:
                raise ValueError(f"invalid GP shape: {name}")
            gp_fields[name] = all_values[index].T.copy()
        cyclemax = _finite("psi_raw_cyclemax_gp", group["psi_raw_cyclemax_gp"])
        if cyclemax.ndim != 2 or cyclemax.shape[0] != 4:
            raise ValueError("invalid GP shape: psi_raw_cyclemax_gp")
        gp_fields["psi_raw_cyclemax_gp"] = cyclemax.T.copy()
        identity_names = required[-7:]
        identities = {name: _decode_matlab_string(group[name]) for name in identity_names}
    if expected_identities:
        for name, expected in expected_identities.items():
            if identities.get(name) != expected:
                raise ValueError(f"identity mismatch for cycle {expected_cycle}: {name}")
    element_counts = {values.shape[0] for values in gp_fields.values()}
    if len(element_counts) != 1:
        raise ValueError("GP field element counts disagree")
    return PeakFields(expected_cycle, 4, float(loads[index]), d_node, gp_fields, identities)


def element_geometry(mesh: Mesh) -> ElementGeometry:
    xy = mesh.node_coords[mesh.connectivity]
    x = xy[:, :, 0]
    y = xy[:, :, 1]
    cross = x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1)
    signed_twice_area = cross.sum(axis=1)
    areas = 0.5 * np.abs(signed_twice_area)
    if np.any(~np.isfinite(areas)) or np.any(areas <= 0):
        raise ValueError("mesh contains nonpositive Q4 area")
    factor = signed_twice_area * 3.0
    centroid_x = ((x + np.roll(x, -1, axis=1)) * cross).sum(axis=1) / factor
    centroid_y = ((y + np.roll(y, -1, axis=1)) * cross).sum(axis=1) / factor
    centroids = np.column_stack([centroid_x, centroid_y])
    return ElementGeometry(centroids, areas)


def _weighted_quantile(values: np.ndarray, weights: np.ndarray, quantile: float) -> float:
    order = np.argsort(values, kind="stable")
    ordered_values = values[order]
    cumulative = np.cumsum(weights[order])
    index = int(np.searchsorted(cumulative, quantile * cumulative[-1], side="left"))
    return float(ordered_values[min(index, len(ordered_values) - 1)])


def reduce_field(values: np.ndarray, areas: np.ndarray, centroids: np.ndarray) -> dict[str, float]:
    values = _finite("field", values).ravel()
    areas = _finite("areas", areas).ravel()
    centroids = _finite("centroids", centroids)
    if values.shape != areas.shape or centroids.shape != (values.size, 2):
        raise ValueError("field/geometry shape mismatch")
    if np.any(areas <= 0):
        raise ValueError("areas must be positive")
    total_area = float(areas.sum())
    integral = float(np.dot(values, areas))
    positive_weight = np.maximum(values, 0.0) * areas
    total_weight = float(positive_weight.sum())
    if total_weight > 0:
        centroid = np.sum(centroids * positive_weight[:, None], axis=0) / total_weight
        variance = np.sum(
            positive_weight[:, None] * (centroids - centroid) ** 2, axis=0
        ) / total_weight
        width = np.sqrt(np.maximum(variance, 0.0))
    else:
        centroid = np.asarray([math.nan, math.nan])
        width = np.asarray([math.nan, math.nan])
    relative_floor = max(1e-15, 0.01 * max(float(values.max(initial=0.0)), 0.0))
    return {
        "min": float(values.min()),
        "max": float(values.max()),
        "area_weighted_mean": integral / total_area,
        "area_weighted_integral": integral,
        "p50": _weighted_quantile(values, areas, 0.50),
        "p95": _weighted_quantile(values, areas, 0.95),
        "p99": _weighted_quantile(values, areas, 0.99),
        "support_area_abs_1e15": float(areas[values > 1e-15].sum()),
        "support_area_rel_1pct": float(areas[values >= relative_floor].sum()),
        "weighted_centroid_x": float(centroid[0]),
        "weighted_centroid_y": float(centroid[1]),
        "weighted_rms_width_x": float(width[0]),
        "weighted_rms_width_y": float(width[1]),
    }


def process_zone(delta_damage: np.ndarray, geometry: ElementGeometry) -> dict[str, float]:
    delta = np.maximum(_finite("delta_damage", delta_damage).ravel(), 0.0)
    if delta.shape != geometry.areas.shape:
        raise ValueError("delta damage/geometry shape mismatch")
    threshold = max(1e-8, 0.01 * float(delta.max(initial=0.0)))
    mask = delta >= threshold
    support_area = float(geometry.areas[mask].sum())
    weights = delta * geometry.areas
    total = float(weights[mask].sum())
    if total > 0:
        centroid = np.sum(geometry.centroids[mask] * weights[mask, None], axis=0) / total
        variance = np.sum(
            weights[mask, None] * (geometry.centroids[mask] - centroid) ** 2,
            axis=0,
        ) / total
        width = np.sqrt(np.maximum(variance, 0.0))
    else:
        centroid = np.asarray([math.nan, math.nan])
        width = np.asarray([math.nan, math.nan])
    return {
        "threshold": threshold,
        "support_area": support_area,
        "centroid_x": float(centroid[0]),
        "centroid_y": float(centroid[1]),
        "rms_width_x": float(width[0]),
        "rms_width_y": float(width[1]),
    }


def build_comparison_pairs() -> dict[str, object]:
    return {
        "same_cycle": [20, 30, 31, 40, 60, 61, 68, 70, 71],
        "own_event": [("first_hit", 70, 68), ("confirmed", 73, 71)],
        "transitions": [(30, 31), (60, 61)],
        "p0_only": [73],
    }


def classify_memory(evidence: Mapping[str, bool]) -> str:
    required = ("departure", "persistence", "spatial_colocation")
    if all(evidence.get(name) is True for name in required):
        return "PERSISTENT_MEMORY_OBSERVED"
    return "MEMORY_NOT_ESTABLISHED"
