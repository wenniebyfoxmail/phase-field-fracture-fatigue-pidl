# ChatGPT Pro review request: LTPP enriched-input v3 amendment

Please review these four files in order:

1. `docs/experiments/ltpp_geoforecast_enriched_input_preregistration_v2_20260806.md`;
2. `docs/experiments/ltpp_geoforecast_enriched_input_freeze_blocked_20260806.md`;
3. `docs/experiments/ltpp_geoforecast_enriched_input_preregistration_v3_amendment_candidate_20260806.md`;
4. `docs/experiments/ltpp_geoforecast_enriched_input_track.md`.

V2 was externally approved for input freeze and then stopped before any
prior-predictive or outcome fit because one exact traffic construction-year
join was absent. V3 proposes only one fixed input-driven change: remove the
named transition `06-2041-T01` and execute every model on the same remaining 30
rows.

Please act as a strict Registered Report Stage 1 reviewer and answer:

1. Is the fixed named exclusion scientifically acceptable when its outcome was
   already present in an earlier geometry benchmark, although no enriched model
   was fitted or scored?
2. Does the amendment leave any opportunity to remove further rows, change
   traffic alignment, impute ESAL, or choose among rescue rules after results?
3. Are the new split sizes and the exact 26--28 coverage count correct for 30
   pooled predictions?
4. Is it valid to retain the same endpoint, 11 features, model, priors, seeds,
   10% MAE, four-of-six, and 5% CRPS gates?
5. Must this be labelled a separately reviewed sensitivity experiment rather
   than an untouched confirmatory continuation?
6. Does approval require a replacement independent section instead of the
   fixed 30-row set?

Return exactly one design status with the minimum necessary reason:

- `APPROVE_V3_30_ROW_INPUT_FREEZE`;
- `REVISE_V3_BEFORE_INPUT_FREEZE`; or
- `REJECT_V3_CONFIRMATORY_RESCUE`.

If revision is required, give only the minimum revision set. Do not recommend
architecture search, alternative algorithms, outcome-driven row selection, or
multiple traffic imputations.

Approval authorizes input freeze and prior-predictive preflight only. It does
not authorize posterior fitting or ablation scoring.
