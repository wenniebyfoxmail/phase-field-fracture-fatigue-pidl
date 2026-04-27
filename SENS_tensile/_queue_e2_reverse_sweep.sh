#!/usr/bin/env bash
# Sequential Task 1 oracle-driver sweep — Umax in {0.08, 0.09, 0.10, 0.11}.
# Uses Mac's option-C fem_supervision (auto-discover + FEM_DATA_DIR env).
# Excludes 0.12 because smoke test is already running on 0.12.
#
# Per Mac handoff (2026-04-27 [decision+done] commit ac773a7) + Windows
# [finding] (2026-04-27 commit 2139149): full per-cycle FEM data on Windows.
# FEM_DATA_DIR points at the GRIPHFiTH parent that contains
# SENT_PIDL_<NN>_export/psi_fields/cycle_NNNN.mat for NN ∈ {08,09,10,11,12}.

set -u  # do NOT set -e (continue past per-case failures)

SENS=/c/Users/xw436/phase-field-fracture-fatigue-pidl/SENS_tensile
PY="C:/Users/xw436/Python310/python.exe"
WATCHER_LOG="$SENS/_queue_e2_reverse_sweep.watcher.log"

export FEM_DATA_DIR="C:\\Users\\xw436\\GRIPHFiTH\\Scripts\\fatigue_fracture"

cd "$SENS"
echo "[$(date)] Task 1 oracle-driver sweep starting (Umax: 0.08, 0.09, 0.10, 0.11)" \
    | tee -a "$WATCHER_LOG"
echo "[$(date)]   FEM_DATA_DIR=$FEM_DATA_DIR" | tee -a "$WATCHER_LOG"

for UMAX in 0.08 0.09 0.10 0.11; do
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

echo "[$(date)] Task 1 oracle-driver sweep queue complete" | tee -a "$WATCHER_LOG"
