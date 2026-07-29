---
name: pidl-experiment-gate
description: Gate PIDL/FEM experiments before launch and after completion. Use when proposing, dispatching, reviewing, cleaning, or registering a PIDL, FEM, surrogate, restart, diagnostic, Taobo, CSD3, Windows-PIDL, or Windows-FEM experiment so each run has a mechanism question, cheaper diagnostic check, minimal output asset, code/runtime alignment, success/failure criteria, and a path into the main result registry instead of becoming an orphan run.
---

# PIDL Experiment Gate

Use this skill to stop PIDL work from becoming a pile of plausible runs. Every
new experiment must answer one mechanism question, specify which claim changes
if it succeeds or fails, pass a cheaper-diagnostic check, declare its minimal
output asset, and register back into the project evidence map.

For complex diagnostic design, architecture/code-framework changes,
claim-changing interpretation, or threshold/mask/criterion design, ask GPT Pro
for an external plan first. Then record what was adopted, modified, or rejected
with `scripts/pidl_attempt_ledger.py`. Do not log every small edit; log one
attempt only when the outcome can change a claim, branch, or release state.

## Pre-Launch Gate

Ask exactly these five questions before approving a new run:

1. What mechanism question does this run answer?
2. If it succeeds or fails, which claim changes?
3. Is there a cheaper diagnostic that should run first?
4. What is the minimal output asset: table, figure, state export, or decision note?
5. How will it enter the main checklist after completion instead of becoming an orphan experiment?

If any answer is missing, do not launch training. Convert the idea into an
analysis-only task, a state-export request, or a short decision note.

## GPT Pro Planning Gate

Ask GPT Pro first for:

- New diagnostic design or experiment branch.
- State/provenance audit logic.
- Claim-changing result interpretation.
- Threshold, mask, criterion, or framework changes.
- Code framework that other agents or future runs will reuse.

GPT Pro is not required for typo fixes, path fixes, label edits, formatting,
rerunning unchanged deterministic scripts, or copying registry files.

After GPT Pro replies, record the local decision:

```bash
python docs/skills/pidl-experiment-gate/scripts/pidl_attempt_ledger.py new ...
python docs/skills/pidl-experiment-gate/scripts/pidl_attempt_ledger.py attach-advice ...
python docs/skills/pidl-experiment-gate/scripts/pidl_attempt_ledger.py decide ...
python docs/skills/pidl-experiment-gate/scripts/pidl_attempt_ledger.py change ...
python docs/skills/pidl-experiment-gate/scripts/pidl_attempt_ledger.py test ...
python docs/skills/pidl-experiment-gate/scripts/pidl_attempt_ledger.py close ...
python docs/skills/pidl-experiment-gate/scripts/pidl_attempt_ledger.py render ...
python docs/skills/pidl-experiment-gate/scripts/pidl_attempt_ledger.py validate ...
```

