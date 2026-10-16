"""Identity-bound, read-only capability adapter for S09-E008 Stage 0A.

The exact public wrapper is frozen to one sealed run.  It qualifies metadata,
static identity and all 366 unique payload hashes before any HDF5 decode.  It
then validates all six physical substeps, derives native weights from the same
verified static bytes, constructs the 73 endpoint transitions internally and
only then freezes P1.  No caller-supplied scientific array crosses that route.
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import hashlib
import io
import json
from pathlib import Path

import h5py
import numpy as np

from s09_stage0a_packet import (
    _reject_external_hdf5_storage,
    decode_payload,
    index_by_key,
    preflight_rows,
)
from s09_stage0a_p1_freeze import freeze_p1_contract


@dataclass(frozen=True)
class Stage0ACapabilityContext:
    run_id: str
    producer_commit: str
    state_index_sha256: str
    static_sha256: str
    expected_nodes: int
    expected_elements: int
    expected_gp: int
    history_channel_order: tuple[str, ...]
    nominal_load_path: tuple[float, ...]
    static_filename: str = "native_q4_mesh_dofs_quadrature.mat"
    static_semantics: str = "exact-static-hash+producer-source-bound-native-order"

    @property
    def digest(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


S09_E008_CONTEXT = Stage0ACapabilityContext(
    run_id="hard5_u0125_stage0b_f24eff2a79b64cc3a6538dd4f18f71ae",
    producer_commit="862992a60edc7f59335365beacb5c71fc8592a7a",
    state_index_sha256="3d815b4abc8e4d215b2d6ce747bbc728729d9ed41e7ff7dfe29dbb77695ad1f1",
    static_sha256="b79a36298eabec363fb7a53fb0590db46eb949b05c05dbffb9cb5a8bc0e4b40e",
    expected_nodes=86_756,
    expected_elements=86_408,
    expected_gp=4,
    history_channel_order=("H", "alpha_bar", "q_prev", "f"),
    nominal_load_path=(0.0, 0.25, 0.5, 0.75, 1.0, 0.0),
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_identity_file(path: Path, expected_name: str, expected_sha256: str) -> bytes:
    if path.name != expected_name or path.is_symlink() or not path.is_file():
        raise ValueError(f"invalid identity file: {expected_name}")
    data = path.read_bytes()
    if _sha256_bytes(data) != expected_sha256:
        raise ValueError(f"identity hash mismatch: {expected_name}")
    return data


def load_state_index(index_path: Path, context: Stage0ACapabilityContext) -> list[dict[str, str]]:
    data = _read_identity_file(index_path, "state_index.csv", context.state_index_sha256)
    text = data.decode("utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    required = {
        "state_key", "cycle", "substep", "timing", "is_alias",
        "source_state_key", "payload_file", "payload_sha256",
        "nominal_load_factor", "imposed_displacement", "converged",
    }
    if reader.fieldnames is None or not required.issubset(reader.fieldnames):
        raise ValueError("state index schema mismatch")
    return list(reader)


def _require_complete_six_state_index(
    rows: list[dict[str, str]], context: Stage0ACapabilityContext
) -> None:
    if len(rows) != 73 * 6:
        raise ValueError("full trajectory must contain 438 logical rows")
    by_key = index_by_key(rows)
    if set(by_key) != {f"c{cycle:04d}_s{substep:02d}"
                       for cycle in range(1, 74) for substep in range(6)}:
        raise ValueError("full six-state coverage mismatch")
    for cycle in range(1, 74):
        for substep, expected_load in enumerate(context.nominal_load_path):
            key = f"c{cycle:04d}_s{substep:02d}"
            row = by_key[key]
            if int(row["cycle"]) != cycle or int(row["substep"]) != substep:
                raise ValueError(f"logical identity mismatch: {key}")
            timing = "pre_cycle_committed" if substep == 0 else "post_history_commit"
            if row["timing"] != timing or row["converged"] != "1":
                raise ValueError(f"timing/convergence mismatch: {key}")
            if float(row["nominal_load_factor"]) != expected_load:
                raise ValueError(f"prescribed path mismatch: {key}")
            if substep == 0 and cycle > 1:
                prior = f"c{cycle - 1:04d}_s05"
                prior_row = by_key[prior]
                valid = (
                    row["is_alias"] == "1"
                    and row["source_state_key"] == prior
                    and row["payload_file"] == prior_row["payload_file"]
                    and row["payload_sha256"] == prior_row["payload_sha256"]
                )
            else:
                valid = row["is_alias"] == "0" and row["source_state_key"] == key
            if not valid:
                raise ValueError(f"source identity mismatch: {key}")


def _qualify_full_trajectory(
    *, run_root: Path, context: Stage0ACapabilityContext
) -> tuple[list[dict[str, str]], dict[str, object]]:
    index_path = run_root / "state_index.csv"
    static_path = run_root / "static" / context.static_filename
    rows = load_state_index(index_path, context)
    _require_complete_six_state_index(rows, context)
    _read_identity_file(static_path, context.static_filename, context.static_sha256)
    inventory = preflight_rows(run_root / "states", rows)
    if len(inventory) != 366:
        raise ValueError("expected exactly 366 unique physical payloads")
    receipt = {
        "verdict": "FULL_TRAJECTORY_HASH_QUALIFIED",
        "context_sha256": context.digest,
        "run_id": context.run_id,
        "producer_commit": context.producer_commit,
        "state_index_sha256": context.state_index_sha256,
        "static_sha256": context.static_sha256,
        "static_semantics": context.static_semantics,
        "history_channel_order": list(context.history_channel_order),
        "nominal_load_path": list(context.nominal_load_path),
        "qualified_cycles": list(range(1, 74)),
        "qualified_substeps": list(range(6)),
        "unique_payload_inventory": inventory,
        "unique_payload_count": len(inventory),
        "all_payload_hashes_preflighted": True,
        "hdf5_open_count": 0,
        "scientific_execution_authorized": False,
    }
    return rows, receipt


def qualify_s09_e008_full_trajectory(
    run_root: Path,
) -> tuple[list[dict[str, str]], dict[str, object]]:
    """Exact-run wrapper; changing identity requires a new reviewed version."""
    return _qualify_full_trajectory(run_root=run_root, context=S09_E008_CONTEXT)


def _array_sha256(value: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(value)
    return hashlib.sha256(contiguous.tobytes(order="C")).hexdigest()


def _mat_field(handle: h5py.File, value, name: str):
    """Dereference one scalar MATLAB-v7.3 struct field."""
    if not isinstance(value, h5py.Group) or name not in value:
        raise ValueError(f"static MATLAB field missing: {name}")
    field = value[name]
    if isinstance(field, h5py.Group):
        return field
    if not isinstance(field, h5py.Dataset):
        raise ValueError(f"unsupported static MATLAB field: {name}")
    reference_type = h5py.check_dtype(ref=field.dtype)
    if reference_type is not None:
        refs = np.asarray(field).reshape(-1)
        if len(refs) != 1 or not refs[0]:
            raise ValueError(f"static MATLAB field is not scalar: {name}")
        return handle[refs[0]]
    return field


def _mat_numeric(handle: h5py.File, value, name: str) -> np.ndarray:
    dataset = _mat_field(handle, value, name)
    if not isinstance(dataset, h5py.Dataset) or dataset.dtype.kind not in "fiu":
        raise ValueError(f"static field is not numeric: {name}")
    stored = np.asarray(dataset)
    # MATLAB stores array dimensions in reverse order in v7.3 HDF5.
    axes = tuple(reversed(range(stored.ndim)))
    return stored.transpose(axes) if axes else stored


def decode_native_static(
    static_path: Path, context: Stage0ACapabilityContext
) -> tuple[dict[str, np.ndarray | float], dict[str, object]]:
    """Decode the exact native Q4 geometry used by exporter and capability audit."""
    payload = _read_identity_file(static_path, context.static_filename, context.static_sha256)
    with h5py.File(io.BytesIO(payload), "r") as handle:
        _reject_external_hdf5_storage(handle)
        if "stage0b_static" not in handle:
            raise ValueError("stage0b_static root missing")
        root = handle["stage0b_static"]
        mesh = _mat_field(handle, root, "mesh")
        quadrature = _mat_field(handle, root, "quadrature")
        geometry = _mat_field(handle, root, "geometry")
        xy = _mat_numeric(handle, mesh, "node_coordinates")
        conn_raw = _mat_numeric(handle, mesh, "cells_0based")
        gauss_weight = _mat_numeric(handle, quadrature, "gauss_W").reshape(-1)
        nxi = _mat_numeric(handle, quadrature, "Nxi")
        dndxi = _mat_numeric(handle, quadrature, "dNdxi")
        thickness_raw = _mat_numeric(handle, geometry, "t")
        for name, value in (("node_coordinates", xy), ("gauss_W", gauss_weight),
                            ("Nxi", nxi), ("dNdxi", dndxi), ("t", thickness_raw)):
            if value.dtype != np.dtype("float64"):
                raise ValueError(f"static field must be stored float64: {name}")
        if thickness_raw.shape != (1, 1) or not np.isfinite(thickness_raw).all():
            raise ValueError("static thickness must be one finite scalar")
        thickness = float(thickness_raw.reshape(-1)[0])
    if conn_raw.dtype.kind not in "iu" or not np.equal(conn_raw, np.floor(conn_raw)).all():
        raise ValueError("static connectivity must contain exact integers")
    conn = conn_raw.astype(np.int64, copy=False)
    expected = (context.expected_nodes, context.expected_elements, context.expected_gp)
    if (xy.shape, conn.shape, gauss_weight.shape, nxi.shape, dndxi.shape) != (
        (expected[0], 2), (expected[1], 4), (expected[2],),
        (4, expected[2]), (2, 4, expected[2]),
    ):
        raise ValueError("static native-Q4 shape/order contract mismatch")
    if (not np.isfinite(xy).all() or not np.isfinite(gauss_weight).all()
            or not np.isfinite(nxi).all() or not np.isfinite(dndxi).all()
            or not np.isfinite(thickness) or thickness <= 0):
        raise ValueError("static native-Q4 values are invalid")
    if np.any(conn < 0) or np.any(conn >= context.expected_nodes):
        raise ValueError("static connectivity is out of bounds")
    element_xy = xy[conn]
    jacobian = np.einsum("ing,enj->egij", dndxi, element_xy)
    determinant = np.linalg.det(jacobian)
    gp_weight = determinant * gauss_weight[None, :] * thickness
    if not np.isfinite(gp_weight).all() or np.any(gp_weight <= 0):
        raise ValueError("nonpositive or nonfinite native GP weight")
    local = np.einsum("ng,eg->en", nxi, gp_weight)
    nodal_weight = np.zeros(context.expected_nodes, dtype=np.float64)
    np.add.at(nodal_weight, conn.reshape(-1), local.reshape(-1))
    if not np.isfinite(nodal_weight).all() or np.any(nodal_weight <= 0):
        raise ValueError("nonpositive or nonfinite native nodal weight")
    receipt = {
        "source_static_sha256": context.static_sha256,
        "derivation": "Q4 detJ * gauss_W * thickness; Nxi-consistent nodal lumping",
        "node_order": "native", "element_order": "native",
        "gauss_point_order": "native quadrature",
        "node_coordinates_sha256": _array_sha256(xy),
        "cells_0based_sha256": _array_sha256(conn),
        "gauss_weight_sha256": _array_sha256(gauss_weight),
        "Nxi_sha256": _array_sha256(nxi),
        "dNdxi_sha256": _array_sha256(dndxi),
        "thickness": thickness,
        "nodal_weight_sha256": _array_sha256(nodal_weight),
        "gp_weight_sha256": _array_sha256(gp_weight),
        "nodal_weight_shape": list(nodal_weight.shape),
        "gp_weight_shape": list(gp_weight.shape),
    }
    arrays: dict[str, np.ndarray | float] = {
        "xy": xy,
        "conn": conn,
        "gauss_weight": gauss_weight,
        "shape": nxi.T,
        "reference_derivative": dndxi.transpose(2, 0, 1),
        "nodal_weight": nodal_weight,
        "gp_weight": gp_weight,
        "thickness": thickness,
    }
    return arrays, receipt


def _derive_native_weights(
    static_path: Path, context: Stage0ACapabilityContext
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Derive weights only from the exact verified native static payload."""
    arrays, receipt = decode_native_static(static_path, context)
    return arrays["nodal_weight"], arrays["gp_weight"], receipt


