#!/usr/bin/env python3
"""Validate and bind the exact-peak U0.12 FEM package for the RRaPINN G4 gate.

The validator is intentionally specific to the frozen G4 U0.12 contract.  It
does not launch training and it refuses to overwrite receipts or mapping
sources.  MATLAB v7.3 arrays are read with h5py in their on-disk orientation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import numpy as np


PACKAGE_ID = "hard5_u012_exact_peak_native_q4_c76_c82_c83_20260824_v2.1"
PACKAGE_SCHEMA = "request27.package-manifest.v2.1"
EXPECTED_CYCLES = (76, 82, 83)
EXPECTED_COUNTS = (0, 0, 22)
EXPECTED_NODES = 86756
EXPECTED_ELEMENTS = 86408
EXPECTED_STATE_TIMING = (
    "post-convergence/post-damage-commit/post-history-commit/"
    "post-cyclemax-update"
)
EXPECTED_FIELDS = {
    "cycle", "substep", "load_factor", "staggered_iterations",
    "damage_committed", "history_committed", "cyclemax_updated",
    "node_coords", "connectivity_q4", "u_node", "d_node", "psi_raw_gp",
    "psi_cyclemax_gp", "history_vars_old", "d_gp", "g_gp", "strain_gp",
    "trace_strain_gp", "node_ids", "element_ids", "history_H_gp",
    "alpha_bar_gp", "psi_eff_prev_gp", "f_alpha_gp", "psi_raw_peak_elem",
    "psi_cyclemax_elem", "alpha_bar_elem", "f_alpha_elem", "d_elem",
    "element_centroid", "element_area", "g_stiffness_peak_elem",
    "psi_active_peak_elem", "first_detect",
}
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class ValidationError(ValueError):
    """Raised when an exact FEM input violates the frozen contract."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _exclusive_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {path}")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def parse_sha256s(path: Path) -> dict[str, str]:
    """Parse GNU-style SHA256SUMS while tolerating Windows CRLF."""
    records: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        try:
            digest, relative = line.split(None, 1)
        except ValueError as exc:
            raise ValidationError("malformed SHA256SUMS line") from exc
        relative = relative.lstrip("*").strip()
        if not _SHA_RE.fullmatch(digest) or not relative or relative in records:
            raise ValidationError("invalid or duplicate SHA256SUMS record")
        records[relative] = digest
    if not records:
        raise ValidationError("SHA256SUMS is empty")
    return records


def _verify_hash_records(package: Path, records: dict[str, str]) -> None:
    for relative, expected in records.items():
        target = package / relative
        if not target.is_file() or sha256_file(target) != expected:
            raise ValidationError(f"missing or hash-mismatched package file: {relative}")


def _require_h5py():
    try:
        import h5py  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError("h5py is required to validate MATLAB v7.3 FEM inputs") from exc
    return h5py


def _q4_geometry(nodes: np.ndarray, connectivity: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if nodes.shape != (EXPECTED_NODES, 2) or connectivity.shape != (EXPECTED_ELEMENTS, 4):
        raise ValidationError("native Q4 node/connectivity shape mismatch")
    if not np.isfinite(nodes).all():
        raise ValidationError("node coordinates contain non-finite values")
    if connectivity.min() != 1 or connectivity.max() != EXPECTED_NODES:
        raise ValidationError("Q4 connectivity is not one-based and in range")
    xy = nodes[connectivity.astype(np.int64) - 1]
    centroids = xy.mean(axis=1)
    x, y = xy[:, :, 0], xy[:, :, 1]
    areas = 0.5 * np.abs(
        np.sum(x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1), axis=1)
    )
    if not np.isfinite(areas).all() or np.any(areas <= 0.0):
        raise ValidationError("Q4 areas are not finite and strictly positive")
    return centroids, areas


