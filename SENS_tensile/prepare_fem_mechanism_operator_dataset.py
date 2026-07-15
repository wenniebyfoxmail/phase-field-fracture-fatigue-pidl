#!/usr/bin/env python3
"""Build a native-quad FEM trajectory dataset for a supervised mesh operator.

This is a data-preparation command, not a training command.  It reads all
cycle-peak MAT exports and obtains geometry/connectivity from one VTK snapshot.
The VTK mechanics fields are unloaded and are never used as peak targets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import meshio
import numpy as np
from scipy.io import loadmat


FIELD_MAP = {
    "damage": "d_elem",
    "alpha_bar": "alpha_bar_elem",
    "fatigue_degradation": "f_alpha_elem",
    "psi_raw": "psi_elem",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quad_geometry(points: np.ndarray, connectivity: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    xy = points[connectivity, :2]
    centroids = xy.mean(axis=1)
    x = xy[:, :, 0]
    y = xy[:, :, 1]
    areas = 0.5 * np.abs(
        np.sum(x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1), axis=1)
    )
    if np.any(areas <= 0.0):
        raise ValueError("reference VTK contains zero-area or invalid quads")
    return centroids, areas


def quad_adjacency(connectivity: np.ndarray) -> np.ndarray:
    """Return directed element adjacency for quads sharing a full edge."""
    edge_nodes = np.stack(
        [
            connectivity[:, [0, 1]],
            connectivity[:, [1, 2]],
            connectivity[:, [2, 3]],
            connectivity[:, [3, 0]],
        ],
        axis=1,
    ).reshape(-1, 2)
    edge_nodes.sort(axis=1)
    owners = np.repeat(np.arange(len(connectivity), dtype=np.int64), 4)
    order = np.lexsort((edge_nodes[:, 1], edge_nodes[:, 0]))
    edge_nodes = edge_nodes[order]
    owners = owners[order]
    shared = np.all(edge_nodes[1:] == edge_nodes[:-1], axis=1)
    left = owners[:-1][shared]
    right = owners[1:][shared]
    valid = left != right
    undirected = np.stack([left[valid], right[valid]], axis=0)
    directed = np.concatenate([undirected, undirected[::-1]], axis=1)
    directed = np.unique(directed, axis=1)
    if directed.size == 0:
        raise ValueError("no shared quad edges found")
    return directed


def normalized_coordinates(centroids: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    minimum = centroids.min(axis=0)
    maximum = centroids.max(axis=0)
    span = np.maximum(maximum - minimum, np.finfo(float).eps)
    normalized = 2.0 * (centroids - minimum) / span - 1.0
    return normalized, minimum, maximum


def edge_attributes(
    coordinates: np.ndarray,
    areas: np.ndarray,
    edge_index: np.ndarray,
) -> np.ndarray:
    src, dst = edge_index
    delta = coordinates[dst] - coordinates[src]
    distance = np.linalg.norm(delta, axis=1, keepdims=True)
    log_area_ratio = np.log(np.maximum(areas[dst], 1.0e-16) / np.maximum(areas[src], 1.0e-16))[:, None]
    return np.concatenate([delta, distance, log_area_ratio], axis=1)


def coarse_graph(
    coordinates: np.ndarray,
    areas: np.ndarray,
    edge_index: np.ndarray,
    bins: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    raw_x = np.clip(((coordinates[:, 0] + 1.0) * 0.5 * bins).astype(int), 0, bins - 1)
    raw_y = np.clip(((coordinates[:, 1] + 1.0) * 0.5 * bins).astype(int), 0, bins - 1)
    raw_cluster = raw_y * bins + raw_x
    _, cluster_index = np.unique(raw_cluster, return_inverse=True)
    cluster_index = cluster_index.astype(np.int64)
    cluster_count = int(cluster_index.max()) + 1

    cluster_area = np.bincount(cluster_index, weights=areas, minlength=cluster_count)
    cluster_xy = np.column_stack(
        [
            np.bincount(cluster_index, weights=coordinates[:, axis] * areas, minlength=cluster_count)
            / cluster_area
            for axis in range(2)
        ]
    )
    coarse_edges = cluster_index[edge_index]
    coarse_edges = coarse_edges[:, coarse_edges[0] != coarse_edges[1]]
    coarse_edges = np.unique(coarse_edges, axis=1)
    coarse_attr = edge_attributes(cluster_xy, cluster_area, coarse_edges)
    return cluster_index, coarse_edges, coarse_attr


def load_cycle_state(path: Path, expected_elements: int, log_floor: float) -> np.ndarray:
    data = loadmat(path)
    missing = [name for name in FIELD_MAP.values() if name not in data]
    if missing:
        raise KeyError(f"{path} misses {missing}")
    arrays = {name: np.asarray(data[key], dtype=np.float64).reshape(-1) for name, key in FIELD_MAP.items()}
    for name, values in arrays.items():
        if len(values) != expected_elements:
            raise ValueError(f"{path}: {name} has {len(values)} elements, expected {expected_elements}")
        if not np.all(np.isfinite(values)):
            raise ValueError(f"{path}: {name} contains non-finite values")
    return np.column_stack(
        [
            np.clip(arrays["damage"], 0.0, 1.0),
            np.maximum(arrays["alpha_bar"], 0.0),
            np.clip(arrays["fatigue_degradation"], 0.0, 1.0),
            np.log10(np.maximum(arrays["psi_raw"], log_floor)),
        ]
    ).astype(np.float32)


def trajectory_violation_counts(states: np.ndarray, tolerance: float = 1.0e-6) -> dict[str, int]:
    delta = np.diff(states, axis=0)
    return {
        "damage_decrease": int(np.count_nonzero(delta[:, :, 0] < -tolerance)),
        "history_decrease": int(np.count_nonzero(delta[:, :, 1] < -tolerance)),
        "fatigue_degradation_increase": int(np.count_nonzero(delta[:, :, 2] > tolerance)),
    }


def verify_element_order(
    mesh: meshio.Mesh,
    connectivity: np.ndarray,
    first_cycle_state: np.ndarray,
) -> dict[str, float]:
    """Verify that MAT element rows follow the VTK quad ordering."""
    if "d" not in mesh.point_data:
        raise KeyError("reference VTK needs point-data damage 'd' for element-order verification")
    vtk_damage = np.asarray(mesh.point_data["d"], dtype=np.float64).reshape(-1)
    vtk_element_damage = np.clip(vtk_damage[connectivity].mean(axis=1), 0.0, 1.0)
    mat_damage = first_cycle_state[:, 0].astype(np.float64)
    correlation = float(np.corrcoef(vtk_element_damage, mat_damage)[0, 1])
    mae = float(np.mean(np.abs(vtk_element_damage - mat_damage)))
    max_abs = float(np.max(np.abs(vtk_element_damage - mat_damage)))
    if correlation < 0.999999 or mae > 1.0e-6:
        raise ValueError(
            "MAT/VTK element order failed: "
            f"correlation={correlation:.9f}, mae={mae:.3e}"
        )
    return {"correlation": correlation, "mae": mae, "max_abs": max_abs}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fem-case", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reference-vtk", type=Path, default=None)
    parser.add_argument("--trajectory-id", required=True)
    parser.add_argument("--physics-family", required=True)
    parser.add_argument("--coarse-bins", type=int, default=32)
    parser.add_argument("--log-floor", type=float, default=1.0e-12)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.coarse_bins < 2:
        raise ValueError("--coarse-bins must be at least 2")
    psi_dir = args.fem_case / "psi_fields"
    files = sorted(psi_dir.glob("cycle_*.mat"))
    cycles = np.array([int(path.stem.split("_")[-1]) for path in files], dtype=np.int16)
    if not np.array_equal(cycles, np.arange(1, 90)):
        raise ValueError(f"expected complete cycle 1..89 sequence, found {cycles.tolist()}")

    reference_vtk = args.reference_vtk or args.fem_case / "fields_000001_008.vtk"
    mesh = meshio.read(reference_vtk)
    if "quad" not in mesh.cells_dict:
        raise ValueError(f"{reference_vtk} does not contain quad cells")
    connectivity = np.asarray(mesh.cells_dict["quad"], dtype=np.int64)
    centroids, areas = quad_geometry(np.asarray(mesh.points), connectivity)
    coordinates, coord_min, coord_max = normalized_coordinates(centroids)
    edge_index = quad_adjacency(connectivity)
    edge_attr = edge_attributes(coordinates, areas, edge_index)
    cluster_index, coarse_edge_index, coarse_edge_attr = coarse_graph(
        coordinates, areas, edge_index, args.coarse_bins
    )

    states = np.stack(
        [load_cycle_state(path, len(connectivity), args.log_floor) for path in files],
        axis=0,
    )
    element_order_check = verify_element_order(mesh, connectivity, states[0])
    violations = trajectory_violation_counts(states)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.out,
        cycles=cycles,
        states=states,
        coordinates=coordinates.astype(np.float32),
        centroids=centroids.astype(np.float32),
        areas=areas.astype(np.float32),
        log_area=np.log(areas / np.median(areas)).astype(np.float32)[:, None],
        connectivity=connectivity.astype(np.int32),
        edge_index=edge_index.astype(np.int64),
        edge_attr=edge_attr.astype(np.float32),
        cluster_index=cluster_index,
        coarse_edge_index=coarse_edge_index.astype(np.int64),
        coarse_edge_attr=coarse_edge_attr.astype(np.float32),
        coord_min=coord_min.astype(np.float64),
        coord_max=coord_max.astype(np.float64),
        log_floor=np.array(args.log_floor, dtype=np.float64),
        trajectory_id=np.asarray(args.trajectory_id),
        physics_family=np.asarray(args.physics_family),
        trajectory_count=np.asarray(1, dtype=np.int16),
    )

    manifest = {
        "dataset": str(args.out.resolve()),
        "trajectory_id": args.trajectory_id,
        "physics_family": args.physics_family,
        "trajectory_count": 1,
        "claim_class": "tooling-only",
        "trajectory_generalization": False,
        "assimilation_eligible": False,
        "quarantine_reason": "single physical trajectory with within-trajectory cycle split",
        "fem_case": str(args.fem_case.resolve()),
        "reference_vtk": str(reference_vtk.resolve()),
        "reference_vtk_sha256": file_sha256(reference_vtk),
        "cycle_count": int(len(cycles)),
        "cycles": cycles.astype(int).tolist(),
        "element_count": int(len(connectivity)),
        "directed_edge_count": int(edge_index.shape[1]),
        "coarse_cluster_count": int(cluster_index.max()) + 1,
        "coarse_directed_edge_count": int(coarse_edge_index.shape[1]),
        "state_channels": [
            "damage_clipped_0_1",
            "alpha_bar_nonnegative",
            "fatigue_degradation_clipped_0_1",
            "log10_peak_raw_tensile_driver",
        ],
        "state_semantics": {
            "mat_files": "cycle-peak element fields",
            "reference_vtk": "geometry/topology only; mechanics fields are unloaded and unused",
            "active_driver": "not archived; derive eta0 support as (1-damage)^2 * psi_raw",
        },
        "trajectory_violation_counts": violations,
        "mat_vtk_element_order_check": element_order_check,
        "log_floor": args.log_floor,
    }
    manifest_path = args.out.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
