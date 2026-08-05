from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
from pathlib import Path, PureWindowsPath
from typing import Any, Mapping


class D1ProtocolError(RuntimeError):
    """Raised when D1 diagnostic evidence fails closed."""


DIAGNOSTIC_LOCK_SCHEMA = "toy_road_runtime_diagnostic_lock_v1"
TRANSFORMATION_SCHEMA = "toy_road_runtime_lock_transformation_v1"
DIAGNOSTIC_SCOPE = "diagnostic_only_non_authorizing"
FORBIDDEN_AUTHORIZATION_KEYS = {
    "authorization_path",
    "authorization_id",
    "authorization_sha256",
    "production_authorization_artifact",
    "consumed_marker_path",
}
THREAD_SETTINGS = {
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_DYNAMIC": "FALSE",
}
THREAD_SOURCE_PATH = (
    "producer_handoffs/toy_road_p0_repeatability_20260803/"
    "launch_toy_road_family_case.ps1"
)
THREAD_SOURCE_COMMIT = "eeda43d9faef01622731e877c5048a78f3c5003a"
THREAD_SOURCE_SHA256 = (
    "03d415ad96a484e9a98565fced0d6b8d2f90ffb781d48192a445d19ed5d5e728"
)
WRITABLE_ROOT_NAMES = {
    "work",
    "temp",
    "tmp",
    "pref",
    "cache",
    "matlab_startup_pref",
}
COMPLETE_PACKAGE_FILES = {
    "D1_DIAGNOSTIC_LOCK.json",
    "D1_LOCK_TRANSFORMATION.json",
    "D1_EXACT_BATCH_COMMAND.txt",
    "D1_LAUNCH_PROVENANCE.json",
    "D1_PROCESS_BEFORE.json",
    "D1_RUNTIME_DIAGNOSTIC.json",
    "D1_PROCESS_AFTER.json",
    "D1_TERMINAL.json",
    "D1_SHA256SUMS.txt",
    "MATLAB_STDOUT_STDERR.txt",
}
EXPECTED_PREDICATE_NAMES = (
    "diagnostic_lock_schema",
    "diagnostic_authorization_scope",
    "producer_entrypoint_not_authorized",
    "matlab_path_length",
    "matlab_path_prefix",
    "matlab_release",
    "matlab_update",
    "matlab_version",
    "matlab_computer",
    "matlab_executable_sha256",
    "matlab_blas",
    "matlab_lapack",
    "binary_initial_resolved",
    "binary_initial_readable",
    "binary_initial_sha256",
    "binary_AMOR_resolved",
    "binary_AMOR_readable",
    "binary_AMOR_sha256",
    "binary_AT1_HISTORY_FATIGUE_resolved",
    "binary_AT1_HISTORY_FATIGUE_readable",
    "binary_AT1_HISTORY_FATIGUE_sha256",
    "binary_cholmod2_resolved",
    "binary_cholmod2_readable",
    "binary_cholmod2_sha256",
)


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def canonical_json_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def derive_diagnostic_lock(
    source_lock: Mapping[str, object], relocation: Mapping[str, object]
) -> tuple[dict[str, object], dict[str, object]]:
    source = _require_mapping(source_lock, "source execution lock")
    move = _require_mapping(relocation, "diagnostic relocation")
    _require_exact_fields(
        move,
        {
            "diagnostic_root",
            "old_overlay",
            "new_overlay",
            "writable_roots",
            "quarantine_roots",
            "thread_source",
        },
        "diagnostic relocation",
    )
    _reject_forbidden_authorization_fields(source)
    _validate_thread_source(move["thread_source"])
    diagnostic_root = _require_path_text(move["diagnostic_root"], "diagnostic root")
    quarantine_roots = _require_path_list(move["quarantine_roots"], "quarantine roots")
    if any(_is_same_or_child(diagnostic_root, root) for root in quarantine_roots):
        raise D1ProtocolError("diagnostic root must not be inside a quarantine root")

    expectations = copy.deepcopy(
        _require_mapping(source.get("runtime_expectations"), "runtime expectations")
    )
    _require_exact_fields(
        expectations, {"matlab", "binary_sha256"}, "runtime expectations"
    )
    matlab = _require_mapping(expectations["matlab"], "MATLAB expectations")
    paths = matlab.get("absolute_path_order")
    if not isinstance(paths, list) or not paths or not all(isinstance(p, str) for p in paths):
        raise D1ProtocolError("MATLAB absolute_path_order must be nonempty text paths")
    old_overlay = _require_path_text(move["old_overlay"], "old overlay")
    new_overlay = _require_path_text(move["new_overlay"], "new overlay")
    if _canonical_path(paths[0]) != _canonical_path(old_overlay):
        raise D1ProtocolError("declared old overlay is not the locked path prefix")
    if any(_is_same_or_child(new_overlay, root) for root in quarantine_roots):
        raise D1ProtocolError("new overlay must not be inside a quarantine root")
    paths[0] = new_overlay

    writable = _require_mapping(move["writable_roots"], "diagnostic writable roots")
    _require_exact_fields(writable, WRITABLE_ROOT_NAMES, "diagnostic writable roots")
    normalized_writable: dict[str, str] = {}
    for name in sorted(WRITABLE_ROOT_NAMES):
        value = _require_path_text(writable[name], f"diagnostic writable root {name}")
        if not _is_same_or_child(value, diagnostic_root):
            raise D1ProtocolError(f"diagnostic writable root {name} is outside D1 root")
        if any(_is_same_or_child(value, root) for root in quarantine_roots):
            raise D1ProtocolError(f"diagnostic writable root {name} is quarantined")
        normalized_writable[name] = value

    thread_source = copy.deepcopy(dict(move["thread_source"]))
    diagnostic: dict[str, object] = {
        "schema_version": DIAGNOSTIC_LOCK_SCHEMA,
        "protocol_version": source.get("protocol_version"),
        "authorization_scope": DIAGNOSTIC_SCOPE,
        "producer_entrypoint_authorized": False,
        "source_commit": source.get("source_commit"),
        "source_manifest_sha256": source.get("source_manifest_sha256"),
        "runtime_lock_sha256": source.get("runtime_lock_sha256"),
        "source_execution_lock_sha256": canonical_json_sha256(source),
        "runtime_expectations": expectations,
        "thread_environment": copy.deepcopy(THREAD_SETTINGS),
        "thread_setting_source": thread_source,
        "diagnostic_root": diagnostic_root,
        "writable_roots": normalized_writable,
    }
    _reject_forbidden_authorization_fields(diagnostic)
    before = _unchanged_projection_from_source(source, old_overlay)
    after = _unchanged_projection_from_diagnostic(diagnostic, new_overlay)
    before_sha = canonical_json_sha256(before)
    after_sha = canonical_json_sha256(after)
    if before_sha != after_sha:
        raise D1ProtocolError("undeclared runtime identity changed during derivation")
    replacements = [
        {"field": "runtime_expectations.matlab.absolute_path_order[0]", "old": old_overlay,
         "new": new_overlay, "reason": "fresh_diagnostic_overlay"},
    ]
    source_writable = _require_mapping(source.get("writable_roots"), "source writable roots")
    for name in sorted(WRITABLE_ROOT_NAMES):
        replacements.append(
            {
                "field": f"writable_roots.{name}",
                "old": source_writable.get(name),
                "new": normalized_writable[name],
                "reason": "fresh_diagnostic_writable_root",
            }
        )
    transformation: dict[str, object] = {
        "schema_version": TRANSFORMATION_SCHEMA,
        "source_execution_lock_sha256": canonical_json_sha256(source),
        "diagnostic_lock_sha256": canonical_json_sha256(diagnostic),
        "replacements": replacements,
        "unchanged_fields_sha256_before": before_sha,
        "unchanged_fields_sha256_after": after_sha,
        "thread_setting_source": thread_source,
        "authorization_artifact_read": False,
        "production_output_root_present": False,
    }
    return diagnostic, transformation


