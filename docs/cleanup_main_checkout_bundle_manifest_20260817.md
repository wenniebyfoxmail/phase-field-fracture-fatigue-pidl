# Main Checkout Review-Bundle Manifest

**Snapshot**: 2026-08-17
**Repository**: `upload code/`
**Branch**: `codex/m2s-framework-validation`
**Purpose**: assign every compact `git status` entry to a reviewable bundle
before staging, committing, merging or pushing.

## Snapshot boundary

The initial audit contained 103 compact status entries. Before this manifest was
created, three entries were added:

1. `docs/research_storylines.md` — created by the current cleanup task;
2. `docs/repository_cleanup_register.md` — created by the current cleanup task;
3. `docs/experiments/cross_umax_state_conditioned_transition_track.md` — appeared
   concurrently from another task/process and was not edited by this cleanup.

The pre-manifest working tree therefore contained **106 compact status entries**:
13 tracked modifications and 93 untracked entries. Expanded untracked-file mode
reported 142 paths because several compact entries are directories.

This document itself becomes one additional untracked management file after the
snapshot. Counts are provenance, not a clean-tree target.

The 2026-08-18 Bundle-A review added
`docs/reviews/request28_bundle_a_reconciliation_20260818.md`. It is a management
record, not a change to the historical snapshot counts above.

Two additional cross-Umax tracks appeared concurrently during that review and
were not edited by the cleanup:

- `docs/experiments/cross_umax_autonomous_timing_track.md`;
- `docs/experiments/cross_umax_same_cycle_assimilation_track.md`.

## Bundle contract

| Bundle | Scope | Storylines | Default action |
|---|---|---|---|
| `A` | Request 27/28 and cross-Umax state-conditioned observation bridge | S3 | Reconcile remote semantics first; then review as a small handoff/track bundle. |
| `B` | Real-road/LTPP acquisition, registration, recognition and method framing | S1, S2, S6, S7, S8 | Split committed LTPP chain from dirty August 12 follow-on work; preserve negative gates. |
| `C` | Freeze-Then-Select implementation and evidence | merged into paused S4 methodology evidence | Preserve as a bounded negative/tooling package; no producer run or selector tuning. |
| `D` | PIDL/FEM evidence, figures and FEM-teacher documentation | S4, S5 | Review provenance/status drift and figure sidecars before integration. |
| `E` | Project management, cleanup, skills and planning | management layer | Commit only after scientific bundles are stable enough that links/statuses are correct. |
| `X` | Cross-bundle canonical indexes | S1–S8 | Integrate last; never let one bundle overwrite another's ledger/frontier update. |

No bundle is approved for commit or push merely by appearing here.

## Unpublished commit stack

The 13 commits ahead of `origin/codex/m2s-framework-validation` are already
cleanly separable by purpose:

### Bundle B — twelve LTPP spatial-registration commits

| Commit | Purpose |
|---|---|
| `9fc0a44` | confirmed map-panel and outer-frame MVP evaluation |
| `04a580e` | owner-reviewed corner MVP |
| `4e23176` | assisted corner candidates |
| `f01c8a0` | assisted-candidate correction |
| `0c492b1` | owner-corner render MVP freeze |
| `cab8724` | carrier coordinate correction |
| `9e1c627` | owner-corner MVP result |
| `064274d` | Tier-B review packet freeze |
| `5f0c4a4` | Tier-B approval record |
| `9b07042` | geometry-assisted grid-control pilot |
| `2959af6` | development-eight registration MVP |
| `4f9c8cf` | seven-date registration MVP |

These form one chronological development chain. They should be reviewed against
the later uncommitted full-source/cross-state outcome before deciding whether to
push the chain unchanged or add a terminal status commit.

### Bundle A — one Request 28 commit

| Commit | Purpose |
|---|---|
| `e71ece3` | initial first-detect state-export request |

`e71ece3` is patch-equivalent to `fc65daf` and `1176250`; do not cherry-pick
either duplicate. The follow-up agent commits `e884524` and `368a7e8` are
intermediate semantic/audit records, not the terminal Request 28 decision. The
later clean worktree `codex/kan-rbf-u012-micro@94d9c2b` records package
acceptance (`f3bbc14`) and the terminal negative observability gate (`94d9c2b`).
Do not merge either branch wholesale: the agent branch predates the twelve LTPP
commits, while the terminal branch contains a mixed KAN/RBF/Request-28 chain.
Use the commit-level reconciliation record below before selective integration.

