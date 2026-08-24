from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping


class ExtensionError(RuntimeError):
    """Raised when the T3-rev producer overlay cannot be proven minimal."""


ALLOWED_SHADOW_FILES = (
    "build_toy_road_family_case.m",
    "main_toy_road_family_case.m",
    "private/run_toy_road_driver_core.m",
    "run_toy_road_controlled_driver_harness.m",
    "solve_toy_road_family_case.m",
    "ToyRoadC5Trace.m",
    "toy_road_protocol.py",
    "FAMILY_CONTRACT.json",
    "CASE_PHYSICS_CONTRACTS.json",
)
BASE_SOURCE_MANIFEST_SHA256 = "61e12721da19ce37c2f065804d2a151b6bd80981196687f6f3fe292dca48b89e"
BASE_SOURCE_COMMIT = "7c56ff383187cdee2f45e1b15d707f148f386302"
CASE_ID = "T3_rev_loading_order"
CONTRACT_PATH = Path(__file__).with_name("T3_REV_CONTRACT.json")


def canonical_json_bytes(value: Mapping[str, object]) -> bytes:
    if not isinstance(value, Mapping):
        raise ExtensionError("canonical JSON input must be an object")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _reject_constant(value: str) -> None:
    raise ExtensionError(f"non-finite JSON constant is forbidden: {value}")


def _reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    output: dict[str, object] = {}
    for key, value in pairs:
        if key in output:
            raise ExtensionError(f"duplicate JSON key: {key}")
        output[key] = value
    return output


