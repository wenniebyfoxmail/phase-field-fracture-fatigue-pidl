#!/usr/bin/env bash
# Chained v4 watcher: after α-1 smoke (Umax=0.12, --n-cycles 10) finishes,
# automatically relaunch oracle 0.10 from existing checkpoint_step_55.
#
# Per Mac SWAP request 2026-04-27 (commit c61e50c) + user 21:25 confirmation:
# 0.10 worker (PID 38147) was killed mid-step-56; archive
# `..._N300_R0.0_Umax0.1_oracle_zone0.02/` retains checkpoints up to step 55.
# `model_train.py:266-292` resume logic globs `checkpoint_step_*.pt` and picks
# the latest → continues from step 56.

set -u

SENS=/c/Users/xw436/phase-field-fracture-fatigue-pidl/SENS_tensile
PY="C:/Users/xw436/Python310/python.exe"
ALPHA1_PID=39347
ALPHA1_LOG="$SENS/run_alpha1_smoke_Umax0.12.log"
ORACLE_RESUME_LOG="$SENS/run_e2_reverse_Umax0.10_resumed.log"
MY_LOG="$SENS/_queue_chained_v4_alpha1_then_oracle_0.10.watcher.log"

export FEM_DATA_DIR="C:\\Users\\xw436\\GRIPHFiTH\\Scripts\\fatigue_fracture"

cd "$SENS"
echo "[$(date)] chained_v4 watcher starting; waiting on α-1 smoke PID $ALPHA1_PID to finish" \
    | tee -a "$MY_LOG"

# Poll α-1 process death (process exits cleanly whether by 10-cycle cap or fracture)
while true; do
    if ! ps -ef | awk -v p="$ALPHA1_PID" '$2 == p { f=1 } END { exit !f }'; then
        echo "[$(date)] α-1 smoke PID $ALPHA1_PID exited; checking log for state" \
            | tee -a "$MY_LOG"
        sleep 5  # let final flush land
        break
    fi
    sleep 60
done

# Brief pause + report α-1 final state
LAST_STEP=$(grep -cE "Fatigue step" "$ALPHA1_LOG")
LAST_ALPHA=$(grep -oE "ᾱ_max=[0-9.eE+-]+" "$ALPHA1_LOG" | tail -1)
FRAC=$(grep -E "Fracture confirmed" "$ALPHA1_LOG" | tail -1)
echo "[$(date)]   α-1 smoke final: $LAST_STEP fatigue steps, last $LAST_ALPHA" \
    | tee -a "$MY_LOG"
[ -n "$FRAC" ] && echo "[$(date)]   $FRAC" | tee -a "$MY_LOG"

# Relaunch oracle 0.10 (resume from checkpoint_step_55)
echo "[$(date)] relaunching oracle 0.10: python -u run_e2_reverse_umax.py 0.10" \
    | tee -a "$MY_LOG"
PYTHONIOENCODING=utf-8 "$PY" -u run_e2_reverse_umax.py 0.10 \
    > "$ORACLE_RESUME_LOG" 2>&1
EC=$?

if [ $EC -eq 0 ]; then
    echo "[$(date)] oracle 0.10 resume finished cleanly (exit 0)" | tee -a "$MY_LOG"
else
    echo "[$(date)] oracle 0.10 resume exited with code $EC" | tee -a "$MY_LOG"
fi
