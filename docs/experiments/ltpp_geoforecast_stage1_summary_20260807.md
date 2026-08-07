# LTPP GeoForecast Stage 1 阶段总结

- **主要工作时间：** 2026-08-05 至 2026-08-07
- **总结归档日期：** 2026-08-07
- **阶段状态：** 标注与裁决完成；标量预测、富集输入和 load-only 增量实验已完成首轮门控；自动识别和二维配准未通过资格门
- **文档角色：** 本文件是面向阅读的阶段总结，不替代各实验预注册、结果文件或哈希证据
- **证据总索引：** `docs/experiments/ltpp_geoforecast_evidence_archive_20260807.md`

总体结论：我们已经把这批标注做成了一个完整、可审计的 LTPP 小样本研究基准，但目前得到的主要是可信的负结果。

- 标注和裁决流程完成；
- 标量裂缝长度可以继续研究；
- 当前模型没有稳定胜过 persistence；
- ESAL、交通、结构、FWD 暂未显示增量预测价值；
- 自动裂缝识别未达标；
- 跨日期二维配准未达标，因此不能研究裂缝尖端位置或二维演化。

## 本对话框的研究目的、方法、工作、结论与证据位置

本节把本次对话中形成的研究链条压缩成一个可追溯入口；各项具体规则、结果和哈希仍以链接到的实验文档为准。

### 研究目的

我们不是单纯寻找一个“更强的模型”，而是建立一个小规模、可审计、无时间泄漏的 LTPP 道路裂缝预测基准，逐步回答：

1. 人工裁决后的扫描图标签是否足以支持可重复的时序任务；
2. 当前裂缝状态能否预测下一调查时段的裂缝长度增长；
3. 在未见过的路段上，增加气候、交通、结构、FWD，或只增加单一荷载通道，是否带来稳定的增量预测价值；
4. 什么时候应停止并报告负结果，而不是继续事后调参。

研究边界已冻结：这是预测信息价值和任务可行性研究，不是因果推断；标量长度预测、二维空间配准和原图裂缝识别是三个分开的问题。

### 采用的方法

- **数据与标签：** 对 6 条 LTPP section 的扫描图进行 AI/人工盲配对、逐项裁决，并冻结最终 GeoJSON 与 SHA-256 manifest。
- **时序构造：** 将 37 个调查状态组成原始 31 条相邻 transition；以 source 状态预测下一调查状态，保留 25 条 development transition 和 6 条 future-time transition。
- **验证：** 主要采用 Leave-One-Section-Out（LOSO），并单独保留未来时间轴检查；所有标准化、正则和先验只在训练折内确定。
- **标量目标：** 预测下一时段新增裂缝长度 `ΔL = max(0, L_target - L_source)`，以 persistence 作为不可省略的诚实基准，主要指标为 MAE。
- **模型与增量实验：** 先测试分层状态空间模型；随后冻结 Geometry+Climate → +Traffic → +Structure → +FWD 的 enriched-input 消融；在该轨道失败后，另开只增加一个 `ANNUAL_ESAL_TREND` 的 load-only track。各轨道在 input freeze、prior-predictive 和 outcome fitting 之间实行 fail-closed，不以结果驱动删行或改算法。
- **二维与识别资格：** 单独审核跨日期空间配准，以及从原始扫描图自动识别裂缝的 B0/B1 方法；不把这两项结果混入标量预测结论。

### 已完成的工作

- 完成 37 张 AI 标注、37 张人工标注和 139 项分歧裁决，冻结 37 个状态、249 个最终几何对象（其中 232 个裂缝对象）。
- 建立时间线网页、transition 表、persistence 和局部基准，并完成最终 6 路段 LOSO 评估。
- 完成分层状态空间模型、30-row enriched-input sensitivity experiment，以及 29-row load-only 单因素 ESAL experiment；全部保留预检、split receipt、诊断和 sealed evaluation 哈希。
- 完成自然发展 episode 审核、自动裂缝识别 B0/B1 评估和 06-1253 八日期二维配准审计。

