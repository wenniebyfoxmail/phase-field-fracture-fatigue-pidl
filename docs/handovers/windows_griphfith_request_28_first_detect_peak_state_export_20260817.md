# Windows-FEM Request 28 — first-detect same-state and transition-pair export

Date: 2026-08-17

From: Mac-PIDL

To: Windows-FEM / GRIPHFiTH

Priority: high, state-semantics correction and minimal-export planning

Evidence class: `state-semantics` / `tooling-only`; diagnostic only

Status: **scope corrected; audit existing assets and report the minimum replay plan before replaying**

## Corrected request decision

Request 28 needs two different data products, with different meanings. They
must never be merged or described as one converged FEM state.

1. **Primary P0 — same-state event-peak packet**
   - At each first-detect event, export `u`, `d`, and the declared energetic
     fields from the same physical `cycle/substep`, after that substep has
     converged and been committed.
   - This is the data required for the XDEM-inspired enriched-vs-plain
     displacement-to-energy observation diagnostic.
2. **Secondary P1 — cross-cycle transition pair**
   - Pair the previous cycle's committed unload state with the next cycle's
     committed event-peak state: `c(N-1)/s5 -> cN/s4`.
   - This is a valid ML input-target pair and a mechanics-transition
     diagnostic, but it is **not** a same-state FEM snapshot.

The Windows side should first audit what can be directly exported and then
report the minimum replay range for P0 alone and for P0+P1. Do not start a new
replay merely from the old wording of Request 28.

## Authoritative Hard-5 time semantics

The following semantics were checked against the original Hard-5 solver source
and supersede the earlier ambiguous wording:

- `c0/state0` is the zero-load recovered initial state after fatigue history
  reset. It is not the first loading cycle.
- The first actual computed loading cycle is `c1`.
- Every Hard-5 cycle has the retained order:

  ```text
  s1 = 0.25
  s2 = 0.50
  s3 = 0.75
  s4 = 1.00 peak
  s5 ~= 0.00 unload
  ```

- After every converged substep, the solver immediately commits
  `p_field_old` and `history_vars_old`.
- Damage is irreversible. Unloading reduces displacement and stress but does
  not restore earlier damage.
- `fields_<cycle>_005.vtk` is that cycle's committed s5 unload state.
- Therefore `c83/s5` cannot replace missing `c82/s5`: it has already passed
  through the entire c83 damage/fatigue evolution. This is a later-state
  substitution error, not a claim that c82 is influenced by a future state.
- No later VTK may be inverted, projected, or relabelled as an earlier missing
  nodal state.

## Locked event cycles

The `first_detect` events remain fixed:

| Umax | first-detect event | confirmation excluded |
|---:|---:|---:|
| 0.11 | c122 | c125 |
| 0.12 | c83 | c86 |
| 0.13 | c59 | c62 |

Do not replace first detect with the `+3` confirmation cycle and do not
redefine the event from the new exports.

## P0 required outputs — same-state event peaks

Every row below is one physical FEM state. All required fields in a row must
come from the same converged and committed substep.

| output ID | source cycle | source substep | load factor | state timing | semantic class | required fields |
|---|---:|---:|---:|---|---|---|
| `u011_c122_s4_same_state` | c122 | s4 | 1.00 | post-convergence, post-commit | `same-state` | `u_node`, `d_node`, `psi_raw_peak_elem`, mesh/index metadata |
| `u012_c083_s4_same_state` | c83 | s4 | 1.00 | post-convergence, post-commit | `same-state` | `u_node`, `d_node`, `psi_raw_peak_elem`, mesh/index metadata |
| `u013_c059_s4_same_state` | c59 | s4 | 1.00 | post-convergence, post-commit | `same-state` | `u_node`, `d_node`, `psi_raw_peak_elem`, mesh/index metadata |

Also export the following if they are available from the same capture without
changing solver semantics:

```text
alpha_bar_elem
f_alpha_elem
psi_active_peak_elem       # only if computed from the exact declared GP product
reaction_force
top_boundary_node_ids
bottom_boundary_node_ids
```

Do not combine cN/s4 displacement with cN/s5 damage and call it same-state.
The same-state primary packet requires both `u_node` and `d_node` at cN/s4.

