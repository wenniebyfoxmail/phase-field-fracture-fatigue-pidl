from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import loadmat


class ProtocolError(RuntimeError):
    """Raised when a package or repeatability gate fails closed."""


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
SHARD_EXACT_FIELDS = (
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
)
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
THRESHOLD = 1e-12


def relative_l2(candidate: np.ndarray, reference: np.ndarray) -> float:
    delta = np.asarray(candidate, dtype=np.float64).reshape(-1, order="F") - \
        np.asarray(reference, dtype=np.float64).reshape(-1, order="F")
    ref = np.asarray(reference, dtype=np.float64).reshape(-1, order="F")
    return float(np.linalg.norm(delta) / max(np.linalg.norm(ref), 1e-30))


def compare_repeatability(p0_root: Path, p0r_root: Path) -> dict[str, object]:
    p0 = _validate_package(Path(p0_root), "P0")
    p0r = _validate_package(Path(p0r_root), "P0R")

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
        reference_names = set(reference_shard)
        candidate_names = set(candidate_shard)
        if reference_names != candidate_names:
            raise ProtocolError(f"cycle {cycle} field-name mismatch")
        for field in SHARD_EXACT_FIELDS:
            if not _exact_equal(candidate_shard[field], reference_shard[field]):
                raise ProtocolError(f"cycle {cycle} exact {field} identity mismatch")
        for field in TRAJECTORY_FIELDS:
            candidate = np.asarray(candidate_shard[field], dtype=np.float64)
            reference = np.asarray(reference_shard[field], dtype=np.float64)
            if candidate.shape != reference.shape:
                raise ProtocolError(f"cycle {cycle} field {field} shape mismatch")
            metric_relative = relative_l2(candidate, reference)
            delta = candidate.reshape(-1, order="F") - reference.reshape(
                -1, order="F"
            )
            metric_absolute = float(np.max(np.abs(delta)))
            zero_reference = float(
                np.linalg.norm(reference.reshape(-1, order="F"))
            ) == 0.0
            reported_relative: float | str
            if zero_reference:
                reported_relative = "not_applicable_zero_reference"
            else:
                reported_relative = metric_relative
                maximum_relative = max(maximum_relative, metric_relative)
            maximum_absolute = max(maximum_absolute, metric_absolute)
            if (not zero_reference and metric_relative > THRESHOLD) or (
                metric_absolute > THRESHOLD
            ):
                raise ProtocolError(
                    f"cycle {cycle} field {field} exceeds repeatability threshold"
                )
            field_metrics.append(
                {
                    "cycle": cycle,
                    "field": field,
                    "shape": list(reference.shape),
                    "relative_l2": reported_relative,
                    "max_absolute": metric_absolute,
                }
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
    destination = p0_root.parent / "P0_REPEATABILITY_EVIDENCE_LOCK.json"
    _publish_json_exclusive(destination, evidence)
    return evidence


def _validate_package(root: Path, label: str) -> dict[str, Any]:
    if not root.is_dir():
        raise ProtocolError(f"{label} package root is missing")
    manifest_path = root / "TERMINAL_MANIFEST.json"
    manifest = _read_json_object(manifest_path, f"{label} terminal manifest")
    required_manifest = {
        "authorization_scope",
        "case_id",
        "execution_input_lock_sha256",
        "files",
        *PACKAGE_IDENTITY_FIELDS,
    }
    _require_fields(manifest, required_manifest, f"{label} terminal manifest")
    authorization_scope = manifest["authorization_scope"]
    if not isinstance(authorization_scope, str) or not authorization_scope:
        raise ProtocolError(f"{label} authorization_scope must be nonempty text")
    _validate_manifest_identities(manifest, label)

    entries = manifest["files"]
    if not isinstance(entries, list) or not entries:
        raise ProtocolError(f"{label} manifest files must be a nonempty list")
    paths: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise ProtocolError(f"{label} manifest file entry is malformed")
        relative = entry["path"]
        digest = entry["sha256"]
        if (
            not isinstance(relative, str)
            or not relative
            or "\\" in relative
            or ".." in Path(relative).parts
            or Path(relative).is_absolute()
            or not _is_sha256(digest)
        ):
            raise ProtocolError(f"{label} manifest file entry is not canonical")
        paths.append(relative)
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ProtocolError(f"{label} manifest paths are not sorted and unique")
    actual_paths = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path != manifest_path
    )
    if paths != actual_paths:
        raise ProtocolError(f"{label} package manifest is incomplete or mutable")
    for entry in entries:
        if _sha256(root / entry["path"]) != entry["sha256"]:
            raise ProtocolError(f"{label} package bytes are mutable")

    required_paths = {
        "EXECUTION_INPUT_LOCK.json",
        "STATE0.mat",
        "EVENT_METADATA.json",
        "TERMINAL_RESULT.json",
        "qualification/C5_STAGGER_TRACE.csv",
        "qualification/C5_NUMERICAL_GATE_RECEIPT.json",
    }
    if not required_paths.issubset(paths):
        raise ProtocolError(f"{label} package is missing a required artifact")

    execution_digest = _sha256(root / "EXECUTION_INPUT_LOCK.json")
    if execution_digest != manifest["execution_input_lock_sha256"]:
        raise ProtocolError(f"{label} execution lock is inconsistent with its manifest")
    if not _is_sha256(execution_digest):
        raise ProtocolError(f"{label} execution lock digest is malformed")

    trace_path = root / "qualification" / "C5_STAGGER_TRACE.csv"
    receipt_path = root / "qualification" / "C5_NUMERICAL_GATE_RECEIPT.json"
    receipt = _read_json_object(receipt_path, f"{label} c5 receipt")
    _require_fields(
        receipt,
        {
            "authorization_scope",
            "case_id",
            "cycle",
            "substep_ordinal",
            "status",
            "trace_sha256",
        },
        f"{label} c5 receipt",
    )
    if not (
        receipt["authorization_scope"] == authorization_scope
        and receipt["case_id"] == manifest["case_id"]
        and receipt["cycle"] == 5
        and receipt["substep_ordinal"] == 4
        and receipt["status"] == "PASS"
        and receipt["trace_sha256"] == _sha256(trace_path)
    ):
        raise ProtocolError(f"{label} case-local c5 gate did not pass")

    event = _read_json_object(root / "EVENT_METADATA.json", f"{label} event")
    terminal = _read_json_object(
        root / "TERMINAL_RESULT.json", f"{label} terminal result"
    )
    event_fields = {
        "authorization_scope",
        "case_id",
        "first_hit_cycle",
        "confirmed_cycle",
        "terminal_cycle",
        "peak_substep_ordinal",
        "cycle_shard",
        "cycle_shard_sha256",
    }
    terminal_fields = {
        "authorization_scope",
        "case_id",
        "terminal_reason",
        "terminal_cycle",
        "first_hit_cycle",
        "confirmed_cycle",
    }
    _require_fields(event, event_fields, f"{label} event")
    _require_fields(terminal, terminal_fields, f"{label} terminal result")
    if not (
        event["authorization_scope"] == authorization_scope
        and terminal["authorization_scope"] == authorization_scope
        and event["case_id"] == manifest["case_id"]
        and terminal["case_id"] == manifest["case_id"]
        and event["terminal_cycle"] == terminal["terminal_cycle"]
        and event["first_hit_cycle"] == terminal["first_hit_cycle"]
        and event["confirmed_cycle"] == terminal["confirmed_cycle"]
        and event["peak_substep_ordinal"] == 4
    ):
        raise ProtocolError(f"{label} event metadata is inconsistent")

    terminal_cycle = terminal["terminal_cycle"]
    if not isinstance(terminal_cycle, int) or terminal_cycle < 5:
        raise ProtocolError(f"{label} terminal cycle is invalid")
    cycle_paths = [
        relative
        for relative in paths
        if relative.startswith("substeps/cycle_") and relative.endswith(".mat")
    ]
    expected_cycle_paths = [
        f"substeps/cycle_{cycle:04d}.mat" for cycle in range(1, terminal_cycle + 1)
    ]
    if cycle_paths != expected_cycle_paths:
        raise ProtocolError(f"{label} cycle coverage is not consecutive")
    expected_event_path = f"substeps/cycle_{event['confirmed_cycle']:04d}.mat"
    if not (
        event["cycle_shard"] == expected_event_path
        and event["cycle_shard_sha256"] == _sha256(root / expected_event_path)
    ):
        raise ProtocolError(f"{label} event does not identify its cycle shard")

    state0 = _load_struct(root / "STATE0.mat", "state0", f"{label} state0")
    _require_fields(state0, {"d_node", "alpha_bar_gp"}, f"{label} state0")
    shards: list[dict[str, Any]] = []
    for cycle, relative in enumerate(cycle_paths, start=1):
        shard = _load_struct(root / relative, "shard", f"{label} cycle {cycle}")
        _validate_shard(shard, manifest, cycle, label)
        shards.append(shard)

    return {
        "root": root,
        "manifest": manifest,
        "manifest_sha256": _sha256(manifest_path),
        "c5_receipt_sha256": _sha256(receipt_path),
        "event": event,
        "terminal": terminal,
        "state0": state0,
        "shards": shards,
    }


