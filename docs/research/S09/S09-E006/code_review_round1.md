# S09-E006 Code Ready review — round 1

- Conversation:
  `https://chatgpt.com/c/6acc0b4d-ae90-832d-acda-f77f71e770a6`
- Candidate commit: `f6b7cc0`
- Verdict: **CODE_READY FAIL**; no Taobo execution authorised

The reviewer found two execution blockers:

1. global norms and dot products were float64, but projection and direction
   construction still used the original float32 tensors, allowing cancellation
   before the float64 degeneracy test;
2. `clip_grad_norm_(error_if_nonfinite=True)` could raise before the explicit
   arm-local non-finite check, causing an experiment-level failure instead of
   the frozen balanced-arm-local failure.

The repair performs projection, scaling and direction construction fully in
float64 before a checked conversion to parameter dtype.  It also converts only
the specific non-finite total-norm clipping exception into `ArmInvalid` before
any optimizer step.  Regression coverage includes a nearly antiparallel valid
component and an injected clipping failure that leaves the parameter and
optimizer state unchanged.

Nonblocking cautions about downstream evidence assets, denominator guards,
assigned-direction metadata, integration coverage and producer provenance were
retained or strengthened.  The beta values, thresholds and protocol did not
change.
