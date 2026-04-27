#!/usr/bin/env bash
# Chained v2 watcher: waits for orphaned 0.08 worker (PID 33907) to finish,
# then launches sweep_v2 (0.11 → 0.10 → 0.09).
#
# Trigger: 0.08 worker process disappears OR log shows "Fracture confirmed"
# OR log shows "Stopping at cycle 300" (cap hit). Whichever first.

set -u

SENS=/c/Users/xw436/phase-field-fracture-fatigue-pidl/SENS_tensile
ORPHAN_PID=33907
SMOKE_LOG="$SENS/run_e2_reverse_Umax0.08.log"
SWEEP_SCRIPT="$SENS/_queue_e2_reverse_sweep_v2.sh"
MY_LOG="$SENS/_queue_e2_reverse_chained_v2.watcher.log"
SWEEP_NOHUP_LOG="$SENS/_queue_e2_reverse_sweep_v2.nohup.log"

cd "$SENS"
echo "[$(date)] chained v2 watcher starting; waiting on 0.08 worker PID $ORPHAN_PID to finish" \
    | tee -a "$MY_LOG"

while true; do
    # Trigger 1: process gone
    if ! ps -ef | awk -v p="$ORPHAN_PID" '$2 == p { f=1 } END { exit !f }'; then
        echo "[$(date)] 0.08 worker PID $ORPHAN_PID exited; proceeding" | tee -a "$MY_LOG"
        break
    fi
    # Trigger 2: fracture or cap hit (these also imply graceful exit imminent)
    if grep -q "Fracture confirmed\|Stopping at cycle 300" "$SMOKE_LOG" 2>/dev/null; then
        echo "[$(date)] 0.08 reached terminal state in log; waiting brief grace, then proceeding" \
            | tee -a "$MY_LOG"
        sleep 30  # let process finalize archive + exit
        break
    fi
    sleep 60
done

echo "[$(date)] launching sweep_v2: bash $SWEEP_SCRIPT" | tee -a "$MY_LOG"
nohup bash "$SWEEP_SCRIPT" > "$SWEEP_NOHUP_LOG" 2>&1 &
SWEEP_PID=$!
echo "[$(date)] sweep_v2 launched as PID $SWEEP_PID" | tee -a "$MY_LOG"
