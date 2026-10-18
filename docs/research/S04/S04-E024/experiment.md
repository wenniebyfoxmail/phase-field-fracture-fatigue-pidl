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

## 结果追加（2026-10-17；冻结评价不变）

三态原producer均完成并通过原严格解码及归档，完整性有效的比较已完成。相对自身E023，12项全场／损伤／背景／窗口内背景误差全部增加；c60全场+3.7288%、损伤+4.0634%，c83全场+.13377%、损伤+.13423%。不采为精度修复，与是否跨.001无关。整包墙钟3318vs2926秒、输出约3.09倍，较短记录训练段不等于整体节约。独立有限范围Evidence复核无阻塞，严格Mac可移植性例外保留。详见[结果与最小下一步](decision.md)及[evidence_review.md](evidence_review.md)。下一项仅建议固定8000特征的质量加权线性oracle判别，未执行；没有新实验授权。

## 只读诊断E024-D002结果追加（2026-10-17）

按用户授权，三态实际8000快照保持D／BC／窗口／全质量目标，完成独立预用及结果复核。主数值秩279／284／254；c60完整跨度的数值最优仍高于E023全场2.18%，同时E024头尾还未达到该最优，表示与优化两类限制共存。c20／c83有可实现头部收益，背景代价分别约+.40%／+5.73%，窗口内背景+3.78%／+26.33%。数值截断敏感性／实现误差／原后端警告和跨平台例外完整保留；不是统一可用修复或应用验证。[详细结论](fixed_feature_decision.md)、[独立审核](fixed_feature_evidence_review.md)。0神经更新／0CP写回／0远端动作，后续E023联合终态头诊断仅建议未执行。


## 2026-10-17 E024-D003 supplement: E023 joint terminal head

User-authorised three exposed states c20/c60/c83, own E023 final joint10000 checkpoints, unchanged producerD/BC/window/full-mass objective. Diagnostic source e8507f92a7ea869b519d19d129e86a1179826a0f; protocol terminal_head_protocol.md, original-source code preuse review and independent alternate-driver result review passed within numerical-warning limitations. No neural/optimizer update, checkpoint write or remote action. 9 linear solutions plus9 prescribed partial coefficient probes,25.6648s CPU /1,659,256,832-byte peak RSS. Full oracle improves own E023 full/damage but increases backgrounds; partial probes improve all scored regions with disproportionately large parameter increments. See terminal_head_decision.md and terminal_head_{metrics,pairs,numerics,partial,line_geometry}.csv; original verdicts unchanged. A centered parameter trust-region incremental diagnostic is proposed, not executed. .001 historical only; downstream application/background tolerance undefined. Full local archive: local_archive/experiments/S04-E024/terminal_head_oracle_v1.


## 2026-10-17 E024-D004 supplement: original-head-centered10% parameter norm

User-authorised offline constrained head increment on own E023 joint10000 c20/c60/c83, same producerD/BC/window/full-mass target, shared Frobenius radius10% of original head norm across bothUV/bias. Source2c9ab039a3e4497125446d6065bad11593d21a93; protocol centered_head_protocol.md. Eight unit checks and independent Code Ready passed after finite-diagnostic hardening; independent alternate gesvd/dgemm/plain-lambda bisection and Q4/raw/region/KKT verification passed.3 active constrained linear solves,13.4944s CPU /1,674,395,648-byte peak RSS, no neural optimizer/checkpoint write/remote action. Full/damage gains in all states with measured background costs; see centered_head_decision.md and centered_head_{metrics,pairs,numerics,line_geometry}.csv. Original frozen verdicts/portability exceptions unchanged; .001 historical only, application/background tolerances undefined. Proposed same-direction t=.2 step only, not executed. Archive local_archive/experiments/S04-E024/centered_head_trust_region_v1.


## 2026-10-17 E024-D005 supplement: one fixed0.2 shrink actual forward

HQ same-scope night follow-up with direct human authority requested the sole0.2 multiplier on saved D004delta, no new solve/fitting/training/state/holdout. Source3306c1ddb1eace5e601c6672633bf337161c61ab; actual2% original-head norm, D/BC/window/full-mass definitions unchanged.3 actual network layer-order forward checks; all four regional RMS improve versus own E023 in c20/c60/c83, with lower full/damage gains but better backgrounds than D004 full step. D004 original result/old verdicts unchanged. Independent focused509chunk/Q4/asset-hash/arithmetic review PASS; scope/figures in shrink02_decision.md and shrink02_evidence_review.md.9.1185s CPU /718,028,800-byte peak RSS;0fits/0optimizer/0CPwrite/0remote/newdata. Diagnostic external UV/coef in local_archive/experiments/S04-E024/centered_head_shrink02_v1/results. This is not a newly optimal2% trust-region solve, independent generalisation, physical/application or coupled-history validation. No next multiplier or training in this task; completed and closed after recording.


## 2026-10-18 E024-D006: frozen-channel physical observables

User-authorised E023/D005 c20/c60/c83 nativeQ4 strain, AMOR weakrho, psi0/active-energy/instantaneous elastic2(1-d)psi0 diagnosis. Source273e413737dd24a9994cbacce3de86c6a60cc887; originalv1 aborted missingoptional fatigue before scoring, retained; v2same inputs schema-corrected. Existing D/BC/window/damage and reference target fixed, no training or damage/history/fatigue update. Optional fatigue/prior channels unavailablec20/c83, c60 preserved, all maxH absent. Native/reference checks,3 analytical affine checks and independent explicit mechanics/GP/absolute-region scoring passed within scale-aware numerical limits; oldwarning/strictMac exceptions retained. strain/elastic-driver errors slightly improve butrho and somebackground errors worsen; no coupled evolution/usefulness conclusion.96regionalrows/absolute denominators/weakforce error tables, GP fields and figures archived in local_archive/experiments/S04-E024/physical_observables_v2.8.4311s CPU /733,020,160-byte peakRSS. See physical_decision.md/protocol/evidence_review and CSV/receipt. OriginalUV/experiment verdicts unchanged; next weak-balance-guarded smallhead correction only proposed, not run.


## 2026-10-18 E024-D007: bounded head correction with actual weak nondegradation

User-authorised same3 states/D/BC/window/fullmassUV/current2% headnormbudget, no training/history/fatigue/damage update. Source263509c4c7e84756678dca57a39ba5de9faecfe3, weak_guard_protocol.md. Prescribed2Dplane of savedUVdirection plus orthogonal negativeweakgradient;3offline2-variable solves and actual nonlinear force/UV/budget acceptance, predefined8halvings orzero fallback. All3 initial returnedcandidates accepted,no backtracking; actualUV/weakrho/GPfullstrain/elasticdriver all improve slightly, background costs retained. Focus code/independent rawnetwork/AMOR/GP/hashes/budget reviewPASS, no fullhead/physical/evolution claim.15.95997s CPU /1,471,512,576-byte peakRSS. Externalcoef/UV/basis/planez,allactualtrials and exactmetrics archivedlocal_archive/experiments/S04-E024/weak_guard_v1; see weak_guard_decision.md/CSVs/receipt/reviews. Original oldcriterion/portability/warning limits unchanged, .001historical only. NextbackgroundUVguard is proposalnotexecuted; no newproducer/training/holdout.
