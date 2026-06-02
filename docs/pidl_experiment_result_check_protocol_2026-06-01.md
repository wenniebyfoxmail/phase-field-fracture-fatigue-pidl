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

## 2. Experiment Artifact Folder

Each experiment must have one dedicated result folder before interpretation.
This keeps data sync, analysis, figures, and verdicts together instead of
scattering them across logs, chat, and temporary paths.

Recommended folder pattern:

```text
_analysis_fem_mechanism_20260528/experiments/<run_id>/
```

where `<run_id>` should be stable and descriptive, for example:

```text
field_supervision_alpha_fixedtiming_90dd3ad
split_trunk_uv_alpha_c1e8ac9
row_head_staged_730101a
```

Required contents:

```text
0_sync/
1_analysis/
2_figures/
```

### `0_sync/` Download Or Sync Data

Purpose: keep enough raw or mirrored data to reproduce the analysis without
depending on memory of a Taobo path.

Include when practical:

- copied/synced log files
- `model_settings.txt`
- state-timing CSV and selected `.npz` files
- gradient-balance CSV
- scalar arrays such as `alpha_bar_vs_cycle.npy`, `x_tip_vs_cycle.npy`,
  `E_el_vs_cycle.npy`
- FEM reference metadata or a text file containing the FEM reference path
- a `SYNC_SOURCES.md` file listing every remote/local source path and sync time

Large files can remain remote, but the source path must be recorded.  If a file
is too large to sync, write that explicitly in `SYNC_SOURCES.md`.

### `1_analysis/` Necessary Data Analysis MD

Purpose: the experiment's interpretation lives here, not only in chat.

Required file:

```text
result_check.md
```

It should contain:

- artifact completeness and evidence maturity
- run health/provenance
- setting alignment audit
- early state/timing check
- field-level FEM/PIDL comparison
- energy and incremental energy comparison
- gradient/loss-balance check
- event and trajectory check
- method-specific diagnostics
- interpretation in plain English
- verdict label from this protocol
- links to figures and metrics CSVs in `2_figures/`

Use this template at the top of `result_check.md`:

```text
# Result Check: <run_id>

## Artifact Completeness

| gate | status | evidence path | note |
|---|---|---|---|
| sync/provenance | complete / partial / missing | 0_sync/... | ... |
| early state timing | complete / partial / missing | 2_figures/... | ... |
| FEM-reference residual fields | complete / partial / missing | 2_figures/... | ... |
| cyclewise mechanism trajectory | complete / partial / missing | 2_figures/... | ... |
| energy/incremental energy | complete / partial / missing | 2_figures/... | ... |
| gradient/loss balance | complete / partial / missing | 2_figures/... | ... |
| method-specific diagnostics | complete / partial / not-applicable | 2_figures/... | ... |

Evidence maturity: complete / retrospective-partial / provisional / failed

## Verdict

State the verdict only after the completeness table.  If any required gate is
missing, mark the verdict as provisional or retrospective-partial.
```

For method families, add a comparison note such as:

```text
family_comparison.md
```

when comparing baseline, current variant, and previous best variant.

### `2_figures/` Figures And Metrics

Purpose: all evidence figures and their metric CSVs live together.

Required when data is available:

- state-timing alignment strip
- FEM-reference residual montage, full-domain
- FEM-reference residual montage, near-tip crop
- cyclewise mechanism trajectory figure
- energy and incremental-energy trajectory figure
- gradient/loss-balance figure
- experiment-family comparison figure
- one CSV per figure or a shared `metrics.csv`

Every figure filename should include the run id, compared reference, and cycle
set when relevant, for example:

```text
alpha_supervise_vs_fem_nstep10_neartip_c1_c2_c3_c10.png
split_trunk_vs_row_head_gradient_balance_c0_c1_c20_c80.png
```

Keep PNG for quick viewing and PDF for paper-quality line/vector figures when
reasonable.

### Minimum Folder Audit

Before giving a final verdict on an experiment, check:

```text
0_sync/SYNC_SOURCES.md exists
1_analysis/result_check.md exists
2_figures/ contains at least the figures needed for the verdict
```

If the folder is incomplete, state which part is missing and classify the
result as provisional or retrospective-partial.  A retrospective-partial report
is acceptable for old runs that lack state-timing or gradient exports, but it
must not be presented as a full protocol pass.

## 3. Early State And Timing Alignment

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

## 4. Field-Level FEM/PIDL Comparison

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

## 5. Energy And Incremental Energy

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

## 6. Gradient And Loss-Balance Check

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

## 7. Event And Trajectory Check

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

## 8. Method-Specific Diagnostics

Add these when relevant:

- local patch: `corr/total`, `tip_grad/global`, local-vs-global field maps
- staged/split-trunk: stage-wise gradient balance and branch/head movement
- discontinuity/jump head: jump amplitude, localization near the crack ribbon,
  and whether raw/active `psi` moves toward FEM
- FBPINN/domain-decomposed: per-subdomain field continuity and whether the
  decomposition slows or improves propagation
- supervised-field runs: supervised target loss, target field stats at c1/c20,
  and whether non-supervised fields improve or deteriorate

