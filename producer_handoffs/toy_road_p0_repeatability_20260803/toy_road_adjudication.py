from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
import re

import numpy as np


PROJECTION_SCHEMA = "toy_road_physical_input_projection_v1"
INITIAL_STATE_SCHEMA = "toy_road_semantic_initial_state_v1"
SNAPSHOT_SCHEMA = "toy_road_p0_input_snapshot_v1"
SNAPSHOT_FIELDS = {
    "schema_version",
    "authorization_scope",
    "case_id",
    "source_commit",
    "runtime_lock_sha256",
    "family_contract_sha256",
    "case_physics_contract_sha256",
    "execution_input_lock_sha256",
    "input_assets_root",
    "mesh_sha256",
    "changed_axes",
    "cycle_jump",
    "fresh_state0",
    "line_search",
    "resume_allowed",
    "case_physics",
}


class AdjudicationError(RuntimeError):
    pass


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii") + b"\n"
    except (TypeError, ValueError) as exception:
        raise AdjudicationError(f"value is not canonical JSON: {exception}") from exception


def _strict_json_object(payload: bytes, label: str) -> dict[str, object]:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON key {key!r}")
            value[key] = item
        return value

    def reject_nonfinite(token: str) -> object:
        raise ValueError(f"non-finite JSON number {token}")

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exception:
        raise AdjudicationError(f"cannot read {label}: {exception}") from exception
    if not isinstance(value, dict):
        raise AdjudicationError(f"{label} must be one JSON object")
    return value


