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

**Field-level mismatch 是否还能靠 sampling/refinement/loss/irreversibility 修掉，还是必须转向 representation-localization？**

## Active Branches

1. **Representation-localization discriminator** (ACTIVE 5/25) — Sampling/refinement/loss/irreversibility diagnostics did not close the field gap. Next clean discriminator should be a representation-local method: separate tip-local SIREN/FBPINN patch or SDF/discontinuity embedding. Do not mix it with adaptive loss weighting in the first test.
2. **Phase 2A units-transition smoke** (passive) — `run_pcc_baseline_umax.py` remains a PCC scaling/infrastructure check only, not a Baktheer `N_f` anchor. Mac now has PCC v3 trajectory under GRIPHFiTH; Taobo sync still needed before supervised PCC diagnostics.
3. **§5 paper plan** (passive, locked 5/14) — §5 改成依赖 Wu 2017 + Baktheer 2024 出版引用，BFGS port 推到 post-paper。任何 §5 wording 不再 quote "N_f ≈ 1500-2500"（已 retract via inbox `4124444`）。

## Current Best Bet

Field mismatch 仍未解决。Adaptive `lambda_hist` baseline/v4 N100 都断裂（baseline c82→c92 confirm, v4 c80→c90 confirm），但 late logs 显示 `hist_grad=0`、`lambda_hist=1.0`，并未形成真正的 loss balancing。v4 add-only refinement 去掉了 repeated rebuild/transport，但 α field 仍是 thin centerline-like，不是 FEM-like tip localization。Hard irreversibility sigmoid floor 避免 NaN，却在 c99 仍无 fracture，ᾱ_max≈75-76 而 `α_max@bdy=0`。结论：sampling/refinement/constraint bookkeeping 有用，但主瓶颈仍是 representation/localization。

## Best Next Discriminator

Run one clean representation-local discriminator, preferably separate tip-local SIREN/FBPINN patch or SDF/discontinuity embedding, with baseline loss unchanged and no adaptive `lambda_hist` in the first pass. Gate by field-level comparison to reverseBC FEM, not only fracture cycle.

## Switch Condition

If a representation-local method improves FEM field alignment near the tip without worsening V7/reaction, promote to N100. If it only shifts N_f or ᾱ_max while the α/ψ fields remain centerline-like, close it as another scalar-metric fix.

## Parking Lot

- A1+Strac combo N=300 production (~18 GPU-days, 暂不做)
- Hard y² 架构 production (12× slowdown, 暂不做)
- Multi-seed combo smoke (N=5 × 2 more seeds, ~14h Windows, P3 优先级)
- Phase 2A ψ_per_cycle vs PCC v3 trajectory comparison (等 Taobo/PIDL result + trajectory sync)
- True residual-adaptive collocation sampler, detached from the objective weights

## Recently Closed / Triggered

- **§5 plan retracted+reframed 2026-05-14**: Request 12 Wu PF-CZM PCC v3 3000-cycle run **null result** (d_max=0.0037, no fracture); d-localization fails under monolithic Newton (NtN vs BtB 5-6 OOM mismatch); BFGS port deferred to post-paper. §5 改成依赖 Wu 2017 + Baktheer 2024 出版引用。inbox `4124444` 正式 retract "N_f ≈ 1500-2500" 数字。
- **Phase 2A infrastructure shipped 2026-05-14**: `source/scaling.py` (PCC↔non-dim Buckingham π) + `run_pcc_baseline_umax.py` (Phase 2A units-transition runner) committed (`fd4d944`, `8134163`). External expert P0 fix: `w1_norm = w1_phys/ψ_char` not `/σ_char` (was 775× wrong, would have artificially favored crack growth). α_T_norm=100 vs toy 0.5.
- **Phase 1 §4 v1.6 lock 2026-05-10**: 三轮 red-team 全部应用 → §4.2 完整 V4+V7 14-method 表。Memory: `finding_v4_v7_cross_method_may10.md`.
- **References Wu 2026 + Wu 2024 + Baktheer 2024 read 2026-05-10**: 选 PF²-CZM associated (ξ=2) for Phase 2 concrete。
- **Adaptive sampling/refinement/hard-irreversibility diagnostics 2026-05-25**: baseline/v4 adaptive `lambda_hist` fractured but did not close field mismatch; hard irreversibility no-fracture by c99 with huge ᾱ; v4 add-only refinement useful as bookkeeping, not field closure.
