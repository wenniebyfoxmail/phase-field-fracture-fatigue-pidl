# LTPP enriched-input frozen posterior result

Date: 2026-08-06
Status: `PRIMARY_NEGATIVE__ORACLE_DIAGNOSTIC_COMPLETE`

This is the result document for the separately reviewed 30-transition
complete-input sensitivity experiment defined by the composite v2 + v3 + v4
protocol. It is not an untouched continuation of v2: v2 terminated at input
coverage, v3 fixed the one named input-only exclusion, and v4 amended the prior
scales before any outcome fitting. ChatGPT Pro then explicitly authorized the
frozen posterior fit.

## Question and decision

Question: do source-available traffic, structure, and source-prior FWD add
stable predictive information about positive crack-length growth beyond
source geometry and trailing climate on unseen sections?

Decision: **no tested increment passed the preregistered LOSO gate.** The full
M3 model was also worse than persistence in pooled LOSO MAE. This is a valid
negative result for this six-section, 30-transition protocol, not evidence that
these physical variables are universally irrelevant.

## Frozen execution

- Rows: the named 30-transition v3 set across six LTPP sections.
- Primary validation: leave one whole section out (LOSO).
- Secondary validation: fixed 24-development + 6-future-time split.
- Models: persistence `B0`, then `M0` geometry + trailing climate, `M1` +
  traffic, `M2` + structure, and `M3` + source-prior FWD.
- Likelihood: hierarchical Student-t positive-growth model, `nu = 4`, with
  v4 priors applied identically across folds and ablations.
- Sampling: four chains, 2,000 warmup and 2,000 retained draws per chain;
  exactly one permitted retry used 4,000 warmup and target acceptance 0.95.
- Success gate for each named LOSO contrast: at least 10% pooled MAE reduction,
  improvement in at least 4/6 sections, exactly 26--28 of 30 observations
  covered by nominal 90% intervals, and CRPS worsening no greater than 5%.

## Primary LOSO results

| model | inputs through | MAE (m) | RMSE (m) | mean CRPS (m) | 90% covered |
|---|---|---:|---:|---:|---:|
| B0 | persistence | 4.2402 | 7.9509 | 4.2402 | 15/30 |
| M0 | geometry + climate | 4.3888 | 7.5322 | 134.2486 | 26/30 |
| M1 | + traffic | 4.4073 | 7.5599 | 1665.2027 | 26/30 |
| M2 | + structure | 4.4133 | 7.5636 | 547.3601 | 26/30 |
| M3 | + FWD | 4.4154 | 7.5498 | 648.3165 | 26/30 |

| frozen contrast | pooled MAE reduction | improved sections | coverage gate | CRPS change | verdict |
|---|---:|---:|---|---:|---|
| M1 vs M0 | -0.421% | 3/6 | pass | +1140.39% | fail |
| M2 vs M1 | -0.135% | 1/6 | pass | -67.13% | fail |
| M3 vs M2 | -0.049% | 3/6 | pass | +18.44% | fail |
| M3 vs B0 | -4.132% | 3/6 | pass | +15189.67% | fail |

Negative reduction means that the challenger has higher MAE. For M3 minus
B0, the section-bootstrap mean MAE difference was `+0.1842 m`; its descriptive
95% interval was `[-0.0814, +0.5230] m` (10,000 draws, seed 260806). The
interval is descriptive and does not replace the frozen engineering gates.

## Secondary future-time results

| model | MAE (m) | RMSE (m) | mean CRPS (m) | 90% covered |
|---|---:|---:|---:|---:|
| B0 | 5.1148 | 9.0254 | 5.1148 | 4/6 |
| M0 | 5.4161 | 8.4120 | 2.9065e20 | 5/6 |
| M1 | 5.4309 | 8.4014 | 3.7900e11 | 5/6 |
| M2 | 5.4171 | 8.3989 | 3.9926e14 | 5/6 |
| M3 | 5.4074 | 8.3760 | 1.0082e17 | 5/6 |

The very large CRPS values are caused by rare extreme posterior-predictive
draws under the frozen heavy-tailed model. The earlier v4 preflight disclosed
rare maxima even though its frequency gate passed. These values are therefore
reported unchanged; no post-outcome clipping, prior retuning, likelihood
change, or architecture rescue is allowed.

## Sampler validity

All 28 primary fits passed the frozen final diagnostics. Eight used the single
allowed retry; none failed after retry. Worst final rank-normalized R-hat was
`1.00256`, minimum bulk ESS was `2689.96`, minimum tail ESS was `2914.47`, and
final post-warmup divergences were zero. The scientific result is negative,
but the run itself is computationally valid.

## O3 realized-exposure diagnostic

O3 is a non-confirmatory conditional diagnostic on the fixed 29-row set. It
uses realized interval climate and traffic exposure and cannot rescue the
source-available primary result.

| design | comparison | O3 MAE (m) | matched M3 MAE (m) | O3 - M3 (m) |
|---|---|---:|---:|---:|
| LOSO, 29 rows | realized vs source-available | 4.5218 | 4.5310 | -0.0093 |
| future time, 5 rows | realized vs source-available | 6.2191 | 6.2379 | -0.0188 |

The LOSO point improvement is about 0.2% and is practically negligible. O3
also had much worse LOSO CRPS (`3854.29` vs `670.63`). All seven O3 fits passed
final diagnostics; one used the allowed retry. The diagnostic does not suggest
that merely replacing source-available exposure with realized exposure solves
the primary forecasting failure.

## Interpretation boundary

Supported statement:

> Under the frozen six-section complete-input sensitivity protocol, none of
> the tested traffic, structure, or FWD increments provided stable incremental
> predictive value beyond the preceding input block, and the full enriched
> model did not beat persistence in LOSO MAE.

Not supported:

- traffic, structure, or FWD never matter for pavement cracking;
- the inputs have no causal effect;
- the result generalizes beyond these six sections and 30 transitions;
- the model predicts future crack location or two-dimensional geometry;
- O3 is a deployable forecast or a confirmatory rescue.

No further tuning is permitted inside this experiment. Any different outcome,
feature representation, likelihood, spatial target, or larger section panel
must be a newly preregistered track.

## Reproducibility receipts

- Pro fit authorization:
  `docs/reviews/ltpp_geoforecast_enriched_input_chatgpt_pro_fit_authorization_20260806.md`,
  SHA-256 `4ba696915bc85c7b2d656fb3b0c1d3bf3f4572c6037629811a37908ed7bbe27f`.
- Environment lock:
  `requirements/ltpp_enriched_posterior_lock_20260806.txt`, SHA-256
  `446c20589b9bb2b0b6059a2e3953a36274f591d4b28741bb86e9232435cce180`.
- Primary sealed evaluation: SHA-256
  `f3a18f4fc9bdd186da8d1e42fad44d688030e5569f17f36a720f76e53e26c6d2`.
- Primary sealed predictions: SHA-256
  `465c0dff865ae6813b9da75ad16f8a108f2adcdeae17b862835bf9385311b67b`.
- O3 result: SHA-256
  `0b56d9e82c627482ade7affb4186c29a952c44cb42fb3b7f417f9a8735bbc169`.
- O3 predictions: SHA-256
  `67657fb8db34fb065df7c4847d2049fea8c418bbd75e2b8671acff024c09383c`.
- Raw posterior samples, sealed predictions, diagnostics, logs, and manifests:
  local archive `real_road_acquisition/ltpp_geoforecast_enriched_posterior_v1_20260806/`.
