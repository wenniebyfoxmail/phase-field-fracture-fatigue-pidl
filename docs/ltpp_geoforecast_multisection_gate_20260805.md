# LTPP-GeoForecast multi-section candidate gate

Audit date: 2026-08-05. Official source: FHWA LTPP InfoPave SDR 39.

## Decision

`PASS_AT_LEAST_FIVE_MINIMUM_GEOMETRY_CLIMATE_CANDIDATES`

Six independent California asphalt sections pass the minimum acquisition gate
for the next annotation phase. This exceeds the predeclared target of five. A
pass means only that one construction trajectory contains at least five survey
dates with all of the following:

- a non-empty nominal `0-50 ft` manual distress map;
- successful regular-grid rectification to `15.24 m x 5 m` on every retained
  date;
- a manual check that coordinates printed inside the image are actually
  `0-50 ft`, rather than trusting the viewer label alone;
- continuous annual availability of temperature and precipitation over a
  prefix containing at least five surveys;
- no timeline maintenance/rehabilitation candidate inside that prefix.

The frozen machine receipt is:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_multisection_gate_v2_20260805/multisection_gate.json`

SHA-256: `22a2a752cb488ec70365ebec098e5b3b5623dffc8fe31b2c3b251240b348bd3b`

## Passing sections

| Section | Construction | Climate-complete surveys | Retained dates | Humidity exposed |
|---|---:|---:|---|---|
| `06-1253` | 1 | 8 | 1991-06-10 to 2012-04-17 | no |
| `06-2041` | 3 | 8 | 1996-03-20 to 2015-02-25 | no |
| `06-8149` | 2 | 6 | 1997-02-21 to 2007-03-15 | yes |
| `06-2647` | 1 | 5 | 1994-11-04 to 2007-03-09 | yes |
| `06-8150` | 3 | 5 | 2000-03-22 to 2009-11-16 | no |
| `06-8201` | 1 | 5 | 1994-10-31 to 2005-03-10 | yes |

There are 37 retained section-date states and 31 temporal transitions before
expanding from the audited first panel to other fixed panels. The `06-1253`
2015 map remains geometry-only because climate availability ends in 2012.

## Why viewer labels were not sufficient

California exposes 20 asphalt-description constructions with at least five
non-empty repeated maps and identical ordered panel labels. Two apparent grid
passes were rejected after composed-pixel review:

- `06-0563`: the first item is labelled `0-50 ft`, but the maps visibly switch
  among printed `0-50`, `100-150`, and `400-450 ft` stations.
- `06-0569`: the same mismatch occurs, including printed `100-150` and
  `400-450 ft` panels.

This is direct evidence that `ImageDescription` is not a sufficient physical
join key. Future expansion must check printed station coordinates or an
equivalent qualified registration signal on every source map.

## Frozen provenance

- State-wide inventory: `local_archive/real_road_acquisition/ltpp_california_geometry_inventory_20260805/`
- Correct white-composited top-candidate maps: `local_archive/real_road_acquisition/ltpp_california_candidate_panels_v2_20260805/`
- Additional ranked candidates: `local_archive/real_road_acquisition/ltpp_california_candidate_panels_rank8_13_20260805/` and `ltpp_california_candidate_panels_rank14_18_20260805/`
- Rectification results: matching `ltpp_california_candidate_rectification_*_20260805/` roots
- Forcing/timeline gate: `local_archive/real_road_acquisition/ltpp_geoforecast_multisection_gate_v2_20260805/`

The abandoned `ltpp_california_candidate_panels_20260805` package retained raw
RGBA images under an incorrect white-image filename. Its all-fail
rectification is a processing diagnostic, not evidence against the maps. The
v2 package preserves both raw RGBA and white-composited RGB files.

## Claim boundary

The gate does **not** prove that:

- the drawn strokes are qualified crack centreline truth;
- all ten viewer panels have correct station metadata;
- traffic observations are continuous or usable as interval forcing;
- humidity is pavement moisture;
- the six California assets span independent climate regimes;
- any model predicts future cracks;
- LTPP supplies observed phase-field, fatigue-history, or energetic state.

The result authorizes bounded dual-blind semantic vectorization and baseline
forecast construction. It does not authorize PIDL/FEM training or a
traffic-temperature-moisture mechanism claim.

## Next gate

Follow `ltpp_geoforecast_annotation_forecast_protocol_20260805.md`. The
predeclared second panel did not pass every automatic transform; therefore the
first blind batch is the qualified `0-50 ft` panel only. See
`ltpp_geoforecast_second_panel_gate_20260805.md`.
