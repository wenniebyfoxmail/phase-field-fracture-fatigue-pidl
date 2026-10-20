#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SELF_SHA="$(python3 - "$0" <<'PY'
import hashlib, pathlib, sys
print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())
PY
)"
if [[ "${S09_E017_ADMISSION_ONLY_GUARDED:-}" != "$SELF_SHA" ]]; then
  echo "admission-only guard identity missing" >&2
  exit 64
fi

ATTEMPT_ID="${S09_E017_ADMISSION_ONLY_ATTEMPT_ID:?missing attempt id}"
CANDIDATE="${S09_E017_ADMISSION_ONLY_CANDIDATE:?missing candidate}"
CANDIDATE_SHA="${S09_E017_ADMISSION_ONLY_CANDIDATE_SHA256:?missing candidate sha}"
AUTHORITY="${S09_E017_ADMISSION_ONLY_AUTHORITY:?missing authority}"
REMOTE_ATTEMPT="${S09_E017_ADMISSION_ONLY_REMOTE_ATTEMPT_ROOT:?missing remote attempt root}"
DEADLINE="${S09_E017_ADMISSION_ONLY_DEADLINE_EPOCH:?missing deadline}"

HOST="gpu-taobo"
RUN_ROOT="/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0"
CONTROL_ROOT="$RUN_ROOT/control"
CODE_ROOT="$RUN_ROOT/code"
HELPER_ROOT="$CONTROL_ROOT/admission_only_helpers/${CANDIDATE_SHA:0:16}"
SOCKET="/private/tmp/S09-E017-admission-only-$ATTEMPT_ID.sock"
REMOTE_AUTHORITY="$HELPER_ROOT/admission_only_authority.json"
REMOTE_CANDIDATE="$HELPER_ROOT/docs/research/S09/S09-E017/s09_e017_admission_only_candidate_20261020.json"
REMOTE_RUNNER="$HELPER_ROOT/scripts/run_s09_e017_admission_only.py"
REMOTE_FINAL_CANDIDATE="$CODE_ROOT/docs/research/S09/S09-E017/final_execution_candidate_20261020.json"
REMOTE_PACKAGE="$CODE_ROOT/docs/research/S09/S09-E017/final_run_package_config_20261019.json"
REMOTE_ARCHIVE="$CONTROL_ROOT/code.tar.gz"

connection_attempts=0
metadata_transfers=0
master_started=0

remaining_seconds() {
  local now remaining
  now="$(date +%s)"
  remaining=$((DEADLINE - now))
  if ((remaining <= 0)); then
    echo "admission-only wall expired" >&2
    exit 70
  fi
  echo "$remaining"
}

cleanup() {
  if ((master_started == 1)); then
    ssh -S "$SOCKET" -o ControlMaster=no -o ProxyCommand=/usr/bin/false \
      -O exit "$HOST" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

MUX_SSH=(ssh -S "$SOCKET" -o ControlMaster=no -o BatchMode=yes \
  -o ProxyCommand=/usr/bin/false "$HOST")
MUX_RSH="ssh -S $SOCKET -o ControlMaster=no -o BatchMode=yes -o ProxyCommand=/usr/bin/false"

((connection_attempts += 1))
if ((connection_attempts != 1)); then
  echo "connection count drift" >&2
  exit 65
fi
ssh -MNf -S "$SOCKET" -o ControlMaster=yes -o ControlPersist=300 \
  -o BatchMode=yes -o ConnectTimeout=20 "$HOST"
master_started=1
remaining_seconds >/dev/null

# Read-only state check before helper staging.  This does not read packet or
# checkpoint content and refuses any production admission/execution residue.
"${MUX_SSH[@]}" python3 - "$CODE_ROOT" "$CONTROL_ROOT" "$RUN_ROOT/run" \
  "/mnt/data2/drtao/pidl_archives/S09-E017-R001-factorised-head-p0" \
  "$HELPER_ROOT" "$REMOTE_ATTEMPT" <<'PY'
import json, os, pathlib, subprocess, sys
code, control, output, archive, helper, attempt = map(pathlib.Path, sys.argv[1:])
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
    output,
    archive,
    helper,
    attempt,
]
state = {
    "hostname": os.uname().nodename,
    "uid": os.getuid(),
    "head": head,
    "dirty": bool(dirty),
    "blocked_present": [str(path) for path in blocked if path.exists()],
}
expected = {
    "hostname": "GPUServer8",
    "uid": 1010,
    "head": "2002538d9a30c8d4006ccaff5959cd214958fc82",
    "dirty": False,
    "blocked_present": [],
}
if state != expected:
    raise SystemExit(json.dumps(state, sort_keys=True))
