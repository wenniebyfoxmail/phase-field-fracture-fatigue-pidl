# G0 asset and identity audit

Date: 2026-10-01  
Experiment: `S02-E002`  
Scope: read-only audit of existing FEM/PF archives and exporters for camera-like
synthetic fracture sequences  
Verdict: **G0 FAIL — do not render FEM data yet**

## Decision

The repository contains enough mechanics data to avoid a new FEM run for an
initial integration test, but no existing package satisfies the complete
`S02-E002` input contract.

The strongest directly available asset is the Request 28 package. It contains
three exact first-detect transition pairs (`u011`, `u012`, `u013`) with common
Q4 coordinates/connectivity, nodal displacement, nodal and element damage,
cycle/substep/load labels, and audited event semantics. It can support a
bounded **event-pair renderer integration test after the missing contracts are
frozen**. It is not a time-series tracking or forecast dataset.

G0 fails because:

1. no audited mechanics package records `lineage_id` or the shared-history
   grouping required by `S02-E002`;
2. no package contains explicit crack centreline/faces/visible tip, and no
   `S02-E002` rule for converting diffuse damage to visible geometry has been
   frozen;
3. the full Hard5 cycle histories do not contain a simultaneous peak nodal
   displacement sequence: cycle MAT files contain peak element fields, while
   retained VTK displacement is normally the unloaded state;
4. none of the mechanics packages records a camera pixel calibration or image
   visibility state; and
5. all three complete Hard5 trajectories reach the simulator event. There is
   no explicitly right-censored trajectory for a forecast benchmark.

The G0 stop rule therefore applies: **do not create FEM-derived images or
labels until identity/lineage, units/calibration, state timing and the
damage-to-visible-geometry rule are frozen and independently checked.** G1 may
still use prescribed analytic fields because it does not consume FEM data.

## Inventory summary

| Asset | Directly available | Derivable only under a stated rule | Missing or blocked | Decision |
|---|---|---|---|---|
| Request 28 first-detect export | Three trajectory IDs; six exact states; common node coordinates and Q4 connectivity; `u_node`; `d_node`; `d_elem`; fatigue/history fields; cycle; substep; load factor; audited first-hit semantics | Peak reaction for native peak packets could be reduced from stored prescribed-boundary reactions using a frozen sign/sum rule | `lineage_id`; explicit crack geometry; visible-image truth; full pre-event sequence; right-censoring; pixel calibration; reaction scalar in `state_index.csv` | Best integration asset, but not G0-qualified |
| Raw GRIPHFiTH Hard5 family | Three named cases; 125/89/62 cycles; load/displacement/reaction at five substeps per cycle; regularised scalar crack length; 125/89/62 cycle-peak element-field MAT files; 46/42/33 unloaded VTK snapshots with nodal `u` and `d`; first-hit and confirmation cycles in the processed manifest | A scalar length curve is directly readable from `a_ell`; a geometry mask or centreline would require a new frozen rule | No `lineage_id`; no explicit crack path/faces; no complete peak `u_node` sequence; sparse VTK cadence; VTKs are normally substep-5 unloaded; no censor flags or pixel calibration | Useful source archive; not directly renderable as a causal camera sequence |
| Hard5 LOAO processed corpus | Three trajectory IDs; 276 cycle states; common mesh; cycle arrays; first-hit/confirmed cycles; normalized geometry | Active driver can be derived as declared in its builder | No displacement, reaction, crack geometry, `lineage_id`, censoring, or image calibration; manifest states teacher is not qualified | Hidden-state diagnostic only; reject as renderer input |
| Ferrite c1-c5 replay | One named U0.12 trajectory; state0 plus five peak/five unload checkpoints; nodal `x,y,damage,ux,uy`; cell fields; cycle/substep/load factor in convergence table; normalized parameter contract | A scalar reaction might be recoverable from logs/source but is not an indexed output; visible geometry would require a new rule | No `lineage_id`; no event/censor label; only five early cycles; no explicit crack geometry or pixel calibration | Possible code-path fixture only; not a forecast carrier |
| Gate-B synthetic observation package | Two cases with mesh, displacement vectors and Boolean damage masks | It could be converted to images only by introducing a new renderer | Displacements are offline reconstructed rather than native; the package was rejected for state mismatch and unrealistic independent noise/label flips; no images, lineages or valid visibility labels | Negative control only; must not be treated as qualified camera truth |

## Field-by-field status

### Identity and scientific replicate

- Direct: `hard5_u011`, `hard5_u012`, and `hard5_u013` are stable
  `trajectory_id` values in the LOAO manifest and files.
