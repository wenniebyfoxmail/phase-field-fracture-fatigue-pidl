"""No-science tests for the final S09-E017 execution control layer."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

import s09_e017_execution_control as control  # noqa: E402
from s09_code_identity import EXECUTION_FILES  # noqa: E402


CANDIDATE_PATH = (
    ROOT / "docs/research/S09/S09-E017/final_execution_candidate_20261020.json"
)
AUTHORITY_PATH = (
    ROOT / "docs/research/S09/S09-E017/execution_authority_template_20261020.json"
)
BASE_CONFIG_PATH = (
    ROOT / "docs/research/S09/S09-E017/final_run_package_config_20261019.json"
)
BASE_CONFIG_SHA = control.sha256_path(BASE_CONFIG_PATH)
RESOLVER_PATH = ROOT / "scripts/resolve_s09_e017_execution.py"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def approved_authority(candidate_sha: str, archive_sha: str, commit: str):
    authority = load(AUTHORITY_PATH)
    authority.update(
        {
            "approval_status": "APPROVED_FOR_ONE_ADMISSION_AND_COMPLETE_RUN",
            "execution_authorized": True,
            "reviewed_control_commit": commit,
            "candidate_config_sha256": candidate_sha,
            "code_archive_sha256": archive_sha,
            "allowed_actions": list(control.ALLOWED_ACTIONS),
            "maximum_launches": 1,
            "network_recovery_confirmed": True,
            "granted_by": "user",
            "granted_at": "2026-10-20T12:00:00+01:00",
        }
    )
    return authority


def test_candidate_and_disabled_authority_template_are_exact_and_nonexecuting():
    candidate = load(CANDIDATE_PATH)
    authority = load(AUTHORITY_PATH)
    control.validate_execution_candidate(candidate)
    control.validate_authority_template(authority, candidate)
    assert (
        candidate["source"]["reviewed_adapter_commit"]
        == control.ADAPTER_REVIEWED_COMMIT
    )
    assert candidate["execution_authorized"] is False
    assert authority["allowed_actions"] == []
    assert authority["maximum_launches"] == 0


def test_clean_tree_scope_contains_all_e017_execution_inputs():
    required = {
        "source/s09_e017_execution_control.py",
        "source/s09_e017_factorised_pilot.py",
        "source/s09_e017_producer_package.py",
        "source/s09_e017_real_adapter.py",
        "source/s09_e017_runner_contract.py",
        "scripts/resolve_s09_e017_execution.py",
        "scripts/run_s09_e017_producer.py",
        "docs/research/S09/S09-E017/final_run_package_config_20261019.json",
        "docs/research/S09/S09-E017/final_execution_candidate_20261020.json",
    }
    assert required.issubset(EXECUTION_FILES)


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda c: c.update(execution_authorized=True), "disabled"),
        (lambda c: c["science"].update(total_update_cap=193), "science contract"),
        (lambda c: c["resources"].update(host_rss_cap_bytes=0), "resource"),
        (lambda c: c["attempt"].update(retry=True), "attempt"),
        (
            lambda c: c["network_precondition"].update(s09_retry_authorized=True),
            "network precondition",
        ),
        (lambda c: c["admission"].update(ordered_checks=[]), "admission contract"),
        (
            lambda c: c["receipts"].update(required_first_stop_fields=[]),
            "receipt contract",
        ),
        (
            lambda c: c["network_precondition"].update(
                known_local_observation="changed"
            ),
            "network precondition",
        ),
        (lambda c: c["launch"].update(extra=True), "launch contract"),
    ],
)
def test_candidate_rejects_scope_budget_resource_or_network_drift(mutation, match):
    candidate = load(CANDIDATE_PATH)
    mutation(candidate)
    with pytest.raises((ValueError, PermissionError), match=match):
        control.validate_execution_candidate(candidate)


def test_not_granted_authority_cannot_resolve_runtime_config(tmp_path):
    candidate_bytes = CANDIDATE_PATH.read_bytes()
    candidate = load(CANDIDATE_PATH)
    authority = load(AUTHORITY_PATH)
    archive = tmp_path / "code.tar.gz"
    archive.write_bytes(b"synthetic archive fixture")
    with pytest.raises(PermissionError, match="not granted"):
        control.resolve_runtime_config(
            load(BASE_CONFIG_PATH),
            candidate,
            authority,
            observed_commit="a" * 40,
            base_package_config_sha256=BASE_CONFIG_SHA,
            candidate_sha256=control.sha256_bytes(candidate_bytes),
            code_archive_sha256=control.sha256_path(archive),
        )


def test_approved_authority_resolves_only_exact_candidate_archive_and_commit(tmp_path):
    candidate_bytes = CANDIDATE_PATH.read_bytes()
    candidate = load(CANDIDATE_PATH)
    archive = tmp_path / "code.tar.gz"
    archive.write_bytes(b"synthetic archive fixture")
    candidate_sha = control.sha256_bytes(candidate_bytes)
    archive_sha = control.sha256_path(archive)
    commit = "a" * 40
    authority = approved_authority(candidate_sha, archive_sha, commit)
    resolved = control.resolve_runtime_config(
        load(BASE_CONFIG_PATH),
        candidate,
        authority,
        observed_commit=commit,
        base_package_config_sha256=BASE_CONFIG_SHA,
        candidate_sha256=candidate_sha,
        code_archive_sha256=archive_sha,
    )
    assert resolved["execution_authorized"] is True
    assert resolved["source"]["producer_package_reviewed_commit"] == commit
    assert resolved["_execution_control"]["reviewed_adapter_commit"] == (
        control.ADAPTER_REVIEWED_COMMIT
    )
    control.validate_runtime_control(
        resolved,
        load(BASE_CONFIG_PATH),
        candidate,
        authority,
        observed_commit=commit,
        base_package_config_sha256=BASE_CONFIG_SHA,
        candidate_sha256=candidate_sha,
        code_archive_sha256=archive_sha,
    )
    drifted = copy.deepcopy(authority)
    drifted["code_archive_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="archive hash"):
        control.validate_runtime_control(
            resolved,
            load(BASE_CONFIG_PATH),
            candidate,
            drifted,
            observed_commit=commit,
            base_package_config_sha256=BASE_CONFIG_SHA,
            candidate_sha256=candidate_sha,
            code_archive_sha256=archive_sha,
        )


def test_runtime_control_rejects_drift_from_frozen_base(tmp_path):
    candidate_bytes = CANDIDATE_PATH.read_bytes()
    candidate = load(CANDIDATE_PATH)
    archive = tmp_path / "code.tar.gz"
    archive.write_bytes(b"synthetic archive fixture")
    candidate_sha = control.sha256_bytes(candidate_bytes)
    archive_sha = control.sha256_path(archive)
    commit = "a" * 40
    authority = approved_authority(candidate_sha, archive_sha, commit)
    base = load(BASE_CONFIG_PATH)
    resolved = control.resolve_runtime_config(
        base,
        candidate,
        authority,
        observed_commit=commit,
        base_package_config_sha256=BASE_CONFIG_SHA,
        candidate_sha256=candidate_sha,
        code_archive_sha256=archive_sha,
    )
    resolved["producer"]["wall_time_cap_seconds"] = 999999
    with pytest.raises(ValueError, match="resolved runtime config drift"):
        control.validate_runtime_control(
            resolved,
            base,
            candidate,
            authority,
            observed_commit=commit,
            base_package_config_sha256=BASE_CONFIG_SHA,
            candidate_sha256=candidate_sha,
            code_archive_sha256=archive_sha,
        )
    drifted_base = copy.deepcopy(base)
    drifted_base["physics"]["beta"] = 1.0
    with pytest.raises(ValueError, match="base package config content drift"):
        control.validate_runtime_control(
            control.resolve_runtime_config(
                base,
                candidate,
                authority,
                observed_commit=commit,
                base_package_config_sha256=BASE_CONFIG_SHA,
                candidate_sha256=candidate_sha,
                code_archive_sha256=archive_sha,
            ),
            drifted_base,
            candidate,
            authority,
            observed_commit=commit,
            base_package_config_sha256=BASE_CONFIG_SHA,
            candidate_sha256=candidate_sha,
            code_archive_sha256=archive_sha,
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("retry", True),
        ("alternate_host", True),
        ("alternate_gpu", True),
        ("network_recovery_confirmed", True),
        ("granted_by", "user"),
        ("granted_at", "2026-10-20T12:00:00+01:00"),
    ],
)
def test_disabled_authority_template_rejects_every_control_drift(field, value):
    candidate = load(CANDIDATE_PATH)
    authority = load(AUTHORITY_PATH)
    authority[field] = value
    with pytest.raises(ValueError, match="authority template drift"):
        control.validate_authority_template(authority, candidate)


def test_admission_attempt_is_exclusive_and_failure_receipt_is_independent(
    tmp_path, monkeypatch
):
    control_root = tmp_path / "control"
    control_root.mkdir()
    monkeypatch.setattr(control, "CONTROL_ROOT", control_root)
    attempt = control.begin_admission_attempt(control_root)
    assert json.loads(attempt.read_text())["maximum_launches"] == 1
    with pytest.raises(FileExistsError):
        control.begin_admission_attempt(control_root)
    missing = tmp_path / "missing.json"
    error = FileNotFoundError(2, "missing", str(missing))
    receipt_path = control.write_admission_failure_receipt(
        control_root,
        error=error,
        config=None,
        output_dir=None,
    )
    receipt = json.loads(receipt_path.read_text())
    assert receipt["terminal_state"] == "ADMISSION_STOPPED"
    assert receipt["missing_or_unreadable"] == [str(missing)]
    assert receipt["resource_snapshot"] is None
    assert receipt["retry"] is False
    second_root = tmp_path / "second-control"
    second_root.mkdir()
    (second_root / "admission_failure_receipt.json").write_text("{}\n")
    monkeypatch.setattr(control, "CONTROL_ROOT", second_root)
    with pytest.raises(FileExistsError, match="prior admission receipt"):
        control.begin_admission_attempt(second_root)


def test_resource_guard_enforces_rss_disk_output_temp_and_environment(
    tmp_path, monkeypatch
):
    output = tmp_path / "run"
    temp = tmp_path / "tmp"
    cache = tmp_path / "cache"
    temp.mkdir()
    cache.mkdir()
    monkeypatch.setenv("TMPDIR", str(temp))
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    candidate = load(CANDIDATE_PATH)
    runtime_control = {
        "paths": {
            **candidate["paths"],
            "temp_root": str(temp),
            "cache_root": str(cache),
        },
        "resources": dict(candidate["resources"]),
    }
    config = {"_execution_control": runtime_control}
    observed = control.runtime_resource_guard(config, output)
    assert observed["output_tree_bytes"] == 0
    assert observed["temp_tree_bytes"] == 0
    (temp / "too-large").write_bytes(b"12")
    runtime_control["resources"]["temp_tree_cap_bytes"] = 1
    with pytest.raises(ValueError, match="temporary tree cap"):
        control.runtime_resource_guard(config, output)


def test_resolver_with_tracked_template_refuses_without_outputs(tmp_path):
    archive = tmp_path / "code.tar.gz"
    archive.write_bytes(b"synthetic archive fixture")
    output = tmp_path / "resolved.json"
    receipt = tmp_path / "receipt.json"
    result = subprocess.run(
        [
            sys.executable,
            str(RESOLVER_PATH),
            "--base-package-config",
            str(BASE_CONFIG_PATH),
            "--execution-candidate",
            str(CANDIDATE_PATH),
            "--execution-authority",
            str(AUTHORITY_PATH),
            "--code-archive",
            str(archive),
            "--output-config",
            str(output),
            "--output-receipt",
            str(receipt),
            "--resolve-authorised-config",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "execution authority is not granted" in result.stderr
    assert not output.exists() and not receipt.exists()


def test_execution_control_is_stdlib_only_and_import_has_no_side_effects():
    before = set(sys.modules)
    source = (ROOT / "source/s09_e017_execution_control.py").read_text()
    assert "import torch" not in source and "import numpy" not in source
    assert set(sys.modules) == before
    assert os.environ.get("CUDA_VISIBLE_DEVICES") is None or isinstance(
        os.environ["CUDA_VISIBLE_DEVICES"], str
    )
