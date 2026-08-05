from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "producer_handoffs" / "toy_road_p0_repeatability_20260803"
MODULE_PATH = HANDOFF / "toy_road_d1_protocol.py"
SPEC = importlib.util.spec_from_file_location("toy_road_d1_protocol", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
PROTOCOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROTOCOL)

PRODUCTION_PATH = HANDOFF / "toy_road_protocol.py"
PRODUCTION_SPEC = importlib.util.spec_from_file_location(
    "toy_road_protocol_for_d1_tests", PRODUCTION_PATH
)
assert PRODUCTION_SPEC is not None and PRODUCTION_SPEC.loader is not None
PRODUCTION = importlib.util.module_from_spec(PRODUCTION_SPEC)
PRODUCTION_SPEC.loader.exec_module(PRODUCTION)

D1ProtocolError = PROTOCOL.D1ProtocolError

SOURCE_COMMIT = "eeda43d9faef01622731e877c5048a78f3c5003a"
LAUNCHER_SHA256 = "03d415ad96a484e9a98565fced0d6b8d2f90ffb781d48192a445d19ed5d5e728"
THREAD_SETTINGS = {
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_DYNAMIC": "FALSE",
}
FORBIDDEN_KEYS = {
    "authorization_path",
    "authorization_id",
    "authorization_sha256",
    "production_authorization_artifact",
    "consumed_marker_path",
}

EXPECTED_PREDICATES = [
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
]


def _source_lock(tmp_path: Path) -> dict[str, object]:
    production = tmp_path / "quarantine" / "P0_parent"
    overlay = production / ".toy-road-runtime-overlay-old"
    return {
        "schema_version": "toy_road_execution_input_lock_v1",
        "protocol_version": "toy-road-p0-repeatability-v2.1",
        "authorization_scope": "production_authorized",
        "case_id": "P0_parent",
        "source_commit": SOURCE_COMMIT,
        "source_manifest_sha256": "0" * 64,
        "runtime_lock_sha256": "1" * 64,
        "family_contract_sha256": "2" * 64,
        "case_physics_contract_sha256": "3" * 64,
        "launch_timestamp_utc": "2026-08-04T13:17:28Z",
        "no_clobber_receipt_id": "old-receipt",
        "resume_allowed": False,
        "runtime_expectations": {
            "matlab": {
                "release": "R2025b",
                "update": "Update 5",
                "version": "25.2.0.3177638",
                "computer": "PCWIN64",
                "executable_sha256": "4" * 64,
                "blas": "locked BLAS",
                "lapack": "locked LAPACK",
                "absolute_path_order": [
                    str(overlay),
                    str(tmp_path / "sealed-handoff"),
                    str(tmp_path / "griphfith" / "Sources"),
                    str(tmp_path / "SuiteSparse" / "CHOLMOD" / "MATLAB"),
                ],
            },
            "binary_sha256": {
                "initial": "5" * 64,
                "AMOR": "6" * 64,
                "AT1_HISTORY_FATIGUE": "7" * 64,
                "cholmod2": "8" * 64,
            },
        },
        "writable_roots": {
            "output": str(production / "output"),
            "work": str(production / "work"),
            "temp": str(production / "temp"),
            "tmp": str(production / "tmp"),
            "pref": str(production / "pref"),
            "cache": str(production / "cache"),
            "matlab_startup_pref": str(production / "pref.matlab-startup"),
        },
    }


def _relocation(tmp_path: Path, source_lock: dict[str, object]) -> dict[str, object]:
    root = tmp_path / "d1"
    old_overlay = source_lock["runtime_expectations"]["matlab"][
        "absolute_path_order"
    ][0]
    return {
        "diagnostic_root": str(root),
        "old_overlay": old_overlay,
        "new_overlay": str(root / "overlay"),
        "writable_roots": {
            name: str(root / name)
            for name in (
                "work",
                "temp",
                "tmp",
                "pref",
                "cache",
                "matlab_startup_pref",
            )
        },
        "quarantine_roots": [str(tmp_path / "quarantine")],
        "thread_source": {
            "path": (
                "producer_handoffs/toy_road_p0_repeatability_20260803/"
                "launch_toy_road_family_case.ps1"
            ),
            "source_commit": SOURCE_COMMIT,
            "sha256": LAUNCHER_SHA256,
            "settings": THREAD_SETTINGS,
        },
    }


