# S04-E021-LATE-DIAG-R001：四源真实只读接入完成并冻结

2026-10-17 Europe/London。唯一一次已执行，guard COMPLETED、worker READONLY_ACCESS_VERIFIED；
未触限、未重试，主对话核对并只读冻结四输出。**本轮确实读取四份实际保存文件，不是mock。**
仅接入／身份／字段／覆盖核对；未做归因、拟合、重放或打开确认数据，原E021科学结论不变。

## 人方许可、审核与精确执行

- 用户消息`01a14ab6-a34f-7062-9411-009fb113707c`，位于本主对话
  `01a1131d-017c-7b03-a95a-ad73ba8fcc9c`的turn `01a14ab6-a339-7162-b82e-2d72e67ec485`。
  该turn开始时间2026-10-17T16:34:05Z（这是turn时间，不冒充单独消息发送时间）；
  主对话于启动前读回实际人方消息，核对时钟2026-10-17 16:34:32 UTC。
- 批准原文：
  > 批准按33351e2运行卡、使用33feec6代码执行唯一一次S04-E021-LATE-DIAG-R001四源真实只读接入，批准索引S04-E021-LATE-DIAG-R001-CARD-v2-33feec6。保持60秒／512MiB／5MiB预算，失败或触限不重试。完成后冻结核验并报告下一步，由本对话统一更新Obsidian；不做归因、拟合或打开确认数据，避免双写和重复计算。
- 这条实际批准与索引`S04-E021-LATE-DIAG-R001-CARD-v2-33feec6`对应；不是仅凭grant布尔值、
  卡内示例或--allow-real-read自授许可。本次机会已消耗，不继承为第二次读取或分析批准。
- 运行卡`33351e2ac31048eb47c01b9ca1e09914bc7a3977`，源码
  `33feec6813347177649cffbcc0ba39297937a09e`，范围ea9cafbc907cb683544aca75a58480b51c7487bd。
  启动checkout恰为33351e2，工作树及五受控依赖clean／tracked，与源码及范围／方案diff均为空。
- 独立静态认可实际消息`msg_015d0a19570ed14a016ad39fd210048191a8f8c550d8c5caab`，
  审核对话01a12d15-9b60-7280-8248-18386d6ef741，turn01a14aa8-180a-7d93-b7ea-f252e25e86e0；
  记录`late_real_access_code_review_result_33feec6_20261017.md`。本次不新增审核或写入任务。
- Mac Wennies-MacBook-Pro-14.local，本Mac CPU线程1、无GPU／SSH。启动前目标目录不存在，
  同类Python guard／worker为空；方法对话compact状态idle、revision71未变。
- 启动UTC `2026-10-17T16:35:01.337645+00:00`，伦敦17:35:01 BST；guard49666→worker49687。
  外层命令及worker均退出0；cleanup=ALREADY_EXITED、exit_confirmed=true、signals=[]、errors=[]。

