# FEM producer execution note: toy-to-road evidence

Date: 2026-07-31

This note requests two separate FEM deliverables. They must not be merged or
interpreted as real-road validation.

## Producer and source rules

- Producer: approved Windows MATLAB/GRIPHFiTH environment with the required MEX
  and SuiteSparse runtime.
- Pull the latest pushed `codex/toy-road-evidence-integration` branch and record
  the exact clean commit before every solve.
- Never edit archived FEM references in place. Every run needs a new output
  root, immutable input snapshot, producer provenance and SHA-256 manifest.
- FEM eta is `0` throughout. The accepted scale contract is
  `w1 = Gc / ell`; `c_w` is applied once inside the phase-field energy.
- Keep `first_hit` and `confirmed` distinct. Do not relabel one as the other.
- A completed numerical run is not accepted until the mechanism-field and
  provenance bundle passes the Mac-side contract adapter.

## Deliverable A: execute Request 26 unchanged

Run the sealed F1b exact-Pi dimensional positive control from:

```text
producer_handoffs/f1b_exact_pi_20260729/
```

Use the existing PowerShell launcher and do not alter inputs, tolerances,
mesh, event rules or output names. This is one fresh solver-invariance control,
not a training trajectory and not one of the three independent variants.

Return the complete newly created output root containing at least:

```text
F1B_INPUT_SNAPSHOT.json
F1B_PRODUCER_PROVENANCE.json
F1B_EVENT_METADATA.json
f1b_event_trace.dat
f1b_mesh_geometry.mat
psi_fields/cycle_NNNN.mat
```

If the runtime is unavailable, return the exact environment error and stop this
deliverable as `BLOCKED`. Do not substitute another solver or relax the gate.

## Deliverable B: three independent synthetic trajectory variants

Use the current hard-tip, five-step, `Umax=0.12`, eta0 Hard5 trajectory as the
parent reference. Generate three complete variants, each with exactly one
declared primary variation axis. Existing hard/soft-tip or five/eight-substep
factorial runs do not satisfy this request.

### T1: geometric initial-defect variant

Change the physical initial-notch geometry, not only the initial damage
amplitude. Predeclare the baseline and candidate values of `a0/L`, notch-tip
coordinates and orientation in the input lock. Recommended first candidate:

```text
a0_candidate / L = 1.25 * (a0_reference / L)
orientation unchanged
material, loading history, BC, eta and event rule unchanged
```

If the existing mesh cannot resolve the modified tip with `h/ell` comparable
to the reference, generate a conforming mesh and declare that this is a
geometry-transfer trajectory. Record both mesh hashes and the mesh-mapping
contract; never silently reuse a mismatched field ordering.

### T2: material-state variant

Change one fracture-material state while keeping geometry, mesh, loading
history, BC and eta unchanged. Recommended first candidate:

```text
Gc_candidate = 1.20 * Gc_reference
E, nu, ell and fatigue-law parameters unchanged
```

The input lock must report the resulting `Gc/(E*ell)` and every other declared
Pi group. This is a material holdout, not an exact-Pi control, so the changed Pi
group is intentional. Do not tune `Gc` after seeing the event cycle.

### T3: physical loading-history variant

Keep geometry, mesh, material, BC, eta and five-substep numerical cadence
unchanged. Replace constant-amplitude cycling with a predeclared variable-
amplitude block history:

```text
cycles 1-30:  Umax_N = 0.90 * Umax_reference
cycles 31-60: Umax_N = 1.05 * Umax_reference
cycles 61+:   Umax_N = 1.00 * Umax_reference
R = 0 throughout
```

This is a physical load-history change. Merely changing five versus eight
substeps is numerical protocol sensitivity and is not accepted here. Export
the actual `Umax_N`, branch and raw step for every physical cycle.

## Completion and event rules

- Run each trajectory from a fresh initial state through confirmed penetration,
  or to a predeclared censor cap if no event occurs.
- Default connected event criterion remains the versioned Hard5 rule:
  at least three connected/adjacent right-boundary nodes with `d >= 0.95` at
  `x >= 0.48`, evaluated at cycle peak.
- Record the first cycle satisfying the criterion as `first_hit` and require
  the producer-declared three-cycle confirmation window for `confirmed`.
- If a geometry change makes the coordinate threshold invalid, express the
  same rule in normalized coordinates and record the exact transformed value
  before launching. Do not change it after seeing results.
- Event timing is descriptive. A timing shift is not a failure if the mechanism
  fields and provenance are valid.

## Required per-cycle mechanism payload

Export every cycle-peak state from cycle 1 through the terminal state. Each
state must include, with explicit nodal/element semantics and ordering:

```text
coordinates and connectivity
displacement u, v
damage d / alpha
alpha_bar history
fatigue degradation f_alpha
raw tensile driver psi_raw
damage degradation g(d)
active driver psi_active = g(d) * psi_raw
reaction / boundary resultant
cycle, Umax_N, substep, raw step and branch label
```

Also export the model-observable proxies that can be derived without changing
the solve:

```text
element strain or strain-energy summaries
binary/multithreshold crack masks derived from alpha
crack-tip and connected-boundary diagnostics
```

Do not label `alpha_bar`, `f_alpha`, `g(d)`, `psi_raw` or `psi_active` as direct
road sensors. They are FEM latent truth. FWD and WIM are unavailable from this
SENS solve unless a separately reviewed forward experiment is implemented.

## Required package layout

```text
toy_to_road_independent_fem_20260731/
  family_manifest.json
  SHA256SUMS.txt
  T1_initial_defect/
    INPUT_SNAPSHOT.json
    PRODUCER_PROVENANCE.json
    EVENT_METADATA.json
    mesh_geometry.mat
    cycle_index.csv
    states/cycle_NNNN.mat
  T2_material_state/
    ...
  T3_loading_history/
    ...
```

`family_manifest.json` must record parent reference ID, exact parameter diff,
source commit, solver/runtime identity, clean/dirty state, mesh hash, state
ordering, units, plane state, BC, degradation law, history-update ordering,
loading cadence, event rule and every file hash.

## Producer-side checks before handoff

For every state and field:

- all values finite;
- `0 <= alpha <= 1` within declared tolerance;
- `alpha_bar` and damage irreversibility semantics pass;
- `f_alpha` and `g(d)` lie in their legal ranges;
- `psi_raw >= 0` and `psi_active >= 0` within numerical tolerance;
- derived `psi_active` agrees with `g(d)*psi_raw`;
- mesh/order hashes are stable across cycles;
- event metadata points to existing state files;
- SHA-256 manifest verifies from a clean copy.

Return the output roots without renaming or merging them with earlier Umax or
Hard5 factorial archives. These three variants unlock only a synthetic
whole-trajectory LOTO study. They are not three real roads.

