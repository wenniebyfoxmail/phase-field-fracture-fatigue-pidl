---
name: pidl-run-analysis-workflow
description: Run or analyse a strict-alignment or claim-bearing PIDL/FEM case when it needs a complete state-mapped evidence package. Ordinary PIDL runs use the research core, relevant adapter, producer protocol, compact receipt, and fast result snapshot instead.
---

# PIDL Run Analysis Workflow

## Core Rule

Classify a PIDL execution at launch as a **strict package** only when it is
governed by a frozen strict-alignment or claim-bearing protocol, or the user
explicitly requests a complete evidence package. All other executions are
**ordinary runs**.

Every actual producer execution still needs a fresh Run ID and compact receipt:
purpose/next decision, code identity and dirty state, remote run/archive/log
paths, command, GPU/job/PID, start time, and retrieval status/route. Keep
execution status, retrieval status, and scientific verdict separate. Monitoring
is read-only; SSH loss is visibility loss, not a stop or result.

Only a strict package requires the full local case folder, complete diagnostic
export set, local archive/workspace copy, data-capability record, full analysis
figures/tables/README/decision, and durable asset endpoint below. An ordinary
run retains attributable raw/log output at its producer/archive location and,
when it yields a reported computed/measured result, produces the core's one
decision-facing visual, short interpretation, and result pointer. A frozen
protocol is never downgraded by this classification.

For strict alignment packages, compare FEM and PIDL by state label, not raw
cycle number. FEM often starts at `cycle 1`; PIDL may store `step/cycle 0`.
Use explicit state names such as
`state0_initial_unloaded_prehistory`, `c1_peak`, and `c1_unloaded`.

First classify the loading protocol and saved-state cadence. The mapping is
schedule dependent:

- one-step or one saved state per cycle: use `FEM cycle c -> PIDL saved index
  j = c - 1` only when the FEM state and PIDL saved state represent the same
  cycle stage;
- retained five-substep loading: use explicit substep labels and do not collapse
  peak and unloaded states into one cycle index.

For one-step or one-state-per-cycle archives:

```text
FEM cycle c -> PIDL saved index j = c - 1
```

This is valid only when saved-state timing is verified, for example both states
represent the same post-solve or post-history-refresh point. It does not create
separate peak and unloaded comparisons unless those states were exported.

For five-substep retained loading:

```text
cN_peak     -> PIDL step 5*(N-1)+3
cN_unloaded -> PIDL step 5*(N-1)+4
```

Full five-substep mapping for physical cycle `c`:

```text
PIDL global step = 5*(c-1)+0 -> FEM cycle c, substep 1, load 0.25
PIDL global step = 5*(c-1)+1 -> FEM cycle c, substep 2, load 0.50
PIDL global step = 5*(c-1)+2 -> FEM cycle c, substep 3, load 0.75
PIDL global step = 5*(c-1)+3 -> FEM cycle c, substep 4, load 1.00 / peak
PIDL global step = 5*(c-1)+4 -> FEM cycle c, substep 5, unload
```

Do not use an oracle that blindly assumes the raw PIDL loop index equals the FEM
cycle across different schedules. For intermediate substeps, a load-scaled
elastic oracle may use:

```text
strain, displacement, stress ~ load_factor
psi, elastic energy, active energy driver ~ load_factor^2
```

This scaling is only a linear-elastic/displacement approximation for mechanics
and energy-like fields. Do not blindly scale damage, history/fatigue
accumulation, fatigue factor, or already-updated irreversible fields; those need
actual FEM substep exports or an explicit `elastic_oracle_approximation` label.

For Alignment check 2 cyclic `s0.25-0.5-0.75-1-0` runs, FEM and PIDL counters
are intentionally offset:

```text
FEM state label                      PIDL diagnostic export
state0_initial_unloaded_prehistory   no default PIDL step; verify explicitly
c1_peak:      cycle 1 substep 4      step 3
c1_unloaded:  cycle 1 substep 5      step 4
c69_peak:     cycle 69 substep 4     step 343
c69_unloaded: cycle 69 substep 5     step 344
```

Never map `c1_peak` to PIDL step 4 for this schedule: PIDL step 4 is the
first-cycle unloaded state.

Do not assume PIDL `step 0` is `state0_initial_unloaded_prehistory`.
For five-substep runs that start with load factor `0.25`, PIDL `step 0` is
already a loaded state. If a true unloaded prehistory export is missing, mark
`state0` as unavailable and audit PIDL `step 0` separately.

## Case Folder

For a strict package, create local case folders under `local_archive/`, not inside the GitHub-synced
`upload code/` repository. For current strict-alignment PIDL work, default to:

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/pidl_result/<case_id>/
```

For FEM handoff packages, default to:

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/<package_id>/
```