def validate_diagnostic_lock(
    source_lock: Mapping[str, object],
    diagnostic_lock: Mapping[str, object],
    transformation: Mapping[str, object],
    source_execution_lock_sha256: str | None = None,
) -> None:
    source = _require_mapping(source_lock, "source execution lock")
    diagnostic = _require_mapping(diagnostic_lock, "diagnostic lock")
    transform = _require_mapping(transformation, "lock transformation")
    _reject_forbidden_authorization_fields(diagnostic)
    if diagnostic.get("schema_version") != DIAGNOSTIC_LOCK_SCHEMA:
        raise D1ProtocolError("diagnostic lock schema is not approved")
    if diagnostic.get("authorization_scope") != DIAGNOSTIC_SCOPE:
        raise D1ProtocolError("diagnostic authorization scope is not approved")
    if diagnostic.get("producer_entrypoint_authorized") is not False:
        raise D1ProtocolError("diagnostic lock must not authorize producer entrypoint")
    if transform.get("schema_version") != TRANSFORMATION_SCHEMA:
        raise D1ProtocolError("lock transformation schema is not approved")
    if transform.get("authorization_artifact_read") is not False:
        raise D1ProtocolError("diagnostic transformation read authorization evidence")
    if transform.get("production_output_root_present") is not False:
        raise D1ProtocolError("diagnostic lock contains a production output root")
    _validate_thread_source(diagnostic.get("thread_setting_source"))
    _validate_thread_source(transform.get("thread_setting_source"))
    if diagnostic.get("thread_environment") != THREAD_SETTINGS:
        raise D1ProtocolError("diagnostic thread environment differs from sealed launcher")
    expected_source_sha = source_execution_lock_sha256 or canonical_json_sha256(source)
    if re.fullmatch(r"[0-9a-f]{64}", expected_source_sha) is None:
        raise D1ProtocolError("source execution lock SHA-256 is invalid")
    if diagnostic.get("source_execution_lock_sha256") != expected_source_sha:
        raise D1ProtocolError("diagnostic source execution lock SHA-256 differs")
    if transform.get("source_execution_lock_sha256") != expected_source_sha:
        raise D1ProtocolError("transformation source execution lock SHA-256 differs")
    if transform.get("diagnostic_lock_sha256") != canonical_json_sha256(diagnostic):
        raise D1ProtocolError("transformation diagnostic lock SHA-256 differs")
    replacements = transform.get("replacements")
    if not isinstance(replacements, list) or len(replacements) != 7:
        raise D1ProtocolError("lock transformation replacements are incomplete")
    old_overlay = replacements[0].get("old") if isinstance(replacements[0], dict) else None
    new_overlay = replacements[0].get("new") if isinstance(replacements[0], dict) else None
    before_sha = canonical_json_sha256(
        _unchanged_projection_from_source(source, _require_path_text(old_overlay, "old overlay"))
    )
    after_sha = canonical_json_sha256(
        _unchanged_projection_from_diagnostic(
            diagnostic, _require_path_text(new_overlay, "new overlay")
        )
    )
    if before_sha != after_sha:
        raise D1ProtocolError("diagnostic unchanged runtime identity differs")
    if transform.get("unchanged_fields_sha256_before") != before_sha:
        raise D1ProtocolError("before unchanged-fields SHA-256 differs")
    if transform.get("unchanged_fields_sha256_after") != after_sha:
        raise D1ProtocolError("after unchanged-fields SHA-256 differs")
    source_writable = _require_mapping(source.get("writable_roots"), "source writable roots")
    diagnostic_writable = _require_mapping(
        diagnostic.get("writable_roots"), "diagnostic writable roots"
    )
    expected_replacements = [
        {
            "field": "runtime_expectations.matlab.absolute_path_order[0]",
            "old": old_overlay,
            "new": new_overlay,
            "reason": "fresh_diagnostic_overlay",
        }
    ]
    for name in sorted(WRITABLE_ROOT_NAMES):
        expected_replacements.append(
            {
                "field": f"writable_roots.{name}",
                "old": source_writable.get(name),
                "new": diagnostic_writable.get(name),
                "reason": "fresh_diagnostic_writable_root",
            }
        )
    if replacements != expected_replacements:
        raise D1ProtocolError("lock transformation replacements differ from reconstructed values")


