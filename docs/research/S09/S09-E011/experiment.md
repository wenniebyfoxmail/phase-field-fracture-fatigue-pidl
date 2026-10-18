---
experiment_id: S09-E011
storyline: S09 Neural Operator fracture development
protocol_revision: v2-objective-only-ranking-after-zero-step-stop
status: CODE_REVIEW_REPAIR_READY
date: 2026-10-18
---

# S09-E011 — objective-only ranking repair

## Purpose and evidence stage

This is a bounded C1/C2 synthetic-development experiment. It asks whether one
explicit cross-cycle amplitude-ranking objective can repair the ordering errors
left by S09-E010 B25 without changing the operator head or the `beta=0.25`
equilibrium term. The 16 cycles are already exposed development examples. This
experiment cannot support a holdout, rollout, transfer, FEM-truth, full PINO or
real-road claim.

## D1 reuse decision

Continue the existing S09-E010 route. Reuse its qualified frozen packet,
native-Q4 evaluator, B25 update-500 model and AdamW state, hard constraints,
field reconstruction, metrics and plotting. The only scientific addition is a
single pairwise ranking direction. A factorized amplitude/support head remains
deferred unless this smaller objective-only test fails to produce a realised
repair.

## Operator and physics boundary

The unchanged map is

`(d_s00, [H,alpha_bar,q_prev,f]_s00, prescribed path, fixed mesh/material/BC)`
`-> (d_s04, [H,alpha_bar,q_prev,f]_s04, u_s04)`.

The physics contribution remains the native-Q4 AMOR free-displacement
equilibrium residual at predicted peak, with coefficient `beta=0.25`. It does
not include damage stationarity, the complete fracture variational inequality,
fatigue rollout, or a complete fracture PINO constraint.

For naming continuity, E010 `A25` is the exact E009 damage-anchor control
`g_D+q_U+q_H+0.25q_P`; it does not contain the new support/amplitude terms.
E010 `B25` adds `q_S+q_A` at the same equilibrium coefficient, and `B0`
removes the equilibrium term. E011 starts from the frozen B25 endpoint.

## Fixed data, pairs and initial state

- Packet manifest SHA256:
  `1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6`.
- Source B25 checkpoint SHA256:
  `24bbea271fe3c2df79913f552dde863e495d33df963e0db9586b4920904dcf05`.
- Both arms clone the complete B25 update-500 model and AdamW state.
- Growth cycles: `{1,58,60,69,70}`.
- Near-stagnant cycles: `{3,4,71,72,73}`.
- Pair set: the 25 Cartesian growth-by-stagnant pairs in lexicographic order.
- Batch schedule: one pair per optimiser update; all 25 pairs repeated exactly
  20 times without shuffle, giving 500 updates per arm.
- No fresh holdout or new trajectory is accessed.

## Ranking objective

For cycle `i`, define the weighted predicted damage-increment amplitude

`a_i = sum_x w_x * |d_peak_i(x)-d_pre_i(x)| / sum_x w_x`.

For one growth/stagnant pair `(g,s)`, freeze

`L_R = softplus((m - (a_g-a_s)/D) / tau)`,

where `D=1.6864539921617467e-4`, `m=0`, and `tau=0.01`. `D` is the existing
detectable-growth scale; it is not refit to E010 endpoint errors. Zero margin
asks only for correct ordering. No weight, margin or temperature scan is
allowed.

For each pair, all six B25 objectives are the arithmetic mean of the growth and
stagnant examples. Let `a=grad(L_D)`. Every auxiliary direction is norm-matched
to `a` and has any first-order conflict with `a` removed, exactly as in E010.
The two arms are:

1. `C25_pair_batched_B25_continuation`:
   `a+q_S+q_A+q_U+q_H+0.25q_P`.
2. `R25_pairwise_ranking_beta0p25`:
   `a+q_S+q_A+q_U+q_H+0.25q_P+q_R`.

`q_R` has the unique coefficient `4096.0`. Each complete direction receives one
global L2 clip at 1.0, followed by the cloned AdamW state. This is the only
between-arm change.

### Prospective D2 amendment after A001, before training

