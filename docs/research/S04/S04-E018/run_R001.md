# S04-E018-R001 — exact run candidate, not authorized

> **SUPERSEDED — DO NOT EXECUTE.** `S04-E018` was already allocated elsewhere.
> Use only the globally checked `S04-E021-R001` candidate at commit
> `6aa21e3c469d53c92240c9689d07a3ffb316d67c` after separate human approval.

Date: 2026-10-15 Europe/London. Execution status: `prepared`; retrieval and
scientific verdict: `pending / none`.

## Exact identity

- Producer: `Wennies-MacBook-Pro-14.local`, local CPU4, no GPU.
- Worktree: `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-e018-runtime-c883bfd`.
- Runtime HEAD: `c883bfd8e4ecd37d2ae32dc3717a63db018f1ae2`, detached.
- Design: `45b8d32da2b8088ce697047343bebf0a848e69ce`.
- Input lock SHA-256:
  `cb9f63f8bd4b73afe0bd0f74bc7836018ce2e6bfcbd46edae80e7fef7b07868c`.
- Experiment / Run: `S04-E018` / `S04-E018-R001`.
- Output:
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E018/runs/S04-E018-R001`.
- Authorization artifact, created only after approval:
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E018/authorizations/S04-E018-R001.json`.

This is closed-form streamed ridge analysis, not a PIDL neural-network training
loop. It uses only the admitted four development trajectories. U0.1175/U0.125
are not referenced by the lock or command.

## Exact command after separate approval

```text
cd /Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-e018-runtime-c883bfd
/Users/wenxiaofang/miniconda3/bin/python3 SENS_tensile/s04_raw_guard.py --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E018/runs/S04-E018-R001 --authorization /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E018/authorizations/S04-E018-R001.json
```

The command is not authorized by this record and has not been run.

## Immediate preflight after approval, before launch

1. Confirm no `s04_raw.py`, `s04_raw_guard.py` or `s04_raw_report.py` process.
2. Require runtime HEAD exactly `c883bfd...` and reviewed source paths clean.
3. Require the only runtime untracked item to be the declared `local_archive`
   symlink and verify its exact target.
4. Recompute the tracked lock SHA and require `cb9f63f8...868c`.
5. Require output, guard log and both sidecar receipts absent.
6. Create the authorization directory and exact approved JSON atomically from
   the candidate, changing only `user_approved_real_fit` to `true`.
7. Run the command once. No retry/resume/fallback producer.

## Hard limits and terminal routing

- Joint fit+report wall time: 300 s.
- Aggregate guard and child-tree RSS: 2 GiB.
- Output including logs/receipts: 100 MiB.
- CPU threads: 4; GPU hidden.

`COMPLETED` means execution succeeded only. `WALL_CAP`, `RSS_CAP`, `OUTPUT_CAP`,
child failure, invalid input/numerics/implementation or unidentified denominator
is retained as its own terminal status. None authorizes a retry or scientific
success claim.

## Minimum post-run checks

- Guard, fit-stage and worker receipt identities agree on Run, PID, output,
  code/design/lock and exit status.
- Output contains no missing or nonfinite required metrics and exactly four
  outer folds; all fallbacks and selected alphas remain visible.
- Figures render and use the exact scored outputs; `README_analysis.md` carries
  the allowed and blocked conclusions.
- Preserve raw logs and partial evidence on any failure.
- Independent evidence review is required before interpreting a completed Run.
