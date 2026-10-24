from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import s09_e017_final_launch_guard as launch_guard  # noqa: E402
from verify_s09_e017_admission_handoff import verify_handoff  # noqa: E402


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _write(path: Path, value: object) -> bytes:
    payload = value if isinstance(value, bytes) else _canonical(value)
    path.write_bytes(payload)
    return payload


def _admission_evidence(root: Path) -> Path:
    root.mkdir()
    authority = {
        "admission_only_attempt_id": "admission-test",
        "candidate_sha256": "a" * 64,
        "plan_sha256": "b" * 64,
    }
    authority_bytes = _write(root / "admission_only_authority.json", authority)
    authority_sha = hashlib.sha256(authority_bytes).hexdigest()
    shared = {
        "run_id": launch_guard.RUN_ID,
        "admission_only_attempt_id": "admission-test",
        "candidate_sha256": "a" * 64,
        "plan_sha256": "b" * 64,
        "authority_sha256": authority_sha,
    }
    metadata = {
        "terminal_state": (
            "ADMISSION_ONLY_METADATA_READY__SCIENTIFIC_IDENTITIES_UNVERIFIED"
        ),
        "run_id": launch_guard.RUN_ID,
        "admission_only_attempt_id": "admission-test",
        "authority_sha256": authority_sha,
        "archive": {
            "sha256": launch_guard.ARCHIVE_SHA256,
            "bytes_read": 14_359_316,
        },
        "execution_authorized": False,
        "producer_authorized": False,
        "counters": {"model_forwards": 0, "optimizer_steps": 0},
        "retry": False,
        "reconnect": False,
    }
    stdout = _canonical({"hostname": "GPUServer8"}) + b"\n" + _canonical(metadata)
    _write(root / "stdout.log", stdout)
    _write(
        root / "guard_receipt.json",
        {
            **shared,
            "terminal_state": "ADMISSION_ONLY_PLAN_COMPLETED",
            "process_returncode": 0,
            "first_reason": None,
            "evidence_write_errors": [],
            "stdout_published": True,
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "retry": False,
            "reconnect": False,
        },
    )
    _write(root / "authority_consumption_receipt.json", shared)
    return root


def _execution_authority(path: Path) -> Path:
    _write(
        path,
        {
            "schema_version": "s09-e017-one-run-authority-v1",
            "approval_status": "APPROVED_FOR_ONE_ADMISSION_AND_COMPLETE_RUN",
            "execution_authorized": True,
            "run_id": launch_guard.RUN_ID,
            "reviewed_adapter_commit": launch_guard.ADAPTER_COMMIT,
            "reviewed_control_commit": launch_guard.CONTROL_COMMIT,
            "candidate_config_sha256": launch_guard.CANDIDATE_SHA256,
            "code_archive_sha256": launch_guard.ARCHIVE_SHA256,
            "allowed_actions": ["LIVE_ADMISSION", "COMPLETE_THREE_ARM_RUN"],
            "maximum_launches": 1,
            "retry": False,
            "alternate_host": False,
            "alternate_gpu": False,
            "network_recovery_confirmed": True,
            "granted_by": "user",
            "granted_at": "2026-10-24T21:00:00+01:00",
        },
    )
    return path


def test_handoff_requires_exact_guard_and_metadata_success(tmp_path: Path) -> None:
    root = _admission_evidence(tmp_path / "admission")
    receipt = verify_handoff(root)
    assert receipt["terminal_state"] == (
        "ADMISSION_ONLY_EVIDENCE_VERIFIED_FOR_CONDITIONAL_LAUNCH"
    )
    guard = json.loads((root / "guard_receipt.json").read_text())
    guard["process_returncode"] = 1
    _write(root / "guard_receipt.json", guard)
    try:
        verify_handoff(root)
    except ValueError as error:
        assert "exit cleanly" in str(error)
    else:
        raise AssertionError("dirty guard exit was accepted")


def test_launch_guard_consumes_only_after_handoff(tmp_path: Path) -> None:
    admission = _admission_evidence(tmp_path / "admission")
    authority = _execution_authority(tmp_path / "execution_authority.json")
    launcher = tmp_path / "launcher.py"
    plan = tmp_path / "plan.sh"
    launcher.write_text("# reviewed launcher\n")
    plan.write_text("#!/bin/bash\nset -euo pipefail\nexit 0\n")
    evidence = tmp_path / "launch-evidence"
    evidence.mkdir()
    receipt = launch_guard.run_guard(
        admission_evidence_root=admission,
        execution_authority=authority,
        launcher=launcher,
        launcher_sha256=hashlib.sha256(launcher.read_bytes()).hexdigest(),
        plan=plan,
        plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),
        evidence_root=evidence,
        attempt_id="launch-test",
        execute_authorised_final_launch=True,
    )
    assert receipt["terminal_state"] == "FINAL_LAUNCH_DISPATCH_COMPLETED"
    assert (evidence / "execution_authority_consumption_receipt.json").is_file()
    assert (evidence / "admission_handoff_receipt.json").is_file()


def test_remote_launcher_resolver_failure_never_invokes_producer(
    tmp_path: Path,
) -> None:
    code = tmp_path / "code"
    scripts = code / "scripts"
    control = tmp_path / "control"
    scripts.mkdir(parents=True)
    control.mkdir()
    (scripts / "resolve_s09_e017_execution.py").write_text("raise SystemExit(9)\n")
    (scripts / "run_s09_e017_producer.py").write_text(
        "from pathlib import Path\nPath('producer-called').write_text('bad')\n"
    )
    launcher = ROOT / "scripts/s09_e017_final_launch.py"
    result = subprocess.run(
        [
            sys.executable,
            str(launcher),
            "--code-root",
            str(code),
            "--control-root",
            str(control),
            "--session-name",
            "pf_test",
            "--log-path",
            str(control / "launch.log"),
        ],
        cwd=code,
    )
    assert result.returncode != 0
    failure = json.loads((control / "final_launch_failure.json").read_text())
    assert failure["producer_invoked"] is False
    assert not (code / "producer-called").exists()


def test_remote_launcher_executes_producer_only_after_resolver(
    tmp_path: Path,
) -> None:
    code = tmp_path / "code"
    scripts = code / "scripts"
    control = tmp_path / "control"
    scripts.mkdir(parents=True)
    control.mkdir()
    (scripts / "resolve_s09_e017_execution.py").write_text(
        "from pathlib import Path\nPath('resolver-called').write_text('ok')\n"
    )
    (scripts / "run_s09_e017_producer.py").write_text(
        "from pathlib import Path\n"
        "assert Path('resolver-called').is_file()\n"
        "Path('producer-called').write_text('ok')\n"
    )
    launcher = ROOT / "scripts/s09_e017_final_launch.py"
    result = subprocess.run(
        [
            sys.executable,
            str(launcher),
            "--code-root",
            str(code),
            "--control-root",
            str(control),
            "--session-name",
            "pf_test",
            "--log-path",
            str(control / "launch.log"),
        ],
        cwd=code,
    )
    assert result.returncode == 0
    assert (code / "resolver-called").is_file()
    assert (code / "producer-called").is_file()
    started = json.loads((control / "final_launch_started.json").read_text())
    assert started["session_name"] == "pf_test"
