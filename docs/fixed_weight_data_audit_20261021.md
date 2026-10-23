# Existing FEM data against the fixed-weight state contract

Date: 2026-10-21. Owner: `fixed-weight-learning`.
Contract/code reviewed: `440d4f7dea60175d2ce36deba99692a49e1332ee`,
`source/fixed_weight_contract.py`, `explicit_substep_post_commit_v1`.

Follow-up: the [2026-10-22 read-only remote audit](fixed_weight_data_audit_20261022.md)
verified the complete U0.115/U0.125 raw archives and resolved their material,
mesh and initial-state availability. It found specific strict-admission
differences; the dated inventory below remains the 10-21 metadata-only record.

## Decision

**No complete multi-condition corpus has yet been established as admissible
under this exact contract.** Two Hard5 amplitude conditions have existing
full-substep indexes: Umax 0.115 and 0.125. They are the strongest reuse
candidates, but neither has a completed admission record for this new contract,
both have prior development exposure, and their full raw archives were not
confirmed locally in this audit. They do not provide an untouched test set.

Other real multi-condition datasets exist, including a Ferrite material/load
pilot. Their retained field support, snapshot cadence, source semantics or
geometry differ from this contract. An experiment name, a solver's internal
step count, or a completed old split does not establish complete exported
state trajectories for this model.

This audit read local source, manifests, CSV state indexes, historical receipts
and directory/file names. It did not deserialize scientific MAT/NPY/NPZ arrays,
read protected holdout payloads, contact a producer, run a solver, train a model,
or generate new FEM data. Historical remote paths and verification receipts
are distinguished below from locally verified file existence. This is an
inventory and compatibility decision, not a new numerical-reference validation.

## Required state and trajectory

| Requirement | Exact meaning here |
|---|---|
| Fixed support | Same native Q4 mesh, node/element order and four native Gauss points; one geometry and `clamped_tensile_y` boundary family |
| Displacement/damage | Committed nodal `u[N,2]`, `d[N]`; `d_lower=d` at the declared post-commit boundary |
| History | Native GP `[H, alpha_bar, q_prev]`; `H` is current undegraded tensile energy, not its maximum over time and not damage; redundant `f` must agree with the declared Carrara law |
| Material | E, nu, Gc, ell, alpha_t, fatigue power, residual stiffness, thickness |
| Identity/timing | Immutable trajectory/reference/mesh identities; whole-condition identity; cycle, substep, contiguous ordinal, actual imposed displacement, branch, post-history-commit timing |
| Sequence | All resolved load/unload/reload states for the declared interval; no omitted reversal; aliases resolved; initialization explicitly mapped |
| Admission | Exact state count; native shapes/order, finite values, bounds, adjacent damage/alpha monotonicity, boundary consistency and source semantics checked; qualification pointer describes its actual scope |
| Split | Complete physical conditions grouped together, including seeds, windows, repeated captures and processed derivatives; protected records remain inaccessible |

## Best-matching existing candidates

Both rows below belong to the native GRIPHFiTH Hard5 producer family at commit
`862992a60edc7f59335365beacb5c71fc8592a7a`. The indexed histories are complete
over the recorded cycle range; “complete index” is not proof of current raw-file
availability or of passage through the new loader.

This audit checked each CSV's exact ordered c1..cN × s00..s05 key coverage,
alias/source-key mapping, aliased payload path/hash/displacement agreement,
timing labels and repeated actual load schedule. Both indexes were internally
consistent for those metadata checks. No payload hash was recomputed and no
numerical state-admissibility check is implied.

