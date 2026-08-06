# Initial external planning advice: LTPP enriched-input ablation

Date: 2026-08-06  
Conversation: `chatgpt-conversation://6a744792-7608-83eb-a541-46e5bd3043d7`  
Status: `RECORDED__SECOND_REVIEW_PENDING`

## Advice received

The external planning conversation recommended freezing the scientific question
before choosing among algorithms, using leave-one-section-out validation,
holding one algorithm fixed, limiting the feature count for 31 transitions,
joining only source-prior FWD with an explicit FWD age, running a fixed
geometry/climate to traffic to structure to FWD ablation, defining success
before fitting, and separating exploratory work from confirmatory results.

## Adopted

- fixed feature-block order;
- LOSO as the primary unseen-section axis;
- one small shrinkage model rather than an algorithm search;
- source-prior FWD plus measurement age;
- a predeclared 10% point-error, four-of-six-section, coverage, and CRPS gate;
- prohibition of post-result feature, threshold, and algorithm changes;
- predictive-value language rather than causal claims.

## Modified

- Realized source-to-target climate and traffic were moved out of the primary
  forecast because they are not available at the source date. The primary task
  now uses source-available trailing climate and prior-year traffic; one sealed
  oracle conditional diagnostic retains realized future exposure.
- The scalar model is evaluated only on crack-length growth and probabilistic
  outputs. Spatial F1, IoU, tip error, and new-geometry area were removed because
  the model does not generate crack placement.
- “Ridge or Gaussian prior” was replaced by one exact Bayesian hierarchical
  Student-t shrinkage model with fixed priors, sampling rules, and diagnostics.
- Open-ended AADTT/material/FWD choices were replaced by exact fields and
  aggregation rules. Material-category encoding and backcalculated modulus were
  excluded.
- The already frozen six-row future-time axis was retained as a secondary test
  rather than replaced by LOSO.

## Rejected

- A “causal story” interpretation. The experiment can support only incremental
  predictive value under the frozen ordering.
- Escalation to RF, boosting, GNN, neural operators, PIDL, or FEM as a rescue if
  the small fixed model fails.

## Pending external audit

The revised preregistration is
`docs/experiments/ltpp_geoforecast_enriched_input_preregistration_v2_20260806.md`.
It remains `NO_FIT_AUTHORIZED` until ChatGPT Pro reviews the exact source-time
information set, feature table, probabilistic model, validation axes, gates, and
immutable evidence contract.