### 得到的结论

- **标签和实现层面：** 标注、裁决、数据连接、采样器诊断和结果封存均可审计；失败不是因为 NUTS 未收敛或代码没有运行。
- **标量预测层面：** persistence 仍是最可靠的控制。分层状态空间模型没有稳定改善；在 enriched-input 轨道中，完整 M3 相对 B0 的 LOSO MAE 反而恶化 `4.132%`，只在 `3/6` 个 section 改善。
- **单一荷载层面：** load-only 的 `G+L`（几何状态 + 单一年度 ESAL）相对 `G` 恶化 `0.376%`，仅 `2/6` 个 section 改善，未通过预设整体门槛。因此本数据和当前任务定义下，没有证据表明该单一 ESAL 通道具有稳定增量预测价值。
- **二维与识别层面：** 空间配准正式结果为 `2/8`，自动识别 B0/B1 也未达标；因此不能声称已经预测裂缝位置、尖端或现场裂缝物理真值。
- **科学解释边界：** 这些是“在当前 6 路段、观测频率、特征连接和任务定义下未观察到增量预测收益”的负结果，不等于交通、结构、FWD 或气候在物理上不重要，也不构成因果结论或对整个 LTPP 的推广。

### 证据在哪里

- **阶段总索引：** [LTPP evidence archive](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/experiments/ltpp_geoforecast_evidence_archive_20260807.md)
- **标注与裁决：** 本文第 1 节；最终 manifest 位于 `local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/adjudicated/adjudicated_manifest.json`。
- **分层状态空间结果：** 本文第 4 节及对应结果文档。
- **富集输入结果：** [enriched-input posterior result](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/experiments/ltpp_geoforecast_enriched_input_posterior_result_20260806.md)，sealed evaluation SHA-256：`f3a18f4fc9bdd186da8d1e42fad44d688030e5569f17f36a720f76e53e26c6d2`。
- **load-only 结果：** [load-only posterior result](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/experiments/ltpp_geoforecast_load_only_posterior_result_20260806.md)，sealed evaluation SHA-256：`c0f0d2006661b514e332c3446fa8257f536d69010006fd8e8dd2998cb7d4ba03`。
- **自然发展、识别、配准：** 本文第 7–9 节及各节列出的代码、结果文档和原始 JSON。
- **本对话的决策背景：** 对话中引用的 `LTPP 消融预检分析` 与 `LTPP load-only track` 是讨论和审核记录；正式可复现实验以本仓库的 dated preregistration、result、receipt、manifest 和 archive 为准。

## 1. 标注、双盲比较和最终裁决

我们完成了：

- 37 张 AI 独立标注；
- 37 张人工标注；
- AI/人工盲配对；
- 139 项分歧逐项裁决；
- 冻结最终 GeoJSON 金标准；
- 为每个文件生成 SHA-256。

结果：

- AI：37 张、445 个对象；
- 人工：37 张、245 个对象；
- 初始 AI/人工几何 F1：`0.6921`；
- 139/139 项完成裁决；
- 最终：37 个状态、249 个对象，其中232个裂缝对象。

注意：这里的“金标准”是当前扫描图的人工裁决参考，不等同于现场真实物理裂缝。

代码：

- [标注网页](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_vector_annotator_server.py)
- [人工标注迁移](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_migrate_locked_human_annotations.py)
- [标注角色冻结](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_freeze_annotation_role.py)
- [AI/人工盲配对](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_pair_blind_vectorizations.py)
- [裁决队列生成](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_build_adjudication_queue.py)
- [裁决网页](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_adjudication_server.py)
- [最终标签冻结](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_freeze_adjudicated_labels.py)

依据：

- [完整标注数据包](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805)
- [最终标签 manifest](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/adjudicated/adjudicated_manifest.json)
- [139项裁决记录](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/adjudication_queue.json)
- [完整交接记录](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/ltpp_geoforecast_blind_packet_handoff_20260805.md)

