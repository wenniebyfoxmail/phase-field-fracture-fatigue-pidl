# Design decision — 2026-10-19

Complete coherent constrained incremental variational + FEM–neural hybrid specification delivered. Independent Codex review: REVIEW_PASS, design only, no decisive blocker and no design revision required. Frozen v1 SHA256: `ca50ad0e4913308165745311ece5ff1226f93b8c5c3b5e17512e7df240531b0d`.

The selected method uses a once-per-physical-substep learned next-state damage initial guess, full-space mechanical FEM and constrained damage correction, accepted-state trial fatigue, fresh final coupled acceptance and one durable commit. The new nodal feasible domain is explicitly stronger than historical GP soft/GP-only irreversibility; the primary neural-value comparator is identical constrained FEM with NN off, plus classical extrapolation.

Quality improvement relative to current PIDL and neural acceleration relative to direct constrained FEM are separate questions. Only measured end-to-end savings, including labels/training/setup/correction/failure/fallback, can support learned acceleration. No speedup or field improvement is established here.

## Implementation checklist (future work)

- Bind exact initial state, load path, eligible label supply and complete-trajectory splits; retain the historical versus new-problem distinction.
- Implement nodal lower/box/hard line, full active release and fresh final mechanics/damage/state audit with explicit cache identities.
- Fix dimensional scales, tolerances, globalization, joint caps and eta=0/nullspace behavior before execution; preserve original-operator residuals.
- Verify trial idempotence, old-state lower, stale-certificate rejection, crash/write rollback, durable single commit and restart.
- Freeze graph/features/model/normalizations and own-state rollout; no online future-FEM information or reference-selected solution.
- Measure all work against the same backend/hardware/precision/acceptance, including strong NN-off and classical predictors.
- Obtain exact implementation Code Ready review and a separate authorized data/resource execution card before any training/FEM.

This is implementation preparation for one integrated method, not a compulsory sequence of isolated scientific micro-tests. No source modification, scientific array/model access, SSH, GPU, training or FEM occurred in this task. The reviewer did not independently locate the historical c1 commit/v4 documents in this worktree; its transaction finding rests on the explicit v1 contract and inspected source, as disclosed in its receipt.