def _state_fingerprint(state) -> dict[str, object]:
    return {
        "source_state_key": state.source_state_key,
        "payload_sha256": state.payload_sha256,
        "imposed_displacement": state.imposed_displacement,
        "u_node_sha256": _array_sha256(state.u_node),
        "d_node_sha256": _array_sha256(state.d_node),
        "history_gp_sha256": _array_sha256(state.history_gp),
        "strain_en_undgr_gp_sha256": _array_sha256(state.strain_en_undgr_gp),
        "strain_en_degr_gp_sha256": _array_sha256(state.strain_en_degr_gp),
    }


def _qualify_decode_and_freeze(
    *, run_root: Path, context: Stage0ACapabilityContext
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    """Controlled metadata -> full decode -> P1 freeze route with no caller arrays."""
    rows, hash_receipt = _qualify_full_trajectory(run_root=run_root, context=context)
    nodal_weight, gp_weight, weight_receipt = _derive_native_weights(
        run_root / "static" / context.static_filename, context
    )
    shape_d = (73, context.expected_nodes)
    shape_h = (73, context.expected_elements, context.expected_gp, 4)
    d_pre = np.empty(shape_d, dtype=np.float64)
    d_peak = np.empty(shape_d, dtype=np.float64)
    history_pre = np.empty(shape_h, dtype=np.float64)
    history_peak = np.empty(shape_h, dtype=np.float64)
    u_peak = np.empty((73, context.expected_nodes, 2), dtype=np.float64)
    pre_filled = np.zeros(73, dtype=bool)
    peak_filled = np.zeros(73, dtype=bool)
    physical_bindings: dict[str, dict[str, object]] = {}
    native_rows = [row for row in rows if row["is_alias"] == "0"]
    if len(native_rows) != 366:
        raise ValueError("native physical row count mismatch")
    for row in native_rows:
        state = decode_payload(
            run_root / row["payload_file"], row,
            expected_nodes=context.expected_nodes,
            expected_elements=context.expected_elements,
            expected_gp=context.expected_gp,
        )
        key = row["state_key"]
        physical_bindings[key] = _state_fingerprint(state)
        cycle, substep = int(row["cycle"]), int(row["substep"])
        if substep == 0:
            target = 0
        elif substep == 5 and cycle < 73:
            target = cycle
        else:
            target = None
        if target is not None:
            d_pre[target] = state.d_node
            history_pre[target] = state.history_gp
            pre_filled[target] = True
        if substep == 4:
            target = cycle - 1
            d_peak[target] = state.d_node
            history_peak[target] = state.history_gp
            u_peak[target] = state.u_node
            peak_filled[target] = True
    if not pre_filled.all() or not peak_filled.all():
        raise ValueError("endpoint population is incomplete")
    by_key = index_by_key(rows)
    logical_bindings = {}
    for key, row in by_key.items():
        source = row["source_state_key"]
        binding = physical_bindings.get(source)
        if binding is None or binding["payload_sha256"] != row["payload_sha256"]:
            raise ValueError(f"logical-to-physical decoded binding mismatch: {key}")
        imposed = float(row["imposed_displacement"])
        if not np.isfinite(imposed) or imposed != binding["imposed_displacement"]:
            raise ValueError(f"logical-to-physical load mismatch: {key}")
        logical_bindings[key] = {
            "source_state_key": source,
            "payload_sha256": row["payload_sha256"],
            "imposed_displacement": imposed,
            "decoded_array_fingerprints": binding,
        }
    if len(logical_bindings) != 438:
        raise ValueError("decoded logical binding count mismatch")
    decode_receipt = {
        "verdict": "FULL_TRAJECTORY_DECODE_QUALIFIED",
        "context_sha256": context.digest,
        "source_hash_qualification": hash_receipt["verdict"],
        "decoded_physical_payload_count": len(physical_bindings),
        "decoded_logical_state_count": len(logical_bindings),
        "decoded_substeps": list(range(6)),
        "history_channel_order": list(context.history_channel_order),
        "history_channel_semantics": "source-bound-not-directly-decoded",
        "logical_state_bindings": logical_bindings,
    }
    result = freeze_p1_contract(
        cycles=np.arange(1, 74, dtype=np.int64),
        d_pre=d_pre, d_peak=d_peak,
        history_pre=history_pre, history_peak=history_peak, u_peak=u_peak,
        nodal_weight=nodal_weight, gp_weight=gp_weight,
    )
    result.update({
        "source_context_sha256": context.digest,
        "source_static_sha256": context.static_sha256,
        "native_weight_receipt": weight_receipt,
        "source_decode_verdict": decode_receipt["verdict"],
        "qualified_six_state_trajectory": True,
    })
    return result, hash_receipt, decode_receipt


def qualify_decode_and_freeze_s09_e008(
    run_root: Path,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    """Exact sealed-run route.  It performs no training or optimiser update."""
    return _qualify_decode_and_freeze(run_root=run_root, context=S09_E008_CONTEXT)
