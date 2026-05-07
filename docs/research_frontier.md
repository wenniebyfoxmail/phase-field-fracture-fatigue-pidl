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

1. **Soft symmetry penalty production** — 3-term loss penalty (NN raw correction parity), λ_α=λ_u=λ_v=1.0; smoke verdict: V4 RMS 0.013 (24× baseline improvement), avg cycle 2.99 min (1.5× baseline); auto-pipeline launched N=300 production (Taobo PID 2888934, GPU 1, ETA ~13-15h) → next: 等 N_f 数字 + V4 在 fracture cycle 上的 RMS
2. **§4 outline lock + Layer 3 red-team** — outline draft 完成（Layer 1）；待 soft sym production N_f 数据进 outline 后 lock 进 Layer 2，跑独立 subagent red-team review
3. **Phase 2.1 PCC α_T 反推** — fib MC 2010 §5.1.11 公式 + Lee & Barr 2004 数据已就位，可以反推 α_T 替代 0.094 占位符 → next: 任选目标 N (e.g. 10⁵ at S_c,max=0.7) 反求，给 Windows-FEM 重跑 PCC smoke

## Current Best Bet

**Reframe 现在更强了**：N_f BIT-EXACT cross-method/seed + α_bar_domain 1.08-1.78× + ᾱ_max 9-94× (known limit) + **symmetry resolved via soft penalty (24× rms improvement at near-baseline cost)**. Wu 2026 IJDM published gives theoretical grounding. FEM h-non-monotonic via Mandal 2019. Hard y² prior route abandoned (12× slowdown structural; archived as "rejected design exploration").

## Best Next Discriminator

Soft sym N=300 production N_f → 是否 match baseline 82 within ±10%。
- If yes (N_f ∈ [74, 90]): paper §4 claim "PIDL satisfies geometric symmetry (V4 24× improved) AND maintains framework-level N_f match (Δ<10%)" — **strongest possible §4**
- If no (N_f >> 82 OR no fracture): "soft symmetry preserves N_f at moderate λ; trade-off characterized" still defensible但 weaker

## Switch Condition

如果 soft prod N_f deviates >20% from baseline 82 → paper §4 加 caveat "soft symmetry trade-off small but measurable on N_f"，OR retry with smaller λ (0.1) to reduce penalty pressure.

## Parking Lot

- Symmetric data augmentation (Option B) 作 generalization-friendly fallback
- α-3 follow-up（已 closed out 2026-05-06，仅未来 work）
- MIEHE+AT2 strict Carrara 6-case sweep（kernel 已 fix `e7eb3f8`，等 Mac 决策）
- Oracle u=0.10/0.11 Tier C clean rerun（GPU 7, Queue D 进行中）
- TAFM 2026 non-uniqueness paper 是否进 §4.7（专家提示，待读）

## Recently Closed / Triggered

- **Soft symmetry path B 2026-05-07**: smoke V4 RMS 0.013 (24× vs baseline 0.30), avg cycle 2.99 min (1.5× baseline), auto-pipeline GO·λ=1, production N=300 launched (PID 2888934, ETA ~13-15h). v1+v2 hard y² prior abandoned (12× slowdown structural).
- **FEM h-convergence verdict B-FAIL 2026-05-06**: AT1+PENALTY 真 h-non-monotonic per Mandal 2019. Paper §FEM honest reframe in docs/FEM.md.
- **Symmetry prior 实现验证 2026-05-06**: hard y² cycle 0 alpha mirror RMS = 0 at exact pairs (mathematical guarantee) but production-unviable due to RPROP slowdown.
- **References 整理完毕 2026-05-06**: 15 PDFs 在 `references/`, README with Paradigm A/B/C explanation.
- **α-3 closed out + Phase 2 unblocked 2026-05-06**: fib MC 2010 sufficient, Holmen 不需要.
- **Tier C 4/5 done 2026-05-06**: enriched_v2 N_f=82 + Oracle u=0.12 N_f=85 + psiHack cold N_f=79 + tipw N_f=83; MIT-8 K=40 retry 仍跑; Queue D Oracle u=0.10/0.11 chained.
- **OOD boundary 2026-05-05**: Umax≤0.13 reliable, 0.14 systematic −24% bias.
