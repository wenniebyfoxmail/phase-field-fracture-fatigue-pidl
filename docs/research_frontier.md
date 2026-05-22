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

**Phase 1 controlled alignment variants 能否区分 stop-rule / irreversibility / cycle-abstraction mismatch，还是主要差距仍是 localization capacity？**

## Active Branches

1. **Controlled alignment variants (Phase 1)** (ACTIVE 5/19) — Variant 2 posthoc criterion audit implemented: baseline `u=0.12` crossed criteria give PIDL first hit N=80 vs FEM snapshot N=82, so detector mismatch is small. Variant 3 (`tol_ir=1e-3`, N=100), Variant 4 (explicit cycle, N=5 physical cycles / 25 substeps), and Variant 5 (GRIPHFiTH-style bottom-left `u_x` anchor, N=120) are running on Taobo GPU 2/3/4.
2. **Phase 2A units-transition smoke** (passive) — `run_pcc_baseline_umax.py` remains a PCC scaling/infrastructure check only, not a Baktheer `N_f` anchor. Mac now has PCC v3 trajectory under GRIPHFiTH; Taobo sync still needed before supervised PCC diagnostics.
3. **§5 paper plan** (passive, locked 5/14) — §5 改成依赖 Wu 2017 + Baktheer 2024 出版引用，BFGS port 推到 post-paper。任何 §5 wording 不再 quote "N_f ≈ 1500-2500"（已 retract via inbox `4124444`）。

## Current Best Bet

Phase 1 的 stop-rule mismatch 不是主因。FEM-anchor BC 明显降低 V7-global residual 并把 first-hit 从 baseline `~80` 推到 `93`，所以 essential BC 是真实 trajectory factor；但 tip-zone `psi+` 只提升约 `2-2.5x`，仍差 FEM many OOM。Symmetry 对照也支持这个判断：FEM fair V4 reference 是 exact-pair `2.98e-5`，而 PIDL fem-anchor BC 在 c82 full/right-band/corridor relative RMS 分别约 `4.7e-2 / 5.9e-2 / 1.5e-1`。主叙事仍应压在 representation/localization capacity。

## Best Next Discriminator

Read remaining `tol_ir=1e-3` Taobo run when it finishes. For completed FEM-anchor BC, use `alignment_compare_baseline_vs_femAnchorBC.csv` plus `femAnchorBC_alpha_symmetry_audit.csv`: V7-global improves strongly, reaction early-cycle improves, but local `psi+` and mirror symmetry remain bottlenecks.

## Switch Condition

若 Variant 3 或 4 让 first-hit / `alpha_bar_max` 移动 >10% 且 V4/V7 不恶化 → promote to N=100/N=300; 若变化 <5% → close as non-dominant alignment factor.

## Parking Lot

- A1+Strac combo N=300 production (~18 GPU-days, 暂不做)
- Hard y² 架构 production (12× slowdown, 暂不做)
- Multi-seed combo smoke (N=5 × 2 more seeds, ~14h Windows, P3 优先级)
- Phase 2A ψ_per_cycle vs PCC v3 trajectory comparison (等 Taobo/PIDL result + trajectory sync)
- §4 v1.6 commit/push (drafts 不进 git，只复制到 obsidian — 已完成)
- 论文 §5 / Phase 2 章节正文写作 (等 PCC smoke 数字回来再写)
- **Local spectral tip patch (SIREN, uv-only)** — design + skeleton at `.claude/worktrees/local-spectral-tip-patch/docs/branch_tip_local_spectral.md`. **Gate**: SDF/DENN N=5 smoke result; if SDF closes gap → skip; if SDF partial/fail → launch. No GPU until SDF gate clears. Spec is decoupled: no SDF / no C4 / no Fourier / no α-patch / no adaptive-sampling.

## Recently Closed / Triggered

- **§5 plan retracted+reframed 2026-05-14**: Request 12 Wu PF-CZM PCC v3 3000-cycle run **null result** (d_max=0.0037, no fracture); d-localization fails under monolithic Newton (NtN vs BtB 5-6 OOM mismatch); BFGS port deferred to post-paper. §5 改成依赖 Wu 2017 + Baktheer 2024 出版引用。inbox `4124444` 正式 retract "N_f ≈ 1500-2500" 数字。
- **Phase 2A infrastructure shipped 2026-05-14**: `source/scaling.py` (PCC↔non-dim Buckingham π) + `run_pcc_baseline_umax.py` (Phase 2A units-transition runner) committed (`fd4d944`, `8134163`). External expert P0 fix: `w1_norm = w1_phys/ψ_char` not `/σ_char` (was 775× wrong, would have artificially favored crack growth). α_T_norm=100 vs toy 0.5.
- **Phase 1 §4 v1.6 lock 2026-05-10**: 三轮 red-team 全部应用 → §4.2 完整 V4+V7 14-method 表。Memory: `finding_v4_v7_cross_method_may10.md`.
- **References Wu 2026 + Wu 2024 + Baktheer 2024 read 2026-05-10**: 选 PF²-CZM associated (ξ=2) for Phase 2 concrete。
