from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import stat
import uuid
from importlib import metadata
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import loadmat
from scipy.io.matlab import mat_struct


class ProtocolError(RuntimeError):
    """Raised when a package or repeatability gate fails closed."""


REQUIRED_H5PY_VERSION = "3.16.0"


def _require_runtime_dependencies() -> dict[str, str]:
    try:
        installed = metadata.version("h5py")
    except metadata.PackageNotFoundError as exception:
        raise ProtocolError(
            f"runtime dependency h5py must be exactly {REQUIRED_H5PY_VERSION}; "
            "the distribution is missing"
        ) from exception
    if installed != REQUIRED_H5PY_VERSION:
        raise ProtocolError(
            f"runtime dependency h5py must be exactly {REQUIRED_H5PY_VERSION}; "
            f"found {installed}"
        )
    return {"h5py": installed}


RUNTIME_DEPENDENCY_IDENTITY = _require_runtime_dependencies()

try:
    import h5py
except ImportError as exception:
    raise ProtocolError(
        f"runtime dependency h5py must be exactly {REQUIRED_H5PY_VERSION}; "
        "the module cannot be imported"
    ) from exception

if h5py.__version__ != REQUIRED_H5PY_VERSION:
    raise ProtocolError(
        f"runtime dependency h5py must be exactly {REQUIRED_H5PY_VERSION}; "
        f"module reports {h5py.__version__}"
    )


def runtime_dependency_identity() -> dict[str, str]:
    """Return the exact Task 2 dependency identity for runtime receipts."""
    return dict(RUNTIME_DEPENDENCY_IDENTITY)


PROTOCOL_VERSION = "toy-road-p0-repeatability-v2.1"
THRESHOLD = 1e-12
RANGE_TOLERANCE = 1e-10
TRAJECTORY_FIELDS = (
    "d_node",
    "d_gp",
    "alpha_bar_gp",
    "f_alpha_gp",
    "psi_raw_gp",
    "g_gp",
    "psi_active_gp",
    "psi_raw_cyclemax_gp",
)
SHARD_FIELDS = {
    *TRAJECTORY_FIELDS,
    "cycle",
    "substep_ordinal",
    "load_factor",
    "raw_step_zero_based",
    "branch",
    "mesh_sha256",
    "element_ordering_id",
    "gp_ordering_id",
    "state_semantics_id",
    "runtime_lock_sha256",
    "family_contract_sha256",
    "case_physics_contract_sha256",
    "execution_input_lock_sha256",
}
MANIFEST_FIELDS = {
    "authorization_scope",
    "protocol_version",
    "case_id",
    "source_commit",
    "mesh_sha256",
    "element_ordering_id",
    "gp_ordering_id",
    "state_semantics_id",
    "runtime_lock_sha256",
    "family_contract_sha256",
    "case_physics_contract_sha256",
    "physical_input_sha256",
    "solver_sha256",
    "recovery_sha256",
    "exporter_sha256",
    "numerical_gate_contract_sha256",
    "event_contract_sha256",
    "execution_input_lock_sha256",
    "files",
}
PACKAGE_IDENTITY_FIELDS = (
    "protocol_version",
    "source_commit",
    "runtime_lock_sha256",
    "family_contract_sha256",
    "case_physics_contract_sha256",
    "mesh_sha256",
    "element_ordering_id",
    "gp_ordering_id",
    "state_semantics_id",
    "physical_input_sha256",
    "solver_sha256",
    "recovery_sha256",
    "exporter_sha256",
    "numerical_gate_contract_sha256",
    "event_contract_sha256",
)
TRACE_COLUMNS = (
    "authorization_scope",
    "case_id",
    "cycle",
    "substep_ordinal",
    "stagger_iteration",
    "reassembly_ordinal",
    "displacement_residual",
    "raw_phase_residual",
    "projected_phase_kkt",
    "consecutive_stagger_delta",
    "primal_feasibility",
)
C5_RECEIPT_FIELDS = {
    "authorization_scope",
    "case_id",
    "cycle",
    "substep_ordinal",
    "status",
    "passed",
    "trace_sha256",
    "trace_row_count",
    "reassembly_count",
    "final_stagger_iteration",
    "final_reassembly_ordinal",
    "final_displacement_residual",
    "final_raw_phase_residual",
    "final_projected_phase_kkt",
    "final_consecutive_stagger_delta",
    "final_primal_feasibility",
    "displacement_residual_threshold",
    "projected_phase_kkt_threshold",
    "consecutive_stagger_delta_threshold",
    "primal_feasibility_threshold",
}
EVENT_FIELDS = {
    "authorization_scope",
    "case_id",
    "first_hit_cycle",
    "confirmed_cycle",
    "terminal_cycle",
    "peak_substep_ordinal",
    "cycle_shard",
    "cycle_shard_sha256",
}
TERMINAL_FIELDS = {
    "authorization_scope",
    "case_id",
    "terminal_reason",
    "terminal_cycle",
    "first_hit_cycle",
    "confirmed_cycle",
}