## P1 required outputs — explicit transition pairs

Each pair has one source state and one target state. Preserve both rows in the
index; do not collapse them into a single `state_label`.

| pair ID | role | source cycle | source substep | load factor | state timing | semantic class | required fields |
|---|---|---:|---:|---:|---|---|---|
| `u011_c121s5_to_c122s4` | input | c121 | s5 | ~0.00 | post-convergence, post-commit | `transition-input` | `d_node`, committed fatigue/history fields, mesh/index metadata |
| `u011_c121s5_to_c122s4` | target | c122 | s4 | 1.00 | post-convergence, post-commit | `transition-target` | reference to the complete P0 c122/s4 packet |
| `u012_c082s5_to_c083s4` | input | c82 | s5 | ~0.00 | post-convergence, post-commit | `transition-input` | `d_node`, committed fatigue/history fields, mesh/index metadata |
| `u012_c082s5_to_c083s4` | target | c83 | s4 | 1.00 | post-convergence, post-commit | `transition-target` | reference to the complete P0 c83/s4 packet |
| `u013_c058s5_to_c059s4` | input | c58 | s5 | ~0.00 | post-convergence, post-commit | `transition-input` | `d_node`, committed fatigue/history fields, mesh/index metadata |
| `u013_c058s5_to_c059s4` | target | c59 | s4 | 1.00 | post-convergence, post-commit | `transition-target` | reference to the complete P0 c59/s4 packet |

For `committed fatigue/history fields`, export the native retained arrays and
their native names/shapes needed to identify `history_vars_old`; additionally
provide `alpha_bar_elem` and `f_alpha_elem` if those are the existing canonical
reductions. Do not fabricate a reduction that the original solver did not
store.

U0.12 c82/s5 complete nodal damage is currently missing. `c83/s5` cannot be
used to fill it, and c82 nodal damage must not be approximated from `d_elem`.
If exact P1 U0.12 data is required, it must be captured by an exact canonical
replay that reaches and commits c82/s5 before continuing to c83/s4.

## Source archive and solver identity

Use only the matched July Hard-5 family:

```text
OneDrive/.../griphfith/
  Hard5_eta0_5step_Umax_011_012_013_20260729/
```

Preserve the exact completed-case physics, initialization and ordering. Do not
alter AMOR/AT1, eta, fatigue law, tolerances, boundary conditions, Umax, load
cadence, commit order or event detector.

The replay origin is canonical `c0/state0` unless Windows can prove that a
retained checkpoint contains the complete committed solver state required to
continue exactly. A damage-only VTK is not a complete restart checkpoint.

## Existing capture code that may be reused

The following mechanisms may be reused after source/provenance inspection:

- original solver per-step VTK output;
- the s4 peak export logic used for `peak_load_c1.vtk`;
- `phase_field.audit.capture_peak_state`;
- toy-road substep capture/export mechanism.

Toy-road code may contribute capture mechanics only. Toy-road states, outputs,
manifests or numerical results are not July Hard-5 canonical data and must not
be copied into this package as physical payloads.

## Required common mesh and state index

Create one common mesh payload:

```text
mesh_geometry.mat or mesh_geometry.npz
  node_coords             [Nnode, 2 or 3]
  connectivity_q4         [Nelem, 4]
  node_ids                [Nnode] if ordering is not self-evident
  element_ids             [Nelem] if ordering is not self-evident
```

Expected mesh size is 86,756 nodes and 86,408 Q4 cells. Verify hashes rather
than relying only on counts.

`state_index.csv` must contain at least:

```text
output_id,pair_id,pair_role,semantic_class,umax,
source_cycle,source_substep,load_factor,state_timing,
array_file,required_fields_present,node_count,element_count,
mesh_sha256,source_kind,source_checkpoint,source_case,export_timestamp
```

Allowed semantic labels:

```text
same-state
transition-input
transition-target
```

Allowed `source_kind` labels:

```text
direct_existing_export
checkpoint_replay
canonical_state0_replay
```

Do not leave timing or source kind implicit.

## Preferred package

