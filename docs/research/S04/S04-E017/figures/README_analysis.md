# S04-E017 decision figures

## Question and evidence

Can fixed unbiased damage-stratum batch fractions α=0.5,0.7,0.9 recover the
same-state supervised FEM UV objective within seed7/10000steps, and do their
regional error trajectories differ across early/middle/transition states?

Exact scored assets: all12 admitted runs from
`S04-E017-alpha-ed3adce-20261012T170600Z-bundle`, code
`ed3adcef880e711aed175578a7da7861cfb746aa`, compact retrieved bundle under
`local_archive/experiments/S04-E017/runs/S04-E017-R013-posthoc/retrieved`.
Script `../analyze_ratio_results.py` verifies12unique arms, completed receipts,
prediction/monitor SHA identities,11 frozen monitoring points per run and
weighted-error decomposition. It does not use partial archives or enter training.
References match scored identities: E013 admitted c20/c60/c83 HTTP-input packages;
c40 E009 qualified conditional UV package. Damage/history/fatigue stay frozen.
These are synthetic same-state development fits, not independent validation.

## Reading order and definitions

1. `final_ratio_comparison.png/pdf`: all4states, all3ratios, finalstep10000 only.
   Panels show full mass-weighted UV RMS/|Us|, conditional damage/background RMS,
   and weighted background contribution fraction. The1e-3primary tolerance is
   visible. c40*is the mandatory sentinel; the primary vote uses c20/c60/c83.
2. `fixed_trajectory_regions.png/pdf`:11passive full-field monitoring points,
   including initialization for context. Columns separate whole-field, damage,
   background conditional RMS and weighted background fraction. Numeric spike
   diagnostics explicitly exclude only step0 (use1000..10000); late diagnostics
   use7000..10000. Checkpoints cannot vote or select outputs.
3. `fixed_alpha07_uv_fields.png/pdf`: all4states at fixedα=.7, finalstep10000,
   columns FEM verticalv/Us, predictedv/Us and log10vectorUVerror/|Us|. All target
   and prediction panels share their full nodal value range[-.0399648,1.0408106].
   Error colours use common log10scale[-8,log10(.5880662)], with floor1e-8.
   Q4 polygons display the arithmetic mean of four nodal colour values (including
   logarithmic error colours); this visualization reduction never changes the
   original nodal mass-weighted metric. No interpolation across a Q4 crack/notch
   void is added. α=.7was fixed for display and E018's comparison before results;
   it is neither the statewise bestαnor the formal selected developmentα.

Exact tables `../ratio_comparison.csv` and `../trajectory_diagnostics.csv` are
numerically authoritative. Each identifies full RunID/state/alpha. Contributions
C_A/C_Bare global weighted squared errors. ConditionalRMS divides each by its
own stratum probability. Background fraction=C_B/(C_A+C_B), not background
area or conditionalRMS ratio. The figures explain these values and do not vote.

## Cross-figure interpretation

Every finalUV error is0.00307912..0.00417045, above1e-3. No fixedαpasses the
three-state criterion. Descriptive statewise minima occur atα=.7forc20,
α=.9forc40/c60, andα=.5forc83. The preregistered minimum worst-state error over
all4states chooses fixedα=.9(max.00343512), compared withα=.7(max.00348781) and
α=.5(max.00417045). Statewise minima must not become a mixedαpolicy after viewing
results. α=.9c20/c83 reproduces E014 finalUV/strain/rho exactly.

Transient background shifts depend on state and fraction. For example,
c20α=.7has42.811%weighted background error atstep2000; c83α=.5has33.617%at4000,
α=.9has51.286%at6000, while c83α=.7's post-initialization maximum is4.243%at1000. Thus decreasing
αdoes not uniformly remove transient shifts. Late-window maxima across all
arms are0.339%..4.996%; final background contributions are only0.231%..0.759%.
Final conditional backgroundRMS is.0001592..0003450, versus damage conditional
RMS.0193405..0303787. This shows residual final weighted error is primarily in
the damage-defined stratum for these procedures; it does not establish why.

## Allowed conclusion, blocked conclusion and next decision

Allowed: sampling ratio materially changes state-specific trajectories and some
final errors; all12fresh fits miss the desired fidelity under this fixed procedure.
α=.9remains the preregistered development choice, and α=.7remains the separately
frozen E018 sampler. α=.9's damage-aware benefit seen in E014 is retained rather
than erased by the failedabsolute gate.

Blocked: architecture is provably insufficient; training has mathematically
converged; the transient is uniquely caused by background undersampling;
α=.9is universally optimal; seeds or states from this one trajectory demonstrate
transfer; history/energy/teacher accuracy or fullFEMreproduction is qualified.

Storyline impact: these measurements support advancing the already-reviewed
E018global/local matched representation screen after E017evidence closure, with
fixedα=.7and early/middle/transition coverage. They do not authorize a broader
sweep, extend10000steps, or change E017's frozen verdict. E018success is unknown.

## Render QA

All3PNGsets visually inspected after regeneration: all states mapped correctly,
no missing/blank panels, readable threshold and labels, common field scales,
FEM first, region/fraction quantities distinct. PNG/PDF share the same generated
figures; no manual curve editing. Initial scatter field rendering was replaced
by filled Q4 polygons to avoid misleading visibility from varying node density.
