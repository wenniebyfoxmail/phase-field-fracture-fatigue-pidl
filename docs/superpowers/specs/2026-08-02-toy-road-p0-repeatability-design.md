# Toy-to-Road P0/P0R Repeatability Baseline Design v2.1

Date: 2026-08-03

Revision: v2.1 incorporates review against remote commit
`300b295f474f455045752eb19ac988e472231a3a`. This revision is specification
only. No production runner may be written and no P0/P0R/T1/T2/T3 solve may
start until v2.1 passes review.

## Decision And Scope

The historical U0.12 cycle-1 Q2 parent is closed as
`historical_q2_parent_irrecoverable`. The Windows read-only audit is recorded
in `docs/handovers/windows_fem_outbox.md` at commit
`d2cdcbb8000e68aa9480148181ededcd5bfec489`. Historical Q2 remains blocked;
none of its missing fields may be reconstructed by changing their declared
semantics.

The approved replacement is a new, versioned synthetic-family baseline:

```text
P0(c5 numerical gate) -> terminal validation
P0R(c5 numerical gate) -> terminal validation
P0/P0R repeatability gate
T1(c5 numerical gate) -> terminal validation
T2(c5 numerical gate) -> terminal validation
T3(c5 numerical gate) -> terminal validation
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
silently converted into a pass. P0, P0R, T1, T2 and T3 must each pass the same
reference-independent same-process numerical-solution gate in their own state
and geometry, and only then may their terminal packages be accepted. P0/P0R
repeatability is a separate cycle-level reproducibility gate; it cannot qualify
an under-converged branch or authorize a variant that fails its own gate.

## P0 And P0R Input Identity

Input identity is split into three digests:

- `family_contract_sha256` hashes the shared runtime/environment, cadence,
  exporter, numerical-gate, event, state-semantics and complete predeclared
  case-axis contract. It must be exactly equal for all five cases.
- `case_physics_contract_sha256` hashes `family_contract_sha256` plus one
  case's canonical physical, mesh, recovery, material and loading fields. It
  must be equal for P0 and P0R. T1, T2 and T3 have different case digests that
  encode only their already predeclared single-axis change.
- `execution_input_lock_sha256` hashes one complete execution lock, including
  both parent digests, case ID, fresh roots, launch timestamp and no-clobber
  receipt identity. It is unique to each launch and is validated only against
  that execution's own manifest.

`P0_INPUT_LOCK.json` and `P0R_INPUT_LOCK.json` therefore contain the same
`family_contract_sha256` and `case_physics_contract_sha256`. Their execution
layers may differ only in:

- `case_id` (`P0_parent` versus `P0R_parent_repeat`);
- fresh output-root identity;
- launch timestamp and no-clobber receipt identity.

Both launches start from independently reconstructed fresh state0. P0R may not
read P0 state, checkpoint, output, event metadata, or solver cache. A shared
read-only mesh/input artifact is permitted only when its exact hash is bound
by both input locks.

## C5 Peak Same-Process Numerical-Solution Gate

Each of P0, P0R, T1, T2 and T3 must pass an independent reference-free gate at
its own physical cycle 5, retained peak substep 4. The gate runs inside that
case's original one-shot MATLAB solve process after the normal staggered loop
reports convergence and before the c5-peak history commit or any c6 work. It
reassembles the governing operators at the converged `(u,d)` state without
taking another Newton step. Passing P0 does not qualify a changed geometry,
material or loading history.

At entry to the c5 peak substep, the process snapshots the accepted lower-bound
damage `d_lb` and pre-commit history `history_pre`. At the end of every
completed stagger iteration it records the current damage. Let `d_prev_stag`
be the immediately preceding completed stagger iterate; for the first stagger
iteration it is the accepted damage at substep entry.

The gate first forms `r_u_active=r_u(active_u_dofs)`,
`r_d_active=r_d(active_d_dofs)`, `d_active=d(active_d_dofs)` and
`d_lb_active=d_lb(active_d_dofs)`. It then computes:

```text
displacement_residual = norm(r_u_active(:), 2)
raw_phase_residual = norm(r_d_active(:), 2)

projected_phase_kkt = norm(
    d_active(:) -
    project_[d_lb_active,1](d_active(:) - r_d_active(:)),
    inf)

consecutive_stagger_delta = norm(d(:) - d_prev_stag(:), inf)

