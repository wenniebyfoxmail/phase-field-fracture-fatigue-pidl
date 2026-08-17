# Windows-FEM Request 28 — first-detect causal damage and peak-displacement export

Date: 2026-08-17

From: Mac-PIDL

To: Windows-FEM / GRIPHFiTH

Priority: high, minimal state export

Evidence class: `state-semantics` / `tooling-only`; diagnostic only

## 2026-08-18 authorization update

The bounded U0.13 c0-to-c1 capture smoke passed and Mac verified the shared
OneDrive payload. The user then explicitly authorized proceeding. Windows-FEM
may now run the minimum P0+P1 replay already defined by this request, from each
canonical `c0/state0` initialization path through c122/s4, c83/s4 and c59/s4,
respectively. Capture c121/s5, c82/s5 and c58/s5 in path. P1 adds payload only,
not replay cycles. Keep the same-state peak and cross-cycle transition-input
semantics separate. All original acceptance criteria and no-substitution rules
remain binding.

The same authorized replay must additionally capture the early-origin s4 peak
states passed in trajectory: U0.11 c10/c15/c20/c40; U0.12
c13/c18/c20/c23/c40; U0.13 c9/c14/c19/c20/c40. At minimum export same-state
`u_node` and `d_node` with timing/mesh identity; retain the full tested capture
payload when non-perturbing. These extra captures add no replay cycles and are
required for the displacement-POD/physical-coordinate early first-detect gate.

## Why this is needed

The Taobo Phase-A diagnostic established that event-time mechanics must be
paired causally:

```text
damage(first_detect - 1, unloaded) -> displacement/energy(first_detect, peak)
```

Using post-`first_detect` unloaded damage against the same cycle's peak field
gave a numerically converged but physically mistimed reconstruction. The
causal pairing recovered correlation about 0.9985 for U0.11 and U0.13, but a
fair three-case enriched-vs-plain test is still blocked because:

1. U0.12 c82 native nodal damage was not retained; element-to-node projection
   was inadequate.
2. Existing `fields_<cycle>_005.vtk` files are substep-5 unloaded states, so
   their nodal displacement is zero and cannot be used as synthetic DIC.
3. Native substep-4 peak displacement is missing at the three locked
   first-detect cycles.

This request only fills those state-export gaps. It does not change the FEM
model and does not request PIDL training.

## Locked event table

| Umax | case directory | causal damage source | peak displacement target | confirmation excluded |
|---:|---|---|---|---|
| 0.11 | `u011/SENS_hard5_u011_eta0_canonical_v1/` | c121, substep 5, unloaded post-commit | c122, substep 4, load factor 1.00 | c125 |
| 0.12 | `u012/SENS_hard5_u012_eta0_formal_pidl_native_q4_v1/` | **c82, substep 5, unloaded post-commit** | c83, substep 4, load factor 1.00 | c86 |
| 0.13 | `u013/SENS_hard5_u013_eta0_canonical_v1/` | c58, substep 5, unloaded post-commit | c59, substep 4, load factor 1.00 | c62 |

The first-detect cycles are fixed at `122/83/59`. Do not replace them with
confirmation cycles `125/86/62` and do not redefine failure from the new
exports.

## Source archive

Use only the existing matched family:

```text
OneDrive/.../griphfith/
  Hard5_eta0_5step_Umax_011_012_013_20260729/
```

The retained load factors are:

```text
substep 1  0.25
substep 2  0.50
substep 3  0.75
substep 4  1.00  <- peak state requested
substep 5  0.00  <- unloaded prior-cycle damage requested
```

Preserve the exact completed-case physics, mesh and ordering. Do not alter
AMOR/AT1, eta, fatigue law, tolerances, boundary conditions, Umax, load cadence
or event detector.

## Execution order

1. Inspect existing checkpoints/native staging/state files first.
2. If the requested state can be exported from an existing checkpoint, export
   it without rerunning the trajectory.
3. If a state was never retained, replay only from the nearest verified
   checkpoint through the requested cycle in a fresh output directory.
4. Never overwrite the canonical case directories.
5. If exact recovery is impossible, stop and report which state/checkpoint is
   missing. Do not fill c82 nodal damage by interpolating `d_elem`.

## Required arrays

Create one common mesh file:

```text
mesh_geometry.mat or mesh_geometry.npz
  node_coords             [Nnode, 2 or 3]
  connectivity_q4         [Nelem, 4]
  node_ids                [Nnode] if file ordering is not canonical
  element_ids             [Nelem] if file ordering is not canonical
```

