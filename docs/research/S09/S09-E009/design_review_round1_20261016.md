# S09-E009 design review round 1 — 2026-10-16

## Verdict

`REVISE_AND_REREVIEW`

Haofan / ChatGPT Pro accepted the diagnostic motivation but did not authorise
implementation. The three-arm design confounded removal of physics with a
change of merger, the damage-anchor algorithm could amplify a nearly removed
direction, and the relative advancement filter could still nominate a model
whose growth error is worse than persistence.

## Adopted findings

1. Use four matched arms: exact replay `R`, scalar data-only `S`, anchor control
   `A0` with beta zero, and PINO candidate `A25` with beta 0.25. This permits
   `S -> A0` to assess the whole anchor rule and `A0 -> A25` to assess adding
   the present physics term inside that rule. `R -> A25` remains an overall
   repair comparison, not a single-factor attribution.
2. Preserve the replay coefficients exactly. If the atomic terms are projected
   damage `l_d`, raw damage increment `l_dr`, displacement `l_u`, projected
   history `l_h`, raw history increment `l_hr`, and equilibrium `L_P`, replay
   remains `J_N=(l_d+l_u)/2+l_dr`, `J_H=l_h+l_hr`, `J_P=L_P`.
3. Keep 500 updates only as a bounded screen. Add a non-selective update-496
   evaluation; never select the better checkpoint. A negative result does not
   establish architecture incapacity or state insufficiency.
4. Give every arm a byte-identical initial parameters/buffers state and an
   independent empty AdamW state. Cap the experiment at 2,000 total updates,
   exactly 500 per normally completed arm; unused budget cannot move between
   arms.
5. For anchor arms, equalise auxiliary norms before projection and do not
   renormalise after projection. Zero auxiliary gradients are valid zero
   contributions. An anchor norm at or below `1e-12` makes that arm
   `ANCHOR_STATIONARY_OR_INAPPLICABLE`; missing/nonfinite/layout errors remain
   execution failures.
6. Euclidean gradient alignment is not an AdamW no-harm guarantee. Record the
   actual parameter-displacement alignment `g_D dot (-delta_theta)` and remove
   any claim that anchoring guarantees a damage-loss decrease.
7. Retain the relative repair thresholds as an engineering signal, then require
   growth MAE to beat the frozen persistence baseline before nominating a new
   confirmatory P1 gate.
8. Predefine zero denominators and undefined correlations. Report spatial
   capability separately so amplitude ordering cannot conceal an unresolved
   spatial template.

## Corrected physics statement

The physics loss places predicted peak displacement and predicted peak damage
jointly into the native-Q4 AMOR mechanical-equilibrium residual. Predicted
damage is not detached. The loss does not contain damage stationarity, the
fatigue-history evolution law, or the complete incremental variational
inequality. A smaller equilibrium objective alone therefore does not establish
better displacement or fracture evolution.

## Review evidence boundary

The reviewer read eight packet files, verified both post-run diagnostic hashes,
and recomputed the projection/clipping counts from 1,000 gradient-log rows.
The packet did not include native arrays, checkpoint, or the full training log;
the reviewer did not access the producer, construct an optimiser, or train.

## Local decision

All required amendments are adopted in protocol v2. No training is authorised
by this review. Protocol v2 must receive `DESIGN_READY_PASS` before local
implementation and synthetic/no-training Code Ready work begins.