| Condition | Indexed coverage | Current local evidence | Reuse decision |
|---|---|---|---|
| Hard5 Umax=0.115 | c1–c103, s00–s05: **618 logical rows, 516 distinct physical payloads**, including one initial state and 515 post-commit states; 102 s00 aliases | S09-E004 `data_audit_u0115` contains static data, index/receipts and 17 s04 samples, not the full substep cache. Counts independently recomputed from the CSV in this audit | Candidate second full trajectory. E004 trained on 16 peak states; whole condition is exposed development data. No new-contract admission completed |
| Hard5 Umax=0.125 | c1–c73, s00–s05: **438 logical rows, 366 distinct physical payloads**, including one initial state and 365 post-commit states; 72 s00 aliases | S09-E008 full index/source/receipts; historical A002 full hash/decode record. Local S09-E007 has 73 original s04 MAT files plus native static; local E008 P1 has a 16-window processed packet | Strongest source/decode precedent, but full local substep data not established. Already exposed development condition; no untouched-test role |

Immutable run identities:

- U0.115: `hard5_u0115_stage0b_c23cede2bec94515a393aa291c3d6d92`.
- U0.125: `hard5_u0125_stage0b_f24eff2a79b64cc3a6538dd4f18f71ae`.

The common family has 86,756 nodes and 86,408 Q4 elements. For U0.125, source
and packet metadata specify
`(E,nu,Gc,ell,alpha_t,p,eta,t)=(1,0.3,0.01,0.01,0.5,2,0,1)` and static SHA256
`b79a36298eabec363fb7a53fb0590db46eb949b05c05dbffb9cb5a8bc0e4b40e`.
The U0.115 static/material identity must be bound to its own source record
before admitting the two as one shared-mesh corpus; a common builder alone is
insufficient.

Use **actual indexed displacement**, not nominal amplitude times an ideal
factor. The first-cycle schedules are:

- U0.115: `[0, .028749885, .057499885, .086249885, .114999885, 0]`.
- U0.125: `[0, .031249875, .062499875, .093749875, .124999875, 0]`.

### Remaining gaps in these two candidates

1. **Complete raw assets and identity:** the local metadata is present; a full
   local raw trajectory has not been established. The historical complete
   roots on CITPC12 are
   `C:\q4runs\hard5_new_runs_u0115_u0125_20260827_v1\hard5_u0115_stage0b` and
   `C:\q4runs\hard5_new_runs_u0115_u0125_20260827_v1\hard5_u0125_stage0b`.
   Remote existence was not rechecked. U0.125 A002 proves an earlier full
   decode, not current local possession. U0.115's October reuse/reseal
   receipt covers cycle summary and same-state s4 nodal u/d; it does not provide
   the same full-substep decode evidence as U0.125 A002.
2. **Initial state:** c1s00 is `pre_cycle_committed`; subsequent s00 rows alias
   the preceding s05. The current adapter only accepts native s01–s05
   `post_history_commit` records. It cannot silently relabel c1s00. Starting at
   c1s01 yields 515/365 post states respectively, but omits the initial loading
   transition and must be described as a continuation from that state.
3. **Derived fields and metadata:** `d_lower` is not separately exported. Exact
   producer commit rules support deriving it from committed `d`; that derivation
   needs provenance. `condition_id`, `reference_id`, `mesh_id`, branch and ordinal
   need explicit mapping. Existing filenames are not these semantic identities.
4. **New numerical admission:** prior A002 checks cover native decoding,
   finite values, bounds, identities and aliases, but do not establish the new
   contract's every-substep damage/alpha monotonicity or its eight-ulp boundary
   and Carrara-factor tolerances. No such all-state check was run here.
5. **Reference scope:** both recorded validation receipts have
   `reference_checked=false` and `capture_neutrality_passed=false`, despite
   coarse passed labels. The exact-source state-sufficiency conclusion is
   limited to Stage0A s00→s04 and this producer family. It does not establish
   arbitrary-substep accuracy, autonomous rollout or a physically qualified
   teacher. Synthetic archive imitation must retain that distinction.

The local 73-s04 packet is reusable for isolated native peak-state checks. The
16-window P1 packet contains `d_pre,d_peak,history_pre,history_peak,u_peak` and
mesh arrays, but lacks `u_pre` and the intermediate/unloading sequence. It
cannot be passed to the full-state trajectory loader. E012–E017 reuse this
same U0.125 condition and these windows; they add no independent conditions.

## Other assets and exclusions

These assets may support their original analyses; exclusion here concerns the
exact state/sequence contract above.

