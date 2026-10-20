from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
sys.path.insert(0, str(ROOT / "scripts"))

import s09_e017_admission_only as admission  # noqa: E402
import s09_e017_admission_only_guard as guard  # noqa: E402
import resolve_s09_e017_admission_only as resolver  # noqa: E402


CANDIDATE_PATH = (
    ROOT / "docs/research/S09/S09-E017/"
    "s09_e017_admission_only_candidate_20261020.json"
)
TEMPLATE_PATH = (
    ROOT / "docs/research/S09/S09-E017/"
    "s09_e017_admission_only_authority_template_20261020.json"
)
PLAN_PATH = ROOT / "scripts/s09_e017_admission_only_plan.sh"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def candidate() -> dict:
    return load(CANDIDATE_PATH)


def candidate_sha() -> str:
    return hashlib.sha256(CANDIDATE_PATH.read_bytes()).hexdigest()


def authority(tmp_path: Path, *, attempt: str = "admission-only-test") -> dict:
    item = candidate()
    local = tmp_path / attempt
    local.mkdir()
    return {
        "schema_version": admission.AUTHORITY_SCHEMA,
        "approval_status": "APPROVED_FOR_ONE_RESOLVER_AND_ADMISSION_ONLY",
        "run_id": admission.RUN_ID,
        "admission_only_attempt_id": attempt,
        "candidate_sha256": candidate_sha(),
        "accepted_archive_path": item["accepted_state"]["archive_path"],
        "accepted_archive_bytes": admission.ARCHIVE_BYTES,
        "accepted_archive_sha256": admission.ARCHIVE_SHA256,
        "accepted_control_commit": admission.CONTROL_COMMIT,
        "guard_sha256": item["guard_sha256"],
        "plan_sha256": item["plan_sha256"],
        "helper_manifest": item["helper_manifest"],
        "allowed_actions": list(admission.GUARD_ACTIONS),
        "execution_authorized": False,
        "producer_authorized": False,
        "scientific_asset_content_reads": False,
        "maximum_connection_attempts": 1,
        "maximum_metadata_transfers": 1,
        "retry": False,
        "reconnect": False,
        "alternate_host": False,
        "alternate_gpu": False,
        "budgets": item["budgets"],
        "local_evidence_root": str(local),
        "remote_attempt_root": (
            "/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/"
            f"control/admission_only_attempts/{attempt}"
        ),
        "granted_by": "user",
        "granted_at": "2026-10-20T19:00:00+01:00",
    }


def canonical_file(path: Path, value: object) -> None:
    path.write_bytes(admission.canonical_json(value))


def archive_verification() -> dict:
    return {
        "path": candidate()["accepted_state"]["archive_path"],
        "bytes": admission.ARCHIVE_BYTES,
        "bytes_read": admission.ARCHIVE_BYTES,
        "sha256": admission.ARCHIVE_SHA256,
        "stat": {
            "device": 1,
            "inode": 2,
            "mode": 0o100600,
            "mtime_ns": 3,
            "size_bytes": admission.ARCHIVE_BYTES,
        },
    }


def test_frozen_candidate_and_helper_manifest_are_exact() -> None:
    item = candidate()
    admission.validate_candidate(item)
    assert hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest() == item["plan_sha256"]
    assert (
        hashlib.sha256(
            (ROOT / "scripts/s09_e017_admission_only_guard.py").read_bytes()
        ).hexdigest()
        == item["guard_sha256"]
    )
    for relative, digest in item["helper_manifest"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest
    assert item["scope"]["execution_authorized"] is False
    assert item["scope"]["producer_authorized"] is False
    assert item["scope"]["scientific_asset_content_reads"] is False


def test_disabled_template_is_not_a_granted_authority() -> None:
    with pytest.raises(admission.AdmissionOnlyStop) as caught:
        admission.validate_authority(
            load(TEMPLATE_PATH),
            candidate(),
            candidate_sha256=candidate_sha(),
            plan_sha256=candidate()["plan_sha256"],
        )
    assert caught.value.first_reason == "AUTHORITY_INVALID"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("execution_authorized", True),
        ("producer_authorized", True),
        ("scientific_asset_content_reads", True),
        ("maximum_connection_attempts", 2),
        ("maximum_metadata_transfers", 2),
        ("retry", True),
        ("reconnect", True),
        ("alternate_host", True),
        ("alternate_gpu", True),
    ],
)
def test_authority_rejects_scope_expansion(
    tmp_path: Path, field: str, value: object
) -> None:
    item = authority(tmp_path)
    item[field] = value
    with pytest.raises(admission.AdmissionOnlyStop) as caught:
        admission.validate_authority(
            item,
            candidate(),
            candidate_sha256=candidate_sha(),
            plan_sha256=candidate()["plan_sha256"],
        )
    assert caught.value.first_reason == "AUTHORITY_INVALID"


