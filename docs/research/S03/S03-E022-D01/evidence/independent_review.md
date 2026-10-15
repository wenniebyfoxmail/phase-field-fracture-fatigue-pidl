# Independent code and evidence review — 2026-10-15

Reviewer `/root/halfdepth_code_review`, read-only, no actual aggregate runner,
fresh pixel access, fit, training, forecast or file changes. Protocol
`stage-shift-v1`, numeric clean247b8f6ac0f31b09ca70411baceeb2baae5c3bf6.

## Design/code before real execution

Same nine-point marginals for9common/81Cartesian combinations; RMS comparison
not nested automatic ordering. Diagonal maxima and any-sign-loss ARE nested,
so their raw inequality is context only. Population covariance identity and
same-gradient/opposite-gradient counterexamples checked. Complete9A/B support,
matched primary36original-H pairs, paired median(C-I), aligned secondary,
zeroI/zeroD0, negative increments, missingNone notfalse, no physical threshold
or independent-sample uncertainty correct. Reused E021load_snapshot unchanged.
Reviewer independently reran11synthetic tests, all passed0.015s before R001.
Main11snapshot-helper regression tests also passed. No execution blocker.

## Numerical evidence

Directly from E020 CSV, reviewer independently recomputed all72complete9×9
matrices/5832cells/648diagonal cells: values,valid/common flags,D0,deviations
all agree. All per-pair C/I/D/covariance/identity/ratios/maxima/sign/zero/
opposite/lossfraction agree. Every primary/secondary and transition summary
field independently recomputed and matches. All72matched, allD0nonzero and
I>arithmeticEPS, no missing. Input5file paths/sizes, successful cleanE020
identity and E022clean247b8f6 receipt checked. Wall.067074375s/CPU.04584s,
threads1 within60s. Retrieval verified local.

Primary original36: Cmedian.229766384759/I1.001379164566,
pairedmedian-.843257837256;35commonlower/1higher, median pairwise ratio
.335999307745. Aligned pairedmedian-.834041940780;35/1,
median ratio.172631958553. Original common/independent signloss4/26,
aligned6/26; nested context, not extra proof. C>=|D0| original7/36,
aligned2/36. Unique C>I both armsT4/10→30kN: original.260706071/.223434512,
aligned.255154198/.216875263, confirms no automatic RMS ordering.
Original common-loss cases exactlyT2/10→30,T11/30→40,T2/40→50,T3/40→50.
Covariance arithmetic identity maximum residual3.55e-15/7.11e-15px² is
computation self-consistency, not physical precision.

## Figure repair and final visual check

Initial R001 plot1 aligned legend obscured3highI/lowC T1 points; main and
reviewer independently detected. Renderer-only365908d49e13777d459cd9cad4e81fbebeb76689
small diff reviewed before fresh R002: legend outside panels, no data/statistic/
coordinate change. Reviewer inspected finalR002plot1: all3points now visible,
no overlap. Independently cmp other3PNGs, byte-identical toR001 and visually
checked; all4finalfigures readable, signed/shared axes, matrixprevious-x/next-y/
originlower/diagonal/sharedcolour correct. Plot2 C,I,|D0| are allpixels,
not ratio mixed on pixel axis. Main sidecar check8formats/4notes passed.

## Interpretation and closure

Bounded C1 diagnostic supports cancellation capability under common nominal
coordinate shifts, worth prioritising stable correspondence research/verification.
It does not achieve/verify actual correspondence or remove all difference
sensitivity. No physical/predictionerror claim or uniformgridfraction risk.
Keep old observable/scores; next proposed relative-shift tolerance/reference
comparison is separate, not executed. README/compact final wording check follows.

## Final wording check

Reviewer read R002README, compact summary and R001receipt: no numerical drift
or claim overreach. Pairwise-ratio median is distinguished from ratio of
separate medians, and not phrased as66%/83%physicalerror reduction. Normalized
loss percentages correct/nonprobabilistic, nested ANY-loss warning retained.
All7original commonRMS>=|D0| identities and4flip cases match saved tables;
allzero counts in both arms are0, so the text's "opposite, no zero" is exact.
Conditional counterfactual is not actual material correspondence/physical
accuracy/prediction. Next proposed tolerance requires its own frozen metric/grid,
no old-score tuning; not executed. Final Outcome/S03/Obsidian and R002receipt
record the same reviewed facts; no further numerical/method change needed.
