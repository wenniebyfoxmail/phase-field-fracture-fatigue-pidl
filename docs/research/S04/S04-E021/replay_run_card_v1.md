# S04-E021-REPLAY-R001 — 单次冻结模型推理重放运行卡 v1

日期：2026-10-16 Europe/London。状态：**仅供执行审批，未准备真实输入、未执行。**
本次用户只批准编写运行卡与输入范围；下文描述未来获批后的操作，不是执行指令。

## 1. 目的、身份与唯一执行方

只检验 E021 四个已保存外层模型，能否在原开发数据上复现357个逐周期误差记录、
四折 R/G/Q 和固定 U0.115/C20 字段；这是算术一致性检查，不是新拟合或新方法实验。
沿用 [next_validation_plan_v1.md](next_validation_plan_v1.md) 在 bcb58a6 的原方案，
不改已关闭 E021 的科学结论或门槛。

| 项目 | 本次拟审批的唯一范围 |
|---|---|
| Run ID | S04-E021-REPLAY-R001 |
| 执行／记录方 | 本残差主对话01a1131d-017c-7b03-a95a-ad73ba8fcc9c；方法对话只读，本对话统一更新 Obsidian |
| 执行机器 | 本 Mac，仅 CPU4／无 GPU 的离线推理；无 PINN 训练循环、SSH、Windows、Taobo 或 CSD3 |
| 工作树 | /Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-raw-replay-preparation-20261015 |
| 分支／本轮起点 | codex/s04-raw-replay-preparation-20261015 / f3c3c4c |
| 独立代码审核 | 45d36055ea10ef1177de342dd01dbfe3c4376ee8；无阻断修改，见 replay_code_review_result_45d3605_20261015.md |
| 拟运行提交 | 首次加入本 v1 运行卡的提交；提交完成后在主对话审批摘要中给出完整 SHA，运行时 HEAD 必须精确等于该 SHA |
| 原模型来源 | S04-E021-R001，runtime6aa21e3c469d53c92240c9689d07a3ffb316d67c |
| 数据锁 | paired_s4_lock_candidate_20261013.json；SHA256=cb9f63f8bd4b73afe0bd0f74bc7836018ce2e6bfcbd46edae80e7fef7b07868c |
| 次数／预算 | 整体只调用一次 guard；300秒／2GiB采样聚合RSS／100MiB生成输出，不按折拆分预算；失败、触限均不重试／resume |
| Python | /Users/wenxiaofang/miniconda3/bin/python3；未来启动前仅记录实际 hostname／Python 版本，不做真实数据 pilot |

运行前核对三份新源码与45d3605完全相同：s04_raw_replay.py、s04_raw_replay_guard.py、
s04_raw_replay_checks.py；s04_d0.py、s04_g5_features.py及数据锁与6aa21e3相同；
原重放方案与bcb58a6相同。本轮只增加文档，不把文档提交冒充原审核 SHA。
如 HEAD、代码、数据锁或方案变化，停止并重新报告，不自动追随最新版本。

## 2. 输入准备范围——只允许六个文件级链接

保持原锁、原映射、原字段与原状态语义。只比较四个开发前缀：

| Umax | admitted physical cycles | 数量 |
|---|---|---:|
| 0.11 | C1–C121 | 121 |
| 0.115 | C1–C99 | 99 |
| 0.12 | C1–C82 | 82 |
| 0.13 | C1–C55 | 55 |

合计357周期，85112个 admitted native cells；s4 post-history、horizon0。
C0不可用，不补造；C1–20、C21–40、C41+三层等权。输入仅原32列因果 PINN 特征，
FEM只评分。冻结模型、尺度、normalizers、alpha及回退选择均不重算。
旧容器可能留有更长轨迹：原 loader 会解压完整字段容器后截取前缀，这影响峰值内存，
但不授权分析、评分或挑选前缀外状态，也不把既有数据角色改成部署预测证据。

未来获批后，六个源文件的共同根是：

`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-e016-request31-storage-block-20261009/`

在本运行工作树内建立**同相对路径的六个叶子符号链接**，源和目标均按下表逐项确定：

| 同相对路径（源根＋此路径 → 运行工作树＋此路径） | 用途 | 本轮仅元数据所见字节数 |
|---|---|---:|
| local_archive/experiments/S04-E016/g5_export_20261013/geometry_native64_v4/mapping.npz | 原映射／面积 | 2227213 |
| local_archive/experiments/S04-E016/g5_export_20261013/fem_v3_retrieved/u011_s4.mat | 开发 FEM | 131655759 |
| local_archive/experiments/S04-E016/g5_export_20261013/fem_v3_retrieved/u0115_s4.mat | 开发 FEM | 107145585 |
| local_archive/experiments/S04-E016/g5_export_20261013/fem_v3_retrieved/u012_s4.mat | 开发 FEM | 88404417 |
| local_archive/experiments/S04-E016/g5_export_20261013/fem_v3_retrieved/u013_s4.mat | 开发 FEM | 62255219 |
| local_archive/experiments/S04-E016/g5_export_20261013/pin_v5_retrieved/hard5_u0115_s4.npz | 开发 PINN | 101833137 |