def derive_diagnostic_lock_files(
    source_path: Path,
    relocation_path: Path,
    diagnostic_path: Path,
    transformation_path: Path,
) -> dict[str, str]:
    source_path = Path(source_path)
    relocation_path = Path(relocation_path)
    diagnostic_path = Path(diagnostic_path)
    transformation_path = Path(transformation_path)
    if diagnostic_path.exists() or transformation_path.exists():
        raise D1ProtocolError("diagnostic lock output already exists")
    source_bytes = source_path.read_bytes()
    source = _read_json_bytes(source_bytes, "source execution lock")
    relocation = _read_json_bytes(relocation_path.read_bytes(), "diagnostic relocation")
    diagnostic, transformation = derive_diagnostic_lock(source, relocation)
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    diagnostic["source_execution_lock_sha256"] = source_sha
    transformation["source_execution_lock_sha256"] = source_sha
    transformation["diagnostic_lock_sha256"] = canonical_json_sha256(diagnostic)
    diagnostic_bytes = canonical_json_bytes(diagnostic)
    transformation_bytes = canonical_json_bytes(transformation)
    _write_exclusive(diagnostic_path, diagnostic_bytes)
    try:
        _write_exclusive(transformation_path, transformation_bytes)
    except Exception:
        diagnostic_path.unlink(missing_ok=True)
        raise
    return {
        "diagnostic_lock_sha256": hashlib.sha256(diagnostic_bytes).hexdigest(),
        "transformation_sha256": hashlib.sha256(transformation_bytes).hexdigest(),
    }