primal_feasibility = max([
    0;
    d_lb(:) - d(:);
    d(:) - 1
])
```

Here `r_u` is the equilibrium residual reassembled with the converged damage
and current traction, and `r_d` is the phase residual reassembled with the
same instantaneous raw driver, `d_lb`, and `history_pre` used by the c5 peak
phase solve. `project_[d_lb,1]` is the componentwise projection onto the
irreversibility box. No residual is replaced by an energy difference.

All four gates are mandatory:

```text
displacement_residual       <= 4e-4
projected_phase_kkt          <= 4e-4
consecutive_stagger_delta    <= 1e-3
primal_feasibility           <= 1e-12
```

The process saves a no-clobber c5 peak stagger trace with one row per completed
stagger iteration. Each row is computed by post-update same-process
reassembly, not by the pre-update Newton stopping value, and contains iteration
ordinal, displacement residual, raw phase residual, projected phase KKT,
consecutive-stagger damage infinity norm and primal feasibility. The final row
is bound into the gate receipt and the package manifest.

This is a fixed-point/KKT qualification of the produced solution. It may not
use a teacher field, historical replay, P0/P0R comparison, fixed stagger count,
forced extra iterations or a post-process launched after the solver exits. A
failure stops that execution before history commit. A P0/P0R failure prevents
repeatability evaluation; a T1/T2/T3 failure prevents terminal acceptance and
authorization of every later family member.

## Independent One-Shot Execution Environment

Every P0, P0R, T1, T2 and T3 case uses a fresh one-shot `matlab -batch`
process. Each receives
independent, initially absent writable work, `TEMP`, `TMP`, MATLAB preference
and application-cache roots. The launcher rejects paths shared with the other
execution and exits the MATLAB process after success or failure; persistent
MEX state cannot cross the process boundary.

The physics contract fixes these process settings for all five solves:

```text
OMP_NUM_THREADS=1
MKL_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
MKL_DYNAMIC=FALSE
```

Every execution receipt records and verifies the same Windows machine/CPU
fingerprint, Windows build, MATLAB executable hash and release/update, MATLAB
path ordering and hash, `version -blas`, `version -lapack`, thread environment,
runtime-lock digest and MEX hashes. A mismatch fails before solving. The
separate writable roots and launch-specific receipts remain part of
`execution_input_lock_sha256`, not `case_physics_contract_sha256`. The shared
machine/runtime settings are bound by `family_contract_sha256`. Case-specific
writable roots are never added to the canonical MATLAB path, so the path hash
remains meaningfully comparable across executions.

## Five-Substep Native GP Payload

Every completed physical cycle writes one cycle shard after all five retained
substeps converge. The shard uses MATLAB `-v7.3` and stores double-precision
arrays with stable Q4 element and Gauss-point ordering:

```text
substeps/cycle_NNNN.mat

d_gp             [n_elem, 4, 5]
d_node           [n_node, 5]
alpha_bar_gp     [n_elem, 4, 5]
f_alpha_gp       [n_elem, 4, 5]
psi_raw_gp       [n_elem, 4, 5]
g_gp             [n_elem, 4, 5]
psi_active_gp    [n_elem, 4, 5]
psi_raw_cyclemax_gp [n_elem, 4]
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
family_contract_sha256
case_physics_contract_sha256
execution_input_lock_sha256
```

The fields have these semantics at every retained substep:

```text
d_gp          = Q4 interpolation of converged nodal damage at the same substep
alpha_bar_gp  = fatigue accumulation after that converged substep is committed
f_alpha_gp    = fatigue degradation after that converged substep is committed
psi_raw_gp    = instantaneous undegraded AMOR raw driver at that substep
g_gp          = instantaneous damage degradation at that substep
psi_active_gp = same-substep g_gp .* psi_raw_gp

psi_raw_cyclemax_gp = max(psi_raw_gp, [], 3) over the five current-cycle
                      instantaneous substeps; it is a separate diagnostic