def _cycle_arrays(path: Path) -> dict[str, np.ndarray]:
    h5py = _require_h5py()
    with h5py.File(path, "r") as handle:
        if "cycle_state" not in handle:
            raise ValidationError(f"missing cycle_state group: {path.name}")
        group = handle["cycle_state"]
        missing = sorted(EXPECTED_FIELDS.difference(group.keys()))
        if missing:
            raise ValidationError(f"{path.name} missing required fields: {missing}")
        arrays = {
            key: np.asarray(group[key])
            for key in EXPECTED_FIELDS
            if key != "first_detect"
        }
        first = group["first_detect"]
        for key in ("right_x_min", "damage_threshold", "minimum_nodes", "matching_node_count", "triggered"):
            if key not in first:
                raise ValidationError(f"{path.name} first_detect missing {key}")
            arrays[f"first_detect/{key}"] = np.asarray(first[key])
    return arrays


def _scalar(array: np.ndarray) -> float:
    if array.size != 1:
        raise ValidationError("expected scalar MATLAB field")
    return float(array.reshape(-1)[0])


def _validate_historical_reference(package: Path) -> dict[str, int]:
    h5py = _require_h5py()
    with h5py.File(package / "provenance/pre_run_lock.mat", "r") as handle:
        cfg = handle.get("cfg")
        if cfg is None or "historical_reference" not in cfg:
            raise ValidationError("pre_run_lock lacks cfg.historical_reference")
        hist = cfg["historical_reference"]
        result = {
            "first_hit_cycle": int(_scalar(np.asarray(hist["first_hit_cycle"]))),
            "confirmed_event_cycle": int(_scalar(np.asarray(hist["confirmed_event_cycle"]))),
            "checkpoint_cycle": int(_scalar(np.asarray(hist["checkpoint_cycle"]))),
        }
        requested = tuple(int(x) for x in np.asarray(cfg["requested_cycles"]).reshape(-1))
    if result != {"first_hit_cycle": 83, "confirmed_event_cycle": 86, "checkpoint_cycle": 86}:
        raise ValidationError("historical first-detect/confirmation provenance mismatch")
    if requested != (76, 87, 89):
        raise ValidationError("retained historical requested_cycles field changed unexpectedly")
    return result


