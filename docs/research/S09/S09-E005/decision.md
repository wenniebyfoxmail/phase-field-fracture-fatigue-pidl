# S09-E005 decision

## Verdict

**Execution and diagnostic evidence completeness passed.  The measured
mechanism is strong gradient-scale dominance with localized decoder conflict.**

Independent ChatGPT Pro Evidence Ready review passed after independently
recomputing the per-state results from the corrected raw-evidence archive.

The global physics/data gradient norm ratio across the 16 frozen states was
10,165–57,338 (median 22,664).  All global cosine similarities were positive
(0.138–0.882; median 0.491).  Therefore the common checkpoint does not show a
global negative-gradient conflict.

The decoder tells a narrower story: 6/16 states had negative cosine, with a
minimum of -0.816.  This is a real local conflict and motivates a data-anchored
projection guard, but it does not explain the whole model as globally
conflicting at step 300.

## Link to E004

Multiplying by E004's nominal initial weight 0.01 still leaves the physics
component 102–573 times larger than the data component (median 227).  At the
first assessment weight 0.016309 it is 166–935 times larger (median 370).
Consequently, the apparently small scalar weight did not create a balanced
objective in parameter-gradient space.

Every tested direction was a first-order descent direction for both losses on
all 16 individual states at the frozen checkpoint.  E004's later development
accuracy degradation therefore cannot be attributed to an instantaneous
global negative cosine at this one checkpoint.  Scale dominance together with
optimizer, clipping, curvature and subsequent trajectory effects remains the
leading explanation to test.

## Target residual diagnostic

The exported FEM target's observed free-force RMS was 0.000086–0.0266 times
the affine residual (median 0.0199), whereas the common-checkpoint prediction
was 34.2–61.1 times affine.  This does not support a large target/operator
residual floor.  It is an observed residual under this frozen discretization,
not a proof of an irreducible minimum or of original FEM convergence.

## Next experiment

Open S09-E006 as a fresh, reviewed Pareto-rescue experiment.  Use gradient
normalization to make the physics contribution a declared fraction of the data
gradient norm and project away any component that opposes the data gradient.
Compare a very small predeclared set of balance ratios from the exact common
checkpoint and sequence.  Preserve the provisional joint feasibility rule:
at least 50% development residual reduction versus data only while no
development state's displacement error is more than 10% worse than data only.

This decision does not alter E004's failure and does not yet show that any
multi-objective training method succeeds.
