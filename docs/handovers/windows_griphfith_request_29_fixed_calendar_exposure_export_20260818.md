# Windows-FEM Request 29 — fixed-calendar peak states for fatigue exposure

Date: 2026-08-18

From: Mac-PIDL

To: Windows-FEM / GRIPHFiTH

Priority: high, minimal diagnostic export

Evidence class: `state-semantics` / `field-mechanism` input only

## Goal

Export the nine exact fixed-calendar s4 peak states required to test whether a
load-normalized displacement residual contains fatigue-state and remaining-life
information beyond `cycle * Umax`. This is not a request for PIDL training,
event replay, or another architecture.

## Source family

Reuse the exact Hard-5 eta0 five-substep family:

```text
Hard5_eta0_5step_Umax_011_012_013_20260729/
```

Preserve mesh, ordering, AMOR/AT1 physics, eta, fatigue law, tolerances,
boundary conditions, five-substep cadence and first-detect detector.

## Exact state matrix

Export exactly:

```text
Umax = 0.11: c10/s4, c20/s4, c40/s4
Umax = 0.12: c10/s4, c20/s4, c40/s4
Umax = 0.13: c10/s4, c20/s4, c40/s4
```

Every row is `post-convergence, post-damage-commit, post-history-commit,
post-cyclemax-update` at load factor 1.0. It must use the same timing semantics
accepted for Request 28. Do not export a pre-history-refresh state.

Do not add c50: it is only nine cycles before U0.13 first detect c59 and is
outside this frozen early/intermediate gate. Do not use first-detect or
confirmation states as replacements.

## Existing c1 references

The three canonical `peak_load_c1.vtk` files already exist and share the
86,756-node/86,408-cell mesh. Copy or hash-reference them into the handoff as:

```text
within_trajectory_c1_normalized_reference
```

They are empirical first-cycle references, not certified virgin elastic
solutions. No extra healthy-elastic solve is requested.

## Required payload per state

```text
node_coords              [Nnode, 2]
connectivity_q4          [Nelem, 4]
node_ids                 [Nnode]
element_ids              [Nelem]
u_node                   [Nnode, 2]
d_node                   [Nnode]
d_gp or d_elem           native representation
alpha_bar_gp/elem        native cumulative-history representation
f_alpha_gp/elem          native fatigue degradation
psi_raw_gp/elem          native raw tensile driver/energy
psi_active_gp/elem       if solver stores it; otherwise document exact derivation
cycle, substep=4, load_factor=1.0, imposed_Umax
damage/history/cyclemax commit flags
state_timing and staggered-iteration metadata
```

Do not nodalize an element/GP hidden field merely for convenience. The primary
observable uses only `u_node`; hidden fields are same-cycle audit targets.

## Execution scope

1. Audit retained checkpoints/state files first.
2. Existing `fields_<cycle>_005.vtk` is s5 unload and cannot satisfy this
   request even though it contains hidden fields.
3. Existing `psi_fields/cycle_*.mat` cannot substitute for peak displacement.
4. If direct export is unavailable, use a fresh root and replay each case from
   the canonical c0/state0 initialization path only through c40.
5. Capture c10/c20/c40 during that one replay. Do not replay to c59/c83/c122.
6. Never overwrite the July canonical cases or Request 28 package.

Reuse the corrected Request 28 post-commit capture hook. Toy-road mechanisms
may inform capture implementation but no toy-road numerical state may enter.

## Preferred package

```text
hard5_fixed_calendar_exposure_states_20260818/
  README.md
  state_index.csv
  c1_reference_index.csv
  data/
    u011/c0010_s004_post_commit.mat
    u011/c0020_s004_post_commit.mat
    u011/c0040_s004_post_commit.mat
    u012/c0010_s004_post_commit.mat
    u012/c0020_s004_post_commit.mat
    u012/c0040_s004_post_commit.mat
    u013/c0010_s004_post_commit.mat
    u013/c0020_s004_post_commit.mat
    u013/c0040_s004_post_commit.mat
  references/
    u011_peak_load_c1.vtk
    u012_peak_load_c1.vtk
    u013_peak_load_c1.vtk
  provenance/
    source_commit.txt
    source_paths.txt
    replay_commands.txt
    runtime_versions.txt
    replay_logs/
  SHA256SUMS.txt
```

`state_index.csv` must include:

```text
umax,cycle,substep,load_factor,state_timing,semantic_class,array_file,
node_count,element_count,mesh_sha256,source_kind,source_checkpoint,
damage_committed,history_committed,cyclemax_updated,export_timestamp
```

## Acceptance criteria

1. Exactly nine rows: 3 Umax x c10/c20/c40; no c50/event/confirmation row.
2. Every row is cN/s4, load factor 1.0, post-commit, finite and native Q4.
3. All mesh hashes and node/element orderings match Request 28 and c1.
4. Top-edge `u_y` equals the declared Umax within solver/export precision.
5. Peak `u_node` is nonzero and is not copied from s5 unload.
6. `d_node` is finite and bounded in [0,1] up to reported roundoff.
7. Native history/fatigue/driver representations and dimensions are indexed.
8. Replay, if used, ends at c40 and reproduces at least c1 or a retained
   c10/c20/c40 hidden-field anchor within declared numerical tolerance.
9. SHA256SUMS covers all payload, index, reference and provenance files.

If any exact state cannot be recovered, report `BLOCKED` with the missing
checkpoint/capture and do not infer displacement from psi or unload VTK.

## Frozen downstream formula — do not optimize on Windows

Mac will compute, without parameter fitting:

```text
u_res(N) = u_s4(N)/Umax - u_s4(c1)/Umax
h_ROI = 0.04
Omega_L = {cell centre x >= 0, |y| <= 0.04}
A_u(N) = area-weighted RMS ||sym(grad u_res)||_F
z_E_inst = N * A_u(N)
z_E_cum = fixed sparse-calendar trapezoidal integral over c10/c20/c40
```

No Umax exponent, response exponent, ROI tuning, KAN/RBF/Williams basis or
training is authorized.

## Outbox response

Reply under Request 29 in `docs/handovers/windows_fem_outbox.md` with either:

```text
COMPLETE
  package path
  state count and index audit
  direct export vs replay per row
  replay start/end and anchor comparison
  mesh/top-edge/bounds/hash checks

BLOCKED
  exact missing state or implementation blocker
  checks attempted
  minimum replay/capture change needed
```

