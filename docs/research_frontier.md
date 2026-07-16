# Research Frontier

**规则**：此文件是"一屏决策前线"，不是历史日志。
- 总长度 ≤ 50 行（不含本 header）
- Active Branches ≤ 3 个
- Current Question 只能 1 个
- 关闭的分支移到 `shared_research_log.md`，不留在这里
- 如果本 session 改变了主问题，重写前两节

**Owner**: Mac-PIDL | **Update**: 每个 Mac research session 结束时

---

## Current Question

**哪一种现实可测的观测组合，能在不使用相场隐变量标签的情况下，把 FEM/物理模型同化成校准的裂缝几何与 RUL 预测？**

## Active Branches

1. **Reality-facing sequential assimilation** (ACTIVE 7/15) — Implemented a direct-FEM library Bayesian update with explicit `observable` / `synthetic_proxy` / `oracle_only` channels, cumulative sensor tiers, RUL posterior, CRPS/coverage, future crack-tip forecast, right-censored survival support, versioned DIC/strain + AE observation operators with calibrated uncertainty/missingness, registered probability-mask CV ingestion, grouped paired-sensor calibration, posterior recovery of declared FEM/model parameters, and an observation-only probabilistic crack-growth baseline. Real inference rejects synthetic-only or not-independently-approved sensor calibration, constant-parameter holdouts are marked non-identifiable, and every trajectory must share one `physics_family`. With exactly the same tip-only observation, the cadence-only direct-FEM library gives CRPS 0.489 versus 18.9 for a local growth-rate particle model; this shows the value of a complete transition prior but not FEM generalisation because the three FEM trajectories are nearly identical. The current 3-trajectory strict library remains a code gate only: one `Umax`, `N_f=69..70`, 90% coverage 0.67. A deliberately mixed-family U10/U11/U12 stress is automatically quarantined and collapses vision+load coverage to 0.049. No sensor/model claim is promoted. Artifacts: `SENS_tensile/reality_assimilation.py`, `SENS_tensile/observable_growth_baseline.py`, `SENS_tensile/build_vision_observation_table.py`, `SENS_tensile/calibrate_reality_sensor_observation_model.py`, `SENS_tensile/run_reality_assimilation_benchmark.py`, `SENS_tensile/run_reality_assimilation_inference.py`, `docs/reality_assimilation_framework_2026-07-15.md`, local `_analysis_reality_assimilation_20260715/decision.md`.
2. **Hard-recovery c89 field mechanism** (ACTIVE diagnostic 7/16) — PIDL can match FEM `N_f=89` while failing active-driver/process-zone/history co-location. Exact eta0 equilibrium conditioned on the true diffuse c86 FEM damage nearly closes c87 raw and c89 active support, proving a missing-state problem rather than a generic GNN/MLP limitation. A sealed binary crack skeleton plus nominal AT1 reconstruction fails badly despite c86 damage correlation `0.991`: c87 raw log-MAE `5.05`, p99 support area about `100x` FEM. The missing state is the near-core degradation amplitude, not crack location alone. Next gate: infer that amplitude from c86 reaction/global stiffness and sparse mechanics, then lock it before c87/c89. Artifacts: local `analysis/fem_damage_conditioned_equilibrium_20260716/decision.md`, `analysis/fem_visible_crack_equilibrium_20260716/decision.md`.
3. **FEM-surrogate transition operator** (QUARANTINE 7/15) — The current mesh-operator prototype has sound FEM-centred field metrics and recurrent rollout mechanics but only one c1--c89 trajectory with within-trajectory splits, no load/material/precrack/environment conditioning, no calibrated uncertainty, and no trained checkpoint. Code now forces tooling-only/assimilation-ineligible manifests and explicit diagnostic acknowledgement. Do not train/promote it before reviewed multi-trajectory data exist. Artifact: `docs/fem_surrogate_transition_gate_2026-07-15.md`.
4. **Phase 2A units-transition smoke** (passive) — `run_pcc_baseline_umax.py` remains a PCC scaling/infrastructure check only, not a Baktheer `N_f` anchor. Mac now has PCC v3 trajectory under GRIPHFiTH; Taobo sync still needed before supervised PCC diagnostics.

## Current Best Bet

主线改为 observation-first probabilistic digital twin：现实图像/3D/载荷/DIC-strain/AE 通过显式观测模型约束隐状态；FEM、相场、降阶模型、PIDL 和经验疲劳律作为可竞争的 transition models。第一版 direct-FEM sequential assimilation 已跑通，但现有 cadence-only trajectories 太相似且后验欠覆盖，当前最重要的不是换模型，而是建立有物理多样性的严格全场轨迹库并校准现实观测 likelihood。