最终 manifest 哈希为：

```
6a9422bdcef707fa861b05ad0c817d6deaa4e4ad03ea636c46c5820f8b01f4ad
```

我刚刚重新计算，仍与文档记录一致。

## 2. 按路段和日期查看损伤发展

我们建立了只读时间线网页，可以按同一路段、调查日期排序，同时显示：

1. 原图；
2. AI 标注；
3. 人工标注；
4. 最终裁决标注。

还显示裂缝长度、面积、相邻日期变化和 Out-of-Study 提示。

代码：

- [时间线服务器](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_timeline_review_server.py)
- [对应测试](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/tests/test_ltpp_timeline_review_server.py)

依据：

- [工具说明与验证结果](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/experiments/ltpp_geoforecast_timeline_review_tool_20260806.md)

这个工具只是查看器，不产生新科学结论。

## 3. 构建时序 transition 和便宜基准

我们把37个状态连接成：

- 6条 LTPP section；
- 31个相邻调查 transition；
- 25个 development transition；
- 6个最终时间点测试。

随后比较了：

- persistence；
- scalar linear growth；
- local-tip extrapolation。

结果：

- 未来6个时间点上，persistence 裂缝长度 MAE：`7.0543 m`；
- local-tip extrapolation MAE：`7.8401 m`；
- 空间 F1 只从 `0.4333` 变为 `0.4368`；
- 新增几何误差反而从 `1.6018` 增至 `1.6847 m²`。

因此 persistence 保留为最诚实的基准。

代码：

- [构建 transitions](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_build_adjudicated_transitions.py)
- [运行冻结基准](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_run_frozen_baselines.py)

依据：

- [transition manifest](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/adjudicated_transitions/transition_manifest.json)
- [逐行 transition 数据](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/adjudicated_transitions/transitions.json)
- [基准汇总](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/frozen_baselines/baseline_aggregate.json)
- [算法决策文档](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/ltpp_geoforecast_algorithm_plan_20260805.md)

transition 和 baseline manifest 的当前哈希也与冻结记录一致。

## 4. 分层状态空间预测

我们用裂缝状态、调查间隔和气候信息，运行了一次固定的分层概率状态空间模型，以 LOSO 检验对未见路段的预测。

结果：

- 裂缝长度误差相对 persistence 恶化 `15.63%`；
- 新增几何误差恶化 `6.31%`；
- 同时改善长度和几何的路段：`0/6`；
- 90%区间覆盖率：`0.9355`，只有这一项通过。

结论是 `RELIABILITY_NEGATIVE`。模型可作为不确定性诊断，不能称为可靠预测器。

代码：

- [状态空间模型](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_run_hierarchical_state_space.py)

依据：

- [完整模型决策 JSON](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/hierarchical_state_space/decision.json)
- [逐 transition 预测](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/hierarchical_state_space/state_space_predictions.csv)

决策文件当前哈希：

```
a71e2c87068fc400e12b6e200a6d34c4719545b71819f6f52cdf82650353ecce
```

由于后来二维配准未通过，这里的长度负结论仍然有效，但二维位置和新增几何指标只能作为历史诊断，不能用来授权二维预测。

## 5. 交通、结构、FWD富集输入消融

我们针对30个完整输入 transition，固定同一个 Bayesian Student-t 模型，只依次增加输入：

- B0：persistence；
- M0：geometry + climate；
- M1：再加 traffic；
- M2：再加 structure；
- M3：再加 source-prior FWD。

主要 LOSO 结果：

| 模型        | MAE      |
| ----------- | -------- |
| Persistence | 4.2402 m |
| M0          | 4.3888 m |
| M1          | 4.4073 m |
| M2          | 4.4133 m |
| M3          | 4.4154 m |

完整 M3 相对 persistence 恶化 `4.132%`，只有 `3/6` 路段改善。所有28个正式拟合通过采样诊断，说明是科学假设未通过，不是采样器崩溃。

