#!/bin/bash
# auto_monitor_and_launch.sh
# 监控 Umax=0.08 N600 运行，结束后自动启动 Umax=0.10 N600

SENS_DIR="/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/SENS_tensile"
CONFIG_FILE="$SENS_DIR/config.py"
MONITOR_LOG="$SENS_DIR/auto_monitor.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$MONITOR_LOG"
}

log "=== 自动监控启动 ==="
log "等待 1 小时后开始检测..."
sleep 3600

log "开始检测训练进程..."

# 等待 main.py 结束（每 5 分钟检查一次，最多再等 3 小时）
MAX_WAIT=36  # 36 * 5min = 3 hours
COUNT=0
while pgrep -f "main.py" > /dev/null 2>&1; do
    COUNT=$((COUNT + 1))
    if [ $COUNT -ge $MAX_WAIT ]; then
        log "等待超时（3小时），强制继续..."
        break
    fi
    log "训练仍在运行... 5 分钟后再检查 (${COUNT}/${MAX_WAIT})"
    sleep 300
done

log "训练进程已结束，准备启动 Umax=0.10 case..."

# 读取最后的 crack_length 和 cycle 数
LAST_LOG="$SENS_DIR/training_caseE_Umax008_N600_cont.log"
if [ -f "$LAST_LOG" ]; then
    LAST_IDX=$(grep "idx:" "$LAST_LOG" | tail -1)
    LAST_CRACK=$(grep "L∞_length" "$LAST_LOG" | tail -1)
    log "Umax=0.08 最终状态: $LAST_IDX | $LAST_CRACK"
fi

# 修改 config.py: disp_max 0.08 → 0.10
log "修改 config.py: disp_max 0.08 → 0.10"
python3 -c "
import re
with open('$CONFIG_FILE', 'r') as f:
    content = f.read()

# 修改 disp_max
content = content.replace(
    '\"disp_max\"     : 0.08,',
    '\"disp_max\"     : 0.10,'
)
# 修改注释说明
content = content.replace(
    '# 峰值位移振幅（低于单调断裂值 0.155，可试 0.10/0.14）',
    '# 峰值位移振幅（低于单调断裂值 0.155；Case F: Umax=0.10）'
)

with open('$CONFIG_FILE', 'w') as f:
    f.write(content)
print('config.py 修改完成')
"

if [ $? -ne 0 ]; then
    log "❌ config.py 修改失败，终止"
    exit 1
fi

# 验证修改
DISP_MAX=$(grep '"disp_max"' "$CONFIG_FILE" | head -1)
log "验证 config: $DISP_MAX"

# 启动新训练
NEW_LOG="$SENS_DIR/training_caseF_Umax010_N600.log"
log "启动 Umax=0.10 N600 训练，日志: training_caseF_Umax010_N600.log"
cd "$SENS_DIR"
python3 main.py > "$NEW_LOG" 2>&1
EXIT_CODE=$?

log "Umax=0.10 训练结束，exit code: $EXIT_CODE"

# 汇报最终结果
if [ -f "$NEW_LOG" ]; then
    FINAL_IDX=$(grep "idx:" "$NEW_LOG" | tail -1)
    FINAL_CRACK=$(grep "L∞_length" "$NEW_LOG" | tail -1)
    FRACTURE=$(grep "Fracture confirmed" "$NEW_LOG" | tail -1)
    log "=== Umax=0.10 最终结果 ==="
    log "$FINAL_IDX"
    log "$FINAL_CRACK"
    [ -n "$FRACTURE" ] && log "$FRACTURE" || log "未触发断裂判据（跑满600圈）"
fi

log "=== 自动监控完成 ==="
