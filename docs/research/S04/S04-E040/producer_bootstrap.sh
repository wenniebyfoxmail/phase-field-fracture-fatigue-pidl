#!/bin/bash
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
readonly RUNTIME_DEPENDENCY_SCHEMA=S04-E040-runtime-dependency-receipt-v1
readonly LAUNCH_RELATIVE_PATH=docs/research/S04/S04-E040/producer_launch.sh
readonly BOOTSTRAP_FILE=producer_bootstrap.sh
readonly SYSTEMD_TIMEOUT_SECONDS=3600
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
: "${PHYSICAL_GPU_INDEX:?set PHYSICAL_GPU_INDEX to the selected physical GPU index}"
: "${BASELINE:?set BASELINE to the frozen Umax=0.12 recovery archive}"
: "${REFERENCE_RESULT:?set REFERENCE_RESULT to the completed S04-E037-R001 results directory}"
: "${PACKAGE_ARCHIVE:?set PACKAGE_ARCHIVE to the uploaded tar in TASKROOT}"
: "${PACKAGE_RECEIPT:?set PACKAGE_RECEIPT to the uploaded receipt in TASKROOT}"
: "${PACKAGE_RUNTIME_MANIFEST:?set PACKAGE_RUNTIME_MANIFEST to the uploaded runtime manifest in TASKROOT}"

fail() {
    printf '%s\n' "$*" >&2
    exit 2
}

# Keep an absent approval-card pin on the same explicit fail-closed exit-2
# path as an invalid or mismatched pin.
PACKAGE_RECEIPT_SHA256="${PACKAGE_RECEIPT_SHA256:-}"

# The bootstrap verifier must not inherit Python module/home configuration from
# the submitting shell.  Its dependency metadata lookup uses an explicit
# locked site-packages directory, so user-site discovery remains unnecessary.
unset PYTHONPATH PYTHONHOME PYTHONUSERBASE PYTHONSTARTUP TAR_OPTIONS
unset BASH_ENV ENV LD_PRELOAD LD_LIBRARY_PATH
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1

# Materialization and receipt tools must not be resolved from a caller-supplied
# PATH.  These system locations were verified on the approved producer.
export PATH=/usr/bin:/bin
umask 077

require_command() {
    command -v "$1" >/dev/null 2>&1 || fail "required command unavailable: $1"
}

seal_materialized_tree() {
    local tree="$1"
    [[ -d "$tree" && ! -L "$tree" ]] || fail "materialized code tree is unsafe: $tree"
    if find "$tree" -type l -print -quit | grep -q .; then
        fail "materialized code tree contains a symlink"
    fi
    find "$tree" -type d -exec chmod a-w {} + ||
        fail "could not seal materialized code directories"
    find "$tree" -type f -exec chmod a-w {} + ||
        fail "could not seal materialized code files"
}

for required in sha256sum tar git find grep chmod systemd-run systemctl /usr/bin/python3; do
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
[[ ! -e "$TASKROOT/runtime_deps" ]] || fail "refusing pre-existing runtime dependency snapshot"
[[ ! -e "$TASKROOT/$GMSHPARSER_RECEIPT_FILE" ]] || fail "refusing pre-existing runtime dependency receipt"
[[ ! -e "$PIDL_ARCHIVE_DIR" ]] || fail "refusing non-fresh archive root: $PIDL_ARCHIVE_DIR"
[[ "$PACKAGE_RECEIPT_SHA256" =~ ^[0-9a-f]{64}$ ]] || fail "invalid pinned receipt SHA-256"

# Establish the private staging parent before looking at any uploaded sidecar.
# A group-writable staging directory is acceptable only until this owner check
# and immediate 0700 conversion; package authentication never reads through it
# while it remains shared.
/usr/bin/python3 - "$TASKROOT" <<'PY'
import os
import stat
import sys
from pathlib import Path


root = Path(sys.argv[1])
if root.is_symlink() or not root.is_dir():
    raise SystemExit("bootstrap staging verification failed: task root is not a regular directory")
metadata = root.stat()
if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid():
    raise SystemExit("bootstrap staging verification failed: task root is not owned by the submitting account")
PY
chmod 700 "$TASKROOT" || fail "could not make task root private"

