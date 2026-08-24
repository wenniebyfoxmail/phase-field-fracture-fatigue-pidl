"""Fail-closed authorization contract for the full RRaPINN G4 U0.12 pilot."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


LOCK_SCHEMA = "rrapinn-g4-prelaunch-lock-v2"
LOCK_STATUS = "READY_FOR_INDEPENDENT_GATE_TRAINING_UNAUTHORIZED"
AUTH_SCHEMA = "rrapinn-g4-user-authorization-v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class LaunchContractError(RuntimeError):
    """Raised before any producer output is created or training is entered."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_and_verify_prelaunch_lock(
    lock_path: Path, expected_sha256: str, repo_root: Path, producer_head: str,
) -> dict:
    if not _SHA256_RE.fullmatch(expected_sha256):
        raise LaunchContractError("prelaunch lock SHA256 is invalid")
    if not lock_path.is_file() or sha256_file(lock_path) != expected_sha256:
        raise LaunchContractError("prelaunch lock is missing or hash-mismatched")
    payload = json.loads(lock_path.read_text(encoding="utf-8"))
    if (
        payload.get("schema") != LOCK_SCHEMA
        or payload.get("status") != LOCK_STATUS
        or payload.get("training_authorized") is not False
        or payload.get("development_case") != "U0.12"
        or payload.get("first_detect_truth_cycle") != 83
        or payload.get("confirmation_used_as_truth") is not False
        or payload.get("integration_commit") != producer_head
        or not _COMMIT_RE.fullmatch(producer_head)
    ):
        raise LaunchContractError("prelaunch lock identity/state mismatch")
    root = repo_root.resolve()
    code = payload.get("locked_code", {})
    for record in code.get("files", []):
        path = (root / record["path"]).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise LaunchContractError("locked code path escapes producer repo") from exc
        if not path.is_file() or sha256_file(path) != record.get("sha256"):
            raise LaunchContractError(f"locked code changed: {record.get('path')}")
    if not code.get("files"):
        raise LaunchContractError("prelaunch lock has no locked code closure")
    for label, record in payload.get("artifacts", {}).items():
        path = Path(record.get("path", "")).expanduser()
        if not path.is_file() or sha256_file(path) != record.get("sha256"):
            raise LaunchContractError(f"locked artifact changed: {label}")
    return payload


def verify_user_authorization(
    authorization_path: Path, lock_sha256: str, producer_head: str,
) -> dict:
    if not authorization_path.is_file():
        raise LaunchContractError("explicit G4 user authorization receipt is missing")
    payload = json.loads(authorization_path.read_text(encoding="utf-8"))
    expected = {
        "schema": AUTH_SCHEMA,
        "authorized": True,
        "scope": "g4-u012-c60-two-arm-pilot",
        "development_case": "U0.12",
        "producer_head": producer_head,
        "prelaunch_lock_sha256": lock_sha256,
        "authorized_arms": ["A_absent", "B_on"],
        "heldout_access_authorized": False,
    }
    if payload != expected:
        raise LaunchContractError("explicit G4 authorization does not exactly match lock/head/scope")
    return payload