def validate_d1_package(root: Path) -> dict[str, object]:
    package = Path(root)
    if not package.is_dir():
        raise D1ProtocolError("D1 package root is missing")
    files = {path.name: path for path in package.iterdir() if path.is_file()}
    if any(name.lower().endswith(".consumed") for name in files):
        raise D1ProtocolError("D1 package contains a forbidden .consumed artifact")
    if set(files) == COMPLETE_PACKAGE_FILES:
        return _validate_complete_d1_package(files)
    return _validate_partial_d1_package(files)


def _validate_complete_d1_package(files: Mapping[str, Path]) -> dict[str, object]:
    sums_path = files["D1_SHA256SUMS.txt"]
    try:
        lines = sums_path.read_text("ascii").splitlines()
    except (OSError, UnicodeDecodeError) as exception:
        raise D1ProtocolError("D1 checksum file is unreadable") from exception
    if len(lines) != 9:
        raise D1ProtocolError("D1 checksum file must contain exactly nine entries")
    expected_names = COMPLETE_PACKAGE_FILES - {"D1_SHA256SUMS.txt"}
    checksums: dict[str, str] = {}
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        if match is None or match.group(2) in checksums:
            raise D1ProtocolError("D1 checksum line is malformed or duplicated")
        checksums[match.group(2)] = match.group(1)
    if set(checksums) != expected_names:
        raise D1ProtocolError("D1 checksum names differ from the nine package files")
    for name, digest in checksums.items():
        actual = hashlib.sha256(files[name].read_bytes()).hexdigest()
        if actual != digest:
            raise D1ProtocolError(f"D1 package SHA-256 mismatch: {name}")

    lock = _read_json_bytes(files["D1_DIAGNOSTIC_LOCK.json"].read_bytes(), "D1 lock")
    transformation = _read_json_bytes(
        files["D1_LOCK_TRANSFORMATION.json"].read_bytes(), "D1 transformation"
    )
    provenance = _read_json_bytes(
        files["D1_LAUNCH_PROVENANCE.json"].read_bytes(), "D1 launch provenance"
    )
    before = _read_json_bytes(files["D1_PROCESS_BEFORE.json"].read_bytes(), "D1 process before")
    after = _read_json_bytes(files["D1_PROCESS_AFTER.json"].read_bytes(), "D1 process after")
    receipt = _read_json_bytes(
        files["D1_RUNTIME_DIAGNOSTIC.json"].read_bytes(), "D1 diagnostic receipt"
    )
    terminal = _read_json_bytes(files["D1_TERMINAL.json"].read_bytes(), "D1 terminal")
    if lock.get("schema_version") != DIAGNOSTIC_LOCK_SCHEMA:
        raise D1ProtocolError("D1 package lock schema is invalid")
    if lock.get("authorization_scope") != DIAGNOSTIC_SCOPE:
        raise D1ProtocolError("D1 package lock scope is invalid")
    if transformation.get("schema_version") != TRANSFORMATION_SCHEMA:
        raise D1ProtocolError("D1 package transformation schema is invalid")
    lock_sha = hashlib.sha256(files["D1_DIAGNOSTIC_LOCK.json"].read_bytes()).hexdigest()
    transform_sha = hashlib.sha256(
        files["D1_LOCK_TRANSFORMATION.json"].read_bytes()
    ).hexdigest()
    batch_bytes = files["D1_EXACT_BATCH_COMMAND.txt"].read_bytes()
    if transformation.get("diagnostic_lock_sha256") != lock_sha:
        raise D1ProtocolError("D1 transformation lock SHA-256 is invalid")
    if provenance.get("diagnostic_lock_sha256") != lock_sha:
        raise D1ProtocolError("D1 provenance lock SHA-256 is invalid")
    if provenance.get("transformation_sha256") != transform_sha:
        raise D1ProtocolError("D1 provenance transformation SHA-256 is invalid")
    if provenance.get("batch_sha256") != hashlib.sha256(batch_bytes).hexdigest():
        raise D1ProtocolError("D1 provenance batch SHA-256 is invalid")
    batch = batch_bytes.decode("utf-8")
    if len(re.findall(r"run_toy_road_runtime_diagnostic\s*\(", batch)) != 1:
        raise D1ProtocolError("D1 batch does not contain exactly one diagnostic call")
    if any(name in batch for name in _forbidden_entrypoint_names()):
        raise D1ProtocolError("D1 batch contains a production entrypoint")
    if provenance.get("authorization_path_present") is not False:
        raise D1ProtocolError("D1 provenance contains an authorization path")
    if provenance.get("production_output_parameter_present") is not False:
        raise D1ProtocolError("D1 provenance contains a production output parameter")
    for label, inventory in (("before", before), ("after", after)):
        if inventory.get("schema_version") != "toy_road_d1_process_inventory_v1":
            raise D1ProtocolError(f"D1 {label} process inventory schema is invalid")
        if inventory.get("count") != 0 or inventory.get("processes") != []:
            raise D1ProtocolError(f"D1 {label} process inventory is nonzero")
    if receipt.get("schema_version") != "toy_road_runtime_diagnostic_v1":
        raise D1ProtocolError("D1 diagnostic receipt schema is invalid")
    result = receipt.get("status")
    if result not in {"PASS", "FAIL"}:
        raise D1ProtocolError("D1 diagnostic receipt is not terminal")
    for value in (lock, receipt):
        if value.get("authorization_scope") != DIAGNOSTIC_SCOPE:
            raise D1ProtocolError("D1 artifact scope is invalid")
        if value.get("producer_entrypoint_authorized") is not False:
            raise D1ProtocolError("D1 artifact authorizes a producer")
    required_terminal = {
        "schema_version": "toy_road_d1_terminal_v1",
        "status": "D1_DIAGNOSTIC_EVIDENCE_COMPLETE",
        "diagnostic_result": result,
        "production_authorized": False,
        "authorization_consumed": False,
        "automatic_retry_performed": False,
        "producer_invocation_count": 0,
        "fem_cycle_count": 0,
        "matlab_process_count_before": 0,
        "matlab_process_count_after": 0,
        "production_output_absent": True,
    }
    for field, expected in required_terminal.items():
        if terminal.get(field) != expected:
            raise D1ProtocolError(f"D1 terminal field is invalid: {field}")
    if receipt.get("producer_invocation_count") != 0 or receipt.get("fem_cycle_count") != 0:
        raise D1ProtocolError("D1 diagnostic receipt reports producer or FEM activity")
    _validate_predicate_chronology(receipt, result)
    return {
        "status": "D1_DIAGNOSTIC_EVIDENCE_ACCEPTED",
        "diagnostic_result": result,
        "production_authorized": False,
    }


