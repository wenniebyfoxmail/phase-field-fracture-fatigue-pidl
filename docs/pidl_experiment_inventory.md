# PIDL Experiment Inventory

Date: 2026-06-27

This is a first-pass census of PIDL-related experiments visible on the Mac.
It is deliberately read-only: no raw archive, worktree, OneDrive package, or
result folder was moved or deleted while making this file.

Project aliases used below:

```text
PROJECT=/Users/wenxiaofang/phase-field-fracture-with-pidl
UPLOAD=$PROJECT/upload code
ONEDRIVE=/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result
```

Two columns are intentionally first-class because they are the useful research
memory, not decoration:

- `Why run this experiment`
- `Key change`

Credibility labels:

```text
canonical      trusted evidence used directly for a paper/thesis claim
supporting     useful supporting evidence, usually with caveats
diagnostic     mechanism/debugging evidence
negative       useful failed attempt
inconclusive   preserved for traceability only
```

## Census Scope

Scanned roots:

| Root | Observed role | Notes |
|---|---|---|
| `$PROJECT/local_archive/after_strict_setting_alignment/` | Main post-strict PIDL/FEM archive | About 136G; highest-priority evidence root. |
| `$PROJECT/local_archive/before_strict_setting_alignment/` | Legacy/pre-strict PIDL/FEM archive | About 26G; keep separate from strict evidence. |
| `$PROJECT/local_archive/mac_pidl_smoke_20260626/` | Mac smoke payload | Lightweight/local only; not a production training pattern. |
| `$UPLOAD/docs/` | Shared decision summaries | Contains discriminator and validation notes. |
| `$UPLOAD/.codex/worktrees/` and `$UPLOAD/.claude/worktrees/` | Historical worktrees | Useful for code provenance; do not remove before branch inventory. |
| `$ONEDRIVE/` | FEM/PIDL handoff packages | Mostly producer/handoff data, not all are PIDL runs. |

Current repo hygiene note: `$PROJECT` is not currently a git repo from the
shell's point of view. `$UPLOAD` is the shared git repo and is on branch
`codex/m2s-framework-validation`; untracked files seen before this inventory
were `SENS_tensile/figfiles/` and `SENS_tensile/posthoc_element_tip_criterion.py`.
They were not touched.

## Experiment Time Index

Time zones are preserved as recorded in the source note when possible. If a
timestamp comes only from a run id such as `..._20260616_133936`, it is marked
as `from run_id` rather than treated as a verified wall-clock launch time.

