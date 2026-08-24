"""Fail-closed, create-once terminal adjudication for the one T3-rev run."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping

import numpy as np


CASE_ID = "T3_rev_loading_order"
AUTHORIZATION_CAPABILITY = "exactly_one_T3_rev_loading_order_execution"


class TerminalValidationError(RuntimeError):
    """The terminal package or its launch chain is not admissible evidence."""


def _load(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise TerminalValidationError(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise TerminalValidationError(f"cannot load {path.name}: {error}") from error
    finally:
        sys.modules.pop(name, None)
    return module


def _strict_json(path: Path) -> dict[str, object]:
    def reject_duplicate(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise TerminalValidationError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate,
                           parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise TerminalValidationError(f"cannot read strict JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise TerminalValidationError(f"JSON root must be an object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify_terminal(terminal: Mapping[str, object]) -> str:
    """Keep every terminal category distinct; no failure is recast as censoring."""
    reason = terminal.get("terminal_reason")
    classes = {
        "confirmed_penetration": "PASS_CONFIRMED_FRACTURE_TRAJECTORY",
        "right_censored": "PASS_NO_CONFIRMED_FRACTURE_BY_C150",
        "coupled_fixed_point_nonconvergence": "FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE",
        "newton_nonconvergence": "FAIL_NEWTON_NONCONVERGENCE",
        "startup_failure": "FAIL_STARTUP",
        "runtime_failure": "FAIL_RUNTIME",
    }
    if reason not in classes:
        raise TerminalValidationError(f"unknown terminal_reason: {reason!r}")
    if reason == "confirmed_penetration":
        first_hit = terminal.get("first_hit_cycle")
        confirmed = terminal.get("confirmed_cycle")
        terminal_cycle = terminal.get("terminal_cycle")
        if type(first_hit) is not int or type(confirmed) is not int \
                or type(terminal_cycle) is not int \
                or confirmed != first_hit + 3 or terminal_cycle != confirmed:
            raise TerminalValidationError("confirmed outcome must preserve the exact three-cycle event rule")
    if reason == "right_censored" and (
            terminal.get("terminal_cycle") != 150
            or terminal.get("first_hit_cycle") is not None
            or terminal.get("confirmed_cycle") is not None):
        raise TerminalValidationError("right-censored outcome must end at c150 without a hit or confirmation")
    if reason in {"coupled_fixed_point_nonconvergence", "newton_nonconvergence"}:
        if type(terminal.get("cycle")) is not int or terminal["cycle"] < 1 \
                or type(terminal.get("substep")) is not int \
                or not 1 <= terminal["substep"] <= 5:
            raise TerminalValidationError("solver nonconvergence must identify exact cycle and substep")
    return classes[reason]


def terminal_adjudication_status(classification: str) -> str:
    if classification in {
        "PASS_CONFIRMED_FRACTURE_TRAJECTORY",
        "PASS_NO_CONFIRMED_FRACTURE_BY_C150",
    }:
        return "PASS_TERMINAL_ADJUDICATION"
    if classification.startswith("FAIL_"):
        return classification
    raise TerminalValidationError(f"unknown terminal classification: {classification}")


def require_canonical_seal_bytes(path: Path, seal: Mapping[str, object]) -> str:
    expected = json.dumps(seal, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
    actual = Path(path).read_bytes()
    if actual != expected:
        raise TerminalValidationError("seal bytes are not canonical builder bytes")
    return hashlib.sha256(actual).hexdigest()


def _write_create_once(path: Path, value: Mapping[str, object]) -> None:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
    try:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as error:
        raise TerminalValidationError(f"terminal adjudication already exists: {path}") from error


def require_canonical_lock_bytes(protocol: Any, lock_path: Path, lock: Mapping[str, object]) -> None:
    """The launch receipt binds protocol-canonical bytes, not JSON-equivalent text."""
    try:
        expected = protocol.canonical_json_bytes(lock)
    except Exception as error:
        raise TerminalValidationError(f"cannot encode canonical execution lock: {error}") from error
    if not isinstance(expected, bytes) or Path(lock_path).read_bytes() != expected:
        raise TerminalValidationError("execution lock bytes are not authoritative canonical JSON")


def _validate_package_checksum(protocol: Any, snapshot: Mapping[str, object]) -> None:
    """Validate the producer checksum ledger in addition to manifest closure."""
    files = snapshot.get("bytes")
    if not isinstance(files, dict) or "SHA256SUMS.txt" not in files:
        raise TerminalValidationError("terminal package checksum ledger is missing")
    payload = files["SHA256SUMS.txt"]
    if not isinstance(payload, bytes) or not payload.endswith(b"\n") or b"\r" in payload:
        raise TerminalValidationError("terminal package checksum ledger bytes are not canonical")
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise TerminalValidationError("terminal package checksum ledger is not ASCII") from error
    declared: dict[str, str] = {}
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match is None:
            raise TerminalValidationError("terminal package checksum row is malformed")
        digest, relative = match.groups()
        if not protocol._canonical_relative_path(relative) or relative in declared:
            raise TerminalValidationError("terminal package checksum path is invalid")
        declared[relative] = digest
    expected_paths = sorted(set(files) - {"SHA256SUMS.txt", "TERMINAL_MANIFEST.json"})
    if list(declared) != expected_paths:
        raise TerminalValidationError("terminal package checksum closure is incomplete")
    for relative, digest in declared.items():
        if hashlib.sha256(files[relative]).hexdigest() != digest:
            raise TerminalValidationError("terminal package checksum digest differs")


def _authenticate_right_censored_package(
        protocol: Any, package_root: Path) -> dict[str, object]:
    """Reuse authoritative package components with the sole c150 event variant."""
    root = protocol._canonical_package_root(Path(package_root), CASE_ID)
    snapshot = protocol._capture_package_bytes(root, CASE_ID)
    manifest = protocol._read_json_bytes(
        snapshot["bytes"].get("TERMINAL_MANIFEST.json"), f"{CASE_ID} terminal manifest"
    )
    protocol._require_exact_fields(manifest, protocol.MANIFEST_FIELDS, f"{CASE_ID} terminal manifest")
    if manifest["protocol_version"] != protocol.PROTOCOL_VERSION \
            or type(manifest["protocol_version"]) is not str \
            or manifest["case_id"] != CASE_ID or type(manifest["case_id"]) is not str:
        raise TerminalValidationError("right-censored manifest protocol or case is invalid")
    authorization_scope = protocol._require_nonempty_text(
        manifest["authorization_scope"], f"{CASE_ID} authorization_scope"
    )
    protocol._validate_manifest_identities(manifest, CASE_ID)
    protocol._validate_manifest_closure(manifest, snapshot, CASE_ID)
    _validate_package_checksum(protocol, snapshot)
    required_paths = {
        "EXECUTION_INPUT_LOCK.json", "STATE0.mat", "EVENT_METADATA.json",
        "TERMINAL_RESULT.json", "SHA256SUMS.txt",
        "qualification/C5_STAGGER_TRACE.csv",
        "qualification/C5_NUMERICAL_GATE_RECEIPT.json",
    }
    if not required_paths.issubset(snapshot["bytes"]):
        raise TerminalValidationError("right-censored package is missing a required artifact")
    lock_bytes = snapshot["bytes"]["EXECUTION_INPUT_LOCK.json"]
    execution_digest = hashlib.sha256(lock_bytes).hexdigest()
    if execution_digest != manifest["execution_input_lock_sha256"]:
        raise TerminalValidationError("right-censored execution lock differs from its manifest")
    lock = protocol._read_json_bytes(lock_bytes, f"{CASE_ID} execution lock")
    protocol.validate_execution_input_lock(lock, CASE_ID)
    if lock["authorization_scope"] != authorization_scope \
            or protocol.canonical_json_bytes(lock) != lock_bytes:
        raise TerminalValidationError("right-censored execution lock is not canonical or package-local")
    protocol._validate_c5(snapshot, manifest, CASE_ID)
    event = protocol._read_json_bytes(snapshot["bytes"]["EVENT_METADATA.json"], f"{CASE_ID} event")
    terminal = protocol._read_json_bytes(
        snapshot["bytes"]["TERMINAL_RESULT.json"], f"{CASE_ID} terminal result"
    )
    protocol._require_exact_fields(event, protocol.EVENT_FIELDS, f"{CASE_ID} event")
    protocol._require_exact_fields(terminal, protocol.TERMINAL_FIELDS, f"{CASE_ID} terminal result")
    if not (
            event["authorization_scope"] == authorization_scope
            and terminal["authorization_scope"] == authorization_scope
            and event["case_id"] == CASE_ID and terminal["case_id"] == CASE_ID
            and event["first_hit_cycle"] is None and terminal["first_hit_cycle"] is None
            and event["confirmed_cycle"] is None and terminal["confirmed_cycle"] is None
            and protocol._exact_json_int(event["terminal_cycle"], 150)
            and protocol._exact_json_int(terminal["terminal_cycle"], 150)
            and protocol._exact_json_int(event["peak_substep_ordinal"], 4)
            and terminal["terminal_reason"] == "right_censored"):
        raise TerminalValidationError(
            "right-censored event and terminal metadata must end at c150 without first-hit or confirmation"
        )
    terminal_path = "substeps/cycle_0150.mat"
    if terminal_path not in snapshot["bytes"] or event["cycle_shard"] != terminal_path \
            or event["cycle_shard_sha256"] != hashlib.sha256(snapshot["bytes"][terminal_path]).hexdigest():
        raise TerminalValidationError("right-censored event metadata does not bind the c150 shard")
    cycle_paths = sorted(
        path for path in snapshot["bytes"]
        if re.fullmatch(r"substeps/cycle_[0-9]{4}\.mat", path)
    )
    expected_cycle_paths = [f"substeps/cycle_{cycle:04d}.mat" for cycle in range(1, 151)]
    if cycle_paths != expected_cycle_paths:
        raise TerminalValidationError("right-censored cycle coverage is not exactly c1-c150")
    state0 = protocol._read_mat_struct_bytes(snapshot["bytes"]["STATE0.mat"], "state0", f"{CASE_ID} state0")
    protocol._require_exact_fields(state0, {"d_node", "alpha_bar_gp"}, f"{CASE_ID} state0")
    state0_damage = protocol._require_double_array(state0["d_node"], f"{CASE_ID} state0.d_node")
    state0_alpha = protocol._require_double_array(
        state0["alpha_bar_gp"], f"{CASE_ID} state0.alpha_bar_gp"
    )
    if state0_damage.ndim != 2 or state0_damage.shape[1] != 1 or state0_damage.shape[0] == 0 \
            or state0_alpha.ndim != 2 or state0_alpha.shape[1] != 4 or state0_alpha.shape[0] == 0 \
            or np.any(state0_damage < -protocol.THRESHOLD) \
            or np.any(state0_damage > 1 + protocol.THRESHOLD) \
            or np.any(state0_alpha < -protocol.THRESHOLD):
        raise TerminalValidationError("right-censored state0 shape or bounds are invalid")
    previous_damage = state0_damage[:, 0]
    previous_alpha = state0_alpha
    shards: list[dict[str, Any]] = []
    for cycle, relative in enumerate(cycle_paths, start=1):
        shard = protocol._read_mat_struct_bytes(snapshot["bytes"][relative], "shard", f"{CASE_ID} cycle {cycle}")
        previous_damage, previous_alpha = protocol._validate_shard(
            shard, manifest, cycle, CASE_ID, previous_damage, previous_alpha,
            state0_damage.shape[0], state0_alpha.shape[0],
        )
        shards.append(shard)
    package = {
        "root": root, "snapshot": snapshot, "manifest": manifest,
        "manifest_sha256": hashlib.sha256(snapshot["bytes"]["TERMINAL_MANIFEST.json"]).hexdigest(),
        "c5_receipt_sha256": hashlib.sha256(
            snapshot["bytes"]["qualification/C5_NUMERICAL_GATE_RECEIPT.json"]
        ).hexdigest(),
        "event": event, "terminal": terminal, "state0": state0, "shards": shards,
    }
    receipt = protocol._terminal_authentication_receipt(package)
    protocol._verify_package_snapshot(package)
    return receipt


def authenticate_completed_package(protocol: Any, package_root: Path) -> dict[str, object]:
    """Authenticate confirmed packages unchanged or the strict c150 no-event variant."""
    root = Path(package_root)
    try:
        snapshot = protocol._capture_package_bytes(
            protocol._canonical_package_root(root, CASE_ID), CASE_ID
        )
        terminal = protocol._read_json_bytes(
            snapshot["bytes"].get("TERMINAL_RESULT.json"), f"{CASE_ID} terminal result"
        )
        classification = classify_terminal(terminal)
        if classification == "PASS_CONFIRMED_FRACTURE_TRAJECTORY":
            receipt = protocol.authenticate_terminal_package(root, CASE_ID)
            _validate_package_checksum(protocol, snapshot)
            protocol.recheck_authenticated_package(receipt)
            return receipt
        if classification == "PASS_NO_CONFIRMED_FRACTURE_BY_C150":
            return _authenticate_right_censored_package(protocol, root)
        raise TerminalValidationError("completed-package authentication received a failure outcome")
    except TerminalValidationError:
        raise
    except Exception as error:
        raise TerminalValidationError(f"authoritative completed package validation failed: {error}") from error


def _validate_failure_package(
        failure_root: Path, terminal: Mapping[str, object], classification: str,
        lock: Mapping[str, object], protocol: Any, run_root: Path,
        launch_receipt: Mapping[str, object], seal_sha256: str,
        extension_manifest_sha256: str, case_contract: Mapping[str, object]) -> dict[str, object]:
    """Authenticate the exact T2-pattern immutable T3-rev failure dossier."""
    root = Path(failure_root)
    if root != run_root / "T3_REV_FAILURE_PACKAGE" or not root.is_dir():
        raise TerminalValidationError("numerical failure package must use the fixed run-local root")
    manifest = _strict_json(root / "PACKAGE_MANIFEST.json")
    failure = _strict_json(root / "FAILURE_CLASSIFICATION.json")
    identities = _strict_json(root / "SOURCE_RUNTIME_INPUT_IDENTITIES.json")
    manifest_fields = {
        "schema_version", "case_id", "status", "source_run_root",
        "artifact_file_count", "artifact_aggregate_sha256", "artifacts",
    }
    failure_fields = {
        "schema_version", "case_id", "status", "failure_cycle", "failure_substep",
        "failure_layer", "newton_failure", "fixed_point_tolerance",
        "stagger_iteration_cap", "completed_cycle_shards", "automatic_retry_performed",
    }
    if set(manifest) != manifest_fields \
            or manifest.get("schema_version") != "toy_road_t3_rev_immutable_failure_package_v1" \
            or manifest.get("case_id") != CASE_ID or manifest.get("status") != classification \
            or manifest.get("source_run_root") != str(run_root) \
            or set(failure) != failure_fields \
            or failure.get("schema_version") != "toy_road_t3_rev_failure_classification_v1" \
            or failure.get("case_id") != CASE_ID or failure.get("status") != classification:
        raise TerminalValidationError("failure package manifest or classification schema is not exact")
    expected_layer = "coupled_damage_fixed_point" if classification.endswith("FIXED_POINT_NONCONVERGENCE") else "newton"
    observed_layer = failure.get("failure_layer")
    if failure.get("failure_cycle") != terminal.get("cycle") \
            or failure.get("failure_substep") != terminal.get("substep") \
            or (expected_layer == "coupled_damage_fixed_point" and observed_layer != expected_layer) \
            or (expected_layer == "newton" and observed_layer not in {"displacement_newton", "phase_newton"}) \
            or failure.get("newton_failure") is not (expected_layer == "newton") \
            or type(failure.get("fixed_point_tolerance")) is not float \
            or failure.get("fixed_point_tolerance") != 1e-3 \
            or type(failure.get("stagger_iteration_cap")) is not int \
            or failure.get("stagger_iteration_cap") != 1000 \
            or failure.get("automatic_retry_performed") is not False:
        raise TerminalValidationError("failure package classification does not bind the terminal numerical failure")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or manifest.get("artifact_file_count") != len(artifacts):
        raise TerminalValidationError("failure package artifact inventory is malformed")
    canonical_artifacts = json.dumps(
        artifacts, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    if manifest.get("artifact_aggregate_sha256") != hashlib.sha256(canonical_artifacts).hexdigest():
        raise TerminalValidationError("failure package artifact aggregate differs")
    paths: list[str] = []
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {"path", "bytes", "sha256"}:
            raise TerminalValidationError("failure package artifact entry is malformed")
        relative = item["path"]
        if not isinstance(relative, str) or not relative.startswith("artifacts/") or relative in paths:
            raise TerminalValidationError("failure package artifact path is invalid")
        copied = root / relative
        if not copied.is_file() or copied.stat().st_size != item["bytes"] or _sha256(copied) != item["sha256"]:
            raise TerminalValidationError("failure package artifact bytes do not match inventory")
        live = run_root / Path(relative).relative_to("artifacts")
        if not live.is_file() or live.read_bytes() != copied.read_bytes():
            raise TerminalValidationError("failure package artifact is not the immutable live run byte identity")
        paths.append(relative)
    completed = failure.get("completed_cycle_shards")
    if type(completed) is not int or completed != terminal.get("cycle", 0) - 1:
        raise TerminalValidationError("failure package does not bind exact completed sequential shards")
    expected_relatives = {
        "launcher.pid", "T3_REV.stdout.log", "T3_REV.stderr.log",
        "output/INPUT_SNAPSHOT.json", "output/mesh_geometry.mat", "output/RUN_RESULT.json",
        "output/RUNTIME_RECEIPT.json", "output/state0_analysis.mat",
        "receipts/T3_REV_EXECUTION_INPUT_LOCK.json", "receipts/T3_REV_LAUNCH_RECEIPT.json",
        "receipts/T3_REV_RUNTIME_MEASUREMENT.json",
        *[f"output/substeps/cycle_{cycle:04d}.mat" for cycle in range(1, completed + 1)],
    }
    if terminal.get("cycle", 0) > 5:
        expected_relatives.update({
            "output/qualification/C5_STAGGER_TRACE.csv",
            "output/qualification/C5_NUMERICAL_GATE_RECEIPT.json",
        })
    expected_artifact_paths = sorted(f"artifacts/{relative}" for relative in expected_relatives)
    if paths != expected_artifact_paths:
        raise TerminalValidationError("failure package artifact closure is not the exact phase-specific set")
    package_files = sorted(
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    )
    if package_files != sorted({
            "PACKAGE_MANIFEST.json", "FAILURE_CLASSIFICATION.json",
            "SOURCE_RUNTIME_INPUT_IDENTITIES.json", "SHA256SUMS.txt", *expected_artifact_paths}):
        raise TerminalValidationError("failure package contains undeclared or missing files")
    sums_payload = (root / "SHA256SUMS.txt").read_bytes()
    if not sums_payload.endswith(b"\n") or b"\r" in sums_payload:
        raise TerminalValidationError("failure package checksum ledger bytes are not canonical")
    sums: dict[str, str] = {}
    try:
        sum_lines = sums_payload.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise TerminalValidationError("failure package checksum ledger is not ASCII") from error
    for line in sum_lines:
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match is None or match.group(2) in sums:
            raise TerminalValidationError("failure package checksum row is malformed")
        sums[match.group(2)] = match.group(1)
    expected_sums = sorted(set(package_files) - {"SHA256SUMS.txt"})
    if list(sums) != expected_sums \
            or any(_sha256(root / relative) != digest for relative, digest in sums.items()):
        raise TerminalValidationError("failure package checksum closure or digest differs")
    identity_fields = {"schema_version", "producer", "runtime", "input", "launch"}
    producer = identities.get("producer")
    runtime = identities.get("runtime")
    input_identity = identities.get("input")
    launch_identity = identities.get("launch")
    if set(identities) != identity_fields \
            or identities.get("schema_version") != "toy_road_t3_rev_failure_identity_v1" \
            or not all(isinstance(value, dict) for value in (
                producer, runtime, input_identity, launch_identity)):
        raise TerminalValidationError("failure package identity schema is not exact")
    if set(producer) != {"source_commit", "source_manifest_sha256", "family_contract_sha256", "case_physics_contract_sha256"} \
            or any(producer.get(field) != lock.get(field) for field in producer) \
            or set(runtime) != {"runtime_lock_sha256", "matlab", "binary_sha256", "thread_settings"} \
            or runtime.get("runtime_lock_sha256") != lock.get("runtime_lock_sha256") \
            or runtime.get("matlab") != lock.get("runtime_expectations", {}).get("matlab") \
            or runtime.get("binary_sha256") != lock.get("runtime_expectations", {}).get("binary_sha256") \
            or runtime.get("thread_settings") != launch_receipt.get("thread_environment"):
        raise TerminalValidationError("failure package producer/runtime identity differs from the lock")
    lock_sha256 = _sha256(run_root / "receipts" / "T3_REV_EXECUTION_INPUT_LOCK.json")
    artifact_root = root / "artifacts"
    snapshot_path = artifact_root / "output" / "INPUT_SNAPSHOT.json"
    snapshot = _strict_json(snapshot_path)
    if set(input_identity) != {"execution_input_lock_sha256", "input_snapshot_sha256", "mesh_sha256", "output_root", "run_root"} \
            or input_identity.get("execution_input_lock_sha256") != lock_sha256 \
            or input_identity.get("input_snapshot_sha256") != _sha256(snapshot_path) \
            or input_identity.get("mesh_sha256") != snapshot.get("mesh_sha256") \
            or input_identity.get("output_root") != str(run_root / "output") \
            or input_identity.get("run_root") != str(run_root):
        raise TerminalValidationError("failure package input/root identity differs")
    measurement_path = run_root / "receipts" / "T3_REV_RUNTIME_MEASUREMENT.json"
    launch_path = run_root / "receipts" / "T3_REV_LAUNCH_RECEIPT.json"
    if set(launch_identity) != {"seal_sha256", "launch_receipt_sha256", "runtime_measurement_sha256", "extension_source_manifest_sha256"} \
            or launch_identity.get("seal_sha256") != seal_sha256 \
            or launch_identity.get("launch_receipt_sha256") != _sha256(launch_path) \
            or launch_identity.get("runtime_measurement_sha256") != _sha256(measurement_path) \
            or launch_identity.get("extension_source_manifest_sha256") != extension_manifest_sha256:
        raise TerminalValidationError("failure package launch-chain identity differs")
    snapshot_fields = {
        "schema_version", "authorization_scope", "case_id", "source_commit",
        "runtime_lock_sha256", "family_contract_sha256", "case_physics_contract_sha256",
        "execution_input_lock_sha256", "input_assets_root", "mesh_sha256", "changed_axes",
        "case_physics", "fresh_state0", "resume_allowed", "line_search", "cycle_jump",
    }
    physics = case_contract.get("physics")
    mesh_identity = physics.get("mesh") if isinstance(physics, dict) else None
    if set(snapshot) != snapshot_fields or snapshot.get("schema_version") != "toy_road_p0_input_snapshot_v1" \
            or snapshot.get("authorization_scope") != "production_authorized" \
            or snapshot.get("case_id") != CASE_ID \
            or any(snapshot.get(field) != lock.get(field) for field in (
                "source_commit", "runtime_lock_sha256", "family_contract_sha256",
                "case_physics_contract_sha256")) \
            or snapshot.get("execution_input_lock_sha256") != lock_sha256 \
            or snapshot.get("changed_axes") != ["loading.blocks"] \
            or snapshot.get("case_physics") != physics \
            or not isinstance(mesh_identity, dict) \
            or snapshot.get("mesh_sha256") != mesh_identity.get("mesh_sha256") \
            or snapshot.get("fresh_state0") is not True \
            or snapshot.get("resume_allowed") is not False \
            or snapshot.get("line_search") is not False or snapshot.get("cycle_jump") is not False:
        raise TerminalValidationError("failure package input snapshot is not the exact locked case")
    mesh = protocol._read_mat_struct_bytes(
        (artifact_root / "output" / "mesh_geometry.mat").read_bytes(),
        "mesh_geometry", f"{CASE_ID} failure mesh",
    )
    required_mesh_fields = {
        "node_coords", "connectivity", "mesh_sha256", "connectivity_sha256",
        "mesh_sha256_semantics", "element_ordering_id", "gp_ordering_id",
    }
    if not required_mesh_fields.issubset(mesh):
        raise TerminalValidationError("failure package mesh metadata is incomplete")
    coordinates = protocol._require_double_array(
        mesh["node_coords"], f"{CASE_ID} failure mesh node_coords")
    connectivity_values = protocol._require_double_array(
        mesh["connectivity"], f"{CASE_ID} failure mesh connectivity")
    rounded_connectivity = np.rint(connectivity_values)
    if coordinates.ndim != 2 or coordinates.shape[1] != 2 or connectivity_values.ndim != 2 \
            or connectivity_values.shape[1] != 4 \
            or not np.array_equal(connectivity_values, rounded_connectivity):
        raise TerminalValidationError("failure package mesh arrays are not exact Q4 geometry")
    mesh_digest = hashlib.sha256(
        np.asarray(coordinates, dtype="<f8").tobytes(order="F")
        + np.asarray(rounded_connectivity, dtype="<i8").tobytes(order="F")
    ).hexdigest()
    connectivity_digest = hashlib.sha256(
        np.asarray(rounded_connectivity, dtype="<i8").tobytes(order="F")
    ).hexdigest()
    if mesh.get("mesh_sha256") != mesh_digest \
            or mesh_digest != snapshot.get("mesh_sha256") \
            or connectivity_digest != mesh_identity.get("connectivity_sha256") \
            or type(mesh.get("connectivity_sha256")) is not str \
            or len(mesh["connectivity_sha256"]) != 64 \
            or mesh.get("mesh_sha256_semantics") != mesh_identity.get("mesh_sha256_semantics") \
            or mesh.get("element_ordering_id") != mesh_identity.get("element_ordering_id") \
            or mesh.get("gp_ordering_id") != mesh_identity.get("gp_ordering_id"):
        raise TerminalValidationError("failure package mesh arrays/identity differ from the case contract")
    runtime_receipt = _strict_json(artifact_root / "output" / "RUNTIME_RECEIPT.json")
    matlab = lock.get("runtime_expectations", {}).get("matlab")
    if set(runtime_receipt) != {"status", "authorization_scope", "case_id", "source_commit", "runtime_lock_sha256", "matlab_version", "computer", "blas", "lapack"} \
            or runtime_receipt.get("status") != "PASS" \
            or runtime_receipt.get("authorization_scope") != "production_authorized" \
            or runtime_receipt.get("case_id") != CASE_ID \
            or runtime_receipt.get("source_commit") != lock.get("source_commit") \
            or runtime_receipt.get("runtime_lock_sha256") != lock.get("runtime_lock_sha256") \
            or not isinstance(matlab, dict) \
            or runtime_receipt.get("matlab_version") != matlab.get("version") \
            or any(runtime_receipt.get(field) != matlab.get(field) for field in ("computer", "blas", "lapack")):
        raise TerminalValidationError("failure package runtime receipt differs from the PASS measurement lock")
    run_result = _strict_json(artifact_root / "output" / "RUN_RESULT.json")
    if set(run_result) != {"authorization_scope", "case_id", "complete", "status", "error_identifier", "error_message"} \
            or run_result.get("authorization_scope") != "production_authorized" \
            or run_result.get("case_id") != CASE_ID or run_result.get("complete") is not False \
            or run_result.get("status") != "failed":
        raise TerminalValidationError("failure package RUN_RESULT schema or status is invalid")
    if expected_layer == "coupled_damage_fixed_point":
        expected_error = (
            "toyRoadP0:StaggeredSolveFailed",
            f"Stagger convergence failed at cycle {terminal['cycle']} substep {terminal['substep']}.",
        )
    else:
        expected_error = (
            "toyRoadP0:EquilibriumSolveFailed" if observed_layer == "displacement_newton"
            else "toyRoadP0:PhaseSolveFailed",
            "The displacement Newton solve failed." if observed_layer == "displacement_newton"
            else "The phase Newton solve failed.",
        )
    if (run_result.get("error_identifier"), run_result.get("error_message")) != expected_error \
            or expected_error[1] not in (artifact_root / "T3_REV.stderr.log").read_text(encoding="utf-8"):
        raise TerminalValidationError("failure package numerical error class/message differs")
    if terminal.get("cycle", 0) > 5:
        c5_snapshot = {"bytes": {
            "qualification/C5_STAGGER_TRACE.csv": (
                artifact_root / "output" / "qualification" / "C5_STAGGER_TRACE.csv"
            ).read_bytes(),
            "qualification/C5_NUMERICAL_GATE_RECEIPT.json": (
                artifact_root / "output" / "qualification" / "C5_NUMERICAL_GATE_RECEIPT.json"
            ).read_bytes(),
        }}
        protocol._validate_c5(c5_snapshot, {
            "authorization_scope": "production_authorized", "case_id": CASE_ID,
        }, CASE_ID)
    state0 = protocol._read_mat_struct_bytes(
        (artifact_root / "output" / "state0_analysis.mat").read_bytes(),
        "state0", f"{CASE_ID} failure state0"
    )
    if not isinstance(state0, dict) or not {"d_node", "alpha_bar_gp"}.issubset(state0):
        raise TerminalValidationError("failure package state0 is incomplete")
    state0_damage = protocol._require_double_array(state0["d_node"], f"{CASE_ID} failure state0.d_node")
    state0_alpha = protocol._require_double_array(state0["alpha_bar_gp"], f"{CASE_ID} failure state0.alpha_bar_gp")
    if state0_damage.ndim != 2 or state0_damage.shape[1] != 1 \
            or state0_alpha.ndim != 2 or state0_alpha.shape[1] != 4:
        raise TerminalValidationError("failure package state0 shape is invalid")
    if not isinstance(mesh_identity, dict):
        raise TerminalValidationError("failure package mesh contract is missing")
    shard_manifest = {
        "mesh_sha256": snapshot["mesh_sha256"],
        "element_ordering_id": mesh_identity.get("element_ordering_id"),
        "gp_ordering_id": mesh_identity.get("gp_ordering_id"),
        "state_semantics_id": "five_substep_post_commit_history_v1",
        "runtime_lock_sha256": lock["runtime_lock_sha256"],
        "family_contract_sha256": lock["family_contract_sha256"],
        "case_physics_contract_sha256": lock["case_physics_contract_sha256"],
        "execution_input_lock_sha256": lock_sha256,
    }
    previous_damage, previous_alpha = state0_damage[:, 0], state0_alpha
    for cycle in range(1, completed + 1):
        shard = protocol._read_mat_struct_bytes(
            (artifact_root / "output" / "substeps" / f"cycle_{cycle:04d}.mat").read_bytes(),
            "shard", f"{CASE_ID} failure cycle {cycle}",
        )
        previous_damage, previous_alpha = protocol._validate_shard(
            shard, shard_manifest, cycle, CASE_ID, previous_damage, previous_alpha,
            state0_damage.shape[0], state0_alpha.shape[0],
        )
    for item in artifacts:
        relative = item["path"]
        copied = root / relative
        live = run_root / Path(relative).relative_to("artifacts")
        if _sha256(copied) != item["sha256"] or copied.read_bytes() != live.read_bytes():
            raise TerminalValidationError("failure artifacts changed during authentication")
    package_digest = hashlib.sha256("".join(
        f"{relative}\0{_sha256(root / relative)}\n" for relative in package_files
    ).encode("utf-8")).hexdigest()
    return {
        "failure_package_sha256": package_digest,
        "package_manifest_sha256": _sha256(root / "PACKAGE_MANIFEST.json"),
        "failure_classification_sha256": _sha256(root / "FAILURE_CLASSIFICATION.json"),
        "sha256sums_sha256": _sha256(root / "SHA256SUMS.txt"),
    }


def _validate_startup_or_runtime_failure(
        terminal: Mapping[str, object], classification: str, receipts: Path,
        launch_receipt: Mapping[str, object], seal_sha256: str, run_root: Path,
        lock: Mapping[str, object], protocol: Any) -> dict[str, object]:
    """Validate phase-appropriate failure evidence before demanding producer artifacts."""
    fields = {
        "schema_version", "status", "case_id", "terminal_reason", "failure_phase",
        "cycle", "substep", "error_identifier", "error_message", "seal_sha256",
        "run_root", "launch_receipt_sha256", "runtime_measurement_sha256",
        "failure_package_manifest_sha256",
    }
    phase = terminal.get("failure_phase")
    expected = {
        "matlab_startup_before_runtime_measurement": ("FAIL_STARTUP", "MATLAB:startup"),
        "bootstrap_or_runtime_bridge_before_measurement": (
            "FAIL_RUNTIME", "toyRoadP0:RuntimeBridgeFailed"),
        "producer_after_pass_runtime_measurement": (
            "FAIL_RUNTIME", "toyRoadP0:ProducerRuntimeFailed"),
    }
    expected_outcome = expected.get(phase)
    if set(terminal) != fields \
            or terminal.get("schema_version") != "toy_road_t3_rev_terminal_failure_v1" \
            or terminal.get("status") != classification \
            or terminal.get("case_id") != CASE_ID \
            or expected_outcome is None or expected_outcome[0] != classification \
            or terminal.get("error_identifier") != expected_outcome[1] \
            or not isinstance(terminal.get("error_message"), str) \
            or not terminal.get("error_message") \
            or terminal.get("cycle") is not None or terminal.get("substep") is not None \
            or terminal.get("failure_package_manifest_sha256") is not None \
            or terminal.get("seal_sha256") != seal_sha256 or terminal.get("run_root") != str(run_root) \
            or terminal.get("launch_receipt_sha256") != _sha256(receipts / "T3_REV_LAUNCH_RECEIPT.json"):
        raise TerminalValidationError("startup/runtime failure receipt class, phase, or binding is not exact")
    required_logs = (run_root / "T3_REV.stdout.log", run_root / "T3_REV.stderr.log")
    if not all(path.is_file() for path in required_logs):
        raise TerminalValidationError("startup/runtime failure does not retain both launch logs")
    if terminal["error_message"] not in required_logs[1].read_text(encoding="utf-8"):
        raise TerminalValidationError("startup/runtime failure message is absent from stderr")
    measurement_path = receipts / "T3_REV_RUNTIME_MEASUREMENT.json"
    if phase in {
            "matlab_startup_before_runtime_measurement",
            "bootstrap_or_runtime_bridge_before_measurement"}:
        if measurement_path.exists() or terminal.get("runtime_measurement_sha256") is not None:
            raise TerminalValidationError("pre-measurement failure cannot carry runtime measurement evidence")
    else:
        if not measurement_path.is_file() \
                or terminal.get("runtime_measurement_sha256") != _sha256(measurement_path):
            raise TerminalValidationError("post-authorization runtime failure does not bind its PASS measurement")
        try:
            protocol.validate_runtime_measurement(lock, _strict_json(measurement_path))
        except Exception as error:
            raise TerminalValidationError(
                f"post-authorization runtime failure measurement is not genuine PASS: {error}") from error
        result = _strict_json(run_root / "output" / "RUN_RESULT.json")
        expected_result = {
            "authorization_scope": "production_authorized", "case_id": CASE_ID,
            "complete": False, "status": "failed",
            "error_identifier": terminal["error_identifier"],
            "error_message": terminal["error_message"],
        }
        if result != expected_result:
            raise TerminalValidationError("post-authorization producer RUN_RESULT is not exact")
    return {
        "failure_phase": phase,
        "stdout_sha256": _sha256(required_logs[0]),
        "stderr_sha256": _sha256(required_logs[1]),
    }


def _validate_terminal(
        terminal_root: Path, *, sealed_base_root: Path, extension_root: Path,
        seal_path: Path, run_root: Path | None = None, destination: Path | None = None,
        failure_package_root: Path | None = None, failure_receipt_path: Path | None = None,
        launch: Any | None = None,
) -> dict[str, object]:
    """Authenticate one terminal package and emit one non-authorizing adjudication."""
    launch = _load(Path(__file__).with_name("launch_t3_rev.py"), "t3_rev_terminal_launch") \
        if launch is None else launch
    if failure_package_root is not None or failure_receipt_path is not None:
        raise TerminalValidationError("failure evidence roots are fixed by the run contract")
    terminal_root = launch._absolute_literal_path(terminal_root)
    sealed_base_root = launch._absolute_literal_path(sealed_base_root)
    extension_root = launch._absolute_literal_path(extension_root)
    seal_path = launch._absolute_literal_path(seal_path)
    run_root = terminal_root.parent if run_root is None else launch._absolute_literal_path(run_root)
    for path, label in (
            (terminal_root, "terminal package"), (sealed_base_root, "sealed base"),
            (extension_root, "extension"), (seal_path, "seal"), (run_root, "run root")):
        try:
            launch.require_no_reparse_chain(path, label)
        except Exception as error:
            raise TerminalValidationError(f"{label} path identity failed: {error}") from error
    receipts = run_root / "receipts"
    destination = receipts / "T3_REV_TERMINAL_ADJUDICATION.json" if destination is None else Path(destination)
    if launch._literal_path_text(destination) != launch._literal_path_text(
            receipts / "T3_REV_TERMINAL_ADJUDICATION.json"):
        raise TerminalValidationError("terminal adjudication must remain in the run receipt directory")
    verifier = _load(Path(__file__).with_name("verify_extension_diff.py"), "t3_rev_terminal_diff")
    builder = _load(Path(__file__).with_name("build_t3_rev_extension.py"), "t3_rev_terminal_builder")
    base_before = builder.inventory_tree(sealed_base_root)
    extension_before = builder.inventory_tree(extension_root)
    seal = _strict_json(seal_path)
    launch_receipt = _strict_json(receipts / "T3_REV_LAUNCH_RECEIPT.json")
    lock_path = receipts / "T3_REV_EXECUTION_INPUT_LOCK.json"
    lock = _strict_json(lock_path)
    completed_terminal_path = terminal_root / "TERMINAL_RESULT.json"
    failure_terminal_path = receipts / "T3_REV_TERMINAL_FAILURE.json"
    present_terminal_paths = [
        path for path in (completed_terminal_path, failure_terminal_path) if path.is_file()
    ]
    if len(present_terminal_paths) != 1:
        raise TerminalValidationError("run must contain exactly one fixed completed or failure terminal receipt")
    terminal_path = present_terminal_paths[0]
    terminal = _strict_json(terminal_path)
    classification = classify_terminal(terminal)
    try:
        launch.require_bridge_authorization_receipt(launch_receipt)
    except Exception as error:
        raise TerminalValidationError(f"launch credential is invalid: {error}") from error
    seal_sha256 = require_canonical_seal_bytes(seal_path, seal)
    try:
        launch._require_seal(seal_path, str(launch_receipt["launcher_repository_commit"]))
    except Exception as error:
        raise TerminalValidationError(f"exact sealed producer/runtime identity failed: {error}") from error
    if seal.get("case_id") != CASE_ID or seal.get("authorization_capability") != AUTHORIZATION_CAPABILITY \
            or seal.get("resume_allowed") is not False or seal.get("follow_on_authorized") is not False \
            or launch_receipt.get("seal_sha256") != seal_sha256 or launch_receipt.get("run_root") != str(run_root):
        raise TerminalValidationError("canonical seal, nonce credential, and run-root binding differ")
    runtime_identity = seal.get("runtime_identity")
    seal_identity = seal.get("extension_identity")
    if not isinstance(runtime_identity, dict) or not isinstance(seal_identity, dict) \
            or launch_receipt.get("source_commit") != runtime_identity.get("source_commit") \
            or launch_receipt.get("launcher_repository_commit") != seal_identity.get("repository_commit") \
            or launch_receipt.get("runtime_lock_sha256") != runtime_identity.get("runtime_lock_sha256"):
        raise TerminalValidationError("launch source or runtime identity differs from the canonical seal")
    marker = _strict_json(launch.seal_consumption_marker(seal_sha256))
    expected_marker = {
        "schema_version": "toy_road_t3_rev_seal_consumption_v1", "case_id": CASE_ID,
        "composite_producer": "sealed_T3_base_plus_T3_rev_case_definition_extension",
        "authorization_capability": AUTHORIZATION_CAPABILITY, "seal_sha256": seal_sha256,
        "run_root": str(run_root), "resume_allowed": False, "new_authorization_required": True,
    }
    if marker != expected_marker:
        raise TerminalValidationError("global seal claim does not bind this terminal root")
    manifest = _strict_json(extension_root / "EXTENSION_SOURCE_MANIFEST.json")
    identity = seal.get("extension_identity")
    if not isinstance(identity, dict) or identity.get("extension_source_manifest_sha256") != _sha256(extension_root / "EXTENSION_SOURCE_MANIFEST.json") \
            or launch_receipt.get("extension_source_manifest_sha256") != _sha256(extension_root / "EXTENSION_SOURCE_MANIFEST.json"):
        raise TerminalValidationError("sealed composite extension identity differs")
    try:
        verified = verifier.verify_extension_diff(sealed_base_root, extension_root)
    except Exception as error:
        raise TerminalValidationError(f"extension verification failed: {error}") from error
    if verified != identity.get("verification"):
        raise TerminalValidationError("extension verification no longer matches the sealed composite")
    protocol_hashes = {item.get("path"): item.get("sha256") for item in manifest.get("shadow_files", []) if isinstance(item, dict)}
    generated_hash = protocol_hashes.get("toy_road_protocol.py")
    if not isinstance(generated_hash, str) or _sha256(extension_root / "toy_road_protocol.py") != generated_hash:
        raise TerminalValidationError("generated protocol is not the sealed extension byte identity")
    protocol = launch.load_protocol(extension_root / "toy_road_protocol.py", "t3_rev_terminal_protocol", generated_hash)
    try:
        protocol.validate_execution_input_lock(lock, CASE_ID)
        require_canonical_lock_bytes(protocol, lock_path, lock)
    except Exception as error:
        raise TerminalValidationError(f"authoritative execution lock validation failed: {error}") from error
    seal_builder = _load(Path(__file__).with_name("build_t3_rev_seal.py"), "t3_rev_terminal_seal")
    if not launch._exact_json_equal(runtime_identity, seal_builder.EXPECTED_EXECUTION):
        raise TerminalValidationError("sealed runtime/MATLAB/four-MEX identity is not the qualified exact mapping")
    cases = _strict_json(extension_root / "CASE_PHYSICS_CONTRACTS.json")
    case_table = cases.get("cases")
    case_contract = case_table.get(CASE_ID) if isinstance(case_table, dict) else None
    if not isinstance(case_contract, dict) \
            or lock.get("source_commit") != runtime_identity.get("source_commit") \
            or lock.get("source_manifest_sha256") != runtime_identity.get("source_manifest_sha256") \
            or lock.get("runtime_lock_sha256") != runtime_identity.get("runtime_lock_sha256") \
            or lock.get("family_contract_sha256") != cases.get("family_contract_sha256") \
            or lock.get("case_physics_contract_sha256") != case_contract.get("case_physics_contract_sha256") \
            or launch_receipt.get("family_contract_sha256") != lock.get("family_contract_sha256") \
            or launch_receipt.get("case_physics_contract_sha256") != lock.get("case_physics_contract_sha256"):
        raise TerminalValidationError("seal, extension contracts, launch, and lock identities differ")
    expectations = lock.get("runtime_expectations")
    sealed_matlab = runtime_identity.get("matlab")
    if not isinstance(expectations, dict) or not isinstance(sealed_matlab, dict) \
            or not launch._exact_json_equal(expectations.get("binary_sha256"), runtime_identity.get("four_binary_sha256")) \
            or not isinstance(expectations.get("matlab"), dict) \
            or any(not launch._exact_json_equal(expectations["matlab"].get(field), sealed_matlab.get(field))
                   for field in sealed_matlab if field != "absolute_path_order"):
        raise TerminalValidationError("runtime measurement lock differs from the sealed MATLAB or four-MEX identity")
    if launch_receipt.get("execution_input_lock_sha256") != _sha256(lock_path) \
            or launch_receipt.get("launch_nonce") is None \
            or launch_receipt.get("thread_environment") != runtime_identity.get("thread_settings"):
        raise TerminalValidationError("launch nonce, lock, or sealed thread identity differs")
    writable_roots = lock.get("writable_roots")
    expected_roots = {
        "output": str(terminal_root),
        **{name: str(run_root / name) for name in ("work", "temp", "tmp", "pref", "cache")},
        "matlab_startup_pref": str(run_root / "pref.matlab-startup"),
    }
    runtime_overlay = run_root / ".toy-road-runtime-overlay"
    path_order = expectations.get("matlab", {}).get("absolute_path_order") \
        if isinstance(expectations, dict) else None
    path_binding_failures: list[str] = []
    if not isinstance(writable_roots, dict) or writable_roots != expected_roots:
        path_binding_failures.append("writable_roots")
    if launch_receipt.get("extension_root") != str(extension_root):
        path_binding_failures.append("extension_root")
    if launch_receipt.get("runtime_overlay_root") != str(runtime_overlay):
        path_binding_failures.append("runtime_overlay_root")
    if not isinstance(path_order, list) or len(path_order) != 8:
        path_binding_failures.append("absolute_path_order_schema")
    elif path_order[0] != str(runtime_overlay) or path_order[1] != str(sealed_base_root) \
            or path_order[2:] != sealed_matlab.get("absolute_path_order", [])[2:]:
        path_binding_failures.append("absolute_path_order")
    if path_binding_failures:
        raise TerminalValidationError(
            "terminal/run launch path binding differs: " + ", ".join(path_binding_failures)
        )
    if not launch._exact_json_equal(launch_receipt.get("extension_shadow_sha256"), protocol_hashes) \
            or launch_receipt.get("bootstrap_helper_sha256") != launch.BOOTSTRAP_HELPER_SHA256:
        raise TerminalValidationError("launch shadow or bootstrap identity differs from the extension")
    try:
        launch.require_materialized_runtime_overlay(
            runtime_overlay, protocol_hashes, runtime_identity.get("four_binary_sha256")
        )
    except Exception as error:
        raise TerminalValidationError(f"materialized runtime overlay identity failed: {error}") from error
    authenticated: dict[str, object] | None = None
    phase_evidence: dict[str, object] | None = None
    if classification in {"PASS_CONFIRMED_FRACTURE_TRAJECTORY", "PASS_NO_CONFIRMED_FRACTURE_BY_C150"}:
        try:
            measurement = _strict_json(receipts / "T3_REV_RUNTIME_MEASUREMENT.json")
            protocol.validate_runtime_measurement(lock, measurement)
            authenticated = authenticate_completed_package(protocol, terminal_root)
        except Exception as error:
            raise TerminalValidationError(f"authoritative terminal package validation failed: {error}") from error
        if authenticated.get("execution_input_lock_sha256") != launch_receipt.get("execution_input_lock_sha256"):
            raise TerminalValidationError("terminal package lock does not bind the launch credential")
        if authenticated.get("package_root") != str(terminal_root):
            raise TerminalValidationError("authenticated terminal package root differs from the locked output root")
    elif classification in {"FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE", "FAIL_NEWTON_NONCONVERGENCE"}:
        try:
            failure_terminal_fields = {
                "schema_version", "status", "case_id", "terminal_reason", "failure_phase",
                "cycle", "substep", "seal_sha256", "run_root", "launch_receipt_sha256",
                "runtime_measurement_sha256", "failure_package_manifest_sha256",
            }
            failure_package = run_root / "T3_REV_FAILURE_PACKAGE"
            if set(terminal) != failure_terminal_fields \
                    or terminal.get("schema_version") != "toy_road_t3_rev_terminal_failure_v1" \
                    or terminal.get("status") != classification \
                    or terminal.get("case_id") != CASE_ID \
                    or terminal.get("failure_phase") != "producer_after_pass_runtime_measurement" \
                    or terminal.get("seal_sha256") != seal_sha256 \
                    or terminal.get("run_root") != str(run_root) \
                    or terminal.get("launch_receipt_sha256") != _sha256(
                        receipts / "T3_REV_LAUNCH_RECEIPT.json") \
                    or terminal.get("runtime_measurement_sha256") != _sha256(
                        receipts / "T3_REV_RUNTIME_MEASUREMENT.json") \
                    or terminal.get("failure_package_manifest_sha256") != _sha256(
                        failure_package / "PACKAGE_MANIFEST.json"):
                raise TerminalValidationError("numerical terminal failure receipt is not exact or bound")
            measurement = _strict_json(receipts / "T3_REV_RUNTIME_MEASUREMENT.json")
            protocol.validate_runtime_measurement(lock, measurement)
            phase_evidence = _validate_failure_package(
                failure_package, terminal, classification, lock, protocol, run_root,
                launch_receipt, seal_sha256, _sha256(
                    extension_root / "EXTENSION_SOURCE_MANIFEST.json"), case_contract,
            )
        except Exception as error:
            raise TerminalValidationError(f"numerical failure package validation failed: {error}") from error
    else:
        phase_evidence = _validate_startup_or_runtime_failure(
            terminal, classification, receipts, launch_receipt, seal_sha256, run_root,
            lock, protocol,
        )
    if builder.inventory_tree(sealed_base_root) != base_before or builder.inventory_tree(extension_root) != extension_before:
        raise TerminalValidationError("sealed base or extension inventory changed during terminal validation")
    result: dict[str, object] = {
        "schema_version": "toy_road_t3_rev_terminal_adjudication_v1",
        "status": terminal_adjudication_status(classification),
        "case_id": CASE_ID,
        "classification": classification,
        "terminal_reason": terminal["terminal_reason"],
        "seal_sha256": seal_sha256,
        "launch_receipt_sha256": _sha256(receipts / "T3_REV_LAUNCH_RECEIPT.json"),
        "execution_input_lock_sha256": _sha256(lock_path),
        "runtime_measurement_sha256": _sha256(receipts / "T3_REV_RUNTIME_MEASUREMENT.json")
        if (receipts / "T3_REV_RUNTIME_MEASUREMENT.json").is_file() else None,
        "extension_source_manifest_sha256": _sha256(extension_root / "EXTENSION_SOURCE_MANIFEST.json"),
        "sealed_base_inventory": base_before,
        "sealed_extension_inventory": extension_before,
        "terminal_authentication": authenticated,
        "phase_evidence": phase_evidence,
        "authorization_capability": None,
        "follow_on_authorized": False,
    }
    _write_create_once(destination, result)
    return result


def validate_terminal(
        terminal_root: Path, *, sealed_base_root: Path, extension_root: Path,
        seal_path: Path, run_root: Path | None = None, destination: Path | None = None,
) -> dict[str, object]:
    """Public terminal validation has no caller-selected protocol or evidence roots."""
    return _validate_terminal(
        terminal_root,
        sealed_base_root=sealed_base_root,
        extension_root=extension_root,
        seal_path=seal_path,
        run_root=run_root,
        destination=destination,
    )
