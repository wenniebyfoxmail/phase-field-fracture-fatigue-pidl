---
storyline_id: S09
experiment_id: S09-E012
protocol_revision: v1-local-support-sensitivity-diagnostic
status: design-review-candidate
updated: 2026-10-19
---

# S09-E012 — local-support sensitivity and realised-update audit

## Bounded question

Why did the E011 global amplitude-ranking direction preserve all 25 pair
outcomes instead of repairing the eight wrong pairs?  Distinguish one of three
next levers without another optimiser run:

1. replace the global amplitude observable with a localisation-aware objective;
2. repair gradient merging / AdamW preconditioning if they remove a useful
   local direction; or
3. change to a factorized amplitude-by-support head only if the present head
   has negligible local pair-contrast sensitivity.

This is a synthetic, exposed-development, no-training diagnostic.  It cannot
support holdout, rollout, transfer, FEM-teacher truth, real-road, or complete
fracture-PINO claims.

## Frozen evidence and states

- Same 16 exposed development cycles and 25 fixed growth-major pairs used by
  E010/E011; the eight initial errors and 17 initial correct pairs are retained.
- `S0`: E010 B25 update-500 checkpoint, the common E011 start.
- `C500`: E011 control update-500 checkpoint.
- `R500`: E011 ranking update-500 checkpoint.
- Frozen SHA256 identities are `24bbea27...cf05` (S0),
  `7a3f83e2...b057` (C500), `a3f2f83b...24c8d` (R500),
  `2f38ead9...247e` (E010 per-cycle CSV), `8acc97ba...e52` (E011
  per-cycle CSV), `0cf59c58...e4b` (executable P1 base config),
  `be399942...2b4` (E010 resolved arm/provenance config), and
  `1658d2a2...2a6` (packet manifest).  The implementation stores and compares
  the full values.
- Reuse the existing S0 global-amplitude pair Jacobian and E011 zero-step/log
  evidence.  Do not recompute an unchanged broad global audit.
- New autograd is one forward/gradient collection per unique cycle and state;
  pair vectors are assembled from cached cycle gradients.  No pair receives a
  second full forward/backward evaluation.

## Frozen local-support observable

For cycle `c`, use the exact E010 target-only support mask

`m_c(i) = 1[Delta d_FEM,c(i) > 1e-15]`.

The threshold, target increment and nodal weights are already frozen in E010.
The mask is not adjusted after inspecting any new gradient.  Its weighted area
is reported for every cycle.

For predicted projected increment `p_c = d_peak_pred - d_pre`, define

`a_local,c = sum_i w_i m_c(i) p_c(i) / sum_i w_i m_c(i)`;

`a_background,c = sum_i w_i (1-m_c(i)) p_c(i) / sum_i w_i (1-m_c(i))`;

`s_local,c = a_local,c - a_background,c`.

`s_local` is the sole new differentiable observable.  The predicted increment
mass fraction inside `m_c` is also reported as a field diagnostic but does not
define a separate gradient objective.  Because `m_c` uses FEM truth, all local
scores are diagnostics using a frozen oracle mask and are prohibited as
inference inputs or deployable masks.  No numerical upper-bound claim is made.

## New sensitivity and update decomposition

At `S0`, `C500`, and `R500`, collect per-cycle gradients for the frozen B25
objectives, global amplitude, and `s_local`.  Assemble all 25 pair contrasts and
report the original eight wrong and 17 correct pairs separately.

For each pair, report the change in global and local margins along:

1. raw global-ranking gradient descent;
2. damage-conflict-projected rank component;
3. complete pre-clip merge;
4. complete post-clip merge;
5. the exact next AdamW displacement reconstructed from the saved moments.

Also evaluate the finite displacement `C500-S0` and `R500-S0` against the S0
local/global contrast gradients.  This first-order response is reported
separately from the exact endpoint observable change and is never substituted
for it.  Split vector norms and dot products by
parameter groups: encoders, fusion, local blocks, coarse block, node decoder,
and global-property decoder.  Weight decay is reported explicitly; all three
frozen optimizers currently declare `weight_decay=0`.

Global clipping is a positive scalar operation.  The audit must distinguish a
smaller magnitude from a changed direction or pair sign and must not attribute
a direct sign flip to clipping when the cosine is one.  The subsequent saved-
moment AdamW transform is assessed separately and may change the parameter-
space direction of the resulting displacement.

