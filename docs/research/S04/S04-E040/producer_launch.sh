#!/usr/bin/env bash
# Execute the already materialized S04-E040 producer package exactly once.
#
# This is deliberately an *inner* launcher. The trusted bootstrap outside the
# tar verifies the user-pinned receipt, SHA-checks the tar, materializes a fresh
# code tree and checks this entrypoint before systemd starts this script. The
# checks below repeat the runtime-manifest and frozen-input checks immediately
# before CUDA work, so an altered tree cannot silently enter the calculation.
set -euo pipefail

readonly REVIEWED_RUNTIME_COMMIT=5aaa317ed55175e80acb581d922eb6a1a4cb6d49
readonly RECEIPT_SCHEMA=S04-E040-producer-package-receipt-v2
readonly RUNTIME_MANIFEST_SCHEMA=S04-E040-reviewed-runtime-manifest-v1
readonly MATERIALIZATION_SCHEMA=S04-E040-materialization-receipt-v1
readonly LAUNCH_RELATIVE_PATH=docs/research/S04/S04-E040/producer_launch.sh
readonly EXPECTED_MODEL_SETTINGS_SHA256=015fe8ddf563b2b9d81b8a681705e2a35f9044206311a6a7e26f40a7dc9c1047
readonly EXPECTED_CHECKPOINT_SHA256=aad4ebcb60a41caba6e0d2dbfaaba7cb7cb2ece631da8fbbfcaf3d374fc77aae
readonly EXPECTED_NETWORK_SHA256=09f1fc279007262b1068f0526e36e3aa2005633da271924cb598b7994ba8509a
readonly EXPECTED_R001_STEPS_SHA256=fd21fced6639591c1966e12c6ed5e7ec086403dc02d889ec49011c0d2524deec
readonly MAX_IDLE_MEMORY_MIB=64
readonly MAX_IDLE_UTILIZATION_PERCENT=2

: "${RUN_ID:?set RUN_ID to the approved fresh run id}"
: "${TASKROOT:?set TASKROOT to the fresh /mnt/data2/drtao/wennie run directory}"
: "${PIDL_ARCHIVE_DIR:?set PIDL_ARCHIVE_DIR to the fresh archive directory}"
: "${PHYSICAL_GPU_INDEX:?set PHYSICAL_GPU_INDEX to one physical GPU index}"
: "${BASELINE:?set BASELINE to the frozen Umax=0.12 recovery archive}"
: "${REFERENCE_RESULT:?set REFERENCE_RESULT to the completed S04-E037-R001 results directory}"
: "${PACKAGE_ARCHIVE:?set PACKAGE_ARCHIVE to the uploaded tar in TASKROOT}"
: "${PACKAGE_RECEIPT:?set PACKAGE_RECEIPT to the pinned package receipt in TASKROOT}"
: "${PACKAGE_RUNTIME_MANIFEST:?set PACKAGE_RUNTIME_MANIFEST to the pinned runtime manifest in TASKROOT}"

fail() {
    printf '%s\n' "$*" >&2
    exit 2
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || fail "required command unavailable: $1"
}

sha256_of() {
    sha256sum "$1" | awk '{print $1}'
}

assert_sha256() {
    local path="$1"
    local expected="$2"
    local actual
    [[ -f "$path" ]] || fail "missing required file: $path"
    actual="$(sha256_of "$path")"
    [[ "$actual" == "$expected" ]] ||
        fail "SHA-256 mismatch for $path (expected $expected, got $actual)"
}

for required in sha256sum timeout nvidia-smi flock /usr/bin/python3; do
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
[[ -d "$TASKROOT/code" ]] || fail "missing materialized code directory"
[[ -f "$TASKROOT/materialization_receipt.json" ]] ||
    fail "missing bootstrap materialization receipt"
[[ ! -e "$PIDL_ARCHIVE_DIR" ]] ||
    fail "refusing non-fresh archive root: $PIDL_ARCHIVE_DIR"

# The package receipt, manifest and archive must be direct children of the
# same staged task root. Python validates the JSON schemas, runtime-file
# hashes, current entrypoint hash, and the bootstrap materialization receipt.
package_metadata="$(/usr/bin/python3 - \
    "$TASKROOT" "$PACKAGE_ARCHIVE" "$PACKAGE_RECEIPT" "$PACKAGE_RUNTIME_MANIFEST" \
    "$TASKROOT/materialization_receipt.json" "$REVIEWED_RUNTIME_COMMIT" \
    "$RECEIPT_SCHEMA" "$RUNTIME_MANIFEST_SCHEMA" "$MATERIALIZATION_SCHEMA" \
    "$LAUNCH_RELATIVE_PATH" <<'PY'
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
    raise SystemExit(f"package verification failed: {message}")