另三份 PINN 文件保持锁内的绝对路径，不新增链接：

共同目录：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/pidl_result/pidl_peak_trajectories_three_umax_20261007/outputs/`

| 该目录中的精确文件名 | 本轮仅元数据所见字节数 |
|---|---:|
| hard5_u011_peak_trajectory.npz | 126942109 |
| hard5_u012_peak_trajectory.npz | 85339974 |
| hard5_u013_peak_trajectory.npz | 59714873 |

只可创建必要的父目录和上述叶子链接；不链接整个 local_archive 或兄弟目录，
不复制／搬移数据、不解包、不新导出、不重映射、不修改源权限或时间戳。
源缺失／目标冲突／新元数据与准备清单不一致时，停止报告，不换源或覆盖。
已存在的叶子只在确定指向同一精确源且无冲突时复用。
上述磁盘文件大小不代表解压后内存；本轮未做内容哈希或状态验证。
正式 loader 的原九份输入哈希及状态检查必须在同一次受限调用内完成。

## 3. 既有 E021 父包——原址只读，不重新封装

共同根：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/`

未来 guard worker 可读取 `runs/S04-E021-R001/` 中的 receipt.json、models.json、
selection.json、decision.json、percycle.csv、u0115_C20.npz；并核对完整十文件集合：
上述六文件加 folds.csv、V0_V1_holdouts.png、u0115_C20_raw.png、README_analysis.md。
原两张 PNG、folds.csv 和 README 仅列名／元数据核对，不重绘或修改。
还读取 runs/ 下原三个 sidecar：S04-E021-R001_guard.log（仅元数据）、
S04-E021-R001_fit_guard_receipt.json、S04-E021-R001_guard_receipt.json；
以及 control/S04-E021-R001_saved_output_verification.json 的原13文件清单。

沿用审核版本：运行前后核对父包文件集合、只读权限、大小和 mtime，核对原 receipt 身份。
**这不是父包 SHA256 内容认证。** 不新增父包哈希方案、不修复父包权限、不重写其清单；
不符合则停止。原输入锁中的哈希检查与此父包元数据检查是不同层次。
本轮不打开父包内容，也不为准备运行卡预先解码 C20 或模型。

## 4. 唯一输出与未来授权文件

新输出根（必须全新，不提前创建）：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/replay_runs/S04-E021-REPLAY-R001`

| 位置 | 预期内容 |
|---|---|
| 输出根/comparison.csv | 357行逐周期保存值与重放值、差异／容差比及 V1 raw 范围 |
| 输出根/summary.json | 四折 R/G、Q、三层 MSE、固定 C20 字段差异、原结论与身份；失败则记不完整／错误 |
| 输出根/replay_comparison.png、README_analysis.md | 本次算术差异图与解释，仅在同一 worker 中生成 |
| replay_runs/S04-E021-REPLAY-R001_guard.log | 唯一 worker stdout／stderr |
| replay_runs/S04-E021-REPLAY-R001_guard_receipt.json | 终态、命令、PID、机器、起时、采样资源、退出与 code_commit |

不输出完整357周期预测场，不另开 report、重绘、benchmark 或检查作业。

只有收到绑定本卡最终提交的**执行批准**后，才能新建：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/control/S04-E021-REPLAY-R001_authorization.json`

未来 JSON 必需字段及值如下；此表不是授权文件，也不表示已获准：

| 字段 | 执行批准后才可填写的值 |
|---|---|
| action | frozen_inference_replay_only |
| user_approved_replay | true，且须有本次实际用户批准 |
| independent_code_review | APPROVED，引用45d3605的独立回复 |
| code_commit | 主对话审批摘要列出的本卡完整提交 SHA，必须等于运行时 HEAD |
| reference_commit | 6aa21e3c469d53c92240c9689d07a3ffb316d67c |
| lock_sha256 | cb9f63f8bd4b73afe0bd0f74bc7836018ce2e6bfcbd46edae80e7fef7b07868c |
| plan_commit | bcb58a6 |
| run_id | S04-E021-REPLAY-R001 |
| output | 上述完整新输出根 |

另保存实际人方批准引用、reviewed_source_commit和本卡路径作为来源说明；
不复用旧 fit approval，不覆盖已有授权文件。JSON只是程序入口检查，不代替人方同意。

## 5. 获批后顺序与精确命令——现在不执行