def _validate_predicate_chronology(receipt: Mapping[str, object], result: object) -> None:
    predicates = receipt.get("predicates")
    if not isinstance(predicates, list) or not predicates:
        raise D1ProtocolError("D1 predicate chronology is missing")
    if len(predicates) > len(EXPECTED_PREDICATE_NAMES):
        raise D1ProtocolError("D1 predicate chronology has extra rows")
    names: list[str] = []
    passes: list[bool] = []
    required_fields = {
        "ordinal", "name", "expected", "measured_raw", "measured_normalized",
        "pass", "measured_at_utc",
    }
    for index, row in enumerate(predicates):
        if not isinstance(row, Mapping) or set(row) != required_fields:
            raise D1ProtocolError("D1 predicate row schema is invalid")
        if row.get("ordinal") != index + 1:
            raise D1ProtocolError("D1 predicate ordinal is invalid")
        if row.get("name") != EXPECTED_PREDICATE_NAMES[index]:
            raise D1ProtocolError("D1 predicate names or order are invalid")
        if not isinstance(row.get("pass"), bool):
            raise D1ProtocolError("D1 predicate pass value is invalid")
        names.append(str(row["name"]))
        passes.append(bool(row["pass"]))
    if receipt.get("completed_predicate_count") != len(predicates):
        raise D1ProtocolError("D1 completed predicate count is invalid")
    failures = [index for index, passed in enumerate(passes) if not passed]
    if result == "PASS":
        if len(predicates) != len(EXPECTED_PREDICATE_NAMES) or failures:
            raise D1ProtocolError("D1 PASS predicate chronology is incomplete")
        if receipt.get("first_failed_predicate") not in (None, []):
            raise D1ProtocolError("D1 PASS has a first failed predicate")
        return
    if len(failures) != 1 or failures[0] != len(predicates) - 1:
        raise D1ProtocolError("D1 FAIL chronology must stop at its first failure")
    if receipt.get("first_failed_predicate") != names[failures[0]]:
        raise D1ProtocolError("D1 first failed predicate differs from chronology")
    exception = receipt.get("matlab_exception")
    if not isinstance(exception, Mapping):
        raise D1ProtocolError("D1 FAIL structured exception is missing")
    for field in ("identifier", "message", "extended_report"):
        if not isinstance(exception.get(field), str) or not exception[field]:
            raise D1ProtocolError("D1 FAIL structured exception is incomplete")
    if not isinstance(exception.get("stack"), list):
        raise D1ProtocolError("D1 FAIL structured exception stack is invalid")