| Asset/family | What can be reused | Missing or incompatible with this contract | Split/exposure consequence |
|---|---|---|---|
| Legacy GRIPHFiTH Hard5 U0.11/U0.12/U0.13; `hard5_loao_fem_states_v1` | Three amplitude trajectories with cycle summaries c1–125/89/62 respectively; geometry/material/source descriptions; old archive-imitation benchmark | `psi_fields/cycle_N.mat` combines cycle-peak raw energy with **cycle-end** damage/history/f. Processed carrier is four element-mean channels with clipping/log transformation; not a synchronized peak state. Missing native nodal u/d, native full GP history and complete substeps; cannot invert this carrier to recover them | Original S09-E001: train U0.11/U0.13, development U0.12; no untouched test. Prior LOAO/development exposure remains; original no-post-result-tuning restrictions remain |
| Request28/Request29 native exports | Exact sparse native states, especially Request29 v3's 9 s4 states: U0.11/.12/.13 × c10/20/40; useful adapter/source diagnostics | Sparse peaks are not continuous trajectories; restart bookkeeping and all intermediate/unload states are not provided | Group with their original amplitude conditions; do not count as new independent conditions |
| FEM22 U0.12 soft/hist0 `normal`, `nstep2`, `nstep10` | Existing short c0–c5 pre/post snapshots, 45,591 nodes / 45,000 Q4; three cadences. Mixed pre/post counts are 51/21/61, not independent committed-state counts | Exporter stores slot1, slot2/alpha, slot4/f and energy diagnostics, **omits history slot3/q_prev**. Slot1 semantics not established as current H. Penalty irreversibility (`tol_irrev=1e-3`, eta=1e-6) is not established as strict `d_lower=d` semantics | Different cadence/recovery family; no new three-way split can be inferred. Short histories may aid exporter semantics checks |
| Soft5 masked explicit-step export | 346 states, c0 + c1–69 at U0.12; nodal u/d, element means and mesh/GP geometry | All-state full GP tensors explicitly omitted; precrack fatigue mask changes history/degradation semantics. Complete state count alone does not establish compatibility | Historical alignment/diagnostic data; untouched-test status unestablished |
| Older FEM factorial4 LOCO carriers | Completed original factorial comparisons and processed field carriers | No native all-substep history admission established here; cannot import old processed GNO inputs into the new contract | Existing held-out evaluations completed (36/36 training/evaluation matrix); cannot relabel the old conditions as untouched tests |
| Ferrite 2×2×2 pilot (2026-08-04) | Eight real conditions: Umax .11/.12 × E .9/1 × Gc .009/.01; existing 6/1/1 split | Representative unprotected run records 25 solved substeps, but retained snapshots are state0 plus c1–c5 peak/unload, missing s1–s3. Frozen export samples 4,320 cells, cell-averages d and u; not native nodal/full-GP state. Material8, commit timing and H mapping not established | Preserve six train, one validation and one protected holdout IDs below. Protected payload was not opened |
| Ferrite revised base / geometry family (2026-08-04) | Base eight-condition Umax .08/.10 × E 1/.9 × Gc .010/.008; base/mid/short mesh manifests and existing runs | Representative geometry run retains state0 + c1–c5 peak/unload despite 25 internal solves. Geometry/mesh identities differ between sections; cannot mix them in one fixed-mesh model. Full native-state mapping unestablished | Existing runs are real; stale top-level `LOCKED_NOT_RUN` is not proof of non-execution. Do not count mesh refinement as a new physical condition or overwrite old splits |
| S04-E027 SYNMEM | Complete synthetic histories/restarts on 16×16 and 32×32 Q4 for two prescribed prehistories | Top/bottom uy=±U/2 and only bottom-left ux fixed; other ux free. This differs from whole-edge ux clamps here and cannot be repaired by a vertical translation. Resolution/load-step variants are numerical controls, not extra independent conditions | Preserve original negative result and stopped expansion/training boundary; not a replacement corpus for this contract |
| Hybrid solver repair v11 / MOOSE-Felino / older Ferrite handoff | Source and reference-diagnostic records | v11 records no accepted continuation substeps; MOOSE candidate retains no-downstream-use conclusion; old Ferrite/GRIPHFiTH handoff supports early diagnostics only. No compatible complete reference corpus established | No additional admissible train/validation/test conditions |
| October Request31 U0.1175 launch preparations | Producer configuration, planned archive contract and launcher diagnostics | Outbox records v7 `START_FAILED_NOT_RUNNING`, no scientific output; v8 only prepared for launcher review. Not an available new trajectory | Cannot reserve or count a non-existent result as validation/test |

