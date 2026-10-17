# LTPP document-aware target preview

Status: `DIRECT_WEAK_NEGATIVE_REUSE_NOT_QUALIFIED__NO_FIT`
Date: 2026-08-10

## Five-question pre-launch gate

1. **Mechanism question:** can the frozen adjudicated crack target be combined
   safely with existing primary non-crack candidates and a WIM exclusion mask?
2. **Claim change:** success would qualify only the target/mask construction
   for exact implementation; failure blocks direct reuse of auxiliary labels.
3. **Cheaper diagnostic:** render all 37 masks and inspect representative maps
   before writing or fitting a challenger.
4. **Minimal asset:** one four-column review figure plus a JSON receipt and
   per-map masks.
5. **Registry handoff:** update the canonical crack-recognition track; no new
   experiment-inventory row or training authorization is created.

## Inputs

- 37 original primary scans;
- frozen adjudicated crack GeoJSON, manifest SHA-256
  `6a9422bdcef707fa861b05ad0c817d6deaa4e4ad03ea636c46c5820f8b01f4ad`;
- existing primary independent features for handwriting, lane/reference
  boundary, other non-crack distress, and WIM evidence notes.

No chronology, future map, traffic, climate, maintenance, registration output,
B1 score, or new model fit enters target construction.

## Preview rules

- Green: adjudicated crack target.
- Orange: existing weak-negative support after conflict filtering.
- Magenta: primary weak-negative candidate within 10 px of adjudicated crack;
  quarantined and unavailable for training.
- Purple: WIM carrier exclusion after conflict filtering; never a recognition
  output class.
- Red in the WIM panel: WIM candidate within 10 px of adjudicated crack;
  quarantined and unavailable for exclusion.

The 7-pixel support/exclusion width and 10-pixel crack guard are preview rules,
not yet an approved training freeze.

## Result

The target preview was generated for all 37 maps. Direct reuse of primary
non-crack candidates fails the no-fit safety check:

- 26/37 maps contain weak-negative/crack conflicts;
- 379,512 buffered pixels are quarantined as weak-negative conflicts;
- 4/37 maps contain WIM/crack conflicts;
- 10,491 buffered pixels are quarantined as WIM conflicts.

The large conflict is expected in part because the primary independent layer
and adjudicated layer assign different semantics to some long horizontal and
reference structures. It means the primary candidates may remain diagnostic,
but cannot be silently promoted to supervised hard-negative truth.

## Decision

Do not authorize challenger training. The next amendment revision must choose
one of two auditable routes:

1. use adjudicated crack gold plus ordinary background only, with deterministic
   document preprocessing and no auxiliary semantic-negative head; or
2. create a small, independently reviewed hard-negative supplement that does
   not overlap crack gold.

WIM remains outside the recognition target. Any carrier-specific WIM exclusion
must be visually reviewed, crack-protected, and frozen before use; otherwise it
must remain diagnostic only.

## Assets

- figure:
  `local_archive/real_road_acquisition/ltpp_geoforecast_document_aware_target_preview_v1_20260810/document_aware_target_preview.png`;
- receipt:
  `local_archive/real_road_acquisition/ltpp_geoforecast_document_aware_target_preview_v1_20260810/target_preview_receipt.json`;
- implementation:
  `scripts/ltpp_build_document_aware_target_preview.py`.

