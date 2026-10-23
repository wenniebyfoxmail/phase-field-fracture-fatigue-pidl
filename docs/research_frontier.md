# Research Frontier

**规则**：此文件是“一屏决策前线”，不是历史日志。Current Question 只能 1 个，Active Branches 最多 3 个；关闭分支移入日志或 registry。
**Owner**: Mac-PIDL | **Updated**: 2026-08-06

---

## North Star / Current Question

**能否只使用可部署的道路观测（注册图像/3D、交通荷载、天气、挠度或稀疏应变/AE），构建一个经过校准的 observation-conditioned road-fracture world model，在未见道路与气候上前瞻预测裂缝几何、失效/养护风险及不确定性？**

PIDL/FEM 不再是最终产品，而是可与经验状态空间模型、数据驱动模型竞争并被现实观测纠正的 transition prior。相场隐变量只能用于 oracle audit，不能作为部署输入或现实结论的 ground truth。

## Active Branches

1. **Real longitudinal road evidence (PRIMARY)** — 先建立真实的 asset-time trajectory，而不是继续扩大 synthetic trajectory。PaveTrack-PD 提供 165 个固定位置、约六个月的裂缝/坑槽跟踪与 masks；MnROAD 提供真实交通、天气、结构传感器和重复 distress survey，但二者是否能形成同一资产、同一时间轴、同一事件语义的可训练序列尚未证明。第一目标是数据交集与 provenance audit；现实合作优先对接 Cambridge Digital Roads of the Future / National Highways，争取可前瞻复测的道路小样本，而不是另起一个孤立采集系统。
2. **Observation-conditioned fracture world model (METHOD)** — Encoder 将图像/3D/载荷/天气/稀疏 mechanics 映射为不确定 latent state；action-conditioned transition 预测自然演化与养护/排水/限载干预；decoder 输出未来 crack mask/tip/area、pothole transition、RUL/maintenance risk 和 calibrated uncertainty。Direct FEM、PIDL、经验增长律和 learned operator 使用同一观测协议公平竞争；每次新观测通过 Bayesian filtering/assimilation 更新状态。
3. **Physics-to-reality calibration bridge (ENABLER)** — 保留 c89 field-mechanism 作为局部科学问题：reaction/global stiffness + sparse mechanics 能否辨识 near-core degradation amplitude。Azinpour/GRIPHFiTH 只有通过 strict fixed-point/provenance qualification 才能生产训练数据；优先做小型加速加载试件的图像/3D + DIC/AE + load 同步实验，用作 sim-to-real calibration，不把未合格 FEM 当 teacher。

## Current Evidence / Claim Boundary

- Hard-recovery PIDL 可匹配 FEM `N_f=89`，但 active-driver/process-zone/history 不共定位；正确事件时间不等于正确机制。
- c86 true diffuse damage 条件化可近闭合后续场，二值裂缝几何失败约 `100x` support area：缺失的是近核状态幅值，不只是裂缝位置。
- LTPP `06-1253` observation-state experiment tested whether a noisy irreversible latent history can outperform persistence and a nonmonotone trend on full-field rolling forecasts. v1 completed as `FAIL_L_NOT_QUALIFIED`: it improved median bMAE by 7.57% versus persistence but missed the frozen 10% gate and one interval-coverage gate; do not tune this section further, and test reproducibility only in the separate multisection route. Experiment: `docs/experiments/ltpp_06_1253_observation_state_gate_v1_20260805.md`; workstream: `docs/workstreams/ltpp_06_1253_single_annotator_fts_progress_20260805.md`.
- The multisection LTPP benchmark is now terminal rather than blocked. Human adjudication reached `139/139`; 37 locked states contain 249 final geometries (232 crack), and all hashes passed. The leakage-safe package contains 25 development plus six future-time transitions. On future time, local-tip extrapolation moved mean F1 only `0.4333 -> 0.4368` while worsening new-geometry error `1.6018 -> 1.6847 m2`. The one-shot hierarchical state-space challenger was `RELIABILITY_NEGATIVE`: versus persistence on unseen sections, length error worsened `15.63%`, new-geometry error worsened `6.31%`, and joint wins were `0/6`; nominal-90% coverage `0.9355` was the only passing gate. Persistence remains the honest point control. Decision: `docs/ltpp_geoforecast_algorithm_plan_20260805.md`; handoff: `docs/ltpp_geoforecast_blind_packet_handoff_20260805.md`.
- **LTPP spatial-registration track（二维路线暂时关闭）**：外部审核后一次性运行的 `06-1253` frozen-grid audit 只有 `2/8` 日期通过；1995、2001、2007 控制线不足，1991、1997、2003 又未通过预设空间误差门。2026-08-10 的 no-OCR complete-grid MVP 与独立 outer-boundary/topology MVP v2 都在 8 个已见 development 页面全部 fail-closed；后续冻结 A/B owner review 仅为 1991/1995/1997/2012 建立工程页面画布候选，仍有 4/8 fail-closed，不能成为裁切或配准证据。不得调参重跑或进入二维路线。因此当前 deskew/crop/resize carrier 不得进入二维位置或裂缝尖端算法；这不追溯否定独立的标量长度任务。完整证据维护在 `docs/experiments/ltpp_geoforecast_spatial_registration_track.md`。
- 当前 reality assimilation 的 3 条 cadence-only FEM 轨迹物理差异不足且 90% coverage 仅 `0.67`；不支持泛化或部署主张。

