from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import pytest

import s09_e017_finite_deployment_guard as guard
from s09_e017_chunked_deployment import DeploymentStop, canonical_json


RUN_ID = "S09-E017-R001-factorised-head-p0"


def _controls(tmp_path: Path, plan_body: str = "exit 0\n"):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    plan = scripts / "plan.sh"
    plan.write_text("#!/bin/bash\nset -eu\n" + plan_body, encoding="utf-8")
    plan.chmod(0o755)
    plan_sha = hashlib.sha256(plan.read_bytes()).hexdigest()
    candidate = {
        "status": "LOCAL_CANDIDATE_NO_REMOTE_ACTION_NO_AUTHORITY",
        "frozen_science": {"run_id": RUN_ID},
    }
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_bytes(canonical_json(candidate))
    candidate_sha = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    authority = {
        "schema_version": guard.AUTHORITY_SCHEMA,
        "approval_status": "APPROVED_FOR_ONE_FINITE_DEPLOYMENT",
        "deployment_authorized": True,
        "execution_authorized": False,
        "run_id": RUN_ID,
        "candidate_sha256": candidate_sha,
        "plan_sha256": plan_sha,
        "allowed_actions": [guard.ACTION],
        "deployment_attempt_id": "fixture-001",
        "consumption_receipt_path": str(
            tmp_path / "consumed" / "fixture-001" / "guard-consumption.json"
        ),
        "maximum_connection_attempts": 1,
        "maximum_metadata_transfers": 1,
        "maximum_chunk_transfers": 1,
        "maximum_source_bytes": 14_500_000,
        "wall_seconds": 1800,
        "retry": False,
        "reconnect": False,
        "granted_by": "user",
        "granted_at": "2026-10-20T12:00:00+01:00",
    }
    authority_path = tmp_path / "authority.json"
    authority_path.write_bytes(canonical_json(authority))
    return candidate_path, candidate_sha, authority_path, plan, plan_sha


def test_guard_rejects_disabled_call_before_plan_execution(tmp_path: Path) -> None:
    candidate, candidate_sha, authority, plan, plan_sha = _controls(
        tmp_path, "touch should-not-exist\n"
    )
    with pytest.raises(DeploymentStop) as caught:
        guard.run_guarded_plan(
            candidate_path=candidate,
            candidate_sha256=candidate_sha,
            authority_path=authority,
            plan_path=plan,
            plan_sha256=plan_sha,
            receipt_path=tmp_path / "receipt.json",
            execute_authorised_deployment=False,
        )
    assert caught.value.first_reason == "DEPLOYMENT_DISABLED"
    assert not (tmp_path / "should-not-exist").exists()


def test_guard_runs_exact_plan_once_and_writes_success_receipt(tmp_path: Path) -> None:
    candidate, candidate_sha, authority, plan, plan_sha = _controls(
        tmp_path,
        '[[ "$S09_E017_GUARDED" = "' + "PLACEHOLDER" + '" ]]\n',
    )
    plan.write_text(
        "#!/bin/bash\nset -eu\n"
        '[[ "$S09_E017_GUARDED" = "$(python3 - "$0" <<\'PY\'\n'
        "import hashlib,pathlib,sys\n"
        "print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())\n"
        "PY\n"
        ')" ]]\n',
        encoding="utf-8",
    )
    plan_sha = hashlib.sha256(plan.read_bytes()).hexdigest()
    authority_data = json.loads(authority.read_text())
    authority_data["plan_sha256"] = plan_sha
    authority.write_bytes(canonical_json(authority_data))
    receipt_path = tmp_path / "receipt.json"
    receipt = guard.run_guarded_plan(
        candidate_path=candidate,
        candidate_sha256=candidate_sha,
        authority_path=authority,
        plan_path=plan,
        plan_sha256=plan_sha,
        receipt_path=receipt_path,
        execute_authorised_deployment=True,
    )
    assert receipt["terminal_state"] == "DEPLOYMENT_PLAN_COMPLETED"
    assert receipt["first_reason"] is None
    assert json.loads(receipt_path.read_text()) == receipt


def test_guard_nonzero_plan_is_a_nonretrying_stop(tmp_path: Path) -> None:
    candidate, candidate_sha, authority, plan, plan_sha = _controls(
        tmp_path, "echo first-cause >&2\nexit 7\n"
    )
    receipt = guard.run_guarded_plan(
        candidate_path=candidate,
        candidate_sha256=candidate_sha,
        authority_path=authority,
        plan_path=plan,
        plan_sha256=plan_sha,
        receipt_path=tmp_path / "receipt.json",
        execute_authorised_deployment=True,
    )
    assert receipt["terminal_state"] == "DEPLOYMENT_GUARD_STOPPED"
    assert receipt["first_reason"] == "DEPLOYMENT_PLAN_EXIT_NONZERO"
    assert receipt["process_returncode"] == 7
    assert "first-cause" in receipt["stderr"]
    assert receipt["retry"] is False
    assert receipt["reconnect"] is False