## 9. Figure Protocol

Every serious experiment should produce a small, repeatable evidence package.
Do not make a single "pretty field plot" and then infer the mechanism from it.
The figures should make FEM the explicit reference and should separate timing,
field shape, energy, and gradient evidence.

### Required Figure Set

1. **State-timing alignment strip**

   Purpose: locate when the first gap appears.

   Required panels:

   ```text
   initial/pre-fit
   c1 post-fit pre-history-refresh
   c1 post-history-refresh
   c2 post-fit pre-history-refresh
   c2 post-history-refresh
   c3 post-fit pre-history-refresh
   c3 post-history-refresh
   ```

   Required fields:

   ```text
   alpha or d
   alpha_bar or hist_fat
   f_fatigue
   psi_raw
   psi_active = g(alpha) * psi_raw
   ```

   Use this figure before any final interpretation.  If the initial state or c1
   timing is not aligned, later cycle differences are not yet a physics result.

2. **FEM-reference residual montage**

   Purpose: show field mismatch directly.

   Layout:

   ```text
   column 1: FEM REFERENCE
   column 2: PIDL / variant
   column 3: residual
   ```

   The first column title must include `FEM REFERENCE`.  Residual definitions:

   ```text
   alpha, alpha_bar, f_fatigue: PIDL - FEM
   psi_raw, psi_active: log10((PIDL + eps) / (FEM + eps))
   ```

   Required cycles:

   ```text
   c1, c2, c3, c10
   plus c20/c40/c69/c80 when available
   plus matched-event states when the run fractures
   ```

   Required views:

   ```text
   full domain for event/path audit
   near-tip crop for mechanism audit
   ```

   Use shared colour limits for FEM and PIDL within each row.  Use a zero-centred
   diverging colour scale for residuals.  Mark the initial crack tip `x=0` and
   the right-boundary event line when relevant.

3. **Cyclewise mechanism trajectory**

   Purpose: show whether the crack and drivers co-evolve like FEM.

   Required curves:

   ```text
   crack_tip_x
   process-zone width or y-span
   alpha_bar_max, alpha_bar_p99, alpha_bar_near_tip_integral
   psi_raw_near_tip_integral
   psi_active_near_tip_integral
   f_min and f_near_tip_mean
   right-boundary alpha_max and boundary count
   ```

   Plot FEM and PIDL on the same axes when cycle mapping is valid.  Otherwise
   label the comparison as native-cycle only.

4. **Energy and incremental-energy trajectory**

   Purpose: separate absolute precrack convention from evolving damage work.

   Required curves:

   ```text
   E_el
   E_d
   E_hist / E_irre
   E_total when available
   Delta E_d
   Delta E_el when available
   ```

   Always show absolute `E_d` and `Delta E_d` separately.  If the initial
   precrack conventions differ, do not use absolute `E_d` as the main comparison.

5. **Gradient/loss-balance figure**

   Purpose: show which physics term and which network part is moving.

   Required panels:

   ```text
   contribE_el, contribE_d, contribE_hist
   logE_el, logE_d, logE_hist
   all parameters
   uv_head or uv_branch
   alpha_head or alpha_branch
   trunk/shared parameters when available
   supervised/auxiliary loss gradient when present
   ```

   Use the pre-history-refresh probe to judge `E_hist`.  A post-refresh zero
   `E_hist` row is useful for timing audit but not for loss-balance judgement.

6. **Experiment-family comparison figure**

   Purpose: compare variants without hiding field failures behind `N_f`.

   Required rows or markers:

   ```text
   baseline strict FEM-mesh soft-hist0
   current variant
   best previous variant in the same family
   FEM reference
   ```

   Required columns:

   ```text
   first_hit / confirmed_stop
   crack_tip_x at c10/c20/c40/c69 or matched event
   alpha_bar near-tip integral ratio to FEM
   psi_active near-tip integral ratio to FEM
   Delta E_d ratio to FEM
   field-shape verdict
   ```

### Method-Specific Figure Add-Ons

- supervised-field runs: show the supervised target and at least two
  non-supervised fields.  For example, an `alpha`-supervised run must also show
  `alpha_bar`, `psi_raw`, and `psi_active`.
- staged/split-trunk runs: add a branch-gradient panel and a stage timeline.
- local patch or FBPINN runs: add local-vs-global contribution maps and
  subdomain/patch boundary continuity panels.
- discontinuity/jump runs: add the jump/ribbon amplitude map and the active
  driver near the crack ribbon.

### Figure QA Rules

- Each figure must state the run id, FEM reference, cycle mapping, and timing
  state in the caption or title.
- Full-domain figures answer "where did it go"; near-tip crops answer "is the
  mechanism FEM-like".  Use both when judging a new method.
- Do not compare different quantities in a residual panel.  If FEM exports
  peak-to-date `psi+` and PIDL exports active end-cycle `psi+`, label them as
  different timing states rather than subtracting them.
- Keep scalar and field evidence separate.  A good `N_f` plot is not evidence
  of field-level agreement.
- Record the figure path and the metrics CSV path in the result note.

## 10. Verdict Labels

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
