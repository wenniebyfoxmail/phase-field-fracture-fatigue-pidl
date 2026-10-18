# FEM synthetic supervision track

机制问题：从FEM全场数据锚点出发，怎样保留正确损伤历史界并改善PIDL局部active场，而不让u/v/d偏离已知状态？历史已存在MIT-8、Path C、四字段与mesh预训练；不主张首次FEM增强。当前仅为已暴露合成c20s4/horizon0/seed1的C2状态拟合探索，不作自主演化、物理真值或泛化结论。

当前结果：[E032冻结空间联合曲率选择](../research/S04/S04-E032/result_20261018.md)完成：raw全域再降.0460047%<事前.1%目标，幅度主标准negative；七指标组件收益保留（UV全域/Z再降4.45%/2.15%），物理damage逐位不变。但u全域/Z误差回退15.25%/8.30%，反力出现过冲，旧全域active代价仍在。不是完整FEM复现、演化或泛化；[E031](../research/S04/S04-E031/result_20261018.md)及更早结果冻结。

|决定|用途与最小证据|结果／下一步|
|---|---|---|
|D1 复用（完成）|历史方向、实现与负结果检索；原方案与E027准备记录|沿用既有FEM监督资产，限定单态修复问题|
|D2 失效分解（完成）|E027原始三臂及raw×degradation分解|C损伤几乎抹除；不能把低force作完整物理收益|
|D3 可行性+active锚点（完成）|E028固定两臂200步|硬界保持、active仍漂移；两臂d全回lower，真实导数0|
|D4 表示修复（完成）|E029单因素映射、固定200步、全部场/数值|导数恢复且有训练增量，主读数仍未改善|
|D5 UV隔离（完成）|E029全部200更新时序对齐、E030固定物理UV同设置200步|实际damage与局部active可改善，排除完全不能学；global active/force代价仍在|
|D6 UV头受保护有限校正（完成）|原生2×2代数归因/左带误差分区，复用E024/PC16既有路线；E031原802头内一步|首候选七指标均下降，raw收益极小、旧global active代价仍在；实际图/数值独立核验通过|
|D7 同空间联合曲率选择（完成）|E031保存梯度/曲率诊断→E032从其实际终态一次小空间SLSQP+真实有限校正|raw幅度目标negative，UV组件进展但u回退；当前七维配方停止追加|
|**D8 平面外可达性（E033资源首停）**|原802头当前方向的只读诊断及条件性单轴校正已准备/焦点审查|GPU5资源条件未通过，早于worker启动；完整头方向未测量，停止本Run、不重试或换卡|

## 冻结历史

[E027](../research/S04/S04-E027/result_20261018.md)：3500更新/.67496GPU小时，C/S=.952342（下降4.77%）但C几乎抹去损伤；初态active误差也低于S/C。三臂执行/取回/独立图审完成，限定方向信号保留，非完整修复。原判据与结果不改。

[E028](../research/S04/S04-E028/result_20261018.md)：400更新/.18049GPU小时，R/B=.27403但R3.83983劣于mapped0 .77277。d终态全部等c20s3 lower，真实投影导数0；可行性组件成功，active拟合修复negative。原实验已冻结，不重跑。

[E029](../research/S04/S04-E029/experiment.md)：相同S1500、fresh Adam、seed、损失、采样与200步，仅damage改为true AD的bounded increment，含独立0步对照。8项fixture检查及7c72db17焦点审查通过后执行新Run；精确runtime/授权/成本/取回/主读数在[run_summary](../research/S04/S04-E029/run_summary.json)。下一决定基于实际数据，非“审查通过即可称修复”。



[E030](../research/S04/S04-E030/experiment.md)：在新表示、目标、Adam、采样和起点均不变下，只固定原S1500物理UV。真实局部active .772727→.738755，Z d .00767785→.00581067，4115节点增长域d .01200765→.01025541；对照E029联合训练终态active2.72229。所有位移/原生raw不变、保存导数和0/50/200字段核验通过。全部200更新后active明确保存，137仍高于零步，不能择最低状态；无Adam因果定论。完整实际身份/资源/取回见[run_summary](../research/S04/S04-E030/run_summary.json)。

[E031](../research/S04/S04-E031/experiment.md)：精确原S1500的冻结hidden/UV起点配合E030实际物理damage，七个真实指标的802维凸包证书给共同下降方向；2%半径上限经UV精确曲率取.0170182 fraction，实际头相对变化.0340364%。一候选被接受，一次实际头写入；并非FEM UV代换。首候选/前向/控制身份/所有分量、21项hash、五图与独立产物核验完成，见[run_summary](../research/S04/S04-E031/run_summary.json)。

[E032](../research/S04/S04-E032/experiment.md)：在实际E031终态固定hidden/damage，从已保存七梯度冻结空间计算当前梯度，联合UV二次式/raw tangent/严格切线cone选择系数。13次proxy迭代后full候选因Z UV舍入级超值严格拒绝，half接受；full raw .0920693%也未到.1%，主目标miss不是只由舍入拒绝造成。保存proposal的凸proxy KKT残差1.11e−8，解释局部约束取舍而非全头容量。实际u回退和反力过冲明确保留；24项大小/SHA、原生分量/参数/basis/候选重算与五图独审通过。见[收据](../research/S04/S04-E032/run_summary.json)。

六次Run receipt累计1.09177620GPU小时<原2小时总限；E03242.648329秒/.01184676GPU小时，无重试、替代权重或history提交。D7完成，停止当前七维配方追加优化。HQ选定D8后，[E033首次资源准入停止](../research/S04/S04-E033/admission_stop_20261019.md)：GPU5 18314MiB空闲/87%利用率，未到20480MiB/0%。无worker、模型/梯度/校正/FEM及残留进程，新增GPU小时0；完整802维方向仍未评价。本Run停止，不重发/换卡/新编号绕过，后续资源安排由HQ决定。
