# S09-E017 numerical-core review round 2

Verdict: `E017_CORE_CODE_READY_PASS`
Reviewed commit: `5ac6b7955b56309ac8ff2fda50b16b2e1669110a`
Review route: ChatGPT Pro, Haofan account
Archive: `S09-E017-core-rereview-5ac6b795.zip`
Archive size: 27,894 bytes
Archive SHA-256: `ab999c0f3fb522aa7df15cc02969adbf60858fab9d2898b06c4d7cde17b9e803`

## Integrity and independent checks

The reviewer verified the exact commit in `MANIFEST.sha256`, all 8/8 content
hashes, CRCs, decompressed lengths and membership. It found no duplicate,
missing, unlisted or unsafe archive member. All content hashes stayed unchanged
during review.

The review independently executed 52 pure-Python classifier/schema checks and
replayed the factorisation and overflow cases through candidate ASTs using a
narrow NumPy float64 adapter. PyTorch and pytest were unavailable in the review
environment, so the reviewer did not describe these checks as native Torch or
autograd validation. The native project evidence remains the local 49-test
PyTorch/pytest run.

## Closed blockers

- **B1:** difference-based tolerance comparison preserves the two
  just-outside-tolerance directions, the inward representable tie and the
  complete A2/S6/R2/P4 boundary profile.
- **B2:** exact A2/S6/R2/P4 widths and bounded integer counts are checked before
  classification. Missing, shortened, extended, fractional, negative,
  out-of-range, boolean, nonfinite and string count cases were rejected.
- **B3:** a positive increment cannot become the legal-zero sentinel; valid
  positive shapes must be nonnegative and weighted-normalised; reconstruction
  must satisfy exact-zero and frozen relative round-trip rules. Genuine zero,
  all-zero-capacity, ordinary `1e-300`, near-zero-capacity and saturation
  controls retain their intended behavior.
- **B4:** nonfinite frozen norms, scaled/projected quantities, geometry,
  preclip/postclip norms, returned diagnostics, reconstruction loss and
  amplitude decision errors fail closed. Clipping can no longer turn an
  overflow into an accepted zero direction.

Ordinary PCGrad controls remained unchanged, including the beta-weighted
three-group direction `[1/12, 1/3]`, the conflict control, the four-group mean
and one final clip.

## Authority boundary

This PASS means only that the isolated float64 numerical core at the exact
reviewed commit is ready to support a separately reviewed no-training
runner/config/evidence integration. It does not authorise a model forward,
scientific-data access, optimiser mutation, training, SSH/GPU operation,
producer launch, holdout, rollout or scientific claim.

