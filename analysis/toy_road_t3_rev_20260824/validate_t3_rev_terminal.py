"""Fail-closed, create-once terminal adjudication for the one T3-rev run."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping


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
        "confirmed": "PASS_CONFIRMED_FRACTURE_TRAJECTORY",
        "confirmed_penetration": "PASS_CONFIRMED_FRACTURE_TRAJECTORY",
        "right_censored": "PASS_NO_CONFIRMED_FRACTURE_BY_C150",
        "coupled_fixed_point_nonconvergence": "FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE",
        "newton_nonconvergence": "FAIL_NEWTON_NONCONVERGENCE",
        "startup_failure": "FAIL_STARTUP",
        "runtime_failure": "FAIL_RUNTIME",
        "runtime_qualification_failure": "FAIL_RUNTIME",
    }
    if reason not in classes:
        raise TerminalValidationError(f"unknown terminal_reason: {reason!r}")
    if reason == "right_censored" and terminal.get("terminal_cycle") != 150:
        raise TerminalValidationError("right-censored outcome must end at c150")
    if reason in {"coupled_fixed_point_nonconvergence", "newton_nonconvergence"}:
        if type(terminal.get("cycle")) is not int or type(terminal.get("substep")) is not int:
            raise TerminalValidationError("solver nonconvergence must identify exact cycle and substep")
    return classes[reason]


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


def validate_terminal(
        terminal_root: Path, *, sealed_base_root: Path, extension_root: Path,
        seal_path: Path, run_root: Path | None = None, destination: Path | None = None,
) -> dict[str, object]:
    """Authenticate one terminal package and emit one non-authorizing adjudication."""
    terminal_root, sealed_base_root = Path(terminal_root), Path(sealed_base_root)
    extension_root, seal_path = Path(extension_root), Path(seal_path)
    run_root = terminal_root.parent if run_root is None else Path(run_root)
    receipts = run_root / "receipts"
    destination = receipts / "T3_REV_TERMINAL_ADJUDICATION.json" if destination is None else Path(destination)
    if destination.parent != receipts:
        raise TerminalValidationError("terminal adjudication must remain in the run receipt directory")
    launch = _load(Path(__file__).with_name("launch_t3_rev.py"), "t3_rev_terminal_launch")
    verifier = _load(Path(__file__).with_name("verify_extension_diff.py"), "t3_rev_terminal_diff")
    builder = _load(Path(__file__).with_name("build_t3_rev_extension.py"), "t3_rev_terminal_builder")
    base_before = builder.inventory_tree(sealed_base_root)
    extension_before = builder.inventory_tree(extension_root)
    seal = _strict_json(seal_path)
    launch_receipt = _strict_json(receipts / "T3_REV_LAUNCH_RECEIPT.json")
    lock_path = receipts / "T3_REV_EXECUTION_INPUT_LOCK.json"
    lock = _strict_json(lock_path)
    measurement = _strict_json(receipts / "T3_REV_RUNTIME_MEASUREMENT.json")
    try:
        launch.require_bridge_authorization_receipt(launch_receipt)
    except Exception as error:
        raise TerminalValidationError(f"launch credential is invalid: {error}") from error
    seal_sha256 = _sha256(seal_path)
    if seal.get("case_id") != CASE_ID or seal.get("authorization_capability") != AUTHORIZATION_CAPABILITY \
            or seal.get("resume_allowed") is not False or seal.get("follow_on_authorized") is not False \
            or launch_receipt.get("seal_sha256") != seal_sha256 or launch_receipt.get("run_root") != str(run_root):
        raise TerminalValidationError("canonical seal, nonce credential, and run-root binding differ")
    marker = _strict_json(launch.seal_consumption_marker(seal_sha256))
    if marker.get("seal_sha256") != seal_sha256 or marker.get("case_id") != CASE_ID \
            or marker.get("run_root") != str(run_root) or marker.get("authorization_capability") != AUTHORIZATION_CAPABILITY:
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
        protocol.validate_runtime_measurement(lock, measurement)
    except Exception as error:
        raise TerminalValidationError(f"authoritative lock/runtime validation failed: {error}") from error
    runtime_identity = seal.get("runtime_identity")
    if not isinstance(runtime_identity, dict):
        raise TerminalValidationError("sealed runtime identity is malformed")
    seal_builder = _load(Path(__file__).with_name("build_t3_rev_seal.py"), "t3_rev_terminal_seal")
    if not launch._exact_json_equal(runtime_identity, seal_builder.EXPECTED_EXECUTION):
        raise TerminalValidationError("sealed runtime/MATLAB/four-MEX identity is not the qualified exact mapping")
    expectations = lock.get("runtime_expectations")
    sealed_matlab = runtime_identity.get("matlab")
    if not isinstance(expectations, dict) or not isinstance(sealed_matlab, dict) \
            or not launch._exact_json_equal(expectations.get("binary_sha256"), runtime_identity.get("four_binary_sha256")) \
            or not isinstance(expectations.get("matlab"), dict) \
            or any(expectations["matlab"].get(field) != sealed_matlab.get(field)
                   for field in sealed_matlab if field != "absolute_path_order"):
        raise TerminalValidationError("runtime measurement lock differs from the sealed MATLAB or four-MEX identity")
    if launch_receipt.get("execution_input_lock_sha256") != _sha256(lock_path) \
            or launch_receipt.get("launch_nonce") is None \
            or launch_receipt.get("thread_environment") != runtime_identity.get("thread_settings"):
        raise TerminalValidationError("launch nonce, lock, or sealed thread identity differs")
    terminal = _strict_json(terminal_root / "TERMINAL_RESULT.json")
    classification = classify_terminal(terminal)
    authenticated: dict[str, object] | None = None
    if classification == "PASS_CONFIRMED_FRACTURE_TRAJECTORY":
        try:
            authenticated = protocol.authenticate_terminal_package(terminal_root, CASE_ID)
        except Exception as error:
            raise TerminalValidationError(f"authoritative terminal package validation failed: {error}") from error
        if authenticated.get("execution_input_lock_sha256") != launch_receipt.get("execution_input_lock_sha256"):
            raise TerminalValidationError("terminal package lock does not bind the launch credential")
    else:
        try:
            snapshot = protocol._capture_package_bytes(terminal_root, "T3-rev terminal")
            package_manifest = protocol._read_json_bytes(
                snapshot["bytes"].get("TERMINAL_MANIFEST.json"), "T3-rev terminal manifest"
            )
            protocol._validate_c5(snapshot, package_manifest, "T3-rev terminal")
        except Exception as error:
            raise TerminalValidationError(f"non-confirmed terminal C5 four-gate receipt failed: {error}") from error
    if builder.inventory_tree(sealed_base_root) != base_before or builder.inventory_tree(extension_root) != extension_before:
        raise TerminalValidationError("sealed base or extension inventory changed during terminal validation")
    result: dict[str, object] = {
        "schema_version": "toy_road_t3_rev_terminal_adjudication_v1",
        "status": "PASS_TERMINAL_ADJUDICATION",
        "case_id": CASE_ID,
        "classification": classification,
        "terminal_reason": terminal["terminal_reason"],
        "seal_sha256": seal_sha256,
        "launch_receipt_sha256": _sha256(receipts / "T3_REV_LAUNCH_RECEIPT.json"),
        "execution_input_lock_sha256": _sha256(lock_path),
        "runtime_measurement_sha256": _sha256(receipts / "T3_REV_RUNTIME_MEASUREMENT.json"),
        "extension_source_manifest_sha256": _sha256(extension_root / "EXTENSION_SOURCE_MANIFEST.json"),
        "sealed_base_inventory": base_before,
        "sealed_extension_inventory": extension_before,
        "terminal_authentication": authenticated,
        "authorization_capability": None,
        "follow_on_authorized": False,
    }
    _write_create_once(destination, result)
    return result