| case_id | Experiment time marker | Time evidence |
|---|---|---|
| `femlike_irr_penalty_b70cdf3_20260626` | Created 2026-06-26 17:40 BST; launched 2026-06-26 17:45 BST; still running at 18:31 BST; analysis continued 2026-06-27 | `01_monitor.md`; run id `pf_femlike_irr_b70cdf3_20260626_174545`; analysis folder names |
| `mono_fatigue_off_f3b29cc_20260627` | Created 2026-06-27 00:44 BST; launched 00:45 BST; completed normally by 01:00 BST | `01_monitor.md`; run id `pf_mono_fatoff_f3b29cc_20260627_0044` |
| `softHist0_monoU02_8seed_ec32214_20260623_172416` | Manager launched 2026-06-23 17:41 BST; manager ended Wed Jun 24 13:35:05 CST as recorded; result check dated 2026-06-24 | `01_monitor.md`; run id timestamp `20260623_172416` |
| `pf_softHist0_state0_seed1_66b56e4_20260624_124606` | First state0-export attempt timestamp 2026-06-24 12:46 from run id | `00_intent.md`; run id `pf_softHist0_state0_seed1_66b56e4_20260624_124606` |
| `pf_softHist0_state0_seed1_meshsync_66b56e4_20260624_124900` | Retry timestamp 2026-06-24 12:49 from run id | `00_intent.md`; run id `pf_softHist0_state0_seed1_meshsync_66b56e4_20260624_124900` |
| `A_hist_alpha_max_coarse_pretrain_20260615` | Timestamp 2026-06-15 06:44:11 from run id | `00_intent.md`; run id `pf_hist_alpha_max_clean2_16ba4cf_20260615_064411` |
| `A_hist_alpha_max_fem_pretrain_20260615` | Timestamp 2026-06-15 06:49:15 from run id | `00_intent.md`; run id `pf_hist_alpha_max_fempretrain_16ba4cf_20260615_064915` |
| `A_hist_alpha_max_pair_analysis_20260615` | Pair analysis dated 2026-06-15; source runs launched from the two 2026-06-15 run ids above | `analysis/decision.md`; sibling case intents |
| `A_hist_alpha_max_raw_driver_fem_pretrain_20260616` | Launch preparation and run id timestamp 2026-06-16 13:39:36; completed at Python elapsed 17:37 in monitor | `01_monitor.md`; run id `pf_Araw_histmax_fempretrain_a2dc123_20260616_133936` |
| `F_fem_state_restart_pair_20260616_analysis` | Run id timestamp 2026-06-16 08:01:48; c60 launch time recorded as Tue Jun 16 08:03:00 BST | `F_fem_state_restart_c60_to_c72_20260616/01_monitor.md`; run id `pf_Frestart_c60_c68_292d859_20260616_080148` |
| `precrack_fatigue_mask_complete_export_630111c_20260609` | Failed setup at 2026-06-09 12:11 CST, stopped second setup at 12:17 CST, clean rerun launched Tue Jun 9 12:22 PM CST; finish checked 2026-06-09 | `01_monitor.md`; run id `pf_precrack_fatigue_mask_complete_630111c_20260609_122200` |
| `probe_driver_fullskill_8970066_20260609` | Corrected aligned-coarse launch 2026-06-09T17:44:58+01 / 2026-06-10T00:44:58+08 | `01_monitor.md`; run id `pf_probe_driver_fullskill_alignedcoarse_8970066_20260609_174404` |
| `oracle_triplet_8970066_20260609` | Launched 2026-06-09 18:27 BST; raw-pidl-g and delta/active cases stopped by 19:35 BST; download/analysis around 19:44-20:40 BST | per-case `01_monitor.md` files under oracle triplet cases |
| `oracle_alpha_fem_feedback_20260610` | Prepared 2026-06-10 16:56 BST; actual launch 2026-06-10 17:31 BST | `oracle_alpha_fem_feedback_20260610/01_monitor.md` |
| `oracle_six_run_comparison_20260610` | Six-run suite launched 2026-06-10 18:22 BST; fast cases done by 21:05 BST; slow `psi_raw_feedback` completed 2026-06-11 04:20 BST | six oracle per-case `01_monitor.md`; comparison README |
| `lagged_g_stiffness_pair_20260613` | Initial SSH blocker 2026-06-13 05:17 BST; both pair runs launched 2026-06-13 06:10 BST | `lagged_g_solver_only_20260613/01_monitor.md`; `lagged_g_stiffness_20260613/01_monitor.md` |
| `history_driver_wake_mismatch_trio_20260602` | Protocol experiments dated 2026-06-02; exact per-run launch times still need extraction | `result_check.md`, `mismatch_check.md`, and memory handoff |
| `stateTiming_onepeak_substeps_diagnostics_20260531_0601` | First state-timing jobs launched 2026-05-31 22:50 CST; head-wise diagnostics launched 2026-06-01; long field diagnostic still running at 2026-06-01 02:32 CST snapshot | `MEMORY.md`; state-timing case docs |
| `tiplocal_exp18_20260528` | Exp18 queue launched 2026-05-26 07:01 CST; summary dated 2026-05-28 | `successor_handoff.md`; `docs/tiplocal_exp18_summary_2026-05-28.md` |
| `staged_alpha_discriminator_20260530` | Initial branch and matrix launched 2026-05-30; exact minute not yet extracted | `docs/staged_alpha_discriminator_2026-05-30.md` |
| `split_trunk_discriminator_20260601` | Run log dated 2026-06-01; Mac result check dated 2026-06-02 | `docs/split_trunk_discriminator_2026-06-01.md` |
| `local_patch_discriminator_20260530` | Launched 2026-05-30; exact minute not yet extracted | `docs/local_patch_discriminator_2026-05-30.md` |
| `fbpinn_chain_discriminator_20260530` | Submitted 2026-05-30; checked on Taobo 2026-06-02; field-gate analysis completed 2026-06-02 | `docs/fbpinn_chain_discriminator_2026-05-30.md` |
| `frozen_alpha_elastic_discriminator_20260603` | Completed on Taobo 2026-06-03 | `docs/frozen_alpha_elastic_discriminator_2026-06-03.md` |
| `c1_altmin_discriminator_20260603` | Main run and follow-up branch matrix completed on Taobo 2026-06-03 | `docs/c1_altmin_discriminator_2026-06-03.md` |
| `history_driver_discriminator_20260602_0603` | Mac note 2026-06-02; Taobo launch timestamp 20260603_011115 | `docs/history_driver_discriminator_2026-06-02.md` |
| `inverse_alphaT_femmesh_softHist0_20260531` | Remote log timestamp 20260531_1707; note dated 2026-05-31 | `docs/inverse_problem_experiments_2026-05-31.md` |
| `mesh_gnn_residual_discriminator_20260616` | Offline Mac analysis dated 2026-06-16 | `docs/mesh_gnn_residual_discriminator_2026-06-16.md` |
| `m2s_framework_validation_20260531` | Validation note dated 2026-05-31 | `docs/m2s_framework_validation_2026-05-31.md` |
| `manav_reproduction_8seed_20260621` | Intent dated 2026-06-21; later analysis/handoff package dated 2026-06-24 | local archive intent and `manav_sens8seed_20260622` analysis package |
| `sdf_discontinuity_embedding_archive` | Archived 2026-06-11 | `$PROJECT/local_archive/before_strict_setting_alignment/pidl_result/sdf_discontinuity_embedding/README.md` |

## Taobo Remote Coverage Snapshot

Read-only shallow Taobo census by subagent `Locke`, 2026-06-27. Roots checked:

```text
/mnt/data2/drtao/wennie
/mnt/data2/drtao/pidl_archives
/mnt/data2/drtao/projects
/mnt/data2/drtao/runs
```

No jobs were launched, killed, moved, downloaded, tarred, or rsynced during this
remote census. Sizes are cheap top-level `du -sh` values and mtimes are Taobo
stat times.

### Remote Matches To Local Inventory

