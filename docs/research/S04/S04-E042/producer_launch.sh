#!/bin/bash
# Execute the already materialized S04-E042 producer package exactly once.
#
# This is deliberately an *inner* launcher. The trusted bootstrap outside the
# tar verifies the user-pinned receipt, SHA-checks the tar, materializes a fresh
# code tree and checks this entrypoint before systemd starts this script. The
# checks below repeat the runtime-manifest and frozen-input checks immediately
# before CUDA work, so an altered tree cannot silently enter the calculation.
set -euo pipefail

readonly REVIEWED_RUNTIME_COMMIT=521c611fb2b24622df50ef5c2f4624b4abfed72d
readonly RECEIPT_SCHEMA=S04-E042-producer-package-receipt-v2
readonly RUNTIME_MANIFEST_SCHEMA=S04-E042-reviewed-runtime-manifest-v2
readonly MATERIALIZATION_SCHEMA=S04-E042-materialization-receipt-v1
readonly RUNTIME_DEPENDENCY_SCHEMA=S04-E042-runtime-dependency-receipt-v1
readonly ANALYSIS_IDENTITY_SCHEMA=S04-E042-analysis-identity-receipt-v1
readonly LAUNCH_RELATIVE_PATH=docs/research/S04/S04-E042/producer_launch.sh
readonly EXPECTED_MODEL_SETTINGS_SHA256=015fe8ddf563b2b9d81b8a681705e2a35f9044206311a6a7e26f40a7dc9c1047
readonly EXPECTED_CHECKPOINT_SHA256=aad4ebcb60a41caba6e0d2dbfaaba7cb7cb2ece631da8fbbfcaf3d374fc77aae
readonly EXPECTED_NETWORK_SHA256=09f1fc279007262b1068f0526e36e3aa2005633da271924cb598b7994ba8509a
readonly EXPECTED_R001_STEPS_SHA256=fd21fced6639591c1966e12c6ed5e7ec086403dc02d889ec49011c0d2524deec
readonly MAX_IDLE_MEMORY_MIB=64
readonly MAX_IDLE_UTILIZATION_PERCENT=2
# The CUDA/import check deliberately submits a tiny CUDA workload.  NVIDIA's
# utilization field is sampled over an interval and can report that completed
# work briefly after the Python preflight process has exited.  Only the
# utilization sample may settle; memory and compute-process checks remain
# immediate and strict throughout this bounded interval.
readonly POST_CUDA_PREFLIGHT_SETTLE_ATTEMPTS=3
readonly POST_CUDA_PREFLIGHT_SETTLE_SECONDS=1
readonly GMSHPARSER_SOURCE_ROOT=/home/drtao/.local/lib/python3.10/site-packages/gmshparser
readonly GMSHPARSER_DISTRIBUTION_VERSION=0.2.0
readonly GMSHPARSER_TREE_SHA256=8e7134569df830851a9ebfe741c7477e10efbc781bb8e5e76850078e6a64c4ba
readonly GMSHPARSER_SNAPSHOT_RELATIVE=runtime_deps/gmshparser
readonly GMSHPARSER_RECEIPT_FILE=runtime_dependency_receipt.json
readonly GMSHPARSER_FILES_JSON='[
  {"path":"__init__.py","bytes":377,"sha256":"2a629709d6c88040451f6974aa761495202770013050ca4b869179e25ff82f93"},
  {"path":"abstract_parser.py","bytes":1175,"sha256":"f7e155409652bbb029174d880cf6080d662d3bb7daf91c86fcc25ed463211ce7"},
  {"path":"cli.py","bytes":1320,"sha256":"44a6dfafbcd93ee4e8c8c78b967d749f019a89534b9dbaa889076dd34ae9dca2"},
  {"path":"element.py","bytes":580,"sha256":"2e7f18430beb0c5d1ced371165c63b806f7763d71da676ffe63c54c98a0f359f"},
  {"path":"element_entity.py","bytes":2151,"sha256":"851ea05778d72e42ba9aff1d1aa350f9dbdd7daae1b7293fdfa47b5f72ce473a"},
  {"path":"elements_parser.py","bytes":1570,"sha256":"64af3d687e7d4078fc1a45e77bd03aa17d9c7aace6a22afa6feb12b5cab33c7e"},
  {"path":"helpers.py","bytes":2248,"sha256":"3150914858ae05cd2055c97be83abfec567ef216921dba291acc72ca4bef7fe9"},
  {"path":"main_parser.py","bytes":903,"sha256":"e4e0820a59ba5051d5cc88c2f23d34023872a8faf70e95171fc8db7eb98a1f22"},
  {"path":"mesh.py","bytes":6234,"sha256":"7f4ac041b0f9209638a7fa0e0e69ebe557387be153a35644873762df9d6c34c3"},
  {"path":"mesh_format_parser.py","bytes":437,"sha256":"987600f30b3c410049ab4320c11e04b4acb3a9fda25facfd782be840e4a5c070"},
  {"path":"node.py","bytes":653,"sha256":"c4e15aef37ae5fdab96db94cc9f327a4d5cb3945df0a8dea943d74a1bdd38083"},
  {"path":"node_entity.py","bytes":1800,"sha256":"e1151da6e52e2fbadb1e59353002643817c75c9c78db87e7db81ada2a06f4af1"},
  {"path":"nodes_parser.py","bytes":1511,"sha256":"a360c95fc0f75ff8edc5539e2117c70bf24d8420cffa3780b720308b4241c60d"}
]'

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

