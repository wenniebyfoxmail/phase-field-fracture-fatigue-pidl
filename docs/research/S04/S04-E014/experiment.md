---
storyline_id: S04
experiment_id: S04-E014
protocol_revision: 20261011-r0-posthoc
status: offline-diagnostic-running; producer-repair-not-yet-authorized
---
# Select the first controllable repair after S04-E013

Current status: R001 selected unbiased damage-stratified sampling; R002
completed the reviewed c20/c83 screen and received `EVIDENCE PASS` for
`SAMPLING_ONLY_REPAIR_REJECTED`. No rerun is required. The next experiment may
design, but may not yet execute, one bounded local/multiscale representation
screen.

## Question and decision

S04-E013 established that the fixed 10,000-step supervised procedure failed
all displacement, strain and weak-form gates from c20 onward. S04-E014 asks
which first controllable lever should be tested before any unsupervised Stage 2
run: stochastic optimisation/sampling, spatial representation, or the
derivative/mechanics objective.

This is a synthetic-domain C0/C1 repair-selection diagnostic. It does not
reopen or modify the S04-E013 verdict.

## R001 frozen offline scope

R001 reads only the completed S04-E013 Attempt B assets:

- c20s4, c60s4, c82s4 and c83s4;
- seeds 1, 7 and 19;
- final predictions, exact admitted references and 100-step sampled-loss logs;
- the original frozen metrics and thresholds.

It performs no optimiser step, damage solve, history update or producer
mutation. It must report:

1. tail sampled-loss level and variability versus the exact full-field
   displacement loss;
2. cross-state correlation of loss traces under the same sampling seed;
3. ensemble shared bias versus between-seed variance;
4. displacement and strain-error concentration in the damaged and original
   active-p99 regions; and
5. the exact-BC affine field as the simplest comparator.

Minimum evidence is a convergence table, state decomposition table,
localisation table, decision figure and spatial error figure.

## Repair-selection logic

- Large sampled-loss variability or synchronised same-seed traces, together
  with shared cross-seed field bias, selects a deterministic full-field
  optimisation audit as the next smallest test.
- Small optimisation noise but shared error concentrated in the crack/process
  zone selects one preregistered local or multiscale representation test.
- Displacement recovery with persistent strain/residual failure selects one
  derivative/mechanics-aware objective test.
- If the existing outputs do not separate these alternatives, R001 is
  `INCONCLUSIVE_FOR_REPAIR_SELECTION`; no producer run is launched.

Any optimizer step, checkpoint continuation, new architecture or changed loss
requires a reviewed protocol amendment, exact-commit Code Ready review, fresh
Run ID and fresh producer roots.

## Blocked conclusions

R001 cannot establish neural-network representability, Stage 2 readiness,
native trajectory fidelity, full FEM reproduction or FEM-teacher qualification.
