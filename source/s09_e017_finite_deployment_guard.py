"""Finite outer guard for the separately reviewed S09-E017 deployment plan."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
from typing import Any, Mapping

from s09_e017_chunked_deployment import (
    DeploymentStop,
    canonical_json,
    require_new_path,
    _publish_bytes_no_replace,
)


AUTHORITY_SCHEMA = "s09-e017-chunked-deployment-authority-v1"
RECEIPT_SCHEMA = "s09-e017-finite-deployment-guard-receipt-v1"
ACTION = "CONTENT_ADDRESSED_ARCHIVE_DEPLOYMENT"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _strict_json(path: Path) -> tuple[dict[str, Any], bytes]:
    if not path.is_file() or path.is_symlink():
        raise DeploymentStop("CONTROL_FILE_MISSING", f"invalid control file: {path}")
    payload = path.read_bytes()
    try:
        value = json.loads(
            payload,
            parse_constant=lambda item: (_ for _ in ()).throw(ValueError(item)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise DeploymentStop("CONTROL_JSON_INVALID", f"invalid JSON: {path}") from error
    if not isinstance(value, dict) or canonical_json(value) != payload:
        raise DeploymentStop("CONTROL_JSON_INVALID", f"non-canonical JSON: {path}")
    return value, payload


def validate_deployment_authority(
    authority: Mapping[str, Any],
    *,
    candidate_sha256: str,
    plan_sha256: str,
    run_id: str,
) -> None:
    required = {
        "schema_version",
        "approval_status",
        "deployment_authorized",
        "run_id",
        "candidate_sha256",
        "plan_sha256",
        "allowed_actions",
        "deployment_attempt_id",
        "maximum_connection_attempts",
        "maximum_metadata_transfers",
        "maximum_chunk_transfers",
        "maximum_source_bytes",
        "wall_seconds",
        "retry",
        "reconnect",
        "execution_authorized",
        "granted_by",
        "granted_at",
    }
    if set(authority) != required:
        raise DeploymentStop("DEPLOYMENT_AUTHORITY_INVALID", "authority keys drift")
    checks = [
        authority["schema_version"] == AUTHORITY_SCHEMA,
        authority["approval_status"] == "APPROVED_FOR_ONE_FINITE_DEPLOYMENT",
        authority["deployment_authorized"] is True,
        authority["execution_authorized"] is False,
        authority["run_id"] == run_id,
        authority["candidate_sha256"] == candidate_sha256,
        authority["plan_sha256"] == plan_sha256,
        authority["allowed_actions"] == [ACTION],
        authority["maximum_connection_attempts"] == 1,
        authority["maximum_metadata_transfers"] == 1,
        authority["maximum_chunk_transfers"] == 1,
        authority["maximum_source_bytes"] == 14_500_000,
        authority["wall_seconds"] == 1800,
        authority["retry"] is False,
        authority["reconnect"] is False,
        authority["granted_by"] == "user",
        isinstance(authority["granted_at"], str) and bool(authority["granted_at"]),
        isinstance(authority["deployment_attempt_id"], str)
        and re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", authority["deployment_attempt_id"]
        )
        is not None,
    ]
    if not all(checks):
        raise DeploymentStop(
            "DEPLOYMENT_AUTHORITY_INVALID", "authority value drift or disabled"
        )


def run_guarded_plan(
    *,
    candidate_path: Path,
    candidate_sha256: str,
    authority_path: Path,
    plan_path: Path,
    plan_sha256: str,
    receipt_path: Path,
    execute_authorised_deployment: bool,
    monotonic=time.monotonic,
) -> dict[str, Any]:
    if not execute_authorised_deployment:
        raise DeploymentStop(
            "DEPLOYMENT_DISABLED", "--execute-authorised-deployment is required"
        )
    require_new_path(receipt_path, reason="RECEIPT_PATH_CONFLICT")
    candidate, candidate_bytes = _strict_json(candidate_path)
    if hashlib.sha256(candidate_bytes).hexdigest() != candidate_sha256:
        raise DeploymentStop("CANDIDATE_HASH_MISMATCH", "candidate SHA-256 mismatch")
    if candidate.get("status") != "LOCAL_CANDIDATE_NO_REMOTE_ACTION_NO_AUTHORITY":
        raise DeploymentStop("CANDIDATE_INVALID", "candidate status drift")
    if sha256_path(plan_path) != plan_sha256:
        raise DeploymentStop("PLAN_HASH_MISMATCH", "plan SHA-256 mismatch")
    authority, _ = _strict_json(authority_path)
    validate_deployment_authority(
        authority,
        candidate_sha256=candidate_sha256,
        plan_sha256=plan_sha256,
        run_id=candidate["frozen_science"]["run_id"],
    )
    start = monotonic()
    deadline_epoch = int(time.time()) + authority["wall_seconds"]
    environment = os.environ.copy()
    environment.update(
        {
            "S09_E017_GUARDED": plan_sha256,
            "S09_E017_DEPLOYMENT_ATTEMPT_ID": authority["deployment_attempt_id"],
            "S09_E017_DEPLOYMENT_DEADLINE_EPOCH": str(deadline_epoch),
        }
    )
    process = subprocess.Popen(
        ["/bin/bash", str(plan_path)],
        cwd=plan_path.resolve().parents[1],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=authority["wall_seconds"])
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
        terminal_state = "DEPLOYMENT_GUARD_STOPPED"
        first_reason = "DEPLOYMENT_WALL_CAP_EXCEEDED"
    elif process.returncode != 0:
        terminal_state = "DEPLOYMENT_GUARD_STOPPED"
        first_reason = "DEPLOYMENT_PLAN_EXIT_NONZERO"
    else:
        terminal_state = "DEPLOYMENT_PLAN_COMPLETED"
        first_reason = None
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "terminal_state": terminal_state,
        "first_reason": first_reason,
        "run_id": candidate["frozen_science"]["run_id"],
        "deployment_attempt_id": authority["deployment_attempt_id"],
        "candidate_sha256": candidate_sha256,
        "plan_sha256": plan_sha256,
        "wall_cap_seconds": authority["wall_seconds"],
        "elapsed_seconds": elapsed,
        "process_returncode": process.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "execution_authorized": False,
        "retry": False,
        "reconnect": False,
    }
    _publish_bytes_no_replace(receipt_path, canonical_json(receipt))
    return receipt
