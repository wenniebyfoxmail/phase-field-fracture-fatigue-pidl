"""Standard-library-only controls for the S09-E017 admission-only gate.

This module deliberately has no scientific import or execution path.  It may
read control JSON, Git metadata, the frozen code archive, filesystem metadata
and nvidia-smi metadata.  Packet/checkpoint contents, CUDA, runtime/model
construction and producer bindings are outside its authority.
"""
from __future__ import annotations

from datetime import datetime
import getpass
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import socket
import subprocess
import sys
from typing import Any, Callable, Mapping, Sequence


RUN_ID = "S09-E017-R001-factorised-head-p0"
CANDIDATE_SCHEMA = "s09-e017-admission-only-candidate-v1"
AUTHORITY_SCHEMA = "s09-e017-resolver-admission-only-authority-v1"
RESOLVED_SCHEMA = "s09-e017-admission-only-resolved-v1"
ATTEMPT_SCHEMA = "s09-e017-admission-only-attempt-v1"
RECEIPT_SCHEMA = "s09-e017-admission-only-receipt-v1"
FAILURE_SCHEMA = "s09-e017-admission-only-first-stop-v1"
GUARD_ACTIONS = (
    "STAGE_REVIEWED_ADMISSION_ONLY_HELPER",
    "RESOLVE_ADMISSION_ONLY_CONTROL",
    "RUN_METADATA_ADMISSION_ONLY",
)
SUCCESS_STATE = "ADMISSION_ONLY_METADATA_READY__SCIENTIFIC_IDENTITIES_UNVERIFIED"
CONTROL_COMMIT = "2002538d9a30c8d4006ccaff5959cd214958fc82"
FINAL_CANDIDATE_SHA256 = (
    "4c1e928274f6fbee134ff540345844260cf16675727d0e996abb0054062ddcf1"
)
PACKAGE_SHA256 = "46c0cc6b9c5dcc62794845a20502a2eaa98c7ce7dd05b423a6b00a3d1784a2e6"
ARCHIVE_SHA256 = "4ece34be786fc85bb9655c076c13c45d276d08dfde405a8fb1367e4b49ffdd22"
ARCHIVE_BYTES = 14_359_316
HOSTNAME = "GPUServer8"
REMOTE_USER = "drtao"
REMOTE_UID = 1010
GPU_INDEX = 5
GPU_UUID = "GPU-5622bd47-1050-3003-246d-3cabe2b4791b"
BANNED_MODULE_PREFIXES = (
    "torch",
    "numpy",
    "s09_e017_real_adapter",
    "s09_stage0a_p1_packet",
    "s09_stage0a_p1_trainer",
)


class AdmissionOnlyStop(RuntimeError):
    """A fail-closed admission-only first stop."""

    def __init__(self, first_reason: str, message: str) -> None:
        super().__init__(message)
        self.first_reason = first_reason


def _require(condition: bool, reason: str, message: str) -> None:
    if not condition:
        raise AdmissionOnlyStop(reason, message)


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path, *, expected_bytes: int | None = None) -> str:
    if not path.is_file() or path.is_symlink():
        raise AdmissionOnlyStop("FILE_IDENTITY_INVALID", f"invalid file: {path}")
    if expected_bytes is not None and path.stat().st_size != expected_bytes:
        raise AdmissionOnlyStop("FILE_IDENTITY_INVALID", f"size mismatch: {path}")
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            count += len(block)
    if expected_bytes is not None and count != expected_bytes:
        raise AdmissionOnlyStop("FILE_IDENTITY_INVALID", f"read size mismatch: {path}")
    return digest.hexdigest()


