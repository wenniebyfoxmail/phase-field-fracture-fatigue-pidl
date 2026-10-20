"""Standard-library execution control for the final S09-E017 candidate.

This module does not import scientific dependencies or read packet/checkpoint
contents.  It validates the frozen local candidate, a later one-run authority
receipt, the exact code archive and non-scientific admission/resource state.
"""
from __future__ import annotations

import copy
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import socket
from typing import Any, Mapping


CANDIDATE_SCHEMA = "s09-e017-final-execution-candidate-v1"
AUTHORITY_SCHEMA = "s09-e017-one-run-authority-v1"
RUNTIME_CONTROL_SCHEMA = "s09-e017-runtime-control-v1"
RUN_ID = "S09-E017-R001-factorised-head-p0"
ADAPTER_REVIEWED_COMMIT = "662005f1fde22cb9a6e8069f4e430b7190f21860"
CORE_REVIEWED_COMMIT = "5ac6b7955b56309ac8ff2fda50b16b2e1669110a"
DESIGN_REVIEWED_COMMIT = "06bf5fef693be5321ce7daf9d2384b8fa3953fde"
INTEGRATION_REVIEWED_COMMIT = "3a5a2020c7b16555e9ecd9ec19377bf87a52d5c5"
ARMS = ("D_DIRECT", "F_AMP", "F_AMP_SHAPE")
CYCLES = (1, 2, 3, 4, 21, 29, 41, 46, 48, 58, 60, 69, 70, 71, 72, 73)
ALLOWED_ACTIONS = ("LIVE_ADMISSION", "COMPLETE_THREE_ARM_RUN")


def _require(
    condition: bool, message: str, error: type[Exception] = ValueError
) -> None:
    if not condition:
        raise error(message)


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: Any, name: str) -> str:
    _require(isinstance(value, str) and len(value) == 64, f"{name} must be SHA256")
    _require(
        all(character in "0123456789abcdef" for character in value),
        f"{name} must be lowercase SHA256",
    )
    return value


def _strict_int(value: Any, name: str, *, minimum: int = 0) -> int:
    _require(
        isinstance(value, int) and not isinstance(value, bool) and value >= minimum,
        f"{name} must be an integer >= {minimum}",
    )
    return value


