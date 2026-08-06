# ChatGPT Pro request: LTPP enriched-input posterior-fit authorization

Please review only whether the completed composite pre-fit gates authorize the
already frozen posterior-fitting and ablation protocol. Do not redesign the
experiment.

## Files

1. v2 base preregistration:
   `docs/experiments/ltpp_geoforecast_enriched_input_preregistration_v2_20260806.md`
2. approved v3 row amendment:
   `docs/experiments/ltpp_geoforecast_enriched_input_preregistration_v3_amendment_candidate_20260806.md`
3. approved v4 prior amendment:
   `docs/experiments/ltpp_geoforecast_enriched_input_preregistration_v4_prior_amendment_candidate_20260806.md`
4. v4 approval receipt:
   `docs/reviews/ltpp_geoforecast_enriched_input_chatgpt_pro_v4_approval_20260806.md`
5. sealed v4 preflight result:
   `docs/experiments/ltpp_geoforecast_enriched_input_v4_prior_preflight_pass_20260806.md`

## Completed gates

- exact 30x11 input coverage: pass;
- fixed LOSO and 24+6 split receipt: pass;
- amendment and approval hashes: pass;
- outcome-free v4 prior predictive: all 28 checks pass;
- observed above-cap fractions: `0.0000`--`0.0040`, gate `<=0.01`;
- outcome likelihood/posterior/held-out enriched prediction/ablation: not run.

The result also discloses rare individual draws up to about `179,895 m` even
though their per-fold frequency remains below the frozen 1% gate. Do not ignore
this fact when deciding authorization; equally, do not retroactively substitute
a new maximum-based gate.

## Required decision

Return exactly one headline:

- `AUTHORIZE_FROZEN_POSTERIOR_FIT`
- `KEEP_NO_FIT_AND_REQUIRE_EXACT_MINIMAL_REVISION`
- `TERMINATE_TRACK_WITHOUT_FIT`

Then answer:

1. Have the composite v2+v3+v4 pre-fit gates been executed as approved?
2. Does passing the frozen frequency-based prior gate authorize the existing
   posterior protocol despite the disclosed rare maxima?
3. If authorized, confirm that no feature, row, split, prior, likelihood,
   sampler, seed, metric, threshold, or ablation-order change is allowed.
4. If not authorized, provide only the smallest required action and state
   whether it requires a newly hashed amendment.

Authorization should cover the frozen posterior fit and sealed evaluation only;
it must not authorize exploratory model switching or claim expansion.
