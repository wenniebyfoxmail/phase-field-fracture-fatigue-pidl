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

## Required v2 split before any model selection

For every date, an independent reviewer must freeze a control inventory before
transform selection:

- development controls: at least 6 non-collinear Tier A/B points when a model
  has more than translation and diagonal scale;
- final audit controls: at least 8 non-collinear Tier A/B points, disjoint from
  development controls and withheld from all model/threshold choices;
- at least two final controls must constrain each relevant frame edge or
  boundary region, where the source geometry permits this;
- every point must have a source-image crop/overlay for manual review and a
  reason code identifying the stable non-damage reference.

If these conditions cannot be met for every date, no final v2 gate may run.

## Candidate models and selection

The future v2 implementation must test in this fixed order:

1. translation plus independent x/y scale (diagonal affine);
2. full affine, only if the first model fails the frozen development rule;
3. homography, only if affine fails and at least four independent non-collinear
   final-quality controls support it.

Local non-rigid models are excluded from the final route unless a separate
review proves that they preserve crack geometry; this experiment does not make
that case.

Model selection, tie-breaking, thresholds, quantile calculation, pixel-to-metre
conversion, image orientation, and crop policy must be frozen before final
controls are revealed. Final metrics use:

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

`PENDING_V2_EXTERNAL_REVIEW`

The review request must assess this protocol before any v2 transform is tuned
or any final audit is executed.