For each Umax export the two state classes:

```text
prior_unloaded_damage
  d_node                  [Nnode]
  physical_cycle
  substep = 5
  load_factor = 0.0
  state_label = cNNN_unloaded_post_commit

event_peak_displacement
  u_node                  [Nnode, 2 or 3]
  physical_cycle
  substep = 4
  load_factor = 1.0
  imposed_Umax
  state_label = cNNN_peak_post_commit
```

If it is essentially free to include them, also export `d_node` at the peak
state, top/bottom boundary node IDs and reaction at substep 4. These are audit
fields, not additional scientific targets.

Do not substitute:

- unloaded `u_node` from substep 5;
- element-centred damage for c82 nodal damage;
- a monotonic elastic run with no fatigue history;
- confirmation-cycle fields;
- remeshed or reordered arrays without an explicit index map.

## Preferred package

```text
hard5_first_detect_peak_state_export_20260817/
  README.md
  state_index.csv
  mesh_geometry.mat
  u011/
    c121_unloaded_post_commit_damage.mat
    c122_peak_post_commit_displacement.mat
  u012/
    c082_unloaded_post_commit_damage.mat
    c083_peak_post_commit_displacement.mat
  u013/
    c058_unloaded_post_commit_damage.mat
    c059_peak_post_commit_displacement.mat
  provenance/
    source_paths.txt
    source_commit.txt
    source_file_hashes.txt
    export_or_replay_commands.txt
    runtime_versions.txt
    replay_logs/                 # only if replay was necessary
  SHA256SUMS
```

`state_index.csv` columns:

```text
umax,physical_cycle,substep,load_factor,state_label,array_file,
node_count,element_count,mesh_sha256,source_kind,source_checkpoint,
source_case,export_timestamp
```

Use `source_kind=direct_export` or `checkpoint_replay`; do not leave it
implicit.

## Acceptance checks before handoff

1. All three cases use the same coordinate/connectivity hashes, expected
   `Nnode=86756` and `Nelem=86408`.
2. Every requested array is finite and its first dimension matches the mesh.
3. `d_node` lies in `[0,1]`, up to explicitly reported roundoff only.
4. Each peak row is substep 4 with `load_factor=1.0`.
5. On top-edge nodes, peak `u_y` matches the declared Umax within the solver's
   export precision; report max and mean explicitly.
6. Peak displacement is nonzero and the corresponding unloaded displacement
   is not accidentally shipped in its place.
7. The causal source cycles are exactly c121/c82/c58 and event targets exactly
   c122/c83/c59.
8. No c125/c86/c62 confirmation field enters the requested package.
9. `SHA256SUMS` covers every payload, state index, README and provenance file.
10. If replay is used, report the nearest checkpoint, replay start/end cycles,
    command, source commit/dirty state, runtime version and a non-perturbation
    comparison against at least one already retained anchor.

## Experiment gate

- **Mechanism question**: does an exact FEM peak-displacement observation
  contain enough near-tip information for a crack-enriched representation to
  outperform a plain displacement-gradient representation at first detect?
- **Claim changed if successful later on Mac**: XDEM-style enrichment remains
  a viable displacement-to-energy observation bridge within this matched
  three-Umax family.
- **Claim changed if unsuccessful later on Mac**: stop the enrichment route;
  do not escalate to KAN/RBF/LoRA or PIDL retraining.
- **Cheaper diagnostic first**: completed. Archive audit and fixed-damage
  micro-solve found the exact missing states; no production sweep is needed.
- **Minimal output asset**: the six indexed state exports, common mesh,
  provenance and hashes.
- **Registry destination**: reply under Request 28 in
  `docs/handovers/windows_fem_outbox.md`. Mac will validate the package and
  update the diagnostic decision; Windows-FEM should not make a PIDL or paper
  claim from the export alone.
- **Decision**: export/replay only the missing states; no broader FEM sweep.

## Outbox response requested

Please report one of:

```text
COMPLETE
  package path
  direct export vs checkpoint replay per state
  state_index and SHA256 verification result
  mesh/node/cell counts and hashes
  top-edge peak-u audit for all Umax

BLOCKED
  exact missing checkpoint/state
  checks already attempted
  whether a minimal replay from an earlier checkpoint is possible
  estimated replay scope, without launching it unless it stays within this request
```