def _walk_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_walk_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_walk_keys(item) for item in value), set())
    return set()


def test_derives_non_authorizing_lock_with_exact_provenance(tmp_path: Path) -> None:
    source = _source_lock(tmp_path)
    relocation = _relocation(tmp_path, source)

    diagnostic, transformation = PROTOCOL.derive_diagnostic_lock(source, relocation)

    assert diagnostic["schema_version"] == "toy_road_runtime_diagnostic_lock_v1"
    assert diagnostic["authorization_scope"] == "diagnostic_only_non_authorizing"
    assert diagnostic["producer_entrypoint_authorized"] is False
    assert diagnostic["runtime_expectations"]["binary_sha256"] == source[
        "runtime_expectations"
    ]["binary_sha256"]
    assert diagnostic["thread_environment"] == THREAD_SETTINGS
    assert not (FORBIDDEN_KEYS & _walk_keys(diagnostic))
    assert ".consumed" not in json.dumps(diagnostic)
    assert transformation["authorization_artifact_read"] is False
    assert transformation["production_output_root_present"] is False
    assert transformation["thread_setting_source"] == relocation["thread_source"]
    assert transformation["unchanged_fields_sha256_before"] == transformation[
        "unchanged_fields_sha256_after"
    ]
    assert transformation["source_execution_lock_sha256"] == hashlib.sha256(
        PROTOCOL.canonical_json_bytes(source)
    ).hexdigest()
    assert transformation["diagnostic_lock_sha256"] == hashlib.sha256(
        PROTOCOL.canonical_json_bytes(diagnostic)
    ).hexdigest()
    PROTOCOL.validate_diagnostic_lock(source, diagnostic, transformation)


@pytest.mark.parametrize(
    "mutation",
    [
        ("runtime_expectations.matlab.release", "R2024b"),
        ("runtime_expectations.binary_sha256.initial", "f" * 64),
        ("thread_environment.OMP_NUM_THREADS", "2"),
        ("thread_setting_source.sha256", "a" * 64),
        ("source_execution_lock_sha256", "b" * 64),
    ],
)
def test_validator_rejects_identity_or_provenance_mutation(
    tmp_path: Path, mutation: tuple[str, str]
) -> None:
    source = _source_lock(tmp_path)
    diagnostic, transformation = PROTOCOL.derive_diagnostic_lock(
        source, _relocation(tmp_path, source)
    )
    target = transformation if mutation[0].split(".")[0] in transformation else diagnostic
    parts = mutation[0].split(".")
    cursor = target
    for part in parts[:-1]:
        cursor = cursor[part]
    cursor[parts[-1]] = mutation[1]

    with pytest.raises(D1ProtocolError):
        PROTOCOL.validate_diagnostic_lock(source, diagnostic, transformation)


@pytest.mark.parametrize("replacement_index", range(7))
def test_validator_reconstructs_every_declared_lock_replacement(
    tmp_path: Path, replacement_index: int
) -> None:
    source = _source_lock(tmp_path)
    diagnostic, transformation = PROTOCOL.derive_diagnostic_lock(
        source, _relocation(tmp_path, source)
    )
    transformation["replacements"][replacement_index]["field"] += ".forged"

    with pytest.raises(D1ProtocolError, match="replacement|transformation"):
        PROTOCOL.validate_diagnostic_lock(source, diagnostic, transformation)


@pytest.mark.parametrize("forbidden", sorted(FORBIDDEN_KEYS))
def test_validator_rejects_exact_authorization_artifact_keys(
    tmp_path: Path, forbidden: str
) -> None:
    source = _source_lock(tmp_path)
    diagnostic, transformation = PROTOCOL.derive_diagnostic_lock(
        source, _relocation(tmp_path, source)
    )
    diagnostic[forbidden] = "forbidden"

    with pytest.raises(D1ProtocolError, match="authorization|field|forbidden"):
        PROTOCOL.validate_diagnostic_lock(source, diagnostic, transformation)


