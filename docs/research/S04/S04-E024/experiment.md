# S04-E024 — 前8000联合，后2000固定隐藏特征只训输出头

Storyline S04；protocol20261017-r1-8000joint-2000headonly-comparative；C1合成同状态优化判别。用户授权实现、非训练检查、Codex独立Code Ready及文档更新；未授权本次producer传输/训练。物理目标与损伤/history/fatigue保持冻结，架构/坐标/支持/目标/采样/D/leak/总更新预算均沿用E023。

## 评价修订：`.001` 是历史实验门槛，不是物理标准

用户于2026-10-17明确：保留各历史实验未通过.001的原记录；后续路线不再由该数值单独决定。当前没有把.001与应用需求或FEM参考不确定性绑定的充分依据，因此E024不继承“全三态必须跨过.001”的科学成功/路线淘汰判据。旧指标函数中gate_*与joint_pass仅供核对历史定义，输出摘要明确标为legacy诊断，不能判定应用适用或路线成败。

E024主要估计量是每状态候选相对自身E023的全场和损伤区质量加权UV RMS变化率；背景及window内背景代价、绝对UV RMS和计算成本同时报告。E022/E021/E019为共同历史对照，不重训。三态来自同一暴露轨迹，不视为独立统计重复，不拼赢家，不挑最佳中间checkpoint。无预设新的百分比收益门槛或背景可接受上限；描述性完成不等于科学应用通过。完整性/身份/解码/冻结等数值有效性检查仍严格，不因评价修订放宽。

原E023 c60的全场−22.84%、损伤−24.31%、背景+.156%保留为组件进展，其价值不依赖跨过.001；更早E021/E019比较继续保留，不能因有改进就称已恢复最佳基线。预声明不论是否跨.001都报告完整效应/代价/成本，汇总器不生成自动route_acceptance。

## 用户确认的实际用途及尚缺精度需求

优先用途：损伤演化、裂纹及疲劳判断。UV误差只是上游力学近似，不能直接证明这些输出可用。下一精度需求需沿链明确：UV→应变/应力及活性拉伸能量→history/fatigue驱动→不可逆损伤更新→裂纹几何/转变时点/疲劳累积。需用正确配对FEM前态/时序与参考不确定性，测误差传播，再给物理量/判断的容差与愿意支付的GPU/墙钟/存储成本。

本次不新解FEM，不更新damage/history/fatigue，不新增耦合训练；不能从UV全场RMS或.001推出疲劳寿命、裂纹路径、事件cycle或完整FEM教师资格。独立[应用精度需求草案](application_accuracy_contract.md)保留UNDEFINED项；不编造可接受背景预算或物理容差。

## 三状态配对、单因素和预算

|状态|直接E023历史对照|候选|
|---|---|---|
|c20s4|S04-E023-head-rms-c4ceb5d-20261016-v1-R001-c20s4-localized-s7|原E017alpha.7seed7backbone/共同零输出残差新初始化|
|c60s4|S04-E023-head-rms-c4ceb5d-20261016-v1-R002-c60s4-localized-s7|同状态自己的backbone与原FEM UV目标|
|c83s4|S04-E023-head-rms-c4ceb5d-20261016-v1-R003-c83s4-localized-s7|同上，不resume10000终态|

全部localized alpha.7 seed7，原采样PCG64/索引顺序/完整10000摘要，原E023初始全质量CPUfloat64/two-thread RMS D/s（含bias，floor1e-6/zeroD1）与leak=.01。科学源码c4控制只读字节/UV历史准入；其主目标FAIL及Mac nativeLR/mass/D/rho例外保持。生产端新初始化D/梯度审计须与自身E023原文件完全一致；Mac验证不伪造该native通过。

更新1..8000所有残差隐藏/activation.coeff/head联合；完成8000后，先清空所有.grad=None，再冻结input/hidden/所有coeff，只让output_layer.weight/bias训练8001..10000。backbone/D始终固定。保留同一个AdamW对象和head全部动量/step，无重置。隐藏参数.grad必须None，AdamW不再对其执行梯度或decoupled decay；head计数最终10000、hidden8000。每步验证阶段/mask/计数，tail监测点及最终深核hidden权重/动量摘要。无额外head拟合、LS/ridge、参数扰动或第10001次更新。

