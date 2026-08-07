# LTPP 06-1253 repeated-geometry gate

Audit date: 2026-08-05.

## Decision

The repeated physical-geometry gate passes conditionally. InfoPave provides nine survey dates and ten fixed 50-ft maps per date for asphalt section `06-1253`. A frozen audit of the `0-50 ft` segment confirms that all nine drawings use the same longitudinal `0-50 ft` and lateral `0-5 m` physical grid.

This is stronger than PaveTrack's repeat-scene key because the LTPP drawings explicitly encode station and lateral position. It is weaker than a calibrated crack mask because the files are scanned manual maps with handwritten codes, variable crop, skew, and resolution.

## Frozen download

- Maps: 90.
- Survey dates: 9.
- Segments per date: 10.
- Downloaded bytes: 18,994,135.
- Width range: 2,861–5,871 px.
- Height range: 918–2,457 px.
- Original encoding: transparent RGBA with black ink stored in the alpha channel.

The full manifest records source URL, section, construction number, date, segment, local path, dimensions, bytes, and SHA-256:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_maps_20260805/map_manifest.csv`

## Coordinate audit

The nine fixed `0-50 ft` maps show:

- A longitudinal axis from 0 to 50 ft, approximately 0 to 15.24 m.
- A lateral axis from 0 to 5 m.
- Repeated lane/shoulder boundaries and manually drawn distress lines.
- Distress type/severity codes and surveyor notes.

Pixel coordinates cannot be compared directly because scan dimensions and cropping differ. Each map must be rectified from its grid corners into a canonical physical raster before line extraction.

## Evidence boundaries

- Authorized: crack-line and tip position in the rectified station-lateral coordinate frame.
- Not authorized: physical crack width inferred from drawn line thickness.
- Not authorized: treating handwritten annotations, grid lines, or lane boundaries as crack pixels.
- Initiation timing is interval-censored between survey dates, not an exact date.
- The first seven viewer events are labelled as transverse-profile collection even though their exposed images visibly contain manual distress drawings. This metadata inconsistency must remain explicit.

## Next processing gate

1. Detect or manually qualify the four physical grid boundaries for every map.
2. Warp accepted maps to a canonical `15.24 m × 5 m` raster.
3. Separate fixed grid/lane geometry from distress strokes and handwritten codes.
4. Vectorize crack lines and attach the LTPP distress type/severity codes.
5. Check monotonic persistence only within compatible survey semantics; do not force repaired or missing lines to persist.
6. Freeze chronological training and future-test dates before fitting a field adapter.

No real-road prediction result is claimed yet. The traffic, climate, FWD, structure, maintenance, and moisture joins remain outside this geometry receipt.