def _read_strict_json(path: Path) -> dict[str, object]:
    try:
        payload = Path(path).read_bytes()
        value = json.loads(
            payload.decode("utf-8"), object_pairs_hook=_reject_duplicates, parse_constant=_reject_constant
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exception:
        raise ExtensionError(f"cannot read strict JSON {path}: {exception}") from exception
    if not isinstance(value, dict):
        raise ExtensionError("strict JSON document must be an object")
    if not _json_values_are_canonical(value):
        raise ExtensionError("strict JSON contains a noncanonical value")
    canonical_payload = canonical_json_bytes(value)
    if payload not in {canonical_payload, canonical_payload + b"\n"}:
        raise ExtensionError("strict JSON bytes are not canonical")
    return value


def _json_values_are_canonical(value: object) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_json_values_are_canonical(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _json_values_are_canonical(item) for key, item in value.items())
    return False


def read_strict_contract(path: Path) -> dict[str, object]:
    contract = _read_strict_json(path)
    expected = {
        "authorization_capability": None,
        "base_source_commit": BASE_SOURCE_COMMIT,
        "base_source_manifest_sha256": BASE_SOURCE_MANIFEST_SHA256,
        "case_id": CASE_ID,
        "changed_axes": ["loading.blocks"],
        "follow_on_authorized": False,
        "loading_blocks": [[1, 30, 0.126], [31, 60, 0.108], [61, 150, 0.12]],
        "resume_allowed": False,
        "schema_version": "toy_road_t3_rev_contract_v1",
    }
    if contract != expected:
        raise ExtensionError("T3-rev contract contents are not exact")
    return contract


def inventory_tree(root: Path) -> dict[str, str]:
    root = Path(root)
    if not root.is_dir():
        raise ExtensionError(f"inventory root is not a directory: {root}")
    return {
        path.relative_to(root).as_posix(): _sha256(path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise ExtensionError(f"exact patch count differs for {label}")
    return text.replace(old, new, 1)


def _validate_base(base_root: Path) -> None:
    manifest_path = base_root / "SOURCE_MANIFEST.json"
    if _sha256(manifest_path.read_bytes()) != BASE_SOURCE_MANIFEST_SHA256:
        raise ExtensionError("base source identity does not match the sealed manifest")
    try:
        manifest = json.loads(manifest_path.read_text("utf-8"))
        entries = manifest["files"]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exception:
        raise ExtensionError("base source identity manifest is unreadable") from exception
    if not isinstance(entries, list):
        raise ExtensionError("base source identity manifest is malformed")
    declared = {entry.get("path"): entry.get("sha256") for entry in entries if isinstance(entry, dict)}
    if len(declared) != len(entries) or not all(isinstance(path, str) and isinstance(digest, str) for path, digest in declared.items()):
        raise ExtensionError("base source identity manifest is malformed")
    for relative, expected in declared.items():
        path = base_root / relative
        if not path.is_file() or _sha256(path.read_bytes()) != expected:
            raise ExtensionError(f"base source identity differs: {relative}")
    if set(ALLOWED_SHADOW_FILES) - set(declared):
        raise ExtensionError("base source identity omits an allowlisted shadow file")


def _write_exclusive(path: Path, payload: bytes) -> None:
    try:
        with path.open("xb") as stream:
            stream.write(payload)
    except FileExistsError as exception:
        raise ExtensionError(f"refusing to overwrite extension file: {path}") from exception


def _read_text(base_root: Path, relative: str) -> str:
    try:
        return (base_root / relative).read_text(encoding="utf-8")
    except OSError as exception:
        raise ExtensionError(f"cannot read base source {relative}: {exception}") from exception


def _patch_role_allowlist(text: str, label: str) -> str:
    return replace_once(
        text,
        "'T2_material_state','T3_loading_history'}",
        "'T2_material_state','T3_loading_history','T3_rev_loading_order'}",
        label,
    )


def _patch_sources(base_root: Path) -> tuple[dict[str, bytes], list[dict[str, str]]]:
    files: dict[str, bytes] = {}
    hunks: list[dict[str, str]] = []
    for relative in ALLOWED_SHADOW_FILES[:6]:
        original = _read_text(base_root, relative)
        patched = _patch_role_allowlist(original, relative)
        if relative == "build_toy_road_family_case.m":
            old = """elseif strcmp(caseId, 'T3_loading_history')
    loading.blocks = [1 30 0.108; 31 60 0.126; 61 150 0.120];
    changedAxes = {'loading.blocks'};
end"""
            new = """elseif strcmp(caseId, 'T3_loading_history')
    loading.blocks = [1 30 0.108; 31 60 0.126; 61 150 0.120];
    changedAxes = {'loading.blocks'};
elseif strcmp(caseId, 'T3_rev_loading_order')
    loading.blocks = [1 30 0.126; 31 60 0.108; 61 150 0.120];
    changedAxes = {'loading.blocks'};
end"""
            patched = replace_once(patched, old, new, "T3-rev loading blocks")
            hunks.append({"path": relative, "classification": "loading_block_definition"})
        files[relative] = patched.encode("utf-8")
        hunks.append({
            "path": relative,
            "classification": "case_registration" if relative == "build_toy_road_family_case.m" else "role_allowlist",
        })

    protocol = _read_text(base_root, "toy_road_protocol.py")
    protocol = replace_once(protocol, '    "T3_loading_history",\n)', '    "T3_loading_history",\n    "T3_rev_loading_order",\n)', "Python family roles")
    protocol = replace_once(protocol, '    "T3_loading_history": ["loading.blocks"],\n}', '    "T3_loading_history": ["loading.blocks"],\n    "T3_rev_loading_order": ["loading.blocks"],\n}', "Python changed-axis table")
    protocol = replace_once(protocol, "family case-axis table does not declare exactly five roles", "family case-axis table does not declare exactly six roles", "family role count error")
    protocol = replace_once(protocol, "case contract table does not contain exactly five roles", "case contract table does not contain exactly six roles", "case role count error")
    files["toy_road_protocol.py"] = protocol.encode("utf-8")
    hunks.extend({"path": "toy_road_protocol.py", "classification": "role_allowlist"} for _ in range(4))
    return files, hunks


def _import_protocol(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("t3_rev_generated_protocol", path)
    if spec is None or spec.loader is None:
        raise ExtensionError("cannot load generated toy-road protocol")
    module = importlib.util.module_from_spec(spec)
    original_dont_write_bytecode = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    except Exception as exception:
        raise ExtensionError(f"generated toy-road protocol cannot load: {exception}") from exception
    finally:
        sys.dont_write_bytecode = original_dont_write_bytecode
    return module


def _build_contract_data(base_root: Path, protocol: Any) -> tuple[bytes, bytes]:
    family = json.loads(_read_text(base_root, "FAMILY_CONTRACT.json"))
    cases = json.loads(_read_text(base_root, "CASE_PHYSICS_CONTRACTS.json"))
    family["case_axis_table"][CASE_ID] = ["loading.blocks"]
    family_digest = protocol.canonical_json_sha256(family)
    cases["family_contract_sha256"] = family_digest
    t3 = cases["cases"]["T3_loading_history"]
    rev = json.loads(json.dumps(t3))
    rev["changed_axes"] = ["loading.blocks"]
    rev["physics"]["loading"]["blocks"] = [[1, 30, 0.126], [31, 60, 0.108], [61, 150, 0.12]]
    cases["cases"][CASE_ID] = rev
    for role, entry in cases["cases"].items():
        entry["case_physics_contract_sha256"] = protocol.canonical_json_sha256({
            "family_contract_sha256": family_digest,
            "physics": entry["physics"],
        })
    try:
        protocol.validate_contract_documents(family, cases)
    except Exception as exception:
        raise ExtensionError(f"generated contracts are invalid: {exception}") from exception
    return protocol.canonical_json_bytes(family), protocol.canonical_json_bytes(cases)


def build_extension(base_root: Path, destination: Path, repo_commit: str) -> dict[str, object]:
    base_root, destination = Path(base_root), Path(destination)
    if not isinstance(repo_commit, str) or len(repo_commit) != 40 or any(char not in "0123456789abcdef" for char in repo_commit):
        raise ExtensionError("repo_commit must be a 40-character lowercase SHA-1")
    contract = read_strict_contract(CONTRACT_PATH)
    _validate_base(base_root)
    if destination.exists():
        raise ExtensionError(f"extension destination already exists: {destination}")
    destination.mkdir(parents=True)
    (destination / "private").mkdir()
    files, hunks = _patch_sources(base_root)
    _write_exclusive(destination / "toy_road_protocol.py", files.pop("toy_road_protocol.py"))
    protocol = _import_protocol(destination / "toy_road_protocol.py")
    family, cases = _build_contract_data(base_root, protocol)
    files["FAMILY_CONTRACT.json"] = family
    files["CASE_PHYSICS_CONTRACTS.json"] = cases
    hunks.extend({"path": path, "classification": "contract_data"} for path in ("FAMILY_CONTRACT.json", "CASE_PHYSICS_CONTRACTS.json"))
    for relative in ALLOWED_SHADOW_FILES:
        if relative == "toy_road_protocol.py":
            continue
        _write_exclusive(destination / relative, files[relative])
    inventory = {
        "schema_version": "toy_road_t3_rev_source_diff_inventory_v1",
        "case_id": CASE_ID,
        "hunks": hunks,
    }
    inventory_bytes = canonical_json_bytes(inventory)
    _write_exclusive(destination / "SOURCE_DIFF_INVENTORY.json", inventory_bytes)
    shadow_files = [
        {"path": relative, "sha256": _sha256((destination / relative).read_bytes())}
        for relative in ALLOWED_SHADOW_FILES
    ]
    manifest = {
        "schema_version": "toy_road_t3_rev_extension_source_manifest_v1",
        "case_id": CASE_ID,
        "repo_commit": repo_commit,
        "base_source_commit": BASE_SOURCE_COMMIT,
        "base_source_manifest_sha256": BASE_SOURCE_MANIFEST_SHA256,
        "contract_sha256": _sha256(CONTRACT_PATH.read_bytes()),
        "source_diff_inventory_sha256": _sha256(inventory_bytes),
        "shadow_files": shadow_files,
    }
    _write_exclusive(destination / "EXTENSION_SOURCE_MANIFEST.json", canonical_json_bytes(manifest))
    return {
        "case_id": CASE_ID,
        "loading_blocks": contract["loading_blocks"],
        "base_source_manifest_sha256": BASE_SOURCE_MANIFEST_SHA256,
        "changed_source_files": list(ALLOWED_SHADOW_FILES),
    }
