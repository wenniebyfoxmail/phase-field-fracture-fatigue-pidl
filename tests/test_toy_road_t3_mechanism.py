from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from analysis.toy_road_t3_mechanism_20260819.evidence import (
    EvidencePaths,
    build_compact_evidence,
    load_json_strict,
    sha256_file,
    validate_shard_inventory,
    validate_t3_bindings,
    verify_compact_evidence,
)


REPO = Path(__file__).resolve().parents[1]
REAL_T3_OUTPUT = Path(r"C:\q4diag\toy-road-t3-production-7c56ff3-run1\output")
REAL_T3_RUN = REAL_T3_OUTPUT.parent
REAL_T3_SEAL = Path(r"C:\q4diag\toy-road-t3-sibling-seal-2ff8b5f")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _real_paths() -> EvidencePaths:
    return EvidencePaths(
        authenticated_terminal=REAL_T3_SEAL / "T3_AUTHENTICATED_TERMINAL.json",
        terminal_adjudication=(
            REAL_T3_SEAL
            / "terminal_evidence"
            / "T3_SIBLING_TERMINAL_ADJUDICATION.json"
        ),
        terminal_manifest=REAL_T3_OUTPUT / "TERMINAL_MANIFEST.json",
        terminal_result=REAL_T3_OUTPUT / "TERMINAL_RESULT.json",
        event_metadata=REAL_T3_OUTPUT / "EVENT_METADATA.json",
        c5_receipt=(
            REAL_T3_OUTPUT / "qualification" / "C5_NUMERICAL_GATE_RECEIPT.json"
        ),
        c5_trace=REAL_T3_OUTPUT / "qualification" / "C5_STAGGER_TRACE.csv",
        runtime_measurement=(
            REAL_T3_RUN / "receipts" / "T3_RUNTIME_MEASUREMENT.json"
        ),
        execution_input_lock=REAL_T3_OUTPUT / "EXECUTION_INPUT_LOCK.json",
        launch_receipt=REAL_T3_RUN / "receipts" / "T3_SIBLING_LAUNCH_RECEIPT.json",
    )


def test_load_json_strict_rejects_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"status":"PASS","status":"FAIL"}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key: status"):
        load_json_strict(path)


def test_load_json_strict_rejects_nan(tmp_path: Path) -> None:
    path = tmp_path / "nan.json"
    path.write_text('{"value":NaN}', encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite JSON constant"):
        load_json_strict(path)


def test_validate_shard_inventory_requires_71_consecutive_entries() -> None:
    files = [
        {
            "path": f"substeps/cycle_{cycle:04d}.mat",
            "sha256": f"{cycle:064x}",
            "identity": {"size": cycle},
        }
        for cycle in range(1, 72)
    ]
    records = validate_shard_inventory(files)
    assert len(records) == 71
    assert records[0].path == "substeps/cycle_0001.mat"
    assert records[-1].path == "substeps/cycle_0071.mat"

    with pytest.raises(ValueError, match="exactly 71"):
        validate_shard_inventory(files[:-1])


def test_validate_t3_bindings_rejects_manifest_tampering(tmp_path: Path) -> None:
    paths = _real_paths()
    assert validate_t3_bindings(paths)["status"] == "PASS"

    tampered_manifest = tmp_path / "TERMINAL_MANIFEST.json"
    tampered_manifest.write_bytes(paths.terminal_manifest.read_bytes() + b" ")
    tampered = EvidencePaths(
        **{
            **paths.__dict__,
            "terminal_manifest": tampered_manifest,
        }
    )
    with pytest.raises(ValueError, match="terminal manifest SHA-256 mismatch"):
        validate_t3_bindings(tampered)


def test_compact_locator_is_portable_and_non_authorizing(tmp_path: Path) -> None:
    destination = tmp_path / "compact"
    result = build_compact_evidence(
        _real_paths(),
        destination,
        (
            "griphfith/toy-road-evidence/T3_loading_history/"
            "manifest-455b149b14276598ad87e4bcea6b6a2916de6e59d3812f791d66e61b1344bb01"
        ),
    )
    assert result["status"] == "PASS"
    locator = load_json_strict(destination / "ONEDRIVE_PACKAGE.json")
    encoded = json.dumps(locator, sort_keys=True)
    assert "C:\\Users\\" not in encoded
    assert locator["authorization_capability"] is None
    assert locator["follow_on_authorized"] is False
    assert locator["cycle_shard_count"] == 71
    assert verify_compact_evidence(destination)["status"] == "PASS"


def test_verify_compact_evidence_detects_modified_file(tmp_path: Path) -> None:
    destination = tmp_path / "compact"
    build_compact_evidence(
        _real_paths(),
        destination,
        "griphfith/toy-road-evidence/T3_loading_history/manifest-455b149b",
    )
    target = destination / "TERMINAL_RESULT.json"
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(ValueError, match="compact evidence SHA-256 mismatch"):
        verify_compact_evidence(destination)


def test_sha256_file_matches_direct_hash(tmp_path: Path) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(b"toy-road-t3")
    assert sha256_file(path) == _sha(path)
