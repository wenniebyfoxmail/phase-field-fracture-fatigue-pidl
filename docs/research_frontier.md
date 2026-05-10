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

**Phase 2.1: 给 PCC concrete (E~30GPa, ν~0.18, ℓ~2 mm, G_f~100 J/m²) 反推一个物理可解释的 α_T，解锁 Windows-FEM Task C 的 PCC PF-CZM smoke。**

## Active Branches

1. **α_T calibration for PCC** — Baktheer 2024 公式 α_T = G_f / (k_f · ℓ) 已确立，k_f=0.01 是混凝土标准值。当前 session 用具体 PCC 数字算出 α_T，cross-check 与 Holmen 1979 / ACI 215R 的 S-N 曲线趋势是否一致。Deliverable: α_T 数字 + memory entry + Windows-FEM inbox unblock Task C。
2. **Phase 2 framework decision (2A vs 2B)** — Wu 2026 IJDM unified review 已读完，结论是 PF²-CZM (associated, ξ=2, α=2d−d²) 是混凝土单调凸软化的标准；μPF-CZM 仅当凹形软化 (沥青) 时必要。Phase 2A = Carrara extended (low effort)；Phase 2B = Wu PF-CZM (kernel rewrite, high effort)。Baktheer 2024 给的就是 2B blueprint (PF-CZM + Carrara fatigue + Macaulay split)。决策：2A 先做小工作量过渡，2B 在 Phase 3 升级。
3. **Phase 1 §4 v1.6 LOCK** (passive) — 三轮 red-team 全部应用，hedging 完整。不再加新实验。备份 obsidian + commit by user discretion.

## Current Best Bet

Phase 2 走 **2A (Carrara extended at PCC concrete units)**：动 config.py 物理参数 + α_T 反推，FEM kernel 不动。论文 §5 / Phase 2 章节定位为 "framework transition demonstration"，不是 Wu PF-CZM 完整实现。

## Best Next Discriminator

α_T = G_f / (k_f · ℓ) 反推后，Windows-FEM 跑一个 PCC smoke (S^max=0.75, expect N_f ~ 10³-10⁴ for reasonable HCF) → 若 N_f 落在合理 HCF 区间 = α_T 校准成功；否则迭代 k_f 或重审 fib MC 2010 数据。

## Switch Condition

如果 α_T 反推出的 PCC smoke N_f << 10² 或 >> 10⁶ → 说明 k_f=0.01 不能直接平移到 PCC concrete (Baktheer 用 C60 高强混凝土，PCC 是普通混凝土)，需要从 Holmen S-N 数据点反推一个 PCC-specific k_f。

## Parking Lot

- A1+Strac combo N=300 production (~18 GPU-days, 暂不做)
- Hard y² 架构 production (12× slowdown, 暂不做)
- Multi-seed combo smoke (N=5 × 2 more seeds, ~14h Windows, P3 优先级)
- §4 v1.6 commit/push (drafts 不进 git，只复制到 obsidian — 已完成)
- 论文 §5 / Phase 2 章节正文写作 (等 PCC smoke 数字回来再写)

## Recently Closed / Triggered

- **Phase 1 §4 v1.6 lock 2026-05-10**: 三轮 red-team 全部应用 → §4.2 包含完整 V4+V7 14-method 表 + targeted-supervised reframe + 13 PIDL configs + falsifiable prediction (V4 ≥5× reduction relative to 0.07 baseline)。Backup at `obsidian/01 PINN/paper1/section4_v1.6_2026-05-10.md`. Memory: `finding_v4_v7_cross_method_may10.md`.
- **Strac-alone V7 confirmed FAIL 2026-05-10**: Taobo seed1 N=300 cycle 87, V7=138% (FAIL). Bimodal as Phase F smoke predicted. 不再尝试 Strac-only path，combo (Sym+A1+Strac) 是唯一 V7 改进路径。
- **A1+Strac combo Phase C 2026-05-09 done**: 5-cycle smoke V4=0 (by construction) + V7=15.8% (WARN range)。Multi-seed combo + N=300 production 暂不做（compute-prohibitive，18 GPU-days/seed）。
- **References Wu 2026 + Wu 2024 + Baktheer 2024 read 2026-05-10**: 选 PF²-CZM associated (ξ=2) for Phase 2 concrete。
- **FEM-9 dispatched 2026-05-09 + scope Q&A 2026-05-10**: A→B→F→D→E→C 7-task week plan。Task A 进行中（docs/FEM.md update）；Task C 等本 session 的 α_T。
