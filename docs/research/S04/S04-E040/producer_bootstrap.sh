#!/usr/bin/env bash
# Materialize and submit exactly one S04-E040 package from a user-pinned receipt.
#
# This script is uploaded next to the tar, receipt and runtime manifest rather
# than being executed from the tar. The approval card pins PACKAGE_RECEIPT_SHA256;
# that external value is the root of the deployment provenance chain.
set -euo pipefail

readonly REVIEWED_RUNTIME_COMMIT=5aaa317ed55175e80acb581d922eb6a1a4cb6d49
readonly RECEIPT_SCHEMA=S04-E040-producer-package-receipt-v2
readonly RUNTIME_MANIFEST_SCHEMA=S04-E040-reviewed-runtime-manifest-v1
readonly MATERIALIZATION_SCHEMA=S04-E040-materialization-receipt-v1
readonly LAUNCH_RELATIVE_PATH=docs/research/S04/S04-E040/producer_launch.sh
readonly BOOTSTRAP_FILE=producer_bootstrap.sh
readonly SYSTEMD_TIMEOUT_SECONDS=3600

: "${RUN_ID:?set RUN_ID to the approved fresh run id}"
: "${TASKROOT:?set TASKROOT to the fresh /mnt/data2/drtao/wennie run directory}"
: "${PIDL_ARCHIVE_DIR:?set PIDL_ARCHIVE_DIR to the fresh archive directory}"
: "${PHYSICAL_GPU_INDEX:?set PHYSICAL_GPU_INDEX to the selected physical GPU index}"
: "${BASELINE:?set BASELINE to the frozen Umax=0.12 recovery archive}"
: "${REFERENCE_RESULT:?set REFERENCE_RESULT to the completed S04-E037-R001 results directory}"
: "${PACKAGE_ARCHIVE:?set PACKAGE_ARCHIVE to the uploaded tar in TASKROOT}"
: "${PACKAGE_RECEIPT:?set PACKAGE_RECEIPT to the uploaded receipt in TASKROOT}"
: "${PACKAGE_RUNTIME_MANIFEST:?set PACKAGE_RUNTIME_MANIFEST to the uploaded runtime manifest in TASKROOT}"
: "${PACKAGE_RECEIPT_SHA256:?set PACKAGE_RECEIPT_SHA256 to the approval-card SHA-256}"

fail() {
    printf '%s\n' "$*" >&2
    exit 2
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || fail "required command unavailable: $1"
}

for required in sha256sum tar git find grep systemd-run systemctl /usr/bin/python3; do
    require_command "$required"
done

[[ "$RUN_ID" =~ ^pf_s04e040_feasible_damage_[a-z0-9]+_[0-9]{8}T[0-9]{6}Z$ ]] ||
    fail "invalid S04-E040 run id: $RUN_ID"
[[ "$PHYSICAL_GPU_INDEX" =~ ^[0-9]+$ ]] ||
    fail "PHYSICAL_GPU_INDEX must be one physical GPU index"
[[ "$TASKROOT" == "/mnt/data2/drtao/wennie/$RUN_ID" ]] ||
    fail "TASKROOT does not match the approved run-id path"
[[ "$PIDL_ARCHIVE_DIR" == "/mnt/data2/drtao/pidl_archives/$RUN_ID" ]] ||
    fail "PIDL_ARCHIVE_DIR does not match the approved run-id path"
[[ -d "$TASKROOT" ]] || fail "missing staged task root: $TASKROOT"
[[ ! -e "$TASKROOT/code" ]] || fail "refusing pre-existing code tree in task root"
[[ ! -e "$PIDL_ARCHIVE_DIR" ]] || fail "refusing non-fresh archive root: $PIDL_ARCHIVE_DIR"
[[ "$PACKAGE_RECEIPT_SHA256" =~ ^[0-9a-f]{64}$ ]] || fail "invalid pinned receipt SHA-256"

