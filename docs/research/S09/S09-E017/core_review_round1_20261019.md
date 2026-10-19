# S09-E017 numerical-core review round 1

Verdict: `E017_CORE_CODE_REVISE`
Reviewed commit: `0fa5ca33d452eccc8ed56847f1ad3f8906626f5c`
Review route: ChatGPT Pro, Haofan account
Archive: `S09-E017-core-review-0fa5ca33-r2.zip`
Archive SHA-256: `ca1f2ba9f4c562408d6d5fbe1b9c3f54d8decdb6138ee9b8b2ae59bd2f7c2255`

## Review integrity and scope

The reviewer verified the archive size, archive SHA-256, exact candidate commit,
all seven manifest hashes, decompressed lengths, CRCs, member paths and the
absence of duplicate or unlisted content.  It read the source, tests, design
card, prior design review, implementation status, attempt record and review
request.

The review environment did not contain PyTorch or pytest.  It therefore did not
reproduce the 36 native local tests.  It parsed and compiled both Python files,
executed unchanged pure-Python classifier functions and applicable tests through
their ASTs, and independently replayed selected tensor arithmetic using NumPy
float64 and analytical checks.  The reviewer explicitly did not describe this
as native PyTorch or autograd validation.

## Blocking findings and accepted repairs

1. **B1: floating-point tie comparison.**  `_signs` compared `left` with
   `right +/- tolerance`; binary64 rounding can turn a difference just outside
   the frozen tolerance into a tie.  Compute `difference = left - right` once
   and compare it with `+/- tolerance`.  Add both directions, an adjacent value
   inside tolerance and the supplied complete-profile regression.
2. **B2: malformed protected evidence.**  The classifier did not enforce the
   frozen `A2/S6/R2/P4` widths.  Its own fixture supplied only P2.  It also
   accepted fractional, negative or out-of-range pair-mismatch and
   undefined-shape counts.  Require exact widths, integer-valued A counts in
   0--25 and S counts in 0--16 before profile calculation; correct the fixture
   to P4 and add rejection tests.
3. **B3: near-zero factorisation.**  A positive increment could underflow to
   the same sentinel as a genuine zero event, or produce a positive amplitude
   with a non-normalised effective shape.  Preserve the E016 strict-zero
   contract: positive input requires positive amplitude, positive-amplitude
   shape mass must equal one under the frozen tolerance, and decoded
   reconstruction must meet the frozen relative and exact-zero round-trip
   rules.  Reject invalid representations without adding an epsilon or silently
   renormalising the shape.
4. **B4: derived nonfinite arithmetic.**  Finite inputs could produce infinite
   norms, dots, losses or decision errors.  A nonfinite preclip norm could then
   yield a zero clipping factor and a falsely finite zero direction.  Check
   frozen norms, scaled/projected vectors, pairwise/projection geometry,
   preclip norm before clipping, postclip diagnostics, reconstruction loss and
   amplitude decision errors.  Failing closed is sufficient.

## Findings that remain closed

The reviewer confirmed that beta is applied after update-zero scale
normalisation, PCGrad uses unmodified scaled references, the active-group mean
is correct, F_AMP excludes S, and clipping occurs once.  Signed pair regression,
mass-entry seeding, capacity masking and ordinary zero semantics were also
accepted.

The three exposed choices remain compatible with the approved design at this
scope: `A_B25 * exp(r)`, equal internal shape-term weights and a supplied
positive reconstruction-scale interface.  The actual scale identities and
values remain a runner/config obligation.

## Optional observations

The reviewer suggested documenting that `decision_shape_values` accepts
error-oriented inputs, persisting projected vectors in the later evidence
layer, and adding a decoded update-zero bound regression.  These were explicitly
labelled optional rather than blockers.

No model, data, optimiser, training, holdout, rollout or producer execution was
authorised by this review.
