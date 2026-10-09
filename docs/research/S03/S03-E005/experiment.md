---
storyline_id: S03
experiment_id: S03-E005
protocol_revision: v1
status: closed
started_at: 2026-10-09
closed_at: 2026-10-09
primary_storyline: S03
claim_class: C2_state_measurement
evidence_domain: controlled_experiment
scientific_verdict: inadmissible
---

# D01 fixed-versus-moving-view repeatability diagnostic

## Road-Fracture Experiment Gate

- **Bounded question:** after geometric registration onto a fixed-camera image,
  is same-load cross-view variation smaller than the apparent image change
  between two well-separated load stops for all three D01 beams?
- **Independent unit:** physical beam (`Beam 4`, `Beam 5`, `Beam 6`). Images,
  mobile poses and load stops are repeated observations, not independent units.
- **Paired unit:** same beam x region IA x declared load stop. Region IA is
  selected before image retrieval because it is the lexicographically first
  region present for both fixed and moving cameras in every beam.
- **Evidence domain:** controlled reinforced-concrete beam experiment.
- **Allowed conclusion:** a diagnostic statement about whether this fixed
  registration and image-measurement pipeline resolves load-step change above
  cross-view variation in the selected D01 observations.
- **Blocked conclusion:** no crack-width accuracy, true crack-growth magnitude,
  future prediction, RUL, temporal-token sufficiency, field validity or road
  transfer.

## Frozen observations

Use the lowest and highest *non-final* load stops whose fixed-image time lies
inside the filtered machine table. This avoids the final-state coverage and
Beam 5 timestamp conflicts identified by S03-E004.

| Beam | Low stop | High stop | Fixed times | Moving workbook times |
|---|---:|---:|---|---|
| Beam 4 | 10 kN | 50 kN | 225, 588 s | 271/278/287 and 605/608/611 s |
| Beam 5 | 10 kN | 60 kN | 228, 729 s | 265/269/271 and 746/748/751 s |
| Beam 6 | 10 kN | 40 kN | 183, 460 s | 214/216/219 and 478/480/483 s |

For each beam and stop, retrieve one fixed image and the three corresponding
K2/IA moving images, plus the released fixed and moving ruler references needed
to audit scale. No other image may be substituted after results are viewed.

## Registration and common visible domain

1. Convert images to grayscale and cap the longer side at 2,000 pixels while
   preserving aspect ratio. Retain the exact scale back to fixed native pixels.
2. Estimate each moving-to-fixed planar homography with SIFT descriptors,
   Lowe-ratio matching and RANSAC. No learned feature model is allowed.
3. A registration is valid only with at least 50 inliers, inlier ratio at least
   0.20, median inlier reprojection error at most 3.0 fixed-native pixels, and
   warped overlap at least 0.50 of the fixed image.
4. For a beam-stop pair, the common visible mask is the intersection of the
   fixed image and all valid warped moving views, eroded by 20 working pixels.
   At least two of three moving views and at least 30% fixed-image coverage are
   required. Record every failed view; never replace it opportunistically.
5. Register the high-load fixed image to the low-load fixed image with the same
   validity checks so both stops use a common fixed-camera coordinate system.

## Scale and measurement definition

- Ruler references are inspected for each beam and camera type. Record any
  auditable pixels-per-millimetre estimate and its method. If the ruler cannot
  be calibrated without guessing, preserve scale as unavailable and block any
  physical-width statement.
- The diagnostic measurement is not crack width. Within the common mask, each
  registered grayscale image is locally contrast-normalized and converted to a
  fixed multiscale dark-ridge response. Parameters are fixed in code before the
  selected observations are analysed.
- For each beam and stop, same-stop cross-view variation is the median absolute
  ridge-response difference between the fixed image and each valid registered
  moving view, aggregated by the median across views.
- Between-stop apparent change is the median absolute ridge-response difference
  between the registered low- and high-load fixed images on their common mask.
  This is an image-change comparator, not an independently measured true crack
  increment.

## Primary criterion

For every one of the three beams,

```text
same-stop cross-view variation < between-stop apparent fixed-view change
```

must hold at both selected stops when the within-stop term is compared with the
single low-to-high fixed-view change for that beam. Equivalently, the larger of
the two within-stop variations must be strictly below the between-stop change.

