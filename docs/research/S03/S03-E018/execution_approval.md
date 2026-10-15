# S03-E018-R001 本地训练剖面检查 — 待执行审批

2026-10-15。用户已确认4446111方案。本轮仅实现新脚本、合成测试、
独立代码审查和确切命令；没有载入真实场生成新剖面，Run目录尚未创建。

## 本次拟批准的唯一动作

在Mac本地执行一次离线训练侧检查，使用已验收E016-R001/R002文件。
对主带b=3.6mm、x=0.9*i（i=-18..18）的37对位置，比较DIC、直接CST采样、
复用原DIC四邻权重的模型采样。三机械臂old/proxy/intact均报告法向、切向
配对增量；同一模型两接口共用完整648训练点、继承面积权重的theta。
不重选四邻、不改负权重、不扣背景、不量新裂尖、不进行求解或拟合。

代码版本：63cf057fdc6973ecc3147898b39a7f42b4db51b3。
新增scripts/aa2024_training_profile_consistency.py及合成测试；原数值源、
既有图器/E017辅助函数和E016四组预测不变。
协议experiment.md SHA256：
42fe3505d5616f82879dda113af1f211b45ba76cd85442eb94d8745f7f59ab27。
独立审查完成状态见review.md；仅代码及命令审查通过后才展示为可执行版本。
后续仅记录审查/审批状态的文档提交不改变上述代码快照。

输入仅项目local_archive/experiments/S03-E016中的：

- R001/prepare：4个PREP产物和成功收据；实际载入prepared.npz和
  training_geometry.npz。按39970个联合有限原facet ID映射，不使用ID-1。
- R002/fit：完整FIT哈希链及成功收据；实际仅载入solved_fields.npz。
  frozen_predictions.npz只作字节哈希核对，**不载入高载预测数组**。

代码先核对两份预定收据SHA、原runner/依赖与产物SHA、阶段/循环/参考态，
再载入这三个训练侧NPZ。检查原648点采样、网格/边界身份、四邻同侧与域、
仿射再现、37点raw opening重构；任意异常停止，不丢点或改变协议。
不读取R003目标/残差、E017逐点文件、原ZIP/nodemap或任何新留出。

输出仅新local_archive/experiments/S03-E018/S03-E018-R001/analysis/：
37点三臂表profiles.csv、profiles.npz、summary.csv、report.json；两张PNG/PDF
及同名说明、README_analysis.md、含前后来源和11项产物哈希的执行收据。
Run根保存本审批文本副本与run.log。

## 预算与停止规则

- 单线程CPU，0次求解/参数拟合；一次分析，不自动重试。
- 分析函数进入起软60秒，覆盖输入核对、采样/代数、绘图/保存及最终哈希、
  成功收据写入后检查；晚完成亦记失败，产物仅作取证。不是强制60秒杀进程。
- 代码字节核对、Run/日志准备属于分析前操作，不计算真实场。
- 新警告提升为错误，包括Python导入期；任意身份/有限性/越界/算术/输出
  异常立即停，保留现场，不覆写既有Run，不自动重跑或改环境消警。
- 旧文件前后SHA必须相同。不改mesh/BC/damage/q/材料/尺度/背景/端点，
  不blend、拟合比例、变带或筛点；不重跑prepare/fit/validate/旧render。
- 不联网、SSH、push、发送消息或文件。stage15不用于本次计算或调整。
- 完成后仅检查这次已有输出完整性、图形和独立验收，不重新生成图/分析。

## 确切待批准命令（仅展示，未执行）

没有外部账号、收件人/提交对象、附件或对外承诺。所有操作只在本机。
下列命令在新shell中顺序执行，任一步失败即停。

```bash
set -euo pipefail
task_repo='/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013'
task_base='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E018'
task_run="$task_base/S03-E018-R001"
task_py='/Users/wenxiaofang/miniconda3/bin/python3'
cd "$task_repo"
export PYTHONDONTWRITEBYTECODE=1 PYTHONWARNINGS=error CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1

# 只核对本地代码，不载入真实NPZ；任何字节不同即停止。
"$task_py" - <<'PY'
import subprocess
from pathlib import Path
snapshot='63cf057fdc6973ecc3147898b39a7f42b4db51b3'
names=['aa2024_training_profile_consistency.py','aa2024_frozen_error_decomposition.py',
       'aa2024_geometry_result_view.py','aa2024_geometry_prior.py','aa2024_boundary_basis.py',
       'aa2024_triplet_structure.py','aa2024_patch_mechanics.py','aa2024_rigid_observable.py']
paths=['scripts/'+n for n in names]+['docs/research/S03/S03-E018/experiment.md']
for name in paths:
    expected=subprocess.check_output(['git','show',snapshot+':'+name])
    if Path(name).read_bytes()!=expected:raise ValueError('reviewed source changed: '+name)
PY

mkdir -p "$task_base"
mkdir "$task_run"
cp docs/research/S03/S03-E018/execution_approval.md "$task_run/00_intent_approved.md"

"$task_py" -u scripts/aa2024_training_profile_consistency.py \
  --prepare '/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016/S03-E016-R001/prepare' \
  --fit '/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016/S03-E016-R002/fit' \
  --output "$task_run/analysis" \
  --source-commit 63cf057fdc6973ecc3147898b39a7f42b4db51b3 \
  --run-id S03-E018-R001 \
  > "$task_run/run.log" 2>&1
```

这是已知结果后的训练剖面接口诊断，不是独立留出验证或新预测。
r_direct=r_op+r_match是向量恒等式，范数不可加；A仅为本37点等权剖面的
接口净差额，不能归因为噪声/材料/三维或分摊E017原面积加权MAE差距。
proxy先验本就用过训练开口，本次也不能验证真实裂尖或相场/材料可辨识性。
结果用于决定下一项最小诊断，不据此在stage15上调参。新方案或执行仍需审批。
