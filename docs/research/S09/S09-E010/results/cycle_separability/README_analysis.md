# S09-E010 no-training cycle-separability audit

## Question

Why did adding the support and amplitude objectives fail to improve the frozen
growth-versus-stagnant ranking?  This audit distinguishes two explanations:

1. the operator can express cycle-specific damage responses, but the
   multiobjective merge suppresses their useful directions; or
2. the current damage output behaves as an almost one-direction response across
   cycles, so reweighting similar losses cannot create the missing variation.

The audit replays the common initial state and all three update-500 checkpoints
on the same 16 development examples.  It computes weighted damage-increment
field geometry and per-cycle parameter gradients for `L_D`, `L_S`, `L_A`, and
`L_P`.  It creates no optimizer, performs zero updates, and accesses no new
holdout.

## Initial SVD result

The SVD audit found strong output compression and objective redundancy, but a
focused pair-contrast check was required before assigning the cause to the
head.

| state | centred effective rank of predicted `Delta d` | first-mode energy | growth/stagnant contrast-to-within ratio |
|---|---:|---:|---:|
| initial common state | 0.000 | 0.000 | n/a |
| A25 update 500 | 1.280 | 0.951 | 0.353 |
| B25 update 500 | 1.130 | 0.978 | 0.335 |
| B0 update 500 | 1.341 | 0.940 | 0.398 |

The update-500 damage increments therefore occupy an almost one-dimensional
cycle-varying subspace.  Their growth/stagnant centroid difference is also less
than 0.4 of the within-group RMS variation in every arm.

The added objectives do not introduce independent cycle geometry:

- `L_A` gradient effective rank is 1.000 in A25, B25, and B0.
- `L_S` gradient effective rank is 1.002, 1.000, and 1.059 respectively.
- At B25 update 500, the growth/stagnant contrast directions of `L_S` and `L_A`
  have cosine 0.995 and 0.996 with the `L_D` contrast direction.
- At the common initial state, predicted `Delta d` is identically zero and the
  absolute-amplitude objective has a zero gradient.  This is the zero
  subgradient of `abs(Delta d)` at the origin, rather than evidence that the
  target amplitude is already correct.
- `L_P` supplies a geometrically different direction (median per-cycle
  `L_D`-versus-`L_P` cosine is 0.073 at B25 update 500), but its cycle-centred
  effective rank is only 1.241.  This agrees with the producer result: beta
  0.25 controls equilibrium without improving amplitude ranking.

## Focused pair-contrast self-check

Low rank alone cannot distinguish a missing ranking objective from an
insufficient head.  A rank-one Jacobian can still repair every pair if the row
coefficients differ.  The follow-up audit therefore evaluated the exact 25
growth-versus-stagnant amplitude margins at the B25 update-500 checkpoint and
their direct parameter Jacobians `J_g - J_s`.

All eight misordered pairs are `{58,60,69,70} x {3,4}`.  Their contrast
Jacobians are finite and nonzero:

- median `||J_g-J_s||` is `2.969e-3`;
- median contrast norm is 12.10% of the RMS norm of the two source rows;
- the first-order minimum parameter displacement needed to reach zero margin
  is only `5.23e-5` of the already observed initial-to-B25 parameter
  displacement;
- the current mean B25 descent direction *decreases* the margin for all eight
  wrong pairs, while it increases all 17 already-correct margins; its cosine
  with each wrong-pair contrast is approximately `-0.988`.

This changes the causal priority.  The current head has local first-order
capacity to repair the wrong margins, even though that capacity is almost
one-dimensional.  The current objective/merge points that direction the wrong
way for exactly the eight errors.

## Decision

Do not run another beta or scalar-weight sweep, and do not change the head yet.
The next minimal controlled experiment should keep the current operator and
beta 0.25 physics term, then add an explicit cross-cycle pairwise/listwise
amplitude-ranking objective.  Compare it against a compute-matched continuation
of B25 from the same checkpoint.  This isolates objective repair from capacity
repair.  A factorized nonnegative `amplitude x normalized support` head remains
the next contingency only if the ranking objective has usable zero-step
gradients but still cannot repair margins without unacceptable field or physics
cost.

## See / Therefore / Does not show

**See.** Predicted increments across all 16 cycles are nearly collinear, while
the `L_S` and `L_A` gradients are essentially rank one and their
growth/stagnant contrast aligns with `L_D`.  `L_P` remains the only clearly
different objective direction.

**Therefore.** E010 was a useful negative result: it rules out simple addition
of per-cycle support/amplitude MSE under the current merge as a sufficient
repair.  The focused audit shows that the next intervention should be an
explicit pair-ranking objective before a head redesign.  The field plots still
explain why A25 can look good while missing new crack growth: most visible
structure is inherited from `d_pre`.

**Does not show.** This read-only audit does not prove that every neural
operator architecture lacks the needed state, does not test unseen trajectories,
and does not establish a full fracture PINO.  The proposed factorized head and
ranking objective remain an untrained design hypothesis.

## Files

- `cycle_separability_receipt.json`: complete identities, matrices, cosines,
  singular values, and zero-step statement.
- `cycle_separability_summary.csv`: compact numeric table.
- `S09-E010-R001-cycle-separability-summary.{png,pdf}`: rank and group-separation
  summary.
- `S09-E010-R001-cycle-gradient-gram.{png,pdf}`: 16-by-16 output/gradient cosine
  matrices for all four parameter states.
- `B25_update500_pair_contrast_jacobian_receipt.json`: exact 25-pair local
  sensitivity audit and checkpoint identities.
- `B25_update500_pair_contrast_jacobian.csv`: one row per frozen pair.
- `S09-E010-R001-B25-pair-contrast-jacobian.{png,pdf}`: current margins and
  relative pair-contrast sensitivities.
- `scripts/analyse_s09_e010_cycle_separability.py`: reproducible read-only audit.
- `scripts/analyse_s09_e010_pair_contrast_jacobian.py`: focused pair audit.
