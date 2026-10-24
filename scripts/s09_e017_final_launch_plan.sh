#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SELF_SHA="$(python3 - "$0" <<'PY'
import hashlib, pathlib, sys
print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())
PY
)"
if [[ "${S09_E017_FINAL_LAUNCH_GUARDED:-}" != "$SELF_SHA" ]]; then
  echo "final launch guard identity missing" >&2
  exit 64
fi

ATTEMPT_ID="${S09_E017_FINAL_LAUNCH_ATTEMPT_ID:?missing attempt id}"
AUTHORITY="${S09_E017_EXECUTION_AUTHORITY:?missing execution authority}"
AUTHORITY_SHA="${S09_E017_EXECUTION_AUTHORITY_SHA256:?missing authority sha}"
LAUNCHER="${S09_E017_FINAL_LAUNCHER:?missing launcher}"
LAUNCHER_SHA="${S09_E017_FINAL_LAUNCHER_SHA256:?missing launcher sha}"
EVIDENCE_ROOT="${S09_E017_FINAL_LAUNCH_EVIDENCE_ROOT:?missing evidence root}"
DEADLINE="${S09_E017_FINAL_LAUNCH_DEADLINE_EPOCH:?missing deadline}"

HOST="gpu-taobo"
RUN_ROOT="/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0"
CODE_ROOT="$RUN_ROOT/code"
CONTROL_ROOT="$RUN_ROOT/control"
OUTPUT_ROOT="$RUN_ROOT/run"
ARCHIVE_ROOT="/mnt/data2/drtao/pidl_archives/S09-E017-R001-factorised-head-p0"
HELPER_ROOT="$CONTROL_ROOT/final_launch_helpers/${LAUNCHER_SHA:0:16}"
REMOTE_AUTHORITY="$HELPER_ROOT/execution_authority.json"
REMOTE_LAUNCHER="$HELPER_ROOT/s09_e017_final_launch.py"
SESSION="pf_s09_e017_r001_factorised_head_p0"
LOG="$CONTROL_ROOT/final_launch.log"
SOCKET="/private/tmp/S09-E017-final-launch-$ATTEMPT_ID.sock"
connection_attempts=0
metadata_transfers=0
master_started=0

remaining_seconds() {
  local remaining
  remaining=$((DEADLINE - $(date +%s)))
  if ((remaining <= 0)); then
    echo "final launch dispatch wall expired" >&2
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
ssh -MNf -S "$SOCKET" -o ControlMaster=yes -o ControlPersist=120 \
  -o BatchMode=yes -o ConnectTimeout=20 "$HOST"
master_started=1
remaining_seconds >/dev/null

"${MUX_SSH[@]}" python3 - "$CODE_ROOT" "$CONTROL_ROOT" "$OUTPUT_ROOT" \
  "$ARCHIVE_ROOT" "$HELPER_ROOT" "$SESSION" <<'PY'
import hashlib, json, os, pathlib, shutil, subprocess, sys
code, control, output, science_archive, helper = map(pathlib.Path, sys.argv[1:6])
session = sys.argv[6]
head = subprocess.run(
    ["git", "-C", str(code), "rev-parse", "HEAD"],
    check=True, capture_output=True, text=True,
).stdout.strip()
dirty = subprocess.run(
    ["git", "-C", str(code), "status", "--short"],
    check=True, capture_output=True, text=True,
).stdout
archive = control / "code.tar.gz"
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
blocked = [
    control / "execution_authority.json",
    control / "config_resolved.json",
    control / "resolution_receipt.json",
    control / "admission_attempt.json",
    control / "admission_receipt.json",
    control / "admission_failure_receipt.json",
    control / "final_launch_started.json",
    control / "final_launch_failure.json",
    control / "final_launch.log",
    output,
    science_archive,
    helper,
]
gpu_rows = subprocess.run(
    ["nvidia-smi", "--query-gpu=index,uuid,memory.free,utilization.gpu",
     "--format=csv,noheader,nounits"],
    check=True, capture_output=True, text=True,
).stdout.splitlines()
gpu5 = [row for row in gpu_rows if row.split(",", 1)[0].strip() == "5"]
compute = subprocess.run(
    ["nvidia-smi", "--query-compute-apps=gpu_uuid,pid",
     "--format=csv,noheader,nounits"],
    check=True, capture_output=True, text=True,
).stdout
state = {
    "hostname": os.uname().nodename,
    "uid": os.getuid(),
    "head": head,
    "dirty": bool(dirty),
    "archive_bytes": archive.stat().st_size,
    "archive_sha256": digest,
    "data2_free_bytes": shutil.disk_usage("/mnt/data2").free,
    "blocked_present": [str(path) for path in blocked if path.exists()],
    "tmux": shutil.which("tmux"),
    "session_present": subprocess.run(
        ["tmux", "has-session", "-t", session], capture_output=True
    ).returncode == 0 if shutil.which("tmux") else None,
    "gpu5": gpu5,
    "gpu5_compute_process_present":
        "GPU-5622bd47-1050-3003-246d-3cabe2b4791b" in compute,
}
if state["hostname"] != "GPUServer8" or state["uid"] != 1010:
    raise SystemExit(json.dumps(state, sort_keys=True))
if state["head"] != "2002538d9a30c8d4006ccaff5959cd214958fc82" or state["dirty"]:
    raise SystemExit(json.dumps(state, sort_keys=True))
if state["archive_bytes"] != 14359316 or state["archive_sha256"] != "4ece34be786fc85bb9655c076c13c45d276d08dfde405a8fb1367e4b49ffdd22":
    raise SystemExit(json.dumps(state, sort_keys=True))
if state["data2_free_bytes"] < 21474836480:
    raise SystemExit(json.dumps(state, sort_keys=True))
if state["blocked_present"] or not state["tmux"] or state["session_present"]:
    raise SystemExit(json.dumps(state, sort_keys=True))
if len(state["gpu5"]) != 1:
    raise SystemExit(json.dumps(state, sort_keys=True))
gpu5_parts = [part.strip() for part in state["gpu5"][0].split(",")]
if gpu5_parts[1] != "GPU-5622bd47-1050-3003-246d-3cabe2b4791b":
    raise SystemExit(json.dumps(state, sort_keys=True))
if int(gpu5_parts[2]) < 20480 or int(gpu5_parts[3]) != 0:
    raise SystemExit(json.dumps(state, sort_keys=True))
if state["gpu5_compute_process_present"]:
    raise SystemExit(json.dumps(state, sort_keys=True))
print(json.dumps(state, sort_keys=True))
PY
remaining_seconds >/dev/null

"${MUX_SSH[@]}" mkdir -p "$CONTROL_ROOT/final_launch_helpers"
"${MUX_SSH[@]}" mkdir "$HELPER_ROOT"
LOCAL_STAGE="$EVIDENCE_ROOT/final_launch_stage"
if [[ -e "$LOCAL_STAGE" ]]; then
  echo "local final launch stage conflict" >&2
  exit 66
fi
mkdir "$LOCAL_STAGE"
cp "$AUTHORITY" "$LOCAL_STAGE/execution_authority.json"
cp "$LAUNCHER" "$LOCAL_STAGE/s09_e017_final_launch.py"
stage_bytes="$(du -sk "$LOCAL_STAGE" | awk '{print $1 * 1024}')"
if ((stage_bytes > 65536)); then
  echo "final launch metadata transfer cap exceeded" >&2
  exit 67
fi
((metadata_transfers += 1))
if ((metadata_transfers != 1)); then
  echo "metadata transfer count drift" >&2
  exit 65
fi
rsync -a --ignore-existing -e "$MUX_RSH" "$LOCAL_STAGE/" "$HOST:$HELPER_ROOT/"
remaining_seconds >/dev/null

"${MUX_SSH[@]}" python3 - "$REMOTE_AUTHORITY" "$AUTHORITY_SHA" \
  "$REMOTE_LAUNCHER" "$LAUNCHER_SHA" <<'PY'
import hashlib, pathlib, sys
for raw_path, expected in ((sys.argv[1], sys.argv[2]), (sys.argv[3], sys.argv[4])):
    path = pathlib.Path(raw_path)
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"invalid staged file: {path}")
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit(f"staged hash mismatch: {path}")
PY
"${MUX_SSH[@]}" ln "$REMOTE_AUTHORITY" "$CONTROL_ROOT/execution_authority.json"
remaining_seconds >/dev/null

