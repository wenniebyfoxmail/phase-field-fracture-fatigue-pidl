from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path


class BusyExperimentError(RuntimeError):
    pass


class LaunchError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, object]:
    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in items:
            if key in value:
                raise LaunchError(f"duplicate JSON key: {key}")
            value[key] = item
        return value

    value = json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
    )
    if not isinstance(value, dict):
        raise LaunchError(f"expected JSON object: {path}")
    return value


def write_json_create_new(path: Path, value: object) -> None:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def matlab_processes() -> list[dict[str, object]]:
    script = (
        "$p=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^MATLAB'} | "
        "Select-Object ProcessId,Name,CreationDate,CommandLine); if($p.Count){$p|ConvertTo-Json -Compress}"
    )
    result = subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True, capture_output=True, text=True)
    if not result.stdout.strip():
        return []
    value = json.loads(result.stdout)
    return value if isinstance(value, list) else [value]


def matlab_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def launch_t3(
    repo_root: Path,
    run_root: Path,
    seal_path: Path,
    template_run: Path,
    gripfith_root: Path,
    input_assets_root: Path,
    matlab: Path,
) -> dict[str, object]:
    if matlab_processes():
        raise BusyExperimentError("BUSY_NO_LAUNCH: an existing MATLAB/FEM process blocks T3")
    repo_root, run_root = repo_root.resolve(), run_root.resolve()
    seal_path, template_run = seal_path.resolve(), template_run.resolve()
    gripfith_root, input_assets_root, matlab = gripfith_root.resolve(), input_assets_root.resolve(), matlab.resolve()
    if run_root.exists():
        raise FileExistsError(f"T3 run root already exists: {run_root}")
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo_root, check=True, capture_output=True, text=True).stdout
    if status:
        raise LaunchError("T3 sibling code must be committed before launch")
    seal = read_json(seal_path)
    if seal.get("status") != "PASS" or seal.get("authorization_capability") != "exactly_one_T3_loading_history_execution":
        raise LaunchError("T3 sibling seal does not authorize exactly one T3")
    if seal.get("resume_allowed") is not False or seal.get("follow_on_authorized") is not False:
        raise LaunchError("T3 seal violates nonresume/no-follow-on scope")
    template_lock_path = template_run / "receipts" / "T2_EXECUTION_INPUT_LOCK.json"
    template = read_json(template_lock_path)
    handoff = repo_root / "producer_handoffs" / "toy_road_p0_repeatability_20260803"
    initial_source = repo_root / "producer_handoffs" / "rebuilt_initial_mex_qualification_20260801" / "runtime" / "initial.mexw64"
    required = [matlab, initial_source, handoff / "run_toy_road_runtime_bridge.m", handoff / "main_toy_road_family_case.m"]
    if any(not item.is_file() for item in required):
        raise LaunchError("sealed T3 runtime inputs are incomplete")
    source_manifest = handoff / "SOURCE_MANIFEST.json"
    if sha256(source_manifest) != template.get("source_manifest_sha256"):
        raise LaunchError("sealed source manifest identity differs from the execution template")
    verification = subprocess.run(
        ["py", "-3", str(handoff / "toy_road_protocol.py"), "--verify-source-manifest", str(handoff)],
        capture_output=True, text=True,
    )
    if verification.returncode != 0:
        raise LaunchError(f"sealed source manifest verification failed: {verification.stderr.strip()}")
    roots = {name: run_root / name for name in ("output", "work", "temp", "tmp", "pref", "cache", "receipts")}
    roots["matlab_startup_pref"] = run_root / "pref.matlab-startup"
    runtime_overlay = run_root / ".toy-road-runtime-overlay"
    initial_target = runtime_overlay / "+phase_field" / "+mex" / "+fem" / "+assembly" / "+equilibrium" / "initial.mexw64"
    run_root.mkdir(parents=True, exist_ok=False)
    for path in (roots["receipts"], roots["matlab_startup_pref"], initial_target.parent):
        path.mkdir(parents=True, exist_ok=False)
    os.link(initial_source, initial_target)
    suite = Path(r"C:\SuiteSparse\SuiteSparse-dev")
    matlab_paths = [
        runtime_overlay, handoff, gripfith_root / "Sources", suite / "CHOLMOD" / "MATLAB",
        suite / "AMD" / "MATLAB", suite / "COLAMD" / "MATLAB", suite / "CCOLAMD" / "MATLAB", suite / "CAMD" / "MATLAB",
    ]
    lock = json.loads(json.dumps(template))
    lock.update({
        "case_id": "T3_loading_history",
        "case_physics_contract_sha256": seal["case_physics_contract_sha256"],
        "launch_timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "no_clobber_receipt_id": uuid.uuid4().hex,
        "resume_allowed": False,
        "writable_roots": {key: str(value) for key, value in roots.items() if key != "receipts"},
    })
    lock["runtime_expectations"]["matlab"]["absolute_path_order"] = [str(path.resolve()) for path in matlab_paths]
    lock_path = roots["receipts"] / "T3_EXECUTION_INPUT_LOCK.json"
    write_json_create_new(lock_path, lock)
    launch_receipt = {
        "schema_version": "toy_road_t3_sibling_launch_receipt_v1",
        "status": "PASS",
        "authorization_scope": "production_authorized",
        "authorized_entrypoint": "run_toy_road_runtime_bridge",
        "case_id": "T3_loading_history",
        "resume_allowed": False,
        "source_commit": lock["source_commit"],
        "runtime_lock_sha256": lock["runtime_lock_sha256"],
        "family_contract_sha256": lock["family_contract_sha256"],
        "case_physics_contract_sha256": lock["case_physics_contract_sha256"],
        "execution_input_lock_sha256": sha256(lock_path),
        "sibling_seal_sha256": sha256(seal_path),
    }
    launch_receipt_path = roots["receipts"] / "T3_SIBLING_LAUNCH_RECEIPT.json"
    write_json_create_new(launch_receipt_path, launch_receipt)
    measurement_path = roots["receipts"] / "T3_RUNTIME_MEASUREMENT.json"
    prefix = os.pathsep.join(str(path.resolve()) for path in matlab_paths)
    batch = f"path([{matlab_literal(prefix)} pathsep path]);run_toy_road_runtime_bridge({matlab_literal(str(lock_path))},{matlab_literal(str(measurement_path))});"
    env = os.environ.copy()
    env.update({
        "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_DYNAMIC": "FALSE",
        "TEMP": str(roots["temp"]), "TMP": str(roots["tmp"]), "MATLAB_PREFDIR": str(roots["matlab_startup_pref"]), "MCR_CACHE_ROOT": str(roots["cache"]),
        "TOY_ROAD_CASE_ROLE": "T3_loading_history", "TOY_ROAD_SOURCE_COMMIT": str(lock["source_commit"]),
        "TOY_ROAD_RUNTIME_LOCK_SHA256": str(lock["runtime_lock_sha256"]), "TOY_ROAD_FAMILY_CONTRACT_SHA256": str(lock["family_contract_sha256"]),
        "TOY_ROAD_CASE_PHYSICS_CONTRACT_SHA256": str(lock["case_physics_contract_sha256"]), "TOY_ROAD_EXECUTION_INPUT_LOCK_SHA256": sha256(lock_path),
        "TOY_ROAD_OUTPUT_ROOT": str(roots["output"]), "TOY_ROAD_WORK_ROOT": str(roots["work"]), "TOY_ROAD_TEMP_ROOT": str(roots["temp"]),
        "TOY_ROAD_TMP_ROOT": str(roots["tmp"]), "TOY_ROAD_PREF_ROOT": str(roots["pref"]), "TOY_ROAD_CACHE_ROOT": str(roots["cache"]),
        "TOY_ROAD_INPUT_ASSETS_ROOT": str(input_assets_root), "TOY_ROAD_AUTHORIZATION_RECEIPT": str(launch_receipt_path),
    })
    stdout = (run_root / "T3.stdout.log").open("xb")
    stderr = (run_root / "T3.stderr.log").open("xb")
    try:
        process = subprocess.Popen([str(matlab), "-batch", batch], cwd=run_root, env=env, stdout=stdout, stderr=stderr, creationflags=0x08000000 | 0x00000200)
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
    parser.add_argument("--template-run", type=Path, required=True)
    parser.add_argument("--gripfith-root", type=Path, required=True)
    parser.add_argument("--input-assets-root", type=Path, required=True)
    parser.add_argument("--matlab", type=Path, default=Path(r"C:\Program Files\MATLAB\R2025b\bin\matlab.exe"))
    args = parser.parse_args()
    print(json.dumps(launch_t3(args.repo_root, args.run_root, args.seal, args.template_run, args.gripfith_root, args.input_assets_root, args.matlab), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
