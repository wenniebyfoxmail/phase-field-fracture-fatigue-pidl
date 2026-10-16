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
| c86 damage-conditioned eta0 equilibrium projection | `diagnostic` | Shows that true diffuse c86 FEM damage is sufficient to reconstruct c87 raw mechanics and near-close c89 active support through a frozen operator. | Conditional mechanism closure only; do not call it autonomous PIDL or inspection-only recovery because full diffuse damage and hidden history/degradation are supplied. | Local `analysis/fem_damage_conditioned_equilibrium_20260716/decision.md`. |

## Negative Evidence To Keep, But Not Re-run Blindly

| Case | Status | Cleanup decision |
|---|---|---|
| Raw/lagged history-driver family | `negative` | Keep as bracket evidence: active-degraded under-accumulates, lagged/raw over-accumulate. Do not treat raw as untried. |
| Inverse `alpha_T` strict FEM-mesh run | `negative` | Keep as identifiability failure: parameter compensation does not repair active-driver fields. |
| Tip-local MLP/Fourier/SIREN, local patch, FBPINN, SDF/XFEM, staged head | `negative` | Keep as representation-localization negatives; do not launch another representation tweak without the active-driver gate. |
| Adaptive `lambda_hist` and repaired hard irreversibility | `negative` | Keep as evidence against loss/constraint-only closure. Do not cite as aligned field evidence. |
| Field-supervision direct forcing | `negative` | Keep as direct-forcing negative; rerun only with normalized/gated field loss and early process-zone criteria. |
| Surrogate smoke roots | `diagnostic` | Tooling only. Do not use for physics claims. |
| c86 binary-crack skeleton + fixed AT1 equilibrium assimilation | `negative` | Reject geometry-only damage reconstruction: c86 damage morphology looks close, but c87 raw and c89 active support spread to about 100x FEM area. Hard binary/full-resolution masks are eta0-singular. Near-core degradation amplitude, not crack location alone, is the missing state. Next gate must infer amplitude from c86 observables rather than tune target-cycle thresholds. Local `analysis/fem_visible_crack_equilibrium_20260716/decision.md`. |

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

## Supplemental diagnostic — 2026-10-12

| Case | Status | What it answers | Use for claims | Asset endpoint |
|---|---|---|---|---|
| Q4 c83s4 bounded solver-control refinement | diagnostic; EXTRA_BUDGET_EXHAUSTED | Original20-round baseline reproduced; tighterinner and freshoutermonitor,10extra rounds, residualsum1.30639× and absolute PIDLactivegap1.99032×. | Budget-specific control sensitivity only; not convergedteacher or physicaltruth, original E003/E011 unchanged. | [Terminal evidence](research/S04/S04-E011/runs/endpoint_q4_tight_20261012.md); [track](experiments/hard5_q4_t3_solver_alignment_track.md) |


## Supplemental diagnostic — 2026-10-13

| Case | Status | Question and changed claim | Minimal asset / producer / source | Verdict and next action |
|---|---|---|---|---|
| Q4 six-state joint backtracking | terminal diagnostic, five budget exhaustions and c83 trial stall | Offline outer20–30 localization preceded bounded coupled-control test; earlier states improve but c83 active gap worsens despite merit decrease. | [Decision/metrics](research/S04/S04-E011/runs/endpoint_backtrack_grid_20261013.md); CITPC12, e8c57e3, run_s04_e011_endpoint_backtrack.m, external run pf_s04e011_backtrack_grid_e8c57e3_20261013T111601Z. | All gates/review PASS, all six miss4e-6; no teacher/truth claim. Next saved-state phase-floor and coupled tangent diagnostic, unexecuted. |


## Saved-state diagnostic — 2026-10-13

