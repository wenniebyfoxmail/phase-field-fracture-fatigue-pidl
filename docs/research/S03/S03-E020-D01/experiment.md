# S03-E020-D01 — Beam4 fixed tangential position/half-depth response

2026-10-15; Storyline S03; `tangent-response-v1`; controlled-experiment
DEVELOPMENT C1 diagnostic. User authorises fixed-range position/width response,
source-image comparisons and Obsidian update. No new target, training,
registration fit or forecast scoring. E015/E018/E019 records are read-only.

## Question, scope and comparator

Does a small tangential displacement change half-depth width through spatial
width variation within the selected dark band, or through changes in the
half-depth component selected by the measurement function? Use ALL12 frozen
Beam4 transects ×4 fixed stages10/30/40/50kN. Compare original H to the SAME
frozen E019 background translations, not new fits. Each curve is41 tangential
centres from-10 to+10 inclusive at0.5 native-pixel steps:96 curves,3936 profiles,
3840 adjacent-position opportunities. One previously viewed specimen, spatially
overlapping samples; no independent-specimen statistics or physical accuracy.

Normal grid unchanged-60..60 at0.25, five tangent lines centred at each new
position (-2..2), Pillow EXIF/L/float32 and manual1/32 bilinear as E018.
At each centre reapply the UNCHANGED half-depth function/QC/search radius15;
no recentering to a preferred edge, no smoothing of measured response curves.
Correction is reused once per stage/transect for ALL41 centres; never refit.
Reference inputs: E018-R001 safe Beam4 geometry/H/source identity and E019-R001
translations.csv. At tangent0, widths must reproduce E019 both arms (96 cases)
within1e-8 px deterministic arithmetic tolerance; retain missing flags.

## Predeclared descriptive mechanism checks

Primary descriptive quantity: fraction of paired-valid adjacent centres showing
an operational selected-half-depth-band event; report switch/merge/split flags
separately, exact support out of3840 and per curve/stage/arm. No physical
acceptance threshold or binary smooth/true-width certification. Existing
references cannot qualify physical boundaries or material coordinates.

For each profile, use its own selected-peak depth/2. Enumerate ALL bounded
connected intervals of deficit>=that level, interpolate crossings and retain
intervals width>=1 native px. Apply same endpoint-censor convention as the
frozen function. The interval containing its selected maximum is the selected
interval; assert it agrees with the unchanged function's crossings.

For paired-valid neighbouring centres A/B:

- disjoint selected intervals (zero/negative intersection length) -> selected
  band switch CANDIDATE;
- selected A intersects more than one retained interval at B -> split candidate;
- selected B intersects more than one retained interval at A -> merge candidate.

Count union once per adjacent pair. Large peak motion INSIDE the same broad
overlapping interval is not sufficient to call a band switch. Events are
algorithmic half-level/topology candidates, not independent true branch labels:
threshold bridge changes and true edge shape can both cause them. Absence of
events on a0.5-grid does not prove continuous physical width, nor rule out rapid
crossing changes inside the same band. Show full width/crossing/peak curves,
maximum adjacent width change, and invalid measurements without zero-filling.

Per-curve descriptive width range and max adjacent increment provide context,
not votes on physical truth. Compare both frozen arms on available support;
no choosing a better arm or position from these responses. No new spatial
aggregation estimator is evaluated: fixed-segment median remains a proposal.

## Figures fixed before execution

1. ALL12 response panels: four stage colours, original solid / background-aligned
   dashed, shared width axes; full t range and missing gaps.
2. All48 curves per arm: signed width difference from that curve's t0, shared
   symmetric colour scale, invalid masked; operational event ticks shown.
3. Fixed T6, all4 stages, original arm: original-image local strip with projected
   five-line-profile half-depth crossings and selected peak at each t, plus
   response. Crossings are NOT central-row human-visible edge ground truth.
4. Deterministic diagnostic examples: first event in order(stage,transect,
   original-before-aligned,t index), if any; plus maximum absolute adjacent
   width jump among all paired-valid opportunities, ties in same order. If
   identical show once. Raw strip/width curve and BOTH adjacent deficit profiles
   with half-level/peak/crossings. Selection declared now, not cherry-picked.

Underlying raw strips cover t-14..14 at0.5 and normal-60..60 at1 pixel, using
unchanged source sampling. No image generation, image smoothing or mask fitting.

## Budget, review and repair map

Reuse checked measurement/mapping helpers. Synthetic tests must cover Gaussian
width varying smoothly with tangent, selected disjoint bands, split/merge,
peak drift within one band, censor/invalid pairs and t0 replay. Independent
read-only code review before R001; then one Mac lightweight diagnostic, CPU
AND wall120s, numerical library threads1, fresh output, preserve partial on
identity/bounds/budget error. Source size/CRC checked; E019 translation identities
and unique48 rows verified; no external send/push or raw-key access.
Before any pixel access, verify `input_lock.json` combined snapshot for safe
geometry/Beam4NPZ/E019translations/width_variants, E019 completed-runtime commit,
exact96 reference keys and finite valid widths, finite available translations
and zero origin correction. t0 replay must have finite actual/expected/difference;
NaN is never allowed to pass a numeric-tolerance comparison.

Result map: frequent selected-band events -> focus on ambiguity/component
correspondence before aggregation. Large response without detected events ->
inspect same-band edge variation/threshold response with source, not assume
registration failure. Predominantly small/local smooth response -> justify
testing a separately frozen spatial-support repair, not physical metrology.
Both mechanisms may coexist, so preserve per-case evidence rather than declaring
all outcomes fail. Human/physical-reference and future-load availability gaps
remain. Report operational findings, uncertainty and next smallest intervention.

Minimum evidence: all3936 measurement rows,3840 adjacent-pair rows,96 curve
summaries, source profiles/deficits/strips, t0 replay check, runtime receipt,
all figures/sidecars/README_analysis, independent evidence review and one S03 /
Obsidian milestone. This is a mechanism diagnostic, not a new prediction score.