## Bundle A — Request 27/28 and cross-Umax observation bridge

### Tracked modifications

- `docs/handovers/windows_fem_inbox.md`
  - adds Request 27 to the shared inbox;
  - must be reconciled with the existing Request 28 edits and the corrected
    `agent/fem-request-28` branch.

### Untracked paths

- `docs/experiments/cross_umax_state_conditioned_transition_track.md`
  - concurrent addition; active oracle gate;
  - preserve owner/content unchanged until its producing task is identified.
- `docs/experiments/cross_umax_autonomous_timing_track.md`
  - concurrent addition; preserve unchanged pending owner/status review.
- `docs/experiments/cross_umax_same_cycle_assimilation_track.md`
  - concurrent addition; preserve unchanged pending owner/status review.
- `docs/experiments/cross_umax_short_horizon_forecast_preregistration_20260818.md`
  - concurrent development-only preregistration using calendar-cycle windows;
  - does not itself reopen S3 or authorize a producer trajectory.
- `docs/experiments/cross_umax_short_horizon_forecast_result_20260818.md`
  - terminal development result: `DIAGNOSTIC_NEGATIVE__NO_ARCHITECTURE_EXPANSION`;
  - preserve unchanged; it does not authorize an architecture sweep or new producer trajectory.
- `docs/reviews/cross_umax_short_horizon_forecast_external_review_20260818.md`
  - external review confirms the mandatory within-fold standardization and leakage isolation;
  - preserve unchanged as review evidence for the terminal negative result.
- `SENS_tensile/run_cross_umax_short_horizon_forecast.py`
- `tests/test_cross_umax_short_horizon_forecast.py`
  - concurrent runner/test pair for the preregistration above;
  - preserve unchanged; execution and result registration are now terminally negative.
- `docs/handovers/windows_griphfith_request_27_u013_c5_probe_20260730.md`
- `docs/reviews/request28_bundle_a_reconciliation_20260818.md`
  - commit-level supersession and integration decision created by this cleanup;
  - no replay, experiment, merge or push authorization.
- `docs/reviews/request28_terminal_dependency_audit_20260818.md`
  - isolated file-level dependency, evidence and patch-applicability audit;
  - defines Unit A, Unit B and later Bundle-X reconciliation without applying
    them.

### Shared-index dependency

- the new cross-Umax result rows in `docs/pidl_experiment_inventory.md` belong to
  Bundle A scientifically, but the file itself remains Bundle X;
- S3 status wording in `docs/research_frontier.md` remains Bundle X.

### Review gate

1. Completed: `e71ece3`, `fc65daf` and `1176250` are patch-equivalent.
2. Completed: `e884524`/`368a7e8` are intermediate records superseded by
   `f3bbc14`/`94d9c2b`; do not cherry-pick the three-commit agent series.
3. Preserve the twelve intervening LTPP commits.
4. Completed: the terminal branch was reviewed by file dependency; Unit A is
   `f3bbc14`, Unit B is the four core additions from `94d9c2b`, and its two
   shared-index hunks are deferred to Unit X. Do not merge the mixed
   fourteen-commit chain wholesale.
5. Inspect concurrent ownership of the cross-Umax track.
6. Validate links and terminal evidence in an isolated integration worktree;
   this cleanup authorizes no Windows/FEM replay.

### Isolated integration update — 2026-08-18

Completed on clean local branch `codex/request28-terminal-integration` based on
`e71ece3`:

- Unit A `a2218cb`;
- Request 27 preservation `1e9ecab`;
- Unit B `59613d0`.

At the three-commit stage, the branch preserved the twelve LTPP commits, passed
the package and deterministic-analysis checks, and remained unpushed. Bundle-X
registry/frontier/storyline reconciliation was intentionally absent.

Unit X was subsequently added as `15f0975`, containing only the Request 28
inventory row and frontier terminal status. The main working copy's concurrent
inventory/frontier edits were deliberately excluded. S3 was reconciled to
`paused` in the untracked management-layer `docs/research_storylines.md`, with a
branch-qualified terminal-track reference until integration occurs.

The completed four-commit branch was then remotely preserved at
`origin/codex/request28-terminal-integration@15f0975b65489a9ef19e88030d8497c3327f2571`.
No PR or merge was created.

