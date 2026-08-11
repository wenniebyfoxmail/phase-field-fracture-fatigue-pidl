# LTPP geometry-assisted grid-control pilot result — 2026-08-11

## Status

`EXPLORATORY_AI_ASSISTED_CONTROL_PILOT_READY__NOT_INDEPENDENT`

The deterministic assistance and correction interface is operational for all
eight dates. It does not change v1, the independent-control availability
status, or the 2-D gate.

## Delivered interaction

- All 66 `G[i,j]` suggestions are pre-positioned by the owner-corner
  projective construction.
- The interface explicitly states that `i` is the left-to-right position of a
  vertical printed line and `j` is the bottom-to-top position of a horizontal
  printed line.
- A cyan vertical guide highlights `i`; an orange horizontal guide highlights
  `j`; the current candidate is a large magenta point.
- The user can accept the suggestion, click to move it, or mark
  `missing_print`, `occluded`, or `ambiguous`.

## Local pilot package

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_geometry_assisted_grid_control_pilot_20260811/`

The initial `input_receipt.json` SHA-256 is
`aa488f9af31953d3d4e32e41876acdedacee3d7eea7e2b27fbb2e227fba801f2`.
All eight records initially contain 66 `unreviewed` suggestions. The approved
formal A packet was checked separately and remained at 0 completed tasks and
0 locked maps when the pilot started.

## Verification

`3 passed`

Tests cover the exact 66-point inventory and display order, the `i`
left-to-right / `j` bottom-to-top convention including `G[2,2]`, and the
frozen 48-source-pixel crop rule.

## Claim boundary

The suggestions and user corrections are exposed development evidence. They
cannot be copied into formal A/B records or used for availability consensus,
fit/development/final controls, transform selection, registration residuals,
the final gate, or a 2-D model. A later scientific route still requires two
eligible blind human annotators using the immutable approved packet.