| local inventory row | Taobo remote evidence | Approx remote size | Coverage |
|---|---|---:|---|
| `femlike_irr_penalty_b70cdf3_20260626` | `/mnt/data2/drtao/wennie/pf_femlike_irr_b70cdf3_20260626_174545`; archive `/mnt/data2/drtao/pidl_archives/pf_femlike_irr_b70cdf3_20260626_174545` | 12M code/log root; 2.6G archive | matched high confidence |
| `mono_fatigue_off_f3b29cc_20260627` | `/mnt/data2/drtao/wennie/pf_mono_fatoff_f3b29cc_20260627_0044`; archive `/mnt/data2/drtao/pidl_archives/pf_mono_fatoff_f3b29cc_20260627_0044` | 13M root; 671M archive | matched high confidence |
| `softHist0_monoU02_8seed_ec32214_20260623_172416` | `/mnt/data2/drtao/wennie/pf_softHist0_monoU02_8seed_ec32214_20260623_172416`; archive `/mnt/data2/drtao/pidl_archives/pf_softHist0_monoU02_8seed_ec32214_20260623_172416` | 36M root; 4.7G archive | matched high confidence |
| `pf_softHist0_state0_seed1_*` | `/mnt/data2/drtao/wennie/pf_softHist0_state0_seed1_66b56e4_20260624_124606`; `/mnt/data2/drtao/wennie/pf_softHist0_state0_seed1_meshsync_66b56e4_20260624_124900` | 15M/9.7M roots; 696K/671M archives | matched high confidence |
| `A_hist_alpha_max_pair_analysis_20260615` | Archives for `pf_hist_alpha_max_clean2_16ba4cf_20260615_064411` and `pf_hist_alpha_max_fempretrain_16ba4cf_20260615_064915` | 506M and 519M archives | matched high confidence at subrun level |
| `A_hist_alpha_max_raw_driver_fem_pretrain_20260616` | `/mnt/data2/drtao/wennie/pf_Araw_histmax_fempretrain_a2dc123_20260616_133936`; archive `/mnt/data2/drtao/pidl_archives/pf_Araw_histmax_fempretrain_a2dc123_20260616_133936` | 594M root; 601M archive | matched high confidence |
| `F_fem_state_restart_pair_20260616_analysis` | `/mnt/data2/drtao/wennie/pf_Frestart_c60_c68_292d859_20260616_080148`; archive `/mnt/data2/drtao/pidl_archives/pf_Frestart_c60_c68_292d859_20260616_080148` | 39M root; 391M archive | matched high confidence |
| `precrack_fatigue_mask_complete_export_630111c_20260609` | `/mnt/data2/drtao/wennie/pf_precrack_fatigue_mask_complete_630111c_20260609_122200`; archive `/mnt/data2/drtao/pidl_archives/pf_precrack_fatigue_mask_complete_630111c_20260609_122200` | 537M root; 2.5G archive | matched high confidence |
| `probe_driver_fullskill_8970066_20260609` | `/mnt/data2/drtao/wennie/pf_probe_driver_fullskill_alignedcoarse_8970066_20260609_174404`; archive `/mnt/data2/drtao/pidl_archives/pf_probe_driver_fullskill_alignedcoarse_8970066_20260609_174404` | 6.3M root; 2.5G archive | matched high confidence |
| `oracle_six_run_comparison_20260610` and oracle triplet/alpha-feedback cases | `/mnt/data2/drtao/wennie/oracle_six_injections_87938e1_20260610_182154`; `/mnt/data2/drtao/wennie/oracle_alpha_feedback_fdd3984_20260610_1656`; `/mnt/data2/drtao/wennie/oracle_triplet_8970066_20260609_182141` | 15G, 3.2G, 7.0G archives | matched high confidence |
| `lagged_g_stiffness_pair_20260613` | `/mnt/data2/drtao/wennie/lagged_stiffness_pair_16ba4cf_20260613_051737`; archive `/mnt/data2/drtao/pidl_archives/lagged_stiffness_pair_16ba4cf_20260613_051737` | 5.6G root; 5.6G archive | matched high confidence |
| `staged_alpha_discriminator_20260530` | Four staged dirs under `/mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile/` | 473-527M each | matched high confidence |
| `local_patch_discriminator_20260530` | Three localPatch dirs under `/mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile/` | 503-510M each | matched high confidence |
| `fbpinn_chain_discriminator_20260530` | FBPINN dir under `/mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile/` | 613M | matched high confidence |
| `split_trunk_discriminator_20260601` | `/mnt/data2/drtao/pidl_archives/split_trunk_c1e8ac9` | 937M | matched high confidence |
| `inverse_alphaT_femmesh_softHist0_20260531` | Inverse archive under `/mnt/data2/drtao/projects/pidl-femmesh-inverse-alphaT-215c3bd/SENS_tensile/` | 545M | matched high confidence |
| `frozen_alpha_elastic_discriminator_20260603` | Frozen-alpha dir under `/mnt/data2/drtao/projects/pidl-resstiff-69bb1b2-20260603/SENS_tensile/` | 6.7M | matched high confidence |
| `c1_altmin_discriminator_20260603` | Primary alt-min dir under `/mnt/data2/drtao/projects/pidl-resstiff-69bb1b2-20260603/SENS_tensile/` | 28M | matched high confidence |
| `history_driver_wake_mismatch_trio_20260602` / `history_driver_discriminator_20260602_0603` | `/mnt/data2/drtao/projects/pidl-prefit-history-update-4360003`; `pidl-lagged-degradation-postfit-4360003`; `pidl-raw-driver-postfit-state-timing-4360003-20260602-170754`; `pidl-history-driver-23402f9-20260603`; `pidl-history-driver-ddd30da` | 51M-1.7G | matched medium-high confidence |
| `tiplocal_exp18_20260528` | `/mnt/data2/drtao/projects/phase-field-pidl-tip-local-net-18runs-f2d648`; many matching `tipLocal` archives under `/mnt/data2/drtao/pidl_archives` | 17M code/log root plus archives | matched high confidence |
| `m2s_framework_validation_20260531` | Logs under `/mnt/data2/drtao/projects/pidl-femmesh-inverse-alphaT-215c3bd/SENS_tensile/run_logs/m2s_framework_validation_softHist0_20260531*` | small log/output root | matched high confidence; not forward PIDL training |

### Remote Likely PIDL But Not Yet In Main Inventory

