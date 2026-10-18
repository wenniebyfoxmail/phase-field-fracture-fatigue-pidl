---
storyline_id: S04
experiment_id: S04-E013
protocol_revision: v1
status: completed
started_at: 2026-10-08
closed_at: 2026-10-08
primary_storyline: S04
related_storylines: [S09]
scientific_verdict:
---

# Three-Umax residual-sufficiency audit before Delta learning

## Scientific question

Can a centered rank-20 POD spatial residual basis fitted on two complete Hard-5
Umax trajectories reduce the held-out third-Umax FEM-minus-PIDL residual RMSE
by at least 10% relative to no correction, for damage, fatigue history, and raw
tensile driver, through each FEM own-first-event peak?

## Claim contract

- Claim tier / optional tag: `T2 synthetic science / residual`.
- Estimand and comparison class: same-Umax, same-physical-cycle peak fields on
  the identical 86,408-cell FEM grid; C1 through FEM own-first-event inclusive.
- Claim if primary gate passes: the specified centered rank-20 POD bases provide
  a practically meaningful oracle-reduction ceiling and justify a separate
  offline coefficient-prediction Experiment.
- Claim if primary gate fails: this specified centered rank-20 POD construction
  does not meet the frozen practical-reduction target in every fold/channel;
  this does not rule out other ranks, bases, losses, or Delta networks.
- Blocked conclusion regardless of outcome: FEM physical truth, real-road
  validity, a successful neural corrector, online PIDL coupling, or improved
  independent PINN physics.

## Reuse decision

- Searched: direct field-supervision, graph-residual discriminators, S09 native-
  Q4 data-first GNO, process-zone metrics, and the existing Hard-5 operator
  dataset builder.
- Reused: frozen FEM trajectories/graph, verified PIDL peak trajectories,
  FEM area/centroid grid, log floor `1e-12`, complete-Umax holdout, and FEM-p99
  active-support definitions. For raw log-driver, oracle coefficients are fitted
  with the same cycle-specific FEM-p99 mask and area weights used by its primary
  RMSE; damage/history use the whole-domain area-weighted projection.
- New code justification: no existing runner performs the required paired
  three-Umax residual sensitivity plus training-Umax-only POD ceiling audit.

## Frozen protocol

- Evidence identity: exact files and SHA-256 values in `input_lock.json`.
- Comparator: zero correction, `Delta=0`.
- Necessary validity gates:
  1. hashes, physics family, cycle ranges, peak semantics, element count, FEM
     centroid/area identity, and finite arrays pass;
  2. C0 is absent; raw PIDL peak step is `5N-1`;
  3. at the three locked near-event spot states, replacing the Taobo export by
     the locked Mac reference changes each primary residual RMSE and rank-20
     oracle error ratio by at most 1%, does not change the residual-RMSE Umax
     ordering, and does not move the ratio across the primary threshold. This
     spot gate does not validate unobserved cycle-wise export stability.
- Primary criterion: for every one of the 3 complete-Umax holdout folds and all
  3 primary channels, the upper endpoint of a deterministic 95% moving-block
  bootstrap interval for the median per-cycle rank-20 oracle-POD error ratio is
  `< 0.90`. Ratio = corrected residual RMSE / zero-correction residual RMSE.
  Damage and history use FEM-area-weighted whole-domain RMSE; raw log-driver
  uses FEM-area-weighted RMSE inside that cycle's FEM active-driver p99 support.
  Fewer than 20 finite cycle ratios makes the primary criterion unidentified.
- Threshold rationale: `<0.90` requires at least a 10% median RMSE reduction at
  the conservative interval endpoint, avoiding a merely numerical improvement.
  Rank 20 is an exploratory capacity cap informed by, but not scientifically
  equivalent to, the prior K=20 supervision scale. The 1% spot-replay budget is
  a frozen engineering sensitivity limit, not a field-error equivalence claim.
- Minimal fatal-regression guards: none; this is a representation ceiling, not
  a deployed correction.
- Explanatory diagnostics that cannot change the verdict: cycle-bin residual
  magnitude, q={0.95,0.99,0.995} active-support IoU/area ratio, cross-Umax
  landmark correlation, fatigue-factor consistency, singular-value spectra,
  and selected residual maps.
- Stop rule: stop as inadmissible on any identity/semantic/runtime-sensitivity
  validity failure.  Otherwise stop after rank-20 POD analysis; no neural
  training or PIDL feedback is authorised in this Experiment.
