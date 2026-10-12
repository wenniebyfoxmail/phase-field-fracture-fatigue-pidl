# S03-E015-D01 — first-frame-locked transverse crack profiles

2026-10-12; S03; protocol `development-v1`; controlled-experiment.
Owner: this Experiment. Branch `codex/crackmnist-tokenizer-mvp`, clean base
`9e4191bff2d50b6c0d56dd9404071f2d8d46f83c`.
Scope: new profile runner, this record, compact evidence, S03 impact entry and
the existing Obsidian milestone. Old experiments and external writers excluded.

## Decision, not a formal metrology/forecasting claim

Question: can a crack-local image observable replace the texture-dominated
16x16 dark-ridge means and yield an inspectable stage trajectory?
This is an offline DEVELOPMENT diagnostic selected after E012/E013 were seen.
It does not pass C2 physical metrology or C3 generalisation gates. Independent
boundary reference, repeatability and independent code/evidence reviews are
pending. No formal Code Ready/Evidence Ready label or statistical pass threshold.

## Frozen method before future profile scoring

- Same 14 non-final IB fixed-camera states of D01 v4 (DOI
  10.17632/z3yc9z84tk.4), same three beams and eight origins with two prior
  observations. No new source download, seconds-force synchronization or final
  stage imputation. Reuse E012 source CRCs and saved homographies.
- Observer-assisted approximate path knots use ONLY the first 10 kN image of
  each beam. They are NOT independently annotated masks/ground truth. All 12
  knots per beam remain visible in overlays, including weak/invalid profiles.
  Beam 4 now covers the right-hand dominant crack. Path normals are fixed from
  adjacent knots; this is one crack segment per beam, not exhaustive topology.
- Origin-only preparation centers each transect on the strongest local dark
  deficit within +/-40 native pixels. Freeze these locations in a saved JSON
  before reading future profiles. Background controls use the same normals at
  12 fixed locations on the previously selected control rectangle centerline.
- Sample native grayscale images directly through inverse native-coordinate
  homographies. Resize coordinate conversion uses actual x/y dimensions and
  pixel-center mapping. No image warping or added Gaussian smoothing. Median
  of five parallel lines at tangential offsets -2..2 native pixels; normal
  samples +/-60 at 0.25 pixel spacing (oversampling is not higher resolution).
- Fit local linear background using median shoulders at |s|=45..60. Estimand:
  connected full width at half local intensity deficit (FWHM), native-image
  pixels in first-frame coordinates, NOT millimeters/physical aperture.
  Later peak search is limited to +/-15 pixels from origin-fixed center.
- Diagnostic QC: peak deficit >= max(10 gray levels, 3 times robust shoulder
  residual noise), both half-depth crossings visible, width >=1 native pixel.
  Missing is missing, never zero. Show validity and background false-detection
  counts. Only origin-valid crack transects enter scoring; require the last two
  historical and next target widths valid. Identical support for all arms;
  report denominator and abstentions, not selective accuracy alone.
- Persistence, secant and fixed half-secant use only last two observed widths
  and scheduled next nominal load, including unequal Beam 4 increments. Lower
  bound zero, upper bound full profile window (120 pixels), not old [0,1] range.
  One-step observed-history updates, NOT autonomous rollout. No fitted model,
  held-out beam, future-tuned measurement settings or novel architecture.
- Primary descriptive comparison: transect MAE averaged per prediction pair,
  then within beam, then equally across beams. Pixel transects are NOT
  independent specimens. Display all three beams and all eight origins.
- Secondary sensitivity: shift locked measurement centers +/-2 pixels along
  the tangent, keep normals/algorithm fixed; compare resulting width changes
  against stage changes. This is sensitivity, NOT independent repeatability.

## Budget and outcome map

One first-image-only preparation, one full offline run; no threshold sweep.
Stop for identity/CRC/support error or no computable beam comparison. Preserve
invalid profiles and original E012/E013 outcomes. Without a physical reference,
no pass/fail is assigned to physical measurement or future crack prediction.

Components: source-to-transect overlay -> measured profiles/QC -> local widths
and nuisance sensitivity -> same-support baselines. If signal is below noise,
repair local reference/sampling; if width trend is observable but extrapolation
misses, test a bounded origin-only growth rule under a fresh protocol. Do not
train a temporal network yet. Minimum evidence: locked geometry, saved profiles,
per-profile widths/QC, all pair errors and coverage, all-beam figures, receipt
and README_analysis with allowed/blocked conclusions.

Raw destination: `local_archive/experiments/S03-E015-D01/runs/` under the parent
project; native raw files stay in E012-D01-R001. Mac CPU lightweight image
analysis only. Preparation uses R000; full diagnostic uses R001.