代码：

- [输入冻结](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_build_enriched_input_freeze.py)
- [prior predictive](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_run_enriched_prior_predictive.py)
- [posterior runner](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_run_enriched_posterior.py)
- [oracle诊断](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_run_enriched_oracle.py)

依据：

- [正式结果文档](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/experiments/ltpp_geoforecast_enriched_input_posterior_result_20260806.md)
- [研究 track](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/experiments/ltpp_geoforecast_enriched_input_track.md)
- [冻结 evaluation](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_enriched_posterior_v1_20260806/primary_fit/sealed_evaluation.json)
- [冻结逐行预测](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_enriched_posterior_v1_20260806/primary_fit/sealed_predictions.csv)
- [采样诊断](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_enriched_posterior_v1_20260806/primary_fit/sampler_diagnostics.json)

当前 evaluation 哈希：

```
f3a18f4fc9bdd186da8d1e42fad44d688030e5569f17f36a720f76e53e26c6d2
```

## 6. 单因素 ESAL 实验

因为你不希望一次加入气候、水分、荷载等很多因素，我们另外做了单一荷载通道：

- G：当前裂缝长度、面积、预测时长；
- G+L：只增加年度 ESAL。

结果：

- G MAE：`4.4832 m`；
- G+L MAE：`4.5001 m`；
- 增加 ESAL 后恶化 `0.376%`；
- 只有 `2/6` 路段改善。

这是一个有效的单因素负结果：当前29个 transition 中，这个年度 ESAL 表达没有稳定增量价值，但不能推出交通荷载在物理上不重要。

代码：

- [输入预检](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_build_load_only_input_preflight.py)
- [posterior runner](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_run_load_only_posterior.py)

依据：

- [正式结果](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/experiments/ltpp_geoforecast_load_only_posterior_result_20260806.md)
- [完整研究 track](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/experiments/ltpp_geoforecast_load_only_incremental_track_20260806.md)
- [冻结 evaluation](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_load_only_posterior_v1_20260806/sealed_evaluation.json)
- [逐行预测](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_load_only_posterior_v1_20260806/sealed_predictions.csv)

当前 evaluation 哈希：

```
c0f0d2006661b514e332c3446fa8257f536d69010006fd8e8dd2998cb7d4ba03
```

## 7. 维修和自然发展区间审核

我们检查了这31个 transition 是否位于同一个 construction episode、是否存在已记录维修，以及是否跨越 Out-of-Study。

结果：

- 31/31 保持同一 construction；
- 31/31 没发现已记录的维修/reset；
- 30/31 不跨 terminal censoring；
- 唯一例外是 `06-1253-T07`：2007→2012，跨过2011-06-01的 Out-of-Study。

因此可以说“没有发现已记录维修”，但不能说“绝对没有未记录维修”。

代码入口：

- [事件时间线生成](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_build_section_event_ledger.py)

依据：

- [自然发展 episode 审核](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/experiments/ltpp_geoforecast_natural_episode_audit_20260806.md)
- [机器审核 JSON](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_natural_evolution_episode_audit_v1_20260806/episode_audit.json)

## 8. 从原始扫描图自动识别裂缝

我们用最终裁决标签作为当前地图识别的参考，测试了两个方法。

B0确定性图像方法：

- precision：`0.3919`
- recall：`0.1143`
- mean map F1：`0.2739`

B1 Tiny U-Net：

- precision：`0.2025`
- recall：`0.7639`
- mean map F1：`0.2689`
- 4个路段未达到 recall 门槛。

B1虽然召回提高，但把大量网格、表格结构等误识别为裂缝，因此整体仍失败。

代码：

- [识别预检](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_audit_crack_recognition_preflight.py)
- [B0](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_run_crack_recognition_b0.py)
- [B1 Tiny U-Net](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_run_crack_recognition_b1.py)

依据：

