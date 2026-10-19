# S09-E017 runner integration review round 2

Verdict: `E017_RUNNER_INTEGRATION_REVISE`
Reviewed candidate:
`c14ed37b871840f309be8e82d448412aa62c9886`
Round-1 base:
`1d30506e25fa990460e97c5b9376abee24c4bc92`
Reviewer: ChatGPT Pro, Haofan account
Date: 2026-10-19

## Package identity

- archive:
  `S09-E017-runner-integration-rereview-c14ed37b.zip`;
- size: 50,291 bytes;
- SHA-256:
  `3f91be9eda4be568b417d8f9404e861bc281e44bcb5fa19149082311eee2a8b2`;
- 13 unique safe members; ZIP integrity and all 12 manifest hashes passed;
- commit, round-1 base and reviewed-core identities matched; and
- the five-path diff reconstructed the archived files byte for byte.

## Closure and residual

B1, B3 and B4 were closed.  B2's schema, order, completeness, beta scaling,
sequential projection, clip norms and `F_AMP` S exclusion were also closed.

One residual remained: the validator computed a reference self-dot only when a
projection was applied.  The reviewed core requires this self-dot to be finite
for every reference before deciding whether to skip or apply a projection.
Consequently, a one-component reference immediately above
`sqrt(float_info.max)` could have an overflowing self-dot while all recorded
fields remained finite and no projection was applied.

The minimal repair is to compute and check the self-dot unconditionally, derive
the skip flag from its square root, and reuse it if projection occurs.  The
adjacent finite and overflowing representable values must be a regression
pair.

## Authority boundary

Only this residual validator repair and its synthetic test were authorised.
No numerical-core or scientific-design change was requested.  No scientific
asset read, model forward, optimiser construction, training, SSH/GPU work,
producer launch, holdout, rollout or scientific claim was authorised.