The first zero-step candidate used `gamma_R=1.0` and stopped without an
optimiser step. All eight wrong pairs had nonzero sensitivity, but the added
direction changed their opposing merged B25 derivatives by only 0.04--0.28%;
the required zero-crossing coefficient was at most approximately `2.84e3`.
Revision v2 fixes `gamma_R=4096`, the next power of two above that bound. This
is one analytic repair, not a weight scan. The immutable A001 receipt remains
under `attempts/`.

A001 used the historical v1 admission predicate and therefore remains a
faithful `STOP` record. Under the prospectively amended v2 predicate it is not
relabelled after the fact; A002 is the first v2 admission record.

## Zero-step directional admission

Before either optimiser advances, replay all 25 pair-specific merged and
projected directions at the shared B25 endpoint. For each arm, analytically
propagate the direction through the exact next AdamW state without mutating the
model or optimiser, then record the first-order changes in pair margin, `L_D`
and `L_P`.

Admission requires:

- the initial wrong-pair set remains exactly eight pairs;
- the ranking arm predicts a positive next-step margin change for all eight
  wrong pairs;
- after adding the predicted first-order change, no more than three of the 17
  initially correct margins cross zero; negative but non-flipping changes are
  reported as amplitude-ranking cost rather than treated as invalidity;
- its median wrong-pair margin change exceeds the control median;
- all values are finite, and model/optimiser hashes remain unchanged.

This audit checks the actual pair-specific merged/projected direction and the
next AdamW state. It is still a first-order local diagnostic and does not
guarantee finite-step repair.

## Evaluation and prospective interpretation

Evaluate both arms at updates `{0,16,64,128,256,496,500}`. The smallest
primary exploratory signal is

`pair_score_R25 - pair_score_C25 >= 2`,

where `pair_score=2W+T`. A gain of 2 is one net repaired pair and is deliberately
less demanding than the unchanged E010 primary gain of 4. It selects whether
the explicit objective creates any realised ordering value; it does not revise
the E010 negative result.

Report separately:

- zero-step directional improvement;
- which of the eight initial wrong pairs are actually repaired;
- which of the 17 initial correct pairs are lost;
- final pair score and AUC versus the control and original E010 B25;
- `G`, false growth `F`, `L_P`, `L_judge`, and spatial correlation;
- candidate/control protected ratios, with `1.10` as a diagnostic limit;
- `delta d` fields on identical colour scales and all-cycle amplitudes.

Outcome labels:

- `OBJECTIVE_REPAIR_SIGNAL`: valid run and primary gain at least 2;
- `NO_REALISED_RANKING_REPAIR`: valid run and primary gain below 2;
- `ROBUST_LOCAL_REPAIR`: secondary tier only, requiring gain at least 4 and
  all four protected ratios at most 1.10;
- `EXECUTION_INVALID`: identity, finite, hard-constraint or evidence failure.

Directional improvement, realised pair repair and the final primary result are
reported separately. Component changes never overwrite the primary label.

## Budget, stop rule and evidence

- Two arms, at most 500 optimiser updates each; total cap 1,000 updates.
- One GPU, total wall time at most one GPU-hour.
- No weight scan, retry, alternate seed, new head or fresh holdout.
- Stop before training if zero-step admission fails.
- Stop on identity drift, nonfinite values, hard-constraint violation, evidence
  write failure or wall-time cap.
- Preserve the first stopped or completed result; do not retry.
- Required evidence: environment/source identity, zero-step audit, per-arm
  start/gradient/train/evaluation logs, update-500 checkpoints, completion
  receipt, decision metrics/table, aligned amplitude plot and equal-scale
  reference/control/ranking `delta d` fields.
- A shared success is published only after rereading canonical per-arm
  receipts, checking the 500 update rows and seven evaluations, recomputing
  every declared artifact hash, reconstructing fields, and writing the two
  required figures. `failure_receipt.json` is authoritative if close-out is
  interrupted after any success-looking file is written.

## Decision ladder

| Step | Question | Evidence | Advance or redirect |
|---|---|---|---|
| D1 complete | Can existing E010 assets isolate an objective change? | pair-contrast audit and reusable B25 endpoint | Continue; no head change |
| D2 active | Does the exact merged/AdamW direction target wrong pairs safely enough? | zero-step audit | Pass -> exact review and one run; fail -> redesign objective only |
| D3 | Does the objective produce realised net pair repair? | R001 two-arm result | Gain >=2 -> retain objective; miss -> factorized head becomes next discriminator |