def test_derivation_rejects_diagnostic_root_in_quarantine(tmp_path: Path) -> None:
    source = _source_lock(tmp_path)
    relocation = _relocation(tmp_path, source)
    relocation["diagnostic_root"] = str(tmp_path / "quarantine" / "new-d1")

    with pytest.raises(D1ProtocolError, match="quarantine"):
        PROTOCOL.derive_diagnostic_lock(source, relocation)


def test_cli_create_new_preserves_existing_bytes(tmp_path: Path) -> None:
    source = _source_lock(tmp_path)
    relocation = _relocation(tmp_path, source)
    source_path = tmp_path / "source.json"
    relocation_path = tmp_path / "relocation.json"
    diagnostic_path = tmp_path / "diagnostic.json"
    transformation_path = tmp_path / "transformation.json"
    source_path.write_bytes(PROTOCOL.canonical_json_bytes(source))
    relocation_path.write_bytes(PROTOCOL.canonical_json_bytes(relocation))
    sentinel = b"do-not-replace"
    diagnostic_path.write_bytes(sentinel)

    with pytest.raises(D1ProtocolError, match="exists"):
        PROTOCOL.derive_diagnostic_lock_files(
            source_path, relocation_path, diagnostic_path, transformation_path
        )

    assert diagnostic_path.read_bytes() == sentinel
    assert not transformation_path.exists()
    assert not list(tmp_path.glob("*.consumed"))


def test_powershell_derivation_wrapper_has_no_authorization_surface(
    tmp_path: Path,
) -> None:
    wrapper = HANDOFF / "new_toy_road_d1_diagnostic_lock.ps1"
    source_text = wrapper.read_text("utf-8")
    for forbidden_parameter in (
        "ExecutionAuthorizationPath",
        "AuthorizationId",
        "ConsumedPath",
        "ProductionOutputRoot",
    ):
        assert forbidden_parameter not in source_text

    source = _source_lock(tmp_path)
    relocation = _relocation(tmp_path, source)
    source_path = tmp_path / "source.json"
    relocation_path = tmp_path / "relocation.json"
    diagnostic_path = tmp_path / "D1_DIAGNOSTIC_LOCK.json"
    transformation_path = tmp_path / "D1_LOCK_TRANSFORMATION.json"
    source_path.write_bytes(PROTOCOL.canonical_json_bytes(source))
    relocation_path.write_bytes(PROTOCOL.canonical_json_bytes(relocation))
    python_sha = hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(wrapper),
        "-SourceExecutionLockPath",
        str(source_path),
        "-RelocationPath",
        str(relocation_path),
        "-DiagnosticLockPath",
        str(diagnostic_path),
        "-TransformationPath",
        str(transformation_path),
        "-PythonExecutable",
        sys.executable,
        "-ApprovedPythonSha256",
        python_sha,
    ]

    first = subprocess.run(command, capture_output=True, text=True, check=False)
    assert first.returncode == 0, first.stdout + first.stderr
    assert diagnostic_path.is_file()
    assert transformation_path.is_file()
    second = subprocess.run(command, capture_output=True, text=True, check=False)
    assert second.returncode != 0
    assert "exists" in (second.stdout + second.stderr).lower()


