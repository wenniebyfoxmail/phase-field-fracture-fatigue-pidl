# Aligned Result Registry

**Date**: 2026-07-06
**Purpose**: short curated registry for aligned PIDL/FEM evidence after the strict-setting cleanup.
**Rule**: use this as the daily decision entry; keep `docs/pidl_experiment_inventory.md` as the full audit ledger.

## Status Labels

| Label | Meaning |
|---|---|
| `primary` | Can support the current aligned story directly. |
| `supporting` | Useful evidence with caveats or narrower scope. |
| `negative` | Failed attempt that narrows mechanism space. |
| `diagnostic` | Explains behavior but should not be the main claim. |
| `quarantine` | Superseded, incomplete, pre-alignment, or unclear. |
| `do-not-cite` | Known bad mapping, aborted, or misleading artifact. |

## Primary / Supporting Aligned Evidence

| Case | Status | What it answers | Use for claims | Asset endpoint |
|---|---|---|---|---|
| Hard-recovery PIDL c89 vs SENS recovery FEM `N_f=89` | `primary` | Establishes the current clean final comparison pair: event timing aligns, field mechanism remains mismatched. | Main event-scale PIDL/FEM comparison; c89 replaces c69 as the hard-recovery final event reference. | `docs/pidl_fem_clear_comparison_board_2026-07-07.md`; local `COMPARISON_TO_hard_d1_u0_recovery_5step_0630.md`. |
| FEM soft-hist0 reverseBC explicit five-substep package, Requests 22/23 | `primary` | Establishes the strict FEM state semantics and c1/c69 mapping. | FEM reference, state labels, retained substep schedule, field meaning. | `docs/handovers/windows_fem_outbox.md`; OneDrive selected-state package. |
| FEM Request 21 cadence controls | `primary` | Shows retained unload cadence, not substep count alone, controls FEM fracture timing. | Peak-only is the outlier; n_step2/3/standard/10 cluster at c69-c70. | `docs/handovers/windows_fem_outbox.md`; `docs/fem_request21_cadence_interpretation_2026-05-30.md`. |
| A hist-alpha max pair | `supporting` | Tests monotone damage history under coarse vs FEM pretraining. | Max-history alone does not fix early/pathwise crack-tip lag. | `local_archive/after_strict_setting_alignment/pidl_result/A_hist_alpha_max_pair_analysis_20260615/analysis/decision.md`. |
| FEM-state restart pair | `primary` | Tests whether PIDL can propagate from a sufficiently near-critical FEM state. | c68 restart succeeds; c60 restart drifts, so the bottleneck is accumulated trajectory state before c68. | `local_archive/after_strict_setting_alignment/pidl_result/F_fem_state_restart_pair_20260616_analysis/decision.md`. |
| Active-driver/process-zone metric | `primary` | Defines the field gate for future forward PIDL claims. | Do not promote scalar `N_f` fixes unless active-driver/process-zone improves. | `docs/active_driver_process_zone_metric_2026-06-28.md`. |
| Hard-recovery graph residual discriminator v2, eta=0 | `diagnostic` | Shows a reproducible neighbourhood signal in the matched c89 peak raw-driver residual: graph beats parameter-matched MLP for all three seeds in all primary high-driver masks, but localization improvement over uncorrected PIDL is threshold-dependent. | Keep as a secondary representation diagnostic, not active-driver/mechanism closure. Freeze the protocol for the eta=1e-3 matched repeat before considering online GNN coupling. | `docs/hard_recovery_graph_residual_discriminator_v2_2026-07-10.md`; local `pidl_result/hard_recovery_graph_raw_eta0_926c34c_20260711_141546/analysis/decision.md`. |
| Bounded-degradation/history-update diagnostic for hard-recovery c89 | `diagnostic` | Shows c89 active-driver collapse is bounded-degradation dominated, with partial history-update timing support and raw-driver amplitude as secondary. | Next branch should be bounded alpha/degradation handling or history-update ordering micro-diagnostic; no full production run yet. | `local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/bounded_degradation_history_update_diagnostic_20260709/decision.md`. |
| Bounded-alpha/history-order micro-diagnostic for hard-recovery c89 | `diagnostic` | Ranks next source-level branch: residual/degradation floor is the cleanest candidate; alpha cap mostly acts as implicit floor; lagged hist-alpha and raw amplitude are not next primary. | Gate a tiny residual-stiffness/degradation-floor code-path micro-run or pre-refresh export; measure c89 active-driver support, not scalar `N_f`. | `local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/bounded_alpha_history_order_microdiagnostic_20260709/decision.md`. |
| Monotonic latest-code fatigue-off/on pair | `supporting` | Confirms monotonic fatigue-on common checkpoints match fatigue-off when no fatigue history accumulates. | Case C semantic check; compare by load value, not cyclic label. | `local_archive/after_strict_setting_alignment/pidl_result/Alignment_check2_monotonic/PIDL_mono_onoff_latest_ddc22eb_20260627_234645/`. |
| Hard-alpha U0 recovery ablations | `diagnostic` | Separates initial zero-load recovery and unload-path effects. | Five-step formal run belongs to the primary c89 comparison above; eight-step remains an unload-path ablation only. | `memory/successor_handoff.md`; local hard-alpha case notes. |
| M2S next-stage feasibility | `supporting` | Tests road-DT/M2S forecast framework, separate from forward PIDL field closure. | Useful for validation planning; do not use to hide PIDL field mismatch. | `docs/m2s_next_stage_feasibility_2026-05-31.md`; `_analysis_m2s_next_stage_20260531/`. |