def _validate_shard(
    shard: dict[str, Any], manifest: dict[str, Any], cycle: int, label: str
) -> None:
    required = {*TRAJECTORY_FIELDS, *SHARD_EXACT_FIELDS, "execution_input_lock_sha256"}
    _require_fields(shard, required, f"{label} cycle {cycle}")
    unexpected = sorted(set(shard) - required)
    if unexpected:
        raise ProtocolError(
            f"{label} cycle {cycle} has unexpected fields: {', '.join(unexpected)}"
        )
    if int(np.asarray(shard["cycle"]).item()) != cycle:
        raise ProtocolError(f"{label} cycle ordinal is invalid")
    if not (
        _exact_equal(shard["substep_ordinal"], np.arange(1, 6))
        and _exact_equal(
            shard["load_factor"], np.array([0.25, 0.5, 0.75, 1.0, 0.0])
        )
        and _exact_equal(
            shard["raw_step_zero_based"], 5 * (cycle - 1) + np.arange(5)
        )
        and _exact_equal(
            shard["branch"],
            np.array(["loading", "loading", "loading", "loading", "unloading"]),
        )
    ):
        raise ProtocolError(f"{label} cycle {cycle} chronology metadata is invalid")
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
        if _scalar_value(shard[field]) != manifest[field]:
            raise ProtocolError(f"{label} cycle {cycle} {field} is not package-local")
    for field in TRAJECTORY_FIELDS:
        value = np.asarray(shard[field], dtype=np.float64)
        if not np.all(np.isfinite(value)):
            raise ProtocolError(f"{label} cycle {cycle} field {field} is non-finite")
    d_node = np.asarray(shard["d_node"], dtype=np.float64)
    d_gp = np.asarray(shard["d_gp"], dtype=np.float64)
    if d_node.ndim != 2 or d_node.shape[1] != 5 or d_gp.ndim != 3 or d_gp.shape[1:] != (4, 5):
        raise ProtocolError(f"{label} cycle {cycle} state shape is invalid")
    expected_gp_shape = d_gp.shape
    for field in (
        "alpha_bar_gp",
        "f_alpha_gp",
        "psi_raw_gp",
        "g_gp",
        "psi_active_gp",
    ):
        if np.asarray(shard[field]).shape != expected_gp_shape:
            raise ProtocolError(f"{label} cycle {cycle} field {field} shape is invalid")
    if np.asarray(shard["psi_raw_cyclemax_gp"]).shape != d_gp.shape[:2]:
        raise ProtocolError(f"{label} cycle {cycle} cyclemax shape is invalid")
    alpha = np.asarray(shard["alpha_bar_gp"], dtype=np.float64)
    raw = np.asarray(shard["psi_raw_gp"], dtype=np.float64)
    g_expected = (1.0 - d_gp) ** 2
    f_expected = np.minimum(1.0, (1.0 - ((alpha - 0.5) / (alpha + 0.5))) ** 2)
    identities = (
        np.max(np.abs(np.asarray(shard["g_gp"]) - g_expected)),
        np.max(np.abs(np.asarray(shard["f_alpha_gp"]) - f_expected)),
        np.max(
            np.abs(
                np.asarray(shard["psi_active_gp"])
                - np.asarray(shard["g_gp"]) * raw
            )
        ),
        np.max(
            np.abs(np.asarray(shard["psi_raw_cyclemax_gp"]) - np.max(raw, axis=2))
        ),
    )
    if max(float(value) for value in identities) > THRESHOLD:
        raise ProtocolError(f"{label} cycle {cycle} constitutive identity failed")


