# LTPP spatial-registration improvement experiment v2

## Status

`EXPLORATORY_REGISTRATION_IMPROVEMENT`

This document freezes the design boundary for an independent control-point
availability diagnostic. It does not amend, rerun, or rescue the v1 audit.
The v1 result remains:

`SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`

No final v2 registration gate or 2-D crack model is authorized by this document.

## Mechanism question

Do the eight frozen 06-1253 survey images contain enough stable,
damage-independent geometric references to construct an independently reviewed
v2 registration audit, or is the coordinate carrier limited by source-data
observability rather than by the choice of transform?

## Claim boundary

This experiment may establish only one of:

- a documented inventory of candidate stable references;
- sufficient conditions for a future, externally reviewed v2 audit; or
- `INSUFFICIENT_INDEPENDENT_CONTROLS__NO_2D_MODEL`.

It cannot qualify the current carrier for 2-D crack-position or tip modelling.
It does not inspect, edit, or use crack geometry, WIM boxes, repair boxes, or
distress marks as controls.

## Frozen input boundary

The diagnostic reads the frozen v1 grid receipt and its rectified source images
only for inventory. It does not rerun or modify the v1 detector and does not
use the frozen crack labels. The v1 control-point receipt is treated as
historical and non-independent evidence.

The 2015 image is excluded because it is not part of the frozen eight-date
adjudicated packet.

## Control-point tiers

Only the following can qualify as final v2 controls:

1. **Tier A: external fixed references.** Independent page/measurement
   fiducials, fixed survey-frame marks, or independently documented physical
   reference marks.
2. **Tier B: independently adjudicated printed geometry.** Grid intersections,
   road boundaries, or cross-section/chainage marks manually identified from
   the source image under a separately frozen protocol, with the annotator
   explicitly excluding damage and annotations.

The existing v1 automatic line candidates are Tier C. They are useful for
diagnostic/development purposes only and are not independent final controls,
because the full candidate receipt and v1 outcomes have already been observed.

## Fixed v2 control roles before any model selection

Tier B collection follows the separately frozen
`ltpp_geoforecast_spatial_registration_v2_tier_b_annotation_protocol_20260807.md`.
The only Tier B candidates for the current eight-date route are the 66 printed
grid intersections `G[i,j]`, where `i = 0..10` and `j = 0..5`; their physical
coordinates are exactly `(15.24 * i / 10, 5.00 * j / 5)` metres. No crack,
WIM box, repair box, distress mark, or handwritten annotation may be a
candidate or substitute.

For every date, the control identity and role are frozen as follows:

- **final audit:** `G[0,0]`, `G[10,0]`, `G[0,5]`, `G[10,5]`, `G[2,2]`,
  `G[8,2]`, `G[2,3]`, and `G[8,3]`;
- **development selection:** `G[5,0]`, `G[5,5]`, `G[0,2]`, `G[0,3]`,
  `G[10,2]`, `G[10,3]`, `G[3,1]`, and `G[7,4]`;
- **fit:** every other Tier A/B point that passes the frozen Tier B consensus
  rule.

The final set is held by an annotation custodian and never disclosed to the
implementer or used in fitting, model choice, thresholds, missing-data
decisions, or image-processing choices. The eight final IDs intentionally
span all frame corners and both interior bands. A date is ineligible for a
final v2 gate if any final or development ID is missing, ambiguous, or fails
the annotation-consensus rule; there is no replacement, reassignment, or date
deletion. A date also fails preflight if its fit set has fewer than eight
non-collinear points.

## Candidate models and selection

The future v2 implementation must test independently for each date in this
fixed order, always fitting only the frozen fit set:

1. translation plus independent x/y scale (diagonal affine);
2. full affine, only if the diagonal-affine model fails the frozen development
   rule;
3. homography, only if affine fails the frozen development rule and the fit
   set contains at least eight non-collinear points.

For each candidate model, development errors are computed only on the eight
development controls. A candidate **fails development** if any of its
development median, linear p95, or maximum errors exceeds respectively
`0.05 m`, `0.10 m`, or `0.20 m`, or if its coordinate mapping reverses either
axis or maps any source-frame corner outside the declared physical rectangle by
more than `0.20 m`. The first model in the ladder that does not fail is selected
for that date. If homography fails or is ineligible, the date fails preflight.
No model is selected because it is merely numerically better after a simpler
model passes.

Homography eligibility and selection therefore depend only on fit and
development Tier A/B controls. Final audit controls may meet the same quality
standard but never determine whether homography is tried, selected, or tuned.

Local non-rigid models are excluded from the final route unless a separate
review proves that they preserve crack geometry; this experiment does not make
that case.

Model selection, tie-breaking, thresholds, quantile calculation, pixel-to-metre
conversion, image orientation, and crop policy must be frozen before final
controls are revealed. The selected transform is not refitted after development
selection. Final metrics use:

```python
median = numpy.median(errors)
p95 = numpy.quantile(errors, 0.95, method="linear")
maximum = numpy.max(errors)
```

The engineering gate remains median `<= 0.05 m`, p95 `<= 0.10 m`, and maximum
`<= 0.20 m` for every date; it is not a statistical confidence interval.

## One-shot termination

The future final audit may run once only after an external review approves the
frozen protocol and every date has the required independent controls. Missing
controls, post-selection control replacement, date deletion, threshold
relaxation, metric changes, or post-hoc model changes terminate the route as
`INSUFFICIENT_INDEPENDENT_CONTROLS__NO_2D_MODEL`.

## External review status

The first external methodological review returned
`REVISE_V2_PROTOCOL_BEFORE_DIAGNOSTIC`; its three blocking findings are adopted
in this revision. The revised protocol is
`PENDING_MINIMAL_REVISION_REVIEW`. No v2 transform may be tuned and no final
audit may execute until the reviewer returns
`APPROVE_V2_AVAILABILITY_DIAGNOSTIC_ONLY`.