def test_matlab_probe_is_structurally_diagnostic_only() -> None:
    probe_path = HANDOFF / "run_toy_road_runtime_diagnostic.m"
    probe = probe_path.read_text("utf-8")
    assert probe.startswith("function run_toy_road_runtime_diagnostic(")
    for required in (
        "toy_road_runtime_diagnostic_v1",
        "diagnostic_only_non_authorizing",
        "producer_entrypoint_authorized",
        "first_failed_predicate",
        "diagnostic_internal_error",
        "measured_raw",
        "measured_normalized",
        "which(",
        "'-all'",
        "getReport",
        "java.nio.file.StandardOpenOption.CREATE_NEW",
        ".D1_RUNTIME_DIAGNOSTIC.json.",
        "java.nio.file.StandardCopyOption.ATOMIC_MOVE",
        "producer_invocation_count",
        "fem_cycle_count",
    ):
        assert required in probe
    forbidden_patterns = (
        r"\bmain_toy_road_family_case\b",
        r"\bsolve_toy_road_family_case\b",
        r"\brecover_toy_road_family_state\b",
        r"\bSystem\s*\(",
        r"\bNewton\b",
        r"\beval(?:in)?\s*\(",
        r"\bfeval\s*\(",
        r"\bstr2func\s*\(",
        r"\brun\s*\(",
    )
    for pattern in forbidden_patterns:
        assert not __import__("re").search(pattern, probe, flags=__import__("re").IGNORECASE)


def test_matlab_unit_test_source_cannot_enter_launcher_or_producer() -> None:
    test_path = HANDOFF / "tests" / "toyRoadD1RuntimeDiagnosticTest.m"
    test_source = test_path.read_text("utf-8")
    assert "run_toy_road_runtime_diagnostic" in test_source
    for forbidden in (
        "launch_toy_road_runtime_diagnostic",
        "launch_toy_road_family_case",
        "main_toy_road_family_case",
        "solve_toy_road_family_case",
        "recover_toy_road_family_state",
    ):
        assert forbidden not in test_source
    plan = (
        ROOT
        / "docs"
        / "superpowers"
        / "plans"
        / "2026-08-04-toy-road-d1-runtime-diagnostic.md"
    ).read_text("utf-8")
    assert plan.count("matlab -batch") == 1
    assert "pre_matlab_candidate_commit" in plan


def test_d1_launcher_and_adapter_are_structurally_non_production() -> None:
    launcher = (HANDOFF / "launch_toy_road_runtime_diagnostic.ps1").read_text("utf-8")
    adapter = (HANDOFF / "invoke_toy_road_d1_test_process_adapter.ps1").read_text(
        "utf-8"
    )
    assert "run_toy_road_runtime_diagnostic" in launcher
    assert "D1_EXACT_BATCH_COMMAND.txt" in launcher
    assert "D1_LAUNCHER_RECOVERY.json" in launcher
    assert "D1_SHA256SUMS.txt" in launcher
    assert "automatic_retry_performed=$false" in launcher
    for required in (
        "SourceExecutionLockPath",
        "--validate-lock",
        "New-Item -ItemType HardLink",
        "overlay_source_path",
        "overlay_target_path",
    ):
        assert required in launcher
    for forbidden in (
        "ExecutionAuthorizationPath",
        "AuthorizationId",
        "ProductionOutputRoot",
        "main_toy_road_family_case",
        "solve_toy_road_family_case",
        "recover_toy_road_family_state",
    ):
        assert forbidden not in launcher
    assert "diagnostic_invocation_count=1" in adapter
    assert "producer_invocation_count=0" in adapter
    assert "fem_cycle_count=0" in adapter
    assert "matlab.exe" not in adapter.lower()