## Bundle B — Real-road/LTPP and observation-conditioned framing

### Tracked modifications

- `docs/experiments/ltpp_geoforecast_crack_recognition_b1_failure_audit_20260807.md`
- `docs/experiments/ltpp_geoforecast_crack_recognition_document_aware_amendment_candidate_20260807.md`
- `docs/experiments/ltpp_geoforecast_crack_recognition_track.md`
- `docs/experiments/ltpp_geoforecast_spatial_registration_track.md`
- `scripts/ltpp_acquire_enriched_tables.py`
- `scripts/ltpp_audit_candidate_forcing_timeline.py`
- `scripts/ltpp_geometry_assisted_grid_control_pilot_server.py`
- `scripts/ltpp_registration_control_annotator_server.py`

The two acquisition-script edits generalize state handling beyond the original
six California sections. They belong with the cross-state acquisition evidence,
not with the earlier six-section posterior result.

### Cross-state acquisition and registration records

- `docs/experiments/ltpp_cross_state_acquisition_result_20260812.csv`
- `docs/experiments/ltpp_cross_state_acquisition_track.md`
- `docs/experiments/ltpp_cross_state_batch2_fl_candidates_20260812.json`
- `docs/experiments/ltpp_cross_state_batch2_mn_candidates_20260812.json`
- `docs/experiments/ltpp_cross_state_batch2_tx_candidates_20260812.json`
- `docs/experiments/ltpp_cross_state_co_candidates_20260812.json`
- `docs/experiments/ltpp_cross_state_co_enriched_retry_gate_20260812.json`
- `docs/experiments/ltpp_cross_state_fl_candidates_20260812.json`
- `docs/experiments/ltpp_cross_state_geometry_pass_config_20260812.json`
- `docs/experiments/ltpp_cross_state_mn_candidates_20260812.json`
- `docs/experiments/ltpp_cross_state_single_owner_grid_annotation_20260812.md`
- `docs/experiments/ltpp_cross_state_single_owner_line_annotation_full_source_amendment_20260812.md`
- `docs/experiments/ltpp_cross_state_single_owner_line_annotation_preregistration_20260812.md`
- `docs/experiments/ltpp_cross_state_single_owner_line_annotation_result_20260812.md`
- `docs/experiments/ltpp_cross_state_spatial_registration_tier_b_packet_amendment_20260812.md`
- `docs/experiments/ltpp_cross_state_spatial_registration_tier_b_packet_result_20260812.md`
- `docs/experiments/ltpp_cross_state_tx_candidates_20260812.json`

### Crack-recognition follow-on records

- `docs/experiments/ltpp_geoforecast_crack_recognition_nondestructive_freeze_candidate_20260810.md`
- `docs/experiments/ltpp_geoforecast_crack_recognition_nondestructive_no_fit_result_20260810.md`
- `docs/experiments/ltpp_geoforecast_crack_recognition_nondestructive_taobo_result_20260810.md`
- `docs/experiments/ltpp_geoforecast_crack_recognition_training_runner_preflight_20260810.md`
- `docs/experiments/ltpp_geoforecast_document_aware_target_preview_20260810.md`
- `docs/experiments/ltpp_geoforecast_document_preprocessing_preservation_result_20260810.md`

These records must retain the terminal `RECOGNITION_GATE_FAILED` interpretation;
implementation/preflight passes do not convert the training result to a pass.

### Road-source and framework records

- `docs/figures/observation_conditioned_latent_temporal_20260720/`
- `docs/mnroad_cell22_data_request_20260805.md`
- `docs/pavetrack_pd_manifest_audit_20260805.json`
- `docs/pavetrack_pd_manifest_audit_20260805.md`
- `docs/pavetrack_pd_registration_gate_20260805.json`
- `docs/pavetrack_pd_registration_gate_20260805.md`
- `docs/real_road_trajectory_coverage_matrix.csv`
- `docs/real_road_trajectory_coverage_matrix.md`
- `docs/literature_notes/yang_guo_ren_2026_latent_temporal_surrogate.md`
- `docs/literature_notes/zezhi_shao_road_crack/reading_list_20260812.md`

The framework figure directory contains source plus PNG/PDF/SVG renders and a
README. Before tracking rendered figures, verify the README satisfies the
project figure-sidecar contract and decide which formats are canonical.

### Review records

