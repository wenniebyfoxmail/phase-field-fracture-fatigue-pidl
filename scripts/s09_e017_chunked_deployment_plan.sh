#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SELF_SHA="$(python3 - "$0" <<'PY'
import hashlib, pathlib, sys
print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())
PY
)"
if [[ "${S09_E017_GUARDED:-}" != "$SELF_SHA" ]]; then
  echo "guard identity missing" >&2
  exit 64
fi
ATTEMPT_ID="${S09_E017_DEPLOYMENT_ATTEMPT_ID:?missing deployment attempt id}"
DEADLINE="${S09_E017_DEPLOYMENT_DEADLINE_EPOCH:?missing deployment deadline}"

HOST="gpu-taobo"
RUN_ROOT="/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0"
CONTROL_ROOT="$RUN_ROOT/control"
HELPER_ROOT="$CONTROL_ROOT/chunked_deployment_v1"
CHUNK_STORE="$CONTROL_ROOT/archive_chunks/4ece34be786fc85bb"
LEGACY_PARTIAL="$CONTROL_ROOT/code.tar.gz.partial_frozen_transfer_stopped_20261020"
EXPECTED_ARCHIVE="$CONTROL_ROOT/code.tar.gz"
REMOTE_ATTEMPT="$CONTROL_ROOT/deployment_attempts/$ATTEMPT_ID"
ARCHIVE_ROOT="/mnt/data2/drtao/pidl_archives/S09-E017-R001-factorised-head-p0"
SOCKET="/private/tmp/S09-E017-$ATTEMPT_ID.sock"
LOCAL_CHUNKS="/tmp/S09-E017-code-4ece34be-chunks-v1"
LOCAL_INSPECTION="/private/tmp/S09-E017-$ATTEMPT_ID-store-before-transfer.json"
LOCAL_MISSING="/private/tmp/S09-E017-$ATTEMPT_ID-missing-files.txt"
MANIFEST_REL="docs/research/S09/S09-E017/chunked_archive_manifest_20261020.json"
MANIFEST_SHA="a88a23859c2edd2ac2ddc09d9140029d128fbcbb21b689c46274918d6f1318ae"
ARCHIVE_SHA="4ece34be786fc85bb9655c076c13c45d276d08dfde405a8fb1367e4b49ffdd22"
ARCHIVE_BYTES=14359316
SOURCE_BYTE_CAP=14500000

connection_attempts=0
metadata_transfers=0
chunk_transfers=0
master_started=0

remaining_seconds() {
  local now
  now="$(date +%s)"
  local remaining=$((DEADLINE - now))
  if ((remaining <= 0)); then
    echo "outer deployment wall expired" >&2
    exit 70
  fi
  echo "$remaining"
}