For legacy/pre-strict diagnostic PIDL outputs, default to:

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/before_strict_setting_alignment/pidl_result/<case_id>/
```

Use a symlink at the old path only when older scripts, notebooks, or handover
notes still expect it. Do not put bulky raw archives under `upload code/result`,
`upload code/experiment`, `upload code/fem_result`, or `SENS_tensile/hl_*`
except as compatibility symlinks.

The case folder should follow this shape:

```text
local_archive/.../<case_id>/
  00_intent.md
  01_monitor.md
  02_download_verification.md
  03_data_capability.md
  raw_archive/ or archive/
  logs/
  run_workspace/
  analysis/
    figures/
    tables/
    README_analysis.md
    comparison_manifest.json
    decision.md
```

If the folder is created after a finished run, mark intent/provenance as
`retrospective` rather than pretending it was launch-time evidence.

For an ordinary run, use the compact receipt and owner note instead. Verify that
the output/archive remains locatable, preserve the exact evaluated output needed
for the fixed benchmark or result snapshot, and record missing evidence rather
than inferring it.

## Launch-Time Intent

For a strict package, record:

- purpose and hypothesis,
- central intervention/configuration changes and comparator; use a one-factor
  change only when it identifies the live uncertainty,
- expected pass/fail gate,
- FEM reference and state mapping,
- branch, commit, sync mode, runner, command, GPU, PID placeholder,
- required diagnostic exports.
- a credible attainable range for the primary criterion, based on baseline,
  reference uncertainty and any available oracle/replay ceiling;
- component milestones that will select a repair if the primary claim misses.

For alignment-track PIDL runs, require these exports unless the user explicitly
accepts a reduced diagnostic:

```text
alpha, alpha_bar/hist_fat, f_fatigue, g(alpha)
psi_raw, psi_active, history_driver
E_el, E_d, E_hist
grad_E_el, grad_E_d, grad_E_hist measured pre-history-refresh
eps_xx, eps_yy, eps_xy, eps_eq
sigma_raw_*, sigma_effective_*
state0 plus c1/c2/c3/c20/c40/c60/c69 peak/unload states
```

For retrospective runs, do not infer missing fields silently. If strain/stress,
gradient balance, or true state0 exports are absent, write that into
`03_data_capability.md`, make only the figures supported by available data, and
state the limitation in `decision.md`.

## Taobo Discipline

Use Mac for code edits, analysis, and git. Use Taobo/CSD3/Windows for PIDL
training. Use fresh remote directories and detached jobs. Always record:

```text
run_id, commit, branch, sync mode
remote code dir, archive root
gpu, pid, command, log, launch time
```

Do not kill shared-account processes unless cwd, cmdline, and elapsed time prove
the process is yours.

## Monitoring

Monitoring is read-only. For a strict package append status snapshots to
`01_monitor.md`:

- `ps -p <PID> -o pid,etime,stat,cmd`
- `tail -40 <log>`
- selected final lines once stopped,
- fracture/event cycle, final checkpoint, final alpha/f/Kt if available.

SSH failure means visibility loss only; do not assume the job stopped.
For an ordinary run, retain the same checks in its compact receipt or owner
note; do not create a case folder merely to hold routine monitoring.

## Download And Verification

For a strict package, after completion download archive, logs, and the run workspace/code provenance
directly into the relevant `local_archive/` case folder. Then write
`02_download_verification.md` with:

- local paths,
- total size and file count,
- final checkpoint/model found,
- final element diagnostics found,
- log tail confirms normal stop or failure,
- missing artifacts explicitly listed.

## Data Capability

For a strict package, write `03_data_capability.md` before analysis. State
whether the archive contains:

- state-timing fields,
- strain/stress fields,
- gradient diagnostics,
- alpha snapshots,
- scalar histories,
- element diagnostics,
- final checkpoint.

If a field is missing, do not infer it silently. Mark the corresponding figures
as unavailable or regenerate only if post-hoc reconstruction is valid.

## Analysis Package

For a strict package, generate only analyses and figures required by the frozen
protocol, limited to available data; do not add a data collection, execution,
comparator, criterion, review, or test. Within that scope, use the strongest
analysis supported by the data:

1. Initial alignment: `state0_initial_unloaded_prehistory`.
2. Early timing: c1/c2/c3 peak and unloaded states.
3. Mechanism cycles: c20/c40/c60/c69 and near event.
4. Energies: `E_el`, `E_d`, `E_hist`, plus incremental `Delta E_d` when relevant.
5. Fields: alpha, alpha_bar/history, f, g(alpha), psi_raw, psi_active, history driver.
6. Mechanics: strain and raw/effective stress residuals when exported.
7. Gradient balance: `grad_E_el`, `grad_E_d`, `grad_E_hist`.
8. Purpose-specific gate tied to `00_intent.md`.

For a strict or claim-bearing figure set, pair figures with CSV tables and a
short README interpretation. For an ordinary reported result, the core's one
decision visual and two-to-three-line explanation suffice. At minimum, define
each scalar reduction in the table/README:
`max`, `mean`, `p99`, `p999`, integrated energy, residual field
`PIDL - FEM`, and any near-tip or overlap metric. Record whether PIDL fields
were evaluated directly, interpolated, or area-averaged onto the FEM mesh.

For Alignment check 2 five-substep PIDL archives with local `raw_archive/`, use
the reusable skill script rather than generating case-local analysis code:

```bash
python /Users/wenxiaofang/.codex/skills/pidl-run-analysis-workflow/scripts/regenerate_alignment_analysis.py \
  --case "/path/to/Alignment check 2/PIDL cyclic 012/cases/<case_id>" \
  --run-purpose "Purpose text for decision.md"