def test_full_run_authority_cannot_cross_the_schema(tmp_path: Path) -> None:
    item = authority(tmp_path)
    item["schema_version"] = "s09-e017-one-run-authority-v1"
    item["approval_status"] = "APPROVED_FOR_ONE_ADMISSION_AND_COMPLETE_RUN"
    item["execution_authorized"] = True
    item["allowed_actions"] = ["LIVE_ADMISSION", "COMPLETE_THREE_ARM_RUN"]
    with pytest.raises(admission.AdmissionOnlyStop):
        admission.validate_authority(
            item,
            candidate(),
            candidate_sha256=candidate_sha(),
            plan_sha256=candidate()["plan_sha256"],
        )


def test_resolved_control_is_nonexecuting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item = candidate()
    auth = authority(tmp_path)
    monkeypatch.setattr(admission, "assert_no_scientific_modules", lambda: None)
    resolved = admission.resolve_admission_only(
        candidate=item,
        authority=auth,
        candidate_sha256=candidate_sha(),
        plan_sha256=item["plan_sha256"],
        package_config_sha256=admission.PACKAGE_SHA256,
        final_candidate_sha256=admission.FINAL_CANDIDATE_SHA256,
        archive_sha256=admission.ARCHIVE_SHA256,
        archive_verification=archive_verification(),
        observed_commit=admission.CONTROL_COMMIT,
    )
    admission.validate_resolved(resolved)
    assert resolved["status"] == "RESOLVED_FOR_ADMISSION_ONLY"
    assert resolved["execution_authorized"] is False
    assert resolved["producer_authorized"] is False
    assert "COMPLETE_THREE_ARM_RUN" not in resolved["allowed_actions"]
    assert all(value == 0 for value in resolved["counters"].values())


def test_metadata_admission_stops_with_scientific_identities_unverified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item = candidate()
    auth = authority(tmp_path)
    monkeypatch.setattr(admission, "assert_no_scientific_modules", lambda: None)
    resolved = admission.resolve_admission_only(
        candidate=item,
        authority=auth,
        candidate_sha256=candidate_sha(),
        plan_sha256=item["plan_sha256"],
        package_config_sha256=admission.PACKAGE_SHA256,
        final_candidate_sha256=admission.FINAL_CANDIDATE_SHA256,
        archive_sha256=admission.ARCHIVE_SHA256,
        archive_verification=archive_verification(),
        observed_commit=admission.CONTROL_COMMIT,
    )
    monkeypatch.setattr(admission.platform, "system", lambda: "Linux")
    monkeypatch.setattr(admission.socket, "gethostname", lambda: admission.HOSTNAME)
    monkeypatch.setattr(admission.os, "getuid", lambda: admission.REMOTE_UID)
    monkeypatch.setattr(admission.getpass, "getuser", lambda: admission.REMOTE_USER)
    monkeypatch.setattr(
        Path, "cwd", classmethod(lambda cls: Path(item["remote"]["code_root"]))
    )
    monkeypatch.setattr(
        admission,
        "git_identity",
        lambda *args, **kwargs: {"head": admission.CONTROL_COMMIT, "dirty": False},
    )
    monkeypatch.setattr(Path, "exists", lambda self: False)
    monkeypatch.setattr(Path, "is_dir", lambda self: True)
    monkeypatch.setattr(Path, "is_symlink", lambda self: False)

    def content_reopen_forbidden(*args, **kwargs):
        raise AssertionError("admission reopened archive content")

    monkeypatch.setattr(admission, "sha256_path", content_reopen_forbidden)
    frozen_stat = archive_verification()["stat"]
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda self: SimpleNamespace(
            st_dev=frozen_stat["device"],
            st_ino=frozen_stat["inode"],
            st_mode=frozen_stat["mode"],
            st_mtime_ns=frozen_stat["mtime_ns"],
            st_size=frozen_stat["size_bytes"],
        ),
    )
    metadata_calls: list[tuple[str, str]] = []

    def metadata(path: Path, *, kind: str):
        metadata_calls.append((str(path), kind))
        return {
            "path": str(path),
            "kind": kind,
            "size_bytes": 1,
            "mode": 0,
            "content_opened": False,
        }

    monkeypatch.setattr(admission, "path_metadata", metadata)
    monkeypatch.setattr(
        admission,
        "host_resource_snapshot",
        lambda *args, **kwargs: {
            "host_max_rss_bytes": 1,
            "free_disk_bytes": 30 * 1024**3,
            "admission_only_control_tree_bytes": 1,
        },
    )
    monkeypatch.setattr(
        admission,
        "gpu_metadata",
        lambda *args, **kwargs: {
            "uuid": admission.GPU_UUID,
            "cuda_initialized": False,
            "compute_processes": 0,
        },
    )
    receipt = admission.run_metadata_admission(
        candidate=item,
        resolved=resolved,
        authority=auth,
        attempt_root=Path(auth["remote_attempt_root"]),
    )
    assert receipt["terminal_state"] == admission.SUCCESS_STATE
    assert receipt["scientific_identities_verified_live"] is False
    assert receipt["execution_authorized"] is False
    assert receipt["producer_authorized"] is False
    assert receipt["archive"]["content_reopened_during_admission"] is False
    assert receipt["archive"]["bytes_read"] == admission.ARCHIVE_BYTES
    assert all(value == 0 for value in receipt["counters"].values())
    assert metadata_calls == [
        (item["remote"]["packet_dir"], "directory"),
        (item["remote"]["base_runtime_config"], "file"),
        (item["remote"]["checkpoint"], "file"),
    ]


