# E040 — Step19 exclusion-support repair (exploration)

2026-10-17; S03 controlled-experiment C2 diagnostic. User approves tightening
over-broad purple exclusion support. Only existingStep19 IMG_0379.JPG, original
ROI[3800,900,4800,3500]. No other source frames, new downloads or training.

- Question: does a source-only tighter exclusion recover visible candidate
  crack segments previously screened out, without opening actual fixture/glue?
- Comparator/observable: immutable saved E038 Step19 v1 mask/excluded; show
  original RGB, old/new support and masks, added pixels. Report released support
  area and added candidate pixels, including any connectivity-driven additions
  outside released support. These counts are not true-positive/accuracy scores.
- One repair: retain old right exclusion; tighten left fixture/glue edge from
  unenhanced source inspection, with roughly10–20px conservative margin. Move
  whole bottom strip start3300→3370, about20px above earliest visible bright
  specimen/backdrop boundary in the inspected source grid. Intersect proposed
  keep-exclusions with oldexcluded: may only release, never add excluded pixels.
  Exact source-derived vertices in support_repair.json, frozen before extraction.
  Source-only R000 preview exposed a potentially unprotected glue fringe: add
  fixed10px elliptical outward buffer to left keep-exclusion BEFORE any crack
  extraction. Keep first preparation, effective R004 prepares this sole final
  source-only candidate. No masks/prediction errors inspected to choose buffer.
- Resource cap: one frame, old default reconstruction plus one changed-support
  extraction, CPU/wall60s; renderer separate. Existing v1.extract unchanged.
  No threshold sweep, skeleton/path/thickness calculation, forecast/scoring,
  registration or error-based selection. Do not apply E039 spur filtering too.
- Next observation: raw-source overlays determine whether released pixels stay
  on visible surface and whether additions look crack-/texture-like. Ambiguous
  pixels remain candidate; one frame/AI boundaries are not human ground truth.

## Source inspection and boundary limitations

First examined rawROI, left/right middle, lower crops and native100px grids in
local_archive/experiments/S03-E040-MD01/source_inspection, all same locked source.
Actual glue/hardware remains excluded; do not infer hidden crack or bridge gaps.
Right side stays unchanged because its glue edge is not safely loosened here.
Left trace/bottom change is one support lever, not a new darkness/texture filter.
The existing guide ends at(4220,3300), with60px corridor: further visible lower
crack may remain outside support. Upper fine omissions/noise remain unaddressed.

R000 prepare verifies source bytes/SHA and saved baseline NPZ SHA against E038
independent record; hashes old arrays/paths/metrics, v1/halfdepth code and locks.
Rasterise source-only support, convert contours to polygons, verify exact raster
round trip and strict subset; no crack extractor used inpreparation. R001 first
reconstructs old mask/excluded/safe exactly, then unchanged v1.extract with only
the exclusion polygons changed. Stop on mismatch, support added or old mask lost.
Keep safe/old geometry files unchanged; new safe is internal extractor output,
not permission to update old width readings. No claims of new path/width values.
R000 andR001 separate start/final receipt names, fresh directories, no overwrite.

## Figure plan

Destination=chat/Obsidian diagnostic. F01 four fullROI columns: unenhancedRGB,
old cyan mask+purpleexcluded, new blue mask+purpleexcluded, orange addedpixels.
F02 fixed source-only crops, selected BEFORE new extraction: left/glue adjacent
[4100,2600,4450,3160] andbottom[4050,3230,4390,3420], same four columns. Orange
means newly included candidate, not verified crack. Source-native coordinates,
shared scale per row, no display dilation or filling. Preview/actual visualread,
then PNG300dpi/PDFembeddedfonts/gray with same-stem provenance notes. No scalar
performance plot or four-card accuracy. If result not useful, record it unchanged;
do not tune vertices from candidate pixels or prediction error inthis attempt.

Preserve v1, original half-depth and old scores. Separate named support candidate,
not promotion to v1.1. Update canonicaltrack beforefrontier and brief Obsidian
milestone with actual comparison image; previous no-Obsidian restriction applied
to completed source-card preparation, not this user-approved repair iteration.
