from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import s09_e017_final_launch_guard as launch_guard  # noqa: E402
import verify_s09_e017_admission_handoff as handoff_module  # noqa: E402
from verify_s09_e017_admission_handoff import verify_handoff  # noqa: E402


def _canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _write(path: Path, value: object) -> bytes:
    payload = value if isinstance(value, bytes) else _canonical(value)
    path.write_bytes(payload)
    return payload


def _admission_evidence(root: Path) -> Path:
    root.mkdir(parents=True)
    authority = json.loads(
        (
            ROOT / "docs/research/S09/S09-E017/"
            "s09_e017_admission_only_authority_template_20261020.json"
        ).read_text()
    )
    authority.update(
        {
            "admission_only_attempt_id": handoff_module.STAGE1_ATTEMPT_ID,
            "candidate_sha256": handoff_module.STAGE1_CANDIDATE_SHA256,
            "plan_sha256": handoff_module.STAGE1_PLAN_SHA256,
            "approval_status": "APPROVED_FOR_ONE_RESOLVER_AND_ADMISSION_ONLY",
            "allowed_actions": [
                "STAGE_REVIEWED_ADMISSION_ONLY_HELPER",
                "RESOLVE_ADMISSION_ONLY_CONTROL",
                "RUN_METADATA_ADMISSION_ONLY",
            ],
            "maximum_connection_attempts": 1,
            "maximum_metadata_transfers": 1,
            "local_evidence_root": str(root.resolve()),
            "remote_attempt_root": (
                "/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/"
                "control/admission_only_attempts/" + handoff_module.STAGE1_ATTEMPT_ID
            ),
            "granted_by": "user",
            "granted_at": "2026-10-24T21:00:00+01:00",
        }
    )
    authority_bytes = _write(root / "admission_only_authority.json", authority)
    authority_sha = hashlib.sha256(authority_bytes).hexdigest()
    shared = {
        "run_id": launch_guard.RUN_ID,
        "admission_only_attempt_id": handoff_module.STAGE1_ATTEMPT_ID,
        "candidate_sha256": handoff_module.STAGE1_CANDIDATE_SHA256,
        "plan_sha256": handoff_module.STAGE1_PLAN_SHA256,
        "authority_sha256": authority_sha,
    }
    metadata = {
        "terminal_state": (
            "ADMISSION_ONLY_METADATA_READY__SCIENTIFIC_IDENTITIES_UNVERIFIED"
        ),
        "run_id": launch_guard.RUN_ID,
        "admission_only_attempt_id": handoff_module.STAGE1_ATTEMPT_ID,
        "authority_sha256": authority_sha,
        "archive": {
            "sha256": launch_guard.ARCHIVE_SHA256,
            "bytes_read": 14_359_316,
        },
        "execution_authorized": False,
        "producer_authorized": False,
        "counters": dict(handoff_module.ZERO_COUNTERS),
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
    _write(
        root / "authority_consumption_receipt.json",
        {
            **shared,
            "terminal_state": "ADMISSION_ONLY_AUTHORITY_CONSUMED_NO_RETRY",
            "retry": False,
            "reconnect": False,
        },
    )
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


def test_handoff_requires_exact_guard_and_metadata_success(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "admission" / handoff_module.STAGE1_ATTEMPT_ID
    monkeypatch.setattr(handoff_module, "EXPECTED_ADMISSION_ROOT", root)
    _admission_evidence(root)
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


def test_launch_guard_consumes_only_after_handoff(tmp_path: Path, monkeypatch) -> None:
    admission = tmp_path / "admission" / handoff_module.STAGE1_ATTEMPT_ID
    monkeypatch.setattr(handoff_module, "EXPECTED_ADMISSION_ROOT", admission)
    _admission_evidence(admission)
    authority = _execution_authority(tmp_path / "execution_authority.json")
    launcher = tmp_path / "launcher.py"
    plan = tmp_path / "plan.sh"
    launcher.write_text("# reviewed launcher\n")
    plan.write_text("#!/bin/bash\nset -euo pipefail\nexit 0\n")
    monkeypatch.setattr(launch_guard, "ROOT", tmp_path)
    evidence = (
        tmp_path
        / "local_archive/experiments/S09-E017/final_launch_attempts"
        / launch_guard.FINAL_ATTEMPT_ID
    )
    evidence.mkdir(parents=True)
    receipt = launch_guard.run_guard(
        admission_evidence_root=admission,
        execution_authority=authority,
        launcher=launcher,
        launcher_sha256=hashlib.sha256(launcher.read_bytes()).hexdigest(),
        plan=plan,
        plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),
        evidence_root=evidence,
        attempt_id=launch_guard.FINAL_ATTEMPT_ID,
        execute_authorised_final_launch=True,
    )
    assert receipt["terminal_state"] == "FINAL_LAUNCH_DISPATCH_COMPLETED"
    assert (evidence / "execution_authority_consumption_receipt.json").is_file()
    assert (evidence / "admission_handoff_receipt.json").is_file()
    alternate = tmp_path / "alternate-evidence"
    alternate.mkdir()
    try:
        launch_guard.run_guard(
            admission_evidence_root=admission,
            execution_authority=authority,
            launcher=launcher,
            launcher_sha256=hashlib.sha256(launcher.read_bytes()).hexdigest(),
            plan=plan,
            plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),
            evidence_root=alternate,
            attempt_id=launch_guard.FINAL_ATTEMPT_ID,
            execute_authorised_final_launch=True,
        )
    except ValueError as error:
        assert "evidence root drift" in str(error)
    else:
        raise AssertionError("alternate evidence root replay was accepted")


