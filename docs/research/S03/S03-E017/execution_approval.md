# S03-E017-R001 本地最小误差分解 — 待执行审批

2026-10-15。用户已确认5b9ab6e方案；本轮仅准备代码、合成测试、独立审查
及确切命令。真实分解尚未运行，目标Run目录尚未创建。

## 本次拟批准的唯一动作

Mac本地一次离线分析，使用已经验收的E016冻结产物；不重新解析任何nodemap。
只计算既定secant残差、三组力学相对secant偏离、原MAE净差额及固定B/O贡献；
平方C+I仅作辅助。四组原预测、原E016分数/结论均不改变，不拟合新预测。

代码版本：0bfbaf535f883dcefa2b6bc9484efe6c12cf6b47。
协议原文SHA256：c2dbcc77e283d9b11f912a99407cef618578790999f7b8de9dd25c1ccbc2da02。
新增脚本scripts/aa2024_frozen_error_decomposition.py；原数值源/图器不变。
独立审查范围与结论见review.md；后续只记录审批状态的文档提交不改变代码。

输入：

- E016-R001/prepare：已有训练增量/IDs/坐标/权重/alpha及元数据；
- E016-R002/fit：三组已保存采样位移、四组冻结预测及收据；
- E016-R003/validate与figures：已消费stage15的目标/残差、已验收分数/图器证据。

全部位于项目local_archive/experiments/S03-E016/，沿既有完整来源链、
成功收据和预定SHA逐项核验。仅646个原有顺序ID；先按同一子集构造全局P，
再做固定abs(y)<=3.6mm条带/外侧汇总，继承面积权重，不分区重投影。

输出：新local_archive/experiments/S03-E017/S03-E017-R001/analysis/，
一份CSV分解表、一份逐点NPZ、一份JSON算术报告、两张PNG/PDF与同名说明、
README和含输入/代码/产物前后哈希的执行收据。Run根保留审批文本副本及日志。

## 预算与停止规则

- 单线程CPU，0次求解/拟合；一次分析，不自动重试。
- 分析函数从进入开始软60秒，覆盖输入核对/分解/绘图/保存/源与产物哈希，
  并在最终成功收据写入后再次检查；晚完成也改记失败、只作取证。
- 源码版本核对、Run目录/日志准备是分析前操作；没有真实场计算。
- 新警告提升为错误，包括Python导入期；任意身份、有限性、算术或输出异常
  立即停止，保留现场。原E016历史警告仅保留既有说明，不改环境消除它。
- 任意既有Run或analysis目录存在即停，不覆盖；旧产物前后SHA必须相同。
- 原ZIP、所有原始nodemap（含stage15.txt）、其他循环/新留出均不读取。
- 不求解、调参、blend/最优缩放/区域扫描，不联网/SSH/push/外发文件或消息。
- 完成后只做原输出的只读完整性/图形与独立验收，不重跑原评分或绘图。

## 确切待批准命令（仅展示，未执行）

没有发件账号、外部收件人/提交对象或附件；所有操作仅在本机。
下列代码在一个新shell中顺序执行，任一步非零退出即停。

```bash
set -euo pipefail
task_repo='/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013'
task_base='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E017'
task_run="$task_base/S03-E017-R001"
task_py='/Users/wenxiaofang/miniconda3/bin/python3'
cd "$task_repo"
export PYTHONDONTWRITEBYTECODE=1 PYTHONWARNINGS=error CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1

# 仅核验本地源码；不载入真实NPZ。任一字节不同即停止。
"$task_py" - <<'PY'
import subprocess
from pathlib import Path
snapshot='0bfbaf535f883dcefa2b6bc9484efe6c12cf6b47'
names=['aa2024_frozen_error_decomposition.py','aa2024_geometry_result_view.py',
       'aa2024_geometry_prior.py','aa2024_boundary_basis.py','aa2024_triplet_structure.py',
       'aa2024_patch_mechanics.py','aa2024_rigid_observable.py']
paths=['scripts/'+n for n in names]+['docs/research/S03/S03-E017/experiment.md']
for name in paths:
    expected=subprocess.check_output(['git','show',snapshot+':'+name])
    if Path(name).read_bytes()!=expected:raise ValueError('reviewed source changed: '+name)
PY

mkdir -p "$task_base"
mkdir "$task_run"
cp docs/research/S03/S03-E017/execution_approval.md "$task_run/00_intent_approved.md"

"$task_py" -u scripts/aa2024_frozen_error_decomposition.py \
  --prepare '/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016/S03-E016-R001/prepare' \
  --fit '/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016/S03-E016-R002/fit' \
  --validation '/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016/S03-E016-R003/validate' \
  --output "$task_run/analysis" \
  --source-commit 0bfbaf535f883dcefa2b6bc9484efe6c12cf6b47 \
  --run-id S03-E017-R001 \
  > "$task_run/run.log" 2>&1
```

解释边界：这是已知结果后的误差账本，不是新的独立留出验证。它可以定位
力学偏离是否抵消/强化secant残差以及空间差额，不能单独区分DIC噪声、真实
非线性、三维、导出补偿与边界/材料的因果贡献。结果只用于准备下一项诊断，
不能据此在stage15上调参。任何新方案或对外动作仍需另行确认。
