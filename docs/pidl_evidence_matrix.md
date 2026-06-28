# PIDL Evidence Matrix

Date: 2026-06-28

Purpose: turn the PIDL experiment inventory into claim-level research evidence.
The inventory answers "what exists"; this matrix answers "what these runs
jointly prove, rule out, or leave uncertain".

Primary source:

- `docs/pidl_experiment_inventory.md`
- local case decisions and READMEs under
  `$PROJECT/local_archive/after_strict_setting_alignment/`
- Taobo gap import README under
  `$PROJECT/local_archive/taobo_remote_gap_census_20260627/`

Credibility labels follow the inventory convention:

```text
canonical      trusted evidence used directly for a paper/thesis claim
supporting     useful supporting evidence, usually with caveats
diagnostic     mechanism/debugging evidence
negative       useful failed attempt
inconclusive   preserved for traceability only
```

## Executive Read

The current PIDL evidence points to a path-history/state-trajectory problem,
not a simple cycle-index, mesh, scalar fatigue-threshold, or architecture-only
problem.  The strongest causal evidence is:

1. state mapping is now pinned for the retained five-substep cyclic protocol;
2. restart/oracle runs show PIDL can penetrate if handed a sufficiently
   near-critical FEM state or irreversible history/damage feedback;
3. raw/lagged drivers, local heads, split trunks, patches, FBPINNs,
   hard/simple irreversibility fixes, field supervision, and scalar inverse
   `alpha_T` calibration do not by themselves recover FEM-like field evolution.

Safe high-level claim:

```text
In the strict soft-hist0 FEM-mesh setting, PIDL can match or shift scalar event
timing, but the unresolved gap is the local degraded active-driver/history
feedback trajectory.  Penetration-positive oracle/restart tests show the solver
is not intrinsically unable to propagate from a near-critical state; negative
driver, representation, irreversibility, and supervision tests show that
single-lever fixes do not close the field-level mechanism.
```

Unsafe claims:

- Do not call any oracle-positive case "full FEM/PIDL alignment".
- Do not use `N_f` or boundary penetration alone as success.
- Do not mix monotonic controls into cyclic fatigue mechanism claims.
- Do not treat pre-strict local-head/SDF/hard-irreversibility results as
  current strict evidence without the strict-alignment caveat.
- Do not claim hidden M2S state-driver fields outperform visible damage from the
  single-trajectory synthetic validation.

## Claim Matrix

