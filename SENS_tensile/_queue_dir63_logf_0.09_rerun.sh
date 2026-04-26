#!/usr/bin/env bash
# Chained watcher: waits for current Dir 6.3 sweep (Umax 0.08-0.11) to finish,
# then launches 0.09 long-cycle re-run with --n-cycles 700 per Mac decision
# (shared_research_log 2026-04-26 [reply+decision], commit 522299d).
#
# Polls _queue_dir63_logf_sweep.watcher.log for "queue complete" marker.
# If the parent sweep already crashed before 0.11, exits without launching.

set -u  # do NOT set -e (we want graceful exit if watcher log shows crash)

SENS=/c/Users/xw436/phase-field-fracture-fatigue-pidl/SENS_tensile
PY="C:/Users/xw436/Python310/python.exe"
PARENT_LOG="$SENS/_queue_dir63_logf_sweep.watcher.log"
MY_LOG="$SENS/_queue_dir63_logf_0.09_rerun.watcher.log"
RERUN_LOG="$SENS/run_dir63_logf_Umax0.09_N700.log"

cd "$SENS"
echo "[$(date)] chained watcher starting; will fire 0.09 --n-cycles 700 after parent sweep complete" | tee -a "$MY_LOG"

# Poll until the parent sweep prints "queue complete"
# (pgrep not available in git-bash; rely on log marker only — manual kill if parent crashed)
while true; do
    if grep -q "Dir 6.3 logf sweep queue complete" "$PARENT_LOG" 2>/dev/null; then
        echo "[$(date)] parent sweep complete detected; launching 0.09 re-run" | tee -a "$MY_LOG"
        break
    fi
    sleep 60
done

echo "[$(date)] launching: $PY -u run_dir63_logf_umax.py 0.09 --n-cycles 700" | tee -a "$MY_LOG"
PYTHONIOENCODING=utf-8 "$PY" -u run_dir63_logf_umax.py 0.09 --n-cycles 700 \
    > "$RERUN_LOG" 2>&1
EC=$?

if [ $EC -eq 0 ]; then
    echo "[$(date)] 0.09 re-run finished cleanly (exit 0)" | tee -a "$MY_LOG"
else
    echo "[$(date)] 0.09 re-run exited with code $EC" | tee -a "$MY_LOG"
fi