## Best Next Discriminator (acquisition-only, no architecture sweep)

2026-08-05 的真实道路轨迹覆盖审计仍成立：当前没有一条路线在同一 asset-time key 下同时提供注册未来裂缝几何、traffic/load、temperature、moisture、structure/mechanics 与 maintenance/censoring。PaveTrack_PD location `10` 已降级为 scene-level；LTPP 仍不是完整机制路线，但已从 `06-1253` 单路段 pilot 扩展为一个通过最小 acquisition gate 的多路段 geometry-climate benchmark 候选。

California 126 条 section 的官方 viewer 全量审计得到 20 条重复地图库存候选；经 RGBA 白底合成、逐日期物理网格检测和印刷站距人工复核后，`06-1253`、`06-2041`、`06-8149`、`06-2647`、`06-8150`、`06-8201` 共 6 条独立沥青 section 各保留至少 5 个 climate-complete survey states，完整 timeline 在保留 construction prefix 内未触发 maintenance/reset review。总计 37 个 states、31 个 transitions；`06-1253` 的 2015 图因气候不完整不进入主序列。机器收据、哈希和边界见 `ltpp_geoforecast_multisection_gate_20260805.md`。




**LTPP enriched-input track（有效负结果）**：经 Pro 授权的冻结 posterior 已完成；四个 LOSO 增量比较均未通过，完整 M3 相对 persistence 的 MAE 反而恶化 4.13%（仅 3/6 section 改善），O3 realized-exposure 诊断在匹配 29 行仅改善 0.0093 m，不能挽救主结论。该结果只说明六路段/30-transition 协议下未见稳定增量预测价值；完整证据维护在 `experiments/ltpp_geoforecast_enriched_input_track.md`。

**LTPP load-only incremental track（单因素负结果）**：Pro 授权的 29-row G vs G+ESAL posterior 已完成；G+L 的 LOSO MAE 比 G 恶化 0.376%，仅 2/6 section 改善，未通过增量 gate。该结果只说明当前六路段/29-transition 面板中的单一年度 ESAL 通道没有稳定增量预测价值；完整证据维护在 `experiments/ltpp_geoforecast_load_only_posterior_result_20260806.md`。

## Breakthrough / Publication Gates

- **Feasible paper**：真实纵向轨迹上，calibrated probabilistic baseline 显著优于 persistence/linear growth，并公开 provenance-safe benchmark。
- **Strong Nature-portfolio paper**：跨道路/气候/材料 holdout，world model 在 crack geometry、transition timing、coverage 和 maintenance utility 上同时通过，并有 prospective blind test。
- **Nature-level opportunity**：证明一个跨实验室—试验道路—运营道路可迁移的裂缝状态表示或可检验演化规律，并通过真实干预（维修、排水或荷载变化）做 counterfactual/prospective validation；单一网络结构或 synthetic FEM leaderboard 不足。

## Stop / Switch Rules

- 不再用单轨迹、随机帧切分、同一路段 cadence 变化声称 generalisation；必须按 physical asset/site/environment 分组 holdout。
- 不把 generative video 视觉逼真度当物理预测；headline metrics 必须是未来 registered mask/tip/area、event timing、CRPS/coverage 与决策效用。
- 若公开数据无法对齐图像—荷载—天气—维修时间轴，立即转为最小 prospective pilot；若 world model 不优于 persistence 和 observation-only state-space baseline，则停止扩大架构。
- 暂停新的 PIDL loss/architecture sweep、Freeze-Then-Select 阈值调节、未合格 FEM corpus 和单轨迹 foundation-model 宣称。

## 2026-10-21 — S04-E035 published static shear