- Missing: no candidate contains `lineage_id`.
- Ambiguity: the three runs share a specimen family, mesh and recovered initial
  state but vary `Umax`. The current evidence does not state whether they must
  be one shared-history group or three independent lineages. This must not be
  guessed.
- Count permitted by current evidence: three named mechanics trajectories;
  **zero S02-E002-qualified independent lineages**.

### Surface or nodal displacement

- Direct: Request 28 stores `u_node` with shape `2 x 86,756` in every one of
  its six states. The three event-peak arrays are non-zero and pass the native
  peak equality audit.
- Direct but unsuitable for peak imaging: raw `fields_<cycle>_005.vtk` files
  store point vector `u`; their suffix and audit identify them as substep-5
  unloaded states, normally with effectively zero displacement.
- Direct for a short fixture: Ferrite c1-c5 `nodes.csv` stores `ux,uy` for 11
  states.
- Missing: a complete, common-phase peak `u_node` sequence for every cycle of
  the three Hard5 trajectories.

### Crack geometry and visibility

- Direct mechanics proxy: nodal/element damage is available; the raw solver
  also records scalar regularised crack length `a_ell` once per cycle.
- Not direct geometry: `a_ell` is computed from the phase-field integral. It
  is not a centreline, pair of faces, surface intersection, or visible tip.
- Missing: explicit crack centreline/faces and image-visible crack truth.
- Required derivation contract: if damage is used, freeze the threshold(s),
  connectivity rule, component selection, centreline/tip convention,
  sub-pixel visibility rule and behaviour for closed cracks before opening any
  evaluation result. No such `S02-E002` rule exists yet.

### Loading coordinate and reactions

- Direct: every raw Hard5 `load_displ_*.out` has columns `step, u_x, F_x,
  u_y, F_y` and five rows per cycle. Counts are 625, 445 and 310 data rows for
  U0.11, U0.12 and U0.13 respectively.
- Direct: Request 28 states carry physical cycle, substep and load factor.
- Derivable: event-peak native packets contain prescribed-boundary reaction
  arrays and a sign convention, but reduction to one scalar must be frozen and
  checked before use.
- Missing: one joined state index that links every image candidate to its
  exact reaction row without relying on filename parsing.

### Units and calibration

- Directly documented: the Hard5 family is normalized/nondimensional (`E=1`,
  `Gc=ell=0.01`, `Umax` 0.11/0.12/0.13) on a `[-0.5,0.5]^2` specimen domain.
- This is sufficient to preserve normalized FEM coordinates if copied into a
  new manifest; it is not physical millimetre calibration.
- Missing: pixels per normalized length, crop, reference origin/axis, optical
  projection and any conversion to physical units. These belong to the frozen
  G1 camera contract and must be written explicitly.

### Event and censoring

- Direct: LOAO manifest records first-hit/confirmation cycles as
  `122/125`, `83/86`, and `59/62` for U0.11/U0.12/U0.13.
- Direct: Request 28 independently verifies the first-hit snapshots at cycles
  122, 83 and 59 and excludes the confirmation states.
- Count: three event-positive trajectories; zero explicitly right-censored
  trajectories.
- Missing: at-risk origin table, horizon, follow-up completeness and censor
  reason. Multiple frames or texture renderings cannot increase the event
  count.

## Reusable exporters and code

1. `SENS_tensile/prepare_fem_mechanism_operator_dataset.py` verifies common
   Q4 geometry and MAT/VTK element ordering, and builds cycle-wise hidden-state
   arrays. Its own header states that VTK mechanics fields are unloaded and it
   does not export displacement. Reuse only its ordering checks.
2. `SENS_tensile/export_freeze_select_ferrite_carrier.py` shows how to join
   `nodes.csv`, `cells.csv`, mesh identity and state labels into a trajectory
   table. It also adds semisynthetic corrections and lacks `lineage_id`, so it
   must not be reused as-is for image truth.
3. The Ferrite `export_hard5_checkpoint!` helper writes nodal coordinates,
   damage and displacement plus cell mechanics fields. It is a useful schema
   example, not a qualified S02-E002 exporter.
4. GRIPHFiTH's `post_iter_update.m` writes imposed displacement and reaction;
   `crack_regularized.m` writes an integral-based scalar crack measure. Neither
   writes explicit visible crack geometry.
5. No existing deterministic speckle/camera renderer satisfying the G1
   analytic invariants was found in this repository or the audited archive
   paths.

