# Decision: road observation-aware predictor, stage 1

## Verdict

Stage 1 passes as a **tooling-only interface and legacy-transfer gate**.

The existing matched Markov graph, TCN, and diagonal SSM checkpoints can be
embedded in an observation-aware road forecasting architecture without changing
their first raw state forecast when every new road input is absent. On the real
86,408-element eta0 FEM graph, the maximum absolute transfer error is exactly
zero for the three seed-1 formal checkpoints.

This does **not** show that observations improve forecasts, that the risk heads
are calibrated, or that any model generalises to roads. Agent1 and Agent2 have
not yet frozen their observation/time interfaces, and no observation-aware
training was launched.

## Preserved scientific boundary

- Markov graph remains the formal matched control.
- TCN remains the simple temporal baseline.
- Diagonal SSM remains the candidate for conditional propagation after an
  assimilated transition state.
- Transformer is implemented only as a secondary interface candidate.
- `current_multiscale` remains a cycle-conditioned, single-seed historical
  reference and is excluded from formal ranking.
- All autonomous free rollouts still miss the c87 transition.
- FEM eta0 remains the physical numerical reference.

## Experiment gate

1. **Mechanism question**: can realistic observation, elapsed-time, traffic,
   environment, and maintenance inputs be added without silently changing the
   already-audited temporal state path?
2. **Claim changed by success/failure**: success permits observation-aware
   training to be designed; failure would invalidate warm-starting from the
   matched checkpoints.
3. **Cheaper diagnostic**: strict offline checkpoint transfer at c76 is cheaper
   than any producer training and is sufficient for stage 1.
4. **Minimal asset**: `legacy_transfer_audit.csv`, this decision note, and the
   versioned input contract.
5. **Registry path**: keep the stage quarantined in this branch until Agent1 and
   Agent2 freeze compatible specs and a producer experiment passes its own gate.

## Implemented contract

`source/road_observation_aware_operator.py` adds:

- analysed latent state `z_analysis`;
- node and global observations with explicit missingness masks;
- irregular `Delta t`;
- traffic/load, environment, and maintenance histories;
- future traffic/environment/maintenance scenarios;
- direct monotone h1--h3 state heads;
- discrete hazard and cumulative event probability;
- positive-scale RUL distribution parameters;
- a strict legacy-checkpoint transfer path;
- censor-aware discrete hazard and log-normal RUL likelihoods.

The existing `TemporalMeshOperator` remains backward compatible. Optional
node-level metadata were added with a default dimension of zero, and all prior
temporal tests continue to pass.

## Offline checkpoint audit

| family | selected context | legacy parameters | road parameters | h1 raw max error | status |
|---|---:|---:|---:|---:|---|
| Markov graph | 1 | 328,156 | 339,815 | 0 | pass |
| TCN | 20 | 326,356 | 338,015 | 0 | pass |
| diagonal SSM | 5 | 330,028 | 341,687 | 0 | pass |

The added parameters belong to observation/scenario/direct-horizon/risk paths.
Before a scientific comparison, all road-aware families must be capacity
matched again under the same new heads and training budget. The table above is
not a performance ranking.

## What is deliberately not reported

- No road field, RUL, hazard, or calibration figure is reported. The new risk
  heads are untrained; plotting their random smoke output would be misleading.
- No recursive-versus-direct result is reported. The protocol is frozen in
  `recursive_vs_direct_multi_horizon_ablation.csv`, but the required Agent1/2
  inputs are not frozen.
- No synthetic proxy is labelled as real data.
- No repeated cycle window is counted as an independent road section.

## Required next gate

Do not launch expensive training until all items exist:

1. Agent1: `road_observation_operator_spec.json` and one hash-locked
   assimilated-state package with synthetic/real/oracle provenance.
2. Agent2: `road_time_mapping_spec.json`, future scenario schema, and frozen
   observation-trigger specification.
3. At least three compatible physical trajectories for any RUL/hazard claim;
   otherwise risk outputs remain tooling-only.
4. A newly declared split supporting leave-one-trajectory/load evaluation.
5. Parameter-matched Markov/TCN/SSM budgets and identical masks/scenarios.

After those inputs freeze, the cheapest producer experiment is one seed per
formal family on the same synthetic-observation package, comparing recursive
one-step and direct h1--h3 state heads. Hazard/RUL training comes later and
requires event/censor diversity.