def validate_execution_candidate(candidate: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "status",
        "execution_authorized",
        "run_id",
        "source",
        "science",
        "paths",
        "resources",
        "attempt",
        "network_precondition",
        "launch",
        "authority",
        "admission",
        "receipts",
    }
    _require(set(candidate) == required, "execution candidate keys drift")
    _require(candidate["schema_version"] == CANDIDATE_SCHEMA, "candidate schema drift")
    _require(
        candidate["status"] == "FINAL_EXECUTION_CANDIDATE__NO_EXECUTION",
        "candidate status drift",
    )
    _require(
        candidate["execution_authorized"] is False,
        "tracked candidate must remain disabled",
        PermissionError,
    )
    _require(candidate["run_id"] == RUN_ID, "run id drift")

    source = candidate["source"]
    _require(
        source
        == {
            "reviewed_core_commit": CORE_REVIEWED_COMMIT,
            "reviewed_design_commit": DESIGN_REVIEWED_COMMIT,
            "reviewed_integration_commit": INTEGRATION_REVIEWED_COMMIT,
            "reviewed_adapter_commit": ADAPTER_REVIEWED_COMMIT,
            "control_review_binding": (
                "EXECUTION_AUTHORITY_MUST_MATCH_FOCUSED_REVIEWED_HEAD"
            ),
        },
        "reviewed source identities drift",
    )
    science = candidate["science"]
    _require(tuple(science["arms"]) == ARMS, "arm order drift")
    _require(tuple(science["cycles"]) == CYCLES, "cycle order drift")
    _require(
        science["updates_per_arm"] == 64
        and science["total_update_cap"] == 192,
        "update budget drift",
    )
    _require(
        science["beta"] == 0.25
        and science["fresh_holdout"] is False
        and science["autoregressive"] is False,
        "science boundary drift",
    )
    _require(science["shape_seed_epsilon"] == 1e-6, "shape seed drift")
    _require(
        science["parameter_counts"]
        == {"D_DIRECT": "width+1", "F_AMP": "width+1", "F_AMP_SHAPE": "2*width+1"},
        "parameter count contract drift",
    )

    paths = candidate["paths"]
    task_root = Path("/mnt/data2/drtao/wennie") / RUN_ID
    _require(Path(paths["code_root"]) == task_root / "code", "code root drift")
    _require(Path(paths["output_root"]) == task_root / "run", "output root drift")
    _require(Path(paths["control_root"]) == task_root / "control", "control root drift")
    _require(Path(paths["temp_root"]) == task_root / "tmp", "temp root drift")
    _require(Path(paths["cache_root"]) == task_root / "cache", "cache root drift")
    _require(
        Path(paths["archive_root"])
        == Path("/mnt/data2/drtao/pidl_archives") / RUN_ID,
        "archive root drift",
    )
    _require(
        paths["packet_dir"]
        == "/mnt/data2/drtao/wennie/S09-E008-P1-STAGING-20261016/packet",
        "packet path drift",
    )
    _require(
        paths["initial_checkpoint"]
        == (
            "/mnt/data2/drtao/wennie/"
            "S09-E010-R001-support-amplitude-three-arm/"
            "B25_support_amplitude_beta0p25/checkpoint_update500.pt"
        ),
        "checkpoint path drift",
    )
    _require(
        Path(paths["base_runtime_config"])
        == task_root
        / "code/docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json",
        "base config path drift",
    )
    _require(
        Path(paths["code_archive"]) == task_root / "control/code.tar.gz",
        "code archive path drift",
    )

    resources = candidate["resources"]
    _require(
        resources
        == {
            "wall_time_cap_seconds": 1800,
            "reserved_memory_cap_bytes": 20 * 1024**3,
            "host_rss_cap_bytes": 16 * 1024**3,
            "minimum_free_disk_bytes": 20 * 1024**3,
            "output_tree_cap_bytes": 10 * 1024**3,
            "temp_tree_cap_bytes": 4 * 1024**3,
            "code_archive_cap_bytes": 100 * 1024**2,
        },
        "resource budget drift",
    )
    _require(
        candidate["attempt"]
        == {
            "maximum_launches": 1,
            "retry": False,
            "resume": False,
            "alternate_host": False,
            "alternate_gpu": False,
            "budget_transfer": False,
        },
        "attempt policy drift",
    )
    network = candidate["network_precondition"]
    _require(
        network["current_state"] == "BLOCKED_NO_REMOTE_SHELL",
        "network state drift",
    )
    _require(network["last_ssh_exit_code"] == 255, "network receipt drift")
    _require(network["remote_shell_obtained"] is False, "remote shell drift")
    _require(network["s09_retry_authorized"] is False, "network retry drift")
    _require(
        network["required_before_authority"]
        == "EXTERNAL_CONFIRMATION_THAT_CONNECTION_CONDITION_RECOVERED",
        "network recovery condition drift",
    )
    launch = candidate["launch"]
    _require(
        launch["entrypoint"] == "scripts/run_s09_e017_producer.py",
        "entrypoint drift",
    )
    _require(launch["cuda_visible_devices"] == "5", "visible GPU drift")
    _require(launch["hostname"] == "GPUServer8", "hostname drift")
    _require(
        launch["gpu_uuid"] == "GPU-5622bd47-1050-3003-246d-3cabe2b4791b",
        "GPU identity drift",
    )
    _require(
        launch["required_environment"]
        == {"TMPDIR": paths["temp_root"], "XDG_CACHE_HOME": paths["cache_root"]},
        "runtime environment drift",
    )
    _require(
        candidate["authority"]
        == {
            "schema_version": AUTHORITY_SCHEMA,
            "template_status": "NOT_GRANTED",
            "template_path": (
                "docs/research/S09/S09-E017/"
                "execution_authority_template_20261020.json"
            ),
        },
        "authority template binding drift",
    )
    _require(
        candidate["admission"]["first_stop_scope"] == "WHOLE_RUN_NO_RETRY",
        "admission stop scope drift",
    )
    _require(
        candidate["receipts"]["terminal_states"]
        == ["ADMISSION_STOPPED", "EXECUTION_FAILED", "COMPLETED"],
        "terminal receipt states drift",
    )