| Remote root | What it likely is | Inventory status |
|---|---|---|
| `/mnt/data2/drtao/wennie/pf_surrogate_smoke_ecafe0e_archive_20260625_221509` | Surrogate smoke attempt | not in main inventory |
| `/mnt/data2/drtao/wennie/pf_surrogate_smoke_fee0ccf_rsync_20260625_221322` | Surrogate smoke / rsync attempt | not in main inventory |
| `/mnt/data2/drtao/wennie/pf_surrogate_smoke_fee0ccf_20260626_051135` | Empty or failed surrogate smoke attempt | not in main inventory |
| `pf_probe_driver_clean_0148b7f_20260609_012725` and `pf_precrack_fatigue_mask_clean_*` / `pf_precrack_fatigue_mask_rsync_*` under `/mnt/data2/drtao/wennie` | Earlier probe/precrack attempts and failed or packaging reruns before the complete-export case | not atomized; should be grouped as predecessor attempts |
| `/mnt/data2/drtao/projects/pidl-allfemmesh-fb06879` and `/mnt/data2/drtao/projects/pidl-allfemmesh-fb06879-runs` | All-FEM-mesh experiment family, mtime 2026-06-04 | not in main inventory |
| `/mnt/data2/drtao/projects/pidl-field-supervision-90dd3ad` | Field-supervision experiment family | not in main inventory |
| `/mnt/data2/drtao/projects/pidl-discontinuity-f17e77e` | Discontinuity/SDF-related remote family | possible relation to local SDF archive; not confirmed |
| Older `phase-field-pidl-adapthist-*`, `phase-field-pidl-hardirr-*`, `phase-field-pidl-tip-local-net-68871eb`, and `phase-field-pidl-tip-local-net-422a368` roots | Older adaptive-history, hard-irreversibility, and tip-local families | only partially covered by current inventory |

### Local Rows Not Found Or Not Expected On Taobo

| local inventory row | Taobo status |
|---|---|
| `mesh_gnn_residual_discriminator_20260616` | Mac offline analysis; no Taobo run expected or found |
| `sdf_discontinuity_embedding_archive` | No exact remote `sdf_discontinuity_embedding` match in shallow pass; possible adjacent `/mnt/data2/drtao/projects/pidl-discontinuity-f17e77e` |
| `manav_reproduction_8seed_20260621` | Remote workspace found at `/mnt/data2/drtao/wennie/pf_manav_sens8seed_ec32214_20260621_214002` (6.4G), but no separate matching `pidl_archives/pf_manav...` top-level path found |
| `stateTiming_onepeak_substeps_diagnostics_20260531_0601` | Family roots found (`state_timing_9f5c242`, `state_timing_4db4674`, `pf_stateTiming_until_fracture_5fa9dd6...`), but exact local case names were not traced through all nested archives |
| Local `upload_code/`, OneDrive handoffs, historical worktrees | Not atomized against Taobo in this pass |

### Active Taobo PIDL Visibility

At the read-only snapshot:

- no `tmux` sessions were listed;
- no active `drtao` PIDL/Python training process was visible;
- two active GPU processes were owned by `root`, not `drtao` (`angle_main.py`
  and a `uvicorn det_main:service` process), and did not look like PIDL.

This is visibility evidence only, not a machine-wide guarantee that no detached
or non-matching job exists.

## Main Inventory

