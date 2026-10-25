#!/usr/bin/env python3
"""Read-only S04-E042 versus fixed R001 and E040 trajectory comparison.

This analyzer accepts three already-produced archives:

* the frozen S04-E037 R001 original trajectory;
* the completed S04-E040 feasible-damage trajectory; and
* one S04-E042 projected-damage trajectory.

It does not run a solver or modify any input.  Before reading a field, it
verifies the fixed R001 byte identity, the E040 pointer/index/manifest chain,
and the E042 pointer/index/manifest chain plus its launcher-written identity
receipt.  It then pairs only the common accepted prefix at the declared
Umax=0.12 cyclic phase identity.  Outputs are descriptive PIDL-to-PIDL field
and wall-time comparisons.  They are not a FEM agreement, physical-validity,
or global-convergence conclusion.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_R001_IDENTITY = ROOT / "docs" / "research" / "S04" / "S04-E042" / "r001_reference_identity.json"
DEFAULT_E040_CONTRACT = ROOT / "docs" / "research" / "S04" / "S04-E042" / "e040_reference_contract.json"

LOAD_ABS_TOLERANCE = 1.0e-7
UMAX = 0.12
LOAD_FACTORS = (0.25, 0.5, 0.75, 1.0, 0.0)
CYCLES = 3
SUBSTEPS_PER_CYCLE = len(LOAD_FACTORS)
TOTAL_STEPS = CYCLES * SUBSTEPS_PER_CYCLE

R001_IDENTITY_SCHEMA = "S04-E042-fixed-r001-reference-identity-v1"
E040_CONTRACT_SCHEMA = "S04-E042-fixed-e040-reference-contract-v1"
E042_IDENTITY_SCHEMA = "S04-E042-analysis-identity-receipt-v1"

E040_POINTER_SCHEMA = "S04-E040-accepted-state-pointer-v1"
E040_INDEX_SCHEMA = "S04-E040-state-index-v2"
E040_MANIFEST_SCHEMA = "S04-E040-artifact-manifest-v1"
E042_POINTER_SCHEMA = "S04-E042-accepted-state-pointer-v1"
E042_INDEX_SCHEMA = "S04-E042-state-index-v1"
E042_MANIFEST_SCHEMA = "S04-E042-artifact-manifest-v1"
E042_RESULT_LINKAGE_SCHEMA = "S04-E042-analysis-result-linkage-receipt-v2"

REQUIRED_FIELD_KEYS = (
    "d",
    "history_d",
    "history_A",
    "history_prev",
    "strain_xx",
    "strain_yy",
    "strain_xy",
    "raw_psi",
    "active_driver",
    "trial_A",
)
MESH_KEYS = ("xy", "triangles", "area", "node_weights")
HISTORY_HANDOFF_KEYS = ("history_d", "history_A", "history_prev")


def _route_hash(route: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(route, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


EXPECTED_E040_ROUTE_HASH = _route_hash(
    {
        "raw_damage_input": "FieldComputation.net_output[:,2]",
        "williams_enabled": False,
        "symmetry_prior": False,
        "local_patch_enabled": False,
        "ansatz_enabled": False,
        "exact_bc_enabled": False,
    }
)
EXPECTED_E042_ROUTE_HASH = _route_hash(
    {
        "raw_damage_input": "FieldComputation.net_output[:,2]",
        "damage_carrier": "reference_base_eta_projected_v1",
        "theta_damage_mode": "hold_damage",
        "eta_damage_mode": "direct_damage",
        "williams_enabled": False,
        "symmetry_prior": False,
        "local_patch_enabled": False,
        "ansatz_enabled": False,
        "exact_bc_enabled": False,
    }
)


class InputContractError(RuntimeError):
    """An archive is incomplete, mismatched, or cannot support pairing."""


@dataclass(frozen=True)
class ArchiveLocation:
    label: str
    supplied: Path
    result_root: Path
    archive_root: Path
    arm_dir: Path
    mesh_path: Path


@dataclass
class PointerTrajectory:
    records: list[dict[str, Any]]
    receipts_by_step: dict[int, dict[str, Any]]
    audit: dict[str, Any]
    mesh_order_hash: str
    field_route_hash: str


def _json_safe(value: Any) -> Any:
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
    keys = list(dict.fromkeys((*default_keys, *(key for row in rows for key in row))))
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows([_json_safe(row) for row in rows])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except FileNotFoundError as exc:
        raise InputContractError(f"Missing required input: {path}") from exc
    return digest.hexdigest()


def read_json(path: Path, context: str) -> Any:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise InputContractError(f"{context}: missing JSON file {path}") from exc
    except json.JSONDecodeError as exc:
        raise InputContractError(f"{context}: invalid JSON in {path}: {exc}") from exc


def json_object(path: Path, context: str) -> dict[str, Any]:
    value = read_json(path, context)
    if not isinstance(value, dict):
        raise InputContractError(f"{context}: expected one JSON object in {path}")
    return value


def json_list(path: Path, context: str) -> list[dict[str, Any]]:
    value = read_json(path, context)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise InputContractError(f"{context}: expected a JSON list of objects in {path}")
    return list(value)


def require_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise InputContractError(f"{context}: expected a non-empty string")
    return value


def require_sha256(value: Any, context: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise InputContractError(f"{context}: invalid SHA-256")
    return value


def require_safe_child_name(value: Any, context: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or Path(value).name != value
    ):
        raise InputContractError(f"{context}: expected one safe child filename")
    return value


def require_safe_relative_path(value: Any, context: str) -> Path:
    if not isinstance(value, str) or not value:
        raise InputContractError(f"{context}: expected a non-empty relative path")
    path = Path(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise InputContractError(f"{context}: unsafe relative path")
    return path


def verify_hashed_file(path: Path, expected: Any, context: str) -> str:
    expected_sha = require_sha256(expected, f"{context} expected digest")
    if path.is_symlink() or not path.is_file():
        raise InputContractError(f"{context}: expected regular file {path}")
    actual = sha256_file(path)
    if actual != expected_sha:
        raise InputContractError(f"{context}: SHA-256 mismatch for {path}")
    return actual


def required_float(record: Mapping[str, Any], key: str, context: str) -> float:
    try:
        value = float(record[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise InputContractError(f"{context}: missing or nonnumeric {key!r}") from exc
    if not math.isfinite(value):
        raise InputContractError(f"{context}: {key!r} is not finite")
    return value


def required_nonnegative_int(record: Mapping[str, Any], key: str, context: str) -> int:
    value = record.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InputContractError(f"{context}: missing or invalid non-negative integer {key!r}")
    return value


def exact_array_equal(first: np.ndarray, second: np.ndarray) -> bool:
    """Require the same stored dtype as well as elementwise equality."""
    return first.dtype == second.dtype and first.shape == second.shape and bool(np.array_equal(first, second))


def phase(record: Mapping[str, Any], context: str) -> tuple[int, int, int, float]:
    result: list[int] = []
    for key in ("step", "cycle", "substep"):
        try:
            value = int(record[key])
        except (KeyError, TypeError, ValueError) as exc:
            raise InputContractError(f"{context}: missing or noninteger {key!r}") from exc
        if value < 1:
            raise InputContractError(f"{context}: {key!r} must be positive")
        result.append(value)
    return result[0], result[1], result[2], required_float(record, "load", context)


def phase_dict(record: Mapping[str, Any], context: str) -> dict[str, Any]:
    step, cycle, substep, load = phase(record, context)
    return {"step": step, "cycle": cycle, "substep": substep, "load": load, "load_branch": load_branch(substep)}


def accepted(record: Mapping[str, Any], context: str) -> bool:
    value = record.get("accepted")
    if not isinstance(value, bool):
        raise InputContractError(f"{context}: accepted must be a JSON boolean")
    return value


def same_phase(first: Mapping[str, Any], second: Mapping[str, Any], tolerance: float) -> bool:
    first_values = phase(first, "first phase")
    second_values = phase(second, "second phase")
    return first_values[:3] == second_values[:3] and abs(first_values[3] - second_values[3]) <= tolerance


def expected_phase(step: int) -> tuple[int, int, int, float]:
    if not 1 <= step <= TOTAL_STEPS:
        raise InputContractError(f"step {step} is outside the fixed {TOTAL_STEPS}-state horizon")
    cycle = (step - 1) // SUBSTEPS_PER_CYCLE + 1
    substep = (step - 1) % SUBSTEPS_PER_CYCLE + 1
    return step, cycle, substep, UMAX * LOAD_FACTORS[substep - 1]


def load_branch(substep: int) -> str:
    branches = {
        1: "ascending_0.25_umax",
        2: "ascending_0.50_umax",
        3: "ascending_0.75_umax",
        4: "peak_1.00_umax",
        5: "unload_0.00_umax",
    }
    try:
        return branches[substep]
    except KeyError as exc:
        raise InputContractError(f"unknown fixed load branch for substep {substep}") from exc


def validate_fixed_schedule(
    records: list[dict[str, Any]],
    label: str,
    *,
    require_full: bool,
    load_tolerance: float,
) -> None:
    if not records:
        raise InputContractError(f"{label}: no trajectory records")
    if require_full and len(records) != TOTAL_STEPS:
        raise InputContractError(f"{label}: requires exactly {TOTAL_STEPS} records, found {len(records)}")
    if len(records) > TOTAL_STEPS:
        raise InputContractError(f"{label}: has more than {TOTAL_STEPS} fixed-horizon records")
    seen_steps: set[int] = set()
    for ordinal, record in enumerate(records, start=1):
        item_phase = phase(record, f"{label} record #{ordinal}")
        if item_phase[0] in seen_steps:
            raise InputContractError(f"{label}: duplicate physical step {item_phase[0]}")
        seen_steps.add(item_phase[0])
        expected = expected_phase(ordinal)
        if item_phase[:3] != expected[:3] or abs(item_phase[3] - expected[3]) > load_tolerance:
            raise InputContractError(
                f"{label}: record #{ordinal} has phase {item_phase}, expected {expected}"
            )


def resolve_location(provided: Path, arm_name: str, label: str) -> ArchiveLocation:
    supplied = provided.resolve()
    candidates: list[tuple[Path, Path]] = []
    for result_root in (supplied, supplied / "results", supplied.parent if supplied.name == arm_name else supplied):
        if not result_root.is_dir():
            continue
        arm_dir = result_root / arm_name
        if (result_root / "manifest.json").is_file() and arm_dir.is_dir():
            candidates.append((result_root.resolve(), arm_dir.resolve()))
    unique: dict[Path, Path] = {result_root: arm_dir for result_root, arm_dir in candidates}
    if len(unique) != 1:
        rendered = ", ".join(str(path) for path in unique) or str(supplied)
        raise InputContractError(
            f"{label}: could not uniquely locate result root with manifest.json and {arm_name}/ below {rendered}"
        )
    result_root, arm_dir = next(iter(unique.items()))
    archive_root = result_root.parent if (result_root.parent / "producer_preflight.txt").is_file() else result_root
    mesh_path = result_root / "mesh.npz"
    if mesh_path.is_symlink() or not mesh_path.is_file():
        raise InputContractError(f"{label}: missing regular result mesh {mesh_path}")
    return ArchiveLocation(label, supplied, result_root, archive_root, arm_dir, mesh_path)


def find_archive_file(location: ArchiveLocation, name: str, context: str) -> Path:
    candidates = (location.archive_root / name, location.result_root / name)
    found = [candidate for candidate in candidates if candidate.is_file() and not candidate.is_symlink()]
    if len(found) != 1:
        rendered = ", ".join(str(candidate) for candidate in candidates)
        raise InputContractError(f"{context}: expected exactly one regular {name}; checked {rendered}")
    return found[0]


def parse_key_value_receipt(path: Path, context: str) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        raise InputContractError(f"{context}: expected regular text receipt {path}")
    values: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text().splitlines(), start=1):
        if not raw:
            continue
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        if not key or key in values:
            raise InputContractError(f"{context}: malformed or duplicate key at line {line_number}")
        values[key] = value
    if not values:
        raise InputContractError(f"{context}: no key=value lines in {path}")
    return values


def load_mesh(path: Path, context: str) -> dict[str, np.ndarray]:
    try:
        with np.load(path, allow_pickle=False) as archive:
            missing = [key for key in MESH_KEYS if key not in archive.files]
            if missing:
                raise InputContractError(f"{context}: mesh lacks keys {missing}")
            mesh = {key: np.asarray(archive[key]) for key in MESH_KEYS}
    except OSError as exc:
        raise InputContractError(f"{context}: cannot read mesh {path}: {exc}") from exc
    xy, triangles, area, node_weights = mesh["xy"], mesh["triangles"], mesh["area"], mesh["node_weights"]
    if xy.ndim != 2 or xy.shape[1] != 2:
        raise InputContractError(f"{context}: xy must have shape (n_nodes,2), got {xy.shape}")
    if triangles.ndim != 2 or triangles.shape[1] != 3 or not np.issubdtype(triangles.dtype, np.integer):
        raise InputContractError(f"{context}: triangles must be an integer (n_elements,3) array")
    if area.shape != (len(triangles),) or node_weights.shape != (len(xy),):
        raise InputContractError(f"{context}: mesh area/node_weights dimensions do not match support")
    if not np.isfinite(xy).all() or not np.isfinite(area).all() or not np.isfinite(node_weights).all():
        raise InputContractError(f"{context}: mesh contains non-finite values")
    if np.any(area <= 0.0) or np.any(node_weights <= 0.0):
        raise InputContractError(f"{context}: mesh area and node_weights must be strictly positive")
    if triangles.size and (triangles.min() < 0 or triangles.max() >= len(xy)):
        raise InputContractError(f"{context}: triangles contain out-of-range node indices")
    return mesh


def strict_mesh_check(named_meshes: Mapping[str, dict[str, np.ndarray]]) -> dict[str, Any]:
    labels = list(named_meshes)
    reference_label = labels[0]
    reference = named_meshes[reference_label]
    report: dict[str, Any] = {"reference": reference_label, "comparisons": {}}
    for label in labels[1:]:
        candidate = named_meshes[label]
        comparison: dict[str, Any] = {}
        for key in MESH_KEYS:
            dtype_equal = reference[key].dtype == candidate[key].dtype
            identical = exact_array_equal(reference[key], candidate[key])
            comparison[f"{key}_dtype_equal"] = bool(dtype_equal)
            comparison[f"{key}_bitwise_equal"] = bool(identical)
            if not identical:
                raise InputContractError(f"strict mesh mismatch: {label}.{key} differs from {reference_label}.{key}")
        report["comparisons"][label] = comparison
    return report


def verify_artifact_manifest(
    evidence_dir: Path,
    manifest_file: Any,
    expected_sha256: Any,
    schema: str,
    context: str,
) -> dict[str, dict[str, Any]]:
    name = require_safe_child_name(manifest_file, f"{context} artifact manifest")
    manifest_path = evidence_dir / name
    verify_hashed_file(manifest_path, expected_sha256, f"{context} artifact manifest")
    manifest = json_object(manifest_path, f"{context} artifact manifest")
    if manifest.get("schema") != schema:
        raise InputContractError(f"{context}: unexpected artifact manifest schema")
    raw_entries = manifest.get("artifacts")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise InputContractError(f"{context}: artifact manifest has no entries")
    entries: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(raw_entries):
        if not isinstance(entry, dict):
            raise InputContractError(f"{context}: malformed artifact entry #{index}")
        name = require_safe_child_name(entry.get("name"), f"{context} artifact #{index}")
        if name in entries:
            raise InputContractError(f"{context}: duplicate artifact name {name!r}")
        byte_count = entry.get("bytes")
        if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count < 0:
            raise InputContractError(f"{context}: invalid byte count for {name}")
        artifact = evidence_dir / name
        verify_hashed_file(artifact, entry.get("sha256"), f"{context} artifact {name}")
        if artifact.stat().st_size != byte_count:
            raise InputContractError(f"{context}: artifact byte count mismatch for {name}")
        entries[name] = entry
    return entries


def _pointer_record(
    artifact_receipt: dict[str, Any],
    *,
    state_commit: str,
    parent_commit: str | None,
    arm_name: str,
    expected_carrier: str | None,
    context: str,
    load_tolerance: float,
) -> dict[str, Any]:
    if artifact_receipt.get("arm") != arm_name:
        raise InputContractError(f"{context}: wrong arm name")
    if expected_carrier is not None and artifact_receipt.get("damage_carrier") != expected_carrier:
        raise InputContractError(f"{context}: wrong damage carrier")
    if artifact_receipt.get("accepted") not in (None, True):
        raise InputContractError(f"{context}: pointer-published state has a rejected artifact receipt")
    if artifact_receipt.get("candidate_commit_id") != state_commit:
        raise InputContractError(f"{context}: artifact receipt does not bind state commit {state_commit}")
    if artifact_receipt.get("accepted_commit_id_before") != parent_commit:
        raise InputContractError(f"{context}: artifact receipt does not bind parent state")
    phase(artifact_receipt, context)
    return dict(artifact_receipt)


def load_pointer_trajectory(
    location: ArchiveLocation,
    *,
    pointer_schema: str,
    index_schema: str,
    artifact_schema: str,
    arm_name: str,
    expected_carrier: str | None,
    expected_route_hash: str,
    load_tolerance: float,
) -> PointerTrajectory:
    pointer_path = location.arm_dir / "accepted_state_pointer.json"
    pointer = json_object(pointer_path, f"{location.label} accepted-state pointer")
    if pointer.get("schema") != pointer_schema:
        raise InputContractError(f"{location.label}: unexpected pointer schema")
    expected_mesh_hash = require_string(pointer.get("mesh_order_hash"), f"{location.label} pointer mesh_order_hash")
    pointer_route_hash = require_string(pointer.get("field_route_hash"), f"{location.label} pointer field_route_hash")
    if pointer_route_hash != expected_route_hash:
        raise InputContractError(f"{location.label}: pointer field route does not match this solver route")
    pointer_index_file = require_safe_child_name(pointer.get("state_index_file"), f"{location.label} pointer state index")
    pointer_index_sha = require_sha256(pointer.get("state_index_sha256"), f"{location.label} pointer state index")
    pointer_commit = require_string(pointer.get("accepted_commit_id"), f"{location.label} pointer accepted commit")
    pointer_parent_commit = pointer.get("parent_commit_id")
    if pointer_parent_commit is not None and not isinstance(pointer_parent_commit, str):
        raise InputContractError(f"{location.label}: pointer parent commit is invalid")
    pointer_record = require_safe_child_name(pointer.get("record_file"), f"{location.label} pointer record")
    pointer_record_sha = require_sha256(pointer.get("record_sha256"), f"{location.label} pointer record")
    pointer_parent_index = pointer.get("parent_index_file")
    if pointer_parent_index is not None:
        require_safe_child_name(pointer_parent_index, f"{location.label} pointer parent index")

    indices_dir = location.arm_dir / "state_indices"
    records_dir = location.arm_dir / "accepted_states"
    if indices_dir.is_symlink() or records_dir.is_symlink() or not indices_dir.is_dir() or not records_dir.is_dir():
        raise InputContractError(f"{location.label}: pointer archive lacks regular state_indices/ or accepted_states/")

    expected_index_file = pointer_index_file
    expected_index_sha = pointer_index_sha
    expected_commit = pointer_commit
    expected_parent_commit = pointer_parent_commit
    is_head = True
    visited: set[str] = set()
    reverse_chain: list[dict[str, Any]] = []
    audit_entries: list[dict[str, Any]] = []

    while True:
        if expected_index_file in visited:
            raise InputContractError(f"{location.label}: state-index chain contains a cycle")
        visited.add(expected_index_file)
        index_path = indices_dir / expected_index_file
        index_sha = verify_hashed_file(index_path, expected_index_sha, f"{location.label} state index")
        state_index = json_object(index_path, f"{location.label} state index")
        if state_index.get("schema") != index_schema:
            raise InputContractError(f"{location.label}: unexpected state-index schema")
        state_commit = require_string(state_index.get("state_commit_id"), f"{location.label} state-index state commit")
        parent_commit = state_index.get("parent_state_commit_id")
        if parent_commit is not None and not isinstance(parent_commit, str):
            raise InputContractError(f"{location.label}: invalid state-index parent commit")
        if state_commit != expected_commit or (is_head and parent_commit != expected_parent_commit):
            raise InputContractError(f"{location.label}: state-index lineage mismatch at {index_path.name}")
        if is_head:
            if state_index.get("record_file") != pointer_record or state_index.get("record_sha256") != pointer_record_sha:
                raise InputContractError(f"{location.label}: pointer record does not match head state index")
            if state_index.get("parent_index_file") != pointer_parent_index:
                raise InputContractError(f"{location.label}: pointer parent index does not match head state index")
        if state_index.get("mesh_order_hash") != expected_mesh_hash:
            raise InputContractError(f"{location.label}: state-index mesh hash differs from pointer")
        if state_index.get("field_route_hash") != pointer_route_hash:
            raise InputContractError(f"{location.label}: state-index route hash differs from pointer")

        record_name = require_safe_child_name(state_index.get("record_file"), f"{location.label} state record")
        record_sha = require_sha256(state_index.get("record_sha256"), f"{location.label} state record")
        record_path = records_dir / record_name
        verify_hashed_file(record_path, record_sha, f"{location.label} state record")
        evidence_name = require_safe_child_name(state_index.get("evidence_dir"), f"{location.label} evidence directory")
        evidence_dir = location.arm_dir / evidence_name
        if evidence_dir.is_symlink() or not evidence_dir.is_dir():
            raise InputContractError(f"{location.label}: evidence directory is missing or unsafe: {evidence_dir}")
        artifacts = verify_artifact_manifest(
            evidence_dir,
            state_index.get("artifact_manifest_file"),
            state_index.get("artifact_manifest_sha256"),
            artifact_schema,
            f"{location.label} state {state_commit}",
        )

        index_phase = state_index.get("phase")
        artifact_receipt: dict[str, Any] | None = None
        if parent_commit is None:
            if index_phase is not None:
                raise InputContractError(f"{location.label}: root state must have null phase")
            if state_commit != "state_000":
                raise InputContractError(f"{location.label}: root state must be state_000")
        else:
            if not isinstance(index_phase, dict):
                raise InputContractError(f"{location.label}: physical state index lacks phase")
            if "receipt.json" not in artifacts or "fields.npz" not in artifacts:
                raise InputContractError(f"{location.label}: physical state manifest lacks receipt.json or fields.npz")
            artifact_receipt = json_object(evidence_dir / "receipt.json", f"{location.label} artifact receipt")
            if not same_phase(index_phase, artifact_receipt, load_tolerance):
                raise InputContractError(f"{location.label}: artifact receipt phase differs from state index")
            artifact_receipt = _pointer_record(
                artifact_receipt,
                state_commit=state_commit,
                parent_commit=parent_commit,
                arm_name=arm_name,
                expected_carrier=expected_carrier,
                context=f"{location.label} artifact receipt for {state_commit}",
                load_tolerance=load_tolerance,
            )
            expected_evidence_dir = f"step_{phase(artifact_receipt, f'{location.label} artifact receipt')[0]:03d}"
            if evidence_name != expected_evidence_dir:
                raise InputContractError(
                    f"{location.label}: pointer state {state_commit} has unexpected evidence directory {evidence_name!r}"
                )
            reverse_chain.append(
                {
                    "state_commit_id": state_commit,
                    "parent_state_commit_id": parent_commit,
                    "index_phase": dict(index_phase),
                    "artifact_receipt": artifact_receipt,
                    "index_file": index_path.name,
                    "index_sha256": index_sha,
                    "record_file": record_name,
                    "record_sha256": record_sha,
                    "evidence_dir": evidence_name,
                    "artifact_manifest_file": state_index.get("artifact_manifest_file"),
                    "artifact_manifest_sha256": state_index.get("artifact_manifest_sha256"),
                }
            )
        audit_entries.append(
            {
                "state_commit_id": state_commit,
                "parent_state_commit_id": parent_commit,
                "index_file": index_path.name,
                "index_sha256": index_sha,
                "record_file": record_name,
                "record_sha256": record_sha,
                "evidence_dir": evidence_name,
                "phase": index_phase,
            }
        )

        parent_index_file = state_index.get("parent_index_file")
        parent_index_sha = state_index.get("parent_index_sha256")
        if parent_index_file is None:
            if parent_index_sha is not None or parent_commit is not None:
                raise InputContractError(f"{location.label}: root state carries a parent")
            break
        parent_index_file = require_safe_child_name(parent_index_file, f"{location.label} state-index parent")
        parent_index_sha = require_sha256(parent_index_sha, f"{location.label} state-index parent")
        if parent_commit is None:
            raise InputContractError(f"{location.label}: non-root state index lacks parent commit")
        expected_index_file = parent_index_file
        expected_index_sha = parent_index_sha
        expected_commit = parent_commit
        is_head = False

    pointer_records = list(reversed(reverse_chain))
    if not pointer_records and pointer_commit != "state_000":
        raise InputContractError(f"{location.label}: pointer head has no physical ancestry")

    pointer_receipts: dict[int, dict[str, Any]] = {}
    for expected_step, entry in enumerate(pointer_records, start=1):
        receipt = entry["artifact_receipt"]
        observed_step = phase(receipt, f"{location.label} pointer receipt")[0]
        if observed_step != expected_step:
            raise InputContractError(f"{location.label}: pointer chain skips/reorders step {expected_step}")
        pointer_receipts[observed_step] = receipt

    steps_path = location.arm_dir / "steps.json"
    global_records = json_list(steps_path, f"{location.label} global steps receipt")
    validate_fixed_schedule(global_records, f"{location.label} global steps receipt", require_full=False, load_tolerance=load_tolerance)
    if not global_records:
        raise InputContractError(f"{location.label}: steps.json is empty")

    accepted_prefix: list[dict[str, Any]] = []
    terminal: dict[str, Any] | None = None
    for ordinal, global_record in enumerate(global_records, start=1):
        global_accepted = accepted(global_record, f"{location.label} global record {ordinal}")
        step = phase(global_record, f"{location.label} global record {ordinal}")[0]
        if global_accepted:
            if terminal is not None:
                raise InputContractError(f"{location.label}: accepted record follows a terminal unaccepted record")
            immutable = pointer_receipts.get(step)
            if immutable is None:
                raise InputContractError(f"{location.label}: global accepted step {step} is absent from pointer chain")
            if not same_phase(global_record, immutable, load_tolerance):
                raise InputContractError(f"{location.label}: global accepted receipt phase differs from pointer receipt")
            if global_record.get("arm") != arm_name:
                raise InputContractError(f"{location.label}: global accepted receipt has wrong arm")
            if expected_carrier is not None and global_record.get("damage_carrier") != expected_carrier:
                raise InputContractError(f"{location.label}: global accepted receipt has wrong carrier")
            if global_record.get("candidate_commit_id") != immutable.get("candidate_commit_id"):
                raise InputContractError(f"{location.label}: global receipt differs from pointer-bound candidate commit")
            if global_record.get("accepted_commit_id_before") != immutable.get("accepted_commit_id_before"):
                raise InputContractError(f"{location.label}: global receipt differs from pointer-bound parent commit")
            if global_record.get("accepted_commit_id_after") != immutable.get("candidate_commit_id"):
                raise InputContractError(f"{location.label}: global receipt does not record the pointer-published state")
            if global_record.get("acceptance_status") != "committed_by_pointer":
                raise InputContractError(f"{location.label}: global accepted receipt lacks pointer-commit status")
            required_float(global_record, "step_elapsed_seconds", f"{location.label} global accepted receipt")
            merged = dict(immutable)
            merged.update(global_record)
            accepted_prefix.append(merged)
        else:
            if terminal is not None:
                raise InputContractError(f"{location.label}: more than one terminal global record")
            terminal = dict(global_record)
            if ordinal != len(global_records):
                raise InputContractError(f"{location.label}: records follow terminal unaccepted state")
    if len(accepted_prefix) != len(pointer_records):
        raise InputContractError(f"{location.label}: pointer and global accepted-state counts differ")

    audit = {
        "schema": "S04-E042-pointer-chain-audit-v1",
        "pointer_file": str(pointer_path),
        "pointer_sha256": sha256_file(pointer_path),
        "pointer_schema": pointer_schema,
        "pointer_accepted_commit_id": pointer_commit,
        "pointer_parent_commit_id": pointer_parent_commit,
        "mesh_order_hash": expected_mesh_hash,
        "field_route_hash": pointer_route_hash,
        "accepted_state_count": len(accepted_prefix),
        "global_steps_sha256": sha256_file(steps_path),
        "global_record_count": len(global_records),
        "terminal_record": terminal,
        "chain": list(reversed(audit_entries)),
    }
    return PointerTrajectory(accepted_prefix, {phase(row, location.label)[0]: row for row in accepted_prefix}, audit, expected_mesh_hash, pointer_route_hash)


def load_fields(location: ArchiveLocation, record: Mapping[str, Any], mesh: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    step = phase(record, f"{location.label} record")[0]
    path = location.arm_dir / f"step_{step:03d}" / "fields.npz"
    try:
        with np.load(path, allow_pickle=False) as archive:
            missing = [key for key in REQUIRED_FIELD_KEYS if key not in archive.files]
            if missing:
                raise InputContractError(f"{location.label}: {path} lacks field keys {missing}")
            fields = {key: np.asarray(archive[key]) for key in REQUIRED_FIELD_KEYS}
    except FileNotFoundError as exc:
        raise InputContractError(f"{location.label}: missing required field artifact {path}") from exc
    except OSError as exc:
        raise InputContractError(f"{location.label}: cannot read field artifact {path}: {exc}") from exc
    n_nodes, n_elements = len(mesh["xy"]), len(mesh["triangles"])
    node_keys = ("d", "history_d")
    element_keys = tuple(key for key in REQUIRED_FIELD_KEYS if key not in node_keys)
    for key in node_keys:
        if fields[key].shape != (n_nodes,):
            raise InputContractError(f"{location.label}: {path} {key} has incorrect node shape")
    for key in element_keys:
        if fields[key].shape != (n_elements,):
            raise InputContractError(f"{location.label}: {path} {key} has incorrect element shape")
    for key, values in fields.items():
        if not np.issubdtype(values.dtype, np.floating):
            raise InputContractError(f"{location.label}: {path} {key} must be a floating-point array")
        if not np.isfinite(values).all():
            raise InputContractError(f"{location.label}: {path} {key} contains non-finite values")
    return fields


def history_continuity(
    location: ArchiveLocation,
    records: list[dict[str, Any]],
    mesh: Mapping[str, np.ndarray],
    *,
    damage_history_rule: str,
) -> list[dict[str, Any]]:
    if damage_history_rule not in {"previous_damage", "max_previous_history_and_damage"}:
        raise ValueError(f"unsupported damage history rule: {damage_history_rule}")
    rows: list[dict[str, Any]] = []
    previous: dict[str, np.ndarray] | None = None
    for record in records:
        fields = load_fields(location, record, mesh)
        row = {
            "arm": location.label,
            "damage_history_rule": damage_history_rule,
            **phase_dict(record, f"{location.label} record"),
        }
        if previous is None:
            row.update(
                predecessor="recovery_state",
                history_d_matches_expected_commit=None,
                history_d_equals_previous_d=None,
                history_d_equals_max_previous_history_and_damage=None,
                history_A_equals_previous_trial_A=None,
                history_prev_equals_previous_active_driver=None,
            )
        else:
            direct_history_d = exact_array_equal(fields["history_d"], previous["d"])
            max_history_d = exact_array_equal(
                fields["history_d"], np.maximum(previous["history_d"], previous["d"])
            )
            expected_history_d = (
                previous["d"]
                if damage_history_rule == "previous_damage"
                else np.maximum(previous["history_d"], previous["d"])
            )
            d_ok = exact_array_equal(fields["history_d"], expected_history_d)
            a_ok = exact_array_equal(fields["history_A"], previous["trial_A"])
            prev_ok = exact_array_equal(fields["history_prev"], previous["active_driver"])
            row.update(
                predecessor=f"step_{phase(record, location.label)[0] - 1:03d}",
                history_d_matches_expected_commit=d_ok,
                history_d_equals_previous_d=direct_history_d,
                history_d_equals_max_previous_history_and_damage=max_history_d,
                history_A_equals_previous_trial_A=a_ok,
                history_prev_equals_previous_active_driver=prev_ok,
                history_d_maxabs_delta=float(np.max(np.abs(fields["history_d"] - previous["d"]))),
                history_d_expected_maxabs_delta=float(
                    np.max(np.abs(fields["history_d"] - expected_history_d))
                ),
                history_A_maxabs_delta=float(np.max(np.abs(fields["history_A"] - previous["trial_A"]))),
                history_prev_maxabs_delta=float(np.max(np.abs(fields["history_prev"] - previous["active_driver"]))),
            )
            if not (d_ok and a_ok and prev_ok):
                raise InputContractError(
                    f"{location.label}: accepted history handoff is not bitwise continuous before step {phase(record, location.label)[0]}"
                )
        rows.append(row)
        previous = fields
    return rows


def initial_history_identity(
    r001_location: ArchiveLocation,
    r001_records: list[dict[str, Any]],
    r001_mesh: Mapping[str, np.ndarray],
    e040_location: ArchiveLocation,
    e040_records: list[dict[str, Any]],
    e040_mesh: Mapping[str, np.ndarray],
    e042_location: ArchiveLocation,
    e042_records: list[dict[str, Any]],
    e042_mesh: Mapping[str, np.ndarray],
) -> dict[str, Any]:
    """Confirm the first accepted E040/E042 step starts from R001's history."""
    if not e042_records:
        return {
            "evaluated": False,
            "reason": "E042 has no pointer-accepted state from which to inspect the initial history",
        }
    first_fields = {
        "R001": load_fields(r001_location, r001_records[0], r001_mesh),
        "E040": load_fields(e040_location, e040_records[0], e040_mesh),
        "E042": load_fields(e042_location, e042_records[0], e042_mesh),
    }
    comparisons: dict[str, dict[str, bool]] = {}
    for label in ("E040", "E042"):
        comparison = {
            key: exact_array_equal(first_fields["R001"][key], first_fields[label][key])
            for key in HISTORY_HANDOFF_KEYS
        }
        comparisons[label] = comparison
        if not all(comparison.values()):
            mismatched = ", ".join(key for key, matched in comparison.items() if not matched)
            raise InputContractError(
                f"initial accepted history mismatch: {label} differs from fixed R001 for {mismatched}"
            )
    return {
        "evaluated": True,
        "reference_phase": phase_dict(r001_records[0], "R001 initial accepted record"),
        "required_history_fields": list(HISTORY_HANDOFF_KEYS),
        "comparisons_to_r001": comparisons,
    }