| Case | Status | Question | Asset / producer | Interpretation |
|---|---|---|---|---|
| c1/c83 saved-state phase/tangent diagnostic | offline diagnostic complete; native capture prepared | Separate cache/projection/raw refresh and coupled derivative mechanisms; c1 f=1 rules out fatigue derivative as universal explanation. | [Result and compact metrics](research/S04/S04-E011/runs/phase_tangent_saved_state_20261013.md); native four-state CITPC12 bundle pending final transfer approval. | Source-equivalent/native residual agreement; no native tangent or projection attribution yet. |


## Native phase capture — 2026-10-15

| Case | Status | Measured discriminator | Evidence endpoint | Next action / boundary |
|---|---|---|---|---|
| c1/c83 baseline and last native phase/update capture v2 | completed,13files246934739bytesverified | Cache→return→clip→raw-refresh; native K direction and60merit differences. Residual/state mismatch and incomplete constrained stationarity; smaller c83 step gives tiny descent beyond old grid. | [Result](research/S04/S04-E011/runs/phase_capture_v2_result_20261015.md),CITPC12,ce7085e,run_s04_e011_phase_capture.m,external local archive pf_s04e011_phase_capture_20261014_v2. | Genuine nodal constrained damage/fresh-stop comparison, unexecuted; no full-trajectory or teacher claim. |


## Constrained phase repair preparation — 2026-10-15

| Candidate | Status | Comparator | Evidence / next action |
|---|---|---|---|
| E011 fixed captured-u fresh-only / constrained damage | prepared locally; native execution pending | completed four-state native v2 capture | [Protocol](research/S04/S04-E011/constrained_damage_protocol_20261015.md); six-file upload approval, producer syntax/selftests, c1 prerequisite then c83. No new numerical result or teacher. |


## Fixed-u constrained damage result — 2026-10-15

| Case | Execution / retrieval | Numerical finding | Evidence / disposition |
|---|---|---|---|
| E011 c1/c83 fixed captured-u fresh-only / constrained damage v1 | completed4states8arms;40files468584478bytesverified; source8070c02 | Constrained4/4phasepass; fresh-onlyafterclip0/4. c83-lastRu+14.75%, sum+5.91%, activegap modestly lower but integralgap higher. | [Result](research/S04/S04-E011/runs/damage_repair_v1_result_20261015.md); advance boundedphase/repair coupling. No acceptedhistory, trajectory or teacher qualification. |


## Coupled repair preparation — 2026-10-15

| Candidate | Status | Comparator / fixed decision | Evidence |
|---|---|---|---|
| E011 displacement re-equilibration + constrained damage v1 | prepared locally, not uploaded/launched | DR-v1 constrained endpoints; joint C<=1, c1 both pass before c83,20 blocks/250u+250d calls per state | [Protocol](research/S04/S04-E011/coupled_repair_protocol_20261015.md); independent local review, exact-version transfer approval and Windows12-selftest validation pending. No new solver/teacher claim. |


## Coupled repair v1 attempt / locator v2 — 2026-10-15

| Candidate | Execution / retrieval | Interpretation / next action |
|---|---|---|
| E011 coupled v1, source8ce3a58 | uploaded/Windows static +12selftests pass; MissingFile before native oracle;16files73957bytesverified | Inconclusive,0completedstates; not couplednegative. [Attempt](research/S04/S04-E011/runs/coupled_repair_v1_attempt_20261015.md). Two backup predecessor hashes match; locator-onlyv2 requires new exact upload approval. |


## Coupled v2 I/O attempt / v3 snapshot preparation — 2026-10-15

| Case | Execution / retrieval | Verdict / next action |
|---|---|---|
| E011 CR-v2 source89056f5 |12selftests pass, mesh fileread I/O failure before nativefields;16files75941bytesverified | Inconclusive. [Attempt](research/S04/S04-E011/runs/coupled_repair_v2_attempt_20261015.md). IdenticalSHA mesh readable elsewhere; v3 snapshots all15data inputs and gates actual worker IO before c1, exact upload approval pending. No coupled numerical result. |


