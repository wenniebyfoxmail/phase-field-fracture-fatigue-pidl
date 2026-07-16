#!/usr/bin/env python3
"""Prepare a pre-lock dataset for c86 spatial degradation reconstruction.

Only the individual c1-c85 MAT files are opened.  The sole c86 input is the
previously sealed binary nodal crack core plus reaction scalars.  The script
therefore cannot index the c86 hidden state and writes a self-contained
training dataset whose target arrays end at c85.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import meshio
import numpy as np
from scipy import sparse
from scipy.io import loadmat
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from damage_observation_reconstruction import at1_profile  # noqa: E402
from damage_state_inversion import parse_load_displacement_cycles  # noqa: E402
from prepare_fem_mechanism_operator_dataset import (  # noqa: E402
    edge_attributes,
    normalized_coordinates,
    quad_adjacency,
    quad_geometry,
)
from spatial_degradation_reconstruction import damage_to_z, target_increment  # noqa: E402


TRAIN_TARGET_START = 5
PRELOCK_TARGET_END = 85
SEALED_TARGET_CYCLE = 86
CORE_THRESHOLD = 0.95
LENGTH_SCALE = 0.01
STEPS_PER_CYCLE = 8
REACTION_STEPS = (4, 5, 6, 7)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def element_core(
    damage: np.ndarray,
    edge_index: np.ndarray,
    coordinates: np.ndarray,
    *,
    threshold: float = CORE_THRESHOLD,
) -> np.ndarray:
    """Return the thresholded element component attached to the left notch."""
    candidate = np.asarray(damage).reshape(-1) >= threshold
    indices = np.flatnonzero(candidate)
    if not len(indices):
        raise ValueError("damage field contains no visible crack-core elements")
    remap = np.full(len(candidate), -1, dtype=np.int64)
    remap[indices] = np.arange(len(indices))
    src, dst = np.asarray(edge_index, dtype=np.int64)
    retained = candidate[src] & candidate[dst]
    rows = remap[src[retained]]
    cols = remap[dst[retained]]
    graph = sparse.csr_matrix(
        (np.ones(len(rows), dtype=np.uint8), (rows, cols)),
        shape=(len(indices), len(indices)),
    )
    _, labels = connected_components(graph, directed=False)
    seed = int(np.argmin(coordinates[indices, 0]))
    connected = np.zeros(len(candidate), dtype=bool)
    connected[indices[labels == labels[seed]]] = True
    return connected


def reaction_features(load_displacement: Path) -> np.ndarray:
    cycles = parse_load_displacement_cycles(
        load_displacement, steps_per_cycle=STEPS_PER_CYCLE
    )
    if len(cycles) < SEALED_TARGET_CYCLE:
        raise ValueError("load-displacement table does not reach c86")
    rows = []
    for cycle in cycles[:SEALED_TARGET_CYCLE]:
        indices = np.asarray(REACTION_STEPS, dtype=int) - 1
        reaction = np.abs(cycle.fy[indices])
        log_reaction = np.log10(np.maximum(reaction, 1.0e-12))
        ratios = reaction[1:] / max(float(reaction[0]), 1.0e-12)
        rows.append(np.concatenate((log_reaction, ratios)))
    return np.asarray(rows, dtype=np.float32)


def observation_geometry(
    core: np.ndarray,
    centroids: np.ndarray,
    areas: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    core = np.asarray(core, dtype=bool).reshape(-1)
    if not np.any(core):
        raise ValueError("visible core is empty")
    core_points = centroids[core]
    distance = cKDTree(core_points).query(centroids, k=1)[0]
    tip_x = float(core_points[:, 0].max())
    tip_band = core_points[:, 0] >= tip_x - 2.0 * LENGTH_SCALE
    tip_y = float(np.median(core_points[tip_band, 1]))
    core_area_fraction = float(areas[core].sum() / areas.sum())
    geometry = np.column_stack(
        (
            np.clip(distance / LENGTH_SCALE, 0.0, 20.0),
            at1_profile(distance, LENGTH_SCALE),
            np.clip((centroids[:, 0] - tip_x) / LENGTH_SCALE, -20.0, 20.0),
            np.clip((centroids[:, 1] - tip_y) / LENGTH_SCALE, -20.0, 20.0),
        )
    ).astype(np.float32)
    globals_ = np.asarray((tip_x, tip_y, core_area_fraction), dtype=np.float32)
    return geometry, globals_


def build_features(
    prior_damage: np.ndarray,
    older_damage: np.ndarray,
    core: np.ndarray,
    observation_geometry_features: np.ndarray,
    observation_globals: np.ndarray,
    coordinates: np.ndarray,
    log_area: np.ndarray,
    reaction: np.ndarray,
    cycle: int,
) -> np.ndarray:
    prior_z = np.asarray(damage_to_z(prior_damage), dtype=np.float32)
    older_z = np.asarray(damage_to_z(older_damage), dtype=np.float32)
    phase = float(cycle) / SEALED_TARGET_CYCLE
    repeated = np.concatenate(
        (
            reaction.astype(np.float32),
            observation_globals,
            np.asarray(
                (phase, np.sin(2.0 * np.pi * phase), np.cos(2.0 * np.pi * phase)),
                dtype=np.float32,
            ),
        )
    )
    return np.column_stack(
        (
            prior_damage,
            older_damage,
            prior_z,
            older_z,
            prior_z - older_z,
            core.astype(np.float32),
            observation_geometry_features,
            coordinates,
            log_area.reshape(-1),
            np.broadcast_to(repeated, (len(prior_damage), len(repeated))),
        )
    ).astype(np.float32)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fem-case", type=Path, required=True)
    parser.add_argument("--reference-vtk", type=Path, required=True)
    parser.add_argument("--sealed-c86-observation", type=Path, required=True)
    parser.add_argument("--load-displacement", type=Path, required=True)
    parser.add_argument("--trajectory-id", required=True)
    parser.add_argument("--physics-family", required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def load_prelock_damage(
    fem_case: Path, expected_elements: int
) -> tuple[np.ndarray, list[Path]]:
    paths = [
        fem_case / "psi_fields" / f"cycle_{cycle:04d}.mat" for cycle in range(1, 86)
    ]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"pre-lock cycle files are missing: {missing[:3]}")
    rows = []
    for path in paths:
        data = loadmat(path, variable_names=("d_elem",))
        if "d_elem" not in data:
            raise KeyError(f"{path} lacks d_elem")
        damage = np.asarray(data["d_elem"], dtype=np.float64).reshape(-1)
        if len(damage) != expected_elements or not np.all(np.isfinite(damage)):
            raise ValueError(f"{path} has invalid element damage")
        rows.append(np.clip(damage, 0.0, 1.0).astype(np.float32))
    return np.stack(rows), paths


def main() -> None:
    args = parse_args()
    mesh = meshio.read(args.reference_vtk)
    if "quad" not in mesh.cells_dict:
        raise ValueError("reference VTK does not contain quad elements")
    connectivity = np.asarray(mesh.cells_dict["quad"], dtype=np.int32)
    centroids, areas64 = quad_geometry(np.asarray(mesh.points), connectivity)
    coordinates64, _, _ = normalized_coordinates(centroids)
    edge_index = quad_adjacency(connectivity).astype(np.int64)
    edge_attr = edge_attributes(coordinates64, areas64, edge_index).astype(np.float32)
    coordinates = coordinates64.astype(np.float32)
    areas = areas64.astype(np.float32)
    log_area = np.log(areas64 / np.median(areas64)).astype(np.float32)[:, None]
    prelock_damage, prelock_paths = load_prelock_damage(
        args.fem_case, len(connectivity)
    )
    reactions = reaction_features(args.load_displacement)

    target_cycles = np.arange(
        TRAIN_TARGET_START, PRELOCK_TARGET_END + 1, dtype=np.int16
    )
    feature_rows = []
    target_rows = []
    target_damage_rows = []
    core_rows = []
    for cycle in target_cycles:
        prior = prelock_damage[cycle - 3]
        older = prelock_damage[cycle - 5]
        target = prelock_damage[cycle - 1]
        core = element_core(target, edge_index, coordinates)
        geometry, globals_ = observation_geometry(core, centroids, areas)
        feature_rows.append(
            build_features(
                prior,
                older,
                core,
                geometry,
                globals_,
                coordinates,
                log_area,
                reactions[cycle - 1],
                int(cycle),
            )
        )
        target_rows.append(target_increment(prior, target).astype(np.float32))
        target_damage_rows.append(target)
        core_rows.append(core.astype(np.uint8))

    sealed = np.load(args.sealed_c86_observation, allow_pickle=False)
    if int(np.asarray(sealed["observation_cycle"]).item()) != SEALED_TARGET_CYCLE:
        raise ValueError("sealed observation is not c86")
    nodal_core = np.asarray(sealed["core95"], dtype=bool)
    if len(nodal_core) <= int(connectivity.max()):
        raise ValueError("sealed nodal core does not match mechanism connectivity")
    # Requiring all four nodes gives a high-precision element observation and
    # matches the element d>=0.95 operator used for pre-c86 training cycles.
    sealed_element_core = nodal_core[connectivity].all(axis=1)
    sealed_geometry, sealed_globals = observation_geometry(
        sealed_element_core, centroids, areas
    )
    sealed_features = build_features(
        prelock_damage[83],
        prelock_damage[81],
        sealed_element_core,
        sealed_geometry,
        sealed_globals,
        coordinates,
        log_area,
        reactions[85],
        SEALED_TARGET_CYCLE,
    )

    feature_names = np.asarray(
        [
            "prior_damage_cminus2",
            "older_damage_cminus4",
            "prior_z_cminus2",
            "older_z_cminus4",
            "prior_z_trend",
            "visible_core",
            "distance_to_core_over_l",
            "nominal_at1_damage",
            "tip_relative_x_over_l",
            "tip_relative_y_over_l",
            "x_normalized",
            "y_normalized",
            "log_area",
            "log_reaction_peak",
            "log_reaction_post1",
            "log_reaction_post2",
            "log_reaction_post3",
            "post1_over_peak",
            "post2_over_peak",
            "post3_over_peak",
            "visible_tip_x",
            "visible_tip_y",
            "visible_core_area_fraction",
            "cycle_fraction",
            "cycle_sin",
            "cycle_cos",
        ]
    )
    features = np.stack(feature_rows)
    if features.shape[-1] != len(feature_names):
        raise RuntimeError("feature-name count does not match prepared features")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.out,
        target_cycles=target_cycles,
        features=features,
        target_capacity_fraction=np.stack(target_rows),
        target_damage=np.stack(target_damage_rows),
        visible_core=np.stack(core_rows),
        sealed_c86_features=sealed_features,
        sealed_c86_prior_damage=prelock_damage[83],
        sealed_c86_visible_core=sealed_element_core.astype(np.uint8),
        coordinates=coordinates,
        centroids=centroids.astype(np.float32),
        areas=areas,
        edge_index=edge_index,
        edge_attr=edge_attr,
        connectivity=connectivity,
        feature_names=feature_names,
        trajectory_id=np.asarray(args.trajectory_id),
        physics_family=np.asarray(args.physics_family),
        hidden_target_max_cycle=np.asarray(PRELOCK_TARGET_END, dtype=np.int16),
        sealed_prediction_cycle=np.asarray(SEALED_TARGET_CYCLE, dtype=np.int16),
    )
    manifest = {
        "dataset": str(args.out.resolve()),
        "fem_case": str(args.fem_case.resolve()),
        "reference_vtk_sha256": sha256(args.reference_vtk),
        "prelock_cycle_file_count": len(prelock_paths),
        "prelock_cycle_file_sha256": {
            path.name: sha256(path) for path in prelock_paths
        },
        "sealed_c86_observation_sha256": sha256(args.sealed_c86_observation),
        "load_displacement_sha256": sha256(args.load_displacement),
        "target_cycles": f"c{TRAIN_TARGET_START}..c{PRELOCK_TARGET_END}",
        "hidden_target_max_cycle": PRELOCK_TARGET_END,
        "sealed_prediction_cycle": SEALED_TARGET_CYCLE,
        "prior_lag": 2,
        "older_prior_lag": 4,
        "visible_core_semantics": (
            "notch-connected target element d>=0.95 before c86; "
            "all-four-nodes sealed c86 core"
        ),
        "target": (
            "remaining-capacity-normalized increment in "
            "z=-log10((1-d)^2) relative to c-2 prior"
        ),
        "feature_names": feature_names.tolist(),
        "element_count": int(len(areas)),
        "edge_count": int(edge_index.shape[1]),
        "c86_hidden_damage_opened": False,
        "c87_c89_targets_opened": False,
    }
    manifest_path = args.out.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