submission_metadata="$(/usr/bin/python3 - \
    "$TASKROOT" "$PACKAGE_ARCHIVE" "$PACKAGE_RECEIPT" "$PACKAGE_RUNTIME_MANIFEST" \
    "${BASH_SOURCE[0]}" "$PACKAGE_RECEIPT_SHA256" "$REVIEWED_RUNTIME_COMMIT" \
    "$RECEIPT_SCHEMA" "$RUNTIME_MANIFEST_SCHEMA" "$LAUNCH_RELATIVE_PATH" "$BOOTSTRAP_FILE" <<'PY'
import hashlib
import json
import re
import sys
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"bootstrap verification failed: {message}")


raw_root = Path(sys.argv[1])
raw_archive = Path(sys.argv[2])
raw_receipt = Path(sys.argv[3])
raw_manifest = Path(sys.argv[4])
raw_bootstrap = Path(sys.argv[5])
if any(path.is_symlink() for path in (raw_root, raw_archive, raw_receipt, raw_manifest, raw_bootstrap)):
    fail("task root or package sidecar must not be a symlink")
root = raw_root.resolve()
archive = raw_archive.resolve()
receipt_path = raw_receipt.resolve()
manifest_path = raw_manifest.resolve()
bootstrap = raw_bootstrap.resolve()
pinned_receipt, reviewed_commit, receipt_schema, manifest_schema, entrypoint, bootstrap_file = sys.argv[6:]
for path, label in ((archive, "archive"), (receipt_path, "receipt"),
                    (manifest_path, "runtime manifest"), (bootstrap, "bootstrap")):
    if path.parent != root or not path.is_file():
        fail(f"{label} is not a regular direct child of task root")
expected_stage = {archive.name, receipt_path.name, manifest_path.name, bootstrap.name}
actual_stage = {path.name for path in root.iterdir()}
if actual_stage != expected_stage:
    fail("task root is not a fresh four-file staging directory")
if digest(receipt_path) != pinned_receipt:
    fail("receipt does not match its approval-card SHA-256")
try:
    receipt = json.loads(receipt_path.read_text())
    manifest = json.loads(manifest_path.read_text())
except (OSError, json.JSONDecodeError) as error:
    fail(f"unreadable receipt or runtime manifest: {error}")
required = {
    "package_commit", "reviewed_runtime_commit", "archive_file", "archive_sha256",
    "archive_bytes", "runtime_manifest_file", "runtime_manifest_sha256",
    "entrypoint", "entrypoint_sha256", "bootstrap_file", "bootstrap_sha256",
}
if receipt.get("schema") != receipt_schema or not required <= receipt.keys():
    fail("unexpected or incomplete package receipt")
if receipt["reviewed_runtime_commit"] != reviewed_commit:
    fail("reviewed runtime commit differs from the approved source")
if receipt["bootstrap_file"] != bootstrap_file or digest(bootstrap) != receipt["bootstrap_sha256"]:
    fail("bootstrap differs from the pinned package")
if receipt["archive_file"] != archive.name or receipt["runtime_manifest_file"] != manifest_path.name:
    fail("sidecar filename differs from receipt")
if not re.fullmatch(r"[0-9a-f]{40}", receipt["package_commit"]):
    fail("invalid package commit")
for key in ("archive_sha256", "runtime_manifest_sha256", "entrypoint_sha256", "bootstrap_sha256"):
    if not isinstance(receipt[key], str) or not re.fullmatch(r"[0-9a-f]{64}", receipt[key]):
        fail(f"invalid {key}")
if not isinstance(receipt["archive_bytes"], int) or receipt["archive_bytes"] < 1:
    fail("invalid archive byte count")
if archive.stat().st_size != receipt["archive_bytes"] or digest(archive) != receipt["archive_sha256"]:
    fail("tar differs from receipt")
if digest(manifest_path) != receipt["runtime_manifest_sha256"]:
    fail("runtime manifest differs from receipt")
if manifest.get("schema") != manifest_schema or manifest.get("reviewed_runtime_commit") != reviewed_commit:
    fail("unexpected runtime manifest")
files = manifest.get("files")
if not isinstance(files, list) or not files:
    fail("runtime manifest has no files")
