---
storyline_id: S01
experiment_id: S01-E015
protocol_revision: v1
created_at: 2026-10-16
status: frozen_pending_independent_design_review
branch: codex/s01-e015-locality-gate-20261016
base_commit: cce4ecf39b6c8be57d1f24696db343dbad82d366
---

# 固定正面积交集门槛，其余E014机制不变

## 问题、比较与允许结论

C2 state-measurement / real-road，当前图像检测，无预测时域。图像是1FP/image预算单位，地点是FIT/held分组单位。问题：只增加原框与修正框须有正面积交集的GT无关门槛，能否把既有正例选入有限容量，最终保护E003旧检测并获得实际净收益？不变E003是主比较；E014净0/弃权是已看历史参考，不另算一个检测arm。

沿用固定E012-R004的835图、43347原框、31156既有修正及评分，原GT无关base eligible19384；7个不同正GT/5地点，FIT8正GT3/5/6（正地点3/3/4）。E014已完成：18active政策各6次入选记录全是d=1零交集，已有正候选d约0.575371–0.868760，任一政策最大入选及最终正GT入选均0；三主模型及10诊断全部弃权，预算后684旧命中全保留而净0。最大变化优先把完全跳转排在这些部分重叠正例前，具体瓶颈明确；不把几何信息整体判死。

本门槛受已消费结果启发，只能支持冻结上游、复用既有训练地点条件下的选择器OOF探索。上游E003/修正器及结果均已复用，不能声称整管线独立验证、未接触地点泛化或物理预测。新确认/validation/reserve及旧四资格地点继续排除，不读取其GT或原图。

## 唯一决策改动：正面积交集

对原框o和修正框n，固定require min(o.x2,n.x2)>max(o.x1,n.x1) 且 min(o.y2,n.y2)>max(o.y1,n.y1)。有限、正宽高框上的这个布尔判据表示数学交集面积严格>0；边缘/角点接触不算。直接比较两个方向，避免面积乘法下溢或1-IoU舍入导致误判。没有epsilon、比例阈值、拟合容差或交集门槛搜索，不用d<1替代原坐标判据。任意微小正交集都可通过，可能仍有害，门槛不是定位质量保证。

不改原base eligibility或稀疏parent/index映射；其19384计数仍用于源身份核验。为每个候选额外保存positive_intersection布尔值，在policy的阈值筛选/NMS/cap之前只保留base eligible且交集为真的候选。base已不合格者不得复活。局部判据与GT/新U/全12oracle无关，原框不删不变。诊断原支持时保留base候选，不能把新增门槛造成的删除误写成来源不完整。

其余E014决策严格不变：d=1-IoU降序、原s0降序并列回退、image/box/key稳定排序；x=logit(pnew)-logit(pold)，clip[1e-6,1-1e-6]，仅0,.5,1,2,4,8,abstain七档；每主模型只学一个索引，无新可训练参数/特征/权重/反向排序。原s0与最终检测分数不变；沿用对任何原框IoU<=.7、修正间IoU>.5拒绝、每图1/每源组3、accepted-only状态。门槛拒绝者不占NMS/cap，最多9个OOF追加；原43347行、框/概率/分数/顺序是不变前缀，不对原框NMS。

## FIT学习、冻结顺序和范围

三个主模型各只收到自己的FIT8图像/候选/GT，七档使用同一新增门槛及E014排序，计算实际FIT联合检测结果；singleton U不作为排序输入，不相加替代联合收益。active需旧保留==1、净GT>=1且macrodelta>0才可选；按净GT最大、实际预算内新增修正FP最少、追加行数最少、阈值最高决胜；无active收益则abstain。容量入选和门槛保留数不反馈阈值或形成额外门槛，各fold允许独立弃权。

三个主模型与OOF预测先落盘冻结，才做10个整正例地点删除诊断和任何held/full12评价。诊断仍按原FIT8正地点3/3/4列表删除整个地点，重建FIT7基线/预算，不把原FIT8 U冒充FIT7标签；只报告阈值翻转、弃权及原FIT8描述性支持变化，不反馈主预测，不增加置信/成功门槛。即使新门槛移除全部正例，13fits/91policies和固定后续评价仍在这一Run内完成，明确弃权/净0；不换gate或临时跳过后另加试验。