- `docs/reviews/ltpp_cross_state_single_owner_line_annotation_external_review_20260812.md`
- `docs/reviews/ltpp_cross_state_single_owner_line_annotation_full_source_external_review_20260812.md`
- `docs/reviews/ltpp_cross_state_single_owner_line_annotation_full_source_external_review_request_20260812.md`
- `docs/reviews/ltpp_cross_state_spatial_registration_tier_b_external_review_20260812.md`
- `docs/reviews/ltpp_cross_state_spatial_registration_tier_b_external_review_request_20260812.md`
- `docs/reviews/ltpp_geoforecast_crack_recognition_document_aware_external_review_request_20260807.md`
- `docs/reviews/ltpp_geoforecast_crack_recognition_document_aware_owner_visual_review_20260810.md`
- `docs/reviews/ltpp_geoforecast_crack_recognition_document_aware_visual_review_packet_20260810.md`
- `docs/reviews/ltpp_geoforecast_crack_recognition_nondestructive_chatgpt_review_20260810.md`
- `docs/reviews/ltpp_geoforecast_crack_recognition_nondestructive_freeze_approval_20260810.md`
- `docs/reviews/ltpp_geoforecast_crack_recognition_nondestructive_review_bundle_20260810.sha256`
- `docs/reviews/ltpp_geoforecast_crack_recognition_training_authorization_approval_20260810.md`
- `docs/reviews/ltpp_geoforecast_crack_recognition_training_authorization_approved_20260810.json`
- `docs/reviews/ltpp_geoforecast_crack_recognition_training_authorization_template_20260810.json`
- `docs/reviews/ltpp_geoforecast_crack_recognition_training_review_round1_20260810.md`

Review requests, review verdicts, approvals and execution results must remain
distinct. Presence of an approval template is not execution authorization.

### Source and tests

- `scripts/ltpp_audit_document_preprocessing_preservation.py`
- `scripts/ltpp_build_document_aware_target_preview.py`
- `scripts/ltpp_document_nondestructive_prediction_assets.py`
- `scripts/ltpp_prepare_cross_state_owner_grid_control_packet.py`
- `scripts/ltpp_prepare_cross_state_registration_review_packets.py`
- `scripts/ltpp_render_crack_recognition_review_figure.py`
- `scripts/ltpp_run_nondestructive_crack_recognition_taobo.py`
- `scripts/ltpp_single_owner_line_annotator_server.py`
- `scripts/ltpp_validate_nondestructive_recognition_freeze.py`
- `tests/test_ltpp_prepare_cross_state_owner_grid_control_packet.py`
- `tests/test_ltpp_prepare_cross_state_registration_review_packets.py`
- `tests/test_ltpp_single_owner_line_annotator_server.py`

### Review gate

1. Validate each script/test group against its dated experiment record.
2. Run only lightweight Mac tests; no training.
3. Ensure the spatial-registration track remains `paused` and recognition remains
   `killed` under the frozen protocol.
4. Decide whether the twelve committed MVPs need a terminal follow-on commit
   before pushing.

## Bundle C — Freeze-Then-Select bounded methodology package

### Source package

- `SENS_tensile/export_freeze_select_ferrite_carrier.py`
- `SENS_tensile/freeze_select/`
- `SENS_tensile/run_freeze_select_comparison_gate.py`
- `SENS_tensile/run_freeze_select_environment_consensus.py`
- `SENS_tensile/run_freeze_select_ferrite_adapter_sentinel.py`
- `SENS_tensile/run_freeze_select_from_snapshot.py`
- `SENS_tensile/run_freeze_select_genuine_joint_sentinel.py`
- `SENS_tensile/run_freeze_select_producer_gate.py`
- `SENS_tensile/run_freeze_select_single_shot_loo.py`
- `SENS_tensile/run_freeze_select_stage_a2.py`
- `SENS_tensile/run_freeze_select_stage_a2_matrix.py`
- `SENS_tensile/run_freeze_select_stage_a3.py`
- `SENS_tensile/run_freeze_select_stage_a4.py`
- `SENS_tensile/run_freeze_select_stage_a5_oracle.py`
- `SENS_tensile/run_freeze_select_synthetic.py`

`SENS_tensile/freeze_select/__pycache__/` files are generated dependencies and
must remain ignored/untracked.

### Evidence and handoff

- `docs/freeze_then_select/`
- `docs/handovers/freeze_select_fem_producer_request_2026-08-04.md`