def relative_l2(candidate: np.ndarray, reference: np.ndarray) -> float:
    delta = np.asarray(candidate, dtype=np.float64).reshape(-1, order="F") - \
        np.asarray(reference, dtype=np.float64).reshape(-1, order="F")
    ref = np.asarray(reference, dtype=np.float64).reshape(-1, order="F")
    return float(np.linalg.norm(delta) / max(np.linalg.norm(ref), 1e-30))


def read_mat_struct(path: Path, variable: str) -> dict[str, Any]:
    try:
        payload = Path(path).read_bytes()
    except OSError as exception:
        raise ProtocolError(f"cannot read MAT file {path}: {exception}") from exception
    return _read_mat_struct_bytes(payload, variable, str(path))


def compare_repeatability(p0_root: Path, p0r_root: Path) -> dict[str, object]:
    p0_input = Path(p0_root)
    p0r_input = Path(p0r_root)
    destination = p0_input.absolute().parent / "P0_REPEATABILITY_EVIDENCE_LOCK.json"
    if os.path.lexists(destination):
        raise ProtocolError(f"evidence lock already exists: {destination}")

    p0_canonical = _canonical_package_root(p0_input, "P0")
    p0r_canonical = _canonical_package_root(p0r_input, "P0R")
    if os.path.normcase(str(p0_canonical)) == os.path.normcase(str(p0r_canonical)):
        raise ProtocolError("P0 and P0R package roots must be distinct")
    try:
        if os.path.samefile(p0_canonical, p0r_canonical):
            raise ProtocolError("P0 and P0R package roots must be distinct")
    except OSError:
        pass

    p0 = _validate_package(p0_canonical, "P0", "P0_parent")
    p0r = _validate_package(p0r_canonical, "P0R", "P0R_parent_repeat")
    if p0["manifest"]["execution_input_lock_sha256"] == p0r["manifest"][
        "execution_input_lock_sha256"
    ]:
        raise ProtocolError("P0 and P0R must use distinct execution locks")

    for field in PACKAGE_IDENTITY_FIELDS:
        if p0["manifest"][field] != p0r["manifest"][field]:
            raise ProtocolError(f"exact {field} identity mismatch")
    if p0["manifest"]["authorization_scope"] != p0r["manifest"][
        "authorization_scope"
    ]:
        raise ProtocolError("exact authorization_scope identity mismatch")

    _require_equal_event_and_terminal(p0, p0r)
    _require_equal_state0(p0["state0"], p0r["state0"])

    field_metrics: list[dict[str, object]] = []
    maximum_relative = 0.0
    maximum_absolute = 0.0
    for cycle, (reference_shard, candidate_shard) in enumerate(
        zip(p0["shards"], p0r["shards"], strict=True), start=1
    ):
        for field in SHARD_FIELDS - set(TRAJECTORY_FIELDS) - {
            "execution_input_lock_sha256"
        }:
            if not _exact_equal(candidate_shard[field], reference_shard[field]):
                raise ProtocolError(f"cycle {cycle} exact {field} identity mismatch")
        for field in TRAJECTORY_FIELDS:
            candidate = _require_double_array(
                candidate_shard[field], f"P0R cycle {cycle}.{field}"
            )
            reference = _require_double_array(
                reference_shard[field], f"P0 cycle {cycle}.{field}"
            )
            if candidate.shape != reference.shape:
                raise ProtocolError(f"cycle {cycle} field {field} shape mismatch")
            metric = _compute_field_metric(candidate, reference)
            zero_reference = metric["relative_l2"] == "not_applicable_zero_reference"
            relative = 0.0 if zero_reference else float(metric["relative_l2"])
            _require_metric_within_threshold(
                relative, float(metric["max_absolute"]), zero_reference
            )
            if not zero_reference:
                maximum_relative = max(maximum_relative, relative)
            maximum_absolute = max(maximum_absolute, float(metric["max_absolute"]))
            field_metrics.append(
                {"cycle": cycle, "field": field, "shape": list(reference.shape), **metric}
            )

    evidence: dict[str, object] = {
        "authorization_scope": p0["manifest"]["authorization_scope"],
        "status": "PASS",
        "protocol_version": p0["manifest"]["protocol_version"],
        "source_commit": p0["manifest"]["source_commit"],
        "runtime_lock_sha256": p0["manifest"]["runtime_lock_sha256"],
        "exporter_sha256": p0["manifest"]["exporter_sha256"],
        "p0_manifest_sha256": p0["manifest_sha256"],
        "p0r_manifest_sha256": p0r["manifest_sha256"],
        "p0_c5_receipt_sha256": p0["c5_receipt_sha256"],
        "p0r_c5_receipt_sha256": p0r["c5_receipt_sha256"],
        "p0_execution_input_lock_sha256": p0["manifest"][
            "execution_input_lock_sha256"
        ],
        "p0r_execution_input_lock_sha256": p0r["manifest"][
            "execution_input_lock_sha256"
        ],
        "threshold_relative_l2": THRESHOLD,
        "threshold_max_absolute": THRESHOLD,
        "trajectory_max_relative_l2": maximum_relative,
        "trajectory_max_absolute": maximum_absolute,
        "field_metrics": field_metrics,
    }
    _verify_package_snapshot(p0)
    _verify_package_snapshot(p0r)
    _publish_json_exclusive(destination, evidence)
    return evidence


