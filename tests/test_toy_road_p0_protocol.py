from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import os
import copy
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

import h5py
import numpy as np
import pytest
from scipy.io import savemat


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "producer_handoffs"
    / "toy_road_p0_repeatability_20260803"
    / "toy_road_protocol.py"
)
SPEC = importlib.util.spec_from_file_location("toy_road_protocol", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
PROTOCOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROTOCOL)

ProtocolError = PROTOCOL.ProtocolError
compare_repeatability = PROTOCOL.compare_repeatability
relative_l2 = PROTOCOL.relative_l2
append_attempt_record = PROTOCOL.append_attempt_record

PRIMARY_DECISION = (
    ROOT / "docs" / "toy_road_p0_repeatability_20260802" / "decision.md"
)
ATTEMPT_LEDGER = (
    PRIMARY_DECISION.parent / "_pidl_attempt_ledger" / "attempts.jsonl"
)
ATTEMPT_VIEW = PRIMARY_DECISION.parent / "attempt.md"
PREFLIGHT_EVIDENCE = PRIMARY_DECISION.parent / "preflight_evidence.json"
INVENTORY = ROOT / "docs" / "pidl_experiment_inventory.md"
FAMILY_REGISTRY_ID = "toy_road_p0_repeatability_family_20260802"

PROTOCOL_VERSION = "toy-road-p0-repeatability-v2.1"
AUTHORIZATION_SCOPE = "test_only_non_authorizing"
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


def test_family_has_one_primary_asset_and_registry_row() -> None:
    assert PRIMARY_DECISION.is_file()
    decision = PRIMARY_DECISION.read_text(encoding="utf-8")
    assert "BLOCKED_PENDING_EXECUTION_AUTHORIZATION" in decision
    assert "synthetic FEM transfer family" in decision
    assert "not real-road validation" in decision
    assert "P0/P0R" in decision and "producer qualification" in decision
    evidence = json.loads(PREFLIGHT_EVIDENCE.read_text(encoding="utf-8"))
    assert re.fullmatch(r"[0-9a-f]{40}", evidence["sealed_source_commit"])
    assert evidence["authorization_scope"] == "preflight_only_non_authorizing"
    assert evidence["dynamic_chain_status"] == "not_evaluated_no_execution"
    assert evidence["production_execution_authorized"] is False
    assert evidence["fem_cycles_executed"] == 0
    assert len(evidence["receipts"]) == 5

    rows = [
        line
        for line in INVENTORY.read_text(encoding="utf-8").splitlines()
        if FAMILY_REGISTRY_ID in line
    ]
    assert len(rows) == 1
    assert "synthetic" in rows[0].lower()
    assert "decision.md" in rows[0]


def test_family_attempt_ledger_preserves_original_and_tracks_latest_transition() -> None:
    assert ATTEMPT_LEDGER.is_file()
    records = [
        json.loads(line)
        for line in ATTEMPT_LEDGER.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) in (1, 2)
    original = records[0]
    assert original["attempt_id"] == "toy-road-p0-family-producer-implementation-20260803"
    assert original["role"] == "producer_qualification_and_future_synthetic_family"
    assert original["end_state"] == "blocked_pending_sealed_preflight"
    assert original["next_action"].startswith("Complete Tasks 7 and 8")
    record = records[-1]
    assert re.fullmatch(r"[0-9a-f]{40}", record["source_commit"])
    for field in (
        "family_contract_sha256",
        "case_physics_contract_sha256",
        "execution_input_lock_sha256",
        "runtime_lock_sha256",
        "environment_fingerprint_sha256",
    ):
        assert re.fullmatch(r"[0-9a-f]{64}", record[field])
    if len(records) == 2:
        assert record["attempt_id"] == "toy-road-p0-independent-review-transition-20260804"
        assert record["start_state"] == "blocked_pending_execution_authorization"
        assert record["end_state"] == "blocked_pending_p0_authorization_review"
        assert "Tasks 7 and 8" not in record["next_action"]
    else:
        assert record is original
    assert record["immutable_receipt_links"]
    assert ATTEMPT_VIEW.is_file()
    assert record["attempt_id"] in ATTEMPT_VIEW.read_text(encoding="utf-8")


def test_launcher_hash_gates_python_before_protocol_and_rechecks_source_before_matlab() -> None:
    launcher = (
        MODULE_PATH.parent / "launch_toy_road_family_case.ps1"
    ).read_text(encoding="utf-8")
    approved_python_sha256 = (
        "15b41a488c356c0e331facdea6c836a6cec021f12d5fde9844e7ca4a1aa0361a"
    )
    assert f"$ApprovedPythonSha256 = '{approved_python_sha256}'" in launcher
    assert "function Assert-ApprovedPythonIdentity" in launcher
    assert launcher.index("Assert-ApprovedPythonIdentity") < launcher.index(
        "$ContractSummary = Get-ContractSummary"
    )
    assert "function Assert-FinalSourceIdentity" in launcher
    final_check = launcher.rindex("Assert-FinalSourceIdentity")
    matlab_call = launcher.rindex("& $MatlabExecutable -batch $batch")
    assert final_check < matlab_call
    final_identity = launcher[
        launcher.index("function Assert-FinalSourceIdentity") :
        launcher.index("function Get-LiveExperimentInventory")
    ]
    assert "Get-CleanGitState" in final_identity
    assert "Get-SourceSealReceipt" in final_identity


def test_post_seal_p0_wrapper_generator_is_commit_fixed_and_fail_closed() -> None:
    generator = MODULE_PATH.parent / "new_toy_road_p0_one_shot_wrapper.ps1"
    assert generator.is_file()
    source = generator.read_text(encoding="utf-8")
    assert "P0_parent" in source
    assert "ExpectedSourceCommit" in source
    assert "P0_PARENT_EXECUTION_AUTHORIZED" in source
    assert "preflight_only_non_authorizing" in source
    assert "CreateNew" in source
    assert "consumed" in source.lower()
    assert "dedicated_producer_attested" in source
    assert "no_manual_or_agent_matlab_fem" in source
    launcher = (
        MODULE_PATH.parent / "launch_toy_road_family_case.ps1"
    ).read_text(encoding="utf-8")
    assert "TOY_ROAD_P0_ONE_SHOT_AUTHORIZATION_ID" in launcher
    assert "TOY_ROAD_DEDICATED_PRODUCER_ATTESTED" in launcher
    policy = json.loads(
        (MODULE_PATH.parent / "DEDICATED_PRODUCER_POLICY.json").read_text(
            encoding="utf-8"
        )
    )
    assert policy["case_id"] == "P0_parent"
    assert policy["machine_name"] == "CITPC12"
    assert policy["preflight_authorizes_execution"] is False


