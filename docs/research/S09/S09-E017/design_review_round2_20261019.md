# S09-E017 design review closure

Reviewer: ChatGPT Pro, Haofan account  
Date: 2026-10-19  
Final reviewed commit: `07b66e1df22d6e44d01780003e0b539b0f5886fa`  
Final verdict: `E017_DESIGN_READY_PASS`

## Review sequence

The first narrow rereview bound to
`d175e72322d4f7402a9973ca1920e96e0478bbc5` closed R1-R4 and the R5
comparison and causal principles. It retained one blocker because the review
message summarised, but did not reproduce, the actual profile predicates.

The next candidate, `cf711184`, supplied executable update-64 predicates,
explicit start/change/terminal comparisons and legal zero-amplitude shape
handling. The reviewer confirmed that the missing-predicate issue was closed
and found two residual edge cases:

1. strict mutual non-dominance also included completely tied change vectors,
   incorrectly labelling an all-tie outcome as a mixed trade-off;
2. ordinary hazard log-ratio was undefined for a legal zero decoded amplitude,
   so the amplitude decision vector and subsequent differences could become
   nonfinite.

Commit `07b66e1df22d6e44d01780003e0b539b0f5886fa` applied the smallest fixes. `VALID_MIXED_TRADEOFF` now
requires either within-arm strict improvements and worsenings or an inter-arm
change-gap with at least one strictly positive and one strictly negative
component. The amplitude decision now uses the already frozen zero-compatible
scaled-log error
`abs(log1p(A_eff/A_scale)-log1p(A_FEM/A_scale))`; raw ordinary log-ratio stays
a diagnostic with `predicted_zero` NA semantics and does not trigger execution
invalidity.

## Independent final check

ChatGPT Pro substituted the all-zero change-vector counterexample and confirmed
that both mixed-tradeoff branches are false. It also substituted zero effective
amplitude into the scaled-log decision error and confirmed finite amplitude
errors, pair mismatches, own-start changes, terminal gaps and change gaps.

The final response began `E017_DESIGN_READY_PASS` and explicitly bound exact
commit `07b66e1df22d6e44d01780003e0b539b0f5886fa`. It stated that both residual counterexamples were closed and
no blocker remained in the design-review scope. R1-R4 and the remainder of R5
stay closed.

## Authority boundary

This PASS makes E017 ready only for local no-training implementation planning.
No model forward, autograd, optimiser mutation, training, SSH/GPU launch, new
data or FEM access, holdout access, rollout, longer budget or scientific claim
is authorised by this review.
