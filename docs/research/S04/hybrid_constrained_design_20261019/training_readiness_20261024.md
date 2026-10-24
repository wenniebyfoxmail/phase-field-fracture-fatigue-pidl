# R2对账与当前训练入口（2026-10-24）

**结论：R2已核实首停；同一路线此后已推进至R008，仍无完整teacher轨迹和模型。当前复用owner为`/Users/wenxiaofang/phase-field-fracture-with-pidl/worktrees/fem-surrogate-solver-repair-v6-20261020`，不是停在D13的旧工作树。** 本轮实地只读核R2及R3–R008终态，R009目录不存在；当前没有对应运行进程。没有新FEM或训练。

## R2实际结果

R2 `pf_hybrid_complete_20261020_r2` 源d703e3c8/card f3cc0463，在10月20日19:07:25英国时间因第2子步120秒保护停止。train_A1/600、case157.477526秒、producer171.379771秒，GPU0、fit0；state0/state1/features及latest字节SHA、父链和78源文件一致。其余轨迹未开始。只取NPZ头、JSON提交证书与哈希，没有独立重算场残差。见[r2-specific receipt](r2_reconciliation_20261024.json)。

原`cost_ledger.wall_seconds=795.761521`是前费＋phase，最终`total_job_wall_seconds=797.078552`另含1.317031秒supervisor overhead；使用后者一次，不相加。该数已经被后续owner累计账本包含，**不能再次叠加进R008余额**。

## 当前路线必须一并考虑的证据

| Run | 接受/原600步 | case秒 | 首停 | fit |
|---|---:|---:|---|---:|
| R2 | 1/600 | 157.478 | step2 old120s cap | 0 |
| R3 | 1/600 | 333.032 | step2 300s cap; residual rebound | 0 |
| R4 | 1/600 | 150.708 | Schur true residual target failed | 0 |
| R5 | 1/600 | 205.137 | unaccepted fullstep current-K/pivot qualification | 0 |
| R006 | 1/600 | 160.748 | 8 coupled direction budget exhausted | 0 |
| R007 | 0/600 | 41.216 | optional candidate conservative feasibility certificate | 0 |
| R008 | 0/600 | 170.495 | 8 subproblem budget exhausted | 0 |

R3已在300秒首停，之后R4–R008暴露Schur内解、投影后机械资格、全局化/子问题推进等不同障碍。R008目标Phi下降36.78倍，但原force仍173.23倍门、damage KKT15.69倍门；不是单纯“120秒不够”。所以**撤回本轮早期基于R2单独提出的旧求解器600秒候选**，其未部署、未执行。其源ddb4ad59及元数据基准仅为已被后续证据否定的准备记录，不用它替代现有D21。

当前可复用的是D21有限活动面CG代码fee87bac及既有97项工程检查，原Cauchy/可表示域/真实最终QP、current K、D13 f_solve/f_commit、单CAS均保留；小矩阵通过不代表原FEM已可达。旧D21是reference-only600步/4h/0GPU提案，已在10月21日14:44Z过期且禁用；没有R009，不自动改日期或复用旧授权。

## 剩余预算：当前余额不是R2余额

历史R1至R008保守累计 **19079.395674秒**，已经包含R2、R3和后续各包；D21准备含原120秒收尾余量 **1494.178582秒**。当前核查准备从证据目录创建起的可追溯calendar **1445.074秒**（含两次只读查询、旧候选准备及纠正，不能再叠加它们各自墙钟）。另保留历史未知控制600秒、当前初始未计量读取600秒、最终收尾120秒；这些是保守余量，**不是实测运行/CPU费用**。关闭包与三天空闲不按运行时间扣费。

截至本次记账，原136hosth下**保守可用约129.517小时**，GPU实际未用、原12GPUh容量保留。CPU全生命周期实测仍UNKNOWN，不填零。机器可读分项及SHA见[training_readiness_20261024.json](training_readiness_20261024.json)。原r2-only约135.773h仅是历史子集余额，现已明确作废为“当前余额”。额度有余也不产生首停后的新尝试权限。

## 能复用什么，不能拼什么

- 复用原mesh/material/state0/载荷、D13合同和图网络/损失/划分，复用最新D21实施及原检查，不另起求解器、不重跑旧负基线。
- R2的一份旧合同pair，以及R3–R006不同策略的首步片段只作回归/溯源。它们不是连续600轨迹，更不是5条独立数据；不跨策略拼历史，不把R007/R008 trial当接受标签。
- 复用已有完整取回的失败证据与current-K/表示域改进，不重复全量下载或运行保存大J优化。当前方法合格训练/验证条数均为0；尚缺A600+B600+validation600。测试1800步在fit之后。

## 最快训练的一个完整安排（方案，尚未启动）

1. **先补训练数据出口，而不是新算法。** 当前D21卡`role=reference`；`hybrid_producer_worker.py`仅在`role=labels`保存共同预测器和features。因此需沿现有worker启用labels分支、将单case validator/编排扩为A/B/validation，绑定同一个D21 coupling与字段合同。复用既有fit；不改网络或loss。此工程缺口尚未实施，不能称现卡可直接训练。
2. **直接原尺度标签生产，不再排一串小试。** 新一次有边界任务从共同state0产生A(.8)、B(1.2)、validation(1.0)各120cycle×5=600；原300秒/100fresh/8outer/子问题动作更新上限与物理精度保持。建议≤20hosth/条、teacher合计≤60hosth，4CPU/0GPU/32GiB；首科学失败停，无重试。D21实际能否完成仍未知。
3. **1800完整标签通过即自动进入一次fit**：1200训练＋600验证，原4×64网络、loss/seed/early-stop，≤6GPUh。无需等三条测试轨迹；不拿一小撮早期f=1点抢跑，更不另训“临时模型”。
4. 冻结模型后，再做reference/classical/hybrid各600，原20hosth/20hosth/6GPUh及共同质量/历史/反力/10%时间判据；准入/回放/分析仍共用原4hosth。全计划phase合计116hosth，原总136hosth/12GPUh不增加；历史费用继续扣。
5. 训练数据量须明确使用原128GiB主输出＋128GiB归档/足够free空间，不能继续用D21诊断卡archive7GiB。600个未压缩接受态本身就约10.4GiB，加入features和工作证据更大。原3600全部状态/标签payload估算86.51GiB，旧20GiB余量需再核最新诊断保留政策；不预支压缩收益，也不承诺原诊断16GiB包能装下完整训练集。

这是一份新任务方案，**不是过期4h/0GPU卡的重启**。科学范围拟一次完整3600设计、teacher后唯一fit再测试；执行前需要人方明确这一新尝试及完整数据/训练/存储包络。在该包络获准后，实现labels出口、固定基准、必要机械绑定/资源与部署由Agent完成，不逐字段再审批、不自动追加独审；若原物理问题仍未走出首步则按首停保留失败，不能把预算余额当自动重试权限。

本轮只作核清、必要纠正和具体安排；最新D21源未改、未新跑97项测试或任何科学验证。原v5签名、R2/R3各已用卡和全部负结果保持。原始当前两次只读快照及查询收据在`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/fem_surrogate_comparison_preparation_20261020/execution_v1/reconciliation_20261024`。
