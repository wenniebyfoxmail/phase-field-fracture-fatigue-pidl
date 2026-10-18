---
storyline_id: S04
experiment_id: S04-E014
protocol_revision: v1
status: completed
started_at: 2026-10-08
closed_at: 2026-10-08
primary_storyline: S04
related_storylines: [S09]
scientific_verdict:
---

# Raw-driver progress/support mechanism diagnostic

## Scientific question

After the frozen S04-E013 failure, does one predeclared raw-driver
representation—normalized-progress-conditioned mean plus a rank-20 POD of
training deviations masked to each training cycle's FEM-p99 active support—meet
the same practical oracle-reduction target in all three complete-Umax holdouts?

## Claim contract

- Claim tier / tag: `T2 synthetic science / exploratory residual mechanism`.
- Estimand: raw log10 FEM-minus-PIDL driver residual on the identical 86,408-cell
  FEM grid, C1 through FEM own-first-event inclusive, evaluated within each
  held-out cycle's FEM-p99 active-driver support.
- Comparator: zero correction. The frozen E013 pooled-global rank-20 POD is
  reproduced as `M0`; it is not re-decided.
- Primary candidate: `M3_progress_support_pod` only.
- If primary passes: the specified progress-conditioned local residual
  representation is sufficiently promising to justify a separate retrospective,
  true-event-time-conditioned offline coefficient experiment.
- If primary fails: do not train that representation. Retain the component arms
  as exploratory diagnostics; do not reinterpret E013 damage/history.
- Regardless of outcome, this seen-data mechanism selection is not independent
  confirmation, predictive generalization, neural correction success, FEM
  physical truth, online PINN improvement, online availability of normalized
  event progress, or real-road validity.

## Intake and cheaper falsification

1. Question: can progress conditioning plus support-aligned basis construction
   explain the raw-driver-only cross-Umax failure?
2. Claim change: only whether this exact representation advances to an offline
   coefficient-prediction experiment.
3. Cheapest evidence: reuse the locked E013 trajectories; no FEM/PIDL rerun and
   no neural training.
4. Smallest decisive asset: three-row M3 holdout summary plus its frozen
   bootstrap endpoint.
5. Storyline route: `S04 -> S04-E014 -> R001 -> mechanism table/decision`.

## Frozen mechanisms

- `M0_pooled_global_pod`: exact E013 raw-log10 construction.
- `M1_progress_global_pod`: equal-weight mean of the two training-Umax residual
  fields linearly interpolated in normalized progress; rank-20 POD is fitted to
  whole-domain training deviations from that progress mean.
- `M2_support_pod`: rank-20 POD fitted after setting every training residual to
  zero outside that cycle's FEM-p99 active support; no progress mean.
- `M3_progress_support_pod` (primary): M1 progress mean plus rank-20 POD fitted
  to progress-mean deviations set to zero outside each training cycle's FEM-p99
  support.
- `M4_affine_umax_progress_mean`: no POD; at each normalized progress, the two
  training fields define an affine Umax interpolation/extrapolation. This is a
  diagnostic only because the middle Umax is interpolated while endpoint Umax
  holdouts are extrapolated.

All POD bases, centering fields, progress means, and training supports use only
the two training Umax trajectories. Held-out residuals enter only the disclosed
oracle coefficient fit and evaluation. Held-out FEM support defines the frozen
local metric, as in E013.

M1, M3, and M4 additionally query `tau=(cycle-1)/(heldout FEM own-first-event-1)`.
They therefore use the held-out future event time as a retrospective oracle.
This experiment can select a same-condition offline representation only; it
cannot establish an online predictor unless a later experiment replaces true
event time with an input available at inference.

## Frozen decision contract

- Evidence identity: `input_lock.json` locks the E013 data lock and claim-bearing
  R002 decision/primary table.
