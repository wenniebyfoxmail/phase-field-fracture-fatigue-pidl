from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


EXPECTED_CASE = "T3_loading_history"
EXPECTED_MANIFEST = "455b149b14276598ad87e4bcea6b6a2916de6e59d3812f791d66e61b1344bb01"
EXPECTED_ADJUDICATION = "9c0a0783bd6c59d825300538336258350df63c294f38f7febf29dae905c00300"
EXPECTED_FIRST_HIT = 68
EXPECTED_CONFIRMED = 71
EXPECTED_SHARDS = 71


@dataclass(frozen=True)
class EvidencePaths:
    authenticated_terminal: Path
    terminal_adjudication: Path
    terminal_manifest: Path
    terminal_result: Path
    event_metadata: Path
    c5_receipt: Path
    c5_trace: Path
    runtime_measurement: Path
    execution_input_lock: Path
    launch_receipt: Path


@dataclass(frozen=True)
class ShardRecord:
    path: str
    size: int
    sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def load_json_strict(path: Path) -> dict[str, Any]:
    value = json.loads(
        Path(path).read_text(encoding="utf-8"),
        object_pairs_hook=_pairs_no_duplicates,
        parse_constant=_reject_constant,
    )
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _canonical_sha(value: str, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"invalid {label}")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"invalid {label}") from exc
    return value.lower()


def validate_shard_inventory(files: Iterable[dict[str, Any]]) -> list[ShardRecord]:
    selected = [item for item in files if str(item.get("path", "")).startswith("substeps/cycle_")]
    if len(selected) != EXPECTED_SHARDS:
        raise ValueError(f"expected exactly 71 cycle shards, found {len(selected)}")
    records: list[ShardRecord] = []
    for cycle, item in enumerate(selected, start=1):
        expected = f"substeps/cycle_{cycle:04d}.mat"
        if item.get("path") != expected:
            raise ValueError(f"nonconsecutive cycle shard: expected {expected}")
        identity = item.get("identity")
        if not isinstance(identity, dict) or not isinstance(identity.get("size"), int):
            raise ValueError(f"invalid size identity for {expected}")
        records.append(
            ShardRecord(
                path=expected,
                size=identity["size"],
                sha256=_canonical_sha(item.get("sha256"), f"SHA-256 for {expected}"),
            )
        )
    return records


def validate_t3_bindings(paths: EvidencePaths) -> dict[str, Any]:
    auth = load_json_strict(paths.authenticated_terminal)
    adjudication = load_json_strict(paths.terminal_adjudication)
    terminal = load_json_strict(paths.terminal_result)
    event = load_json_strict(paths.event_metadata)
    c5 = load_json_strict(paths.c5_receipt)
    runtime = load_json_strict(paths.runtime_measurement)
    lock = load_json_strict(paths.execution_input_lock)
    launch = load_json_strict(paths.launch_receipt)

    if auth.get("status") != "PASS" or auth.get("case_id") != EXPECTED_CASE:
        raise ValueError("authenticated terminal is not T3 PASS")
    actual_manifest = sha256_file(paths.terminal_manifest)
    if actual_manifest != EXPECTED_MANIFEST or auth.get("manifest_sha256") != actual_manifest:
        raise ValueError("terminal manifest SHA-256 mismatch")
    if sha256_file(paths.terminal_adjudication) != EXPECTED_ADJUDICATION:
        raise ValueError("terminal adjudication SHA-256 mismatch")
    if adjudication.get("status") != "PASS" or adjudication.get("case_id") != EXPECTED_CASE:
        raise ValueError("terminal adjudication is not T3 PASS")
    shards = validate_shard_inventory(auth.get("files", []))
    if terminal.get("case_id") != EXPECTED_CASE:
        raise ValueError("terminal result case mismatch")
    for payload in (terminal, event):
        if payload.get("first_hit_cycle") != EXPECTED_FIRST_HIT:
            raise ValueError("T3 first-hit mismatch")
        if payload.get("confirmed_cycle") != EXPECTED_CONFIRMED:
            raise ValueError("T3 confirmation mismatch")
        if payload.get("terminal_cycle") != EXPECTED_CONFIRMED:
            raise ValueError("T3 terminal cycle mismatch")
    if c5.get("status") != "PASS" or c5.get("passed") is not True:
        raise ValueError("T3 c5 gate is not PASS")
    if sha256_file(paths.c5_receipt) != auth.get("c5_receipt_sha256"):
        raise ValueError("T3 c5 receipt SHA-256 mismatch")
    identities = (
        "source_commit",
        "runtime_lock_sha256",
        "family_contract_sha256",
        "case_physics_contract_sha256",
        "execution_input_lock_sha256",
    )
    for key in identities:
        expected = runtime.get(key)
        candidates = [value for value in (lock.get(key), launch.get(key), auth.get(key)) if value is not None]
        if any(value != expected for value in candidates):
            raise ValueError(f"identity mismatch: {key}")
    return {
        "status": "PASS",
        "case_id": EXPECTED_CASE,
        "manifest_sha256": actual_manifest,
        "adjudication_sha256": EXPECTED_ADJUDICATION,
        "first_hit_cycle": EXPECTED_FIRST_HIT,
        "confirmed_cycle": EXPECTED_CONFIRMED,
        "cycle_shard_count": len(shards),
        "cycle_shards": [record.__dict__ for record in shards],
    }