cleanup() {
  if ((master_started == 1)); then
    ssh -S "$SOCKET" -o ControlMaster=no \
      -o ProxyCommand=/usr/bin/false -O exit "$HOST" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

MUX_SSH=(ssh -S "$SOCKET" -o ControlMaster=no -o BatchMode=yes \
  -o ProxyCommand=/usr/bin/false "$HOST")
MUX_RSH="ssh -S $SOCKET -o ControlMaster=no -o BatchMode=yes -o ProxyCommand=/usr/bin/false"

# Local identities and all 28 source chunks must be valid before networking.
PYTHONPATH="$ROOT/source" python3 "$ROOT/scripts/s09_e017_chunked_archive.py" \
  inspect-store \
  --manifest "$ROOT/$MANIFEST_REL" \
  --manifest-sha256 "$MANIFEST_SHA" \
  --chunk-dir "$LOCAL_CHUNKS" | python3 -c \
  'import json,sys; r=json.load(sys.stdin); assert r["complete"] and not r["corrupt"]'

((connection_attempts += 1))
if ((connection_attempts != 1)); then
  echo "connection attempt count drift" >&2
  exit 65
fi
ssh -MNf -S "$SOCKET" -o ControlMaster=yes -o ControlPersist=1800 \
  -o BatchMode=yes -o ConnectTimeout=20 "$HOST"
master_started=1
remaining_seconds >/dev/null

# Read-only state inspection before any remote mutation.
"${MUX_SSH[@]}" python3 - "$RUN_ROOT" "$ARCHIVE_ROOT" <<'PY'
import json, os, pathlib, subprocess, sys
run_root = pathlib.Path(sys.argv[1])
archive_root = pathlib.Path(sys.argv[2])
control = run_root / "control"
code = run_root / "code"
head = subprocess.run(
    ["git", "-C", str(code), "rev-parse", "HEAD"],
    check=True, capture_output=True, text=True,
).stdout.strip()
dirty = subprocess.run(
    ["git", "-C", str(code), "status", "--short"],
    check=True, capture_output=True, text=True,
).stdout
blocked = [
    control / "execution_authority.json",
    control / "config_resolved.json",
    control / "resolution_receipt.json",
    control / "admission_attempt.json",
    control / "admission_receipt.json",
    control / "admission_failure_receipt.json",
    run_root / "run",
    archive_root,
    control / "code.tar.gz",
]
state = {
    "hostname": os.uname().nodename,
    "head": head,
    "dirty": bool(dirty),
    "blocked_present": [str(path) for path in blocked if path.exists()],
}
if state != {
    "hostname": "GPUServer8",
    "head": "2002538d9a30c8d4006ccaff5959cd214958fc82",
    "dirty": False,
    "blocked_present": [],
}:
    raise SystemExit(json.dumps(state, sort_keys=True))
print(json.dumps(state, sort_keys=True))
PY
remaining_seconds >/dev/null

"${MUX_SSH[@]}" mkdir -p "$HELPER_ROOT" "$CHUNK_STORE" \
  "$CONTROL_ROOT/deployment_attempts"
"${MUX_SSH[@]}" mkdir "$REMOTE_ATTEMPT"

((metadata_transfers += 1))
if ((metadata_transfers != 1)); then
  echo "metadata transfer count drift" >&2
  exit 65
fi
cd "$ROOT"
rsync -aR --ignore-existing -e "$MUX_RSH" \
  source/s09_e017_chunked_deployment.py \
  scripts/s09_e017_chunked_archive.py \
  "$MANIFEST_REL" \
  "$HOST:$HELPER_ROOT/"
remaining_seconds >/dev/null

"${MUX_SSH[@]}" python3 - "$HELPER_ROOT" <<'PY'
import hashlib, pathlib, sys
root = pathlib.Path(sys.argv[1])
expected = {
    "source/s09_e017_chunked_deployment.py": "a218f252c144bf7a19d3c0cb62b5de6f66dd0317fb159cb7c3b5f9a77c33e0cd",
    "scripts/s09_e017_chunked_archive.py": "11b7b1f8d409366480844a511603fe5b6b1349ff17b2e3e924691cdccd7dc473",
    "docs/research/S09/S09-E017/chunked_archive_manifest_20261020.json": "a88a23859c2edd2ac2ddc09d9140029d128fbcbb21b689c46274918d6f1318ae",
}
for relative, digest in expected.items():
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"missing helper file: {relative}")
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise SystemExit(f"helper hash mismatch: {relative}")
PY

REMOTE_PYTHONPATH="$HELPER_ROOT/source"
REMOTE_CLI="$HELPER_ROOT/scripts/s09_e017_chunked_archive.py"
REMOTE_MANIFEST="$HELPER_ROOT/$MANIFEST_REL"

if "${MUX_SSH[@]}" test -f "$LEGACY_PARTIAL"; then
  "${MUX_SSH[@]}" env PYTHONPATH="$REMOTE_PYTHONPATH" python3 "$REMOTE_CLI" \
    audit-legacy --manifest "$REMOTE_MANIFEST" \
    --manifest-sha256 "$MANIFEST_SHA" \
    --legacy-partial "$LEGACY_PARTIAL" \
    --report "$REMOTE_ATTEMPT/legacy-audit.json"
  "${MUX_SSH[@]}" env PYTHONPATH="$REMOTE_PYTHONPATH" python3 "$REMOTE_CLI" \
    import-legacy --manifest "$REMOTE_MANIFEST" \
    --manifest-sha256 "$MANIFEST_SHA" \
    --legacy-partial "$LEGACY_PARTIAL" \
    --chunk-dir "$CHUNK_STORE" \
    --report "$REMOTE_ATTEMPT/legacy-import.json"
fi
remaining_seconds >/dev/null

if [[ -e "$LOCAL_INSPECTION" || -e "$LOCAL_MISSING" ]]; then
  echo "local attempt path conflict" >&2
  exit 66
