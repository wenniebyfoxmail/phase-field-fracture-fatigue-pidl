# E038 independent numerical and visual review

2026-10-17. Reviewer scope: existing stages18/19/21/22/23 only; no new images,
forecasts, parameter changes, material registration or producer-file edits.
Authorised outputs are confined to this fresh R004 directory.

## Numerical conclusion

No numerical blocker found in the bounded E038 output. This is successful
execution/reproduction of sensitivity measurements, not segmentation accuracy
or a scientific stability PASS. All45 full/common outputs are present, which
does not mean that they are stable.

Producer R001 execution clean commit
`8907da3`; exact full commit is recorded in independent_results.json.
Manifest SHA256
`c069e93291d89e508cbaf30b460729ea43a39149a7f7e93fc5780f93fb5c8b34`.
Independent script runtime17.24s. All75 protected file hashes matched before and
after review; R001 payload hashes also remained unchanged during review.
Sources are only the five frozen E036 JPGs375/379/385/388/391 with exact source
SHA/byte checks. No old forecast/score contents were parsed by this reviewer.

Independently reconstructed all45 candidate masks from source ROI pixels using
integer reflected101x101 box sums and SciPy component labels, rather than the
producer boxFilter/OpenCV component filtering. Mask/exclusion/safe/skeleton
pixel differences were all zero. All5 reconstructed v1 arms exactly match the
protected E037 arrays, full/common metrics and ordered path JSON.

Independently checked every saved path's pixel adjacency, diagonal restrictions,
arc coordinates, length, EDT samples, boundary withholding/endpoints and all
full/common scalar aggregations. Maximum difference is zero. Independently
checked all IoUs and signed/relative metric changes; KDTree vs EDT symmetric
nearest-path-distance computation differs by at most1.7763568394002505e-15px.
Every fixed-v1-path sample, all9xpoint thickness grids, missing entries, setting
support-count maps, available fractions and thickness-difference summaries match
exactly. All per-frame summary arithmetic matches exactly.

Independent heap-Dijkstra graph traversal (not producer sparse csgraph) found40
equal-length paths with different pixel choices. All lengths, path counts,
withheld fractions and P10/P50/P90 summaries match. Maximum own-path thickness
mean difference is0.0012668710552752316px. All metrics recomputed on the actual
saved paths match exactly. Equal-geodesic tie choice is thus a small real
representation dependence; do not report every independently chosen path metric
as exactly identical or relabel the old result.

## Recomputed primary descriptive results

Relative maxima across the eight declared alternatives, not confidence bounds:

| Stage | Full area max abs change | Common area max abs change | Minimum original-safe-path coverage |
|---|---:|---:|---:|
|18|29.764%|70.203%|71.644%|
|19|46.851%|156.454%|88.889%|
|21|16.343%|19.635%|89.218%|
|22|20.868%|11.172%|92.457%|
|23|12.448%|8.602%|96.206%|

Every stage has9/9 full and9/9 common metrics, with all8 alternatives retained.
Coverage above is conditional on original v1 path points with finite/safe
thickness, not all path points or detector recall. Boundary-withheld samples
remain missing, not zero. Per-point min/max settings envelopes are finite
deterministic sensitivity, not a statistical uncertainty interval.

For full area, contrast±5 is the largest family in all five frames. Gray±5
full-area maxima are0.807/0/1.040/2.446/0.284%; guide±5 maxima are
3.381/6.958/2.621/0.690/1.857%. This does not make guides irrelevant: in the
fixed common band, guide changes reach43.653% and38.726% in18 and19. Their
corresponding contrast changes reach70.203% and156.454%. Later common-band
guide area changes are0/0.088/0%, respectively. Support-size, fragmentation and
threshold/contact decisions are not separable physical mechanisms here.

The full/common primary and per-arm results are descriptive for one trajectory,
not45 independent trials. IoU compares to observer-guided v1, not ground truth;
support count9 means invariance under nine settings, not true-crack confidence.
The mask2xEDT thickness is not half-depth width, perpendicular aperture or mm.
No replacement setting is recommended from these data, no old score changes,
and no forecast-error parameter choice occurred.

## Independence / reproducibility limits

The check imports only the archived E037 independent reviewer helper, whose
path and SHA are recorded, never the producer extractor/metrics/new runner.
Pillow decoding, OpenCV grayscale/guide-polygon rasterisation, SciPy EDT and
skimage skeletonize remain shared low-level libraries. Thus the reconstruction
is algorithmically independent in box sums/component filtering, heap graph
implementation, aggregation and nearest-path distance calculation, but it is
not a fully separate skeleton/EDT algorithm or independent manual annotation.
The five source ROI supports and exclusions remain observer-defined development
inputs, not blinded physical reference labels. Hidden regions remain excluded.

Run `independent_check.py` in a fresh review directory containing the script to
reproduce; outputs use exclusive creation and preserve this run. It depends on
the archived E037 reviewer helper at the exact recorded path/hash. Full numeric
checks, tie records, family results and input hashes are in
`independent_results.json`.

## Visual review

Completed actual viewing of final R003/analysis produced at5bb5eb3:

- All5 F01 identification-layer PNGs (18/19/21/22/23).
- F02 all-setting geometry PNG, F03 spatial-setting-support PNG and F04 path/sample PNG.
- F01_step19 grayscale, F02 grayscale and F04 grayscale.
- Final README_analysis.md, renderer code and same-stem explanatory conventions.

No blocking layout, source-orientation, value-label or axis/cropping problem
found in these viewed assets. Raw ROI, binary candidate, complete skeleton and
selected fragment paths are visually distinct. Thickness and support-count
panels share the same display arc axis and retain missing gaps; different
frame-specific y ranges are labelled and no common quantitative scale is
implied. The per-fragment10px display gap is explicitly not measured length.
F02 displays all8 settings and has matched signed colour ranges per metric
across full/common, with percent and px units separated. F04 values and grayscale
numbers remain legible. F02 grayscale cannot itself encode signed differences
uniquely because it is a converted diverging map, but all cells carry signed
numbers, preserving the conclusion without colour. These are display copies,
not new calculations. Individual PDF pages were not separately rasterised by
this reviewer; the actual visible QA used the final PNGs.

Visual scientific limits are material, not blockers to this descriptive study:
the main visible crack is captured, but rough-surface/pore sidebranches, fine
crack omission and disconnected selected segments remain. Stage18/19 source
images visibly contain upper fine cracks not fully represented in v1 masks;
later upper-source thin traces can also be absent. The plate/glue exclusion
changes support across frames. Selected main paths are representative within
fragments, not the whole branch network or true crack tips; do not interpret
cross-frame path-length decrease as physical shortening. F03 stable yellow
candidate pixels may still be texture/pore confounds, not calibrated confidence.
Its mask-support counts do not have the boundary-safe restriction of the
along-path count panel; the captions distinguish these definitions.

The final README correctly discloses original-safe-point coverage, count0
including original60px withholding, P90=0 not implying identical paths,
contrast dominance with18/19 common-band guide exceptions, equal-path tie and
shared-library limitations. Its next-step proposal is bounded source/geometry
inspection of already saved contrast masks, not an unapproved parameter
replacement or a prediction-based tuning rule. Retained R002 rendering receipt
failure and R005 renderer-only correction do not change the single numerical
run. No further correction is requested before user delivery.