## Negative Evidence To Keep, But Not Re-run Blindly

| Case | Status | Cleanup decision |
|---|---|---|
| Raw/lagged history-driver family | `negative` | Keep as bracket evidence: active-degraded under-accumulates, lagged/raw over-accumulate. Do not treat raw as untried. |
| Inverse `alpha_T` strict FEM-mesh run | `negative` | Keep as identifiability failure: parameter compensation does not repair active-driver fields. |
| Tip-local MLP/Fourier/SIREN, local patch, FBPINN, SDF/XFEM, staged head | `negative` | Keep as representation-localization negatives; do not launch another representation tweak without the active-driver gate. |
| Adaptive `lambda_hist` and repaired hard irreversibility | `negative` | Keep as evidence against loss/constraint-only closure. Do not cite as aligned field evidence. |
| Field-supervision direct forcing | `negative` | Keep as direct-forcing negative; rerun only with normalized/gated field loss and early process-zone criteria. |
| Surrogate smoke roots | `diagnostic` | Tooling only. Do not use for physics claims. |

## Quarantine / Deletion Queue

These are not physically deleted yet. They are removed from the daily decision
surface and should be moved or deleted only after the full audit row confirms no
unique evidence remains.

Second-layer cleanup details are in `docs/cleanup_manifest_2026-07-06.md`.

| Pattern / family | Status | Reason | Next action before physical deletion |
|---|---|---|---|
| `before_strict_setting_alignment/*` | `quarantine` | Pre-strict settings are not comparable to current aligned claims. | Keep only lineage rows or figures explicitly cited. |
| Failed `4905a70` precrack package attempts | `quarantine` | Failed/path-length or packaging attempts superseded by complete export. | Preserve one provenance note; delete duplicate raw payloads if disk cleanup is needed. |
| Normalized-interface eight-step recovery run | `do-not-cite` | Aborted after protocol mismatch; absolute displacement is the valid interface. | Keep only monitor/provenance note; do not use in tables. |
| Empty surrogate placeholder roots | `do-not-cite` | No evidence payload. | Safe deletion candidate after confirming no run log. |
| Metadata-only roots superseded by full `raw_remote/` downloads | `quarantine` | Duplicate census copies. | Compare checksums/provenance, then delete metadata-only duplicate if storage pressure returns. |
| Historical worktrees under `.claude/worktrees` and `.codex/worktrees` | `quarantine` | Code provenance only; not result evidence. | Use `docs/branch_inventory.md` before removing. |

## Main Checklist Entry Rule

Every future run must add one row here or in `docs/pidl_experiment_inventory.md`
with: mechanism question, changed claim, cheaper diagnostic, minimal asset,
producer machine, commit, runner, output root, verdict, and next action.