def test_guard_consumes_authority_before_plan_and_blocks_replay(
    tmp_path: Path,
) -> None:
    counter = tmp_path / "plan-calls.txt"
    candidate, candidate_sha, authority, plan, plan_sha = _controls(
        tmp_path, f'echo called >> "{counter}"\n'
    )
    first = guard.run_guarded_plan(
        candidate_path=candidate,
        candidate_sha256=candidate_sha,
        authority_path=authority,
        plan_path=plan,
        plan_sha256=plan_sha,
        receipt_path=tmp_path / "receipt-1.json",
        execute_authorised_deployment=True,
    )
    assert first["terminal_state"] == "DEPLOYMENT_PLAN_COMPLETED"
    with pytest.raises(DeploymentStop) as caught:
        guard.run_guarded_plan(
            candidate_path=candidate,
            candidate_sha256=candidate_sha,
            authority_path=authority,
            plan_path=plan,
            plan_sha256=plan_sha,
            receipt_path=tmp_path / "receipt-2.json",
            execute_authorised_deployment=True,
        )
    assert caught.value.first_reason == "PATH_CONFLICT"
    assert counter.read_text().splitlines() == ["called"]


def test_guard_timeout_kills_process_group_and_records_wall_first_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate, candidate_sha, authority, plan, plan_sha = _controls(tmp_path)

    class FakeProcess:
        pid = 4242
        returncode = -15

        def __init__(self):
            self.calls = 0

        def communicate(self, timeout=None):
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired(["plan"], timeout)
            return "", "timed out"

    fake = FakeProcess()
    monkeypatch.setattr(guard.subprocess, "Popen", lambda *args, **kwargs: fake)
    killed: list[tuple[int, signal.Signals]] = []
    import signal

    monkeypatch.setattr(guard.os, "killpg", lambda pid, sig: killed.append((pid, sig)))
    receipt = guard.run_guarded_plan(
        candidate_path=candidate,
        candidate_sha256=candidate_sha,
        authority_path=authority,
        plan_path=plan,
        plan_sha256=plan_sha,
        receipt_path=tmp_path / "receipt.json",
        execute_authorised_deployment=True,
    )
    assert killed == [(4242, signal.SIGTERM)]
    assert receipt["first_reason"] == "DEPLOYMENT_WALL_CAP_EXCEEDED"
    assert receipt["terminal_state"] == "DEPLOYMENT_GUARD_STOPPED"


def test_exact_plan_has_one_connection_and_two_bounded_transfer_sites() -> None:
    root = Path(__file__).resolve().parents[1]
    plan = root / "scripts/s09_e017_chunked_deployment_plan.sh"
    text = plan.read_text(encoding="utf-8")
    assert text.count("ssh -MNf") == 1
    assert text.count("rsync -aR --ignore-existing") == 1
    assert text.count("rsync -a --ignore-existing --files-from") == 1
    assert text.count("ProxyCommand=/usr/bin/false") >= 2
    assert "SOURCE_BYTE_CAP=14500000" in text
    assert "verify-archive" in text
    assert "gzip.wait()" not in text
    for relative in (
        "source/s09_e017_chunked_deployment.py",
        "scripts/s09_e017_chunked_archive.py",
    ):
        digest = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        assert f'"{relative}": "{digest}"' in text
    completed = subprocess.run(
        ["/bin/bash", "-n", str(plan)], check=False, capture_output=True, text=True
    )
    assert completed.returncode == 0, completed.stderr


def test_authority_template_cannot_enable_scientific_execution(tmp_path: Path) -> None:
    candidate, candidate_sha, authority, plan, plan_sha = _controls(tmp_path)
    value = json.loads(authority.read_text())
    value["execution_authorized"] = True
    authority.write_bytes(canonical_json(value))
    with pytest.raises(DeploymentStop) as caught:
        guard.run_guarded_plan(
            candidate_path=candidate,
            candidate_sha256=candidate_sha,
            authority_path=authority,
            plan_path=plan,
            plan_sha256=plan_sha,
            receipt_path=tmp_path / "receipt.json",
            execute_authorised_deployment=True,
        )
    assert caught.value.first_reason == "DEPLOYMENT_AUTHORITY_INVALID"


def test_tracked_candidate_binds_exact_helpers_and_disabled_authority() -> None:
    root = Path(__file__).resolve().parents[1]
    candidate_path = (
        root / "docs/research/S09/S09-E017/chunked_deployment_candidate_20261020.json"
    )
    candidate_bytes = candidate_path.read_bytes()
    candidate = json.loads(candidate_bytes)
    assert canonical_json(candidate) == candidate_bytes
    for item in candidate["helper"].values():
        if not isinstance(item, dict) or "path" not in item:
            continue
        payload = (root / item["path"]).read_bytes()
        assert len(payload) == item["bytes"]
        assert hashlib.sha256(payload).hexdigest() == item["sha256"]
    authority_path = (
        root
        / "docs/research/S09/S09-E017"
        / "chunked_deployment_authority_template_20261020.json"
    )
    authority_bytes = authority_path.read_bytes()
    authority = json.loads(authority_bytes)
    assert canonical_json(authority) == authority_bytes
    assert authority["candidate_sha256"] == hashlib.sha256(candidate_bytes).hexdigest()
    assert authority["approval_status"] == "NOT_GRANTED"
    assert authority["deployment_authorized"] is False
    assert authority["execution_authorized"] is False
