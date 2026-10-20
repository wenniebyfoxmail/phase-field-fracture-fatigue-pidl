#!/usr/bin/env python3
"""Finite local guard for the reviewed E017 admission-only plan."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e017_admission_only import (  # noqa: E402
    AdmissionOnlyStop,
    canonical_json,
    sha256_bytes,
    sha256_path,
    strict_json,
    validate_authority,
    validate_candidate,
)


def _publish(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)


def run_guarded_plan(
    *,
    candidate_path: Path,
    candidate_sha256: str,
    authority_path: Path,
    plan_path: Path,
    plan_sha256: str,
    execute_authorised_admission_only: bool,
    popen: Callable[..., Any] = subprocess.Popen,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    if not execute_authorised_admission_only:
        raise AdmissionOnlyStop(
            "ADMISSION_ONLY_DISABLED",
            "--execute-authorised-admission-only is required",
        )
    candidate, candidate_bytes = strict_json(candidate_path)
    authority, authority_bytes = strict_json(authority_path)
    validate_candidate(candidate)
    if sha256_bytes(candidate_bytes) != candidate_sha256:
        raise AdmissionOnlyStop("CANDIDATE_HASH_MISMATCH", "candidate SHA256")
    if sha256_path(Path(__file__).resolve()) != candidate["guard_sha256"]:
        raise AdmissionOnlyStop("GUARD_HASH_MISMATCH", "local guard SHA256")
    if sha256_path(plan_path) != plan_sha256:
        raise AdmissionOnlyStop("PLAN_HASH_MISMATCH", "plan SHA256")
    validate_authority(
        authority,
        candidate,
        candidate_sha256=candidate_sha256,
        plan_sha256=plan_sha256,
    )
    for relative, expected in candidate["helper_manifest"].items():
        path = ROOT / relative
        if sha256_path(path) != expected:
            raise AdmissionOnlyStop("HELPER_HASH_MISMATCH", relative)
    local_root = Path(authority["local_evidence_root"])
    if not local_root.is_dir():
        raise AdmissionOnlyStop("LOCAL_EVIDENCE_ROOT_MISSING", str(local_root))
    paths = {
        "consumption": local_root / "authority_consumption_receipt.json",
        "guard": local_root / "guard_receipt.json",
        "stdout": local_root / "stdout.log",
        "stderr": local_root / "stderr.log",
    }
    conflicts = [str(path) for path in paths.values() if path.exists()]
    if conflicts:
        raise AdmissionOnlyStop("LOCAL_RECEIPT_PATH_CONFLICT", json.dumps(conflicts))
    transfer_bytes = len(candidate_bytes) + len(authority_bytes)
    transfer_bytes += sum(
        (ROOT / relative).stat().st_size for relative in candidate["helper_manifest"]
    )
    if transfer_bytes > candidate["budgets"]["metadata_transfer_bytes"]:
        raise AdmissionOnlyStop("METADATA_TRANSFER_CAP_EXCEEDED", str(transfer_bytes))
    consumption = {
        "schema_version": "s09-e017-admission-only-authority-consumption-v1",
        "terminal_state": "ADMISSION_ONLY_AUTHORITY_CONSUMED_NO_RETRY",
        "run_id": candidate["run_id"],
        "admission_only_attempt_id": authority["admission_only_attempt_id"],
        "candidate_sha256": candidate_sha256,
        "plan_sha256": plan_sha256,
        "authority_sha256": sha256_bytes(authority_bytes),
        "retry": False,
        "reconnect": False,
    }
    _publish(paths["consumption"], canonical_json(consumption))
    environment = os.environ.copy()
    environment.update(
        {
            "S09_E017_ADMISSION_ONLY_GUARDED": plan_sha256,
            "S09_E017_ADMISSION_ONLY_ATTEMPT_ID": authority[
                "admission_only_attempt_id"
            ],
            "S09_E017_ADMISSION_ONLY_CANDIDATE": str(candidate_path.resolve()),
            "S09_E017_ADMISSION_ONLY_CANDIDATE_SHA256": candidate_sha256,
            "S09_E017_ADMISSION_ONLY_AUTHORITY": str(authority_path.resolve()),
            "S09_E017_ADMISSION_ONLY_REMOTE_ATTEMPT_ROOT": authority[
                "remote_attempt_root"
            ],
            "S09_E017_ADMISSION_ONLY_DEADLINE_EPOCH": str(
                int(time.time()) + candidate["budgets"]["wall_seconds"]
            ),
        }
    )
    start = monotonic()
    process = popen(
        ["/bin/bash", str(plan_path)],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(
            timeout=candidate["budgets"]["wall_seconds"]
        )
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
    elapsed = monotonic() - start
    if timed_out:
        terminal = "ADMISSION_ONLY_GUARD_STOPPED"
        first_reason = "ADMISSION_ONLY_WALL_CAP_EXCEEDED"
    elif process.returncode != 0:
        terminal = "ADMISSION_ONLY_GUARD_STOPPED"
        first_reason = "ADMISSION_ONLY_PLAN_EXIT_NONZERO"
    else:
        terminal = "ADMISSION_ONLY_PLAN_COMPLETED"
        first_reason = None
    receipt = {
        "schema_version": "s09-e017-admission-only-guard-receipt-v1",
        "terminal_state": terminal,
        "first_reason": first_reason,
        "run_id": candidate["run_id"],
        "admission_only_attempt_id": authority["admission_only_attempt_id"],
        "candidate_sha256": candidate_sha256,
        "plan_sha256": plan_sha256,
        "authority_sha256": sha256_bytes(authority_bytes),
        "elapsed_seconds": elapsed,
        "process_returncode": process.returncode,
        "stdout_sha256": sha256_bytes(stdout.encode("utf-8")),
        "stderr_sha256": sha256_bytes(stderr.encode("utf-8")),
        "execution_authorized": False,
        "producer_authorized": False,
        "retry": False,
        "reconnect": False,
    }
    _publish(paths["stdout"], stdout.encode("utf-8"))
    _publish(paths["stderr"], stderr.encode("utf-8"))
    _publish(paths["guard"], canonical_json(receipt))
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--execute-authorised-admission-only", action="store_true")
    args = parser.parse_args()
    receipt = run_guarded_plan(
        candidate_path=args.candidate,
        candidate_sha256=args.candidate_sha256,
        authority_path=args.authority,
        plan_path=args.plan,
        plan_sha256=args.plan_sha256,
        execute_authorised_admission_only=args.execute_authorised_admission_only,
    )
    print(canonical_json(receipt).decode("utf-8"), end="")
    if receipt["terminal_state"] != "ADMISSION_ONLY_PLAN_COMPLETED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
