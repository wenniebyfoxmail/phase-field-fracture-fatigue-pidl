# ChatGPT Pro review request: LTPP enriched-input v4 prior amendment

Please review this as a bounded post-gate amendment, not as a request to redesign
the experiment.

## Files to review

1. v2 base preregistration:
   `docs/experiments/ltpp_geoforecast_enriched_input_preregistration_v2_20260806.md`
   (`3b93cdb71be7c32ea6a7524d14ab2b3d3a619a13fcbed9be596d9e2d5c824992`)
2. approved v3 row amendment:
   `docs/experiments/ltpp_geoforecast_enriched_input_preregistration_v3_amendment_candidate_20260806.md`
   (`f2490cd99b07912567ab52aabcf2ba9472b9514de3dd0fe1c1b1bba4e85ec70d`)
3. v3 gate result:
   `docs/experiments/ltpp_geoforecast_enriched_input_v3_prior_predictive_blocked_20260806.md`
4. proposed v4 prior amendment:
   `docs/experiments/ltpp_geoforecast_enriched_input_preregistration_v4_prior_amendment_candidate_20260806.md`
   (`d8fa9840581b1aa0ad9a19a11bd892fdf3ac6d5325ecacb1454f2c9a7f955565`)

## Facts that must not be reinterpreted

- V2 terminated at input coverage without prior prediction or fitting.
- V3 froze a complete 30x11 source-only input table.
- The original fixed priors then failed all 28 prior-predictive checks, with
  8.2%--27.8% above the physical cap versus an allowed maximum of 1%.
- No outcome fields have been read by the enriched-input code. No posterior,
  held-out enriched prediction, or ablation score exists.
- The v4 candidate was written without simulating or comparing alternative
  replacement prior sets.

## Required decision

Please return exactly one headline:

- `APPROVE_V4_PRIOR_PREFLIGHT_ONLY`
- `REVISE_V4_BEFORE_PREFLIGHT`
- `REJECT_V4_AND_KEEP_TRACK_BLOCKED`

Then answer only these questions:

1. Is one externally reviewed prior amendment scientifically admissible after
   a transparent prior-predictive failure but before any outcome fitting?
2. Are `Normal(0,1)`, `Normal(0,0.1)`, `HalfNormal(0.5)`, and
   `HalfNormal(0.5)` sufficiently justified by the disclosed model scale and
   fixed predictor geometry, or is any scale still arbitrary in a way that
   creates material researcher degrees of freedom?
3. Does applying the same amended priors to all M0--M3 models and folds preserve
   matched ablation comparisons?
4. Does the one-run terminal rule adequately prevent iterative prior tuning?
5. Is any additional change strictly required before rerunning the
   prior-predictive check?

If revision is required, give the smallest exact replacement text only. Do not
recommend new features, models, thresholds, rows, datasets, or outcome
inspection. Approval must authorize only the amended prior-predictive preflight,
not posterior fitting.
