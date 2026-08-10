# LTPP owner-confirmed map-panel MVP v2 — result

## Decision

`PARTIAL_PANEL_CANDIDATES_17_OF_40__NOT_REGISTRATION`

The completed v2 package used exactly the owner-confirmed 40 map pages.  It
returned paired panel candidates on 17 pages and `NO_PAIR` on 23 pages.  It
did not crop an input, extract a control, fit a transform, or change the closed
spatial-registration v1 decision.

## Complete output

| Date | Pair candidates | `NO_PAIR` |
|---|---:|---:|
| 1991-06-10 | 5 | 0 |
| 1995-10-24 | 0 | 5 |
| 1997-02-28 | 5 | 0 |
| 1998-04-07 | 5 | 0 |
| 2001-09-13 | 0 | 5 |
| 2003-05-14 | 0 | 5 |
| 2007-11-06 | 2 | 3 |
| 2012-04-17 | 0 | 5 |

The canonical package is:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_confirmed_map_panel_mvp_v2_20260810_after_page_name_repair/`

Its 50-entry manifest verified without mismatch.  The SHA-256 of
`manifest.sha256` is
`459f27759727eb500ef048728c8ada8edf567726a72d3fe81b820bf13303fd36`.

## Implementation-abort receipt

The first similarly named output stopped after writing the five 1991 overlays:
`pdftoppm` names pages with zero padding only when a PDF has enough pages.
There was no result JSON or manifest.  The repair accepts the exact padded or
unpadded page filename and changes no detection parameter, source page, or
interpretation rule.  The incomplete directory is retained.

## Interpretation

The owner-confirmed page inventory removed the false source-page assumption.
Where v2 produced candidates, the first-page overview visibly places boxes
near the two tall map grids.  However, 17/40 is insufficient even for an
engineering window carrier.  v2 is frozen as partial and must not be tuned or
used for registration.

The next separately named engineering model may use long outer-border lines on
the same confirmed pages, provided it remains barred from crack semantics,
controls, transforms, and qualification claims.
