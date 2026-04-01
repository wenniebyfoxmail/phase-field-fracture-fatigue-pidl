#!/bin/bash
# 串行自动运行 Case E (Umax=0.08) → Case F (Umax=0.10)
# 崩了自动重启，跑完自动切换

SENS_DIR="/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/SENS_tensile"
CONFIG="$SENS_DIR/config.py"

run_until_done() {
    local UMAX=$1
    local LOG=$2
    local CKPT_DIR=$3
    local MAX_STEP=$4

    echo "[$(date)] === 开始 Umax=$UMAX ===" | tee -a "$LOG"

    while true; do
        # 检查是否已经完成
        LAST=$(ls "$CKPT_DIR" 2>/dev/null | grep "checkpoint_step_" | sort -V | tail -1 | grep -oE '[0-9]+')
        if grep -q "Fracture confirmed" "$LOG" 2>/dev/null; then
            echo "[$(date)] 检测到断裂，Umax=$UMAX 完成" | tee -a "$LOG"
            break
        fi
        if [ ! -z "$LAST" ] && [ "$LAST" -ge "$MAX_STEP" ]; then
            echo "[$(date)] 已跑满 $MAX_STEP 圈，Umax=$UMAX 完成" | tee -a "$LOG"
            break
        fi

        echo "[$(date)] 启动 Umax=$UMAX (从 checkpoint $LAST 续跑)" | tee -a "$LOG"
        cd "$SENS_DIR"
        python3 main.py >> "$LOG" 2>&1
        echo "[$(date)] 进程退出，5秒后重启..." | tee -a "$LOG"
        sleep 5
    done
}

# === Case E: Umax=0.08 ===
python3 -c "
import re
with open('$CONFIG', 'r') as f: content = f.read()
content = re.sub(r'\"disp_max\"\s*: \d+\.\d+.*', '\"disp_max\"     : 0.08,           # 峰值位移振幅（Case E）', content)
with open('$CONFIG', 'w') as f: f.write(content)
print('Config set to Umax=0.08')
"
CKPT_E="$SENS_DIR/hl_6_Neurons_100_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N600_R0.0_Umax0.08/best_models"
run_until_done "0.08" "$SENS_DIR/auto_caseE.log" "$CKPT_E" 599

# === Case F: Umax=0.10 ===
python3 -c "
import re
with open('$CONFIG', 'r') as f: content = f.read()
content = re.sub(r'\"disp_max\"\s*: \d+\.\d+.*', '\"disp_max\"     : 0.10,           # 峰值位移振幅（Case F）', content)
with open('$CONFIG', 'w') as f: f.write(content)
print('Config set to Umax=0.10')
"
CKPT_F="$SENS_DIR/hl_6_Neurons_100_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N600_R0.0_Umax0.1/best_models"
run_until_done "0.10" "$SENS_DIR/auto_caseF.log" "$CKPT_F" 599

echo "[$(date)] === 全部完成 ==="