submission_metadata="$(/usr/bin/python3 - \
    "$TASKROOT" "$PACKAGE_ARCHIVE" "$PACKAGE_RECEIPT" "$PACKAGE_RUNTIME_MANIFEST" \
    "${BASH_SOURCE[0]}" "$PACKAGE_RECEIPT_SHA256" "$REVIEWED_RUNTIME_COMMIT" \
    "$RECEIPT_SCHEMA" "$RUNTIME_MANIFEST_SCHEMA" "$LAUNCH_RELATIVE_PATH" "$BOOTSTRAP_FILE" <<'PY'
import hashlib
import json
import os
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
if root.stat().st_uid != os.getuid():
    fail("task root is not owned by the submitting account")
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
print(f"archive_bytes={receipt['archive_bytes']}")
print(f"runtime_manifest_sha256={receipt['runtime_manifest_sha256']}")
print(f"runtime_files_expected={len(files)}")
PY
)" || fail "bootstrap sidecar verification failed"

receipt_archive_sha256="$(sed -n 's/^archive_sha256=//p' <<< "$submission_metadata")"
receipt_archive_bytes="$(sed -n 's/^archive_bytes=//p' <<< "$submission_metadata")"
[[ "$receipt_archive_sha256" =~ ^[0-9a-f]{64}$ ]] ||
    fail "bootstrap metadata did not return one archive SHA-256"
[[ "$receipt_archive_bytes" =~ ^[1-9][0-9]*$ ]] ||
    fail "bootstrap metadata did not return one positive archive byte count"

# Freeze the byte stream that passed the staged-receipt check.  Later commit
# inspection and extraction must never reopen the mutable upload path.
frozen_archive=""
cleanup_frozen_archive() {
    local path="${frozen_archive:-}"
    [[ -z "$path" || ! -e "$path" ]] || /bin/rm -f -- "$path" || true
}
trap cleanup_frozen_archive EXIT
frozen_archive="$TASKROOT/.verified-package-${RUN_ID}-$$.tar"
frozen_archive_metadata="$(/usr/bin/python3 - \
    "$PACKAGE_ARCHIVE" "$frozen_archive" "$receipt_archive_bytes" "$receipt_archive_sha256" <<'PY'
import hashlib
import os
import stat
import sys
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(f"frozen package archive verification failed: {message}")


source = Path(sys.argv[1])
target = Path(sys.argv[2])
try:
    expected_bytes = int(sys.argv[3])
except ValueError:
    fail("expected byte count is invalid")
expected_digest = sys.argv[4]
if expected_bytes < 1 or len(expected_digest) != 64:
    fail("expected archive lock is invalid")
if source.is_symlink() or not source.is_file():
    fail("staged archive is not a regular non-symlink file")
if target.parent != source.parent or target.exists() or target.is_symlink():
    fail("private archive target is unsafe or already exists")

digest = hashlib.sha256()
total = 0
try:
    with source.open("rb") as input_handle:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as output_handle:
            while True:
                block = input_handle.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                digest.update(block)
                output_handle.write(block)
            output_handle.flush()
            os.fsync(output_handle.fileno())
except OSError as error:
    try:
        target.unlink()
    except OSError:
        pass
    fail(f"could not create private archive: {error}")

if target.is_symlink() or not target.is_file() or not stat.S_ISREG(target.stat().st_mode):
    fail("private archive is not a regular file")
actual_digest = digest.hexdigest()
if total != expected_bytes or actual_digest != expected_digest:
    try:
        target.unlink()
    except OSError:
        pass
    fail("private archive differs from the staged receipt lock")
os.chmod(target, 0o400)
print(f"frozen_archive_sha256={actual_digest}")
print(f"frozen_archive_bytes={total}")
PY
)" || fail "could not freeze checked package archive"

tar_commit="$(git get-tar-commit-id < "$frozen_archive" 2>/dev/null)" ||
    fail "could not read git archive commit id from package tar"
receipt_commit="$(sed -n 's/^package_commit=//p' <<< "$submission_metadata")"
[[ "$tar_commit" == "$receipt_commit" ]] ||
    fail "tar package commit differs from receipt"

staging="$TASKROOT/.materialize-$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir "$staging"
if ! tar -xf "$frozen_archive" -C "$staging"; then
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