def test_attempt_ledger_append_preserves_existing_bytes_and_rejects_duplicate(
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "attempts.jsonl"
    append_attempt_record(ledger, {"attempt_id": "first", "status": "open"})
    original = ledger.read_bytes()
    append_attempt_record(ledger, {"attempt_id": "second", "status": "open"})
    assert ledger.read_bytes().startswith(original)
    with pytest.raises(ProtocolError, match="attempt_id already exists"):
        append_attempt_record(ledger, {"attempt_id": "first", "status": "open"})


def test_attempt_ledger_validate_and_render_do_not_rewrite_jsonl(
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "attempts.jsonl"
    record = json.loads(ATTEMPT_LEDGER.read_text(encoding="utf-8"))
    original = (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")
    ledger.write_bytes(original)
    script = ROOT / "docs/skills/pidl-experiment-gate/scripts/pidl_attempt_ledger.py"
    subprocess.run(
        ["py", "-3", str(script), "validate", "--ledger", str(ledger)],
        check=True,
    )
    subprocess.run(
        [
            "py", "-3", str(script), "render", "--ledger", str(ledger),
            "--attempt-id", record["attempt_id"], "--out", str(tmp_path / "attempt.md"),
        ],
        check=True,
    )
    assert ledger.read_bytes() == original


def test_contract_digest_layers_are_correct() -> None:
    contracts = PROTOCOL.load_contracts()
    assert set(contracts) == {
        "P0_parent",
        "P0R_parent_repeat",
        "T1_initial_defect",
        "T2_material_state",
        "T3_loading_history",
    }
    assert len({case.family_sha256 for case in contracts.values()}) == 1
    assert (
        contracts["P0_parent"].case_sha256
        == contracts["P0R_parent_repeat"].case_sha256
    )
    assert (
        contracts["T1_initial_defect"].case_sha256
        != contracts["P0_parent"].case_sha256
    )
    assert contracts["T1_initial_defect"].changed_axes == ["mesh.node_coords"]
    assert contracts["T2_material_state"].changed_axes == ["material.Gc"]
    assert contracts["T3_loading_history"].changed_axes == ["loading.blocks"]
    assert {
        case.physics["mesh"]["connectivity_sha256"] for case in contracts.values()
    } == {"a751fe5bfdbbfdd08ccddc6880bae1852d31260560583725e678ebc24a85ceb8"}
    assert len({case.execution_sha256 for case in contracts.values()}) == 1
    assert next(iter(contracts.values())).execution_sha256 == "not_applicable"


def test_contract_files_bind_runtime_and_historical_closure() -> None:
    family = json.loads((MODULE_PATH.parent / "FAMILY_CONTRACT.json").read_text("utf-8"))
    closure = json.loads(
        (MODULE_PATH.parent / "HISTORICAL_Q2_CLOSURE.json").read_text("utf-8")
    )
    contracts = PROTOCOL.load_contracts()
    expected_family = PROTOCOL.canonical_json_sha256(family)
    assert {case.family_sha256 for case in contracts.values()} == {expected_family}
    runtime = family["runtime_identity"]
    assert runtime["griphfith_source_commit"] == (
        "355d4c83fefc2db88c32031a2dd2623b3de85c89"
    )
    assert runtime["initial_mexw64_sha256"] == (
        "ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db"
    )
    assert runtime["h5py_version"] == "3.16.0"
    assert runtime["java_hard_link_required"] is True
    assert runtime["mesh_sha256_semantics"] == (
        "sha256_matlab_column_major_float64_coords_then_int64_connectivity_v1"
    )
    assert set(runtime["binary_sha256"]) == {
        "initial",
        "AMOR",
        "AT1_HISTORY_FATIGUE",
        "cholmod2",
    }
    assert closure["verdict"] == "historical_q2_parent_irrecoverable"
    assert closure["active_field_backward_equivalence_claimed"] is False


def test_source_manifest_binds_executed_launcher_protocol_and_producer_bytes(
    tmp_path: Path,
) -> None:
    receipt = PROTOCOL.verify_source_manifest(MODULE_PATH.parent)
    required = {
        "CASE_PHYSICS_CONTRACTS.json",
        "FAMILY_CONTRACT.json",
        "HISTORICAL_Q2_CLOSURE.json",
        "launch_toy_road_family_case.ps1",
        "main_toy_road_family_case.m",
        "toy_road_protocol.py",
        "validate_toy_road_terminal_package.m",
        "private/run_toy_road_driver_core.m",
    }
    assert required.issubset(receipt["files"])
    copied = tmp_path / "producer_handoffs" / MODULE_PATH.parent.name
    shutil.copytree(MODULE_PATH.parent, copied)
    target = copied / "main_toy_road_family_case.m"
    target.write_bytes(target.read_bytes() + b"\n% forged\n")
    with pytest.raises(ProtocolError, match="source manifest|hash|bytes"):
        PROTOCOL.verify_source_manifest(copied)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("family_digest", "family"),
        ("p0r_physics", "P0/P0R"),
        ("t1_second_axis", "single-axis|T1"),
        ("t2_second_axis", "single-axis|T2"),
        ("t3_second_axis", "single-axis|T3"),
        ("t1_connectivity", "single-axis|T1"),
        ("t1_element_ordering", "single-axis|T1"),
        ("t1_gp_ordering", "single-axis|T1"),
        ("t1_hash_semantics", "single-axis|T1"),
        ("t1_mesh_metadata", "single-axis|T1"),
        ("t1_transform_metadata", "single-axis|T1"),
    ],
)
def test_contract_mutations_fail_closed(mutation: str, message: str) -> None:
    family = json.loads((MODULE_PATH.parent / "FAMILY_CONTRACT.json").read_text("utf-8"))
    cases = json.loads(
        (MODULE_PATH.parent / "CASE_PHYSICS_CONTRACTS.json").read_text("utf-8")
    )
    family = copy.deepcopy(family)
    cases = copy.deepcopy(cases)
    if mutation == "family_digest":
        cases["family_contract_sha256"] = "0" * 64
    elif mutation == "p0r_physics":
        cases["cases"]["P0R_parent_repeat"]["physics"]["material"]["Gc"] = 0.009
    elif mutation == "t1_second_axis":
        cases["cases"]["T1_initial_defect"]["physics"]["material"]["Gc"] = 0.009
    elif mutation == "t2_second_axis":
        cases["cases"]["T2_material_state"]["physics"]["loading"]["R"] = 0.1
    elif mutation == "t3_second_axis":
        cases["cases"]["T3_loading_history"]["physics"]["material"]["Gc"] = 0.009
    elif mutation == "t1_connectivity":
        cases["cases"]["T1_initial_defect"]["physics"]["mesh"][
            "connectivity_sha256"
        ] = "0" * 64
    elif mutation == "t1_element_ordering":
        cases["cases"]["T1_initial_defect"]["physics"]["mesh"][
            "element_ordering_id"
        ] = "forged_order"
    elif mutation == "t1_gp_ordering":
        cases["cases"]["T1_initial_defect"]["physics"]["mesh"][
            "gp_ordering_id"
        ] = "forged_gp_order"
    elif mutation == "t1_hash_semantics":
        cases["cases"]["T1_initial_defect"]["physics"]["mesh"][
            "mesh_sha256_semantics"
        ] = "forged_hash_semantics"
    elif mutation == "t1_mesh_metadata":
        cases["cases"]["T1_initial_defect"]["physics"]["mesh"][
            "undeclared_metadata"
        ] = "forged"
    elif mutation == "t1_transform_metadata":
        cases["cases"]["T1_initial_defect"]["physics"]["mesh"][
            "node_transform"
        ]["undeclared_metadata"] = "forged"
    if mutation.startswith("t1_") and mutation != "t1_second_axis":
        entry = cases["cases"]["T1_initial_defect"]
        entry["case_physics_contract_sha256"] = PROTOCOL.canonical_json_sha256(
            {
                "family_contract_sha256": cases["family_contract_sha256"],
                "physics": entry["physics"],
            }
        )
    with pytest.raises(ProtocolError, match=message):
        PROTOCOL.validate_contract_documents(family, cases)


def test_execution_input_lock_is_launch_local_and_self_consistent(tmp_path: Path) -> None:
    contracts = PROTOCOL.load_contracts()
    roots = {
        name: str(tmp_path / name)
        for name in (
            "output",
            "work",
            "temp",
            "tmp",
            "pref",
            "cache",
            "matlab_startup_pref",
        )
    }
    lock = PROTOCOL.build_execution_input_lock(
        authorization_scope="production_authorized",
        role="P0_parent",
        family_contract_sha256=contracts["P0_parent"].family_sha256,
        case_physics_contract_sha256=contracts["P0_parent"].case_sha256,
        source_commit="a" * 40,
        runtime_lock_sha256="b" * 64,
        source_manifest_sha256="c" * 64,
        runtime_expectations=canonical_runtime_expectations(tmp_path),
        roots=roots,
        launch_timestamp_utc="2026-08-03T12:00:00.0000000Z",
        no_clobber_receipt_id="fixture-no-clobber-1",
    )
    assert lock["authorization_scope"] == "production_authorized"
    assert lock["case_id"] == "P0_parent"
    assert lock["source_manifest_sha256"] == "c" * 64
    assert lock["runtime_expectations"]["matlab"]["update"] == "Update 5"
    assert lock["writable_roots"] == roots
    assert "execution_input_lock_sha256" not in lock
    digest = hashlib.sha256(PROTOCOL.canonical_json_bytes(lock)).hexdigest()
    assert digest not in {
        contracts["P0_parent"].family_sha256,
        contracts["P0_parent"].case_sha256,
    }


def test_canonical_json_golden_vector_uses_ascii_escapes_and_exact_shape() -> None:
    value = {
        "authorization_scope": "test_only_non_authorizing",
        "enabled": True,
        "escaped": "line\nquote\"slash\\",
        "roots": {
            "cache": "C:/tmp/cache",
            "matlab_startup_pref": "C:/tmp/startup",
            "output": "C:/tmp/\u8f93\u51fa",
            "pref": "C:/tmp/pref",
            "temp": "C:/tmp/temp",
            "tmp": "C:/tmp/tmp",
            "work": "C:/tmp/work",
        },
    }
    expected = (
        b'{"authorization_scope":"test_only_non_authorizing","enabled":true,'
        b'"escaped":"line\\nquote\\\"slash\\\\","roots":{"cache":"C:/tmp/cache",'
        b'"matlab_startup_pref":"C:/tmp/startup","output":"C:/tmp/\\u8f93\\u51fa",'
        b'"pref":"C:/tmp/pref","temp":"C:/tmp/temp","tmp":"C:/tmp/tmp",'
        b'"work":"C:/tmp/work"}}'
    )
    assert PROTOCOL.canonical_json_bytes(value) == expected
    assert PROTOCOL.canonical_json_sha256(value) == hashlib.sha256(expected).hexdigest()


def test_execution_lock_cli_publishes_python_canonical_bytes_create_new(
    tmp_path: Path,
) -> None:
    contracts = PROTOCOL.load_contracts()
    request = {
        "authorization_scope": "test_only_non_authorizing",
        "role": "P0_parent",
        "family_contract_sha256": contracts["P0_parent"].family_sha256,
        "case_physics_contract_sha256": contracts["P0_parent"].case_sha256,
        "source_commit": "a" * 40,
        "runtime_lock_sha256": "b" * 64,
        "source_manifest_sha256": "c" * 64,
        "runtime_expectations": canonical_runtime_expectations(tmp_path),
        "roots": {
            name: str(tmp_path / name)
            for name in (
                "output",
                "work",
                "temp",
                "tmp",
                "pref",
                "cache",
                "matlab_startup_pref",
            )
        },
        "launch_timestamp_utc": "2026-08-03T12:00:00.0000000Z",
        "no_clobber_receipt_id": "fixture-\u8f93\u51fa",
    }
    request_path = tmp_path / "request.json"
    output_path = tmp_path / "EXECUTION_INPUT_LOCK.json"
    request_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
    command = [
        os.fspath(Path(os.sys.executable)),
        os.fspath(MODULE_PATH),
        "--emit-execution-lock",
        os.fspath(request_path),
        os.fspath(output_path),
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    receipt = json.loads(completed.stdout)
    expected = PROTOCOL.build_execution_input_lock(**request)
    expected_bytes = PROTOCOL.canonical_json_bytes(expected)
    assert output_path.read_bytes() == expected_bytes
    assert receipt == {
        "execution_input_lock_sha256": hashlib.sha256(expected_bytes).hexdigest()
    }
    repeated = subprocess.run(command, check=False, capture_output=True, text=True)
    assert repeated.returncode != 0
    assert output_path.read_bytes() == expected_bytes


def test_execution_lock_schema_is_exact_across_python_and_matlab(tmp_path: Path) -> None:
    contracts = PROTOCOL.load_contracts()
    roots = {
        name: str(tmp_path / name)
        for name in (
            "output",
            "work",
            "temp",
            "tmp",
            "pref",
            "cache",
            "matlab_startup_pref",
        )
    }
    lock = PROTOCOL.build_execution_input_lock(
        authorization_scope="production_authorized",
        role="P0_parent",
        family_contract_sha256=contracts["P0_parent"].family_sha256,
        case_physics_contract_sha256=contracts["P0_parent"].case_sha256,
        source_commit="a" * 40,
        runtime_lock_sha256="b" * 64,
        source_manifest_sha256="c" * 64,
        runtime_expectations=canonical_runtime_expectations(tmp_path),
        roots=roots,
        launch_timestamp_utc="2026-08-03T12:00:00.0000000Z",
        no_clobber_receipt_id="cross-component",
    )
    PROTOCOL.validate_execution_input_lock(lock, "P0_parent")
    assert set(lock) == PROTOCOL.EXECUTION_INPUT_LOCK_FIELDS
    malformed = dict(lock)
    malformed.pop("authorization_scope")
    with pytest.raises(ProtocolError, match="execution lock|schema|missing"):
        PROTOCOL.validate_execution_input_lock(malformed, "P0_parent")
    malformed_runtime = copy.deepcopy(lock)
    del malformed_runtime["runtime_expectations"]["matlab"]["blas"]
    with pytest.raises(ProtocolError, match="runtime|MATLAB|schema"):
        PROTOCOL.validate_execution_input_lock(malformed_runtime, "P0_parent")

    matlab = (MODULE_PATH.parent / "validate_toy_road_terminal_package.m").read_text(
        "utf-8"
    )
    assert "protocolVersion = 'toy-road-p0-repeatability-v2.1';" in matlab
    match = re.search(
        r"executionLockFields\s*=\s*\{(?P<body>.*?)\};", matlab, re.DOTALL
    )
    assert match is not None
    matlab_fields = set(re.findall(r"'([^']+)'", match.group("body")))
    assert matlab_fields == PROTOCOL.EXECUTION_INPUT_LOCK_FIELDS


@pytest.mark.parametrize(
    "mutation",
    [
        "release",
        "update",
        "version",
        "computer",
        "executable_sha256",
        "blas",
        "lapack",
        "absolute_path_order",
        "initial",
        "AMOR",
        "AT1_HISTORY_FATIGUE",
        "cholmod2",
        "lock_digest",
    ],
)
def test_runtime_measurement_is_not_self_compared(
    tmp_path: Path, mutation: str
) -> None:
    lock = _fixture_execution_lock(tmp_path)
    measurement = {
        "schema_version": "toy_road_runtime_measurement_v1",
        "protocol_version": PROTOCOL_VERSION,
        "authorization_scope": "test_only_non_authorizing",
        "status": "PASS",
        "producer_entrypoint_authorized": False,
        "execution_input_lock_sha256": hashlib.sha256(
            PROTOCOL.canonical_json_bytes(lock)
        ).hexdigest(),
        "matlab": copy.deepcopy(lock["runtime_expectations"]["matlab"]),
        "binary_sha256": copy.deepcopy(
            lock["runtime_expectations"]["binary_sha256"]
        ),
    }
    if mutation in measurement["matlab"]:
        if mutation == "absolute_path_order":
            measurement["matlab"][mutation][0], measurement["matlab"][mutation][1] = (
                measurement["matlab"][mutation][1],
                measurement["matlab"][mutation][0],
            )
        elif mutation == "executable_sha256":
            measurement["matlab"][mutation] = "0" * 64
        else:
            measurement["matlab"][mutation] = "mutated"
    elif mutation in measurement["binary_sha256"]:
        measurement["binary_sha256"][mutation] = "0" * 64
    else:
        measurement["execution_input_lock_sha256"] = "0" * 64
    with pytest.raises(ProtocolError, match="runtime|measurement|identity|lock"):
        PROTOCOL.validate_runtime_measurement(lock, measurement)


def test_runtime_measurement_accepts_exact_external_fixture(tmp_path: Path) -> None:
    lock = _fixture_execution_lock(tmp_path)
    measurement = PROTOCOL.build_test_runtime_measurement(lock)
    PROTOCOL.validate_runtime_measurement(lock, measurement)


def test_sealed_process_adapter_and_runtime_bridge_are_structurally_safe() -> None:
    adapter_path = MODULE_PATH.parent / "invoke_toy_road_test_process_adapter.ps1"
    bridge_path = MODULE_PATH.parent / "run_toy_road_runtime_bridge.m"
    launcher_path = MODULE_PATH.parent / "launch_toy_road_family_case.ps1"
    assert adapter_path.is_file()
    assert bridge_path.is_file()
    adapter = adapter_path.read_text("utf-8")
    assert "TestAdapterMeasurementPath" not in adapter
    assert not re.search(r"(?im)^\s*(Start-Process|Invoke-Expression|&\s*\$)", adapter)
    assert not re.search(r"(?i)matlab\.exe(?![A-Za-z0-9_])", adapter)
    assert "invocation_count = 1" in adapter
    bridge = bridge_path.read_text("utf-8")
    for required in (
        "matlabRelease",
        "version('-blas')",
        "version('-lapack')",
        "absolute_path_order",
        "fileSha256",
        "function digest = fileSha256(path)",
        "localReleaseUpdate",
        "main_toy_road_family_case",
    ):
        assert required in bridge
    launcher = launcher_path.read_text("utf-8")
    assert "run_toy_road_runtime_bridge" in launcher
    assert "'-begin'" in launcher
    assert "[Threading.Mutex]" in launcher
    assert ".java-source.java" not in launcher
    assert "java.nio.file.Files.createLink" in launcher
    assert "& $MatlabExecutable -batch $javaBatch" in launcher
    assert "$Value -is [Collections.IDictionary]" in launcher
    assert "$Value.Contains($Name)" in launcher
    assert "$commitLines = @(Invoke-Git $Root @('rev-parse','HEAD'))" in launcher
    assert "([string]$commitLines[0]).Trim().ToLowerInvariant()" in launcher
    assert "dec2hex" not in bridge
    assert "hexDigits" in bridge
    attributes = (MODULE_PATH.parent / ".gitattributes").read_text("ascii")
    for pattern in ("*.json", "*.m", "*.ps1", "*.py"):
        assert f"{pattern} text eol=lf" in attributes


def test_exposes_exact_h5py_runtime_dependency_identity() -> None:
    assert PROTOCOL.RUNTIME_DEPENDENCY_IDENTITY == {"h5py": "3.16.0"}
    assert PROTOCOL.runtime_dependency_identity() == {"h5py": "3.16.0"}


@pytest.mark.parametrize("installed_version", [None, "3.15.1", "3.16.1"])
def test_import_fails_closed_on_missing_or_wrong_h5py_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    installed_version: str | None,
) -> None:
    def reported_version(distribution: str) -> str:
        assert distribution == "h5py"
        if installed_version is None:
            raise importlib.metadata.PackageNotFoundError(distribution)
        return installed_version

    monkeypatch.setattr(importlib.metadata, "version", reported_version)
    spec = importlib.util.spec_from_file_location(
        f"toy_road_protocol_dependency_{installed_version}", MODULE_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    with pytest.raises(RuntimeError, match=r"h5py.*3\.16\.0"):
        spec.loader.exec_module(module)


def test_relative_l2_vectorizes_nd_fields() -> None:
    reference = np.arange(24, dtype=np.float64).reshape((2, 3, 4), order="F")
    candidate = reference.copy()
    candidate[1, 2, 3] += 5e-13 * max(
        np.linalg.norm(reference.reshape(-1, order="F")), 1e-30
    )
    assert relative_l2(candidate, reference) <= 1e-12


def test_relative_l2_vectorizes_matrix_fields() -> None:
    reference = np.array([[1.0, 2.0], [3.0, 4.0]])
    candidate = reference.copy()
    candidate[0, 1] += 1e-13
    expected = np.linalg.norm(
        candidate.reshape(-1, order="F") - reference.reshape(-1, order="F")
    ) / np.linalg.norm(reference.reshape(-1, order="F"))
    assert relative_l2(candidate, reference) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("relative", "maximum", "accepted"),
    [
        (np.nextafter(1e-12, 0.0), np.nextafter(1e-12, 0.0), True),
        (1e-12, 1e-12, True),
        (np.nextafter(1e-12, np.inf), 1e-12, False),
        (1e-12, np.nextafter(1e-12, np.inf), False),
    ],
)
def test_both_thresholds_accept_below_and_at_and_reject_above(
    relative: float, maximum: float, accepted: bool
) -> None:
    if accepted:
        PROTOCOL._require_metric_within_threshold(relative, maximum, False)
    else:
        with pytest.raises(ProtocolError, match="threshold"):
            PROTOCOL._require_metric_within_threshold(relative, maximum, False)


def test_exact_zero_reference_reports_not_applicable_but_keeps_absolute_gate() -> None:
    metric = PROTOCOL._compute_field_metric(
        np.full((2, 3), 5e-13), np.zeros((2, 3))
    )
    assert metric["relative_l2"] == "not_applicable_zero_reference"
    assert metric["max_absolute"] == 5e-13
    PROTOCOL._require_metric_within_threshold(0.0, metric["max_absolute"], True)
    with pytest.raises(ProtocolError, match="threshold"):
        PROTOCOL._require_metric_within_threshold(0.0, 2e-12, True)


def test_tiny_nonzero_reference_is_not_misclassified_after_norm_underflow() -> None:
    reference = np.full((2, 2), 1e-300)
    candidate = np.full((2, 2), 1e-13)
    metric = PROTOCOL._compute_field_metric(candidate, reference)
    assert metric["relative_l2"] != "not_applicable_zero_reference"
    assert metric["relative_l2"] > 1e-12
    with pytest.raises(ProtocolError, match="threshold"):
        PROTOCOL._require_metric_within_threshold(
            metric["relative_l2"], metric["max_absolute"], False
        )


def test_repeatability_accepts_legacy_packages_and_complete_c5_evidence(
    tmp_path: Path,
) -> None:
    p0, p0r = make_repeatability_packages(tmp_path)
    evidence = compare_repeatability(p0, p0r)
    lock = json.loads(
        (tmp_path / "P0_REPEATABILITY_EVIDENCE_LOCK.json").read_text("utf-8")
    )
    assert evidence == lock
    assert evidence["status"] == "PASS"
    assert evidence["authorization_scope"] == AUTHORIZATION_SCOPE
    assert evidence["family_contract_sha256"] == "3" * 64
    assert evidence["p0_execution_input_lock_sha256"] != evidence[
        "p0r_execution_input_lock_sha256"
    ]
    assert len(evidence["field_metrics"]) == 5 * len(TRAJECTORY_FIELDS)
    assert all(len(evidence[name]) == 64 for name in (
        "p0_manifest_sha256",
        "p0r_manifest_sha256",
        "p0_c5_receipt_sha256",
        "p0r_c5_receipt_sha256",
        "p0_package_snapshot_sha256",
        "p0r_package_snapshot_sha256",
    ))
    assert evidence["schema_version"] == "toy_road_repeatability_evidence_v1"


def test_terminal_evidence_authentication_binds_validated_package_snapshot(
    tmp_path: Path,
) -> None:
    p0, _ = make_repeatability_packages(tmp_path)
    receipt = PROTOCOL.authenticate_terminal_package(p0, "P0_parent")
    assert receipt["schema_version"] == "toy_road_authenticated_terminal_v1"
    assert receipt["status"] == "PASS"
    assert receipt["case_id"] == "P0_parent"
    assert len(receipt["package_snapshot_sha256"]) == 64
    assert receipt["manifest_sha256"] == _sha256(p0 / "TERMINAL_MANIFEST.json")
    assert receipt["c5_receipt_sha256"] == _sha256(
        p0 / "qualification" / "C5_NUMERICAL_GATE_RECEIPT.json"
    )
    PROTOCOL.recheck_authenticated_package(receipt)

    with (p0 / "TERMINAL_RESULT.json").open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(ProtocolError, match="identity|snapshot|changed|hash"):
        PROTOCOL.recheck_authenticated_package(receipt)


def test_handwritten_terminal_pass_json_cannot_authenticate(tmp_path: Path) -> None:
    package = tmp_path / "handwritten"
    (package / "qualification").mkdir(parents=True)
    _write_json_no_clobber(
        package / "TERMINAL_MANIFEST.json",
        {"authorization_scope": AUTHORIZATION_SCOPE, "case_id": "P0_parent"},
    )
    _write_json_no_clobber(
        package / "qualification" / "C5_NUMERICAL_GATE_RECEIPT.json",
        {"status": "PASS", "passed": True},
    )
    with pytest.raises(ProtocolError, match="schema|missing|manifest"):
        PROTOCOL.authenticate_terminal_package(package, "P0_parent")


def test_repeatability_evidence_authentication_is_bound_to_p0_p0r_bytes(
    tmp_path: Path,
) -> None:
    p0, p0r = make_repeatability_packages(tmp_path)
    compare_repeatability(p0, p0r)
    evidence_path = tmp_path / "P0_REPEATABILITY_EVIDENCE_LOCK.json"
    receipt = PROTOCOL.authenticate_repeatability_evidence(evidence_path, p0, p0r)
    assert receipt["schema_version"] == "toy_road_authenticated_repeatability_v1"
    assert receipt["status"] == "PASS"
    assert receipt["family_contract_sha256"] == "3" * 64
    assert receipt["repeatability_evidence_sha256"] == _sha256(evidence_path)
    evidence_value = json.loads(evidence_path.read_text("utf-8"))
    for name in (
        "runtime_lock_sha256",
        "p0_manifest_sha256",
        "p0r_manifest_sha256",
        "p0_c5_receipt_sha256",
        "p0r_c5_receipt_sha256",
        "p0_package_snapshot_sha256",
        "p0r_package_snapshot_sha256",
    ):
        assert receipt[name] == evidence_value[name]
    PROTOCOL.recheck_authenticated_repeatability(receipt)

    value = json.loads(evidence_path.read_text("utf-8"))
    value["p0_manifest_sha256"] = "f" * 64
    _replace_json(evidence_path, value)
    with pytest.raises(ProtocolError, match="repeatability|snapshot|changed|hash"):
        PROTOCOL.recheck_authenticated_repeatability(receipt)


def test_authentication_cli_publishes_immutable_receipt_and_rechecks(
    tmp_path: Path,
) -> None:
    p0, _ = make_repeatability_packages(tmp_path)
    receipt_path = tmp_path / "P0_AUTHENTICATED.json"
    command = [
        os.fspath(Path(os.sys.executable)),
        os.fspath(MODULE_PATH),
        "--authenticate-terminal",
        os.fspath(p0),
        "P0_parent",
        os.fspath(receipt_path),
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    assert json.loads(completed.stdout) == {
        "authentication_receipt_sha256": _sha256(receipt_path)
    }
    recheck = subprocess.run(
        [
            os.fspath(Path(os.sys.executable)),
            os.fspath(MODULE_PATH),
            "--recheck-authentication",
            os.fspath(receipt_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(recheck.stdout) == {"status": "PASS"}
    repeated = subprocess.run(command, check=False, capture_output=True, text=True)
    assert repeated.returncode != 0


def test_repeatability_evidence_symlink_cannot_authenticate(tmp_path: Path) -> None:
    p0, p0r = make_repeatability_packages(tmp_path)
    compare_repeatability(p0, p0r)
    evidence = tmp_path / "P0_REPEATABILITY_EVIDENCE_LOCK.json"
    alias = tmp_path / "repeatability-alias.json"
    try:
        os.symlink(evidence, alias)
    except (OSError, NotImplementedError) as exception:
        pytest.skip(f"file symlink creation unavailable: {exception}")
    with pytest.raises(ProtocolError, match="link|reparse"):
        PROTOCOL.authenticate_repeatability_evidence(alias, p0, p0r)


def test_real_matlab_v73_and_legacy_packages_reach_complete_comparison(
    tmp_path: Path,
) -> None:
    if shutil.which("matlab") is None:
        pytest.skip("MATLAB is required for the real -v7.3 integration fixture")
    p0, p0r = make_repeatability_packages(tmp_path, p0_mat_format="v7.3")
    shard = PROTOCOL.read_mat_struct(p0 / "substeps" / "cycle_0002.mat", "shard")
    assert shard["d_gp"].shape == (2, 4, 5)
    assert shard["d_gp"].dtype == np.float64
    assert np.asarray(shard["branch"], dtype=object).reshape(-1).tolist() == [
        "loading",
        "loading",
        "loading",
        "loading",
        "unloading",
    ]
    assert shard["state_semantics_id"] == "five_substep_post_commit_history_v1"
    assert compare_repeatability(p0, p0r)["status"] == "PASS"


def test_mat_reader_normalizes_big_endian_real_double(tmp_path: Path) -> None:
    path = tmp_path / "big-endian.mat"
    with h5py.File(path, "w") as handle:
        payload = handle.create_group("payload")
        payload.attrs["MATLAB_class"] = np.bytes_("struct")
        value = payload.create_dataset("value", data=np.array([[1.25]], dtype=">f8"))
        value.attrs["MATLAB_class"] = np.bytes_("double")
    value = PROTOCOL.read_mat_struct(path, "payload")["value"]
    normalized = PROTOCOL._require_double_array(value, "big-endian fixture")
    assert normalized.dtype == np.dtype(np.float64)
    assert normalized.item() == 1.25


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("source_commit", "b" * 40, "source"),
        ("runtime_lock_sha256", "7" * 64, "runtime"),
        ("family_contract_sha256", "8" * 64, "family"),
        ("case_physics_contract_sha256", "9" * 64, "case"),
        ("physical_input_sha256", "a" * 64, "physical"),
        ("solver_sha256", "b" * 64, "solver"),
        ("recovery_sha256", "c" * 64, "recovery"),
        ("exporter_sha256", "d" * 64, "exporter"),
        ("numerical_gate_contract_sha256", "e" * 64, "numerical"),
        ("event_contract_sha256", "f" * 64, "event"),
    ],
)
def test_repeatability_rejects_exact_identity_mismatch_before_numerics(
    tmp_path: Path, field: str, replacement: str, message: str
) -> None:
    p0, p0r = make_repeatability_packages(
        tmp_path,
        p0r_identity_overrides={field: replacement},
        p0r_raw_offset=2e-12,
    )
    assert_failure_without_evidence(tmp_path, p0, p0r, message)


def test_repeatability_rejects_two_internally_valid_different_events(
    tmp_path: Path,
) -> None:
    p0, p0r = make_repeatability_packages(tmp_path, p0r_terminal_cycle=6)
    PROTOCOL._validate_package(p0.resolve(), "P0", "P0_parent")
    PROTOCOL._validate_package(p0r.resolve(), "P0R", "P0R_parent_repeat")
    assert_failure_without_evidence(tmp_path, p0, p0r, "event|terminal")


@pytest.mark.parametrize(
    ("first_hit_cycle", "timing"),
    [(3, "early"), (1, "late")],
)
def test_repeatability_rejects_non_three_cycle_confirmation(
    tmp_path: Path, first_hit_cycle: int, timing: str
) -> None:
    p0, _ = make_repeatability_packages(
        tmp_path, p0_first_hit_cycle=first_hit_cycle
    )
    with pytest.raises(ProtocolError, match=f"confirmation|three|event|{timing}"):
        PROTOCOL._validate_package(p0.resolve(), "P0", "P0_parent")
    assert not (tmp_path / "P0_REPEATABILITY_EVIDENCE_LOCK.json").exists()


@pytest.mark.parametrize(
    "role_overrides",
    [
        {"p0": "P0R_parent_repeat"},
        {"p0r": "P0_parent"},
        {"p0": 7},
    ],
)
def test_repeatability_requires_exact_role_ids(
    tmp_path: Path, role_overrides: dict[str, object]
) -> None:
    p0, p0r = make_repeatability_packages(tmp_path, role_overrides=role_overrides)
    assert_failure_without_evidence(tmp_path, p0, p0r, "role|case_id")


def test_repeatability_rejects_same_package_twice(tmp_path: Path) -> None:
    p0, _ = make_repeatability_packages(tmp_path)
    assert_failure_without_evidence(tmp_path, p0, p0, "distinct|same")


def test_repeatability_rejects_execution_lock_for_wrong_role(tmp_path: Path) -> None:
    p0, p0r = make_repeatability_packages(tmp_path, p0r_lock_case_id="P0_parent")
    assert_failure_without_evidence(tmp_path, p0, p0r, "execution lock|case_id")


@pytest.mark.parametrize(
    "legality_defect",
    [
        "state0_float32",
        "state0_bad_shape",
        "state0_damage_above_one",
        "cycle_nonintegral",
        "physical_float32",
        "physical_complex",
        "physical_bad_shape",
        "damage_above_one",
        "damage_decreases_within_cycle",
        "damage_decreases_across_cycles",
        "alpha_negative",
        "alpha_decreases_within_cycle",
        "alpha_decreases_across_cycles",
        "d_gp_out_of_range",
        "f_alpha_out_of_range",
        "g_out_of_range",
        "raw_negative",
        "active_negative",
        "cyclemax_mismatch",
        "chronology_schedule",
    ],
)
def test_equal_illegal_packages_cannot_authenticate(
    tmp_path: Path, legality_defect: str
) -> None:
    p0, p0r = make_repeatability_packages(
        tmp_path, p0_legality_defect=legality_defect, p0r_legality_defect=legality_defect
    )
    assert_failure_without_evidence(
        tmp_path, p0, p0r, "state0|cycle|double|shape|damage|alpha|range|chronology|identity"
    )


@pytest.mark.parametrize("field_change", ["missing", "extra"])
def test_shard_schema_is_exact(tmp_path: Path, field_change: str) -> None:
    p0, p0r = make_repeatability_packages(
        tmp_path, p0_shard_schema=field_change, p0r_shard_schema=field_change
    )
    assert_failure_without_evidence(tmp_path, p0, p0r, "missing|unexpected|schema")


@pytest.mark.parametrize(
    ("manifest_change", "message"),
    [
        ("missing_mesh", "mesh"),
        ("extra_field", "unexpected|schema"),
        ("wrong_protocol", "protocol_version"),
        ("nonnumeric_protocol", "protocol_version"),
    ],
)
def test_terminal_manifest_schema_and_protocol_are_exact(
    tmp_path: Path, manifest_change: str, message: str
) -> None:
    p0, p0r = make_repeatability_packages(tmp_path)
    mutate_manifest(p0, manifest_change)
    assert_failure_without_evidence(tmp_path, p0, p0r, message)


@pytest.mark.parametrize(
    "c5_defect",
    [
        "missing_trace_column",
        "row_count",
        "reassembly_count",
        "final_metric",
        "threshold",
        "passed_false",
        "trace_hash",
        "stagger_skipped",
        "stagger_duplicated",
        "stagger_reordered",
        "stagger_fractional",
        "reassembly_skipped",
    ],
)
def test_complete_case_local_c5_evidence_is_authenticated(
    tmp_path: Path, c5_defect: str
) -> None:
    p0, p0r = make_repeatability_packages(
        tmp_path, p0_c5_defect=c5_defect, p0r_c5_defect=c5_defect
    )
    assert_failure_without_evidence(tmp_path, p0, p0r, "c5|trace|threshold")


def test_stale_manifest_hash_is_rejected_without_evidence(tmp_path: Path) -> None:
    p0, p0r = make_repeatability_packages(tmp_path)
    with (p0 / "TERMINAL_RESULT.json").open("ab") as stream:
        stream.write(b" ")
    assert_failure_without_evidence(tmp_path, p0, p0r, "mutable|bytes|hash")


def test_case_folded_manifest_collision_is_rejected(tmp_path: Path) -> None:
    p0, p0r = make_repeatability_packages(tmp_path)
    manifest_path = p0 / "TERMINAL_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text("utf-8"))
    duplicate = dict(manifest["files"][0])
    duplicate["path"] = duplicate["path"].swapcase()
    manifest["files"].append(duplicate)
    manifest["files"].sort(key=lambda item: item["path"])
    _replace_json(manifest_path, manifest)
    assert_failure_without_evidence(tmp_path, p0, p0r, "case-fold|collision")


def test_package_file_symlink_is_rejected_when_supported(tmp_path: Path) -> None:
    p0, p0r = make_repeatability_packages(tmp_path)
    event_path = p0 / "EVENT_METADATA.json"
    external = tmp_path / "outside-event.json"
    external.write_bytes(event_path.read_bytes())
    event_path.unlink()
    try:
        os.symlink(external, event_path)
    except (OSError, NotImplementedError) as exception:
        pytest.skip(f"file symlink creation unavailable: {exception}")
    refresh_manifest(p0)
    assert_failure_without_evidence(tmp_path, p0, p0r, "link|reparse")


def test_package_root_symlink_is_rejected_when_supported(tmp_path: Path) -> None:
    p0, p0r = make_repeatability_packages(tmp_path)
    alias = tmp_path / "P0_alias"
    try:
        os.symlink(p0, alias, target_is_directory=True)
    except (OSError, NotImplementedError) as exception:
        pytest.skip(f"directory symlink creation unavailable: {exception}")
    assert_failure_without_evidence(tmp_path, alias, p0r, "link|reparse")


def test_post_load_byte_replacement_is_caught_by_final_snapshot_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p0, p0r = make_repeatability_packages(tmp_path)
    original = PROTOCOL._read_mat_struct_bytes
    changed = False

    def mutate_after_read(payload: bytes, variable: str, label: str) -> dict[str, Any]:
        nonlocal changed
        value = original(payload, variable, label)
        if not changed:
            changed = True
            with (p0 / "TERMINAL_RESULT.json").open("ab") as stream:
                stream.write(b" ")
        return value

    monkeypatch.setattr(PROTOCOL, "_read_mat_struct_bytes", mutate_after_read)
    assert_failure_without_evidence(tmp_path, p0, p0r, "snapshot|changed|mutable")


def test_preexisting_evidence_lock_is_never_replaced(tmp_path: Path) -> None:
    p0, p0r = make_repeatability_packages(tmp_path)
    destination = tmp_path / "P0_REPEATABILITY_EVIDENCE_LOCK.json"
    destination.write_text("sentinel\n", encoding="utf-8")
    with pytest.raises(ProtocolError, match="already exists"):
        compare_repeatability(p0, p0r)
    assert destination.read_text("utf-8") == "sentinel\n"
    assert not list(tmp_path.glob(".P0_REPEATABILITY_EVIDENCE_LOCK.json.*.tmp"))


@pytest.mark.parametrize(
    "failure_class",
    ["identity", "event", "c5", "threshold", "missing", "dtype", "shape", "lock"],
)
def test_each_failure_class_has_no_publication_side_effect(
    tmp_path: Path, failure_class: str
) -> None:
    options: dict[str, object] = {}
    if failure_class == "identity":
        options["p0r_identity_overrides"] = {"source_commit": "b" * 40}
    elif failure_class == "event":
        options["p0r_terminal_cycle"] = 6
    elif failure_class == "c5":
        options["p0r_c5_defect"] = "passed_false"
    elif failure_class == "threshold":
        options["p0r_raw_offset"] = 2e-12
    elif failure_class == "missing":
        options["p0r_shard_schema"] = "missing"
    elif failure_class == "dtype":
        options["p0r_legality_defect"] = "physical_float32"
    elif failure_class == "shape":
        options["p0r_legality_defect"] = "state0_bad_shape"
    elif failure_class == "lock":
        options["p0r_lock_case_id"] = "P0_parent"
    p0, p0r = make_repeatability_packages(tmp_path, **options)
    with pytest.raises(ProtocolError):
        compare_repeatability(p0, p0r)
    assert not (tmp_path / "P0_REPEATABILITY_EVIDENCE_LOCK.json").exists()
    assert not list(tmp_path.glob(".P0_REPEATABILITY_EVIDENCE_LOCK.json.*.tmp"))


def make_repeatability_packages(
    root: Path,
    *,
    p0_terminal_cycle: int = 5,
    p0r_terminal_cycle: int = 5,
    p0_first_hit_cycle: int | None = None,
    p0_mat_format: str = "legacy",
    p0r_mat_format: str = "legacy",
    p0r_identity_overrides: dict[str, str] | None = None,
    role_overrides: dict[str, object] | None = None,
    p0r_lock_case_id: str | None = None,
    p0_legality_defect: str | None = None,
    p0r_legality_defect: str | None = None,
    p0_shard_schema: str | None = None,
    p0r_shard_schema: str | None = None,
    p0_c5_defect: str | None = None,
    p0r_c5_defect: str | None = None,
    p0r_raw_offset: float = 0.0,
) -> tuple[Path, Path]:
    identities = canonical_identities()
    roles = {"p0": "P0_parent", "p0r": "P0R_parent_repeat"}
    roles.update(role_overrides or {})
    p0_lock_nonce = "independent-p0-lock"
    p0r_lock_nonce = "independent-p0r-lock"
    p0 = _build_package(
        root / "P0_parent",
        roles["p0"],
        identities,
        terminal_cycle=p0_terminal_cycle,
        first_hit_cycle=p0_first_hit_cycle,
        mat_format=p0_mat_format,
        lock_case_id=str(roles["p0"]),
        lock_nonce=p0_lock_nonce,
        legality_defect=p0_legality_defect,
        shard_schema=p0_shard_schema,
        c5_defect=p0_c5_defect,
    )
    p0r_identities = {**identities, **(p0r_identity_overrides or {})}
    p0r = _build_package(
        root / "P0R_parent_repeat",
        roles["p0r"],
        p0r_identities,
        terminal_cycle=p0r_terminal_cycle,
        first_hit_cycle=None,
        mat_format=p0r_mat_format,
        lock_case_id=p0r_lock_case_id or str(roles["p0r"]),
        lock_nonce=p0r_lock_nonce,
        legality_defect=p0r_legality_defect,
        shard_schema=p0r_shard_schema,
        c5_defect=p0r_c5_defect,
        raw_offset=p0r_raw_offset,
    )
    return p0, p0r


def canonical_identities() -> dict[str, str]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "source_commit": "a" * 40,
        "mesh_sha256": "1" * 64,
        "element_ordering_id": "q4_connectivity_1_based_v1",
        "gp_ordering_id": "q4_2x2_native_order_v1",
        "state_semantics_id": "five_substep_post_commit_history_v1",
        "runtime_lock_sha256": "2" * 64,
        "family_contract_sha256": "3" * 64,
        "case_physics_contract_sha256": "4" * 64,
        "physical_input_sha256": "5" * 64,
        "solver_sha256": "6" * 64,
        "recovery_sha256": "7" * 64,
        "exporter_sha256": "8" * 64,
        "numerical_gate_contract_sha256": "9" * 64,
        "event_contract_sha256": "0" * 64,
    }


def canonical_runtime_expectations(root: Path) -> dict[str, object]:
    return {
        "matlab": {
            "release": "R2025b",
            "update": "Update 5",
            "version": "25.2.0.3177638",
            "computer": "PCWIN64",
            "executable_sha256": "a" * 64,
            "blas": "locked BLAS identity",
            "lapack": "locked LAPACK identity",
            "absolute_path_order": [
                str(root / name)
                for name in (
                    "runtime-overlay",
                    "producer-handoff",
                    "griphfith-sources",
                    "suitesparse-cholmod",
                    "suitesparse-amd",
                    "suitesparse-colamd",
                    "suitesparse-ccolamd",
                    "suitesparse-camd",
                )
            ],
        },
        "binary_sha256": {
            "initial": "b" * 64,
            "AMOR": "c" * 64,
            "AT1_HISTORY_FATIGUE": "d" * 64,
            "cholmod2": "e" * 64,
        },
    }


def _fixture_execution_lock(root: Path) -> dict[str, object]:
    roots = {
        name: str(root / name)
        for name in (
            "output",
            "work",
            "temp",
            "tmp",
            "pref",
            "cache",
            "matlab_startup_pref",
        )
    }
    return PROTOCOL.build_execution_input_lock(
        authorization_scope="test_only_non_authorizing",
        role="P0_parent",
        family_contract_sha256="1" * 64,
        case_physics_contract_sha256="2" * 64,
        source_commit="3" * 40,
        runtime_lock_sha256="4" * 64,
        source_manifest_sha256="5" * 64,
        runtime_expectations=canonical_runtime_expectations(root),
        roots=roots,
        launch_timestamp_utc="2026-08-03T12:00:00.0000000Z",
        no_clobber_receipt_id="runtime-measurement-fixture",
    )


def _build_package(
    root: Path,
    case_id: object,
    identities: dict[str, str],
    *,
    terminal_cycle: int,
    first_hit_cycle: int | None,
    mat_format: str,
    lock_case_id: str,
    lock_nonce: str,
    legality_defect: str | None,
    shard_schema: str | None,
    c5_defect: str | None,
    raw_offset: float = 0.0,
) -> Path:
    root.mkdir()
    (root / "substeps").mkdir()
    (root / "qualification").mkdir()

    lock_roots = {
        name: str(root.parent / f"{root.name}-{name}")
        for name in (
            "output",
            "work",
            "temp",
            "tmp",
            "pref",
            "cache",
            "matlab_startup_pref",
        )
    }
    builder_role = (
        lock_case_id
        if lock_case_id in PROTOCOL.FAMILY_ROLES
        else ("P0R_parent_repeat" if "P0R" in root.name else "P0_parent")
    )
    lock = PROTOCOL.build_execution_input_lock(
        authorization_scope=AUTHORIZATION_SCOPE,
        role=builder_role,
        family_contract_sha256=identities["family_contract_sha256"],
        case_physics_contract_sha256=identities["case_physics_contract_sha256"],
        source_commit=identities["source_commit"],
        runtime_lock_sha256=identities["runtime_lock_sha256"],
        source_manifest_sha256="c" * 64,
        runtime_expectations=canonical_runtime_expectations(root),
        roots=lock_roots,
        launch_timestamp_utc="2026-08-03T12:00:00.0000000Z",
        no_clobber_receipt_id=lock_nonce,
    )
    lock["case_id"] = lock_case_id
    lock_path = root / "EXECUTION_INPUT_LOCK.json"
    _write_json_no_clobber(lock_path, lock)
    execution_digest = _sha256(lock_path)

    state0 = {
        "d_node": np.full((4, 1), 0.09, dtype=np.float64),
        "alpha_bar_gp": np.zeros((2, 4), dtype=np.float64),
    }
    _apply_state0_defect(state0, legality_defect)
    savemat(root / "STATE0.mat", {"state0": state0}, do_compression=False)

    for cycle in range(1, terminal_cycle + 1):
        shard = _cycle_shard(cycle, identities, execution_digest, raw_offset)
        _apply_shard_defect(shard, cycle, legality_defect)
        if shard_schema == "missing":
            del shard["psi_active_gp"]
        elif shard_schema == "extra":
            shard["unrecognized_gp"] = np.zeros((2, 4, 5), dtype=np.float64)
        savemat(
            root / "substeps" / f"cycle_{cycle:04d}.mat",
            {"shard": shard},
            do_compression=False,
        )
    if mat_format == "v7.3":
        _convert_package_mats_to_real_v73(root)
    elif mat_format != "legacy":
        raise ValueError(f"unknown MAT format: {mat_format}")

    trace_path = root / "qualification" / "C5_STAGGER_TRACE.csv"
    trace_rows = complete_trace_rows(str(case_id))
    _apply_c5_trace_defect(trace_rows, c5_defect)
    columns = list(TRACE_COLUMNS)
    if c5_defect == "missing_trace_column":
        columns.remove("raw_phase_residual")
    trace_text = ",".join(columns) + "\n"
    for row in trace_rows:
        trace_text += ",".join(str(row[column]) for column in columns) + "\n"
    _write_bytes_no_clobber(trace_path, trace_text.encode("ascii"))
    receipt = complete_c5_receipt(str(case_id), trace_path, trace_rows)
    _apply_c5_defect(receipt, c5_defect)
    _write_json_no_clobber(
        root / "qualification" / "C5_NUMERICAL_GATE_RECEIPT.json", receipt
    )

    event_first_hit = terminal_cycle - 3 if first_hit_cycle is None else first_hit_cycle
    event = {
        "authorization_scope": AUTHORIZATION_SCOPE,
        "case_id": case_id,
        "first_hit_cycle": event_first_hit,
        "confirmed_cycle": terminal_cycle,
        "terminal_cycle": terminal_cycle,
        "peak_substep_ordinal": 4,
        "cycle_shard": f"substeps/cycle_{terminal_cycle:04d}.mat",
        "cycle_shard_sha256": _sha256(
            root / "substeps" / f"cycle_{terminal_cycle:04d}.mat"
        ),
    }
    _write_json_no_clobber(root / "EVENT_METADATA.json", event)
    _write_json_no_clobber(
        root / "TERMINAL_RESULT.json",
        {
            "authorization_scope": AUTHORIZATION_SCOPE,
            "case_id": case_id,
            "terminal_reason": "confirmed_penetration",
            "terminal_cycle": terminal_cycle,
            "first_hit_cycle": event_first_hit,
            "confirmed_cycle": terminal_cycle,
        },
    )
    manifest: dict[str, Any] = {
        "authorization_scope": AUTHORIZATION_SCOPE,
        "case_id": case_id,
        **identities,
        "execution_input_lock_sha256": execution_digest,
        "files": _manifest_file_entries(root),
    }
    assert set(manifest) == MANIFEST_FIELDS
    _write_json_no_clobber(root / "TERMINAL_MANIFEST.json", manifest)
    return root


def _cycle_shard(
    cycle: int,
    identities: dict[str, str],
    execution_digest: str,
    raw_offset: float,
) -> dict[str, object]:
    d_node = np.tile(
        np.linspace(0.10, 0.14, 5, dtype=np.float64) + 0.04 * (cycle - 1),
        (4, 1),
    )
    d_gp = np.empty((2, 4, 5), dtype=np.float64)
    for substep in range(5):
        d_gp[:, :, substep] = np.mean(d_node[:, substep])
    alpha = np.broadcast_to(
        (np.linspace(0.01, 0.05, 5) + 0.05 * (cycle - 1)).reshape(1, 1, 5),
        (2, 4, 5),
    ).copy()
    f_alpha = np.minimum(1.0, (1.0 - ((alpha - 0.5) / (alpha + 0.5))) ** 2)
    if cycle == 1:
        psi_raw = np.zeros((2, 4, 5), dtype=np.float64)
    else:
        psi_raw = np.broadcast_to(
            np.arange(1.0, 6.0).reshape(1, 1, 5), (2, 4, 5)
        ).copy() + raw_offset
    g_gp = (1.0 - d_gp) ** 2
    shard: dict[str, object] = {
        "cycle": np.array([[float(cycle)]], dtype=np.float64),
        "d_node": d_node,
        "d_gp": d_gp,
        "alpha_bar_gp": alpha,
        "f_alpha_gp": f_alpha,
        "psi_raw_gp": psi_raw,
        "g_gp": g_gp,
        "psi_active_gp": g_gp * psi_raw,
        "psi_raw_cyclemax_gp": np.max(psi_raw, axis=2),
        "substep_ordinal": np.arange(1.0, 6.0, dtype=np.float64).reshape(1, 5),
        "load_factor": np.array([[0.25, 0.5, 0.75, 1.0, 0.0]], dtype=np.float64),
        "raw_step_zero_based": (
            5 * (cycle - 1) + np.arange(5, dtype=np.float64)
        ).reshape(1, 5),
        "branch": np.array(
            [["loading", "loading", "loading", "loading", "unloading"]],
            dtype=object,
        ),
        "mesh_sha256": identities["mesh_sha256"],
        "element_ordering_id": identities["element_ordering_id"],
        "gp_ordering_id": identities["gp_ordering_id"],
        "state_semantics_id": identities["state_semantics_id"],
        "runtime_lock_sha256": identities["runtime_lock_sha256"],
        "family_contract_sha256": identities["family_contract_sha256"],
        "case_physics_contract_sha256": identities[
            "case_physics_contract_sha256"
        ],
        "execution_input_lock_sha256": execution_digest,
    }
    assert set(shard) == SHARD_FIELDS
    return shard


def _apply_state0_defect(state0: dict[str, np.ndarray], defect: str | None) -> None:
    if defect == "state0_float32":
        state0["d_node"] = state0["d_node"].astype(np.float32)
    elif defect == "state0_bad_shape":
        state0["d_node"] = state0["d_node"].reshape(1, 4)
    elif defect == "state0_damage_above_one":
        state0["d_node"][0, 0] = 1.1


def _apply_shard_defect(
    shard: dict[str, object], cycle: int, defect: str | None
) -> None:
    if defect == "cycle_nonintegral":
        shard["cycle"] = np.array([[float(cycle) + 0.5]])
    elif defect == "physical_float32":
        shard["d_node"] = np.asarray(shard["d_node"]).astype(np.float32)
    elif defect == "physical_complex":
        shard["d_node"] = np.asarray(shard["d_node"]).astype(np.complex128)
    elif defect == "physical_bad_shape":
        shard["d_node"] = np.asarray(shard["d_node"])[:, :4]
    elif defect == "damage_above_one":
        np.asarray(shard["d_node"])[0, 4] = 1.1
    elif defect == "damage_decreases_within_cycle":
        np.asarray(shard["d_node"])[0, 2] = 0.05
    elif defect == "damage_decreases_across_cycles" and cycle == 2:
        np.asarray(shard["d_node"])[:, 0] = 0.10
    elif defect == "alpha_negative":
        np.asarray(shard["alpha_bar_gp"])[0, 0, 0] = -2e-12
        _recompute_f_alpha(shard)
    elif defect == "alpha_decreases_within_cycle":
        np.asarray(shard["alpha_bar_gp"])[0, 0, 2] = 0.001
        _recompute_f_alpha(shard)
    elif defect == "alpha_decreases_across_cycles" and cycle == 2:
        np.asarray(shard["alpha_bar_gp"])[:, :, 0] = 0.001
        _recompute_f_alpha(shard)
    elif defect == "d_gp_out_of_range":
        np.asarray(shard["d_gp"])[0, 0, 0] = 1.1
        _recompute_g_active(shard)
    elif defect == "f_alpha_out_of_range":
        np.asarray(shard["f_alpha_gp"])[0, 0, 0] = 1.1
    elif defect == "g_out_of_range":
        np.asarray(shard["g_gp"])[0, 0, 0] = -0.1
        np.asarray(shard["psi_active_gp"])[0, 0, 0] = (
            np.asarray(shard["g_gp"])[0, 0, 0]
            * np.asarray(shard["psi_raw_gp"])[0, 0, 0]
        )
    elif defect == "raw_negative":
        np.asarray(shard["psi_raw_gp"])[0, 0, 0] = -1e-3
        _recompute_active_cyclemax(shard)
    elif defect == "active_negative":
        np.asarray(shard["psi_active_gp"])[0, 0, 0] = -1e-3
    elif defect == "cyclemax_mismatch":
        np.asarray(shard["psi_raw_cyclemax_gp"])[0, 0] += 2e-12
    elif defect == "chronology_schedule":
        np.asarray(shard["load_factor"])[0, 2] = 0.70


def _recompute_f_alpha(shard: dict[str, object]) -> None:
    alpha = np.asarray(shard["alpha_bar_gp"])
    shard["f_alpha_gp"] = np.minimum(
        1.0, (1.0 - ((alpha - 0.5) / (alpha + 0.5))) ** 2
    )


def _recompute_g_active(shard: dict[str, object]) -> None:
    shard["g_gp"] = (1.0 - np.asarray(shard["d_gp"])) ** 2
    _recompute_active_cyclemax(shard)


def _recompute_active_cyclemax(shard: dict[str, object]) -> None:
    shard["psi_active_gp"] = np.asarray(shard["g_gp"]) * np.asarray(
        shard["psi_raw_gp"]
    )
    shard["psi_raw_cyclemax_gp"] = np.max(
        np.asarray(shard["psi_raw_gp"]), axis=2
    )


def complete_trace_rows(case_id: str) -> list[dict[str, object]]:
    return [
        {
            "authorization_scope": AUTHORIZATION_SCOPE,
            "case_id": case_id,
            "cycle": 5,
            "substep_ordinal": 4,
            "stagger_iteration": 1,
            "reassembly_ordinal": 1,
            "displacement_residual": 2e-4,
            "raw_phase_residual": 8e-4,
            "projected_phase_kkt": 3e-4,
            "consecutive_stagger_delta": 8e-4,
            "primal_feasibility": 1e-13,
        },
        {
            "authorization_scope": AUTHORIZATION_SCOPE,
            "case_id": case_id,
            "cycle": 5,
            "substep_ordinal": 4,
            "stagger_iteration": 2,
            "reassembly_ordinal": 2,
            "displacement_residual": 1e-5,
            "raw_phase_residual": 6e-4,
            "projected_phase_kkt": 2e-5,
            "consecutive_stagger_delta": 3e-5,
            "primal_feasibility": 0.0,
        },
    ]


def complete_c5_receipt(
    case_id: str, trace_path: Path, rows: list[dict[str, object]]
) -> dict[str, object]:
    final = rows[-1]
    return {
        "authorization_scope": AUTHORIZATION_SCOPE,
        "case_id": case_id,
        "cycle": 5,
        "substep_ordinal": 4,
        "status": "PASS",
        "passed": True,
        "trace_sha256": _sha256(trace_path),
        "trace_row_count": len(rows),
        "reassembly_count": len(rows),
        "final_stagger_iteration": final["stagger_iteration"],
        "final_reassembly_ordinal": final["reassembly_ordinal"],
        "final_displacement_residual": final["displacement_residual"],
        "final_raw_phase_residual": final["raw_phase_residual"],
        "final_projected_phase_kkt": final["projected_phase_kkt"],
        "final_consecutive_stagger_delta": final["consecutive_stagger_delta"],
        "final_primal_feasibility": final["primal_feasibility"],
        "displacement_residual_threshold": 4e-4,
        "projected_phase_kkt_threshold": 4e-4,
        "consecutive_stagger_delta_threshold": 1e-3,
        "primal_feasibility_threshold": 1e-12,
    }


def _apply_c5_defect(receipt: dict[str, object], defect: str | None) -> None:
    if defect == "row_count":
        receipt["trace_row_count"] = 3
    elif defect == "reassembly_count":
        receipt["reassembly_count"] = 3
    elif defect == "final_metric":
        receipt["final_projected_phase_kkt"] = 1e-5
    elif defect == "threshold":
        receipt["projected_phase_kkt_threshold"] = 1e-2
    elif defect == "passed_false":
        receipt["passed"] = False
        receipt["status"] = "FAIL"
    elif defect == "trace_hash":
        receipt["trace_sha256"] = "f" * 64


def _apply_c5_trace_defect(
    rows: list[dict[str, object]], defect: str | None
) -> None:
    if defect == "stagger_skipped":
        rows[1]["stagger_iteration"] = 3
    elif defect == "stagger_duplicated":
        rows[1]["stagger_iteration"] = 1
    elif defect == "stagger_reordered":
        rows[0]["stagger_iteration"] = 2
        rows[1]["stagger_iteration"] = 1
    elif defect == "stagger_fractional":
        rows[1]["stagger_iteration"] = 1.5
    elif defect == "reassembly_skipped":
        rows[1]["reassembly_ordinal"] = 3


def mutate_manifest(root: Path, change: str) -> None:
    path = root / "TERMINAL_MANIFEST.json"
    value = json.loads(path.read_text("utf-8"))
    if change == "missing_mesh":
        del value["mesh_sha256"]
    elif change == "extra_field":
        value["unexpected"] = "forbidden"
    elif change == "wrong_protocol":
        value["protocol_version"] = "toy-road-p0-repeatability-v2.0"
    elif change == "nonnumeric_protocol":
        value["protocol_version"] = 21
    _replace_json(path, value)


def refresh_manifest(root: Path) -> None:
    path = root / "TERMINAL_MANIFEST.json"
    value = json.loads(path.read_text("utf-8"))
    value["files"] = _manifest_file_entries(root)
    _replace_json(path, value)


def _manifest_file_entries(root: Path) -> list[dict[str, str]]:
    manifest_path = root / "TERMINAL_MANIFEST.json"
    paths = sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file() and path != manifest_path
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    return [
        {"path": path.relative_to(root).as_posix(), "sha256": _sha256(path)}
        for path in paths
    ]


def _convert_package_mats_to_real_v73(root: Path) -> None:
    matlab = shutil.which("matlab")
    if matlab is None:
        pytest.skip("MATLAB is required for the real -v7.3 integration fixture")
    paths = [root / "STATE0.mat", *sorted((root / "substeps").glob("*.mat"))]
    script_path = root.parent / f"convert_{root.name}_to_v73.m"
    matlab_paths = ";".join(
        f"'{str(path).replace("'", "''")}'" for path in paths
    )
    script = (
        f"paths={{{matlab_paths}}};\n"
        "for index=1:numel(paths)\n"
        "  payload=load(paths{index});\n"
        "  temporary=[paths{index} '.v73'];\n"
        "  save(temporary,'-struct','payload','-v7.3');\n"
        "  movefile(temporary,paths{index},'f');\n"
        "end\n"
    )
    script_path.write_text(script, encoding="ascii")
    try:
        result = subprocess.run(
            [matlab, "-batch", f"run('{str(script_path).replace("'", "''")}')"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
    finally:
        script_path.unlink(missing_ok=True)
    if result.returncode != 0:
        raise AssertionError(
            f"MATLAB -v7.3 fixture conversion failed:\n{result.stdout}\n{result.stderr}"
        )


def assert_failure_without_evidence(
    root: Path, p0: Path, p0r: Path, message: str
) -> None:
    with pytest.raises(ProtocolError, match=message):
        compare_repeatability(p0, p0r)
    assert not (root / "P0_REPEATABILITY_EVIDENCE_LOCK.json").exists()
    assert not list(root.glob(".P0_REPEATABILITY_EVIDENCE_LOCK.json.*.tmp"))


def _write_json_no_clobber(path: Path, value: object) -> None:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8") + b"\n"
    _write_bytes_no_clobber(path, payload)


def _replace_json(path: Path, value: object) -> None:
    path.unlink()
    _write_json_no_clobber(path, value)


def _write_bytes_no_clobber(path: Path, payload: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(payload)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
