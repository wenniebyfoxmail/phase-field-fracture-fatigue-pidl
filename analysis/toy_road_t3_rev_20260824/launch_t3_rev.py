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
import subprocess
from subprocess import Popen
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping


CASE_ID = "T3_rev_loading_order"
AUTHORIZATION_CAPABILITY = "exactly_one_T3_rev_loading_order_execution"
SUITESPARSE_ROOT = Path(r"C:\SuiteSparse\SuiteSparse-dev")
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200


class BusyExperimentError(RuntimeError):
    """Raised when an existing experiment makes this one-shot launch unsafe."""


class LaunchError(RuntimeError):
    """Raised when the sealed launch inputs cannot be proven consistent."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
    with Path(path).open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


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


def _load_module(filename: str, name: str) -> Any:
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LaunchError(f"cannot load launch dependency: {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise LaunchError(f"cannot load launch dependency {filename}: {error}") from error
    finally:
        sys.modules.pop(spec.name, None)
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


def _require_template_inputs(template_run: Path, runtime: Mapping[str, object], input_assets_root: Path, matlab: Path) -> dict[str, object]:
    lock = read_json(template_run / "receipts" / "T2_EXECUTION_INPUT_LOCK.json")
    expectation = lock.get("runtime_expectations")
    if not isinstance(expectation, dict) or not input_assets_root.is_dir() or not matlab.is_file():
        raise LaunchError("runtime or input assets are incomplete")
    expected_binaries = runtime.get("four_binary_sha256")
    if lock.get("runtime_lock_sha256") != runtime.get("runtime_lock_sha256") \
            or lock.get("source_manifest_sha256") != runtime.get("source_manifest_sha256") \
            or expectation.get("binary_sha256") != expected_binaries:
        raise LaunchError("template runtime identity differs from the seal")
    matlab_identity = expectation.get("matlab")
    sealed_matlab = runtime.get("matlab")
    if not isinstance(matlab_identity, dict) or not isinstance(sealed_matlab, dict):
        raise LaunchError("template MATLAB identity is malformed")
    for field in ("version", "computer", "executable_sha256", "blas", "lapack"):
        if matlab_identity.get(field) != sealed_matlab.get(field):
            raise LaunchError("template MATLAB identity differs from the seal")
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


def launch_t3_rev(
        repo_root: Path, run_root: Path, seal_path: Path, extension_root: Path,
        template_run: Path, griphfith_root: Path, input_assets_root: Path,
        matlab: Path) -> dict[str, object]:
    """Create the sole T3-rev process after both idle checks and all input locks."""
    first_processes = matlab_processes()
    if first_processes:
        raise BusyExperimentError("BUSY_NO_LAUNCH: existing MATLAB experiment blocks T3-rev")
    repo_root, run_root = Path(repo_root).resolve(), Path(run_root).resolve()
    seal_path, extension_root = Path(seal_path).resolve(), Path(extension_root).resolve()
    template_run, griphfith_root = Path(template_run).resolve(), Path(griphfith_root).resolve()
    input_assets_root, matlab = Path(input_assets_root).resolve(), Path(matlab).resolve()
    if run_root.exists():
        raise FileExistsError(f"T3-rev run root already exists: {run_root}")
    repo_commit = clean_repository_commit(repo_root)
    seal = _require_seal(seal_path, repo_commit)
    sealed_base_root, manifest, case = _require_extension(repo_root, extension_root, seal)
    runtime = seal["runtime_identity"]
    if not isinstance(runtime, dict):
        raise LaunchError("seal runtime identity is malformed")
    template = _require_template_inputs(template_run, runtime, input_assets_root, matlab)
    initial_source = repo_root / "producer_handoffs" / "rebuilt_initial_mex_qualification_20260801" / "runtime" / "initial.mexw64"
    if not initial_source.is_file() or not (sealed_base_root / "run_toy_road_runtime_bridge.m").is_file():
        raise LaunchError("sealed source inputs are incomplete")

    roots = {name: run_root / name for name in ("output", "work", "temp", "tmp", "pref", "cache", "receipts")}
    roots["matlab_startup_pref"] = run_root / "pref.matlab-startup"
    runtime_overlay = run_root / ".toy-road-runtime-overlay"
    initial_target = runtime_overlay / "+phase_field" / "+mex" / "+fem" / "+assembly" / "+equilibrium" / "initial.mexw64"
    run_root.mkdir(parents=True, exist_ok=False)
    for path in (*roots.values(), initial_target.parent):
        path.mkdir(parents=True, exist_ok=False)
    os.link(initial_source, initial_target)
    matlab_paths = [
        runtime_overlay,
        extension_root,
        sealed_base_root,
        griphfith_root / "Sources",
        SUITESPARSE_ROOT / "CHOLMOD" / "MATLAB",
        SUITESPARSE_ROOT / "AMD" / "MATLAB",
        SUITESPARSE_ROOT / "COLAMD" / "MATLAB",
        SUITESPARSE_ROOT / "CCOLAMD" / "MATLAB",
        SUITESPARSE_ROOT / "CAMD" / "MATLAB",
    ]
    if not (griphfith_root / "Sources").is_dir():
        raise LaunchError("GRIPHFiTH source identity is incomplete")
    family = read_json(extension_root / "CASE_PHYSICS_CONTRACTS.json")
    family_hash = family.get("family_contract_sha256")
    case_hash = case.get("case_physics_contract_sha256")
    if not isinstance(family_hash, str) or not isinstance(case_hash, str):
        raise LaunchError("extension family or case hash is malformed")
    lock = copy.deepcopy(template)
    lock.update({
        "case_id": CASE_ID,
        "case_physics_contract_sha256": case_hash,
        "family_contract_sha256": family_hash,
        "source_commit": repo_commit,
        "launch_timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "no_clobber_receipt_id": uuid.uuid4().hex,
        "resume_allowed": False,
        "writable_roots": {name: str(path) for name, path in roots.items()},
        "extension_source_manifest_sha256": sha256(extension_root / "EXTENSION_SOURCE_MANIFEST.json"),
    })
    runtime_expectations = lock.get("runtime_expectations")
    if not isinstance(runtime_expectations, dict) or not isinstance(runtime_expectations.get("matlab"), dict):
        raise LaunchError("template lock lacks MATLAB expectations")
    runtime_expectations["matlab"]["absolute_path_order"] = [str(path) for path in matlab_paths]
    lock_path = roots["receipts"] / "T3_REV_EXECUTION_INPUT_LOCK.json"
    write_json_create_new(lock_path, lock)
    launch_receipt_path = roots["receipts"] / "T3_REV_LAUNCH_RECEIPT.json"
    write_json_create_new(launch_receipt_path, {
        "schema_version": "toy_road_t3_rev_launch_receipt_v1",
        "status": "PREPARED",
        "case_id": CASE_ID,
        "authorization_capability": AUTHORIZATION_CAPABILITY,
        "resume_allowed": False,
        "source_commit": repo_commit,
        "runtime_lock_sha256": runtime["runtime_lock_sha256"],
        "family_contract_sha256": family_hash,
        "case_physics_contract_sha256": case_hash,
        "execution_input_lock_sha256": sha256(lock_path),
        "seal_sha256": sha256(seal_path),
        "extension_source_manifest_sha256": sha256(extension_root / "EXTENSION_SOURCE_MANIFEST.json"),
    })
    measurement_path = roots["receipts"] / "T3_REV_RUNTIME_MEASUREMENT.json"
    prefix = os.pathsep.join(str(path) for path in matlab_paths)
    batch = (
        f"path([{matlab_literal(prefix)} pathsep path]);"
        f"run_toy_road_runtime_bridge({matlab_literal(str(lock_path))},{matlab_literal(str(measurement_path))});"
    )
    env = os.environ.copy()
    env.update({
        "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_DYNAMIC": "FALSE",
        "TEMP": str(roots["temp"]), "TMP": str(roots["tmp"]),
        "MATLAB_PREFDIR": str(roots["matlab_startup_pref"]), "MCR_CACHE_ROOT": str(roots["cache"]),
        "TOY_ROAD_CASE_ROLE": "T3_rev_loading_order", "TOY_ROAD_SOURCE_COMMIT": repo_commit,
        "TOY_ROAD_RUNTIME_LOCK_SHA256": str(runtime["runtime_lock_sha256"]),
        "TOY_ROAD_FAMILY_CONTRACT_SHA256": family_hash,
        "TOY_ROAD_CASE_PHYSICS_CONTRACT_SHA256": case_hash,
        "TOY_ROAD_EXECUTION_INPUT_LOCK_SHA256": sha256(lock_path),
        "TOY_ROAD_OUTPUT_ROOT": str(roots["output"]), "TOY_ROAD_WORK_ROOT": str(roots["work"]),
        "TOY_ROAD_TEMP_ROOT": str(roots["temp"]), "TOY_ROAD_TMP_ROOT": str(roots["tmp"]),
        "TOY_ROAD_PREF_ROOT": str(roots["pref"]), "TOY_ROAD_CACHE_ROOT": str(roots["cache"]),
        "TOY_ROAD_INPUT_ASSETS_ROOT": str(input_assets_root),
        "TOY_ROAD_AUTHORIZATION_RECEIPT": str(launch_receipt_path),
    })
    final_processes = matlab_processes()
    if final_processes:
        _write_busy_receipt(roots["receipts"], final_processes)
        raise BusyExperimentError("BUSY_NO_LAUNCH: final process check blocks T3-rev launch")
    stdout = (run_root / "T3_REV.stdout.log").open("xb")
    stderr = (run_root / "T3_REV.stderr.log").open("xb")
    try:
        process = Popen(
            [str(matlab), "-batch", batch], cwd=run_root, env=env, stdout=stdout, stderr=stderr,
            creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
        )
    finally:
        stdout.close()
        stderr.close()
    (run_root / "launcher.pid").write_text(str(process.pid) + "\n", encoding="ascii")
    return {"status": "LAUNCHED", "pid": process.pid, "run_root": str(run_root), "resume_allowed": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--seal", type=Path, required=True)
    parser.add_argument("--extension-root", type=Path, required=True)
    parser.add_argument("--template-run", type=Path, required=True)
    parser.add_argument("--gripfith-root", type=Path, required=True)
    parser.add_argument("--input-assets-root", type=Path, required=True)
    parser.add_argument("--matlab", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(launch_t3_rev(**vars(args)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
