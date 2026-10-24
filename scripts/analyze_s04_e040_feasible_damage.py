#!/usr/bin/env python3
"""Read-only S04-E040 versus S04-E037-R001 trajectory comparison.

The two arms optimise different scalar objectives.  This tool never compares
them as if they had the same loss: it reports the common physical-energy
components and writes both objective definitions explicitly.  It pairs only a
continuous prefix of *accepted* candidate states, keyed by
``(step, cycle, substep, load)``.  A capped, rejected, missing, or phase-mismatched
candidate record is retained separately in ``terminal_trial.json`` and is never
used as a trajectory point.

Inputs are read only.  All generated files live below ``--output``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np


LOAD_ABS_TOLERANCE = 1.0e-7
MESH_KEYS = ("xy", "triangles", "area")
NODE_FIELD_KEYS = ("d", "history_d")
ELEMENT_FIELD_KEYS = ("strain_xx", "strain_yy", "strain_xy", "raw_psi", "trial_A")
E040_POINTER_SCHEMA = "S04-E040-accepted-state-pointer-v1"
E040_INDEX_SCHEMA = "S04-E040-state-index-v1"
E040_MANIFEST_SCHEMA = "S04-E040-artifact-manifest-v1"
TRI3_GAUSS_BARYCENTRIC = np.asarray(
    ((2.0 / 3.0, 1.0 / 6.0, 1.0 / 6.0),
     (1.0 / 6.0, 2.0 / 3.0, 1.0 / 6.0),
     (1.0 / 6.0, 1.0 / 6.0, 2.0 / 3.0)),
    dtype=np.float64,
)


class InputContractError(RuntimeError):
    """The archived inputs cannot support the declared comparison."""


def _json_safe(value: Any) -> Any:
    """Convert numpy values recursively and reject non-finite JSON numbers."""
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def dump_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(_json_safe(value), indent=2, sort_keys=True, allow_nan=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], default_keys: Iterable[str] = ()) -> None:
    """Write a stable union of row keys, including an empty-schema CSV if needed."""
    keys = list(dict.fromkeys((*default_keys, *(key for row in rows for key in row))))
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows([_json_safe(row) for row in rows])


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise InputContractError(f"Missing required input: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InputContractError(f"Invalid JSON in {path}: {exc}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _existing_unique(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        path = path.resolve()
        if path not in seen:
            seen.add(path)
            result.append(path)
    return result


def resolve_arm_dir(provided: Path, arm_name: str) -> Path:
    """Accept either an arm directory or its enclosing output/raw directory."""
    provided = provided.resolve()
    candidates = _existing_unique((provided, provided / arm_name))
    for candidate in candidates:
        if (candidate / "steps.json").is_file():
            return candidate
    rendered = ", ".join(str(item) for item in candidates)
    raise InputContractError(
        f"Could not find {arm_name!r} steps.json under supplied path; checked {rendered}"
    )


def resolve_e040_candidate_arm_dir(provided: Path) -> Path:
    """Locate an E040 arm even when a crash prevented ``steps.json`` writing."""
    provided = provided.resolve()
    candidates = _existing_unique((provided, provided / "feasible_damage"))
    for candidate in candidates:
        if (candidate / "accepted_state_pointer.json").is_file():
            return candidate
    rendered = ", ".join(str(item) for item in candidates)
    raise InputContractError(
        "Could not find E040 accepted_state_pointer.json under supplied path; "
        f"checked {rendered}"
    )


def resolve_mesh_path(provided: Path, arm_dir: Path) -> Path:
    """Find a shared mesh next to either a result root or its arm subdirectory."""
    candidates = _existing_unique(
        (
            provided / "mesh.npz",
            arm_dir / "mesh.npz",
            arm_dir.parent / "mesh.npz",
            provided.parent / "mesh.npz",
        )
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    rendered = ", ".join(str(item) for item in candidates)
    raise InputContractError(f"Could not locate mesh.npz; checked {rendered}")


def load_mesh(path: Path) -> dict[str, np.ndarray]:
    try:
        with np.load(path, allow_pickle=False) as archive:
            missing = [key for key in MESH_KEYS if key not in archive.files]
            if missing:
                raise InputContractError(f"{path} lacks required mesh keys: {missing}")
            mesh = {key: np.asarray(archive[key]) for key in (*MESH_KEYS, "node_weights") if key in archive.files}
    except OSError as exc:
        raise InputContractError(f"Cannot read mesh {path}: {exc}") from exc

    xy, triangles, area = mesh["xy"], mesh["triangles"], mesh["area"]
    if xy.ndim != 2 or xy.shape[1] != 2:
        raise InputContractError(f"{path}: xy must have shape (n_nodes, 2), got {xy.shape}")
    if triangles.ndim != 2 or triangles.shape[1] != 3:
        raise InputContractError(f"{path}: triangles must have shape (n_elements, 3), got {triangles.shape}")
    if area.shape != (len(triangles),):
        raise InputContractError(f"{path}: area shape {area.shape} does not match {len(triangles)} elements")
    if not np.issubdtype(triangles.dtype, np.integer):
        raise InputContractError(f"{path}: triangles must be integer indices, got {triangles.dtype}")
    if not np.isfinite(xy).all() or not np.isfinite(area).all():
        raise InputContractError(f"{path}: xy or area contains non-finite values")
    if np.any(area <= 0.0):
        raise InputContractError(f"{path}: element areas must be strictly positive")
    if triangles.size and (triangles.min() < 0 or triangles.max() >= len(xy)):
        raise InputContractError(f"{path}: triangles contain out-of-range node indices")
    if "node_weights" in mesh:
        weights = mesh["node_weights"]
        if weights.shape != (len(xy),):
            raise InputContractError(f"{path}: node_weights shape {weights.shape} does not match {len(xy)} nodes")
        if not np.isfinite(weights).all() or np.any(weights < 0.0) or float(weights.sum()) <= 0.0:
            raise InputContractError(f"{path}: node_weights must be finite, non-negative, and sum positive")
    return mesh


def strict_mesh_check(reference: dict[str, np.ndarray], candidate: dict[str, np.ndarray]) -> dict[str, Any]:
    """Reject any geometry/order mismatch before field values are paired."""
    report: dict[str, Any] = {}
    for key in MESH_KEYS:
        ref, new = reference[key], candidate[key]
        identical = np.array_equal(ref, new)
        report[f"{key}_bitwise_equal"] = bool(identical)
        if not identical:
            detail = f"shape {ref.shape} versus {new.shape}"
            if ref.shape == new.shape and np.issubdtype(ref.dtype, np.number) and np.issubdtype(new.dtype, np.number):
                detail += f", maximum absolute difference {float(np.max(np.abs(ref.astype(np.float64) - new.astype(np.float64)))):.17g}"
            raise InputContractError(f"Strict mesh mismatch for {key}: {detail}")
    if "node_weights" in reference and "node_weights" in candidate:
        report["node_weights_bitwise_equal"] = bool(
            np.array_equal(reference["node_weights"], candidate["node_weights"])
        )
    else:
        report["node_weights_bitwise_equal"] = None
    return report


def require_records(path: Path) -> list[dict[str, Any]]:
    raw = read_json(path / "steps.json")
    if not isinstance(raw, list) or not all(isinstance(item, dict) for item in raw):
        raise InputContractError(f"{path / 'steps.json'} must contain a JSON list of records")
    return list(raw)


def _required_float(record: dict[str, Any], key: str, context: str) -> float:
    if key not in record:
        raise InputContractError(f"{context}: missing {key!r}")
    try:
        value = float(record[key])
    except (TypeError, ValueError) as exc:
        raise InputContractError(f"{context}: {key!r} is not numeric") from exc
    if not math.isfinite(value):
        raise InputContractError(f"{context}: {key!r} is not finite")
    return value


def phase(record: dict[str, Any], context: str) -> tuple[int, int, int, float]:
    values: list[int] = []
    for key in ("step", "cycle", "substep"):
        if key not in record:
            raise InputContractError(f"{context}: missing {key!r}")
        try:
            value = int(record[key])
        except (TypeError, ValueError) as exc:
            raise InputContractError(f"{context}: {key!r} is not an integer") from exc
        if value < 1:
            raise InputContractError(f"{context}: {key!r} must be positive")
        values.append(value)
    return values[0], values[1], values[2], _required_float(record, "load", context)


def accepted(record: dict[str, Any], context: str) -> bool:
    if "accepted" not in record or not isinstance(record["accepted"], bool):
        raise InputContractError(f"{context}: accepted must be a JSON boolean")
    return record["accepted"]


def ordered_records(records: list[dict[str, Any]], label: str) -> list[dict[str, Any]]:
    seen_steps: set[int] = set()
    checked: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        context = f"{label} record #{index}"
        step, _, _, _ = phase(record, context)
        accepted(record, context)
        if step in seen_steps:
            raise InputContractError(f"{label}: duplicate step number {step}")
        seen_steps.add(step)
        checked.append(record)
    return sorted(checked, key=lambda record: phase(record, label)[0])


def phase_dict(record: dict[str, Any], context: str) -> dict[str, Any]:
    step, cycle, substep, load = phase(record, context)
    return {"step": step, "cycle": cycle, "substep": substep, "load": load}


def same_phase(reference: dict[str, Any], candidate: dict[str, Any], load_tolerance: float) -> bool:
    ref = phase(reference, "reference record")
    new = phase(candidate, "candidate record")
    return ref[:3] == new[:3] and abs(ref[3] - new[3]) <= load_tolerance


def step_dir(arm_dir: Path, record: dict[str, Any], label: str) -> Path:
    step, _, _, _ = phase(record, label)
    return arm_dir / f"step_{step:03d}"


def receipt_for(arm_dir: Path, record: dict[str, Any], label: str, load_tolerance: float) -> dict[str, Any]:
    """Use the per-step receipt when present and reject a conflicting one."""
    receipt_path = step_dir(arm_dir, record, label) / "receipt.json"
    if not receipt_path.exists():
        return record
    receipt = read_json(receipt_path)
    if not isinstance(receipt, dict):
        raise InputContractError(f"{receipt_path} must contain one JSON object")
    if not same_phase(record, receipt, load_tolerance):
        raise InputContractError(f"{receipt_path} phase does not match steps.json")
    if accepted(record, label) != accepted(receipt, str(receipt_path)):
        raise InputContractError(f"{receipt_path} accepted flag does not match steps.json")
    return receipt


def _json_object(path: Path, context: str) -> dict[str, Any]:
    value = read_json(path)
    if not isinstance(value, dict):
        raise InputContractError(f"{context} must contain one JSON object: {path}")
    return value


def _safe_child_name(value: Any, context: str) -> str:
    """Return one artifact filename, rejecting path traversal in archived metadata."""
    if (
        not isinstance(value, str)
        or not value
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or Path(value).name != value
    ):
        raise InputContractError(f"{context}: expected one safe filename")
    return value


def _required_string(record: dict[str, Any], key: str, context: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value:
        raise InputContractError(f"{context}: missing or invalid {key!r}")
    return value


def _verify_hashed_file(path: Path, expected_sha256: Any, context: str) -> str:
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        raise InputContractError(f"{context}: invalid expected SHA-256")
    if not path.is_file():
        raise InputContractError(f"{context}: missing file {path}")
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise InputContractError(f"{context}: SHA-256 mismatch for {path}")
    return actual


def _verify_artifact_manifest(
    evidence_dir: Path,
    manifest_file: Any,
    expected_manifest_sha256: Any,
    context: str,
) -> dict[str, dict[str, Any]]:
    manifest_name = _safe_child_name(manifest_file, f"{context} artifact manifest")
    manifest_path = evidence_dir / manifest_name
    _verify_hashed_file(manifest_path, expected_manifest_sha256, f"{context} artifact manifest")
    manifest = _json_object(manifest_path, f"{context} artifact manifest")
    if manifest.get("schema") != E040_MANIFEST_SCHEMA:
        raise InputContractError(f"{context}: unexpected artifact manifest schema")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise InputContractError(f"{context}: artifact manifest has no artifacts")
    entries: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(artifacts):
        entry_context = f"{context} artifact #{index}"
        if not isinstance(entry, dict):
            raise InputContractError(f"{entry_context}: malformed artifact entry")
        name = _safe_child_name(entry.get("name"), entry_context)
        if name in entries:
            raise InputContractError(f"{entry_context}: duplicate artifact name {name!r}")
        size = entry.get("bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise InputContractError(f"{entry_context}: invalid artifact byte count")
        artifact_path = evidence_dir / name
        _verify_hashed_file(artifact_path, entry.get("sha256"), entry_context)
        if artifact_path.stat().st_size != size:
            raise InputContractError(f"{entry_context}: artifact byte count mismatch")
        entries[name] = entry
    return entries


def _validate_pointer_index_chain(
    arm_dir: Path,
    load_tolerance: float,
) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], dict[str, Any]]:
    """Read E040's pointer chain and derive only pointer-authoritative states.

    The per-step artifact receipt is deliberately immutable and is written
    before pointer publication, so its ``accepted`` value may be ``null``.
    The pointer/index/manifest chain, rather than that field, is the authority
    for an accepted E040 state.
    """
    pointer_path = arm_dir / "accepted_state_pointer.json"
    pointer = _json_object(pointer_path, "E040 accepted-state pointer")
    if pointer.get("schema") != E040_POINTER_SCHEMA:
        raise InputContractError("E040 accepted-state pointer has an unexpected schema")
    indices_dir = arm_dir / "state_indices"
    records_dir = arm_dir / "accepted_states"
    if not indices_dir.is_dir() or not records_dir.is_dir():
        raise InputContractError("E040 pointer requires state_indices/ and accepted_states/ directories")

    pointer_index_file = _safe_child_name(pointer.get("state_index_file"), "E040 pointer state index")
    pointer_index_sha = pointer.get("state_index_sha256")
    pointer_commit = _required_string(pointer, "accepted_commit_id", "E040 pointer")
    pointer_parent_commit = pointer.get("parent_commit_id")
    if pointer_parent_commit is not None and not isinstance(pointer_parent_commit, str):
        raise InputContractError("E040 pointer: invalid parent_commit_id")
    pointer_parent_index = pointer.get("parent_index_file")
    if pointer_parent_index is not None:
        _safe_child_name(pointer_parent_index, "E040 pointer parent index")
    pointer_mesh_hash = _required_string(pointer, "mesh_order_hash", "E040 pointer")
    pointer_route_hash = _required_string(pointer, "field_route_hash", "E040 pointer")
    pointer_record_file = _safe_child_name(pointer.get("record_file"), "E040 pointer record")
    pointer_record_sha = pointer.get("record_sha256")

    if not isinstance(pointer_index_sha, str):
        raise InputContractError("E040 pointer: invalid state_index_sha256")
    expected_index_file = pointer_index_file
    expected_index_sha: str | None = pointer_index_sha
    expected_commit = pointer_commit
    expected_parent_commit: str | None = pointer_parent_commit
    check_expected_parent = True
    visited: set[str] = set()
    reverse_chain: list[dict[str, Any]] = []

    while True:
        if expected_index_file in visited:
            raise InputContractError("E040 state-index chain contains a cycle")
        visited.add(expected_index_file)
        index_path = indices_dir / expected_index_file
        if expected_index_sha is None:
            if not index_path.is_file():
                raise InputContractError(f"E040 state-index chain is missing {index_path}")
            index_sha = sha256_file(index_path)
        else:
            index_sha = _verify_hashed_file(index_path, expected_index_sha, "E040 state index")
        state_index = _json_object(index_path, "E040 state index")
        if state_index.get("schema") != E040_INDEX_SCHEMA:
            raise InputContractError(f"E040 state index has an unexpected schema: {index_path}")
        state_commit = _required_string(state_index, "state_commit_id", f"E040 state index {expected_index_file}")
        parent_commit = state_index.get("parent_state_commit_id")
        if parent_commit is not None and not isinstance(parent_commit, str):
            raise InputContractError(f"E040 state index {expected_index_file}: invalid parent_state_commit_id")
        if state_commit != expected_commit or (
            check_expected_parent and parent_commit != expected_parent_commit
        ):
            raise InputContractError(f"E040 state-index lineage mismatch at {expected_index_file}")
        if state_index.get("mesh_order_hash") != pointer_mesh_hash:
            raise InputContractError(f"E040 state index {expected_index_file}: mesh hash differs from pointer")
        if state_index.get("field_route_hash") != pointer_route_hash:
            raise InputContractError(f"E040 state index {expected_index_file}: route hash differs from pointer")

        record_file = _safe_child_name(state_index.get("record_file"), f"E040 state index {expected_index_file} record")
        record_sha = state_index.get("record_sha256")
        _verify_hashed_file(records_dir / record_file, record_sha, f"E040 state record {record_file}")
        evidence_name = _safe_child_name(state_index.get("evidence_dir"), f"E040 state index {expected_index_file} evidence")
        evidence_dir = arm_dir / evidence_name
        if not evidence_dir.is_dir():
            raise InputContractError(f"E040 state index {expected_index_file}: evidence directory is missing")
        artifacts = _verify_artifact_manifest(
            evidence_dir,
            state_index.get("artifact_manifest_file"),
            state_index.get("artifact_manifest_sha256"),
            f"E040 state index {expected_index_file}",
        )

        if not reverse_chain:
            if record_file != pointer_record_file or record_sha != pointer_record_sha:
                raise InputContractError("E040 pointer record does not match its state index")
            if state_index.get("parent_index_file") != pointer_parent_index:
                raise InputContractError("E040 pointer parent index does not match its state index")

        index_phase = state_index.get("phase")
        artifact_receipt: dict[str, Any] | None = None
        if index_phase is None:
            if parent_commit is not None or state_index.get("parent_index_file") is not None:
                raise InputContractError(f"E040 root state index {expected_index_file} has a parent")
        else:
            if not isinstance(index_phase, dict):
                raise InputContractError(f"E040 state index {expected_index_file}: phase must be an object or null")
            step, _, _, _ = phase(index_phase, f"E040 state index {expected_index_file} phase")
            if evidence_name != f"step_{step:03d}":
                raise InputContractError(f"E040 state index {expected_index_file}: evidence directory does not match phase")
            for required_artifact in ("receipt.json", "fields.npz"):
                if required_artifact not in artifacts:
                    raise InputContractError(
                        f"E040 state index {expected_index_file}: manifest lacks {required_artifact}"
                    )
            artifact_receipt = _json_object(evidence_dir / "receipt.json", "E040 artifact receipt")
            if not same_phase(index_phase, artifact_receipt, load_tolerance):
                raise InputContractError(f"E040 artifact receipt phase differs from {expected_index_file}")
            receipt_accepted = artifact_receipt.get("accepted")
            if receipt_accepted not in (None, True):
                raise InputContractError(
                    f"E040 artifact receipt for step {step} is not a pointer-prepared acceptance"
                )
            if artifact_receipt.get("candidate_commit_id") != state_commit:
                raise InputContractError(
                    f"E040 artifact receipt for step {step} does not bind state commit {state_commit}"
                )
            if artifact_receipt.get("accepted_commit_id_before") != parent_commit:
                raise InputContractError(
                    f"E040 artifact receipt for step {step} does not bind its parent commit"
                )

        reverse_chain.append(
            {
                "index_file": expected_index_file,
                "index_sha256": index_sha,
                "state_commit_id": state_commit,
                "parent_state_commit_id": parent_commit,
                "phase": index_phase,
                "record_file": record_file,
                "record_sha256": record_sha,
                "evidence_dir": evidence_name,
                "artifact_manifest_file": state_index.get("artifact_manifest_file"),
                "artifact_manifest_sha256": state_index.get("artifact_manifest_sha256"),
                "artifact_names": sorted(artifacts),
                "artifact_receipt": artifact_receipt,
            }
        )

        parent_index = state_index.get("parent_index_file")
        if parent_index is None:
            break
        expected_index_file = _safe_child_name(parent_index, f"E040 state index {expected_index_file} parent")
        expected_index_sha = None
        expected_commit = parent_commit if isinstance(parent_commit, str) else ""
        expected_parent_commit = None
        check_expected_parent = False
        if not expected_commit:
            raise InputContractError(f"E040 state index {index_path.name}: parent index lacks parent state commit")

    chain = list(reversed(reverse_chain))
    if not chain or chain[0]["phase"] is not None:
        raise InputContractError("E040 state-index chain must begin with an initial state")
    physical_chain = chain[1:]
    records: list[dict[str, Any]] = []
    receipts_by_step: dict[int, dict[str, Any]] = {}
    for expected_step, entry in enumerate(physical_chain, start=1):
        index_phase = entry["phase"]
        if not isinstance(index_phase, dict) or not isinstance(entry["artifact_receipt"], dict):
            raise InputContractError("E040 physical state index is missing its phase or artifact receipt")
        current_step, _, _, _ = phase(index_phase, "E040 pointer-chain phase")
        if current_step != expected_step:
            raise InputContractError(
                f"E040 accepted state-index chain skips or reorders physical step {expected_step}"
            )
        artifact_receipt = dict(entry["artifact_receipt"])
        authoritative = dict(artifact_receipt)
        authoritative.update(
            accepted=True,
            acceptance_status="committed_by_accepted_state_pointer",
            accepted_commit_id_after=entry["state_commit_id"],
            candidate_state_index_file=entry["index_file"],
            candidate_state_index_sha256=entry["index_sha256"],
            acceptance_authority="accepted_state_pointer_chain",
        )
        records.append(authoritative)
        receipts_by_step[current_step] = authoritative

    audit_entries = []
    for entry in chain:
        audit_entries.append({key: value for key, value in entry.items() if key != "artifact_receipt"})
    audit = {
        "schema": "S04-E040-pointer-chain-audit-v1",
        "accepted_state_pointer": {
            "path": str(pointer_path),
            "sha256": sha256_file(pointer_path),
            "accepted_commit_id": pointer_commit,
            "parent_commit_id": pointer_parent_commit,
            "state_index_file": pointer_index_file,
            "mesh_order_hash": pointer_mesh_hash,
            "field_route_hash": pointer_route_hash,
        },
        "state_indices": audit_entries,
        "accepted_physical_steps": [phase(record, "E040 accepted record")[0] for record in records],
    }
    return records, receipts_by_step, audit


def _validate_global_e040_acceptance(
    global_record: dict[str, Any],
    pointer_record: dict[str, Any],
    load_tolerance: float,
) -> None:
    if not same_phase(global_record, pointer_record, load_tolerance):
        raise InputContractError("E040 steps.json accepted record phase differs from pointer-authoritative receipt")
    pointer_commit = pointer_record["accepted_commit_id_after"]
    for key in ("candidate_commit_id", "accepted_commit_id_after"):
        if key in global_record and global_record[key] not in (None, pointer_commit):
            raise InputContractError(f"E040 steps.json accepted record has conflicting {key}")
    for key in ("arm", "stop_reason", "updates", "max_updates", "metrics", "accepted_commit_id_before"):
        if key in global_record and key in pointer_record and global_record[key] != pointer_record[key]:
            raise InputContractError(f"E040 steps.json accepted record conflicts with immutable artifact field {key!r}")


def load_e040_candidate_records(
    arm_dir: Path,
    load_tolerance: float,
) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], dict[str, Any]]:
    """Merge optional global completion receipts with pointer-authoritative states.

    ``steps.json`` is only a post-pointer convenience receipt.  It supplies a
    full step wall time when it exists, while the immutable artifact receipt
    supplies physical metrics.  A crash before that global file is written can
    therefore still be analysed from the committed pointer chain.
    """
    pointer_records, receipts_by_step, chain_audit = _validate_pointer_index_chain(arm_dir, load_tolerance)
    records_by_step = {phase(record, "E040 pointer record")[0]: dict(record) for record in pointer_records}
    steps_path = arm_dir / "steps.json"
    chain_audit["steps_json"] = {"present": steps_path.is_file()}
    if not steps_path.is_file():
        chain_audit["steps_json"].update(
            recovery="pointer_chain_only_after_missing_or_unwritten_steps_json",
            accepted_records_derived_from_pointer=len(pointer_records),
        )
        return ordered_records(list(records_by_step.values()), "candidate pointer chain"), receipts_by_step, chain_audit

    global_records = ordered_records(require_records(arm_dir), "candidate steps.json")
    global_by_step = {phase(record, "candidate steps.json record")[0]: record for record in global_records}
    missing_global_steps: list[int] = []
    superseded_unaccepted_steps: list[int] = []
    for step, pointer_record in records_by_step.items():
        global_record = global_by_step.get(step)
        if global_record is None:
            missing_global_steps.append(step)
            continue
        if accepted(global_record, f"candidate steps.json step {step}"):
            _validate_global_e040_acceptance(global_record, pointer_record, load_tolerance)
            if "step_elapsed_seconds" in global_record and global_record["step_elapsed_seconds"] is not None:
                receipts_by_step[step]["step_elapsed_seconds"] = _required_float(
                    global_record, "step_elapsed_seconds", f"candidate steps.json step {step}"
                )
                receipts_by_step[step]["timing_source"] = "steps.json_post_pointer_receipt"
        else:
            # The pointer is the sole acceptance authority.  A torn/stale
            # global receipt cannot turn an already published state into a
            # rejected one.
            superseded_unaccepted_steps.append(step)

    nonpointer_records: list[dict[str, Any]] = []
    for global_record in global_records:
        step = phase(global_record, "candidate steps.json record")[0]
        if step in records_by_step:
            continue
        if accepted(global_record, f"candidate steps.json step {step}"):
            raise InputContractError(
                f"E040 steps.json marks step {step} accepted but it is absent from the accepted-state pointer chain"
            )
        # A rejected terminal is not pointer-governed.  Preserve the existing
        # strict global/per-step receipt behaviour for it.
        receipt_for(arm_dir, global_record, "candidate", load_tolerance)
        nonpointer_records.append(global_record)

    chain_audit["steps_json"].update(
        record_count=len(global_records),
        missing_accepted_pointer_steps=missing_global_steps,
        superseded_unaccepted_steps=superseded_unaccepted_steps,
        accepted_records_derived_from_pointer=len(pointer_records),
    )
    return (
        ordered_records([*records_by_step.values(), *nonpointer_records], "candidate"),
        receipts_by_step,
        chain_audit,
    )


def e040_candidate_receipt_for(
    arm_dir: Path,
    record: dict[str, Any],
    receipts_by_step: dict[int, dict[str, Any]],
    load_tolerance: float,
) -> dict[str, Any]:
    """Return manifest-bound evidence for a committed step, otherwise its terminal receipt."""
    step = phase(record, "candidate record")[0]
    if step in receipts_by_step:
        return receipts_by_step[step]
    return receipt_for(arm_dir, record, "candidate", load_tolerance)


def load_fields(
    arm_dir: Path,
    record: dict[str, Any],
    mesh: dict[str, np.ndarray],
    label: str,
) -> dict[str, np.ndarray]:
    path = step_dir(arm_dir, record, label) / "fields.npz"
    try:
        with np.load(path, allow_pickle=False) as archive:
            required = NODE_FIELD_KEYS + ELEMENT_FIELD_KEYS
            missing = [key for key in required if key not in archive.files]
            if missing:
                raise InputContractError(f"{path}: missing required field keys {missing}")
            optional = {"q_raw", "q_ref"}
            fields = {
                key: np.asarray(archive[key], dtype=np.float64)
                for key in set(required).union(optional).intersection(archive.files)
            }
    except FileNotFoundError as exc:
        raise InputContractError(f"Missing paired final field file: {path}") from exc
    except OSError as exc:
        raise InputContractError(f"Cannot read field file {path}: {exc}") from exc

    n_nodes, n_elements = len(mesh["xy"]), len(mesh["triangles"])
    for key in NODE_FIELD_KEYS:
        if fields[key].shape != (n_nodes,):
            raise InputContractError(f"{path}: {key} shape {fields[key].shape} does not match {n_nodes} nodes")
    for key in ELEMENT_FIELD_KEYS:
        if fields[key].shape != (n_elements,):
            raise InputContractError(f"{path}: {key} shape {fields[key].shape} does not match {n_elements} elements")
    for key in (*NODE_FIELD_KEYS, *ELEMENT_FIELD_KEYS):
        if not np.isfinite(fields[key]).all():
            raise InputContractError(f"{path}: {key} has non-finite values")
    return fields


def optional_metric(metrics: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        if key in metrics and metrics[key] is not None:
            try:
                value = float(metrics[key])
            except (TypeError, ValueError) as exc:
                raise InputContractError(f"Metric {key!r} is not numeric") from exc
            if not math.isfinite(value):
                raise InputContractError(f"Metric {key!r} is not finite")
            return value
    return None


def energy_values(receipt: dict[str, Any], label: str, includes_irr: bool) -> dict[str, Any]:
    metrics = receipt.get("metrics")
    if not isinstance(metrics, dict):
        raise InputContractError(f"{label}: receipt has no metrics object")
    e_el = optional_metric(metrics, "E_el")
    e_d = optional_metric(metrics, "E_d")
    e_irr = optional_metric(metrics, "shadow_E_irr", "E_irr")
    l2 = optional_metric(metrics, "weighted_L2")
    if e_el is None or e_d is None or e_irr is None or l2 is None:
        raise InputContractError(
            f"{label}: metrics must contain E_el, E_d, shadow_E_irr (or E_irr), and weighted_L2"
        )
    e_noirr = e_el + e_d
    objective_input = e_noirr + e_irr if includes_irr else e_noirr
    if objective_input <= 0.0:
        raise InputContractError(f"{label}: objective log input must be positive, got {objective_input:.17g}")
    reported_noirr = optional_metric(metrics, "E_noirr")
    return {
        "E_el": e_el,
        "E_d": e_d,
        "shadow_E_irr": e_irr,
        "weighted_L2": l2,
        "E_noirr": e_noirr,
        "reported_E_noirr": reported_noirr,
        "reported_minus_recomputed_E_noirr": None if reported_noirr is None else reported_noirr - e_noirr,
        "E_irr_objective_included": includes_irr,
        "objective_log_input": objective_input,
        "objective_value": math.log10(objective_input) + l2,
    }


def weighted_field_metric(
    reference: np.ndarray,
    candidate: np.ndarray,
    weights: np.ndarray,
) -> dict[str, Any]:
    if reference.shape != candidate.shape or reference.shape != weights.shape:
        raise InputContractError(
            f"Field/support shape mismatch: ref={reference.shape}, candidate={candidate.shape}, weights={weights.shape}"
        )
    if not np.isfinite(reference).all() or not np.isfinite(candidate).all():
        raise InputContractError("Cannot compare non-finite final fields")
    weights = np.asarray(weights, dtype=np.float64)
    if not np.isfinite(weights).all() or np.any(weights < 0.0):
        raise InputContractError("Comparison weights must be finite and non-negative")
    weight_sum = float(weights.sum())
    if weight_sum <= 0.0:
        raise InputContractError("Comparison weights must sum positive")
    delta = candidate - reference
    ref_l2_sq = float(np.sum(weights * reference**2))
    candidate_l2_sq = float(np.sum(weights * candidate**2))
    delta_l2_sq = float(np.sum(weights * delta**2))
    reference_mean = float(np.sum(weights * reference) / weight_sum)
    candidate_mean = float(np.sum(weights * candidate) / weight_sum)
    return {
        "support_weight_sum": weight_sum,
        "reference_weighted_mean": reference_mean,
        "candidate_weighted_mean": candidate_mean,
        "candidate_minus_reference_weighted_mean": candidate_mean - reference_mean,
        "reference_weighted_l2": math.sqrt(ref_l2_sq),
        "candidate_weighted_l2": math.sqrt(candidate_l2_sq),
        "difference_weighted_rms": math.sqrt(delta_l2_sq / weight_sum),
        "difference_maxabs": float(np.max(np.abs(delta))),
        "relative_l2": None if ref_l2_sq == 0.0 else math.sqrt(delta_l2_sq / ref_l2_sq),
        "relative_l2_defined": bool(ref_l2_sq != 0.0),
        "mean_ratio": None if reference_mean == 0.0 else candidate_mean / reference_mean,
        "mean_ratio_defined": bool(reference_mean != 0.0),
        "reference_min": float(reference.min()),
        "reference_max": float(reference.max()),
        "candidate_min": float(candidate.min()),
        "candidate_max": float(candidate.max()),
    }


def field_rows(
    reference_record: dict[str, Any],
    candidate_record: dict[str, Any],
    reference_fields: dict[str, np.ndarray],
    candidate_fields: dict[str, np.ndarray],
    reference_mesh: dict[str, np.ndarray],
) -> list[dict[str, Any]]:
    common = phase_dict(candidate_record, "candidate record")
    element_weights = np.asarray(reference_mesh["area"], dtype=np.float64)
    if "node_weights" not in reference_mesh:
        raise InputContractError("Reference mesh must supply node_weights for the nodal-damage comparison")
    node_weights = np.asarray(reference_mesh["node_weights"], dtype=np.float64)
    if node_weights.shape != reference_fields["d"].shape:
        raise InputContractError("Reference mesh must supply node_weights matching damage nodes")
    quantities = (
        ("damage_d", "node", reference_fields["d"], candidate_fields["d"], node_weights),
        (
            "strain_norm",
            "element",
            np.sqrt(reference_fields["strain_xx"]**2 + reference_fields["strain_yy"]**2 + 2.0 * reference_fields["strain_xy"]**2),
            np.sqrt(candidate_fields["strain_xx"]**2 + candidate_fields["strain_yy"]**2 + 2.0 * candidate_fields["strain_xy"]**2),
            element_weights,
        ),
        ("raw_psi_plus", "element", reference_fields["raw_psi"], candidate_fields["raw_psi"], element_weights),
        ("fatigue_A_trial", "element", reference_fields["trial_A"], candidate_fields["trial_A"], element_weights),
    )
    rows: list[dict[str, Any]] = []
    for quantity, support, reference, candidate, weights in quantities:
        rows.append(
            {
                **common,
                "quantity": quantity,
                "support": support,
                **weighted_field_metric(reference, candidate, weights),
            }
        )
    return rows


def constraint_row(
    arm: str,
    record: dict[str, Any],
    fields: dict[str, np.ndarray],
    mesh: dict[str, np.ndarray],
) -> dict[str, Any]:
    """Report direct nodal and TRI3 Gauss-point bounds from saved final fields."""
    d, h = fields["d"], fields["history_d"]
    delta = d - h
    tri = mesh["triangles"]
    tri_d = d[tri]
    tri_delta = delta[tri]
    gp_d = tri_d @ TRI3_GAUSS_BARYCENTRIC.T
    gp_delta = tri_delta @ TRI3_GAUSS_BARYCENTRIC.T
    row: dict[str, Any] = {
        "arm": arm,
        **phase_dict(record, f"{arm} record"),
        "node_min_d_minus_history_d": float(delta.min()),
        "node_max_d_minus_history_d": float(delta.max()),
        "node_min_d": float(d.min()),
        "node_max_d": float(d.max()),
        "node_lower_violation_count_exact": int(np.count_nonzero(delta < 0.0)),
        "node_upper_violation_count_exact": int(np.count_nonzero(d > 1.0)),
        "tri3_gp_min_d_minus_history_d": float(gp_delta.min()),
        "tri3_gp_max_d_minus_history_d": float(gp_delta.max()),
        "tri3_gp_min_d": float(gp_d.min()),
        "tri3_gp_max_d": float(gp_d.max()),
        "tri3_gp_lower_violation_count_exact": int(np.count_nonzero(gp_delta < 0.0)),
        "tri3_gp_upper_violation_count_exact": int(np.count_nonzero(gp_d > 1.0)),
    }
    if "q_raw" in fields and "q_ref" in fields:
        raw, reference = fields["q_raw"], fields["q_ref"]
        if raw.shape != d.shape or reference.shape != d.shape:
            raise InputContractError("q_raw and q_ref must match nodal damage shape")
        if not np.isfinite(raw).all() or not np.isfinite(reference).all():
            raise InputContractError("q_raw or q_ref contains non-finite values")
        increment = raw - reference
        row.update(
            {
                "q_minus_q_ref_min": float(increment.min()),
                "q_minus_q_ref_max": float(increment.max()),
                "q_le_q_ref_node_fraction": float(np.mean(increment <= 0.0)),
                "q_gt_q_ref_node_fraction": float(np.mean(increment > 0.0)),
            }
        )
    return row


def terminal_field_summary(arm_dir: Path, record: dict[str, Any], mesh: dict[str, np.ndarray], label: str) -> dict[str, Any]:
    """Summarise a non-paired terminal field if it was written, without comparing it."""
    path = step_dir(arm_dir, record, label) / "fields.npz"
    summary: dict[str, Any] = {"fields_path": str(path), "fields_available": path.is_file()}
    if not path.is_file():
        return summary
    try:
        with np.load(path, allow_pickle=False) as archive:
            for key in ("d", "history_d", "raw_psi", "trial_A"):
                if key in archive.files:
                    values = np.asarray(archive[key], dtype=np.float64)
                    summary[f"{key}_finite"] = bool(np.isfinite(values).all())
                    if values.size and np.isfinite(values).all():
                        summary[f"{key}_min"] = float(values.min())
                        summary[f"{key}_max"] = float(values.max())
            if "d" in archive.files and "history_d" in archive.files:
                d = np.asarray(archive["d"], dtype=np.float64)
                h = np.asarray(archive["history_d"], dtype=np.float64)
                if d.shape == h.shape and np.isfinite(d).all() and np.isfinite(h).all():
                    summary["d_minus_history_d_min"] = float((d - h).min())
    except (OSError, ValueError) as exc:
        summary["fields_read_error"] = str(exc)
    return summary


def continuous_prefix(
    reference_records: list[dict[str, Any]],
    candidate_records: list[dict[str, Any]],
    load_tolerance: float,
) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], dict[str, Any]]:
    """Return only the beginning of the candidate trajectory that is comparable."""
    if any(not accepted(record, "reference record") for record in reference_records):
        raise InputContractError("Reference arm contains an unaccepted record; it is not a completed control trajectory")

    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for index, reference in enumerate(reference_records):
        expected = phase_dict(reference, "reference record")
        if index >= len(candidate_records):
            return pairs, {
                "kind": "missing_candidate_record",
                "expected_reference_phase": expected,
                "candidate_record_index": index,
            }
        candidate = candidate_records[index]
        observed = phase_dict(candidate, "candidate record")
        if not same_phase(reference, candidate, load_tolerance):
            return pairs, {
                "kind": "phase_mismatch",
                "expected_reference_phase": expected,
                "candidate_phase": observed,
                "candidate_record_index": index,
                "candidate_record": candidate,
            }
        if not accepted(candidate, "candidate record"):
            return pairs, {
                "kind": "unaccepted_record",
                "expected_reference_phase": expected,
                "candidate_phase": observed,
                "candidate_record_index": index,
                "candidate_record": candidate,
            }
        pairs.append((reference, candidate))

    if len(candidate_records) > len(reference_records):
        extra = candidate_records[len(reference_records)]
        return pairs, {
            "kind": "extra_candidate_record_after_reference",
            "candidate_record_index": len(reference_records),
            "candidate_phase": phase_dict(extra, "candidate record"),
            "candidate_record": extra,
        }
    return pairs, {"kind": "none", "message": "Candidate accepted the full reference horizon."}


def _receipt_metric_row(
    reference_receipt: dict[str, Any],
    candidate_receipt: dict[str, Any],
    candidate_record: dict[str, Any],
) -> dict[str, Any]:
    ref = energy_values(reference_receipt, "reference receipt", includes_irr=True)
    new = energy_values(candidate_receipt, "candidate receipt", includes_irr=False)
    return {
        **phase_dict(candidate_record, "candidate record"),
        **{f"reference_{key}": value for key, value in ref.items()},
        **{f"candidate_{key}": value for key, value in new.items()},
        "candidate_minus_reference_E_noirr": new["E_noirr"] - ref["E_noirr"],
        "candidate_to_reference_E_noirr_ratio": new["E_noirr"] / ref["E_noirr"] if ref["E_noirr"] != 0.0 else None,
        "objective_definition_note": (
            "reference=log10(E_el+E_d+shadow_E_irr)+weighted_L2; "
            "candidate=log10(E_el+E_d)+weighted_L2"
        ),
    }


def _timing_row(
    reference_receipt: dict[str, Any],
    candidate_receipt: dict[str, Any],
    candidate_record: dict[str, Any],
) -> dict[str, Any] | None:
    """Return comparable wall time only when post-pointer timing was persisted.

    E040's manifest-bound artifact receipt is written before pointer
    publication.  It records physical metrics but intentionally does not call
    its pre-evidence duration a full step wall time.  If a crash leaves no
    ``steps.json`` completion receipt, field/energy comparison remains valid
    while timing is explicitly unavailable.
    """
    ref_seconds = _required_float(reference_receipt, "step_elapsed_seconds", "reference receipt")
    if candidate_receipt.get("step_elapsed_seconds") is None:
        return None
    new_seconds = _required_float(candidate_receipt, "step_elapsed_seconds", "candidate receipt")
    ref_updates = _required_float(reference_receipt, "updates", "reference receipt")
    new_updates = _required_float(candidate_receipt, "updates", "candidate receipt")
    return {
        **phase_dict(candidate_record, "candidate record"),
        "reference_updates": int(ref_updates) if ref_updates.is_integer() else ref_updates,
        "candidate_updates": int(new_updates) if new_updates.is_integer() else new_updates,
        "reference_step_elapsed_seconds": ref_seconds,
        "candidate_step_elapsed_seconds": new_seconds,
        "candidate_minus_reference_seconds": new_seconds - ref_seconds,
        "candidate_to_reference_seconds_ratio": new_seconds / ref_seconds if ref_seconds != 0.0 else None,
        "candidate_timing_source": candidate_receipt.get("timing_source", "candidate_receipt"),
    }


def analyze(reference_input: Path, candidate_input: Path, output: Path, load_tolerance: float) -> dict[str, Any]:
    if not math.isfinite(load_tolerance) or load_tolerance < 0.0:
        raise InputContractError("load tolerance must be a finite non-negative number")

    reference_arm = resolve_arm_dir(reference_input, "original")
    candidate_arm = resolve_e040_candidate_arm_dir(candidate_input)
    reference_mesh_path = resolve_mesh_path(reference_input, reference_arm)
    candidate_mesh_path = resolve_mesh_path(candidate_input, candidate_arm)
    reference_mesh = load_mesh(reference_mesh_path)
    candidate_mesh = load_mesh(candidate_mesh_path)
    mesh_report = strict_mesh_check(reference_mesh, candidate_mesh)

    reference_records = ordered_records(require_records(reference_arm), "reference")
    candidate_records, candidate_receipts_by_step, candidate_chain_audit = load_e040_candidate_records(
        candidate_arm, load_tolerance
    )
    pairs, terminal = continuous_prefix(reference_records, candidate_records, load_tolerance)

    output.mkdir(parents=True, exist_ok=True)
    dump_json(output / "candidate_state_chain.json", candidate_chain_audit)
    dump_json(
        output / "input_provenance.json",
        {
            "reference_input": str(reference_input.resolve()),
            "candidate_input": str(candidate_input.resolve()),
            "reference_arm": str(reference_arm),
            "candidate_arm": str(candidate_arm),
            "reference_mesh": str(reference_mesh_path),
            "candidate_mesh": str(candidate_mesh_path),
            "reference_mesh_sha256": sha256_file(reference_mesh_path),
            "candidate_mesh_sha256": sha256_file(candidate_mesh_path),
            "strict_mesh_check": mesh_report,
            "load_absolute_tolerance": load_tolerance,
            "reference_reexecuted": False,
            "candidate_accepted_state_authority": "accepted_state_pointer_chain",
            "candidate_steps_json_present": candidate_chain_audit["steps_json"]["present"],
        },
    )

    field_output: list[dict[str, Any]] = []
    energy_output: list[dict[str, Any]] = []
    timing_output: list[dict[str, Any]] = []
    timing_unavailable: list[dict[str, Any]] = []
    constraint_output: list[dict[str, Any]] = []
    for reference_record, candidate_record in pairs:
        reference_receipt = receipt_for(reference_arm, reference_record, "reference", load_tolerance)
        candidate_receipt = e040_candidate_receipt_for(
            candidate_arm, candidate_record, candidate_receipts_by_step, load_tolerance
        )
        reference_fields = load_fields(reference_arm, reference_record, reference_mesh, "reference")
        candidate_fields = load_fields(candidate_arm, candidate_record, candidate_mesh, "candidate")
        field_output.extend(field_rows(reference_record, candidate_record, reference_fields, candidate_fields, reference_mesh))
        energy_output.append(_receipt_metric_row(reference_receipt, candidate_receipt, candidate_record))
        timing_row = _timing_row(reference_receipt, candidate_receipt, candidate_record)
        if timing_row is None:
            timing_unavailable.append(
                {
                    **phase_dict(candidate_record, "candidate record"),
                    "reason": "no post_pointer_step_elapsed_seconds",
                }
            )
        else:
            timing_output.append(timing_row)
        constraint_output.extend(
            (
                constraint_row("reference", reference_record, reference_fields, reference_mesh),
                constraint_row("candidate", candidate_record, candidate_fields, candidate_mesh),
            )
        )

    terminal_output = dict(terminal)
    terminal_record = terminal.get("candidate_record")
    if isinstance(terminal_record, dict):
        terminal_output["receipt"] = e040_candidate_receipt_for(
            candidate_arm, terminal_record, candidate_receipts_by_step, load_tolerance
        )
        terminal_output["field_summary"] = terminal_field_summary(candidate_arm, terminal_record, candidate_mesh, "candidate")
        terminal_output["not_used_in_field_or_timing_comparison"] = True
    terminal_index = terminal.get("candidate_record_index")
    if isinstance(terminal_index, int):
        tail = candidate_records[terminal_index + 1 :]
        terminal_output["candidate_records_after_terminal_count"] = len(tail)
        terminal_output["candidate_phases_after_terminal"] = [
            phase_dict(record, "candidate trailing record") for record in tail
        ]
    terminal_output["common_accepted_prefix_steps"] = len(pairs)
    dump_json(output / "terminal_trial.json", terminal_output)

    write_csv(
        output / "paired_fields.csv",
        field_output,
        default_keys=("step", "cycle", "substep", "load", "quantity", "support", "relative_l2"),
    )
    write_csv(
        output / "paired_energies.csv",
        energy_output,
        default_keys=("step", "cycle", "substep", "load", "reference_E_noirr", "candidate_E_noirr"),
    )
    write_csv(
        output / "timing.csv",
        timing_output,
        default_keys=("step", "cycle", "substep", "load", "reference_step_elapsed_seconds", "candidate_step_elapsed_seconds"),
    )
    write_csv(
        output / "constraint_state.csv",
        constraint_output,
        default_keys=("arm", "step", "cycle", "substep", "load", "node_min_d_minus_history_d"),
    )

    timing_complete = len(timing_output) == len(pairs)
    reference_seconds = sum(float(row["reference_step_elapsed_seconds"]) for row in timing_output)
    candidate_seconds = sum(float(row["candidate_step_elapsed_seconds"]) for row in timing_output)
    timing_summary = {
        "comparison_scope": "continuous common accepted prefix only",
        "common_accepted_prefix_steps": len(pairs),
        "timing_rows_available": len(timing_output),
        "timing_complete_for_common_prefix": timing_complete,
        "timing_unavailable_phases": timing_unavailable,
        "reference_seconds_common_prefix": reference_seconds if timing_complete else None,
        "candidate_seconds_common_prefix": candidate_seconds if timing_complete else None,
        "candidate_minus_reference_seconds_common_prefix": (
            candidate_seconds - reference_seconds if timing_complete else None
        ),
        "candidate_to_reference_seconds_ratio_common_prefix": (
            candidate_seconds / reference_seconds if timing_complete and reference_seconds != 0.0 else None
        ),
        "speed_claim_supported": bool(
            timing_complete and terminal["kind"] == "none" and len(pairs) == len(reference_records)
        ),
    }
    dump_json(output / "timing_summary.json", timing_summary)

    summary = {
        "analysis_status": "complete",
        "comparison_scope": "continuous common accepted prefix only",
        "reference_records": len(reference_records),
        "candidate_records": len(candidate_records),
        "common_accepted_prefix_steps": len(pairs),
        "reference_horizon_completed_by_candidate": bool(
            terminal["kind"] == "none" and len(pairs) == len(reference_records)
        ),
        "terminal_kind": terminal["kind"],
        "objective_distinction": {
            "reference_E_irr_objective_included": True,
            "candidate_E_irr_objective_included": False,
            "reference_formula": "log10(E_el + E_d + shadow_E_irr) + weighted_L2",
            "candidate_formula": "log10(E_el + E_d) + weighted_L2",
        },
        "outputs": {
            "input_provenance": "input_provenance.json",
            "candidate_state_chain": "candidate_state_chain.json",
            "paired_fields": "paired_fields.csv",
            "paired_energies": "paired_energies.csv",
            "timing": "timing.csv",
            "timing_summary": "timing_summary.json",
            "constraint_state": "constraint_state.csv",
            "terminal_trial": "terminal_trial.json",
        },
        "timing": timing_summary,
    }
    dump_json(output / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reference",
        required=True,
        type=Path,
        help="R001 original arm directory, or raw_producer directory containing original/ and mesh.npz",
    )
    parser.add_argument(
        "--candidate",
        required=True,
        type=Path,
        help="E040 output directory containing feasible_damage/ and mesh.npz, or feasible_damage/ directly",
    )
    parser.add_argument("--output", required=True, type=Path, help="New analysis output directory")
    parser.add_argument(
        "--load-abs-tolerance",
        type=float,
        default=LOAD_ABS_TOLERANCE,
        help=f"absolute load tolerance for phase pairing (default: {LOAD_ABS_TOLERANCE:g})",
    )
    args = parser.parse_args()
    try:
        summary = analyze(args.reference, args.candidate, args.output, args.load_abs_tolerance)
    except InputContractError as exc:
        parser.error(str(exc))
    print(json.dumps(_json_safe(summary), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