def _require_equal_event_and_terminal(p0: dict[str, Any], p0r: dict[str, Any]) -> None:
    event_fields = (
        "first_hit_cycle",
        "confirmed_cycle",
        "terminal_cycle",
        "peak_substep_ordinal",
        "cycle_shard",
    )
    for field in event_fields:
        if p0["event"][field] != p0r["event"][field]:
            raise ProtocolError(f"event {field} mismatch")
    terminal_fields = (
        "terminal_reason",
        "terminal_cycle",
        "first_hit_cycle",
        "confirmed_cycle",
    )
    for field in terminal_fields:
        if p0["terminal"][field] != p0r["terminal"][field]:
            raise ProtocolError(f"terminal {field} mismatch")


def _require_equal_state0(reference: dict[str, Any], candidate: dict[str, Any]) -> None:
    if set(reference) != set(candidate):
        raise ProtocolError("state0 field-name mismatch")
    for field in reference:
        if np.asarray(candidate[field]).shape != np.asarray(reference[field]).shape:
            raise ProtocolError(f"state0 field {field} shape mismatch")
        if not _exact_equal(candidate[field], reference[field]):
            raise ProtocolError(f"state0 exact {field} mismatch")


def _load_struct(path: Path, variable: str, label: str) -> dict[str, Any]:
    try:
        value = loadmat(path, simplify_cells=True)[variable]
    except (KeyError, OSError, ValueError) as exception:
        raise ProtocolError(f"cannot load {label}: {exception}") from exception
    if not isinstance(value, dict):
        raise ProtocolError(f"{label} must contain one scalar struct")
    return value


