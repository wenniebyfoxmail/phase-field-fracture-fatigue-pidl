# Request 28 plain-versus-enriched observability gate

Date: 2026-08-18

## Five-question lock

1. **Mechanism question**: at first-detect peak displacement, does a fixed
   crack-oriented antisymmetric opening representation encode the immediately
   preceding process-zone state better than a plain Q4 displacement-gradient
   representation?
2. **Success claim**: retrospective two-coordinate observability is positive
   on these three matched Hard-5 trajectories.  This is not early prediction.
3. **Failure claim**: close the XDEM-like displacement-observation route; do
   not rescue it with KAN, Williams-basis search, tuned ROIs, or a second
   enriched representation.
4. **Cheaper diagnostic**: Request 28 already supplies the exact three
   post-commit `c-1/s5` hidden states and `c/s4` event displacement fields, so
   no FEM replay, PIDL run, or model training is permitted.
5. **Minimum retained asset**: frozen script, physical-coordinate table,
   fold-level predictions, manifest, attempt ledger, and terminal decision.

## Frozen data

| case | hidden source | displacement observation |
|---|---:|---:|
| U0.11 | c121/s5 post-commit | c122/s4 first-detect peak |
| U0.12 | c82/s5 post-commit | c83/s4 first-detect peak |
| U0.13 | c58/s5 post-commit | c59/s4 first-detect peak |

`c0/state0` is initialization and is not used.  Confirmation cycles are not
read.  The declared initial crack tip is `(0,0)`, tangent is `+x`, normal is
`+y`, and forward ligament length is `L=0.5`.

## Frozen physical targets

For prior-state Q4 cell `i` in the entire forward ligament `x_i >= 0`, define
`w_i=4*d_i*(1-d_i)`.

- `z_H = sum(A_i*w_i*alpha_bar_i) / sum(A_i*w_i)`.
- `z_F = sum(A_i*w_i*x_i) / (L*sum(A_i*w_i))`.

If `sum(A*w) <= 1e-14`, the target is undefined and the gate fails.  Maximum
front x, thresholded damage support, percentiles, and learned POD targets are
forbidden.

## Frozen displacement representations

PLAIN is computed from event `u_node` and native Q4 geometry only.  An affine
least-squares Q4-centre gradient gives infinitesimal strain and
`q_i=||epsilon_i||_F`.

- `p_H = sqrt(sum(A*q^2)/sum(A))` over the forward ligament.
- `p_F = sum(A*q^2*x)/(L*sum(A*q^2))`.

ENRICHED uses positive-side forward-ligament Q4 centres as the fixed quadrature
set.  Each centre is mirrored across `y=0` and paired to the nearest
negative-side Q4 centre, with lexicographic element index as the deterministic
tie-break.  The maximum distance is the median `sqrt(cell area)` over the
forward ligament.  More than 1% unmatched positive-side area fails the gate.
For each accepted pair,
`o=((u_plus-u_minus).n)/||x_plus-x_minus||` and `e=o^2`.

- `e_H = sqrt(sum(A_plus*e)/sum(A_plus))`.
- `e_F = sum(A_plus*e*x_pair)/(L*sum(A_plus*e))`, where `x_pair` is the mean
  pair x coordinate.

No displacement feature is normalized by a hidden field.  No crack-tip search,
fitting radius, Williams basis, candidate ROI, or target-dependent pairing is
allowed.

## Frozen estimator and controls

Each Umax is held out once.  The other two cases define the unique affine map
`z_hat=a+b*r`, separately for `p_H -> z_H`, `e_H -> z_H`, `p_F -> z_F`, and
`e_F -> z_F`.  Predictor separation `<=1e-14*max(1,|r1|,|r2|)` is undefined.
Slope `b<=0` is `NON_MONOTONE_REPRESENTATION` and fails structurally.

Controls are the two-training-target mean and the two-point Umax-only affine
map.  `z_H` error is both raw absolute error and
`abs(error)/(abs(z_H)+1e-12)`; `z_F` error is absolute ligament-normalized
error.  No cell-level hypothesis test or confidence interval is reported.

## Decision rule

`ENRICHED_RETROSPECTIVE_ENCODING_POSITIVE` requires:

- all six enriched fold-target calibrations are defined with positive slope;
- enriched error is strictly smaller than plain error on all 3 folds for both
  targets (6/6);
- enriched error is strictly smaller than Umax-only on all 3 folds for both
  targets (6/6).

The training-mean control is descriptive.  Failure of either target fails the
combined hypothesis.  No tuning or second enriched variant is allowed after
opening the results.

## Claim boundary and next authorization

A pass may authorize only sparse, preregistered earlier hidden-state origins
such as `Nf-2`, `Nf-5`, and `Nf-10` to measure an event-relative observability
horizon.  Those offsets still do not validate early warning because `Nf`
selects the origins.  A genuine early-warning test later needs fixed
calendar-cycle origins and independent trajectories.

## Terminal result

Verdict: **`ENRICHED_RETROSPECTIVE_ENCODING_NEGATIVE`**.

The geometry-only pairing gate passed: all cases retained 7,159 positive-side
pairs and the unmatched positive-side area fraction was only
`1.6174e-05`, versus the frozen 1% maximum. The result is therefore not a
pairing-coverage failure.

| case | zH | zF | pH | pF | eH | eF |
|---|---:|---:|---:|---:|---:|---:|
| U0.11 | 1.049856 | 0.493006 | 2.445018 | 0.496408 | 1.879530 | 0.420320 |
| U0.12 | 0.884256 | 0.479183 | 2.674590 | 0.499431 | 2.380912 | 0.514413 |
| U0.13 | 0.737829 | 0.491054 | 2.894587 | 0.499887 | 1.877565 | 0.457384 |

ENRICHED beat PLAIN in only `3/6` fold-target comparisons and Umax-only in
only `3/6`. More decisively, not all enriched calibrations were monotone:
all three `z_F` folds had negative slope, and the U0.13 `z_H` fold was also
negative. The U0.12 enriched `z_H` two-point extrapolation predicted
`80.6862` against `0.8843`, exposing instability rather than a usable
coordinate.

The constructive diagnostic is that PLAIN `p_H` gave small raw
leave-one-Umax-out `z_H` errors (`0.00626--0.01280`, relative
`0.71%--1.66%`) but with negative slopes. That sign is physically compatible
with the confounding in this event-aligned sweep: larger Umax reaches first
detect in fewer cycles and therefore carries lower cumulative history. It
does not rescue the frozen enriched hypothesis. It instead motivates a
future, separately locked fatigue-exposure coordinate that separates load
amplitude from elapsed cycles.

Reproducibility checks passed: a fresh second output root was byte-identical
for all four decision payloads, and a synthetic affine-displacement unit test
recovered the exact Frobenius strain norm `sqrt(22)`.

Evidence root:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/request28_xdem_observability_gate_20260818/`

Per the frozen stop rule, no pairing/ROI/Williams/KAN rescue and no sparse
earlier-origin request is authorized by this negative combined gate.
