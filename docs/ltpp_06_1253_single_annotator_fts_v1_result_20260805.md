# LTPP 06-1253 single-annotator Freeze-Then-Select v1 result

## Evidence grade

`exploratory_single_annotator`. The locked primary geometry is an observational
interpretation, not ground truth or an adjudicated reference. No causal,
confirmatory, traffic, moisture, mechanics, phase-field-teacher, natural crack
morphology, exact-tip, or cross-road claim is authorized.

## Frozen inputs

- Nine locked `line_area_v2` primary maps: 88 geometries, comprising 72
  LineStrings and 16 Polygons.
- Frozen observation field: 9 x 126 x 382, SHA-256
  `7d6a230ed12b885ed3d14166ea73c563b350515b25953cbb3fb42b612ed7e96e`.
- Seven climate-complete transitions; the 2012-to-2015 transition remains
  prohibited.
- Candidate library: constant, damage, damage squared, low-temperature
  exposure, temperature-variation rate, precipitation rate, and the three
  damage-forcing interactions.

## Perturbation matrix

The run crossed four time windows, four weak-test configurations, and three
random seeds, for 48 systems. Each system used 192 spatial weak windows and 32
grouped stability trials. Spatial sections and transition IDs formed holdout
groups.

## Results

- FTS cross-run support Jaccard: `0.5065`.
- Single-shot cross-run support Jaccard: `0.7528`.
- Mean FTS grouped holdout RMSE: `0.06570`.
- Mean single-shot holdout RMSE: `0.06648`.
- Relative FTS RMSE improvement over single-shot: approximately `1.16%`.

The higher single-shot Jaccard is not evidence of correct recovery: single-shot
often retained most of the nine-term library. FTS was sparser but changed support
substantially across temporal windows.

Across the 48 FTS runs, the stable-run fractions were:

| Term | Stable-run fraction |
|---|---:|
| constant | 0.938 |
| temp_variation_rate | 0.833 |
| damage | 0.688 |
| damage_x_low_temp_exposure | 0.667 |
| low_temp_exposure | 0.646 |
| damage_x_temp_variation_rate | 0.583 |
| precipitation_rate | 0.458 |
| damage_sq | 0.396 |
| damage_x_precipitation_rate | 0.313 |

## Decision

`NOT_RELIABILITY_POSITIVE`.

The v1 observation-only experiment does not show that FTS is more support-stable
than single-shot selection on this asset. The small weak-RMSE improvement is not
decisive, and no true support is available. Temperature-variation rate is the
most repeatable environmental association, but it must not be called causal.

The next valid step is an identifiability gate, not threshold tuning. A reduced
library may be run only as an explicitly post-v1 diagnostic or against new
independent evidence; it cannot retroactively replace this frozen result.

## Artifacts

- Result root:
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_single_annotator_fts_v1_20260805`
- Preflight:
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_single_annotator_preflight_v1_20260805.json`
- Observation fields:
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_single_annotator_fields_v1_20260805`
