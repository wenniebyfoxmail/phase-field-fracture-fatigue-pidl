# Windows-FEM Request 30 — AT1-fatigue mesh-PINO Stage 0b substep packet

> **DEFERRED 2026-08-26 — DO NOT EXECUTE.** The owner moved the active branch
> to data-only FEM imitation. Preserve this request for a later physics-residual
> branch; it is not a current Windows-FEM task.

**Date:** 2026-08-24  
**From:** Mac-PIDL  
**To:** Windows-FEM / GRIPHFiTH  
**Priority:** minimal diagnostic export  
**Authorization:** prepare/export or exact replay only after the user explicitly
approves execution; this document itself does not launch a run

## Decision and boundary

Existing Umax=0.12 factorial archives are complete for cycle-level element-mean
fields but cannot support a producer-matched physics residual: they do not retain
complete within-cycle nodal states or committed Gauss-point history. Request 30
asks for only 39 converged transitions (plus six preceding committed states) to
test residual computability before considering a full corpus.

This is not FEM qualification, teacher-corpus approval, PINO/PIDL training,
physical validation, or permission to change the model. Do not run on CSD3 and
do not create a broader trajectory export.

## Locked source family

Use the completed archive:

```text
OneDrive/.../griphfith/Umax_012_all_versions_20260729/
  02_hard_5step_factorial/
  01_hard_8step_historical/
```

Both targets use Umax=0.12, R=0, hard initial recovery, eta=0, AMOR, AT1,
alpha_T=0.5, p=2, residual stiffness 1e-6, and the archive's exact mesh,
boundary conditions, tolerances, initialization and stopping logic. Preserve
the archived raw-step map and update ordering. Do not substitute folder 05 for
the locked hard-5 factorial case.

## Locked selected states

| case | cycles | complete retained substeps | transitions |
|---|---|---:|---:|
| `hard5` | c1, c60, c82 | 1..5 | 15 |
| `hard8` | c1, c60, c85 | 1..8 | 24 |

Load factors are exactly:

```text
hard5: 0.25, 0.50, 0.75, 1.00, 0.00
hard8: 0.25, 0.50, 0.75, 1.00, 0.75, 0.50, 0.25, 0.00
```

For every selected cycle, also export its committed state immediately before
substep 1. For c1 this is the initialized state0; for c60/c82/c85 it is the
exact post-commit final substep of c59/c81/c84. A cycle-peak summary is not an
acceptable preceding state.

## Producer timing and channel semantics

The current producer does this after staggered convergence:

```matlab
p_field_old = p_field;
[~, ~, ~, history_vars_old] = assembly_pf_fh(..., p_field, ...,
                                               strain_en_undgr, ...,
                                               history_vars_old);
```

Save each requested substep only after that history refresh. Save the
pre-substep committed state before `pre_iter_update` changes the displacement.
The four raw Gauss-point channels must remain in producer order:

1. `H`: max tensile-energy history;
2. `alpha_bar`: Carrara accumulated positive degraded-driver increment;
3. `q_prev`: committed degraded driver;
4. `f`: fatigue degradation.

The exact update checked on Mac is:

```text
d_gp       = Nxi * d_node(post)
q_post     = ((1-d_gp)^2 + res_stiff) * psi_plus_undamaged(post)
H_post     = max(H_pre, psi_plus_undamaged(post))
alpha_post = alpha_pre + max(q_post-q_pre, 0)
f_post     = min(1, [1-(alpha_post-alpha_T)/(alpha_post+alpha_T)]^p)
```

Do not export the L2-projected VTK channels as a substitute for raw
`history_vars_old` or `strain_en_undgr`.

## Required packet

Follow the locked machine-readable schema:

[`at1_fatigue_mesh_pino_stage0b_export_spec_v1.json`](../experiments/at1_fatigue_mesh_pino_stage0b_export_spec_v1.json)

Preferred layout:

```text
at1_fatigue_mesh_pino_stage0b_request30_v1/
  README.md
  REQUEST_MANIFEST.json
  state_index.csv
  static_mesh.mat
  states/
    hard5/c0001_s00.mat ... c0001_s05.mat
    hard5/c0060_s00.mat ... c0060_s05.mat
    hard5/c0082_s00.mat ... c0082_s05.mat
    hard8/c0001_s00.mat ... c0001_s08.mat
    hard8/c0060_s00.mat ... c0060_s08.mat
    hard8/c0085_s00.mat ... c0085_s08.mat
  provenance/
    source_commit.txt
    source_file_hashes.txt
    export_or_replay_commands.txt
    runtime_versions.txt
    replay_logs/
  SHA256SUMS
```

Use MATLAB v7-or-earlier MAT files, not `-v7.3`, so the locked SciPy validator
can read them directly. Split one state per MAT file to stay below format size
limits.

### `static_mesh.mat`

Required fields:

