# E043 — separate detected support from conditional row mass

2026-10-18; exploratory repair on one already-exposed MD01 trajectory.
User explicitly approves frozen identification, separate support/thickness inputs,
comparison to persistence/secant, no error-selected settings, figures and Obsidian.
User explicitly revokes the old80%usage stop rule; it is not a condition here.
Residual shadow/texture false positives are acknowledged, not removed or relabelled.

Question: does separating coverage from conditional size reduce the observed
coverage-driven slope problem without changing any candidate pixels?

Data: unchanged E038 R001 five stages18,19,21,22,23, all nine saved settings.
Same E037 image band[3900,1700,4600,1950],250rows×700columns. E041 accepted
Step19 must match v1 inside this band. No other images, thresholds or segmentation.
All windows unchanged:18,19→21;19,21→22;21,22→23. Origin=second history,
requested horizon measured in stage index, not physical time, cycles or kN.
Future target masks are not used by the prediction function, but were already
exposed in prior work: this is not a prospective blind test.

Definitions, frozen before this calculation:
- A=number of candidate pixels in band, px².
- L=number of image rows containing any candidate, image-row px,0..250.
- M=A/L=mean candidate-pixel count among occupied horizontal rows, px;
  undefined if L=0. M includes multiple blobs/branches/shadows per row, not
  their enclosing span, normal crack width, EDT diameter or old half-depth.
- Exact identity A=L*M. L is detected support, NOT true visible crack length
  or recall. M is a conditional row-mass/thickness proxy, NOT physical aperture.

Methods, with q=(target-origin)/(origin-previous):
1. Persistence Ahat=A_origin (reuse E042 exact comparator).
2. Area secant Ahat=max(0,A_origin+q*(A_origin-A_previous)).
3. Separated support-hold: Lhat=L_origin;
   Mraw=M_origin+q*(M_origin-M_previous);
   Mhat=clip(Mraw,0,700); Ahat=Lhat*Mhat.
   The bound700 is the fixed image-band width, not a fitted cap. Keep raw values.

Mechanism rationale: without an independently identified visibility process, do
not extrapolate detector support loss as physical crack shortening; persist L
and test whether within-detected-row size carries a useful signal. This can
underpredict when support newly expands. No selection among alternative L models,
no damping fit, no optimum based on target errors. Design is informed by prior
development results and must not be promoted to independent validation.

Primary diagnostic: candidate-area AE per all3fixedwindows and equal-window MAE
against both comparators, same target masks. Report gains, missingness and clips.
Secondary: L/M errors separately, all nine cached definition sensitivities,
row-mass profiles/distributions for all five stages. Same arm across every stage;
do not promote the best arm. Zero/missing history coverage yields null for method3,
not a zero-thickness observation; preserve comparators and denominator reporting.

Budget: one cached numeric analysis <=60sCPU/wall, no GPU, training, new inference,
holdouts or raw image decoding needed. Plot from exact saved tables/profiles,
reuse E042 raw/mask visual as the source reference. Relevant synthetic arithmetic
tests and post-run checks, no separate independent-agent review required for this
small exploration. Protect old mask/half-depth/scoring hashes; never alter E042.

Figures: F01 all5 L/M trajectories and per-row candidate-mass profiles, with
zeros/missing-support shown rather than filled. F02 all3window predictions and
errors plus all9setting gains. Native image units, same cases, no confidence-band
claim. Shadow/texture contamination explicit in both figures and conclusions.
Next decision: retain component gain if present; no physical-truth/road claim.