## Frozen diagnosis and action-selection rule

The following numerical predicates are fixed before new gradients are read.
For a local pair contrast `J`, let `r = ||J|| / RMS(||J_g||, ||J_s||)`.
`usable` means `r >= 1e-4`; `negligible` means `r < 1e-4` (equality belongs to
`usable`).  For a nonzero proposed parameter change `v`, its normalised local
response is `rho = J dot v / (||J|| ||v||)`.  `locally_helpful` means
`rho >= 1e-3`; equality is helpful.  Zero vectors are not helpful.  Background
response is retained as descriptive evidence and is not a route predicate.

First assign zero or more mechanism labels to each of `S0`, `C500`, and
`R500`.  These labels are descriptive and may coexist across states:

- `RAW_OBSERVABLE_MISMATCH` iff all original eight wrong-pair local
  contrasts are usable and raw global-ranking descent is locally helpful for
  fewer than eight.
- `DOWNSTREAM_DIRECTION_LOSS` iff all eight are usable, raw global-
  ranking descent is locally helpful for all eight, and at least one later
  stage (projected rank, complete post-clip merge, or exact AdamW displacement)
  is locally helpful for fewer than eight.  Record the first such stage.
- `WEAK_LOCAL_PARAMETERISATION` iff all 25 local contrasts are negligible and
  every local contrast assigns less than `1e-4` of squared norm to the node
  decoder at that state.  This is weak architectural evidence, not proof that
  a factorized head is required.

Mechanism labels do not have to agree across states and are not forced into a
single causal explanation.  The next intervention is selected separately as
one exploratory probe by the following fixed priority, chosen for minimum code
change and ability to distinguish the proposed mechanism:

1. `MERGER_OR_PRECONDITIONER_REPAIR_PROBE` when `S0` has
   `DOWNSTREAM_DIRECTION_LOSS`.  This acts on the common continuation start,
   changes no observable, and is the smallest direct test of a lost raw signal.
2. `LOCALISATION_AWARE_OBJECTIVE_PROBE` when rule 1 does not apply and either
   `S0` or at least two of the three states have `RAW_OBSERVABLE_MISMATCH`.
3. `FACTORIZED_HEAD_PROBE` when rules 1--2 do not apply and all three states
   have `WEAK_LOCAL_PARAMETERISATION`.
4. `NO_ACTIONABLE_SIGNAL` only when no rule above applies or a validity check
   fails.

All matched action candidates and all mechanism labels remain in the receipt.
The priority chooses one bounded next test; it does not claim exclusive cause
or that lower-priority mechanisms have been excluded.  Background response is
descriptive evidence only.  No numerical threshold is relaxed to obtain an
action.

The 17 correct pairs are protected evidence: every sign count, realised loss,
and prospective crossing is reported.  The control's realised repair of all
eight old errors and loss of five old correct pairs remains visible.

## Budget, validity and stop rule

- Producer-only forward/autograd on Taobo; one GPU; wall time <= 15 minutes.
- Zero optimiser construction or mutation, zero FEM solve, zero fresh holdout.
- Model, optimizer and checkpoint hashes must be unchanged after the audit.
- Stop on identity drift, missing state, nonfinite value, support denominator
  failure, unexpected pair membership, evidence-write failure, or wall cap.
- Preserve the first result; no retry or support/threshold adjustment.

## Minimum evidence

- one CSV containing all pair/state/stage metrics;
- one compact JSON receipt with identities, sign counts, layer allocations and
  selected route;
- one decision-facing figure comparing global versus local pair response across
  S0/C500/R500 and the actual control/ranking displacements;
- one `README_analysis.md` stating the allowed and blocked conclusions.

## 2026-10-19 implementation identity clarification

The prelaunch producer preflight found that the frozen E010 resolved config is
an arm/provenance receipt and does not contain the executable operator width,
rank, normalisers, geometry contract, or complete gradient-vector contract
required by `build_runtime`.  The inherited reviewed P1 base config is the
executable runtime contract.  E012 therefore freezes and records both files:
the P1 base config constructs the runtime, while the E010 resolved config binds
the analysed B25 experiment provenance.  No data, state, observable, threshold,
pair, or decision rule changed.

