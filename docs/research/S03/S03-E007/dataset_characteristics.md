# D01 IB scale and target qualification before measurement code

Date: 2026-10-09  
Status: dataset-first route decision; no crack-measurement code or outcome was
run for this step.

## Question

After S03-E006 qualified local registration on region IB, does the released
evidence support a physical crack-width target, or only a cross-view
self-consistency target?

## Evidence inspected

- Three IB fixed ruler references already retrieved for S03-E006:
  `G4-IB_ref1.JPG`, `G5-IB_ref1.JPG`, and `G6-IB_ref1.JPG`.
- The complete remote ZIP manifest, which also lists one second fixed reference
  for every beam and moving-camera ruler references for every beam.
- S03-E004--E006 identity, registration, support, and scale-boundary records.

The fixed IB references are Canon images at `5616 x 3744`. In all three beams,
the steel ruler lies on or immediately against the visible beam face. Millimetre
ticks and centimetre numbers are visible over a long span. The ruler is not
fronto-parallel: its image line and apparent tick spacing vary with pose, so a
single global pixels-per-millimetre constant read from the raw image would be an
unqualified shortcut.

## Dataset capability

### Present

- A directional metric carrier: repeated ruler ticks along the beam's
  horizontal direction.
- Two fixed-camera ruler images per beam, allowing a within-beam repeat-image
  check.
- At least one moving-camera ruler image per beam, allowing camera-family scale
  transfer to be diagnosed.
- S03-E006 homographies mapping fixed and moving observations into a local
  canonical plane.

### Missing

- No released per-state crack-width measurement, microscope/gauge reference,
  or adjudicated crack edge annotation.
- No two-dimensional calibration target. A one-dimensional ruler primarily
  qualifies distance along its own direction; it does not by itself prove an
  isotropic planar metric everywhere on the beam face.
- No independent evidence that an image-derived dark ridge or edge pair equals
  the physical crack opening.

## Method consequence

The data can support a new C1 experiment that estimates a **directional ruler
mapping** and tests its repeat-image and cross-camera transfer uncertainty. It
cannot yet support a confirmatory claim of physical crack-width accuracy.

Therefore the next C2 target, if scale qualification passes, must initially be
**cross-view self-consistency of a frozen observable in the registered local
footprint**. Millimetres may be reported only as a directional calibration with
its uncertainty and must not be described as validated crack width. A physical
width-accuracy claim requires an external or independently annotated reference.

## Route decision

`READY_TO_FREEZE_DIRECTIONAL_SCALE_REPEATABILITY__PHYSICAL_WIDTH_REFERENCE_ABSENT`

Next protocol should retrieve exactly the second fixed references and the
released moving ruler references, freeze ruler-mark selection before fitting,
and quantify within-beam repeat-image plus fixed-to-moving scale-transfer
uncertainty. Do not write crack segmentation or width code before that result.