def _validate_portable_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "://" in value or "?" in value:
        raise ValueError("OneDrive locator must be a portable relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("OneDrive locator must be a portable relative path")
    return path.as_posix()


def build_compact_evidence(
    paths: EvidencePaths,
    destination: Path,
    onedrive_relative_path: str,
    *,
    upload_state: str = "LOCAL_MIRROR_NOT_YET_BUILT",
) -> dict[str, Any]:
    binding = validate_t3_bindings(paths)
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(f"compact evidence destination exists: {destination}")
    portable = _validate_portable_path(onedrive_relative_path)
    allowed_upload_states = {
        "LOCAL_MIRROR_NOT_YET_BUILT",
        "LOCAL_MIRROR_VERIFIED",
        "ONEDRIVE_UPLOAD_VERIFIED",
    }
    if upload_state not in allowed_upload_states:
        raise ValueError(f"invalid OneDrive upload state: {upload_state}")
    destination.mkdir(parents=True, exist_ok=False)
    allowlist = {
        "T3_AUTHENTICATED_TERMINAL.json": paths.authenticated_terminal,
        "T3_SIBLING_TERMINAL_ADJUDICATION.json": paths.terminal_adjudication,
        "TERMINAL_MANIFEST.json": paths.terminal_manifest,
        "TERMINAL_RESULT.json": paths.terminal_result,
        "EVENT_METADATA.json": paths.event_metadata,
        "C5_NUMERICAL_GATE_RECEIPT.json": paths.c5_receipt,
        "C5_STAGGER_TRACE.csv": paths.c5_trace,
        "T3_RUNTIME_MEASUREMENT.json": paths.runtime_measurement,
        "EXECUTION_INPUT_LOCK.json": paths.execution_input_lock,
        "T3_SIBLING_LAUNCH_RECEIPT.json": paths.launch_receipt,
    }
    for name, source in allowlist.items():
        shutil.copyfile(source, destination / name)
    locator = {
        "schema_version": "toy_road_t3_onedrive_locator_v1",
        "status": "PASS",
        "case_id": EXPECTED_CASE,
        "manifest_sha256": EXPECTED_MANIFEST,
        "terminal_adjudication_sha256": EXPECTED_ADJUDICATION,
        "cycle_shard_count": EXPECTED_SHARDS,
        "onedrive_relative_path": portable,
        "upload_state": upload_state,
        "authorization_capability": None,
        "follow_on_authorized": False,
    }
    (destination / "ONEDRIVE_PACKAGE.json").write_bytes(_canonical_bytes(locator) + b"\n")
    records = [
        {"path": path.name, "size": path.stat().st_size, "sha256": sha256_file(path)}
        for path in sorted(destination.iterdir(), key=lambda item: item.name)
        if path.is_file()
    ]
    inventory = {
        "schema_version": "toy_road_t3_compact_evidence_inventory_v1",
        "status": "PASS",
        "binding": binding,
        "files": records,
        "authorization_capability": None,
        "follow_on_authorized": False,
    }
    inventory_path = destination / "COMPACT_EVIDENCE_INVENTORY.json"
    inventory_path.write_bytes(_canonical_bytes(inventory) + b"\n")
    sums = "".join(f"{record['sha256']}  {record['path']}\n" for record in records)
    (destination / "SHA256SUMS.txt").write_text(sums, encoding="ascii", newline="\n")
    return verify_compact_evidence(destination)


def verify_compact_evidence(root: Path) -> dict[str, Any]:
    root = Path(root)
    inventory = load_json_strict(root / "COMPACT_EVIDENCE_INVENTORY.json")
    if inventory.get("status") != "PASS":
        raise ValueError("compact evidence inventory is not PASS")
    for record in inventory.get("files", []):
        path = root / record["path"]
        if not path.is_file() or sha256_file(path) != record["sha256"]:
            raise ValueError(f"compact evidence SHA-256 mismatch: {record['path']}")
        if path.stat().st_size != record["size"]:
            raise ValueError(f"compact evidence size mismatch: {record['path']}")
    listed = {record["path"] for record in inventory.get("files", [])}
    expected_files = listed | {"COMPACT_EVIDENCE_INVENTORY.json", "SHA256SUMS.txt"}
    actual_files = {path.name for path in root.iterdir() if path.is_file()}
    extras = sorted(actual_files - expected_files)
    missing = sorted(expected_files - actual_files)
    if extras:
        raise ValueError(f"unlisted compact evidence file: {extras[0]}")
    if missing:
        raise ValueError(f"missing compact evidence file: {missing[0]}")
    locator = load_json_strict(root / "ONEDRIVE_PACKAGE.json")
    if locator.get("authorization_capability") is not None or locator.get("follow_on_authorized") is not False:
        raise ValueError("compact evidence locator carries authorization capability")
    binding = inventory.get("binding", {})
    if binding.get("manifest_sha256") != EXPECTED_MANIFEST or binding.get("cycle_shard_count") != EXPECTED_SHARDS:
        raise ValueError("compact evidence binding mismatch")
    return {
        "status": "PASS",
        "case_id": EXPECTED_CASE,
        "manifest_sha256": EXPECTED_MANIFEST,
        "cycle_shard_count": EXPECTED_SHARDS,
        "file_count": len(inventory["files"]),
    }


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify_compact_evidence(args.root), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
