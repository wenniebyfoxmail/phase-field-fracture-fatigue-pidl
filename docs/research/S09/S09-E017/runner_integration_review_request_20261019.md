# S09-E017 static runner/config/evidence review request

Review the exact commit and supplied manifest as a static, no-I/O integration
candidate over the already reviewed numerical core commit
`5ac6b7955b56309ac8ff2fda50b16b2e1669110a`.  Do not infer behavior from an
unattached repository state.

Please independently check:

- exact three-arm order, active objectives and trainable/frozen parameter-class
  declarations, including the diagnostic-only withheld S gradient in `F_AMP`;
- shared initial-state/seed declarations and the requirement that no optimiser
  object, state entry or step exists at this gate;
- the 64-per-arm/192-total budget, exact evaluation set and update-64-only
  terminal voting;
- A2/S6/R2/P4 widths, finite lower-better values and bounded integer counts;
- raw/scaled/projected gradient schema, beta=0.25, complete pairwise geometry,
  vector consistency and required update diagnostics;
- first-stop precedence, whole-run stop, persistent write-once failure receipt,
  last-complete preservation and no retry or alternate GPU;
- fixed figure selection and shared physical colour scale, including the
  colourbar-versus-right-edge-field distinction; and
- whether the source or config contains any path to scientific data access,
  model forward, autograd, optimiser construction/mutation, SSH or GPU work.

Return one top-line verdict:

- `E017_RUNNER_INTEGRATION_CODE_READY_PASS`, or
- `E017_RUNNER_INTEGRATION_REVISE` with concrete blockers and a minimal
  counterexample or test where possible.

A PASS authorises only preparation of one final, separately reviewable run
package.  It does not authorise asset access, model forward, training, SSH/GPU
preflight, producer launch, holdout, rollout or a scientific claim.