def weighted_field_metric(reference: np.ndarray, candidate: np.ndarray, weights: np.ndarray) -> dict[str, Any]:
    if reference.shape != candidate.shape or reference.shape != weights.shape:
        raise InputContractError("field/support shape mismatch during paired comparison")
    weights = np.asarray(weights, dtype=np.float64)
    if not np.isfinite(weights).all() or np.any(weights <= 0.0):
        raise InputContractError("paired comparison weights must be finite and strictly positive")
    delta = candidate - reference
    weight_sum = float(weights.sum())
    reference_l2_sq = float(np.sum(weights * reference**2))
    candidate_l2_sq = float(np.sum(weights * candidate**2))
    delta_l2_sq = float(np.sum(weights * delta**2))
    reference_mean = float(np.sum(weights * reference) / weight_sum)
    candidate_mean = float(np.sum(weights * candidate) / weight_sum)
    return {
        "support_weight_sum": weight_sum,
        "reference_weighted_mean": reference_mean,
        "candidate_weighted_mean": candidate_mean,
        "candidate_minus_reference_weighted_mean": candidate_mean - reference_mean,
        "reference_weighted_l2": math.sqrt(reference_l2_sq),
        "candidate_weighted_l2": math.sqrt(candidate_l2_sq),
        "difference_weighted_rms": math.sqrt(delta_l2_sq / weight_sum),
        "difference_maxabs": float(np.max(np.abs(delta))),
        "relative_l2": None if reference_l2_sq == 0.0 else math.sqrt(delta_l2_sq / reference_l2_sq),
        "relative_l2_defined": bool(reference_l2_sq != 0.0),
        "reference_min": float(reference.min()),
        "reference_max": float(reference.max()),
        "candidate_min": float(candidate.min()),
        "candidate_max": float(candidate.max()),
    }