```

For each retained substep, the converged `(u,d)` and instantaneous raw driver
are captured before history mutation. The normal solver then commits that
substep's history exactly once; `alpha_bar_gp` and `f_alpha_gp` are captured
from this post-commit state. The shard declares
`history_state_semantics=post_commit_after_converged_substep_v1`. No later
substep or cycle may overwrite an earlier saved history slice.

The exporter independently verifies both constitutive identities before
publishing the shard:

```text
g_gp = (1 - d_gp).^2 + eta
psi_active_gp = g_gp .* psi_raw_gp
```

Both maximum absolute errors must be `<=1e-12`; `eta` is the locked scalar
`0` for this family. The exporter also derives element means using
`mean(...,2)` over the four GPs; it never uses a product of element means. No
`f_alpha` field or cycle-maximum raw field may be labelled active.

The coherent cycle peak is substep 4 before unloading. Peak active is exactly
`g_gp(:,:,4).*psi_raw_gp(:,:,4)`; it may not use
`psi_raw_cyclemax_gp`. Existing compact peak state, event, mesh and cycle-index
outputs are retained, but the peak GP fields must reference the same bytes
already present in the cycle shard rather than being serialized a second time.
Dense VTK output and unrelated visualization snapshots are disabled for all
five solves.

One MAT shard per cycle is chosen instead of five files per cycle. It preserves
all required states while reducing file count and redundant metadata. Field
precision, substep count, and state content may not be reduced for speed.

## State Legality Gates

Before a shard is accepted:

- the six five-substep GP arrays must have exact shape `[n_elem,4,5]` and
  contain finite doubles;
- `d_node` must have exact shape `[n_node,5]` and contain finite doubles;
- `psi_raw_cyclemax_gp` must have exact shape `[n_elem,4]`, equal
  `max(psi_raw_gp,[],3)` within `1e-12`, and remain semantically separate from
  every instantaneous and active field;
- for each substep, `d_lb_node` is the immediately preceding accepted nodal
  damage in chronological order, using state0 before c1/substep 1; nodal damage
  must satisfy
  `max([0; d_lb_node(:)-d_node(:); d_node(:)-1]) <= 1e-12` with no clipping;
- `d_gp` and `g_gp` must remain in `[0,1]` within range tolerance `1e-10`;
- `alpha_bar_gp` must be non-negative within tolerance `1e-12` and must not
  decrease by more than `1e-12` from its chronological predecessor across both
  substep and cycle boundaries; the predecessor of c1/substep 1 is the locked
  state0 history;
- `f_alpha_gp` must remain in `[0,1]` within tolerance `1e-12`;
- raw and active drivers must be non-negative within range tolerance `1e-10`;
  values are never clipped by the validator;
- every negative value below tolerance fails the shard;
- damage-degradation, fatigue-degradation and active-driver recomputations must
  each have maximum absolute error `<=1e-12` for every GP and substep. The
  fatigue reference uses the locked GRIPHFiTH Carrara implementation exactly,
  without an algebraic rewrite:

  ```text
  f_alpha_expected = min(1, ...
      (1 - ((alpha_bar_gp - alpha_T) ./ ...
            (alpha_bar_gp + alpha_T))).^p)
  alpha_T = 0.5
  p = 2
  ```

  It is evaluated from the post-commit `alpha_bar_gp` slice and compared to the
  independently exported `f_alpha_gp`; recomputing both from one exporter
  temporary is not a legality test;
- cycle, substep, load, raw-step, branch, case-declared mesh, ordering, runtime,
  family-contract, case-physics-contract and own execution-lock identities must
  be exact;
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

- source, runtime, P0/P0R parent mesh, `family_contract_sha256`,
  `case_physics_contract_sha256`, physical input, solver, recovery, exporter,
  numerical-solution and event contracts;
- state0 and mesh ordering metadata;
- terminal reason and terminal cycle;
- first-hit and confirmed cycles;
- cycle/substep/load/raw-step/branch labels;
- array shapes and the complete set of physical field names.

`execution_input_lock_sha256`, case ID, fresh-root identity, timestamps and
receipt identities are verified against each package's own manifest but are
not compared for cross-run equality.

For every saved physical numerical field at every cycle and retained substep,
P0 is the reference and P0R is the candidate. Arrays of any dimensionality are
vectorized before norm and maximum operations. The gate computes in double
precision:

```text
delta = candidate(:) - reference(:)
reference_vector = reference(:)
relative_L2 = norm(delta,2) / max(norm(reference_vector,2),1e-30)
max_absolute = max(abs(delta))
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
2. P0 and P0R each publish an independent validated package, passing its own c5
   peak numerical-solution receipt and no-clobber producer provenance bound to
   the accepted Q1 runtime. Every T1/T2/T3 terminal manifest likewise binds that
   case's complete c5 stagger trace and PASS receipt; a parent receipt cannot be
   reused by a variant.
3. `P0_REPEATABILITY_EVIDENCE_LOCK.json` binds both complete package manifests,
   both c5 numerical-solution PASS receipts, repeatability metrics, PASS
   receipt, runtime lock, source commit, exporter hash and protocol version.

T1 launcher authorization requires the canonical repeatability evidence lock;
Q1 alone is insufficient. T2 additionally requires validated T1 terminal
evidence including the T1 c5 PASS receipt, and T3 additionally requires
validated T1 and T2 terminal evidence including both case-local c5 PASS
receipts.
The launcher rejects:

- a missing or failed historical closure;
- missing, failed, incomplete or mutable P0/P0R packages;
- missing or failed repeatability evidence;
- any source, runtime, exporter, family-contract, or case-declared mesh-hash
  mismatch; T1 must match its predeclared mapped-mesh hash and is not required
  to equal the P0 parent-mesh hash;
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

## Primary Asset, Attempt Ledger And Registry

The family has exactly one primary scientific/qualification asset:

```text
docs/toy_road_p0_repeatability_20260802/decision.md
```

That file is created in a pre-execution blocked state and updated only by the
sealed evidence publication workflow to a terminal pass, failure or blocker.
P0, P0R, T1, T2 and T3 must not create competing primary `decision.md` files.
Per-case package receipts remain evidence linked from this decision.

Every preflight, blocked launch, failed attempt and completed launch is appended
to the canonical machine-readable attempt ledger:

```text
docs/toy_road_p0_repeatability_20260802/_pidl_attempt_ledger/attempts.jsonl
```

Each ledger entry records attempt ID, case role, source commit, family-contract
digest, case-physics-contract digest, execution-lock digest, runtime digest,
roots, process/environment fingerprint, start/end state and linked immutable
receipts. Existing entries are never rewritten or deleted. The repository's
attempt-ledger tool renders the human-readable view at
`docs/toy_road_p0_repeatability_20260802/attempt.md`; the rendered file is not a
second ledger.

`docs/pidl_experiment_inventory.md` contains exactly one registry row with case
ID `toy_road_p0_repeatability_family_20260802` and the primary asset above.
P0/P0R are producer repeatability and numerical-solution qualification runs,
not two independent trajectories, training cases or LOTO members. The row's
claim boundary states that only T1/T2/T3 are candidate synthetic transfer
trajectories after all gates pass; none is real-road validation.

## Execution And Failure Policy

Before each solve, the producer checks for an existing MATLAB/FEM experiment.
Only one experiment may run at a time. The strict order is:

```text
P0(c5 numerical gate) -> validate ->
P0R(c5 numerical gate) -> validate -> repeatability ->
T1(c5 numerical gate) -> validate ->
T2(c5 numerical gate) -> validate ->
T3(c5 numerical gate) -> validate
```

Any failure stops the family. The launcher never terminates an unrelated
process, deletes an output root, resumes a failed solve, adjusts a gate, or
starts the next case. A rerun after failure requires a new reviewed execution
decision and a fresh output root.

## Test Contract

Automated tests must demonstrate fail-closed behavior for:

- P0/P0R physical-input differences outside the allowed identity fields;
- unequal `family_contract_sha256` among any of the five cases;
- unequal P0/P0R `case_physics_contract_sha256`, or a T1/T2/T3 case digest that
  does not encode exactly its predeclared single-axis change relative to P0;
- an `execution_input_lock_sha256` not self-consistent with its own manifest;
- P0R reading any P0 state, checkpoint, output or cache;
- reused writable work/TEMP/TMP/preference/cache roots, persistent MATLAB/MEX
  state, CPU/Windows/MATLAB-path/BLAS/thread-setting mismatch, or a process that
  is not a fresh one-shot MATLAB invocation;
- missing or failing case-local c5 same-process displacement, projected-KKT,
  consecutive-stagger or primal-feasibility gate for any of P0, P0R, T1, T2 or
  T3, or a terminal manifest missing its own trace and PASS receipt;
- a c5 gate produced post-process, by fixed iteration count, teacher comparison
  or replay qualification, or without a complete stagger trace;
- missing, reordered or duplicated substeps and cycles;
- incorrect raw-step or peak-state identity;
- missing, extra, wrong-shape, non-finite, illegal-range or clipped GP/nodal
  fields;
- pre-commit history labelled post-commit, overwritten history slices, or a
  missing `alpha_bar_gp`/`f_alpha_gp` five-step payload;
- negative or chronologically decreasing `alpha_bar_gp`, out-of-range
  `f_alpha_gp`, mismatch with the locked Carrara formula, or nodal damage that
  violates `d_lb <= d <= 1`;
- instantaneous raw, cycle-maximum raw and active fields relabelled or mixed;
- `f_alpha`, cycle-maximum raw, or a product of element means substituted for
  active driver;
- degradation-law or active GP product mismatch;
- repeatability at, below and above both `1e-12` thresholds;
- matrix and three-dimensional repeatability inputs that prove vectorized norm
  semantics;
- zero-reference fields;
- event, terminal, case-declared mesh, source, exporter or runtime mismatch;
- T1 correctly using its predeclared mapped-mesh hash while rejecting either
  the P0 hash or an undeclared third mesh;
- missing/failed/mutable repeatability evidence;
- T1/T2/T3 launch out of order or after a prior failure;
- runtime replacement between any two family members;
- pre-existing output, resume input, or concurrent FEM execution;
- multiple primary decisions, multiple registry rows, missing attempt entries,
  or P0/P0R counted as independent training/LOTO trajectories.

The source manifest, runtime/API hashes, Python tests and MATLAB tests must all
pass from a clean sealed checkout before P0 is launched. No controlled solver
fixture or preflight-only artifact may authorize production execution.