def test_metadata_admission_rejects_authority_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item = candidate()
    auth = authority(tmp_path)
    monkeypatch.setattr(admission, "assert_no_scientific_modules", lambda: None)
    resolved = admission.resolve_admission_only(
        candidate=item,
        authority=auth,
        candidate_sha256=candidate_sha(),
        plan_sha256=item["plan_sha256"],
        package_config_sha256=admission.PACKAGE_SHA256,
        final_candidate_sha256=admission.FINAL_CANDIDATE_SHA256,
        archive_sha256=admission.ARCHIVE_SHA256,
        archive_verification=archive_verification(),
        observed_commit=admission.CONTROL_COMMIT,
    )
    swapped = dict(auth)
    swapped["granted_at"] = "2026-10-20T19:01:00+01:00"
    with pytest.raises(admission.AdmissionOnlyStop) as caught:
        admission.run_metadata_admission(
            candidate=item,
            resolved=resolved,
            authority=swapped,
            attempt_root=Path(swapped["remote_attempt_root"]),
        )
    assert caught.value.first_reason == "RESOLVED_CONTROL_INVALID"


def test_resolver_and_admission_consume_exactly_one_archive_read_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item = candidate()
    auth = authority(tmp_path, attempt="admission-only-single-archive-read")
    authority_path = Path(auth["local_evidence_root"]) / "authority.json"
    canonical_file(authority_path, auth)
    frozen_stat = archive_verification()["stat"]
    archive_path = Path(item["accepted_state"]["archive_path"])
    original_lstat = Path.lstat

    def controlled_lstat(path: Path):
        if path == archive_path:
            return SimpleNamespace(
                st_dev=frozen_stat["device"],
                st_ino=frozen_stat["inode"],
                st_mode=frozen_stat["mode"],
                st_mtime_ns=frozen_stat["mtime_ns"],
                st_size=frozen_stat["size_bytes"],
            )
        return original_lstat(path)

    archive_hash_calls: list[int] = []

    def counted_archive_hash(path: Path, *, expected_bytes: int | None = None):
        assert path == archive_path
        assert expected_bytes == admission.ARCHIVE_BYTES
        archive_hash_calls.append(expected_bytes)
        return admission.ARCHIVE_SHA256

    monkeypatch.setattr(Path, "lstat", controlled_lstat)
    monkeypatch.setattr(resolver, "sha256_path", counted_archive_hash)
    monkeypatch.setattr(
        resolver.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout=admission.CONTROL_COMMIT + "\n"),
    )
    monkeypatch.setattr(admission, "assert_no_scientific_modules", lambda: None)
    resolved, resolution = resolver.resolve_from_paths(
        candidate_path=CANDIDATE_PATH,
        candidate_sha256=candidate_sha(),
        final_candidate_path=(
            ROOT / "docs/research/S09/S09-E017/final_execution_candidate_20261020.json"
        ),
        package_config_path=(
            ROOT / "docs/research/S09/S09-E017/final_run_package_config_20261019.json"
        ),
        authority_path=authority_path,
        code_archive=archive_path,
        code_root=tmp_path,
    )
    assert archive_hash_calls == [admission.ARCHIVE_BYTES]
    assert resolution["archive_bytes_read"] == admission.ARCHIVE_BYTES

    monkeypatch.setattr(admission.platform, "system", lambda: "Linux")
    monkeypatch.setattr(admission.socket, "gethostname", lambda: admission.HOSTNAME)
    monkeypatch.setattr(admission.os, "getuid", lambda: admission.REMOTE_UID)
    monkeypatch.setattr(admission.getpass, "getuser", lambda: admission.REMOTE_USER)
    monkeypatch.setattr(
        Path, "cwd", classmethod(lambda cls: Path(item["remote"]["code_root"]))
    )
    monkeypatch.setattr(
        admission,
        "git_identity",
        lambda *args, **kwargs: {"head": admission.CONTROL_COMMIT, "dirty": False},
    )
    monkeypatch.setattr(Path, "exists", lambda self: False)
    monkeypatch.setattr(Path, "is_dir", lambda self: True)
    monkeypatch.setattr(Path, "is_symlink", lambda self: False)
    monkeypatch.setattr(
        admission,
        "path_metadata",
        lambda path, *, kind: {
            "path": str(path),
            "kind": kind,
            "size_bytes": 1,
            "mode": 0,
            "content_opened": False,
        },
    )
    monkeypatch.setattr(
        admission,
        "host_resource_snapshot",
        lambda *args, **kwargs: {
            "host_max_rss_bytes": 1,
            "free_disk_bytes": 30 * 1024**3,
            "admission_only_control_tree_bytes": 1,
        },
    )
    monkeypatch.setattr(
        admission,
        "gpu_metadata",
        lambda *args, **kwargs: {
            "uuid": admission.GPU_UUID,
            "cuda_initialized": False,
            "compute_processes": 0,
        },
    )
    receipt = admission.run_metadata_admission(
        candidate=item,
        resolved=resolved,
        authority=auth,
        attempt_root=Path(auth["remote_attempt_root"]),
    )
    assert receipt["terminal_state"] == admission.SUCCESS_STATE
    assert archive_hash_calls == [admission.ARCHIVE_BYTES]
    assert receipt["archive"]["bytes_read"] == admission.ARCHIVE_BYTES