def _validate_package(root: Path, label: str, expected_case_id: str) -> dict[str, Any]:
    snapshot = _capture_package_bytes(root, label)
    manifest = _read_json_bytes(
        snapshot["bytes"].get("TERMINAL_MANIFEST.json"), f"{label} terminal manifest"
    )
    _require_exact_fields(manifest, MANIFEST_FIELDS, f"{label} terminal manifest")
    if manifest["protocol_version"] != PROTOCOL_VERSION or not isinstance(
        manifest["protocol_version"], str
    ):
        raise ProtocolError(f"{label} protocol_version is invalid")
    if manifest["case_id"] != expected_case_id or not isinstance(
        manifest["case_id"], str
    ):
        raise ProtocolError(f"{label} case_id does not match its exact role")
    authorization_scope = _require_nonempty_text(
        manifest["authorization_scope"], f"{label} authorization_scope"
    )
    _validate_manifest_identities(manifest, label)
    _validate_manifest_closure(manifest, snapshot, label)

    required_paths = {
        "EXECUTION_INPUT_LOCK.json",
        "STATE0.mat",
        "EVENT_METADATA.json",
        "TERMINAL_RESULT.json",
        "qualification/C5_STAGGER_TRACE.csv",
        "qualification/C5_NUMERICAL_GATE_RECEIPT.json",
    }
    if not required_paths.issubset(snapshot["bytes"]):
        raise ProtocolError(f"{label} package is missing a required artifact")

    lock_bytes = snapshot["bytes"]["EXECUTION_INPUT_LOCK.json"]
    execution_digest = _sha256_bytes(lock_bytes)
    if execution_digest != manifest["execution_input_lock_sha256"]:
        raise ProtocolError(f"{label} execution lock is inconsistent with its manifest")
    lock = _read_json_bytes(lock_bytes, f"{label} execution lock")
    if lock.get("authorization_scope") != authorization_scope or lock.get(
        "case_id"
    ) != expected_case_id:
        raise ProtocolError(f"{label} execution lock case_id or scope is inconsistent")

    _validate_c5(snapshot, manifest, label)
    event = _read_json_bytes(snapshot["bytes"]["EVENT_METADATA.json"], f"{label} event")
    terminal = _read_json_bytes(
        snapshot["bytes"]["TERMINAL_RESULT.json"], f"{label} terminal result"
    )
    _require_exact_fields(event, EVENT_FIELDS, f"{label} event")
    _require_exact_fields(terminal, TERMINAL_FIELDS, f"{label} terminal result")
    _validate_event_terminal(event, terminal, manifest, snapshot, label)

    terminal_cycle = terminal["terminal_cycle"]
    cycle_paths = sorted(
        path
        for path in snapshot["bytes"]
        if re.fullmatch(r"substeps/cycle_[0-9]{4}\.mat", path)
    )
    expected_cycle_paths = [
        f"substeps/cycle_{cycle:04d}.mat" for cycle in range(1, terminal_cycle + 1)
    ]
    if cycle_paths != expected_cycle_paths:
        raise ProtocolError(f"{label} cycle coverage is not consecutive")

    state0 = _read_mat_struct_bytes(
        snapshot["bytes"]["STATE0.mat"], "state0", f"{label} state0"
    )
    _require_exact_fields(state0, {"d_node", "alpha_bar_gp"}, f"{label} state0")
    state0_damage = _require_double_array(state0["d_node"], f"{label} state0.d_node")
    state0_alpha = _require_double_array(
        state0["alpha_bar_gp"], f"{label} state0.alpha_bar_gp"
    )
    if (
        state0_damage.ndim != 2
        or state0_damage.shape[1] != 1
        or state0_damage.shape[0] == 0
        or state0_alpha.ndim != 2
        or state0_alpha.shape[1] != 4
        or state0_alpha.shape[0] == 0
    ):
        raise ProtocolError(f"{label} state0 shape is invalid")
    if np.any(state0_damage < -THRESHOLD) or np.any(state0_damage > 1 + THRESHOLD):
        raise ProtocolError(f"{label} state0 damage lies outside [0, 1]")
    if np.any(state0_alpha < -THRESHOLD):
        raise ProtocolError(f"{label} state0 alpha must be nonnegative")

    shards: list[dict[str, Any]] = []
    previous_damage = state0_damage[:, 0]
    previous_alpha = state0_alpha
    for cycle, relative in enumerate(cycle_paths, start=1):
        shard = _read_mat_struct_bytes(
            snapshot["bytes"][relative], "shard", f"{label} cycle {cycle}"
        )
        previous_damage, previous_alpha = _validate_shard(
            shard,
            manifest,
            cycle,
            label,
            previous_damage,
            previous_alpha,
            state0_damage.shape[0],
            state0_alpha.shape[0],
        )
        shards.append(shard)

    _verify_package_snapshot({"root": root, "snapshot": snapshot})
    return {
        "root": root,
        "snapshot": snapshot,
        "manifest": manifest,
        "manifest_sha256": _sha256_bytes(snapshot["bytes"]["TERMINAL_MANIFEST.json"]),
        "c5_receipt_sha256": _sha256_bytes(
            snapshot["bytes"]["qualification/C5_NUMERICAL_GATE_RECEIPT.json"]
        ),
        "event": event,
        "terminal": terminal,
        "state0": state0,
        "shards": shards,
    }


