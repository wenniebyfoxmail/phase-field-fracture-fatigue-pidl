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

**PIDL 在 reverseBC synthetic inverse problem 中能否识别 `alpha_T`，而不是用参数偏差补偿 field-level mismatch？**

## Active Branches

1. **Inverse-alphaT discriminator** (ACTIVE 5/28) — Use reverseBC FEM synthetic observations and fixed PIDL `E_irrev` weighting. FEM baseline is an outer-loop `alpha_T` grid; PIDL baseline is joint optimization of NN weights + positive trainable `alpha_T`.
2. **Representation-localization discriminator** (parked) — Tip-local/SDF methods remain the forward-problem closure path, but this branch asks whether inverse calibration exposes or compensates the same mismatch.
3. **Phase 2A units-transition smoke** (passive) — `run_pcc_baseline_umax.py` remains a PCC scaling/infrastructure check only, not a Baktheer `N_f` anchor.

## Current Best Bet

FEM 当然可以通过 outer-loop optimization 解 inverse problem；本 branch 不用 “FEM 不能 inverse” 作为 claim。第一轮公平比较：FEM 每个 `alpha_T` candidate 重跑 forward；PIDL 在同一个 differentiable training loop 中学习 NN field + `alpha_T`。PIDL 只算成功物理识别，若 recovered `alpha_T≈0.5` 且 field/trajectory 不恶化。

## Best Next Discriminator

Run `SENS_tensile/fem_inverse_alphaT_grid.py` for the FEM manifest, then producer-side PIDL smoke with `run_inverse_alphaT_reversebc_umax.py 0.12 --alphaT-init 0.25 --fem-dir <reverseBC handoff>`. Do not run the training loop on Mac.

## Switch Condition

If PIDL improves observation loss or `N_f` using a biased `alpha_T`, classify as model-error compensation, not successful inverse identification. If fixed-`E_irrev` PIDL recovers `alpha_T≈0.5`, then test high-init and adaptive-`E_irrev` ablations.

## Parking Lot

- A1+Strac combo N=300 production (~18 GPU-days, 暂不做)
- Hard y² 架构 production (12× slowdown, 暂不做)
- Multi-seed combo smoke (N=5 × 2 more seeds, ~14h Windows, P3 优先级)
- Phase 2A ψ_per_cycle vs PCC v3 trajectory comparison (等 Taobo/PIDL result + trajectory sync)
- True residual-adaptive collocation sampler, detached from the objective weights
- Adaptive `E_irrev` inverse ablation after fixed-`E_irrev` baseline

## Recently Closed / Triggered

- **§5 plan retracted+reframed 2026-05-14**: Request 12 Wu PF-CZM PCC v3 3000-cycle run **null result** (d_max=0.0037, no fracture); d-localization fails under monolithic Newton (NtN vs BtB 5-6 OOM mismatch); BFGS port deferred to post-paper. §5 改成依赖 Wu 2017 + Baktheer 2024 出版引用。inbox `4124444` 正式 retract "N_f ≈ 1500-2500" 数字。
- **Phase 2A infrastructure shipped 2026-05-14**: `source/scaling.py` (PCC↔non-dim Buckingham π) + `run_pcc_baseline_umax.py` (Phase 2A units-transition runner) committed (`fd4d944`, `8134163`). External expert P0 fix: `w1_norm = w1_phys/ψ_char` not `/σ_char` (was 775× wrong, would have artificially favored crack growth). α_T_norm=100 vs toy 0.5.
- **Phase 1 §4 v1.6 lock 2026-05-10**: 三轮 red-team 全部应用 → §4.2 完整 V4+V7 14-method 表。Memory: `finding_v4_v7_cross_method_may10.md`.
- **References Wu 2026 + Wu 2024 + Baktheer 2024 read 2026-05-10**: 选 PF²-CZM associated (ξ=2) for Phase 2 concrete。
- **Adaptive sampling/refinement/hard-irreversibility diagnostics 2026-05-25**: baseline/v4 adaptive `lambda_hist` fractured but did not close field mismatch; hard irreversibility no-fracture by c99 with huge ᾱ; v4 add-only refinement useful as bookkeeping, not field closure.