def test_path_metadata_does_not_open_scientific_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scientific = tmp_path / "checkpoint.pt"
    scientific.write_bytes(b"not opened")
    original_open = Path.open

    def reject_open(self: Path, *args, **kwargs):
        if self == scientific:
            raise AssertionError("scientific content opened")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", reject_open)
    result = admission.path_metadata(scientific, kind="file")
    assert result["size_bytes"] == len(b"not opened")
    assert result["content_opened"] is False


def test_gpu_parser_requires_frozen_uuid_free_memory_and_no_process() -> None:
    identity = (
        "5, GPU-5622bd47-1050-3003-246d-3cabe2b4791b, "
        "NVIDIA GeForce RTX 4090, 24564, 4, 0"
    )
    result = admission.parse_gpu_rows(identity, "")
    assert result["uuid"] == admission.GPU_UUID
    assert result["compute_processes"] == 0
    with pytest.raises(admission.AdmissionOnlyStop):
        admission.parse_gpu_rows(identity, f"123, {admission.GPU_UUID}, 10")
    with pytest.raises(admission.AdmissionOnlyStop):
        admission.parse_gpu_rows(identity.replace(admission.GPU_UUID, "GPU-wrong"), "")


def test_attempt_token_is_exclusive(tmp_path: Path) -> None:
    auth = authority(tmp_path)
    remote = tmp_path / "remote" / auth["admission_only_attempt_id"]
    auth["remote_attempt_root"] = str(remote)
    first = admission.begin_attempt(remote, auth)
    assert first.name == "attempt.json"
    with pytest.raises(FileExistsError):
        admission.begin_attempt(remote, auth)


