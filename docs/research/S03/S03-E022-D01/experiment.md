# S03-E022-D01 — stage differences under common versus independent shifts

2026-10-15; S03; `stage-shift-v1`; C1 controlled-experiment DEVELOPMENT
counterfactual sensitivity diagnostic, not physical metrology or forecasting.
User authorises cached calculation/visuals/Obsidian. No new images, alignment,
fits, support/length sweep, model, human labels or old prediction scores.

## Ownership, question and allowed information

Reuse clean matching worktree `codex/crackmnist-tokenizer-mvp`, base
9eb12428294e4ed2028b00f9148a29d6c1b1a390. Scope new E022 runner/tests/render/
protocol/receipts/evidence and S03 index; previous files and raw data read-only.
No external transfer/push, producer solve or training. Safe for existing runs.

Question: how much of point-width spatial response cancels in a stage
difference when both stages have the SAME nominal tangent shift, versus two
independently varied shifts with identical marginal grids? Does this support
prioritising stable position correspondence rather than spatial smoothing?

Use unchanged E020 point half-depth widths, all12 Beam4 transects, three
adjacent stage pairs10→30/30→40/40→50kN and both frozen location arms.
OriginalH36 stage/transect pairs is primary; aligned36 secondary, not pooled
or selected for better results. One viewed beam, dependent positions/stages/
arms; no holdout, physical branch or material-coordinate certification.
Observed load stages are retrospective labels; do not infer next-load knowledge.

## Fixed finite counterfactual grid

Let A(d)=width at previous stage, B(d)=next stage, d∈{-2,-1.5,…,+2} native px.
Keep original five-line half-depth function; no segment median or new target.
Baseline D0=B(0)-A(0); zero-shift measured change is NOT physical truth.
Common differences Dc(d)=B(d)-A(d),9 diagonal pairs.
Independent differences Di(da,db)=B(db)-A(da),all81 Cartesian pairs.
Both finite marginals are equal-weight nine-point grids; this is a deterministic
stress test, NOT an estimated displacement distribution/error probability.
Positive d has the SAME frozen origin-frame tangent convention in both stages;
common nominal shift alone does not prove same material location or repairedH.
Inherited gray footprint makes each source strip extend±2 beyond its width
centre; tested union of raw tangential support is±4 around nominal centre.

## One primary descriptive comparison, rationale and feasibility

C=sqrt(mean_d (Dc(d)-D0)^2), I=sqrt(mean_da,db (Di(da,db)-D0)^2).
Primary=median(C-I) over matched ORIGINAL-H pairs, out36; negative means lower
finite-grid RMS response under common offsets. Report separate medians too,
never replace the median of paired differences with difference of medians.
Aligned36 is prespecified secondary. Equal/better/worse1e-8 arithmetic only.
No physical reference/noise-qualified margin exists: no pass/fail threshold,
independent-sample CI or forecast accuracy claim. No matched pairs=inconclusive.

Why RMS instead of only maxima: common diagonal is a SUBSET of independent
Cartesian grid, so maxIndependent>=maxCommon by construction, not an empirical
discovery. RMS comparison is not ordered automatically: with ea=A(d)-A(0),
eb=B(d)-B(0), exact identity I²-C²=2*cov_grid(ea,eb), population covariance.
Same NONFLAT spatial gradient plus an additive stage change gives C=0 but I>0;
opposite spatial gradients can give C>I. Synthetic tests must include both.
The primary tests the coupling/cancellation sensitivity under this fixed grid,
not whether unknown real offsets are common or physical width is accurate.

Secondary context, not votes: full signed common-response curves; C/I where
I>1e-8 (separately count zero-I pairs); maxC/maxI with nested-grid warning;
|D0| and C/|D0| for nonzero baseline only, all raw values retained; covariance
identity arithmetic check. Report for each perturbation whether its increment
is opposite to D0 or arithmetic zero; per pair count any sign loss (opposite
OR zero) AND loss fractions out9/common and81/independent, only if |D0|>1e-8.
ANY-loss independent>=common is also nested by construction and cannot serve
as independent evidence; normalized grid fractions are descriptive, not risks.
Baseline-zero pairs separately count nonzero
perturbed values. Fractions over grids are NOT physical event probabilities.

## Missing, identity, runtime and review

Require all9 A/B widths valid for a MATCHED pair comparison; no partial RMS,
different-support common/independent estimates, padding, interpolation or
point selection. Raw perturbation rows keep individually valid differences;
without valid D0 their baseline deviation remains missing. Unmatched pairs
remain in counts; all36 opportunities per arm reported. No division by zero.

Reuse reviewed E021 `load_snapshot` for E020 successful clean84c34422 identity,
3936/3840/96/96 cached key/grid/finitewidth/curve/adjacent/replay checks.
Record five source file paths/byte sizes and actual runtime identity; no new
external holdout, hash forest or raw resampling. Freeze code+protocol, synthetic
tests and independent read-only code review BEFORE new E022 calculation.
Mac lightweight R001, CPU AND wall60s, threads1; fresh output, stop on identity/
schema/budget errors with partial receipt preserved; no broad rerun/tuning.

## Figures fixed before results and minimum evidence

1. All36 matched pair RMS scatter per arm, identical axes/identity line,
   transition colours, primary paired-change annotation and count out36.
2. All36 pairs per arm: C, I RMS magnitudes and |D0| on shared native-pixel
   axis, ordered transition then transect; no hidden negative D0 in raw tables.
   Label absolute baseline signal as magnitude, not true growth or threshold;
   dimensionless C/I ratio is not plotted on this pixel axis.
3. All12 original-H transects: all3 signed Dc(d) curves over all9 d with
   D0 at d0, shared signed y-scale; shows nonuniform residuals/negative changes.
4. Preselected fixedT6: six9×9 deviation maps (3transitions×2arms), shared
   symmetric colour scale, previous-shift x/next-shift y, diagonal common,
   d0 centre marked. FixedT6 is not selected as representative performance.

Save5832 perturbation rows (648 common diagonal subset, not extra samples),
72 pair metrics, summary overall original/secondary plus each transition,
runtime receipt,4figure PNG/PDF sets with guides, README_analysis, independent
evidence review, compact tracked Run/evidence, S03 and Obsidian milestones.

## Component outcomes and next repair

If common RMS much lower but independent substantial, retain this cancellation
capability and prioritise how to maintain/verify correspondence; do not claim
correspondence is already achieved. If common remains comparable to the observed
increment or changes its sign, local correspondence alone is insufficient:
inspect spatially varying stage response/topology at the fixed affected cases,
not a more complex predictor. If I and C both small, retain the point difference
and prepare separate reference/forecast assessment. No physical acceptance
threshold is invented; report magnitudes and residual failures to select the
next smallest controlled test. Old observable/scores remain unchanged.