def field_rows(
    comparator_label: str,
    comparator_record: Mapping[str, Any],
    candidate_record: Mapping[str, Any],
    comparator_fields: Mapping[str, np.ndarray],
    candidate_fields: Mapping[str, np.ndarray],
    mesh: Mapping[str, np.ndarray],
) -> list[dict[str, Any]]:
    if not same_phase(comparator_record, candidate_record, LOAD_ABS_TOLERANCE):
        raise InputContractError("internal pairing error: comparator phase differs from candidate phase")
    node_weights = np.asarray(mesh["node_weights"], dtype=np.float64)
    element_weights = np.asarray(mesh["area"], dtype=np.float64)
    quantities = (
        ("damage_d", "node", comparator_fields["d"], candidate_fields["d"], node_weights),
        (
            "strain_norm",
            "element",
            np.sqrt(
                comparator_fields["strain_xx"] ** 2
                + comparator_fields["strain_yy"] ** 2
                + 2.0 * comparator_fields["strain_xy"] ** 2
            ),
            np.sqrt(
                candidate_fields["strain_xx"] ** 2
                + candidate_fields["strain_yy"] ** 2
                + 2.0 * candidate_fields["strain_xy"] ** 2
            ),
            element_weights,
        ),
        ("psi_plus_raw", "element", comparator_fields["raw_psi"], candidate_fields["raw_psi"], element_weights),
        ("fatigue_A_trial", "element", comparator_fields["trial_A"], candidate_fields["trial_A"], element_weights),
    )
    result: list[dict[str, Any]] = []
    for quantity, support, reference, candidate, weights in quantities:
        result.append(
            {
                "comparator": comparator_label,
                **phase_dict(candidate_record, "candidate record"),
                "quantity": quantity,
                "support": support,
                **weighted_field_metric(reference, candidate, weights),
            }
        )
    return result


