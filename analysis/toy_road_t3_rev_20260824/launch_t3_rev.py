"""Create one fresh, sealed T3-rev MATLAB launch boundary."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import secrets
import subprocess
from subprocess import Popen
import sys
import types
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping


CASE_ID = "T3_rev_loading_order"
AUTHORIZATION_CAPABILITY = "exactly_one_T3_rev_loading_order_execution"
SUITESPARSE_ROOT = Path(r"C:\SuiteSparse\SuiteSparse-dev")
AUTHORIZATION_STATE_ROOT = Path(r"C:\q4diag\toy-road-authorization-state\t3-rev-seal-v1")
QUALIFIED_SOURCE_COMMIT = "355d4c83fefc2db88c32031a2dd2623b3de85c89"
QUALIFIED_SOURCE_COUNT = 221
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200
QUALIFIED_TEMPLATE_ROOT = Path(r"C:\q4diag\toy-road-t3-production-7c56ff3-run1")
QUALIFIED_TEMPLATE_LOCK_SHA256 = "da1d30e728a0f689b02bbbf36ea85e18989ad6964d31b3c7824fb0755c362d59"
QUALIFIED_TEMPLATE_CASE_ID = "T3_loading_history"
QUALIFIED_TEMPLATE_CASE_CONTRACT_SHA256 = (
    "fbbe2c46ec394f20589e7c150783a08b5fbd79d13e51ce74eef90930def0146c"
)
QUALIFIED_TEMPLATE_WRITABLE_ROOTS = {
    "cache": r"C:\q4diag\toy-road-t3-production-7c56ff3-run1\cache",
    "matlab_startup_pref": r"C:\q4diag\toy-road-t3-production-7c56ff3-run1\pref.matlab-startup",
    "output": r"C:\q4diag\toy-road-t3-production-7c56ff3-run1\output",
    "pref": r"C:\q4diag\toy-road-t3-production-7c56ff3-run1\pref",
    "temp": r"C:\q4diag\toy-road-t3-production-7c56ff3-run1\temp",
    "tmp": r"C:\q4diag\toy-road-t3-production-7c56ff3-run1\tmp",
    "work": r"C:\q4diag\toy-road-t3-production-7c56ff3-run1\work",
}
QUALIFIED_SOURCE_HASHES_SHA256 = "4951e9bb43515c036ec2f100b8c94627d48d88ae5b515d49c3d9bcec09bb7481"
QUALIFIED_BASE_PROTOCOL_SHA256 = "db51a9cb54810711c2bdfe7ee35a705179e2852c7b069995d69693579c1e84a9"
EXPECTED_INPUT_ASSET_SHA256 = {
    "sens_mesh.m": "dbf13237939425b61cde93b841ae2c24e7fccd291861df5508a34800bb9f4706",
}
BOOTSTRAP_HELPER_RELATIVE = "toy_road_wait_for_launch_receipt.m"
BOOTSTRAP_HELPER_BYTES = b"""function toy_road_wait_for_launch_receipt(receiptPath, expectedSha256, expectedNonce, expectedSealSha256, expectedCaseId, expectedLockSha256, expectedRunRoot, timeoutSeconds)\nstartTime = tic;\nwhile toc(startTime) <= timeoutSeconds\n    if isfile(receiptPath)\n        try\n            bytes = uint8(fileread(receiptPath));\n            hasher = java.security.MessageDigest.getInstance('SHA-256');\n            hasher.update(bytes);\n            digest = lower(reshape(dec2hex(typecast(hasher.digest(), 'uint8'), 2).', 1, []));\n            receipt = jsondecode(native2unicode(bytes, 'UTF-8'));\n            valid = strcmp(digest, expectedSha256) && isstruct(receipt) && isscalar(receipt) && ...\n                isfield(receipt, 'launch_nonce') && strcmp(receipt.launch_nonce, expectedNonce) && ...\n                isfield(receipt, 'seal_sha256') && strcmp(receipt.seal_sha256, expectedSealSha256) && ...\n                isfield(receipt, 'case_id') && strcmp(receipt.case_id, expectedCaseId) && ...\n                isfield(receipt, 'execution_input_lock_sha256') && strcmp(receipt.execution_input_lock_sha256, expectedLockSha256) && ...\n                isfield(receipt, 'run_root') && strcmp(receipt.run_root, expectedRunRoot);\n            if valid\n                return\n            end\n        catch\n        end\n    end\n    pause(0.05);\nend\nerror('toyRoad:LaunchCredentialTimeout', 'Exact launch credential was not published');\nend\n"""
BOOTSTRAP_HELPER_SHA256 = hashlib.sha256(BOOTSTRAP_HELPER_BYTES).hexdigest()


class BusyExperimentError(RuntimeError):
    """Raised when an existing experiment makes this one-shot launch unsafe."""


class LaunchError(RuntimeError):
    """Raised when the sealed launch inputs cannot be proven consistent."""


class PreparedLaunchError(LaunchError):
    """Raised after a validated launch has claimed a root but failed during preparation."""


class LaunchCredentialError(LaunchError):
    """Raised when a started bootstrap cannot receive its create-once authorization receipt."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def executable_sha256(path: Path) -> str:
    """Hash the supplied MATLAB executable before it can become a process."""
    return sha256(path)


def resolve_runtime_binaries(repo_root: Path, griphfith_root: Path) -> dict[str, Path]:
    """Resolve the only four binary locations admitted by the qualified runtime."""
    paths = {
        "initial": repo_root / "producer_handoffs" / "rebuilt_initial_mex_qualification_20260801" / "runtime" / "initial.mexw64",
        "AMOR": griphfith_root / "Sources" / "+phase_field" / "+mex" / "+fem" / "+assembly" / "+equilibrium" / "AMOR.mexw64",
        "AT1_HISTORY_FATIGUE": griphfith_root / "Sources" / "+phase_field" / "+mex" / "+fem" / "+assembly" / "+pf" / "AT1_HISTORY_FATIGUE.mexw64",
        "cholmod2": SUITESPARSE_ROOT / "CHOLMOD" / "MATLAB" / "cholmod2.mexw64",
    }
    resolved = {name: _absolute_literal_path(path) for name, path in paths.items()}
    for name, path in resolved.items():
        require_no_reparse_chain(path, f"qualified runtime binary {name}")
        if _literal_path_text(path.resolve()) != _literal_path_text(path):
            raise LaunchError(f"qualified runtime binary {name} has a substituted canonical identity")
    if len(set(resolved.values())) != len(resolved) or any(not path.is_file() for path in resolved.values()):
        raise LaunchError("runtime binary path is missing, duplicate, or not the qualified exact location")
    return resolved


def runtime_binary_sha256(paths: Mapping[str, Path]) -> dict[str, str]:
    return {name: sha256(path) for name, path in paths.items()}


def require_runtime_binaries(repo_root: Path, griphfith_root: Path, expected: object) -> dict[str, Path]:
    paths = resolve_runtime_binaries(repo_root, griphfith_root)
    if not isinstance(expected, dict) or set(expected) != set(paths) \
            or not _exact_json_equal(runtime_binary_sha256(paths), expected):
        raise LaunchError("runtime binary bytes differ from the sealed qualified mapping")
    return paths


def _reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise LaunchError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(token: str) -> None:
    raise LaunchError(f"non-finite JSON number: {token}")


def _finite_json(value: object) -> bool:
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_finite_json(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _finite_json(item) for key, item in value.items())
    return False


def read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicates,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LaunchError(f"cannot read strict JSON {path}: {error}") from error
    if not isinstance(value, dict) or not _finite_json(value):
        raise LaunchError(f"expected a finite JSON object: {path}")
    return value


def write_json_create_new(path: Path, value: Mapping[str, object]) -> None:
    payload = json_payload(value)
    with Path(path).open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def write_bytes_create_new(path: Path, payload: bytes) -> None:
    with Path(path).open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def json_payload(value: Mapping[str, object]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"


def matlab_processes() -> list[dict[str, object]]:
    """Return actual MATLAB executables only; do not match similarly named tools."""
    script = (
        "$p=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -ieq 'MATLAB.exe'} | "
        "Select-Object ProcessId,Name,CreationDate,CommandLine); if($p.Count){$p|ConvertTo-Json -Compress}"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script], check=True,
        capture_output=True, text=True,
    )
    if not result.stdout.strip():
        return []
    value = json.loads(result.stdout)
    return value if isinstance(value, list) else [value]


def matlab_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _load_module_path(path: Path, name: str) -> Any:
    path = Path(path)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LaunchError(f"cannot load launch dependency: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    original_dont_write_bytecode = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    except Exception as error:
        raise LaunchError(f"cannot load launch dependency {path}: {error}") from error
    finally:
        sys.dont_write_bytecode = original_dont_write_bytecode
        sys.modules.pop(spec.name, None)
    return module


def _load_module(filename: str, name: str) -> Any:
    return _load_module_path(Path(__file__).with_name(filename), name)


def _absolute_literal_path(path: Path | str) -> Path:
    """Make a path absolute without dereferencing a junction, symlink, or other reparse point."""
    return Path(os.path.abspath(os.path.normpath(str(path))))


def _literal_path_text(path: Path | str) -> str:
    return os.path.normcase(str(_absolute_literal_path(path))).replace("\\", "/")


def require_no_reparse_chain(path: Path | str, label: str) -> None:
    """Reject every symlink/junction/reparse component in one qualified input path."""
    absolute = _absolute_literal_path(path)
    chain = [absolute, *absolute.parents]
    for component in chain:
        try:
            metadata = component.lstat()
        except FileNotFoundError as error:
            raise LaunchError(f"{label} path component is missing: {component}") from error
        attributes = getattr(metadata, "st_file_attributes", 0)
        if component.is_symlink() or attributes & 0x400:
            raise LaunchError(f"{label} path contains a symlink, junction, or reparse point: {component}")


def load_protocol(path: Path, name: str, expected_sha256: str | None = None) -> Any:
    """Execute a protocol snapshot only after hash validation, then recheck its disk bytes."""
    path = _absolute_literal_path(path)
    require_no_reparse_chain(path, "protocol")
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise LaunchError(f"cannot read protocol bytes: {path}") from error
    digest = hashlib.sha256(payload).hexdigest()
    expected = digest if expected_sha256 is None else expected_sha256
    if digest != expected:
        raise LaunchError(f"protocol bytes differ from the validated SHA-256: {path}")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    try:
        exec(compile(payload, str(path), "exec"), module.__dict__)
    except Exception as error:
        raise LaunchError(f"cannot execute validated protocol bytes {path}: {error}") from error
    if sha256(path) != expected:
        raise LaunchError(f"protocol bytes changed during validated load: {path}")
    return module


def _exact_json_equal(actual: object, expected: object) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            _exact_json_equal(actual[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _exact_json_equal(item, expected_item) for item, expected_item in zip(actual, expected)
        )
    return actual == expected


def clean_repository_commit(repo_root: Path) -> str:
    try:
        head = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"], check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain"], check=True,
            capture_output=True, text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise LaunchError("repository commit cannot be resolved") from error
    if len(head) != 40 or any(character not in "0123456789abcdef" for character in head):
        raise LaunchError("repository HEAD is not a full lowercase commit")
    if status:
        raise LaunchError("repository must be clean before the one-shot launch")
    return head


def _require_seal(seal_path: Path, repo_commit: str) -> dict[str, object]:
    seal = read_json(seal_path)
    required = {
        "schema_version", "status", "case_id", "authorization_capability", "resume_allowed",
        "follow_on_authorized", "extension_identity", "predecessor_evidence", "physics_closure",
        "runtime_identity",
    }
    if set(seal) != required or seal.get("schema_version") != "toy_road_t3_rev_seal_v1" \
            or seal.get("status") != "PASS" or seal.get("case_id") != CASE_ID \
            or seal.get("authorization_capability") != AUTHORIZATION_CAPABILITY \
            or seal.get("resume_allowed") is not False or seal.get("follow_on_authorized") is not False:
        raise LaunchError("seal does not authorize exactly one nonresume T3-rev execution")
    identity = seal.get("extension_identity")
    if not isinstance(identity, dict) or identity.get("repository_commit") != repo_commit \
            or identity.get("composite_producer") != "sealed_T3_base_plus_T3_rev_case_definition_extension":
        raise LaunchError("seal composite producer identity does not bind this clean repository")
    runtime = seal.get("runtime_identity")
    seal_builder = _load_module("build_t3_rev_seal.py", "t3_rev_launch_seal")
    if not _exact_json_equal(runtime, seal_builder.EXPECTED_EXECUTION):
        raise LaunchError("seal runtime identity is not the accepted exact mapping")
    return seal


def seal_consumption_marker(expected_seal_sha256: str) -> Path:
    """Return the machine-global immutable registry key for these exact seal bytes."""
    if len(expected_seal_sha256) != 64 \
            or any(character not in "0123456789abcdef" for character in expected_seal_sha256):
        raise LaunchError("snapshot seal SHA-256 is malformed")
    return _absolute_literal_path(AUTHORIZATION_STATE_ROOT) / f"{expected_seal_sha256}.json"


def _require_unconsumed_seal(expected_seal_sha256: str) -> None:
    marker = seal_consumption_marker(expected_seal_sha256)
    if marker.parent.exists():
        require_no_reparse_chain(marker.parent, "authorization state registry")
    if marker.exists():
        raise LaunchError(f"seal already consumed and cannot authorize another run root: {marker}")


def consume_seal(
        seal_path: Path, run_root: Path, expected_seal_sha256: str,
        expected_seal_bytes: bytes) -> dict[str, object]:
    """Atomically bind this exact seal to one root before the final idle check."""
    seal_path, run_root = Path(seal_path).resolve(), Path(run_root).resolve()
    live_bytes = seal_path.read_bytes()
    live_sha256 = hashlib.sha256(live_bytes).hexdigest()
    if live_bytes != expected_seal_bytes or live_sha256 != expected_seal_sha256:
        raise LaunchError("live seal bytes changed after validated preflight snapshot")
    marker = seal_consumption_marker(expected_seal_sha256)
    marker.parent.mkdir(parents=True, exist_ok=True)
    require_no_reparse_chain(marker.parent, "authorization state registry")
    value = {
        "schema_version": "toy_road_t3_rev_seal_consumption_v1",
        "case_id": CASE_ID,
        "composite_producer": "sealed_T3_base_plus_T3_rev_case_definition_extension",
        "authorization_capability": AUTHORIZATION_CAPABILITY,
        "seal_sha256": expected_seal_sha256,
        "run_root": str(run_root),
        "resume_allowed": False,
        "new_authorization_required": True,
    }
    try:
        write_json_create_new(marker, value)
    except FileExistsError as error:
        raise LaunchError(f"seal already consumed and cannot authorize another run root: {marker}") from error
    return value


def require_bridge_authorization_receipt(receipt: Mapping[str, object]) -> None:
    """Require the upstream receipt shape consumed by run_toy_road_runtime_bridge."""
    required = {
        "schema_version", "status", "authorization_scope", "authorized_entrypoint", "case_id",
        "authorization_capability", "resume_allowed", "follow_on_authorized", "source_commit",
        "launcher_repository_commit",
        "runtime_lock_sha256", "family_contract_sha256", "case_physics_contract_sha256",
        "execution_input_lock_sha256", "seal_sha256", "extension_source_manifest_sha256",
        "extension_root", "runtime_overlay_root", "run_root", "extension_shadow_sha256",
        "thread_environment", "launch_nonce", "bootstrap_helper_sha256",
    }
    if set(receipt) != required or receipt.get("schema_version") != "toy_road_t3_rev_launch_receipt_v1" \
            or receipt.get("status") != "PASS" \
            or receipt.get("authorization_scope") != "production_authorized" \
            or receipt.get("authorized_entrypoint") != "run_toy_road_runtime_bridge" \
            or receipt.get("case_id") != CASE_ID \
            or receipt.get("authorization_capability") != AUTHORIZATION_CAPABILITY \
            or receipt.get("resume_allowed") is not False \
            or receipt.get("follow_on_authorized") is not False:
        raise LaunchError("launch receipt does not authorize the runtime bridge for exactly one T3-rev case")
    digest_fields = (
        "runtime_lock_sha256", "family_contract_sha256", "case_physics_contract_sha256",
        "execution_input_lock_sha256", "seal_sha256", "extension_source_manifest_sha256",
        "bootstrap_helper_sha256",
    )
    if type(receipt.get("source_commit")) is not str or len(receipt["source_commit"]) != 40 \
            or any(character not in "0123456789abcdef" for character in receipt["source_commit"]) \
            or type(receipt.get("launcher_repository_commit")) is not str \
            or len(receipt["launcher_repository_commit"]) != 40 \
            or any(character not in "0123456789abcdef"
                   for character in receipt["launcher_repository_commit"]) \
            or any(type(receipt.get(field)) is not str or len(receipt[field]) != 64
                   or any(character not in "0123456789abcdef" for character in receipt[field])
                   for field in digest_fields):
        raise LaunchError("launch receipt bridge identity fields are malformed")
    nonce = receipt.get("launch_nonce")
    if type(nonce) is not str or len(nonce) != 64 \
            or any(character not in "0123456789abcdef" for character in nonce):
        raise LaunchError("launch receipt nonce is malformed")
    shadow = receipt.get("extension_shadow_sha256")
    if not isinstance(shadow, dict) or not shadow \
            or not all(type(path) is str and path and type(digest) is str and len(digest) == 64
                       and all(character in "0123456789abcdef" for character in digest)
                       for path, digest in shadow.items()):
        raise LaunchError("launch receipt extension shadow identity is malformed")
    expected_threads = {
        "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1", "MKL_DYNAMIC": "FALSE",
    }
    if not _exact_json_equal(receipt.get("thread_environment"), expected_threads) \
            or any(type(receipt.get(field)) is not str or not Path(receipt[field]).is_absolute()
                   for field in ("extension_root", "runtime_overlay_root", "run_root")):
        raise LaunchError("launch receipt extension or thread binding is malformed")


def _require_extension(
        repo_root: Path, extension_root: Path, seal: Mapping[str, object]) -> tuple[Path, dict[str, object], dict[str, object]]:
    sealed_base_root = repo_root / "producer_handoffs" / "toy_road_p0_repeatability_20260803"
    identity = seal["extension_identity"]
    if not isinstance(identity, dict):
        raise LaunchError("seal composite producer identity is malformed")
    manifest_path = extension_root / "EXTENSION_SOURCE_MANIFEST.json"
    inventory_path = extension_root / "SOURCE_DIFF_INVENTORY.json"
    family_path = extension_root / "FAMILY_CONTRACT.json"
    contract_path = Path(__file__).with_name("T3_REV_CONTRACT.json")
    for path, label in (
            (manifest_path, "extension source manifest"),
            (inventory_path, "extension source inventory"),
            (family_path, "extension family contract"),
            (contract_path, "T3-rev contract"),
            (extension_root / "CASE_PHYSICS_CONTRACTS.json", "extension case contracts")):
        require_no_reparse_chain(path, label)
    manifest = read_json(manifest_path)
    expected_hashes = {
        "extension_source_manifest_sha256": sha256(manifest_path),
        "extension_contract_sha256": sha256(contract_path),
        "source_diff_inventory_sha256": sha256(inventory_path),
        "extension_family_contract_sha256": sha256(family_path),
    }
    if any(identity.get(field) != digest for field, digest in expected_hashes.items()):
        raise LaunchError("extension composite identity differs from the seal")
    if manifest.get("case_id") != CASE_ID \
            or manifest.get("base_source_commit") != identity.get("base_source_commit") \
            or manifest.get("base_source_manifest_sha256") != identity.get("base_source_manifest_sha256"):
        raise LaunchError("extension source manifest differs from sealed source identity")
    verifier = _load_module("verify_extension_diff.py", "t3_rev_launch_verifier")
    try:
        verification = verifier.verify_extension_diff(sealed_base_root, extension_root)
    except Exception as error:
        raise LaunchError(f"extension source verification failed: {error}") from error
    if not _exact_json_equal(verification, identity.get("verification")):
        raise LaunchError("extension verification does not match the sealed composite identity")
    cases = read_json(extension_root / "CASE_PHYSICS_CONTRACTS.json")
    case_table = cases.get("cases")
    if not isinstance(case_table, dict):
        raise LaunchError("extension case physics contracts are malformed")
    case = case_table.get(CASE_ID)
    family_hash = cases.get("family_contract_sha256")
    if not isinstance(case, dict) or not isinstance(family_hash, str) \
            or not isinstance(case.get("case_physics_contract_sha256"), str):
        raise LaunchError("extension case hashes are malformed")
    return sealed_base_root, manifest, case


def _require_template_inputs(
        template_run: Path, runtime: Mapping[str, object], matlab: Path,
        base_protocol: Any) -> dict[str, object]:
    if _literal_path_text(template_run) != _literal_path_text(QUALIFIED_TEMPLATE_ROOT):
        raise LaunchError("template run is not the exact qualified T3 root")
    lock_path = template_run / "receipts" / "T3_EXECUTION_INPUT_LOCK.json"
    require_no_reparse_chain(lock_path, "qualified template execution lock")
    lock = read_json(lock_path)
    try:
        base_protocol.validate_execution_input_lock(lock, QUALIFIED_TEMPLATE_CASE_ID)
    except Exception as error:
        raise LaunchError(
            f"template execution lock failed authoritative protocol validation: {error}"
        ) from error
    if sha256(lock_path) != QUALIFIED_TEMPLATE_LOCK_SHA256 \
            or lock_path.read_bytes() != json_payload(lock):
        raise LaunchError("template execution lock is not the exact qualified predecessor")
    expectation = lock.get("runtime_expectations")
    if not isinstance(expectation, dict) or not matlab.is_file():
        raise LaunchError("template runtime or MATLAB executable is incomplete")
    expected_binaries = runtime.get("four_binary_sha256")
    sealed_matlab = runtime.get("matlab")
    expected_identity = {
        "schema_version": "toy_road_execution_input_lock_v1",
        "authorization_scope": "production_authorized",
        "case_id": QUALIFIED_TEMPLATE_CASE_ID,
        "case_physics_contract_sha256": QUALIFIED_TEMPLATE_CASE_CONTRACT_SHA256,
        "family_contract_sha256": runtime.get("family_contract_sha256"),
        "protocol_version": "toy-road-p0-repeatability-v2.1",
        "resume_allowed": False,
        "runtime_lock_sha256": runtime.get("runtime_lock_sha256"),
        "source_commit": runtime.get("source_commit"),
        "source_manifest_sha256": runtime.get("source_manifest_sha256"),
        "writable_roots": QUALIFIED_TEMPLATE_WRITABLE_ROOTS,
    }
    if any(not _exact_json_equal(lock.get(field), expected)
           for field, expected in expected_identity.items()) \
            or not _exact_json_equal(expectation, {
                "binary_sha256": expected_binaries,
                "matlab": sealed_matlab,
            }):
        raise LaunchError("template execution lock is not the exact qualified predecessor identity")
    matlab_identity = expectation.get("matlab")
    if not isinstance(matlab_identity, dict) or not isinstance(sealed_matlab, dict):
        raise LaunchError("template MATLAB identity is malformed")
    if not _exact_json_equal(matlab_identity, sealed_matlab):
        raise LaunchError("template MATLAB identity differs from the sealed release/update/platform mapping")
    if executable_sha256(matlab) != sealed_matlab["executable_sha256"]:
        raise LaunchError("MATLAB executable SHA-256 differs from the sealed runtime identity")
    return lock


def input_asset_sha256(path: Path) -> str:
    """Hash an input asset independently from mutable directory claims."""
    return sha256(path)


def require_qualified_runtime_paths(
        runtime: Mapping[str, object], matlab: Path, griphfith_root: Path) -> None:
    """Pin executable, GRIPHFiTH, and SuiteSparse to their sealed absolute locations."""
    executable_path = runtime.get("matlab_executable_path")
    matlab_identity = runtime.get("matlab")
    if type(executable_path) is not str or not isinstance(matlab_identity, dict):
        raise LaunchError("sealed MATLAB executable path identity is missing")
    path_order = matlab_identity.get("absolute_path_order")
    if not isinstance(path_order, list) or len(path_order) != 8 \
            or not all(type(path) is str for path in path_order):
        raise LaunchError("sealed MATLAB absolute path order is malformed")
    actual_tail = [
        griphfith_root / "Sources",
        SUITESPARSE_ROOT / "CHOLMOD" / "MATLAB",
        SUITESPARSE_ROOT / "AMD" / "MATLAB",
        SUITESPARSE_ROOT / "COLAMD" / "MATLAB",
        SUITESPARSE_ROOT / "CCOLAMD" / "MATLAB",
        SUITESPARSE_ROOT / "CAMD" / "MATLAB",
    ]
    if _literal_path_text(matlab) != _literal_path_text(executable_path):
        raise LaunchError("MATLAB executable is not the sealed qualified absolute path")
    if [_literal_path_text(path) for path in actual_tail] \
            != [_literal_path_text(path) for path in path_order[2:]]:
        raise LaunchError("GRIPHFiTH or SuiteSparse is not the sealed qualified absolute path order")
    qualified_paths = [(matlab, "MATLAB executable"), (griphfith_root, "GRIPHFiTH root")]
    qualified_paths.extend((path, "qualified MATLAB path order") for path in actual_tail)
    for path, label in qualified_paths:
        require_no_reparse_chain(path, label)
        if _literal_path_text(Path(path).resolve()) != _literal_path_text(path):
            raise LaunchError(f"{label} canonical identity differs from its literal sealed path")


def qualified_source_inventory(repo_root: Path) -> dict[str, str]:
    """Load the exact 221-record source inventory sealed by qualification evidence."""
    evidence_path = (
        repo_root / "producer_handoffs" / "rebuilt_initial_mex_qualification_20260801" /
        "build" / "SOURCE_HASHES.json"
    )
    require_no_reparse_chain(evidence_path, "qualified source inventory evidence")
    if not evidence_path.is_file() or sha256(evidence_path) != QUALIFIED_SOURCE_HASHES_SHA256:
        raise LaunchError("qualified source inventory evidence bytes are not exact")
    evidence = read_json(evidence_path)
    records = evidence.get("locked_git_tree_inventory")
    if set(evidence) != {
            "schema_version", "locked_commit", "consumed_fortran", "locked_git_tree_inventory",
    } or evidence.get("schema_version") != "rebuilt_initial_mex_source_hashes_v1" \
            or evidence.get("locked_commit") != QUALIFIED_SOURCE_COMMIT \
            or not isinstance(records, list) or len(records) != QUALIFIED_SOURCE_COUNT:
        raise LaunchError("qualified source inventory identity or closure is malformed")
    inventory: dict[str, str] = {}
    folded: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
            raise LaunchError("qualified source inventory entry is malformed")
        relative, digest = record["path"], record["sha256"]
        path = Path(relative) if type(relative) is str else Path(".")
        if type(relative) is not str or type(digest) is not str or len(digest) != 64 \
                or any(character not in "0123456789abcdef" for character in digest) \
                or path.is_absolute() or ".." in path.parts \
                or path.suffix.lower() not in {".m", ".c", ".cpp", ".h"} \
                or relative in inventory or relative.casefold() in folded:
            raise LaunchError("qualified source inventory entry or path closure is malformed")
        inventory[relative] = digest
        folded.add(relative.casefold())
    if len(inventory) != QUALIFIED_SOURCE_COUNT:
        raise LaunchError("qualified source inventory closure is not exact")
    return inventory


def require_qualified_griphfith_sources(repo_root: Path, griphfith_root: Path) -> None:
    """Validate the complete qualified source checkout before any root is claimed."""
    try:
        require_no_reparse_chain(griphfith_root, "qualified GRIPHFiTH source checkout")
        inventory = qualified_source_inventory(repo_root)
    except LaunchError as error:
        raise LaunchError(f"QUALIFIED_SOURCE_CHECKOUT_REQUIRED: {error}") from error
    actual_paths: set[str] = set()
    for path in griphfith_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".m", ".c", ".cpp", ".h"} \
                and ".git" not in path.relative_to(griphfith_root).parts:
            actual_paths.add(path.relative_to(griphfith_root).as_posix())
    if actual_paths != set(inventory):
        raise LaunchError(
            "QUALIFIED_SOURCE_CHECKOUT_REQUIRED: qualified source checkout does not have "
            "the exact 221-entry closure"
        )
    for relative, expected_digest in inventory.items():
        source = griphfith_root / Path(relative)
        try:
            require_no_reparse_chain(source, f"qualified GRIPHFiTH source {relative}")
        except LaunchError as error:
            raise LaunchError(f"QUALIFIED_SOURCE_CHECKOUT_REQUIRED: {error}") from error
        if not source.is_file():
            raise LaunchError(
                f"QUALIFIED_SOURCE_CHECKOUT_REQUIRED: qualified source is missing or not a file: {relative}"
            )
        if sha256(source) != expected_digest:
            raise LaunchError(
                f"QUALIFIED_SOURCE_CHECKOUT_REQUIRED: qualified source SHA-256 differs: {relative}"
            )


def _paths_related(left: Path, right: Path) -> bool:
    left_text = os.path.normcase(os.path.abspath(str(left)))
    right_text = os.path.normcase(os.path.abspath(str(right)))
    try:
        common = os.path.commonpath([left_text, right_text])
    except ValueError:
        return False
    return common in {left_text, right_text}


def qualified_input_asset_sha256(repo_root: Path) -> dict[str, str]:
    evidence_path = (
        repo_root / "producer_handoffs" / "rebuilt_initial_mex_qualification_20260801" /
        "build" / "SOURCE_HASHES.json"
    )
    require_no_reparse_chain(evidence_path, "input asset qualification evidence")
    if not evidence_path.is_file() or sha256(evidence_path) != QUALIFIED_SOURCE_HASHES_SHA256:
        raise LaunchError("input asset qualification evidence bytes are not exact")
    evidence = read_json(evidence_path)
    inventory = evidence.get("locked_git_tree_inventory")
    if evidence.get("schema_version") != "rebuilt_initial_mex_source_hashes_v1" \
            or evidence.get("locked_commit") \
            != "355d4c83fefc2db88c32031a2dd2623b3de85c89" \
            or not isinstance(inventory, list):
        raise LaunchError("input asset qualification evidence identity is malformed")
    required_paths = {
        f"Dependencies/meshes/{name}": name for name in EXPECTED_INPUT_ASSET_SHA256
    }
    selected: dict[str, str] = {}
    for entry in inventory:
        if not isinstance(entry, dict):
            raise LaunchError("input asset qualification evidence inventory is malformed")
        relative = entry.get("path")
        if relative in required_paths:
            name = required_paths[relative]
            if name in selected or type(entry.get("sha256")) is not str:
                raise LaunchError("input asset qualification evidence closure is malformed")
            selected[name] = entry["sha256"]
    if not _exact_json_equal(selected, EXPECTED_INPUT_ASSET_SHA256):
        raise LaunchError("input asset qualification evidence closure is not exact")
    return selected


def require_input_assets(
        repo_root: Path, input_assets_root: Path,
        writable_roots: Mapping[str, Path]) -> None:
    """Close the complete producer-read input asset set before any consumption."""
    if not input_assets_root.is_dir():
        raise LaunchError("input asset root is missing")
    expected_assets = qualified_input_asset_sha256(repo_root)
    for name, expected_digest in expected_assets.items():
        path = input_assets_root / name
        require_no_reparse_chain(path, f"input asset {name}")
        if not path.is_file():
            raise LaunchError(f"input asset is missing: {name}")
        if input_asset_sha256(path) != expected_digest:
            raise LaunchError(f"input asset SHA-256 differs from qualified evidence: {name}")
    if any(_paths_related(input_assets_root, root) for root in writable_roots.values()):
        raise LaunchError("input asset root overlaps a producer writable root")


def require_sealed_base_sources(
        sealed_base_root: Path, source_manifest_sha256: object) -> dict[str, str]:
    """Hash every file in the sealed base manifest without following reparse aliases."""
    require_no_reparse_chain(sealed_base_root, "sealed base source root")
    manifest_path = sealed_base_root / "SOURCE_MANIFEST.json"
    require_no_reparse_chain(manifest_path, "sealed base source manifest")
    if type(source_manifest_sha256) is not str or sha256(manifest_path) != source_manifest_sha256:
        raise LaunchError("sealed base SOURCE_MANIFEST.json bytes differ")
    manifest = read_json(manifest_path)
    records = manifest.get("files")
    if set(manifest) != {"schema_version", "protocol_version", "files"} \
            or manifest.get("schema_version") != "toy_road_source_manifest_v1" \
            or not isinstance(records, list) or not records:
        raise LaunchError("sealed base source manifest closure is malformed")
    inventory: dict[str, str] = {}
    folded: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
            raise LaunchError("sealed base source manifest entry is malformed")
        relative, digest = record["path"], record["sha256"]
        candidate = Path(relative) if type(relative) is str else Path(".")
        if type(relative) is not str or type(digest) is not str or len(digest) != 64 \
                or candidate.is_absolute() or ".." in candidate.parts \
                or relative in inventory or relative.casefold() in folded:
            raise LaunchError("sealed base source manifest path closure is malformed")
        path = sealed_base_root / candidate
        require_no_reparse_chain(path, "sealed base source")
        if not path.is_file() or sha256(path) != digest:
            raise LaunchError(f"sealed base source bytes differ: {relative}")
        inventory[relative] = digest
        folded.add(relative.casefold())
    if inventory.get("toy_road_protocol.py") != QUALIFIED_BASE_PROTOCOL_SHA256:
        raise LaunchError("sealed base protocol is not in the exact source closure")
    return inventory


def _extension_shadow_hashes(manifest: Mapping[str, object]) -> dict[str, str]:
    entries = manifest.get("shadow_files")
    if not isinstance(entries, list) or not entries:
        raise LaunchError("extension source manifest shadow closure is missing")
    output: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise LaunchError("extension source manifest shadow entry is malformed")
        relative, digest = entry["path"], entry["sha256"]
        if type(relative) is not str or type(digest) is not str or len(digest) != 64 \
                or Path(relative).is_absolute() or ".." in Path(relative).parts \
                or relative in output or relative.casefold() in {path.casefold() for path in output}:
            raise LaunchError("extension source manifest shadow identity is malformed")
        output[relative] = digest
    return output


def validate_runtime_overlay_inputs(
        extension_root: Path, manifest: Mapping[str, object]) -> tuple[dict[str, str], dict[str, bytes]]:
    """Validate and snapshot every extension shadow before a run root exists."""
    shadow_hashes = _extension_shadow_hashes(manifest)
    payloads: dict[str, bytes] = {}
    for relative, expected_digest in shadow_hashes.items():
        source = extension_root / relative
        require_no_reparse_chain(source, f"extension shadow {relative}")
        if not source.is_file():
            raise LaunchError(f"extension shadow is missing before launch: {relative}")
        payload = source.read_bytes()
        if hashlib.sha256(payload).hexdigest() != expected_digest:
            raise LaunchError(f"extension shadow bytes changed before launch: {relative}")
        payloads[relative] = payload
    return shadow_hashes, payloads


def materialize_runtime_overlay(
        shadow_payloads: Mapping[str, bytes], runtime_overlay: Path,
        initial_source: Path) -> None:
    """Materialize only the already-validated overlay snapshot into a claimed root."""
    runtime_overlay.mkdir(parents=True, exist_ok=False)
    for relative, payload in shadow_payloads.items():
        target = runtime_overlay / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    helper_target = runtime_overlay / BOOTSTRAP_HELPER_RELATIVE
    with helper_target.open("xb") as stream:
        stream.write(BOOTSTRAP_HELPER_BYTES)
        stream.flush()
        os.fsync(stream.fileno())
    initial_target = (
        runtime_overlay / "+phase_field" / "+mex" / "+fem" / "+assembly" /
        "+equilibrium" / "initial.mexw64"
    )
    initial_target.parent.mkdir(parents=True, exist_ok=True)
    os.link(initial_source, initial_target)


def require_materialized_runtime_overlay(
        runtime_overlay: Path, shadow_hashes: Mapping[str, str],
        expected_binaries: object) -> None:
    """Close every file, directory, byte, and reparse identity in the launch overlay."""
    if not isinstance(expected_binaries, dict) or type(expected_binaries.get("initial")) is not str:
        raise LaunchError("runtime overlay initial MEX identity is malformed")
    initial_relative = "+phase_field/+mex/+fem/+assembly/+equilibrium/initial.mexw64"
    expected_files = dict(shadow_hashes)
    expected_files[initial_relative] = expected_binaries["initial"]
    expected_files[BOOTSTRAP_HELPER_RELATIVE] = BOOTSTRAP_HELPER_SHA256
    expected_directories: set[str] = set()
    for relative in expected_files:
        parent = Path(relative).parent
        while str(parent) != ".":
            expected_directories.add(parent.as_posix())
            parent = parent.parent
    require_no_reparse_chain(runtime_overlay, "materialized runtime overlay")
    actual_files: set[str] = set()
    actual_directories: set[str] = set()
    for path in runtime_overlay.rglob("*"):
        relative = path.relative_to(runtime_overlay).as_posix()
        require_no_reparse_chain(path, f"materialized runtime overlay path {relative}")
        if path.is_dir():
            actual_directories.add(relative)
        elif path.is_file():
            actual_files.add(relative)
        else:
            raise LaunchError(f"materialized runtime overlay has a non-file path: {relative}")
    if actual_files != set(expected_files) or actual_directories != expected_directories:
        raise LaunchError("materialized runtime overlay inventory is not the exact qualified closure")
    for relative, expected_digest in expected_files.items():
        if sha256(runtime_overlay / Path(relative)) != expected_digest:
            raise LaunchError(f"materialized runtime overlay bytes differ: {relative}")


def build_future_execution_lock(
        generated_protocol: Any, runtime: Mapping[str, object], expected_binaries: object,
        family_hash: str, case_hash: str, matlab_paths: list[Path],
        roots: Mapping[str, Path]) -> dict[str, object]:
    """Construct and authoritatively validate the future lock before creating its root."""
    sealed_matlab = runtime.get("matlab")
    if not isinstance(sealed_matlab, dict):
        raise LaunchError("seal MATLAB identity is malformed")
    runtime_expectations = {
        "binary_sha256": copy.deepcopy(expected_binaries),
        "matlab": {
            **copy.deepcopy(sealed_matlab),
            "absolute_path_order": [str(path) for path in matlab_paths],
        },
    }
    try:
        lock = generated_protocol.build_execution_input_lock(
            authorization_scope="production_authorized",
            role=CASE_ID,
            family_contract_sha256=family_hash,
            case_physics_contract_sha256=case_hash,
            source_commit=runtime["source_commit"],
            runtime_lock_sha256=runtime["runtime_lock_sha256"],
            source_manifest_sha256=runtime["source_manifest_sha256"],
            runtime_expectations=runtime_expectations,
            roots={name: str(path) for name, path in roots.items()},
            launch_timestamp_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            no_clobber_receipt_id=uuid.uuid4().hex,
        )
        generated_protocol.validate_execution_input_lock(lock, CASE_ID)
    except Exception as error:
        raise LaunchError(
            f"generated execution lock failed authoritative protocol validation: {error}"
        ) from error
    return lock


def _write_busy_receipt(receipts: Path, processes: list[dict[str, object]]) -> None:
    write_json_create_new(receipts / "BUSY_NO_LAUNCH.json", {
        "schema_version": "toy_road_t3_rev_busy_no_launch_v1",
        "status": "BUSY_NO_LAUNCH",
        "case_id": CASE_ID,
        "resume_allowed": False,
        "new_authorization_required": True,
        "observed_processes": processes,
    })


def _invalidate_pass_receipt(receipts: Path) -> None:
    live = receipts / "T3_REV_LAUNCH_RECEIPT.json"
    if live.exists():
        invalidated = receipts / "T3_REV_LAUNCH_RECEIPT.INVALIDATED.json"
        os.replace(live, invalidated)


def _raise_prepared_failure(
        seal_path: Path, expected_seal_sha256: str, expected_seal_bytes: bytes,
        run_root: Path, receipts: Path, error: Exception) -> None:
    """Consume a root claimed after PASS preflight and record that no launch occurred."""
    marker_error: Exception | None = None
    invalidation_error: Exception | None = None
    try:
        _invalidate_pass_receipt(receipts)
    except OSError as receipt_error:
        invalidation_error = receipt_error
    if not seal_consumption_marker(expected_seal_sha256).exists():
        try:
            consume_seal(
                seal_path, run_root, expected_seal_sha256, expected_seal_bytes
            )
        except Exception as consumed_error:  # preserve both fail-closed diagnostics
            marker_error = consumed_error
    try:
        receipts.mkdir(parents=True, exist_ok=True)
        failure_path = receipts / "PREPARED_NO_LAUNCH.json"
        if not failure_path.exists():
            write_json_create_new(failure_path, {
                "schema_version": "toy_road_t3_rev_prepared_no_launch_v1",
                "status": "PREPARED_NO_LAUNCH",
                "case_id": CASE_ID,
                "resume_allowed": False,
                "new_authorization_required": True,
                "error_type": type(error).__name__,
            })
    except OSError:
        pass
    details = []
    if marker_error:
        details.append(f"seal consumption also failed: {marker_error}")
    if invalidation_error:
        details.append(f"PASS receipt invalidation failed: {invalidation_error}")
    detail = "; " + "; ".join(details) if details else ""
    raise PreparedLaunchError(
        f"validated launch root was consumed/prepared but no process was launched: {error}{detail}"
    ) from error


def open_launch_logs(run_root: Path) -> tuple[Any, Any]:
    stdout = None
    try:
        stdout = (run_root / "T3_REV.stdout.log").open("xb")
        stderr = (run_root / "T3_REV.stderr.log").open("xb")
    except OSError:
        if stdout is not None:
            stdout.close()
        raise
    return stdout, stderr


def _best_effort_unlink(path: Path) -> None:
    try:
        path.unlink()
    except Exception:
        pass


def prepare_launch_receipt(
        launch_receipt_path: Path, launch_receipt_bytes: bytes,
        expected_receipt_sha256: str) -> Path:
    """Durably prepare complete credential bytes without making them authoritative."""
    temporary = launch_receipt_path.with_name(
        f".{launch_receipt_path.name}.{uuid.uuid4().hex}.tmp"
    )
    if launch_receipt_path.exists():
        raise LaunchCredentialError("launch credential path already exists")
    try:
        if hashlib.sha256(launch_receipt_bytes).hexdigest() != expected_receipt_sha256:
            raise LaunchCredentialError("precomputed launch credential bytes changed")
        write_bytes_create_new(temporary, launch_receipt_bytes)
        if sha256(temporary) != expected_receipt_sha256:
            raise LaunchCredentialError("temporary launch credential SHA-256 differs")
    except Exception:
        _best_effort_unlink(temporary)
        raise
    return temporary


def publish_launch_receipt(temporary: Path, launch_receipt_path: Path) -> None:
    """Make prepared exact bytes visible at the sole atomic launch commit point."""
    try:
        os.link(temporary, launch_receipt_path)
    except Exception:
        _best_effort_unlink(temporary)
        raise
    _best_effort_unlink(temporary)


def write_launcher_pid(run_root: Path, pid: object) -> None:
    """Durably record the child identity before its credential can become visible."""
    write_bytes_create_new(run_root / "launcher.pid", f"{pid}\n".encode("ascii"))


def close_launch_logs(stdout: Any, stderr: Any) -> None:
    """Attempt both parent-side closes and surface the first failure."""
    failures: list[Exception] = []
    for stream in (stdout, stderr):
        try:
            stream.close()
        except Exception as error:
            failures.append(error)
    if failures:
        raise failures[0]


def _best_effort_close_launch_logs(stdout: Any, stderr: Any) -> None:
    try:
        close_launch_logs(stdout, stderr)
    except Exception:
        pass


def raise_launch_credential_failure(
        receipts: Path, launch_receipt_path: Path, process: Any, error: Exception) -> None:
    """Record a started-but-unauthorized bootstrap without retrying or exposing PASS."""
    failure = receipts / "LAUNCH_CREDENTIAL_FAILED.json"
    try:
        write_json_create_new(failure, {
            "schema_version": "toy_road_t3_rev_launch_credential_failed_v1",
            "status": "LAUNCH_CREDENTIAL_FAILED",
            "case_id": CASE_ID,
            "process_started": True,
            "pid": process.pid,
            "resume_allowed": False,
            "retry_allowed": False,
            "new_authorization_required": True,
            "error_type": type(error).__name__,
        })
    except OSError:
        pass
    raise LaunchCredentialError(
        f"MATLAB bootstrap started but launch credential publication failed: {error}"
    ) from error


def require_final_launch_inputs(
        repo_root: Path, seal_path: Path, expected_seal_bytes: bytes,
        expected_seal_sha256: str, extension_root: Path, sealed_base_root: Path,
        manifest: Mapping[str, object], runtime: Mapping[str, object], matlab: Path,
        griphfith_root: Path, input_assets_root: Path, runtime_overlay: Path,
        roots: Mapping[str, Path],
        initial_shadow_hashes: Mapping[str, str], initial_shadow_payloads: Mapping[str, bytes],
        expected_binaries: object) -> None:
    """Repeat every mutable identity check at the last no-process boundary."""
    live_seal_bytes = seal_path.read_bytes()
    if live_seal_bytes != expected_seal_bytes \
            or hashlib.sha256(live_seal_bytes).hexdigest() != expected_seal_sha256:
        raise LaunchError("final live seal bytes differ from the validated preflight snapshot")
    require_no_reparse_chain(repo_root, "launcher repository")
    require_no_reparse_chain(seal_path, "T3-rev seal")
    require_no_reparse_chain(extension_root, "T3-rev extension")
    require_no_reparse_chain(input_assets_root, "input assets")
    require_qualified_runtime_paths(runtime, matlab, griphfith_root)
    if executable_sha256(matlab) != runtime["matlab"]["executable_sha256"]:
        raise LaunchError("final MATLAB executable SHA-256 differs from sealed identity")
    final_base, final_manifest, _ = _require_extension(repo_root, extension_root, {
        **read_json(seal_path),
    })
    if _literal_path_text(final_base) != _literal_path_text(sealed_base_root) \
            or not _exact_json_equal(final_manifest, manifest):
        raise LaunchError("final extension/base identity differs from preflight")
    require_sealed_base_sources(sealed_base_root, runtime.get("source_manifest_sha256"))
    base_protocol_path = sealed_base_root / "toy_road_protocol.py"
    if sha256(base_protocol_path) != QUALIFIED_BASE_PROTOCOL_SHA256:
        raise LaunchError("final sealed base protocol bytes differ")
    final_shadow_hashes, final_shadow_payloads = validate_runtime_overlay_inputs(
        extension_root, manifest
    )
    if not _exact_json_equal(final_shadow_hashes, initial_shadow_hashes) \
            or final_shadow_payloads != initial_shadow_payloads:
        raise LaunchError("final extension shadow snapshot differs from preflight")
    protocol_digest = final_shadow_hashes.get("toy_road_protocol.py")
    if protocol_digest is None or sha256(extension_root / "toy_road_protocol.py") != protocol_digest:
        raise LaunchError("final extension protocol bytes differ")
    require_runtime_binaries(repo_root, griphfith_root, expected_binaries)
    require_qualified_griphfith_sources(repo_root, griphfith_root)
    require_input_assets(repo_root, input_assets_root, roots)
    require_materialized_runtime_overlay(runtime_overlay, initial_shadow_hashes, expected_binaries)


def launch_t3_rev(
        repo_root: Path, run_root: Path, seal_path: Path, extension_root: Path,
        template_run: Path, griphfith_root: Path, input_assets_root: Path,
        matlab: Path) -> dict[str, object]:
    """Create the sole T3-rev process after both idle checks and all input locks."""
    first_processes = matlab_processes()
    if first_processes:
        raise BusyExperimentError("BUSY_NO_LAUNCH: existing MATLAB experiment blocks T3-rev")
    repo_root, run_root = _absolute_literal_path(repo_root), _absolute_literal_path(run_root)
    seal_path, extension_root = _absolute_literal_path(seal_path), _absolute_literal_path(extension_root)
    template_run = _absolute_literal_path(template_run)
    griphfith_root = _absolute_literal_path(griphfith_root)
    input_assets_root, matlab = _absolute_literal_path(input_assets_root), _absolute_literal_path(matlab)
    if run_root.exists():
        raise FileExistsError(f"T3-rev run root already exists: {run_root}")
    require_no_reparse_chain(repo_root, "launcher repository")
    require_no_reparse_chain(seal_path, "T3-rev seal")
    require_no_reparse_chain(extension_root, "T3-rev extension")
    require_no_reparse_chain(template_run, "qualified template run")
    require_no_reparse_chain(input_assets_root, "input assets")
    seal_bytes = seal_path.read_bytes()
    seal_sha256 = hashlib.sha256(seal_bytes).hexdigest()
    repo_commit = clean_repository_commit(repo_root)
    seal = _require_seal(seal_path, repo_commit)
    canonical_seal_bytes = json_payload(seal)
    if seal_path.read_bytes() != seal_bytes or seal_bytes != canonical_seal_bytes:
        raise LaunchError(
            "seal bytes changed or are not the seal builder's exact canonical JSON encoding"
        )
    seal_bytes = canonical_seal_bytes
    seal_sha256 = hashlib.sha256(seal_bytes).hexdigest()
    sealed_base_root, manifest, case = _require_extension(repo_root, extension_root, seal)
    seal_builder = _load_module("build_t3_rev_seal.py", "t3_rev_launch_seal_evidence")
    try:
        seal_builder.require_seal_evidence(repo_root, extension_root, seal)
    except Exception as error:
        raise LaunchError(f"seal predecessor/physics closure failed: {error}") from error
    runtime = seal["runtime_identity"]
    if not isinstance(runtime, dict):
        raise LaunchError("seal runtime identity is malformed")
    require_qualified_runtime_paths(runtime, matlab, griphfith_root)
    require_sealed_base_sources(sealed_base_root, runtime.get("source_manifest_sha256"))
    shadow_hashes, shadow_payloads = validate_runtime_overlay_inputs(extension_root, manifest)
    generated_protocol_digest = shadow_hashes.get("toy_road_protocol.py")
    if generated_protocol_digest is None:
        raise LaunchError("extension protocol is absent from the validated shadow closure")
    base_protocol = load_protocol(
        sealed_base_root / "toy_road_protocol.py", "t3_rev_launch_base_protocol",
        QUALIFIED_BASE_PROTOCOL_SHA256,
    )
    generated_protocol = load_protocol(
        extension_root / "toy_road_protocol.py", "t3_rev_launch_generated_protocol",
        generated_protocol_digest,
    )
    _require_template_inputs(template_run, runtime, matlab, base_protocol)
    if not (sealed_base_root / "run_toy_road_runtime_bridge.m").is_file():
        raise LaunchError("sealed source inputs are incomplete")
    expected_binaries = runtime.get("four_binary_sha256")
    binary_paths = require_runtime_binaries(repo_root, griphfith_root, expected_binaries)
    require_qualified_griphfith_sources(repo_root, griphfith_root)
    initial_source = binary_paths["initial"]
    roots = {name: run_root / name for name in ("output", "work", "temp", "tmp", "pref", "cache")}
    roots["matlab_startup_pref"] = run_root / "pref.matlab-startup"
    receipts = run_root / "receipts"
    runtime_overlay = run_root / ".toy-road-runtime-overlay"
    require_input_assets(repo_root, input_assets_root, roots)
    _require_unconsumed_seal(seal_sha256)
    matlab_paths = [
        runtime_overlay,
        sealed_base_root,
        griphfith_root / "Sources",
        SUITESPARSE_ROOT / "CHOLMOD" / "MATLAB",
        SUITESPARSE_ROOT / "AMD" / "MATLAB",
        SUITESPARSE_ROOT / "COLAMD" / "MATLAB",
        SUITESPARSE_ROOT / "CCOLAMD" / "MATLAB",
        SUITESPARSE_ROOT / "CAMD" / "MATLAB",
    ]
    family = read_json(extension_root / "CASE_PHYSICS_CONTRACTS.json")
    family_hash = family.get("family_contract_sha256")
    case_hash = case.get("case_physics_contract_sha256")
    if not isinstance(family_hash, str) or not isinstance(case_hash, str):
        raise LaunchError("extension family or case hash is malformed")
    lock = build_future_execution_lock(
        generated_protocol, runtime, expected_binaries, family_hash, case_hash, matlab_paths, roots
    )
    lock_path = receipts / "T3_REV_EXECUTION_INPUT_LOCK.json"
    lock_bytes = generated_protocol.canonical_json_bytes(lock)
    lock_sha256 = hashlib.sha256(lock_bytes).hexdigest()
    launch_receipt_path = receipts / "T3_REV_LAUNCH_RECEIPT.json"
    launch_nonce = secrets.token_hex(32)
    launch_receipt = {
        "schema_version": "toy_road_t3_rev_launch_receipt_v1",
        "status": "PASS",
        "authorization_scope": "production_authorized",
        "authorized_entrypoint": "run_toy_road_runtime_bridge",
        "case_id": CASE_ID,
        "authorization_capability": AUTHORIZATION_CAPABILITY,
        "resume_allowed": False,
        "follow_on_authorized": False,
        "source_commit": runtime["source_commit"],
        "launcher_repository_commit": repo_commit,
        "runtime_lock_sha256": runtime["runtime_lock_sha256"],
        "family_contract_sha256": family_hash,
        "case_physics_contract_sha256": case_hash,
        "execution_input_lock_sha256": lock_sha256,
        "seal_sha256": seal_sha256,
        "extension_source_manifest_sha256": sha256(extension_root / "EXTENSION_SOURCE_MANIFEST.json"),
        "extension_root": str(extension_root),
        "runtime_overlay_root": str(runtime_overlay),
        "run_root": str(run_root),
        "extension_shadow_sha256": shadow_hashes,
        "thread_environment": copy.deepcopy(runtime["thread_settings"]),
        "launch_nonce": launch_nonce,
        "bootstrap_helper_sha256": BOOTSTRAP_HELPER_SHA256,
    }
    require_bridge_authorization_receipt(launch_receipt)
    launch_receipt_bytes = json_payload(launch_receipt)
    launch_receipt_sha256 = hashlib.sha256(launch_receipt_bytes).hexdigest()
    measurement_path = receipts / "T3_REV_RUNTIME_MEASUREMENT.json"
    prefix = os.pathsep.join(str(path) for path in matlab_paths)
    batch = (
        f"path([{matlab_literal(prefix)} pathsep path]);"
        "toy_road_wait_for_launch_receipt("
        f"{matlab_literal(str(launch_receipt_path))},"
        f"{matlab_literal(launch_receipt_sha256)},"
        f"{matlab_literal(launch_nonce)},"
        f"{matlab_literal(seal_sha256)},"
        f"{matlab_literal(CASE_ID)},"
        f"{matlab_literal(lock_sha256)},"
        f"{matlab_literal(str(run_root))},30);"
        f"run_toy_road_runtime_bridge({matlab_literal(str(lock_path))},{matlab_literal(str(measurement_path))});"
    )
    env = os.environ.copy()
    env.update({
        "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_DYNAMIC": "FALSE",
        "TEMP": str(roots["temp"]), "TMP": str(roots["tmp"]),
        "MATLAB_PREFDIR": str(roots["matlab_startup_pref"]), "MCR_CACHE_ROOT": str(roots["cache"]),
        "TOY_ROAD_CASE_ROLE": "T3_rev_loading_order",
        "TOY_ROAD_SOURCE_COMMIT": str(lock["source_commit"]),
        "TOY_ROAD_RUNTIME_LOCK_SHA256": str(runtime["runtime_lock_sha256"]),
        "TOY_ROAD_FAMILY_CONTRACT_SHA256": family_hash,
        "TOY_ROAD_CASE_PHYSICS_CONTRACT_SHA256": case_hash,
        "TOY_ROAD_EXECUTION_INPUT_LOCK_SHA256": lock_sha256,
        "TOY_ROAD_OUTPUT_ROOT": str(roots["output"]), "TOY_ROAD_WORK_ROOT": str(roots["work"]),
        "TOY_ROAD_TEMP_ROOT": str(roots["temp"]), "TOY_ROAD_TMP_ROOT": str(roots["tmp"]),
        "TOY_ROAD_PREF_ROOT": str(roots["pref"]), "TOY_ROAD_CACHE_ROOT": str(roots["cache"]),
        "TOY_ROAD_INPUT_ASSETS_ROOT": str(input_assets_root),
        "TOY_ROAD_AUTHORIZATION_RECEIPT": str(launch_receipt_path),
    })
    root_created = False
    try:
        run_root.mkdir(parents=True, exist_ok=False)
        root_created = True
        receipts.mkdir(parents=True, exist_ok=False)
        materialize_runtime_overlay(shadow_payloads, runtime_overlay, initial_source)
        write_bytes_create_new(lock_path, lock_bytes)
    except OSError as error:
        if root_created:
            _raise_prepared_failure(seal_path, seal_sha256, seal_bytes, run_root, receipts, error)
        raise
    try:
        consume_seal(seal_path, run_root, seal_sha256, seal_bytes)
    except (OSError, LaunchError) as error:
        _raise_prepared_failure(seal_path, seal_sha256, seal_bytes, run_root, receipts, error)
    try:
        require_final_launch_inputs(
            repo_root, seal_path, seal_bytes, seal_sha256, extension_root,
            sealed_base_root, manifest, runtime,
            matlab, griphfith_root, input_assets_root, runtime_overlay, roots, shadow_hashes,
            shadow_payloads, expected_binaries,
        )
    except Exception as error:
        _raise_prepared_failure(seal_path, seal_sha256, seal_bytes, run_root, receipts, error)
    try:
        final_processes = matlab_processes()
    except Exception as error:
        _raise_prepared_failure(seal_path, seal_sha256, seal_bytes, run_root, receipts, error)
    if final_processes:
        try:
            _write_busy_receipt(receipts, final_processes)
        except OSError as error:
            _raise_prepared_failure(seal_path, seal_sha256, seal_bytes, run_root, receipts, error)
        raise BusyExperimentError("BUSY_NO_LAUNCH: final process check blocks T3-rev launch")
    try:
        stdout, stderr = open_launch_logs(run_root)
    except OSError as error:
        _raise_prepared_failure(seal_path, seal_sha256, seal_bytes, run_root, receipts, error)
    try:
        process = Popen(
            [str(matlab), "-batch", batch], cwd=run_root, env=env, stdout=stdout, stderr=stderr,
            creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
        )
    except Exception as error:
        _best_effort_close_launch_logs(stdout, stderr)
        _raise_prepared_failure(seal_path, seal_sha256, seal_bytes, run_root, receipts, error)
    temporary_receipt: Path | None = None
    try:
        temporary_receipt = prepare_launch_receipt(
            launch_receipt_path, launch_receipt_bytes, launch_receipt_sha256
        )
        write_launcher_pid(run_root, process.pid)
        close_launch_logs(stdout, stderr)
        launched_result = {
            "status": "LAUNCHED", "pid": process.pid,
            "run_root": str(run_root), "resume_allowed": False,
        }
    except Exception as error:
        if temporary_receipt is not None:
            _best_effort_unlink(temporary_receipt)
        _best_effort_close_launch_logs(stdout, stderr)
        raise_launch_credential_failure(receipts, launch_receipt_path, process, error)
    try:
        publish_launch_receipt(temporary_receipt, launch_receipt_path)
    except Exception as error:
        raise_launch_credential_failure(receipts, launch_receipt_path, process, error)
    return launched_result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--seal", dest="seal_path", type=Path, required=True)
    parser.add_argument("--extension-root", type=Path, required=True)
    parser.add_argument("--template-run", type=Path, required=True)
    parser.add_argument("--gripfith-root", dest="griphfith_root", type=Path, required=True)
    parser.add_argument("--input-assets-root", type=Path, required=True)
    parser.add_argument("--matlab", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(launch_t3_rev(**vars(args)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