1. 核对批准的完整 SHA／干净状态／源码和依赖 diff；记录实际主机、解释器版本。
2. 仅只读检查本任务 guard／worker 的 cmdline＋cwd 和本 Run 的输出／log／receipt／授权路径。
   若本 Run 曾调用或任何相关残留存在，停止，不删除后重试。若发现另一候选重放正在运行，
   同样停止协调，不杀它。首次调用即消耗本次机会，即使入口或启动阶段失败。
3. 按第2节准备六叶链接；只做元数据／目标解析核对，不单独加载或预哈希真实输入。
4. 新建第4节精确授权 JSON 后，只调用下面一次命令。无 preflight real-data smoke。

cwd：`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-raw-replay-preparation-20261015`

```bash
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 VECLIB_MAXIMUM_THREADS=4 CUDA_VISIBLE_DEVICES='' /Users/wenxiaofang/miniconda3/bin/python3 SENS_tensile/s04_raw_replay_guard.py --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/replay_runs/S04-E021-REPLAY-R001 --authorization /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/control/S04-E021-REPLAY-R001_authorization.json
```

不调用旧 s04_raw_guard.py（会拟合），不直接启动 worker，不运行另一份 E022 runner。
需要额外消息、传输或复审发送时，仍须单独展示最终版本并取得本次发送批准。

## 6. 预算口径、停止与终态核验

- **300秒**：审核版本的 timer 从父进程授权通过后开始，覆盖 worker 启动、父包检查、
  真实输入 hash／解压、全域推理、评分、汇总和绘图；worker有295秒检查余量。
  链接准备、父进程启动／授权和终态归档不在此 timer 内，不承诺整个 shell 生存期≤300秒。
- **2GiB**：guard＋活跃 worker／子树约0.1秒采样的聚合 RSS；不是操作系统硬内存上限。
  原 loader 会先保留完整开发数据，实际工作集／解压峰值／真实清理尚未验证。
- **100MiB**：审核版本统计新输出树＋本次 log／终态 receipt，预留32KiB；
  不是把原输入或已有父包算成新增输出，授权 JSON／文档亦不属于该计数。
  不扩大额度；报告最终 receipt 写入前后的字节差异，避免将前值当最终总量。
- 任一数值、身份、完整性失配或触限即终止，保留已有输出和控制证据；guard仅清理
  自己启动的进程组，TERM后0.5秒仍未退出则升级KILL。清理耗时可能超出触限时刻。
  不重启、resume、重试、增预算、改容差、选新alpha、回退补救或删除失败残留。
- 固定比较仍为逐周期 MSE／C20字段 `abs(replay-saved) <= 1e-10+1e-10*abs(saved)`；
  R/G/Q绝对差≤1e-12，原方向分类相同，有限性／合法输出和 damage/history 恒等保持。
  任何失败是本次复现未通过或不完整，不把运行 exit0单独当算术通过。
- 任一终态后，先核对 guard退出、worker退出及归属、log警告、summary和表覆盖；
  成功还须有357唯一有序行、四折／三层、C20及图/README，父包检查无变化。
  只从已输出小表／summary核对已知 U0.11 C41+约1.6083%退化仍保留；不再调用推理。
  缺终态证据则报告不完整，不补跑 worker或报告。精确冻结仅针对本次输出／log／receipt，
  记录文件数／大小并移除这些新结果的写权限，不改源、旧父包或旧控制文件。

通过仅增加冻结模型的算术一致性证据；不能证明未保存周期的逐点相等、物理／teacher
资格、确认泛化、未来预测，不能抹去晚期退化。失败则报告差异和下一项待审批诊断，
不自动拟合修复。E021旧科学结论不改，U0.1175/U0.125、S04-E017、NN／MOO均不放行。

## 7. 本轮准备记录与审批对象

2026-10-16只读核对了九个输入文件的名称／大小、源码diff，以及运行工作树中
local_archive和本次输出／sidecar／授权路径均不存在；
读取的内容仅是仓库代码／数据锁／既有审核文档。未打开真实数组或 E021父包内容，
未重跑生成测试、绘图或完整资源测试，未创建链接、实际授权 JSON或新运行输出。

da35d7a／S04-E022工作树与已有记录保持原状，不合并、不当后备、不调用或发送新任务。
本主对话是唯一准备／未来执行／记录方，Obsidian沿用原笔记及Roadmap唯一链接。

**待审批动作：按本卡最终提交，准备上述六个文件级链接及专用授权文件，并在本 Mac
执行唯一一次 S04-E021-REPLAY-R001；预算300秒／2GiB／100MiB，失败或触限不重试；
终态冻结、核验并由本对话更新记录／Obsidian。批准仅覆盖该动作，不包含真实拟合或确认评估。**