print(json.dumps(state, sort_keys=True))
PY
remaining_seconds >/dev/null

"${MUX_SSH[@]}" mkdir -p "$CONTROL_ROOT/admission_only_helpers" \
  "$CONTROL_ROOT/admission_only_attempts"
"${MUX_SSH[@]}" mkdir "$HELPER_ROOT"

((metadata_transfers += 1))
if ((metadata_transfers != 1)); then
  echo "metadata transfer count drift" >&2
  exit 65
fi
AUTHORITY_PARENT="$(dirname "$AUTHORITY")"
AUTHORITY_NAME="$(basename "$AUTHORITY")"
if [[ "$AUTHORITY_NAME" != "admission_only_authority.json" ]]; then
  echo "authority basename drift" >&2
  exit 66
fi
cd "$ROOT"
rsync -aR --ignore-existing -e "$MUX_RSH" \
  source/s09_e017_admission_only.py \
  scripts/resolve_s09_e017_admission_only.py \
  scripts/run_s09_e017_admission_only.py \
  docs/research/S09/S09-E017/s09_e017_admission_only_candidate_20261020.json \
  "$AUTHORITY_PARENT/./$AUTHORITY_NAME" \
  "$HOST:$HELPER_ROOT/"
remaining_seconds >/dev/null

# Verify every staged byte before the reviewed helper can create its token.
"${MUX_SSH[@]}" python3 - "$HELPER_ROOT" "$REMOTE_CANDIDATE" \
  "$REMOTE_AUTHORITY" "$CANDIDATE_SHA" <<'PY'
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
candidate_path = pathlib.Path(sys.argv[2])
authority_path = pathlib.Path(sys.argv[3])
expected_candidate = sys.argv[4]
candidate_bytes = candidate_path.read_bytes()
if hashlib.sha256(candidate_bytes).hexdigest() != expected_candidate:
    raise SystemExit("candidate hash mismatch")
candidate = json.loads(candidate_bytes)
for relative, expected in candidate["helper_manifest"].items():
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"invalid helper: {relative}")
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit(f"helper hash mismatch: {relative}")
if not authority_path.is_file() or authority_path.is_symlink():
    raise SystemExit("authority missing")
PY

SECONDS_LEFT="$(remaining_seconds)"
"${MUX_SSH[@]}" env \
  PYTHONPATH="$HELPER_ROOT/source:$HELPER_ROOT/scripts" \
  CUDA_VISIBLE_DEVICES="" \
  OMP_NUM_THREADS=1 \
  OPENBLAS_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 \
  bash -c 'ulimit -t 60; ulimit -v 1048576; cd "$1"; exec timeout "$2" python3 "$3" "${@:4}"' \
  admission-only "$CODE_ROOT" "$SECONDS_LEFT" "$REMOTE_RUNNER" \
  --admission-candidate "$REMOTE_CANDIDATE" \
  --admission-candidate-sha256 "$CANDIDATE_SHA" \
  --final-execution-candidate "$REMOTE_FINAL_CANDIDATE" \
  --base-package-config "$REMOTE_PACKAGE" \
  --authority "$REMOTE_AUTHORITY" \
  --code-archive "$REMOTE_ARCHIVE" \
  --code-root "$CODE_ROOT" \
  --attempt-root "$REMOTE_ATTEMPT" \
  --execute-authorised-admission-only

# The reviewed runner stops after its bounded receipt.  There is intentionally
# no resolver handoff, producer command, CUDA path or follow-up inspection.
