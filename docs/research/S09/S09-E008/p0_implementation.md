# Stage 0A synthetic P0 implementation

## Implemented scope

The synthetic-only prototype has separate nodal and Gauss-point encoders.
Fixed native-Q4 interpolation carries nodal features to GP support; consistent
weighted assembly carries GP features back to nodes. Two local integral blocks,
one coarse block and a fine skip produce nodal peak damage/displacement and GP
history proposals.

Hard reconstruction provides peak displacement boundary values, damage bounds
and irreversibility, `alpha_bar` monotonicity and exact `f(alpha_bar)`. `H` and
`q` remain unconstrained pending exact producer semantics. Raw increment losses
remain available behind the hard projections.

The code exposes separate nodal-state, GP-history and peak-equilibrium
objectives. Its fixed P1 judgement function is the reviewed equal three-group
metric and has no argument for adaptive objective weights.

## Local synthetic verification

- 52 focused S09 tests passed.
- `P0_SYNTHETIC_PASS` on a deterministic 3x3-node/four-Q4 fixture.
- zero increment, hard boundary, damage/alpha/Carrara constraints passed;
- all 50 trainable parameter gradients were finite and nonzero in the
  differentiation probe;
- optimizer steps: 0; scientific arrays opened: false.

This is wiring evidence only. Exact Code Ready review is pending. Scientific
packet decode, training, Stage 0B and all predictive/physics claims remain
blocked.
