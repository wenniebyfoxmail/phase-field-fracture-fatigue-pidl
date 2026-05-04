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

[新 entries 从这里开始，newest first]