Published Manav21-page paper and code links verified. Authorized recovery repair R009 passed recovery and accepted seven loaded states through U=.21, then stopped at U=.24 in the added loaded-PF residual Armijo rule. All50remote files hash verified; saved loaded states independently checked. Full U=.4 reference absent, so PIDL was not started. Whole-PF native Newton candidate and conditional PIDL deployment are prepared and reviewed, unexecuted. The one repair attempt is consumed; original deadline and prior costs retained. See [owner](research/S04/S04-E035/experiment.md), [R009](research/S04/S04-E035/runs/S04-E035-R009.md), and preserved [R008](research/S04/S04-E035/runs/S04-E035-R008.md).

R011 full native-PF preparation remains unexecuted: first SCP failed DNS before upload; automatic approval review then rejected new remote upload/compute authority. Zero scientific starts, no PIDL; explicit new human launch permission required. R009 outcome unchanged. See [owner](research/S04/S04-E035/experiment.md).

R011 update: human explicitly approved exact submission; MATLAB17960 started19:00:10Z onCITPC12 with9750s cap. Original00:20Z deadline retained; R010 remains conditional on full24-state validity. [45-degree follow-up design](research/S04/S04-E035/mixed_direction_next_plan.md) prepared, not launched.

R011 terminal: six valid loads throughU=.18; U=.21 native PF preupdate residual8.92e-7 but returned fresh scalar1.23e-6. Locked code and saved fields locate update/stop-point mismatch; no coupled acceptance for rejected load.47files hash verified, both own PIDs exited, noPIDL. Consistent-return candidate prepared/unexecuted; [result/next decision](research/S04/S04-E035/runs/S04-E035-R011.md).45degree remains planned only.

R012 active: human approved consistent-return repair and later equal-U45degree within original window. MATLAB30120 onCITPC12 has accepted throughU=.28; U=.29coupling active, noPIDL yet. Reviewed independent Q4GP/T3 mapping ready;45degree science/verifier code reviewed, deployment remains conditional on0degree full comparison and remaining shared budget. [Owner](research/S04/S04-E035/experiment.md).

R012 terminal:12/24 states throughU=.28 valid. AtU=.29 coupled sum9.925185e-5 met, but9nodes exceed1.005(max1.006614).66files fully verified; noPIDL/45°. ActualAT1 source has no upper-bound penalty; no grounded same-equation repair identified. Same-model retry remains conditional; common bound-constrained model only proposed for scientific selection. [R012](research/S04/S04-E035/runs/S04-E035-R012.md), [nextcontract](research/S04/S04-E035/range_resolution_next_contract_20261021.md).

Common-box prospective revision explicitly human-approved20:52Z; sameowner prepares one full0°FEM thenconditionaloriginalGPU NN underoriginalcumulativebudget/deadline. Originalpenalty-onlyR012remains12/24. [Frozenprotocol](research/S04/S04-E035/common_box_protocol_20261021.md).

R015 common-box FEM active onCITPC12 MATLAB40592 since21:08:11Z; mandatoryarrayfixturespassed, frozenend22:47:49Z. Full24-statequalificationpending; noNN/45°. [Run](research/S04/S04-E035/runs/S04-E035-R015.md).

R015 terminal:7/24 common-box states throughU.21 verified; U.24phase energyline search exhaustedfull+12halvings.55fileshashverified,ownPIDsexited,189.667s; noPIDL/45. Saved13trialenergy reconstruction locates insufficient finite-step schedule; curvature-controlled initial-step candidate reviewed/prepared, neverexecuted. Originaloneattemptconsumed, freshsame-modelrerunapprovalrequired. [Result](research/S04/S04-E035/runs/S04-E035-R015.md), [proposal](research/S04/S04-E035/common_box_curvature_proposal_20261021.md).

Directhuman21:42Zapprovedonecurvature-controlledfullFEMretry withinoriginalcumulativebudget/deadline; R017adapterprepared, no launchyet. Alloriginalnegatives/costsretained; conditionalR016NNnowrequiresfullR017reference. [Run](research/S04/S04-E035/runs/S04-E035-R017.md).

R017 terminal:recoverypassed,0loadedstates; MATLAB nestedmechanics overwrote sharedphaseopts, losingcurvature callback.37fileshashverified,ownPIDsexited,21.507s actualscience(consumed). Namespace-only fix reviewed/prepared, notrun; noPIDL/45. Old2hNNopportunity admissionpoint21:50Zpassed, futuretimearrangementrequiresdecision. [Result](research/S04/S04-E035/runs/S04-E035-R017.md).