# Unlike the ordinary environment prerequisites above, make a missing approval
# pin follow the wrapper's ordinary fail-closed exit-2 contract rather than
# Bash's parameter-expansion exit path.
PACKAGE_RECEIPT_SHA256="${PACKAGE_RECEIPT_SHA256:-}"

# The package and dependency verifiers use only the standard library.  Clear
# inherited Python path/home knobs before their first interpreter invocation;
# the controlled runtime path is installed below, immediately before CUDA.
unset PYTHONPATH PYTHONHOME PYTHONUSERBASE PYTHONSTARTUP
unset BASH_ENV ENV LD_PRELOAD LD_LIBRARY_PATH
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1

# Verification tools must come from the producer's verified system locations,
# not from the submitting shell's PATH.
export PATH=/usr/bin:/bin
umask 077

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

for required in sha256sum timeout nvidia-smi flock sleep /usr/bin/python3; do
    require_command "$required"
done

[[ "$RUN_ID" =~ ^pf_s04e042_projected_damage_[a-z0-9]+_[0-9]{8}T[0-9]{6}Z$ ]] ||
    fail "invalid S04-E042 run id: $RUN_ID"
[[ "$PHYSICAL_GPU_INDEX" =~ ^[0-9]+$ ]] ||
    fail "PHYSICAL_GPU_INDEX must be one physical GPU index"
[[ "$TASKROOT" == "/mnt/data2/drtao/wennie/$RUN_ID" ]] ||
    fail "TASKROOT does not match the approved run-id path"
[[ "$PIDL_ARCHIVE_DIR" == "/mnt/data2/drtao/pidl_archives/$RUN_ID" ]] ||
    fail "PIDL_ARCHIVE_DIR does not match the approved run-id path"
[[ -d "$TASKROOT/code" ]] || fail "missing materialized code directory"
[[ -f "$TASKROOT/materialization_receipt.json" ]] ||
    fail "missing bootstrap materialization receipt"
[[ -d "$TASKROOT/runtime_deps/gmshparser" ]] ||
    fail "missing bootstrap runtime dependency snapshot"
[[ -f "$TASKROOT/$GMSHPARSER_RECEIPT_FILE" ]] ||
    fail "missing bootstrap runtime dependency receipt"
[[ "$PACKAGE_RECEIPT_SHA256" =~ ^[0-9a-f]{64}$ ]] ||
    fail "invalid approval-card receipt SHA-256"
[[ ! -e "$PIDL_ARCHIVE_DIR" ]] ||
    fail "refusing non-fresh archive root: $PIDL_ARCHIVE_DIR"

# The package receipt, manifest and archive must be direct children of the
# same staged task root. Python validates the JSON schemas, runtime-file
# hashes, current entrypoint hash, and the bootstrap materialization receipt.
package_metadata="$(/usr/bin/python3 - \
    "$TASKROOT" "$PACKAGE_ARCHIVE" "$PACKAGE_RECEIPT" "$PACKAGE_RUNTIME_MANIFEST" \
    "$TASKROOT/materialization_receipt.json" "$REVIEWED_RUNTIME_COMMIT" \
    "$RECEIPT_SCHEMA" "$RUNTIME_MANIFEST_SCHEMA" "$MATERIALIZATION_SCHEMA" \
    "$LAUNCH_RELATIVE_PATH" "$PACKAGE_RECEIPT_SHA256" <<'PY'
import hashlib
import json
import os
import re
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

EXPECTED_E042_IMPORT_PROOF = {
    "module": "projected_damage",
    "symbol": "ReferenceBaseProjectedDamage",
    "module_path": "source/projected_damage.py",
    "runner_path": "scripts/run_s04_e042_projected_damage.py",
}


