> D18终态：R006单次1/600、case160.748秒，第2步8方向后首停；联合Phi下降但原force仍1639倍门，半径限制的小步未达平衡。完整162文件全核/4PID全退，无重试/训练。收束有限Newton-ray，下一全局化承重缺项仅列出、无R007授权。[结果](../solver_repair_v9/result.md)／[elapsed](../solver_repair_v9/step_elapsed_times.csv)／[复核](../solver_repair_v9/evidence_review.json)。

> Current D19: R007 is stopped0/600 after step1 optional Newton-candidate feasibility certification failure; complete162 files verified, no retry/NN. [Actual result, elapsed and next proposal](../solver_repair_v10/result.md). Original attempt/clock consumed; no autoR008.

> D17终态（英国2026-10-21 00:49）：R5单次train_A1/600、首步31.843秒、case205.137秒；三次块方向双行真残差通过，但第三方向投影全步触发新未接受候选的原机械pivot保护。全量159文件/75.154MB核验、4进程全退，无重试。重建发现50个全nodal-d1单元/32自由DOF的近零刚度局部，非旧接受态奇异或全模型无解。下一仅联合投影/信任域全局化设计，完整轨迹/NN收益未取得；[结果](../solver_repair_v8/result.md)／[elapsed](../solver_repair_v8/case_elapsed_times.csv)／[结果独立复审](../solver_repair_v8/evidence_review.json)。

> D16终态（2026-10-21英国时间）：后续HQ人方新授权的单次train_A600步包已按首科学失败停止，1/600、首步30.405秒、case150.708秒、GPU0。全程残差保护拒绝Newton全步/接受半步，但第二次Schur48内迭代真相对残差0.15525未达0.001；另定位AA全步浮点判等误清历史。33源/29返回文件核验、进程全退，无重试。完整轨迹及NN收益未完成；[实际结果/下一数值方案](../solver_repair_v7/result.md)／[逐case elapsed](../solver_repair_v7/case_elapsed_times.csv)／[保存证据独立复审](../solver_repair_v7/evidence_review.json)。下方R3/R2运行文字为历史。

<!-- HYBRID_D16_HQ_AUTHORIZED_V7 -->
> D16启动时记录（历史，2026-10-20）：已核原HQ较晚直接人方托管/计算授权，再由HQ前瞻限定新包：原train_A一次连续600步、4墙钟h/4CPU/0GPU/32GiB/新输出归档合计16GiB，首科学失败停且不重试。实现全程m_work保护＋有界AA＋原残差约化VI Newton/Schur，保留真实最终QP/D13。仅轨迹可达性，无其他case或训练；[authority](../solver_repair_v7/authority.json)／[准确连贯方案](../solver_repair_v7/plan.md)。此前“先不重跑”分析任务已完成，R3许可不复用；准确包独立复核及准入通过后已单次启动；首快照1/600、第2步在解，[真实运行状态](../solver_repair_v7/run_status.md)，尚无完整轨迹成功。

<!-- HYBRID_R3_D15_COUPLING_DIAGNOSIS -->
> D15（2026-10-20）：R3原日志诊断已完成；机械单次成本下降，但第17轮m最低1.783后回升，3次有效Anderson在第5轮耗尽，普通map无全程保护。下一候选为统一工作残差保护＋受约束Newton/Schur，并保留真实最终QP及原接受态合同；仅方案，无新实现/重跑。[完整诊断](../solver_repair_v6/r3_coupling_diagnosis.md)／[独立诊断与方案复核](../solver_repair_v6/r3_coupling_diagnosis_review.json)。

> R3历史终态：R3已在2026-10-20 22:29:18英国时间按首科学失败停止，第2子步300秒未接受；train_A1/600、phase333.032秒，其余case/fit未开始、GPU0，三个归属PID均退出，没有重试。[终态与边界](../solver_repair_v6/execution_r3/terminal_summary.md)／[逐case elapsed](../solver_repair_v6/execution_r3/case_elapsed_times.csv)。下方启动/运行中/审批阻断条目均为历史状态，不代表当前仍在运行。

> 当前D14更新：用户已明确批准原GPUServer8的具体脚本、同机R2→R3复制和一次修复后重跑。R3 stage成功、准确独立执行绑定REVIEW_PASS后已单次提交；源9216909d，物理/历史/预算不变。依赖/Agg/native replay准入通过，最新真实进度见[运行记录](../solver_repair_v6/execution_r3/run_status.md)和[逐case elapsed](../solver_repair_v6/execution_r3/case_elapsed_times.csv)。首科学失败即停，不自动重试。下方stage被拦文字属已解决历史，不能代表当前状态。

> 当前D14（2026-10-20）：R2已核实失败且三个归属PID均不在；train_A接受1步、在第2步120秒停，累计生产研究wall797.079秒。新用户授权一次修复后完整重跑，沿同owner实现v6，保留D13字段/历史合同和物理精度。实现、142项人工测试及独立代码复审已完成；[当前准备](../solver_repair_v6/repair_plan.md)、[准确动作](../solver_repair_v6/stage_request.json)。远端stage被自动审批拒绝，未执行；新卡禁用并待具体服务器/脚本/复制动作的人方确认及实际stage成本绑定。以下D12/D13条款为历史治理沿革，不代表R2目前仍在运行。旧R2源/卡/收据不变。

# FEM surrogate比较：当前任务入口与前瞻治理修订

后续本地D13：按用户新请求完成[统一接受态/逐字段时刻接入](../accepted_state_plan_v5.md)，沿同owner实现，旧R2卡/源/收据不改。新v5卡禁用；R2当前终态/完整费用未核实，不能追认旧输出为新合同标签或重用已消费许可。此段只更新本地实现入口，不代表远程监测或科学启动。

