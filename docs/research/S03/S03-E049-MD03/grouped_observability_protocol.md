# D3 grouped observability diagnostic — fixed before execution, 2026-10-19

User authorises only existing89/132/175, old/motion/two-sided opening evidence,
texture perturbation and structure preservation controls, no result-tuned
thresholds,175 exposed development, old definitions/scores preserved.
Exploratory controlled-experiment observation diagnostic, not a new forecast.

## Goal, reuse and information

Original goal remains crack evolution prediction. Current binding question:
does texture-correspondence evidence distinguish opening from dark paint,
smooth motion/deformation, illumination and resampling? D1continue existing
E049/D3 source and decoder records, cached native bands, saved matrices and
unchanged old masks. No external research, new data, fitting global transforms,
training, predictor scoring or old-file rewrite. Only source89 supplies controls;
89→132 is design pair,132→175 is exposed development diagnostic, not holdout.

Use old fixed nativeband[2500,1720,3000,2080], processingROI as before, same
full-range uint16//257 decoding. Real comparison uses exact previously saved
source band, later band and globally warped source from D3R001. Same common
support; no histogram adjustment. New structural maps are evidence fields,
NOT new masks or a replacement half-depth width.

## Fixed mechanism-led probe

For near-vertical opening, the relevant displacement is horizontal. Use probes
x=2750+8k,k=-19..19 (2598..2902), y=1900+16j,j=-10..10 (1740..2060):819probes,
same grid for all arms and all cases, no hotspot/position selection.

At each probe, take31×31 reference texture patches at horizontal offsets
−72/−48/−24 and+24/+48/+72. Their inner edges leave the central18pixels out
of motion fitting. Match each patch in the later image within±4pixels x/y
by zero-mean normalised cross-correlation (NCC). One fixed search, deterministic
closest-to-zero tie choice, one bounded3point parabola refinement per axis.
No confidence cutoff, correlation/contrast thresholds, learned model or sweep.
Record all peak correlations, fit residuals and search-edge censorship; search
edge or constant-texture probes are unassessable, not zero opening.

Fit a straight displacement trend separately on each side using its3offsets;
extrapolate both to the centre. Horizontal jumpJ=u_right(0)-u_left(0), in image
pixels. Common translation and an ideal smooth linear strain cancel; opposite
side shifts at a gap remain. This is a horizontal discontinuity proxy, NOT
physical aperture, millimetres, old half-depth, or every possible crack normal.
Nonlinear deformation, imperfect matches and extrapolation can imitate a jump.

Independent appearance cueQ: central5px×31px mean darkening in
(warped reference minus later image) minus average darkening in flanking
8px×31px strips x[-13:-5] and[6:14]. Uniform additive illumination cancels
ideally; paint transport/gain/clipping can still affectQ. PositiveQ means
locally enhanced darkening, not automatically a crack. Report J,Q and quality
jointly, no binary crack threshold/classification or truth-area claim.

Old arm: immutable later E049 dark mask, also report its occupancy within the
same5×31 probe footprints. Motion arm: same-footprint mean absolute residual.
Structural arm: J/Q/quality at those probes. Wholeband residual summaries stay
context only; do not compare different supports as if they were equal evidence.

## Fixed source-texture controls: one group, not serial tuning

Reference controls are saved-global-warped89; create controls on its full ROI,
with all measurements in the same band/probes. The old observer may be called
unchanged on synthetic controls only, with separate outputs. Never alter real
old masks. Warp once using recorded89→132 matrix. Controls then receive one
explicit bilinear resampling where prescribed; motion-only control includes
the rounding/resampling baseline, so quietness is not presumed perfect.

Eight cases, all retained:

1. motion_only: warped89, no new structure;
2. illumination:1.05×warped89+8, clipped0..255;
3. smooth_strain: continuous horizontal scale1+e aboutx2750,
   e=the saved historical global scale−1, not175-derived;
4. illumination_smooth:3plus2;
5–7. opening_1/2/4: known vertical gap of1/2/4px centredx2750; move
   left/right texture by−g/2,+g/2, leave a dark intervening strip (zero gray);
8. opening_2_illum_smooth:2px opening plus continuous strain and illumination.

The1/2/4px gaps bracket one native-pixel resolution and small multi-pixel
openings within the±4side search, not chosen from real scores. Vertical straight
gap is a favourable generator, not a realistic truth set. Identity/translation,
continuous strain and synthetic steps are also checked arithmetically.

No comparison threshold. For all controls report J/Q at the predetermined
x2750 column across all21 y positions, median and10–90% spatial range (not CI),
known injected gap, fit availability/censorship and old-mask occupancy. Display
all819probe fields for real pairs. Real-map response is assessed against the
observed control response, without deriving/tuning a new segmentation cut.

## Reading the grouped result

- Nuisance response small, injected opening recovered, real J andQ co-located
  with source-visible gap and defensible matching: useful candidate evidence,
  advance whole candidate-geometry development, not independent accuracy.
- Controls distinguish mechanisms but real maps lack corresponding evidence:
  real observability unresolved; need a located raw-image opening/reference or
  local DIC discontinuity evidence, not more predictor complexity.
- Negative controls imitate positive controls or gap removed/missed: this
  implementation cannot supply a trustworthy measurement interface at that
  scale. Preserve useful scales/components; choose an observation redesign
  rather than threshold patching or a global research-route failure.

All scales/cases/maps reported; partially useful controls may justify progress,
not an all-or-nothing perfection gate.175never establishes independent success.

## Execution and visual contract

One candidate/group,300sCPU/wall analysis cap, no GPU/training/download or
repeated scientific run. Fresh attributable run, inputs/old-file hashes, code
snapshot, command/runtime/start/end and allfields/control images retained.
Local synthetic and separate numerical audit, no mandatory extra agent review.
Real figure: old contours, motion residual, J, Q and matching quality, bothpairs.
Control figure: all8response summaries withknown gaps and spatial ranges;
montage ofall8controls/fields. Fixed shared colour ranges from code scales,
no per-case autoscale or favourable cropping. PNG/same-stem explanatory notes,
actual rendered QA and concise Obsidian milestone/one Roadmap entry.