The controlling conclusion is
`docs/freeze_then_select/current_reliability_verdict_2026-08-04.md`: the tooling
loop works, but mechanism-support reliability repeatedly failed. A2–A5 are
quarantined; do not tune another threshold, launch the provisional FEM producer,
or present forecast IoU as mechanism recovery.

### Tests

- `tests/test_freeze_select.py`
- `tests/test_freeze_select_comparison_gate.py`
- `tests/test_freeze_select_producer_gate.py`
- `tests/test_freeze_select_stage_a2.py`
- `tests/test_freeze_select_stage_a3.py`
- `tests/test_freeze_select_stage_a4.py`

### Review gate

1. Confirm generated caches are excluded.
2. Run the focused unit suite using the approved local lightweight environment.
3. Validate `attempts.jsonl`, manifest templates and result links.
4. Commit code, tests and bounded negative/tooling verdict together; do not split
   code from the claim boundary.

## Bundle D — PIDL/FEM and FEM-teacher evidence

### Tracked modifications

- `SENS_tensile/figfiles/pidl_fem/fig_A3_SN_comparison.png`
- `SENS_tensile/generate_figs_pidl_fem.py`

The binary figure changed together with its generator. Verify exact data
provenance, rerender deterministically and satisfy the same-stem sidecar rule
before tracking the figure change.

### Untracked evidence and reviews

- `docs/handovers/moose_felino_taobo_qualification_handoff_20260805.md`
  - locally ends at a 2026-08-06 `RUNNING` status and is stale relative to the
    later full exact-KKT numerical PASS and Gate-3A behavioral failure;
  - update or clearly supersede before commit.
- `docs/pidl_fem_clear_comparison_board_2026-07-07.md`
- `docs/reviews/fem_teacher_candidate_library_survey_20260806.md`
- `docs/literature_notes/raissi_perdikaris_karniadakis_2019_pinns.md`

### Shared-index dependency

- PIDL/FEM, Azinpour and MOOSE/Felino rows in
  `docs/pidl_experiment_inventory.md` are Bundle D content inside Bundle X.

### Review gate

1. Validate the figure sidecar and source-data path.
2. Reconcile the stale MOOSE/Felino handoff with the current local archive
   decisions without erasing historical statuses.
3. Preserve numerical-pass versus physical/teacher `NO_GO` separation.
4. Do not run PIDL training or FEM production as part of documentation cleanup.

## Bundle E — Project management and reusable workflow documents

- `docs/cleanup_manifest_2026-07-06.md`
- `docs/future_plan_with_criteria_2026-07-06.md`
- `docs/repository_cleanup_register.md`
- `docs/research_storylines.md`
- `docs/skills/paper-ledger-to-paper/`
- `docs/skills/project_skill_inventory_2026-07-06.md`
- `docs/cleanup_main_checkout_bundle_manifest_20260817.md` — this manifest,
  added after the 106-entry snapshot.

These are compact knowledge assets appropriate for Git after link/status review.
They must not be used to hide or overwrite unresolved scientific working-tree
changes.

## Bundle X — integrate canonical indexes last

### `docs/pidl_experiment_inventory.md`

The current 10-line addition actually contains multiple FEM/PIDL result rows,
including cross-Umax, Azinpour, Hard5 and temporal-gate evidence. It is a shared
ledger update, not a single-experiment change. Review each inserted row against
its decision artifact, then integrate only after Bundles A and D are settled.

### `docs/research_frontier.md`

The current diff adds LTPP recognition as a fourth active branch even though the
file declares a maximum of three active branches. `docs/research_storylines.md`
now owns the multi-route state. Before commit, reduce the frontier back to one
current question and at most three active branches, with paused/killed routes
linked rather than presented as active.

## Recommended integration order

1. Protect concurrent Bundle-A ownership and reconcile corrected Request 28.
2. Review Bundle C as the smallest self-contained code/test/evidence package.
3. Review Bundle B's uncommitted August 12 continuation and terminal statuses,
   then decide how to publish the existing twelve-commit chain.
4. Review Bundle D figure provenance and stale FEM-teacher status documents.
5. Integrate Bundle X ledgers/frontier after A–D conclusions are fixed.
6. Commit Bundle E management pages last or in a separate documentation-only
   commit.

No deletion or worktree removal should occur until these bundles have reviewed
destinations.
