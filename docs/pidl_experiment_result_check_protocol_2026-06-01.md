# PIDL Experiment Result-Check Protocol

This is the fixed checklist for judging each PIDL experiment.  It is meant to
avoid the old trap of judging by `N_f` or one scalar field max alone.

## 1. Run Health And Provenance

Record before interpretation:

- git commit, branch/workspace, runner, command, GPU, PID/log path, archive path
- mesh file, FEM reference folder, FEM cycle mapping, seed, `Umax`, `N`, confirm cycles
- enabled interventions only: architecture, sampling, history driver, supervision, staging, patch, discontinuity
- whether pretraining was default, short, or off
- whether state-timing and gradient-balance exports are present

If a run failed before the first post-fit state, classify it as an execution
failure, not a physics result.

## 2. Early State And Timing Alignment

The user's proposed check is correct and should be mandatory.  Compare the
initial state and the first few states/cycles before any final judgement.

Required states when available:

- initial/pre-fit state
- c1/c2/c3 post-fit before history refresh
- c1/c2/c3 post-history refresh
- selected later cycles such as c10/c20/c40/c69/c80 depending on run length

Required fields:

- `alpha` / `d`
- `hist_alpha`
- `alpha_bar` / `hist_fat`
- `f_fatigue`
- `psi_raw`
- `psi_active = g(alpha) * psi_raw`

Main questions:

- Is the initial precrack profile aligned?
- Is `alpha_bar=0` and `f=1` initially when the benchmark expects soft-hist0?
- Does the c1 comparison use the same timing, not a mixed peak/end-cycle row?
- Does the gap appear before history refresh, after history refresh, or only after several cycles?

## 3. Field-Level FEM/PIDL Comparison

Use common-probe or clearly documented interpolation.  Do not compare FEM
element max against PIDL node/triangle max without labelling the reduction.

Required field metrics:

- max, p99, p999, mean, near-tip integral, and crack-corridor integral
- crack-tip position
- process-zone width and y-span at thresholds such as `alpha>0.5` and `alpha>0.95`
- right-boundary `alpha_max` and count of boundary nodes/elements over event threshold
- residual field visual: `PIDL - FEM`, ideally for `alpha`, `alpha_bar`, `f_fatigue`, `psi_raw`, and `psi_active`

Interpretation rule:

- A good result should improve field shape, width, position, and active-driver
  trajectory, not merely reach the right boundary at a convenient cycle.
- A thin band reaching the boundary is not automatically a FEM-like crack.

## 4. Energy And Incremental Energy

Report absolute and incremental values separately:

- `E_el`
- `E_d`
- `E_hist`
- `E_total`
- `Delta E_d = E_d(c) - E_d(initial or c1 reference)`
- if available, `Delta E_el` and `Delta E_hist`

Use incremental damage energy when the initial precrack convention pollutes
absolute `E_d`.  Compare the energy trajectory cycle by cycle, especially
c1/c2/c3/c10/c20 and near FEM fracture.

## 5. Gradient And Loss-Balance Check

The user's second proposed check is also mandatory.  Compare gradients for the
actual loss combination, not only raw scalar energies.

Required gradient rows:

- `logE_el`, `logE_d`, `logE_hist`, `logE_total`
- contribution-to-total gradients: `contribE_el`, `contribE_d`, `contribE_hist`
- all parameters, `trunk_shared`, `uv_head`, and `alpha_head` where available
- supervised/auxiliary loss gradient if a run adds FEM supervision, symmetry,
  side traction, patch loss, or staged heads

Timing caution:

- If the gradient probe is after `hist_alpha` refresh, `E_hist` may look zero
  because the irreversibility active set is empty.  Use the pre-refresh probe
  to judge whether irreversibility is balanced during optimisation.

Interpretation rule:

- If `uv_head` gradients are tiny while `alpha_head` dominates, the run may be
  evolving damage without enough elastic relaxation.
- If `E_hist` gradients dominate only at the wrong hook, do not overclaim a
  loss-balance problem.

## 6. Event And Trajectory Check

Record:

- first right-boundary hit cycle
- confirmed stop cycle
- final cycle if no fracture
- event variable used by the detector
- `alpha_bar_max`, but never treat it as the boundary event variable
- `Kt`, crack-tip coordinate, boundary `alpha_max`, and boundary count

Interpretation rule:

- Similar `N_f` is not enough.  It can be life-matching but field-divergent.
- `alpha_bar_max` can be large while boundary `alpha` is still low; these are
  different parts of the mechanism.

## 7. Method-Specific Diagnostics

Add these when relevant:

- local patch: `corr/total`, `tip_grad/global`, local-vs-global field maps
- staged/split-trunk: stage-wise gradient balance and branch/head movement
- discontinuity/jump head: jump amplitude, localization near the crack ribbon,
  and whether raw/active `psi` moves toward FEM
- FBPINN/domain-decomposed: per-subdomain field continuity and whether the
  decomposition slows or improves propagation
- supervised-field runs: supervised target loss, target field stats at c1/c20,
  and whether non-supervised fields improve or deteriorate

## 8. Verdict Labels

Use one of these labels:

- `execution_failed`: did not run far enough to judge physics
- `alignment_failed`: settings/timing/field definitions are not comparable
- `negative`: clean run, but field/energy/gradient evidence does not improve
- `life_matching_field_divergent`: `N_f` improves but mechanism remains wrong
- `mechanism_promising`: field shape, energy trajectory, and gradients move
  toward FEM even if `N_f` is not perfect
- `needs_ablation`: combined method works enough that one-factor ablations are
  worth running

## Minimum Report Table

For each experiment, produce one row with:

```text
run_id, commit, runner, intervention, mesh, pretrain_mode,
first_hit, stop_cycle,
c1 alpha_max, c1 alpha_bar_max, c1 psi_raw_max, c1 psi_active_max,
c20 alpha_max, c20 alpha_bar_max, c20 psi_raw_max, c20 psi_active_max,
selected E_el/E_d/E_hist/Delta_E_d,
gradient verdict,
field-shape verdict,
overall verdict
```

For longer runs, add c40/c69/c80 or cycle-matched FEM-fracture rows.