def strict_json(path: Path) -> tuple[dict[str, Any], bytes]:
    if not path.is_file() or path.is_symlink():
        raise AdmissionOnlyStop("CONTROL_FILE_INVALID", f"invalid control file: {path}")
    payload = path.read_bytes()
    try:
        value = json.loads(
            payload,
            parse_constant=lambda item: (_ for _ in ()).throw(ValueError(item)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise AdmissionOnlyStop("CONTROL_JSON_INVALID", str(path)) from error
    if not isinstance(value, dict) or canonical_json(value) != payload:
        raise AdmissionOnlyStop("CONTROL_JSON_INVALID", f"noncanonical JSON: {path}")
    return value, payload


def _sha(value: Any, name: str) -> str:
    _require(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value),
        "CONTROL_VALUE_INVALID",
        f"{name} must be lowercase SHA256",
    )
    return value


def _strict_int(value: Any, name: str, minimum: int = 0) -> int:
    _require(
        isinstance(value, int) and not isinstance(value, bool) and value >= minimum,
        "CONTROL_VALUE_INVALID",
        f"{name} must be integer >= {minimum}",
    )
    return value


def validate_candidate(candidate: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "status",
        "run_id",
        "accepted_state",
        "remote",
        "gpu",
        "budgets",
        "attempt",
        "scope",
        "helper_manifest",
        "guard_sha256",
        "plan_sha256",
    }
    _require(set(candidate) == required, "CANDIDATE_INVALID", "candidate keys drift")
    _require(
        candidate["schema_version"] == CANDIDATE_SCHEMA,
        "CANDIDATE_INVALID",
        "candidate schema drift",
    )
    _require(
        candidate["status"] == "LOCAL_CANDIDATE_NO_REMOTE_ACTION_NO_AUTHORITY",
        "CANDIDATE_INVALID",
        "candidate status drift",
    )
    _require(candidate["run_id"] == RUN_ID, "CANDIDATE_INVALID", "run id drift")
    accepted = candidate["accepted_state"]
    _require(
        accepted
        == {
            "archive_path": (
                "/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/"
                "control/code.tar.gz"
            ),
            "archive_bytes": ARCHIVE_BYTES,
            "archive_sha256": ARCHIVE_SHA256,
            "control_commit": CONTROL_COMMIT,
            "final_candidate_sha256": FINAL_CANDIDATE_SHA256,
            "package_sha256": PACKAGE_SHA256,
        },
        "CANDIDATE_INVALID",
        "accepted state drift",
    )
    remote = candidate["remote"]
    _require(
        remote
        == {
            "host_alias": "gpu-taobo",
            "hostname": HOSTNAME,
            "user": REMOTE_USER,
            "uid": REMOTE_UID,
            "task_root": "/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0",
            "code_root": (
                "/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/code"
            ),
            "control_root": (
                "/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control"
            ),
            "packet_dir": "/mnt/data2/drtao/wennie/S09-E008-P1-STAGING-20261016/packet",
            "base_runtime_config": (
                "/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/code/"
                "docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json"
            ),
            "base_package_config": (
                "/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/code/"
                "docs/research/S09/S09-E017/final_run_package_config_20261019.json"
            ),
            "final_candidate": (
                "/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/code/"
                "docs/research/S09/S09-E017/final_execution_candidate_20261020.json"
            ),
            "checkpoint": (
                "/mnt/data2/drtao/wennie/S09-E010-R001-support-amplitude-three-arm/"
                "B25_support_amplitude_beta0p25/checkpoint_update500.pt"
            ),
            "temp_root": (
                "/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/tmp"
            ),
            "cache_root": (
                "/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/cache"
            ),
            "output_root": (
                "/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/run"
            ),
            "science_archive_root": (
                "/mnt/data2/drtao/pidl_archives/S09-E017-R001-factorised-head-p0"
            ),
        },
        "CANDIDATE_INVALID",
        "remote path/identity drift",
    )
    _require(
        candidate["gpu"]
        == {
            "index": GPU_INDEX,
            "uuid": GPU_UUID,
            "minimum_free_bytes": 20 * 1024**3,
            "maximum_compute_processes": 0,
        },
        "CANDIDATE_INVALID",
        "GPU contract drift",
    )
    _require(
        candidate["budgets"]
        == {
            "wall_seconds": 300,
            "remote_cpu_seconds": 60,
            "cpu_threads": 1,
            "host_rss_bytes": 1024**3,
            "metadata_transfer_bytes": 1024**2,
            "remote_control_tree_bytes": 2 * 1024**2,
            "archive_read_bytes": ARCHIVE_BYTES,
            "minimum_free_disk_bytes": 20 * 1024**3,
            "packet_checkpoint_content_bytes": 0,
            "cuda_initializations": 0,
            "cuda_bytes": 0,
            "scientific_output_bytes": 0,
        },
        "CANDIDATE_INVALID",
        "budget drift",
    )
    _require(
        candidate["attempt"]
        == {
            "maximum_connection_attempts": 1,
            "maximum_metadata_transfers": 1,
            "retry": False,
            "reconnect": False,
            "resume": False,
            "alternate_host": False,
            "alternate_gpu": False,
        },
        "CANDIDATE_INVALID",
        "attempt policy drift",
    )
    _require(
        candidate["scope"]
        == {
            "execution_authorized": False,
            "producer_authorized": False,
            "scientific_asset_content_reads": False,
            "packet_manifest_verified_live": False,
            "checkpoint_verified_live": False,
            "runtime_builds": 0,
            "model_forwards": 0,
            "autograd_collections": 0,
            "optimizer_constructions": 0,
            "optimizer_steps": 0,
        },
        "CANDIDATE_INVALID",
        "scope drift",
    )
    manifest = candidate["helper_manifest"]
    _require(
        isinstance(manifest, dict) and 3 <= len(manifest) <= 8,
        "CANDIDATE_INVALID",
        "helper manifest width drift",
    )
    for relative, digest in manifest.items():
        _require(
            isinstance(relative, str)
            and not Path(relative).is_absolute()
            and ".." not in Path(relative).parts,
            "CANDIDATE_INVALID",
            "unsafe helper path",
        )
        _sha(digest, f"helper {relative}")
    _sha(candidate["guard_sha256"], "guard")
    _sha(candidate["plan_sha256"], "plan")


def validate_authority(
    authority: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    candidate_sha256: str,
    plan_sha256: str,
) -> None:
    validate_candidate(candidate)
    required = {
        "schema_version",
        "approval_status",
        "run_id",
        "admission_only_attempt_id",
        "candidate_sha256",
        "accepted_archive_path",
        "accepted_archive_bytes",
        "accepted_archive_sha256",
        "accepted_control_commit",
        "guard_sha256",
        "plan_sha256",
        "helper_manifest",
        "allowed_actions",
        "execution_authorized",
        "producer_authorized",
        "scientific_asset_content_reads",
        "maximum_connection_attempts",
        "maximum_metadata_transfers",
        "retry",
        "reconnect",
        "alternate_host",
        "alternate_gpu",
        "budgets",
        "local_evidence_root",
        "remote_attempt_root",
        "granted_by",
        "granted_at",
    }
    _require(set(authority) == required, "AUTHORITY_INVALID", "authority keys drift")
    checks = [
        authority["schema_version"] == AUTHORITY_SCHEMA,
        authority["approval_status"] == "APPROVED_FOR_ONE_RESOLVER_AND_ADMISSION_ONLY",
        authority["run_id"] == RUN_ID,
        authority["candidate_sha256"] == candidate_sha256,
        authority["accepted_archive_path"]
        == candidate["accepted_state"]["archive_path"],
        authority["accepted_archive_bytes"] == ARCHIVE_BYTES,
        authority["accepted_archive_sha256"] == ARCHIVE_SHA256,
        authority["accepted_control_commit"] == CONTROL_COMMIT,
        authority["guard_sha256"] == candidate["guard_sha256"],
        authority["plan_sha256"] == plan_sha256 == candidate["plan_sha256"],
        authority["helper_manifest"] == candidate["helper_manifest"],
        tuple(authority["allowed_actions"]) == GUARD_ACTIONS,
        authority["execution_authorized"] is False,
        authority["producer_authorized"] is False,
        authority["scientific_asset_content_reads"] is False,
        authority["maximum_connection_attempts"] == 1,
        authority["maximum_metadata_transfers"] == 1,
        authority["retry"] is False,
        authority["reconnect"] is False,
        authority["alternate_host"] is False,
        authority["alternate_gpu"] is False,
        authority["budgets"] == candidate["budgets"],
        authority["granted_by"] == "user",
    ]
    _require(all(checks), "AUTHORITY_INVALID", "authority value drift")
    attempt_id = authority["admission_only_attempt_id"]
    _require(
        isinstance(attempt_id, str)
        and 1 <= len(attempt_id) <= 64
        and attempt_id[0].isalnum()
        and all(c.isalnum() or c in "_-" for c in attempt_id),
        "AUTHORITY_INVALID",
        "attempt id invalid",
    )
    local_root = Path(authority["local_evidence_root"])
    remote_root = Path(authority["remote_attempt_root"])
    _require(local_root.is_absolute(), "AUTHORITY_INVALID", "local root not absolute")
    _require(
        local_root.name == attempt_id,
        "AUTHORITY_INVALID",
        "local attempt root mismatch",
    )
    expected_remote = (
        Path(candidate["remote"]["control_root"])
        / "admission_only_attempts"
        / attempt_id
    )
    _require(remote_root == expected_remote, "AUTHORITY_INVALID", "remote root drift")
    try:
        granted = datetime.fromisoformat(authority["granted_at"])
    except (TypeError, ValueError) as error:
        raise AdmissionOnlyStop("AUTHORITY_INVALID", "grant time invalid") from error
    _require(granted.tzinfo is not None, "AUTHORITY_INVALID", "grant timezone missing")


def banned_modules_loaded() -> list[str]:
    return sorted(
        name
        for name in sys.modules
        if any(
            name == prefix or name.startswith(prefix + ".")
            for prefix in BANNED_MODULE_PREFIXES
        )
    )


def assert_no_scientific_modules() -> None:
    loaded = banned_modules_loaded()
    _require(not loaded, "PROHIBITED_IMPORT", f"scientific modules loaded: {loaded}")


def path_metadata(path: Path, *, kind: str) -> dict[str, Any]:
    try:
        stat = path.lstat()
    except FileNotFoundError as error:
        raise AdmissionOnlyStop("SCIENTIFIC_PATH_MISSING", str(path)) from error
    _require(not path.is_symlink(), "SCIENTIFIC_PATH_INVALID", f"symlink: {path}")
    if kind == "directory":
        _require(path.is_dir(), "SCIENTIFIC_PATH_INVALID", f"not directory: {path}")
    elif kind == "file":
        _require(path.is_file(), "SCIENTIFIC_PATH_INVALID", f"not file: {path}")
    else:
        raise ValueError(kind)
    return {
        "path": str(path),
        "kind": kind,
        "size_bytes": stat.st_size,
        "mode": stat.st_mode,
        "content_opened": False,
    }


def tree_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            item = Path(root) / name
            try:
                total += item.stat().st_size
            except FileNotFoundError:
                continue
    return total


def process_identity() -> dict[str, Any]:
    return {
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "uid": os.getuid(),
        "user": getpass.getuser(),
        "cwd": str(Path.cwd()),
    }


def _run_text(command: Sequence[str], *, cwd: Path | None = None) -> str:
    allowed = {"git", "nvidia-smi"}
    _require(
        Path(command[0]).name in allowed,
        "PROHIBITED_COMMAND",
        f"command not allowed: {command[0]}",
    )
    result = subprocess.run(
        list(command),
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip()


def git_identity(
    code_root: Path, runner: Callable[..., str] = _run_text
) -> dict[str, Any]:
    head = runner(("git", "rev-parse", "HEAD"), cwd=code_root)
    status = runner(("git", "status", "--short"), cwd=code_root)
    _require(head == CONTROL_COMMIT, "CODE_IDENTITY_MISMATCH", "Git HEAD drift")
    _require(not status, "CODE_DIRTY", "tracked/untracked code root is dirty")
    return {"head": head, "dirty": False}


def parse_gpu_rows(identity_text: str, process_text: str) -> dict[str, Any]:
    rows = [line.strip() for line in identity_text.splitlines() if line.strip()]
    match = None
    for row in rows:
        parts = [part.strip() for part in row.split(",")]
        _require(len(parts) == 6, "GPU_METADATA_INVALID", "GPU row width drift")
        if int(parts[0]) == GPU_INDEX:
            match = parts
    _require(match is not None, "GPU_IDENTITY_MISMATCH", "GPU index missing")
    index, uuid, name, total_mib, used_mib, utilisation = match
    _require(uuid == GPU_UUID, "GPU_IDENTITY_MISMATCH", "GPU UUID drift")
    free_bytes = (int(total_mib) - int(used_mib)) * 1024**2
    process_rows = [line.strip() for line in process_text.splitlines() if line.strip()]
    matching_processes = [row for row in process_rows if GPU_UUID in row]
    _require(
        free_bytes >= 20 * 1024**3,
        "GPU_AVAILABILITY_FAILED",
        "less than 20 GiB GPU memory free",
    )
    _require(
        not matching_processes,
        "GPU_AVAILABILITY_FAILED",
        "compute process present on frozen GPU",
    )
    return {
        "index": int(index),
        "uuid": uuid,
        "name": name,
        "total_mib": int(total_mib),
        "used_mib": int(used_mib),
        "free_bytes": free_bytes,
        "utilization_percent": int(utilisation),
        "compute_processes": 0,
        "query_type": "nvidia-smi-metadata-only",
        "cuda_initialized": False,
    }


def gpu_metadata(runner: Callable[..., str] = _run_text) -> dict[str, Any]:
    identity = runner(
        (
            "nvidia-smi",
            "--query-gpu=index,uuid,name,memory.total,memory.used,utilization.gpu",
            "--format=csv,noheader,nounits",
        )
    )
    try:
        processes = runner(
            (
                "nvidia-smi",
                "--query-compute-apps=pid,gpu_uuid,used_memory",
                "--format=csv,noheader,nounits",
            )
        )
    except subprocess.CalledProcessError as error:
        # nvidia-smi returns a nonzero status on some drivers when no process
        # table exists.  This is not accepted as an empty list.
        raise AdmissionOnlyStop(
            "GPU_METADATA_INVALID", "compute query failed"
        ) from error
    return parse_gpu_rows(identity, processes)


def host_resource_snapshot(
    candidate: Mapping[str, Any], attempt_root: Path
) -> dict[str, Any]:
    remote = candidate["remote"]
    budgets = candidate["budgets"]
    maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_bytes = int(maxrss * 1024) if platform.system() == "Linux" else int(maxrss)
    free_disk = shutil.disk_usage(attempt_root.parent).free
    control_bytes = tree_size(Path(remote["control_root"]) / "admission_only_attempts")
    _require(rss_bytes <= budgets["host_rss_bytes"], "RESOURCE_CAP_EXCEEDED", "RSS cap")
    _require(
        free_disk >= budgets["minimum_free_disk_bytes"],
        "RESOURCE_CAP_EXCEEDED",
        "disk floor",
    )
    _require(
        control_bytes <= budgets["remote_control_tree_bytes"],
        "RESOURCE_CAP_EXCEEDED",
        "control tree cap",
    )
    return {
        "host_max_rss_bytes": rss_bytes,
        "free_disk_bytes": free_disk,
        "admission_only_control_tree_bytes": control_bytes,
    }


def resolve_admission_only(
    *,
    candidate: Mapping[str, Any],
    authority: Mapping[str, Any],
    candidate_sha256: str,
    plan_sha256: str,
    package_config_sha256: str,
    final_candidate_sha256: str,
    archive_sha256: str,
    observed_commit: str,
) -> dict[str, Any]:
    validate_authority(
        authority,
        candidate,
        candidate_sha256=candidate_sha256,
        plan_sha256=plan_sha256,
    )
    checks = [
        package_config_sha256 == PACKAGE_SHA256,
        final_candidate_sha256 == FINAL_CANDIDATE_SHA256,
        archive_sha256 == ARCHIVE_SHA256,
        observed_commit == CONTROL_COMMIT,
    ]
    _require(all(checks), "CONTROL_IDENTITY_MISMATCH", "resolved input drift")
    assert_no_scientific_modules()
    return {
        "schema_version": RESOLVED_SCHEMA,
        "status": "RESOLVED_FOR_ADMISSION_ONLY",
        "run_id": RUN_ID,
        "admission_only_attempt_id": authority["admission_only_attempt_id"],
        "execution_authorized": False,
        "producer_authorized": False,
        "scientific_asset_content_reads": False,
        "allowed_actions": list(GUARD_ACTIONS),
        "candidate_sha256": candidate_sha256,
        "plan_sha256": plan_sha256,
        "authority_sha256": sha256_bytes(canonical_json(authority)),
        "accepted_state": dict(candidate["accepted_state"]),
        "remote": dict(candidate["remote"]),
        "gpu": dict(candidate["gpu"]),
        "budgets": dict(candidate["budgets"]),
        "counters": {
            "scientific_asset_content_bytes": 0,
            "cuda_initializations": 0,
            "runtime_builds": 0,
            "model_forwards": 0,
            "autograd_collections": 0,
            "optimizer_constructions": 0,
            "optimizer_steps": 0,
        },
    }


def validate_resolved(resolved: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "status",
        "run_id",
        "admission_only_attempt_id",
        "execution_authorized",
        "producer_authorized",
        "scientific_asset_content_reads",
        "allowed_actions",
        "candidate_sha256",
        "plan_sha256",
        "authority_sha256",
        "accepted_state",
        "remote",
        "gpu",
        "budgets",
        "counters",
    }
    _require(set(resolved) == required, "RESOLVED_CONTROL_INVALID", "keys drift")
    checks = [
        resolved["schema_version"] == RESOLVED_SCHEMA,
        resolved["status"] == "RESOLVED_FOR_ADMISSION_ONLY",
        resolved["run_id"] == RUN_ID,
        resolved["execution_authorized"] is False,
        resolved["producer_authorized"] is False,
        resolved["scientific_asset_content_reads"] is False,
        tuple(resolved["allowed_actions"]) == GUARD_ACTIONS,
        resolved["accepted_state"]["archive_sha256"] == ARCHIVE_SHA256,
        resolved["accepted_state"]["control_commit"] == CONTROL_COMMIT,
        all(value == 0 for value in resolved["counters"].values()),
    ]
    _require(all(checks), "RESOLVED_CONTROL_INVALID", "value drift")


def begin_attempt(attempt_root: Path, authority: Mapping[str, Any]) -> Path:
    expected = Path(authority["remote_attempt_root"])
    _require(attempt_root == expected, "ATTEMPT_PATH_INVALID", "attempt root drift")
    attempt_root.mkdir(parents=True, exist_ok=False)
    path = attempt_root / "attempt.json"
    payload = {
        "schema_version": ATTEMPT_SCHEMA,
        "terminal_state": "ADMISSION_ONLY_ATTEMPT_STARTED",
        "run_id": RUN_ID,
        "admission_only_attempt_id": authority["admission_only_attempt_id"],
        "started_at": datetime.now().astimezone().isoformat(),
        "process_identity": process_identity(),
        "retry": False,
        "reconnect": False,
    }
    with path.open("xb") as stream:
        stream.write(canonical_json(payload))
    return path


def _write_once(path: Path, value: Mapping[str, Any]) -> Path:
    with path.open("xb") as stream:
        stream.write(canonical_json(value))
    return path


def run_metadata_admission(
    *,
    candidate: Mapping[str, Any],
    resolved: Mapping[str, Any],
    authority: Mapping[str, Any],
    attempt_root: Path,
    command_runner: Callable[..., str] = _run_text,
) -> dict[str, Any]:
    validate_candidate(candidate)
    validate_resolved(resolved)
    _require(
        resolved["authority_sha256"] == sha256_bytes(canonical_json(authority)),
        "RESOLVED_CONTROL_INVALID",
        "authority binding drift",
    )
    _require(
        resolved["admission_only_attempt_id"] == authority["admission_only_attempt_id"],
        "RESOLVED_CONTROL_INVALID",
        "attempt binding drift",
    )
    for name in ("accepted_state", "remote", "gpu", "budgets"):
        _require(
            resolved[name] == candidate[name],
            "RESOLVED_CONTROL_INVALID",
            f"resolved {name} drift",
        )
    assert_no_scientific_modules()
    _require(platform.system() == "Linux", "HOST_IDENTITY_MISMATCH", "not Linux")
    _require(socket.gethostname() == HOSTNAME, "HOST_IDENTITY_MISMATCH", "host drift")
    _require(os.getuid() == REMOTE_UID, "HOST_IDENTITY_MISMATCH", "uid drift")
    _require(getpass.getuser() == REMOTE_USER, "HOST_IDENTITY_MISMATCH", "user drift")
    remote = candidate["remote"]
    code_root = Path(remote["code_root"])
    _require(Path.cwd() == code_root, "HOST_IDENTITY_MISMATCH", "cwd drift")
    git = git_identity(code_root, command_runner)
    blocked = [
        Path(remote["control_root"]) / "execution_authority.json",
        Path(remote["control_root"]) / "config_resolved.json",
        Path(remote["control_root"]) / "resolution_receipt.json",
        Path(remote["control_root"]) / "admission_attempt.json",
        Path(remote["control_root"]) / "admission_receipt.json",
        Path(remote["control_root"]) / "admission_failure_receipt.json",
        Path(remote["output_root"]),
        Path(remote["science_archive_root"]),
    ]
    present = [str(path) for path in blocked if path.exists()]
    _require(not present, "BLOCKED_PATH_PRESENT", json.dumps(present))
    for name in ("control_root", "temp_root", "cache_root"):
        path = Path(remote[name])
        _require(path.is_dir() and not path.is_symlink(), "CONTROL_PATH_INVALID", name)
    archive = Path(candidate["accepted_state"]["archive_path"])
    archive_digest = sha256_path(archive, expected_bytes=ARCHIVE_BYTES)
    _require(archive_digest == ARCHIVE_SHA256, "ARCHIVE_IDENTITY_MISMATCH", "archive")
    scientific_paths = {
        "packet_dir": path_metadata(Path(remote["packet_dir"]), kind="directory"),
        "base_runtime_config": path_metadata(
            Path(remote["base_runtime_config"]), kind="file"
        ),
        "checkpoint": path_metadata(Path(remote["checkpoint"]), kind="file"),
    }
    resources = host_resource_snapshot(candidate, attempt_root)
    gpu = gpu_metadata(command_runner)
    assert_no_scientific_modules()
    return {
        "schema_version": RECEIPT_SCHEMA,
        "terminal_state": SUCCESS_STATE,
        "run_id": RUN_ID,
        "admission_only_attempt_id": authority["admission_only_attempt_id"],
        "authority_sha256": resolved["authority_sha256"],
        "process_identity": process_identity(),
        "git": git,
        "archive": {
            "path": str(archive),
            "bytes": ARCHIVE_BYTES,
            "sha256": archive_digest,
        },
        "scientific_path_metadata": scientific_paths,
        "scientific_identities_verified_live": False,
        "resource_snapshot": resources,
        "gpu_metadata": gpu,
        "execution_authorized": False,
        "producer_authorized": False,
        "counters": dict(resolved["counters"]),
        "retry": False,
        "reconnect": False,
        "next_action": "STOP_NO_PRODUCER_SEPARATE_EXPLICIT_AUTHORITY_REQUIRED",
    }


def failure_receipt(
    *,
    authority: Mapping[str, Any],
    error: BaseException,
) -> dict[str, Any]:
    reason = getattr(error, "first_reason", type(error).__name__)
    return {
        "schema_version": FAILURE_SCHEMA,
        "terminal_state": "ADMISSION_ONLY_STOPPED",
        "first_reason": reason,
        "detail": f"{type(error).__name__}: {error}",
        "run_id": RUN_ID,
        "admission_only_attempt_id": authority.get("admission_only_attempt_id"),
        "process_identity": process_identity(),
        "execution_authorized": False,
        "producer_authorized": False,
        "counters": {
            "scientific_asset_content_bytes": 0,
            "cuda_initializations": 0,
            "runtime_builds": 0,
            "model_forwards": 0,
            "autograd_collections": 0,
            "optimizer_constructions": 0,
            "optimizer_steps": 0,
        },
        "retry": False,
        "reconnect": False,
    }


__all__ = [
    "AdmissionOnlyStop",
    "ARCHIVE_BYTES",
    "ARCHIVE_SHA256",
    "AUTHORITY_SCHEMA",
    "CANDIDATE_SCHEMA",
    "CONTROL_COMMIT",
    "FINAL_CANDIDATE_SHA256",
    "GUARD_ACTIONS",
    "PACKAGE_SHA256",
    "RUN_ID",
    "SUCCESS_STATE",
    "assert_no_scientific_modules",
    "begin_attempt",
    "canonical_json",
    "failure_receipt",
    "resolve_admission_only",
    "run_metadata_admission",
    "sha256_bytes",
    "sha256_path",
    "strict_json",
    "validate_authority",
    "validate_candidate",
    "validate_resolved",
]