def _validate_shard(
    shard: dict[str, Any],
    manifest: dict[str, Any],
    cycle: int,
    label: str,
    previous_damage: np.ndarray,
    previous_alpha: np.ndarray,
    n_node: int,
    n_elem: int,
) -> tuple[np.ndarray, np.ndarray]:
    _require_exact_fields(shard, SHARD_FIELDS, f"{label} cycle {cycle}")
    numeric_names = {
        *TRAJECTORY_FIELDS,
        "cycle",
        "substep_ordinal",
        "load_factor",
        "raw_step_zero_based",
    }
    values = {
        name: _require_double_array(shard[name], f"{label} cycle {cycle}.{name}")
        for name in numeric_names
    }
    cycle_value = values["cycle"]
    if cycle_value.size != 1 or float(cycle_value.reshape(-1)[0]) != cycle:
        raise ProtocolError(f"{label} cycle ordinal must be an exact integer scalar")
    if not (
        values["substep_ordinal"].shape == (1, 5)
        and np.array_equal(values["substep_ordinal"], np.arange(1.0, 6.0).reshape(1, 5))
        and values["load_factor"].shape == (1, 5)
        and np.array_equal(values["load_factor"], [[0.25, 0.5, 0.75, 1.0, 0.0]])
        and values["raw_step_zero_based"].shape == (1, 5)
        and np.array_equal(
            values["raw_step_zero_based"],
            (5 * (cycle - 1) + np.arange(5.0)).reshape(1, 5),
        )
        and _text_cell_values(shard["branch"]) == [
            "loading", "loading", "loading", "loading", "unloading"
        ]
    ):
        raise ProtocolError(f"{label} cycle {cycle} chronology schedule is invalid")

    for field in (
        "mesh_sha256",
        "element_ordering_id",
        "gp_ordering_id",
        "state_semantics_id",
        "runtime_lock_sha256",
        "family_contract_sha256",
        "case_physics_contract_sha256",
        "execution_input_lock_sha256",
    ):
        if _require_nonempty_text(shard[field], f"{label} cycle {cycle}.{field}") != manifest[field]:
            raise ProtocolError(f"{label} cycle {cycle} {field} is not package-local")

    d_node = values["d_node"]
    d_gp = values["d_gp"]
    if d_node.shape != (n_node, 5) or d_gp.shape != (n_elem, 4, 5):
        raise ProtocolError(f"{label} cycle {cycle} physical state shape is invalid")
    for field in ("alpha_bar_gp", "f_alpha_gp", "psi_raw_gp", "g_gp", "psi_active_gp"):
        if values[field].shape != (n_elem, 4, 5):
            raise ProtocolError(f"{label} cycle {cycle}.{field} shape is invalid")
    if values["psi_raw_cyclemax_gp"].shape != (n_elem, 4):
        raise ProtocolError(f"{label} cycle {cycle} cycle maximum shape is invalid")

    alpha = values["alpha_bar_gp"]
    for substep in range(5):
        if np.any(d_node[:, substep] < previous_damage - THRESHOLD) or np.any(
            d_node[:, substep] > 1 + THRESHOLD
        ):
            raise ProtocolError(f"{label} cycle {cycle} damage chronology or bounds failed")
        if np.any(alpha[:, :, substep] < previous_alpha - THRESHOLD):
            raise ProtocolError(f"{label} cycle {cycle} alpha chronology failed")
        previous_damage = d_node[:, substep]
        previous_alpha = alpha[:, :, substep]

    f_alpha = values["f_alpha_gp"]
    raw = values["psi_raw_gp"]
    g_gp = values["g_gp"]
    active = values["psi_active_gp"]
    if np.any(d_gp < -RANGE_TOLERANCE) or np.any(d_gp > 1 + RANGE_TOLERANCE):
        raise ProtocolError(f"{label} cycle {cycle} d_gp range failed")
    if np.any(alpha < -THRESHOLD):
        raise ProtocolError(f"{label} cycle {cycle} alpha must be nonnegative")
    if np.any(f_alpha < -THRESHOLD) or np.any(f_alpha > 1 + THRESHOLD):
        raise ProtocolError(f"{label} cycle {cycle} f_alpha range failed")
    if np.any(g_gp < -RANGE_TOLERANCE) or np.any(g_gp > 1 + RANGE_TOLERANCE):
        raise ProtocolError(f"{label} cycle {cycle} g range failed")
    if np.any(raw < -RANGE_TOLERANCE) or np.any(active < -RANGE_TOLERANCE):
        raise ProtocolError(f"{label} cycle {cycle} raw or active driver range failed")

    f_expected = np.minimum(1.0, (1.0 - ((alpha - 0.5) / (alpha + 0.5))) ** 2)
    errors = (
        np.max(np.abs(f_alpha - f_expected)),
        np.max(np.abs(g_gp - (1.0 - d_gp) ** 2)),
        np.max(np.abs(active - g_gp * raw)),
        np.max(np.abs(values["psi_raw_cyclemax_gp"] - np.max(raw, axis=2))),
    )
    if max(float(error) for error in errors) > THRESHOLD:
        raise ProtocolError(f"{label} cycle {cycle} constitutive identity failed")
    return previous_damage, previous_alpha


