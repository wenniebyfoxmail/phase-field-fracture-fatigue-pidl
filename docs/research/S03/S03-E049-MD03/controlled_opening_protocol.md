# D3 matched-resource opening candidate — prepared, not a real-image run

2026-10-20. Continue E049/D3; no new Storyline. C1/C2 exploratory observation
component, controlled laboratory specimen, not physical aperture certification
or C3 forecasting. User agrees not to wait for the author. Current HQ scope is
implementation, artificial-only checks and a reviewed execution proposal;
no real-image algorithm/scoring, annotation, producer launch, download or training.

## Goal and reuse

Image observations → crack evolution remains the goal. D3 addresses the observed
speckle contamination of the old dark candidate, not a new target of forecasting
arbitrary DIC signals. Continue and reuse the existing six-patch NCC, fixed ROI,
two saved transforms, source hashes and old masks. New code is separate in
`scripts/md03_controlled_opening.py`; the original matcher/results are unchanged.
Earlier 1/2/4px artificial recovery and real J1.576px are motivation, not evidence
that this candidate is correct. Do not rerun equal-step forecasts for time labels.

## Mechanism and discriminating intervention

For an image normal n=(1,0), local displacement is schematically
`u(x)=t+B*x + H(x-xc)*j + curvature(x) + correspondence_error(x)`.
Separate linear fits on six texture patches cancel common translation and linear
strain; their intercept difference J may retain a jump, but also curvature or
wrong matches. Horizontal J is not automatically the crack-normal opening.

The intervention combines three equal-resource stencils: central and two internal
controls centred x−120/x+120, each with offsets −72/−48/−24/+24/+48/+72,31px
patches, ±4px search, identical NCC/refinement, two three-point OLS fits and
bidirectional checks. Internal patch supports are respectively ≤x−33 and ≥x+33;
they do not sample across the nominal central line. They are **same-side by
design**, not independently proven crack-free; multiple cracks/curvature can
affect them too. They receive exactly the same five saved-transform perturbations
(0,0), (−1,0), (+1,0), (0,−1), (0,+1)px; no transformation is refitted or chosen.
This tests one integrated mechanism, not serial threshold micro-tests.

Expected signatures:

| Competing explanation | Central vs internal and nuisance signature |
|---|---|
| Two-sided normal displacement discontinuity | Central positive J beyond internal responses, little tangential response, stable to declared transform shifts, defensible raw appearance/correspondences |
| Common registration/translation/linear strain | J approximately cancels in all three; brightness residual may remain |
| Smooth curvature / texture drift | Similar internal responses or spatially unstable J; cannot call it a crack merely because NCC is high |
| Painted darkening / illumination | Central appearance changes without corresponding two-sided J |
| Occlusion, insufficient texture, mismatch | Numerical unknown; preserve denominator and failure group, do not fill zero |

## Exact input and information contract

- Only already-exposed19.2% beam IMG_0089/0132/0175, hashes fixed in code and
  manifest. Native5496×3670,uint16//257 decoding unchanged; execution uses
  **existing** ROI arrays, not new original-image decode or segmentation.
- `R002_history/89/arrays.npz`, `R002_history/132/arrays.npz`,
  `R003_target/arrays.npz`: roi_rgb and immutable full-ROI mask. ROI
  [2260,1600,3240,2160], array560×980. Same native grid is not material identity.
- Existing `D3_20261019/R001/input_specification.json`: matrices89→132 and
  132→175, already target-informed development transforms. No origin-known
  future or blind validation claim. Five variants each warp original cached A
  once, rather than repeatedly warping the previous variant.
- Fixed x2598/2750/2782/2902 × y1740..2060 step16:84sites per pair, all retained.
  x2782 was previously selected by largest175 J and is explicitly algorithm-
  informed; it receives no confirmatory weight. The other three are the previous
  fixed comparisons, not newly selected positives. All5×3 stencils at every site:
  1260gauges per pair,2520total,15120forward/reverse patch pairs,30240NCC calls
  maximum. Cached repeated patches are optional only if byte-identical results.
- Existing MAT/TXT mappings may be linked as conditional retrospective context,
  but no DIC gauge channels, guessed endpoints, actual future loads or time labels
  are algorithm inputs or ground truth. No new reference labels are created.
- Every real site's visibility and crossing remain unknown/unannotated in this
  preparation. A future visual reading may describe appearance but cannot be
  called independent annotation. No false-positive/negative accuracy is scored.

`prepare` reads JSON/bytes and hashes exactly9existing files, no np.load or CV.
The resulting manifest owns identities, parameters, code/protocol hashes. A
producer copy must preserve relative input bytes and regenerate/review the same
manifest with its approved archive root; local Mac paths are not assumed remote.

## Numerically usable versus physically interpretable

Each31px template and39px search needs a full bilinear valid footprint. Fixed
exploratory QC: template/search std≥2 gray levels; NCC≥.90; peak advantage over
all positions outside its3×3 neighbourhood≥.02; no ±4 search-edge hit; both
directions meet the same rules; forward+reverse displacement norm≤.5px.
The2gray threshold is a code-level texture floor; .5px is a half-native-pixel
correspondence check; .90/.02 are conservative engineering ambiguity screens,
not calibrated physical tolerances, confidence intervals or crack labels. Keep
all raw fits/quality and show coverage, so low coverage cannot manufacture a win.
These settings are fixed before new real outputs; no real-result tuning.

