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
- 当前 reality assimilation 的 3 条 cadence-only FEM 轨迹物理差异不足且 90% coverage 仅 `0.67`；不支持泛化或部署主张。

## Best Next Discriminator (acquisition-only, no architecture sweep)

2026-08-05 的真实道路轨迹覆盖审计仍成立：当前没有一条路线在同一 asset-time key 下同时提供注册未来裂缝几何、traffic/load、temperature、moisture、structure/mechanics 与 maintenance/censoring。PaveTrack_PD location `10` 已降级为 scene-level；LTPP 仍不是完整机制路线，但已从 `06-1253` 单路段 pilot 扩展为一个通过最小 acquisition gate 的多路段 geometry-climate benchmark 候选。

California 126 条 section 的官方 viewer 全量审计得到 20 条重复地图库存候选；经 RGBA 白底合成、逐日期物理网格检测和印刷站距人工复核后，`06-1253`、`06-2041`、`06-8149`、`06-2647`、`06-8150`、`06-8201` 共 6 条独立沥青 section 各保留至少 5 个 climate-complete survey states，完整 timeline 在保留 construction prefix 内未触发 maintenance/reset review。总计 37 个 states、31 个 transitions；`06-1253` 的 2015 图因气候不完整不进入主序列。机器收据、哈希和边界见 `ltpp_geoforecast_multisection_gate_20260805.md`。




**LTPP enriched-input track（有效负结果）**：经 Pro 授权的冻结 posterior 已完成；四个 LOSO 增量比较均未通过，完整 M3 相对 persistence 的 MAE 反而恶化 4.13%（仅 3/6 section 改善），O3 realized-exposure 诊断在匹配 29 行仅改善 0.0093 m，不能挽救主结论。该结果只说明六路段/30-transition 协议下未见稳定增量预测价值；完整证据维护在 `experiments/ltpp_geoforecast_enriched_input_track.md`。

**LTPP load-only incremental track（输入预检通过、等待 fit authorization）**：29-row outcome-free preflight 已通过（唯一排除 `06-1253-T07`；24 development + 5 future-time；G vs G+单一年度 ESAL），但尚未授权 posterior。下一步只申请 `APPROVE_LOAD_ONLY_POSTERIOR_FIT`，不改变行、特征或门槛。完整协议维护在 `experiments/ltpp_geoforecast_load_only_incremental_track_20260806.md`。

## Breakthrough / Publication Gates

- **Feasible paper**：真实纵向轨迹上，calibrated probabilistic baseline 显著优于 persistence/linear growth，并公开 provenance-safe benchmark。
- **Strong Nature-portfolio paper**：跨道路/气候/材料 holdout，world model 在 crack geometry、transition timing、coverage 和 maintenance utility 上同时通过，并有 prospective blind test。
- **Nature-level opportunity**：证明一个跨实验室—试验道路—运营道路可迁移的裂缝状态表示或可检验演化规律，并通过真实干预（维修、排水或荷载变化）做 counterfactual/prospective validation；单一网络结构或 synthetic FEM leaderboard 不足。

## Stop / Switch Rules

- 不再用单轨迹、随机帧切分、同一路段 cadence 变化声称 generalisation；必须按 physical asset/site/environment 分组 holdout。
- 不把 generative video 视觉逼真度当物理预测；headline metrics 必须是未来 registered mask/tip/area、event timing、CRPS/coverage 与决策效用。
- 若公开数据无法对齐图像—荷载—天气—维修时间轴，立即转为最小 prospective pilot；若 world model 不优于 persistence 和 observation-only state-space baseline，则停止扩大架构。
- 暂停新的 PIDL loss/architecture sweep、Freeze-Then-Select 阈值调节、未合格 FEM corpus 和单轨迹 foundation-model 宣称。
