# Cross-Umax state-conditioned transition track

**Owner:** Mac-PIDL  
**Status:** closed negative oracle gates  
**Claim class:** trajectory-sufficiency, not autonomous timing

## Mechanism question

Does the exact pre-event FEM state contain locally transferable information
that improves the one-cycle first-detect field beyond a shared event-aligned
mean increment across Umax?

## Claim boundary

The independent units are three matched Hard5/eta0/five-step trajectories at
Umax 0.11, 0.12, and 0.13. Event-relative alignment is retrospective. A pass
can support only a same-geometry, same-material conditional transition claim.
It cannot support autonomous fatigue-life prediction, new geometry/material
generalization, or a deployable observation model.

## Completed gate

Frozen pairs were c121→c122, c82→c83, and c58→c59. The candidate was a
coordinate-free, fixed-lambda local ridge residual model. Controls were
persistence, mean-delta, and linear-Umax delta. The primary criterion was
trajectory-level leave-one-Umax-out absolute-p99 active-support localization.

Full local preregistration and generated assets live under:

`local_archive/after_strict_setting_alignment/fem/cross_umax_state_conditioned_transition_20260817/`

## Result and next action

The ridge active-energy IoUs were `0.8174/0.8066/0.8574`, below mean-delta
`0.9720/0.8470/0.9219`; it predicted zero right-boundary penetration elements
on all folds versus FEM `8/6/6`. The candidate therefore failed 0/3 topology
gates and provided 0/3 incremental localization wins. Retain mean-delta as the
same-family oracle control and do not open PIDL+10% assimilation with this
transition. Any nonlinear, spatial-template-residual, or multi-cycle successor
must be a new preregistered estimand, not a post-hoc rescue.

## Gate C-NL v1 development A1 (2026-08-18)

Following GPT Pro strategy review, a new development-only nonlinear candidate
was preregistered before evaluation. It was a deterministic 27-bin local
lookup over current damage, recomputed fatigue factor, and current raw-energy
area rank. It predicted one-cycle increments in damage, history, and raw
energy, with equal trajectory weighting and linear-Umax interpolation across
the two training trajectories. Coordinates, event-relative time, target maps,
and Gate A observations were excluded.

The first ladder stage used exact current FEM state from c20 through
first_detect-1. Against the linear-Umax control, the candidate improved only
`1/4`, `1/4`, and `0/4` metrics on U0.11/U0.12/U0.13. U0.11 damage was
catastrophic with an error ratio of `2.0438`, above the locked `1.25` ceiling.
Thus A1 passed `0/3` trajectory challenges.

The preregistered stop rule was applied: A2 ten-cycle rollouts and A3
autonomous timing were not run, and no new FEM/PIDL producer was launched.
This rejects the 27-bin local Markov candidate; it does not establish that all
nonlinear transitions are impossible. It also does not support escalation to
a larger learned architecture on the same three seen trajectories.

Full preregistration, code, metrics, deterministic rerun hashes, figure, and
decision live under:

`local_archive/after_strict_setting_alignment/fem/cross_umax_state_conditioned_nonlinear_development_v1_20260818/`