def timing_row(
    candidate_record: Mapping[str, Any],
    r001_record: Mapping[str, Any],
    e040_record: Mapping[str, Any],
) -> dict[str, Any]:
    for label, record in (("E042", candidate_record), ("R001", r001_record), ("E040", e040_record)):
        if not same_phase(candidate_record, record, LOAD_ABS_TOLERANCE):
            raise InputContractError(f"timing pairing phase mismatch for {label}")
    candidate_seconds = required_float(candidate_record, "step_elapsed_seconds", "E042 timing receipt")
    r001_seconds = required_float(r001_record, "step_elapsed_seconds", "R001 timing receipt")
    e040_seconds = required_float(e040_record, "step_elapsed_seconds", "E040 timing receipt")
    if candidate_seconds <= 0.0 or r001_seconds <= 0.0 or e040_seconds <= 0.0:
        raise InputContractError("timing comparison requires positive per-step elapsed seconds")
    row: dict[str, Any] = {
        **phase_dict(candidate_record, "E042 timing receipt"),
        "r001_step_elapsed_seconds": r001_seconds,
        "e040_step_elapsed_seconds": e040_seconds,
        "e042_step_elapsed_seconds": candidate_seconds,
        "e042_minus_r001_seconds": candidate_seconds - r001_seconds,
        "e042_to_r001_seconds_ratio": candidate_seconds / r001_seconds,
        "e042_minus_e040_seconds": candidate_seconds - e040_seconds,
        "e042_to_e040_seconds_ratio": candidate_seconds / e040_seconds,
        "r001_updates": r001_record.get("updates"),
        "e040_updates": e040_record.get("updates"),
        "e042_theta_rprop_updates": candidate_record.get("theta_rprop_updates"),
        "e042_eta_accepted_updates": candidate_record.get("eta_accepted_updates"),
        "e042_uv_reequilibration_rprop_updates": candidate_record.get("uv_reequilibration_rprop_updates"),
    }
    return row


