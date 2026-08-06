# LTPP source-available enriched-input forecast track

Canonical track document

Status: `V2_BLOCKED__V3_APPROVED_FOR_30_ROW_INPUT_FREEZE__NO_FIT`

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

## V2 terminal decision

The v2 builder completed all 11 source-time joins for 30/31 transitions. It
failed exactly at `06-2041-T01`: the source date is `1996-03-20`, the
source-active construction is `3`, and `TRF_TREND` contains no construction-3
row for the required prior complete year 1995. Construction 2 has AADTT but a
null ESAL. V2 prohibits substitution, imputation, row removal, or source-year
leakage, so prior-predictive checking and fitting did not run.

## Current gate: v3 30-row input freeze

- **Mechanism question:** unchanged from v2.
- **Cheaper diagnostic:** exact input coverage audit is complete; only one row
  fails.
- **Minimal candidate change:** freeze a 30-transition complete-case set by
  excluding only `06-2041-T01`, with all features, algorithm, ordering, and
  thresholds otherwise unchanged.
- **External disposition:** ChatGPT Pro returned
  `APPROVE_V3_30_ROW_INPUT_FREEZE` for amendment SHA-256
  `f2490cd99b07912567ab52aabcf2ba9472b9514de3dd0fe1c1b1bba4e85ec70d`.
- **Success condition for this gate:** a complete fixed 30x11 table, regenerated
  split receipt, code/environment receipt, all hashes, and the fixed prior-
  predictive check pass.
- **Failure condition:** any remaining input is missing, any source-after-cutoff
  value appears, a split/hash differs, or prior predictive exceeds its gate.
- **Fit authorization:** still `NO_FIT`; Pro approval authorizes preflight only.

## Current decision

Keep v2 terminal and execute only the approved named 30-row v3 pre-fit package.
Do not compare rescue rules or inspect enriched-model outcomes.

## Next action

Freeze the exact 30x11 source-cutoff table, regenerate the LOSO and 24+6 split
receipt, record code/environment hashes, and run the fixed prior-predictive
check. Stop before posterior fitting unless every gate passes.

## Research-frontier handoff

LTPP enriched-input v2 stopped at a preregistered 30/31 coverage failure before
any fit. The fixed 30-row v3 sensitivity amendment is approved for input freeze
and prior-predictive preflight only; full evidence remains in this track.