def validate_e042_import_proof(manifest: object, files: object) -> None:
    if not isinstance(manifest, dict) or not isinstance(files, list):
        fail("invalid E042 runtime manifest")
    proof = manifest.get("e042_import_proof")
    if not isinstance(proof, dict) or set(proof) != {*EXPECTED_E042_IMPORT_PROOF, "module_sha256"}:
        fail("missing or malformed E042 projected-damage import proof")
    if any(proof[key] != value for key, value in EXPECTED_E042_IMPORT_PROOF.items()):
        fail("E042 projected-damage import proof has unexpected identity")
    module_sha256 = proof["module_sha256"]
    if not isinstance(module_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", module_sha256):
        fail("E042 projected-damage import proof has invalid module SHA-256")
    matches = [
        item for item in files
        if isinstance(item, dict) and item.get("path") == EXPECTED_E042_IMPORT_PROOF["module_path"]
    ]
    if len(matches) != 1 or matches[0].get("sha256") != module_sha256:
        fail("E042 projected-damage import proof is not bound to runtime manifest")

def private_directory(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_dir():
        fail(f"{label} is not a regular directory")
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
        fail(f"{label} is not private to the submitting account")


def sealed_tree(path: Path, label: str) -> None:
    pending = [path]
    while pending:
        candidate = pending.pop()
        if candidate.is_symlink():
            fail(f"{label} contains a symlink")
        try:
            metadata = candidate.stat()
        except OSError as error:
            fail(f"could not stat {label}: {error}")
        if metadata.st_uid != os.getuid():
            fail(f"{label} is not owned by the submitting account")
        if metadata.st_mode & 0o222:
            fail(f"{label} contains a writable path")
        if stat.S_ISDIR(metadata.st_mode):
            try:
                pending.extend(candidate.iterdir())
            except OSError as error:
                fail(f"could not read {label}: {error}")
        elif not stat.S_ISREG(metadata.st_mode):
            fail(f"{label} contains a non-regular path")


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
reviewed_commit, receipt_schema, manifest_schema, materialization_schema, entrypoint, pinned_receipt = sys.argv[6:]
if not root.is_dir():
    fail("task root is missing")
private_directory(root, "task root")
for path, label in ((archive, "archive"), (receipt_path, "receipt"),
                    (manifest_path, "runtime manifest"),
                    (materialization_path, "materialization receipt")):
    if path.parent != root or not path.is_file():
        fail(f"{label} is not a regular direct child of task root")
if not re.fullmatch(r"[0-9a-f]{64}", pinned_receipt):
    fail("invalid approval-card receipt SHA-256")
if digest(receipt_path) != pinned_receipt:
    fail("package receipt does not match approval-card SHA-256")
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
sealed_tree(code, "materialized code tree")
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
validate_e042_import_proof(manifest, files)
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

# The bootstrap's receipt is bound to the checked package receipt. Recompute the
# full 13-file lock here, before frozen inputs or CUDA are considered.
dependency_metadata="$(/usr/bin/python3 - \
    "$TASKROOT" "$TASKROOT/$GMSHPARSER_SNAPSHOT_RELATIVE" "$TASKROOT/$GMSHPARSER_RECEIPT_FILE" \
    "$PACKAGE_RECEIPT" "$RUNTIME_DEPENDENCY_SCHEMA" "$GMSHPARSER_SOURCE_ROOT" \
    "$GMSHPARSER_DISTRIBUTION_VERSION" "$GMSHPARSER_TREE_SHA256" \
    "$GMSHPARSER_SNAPSHOT_RELATIVE" "$GMSHPARSER_FILES_JSON" <<'PY'
import hashlib
import json
import os
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
    raise SystemExit(f"runtime dependency verification failed: {message}")


def read_only_directory(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_dir():
        fail(f"{label} is not a regular directory")
    metadata = path.stat()
    if metadata.st_uid != os.getuid():
        fail(f"{label} is not owned by the submitting account")
    if metadata.st_mode & 0o222:
        fail(f"{label} is writable")


raw_root = Path(sys.argv[1])
raw_snapshot = Path(sys.argv[2])
raw_dependency_receipt = Path(sys.argv[3])
raw_package_receipt = Path(sys.argv[4])
schema, source_root, distribution_version, expected_tree, snapshot_relative, raw_manifest = sys.argv[5:]
if any(path.is_symlink() for path in (raw_root, raw_snapshot, raw_dependency_receipt, raw_package_receipt)):
    fail("task root, snapshot, or receipt must not be a symlink")
if not raw_root.is_dir():
    fail("task root is missing")
root = raw_root.resolve()
snapshot = raw_snapshot.resolve()
dependency_receipt_path = raw_dependency_receipt.resolve()
package_receipt_path = raw_package_receipt.resolve()
if (not snapshot.is_dir() or snapshot.resolve() != root / snapshot_relative
        or snapshot.parent != root / "runtime_deps"):
    fail("snapshot is not the expected task-root dependency directory")
read_only_directory(root / "runtime_deps", "runtime dependency parent")
read_only_directory(snapshot, "runtime dependency snapshot")
for path, label in ((dependency_receipt_path, "dependency receipt"), (package_receipt_path, "package receipt")):
    if path.parent != root or not path.is_file():
        fail(f"{label} is not a regular direct child of task root")
try:
    files = json.loads(raw_manifest)
    dependency_receipt = json.loads(dependency_receipt_path.read_text())
except (OSError, json.JSONDecodeError) as error:
    fail(f"unreadable dependency metadata: {error}")
if not isinstance(files, list) or not files:
    fail("embedded dependency manifest is empty")
expected_paths: set[str] = set()
for item in files:
    if not isinstance(item, dict) or set(item) != {"path", "bytes", "sha256"}:
        fail("invalid embedded dependency-manifest entry")
    relative = item["path"]
    if (not isinstance(relative, str) or not relative or Path(relative).name != relative
            or relative in expected_paths):
        fail("unsafe or duplicate embedded dependency path")
    if not isinstance(item["bytes"], int) or item["bytes"] < 1:
        fail("invalid embedded dependency byte count")
    if not isinstance(item["sha256"], str) or len(item["sha256"]) != 64:
        fail("invalid embedded dependency SHA-256")
    expected_paths.add(relative)
expected_receipt = {
    "schema": schema,
    "package_receipt_sha256": digest(package_receipt_path),
    "source_root": source_root,
    "distribution_name": "gmshparser",
    "distribution_version": distribution_version,
    "snapshot_relative_path": snapshot_relative,
    "canonical_tree_sha256": expected_tree,
    "files": files,
}
if dependency_receipt != expected_receipt:
    fail("dependency receipt does not bind the checked package and locked source")

canonical = hashlib.sha256()
actual_paths = set()
for candidate in snapshot.iterdir():
    if candidate.is_symlink() or not candidate.is_file() or not stat.S_ISREG(candidate.stat().st_mode):
        fail("snapshot contains a non-regular file")
    metadata = candidate.stat()
    if metadata.st_uid != os.getuid() or metadata.st_mode & 0o222:
        fail("snapshot contains an unsealed file")
    actual_paths.add(candidate.name)
if actual_paths != expected_paths:
    fail("snapshot file set differs from lock")
for item in sorted(files, key=lambda value: value["path"]):
    relative = item["path"]
    candidate = snapshot / relative
    if candidate.is_symlink() or not candidate.is_file() or not stat.S_ISREG(candidate.stat().st_mode):
        fail(f"snapshot dependency file is missing or unsafe: {relative}")
    metadata = candidate.stat()
    if metadata.st_uid != os.getuid() or metadata.st_mode & 0o222:
        fail(f"snapshot dependency file is not sealed: {relative}")
    if candidate.stat().st_size != item["bytes"] or digest(candidate) != item["sha256"]:
        fail(f"snapshot dependency file differs from lock: {relative}")
    canonical.update(
        f"gmshparser/{relative}\0{item['bytes']}\0{item['sha256']}\n".encode("utf-8")
    )
if canonical.hexdigest() != expected_tree:
    fail("snapshot canonical tree SHA-256 differs from lock")
print(f"runtime_dependency_tree_sha256={expected_tree}")
print(f"runtime_dependency_receipt_sha256={digest(dependency_receipt_path)}")
print(f"runtime_dependency_files_verified={len(files)}")
PY
)" || fail "runtime dependency verification command failed"

assert_sha256 "$BASELINE/model_settings.txt" "$EXPECTED_MODEL_SETTINGS_SHA256"
assert_sha256 "$BASELINE/best_models/checkpoint_step_0.pt" "$EXPECTED_CHECKPOINT_SHA256"
assert_sha256 "$BASELINE/best_models/trained_1NN_0.pt" "$EXPECTED_NETWORK_SHA256"
assert_sha256 "$REFERENCE_RESULT/original/steps.json" "$EXPECTED_R001_STEPS_SHA256"

refresh_gpu_telemetry() {
    gpu_info="$(nvidia-smi --id="$PHYSICAL_GPU_INDEX" \
        --query-gpu=index,uuid,name,memory.used,utilization.gpu,driver_version \
        --format=csv,noheader,nounits 2>&1)" ||
        fail "could not query physical GPU $PHYSICAL_GPU_INDEX: $gpu_info"
    IFS=',' read -r reported_index gpu_uuid gpu_name gpu_memory_used gpu_utilization gpu_driver <<< "$gpu_info"
    for variable in reported_index gpu_uuid gpu_name gpu_memory_used gpu_utilization gpu_driver; do
        value="${!variable//[[:space:]]/}"
        printf -v "$variable" '%s' "$value"
    done
    [[ "$reported_index" == "$PHYSICAL_GPU_INDEX" && "$gpu_uuid" == GPU-* ]] ||
        fail "could not resolve selected physical GPU UUID"
    [[ "$gpu_memory_used" =~ ^[0-9]+$ && "$gpu_utilization" =~ ^[0-9]+$ ]] ||
        fail "selected GPU did not report numeric idle telemetry"
}

refresh_gpu_telemetry
selected_gpu_uuid="$gpu_uuid"

# Compatibility lock: E040 already used this exact physical-GPU lock namespace.
# Keeping it prevents a new E042 service from racing an E040 service on the
# same device, while RunID, task root, archive schema, and systemd unit remain
# E042-specific.
lock_dir=/mnt/data2/drtao/wennie/.s04-e040-gpu-locks
mkdir -p "$lock_dir"
exec 9>"$lock_dir/$gpu_uuid.lock"
flock -n 9 || fail "selected GPU $PHYSICAL_GPU_INDEX is reserved by another S04 physical-GPU launcher"

assert_no_selected_gpu_compute_process() {
    local stage="$1"
    local apps
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

assert_gpu_quiescent() {
    local stage="$1"
    (( gpu_memory_used <= MAX_IDLE_MEMORY_MIB )) ||
        fail "selected GPU has ${gpu_memory_used} MiB in use at $stage"
    assert_no_selected_gpu_compute_process "$stage"
    (( gpu_utilization <= MAX_IDLE_UTILIZATION_PERCENT )) ||
        fail "selected GPU has ${gpu_utilization}% utilization at $stage"
}

assert_gpu_quiescent before_cuda_preflight
export CUDA_VISIBLE_DEVICES="$gpu_uuid"
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export PYTHONPATH="$TASKROOT/runtime_deps:$TASKROOT/code/source:$TASKROOT/code/SENS_tensile"
cuda_preflight="$(
    cd "$TASKROOT/code"
    /usr/bin/python3 - <<'PY'
import importlib.util
import json
import os
import sys
from pathlib import Path

import gmshparser
import numpy
import torch
import tqdm

root = Path.cwd().resolve()
source_root = root / "source"
sens_root = root / "SENS_tensile"
dependency_root = Path(os.environ["TASKROOT"]).resolve() / "runtime_deps" / "gmshparser"
gmshparser_path = Path(gmshparser.__file__).resolve()
assert gmshparser_path == dependency_root / "__init__.py" and dependency_root in gmshparser_path.parents, (
    f"gmshparser was not imported from the locked snapshot: {gmshparser_path}"
)
spec = importlib.util.spec_from_file_location("s04_e042_runner", root / "scripts" / "run_s04_e042_projected_damage.py")
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load E042 runner")
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)
import projected_damage

assert torch.cuda.is_available(), "CUDA unavailable"
assert torch.cuda.device_count() == 1, "selected GPU was not isolated"
assert torch.cuda.get_device_name(0) == "NVIDIA GeForce RTX 4090", "unexpected GPU"
for module_name in ("projected_damage", "compute_energy", "field_computation", "construct_model"):
    module_path = Path(sys.modules[module_name].__file__).resolve()
    assert source_root in module_path.parents or sens_root in module_path.parents, (
        f"foreign import for {module_name}: {module_path}"
    )
projected_damage_path = Path(projected_damage.__file__).resolve()
assert projected_damage_path == source_root / "projected_damage.py", (
    f"projected_damage was not imported from the checked runtime: {projected_damage_path}"
)
assert getattr(runner, "ReferenceBaseProjectedDamage", None) is projected_damage.ReferenceBaseProjectedDamage, (
    "E042 runner did not bind ReferenceBaseProjectedDamage from the checked projected_damage module"
)
probe = torch.ones(1, device="cuda")
torch.cuda.synchronize()
assert float(probe.item()) == 1.0
print(json.dumps({
    "torch": torch.__version__,
    "torch_cuda": torch.version.cuda,
    "numpy": numpy.__version__,
    "tqdm": tqdm.__version__,
    "gpu": torch.cuda.get_device_name(0),
    "gmshparser": str(gmshparser_path),
    "runner": str(Path(runner.__file__).resolve()),
    "projected_damage": str(projected_damage_path),
    "damage_carrier": "ReferenceBaseProjectedDamage",
}))
PY
)" || fail "CUDA/import preflight failed"

# Re-query after the CUDA subprocess exits.  Its just-completed kernel can
# occupy the driver's utilization sampling window, so retry that field for at
# most three seconds.  Every snapshot still rejects extra memory or a compute
# process, and entering the runner still requires the original low-utilization
# threshold.
post_preflight_attempt=0
while :; do
    refresh_gpu_telemetry
    [[ "$gpu_uuid" == "$selected_gpu_uuid" ]] ||
        fail "selected GPU identity changed during preflight"
    (( gpu_memory_used <= MAX_IDLE_MEMORY_MIB )) ||
        fail "selected GPU has ${gpu_memory_used} MiB in use at before_runner"
    assert_no_selected_gpu_compute_process before_runner
    (( gpu_utilization <= MAX_IDLE_UTILIZATION_PERCENT )) && break
    (( post_preflight_attempt < POST_CUDA_PREFLIGHT_SETTLE_ATTEMPTS )) ||
        fail "selected GPU has ${gpu_utilization}% utilization after ${POST_CUDA_PREFLIGHT_SETTLE_ATTEMPTS}s post-preflight cooldown"
    sleep "$POST_CUDA_PREFLIGHT_SETTLE_SECONDS"
    (( post_preflight_attempt += 1 ))
done

mkdir "$PIDL_ARCHIVE_DIR"
mkdir "$PIDL_ARCHIVE_DIR/runtime_deps"
cp "$TASKROOT/$GMSHPARSER_RECEIPT_FILE" "$PIDL_ARCHIVE_DIR/$GMSHPARSER_RECEIPT_FILE"
cp -R "$TASKROOT/runtime_deps/gmshparser" "$PIDL_ARCHIVE_DIR/runtime_deps/gmshparser"
export TMPDIR="$TASKROOT/tmp"
export XDG_CACHE_HOME="$TASKROOT/cache"
export TORCH_EXTENSIONS_DIR="$TASKROOT/.jitcache"
export MPLCONFIGDIR="$TASKROOT/cache/matplotlib"
export OMP_NUM_THREADS=4
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME" "$TORCH_EXTENSIONS_DIR" "$MPLCONFIGDIR"

{
    printf '%s\n' 'schema=S04-E042-producer-preflight-v2'
    printf 'run_id=%s\n' "$RUN_ID"
    printf 'reviewed_runtime_commit=%s\n' "$REVIEWED_RUNTIME_COMMIT"
    printf '%s\n' "$package_metadata"
    printf '%s\n' "$dependency_metadata"
    printf 'package_receipt_sha256=%s\n' "$(sha256_of "$PACKAGE_RECEIPT")"
    printf 'physical_gpu_index=%s\n' "$PHYSICAL_GPU_INDEX"
    printf 'gpu_uuid=%s\n' "$gpu_uuid"
    printf 'nvidia_smi=%s\n' "$gpu_info"
    printf 'post_cuda_preflight_settle_attempts=%s\n' "$post_preflight_attempt"
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

# The post-run analyzer admits an archive only through this create-once,
# read-only identity receipt. It binds the runtime closure and preflight to the
# exact history-timing regime; the numerical runner itself remains unchanged.
analysis_identity_receipt="$PIDL_ARCHIVE_DIR/analysis_identity_receipt.json"
[[ ! -e "$analysis_identity_receipt" ]] || fail "analysis identity receipt already exists"
/usr/bin/python3 - \
    "$analysis_identity_receipt" "$PACKAGE_RECEIPT" "$PACKAGE_RUNTIME_MANIFEST" \
    "$TASKROOT/materialization_receipt.json" "$PIDL_ARCHIVE_DIR/producer_preflight.txt" \
    "$BASELINE/model_settings.txt" "$BASELINE/best_models/checkpoint_step_0.pt" \
    "$BASELINE/best_models/trained_1NN_0.pt" "$REFERENCE_RESULT/original/steps.json" \
    "$TASKROOT/code/scripts/run_s04_e042_projected_damage.py" \
    "$RUN_ID" "$REVIEWED_RUNTIME_COMMIT" "$ANALYSIS_IDENTITY_SCHEMA" <<'PY'
import hashlib
import json
import os
import re
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
    raise SystemExit(f"analysis identity receipt failed: {message}")


def regular_file(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        fail(f"{label} is not a regular file")


arguments = sys.argv[1:]
if len(arguments) != 13:
    fail("wrong identity-receipt argument count")
(
    raw_target,
    raw_package_receipt,
    raw_manifest,
    raw_materialization,
    raw_preflight,
    raw_settings,
    raw_checkpoint,
    raw_network,
    raw_reference_steps,
    raw_runner,
) = map(Path, arguments[:10])
run_id, reviewed_runtime_commit, schema = arguments[10:]
for path, label in (
    (raw_package_receipt, "package receipt"),
    (raw_manifest, "runtime manifest"),
    (raw_materialization, "materialization receipt"),
    (raw_preflight, "producer preflight"),
    (raw_settings, "model settings"),
    (raw_checkpoint, "checkpoint"),
    (raw_network, "network"),
    (raw_reference_steps, "reference steps"),
    (raw_runner, "E042 runner"),
):
    regular_file(path, label)
if raw_target.is_symlink() or raw_target.exists() or raw_target.parent != raw_preflight.parent:
    fail("identity receipt target is unsafe")
if not re.fullmatch(r"pf_s04e042_projected_damage_[a-z0-9]+_[0-9]{8}T[0-9]{6}Z", run_id):
    fail("invalid E042 run id")
if not re.fullmatch(r"[0-9a-f]{40}", reviewed_runtime_commit):
    fail("invalid reviewed runtime commit")
try:
    receipt = json.loads(raw_package_receipt.read_text())
    manifest = json.loads(raw_manifest.read_text())
    materialization = json.loads(raw_materialization.read_text())
except (OSError, json.JSONDecodeError) as error:
    fail(f"could not read package linkage: {error}")
if receipt.get("reviewed_runtime_commit") != reviewed_runtime_commit:
    fail("package receipt reviewed runtime does not match identity")
if manifest.get("reviewed_runtime_commit") != reviewed_runtime_commit:
    fail("runtime manifest reviewed runtime does not match identity")
if not isinstance(receipt.get("package_commit"), str) or not re.fullmatch(r"[0-9a-f]{40}", receipt["package_commit"]):
    fail("invalid package commit")
manifest_sha = digest(raw_manifest)
package_receipt_sha = digest(raw_package_receipt)
materialization_sha = digest(raw_materialization)
if receipt.get("runtime_manifest_sha256") != manifest_sha:
    fail("package receipt does not bind runtime manifest")
expected_materialization = {
    "package_receipt_sha256": package_receipt_sha,
    "archive_sha256": receipt.get("archive_sha256"),
    "runtime_manifest_sha256": manifest_sha,
    "package_commit": receipt.get("package_commit"),
}
if any(materialization.get(key) != value for key, value in expected_materialization.items()):
    fail("materialization receipt does not bind package identity")
files = manifest.get("files")
proof = manifest.get("e042_import_proof")
expected_proof = {
    "module": "projected_damage",
    "symbol": "ReferenceBaseProjectedDamage",
    "module_path": "source/projected_damage.py",
    "runner_path": "scripts/run_s04_e042_projected_damage.py",
}
if not isinstance(files, list) or not isinstance(proof, dict):
    fail("runtime manifest lacks E042 import proof")
if set(proof) != {*expected_proof, "module_sha256"} or any(
    proof.get(key) != value for key, value in expected_proof.items()
):
    fail("runtime manifest has wrong E042 import proof")
manifest_by_path = {
    item.get("path"): item
    for item in files
    if isinstance(item, dict) and set(item) == {"path", "bytes", "sha256"}
}
projected_item = manifest_by_path.get("source/projected_damage.py")
runner_item = manifest_by_path.get("scripts/run_s04_e042_projected_damage.py")
if not isinstance(projected_item, dict) or not isinstance(runner_item, dict):
    fail("runtime manifest omits E042 carrier or runner")
if proof.get("module_sha256") != projected_item.get("sha256"):
    fail("E042 import proof is not bound to projected_damage runtime hash")
if digest(raw_runner) != runner_item.get("sha256"):
    fail("materialized E042 runner differs from runtime manifest")
runner_source = raw_runner.read_text(encoding="utf-8")
history_tokens = (
    'checkpoint["history_driver_mode"] == "current_active"',
    'not checkpoint["lagged_stiffness_enabled"]',
    "if not can_prepare_acceptance:",
    "publish_pointer_last(",
)
if any(token not in runner_source for token in history_tokens):
    fail("reviewed runner does not expose required E042 history transaction contract")
settings_sha = digest(raw_settings)
checkpoint_sha = digest(raw_checkpoint)
network_sha = digest(raw_network)
reference_steps_sha = digest(raw_reference_steps)
preflight = raw_preflight.read_text(encoding="utf-8")
required_preflight_lines = {
    "schema": "S04-E042-producer-preflight-v2",
    "reviewed_runtime_commit": reviewed_runtime_commit,
    "package_receipt_sha256": package_receipt_sha,
    "runtime_manifest_sha256": manifest_sha,
    "model_settings_sha256": settings_sha,
    "checkpoint_sha256": checkpoint_sha,
    "network_sha256": network_sha,
    "r001_steps_sha256": reference_steps_sha,
}
preflight_values: dict[str, str] = {}
for line in preflight.splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        preflight_values.setdefault(key, value)
if any(preflight_values.get(key) != value for key, value in required_preflight_lines.items()):
    fail("producer preflight does not bind analysis identity")
payload = {
    "schema": schema,
    "run_id": run_id,
    "sealed": {"mode": "create_once_0444", "archive_root_file": raw_target.name},
    "runtime": {
        "reviewed_runtime_commit": reviewed_runtime_commit,
        "package_commit": receipt["package_commit"],
        "package_receipt_sha256": package_receipt_sha,
        "runtime_manifest_sha256": manifest_sha,
        "materialization_receipt_sha256": materialization_sha,
        "runner_path": "scripts/run_s04_e042_projected_damage.py",
        "runner_sha256": digest(raw_runner),
        "e042_import_proof": proof,
    },
    "preflight": {
        "file": raw_preflight.name,
        "sha256": digest(raw_preflight),
        "schema": required_preflight_lines["schema"],
    },
    "frozen_inputs": {
        "model_settings_sha256": settings_sha,
        "checkpoint_sha256": checkpoint_sha,
        "network_sha256": network_sha,
        "r001_steps_sha256": reference_steps_sha,
    },
    "history_timing": {
        "history_driver_mode": "current_active",
        "lagged_stiffness_enabled": False,
        "transaction_boundary": "accepted_only",
        "transactions_per_physical_step": 1,
        "commit_mechanism": "pointer_last_after_accepted_candidate_bundle",
        "runner_contract_tokens": list(history_tokens),
    },
    "result_linkage": {
        "state": "pre_run_identity_only",
        "completion_receipt": "analysis_result_linkage_receipt.json",
        "completion_condition": "written only after runner exit code 0 and result-file hash checks",
    },
}
rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
fd = os.open(raw_target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
with os.fdopen(fd, "w", encoding="utf-8") as handle:
    handle.write(rendered)
    handle.flush()
    os.fsync(handle.fileno())
os.chmod(raw_target, 0o444)
if raw_target.stat().st_mode & 0o222:
    fail("could not seal analysis identity receipt")
directory_fd = os.open(raw_target.parent, os.O_RDONLY)
try:
    os.fsync(directory_fd)
finally:
    os.close(directory_fd)
print(f"analysis_identity_receipt_sha256={digest(raw_target)}")
PY

cd "$TASKROOT/code"
date -u +%Y-%m-%dT%H:%M:%SZ > "$TASKROOT/started_utc.txt"
set +e
timeout --signal=TERM --kill-after=10s 3500s /usr/bin/python3 -u \
    scripts/run_s04_e042_projected_damage.py \
    --baseline "$BASELINE" \
    --reference-result "$REFERENCE_RESULT" \
    --output "$PIDL_ARCHIVE_DIR/results" \
    --source-commit "$REVIEWED_RUNTIME_COMMIT" \
    --step-seconds 240 \
    --total-seconds 3300 \
    --max-updates 10000
task_exit=$?
set -e
if (( task_exit == 0 )); then
    # Result hashes are deliberately emitted only after the runner has returned
    # normally. The analyzer checks this receipt *and* the pre-run identity;
    # neither receipt substitutes for the other.
    result_linkage_receipt="$PIDL_ARCHIVE_DIR/analysis_result_linkage_receipt.json"
    [[ ! -e "$result_linkage_receipt" ]] || fail "analysis result linkage receipt already exists"
    if ! /usr/bin/python3 - \
        "$result_linkage_receipt" "$PIDL_ARCHIVE_DIR/analysis_identity_receipt.json" \
        "$PIDL_ARCHIVE_DIR/producer_preflight.txt" "$PIDL_ARCHIVE_DIR/results" \
        "$RUN_ID" "$REVIEWED_RUNTIME_COMMIT" <<'PY'
import hashlib
import json
import os
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
    raise SystemExit(f"analysis result linkage receipt failed: {message}")


def regular_file(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        fail(f"{label} is not a regular file")


target, identity_path, preflight_path, results_root = map(Path, sys.argv[1:5])
run_id, reviewed_runtime_commit = sys.argv[5:]
if (target.is_symlink() or target.exists() or results_root.is_symlink() or not results_root.is_dir()
        or target.parent != results_root.parent):
    fail("result-linkage target or results root is unsafe")
for path, label in ((identity_path, "analysis identity receipt"), (preflight_path, "producer preflight")):
    regular_file(path, label)
if identity_path.stat().st_mode & 0o222:
    fail("analysis identity receipt is not sealed")
try:
    identity = json.loads(identity_path.read_text())
except (OSError, json.JSONDecodeError) as error:
    fail(f"could not read analysis identity receipt: {error}")
if identity.get("schema") != "S04-E042-analysis-identity-receipt-v1" or identity.get("run_id") != run_id:
    fail("analysis identity receipt does not match this E042 run")
if identity.get("runtime", {}).get("reviewed_runtime_commit") != reviewed_runtime_commit:
    fail("analysis identity receipt reviewed runtime mismatch")
if identity.get("result_linkage", {}).get("state") != "pre_run_identity_only":
    fail("analysis identity receipt is not a pre-run identity")
preflight_sha = digest(preflight_path)
if identity.get("preflight", {}).get("sha256") != preflight_sha:
    fail("analysis identity receipt does not bind producer preflight")
expected = {
    "manifest.json": results_root / "manifest.json",
    "mesh.npz": results_root / "mesh.npz",
    "projected_damage/steps.json": results_root / "projected_damage" / "steps.json",
    "projected_damage/accepted_state_pointer.json": results_root / "projected_damage" / "accepted_state_pointer.json",
    "projected_damage/summary.json": results_root / "projected_damage" / "summary.json",
    "results.json": results_root / "results.json",
    "completed.json": results_root / "completed.json",
}
for relative, path in expected.items():
    regular_file(path, f"result file {relative}")
try:
    manifest = json.loads(expected["manifest.json"].read_text())
    steps = json.loads(expected["projected_damage/steps.json"].read_text())
    summary = json.loads(expected["projected_damage/summary.json"].read_text())
    completed = json.loads(expected["completed.json"].read_text())
except (OSError, json.JSONDecodeError) as error:
    fail(f"could not parse result metadata: {error}")
if manifest.get("experiment") != "S04-E042" or manifest.get("source_commit") != reviewed_runtime_commit:
    fail("result manifest does not match E042 reviewed runtime")
if not isinstance(steps, list) or not isinstance(summary, dict) or not isinstance(completed, dict):
    fail("result metadata has wrong structural type")
if completed.get("execution") != "runner_finished":
    fail("completed metadata does not report normal runner finish")
files = {
    relative: {"sha256": digest(path), "bytes": path.stat().st_size}
    for relative, path in expected.items()
}
payload = {
    "schema": "S04-E042-analysis-result-linkage-receipt-v2",
    "run_id": run_id,
    "sealed": {"mode": "create_once_0444", "archive_root_file": target.name},
    "pre_run_identity_receipt_sha256": digest(identity_path),
    "producer_preflight_sha256": preflight_sha,
    "runner_exit_code": 0,
    "result_files": files,
    "result_summary": {
        "outcome": summary.get("outcome"),
        "steps_attempted": summary.get("steps_attempted"),
        "steps_accepted": summary.get("steps_accepted"),
        "completed_three_cycles": summary.get("completed_three_cycles"),
        "completed_outcome": completed.get("outcome"),
    },
}
rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
with os.fdopen(fd, "w", encoding="utf-8") as handle:
    handle.write(rendered)
    handle.flush()
    os.fsync(handle.fileno())
os.chmod(target, 0o444)
if target.stat().st_mode & 0o222:
    fail("could not seal analysis result linkage receipt")
directory_fd = os.open(target.parent, os.O_RDONLY)
try:
    os.fsync(directory_fd)
finally:
    os.close(directory_fd)
print(f"analysis_result_linkage_receipt_sha256={digest(target)}")
PY
    then
        task_exit=2
    fi
fi
printf '%s\n' "$task_exit" > "$TASKROOT/exit_code.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$TASKROOT/finished_utc.txt"
exit "$task_exit"
