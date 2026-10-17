# Owner visual review: document-aware crack-recognition amendment

Status: `REVISE_CANDIDATE__NO_FIT`  
Date: 2026-08-10

## Reviewed material

- `docs/reviews/ltpp_geoforecast_crack_recognition_document_aware_visual_review_packet_20260810.md`
- `local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_b1_failure_audit_20260807/review_figures/b1_visual_evidence_examples.png`
- `local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_b1_failure_audit_20260807/review_figures/b1_section_failure_summary.png`

## Owner observations

1. `P020` has one missed crack.
2. `P008` recognizes handwriting as crack.
3. `P002` contains text/form structure only and has no target crack.
4. WIM does not need recognition.

## Adopted revisions

- Keep recall and crack continuity as active design targets; the stronger B1
  example does not close the false-negative problem.
- Keep handwriting as an explicit hard-negative target/error category.
- Add a predeclared map-level specificity sentinel for zero-crack maps,
  reporting recognized crack length and component count.
- Remove WIM as a dedicated semantic output. Handle it using one frozen
  region-of-interest/exclusion rule or generic non-crack support.

## Decision boundary

This review revises the amendment candidate. It does not approve training or
held-out evaluation. Exact architecture, ROI/exclusion rule, zero-crack-map
threshold, losses, seed, epochs, and recognition binarization threshold remain
to be frozen.