"${MUX_SSH[@]}" bash -s -- "$REMOTE_LAUNCHER" "$CODE_ROOT" "$CONTROL_ROOT" \
  "$SESSION" "$LOG" <<'REMOTE_LAUNCH'
set -euo pipefail
launcher="$1"
code="$2"
control="$3"
session="$4"
log="$5"
printf -v command '%q ' timeout --signal=TERM --kill-after=10s 1830s \
  python3 "$launcher" --code-root "$code" --control-root "$control" \
  --session-name "$session" --log-path "$log"
tmux new-session -d -s "$session" -c "$code" "$command"
for _ in $(seq 1 30); do
  if [[ -f "$control/final_launch_failure.json" ]]; then
    cat "$control/final_launch_failure.json"
    exit 1
  fi
  if [[ -f "$control/admission_failure_receipt.json" ]]; then
    cat "$control/admission_failure_receipt.json"
    exit 1
  fi
  if [[ -f "$control/admission_receipt.json" ]]; then
    python3 - "$control/final_launch_started.json" "$control/admission_receipt.json" <<'PY'
import json, pathlib, sys
started = json.loads(pathlib.Path(sys.argv[1]).read_text())
admission = json.loads(pathlib.Path(sys.argv[2]).read_text())
print(json.dumps({"terminal_state": "FINAL_PRODUCTION_ADMISSION_REACHED", "launch": started, "admission": admission}, sort_keys=True))
PY
    exit 0
  fi
  if [[ -f "$control/final_launch_started.json" ]] && ! tmux has-session -t "$session" 2>/dev/null; then
    echo "detached session exited before admission receipt" >&2
    exit 1
  fi
  sleep 1
done
if [[ ! -f "$control/final_launch_started.json" ]]; then
  echo "launch started receipt missing" >&2
  exit 1
fi
if ! tmux has-session -t "$session" 2>/dev/null; then
  echo "detached session absent" >&2
  exit 1
fi
python3 - "$control/final_launch_started.json" <<'PY'
import json, pathlib, sys
started = json.loads(pathlib.Path(sys.argv[1]).read_text())
print(json.dumps({"terminal_state": "FINAL_LAUNCH_STARTED_ADMISSION_PENDING", "launch": started}, sort_keys=True))
PY
REMOTE_LAUNCH

# This card obtains its launch/admission return through the same connection.
# It performs no later status poll, result retrieval, retry or reconnect.
