#!/usr/bin/env bash
# Chained watcher: waits for the in-flight Umax=0.12 oracle-driver smoke test
# (PID 32333, log run_e2_reverse_Umax0.12.log) to fracture, then launches
# the 4-Umax sweep (0.08, 0.09, 0.10, 0.11) via _queue_e2_reverse_sweep.sh.
#
# Uses "Fracture confirmed" (fixed string in fracture detector output) as
# the trigger so it works whether the smoke test fractures within 300 cycles
# or hits cap (in which case the runner exits cleanly anyway and this watcher
# falls through after a brief grace period).

set -u

SENS=/c/Users/xw436/phase-field-fracture-fatigue-pidl/SENS_tensile
SMOKE_LOG="$SENS/run_e2_reverse_Umax0.12.log"
SMOKE_PID=32333
SWEEP_SCRIPT="$SENS/_queue_e2_reverse_sweep.sh"
MY_LOG="$SENS/_queue_e2_reverse_chained.watcher.log"
SWEEP_NOHUP_LOG="$SENS/_queue_e2_reverse_sweep.nohup.log"

cd "$SENS"
echo "[$(date)] chained watcher starting; waiting on smoke PID $SMOKE_PID (Umax=0.12) to finish" \
    | tee -a "$MY_LOG"

# Poll: trigger when smoke log shows "Fracture confirmed" OR smoke process exits
while true; do
    if grep -q "Fracture confirmed" "$SMOKE_LOG" 2>/dev/null; then
        echo "[$(date)] smoke fracture detected; launching sweep" | tee -a "$MY_LOG"
        break
    fi
    # Also fire if the smoke process is dead (exit clean OR crash)
    # Use ps -p style check that works in git-bash (no pgrep)
    if ! ps -ef | awk -v p="$SMOKE_PID" '$2 == p { f=1 } END { exit !f }'; then
        echo "[$(date)] smoke PID $SMOKE_PID no longer alive; checking log for exit state" \
            | tee -a "$MY_LOG"
        sleep 5  # let final flush land
        if grep -q "Fracture confirmed" "$SMOKE_LOG" 2>/dev/null; then
            echo "[$(date)]   smoke fractured cleanly; proceeding to sweep" | tee -a "$MY_LOG"
        else
            echo "[$(date)]   smoke exited WITHOUT fracture (cap hit or crash); proceeding to sweep anyway" \
                | tee -a "$MY_LOG"
        fi
        break
    fi
    sleep 60
done

echo "[$(date)] launching: bash $SWEEP_SCRIPT" | tee -a "$MY_LOG"
nohup bash "$SWEEP_SCRIPT" > "$SWEEP_NOHUP_LOG" 2>&1 &
SWEEP_PID=$!
echo "[$(date)] sweep launched as PID $SWEEP_PID" | tee -a "$MY_LOG"
