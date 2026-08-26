# AT1-fatigue neural-operator data-first amendment

**Date:** 2026-08-26
**Owner decision:** physics validation deferred; first require the operator to
learn the chosen FEM producer, even if that producer is physically imperfect
**Status:** `ONE_D1_PRODUCER_SMOKE_COMPLETE__REMAINING_11_UNCHANGED_JOBS_AUTHORIZED`

## What changes

The active branch no longer waits for Request 30, equilibrium residuals, AT1
phase residuals, Carrara substep replay or KKT/non-recovery validation. Those
assets are preserved for a later physics branch.

The immediate target is empirical:

> Given recent FEM cycle-peak fields on the native mesh, predict the next FEM
> fields and terminal crack-growth regime more accurately than PIDL and the
> existing data-only temporal controls.

Strict terminology: before a nonzero physics loss is introduced, this is a
`data-driven neural operator` or `GNO-data`, not a complete PINO. The project may
use “PINO route” informally for the planned family, but result files must retain
the precise label.

## Existing evidence means we do not start from zero

The July single-trajectory multiscale mesh operator learned ordinary FEM
evolution but failed the late c89 transition:

- c20/c40 masked one-step active log-MAE about 0.013/0.015;
- c76 recurrent-rollout active log-MAE 0.122, correlation 0.986;
- c89 rollout active log-MAE 3.196, correlation -0.371 and support-area ratio
  96.93.

The four-trajectory, 36-run LOCO matrix then showed:

- same-regime horizon-1 active log-MAE 0.0276--0.0317 and FEM-p99 IoU
  0.761--0.791;
- every Markov/TCN/Transformer run missed every transition-positive warning
  state;
- post-reset propagation produced about 95 times the FEM active-support area.

Therefore “can the network fit normal FEM steps?” is already positive. The
remaining data-only question is whether rare terminal transitions are learnable
from four trajectories without leaking the held-out event.

## PIDL experiment gate

- **Mechanism question:** can transition-aware supervision make a native-mesh
  operator reproduce held-out FEM terminal evolution better than existing
  data-only controls and PIDL?
- **Claim changed if success:** within this shared-mesh Umax=0.12 factorial, the
  FEM transition is learnable by a supervised operator and the operator is a
  viable numerical surrogate candidate.
- **Claim changed if failure:** the available four trajectories are
  insufficient for this terminal-transition surrogate; physics correctness is
  not adjudicated.
- **Cheaper diagnostic first:** completed by the single-trajectory and 36-run
  LOCO audits above.
- **Minimal output asset:** one four-fold/three-seed metrics table with locked
  transition predictions, PIDL/control comparisons, run provenance and a
  decision note.
- **Code/producer alignment:** Mac may edit and run unit/import checks only;
  training belongs on the approved PIDL producer after a separate launch gate.
- **Registry destination:** canonical track plus the existing full experiment
  inventory row; no new FEM handoff is needed.
- **Decision:** after independent review and the user's explicit 2026-08-26
  instruction, authorize only one revised D1 hard-5/seed-1 3,000-step Taobo
  producer smoke. The remaining 11 jobs stay blocked until its required
  assets, hashes and provenance validate.

## D1 design to freeze next

1. Use the existing four complete cycle-peak trajectories; no new substep FEM
   export.
2. Hold out one whole trajectory per fold. Never split elements or expose the
   held-out transition window.
3. Input the previous three states, geometry/area, initial-tip type and 5/8-step
   cadence; prohibit event-distance, first-hit cycle and future normalization.
4. Predict next-state increments for `d, alpha_bar, f, log10(psi_raw)` plus a
   transition score.
5. Use supervised field/gradient/rollout losses and a training-fold-only
   transition-balanced term. Use zero PDE/constitutive/KKT residual weight.
6. Compare with persistence, the existing matched Markov/TCN/Transformer runs,
   and matched PIDL outputs where state semantics exist.
7. Treat in-sample reconstruction as an optimization smoke only. Promotion
   requires held-out-trajectory transition and post-transition field gains.

## First producer-smoke outcome

The one authorized hard-5/seed-1 Taobo job completed at clean commit
`d45f58aca660909306cad93b376f2ce3dab91d93` with all required assets and
provenance. At the frozen 0.5 score threshold it detected 3 of 6 retrospective
transition-positive rows with 0 of 3 false positives. Mean active log-MAE was
0.3634 and absolute-p99 IoU was 0.3900.

This passes the producer/runtime/asset smoke but fails the preregistered recall
gate of at least 4/6 and does not beat the best locked control IoU. It is one
seed in one fold, so there is no scientific promotion and the remaining 11 jobs
cannot inherit a positive claim from the smoke. The owner explicitly authorized
those 11 unchanged jobs on 2026-08-26; the scientific lock and stop conditions
remain unchanged. The archived local smoke decision is
`local_archive/after_strict_setting_alignment/pidl_result/pf_gno_data_d1_hard5_seed1_d45f58a_20260826/decision.md`.

## Deferred assets

Request 30, its 45-state schema and history validator remain valid preparation
for a later physics-informed branch. They are neither deleted nor executed, and
their residual gates no longer block the current data-first surrogate test.
