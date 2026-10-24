#!/usr/bin/env python3
"""Finite local guard for the conditional E017 final launch."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_s09_e017_admission_handoff import verify_handoff  # noqa: E402


RUN_ID = "S09-E017-R001-factorised-head-p0"
CANDIDATE_SHA256 = "4c1e928274f6fbee134ff540345844260cf16675727d0e996abb0054062ddcf1"
ARCHIVE_SHA256 = "4ece34be786fc85bb9655c076c13c45d276d08dfde405a8fb1367e4b49ffdd22"
CONTROL_COMMIT = "2002538d9a30c8d4006ccaff5959cd214958fc82"
ADAPTER_COMMIT = "662005f1fde22cb9a6e8069f4e430b7190f21860"
WALL_SECONDS = 120
FINAL_ATTEMPT_ID = "s09e017-final-launch-20261024-r1"


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _path_sha(path: Path) -> str:
    return _sha(path.read_bytes())


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _publish(path: Path, value: object) -> None:
    payload = value if isinstance(value, bytes) else _canonical(value)
    temporary = path.parent / f".{path.name}.tmp-{os.getpid()}-{time.time_ns()}"
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _validate_authority(authority: dict) -> None:
    required = {
        "schema_version",
        "approval_status",
        "execution_authorized",
        "run_id",
        "reviewed_adapter_commit",
        "reviewed_control_commit",
        "candidate_config_sha256",
        "code_archive_sha256",
        "allowed_actions",
        "maximum_launches",
        "retry",
        "alternate_host",
        "alternate_gpu",
        "network_recovery_confirmed",
        "granted_by",
        "granted_at",
    }
    if set(authority) != required:
        raise ValueError("execution authority keys drift")
    expected = {
        "schema_version": "s09-e017-one-run-authority-v1",
        "approval_status": "APPROVED_FOR_ONE_ADMISSION_AND_COMPLETE_RUN",
        "execution_authorized": True,
        "run_id": RUN_ID,
        "reviewed_adapter_commit": ADAPTER_COMMIT,
        "reviewed_control_commit": CONTROL_COMMIT,
        "candidate_config_sha256": CANDIDATE_SHA256,
        "code_archive_sha256": ARCHIVE_SHA256,
        "allowed_actions": ["LIVE_ADMISSION", "COMPLETE_THREE_ARM_RUN"],
        "maximum_launches": 1,
        "retry": False,
        "alternate_host": False,
        "alternate_gpu": False,
        "network_recovery_confirmed": True,
        "granted_by": "user",
    }
    for key, value in expected.items():
        if authority[key] != value:
            raise ValueError(f"execution authority {key} drift")
    if (
        not isinstance(authority["granted_at"], str)
        or "+" not in authority["granted_at"]
    ):
        raise ValueError("execution authority timestamp missing timezone")


def run_guard(
    *,
    admission_evidence_root: Path,
    execution_authority: Path,
    launcher: Path,
    launcher_sha256: str,
    plan: Path,
    plan_sha256: str,
    evidence_root: Path,
    attempt_id: str,
    execute_authorised_final_launch: bool,
    popen=subprocess.Popen,
    publisher=_publish,
    kill_process_group=os.killpg,
) -> dict:
    if not execute_authorised_final_launch:
        raise PermissionError("--execute-authorised-final-launch is required")
    if attempt_id != FINAL_ATTEMPT_ID:
        raise ValueError("final launch attempt id drift")
    expected_evidence_root = (
        ROOT
        / "local_archive/experiments/S09-E017/final_launch_attempts"
        / FINAL_ATTEMPT_ID
    )
    if evidence_root.resolve() != expected_evidence_root.resolve():
        raise ValueError("final launch evidence root drift")
    handoff = verify_handoff(admission_evidence_root)
    authority_bytes = execution_authority.read_bytes()
    authority = json.loads(authority_bytes)
    _validate_authority(authority)
    if _path_sha(launcher) != launcher_sha256:
        raise ValueError("final launcher hash mismatch")
    if _path_sha(plan) != plan_sha256:
        raise ValueError("final launch plan hash mismatch")
    if not evidence_root.is_dir():
        raise ValueError("final launch evidence root missing")
    paths = {
        "handoff": evidence_root / "admission_handoff_receipt.json",
        "consumption": evidence_root / "execution_authority_consumption_receipt.json",
        "stdout": evidence_root / "stdout.log",
        "stderr": evidence_root / "stderr.log",
        "guard": evidence_root / "guard_receipt.json",
    }
    if any(path.exists() for path in paths.values()):
        raise FileExistsError("final launch evidence path conflict")
    publisher(paths["handoff"], handoff)
    authority_sha256 = _sha(authority_bytes)
    publisher(
        paths["consumption"],
        {
            "schema_version": "s09-e017-final-launch-authority-consumption-v1",
            "terminal_state": "FINAL_LAUNCH_AUTHORITY_CONSUMED_NO_RETRY",
            "run_id": RUN_ID,
            "attempt_id": attempt_id,
            "authority_sha256": authority_sha256,
            "launcher_sha256": launcher_sha256,
            "plan_sha256": plan_sha256,
            "retry": False,
            "reconnect": False,
        },
    )
    environment = os.environ.copy()
    environment.update(
        {
            "S09_E017_FINAL_LAUNCH_GUARDED": plan_sha256,
            "S09_E017_FINAL_LAUNCH_ATTEMPT_ID": attempt_id,
            "S09_E017_EXECUTION_AUTHORITY": str(execution_authority.resolve()),
            "S09_E017_EXECUTION_AUTHORITY_SHA256": authority_sha256,
            "S09_E017_FINAL_LAUNCHER": str(launcher.resolve()),
            "S09_E017_FINAL_LAUNCHER_SHA256": launcher_sha256,
            "S09_E017_FINAL_LAUNCH_EVIDENCE_ROOT": str(evidence_root.resolve()),
            "S09_E017_FINAL_LAUNCH_DEADLINE_EPOCH": str(
                int(time.time()) + WALL_SECONDS
            ),
        }
    )
    start = time.monotonic()
    process = None
    timed_out = False
    try:
        process = popen(
            ["/bin/bash", str(plan)],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=WALL_SECONDS)
        except subprocess.TimeoutExpired:
            timed_out = True
            kill_process_group(process.pid, signal.SIGTERM)
            try:
                stdout, stderr = process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                kill_process_group(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
        process_returncode = process.returncode
        process_error = None
    except Exception as error:
        process_started = process is not None
        if process_started:
            try:
                kill_process_group(process.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
            try:
                process.wait(timeout=10)
            except (AttributeError, subprocess.TimeoutExpired):
                pass
        stdout = ""
        stderr = ""
        process_returncode = None if process is None else process.returncode
        process_error = f"{type(error).__name__}: {error}"
    evidence_write_errors = []
    for name, payload in (("stdout", stdout), ("stderr", stderr)):
        try:
            publisher(paths[name], payload.encode())
        except Exception as error:
            evidence_write_errors.append(
                {"artifact": name, "error": f"{type(error).__name__}: {error}"}
            )
    if process_error is not None:
        terminal = "FINAL_LAUNCH_GUARD_STOPPED"
        reason = (
            "FINAL_LAUNCH_PROCESS_IO_FAILED"
            if process_started
            else "FINAL_LAUNCH_PROCESS_START_FAILED"
        )
    elif timed_out:
        terminal = "FINAL_LAUNCH_GUARD_STOPPED"
        reason = "FINAL_LAUNCH_DISPATCH_WALL_CAP_EXCEEDED"
    elif process_returncode != 0:
        terminal = "FINAL_LAUNCH_GUARD_STOPPED"
        reason = "FINAL_LAUNCH_PLAN_EXIT_NONZERO"
    else:
        terminal = "FINAL_LAUNCH_DISPATCH_COMPLETED"
        reason = None
    if evidence_write_errors and reason is None:
        terminal = "FINAL_LAUNCH_GUARD_STOPPED"
        reason = "LOCAL_LOG_WRITE_FAILED"
    receipt = {
        "schema_version": "s09-e017-final-launch-guard-receipt-v1",
        "terminal_state": terminal,
        "first_reason": reason,
        "run_id": RUN_ID,
        "attempt_id": attempt_id,
        "authority_sha256": authority_sha256,
        "launcher_sha256": launcher_sha256,
        "plan_sha256": plan_sha256,
        "elapsed_seconds": time.monotonic() - start,
        "process_returncode": process_returncode,
        "process_error": process_error,
        "stdout_sha256": _sha(stdout.encode()),
        "stderr_sha256": _sha(stderr.encode()),
        "evidence_write_errors": evidence_write_errors,
        "remote_detached_state_unknown": reason == "FINAL_LAUNCH_PROCESS_IO_FAILED",
        "retry": False,
        "reconnect": False,
    }
    publisher(paths["guard"], receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admission-evidence-root", type=Path, required=True)
    parser.add_argument("--execution-authority", type=Path, required=True)
    parser.add_argument("--launcher", type=Path, required=True)
    parser.add_argument("--launcher-sha256", required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--execute-authorised-final-launch", action="store_true")
    args = parser.parse_args()
    receipt = run_guard(
        admission_evidence_root=args.admission_evidence_root,
        execution_authority=args.execution_authority,
        launcher=args.launcher,
        launcher_sha256=args.launcher_sha256,
        plan=args.plan,
        plan_sha256=args.plan_sha256,
        evidence_root=args.evidence_root,
        attempt_id=args.attempt_id,
        execute_authorised_final_launch=args.execute_authorised_final_launch,
    )
    print(_canonical(receipt).decode(), end="")
    if receipt["terminal_state"] != "FINAL_LAUNCH_DISPATCH_COMPLETED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
