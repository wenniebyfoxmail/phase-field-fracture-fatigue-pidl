#!/usr/bin/env bash
# Task 1 oracle-driver sweep v2 — REVERSED order per user request 2026-04-27.
# Order: 0.11 → 0.10 → 0.09 (smaller-N_f first → faster data, save longest 0.09 for last).
# Excludes 0.08 (already running as orphan PID 33907) and 0.12 (smoke done).

set -u

SENS=/c/Users/xw436/phase-field-fracture-fatigue-pidl/SENS_tensile
PY="C:/Users/xw436/Python310/python.exe"
WATCHER_LOG="$SENS/_queue_e2_reverse_sweep_v2.watcher.log"

export FEM_DATA_DIR="C:\\Users\\xw436\\GRIPHFiTH\\Scripts\\fatigue_fracture"

cd "$SENS"
echo "[$(date)] Task 1 oracle-driver sweep v2 starting (Umax: 0.11, 0.10, 0.09)" \
    | tee -a "$WATCHER_LOG"
echo "[$(date)]   FEM_DATA_DIR=$FEM_DATA_DIR" | tee -a "$WATCHER_LOG"

for UMAX in 0.11 0.10 0.09; do
    LOG="$SENS/run_e2_reverse_Umax${UMAX}.log"
    echo "[$(date)] launching Umax=${UMAX} → ${LOG}" | tee -a "$WATCHER_LOG"
    PYTHONIOENCODING=utf-8 "$PY" -u run_e2_reverse_umax.py "$UMAX" \
        > "$LOG" 2>&1
    EC=$?
    if [ $EC -eq 0 ]; then
        echo "[$(date)] Umax=${UMAX} finished cleanly (exit 0)" | tee -a "$WATCHER_LOG"
    else
        echo "[$(date)] Umax=${UMAX} exited with code $EC — continuing" | tee -a "$WATCHER_LOG"
    fi
done

echo "[$(date)] Task 1 oracle-driver sweep v2 queue complete" | tee -a "$WATCHER_LOG"
