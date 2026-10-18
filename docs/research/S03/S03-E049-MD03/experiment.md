# E049 — MD03 fixed three-frame frozen-observer transfer

2026-10-18. User-authorised lightweight exploration; controlled experiment.
Question: can the accepted MD01 observer produce useful geometry observations
on another beam, and does a two-history extrapolation beat persistence?
No new model, segmentation parameter search, physical-width or road claim.

## D1 reuse and acquisition-text check

Continue the completed independent-sequence metadata audit. Reuse unchanged
`md01_geometric_guide_transfer.transfer`, `md01_frame_geometry.extract/metrics`,
`md01_support_mass_forecast.observe/predict` and simple `forecast` arithmetic.
Only source-reader dimensions and history-only ROI/guide are new specimen
configuration; no threshold, corridor, path penalty or component change.

Official dataset: https://data.mendeley.com/datasets/wv7hvgg8c7/1 (CC BY4.0).
Associated author manuscript, section2.3: Canon EOS6D,100mm macro, sprayed black
speckles on white beam faces, one DIC beam per19.2/33.7% group, four-point
bending. Section3.3 describes an image sequence used for crack evolution.
Source: https://escholarship.org/content/qt3781m1pg/qt3781m1pg_noSplash_ced41e2ca80b44c68b0c2c1d369efc09.pdf
and DOI10.1016/j.matdes.2020.109184. Web search returns the relevant text; Jina
PDF route returned403, no locally acquired PDF/method figures. Filename-to-time
or load mapping and camera stability are not specified in the retrieved text.
Record embedded TIFF/EXIF timestamps if present; never use upload timestamps
as capture times. File-order interpolation alone is not a qualified time model.

## D2 fixed information boundary (before new pixels)

- First beam: lower19.2% reinforcement label, not performance. Only this beam
  in this minimum attempt;33.7% remains unopened for a later decision.
- Sort all173 published filenames by numeric suffix. Ranks `ceil(N/2)`,
  `ceil(3*N/4)`, `N`:87/130/173, filesIMG_0089/0132/0175.tif. Equal gaps43.
  Three fixed mid-to-end observations; do not replace a hard/uncracked frame.
- Download/decode only two history images first; SHA/byte identity against
  archived official metadata. Inspect original native geometry and timestamps.
  Define a visible interior ROI and a single y-monotone coarse guide using
  those histories only. Use the same ROI/support at target; target image may
  drive only its own unchanged guide transfer, never the saved prediction.
- Use native RGB conversion as in the accepted observer, no contrast scaling,
  downsampling, de-speckling or threshold adaptation for measurement. Preview
  downsampling is display-only. Do not inherit MD01 coordinates or px-to-mm.
- If no history-visible crack can be identified, freeze a no-visible-trace
  support and report candidate-empty/unsupported trend, not physical absence.
  If the frozen observer follows speckles, retain the output and diagnose it;
  no post-target repair. This is observer-space capability, not segmentation
  accuracy without an independent reference.
- At origin save+hash immutable history measurements/configuration and hold,
  nonnegative area secant, and existing support-hold/mass-secant diagnostic.
  Only then download/decode third image. Primary comparator: area secant vs
  persistence on candidate-area absolute error (pixel²), one paired case;
  separated-input arm reported explicitly as secondary, not selected winner.
- Use equal FILE-INDEX steps for arithmetic. Embedded times, if present, check
  direction/gap but do not silently change the predictor to clock-time. Without
  timestamp evidence, results remain a filename-order continuation diagnostic,
  not confirmed future prediction. No absolute-load labels required or used.
- Candidate area A; occupied image rows L; row mass M=A/L; skeleton path length
  and EDT mask thickness are additional pixel geometry. L is not crack length,
  M/EDT are not the old half-depth width or physical aperture. Empty area is0
  with a visibility warning, conditional mass missing; no invented widths.
- Protect old E048 inputs/results, recognition code and half-depth source.
  No overwriting old masks/scores, no pooled rescore. One triplet, no sweeps.

## D3 result and next decision

One causal two-history save, one target, one frozen extraction per image.
Budget: three official images only, <=150MB sources; local CPU analysis
<=120s per phase, no GPU/training. Failed executions retain separate receipts;
infrastructure-only repair may not alter data/parameters/selection.
Missing identities stop the affected source; missing time narrows the claim.
Advance the working trend if it improves this case; retain component progress
and choose one bottleneck repair if not. One beam/window cannot establish
generalisation. Do not expand architecture or open second beam automatically.

Figures: all3 fixed original views and native ROI masks/paths; origin-to-target
geometry trajectory, all predicted values/errors; same scales, every frame
shown, empty masks and scattered speckles visible. PNG with same-stem sidecar,
actual rendered QA, concise Obsidian milestone and one Roadmap status.
Exploratory local tests suffice; no mandatory new agent review.
