# E037 independent output review — 2026-10-17

Reviewer: `/root/md01_early_review`. Only this authorised R005 review directory
was written. No new source/target, threshold, guide, exclusion polygon,
position, registration fit, training or other agent was introduced. Production
arrays, metrics, predictions and previous experiments remained read-only.

## Decision

No numerical or final-figure blocker for the explicitly bounded development
result. Per-frame observer-guided visible candidates and their image-space
geometry can be computed without the old four-anchor material-position test.
Step19 demonstrates this separation. These outputs are not independent crack
labels, segmentation accuracy, physical aperture or material-point truth.

The primary common-band candidate-area replay favours trend: persistence
absolute error **492 px²**, trend **19 px²**, gain **473 px²**. Length and
thickness P10 favour persistence; all six outcomes remain visible and separate.
There is one already-viewed query, not six independent validations.

## Reproducible independent checks

`independent_check.py` and `independent_results.json` in this directory contain
the full frame/scalar checks, source/protected/input hashes and method limits.
The script refuses to overwrite an existing result. To rerun, preserve this
result or copy the script into another explicitly authorised fresh directory.

The review does **not** import producer extraction, metric, graph or prediction
functions. It uses:

- integer reflected summed-area tables for the 101×101 background threshold,
  rather than producer `cv2.boxFilter`;
- SciPy 8-connected component labels and explicit height/guide filtering,
  rather than OpenCV connected-component filtering;
- independently constructed adjacency dictionaries and heap-Dijkstra, rather
  than producer sparse-graph `csgraph` traversal;
- direct area counts, saved-path edge sums, EDT-value checks, quantiles and
  independently written persistence/trend arithmetic.

Shared low-level libraries remain: Pillow source decode, OpenCV colour and
polygon/guide rasterisation, SciPy exact EDT and skimage `skeletonize`. In
particular, skeletonisation is **shared**, not an independently validated
skeleton algorithm. No independent human/pixel reference is supplied by this
code audit. ORB/RANSAC diagnostics were inspected but not refit.

### Exact and nonexact reproduction

| Check | Maximum difference |
|---|---:|
| 9 source masks, exclusions and thickness-safe masks | 0 pixels |
| Rebuilt skeleton bitmaps using shared skeleton library | 0 pixels |
| Saved ordered-path edge lengths and arc-length arrays | 0 px |
| Saved-path pointwise EDT thickness and withheld/null values | 0 px |
| All saved-path metric aggregates/quantiles and endpoints | 0 |
| Common-band independent graph metrics and all six scores | 0 |

Independent heap traversal selected different coordinates for **five equal-length
paths**: three full-ROI fragments in Step18, one in Step22, one in Step23.
Every alternative has exactly the same path length as the saved path. Their
effect is limited to full-visible mean mask thickness:

- Step18: independent 7.042323790962218 versus saved 7.043073681337194 px;
  difference **-0.0007498903749763031 px**.
- Step23: independent 14.978472675100447 versus saved 14.978389317050269 px;
  difference **+0.00008335805017800624 px**.

All other independently aggregated fields match, including all common-band
metrics and forecasts. This is shortest-path tie-choice sensitivity, not a
source/mask mismatch or reason to modify the original path/score. Do **not**
summarise the entire independent graph audit as “all scalars differ by zero”.

## Coverage, visibility and integrity

- Sources are exactly the nine existing E036 frames; all nine source byte
  counts/SHA256 match the frozen lock. No14/17/20 or other source was acquired.
- Five guided frames18/19/21/22/23 yield visible candidates; four early frames
  12/13/15/16 have no observer-supplied credible trace. Their geometry metrics
  remain null, not zero. Thus **5/9 is extractable candidate coverage**, not
  detection recall, true negative rate or automatic crack/no-crack accuracy.
- Excluded pixels never enter the candidate mask. No morphological closing or
  graph bridge fills the excluded regions. Full-support metrics explicitly
  say `visible_only`; different excluded support is not treated as hidden
  crack area zero or as physical shrinkage.
- Thickness near original ROI/exclusion boundaries is withheld. Endpoint flags
  and counts reproduce; they indicate possible support cuts, not real tips.
  These flags do not label every threshold-induced break or common-band cut.
