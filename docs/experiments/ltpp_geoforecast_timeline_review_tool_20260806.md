# LTPP chronological annotation review tool

## Status

`PASS_READ_ONLY_TIMELINE_VIEWER`

This is a bounded review tool for the frozen 37-state LTPP geoforecast packet. It is not a new model, experiment, annotation pass, or claim-changing result.

## Purpose

For one LTPP section at a time, display survey states in ascending survey-date order and show four separate layers:

1. clean source image;
2. locked AI primary annotation;
3. locked human secondary annotation;
4. frozen adjudicated annotation.

The page also reports adjudicated crack-line length, crack area, change from the preceding observed state, and the AI/human/final feature counts. Dates after the recorded LTPP `Out-of-Study` boundary are visibly flagged.

## Safety and interpretation boundary

- The server implements GET only; every POST request returns HTTP 405.
- It checks the adjudicated freeze manifest, the completed sealed-pairing gate, locked role labels, and identical primary/secondary image hashes before serving.
- It does not alter the primary, secondary, adjudication queue, or final GeoJSON files.
- Chronological display makes changes visible but does not imply monotonically increasing physical damage. Decreases may reflect mapping visibility, registration/annotation variation, or unrecorded events.

## Run

```bash
python scripts/ltpp_timeline_review_server.py \
  --packet-root ../local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805 \
  --section 06-1253 \
  --host 127.0.0.1 \
  --port 8769
```

Open `http://127.0.0.1:8769/`.

## Verification

```bash
python -m pytest -q tests/test_ltpp_timeline_review_server.py
```

The verification covers all 37 frozen states, six sections, chronological ordering, the final 06-1253 blind-ID mapping, the post-Out-of-Study flag, all four returned visual layers, and rejection of write requests.
