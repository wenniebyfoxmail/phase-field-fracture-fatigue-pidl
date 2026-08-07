# LTPP 06-1253 physical-grid rectification gate (2026-08-05)

## Result

All nine `0-50 ft` distress maps pass the frozen physical-grid rectification gate. This authorizes coordinate comparison; it does not authorize any crack mask.

| Survey date | Qualification mode | Vertical matches | Horizontal matches | Relative aspect error |
|---|---|---:|---:|---:|
| 1991-06-10 | dense internal grid | 11 | 6 | 0.0041 |
| 1995-10-24 | outer border pair | 2 | 6 | 0.0157 |
| 1997-02-28 | dense internal grid | 11 | 6 | 0.0005 |
| 1998-04-07 | dense internal grid | 11 | 6 | 0.0215 |
| 2001-09-13 | dense internal grid | 8 | 6 | 0.1275 |
| 2003-05-14 | dense internal grid | 11 | 6 | 0.0039 |
| 2007-11-06 | dense internal grid | 8 | 5 | 0.0205 |
| 2012-04-17 | dense internal grid | 11 | 6 | 0.0013 |
| 2015-03-02 | dense internal grid | 11 | 6 | 0.0255 |

The qualified output root is:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_rectified_grid_v3_20260805`

Each map is represented on a `1524 x 500` pixel canvas corresponding to `15.24 m x 5.00 m`, or `0.01 m/pixel`. The coordinate transform for later vector labels is:

```text
x_m = x_pixel / 100
y_m = (500 - y_pixel) / 100
```

The output contains `grid_gate_results.json`, `grid_gate_results.csv`, a contact sheet, per-date overlays, rectified images, deliberately named `rectified_ink_not_crack_mask.png` files, and a 30-entry SHA-256 manifest.

## Qualification modes

`dense_internal_grid` requires:

- absolute deskew angle no greater than 5 degrees;
- at least 8 of 11 vertical regular-grid matches;
- at least 5 of 6 horizontal matches;
- relative physical-aspect error no greater than 0.20;
- border ink support at least 0.10.

`outer_border_pair` is an independent fallback for faded internal point grids. It requires:

- absolute deskew angle no greater than 5 degrees;
- both vertical borders and at least 5 horizontal lines;
- relative physical-aspect error no greater than 0.05;
- border ink support at least 0.25.

Only `1995-10-24` uses this fallback. Its overlay was visually checked to ensure that the selected rectangle spans the printed 0-50 ft and 0-5 m boundaries.

## Evidence boundary

The rectified pixels still contain:

- survey grid lines;
- lane and shoulder boundaries;
- handwritten distress codes and severity labels;
- circles, calculations, and other annotations;
- actual distress strokes.

Therefore the rectified images are qualified coordinate carriers, not damage fields. No PIDL or Freeze-Then-Select experiment may consume the raw `ink` image as a crack target.

## Failed automatic semantic extraction

Five conservative automatic candidate variants were generated and visually audited. None passed the semantic gate.

- `v1` retained wavy lane boundaries as high-confidence cracks.
- `v2` removed the boundaries but fragmented vertical crack strokes at grid intersections.
- `v3` reconnected vertical strokes but labelled periodic 1991 grid columns as cracks.
- `v4` and `v5` added periodic-grid models, but regular grid columns remained selected while the true central handwritten crack remained uncertain.

All candidate packages retain `review_status = not_reviewed` and are diagnostic only. They must not be promoted to frozen labels or used to report crack length, tips, initiation, or support recovery.

## Next gate

The next authorized operation is independent centerline vectorization under [ltpp_06_1253_semantic_vectorization_protocol_20260805.md](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload%20code/docs/ltpp_06_1253_semantic_vectorization_protocol_20260805.md).