```

The script regenerates:

```text
analysis/figures/pidl_scalar_histories.{png,pdf}
analysis/figures/pidl_gradient_balance.{png,pdf}
analysis/figures/pidl_selected_field_montage.{png,pdf}
analysis/figures/residual_fields_damage_history_degradation_peak_states.{png,pdf}
analysis/figures/residual_fields_energy_drivers_peak_states.{png,pdf}
analysis/figures/residual_fields_strain_stress_peak_states.{png,pdf}
analysis/figures/fem_pidl_state_mapped_peak_residuals.{png,pdf}
analysis/figures/c1_fatigue_driver_mask_audit.{png,pdf}
analysis/tables/data_availability.csv
analysis/tables/crack_tip_comparison.csv
analysis/tables/energy_accounting_matched_states.csv
analysis/tables/figure_table_manifest.csv
analysis/tables/precrack_line_region_audit.csv
analysis/tables/*.csv and *.json
analysis/README_analysis.md
analysis/README_state_mapping_audit.md
analysis/case_evidence_summary.md
analysis/decision.md
analysis/comparison_manifest.json
```

For FEM/PIDL residual figures, follow the style of
`Alignment check 2/comparisons/latest_align_state_field_comparison_20260608`:
shift PIDL element centroids into the FEM frame, area-average the two PIDL
triangles associated with each FEM quadrilateral, and plot grouped
`FEM | PIDL | PIDL-FEM` panels on the FEM element grid. Avoid PIDL-point scatter
residual maps for standard case records unless explicitly requested as a
debugging view.

For precrack/fatigue-mask audits, keep the real FEM reference and any
mask-applied oracle separate. Do not silently replace FEM fields with a masked
FEM field to make PIDL look aligned. Report at least:

```text
actual FEM vs PIDL on the FEM grid
left precrack line band: x <= 0.5 and |y - 0.5| <= 0.014
tip-x0 band: |x - 0.5| <= 0.02, when the run tag uses x0/hw mask parameters
fatigue factor f separately from history/active-driver fields
```

If a masked-FEM reference is useful, label it explicitly as a
`masked_FEM_counterfactual_oracle`, not as the FEM truth.

The script does not write a copy of itself into the case folder. If rerunning to
avoid stale evidence, delete the case `analysis/` outputs first while preserving
`raw_archive/`, `logs/`, `run_workspace/`, and the provenance notes.

## Decision

End every strict package with `analysis/decision.md`:

```text
Claim verdict: supports / mixed / negative / inconclusive / inadmissible
Research disposition: advance / repair / redirect / stop
Purpose:
Gate:
What improved:
What worsened:
Component progress:
Binding bottleneck and evidence:
Chosen repair or next decision-scale test and expected observable:
What is still missing:
Next action:
```

Do not judge a run by `N_f` alone. For FEM/PIDL alignment, the gate must include
field shape, alpha_bar/history, active driver, incremental energy, and timing.
Do not use a primary miss as the final paragraph when the evidence identifies a
repairable bottleneck. Keep the claim verdict unchanged, then implement or
recommend one bounded repair that directly targets the bottleneck, subject to
the approved task authority. Stop only when the route is inadmissible, its
attainable ceiling is inadequate, no meaningful lever remains, or the declared
budget is exhausted.

## Asset Endpoint

Before closing a strict package, decide what its durable asset is:

- `docs/` summary: use for compact, shared conclusions, small CSV/JSON tables,
  manifests, and claims that should travel with Git.
- local archive README: use for bulky generated payloads, checkpoints, raw
  fields, rendered figures, sync packages, and diagnostic runs that should stay
  local-only.

Do not leave a strict package as only a raw folder. Its endpoint must state:

```text
Purpose:
Settings / central intervention:
Producer machine:
Branch and commit:
Raw result location:
Linked summary or manifest:
Credibility: canonical / supporting / diagnostic / negative / inconclusive
Limitations:
Next action:
```

Keep generated payloads out of Git by default. Track the explanation and the
pointer, not the heavy result bytes.

For strict-package local Mac workflows, the raw-payload endpoint should normally
be under:

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/
```

Use the `before_strict_setting_alignment/` or `after_strict_setting_alignment/`
split first, then `pidl_result/` or `fem/`, then the experiment/case name.
