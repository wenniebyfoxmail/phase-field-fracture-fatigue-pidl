"""Identity-bound, read-only capability adapter for S09-E008 Stage 0A.

The exact public wrapper is frozen to one sealed run.  It qualifies metadata,
static identity and all 366 unique payload hashes before any HDF5 decode.  P1
freezing additionally requires all 73 decoded s00/s04 pairs and weight hashes
bound to the same static file.
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

import numpy as np

from s09_stage0a_packet import (
    DecodedStage0AState,
    decode_stage0a_transitions,
    index_by_key,
    preflight_rows,
)
from s09_stage0a_p1_freeze import freeze_p1_contract, require_float64


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


def decode_s09_e008_all_endpoints(
    run_root: Path,
) -> tuple[
    dict[int, tuple[DecodedStage0AState, DecodedStage0AState]],
    dict[str, object],
    dict[str, object],
]:
    """Exact-run entry: qualify all six states, then decode all 73 s00/s04 pairs."""
    rows, qualification = qualify_s09_e008_full_trajectory(run_root)
    decoded, decode_receipt = decode_stage0a_transitions(
        states_dir=run_root / "states",
        rows=rows,
        cycles=list(range(1, 74)),
        expected_nodes=S09_E008_CONTEXT.expected_nodes,
        expected_elements=S09_E008_CONTEXT.expected_elements,
        expected_gp=S09_E008_CONTEXT.expected_gp,
    )
    pairs = {pre.logical_cycle: (pre, peak) for pre, peak in decoded}
    if set(pairs) != set(range(1, 74)):
        raise ValueError("decoded endpoint cycle coverage mismatch")
    decode_receipt.update({
        "source_context_sha256": S09_E008_CONTEXT.digest,
        "source_qualification_verdict": qualification["verdict"],
        "source_static_sha256": S09_E008_CONTEXT.static_sha256,
        "history_channel_semantics": "source-bound-not-directly-decoded",
    })
    return pairs, qualification, decode_receipt


def _array_sha256(value: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(value)
    return hashlib.sha256(contiguous.tobytes(order="C")).hexdigest()


def freeze_p1_from_qualified_pairs(
    *,
    pairs_by_cycle: dict[int, tuple[DecodedStage0AState, DecodedStage0AState]],
    qualification_receipt: dict[str, object],
    nodal_weight,
    gp_weight,
    weight_receipt: dict[str, object],
    context: Stage0ACapabilityContext = S09_E008_CONTEXT,
) -> dict:
    """Bind all 73 decoded pairs and native weights to the qualified archive."""
    if qualification_receipt.get("verdict") != "FULL_TRAJECTORY_HASH_QUALIFIED":
        raise ValueError("full trajectory is not qualified")
    if qualification_receipt.get("context_sha256") != context.digest:
        raise ValueError("qualification context mismatch")
    if qualification_receipt.get("qualified_cycles") != list(range(1, 74)):
        raise ValueError("incomplete qualified cycle set")
    if qualification_receipt.get("qualified_substeps") != list(range(6)):
        raise ValueError("incomplete six-state qualification")
    if qualification_receipt.get("unique_payload_count") != 366 or not qualification_receipt.get(
        "all_payload_hashes_preflighted"
    ):
        raise ValueError("incomplete physical payload qualification")
    if set(pairs_by_cycle) != set(range(1, 74)):
        raise ValueError("decoded pairs must cover exact cycles 1..73")
    nodal_weight = require_float64("nodal_weight", nodal_weight)
    gp_weight = require_float64("gp_weight", gp_weight)
    if nodal_weight.shape != (context.expected_nodes,):
        raise ValueError("nodal weights do not match frozen static dimensions")
    if gp_weight.shape != (context.expected_elements, context.expected_gp):
        raise ValueError("GP weights do not match frozen static dimensions")
    expected_weight_receipt = {
        "source_static_sha256": context.static_sha256,
        "node_order": "native",
        "element_order": "native",
        "gauss_point_order": "native quadrature",
        "nodal_weight_sha256": _array_sha256(nodal_weight),
        "gp_weight_sha256": _array_sha256(gp_weight),
        "nodal_weight_shape": list(nodal_weight.shape),
        "gp_weight_shape": list(gp_weight.shape),
    }
    if weight_receipt != expected_weight_receipt:
        raise ValueError("native weight receipt mismatch")
    pres, peaks = [], []
    for cycle in range(1, 74):
        pre, peak = pairs_by_cycle[cycle]
        if (pre.logical_cycle, pre.logical_substep) != (cycle, 0):
            raise ValueError(f"pre-state cycle mismatch: {cycle}")
        if (peak.logical_cycle, peak.logical_substep) != (cycle, 4):
            raise ValueError(f"peak-state cycle mismatch: {cycle}")
        if pre.history_gp.shape[-1] != len(context.history_channel_order):
            raise ValueError(f"history channel mismatch: {cycle}")
        pres.append(pre); peaks.append(peak)
    result = freeze_p1_contract(
        cycles=np.arange(1, 74, dtype=np.int64),
        d_pre=np.stack([state.d_node for state in pres]),
        d_peak=np.stack([state.d_node for state in peaks]),
        history_pre=np.stack([state.history_gp for state in pres]),
        history_peak=np.stack([state.history_gp for state in peaks]),
        u_peak=np.stack([state.u_node for state in peaks]),
        nodal_weight=nodal_weight,
        gp_weight=gp_weight,
    )
    result["source_context_sha256"] = context.digest
    result["source_static_sha256"] = context.static_sha256
    result["native_weight_receipt"] = weight_receipt
    result["qualified_six_state_trajectory"] = True
    return result
