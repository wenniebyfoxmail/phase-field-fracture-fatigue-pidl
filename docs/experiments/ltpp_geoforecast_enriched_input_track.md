# LTPP source-available enriched-input forecast track

Canonical track document

Status: `V2_BLOCKED_INPUT_COVERAGE__V3_EXTERNAL_REVIEW_REQUIRED__NO_FIT`

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
| enriched-input v3 complete-case amendment | `CANDIDATE__EXTERNAL_REVIEW_REQUIRED__NO_FIT` | `ltpp_geoforecast_enriched_input_preregistration_v3_amendment_candidate_20260806.md` |

## V2 terminal decision

The v2 builder completed all 11 source-time joins for 30/31 transitions. It
failed exactly at `06-2041-T01`: the source date is `1996-03-20`, the
source-active construction is `3`, and `TRF_TREND` contains no construction-3
row for the required prior complete year 1995. Construction 2 has AADTT but a
null ESAL. V2 prohibits substitution, imputation, row removal, or source-year
leakage, so prior-predictive checking and fitting did not run.

## Current gate: v3 design review

- **Mechanism question:** unchanged from v2.
- **Cheaper diagnostic:** exact input coverage audit is complete; only one row
  fails.
- **Minimal candidate change:** freeze a 30-transition complete-case set by
  excluding only `06-2041-T01`, with all features, algorithm, ordering, and
  thresholds otherwise unchanged.
- **Researcher-degree-of-freedom risk:** the excluded row's historical outcome
  existed in the earlier benchmark, even though no enriched model was fitted.
  External review must decide whether a fixed input-only exclusion is still
  acceptable for a confirmatory information-value experiment.
- **Success condition for this gate:** ChatGPT Pro explicitly approves the
  30-row amendment and its revised integer coverage rule.
- **Failure condition:** reviewer requires a replacement independent section,
  a different missing-data design, or rejects confirmatory status.
- **Fit authorization:** `NO_FIT` until review approval, new hashes, a complete
  30x11 table, split receipt, code receipt, and prior-predictive pass exist.

## Current decision

Keep v2 terminal. Present exactly one minimal v3 amendment for external review;
do not compare multiple rescue rules and do not inspect enriched-model results.

## Next action

Submit
`ltpp_geoforecast_enriched_input_chatgpt_pro_v3_review_request_20260806.md`
with the v2 preregistration, v2 blocked decision, and v3 amendment candidate.
Adopt the review before changing the builder or freezing a 30-row package.

## Research-frontier handoff

LTPP enriched-input v2 stopped at a preregistered 30/31 coverage failure before
any fit. A single 30-row complete-case v3 amendment is awaiting external review;
the full state and evidence are maintained in this track document.