输入读取复用E014/E013：固定R004 ZIP允许成员与12既有train地点metadata，qualification仅作用域读取joint.rows前43347原框并校验digest，跳过oracle尾行/字段；候选/概率从固定identity/scores重建。三个FIT标签只用于自身支持审计、固定地点删除列表、冻结主预测后的只读容量和局部门槛审计。full12/oracle只能在冻结后说明，不用于训练；无pooled_features/checkpoint/原图/新U/full12refit。

## 正例留池、入容量、实际净收益分开

原有capacity_audit不改语义：各主FIT七档已存source_keys与自身singleton正身份join，分别给出任一固定政策最大与最终所选政策的不同正GT入选数，按new_identities去重；不能用其他FIT标签给当前held算正例转化率。这只是原单例支持身份，不是新门槛下重算U，也不保证联合新命中。

新增locality_audit：全12只报告GT无关base eligible/retained/removed总量及每主FIT同类计数；各主FIT另报告自身原标签中的正候选/不同正GT在门槛前后的留存。before正GT仍3/5/6作为来源支持；after多少是描述性组件，不要求强行等于before，也不作为有效性或主判定新门槛。多候选支持同一GT去重，正候选删除与GT仍被另一候选保留分别记录。无新增U、policy比较或检测metric，不能改变主模型/OOF预测。

正式唯一主判定仍是一次汇总12地点OOF在相同1FP/image、IoU=.5下：B12旧命中保留>=.95、净新增GT>=1、macro地点召回delta>0。核验基线684，不是旧四地点282。净1是会改变下一步的最小实效，不要求oracle+7或三fold全活跃；训练100%FIT保护不是抬高最终95%门槛。原框不变不能代替预算后旧保留，留池和入cap不能代替联合净益。

组件顺序为L0身份/预算/原框/隔离可信；L1门槛保留已有正例并减少无交集竞争池；L2已有正例实际进入容量及FIT受保护联合收益/安全弃权；L3正式OOF主判定。L1/L2保留作为进展但不救L3。当前已知正例有交集只说明它们预计可留池，不证明余下排序能选中或泛化；本局部先验可能牺牲有用远距新增覆盖，必须报告删除量。

若仍无FIT主动受保护净收益，则停止此固定门槛家族，不扫描更大IoU、epsilon、反向/新排序、权重或cap。若留池但不入cap，后续需另冻表示/排序修复；若入cap但无联合增益，优先审单例与联合预算/冲突差异；若FIT有益而OOF不增，利用地点删除和held分项决定支持扩充；若损旧命中，优先集合保护。这些只定义下一实验的触发，不在当前Run加试或改变负结论。新地点持续封存。

## 冻结预算、证据与本轮授权

拟议S01-E015-R001仅一次，gpu-server/D-26-09/ad\xw436，固定venv，CPU1/禁GPU/OMP和MKL1，总3600秒（输入读取至输出核验），主进程及后代聚合RSS4GiB，0.5s监控、E012窗口读取不变。13有限阈值学习（3主+10诊断）、91政策比较、13FIT基线、1汇总+3held比较。0原图/模型前向/原框重打分/新U/梯度/线性求解/full12refit，0自动重跑/预算扩大/换机器。E014实测66.953秒/589MiB仅为参考，不保证Windows新完整时延。

最低输出复用E014：原身份/每候选x、d、eligible，再加positive_intersection；13模型轨迹、OOF冻结、地点删除、capacity_audit、一次汇总和3held实际new/lost/net/FP分解/原框不变；新增locality_audit池删除和自身正支持留存。F00显示每FIT正GT留池前后、最大与学得政策的入cap、阈值及池删除量；F01正式预算后的E003/候选旧保留/净益；F02最多6个按原分数/image/box/key固定选择的实际追加案例或明确空。README区分来源正支持、门槛留存、入选和联合主结果；绘图/验收只读保存对象，不新增真实policy/metric/U。

本轮用户仅授权先冻结、6.1 sol-Medium独立设计审查，通过后实现及合成测试，再按Code Ready规则独立代码审查。无真实缓存政策学习/producer/SSH/传送/推送/Run授权，本轮不执行R001。所有本地拟合测试仅构造数据并显式替换producer guard。

独立工作区codex/s01-e015-locality-gate-20261016，base cce4ecf39b6c8be57d1f24696db343dbad82d366；范围本实验docs、新scripts/pavetrack_locality_selector及tests、审查/状态/故事线。复用私有E014适配、原FIT阈值选择、冻结/诊断/actual metrics/核验，只增加坐标交集判据及只读审计，不改E003–E014冻结代码/结果。safe during running trainings。
