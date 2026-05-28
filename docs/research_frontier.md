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

**Field-level mismatch 是否需要更强的 discontinuity/domain-decomposition representation，而不是小型 tip-local heads？**

## Active Branches

1. **Representation-localization discriminator** (ACTIVE 5/28) — Sampling/refinement/loss/irreversibility did not close the field gap. Tip-local MLP/Fourier/SIREN Exp18 also changes `N_f`/scalar metrics but leaves alpha fields as coherent centerline/right-boundary, boundary-saturating paths. Next clean discriminator should be stronger: SDF/discontinuity embedding or FBPINN/domain-decomposed tip patch, not another small local head sweep.
2. **Phase 2A units-transition smoke** (passive) — `run_pcc_baseline_umax.py` remains a PCC scaling/infrastructure check only, not a Baktheer `N_f` anchor. Mac now has PCC v3 trajectory under GRIPHFiTH; Taobo sync still needed before supervised PCC diagnostics.
3. **§5 paper plan** (passive, locked 5/14) — §5 改成依赖 Wu 2017 + Baktheer 2024 出版引用，BFGS port 推到 post-paper。任何 §5 wording 不再 quote "N_f ≈ 1500-2500"（已 retract via inbox `4124444`）。

## Current Best Bet

Field mismatch 仍未解决。Adaptive/refinement/hard-irreversibility failed to recover FEM-like fields. Tip-local Exp18 completed enough to decide: first hit `N≈75-81`, confirmed stop `N≈78-84`, `alpha_bar_max≈6.6-11.3`, but montage vs reverseBC FEM still shows coherent centerline/right-boundary, boundary-saturating paths. This should not be read as a measured claim that the PIDL high-alpha core is always narrower than FEM. Small local correction heads are not the missing representation.

## Best Next Discriminator

Run one stronger representation-local discriminator with the field-level gate defined first. Metric plan/results started in `docs/field_level_comparison_metric_plan.md` and `docs/field_level_metric_results_2026-05-28.md`. For the current evidence base, use reverseBC FEM as the primary aligned field-level reference because most PIDL evidence is already organized that way and FEM is cheap to rerun; keep femAnchorBC PIDL as a secondary opposite-direction alignment diagnostic. Audit found that a Heaviside/XFEM jump-head discontinuity branch was already tried and only partially passed, so the cleaner next architecture discriminator is FBPINN/domain-decomposed tip patch unless we deliberately revive the jump-head branch with fixed tip tracking. No broad GPU sweep until the metric is fixed.

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
