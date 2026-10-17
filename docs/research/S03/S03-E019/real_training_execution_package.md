# E019-D03 v0.2 — 执行包（只准备，未执行）

2026-10-17。Pro PASS_PLAN，见[完整回复](real_training_pro_reply.md)与
[采纳附录](real_training_recheck_v02.md)。代码基线
`a3352a6954543f965d559a1f1a6452cf9e58b2fb`，静态代码审查状态另见[review](real_training_code_review.md)；
独立复审已给PASS_STATIC_CODE（snapshot53c38443）；24项仍未运行，预算与真实资产
仍未核验，不因静态通过自动取得执行许可。

## 范围与分步审批

| 命令 | 输入/产物 | 预算与计算 | 当前状态 |
|---|---|---|---|
| A | 源码内人工24项单元，不读任何report/NPZ/真实/留出；仅终端输出 | 单线程CPU/60s；QR/SVD仅stub，零实际分解 | 待单独批准 |
| B | 新造648点/原尺寸网格/3个人工节点场，新B001全生产产物 | 单线程CPU/60s；1gesvd、2薄QR；包含全量自检/保存/图/哈希 | A通过后另批 |
| B验收 | B001保存操作数与图说明，只写B001-acceptance | 独立60s；零分解；BLAS全量+完整fsum/Decimal80 | B完成后另批 |
| C | 原stage13/14白名单资产，新R001，不重求解 | 单线程CPU/60s；1gesvd、2薄QR | A/B/独立验收及真实清单可用性确认后另批 |
| D | C保存操作数与同一源白名单，新R001-acceptance | 独立60s；零分解；不重绘 | C完成后另批 |

当前不运行A/B/C/D，不导入代码、不做语法检查、SVD/QR、真实/留出读取或绘图。
合成资源检查不是旧D02的三个16×5例：它覆盖实际1296×1482构造、全量
矩阵检查、1SVD/2QR、完整证书及两图/说明/哈希。人工支持和rank不要求
等于真实1203，只测试资源及保存数值一致性，不证明真实准确性或物理效果。

## 文件与信息权限（C/D未来审批时须逐项包含）

共同前缀：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016/`

| 文件 | 原字节读取 | 允许解码 |
|---|---|---|
| S03-E016-R001/prepare/execution_receipt.json | SHA锚8655d49b30e341d488eeb8c15db9a7d347f236634a22adbbf39fcb7b4bbd3ccf | 成功/模式/Run/产物来源 |
| 同目录preparation.json、geometry_audit.json | 哈希 | 训练cycle/ref/stage/forces及来源；不利用高载信息生成新量 |
| 同目录prepared.npz | 哈希 | 仅ids/xy/weights/train_v/mesh/tri/boundary/bc |
| 同目录training_geometry.npz | **另需明示批准，只opaque SHA** | 无 |
| S03-E016-R002/fit/execution_receipt.json | SHA锚3173f0f659d6e451f7fccc39a4ca0973ae3caad750c9d98ce754a1bcec325674 | 成功/模式/Run/产物来源 |
| 同目录fit.json | 哈希 | 原PREP来源及固定cycle/status |
| 同目录solved_fields.npz | 哈希 | old/proxy/intact和三组*_sampled；不读damage |
| 同目录frozen_predictions.npz | **另需明示批准，只opaque SHA** | 无 |

所有数组权限当前未使用；未核实际可用性，未核真实文件SHA。原alpha/u13、
高载预测数组、stage15响应、其他cycle/新留出、旧E019数组/谱均不解码。
C/D的`--allow-two-opaque-hashes`只表示该次命令明确批准的两个原字节哈希，
不是任何数组或留出授权。不批准就停在准备，不能默认为整包来源通过。

## 确切命令

以下每段是独立的一次性命令，不能串联或自动继续。工作目录固定为
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013`。
使用系统既有Python；`-B`不写pycache，`-W error`覆盖导入期warning。三个脚本
在导入NumPy/SciPy前安装Python warning及logging WARNING停止策略，无字体例外。
源码基线与实际HEAD分别记录；
后续仅docs提交可附加审查记录，代码任一改动必须重新固定基线并复审。