CR-v3 2026-10-15: uploaded9file set verified;15inputcopies540736827bytes/fullSHA/attrs32 verified. Strictstatic blocks two scriptSAGROW suppression-comment mistakes; no worker launched. [Two-file static repair](research/S04/S04-E011/runs/coupled_repair_v3_static_annotation_20261015.md) prepared, pending replacement approval, no numerical change/result.


| E011 CR-v3 clean5cf59f8 | completed4/4jointpass;51files1058569769bytesverified | c1blocks4/1,c83blocks17/15; C=.647694/.192506/.093877/.007198, immutablehistory0. Independent16snapshot replay/counter/state checks pass. c83activeintegral~3%ofprior, fixedPIDLgap104.16%,rho~.00664. | [Terminal/metrics](research/S04/S04-E011/runs/coupled_repair_v3_result_20261015.md); bounded numerical closure only, not field-alignment/teacher/trajectory success. Next sequential accepted-history diagnostic unexecuted. |


E011 c1 commit v1: [local preparation only](research/S04/S04-E011/runs/c1_commit_v1_preparation_20261015.md), [protocol](research/S04/S04-E011/c1_commit_protocol_20261015.md).15files,8inputcopies156839354bytes; original archive regression then repaired sequential5substeps. Local independent source review passed; Windows22tests and native calculations notrun, no transfer. Fresh joint gate uses PREcommit oldlower/history, exactlyone accepted version/step. No new numerical/trajectory claim.


2026-10-16 S04-E011 c1 sequence v1: [attempt](research/S04/S04-E011/runs/c1_commit_v1_attempt_20261016.md), producer db5cb94, WMI30232, staticcheck stop,0native fields/commits,31files156923216bytes hashverified; operational failure/scientifically inconclusive. v2 preparation does not alter frozen E003/E011.


2026-10-16 S04-E011 [c1v2](research/S04/S04-E011/runs/c1_commit_v2_attempt_20261016.md): producer aab3edd/WMI6324, static pass then JSONcell-vs-struct admission failure,0nativefields/commits.31files156920132bytes hashverified. Inconclusive; v3schema repair local-only, old scientific verdicts unchanged.


2026-10-16 S04-E011 [c1v3 terminal](research/S04/S04-E011/runs/c1_commit_v3_result_20261016.md): producer3d2d738/WMI8304/worker7468. Admission22tests/I/Opassed, original2durablecommits; s3rawregressionmiss, no repair.42files406754040bytes verified. Diagnosticpartial, pairedrepair inadmissible/efficacyunassessed. s3rawweightedrelL2~1.64e-12 andown-ureplayexplanation do not relaxgate.


2026-10-16 S04-E011 [rawresponse r4](research/S04/S04-E011/raw_admission_r4_20261016.md): supportingoffline admission-design audit, no newnative result. ExplicitQ4replay + analyticLbound +6rawfieldnegativecontrols/4logicchecks reviewed. v4newdefinition pending exact16fileapproval; frozen v3result unchanged.


2026-10-16 [c1 v4/r4 completed](research/S04/S04-E011/runs/c1_commit_v4_r1_result_20261016.md): original five-step admission passes under prospective r4; legacy raw s3 still fails. Repaired five steps pass the PRE-COMMIT joint criterion under old history/lower, each with one durable version advance. Shared recovery: 34 phase calls, one reset. All 69 files / 1,353,725,620 bytes verified; producer 6794251. Repaired C = .165322/.392168/.887083/.813816/2.04e-6; s2 uses all 20 blocks. Original misses strict fresh closure at all five steps. Active weighted relative L2 difference is 79.41% at s2 and 16.50% at peak, although peak integral changes only −.2243%. All GP f=1: supports one-c1 numerical/state-transition consistency, not fatigue-degradation feedback, unique equilibrium, teacher or physical validity. Next unexecuted discriminator: same-predecessor s2 local solver sensitivity versus incoming-state propagation.
