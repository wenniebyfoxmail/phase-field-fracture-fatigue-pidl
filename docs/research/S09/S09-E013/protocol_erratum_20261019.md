# S09-E013 post-run semantic erratum

Date: 2026-10-19

The frozen E013 protocol and raw receipt remain unchanged.  This erratum
corrects two interpretation errors found after the zero-step STOP.

## Cohort semantics

The frozen eight-pair error cohort is defined by the B25 **predicted global
amplitude** margin.  The E013 classifier instead selected rows with
`initial_local_outcome == LOSS` and then compared those identities with the
frozen global-loss set.  The observed cohorts contain eight and 17
complementary pairs.  This classifier mismatch is retained as evidence; it is
not silently repaired or rerun.

The STOP remains supported independently: the recorded L25 pair-specific
direction fails the protected-global-margin condition.

## Pair-specific direction scope

`zero_step_audit` calls `_pair_objectives`, `merge_ranking_gradients`, and
`_adamw_displacement` inside the pair loop.  The receipt therefore stores
`delta_G25,p` and `delta_L25,p` for every pair `p`.  It does not store one
shared G25 displacement and one shared L25 displacement.

The later interpolation is consequently a pair-specific diagonal assay:

`delta_p(lambda)=(1-lambda)delta_G25,p+lambda delta_L25,p`.

Counts across 25 rows tally different hypothetical updates and are not jointly
achievable by one parameter update.  They cannot establish a common Pareto
frontier or rule out a shared scalar mixture/constrained direction.  The
corrected figure and summary state this limitation explicitly.

## Unchanged evidence

- execution status: `ZERO_STEP_DIRECTION_STOP`;
- optimiser steps: zero;
- fresh holdout access: false;
- initial predicted global/local margin signs disagree on 25/25 pairs;
- FEM target global/local pair labels agree on 25/25 pairs;
- stagnant target supports are nonempty;
- no training or retry occurred.
