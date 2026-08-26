# Windows-FEM Request 31 — Hard5 mesh-PINO Stage 0b substep packet

**Date:** 2026-08-26

**From:** Mac-PIDL

**To:** Windows-FEM / GRIPHFiTH

**Status:** `PREPARE_ONLY__ACTUAL_REPLAY_REQUIRES_SEPARATE_APPROVAL`

**Scope:** Hard5 Umax=0.12 only

## Required first response — no replay yet

Perform a read-only source/checkpoint audit and reply with exactly one of:

```text
READY_FOR_USER_EXECUTION_APPROVAL
  source case path
  source commit and dirty status
  exact states already available
  nearest complete checkpoints
  direct-export/checkpoint-replay/fresh-replay plan
  estimated runtime and storage
  fresh output directory

BLOCKED
  missing source, checkpoint or provenance item
  checks performed
  smallest non-substitutable next action
```

Do not start replay/export until a separate execution approval is received.
Do not run on CSD3, train PINO, modify the archived run or broaden to Hard8/soft.

## Locked source and identity

Use only the completed Umax=0.12 archive case:

```text
OneDrive/.../griphfith/Umax_012_all_versions_20260729/
  02_hard_5step_factorial/
```

Lock the archived mesh, boundary conditions, tolerances, initialization,
stopping logic and update order. Expected identity includes R=0, hard initial
recovery, eta=0, AMOR, AT1, alpha_T=0.5, p=2 and residual stiffness 1e-6.
Do not substitute another similarly named Hard5 directory.

The authoritative schema is
[`../experiments/at1_fatigue_mesh_pino_stage0b_hard5_export_spec_v2.json`](../experiments/at1_fatigue_mesh_pino_stage0b_hard5_export_spec_v2.json).

## Exact state coverage

| case | cycles | states per cycle | total states | transitions |
|---|---|---:|---:|---:|
| `hard5_u012` | c1, c60, c82 | s00 plus s01-s05 | 18 | 15 |

The five load factors are exactly `0.25, 0.50, 0.75, 1.00, 0.00`.

- `s00` is the exact committed state immediately before substep 1.
- For c1, s00 is true initialized state0.
- For c60/c82, s00 is the exact post-commit state from c59/c81.
- `s01-s05` are saved after staggered convergence and after history refresh.
- A cycle-peak element mean, sampled VTK or inferred preceding state is not an
  acceptable substitute.

## Required producer timing

The producer commits history after convergence. Save each requested state only
after the equivalent of:

```matlab
p_field_old = p_field;
[~, ~, ~, history_vars_old] = assembly_pf_fh(..., p_field, ...,
                                               strain_en_undgr, ...,
                                               history_vars_old);
```

Preserve the pre-commit history long enough to reassemble the final phase
residual. Do not copy a Newton residual measured before its final field update.

The raw Gauss-point history channel order is exactly:

1. `H` — maximum tensile-energy history;
2. `alpha_bar` — accumulated positive degraded-driver increment;
3. `q_prev` — committed degraded driver;
4. `f` — fatigue degradation.

## Packet layout

```text
at1_fatigue_pino_stage0b_request31_hard5_u012_v2/
  README.md
  REQUEST_MANIFEST.json
  state_index.csv
  static_mesh.mat
  states/
    hard5_u012/c0001_s00.mat ... c0001_s05.mat
    hard5_u012/c0060_s00.mat ... c0060_s05.mat
    hard5_u012/c0082_s00.mat ... c0082_s05.mat
  provenance/
    source_commit.txt
    source_file_hashes.txt
    export_or_replay_commands.txt
    runtime_versions.txt
    replay_logs/
  SHA256SUMS
```

Use MATLAB v7-or-earlier MAT files, one state per file. Do not use `-v7.3`.

### `REQUEST_MANIFEST.json`

It must copy the spec values for `schema_version`, `request_id`, `scope`,
`state_timing` and `history_channel_order`, and declare:

```json
{
  "mesh_file": "static_mesh.mat",
  "state_index_file": "state_index.csv",
  "sha256sums_file": "SHA256SUMS"
}
```

### `static_mesh.mat`

Required flat numeric fields:

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

Also export the required flat finite scalar fields `E`, `nu`, `Gc`, `ell`,
`res_stiff`, `alpha_T`, `fatigue_p` and `stress_state_code`. Preserve any
additional boundary masks, imposed-displacement increments and sparse assembly
maps needed by the producer assembly.

### Every state MAT

```text
u_node                    [86756,2]
d_node                    [86756]
history_gp                [86408,4,4]
strain_en_undgr_gp        [86408,4]
```

For s00, `strain_en_undgr_gp` is the committed driver source state; zeros are
valid only for true state0. Never replace raw Gauss-point state with projected
VTK fields or element averages.

### `state_index.csv`

Required columns:

```text
case_id,physical_cycle,substep,load_factor,state_kind,state_file,
source_kind,source_checkpoint,converged,n_stagger,n_newton_u,n_newton_d,
equilibrium_residual_free_l2,phase_residual_active_l2
```

- s00 uses `state_kind=precycle_committed`.
- s01-s05 use `state_kind=post_substep_committed`.
- `source_kind` is `direct_export`, `checkpoint_replay` or
  `fresh_exact_replay`.
- Record final post-stagger free equilibrium residual and final active-DOF AT1
  phase residual. Do not label the producer as a projected-KKT/VI solver.

## Replay rules

1. Prefer exact existing committed states and direct export.
2. Otherwise use the nearest verified checkpoint that precedes the requested
   state and contains `displ`, `p_field`, `p_field_old` and raw
   `history_vars_old`.
3. Otherwise replay from state0 in a fresh directory.
4. Never overwrite the completed archive.
5. Compare replayed scalar histories and at least one retained VTK anchor to the
   archive. Any unexplained drift stops the request.
6. Never infer c59/c81 committed state from c60/c82 peak summaries.

## Windows pre-handoff validator

From the exact shared-repo commit containing Request 31, run:

```text
python SENS_tensile/validate_at1_fatigue_pino_stage0b_hard5_packet.py \
  <packet-directory>
```

Required output:

```text
PASS_REQUEST31_HARD5_STAGE0B_SCHEMA_AND_HISTORY
state_count = 18
transition_count = 15
```

This validates identity, exact coverage, hashes, shapes, finite values, load
factors, damage bounds/non-recovery and the four-channel history update. It does
not validate equilibrium or the AT1 phase residual independently.

## Completion response

After separate execution approval and successful export, reply:

```text
COMPLETE
  packet path and SHA256SUMS hash
  source commit and dirty status
  direct-export/checkpoint/fresh-replay map
  validator JSON output
  replay-anchor comparison
  runtime and final size
```

## Claim boundary

Request 31 is a tooling/state-semantics gate. Passing it does not qualify the
FEM teacher, repair the failed damage fixed-point gate, validate physics or
authorize PINO training. Mac must independently recompute equilibrium/phase
residuals and run perturbation/shuffle controls before any PINO micro-test.