The **August 26 Request31** is a different item: a prepared U0.12 sparse
c1/c60/c82 plan with 18 states / 15 transitions. Its name must not be confused
with the October amendment or with the completed August U0.115/U0.125 runs.

E/Gc in the Ferrite factorial are synthetic parameter proxies; their labels do
not establish calibrated temperature or moisture physics.

## Split decision

**Executable admitted split now:** train = empty; validation = empty; test =
empty. No `TrajectoryRecord` or executable split manifest was created. In
particular, an old receipt was not inserted as a new qualification assertion.

For the two strongest candidates, a possible **future development-only**
allocation is U0.115 to training and U0.125 to validation, after the missing
admission and initialization work. Both have prior exposure, so this validation
would guide development and would not be an independent confirmatory result.
This is a recorded proposal, not a replacement of an existing protected split
and not authority to train. There is no matching untouched test condition
established by this inventory.

The Ferrite pilot's **existing split is preserved**, but is not admitted into
the present contract:

| Existing role | Exact condition IDs |
|---|---|
| Train (6) | `u011_tsoft_mwet`, `u011_tsoft_mdry`, `u011_tbase_mwet`, `u012_tsoft_mdry`, `u012_tbase_mwet`, `u012_tbase_mdry` |
| Validation (1) | `u011_tbase_mdry` |
| Protected holdout (1) | `u012_tsoft_mwet`; no run files or payload inspected |

Do not split cycles, native nodes, overlapping windows or s00 aliases between
train/validation/test. Do not count repeated captures, A002, P1 and E012–E017 as
new U0.125 conditions. Do not merge a different mesh, recovery convention,
boundary condition or solver family merely to reach a target condition count.

The earlier exploratory proposal in `fixed_weight_learning.md` required at
least six compatible complete conditions, allocated 4/1/1. This audit does
not satisfy that prerequisite. The immediate useful work is verification and
explicit adaptation of existing unprotected assets; no new data or training
is implied by this report.

Independent read-only review on 2026-10-21 recomputed both index counts and
checked the preserved Ferrite split IDs and the candidate/admission/exposure
distinctions. It found no blocking corrections. This review did not open
scientific arrays or establish new numerical qualification.

## Evidence locations

All paths below are local evidence unless explicitly labelled historical
remote. No array payloads were opened to construct this inventory.

