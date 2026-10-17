# External review request: document-aware LTPP crack recognition amendment

Please review the proposed amendment as a **no-fit methodological review**.
No new challenger has been trained or authorized.

## Materials

1. Current track:
   `docs/experiments/ltpp_geoforecast_crack_recognition_track.md`
2. B1 result:
   `docs/experiments/ltpp_geoforecast_crack_recognition_b1_result_20260807.md`
3. B1 failure audit:
   `docs/experiments/ltpp_geoforecast_crack_recognition_b1_failure_audit_20260807.md`
4. Amendment candidate:
   `docs/experiments/ltpp_geoforecast_crack_recognition_document_aware_amendment_candidate_20260807.md`
5. Existing-label proxy audit:
   `local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_b1_failure_audit_20260807/existing_noncrack_overlap_proxy.json`
6. Read-only preflight:
   `local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_b1_failure_audit_20260807/document_aware_no_fit_preflight_20260807.json`
7. Visual owner-review packet:
   `docs/reviews/ltpp_geoforecast_crack_recognition_document_aware_visual_review_packet_20260810.md`
8. Corrected derived B1 evidence figures:
   `local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_b1_failure_audit_20260807/review_figures/`
9. Amendment-owner visual review:
   `docs/reviews/ltpp_geoforecast_crack_recognition_document_aware_owner_visual_review_20260810.md`
10. Direct weak-negative target preview:
   `docs/experiments/ltpp_geoforecast_document_aware_target_preview_20260810.md`
11. Destructive-preprocessing preservation result:
   `docs/experiments/ltpp_geoforecast_document_preprocessing_preservation_result_20260810.md`

## Review questions

1. Is the proposed non-destructive representation—raw grayscale preserved,
   with a fixed document-structure mask used only as an auxiliary input cue—
   genuinely different from the completed single-output B1 Tiny U-Net?
2. Is it scientifically admissible to reuse adjudicated crack targets while
   treating the existing primary handwriting/boundary annotations as
   diagnostic candidates rather than gold?
3. Given that direct weak-negative reuse conflicts with adjudicated crack gold,
   is adjudicated crack target plus ordinary background scientifically
   admissible without semantic negative classes?
4. Are the six section-level LOSO folds, frozen thresholds, topology metrics,
   and unchanged recognition gate adequate?
5. Does the amendment preserve the claim boundary: current-map recognition
   only, with no spatial registration, physical-width, or future-map claim?
6. Should the decision be `APPROVE_NONDESTRUCTIVE_INPUT_FREEZE_ONLY`, `REVISE_BEFORE_NO_FIT`,
   or `REJECT_NEW_CHALLENGER`?
7. Is it adequate to leave WIM as ordinary background and a diagnostic error
   category, without a dedicated semantic output class or destructive ROI?
8. What pre-fit threshold should be frozen for the zero-crack-map specificity
   sentinel (predicted crack length and component count)?

## Current local preflight

The original read-only inventory remains valid, but two later no-fit gates
narrowed the admissible design:

- direct semantic reuse of primary weak negatives is not qualified because it
  conflicts with adjudicated crack targets on 26/37 maps;
- hard removal using the existing B0 `static_line_mask` failed preservation:
  pooled crack retention `69.06%`, with `P020` retaining `5.91%`.

No new weights exist and `fit_performed=false`. The request is now limited to
review of a non-destructive input cue; it does not request fit authorization.

## PIDL Experiment Gate

- Mechanism question: can a fixed document-structure cue reduce form/grid
  confusion without removing crack evidence from the raw scan?
- Claim changed if success: one non-destructive current-map recognition
  challenger becomes eligible for an exact no-fit implementation freeze.
- Claim changed if failure: the auxiliary-cue branch is rejected and the B1
  recognition failure remains the terminal result for this carrier.
- Cheaper diagnostic first: completed hard-removal preservation audit, which
  failed and ruled out destructive preprocessing.
- Minimal output asset: one external-review decision note plus one hashed
  no-fit input/architecture freeze if approved.
- Code/producer alignment: Mac may build and validate the no-fit package only;
  no training command is authorized here.
- Success criteria: external reviewer explicitly approves the non-destructive
  cue and names any required architecture/specificity revisions.
- Failure criteria: reviewer rejects the added cue or requires unavailable
  independent evidence.
- Registry destination: `docs/experiments/ltpp_geoforecast_crack_recognition_track.md`.
- Decision: `DIAGNOSE_FIRST__EXTERNAL_REVIEW_PENDING__NO_FIT`.

External review remains pending. This request does not authorize training.
