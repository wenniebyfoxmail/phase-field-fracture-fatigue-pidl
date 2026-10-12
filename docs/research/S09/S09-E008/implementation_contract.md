# Stage 0A implementation contract before Code Ready

This contract implements only the Design Ready Stage 0A/P0/P1 scope. It does
not authorise scientific-array decode, training, Stage 0B or rollout.

## Fixed transition set and ranking conventions

- Eligible cycles are exactly integer cycles 1--73 after all six state keys
  `s00..s05`, payload hashes, decoded supports and causal identities pass.
- Rank cycles by `(g_k, cycle_id)` in ascending order. Chronological bands are
  the inclusive sets 1--24, 25--49 and 50--73.
- The upper quartile is the highest `ceil(N/4)` ranked cycles. Its median is the
  middle value for odd cardinality and the arithmetic mean of the two middle
  values for even cardinality.
- The deterministic 16-cycle selection and the growth/near-stagnant memberships
  are serialized before model construction. Any nonfinite value, duplicate or
  group-count failure gives `P1_NOT_READY`.

## Supports, weights and floating-point convention

- All decoded scientific fields must be IEEE-754 float64. Conversion from a
  different stored dtype is a capability failure rather than an implicit cast.
- Nodal weights are the frozen Q4 lumped areas computed from the native
  connectivity, shape functions, Gauss weights, Jacobian determinants and
  thickness. GP weights are `det(J) * gauss_weight * thickness` on the same
  native element/GP order. Each metric divides by the sum of weights on its own
  support.
- For a finite float64 value `x`, half-ULP is
  `0.5 * min(nextafter(x,+inf)-x, x-nextafter(x,-inf))` using the positive
  finite spacings. Zero uses half the least positive float64 subnormal. The
  export-resolution aggregate follows the formula in `experiment.md`.
- Damage and history targets are `s04-s00` increments. Displacement targets are
  absolute `s04` nodal components after the same hard boundary lifting used by
  the model.
- Each RMS normaliser is `max(teacher_RMS, half_ULP_RMS, float64.tiny)` and must
  be finite and strictly positive. Values, hashes and formulas are recorded
  before model initialisation.

## Initial and final judgement

- Seed, parameter initialisation and data order are fixed in the future code
  protocol. `L_judge_initial` is evaluated after construction and before the
  first optimiser call or state mutation.
- `L_judge_final` is evaluated after the last permitted update in evaluation
  mode on the identical 16 examples, weights and normalisers.
- Gradient-balancing weights, conflict projections, optimiser moments and
  physics residual scales never enter `L_judge`.

## State-sufficiency audit

The provisional carried state is nodal `d` plus GP
`(H, alpha_bar, q_prev, f)`. The prescribed input is the complete known load
path. Frozen context must include native geometry/quadrature, material
constants, boundary masks and producer update law. Before Code Ready, source
review must decide whether displacement, undegraded energy or any staggered
old-state variable is a physical carried state, a solver initial guess, or
causally reconstructible. An unresolved variable gives
`STATE_SUFFICIENCY_BLOCKED`; it cannot be silently omitted or supplied from the
target.

## Multi-objective code-review gate

The future code review must freeze the exact gradient-norm scaling, conflict
projection order, zero-gradient handling, clipping and optimiser-update order.
The three reported objectives remain nodal-state data, GP-history data and
peak equilibrium. Their individual raw/scaled losses and gradients must be
logged. Hard constraints and fixed P1 acceptance metrics remain separate.
