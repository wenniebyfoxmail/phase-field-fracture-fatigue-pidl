# S03-E019-R001 固定边界运动学上限 — 待执行审批

2026-10-16。用户已确认E019 v2，本轮仅代码、合成测试、独立只读代码审查
和确切命令准备；未打开真实数组或启动真实分析，Run目录尚未创建。

## 本次拟批准的唯一动作

Mac本地一次训练侧观测空间计算：保持原41×21网格、120节点边界值、
648训练点/顺序/面积权重。只计算v2约定的加权刚体商、一次gesvd薄SVD、
唯一观测投影/平方误差下界与三组已保存平衡场的额外差距；不生成任意
oracle节点场、E018剖面、高载预测或新的物理反演结果。

代码快照5c3fb4a083c9ff2967faf046036091b695dad5d2；新增
scripts/aa2024_kinematic_capacity.py及对应合成测试。原数值源/图器不改。
协议SHA256 b956f21fa8c417d65d668ca876d91a35b04756c97318938eb95312e758b0cbde。
本审批文本和代码的独立审查状态以review.md/code_review.md为准；审查未通过
不得执行。后续仅记录状态的文档提交不改变受审代码与本命令字节。

实际仅载入E016-R001/prepare/prepared.npz与R002/fit/solved_fields.npz。
完整PREP/FIT回执/runner/依赖/产物链先按预定锚点核对；training_geometry.npz、
frozen_predictions.npz只核对字节哈希，绝不载入数组。保留原边界/旧采样
可行性，核对严格ROI及S_B=0；不释放边界、不正则化/改rank或调参。
不读取R003/stage15响应、E017逐点、E018新剖面、原ZIP/nodemap或新留出。

原四组预测、原权重及输入前后SHA必须相同。输出仅新
local_archive/experiments/S03-E019/S03-E019-R001/analysis/：
summary.csv、report.json、pointwise.npz；两张PNG/PDF、两同名说明、README；
含来源/代码/10项产物哈希的execution_receipt.json。Run根存原审批副本及日志。

## 已完成的合成检查及已知边界

主代理50项新测试及110项既有回归全部通过；同尺寸纯合成1296×1482矩阵
整套输入/一次SVD/绘图/保存约4.01秒。它不证明真实rank/预算/结果必通过。
两合成PNG已目视，官方sidecar验证通过。实际独立检查另记code_review.md。

最初合成测试在NumPy matmul触发RuntimeWarning并报错。新脚本将密集乘法
写为非BLAS的einsum显式收缩，与math.fsum交叉核对；不屏蔽警告、不改变
本机依赖/环境、不改旧数值代码，SVD仍固定SciPy float64 gesvd一次。
警告根因没有被本次实现解释；修订不是对旧E016结果或收据的改写。

S_B=0只说明内缩观测不直接采样边界，不能否定其经平衡传播的影响。
下界近零可能因宽松/欠定表示而得，不是物理状态、去噪或预测成功。
新648点加权RMS/平方账本不替代旧MAE或37点配对范数，也不分摊原高载误差。

## 预算和停止规则

- 单线程CPU，无GPU；一次SVD，0次FEM求解/刚度装配/物理参数拟合，不加q。
- 分析函数进入起软60秒，覆盖输入/矩阵/SVD/账本/图/保存/哈希及最终成功
  收据写入后的检查；SVD返回及各后续阶段都检查，晚完成记失败、仅作取证。
  这是软预算，不是强制60秒杀进程；没有自动延时、换producer/算法或重试。
- 代码字节核对和目录/日志准备在分析前，不计算真实场。
- 导入及运行新警告升为错误；非有限、身份/ROI/BC/采样/算术/输出异常即停。
  奇异值落入既定cutoff附近、旧场不在保留像空间亦停止，不改阈值救结果。
- 三臂分别按RMS_kin、gap与同一T（mm）分类；平方量只对T²，不作总赢家。
- 全新Run/analysis目录，存在即停，不覆盖，不重跑旧prepare/fit/validate/render。
- 不读取留出/其他cycle，不联网、SSH、push或向外发送消息/文件。
- 完成后仅只读检查现有输出与独立验收，不重新分析或重绘。

## 确切待批准命令（仅展示，未执行）

没有外部发件账号、收件人/提交对象、附件或承诺。新shell顺序执行，任何非零
退出即停。以下命令并未执行，需用户对本完整版本另行批准。

```bash
set -euo pipefail
task_repo='/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013'
task_base='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019'
task_run="$task_base/S03-E019-R001"
task_py='/Users/wenxiaofang/miniconda3/bin/python3'
cd "$task_repo"
export PYTHONDONTWRITEBYTECODE=1 PYTHONWARNINGS=error CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1

# 只核对本地源码/协议字节，不载入真实NPZ。
"$task_py" - <<'PY'
import subprocess
from pathlib import Path
snapshot='5c3fb4a083c9ff2967faf046036091b695dad5d2'
names=['aa2024_kinematic_capacity.py','aa2024_geometry_prior.py','aa2024_boundary_basis.py',
       'aa2024_triplet_structure.py','aa2024_patch_mechanics.py','aa2024_rigid_observable.py']
paths=['scripts/'+n for n in names]+['docs/research/S03/S03-E019/experiment.md']
for name in paths:
    expected=subprocess.check_output(['git','show',snapshot+':'+name])
    if Path(name).read_bytes()!=expected:raise ValueError('reviewed source changed: '+name)
PY

mkdir -p "$task_base"
mkdir "$task_run"
cp docs/research/S03/S03-E019/execution_approval.md "$task_run/00_intent_approved.md"

"$task_py" -u scripts/aa2024_kinematic_capacity.py \
  --prepare '/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016/S03-E016-R001/prepare' \
  --fit '/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016/S03-E016-R002/fit' \
  --output "$task_run/analysis" \
  --source-commit 5c3fb4a083c9ff2967faf046036091b695dad5d2 \
  --run-id S03-E019-R001 \
  > "$task_run/run.log" 2>&1
```