fi
"${MUX_SSH[@]}" env PYTHONPATH="$REMOTE_PYTHONPATH" python3 "$REMOTE_CLI" \
  inspect-store --manifest "$REMOTE_MANIFEST" \
  --manifest-sha256 "$MANIFEST_SHA" \
  --chunk-dir "$CHUNK_STORE" \
  --report "$REMOTE_ATTEMPT/store-before-transfer.json" > "$LOCAL_INSPECTION"

MISSING_BYTES="$(python3 - "$ROOT/$MANIFEST_REL" "$LOCAL_INSPECTION" "$LOCAL_MISSING" <<'PY'
import json, pathlib, sys
manifest = json.loads(pathlib.Path(sys.argv[1]).read_text())
report = json.loads(pathlib.Path(sys.argv[2]).read_text())
output = pathlib.Path(sys.argv[3])
if report["manifest_sha256"] != "a88a23859c2edd2ac2ddc09d9140029d128fbcbb21b689c46274918d6f1318ae":
    raise SystemExit("inspection manifest drift")
if report["corrupt"] or report["corrupt_names"]:
    raise SystemExit("corrupt final chunk path present")
by_name = {chunk["name"]: chunk for chunk in manifest["chunks"]}
names = report["missing_names"]
if len(names) != len(set(names)) or any(name not in by_name for name in names):
    raise SystemExit("missing-name list invalid")
if any(pathlib.PurePosixPath(name).name != name for name in names):
    raise SystemExit("unsafe missing-name path")
with output.open("x", encoding="utf-8") as stream:
    for name in names:
        stream.write(name + "\n")
print(sum(by_name[name]["size"] for name in names))
PY
)"
METADATA_BYTES="$(python3 - "$ROOT" "$MANIFEST_REL" <<'PY'
import pathlib, sys
root = pathlib.Path(sys.argv[1])
paths = [
    root / "source/s09_e017_chunked_deployment.py",
    root / "scripts/s09_e017_chunked_archive.py",
    root / sys.argv[2],
]
print(sum(path.stat().st_size for path in paths))
PY
)"
if ((METADATA_BYTES + MISSING_BYTES > SOURCE_BYTE_CAP)); then
  echo "source byte cap exceeded" >&2
  exit 67
fi

if ((MISSING_BYTES > 0)); then
  ((chunk_transfers += 1))
  if ((chunk_transfers != 1)); then
    echo "chunk transfer count drift" >&2
    exit 65
  fi
  rsync -a --ignore-existing --files-from="$LOCAL_MISSING" -e "$MUX_RSH" \
    "$LOCAL_CHUNKS/" "$HOST:$CHUNK_STORE/"
fi
remaining_seconds >/dev/null

"${MUX_SSH[@]}" env PYTHONPATH="$REMOTE_PYTHONPATH" python3 "$REMOTE_CLI" \
  inspect-store --manifest "$REMOTE_MANIFEST" \
  --manifest-sha256 "$MANIFEST_SHA" \
  --chunk-dir "$CHUNK_STORE" \
  --report "$REMOTE_ATTEMPT/store-after-transfer.json" | python3 -c \
  'import json,sys; r=json.load(sys.stdin); assert r["complete"] and not r["corrupt"]'

REMAINING="$(remaining_seconds)"
"${MUX_SSH[@]}" env PYTHONPATH="$REMOTE_PYTHONPATH" python3 "$REMOTE_CLI" \
  assemble --manifest "$REMOTE_MANIFEST" \
  --manifest-sha256 "$MANIFEST_SHA" \
  --chunk-dir "$CHUNK_STORE" \
  --output "$EXPECTED_ARCHIVE" \
  --receipt "$REMOTE_ATTEMPT/assembly-receipt.json" \
  --max-wall-seconds "$REMAINING"

"${MUX_SSH[@]}" env PYTHONPATH="$REMOTE_PYTHONPATH" python3 "$REMOTE_CLI" \
  verify-archive \
  --archive "$EXPECTED_ARCHIVE" \
  --expected-bytes "$ARCHIVE_BYTES" \
  --expected-sha256 "$ARCHIVE_SHA" \
  --expected-commit 2002538d9a30c8d4006ccaff5959cd214958fc82

if ((connection_attempts != 1 || metadata_transfers != 1 || chunk_transfers > 1)); then
  echo "final invocation count drift" >&2
  exit 65
fi
remaining_seconds >/dev/null
