# Owner-corner carrier render MVP v1 coordinate-convention failure — 2026-08-11

## Result

`EXPLORATORY_RENDER_INVALID_COORDINATE_CONVENTION__NOT_QUALIFIED`

The v1 render completed structurally and its immutable local package is
`ltpp_06_1253_owner_corner_carrier_render_mvp_v1_20260811`. Its 55 manifest
entries matched and its eight corner constructions were finite and
orientation-preserving. Those facts do not rescue the physical convention.

## Failure

The v1 preregistration interpreted the accepted frame as exactly 50 ft × 15 ft
and rendered 15.24 m × 4.572 m. Read-only comparison after rendering showed
that the frozen project coordinate system is instead `[0,15.24] × [0,5.00] m`:

- spatial-registration v1 audits y controls over 0–5.0 m;
- the v2 Tier B protocol freezes 15.24 m × 5.00 m;
- crack vectorization and recognition use extent `[0,0,15.24,5]`;
- the owner had explicitly rejected a 2001 crop because it omitted the
  `y=0–0.5 m` band.

Thus v1 would compress the transverse physical coordinate by 8.56% and cannot
be used as a scientific carrier. The package and preregistration remain
unchanged as evidence of the failed exploratory convention.

## Consequence

No final audit was run and no v1 image may enter 2-D modelling. A separately
named v2 may retain the locked source corners while changing only the target
carrier to the already-established 15.24 m × 5.00 m convention.