def _compute_field_metric(candidate: np.ndarray, reference: np.ndarray) -> dict[str, object]:
    candidate_array = np.asarray(candidate)
    reference_array = np.asarray(reference)
    if candidate_array.shape != reference_array.shape:
        raise ProtocolError("field shape mismatch")
    delta = candidate_array.reshape(-1, order="F") - reference_array.reshape(-1, order="F")
    maximum = float(np.max(np.abs(delta))) if delta.size else 0.0
    if bool(np.all(reference_array == 0.0)):
        return {
            "relative_l2": "not_applicable_zero_reference",
            "max_absolute": maximum,
        }
    return {"relative_l2": relative_l2(candidate_array, reference_array), "max_absolute": maximum}


def _require_metric_within_threshold(
    relative: float, maximum: float, zero_reference: bool
) -> None:
    if maximum > THRESHOLD or (not zero_reference and relative > THRESHOLD):
        raise ProtocolError("trajectory field exceeds repeatability threshold")


def _validate_c5(snapshot: dict[str, Any], manifest: dict[str, Any], label: str) -> None:
    trace_name = "qualification/C5_STAGGER_TRACE.csv"
    receipt_name = "qualification/C5_NUMERICAL_GATE_RECEIPT.json"
    trace_bytes = snapshot["bytes"][trace_name]
    receipt = _read_json_bytes(snapshot["bytes"][receipt_name], f"{label} c5 receipt")
    _require_exact_fields(receipt, C5_RECEIPT_FIELDS, f"{label} c5 receipt")
    try:
        reader = csv.DictReader(io.StringIO(trace_bytes.decode("ascii"), newline=""))
        if tuple(reader.fieldnames or ()) != TRACE_COLUMNS:
            raise ProtocolError(f"{label} c5 trace columns are invalid")
        rows = list(reader)
    except (UnicodeDecodeError, csv.Error) as exception:
        raise ProtocolError(f"{label} c5 trace is malformed: {exception}") from exception
    if not rows:
        raise ProtocolError(f"{label} c5 trace is empty")
    parsed_rows: list[dict[str, object]] = []
    for index, row in enumerate(rows, start=1):
        if set(row) != set(TRACE_COLUMNS) or any(value is None for value in row.values()):
            raise ProtocolError(f"{label} c5 trace row is malformed")
        parsed = {
            "authorization_scope": row["authorization_scope"],
            "case_id": row["case_id"],
            "cycle": _parse_csv_int(row["cycle"], f"{label} c5 cycle"),
            "substep_ordinal": _parse_csv_int(row["substep_ordinal"], f"{label} c5 substep"),
            "stagger_iteration": _parse_csv_int(row["stagger_iteration"], f"{label} c5 iteration"),
            "reassembly_ordinal": _parse_csv_int(row["reassembly_ordinal"], f"{label} c5 reassembly"),
        }
        for field in TRACE_COLUMNS[6:]:
            parsed[field] = _parse_csv_float(row[field], f"{label} c5 {field}")
            if parsed[field] < 0:
                raise ProtocolError(f"{label} c5 metrics must be nonnegative")
        if not (
            parsed["authorization_scope"] == manifest["authorization_scope"]
            and parsed["case_id"] == manifest["case_id"]
            and parsed["cycle"] == 5
            and parsed["substep_ordinal"] == 4
            and parsed["stagger_iteration"] == index
            and parsed["reassembly_ordinal"] == index
        ):
            raise ProtocolError(f"{label} c5 trace identity or chronology is invalid")
        parsed_rows.append(parsed)

    final = parsed_rows[-1]
    expected_thresholds = {
        "displacement_residual_threshold": 4e-4,
        "projected_phase_kkt_threshold": 4e-4,
        "consecutive_stagger_delta_threshold": 1e-3,
        "primal_feasibility_threshold": 1e-12,
    }
    for field, expected in expected_thresholds.items():
        if not _exact_json_number(receipt[field], expected):
            raise ProtocolError(f"{label} c5 threshold {field} is invalid")
    integer_expectations = {
        "cycle": 5,
        "substep_ordinal": 4,
        "trace_row_count": len(parsed_rows),
        "reassembly_count": len(parsed_rows),
        "final_stagger_iteration": final["stagger_iteration"],
        "final_reassembly_ordinal": final["reassembly_ordinal"],
    }
    for field, expected in integer_expectations.items():
        if not _exact_json_int(receipt[field], int(expected)):
            raise ProtocolError(f"{label} c5 receipt {field} is invalid")
    metric_fields = {
        "final_displacement_residual": "displacement_residual",
        "final_raw_phase_residual": "raw_phase_residual",
        "final_projected_phase_kkt": "projected_phase_kkt",
        "final_consecutive_stagger_delta": "consecutive_stagger_delta",
        "final_primal_feasibility": "primal_feasibility",
    }
    for receipt_field, trace_field in metric_fields.items():
        if not _exact_json_number(receipt[receipt_field], float(final[trace_field])):
            raise ProtocolError(f"{label} c5 final metric {receipt_field} is invalid")
    if not (
        receipt["authorization_scope"] == manifest["authorization_scope"]
        and receipt["case_id"] == manifest["case_id"]
        and receipt["status"] == "PASS"
        and receipt["passed"] is True
        and receipt["trace_sha256"] == _sha256_bytes(trace_bytes)
        and receipt["final_displacement_residual"] <= receipt["displacement_residual_threshold"]
        and receipt["final_projected_phase_kkt"] <= receipt["projected_phase_kkt_threshold"]
        and receipt["final_consecutive_stagger_delta"] <= receipt["consecutive_stagger_delta_threshold"]
        and receipt["final_primal_feasibility"] <= receipt["primal_feasibility_threshold"]
    ):
        raise ProtocolError(f"{label} case-local c5 gate did not pass")