专用分支codex/s04-late-regression-plan-20261016，唯一命令从以下cwd执行：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-late-regression-plan-20261016`。

```bash
PYTHONOPTIMIZE=0 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 SENS_tensile/s04_late_access_guard.py --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/late_attribution_runs/S04-E021-LATE-DIAG-R001 --expected-commit 33feec6813347177649cffbcc0ba39297937a09e --approval-ref 'codex-thread:01a1131d-017c-7b03-a95a-ad73ba8fcc9c/approval:S04-E021-LATE-DIAG-R001-CARD-v2-33feec6' --review-ref 'codex-thread:01a12d15-9b60-7280-8248-18386d6ef741/message:msg_015d0a19570ed14a016ad39fd210048191a8f8c550d8c5caab' --allow-real-read
```

卡的“待审批／未执行”保留为准备时快照，本记录补充实际状态；没有改源码、参数或原卡。

## 本次读取及核对范围

共同根`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/`。
下表是已保存活动记录，不是主对话额外重开源文件；读取字节均与保存的源metadata.size一致。

| 固定源（相对共同根） | 实际读取bytes | 核对边界 |
|---|---:|---|
| runs/S04-E021-R001/percycle.csv | 68,796 | 六列、357唯一状态键、四完整前缀、原分层权重、有限非负MSE；未分解误差 |
| replay_runs/S04-E021-REPLAY-R001/summary.json | 2,496 | 自身Run／code／状态／原结论、四fold三层保存结构；未重算均值或输出背景MSE |
| control/S04-E021-REPLAY-R001_verification.json | 2,941 | 显式selector、357／counts、保存百分数换算比值与冻结参考相符；不是从CSV重算RMSE |
| control/S04-E021-R001_saved_output_verification.json | 5,144 | 原审计身份和唯一CSV的path／size／mtime；未跟随其他清单项 |

共79,377 bytes、4次read_attempts、16次metadata_attempts。日志读顺序为inventory→verification→summary→CSV，
所有事件路径严格限于四源；四源前后token核对完成。授权文件另为本Run自有控制文件，不是第五份科学源。
这是有界全文读取；额外列／键随文件入内存，声明字段之外未分析／输出，不称字节级列过滤。

access_verification保存coverage_verified=true、rows_verified=357，
counts={u011:121,u0115:99,u012:82,u013:55}、saved_ratio_verified=true、python_optimize=0／python_debug=true。
source_metadata_accessed=true、real_data_read=true；attribution_invoked／fitting_invoked／confirmation_accessed均false。
本次不生成D_i、S_plus／minus／net、k50、harm比例、R/G/Q、图或模型，未打开U0.1175／U0.125。

## 资源、终态与冻结清单

| 资源／控制 | 本次 | 批准上限／判据 |
|---|---:|---|
| guard elapsed | 0.10125091695226729秒 | 60秒；工作58秒 |
| 聚合采样峰值RSS | 37,814,272 bytes＝36.0625MiB | 512MiB |
| 写回执前输出 | 9,765 bytes | 授权／日志／核验JSON计入5MiB |
| 全部输出含回执 | 12,638 bytes，4文件 | 5MiB |
| primary_reason／terminal_caps／errors | null／[]／[] | 无首因或触限；receipt_persisted=true |

计时从execute入口开始，含函数内预检、授权交接／生成、读取／核验／清理；不含解释器／import启动。
20ms采样、16KiB余量及post-receipt检查沿用卡；不是OS硬峰值保证。未注入触限、OS故障或优化负例。
console的final_output_bytes=12638与实际文件之和一致；落盘receipt无该console追加字段。

唯一冻结目录：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/late_attribution_runs/S04-E021-LATE-DIAG-R001`。

| 自有产物 | bytes | 冻结权限 |
|---|---:|---|
| authorization.json | 1,185 | 0444 |
| access_verification.json | 3,338 | 0444 |
| access.log | 5,242 | 0444 |
| guard_receipt.json | 2,873 | 0444 |

四常规文件、各nlink=1、无符号链接，无其他目录／缓存／副本；主目录0555。
先核对保存控制记录及两个PID均已不存在、同类进程为空，再仅移除自有四文件和目录的写权限。
冻结核对时钟2026-10-17 16:36:08 UTC；未改原四源／旧现场、复制科学数据或新增hash。

主对话后续核验只用标准库读取本Run四输出，没有导入项目模块或再次打开原四源：
grant精确字段／范围、两个引用、source／checkout／scope身份、预算、退出及失败标记一致；
26行日志均为可解析的25个白名单活动事件＋1个终态JSON，没有额外stderr或Traceback，
按路径累计content bytes与两回执和保存token大小一致。metadata按尝试保守标记，不是内容认证。
这是主对话执行后核验，不冒充独立结果审核或hash级认证。

## 结果边界和唯一下一步建议

Run execution=succeeded；local retrieval/integrity=verified；本次接入C0/C1检查支持其有界能力。
接入链已在一次真实保存文件读取中完成，不需重复本次接入或mock。原E021科学判定不变，
没有新物理、teacher、空间支持、梯度冲突或确认泛化结论。

建议唯一下一步：**仅准备沿用9984226冻结问题／公式的晚期归因真实运行方案和运行卡供审批**，
先明确最小实现／报告出口、输出和精确版本审核要求，仍不执行。现有真实入口只做接入，
原report仍限generated，不能直接假标为真实报告或把本次许可沿用给describe／report。
本次没有保存源rows，因此不能从这四控制产物计算k50；以后再读原CSV或做归因均需新的明确范围与单次批准。
当前不追加实现、归因、拟合、重放或新读取，不自动送审／派计算任务；本次单次许可已收尾。

主对话统一写本记录、Experiment索引、Obsidian／Roadmap，方法对话保持只读；没有双写／重复计算。
U0.1175／U0.125继续关闭，S04-E017／NN／多目标训练暂缓。专用分支／工作树保留，不push／移除或清理其他产物。