The conjunction is necessary because the claim concerns all three independent
beams. The rationale is the measurement-resolution condition: nuisance
variation must be smaller than the effect the pipeline is asked to resolve.
No post-result tolerance or beam exclusion is allowed.

## Outcome map and stop rule

- Any identity, decoding, registration or common-mask validity failure ->
  `INADMISSIBLE_D01_MULTIVIEW_REPEATABILITY`.
- Validity passes and the primary criterion passes for all beams ->
  `PASS_D01_MULTIVIEW_REPEATABILITY_DIAGNOSTIC`.
- Validity passes but any beam fails ->
  `NO_GO_D01_MULTIVIEW_REPEATABILITY`.
- The physical-scale audit is missing or ambiguous -> physical crack-width
  claims remain blocked even if the dimensionless diagnostic passes.

Stop after this single frozen pipeline. Do not tune feature, RANSAC, mask,
ridge or contrast parameters after viewing the six selected beam-stop groups.

## Minimum evidence

- exact versioned source paths and SHA-256 for every retrieved image;
- frozen selection/mapping table and run receipt;
- per-view registration table with failures, inliers, reprojection error and
  overlap;
- per-beam within-stop and between-stop measurement table;
- scale-calibration audit, exact decision JSON and one decision figure showing
  all independent beams plus representative registered overlays;
- explicit statement that fixed-view change is not independent crack truth.

## Decision before image retrieval

`READY_FOR_NO_TRAINING_DIAGNOSTIC`. Local deterministic image processing is
authorized; model training and prediction claims are not.

## Analysis execution

- Attempt: `S03-E005-A001`; Mac deterministic CPU, no training.
- Final execution code:
  `6a0fb60bf6fa96443a62eb7f92b3eb6cecc48c56`, clean tree.
- Runtime: `37.2 s` after the 33 frozen images had been range-retrieved; initial
  remote retrieval took about 16 minutes and was not expanded to the 3 GB ZIP.
- Evidence package:
  `$PROJECT/local_archive/experiments/S03-E005/analysis/`.
- All 33 selected images were revalidated by SHA-256 and decoded successfully.

## Evidence result

- Fixed high-to-low registrations pass for all three beams: overlap
  `0.9939–0.9990`, median native-pixel reprojection error `1.68–2.21 px`, and
  `656–735` RANSAC inliers.
- All 18 moving-to-fixed views fail the frozen `0.50` full-fixed-frame overlap
  gate. Their warped footprints cover only `0.0276–0.1320` of the fixed frame.
- Moving-view reprojection error is nevertheless low (`0.35–1.44 px`); 13/18
  views have at least 50 inliers and fail only on overlap. Five views fail both
  overlap and the 50-inlier gate.
- No beam-stop group retains the required two valid moving views. Therefore the
  within-stop versus between-stop measurement table is intentionally empty and
  the primary criterion is not computed.
- Visual inspection confirms a ruler in each selected fixed and moving
  reference. Because v1 did not freeze ruler-tick endpoints or perspective
  correction, physical scale remains unqualified and no millimetre result is
  permitted.

## Decision visualization

- `d01_multiview_repeatability.png/.pdf` shows every moving view against the
  frozen overlap and inlier thresholds.
- `scale_reference_contact_sheet.png` shows all nine selected ruler references
  in a fixed beam-by-camera layout.
- Both figures have same-stem Markdown sidecars recording provenance and claim
  boundaries.

## Scientific verdict

`INADMISSIBLE_D01_MULTIVIEW_REPEATABILITY`.

This is not a negative crack-measurement result. The validity failure occurs
because v1 asks each moving close-up to cover half of the much wider fixed
camera frame. That estimand is incompatible with the released acquisition
geometry, even though many local feature matches are stable. S03-E005 is not
rescued by relaxing its viewed gate.

## Claim impact

The experiment closes the whole-fixed-frame comparison route. It does not
establish cross-view measurement error, crack width, true crack change,
prediction, RUL, temporal-token sufficiency, field validity or road transfer.

No independent evidence-readiness review was requested for this conservative
admissibility stop. The exact inputs, code, metrics and figures are retained for
review, but S03-E005 is not labelled `Evidence Ready`.

## Next action

If the measurement route remains useful, freeze a separate experiment for the
intersection of registered *mobile footprints*, normalize overlap to the mobile
footprint, and preregister ruler-tick annotation before reporting physical
units. Keep beam as the independent unit and do not reuse S03-E005's verdict as
evidence of measurement accuracy.
