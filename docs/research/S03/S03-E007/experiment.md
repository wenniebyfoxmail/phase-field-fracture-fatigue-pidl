---
storyline_id: S03
experiment_id: S03-E007
protocol_revision: v3
status: closed
started_at: 2026-10-09
closed_at: 2026-10-09
primary_storyline: S03
related_storylines: []
scientific_verdict: FAIL_VALIDITY
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
2. Resize the search crop to `0.25x`, convert it to grayscale, apply a `5 x 5`
   Gaussian blur and Canny thresholds `40/120`, then run probabilistic Hough
   detection with `rho=1`, `theta=pi/720`, vote threshold `80`, minimum line
   length `25%` of the working-image width and maximum gap `40` working pixels.
   Keep segments within `8 degrees` of horizontal and choose the segment with
   the smallest midpoint y-coordinate (longest segment breaks an exact tie).
   This is the ruler's single upper boundary; a lower boundary is not required.
3. Map that line to native pixels. Across its detected x-span, sample the band
   from `5` through `90` native pixels below the line. Average the absolute
   horizontal Sobel response over the band and smooth it with a one-dimensional
   Gaussian sigma of `1` pixel. Estimate the nominal tick period from the
   strongest autocorrelation lag in `[8, 30]` native pixels. Detect peaks with
   minimum separation `floor(0.55 * period)` and prominence `0.25` times the
   response standard deviation. Assign integer tick indices by rounded peak
   separation divided by the nominal period. Retain the longest sequence with
   step sizes of one or two ticks; require at least 50 indexed ticks.
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
- `v3`, 2026-10-09, after reference-2 retrieval but before any reference-2
  pixel inspection or scale computation: replaced the lower-boundary
  requirement with the exact single-upper-boundary and tick-response procedure
  above. Development on reference 1 showed that Beam 6's ruler lower edge
  merges into the dark background, while the upper boundary and periodic tick
  response remain detectable. Reference 2 stayed excluded from development.
  The question, evidence, primary criterion and stop rule are unchanged.

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

## Formal result and closure

- Run: `S03-E007-R001` on Mac-PIDL as lightweight deterministic CV only.
- Reviewed execution commit:
  `6b362570d7e8889b631bc49f8c28ce3864f7d6f7`; clean checkout.
- Selection-manifest SHA-256:
  `0e2dd2232f47e79523478972747ca957e79f1a3fa5745af15d77a291e75db383`.
- Independent code review: `PASS_CODE_READY` after closing dirty-checkout and
  beam-level CSV blockers.
- Input identity: 6/6 files passed frozen size, CRC, SHA-256, decoding and
  `5616 x 3744` dimensions.
- Detected tick counts for Beam 4 ref1/ref2, Beam 5 ref1/ref2 and Beam 6
  ref1/ref2 were `137/126`, `179/180` and `165/26`, respectively.
- Beam 6 reference 2 failed the necessary `>=50` indexed-tick gate. Therefore
  the frozen scientific verdict is `FAIL_VALIDITY`.
- The diagnostic maximum beam-worst LOMO p95 was `0.164201 mm`, below the
  `1.0 mm` primary threshold, but it has no qualifying vote after a necessary
  validity failure and cannot rescue the experiment.
- The minimum evidence package contains the exact 6 image + 3 beam CSV,
  summary, decision, clean run receipt, six-panel detection view, six-panel
  fitted-coordinate view, reproduction checks and analysis README.
- Independent evidence review: `PASS_EVIDENCE_READY`; the fitted-coordinate
  visualization blocker was closed without rerunning or changing the formal
  decision.

Allowed conclusion: the frozen automatic detector did not establish at least
50 indexed ruler ticks in all six references, so S03-E007-v3 did not qualify a
directional millimetre carrier. This does not show that the physical ruler is
invalid. It does not validate or invalidate physical crack width, isotropic
2-D scale, crack growth, forecasting, RUL or road transfer.

Evidence root:
`local_archive/experiments/S03-E007/runs/S03-E007-R001/`.