```text
hard5_first_detect_state_semantics_export_20260817/
  README.md
  state_index.csv
  mesh_geometry.mat
  same_state_peak/
    u011_c122_s4_same_state.mat
    u012_c083_s4_same_state.mat
    u013_c059_s4_same_state.mat
  transition_pair/
    u011_c121_s5_input.mat
    u012_c082_s5_input.mat
    u013_c058_s5_input.mat
    # targets reference the matching same_state_peak files
  provenance/
    source_paths.txt
    source_commit.txt
    source_file_hashes.txt
    capture_code_paths_and_hashes.txt
    export_or_replay_commands.txt
    runtime_versions.txt
    replay_plan.md
    replay_logs/                 # only after replay is separately authorized
  SHA256SUMS
```

## Audit and replay-planning sequence

1. Audit existing direct exports, complete restart checkpoints and capture
   code for all six state times.
2. Fill a provisional `state_index.csv` with `available`, `missing`, or
   `incomplete_restart_state` for each required output.
3. Propose the minimum exact replay range separately for:
   - P0 same-state peak packets only;
   - P0 plus all P1 transition inputs.
4. State whether each replay must begin from canonical c0/state0 or can begin
   from a verified complete checkpoint.
5. Do not launch replay until the resulting plan is posted in the Windows-FEM
   outbox and its scope is confirmed.
6. Never overwrite canonical case directories; every replay must use a fresh
   output root.

## Windows audit result — 2026-08-17

Status: `AUDIT_COMPLETE`; no replay started.

### P0 same-state peaks

| output | status | evidence |
|---|---|---|
| U0.11 c122/s4 | missing | only `fields_000122_005.vtk` exists; no s4 VTK or complete s4 checkpoint |
| U0.12 c83/s4 | missing | only `fields_000083_005.vtk` exists; no s4 VTK or complete s4 checkpoint |
| U0.13 c59/s4 | missing | only `fields_000059_005.vtk` exists; no s4 VTK or complete s4 checkpoint |

Every retained `fields_<cycle>_005.vtk` is s5 unload and is not a P0 s4
same-state packet.

### P1 transition inputs

| input | status | evidence boundary |
|---|---|---|
| U0.11 c121/s5 | partial | nodal VTK plus element reductions exist; complete native GP history/restart state is absent |
| U0.12 c82/s5 | missing | only element reductions exist; no nodal damage or complete restart state |
| U0.13 c58/s5 | partial | nodal VTK plus element reductions exist; complete native GP history/restart state is absent |

The partial rows are useful for audit only. They are not complete transition
inputs under Request 28. U0.12 c83/s5 remains prohibited as a substitute for
c82/s5.

### Restart audit

Each case retains only one terminal checkpoint:

```text
U0.11 terminal c125
U0.12 terminal c89
U0.13 terminal c62
```

There is no target-adjacent step/cycle checkpoint. A terminal checkpoint
cannot run backward, so every exact replay must follow the original Hard-5
solver from canonical c0/state0.

### Minimum exact replay ranges

| case | P0 only | P0+P1 |
|---|---|---|
| U0.11 | c0 -> c122/s4 | c0 -> c122/s4, additionally capture c121/s5 |
| U0.12 | c0 -> c83/s4 | c0 -> c83/s4, additionally capture c82/s5 |
| U0.13 | c0 -> c59/s4 | c0 -> c59/s4, additionally capture c58/s5 |

P1 adds no replay cycles. It only adds capture payload at states traversed by
the P0 replay.

### Audited capture path

The hook must run only after the current substep has converged and after
`p_field_old` and `history_vars_old` have been committed. The following may be
reused:

- original Hard-5 per-step VTK output;
- `peak_load_c1.vtk` s4 peak export pattern;
- `phase_field.audit.capture_peak_state` audit structure;
- toy-road substep capture/export mechanism only.

`capture_peak_state` is insufficient unchanged because it lacks the complete
history/psi payload and some timing paths are pre-history-refresh. Extend it
for Request 28 rather than silently accepting its current output contract.

Proposed full-run roots, after authorization:

```text
C:/q4runs/request28_first_detect_20260817_v1/u011
C:/q4runs/request28_first_detect_20260817_v1/u012
C:/q4runs/request28_first_detect_20260817_v1/u013
```

