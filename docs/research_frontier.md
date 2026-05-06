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

Phase 1 paper §4 的 framework-vs-field reframe 怎么落地：claim "PIDL captures Carrara framework" 在 V4 对称破缺 + AT1 h-non-monotonic 两道严谨性问题下能否成立？

## Active Branches

1. **Symmetry prior 速度 + N_f 验证** — y² hard prior 数学正确（rms=0 at exact mirrors）但 v1 慢 6-15×。v2 加 input rescale `8y²-1 ∈ [-1,1]` 修 RPROP ill-conditioning，smoke 进行中 (Taobo GPU 1, PID 2425141) → next: 看 cycle 0-1 timing；如恢复 baseline-class 则派 N=300 production
2. **§4 outline lock + Layer 3 red-team** — outline draft 完成（Layer 1）但还没 lock；symmetry smoke 出 N_f 后 lock outline 进 Layer 2，跑独立 subagent red-team review
3. **Phase 2.1 PCC α_T 反推** — fib MC 2010 §5.1.11 公式 + Lee & Barr 2004 数据已就位，可以反推 α_T 替代 0.094 占位符 → next: 任选目标 N (e.g. 10⁵ at S_c,max=0.7) 反求，给 Windows-FEM 重跑 PCC smoke

## Current Best Bet

**Reframe 已经基本可写**：N_f BIT-EXACT cross-method/seed + α_bar_domain 1.08-1.78× + ᾱ_max 9-94×（已 known limit）+ symmetry hard prior 数学解决（待 production 验证 N_f match）。Wu 2026 IJDM published 给理论 grounding。FEM h-non-monotonic 已用 Mandal 2019 reframe（non-blocker）。

## Best Next Discriminator

Symmetry v2 smoke cycle 0 timing → 决定全 production 是否可行。如果 cycle 0 ~7 min（baseline-class），symmetric-PIDL N=300 大约 10-12h，立刻派；否则 fallback 到 symmetric data augmentation 或 loosen rel_tol。

## Switch Condition

如果 v2 smoke cycle 0 仍 >15 min → input rescale 没解决根因，paper §4 改为 "we identify symmetry violation; demonstrate architectural fix at cycle-0 forward; full production deferred to Phase 2"（弱 claim 但仍 honest）。

## Parking Lot

- Symmetric data augmentation (Option B) 作 generalization-friendly fallback
- α-3 follow-up（已 closed out 2026-05-06，仅未来 work）
- MIEHE+AT2 strict Carrara 6-case sweep（kernel 已 fix `e7eb3f8`，等 Mac 决策）
- Oracle u=0.10/0.11 Tier C clean rerun（GPU 7, Queue D 进行中）
- TAFM 2026 non-uniqueness paper 是否进 §4.7（专家提示，待读）

## Recently Closed / Triggered

- **FEM h-convergence verdict B-FAIL 2026-05-06**: load-drop and d-front bit-identical N_f；wide=narrow band 也 bit-identical → AT1+PENALTY 真 h-non-monotonic per Mandal 2019. Paper §FEM 用 honest reframe（详 docs/FEM.md）
- **Symmetry prior 实现验证 2026-05-06**: cycle 0 alpha mirror RMS = 0 at exact pairs (mathematical guarantee confirmed)
- **References 整理完毕 2026-05-06**: 15 PDFs 在 `references/`，加了 README + Paradigm A/B/C 说明
- **α-3 closed out + Phase 2 unblocked 2026-05-06**: fib MC 2010 sufficient，Holmen 不需要
- **Tier C 4/5 done 2026-05-06**: enriched_v2 N_f=82 + Oracle u=0.12 N_f=85 + psiHack cold N_f=79 + tipw N_f=83；MIT-8 K=40 retry 仍跑（~12h ETA）；Queue D Oracle u=0.10/0.11 chained
- **OOD boundary 2026-05-05**: Umax≤0.13 reliable, 0.14 systematic −24% bias