def _complete_d1_package(root: Path, diagnostic_status: str = "PASS") -> None:
    lock = {
        "schema_version": "toy_road_runtime_diagnostic_lock_v1",
        "authorization_scope": "diagnostic_only_non_authorizing",
        "producer_entrypoint_authorized": False,
    }
    transformation = {
        "schema_version": "toy_road_runtime_lock_transformation_v1",
        "diagnostic_lock_sha256": hashlib.sha256(
            PROTOCOL.canonical_json_bytes(lock)
        ).hexdigest(),
        "authorization_artifact_read": False,
        "production_output_root_present": False,
    }
    failure_index = 10 if diagnostic_status == "FAIL" else None
    predicates = [
        {
            "ordinal": index + 1,
            "name": name,
            "expected": "expected",
            "measured_raw": "measured",
            "measured_normalized": "measured",
            "pass": failure_index is None or index < failure_index,
            "measured_at_utc": "2026-08-05T10:00:00.000Z",
        }
        for index, name in enumerate(EXPECTED_PREDICATES)
        if failure_index is None or index <= failure_index
    ]
    first_failure = EXPECTED_PREDICATES[failure_index] if failure_index is not None else None
    receipt = {
        "schema_version": "toy_road_runtime_diagnostic_v1",
        "status": diagnostic_status,
        "authorization_scope": "diagnostic_only_non_authorizing",
        "producer_entrypoint_authorized": False,
        "producer_invocation_count": 0,
        "fem_cycle_count": 0,
        "predicates": predicates,
        "completed_predicate_count": len(predicates),
        "first_failed_predicate": first_failure,
        "matlab_exception": {} if diagnostic_status == "PASS" else {
            "identifier": "toyRoadD1:PredicateFailed",
            "message": f"D1 runtime predicate failed: {first_failure}",
            "stack": [],
            "extended_report": "predicate failure",
        },
    }
    batch = "run_toy_road_runtime_diagnostic('D1_DIAGNOSTIC_LOCK.json','D1_RUNTIME_DIAGNOSTIC.json');"
    files: dict[str, bytes] = {
        "D1_DIAGNOSTIC_LOCK.json": PROTOCOL.canonical_json_bytes(lock),
        "D1_LOCK_TRANSFORMATION.json": PROTOCOL.canonical_json_bytes(transformation),
        "D1_EXACT_BATCH_COMMAND.txt": batch.encode("utf-8"),
        "D1_LAUNCH_PROVENANCE.json": PROTOCOL.canonical_json_bytes(
            {
                "schema_version": "toy_road_d1_launch_provenance_v1",
                "authorization_scope": "diagnostic_only_non_authorizing",
                "diagnostic_lock_sha256": hashlib.sha256(
                    PROTOCOL.canonical_json_bytes(lock)
                ).hexdigest(),
                "transformation_sha256": hashlib.sha256(
                    PROTOCOL.canonical_json_bytes(transformation)
                ).hexdigest(),
                "batch_sha256": hashlib.sha256(batch.encode("utf-8")).hexdigest(),
                "authorization_path_present": False,
                "production_output_parameter_present": False,
            }
        ),
        "D1_PROCESS_BEFORE.json": PROTOCOL.canonical_json_bytes(
            {"schema_version": "toy_road_d1_process_inventory_v1", "count": 0, "processes": []}
        ),
        "D1_RUNTIME_DIAGNOSTIC.json": PROTOCOL.canonical_json_bytes(receipt),
        "D1_PROCESS_AFTER.json": PROTOCOL.canonical_json_bytes(
            {"schema_version": "toy_road_d1_process_inventory_v1", "count": 0, "processes": []}
        ),
        "D1_TERMINAL.json": PROTOCOL.canonical_json_bytes(
            {
                "schema_version": "toy_road_d1_terminal_v1",
                "status": "D1_DIAGNOSTIC_EVIDENCE_COMPLETE",
                "diagnostic_result": diagnostic_status,
                "production_authorized": False,
                "authorization_consumed": False,
                "automatic_retry_performed": False,
                "producer_invocation_count": 0,
                "fem_cycle_count": 0,
                "matlab_process_count_before": 0,
                "matlab_process_count_after": 0,
                "production_output_absent": True,
            }
        ),
        "MATLAB_STDOUT_STDERR.txt": b"diagnostic output\n",
    }
    root.mkdir()
    for name, payload in files.items():
        (root / name).write_bytes(payload)
    sums = "".join(
        f"{hashlib.sha256(files[name]).hexdigest()}  {name}\n" for name in sorted(files)
    )
    (root / "D1_SHA256SUMS.txt").write_text(sums, "ascii", newline="")


@pytest.mark.parametrize("status", ["PASS", "FAIL"])
def test_complete_d1_package_validates_without_authorizing_production(
    tmp_path: Path, status: str
) -> None:
    root = tmp_path / "package"
    _complete_d1_package(root, status)

    result = PROTOCOL.validate_d1_package(root)

    assert result == {
        "status": "D1_DIAGNOSTIC_EVIDENCE_ACCEPTED",
        "diagnostic_result": status,
        "production_authorized": False,
    }