def validate_authority_template(
    authority: Mapping[str, Any], candidate: Mapping[str, Any]
) -> None:
    validate_execution_candidate(candidate)
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
    _require(set(authority) == required, "authority template keys drift")
    _require(authority["schema_version"] == AUTHORITY_SCHEMA, "authority schema drift")
    _require(authority["approval_status"] == "NOT_GRANTED", "template is not disabled")
    _require(authority["execution_authorized"] is False, "template grants authority")
    _require(authority["run_id"] == RUN_ID, "authority run id drift")
    _require(
        authority["reviewed_adapter_commit"] == ADAPTER_REVIEWED_COMMIT,
        "authority adapter drift",
    )
    _require(
        authority["reviewed_control_commit"] == "TO_BE_BOUND_AFTER_FOCUSED_REVIEW",
        "template control binding drift",
    )
    _require(
        authority["candidate_config_sha256"] == "TO_BE_BOUND_AFTER_CANDIDATE_FREEZE"
        and authority["code_archive_sha256"] == "TO_BE_BOUND_AFTER_FOCUSED_REVIEW",
        "template package binding drift",
    )
    _require(authority["allowed_actions"] == [], "template contains allowed actions")
    _require(authority["maximum_launches"] == 0, "template contains launch authority")


def validate_execution_authority(
    authority: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    observed_commit: str,
    candidate_sha256: str,
    code_archive_sha256: str,
) -> None:
    validate_execution_candidate(candidate)
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
    _require(set(authority) == required, "execution authority keys drift")
    _require(authority["schema_version"] == AUTHORITY_SCHEMA, "authority schema drift")
    _require(
        authority["approval_status"] == "APPROVED_FOR_ONE_ADMISSION_AND_COMPLETE_RUN",
        "execution authority is not granted",
        PermissionError,
    )
    _require(
        authority["execution_authorized"] is True,
        "authority is disabled",
        PermissionError,
    )
    _require(authority["run_id"] == RUN_ID, "authority run id drift")
    _require(
        authority["reviewed_adapter_commit"] == ADAPTER_REVIEWED_COMMIT,
        "authority adapter drift",
    )
    _require(
        authority["reviewed_control_commit"] == observed_commit,
        "authority control commit differs from checkout",
    )
    _require(
        _digest(authority["candidate_config_sha256"], "candidate config")
        == candidate_sha256,
        "authority candidate hash drift",
    )
    _require(
        _digest(authority["code_archive_sha256"], "code archive")
        == code_archive_sha256,
        "authority archive hash drift",
    )
    _require(
        tuple(authority["allowed_actions"]) == ALLOWED_ACTIONS,
        "authority action drift",
    )
    _require(authority["maximum_launches"] == 1, "authority launch count drift")
    _require(authority["retry"] is False, "authority permits retry")
    _require(authority["alternate_host"] is False, "authority permits alternate host")
    _require(authority["alternate_gpu"] is False, "authority permits alternate GPU")
    _require(
        authority["network_recovery_confirmed"] is True,
        "network recovery has not been confirmed",
        PermissionError,
    )
    _require(authority["granted_by"] == "user", "authority grantor drift")
    _require(
        isinstance(authority["granted_at"], str) and authority["granted_at"],
        "grant time missing",
    )
    try:
        granted_at = datetime.fromisoformat(authority["granted_at"])
    except ValueError as error:
        raise ValueError("grant time is not ISO-8601") from error
    _require(granted_at.tzinfo is not None, "grant time must include timezone")


def resolve_runtime_config(
    base_config: Mapping[str, Any],
    candidate: Mapping[str, Any],
    authority: Mapping[str, Any],
    *,
    observed_commit: str,
    candidate_sha256: str,
    code_archive_sha256: str,
) -> dict[str, Any]:
    validate_execution_authority(
        authority,
        candidate,
        observed_commit=observed_commit,
        candidate_sha256=candidate_sha256,
        code_archive_sha256=code_archive_sha256,
    )
    resolved = copy.deepcopy(dict(base_config))
    resolved["status"] = "RESOLVED_FOR_AUTHORISED_EXECUTION"
    resolved["execution_authorized"] = True
    resolved["source"]["producer_package_reviewed_commit"] = observed_commit
    resolved["launch"]["wrapper_enabled"] = True
    resolved["_execution_control"] = {
        "schema_version": RUNTIME_CONTROL_SCHEMA,
        "candidate_config_sha256": candidate_sha256,
        "authority_sha256": sha256_bytes(canonical_json(authority)),
        "code_archive_sha256": code_archive_sha256,
        "reviewed_control_commit": observed_commit,
        "reviewed_adapter_commit": ADAPTER_REVIEWED_COMMIT,
        "allowed_actions": list(ALLOWED_ACTIONS),
        "paths": dict(candidate["paths"]),
        "resources": dict(candidate["resources"]),
        "attempt": dict(candidate["attempt"]),
    }
    return resolved


