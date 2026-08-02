# Toy-to-Road P0/P0R Repeatability Baseline Design

Date: 2026-08-02

## Decision And Scope

The historical U0.12 cycle-1 Q2 parent is closed as
`historical_q2_parent_irrecoverable`. The Windows read-only audit is recorded
in `docs/handovers/windows_fem_outbox.md` at commit
`d2cdcbb8000e68aa9480148181ededcd5bfec489`. Historical Q2 remains blocked;
none of its missing fields may be reconstructed by changing their declared
semantics.

The approved replacement is a new, versioned synthetic-family baseline:

```text
P0 -> terminal validation
P0R -> terminal validation
P0/P0R repeatability gate
T1 -> terminal validation
T2 -> terminal validation
T3 -> terminal validation
```

P0 and P0R are independent executions of the same unmodified Hard5 U0.12
parent. T1, T2, and T3 retain their already sealed single-axis definitions and
are compared only with the new P0. This protocol supports an internally
consistent synthetic transfer family. It does not retroactively pass
historical Q2, establish active-field backward equivalence, or validate a real
road trajectory.

## Immutable Physical And Numerical Parent

P0 and P0R both use the fixed parent contract already declared for the
toy-to-road family:

- fresh hard-tip zero-load recovery;
- post-recovery damage projected to `[0,1]`, followed by rebuilding `System`;
- five retained substeps with factors `[0.25, 0.50, 0.75, 1.00, 0.00]`;
- `Umax=0.12`, `R=0`, and `eta=0`;
- `E=1`, `nu=0.3`, `Gc=0.01`, `ell=0.01`;
- `alpha_T=0.5`, `p=2`, plane strain, AMOR, and AT1 history fatigue;
- reverse top/bottom displacement boundary conditions;
- displacement tolerance `1e-6`, phase tolerance `4e-4`, and staggered
  tolerance `4e-4`;
- no line search, no cycle jump, no checkpoint resume, and no parameter
  adjustment after launch;
- penetration evaluated at cycle peak using at least three connected or
  adjacent right-boundary nodes with `d>=0.95` and `x>=0.48`;
- three post-hit confirmation cycles;
- stop immediately at confirmed penetration, otherwise right-censor at c150.

The c150 cap, tolerances, cadence, event rule, and confirmation rule may not be
changed to reduce wall time. Runtime reduction is limited to removing
non-contract output and avoiding redundant serialization.

## Runtime Identity

All five solves use one immutable runtime. The baseline runtime starts from the
accepted Q1 qualification:

```text
GRIPHFiTH source commit:
355d4c83fefc2db88c32031a2dd2623b3de85c89

rebuilt initial.mexw64 SHA-256:
ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db
```

The runtime lock also binds MATLAB release/update, compiler/build provenance,
AMOR, AT1-history-fatigue, CHOLMOD and every other consumed MEX hash. P0,
P0R, T1, T2, and T3 must use the same runtime-lock digest. A runtime change at
any point invalidates the family and requires a new protocol version; it may
not be handled by rerunning only the remaining cases.

Q1 is not rerun between family members. The old historical Q2 blocker is not
silently converted into a pass. Instead, the new P0/P0R repeatability evidence
becomes the cycle-level admission gate for this newly versioned family.

## P0 And P0R Input Identity

`P0_INPUT_LOCK.json` and `P0R_INPUT_LOCK.json` contain identical physical,
mesh, recovery, solver, cadence, exporter, runtime, and event fields. Their
only allowed differences are:

- `case_id` (`P0_parent` versus `P0R_parent_repeat`);
- fresh output-root identity;
- launch timestamp and no-clobber receipt identity.

Both launches start from independently reconstructed fresh state0. P0R may not
read P0 state, checkpoint, output, event metadata, or solver cache. A shared
read-only mesh/input artifact is permitted only when its exact hash is bound
by both input locks.

## Five-Substep Native GP Payload

Every completed physical cycle writes one cycle shard after all five retained
substeps converge. The shard uses MATLAB `-v7.3` and stores double-precision
arrays with stable Q4 element and Gauss-point ordering:

```text
substeps/cycle_NNNN.mat

d_gp             [n_elem, 4, 5]
psi_raw_gp       [n_elem, 4, 5]
g_gp             [n_elem, 4, 5]
psi_active_gp    [n_elem, 4, 5]
```

The third dimension is exactly the retained-substep order
`[0.25, 0.50, 0.75, 1.00, 0.00]`. Each shard also stores exact scalar/vector
metadata:

```text
cycle
substep_ordinal       = [1,2,3,4,5]
load_factor           = [0.25,0.50,0.75,1.00,0.00]
raw_step_zero_based   = 5*(cycle-1) + [0,1,2,3,4]
branch                = loading/loading/loading/loading/unloading
peak_substep_ordinal  = 4
mesh_sha256
element_ordering_id
gp_ordering_id
state_semantics_id
runtime_lock_sha256
input_lock_sha256
```

The fields have these semantics at every retained substep:

```text
d_gp          = Q4 interpolation of the converged nodal phase field at each GP
psi_raw_gp    = native undegraded AMOR tensile/raw driver at each GP
g_gp          = native damage degradation used at that GP
psi_active_gp = g_gp .* psi_raw_gp
```

The exporter verifies `psi_active_gp == g_gp .* psi_raw_gp` before publishing
the shard. It also derives element means using `mean(...,2)` over the four GPs;
it never uses a product of element means. No `f_alpha` field may be labelled
active.

The coherent cycle peak is substep 4 before unloading. Existing compact peak
state, event, mesh and cycle-index outputs are retained, but the peak GP fields
must reference the same bytes already present in the cycle shard rather than
being serialized a second time. Dense VTK output and unrelated visualization
snapshots are disabled for all five solves.

