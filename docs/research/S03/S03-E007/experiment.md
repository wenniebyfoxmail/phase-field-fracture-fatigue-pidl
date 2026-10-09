---
storyline_id: S03
experiment_id: S03-E007
protocol_revision: v2
status: frozen-before-execution
started_at: 2026-10-09
closed_at:
primary_storyline: S03
related_storylines: []
scientific_verdict:
---

# D01 IB directional ruler-scale repeatability

## Question and claim boundary

Can the released IB ruler references provide a reproducible one-dimensional
millimetre coordinate along the ruler direction across repeat fixed-camera
images, before any crack-measurement operator is written?

- Claim class / domain: `C1 evidence-validity`; controlled experiment.
- Independent unit: physical beam (`Beam 4`, `Beam 5`, `Beam 6`). Images and
  ruler marks are repeated observations nested within beam.
- Allowed claim if passed: the fixed IB reference images contain an auditable
  directional millimetre carrier suitable for a later self-consistency study.
- Blocked regardless of result: validated physical crack width, isotropic 2-D
  scale, crack growth, future prediction, RUL, or road transfer.

## Exact evidence

Use only the two released fixed IB ruler references for each beam:

| Beam | Reference 1 | Reference 2 |
|---|---|---|
| Beam 4 | `G4-IB-Fixed/G4-IB_ref1.JPG` | `G4-IB-Fixed/G4-IB_ref2.JPG` |
| Beam 5 | `G5-IB-Fixed/G5-IB_ref1.JPG` | `G5-IB-Fixed/G5-IB_ref2.JPG` |
| Beam 6 | `G6-IB-Fixed/G6-IB_ref1.JPG` | `G6-IB-Fixed/G6-IB_ref2.JPG` |

Files must match the CRC and uncompressed size in the frozen S03-E004 remote
ZIP manifest and must decode as `5616 x 3744` images. No load-state crack image
or crack outcome may be read by this experiment.

Moving-camera ruler images are reserved for a later transfer diagnostic. They
do not enter the v1 primary decision because their zoom and pose differ and a
one-dimensional ruler cannot independently qualify a full planar homography.

## Frozen ruler procedure

1. Restrict processing to the bottom `50%` of the native image, where all three
   already-inspected reference-1 images place the ruler. Do not tune this crop
   after reference-2 results are viewed.
2. Detect the ruler's long axis from the longest near-horizontal dark boundary
   pair. Rectify only rotation and along-axis perspective; do not infer a 2-D
   isotropic beam-plane scale.
3. In the upper tick band of the rectified ruler, compute a one-dimensional
   vertical-line response. Retain a sequence only when at least 50 consecutive
   millimetre ticks can be indexed with no gap longer than two nominal ticks.
4. Fit a one-dimensional projective coordinate from image position to tick
   index using RANSAC. Convert tick index to millimetres; absolute ruler origin
   is irrelevant.
5. Report leave-one-centimetre-mark-out physical-coordinate error and local
   millimetre-spacing variation. The two fixed references are processed
   independently; reference 2 must not reuse the fitted map from reference 1.

Any manual rescue, beam-specific threshold, hand-selected mark deletion, or
post-result crop change makes v1 diagnostic-only and requires a new protocol.

## Necessary validity gates

- 6/6 exact files pass manifest size/CRC and image decoding.
- The frozen detector returns at least 50 indexed millimetre ticks in every
  image.
- The fitted coordinate is monotone and every reported value is finite.
- Both fixed references are available for all three beams.

## Primary criterion

For each beam, take the worse of its two reference images' 95th percentile
absolute leave-one-centimetre-mark-out coordinate error. The experiment passes
only if the maximum across the three beams is no more than `1.0 mm`.

Rationale: one millimetre is the smallest visible ruler division and therefore
the weakest defensible data-capability tolerance. Passing does not establish
sub-millimetre crack-width accuracy; failing stops all millimetre reporting.

Secondary diagnostics that do not vote: median error, interval-spacing CV,
reference-1 versus reference-2 fitted scale difference, detected tick count,
and beam-specific overlays.

## Outcome map and stop rule

```text
validity fails                    -> inadmissible
validity passes + primary passes  -> directional scale carrier qualified
validity passes + primary fails   -> negative for millimetre-scale reporting
primary cannot be computed        -> inconclusive
```

Run the frozen deterministic procedure once. Do not alter detection thresholds
or add a manual arm after viewing results. Stop after the six-image decision.

## Amendment

- `v2`, 2026-10-09, before reference-2 retrieval or execution: changed the
  generic search crop from the bottom 40% to the bottom 50%. Development
  reference 1 for Beam 5 places the ruler's upper tick band slightly above the
  40% boundary. No reference-2 pixels or scale outcomes had been viewed. The
  question, evidence, primary criterion and stop rule are unchanged.

## Minimum evidence

- selection manifest with CRC, SHA-256, dimensions and retrieval status;
- one row per image plus one row per beam in an exact CSV;
- decision JSON/Markdown and run receipt;
- a six-panel visualization showing detected ticks, fitted coordinate and the
  primary error on every image;
- an analysis README stating allowed and blocked conclusions.

## Next action if passed

Freeze a separate C2 cross-view self-consistency experiment in the S03-E006
local canonical footprint. Treat any millimetre conversion as directional and
uncertainty-bounded. Do not claim physical crack-width accuracy without an
independent crack-edge or gauge reference.