def _validate_partial_d1_package(files: Mapping[str, Path]) -> dict[str, object]:
    allowed = COMPLETE_PACKAGE_FILES | {"D1_LAUNCHER_RECOVERY.json"}
    for name in files:
        if name in allowed or re.fullmatch(
            r"\.D1_RUNTIME_DIAGNOSTIC\.json\.[0-9A-Fa-f-]+\.tmp", name
        ):
            continue
        raise D1ProtocolError(f"D1 partial package contains undeclared file: {name}")
    if "D1_TERMINAL.json" in files or "D1_SHA256SUMS.txt" in files:
        raise D1ProtocolError("D1 partial package must not claim terminal completion")
    recovery_path = files.get("D1_LAUNCHER_RECOVERY.json")
    if recovery_path is not None:
        recovery = _read_json_bytes(recovery_path.read_bytes(), "D1 launcher recovery")
        required = {
            "schema_version": "toy_road_d1_launcher_recovery_v1",
            "status": "PARTIAL_FAIL",
            "authorization_scope": DIAGNOSTIC_SCOPE,
            "producer_invocation_count": 0,
            "fem_cycle_count": 0,
            "automatic_retry_performed": False,
        }
        for field, expected in required.items():
            if recovery.get(field) != expected:
                raise D1ProtocolError(f"D1 recovery field is invalid: {field}")
    if not files:
        raise D1ProtocolError("D1 partial package is empty")
    return {
        "status": "D1_DIAGNOSTIC_EVIDENCE_PARTIAL",
        "diagnostic_result": "PARTIAL_FAIL",
        "production_authorized": False,
    }


def _forbidden_entrypoint_names() -> tuple[str, ...]:
    return (
        "main_" + "toy_road_family_case",
        "solve_" + "toy_road_family_case",
        "recover_" + "toy_road_family_state",
    )


def _unchanged_projection_from_source(source: Mapping[str, object], overlay: str) -> dict[str, object]:
    expectations = copy.deepcopy(source["runtime_expectations"])
    expectations["matlab"]["absolute_path_order"][0] = "<D1_OVERLAY>"
    return {
        "protocol_version": source.get("protocol_version"),
        "source_commit": source.get("source_commit"),
        "source_manifest_sha256": source.get("source_manifest_sha256"),
        "runtime_lock_sha256": source.get("runtime_lock_sha256"),
        "runtime_expectations": expectations,
    }


