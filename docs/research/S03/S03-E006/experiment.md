---
storyline_id: S03
experiment_id: S03-E006
protocol_revision: v1
status: prepared
started_at: 2026-10-09
primary_storyline: S03
claim_class: C1_evidence_validity
evidence_domain: controlled_experiment
---

# D01 held-out local-footprint registration qualification

## Dataset-first route decision

The method is bound to `dataset_characteristics.md`, committed before this
protocol. IA is development evidence because its pixels and geometry were
viewed in S03-E005. Region IB is the lexicographically first remaining region
and is frozen as an untouched image holdout. IB also changes the fixed-camera
family from GoPro in IA to Canon, making it a useful sensor-transfer check.

No IB image pixels may be inspected before this protocol and the exact file
selection are committed.

## Road-Fracture Experiment Gate

- **Bounded question:** on held-out region IB, can the three moving-camera views
  at each selected load stop be mapped to one fixed-reference plane with enough
  shared *local* support for a later measurement study?
- **Claim class / domain:** C1 evidence-validity / controlled experiment.
- **Independent unit:** physical beam (`Beam 4`, `Beam 5`, `Beam 6`).
- **Repeated observations:** region, load stop and mobile pose. They do not
  increase the independent sample count beyond three beams.
- **Allowed inputs:** exact IB fixed reference, fixed low/high state and three
  moving images per selected stop; source filenames and workbook mapping.
- **Forbidden inputs:** IA crack-response values, final load stops, manual
  outcome-driven crops, future images for transform selection, trained features
  or post-result threshold changes.
- **Allowed conclusion if pass:** held-out local planar registration and support
  are qualified for designing a separate crack-measurement protocol.
- **Blocked conclusions:** crack width, true crack change, DIC/CMfM accuracy,
  future prediction, RUL, temporal-token sufficiency, field validity and road
  transfer.

## Frozen holdout observations

Use the same lowest/highest non-final load-stop rule as the IA development
audit, now applied to IB. Filenames are verified against the remote manifest and
the workbook before pixel retrieval.

| Beam | Fixed reference | Low fixed / moving triplet | High fixed / moving triplet |
|---|---|---|---|
| Beam 4 | `G4-IB_ref1.JPG` | `t=225`; `244/249/254` | `t=588`; `594/597/600` |
| Beam 5 | `G5-IB_ref1.JPG` | `t=228`; `247/248/249` | `t=729`; `737/739/741` |
| Beam 6 | `G6-IB_ref1.JPG` | `t=183`; `03_18/03_21/03_23` | `t=460`; `07_48/07_50/07_53` |

Retrieve exactly 27 images: three beams x (one fixed reference, two fixed
states, six moving states). No alternate image may replace a failed view.

## Frozen canonicalization method

1. Use the fixed IB ruler-reference image as the canonical plane. Resize each
   image with preserved aspect ratio to a maximum side of 2,000 pixels for
   feature processing; retain scale back to canonical native pixels.
2. Register the two fixed states and each moving state directly to the canonical
   reference using grayscale CLAHE, SIFT, Lowe ratio `0.75`, and RANSAC planar
   homography with a `2.0` working-pixel threshold.
3. Fixed-to-reference validity requires at least 50 inliers, inlier ratio at
   least `0.20`, median reprojection error at most `3.0` canonical native pixels,
   and reference-frame overlap at least `0.90`.
4. Moving-to-reference validity requires at least 15 inliers, inlier ratio at
   least `0.30`, median reprojection error at most `3.0` canonical native pixels,
   and a finite, non-self-intersecting footprint with positive area. There is no
   full-reference-frame coverage threshold.
5. The local footprint for one stop is the intersection of its three valid
   moving footprints in canonical coordinates. Its normalized support is that
   intersection area divided by the smallest of the three footprint areas.
6. Cross-stop support is the intersection of the low- and high-stop local
   footprints divided by the smaller stop-footprint area. Geometry alone defines
   these masks; crack response, darkness or load-change magnitude is not used.

The moving thresholds were selected on IA development geometry before IB pixel
retrieval. They are not evidence about IB and cannot be changed after retrieval.

## Scale status

The fixed canonical reference must visibly contain a ruler and its image path is
recorded. Numerical ruler-tick annotation and perspective-corrected pixels per
millimetre are intentionally outside S03-E006. Thus a pass qualifies geometry
only and does not authorize a physical-width claim.

## Primary criterion

After all registration validity gates pass, compute the minimum of:

- six same-stop normalized supports (three beams x low/high); and
- three cross-stop normalized supports (one per beam).

Return `PASS_D01_LOCAL_REGISTRATION_HOLDOUT` only if this minimum is at least
`0.75`. The threshold requires a shared local domain covering at least
three-quarters of the smallest available footprint, leaving enough support for
a later common-ROI measurement while tolerating handheld pose variation.

## Outcome map and stop rule

- Any fixed or moving registration validity failure ->
  `INADMISSIBLE_D01_LOCAL_REGISTRATION_HOLDOUT`.
- Validity passes and minimum normalized support >= `0.75` ->
  `PASS_D01_LOCAL_REGISTRATION_HOLDOUT`.
- Validity passes but minimum support < `0.75` ->
  `NO_GO_D01_LOCAL_REGISTRATION_HOLDOUT`.

Stop after this geometry qualification. Do not add a crack detector, image
difference, ruler calibration or measurement result to rescue or extend v1.

## Minimum decision visualization

- One row per beam showing the canonical fixed reference, all-six footprint
  intersection and footprint boundaries for low/high moving views.
- One aggregate panel showing all same-stop and cross-stop normalized supports
  against the frozen `0.75` threshold.
- Display all three beams; no example selection.

## Minimum evidence

- exact 27-image selection manifest with CRC and SHA-256;
- clean-code run receipt and decoding checks;
- per-view matches, inliers, ratio, reprojection error and footprint area;
- per-beam same-stop and cross-stop support table;
- decision JSON/Markdown, PNG/PDF decision figure and same-stem sidecar;
- explicit scale and claim boundaries.

## Decision before holdout retrieval

`READY_FOR_HELDOUT_LOCAL_REGISTRATION_AUDIT`. No training or crack-response
analysis is authorized.