raw_root = Path(sys.argv[1])
raw_archive = Path(sys.argv[2])
raw_receipt = Path(sys.argv[3])
raw_manifest = Path(sys.argv[4])
raw_materialization = Path(sys.argv[5])
if any(path.is_symlink() for path in (raw_root, raw_archive, raw_receipt, raw_manifest, raw_materialization)):
    fail("task root or package metadata must not be a symlink")
root = raw_root.resolve()
archive = raw_archive.resolve()
receipt_path = raw_receipt.resolve()
manifest_path = raw_manifest.resolve()
materialization_path = raw_materialization.resolve()
reviewed_commit, receipt_schema, manifest_schema, materialization_schema, entrypoint = sys.argv[6:]
if not root.is_dir():
    fail("task root is missing")
for path, label in ((archive, "archive"), (receipt_path, "receipt"),
                    (manifest_path, "runtime manifest"),
                    (materialization_path, "materialization receipt")):
    if path.parent != root or not path.is_file():
        fail(f"{label} is not a regular direct child of task root")
try:
    receipt = json.loads(receipt_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    materialization = json.loads(materialization_path.read_text())
except (OSError, json.JSONDecodeError) as error:
    fail(f"unreadable package metadata: {error}")
required_receipt = {
    "package_commit", "reviewed_runtime_commit", "archive_file", "archive_sha256",
    "archive_bytes", "runtime_manifest_file", "runtime_manifest_sha256",
    "entrypoint", "entrypoint_sha256", "bootstrap_file", "bootstrap_sha256",
}
if receipt.get("schema") != receipt_schema or not required_receipt <= receipt.keys():
    fail("unexpected or incomplete package receipt")
if receipt["reviewed_runtime_commit"] != reviewed_commit:
    fail("receipt reviewed runtime commit differs from the reviewed source")
if not isinstance(receipt["package_commit"], str) or len(receipt["package_commit"]) != 40:
    fail("invalid package commit")
for key in ("archive_sha256", "runtime_manifest_sha256", "entrypoint_sha256", "bootstrap_sha256"):
    if not isinstance(receipt[key], str) or len(receipt[key]) != 64:
        fail(f"invalid {key}")
if receipt["archive_file"] != archive.name or receipt["runtime_manifest_file"] != manifest_path.name:
    fail("sidecar filename differs from receipt")
if not isinstance(receipt["archive_bytes"], int) or receipt["archive_bytes"] < 1:
    fail("invalid archive byte count")
if archive.stat().st_size != receipt["archive_bytes"] or digest(archive) != receipt["archive_sha256"]:
    fail("uploaded package archive differs from receipt")
if digest(manifest_path) != receipt["runtime_manifest_sha256"]:
    fail("runtime manifest differs from receipt")
if manifest.get("schema") != manifest_schema or manifest.get("reviewed_runtime_commit") != reviewed_commit:
    fail("unexpected runtime manifest")
files = manifest.get("files")
if not isinstance(files, list) or not files:
    fail("runtime manifest has no files")
seen: set[str] = set()
code = root / "code"
if code.is_symlink():
    fail("materialized code directory must not be a symlink")
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
    mode = candidate.stat().st_mode
    if not stat.S_ISREG(mode) or candidate.stat().st_size != item["bytes"]:
        fail(f"runtime file shape differs: {relative}")
    if digest(candidate) != item["sha256"]:
        fail(f"runtime file hash differs: {relative}")
raw_entrypoint = code / receipt["entrypoint"]
if raw_entrypoint.is_symlink():
    fail("inner launcher is a symlink")
entrypoint_path = raw_entrypoint.resolve()
if receipt["entrypoint"] != entrypoint or code not in entrypoint_path.parents:
    fail("unexpected entrypoint")
if not entrypoint_path.is_file() or digest(entrypoint_path) != receipt["entrypoint_sha256"]:
    fail("inner launcher differs from the checked package")
expected_materialization = {
    "schema": materialization_schema,
    "package_receipt_sha256": digest(receipt_path),
    "archive_sha256": receipt["archive_sha256"],
    "runtime_manifest_sha256": receipt["runtime_manifest_sha256"],
    "package_commit": receipt["package_commit"],
}
if any(materialization.get(key) != value for key, value in expected_materialization.items()):
    fail("materialization receipt does not bind this package")
print(f"package_commit={receipt['package_commit']}")
print(f"archive_sha256={receipt['archive_sha256']}")
print(f"runtime_manifest_sha256={receipt['runtime_manifest_sha256']}")
print(f"runtime_files_verified={len(files)}")
PY
)" || fail "package verification command failed"

