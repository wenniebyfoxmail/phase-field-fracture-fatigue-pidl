# S09-E017 first-principles pilot design review request

Review the exact commit named in the submission, focusing on whether the
proposed P0 experiment can distinguish head representation, objective conflict
and state/trunk insufficiency without overstating its physics.

Check these points:

- the function-to-function operator mapping and the exact boundary of the
  `beta=0.25` native-Q4 AMOR free-DOF equilibrium term;
- whether `F_AMP` is a true amplitude-only ablation with `S` bitwise frozen;
- whether the step-0 bridge and bounded mass-entry construction make all three
  arms comparable;
- whether PCGrad is applied and logged so that amplitude, shape,
  reconstruction and equilibrium conflicts remain visible;
- whether 64 updates per arm and the graded profile criteria are the cheapest
  informative first gate;
- whether any criterion silently collapses a mixed but useful result into
  failure or permits an unjustified PINO, holdout, rollout or physical-truth
  claim.

Return one top-line verdict:

- `E017_DESIGN_READY_PASS`, or
- `E017_DESIGN_REVISE` with concrete blocking findings.

This is a static design review. It does not authorise model forward, autograd,
optimiser mutation, training, SSH/GPU launch, new data, FEM work, holdout or
rollout.
