# Windows-FEM Hard-5 archival contract v1 — DRAFT / HOLD

Date: 2026-08-18

Owner: Mac-PIDL specification; Windows-FEM producer

Status: `DRAFT_PENDING_EXTERNAL_ARCHITECTURE_REVIEW`

Execution authorization: **none**. Do not start MATLAB or replay from this
document. Request 29 is on hold until this contract is reviewed and explicitly
released.

Evidence class: `tooling-only` / `state-semantics`. Archive completeness cannot
support a fatigue-exposure, early-warning, RUL, or field-mechanism claim.

## Purpose

Make the next canonical replay the last replay that starts from `c0/state0`
merely because intermediate peak or restart state was not retained. Keep the
scientific Request 29 consumer (c10/c20/c40) separate from the acquisition
infrastructure: the archive may contain more states, but only preregistered
states may enter a scientific gate.

## Scope decision still required

Two scopes must not be conflated:

1. `A_C40_ARCHIVE`: replay each Umax only through c40 and retain c1..c40.
   This satisfies Request 29 and prevents c0 replay only for cycles at or below
   c40. It cannot honestly be called the final c0 replay for the trajectories.
2. `B_FIRST_DETECT_ARCHIVE`: replay U0.11 through c122, U0.12 through c83 and
   U0.13 through c59, stopping at first detect. This can fill the complete
   pre-event archive and support the statement that later field requests up to
   first detect should not require another c0 replay.

Neither scope includes confirmation cycles. Scope B is materially more compute
and is not authorized by Request 29; it needs separate explicit approval.

## Two-layer storage model

Store immutable mesh/parameter data once per trajectory. Do not duplicate the
mesh in every snapshot unless a compatibility export needs a self-contained
file.

### Layer A — s4 analysis snapshot, every completed cycle

Timing label:

```text
cN/s4_post_convergence_post_damage_history_cyclemax_commit_pre_s5
```

Required native dynamic payload:

- `u_node [Nnode,2]` and native nodal `d_node [Nnode]`;
- `p_field_old` or the solver's exact committed damage state;
- complete native `history_vars_old` with documented component ordering;
- native `alpha_bar_gp`, `f_alpha_gp`, `psi_raw_gp`, `psi_cyclemax_gp` and
  `psi_eff_prev_gp` when they are distinct solver states;
- any other dynamic array required to interpret the fatigue update without
  reconstructing it;
- cycle, substep, load factor, imposed Umax, nonlinear/stagger iteration count,
  convergence flags and explicit commit flags.

Derived element reductions, nodalized GP fields and recomputed strain may be
provided as convenience fields, but must be labelled `derived` with method and
source hashes. They never replace the native arrays. `strain_gp` may be omitted
from the every-cycle core when it is deterministically recomputable from
`u_node`, native Q4 connectivity and the frozen quadrature implementation.

### Layer B — s5 restart checkpoint, every completed cycle

Timing label:

```text
cN/s5_post_convergence_post_all_commits_ready_for_c(N+1)/s1
```

The checkpoint must contain every variable the original solver needs to resume
the exact path, including the converged displacement/damage state, committed
damage/history/fatigue/cycle-max arrays, cycle counters, solver continuation
metadata, immutable-parameter reference and code/config identity.

The contract uses an s5 checkpoint for every cycle because this is the only
scheme that guarantees a missing cN peak field can be regenerated from
c(N-1)/s5 by replaying at most one cycle. A strided checkpoint scheme cannot
make that guarantee. If storage later forces a stride, rename the guarantee to
`replay_at_most_stride_cycles`; do not keep the one-cycle claim.

## Event-adjacent analysis pair

When first detect is reached at cN, additionally export accessible analysis
snapshots, not merely opaque restart files:

```text
transition_input:  c(N-1)/s5 post-commit
same_state_target: cN/s4 post-commit
```

Label this as a cross-cycle `transition_pair`. Never call it one converged FEM
state. Do not generate or retain confirmation cycles under this contract.

## Static package

Store once per trajectory and hash-reference from every row:

- node coordinates, node IDs, native Q4 connectivity and element IDs;
- material/fatigue parameters, boundary/load cadence and detector definition;
- state0 identity and hash;
- solver source commit or source-tree hash, MATLAB/runtime version;
- exact capture-hook source and configuration.

## Index and provenance

`state_index.csv` must contain at least:

```text
trajectory_id,umax,cycle,substep,load_factor,state_timing,semantic_class,
analysis_or_restart,array_file,mesh_sha256,state_sha256,source_kind,
source_checkpoint,parent_checkpoint_sha256,restart_next_cycle,
damage_committed,history_committed,cyclemax_updated,converged,
staggered_iterations,code_sha256,config_sha256,export_timestamp
```

Also provide `field_schema.csv`, `RUN_PROVENANCE.txt`, replay commands/logs and
`SHA256SUMS.txt`. `field_schema.csv` records field name, native/derived status,
location (node/element/GP/global), shape, dtype, units, component meaning and
derivation when applicable.

## Pre-launch gates

No production replay is allowed until all gates pass:

1. **Schema audit** — Windows identifies the exact solver variables backing
   every required native field and restart field; no placeholder is accepted.
2. **Size audit** — capture one representative s4 snapshot and one s5
   checkpoint using the final schema; report compressed and uncompressed bytes,
   write time and projected total with at least 20% free-space reserve.
3. **Restart equivalence micro-test** — continuous c1→c2 versus restart from
   c1/s5→c2 must match declared c2/s4 and c2/s5 arrays within a frozen numerical
   tolerance. File readability alone is insufficient.
4. **Timing audit** — assert s4 capture occurs after damage/history/cycle-max
   commit and before s5, and s5 restart is ready for the next cycle's s1.
5. **Scope approval** — explicitly select `A_C40_ARCHIVE` or
   `B_FIRST_DETECT_ARCHIVE` and record storage/run-time budget.

Stop and reply `BLOCKED` if any required native variable cannot be identified,
restart equivalence fails, state timing is ambiguous, projected free space is
insufficient, or the selected scope is not explicitly authorized.

## Current measured storage evidence

The accepted Request 28 package provides the nearest measured sizes:

- full s4/s5 analysis snapshots: approximately 35.0–36.3 MB each;
- existing terminal checkpoints: approximately 7.8–8.3 MB each.

There are 122 + 83 + 59 = 264 cycles through first detect. Naively retaining
both artifacts each cycle projects approximately 11.3–11.8 GB before logs,
hashes and filesystem overhead. Plan roughly 14 GB with a 20% reserve, then
replace this estimate with the final-schema size audit. Static-mesh
deduplication and omission of labelled deterministic convenience fields may
reduce the analysis-snapshot component, but must not remove native state.

## PIDL Experiment Gate

- Mechanism question: none; can the archival implementation preserve exact
  peak semantics and one-cycle restartability?
- Claim changed if success: future state requests up to the approved endpoint
  need not replay from c0 solely due to missing archives.
- Claim changed if failure: none scientifically; archival design remains
  unqualified and production replay stays blocked.
- Cheaper diagnostic first: schema/size audit and c1→c2 restart equivalence.
- Minimal output asset: contract, micro-test report, state index and hashes.
- Code/producer alignment: Mac specifies; Windows-FEM implements and runs.
- Success criteria: all five pre-launch gates pass.
- Failure criteria: any stop condition above.
- Registry destination: Windows FEM outbox plus the relevant handover entry.
- Decision: `diagnose first`; no production launch.
