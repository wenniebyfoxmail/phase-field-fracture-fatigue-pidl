# LTPP GeoForecast crack recognition track

Status: `RECOGNITION_GATE_FAILED`  
Owner: Mac-PIDL  
Updated: 2026-08-06

## Mechanism question

Can scanned LTPP hand-drawn distress maps be converted into reliable current-map
crack centerlines and crack-family labels while rejecting printed grids,
boundaries, handwriting, arrows/dimensions, WIM or patch boxes, hatching, and
other non-crack marks?

This is a recognition and label-production question. It is not a forecast of a
future map, a physical crack-width estimate, a material-point identity claim,
or a repair of the failed spatial-registration carrier.

## Claim boundary

A passing v1 result would qualify recognition only on the frozen 37-state,
six-section LTPP carrier and the preregistered raster frame. It would not
authorize ordinary road-photo deployment, cross-date crack-tip prediction,
future geometry, or mechanistic interpretation.

## Frozen inputs and receipts

| input | role | status / receipt |
|---|---|---|
| `local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/primary/images` | 37 blind source maps | all `1524x500`, 8-bit grayscale; hashes verified |
| `.../adjudicated/geojson` | adjudicated gold | 37 FeatureCollections; 249 geometries, 232 crack geometries |
| `.../adjudicated/adjudicated_manifest.json` | canonical label manifest | SHA-256 `6a9422bdcef707fa861b05ad0c817d6deaa4e4ad03ea636c46c5820f8b01f4ad` |
| `local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_preflight_v1_20260806/stage1_read_only_audit.json` | Stage 1 audit | SHA-256 `636b2bf1e0fdc1ab7b348d87ec99a79826c15651c32feed9e439d0da792cf244`; `PASS_STAGE1_READ_ONLY` |
| `scripts/ltpp_audit_crack_recognition_preflight.py` | audit implementation | SHA-256 `53342b00e5f814799592a69b81d9359d1b31194faaaf5bcb6e6282ef78574f90` |

The GeoJSON coordinate reference is explicitly `lower_left`, units metres,
extent `[0, 0, 15.24, 5]`. All observed coordinates lie in the declared frame
and therefore rasterize deterministically at 100 px/m to the image frame.
The locked GeoJSON embeds `primary_blind_id` and `asset_key`; the image-label
mapping was verified from those properties and the primary image-lock hashes,
without opening the sealed annotation mapping.

## Stage 1 qualification

Stage 1 passed all deterministic checks:

- 37/37 images and 37/37 labels are present and hash-consistent.
- All label geometries are supported `LineString` or `Polygon` objects.
- Pooled families are 128 transverse, 49 longitudinal, 54 fatigue/alligator,
  1 other crack, 2 uncertain, 8 other non-crack distress, and 7 water
  bleeding/pumping.
- The exact LOSO folds are the six complete physical sections:
  `06-1253`, `06-2041`, `06-2647`, `06-8149`, `06-8150`, `06-8201`.
- The existing transition package has 25 development and six future-time
  transitions; recognition will use section holdout, not random crops.

The independent primary-lock inventory records 199 handwriting/calculation
items and 67 lane/reference-boundary items. Grid, frame stroke, arrows or
dimensions, WIM/patch boxes, and hatching/X symbols are visibly present in the
source and semantically discussed in the annotation record, but are not
independently counted categories in the frozen adjudicated schema. They must be
retained as explicit negative/error-audit categories; no exact count is
invented from the current manifest.

## Experiment registry

| experiment | status | decision document |
|---|---|---|
| Stage 1 read-only qualification | `PASS_STAGE1_READ_ONLY` | `local_archive/.../stage1_read_only_audit.md` |
| B0 deterministic document/image baseline | `B0_BASELINE_NEGATIVE` | `ltpp_geoforecast_crack_recognition_b0_result_20260806.md` |
| B1 lightweight segmentation | `RECOGNITION_GATE_FAILED` | `ltpp_geoforecast_crack_recognition_b1_result_20260807.md` |
| B2 foundation-model assistance | `NOT_AUTHORIZED_YET` | same preregistration; generic masks cannot be gold |

## Active gate and next action

The preregistration freeze was completed before B0 evaluation. B0 was then run
on all six held-out sections and the required original / gold / prediction /
TP-FP-FN audit panels were generated and sidecar-validated.

B0 failed as a diagnostic baseline. The dated B1 amendment then authorized and
completed one trained challenger, which also failed the recognition gate. The
current execution therefore ends as `RECOGNITION_GATE_FAILED`. B2 remains
unselected; any further attempt requires a new amendment and must not overwrite
the B0 or B1 results.