def test_launch_guard_writes_terminal_receipt_after_popen_failure(
    tmp_path: Path, monkeypatch
) -> None:
    admission = tmp_path / "admission" / handoff_module.STAGE1_ATTEMPT_ID
    monkeypatch.setattr(handoff_module, "EXPECTED_ADMISSION_ROOT", admission)
    _admission_evidence(admission)
    authority = _execution_authority(tmp_path / "execution_authority.json")
    launcher = tmp_path / "launcher.py"
    plan = tmp_path / "plan.sh"
    launcher.write_text("# reviewed launcher\n")
    plan.write_text("#!/bin/bash\nexit 0\n")
    monkeypatch.setattr(launch_guard, "ROOT", tmp_path)
    evidence = (
        tmp_path
        / "local_archive/experiments/S09-E017/final_launch_attempts"
        / launch_guard.FINAL_ATTEMPT_ID
    )
    evidence.mkdir(parents=True)

    def broken_popen(*_args, **_kwargs):
        raise OSError("fixture spawn failure")

    receipt = launch_guard.run_guard(
        admission_evidence_root=admission,
        execution_authority=authority,
        launcher=launcher,
        launcher_sha256=hashlib.sha256(launcher.read_bytes()).hexdigest(),
        plan=plan,
        plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),
        evidence_root=evidence,
        attempt_id=launch_guard.FINAL_ATTEMPT_ID,
        execute_authorised_final_launch=True,
        popen=broken_popen,
    )
    assert receipt["first_reason"] == "FINAL_LAUNCH_PROCESS_START_FAILED"
    assert (evidence / "guard_receipt.json").is_file()
    assert (evidence / "execution_authority_consumption_receipt.json").is_file()


def test_launch_guard_records_log_publication_failure(
    tmp_path: Path, monkeypatch
) -> None:
    admission = tmp_path / "admission" / handoff_module.STAGE1_ATTEMPT_ID
    monkeypatch.setattr(handoff_module, "EXPECTED_ADMISSION_ROOT", admission)
    _admission_evidence(admission)
    authority = _execution_authority(tmp_path / "execution_authority.json")
    launcher = tmp_path / "launcher.py"
    plan = tmp_path / "plan.sh"
    launcher.write_text("# reviewed launcher\n")
    plan.write_text("#!/bin/bash\nexit 0\n")
    monkeypatch.setattr(launch_guard, "ROOT", tmp_path)
    evidence = (
        tmp_path
        / "local_archive/experiments/S09-E017/final_launch_attempts"
        / launch_guard.FINAL_ATTEMPT_ID
    )
    evidence.mkdir(parents=True)

    def fail_stdout(path: Path, value: object) -> None:
        if path.name == "stdout.log":
            raise OSError("fixture log failure")
        launch_guard._publish(path, value)

    receipt = launch_guard.run_guard(
        admission_evidence_root=admission,
        execution_authority=authority,
        launcher=launcher,
        launcher_sha256=hashlib.sha256(launcher.read_bytes()).hexdigest(),
        plan=plan,
        plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),
        evidence_root=evidence,
        attempt_id=launch_guard.FINAL_ATTEMPT_ID,
        execute_authorised_final_launch=True,
        publisher=fail_stdout,
    )
    assert receipt["first_reason"] == "LOCAL_LOG_WRITE_FAILED"
    assert receipt["evidence_write_errors"][0]["artifact"] == "stdout"
    assert (evidence / "guard_receipt.json").is_file()


def test_launch_guard_kills_process_and_receipts_communication_failure(
    tmp_path: Path, monkeypatch
) -> None:
    admission = tmp_path / "admission" / handoff_module.STAGE1_ATTEMPT_ID
    monkeypatch.setattr(handoff_module, "EXPECTED_ADMISSION_ROOT", admission)
    _admission_evidence(admission)
    authority = _execution_authority(tmp_path / "execution_authority.json")
    launcher = tmp_path / "launcher.py"
    plan = tmp_path / "plan.sh"
    launcher.write_text("# reviewed launcher\n")
    plan.write_text("#!/bin/bash\nexit 0\n")
    monkeypatch.setattr(launch_guard, "ROOT", tmp_path)
    evidence = (
        tmp_path
        / "local_archive/experiments/S09-E017/final_launch_attempts"
        / launch_guard.FINAL_ATTEMPT_ID
    )
    evidence.mkdir(parents=True)

    class BrokenProcess:
        pid = 987654
        returncode = None

        def communicate(self, timeout):
            raise OSError(f"fixture communication failure after {timeout}")

        def wait(self, timeout):
            assert timeout == 10
            self.returncode = -9
            return self.returncode

    killed = []
    receipt = launch_guard.run_guard(
        admission_evidence_root=admission,
        execution_authority=authority,
        launcher=launcher,
        launcher_sha256=hashlib.sha256(launcher.read_bytes()).hexdigest(),
        plan=plan,
        plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),
        evidence_root=evidence,
        attempt_id=launch_guard.FINAL_ATTEMPT_ID,
        execute_authorised_final_launch=True,
        popen=lambda *_args, **_kwargs: BrokenProcess(),
        kill_process_group=lambda pid, sig: killed.append((pid, sig)),
    )
    assert receipt["first_reason"] == "FINAL_LAUNCH_PROCESS_IO_FAILED"
    assert killed == [(987654, launch_guard.signal.SIGKILL)]
    assert receipt["process_returncode"] == -9
    assert receipt["remote_detached_state_unknown"] is True
    assert (evidence / "guard_receipt.json").is_file()


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
        cwd=tmp_path,
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
        cwd=tmp_path,
    )
    assert result.returncode == 0
    assert (code / "resolver-called").is_file()
    assert (code / "producer-called").is_file()
    started = json.loads((control / "final_launch_started.json").read_text())
    assert started["session_name"] == "pf_test"
