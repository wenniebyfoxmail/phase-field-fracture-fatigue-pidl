# Next solution proposal: explicit paired loss control and abstention

Proposal only. No extra fit, threshold sweep, validation arm or fresh access was
executed under E006. E003 remains the deployed research baseline.

The required behavior is still additional actual detections at the same FP
budget while retaining at least 95% of previously detected target identities.
Preserving the fallback bank does not by itself preserve emitted detections.
An original-versus-correction local-validity comparison can replace a useful
original whenever the two uncalibrated scores disagree; conflict filtering only
limits overlap with other parents, not harm to the parent's original target.

The next bounded solution should make that parent-specific loss explicit:

1. Reuse the fixed train-location crossfit corrections and both spatial crops;
   derive **paired** labels for original-valid/correction-invalid (harm),
   original-invalid/correction-valid (gain), both valid and neither valid.
   Keep GT out of inference. Original-valid status must be a separate protection
   target, rather than disappearing into two independent binary crop scores.
2. Fit one paired decision head that uses both variants and their geometry
   change. Its policy must have an original/abstain outcome. Qualify harm risk and
   gain on held train locations with the same conditional-encoder limitation;
   freeze the acceptance rule entirely from those train folds. Do not select
   margins or displacement caps against the reused development failures.
3. Emit a correction only when its held-train-qualified harm-risk bound passes
   and predicted gain is positive; otherwise emit the original unchanged.
   Displacement/scale features expose large changes to the policy. Original
   parent count and E003 ordering remain fixed for a clean bounded comparison.
4. Freeze exactly one resulting policy, numerical checks, 4-fold fitting budget,
   the same +.05 recall and .95 retention co-primary standard, and test firewall;
   obtain independent 5.6-sol / Medium review before fitting. A train qualification
   failure stops without development access or widening the rule.

This is a concrete attempt to reduce erroneous replacement, not proof that it
will work. A low replacement rate can protect originals while producing no gain;
that would be useful protection progress but not success for the joint claim.
If qualified correction gains remain too rare, the next decision is to invest
in a genuinely more informative localisation model/data, rather than repeatedly
loosening the selector or the result standard. No E007 is registered or executed
by this proposal.
