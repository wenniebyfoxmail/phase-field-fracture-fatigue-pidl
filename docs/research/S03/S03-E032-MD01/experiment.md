# S03-E032-MD01 — background-informed position sensitivity

2026-10-16; S03; protocol `md01-position-sensitivity-v1`; baseaecb021.
User approves using ONLY the existing three MD01 images for position sensitivity,
unchanged half-depth definition and E031 scores, no error-based position choice,
visual comparisons and Obsidian sync. No new photos, annotations, NCC fitting,
training or model tuning. This is a NEW viewed-development diagnostic, not an
amendment that rescues/changes E031's positive single-case optical-width result.

## Bounded question and unit

C2 position/measurement sensitivity of an inherited C3 comparison; controlled
experiment, one viewed source record and one transect, origin28/target29.
Does secant's lower same-target absolute error persist at background-determined
alternative sampling positions? Stage27/28/29 = IMG_0403/0406/0409.JPG, from
E031 source folder. No absolute kN or physical crack-width claims.
Target29 and E031 widths/errors already viewed. Target background may determine
the stress range, so this is NOT a new prediction using origin-time information.

## Position rules, before shifted-width access

Reuse E031's once-refined centre, fixed normal n, tangent t=(-ny,nx), fixed
first-to-later median translations and all four fixed background correspondences.
No refit, normal adjustment, centre refinement, quality-based point deletion or
search for favourable width error. For j=28/29 and each anchor i define
r[j,i]=anchor_translation[j,i] - saved_median_translation[j]. This is a possible
local sampling displacement, NOT a known crack-position error or probability.
Each residual's normal/tangent projections retain the paired signed vector.

1. COMMON spatial displacement: Rn=max|r.n| and Rt=max|r.t| over all8saved
   residuals. Cartesian fractions{-1,-.5,0,.5,1} of Rn/Rt give25positions.
   Apply exactly the SAME displacement fn*Rn*n + ft*Rt*t to all3stage centres.
   This asks whether nearby spatial location alone changes the comparison.
   Global envelope corners are stress points, not proven possible error pairs.
2. INDEPENDENT stage mismatch: stage27 remains at its reference centre. Stage28
   selects from{M=zero,L1,R1,L2,R2 residuals}; stage29 independently selects the
   same5anchor identities' residuals at29. Full5x5=25combinations, no dropping.
   Four same-anchor temporal paths plus M/M are labelled subsets, not extra
   independent cases. Do not rotate or mix components to manufacture extremes.

All50scenario IDs, sampled centres and residual provenance must be saved and
committed before any new shifted profile is read. Up to83unique profiles
(75common plus8nonzero anchor residual profiles); shared zero shifts cached.
Signed offsets are ADDITIVE to E031's source-sampling position. First-stage
unknown absolute errors are not inferred from unavailable first-stage residuals;
the common grid separately tests a shared absolute-location change.

## Same measurement and meaningful comparison

Reuse E031/old sample_profile + measure exactly: native gray; normal offsets
-60:.25:60, five tangent lines[-2,-1,0,1,2] median; shoulder medians|s|>=45,
straight background, core peak|s|<=15, half-depth interpolated crossings and
same depth/noise/resolution/censoring QC. No offset-dependent re-centring.
Before interpreting perturbations reproduce all3E031 baseline profiles/widths,
both predictions/errors at1e-8px software tolerance; otherwise stop, no tuning.

For EVERY available scenario, use its w27/w28 history to form persistence=w28,
secant=clip(2*w28-w27,0,120). Both score against its SAME w29 reference.
This is retrospective propagation of a position assumption, not new forecast
validation or replacement scores. Save raw/clipped values and changes of
prediction, target and signed error relative to E031 so target changes are not
mislabelled as pure forecast improvements. Also report the optional fixed-E031-
prediction vs varied-target comparison from the same data, as secondary only.

Primary quantity: Delta=abs(secant-w29)-abs(persistence-w29), lower than0 favours
secant. Report count/available/nominal, full min/max range and EVERY point for
each prespecified family. Numerical ties |Delta|<=1e-10px, not physical tolerance.
No new minimum margin, majority/all-case pass requirement or significance.
All retain -> tested finite set consistent with retention; some reverse ->
conditional location sensitivity, not whole-route failure; no valid comparison
-> inconclusive. All variants valid does not prove continuous robustness.
Invalid profiles retain null/reason and scenario denominator; never fill0.
Envelopes/combinations are sensitivity assumptions, NOT CI or calibrated bounds.

## Execution, visualization and next decision

Only existing E031 JSON/NPZ and3JPEGs; original protocol, geometry, measurement,
prediction/summary files remain byte-identical. New source metadata lock has
no error-based selection logic. One metadata prepare then one lightweight Mac
CPU run with120s external timeout, no GPU or training. Reuse matching worktree;
synthetic tests and independent read-only exact-code/protocol/lock review before
image sampling, then independent reproduction before closure.
New files/runs under local_archive/experiments/S03-E032-MD01; compact receipts,
lock and verdict under this Experiment. No edits to E031 code or output files.

Minimum figures: common25Delta map; independent25Delta map on shared signed
scale; paired same-target error points against equal-error line (all50), plus
same-scale source crops and plotted displacement support. Label development,
one case, native pixels, origin28/target29, RunID and no-probability semantics.
PNG/PDF, visible/gray QA and README_analysis.md. Show primary comparator, not
only width changes or pooled means. No best-error example selection.

If retained: retain the finite-set location evidence and identify the cheapest
independent continuation/measurement check, without repeating this viewed score.
If reversals: separate common-location versus stage-mismatch failures, freeze
the background-driven repair question rather than choose the winning offset.
No physical correspondence, independent beam, road transfer or optimum-position
claim. Obsidian reuses existing multimodal task note and one Roadmap link.

Status: protocol prepared before perturbation widths; no shifted images measured.
