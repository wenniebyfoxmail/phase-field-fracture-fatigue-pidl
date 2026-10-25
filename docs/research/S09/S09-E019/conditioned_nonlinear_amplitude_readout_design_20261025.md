---
experiment_id: S09-E019
status: DESIGN_AND_LOCAL_IMPLEMENTATION_IN_PROGRESS
mode: scientific_validation_exploration
continuation_of: S09-E018
---

# S09-E019: conditioned nonlinear amplitude readout

## Decision and evidence

E018 completed its paired 64-update run with valid artifacts but rejected the
merge-cancellation explanation: protecting the amplitude direction reduced the
high-event predicted mass from 0.351 (symmetric PCGrad) to 0.133, while the FEM
mean event mass remains orders larger.  The smaller pixel MAE of the priority
arm is a near-zero-field effect, not an amplitude recovery.

The affine residual used in E017/E018 is

`r = w^T pooled_hidden + b`, `a = a_base exp(r)`.

At update 64, its cycle-to-cycle feature span was only `9.53e-4` under PCGrad
and `1.61e-2` under priority.  A deeper function of this nearly constant vector
alone has no identified reason to separate high event cycles.  E019 therefore
tests capacity supplied by **causal transition-origin condition**, rather than
another objective merge.

The mapping remains exactly the existing independent transition:

`(d_pre(x), history_pre(x), load_path, mesh/material/BC) -> (d_peak(x), history_peak(x), u_peak(x))`.

It is still not an autonomous rollout, a fresh holdout study, or a road claim.

## Intervention

Use two factorised arms from the same pristine checkpoint, with the existing
shape head, objective groups A/S/R/P, symmetric weighted PCGrad, AdamW schedule,
16 exposed transitions, beta=.25 native-Q4 AMOR equilibrium residual, and
64-update budget unchanged.

1. `F_AMP_SHAPE_PCG`: the E018 symmetric-PCGrad reference.
2. `F_AMP_SHAPE_COND_NL`: only replace the affine amplitude residual with a
   16-unit GELU MLP.  Its input concatenates the existing pooled node-hidden
   vector and origin-only conditioning features: area-weighted mean and second
   moment of `d_pre`, area-weighted remaining capacity, each history channel's
   area-weighted mean, and the supplied load-path entries.

The feature normalisation mean/scale is frozen from those 16 admitted origins
before optimisation.  It may not use cycle IDs, FEM targets, post-state fields,
future history, held-out transitions, or any output-derived statistic.  The MLP
final layer is zero-initialised, so `r=0` at update zero and the pre-existing
`a_base exp(r)` decoder replays exactly.  `8 tanh(raw/8)` bounds the residual
without changing its zero-replay property; the existing irreversible bounded
damage decoder still guarantees `d_pre <= d_peak <= 1`.

This is a readout-capacity ablation, not a representation or physics change.
If it fails, the next distinct hypothesis is trainable representation, not a
larger MLP sweep.

## Relaxed exploratory decision rule

The paired update-64 primary observable is the median high-event (cycles
46/48/58/60/69/70) log-mass error,

`abs(log10(sum Delta_d_pred + 1e-12) - log10(sum Delta_d_FEM + 1e-12))`.

E019 shows a useful early capacity signal if the conditioned arm reduces that
median by at least 0.5 log10 relative to its same-run PCGrad control, keeps the
mean near-stagnant mass (3/4/71/72/73) no greater than 1.5 times control, and
has no hard-constraint violation.  This deliberately modest criterion only
asks whether the readout escapes the collapsed amplitude regime; it is not a
claim of FEM reconstruction, phase-field closure, generalisation, or PINO
success.  Plot both mass and peak, plus the state/increment five-column fields;
never judge by MAE alone.

If the condition arm cannot clear this signal, stop amplitude-head tuning and
move to a separately designed, bounded trainable-representation test.  If it
does, retain the component result and next test it on a frozen grouped holdout
before making any transition-prediction claim.

## Local implementation boundary

`source/s09_e019_conditioned_amplitude.py` is an I/O-free primitive.  Its fixed
benchmark checks that all conditioning derives from allowed origin inputs, that
the feature width is explicit, and that the new readout gives exact zero
residual at initialisation while remaining finite and bounded after activation.
It is not yet wired into a producer or assigned a run card; no GPU work is
authorised by this design document.