def validate_runtime_control(
    resolved: Mapping[str, Any],
    candidate: Mapping[str, Any],
    authority: Mapping[str, Any],
    *,
    observed_commit: str,
    candidate_sha256: str,
    code_archive_sha256: str,
) -> None:
    validate_execution_authority(
        authority,
        candidate,
        observed_commit=observed_commit,
        candidate_sha256=candidate_sha256,
        code_archive_sha256=code_archive_sha256,
    )
    expected = resolve_runtime_config(
        {key: value for key, value in resolved.items() if key != "_execution_control"},
        candidate,
        authority,
        observed_commit=observed_commit,
        candidate_sha256=candidate_sha256,
        code_archive_sha256=code_archive_sha256,
    )
    _require(resolved == expected, "resolved runtime config drift")


def tree_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for root, _directories, files in os.walk(path):
        for name in files:
            item = Path(root) / name
            try:
                total += item.stat().st_size
            except FileNotFoundError:
                continue
    return total


def process_identity() -> dict[str, Any]:
    cmdline_path = Path("/proc/self/cmdline")
    cmdline = ""
    if cmdline_path.is_file():
        cmdline = cmdline_path.read_bytes().replace(b"\0", b" ").decode(
            "utf-8", errors="replace"
        ).strip()
    return {
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "uid": os.getuid(),
        "cwd": str(Path.cwd()),
        "cmdline": cmdline,
    }


def resource_snapshot(control: Mapping[str, Any], output_dir: Path) -> dict[str, int]:
    paths = control["paths"]
    ru_maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_bytes = (
        int(ru_maxrss * 1024) if platform.system() == "Linux" else int(ru_maxrss)
    )
    return {
        "host_max_rss_bytes": rss_bytes,
        "free_disk_bytes": shutil.disk_usage(output_dir.parent).free,
        "output_tree_bytes": tree_size(output_dir),
        "temp_tree_bytes": tree_size(Path(paths["temp_root"])),
    }


def runtime_resource_guard(
    config: Mapping[str, Any], output_dir: Path
) -> dict[str, int]:
    control = config.get("_execution_control")
    _require(isinstance(control, Mapping), "runtime control missing", PermissionError)
    resources = control["resources"]
    paths = control["paths"]
    _require(os.environ.get("TMPDIR") == paths["temp_root"], "TMPDIR drift")
    _require(
        os.environ.get("XDG_CACHE_HOME") == paths["cache_root"],
        "XDG_CACHE_HOME drift",
    )
    observed = resource_snapshot(control, output_dir)
    _require(
        observed["host_max_rss_bytes"] <= resources["host_rss_cap_bytes"],
        "host RSS cap exceeded",
    )
    _require(
        observed["free_disk_bytes"] >= resources["minimum_free_disk_bytes"],
        "free disk floor crossed",
    )
    _require(
        observed["output_tree_bytes"] <= resources["output_tree_cap_bytes"],
        "output tree cap exceeded",
    )
    _require(
        observed["temp_tree_bytes"] <= resources["temp_tree_cap_bytes"],
        "temporary tree cap exceeded",
    )
    return observed


def control_admission(
    candidate: Mapping[str, Any],
    resolved: Mapping[str, Any],
    *,
    code_archive: Path,
) -> dict[str, Any]:
    validate_execution_candidate(candidate)
    paths = candidate["paths"]
    resources = candidate["resources"]
    _require(platform.system() == "Linux", "producer must be Linux")
    _require(socket.gethostname() == candidate["launch"]["hostname"], "hostname drift")
    _require(Path.cwd() == Path(paths["code_root"]), "producer cwd drift")
    _require(code_archive == Path(paths["code_archive"]), "archive path drift")
    _require(code_archive.is_file(), "code archive missing")
    _require(
        code_archive.stat().st_size <= resources["code_archive_cap_bytes"],
        "code archive cap exceeded",
    )
    for name in ("output_root", "archive_root"):
        _require(not Path(paths[name]).exists(), f"{name} is not fresh")
    for name in ("control_root", "temp_root", "cache_root"):
        _require(Path(paths[name]).is_dir(), f"{name} missing")
    observed = runtime_resource_guard(resolved, Path(paths["output_root"]))
    return {
        "terminal_state": "ADMISSION_READY",
        "run_id": RUN_ID,
        "process_identity": process_identity(),
        "resource_snapshot": observed,
        "scientific_assets_read": False,
        "binding_resolutions": 0,
        "model_forwards": 0,
        "autograd_collections": 0,
        "optimizer_steps": 0,
    }
