# S09-E016 implementation review round 1

Reviewer: ChatGPT Pro, Haofan account  
Reviewed commit: `1a68a73ee101d14b05ca5671aa4b39ee77948e0b`  
Design baseline: `68e47e543630efea45c67690e8842baed219500c`  
Verdict: `E016_IMPLEMENTATION_REVISE`

The reviewer accepted the default factorisation path: no positive capacity
cutoff, representable `q_max`, `log1p`/`expm1`, strict zero events, positive
quadrature weights, and separate `r`, `r_eff`, and `r_hat` evidence. It found
six blocking groups, all reproducible with synthetic data and none requiring
access to the real experiment arrays:

1. The inherited local bridge used capacity-clipped increments rather than the
   frozen raw FEM support and nonnegative raw candidate increments. A permitted
   near-boundary perturbation could flip the contrast sign.
2. Optional pair availability incorrectly depended on all 16 cycles rather
   than the ten cycles used by the frozen 25 growth/stagnant pairs.
3. The readiness evidence did not explicitly gate all computed shape metrics;
   the cosine formula could overflow for extreme positive weight ratios. A25
   scalar rows also lacked finite/nonnegative validation, and positive log
   ratios divided before taking logs.
4. Legal non-readiness cases, especially `C_F` empty, did not retain a complete
   decision package; some prose could still recommend E017 after a numerical
   readiness failure.
5. The output validator did not compare complete CSV/JSON/NPZ scientific
   content and did not re-lock the two frozen source hashes at closure.
6. The clipping-bound check used the permitted `2*eps_float64*c` allowance but
   did not persist the analytic upper bound and roundoff slack arrays.

Optional wording fixes were to name the three-arm bridge as weighted-mean
absolute increment, label zero-event shape panels as undefined, and distinguish
hazard-shape mass diagnostics from physical-increment mass.

## Narrow repair implemented for rereview

- Restored raw support and raw nonnegative local-bridge semantics.
- Restricted optional pair prerequisites to the frozen pair cycles.
- Added scaled weighted cosine, derived-metric finite checks, full A25 scalar
  validation, stable log ratios, and stable scaled-hazard evaluation.
- Split `audit_valid` from `shape_target_ready`, retained the all-zero FEM
  result path, and conditioned JSON/Markdown/README routing on the same state.
- Added exact CSV/JSON/NPZ content checks, dtype/shape checks, rendered-figure
  checks, and source-hash closure checks.
- Persisted per-node clipping analytic upper bounds and roundoff slack, and
  reported their maxima and formula.
- Added focused synthetic regression tests for each executable counterexample.

No experiment arrays were read and no model forward, training, gradient,
optimizer, FEM, or holdout action occurred while closing this review.