- Contract: [fixed_weight_contract.py](../source/fixed_weight_contract.py).
- U0.115 indexed archive: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S09-E004/data_audit_u0115/{state_index.csv,run_summary.json,validation_receipt.json}`.
- U0.115 historical source root and reuse scope: `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/local_archive/experiments/S04-E016/request31_v2_readonly_audit_20261008/u0115_reuse_audit.json:3–17,59–67` and `u0115_reseal_receipt.json:7–19` in the same directory. Prior training/timing limits: S09 owner `docs/research/S09/S09-E004/experiment.md:14–39` and `code_review.md:16`.
- S09 owning worktree: `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s09-e007-fixed-damage-holdout-20261012/`.
  Relative to that owner: `local_archive/experiments/S09-E008/producer_provenance_20261016/run/state_index.csv`; `runs/S09-E008-A002-stage0a-capability-20261016/capability_audit_receipt.json` under the same E008 archive; `docs/research/S09/S09-E008/{source_state_sufficiency_audit_20261016.md,data_capability_a002_20261016.md,producer_provenance_receipt_20261016.json,experiment.md}`.
- U0.125 local peak files: S09 owner `local_archive/experiments/S09-E007/source/states/`; static `source/native_q4_mesh_dofs_quadrature.mat`.
- U0.125 P1 packet: S09 owner `local_archive/experiments/S09-E008/runs/S09-E008-P1-R001-stage0a-memorisation/packet/manifest.json`.
- U0.125 derivative reuse: S09 owner `docs/research/S09/S09-E017/runner_integration_config_draft_20261019.json` and `final_execution_candidate_20261020.json`.
- Old three-amplitude semantics: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/pidl_griphfith_hardsoft_step_audit_20260819/confirmation_report.md`, especially lines 28–42 and 58–68.
- Old processed corpus builder: `SENS_tensile/prepare_hard5_loao_gno_dataset.py`; S09 owner `docs/research/S09/S09-E001/experiment.md:60–79` records train U0.11/U0.13 and development U0.12.
- Ferrite pilot: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/freeze_select_ferrite_2x2x2_pilot_20260804/`: `gate_input/manifest.json:70–97` (split/axes), `runs/u012_tbase_mdry/run_manifest.json:8–10` and `OUTPUT_SHA256SUMS:3–42` (internal steps vs exported files), `frozen_export_v2/manifest.json:60–74` (sampled element carrier).
- Ferrite alternate family, under the same `.../after_strict_setting_alignment/fem/` parent: `ferrite_revised_base_factorial_20260804/README.md:6–25`, `ferrite_independent_mesh_3section_design_20260804/mesh_family_manifest.json`, and `ferrite_revised_geometry_corpus_20260804/runs/section_mid_L0_S0_T0/run_manifest.json` plus directory file inventory.
- FEM22 exporter: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/upload_code/fem_result/local_packages/FEM_u12/normal/export_fem22_soft_hist0_whole_field_package.m:247–276`.
- FEM22 counts: `README_fem_u012_soft_hist0_whole_field_package.md:17` in the preceding `FEM_u12` parent. Soft5 mask/full-GP omission: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/Alignment_check2_cyclic/_pidl_handoff_latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_MANIFEST_20260610/README_latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps.md:15`.
- Sparse-state coverage: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/request28_first_detect_state_semantics_export_20260817/analysis/decision.md:13`; `fixed_calendar_fatigue_exposure_gate_20260824/{02_download_verification.md,03_data_capability.md}:3` under that same `fem` parent.
- Old exposure restrictions: `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-loao-gno-20260826/docs/experiments/hard5_loao_gno_preregistration_20260826.md:32–63`; `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/pidl_result/factorial_loco_matrix_20260729/analysis/decision.md:5`.
- October U0.1175 status: `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/handovers/windows_fem_outbox.md:29–53,92–107`. August Request31: `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-loao-gno-20260826/docs/experiments/at1_fatigue_mesh_pino_stage0b_hard5_request31_decision_20260826.md:5–43`.
- SYNMEM: `/Users/wenxiaofang/phase-field-fracture-with-pidl/worktrees/synthetic-memory-mechanism-20261020/docs/research/S04/S04-E027-SYNMEM/experiment.md:24–55`.
- Other reference boundaries: `/Users/wenxiaofang/phase-field-fracture-with-pidl/worktrees/fem-surrogate-solver-repair-v6-20261020/docs/research/S04/hybrid_constrained_design_20261019/solver_repair_v11/result.md:3–12`; `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/fem-teacher-records-recovery-20261017/docs/experiments/moose_fem_teacher_candidate_track.md:47–53`; `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/handoffs/ferrite_hard5_locked_handoff_20260801_staging/README.md:67–71`.


## 2026-10-23 dated correction and continuation

The earlier exclusions describe the inspected old carriers and the then-used
handover record. Live metadata now establishes later complete native Stage0b
indexes for U0.11/.12/.13 and a completed, sealed U0.1175 fresh-v10 archive.
These are reuse candidates, not current-contract admission or independence
assertions. See [the current evidence and minimum completion plan](fixed_weight_reference_gaps_20261023.md).
The original dated observations and protected roles remain on record.