| case_id | Path / asset endpoint | Time | Producer machine | Git commit | Runner / script | Config / setting | Protocol | Strict alignment? | Data available | Why run this experiment | Key change | Conclusion | Credibility | Next action |
|---|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|
| `femlike_irr_penalty_b70cdf3_20260626` | `$PROJECT/local_archive/after_strict_setting_alignment/pidl_result/Alignment_check2_cyclic/PIDL_cyclic_012/cases/femlike_irr_penalty_b70cdf3_20260626/` | 2026-06-26/27 | Taobo GPU | `b70cdf3` | `SENS_tensile/run_fem_mesh_probe_driver_umax.py` | Max-history, `current_active`, retained substeps `[0.25,0.5,0.75,1,0]`, `fem_gp_tri3_g_mean`, FEM-like GP irreversibility penalty | Alignment Check 2 cyclic, five-substep state mapping | yes | Full case notes, logs, download verification, capability file, regenerated analysis, tables, figures | Test whether FEM-like PIDL irreversibility reduction closes the mechanism gap | Enable `numr_dict["irreversibility_penalty"]` with `mode=fem_gp_tri3` and FEM-like history-driver reduction | Penetration gate passed at PIDL steps 398/401, but corrected state-mapped field alignment remains mixed; c1 history/driver residual and history-dominated gradients remain | supporting / diagnostic | Use regenerated diagnostics as clean case record; separate crack-tip active-front mismatch from full-field left-precrack outliers before any new training |
| `mono_fatigue_off_f3b29cc_20260627` | `$PROJECT/local_archive/after_strict_setting_alignment/pidl_result/Alignment_check2_monotonic/PIDL_mono_fatigue_off_U02/cases/mono_fatigue_off_f3b29cc_20260627/` | 2026-06-27 | Taobo GPU | `f3b29cc` | `SENS_tensile/run_fem_mesh_monotonic_fatigue_off.py` | Fatigue off, monotonic `U=0.2`, nonuniform displacement sequence | Strict monotonic control | yes | Full case notes, logs, capability file, monotonic step/loss/energy tables | Establish a non-fatigue monotonic control under the current strict soft-hist0 FEM mesh setup | Disable fatigue and run monotonic loading to `U=0.2` | Completed 24 steps; right-boundary penetration occurs around `U=0.140--0.145`; useful non-fatigue control | supporting / diagnostic | If field-level FEM comparison is needed, compare by load value, not cyclic state label |
| `softHist0_monoU02_8seed_ec32214_20260623_172416` | `$PROJECT/local_archive/after_strict_setting_alignment/pidl_result/softHist0_monoU02_8seed_ec32214_20260623_172416/` | 2026-06-23 | Taobo GPU dispatcher | `ec32214` | `SENS_tensile/run_fem_mesh_monotonic_fatigue_off.py` | Strict FEM-mesh soft-hist0 monotonic fatigue-off, seeds 1--8 | Chapter 3 monotonic alignment B | yes | Intent, data capability, logs, decision, energy tables, figures | Build an eight-seed scalar energy/event comparison against the soft-hist0 FEM monotonic curve | Multi-seed run under current strict monotonic fatigue-off setup | Mixed diagnostic support: all eight processes returned, seven finite traces; event window matches FEM around `U=0.140--0.145`, but seed 6 NaN and fields are not verified | supporting | Rerun seed 6 or replacement seed before claiming an eight-seed aggregate |
| `pf_softHist0_state0_seed1_66b56e4_20260624_124606` and `pf_softHist0_state0_seed1_meshsync_66b56e4_20260624_124900` | `$PROJECT/local_archive/after_strict_setting_alignment/pidl_result/pf_softHist0_state0_seed1_66b56e4_20260624_124606/`; `$PROJECT/local_archive/after_strict_setting_alignment/pidl_result/pf_softHist0_state0_seed1_meshsync_66b56e4_20260624_124900/` | 2026-06-24 | Taobo GPU | `66b56e4` | `SENS_tensile/run_fem_mesh_monotonic_fatigue_off.py` | Strict monotonic soft-hist0 seed 1 | State0 export verification | yes | Intent and raw/log folders; no decision file found in first pass | Verify explicit `state0_initial_unloaded_prehistory` export before the first training/load solve | Add pre-training state0 export; retry copied missing untracked mesh assets | First launch exported state0 but failed at mesh loading; retry preserves same code/settings with mesh sync | diagnostic / incomplete | Write a decision file after verifying logs and state0 fields |
| `A_hist_alpha_max_pair_analysis_20260615` | `$PROJECT/local_archive/after_strict_setting_alignment/pidl_result/A_hist_alpha_max_pair_analysis_20260615/analysis/decision.md` plus sibling coarse/FEM-pretrain case folders | 2026-06-15 | Taobo GPU | `16ba4cf` | `SENS_tensile/run_fem_mesh_umax.py` | Latest soft-hist0 diffuse-precrack reverseBC, `hist_alpha=max(old,current)` | A ablation / crack-tip lag | yes | Intent, data capability, logs, pair analysis tables, decision | Test whether monotone damage history and FEM-aligned pretraining reduce PIDL/FEM crack-tip mismatch | Replace overwrite with `hist_alpha=max(previous,current)`; compare coarse pretrain vs FEM pretrain | Stored history monotone in both runs, but neither improves right-tip alignment; both first hit c80 and stop c83 | negative / diagnostic | Do not repeat A alone; use as baseline for driver ablations |
| `A_hist_alpha_max_raw_driver_fem_pretrain_20260616` | `$PROJECT/local_archive/after_strict_setting_alignment/pidl_result/A_hist_alpha_max_raw_driver_fem_pretrain_20260616/` | 2026-06-16 | Taobo GPU | `a2dc123` | `SENS_tensile/run_fem_mesh_umax.py` | A FEM-pretrain baseline plus raw history driver | Driver-gate diagnostic | yes | Intent, data capability, logs, analysis decision | Test whether degraded active driver is the remaining gate after monotone `hist_alpha` | Set `history_driver_mode=raw` while keeping FEM pretraining and max-history fixed | Negative as a fix: event advances one cycle and tip error partly improves, but c69 remains far behind and scalar history explodes | negative / diagnostic | Do not expand plain raw-driver production; only try bounded/mixed driver with same c69 field gate |
| `F_fem_state_restart_pair_20260616_analysis` | `$PROJECT/local_archive/after_strict_setting_alignment/pidl_result/F_fem_state_restart_pair_20260616_analysis/decision.md` plus c60/c68 restart case folders | 2026-06-16 | Taobo GPU | `292d859` | FEM-state restart runner | Restart from FEM c60 or FEM c68 state toward c72 | Near-critical sufficiency discriminator | yes | Restart case folders, pair decision, element-tip summary | Test whether PIDL can propagate if handed a sufficiently near-critical FEM state | Start PIDL from FEM c60 or c68 instead of its own trajectory state | c68 restart reaches FEM c69 almost exactly; c60 restart still lags, so the problem is path-history/state trajectory before c68, not one-step propagation inability | supporting / diagnostic | Use in writing as causal evidence for accumulated trajectory error |
| `precrack_fatigue_mask_complete_export_630111c_20260609` | `$PROJECT/local_archive/after_strict_setting_alignment/pidl_result/Alignment_check2_cyclic/PIDL cyclic 012/cases/precrack_fatigue_mask_complete_export_630111c_20260609/` | 2026-06-09/10 regenerated | Taobo GPU | `630111c` | strict cyclic export runner | Precrack fatigue/history mask, complete diagnostics | Alignment Check 2 cyclic | yes | Intent, logs, raw archive, regenerated residual diagnostics, mask audit, decision | Produce a complete diagnostic export for retained precrack fatigue/history mask | Enable complete state/field export for the precrack-fatigue-mask case | Mixed: corrected mapping applied, c1/c69 ambiguity resolved, but mechanism still not fully aligned; history/driver residual remains | diagnostic | Use regenerated state-mapped diagnostics; do not claim history/active driver is absent near precrack |
| `probe_driver_fullskill_8970066_20260609` | `$PROJECT/local_archive/after_strict_setting_alignment/pidl_result/Alignment_check2_cyclic/PIDL cyclic 012/cases/probe_driver_fullskill_8970066_20260609/` | 2026-06-09/10 regenerated | Taobo GPU | `8970066` | probe-driver rerun | Strict aligned coarse FEM-mesh with stress/strain mapped states and gradient diagnostics | Alignment Check 2 cyclic | yes | Intent, logs, raw archive, regenerated residual diagnostics, decision | Create a high-capability probe-driver case with stress/strain and pre-history-refresh gradient diagnostics | Add stress/strain mapped states plus `E_el/E_d/E_hist` gradient diagnostics | Mixed: mapping fixed and audit added, but c1 history/driver residual and history-dominated gradients remain | diagnostic | Use as clean probe-driver case record |
| `oracle_six_run_comparison_20260610` | `$PROJECT/local_archive/after_strict_setting_alignment/pidl_result/Alignment_check2_cyclic/PIDL cyclic 012/cases/_oracle_six_run_comparison_20260610/` | 2026-06-10 | Taobo GPU | `87938e1` family | `SENS_tensile/run_fem_mesh_oracle_field_umax.py` | Six oracle injections: `hard_hist_alpha`, `alpha_bar_state`, `psi_raw_feedback`, `psi_prev`, `f_fatigue`, `fem_g_stiffness` | Alignment Check 2 cyclic, explicit state mapping | yes | README, six-run summary CSV, crack progression table, c1/c69 residual matrices, figures | Isolate which hidden state/feedback channel can force penetration | Inject one oracle channel at a time while keeping the rest PIDL-evolved | Penetration-positive: hard hist-alpha, alpha-bar state, psi-raw feedback. Negative/partial: psi-prev, f-fatigue, FEM g-stiffness. Still not full field alignment | supporting / diagnostic | Use as causal channel split; do not describe positive penetration as full alignment |
| `lagged_g_stiffness_pair_20260613` | `$PROJECT/local_archive/after_strict_setting_alignment/pidl_result/Alignment_check2_cyclic/PIDL cyclic 012/cases/lagged_g_solver_only_20260613/`; `$PROJECT/local_archive/after_strict_setting_alignment/pidl_result/Alignment_check2_cyclic/PIDL cyclic 012/cases/lagged_g_stiffness_20260613/` | 2026-06-13 | Taobo GPU | `16ba4cf` | `SENS_tensile/run_fem_mesh_oracle_field_umax.py` | Lagged previous-alpha stiffness, solver-only vs coupled history policy | Alignment Check 2 cyclic | yes | Intent, analysis README, regenerated state-mapped diagnostics, decisions | Test whether using previous irreversible damage/history in stiffness changes mechanics redistribution and penetration | Use `g(hist_alpha_previous)` in solver only or coupled post-update | No log-confirmed penetration for either case; field alignment remains mixed and final gradients remain history-dominated | negative / diagnostic | Keep regenerated diagnostics as clean record; do not treat lagged stiffness as solved |
| `history_driver_wake_mismatch_trio_20260602` | `$UPLOAD/.codex/worktrees/pidl-state-timing-diagnostic/_analysis_fem_mechanism_20260528/experiments/{pre_fit_history_update_active_degraded_4360003,lagged_degradation_postfit_4360003,raw_driver_postfit_state_timing_4360003}/` | 2026-06-02 | Taobo GPU, analyzed on Mac | `4360003` protocol family | `SENS_tensile/run_fem_mesh_state_timing_umax.py` and related runners | N4 early-state timing/history-driver diagnostics | Wake mismatch / state timing | yes | `SYNC_SOURCES.md`, logs, `result_check.md`, `mismatch_check.md`, wake-band metrics, figures | Bracket whether wake mismatch comes from history timing or driver definition | Pre-fit active-degraded, lagged-degraded post-fit, raw-driver post-fit state-timing | Pre-fit helps but too weak; lagged/raw overshoot or explode; plain raw is a negative upper-bound, not an untried fix | negative / diagnostic | Only rerun raw if a protocol-comparable c0-c3 artifact is explicitly needed |
| `stateTiming_onepeak_substeps_diagnostics_20260531_0601` | `$PROJECT/local_archive/after_strict_setting_alignment/pidl_result/Alignment_check2_cyclic/PIDL cyclic 012/cases/stateTiming_onepeak_untilFrac_Nphys100_Nstep100/`; `$PROJECT/local_archive/after_strict_setting_alignment/pidl_result/Alignment_check2_cyclic/PIDL cyclic 012/cases/stateTiming_substeps025_untilFrac_Nphys120_Nstep600/` | 2026-05-31/06-01 | Taobo GPU | `9f5c242`, `4db4674` family | `SENS_tensile/run_fem_mesh_state_timing_umax.py` | One-peak and five-substep state-timing exports with gradient/head-wise diagnostics | State timing / mapping | yes | Case folders with docs/logs/raw data; research memory has mapping conclusions | Audit whether timing/export cadence explains FEM/PIDL divergence | Export pre/post history-refresh states and gradient balance under one-peak and substep schedules | Established critical mapping rules and showed timing bookkeeping matters, but did not close field mismatch | supporting / diagnostic | Preserve mapping rule; compare by state label, never raw PIDL index |
| `tiplocal_exp18_20260528` | `$UPLOAD/docs/tiplocal_exp18_summary_2026-05-28.md` and `$UPLOAD/docs/figures/tiplocal_exp18_20260528/` | 2026-05-26/28 | Taobo GPU | `229f5a0` base plus patch | `SENS_tensile/run_tip_local_net_S1_umax.py` and S2 runners | 3 architectures x 6 conditions, tip-local heads | Representation-localization discriminator | mostly pre-current strict, but FEM-referenced | Summary CSVs, field montage, diagnostics plots | Test whether compact moving tip-local correction heads fix field-level mismatch | Add MLP/Fourier/SIREN local correction heads; vary output mode and S1/S2/adaptive history | Closed as field-level route: scalar timing changes, but fields remain centerline/right-boundary dominated | negative / diagnostic | Do not launch broad local-head sweeps until field metric is fixed |
| `staged_alpha_discriminator_20260530` | `$UPLOAD/docs/staged_alpha_discriminator_2026-05-30.md` | 2026-05-30 | Taobo GPU | strict FEM-mesh branch family | `SENS_tensile/run_fem_mesh_staged_alpha_umax.py` | uv-head, alpha-head, joint staged schedules | Coupled optimization path discriminator | yes | Shared doc, scalar/event table, field-gate ratios | Test whether per-cycle optimization path, not mesh/reference, causes gap | Stage uv and alpha output rows before joint solve | Negative: head-staging shifts `N_f` but keeps active `psi+` and `alpha_bar` far from FEM; no-joint is pathological | negative / diagnostic | Close head-staging; move to stronger local representation/history formulation tests |
| `split_trunk_discriminator_20260601` | `$UPLOAD/docs/split_trunk_discriminator_2026-06-01.md` | 2026-06-01/02 | Taobo GPU | `c1e8ac9` | `SENS_tensile/run_fem_mesh_staged_alpha_umax.py` with `SplitTrunkNet` | True separate `uv_net` and `alpha_net` | Coupled optimization path discriminator | yes | Shared doc with remote workspace/archive/log references | Check whether true split trunks and separate staged optimizer were already tried | Replace row-head staging proxy with independent uv/alpha trunks | Negative: event slightly earlier but active-driver/history trajectory remains wrong | negative / diagnostic | Do not propose split trunks again unless materially different |
| `local_patch_discriminator_20260530` | `$UPLOAD/docs/local_patch_discriminator_2026-05-30.md` | 2026-05-30 | Taobo GPU | `a6818cf` | `SENS_tensile/run_fem_mesh_local_patch_umax.py` | Additive local crack-tip patch, all/alpha/uv output modes | Representation-localization discriminator | yes | Shared doc, remote reduction tables | Test whether an independently trained compact tip patch fixes the strict FEM-mesh field gap | Add local patch MLP inside a radial window with patch warm-up and joint RPROP | Weak/negative: baseline-like or worse; still right-boundary saturation and active driver remains deficient | negative / diagnostic | If revisiting, use local subdomains carrying raw field, not small additive correction |
| `fbpinn_chain_discriminator_20260530` | `$UPLOAD/docs/fbpinn_chain_discriminator_2026-05-30.md` | 2026-05-30/06-02 | Taobo GPU | `a4b8380` | `SENS_tensile/run_fem_mesh_fbpinn_umax.py` | Six overlapping local patches along the crack path | Representation-localization discriminator | yes | Shared doc, result check, FEM n_step2 field-gate analysis | Test a true domain-decomposed representation after additive patch failed | Blend global MLP with overlapping local subnetworks that carry the raw field | Diagnostic: propagation mode changes and no boundary event by j99, but active driver remains off-location and not FEM-like | diagnostic / negative | Keep as evidence that representation changes mode but not mechanism closure |
| `frozen_alpha_elastic_discriminator_20260603` | `$UPLOAD/docs/frozen_alpha_elastic_discriminator_2026-06-03.md` | 2026-06-03 | Taobo GPU | residual-stiffness branch | `SENS_tensile/run_fem_mesh_frozen_alpha_elastic_probe.py` | Fixed analytic alpha, displacement-only elastic solve | C1 micro-solve discriminator | yes | Shared doc, archive reference, c1 ratios | Check if first-cycle raw `psi` mismatch exists before alpha/fatigue feedback | Freeze alpha to soft-hist0 initial precrack and optimize only displacement | Frozen-alpha elastic is too cold, while coupled c1 is too hot; mismatch is created by coupled elastic-damage path | supporting / diagnostic | Use as lead-in to c1 alternate-minimization result |
| `c1_altmin_discriminator_20260603` | `$UPLOAD/docs/c1_altmin_discriminator_2026-06-03.md` | 2026-06-03 | Taobo GPU | residual-stiffness branch | `SENS_tensile/run_fem_mesh_c1_altmin_probe.py` | Freeze alpha/u-v in alternating substages; branch matrix follows | C1 micro-solve discriminator | yes | Shared doc, local analysis package paths, scalar/field ratios | Identify when c1 hotspot appears under FEM-like alternate minimization | Alternate fixed-alpha uv solves and fixed-uv alpha solves; vary alpha authority/LR/stagger size | Useful negative: uv re-equilibration around updated alpha rebuilds raw hotspot; shorter alpha or smaller staggers do not fix it | supporting / diagnostic | Target irreversibility/update formulation or local stiffness/degradation response, not epoch schedule |
| `history_driver_discriminator_20260602_0603` | `$UPLOAD/docs/history_driver_discriminator_2026-06-02.md`; local artifacts under `$UPLOAD/_analysis_fem_mechanism_20260528/history_driver_event_diagnostics/` | 2026-06-02/03 | Taobo GPU | `23402f9`; older raw branch `ddd30da` | history-driver runners | `current_active`, `lagged_g`, `raw` fatigue-history drivers | History/active-driver discriminator | yes | Shared doc, local event diagnostics CSV/figures | Test whether current-cycle degradation starves fatigue history | Change only post-solve history refresh driver | Raw/lagged can inflate history or shift timing but do not produce FEM-like process-zone evolution | negative / diagnostic | Do not treat raw driver as untried; bounded/mixed driver only if explicitly gated |
| `inverse_alphaT_femmesh_softHist0_20260531` | `$UPLOAD/docs/inverse_problem_experiments_2026-05-31.md` | 2026-05-31 | Taobo GPU | `215c3bd` | `SENS_tensile/run_fem_mesh_inverse_alphaT_umax.py` | Trainable `alpha_T`, FEM field target K=69 | Inverse parameter identifiability | yes | Shared doc, remote run/log/archive references, raw/active split table | Test whether inverse loop can recover a meaningful fatigue parameter under fair alignment | Make `alpha_T` trainable with bounds and FEM damage target | Negative: `alpha_T` collapses to 0.05, causing premature fracture and not repairing active-driver field | negative / diagnostic | Use as identifiability failure; rerun only after forward field mechanism improves |
| `mesh_gnn_residual_discriminator_20260616` | `$UPLOAD/docs/mesh_gnn_residual_discriminator_2026-06-16.md` | 2026-06-16 | Mac offline analysis | current soft-hist0 assets | `SENS_tensile/analyze_mesh_gnn_residual_discriminator.py` | Graph/MLP residual sidecar for `psi_active` and `alpha_bar` | Offline residual discriminator | yes, analysis-only | Shared doc and generated experiment output path | Test whether local mesh-neighbourhood information explains residuals before online changes | Train small graph residual model against FEM-PIDL log residuals | Mixed: graph improves held-out `psi_active` residual, but not near-tip closure; `alpha_bar` correction is negative | diagnostic | Only revisit as `psi_active` sidecar with stricter holdouts |
| `m2s_framework_validation_20260531` | `$UPLOAD/docs/m2s_framework_validation_2026-05-31.md` | 2026-05-31 | Taobo/Mac analysis | not a PIDL training run | `SENS_tensile/run_m2s_synthetic_validation.py` | Synthetic FEM truth, RUL prediction without cycle index | Framework validation | adjacent, not PIDL forward | Shared doc, remote output summary CSV/MD | Validate smallest M2S layer on synthetic FEM truth | Use progressively richer observation sets to predict remaining life | Feasible but too easy on one trajectory; does not prove hidden state fields add independent prognostic value | supporting | Next rung needs multi-trajectory FEM benchmark |
| `manav_reproduction_8seed_20260621` | `$PROJECT/local_archive/before_strict_setting_alignment/pidl_result/manav_reproduction_8seed_20260621/`; later analysis at `$PROJECT/local_archive/after_strict_setting_alignment/pidl_result/manav_sens8seed_20260622/` | 2026-06-21/24 | Mac/Taobo depending package stage | example/source snapshot | `examples/SENS_tensile` | Original Manav-style monotonic SEN, seeds 1--8, fatigue off | Backbone sanity check | no, before strict | Intent, logs/scripts; later analysis tables and FEM handoff | Check whether local Manav-style PIDL backbone reproduces expected monotonic SEN behavior | Run original-style example over eight seeds | Useful backbone sanity evidence, not a retained-fatigue or strict-alignment benchmark | supporting / diagnostic | Keep separate from strict evidence; use only with claim boundary |
| `sdf_discontinuity_embedding_archive` | `$PROJECT/local_archive/before_strict_setting_alignment/pidl_result/sdf_discontinuity_embedding/` | archived 2026-06-11 | Mac/Windows historical | local branch ahead by `fa6e5b2`, `1b538d8` at archive time | SDF/ribbon analysis and run scripts | SDF ribbon input, `uv_only` split, Umax/seed variants | Representation-localization legacy | no, before strict | README, logs, references, moved `hl_*` runs | Preserve SDF/discontinuity-ribbon experiment outputs and scripts | Add localized SDF ribbon input and `uv_only` split | Diagnostic/partial legacy evidence only; predates strict setting alignment | diagnostic | Decide whether two local commits should be pushed/merged before removing worktree |

