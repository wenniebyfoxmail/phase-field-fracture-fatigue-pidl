# LTPP confirmed-page outer-frame MVP v3 — result

## Decision

`OUTER_FRAME_MVP_V3_NOT_ACCEPTED__NO_REGISTRATION`

The one-shot v3 run completed all 40 owner-confirmed map pages.  It produced
18 candidate pairs and 22 `NO_PAIR` results, only one more candidate page than
v2.  Visual inspection of the frozen overview shows that some candidates still
extend to a page-bottom rule or splice non-map form structure into the proposed
frame.  The output is therefore not accepted for cropping or registration.

## Complete output

| Date | Pair candidates | `NO_PAIR` |
|---|---:|---:|
| 1991-06-10 | 3 | 2 |
| 1995-10-24 | 1 | 4 |
| 1997-02-28 | 5 | 0 |
| 1998-04-07 | 1 | 4 |
| 2001-09-13 | 4 | 1 |
| 2003-05-14 | 0 | 5 |
| 2007-11-06 | 2 | 3 |
| 2012-04-17 | 2 | 3 |

The canonical package is:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_confirmed_outer_frame_mvp_v3_20260810/`

Its 50-entry manifest verified without mismatch.  The SHA-256 of
`manifest.sha256` is
`51a8fd5cad7aa4ec5b5c3d2db56fab51a5a1692e0627d671e899fe359329f752`.

## Interpretation and route correction

The confirmed PDF page ranges are useful provenance, but extracting two map
panels from full survey pages is not required for the engineering registration
MVP.  The official acquisition archive already contains ten separate 50-ft
viewer PNGs per date, including `segment_0_50.png`, with source URLs and hashes.
The full PDFs should remain source/context receipts rather than becoming a new
panel-extraction dependency.

Do not tune v3.  The smallest practical MVP now returns to each date's official
0–50-ft PNG and obtains only its four printed physical-grid corners.  Owner
corner review can complete an explicitly exploratory carrier, but because the
owner has seen v1 outcomes it cannot supply independent final v2 audit
controls.  No PDF candidate in this package is transferred into registration.

The closed result remains:

`SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`
