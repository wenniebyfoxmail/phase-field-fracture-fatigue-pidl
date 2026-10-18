# E019-D03-U01 B002 — 一次执行，后台警告首停失效，产物隔离

2026-10-18（Europe/London）。用户明确批准最终包 v1 的确切命令一次，
不自动重试；仅执行该命令。按本次规则不能判通过，未启动 C/D 或独立验收。

## 结论与组件进展

| 层级 | 本次观测 | 边界 |
|---|---|---|
| 启动前身份/目录 | clean HEAD a01c55b7；五源码 SHA 与 A002 一致；B002 不存在且祖先无 symlink | 原阈值、线程和命令未改 |
| producer 收据 | 1 SVD、2 QR；最终自报 14.636742583010346 秒，exit0 | 是受控计数与自身报告，非独立数值验收或精确全进程计时 |
| 异常首停 | Matplotlib 字体缓存计时线程抛 RuntimeError，主线程仍完成 | 未满足无豁免的首警告停止要求，不能按 exit0 接纳 |
| 数据/后续 | synthetic，收据 inputs={}；未读真实/留出、未启动 C/D/verifier | 未打开 certificate/report 或 PNG/PDF 进行数值/图形验收 |

明确分开：进程退出状态为 exit0/producer_completed_not_independently_accepted；
本次执行协议结果为**未通过、quarantined**，不是无异常的资源检查成功。
原数值过程已到绘图入口且 producer 最后报告完整执行，支持“全尺寸人工路径
实际走到更后阶段”的有限进展；不证明各数值结论独立正确，也不证明 B001
实际根因、真实 DIC 反演或相场/预测能力。A002 通过及 A001/B001 失败均不变。

## 身份、命令与预检

- 工作目录：`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013`。
- branch `codex/s03-e016-geometry-alignment-20261013`。
- 代码基线 ab6f123a0174c7009b5427c0db0b98901ca1e2d3；运行起止 HEAD
  a01c55b771a21e3032136032849160ecd04abed9，clean；基线之后仅 docs。
  五源码运行前后外部 SHA 逐项保持最终执行包所列值，没有源码修正。
- 输出：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03/S03-E019-D03-B002`。
  启动前 stat 确认目录不存在及祖先非 symlink；所在卷约 494 GiB 可用。
- Python 3.12.2，NumPy 2.2.6（本次收据），hostname
  Wennies-MacBook-Pro-14.local，PID 61645，CPU、CUDA 空、六类线程环境均 1。
- 启动前 UTC 观察 09:09:14、结束后身份观察 09:09:40；非精确进程起止。
  普通 Codex 窗口启动前 used16%/remaining84%。
  保存结果后复查仍 used16%/remaining84%。

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/aa2024_q_recheck.py synthetic --source-commit ab6f123a0174c7009b5427c0db0b98901ca1e2d3 --output /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03/S03-E019-D03-B002
```

## 原始输出与停止事实

仅一次 launch，chunk57fec7，session57800；首次工具等待 1.002598083 秒无输出。
随后只读轮询 chunk70cb30（工具等待 5.001070375 秒）收到下列异常；
主代理随即报告异常并检查本命令的进程，ps 无匹配进程，未发信号或重试。
最终取回 chunkeb81af：exit0，工具等待 0.00000575 秒，完成 stdout 如下。
分块等待不是完整进程 wall，不能相加冒充总耗时。异常发现时到 ps 检查之间
主线程已经自然退出，故不能声称成功硬停或异常后没有继续生成产物。

```text
Exception in thread Thread-1:
Traceback (most recent call last):
  File "/Users/wenxiaofang/miniconda3/lib/python3.12/threading.py", line 1073, in _bootstrap_inner
    self.run()
  File "/Users/wenxiaofang/miniconda3/lib/python3.12/threading.py", line 1431, in run
    self.function(*self.args, **self.kwargs)
  File "/Users/wenxiaofang/miniconda3/lib/python3.12/site-packages/matplotlib/font_manager.py", line 1040, in <lambda>
    timer = threading.Timer(5, lambda: _log.warning(
                                       ^^^^^^^^^^^^^
  File "/Users/wenxiaofang/miniconda3/lib/python3.12/logging/__init__.py", line 1551, in warning
    self._log(WARNING, msg, args, **kwargs)
  File "/Users/wenxiaofang/miniconda3/lib/python3.12/logging/__init__.py", line 1684, in _log
    self.handle(record)
  File "/Users/wenxiaofang/miniconda3/lib/python3.12/logging/__init__.py", line 1700, in handle
    self.callHandlers(record)
  File "/Users/wenxiaofang/miniconda3/lib/python3.12/logging/__init__.py", line 1762, in callHandlers
    hdlr.handle(record)
  File "/Users/wenxiaofang/miniconda3/lib/python3.12/logging/__init__.py", line 1028, in handle
    self.emit(record)
  File "/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013/scripts/aa2024_q_recheck.py", line 24, in emit
    raise RuntimeError('unexpected logging warning: '+record.getMessage())
RuntimeError: unexpected logging warning: Matplotlib is building the font cache; this may take a moment.

{"status": "producer_completed_not_independently_accepted", "elapsed_seconds": 14.636742583010346}
```

直接可见的代码保护缺陷：logging handler 在发日志的后台线程内 raise，
只结束该线程，异常没有进入主线程 main 的 except，因此仍写执行收据和
completion；没有 failure_receipt。不能只依赖 main 的异常捕获宣称所有线程
“首警告即停”。本次不修改代码、不添加豁免，也不事后把该日志判成预期。

## 保存的资产及限制

仅只读列目录与读取本次 execution_receipt/completion 元数据，未读取数值
report/certificate、查看图片或执行额外数值检查。目录现有 certificate.npz、
report.json、两套 PNG/PDF/MD、execution_receipt.json、completion.json 及
.cache/.mplconfig。原始完成标记保留不改；**不得据其自行放行**。
本文件是额外的协议隔离说明，不回写生产收据或冻结产物。

收据 elapsed_before_receipt=14.597735165967606；末次自报 elapsed 如上，
小于原 60 秒软预算。启动前的导入/元数据和最终 stdout 等不在此计时口径，
详见最终包。预算未成为这次首个阻断，停止保护才是；不是数值容差失败。

下一步建议：仅准备源码/纯人工层面的跨线程警告传播与主线程终止保护
修订方案及独立静态审查，保持原容差和预算。先修保护再谈另批新运行；
不重用 B002、不把本次图当已验收结果，不自动准许日志或真实 C/D。
本轮只报告并保存，无源码修订、重试、发送、真实/留出读取或独立验收。
