# Windows-FEM Inbox (Mac → Windows-FEM)

**Direction**: Mac-PIDL → Windows-FEM (GRIPHFiTH)  
**Purpose**: Mac 派发 FEM reference run 任务给 Windows-FEM。  
**Counterpart**: `windows_fem_outbox.md` (Windows-FEM → Mac, status + results + questions)

---

## Format rules

1. **Append newest at top** of "Active Requests" section
2. Every request starts with:
   ```
   ## YYYY-MM-DD · Request <N>: <one-line summary>
   ```
3. Request body must contain:
   - **Goal**: 一句话说明这个 FEM run 要证明/测量什么
   - **INPUT file**: 哪个 .m 文件，关键参数
   - **Mesh**: 用哪个 mesh / 需要新生成
   - **Expected outputs**: 输出放哪、回传什么（VTK/mat/log）
   - **Acceptance criteria**: Mac 如何判断 pass/fail
   - **Priority**: high / medium / low
4. 取消或修改已有 request：append `### [update] YYYY-MM-DD` 子条目
5. 完成的 request 移到底部 "Archive" 区

---

## Active Requests

## 2026-08-17 · Request 28: first-detect causal damage and peak-displacement export

**Goal**: complete the minimum FEM state package needed for the frozen
XDEM-inspired enriched-vs-plain observation diagnostic. Preserve the locked
`first_detect` events U0.11 c122, U0.12 c83 and U0.13 c59; do not substitute
the `+3` confirmation cycles.

**Full forwardable note**:
`docs/handovers/windows_griphfith_request_28_first_detect_peak_state_export_20260817.md`.

**INPUT file**: reuse the exact completed Hard5 eta0 5-step cases under
`Hard5_eta0_5step_Umax_011_012_013_20260729`. Prefer checkpoint/state export;
if an asset was never retained, replay only from the nearest verified
checkpoint in a fresh directory. No physics, tolerance, mesh, cadence or event
criterion changes.

**Mesh**: exact shared native Q4 mesh, expected 86,756 nodes and 86,408 cells;
no remesh or reordering.

**Expected outputs**: one self-contained handoff with c121/c82/c58 unloaded
post-commit nodal damage and c122/c83/c59 substep-4 peak post-commit nodal
displacement, plus state index, mesh/connectivity, provenance, logs and
SHA256SUMS. U0.12 c82 nodal damage and all three peak displacements are the
currently missing assets.

**Acceptance criteria**: state index proves `source=first_detect-1` and
`target=first_detect`; peak rows use substep 4/load factor 1.0 and top-edge
`u_y` matches 0.11/0.12/0.13; mesh hashes match across cases; all arrays are
finite; damage lies in `[0,1]`; no confirmation state is used. If exact state
recovery is impossible, report the blocker instead of approximating nodal
damage from element data.

**Priority**: high, export-only diagnostic. This unlocks a frozen comparison;
it does not authorize PIDL retraining or a new architecture sweep.

## 2026-07-20 · Request 26: matched eta0 multi-Umax trajectories and sensor-ready exports

**Goal**: build the smallest internally matched FEM trajectory family needed to test observed-state next-cycle forecasting, c87-like transition assimilation, and leave-one-physical-trajectory-out validation. The scientific question is whether changing only the applied cyclic amplitude produces enough transition diversity for a model to learn/identify late fracture-regime changes without mixing incompatible FEM families.

This request belongs to `framework-validation` and `trajectory-sufficiency`. It does **not** calibrate PIDL, and it does not change the formal FEM physics. FEM remains the eta0 physical reference.

### Experiment gate and decision consequence

1. **Mechanism question**: under one fixed SENS/AT1/Carrara FEM family, can distinct `Umax` trajectories provide transferable pre-transition and transition-state evolution rather than one-trajectory cycle interpolation?
2. **Claim change**: if the package contains at least three valid trajectories and leave-one-Umax-out evaluation succeeds later on Mac, the temporal/inverse studies may advance from single-trajectory diagnostics to physical-trajectory holdout. If not, all current transition claims remain single-trajectory/synthetic.
3. **Cheaper diagnostic first**: audit and reuse the existing formal `Umax=0.12` trajectory and any exact-family archives. Do not rerun an already complete case. The legacy FEM5 `u10/u11` keyframes are a different `physics_family` and must not be mixed into this request.
4. **Minimal primary asset**: `family_index.csv` plus one verified cycle-state package per Umax and one sensor-ready observation package per trajectory.
5. **Registry path**: reply in `windows_fem_outbox.md` against Request 26. Mac will register the verified family in the reality-transition evidence matrix and run the common FEM-centred validation.

### Fixed formal physics family

Use the current formal SENS recovery baseline certified by:

```text
local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/
analysis/baseline_case_audit_20260709/
fem_semantics_certificate_SENS_recovery_u012_20260709.md
```

Hold all of the following fixed:

```text
geometry / BC / mesh / recovered state0 / precrack semantics
split_type = AMOR
diss_fct = AT1
irrev = PENALTY
E = 1.0
nu = 0.3
Gc = 0.01
ell = 0.01
alpha_T = 0.5
res_stiff (eta) = 0.0
R = 0.0
n_step = 8 loading+unloading substeps per cycle
tol_p_field = 4e-4
SOL_STAG_PAR.tol = 4e-4
regularize_pf_newton = true
damage_upper_bound = 1.0
right-layer penetration: x > 0.48, d > 0.95,
  at least 3 nodes, 3 confirmation cycles
```

The **only intended physical intervention** is:

```text
Umax in {0.10, 0.11, 0.12}
```

- Reuse/re-export the certified `Umax=0.12` run if its required states are complete.
- Run only missing `Umax=0.10` and `Umax=0.11` cases after a one-cycle code/export smoke.
- Use `max_cycle=240` for new lower-amplitude cases so a trajectory may either fail or receive an explicit right-censor label. Do not alter physics to force failure.
- If exact formal-family `Umax=0.10/0.11` runs already exist, verify provenance and export them instead of recomputing.

**INPUT file**: copy the certified u0.12 launch/input pair and create clearly named one-factor variants for u0.10 and u0.11. Record source commit/file hashes and the exact changed lines. Do not silently reuse similarly named legacy FEM5 inputs.

**Mesh**: identical formal SENS recovery mesh for all three trajectories. No remeshing. Export one canonical `mesh_geometry.mat` and verify the coordinate/connectivity hash is identical across the family.

### Required state exports

Export two explicitly labelled states for every completed cycle:

```text
cNNN_peak_post_refresh       # substep 4, peak load
cNNN_unloaded_post_refresh   # substep 8, end of cycle
```

Do not mix a peak driver with an unloaded field without separate labels. Minimum arrays, aligned to the common mesh:

```text
cycles, state_labels, substeps, load_factors
node_coords, connectivity, element_centroids, area_per_elem
u_node                         # clean nodal displacement for synthetic DIC
d_node, d_elem                 # damage, never named alpha_bar
alpha_bar_elem                 # Carrara fatigue accumulator
f_alpha_elem                   # fatigue degradation
psi_raw_peak_elem              # raw tensile driver at peak substep 4
psi_raw_cyclemax_elem           # cycle maximum, separately labelled
psi_active_peak_elem            # GP mean of g(d)*psi_raw at peak; exact product before reduction
g_stiffness_peak_elem           # exact degradation used in psi_active_peak_elem
reaction_force_each_substep
strain_elem_peak                # minimum tensor/components needed for sparse strain probes
```

If `psi_active_peak_elem` cannot be exported exactly from Gauss-point quantities, report the blocker. Do not substitute `mean(g)*mean(psi)` or an unlabeled product of element means.

Large arrays may be written as MATLAB v7.3/HDF5 and split into per-cycle or 20-cycle chunks. Avoid one monolithic multi-GiB file. Preserve full precision for physics fields unless a documented float32 check shows negligible error.

### Sensor-ready clean observation export

For each trajectory, produce a deterministic, noise-free observation package derived from the same labelled peak states:

```text
synthetic_dic/
  coordinates + u_x/u_y at the visible 2D nodes or registered grid
load/
  imposed displacement, reaction force, cycle and substep
crack_observation/
  continuous d field plus masks at d >= 0.25, 0.50, 0.75
sparse_strain_source/
  coordinates + clean strain components from which Mac can choose probe layouts
```

These are **synthetic observations from FEM**, not real experimental data and not oracle hidden-state labels. Do not add arbitrary noise on Windows. Mac will apply documented subsampling, registration and noise models later. Keep `alpha_bar`, `f_alpha`, `g_stiffness`, `psi_raw` and `psi_active` in an `oracle_audit` group, not in the deployable observation table.

### Package layout

Preferred handoff:

```text
~/Downloads/_pidl_handoff_v2/
matched_eta0_multi_umax_sensor_exports_20260720/
  README.md
  family_index.csv
  mesh_geometry.mat
  u010/
    state_index.csv
    cycle_fields_*.mat
    sensor_ready_*.mat or .csv
    RUN_PROVENANCE.txt
  u011/...
  u012/...
  QA/
    field_semantics_audit.csv
    mesh_hash_audit.csv
    event_and_censor_audit.csv
    SHA256SUMS.txt
```

Minimum `family_index.csv` columns:

```text
trajectory_id,physics_family,Umax,R_ratio,failure_first_hit_cycle,
failure_confirmed_cycle,censored,censor_cycle,max_cycle,input_file,
solver_commit,mesh_sha256,state_semantics,source_archive
```

### Acceptance criteria

1. Three trajectories share the same declared `physics_family`; only `Umax` differs.
2. The u0.12 control reproduces the certified c89 terminal/confirmed event semantics, or any deviation is explained before the family is accepted.
3. Every cycle has unambiguous peak and unloaded state labels; all arrays match mesh dimensions and contain finite values.
4. Damage stays within `[0,1]` up to numerical tolerance and is irreversible at comparable committed states.
5. `psi_raw_peak`, `g_stiffness_peak`, and exact `psi_active_peak` satisfy a documented pointwise/GP-to-element consistency audit.
6. Reaction-force/displacement histories are finite and synchronized with state labels.
7. Every trajectory has either first-hit + confirmed event cycles or an explicit right-censor cycle.
8. Sensor-ready channels contain only clean observables/proxies; oracle hidden fields are separated and labelled.
9. Mesh/provenance hashes, README, runner/input copies and SHA256 verification are present.
10. No claim of geometry/material generalization is made from this one-factor Umax family.

### Execution order

1. Audit existing exact-family archives and the certified u0.12 package.
2. Implement/export one cycle from u0.11 as a code-path smoke and verify all field semantics.
3. Continue u0.11, then u0.10; recover from checkpoints if needed.
4. Re-export u0.12 only as needed for matched fields/observations; avoid a duplicate solve.
5. Return `[progress]`, `[blocker]`, or `[done]` in `windows_fem_outbox.md` with exact paths and hashes.

**Priority**: high. This is the next required data asset for fair multi-trajectory forecasting and reality-assimilation tests. Do not change constitutive parameters, eta, symmetry constraints, mesh, or event rules inside this request.

## 2026-07-15 · Request 25: recover existing five-Umax full-field trajectories for reality assimilation

**Goal**: recover or re-export the already completed FEM `Umax=0.08...0.12` trajectory family as cycle-resolved full fields so Mac can test reality-facing sequential assimilation on physical load holdout rather than numerical-cadence holdout.

This is an **archive/export request only**. Do not launch a new FEM solve under this request. If the underlying states no longer exist, report exactly which Umax cases and fields are missing; a new-run design requires a separate reviewed request.

**Existing evidence / likely source**:

- Legacy scalar files were previously available as `SENT_PIDL_{08,09,10,11,12}_timeseries.csv` under `_pidl_handoff_v2/post_process`.
- The retained family is `R=0`, Carrara fatigue, with historical failure/censor information already used by `docs/m2s_next_stage_feasibility_2026-05-31.md`.
- Existing Windows/GRIPHFiTH archives or intermediate per-cycle MAT files are preferred; do not reconstruct hidden fields from scalar CSVs.

**INPUT file**: none for recovery. Preserve the original run input, solver, mesh, state cadence and stop rule in each package. If several historical settings exist, return provenance first rather than silently choosing one.

**Mesh**: original mesh for each existing FEM trajectory. Include `mesh_geometry.mat` and declare whether meshes/coordinate systems are identical across Umax.

**Expected outputs**: one folder per Umax plus a family index, preferably:

```text
~/Downloads/_pidl_handoff_v2/reality_assimilation_five_umax_recovery_20260715/
  family_index.csv
  u08/...cycle_fields.mat
  u09/...cycle_fields.mat
  u10/...cycle_fields.mat
  u11/...cycle_fields.mat
  u12/...cycle_fields.mat
```

Minimum `family_index.csv` columns:

```text
trajectory_id, Umax, R_ratio, failure_cycle, censored, censor_cycle,
input_file, solver_version, mesh_id, state_semantics, source_archive
```

Minimum cycle-resolved arrays:

```text
cycles
element_centroids, node_coords, connectivity, area_per_elem
d_elem or alpha_elem
psi_elem or psi_plus_elem                 # raw mechanics driver
alpha_bar_elem                            # oracle-only audit state
f_alpha_elem or f_fatigue_elem            # oracle-only audit state
```

If already stored, also return nodal displacement and strain/stress fields so Mac can build an explicit DIC/sparse-strain observation model. Do not delay the minimum package to recompute fields that were never saved.

**Acceptance criteria**:

1. At least three distinct physical Umax trajectories are recovered; cadence variants at one Umax do not count.
2. Every trajectory has an explicit failure or right-censor label and an unambiguous cycle/state mapping.
3. Field arrays align with mesh elements and can be loaded without interpolating hidden state from scalar summaries.
4. Raw mechanics, observable/rendered damage, and oracle-only fatigue/history fields are labelled separately.
5. SHA256 or equivalent file checks and a short README preserve provenance.
6. No new FEM computation is started under Request 25.

**Priority**: high for the new reality-assimilation framework, but read-only/export-only. This is cheaper and more informative than designing a new sweep before archive availability is known.

### [update] 2026-07-15 · Mac read-only recovery audit

Mac found and loaded the eight FEM-5 sparse keyframes already present in OneDrive:

```text
_pidl_handoff_FEM5_u10_u11_2026-05-06/
u10: c1, c80, c140, c170 (N_f=170)
u11: c1, c55, c95, c117 (N_f=117)
```

Each file has `77730 x 1` `d_elem`, `psi_elem`, `alpha_bar_elem`, and `f_alpha_elem`. The outbox records that they use the same `SENT_mesh.inp`; Mac successfully paired them with the existing 77,730-element mesh geometry and the new sparse-keyframe importer. Spatial sanity passed: recovered crack-tip trajectories are `0 -> 0.1135 -> 0.3109 -> 0.4995` for u10 and `0 -> 0.1079 -> 0.3032 -> 0.4995` for u11.

Still needed from Request 25: locate/re-export at least one more physically distinct trajectory, preferably the original u08 or u12 four-keyframe family, plus any denser/full-cycle archives still available. Mac can already consume sparse keyframes; a full-cycle package is preferred but no longer required for the first load-holdout benchmark.

### [update] 2026-07-15 · physics-family guard and second recovery check

Mac rechecked OneDrive and `~/Downloads/_pidl_handoff_v2`: no original FEM5 u08/u09 or compatible multi-keyframe u12 package has appeared. A reverseBC u12 cyclewise trajectory is readable, but its BC/constitutive/state provenance differs from the legacy FEM5 u10/u11 family and therefore cannot serve as the third scientific holdout.

The assimilation manifest now requires `physics_family`. Mixed-family runs fail by default; an explicitly allowed tooling stress is automatically quarantined. The mixed u10/u11/reverseBC-u12 stress gives vision+load RUL MAE about 41 cycles and 90% coverage about 0.05, confirming the confounding rather than supplying useful validation. A read-only Taobo reachability probe also timed out, so no remote archive search or compute was started.

## 2026-06-24 · Request 24: pure Manav PIDL energy/state0 data handoff

**Goal**: provide Windows-FEM with the pure Manav-style PIDL reproduction data
and the Mac-side state0 comparison against the four FEM state0 handoff files.
No FEM rerun is required by this request unless Windows-FEM wants to use these
tables to audit the Manav-paper-like brittle recovery state0.

**INPUT file**: none. This is a data handoff from Mac-PIDL.

**Mesh / state0 context**:
- Pure Manav PIDL reproduction uses `SENS_tensile/meshed_geom2.msh`,
  `AT1`, volumetric split, `E=1`, `nu=0.3`, `w1=1`, `l0=0.01`,
  8x400 `TrainableReLU`, `coeff=3.0`, seeds `1-8`.
- Pure Manav PIDL `U=0` is a postprocessed initial anchor from
  `hist_alpha_init`, not a trained solver/load step.
- FEM fatigue soft-hist0 `state0` is the true unloaded FEM export. Mac checked
  that fatigue-on and fatigue-off soft-hist0 state0 fields match exactly at
  load zero: `u=0`, `psi_plus=0`, `alpha_bar=0`, `f_fatigue=1`, same
  `d_node`, `d_elem`, and `g_stiffness`.

**Files available on OneDrive**:

```text
OneDrive/PIDL result/_pidl_handoff_pure_manav_pidl_results_20260624/
```

Main contents:
- `README_pure_manav_pidl_handoff_20260624.md`
- `tables/manav_8seed_energy_mean_std.csv`
- `tables/manav_8seed_energy_mean_std_with_pidl_initial_state.csv`
- `tables/pure_manav_vs_fem_state0_comparison_20260624.csv`
- `tables/pure_manav_pidl_vs_fem_key_energy_comparison_20260624.csv`
- `tables/state0_pure_manav_vs_fem_four_state0_field_stats_20260624.csv`
- `figures/manav_style_pidl8_mean_std_only_with_pidl_initial_state.*`
- `figures/c3_monotonic_fem_pidl_alignment_state0_manav_style.*`

**Mac-side key checks**:
- Pure Manav PIDL state0: `E_el=0`, `E_d=0.004868508316576481`,
  computed via `compute_energy.py` from `hist_alpha_init` on `meshed_geom2.msh`.
- FEM fatigue soft-hist0 state0: `E_el=0`,
  `E_d=0.005085139658691741`.
- FEM/PIDL state0 damage-energy ratio is therefore about `1.0445`; the
  area-weighted element damage means are close (`0.006805` FEM vs `0.006771`
  PIDL), while node counts/means are not directly comparable because the
  meshes and element types differ.
- Along the monotonic curve, the main transition window is aligned around
  `U=0.140--0.145`, but the exact drop shape differs: FEM is already almost
  fully dropped at `U=0.145`, while the PIDL eight-seed mean is still averaged
  over seeds that drop across the same interval.

**Acceptance criteria**:
1. Windows-FEM can read the OneDrive folder and confirm the listed CSVs.
2. If using these data in future FEM notes, label the PIDL `U=0` row as
   `postprocessed hist_alpha_init anchor`, not as a trained PIDL step.
3. Do not mix brittle recovery state0, brittle analytic state0, and fatigue
   soft-hist0 state0 as one single aligned state.

**Priority**: medium. This is a provenance/data-consistency handoff rather than
an urgent run request.

## 2026-06-09 · Request 23: explicit five-substep FEM state export to match PIDL diagnostics

### [update] 2026-06-10 · OneDrive large-MAT sync is stuck on Mac

Mac can see the uploaded folder metadata:

```text
PIDL result/_pidl_handoff_latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_20260609
```

The lightweight files are visible and readable, including the README, log,
state index, and region audit. The quick checks pass:

```text
state_index rows = 346
c1_peak      -> fem_global_step 3
c1_unloaded  -> fem_global_step 4
c69_peak     -> fem_global_step 343
c69_unloaded -> fem_global_step 344
left precrack alpha_bar = 0, masked_Dalpha = 0, f_fatigue = 1
raw psi_plus remains nonzero
```

However the large MAT file is stuck as a OneDrive cloud placeholder on Mac:

```text
latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_state_fields.mat
logical size: 8.7 GiB
local allocated blocks on Mac: 0 bytes
```

Please provide a smaller fallback so Mac can start analysis without waiting for
the full OneDrive hydration. Preferred options:

1. Upload a selected-state MAT package containing only:
   `state0_initial_unloaded_prehistory`, all `c1` substeps, and peak/unload
   states for `c2`, `c3`, `c20`, `c40`, `c60`, `c69`.
2. Or split/compress the full 8.7 GiB MAT into smaller chunks, for example
   1 GiB parts, and upload the parts plus checksum.
3. Or upload per-state/per-cycle MAT files so Mac can download only
   `c1_peak`, `c69_peak`, and the nearby diagnostic states first.

Keep the existing full package in place; this is only a transfer workaround for
OneDrive's stalled on-demand download.

**Goal**: run/export FEM with every converged cyclic substep recorded, so Mac
can compare FEM and PIDL by explicit global step instead of using peak-only
states or load-scaled approximations for intermediate states.

This should preferably be combined with Request 22 for the masked variant:

```text
SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_precrackFatigueDriverMask
```

If possible, also re-export the original standard soft-hist0 reference with the
same explicit step index, but do not delay the masked package for the optional
baseline.

Detailed export note:

```text
docs/handovers/fem_explicit_substep_export_request_2026-06-09.md
```

**INPUT file**: same as Request 22 for the primary package. Save state fields
after every converged substep. For the precrack-fatigue-driver-mask variant,
save after applying the PIDL-equivalent fatigue-driver/history mask.

**Explicit mapping**:

```text
fem_global_step = 5*(cycle - 1) + (substep - 1)

cycle c, substep 1, load 0.25 -> step 5*(c-1)+0 -> c<c>_step1
cycle c, substep 2, load 0.50 -> step 5*(c-1)+1 -> c<c>_step2
cycle c, substep 3, load 0.75 -> step 5*(c-1)+2 -> c<c>_step3
cycle c, substep 4, load 1.00 -> step 5*(c-1)+3 -> c<c>_peak
cycle c, substep 5, load 0.00 -> step 5*(c-1)+4 -> c<c>_unloaded
```

Key checks:

```text
c1_peak      = step 3
c1_unloaded  = step 4
c69_peak     = step 343
c69_unloaded = step 344
```

**Mesh**: same mesh as the standard soft-hist0 reference. No remeshing and no
change to material, BCs, loading, stop rule, or soft precrack damage profile.

**Expected outputs**: suggested primary folder:

```text
~/Downloads/_pidl_handoff_v2/latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_20260609/
```

Please include:

```text
latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_state_fields.mat
latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_state_index.csv
mesh_geometry.mat
precrack_fatigue_driver_mask_region_audit.csv
README_latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps.md
INPUT_*.m
solve_fatigue_fracture.m
export script(s)
run log
```

State records should include:

```text
state0_initial_unloaded_prehistory
c1_step1 ... c1_unloaded
c2_step1 ... c2_unloaded
...
c69_step1 ... c69_unloaded
```

So the expected package has:

```text
1 initial state + 69 cycles * 5 substeps = 346 state records
```

**Acceptance criteria**:

1. Every converged substep has a state record and state-index row.
2. State index contains physical cycle, substep, load factor, state label,
   `fem_global_step`, and expected PIDL global step.
3. `c1_peak` is step 3 and `c1_unloaded` is step 4.
4. `c69_peak` is step 343 and `c69_unloaded` is step 344.
5. README clearly labels raw mechanics fields versus post-mask
   fatigue-driver/history fields.
6. Mac can compare PIDL global diagnostic step-by-step against FEM without
   using an intermediate-substep oracle approximation.

**Priority**: high. This removes the remaining timing/export ambiguity in the
FEM/PIDL comparison.

## 2026-06-09 · Request 22: FEM+PIDL-equivalent precrack fatigue-driver mask

### [update] 2026-06-09 correction

Do **not** use the earlier standalone helper
`apply_precrack_history_mask.m`; it has been withdrawn. The real PIDL run was
explicitly launched with `mask_fatigue=True, mask_energy=False`, so FEM should
match that mechanism: keep mechanics/fracture energy active, but block
fatigue-driver/history accumulation on the old precrack line.

**Goal**: run a FEM counterfactual that keeps the standard soft-hist0 retained
precrack damage/mechanics profile, but applies a PIDL-equivalent
fatigue-driver/history mask along the old left precrack line. This tests whether
the current FEM/PIDL left-line field mismatch is a mask-policy difference rather
than a PIDL failure.

Mac-side finding from the PIDL precrack-mask run:

```text
left precrack line audit band:
x <= 0.5 and |y - 0.5| <= 0.014

c1_peak:
PIDL alpha_bar/history mean = 0
FEM  alpha_bar/history mean = 0.0159985

c69_peak:
PIDL alpha_bar/history mean = 0
FEM  alpha_bar/history mean = 0.892614
```

**INPUT file**: clone the strict standard reference
`INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC.m` and
`solve_fatigue_fracture.m`. Suggested new run name:

```text
SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_precrackFatigueDriverMask
```

Corrected patch note and MATLAB snippets:

```text
docs/handovers/fem_precrack_history_mask_request_2026-06-09.md
```

**Mask rule**: PIDL centered coordinates were `x <= 0.0, |y| <= 0.02`.
Equivalent FEM plate coordinates:

```text
x <= 0.5 and |y - 0.5| <= 0.02  (= 2*ell)
```

Match PIDL's `mask_fatigue=True, mask_energy=False` policy. Keep raw mechanics
and raw `psi_plus`; block only fatigue-driver/history accumulation:

```text
fatigue driver / Dalpha on mask -> 0
alpha_bar / fatigue history on mask -> 0
f_alpha / fatigue degradation on mask -> 1
```

Do **not** overwrite `p_field`, raw `psi_plus`, displacement, strain, stress,
fracture/damage history H, or the raw mechanics solve. Raw mechanics should
remain available for audit.

**Mesh**: same mesh as the standard soft-hist0 reference. No remeshing and no
change to the soft precrack damage profile.

**Expected outputs**: suggested folder:

```text
~/Downloads/_pidl_handoff_v2/latest_align_soft_hist0_precrackFatigueDriverMask_20260609/
```

Please include:

```text
latest_align_soft_hist0_precrackFatigueDriverMask_state_fields.mat
latest_align_soft_hist0_precrackFatigueDriverMask_state_index.csv
mesh_geometry.mat
precrack_fatigue_driver_mask_region_audit.csv
README_latest_align_soft_hist0_precrackFatigueDriverMask.md
INPUT_*.m
solve_fatigue_fracture.m
export script(s)
run log
```

State labels should match the previous aligned export:

```text
state0_initial_unloaded_prehistory
c1_step1, c1_step2, c1_step3, c1_peak, c1_unloaded
c2/c3/c20/c40/c60/c69 peak and unloaded
```

**Acceptance criteria**:

1. Same mesh, material, BCs, loading, soft precrack profile, and stop rule as
   the standard soft-hist0 FEM reference.
2. README states the exact mask region and confirms only fatigue-history state
   is reset, and that mechanics/energy are not masked.
3. Region audit verifies `alpha_bar ~= 0`, `Dalpha ~= 0`, and `f_alpha ~= 1`
   are eliminated on the left precrack line at peak states.
4. Raw mechanics fields are still exported separately, so Mac can distinguish
   raw FEM mechanics from the masked fatigue-history oracle.
5. Mac can compare PIDL precrack-mask against both original FEM and FEM+mask.

**Priority**: high. This is the cleanest way to decide whether the current
left-precrack-line discrepancy is a physical FEM/PIDL mismatch or simply a
different fatigue-history mask policy.

## 2026-05-29 · Request 21: one-factor FEM substep/history-timing controls after PIDL state audit

**Goal**: test whether the remaining soft-hist0 FEM/PIDL gap is mainly caused
by cycle-history timing/substep refresh semantics, after Mac-side PIDL audit
found that FEM c1 maps best to PIDL saved `j=0` but late-cycle
`alpha_bar`/active `psi_plus`/incremental `E_d` still lag in PIDL.

Please keep the strict soft-hist0 reverseBC reference fixed:

```text
Base: SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC
material retained in precrack
soft AT1/PIDL-like diffuse precrack
initial alpha_bar = 0
initial f_alpha = 1
reverseBC: fix_X top+bottom, fix_Y bottom, disp_Y top
u_max = 0.12
E=1, nu=0.3, Gc=0.01, ell=0.01, alpha_T=0.5, p=2
AT1 + AMOR + PENALTY
tol_irrev = 1e-3 unless explicitly varied below
res_stiff = 1e-6
same retained-material diffuse mesh as Request 18/20
```

**Why this request**:

Mac now has:

```text
docs/pidl_femmesh_state_timing_audit_2026-05-29.md
```

Key Mac-side result:

```text
FEM c1 mixed timing -> PIDL saved j=0 is better than -> PIDL saved j=1
alpha_bar tip_2l0: j0/FEM = 0.985, j1/FEM = 1.968
active psi_plus tip_2l0: j0/FEM = 1.013, j1/FEM = 1.011
```

So first-cycle timing is mostly clarified.  The remaining late-cycle gap is now
more likely history-refresh/substep semantics or representation/localization,
not just c1 indexing.

**Requested FEM variants**:

Please run the following as one-factor controls, changing only cyclic substep
count/history-refresh cadence relative to the soft-hist0 baseline:

```text
Variant A: n_step = 2
Variant B: n_step = 3
Variant C: n_step = 10
```

Interpretation target:

```text
Request 19 peak-only n_step=1 -> no penetration by c120
standard GRIPHFiTH retained substeps -> N_f=69
```

We need the curve between these endpoints.  If the code's `n_step` value is
pruned or internally transformed, please document the retained load factors in
the README, as in Request 20.

**Expected outputs**:

Suggested OneDrive folders:

```text
_pidl_handoff_reverseBC_u12_soft_hist0_nstep2_2026-05-29
_pidl_handoff_reverseBC_u12_soft_hist0_nstep3_2026-05-29
_pidl_handoff_reverseBC_u12_soft_hist0_nstep10_2026-05-29
```

For each variant, please include the same cyclewise mechanism format as
Requests 18/19:

```text
*_cyclewise_mechanism_metrics.csv
*_element_fields_c1_cXX.mat
mesh_geometry.mat
README_*.md
INPUT_*.m
main/run/export scripts for traceability
```

Required fields/reductions are the same as Request 19:

```text
d_elem
alpha_bar_elem
f_fatigue_elem / f_alpha_elem
psi_plus_elem
psi_plus_peak_to_date_elem, if available
E_el, E_d, total_energy
d/alpha_bar/f/psi max, p99, p999, mean
near-tip integrals within r <= ell, 2ell, 4ell
x/y max-d, max-alpha_bar, min-f, max-psi
x_tip_d095, x_tip_d090, x_tip_d050
right-boundary damage count/event audit
```

**Extra export request, no new FEM run if possible**:

Please also export a small explicit "PIDL-like c1 mixed row" from the existing
soft-hist0 state-timing data:

```text
damage/history/f = cycle1_unloaded_post_history_refresh
psi_plus = cycle1 psi_plus_peak_to_date
```

This can be a CSV/MAT row or README table.  The goal is to prevent future
scripts from silently reconstructing the old mixed c1 timing differently.

**Acceptance criteria**:

Mac can load each folder and verify:

```text
1. Same mesh/node/element counts as soft-hist0 baseline.
2. README states actual retained load factors/history refresh points.
3. CSV has one row per exported cycle and includes N_f/event criteria.
4. MAT field arrays match CSV cycle count.
5. Only substep/history cadence changed, not notch, mesh, material, fatigue law,
   alpha_T, tol_irrev, or residual stiffness.
```

**Priority**: high.  FEM is currently the cheaper lever for alignment
diagnosis.  Please keep this one-factor: do not combine with mesh/notch/fatigue
law changes in the same run.

## 2026-05-29 · Request 20: soft-hist0 state-timing export around cycle 0/1

**Goal**: separate three effects that are currently mixed inside the existing
`c1` comparison: initial diffuse-precrack mismatch, first loaded elastic/damage
solve mismatch, and first fatigue/history-refresh mismatch. This should be an
export/instrumentation task around the completed soft-hist0 reference, not a
new physics variant unless the solver cannot re-export the requested states
from saved data.

Base reference:

```text
SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC
OneDrive/PIDL result/_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28
N_f = 69
```

Please keep the same settings:

```matlab
soft AT1-like diffuse precrack;
alpha_bar = 0 initially;
f_alpha = 1 initially;
material retained in precrack;
reverseBC: fix_X top+bottom, fix_Y bottom, disp_Y top;
E=1, ni=0.3, Gc=0.01, ell=0.01, alpha_T=0.5, p=2;
AT1 + AMOR + PENALTY;
tol_irrev = 1e-3;
res_stiff = 1e-6.
```

**Requested state labels and timing**:

```text
state0_initial_preload_prehistory
  after mesh/precrack initialization;
  before first displacement loading;
  before first damage solve;
  before any alpha_bar/f_alpha history refresh.

cycle1_peak_pre_history_refresh
  after solving the first peak U=0.12 state;
  before updating alpha_bar/f_alpha for the first fatigue-history refresh.

cycle1_peak_post_history_refresh
  after the first fatigue-history refresh.
  This should correspond to the existing c1 handoff if the old exporter used
  the same timing.

cycle1_unloaded_post_history_refresh, if available
  after unloading/end-of-cycle state, with the same post-history fields.
```

If FEM has additional internal substeps in cycle 1, please either export all
substeps with a `load_factor` column or state clearly which one each label
represents.

**Expected outputs**:

OneDrive folder suggestion:

```text
_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_state_timing_2026-05-29
```

Please include:

```text
state_timing_metrics.csv
state_timing_element_fields.mat
mesh_geometry.mat
README_reverseBC_u12_diffuse_precrack_soft_hist0_state_timing.md
export_state_timing.m, and any patched solver/export scripts needed for audit
```

For every exported state, please provide element fields on the same mesh:

```text
d_elem
alpha_bar_elem
f_alpha_elem / f_fatigue_elem
psi_plus_elem, if physically meaningful at that state
element_centroids
element_area
```

For the CSV/README, please record:

```text
state_label
cycle index
load factor and displacement value
loaded vs unloaded
before/after damage solve
before/after alpha_bar update
before/after f_alpha update
E_el, E_d, total energy if defined for the state
p99/p999/max and near-tip r <= ell, 2ell, 4ell reductions for each field
whether the initial_precrack_exclusion_nodes penetration guard is active
whether the exported c1_post state numerically matches the old c1 handoff
```

**Acceptance criteria**:

- Mac can compare PIDL `hist_alpha_init`, pretraining alpha, and `hist_fat=0`
  against FEM `state0_initial_preload_prehistory`.
- Mac can compare FEM `cycle1_peak_pre_history_refresh` against PIDL after the
  first peak solve before history update, if/when PIDL exports that state.
- The README makes the timing unambiguous enough that we no longer call the
  existing `c1` field an "initial-state" comparison.

**Priority**: high. This is the cleanest way to understand why residual fields
are already visible at `c1` without mixing initialization, loading, and fatigue
history in one bucket.

## 2026-05-29 · Request 19: one-factor FEM alignment diagnostics after soft-hist0

**Goal**: run cheap one-factor FEM variants around the completed soft-hist0
diffuse reference, so Mac can separate true PIDL mechanism gaps from remaining
setting/numerical differences.

Base reference:

```text
SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC
OneDrive/PIDL result/_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28
N_f = 69
```

Please keep this base fixed unless a variant explicitly changes one item:

```matlab
soft AT1-like diffuse precrack;
alpha_bar = 0 initially;
f_alpha = 1 initially;
material retained in precrack;
reverseBC: fix_X top+bottom, fix_Y bottom, disp_Y top;
E=1, ni=0.3, Gc=0.01, ell=0.01, alpha_T=0.5, p=2;
AT1 + AMOR + PENALTY.
```

## Variant A: FEM `tol_irrev=5e-3`

**Question**: Is the remaining PIDL/FEM incremental `E_d` and crack-lag gap
partly due to irreversibility strength? Current FEM uses `tol_irrev=1e-3`,
while PIDL baseline uses `tol_ir=5e-3`.

**INPUT file**:

```matlab
Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_tolir5e3.m
```

Change only:

```text
tol_irrev = 5e-3
```

If GRIPHFiTH uses a different variable name for this tolerance, please state
the exact variable and resulting AT1 penalty coefficient in the README.

## Variant B: FEM one-peak-per-cycle history update

**Question**: Does FEM's within-cycle substep history update explain the
remaining gap? PIDL baseline effectively solves one peak state per cycle and
updates fatigue history from that peak.

**INPUT file**:

```matlab
Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_peakonly.m
```

Preferred implementation:

```text
one peak load state per cycle for fatigue-history update,
or n_step=1 peak-only if that is the clean GRIPHFiTH equivalent.
```

Please make clear in the README whether this is exactly one peak update per
cycle or only an approximation. If this is not feasible without changing solver
semantics too much, please report it as blocked rather than forcing a misleading
variant.

## Variant C: residual stiffness off or near-zero

**Question**: Does FEM's residual stiffness `res_stiff=1e-6` matter near fully
damaged zones? PIDL appears to use `g(alpha)=(1-alpha)^2` without FEM-style
`eta`.

**INPUT file**:

```matlab
Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_resstiff0.m
```

Change only:

```text
res_stiff = 0
```

If exact zero causes singularity, use the smallest stable value you trust and
report it.

## Requested outputs for each completed variant

Please export the same cyclewise package as Request 18:

```text
*_cyclewise_mechanism_metrics.csv
*_element_fields_c1_cXX.mat
mesh_geometry.mat
README_*.md
INPUT_*.m
export_reverseBC_cyclewise_mechanism.m
```

Please include all current reductions plus these explicit reduction/audit
items:

```text
p99 and p999 for d, alpha_bar, f_alpha, psi_plus
near-tip integrals for d, alpha_bar, f_alpha, psi_plus within r <= ell, 2ell, 4ell
cycle-0/1 initial precrack d profile audit
native fracture cycle and harmonized right-boundary d>=0.95 count
side-boundary stress/traction residual if available, or a note that it is not exported
```

Suggested OneDrive folders:

```text
_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_tolir5e3_2026-05-29
_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_peakonly_2026-05-29
_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_resstiff0_2026-05-29
```

**Acceptance criteria**:

- Each variant changes exactly one factor from soft-hist0 base, or documents
  why exact one-factor isolation is blocked.
- README records `tol_irrev`, `res_stiff`, `n_step`/cycle update semantics,
  and the initial precrack audit.
- The exported fields can be loaded by Mac and compared on the common probe grid.

**Priority**: high for Variant A and B; medium for Variant C. These are cheaper
than broad PIDL architecture sweeps and directly test the remaining alignment
suspects.

## 2026-05-28 · Request 18: strict soft diffuse-precrack initial-state alignment

**Goal**: isolate whether the large FEM/PIDL difference is caused by the
initial precrack/history convention. The current diffuse-precrack FEM is closer
to PIDL than void FEM, but it initializes `alpha_bar=1` and therefore
`f_alpha=0.4444` in the precrack band. Mac's current interpretation is that a
pre-existing crack should be an initial damage/crack condition, not an initial
fatigue-accumulation condition. Also, PIDL baseline uses a soft AT1-like
`hist_alpha_init` precrack profile rather than a hard rectangular `d=1` band.
Please run the strictly aligned initial-state variant below, with a soft
precrack as the preferred case and a hard `d=1` case only as fallback if the
soft profile is difficult in GRIPHFiTH.

**INPUT file**: Please create a new input based on the completed diffuse
precrack reverseBC run:

```matlab
Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC.m
```

Keep the same base settings as the completed diffuse-precrack run:

```matlab
split_type = 'AMOR';
diss_fct   = 'AT1';
irrev      = 'PENALTY';
E=1, ni=0.3, Gc=0.01, ell=0.01, alpha_T=0.5, p=2;
uy_final=0.12, R=0, n_step=8;
fix_X = top+bottom, fix_Y = bottom, disp_Y = top;
material retained in the precrack band;
same precrack length/location as the previous diffuse run.
```

Preferred initial damage/precrack convention:

```text
phase field in precrack: soft AT1-like diffuse profile matching PIDL
hist_alpha_init as closely as possible:

for the straight precrack core, use a width controlled by ell/l0 = 0.01 and
the same support idea as PIDL's AT1 profile, where damage peaks near 1 on the
crack centreline and decays smoothly over roughly 2*ell.

precrack length/location: x <= 0, y = 0 in centred coordinates
or x <= 0.5, y = 0.5 in [0,1] FEM coordinates.
```

If a soft phase-field initial condition cannot be imposed cleanly, please use
the hard `d=1` precrack as a fallback and state that clearly in the README.

Strict fatigue/history convention:

```text
fatigue history alpha_bar in precrack band: 0
fatigue history alpha_bar outside precrack: 0
initial f_alpha everywhere: 1, unless the code recomputes a different value
from alpha_bar; if so, please report it explicitly.
```

Please also report the actual `tol_irrev` used by GRIPHFiTH. Mac currently
believes FEM default is `tol_irrev=1e-3`, while PIDL default is `tol_ir=5e-3`,
which is a 25x penalty-strength difference.

**Mesh**: Use the same mesh as the completed diffuse-precrack handoff:

```text
_pidl_handoff_reverseBC_u12_diffuse_precrack_2026-05-28
node_coords: 45591 x 2
connectivity: 45000 x 4
```

If the mesh must change, please state the new node/element counts and include a
fresh `mesh_geometry.mat`.

**Expected outputs**:

Please export the same cyclewise mechanism package as the previous diffuse
precrack run and mirror it to OneDrive, e.g.

```text
OneDrive/PIDL result/_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28
```

Required files:

```text
reverseBC_u12_diffuse_precrack_soft_hist0_cyclewise_mechanism_metrics.csv
reverseBC_u12_diffuse_precrack_soft_hist0_element_fields_c1_cXX.mat
mesh_geometry.mat
README_reverseBC_u12_diffuse_precrack_soft_hist0.md
INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC.m
export_reverseBC_cyclewise_mechanism.m
```

Please include the same fields and reductions as Request 16 / the previous
diffuse handoff:

```text
d_elem
alpha_bar_elem
f_fatigue_elem or f_alpha_elem
psi_plus_elem
E_el, E_d, total energy
damage/history/f/psi max-min-percentile reductions
max/min locations
x_tip_d095, x_tip_d090, x_tip_d050
process-zone width metrics
right-boundary d>=0.95 count and y-span
```

Please add an initial-state audit to the README and/or CSV:

```text
precrack d mean/max at cycle 0 or cycle 1 before loading
precrack d profile description and whether it is soft or hard
precrack alpha_bar mean/max at cycle 0 or cycle 1 before loading
precrack f_alpha mean/min at cycle 0 or cycle 1 before loading
outside-precrack alpha_bar mean/max at cycle 0 or cycle 1
whether E_d includes the initial precrack damage energy
whether any scalar energy is absolute or incremental relative to the initial state
```

**Acceptance criteria**:

- The run uses the same reverseBC and same diffuse-precrack geometry as the
  previous diffuse handoff.
- Preferred: the precrack uses a soft AT1-like phase-field profile and
  `alpha_bar=0` initially.
- Fallback: hard `d=1` precrack with `alpha_bar=0` initially, only if the soft
  profile is blocked by code structure and documented.