| Mechanism question | Short answer | Key evidence | Credibility | Next action |
|---|---|---|---|---|
| Monotonic controls and Case C | Latest monotonic fatigue-on code path does not accumulate fatigue history; monotonic fracture is a separate high-load control. | `mono_onoff_latest_ddc22eb_20260627_234645`; `mono_fatigue_off_f3b29cc_20260627`; `softHist0_monoU02_8seed_ec32214_20260623_172416` | supporting / diagnostic | Use the completed soft-hist0 FEM energy comparison only as load-indexed scalar evidence. |
| State timing and mapping | Five-substep cyclic comparisons must use explicit state labels; clean regenerated cyclic records still show history/driver residuals after mapping is fixed. | `stateTiming_until_fracture_5fa9dd6_20260608`; `stateTiming_onepeak_substeps_diagnostics_20260531_0601`; `probe_driver_fullskill_8970066_20260609`; `precrack_fatigue_mask_complete_export_630111c_20260609`; `pf_softHist0_state0_seed1_*` | canonical for mapping; diagnostic for runs | Use the new retrospective decisions; exact substep event NPZ still needs posthoc export only if figures require it. |
| History driver / wake mismatch | Raw or lagged driver variants change history magnitude and timing but are not clean fixes. | `history_driver_discriminator_20260602_0603`; `history_driver_wake_mismatch_trio_20260602`; `A_hist_alpha_max_raw_driver_fem_pretrain_20260616`; `lagged_g_stiffness_pair_20260613` | negative / diagnostic | Treat bounded/mixed driver as a new gated design only, not as "raw untried". |
| C1 coupled solve / stiffness feedback | The first-cycle hotspot is created by coupled elastic-damage feedback, not by initial alpha/precrack alone or epoch scheduling alone. | `frozen_alpha_elastic_discriminator_20260603`; `c1_altmin_discriminator_20260603` | supporting / diagnostic | Use as the bridge from early-field mismatch to trajectory/history error. |
| Oracle and restart causal channels | Under oracle/restart intervention, irreversible state/history feedback and near-critical state are sufficient to trigger penetration; stiffness or fatigue factor alone is not. | `oracle_six_run_comparison_20260610`; `oracle_hard_hist_alpha_20260610`; `oracle_alpha_bar_state_20260610`; `oracle_psi_raw_feedback_20260610`; `oracle_f_fatigue_20260610`; `oracle_fem_g_stiffness_20260610`; `F_fem_state_restart_pair_20260616_analysis` | supporting / diagnostic | Use as the main causal split, with the oracle caveat attached. |
| Irreversibility / history update | Simple monotone history and hard transforms do not solve the field gap; FEM-like irreversibility penalty is useful but mixed. | `A_hist_alpha_max_pair_analysis_20260615`; `femlike_irr_penalty_b70cdf3_20260626`; `hardirr_41e0bf1_20260524`; `hardirr_6525a9f_20260525` | mixed supporting / negative | Do not rerun hard transform without bounded numerical guard and field gate. |
| Representation / localization | Local heads, patches, split trunks, FBPINNs, all-FEM-mesh and SDF/XFEM features shift mode/timing but do not close active-driver/history localization. | `tiplocal_exp18_20260528`; `staged_alpha_discriminator_20260530`; `split_trunk_discriminator_20260601`; `local_patch_discriminator_20260530`; `fbpinn_chain_discriminator_20260530`; `allfemmesh_softHist0_fb06879_20260604`; `discontinuity_sdf_xfem_uvonly_f17e77e_20260601` | negative / diagnostic | Do not launch another architecture sweep without a predeclared active-driver/process-zone gate. |
| Field supervision and direct forcing | Direct hidden-field forcing is too aggressive or incomplete unless normalized and gated. | `field_supervision_90dd3ad_20260601`; `oracle_triplet_8970066_20260609`; `oracle_f_fatigue_20260610` | negative / diagnostic | Use the field-supervision and oracle-triplet decisions; rerun only with normalized/gated targets and an active-driver/process-zone gate. |
| Inverse / scalar calibration | Scalar fatigue-parameter inversion compensates event timing by collapsing `alpha_T`; it does not repair the active-driver field. | `inverse_alphaT_femmesh_softHist0_20260531` | negative / diagnostic | Reuse only after a forward field mechanism improves. |
| Surrogate / M2S adjacent work | Useful for framework/tooling, not forward PIDL mechanism closure. | `m2s_framework_validation_20260531`; `mesh_gnn_residual_discriminator_20260616`; `taobo_surrogate_smoke_fee0ccf_ecafe0e_20260625_26` | supporting for framework; diagnostic/tooling for PIDL | Next M2S rung needs multi-trajectory FEM; mesh-GNN only as targeted `psi_active` sidecar. |

## Mechanism Notes

### 1. Monotonic Controls / Case C

Claim:

- `loading_type=monotonic` with fatigue enabled does not accumulate fatigue
  history in the latest `ddc22eb` code path.
- Monotonic fracture should be treated as high-load monotonic damage evidence,
  not as cyclic fatigue mechanism evidence.

Evidence:

- `mono_onoff_latest_ddc22eb_20260627_234645`
  - Fatigue-on final diagnostics show `alpha_bar/hist_fat max=0`, `f_min=1`,
    and `f_mean=1`.
  - Common fatigue-on/off checkpoints 0..22 have identical SHA256 hashes
    according to `03_data_capability.md` and `analysis/04_posthoc_result.md`.
  - Fatigue-off completed all 24 load steps to `U=0.2`.
  - Fatigue-on first boundary fracture appeared at `U=0.145` and confirmed by
    `U=0.195`.
  - The practical difference is stop policy: fatigue-off follows the same
    checkpoint trajectory through `U=0.195` and runs the one extra scheduled
    step to `U=0.2`.
  - FEM soft-hist0 scalar energy comparison now lives at
    `analysis/05_fem_comparison_result.md`; the generated table and figure
    compare latest PIDL on/off against the FEM soft-hist0 VTK/postprocessed
    energy curve by prescribed displacement `U`.
  - In that scalar comparison, FEM soft-hist0 peaks in `E_el` at `U=0.140`,
    while the latest PIDL on/off curves peak at `U=0.135`; all three have their
    largest `E_el` drop over `U=0.140 -> 0.145`.