Transition-model ranking must use one compatible trajectory/observation protocol. Current data-only ridge, direct-FEM, PIDL, and surrogate evidence live on different suites and therefore form an evidence matrix, not a numeric leaderboard; see `docs/reality_transition_model_evidence_matrix_2026-07-15.md`. Direct FEM remains the primary reference implementation, the single-trajectory surrogate is quarantined, and an empirical fatigue law remains a required future baseline after load/failure semantics are locked.

For the current c89 mismatch, the immediate discriminator is c86-only observable-stiffness-constrained degradation inversion. A binary crack mask is insufficient even when its damage correlation is high; the inferred field must reproduce the observed reaction/global stiffness before any future-cycle target is opened.

The trajectory library is now source-agnostic: `source_kind=observation_csv` loads completed `reality_obs_v1` laboratory/road histories as empirical transition candidates with the same censoring, posterior, and holdout metrics. This is the main non-FEM path: use real historical evolution directly when enough compatible assets exist, rather than reconstructing phase-field hidden labels.

## Best Next Discriminator

Before any laboratory campaign or new surrogate training, obtain an externally reviewed minimal FEM design varying physical load spectrum, fatigue/material parameters, precrack severity, one environment proxy, and censored outcomes. Export full fields only for oracle audit; construct deployable inputs through locked vision/load/DIC-strain/AE observation operators. Repeat the same leave-one-physical-trajectory-out CRPS, 90% coverage/width, and future crack-tip gate. Numerical cadence does not count as physical diversity.

## Switch Condition

Promote a sensor tier to a laboratory test only if it beats `vision_plus_load` on held-out physical trajectories in CRPS and future crack-tip MAE, retains calibrated coverage under noise/missingness, and contains no oracle-only state. Promote PIDL/surrogate over direct FEM only if the same locked observation and uncertainty gates improve—not merely runtime or scalar `N_f`.

## Parking Lot

- A1+Strac combo N=300 production (~18 GPU-days, 暂不做)
- Hard y² 架构 production (12× slowdown, 暂不做)
- Multi-seed combo smoke (N=5 × 2 more seeds, ~14h Windows, P3 优先级)
- Phase 2A ψ_per_cycle vs PCC v3 trajectory comparison (等 Taobo/PIDL result + trajectory sync)
- True residual-adaptive collocation sampler, detached from objective weights

## Recently Closed / Triggered

- **§5 plan retracted+reframed 2026-05-14**: Request 12 Wu PF-CZM PCC v3 3000-cycle run **null result** (d_max=0.0037, no fracture); d-localization fails under monolithic Newton (NtN vs BtB 5-6 OOM mismatch); BFGS port deferred to post-paper. §5 改成依赖 Wu 2017 + Baktheer 2024 出版引用。inbox `4124444` 正式 retract "N_f ≈ 1500-2500" 数字。
- **Phase 2A infrastructure shipped 2026-05-14**: `source/scaling.py` (PCC↔non-dim Buckingham π) + `run_pcc_baseline_umax.py` (Phase 2A units-transition runner) committed (`fd4d944`, `8134163`). External expert P0 fix: `w1_norm = w1_phys/ψ_char` not `/σ_char` (was 775× wrong, would have artificially favored crack growth). α_T_norm=100 vs toy 0.5.
- **Phase 1 §4 v1.6 lock 2026-05-10**: 三轮 red-team 全部应用 → §4.2 完整 V4+V7 14-method 表。Memory: `finding_v4_v7_cross_method_may10.md`.
- **References Wu 2026 + Wu 2024 + Baktheer 2024 read 2026-05-10**: 选 PF²-CZM associated (ξ=2) for Phase 2 concrete。
- **Adaptive sampling/refinement/hard-irreversibility diagnostics 2026-05-25**: baseline/v4 adaptive `lambda_hist` fractured but did not close field mismatch; hard irreversibility no-fracture by c99 with huge ᾱ; v4 add-only refinement useful as bookkeeping, not field closure.
- **Tip-local Exp18 2026-05-28**: MLP/Fourier/SIREN × S1/S2/output-mode matrix mostly confirmed fracture around `N=75-84`, but final α fields remain coherent centerline/right-boundary paths rather than FEM-like process-zone envelopes. Artifacts: `docs/tiplocal_exp18_summary_2026-05-28.md` and `docs/figures/tiplocal_exp18_20260528/`.
- **Head-staging discriminator 2026-05-30**: strict FEM-mesh output-head schedules (`uv->alpha->joint`, alpha-only, uv-only, no-joint) closed as negative/diagnostic. Joint-solve variants do not improve local `alpha_bar`/active `psi+`; no-joint accumulates large nonpropagating history. Artifact: `docs/staged_alpha_discriminator_2026-05-30.md`.
