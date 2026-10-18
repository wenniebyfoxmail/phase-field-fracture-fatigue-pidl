# E046 — accepted observer, consistent-history forecast replay

2026-10-18. Lightweight deterministic development analysis, authorised by the
user's acceptance of E045 identification and request to advance downstream.

## Question and fixed scope

Does the accepted image-geometric observer form a usable observation sequence
for simple next-stage candidate-area prediction? Do not polish segmentation.
One already-exposed MD01 SideA trajectory; three overlapping windows, not three
independent specimens or a blind test. Specimen identity relative to D01 remains
unknown. No new images, downloads, training, external actions or load labels.

## Freeze before computation

- Use E045 R000 original stage23 guide/exclusions, ROI and 700×250 scoring band.
  Stage23 anchor is available by every prediction origin (23/24/25). Applying it
  retrospectively to stage22 is an origin23 history measurement, not a claim of
  a causal stage22 observer. Never use target-derived guides for earlier frames.
- Apply unchanged E045 `transfer` then unchanged E037 `extract` once to already
  exposed history22/23. Reuse E045 R001 accepted new masks24/25/26 exactly;
  do not extract them again. No error-based guide/threshold/position selection.
- Fixed windows: 22,23→24; 23,24→25; 24,25→26. Horizon is one relative stage,
  not equal time/cycles/kN. All target values are already exposed development data.
- Unchanged E043 `observe` and `predict`: A=mask pixels; L=occupied image rows;
  M=conditional pixels/occupied row. Compare persistence, area secant and
  support-hold × mass-secant with existing image-size bounds only. L is not
  physical length and M is not normal/half-depth/physical crack width.
- Save each history-only prediction before parsing that target's accepted mask
  in this replay. This protects code information flow, not retrospective blindness.
  Update history only after target scoring. No future image/target is an input
  to a prediction. The image is allowed only to measure its own observation.
- Primary descriptive comparison: mean absolute candidate-area error against
  persistence on these same three windows and this same new observation version.
  Show every window, gain, calculable coverage and L/M trajectories. No arbitrary
  improvement hurdle. A tie with area secant is an informative redundancy result.
- Preserve all prior masks, half-depth definition and scores. New-version errors
  cannot replace E044 scores or establish a physical forecasting improvement.

## Execution and checks

Fresh R000 input lock then one R001 numeric run; 90s wall/CPU cap, no GPU.
Existing synthetic DP/predictor tests plus prefix-only forecast guard, exact
cached-mask identity, A=L*M, input hashes and saved-prediction event chain.
R002 only renders those exact outputs: all five source/mask bands and all three
forecast/error comparisons. Same-stem sidecars and actual image inspection.
Exploratory local checks are proportionate; no independent review prerequisite.

## Decision

If a simple trend beats persistence, retain it as the next working baseline,
without claiming independent validation. If separated input equals area secant,
keep the simpler predictor and retain L/M only as interpretable diagnostics.
Otherwise use the observed failure to select the next cheap diagnostic. Any
new-stage opening or larger model is a separate next action, not implicit here.