2026-10-22 renewal: originalsciencewindowclosed,no newstartthere. DirectHQhuman reply verified “批准新6小时计算窗口”; unique00:14:22Z start/prep00:44:22/science05:44:22/total06:14:22. NewFEM≤2h thenconditionalPIDL≤3GPUh, eachoneactualstart/firstfailurestop; samecommonbox/params/resources, alloldcostsretained. R018/R019preparing; originalagent7200sNNfloorremoved, full24FEMstillrequired;45°deferredoutside6h. [Owner](research/S04/S04-E035/experiment.md), [authority/time](research/S04/S04-E035/approval_window_closed_20261022.md).

R018 active00:19:02Z:CITPC12 MATLAB48532/supervisor47392,cap7186.241s/frozenend02:18:49Z; same-batchfixturespassed, full24statespending, noPIDL/45. [R018](research/S04/S04-E035/runs/S04-E035-R018.md).

R018postlaunchremote status auto-review BLOCKED twice before command creation: interprets HQ humanstop-hosting as prohibiting owner runtime monitoring, despite originalHQhandoff checked. No workaround; actualR018FEM start consumed, latestfixturespassed/0loaded observed only, currentcoverage/terminalUNKNOWN. Autonomous ownsupervisor hardend02:18:49Z remains. R019unlaunched/full24referenceabsent; fixed6hclock unchanged. Specificpermissionneededfor originalowner resultverification/retrieval/conditionalPIDL, notnewbudget. [Owner](research/S04/S04-E035/experiment.md).

2026-10-22 06:42Z: directhuman clarifies stop-hosting onlyHQ and authorizes owner continuation, but explicitly retainsfixeddeadline; total06:14:22Z alreadyexpired. No remote calls/newstarts; R018terminal/retrievalstillabsentlocally, R019unlaunched. New600s read-onlyclosurepreparedonly; no sciencewindowextension or clockreset. [Owner](research/S04/S04-E035/experiment.md).

R018 retrieved/verified:56files41,650,658byteshashmatched,6/24validtoU.18; U.21/stag3 PF500 iterationstop at00:23:15Z,252.221s,CPUUNKNOWN. Notdeadlinefailure; option-scopeintegrationpassed.500bt0 energy-decreasing steps but finalKKT5.069e-5>1e-6; fullrayQconservatismplausible,notunique. NoNN. Sameenergy piecewiseray-firststep candidate prepared underlatestdirectstartrequest, pending source/toolapproval, no newworker. [R018](research/S04/S04-E035/runs/S04-E035-R018.md).

Latestdirect“请启动计算”: R020/R021 sameenergy piecewiserayinitialstep package prepared/code-mathreviewed, notrun. Prospective newexecution interpretation/windows explicit; no oldwindowreclassification, actualtoolapprovalstillrequired. [Plan](research/S04/S04-E035/ray_step_restart_plan_20261022.md).

R020 active07:08:17Z:MATLAB34280/supervisor46232,CITPC12,cap5838.221s/frozenend08:45:35Z,commit ed5766a6; prospective lateststartrequest executionapproved, waitedforotherMATLABrelease. Fixturesreturned/actualBOX_RAYseen, full24qualificationpending; noNN. [Run](research/S04/S04-E035/runs/S04-E035-R020.md).

R020 terminal:12/24validtoU.28; U.29/stag25/PFiter9 ray actualslopes allnonnegative/energyunchanged, KKT1.13297e-6>1e-6.573.016s/RSS1.633GiB/CPUUNKNOWN,77files72,364,190byteshashmatched,ownPIDsgone; notdeadline. NoNN/45. Directionfirst-orderdescent safeguard+fullcurrentwitness prepared/source-reviewedonly; R020actualattemptconsumed, newactualretry/timeenvelopependinghuman. [Result](research/S04/S04-E035/runs/S04-E035-R020.md), [nextproposal](research/S04/S04-E035/descent_safeguard_proposal_20261022.md).


2026-10-23 S04-E035: 人方批准方向保障修复完整重跑、取消计算预算上限；R022准备完整24态共同有界FEM，全部通过U=.4才继续R023原PIDL。旧窗口不再执行，科学判据/资源安全限保持；45°在主比较之后。[owner](research/S04/S04-E035/experiment.md)。

R022 actual: CITPC12 MATLAB23108 started15:36:02Z Oct23, unlimited_compute=true. Full24-state verification pending; noPIDL yet. [Run](research/S04/S04-E035/runs/S04-E035-R022.md).
