# S09-E013 zero-step global/local ranking conflict

## Question

Can the proposed target-localised support score supply a useful ranking
direction from the frozen E010 B25 checkpoint while preserving the global
damage-amplitude ordering that is already correct?

The admission audit evaluates all 25 frozen growth-versus-stagnant pairs for
both the E011 global-ranking direction and the proposed local-support-ranking
direction.  It differentiates the exact merged/projected gradient through the
next frozen AdamW state.  It performs no optimiser step, no post-step forward
evaluation, and no fresh-holdout access.

## Evidence source and reading order

1. `zero_step_receipt.json` is the canonical producer receipt copied from
   Taobo.  Its SHA256 is
   `ec52d61d0872d2a618faa64cd438946c03f13f88c6b41d5f2d16bc9c86779784`.
2. `zero_step_analysis.json` is generated directly from that receipt.
3. `zero_step_global_local_conflict.png` shows the observable conflict and the
   exact first-order next-step consequences.
4. `observable_semantics_summary.json`, `cycle_truth_scores.csv`, and
   `pair_observable_audit.csv` are receipt/packet-only checks of the target
   observable, support normalisation, and all 25 pair identities.  They execute
   no model forward or autograd.

Read panel A first.  Positive margins mean the growth cycle ranks above the
stagnant cycle.  The global-amplitude and local-support margins have opposite
signs for all 25 pairs, with Pearson correlation `-0.8693`.  The 17 pairs that
are global wins are local-support losses; the eight global losses are
local-support wins.

Panel B propagates the proposed L25 direction through the exact next AdamW
state and uses the first-order global-margin change.  Fifteen of the 17
protected global wins cross to loss, while none of the eight global losses
cross to win.  Panel C compares the resulting global-win counts: 17 initially,
25 under the exact G25 global-ranking replay direction, and two under L25.

## Interpretation

The admission status is `ZERO_STEP_DIRECTION_STOP`.  This is a useful design
result rather than a failed training run: training never started and zero
optimiser steps were executed.

At the current B25 prediction, the proposed local score,

`mean positive increment inside target support - mean positive increment outside support`,

does not encode the same cycle order as the predicted global damage-increment
amplitude.  The receipt also exposes a protocol/classifier mismatch that must
not be retained: the frozen eight-pair error cohort is defined by predicted
global-amplitude loss, but the classifier selected predicted local-support loss
before comparing identities.  The two cohorts contain eight and 17
complementary pairs.

The read-only target audit rules out a stronger but incorrect interpretation.
On the FEM target fields, both global amplitude and local-support contrast rank
all 25 growth/stagnant pairs correctly and agree on all 25 labels.  The five
stagnant supports are not empty or numerically degenerate: they contain
4,795--5,374 nodes and 1.880%--2.113% of nodal weight.  The sign inversion is
therefore a property of the current B25 prediction and its local objective
geometry, not proof that the two physical target observables are inherently
incompatible.

## Allowed conclusion

Do not train the reviewed L25 objective.  At this checkpoint, the exact
first-order G25 direction repairs all eight global losses and flips none of the
17 global wins, whereas L25 repairs none and flips 15.  This does not establish
finite-step superiority: E011 already showed that a favourable one-step G25
prediction did not become a realised repair after 500 updates.  A later
localisation term should keep global amplitude ranking primary and expose its
trade-off as a constrained secondary objective or within-cycle spatial loss.

## Blocked conclusion

This audit is not a finite-step training result and does not prove that a
localisation-aware neural operator cannot work.  It does not evaluate unseen
cycles, autoregressive crack propagation, real-road data, damage stationarity,
history complementarity, or a full fracture PINO.  The linearised win counts
must not be reported as measured post-update AUC.

## Storyline impact

E013 closes the specific proposal of directly replacing the global pair
observable with the current target-support-minus-background score.  The next
design should first correct the cohort semantics, then keep global amplitude
ranking primary and add localisation through a protected multiobjective
formulation.  The zero-step report should show the full Pareto spectrum--wrong
pair improvements, protected-pair flips, and spatial gain--under a new,
prospectively reviewed staged criterion.  The observed `8/8` and `17/17`
counts are diagnostics, not a newly imposed all-or-nothing scientific gate.

## Recorded displacement-mixture decision

A final receipt-only audit tested the line segment

`delta(lambda) = (1-lambda) delta_G25 + lambda delta_L25`, `lambda in [0,1]`.

The two arms share the same model state
`4d353f6e...ab684f` and AdamW state `c7a4b497...b1e64`.  The audit interpolates
the recorded parameter-displacement inner products; it does not interpolate
losses and pass them through AdamW, execute an optimiser, or evaluate a new
field.

All global wrong-pair directions improve and all global protected-pair
directions regress throughout the segment; the categorical result is governed
by their relative magnitudes.  The last interval with any of G25's eight
predicted global repairs ends at `lambda=0.0686942444990416`.  The first
interval where local total wins exceed the G25 endpoint begins only at
`lambda=0.09782925602211034`.  These intervals do not overlap.

There is one narrow open interval,
`0.2186957629804058 < lambda < 0.232740643526109`, that recovers the initial
B25 totals of 17 global wins and eight local wins.  It does so by repairing six
local losses while flipping six different local wins; it repairs none of the
eight global losses.  No interval improves both global and local win counts
over the initial B25 counts.

The decision is therefore negative for this specific first-order segment:
there is no count-level local gain while retaining any predicted G25 global
repair.  This does not bound the operator's capacity and does not reject other
constrained directions.  The next intervention must change the direction
construction rather than select a scalar mixture of these two recorded
displacements.

## Files

- `zero_step_receipt.json`: canonical 25-pair, two-arm receipt.
- `zero_step_analysis.json`: generated compact counts and provenance.
- `observable_semantics_summary.json`: target/prediction semantic audit.
- `cycle_truth_scores.csv`: target global/local score and support definition by
  cycle.
- `pair_observable_audit.csv`: complete 25-pair truth, prediction, and
  first-order table.
- `zero_step_global_local_conflict.png`: three-panel diagnostic figure.
- `displacement_mixture_summary.json`: exact segment-level decision and
  identities.
- `displacement_mixture_breakpoints.csv`: all 55 recorded zero-crossing events.
- `displacement_mixture_intervals.csv`: exact piecewise-constant count table.
- `displacement_mixture_tradeoff.png`: global/local count trade-off and
  recorded `L_D/L_P` side effects.
- `scripts/plot_s09_e013_zero_step.py`: reproducible receipt-only analysis.
- `scripts/analyse_s09_e013_observable_semantics.py`: reproducible packet and
  receipt-only semantic audit.
- `scripts/analyse_s09_e013_displacement_mixture.py`: reproducible
  receipt-only displacement-segment audit.
