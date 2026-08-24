"""Verify that a T3-rev extension changes only its declared loading axis."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import types
from typing import Any, Mapping


class DiffError(RuntimeError):
    """Raised when an extension differs from the one permitted T3-rev overlay."""


UNCHANGED_IDENTITY_FIELDS = (
    "solver_sha256",
    "recovery_sha256",
    "exporter_sha256",
    "numerical_gate_contract_sha256",
    "event_contract_sha256",
)

_IDENTITY_SOURCE_FILES = {
    "solver_sha256": "solve_toy_road_family_case.m",
    "recovery_sha256": "recover_toy_road_family_state.m",
    "exporter_sha256": "export_toy_road_cycle_shard.m",
    "numerical_gate_contract_sha256": "finalize_toy_road_c5_gate.m",
    "event_contract_sha256": "build_toy_road_family_case.m",
}


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _reject_constant(value: str) -> None:
    raise DiffError(f"non-finite JSON constant is forbidden: {value}")


def _reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DiffError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json(path: Path) -> dict[str, object]:
    """Read one JSON object without duplicate keys or non-finite constants."""
    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicates,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exception:
        raise DiffError(f"cannot read strict JSON {path}: {exception}") from exception
    if not isinstance(value, dict):
        raise DiffError(f"strict JSON document must be an object: {path}")
    if not _finite_json_values(value):
        raise DiffError(f"strict JSON contains a non-finite value: {path}")
    return value


def _finite_json_values(value: object) -> bool:
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_finite_json_values(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _finite_json_values(item)
                   for key, item in value.items())
    return False


def _load_builder() -> Any:
    path = Path(__file__).with_name("build_t3_rev_extension.py")
    spec = importlib.util.spec_from_file_location("t3_rev_diff_builder", path)
    if spec is None or spec.loader is None:
        raise DiffError("cannot load the T3-rev extension builder")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def _expected_generated_sources(base_root: Path) -> tuple[dict[str, bytes], list[dict[str, str]]]:
    builder = _load_builder()
    try:
        files, hunks = builder._patch_sources(base_root)
        protocol = types.ModuleType("verified_t3_rev_protocol")
        protocol.__file__ = "<verified T3-rev protocol>"
        exec(compile(files["toy_road_protocol.py"], protocol.__file__, "exec"),
             protocol.__dict__)
        family, cases = builder._build_contract_data(base_root, protocol)
    except Exception as exception:
        raise DiffError(f"cannot reconstruct the classified T3-rev overlay: {exception}") from exception
    files["FAMILY_CONTRACT.json"] = family
    files["CASE_PHYSICS_CONTRACTS.json"] = cases
    hunks.extend(
        {"path": path, "classification": "contract_data"}
        for path in ("FAMILY_CONTRACT.json", "CASE_PHYSICS_CONTRACTS.json")
    )
    return files, hunks


def require_exact_shadow_set(manifest: Mapping[str, object], allowed: tuple[str, ...]) -> None:
    """Require exactly the generated shadow list and the digests it declares."""
    expected_fields = {
        "schema_version", "case_id", "repo_commit", "base_source_commit",
        "base_source_manifest_sha256", "contract_sha256",
        "source_diff_inventory_sha256", "shadow_files",
    }
    if set(manifest) != expected_fields:
        raise DiffError("extension manifest fields are not exact")
    shadow_files = manifest["shadow_files"]
    if not isinstance(shadow_files, list) or len(shadow_files) != len(allowed):
        raise DiffError("extension manifest does not declare the exact shadow set")
    paths: list[str] = []
    for entry in shadow_files:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise DiffError("extension manifest shadow entry is malformed")
        path, digest = entry["path"], entry["sha256"]
        if not isinstance(path, str) or not isinstance(digest, str):
            raise DiffError("extension manifest shadow entry is malformed")
        paths.append(path)
    if tuple(paths) != allowed:
        raise DiffError("extension manifest does not declare the exact shadow set")


def require_classified_hunks(
        base_root: Path, extension_root: Path, inventory: Mapping[str, object]) -> None:
    """Prove every shadow is the deterministic Task 2 role/loading insertion."""
    builder = _load_builder()
    expected_files, expected_hunks = _expected_generated_sources(base_root)
    expected_inventory = {
        "schema_version": "toy_road_t3_rev_source_diff_inventory_v1",
        "case_id": builder.CASE_ID,
        "hunks": expected_hunks,
    }
    if inventory != expected_inventory:
        raise DiffError("unclassified hunk inventory or classification mismatch")
    for relative, expected in expected_files.items():
        path = extension_root / relative
        try:
            actual = path.read_bytes()
        except OSError as exception:
            raise DiffError(f"unclassified missing shadow file: {relative}") from exception
        if actual != expected:
            if relative in _IDENTITY_SOURCE_FILES.values():
                raise DiffError(f"unclassified numerical change in {relative}")
            raise DiffError(f"unclassified source change in {relative}")


def _verify_manifest_hashes(
        extension_root: Path, manifest: Mapping[str, object], allowed: tuple[str, ...]) -> None:
    entries = manifest["shadow_files"]
    assert isinstance(entries, list)
    for relative, entry in zip(allowed, entries):
        assert isinstance(entry, dict)
        expected = entry["sha256"]
        if not isinstance(expected, str) or _sha256((extension_root / relative).read_bytes()) != expected:
            raise DiffError(f"extension manifest hash mismatch: {relative}")
    inventory_path = extension_root / "SOURCE_DIFF_INVENTORY.json"
    digest = manifest["source_diff_inventory_sha256"]
    if not isinstance(digest, str) or _sha256(inventory_path.read_bytes()) != digest:
        raise DiffError("extension manifest inventory hash mismatch")


def _verify_numerical_identities(base_root: Path, extension_root: Path) -> None:
    terminal_path = base_root.parents[1] / "analysis" / "toy_road_t3_mechanism_20260819" / "evidence" / "TERMINAL_MANIFEST.json"
    terminal = strict_json(terminal_path)
    for field in UNCHANGED_IDENTITY_FIELDS:
        expected = terminal.get(field)
        relative = _IDENTITY_SOURCE_FILES[field]
        if not isinstance(expected, str):
            raise DiffError(f"terminal numerical identity is malformed: {field}")
        base_digest = _sha256((base_root / relative).read_bytes())
        if base_digest != expected:
            raise DiffError(f"terminal numerical identity does not bind base {relative}")
        # The exact-overlay comparison above proves any shadowed version is
        # byte-for-byte the generated role/loading insertion.  The terminal
        # manifest deliberately hashes the sealed base, not that overlay.


def verify_extension_diff(base_root: Path, extension_root: Path) -> dict[str, object]:
    """Return PASS only for the exact T3-rev role and loading-block overlay."""
    base_root, extension_root = Path(base_root), Path(extension_root)
    builder = _load_builder()
    try:
        builder._validate_base(base_root)
    except Exception as exception:
        raise DiffError(f"base source identity is invalid: {exception}") from exception
    manifest = strict_json(extension_root / "EXTENSION_SOURCE_MANIFEST.json")
    inventory = strict_json(extension_root / "SOURCE_DIFF_INVENTORY.json")
    require_exact_shadow_set(manifest, builder.ALLOWED_SHADOW_FILES)
    require_classified_hunks(base_root, extension_root, inventory)
    _verify_manifest_hashes(extension_root, manifest, builder.ALLOWED_SHADOW_FILES)
    _verify_numerical_identities(base_root, extension_root)
    expected_paths = {*builder.ALLOWED_SHADOW_FILES,
                      "EXTENSION_SOURCE_MANIFEST.json", "SOURCE_DIFF_INVENTORY.json"}
    actual_paths = {
        path.relative_to(extension_root).as_posix()
        for path in extension_root.rglob("*") if path.is_file()
    }
    if actual_paths != expected_paths:
        raise DiffError("extension file set is not exact")
    return {
        "status": "PASS",
        "numerical_algorithm_changed": False,
        "allowed_shadow_files": list(builder.ALLOWED_SHADOW_FILES),
    }
