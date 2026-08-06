# ChatGPT Pro review request: LTPP enriched-input preregistration v2

Please review the attached preregistration as a **confirmatory small-sample
forecast experiment**, not as an invitation to search for a better-performing
algorithm:

`docs/experiments/ltpp_geoforecast_enriched_input_preregistration_v2_20260806.md`

Context already frozen:

- six LTPP sections, 37 adjudicated states, and 31 transitions;
- LOSO is the primary unseen-section axis;
- six last transitions are a frozen secondary future-time axis;
- persistence remains the honest point baseline after the previous
  geometry-plus-realized-climate challenger worsened unseen-section length
  error by 15.63%;
- the new plan tests source-available traffic, structure, and FWD information,
  not another architecture rescue.

Please return a numbered `ADOPT / MODIFY / REJECT` decision for each item below
and explain any necessary correction **without looking at model outcomes**:

1. Is it correct to make source-time-available information the only
   claim-bearing task and demote realized `[source,target)` climate/traffic to a
   non-confirmatory oracle conditional diagnostic?
2. Is positive crack-length increment `max(0,L_target-L_source)` with original-
   scale MAE an acceptable primary endpoint, given that raw signed changes will
   also be disclosed descriptively?
3. Is removing geometry F1/IoU/tip error correct when the fitted model outputs
   only scalar growth?
4. Are the exact 11 predictors and their joins sufficiently unique and
   deployment-safe, especially prior-calendar-year ESAL/AADTT, the two
   construction-matched thickness summaries, and latest-prior normalized
   `D0,566 + FWD age`?
5. Is the fixed Bayesian Student-t hierarchical regression adequately
   regularized for 31 transitions and six sections? Please audit the priors,
   unseen-section random-effect integration, NUTS diagnostics, and inverse-
   transform prediction rule.
6. Are LOSO primary and the already frozen six-row future-time test secondary
   the correct two axes? Does either axis accidentally reuse held-out
   information?
7. Are the locked gates scientifically defensible: at least 10% pooled MAE
   improvement, improvement in at least 4/6 sections, 27--29 of 31 observations
   covered by the nominal-90% interval, and CRPS worsening no more than 5%?
8. Is the fail-closed requirement for complete 31-row inputs preferable to
   imputation in this dataset, or should a different missing-data rule be
   preregistered before acquisition?
9. Does the document make any causal, spatial, or deployment claim that the
   proposed experiment cannot support?
10. Is any remaining choice broad enough to permit post-result researcher
    degrees of freedom?

Please finish with one status only:

- `APPROVE_FOR_INPUT_FREEZE`;
- `REVISE_BEFORE_INPUT_FREEZE`; or
- `REJECT_EXPERIMENT_DESIGN`.

Do not authorize fitting directly. Even after design approval, the raw tables,
31-row feature table, split receipts, code/environment, and final
preregistration must be hashed and pass the no-fit preflight first.
