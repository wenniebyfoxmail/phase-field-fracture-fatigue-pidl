from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from rrapinn_g4_launch_contract import (  # noqa: E402
    CANONICAL_RESTART_MANIFEST_SHA256,
    LaunchContractError,
    load_and_verify_prelaunch_lock,
    verify_user_authorization,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_lock_and_authorization_are_both_required(tmp_path: Path):
    repo = tmp_path / "repo"
    code = repo / "source" / "x.py"
    code.parent.mkdir(parents=True)
    code.write_text("x = 1\n", encoding="utf-8")
    artifact = tmp_path / "packet.json"
    artifact.write_text("{}\n", encoding="utf-8")
    head = "a" * 40
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({
        "schema": "rrapinn-g4-prelaunch-lock-v3",
        "status": "READY_FOR_INDEPENDENT_GATE_TRAINING_UNAUTHORIZED",
        "training_authorized": False, "development_case": "U0.12",
        "first_detect_truth_cycle": 83, "confirmation_used_as_truth": False,
        "integration_commit": head,
        "producer_contract": {
            "restart_manifest_sha256": CANONICAL_RESTART_MANIFEST_SHA256,
        },
        "locked_code": {"files": [{"path": "source/x.py", "sha256": _sha(code)}]},
        "artifacts": {"packet": {
            "scope": "bundle", "path": artifact.name, "sha256": _sha(artifact),
        }},
    }, sort_keys=True), encoding="utf-8")
    lock_sha = _sha(lock)
    assert load_and_verify_prelaunch_lock(lock, lock_sha, repo, head)["training_authorized"] is False
    with pytest.raises(LaunchContractError, match="authorization receipt is missing"):
        verify_user_authorization(tmp_path / "missing.json", lock_sha, head)
    auth = tmp_path / "auth.json"
    auth.write_text(json.dumps({
        "schema": "rrapinn-g4-user-authorization-v1", "authorized": True,
        "scope": "g4-u012-c60-two-arm-pilot", "development_case": "U0.12",
        "producer_head": head, "prelaunch_lock_sha256": lock_sha,
        "authorized_arms": ["A_absent", "B_on"],
        "heldout_access_authorized": False,
    }), encoding="utf-8")
    assert verify_user_authorization(auth, lock_sha, head)["authorized"] is True
    code.write_text("x = 2\n", encoding="utf-8")
    with pytest.raises(LaunchContractError, match="locked code changed"):
        load_and_verify_prelaunch_lock(lock, lock_sha, repo, head)


def test_authorization_cannot_expand_to_heldout(tmp_path: Path):
    auth = tmp_path / "auth.json"
    auth.write_text(json.dumps({
        "schema": "rrapinn-g4-user-authorization-v1", "authorized": True,
        "scope": "g4-u012-c60-two-arm-pilot", "development_case": "U0.12",
        "producer_head": "a" * 40, "prelaunch_lock_sha256": "b" * 64,
        "authorized_arms": ["A_absent", "B_on"],
        "heldout_access_authorized": True,
    }), encoding="utf-8")
    with pytest.raises(LaunchContractError, match="does not exactly match"):
        verify_user_authorization(auth, "b" * 64, "a" * 40)


def test_frozen_command_cannot_accept_a_caller_selected_restart_hash(tmp_path: Path):
    from scripts.run_rrapinn_g4_arm import frozen_command
    command = frozen_command(
        repo=tmp_path, arm="A_absent", restart_bundle=tmp_path / "restart",
        producer_head="a" * 40,
    )
    index = command.index("--resume-bundle-manifest-sha256")
    assert command[index + 1] == CANONICAL_RESTART_MANIFEST_SHA256