- Necessary validity gates:
  1. E013 input hashes, field semantics, shapes, cycles, steps, and common grid
     pass the reused validator;
  2. `M0` reproduces all three E013 raw-log10 median ratios and bootstrap upper
     endpoints within absolute `1e-10`;
  3. every rank-20 basis exists, is finite, and passes the reused float64-SVD
     orthogonality checks; baseline and corrected RMSE values are finite. A
     non-finite ratio caused by a zero baseline is an unidentified estimand, not
     a numerical-validity failure.
- Primary criterion: for `M3_progress_support_pod`, all three complete-Umax
  holdouts have a 97.5th-percentile endpoint of the deterministic non-circular
  moving-block bootstrap distribution of median per-cycle error ratio `<0.90`.
  Error ratio is corrected FEM-p99-support area-RMSE divided by zero-correction
  area-RMSE. Block length 5, 2,000 replicates, seeds `20261080 + fold_index`.
- Threshold rationale: identical to E013, requiring at least a 10% practical
  residual-RMSE reduction at the conservative interval endpoint. It was not
  selected from E014 candidate results.
- Missing/non-finite rule: any primary fold with fewer than 20 cycles or any
  non-finite ratio is `inconclusive`, unless another identified fold fails, in
  which case the bounded verdict is negative.
- Diagnostics that cannot rescue the primary: M1/M2/M4, ranks 1/2/4/8/16/20,
  C1-20, C21-40, middle, late and event bins, support IoU, correction magnitude,
  and per-cycle plots.
- Stop rule: stop after the frozen five-arm offline analysis. Do not add a sixth
  arm, alter masks/ranks/thresholds, or train a network after seeing the result.

```text
validity fails                         -> inadmissible
all three M3 primary folds pass        -> supports retrospective bounded next experiment
any identified M3 primary fold fails  -> negative for M3 only
no identified failure + unidentified  -> inconclusive
```

## Producer and evidence

- Producer: Mac local light analysis; no training loop.
- Runner: `SENS_tensile/analyze_raw_driver_mechanisms.py`.
- Output: `local_archive/experiments/S04-E014/runs/S04-E014-R001/analysis/`.
- Minimum evidence: input validation, E013 reproduction table, per-cycle arm
  metrics, primary summary, phase summary, one comparison figure with
  `README_analysis.md`, decision note, and Run receipt.

## Code review

Independent round 1: FAIL; required separation of numerical invalidity from an
unidentified zero-baseline ratio and explicit disclosure of the held-out future-
event-time oracle. Both were addressed before execution.

Round 2: `PASS — Code Ready`, bound to:

- runner SHA-256 `594fa83e14773a71d0f8d5ad7fb836b3575ec6f09a2a973622b2196a6ea75caf`;
- test SHA-256 `170d7b4fae5e6d560f32aaf9e13d26d5f4ee87b33cd6975da56cb8fe37fcd1a4`;
- protocol SHA-256 `87448b2b4401999de482233d246efd3a437717844fc5ca2f9b15a220cb7fcfb5`;
- input-lock SHA-256 `883ab8e4aa58d85307c764ad52fdb2226f63f49fbfc6eb1589c715ff024db11f`.

Deterministic checks: 18 passed.

## Runs

| Run ID | Purpose | Execution | Retrieval | Receipt |
|---|---|---|---|---|
| S04-E014-R001 | raw-driver mechanism diagnostic | succeeded | verified | `RUN_RECEIPT.md` |

## Scientific verdict

**Negative for M3.** The primary progress-conditioned support-masked rank-20 POD
passes 2/3 folds. Held-out Umax=0.12 fails: median ratio `1.0083607502`, bootstrap
upper endpoint `1.2489917563`, against the frozen `<0.90` criterion.

Diagnostics cannot rescue this verdict. They show that progress conditioning is
the harmful component for Umax=0.12, while support masking alone (`M2`) is below
threshold in all three folds. M2 may motivate a separately gated exploratory
coefficient-prediction feasibility experiment, but E014 does not establish its
predictability or independent validity.

Independent result review: `PASS — Evidence Ready`; 14 input hashes, 6,600
per-cycle rows, 75 summaries, nine independently recomputed bootstrap endpoints,
the figure, receipt, and bounded claim language were verified.