for item in files:
    if not isinstance(item, dict) or set(item) != {"path", "bytes", "sha256"}:
        fail("invalid runtime-manifest entry")
print(f"package_commit={receipt['package_commit']}")
print(f"archive_sha256={receipt['archive_sha256']}")
print(f"runtime_manifest_sha256={receipt['runtime_manifest_sha256']}")
print(f"runtime_files_expected={len(files)}")
PY
)" || fail "bootstrap sidecar verification failed"

tar_commit="$(git get-tar-commit-id < "$PACKAGE_ARCHIVE" 2>/dev/null)" ||
    fail "could not read git archive commit id from package tar"
receipt_commit="$(sed -n 's/^package_commit=//p' <<< "$submission_metadata")"
[[ "$tar_commit" == "$receipt_commit" ]] ||
    fail "tar package commit differs from receipt"

staging="$TASKROOT/.materialize-$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir "$staging"
if ! tar -xf "$PACKAGE_ARCHIVE" -C "$staging"; then
    fail "could not extract checked package tar"
fi
[[ -d "$staging/code" ]] || fail "package tar did not materialize code/"
if find "$staging" -mindepth 1 -maxdepth 1 ! -name code -print -quit | grep -q .; then
    fail "package tar has unexpected top-level content"
fi

# Verify the reviewed runtime closure before its inner launcher is allowed to
# start. The inner launcher repeats the same verification just before CUDA.
/usr/bin/python3 - \
    "$staging/code" "$PACKAGE_RECEIPT" "$PACKAGE_RUNTIME_MANIFEST" \
    "$REVIEWED_RUNTIME_COMMIT" "$RUNTIME_MANIFEST_SCHEMA" "$LAUNCH_RELATIVE_PATH" <<'PY'
import hashlib
import json
import stat
import sys
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"materialization verification failed: {message}")


raw_code = Path(sys.argv[1])
if raw_code.is_symlink():
    fail("materialized code directory must not be a symlink")
code = raw_code.resolve()
receipt = json.loads(Path(sys.argv[2]).read_text())
manifest = json.loads(Path(sys.argv[3]).read_text())
reviewed_commit, manifest_schema, expected_entrypoint = sys.argv[4:]
if manifest.get("schema") != manifest_schema or manifest.get("reviewed_runtime_commit") != reviewed_commit:
    fail("unexpected runtime manifest")
files = manifest.get("files")
if not isinstance(files, list) or not files:
    fail("runtime manifest has no files")
seen: set[str] = set()
for item in files:
    if not isinstance(item, dict) or set(item) != {"path", "bytes", "sha256"}:
        fail("invalid runtime-manifest entry")
    relative = item["path"]
    if not isinstance(relative, str) or not relative or relative in seen:
        fail("invalid or duplicate runtime path")
    seen.add(relative)
    raw_candidate = code / relative
    if raw_candidate.is_symlink():
        fail(f"runtime file is a symlink: {relative}")
    candidate = raw_candidate.resolve()
    if code not in candidate.parents or not candidate.is_file():
        fail(f"runtime file missing or unsafe: {relative}")
    if not stat.S_ISREG(candidate.stat().st_mode) or candidate.stat().st_size != item["bytes"]:
        fail(f"runtime file shape differs: {relative}")
    if digest(candidate) != item["sha256"]:
        fail(f"runtime file hash differs: {relative}")
raw_entrypoint = code / receipt["entrypoint"]
if raw_entrypoint.is_symlink():
    fail("inner launcher is a symlink")
entrypoint = raw_entrypoint.resolve()
if receipt["entrypoint"] != expected_entrypoint or code not in entrypoint.parents:
    fail("unexpected entrypoint")
if not entrypoint.is_file() or digest(entrypoint) != receipt["entrypoint_sha256"]:
    fail("inner launcher differs from package receipt")
PY

mv "$staging/code" "$TASKROOT/code"
rmdir "$staging"
materialization_tmp="$TASKROOT/.materialization_receipt.$$.tmp"
/usr/bin/python3 - \
    "$materialization_tmp" "$PACKAGE_RECEIPT" "$PACKAGE_RUNTIME_MANIFEST" "$PACKAGE_ARCHIVE" \
    "$tar_commit" "$MATERIALIZATION_SCHEMA" <<'PY'
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


