#!/usr/bin/env bash
# Chained v3 watcher: after sweep_v2 (0.11 → 0.10 → 0.09) completes,
# resume Umax=0.08 with --n-cycles 500 from the existing checkpoint_step_299.
# Per Mac decision 2026-04-27 (commit 2f3bf0e) + Windows ack a68cbbe.
#
# Resume mechanic per Mac: rename the _N300_ archive to _N500_ first so the
# runner writes into the same dir; model_train.py:266-292 globs
# checkpoint_step_*.pt and continues from latest.

set -u

SENS=/c/Users/xw436/phase-field-fracture-fatigue-pidl/SENS_tensile
PY="C:/Users/xw436/Python310/python.exe"
SWEEP_LOG="$SENS/_queue_e2_reverse_sweep_v2.watcher.log"
MY_LOG="$SENS/_queue_e2_reverse_chained_v3_resume_0.08.watcher.log"
RESUME_LOG="$SENS/run_e2_reverse_Umax0.08_N500.log"

OLD_DIR="$SENS/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.08_oracle_zone0.02"
NEW_DIR="$SENS/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N500_R0.0_Umax0.08_oracle_zone0.02"

export FEM_DATA_DIR="C:\\Users\\xw436\\GRIPHFiTH\\Scripts\\fatigue_fracture"

cd "$SENS"
echo "[$(date)] chained_v3 watcher starting; waiting on sweep_v2 to print 'queue complete'" \
    | tee -a "$MY_LOG"

while true; do
    if grep -q "Task 1 oracle-driver sweep v2 queue complete" "$SWEEP_LOG" 2>/dev/null; then
        echo "[$(date)] sweep_v2 complete detected" | tee -a "$MY_LOG"
        break
    fi
    sleep 60
done

echo "[$(date)] step 1: rename _N300_ archive → _N500_" | tee -a "$MY_LOG"
if [ -d "$NEW_DIR" ]; then
    echo "[$(date)] WARNING: _N500_ dir already exists, aborting to avoid clobber" | tee -a "$MY_LOG"
    exit 1
fi
if [ ! -d "$OLD_DIR" ]; then
    echo "[$(date)] ERROR: _N300_ source dir missing, aborting" | tee -a "$MY_LOG"
    exit 1
fi
mv "$OLD_DIR" "$NEW_DIR"
echo "[$(date)] mv done: $(basename "$NEW_DIR")" | tee -a "$MY_LOG"

echo "[$(date)] step 2: launch resume — python -u run_e2_reverse_umax.py 0.08 --n-cycles 500" \
    | tee -a "$MY_LOG"
PYTHONIOENCODING=utf-8 "$PY" -u run_e2_reverse_umax.py 0.08 --n-cycles 500 \
    > "$RESUME_LOG" 2>&1
EC=$?

if [ $EC -eq 0 ]; then
    echo "[$(date)] 0.08 resume finished cleanly (exit 0)" | tee -a "$MY_LOG"
else
    echo "[$(date)] 0.08 resume exited with code $EC" | tee -a "$MY_LOG"
fi