## Unexpanded Candidate Roots

These roots were discovered but are not fully atomized into one row per run yet.
They should be expanded by reading the local README/decision files first, not by
moving or deleting payloads.

| Root | What it likely contains | Next extraction rule |
|---|---|---|
| `$PROJECT/local_archive/after_strict_setting_alignment/pidl_result/Alignment_check2_cyclic/PIDL cyclic 012/cases/` | Many standardized oracle/probe/state-timing case folders | Add one row per case only when `00_intent.md` and `analysis/decision.md` both exist, or mark intent-only. |
| `$PROJECT/local_archive/after_strict_setting_alignment/pidl_result/upload_code/` | Archived previous `upload code` generated PIDL outputs and result packages | Split by README and package owner; do not mix raw payloads with shared docs. |
| `$PROJECT/local_archive/before_strict_setting_alignment/pidl_result/upload_code/` | Pre-strict generated PIDL payloads | Keep as legacy unless settings are mapped to strict references. |
| `$PROJECT/upload code/.claude/worktrees/` | Many historical code branches and local analysis branches | Create `docs/branch_inventory.md` before considering cleanup. |
| `$PROJECT/upload code/.codex/worktrees/` | Current diagnostic worktrees, including history-driver and state-timing | Preserve until corresponding main-doc inventory rows are complete. |
| `$ONEDRIVE/` | FEM handoffs, PIDL handoffs, zip packages, Windows-produced packages | Cross-reference by package id; classify as FEM reference, PIDL run, or handoff-only. |
| `$PROJECT/local_archive/parent_git_backup_20260611/` | Large parent backup | Not a PIDL experiment by itself; inspect only if provenance is missing elsewhere. |

## Immediate Cleanup Rules

Do not delete or move anything yet.

First-pass priorities:

1. Add decision files for intent-only cases such as the 2026-06-24 state0 export retries.
2. Expand `Alignment_check2_cyclic/PIDL cyclic 012/cases/` into individual rows where each case has both intent and decision.
3. Create a branch/worktree inventory before touching `.claude/worktrees` or `.codex/worktrees`.
4. Keep all pre-strict archives clearly separated from strict-alignment claims.
5. For every future PIDL run, require an asset endpoint: either a tracked `docs/` summary or a local archive README/decision.