### A — 仅人工单元（最先申请执行的一项）

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/test_aa2024_q_recheck.py --source-commit a3352a6954543f965d559a1f1a6452cf9e58b2fb
```

24项覆盖：干净投影、给定泄漏、输入不回写、QR联动符号、零/非有限对角、
eta=.5及越界/行和、额外QR/SVD拒绝、固定driver、量纲容差、60秒边界、
CST仿射/交错分量/ROI、只解码指定键、opaque未批准先停、独立完整向量、
参考路径分流、Python/logging人工停止控制、假软链拒绝、runtime HEAD改变。
这些人工预期异常均在测试设计内断言，不是运行真实日志或读取真实路径。
分解均为人工stub；守卫禁止真实QR/SVD/solve/lstsq/pinv及
任何np.load。fake容器测试不打开文件。单元成功不证明实际QR或资源可行。
首个非预期测试失败由failfast停止，最终耗时≥60秒亦非完成；不启动B。

### B — 同尺寸人工资源试验（以后另批）

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/aa2024_q_recheck.py synthetic --source-commit a3352a6954543f965d559a1f1a6452cf9e58b2fb --output /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03/S03-E019-D03-B001
```

### B验收 — 已保存人工证书（以后另批）

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/aa2024_q_verify.py synthetic --source-commit a3352a6954543f965d559a1f1a6452cf9e58b2fb --input /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03/S03-E019-D03-B001 --output /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03/S03-E019-D03-B001-acceptance
```

### C — 真实训练新数值复核（以后另批，非当前可执行许可）

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/aa2024_q_recheck.py real --allow-two-opaque-hashes --source-commit a3352a6954543f965d559a1f1a6452cf9e58b2fb --output /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03/S03-E019-D03-R001
```

### D — 真实保存算术独立核验（以后另批）

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/aa2024_q_verify.py real --allow-two-opaque-hashes --source-commit a3352a6954543f965d559a1f1a6452cf9e58b2fb --input /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03/S03-E019-D03-R001 --output /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03/S03-E019-D03-R001-acceptance
```

## 独立验收表达式与限制

核验器不导入producer：独立循环CST、DOF枚举、fsum质心/二阶矩、D/R/U0
以及源数组身份；dgemm全量A=QDSF、H重构/Gram、U/Lr/Vr全Gram、B=QLr、
UT=B、QU=U、原保留奇异对双侧作用。无新分解或抽列代替全量。
完整y/p/r/legacy/b向量分别用fsum和Decimal80核投影、Q数值/状态、Uᵀr、
像内、残差加法；平方和/交叉项/最终保存等式/算术分类独立计算。
高精度从保存float精确导入，参考不回写候选，Q跨路径不符专属未决分流，
不要求ratio标量额外相等。任一不符停止，无自动算法切换。

生产保存A/H/C_H/R/D(stored scale)/原source白名单副本、stencil/自由度/U0、
s/mask/tau/Lr/Vh_r/B/U/T、实际y/b/z、新旧p/r及Q求值、每臂r/d。
完整SVD重构只producer自检；不宣称独立重现未保存全L/Vh或未保留谱。
真实rank不同于1203只触发身份审查，不降秩/改cutoff继续；报实际r。

图为D^{-1}r展示与三臂平方账本，PNG/PDF/同名md均从新产物生成；数值验收
不等于视觉验收。数值通过后再单独只读打开原PNG，检图完整支持/同标度/
标题单位/图说明，PDF不因PNG通过而声称视觉通过。此次不打开或生成图。

## 完成与停止规则

- 原阈值、原输入/权重/648点/BC及四组冻结高载预测不变；0物理求解/训练/q。
- 预算为软完成预算：主要步骤前后、保存/图、输入复核、产物哈希、收据及
  完成标志写后检查；达到60秒不接纳，正在运行的核可结束，不是硬杀进程。
- 首个异常/新warning/nonfinite/身份/BC/采样/截断/eta/正交/Q/像内/账本/
  输出或预算失败即停，不重试、不追加工况、不扩时、不换driver/精度/阈值。
- 不继承旧字体日志豁免；本包没有预期warning，若出现需停止并报告。
- A/B/C/D起止核代码SHA/HEAD/clean；真实D完成前再次核全部源字节。固定
  输入/输出及每层祖先拒绝软链，输入必须普通文件。B/C绘图库首次导入前
  将MPLCONFIGDIR与XDG_CACHE_HOME置于新Run的.mplconfig/.cache，仅新根内缓存写入。
- 仅新独占目录；原源文件前后哈希不变；成功需receipt+completion绑定且无
  failure收据。超时或失败的部分证书/图片不接纳。无执行结果时不声称就绪。
- A/B/独立算术/视觉/真实来源就绪分别报告；Code Ready不等于上述任一已通过。