```text
node_coords              [86756,2]
connectivity_q4          [86408,4], MATLAB 1-based
element_material_id      [86408]
active_dof_u, active_dof_d
dirichlet_dof_u, dirichlet_dof_d
Nxi                      [4,4]
dNdxi                    [2,4,4]
gauss_weights            [4]
thickness
```

Also include all material constants required by the AMOR equilibrium and AT1
phase assemblies (`E, nu, Gc, ell, res_stiff, alpha_T, p`), stress-state code,
boundary node sets/masks, imposed-displacement increments, and sparse assembly
index maps. If an array already lives inside a MATLAB struct, export a flat
numeric copy as well; opaque class objects are not acceptable handoff data.

### Every state MAT

Required fields:

```text
u_node                    [86756,2]
d_node                    [86756]
history_gp                [86408,4,4]
strain_en_undgr_gp        [86408,4]
```

For `s00`, `strain_en_undgr_gp` is the driver's committed source state; use
zeros for true state0 only. Do not average over elements or Gauss points.

### `state_index.csv`

Required columns:

```text
case_id,physical_cycle,substep,load_factor,state_kind,state_file,
source_kind,source_checkpoint,converged,n_stagger,n_newton_u,n_newton_d,
equilibrium_residual_free_l2,phase_residual_active_l2
```

Use `state_kind=precycle_committed` for s00 and
`post_substep_committed` otherwise. `source_kind` must be one of
`direct_export`, `checkpoint_replay`, or `fresh_exact_replay`. Record the actual
Newton iteration counts and final producer residual norms; use zero iterations
only for s00. `phase_residual_active_l2` must be reassembled at the final
converged `p_field` using the substep's pre-commit `history_vars_old`. Do not
copy the scalar returned by `newton_raphson.m`: that scalar is evaluated before
its final field update. Likewise, record equilibrium residual on the final
post-stagger displacement/damage state. Preserve the pre-commit history in
memory until these residual audits and the post-commit state export are both
complete.

## Important phase-equation correction

The locked producer calls `at1_history_fatigue.f90`; `p_field_old` is passed
through the solver interface but is not used by that kernel. Therefore Request
30 validates the producer's active-DOF AT1 phase residual and reports damage
bounds/recovery separately. Do not label this output as a native variational-
inequality or projected-KKT solve. A later neural operator may impose a hard
non-recovery map, but that is an architecture choice, not producer truth.

## Recovery and replay rules

1. Audit whether exact requested states already exist outside the archive.
2. If exact states exist, export them without solving.
3. Otherwise replay each locked case from state0 or the nearest verified full
   checkpoint in a fresh directory. Never overwrite the completed archive.
4. If using a checkpoint, show that it precedes the requested state and includes
   `displ`, `p_field`, `p_field_old`, and raw `history_vars_old`.
5. Compare replayed cycle-level scalar outputs and at least one retained VTK
   anchor to the locked archive. Any unexplained drift stops the request.
6. Do not infer a c59/c81/c84 preceding state from c60/c82/c85 data.

## Windows pre-handoff acceptance

Before handoff, run the validator from the shared repo:

```text
python SENS_tensile/validate_at1_fatigue_pino_stage0b_packet.py \
  <packet-directory>
```

It must report:

```text
PASS_STAGE0B_PACKET_SCHEMA_AND_HISTORY_UPDATE
state_count = 45
transition_count = 39
```

The validator checks identity, exact state coverage, hashes, shapes, finite
values, load factors, damage bounds/non-recovery, and all four history-update
channels. A pass still does not complete Stage 0b: Mac must subsequently
recompute equilibrium and AT1 phase residuals and show real FEM states score
lower than controlled perturbations/shuffles.

## Experiment gate

- **Mechanism question:** are the three proposed PINO physics losses exactly
  computable and discriminative on producer states?
- **Claim if successful:** only that the selected packet supports a numerical
  transition-prior micro-test.
- **Claim if unsuccessful:** full PINO training remains blocked; no physics
  weight or architecture sweep may compensate for inconsistent state.
- **Cheaper diagnostic first:** Stage 0 archive audit completed and failed
  residual computability; this 39-transition packet is the smallest next test.
- **Minimal output:** 45 indexed states, one static mesh/physics file,
  provenance and hashes.
- **Registry destination:** Mac updates the canonical
  `docs/experiments/at1_fatigue_mesh_pino_track.md` and attempt ledger after
  validation. Windows replies under Request 30 in `windows_fem_outbox.md`.

## Requested outbox response

Reply with either:

```text
READY_FOR_USER_EXECUTION_APPROVAL
  exact replay/export plan and estimated runtime/storage
  source commit and dirty-state report
  nearest checkpoints found
  fresh output directory

COMPLETE  # only after separate user execution approval
  packet path and SHA256 result
  direct-export/checkpoint/fresh-replay map
  validator JSON output
  replay-anchor comparison

BLOCKED
  exact missing state or provenance item
  checks attempted
  smallest non-substitutable replay scope, not launched
```
