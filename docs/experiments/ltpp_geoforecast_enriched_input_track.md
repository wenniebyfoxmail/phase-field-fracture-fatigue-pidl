# LTPP source-available enriched-input forecast track

Canonical track document

Status: `PRIMARY_NEGATIVE__ORACLE_DIAGNOSTIC_COMPLETE`

## Mechanism question

Do source-available traffic demand, pavement structure, and source-prior FWD
provide stable incremental predictive information about positive crack-length
growth beyond source geometry and trailing climate on unseen LTPP sections?

## Claim boundary

- A passing experiment may support incremental predictive information value
  under the frozen six-section protocol.
- A failing fitted experiment may show that the tested input blocks did not
  provide stable incremental value in the qualified sample.
- An input-gate failure supports neither conclusion.
- This track cannot establish causality, general road-crack prediction, future
  crack placement, or two-dimensional geometry accuracy.

## Frozen assets and provenance

| asset | role | path | hash/status |
|---|---|---|---|
| adjudicated labels | frozen geometry states | local `ltpp_geoforecast_blind_vectorization_v1_20260805/adjudicated/adjudicated_manifest.json` | `6a9422bd...f4ad` |
| transitions | 37 states / 31 transitions | local `adjudicated_transitions/transition_manifest.json` | `1c38725d...e918` |
| baseline manifest | original split receipt and controls | local `frozen_baselines/baseline_manifest.json` | `e70564d3...b55` |
| approved v2 | exact reviewed design | `ltpp_geoforecast_enriched_input_preregistration_v2_20260806.md` | `3b93cdb7...4992` |
| InfoPave raw v3 | 6 sections by 7 tables | local `ltpp_geoforecast_enriched_raw_sdr39_v3_20260806/raw_data_manifest.json` | `c8659bb6...a6bd` |
| trailing climate v2 | 190 request/response pairs | local `ltpp_geoforecast_multisection_climate_raw_v2_20260806/climate_raw_manifest.json` | `5eb24df2...25cd` |
| v2 coverage receipt | exact blocking result | local `ltpp_geoforecast_enriched_input_freeze_v1_20260806/coverage_report.json` | `d6ef02cf...4ab8` |

All `local` paths above are rooted at
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/`.

## Experiment registry

| experiment | status | primary document |
|---|---|---|
| six-section adjudicated persistence/state-space benchmark | `RELIABILITY_NEGATIVE` | `../ltpp_geoforecast_algorithm_plan_20260805.md` |
| enriched-input preregistration v2 | `APPROVED_FOR_INPUT_FREEZE` | `ltpp_geoforecast_enriched_input_preregistration_v2_20260806.md` |
| enriched-input v2 input freeze | `BLOCKED_INPUT_COVERAGE__NO_FIT` | `ltpp_geoforecast_enriched_input_freeze_blocked_20260806.md` |
| enriched-input v3 complete-case amendment | `APPROVED_FOR_30_ROW_INPUT_FREEZE__NO_FIT` | `ltpp_geoforecast_enriched_input_preregistration_v3_amendment_candidate_20260806.md` |
| enriched-input v3 input freeze | `PASS_30_BY_11__NO_FIT` | `ltpp_geoforecast_enriched_input_v3_prior_predictive_blocked_20260806.md` |
| enriched-input v3 prior-predictive gate | `FAILED__NO_FIT` | `ltpp_geoforecast_enriched_input_v3_prior_predictive_blocked_20260806.md` |
| enriched-input v4 prior amendment | `APPROVED_FOR_PREFLIGHT_ONLY__NO_FIT` | `ltpp_geoforecast_enriched_input_preregistration_v4_prior_amendment_candidate_20260806.md` |
| enriched-input v4 prior preflight | `PASS__FIT_AUTHORIZATION_REQUIRED__NO_FIT` | `ltpp_geoforecast_enriched_input_v4_prior_preflight_pass_20260806.md` |
| enriched-input frozen posterior | `PRIMARY_NEGATIVE__ORACLE_DIAGNOSTIC_COMPLETE` | `ltpp_geoforecast_enriched_input_posterior_result_20260806.md` |

## V2 terminal decision

The v2 builder completed all 11 source-time joins for 30/31 transitions. It
failed exactly at `06-2041-T01`: the source date is `1996-03-20`, the
source-active construction is `3`, and `TRF_TREND` contains no construction-3
row for the required prior complete year 1995. Construction 2 has AADTT but a
null ESAL. V2 prohibits substitution, imputation, row removal, or source-year
leakage, so prior-predictive checking and fitting did not run.

## Frozen posterior result

- **Mechanism question:** unchanged from v2.
- **Completed input gate:** the exact 30x11 table and regenerated LOSO/24+6
  split passed. Feature-table SHA-256 is `c0443e1c...99a4d`.
- **Failed cheaper diagnostic:** all 28 fixed prior-predictive model/folds
  exceeded the 1% cap gate; observed exceedance fractions were 8.2%--27.8%.
- **Evidence boundary:** no outcome field was read and no posterior or ablation
  was fitted. This diagnoses implausibly broad priors, not feature value.
- **Approved amendment:** ChatGPT Pro approved exactly one v4 preflight using
  `Normal(0,1)`, `Normal(0,0.1)`, `HalfNormal(0.5)`, and `HalfNormal(0.5)`.
- **Completed cheaper diagnostic:** all 28 model/design checks passed; fold
  exceedance fractions were 0.0000--0.0040 against the unchanged 0.01 gate.
- **Tail disclosure:** rare individual draws reached about 179,895 m. They do
  not fail the frozen frequency gate, but remain disclosed for fit review.
- **Fit authorization:** ChatGPT Pro explicitly issued
  `AUTHORIZE_FROZEN_POSTERIOR_FIT`; the authorization receipt is sealed at
  SHA-256 `4ba69691...e27f`.
- **Execution validity:** all 28 primary NUTS fits passed final diagnostics;
  eight used the one allowed retry, with zero final divergences.
- **Primary result:** no M1/M0, M2/M1, M3/M2, or M3/B0 contrast passed the
  frozen LOSO gate. M3 worsened pooled MAE by 4.13% relative to persistence and
  improved only 3/6 sections.
- **Oracle result:** O3 changed matched 29-row LOSO MAE by only `-0.0093 m`
  and remains non-confirmatory; it does not rescue the primary result.

## Current decision

Close this experiment as a computationally valid negative result. Do not tune
the frozen model, replace metrics, clip predictive tails, or promote O3. The
supported claim is limited to lack of stable incremental predictive value in
this six-section, 30-transition sensitivity protocol.

## Next action

Use persistence as the honest point baseline for this panel. Any larger panel,
spatial target, alternative likelihood, or different representation must be a
new preregistered experiment rather than a continuation of this track.

## Research-frontier handoff

The authorized frozen posterior experiment completed as a valid negative
result: no enriched input block passed its LOSO increment gate, M3 worsened MAE
4.13% versus persistence, and the O3 realized-exposure diagnostic was
negligible. Full evidence remains in this track and its result document.