- Both numerical receipts bind clean `0eba2af`; lock/support hashes match the
  committed settings. Historical predictions closed before the Step23
  numerical phase; all historical payload hashes remained unchanged.
  Source23/support were already viewed, so this is explicitly not blind
  prediction or an untouched target test.
- All **36** old payload hashes match the predeclared protection lock and remain
  unchanged during independent review. The audit does not claim to have
  checked unrelated filesystem history. No old half-depth definition, score,
  geometry or four-anchor correspondence result was replaced.

## Per-frame geometry and mask quality

Full-visible mask areas independently reproduce as:

| Stage | Area, px² | Observed path fragments | Excluded ROI fraction |
|---|---:|---:|---:|
|12/13/15/16|unidentified/null|0|7.69% each|
|18|29754|18|7.69%|
|19|21803|6|41.72%|
|21|34528|9|40.01%|
|22|39285|8|39.45%|
|23|40497|6|39.14%|

Actual final F01/F05 overlays follow the principal visible crack while exposing
texture/pore side-branches, missed fine portions and disconnected fragments.
These are material candidate-quality limitations. In particular, the large
Step18 visible-path length includes candidate side structure; it is not an
independently established physical crack length. Step18→19 area/length changes
also coincide with altered exclusions/fixtures and cannot be called closure.

The coarse observer line is guidance only, not the measured path or reference
truth. A score against a scalar derived from the same candidate extractor
does not measure segmentation error, even when the scalar replay error is small.
Future refinement should examine source-visible geometry and false branches,
not optimise the already-viewed23 forecast error or default to old-anchor repair.

## Common image-space band and scalar replay

The exact native band [3900,1700,4600,1950] is polygon-clear in21/22/23 and has
extractable candidates. It is the same **image-coordinate support**, not the
same material points. Candidate area4054→4565→5057 px² is exactly reproduced;
the511→492 px² increment is slightly slowing for this one algorithmic quantity.

| Metric | Persistence AE | Trend AE | Gain (keep minus trend) |
|---|---:|---:|---:|
| Area px², PRIMARY |492|19|+473|
| Length px |16.89949493661163|18.828427124746042|-1.9289321881344108|
| Mean local thickness px |2.463261648625803|1.401098129577873|+1.06216351904793|
| P10 local thickness px |0.6677010708443785|0.9891531786480021|-0.32145210780362365|
| P50 local thickness px |3.3718060094619435|2.601476395192936|+0.7703296142690075|
| P90 local thickness px |2.1764340039370182|0.2048611286832056|+1.9715728752538126|

All values reproduce without pooling units or treating diagnostic wins as
additional primary votes. The one query has6/6 scalar outputs; that is not6
independent samples. Residual19 px² is not true crack-area recognition accuracy.

ORB/RANSAC values are nuisance diagnostics only, with explicit no-warp and
no-material-correspondence flags. Reported scales are near1 and rotations small,
but crop translations are not zero (Step23 about36.47 native px vertically).
The same image band can therefore contain changing material support. Masks
were not shifted to remove this, and no position accuracy claim is justified.

## Final figures and communication

Actually inspected final R004 F01, F03, F04, F05, F06 colour and F04 grayscale.
Original imagery/masks/guides/exclusions are distinguished; early null frames
are shown; F03 peaks are not clipped; F04 annotations do not overwrite curves;
the primary area and the length/P10 losses are explicit. Grayscale distinguishes
reference/forecast markers. No numerical or encoding blocker was found.

One minor display interpretation was sent to the main agent: F03 concatenates
fragments with **10 px display padding** after each fragment. The padded axis
must not be read as a pure cumulative measured length or across-frame material
coordinate; padding is not included in numerical length metrics. The same-stem
guide already acknowledges display gaps; the exact10 px convention should
also be stated in the reading guide.

README's task separation, full-vs-common visibility, candidate-quality limits,
image-space drift, one-query/metric-unit restrictions and next source-driven
recognition review are consistent with this audit. The shared-library and
equal-path tie limits above must accompany any summary of independent numerical
agreement.