Reverse matching starts at the matched subpixel point in B, searches A around
that same coordinate, and checks d_forward+d_reverse. A high peak alone is not
evidence of correct material identity. Unknown visibility remains a separate
field even if all numerical checks clear. OLS residual is a diagnostic, not a
filter that discards curvature inconvenient to the claim. No imputation or
positive clamping. Nonfinite, occluded, ambiguous and edge cases stay unknown.

## Primary readout and result decisions

For every site keep signed J_normal,J_tangent, OLS residual, all six forward/
reverse matches and QC reasons; same-footprint central darkening, absolute
residual and old-candidate occupancy are parallel diagnostics, not independent
labels. Report all84nominal per arm/pair, usable counts and overlapping failure
groups. Cross-arm/perturbation comparisons require **all15** estimates usable
at the same site, with their common denominator reported.

Primary exploratory contrast is per-site
`E=min_5variants(Jcentral) - max_2internal×5variants(abs(Jinternal))`, px.
This nuisance envelope is finite and declared, not a statistical CI or exhaustive
registration error bound. No magic percent-gain gate or pooled significance test.
E>0 supports only contrast specificity within these controls; E≤0 preserves the
actual direction and points to ambiguity/continuous deformation/mismatch.
E unavailable means unknown, never zero. Display every site and both pairs,
including tangential changes, QC coverage and all perturbation ranges.

- Useful specificity with defensible raw structure: retain the component and
  develop an explicitly image-defined state measurement; no physical-width claim.
- Internal responses or perturbation ranges explain the central response:
  retain the diagnosed observation limitation; do not add predictor complexity
  or select the “best” centre/transform. This does not prove absence of a crack;
  nearby real cracks may also affect an internal stencil.
- Strong numerical response with unresolved raw fissure identity: compatible
  displacement discontinuity only, not verified opening; park **that** physical
  interpretation, not the whole image route.
- Numerical unknown dominates: preserve the available scales/components and
  identify the resolution/texture limitation. Do not infer no crack.

One physical beam, two exposed dependent intervals,84spatial sites are not84
independent trials. No correlation claim from3frames. No channel-prediction
substitution, old5.81% rescore, future load input or manufactured independent truth.

## Artificial-only preparation and exact-diff review

Unit checks use seeded artificial noise/analytic displacement fields only:
translation/affine intensity, linear strain cancellation, known2px step vs
equal-budget internal controls, dark paint without opening, fractional sampling,
occlusion, periodic ambiguity, mismatched texture, search edges, validity holes,
reverse failure and denominator preservation. Independent NumPy NCC and closed-
form intercept arithmetic cross-check OpenCV/OLS. These are software checks,
not a new scientific result or rerun of the existing source89 controls.
No archive NPZ/TIFF decoding in tests. Exact-diff review must check entrypoint
admission, forward/reverse coordinates, signs, unknown propagation, all-arm
resource equality, output isolation and frozen manifest integrity. Bind its
record to the final commit and SHA; artificial results cannot authorise execution.

## Proposed one-shot producer package — NOT AUTHORISED / NOT LAUNCHED

Producer: Taobo task-owned CPU process only, host/root/RunID still to be chosen
and explicitly approved; no SSH attempt or admission made here. Max1process,
OpenCV1thread,0GPU,0training, estimated<2GBRSS, hard600s wall including figures,
128MiBoutput checked between blocks/end; these are proposed caps, not measured
real-run costs. A single parent subprocess timeout terminates only its own
worker. STOP file is checked before each gauge. No fallback/retry/newRunID on
timeout, mismatch, unknown remote state, storage conflict or implementation error.

Required exact execution decision fields: candidate, contract_sha256, host,
output, wall_seconds=600, run_id and approval_source. A file is a record, not
human consent; do not generate a fictitious approval. CLI refuses macOS. Output
must be a fresh `<approved_archive>/D3_controlled_opening_20261020/runs/<RunID>`.
Verify source hashes before execution and all contracted files after, never
overwrite old NPZ/mask/results. Single bounded command after separate decision:

```text
python scripts/md03_controlled_opening.py run --contract <reviewed_contract.json> --decision <exact_approved_decision.json> --output <exact_fresh_output>
```

Required output: copied contract/decision; start/final receipts, code/protocol
hashes, command, host/runtime/PID/commit and timings, worker log, both1260-record
JSONs and84-site summaries, both comparison PNGs with same-stem notes. PNGs use
untouched cached original ROIs alongside all central/internal maps, shared±4px
scale with clipping disclosed, gray QC-unknown, no favourable example selection.
The JSON includes every perturbation and matching detail. Actual visual QA and
scientific interpretation occur only after that separately approved run.

Missing author endpoints do not prevent this comparison. They still prevent
authentication of Ext1–7 geometry, millimetre aperture validation or relating J
to the authors' particular physical gauge. Reply is not a launch dependency.
