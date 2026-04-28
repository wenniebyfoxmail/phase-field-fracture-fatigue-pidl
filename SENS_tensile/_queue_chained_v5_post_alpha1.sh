#!/usr/bin/env bash
# Chained v5 watcher: after α-1 production (Umax=0.12, --n-cycles 300, PID 43368)
# fractures, sequentially fire P2 (Variant B oracle, zone=0.005) → P3 (oracle 0.10
# fresh re-run). Per Mac priority queue 2026-04-28 (commit 52ad99d).
#
# P4 (oracle 0.09 + 0.08 N=500) intentionally NOT chained per Mac "P4 most droppable".
# User can manually launch P4 after P3 if desired.
#
# Avoids GPU contention: serial only, never parallel.

set -u

SENS=/c/Users/xw436/phase-field-fracture-fatigue-pidl/SENS_tensile
PY="C:/Users/xw436/Python310/python.exe"
ALPHA1_PID=43368
ALPHA1_LOG="$SENS/run_alpha1_Umax0.12.log"
P2_LOG="$SENS/run_e2_reverse_Umax0.12_variantB.log"
P3_LOG="$SENS/run_e2_reverse_Umax0.10_fresh.log"
MY_LOG="$SENS/_queue_chained_v5_post_alpha1.watcher.log"

OLD_010_DIR="$SENS/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.1_oracle_zone0.02"
RENAMED_010_DIR="${OLD_010_DIR}_resumed"

export FEM_DATA_DIR="C:\\Users\\xw436\\GRIPHFiTH\\Scripts\\fatigue_fracture"

cd "$SENS"
echo "[$(date)] chained_v5 watcher starting; waiting on α-1 production PID $ALPHA1_PID to finish" \
    | tee -a "$MY_LOG"

# ---- Phase 1: wait for α-1 production to exit ------------------------------
while true; do
    if ! ps -ef | awk -v p="$ALPHA1_PID" '$2 == p { f=1 } END { exit !f }'; then
        echo "[$(date)] α-1 PID $ALPHA1_PID exited; brief grace then proceed" \
            | tee -a "$MY_LOG"
        sleep 30  # let final flush land
        break
    fi
    sleep 60
done

# Quick α-1 sanity report
A1_STEPS=$(grep -cE "Fatigue step" "$ALPHA1_LOG")
A1_LAST_ALPHA=$(grep -oE "ᾱ_max=[0-9.eE+-]+" "$ALPHA1_LOG" | tail -1)
A1_FRAC=$(grep -E "Fracture confirmed" "$ALPHA1_LOG" | tail -1)
echo "[$(date)]   α-1 final: $A1_STEPS fatigue steps, last $A1_LAST_ALPHA" \
    | tee -a "$MY_LOG"
[ -n "$A1_FRAC" ] && echo "[$(date)]   $A1_FRAC" | tee -a "$MY_LOG"

# ---- Phase 2: P2 — Variant B oracle 0.12 with smaller zone ------------------
echo "[$(date)] P2 launching: Variant B oracle 0.12 --zone-radius 0.005" \
    | tee -a "$MY_LOG"
PYTHONIOENCODING=utf-8 "$PY" -u run_e2_reverse_umax.py 0.12 --zone-radius 0.005 \
    > "$P2_LOG" 2>&1
EC=$?
if [ $EC -eq 0 ]; then
    echo "[$(date)] P2 finished cleanly (exit 0)" | tee -a "$MY_LOG"
else
    echo "[$(date)] P2 exited with code $EC — continuing to P3 anyway" | tee -a "$MY_LOG"
fi

# ---- Phase 3: P3 — Oracle 0.10 RE-RUN fresh (rename old _resumed) ----------
echo "[$(date)] P3 prep: renaming existing 0.10 archive to _resumed" | tee -a "$MY_LOG"
if [ -d "$RENAMED_010_DIR" ]; then
    echo "[$(date)] WARN: $RENAMED_010_DIR already exists, leaving as-is" | tee -a "$MY_LOG"
elif [ -d "$OLD_010_DIR" ]; then
    mv "$OLD_010_DIR" "$RENAMED_010_DIR"
    echo "[$(date)]   renamed: $(basename "$RENAMED_010_DIR")" | tee -a "$MY_LOG"
else
    echo "[$(date)] WARN: $OLD_010_DIR missing, P3 will write to clean path anyway" | tee -a "$MY_LOG"
fi

echo "[$(date)] P3 launching: Oracle 0.10 fresh (no resume)" | tee -a "$MY_LOG"
PYTHONIOENCODING=utf-8 "$PY" -u run_e2_reverse_umax.py 0.10 \
    > "$P3_LOG" 2>&1
EC=$?
if [ $EC -eq 0 ]; then
    echo "[$(date)] P3 finished cleanly (exit 0)" | tee -a "$MY_LOG"
else
    echo "[$(date)] P3 exited with code $EC" | tee -a "$MY_LOG"
fi

echo "[$(date)] chained_v5 queue COMPLETE (P2 + P3 done)" | tee -a "$MY_LOG"
echo "[$(date)] P4 (0.09 + 0.08 N=500) NOT chained; user can manually launch if desired" \
    | tee -a "$MY_LOG"