def _require_exact(value: Any, expected: Any, context: str) -> None:
    if value != expected:
        raise InputContractError(f"{context}: expected {expected!r}, got {value!r}")


def _require_float_exact(value: Any, expected: float, context: str) -> None:
    actual = required_float({"value": value}, "value", context)
    if abs(actual - expected) > 1.0e-12:
        raise InputContractError(f"{context}: expected {expected:.17g}, got {actual:.17g}")


def validate_manifest_schedule(
    manifest: Mapping[str, Any],
    label: str,
    *,
    require_factors: bool = True,
) -> None:
    steps = manifest.get("steps")
    if steps != list(range(1, TOTAL_STEPS + 1)):
        raise InputContractError(f"{label}: manifest must declare the fixed 15-state horizon")
    factors = manifest.get("factors")
    if not isinstance(factors, list) or len(factors) != len(LOAD_FACTORS):
        if require_factors:
            raise InputContractError(f"{label}: manifest lacks the fixed load-factor list")
        return
    for index, expected in enumerate(LOAD_FACTORS):
        _require_float_exact(factors[index], expected, f"{label} load factor {index}")


def validate_r001(
    location: ArchiveLocation,
    identity: Mapping[str, Any],
    load_tolerance: float,
    *,
    identity_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _require_exact(identity.get("schema"), R001_IDENTITY_SCHEMA, "R001 identity schema")
    file_entries = identity.get("files")
    if not isinstance(file_entries, list) or not file_entries:
        raise InputContractError("R001 identity: files must be a non-empty list")
    verified_files: dict[str, str] = {}
    for index, entry in enumerate(file_entries):
        if not isinstance(entry, dict):
            raise InputContractError(f"R001 identity: invalid file entry #{index}")
        relative = require_safe_relative_path(entry.get("path"), f"R001 identity file #{index}")
        text_relative = relative.as_posix()
        if text_relative in verified_files:
            raise InputContractError(f"R001 identity: duplicate file path {text_relative}")
        path = location.result_root / relative
        verified_files[text_relative] = verify_hashed_file(path, entry.get("sha256"), f"fixed R001 {relative}")
        byte_count = entry.get("bytes")
        if not isinstance(byte_count, int) or byte_count < 0 or path.stat().st_size != byte_count:
            raise InputContractError(f"fixed R001 {relative}: byte count differs from identity")
    required_paths = {"manifest.json", "mesh.npz", "original/steps.json"}
    if not required_paths <= set(verified_files):
        raise InputContractError("R001 identity does not seal manifest.json, mesh.npz, and original/steps.json")

    manifest = json_object(location.result_root / "manifest.json", "R001 manifest")
    reference = identity.get("reference")
    if not isinstance(reference, dict):
        raise InputContractError("R001 identity: reference must be an object")
    for key in ("experiment", "protocol", "source_commit", "history"):
        _require_exact(manifest.get(key), reference.get(key), f"R001 manifest {key}")
    if manifest.get("arms") != ["original", "primal_dual"]:
        raise InputContractError("R001 manifest arms do not identify the fixed original trajectory")
    # The fixed R001 manifest predates the explicit `factors` field.  Its
    # independently sealed per-step receipts below still establish every
    # cycle/substep/load value against the fixed schedule.
    validate_manifest_schedule(manifest, "R001 manifest", require_factors=False)
    baseline = require_string(manifest.get("baseline"), "R001 manifest baseline")
    for token in ("U0.12", "current_active", "fem_gp_tri3_g_mean"):
        if token not in baseline:
            raise InputContractError(f"R001 manifest baseline lacks {token!r}")

    records = json_list(location.arm_dir / "steps.json", "R001 steps receipt")
    validate_fixed_schedule(records, "R001 steps receipt", require_full=True, load_tolerance=load_tolerance)
    for record in records:
        if not accepted(record, "R001 record") or record.get("arm") != "original":
            raise InputContractError("R001 must be a complete accepted original trajectory")
        step = phase(record, "R001 record")[0]
        receipt_path = location.arm_dir / f"step_{step:03d}" / "receipt.json"
        if f"original/step_{step:03d}/receipt.json" not in verified_files:
            raise InputContractError(f"R001 identity does not seal receipt for step {step}")
        receipt = json_object(receipt_path, f"R001 receipt step {step}")
        if not same_phase(record, receipt, load_tolerance) or not accepted(receipt, f"R001 receipt step {step}"):
            raise InputContractError(f"R001 receipt phase/acceptance mismatch at step {step}")
        if receipt.get("arm") != "original":
            raise InputContractError(f"R001 receipt has wrong arm at step {step}")
        required_float(receipt, "step_elapsed_seconds", f"R001 receipt step {step}")
        field_key = f"original/step_{step:03d}/fields.npz"
        if field_key not in verified_files:
            raise InputContractError(f"R001 identity does not seal fields for step {step}")
    return records, {
        "identity_file": str(identity_path),
        "identity_sha256": sha256_file(identity_path),
        "sealed_files": verified_files,
        "manifest_sha256": sha256_file(location.result_root / "manifest.json"),
        "mesh_sha256": sha256_file(location.mesh_path),
        "steps_sha256": sha256_file(location.arm_dir / "steps.json"),
    }


def validate_e040_provenance(
    location: ArchiveLocation,
    contract: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    _require_exact(contract.get("schema"), E040_CONTRACT_SCHEMA, "E040 reference contract schema")
    result = contract.get("result")
    package = contract.get("package")
    baseline = contract.get("baseline")
    r001 = contract.get("r001")
    if not all(isinstance(value, dict) for value in (result, package, baseline, r001)):
        raise InputContractError("E040 reference contract has incomplete sections")
    for key in ("experiment", "protocol", "arm"):
        _require_exact(manifest.get(key), result.get(key), f"E040 manifest {key}")
    validate_manifest_schedule(manifest, "E040 manifest")
    _require_exact(manifest.get("source_commit"), package.get("reviewed_runtime_commit"), "E040 manifest source_commit")
    archive_baseline = require_string(manifest.get("baseline"), "E040 manifest baseline")
    for token in ("U0.12", "current_active", "fem_gp_tri3_g_mean"):
        if token not in archive_baseline:
            raise InputContractError(f"E040 manifest baseline lacks {token!r}")

    preflight_path = find_archive_file(location, "producer_preflight.txt", "E040 provenance")
    preflight = parse_key_value_receipt(preflight_path, "E040 producer preflight")
    _require_exact(preflight.get("schema"), package.get("preflight_schema"), "E040 preflight schema")
    _require_exact(preflight.get("run_id"), contract.get("run_id"), "E040 preflight run id")
    _require_exact(preflight.get("reviewed_runtime_commit"), package.get("reviewed_runtime_commit"), "E040 preflight runtime")
    for key in ("model_settings_sha256", "checkpoint_sha256", "network_sha256"):
        _require_exact(preflight.get(key), baseline.get(key), f"E040 preflight {key}")
    _require_exact(preflight.get("r001_steps_sha256"), r001.get("steps_sha256"), "E040 preflight R001 steps")

    package_path = find_archive_file(location, "package_receipt.json", "E040 provenance")
    _require_exact(preflight.get("package_receipt_sha256"), sha256_file(package_path), "E040 preflight package receipt")
    package_receipt = json_object(package_path, "E040 package receipt")
    for key in ("schema", "package_commit", "reviewed_runtime_commit"):
        _require_exact(package_receipt.get(key), package.get(key), f"E040 package receipt {key}")
    runtime_name = require_safe_child_name(package_receipt.get("runtime_manifest_file"), "E040 package runtime manifest")
    runtime_path = find_archive_file(location, runtime_name, "E040 provenance")
    _require_exact(sha256_file(runtime_path), package_receipt.get("runtime_manifest_sha256"), "E040 package runtime manifest hash")
    runtime_manifest = json_object(runtime_path, "E040 reviewed runtime manifest")
    _require_exact(runtime_manifest.get("schema"), package.get("runtime_manifest_schema"), "E040 runtime manifest schema")
    _require_exact(runtime_manifest.get("reviewed_runtime_commit"), package.get("reviewed_runtime_commit"), "E040 runtime manifest commit")
    return {
        "preflight_file": str(preflight_path),
        "preflight_sha256": sha256_file(preflight_path),
        "package_receipt_file": str(package_path),
        "package_receipt_sha256": sha256_file(package_path),
        "runtime_manifest_file": str(runtime_path),
        "runtime_manifest_sha256": sha256_file(runtime_path),
        "manifest_sha256": sha256_file(location.result_root / "manifest.json"),
        "mesh_sha256": sha256_file(location.mesh_path),
    }


def _require_sealed_regular_file(path: Path, context: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise InputContractError(f"{context}: expected a regular file")
    if path.stat().st_mode & 0o222:
        raise InputContractError(f"{context}: receipt is writable, not sealed")


def _result_linkage_file(location: ArchiveLocation, relative: str, expected: Mapping[str, Any], context: str) -> str:
    safe = require_safe_relative_path(relative, context)
    if safe.as_posix() != relative:
        raise InputContractError(f"{context}: noncanonical relative path")
    path = location.result_root / safe
    if path.is_symlink() or not path.is_file():
        raise InputContractError(f"{context}: missing regular result file {path}")
    expected_sha = expected.get("sha256")
    expected_bytes = expected.get("bytes")
    if not isinstance(expected_bytes, int) or expected_bytes < 0:
        raise InputContractError(f"{context}: invalid result byte count")
    if path.stat().st_size != expected_bytes:
        raise InputContractError(f"{context}: result byte count mismatch for {relative}")
    return verify_hashed_file(path, expected_sha, context)


def validate_e042_identity(
    location: ArchiveLocation,
    manifest: Mapping[str, Any],
    r001_provenance: Mapping[str, Any],
) -> dict[str, Any]:
    identity_path = find_archive_file(location, "analysis_identity_receipt.json", "E042 provenance")
    linkage_path = find_archive_file(location, "analysis_result_linkage_receipt.json", "E042 provenance")
    _require_sealed_regular_file(identity_path, "E042 analysis identity receipt")
    _require_sealed_regular_file(linkage_path, "E042 analysis result linkage receipt")
    identity = json_object(identity_path, "E042 analysis identity receipt")
    linkage = json_object(linkage_path, "E042 analysis result linkage receipt")
    _require_exact(identity.get("schema"), E042_IDENTITY_SCHEMA, "E042 identity receipt schema")
    run_id = require_string(identity.get("run_id"), "E042 identity run id")
    _require_exact(identity.get("sealed", {}).get("mode"), "create_once_0444", "E042 identity sealed mode")
    _require_exact(identity.get("sealed", {}).get("archive_root_file"), identity_path.name, "E042 identity filename")

    runtime = identity.get("runtime")
    preflight_identity = identity.get("preflight")
    frozen_inputs = identity.get("frozen_inputs")
    history_timing = identity.get("history_timing")
    result_linkage = identity.get("result_linkage")
    if not all(isinstance(value, dict) for value in (runtime, preflight_identity, frozen_inputs, history_timing, result_linkage)):
        raise InputContractError("E042 identity receipt has incomplete sections")
    _require_exact(result_linkage.get("state"), "pre_run_identity_only", "E042 pre-run identity state")
    _require_exact(result_linkage.get("completion_receipt"), linkage_path.name, "E042 completion receipt name")
    _require_exact(
        result_linkage.get("completion_condition"),
        "written only after runner exit code 0 and result-file hash checks",
        "E042 completion condition",
    )
    _require_exact(history_timing.get("history_driver_mode"), "current_active", "E042 identity history_driver_mode")
    _require_exact(history_timing.get("lagged_stiffness_enabled"), False, "E042 identity lagged_stiffness_enabled")
    _require_exact(history_timing.get("transaction_boundary"), "accepted_only", "E042 identity transaction_boundary")
    _require_exact(history_timing.get("transactions_per_physical_step"), 1, "E042 identity transactions_per_physical_step")
    _require_exact(
        history_timing.get("commit_mechanism"),
        "pointer_last_after_accepted_candidate_bundle",
        "E042 identity commit mechanism",
    )

    package_path = location.archive_root / "package_receipt.json"
    runtime_path = location.archive_root / "reviewed_runtime_manifest.json"
    materialization_path = location.archive_root / "materialization_receipt.json"
    preflight_path = location.archive_root / "producer_preflight.txt"
    for path, context in (
        (package_path, "E042 package receipt"),
        (runtime_path, "E042 reviewed runtime manifest"),
        (materialization_path, "E042 materialization receipt"),
        (preflight_path, "E042 producer preflight"),
    ):
        if path.is_symlink() or not path.is_file():
            raise InputContractError(f"{context}: missing regular archive file")
    package_receipt = json_object(package_path, "E042 package receipt")
    runtime_manifest = json_object(runtime_path, "E042 reviewed runtime manifest")
    materialization = json_object(materialization_path, "E042 materialization receipt")
    preflight = parse_key_value_receipt(preflight_path, "E042 producer preflight")
    _require_exact(package_receipt.get("schema"), "S04-E042-producer-package-receipt-v2", "E042 package receipt schema")
    _require_exact(runtime_manifest.get("schema"), "S04-E042-reviewed-runtime-manifest-v2", "E042 runtime manifest schema")
    reviewed_runtime = require_string(runtime.get("reviewed_runtime_commit"), "E042 identity reviewed runtime")
    _require_exact(package_receipt.get("reviewed_runtime_commit"), reviewed_runtime, "E042 package runtime")
    _require_exact(runtime_manifest.get("reviewed_runtime_commit"), reviewed_runtime, "E042 runtime manifest commit")
    _require_exact(manifest.get("source_commit"), reviewed_runtime, "E042 result manifest source commit")
    _require_exact(runtime.get("package_commit"), package_receipt.get("package_commit"), "E042 identity package commit")
    _require_exact(runtime.get("package_receipt_sha256"), sha256_file(package_path), "E042 identity package receipt hash")
    _require_exact(runtime.get("runtime_manifest_sha256"), sha256_file(runtime_path), "E042 identity runtime manifest hash")
    _require_exact(runtime.get("materialization_receipt_sha256"), sha256_file(materialization_path), "E042 identity materialization receipt hash")
    _require_exact(package_receipt.get("runtime_manifest_file"), runtime_path.name, "E042 runtime manifest filename")
    _require_exact(package_receipt.get("runtime_manifest_sha256"), sha256_file(runtime_path), "E042 package runtime manifest hash")
    _require_exact(materialization.get("package_receipt_sha256"), sha256_file(package_path), "E042 materialization package receipt")
    _require_exact(materialization.get("runtime_manifest_sha256"), sha256_file(runtime_path), "E042 materialization runtime manifest")
    _require_exact(materialization.get("package_commit"), package_receipt.get("package_commit"), "E042 materialization package commit")

    proof = runtime_manifest.get("e042_import_proof")
    _require_exact(runtime.get("e042_import_proof"), proof, "E042 identity import proof")
    if not isinstance(proof, dict):
        raise InputContractError("E042 runtime manifest lacks import proof")
    _require_exact(proof.get("module"), "projected_damage", "E042 import proof module")
    _require_exact(proof.get("symbol"), "ReferenceBaseProjectedDamage", "E042 import proof symbol")
    _require_exact(proof.get("module_path"), "source/projected_damage.py", "E042 import proof module path")
    _require_exact(proof.get("runner_path"), "scripts/run_s04_e042_projected_damage.py", "E042 import proof runner path")
    _require_exact(runtime.get("runner_path"), proof.get("runner_path"), "E042 identity runner path")
    files = runtime_manifest.get("files")
    if not isinstance(files, list):
        raise InputContractError("E042 runtime manifest lacks file list")
    by_path = {item.get("path"): item for item in files if isinstance(item, dict)}
    runner_item = by_path.get(proof["runner_path"])
    carrier_item = by_path.get(proof["module_path"])
    if not isinstance(runner_item, dict) or not isinstance(carrier_item, dict):
        raise InputContractError("E042 runtime manifest does not bind runner and carrier")
    _require_exact(runtime.get("runner_sha256"), runner_item.get("sha256"), "E042 identity runner hash")
    _require_exact(proof.get("module_sha256"), carrier_item.get("sha256"), "E042 import-proof carrier hash")

    _require_exact(preflight_identity.get("file"), preflight_path.name, "E042 identity preflight filename")
    _require_exact(preflight_identity.get("sha256"), sha256_file(preflight_path), "E042 identity preflight hash")
    _require_exact(preflight_identity.get("schema"), "S04-E042-producer-preflight-v2", "E042 identity preflight schema")
    _require_exact(preflight.get("schema"), preflight_identity.get("schema"), "E042 producer preflight schema")
    _require_exact(preflight.get("run_id"), run_id, "E042 producer preflight run id")
    _require_exact(preflight.get("reviewed_runtime_commit"), reviewed_runtime, "E042 producer preflight runtime")
    _require_exact(preflight.get("package_receipt_sha256"), sha256_file(package_path), "E042 producer preflight package receipt")
    _require_exact(preflight.get("runtime_manifest_sha256"), sha256_file(runtime_path), "E042 producer preflight runtime manifest")
    for key in ("model_settings_sha256", "checkpoint_sha256", "network_sha256", "r001_steps_sha256"):
        _require_exact(preflight.get(key), frozen_inputs.get(key), f"E042 producer preflight {key}")
    _require_exact(frozen_inputs.get("r001_steps_sha256"), r001_provenance.get("steps_sha256"), "E042 identity R001 steps")

    _require_exact(linkage.get("schema"), E042_RESULT_LINKAGE_SCHEMA, "E042 result linkage schema")
    _require_exact(linkage.get("run_id"), run_id, "E042 result linkage run id")
    _require_exact(linkage.get("sealed", {}).get("mode"), "create_once_0444", "E042 result linkage sealed mode")
    _require_exact(linkage.get("sealed", {}).get("archive_root_file"), linkage_path.name, "E042 result linkage filename")
    _require_exact(linkage.get("pre_run_identity_receipt_sha256"), sha256_file(identity_path), "E042 linkage identity hash")
    _require_exact(linkage.get("producer_preflight_sha256"), sha256_file(preflight_path), "E042 linkage preflight hash")
    _require_exact(linkage.get("runner_exit_code"), 0, "E042 linkage runner exit")
    result_files = linkage.get("result_files")
    if not isinstance(result_files, dict):
        raise InputContractError("E042 result linkage lacks result_files")
    required_results = {
        "manifest.json",
        "mesh.npz",
        "projected_damage/accepted_state_pointer.json",
        "projected_damage/steps.json",
        "projected_damage/summary.json",
        "results.json",
        "completed.json",
    }
    if set(result_files) != required_results:
        raise InputContractError("E042 result linkage has an unexpected result-file set")
    result_hashes = {
        relative: _result_linkage_file(location, relative, entry, f"E042 result linkage {relative}")
        for relative, entry in result_files.items()
        if isinstance(entry, dict)
    }
    if len(result_hashes) != len(required_results):
        raise InputContractError("E042 result linkage contains malformed result-file entries")
    candidate_summary = json_object(location.arm_dir / "summary.json", "E042 projected-damage summary")
    result_summaries = json_list(location.result_root / "results.json", "E042 results summary")
    completed = json_object(location.result_root / "completed.json", "E042 completed receipt")
    result_summary = linkage.get("result_summary")
    if not isinstance(result_summary, dict):
        raise InputContractError("E042 result linkage lacks result_summary")
    for key in ("outcome", "steps_attempted", "steps_accepted", "completed_three_cycles"):
        _require_exact(result_summary.get(key), candidate_summary.get(key), f"E042 result linkage summary {key}")
    _require_exact(result_summary.get("completed_outcome"), completed.get("outcome"), "E042 linkage completed outcome")
    _require_exact(completed.get("execution"), "runner_finished", "E042 completed execution")
    _require_exact(candidate_summary.get("arm"), "projected_damage", "E042 projected-damage summary arm")
    for key in ("steps_attempted", "steps_accepted"):
        required_nonnegative_int(candidate_summary, key, "E042 projected-damage summary")
    if not isinstance(candidate_summary.get("completed_three_cycles"), bool):
        raise InputContractError("E042 projected-damage summary has non-boolean completed_three_cycles")
    if result_summaries != [candidate_summary]:
        raise InputContractError("E042 results.json does not exactly reproduce the projected-damage summary")
    _require_exact(completed.get("outcome"), candidate_summary.get("outcome"), "E042 completed outcome")
    _require_exact(completed.get("results"), result_summaries, "E042 completed results")

    _require_exact(manifest.get("experiment"), "S04-E042", "E042 manifest experiment")
    _require_exact(manifest.get("protocol"), "r1", "E042 manifest protocol")
    _require_exact(manifest.get("arm"), "projected_damage", "E042 manifest arm")
    validate_manifest_schedule(manifest, "E042 manifest")
    _require_exact(manifest.get("irreversibility_in_backward_graph"), False, "E042 manifest irreversibility route")
    _require_exact(manifest.get("damage_carrier"), "d=h+(base(q)-base_reference).detach()+eta; eta projected to h<=d<=1", "E042 manifest carrier")
    return {
        "identity_file": str(identity_path),
        "identity_sha256": sha256_file(identity_path),
        "result_linkage_file": str(linkage_path),
        "result_linkage_sha256": sha256_file(linkage_path),
        "result_file_sha256": result_hashes,
        "manifest_sha256": sha256_file(location.result_root / "manifest.json"),
        "mesh_sha256": sha256_file(location.mesh_path),
        "steps_sha256": sha256_file(location.arm_dir / "steps.json"),
        "package_receipt_sha256": sha256_file(package_path),
        "runtime_manifest_sha256": sha256_file(runtime_path),
        "producer_preflight_sha256": sha256_file(preflight_path),
        "history_timing": history_timing,
        "candidate_summary": candidate_summary,
    }


def validate_e042_result_relations(
    trajectory: PointerTrajectory,
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    """Cross-check runner summary fields against the anchored pointer history."""
    summary = provenance.get("candidate_summary")
    if not isinstance(summary, dict):
        raise InputContractError("E042 provenance lacks the linked candidate summary")
    attempted = required_nonnegative_int(summary, "steps_attempted", "E042 projected-damage summary")
    accepted_count = required_nonnegative_int(summary, "steps_accepted", "E042 projected-damage summary")
    global_count = trajectory.audit.get("global_record_count")
    if not isinstance(global_count, int) or isinstance(global_count, bool):
        raise InputContractError("E042 pointer audit lacks a valid global record count")
    if attempted != global_count:
        raise InputContractError("E042 summary attempted-step count differs from steps.json")
    if accepted_count != len(trajectory.records):
        raise InputContractError("E042 summary accepted-step count differs from pointer-accepted states")
    expected_complete = global_count == TOTAL_STEPS and len(trajectory.records) == TOTAL_STEPS
    _require_exact(summary.get("completed_three_cycles"), expected_complete, "E042 summary completion flag")
    expected_outcome = (
        "completed_all_15_accepted_steps"
        if expected_complete
        else "terminated_before_full_accepted_trajectory"
    )
    _require_exact(summary.get("outcome"), expected_outcome, "E042 summary outcome")
    pointer_commit = trajectory.audit.get("pointer_accepted_commit_id")
    _require_exact(summary.get("final_accepted_commit_id"), pointer_commit, "E042 summary final accepted state")
    return {
        "attempted_steps_match_steps_json": True,
        "accepted_steps_match_pointer_chain": True,
        "summary_final_state_matches_pointer": True,
        "completed_fixed_horizon": expected_complete,
    }

def pair_common_prefix(
    r001_records: list[dict[str, Any]],
    e040_records: list[dict[str, Any]],
    e042_records: list[dict[str, Any]],
    load_tolerance: float,
) -> tuple[list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]], dict[str, Any]]:
    if len(r001_records) != TOTAL_STEPS or len(e040_records) != TOTAL_STEPS:
        raise InputContractError("both fixed reference trajectories must contain all 15 accepted states")
    pairs: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    for index, candidate in enumerate(e042_records):
        if index >= TOTAL_STEPS:
            raise InputContractError("E042 has more than the fixed 15 states")
        r001 = r001_records[index]
        e040 = e040_records[index]
        if not (same_phase(r001, e040, load_tolerance) and same_phase(r001, candidate, load_tolerance)):
            raise InputContractError(f"trajectory phase mismatch at paired ordinal {index + 1}")
        if not accepted(candidate, "E042 record"):
            raise InputContractError("pointer-published E042 record cannot be unaccepted")
        pairs.append((r001, e040, candidate))
    terminal = {
        "common_accepted_prefix_steps": len(pairs),
        "candidate_completed_fixed_horizon": len(pairs) == TOTAL_STEPS,
        "comparison_scope": "accepted common prefix only",
        "interpretation": "A prefix or complete trajectory is descriptive solver evidence only; it is not a physical-success claim.",
    }
    return pairs, terminal


def analyze(
    r001_input: Path,
    e040_input: Path,
    e042_input: Path,
    output: Path,
    load_tolerance: float = LOAD_ABS_TOLERANCE,
    *,
    r001_identity_path: Path = DEFAULT_R001_IDENTITY,
    e040_contract_path: Path = DEFAULT_E040_CONTRACT,
) -> dict[str, Any]:
    if not math.isfinite(load_tolerance) or load_tolerance < 0.0:
        raise InputContractError("load tolerance must be finite and non-negative")
    if output.exists():
        raise InputContractError(f"analysis output must be a new path, refusing existing {output}")
    r001_location = resolve_location(r001_input, "original", "R001")
    e040_location = resolve_location(e040_input, "feasible_damage", "E040")
    e042_location = resolve_location(e042_input, "projected_damage", "E042")
    r001_identity = json_object(r001_identity_path, "fixed R001 identity")
    e040_contract = json_object(e040_contract_path, "fixed E040 reference contract")

    r001_records, r001_provenance = validate_r001(
        r001_location,
        r001_identity,
        load_tolerance,
        identity_path=r001_identity_path,
    )
    e040_manifest = json_object(e040_location.result_root / "manifest.json", "E040 manifest")
    e040_provenance = validate_e040_provenance(e040_location, e040_contract, e040_manifest)
    e042_manifest = json_object(e042_location.result_root / "manifest.json", "E042 manifest")
    e042_provenance = validate_e042_identity(e042_location, e042_manifest, r001_provenance)

    r001_mesh = load_mesh(r001_location.mesh_path, "R001")
    e040_mesh = load_mesh(e040_location.mesh_path, "E040")
    e042_mesh = load_mesh(e042_location.mesh_path, "E042")
    mesh_report = strict_mesh_check({"R001": r001_mesh, "E040": e040_mesh, "E042": e042_mesh})

    e040_trajectory = load_pointer_trajectory(
        e040_location,
        pointer_schema=E040_POINTER_SCHEMA,
        index_schema=E040_INDEX_SCHEMA,
        artifact_schema=E040_MANIFEST_SCHEMA,
        arm_name="feasible_damage",
        expected_carrier=None,
        expected_route_hash=EXPECTED_E040_ROUTE_HASH,
        load_tolerance=load_tolerance,
    )
    e042_trajectory = load_pointer_trajectory(
        e042_location,
        pointer_schema=E042_POINTER_SCHEMA,
        index_schema=E042_INDEX_SCHEMA,
        artifact_schema=E042_MANIFEST_SCHEMA,
        arm_name="projected_damage",
        expected_carrier="reference_base_eta_projected_v1",
        expected_route_hash=EXPECTED_E042_ROUTE_HASH,
        load_tolerance=load_tolerance,
    )
    if len(e040_trajectory.records) != TOTAL_STEPS:
        raise InputContractError("E040 fixed reference does not contain all 15 pointer-accepted states")
    validate_fixed_schedule(e040_trajectory.records, "E040 pointer trajectory", require_full=True, load_tolerance=load_tolerance)
    validate_fixed_schedule(e042_trajectory.records, "E042 pointer trajectory", require_full=False, load_tolerance=load_tolerance)
    if e040_trajectory.mesh_order_hash != e042_trajectory.mesh_order_hash:
        raise InputContractError("E040/E042 pointer mesh-order hashes differ")
    if e040_manifest.get("mesh_order_hash") != e040_trajectory.mesh_order_hash:
        raise InputContractError("E040 manifest/pointer mesh-order hash mismatch")
    if e042_manifest.get("mesh_order_hash") != e042_trajectory.mesh_order_hash:
        raise InputContractError("E042 manifest/pointer mesh-order hash mismatch")
    if e040_manifest.get("field_route_hash") != e040_trajectory.field_route_hash:
        raise InputContractError("E040 manifest/pointer field-route hash mismatch")
    if e042_manifest.get("field_route_hash") != e042_trajectory.field_route_hash:
        raise InputContractError("E042 manifest/pointer field-route hash mismatch")
    e042_result_relations = validate_e042_result_relations(e042_trajectory, e042_provenance)

    r001_history = history_continuity(
        r001_location,
        r001_records,
        r001_mesh,
        damage_history_rule="max_previous_history_and_damage",
    )
    e040_history = history_continuity(
        e040_location,
        e040_trajectory.records,
        e040_mesh,
        damage_history_rule="previous_damage",
    )
    e042_history = history_continuity(
        e042_location,
        e042_trajectory.records,
        e042_mesh,
        damage_history_rule="previous_damage",
    )
    initial_history = initial_history_identity(
        r001_location,
        r001_records,
        r001_mesh,
        e040_location,
        e040_trajectory.records,
        e040_mesh,
        e042_location,
        e042_trajectory.records,
        e042_mesh,
    )
    pairs, terminal = pair_common_prefix(r001_records, e040_trajectory.records, e042_trajectory.records, load_tolerance)

    output.mkdir(parents=True)
    dump_json(output / "input_provenance.json", {
        "schema": "S04-E042-post-run-analysis-input-provenance-v1",
        "fixed_reference_contracts": {
            "r001_identity_file": str(r001_identity_path),
            "r001_identity_sha256": sha256_file(r001_identity_path),
            "e040_contract_file": str(e040_contract_path),
            "e040_contract_sha256": sha256_file(e040_contract_path),
        },
        "r001": {"input": str(r001_location.supplied), "result_root": str(r001_location.result_root), **r001_provenance},
        "e040": {"input": str(e040_location.supplied), "archive_root": str(e040_location.archive_root), "result_root": str(e040_location.result_root), **e040_provenance},
        "e042": {"input": str(e042_location.supplied), "archive_root": str(e042_location.archive_root), "result_root": str(e042_location.result_root), **e042_provenance},
        "fixed_conditions": {
            "umax": UMAX,
            "load_factors": list(LOAD_FACTORS),
            "cycles": CYCLES,
            "substeps_per_cycle": SUBSTEPS_PER_CYCLE,
            "history_driver_mode": "current_active",
            "lagged_stiffness_enabled": False,
            "history_frozen_during_solve": True,
            "history_commit": "accepted_only_once_per_physical_step",
            "r001_damage_history_commit": "max(previous_history_d, previous_damage)",
            "e040_e042_damage_history_commit": "previous_damage",
            "load_absolute_tolerance": load_tolerance,
        },
        "strict_mesh_check": mesh_report,
        "initial_history_identity": initial_history,
        "e042_result_relations": e042_result_relations,
        "reference_reexecuted": False,
    })
    dump_json(output / "e040_pointer_chain.json", e040_trajectory.audit)
    dump_json(output / "e042_pointer_chain.json", e042_trajectory.audit)
    dump_json(output / "initial_history_identity.json", initial_history)
    write_csv(
        output / "history_continuity.csv",
        [*r001_history, *e040_history, *e042_history],
        default_keys=(
            "arm",
            "damage_history_rule",
            "step",
            "cycle",
            "substep",
            "load",
            "history_d_matches_expected_commit",
        ),
    )

    fields_output: list[dict[str, Any]] = []
    timing_output: list[dict[str, Any]] = []
    for r001_record, e040_record, e042_record in pairs:
        r001_fields = load_fields(r001_location, r001_record, r001_mesh)
        e040_fields = load_fields(e040_location, e040_record, e040_mesh)
        e042_fields = load_fields(e042_location, e042_record, e042_mesh)
        fields_output.extend(field_rows("R001", r001_record, e042_record, r001_fields, e042_fields, r001_mesh))
        fields_output.extend(field_rows("E040", e040_record, e042_record, e040_fields, e042_fields, r001_mesh))
        timing_output.append(timing_row(e042_record, r001_record, e040_record))
    write_csv(
        output / "paired_fields.csv",
        fields_output,
        default_keys=("comparator", "step", "cycle", "substep", "load", "load_branch", "quantity", "support", "relative_l2"),
    )
    write_csv(
        output / "timing.csv",
        timing_output,
        default_keys=("step", "cycle", "substep", "load", "load_branch", "r001_step_elapsed_seconds", "e040_step_elapsed_seconds", "e042_step_elapsed_seconds"),
    )
    r001_seconds = sum(float(row["r001_step_elapsed_seconds"]) for row in timing_output)
    e040_seconds = sum(float(row["e040_step_elapsed_seconds"]) for row in timing_output)
    e042_seconds = sum(float(row["e042_step_elapsed_seconds"]) for row in timing_output)
    timing_summary = {
        "comparison_scope": "accepted common prefix only",
        "common_accepted_prefix_steps": len(pairs),
        "r001_seconds_common_prefix": r001_seconds,
        "e040_seconds_common_prefix": e040_seconds,
        "e042_seconds_common_prefix": e042_seconds,
        "e042_minus_r001_seconds_common_prefix": e042_seconds - r001_seconds,
        "e042_to_r001_seconds_ratio_common_prefix": None if r001_seconds == 0.0 else e042_seconds / r001_seconds,
        "e042_minus_e040_seconds_common_prefix": e042_seconds - e040_seconds,
        "e042_to_e040_seconds_ratio_common_prefix": None if e040_seconds == 0.0 else e042_seconds / e040_seconds,
        "full_horizon_timing_comparable": len(pairs) == TOTAL_STEPS,
        "performance_claim_supported": False,
        "interpretation": "One matched run gives descriptive elapsed time only; it does not establish general performance.",
    }
    dump_json(output / "timing_summary.json", timing_summary)
    dump_json(output / "terminal_state.json", terminal)
    summary = {
        "analysis_status": "complete",
        "comparison_scope": "strict identity-checked accepted common prefix",
        **terminal,
        "scientific_boundary": "No physical success, FEM agreement, or global stationarity claim follows from these PIDL field/time comparisons.",
        "outputs": {
            "input_provenance": "input_provenance.json",
            "e040_pointer_chain": "e040_pointer_chain.json",
            "e042_pointer_chain": "e042_pointer_chain.json",
            "initial_history_identity": "initial_history_identity.json",
            "history_continuity": "history_continuity.csv",
            "paired_fields": "paired_fields.csv",
            "timing": "timing.csv",
            "timing_summary": "timing_summary.json",
            "terminal_state": "terminal_state.json",
        },
        "timing": timing_summary,
    }
    dump_json(output / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r001", type=Path, required=True, help="fixed S04-E037 R001 archive root or its result root")
    parser.add_argument("--e040", type=Path, required=True, help="completed S04-E040 archive root or results root")
    parser.add_argument("--e042", type=Path, required=True, help="E042 archive root or results root")
    parser.add_argument("--output", type=Path, required=True, help="new local analysis output directory")
    parser.add_argument(
        "--load-abs-tolerance",
        type=float,
        default=LOAD_ABS_TOLERANCE,
        help=f"absolute load pairing tolerance (default {LOAD_ABS_TOLERANCE:g})",
    )
    args = parser.parse_args()
    try:
        summary = analyze(args.r001, args.e040, args.e042, args.output, args.load_abs_tolerance)
    except InputContractError as error:
        parser.error(str(error))
    print(json.dumps(_json_safe(summary), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
