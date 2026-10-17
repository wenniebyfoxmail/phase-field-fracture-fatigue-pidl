# E019-D03-U01 — 执行包 v1（静态审查通过）

代码基线`b597d38f8d94dc2a69f89935a350859905d1e636`。
Pro PASS_PLAN及实现明确化见underflow_pro_review.md/underflow_implementation_contract.md。
测试方案见underflow_test_design.md。尚未运行测试或语法/导入检查。
独立只读代码审查PASS_STATIC_CODE，绑定clean d478b2d5；详情与五源码SHA
见underflow_code_review.md。以下tiny仅依已核实总部人方授权执行，不是
Pro或审查者授权；B002/C/D仍不执行。

## 人方授权与当前阶段

总部人方已明确批准tiny在Pro和独立代码审查后执行；原本“暂不测试”仅对
此tiny包解除，凭据见underflow_pro_review.md。未经静态审查通过不启动。
不因代码或Pro通过启动B002/C/D，不重跑B001，不读取真实数组/留出或旧report。
夜间Codex额度任一正常窗口剩余<80%或未知，不开新阶段，仅安全保存。
最近读取为7天used7%/remaining93%，不是remaining7%；主要阶段前后重查。

## 唯一拟执行的命令 A-U01

工作目录固定：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013`

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/test_aa2024_underflow.py --source-commit b597d38f8d94dc2a69f89935a350859905d1e636
```

只运行一次：41项新增+原24项人工stub回归，预期65项。single CPU/CUDA空、
整包60秒软完成预算、failfast，实际QR0/SVD0/求解0。计时从首个time导入后
即开始，涵盖其他导入、代码/Git身份、模型检查、测试及最终身份/打印检查；
另记录工具wall作为进程外观察，不把此软预算说成硬杀进程保证。
不自动重试，不运行另一个测试命令弥补失败，不变容差或操作数救结果。

读权限仅源码内人工位型、小数组、源文件原字节和本地Git；禁止NPZ/report/
真实及留出读取。np.load、两套linalg分解/求解、同尺寸artificial生成均拒绝；
load_real的true拒绝，false仅用于原权限负控在读之前停止。记录成功/失败
终端原文及工具exit/wall；没有产物覆盖或新图。本包不生成数值运行目录。

## 未来B002（仅可审阅草案，当前明确不执行）

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/aa2024_q_recheck.py synthetic --source-commit b597d38f8d94dc2a69f89935a350859905d1e636 --output /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03/S03-E019-D03-B002
```

这一同尺寸包才有1SVD/2QR及新图/证书，必须另批；tiny不能证明它的
证书、序列化/哈希及图都能在60秒内完成，也不能证明B001下溢无害。
当前不核查B002目录或真实资产；B001原样不读不改。C/D无本轮执行命令。

## 静态审查与执行前条件

- 独立Codex只读检查确切源码/命令：五site、预先掩膜、RN64证书、全分量
  原容差/失败见证、Fraction独立性、硬件模型、65项及守卫、身份/预算。
- 修订后重新固定代码基线并焦点复审，不借复审运行测试或读取产物。
- 审查后只允许docs记录提交，实际HEAD/clean及五源码SHA起止一致。
- 首个非预期异常/警告、模型不支持、参考分歧、预算/身份改变立即停止，
  不重试；保留通过组件和失败定位，不据此宣布反演或真实D03有效。
