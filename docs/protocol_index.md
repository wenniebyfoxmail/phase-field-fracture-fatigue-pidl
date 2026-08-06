# Protocol And Evidence Document Index

Date: 2026-06-21

Status: Current navigation index for PIDL/FEM protocols, analysis plans and
case-evidence notes. This file does not replace the linked documents; it states
which document to start from and how to interpret older records.

## How To Choose The Right Document

For a new PIDL/FEM case analysis, start with:

- `docs/pidl_fem_diagnostic_analysis_protocol_2026-06-21.md`

For Taobo GPU launch or monitoring discipline, start with:

- `docs/taobo_gpu_submission_protocol.md`
- `docs/git_workflow.md`

For Codex agent execution rules, use the local skill:

- `/Users/wenxiaofang/.codex/skills/pidl-run-analysis-workflow/SKILL.md`

For any longitudinal real-road natural-evolution dataset, start with:

- `docs/real_road_natural_evolution_episode_policy_20260806.md`

The Codex skill is an agent workflow: folder layout, provenance capture,
download checks, analysis package generation and decision output. The docs
protocol is the shared scientific analysis protocol: what evidence a PIDL/FEM
case must support before it can be used.

## Current Entrypoints

| File | Status | Use for | Notes |
|---|---|---|---|
| `docs/pidl_fem_diagnostic_analysis_protocol_2026-06-21.md` | Current | Case-level PIDL/FEM evidence analysis | Uses schedule-dependent state mapping. |
| `docs/taobo_gpu_submission_protocol.md` | Current | Taobo GPU launch, sync and monitoring discipline | Operational protocol, not analysis evidence. |
| `docs/git_workflow.md` | Current | Mac/Windows/Taobo source-control workflow | Shared code-truth and sync rules. |
| `/Users/wenxiaofang/.codex/skills/pidl-run-analysis-workflow/SKILL.md` | Current local Codex skill | Agent execution workflow | Local to this Mac, not part of the GitHub repo. |
| `docs/real_road_natural_evolution_episode_policy_20260806.md` | Current | Episode construction, intervention/reset boundaries, and terminal censoring for real-road trajectories | Maintenance is a boundary, not a default feature; intervention studies require a separate track. |

## Schedule And Alignment History

These files are useful context, but they should not be treated as universal
current protocol. Check the loading schedule and saved-state cadence before
reusing their mapping rules.

| File | Status | Main use | Caution |
|---|---|---|---|
| `docs/pidl_fem_alignment_protocol_2026-05-29.md` | Historical / schedule-specific | Documents the one-state-per-cycle `j=c-1` alignment context | Valid when saved-state timing matches; not the retained five-substep mapping. |
| `docs/pidl_femmesh_state_timing_audit_2026-05-29.md` | Historical audit | Explains timing gaps and state-refresh issues | Evidence note, not a reusable protocol. |
| `docs/soft_hist0_alignment_audit_2026-05-29.md` | Historical audit | Records soft-hist0 alignment status at that date | Use as provenance for old comparisons only. |
| `docs/fem_pidl_strict_setting_alignment_audit_2026-05-28.md` | Historical audit | Earlier strict-setting mismatch inventory | Superseded by later alignment work for new cases. |

## Metric And Ranking Design

These files define or report scoring ideas. They are not complete provenance
protocols by themselves.

| File | Status | Main use | Caution |
|---|---|---|---|
| `docs/field_level_comparison_metric_plan.md` | Metric-design plan | Field-level score components and promotion rule | Use together with current data/provenance checks. |
| `docs/field_level_metric_results_2026-05-28.md` | Historical metric result | Result of a specific scoring pass | Do not generalise beyond its inputs. |
| `docs/taobo_tiered_comparison_plan_2026-05-29.md` | Historical ranking plan | Old Taobo run tiering and rescore queue | Useful for old-run triage, not current case evidence format. |

## Case Evidence And Audits

These are result summaries or diagnostic notes. Keep them as provenance records;
do not use them as current protocol entrypoints.

| File pattern | Status | Use for |
|---|---|---|
| `docs/*comparison_2026-05-28.md` | Historical evidence notes | Specific FEM/PIDL comparison outputs. |
| `docs/*comparison_2026-05-29.md` | Historical evidence notes | Specific soft-hist0 / diffuse comparison outputs. |
| `docs/*audit_2026-05-28.md` | Historical audits | Definition checks and mismatch inventories. |
| `docs/*audit_2026-05-29.md` | Historical audits | Alignment and state-timing evidence. |
| `docs/lbfgs_polish_audit_2026-05-30.md` | Historical negative diagnostic | Whether LBFGS polish closed a field mismatch. |

## Cleanup Rule

Do not move or archive old files only because the docs folder looks crowded.
First search for references with `rg`, then decide whether a file is an active
entrypoint, historical evidence, or safe to move under `docs/archive/`.

Recommended future archive path, only after reference checks:

```text
docs/archive/protocols/
docs/archive/evidence_notes/
docs/archive/metric_plans/
```