def _require_exact_fields(value: Mapping[str, object], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise AdjudicationError(f"{label} fields are missing or extra")


def _physics_template() -> dict[str, object]:
    path = Path(__file__).with_name("CASE_PHYSICS_CONTRACTS.json")
    document = _strict_json_object(path.read_bytes(), "case physics contracts")
    cases = document.get("cases")
    if not isinstance(cases, dict):
        raise AdjudicationError("case physics contract table is invalid")
    parent = cases.get("P0_parent")
    if not isinstance(parent, dict) or not isinstance(parent.get("physics"), dict):
        raise AdjudicationError("P0 physics contract is invalid")
    physics = json.loads(json.dumps(parent["physics"]))
    mesh = physics["mesh"]
    mesh.pop("node_transform")
    mesh["node_coords"] = [[0.0, 0.0]]
    mesh["connectivity"] = [[1, 1, 1, 1]]
    blocks = physics["loading"]["blocks"]
    if isinstance(blocks, list) and len(blocks) == 1 and isinstance(blocks[0], list):
        physics["loading"]["blocks"] = blocks[0]
    return physics


def _require_json_type(value: object, template: object, label: str) -> None:
    if isinstance(template, dict):
        if not isinstance(value, dict):
            raise AdjudicationError(f"{label} type is invalid")
        _require_exact_fields(value, set(template), label)
        for key in template:
            _require_json_type(value[key], template[key], f"{label}.{key}")
        return
    if isinstance(template, list):
        if not isinstance(value, list) or not value:
            raise AdjudicationError(f"{label} type is invalid")
        if label.endswith("mesh.node_coords"):
            for row in value:
                if not isinstance(row, list) or len(row) != 2 or not all(
                    type(item) in {int, float} and np.isfinite(item) for item in row
                ):
                    raise AdjudicationError(f"{label} type is invalid")
            return
        if label.endswith("mesh.connectivity"):
            for row in value:
                if not isinstance(row, list) or len(row) != 4 or not all(
                    type(item) is int and item > 0 for item in row
                ):
                    raise AdjudicationError(f"{label} integer type is invalid")
            return
        if len(value) != len(template):
            raise AdjudicationError(f"{label} fields are missing or extra")
        for index, (item, expected) in enumerate(zip(value, template, strict=True)):
            _require_json_type(item, expected, f"{label}[{index}]")
        return
    if type(template) is float and type(value) in {int, float}:
        if not np.isfinite(value):
            raise AdjudicationError(f"{label} must be finite")
        return
    if type(value) is not type(template):
        raise AdjudicationError(f"{label} type is invalid; bool/integer confusion")
    if isinstance(value, float) and not np.isfinite(value):
        raise AdjudicationError(f"{label} must be finite")


def semantic_initial_state_sha256(state0: Mapping[str, object]) -> str:
    if set(state0) != {"d_node", "alpha_bar_gp"}:
        raise AdjudicationError("initial state fields are missing or extra")
    hasher = hashlib.sha256()
    hasher.update((INITIAL_STATE_SCHEMA + "\n").encode("ascii"))
    for name in ("d_node", "alpha_bar_gp"):
        array = np.asarray(state0[name])
        if array.dtype.kind != "f" or array.dtype.itemsize != 8:
            raise AdjudicationError(f"initial state {name} must be float64")
        canonical = np.asarray(array, dtype="<f8", order="C")
        if not np.all(np.isfinite(canonical)):
            raise AdjudicationError(f"initial state {name} must be finite")
        if name == "d_node" and (
            canonical.ndim != 2
            or canonical.shape[1] != 1
            or canonical.shape[0] == 0
            or np.any(canonical < 0)
            or np.any(canonical > 1)
        ):
            raise AdjudicationError("initial state d_node shape or bounds are invalid")
        if name == "alpha_bar_gp" and (
            canonical.ndim != 2
            or canonical.shape[1] != 4
            or canonical.shape[0] == 0
            or np.any(canonical < 0)
        ):
            raise AdjudicationError("initial state alpha_bar_gp shape or bounds are invalid")
        metadata = {"field": name, "dtype": "float64-le", "shape": list(canonical.shape)}
        hasher.update(_canonical_json_bytes(metadata))
        hasher.update(canonical.tobytes(order="C"))
    return hasher.hexdigest()


def build_physical_input_projection(
    snapshot_bytes: bytes, state0: Mapping[str, object]
) -> dict[str, object]:
    snapshot = _strict_json_object(snapshot_bytes, "physical input snapshot")
    _require_exact_fields(snapshot, SNAPSHOT_FIELDS, "physical input snapshot")
    if snapshot.get("schema_version") != SNAPSHOT_SCHEMA:
        raise AdjudicationError("physical input snapshot schema is invalid")
    case_physics = snapshot.get("case_physics")
    if not isinstance(case_physics, dict):
        raise AdjudicationError("physical input snapshot case_physics is missing")
    _require_json_type(case_physics, _physics_template(), "case_physics")
    return {
        "schema_version": PROJECTION_SCHEMA,
        "case_physics": case_physics,
        "initial_state": {
            "schema_version": INITIAL_STATE_SCHEMA,
            "sha256": semantic_initial_state_sha256(state0),
        },
    }


def physical_input_projection_sha256(projection: Mapping[str, object]) -> str:
    if projection.get("schema_version") != PROJECTION_SCHEMA:
        raise AdjudicationError("physical input projection schema is invalid")
    return hashlib.sha256(_canonical_json_bytes(dict(projection))).hexdigest()


def require_equal_producer_runtime_identity(
    p0: Mapping[str, object], p0r: Mapping[str, object]
) -> None:
    if p0 != p0r:
        raise AdjudicationError("producer/runtime identity mismatch")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _extract_thread_settings(launcher_bytes: bytes) -> dict[str, str]:
    try:
        text = launcher_bytes.decode("utf-8")
    except UnicodeDecodeError as exception:
        raise AdjudicationError("producer launcher is not UTF-8") from exception
    names = {
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_DYNAMIC",
    }
    observed: dict[str, str] = {}
    pattern = re.compile(
        r"^\s*(OMP_NUM_THREADS|MKL_NUM_THREADS|OPENBLAS_NUM_THREADS|MKL_DYNAMIC)\s*=\s*'([^']+)'\s*$",
        re.MULTILINE,
    )
    for name, value in pattern.findall(text):
        if name in observed:
            raise AdjudicationError(f"duplicate thread setting {name}")
        observed[name] = value
    expected = {
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_DYNAMIC": "FALSE",
    }
    if set(observed) != names or observed != expected:
        raise AdjudicationError("producer thread settings identity mismatch")
    return observed


def extract_producer_runtime_identity(
    package: Mapping[str, object], producer_root: Path
) -> dict[str, object]:
    snapshot = package.get("snapshot")
    manifest = package.get("manifest")
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("bytes"), dict):
        raise AdjudicationError("validated package snapshot is missing")
    if not isinstance(manifest, dict):
        raise AdjudicationError("validated package manifest is missing")
    package_bytes = snapshot["bytes"]
    lock_bytes = package_bytes.get("EXECUTION_INPUT_LOCK.json")
    runtime_bytes = package_bytes.get("RUNTIME_RECEIPT.json")
    if not isinstance(lock_bytes, bytes) or not isinstance(runtime_bytes, bytes):
        raise AdjudicationError("package runtime identity artifacts are missing")
    lock = _strict_json_object(lock_bytes, "execution input lock")
    runtime = _strict_json_object(runtime_bytes, "runtime receipt")
    expectations = lock.get("runtime_expectations")
    if not isinstance(expectations, dict):
        raise AdjudicationError("runtime expectations are missing")
    matlab = expectations.get("matlab")
    binary = expectations.get("binary_sha256")
    if not isinstance(matlab, dict) or not isinstance(binary, dict):
        raise AdjudicationError("runtime MATLAB or binary identity is missing")
    _require_exact_fields(
        binary, {"initial", "AMOR", "AT1_HISTORY_FATIGUE", "cholmod2"}, "binary identity"
    )
    matlab_fields = {
        "release",
        "update",
        "version",
        "computer",
        "executable_sha256",
        "blas",
        "lapack",
        "absolute_path_order",
    }
    _require_exact_fields(matlab, matlab_fields, "MATLAB identity")
    for field in ("source_commit", "runtime_lock_sha256"):
        if runtime.get(field) != lock.get(field):
            raise AdjudicationError(f"runtime receipt {field} identity mismatch")
    for field in ("computer", "blas", "lapack"):
        if runtime.get(field) != matlab.get(field):
            raise AdjudicationError(f"runtime receipt MATLAB {field} identity mismatch")
    manifest_path = Path(producer_root) / "SOURCE_MANIFEST.json"
    launcher_path = Path(producer_root) / "launch_toy_road_family_case.ps1"
    try:
        manifest_bytes = manifest_path.read_bytes()
        launcher_bytes = launcher_path.read_bytes()
    except OSError as exception:
        raise AdjudicationError(f"cannot read sealed producer identity: {exception}") from exception
    if _sha256_bytes(manifest_bytes) != lock.get("source_manifest_sha256"):
        raise AdjudicationError("producer source manifest identity mismatch")
    return {
        "source_commit": lock.get("source_commit"),
        "source_manifest_sha256": lock.get("source_manifest_sha256"),
        "case_physics_contract_sha256": manifest.get(
            "case_physics_contract_sha256"
        ),
        "runtime_lock_sha256": lock.get("runtime_lock_sha256"),
        "matlab": {name: matlab[name] for name in matlab_fields - {"absolute_path_order"}},
        "binary_sha256": dict(binary),
        "thread_settings": _extract_thread_settings(launcher_bytes),
        "launcher_sha256": _sha256_bytes(launcher_bytes),
    }
