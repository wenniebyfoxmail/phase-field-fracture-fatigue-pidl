# S09-E017 factorised numerical-core review request

Review the exact commit and attached files as an isolated no-training numerical
core against the design-approved E017 card.  Do not infer behavior from an
unattached repository state.

Please check:

- whether the capacity-supported seed, stable learnable shape and bounded
  decoder preserve nonnegativity, weighted normalisation, irreversibility and
  `d_peak <= 1`, including nonzero sensitivity where B25 initially has no mass;
- whether the effective decoded-field factorisation and zero-amplitude semantics
  match the common E016 observables without inventing a shape;
- whether the amplitude, shape and reconstruction objectives implement the
  frozen loss meaning, including signed reverse pair contrasts;
- whether PCGrad applies the physics weight `beta=0.25` after scale
  normalisation, projects against unmodified references, uses the active-group
  mean and one clip, and records enough geometry to audit conflicts;
- whether the update-64 classifier implements the reviewed Pareto/tie rules,
  especially all-tie versus mixed-tradeoff and zero-amplitude cases;
- whether `A_B25*exp(r)`, the equal internal shape-term weights and the
  precomputed reconstruction-scale interface are acceptable at core scope or
  require a design amendment; and
- whether any code path exceeds this local pure-core boundary.

Return one top-line verdict:

- `E017_CORE_CODE_READY_PASS`, or
- `E017_CORE_CODE_REVISE` with concrete blocking findings and a minimal
  counterexample or test where possible.

A PASS authorises only a later no-training runner/config/evidence integration
candidate.  It does not authorise model forward, scientific-array access,
training, optimiser mutation, SSH/GPU launch, fresh holdout, rollout or a
scientific claim.