- `mono_fatigue_off_f3b29cc_20260627`
  - Current strict monotonic fatigue-off control; event around `U=0.140--0.145`.
- `softHist0_monoU02_8seed_ec32214_20260623_172416`
  - Seven finite traces out of eight; useful but not a clean eight-seed aggregate
    until seed 6 is replaced or explained.

Caveats:

- The new FEM comparison is scalar energy only, not a pointwise field residual
  or force-displacement validation.
- The FEM reference is the legacy diagnostic soft-hist0 VTK/postprocessed energy
  table with a state0 anchor; do not mix it with current brittle SENS or raw FEM
  fatigue-kernel `Fract_en` without restating the energy convention.
- Use load value, not cyclic state label, for monotonic comparisons.

Credibility: supporting / diagnostic.

### 2. State Timing And Mapping

Claim:

- Mapping is a first-class evidence condition.  For retained five-substep
  cyclic runs, use:

```text
cN_peak     -> PIDL step 5*(N-1)+3
cN_unloaded -> PIDL step 5*(N-1)+4
```

- Do not treat PIDL step 0 as unloaded state0 in five-substep runs unless an
  explicit `state0_initial_unloaded_prehistory` export exists.

Evidence:

- `stateTiming_onepeak_substeps_diagnostics_20260531_0601`
  - Established timing/mapping rules and showed bookkeeping affects c1/c69
    interpretation.
- `stateTiming_until_fracture_5fa9dd6_20260608`
  - One-peak pretrain-off run first detected fracture at cycle 82 and confirmed
    at cycle 85.
  - Five-substep pretrain-off run first detected at global index 408 and
    confirmed at 411, physical cycle about 81.6/82.2.
  - Exact event `.npz` snapshots at 408-411 were not scheduled before the early
    stop; this is an explicit limitation.
  - Retrospective decisions now live under the two existing case folders:
    `stateTiming_onepeak_untilFrac_Nphys100_Nstep100/analysis/decision.md` and
    `stateTiming_substeps025_untilFrac_Nphys120_Nstep600/analysis/decision.md`.
- `pf_softHist0_state0_seed1_*`
  - Validates explicit `state0_initial_unloaded_prehistory` export path for
    monotonic soft-hist0.
  - Retrospective decisions now live in both the first-attempt folder and the
    meshsync retry folder.
- `probe_driver_fullskill_8970066_20260609` and
  `precrack_fatigue_mask_complete_export_630111c_20260609`
  - Clean regenerated state-mapped strict cyclic records.
  - Mapping and diagnostic capability were fixed, but c1/c69 history-driver
    residuals and mixed field alignment remain.

Caveats:

- Older one-state-per-cycle claims need their timing assumption stated.
- Posthoc state0 reconstruction is not the same as native in-loop export.

Credibility: canonical for mapping protocol; diagnostic for the run family.

### 3. History Driver / Wake Mismatch

Claim:

- Changing the history-driver definition changes the wake and scalar trajectory,
  but raw and lagged variants do not by themselves repair FEM-like
  process-zone evolution.

Evidence:

- `history_driver_discriminator_20260602_0603`
  - Compared `current_active`, `lagged_g`, and `raw` history update drivers.
  - This closes the "raw driver was never tried" loophole.
- `A_hist_alpha_max_raw_driver_fem_pretrain_20260616`
  - Raw driver advances the event slightly and changes crack-tip error, but c69
    remains far behind and scalar history can explode.
- `lagged_g_stiffness_pair_20260613`
  - Lagged stiffness/solver-only variants did not produce log-confirmed
    penetration and remained mixed under regenerated state mapping.
- `history_driver_wake_mismatch_trio_20260602`
  - Useful protocol-family evidence that pre-fit, lagged, and raw choices
    bracket the problem rather than solve it.

Caveats:

- Some 2026-06-02 assets are protocol-family evidence rather than standardized
  case packages.
- A future bounded/mixed driver would be a new design and must be judged by
  field gates, not scalar event timing.