# `PYTHONNOUSERSITE=1` is intentionally retained by the inner launcher. The
# only user-site dependency needed by this runtime is therefore copied here as
# a byte-locked snapshot, before the package is allowed to enter systemd.
dependency_snapshot_tmp="$staging/runtime_deps"
dependency_receipt_tmp="$TASKROOT/.$GMSHPARSER_RECEIPT_FILE.$$.tmp"
dependency_metadata="$(/usr/bin/python3 - \
    "$GMSHPARSER_SOURCE_ROOT" "$dependency_snapshot_tmp" "$dependency_receipt_tmp" \
    "$PACKAGE_RECEIPT" "$RUNTIME_DEPENDENCY_SCHEMA" "$GMSHPARSER_DISTRIBUTION_VERSION" \
    "$GMSHPARSER_TREE_SHA256" "$GMSHPARSER_SNAPSHOT_RELATIVE" "$GMSHPARSER_FILES_JSON" <<'PY'
import hashlib
import importlib.metadata
import json
import os
import stat
import sys
from pathlib import Path


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"gmshparser snapshot failed: {message}")


def normalized_name(value: str) -> str:
    return "".join("-" if character in "_.-" else character.lower() for character in value)


raw_source = Path(sys.argv[1])
raw_snapshot_root = Path(sys.argv[2])
receipt_tmp = Path(sys.argv[3])
package_receipt = Path(sys.argv[4])
schema, expected_version, expected_tree, snapshot_relative, raw_manifest = sys.argv[5:]
if raw_source.is_symlink() or raw_snapshot_root.is_symlink() or receipt_tmp.is_symlink() or package_receipt.is_symlink():
    fail("source, snapshot, receipt, and package receipt paths must not be symlinks")
if not raw_source.is_dir():
    fail("source root is missing")
if raw_snapshot_root.exists() or receipt_tmp.exists():
    fail("snapshot temporary target already exists")
if not package_receipt.is_file():
    fail("package receipt is missing")
source_root = raw_source.resolve()
source_root_label = str(raw_source)
snapshot_root = raw_snapshot_root
try:
    files = json.loads(raw_manifest)
except json.JSONDecodeError as error:
    fail(f"invalid embedded file manifest: {error}")
if not isinstance(files, list) or not files:
    fail("embedded file manifest is empty")
expected_paths: set[str] = set()
for item in files:
    if not isinstance(item, dict) or set(item) != {"path", "bytes", "sha256"}:
        fail("invalid embedded file-manifest entry")
    relative = item["path"]
    if (not isinstance(relative, str) or not relative or Path(relative).name != relative
            or relative in expected_paths):
        fail("unsafe or duplicate embedded dependency path")
    if not isinstance(item["bytes"], int) or item["bytes"] < 1:
        fail("invalid embedded dependency byte count")
    if not isinstance(item["sha256"], str) or len(item["sha256"]) != 64:
        fail("invalid embedded dependency SHA-256")
    expected_paths.add(relative)

try:
    distributions = [
        distribution
        for distribution in importlib.metadata.distributions(path=[str(source_root.parent)])
        if normalized_name(str(distribution.metadata.get("Name", ""))) == "gmshparser"
    ]
except Exception as error:
    fail(f"could not read source distribution metadata: {error}")
if len(distributions) != 1 or distributions[0].version != expected_version:
    found = [distribution.version for distribution in distributions]
    fail(f"expected exactly one gmshparser {expected_version} distribution, found {found}")

source_python = {path.name for path in source_root.iterdir() if path.suffix == ".py"}
if source_python != expected_paths:
    fail("source root does not contain exactly the locked Python files")