def _load_mesh_geometry(package: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    h5py = _require_h5py()
    with h5py.File(package / "mesh_geometry.mat", "r") as handle:
        nodes = np.asarray(handle["node_coords"]).T
        connectivity = np.asarray(handle["connectivity_q4"]).T
    centroids, areas = _q4_geometry(nodes, connectivity)
    return nodes, connectivity, centroids, areas


def _require_finite_numeric(arrays: dict[str, np.ndarray], label: str) -> None:
    for key, value in arrays.items():
        if value.dtype.kind in "fiu" and not np.isfinite(value).all():
            raise ValidationError(f"{label} contains non-finite values in {key}")


def validate_package(package: Path) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    package = package.resolve()
    manifest_path = package / "manifest.json"
    sums_path = package / "SHA256SUMS"
    if not manifest_path.is_file() or not sums_path.is_file():
        raise ValidationError("package lacks manifest.json or SHA256SUMS")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("schema_version") != PACKAGE_SCHEMA
        or manifest.get("package_id") != PACKAGE_ID
        or manifest.get("status") != "PACKAGE_CONTRACT_COMPLETE"
        or manifest.get("input_gate_verdict") != "PASS_CLOSE_REQUEST27_INPUT_GATE"
    ):
        raise ValidationError("package identity/status does not match frozen G4 input")

    sums = parse_sha256s(sums_path)
    _verify_hash_records(package, sums)
    if sums.get("manifest.json") != sha256_file(manifest_path):
        raise ValidationError("manifest is not bound by SHA256SUMS")
    manifest_files = {row["path"]: row["sha256"] for row in manifest.get("files", [])}
    if any(sums.get(path) != digest for path, digest in manifest_files.items()):
        raise ValidationError("manifest file records disagree with SHA256SUMS")

    states = manifest.get("states", [])
    if [row.get("cycle") for row in states] != list(EXPECTED_CYCLES):
        raise ValidationError("manifest cycle set/order mismatch")
    if any(
        row.get("substep") != 4
        or row.get("semantic_class") != "exact-peak-native-q4"
        or row.get("state_timing") != EXPECTED_STATE_TIMING
        or not np.isclose(float(row.get("effective_load_factor", np.nan)), 0.999999)
        for row in states
    ):
        raise ValidationError("manifest exact-peak state semantics mismatch")

    nodes, connectivity, exact_centroids, exact_areas = _load_mesh_geometry(package)
    previous_damage: np.ndarray | None = None
    counts: list[int] = []
    cycle_summaries: list[dict[str, Any]] = []
    for expected_cycle, state in zip(EXPECTED_CYCLES, states):
        arrays = _cycle_arrays(package / state["file"])
        _require_finite_numeric(arrays, f"c{expected_cycle}")
        if (
            int(_scalar(arrays["cycle"])) != expected_cycle
            or int(_scalar(arrays["substep"])) != 4
            or not np.isclose(_scalar(arrays["load_factor"]), 0.999999)
            or not all(bool(_scalar(arrays[key])) for key in (
                "damage_committed", "history_committed", "cyclemax_updated"
            ))
        ):
            raise ValidationError(f"c{expected_cycle} state/timing scalar mismatch")
        embedded_nodes = arrays["node_coords"].T
        embedded_connectivity = arrays["connectivity_q4"].T
        if not np.array_equal(embedded_nodes, nodes) or not np.array_equal(embedded_connectivity, connectivity):
            raise ValidationError(f"c{expected_cycle} embedded geometry differs from mesh_geometry")
        if not np.array_equal(arrays["element_centroid"].reshape(2, -1).T, exact_centroids):
            raise ValidationError(f"c{expected_cycle} element centroids are not native-Q4 exact")
        if not np.array_equal(arrays["element_area"].reshape(-1), exact_areas):
            raise ValidationError(f"c{expected_cycle} element areas are not native-Q4 exact")
        g_gp = arrays["g_gp"]
        psi_raw_gp = arrays["psi_raw_gp"]
        if not np.array_equal(g_gp.mean(axis=0), arrays["g_stiffness_peak_elem"].reshape(-1)):
            raise ValidationError(f"c{expected_cycle} stiffness reduction formula mismatch")
        if not np.array_equal((g_gp * psi_raw_gp).mean(axis=0), arrays["psi_active_peak_elem"].reshape(-1)):
            raise ValidationError(f"c{expected_cycle} active-driver reduction formula mismatch")
        damage = arrays["d_node"].reshape(-1)
        if damage.shape != (EXPECTED_NODES,) or np.min(damage) < 0.0 or np.max(damage) > 1.0:
            raise ValidationError(f"c{expected_cycle} nodal damage violates [0,1]")
        count = int(np.sum((nodes[:, 0] >= 0.48) & (damage > 0.95)))
        counts.append(count)
        if (
            not np.isclose(_scalar(arrays["first_detect/right_x_min"]), 0.48)
            or not np.isclose(_scalar(arrays["first_detect/damage_threshold"]), 0.95)
            or int(_scalar(arrays["first_detect/minimum_nodes"])) != 3
            or int(_scalar(arrays["first_detect/matching_node_count"])) != count
            or bool(_scalar(arrays["first_detect/triggered"])) != (count >= 3)
        ):
            raise ValidationError(f"c{expected_cycle} first-detect receipt mismatch")
        if previous_damage is not None and np.any(damage < previous_damage - 1e-12):
            raise ValidationError(f"damage irreversibility violated before c{expected_cycle}")
        previous_damage = damage
        cycle_summaries.append({
            "cycle": expected_cycle,
            "substep": 4,
            "effective_load_factor": _scalar(arrays["load_factor"]),
            "first_detect_node_count": count,
            "first_detect_triggered": count >= 3,
            "cycle_file": state["file"],
            "cycle_file_sha256": sha256_file(package / state["file"]),
        })
    if tuple(counts) != EXPECTED_COUNTS:
        raise ValidationError(f"selected-cycle first-detect counts mismatch: {counts}")

    historical = _validate_historical_reference(package)
    first_prov = manifest.get("first_detect_provenance", {})
    if (
        first_prov.get("historical_reference", {}).get("first_detect_truth_cycle") != 83
        or first_prov.get("historical_reference", {}).get("confirmed_event_cycle") != 86
        or first_prov.get("selected_cycle_scan", {}).get("counts_c76_c82_c83") != list(EXPECTED_COUNTS)
    ):
        raise ValidationError("manifest first-detect provenance does not bind c83/c86 semantics")

    receipt: dict[str, Any] = {
        "schema": "rrapinn-g4-exact-fem-input-validation-v1",
        "status": "PASS_G4_U012_EXACT_PEAK_FEM_INPUT",
        "package": {
            "path": str(package),
            "package_id": PACKAGE_ID,
            "manifest_sha256": sha256_file(manifest_path),
            "sha256s_sha256": sha256_file(sums_path),
            "verified_sha256sum_records": len(sums),
        },
        "geometry": {
            "node_count": EXPECTED_NODES,
            "element_count": EXPECTED_ELEMENTS,
            "total_area": float(exact_areas.sum()),
            "all_areas_finite_positive": True,
            "mesh_geometry_sha256": sha256_file(package / "mesh_geometry.mat"),
        },
        "states": cycle_summaries,
        "first_detect": {
            "criterion": "x>=0.48 and d>0.95 for at least 3 nodes",
            "selected_cycle_counts": counts,
            "truth_cycle": historical["first_hit_cycle"],
            "confirmation_cycle": historical["confirmed_event_cycle"],
            "confirmation_used_as_truth": False,
            "provenance_scope": (
                "c83 first-hit identity is bound to pre_run_lock historical_reference; "
                "the c76/c82/c83 scan alone is not continuous-history evidence"
            ),
        },
        "claim_boundary": (
            "Closes the Request 27 exact-FEM input blocker only; it does not "
            "authorize G4 training or establish an efficacy result."
        ),
    }
    return receipt, exact_centroids, exact_areas