One MAT shard per cycle is chosen instead of five files per cycle. It preserves
all required states while reducing file count and redundant metadata. Field
precision, substep count, and state content may not be reduced for speed.

## State Legality Gates

Before a shard is accepted:

- all arrays must have exact shape `[n_elem,4,5]` and contain finite doubles;
- `d_gp` and `g_gp` must remain in `[0,1]` within range tolerance `1e-10`;
- raw and active drivers must be non-negative within range tolerance `1e-10`;
  values are never clipped by the validator;
- every negative value below tolerance fails the shard;
- active-driver recomputation must have maximum absolute error `<=1e-12` for
  every GP and substep;
- cycle, substep, load, raw-step, branch, mesh, ordering, runtime and input
  identities must be exact;
- cycle shards must be consecutive from c1 through the terminal cycle;
- the cycle-peak event state must be byte-identifiable with substep 4 of the
  same cycle shard.

Publication is no-clobber. An incomplete shard is never renamed or reported as
accepted. The final package manifest covers every source/input/runtime receipt,
state0, mesh, cycle shard, compact peak state, cycle index, event receipt and
terminal result.

## P0/P0R Repeatability Gate

The gate is declared before P0 starts and is evaluated only after both P0 and
P0R independently pass terminal package validation.

The following identities must match exactly:

- source, runtime, mesh, physical input, solver, recovery, exporter and event
  contracts;
- state0 and mesh ordering metadata;
- terminal reason and terminal cycle;
- first-hit and confirmed cycles;
- cycle/substep/load/raw-step/branch labels;
- array shapes and the complete set of field names.

For every saved numerical field at every cycle and retained substep, P0 is the
reference and P0R is the candidate. The gate computes in double precision:

```text
relative_L2 = norm(candidate-reference,2) /
              max(norm(reference,2),1e-30)
max_absolute = max(abs(candidate-reference))
```

Both conditions are required:

```text
relative_L2 <= 1e-12
max_absolute <= 1e-12
```

For an identically zero reference, the relative metric is reported as
`not_applicable_zero_reference`; `max_absolute <= 1e-12` remains mandatory.
No correlation, support mask, clipping, post-observation tolerance change, or
field-specific relaxation is permitted. Metadata and integer/index arrays are
compared exactly.

The gate emits per-field/per-cycle/per-substep metrics plus maxima over the
whole trajectory. Any missing field, extra field, non-finite value, event
difference, shape difference, identity difference, or threshold failure stops
the protocol before T1.

## Evidence Locks And Launch Authorization

The new protocol uses three immutable evidence layers:

1. `HISTORICAL_Q2_CLOSURE.json` binds the historical blocker, Windows search
   scope, locked parent hashes, audit commit and
   `historical_q2_parent_irrecoverable` verdict.
2. P0 and P0R each publish an independent validated package and no-clobber
   producer provenance bound to the accepted Q1 runtime.
3. `P0_REPEATABILITY_EVIDENCE_LOCK.json` binds both complete package manifests,
   repeatability metrics, PASS receipt, runtime lock, source commit, exporter
   hash and protocol version.

T1 launcher authorization requires the canonical repeatability evidence lock;
Q1 alone is insufficient. T2 additionally requires validated T1 terminal
evidence, and T3 additionally requires validated T1 and T2 terminal evidence.
The launcher rejects:

- a missing or failed historical closure;
- missing, failed, incomplete or mutable P0/P0R packages;
- missing or failed repeatability evidence;
- any source, runtime, exporter, mesh, or family-lock mismatch;
- a pre-existing output root, resume/checkpoint input, or running FEM process;
- an attempt to launch out of order;
- any previous family-member terminal-validation failure.

## Historical Comparison Boundary

The 2026-07-29 U0.12 result remains an external reference only. Comparisons may
use fields and events it actually saved, including element damage, history,
fatigue degradation, raw accumulated driver and first-hit/confirmed timing.
No report may claim historical equivalence for `g_gp`, `g_elem`,
`psi_active_gp`, or `psi_active_elem`, and no historical field may be relabelled
to create those quantities.

P0 becomes the sole parent for T1/T2/T3. Differences between P0 and the
historical trajectory are reported as version-boundary diagnostics, not tuned
away and not used to alter the P0/P0R gate.

## Execution And Failure Policy

Before each solve, the producer checks for an existing MATLAB/FEM experiment.
Only one experiment may run at a time. The strict order is:

```text
P0 -> validate -> P0R -> validate -> repeatability ->
T1 -> validate -> T2 -> validate -> T3 -> validate
```

Any failure stops the family. The launcher never terminates an unrelated
process, deletes an output root, resumes a failed solve, adjusts a gate, or
starts the next case. A rerun after failure requires a new reviewed execution
decision and a fresh output root.

## Test Contract

Automated tests must demonstrate fail-closed behavior for:

- P0/P0R physical-input differences outside the allowed identity fields;
- P0R reading any P0 state, checkpoint, output or cache;
- missing, reordered or duplicated substeps and cycles;
- incorrect raw-step or peak-state identity;
- missing, extra, wrong-shape, non-finite, illegal-range or clipped GP fields;
- `f_alpha` or a product of element means substituted for active driver;
- active GP product mismatch;
- repeatability at, below and above both `1e-12` thresholds;
- zero-reference fields;
- event, terminal, mesh, source, exporter or runtime mismatch;
- missing/failed/mutable repeatability evidence;
- T1/T2/T3 launch out of order or after a prior failure;
- runtime replacement between any two family members;
- pre-existing output, resume input, or concurrent FEM execution.

The source manifest, runtime/API hashes, Python tests and MATLAB tests must all
pass from a clean sealed checkout before P0 is launched. No controlled solver
fixture or preflight-only artifact may authorize production execution.