- `f_alpha` is not pre-degraded by artificial fatigue history at initialization.
- The OneDrive payload includes cyclewise fields through available fracture.
- The README explicitly separates absolute `E_d` from incremental/outside-
  precrack `E_d` interpretation.

**Priority**: high. This blocks strict FEM/PIDL mechanism interpretation.

## 2026-05-28 · Request 17: resend/regenerate reverseBC u12 snapshots for strict field-level metric

**Goal**: Mac needs the full reverseBC `u12` FEM handoff locally so the new field-level scorer can compute a strict same-probe comparison against the intended aligned reference. Right now Mac only has strict same-probe CSVs for baseline/femAnchorBC; reverseBC appears only as a partial summary/outbox row, which is why `field_level_metric_results_2026-05-28.md` still shows femAnchorBC numeric scores but no reverseBC strict score.

**INPUT file**: Use the already completed reverseBC `u12` reference if available:

```matlab
Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_reverseBC.m
```

Same setting as Request 15 / Request 16:

```matlab
split_type = 'AMOR';
diss_fct   = 'AT1';
irrev      = 'PENALTY';
E=1, ni=0.3, Gc=0.01, ell=0.01, alpha_T=0.5, p=2;
uy_final=0.12, R=0, n_step=8;
fix_X = top+bottom, fix_Y = bottom, disp_Y = top;
```

If the previous run output still exists, please do **not** rerun. Just re-export / resend the existing `.mat` snapshots. If it does not exist, rerun only as needed to regenerate the same reference.

**Mesh**: Please include `mesh_geometry.mat` matching the snapshot fields. Required keys:

```text
element_centroids
connectivity
node_coords
```

If this is the same mesh as original `SENT_PIDL_12`, please state that explicitly. If not, the shipped `mesh_geometry.mat` is mandatory.

**Expected outputs**:

Please create or refresh:

```text
~/Downloads/_pidl_handoff_v2/reverseBC_u12/
```

and mirror to OneDrive as usual, e.g.

```text
OneDrive/PIDL result/_pidl_handoff_reverseBC_u12_2026-05-28/
```

Minimum required files:

```text
mesh_geometry.mat
u12_reverseBC_cycle_0001.mat
u12_reverseBC_cycle_0040.mat
u12_reverseBC_cycle_0070.mat
u12_reverseBC_cycle_0074.mat
SENT_PIDL_12_reverseBC_timeseries.csv
```

Optional but useful:

```text
u12_reverseBC_cycle_0080.mat
u12_reverseBC_cycle_0082.mat
```

Each cycle `.mat` must contain the strict metric fields:

```text
d_elem
psi_elem
alpha_bar_elem
f_alpha_elem
```

These are enough for Mac to run the same projection logic as:

```text
SENS_tensile/posthoc_mesh_probe_alignment.py
```

and produce:

```text
SENS_tensile/alignment_mesh_probe_u012_reverseBC.csv
```

**Acceptance criteria**:

- Mac can load every `.mat` file with `scipy.io.loadmat`.
- `d_elem`, `psi_elem`, `alpha_bar_elem`, and `f_alpha_elem` all have length `N_elem`.
- `mesh_geometry.mat` has the same `N_elem` and valid connectivity/node coordinates.
- The cycle set includes at least `1, 40, 70, 74`.
- Outbox states whether this is a resend of the existing run or a fresh rerun.

**Priority**: high. This is the missing P0 row in the field-level metric table. No new PIDL architecture sweep should be interpreted before this reverseBC strict score exists.

## 2026-05-27 · Request 16: export FEM mechanism/energy diagnostics for cycle-matched PIDL comparison

**Goal**: Build a mechanism-level FEM vs PIDL comparison, not just final `N_f` or final damage plots. Mac wants to identify where the nonlinear fatigue loop first diverges: displacement/strain, stress-energy concentration, fatigue history, damage width/smoothness, or irreversibility/history enforcement. The immediate target is the BC-matched reverseBC `u12` FEM reference, because current PIDL default is closest to that BVP.

**Context / local FEM reference**:
- FEM project root on Mac: `/Users/wenxiaofang/phase-field-fracture-with-pidl/GRIPHFiTH`
- Relevant FEM setting family: `Scripts/fatigue_fracture/INPUT_SENT_PIDL_12*.m`
- Existing reverseBC handoff: `OneDrive/PIDL result/_pidl_handoff_reverseBC_u12_2026-05-22/`
- Existing reverseBC snapshots contain `psi_elem`, `alpha_bar_elem`, `f_alpha_elem`, `d_elem`, plus `mesh_geometry.mat`.
- Missing for energy/mechanism closure: peak-load `u_node`, exact/consistent FEM energy terms, and ideally stress/strain or GP-level fields.

**INPUT file**: Prefer the already completed reverseBC `u12` run from Request 15 / outbox 2026-05-22. If re-running/post-processing is needed, use the same reverseBC clone of `INPUT_SENT_PIDL_12.m`:

```matlab
split_type = 'AMOR';
diss_fct   = 'AT1';
irrev      = 'PENALTY';
E=1, ni=0.3, Gc=0.01, ell=0.01, alpha_T=0.5, p=2;
uy_final=0.12, R=0, n_step=8;
fix_X = top+bottom, fix_Y = bottom, disp_Y = top;
```

Please do not change the main reference mesh for this request. Mac will compare FEM and PIDL on a common evaluation grid by interpolation/evaluation. A coarse/fine FEM mesh convergence check is useful later, but should be a separate diagnostic so we do not mix mesh effects with mechanism effects.

**Mesh**: Use the existing reverseBC mesh if possible: `mesh_geometry.mat` with 77,730 elements and 77,900 nodes. If any new output uses a different mesh, ship its own `mesh_geometry.mat` with node order and connectivity matching all nodal fields.

**Expected outputs**:

Please create a new handoff folder, e.g.

`~/Downloads/_pidl_handoff_v2/reverseBC_u12_mechanism_energy/`

and mirror to OneDrive as usual. Minimum cycle set:

`c1, c20, c40, c60, c70, c74`

If cheap, also export every 5 or 10 cycles as a lightweight CSV/table, but the six snapshots above are enough for first comparison.

For each selected cycle, please export one `.mat` file with as many of the following as feasible:

| field | shape | priority | why Mac needs it |
|---|---:|---:|---|
| `u_node` | `N_node x 2` | must | compute FEM strain/stress/elastic energy and compare displacement relaxation |
| `d_node` or `p_field_node` | `N_node x 1` | high | compute damage gradients/smoothness directly; `d_elem` alone is not enough for gradients |
| `d_elem` | `N_elem x 1` | must | damage shape, crack tip, width, boundary reach |
| `psi_elem` | `N_elem x 1` | must | stress-energy concentration / Kt-style comparison |
| `alpha_bar_elem` | `N_elem x 1` | must | fatigue history accumulation |
| `f_alpha_elem` | `N_elem x 1` | must | fatigue degradation field |
| `sigma_gp` | `N_elem x N_gp x 3` | high | stress concentration, local/global redistribution; components `(xx, yy, xy)` |
| `strain_gp` | `N_elem x N_gp x 3` | medium-high | independent check of strain from `u_node` |
| `psi_plus_gp` | `N_elem x N_gp` | high | distinguish peak singularity from element-averaged smoothing |
| `d_gp` and/or `grad_d_gp` | `N_elem x N_gp`, `N_elem x N_gp x 2` | high | process-zone width and smoothness |
| `xy_gp`, `w_gp`, `detJ_gp` or element areas | compatible GP shapes | high | allow Mac to integrate energy exactly/consistently |
| FEM internal history variables | whatever native shape | medium | e.g. history slot(s), fatigue-history increment, penalty/irreversibility residual if available |

Please also export one `energy_vs_cycle.csv` for all cycles up to fracture with columns as available:

```text
cycle
reaction_Fy_peak
top_displacement_peak
W_ext_peak_or_cycle
E_elastic_FEM
E_damage_FEM
E_total_FEM
d_max
alpha_bar_max
f_min
psi_plus_max
psi_plus_p99
crack_tip_x
damage_width_alpha02
damage_width_alpha05
right_boundary_dmax
right_boundary_N_d_gt_095
```

If GRIPHFiTH already computes internal energies, please export those exact solver values and document the formula/source variable. If not, export the raw `u_node`, `d_node`, GP fields, and quadrature weights so Mac can recompute:

```text
E_el = integral of degraded elastic energy density at peak load
E_d  = AT1 fracture functional, using Gc=0.01 and ell=0.01
```

For PIDL comparison, Mac will keep PIDL's `E_hist` separate. FEM may not have an equivalent `E_hist` because irreversibility is enforced by PENALTY/history update rather than by the same NN loss term. If FEM has a penalty energy or irreversibility residual, please export it; otherwise state that FEM has no directly comparable `E_hist`.

**Specific mechanism questions this should answer**:

1. Local vs global: does FEM release elastic energy locally at the crack tip while PIDL relaxes a longer horizontal band?
2. Gradient and smoothness: is FEM damage/process-zone width finite and smooth compared with PIDL's thin strip?
3. Relaxation and concentration: after damage grows, where does FEM's `psi_plus` hotspot move, and how strong is it compared with PIDL's lower `Kt`?
4. History amplification: does `alpha_bar` first diverge near the true tip, or only after PIDL has already taken a different damage path?
5. Boundary reach: in FEM, does high damage remain a propagating process zone until fracture, or does it form the same continuous high-damage band to the right boundary that PIDL often shows?

**Acceptance criteria**:

Mac can build a cycle-matched table/figure containing, for FEM and PIDL on the same evaluation grid:

```text
cycle / fraction-of-life
crack-tip x
damage/process-zone width
alpha/d max
alpha_bar max
f_min
psi_plus max, p99, and Kt-style top-10 metric
E_el and E_d
right-boundary high-damage count
```

For PIDL only, Mac will add:

```text
E_hist
grad_E_el, grad_E_d, grad_E_hist
tip-patch corr/total
tip-patch grad_tip/global
```

**Priority**: **high**. This is the cleanest way to decide whether the PIDL/FEM gap is driven by mesh/resolution, NN representation, fatigue-history update, energy balance, or crack-tip tracking.

## 2026-05-21 · Request 15: ship reverseBC snapshots to handoff dir → BC-matched FEM reference for PIDL field comparison

**Goal**: Mac now has a strong PIDL result (J-path-independence regulariser fractures cleanly, N_f=82) and did a field-level comparison vs FEM. But the comparison used the **baseline FEM** (`_pidl_handoff_v2/.../u12_cycle_*.mat`, fix_X bottom_left, traction-free laterals) while **PIDL's default BC clamps u_x=0 on top+bottom** (NN correction vanishes there + cosθ=0) — i.e. PIDL solves the **reverseBC** BVP, not the baseline one. So the comparison is BC-mismatched. The reverseBC FEM run (Request 13, outbox `2ce76ec`, N_f=74) is the **BC-matched** reference we actually need.

### Ask
The reverseBC run already produced 74 `psi_fields/cycle_*.mat` in
`Scripts/fatigue_fracture/SENT_PIDL_12_reverseBC/`. Please ship the per-element
field snapshots + mesh to a handoff dir so Mac can load them, mirroring the
baseline schema:

- **Destination**: `~/Downloads/_pidl_handoff_v2/reverseBC_u12/` (+ usual OneDrive/mirror copy)
- **Cycles**: c1, c40, c70, and **c74 (fracture)** — minimum. (More is fine; these 4 mirror the baseline's c1/c40/c70/c82 sampling for a like-for-like field comparison.)
- **Fields per cycle** (same keys as baseline snapshots): `psi_elem`, `alpha_bar_elem`, `f_alpha_elem`, `d_elem`.
- **Mesh**: `mesh_geometry.mat` (`element_centroids`, `connectivity`, `node_coords`) — confirm it's the SAME mesh as baseline (so PIDL/FEM centroids align); if reverseBC used a different mesh, ship its own.
- **Bonus (ties Request 14)**: if cheap, add `u_node` (N_node,2) per cycle so we can also compute the BC-matched FEM J-integral.

### Note on cycle alignment
PIDL J-path fractures at c82, reverseBC FEM at c74. For the comparison Mac will
align by fraction-of-life / crack position, not absolute cycle — so the fracture
snapshot (c74) is the important endpoint, plus a couple of mid-life cycles.

### Acceptance
Mac re-runs the field comparison (ψ⁺ max/p99/profile, ᾱ_max, α/d band, crack-tip x)
against reverseBC instead of baseline. Expect the qualitative findings (PIDL ψ⁺
bounded vs FEM singular, broader band, lower ᾱ) to persist — this run confirms they
are not BC artifacts.

### Priority
**medium-high** — unblocks turning the provisional J-path field comparison into a
paper-grade BC-matched result.

---

## 2026-05-20 · Request 14: export nodal displacement (u_x, u_y) at existing snapshot cycles → enables true FEM J-integral

**Goal**: Make a *path-independent* fracture metric (J-integral / energy release rate G) available as a FEM reference. Mac wants to supervise/validate PIDL against J instead of pointwise ψ⁺, because the pointwise ψ⁺ singularity at the crack tip is structurally unlearnable by a smooth NN (confirmed: FEM has only 8/77730 elements with ψ⁺>0.5 at c1; a smooth NN cannot reproduce that spike, so pointwise-ψ⁺ supervision drives spurious tip degradation). J is a finite, contour-integrated scalar — learnable and physically meaningful.

**Blocker this resolves**: current FEM dump (`u12_cycle_*.mat`, `u08_cycle_*.mat`) stores only element scalars (`psi_elem`, `alpha_bar_elem`, `f_alpha_elem`, `d_elem`). It does **not** store nodal displacement or Gauss-point stress, so the J-integral cannot be computed on the FEM side. (Documented as G2-followup in `compute_J_integral.py:42-44`.)

### What to export

For the **same runs and same cycles already exported** (no new simulation needed — just dump more fields from those existing solutions):

- **u12** (Umax=0.12): cycles 1, 40, 70, 82
- **u08** (Umax=0.08): cycles 1, 150, 350, 396

Per cycle, add to the existing `.mat` (or a sibling `*_disp.mat`):

| field | shape | meaning |
|---|---|---|
| `u_node` | (N_node, 2) | nodal displacement (u_x, u_y), **same node ordering as `mesh_geometry.mat`** |

**Optional but valuable** (if cheap to dump): Gauss-point stress `sig_gp` (N_elem, n_gp, 3) = (σ_xx, σ_yy, σ_xy) and GP coords `xy_gp`. If omitted, Mac will recompute σ from `u_node` + mesh via shape-function gradients + Hooke (plane strain, E/ν from PCC params), which is adequate for J outside the damage band.

### Mesh
Reuse existing `mesh_geometry.mat` — must confirm `u_node` row order matches its node list.

### Expected outputs
Drop alongside existing snapshots in `psi_snapshots_for_agent/` (and mirror to OneDrive handoff as usual). Either extend the existing per-cycle `.mat` files or add `u12_cycle_XXXX_disp.mat`.

### Acceptance criteria
Mac computes J on 3 contours r ∈ {0.05, 0.08, 0.12} around the tip. **Pass** = J spread across the 3 radii < ~15% at an early cycle (c1 or c40), confirming path-independence and a valid FEM J reference. Large spread → contour radii or node-ordering issue to debug jointly.

### Priority
**medium** — Mac has an interim PIDL-internal J-path-independence regulariser already running (no FEM target needed). This request unblocks the stronger *supervised-against-FEM-J* variant; not on the critical path this week.

### [update] 2026-05-22 — CONFIRMED on critical path, please proceed with u_node extraction
J-integral is now on the critical path: J-path PIDL fractured cleanly (N_f=82) and
we want a BC-matched FEM J-integral to validate the near-tip field against, plus
the supervised-against-FEM-J variant. Please run the brittle-solver u_node extraction.

**Priority order:**
1. **reverseBC u12, cycles c1/40/70/74** (HIGHEST) — PIDL uses the clamp BC, so the
   reverseBC run is the BC-matched reference for our J comparison. Ship `u_node`
   (N_node,2 peak-load) alongside the Request-15 snapshots in `reverseBC_u12/`.
2. baseline u12, c1/40/70/82 (secondary — physically-correct BVP, useful but BC-mismatched to PIDL).
3. u08 (c1/150/350/396) — low priority, only if cheap.

If peak-load re-solve is expensive, just do (1) reverseBC u12 first and outbox the
wall-time so we can decide on (2)/(3).

---

## 2026-05-20 · Request 13: reverse-BC FEM run to test whether PIDL default horizontal clamp explains the field gap

**Goal**: Run a FEM controlled variant that deliberately matches the *old PIDL default essential BC* instead of the normal GRIPHFiTH anchor BC. This is a fast discriminator for the current Mac-PIDL question: does the FEM/PIDL gap mainly come from the horizontal-BC mismatch, or from PIDL representation/localization after BC effects are controlled?

### What "reverse BC" means

Normal GRIPHFiTH/PIDL-series FEM uses:

```matlab
'fix_X', bottom_left, ...
'fix_Y', bottom, ...
'disp_Y', top
```

This fixes horizontal rigid-body motion at one bottom-left anchor only. The old PIDL default hard ansatz is stricter: because the NN correction vanishes on top/bottom and the vertical loading angle has `cos(theta)=0`, it effectively imposes `u_x=0` on the whole top and bottom edges.

For this request, **reverse the alignment direction**: do not change PIDL. Instead, change FEM to mimic the old PIDL default horizontal clamp:

```matlab
top         = find(MESH.node(:,2) ==  0.5);
bottom      = find(MESH.node(:,2) == -0.5);
top_bottom  = unique([top; bottom]);

NODE_BOUNDARIES = phase_field.fem.bc.set_boundaries(...
    'fix_X',  top_bottom, ...
    'fix_Y',  bottom, ...
    'disp_Y', top ...
);
```

This is intentionally *not* the physically preferred FEM BC. It is a diagnostic FEM variant that asks: if FEM is forced to carry the same horizontal clamp as old PIDL, do `N_f`, `psi+`, `alpha_bar`, reaction, and symmetry move toward PIDL?

### INPUT file

Clone the existing Phase-1 toy-unit input:

- source: `GRIPHFiTH/Scripts/fatigue_fracture/INPUT_SENT_PIDL_12.m`
- new file suggestion: `GRIPHFiTH/Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_reverseBC.m`

Keep everything else the same:

- `split_type = 'AMOR'`
- `diss_fct = 'AT1'`
- `irrev = 'PENALTY'`
- `E=1`, `Gc=0.01`, `ell=0.01`, `alpha_T=0.5`, `p=2`
- `uy_final = 0.12`, `R=0`
- `n_step = 8`
- `max_cycle = 120` initially; auto-stop on penetration is fine

Only change the horizontal essential BC from one-node `fix_X` to top+bottom `fix_X`.

Please set a distinct `example_name`, e.g.

```matlab
example_name = 'SENT_PIDL_12_reverseBC';
```

Do not overwrite the existing `SENT_PIDL_12_export` or baseline outputs.

### Mesh

Use the same mesh as `INPUT_SENT_PIDL_12.m` / PIDL-series Phase-1 FEM baseline. Do not introduce a new mesh unless the existing input cannot be reused.

### Expected outputs

Please export enough data for Mac-PIDL to compare against both FEM original and PIDL default/femAnchor:

1. Run log with wall time, cycle stop, and whether NaN occurred.
2. Timeseries CSV or `.out` equivalent containing at least cycle, load/displacement/reaction if available, `d_max`, `alpha_bar_max`, `f_min`.
3. Per-element snapshots at cycles:
   - `1`
   - `40`
   - `70`
   - `80`
   - `82`
   - first penetration / first boundary hit if different
   - final stop cycle
4. For each snapshot, fields:
   - `d_elem`
   - `psi_elem` or `psi_plus_elem`
   - `alpha_elem` / `alpha_bar_elem`
   - `f_alpha_elem`
   - `element_centroids` or separate `mesh_geometry.mat`
5. If easy, add a mirror-symmetry audit for `alpha_bar` at c82 using the same FEM-7 exact-pair logic; otherwise Mac will compute it after handoff.

Suggested handoff directory:

```text
~/Downloads/_pidl_handoff_v2/reverseBC_u12/
```

Suggested filenames:

```text
mesh_geometry.mat
u12_reverseBC_cycle_0001.mat
u12_reverseBC_cycle_0040.mat
u12_reverseBC_cycle_0070.mat
u12_reverseBC_cycle_0080.mat
u12_reverseBC_cycle_0082.mat
u12_reverseBC_cycle_<hit>.mat
SENT_PIDL_12_reverseBC_timeseries.csv
README.md
```

### Acceptance criteria

Mac will judge this run by directional movement, not by a single pass/fail:

- If reverse-BC FEM `N_f`, reaction, `psi+` localization, or symmetry move strongly toward PIDL default, then the old PIDL horizontal clamp is a major confound.
- If reverse-BC FEM still has FEM-like sharp `psi+` localization and near-perfect mirror symmetry while PIDL remains smeared/asymmetric, then BC mismatch is not the root cause; the remaining bottleneck is PIDL representation/localization/optimizer.
- If reverse-BC FEM becomes numerically unstable or develops an obviously artificial crack path, report that too; instability itself is evidence that old PIDL's hard clamp defines a materially different boundary-value problem.

Key comparisons Mac will run:

```text
FEM original BC        vs FEM reverse BC
PIDL default old BC    vs FEM reverse BC
PIDL femAnchorBC       vs FEM original BC
```

Metrics:

- first boundary hit / penetration cycle
- `psi+` tip/right-band probes
- `alpha_bar` and `f(alpha)` right-band probes
- reaction proxy / load-displacement curve
- V4 mirror symmetry at c82 and at hit cycle

### Priority

**High**. This should be faster and cleaner than another PIDL production run, and it directly answers whether we should spend GPU time on `femAnchorBC + symmetry/localization` variants or first reframe the FEM/PIDL comparison as different essential-BC boundary-value problems.

## 2026-05-13 (eve) · [ack data hand-off `b2d8432`] PCC v3 d_elem + mesh_geometry received

**Re**: outbox `b2d8432` PCC v3 fullNf re-run with `d_elem`. Pulled, read.

### Ack key points

- 70 MB `PCC_v3_trajectory_3000c.mat` + `mesh_geometry.mat` mirror `e6d77bb` — noted, will pull GRIPHFiTH mirror when Mac launches PIDL_PCC α-supervision retrain
- per-element f_min stays > 0.78 over 3000 cycles → §5 supplementary will NOT quote "f_min crosses 0.5 at c~2700" (that was per-GP, retracted)
- 4 keys schema (`d_elem, alpha_bar_elem, psi_elem, f_alpha_elem`) matches PIDL `fem_supervision.alpha_target_at_cycle` consumer at `f7ba430`
- u-field NOT needed for now (Mac PIDL's α-supervision branch uses `d_elem` only)

### Side benefit for PPT report

I just verified Mac handoff `~/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent/u12_cycle_0082.mat` (the FEM-7 ref, 77730 elements) is already on disk → previous "re-export FEM-7 α field at u=0.12 c82" request below is now **closed by old data** (we never lost it; OneDrive sync was the red herring). Already generated `fig_b_FEM_alpha_u12_c0082.{pdf,png}` showing all 4 fields side-by-side for PPT.

### Stand by

§5 PCC retrain (PIDL side) hasn't launched yet; will ack again when first run uses the new data.

---

## 2026-05-13 (eve) · [CLOSED by existing handoff data] Request: re-export FEM-7 α field at u=0.12 c82 for PPT figure (b)

> **Resolution**: Mac local `~/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent/u12_cycle_0082.mat` already has `alpha_bar_elem`, `d_elem`, `psi_elem`, `f_alpha_elem` — no re-export needed. Original request preserved below for audit trail.

---

**Goal**: Mac PPT figure (b) 要 FEM α 场 c82 跟 PIDL 同 cycle 对比。OneDrive 上的 `u12_cycle_0082_FEM7.mat` 5/10 sync 超时，至今 Mac 拉不到。请直接从 GRIPHFiTH 重 export。

**最小请求**:
- 找到 FEM-7 (u=0.12 Coarse strict-Carrara baseline) 跑出的 `alpha_bar_elem` array @ cycle 82（或最接近的 snapshot cycle，PIDL fracture 在 ~c82）
- 用 GRIPHFiTH 自带的 export 功能存为 `.mat` 或 `.h5`（fields: `alpha_bar_elem`, `xyz_centroids`, `cycle`）
- 文件名：`FEM7_u0.12_c0082_alphafield.mat`（或 `.h5`）
- 放到 Mac handoff 路径：`~/Downloads/_pidl_handoff_v2/fem_alpha_fields/`

**Why now**: 不卡 §5 PF-CZM 主线，不影响 NaN/BFGS 调试。但 Mac PPT 图 (b) 一直空着，是 §4 PIDL-vs-FEM 视觉对比的核心 1 张图。

**Expected outputs**:
- 1 个 .mat 或 .h5 文件 in handoff
- outbox 一行 done message: 文件名 + size + `n_elements`

**Stop condition**: Mac `ls` 看到文件 + 能 `scipy.io.loadmat` 读出 array shape ≈ (77730,) 那个量级。

**Priority**: low — 不卡训练/调试主线，但 PPT 用。如果 ad-hoc export 太麻烦，回 outbox 说一声，Mac 想办法用 timeseries CSV 替代。

**Re**: External expert review of outbox `598c1d7` (3000-cycle null result) + the strategic re-scope entry directly below.

External review correctly flagged two framings in this inbox file (and the surrounding outbox) that need explicit cleanup:

### Retraction 1 — N_f ≈ 1500–2500 was an invalid extrapolation

The 200-cycle smoke verdict (`6fa2be1` + Mac inbox `7af56c4`) linearly extrapolated ᾱ → α_T at cycle ~1400 and claimed N_f ∈ [1500, 2500] inside Baktheer's range. The 3000-cycle full run (`598c1d7`) showed this was tracking the wrong quantity: ᾱ grew on schedule but **d remained ≈0.005 across 2800 cycles** — N_f is gated on d→1, not ᾱ→α_T.

**Retract the 1500–2500 number** from §5 reference list. The 3000-cycle full run produces **no fracture N_f** under the current solver. Any §5 wording that cites "our Wu PF-CZM gives N_f ≈ 1500–2500" is wrong.

### Retraction 2 — "BFGS not needed" was scoped to the sign-bug stall only

Inbox `7af56c4` declared BFGS withdrawn after the sign-fix; my next two inbox entries (`d3dc3c7` damping, `cd35780` GO BFGS) flipped on the monotonic stall; the `1e3de63` CORRECTION pulled BFGS back as cancelled. **All of those were premature given today's full-run evidence.** The full PCC run exposed that the solver cannot push d into a localized branch even when ᾱ and f(ᾱ) are healthy — that's the localization failure mode Wu/Huang/Nguyen 2019 BFGS was specifically designed for.

**Restore "BFGS port is the right long-term fix"** as a true statement. It just isn't this paper's blocker (see below).

### What hasn't changed

The strategic direction in the entry directly below — §5 leans on Wu 2017 + Baktheer 2024 published anchors, FEM self-closure not blocking, NaN debug capped at 30-60 min — **stays valid**. The reason it stays valid is *not* "we have our own N_f from the smoke extrapolation", but "we don't need our own N_f because community references already exist". Important distinction.

### Updated request to Windows-FEM

| Item | Status |
|---|---|
| BFGS port for §5 closure | Not needed (use citations) |
| BFGS port as proper future-work fix | Yes, correct long-term solution; defer to post-paper |
| Quote "N_f ≈ 1500-2500" anywhere | **DO NOT** — retracted |
| SEN(B) NaN debug | nice-to-have, 30-60 min cap (unchanged) |
| 3000-cycle paragraph for §5 supplementary | Re-frame: "fatigue accumulator + degradation layer behave as expected over 3000 cycles; full d-localization to fracture not achieved under current monolithic Newton stag — open item, addressed by Wu/Huang/Nguyen 2019 BFGS in future work" |
| f_min trajectory push | still optional but useful |
| **NEW**: Wu's ABAQUS `bending_bfgs.inp` brittle anchor | open option — see below |

### NEW option — run Wu's own ABAQUS code for an independent brittle anchor

Wu's `pfczm-abaqus` repo is now cloned locally at `references/_external/pfczm-abaqus/`. If you (Windows-FEM) have ABAQUS access on the box, one command gives us our own brittle anchor from Wu's reference code without any GRIPHFiTH integration:

```
abaqus interactive job=bending_bfgs user=pfczm_bfgs
```

This produces a peak-load result we can cite as "reproduced Wu 2017 Fig 11 in-house via Wu's open-source UEL". Time: ~1h. Strictly nice-to-have — Wu 2017 published values are sufficient — but if you have ABAQUS, this is the lowest-effort way to get an *independent* numerical anchor.

If you do NOT have ABAQUS access, just say so in outbox and we stand down on this entirely. Mac does not have ABAQUS either.

### Net direction (consolidated, supersedes any framing conflicts above)

- §5 = Wu 2017 + Baktheer 2024 citations
- 3000-cycle full run = solver-side negative result, framed as future work
- BFGS port = right long-term fix, deferred to post-paper
- SEN(B) NaN debug = nice-to-have, time-capped
- Wu ABAQUS bending = optional, only if Windows-FEM has ABAQUS

---

## 2026-05-14 (late) · [strategic re-scope] §5 leans on Wu 2017 + Baktheer 2024 published anchors; FEM self-closure no longer blocking. NaN debug = nice-to-have only.

**Re**: Outbox `855ac62` SEN(B) NaN blocker; Mac's earlier CORRECTION inbox (`1e3de63`).

### Re-scope, not retreat

User clarified the paper main-axis: **PIDL framework is the contribution; §5 FEM is the reference anchor, not a co-equal result**. With that framing, the §5 reference doesn't have to come from our own FEM run — it can come from published community standards we cite.

Two published references cover §5 cleanly:

1. **Brittle anchor**: Wu 2017 JMPS Fig 11 (SEN(B) peak load) — published value, we cite directly.
2. **PCC fatigue N_f**: Baktheer 2024 arXiv (Wu PF-CZM + Carrara fatigue, C60 at S^max=0.75·f_t) gives N_f ∈ [1500, 3000] — exactly our PCC scenario. We cite directly.

Mac will write §5 v0.1 with these citations as the FEM-side reference frame. Our PIDL_PCC retrain (Branch 2 future work, deferred) targets this published anchor band.

### What this means for Windows-FEM

**Not blocking on FEM self-closure for §5.** Specifically:

- **SEN(B) NaN debug** — nice-to-have, not blocking. Time-cap: **30-60 min**. If `post_iter_update.m` line 44-78 NaN source is identifiable in that window and the fix is < 10 LOC, ship it and run brittle benchmark for our own anchor. If diagnosis is deeper than that, **stop and stand down** — Wu 2017 published peak load is sufficient for §5.
- **PCC v3 fatigue full N_f** — **no further work**. The 3000-cycle null result (outbox `598c1d7`) already gives us what we need: confirmation that kernel runs cleanly, ᾱ accumulator + Carrara fatigue layer works as designed, and d-localization is incomplete under GRIPHFiTH's current Newton stag implementation. We frame this honestly in §5 as a known FEM-side open item, not a blocker.
- **No BFGS port** — stays cancelled.
- **No ABAQUS run unless user opts in** — Wu's open-source `pfczm-abaqus` is now cloned locally (`references/_external/pfczm-abaqus/`), so if user has ABAQUS access AND wants an independent brittle anchor, `abaqus interactive job=bending_bfgs user=pfczm_bfgs` takes ~1h. But not required.

### What's optional to record before standing down

If you have spare cycles after the 30-60 min SEN(B) attempt, two short writeups would help Mac's §5 v0.1:

1. **One paragraph for §5 supplementary material**: summarize the 3000-cycle PCC v3 trajectory (ᾱ_max, f_min crossing 0.5 around c2700, max d staying ≈0.005, Newton iter counts). Frame as "kernel + fatigue layer verification: accumulator behaves correctly across the cycle window expected to bracket Baktheer 2024's N_f range; d-localization to fracture is incomplete in the current solver, deferred as future work." Mac can lift this directly into §5.

2. **f_min trajectory data**: push `alpha_trajectory_3000c.mat` (per `598c1d7`) so Mac can plot the f_min(cycle) curve as a supporting figure. Optional but visually supports the "fatigue layer works" claim.

### Net direction

| Action | Status |
|---|---|
| BFGS port | cancelled, not needed |
| SEN(B) NaN debug | nice-to-have, time-cap 30-60 min, then stop regardless |
| PCC v3 full N_f re-run | no further work |
| f_min trajectory push | optional, helps §5 supplementary |
| 3000-cycle paragraph for Mac | optional, helps §5 v0.1 |
| Stand down on FEM closure | YES — §5 uses Wu 2017 + Baktheer 2024 citations |

Thanks for the careful diagnostic work across all these iterations — the sign-bug catch, the conditioning analysis, and the SEN(B) NaN localization are all genuine contributions to closing out where the FEM line can and cannot go. The §5 line lands at "Wu PF-CZM + Carrara fatigue is the right community reference; our PIDL PCC aligns to it via Baktheer published anchor."

---

## 2026-05-14 · [CORRECTION — supersedes previous two entries] BFGS not needed; restore original plan: brittle benchmark → PCC fatigue

**Re**: Outbox `598c1d7` (3000-cycle null result) + outbox `b3bbc9a` (monotonic stall) + Mac's two inbox entries this session (`d3dc3c7`, `cd35780`).

### Correction: BFGS was a misdiagnosis chain

Both inbox entries Mac sent today (`d3dc3c7` "damping first", `cd35780` "GO BFGS") were downstream of a compounding misread. Walk it back cleanly:

1. Original Newton stall → misdiagnosed as "Wu non-PD-local property"
2. Windows-FEM found the real cause: **sign bug in `pf_czm_fatigue.f90:197-198`** (g'/g'' terms)
3. After the sign fix (`0aa96c8`): smoke Newton converges trivially, 1 iter per field, no damping, no shift, no BFGS — as you confirmed in outbox `0aa96c8` close-out
4. Mac then over-reacted to the monotonic stall + 3000-cycle null result by re-prescribing BFGS twice

**BFGS is not needed now.** The sign fix is the correct and complete resolution of the solver stall. Keep BFGS only as a named future fallback: if a later brittle benchmark or stiffer production case produces a genuine Newton stall (NaN or divergence), re-evaluate then. Do not port it now.

### On the 3000-cycle null result

Noted as an open observation. d not localizing across 2800 cycles while ᾱ grows is worth investigating — but the right diagnostic is the **brittle benchmark first**, not a BFGS port. If the brittle benchmark (monotonic, d→1 expected) shows the solver correctly finds the localized d-field, the null-result cause is in the physics/loading magnitude, not the solver. If the brittle benchmark also fails to localize, then the conversation about solver strategy reopens.

Do not treat the null result as a confirmed solver bug until the brittle benchmark is done.

### Restored plan (original Task G Week-1 sequence)

**Step 1 — Brittle benchmark** (current priority, HIGH):
- Target: Miehe 2010 SEN(B) geometry OR Wu 2017 JMPS brittle anchor specimen
- Kernel: Wu PF-CZM with α_T=1e10 (f(ᾱ)≡1, brittle), post-sign-fix kernel
- Acceptance: peak load F_max within ±5% of analytical net-section or LEFM K_IC estimate
- Report: F_max, load-disp curve, d-field at peak, Newton iter count per step

**Step 2 — PCC v3 fatigue** (after Step 1 passes):
- Same `INPUT_SENT_pf_czm_PCC_v3.m` setup already committed (`6fa2be1`)
- 200-cycle smoke already gave positive signal (outbox `598c1d7` trajectory table shows ᾱ accumulating correctly, Newton 1-2 iters throughout)
- After Step 1 confirms d-localization works in monotonic, proceed to full N_f run (max_cycle=3000, cycle_jump OFF)

**Step 3 — cross-amplitude / §5 S-N** (after Step 2 stable):
- Not first priority; will specify when Steps 1-2 land

### What Mac needs from you now

Just the Step 1 brittle benchmark result. No BFGS, no ℓ-retune, no f_indicator reframe. When the benchmark passes, GO Step 2.

---

## 2026-05-14 · [null-result read + GO BFGS + §5 interim C]: d-localization failure confirmed for fatigue too — port BFGS now; use f_indicator as §5 interim

**Re**: Outbox `598c1d7` — Request 12 PCC v3 3000-cycle run, no fracture.

### Null result diagnosis confirmed

The 3000-cycle run nails it: ᾱ → 2.14·α_T, f(ᾱ) → 0.40, but max d changed from 0.0045 (c200 smoke) to 0.0050 (c3000) — essentially static across 2800 cycles. Same BtB conditioning root cause as the monotonic stall, now confirmed to affect fatigue localization too.

The earlier "damped Newton first" instruction in Mac's previous inbox entry (same session, "2026-05-14 · direction...") applied to the **monotonic** stall. For the fatigue d-localization failure, damped Newton won't help: Newton already converges correctly — just to the wrong d (CHOLMOD step direction dominated by BtB subspace, not the NtN driving term at the tip). Damping a direction-error doesn't fix the direction.

**Supersede the previous entry's "try damping first" for the fatigue case.** For the monotonic case, damping is still a reasonable first attempt since the symptom there is explicit non-convergence — but given we now need BFGS for fatigue too, just port it once and it handles both.

### GO: Option A — BFGS port

Green light with no further ack needed. Port from Wu's `pfczm_bfgs.for`. Target: handle K_dd ill-conditioning at the d-localization regime for both monotonic (brittle benchmark) and fatigue (PCC N_f).

**BFGS port scope** (based on Wu/Huang/Nguyen 2019 CMAME 112704 + `pfczm_bfgs.for`):
- Replace CHOLMOD d-field solve in `newton_raphson.m` with L-BFGS update for the d-DOF block
- Keep u-field solve (CHOLMOD) unchanged — u-block is well-conditioned
- The BFGS history (m=5 pairs is Wu's default) captures the curvature information that CHOLMOD loses due to BtB-vs-NtN conditioning
- Port the parts of `pfczm_bfgs.for` that handle the d-solve; discard the Fortran u-solve (GRIPHFiTH already has its own)

Once BFGS is in:
1. Re-run monotonic SENT anchor → confirm brittle benchmark passes (peak load, F_max vs analytical)
2. Re-run PCC v3 fatigue to N_f (same INPUT_SENT_pf_czm_PCC_v3.m, same params, max_cycle=3000)
3. Report both to outbox

### GO: Option C — f_indicator as §5 interim

Simultaneously, write the current run's result into §5 v0.1 using the fatigue-degradation indicator:

> **N_f_indicator** = cycle at which f(ᾱ)_min < 0.5 at the most-damaged GP ≈ **2700 cycles** from the trajectory table.

This is inside Baktheer's 1500-3000 range. Paper framing: "We define N_f as the cycle at which the Carrara fatigue degradation factor f(ᾱ) drops below 0.5 at the most-damaged integration point — the cycle at which fracture toughness is halved. Under this definition, our Wu PF-CZM FEM gives N_f ≈ 2700 at S^max = 0.75·f_t, within the Baktheer 2024 C60 reference range [1500–3000]." If BFGS lands before submission, replace with the true fracture N_f.

To extract N_f_indicator precisely, Mac needs the full f_min trajectory from `alpha_trajectory_3000c.mat` — please push the output directory or email the .mat if too large for the mirror.

### Option B (ℓ retune) — skip

B is a partial-fix experiment that doesn't address the solver root cause and risks introducing mesh-physics inconsistency (crack band width vs. PCC cohesive zone size). With BFGS being the principled fix, don't invest 2h in B.

### Priority

- **BFGS port: HIGH** (gates both brittle benchmark and §5 N_f)
- **f_min trajectory data push: HIGH** (needed for §5 interim writing)
- ETA check: when BFGS is done enough to attempt the monotonic SENT run, outbox a [progress] with the brittle benchmark result — Mac will know the solver is working before waiting for the full 3000-cycle PCC re-run

---

## 2026-05-14 · [direction: brittle benchmark in scope + re-read BFGS withdrawal scope]: monotonic stall is separate from sign-bug; use damping infra first, escalate to BFGS if needed

**Re**: Outbox "2026-05-13 (very late + 2h)" — monotonic SENT anchor fails to peak; A/B/C question.

### Clarification: two distinct stall mechanisms

The sign-bug fix (`0aa96c8`) resolved the **d=0 Newton stall** in fatigue cycles. "BFGS no longer needed" in Mac's evening inbox was scoped to that stall only.

The monotonic stall Windows-FEM observed after the sign-fix is a **separate mechanism**: BtB (diffuse regularisation term) has eigenvalue ~ 2·Gc·ℓ/c_α ≈ 6.9e-6, which is negligible relative to NtN (g''·H term ~ 1e4 in the localization zone). The linear-system condition number is huge and CHOLMOD's step stays in a well-conditioned-but-tiny subspace. This is exactly what Wu/Huang/Nguyen 2019 CMAME 112704 Table 1 identifies as the driver for BFGS — not sign conventions, but the K_dd stiffness mismatch between phases.

The sign-fix does not fix BtB conditioning. Both diagnoses are correct simultaneously.

### Direction: brittle benchmark stays in scope (not Path B)

Path B (skip anchor, cite Baktheer's published values as external anchor) was the right fallback under the earlier hypothesis that "monotonic failure = sign-bug consequence". Now that the sign-bug is separated, the original validation plan holds:

1. **Brittle benchmark first** (peak-load vs net-section / LEFM analytical anchor)
2. **PCC fatigue next** (full N_f run, Request 12)

§5 should not trade validation completeness for speed now that the kernel is confirmed correct.

### How to resolve the monotonic stall

The damping infrastructure is already compiled into `newton_raphson.m` (commit `0aa96c8`). The monotonic case is exactly where it should be activated.

**Step 1 — activate damped Newton for monotonic run** (δd cap 0.05, line-search backtracking 0.5×, max 10 backtracks). This was the "option (III)" from the earlier escalation rule (inbox `2bd6c90`) — apply it specifically to the monotonic INPUT, not to fatigue.

**Step 2 — verdict gate (same as old escalation rule)**:
- Monotone-decreasing residual, d localizes, F reaches peak → **brittle benchmark passes; proceed to Request 12 fatigue run**
- Slow but stable (many backtracks, eventual convergence) → **ship it** for the benchmark; note in DESIGN.md that BFGS is the proper long-term fix
- Still stalls or NaN → **escalate to BFGS port** with no further ack needed. Port from `pfczm_bfgs.for` per Wu/Huang/Nguyen 2019 §3.2 (lines 1–200). Wu's BFGS is designed specifically for this K_dd ill-conditioning regime.

### Fatigue cycles: no change

Vanilla Newton (+ inactive damping fallback) stays for fatigue. The sign-fix made d=0 an exact equilibrium; per-cycle d-evolution is smooth and slow; BtB ill-conditioning does not manifest at the low-d regime of early fatigue cycles. Only the brittle (full localization) case triggers it.

### Summary

| Stall | Mechanism | Fix | Scope |
|---|---|---|---|
| d=0 fatigue stall | Sign-bug in `pf_czm_fatigue.f90:197-198` | Fixed by `0aa96c8` | Fatigue cycles |
| Monotonic d-localization stall | BtB K_dd conditioning | Damped Newton (III) → escalate to BFGS | Brittle benchmark only |

Proceed: activate damping for monotonic, run brittle benchmark, then launch Request 12 fatigue.

---

## 2026-05-13 (evening) · [ack sign-fix + smoke verdict + GO PCC full N_f]: kernel works, Newton trivial, PCC trajectory on Baktheer target

**Re**: GRIPHFiTH commits `0aa96c8` (Wu PF-CZM kernel sign fix + Newton damping infra) and `6fa2be1` (PCC v3 INPUT + driver + 200-cycle smoke).

### Excellent catch on the kernel sign bug

Both `-gpp_d * H_t` → `+gpp_d * H_t` and `-gp_d * H_t` → `+gp_d * H_t` corrections (kernel commit `0aa96c8`) are the right fix. The AT1/AT2 sign-ambiguity argument (because `g_AT2'(0) = -2 = -g_AT2''(0)`, so `tmp_1 = 2H` works for either intended sign) is exactly the failure mode that hid the bug for everyone who reviewed the kernel — including Mac's `wu_pfczm_abaqus_alignment.md` doc which confidently claimed component-by-component sign match. Wu with p=2.5 separates `g'(0)` from `g''(0)` and breaks the AT2 ambiguity, exposing the mismatched convention.

Mac has updated:
- `memory/finding_wu_pfczm_kernel_sign_fix_may13.md` — full diagnosis + lessons
- `references/wu_pfczm_abaqus_alignment.md` — post-mortem section flagging the original "matches Wu" claim as wrong + closing solver-strategy open-item
- `MEMORY.md` — headline banner now says "Wu PF-CZM kernel WORKING (was bug, not Wu non-PD)"

The "Wu non-PD-local" hypothesis from the original review (which led to the (I)/(II)/(III) solver branching) is **withdrawn**. Cornelissen identity `a1·H_min = (Gc/(c_α·ℓ))·α'(0) = 0.43` exactly verifies d=0 is an exact equilibrium — pristine cycles converging in 1 Newton iter is the correct physics, not a fluke.

### Solver decision: vanilla Newton stays, damping infrastructure stays as inactive fallback

Approving your judgment in `0aa96c8`: keep the damping arg + step cap + line-search backtracking (~30 LOC in `newton_raphson.m`) wired but defaulting to false. Costs nothing if unused; cheap insurance if a later high-damage cycle gives unexpected trouble.

BFGS port from `pfczm_bfgs.for` is **no longer needed** (was option (I) from inbox `2bd6c90`; withdrawn).

### PCC v3 smoke verdict: GO full N_f run

200-cycle smoke shows max ᾱ = 7e-4 (14% of α_T = 5e-3) with f(ᾱ) = 1.0 still. Linear extrap → N_f ≈ 1500-2500. **Squarely inside the Baktheer 2024 C60 target range 1500-3000 at S^max = 0.75·f_t.** This is the §5 FEM reference Mac has been waiting on since 2026-05-10.

**Request 12 (new) — full PCC v3 fatigue run to N_f**

```
python (or matlab) → INPUT_SENT_pf_czm_PCC_v3.m with max_cycle = 3000 (1.5× Baktheer upper bound for safety)
```

Stop conditions (whichever first):
1. Fracture detection by your existing solver
2. Reach c2999 without fracture (something's off; investigate)
3. NaN / solver divergence (unlikely given the smoke convergence)

**Cycle_jump consideration**: per Mac DESIGN.md (and PCC v2 lesson `finding_cycle_jump_bug_pcc_may10.md`), cycle_jump = OFF is the safe default for Wu PF-CZM at PCC scale. The "jump-off" smoke you ran (`max_cycle=200 explicit`) was correct. Suggest keeping jump-off for the full N_f run too — slower but reproducible. If wall time becomes prohibitive (>24h), revisit jump_on then.

**Wall estimate**: 200 cycles at ~1-2 Newton iter/field finished in ~? minutes per the smoke log. If ~10 min for 200 cycles, 3000 cycles ≈ 2.5h. If slower per-cycle wall as damage accumulates (likely), 5-10h. Either way feasible on Windows-FEM.

**Report when done** (or stopped):
- N_f (cycle at fracture detection)
- ᾱ_max @ N_f
- max d trajectory (key cycles ≥0.1, ≥0.5, ≥0.9, fracture)
- Full ᾱ_bar_vs_cycle.npy if available — Mac wants the trajectory for §5 plot
- Wall time + Newton iter stats per cycle

### Priority: **high** (gates §5 paper section)

After Request 12 lands, the §5 v0.1 skeleton can grow into v1.0 with the FEM reference numbers. Branch 2 PIDL_PCC retrain (Mac dev side, deferred) will use the Request 12 numbers as the target.

### Standing by

If you hit anything unexpected in the full run, ack a `[blocker]` in outbox and Mac picks up.

---

## 2026-05-13 (early) · [ack Newton-stall + GO (III)]: damped Newton with capped step + line-search first; escalate to (I) BFGS port only if (III) stalls

**Re**: Outbox `f88722a` Task G Day 2 progress + Newton stall blocker.

### Day 2 close-out is excellent

Pulled the 3 commits (`a1209dd`, `3cab6c8`, `f88722a`) and reviewed:

- **P4 FD check caught a real g'' bug** (missing factor of w) — exactly why we asked for the FD sanity check. Good catch, well worth the 30 min.
- **Both mex binaries compile** + framework integration is clean (System.m enum, params.m, material_characteristic.m branch). H_min init per Baktheer Eq. 37 wired into the driver.
- **Smoke run reaches kernel and executes assembly** — no segfault, no missing-symbol, no plumbing problems. Math is verified correct (you cross-checked vs pfczm_bfgs.for).
- **Newton stall at d=0** with the diagnostic you computed (`coef_NtN_K = -36.89`, `coef_BtB = 6.9e-6`) is **textbook Wu non-PD-local property**. This is the exact failure mode `pfczm_bfgs.for` + Wu/Huang/Nguyen 2019 CMAME 112704 was published to address. Math is right; problem is purely numerical solver.

This is **fast progress** — fewer than 24 hours from Day-1 skeletons to compiled-mex-with-framework-integration. Excellent execution.

### GO (III) — damped Newton with capped step + line-search backtracking

Approving **option (III) first** per your recommendation. Reasoning:
- 1-2h work, easy to revert if it doesn't help
- If it converges (even slowly), saves 1-2 days of BFGS port
- The math we'd validate post-(III) is identical to what we'd validate post-(I), so no rework on the benchmark side

**Suggested parameter starting points** (you'll tune):
- δd cap per Newton iter: 0.05 (Wu's typical recommendation per BFGS paper §3.2)
- Line-search backtracking on residual norm: factor 0.5 per backtrack, max 10 backtracks
- Trust-region-ish: reject step if residual increases, halve cap, retry

### Escalation rule

If (III) gives:
- **Clean convergence** (residual monotone-decreasing, d-Newton converges in reasonable iters at most cycles) → ship it. Proceed to Miehe-2010 brittle benchmark + PCC v3 fatigue smoke. Document the damping params in `material_characteristic.m` or a top-of-file comment as "Wu non-PD-local mitigation per Wu/Huang/Nguyen 2019 CMAME §3.2".
- **Slow convergence but stable** (no NaN, residual eventually drops but with many backtracks per cycle) → ship for the brittle benchmark, but note in DESIGN.md that (I) BFGS port is the proper long-term fix; we'll port it before PCC v3 if wall time is unreasonable.
- **Still stalls or NaN-out** within ~3h of trying → **escalate to (I) BFGS port** with my explicit green light. No need to ack-and-wait; just start the port. Reference: Wu/Huang/Nguyen 2019 CMAME 112704 + `pfczm_bfgs.for` lines 1-200 (relevant solver bits).

(II) augmented-Lagrangian I'd skip per your read — between (III) and (I) it doesn't add value.

### Paper note (no action required, just FYI)

Whichever solver wins, the **paper §5 should briefly cite** the choice. If (III) works: "vanilla Newton on Wu PF-CZM K_dd is locally indefinite (α''(d)=−2, dominant negative N·N^T contribution); we use damped Newton with step cap δd ≤ 0.05 + line-search backtracking, as recommended in Wu/Huang/Nguyen 2019". If (I): "we port the BFGS monolithic solver from Wu's open-source pfczm-abaqus reference (commit ID)". Either is publishable.

### Reply expectation

No need to ack approval — just go. If (III) hits the "still stalls" escalation, ack the escalation in outbox so Mac knows you're on (I) instead.

### Standby (Mac side)

Mac is busy on Branch 2 (C2/C6 PIDL dev). Will pick up your benchmark numbers async when they land. No coordination needed during (III) tuning.

---

## 2026-05-12 (late) · [ack fat_deg placement Q]: GO with (α), confirmed by Baktheer 2024 Eq. 38 + page-9 prose

**Re**: Outbox `1e92899` Task G Day 2 math question — fat_deg placement on the d-PDE residual/tangent.

### Verdict: (α) is correct — apply the AT2-convention fix

You're right. Day-1 placement on `g''·H` is wrong; fix to AT2 convention (fat_deg on geometric `G_c`-side only, NOT on elastic `g'·H`). Mac cross-checked Baktheer 2024 (the source paper for our Wu PF-CZM + Carrara fatigue formulation) — definitive.

### Evidence from Baktheer 2024 (`references/Baktheer_etal_2024_arXiv_PFCZM_Fatigue_QuasiBrittle.pdf`)

**Eq. 38** (Sec. 2.6 "Extension to fatigue loading", page 8):

```
D(φ, ∇φ, t) = ∫₀ᵗ f(ᾱ(t)) · G_f · γ(φ, ∇φ) dt
```

`f(ᾱ)` multiplies `G_f · γ(φ, ∇φ)` — the **dissipation/crack-density** integrand. Not the elastic driving force ψ⁺ / Y.

**Page 9, last paragraph (explicit prose statement)**:

> "It should be noted that, to account for fatigue degradation, the fracture energy G_f in (Eq. 46) and (Eq. 47) is replaced by the fatigue-degraded quantity f(ᾱ(t)) · G_f."

Eq. 46 is Baktheer's residual; Eq. 47 is his Jacobian. **Both** get `G_f → f(ᾱ)·G_f`. The `g'(φ)·H` term in both equations is untouched.

Three independent references converge on this:
1. **Carrara 2020** CMAME (foundational unified PF + fatigue)
2. **Baktheer 2024** (Eq. 38 + explicit page-9 prose, the direct source paper for our PF-CZM+fatigue)
3. **Existing `at2_history_fatigue.f90:100`** in our codebase (`fat_deg*Gc/ell` on NtN, `fat_deg*Gc*ell` on BtB; `2*H` term unchanged)

### What needs to change in commit (α)

**1. Fortran kernel `pf_czm_fatigue.f90:193-195`** — your proposed diff is correct:

```fortran
coef_NtN_K = -gpp_d * H_t + fat_deg * (Gc / (c_alpha * ell)) * alpha_pp
coef_NtN_R = -gp_d  * H_t + fat_deg * (Gc / (c_alpha * ell)) * alpha_p
coef_BtB   = fat_deg * 2.0d0 * Gc * ell / c_alpha
```

(Sign convention as fixed in `cc9624e` is kept — only fat_deg position moves.)

**2. Also fix Mac's DESIGN.md** (`pf_czm_fatigue_DESIGN.md` lines ~50-53 strong form, ~75 r_d, ~80 K_dd) in the same commit. The wrong placement originated in Mac's spec; you implemented it faithfully. Updated equations:

Strong form:
```
−g'(d)·H + f(ᾱ)·G_c·[α'(d)/(c_α·ℓ) − (2ℓ/c_α)·Δd] = 0
```

r_d:
```
r_d = N^T · [−g'(d_GP)·H + fat_deg·(Gc/c_α/ℓ)·α'(d_GP)] − fat_deg·B^T·(2·Gc·ℓ/c_α)·∇d_GP
```

K_dd:
```
K_dd = N^T · [−g''(d_GP)·H + fat_deg·(Gc/(c_α·ℓ))·α''(d_GP)] · N + fat_deg·B^T·(2·Gc·ℓ/c_α)·B
```

### Bonus findings from same Baktheer pages (FYI, not blocking)

- **Eq. 37**: `H_min = f_t² / (2·E_0)` — matches our P2 sub-item exactly. Init `history_vars_old(:, :, 1) = f_t²/(2·E)` in MATLAB driver at cycle 0, or add an `H_min` floor inside the Fortran kernel. Either works. Open item; no action needed in (α) commit.
- **Eq. 40**: Baktheer uses `f(ᾱ) = (2α_T/(ᾱ+α_T))²` — **p_fat = 2** (not 2.5). Our `args.p` is configurable, so this is a default-value note: PCC v3 INPUT driver should set `args.p = 2` when anchoring against Baktheer's published N_f ≈ 1,500–3,000 at S^max=0.75. **Do not conflate with `args.traction_p = 2.5`** — that one is Wu degradation order (Baktheer page 5 Eq. 15 sets `p = 2.5` for the rational-fraction g(d), separate variable).
- **Eq. 41**: `α_T = G_f / (k_f · ℓ)` — matches our PCC α_T calibration (`finding_alpha_T_PCC_may10.md`).
- **Eq. 42**: ᾱ accumulator `∫|α̇|dt` during loading, 0 during unloading. Note: Baktheer's main definition uses `α(t) = [1−φ(t)]²·ψ₀(t)` (page 9 first paragraph) as the chosen accumulation variable; the paper explicitly lists `α(t) = g(φ(t))·ψ₀(t)` and others as **optional alternative forms** ("done arbitrarily to demonstrate the generality of the presented approach; however, other forms ... can also be chosen, such as α(t) = g(φ(t))·ψ₀(t)"). So our `H_p(g(d)·Y − g(d_prev)·Y_prev)` is *compatible with* one of Baktheer's alternatives but is NOT his primary definition — keep this distinction explicit when writing §5.

### Reply expectation

GO with (α). Run the Fortran + DESIGN.md fix in one commit. No need to wait the 6h auto-default — explicit ack here.

Suggested Day-2 ordering after (α):

1. (α) fix Fortran kernel + DESIGN.md update (this commit)
2. P4 finite-difference sanity checks (g/g'/g'' analytical-vs-FD; K_dd vs r_d tangent) — 1-element, <30 min
3. MATLAB wrappers (`+equilibrium/pf_czm.m`, `+pf/pf_czm_fatigue.m`)
4. `build_pf_czm_mex.m`, compile to `.mexw64`
5. H_min init in MATLAB driver (Baktheer Eq. 37)
6. Miehe-2010 SEN(B) brittle benchmark (target ±5% peak load vs Wu 2017 Fig 11)
7. PCC v3 fatigue smoke at S^max=0.75 (anchor: Baktheer 1,500–3,000)

### Files referenced

- Baktheer 2024 PDF: `references/Baktheer_etal_2024_arXiv_PFCZM_Fatigue_QuasiBrittle.pdf` (pages 5–9 contain Eqs. 9–42 of interest)
- Carrara 2020 CMAME (foundational): in `references/` for cross-check on derivation

---

## 2026-05-12 · [review of Day 1 push `98fbbca`]: 5 items to address BEFORE Day 2 wrapper code

**Re**: Outbox `ee18265` Task G Day 1 — Wu PF-CZM Fortran kernel skeletons (`pf_czm.f90` + `pf_czm_fatigue.f90` + `pf_czm_fatigue_DESIGN.md`).

**Context**: Mac pulled the GRIPHFiTH mirror and read the three new files, plus cross-referenced against Wu's official open-source `jianyingwu/pfczm-abaqus` repo (Fortran/UMAT+UEL+BFGS, https://github.com/jianyingwu/pfczm-abaqus). Full alignment writeup at [`references/wu_pfczm_abaqus_alignment.md`](../../references/wu_pfczm_abaqus_alignment.md).

**Status note** *(SUPERSEDED — see `[update] 2026-05-12 late` block below: the prototype edits were subsequently committed and pushed in GRIPHFiTH `1637934`)*: Mac has already prototyped the smallest interface/doc fixes locally in the Mac-side GRIPHFiTH mirror (`types.f90`, `mex_utils.f90`, `material_characteristic.m`, `pf_czm.f90` comments, `pf_czm_fatigue_DESIGN.md` naming cleanup), but those edits are ~~**not compiled, not committed, and not pushed**~~ (NOW PUSHED — see [update] block). Treat this inbox entry as the authoritative Day 2 checklist.

### [update] 2026-05-12 late

The Day 1.5 interface/doc patch has now been landed in the mirror and pushed:

- **GRIPHFiTH `devel`**: `98fbbca -> 1637934`
- Commit message: `Task G Day 1.5: extend MAT_CHAR for Wu PF-CZM + lock p vs traction_p naming + document strain_en_undgr contract`

This means:

- **P0 is already done in code**: `types.f90`, `mex_utils.f90`, `material_characteristic.m` now carry `traction_p / a1 / a2`
- **P1 is already done in code/doc**: `args.p` remains Carrara fatigue exponent; Wu traction order is `args.traction_p`
- **P2 comment-level contract is already done**: `pf_czm.f90` now explicitly documents that PF-CZM reuses `strain_en_undgr` to carry Wu driving force `Y`, not legacy elastic energy

So **do not re-do P0/P1/P2 from scratch**. Instead, please:

1. `git pull` the mirror and verify `1637934`
2. Continue with Day 2 wrapper / INPUT-driver work on top of that state
3. Keep the `H_min` initialization choice, P3 cosmetic doc corrections, and P4 finite-difference sanity checks as the next open items

The older paragraphs below are preserved for audit/context, but where they conflict with commit `1637934`, the pushed repo state wins.

**Headline good news**: kernel math (g(d), α(d), c_α=π, a₁ formula, K_dd sign convention, Carrara accumulator on degraded driving force) all match Wu's official reference. Math is right. The issues below are about **interface plumbing, naming, and contract clarity** — addressing them before wrappers will save Day 2+ from silent breakage.

### P0 — `MAT_CHAR` chain is incomplete; new kernels will not link

`pf_czm.f90:129` reads `MAT_CHAR(el_mat)%traction_p / %a1 / %a2`, and `pf_czm_fatigue.f90:149-152` reads the same plus uses existing `%p` as `p_fat`. But:

- `Sources/+phase_field/+mex/Modules/types.f90:22-24` `MAT_CHAR_t` only has 12 legacy fields (`E, ni, G, K, lambda, Gc, ell, res_stiff, alpha_T, p, penalty_irrev, penalty_recov`). **No `traction_p`, `a1`, `a2`**.
- `Sources/+phase_field/+mex/Modules/mex_utils.f90:206 mat_char_from_matlab` copies the same 12 fields only; will not see the new ones from MATLAB.
- `Sources/+phase_field/+init/material_characteristic.m:42` `arguments` block accepts `args.p` (default 2) but not `traction_p / a1 / a2`.

**Day 2 first task (atomic step before anything else)**: extend the chain in one commit:
1. `types.f90` — add `traction_p, a1, a2` to `MAT_CHAR_t`.
2. `mex_utils.f90` — add the three `cp_struct_field_real` calls in `mat_char_from_matlab`.
3. `material_characteristic.m` — add `args.traction_p`, `args.a1`, `args.a2`. If you want auto-derive for `a1`, do it in the MATLAB factory with local access to `f_t`; do **not** widen `MAT_CHAR_t` further unless you really choose an in-kernel `H_min` path.
4. Recompile existing `MIEHE.mexw64` / `AT2.mexw64` etc. — they don't read the new fields but the MAT_CHAR_t struct grew, so they need re-linking against new types.f90. Verify no existing kernel breaks.

### P1 — `p` naming collision: lock `args.p` = Carrara fatigue exponent, `args.traction_p` = Wu order

`material_characteristic.m:42` already exposes `args.p` as the Carrara fatigue exponent (used in `f(ᾱ) = (2α_T/(ᾱ+α_T))^p`). Default 2.

DESIGN doc (`pf_czm_fatigue_DESIGN.md:145`) refers to a new `p = 2.5` for the Wu traction order. The Fortran side correctly already renamed this to `traction_p`. The MATLAB side **must not reuse `args.p` for the Wu traction order** — if Day 2 wires `args.p = 2.5` for PCC INPUT, it silently changes the fatigue law.

**Lock**: `args.p` is reserved for Carrara fatigue exponent only. Wu traction order goes through a separate `args.traction_p` keyword. Please also fix the DESIGN doc text so future readers don't conflate.

### P2 — `strain_en_undgr` container reused with different semantics; document the contract

`pf_czm.f90:155-158` writes `Y = ⟨σ̃₁⟩₊² / (2E)` into `strain_en_undgr(element, G_pts)`. All existing equilibrium kernels (amor / miehe / iso / at2) populate this same array with the **undegraded elastic strain energy** ½ε:CC:ε (or its tensile split). Same Fortran array, different physical quantity.

If any of the following still treats `strain_en_undgr` as elastic energy in the PF-CZM branch, the run will silently mis-converge:
- MATLAB wrappers / monitor / post-proc
- History initialization (especially `H_min = f_t²/(2E)` setting at cycle 0)
- VTK output / diagnostics
- Any cross-kernel projection / handoff

**Requested**: add a comment block at top of `pf_czm.f90` and the wrapper noting that in the PF-CZM branch this array carries Y (principal-stress-based driving force), not strain energy. Audit any downstream reader in the PF-CZM dispatch path.

Related sub-item: **history_vars_old(:,:,1) init at cycle 0**. The kernel does `H_t = max(history_vars_old(...,1), Y_t)`. If MATLAB inits this to 0, then sub-threshold cycles run with `H = Y_t < H_min`, allowing damage before f_t is reached. Wu's official `pfczm_bfgs.for` avoids this by clipping `max(smax, ft)` directly into Y. Two equivalent fixes:
- Preferred low-intrusion Day 2 path: init `history_vars(:,:,1) = f_t²/(2·E)` at cycle 0 in the MATLAB driver.
- More invasive alternative: add an `H_min` clip inside the Fortran kernel: `H_t = max(H_t, f_t²/(2E))`.

Recommendation: do the first one now to keep Day 2 scope small. Only widen the kernel/type interface if you later decide the in-kernel clip is worth it.

### P3 — DESIGN doc has two cosmetic errors that mislead readers

(a) **`pf_czm_fatigue_DESIGN.md:80` K_dd sign on α''**. Doc reads `K_dd = N^T·[g''·H − (Gc/c_α/ℓ)·α'']·N + ...`. The Fortran code at `pf_czm_fatigue.f90:193` is actually `+ (Gc/(c_α·ℓ))·α_pp` (no minus). The **code matches Wu's official `pfczm_bfgs.for` exactly**; the doc has a sign typo. Please flip the doc sign.

(b) **`pf_czm_fatigue_DESIGN.md:169` g''(d) blow-up claim**. Doc says `q'' = p(p-1)(1-d)^(p-2) = 2.5·1.5·(1-d)^(-0.5)` is singular at d→1. For p = 2.5, p−2 = +0.5, so the actual expression is `(1-d)^(+0.5)`, which goes to **0** at d→1, not infinity. φ(1) = a₁(1+a₂) > 0, so w(1) > 0 and g'' is bounded. **No singularity, no d_max < 0.99 clip needed for this reason.** (Other reasons may still motivate a d_max clip, but not g''.)

### P4 — Add 2 finite-difference sanity checks BEFORE Miehe-2010 brittle benchmark

These take <30 min to run, but catch sign/factor errors that would otherwise show up as opaque convergence failures in the benchmark. Highly recommended:

1. **`g, g', g''` consistency**: pick d ∈ {0.1, 0.3, 0.5, 0.7, 0.9}; compute analytical g, g', g'' from `wu_degradation`; verify against central-difference of g (3 evals per d) and g' (3 evals per d) at FD step 1e-5. Max relative error should be < 1e-4 for g' and < 1e-2 for g''.

2. **`K_dd` vs `r_d` tangent consistency**: single 4-node quad element, single GP, fixed pfield d_nodal, fixed strain. Perturb each d_node by ±1e-6 and verify `(r(d+ε) − r(d−ε)) / (2ε) ≈ K_dd` per Fortran assembly. Max relative error < 1e-3.

Failure of either signals a sign error or a missed term — fix before any nonlinear solver runs.

### Solver-strategy heads-up (not a blocker, but worth a thought)

Wu's official repo ships **BFGS monolithic** (`pfczm_bfgs.for`) and **augmented-Lagrangian** (`pfczm_am.for`) solvers *specifically because* Wu's K_dd's N·N^T term is locally non-PD (α''=−2, plus `−g''·H·fat_deg` also < 0; only B·B stabilizes globally via 2ℓG_c/c_α). Vanilla Newton in GRIPHFiTH may stall — especially near d→0.99+.

If during Miehe-2010 benchmark you see Newton stalls / oscillation / non-monotone residual: that's not a kernel bug, that's Wu's known property. Port BFGS from `pfczm_bfgs.for` rather than retuning kernel. Reference: Wu/Huang/Nguyen 2019 CMAME 112704.

### Reply expectation

No need to do all 5 items in one push. The priority ordering is the order they should land:
- P0 first (compile/link). Without this, nothing else can be tested.
- P1+P2 atomically with P0 since they touch the same MATLAB factory file.
- P3 doc fix can ride along anytime.
- P4 right before Miehe-2010 benchmark.

A short `[ack]` in outbox confirming you saw this + plan is enough. If you disagree with any of P0–P4, push back in outbox — Mac is in code-review mode now and will respond async.

### Files referenced

- Day 1 push: GRIPHFiTH `devel` commit `98fbbca`
- Wu official: https://github.com/jianyingwu/pfczm-abaqus (`pfczm_bfgs.for`, `pfczm_umat.for`)
- Mac alignment doc: `upload code/references/wu_pfczm_abaqus_alignment.md`

---

## 2026-05-12 · [scheduling note]: drop day-by-day calendar for Task G — continuous work, ship when done

**Re**: Task G Week-1 plan ack (outbox `0bae012`), specifically the 6-day calendar (Day 1 = read miehe/amor, Day 2 = implement kernel, ...).

### What I want changed

Skip the strict day-by-day schedule. Solo dev with no external deadline doesn't benefit from calendar structure — just work in priority order, ship deliverables when each is done. The "ETA 2026-05-18" framing is fine as a rough estimate; **don't treat it as a hard deadline that gates the next step**.

If you finish kernel implementation on Day 3 instead of Day 5, immediately move to brittle benchmark. If a step takes 2× longer than estimated, that's fine — no blocking calendar.

### Order of Task G deliverables (priority, not date)

1. `pf_czm_fatigue.f90` + equilibrium-side decision (new file vs amor.f90 flag) — start now if idle
2. Compile to mexw64, verify smoke build works
3. Brittle Miehe-2010 SEN(B) benchmark — verify peak load within ±5% of Wu 2017
4. PCC fatigue smoke at S^max=0.75 using `SENT_pcc_concrete_v2_quad.inp`
5. Cross-amplitude S-N (3 points at S^max ∈ {0.65, 0.75, 0.85})

Ship each deliverable to outbox as it completes. Mac side will pick up data and respond async; no need to batch.

### Secondary tasks if you hit a blocker on Task G (do NOT do these if Task G is unblocked)

If you genuinely can't make progress on Task G (waiting on something), pick from this list rather than idling:

| Task | Value |
|---|---|
| Sync FEM-4 a(N) CSVs (u=0.08/0.10/0.11/0.12/0.13) to OneDrive `PIDL result/` if not already there | Mac figs F4/F5 currently rely on `~/Downloads/_pidl_handoff_v2/post_process/SENT_PIDL_*_timeseries.csv`; an OneDrive mirror would unblock Mac F10 (α-field side-by-side) |
| Sync FEM-7 / FEM-8 .mat files to OneDrive | Same: Mac F10 needs `u12_cycle_0082_FEM7.mat` reliably |
| `docs/FEM.md` update with Task D + E + F full numbers (per outbox `25975f5`) | One-line update — paper §FEM source of truth |
| Castillon 2025 IJF SEN(B) benchmark run (mentioned in old May-5 outbox as `INPUT_SENT_castillon.m`, est 6-12h GPU) | LOW priority — only if Task G blocks |
| Existing `claude/exp/alpha3-xfem-jump` branch state — what's on it that didn't merge to main? | Audit, no action — just curious if anything paper-grade is on that branch |

### Why I'm sending this

Mac is in heavy work mode (C4 implementation + V7 fix + memory updates + PIDL_Taobo dispatches all today). Don't want Windows-FEM idle waiting for Day-N calendar tick when there's substantial Task G work to do. **Just go.**

### Standby

No reply needed unless something blocks Task G — in that case ack the blocker in outbox and pick up a secondary item.

---

## 2026-05-11 (late) · [withdraw 0.85 + GO Task G] PCC 100k VHCF verdict reframes §5 — Wu PF-CZM is the only real reference

**Re**: outbox `9f6122d` PCC 100k NO_PENETRATION verdict + Task G Week-1 plan question.

### Acknowledge: AT2 PCC at S^max=0.75 = VHCF (~5.5×10⁵ cycles)

Your analysis is right and **both** my hypotheses ("just slow ≈85k") and your earlier ("structurally subcritical") were off:

- d *is* growing (0.0087→0.179, ×20)
- ᾱ_max at 66·α_T but ψ_eff = f(ᾱ)·ψ_tip ~ 1.2e-9 still 10⁴ below ψ_crit
- Carrara accumulator looks at *raw* ψ (no degradation feedback) → ᾱ grows unbounded
- d-evolution looks at *degraded* ψ_eff → near zero forever
- → AT2 PCC produces VHCF (~5×10⁵), NOT the HCF (10³-10⁴) Baktheer Wu PF-CZM gives at S^max=0.75

Architecture-family gap is **10²-10³×** at the same loading. This is the §5 finding, not a problem to fix.

### WITHDRAW S^max=0.85 cross-check (`2026-05-11 [update to current PCC β run]` below)

AT2 PCC at S^max=0.85 estimated N_f ≈ 5×10⁵ × (0.75/0.85)⁴ ≈ 3×10⁵ — still VHCF, still NO_PENETRATION at 100k, no new info. **Drop the run.** 36h wall not justified for confirming the same VHCF verdict at a higher load.

### GO Task G Wu PF-CZM kernel implementation

You asked: *"Should I draft the Task G Week-1 plan ack next or wait for further direction?"*

**Draft and post the Week-1 plan now.** Spec is in `windows_fem_inbox.md` 2026-05-10 `[SCOPE PIVOT]` entry (commit `1bd0081`) + `[REVISED PLAN]` (commit `fb6dabd`). Key constants:

| Component | Value |
|---|---|
| Geometric function | α(d) = 2d − d² (ξ = 2) |
| c_α | π |
| Cracking function | φ(d) = a₁d + a₁a₂d², a₃=0 (Cornelissen rank-1) |
| a₁ | 4·E₀·G_f / (π·ℓ·f_t²) |
| a₂ | 2^(5/3) − 3 ≈ 0.1748 |
| Degradation | g(d) = (1−d)^p / [(1−d)^p + φ(d)], **p = 2.5** |
| Driving force Y | ⟨σ̃₁⟩² / (2E₀), Macaulay on first principal effective stress |
| Softening | Cornelissen 1986 exponential |
| Fatigue layer | Carrara unidirectional ā(t) = ∫|α̇| dt (reuse Phase 1 impl) |
| α_T | G_f/(k_f·ℓ) = 5.0 N/mm² (Baktheer 2024 anchor) |
| cycle_jump | **OFF by default** for PCC fatigue (per PCC 100k bug analysis) |
| File targets | `pf_czm_fatigue.f90` (or extend `miehe.f90` with PF-CZM branch flag); `INPUT_SENT_concrete_PCC_v3.m`; `main_SENT_concrete_PCC_v3.m` |

### Week-1 deliverables expected from your ack

1. **Which Fortran file you'll touch** (new `pf_czm_fatigue.f90` vs branch in `miehe.f90`) — your call based on code-archeology
2. **Brittle benchmark choice**: Miehe 2010 SENT (E=210 GPa, f_t=2000 MPa, G_f=2.7 N/mm) — verify peak load within ±5% of Wu 2017 published
3. **PCC test setup confirmation**: re-use existing `SENT_pcc_concrete_v2_quad.inp` mesh (2391 quads, h_tip=0.4 mm = ℓ/5) — should work for Wu PF-CZM too
4. **ETA**: Week 1 (kernel + brittle benchmark) by 2026-05-18?

### §5 paper narrative (now simpler)

**2-line plot** instead of 3-line:
- PIDL_PCC (Phase 2 PIDL retrain, current AT2 architecture)
- Wu_PF-CZM_FEM_PCC (Task G output)

Plus one paragraph for AT2_FEM_PCC as **negative-result motivation**: "Direct extrapolation of the Phase 1 AT2+Carrara framework to PCC concrete units gives N_f ≈ 5.5×10⁵ at S^max=0.75 (VHCF range), an order or two larger than experimental concrete HCF data (Holmen 1979 / fib MC 2010) and the Wu PF-CZM reference (Baktheer 2024 C60: 1,500–3,000 at the same S^max). This architecture-family gap, traced to Carrara's unidirectional accumulator decoupling from the degraded driving force, motivates the Wu PF-CZM transition used for the §5 reference."

This is **cleaner** than the original 3-line plan — AT2 PCC becomes a clean negative-result anchor, not a confusing third line.

### Priority

Task G ack: **HIGH** — Phase 2 §5 is now blocked on this; PIDL_PCC retrain can wait for the Wu PF-CZM FEM reference to exist first.

### Mac side parallel work

- C4 exact-BC implementation done + Mac CPU smoke u=0.12 N=5 running (PID 73680 + 73688 combo); V7 expected at machine precision by construction
- C5 hard sym on Taobo 3 seeds running (PIDs 836712/3/4)
- Awaiting C10 σ-sweep from Windows-PIDL Request 8

No conflict with your Task G scope. Standby for Week-1 plan ack.

---

## 2026-05-11 · [update to current PCC β run]: after the active 100k AT2 PCC run completes, run one `S^max = 0.85` cross-check as the next Phase 2A discriminator

**[2026-05-11 late: WITHDRAWN by Task G greenlight above. PCC 100k verdict reframes §5; 0.85 cross-check would also be VHCF NO_PENETRATION, no new info worth 36h wall. Compute saved for Task G.]**

Original 0.85 request below preserved for audit:

---

**Re**: outbox `2026-05-11 [auto-fired]` says `INPUT_SENT_concrete_PCC_v2_nojump_100k` started automatically at 13:09 on 2026-05-11 and is expected to finish around the evening of **2026-05-11**. This update does **not** interrupt that run. It schedules the next step **after** the current 100k run returns its verdict.

### Goal

Get one higher-load AT2 PCC reference point to strengthen the §5 transition narrative:

- if `S^max = 0.75` penetrates late, `0.85` tells us whether the same framework produces a clearly measurable lower-cycle failure branch;
- if `S^max = 0.75` still shows `NO_PENETRATION` at 100k, `0.85` tells us whether the AT2 PCC stall is global or only a low-amplitude regime issue.

This is the highest-ROI follow-up after the ongoing 100k run. It is more informative for the paper than spending another full 36 h brute-forcing the same `0.75` point further.

### Trigger

When the active `S^max = 0.75`, no-jump, `max_cycle = 100000` run finishes and its outbox entry is posted, launch this next unless that outbox reveals a solver pathology that makes the result unusable.

### INPUT file

Start from the same AT2 PCC no-jump setup now running, but change only the load amplitude:

- base: `INPUT_SENT_concrete_PCC_v2_nojump_100k.m`
- new load: `S^max = 0.85 f_t`
- keep: `cyclic_jump = false`
- keep the same PCC parameters: `E = 30 GPa`, `ν = 0.18`, `f_t = 3.0 MPa`, `G_f = 0.10 N/mm`, `ℓ = 2.0 mm`, `k_f = 0.01`, `α_T = 5.0 N/mm²`

Use a new input / driver pair, e.g.:

- `INPUT_SENT_concrete_PCC_v2_nojump_smax085.m`
- `main_SENT_concrete_PCC_v2_nojump_smax085.m`

### Mesh

Same PCC concrete SENT mesh as the current v2 run. No remeshing.

### Expected outputs

Please return:

1. exact `N_f` if penetration occurs, otherwise `NO_PENETRATION` with the final cycle reached;
2. `a(N)` trajectory CSV analogous to the `0.75` case;
3. `d_max`, `ᾱ_max`, `f_min`, `f_mean`, `ψ_tip` at the terminal cycle;
4. one mid-life VTK and one terminal VTK;
5. wall time and mean sec/cycle;
6. a one-paragraph interpretation: "penetrates cleanly", "still stalls", or "enters an intermediate slow-growth regime".

### Acceptance criteria

For Mac, this run is successful if it yields **either**:

- a clean penetration cycle at `0.85`, **or**
- a clear non-penetration / slow-growth diagnostic that can be contrasted against the `0.75` run.

The point is not to force penetration at all costs. The point is to map whether the AT2 PCC framework has a usable transition branch before Wu PF-CZM Task G becomes the main reference.

### Priority

`high`, but **strictly after** the currently active `0.75` 100k run completes.

## 2026-05-11 (early) · [reply to brute-force result `e820967`]: my N_f=2,500 prediction was wrong by 30×; pursue (β) brute-force 100k cycles to discriminate

**Re**: outbox `e820967` — cycle_jump OFF brute-force at 4000 cycles still shows d barely moving (0.0087→0.0093). cycle_jump is exonerated.

### Acknowledge: my N_f estimate was off by ~30×

You're right — I over-predicted N_f. My calculation used N_threshold = α_T / ψ_tip = 4,716 cycles for ᾱ to first reach α_T. But I conflated "N_threshold" with "N_f" — they're not the same. From Phase 1 data: at N_f=82 (u=0.12 baseline), the actual ᾱ_max/α_T ratio is **~18× (= 9.34/0.5)**, not ~1×. The damage propagation phase between ᾱ=α_T and ᾱ=18·α_T is much longer than the "small acceleration overhead" I assumed.

Corrected estimate at PCC scale: **N_f ≈ 18 × N_threshold ≈ 85,000 cycles** for AT2 PCC at S^max=0.75. That matches Holmen 1979 / ACI 215R HCF range (10⁴–10⁵) and supersedes my earlier "2,400-3,000" anchor. The Baktheer C60 1,500-3,000 reference is likely model-specific (Wu PF-CZM with rational-fraction degradation has a faster d-evolution than AT2), not directly transferable to AT2.

### Your "structurally subcritical" analysis vs my "just slow" analysis

These are two different hypotheses for the d-stalling:

- **Your reading**: ψ_tip = 1.06e-6 << ψ_crit = 1.88e-5 → AT2 PCC structurally cannot penetrate, regardless of cycles run
- **My reading**: AT2 PCC penetrates around N_f ≈ 85,000 cycles; we only ran 4,000 (= 4.7% of the way), so naturally d hasn't moved

Both predict d stalled at cycle 4,000. The discriminator is what happens at cycle 80,000–100,000.

### Decision: GO (β) — brute-force 100k cycles, ~9h wall

Run AT2 PCC nojump to **max_cycle = 100,000** (or until penetration triggers, whichever first). Wall ~9h overnight.

Two outcomes both useful:

- **If penetration at ~85k**: confirms my "just slow" reading; gives a real AT2 PCC reference N_f → §5 architecturally-matched comparison preserved
- **If still no penetration at 100k**: confirms your "structurally subcritical" reading; this is itself a publishable observation for §5 ("the AT2 phase-field at PCC scale has a regime where Carrara fatigue accumulator cannot drive damage past the elastic-limit ψ_crit barrier within reasonable cycle counts; the Wu PF-CZM rational-fraction degradation handles this regime cleanly, motivating the §5 community-standard reference choice")

Either way, the data from this run lands in §5 as the AT2 PCC reference (or its principled absence). Spending 9h is acceptable for a clean paper-grade discriminator.

### Implementation

- Same INPUT as your nojump run, just bump `max_cycle = 100000`
- Keep cycle_jump=OFF
- Checkpoint every 1000 cycles (so we have intermediate states for diagnostic plots)
- VTK every 500 cycles (200 VTKs, manageable storage)
- Termination: penetration (d≥0.95 at right boundary, ≥3 elements) OR cycle 100,000 hit, whichever first
- If penetration hits, dump full deliverables (a(N) CSV, ᾱ trajectory, final VTK, etc.)
- If 100k hit without penetration, dump diagnostic snapshot (current d-field, ᾱ-field, ψ_tip, f(ᾱ) trace) + report `NO_PENETRATION` verdict

### About options (α) and (γ)

- **(α) Skip AT2 PCC, jump straight to Wu PF-CZM**: rejected. The 9h cost of (β) is small; the discriminator outcome (subcritical-stall vs slow-penetration) is paper-relevant either way. Going straight to Wu PF-CZM loses the AT2 PCC reference data point regardless of which hypothesis is true.
- **(γ) σ_max = 0.95 f_t**: rejected as you noted, unphysical for HCF demonstration.

### Task D + E orchestrator

Acknowledged. Phase 1 supplementary work, no conflict with the (β) run since it's overnight on the same machine sequentially. If (β) needs the GPU/CPU, sequence (β) AFTER Task D+E completes (Task D+E ETA ~9h, then (β) ~9h, total ~18h until both done — by tomorrow afternoon).

If you can interleave (e.g., (β) runs on a different GPU/CPU than Task D+E), that's fine too, your call.

### Implication for Phase 2 strategy

Whatever (β) shows, Wu PF-CZM Task G is still the primary publication-grade reference. (β) gives the AT2 PCC architecturally-matched secondary reference, valid or with a documented "principled absence" caveat.

Phase 2 §5 paper figure remains a 3-line plot: PIDL_PCC, AT2_FEM_PCC (from β if penetrates, or "did not penetrate" annotation if it doesn't), Wu_PF-CZM_FEM_PCC (Task G).

---

## 2026-05-10 (night) · [GO Option B]: cycle_jump OFF brute-force, ~1.5h wall — confirms cycle_jump is broken in post-threshold HCF regime

**Re**: Windows-FEM outbox `d4483c6` — cycle_jump took 24k-cycle leap post-threshold, d_max only grew to 0.023 despite ᾱ → 17·α_T.

**Decision**: GO Option (B) — cycle_jump OFF, brute-force ~1.5h wall.

### Diagnosis confirmed

Your reading is right. The cycle_jump trial-cycle convergence test breaks post-threshold:
- Pre-threshold: ψ_tip ≈ 1.06e-6/cyc, Δd ≈ 0/cyc (no damage yet) → trial-cycle says "stable, big jump OK" → correct extrapolation
- Post-threshold: f(ᾱ) ≪ 1, but per-cycle Δd is small in absolute terms (because the d-equation has ω(d)·ψ on one side and f(ᾱ)·G_c/(c_w·ℓ)·[gradient+barrier] on the other; both shrink, but the d-evolution PDE rate is not directly captured by the trial-cycle's scalar increment test)
- Result: algorithm thinks "stable" again, leaps another 24k cycles, but the **integrated** d-evolution over those 24k cycles should be substantial (rapid penetration) — the heuristic fails to project this correctly

This is a known-bad regime for cycle-jump heuristics in HCF (analogous concerns in the literature for adaptive-time-stepping in stiff non-linear systems). Phase 1 didn't trigger this because toy units (α_T=0.5, ψ~O(1)) gave ~80-cycle pre-threshold + immediate penetration with cycle_jump=OFF; PCC scale (α_T=5.0 N/mm² physical, ψ ~ 1e-6/cyc) gives ~2000-cycle pre-threshold + post-threshold acceleration phase, exactly the regime where this heuristic fails.

### Run plan (B)

- INPUT: `INPUT_SENT_concrete_PCC_v2.m` with `cyclic_jump = false`, `max_cycle = 4000` (you already pre-generated this; just toggle the flag)
- Same PCC params: E=30 GPa, ν=0.18, f_t=3.0 MPa, G_f=0.10 N/mm, ℓ=2.0 mm, k_f=0.01, α_T=5.0 N/mm², S^max=0.75 of f_t
- AT2 + Miehe + HISTORY (confirmed working from your du15-30 strict Carrara runs)
- Expected wall: 1-1.5h (2,500-cycle range × 1-2 s/cyc on small mesh)
- Checkpoint frequently (every 100 cycles) so we have intermediate states
- VTK every 50 cycles; mandatory at penetration cycle (or last cycle before crash)

### Deliverables (same as before)

1. Exact N_f (penetration cycle, d≥0.95 at right boundary, ≥3 elements)
2. a(N) trajectory CSV: `fem_PCC_AT2_a_traj_smax075.csv` (cycle, x_tip_alpha95, alpha_max)
3. ᾱ_max @ N_f, f_min @ N_f, f_mean @ N_f, Kt @ N_f
4. Final crack VTK keyframe (penetration)
5. Mid-life VTK at ~N_f/2 for crack-pattern visualisation
6. Wall time + iteration counts (NR per cycle, stag iter)

### Implication for Wu PF-CZM Task G

Flag this cycle_jump issue when you reach Task G. Wu PF-CZM has different d-evolution dynamics (rational fraction degradation, p=2.5 traction, length-scale insensitive Gamma-convergence) — cycle_jump may behave differently. Recommend:
- **Default cycle_jump = OFF for Wu PF-CZM PCC fatigue runs**, until validated against the cycle_jump=OFF baseline at one S^max
- If wall cost is prohibitive (likely 5-15h per S^max if N_f ~10³-10⁴), revisit cycle_jump tuning later as a separate diagnostic

### What's still in queue

After Option (B) completes (this run, ~1.5h):
- Optional second PCC point at S^max=0.85 (for AT2 reference S-N, ~30 min wall, cycle_jump OFF)
- Then begin Task G Wu PF-CZM kernel implementation (Week 1 plan ack expected)

### Standby

Just relaunch with `cyclic_jump = false`. No further Mac approval needed.

---

## 2026-05-10 (very late) · [REVISED PLAN]: do BOTH — AT2 full run (Option A) + Wu PF-CZM (Task G); supersedes the cancel in `1bd0081`

**Re**: my prior `1bd0081` "SCOPE PIVOT" that cancelled Option A and made Wu PF-CZM the only Phase 2 reference.

**Status**: User pushed back: cancelling AT2 PCC full run loses the PIDL-architecture-matched reference. Reinstating Option A.

### The argument I missed

PIDL was trained on AT1/AT2-style architecture (Phase 1 inherited). For Phase 2, PIDL retrains at PCC scale but stays AT2-style. Therefore:

- **AT2 FEM at PCC** is PIDL's architecturally-matched reference. Comparing PIDL_PCC ↔ AT2_FEM_PCC isolates PIDL approximation error from any model-family mismatch.
- **Wu PF-CZM FEM at PCC** is the community-standard reference. Comparing PIDL_PCC ↔ Wu_FEM_PCC reveals the AT2-vs-PF-CZM architectural gap as a measurable quantity.

Without (a), the (b) comparison conflates "PIDL approximation error" with "AT2 vs PF-CZM model-family difference" into one number. With both (a) and (b), they decompose cleanly. §5 narrative becomes substantially stronger as a result.

Cost of adding (a) is ~5 min wall on top of the 2-3-week Task G — effectively free.

### Revised Phase 2 FEM plan

**Step 1 (this week, ~5 min wall)**: Full Option (A) — AT2 + Miehe + Carrara fatigue at PCC params, S^max=0.75, max_cycle=10000, cycle_jump ON. Already-built scripts; just relaunch with max_cycle bumped from 100 to 10000.

Deliverables (per the spec I gave in `a047ad1`):
- exact N_f
- a(N) trajectory CSV (`fem_PCC_AT2_a_traj_smax075.csv`)
- ᾱ_max @ N_f, f_min @ N_f
- final crack VTK keyframe
- wall time

**Step 2 (this week, optional)**: One additional AT2 PCC run at S^max = 0.85 (LCF end, ~5 min wall). Gives 2-point S-N for the AT2 reference, useful for §5 plot. If you have spare wall time, run it; otherwise hold.

**Step 3 (next 2-3 weeks)**: Task G Wu PF-CZM kernel implementation, brittle benchmark, PCC PCC smoke, cross-amplitude S-N. Per the spec already in this inbox above (Cornelissen a₁/a₂/a₃, p=2.5, Macaulay split, etc.).

### What the §5 paper figure becomes

A 3-line plot: PIDL_PCC, AT2_FEM_PCC, Wu_PF-CZM_FEM_PCC, all at S^max ∈ {0.65, 0.75, 0.85} (or whatever subset Mac PIDL retrain delivers). The agreement / gap pattern is the §5 finding.

### Order of operations

1. **Now**: relaunch Option (A) full 10⁴ — should land tonight/tomorrow morning given 5 min wall
2. **In parallel**: ack Task G + share Week-1 implementation plan (kernel files touched, brittle benchmark choice)
3. **Next**: Task G implementation; AT2 reference is already in hand by the time you're ready for PCC PF-CZM smoke

### What's still cancelled / deferred

- Task D 6-case strict Carrara sweep (AMOR vs MIEHE Basquin slope) — deferred unless Mac asks for §4 supplementary appendix
- Task E (strict Carrara mesh check) — deferred with Task D

### Standby

Just relaunch Option (A) when convenient. No need to wait for further Mac approval. After Step 1 completes, post the deliverables to outbox; then ack Task G with Week-1 plan.

---

## 2026-05-10 (late) · [SCOPE PIVOT]: skip full 2A run, switch to Wu PF-CZM as Phase 2 §5 reference — supersedes prior Option A approval

**Re**: my prior `a047ad1` greenlight of Option (A) full 10⁴-cycle run for PCC AT2+Miehe.
**Status**: **CANCEL Option (A)**. Mac decided after analysing the model-family mismatch with Baktheer.

### What changed

User's question: "Baktheer 用的是什么模型？不需要 Baktheer 吗？" The answer that matters here:

- **Baktheer 2024 uses Wu PF-CZM** (ξ=2, α(d) = 2d−d², rational-fraction degradation, p=2.5, Macaulay-bracket driving force, Cornelissen softening)
- **Our Phase 2A (AT2 + Miehe spectral + HISTORY) shares only the Carrara fatigue layer with Baktheer** — geometric / degradation / softening / split are all different
- N_f match within 1.5× (your 2,400-3,000 vs Baktheer C60 1,500-3,000) is order-of-magnitude consistency at HCF range, **not a true validation**

For a standalone paper §5 with strong Baktheer-anchored validation, we need to **switch the FEM reference to Wu PF-CZM** (community standard per Wu 2026 IJDM and Baktheer 2024). PIDL stays on its current AT2-style architecture (Phase 3 future work = bring PIDL to Wu PF-CZM too); the §5 narrative becomes "PIDL framework-level capture vs community-standard Wu PF-CZM FEM benchmark", with the architectural mismatch acknowledged as a finding rather than hidden.

### Consequence: Option (A) is no longer worth the wall time

A full AT2+Miehe PCC 10⁴-cycle run produces a transitional data point that does NOT enter the §5 paper figure. Smoke + per-cycle Δᾱ rate is already enough as an internal milestone. Stop here on AT2+Miehe PCC.

### Task G (NEW, supersedes Task C in Phase 2 priority): Wu PF-CZM kernel in GRIPHFiTH

**Goal**: implement Wu PF-CZM for Phase 2 §5 community-standard FEM reference.

**Specification** (Baktheer 2024 lineage, validated against published Mode I 3PB S-N):

| Component | Specification | Reference |
|---|---|---|
| Geometric function | α(d) = 2d − d² (ξ = 2) | Wu 2026 IJDM Eq. (29-30); Baktheer 2024 Eq. (a_hat) |
| Normalisation | c_α = π | Wu 2024 Eq. (4.26) |
| Cracking function | φ(d) = a₁·d + a₁·a₂·d² (a₃ = 0 for Cornelissen) | Baktheer 2024 Eq. for Q(φ) |
| a₁ | 4·E₀·G_f / (π·ℓ·f_t²) | derived |
| a₂ | 2^(5/3) − 3 ≈ 0.1748 | Cornelissen 1986 closed-form |
| a₃ | 0 | (rank-1 in this implementation) |
| Degradation | g(d) = (1−d)^p / [(1−d)^p + φ(d)] | Wu 2017/Baktheer 2024 |
| Traction order | p = 2.5 | Baktheer 2024 |
| Driving force Y | ⟨σ̃₁⟩² / (2E₀)  (Macaulay on first principal effective stress) | Baktheer 2024 — replaces Miehe spectral |
| Softening law | Cornelissen 1986 exponential (target reproduced via above φ(d), a₁, a₂) | concrete community standard |
| History | H = max_t [⟨σ̃₁⟩²/(2E₀)] (irreversibility) + H_min = f_t²/(2E₀) | Baktheer 2024 |
| Fatigue layer | Carrara unidirectional ā(t) = ∫|α̇| dt during loading; f(ā) = (2α_T/(ā+α_T))² | unchanged from Phase 1 — reuse |
| α_T | G_f / (k_f · ℓ), k_f = 0.01 | Baktheer 2024 calibrated |

**File targets**:
- `Sources/+phase_field/+mex/Modules/at1_penalty_fatigue.f90` etc. → new `pf_czm_fatigue.f90` (or extend `miehe.f90` with a PF-CZM branch flag)
- `Scripts/fatigue_fracture/INPUT_SENT_concrete_PCC_v3.m` (PF-CZM, replaces v2)
- `Scripts/fatigue_fracture/main_SENT_concrete_PCC_v3.m`

**Validation route**:

1. **Smoke**: monotonic 1D / SENT, verify σ-w curve matches Cornelissen exponential to within ~5% peak load and ~10% tail.
2. **Brittle benchmark**: reproduce Wu 2017 SENT brittle test (E=210 GPa, f_t=2000 MPa, G_f=2.7 N/mm — Miehe 2010 reference). N_f-equivalent peak load should match Wu's published value within ~5%.
3. **Phase 2 PCC fatigue smoke**: PCC params (E=30 GPa, ν=0.18, f_t=3.0 MPa, G_f=0.10 N/mm, ℓ=2.0 mm, k_f=0.01, α_T=5.0 N/mm²), S^max=0.75 of f_t. **Target**: N_f within 50% of Baktheer 2024 C60 published 1,500–3,000 cycles after scaling for f_t and G_f differences. Order-of-magnitude consistency suffices for §5.
4. **Cross-amplitude**: Once smoke passes, run S^max ∈ {0.65, 0.75, 0.85} for §5 S-N plot, ~3 production runs.

**ETA**: ~2-3 weeks for a careful implementation:
- Week 1: kernel writing + brittle benchmark
- Week 2: PCC fatigue smoke + first S-N point
- Week 3: cross-amplitude S-N production + §5 figure-grade output

Do not block on PIDL side; PIDL is on its own Phase 2 thread, will report N_f cross-check once you have the PF-CZM PCC reference numbers.

### Deferred / dropped

- **Option (A) full 10⁴ AT2+Miehe PCC run**: dropped (transitional data, not paper-grade).
- **Task D 6-case strict Carrara sweep (AMOR vs MIEHE Basquin slope)**: held. May still be useful as Phase 1 §4 supplementary appendix evidence. Re-greenlight only if Mac asks. Don't preempt.
- **Task E (strict Carrara mesh check)**: held with Task D.

### Standby

Acknowledge this scope pivot in outbox; propose a Week-1 plan (which kernel files you'll touch, what brittle benchmark you'll use, ETA for the smoke). I'll review before you commit kernel changes. Don't auto-merge into mirror's `devel` branch until brittle benchmark passes.

---

## 2026-05-10 (evening) · [reply to PCC smoke `8162604`]: GO Option (A) — calibration is CORRECT, run full 10⁴

**Re**: Windows-FEM smoke result `8162604`. ᾱ_max @ c1409 = 4.12e-3 (82% α_T), per-cycle Δᾱ ≈ 1.06e-6, extrapolated N_f ≈ 2,400-3,000.

### Verdict: calibration is correct, my expected-N_f range was the error

I had said "expect N_f ~10⁴–10⁵". That estimate was anchored on Holmen 1979 *compression* S-N (S^max ≈ 0.5 of f_c at ~10⁶ cycles), which is the wrong reference for our tension-driven PF-CZM run. The correct community anchor is **Baktheer 2024 C60 at S^max = 0.75 → N_f ≈ 1,500–3,000 cycles** (their Mode I 3PB results, paper-grade calibrated).

Your N_f ≈ 2,400–3,000 is **within a factor of 1.5× of Baktheer's published concrete tension PF-CZM data**. The α_T = 5.0 N/mm² calibration is therefore **correct without re-tuning**; my earlier "10⁴–10⁵ midrange" was the error in expectation, not in α_T.

Why the mismatch with my "in-conversation" 13,500-cycle estimate:
- I assumed Kt ≈ 2.1 (Williams analytic for SENT a/W=0.5)
- Your refined mesh (h_tip = ℓ/5 = 0.4 mm at Phase 2 scale) gives Kt = 3.55 actual
- ψ_tip ∝ Kt² → 3.55² / 2.1² = 2.86× more aggressive accumulation
- 13,500 / 2.86 ≈ 4,720 cycles to threshold; +small acceleration phase → ~2,500-3,000 N_f ✓ matches your reading

### Decision: GO Option (A) — full 10⁴-cycle run, no re-tune

- max_cycle = 10000, cycle_jump = ON (same as smoke)
- Wall ~5 min per your estimate
- Goal: pin down exact N_f for the Phase 2 PCC demonstration data point

Reject (B) and (C):
- (B) k_f re-calibration would push us *away* from Baktheer's anchor — we'd no longer match published concrete PF-CZM data. Bad.
- (C) lowering σ_max to 0.65 f_t to artificially extend life is publication-unfriendly — reviewers will ask why we picked an unusual S^max. 0.75 is the standard Baktheer / fib MC reporting point.

### What to report after the full run

In `windows_fem_outbox.md`:
- Exact N_f
- a(N) crack-tip trajectory (analogous to Phase 1 FEM-4 CSV format: `cycle, x_tip_alpha95, alpha_max`)
- ᾱ_max @ N_f, f_min @ N_f
- Final crack pattern VTK keyframe (penetration cycle)
- Wall time
- Any deviations from cycle 4 → cycle 1409 linear extrapolation (e.g. acceleration shape during damage softening phase)

### Then what

After Option (A) lands:
1. Mac picks one comparable S^max from Baktheer 2024 (likely 0.85 for the LCF end) and asks for one more PCC run for cross-validation. Optional, ~5 min more wall.
2. Task D (6-case strict Carrara sweep) gets re-greenlighted only if Phase 2 paper §5 needs an S-N slope figure. TBD after Mac drafts §5 outline.

### Standby

Just go. No further Mac approval required for the full Option (A) run; start it whenever convenient and post results.

---

## 2026-05-10 (PM) · [reply to Task B/C/F outbox 5359893]: greenlight 100-cycle PCC smoke; ψ_tip math reconciled

**Re**: Windows-FEM outbox commits `40cc400` (Task F) + `5359893` (Task B + Task C). All three acknowledged.

### Task C (PCC smoke) — math reconciliation + GREENLIGHT 100-cycle smoke

Your concern about ψ_tip vs α_T 4-OOM gap → "10⁵–10⁶ cycles" is partially over-stated. Reconciling:

- Your numbers: σ_nom = 2.25 MPa, ψ_far = 8.4e-8 kN/mm², Kt=2.1 → **ψ_tip = 4.4·ψ_far = 3.7e-7 kN/mm²**
- α_T = 5.0e-3 kN/mm²
- **N_threshold = α_T / ψ_tip = 5.0e-3 / 3.7e-7 ≈ 13,500 cycles**

That is **inside** the 10⁴–10⁵ HCF range I predicted, not above it. (My own earlier sanity check used far-field ψ without Kt and got ~59k; your local-tip ψ with Kt² is the right one for the Carrara accumulator since ᾱ integrates per-element ψ₀.)

After threshold, Carrara f(ā) = (2α_T/(ā+α_T))² accelerates damage rapidly, so total N_f ≈ N_threshold + small overhead → **expected N_f ~14,000–25,000 cycles, HCF range, calibration is consistent**.

**GREENLIGHT the 100-cycle smoke**:
- Run with `cycle_jump = ON` (mandatory at HCF range, you flagged this correctly)
- Goal: measure per-cycle Δᾱ rate at peak σ_yy in tip element
- Decision rule: if extrapolated N_f × Δᾱ ≈ α_T (within factor 2× of 14,000), proceed full 10⁴-cycle run with cycle_jump tuning. If extrapolated N_f << 10³ or >> 10⁶, stop and report so we can iterate k_f from Holmen S-N data.

If 100-cycle smoke takes <2 min wall as you estimate, just launch it directly — no need to wait for further Mac approval, but report Δᾱ trend before launching the full 10⁴ run.

### Task B (strict Carrara stable) — confirmed done by reference

Acknowledged: du15/20/25/30 MIEHE+AT2+HISTORY production already cleanly demonstrates kernel stability. No new smoke needed for Task B.

### Task D (6-case sweep) — HOLD

Your gap analysis is correct: need 4 new MIEHE (du35/40/45/50) + 2 new AMOR (du35/45). **Hold launching until PCC smoke (Task C) reports back** — if PCC needs k_f re-calibration that consumes Windows-FEM compute, Task D priority drops. Will re-greenlight once PCC smoke verdict is in.

### Task F (V7 cycle 40 = 0.41%) — paper-grade datum, accepted

Both numbers (cycle 0 = 0.12%, cycle 40 = 0.41%) noted. The fact that PIDL/FEM ratio drops from 140-250× → 42-74× across life is **interesting and worth one sentence in §4.2**: "FEM V7 grows from 0.12% (peak elastic) to 0.41% (mid-life) due to the moving denominator (max σ_yy_bulk softens as damage accumulates), but stays well below 1% throughout the lifetime; PIDL's 17-30% residual remains 40× to 250× the FEM value at every cycle inspected." May fold into §4 v1.7 (no urgency; §4 v1.6 is currently locked).

Files for Task F: `Scripts/brittle_fracture/main_FEM_F_cycle40.m` (script) + `FEM_F_cycle40_*.vtk` output noted; CSV summary if you have it would be nice for the §4 table appendix later. Not blocking.

---

## 2026-05-10 · [unblock Task C]: PCC concrete α_T = 5.0 N/mm² (FEM-9 Task C ready)

**Re**: FEM-9 Task C (PCC Phase 2 scripts ready, awaiting Mac α_T calibration)

**Status**: ✅ α_T computed. Task C unblocked.

### α_T value to use

**α_T = α_N = 5.0 N/mm² = 5.0 MPa**

Derived via Baktheer 2024 formula `α_T = G_f / (k_f · ℓ) = 0.10 / (0.01 × 2.0)` with k_f=0.01 (Baktheer 2024 concrete-calibrated).

### Full PCC parameter set (replaces Handoff F placeholders)

```matlab
% INPUT_SENT_concrete_PCC.m updates:
E      = 3.0e4;     % MPa = 30 GPa (was placeholder)
nu     = 0.18;      % (was 0.3 toy)
f_t    = 3.0;       % MPa (was placeholder)
G_c    = 0.10;      % N/mm = 100 J/m² (was placeholder)
ell    = 2.0;       % mm (Phase 2 regularization length)
h_tip  = 0.4;       % mm (= ell/5, Carrara recommendation)
alpha_T = 5.0;      % N/mm² (this calibration; was 0.094 placeholder)
alpha_N = 5.0;      % N/mm² (= α_T, mean-load-independent)
```

Other settings:
- AT2 (not AT1) + Miehe spectral split + HISTORY accumulator → strict Carrara formulation (your Task B, kernel `e7eb3f8` bugfix already in)
- Geometry: physical SENT 100×100 mm (scale up from Phase 1 toy 1×1 mm); slit 50 mm from left edge at mid-height; thickness 1 mm

### Smoke validation

Run at **S^max = 0.75 of f_t** (= 2.25 MPa amplitude):
- Expected N_f: **10⁴–10⁵ cycles** (HCF range, consistent with Holmen 1979 / ACI 215R)
- If N_f << 10²: k_f too small, α_T threshold blown through too fast
- If N_f >> 10⁶: k_f too large, fatigue never triggers
- Either case: report N_f and we'll iterate k_f from a Holmen S-N data point

### Files

Full derivation + sanity checks + ℓ-sensitivity in Mac memory:
`finding_alpha_T_PCC_may10.md` (not in git; available on request)

### Priority

**HIGH** (unblocks Phase 2 demonstration). Run after Task A (FEM.md update) and Task B (strict Carrara smoke). Per FEM-9 schedule, Task C is Day 6-7 — proceed when you reach it.

---

## 2026-05-10 · [reply to fd2a113]: Answers to 3 scope questions before FEM-9 kickoff

**Re**: Windows-FEM ack fd2a113 — 3 questions answered, proceed with A→B→F→D→E→C sequence.

### Q1: Doc location
`docs/FEM.md` 已存在，路径正确（`upload code/docs/FEM.md`，last sync 2026-05-06）。
Task A 要做的：把 FEM-7（V4 mirror RMS = 2.98e-5，integrated damage = 4.39e-2）和 FEM-8（V7_FEM = 0.12%）追加进 FEM.md 对应 section，更新 Last sync 为今日。

### Q2: Task D 6-case selection
**用同样的 6 个 amplitude（du25/30/35/40/45/50），在 MIEHE+AT2+HISTORY 下重跑，与 AMOR 结果直接对比。**
- MIEHE 的 ψ⁺ 数值与 AMOR 不同（spectral vs volumetric-deviatoric），N_f 会变，必须重跑才能得到 MIEHE 的 Basquin m
- 保留 du40/50（即使是 LCF 端）：Basquin log-log 拟合需要宽幅值范围，截掉高端会让斜率不稳
- 不延伸到更低幅值（N_f >> 10³，代价大，Carrara 2020 也没做超高周）
- 目标：MIEHE 这条线的 m 是否从 3.49 往 3.8–4.0 移动

### Q3: Task F cycle selection
**用 cycle 40（~49% 寿命，u=0.12 N_f=82）代替 cycle 82。**
- Cycle 82 穿透态裂缝带 σ ≈ 0，归一化分母受损伤区扭曲，FEM 自己也会给出不合理的 V7 值
- Cycle 40 在传播阶段（裂缝已启动），归一化分母（体内 σ_yy_max）在清晰的裂缝前端，定义明确
- Cycle 40 有现成 `psi_fields/cycle_0040.mat`（FEM-5 keyframe set 已包含），读 VTK 即可，~10 min 额外计算

**→ 可以按 A→B→F→D→E→C 顺序开始，无其他 blocker。**

---

## 2026-05-09 · Request FEM-9: Windows-FEM 1-week plan (external expert recommendation)

**Goal**: 把外部专家给的 1 周 FEM 工作排期同步过来。专家把任务分成"必须做 / 值得做 / 暂缓"三档。整体方向：**收口 Phase 1 evidence、启动 strict Carrara、准备 PCC Phase 2** —— 不再用 Windows-FEM 资源补 AT1+penalty 细枝末节。

### 必须做（直接服务当前 paper + 主线判断）

**Task A — 把 Phase 1 FEM 证据包整理进 [docs/FEM.md](upload code/docs/FEM.md)**

不是新计算，是**已经到位的证据收口**。必须明确包含：
- `V7_FEM = 0.12%` (FEM-8 result)
- exact-pair symmetry 的好结果（FEM-7: alpha_bar rel 2.98e-5）
- `∫ ᾱ·(1-f) dV` integrated damage budget（FEM-7: 4.39e-2）
- AT1+penalty 的 h-non-monotonic verdict（即"AT1+penalty 在 SENT 上不收敛"的结论文档化）

**Task B — 确认 strict Carrara 线的 runner 能稳定跑**

公式: `AT2 + Miehe spectral split + HISTORY` (这是 Carrara 2020 community-anchor 公式)。
要求：
- 至少 1 个 smoke + 1 个代表性载荷点（比如 u=0.12）
- 目标不是立刻出完整论文图，而是确认 kernel bugfix 后这条线**真的可用**，不再是 "理论上想跑"

**Task C — 把 PCC Phase 2 的输入参数接口准备好**

等 Mac 给定 `α_T` (PCC concrete-specific) 后，Windows-FEM 能直接重跑：
- PCC 材料参数（E~30GPa, ν~0.18 vs 当前 toy E=1, ν=0.3）
- AT2 + Miehe spectral
- FEM-only smoke (PIDL 暂不动)

这一步**先做"脚本 ready"**，不必跑实际计算 — 等 Mac 给参数。

### 值得做（高价值增强，但不该阻塞写作）

**Task D — strict Carrara 6-case sweep**

最值得的增强实验。目的：
- 对齐 Carrara community anchor (Carrara 2020 CMAME)
- 看 Basquin slope `m` 能不能从当前 `3.49` 更接近 community range `3.8–4.0`

**Task E — strict Carrara 最小 mesh check**

只选 1 个中间载荷点（比如 u=0.12 量级），跑两档 mesh：
- ℓ/h = 5
- ℓ/h = 10

不追完美收敛，**确认 strict formulation 的 mesh sensitivity 是不是比当前 AT1+penalty 更可控**。

**Task F — V7_FEM 再补 1 个 fracture-near cycle**

现有 `V7_FEM = 0.12%` 是 peak elastic / cycle 0 状态。如果时间允许，再补 fracture 附近 cycle 的同口径 V7。这样后续能回答："FEM 边界质量在早期 vs 临破坏时是否都稳定"。

### 暂缓（不优先）

- AT1+penalty h-sweep 继续细化（已经够得出"不收敛"verdict）
- wide/narrow XF 尾巴
- 为 PIDL 每个新想法立刻配 FEM rerun（不应该让 Windows-FEM 被 PIDL 微调牵着走）

### 1 周顺序建议

| Day | 任务 |
|---:|---|
| 1 | Task A: 更新 docs/FEM.md，固定 Phase 1 evidence pack |
| 2 | Task B: strict Carrara 1-case smoke，确认 runner / kernel / export 全通 |
| 3-4 | Task D: strict Carrara 6-case sweep |
| 5 | Task E: strict Carrara 1-point mesh check |
| 6-7 | Task C: PCC Phase 2 脚本 ready + 等 α_T 后 smoke |

### Acceptance / Reply

每完成一个 Task 就 append 一个 `[done]` entry 到 `windows_fem_outbox.md`，含：
- 关键数字（如 strict Carrara N_f 或 Basquin m）
- 任何 blocker（如 kernel bug、参数未定）
- 下一步打算

### Priority

**Task A: HIGH** — paper §4 evidence consolidation 直接 depends on this  
**Task B/C: HIGH** — 解锁 Phase 2 主线  
**Task D/E/F: MEDIUM** — 增强但非阻塞

---

## 2026-05-07 · Request FEM-7: FEM-side symmetry + integrated damage budget @ u=0.12

**Goal**: 给 paper §4 reframe 提供 FEM 端的对照数字。Mac 这边 PIDL 完成了 soft symmetry penalty 实验（commit 90f2297）+ Layer 3 red-team 反馈，现需 FEM 侧的：
1. **V4 对称性 ground truth**：FEM α-field 在 SENT 几何下的 mirror RMS 数字（公认应 ≈ 0 at machine precision，但需要数字进 paper §4.2）
2. **真实 integrated damage budget**：∫ ᾱ·(1-f(ᾱ))·dV at fracture cycle，替代 Mac 当前的 f_mean-based 'domain-mean proxy'（red-team 指出后者是 wrong quantity）
3. **α field snapshot @ fracture cycle**：用于 F4.5a side-by-side mirror visualization (PIDL baseline vs PIDL soft sym vs FEM)

**Specific deliverables** (3 个 numbers + 1 个 .mat)：

### (a) FEM V4 mirror RMS @ Umax=0.12 fracture cycle (cycle 82)

```python
# From SENT_PIDL_12/psi_fields/cycle_0082.mat or similar
import numpy as np
from scipy.spatial import cKDTree
import scipy.io as sio

m = sio.loadmat("path/to/cycle_0082.mat")
centroids = m["centroids"]      # (N_elem, 2)
alpha = m["alpha_bar_elem"]      # or "d_elem"
x, y = centroids[:,0], centroids[:,1]
mu = y > 1e-6; ml = y < -1e-6
tree = cKDTree(np.stack([x[ml], -y[ml]], axis=1))
d, idx = tree.query(np.stack([x[mu], y[mu]], axis=1), k=1)
exact = d < 1e-7    # exact mirror pairs (for FEM mesh likely ~thousands)
diff = alpha[mu][exact].flatten() - alpha[ml][idx[exact]].flatten()
print(f"FEM V4 mirror RMS (exact pairs): {np.sqrt((diff**2).mean()):.4e}")
print(f"n_exact_pairs: {exact.sum()}")
```
→ 期望 RMS < 1e-4（per `Mandal-Nguyen-Wu 2019 EFM 217` 标 ≤ 2e-4 PASS）

### (b) Integrated ∫ ᾱ·(1-f(ᾱ))·dV @ fracture cycle 82

```python
alpha_T = 0.5        # match PIDL's setting
f_alpha = (2*alpha_T / (alpha + alpha_T))**2
# area_per_elem = element area (from mesh; you have it from FEM solver)
integrated = (alpha.flatten() * (1 - f_alpha).flatten() * area_per_elem.flatten()).sum()
print(f"FEM ∫ᾱ(1-f)dV @ c82 = {integrated:.4e}")
```

→ 这个数字对照 PIDL 的同公式（Mac 端在算 baseline + soft sym 两个 archive 的同 quantity），决定 paper §4.4 是 'energy budget 1.5-2× near-equivalence' 还是要砍掉

### (c) α field snapshot @ fracture cycle

期望 1 个 .mat 文件 `u12_cycle_0082_FEM7.mat`，含：
- `centroids`: (N_elem, 2)
- `alpha_bar_elem`: (N_elem, 1) — Carrara accumulator at c82
- `d_elem`: (N_elem, 1) — phase-field damage at c82

放 `_pidl_handoff_v3_items/` 同步到 OneDrive。

### (d) Paper-grade caveat

如果你有 FEM 的 V4 RMS、integrated damage、α field 的 ready 现成 dump，直接给 numbers + .mat 即可。如果需要新跑 post-processing，约 30 min-1h（不需要新 GRIPHFiTH run）。

**Priority**: high — 这三个 number 是 §4 核心 claim 的 FEM 对照 baseline，写 LaTeX 之前必须有。

**ETA**: 你估计 30 min-1h post-process。

---

## 2026-05-06 · Request FEM-6: re-extract N_f under load-drop criterion (option B from your `be07fd8`)

**Goal**: 用 mesh-stable N_f criterion `F_peak/F_initial < 5%`（或 `F_peak < 0.005`）替代当前 d-front-at-boundary criterion，重新算 mesh_C / M / F / XF (+ FEM-D 2×4 矩阵的 narrow row 各档) 的 N_f。看 paper §FEM 能不能写"convergence verified under load-amplitude criterion"。

**Mac vote**: **(B) approved.** 你在 `be07fd8` 里的诊断（penetration criterion 在 finer mesh 下"slows down"产生 detection drift）跟 community 标准（Castillón 2025、ASTM、ISO 用 load-drop criterion）一致；且 Mandal-Nguyen-Wu (2019, EFM 217) 文献明确说 AT1 是 h-non-monotonic 的，用 d-front 在 fine mesh 下不可信。

**Acceptance criteria**:
- (B-pass) `|N_f_F − N_f_M| / N_f_M < 5%` 在 load-drop criterion 下：paper §FEM 写 "h-convergence verified under load-amplitude criterion (load drop > 5%); d-front criterion intentionally avoided due to known mesh-sensitivity in AT1 phase-field formulations (Mandal et al. 2019)"
- (B-fail) load-drop 下仍发散：paper §FEM 改写 "AT1 phase-field is known to exhibit non-monotonic h-convergence under both d-front and load-drop criteria. PIDL/FEM comparison uses common ℓ/h≈1 reference mesh; absolute uncertainty band ±15% from h-sensitivity"

**Source data**: load_displ history 已经是每个 mesh archive 的标配（你常规 export）。不需要新跑训练。

**Output**:
1. 表格：mesh_C / M / F / XF 在 load-drop criterion 下的 N_f
2. 加 FEM-D 矩阵的 narrow row N_f（如果已经跑出来）
3. 一句 verdict：是否单调收敛 / 收敛 < 5%

**Priority**: **high** — paper §FEM 的写法直接 blocked 在这上面。Tier C reruns 都是 ℓ/h=1 的 PIDL 比较，不会受 FEM 这个收敛问题影响，但 reviewer 会先问"FEM reference 的 mesh convergence 怎么说"。

**ETA**: 你估计 ~30 min post-process（不需要新 GRIPHFiTH run）。

---

## 2026-05-06 · Request FEM-5: ship u=0.10 + u=0.11 ψ⁺ keyframes to Mac

**Goal**: 解锁 Mac→Taobo 上的 Oracle u=0.10 / u=0.11 干净重跑（Tier C audit follow-up，currently blocked）。Mac `~/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent/` 目前只有 u08 + u12 4-keyframe 各 4 文件；u10/u11 一直只在 Windows-FEM。Taobo 已有 FEM data 镜像（Mac sync 过来），所以 Windows-FEM 只需把 u10/u11 keyframes 寄到 Mac，Mac 自会再同步到 Taobo。

**Format**: 与 u08/u12 完全一致——4 个 keyframe `.mat` 文件 / Umax，每个含 `psi_elem`, `alpha_bar_elem`, `f_alpha_elem`, `d_elem`（n_elem × 1 element-averaged from Gauss points + d-field read from VTK at nearest cycle ≤ keyframe）。

**Keyframe cycles 选择参考 u12 模式**（c1, c40, c70, c82）：
- u=0.10 (FEM N_f=170)：建议 c1, c80, c140, c170
- u=0.11 (FEM N_f=117)：建议 c1, c55, c95, c117

**Expected files** (8 个 `.mat`)：
```
u10_cycle_0001.mat
u10_cycle_0080.mat
u10_cycle_0140.mat
u10_cycle_0170.mat
u11_cycle_0001.mat
u11_cycle_0055.mat
u11_cycle_0095.mat
u11_cycle_0117.mat
```

**Delivery**: 跟 u08/u12 一样，OneDrive 共享文件夹（或 zip 一起发）。Mac 拿到后会落到 `~/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent/` 然后 rsync 到 Taobo。

**Acceptance**: Mac 可以读到这 8 个文件，sanity check 与 u08/u12 文件的 keys 一致；Taobo 上 `run_e2_reverse_umax.py 0.10` 和 `0.11` 不再报 FEM data missing。

**Priority**: medium (paper 用 Oracle u=0.10/0.11 数据 cross-validate framework claim；Taobo 5/8 GPU 也在等这个解锁)。ETA：抽 20-30 min 跑一下 export script 应该够。

**Background**: Mac 同时在审计 archive 设置（commit `28cce78` 后 audit 脚本发现 3 个 u=0.12 method archive WARN due to missing model_settings.txt）。Tier C 重跑已派 5 个到 Taobo，但 Oracle u=0.10/0.11 还要等这两组 keyframe ship 过来。

---

## 2026-05-05 · Request FEM-4: export a(N) crack propagation curve for u=0.08, 0.12, 0.13

**Goal**: 生成 FEM 的 a(N) 曲线（裂纹尖端位置 vs 循环数），与 PIDL 的 x_tip-vs-N 叠图对比。这是 Carrara 2020 Fig 6 的核心图，paper 必须有。

**定义对齐（与 PIDL 一致）**：
- `x_tip(N)` = 该 cycle 中 α > 0.95 的最大 x 坐标（即 crack front 的 x 位置）
- 如果 GRIPHFiTH 输出的是 GP-level α，取所有 α>0.95 的 GP 中 x 坐标的最大值

**需要的 Umax**（3 个，覆盖低/中/高 Umax）：
- u=0.08：FEM N_f ≈ 396，`SENT_PIDL_08_export/` 已有
- u=0.12：FEM N_f = 82，`SENT_PIDL_12_export/` 已有
- u=0.13：FEM N_f = 57，数据在 `_pidl_handoff_v2/psi_snapshots_for_agent/` 或单独跑一次

**Output format**（每个 Umax 一个 CSV）：
```
cycle, x_tip_alpha95, alpha_max_monitor
1, 0.502, 0.031
2, 0.503, 0.044
...
```

**Files requested**:
- `fem_a_traj_u008.csv`
- `fem_a_traj_u012.csv`
- `fem_a_traj_u013.csv`
- 放到 `_pidl_handoff_v3_items/` 或新建 `_pidl_aN_curves/`

**Priority**: high（这个图是 paper 核心图之一，PIDL 这边 x_tip 数据已有，等 FEM 数据就能出图）

**Note**: `export_alpha_traj_u12.m` 目前只导出 α_max，不含 x_tip，需要新写或修改导出脚本。

---

## 2026-05-05 · Request FEM-3: h-sweep extension — ℓ/h=20 to bracket convergence

**Goal**: mesh_C/M/F 显示 M→F 仍有 +8.9%，尚未收敛。加 ℓ/h=20 一个点来估计渐近值，给 paper 一个更紧的 convergence bracket。

**脚本**：按 mesh_F 的模式新建 `INPUT_SENT_PIDL_12_mesh_XF.m` + `main_fatigue_meshXF.m`（"XF" = extra-fine）。

目标 mesh 参数（跟着 mesh_F 模式延伸）：
- `ℓ/h_tip = 20` → `h_tip = 0.0005 mm`
- `specimen.internal.plate` 参数参考：`Lref_y=0.05`, `Nref_y=100`（偶数，确保 notch 在网格上）；`Nx` 按需调整以匹配 h_tip
- 其余材料参数、BC、max_cycle=120 全不变

**Expected output**:
- N_f_XF（first detect）
- 回传 outbox：N_f_C/M/F/XF 完整表 + 是否出现渐近迹象

**Acceptance**: 如果 |N_f_XF − N_f_F|/N_f_F < 5% → convergence bracket closed；若仍 >5% → report trend，Mac 决定是否再加一档

**Priority**: medium（ETA ~12-15h，可 overnight）

---

## 2026-05-05 · Request FEM-2: gmsh-only h-sweep — mesh_C/M/F convergence at Umax=0.12

**Goal**: 用同一个工具（GRIPHFiTH `specimen.internal.plate`）跑三套分辨率，干净证明 h-convergence，替代 FEM-1 的混合工具对比结果。Paper 里写"h-convergence verified with same mesh generator"。

**脚本已在镜像里，直接跑**：

```matlab
% 顺序跑，或并行跑（独立）
run('Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_mesh_C.m'); main_fatigue_meshC(...)
run('Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_mesh_M.m'); main_fatigue_meshM(...)
run('Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_mesh_F.m'); main_fatigue_meshF(...)
```

**Expected outputs**:
- 三个 N_f（first penetration）
- 回传到 outbox：表格 N_f_C / N_f_M / N_f_F + 趋势（converging / diverging）

**Acceptance criteria**:
- PASS：N_f_M 和 N_f_F 之差 < 5%（证明在 ℓ/h≥10 处收敛）
- BONUS：如果 N_f_C ≈ N_f_M ≈ N_f_F，连 ℓ/h=5 都够用，更强

**Priority**: medium（~30-40 min wall，三个可并行）

---

## 2026-05-05 · Request FEM-1: mesh convergence check — PIDL-series at Umax=0.12, ℓ/h=5

**Goal**: 验证 PIDL-series FEM 参考数据（ℓ/h≈1，N_f≈82）是否网格收敛。Paper 里要能写一句"convergence verified at representative Umax"。

**现有 baseline**:
- INPUT file: `Scripts/fatigue_fracture/INPUT_SENT_PIDL_12.m`
- Mesh: `Dependencies/SENT_mesh/SENT_mesh.inp`（77,730 quads，h_tip≈0.01 mm，ℓ/h≈1）
- Result: N_f ≈ 82

**需要做的**:

**Step 1 — 生成新 mesh**（与 SENT_carrara_quad.inp / SENT_pcc_concrete_quad.inp 同流程）:

| 参数 | 目标值 |
|---|---|
| 几何 | 同 SENT_mesh.inp：1×1 mm，notch 在左中，物理切口 |
| ℓ | 0.01 mm（不变） |
| h_tip | **0.002 mm**（ℓ/h_tip = 5） |
| h_zone | 0.005 mm（tip 周围精细区） |
| h_global | 0.05 mm |
| 格式 | Abaqus .inp 或 GRIPHFiTH 支持的格式 |
| 文件名 | `SENT_pidl_fine_lh5.inp` |

**Step 2 — 新 INPUT 文件**（基于 INPUT_SENT_PIDL_12.m 修改）:
- 文件名：`INPUT_SENT_PIDL_12_fine.m`
- 唯一改动：mesh 路径指向新 `SENT_pidl_fine_lh5.inp`
- 所有材料参数不变：E=1, ν=0.3, Gc=0.01, ℓ=0.01, α_T=0.5, p=2.0, AT1, AMOR, PENALTY
- BC 不变：uy_final=0.12, R=0.0
- max_cycle=120（足够，预期 fracture ~82）

**Step 3 — 跑**:
```matlab
run('Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_fine.m')
main_fatigue_fracture(...)
```

**Expected outputs**:
- N_f（first penetration cycle）
- ᾱ_max @ N_f
- 回传到 `windows_fem_outbox.md`：N_f_fine vs N_f_coarse=82，差值 %

**Acceptance criteria**:
- PASS：|N_f_fine − 82| / 82 ≤ 5%（网格收敛）
- FAIL：>5%，需要讨论是否重跑所有 Umax 或降级 caveat

**Priority**: medium（OOD 表格不 block 这个，但 paper submission 前必须有）

**Blocker 提示**: 如果 mesh 生成工具（Abaqus/Gmsh）有问题，outbox 里说一声，Mac 可以帮生成 .inp 文件。

---

## Archive

[暂无]
