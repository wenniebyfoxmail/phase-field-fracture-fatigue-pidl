# Figure-set reading guide

**Status:** specifications frozen; no S02-E001 performance figures generated  
**Reason:** event/data qualification failed before baseline execution

## Scientific question

Can the framework warn before a transition, propagate accurately within a
regime, generate the transition autonomously, recover after causal observation
assimilation, and express increasing uncertainty with horizon?

## Required reading order

1. `figure_1_warning_timeline`: one panel per held-out trajectory showing
   observation times, first detect, censoring/reset, h1-h3 probabilities,
   operating threshold, correct-warning lead and false alarms.
2. `figure_2_precision_recall_calibration`: trajectory-clustered PR curves and
   reliability plots for CUSUM-derived score, hazard, Markov and later neural
   challenger. Annotate independent trajectory counts.
3. `figure_3_same_regime_h1_h3`: error and field/geometry panels by horizon,
   with persistence and secant first.
4. `figure_4_autonomous_transition`: free rollout across the held-out first
   detect, including event topology and warning probability. Never replace this
   with an event-aligned oracle reset.
5. `figure_5_post_transition_reset`: side-by-side free, observable-reset and
   Tier-A oracle-reset continuations, explicitly labelled conditional.
6. `figure_6_rolling_assimilation`: forecast issue/update timeline with errors
   before and after each causal observation.
7. `figure_7_uncertainty_growth`: interval width, empirical coverage and proper
   score versus horizon, summarized per physical trajectory.

## Rendering rules

- Tier-A field figures put FEM first and use common domain, area weighting and
  color limits; show absolute FEM-p99 and own-p99 support separately.
- Tier-B figures use registered physical coordinates and show uncertain or
  unobserved areas explicitly.
- Same-regime, autonomous-transition and conditional-reset results never share
  a pooled headline score.
- Event-aligned stress panels carry a visible `retrospective` label.
- Do not draw PR/calibration curves until both event-positive and event-negative
  held-out opportunities exist at trajectory level.

## Current cross-figure interpretation

Existing evidence indicates that same-regime propagation and observation reset
can work while autonomous transition generation fails. This motivates the
two-stage design but does not validate it. No new claim-bearing figure is
created from incomplete data.

## Allowed conclusion

The figure suite and estimands are preregistered, and existing results justify
separating warning, free rollout and assimilated continuation.

## Blocked conclusion

No transition-warning accuracy, calibration, road deployment, autonomous
transition skill, or neural advantage may be claimed from S02-E001 v1.

## Storyline impact

S02 remains data/acquisition and transparent-baseline limited. A qualified
future package must populate this exact suite before neural promotion.
