# LTPP full-source map-panel MVP v1.1 — result

## Decision

`EXPLORATORY_PANEL_CANDIDATES_ONLY__NOT_ACCEPTED_FOR_REGISTRATION`

The capped, one-shot v1.1 run completed all eight date pages and its manifest
verified.  It generated a candidate pair for seven dates and fail-closed for
1991.  The overlays are intentionally retained for human review; several
rectangles visibly follow a strong internal/form boundary or only a portion of
a map panel rather than the complete printed 50-ft frame.  Therefore the
output is not accepted as a map-window solution, and cannot be used as a crop,
control source, transform input, or registration claim.

The closed v1 status remains unchanged:

`SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`

## Canonical completed package

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_full_source_map_panel_mvp_v1_1_20260810/`

- `eight_date_full_source_panel_overview.png` — all raw page-4 sources with
  green `P1` and magenta `P2` candidates;
- `overlays/` — full-resolution image-by-image review overlays;
- `panel_mvp_result.json` — all source hashes, candidates, and no-candidate
  record;
- `manifest.sha256` — 10 entries, independently recomputed without mismatch.

The SHA-256 of `manifest.sha256` is
`da93a6fe3bf2879dd50f4928b0a28395dd00d4b10995b25a8f07e4883b2b5c4a`.

## Complete one-shot output

| Date | Mechanical output | Interpretation boundary |
|---|---|---|
| 1991-06-10 | `NO_PANEL_PAIR` | retained failure; no manual box completion |
| 1995-10-24 | candidate pair | visual review required; not an approved panel window |
| 1997-02-28 | candidate pair | visual review required; not an approved panel window |
| 1998-04-07 | candidate pair | visual review required; not an approved panel window |
| 2001-09-13 | candidate pair | visual review required; not an approved panel window |
| 2003-05-14 | candidate pair | visual review required; not an approved panel window |
| 2007-11-06 | candidate pair | visual review required; not an approved panel window |
| 2012-04-17 | candidate pair | visual review required; not an approved panel window |

## Execution integrity note

v1.1 was frozen after the v1 runtime problem was identified, before any
complete v1 outcome was read.  Its only added line cap is recorded in the
v1.1 preregistration.  Because the original v1 child was discovered still
running after v1.1 had started, v1.1 is explicitly only an engineering
visualization result, not independent validation and not a selection between
registration methods.  No candidate coordinate was transferred to any v2
control packet.

## Next condition

Do not tune v1.1.  The useful next experiment would need a different,
predeclared source-page model: first identify the form's global 90-degree page
orientation and its printed map-row band, then detect panel frames only within
that band.  It must again be separately named, synthetic-tested, fully
visualised, and barred from transform fitting.  A user visual check of this
overview should guide whether that route is worth authorizing; it does not
reopen the registration gate.
