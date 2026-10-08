# State Measurement And Inverse Adapter

Read this reference for crack identification as measurement, topology or
metrology, multimodal representations, latent-state inference, phase-field or
material inversion, and data assimilation.

## Define The State Claim

Separate these questions:

1. Can the current observable quantity be measured?
2. Can an internal or latent state be inferred from allowed observations?
3. Is the inferred state sufficient for a declared downstream transition?

A trainable parameter or reconstructable image is not automatically an
identifiable physical state. A surface crack mask does not uniquely determine
phase field, energy, material parameters, fatigue history, or moisture.

Freeze allowed observations, nuisance variables, parameter/state bounds,
symmetries, priors, observation operator, reference uncertainty, and the
independent axis used to test identifiability. Fit and evaluate by physical
specimen/site grouping; augmentations, pixels, nodes, or windows from one unit
are not independent evidence.

## Smallest Primary Criterion

Use the criterion that directly matches the bounded claim:

- measurement/metrology: independent-reference error or decision loss;
- representation/token: held-out sufficiency for one frozen probe or transition
  relative to a simpler representation, without changing the downstream model;
- inverse parameter/state: posterior predictive consistency or recovery under
  independently varied conditions, not training loss alone;
- assimilation: incremental future-state or transition value over the same
  observation-only baseline.

When multiple parameter combinations yield observationally equivalent outputs,
report non-identifiability or a bounded posterior/set rather than one recovered
truth. Synthetic recovery demonstrates recovery from that generator only.

## Stop Rules

Stop escalation when a cheaper sensitivity/rank/profile-likelihood test shows
the target is not identified, when repeatability is larger than the proposed
effect, or when the representation fails the frozen simple probe. Do not rescue
the claim with joint fitting, more latent dimensions, or a new architecture
after viewing the result.