## Mac gate decision after audit

**Future replay selection**: P0+P1. It has the same cycle ranges as P0-only and
preserves both same-state and transition evidence without a second replay.

**Current execution decision**: full replay remains blocked. Run the following
cheaper instrumentation gate first only after its plan is posted:

```text
case: U0.13 Hard-5 canonical
range: c0/state0 -> c1/s5
captures:
  c1/s4 post-convergence, post-commit same-state packet
  c1/s5 post-convergence, post-commit committed-history packet
purpose:
  prove state timing and semantic labels
  prove complete native history/psi payload and shapes
  prove mesh/index and SHA manifest coverage
  prove the hook does not perturb the canonical c1 result
```

Before this smoke starts, the Windows outbox must declare:

1. exact hook location relative to convergence and both commits;
2. complete field/array names and native shapes at c1/s4 and c1/s5;
3. capture source files and hashes;
4. fresh smoke output root;
5. canonical c1 comparison assets;
6. predeclared numerical equivalence tolerances derived from export precision,
   not selected after seeing the smoke result;
7. pass/fail and cleanup behavior.

After the smoke passes, request explicit human GO before starting the three
full P0+P1 replays. Neither this audit nor this decision note authorizes full
replay.

## Acceptance checks

1. `c0/state0` is labelled zero-load recovered/reset initialization; c1 is
   labelled the first computed loading cycle.
2. Every row records source cycle, source substep, load factor, state timing,
   semantic class and required fields.
3. P0 rows contain `u_node`, `d_node` and `psi_raw_peak_elem` from exactly the
   same cN/s4 post-commit state.
4. P1 inputs are exactly c121/s5, c82/s5 and c58/s5; targets are explicit
   references to c122/s4, c83/s4 and c59/s4.
5. No cN/s5 field is relabelled as cN/s4, and no c83 field substitutes c82.
6. No c125/c86/c62 confirmation state enters the requested package.
7. Every array is finite, matches the indexed mesh and preserves native
   precision unless a documented equivalence check authorizes otherwise.
8. `d_node` lies in `[0,1]`, up to explicitly reported solver roundoff only.
9. Peak top-edge `u_y` matches Umax 0.11/0.12/0.13 within export precision.
10. Common coordinate/connectivity hashes match across the three cases.
11. `SHA256SUMS` covers every payload, index, README and provenance file.
12. Any replay includes the exact origin state, commit/dirty status, runtime,
    command, capture-code hashes and a non-perturbation check against a retained
    canonical anchor.

## Experiment gate

- **Mechanism question**: at one exact first-detect peak state, does a
  crack-enriched representation recover energetic localization from nodal
  displacement better than a plain displacement-gradient representation?
- **Primary claim changed later on Mac**: only the P0 same-state packet can
  support the observation-representation diagnostic.
- **Secondary claim**: P1 may support a transition-input/target diagnostic but
  cannot be cited as a same-state displacement-to-energy mapping.
- **Claim if unsuccessful**: stop the enrichment route; do not escalate to
  KAN/RBF/LoRA or PIDL retraining.
- **Cheaper diagnostic first**: archive/restart audit is complete. The next
  gate is a c0->c1/s5 post-commit capture smoke before full replay.
- **Minimal output asset now**: capture-smoke plan with hook timing, complete
  payload schema, predeclared equivalence tolerances and fresh output root.
- **Registry destination**: reply under Request 28 in
  `docs/handovers/windows_fem_outbox.md`.
- **Decision**: submit the smoke plan first; no smoke or full replay is
  authorized by this update alone.

## Next outbox response requested

Please report:

```text
CAPTURE_SMOKE_PLAN
  exact hook location after convergence and both state commits
  c1/s4 and c1/s5 native field names and shapes
  capture source paths and SHA256
  U0.13 c0->c1/s5 command and fresh output root
  retained canonical c1 comparison assets
  predeclared numeric equivalence tolerances
  pass/fail checks and cleanup behavior

BLOCKED
  exact missing source/capture path
  checks already attempted
  why a non-perturbing post-commit capture smoke cannot be constructed
```