def _unchanged_projection_from_diagnostic(
    diagnostic: Mapping[str, object], overlay: str
) -> dict[str, object]:
    expectations = copy.deepcopy(diagnostic["runtime_expectations"])
    expectations["matlab"]["absolute_path_order"][0] = "<D1_OVERLAY>"
    return {
        "protocol_version": diagnostic.get("protocol_version"),
        "source_commit": diagnostic.get("source_commit"),
        "source_manifest_sha256": diagnostic.get("source_manifest_sha256"),
        "runtime_lock_sha256": diagnostic.get("runtime_lock_sha256"),
        "runtime_expectations": expectations,
    }


def _validate_thread_source(value: object) -> None:
    source = _require_mapping(value, "thread-setting source")
    _require_exact_fields(
        source, {"path", "source_commit", "sha256", "settings"}, "thread-setting source"
    )
    expected = {
        "path": THREAD_SOURCE_PATH,
        "source_commit": THREAD_SOURCE_COMMIT,
        "sha256": THREAD_SOURCE_SHA256,
        "settings": THREAD_SETTINGS,
    }
    if source != expected:
        raise D1ProtocolError("thread-setting source differs from sealed launcher")


def _reject_forbidden_authorization_fields(value: object) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in FORBIDDEN_AUTHORIZATION_KEYS:
                raise D1ProtocolError(f"forbidden authorization artifact field: {key}")
            _reject_forbidden_authorization_fields(item)
    elif isinstance(value, list):
        for item in value:
            _reject_forbidden_authorization_fields(item)
    elif isinstance(value, str) and value.lower().endswith(".consumed"):
        raise D1ProtocolError("forbidden .consumed artifact path")


def _require_mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise D1ProtocolError(f"{label} must be one JSON object")
    return dict(value)


def _require_exact_fields(value: Mapping[str, object], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise D1ProtocolError(f"{label} fields differ from the schema")


def _require_path_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise D1ProtocolError(f"{label} must be nonempty path text")
    return value


def _require_path_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(x, str) and x for x in value):
        raise D1ProtocolError(f"{label} must be nonempty path text array")
    return list(value)


def _canonical_path(value: str) -> str:
    return str(PureWindowsPath(value)).replace("/", "\\").rstrip("\\").casefold()


def _is_same_or_child(value: str, parent: str) -> bool:
    child_path = _canonical_path(value)
    parent_path = _canonical_path(parent)
    return child_path == parent_path or child_path.startswith(parent_path + "\\")


def _read_json_bytes(payload: bytes, label: str) -> dict[str, object]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exception:
        raise D1ProtocolError(f"{label} is not UTF-8 JSON") from exception
    return _require_mapping(value, label)


def _write_exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exception:
        raise D1ProtocolError(f"diagnostic output already exists: {path}") from exception


def _main_cli() -> int:
    arguments = sys.argv[1:]
    if len(arguments) == 5 and arguments[0] == "--derive-lock":
        receipt = derive_diagnostic_lock_files(
            Path(arguments[1]), Path(arguments[2]), Path(arguments[3]), Path(arguments[4])
        )
        print(canonical_json_bytes(receipt).decode("ascii"))
        return 0
    if len(arguments) == 4 and arguments[0] == "--validate-lock":
        source_bytes = Path(arguments[1]).read_bytes()
        source = _read_json_bytes(source_bytes, "source execution lock")
        diagnostic = _read_json_bytes(Path(arguments[2]).read_bytes(), "diagnostic lock")
        transformation = _read_json_bytes(
            Path(arguments[3]).read_bytes(), "lock transformation"
        )
        validate_diagnostic_lock(
            source,
            diagnostic,
            transformation,
            hashlib.sha256(source_bytes).hexdigest(),
        )
        print('{"status":"PASS"}')
        return 0
    raise D1ProtocolError("unsupported D1 protocol command")


if __name__ == "__main__":
    try:
        raise SystemExit(_main_cli())
    except D1ProtocolError as exception:
        print(str(exception), file=sys.stderr)
        raise SystemExit(2) from exception