def _validate_event_terminal(
    event: dict[str, Any],
    terminal: dict[str, Any],
    manifest: dict[str, Any],
    snapshot: dict[str, Any],
    label: str,
) -> None:
    integer_fields = ("first_hit_cycle", "confirmed_cycle", "terminal_cycle")
    for field in integer_fields:
        if not _exact_json_int(event[field]) or not _exact_json_int(terminal[field]):
            raise ProtocolError(f"{label} event {field} is invalid")
    if not _exact_json_int(event["peak_substep_ordinal"], 4):
        raise ProtocolError(f"{label} event peak substep is invalid")
    if not (
        event["authorization_scope"] == manifest["authorization_scope"]
        and terminal["authorization_scope"] == manifest["authorization_scope"]
        and event["case_id"] == manifest["case_id"]
        and terminal["case_id"] == manifest["case_id"]
        and all(event[field] == terminal[field] for field in integer_fields)
        and terminal["terminal_cycle"] >= 5
        and terminal["confirmed_cycle"] == terminal["first_hit_cycle"] + 3
        and terminal["confirmed_cycle"] == terminal["terminal_cycle"]
        and terminal["terminal_reason"] == "confirmed_penetration"
    ):
        raise ProtocolError(f"{label} event and terminal metadata are inconsistent")
    expected_path = f"substeps/cycle_{event['confirmed_cycle']:04d}.mat"
    if expected_path not in snapshot["bytes"] or not (
        event["cycle_shard"] == expected_path
        and event["cycle_shard_sha256"] == _sha256_bytes(snapshot["bytes"][expected_path])
    ):
        raise ProtocolError(f"{label} event does not identify its authenticated cycle shard")


def _require_equal_event_and_terminal(p0: dict[str, Any], p0r: dict[str, Any]) -> None:
    for field in EVENT_FIELDS - {"authorization_scope", "case_id", "cycle_shard_sha256"}:
        if p0["event"][field] != p0r["event"][field]:
            raise ProtocolError(f"event {field} mismatch")
    for field in TERMINAL_FIELDS - {"authorization_scope", "case_id"}:
        if p0["terminal"][field] != p0r["terminal"][field]:
            raise ProtocolError(f"terminal {field} mismatch")


def _require_equal_state0(reference: dict[str, Any], candidate: dict[str, Any]) -> None:
    if set(reference) != set(candidate):
        raise ProtocolError("state0 field-name mismatch")
    for field in reference:
        if not _exact_equal(candidate[field], reference[field]):
            raise ProtocolError(f"state0 exact {field} mismatch")


def _read_mat_struct_bytes(payload: bytes, variable: str, label: str) -> dict[str, Any]:
    try:
        if payload.startswith(b"\x89HDF\r\n\x1a\n") or payload[512:520] == b"\x89HDF\r\n\x1a\n":
            with h5py.File(io.BytesIO(payload), "r") as handle:
                if variable not in handle:
                    raise ProtocolError(f"{label} is missing variable {variable}")
                node = handle[variable]
                if not isinstance(node, h5py.Group) or _h5_class(node) != "struct":
                    raise ProtocolError(f"{label} must contain one scalar struct")
                return {name: _decode_h5(handle, node[name]) for name in node.keys()}
        loaded = loadmat(io.BytesIO(payload), struct_as_record=False, squeeze_me=False)
        if variable not in loaded:
            raise ProtocolError(f"{label} is missing variable {variable}")
        value = loaded[variable]
        if not isinstance(value, np.ndarray) or value.size != 1:
            raise ProtocolError(f"{label} must contain one scalar struct")
        decoded = _decode_legacy(value.reshape(-1)[0])
        if not isinstance(decoded, dict):
            raise ProtocolError(f"{label} must contain one scalar struct")
        return decoded
    except ProtocolError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as exception:
        raise ProtocolError(f"cannot load {label}: {exception}") from exception


