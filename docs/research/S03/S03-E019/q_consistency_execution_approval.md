# E019-D02 v0.1 — 精确执行包，尚未执行

2026-10-17；Pro方案PASS_PLAN与独立本地方案PASS_STATIC_PLAN。用户仅授权
代码/合成测试设计/命令准备和独立只读代码审查，未授权测试或诊断。
代码、测试和约定快照：b6195191fe35dee7ac093619ceadbc4920d0eedb。
独立静态代码审查完成后才展示执行审批；本稿不声称语法/导入/测试成功。

实现：[新算法](../../../../scripts/aa2024_qconsistent_repair.py)、
[启动器](../../../../scripts/aa2024_qconsistent_launch.py)、
[人工测试](../../../../tests/test_aa2024_qconsistent_repair.py)、
[测试设计与停止规则](q_consistency_test_design.md)。
方案/完整Pro正文与回复见q_consistency_repair_plan.md及q_consistency_plan_review.md。
旧源码、协议、阈值和冻结产物不改；不读原数值归档、真实数组或留出。

## 请先只考虑A，B绝不自动衔接

两命令各自单线程CPU、CUDA禁用、隔离Python -I/-B/-W error、各自60秒预算，
固定来源清单与上述快照逐字节绑定，运行前要求worktree clean；期间和结束
再次核源码/worktree。目录已存在/软链、身份不符、超预算或非预期异常即停，
保留仅供取证的新产物，不自动重试/改参数/改目录。

START覆盖启动器标准库载入后续核对/导入/操作/保存/哈希/收据读回及最终检查。
信号计时从标准库加载后安装，原生调用未返回时可能迟发处理；不是严格墙钟
硬杀保证，但任何观察到≥60秒不能接纳成功。测试子进程只由自身wrapper管理。
收据elapsed_seconds为最终写回前取样，另有写回/读回/stdout后的预算检查，
不将其冒称精确完整总耗时。没有GPU或远程命令，无代码/文件外发。

## A — 仅人工单元测试（未运行，建议下一次仅批准此项）

17个test方法含subtests；真实QR全部禁用，用已知U/T stub检查候选数据流。
0实际QR、0SVD；不执行完整diagnose或render，不导入Matplotlib或旧producer。
只写全新local_archive/code_checks/S03-E019-D02-T001/tests.log和test_receipt.json。
首个非预期失败即停，不自动修后重跑，不进入B。

```bash
set -euo pipefail
cd '/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013'
export CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
unset PYTHONPATH PYTHONSTARTUP PYTHONHOME PYTEST_ADDOPTS PYTEST_PLUGINS MATPLOTLIBRC
'/Users/wenxiaofang/miniconda3/bin/python3' -I -B -W error scripts/aa2024_qconsistent_launch.py A --snapshot b6195191fe35dee7ac093619ceadbc4920d0eedb
```

## B — A通过后仍须单独批准的三例合成诊断（未运行）

启动器只从固定A目录核成功收据、前后完整源码清单、CPU/预算身份和日志SHA。
每例五模式、一次16×5薄QR，共3次；零SVD/eig/pinv/lstsq/数值秩/cond/FEM。
数值算法无显式逆；绘图内部二维仿射几何不属于数值修复分解。
原容差、原C2/C3负控、C2/C3来源区别及解析投影/五探针条件全部保持。
候选函数不接收A/s/V/clean参考，不回写H/Lr/y，不事后Qp/Qr。

独占新输出目录：
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D02/S03-E019-D02-R001。
保存report.json完整人工操作数及检查、summary.csv、q_identity_ratio.png/.pdf/.md、
execution_receipt.json；仅该新目录内可生成.mplconfig/.cache字体缓存。
新旧p/r及中间量齐全，不读取旧report或任何真实响应；不修改旧结果。

随B一并供审批的唯一预期初始化日志：首次导入绘图栈期间最多一次，
logger=matplotlib.font_manager，level=WARNING，完整正文严格等于
`Matplotlib is building the font cache; this may take a moment.`
如出现则原样保存到新收据，不视作数值异常；第二次或其他来源/正文/时段
一律停止。Python warning仍全为error，不继承旧V01许可，也不屏蔽其他警告。

```bash
set -euo pipefail
cd '/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013'
export CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
unset PYTHONPATH PYTHONSTARTUP PYTHONHOME PYTEST_ADDOPTS PYTEST_PLUGINS MATPLOTLIBRC
'/Users/wenxiaofang/miniconda3/bin/python3' -I -B -W error scripts/aa2024_qconsistent_launch.py B --snapshot b6195191fe35dee7ac093619ceadbc4920d0eedb
```

## 之后的界限

A通过只是人工单元测试通过；B succeeded只是候选计算/导出完成。B之后独立
只读算术/图形验收仍需完成，不重新QR或SVD，不在失败后自动修补/重算。
通过最多支持三个固定构造上的五维Q一致正交投影。真实A/Lr缺失，不能修好
旧E019或推断真实根因；训练侧真实复核、加q及任何求解仍须另立方案授权。
stage15不读、不调参，不当新留出；本轮也不读取新留出。
