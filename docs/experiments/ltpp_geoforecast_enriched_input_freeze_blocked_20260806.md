# LTPP enriched-input freeze decision

Date: 2026-08-06

Status: `BLOCKED_INPUT_COVERAGE__NO_FIT`

## Decision

The approved v2 experiment cannot advance to prior-predictive checking or
outcome fitting. The fail-closed 31-row by 11-feature builder completed every
required source-time join for 30 transitions, but the exact preregistered
traffic join is absent for `06-2041-T01`.

This is an input-qualification result, not a predictive-model result. It does
not show that traffic, structure, or FWD lacks predictive value.

## Exact blocking row

| field | frozen value |
|---|---|
| transition | `06-2041-T01` |
| source cutoff | `1996-03-20` |
| source-active construction | `3` |
| required traffic year | `1995` |
| required row | `TRF_TREND(CONSTRUCTION_NO=3, YEAR=1995)` |
| result | zero rows |

The official frozen table has two `1995` rows for this section:

- construction `2`: AADTT `730`, but `ANNUAL_ESAL_TREND` is null;
- construction `1`: AADTT `730` and ESAL `162534`.

Neither row is the preregistered source-active construction `3`. Substituting
construction `1` or `2`, using the incomplete source year `1996`, carrying a
different year, imputing ESAL, or dropping the transition would change the
frozen input rule after inspection. All are prohibited in the approved v2
confirmatory experiment.

## Frozen evidence

| asset | path | SHA-256 |
|---|---|---|
| approved preregistration | `docs/experiments/ltpp_geoforecast_enriched_input_preregistration_v2_20260806.md` | `3b93cdb71be7c32ea6a7524d14ab2b3d3a619a13fcbed9be596d9e2d5c824992` |
| enriched raw manifest | `local_archive/real_road_acquisition/ltpp_geoforecast_enriched_raw_sdr39_v3_20260806/raw_data_manifest.json` | `c8659bb66bc8820b6a65edd754ab16ca7fbeb7d02545574de9f44623a391a6bd` |
| trailing-climate raw manifest | `local_archive/real_road_acquisition/ltpp_geoforecast_multisection_climate_raw_v2_20260806/climate_raw_manifest.json` | `5eb24df21d14b68e2b0b59b259de69cf84f66599c11d21a2fa3922be6eb925cd` |
| coverage report | `local_archive/real_road_acquisition/ltpp_geoforecast_enriched_input_freeze_v1_20260806/coverage_report.json` | `d6ef02cfe234274c7700d433db9424c3e70ae98eacc6f76c93b1783f48dc4ab8` |

The raw package contains 6 sections by 7 official tables, including every
query receipt, dictionary/unit record, raw response page, CSV, row count, and
file hash. Its `raw_files.sha256` passed in full. The expanded climate package
contains 190 official monthly temperature/precipitation requests, including
one source-lookback year, and its `raw_files.sha256` also passed in full.

## Implementation and checks

- implementation commit: `062fac6`;
- builder: `scripts/ltpp_build_enriched_input_freeze.py`;
- acquisition: `scripts/ltpp_acquire_enriched_tables.py` and
  `scripts/ltpp_acquire_multisection_climate.py`;
- builder exit status: `2`, as required for missing coverage;
- coverage: `30/31` complete transitions, `11` required features;
- unit tests: `3/3` passed;
- syntax compilation: passed;
- no outcome columns were written;
- no prior-predictive draws were generated;
- no posterior fitting or ablation scoring was run.

The first acquisition attempt used the human-readable section code where the
InfoPave filter expects `LDW_SECTION_ID`; it failed before downloading table
rows. The corrected acquisition uses the six frozen LDW IDs and independently
verifies returned `STATE_CODE` and `SHRP_ID`. The v3 raw package is the only
claim-bearing enriched raw package.

## Permitted next action

Keep v2 terminal as `BLOCKED_INPUT_COVERAGE`. Any rescue requires a separately
reviewed and re-hashed v3 preregistration that changes the traffic alignment or
the qualified row set before any outcome fit. The present evidence does not
choose among those alternatives.