def _decode_legacy(value: object) -> object:
    if isinstance(value, mat_struct):
        return {name: _decode_legacy(getattr(value, name)) for name in value._fieldnames}
    if isinstance(value, np.ndarray) and value.dtype == object:
        output = np.empty(value.shape, dtype=object)
        for index in np.ndindex(value.shape):
            output[index] = _decode_legacy(value[index])
        return output
    if isinstance(value, np.ndarray) and value.dtype.kind in {"U", "S"}:
        strings = value.astype(str)
        if strings.size == 1:
            return str(strings.reshape(-1)[0])
        if strings.ndim == 2:
            rows = ["".join(row.tolist()) for row in strings]
            return rows[0] if len(rows) == 1 else np.asarray(rows, dtype=object)
    return value


def _decode_h5(handle: h5py.File, node: h5py.Group | h5py.Dataset) -> object:
    matlab_class = _h5_class(node)
    if isinstance(node, h5py.Group):
        if matlab_class != "struct":
            raise ProtocolError(f"unsupported MATLAB/HDF5 group class {matlab_class}")
        return {name: _decode_h5(handle, node[name]) for name in node.keys()}
    data = np.asarray(node[()])
    data = np.transpose(data, axes=tuple(reversed(range(data.ndim)))) if data.ndim else data
    if matlab_class == "double":
        if data.dtype.kind != "f" or data.dtype.itemsize != 8:
            raise ProtocolError("MATLAB double dataset does not have real double semantics")
        return data.astype(np.float64, copy=False)
    if matlab_class == "char":
        codes = data.astype(np.uint16, copy=False)
        if codes.ndim == 1:
            return "".join(chr(int(code)) for code in codes)
        rows = ["".join(chr(int(code)) for code in row) for row in codes]
        return rows[0] if len(rows) == 1 else np.asarray(rows, dtype=object)
    if matlab_class == "cell":
        output = np.empty(data.shape, dtype=object)
        for index in np.ndindex(data.shape):
            reference = data[index]
            output[index] = None if not reference else _decode_h5(handle, handle[reference])
        return output
    if matlab_class == "logical":
        return data.astype(bool)
    raise ProtocolError(f"unsupported MATLAB/HDF5 dataset class {matlab_class}")


def _h5_class(node: h5py.Group | h5py.Dataset) -> str:
    value = node.attrs.get("MATLAB_class", "")
    if isinstance(value, bytes):
        return value.decode("ascii")
    if isinstance(value, np.bytes_):
        return bytes(value).decode("ascii")
    return str(value)


def _capture_package_bytes(root: Path, label: str) -> dict[str, Any]:
    _require_not_link_or_reparse(root, f"{label} package root")
    if not root.is_dir():
        raise ProtocolError(f"{label} package root is missing")
    files: dict[str, bytes] = {}
    folded: dict[str, str] = {}

    def visit(directory: Path) -> None:
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except OSError as exception:
            raise ProtocolError(f"cannot scan {label} package: {exception}") from exception
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            _require_not_link_or_reparse(path, f"{label} package path {relative}")
            folded_name = relative.casefold()
            if folded_name in folded and folded[folded_name] != relative:
                raise ProtocolError(f"{label} package has a case-folded path collision")
            folded[folded_name] = relative
            if entry.is_dir(follow_symlinks=False):
                visit(path)
            elif entry.is_file(follow_symlinks=False):
                try:
                    files[relative] = path.read_bytes()
                except OSError as exception:
                    raise ProtocolError(f"cannot read {label} package path {relative}: {exception}") from exception
            else:
                raise ProtocolError(f"{label} package contains a non-file path")

    visit(root)
    return {"bytes": files}


def _validate_manifest_closure(
    manifest: dict[str, Any], snapshot: dict[str, Any], label: str
) -> None:
    entries = manifest["files"]
    if not isinstance(entries, list) or not entries:
        raise ProtocolError(f"{label} manifest files must be a nonempty list")
    paths: list[str] = []
    folded: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise ProtocolError(f"{label} manifest file entry schema is malformed")
        relative = entry["path"]
        if not isinstance(relative, str) or not _canonical_relative_path(relative):
            raise ProtocolError(f"{label} manifest file path is not canonical")
        if not _is_sha256(entry["sha256"]):
            raise ProtocolError(f"{label} manifest file hash is not canonical")
        folded_name = relative.casefold()
        if folded_name in folded and folded[folded_name] != relative:
            raise ProtocolError(f"{label} manifest has a case-folded path collision")
        folded[folded_name] = relative
        paths.append(relative)
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ProtocolError(f"{label} manifest paths are not sorted and unique")
    actual = sorted(set(snapshot["bytes"]) - {"TERMINAL_MANIFEST.json"})
    if paths != actual:
        raise ProtocolError(f"{label} package manifest is incomplete or mutable")
    for entry in entries:
        if _sha256_bytes(snapshot["bytes"][entry["path"]]) != entry["sha256"]:
            raise ProtocolError(f"{label} package bytes do not match manifest hash")