def _point_in_candidates(point: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    v1, v2, v3 = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    denom = ((v2[:, 1] - v3[:, 1]) * (v1[:, 0] - v3[:, 0])
             + (v3[:, 0] - v2[:, 0]) * (v1[:, 1] - v3[:, 1]))
    valid = np.abs(denom) >= 1e-12
    a = np.full(len(triangles), -np.inf)
    b = np.full(len(triangles), -np.inf)
    a[valid] = (
        (v2[valid, 1] - v3[valid, 1]) * (point[0] - v3[valid, 0])
        + (v3[valid, 0] - v2[valid, 0]) * (point[1] - v3[valid, 1])
    ) / denom[valid]
    b[valid] = (
        (v3[valid, 1] - v1[valid, 1]) * (point[0] - v3[valid, 0])
        + (v1[valid, 0] - v3[valid, 0]) * (point[1] - v3[valid, 1])
    ) / denom[valid]
    c = 1.0 - a - b
    return valid & (a >= -1e-12) & (b >= -1e-12) & (c >= -1e-12)


def recompute_assignment(centroids: np.ndarray, pidl_mesh: Path) -> tuple[np.ndarray, np.ndarray]:
    try:
        import meshio  # type: ignore
        from scipy.spatial import cKDTree  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError("meshio and scipy are required for projector validation") from exc
    mesh = meshio.read(pidl_mesh)
    triangle_blocks = [block.data for block in mesh.cells if block.type == "triangle"]
    if len(triangle_blocks) != 1:
        raise ValidationError("PIDL mesh must contain exactly one triangle block")
    connectivity = np.asarray(triangle_blocks[0], dtype=np.int64)
    # Producer inference evaluates the PIDL coordinates as float32 tensors.
    points = np.asarray(mesh.points[:, :2], dtype=np.float32)
    triangles = points[connectivity]
    triangle_centroids = triangles.mean(axis=1)
    _, candidates = cKDTree(triangle_centroids).query(centroids, k=20)
    assignment = np.empty(len(centroids), dtype=np.int64)
    contained = np.zeros(len(centroids), dtype=bool)
    for index, point in enumerate(centroids):
        candidate_ids = np.atleast_1d(candidates[index]).astype(np.int64)
        inside = _point_in_candidates(point, triangles[candidate_ids].astype(np.float64))
        if np.any(inside):
            assignment[index] = candidate_ids[int(np.flatnonzero(inside)[0])]
            contained[index] = True
        else:
            assignment[index] = candidate_ids[0]
    return assignment, contained


def bind_projector_source(
    *,
    centroids: np.ndarray,
    areas: np.ndarray,
    pidl_mesh: Path,
    legacy_projector: Path,
    output: Path,
) -> dict[str, Any]:
    assignment, contained = recompute_assignment(centroids, pidl_mesh)
    with np.load(legacy_projector, allow_pickle=False) as legacy:
        legacy_rows = np.asarray(legacy["source_fem_row_index"], dtype=np.int64)
        legacy_assignment = np.asarray(legacy["pidl_triangle_assignment"], dtype=np.int64)
    if len(legacy_rows) != 85113 or int(np.sum(contained)) != 85113:
        raise ValidationError("contained headline population changed from the frozen 85,113 rows")
    if np.any(~contained[legacy_rows]):
        raise ValidationError("a previously frozen headline row lost containment")
    changed = np.flatnonzero(assignment[legacy_rows] != legacy_assignment)
    arrays = {
        "pidl_triangle_assignment": assignment,
        "mapping_contained": contained,
        "fem_centroids": np.asarray(centroids, dtype=np.float64),
        "fem_element_area": np.asarray(areas, dtype=np.float64),
    }
    if output.exists() or output.with_suffix(".manifest.json").exists():
        raise FileExistsError(f"refusing to overwrite mapping source: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            np.savez_compressed(handle, **arrays)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    manifest = {
        "schema": "rrapinn-g4-exact-fem-projector-source-v1",
        "method": "centroid_containment_assignment",
        "pidl_coordinate_dtype": "float32_producer_geometry",
        "source_fem_geometry": "request27_v2.1_native_q4_double",
        "fem_rows": int(len(centroids)),
        "contained_rows": int(np.sum(contained)),
        "fallback_rows": int(np.sum(~contained)),
        "legacy_headline_assignment_change_count": int(len(changed)),
        "legacy_changed_fem_rows": [int(legacy_rows[index]) for index in changed],
        "pidl_mesh": str(pidl_mesh.resolve()),
        "pidl_mesh_sha256": sha256_file(pidl_mesh),
        "legacy_projector": str(legacy_projector.resolve()),
        "legacy_projector_sha256": sha256_file(legacy_projector),
        "output_sha256": sha256_file(output),
        "decision": (
            "rebuild_projector_against_exact_geometry"
            if len(changed) else "legacy_assignment_stable_rebind_exact_geometry"
        ),
        "claim_boundary": "Mapping preparation only; fallback rows remain excluded from headline metrics.",
    }
    _exclusive_bytes(output.with_suffix(".manifest.json"), _canonical_json(manifest))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--pidl-mesh", type=Path)
    parser.add_argument("--legacy-projector", type=Path)
    parser.add_argument("--mapping-source-output", type=Path)
    args = parser.parse_args()
    receipt, centroids, areas = validate_package(args.package)
    mapping_args = (args.pidl_mesh, args.legacy_projector, args.mapping_source_output)
    if any(value is not None for value in mapping_args):
        if not all(value is not None for value in mapping_args):
            parser.error("projector validation requires all three projector arguments")
        receipt["projector_source"] = bind_projector_source(
            centroids=centroids,
            areas=areas,
            pidl_mesh=args.pidl_mesh,
            legacy_projector=args.legacy_projector,
            output=args.mapping_source_output,
        )
    encoded = _canonical_json(receipt)
    _exclusive_bytes(args.receipt, encoded)
    print(encoded.decode("utf-8"), end="")


if __name__ == "__main__":
    main()