Default ledger for the current aligned PIDL/FEM comparison:

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/_pidl_attempt_ledger/attempts.jsonl
```

The ledger is an audit trail, not an execution engine. It must never launch
full PIDL/FEM production runs or auto-accept a scientific claim.

## Claim Gate

Classify the target claim before launch:

- `field-mechanism`: active-driver/process-zone, damage/history co-location, FEM/PIDL field alignment.
- `state-semantics`: state label, history timing, pre/post-refresh, FEM/PIDL field meaning.
- `trajectory-sufficiency`: whether a near-critical state can propagate if supplied.
- `framework-validation`: M2S/road-DT validation, RUL prediction, surrogate forecast reliability.
- `tooling-only`: runner, export, smoke, transfer, or code-path validation.

Do not let a `tooling-only` run support a `field-mechanism` claim. Do not let a
scalar event metric such as `N_f` or boundary hit support field closure unless
the active-driver/process-zone gate is explicitly passed.

## Cheaper Diagnostics

Prefer the cheapest diagnostic that can falsify the idea:

- Existing registry/doc check: search `docs/pidl_experiment_inventory.md`, `docs/research_frontier.md`, and relevant `docs/*discriminator*.md`.
- Offline posthoc analysis: run an analysis script against existing archives.
- State export or mapping audit: request/export only the states needed for comparison.
- C1 or one-step micro-solve: use before N100 production when the mechanism is early feedback.
- Tiny code smoke: import/unit/code-path only on Mac; no PIDL training on Mac.
- Producer run: use Taobo, CSD3, Windows-PIDL, or Windows-FEM only after the cheaper gates fail to answer the question.

## Code-Execution Alignment

Before any command that may enter a training loop:

1. Read `AGENTS.md`, `docs/git_workflow.md`, and for Taobo `docs/taobo_gpu_submission_protocol.md`.
2. Confirm producer machine: Mac-PIDL is dev/light sanity only; Taobo/CSD3/Windows-PIDL run PIDL training; Windows-FEM runs FEM.
3. Record commit SHA, branch, dirty status, runner path, command, output root, archive root, log path, PID/session, and GPU if applicable.
4. For Taobo, use attributable roots under `/mnt/data2/drtao/wennie/` and archive under `/mnt/data2/drtao/pidl_archives/...`; set `CUDA_VISIBLE_DEVICES=N`.
5. Never kill shared-machine processes without verifying `cmdline`, elapsed time, and cwd.

## Minimal Asset

Every completed run must leave one primary asset:

- `decision.md` for mechanism verdicts.
- A CSV/table for scalar or field metrics.
- A figure for visual field/process-zone comparisons.
- A state export with an index for FEM/PIDL semantic alignment.
- A short `RUN_PROVENANCE.txt` or `00_intent.md` plus `01_monitor.md` for runs still in progress.

Prefer one strong asset over dumping a full archive into the shared repo.

## Attempt Ledger Script

Use `scripts/pidl_attempt_ledger.py` when an attempt needs an auditable record
of motivation, GPT Pro advice, adopted/rejected decisions, code changes, tests,
outputs, interpretation, and next action.

Required pattern:

1. `new`: create the attempt folder and initial JSONL record.
2. `attach-advice`: attach the GPT Pro note path, hash, and summary.
3. `decide`: state the adopted decision and rationale.
4. `change`: record each meaningful code/doc change.
5. `test`: record deterministic checks and key observations.
6. `close`: accept, reject, quarantine, or supersede the attempt.
7. `render`: write a readable `attempt.md`.
8. `validate`: check required fields and required assets.

The script may validate schemas, asset existence, mapping labels, mask safety,
ratio sanity, and alpha bounds. It must not decide final paper claims, discard
baselines, or approve expensive production runs without a human/GPT Pro gate.

Use `scripts/pidl_result_package_check.py` after building a diagnostic package
that has a manifest and decision note. Current deterministic checks include:

```bash
python docs/skills/pidl-experiment-gate/scripts/pidl_result_package_check.py bounded-degradation --package <analysis-package>
python docs/skills/pidl-experiment-gate/scripts/pidl_result_package_check.py bounded-alpha-micro --package <analysis-package>
```

This check verifies required assets, versioned event-state mapping,
denominator-safe primary masks, top5 quarantine, intervention-ranking
presence, export-limit notes, and the no-production-run guard. Legacy c69/c89
labels must be treated as historical mappings rather than universal state
identifiers.

## Registry Handoff

After completion, add or update exactly one registry endpoint:

- `docs/aligned_result_registry_2026-07-06.md` for curated aligned evidence.
- `docs/pidl_experiment_inventory.md` for full audit/provenance rows.
- `docs/research_frontier.md` only when the one-screen current decision changes.
- A machine handover in `docs/handovers/` when another producer must act.

Use these status labels:

- `primary`: can support the current aligned story.
- `supporting`: useful with caveats.
- `negative`: failed attempt that narrows mechanism space.
- `diagnostic`: explains behavior but should not be cited as a main claim.
- `quarantine`: not aligned, superseded, incomplete, or unclear.
- `do-not-cite`: known bad mapping, aborted run, or misleading artifact.

## FEM-Centred Cross-Method Validation

Use this protocol whenever two PIDL representations, constitutive settings, or
training strategies are compared. FEM is always the physical reference. Formal
MLP eta0 is the control baseline, not ground truth.

### Labels And State Classes

Every table row and figure panel must include architecture, eta, graph scale or
other intervention, physical cycle, loading branch, raw step, and state label.
Write `Hybrid eta0 s=0.05 c79 event peak`, not `H005`, because the latter can be
confused with a damage threshold.

Assign every comparison to exactly one class:

- `same-cycle`: FEM and model at the same physical cycle and same substep.
- `same-cycle-pre-event`: the last common cycle before either trajectory has
  penetrated, on the same loading branch.
- `own-event`: FEM at its event versus each model at its own confirmed event.

Own-event residuals answer whether penetration occurs through the same
mechanism. They are not cycle-aligned prediction errors. Never substitute FEM
c89 when a claimed same-cycle FEM c79 state is unavailable.

The default trajectory is c20, c40, c60, last common pre-event, and each model's
own event. Add named cycles such as c79 or c89 only when their state semantics,
loading protocol, event phase, and exports are available. Use a connected
penetration criterion with a declared confirmation window, not a single noisy
boundary cell. Always retain both `first-hit` and `confirmed` labels; do not
silently substitute one for the other.

### Versioned FEM Reference

Every comparison package must name an immutable FEM reference ID and record its
loading substeps, material/model form, mesh hash, event rule, first-hit cycle,
confirmed cycle, branch/substep, and snapshot hash. A cycle number alone is not
a reference.

Current Hard5 examples are deliberately distinct:

```text
hard5_eta0_u012_8step_legacy: first-hit c86, confirmed c89
hard5_eta0_u012_5step_20260729: first-hit c83, confirmed c86
```

The legacy eight-step and current five-step trajectories may be compared as a
protocol-sensitivity study. They must not be mixed inside a claimed
same-state FEM/PIDL residual. Formal PIDL first-hit c89 should be compared to a
declared FEM first-hit state when answering an own-event mechanism question,
not automatically to FEM confirmed c89.

### Event Timing

Compute event error against the declared reference and the same event phase:

```text
Delta N_first_hit = N_first_hit(model) - N_first_hit(FEM reference)
Delta N_confirmed = N_confirmed(model) - N_confirmed(FEM reference)
```

Promotion and hard-rejection windows are benchmark-specific predeclared gates;
they must not be inherited from the legacy c89 benchmark. Passing a timing gate
never proves mechanism agreement. When loading discretization, event rule, or
confirmation semantics differ, timing is descriptive protocol sensitivity and
cannot be used as a prediction-accuracy gate.

### Field Metrics

Map every field to the same clean FEM domain and use element-area weighting.
Record direct evaluation versus interpolation/area mapping. Report:

- damage alpha: linear MAE, RMSE, and correlation;
- fatigue history alpha_bar: log10 MAE, RMSE, and correlation;
- fatigue degradation: linear MAE, RMSE, and correlation;
- raw driver: log10 MAE, RMSE, and correlation;
- active driver: log10 MAE, RMSE, and correlation.

Use one declared positive log floor across FEM and every model. Whole-domain
averages are supporting evidence only because low-value background cells can
dominate them.

### Active-Support Metrics

Compute support masks with area-weighted quantiles. An unweighted node/cell
quantile must be labelled `unweighted diagnostic` and cannot be the headline
metric when cell areas vary.

For absolute energetic support, compute the FEM area-weighted p99 threshold once
from the declared FEM snapshot and clean domain:

```text
tau_FEM = area_weighted_p99(psi_active_FEM)
A = psi_active_FEM >= tau_FEM
B = psi_active_model >= tau_FEM
IoU_absolute = area(A intersect B) / area(A union B)
R_area = area(B) / area(A)
```

Compute the FEM threshold from the exact versioned reference snapshot. The
legacy confirmed-c89 value near `5.71e-4` is not portable to a first-hit state:
active support can collapse by orders of magnitude between first hit and
confirmation. Never hard-code a threshold across event phases or loading
protocols. `IoU_absolute` combines amplitude and location. Interpret
`R_area << 1` as energetic under-support and `R_area >> 1` as over-diffusion.

For location/ranking independent of absolute amplitude:

```text
A_own = FEM area-weighted top 1 percent
B_own = model area-weighted top 1 percent
IoU_own = area(A_own intersect B_own) / area(A_own union B_own)
```

`IoU_own` does not prove that the model reaches FEM energy levels. Its support
area ratio is approximately one by construction and must not be cited as
amplitude recovery. Report p99 as headline plus a small declared threshold
sensitivity check.

### Morphology, Symmetry, And Corrections

For active support and damage, report centroid offset, forward extent, width,
connected components, crack-tip position, and damage IoU over alpha thresholds
0.25, 0.5, and 0.75. Report threshold-specific penetration cycles separately;
post-penetration whole-domain damage IoU is secondary.

At step 4, c20, c40, c60, last common pre-event, and own event, measure mirror
asymmetry for primitive mechanics, raw stress, alpha, g(alpha), alpha_bar, and
psi_active. The gate is no material amplification relative to Formal MLP eta0,
not perfect symmetry. Stop after two consecutive predeclared checkpoint failures
or a persistent one-sided support lobe.

For hybrid models, report actual raw-output correction median, p95, maximum,
saturation fraction, process-zone versus background magnitude, and graph-edge
neighbour-jump roughness. Graph scale bounds the additive raw network output; it
does not directly bound physical displacement or constrained alpha.

### Required Figure Suite

1. `event_state_map`: event cycle, comparison class, peak/unloaded state, raw
   step, and checkpoint provenance.
2. `active_driver_fields`: columns are FEM then every method; rows are common
   scale `log10(psi_active)`, common FEM-p99 highlight, and each own top-1%
   highlight. Keep axes and color limits common.
3. `active_support_overlap`: two rows per method, common FEM-p99 and own-top1%.
   Use blue for FEM-only, orange for model-only, yellow for overlap, and grey for
   neither. Print IoU and absolute `R_area` on the common-threshold panel.
4. `fem_residual_decomposition`: for alpha, history, raw driver, and active
   driver show FEM, prediction, and prediction minus FEM. Use linear alpha
   residual and signed log residual for positive driver/history fields.
5. `same_cycle_trajectory`: c20, c40, c60, and last common pre-event, with FEM
   at each same-cycle state, crack tip, active-support contour, and symmetry.
6. `own_event_mechanism`: FEM event against every model's own event, explicitly
   labelled `own-event`, never `same-state accuracy`.
7. `hybrid_correction_diagnostics`: per-channel correction distributions,
   saturation, spatial support, and neighbour-jump roughness.

All field figures must put FEM first. Continuous cloud maps alone are
insufficient: each active-driver claim needs both absolute and own-top1% masks.

### Promotion Rule

A candidate replaces Formal MLP eta0 only if all conditions pass:

1. event timing passes the declared promotion window;
2. damage and history improve against same-state FEM;
3. active-driver log residual and correlation improve;
4. absolute-support IoU improves and is at least 0.10;
5. own-top1% IoU improves;
6. absolute support-area ratio lies in [0.5, 2.0];
7. history/degradation are no more than 10 percent worse than the control;
8. no persistent symmetry amplification occurs;
9. improvement is present along the trajectory, not only in final damage;
10. runtime, convergence, and archive completeness pass declared limits.

Any numerical log-MAE or correlation cutoffs must be stored with the versioned
benchmark lock. Legacy thresholds such as active-driver log-MAE at most 2.5 and
correlation at least 0.20 are not universal fracture constants and cannot be
silently applied to a new FEM protocol or event phase. A model that improves
damage but fails energetic support remains a representation diagnostic, not a
promoted baseline.

## Output Template

When using this skill, produce a short gate note:

```markdown
## PIDL Experiment Gate

- Mechanism question:
- Claim changed if success:
- Claim changed if failure:
- Cheaper diagnostic first:
- Minimal output asset:
- Code/producer alignment:
- Success criteria:
- Failure criteria:
- Registry destination:
- Decision: launch / diagnose first / reject / quarantine
```
