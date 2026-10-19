# S09-E016 design review round 1

Verdict: `REVISE_AND_REREVIEW`.

Reviewed exact design commit:
`84b15d8ae8a15b06a74229a503d722ea36940d0e`.

Review channel: Haofan account, ChatGPT Pro, same S09 review conversation.
The reviewer used symbolic derivation and artificial float64 counterexamples;
it did not read the experiment arrays or run a model, gradient, optimiser, FEM,
holdout, or A25 export.

## Blocking findings

1. A positive event at a small positive remaining capacity could be discarded
   by an unfrozen positive `epsilon_c`, become `A=0`, and still pass a loose
   absolute round-trip tolerance. Freeze `capacity cutoff=0`,
   `q_max=nextafter(1,0)`, strict `A==0` semantics, stable `log1p`/`expm1`, and
   compare numerical reconstruction with the encoded increment using
   `rtol=64*eps_float64`, `atol=0`. Report saturation clipping separately.
2. "Enough nonzero cycles" did not identify whether it meant nonzero FEM
   targets or jointly nonzero FEM/B25 fields. Freeze `C_F`, `C_B`, and `C_J`;
   require a nonempty, computable FEM target set for shape readiness, and mark
   B25-vs-FEM shape metrics NA outside `C_J` without invalidating a legal zero
   baseline.

## Other conclusions

The capacity-aware hazard factorisation is mathematically valid under the
revised numerical contract. The A25 scalar-only boundary is honest: A25 may
join only a like-for-like weighted-mean absolute-increment bridge and cannot be
assigned a hazard amplitude, shape, centroid, or latent-amplitude pair score.
The proposed metrics are sufficient for a readiness audit after their domains
and zero-denominator handling are explicit.

The reviewer proposed an amplitude-first ordering whenever every FEM nonzero
cycle also has a defined B25 shape. The local decision modifies this optional
route advice: the user authorised explicit amplitude/shape separation, E015
already measured both amplitude and localisation failures, and the updated
project workflow requires a decision-scale test of the binding representation
hypothesis. E017 will therefore compare a dual-head candidate with an
amplitude-only ablation; this choice is independent of E016 metric magnitude.

No execution is authorised by this review. The v2 protocol needs one narrow
rereview of the two blocker closures before the exact implementation review.
