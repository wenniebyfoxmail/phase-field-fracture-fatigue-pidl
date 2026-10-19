# Attempt S09-E017-A005-real-head-adapter-design

- Status: `accepted`
- Created: 2026-10-20T00:20:00+01:00
- Closed: 2026-10-20T00:37:03+01:00
- Type: `real-head-adapter-design-amendment`
- Human decision required: False

## Outcome

The first independent review returned
`E017_REAL_HEAD_ADAPTER_DESIGN_REVISE` with four design blockers. The revised
exact commit `06bf5fef693be5321ce7daf9d2384b8fa3953fde` received
`E017_REAL_HEAD_ADAPTER_DESIGN_READY_PASS`; B1–B4 were closed without reopening
the mapping, data, physics, budget, profiles or no-retry rule.

## Adopted design

- Reconstruct one original three-output linear operation from independent,
  non-aliasing damage and displacement rows.
- Use the same frozen hidden feature `h_i` for all three arms.
- Give D_DIRECT and F_AMP `width+1` parameters each; remove the cancelling
  shape bias so F_AMP_SHAPE has `2*width+1`.
- Treat the F_AMP_SHAPE epsilon seed as an intentional update-0 offset and use
  each arm's actual start for change metrics.
- Distinguish update entered, step returned and complete update committed; keep
  failure evidence independently writable.
- Limit positive and negative claims to the specified adapter, exposed data and
  fixed 64-update procedure.

## Interpretation and next action

This closes a design gate only. Implement a disabled real adapter and synthetic
equivalence/failure tests, then obtain an exact-commit review. Do not read the
real packet/checkpoint, construct the real optimiser, run a model or autograd,
connect to the producer, train, access a holdout or perform rollout.