## Minimum repair needed before FEM rendering

1. Create a six-row development manifest for the Request 28 states with
   explicit `trajectory_id`, reviewed `lineage_id`, normalized coordinate
   convention, source-state timing and source hashes.
2. Freeze one mechanics-to-geometry rule on development states only. Store
   mechanics damage, derived geometry and later image visibility separately.
3. Freeze a normalized-length-to-pixel calibration and camera axes in G1.
4. Join each retained state to its exact load/reaction observation or mark the
   reaction unavailable; do not infer it from filenames.
5. Use the Request 28 pairs only as integration fixtures. A later G2/G3 corpus
   needs complete peak sequences and independently grouped lineages, including
   explicit right-censoring if forecasting is attempted.

## Exact evidence paths

- `docs/research/S02/S02-E002/experiment.md`
- `docs/pidl_experiment_inventory.md` (Hard5 anchor and multi-trajectory rows)
- `SENS_tensile/prepare_fem_mechanism_operator_dataset.py`
- `SENS_tensile/export_freeze_select_ferrite_carrier.py`
- `docs/handovers/windows_griphfith_request_28_first_detect_peak_state_export_20260817.md`
- `/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/griphfith/hard5_first_detect_state_semantics_export_20260817/state_index.csv`
- `/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/griphfith/hard5_first_detect_state_semantics_export_20260817/data/`
- `/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/griphfith/Hard5_eta0_5step_Umax_011_012_013_20260729/`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/request28_first_detect_state_semantics_export_20260817/analysis/decision.md`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/request28_first_detect_state_semantics_export_20260817/analysis/independent_audit.json`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/hard5_loao_gno_dataset_v1_20260826/RUN_MANIFEST.json`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/hard5_loao_gno_dataset_v1_20260826/trajectories/`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/azinpour_hard5_u012_c2_c5_temporal_gate_20260729/runs/c1_c5_v1/`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/road_current_state_estimator_v1_20260818/gate_b_synthetic_qualification/decision.md`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/GRIPHFiTH/Sources/+phase_field/+fem/+solver/+step/post_iter_update.m`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/GRIPHFiTH/Sources/+phase_field/+fem/+crack/crack_regularized.m`

## G0 verdict under protocol v0.1

- Unique named trajectories: **3**.
- S02-E002-qualified independent lineages: **0**.
- Complete cycle-state hidden-field records: **276** (`125 + 89 + 62`).
- Exact native first-detect transition/peak states with `u_node`: **6**.
- Event-positive trajectories: **3**.
- Explicitly right-censored trajectories: **0**.
- Fully qualified camera-renderable trajectories: **0**.
- **Decision: FAIL.** Continue with prescribed analytic G1 only; repair the
  manifest/geometry/calibration contract before any FEM-derived rendering.

## 2026-10-05 live Windows re-audit amendment

A read-only SSH audit of `citpc12-ssh` found a sealed package that was not
included in the original local-only conclusion:

```text
C:\q4runs\hard5_native_q4_existing_u011_u012_u013_20260827_v1
```

The root has `root_manifest.json` and `SHA256SUMS.txt`. All three case-level
`validation_receipt.json` files report `passed: true`, reference neutrality and
complete state coverage. The package contains one non-alias `s04` peak payload
per cycle with `post_history_commit` timing and native `u_node`, `d_node`,
history and energy fields:

| case | peak `s04` states | cycles | effective load factor |
|---|---:|---|---:|
| `hard5_u011_stage0b` | 125 | 1-125 | 0.999999 |
| `hard5_u012_stage0b` | 86 | 1-86 | 0.999999 |
| `hard5_u013_stage0b` | 62 | 1-62 | 0.999999 |

Therefore the earlier statement that no complete simultaneous peak
displacement sequence exists is superseded for these three trajectories. No
new FEM replay is required to obtain their peak displacement sequence.

G0 remains **FAIL for FEM-derived camera images**, but the remaining blockers
are narrower:

1. freeze and validate `lineage_id` and split-group semantics;
2. implement a declared damage-to-geometry adapter and keep it separate from
   image visibility;
3. freeze normalized-coordinate-to-pixel calibration and camera axes;
4. join reaction/load metadata into the S02-E002 manifest if those channels are
   used; and
5. add explicit censoring and more independent lineages before a forecast
   claim. Censoring is not required for a renderer integration fixture.

The 28.276 GB sealed package is evidence-bearing source data. Do not rerun or
overwrite it. Build any adapter output in a fresh attributable directory and
retain the sealed source paths and manifest identity.
