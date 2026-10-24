#!/usr/bin/env bash
# Launch exactly one approved S04-E040 producer arm from an isolated task root.
# The caller supplies a fresh TASKROOT, archive root, selected visible GPU, and
# the already verified standard baseline/R001 locations.  This wrapper never
# creates or reuses an existing results directory.
set -euo pipefail

: "${TASKROOT:?set TASKROOT to the fresh /mnt/data2/drtao/wennie run directory}"
: "${PIDL_ARCHIVE_DIR:?set PIDL_ARCHIVE_DIR to the fresh archive directory}"
: "${CUDA_VISIBLE_DEVICES:?set CUDA_VISIBLE_DEVICES to the selected GPU index}"
: "${BASELINE:?set BASELINE to the frozen Umax=0.12 recovery archive}"
: "${REFERENCE_RESULT:?set REFERENCE_RESULT to the completed S04-E037-R001 results directory}"
: "${SOURCE_COMMIT:?set SOURCE_COMMIT to the reviewed E040 source commit}"

export TMPDIR="$TASKROOT/tmp"
export XDG_CACHE_HOME="$TASKROOT/cache"
export TORCH_EXTENSIONS_DIR="$TASKROOT/.jitcache"
export MPLCONFIGDIR="$TASKROOT/cache/matplotlib"
export OMP_NUM_THREADS=4

mkdir -p "$TMPDIR" "$XDG_CACHE_HOME" "$TORCH_EXTENSIONS_DIR" "$MPLCONFIGDIR"
mkdir -p "$PIDL_ARCHIVE_DIR"
if [[ -e "$PIDL_ARCHIVE_DIR/results" ]]; then
    printf '%s\n' "refusing to reuse results directory: $PIDL_ARCHIVE_DIR/results" >&2
    exit 2
fi

cd "$TASKROOT/code"
date -u +%Y-%m-%dT%H:%M:%SZ > "$TASKROOT/started_utc.txt"
set +e
timeout --signal=TERM --kill-after=10s 3500s /usr/bin/python3 -u \
    scripts/run_s04_e040_feasible_damage.py \
    --baseline "$BASELINE" \
    --reference-result "$REFERENCE_RESULT" \
    --output "$PIDL_ARCHIVE_DIR/results" \
    --source-commit "$SOURCE_COMMIT" \
    --step-seconds 240 \
    --total-seconds 3300 \
    --max-updates 10000
task_exit=$?
set -e
printf '%s\n' "$task_exit" > "$TASKROOT/exit_code.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$TASKROOT/finished_utc.txt"
exit "$task_exit"