snapshot_package = snapshot_root / "gmshparser"
snapshot_package.mkdir(parents=True)
canonical = hashlib.sha256()
for item in sorted(files, key=lambda value: value["path"]):
    relative = item["path"]
    raw_candidate = source_root / relative
    if raw_candidate.is_symlink():
        fail(f"source dependency file is a symlink: {relative}")
    candidate = raw_candidate.resolve()
    if candidate.parent != source_root or not candidate.is_file() or not stat.S_ISREG(candidate.stat().st_mode):
        fail(f"source dependency file is missing or unsafe: {relative}")
    value = candidate.read_bytes()
    actual_digest = digest_bytes(value)
    if len(value) != item["bytes"] or actual_digest != item["sha256"]:
        fail(f"source dependency file differs from lock: {relative}")
    canonical.update(f"gmshparser/{relative}\0{len(value)}\0{actual_digest}\n".encode("utf-8"))
    destination = snapshot_package / relative
    with destination.open("xb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(destination, 0o400)
if canonical.hexdigest() != expected_tree:
    fail("source dependency canonical tree SHA-256 differs from lock")

snapshot_files = set()
for candidate in snapshot_package.iterdir():
    if candidate.is_symlink() or not candidate.is_file() or not stat.S_ISREG(candidate.stat().st_mode):
        fail("snapshot contains a non-regular file")
    snapshot_files.add(candidate.name)
if snapshot_files != expected_paths:
    fail("snapshot file set differs from lock")
payload = {
    "schema": schema,
    "package_receipt_sha256": digest(package_receipt),
    "source_root": source_root_label,
    "distribution_name": "gmshparser",
    "distribution_version": expected_version,
    "snapshot_relative_path": snapshot_relative,
    "canonical_tree_sha256": expected_tree,
    "files": files,
}
with receipt_tmp.open("x", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
    handle.write("\n")
    handle.flush()
    os.fsync(handle.fileno())
print(f"runtime_dependency_tree_sha256={expected_tree}")
print(f"runtime_dependency_receipt_sha256={digest(receipt_tmp)}")
print(f"runtime_dependency_files_verified={len(files)}")
PY
)" || fail "runtime dependency snapshot verification failed"

# TASKROOT was made 0700 before materialization. Move first because some
# supported filesystems reject a rename of a directory after its write mode has
# been removed. Seal only the targets in TASKROOT; group and other accounts
# cannot reach the short move-to-seal interval through the private parent.
mv "$staging/code" "$TASKROOT/code" || fail "could not materialize checked code tree"
mv "$dependency_snapshot_tmp" "$TASKROOT/runtime_deps" ||
    fail "could not materialize checked runtime dependency snapshot"
seal_materialized_tree "$TASKROOT/code"
seal_materialized_tree "$TASKROOT/runtime_deps"
mv "$dependency_receipt_tmp" "$TASKROOT/$GMSHPARSER_RECEIPT_FILE"
rmdir "$staging"
materialization_tmp="$TASKROOT/.materialization_receipt.$$.tmp"
/usr/bin/python3 - \
    "$materialization_tmp" "$PACKAGE_RECEIPT" "$PACKAGE_RUNTIME_MANIFEST" "$frozen_archive" \
    "$tar_commit" "$MATERIALIZATION_SCHEMA" "$receipt_archive_sha256" "$receipt_archive_bytes" <<'PY'
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
expected_archive_sha256 = sys.argv[7]
try:
    expected_archive_bytes = int(sys.argv[8])
except ValueError:
    raise SystemExit("materialization verification failed: invalid frozen archive byte count")
receipt = json.loads(receipt_path.read_text())
if archive_path.is_symlink() or not archive_path.is_file():
    raise SystemExit("materialization verification failed: frozen archive is unsafe")
actual_archive_sha256 = digest(archive_path)
if (archive_path.stat().st_size != expected_archive_bytes
        or actual_archive_sha256 != expected_archive_sha256
        or receipt.get("archive_sha256") != expected_archive_sha256
        or receipt.get("archive_bytes") != expected_archive_bytes):
    raise SystemExit("materialization verification failed: frozen archive differs from receipt lock")
payload = {
    "schema": schema,
    "package_receipt_sha256": digest(receipt_path),
    "archive_sha256": actual_archive_sha256,
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
    --setenv=PACKAGE_RECEIPT_SHA256="$PACKAGE_RECEIPT_SHA256" \
    --setenv=PACKAGE_RUNTIME_MANIFEST="$PACKAGE_RUNTIME_MANIFEST" \
    --setenv=BASH_ENV= \
    --setenv=ENV= \
    --setenv=LD_PRELOAD= \
    --setenv=LD_LIBRARY_PATH= \
    /bin/bash -c 'exec /bin/bash "$1" >>"$2" 2>&1' -- "$launcher" "$log_path" 2>&1)" ||
    fail "systemd-run failed after launch-once marker: $systemd_run_output"
service_show="$(systemctl --user show "$service_unit" \
    -p Id -p MainPID -p ControlGroup -p ActiveState -p RuntimeMaxUSec -p TimeoutStopUSec \
    -p WorkingDirectory -p ExecStart 2>&1 || true)"
{
    printf '%s\n' 'schema=S04-E040-submission-receipt-v1'
    printf 'run_id=%s\n' "$RUN_ID"
    printf 'package_receipt_pin_sha256=%s\n' "$PACKAGE_RECEIPT_SHA256"
    printf '%s\n' "$submission_metadata"
    printf '%s\n' "$frozen_archive_metadata"
    printf '%s\n' "$dependency_metadata"
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