def _exact_equal(candidate: object, reference: object) -> bool:
    candidate_array = np.asarray(candidate)
    reference_array = np.asarray(reference)
    return candidate_array.shape == reference_array.shape and bool(
        np.array_equal(candidate_array, reference_array)
    )


def _scalar_value(value: object) -> object:
    array = np.asarray(value)
    if array.size != 1:
        return value
    return array.reshape(-1)[0].item()


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exception:
        raise ProtocolError(f"cannot read {label}: {exception}") from exception
    if not isinstance(value, dict):
        raise ProtocolError(f"{label} must be one JSON object")
    return value


def _require_fields(value: dict[str, Any], names: set[str], label: str) -> None:
    missing = sorted(names - set(value))
    if missing:
        raise ProtocolError(f"{label} missing fields: {', '.join(missing)}")


def _validate_manifest_identities(manifest: dict[str, Any], label: str) -> None:
    if not (
        isinstance(manifest["source_commit"], str)
        and len(manifest["source_commit"]) == 40
        and all(
            character in "0123456789abcdef"
            for character in manifest["source_commit"]
        )
    ):
        raise ProtocolError(f"{label} source_commit is not canonical")
    digest_fields = {
        field
        for field in PACKAGE_IDENTITY_FIELDS
        if field.endswith("_sha256")
    } | {"execution_input_lock_sha256"}
    for field in digest_fields:
        if not _is_sha256(manifest[field]):
            raise ProtocolError(f"{label} {field} is not canonical SHA-256")
    for field in (
        "protocol_version",
        "element_ordering_id",
        "gp_ordering_id",
        "state_semantics_id",
    ):
        if not isinstance(manifest[field], str) or not manifest[field]:
            raise ProtocolError(f"{label} {field} must be nonempty text")


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _publish_json_exclusive(destination: Path, value: object) -> None:
    if destination.exists():
        raise ProtocolError(f"evidence lock already exists: {destination}")
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8") + b"\n"
    temporary = destination.with_name(
        f".{destination.name}.{uuid.uuid4().hex}.tmp"
    )
    try:
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.rename(temporary, destination)
    except FileExistsError as exception:
        raise ProtocolError(f"evidence lock already exists: {destination}") from exception
    finally:
        if temporary.exists():
            temporary.unlink()