assert_sha256 "$BASELINE/model_settings.txt" "$EXPECTED_MODEL_SETTINGS_SHA256"
assert_sha256 "$BASELINE/best_models/checkpoint_step_0.pt" "$EXPECTED_CHECKPOINT_SHA256"
assert_sha256 "$BASELINE/best_models/trained_1NN_0.pt" "$EXPECTED_NETWORK_SHA256"
assert_sha256 "$REFERENCE_RESULT/original/steps.json" "$EXPECTED_R001_STEPS_SHA256"

gpu_info="$(nvidia-smi --id="$PHYSICAL_GPU_INDEX" \
    --query-gpu=index,uuid,name,memory.used,utilization.gpu,driver_version \
    --format=csv,noheader,nounits 2>&1)" || fail "could not query physical GPU $PHYSICAL_GPU_INDEX: $gpu_info"
IFS=',' read -r reported_index gpu_uuid gpu_name gpu_memory_used gpu_utilization gpu_driver <<< "$gpu_info"
for variable in reported_index gpu_uuid gpu_name gpu_memory_used gpu_utilization gpu_driver; do
    value="${!variable//[[:space:]]/}"
    printf -v "$variable" '%s' "$value"
done
[[ "$reported_index" == "$PHYSICAL_GPU_INDEX" && "$gpu_uuid" == GPU-* ]] ||
    fail "could not resolve selected physical GPU UUID"
[[ "$gpu_memory_used" =~ ^[0-9]+$ && "$gpu_utilization" =~ ^[0-9]+$ ]] ||
    fail "selected GPU did not report numeric idle telemetry"

lock_dir=/mnt/data2/drtao/wennie/.s04-e040-gpu-locks
mkdir -p "$lock_dir"
exec 9>"$lock_dir/$gpu_uuid.lock"
flock -n 9 || fail "selected GPU $PHYSICAL_GPU_INDEX is reserved by another S04-E040 launcher"

assert_gpu_quiescent() {
    local stage="$1"
    local apps
    (( gpu_memory_used <= MAX_IDLE_MEMORY_MIB )) ||
        fail "selected GPU has ${gpu_memory_used} MiB in use at $stage"
    (( gpu_utilization <= MAX_IDLE_UTILIZATION_PERCENT )) ||
        fail "selected GPU has ${gpu_utilization}% utilization at $stage"
    if ! apps="$(nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_memory \
        --format=csv,noheader,nounits 2>&1)"; then
        fail "could not query compute processes at $stage: $apps"
    fi
    if awk -F, -v uuid="$gpu_uuid" '
        {gsub(/^[ \t]+|[ \t]+$/, "", $1); if ($1 == uuid) found=1}
        END {exit(found ? 0 : 1)}
    ' <<< "$apps"; then
        fail "selected GPU $PHYSICAL_GPU_INDEX already has a compute process at $stage"
    fi
}

assert_gpu_quiescent before_cuda_preflight
export CUDA_VISIBLE_DEVICES="$gpu_uuid"
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export PYTHONPATH="$TASKROOT/code/source:$TASKROOT/code/SENS_tensile"
export PYTHONNOUSERSITE=1
cuda_preflight="$(
    cd "$TASKROOT/code"
    /usr/bin/python3 - <<'PY'
import importlib.util
import json
import sys
from pathlib import Path

import gmshparser
import numpy
import torch
import tqdm

root = Path.cwd().resolve()
source_root = root / "source"
sens_root = root / "SENS_tensile"
spec = importlib.util.spec_from_file_location("s04_e040_runner", root / "scripts" / "run_s04_e040_feasible_damage.py")
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load E040 runner")
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)
from feasible_damage import require_clamp_min_right_derivative

assert torch.cuda.is_available(), "CUDA unavailable"
assert torch.cuda.device_count() == 1, "selected GPU was not isolated"
assert torch.cuda.get_device_name(0) == "NVIDIA GeForce RTX 4090", "unexpected GPU"
for module_name in ("feasible_damage", "compute_energy", "field_computation", "construct_model"):
    module_path = Path(sys.modules[module_name].__file__).resolve()
    assert source_root in module_path.parents or sens_root in module_path.parents, (
        f"foreign import for {module_name}: {module_path}"
    )
