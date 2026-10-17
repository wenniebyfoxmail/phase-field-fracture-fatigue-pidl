# AT1-fatigue mesh-PINO track

**Owner:** Mac-PIDL  
**Status:** data-first FEM-surrogate branch active; physics-residual branch deferred by owner  
**Claim class:** synthetic FEM imitation / trajectory sufficiency  
**Canonical decision:**
[`at1_fatigue_mesh_pino_d1_final_prelaunch_lock_20260826.md`](at1_fatigue_mesh_pino_d1_final_prelaunch_lock_20260826.md)

## Mechanism question

Can a supervised native-mesh neural operator reproduce the archived FEM
cycle-peak field transition, including the terminal crack-growth regime change,
more accurately than the locked PIDL and existing Markov/TCN/Transformer
controls? No PDE/residual correctness question is asked in the active branch.

## Claim boundary

A successful benchmark would support only imitation of the selected FEM
producer on the shared geometry/mesh and synthetic Umax=0.12 Hard5 factorial.
The operator is allowed to reproduce FEM error. Success would not establish
physical correctness, new-mesh/material/specimen/road generalization or
real-observation forecasting. FEM is the teacher for this branch; PIDL is the
comparison baseline.

## Active data-only candidate

- Native Q4 node/element Graph Neural Operator, not a rasterized FNO primary.
- Native Q4 element graph with local and coarse/global message passing.
- Inputs: the last three cycle-peak FEM states
  `[d, alpha_bar, f, log10(psi_raw)]`, geometry/area, hard-vs-soft initial-tip
  label, and retained 5/8-step cadence label. No event-relative or future-cycle
  feature is allowed.
- Outputs: next-cycle state increment plus a learned transition/regime score.
- Supervision only: area-weighted field loss, edge-gradient/process-zone loss,
  short recurrent rollout loss and transition-balanced loss. Physics residuals,
  KKT, constitutive replay and substep-history validation have zero weight and
  are not training prerequisites.
- State bounds/non-recovery projections are numerical output constraints only;
  they are not evidence that the FEM or operator is physically correct.

The active comparison is `GNO-data` versus persistence, the existing matched
Markov/TCN/Transformer controls, and the locked PIDL baseline on identical FEM
targets. `GNO-PINO` is deferred. Test-time fitting and access to the held-out
trajectory's transition window are excluded.

## Gate ladder

1. **D0 — existing evidence:** completed. Same-regime short-horizon FEM
   imitation works; terminal transition forecast fails.
2. **D1 — transition-aware data-only design:** two independent reviews are
   complete and their findings are resolved in
   [`at1_fatigue_mesh_pino_d1_final_prelaunch_lock_20260826.md`](at1_fatigue_mesh_pino_d1_final_prelaunch_lock_20260826.md).
   Local verification and release preparation remain; launch is not approved.
3. **D2 — four-fold LOCO producer run:** train on three complete FEM
   trajectories and hold out the fourth, with three seeds and no physics loss.
4. **D3 — PIDL comparison:** compare same-cycle field and transition timing on
   the held-out hard-5/hard-8 cases using only available matched states.
5. **P0 — deferred physics branch:** Request 30, residual computability and
   PINO physics losses may be reopened later; they do not block D1-D3.

## Active gate

Freeze a transition-aware, data-only GNO experiment using the already
materialized four-trajectory cycle-peak dataset. The cheap audit is already
complete: the existing 36-run LOCO matrix shows that ordinary one-to-three-step
same-regime evolution is learnable, while all six transition-positive warning
states were missed. The new design must therefore change only the treatment of
rare regime-transition supervision, not add PDE losses or request new FEM.

Request 30 and its validator remain preserved as deferred assets. They are not
to be executed or used as a precondition for the active data-first branch.

## Success and stop conditions

The data-only branch succeeds only if the held-out-trajectory transition and
post-transition fields improve over the best existing data-only control and the
matched PIDL comparator. In-sample reconstruction or training on the held-out
transition is not prediction and cannot satisfy the gate. Failure closes this
four-trajectory architecture branch without implying that FEM is physically
wrong or right.

## Evidence

- Machine audit:
  `local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/at1_fatigue_mesh_pino_stage0_20260824/readiness_audit.json`
- Input dataset:
  `local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/factorial_loco_temporal_dataset_20260729/`
- Review:
  [`../reviews/at1_fatigue_mesh_pino_framework_review_20260824.md`](../reviews/at1_fatigue_mesh_pino_framework_review_20260824.md)
- Existing single-trajectory data-only result:
  `local_archive/.../analysis/fem_anchored_mesh_operator_20260715/decision.md`
- Existing four-trajectory LOCO result:
  `local_archive/.../pidl_result/factorial_loco_matrix_20260729/analysis/decision.md`

## Next action

Complete local verification and prepare a clean, committed release identity.
Then request a separate explicit approval that pins the commit and matrix-lock
SHA before any of the 12 Taobo jobs are started. Do not execute Request 30 and
do not add equilibrium, phase, KKT or fatigue-update residuals to this data-only
gate.