实际LR原生CosineAnnealingLR(T_max10000,eta_min1e-5)，optimizer前读取、optimizer后scheduler；首.001、8001使用原对应LR，末实际1.0000024427270673e-5，post-final1e-5。完整actual=expected=原E023/E022/E021 nativeprofile；阶段转换不改LR/paramgroup，不重建optimizer。Mac原生bit例外不放宽。

## 阶段收据、归档、解码

原PRE_UPDATE.json仍只在update1前生成：共同初态、source/map/D/gradient/nativeLR/三态配对/评估规则及阶段规则，之后不可变。

新增step_8000.pt保存全部model及optimizer状态、参数名顺序、完成8000/下一8001；HEAD_ONLY_STAGE_ENTRY.json绑定其hash、原PRE_UPDATE、D/gradient、source/state/run、初期采样摘要、8000实际LR/8001将用LR、冻结前后optimizer/model不变摘要和时间。原PRE_UPDATE绝不覆盖。最终CP也保存真实optimizer状态及阶段/mask计数；每行原11文件+stageJSON+8000snapshot共13份，12个非receipt归档hash及真实独立producer副本。

严格解码重新建类/重算初始D和gradient、核三态/采样/LR/历史身份；根据明确head_only阶段设置requires_grad并严格验证所有隐藏与coeff冻结、仅head可训，不能简单删除旧激活检查。8000stage和10000final所有非输出头模型张量精确相同，隐藏AdamW moment与step精确相同，head step从8000到10000。核stageJSON/CP/final三envelope/hash/时间/原PRE_UPDATE；用8000CP重算被动全场RMS，前0..8000三分区轨迹与自身E023一致；前8000采样摘要独立回放。冻结不是随记录自报。

## 成本与停止

输出preflight/loop/joint/head_only墙钟秒、峰值CUDA allocated/reserved bytes、head/hidden更新数及最终文件大小。墙钟包含规定的监测/阶段快照开销，不冒称纯GPU kernel秒或能耗；旧E023可比成本如测量区间不同则明确不可直接同比。未来应用选择应同时考虑参考FEM成本与误差传播，不以更新数等价实际成本。

身份/nativeprofile/D/阶段/计数/hiddenmoment/采样/数值/BC/支持外/旧文件hash/实际归档任一失效即停，保存日志，不自动修复重投、增步、换GPU/seed/切点/目标或新增背景权重。三态全部有效只标PAIRED_COMPARATIVE_EVALUATION_COMPLETE；完整但无改善仍如实报告，未定义应用容差不虚构scientific PASS。未完整INCONCLUSIVE，完整性错误INADMISSIBLE。旧.001字段仅legacy诊断，background_cost_acceptability和route_acceptance保持null。

## 非训练与独立审核

沿用既有检查，新增非单位D/负coeff初始化/前后函数等价、阶段requires_grad/gradNone、headmoments不重置、hiddenmoment/weight/计数/阶段伪造、原PRE_UPDATE不可变、13文件严格正向临时fixture与一致重hash伪造负例、实际10000LR与无10001、全采样及三态真资产validate-only。临时fixture的8000/10000计数/runtime/cost均人为声明，仅测解码器，不是训练证据；Mac不进入训练循环、不做optimizer参数step。

精确提交后的Codex subagent Code Ready审核通过才具备后续生产包准备资格。Code Ready不是正式native/CUDA预检、性能收益或应用通过。此次无SSH、上传或新训练。

## Code Ready结果（2026-10-17，文档状态更新）

独立Codex subagent审查通过，无阻塞项；精确已审提交`231fe4be83e26ef4054a2a6a567da51229185837`，三个科学文件与`ded0416`字节相同。独立旧版完整31项通过（231.22秒），当前修正测试版17项阶段检查＋真实输出头计数负例共18项通过（46.80秒），两种覆盖分开报告。三态真资产validate-only通过；无训练或optimizer参数更新，正式CUDA/native预检未执行。详见[审查报告](code_ready_review.md)、[精确摘要](code_ready_review.json)及[非训练检查](nontraining_checks.json)。此次仅完成实现与审核，未准备或启动生产。