def test_complete_d1_package_rejects_hash_tampering(tmp_path: Path) -> None:
    root = tmp_path / "package"
    _complete_d1_package(root)
    (root / "D1_RUNTIME_DIAGNOSTIC.json").write_bytes(b"{}")

    with pytest.raises(D1ProtocolError, match="SHA-256|checksum"):
        PROTOCOL.validate_d1_package(root)


@pytest.mark.parametrize(
    "mutation",
    ["missing", "reordered", "wrong_ordinal", "failure_after_first", "bad_first_failure", "missing_exception"],
)
def test_complete_d1_package_rejects_invalid_predicate_chronology(
    tmp_path: Path, mutation: str
) -> None:
    root = tmp_path / "package"
    _complete_d1_package(root, "FAIL")
    receipt_path = root / "D1_RUNTIME_DIAGNOSTIC.json"
    receipt = json.loads(receipt_path.read_text("utf-8"))
    if mutation == "missing":
        receipt["predicates"].pop(2)
    elif mutation == "reordered":
        receipt["predicates"][0], receipt["predicates"][1] = (
            receipt["predicates"][1], receipt["predicates"][0]
        )
    elif mutation == "wrong_ordinal":
        receipt["predicates"][2]["ordinal"] = 99
    elif mutation == "failure_after_first":
        receipt["predicates"][-2]["pass"] = False
    elif mutation == "bad_first_failure":
        receipt["first_failed_predicate"] = "matlab_release"
    else:
        receipt["matlab_exception"] = {}
    receipt_path.write_bytes(PROTOCOL.canonical_json_bytes(receipt))
    files = {
        path.name: path.read_bytes()
        for path in root.iterdir()
        if path.is_file() and path.name != "D1_SHA256SUMS.txt"
    }
    (root / "D1_SHA256SUMS.txt").write_text(
        "".join(
            f"{hashlib.sha256(files[name]).hexdigest()}  {name}\n"
            for name in sorted(files)
        ),
        "ascii",
        newline="",
    )

    with pytest.raises(D1ProtocolError, match="predicate|exception|chronology|ordinal"):
        PROTOCOL.validate_d1_package(root)


def test_partial_d1_package_is_preserved_but_not_accepted_as_terminal(
    tmp_path: Path,
) -> None:
    root = tmp_path / "partial"
    root.mkdir()
    recovery = {
        "schema_version": "toy_road_d1_launcher_recovery_v1",
        "status": "PARTIAL_FAIL",
        "authorization_scope": "diagnostic_only_non_authorizing",
        "producer_invocation_count": 0,
        "fem_cycle_count": 0,
        "automatic_retry_performed": False,
        "observed_files": [],
    }
    (root / "D1_LAUNCHER_RECOVERY.json").write_bytes(
        PROTOCOL.canonical_json_bytes(recovery)
    )

    result = PROTOCOL.validate_d1_package(root)

    assert result["status"] == "D1_DIAGNOSTIC_EVIDENCE_PARTIAL"
    assert result["production_authorized"] is False


def test_production_protocol_explicitly_rejects_d1_schemas() -> None:
    d1_lock = {
        "schema_version": "toy_road_runtime_diagnostic_lock_v1",
        "authorization_scope": "diagnostic_only_non_authorizing",
    }
    d1_receipt = {
        "schema_version": "toy_road_runtime_diagnostic_v1",
        "authorization_scope": "diagnostic_only_non_authorizing",
    }
    with pytest.raises(PRODUCTION.ProtocolError, match="D1 diagnostic"):
        PRODUCTION.validate_execution_input_lock(d1_lock, "P0_parent")
    with pytest.raises(PRODUCTION.ProtocolError, match="D1 diagnostic"):
        PRODUCTION.validate_runtime_measurement(d1_lock, d1_receipt)
