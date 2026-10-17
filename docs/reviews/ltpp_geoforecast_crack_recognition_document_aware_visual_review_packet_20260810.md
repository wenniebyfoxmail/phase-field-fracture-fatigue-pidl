# Visual review packet: document-aware crack-recognition amendment

Status: `OWNER_REVIEWED__PREPROCESSING_NEGATIVE_ADDED__NO_FIT`  
Date: 2026-08-10

## Review question

Does the frozen B1 evidence justify one new, explicitly document-aware
recognition challenger, or should the current carrier remain closed after the
B0/B1 negative results?

## Figure 1: representative frozen B1 evidence

`local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_b1_failure_audit_20260807/review_figures/b1_visual_evidence_examples.png`

Each row shows the original scan, adjudicated gold, frozen B1 recognition
centerline, and a 10-pixel-tolerance overlay. Green is matched recognition
output, red is false-positive recognition output, and blue is missed gold. The
rows intentionally include a stronger case (`P020`) and three failure modes:
handwriting/form over-segmentation (`P008`), a no-gold map dominated by
form/text recognition output (`P002`), and
box/boundary domination (`P019`).

The existing frozen B1 four-panel assets inherit the literal label
`B0 prediction` from the B0 plotting helper. The new review figure corrects the
presentation label without modifying or overwriting any frozen B1 output.

## Figure 2: section-level evidence

`local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_b1_failure_audit_20260807/review_figures/b1_section_failure_summary.png`

The figure compares frozen section mean F1 and recall with the existing-label
boundary and handwriting proxy overlaps. Proxy overlap is diagnostic only:
the primary non-crack candidates are independent annotations, not adjudicated
false-positive gold.

## Owner observations

The amendment owner reviewed the figure on 2026-08-10 and recorded:

- `P020`: one crack remains missed; the stronger case still exposes a recall
  and continuity failure.
- `P008`: handwriting is visibly recognized as crack.
- `P002`: the map contains text/form structure but no target crack; the
  recognized crack output therefore represents a map-level specificity failure.
- WIM does not need semantic recognition and should not be a dedicated output
  class.

The amendment candidate was revised accordingly: no semantic hard-negative
head is proposed, zero-crack maps require a predeclared specificity sentinel,
and WIM remains ordinary non-target background plus a diagnostic error
category.

## Figure 3: destructive-preprocessing preservation audit

`local_archive/real_road_acquisition/ltpp_geoforecast_document_preprocessing_audit_v1_20260810/document_preprocessing_preservation_audit.png`

Columns show the original scan, the existing B0 static-document mask, retained
green versus erased red adjudicated crack target, and the resulting hard-white
removal. The rule retained only `69.06%` of pooled crack pixels and only `5.91%`
on `P020`. It is rejected and cannot be used as training preprocessing.

## What the proposed amendment changes

The completed B1 is a single-output Tiny U-Net trained on crack occupancy. The
revised candidate preserves the raw grayscale scan, permits a fixed
document-structure mask only as a non-destructive auxiliary input cue, and
uses crack occupancy/centerline/topology outputs without semantic form or WIM
heads. It retains the same 37 maps, six section-level LOSO folds, adjudicated
crack gold, and existing success gate.

## Owner decision boundary

Approval at this stage may authorize exact implementation and freeze only. It
does not authorize a held-out fit until architecture, label use, rasterization,
loss weights, seed, epochs, threshold, auxiliary-cue construction, and the
zero-crack specificity sentinel are fixed and hashed.
