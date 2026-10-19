# S09-E017 runner integration focused rereview

Review the manifest-bound revised exact commit only for the round-2 residual:
the unconditional projection-reference self-dot finite check.  B1, B3, B4 and
all other B2 repairs remain closed.  The reviewed numerical core and scientific
design remain closed.

Please verify:

1. every projection reference computes a finite self-dot before skip/apply,
   including when `projection_applied=False`;
2. the skip flag is derived from the checked self-dot using the core's
   `sqrt(denominator) <= 1e-12` rule; and
3. `sqrt(float_info.max)` remains accepted while its next representable value
   toward infinity is rejected because its explicit one-component self-product
   overflows.

The source may write only the canonical write-once failure-metadata receipt.
It must retain no scientific reader, model forward, autograd, optimiser
construction/mutation, subprocess/network, SSH/GPU or producer route.

Return first line exactly one of:

- `E017_RUNNER_INTEGRATION_CODE_READY_PASS`
- `E017_RUNNER_INTEGRATION_REVISE`

A PASS authorises only preparation of a separately reviewed final run package.
It does not authorise scientific-asset reads, model forward, optimiser
construction, training, SSH/GPU work, producer launch, holdout, rollout or a
scientific claim.