- [识别研究 track](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/experiments/ltpp_geoforecast_crack_recognition_track.md)
- [B0结果](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/experiments/ltpp_geoforecast_crack_recognition_b0_result_20260806.md)
- [B1结果](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/experiments/ltpp_geoforecast_crack_recognition_b1_result_20260807.md)
- [B0原始指标](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_b0_v1_20260806/b0_metrics.json)
- [B1原始指标](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_b1_v1_20260807/b1_metrics.json)

两份指标文件的当前哈希分别为：

- B0：`e4757d61011ad151e7e2fcec03b917f5ee01658e8f4bf70b5ec66c86dacdc1e9`
- B1：`7d9ae5bca02a37fa2db1cc533225532d75bc477f89c8242d8f661da7df3ea242`

## 9. 跨日期空间配准

我们审计了06-1253的8个日期能否进入二维裂缝位置预测。

正式 v1 结果：

- 只有1998和2012通过；
- 1995、2001、2007控制点不足；
- 1991、1997、2003误差超标；
- 总体 `2/8`，二维路线关闭。

后续探索性 MVP 已经能够把8张图渲染到统一画布，但没有独立物理控制点。尤其1995年的全部官方页面都缺少可靠纵向网格参照，因此仍不能证明物理配准正确。

代码：

- [正式配准审计](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_audit_spatial_registration.py)
- [配准 MVP](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_run_spatial_registration_mvp.py)
- [网格诊断](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_run_exploratory_grid_registration_mvp.py)

依据：

- [配准研究 track](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/experiments/ltpp_geoforecast_spatial_registration_track.md)
- [正式 v1 结果](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/experiments/ltpp_geoforecast_spatial_registration_audit_v1_result_20260806.md)
- [正式 audit JSON](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_spatial_registration_audit_v1_20260806/audit_result.json)
- [后续非损伤配准 MVP](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/experiments/ltpp_geoforecast_non_damage_registration_mvp_result_20260807.md)

正式 audit 当前哈希：

```
925ceeaa7dd86a7b457067544f162ecdc7492a0ce95a974c859046c88d5b7666
```

## 10. 一个较早的单路段实验

在最终37张双盲裁决数据完成前，我们还用06-1253早期单人标注做过不可逆隐状态实验。

结果：

- 相对 persistence 的中位 bMAE 改善 `7.57%`；
- 低于预设 `10%` 门槛；
- 一折区间覆盖率也未通过；
- 最终 `FAIL_L_NOT_QUALIFIED`。

这只是历史诊断，不是最终多路段基准，也不应与后来的裁决数据实验混在一起。

依据：

- [早期实验记录](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/experiments/ltpp_06_1253_observation_state_gate_v1_20260805.md)
- [原始结果](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_observation_state_gate_v1_20260805/result.json)

## 当前最重要的证据边界

我们现在可以严谨地说：

> 已经建立了六路段、37状态、31时序转移的人工裁决 LTPP 小样本基准；在严格未见路段验证下，现有状态空间、富集输入和单一 ESAL 模型都没有稳定超过简单基准。

不能说：

- 已经能够预测裂缝空间位置；
- 交通、结构或FWD在物理上不重要；
- 自动识别已经能替代人工；
- 这些手绘裂缝就是现场物理真值；
- 结果可以推广到整个 LTPP。

## 当前归档缺口

我还发现一个需要处理的问题：

- enriched-input、load-only、时间线和正式配准代码已经进入 Git；
- 但部分标注流水线、基础模型、状态空间和识别代码/文档目前仍显示为 **untracked**；
- 大型原始结果位于 `local_archive`，这是设计如此，但关键代码和紧凑证据文档不应长期只留在本机。

所以现在是“本机数据和哈希证据完整”，但“GitHub跨机器归档尚不完整”。下一步最合理的是先做一次只包含 LTPP 代码、测试、实验文档和 manifest 的干净归档提交，不碰工作区其他研究改动。
