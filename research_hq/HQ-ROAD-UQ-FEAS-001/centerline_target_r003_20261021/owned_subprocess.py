"""Run one frozen child command and atomically preserve its real exit status.

The invocation manifest binds the command, working directory, output paths,
Run ID, approval snapshot and data lock.  The controller never overwrites an
existing receipt or output, so a duplicate dispatch fails before launch.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: str | Path, payload: bytes) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f"{target.name}.tmp.{os.getpid()}.{uuid.uuid4().hex}")
    with open(temporary, "xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)


def canonical_json_sha(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def read_json(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_receipt(invocation_path: str | Path) -> dict:
    invocation_path = Path(invocation_path)
    invocation = read_json(invocation_path)
    receipt = read_json(invocation["receipt_path"])
    exit_text = Path(invocation["exitcode_path"]).read_text(encoding="ascii").strip()
    if not exit_text or not exit_text.lstrip("-").isdigit():
        raise ValueError("exit sidecar is not one integer")
    approval = read_json(invocation["approval_path"])
    expected = {
        "schema": 1,
        "run_id": invocation["run_id"],
        "role": invocation["role"],
        "invocation_sha256": sha256(invocation_path),
        "command_sha256": canonical_json_sha(invocation["command"]),
        "code_snapshot": approval["code_snapshot"],
        "data_lock_sha256": approval["data_lock_sha256"],
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise ValueError(f"receipt {key} mismatch")
    if receipt.get("controller_exit_code") != int(exit_text):
        raise ValueError("numeric and JSON exit sidecars disagree")
    claim = Path(str(invocation["receipt_path"]) + ".claim")
    if not claim.is_file() or receipt.get("claim_sha256") != sha256(claim):
        raise ValueError("exclusive launch claim mismatch")
    for field in ("stdout", "stderr"):
        path = Path(invocation[f"{field}_path"])
        evidence = receipt.get(field, {})
        if not path.is_file() or evidence.get("bytes") != path.stat().st_size or evidence.get("sha256") != sha256(path):
            raise ValueError(f"{field} evidence mismatch")
    return receipt


def evidence_paths(invocation: dict) -> list[Path]:
    paths = [Path(invocation[name]) for name in ("receipt_path", "exitcode_path", "stdout_path", "stderr_path")]
    paths.append(Path(str(invocation["receipt_path"]) + ".claim"))
    return paths


def assert_clean_launch(invocation: dict) -> None:
    existing = [str(path) for path in evidence_paths(invocation) if path.exists()]
    if existing:
        raise FileExistsError(f"owned subprocess evidence already exists; duplicate launch prohibited: {existing}")


def terminate_owned(process: subprocess.Popen) -> dict:
    attempts = []
    if os.name == "nt":
        while process.poll() is None:
            try:
                result = subprocess.run(
                    ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                    timeout=10, check=False,
                )
                attempts.append({"returncode":result.returncode,"output":result.stdout,"timed_out":False})
            except subprocess.TimeoutExpired as error:
                attempts.append({"returncode":None,"output":str(error),"timed_out":True})
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                continue
        return {"method":"taskkill_tree_until_exit","attempts":attempts,"confirmed_terminated":True,"final_exit_code":process.returncode}
    while process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
            attempts.append({"returncode":0,"output":"","timed_out":False})
        except ProcessLookupError:
            attempts.append({"returncode":0,"output":"already exited","timed_out":False})
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            continue
    return {"method":"killpg_until_exit","attempts":attempts,"confirmed_terminated":True,"final_exit_code":process.returncode}


def timeout_seconds(invocation: dict) -> float:
    has_timeout = "timeout_seconds" in invocation
    has_deadline = "deadline_utc" in invocation
    if has_timeout == has_deadline:
        raise ValueError("invocation must have exactly one of timeout_seconds or deadline_utc")
    if has_timeout:
        value = float(invocation["timeout_seconds"])
    else:
        deadline = dt.datetime.fromisoformat(invocation["deadline_utc"].replace("Z", "+00:00"))
        value = (deadline - dt.datetime.now(dt.timezone.utc)).total_seconds()
    if value <= 0:
        raise ValueError("no child execution time remains")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("invocation")
    args = parser.parse_args()
    invocation_path = Path(args.invocation).resolve()
    invocation = read_json(invocation_path)
    required = {
        "schema", "run_id", "role", "approval_path", "lock_path", "cwd", "command",
        "receipt_path", "exitcode_path", "stdout_path", "stderr_path",
    }
    missing = sorted(required - invocation.keys())
    if missing or invocation.get("schema") != 1 or not isinstance(invocation.get("command"), list) or not invocation["command"]:
        raise ValueError(f"invalid invocation manifest; missing={missing}")
    approval = read_json(invocation["approval_path"])
    if approval.get("run_id") != invocation["run_id"]:
        raise ValueError("invocation/approval Run ID mismatch")
    if sha256(invocation["lock_path"]) != approval.get("data_lock_sha256"):
        raise ValueError("live data lock does not match approval")
    assert_clean_launch(invocation)
    claim_path = Path(str(invocation["receipt_path"]) + ".claim")
    claim_path.parent.mkdir(parents=True, exist_ok=True)
    claim_payload = (json.dumps({"run_id":invocation["run_id"], "role":invocation["role"],
                                 "invocation_sha256":sha256(invocation_path), "controller_pid":os.getpid()},
                                sort_keys=True) + "\n").encode()
    claim_fd = os.open(claim_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(claim_fd, "wb") as claim_stream:
        claim_stream.write(claim_payload); claim_stream.flush(); os.fsync(claim_stream.fileno())
    limit = timeout_seconds(invocation)
    started = dt.datetime.now(dt.timezone.utc)
    monotonic_start = time.monotonic()
    child_exit_code = None
    controller_exit_code = 127
    status = "LAUNCH_ERROR"
    timed_out = False
    kill = None
    pid = None
    launch_error = None
    stdout_path = Path(invocation["stdout_path"])
    stderr_path = Path(invocation["stderr_path"])
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(stdout_path, "xb") as stdout, open(stderr_path, "xb") as stderr:
            kwargs = {"cwd": invocation["cwd"], "stdout": stdout, "stderr": stderr}
            if os.name == "nt":
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                kwargs["start_new_session"] = True
            process = subprocess.Popen(invocation["command"], **kwargs)
            pid = process.pid
            try:
                child_exit_code = process.wait(timeout=limit)
                status = "COMPLETE_ZERO" if child_exit_code == 0 else "COMPLETE_NONZERO"
                controller_exit_code = 0 if child_exit_code == 0 else int(child_exit_code or 1)
            except subprocess.TimeoutExpired:
                timed_out = True
                status = "TIMEOUT"
                controller_exit_code = 124
                kill = terminate_owned(process)
                if not kill.get("confirmed_terminated") or process.poll() is None:
                    raise RuntimeError("owned child tree termination was not confirmed")
                child_exit_code = process.returncode
    except Exception as exc:
        launch_error = f"{type(exc).__name__}: {exc}"
        if not stdout_path.exists():
            stdout_path.touch()
        if not stderr_path.exists():
            stderr_path.write_text(launch_error + "\n", encoding="utf-8")
    ended = dt.datetime.now(dt.timezone.utc)
    receipt = {
        "schema": 1,
        "status": status,
        "run_id": invocation["run_id"],
        "role": invocation["role"],
        "invocation_sha256": sha256(invocation_path),
        "command_sha256": canonical_json_sha(invocation["command"]),
        "code_snapshot": approval["code_snapshot"],
        "data_lock_sha256": approval["data_lock_sha256"],
        "claim_sha256": sha256(claim_path),
        "child_exit_code": child_exit_code,
        "controller_exit_code": controller_exit_code,
        "timed_out": timed_out,
        "timeout_seconds_at_start": limit,
        "pid": pid,
        "kill": kill,
        "launch_error": launch_error,
        "started_utc": started.isoformat(),
        "ended_utc": ended.isoformat(),
        "elapsed_seconds": round(time.monotonic() - monotonic_start, 3),
        "stdout": {"bytes": stdout_path.stat().st_size, "sha256": sha256(stdout_path)},
        "stderr": {"bytes": stderr_path.stat().st_size, "sha256": sha256(stderr_path)},
    }
    atomic_write(invocation["receipt_path"], (json.dumps(receipt, indent=2) + "\n").encode())
    atomic_write(invocation["exitcode_path"], f"{controller_exit_code}\n".encode("ascii"))
    return controller_exit_code


if __name__ == "__main__":
    sys.exit(main())
