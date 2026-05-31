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

**如何把 road-DT/M2S framework 做成可信验证，同时不掩盖 PIDL forward field mismatch？**

## Active Branches

1. **Representation-localization discriminator** (ACTIVE 5/30) — Sampling/refinement/loss/irreversibility did not close the field gap. Tip-local MLP/Fourier/SIREN Exp18, strict head-staging, and additive one-patch local correction change `N_f`/scalar metrics but leave the local driver/history mechanism broken. Current clean test is an FBPINN-style chain: several overlapping local subdomain nets blended by partition weights, so local nets carry the raw field inside process-zone windows. Artifacts: `docs/local_patch_discriminator_2026-05-30.md`, `docs/fbpinn_chain_discriminator_2026-05-30.md`.
2. **M2S framework validation** (ACTIVE 5/31) — First synthetic FEM-truth rung is complete: c1-c69 soft-hist0 FEM predicts RUL from figure/damage observations with sub-cycle MAE, but this is a single-trajectory observability test, not hidden-field value proof. Next rung must be multi-trajectory holdout. Artifact: `docs/m2s_framework_validation_2026-05-31.md`.
3. **Phase 2A units-transition smoke** (passive) — `run_pcc_baseline_umax.py` remains a PCC scaling/infrastructure check only, not a Baktheer `N_f` anchor. Mac now has PCC v3 trajectory under GRIPHFiTH; Taobo sync still needed before supervised PCC diagnostics.

## Current Best Bet

Field mismatch 仍未解决。Soft-hist0/state-timing audit fixed the first-cycle bookkeeping trap: FEM c1 maps best to PIDL j0. Request 21 cadence controls show FEM with unload retained fractures at c69-c70 for n_step=2/3/standard/10, while peak-only is the outlier (>c120); hydrated field reductions confirm n_step=10 is effectively identical to standard at c69. New tiered common-probe comparison confirms FEM-mesh PIDL has the same late gap against standard and n_step10 references: fixed c69 `alpha_bar` tip2 ≈0.47x/0.37x FEM, active `psi_plus` tip2 ≈0.029x/0.023x FEM, and `Delta E_d` ≈0.25x FEM. Matched-event PIDL j84/j85 does not rescue it: damage tip2 stays ≈1.01-1.03x FEM and raw `psi+` tip2 is ≈1.4-1.65x FEM, but active `psi+` tip2 collapses to ≈0.005x FEM. LBFGS polish on j68/j84/j85 cuts gradient norm to 0.15-0.46x but leaves active `psi+`, damage, and `E_d` unchanged. Strict FEM-mesh head-staging also fails. A strict FEM-mesh inverse `alpha_T` retry against the latest soft-hist0 FEM target is now closed as an identifiability failure: `alpha_T` collapses to 0.05, PIDL fractures at j14 vs FEM c69, and raw/active diagnostics show raw `psi+` tip2 is 4-8x FEM while active `g(alpha)psi+` remains 0.06-0.26x FEM. Substep count/reference choice/cycle timing/final optimiser polish/head-staging/scalar `alpha_T` calibration are not the culprit; the local degraded active-driver/history feedback is.

## Best Next Discriminator

For forward PIDL, run one stronger representation-local discriminator with the field-level gate defined first. Metric plan/results started in `docs/field_level_comparison_metric_plan.md`, `docs/field_level_metric_results_2026-05-28.md`, `docs/aligned_fem_pidl_reference_tiers_2026-05-30.md`, `docs/staged_alpha_discriminator_2026-05-30.md`, `docs/local_patch_discriminator_2026-05-30.md`, `docs/fbpinn_chain_discriminator_2026-05-30.md`, and `docs/inverse_problem_experiments_2026-05-31.md`; element/nodal definitions are pinned in `docs/fem_pidl_element_nodal_definitions_2026-05-28.md`. For framework validation, the next meaningful step is a multi-trajectory FEM benchmark with holdout splits; the current single-trajectory M2S result proves feasibility, not hidden-state superiority.

## Switch Condition

If a representation-local method improves FEM field alignment near the tip without worsening V7/reaction, promote to N100. If it only shifts N_f or ᾱ_max while the α/ψ fields remain centerline-like, close it as another scalar-metric fix.

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