Credibility: negative / diagnostic.

### 4. C1 Coupled Solve / Stiffness Feedback

Claim:

- The c1 raw-energy hotspot is created by coupled elastic-damage feedback, not
  by the initial alpha/precrack field alone.
- Changing epoch schedule or alpha learning rate alone does not remove the
  feedback loop.

Evidence:

- `frozen_alpha_elastic_discriminator_20260603`
  - Fixed analytic alpha makes the c1 elastic solve too cold rather than too
    hot: `psi_raw` and strain hotspot ratios drop well below FEM in the
    frozen-alpha elastic probe.
  - This rules out "the displacement network alone must create the oversharp
    hotspot" as the whole explanation.
- `c1_altmin_discriminator_20260603`
  - With fixed alpha, `r1_uv` cools the raw hotspot.
  - The hotspot reappears when `u/v` re-equilibrates around updated alpha
    through later alternate-minimisation stages.
  - Shorter alpha moves, smaller repeated staggers, and lower alpha LR do not
    remove the raw hotspot.

Caveats:

- These are c1 micro-solve diagnostics, not full cyclic repair runs.
- They explain where the early field mismatch is born; they do not by
  themselves prescribe a stable production fix.

Credibility: supporting / diagnostic.

### 5. Oracle And Restart Causal Channels

Claim:

- The strongest causal split points to missing irreversible
  damage/history-state feedback and accumulated path/state error.
- PIDL can propagate if handed a sufficiently near-critical FEM state.

Evidence:

- `oracle_six_run_comparison_20260610`
  - Penetration-positive: `hard_hist_alpha`, `alpha_bar_state`,
    `psi_raw_feedback`.
  - Penetration-negative or partial: `psi_prev`, `f_fatigue`,
    `fem_g_stiffness`.
- Positive cases:
  - `oracle_hard_hist_alpha_20260610`: first hit at step 344, confirmed 347.
  - `oracle_alpha_bar_state_20260610`: first hit at step 363, confirmed 366.
  - `oracle_psi_raw_feedback_20260610`: first hit at step 343, confirmed 346.
- Negative controls:
  - `oracle_f_fatigue_20260610`: final `Linf=0.464`, no boundary trigger.
  - `oracle_fem_g_stiffness_20260610`: no crack advance to penetration.
- `F_fem_state_restart_pair_20260616_analysis`
  - FEM c68 restart mapped to FEM c69 with d095 error `0.000333`.
  - FEM c60 restart still lagged with d095 error `-0.082333`.

Caveats:

- Oracle injection changes the closed-loop physics.  Use it as a causal
  discriminator, not as a proposed production method.
- Penetration-positive does not equal full field alignment.

Credibility: supporting / diagnostic.

### 6. Irreversibility / History Update

Claim:

- Irreversibility and history update matter, but the simple attempted fixes are
  not sufficient field-level solutions.

Evidence:

- `A_hist_alpha_max_pair_analysis_20260615`
  - `hist_alpha=max(old,current)` preserves monotonic stored history but does
    not improve right-tip alignment; both compared cases first hit c80 and stop
    c83.
- `femlike_irr_penalty_b70cdf3_20260626`
  - Penetration gate passed at PIDL steps 398/401.
  - Corrected state-mapped field alignment remains mixed; c1 history/driver
    residuals and history-dominated gradients remain.
- `hardirr_41e0bf1_20260524`
  - Hard transform v1 produced NaNs from cycle 0.
- `hardirr_6525a9f_20260525`
  - Later hard-irreversibility variants avoid some NaNs but do not recover
    propagation; some attempts fail on TensorBoard/path setup.

Caveats:

- Older hard-irreversibility roots are pre-current-strict lineage evidence.
- Do not reuse them as current strict proof without the chronology caveat.

Credibility: mixed supporting / negative / diagnostic.

### 7. Representation / Localization Architectures

Claim:

- Representation changes can shift fracture timing and propagation mode, but
  the tested variants do not close the local active-driver/history feedback gap.

Evidence:

- `tiplocal_exp18_20260528`
  - MLP/Fourier/SIREN local heads mostly confirm fracture in the N75-N84 window,
    but fields remain coherent centerline/right-boundary paths rather than
    FEM-like process-zone envelopes.