2026-10-20；依据用户批准的“一次有边界的授权，机械检查由Agent自动完成”更新。仅本地管理条款迁移，不是新执行卡、执行许可或复审。本轮不SSH、安装、探针、传输、求解、训练、重启、恢复自动化或调用新审核。

## 当前入口、已用卡与历史边界

本文件是当前任务管理入口。[最近准确执行卡](execution_card.json)与[独立静态复审](execution_review.md)属于已消费的一次任务 `pf_hybrid_complete_20261020_r2`，原执行源d703e3c8；原卡、已签名快照、旧失败及全部收据保留字节，不因本修订改变enabled、哈希或authority。没有新建或启用未消费的下一次执行卡。

[运行记录](run_status.md)和[运行收据](run_receipt.json)最后本地核验时间为2026-10-20 19:06英国时间，记录train_A运行中、已接受1子步。本次没有查询当前生产状态；该快照不能证明任务现在仍在运行或已成功，不可凭其重启。执行前须在相应已获批任务范围内核实真实进程/收据，已消费许可不能重用。

继续原D12：在同一数值质量下比较前态／经典外推／神经damage初猜加完整受约束校正；固定单mesh/material族、原3600数值子步、一次fit、12GPUh、总136hosth/≤16核/2176分配coreh、64GiB RAM、24GiB VRAM上限及128+128GiB存储。原全部精度、120秒物理子步、三臂公平性、真实历史提交、测试信息边界和科学判据不变；旧费用和已耗预算不清零。跨loading/property新数据与材料族扩展仍不在本次已用许可中。

## 一次任务授权自动覆盖的机械工作

下次任务许可一旦明确其目标、数据、producer、总预算、停止/重试限制和所需结果，Agent在该范围内自行完成：实现及同范围修复、相关测试、部署准备、既选独立Codex通道的必要聚焦复审、版本/环境兼容性与资源检查、命令及RunID/路径/哈希/收据补齐、逐case elapsed time及失败耗时记录。条件式执行授权的实施／复审／准入条件满足后自动推进，不再为了这些机械字段另问用户。计划限定许可仍不授权运行。

已选审核通道继续独立只读Codex。改变科学行为、数据解释或执行控制风险时，自动安排该通道必要的聚焦复核，沿用未改发现；不因每次commit或元数据补齐重启Code Ready，不再重复请用户批准同通道复审。新通道或外部发送仍按实际适用的人方规则。

版本应记录真实值并按风险核兼容性；包metadata和真实import保持区别。旧已用卡的精确依赖要求不在这里放宽；以后卡片的辅助库版本发现、fresh路径/RunID与哈希实例化本身只需自动一致性检查。若严格runner需要新绑定记录，明确记录继承的独立审查范围和Agent机械核验，不冒充reviewer重签；若需修复runner控制逻辑则按其真实风险聚焦复核，无需另索机械步骤许可。

| 原有重复管理门（历史文本保留） | 本修订后的处理 |
|---|---|
| 版本未知→单独申请查询；pin补齐→再次申请精确卡启动 | 同一有边界的任务许可覆盖查询、兼容检查、实例化和条件满足后执行；不单列人方决策 |
| 仅Matplotlib版本／路径／RunID／哈希变动也要求重新完整独立复审 | 自动一致性检查并沿用原Code Ready；仅科学／控制风险实质变化做必要聚焦复核 |
| 同范围实现／修复／测试／已选通道复审逐次再确认 | 在原许可及预算内由Agent自动完成，并记录真实变化、测试和审核范围 |
| 任一已知未启动的资源等待都算科学失败或要求新许可 | 归机械资源检查；在预设短重查上限和真实许可内处理，不能伪造新RunID换取额外尝试 |

上述是前瞻条款，替代Agent自己添加的逐项审批流程；不能追溯扩大用户明确批准过的那一次inventory／stage／dispatch的连接、时间、次数上限，更不能抹掉失败或已消费authority。

## 后续新卡的短机械重查上限

下次有授权且实际生成新卡时，在第一次尝试前把机械重查明确设为最多2轮、累计≤120墙钟秒、0求解／训练／GPU计算，计入当次获批的原总预算和共享准备费用，不能增大原136hosth／12GPUh或单phase上限。每次连接仍限单次连接、连接超时≤10秒、只读检查≤20秒；若用户许可更严则取更严者。该默认值是后续卡的前瞻管理参数，本轮没有执行或消费它。

已证实没有启动科学worker的资源等待不计科学重试；耗尽机械上限后记录等待/阻塞，不自动扩大上限、换机/卡、重新编号或启动科学计算。连接结果未知先核实已存在进程、reservation及收据，不能把unknown当zero-start。隔离任务目录内、数值语义不变的依赖修复可在获批范围内自动完成；共享／系统环境改变及超范围消耗不包含在内。

## 仍需人方决定的唯一边界

仅当要改变授权包络时合并提问：新增科学范围／受保护数据／producer、超出许可的费用或扩大预算，或原许可未允许的科学重试／恢复。真正的人方停止和科学首停不重试限制保留；资源等待的分类不能变成重跑许可。本次规则迁移本身不启动、恢复或重新批准任何FEM数据生成或训练。

## 当前规则来源

- [research-decision-core：一次授权，机械检查自动完成](/Users/wenxiaofang/.codex/skills/research-decision-core/SKILL.md)
- [agent_bootstrap：2026-10-20更新](/Users/wenxiaofang/.codex/skills/research-decision-core/references/agent_bootstrap.md)
- [research-review-channels](/Users/wenxiaofang/.codex/skills/research-review-channels/SKILL.md)
