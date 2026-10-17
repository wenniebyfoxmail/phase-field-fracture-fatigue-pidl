# E019-D02 图说明派生修订 V01 — 仅准备，等待执行审批

2026-10-17。用户本轮仅授权执行包准备、独立只读静态审查及展示；
未授权运行本脚本、测试、生成修订文件或继续原验收。

## 目的与边界

只修复[原停验记录](q_consistency_evidence_review.md)中的两项说明问题，
不更改算法、五模式、阈值、数值、图形、收据或原源码。
这是 tooling-only / synthetic 文字修复，不改变旧 E019 或 D02 的科学结论。
最低代价是对原说明做两处字节替换；不需要重新生成任何数值/图形。
同名原 sidecar 必须保留，因此新文件是显式映射的 companion，不伪装为
原目录官方 same-stem 检查已通过。后续整体只读验收仍须另行批准其方案。

当前状态：独立静态审查待完成；未做导入/语法/测试或执行预检。

## 唯一两处文字变化（其他字节原样保留）

1. 原章节标题：

   `## Visual grammar and panel guide`

   新标题：

   `## How to read: visual grammar and panel guide`

2. 原句：

   `Full primary analytic-p/r ratios and all five image/Pythagoras probes are in report.json and summary.csv.`

   新句（完整一行）：

   `Full primary analytic-p/r ratios and all five image/Pythagoras probe details are in report.json. summary.csv contains case-level summary columns only; it does not contain the five-probe details.`

明细来源依据：冻结 producer 的 `probes` 保存定义、launcher 的七列 CSV
导出定义和上一轮已读停止记录；本轮不重新读取 report/CSV 或其数组。
所有图中数值与原说明数值直接保留，不重新确认、解释或重新评分。

## 固定来源、新文件与不覆盖承诺

来源目录（以下 basename 全在此目录内）：

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D02/S03-E019-D02-R001`

- 唯一原内容输入：`q_identity_ratio.md`，SHA256
  `0788c0190a6906f633d01fbbc985ff60e765fdf0af7939a98e0a2cac101df0fc`。
- 唯一新说明：`q_identity_ratio.sidecar_v01.md`。
- 唯一新收据：`q_identity_ratio.sidecar_v01.receipt.json`，记录父说明 SHA、
  代码 SHA、新说明 SHA、两处替换和 PNG/PDF 的绝对路径映射。
- 两新文件均必须不存在（包含坏软链）；用 `xb` 独占创建，禁止覆盖。
- 源说明和新代码检查所有祖先/文件类型，拒绝软链；源说明写前/写后
  逐字节核对不变，代码写后再核对不变。并非全目录 syscall 审计。
- 不打开 report.json、summary.csv、PNG/PDF、原执行收据、旧数值归档、
  真实数组、stage15 或新留出内容；不修改或复制这些文件。
- 新文件仍在原目录，因此说明中 report/CSV/PNG/PDF 的相对位置不漂移。
- 不改 `q_identity_ratio.md`；普通官方目录 validator 仍会读到旧说明并
  失败，本命令既不运行它，也不将 companion 自检冒称官方目录通过。
- 后续若采用 companion，必须在新验收协议中明确 PNG/PDF→该 companion
  的映射；本命令不会自动采用它、恢复验收或修改 validator。

## 预算、停止与允许操作

单线程 CPU、60 秒；仅 Python 标准库和字节/文本/哈希/JSON 操作。
不导入 NumPy、Matplotlib、producer、旧验收脚本；零重算/重绘/QR/SVD。
计时覆盖标准库加载后的 main、来源检查、替换、新文件写回/读回及最终
stdout 后检查；SIGALRM 并非系统级硬杀保证，解释不变。
收据耗时是写前取样，不冒称最终总耗时；exit0 还要求最终预算检查完成。
Python warning 当 error，普通 logging WARNING 及以上立即停止。
本命令不初始化字体缓存，没有任何字体或其他警告例外。

身份/环境不符、源变化、任一新路径已存在、替换次数非一、短语缺失、
读写失败、超预算或首个非预期异常：立即停止，保留可能的新局部文件供
取证；不清理、不续写、不修复、不更名重试。即使留下收据也必须以
exit0/最终 stdout 后预算检查为完整执行条件，不能只看收据状态。

自检仅是两处文本变化和新文件读回，不是继续独立算术/图形验收。
若通过，原验收状态依然暂停，需用户另批剩余验收。

## 确切命令（审查通过后才供用户批准执行一次）

运行代码：`scripts/aa2024_d02_sidecar_v01.py`，代码 SHA256
`2247849e9535414ef67762893e4a17194cd448606d062a4ccfcfa91b9805eab2`。
命令中的脚本 SHA 在审批前固定，不允许执行时自动计算替代。

```bash
set -euo pipefail
cd '/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013'
export CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
unset PYTHONPATH PYTHONSTARTUP PYTHONHOME PYTEST_ADDOPTS PYTEST_PLUGINS MATPLOTLIBRC
'/Users/wenxiaofang/miniconda3/bin/python3' -I -B -W error scripts/aa2024_d02_sidecar_v01.py --expected-script-sha256 2247849e9535414ef67762893e4a17194cd448606d062a4ccfcfa91b9805eab2
```

本轮仅静态阅读/差异/哈希检查。合成测试设计（不执行）：来源 SHA 不符、
标题/句子缺失或重复、输出存在或软链、线程环境不符、写回不符、预算到期
均应停止；正常文本仅两处差异、原文件不变、新收据明确未验收。
不把该设计冒称测试通过，不准备自动衔接的第二条命令。