class FakeProcess:
    def __init__(self, returncode: int, stdout: str = "ok", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.pid = 4242

    def communicate(self, timeout: int | None = None):
        return self.stdout, self.stderr


def test_outer_guard_consumes_once_and_preserves_success_receipts(
    tmp_path: Path
) -> None:
    auth = authority(tmp_path)
    authority_path = Path(auth["local_evidence_root"]) / "admission_only_authority.json"
    canonical_file(authority_path, auth)
    receipt = guard.run_guarded_plan(
        candidate_path=CANDIDATE_PATH,
        candidate_sha256=candidate_sha(),
        authority_path=authority_path,
        plan_path=PLAN_PATH,
        plan_sha256=candidate()["plan_sha256"],
        execute_authorised_admission_only=True,
        popen=lambda *args, **kwargs: FakeProcess(0),
        monotonic=iter((1.0, 2.5)).__next__,
    )
    root = Path(auth["local_evidence_root"])
    assert receipt["terminal_state"] == "ADMISSION_ONLY_PLAN_COMPLETED"
    assert (root / "authority_consumption_receipt.json").is_file()
    assert (root / "guard_receipt.json").is_file()
    assert (root / "stdout.log").read_text() == "ok"
    with pytest.raises(admission.AdmissionOnlyStop) as caught:
        guard.run_guarded_plan(
            candidate_path=CANDIDATE_PATH,
            candidate_sha256=candidate_sha(),
            authority_path=authority_path,
            plan_path=PLAN_PATH,
            plan_sha256=candidate()["plan_sha256"],
            execute_authorised_admission_only=True,
            popen=lambda *args, **kwargs: FakeProcess(0),
        )
    assert caught.value.first_reason == "LOCAL_RECEIPT_PATH_CONFLICT"


def test_outer_guard_nonzero_is_terminal_no_retry(tmp_path: Path) -> None:
    auth = authority(tmp_path, attempt="admission-only-failure")
    authority_path = Path(auth["local_evidence_root"]) / "admission_only_authority.json"
    canonical_file(authority_path, auth)
    receipt = guard.run_guarded_plan(
        candidate_path=CANDIDATE_PATH,
        candidate_sha256=candidate_sha(),
        authority_path=authority_path,
        plan_path=PLAN_PATH,
        plan_sha256=candidate()["plan_sha256"],
        execute_authorised_admission_only=True,
        popen=lambda *args, **kwargs: FakeProcess(17, stderr="first stop"),
        monotonic=iter((1.0, 3.0)).__next__,
    )
    assert receipt["terminal_state"] == "ADMISSION_ONLY_GUARD_STOPPED"
    assert receipt["first_reason"] == "ADMISSION_ONLY_PLAN_EXIT_NONZERO"
    assert receipt["retry"] is False
    assert receipt["reconnect"] is False


def test_outer_guard_spawn_failure_still_writes_terminal_receipt(
    tmp_path: Path,
) -> None:
    auth = authority(tmp_path, attempt="admission-only-spawn-error")
    root = Path(auth["local_evidence_root"])
    authority_path = root / "admission_only_authority.json"
    canonical_file(authority_path, auth)

    def fail_spawn(*args, **kwargs):
        raise OSError("synthetic spawn failure")

    receipt = guard.run_guarded_plan(
        candidate_path=CANDIDATE_PATH,
        candidate_sha256=candidate_sha(),
        authority_path=authority_path,
        plan_path=PLAN_PATH,
        plan_sha256=candidate()["plan_sha256"],
        execute_authorised_admission_only=True,
        popen=fail_spawn,
        monotonic=iter((1.0, 1.5)).__next__,
    )
    assert (root / "authority_consumption_receipt.json").is_file()
    assert (root / "guard_receipt.json").is_file()
    assert receipt["terminal_state"] == "ADMISSION_ONLY_GUARD_STOPPED"
    assert receipt["first_reason"] == "ADMISSION_ONLY_PROCESS_START_FAILED"
    assert receipt["process_returncode"] is None
    assert receipt["retry"] is False
    assert receipt["reconnect"] is False


def test_outer_guard_log_failure_preserves_minimal_guard_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth = authority(tmp_path, attempt="admission-only-log-error")
    root = Path(auth["local_evidence_root"])
    authority_path = root / "admission_only_authority.json"
    canonical_file(authority_path, auth)
    real_publish = guard._publish

    def fail_stdout_only(path: Path, payload: bytes) -> None:
        if path.name == "stdout.log":
            raise OSError("synthetic stdout persistence failure")
        real_publish(path, payload)

    monkeypatch.setattr(guard, "_publish", fail_stdout_only)
    receipt = guard.run_guarded_plan(
        candidate_path=CANDIDATE_PATH,
        candidate_sha256=candidate_sha(),
        authority_path=authority_path,
        plan_path=PLAN_PATH,
        plan_sha256=candidate()["plan_sha256"],
        execute_authorised_admission_only=True,
        popen=lambda *args, **kwargs: FakeProcess(0),
        monotonic=iter((1.0, 1.5)).__next__,
    )
    assert (root / "guard_receipt.json").is_file()
    assert not (root / "stdout.log").exists()
    assert (root / "stderr.log").is_file()
    assert receipt["terminal_state"] == "ADMISSION_ONLY_GUARD_STOPPED"
    assert receipt["first_reason"] == "LOCAL_LOG_WRITE_FAILED"
    assert receipt["stdout_published"] is False
    assert receipt["stderr_published"] is True
    assert receipt["evidence_write_errors"][0]["artifact"] == "stdout"
    assert receipt["retry"] is False
    assert receipt["reconnect"] is False


def test_guard_requires_explicit_flag(tmp_path: Path) -> None:
    auth = authority(tmp_path)
    authority_path = Path(auth["local_evidence_root"]) / "admission_only_authority.json"
    canonical_file(authority_path, auth)
    with pytest.raises(admission.AdmissionOnlyStop) as caught:
        guard.run_guarded_plan(
            candidate_path=CANDIDATE_PATH,
            candidate_sha256=candidate_sha(),
            authority_path=authority_path,
            plan_path=PLAN_PATH,
            plan_sha256=candidate()["plan_sha256"],
            execute_authorised_admission_only=False,
        )
    assert caught.value.first_reason == "ADMISSION_ONLY_DISABLED"


def test_python_control_files_have_no_scientific_imports_or_producer_calls() -> None:
    paths = [
        ROOT / "source/s09_e017_admission_only.py",
        ROOT / "scripts/resolve_s09_e017_admission_only.py",
        ROOT / "scripts/run_s09_e017_admission_only.py",
        ROOT / "scripts/s09_e017_admission_only_guard.py",
    ]
    imported: set[str] = set()
    combined = ""
    for path in paths:
        text = path.read_text()
        combined += text
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
    assert "torch" not in imported
    assert "numpy" not in imported
    assert "run_reviewed_producer(" not in combined
    assert "resolve_real_bindings(" not in combined
    assert "COMPLETE_THREE_ARM_RUN" not in combined


def test_plan_has_one_connection_and_one_rsync_without_producer_entrypoint() -> None:
    text = PLAN_PATH.read_text()
    assert text.count("ssh -MNf") == 1
    assert text.count("rsync -aR") == 1
    assert "run_s09_e017_producer.py" not in text
    assert "--execute-reviewed-run" not in text
    assert 'CUDA_VISIBLE_DEVICES=""' in text
    assert "ulimit -t 60" in text
    assert "ulimit -v 1048576" in text
    assert text.count("bash -s -- \\\n") == 1


def test_remote_stdin_script_survives_ssh_command_concatenation(tmp_path: Path) -> None:
    text = PLAN_PATH.read_text()
    start_marker = "<<'REMOTE_ADMISSION_ONLY'\n"
    start = text.index(start_marker) + len(start_marker)
    end = text.index("\nREMOTE_ADMISSION_ONLY", start)
    remote_script = text[start:end].replace("ulimit -v 1048576", ":") + "\n"
    code_root = tmp_path / "code_root"
    code_root.mkdir()
    capture = tmp_path / "capture.json"
    runner = tmp_path / "runner.py"
    runner.write_text(
        "import json, os, pathlib, sys\n"
        "pathlib.Path(sys.argv[1]).write_text(json.dumps({\n"
        "  'argv': sys.argv[2:], 'cwd': os.getcwd(),\n"
        "  'pythonpath': os.environ['PYTHONPATH'],\n"
        "  'cuda': os.environ['CUDA_VISIBLE_DEVICES'],\n"
        "  'omp': os.environ['OMP_NUM_THREADS'],\n"
        "}))\n"
    )
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    timeout = fake_bin / "timeout"
    timeout.write_text('#!/bin/sh\nshift\nexec "$@"\n')
    timeout.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    remote_argv = [
        "bash",
        "-s",
        "--",
        str(code_root),
        "30",
        str(runner),
        "/helper/source:/helper/scripts",
        str(capture),
        "--value",
        "argument_with_underscores",
    ]
    assert all(not any(character.isspace() for character in arg) for arg in remote_argv)
    subprocess.run(
        ["/bin/sh", "-c", " ".join(remote_argv)],
        input=remote_script,
        text=True,
        check=True,
        env=env,
    )
    captured = json.loads(capture.read_text())
    assert captured == {
        "argv": ["--value", "argument_with_underscores"],
        "cwd": str(code_root),
        "pythonpath": "/helper/source:/helper/scripts",
        "cuda": "",
        "omp": "1",
    }