probe = torch.ones(1, device="cuda")
torch.cuda.synchronize()
assert float(probe.item()) == 1.0
require_clamp_min_right_derivative("cuda")
print(json.dumps({
    "torch": torch.__version__,
    "torch_cuda": torch.version.cuda,
    "numpy": numpy.__version__,
    "tqdm": tqdm.__version__,
    "gpu": torch.cuda.get_device_name(0),
    "runner": str(Path(runner.__file__).resolve()),
}))
PY
)" || fail "CUDA/import preflight failed"

# A second query closes the ordinary snapshot race as far as a shared machine
# can: the S04-E040 advisory lock stays open through the child process, and a
# process that appeared during import prevents the numerical runner from start.
gpu_info="$(nvidia-smi --id="$PHYSICAL_GPU_INDEX" \
    --query-gpu=index,uuid,name,memory.used,utilization.gpu,driver_version \
    --format=csv,noheader,nounits 2>&1)" || fail "could not re-query selected GPU"
IFS=',' read -r reported_index gpu_uuid_after gpu_name gpu_memory_used gpu_utilization gpu_driver <<< "$gpu_info"
for variable in reported_index gpu_uuid_after gpu_name gpu_memory_used gpu_utilization gpu_driver; do
    value="${!variable//[[:space:]]/}"
    printf -v "$variable" '%s' "$value"
done
[[ "$reported_index" == "$PHYSICAL_GPU_INDEX" && "$gpu_uuid_after" == "$gpu_uuid" ]] ||
    fail "selected GPU identity changed during preflight"
assert_gpu_quiescent before_runner

mkdir "$PIDL_ARCHIVE_DIR"
export TMPDIR="$TASKROOT/tmp"
export XDG_CACHE_HOME="$TASKROOT/cache"
export TORCH_EXTENSIONS_DIR="$TASKROOT/.jitcache"
export MPLCONFIGDIR="$TASKROOT/cache/matplotlib"
export OMP_NUM_THREADS=4
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME" "$TORCH_EXTENSIONS_DIR" "$MPLCONFIGDIR"

{
    printf '%s\n' 'schema=S04-E040-producer-preflight-v2'
    printf 'run_id=%s\n' "$RUN_ID"
    printf 'reviewed_runtime_commit=%s\n' "$REVIEWED_RUNTIME_COMMIT"
    printf '%s\n' "$package_metadata"
    printf 'package_receipt_sha256=%s\n' "$(sha256_of "$PACKAGE_RECEIPT")"
    printf 'physical_gpu_index=%s\n' "$PHYSICAL_GPU_INDEX"
    printf 'gpu_uuid=%s\n' "$gpu_uuid"
    printf 'nvidia_smi=%s\n' "$gpu_info"
    printf 'cuda_preflight=%s\n' "$cuda_preflight"
    printf 'model_settings_sha256=%s\n' "$(sha256_of "$BASELINE/model_settings.txt")"
    printf 'checkpoint_sha256=%s\n' "$(sha256_of "$BASELINE/best_models/checkpoint_step_0.pt")"
    printf 'network_sha256=%s\n' "$(sha256_of "$BASELINE/best_models/trained_1NN_0.pt")"
    printf 'r001_steps_sha256=%s\n' "$(sha256_of "$REFERENCE_RESULT/original/steps.json")"
    printf 'started_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$PIDL_ARCHIVE_DIR/producer_preflight.txt"
cp "$PACKAGE_RECEIPT" "$PIDL_ARCHIVE_DIR/package_receipt.json"
cp "$PACKAGE_RUNTIME_MANIFEST" "$PIDL_ARCHIVE_DIR/reviewed_runtime_manifest.json"
cp "$TASKROOT/materialization_receipt.json" "$PIDL_ARCHIVE_DIR/materialization_receipt.json"

cd "$TASKROOT/code"
date -u +%Y-%m-%dT%H:%M:%SZ > "$TASKROOT/started_utc.txt"
set +e
timeout --signal=TERM --kill-after=10s 3500s /usr/bin/python3 -u \
    scripts/run_s04_e040_feasible_damage.py \
    --baseline "$BASELINE" \
    --reference-result "$REFERENCE_RESULT" \
    --output "$PIDL_ARCHIVE_DIR/results" \
    --source-commit "$REVIEWED_RUNTIME_COMMIT" \
    --step-seconds 240 \
    --total-seconds 3300 \
    --max-updates 10000
task_exit=$?
set -e
printf '%s\n' "$task_exit" > "$TASKROOT/exit_code.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$TASKROOT/finished_utc.txt"
exit "$task_exit"