- `staged_alpha_discriminator_20260530`
  - Output-head staging leaves `alpha_bar` and active `psi+` deficient; no-joint
    branch becomes pathological.
- `split_trunk_discriminator_20260601`
  - True split trunk was tried and should not be proposed again as untested.
  - It changed scalar state but did not recover FEM-like trajectory.
- `local_patch_discriminator_20260530`
  - Additive patch is baseline-like or worse; uv-only weakens history.
- `fbpinn_chain_discriminator_20260530`
  - Avoids baseline boundary saturation through j99 and changes propagation
    mode, but c69 `psi_active` tip metric remains far below FEM.
- `allfemmesh_softHist0_fb06879_20260604`
  - Using the FEM mesh for coarse/fine shifts event timing but does not
    establish field alignment.
  - Retrospective decision now lives under the Taobo gap-import root at
    `pidl-allfemmesh-fb06879/analysis/decision.md`.
- `discontinuity_sdf_xfem_uvonly_f17e77e_20260601` and
  `sdf_discontinuity_embedding_archive`
  - SDF/XFEM features shift event timing but remain diagnostic/negative, with a
    strict-vs-legacy caveat.
  - Retrospective strict-vs-legacy boundary decision now lives at
    `pidl-discontinuity-f17e77e/analysis/decision.md`. Count the f17e77e root
    as the strict-ish evidence endpoint and the legacy SDF archive as lineage,
    not as a second independent strict result.

Caveats:

- Some SDF and early tip-local assets predate the final strict-alignment
  protocol.
- `allfemmesh` full run directory remains metadata-only locally, so checkpoint
  forensics still require a coordinated 1.1G transfer if figures need it.

Credibility: negative / diagnostic.

### 8. Field Supervision / Direct Forcing

Claim:

- Direct hidden-field forcing is not a clean fix in its current form; it needs
  normalization, gating, and a purpose-specific field gate before rerun.

Evidence:

- `field_supervision_90dd3ad_20260601`
  - Default pretrain batch failed because `meshed_geom1.msh` was missing.
  - Pretrain-off `alpha`/`alpha_bar` reached the logged N20 window without a
    boundary-fracture stop, but `psi_active` fractured by c1/c4 and `psi_raw`
    by c13/c16, indicating unstable/aggressive hidden-driver forcing.
  - Retrospective decision now lives under the Taobo gap-import root at
    `pidl-field-supervision-90dd3ad/analysis/decision.md`.
- Oracle/direct forcing negatives:
  - `oracle_f_fatigue_20260610` fails the penetration gate.
  - `oracle_triplet_8970066_20260609/{oracle_active_fem, oracle_delta_alpha_bar}`
    are useful channel checks but do not establish a standalone direct-forcing
    fix.
  - `oracle_triplet_8970066_20260609/analysis/decision.md` aggregates
    `oracle_raw_pidl_g`, `oracle_active_fem`, and `oracle_delta_alpha_bar`:
    the family gives no clean oracle fix. Do not call all three negative,
    because raw-PIDL-g is mixed: it recovers timing only by over-amplifying the
    history/driver field.

Caveats:

- The decision separates setup failure from the pretrain-off physical
  diagnostic. Do not treat the default-pretrain missing-mesh failure as a
  mechanism result.

Credibility: negative / diagnostic.

### 9. Inverse / Scalar Calibration

Claim:

- Scalar fatigue-threshold calibration is currently an ill-posed compensation
  route, not material identification or mechanism repair.

Evidence:

- `inverse_alphaT_femmesh_softHist0_20260531`
  - Trainable `alpha_T` collapsed to the lower bound `0.05`.
  - PIDL fractured prematurely at `j=11` and confirmed at `j=14`, far earlier
    than the FEM target `N_f=69`.
  - Raw `psi+` near the tip can be several times FEM while active
    `g(alpha) psi+` remains too low, so scalar threshold adjustment does not
    repair the degraded active-driver field.

Caveats:

- Do not treat the learned `alpha_T=0.05` as a calibrated material parameter.
- Rerun inverse identification only after forward field/state mechanism
  improves.

Credibility: negative / diagnostic.

### 10. Surrogate / M2S Adjacent Work

Claim:

- These runs support framework/tooling decisions, not forward PIDL mechanism
  closure.

Evidence:

- `m2s_framework_validation_20260531`
  - The single-trajectory FEM truth validation shows the M2S layer is feasible,
    but the task is too easy: damage geometry almost orders remaining life by
    itself.
- `mesh_gnn_residual_discriminator_20260616`
  - Mesh-neighbourhood residual model improves held-out c69 `psi_active` log
    MAE from 0.498 to 0.364, but near-tip active driver remains far below FEM.
  - Direct `alpha_bar` correction is negative.
- `taobo_surrogate_smoke_fee0ccf_ecafe0e_20260625_26`
  - MeshGNN/TinyUNet/TinyFNO/DynamicsNet/DirectFieldMLP smoke paths ran finite
    short CPU/GPU losses for the represented commits.

Caveats:

- Surrogate smoke is tooling provenance only.
- M2S needs multi-trajectory FEM splits before claiming hidden state-driver
  fields add independent prognostic value.

Credibility: supporting for framework; diagnostic/tooling for PIDL.

## Decision-File Endpoint Status

Completed in the 2026-06-28 evidence-matrix follow-up:

- `pf_softHist0_state0_seed1_66b56e4_20260624_124606/analysis/decision.md`
- `pf_softHist0_state0_seed1_meshsync_66b56e4_20260624_124900/analysis/decision.md`
- `stateTiming_onepeak_untilFrac_Nphys100_Nstep100/analysis/decision.md`
- `stateTiming_substeps025_untilFrac_Nphys120_Nstep600/analysis/decision.md`
- `pidl-allfemmesh-fb06879/analysis/decision.md`
- `pidl-field-supervision-90dd3ad/analysis/decision.md`
- `pidl-discontinuity-f17e77e/analysis/decision.md`
- `oracle_triplet_8970066_20260609/analysis/decision.md`
- `PIDL_mono_onoff_latest_ddc22eb_20260627_234645/analysis/decision.md`
- `PIDL_mono_onoff_latest_ddc22eb_20260627_234645/analysis/05_fem_comparison_result.md`

Highest-value remaining missing or weak endpoints:

No immediate high-value missing decision endpoint remains from the 2026-06-28
triage list.  The remaining weak endpoints are conditional: predecessor rows
should stay as traceability unless cited directly, and exact state snapshots
should be exported only if a figure needs them.

## Remaining Work Backlog

Completed evidence/figure endpoints:

1. Strict-vs-legacy boundary note for
   `discontinuity_sdf_xfem_uvonly_f17e77e_20260601`.
2. Aggregate decision for `oracle_triplet_8970066_20260609`, pointing to the
   three subcase endpoints.
3. FEM soft-hist0 scalar energy table/figure for
   `mono_onoff_latest_ddc22eb_20260627_234645`.

Evidence endpoints still conditional:

1. Keep the predecessor rows (`probe_driver_clean_*`,
   `precrack_fatigue_mask_clean_*`) as traceability unless they become cited
   directly.

Analysis / figure work:

1. Export or reconstruct exact `stateTiming` substep event states
   `idx408-411` only if a figure needs those NPZ snapshots.
2. Decide whether the eight-seed monotonic aggregate needs a seed-6 rerun before
   any "eight-seed" claim.
3. Defer full downloads of metadata-only Taobo roots until a specific
   figure/checkpoint need exists: `pidl-allfemmesh-fb06879-runs` (1.1G),
   `phase-field-pidl-adapthist-af5a533` (2.2G), and
   `phase-field-pidl-hardirr-6525a9f-runs` (2.0G).

Forward-research gates:

1. Do not launch another architecture or representation sweep unless the
   proposal names the active-driver/process-zone metric it is meant to improve.
2. Do not rerun field supervision without target normalization, a gating
   schedule, and an early-state residual table.
3. Treat bounded/mixed history-driver ideas as new gated designs, not as
   evidence that "raw driver was untried".
4. For M2S/framework validation, prioritize multi-trajectory FEM data over more
   single-trajectory feature engineering.

Writing integration:

1. Use the decision files as claim boundaries when drafting the PIDL mechanism
   story.
2. Keep negative controls grouped by mechanism question instead of presenting
   them as a chronological list of failed runs.
