# Shared Research Log

**Purpose**: 跨机公共研究纪要。只记录有长期保留价值的 finding、decision、retraction、blocker。

**边界规则（2026-05-05 起生效）**：
- 日常任务派发/ack/progress/done **不再写这里**
- 这些内容走 `docs/handovers/*_inbox.md` / `*_outbox.md`
- 本文件只收：重要发现、架构决策、结果撤回、持久性阻塞

**历史归档**: `docs/archive/shared_research_log_2026-04_to_2026-05-05.md`

## Format rules

1. Entries ordered **newest first** (reverse chronological).
2. Every entry starts with: `## YYYY-MM-DD · <Agent-Name>`
3. Tag the kind: `[finding]`, `[decision]`, `[retraction]`, `[blocker]`
4. Include commit SHA + branch when relevant.
5. Keep entries concise; link to full memory files by name for detail.
6. Append-only: 修正旧 entry 通过新 entry 标注，不改历史文本。
7. Before pushing, git pull first to catch concurrent edits.

## Agent identifiers (current)

| Agent | Machine | Primary role |
|---|---|---|
| Mac-PIDL    | macOS (user's laptop) | Interactive dev; PIDL training (CPU/MPS); analysis; writing |
| Windows-PIDL | Windows (CPU-bound) | PIDL training + performance optimization |
| Windows-FEM  | Windows (GRIPHFiTH) | FEM reference runs; Fortran source of truth |

---

## Canonical facts (carried over, still valid)

- **run_baseline_umax.py bug FIXED** (commit 6040cbb + guard 427ebe7): 所有 non-u=0.12 baseline results from May-4 INVALID. Clean reruns in progress.
- **u=0.14 N_f=127 RETRACTED**: resume artifact, not real physics.
- **u=0.12 seed=1/2 N_f=82 BIT-EXACT**: VALID, unaffected by bug.
- **Oracle runs (Windows, run_e2_reverse_umax.py)**: all VALID, unaffected by bug.
- **Phase 2 PCC FEM smoke**: completed, α_T=0.094 placeholder → N_f≫10⁵. Blocked on Holmen 1982 calibration.

---

## Entries

## 2026-05-05 · Mac-PIDL [finding]

**u=0.14 pure-physics 5-seed sweep: systematic underestimate (mean −24%) + high variance (std=4.2) — OOD boundary confirmed**

FEM N_f = 39.

| seed | N_f (first) | error |
|---|---|---|
| 1 | 28 | −28% |
| 2 | 36 | −8% |
| 3 | 26 | −33% |
| 4 | 33 | −15% |
| 5 | 25 | −36% |
| **mean** | **29.6** | **−24%** |
| **std** | **4.2** | — |

All 5 seeds underestimate FEM. Range = 25–36 (span 11 cycles). This is not seed noise around the correct answer — it is a systematic bias combined with high variance. Pattern A regime (boundary α saturation compresses N_f before tip accumulator builds) is the leading mechanism.

**OOD boundary conclusion**: PIDL pure-physics reliable for Umax ≤ 0.13 (≤+7% vs FEM, low seed variance). Umax = 0.14 is outside reliable range (−24% bias, std=4.2). Paper should report this as the identified OOD boundary.

**u=0.12 seed=3 also completed**: N_f=82, same as seeds 1+2. u=0.12 is fully deterministic across seeds (zero variance at training Umax).

## 2026-05-05 · Mac-PIDL [finding]

**FEM-1 mesh convergence result: N_f_fine=77 vs N_f_coarse=82 (Δ=-6.1%, borderline outside 5% gate)**

| Mesh | Tool | Quads | h_tip | ℓ/h_tip | N_f |
|---|---|---|---|---|---|
| Coarse baseline | Abaqus (SENT_mesh.inp) | 77,730 | ≈0.004 mm uniform | ≈2.5 | 82 |
| Fine | gmsh (SENT_pidl_fine_lh5.inp) | 10,261 graded | 0.002 mm | 5 | 77 |

Strict 5% gate: FAIL by 1.1pp. However this is a mixed-tool comparison (Abaqus uniform vs gmsh graded), which introduces node-placement noise. Qualitative shape, K_initial, fracture pattern all match.

**Paper decision pending**: (a) use safe "6.1% spread within mixed-tool noise" caveat; or (b) request gmsh-only h-sweep (mesh_C/M/F variants already in GRIPHFiTH mirror) for clean same-tool convergence proof. Audit Hit 16 status: partially closed (evidence of convergence), phrasing still to confirm.

## 2026-05-05 · Mac-PIDL [finding]

**FEM mesh inventory across campaigns — PIDL series is ℓ/h≈1 (coarse), not community standard**

Three distinct mesh campaigns exist in GRIPHFiTH:

| Campaign | Mesh file | ℓ | h_tip | ℓ/h_tip | Quads |
|---|---|---|---|---|---|
| PIDL series (u=0.08–0.14) | SENT_mesh.inp (Abaqus, Mac-supplied) | 0.01 mm | ~0.01 mm | **~1** | 77,730 |
| Carrara strict-repro (AMOR+MIEHE Basquin sweep) | SENT_carrara_quad.inp | 0.004 mm | 0.0008 mm | **5** | 31,041 |
| PCC concrete smoke (Handoff F) | SENT_pcc_concrete_quad.inp | 5 mm | 1 mm | **5** | 1,107 |

**Key implication**: the PIDL-series FEM reference data (all N_f values used for PIDL/FEM comparison) comes from ℓ/h≈1, which is coarser than the Carrara/community standard of ℓ/h=5. The mesh was kept for back-compat with PIDL training data.

**Paper action item**: need mesh-convergence check — run PIDL-series at Umax=0.12 with ℓ/h=5 mesh, verify N_f within 5%. If it passes, state "legacy mesh retained for PIDL back-compat; convergence verified at representative Umax". If N_f shifts >5%, must decide whether to retrain PIDL with new mesh or caveat.

**Audit Hit 16 status**: still open, this finding confirms it's a real gap.
