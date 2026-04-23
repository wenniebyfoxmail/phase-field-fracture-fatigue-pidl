#!/bin/bash
# Auto-pivot watcher:
#   1. wait for "Finished: Umax=0.09" in run_sequential_coeff3.log
#   2. kill the running python process (PID arg)
#   3. launch run_only_Umax_008_fast.py
# Spawned in background; logs to _pivot_to_008_fast.watcher.log

set -u
PID="${1:?need python PID as arg}"
DIR=/c/Users/xw436/phase-field-fracture-fatigue-pidl/SENS_tensile
LOG="$DIR/run_sequential_coeff3.log"
WLOG="$DIR/_pivot_to_008_fast.watcher.log"

echo "[$(date)] watcher started, PID=$PID, polling $LOG" >> "$WLOG"

# Wait until Umax=0.09 finishes
while ! grep -q "Finished: Umax=0.09" "$LOG" 2>/dev/null; do
    sleep 60
done
echo "[$(date)] detected 'Finished: Umax=0.09'" >> "$WLOG"

# Small grace so the line flushes; then kill (Windows-style)
sleep 5
echo "[$(date)] killing PID $PID" >> "$WLOG"
taskkill //PID "$PID" //F >> "$WLOG" 2>&1

# Wait for process to actually die
sleep 10
if tasklist //FI "PID eq $PID" 2>/dev/null | grep -q "$PID"; then
    echo "[$(date)] WARN: PID $PID still alive after taskkill" >> "$WLOG"
fi

# Launch fast 0.08-only script
cd "$DIR" || exit 1
echo "[$(date)] launching run_only_Umax_008_fast.py" >> "$WLOG"
PYTHONIOENCODING=utf-8 nohup /c/Users/xw436/Python310/python.exe -u run_only_Umax_008_fast.py \
    > "$DIR/run_only_Umax_008_fast.log" 2>&1 &
NEW_PID=$!
echo "[$(date)] new PID=$NEW_PID" >> "$WLOG"
echo "[$(date)] watcher exiting" >> "$WLOG"