target = Path(sys.argv[1])
receipt_path = Path(sys.argv[2])
manifest_path = Path(sys.argv[3])
archive_path = Path(sys.argv[4])
tar_commit = sys.argv[5]
schema = sys.argv[6]
receipt = json.loads(receipt_path.read_text())
payload = {
    "schema": schema,
    "package_receipt_sha256": digest(receipt_path),
    "archive_sha256": digest(archive_path),
    "runtime_manifest_sha256": digest(manifest_path),
    "package_commit": receipt["package_commit"],
    "tar_commit": tar_commit,
    "materialized_utc": datetime.now(timezone.utc).isoformat(),
}
with target.open("w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
    handle.write("\n")
    handle.flush()
    os.fsync(handle.fileno())
PY
mv "$materialization_tmp" "$TASKROOT/materialization_receipt.json"

service_unit="s04-e040-${RUN_ID}"
if systemctl --user show "$service_unit" -p LoadState 2>/dev/null | grep -qx 'LoadState=loaded'; then
    fail "systemd unit already exists: $service_unit"
fi
if ! (set -o noclobber; : > "$TASKROOT/launch_once"); then
    fail "run task root already has a launch-once marker"
fi

log_path="$TASKROOT/producer.log"
launcher="$TASKROOT/code/$LAUNCH_RELATIVE_PATH"
systemd_run_output="$(systemd-run --user \
    --unit="$service_unit" \
    --service-type=exec \
    --property=TimeoutStartSec=30 \
    --property=RuntimeMaxSec=${SYSTEMD_TIMEOUT_SECONDS} \
    --property=TimeoutStopSec=30 \
    --property=KillMode=control-group \
    --property=WorkingDirectory="$TASKROOT" \
    --setenv=RUN_ID="$RUN_ID" \
    --setenv=TASKROOT="$TASKROOT" \
    --setenv=PIDL_ARCHIVE_DIR="$PIDL_ARCHIVE_DIR" \
    --setenv=PHYSICAL_GPU_INDEX="$PHYSICAL_GPU_INDEX" \
    --setenv=BASELINE="$BASELINE" \
    --setenv=REFERENCE_RESULT="$REFERENCE_RESULT" \
    --setenv=PACKAGE_ARCHIVE="$PACKAGE_ARCHIVE" \
    --setenv=PACKAGE_RECEIPT="$PACKAGE_RECEIPT" \
    --setenv=PACKAGE_RUNTIME_MANIFEST="$PACKAGE_RUNTIME_MANIFEST" \
    /bin/bash -c 'exec /bin/bash "$1" >>"$2" 2>&1' -- "$launcher" "$log_path" 2>&1)" ||
    fail "systemd-run failed after launch-once marker: $systemd_run_output"
service_show="$(systemctl --user show "$service_unit" \
    -p Id -p MainPID -p ControlGroup -p ActiveState -p RuntimeMaxUSec -p TimeoutStopUSec \
    -p WorkingDirectory -p ExecStart 2>&1 || true)"
{
    printf '%s\n' 'schema=S04-E040-submission-receipt-v1'
    printf 'run_id=%s\n' "$RUN_ID"
    printf '%s\n' "$submission_metadata"
    printf 'tar_commit=%s\n' "$tar_commit"
    printf 'physical_gpu_index=%s\n' "$PHYSICAL_GPU_INDEX"
    printf 'systemd_unit=%s\n' "$service_unit"
    printf 'systemd_runtime_max_seconds=%s\n' "$SYSTEMD_TIMEOUT_SECONDS"
    printf 'launcher=%s\n' "$launcher"
    printf 'log_path=%s\n' "$log_path"
    printf 'runner_timeout_seconds=3500\n'
    printf 'systemd_run_output=%s\n' "$systemd_run_output"
    printf '%s\n' "$service_show"
    printf 'submitted_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$TASKROOT/submission_receipt.txt"
printf '%s\n' "submitted $service_unit; log=$log_path"