- Minimum required evidence: input-validation JSON, runtime-sensitivity CSV,
  per-cycle metrics, POD holdout table and primary summary, figures with
  `README_analysis.md`, and a decision note.

### Conditional fields

- State capability / teacher or reference qualification: processed GRIPHFiTH
  Hard-5 peak archive is an imitation comparator only; its manifest explicitly
  says `teacher_qualified=false` and `physical_validation=false`. FEM damage is
  processed/clipped to [0,1], while PIDL damage is retained as exported and can
  be slightly out of bounds. FEM active driver is derived here as
  `(1-damage_clipped)^2 * 10^log10_raw`; it is not a validated native history-
  update driver.
- Holdout unit / leakage firewall / independence axis: leave one entire Umax
  trajectory out; all centering, spatial basis fitting, and singular vectors use
  the other two trajectories only.  Test residuals are used only to obtain
  oracle projection coefficients, so the result is a compressibility ceiling,
  not predictive generalization.
- Uncertainty: deterministic non-circular moving-block bootstrap over the intact
  cycle sequence, block length 5, 2,000 replicates, seed 20261008. The reported
  endpoint is the 97.5th percentile (upper endpoint of a two-sided 95% interval).
  Any non-finite cycle value or fewer than 20 cycles yields `inconclusive` rather
  than failure. This is a conditional dependence-aware diagnostic for one
  non-stationary trajectory, not population-level uncertainty.

### Frozen outcome map

```text
validity fails                         -> inadmissible
validity passes + all 9 clauses pass   -> supports specified POD construction
validity passes + any identified clause fails -> negative for specified construction only
primary cannot be computed             -> inconclusive
```

## Producer and Run readiness

- Authorised producer: Mac-PIDL local analysis only; no training loop.
- Runner: `SENS_tensile/analyze_three_umax_residual_sufficiency.py`.
- Claim-bearing output: `local_archive/experiments/S04-E013/runs/S04-E013-R002/analysis/`.
- Ownership constraints: read-only access to frozen FEM/PIDL assets; no remote
  solve, no model fitting beyond diagnostic POD, no shared-process action.

## Code review

- Reviewer task: independent design/code review bound to v1, input lock, runner,
  and runner SHA.
- Round 1-3: FAIL with required numerical, metric-alignment, uncertainty, claim-
  boundary, and status-propagation fixes; all were addressed before execution.
- Round 4 verdict: `PASS — Code Ready`.
- Reviewed runner SHA-256:
  `c3b3e69f8d5d4593f45b31337452224faf7e23098f3b726707afd8e1d7305b97`.
- Tests: `10 passed` in `tests/test_three_umax_residual_sufficiency.py`.
- Post-R001 numerical-warning repair review: `PASS — Code Ready` for R002;
  long-vector `matmul` was replaced by mathematically equivalent explicit
  `einsum`, without changing inputs, thresholds, metrics, or outcome map.
- R002 reviewed runner SHA-256:
  `64d608fe50a07573846d9eef159b4e7db34c36892fbde8c53548455993f3fc68`;
  `11 passed` including an 86,408-cell strict floating-point regression.
- Independent result review: `PASS — Evidence Ready`; all 4,752 POD rows,
  nine primary summaries, hashes, sensitivity gates, and figures were checked.

## Runs

| Run ID | Purpose | Execution | Retrieval | Receipt |
|---|---|---|---|---|
| S04-E013-R001 | diagnostic run; numerical warnings | succeeded with warnings | local | non-claim-bearing |
| S04-E013-R002 | warning-strict no-training residual/POD audit | succeeded | verified | `RUN_RECEIPT.md` |

## Scientific verdict

**Negative for the specified centered rank-20 POD construction.** The warning-
strict R002 run passed all identity and runtime-sensitivity gates. Eight of nine
primary clauses passed. The only failure was held-out `hard5_u012` raw log10
driver: median oracle error ratio `0.9603838364`, two-sided 95% moving-block
bootstrap upper endpoint `1.1123062800`, versus the frozen `<0.90` criterion.

Damage and history passed in all three Umax folds, so the next bounded experiment
may preserve those representation findings and isolate raw-driver mechanism
diagnostics. This result neither proves coefficient predictability nor rules out
other Delta-network, basis, rank, or loss designs.
