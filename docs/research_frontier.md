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

PIDL pure-physics 在 OOD Umax (>0.12) 上是否保持准确的 N_f 预测？（§4.6 泛化验证）

## Active Branches

1. **OOD clean rerun** — u=0.11/0.13/0.14 干净重跑（Taobo GPU1+GPU7 进行中）→ status: waiting for results → next: 收到结果后更新 cross-Umax table，确认/否定 u=0.14 anomaly
2. **u=0.14 anomaly diagnosis** — N_f=127 已 retracted（resume artifact），但真实 u=0.14 行为待定 → status: blocked on clean rerun → next: 多 seed 结果到手后判断是否存在 multimodality
3. **Phase 2 PCC concrete** — FEM smoke 已完成（α_T placeholder 导致 N_f≫10⁵）→ status: blocked on Holmen 1982 α_T calibration → next: 拿到 SP-75 PDF 后做 digitization + recalibrate

## Current Best Bet

**OOD 边界已确定**：Umax ≤ 0.13 可靠（≤+7% vs FEM，低 seed 方差）；Umax = 0.14 系统性低估 −24%（mean），std=4.2，超出可靠范围。Switch condition 已触发。

## Best Next Discriminator

u=0.13 多 seed（Windows 在跑）→ 确认 u=0.13 方差低（如预期） → OOD 结论最终锁定。

## Switch Condition

~~如果 u=0.14 clean rerun 显示 N_f 合理（monotone 且误差 <20%），OOD 验证关闭~~

**TRIGGERED 2026-05-05**：u=0.14 5-seed 显示系统性低估 −24% + 高方差。OOD 验证完成，主线切到 **Phase 2 concrete**（等 u=0.13 multi-seed 收口后正式关闭 Branch 1）。

## Parking Lot

- Oracle vs pure-physics systematic drift (+7% at high Umax) 的物理解释
- α-3 follow-up (from `9f2ac69`)
- Phase 2B beam/slab geometry
- PIDL retraining at concrete units (Phase 2.5+)

## Recently Closed / Triggered

- **OOD boundary CONFIRMED 2026-05-05**: Umax ≤ 0.13 reliable; 0.14 = systematic −24% bias + high variance → Branch 1 switch triggered
- u=0.12 seed=1/2/3: N_f=82 all three, zero variance (deterministic at training Umax)
- u=0.14 N_f=127: RETRACTED, resume artifact (詳 shared_research_log 2026-05-05)
- run_baseline_umax.py bug: FIXED commit 6040cbb + guard 427ebe7 (2026-05-04)