def _verify_package_snapshot(package: dict[str, Any]) -> None:
    fresh = _capture_package_bytes(package["root"], "authenticated")
    if fresh["bytes"] != package["snapshot"]["bytes"]:
        raise ProtocolError("authenticated package snapshot changed or became mutable")


def _canonical_package_root(root: Path, label: str) -> Path:
    _require_not_link_or_reparse(root, f"{label} package root")
    try:
        return root.resolve(strict=True)
    except OSError as exception:
        raise ProtocolError(f"{label} package root is missing: {exception}") from exception


def _require_not_link_or_reparse(path: Path, label: str) -> None:
    try:
        info = path.lstat()
    except OSError as exception:
        raise ProtocolError(f"{label} is missing: {exception}") from exception
    attributes = getattr(info, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if stat.S_ISLNK(info.st_mode) or bool(attributes & reparse):
        raise ProtocolError(f"{label} must not be a link or reparse point")


def _read_json_bytes(payload: bytes | None, label: str) -> dict[str, Any]:
    if payload is None:
        raise ProtocolError(f"{label} is missing")
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exception:
        raise ProtocolError(f"cannot read {label}: {exception}") from exception
    if not isinstance(value, dict):
        raise ProtocolError(f"{label} must be one JSON object")
    return value


def _validate_manifest_identities(manifest: dict[str, Any], label: str) -> None:
    if not (
        isinstance(manifest["source_commit"], str)
        and re.fullmatch(r"[0-9a-f]{40}", manifest["source_commit"])
    ):
        raise ProtocolError(f"{label} source_commit is not canonical")
    for field in MANIFEST_FIELDS:
        if field.endswith("_sha256") and not _is_sha256(manifest[field]):
            raise ProtocolError(f"{label} {field} is not canonical SHA-256")
    for field in ("element_ordering_id", "gp_ordering_id", "state_semantics_id"):
        _require_nonempty_text(manifest[field], f"{label} {field}")


def _require_exact_fields(value: dict[str, Any], expected: set[str], label: str) -> None:
    missing = sorted(expected - set(value))
    extra = sorted(set(value) - expected)
    if missing:
        raise ProtocolError(f"{label} missing fields: {', '.join(missing)}")
    if extra:
        raise ProtocolError(f"{label} has unexpected schema fields: {', '.join(extra)}")


def _require_double_array(value: object, label: str) -> np.ndarray:
    if not isinstance(value, np.ndarray) or value.dtype.kind != "f" or value.dtype.itemsize != 8:
        raise ProtocolError(f"{label} must be an exact real double array")
    normalized = value.astype(np.float64, copy=False)
    if not np.all(np.isfinite(normalized)):
        raise ProtocolError(f"{label} must be finite")
    return normalized


def _text_cell_values(value: object) -> list[str]:
    if not isinstance(value, np.ndarray) or value.dtype != object or value.shape != (1, 5):
        return []
    output: list[str] = []
    for item in value.reshape(-1, order="C"):
        if not isinstance(item, str):
            return []
        output.append(item)
    return output


def _require_nonempty_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ProtocolError(f"{label} must be nonempty text")
    return value


def _exact_equal(candidate: object, reference: object) -> bool:
    if isinstance(candidate, str) or isinstance(reference, str):
        return isinstance(candidate, str) and candidate == reference
    candidate_array = np.asarray(candidate)
    reference_array = np.asarray(reference)
    return candidate_array.shape == reference_array.shape and bool(
        np.array_equal(candidate_array, reference_array)
    )


def _parse_csv_int(value: str, label: str) -> int:
    if re.fullmatch(r"[1-9][0-9]*", value) is None:
        raise ProtocolError(f"{label} must be a canonical positive integer")
    return int(value)


def _parse_csv_float(value: str, label: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exception:
        raise ProtocolError(f"{label} must be numeric") from exception
    if not math.isfinite(parsed):
        raise ProtocolError(f"{label} must be finite")
    return parsed


def _exact_json_int(value: object, expected: int | None = None) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and (
        expected is None or value == expected
    )


def _exact_json_number(value: object, expected: float) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) == expected
    )


def _canonical_relative_path(value: str) -> bool:
    return (
        bool(value)
        and "\\" not in value
        and not value.startswith("/")
        and all(part not in {"", ".", ".."} for part in value.split("/"))
    )


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _publish_json_exclusive(destination: Path, value: object) -> None:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8") + b"\n"
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination)
    except FileExistsError as exception:
        raise ProtocolError(f"evidence lock already exists: {destination}") from exception
    except OSError as exception:
        raise ProtocolError(f"cannot publish evidence lock exclusively: {exception}") from exception
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
