from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path


class DiagnosticLaunchError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json_create_new(path: Path, value: object) -> None:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def matlab_processes() -> str:
    command = (
        "$p=@(Get-CimInstance Win32_Process | Where-Object { "
        "$_.Name -match '^MATLAB' }); if($p.Count){$p | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress}"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def matlab_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def launch(run_root: Path, repo_root: Path, base_run: Path, gripfith_root: Path, input_assets_root: Path, matlab: Path) -> dict[str, object]:
    run_root = run_root.resolve()
    repo_root = repo_root.resolve()
    base_run = base_run.resolve()
    gripfith_root = gripfith_root.resolve()
    input_assets_root = input_assets_root.resolve()
    matlab = matlab.resolve()
    if run_root.exists():
        raise FileExistsError(f"D-T2 run root already exists: {run_root}")
    if matlab_processes():
        raise DiagnosticLaunchError("an existing MATLAB/FEM process blocks D-T2")
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo_root, check=True, capture_output=True, text=True).stdout
    if status:
        raise DiagnosticLaunchError("D-T2 diagnostic code must be committed before launch")

    diagnostic_root = Path(__file__).resolve().parent
    overlay = diagnostic_root / "overlay"
    handoff = repo_root / "producer_handoffs" / "toy_road_p0_repeatability_20260803"
    initial_source = repo_root / "producer_handoffs" / "rebuilt_initial_mex_qualification_20260801" / "runtime" / "initial.mexw64"
    template_lock = json.loads((base_run / "receipts" / "T2_EXECUTION_INPUT_LOCK.json").read_text(encoding="utf-8"))
    predecessor_auth = next((base_run / "receipts").glob(".*.T1_initial_defect.terminal-auth.json"))
    predecessor = json.loads(predecessor_auth.read_text(encoding="utf-8"))
    failure_manifest = repo_root / "docs" / "toy_road_p0_repeatability_20260802" / "t2_material_state_failure_20260817" / "PACKAGE_MANIFEST.json"
    required = [overlay / "begin_toy_road_c5_trace.m", overlay / "append_toy_road_c5_stagger_row.m", initial_source, failure_manifest, matlab]
    if any(not path.is_file() for path in required):
        raise DiagnosticLaunchError("D-T2 source/runtime evidence is incomplete")

    roots = {name: run_root / name for name in ("output", "work", "temp", "tmp", "pref", "cache", "receipts")}
    roots["matlab_startup_pref"] = run_root / "pref.matlab-startup"
    runtime_overlay = run_root / "runtime-overlay"
    initial_target = runtime_overlay / "+phase_field" / "+mex" / "+fem" / "+assembly" / "+equilibrium" / "initial.mexw64"
    for path in [*roots.values(), initial_target.parent]:
        path.mkdir(parents=True, exist_ok=False)
    os.link(initial_source, initial_target)

    suite = Path(r"C:\SuiteSparse\SuiteSparse-dev")
    matlab_paths = [
        overlay,
        runtime_overlay,
        handoff,
        gripfith_root / "Sources",
        suite / "CHOLMOD" / "MATLAB",
        suite / "AMD" / "MATLAB",
        suite / "COLAMD" / "MATLAB",
        suite / "CCOLAMD" / "MATLAB",
        suite / "CAMD" / "MATLAB",
    ]
    lock = dict(template_lock)
    lock["launch_timestamp_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    lock["no_clobber_receipt_id"] = uuid.uuid4().hex
    lock["writable_roots"] = {key: str(value) for key, value in roots.items() if key != "receipts"}
    lock["runtime_expectations"] = json.loads(json.dumps(template_lock["runtime_expectations"]))
    lock["runtime_expectations"]["matlab"]["absolute_path_order"] = [str(path.resolve()) for path in matlab_paths]
    lock_path = roots["receipts"] / "DT2_EXECUTION_INPUT_LOCK.json"
    write_json_create_new(lock_path, lock)
    lock_sha = sha256(lock_path)

    launch_receipt = {
        "status": "PASS",
        "authorization_scope": "production_authorized",
        "authorized_entrypoint": "run_toy_road_runtime_bridge",
        "case_id": "T2_material_state",
        "source_commit": template_lock["source_commit"],
        "runtime_lock_sha256": template_lock["runtime_lock_sha256"],
        "family_contract_sha256": template_lock["family_contract_sha256"],
        "case_physics_contract_sha256": template_lock["case_physics_contract_sha256"],
        "execution_input_lock_sha256": lock_sha,
    }
    upstream_path = roots["receipts"] / "DT2_UPSTREAM_LAUNCH_RECEIPT.json"
    write_json_create_new(upstream_path, launch_receipt)

    diagnostic_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True).stdout.strip()
    diagnostic_receipt = {
        "schema_version": "toy_road_dt2_launch_receipt_v1",
        "authorization_scope": "diagnostic_only_nonproduction",
        "case_id": "D-T2_c5_s4_iterate_dynamics",
        "base_case_id": "T2_material_state",
        "base_source_commit": template_lock["source_commit"],
        "diagnostic_code_commit": diagnostic_commit,
        "diagnostic_contract_sha256": sha256(diagnostic_root / "DT2_DIAGNOSTIC_CONTRACT.json"),
        "begin_observer_sha256": sha256(overlay / "begin_toy_road_c5_trace.m"),
        "append_observer_sha256": sha256(overlay / "append_toy_road_c5_stagger_row.m"),
        "execution_input_lock_sha256": lock_sha,
        "original_t2_failure_manifest_sha256": sha256(failure_manifest),
        "predecessor_terminal_manifest_sha256": predecessor["manifest_sha256"],
        "predecessor_terminal_auth_sha256": sha256(predecessor_auth),
        "solver_modified": False,
        "thresholds_modified": False,
        "serial_chain_t3_authorized": False,
    }
    write_json_create_new(roots["receipts"] / "DT2_DIAGNOSTIC_LAUNCH_RECEIPT.json", diagnostic_receipt)

    measurement_path = roots["receipts"] / "DT2_RUNTIME_MEASUREMENT.json"
    iterate_path = roots["output"] / "qualification" / "DT2_C5_ITERATES.mat"
    iterate_path.parent.mkdir()
    prefix = os.pathsep.join(str(path.resolve()) for path in matlab_paths)
    batch = f"path([{matlab_literal(prefix)} pathsep path]);run_toy_road_runtime_bridge({matlab_literal(str(lock_path))},{matlab_literal(str(measurement_path))});"
    env = os.environ.copy()
    env.update({
        "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_DYNAMIC": "FALSE",
        "TEMP": str(roots["temp"]), "TMP": str(roots["tmp"]), "MATLAB_PREFDIR": str(roots["matlab_startup_pref"]), "MCR_CACHE_ROOT": str(roots["cache"]),
        "TOY_ROAD_CASE_ROLE": "T2_material_state", "TOY_ROAD_SOURCE_COMMIT": template_lock["source_commit"],
        "TOY_ROAD_RUNTIME_LOCK_SHA256": template_lock["runtime_lock_sha256"], "TOY_ROAD_FAMILY_CONTRACT_SHA256": template_lock["family_contract_sha256"],
        "TOY_ROAD_CASE_PHYSICS_CONTRACT_SHA256": template_lock["case_physics_contract_sha256"], "TOY_ROAD_EXECUTION_INPUT_LOCK_SHA256": lock_sha,
        "TOY_ROAD_OUTPUT_ROOT": str(roots["output"]), "TOY_ROAD_WORK_ROOT": str(roots["work"]), "TOY_ROAD_TEMP_ROOT": str(roots["temp"]),
        "TOY_ROAD_TMP_ROOT": str(roots["tmp"]), "TOY_ROAD_PREF_ROOT": str(roots["pref"]), "TOY_ROAD_CACHE_ROOT": str(roots["cache"]),
        "TOY_ROAD_INPUT_ASSETS_ROOT": str(input_assets_root), "TOY_ROAD_AUTHORIZATION_RECEIPT": str(upstream_path),
        "TOY_ROAD_DT2_ITERATE_PATH": str(iterate_path),
    })
    stdout = (run_root / "DT2.stdout.log").open("xb")
    stderr = (run_root / "DT2.stderr.log").open("xb")
    try:
        process = subprocess.Popen([str(matlab), "-batch", batch], cwd=roots["work"], env=env, stdout=stdout, stderr=stderr, creationflags=0x08000000 | 0x00000200)
    finally:
        stdout.close(); stderr.close()
    (run_root / "launcher.pid").write_text(str(process.pid) + "\n", encoding="ascii")
    return {"pid": process.pid, "run_root": str(run_root), "iterate_path": str(iterate_path), "diagnostic_code_commit": diagnostic_commit}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--base-run", type=Path, required=True)
    parser.add_argument("--griphfith-root", type=Path, required=True)
    parser.add_argument("--input-assets-root", type=Path, required=True)
    parser.add_argument("--matlab", type=Path, default=Path(r"C:\Program Files\MATLAB\R2025b\bin\matlab.exe"))
    args = parser.parse_args()
    print(json.dumps(launch(args.run_root, args.repo_root, args.base_run, args.griphfith_root, args.input_assets_root, args.matlab), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
