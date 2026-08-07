# LTPP-GeoForecast second-panel acquisition gate

## Decision

`SECOND_PANEL_GATE_NOT_YET_QUALIFIED`

The predeclared `250-300 ft` panel was frozen for all six qualified sections,
covering 38 source maps before excluding the climate-incomplete `06-1253` 2015
state. All source images visibly print the intended `250-300 ft` station range,
but the unchanged automatic physical-grid gate does not pass every date in
three sections.

| Section | Grid passes | Total maps | Decision |
|---|---:|---:|---|
| `06-1253` | 7 | 9 | fail pending two-map crop qualification |
| `06-2041` | 8 | 8 | pass |
| `06-8149` | 6 | 6 | pass |
| `06-2647` | 5 | 5 | pass |
| `06-8150` | 4 | 5 | fail pending one-map crop qualification |
| `06-8201` | 3 | 5 | fail pending two-map crop qualification |

The failed dates remain visually compatible coordinate carriers, but the
current detector either finds too few vertical grid matches or chooses an
aspect-inconsistent border pair. Visual plausibility is not substituted for a
frozen transform.

## Provenance

- Source freeze: `local_archive/real_road_acquisition/ltpp_geoforecast_panel_250_300_v1_20260805/`
- Rectification: `local_archive/real_road_acquisition/ltpp_geoforecast_panel_250_300_rectification_v1_20260805/`

The result forbids threshold tuning after looking at crack content. A later
manual-corner fallback must use only printed physical borders, record the four
source corners and reviewer decision, and remain independent of distress
strokes and future maps.

## Consequence

The first dual-blind annotation gate is reduced to the already qualified
`0-50 ft` panel: 37 climate-complete maps per annotator. The `250-300 ft` panel
may enter only after the five failed transforms are independently frozen and
reviewed. This reduction changes sample size, not the locked prediction success
rule.
