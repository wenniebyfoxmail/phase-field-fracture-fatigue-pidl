# LTPP enriched-input v3 prior-predictive gate decision

Date: 2026-08-06

Decision: `PRIOR_PREDICTIVE_REVIEW_REQUIRED__NO_OUTCOME_FIT`

## Design identity

This is the separately reviewed 30-row complete-input sensitivity experiment
defined by the unchanged v2 preregistration plus the approved v3 amendment.
It is not an untouched continuation of v2.

- v2 SHA-256: `3b93cdb71be7c32ea6a7524d14ab2b3d3a619a13fcbed9be596d9e2d5c824992`
- v3 amendment SHA-256: `f2490cd99b07912567ab52aabcf2ba9472b9514de3dd0fe1c1b1bba4e85ec70d`
- external decision: `APPROVE_V3_30_ROW_INPUT_FREEZE`
- only excluded transition: `06-2041-T01`

## Input-freeze result

The approved input-only amendment passed its exact qualification gate.

- rows by features: `30 x 11`
- complete rows: `30/30`
- feature-table SHA-256:
  `c0443e1c8f66f0c9bb0f3f45af26cf75fd4366ec70f4ccc3a1e87242ddc99a4d`
- feature-manifest SHA-256:
  `e17313471628e28573c62f27c84f1fdca197bb20e6d477d28afb60358989aaf3`
- split-receipt SHA-256:
  `1cb574e0d9e7cb2976f043ad5c83b718c017bff9dff508f1798b603aac4e4a2b`
- LOSO held-out counts: `7, 6, 4, 5, 4, 4` for the six sorted sections
- future-time split: `24 development + 6 final-time`
- outcome columns in the frozen input table: none

The local immutable package is:

`local_archive/real_road_acquisition/ltpp_geoforecast_enriched_input_v3_candidate_20260806/input_freeze/`

## Prior-predictive result

The fixed 500-draw prior check failed in all 28 preregistered model/design
combinations (`M0`--`M3`, six LOSO folds plus future-time). The allowed fraction
above the fixed `100.189733 m` cap was at most 1%; observed fold ranges were:

| model | minimum above-cap fraction | maximum above-cap fraction | fold p95 range (m) |
|---|---:|---:|---:|
| M0 | 0.0820 | 0.1816 | 263.09--5,670.04 |
| M1 | 0.0860 | 0.2320 | 290.77--18,296.38 |
| M2 | 0.0900 | 0.2392 | 326.93--42,622.48 |
| M3 | 0.1130 | 0.2780 | 428.62--264,521.17 |

- prior-predictive report SHA-256:
  `6c615869b1ba6ffc21ce2001825c00e05a9b2d65b1b6a42fb45df5f7317d8049`
- outcome fields read: none
- posterior fit performed: false
- ablation scoring performed: false

The local receipt is:

`local_archive/real_road_acquisition/ltpp_geoforecast_enriched_input_v3_candidate_20260806/prior_predictive/prior_predictive_report.json`

## Interpretation boundary

This failure says that the frozen coefficient/intercept/noise priors are too
diffuse on the physical crack-growth scale after `max(0, exp(y)-1)`. It does
not say whether traffic, structure, or FWD have incremental predictive value,
because no outcome likelihood was fitted and no held-out prediction was made.

The 30x11 input freeze remains qualified and immutable. The prior check cannot
be rescued by silently tightening priors, changing the cap, changing features,
or selecting a favorable fold. V3 remains `NO_FIT`.

## Next admissible action

Prepare exactly one separately hashed prior-calibration amendment and obtain
external approval before rerunning the prior check. The amendment must disclose
that the original prior-predictive result was inspected, derive any new scale
from a stated domain bound rather than from outcome fitting, preserve the fixed
30 rows, features, splits, likelihood, endpoint, and success gate, and authorize
no posterior fitting until the amended prior gate passes.
