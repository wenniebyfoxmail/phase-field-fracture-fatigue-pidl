# Windows-FEM Hard-5 archival contract v1 — REVISED / HOLD

Date: 2026-08-18

Owner: Mac-PIDL specification; Windows-FEM producer

Status: `EXTERNAL_REVIEW_COMPLETE__NEXT_GATE_SCHEMA_FREEZE`

Execution authorization: **none**. Do not start MATLAB or replay from this
document. Request 29 is on hold until the staged qualification below passes and
the relevant next gate is explicitly released.

External review: `MODIFY_AND_FREEZE_ARCHIVAL_CONTRACT_BEFORE_REPLAY`; see
`docs/reviews/windows_griphfith_archival_contract_external_review_20260818.md`.

Evidence class: `tooling-only` / `state-semantics`. Archive completeness cannot
support a fatigue-exposure, early-warning, RUL, or field-mechanism claim.

## Purpose

Qualify an archival mechanism that can eventually make the production replay
the last replay starting from `c0/state0` merely because intermediate peak or
restart state was not retained. Keep the scientific Request 29 consumer
(c10/c20/c40) separate from the acquisition infrastructure: the archive may
contain more states, but only preregistered states may enter a scientific gate.

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
and is not authorized by Request 29; it needs separate explicit approval only
after qualification Gates 0–3 pass.

## Two-layer storage model

Store immutable mesh/parameter data once per trajectory. Do not duplicate the
mesh in every snapshot unless a compatibility export needs a self-contained
file.

### Layer A — `ANALYSIS_PEAK_POSTCOMMIT`, every completed cycle

Timing label:

```text
cN/s4_post_convergence_post_all_state_commit_pre_s5
```

Required native dynamic payload:

- `u_node [Nnode,2]` and native nodal `d_node [Nnode]`;
- `p_field_old` or the solver's exact committed damage state;
- complete native `history_vars_old` with documented component ordering;
- native `alpha_bar_gp`, `psi_raw_gp`, `psi_cyclemax_gp` and
  `psi_eff_prev_gp` when they are distinct evolved solver states;
- any other dynamic array required to interpret the fatigue update without
  reconstructing it;
- cycle, substep, load factor, imposed Umax, nonlinear/stagger iteration count,
  convergence flags and explicit commit flags.

Derived `f_alpha`, element reductions, nodalized GP fields and recomputed strain
may be provided as convenience fields, but must be labelled `derived` with
method and source hashes. They never replace the native primitives. A derived
field may be omitted when it is exactly reproducible from those primitives and
the frozen constitutive/quadrature implementation.

### Layer B — `RESTART_UNLOAD_POSTCOMMIT`, every completed cycle boundary

Timing label:

```text
cN/s5_cycle_complete_post_all_commits_before_c(N+1)/s1
```

The checkpoint must contain every variable the original solver needs to resume
the exact path, including the converged displacement/damage state, committed
damage/history/fatigue/cycle-max arrays, cycle counters, solver continuation
metadata, immutable-parameter reference and code/config identity.

Freeze the functional requirement, not the serialization layout: every cycle
boundary must have an immutable restart-equivalent archived state enabling
cycle N+1 to run without replaying earlier cycles. Prefer static-data
deduplication plus per-cycle mutable restart state if restart equivalence is
preserved. A rolling checkpoint may coexist for crash recovery but cannot
replace immutable archival checkpoints. A strided scheme cannot retain the
at-most-one-cycle guarantee.

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
state_sequence_id,analysis_or_restart,array_file,mesh_sha256,state_sha256,source_kind,
source_checkpoint,parent_checkpoint_sha256,restart_next_cycle,
damage_committed,history_committed,cyclemax_updated,converged,
cycle_complete,next_cycle_not_started,staggered_iterations,
native_history_present,native_psi_present,restart_complete,
code_sha256,config_sha256,file_size_bytes,export_timestamp
```

Also provide `field_schema.csv`, `RUN_PROVENANCE.txt`, replay commands/logs and
`SHA256SUMS.txt`. `field_schema.csv` records field name, native/derived status,
location (node/element/GP/global), shape, dtype, units, component meaning and
derivation when applicable.

## Staged qualification gates

No production replay is allowed until Gates 0–3 pass:

0. **Schema freeze** — Windows identifies the exact solver variables backing
   every required native field and restart field; no placeholder is accepted.
   Freeze native/derived labels, the two canonical timing names, field/file
   manifests, hash rules and the functional restart guarantee. No FEM beyond a
   tiny implementation smoke is authorized.
1. **Restart equivalence** — on one trajectory compare uninterrupted c0→c2
   against c0→c1/s5 then restart→c2. Match c2/s4 and c2/s5 `u`, `d`, native
   history/fatigue, raw/cycle-max psi, reaction/global diagnostics and commit
   counters within frozen tolerances. File readability is insufficient.
2. **Storage/I/O qualification** — archive c1–c10 with the final schema. Report
   compressed/uncompressed bytes, compression, write/read/checksum latency,
   projected total and solver slowdown. Budget at least 1.5 times the measured
   projection; freeze an acceptable I/O-overhead threshold before testing.
3. **Intermediate archival pilot** — prefer U0.13 to c20 or c40. Test random
   archived s5 restarts and one-cycle forward reproduction, plus state timing,
   hashes, bounds and irreversibility.
4. **Production scope** — only after Gates 0–3 pass and separate human
   authorization, select `A_C40_ARCHIVE` or `B_FIRST_DETECT_ARCHIVE`. Only B can
   be called the canonical pre-first-detect archive intended to eliminate
   future c0 replays.

Stop and reply `BLOCKED` if any required native variable cannot be identified,
restart equivalence fails, state timing is ambiguous, the capture hook perturbs
the uninterrupted solution, projected free space is insufficient, I/O overhead
exceeds its frozen limit, or the selected scope is not explicitly authorized.

## Prohibited substitutions

- s5 displacement for s4 displacement, or a later cycle for an earlier state;
- nodal interpolation of element damage as native nodal damage;
- element averaging of GP history as native GP history;
- reconstructed elasticity as observed peak displacement;
- posthoc raw/cycle-max psi inferred from incomplete or current-step state;
- terminal checkpoints used to reconstruct earlier committed states;
- toy-road numerical state used as Hard-5 state;
- any interpolated/reprojected field without preserving its native source.

## Current measured storage evidence

The accepted Request 28 package provides the nearest measured sizes:

- full s4/s5 analysis snapshots: approximately 35.0–36.3 MB each;
- existing terminal checkpoints: approximately 7.8–8.3 MB each.

There are 122 + 83 + 59 = 264 cycles through first detect. Naively retaining
both artifacts each cycle projects approximately 11.3–11.8 GB before logs,
hashes and filesystem overhead. The reviewer requires at least a 1.5x measured
budget, so the present planning envelope is approximately 17.0–17.7 GB, not
14 GB. Replace this estimate with the final-schema size/I/O audit. Static-mesh
deduplication and omission of labelled deterministic convenience fields may
reduce the analysis-snapshot component, but must not remove native state.

## PIDL Experiment Gate

- Mechanism question: none; can the archival implementation preserve exact
  peak semantics and one-cycle restartability?
- Claim changed if success: future state requests up to the approved endpoint
  need not replay from c0 solely due to missing archives.
- Claim changed if failure: none scientifically; archival design remains
  unqualified and production replay stays blocked.
- Cheaper diagnostic first: schema freeze and c1→c2 restart equivalence.
- Minimal output asset: contract, micro-test report, state index and hashes.
- Code/producer alignment: Mac specifies; Windows-FEM implements and runs.
- Success criteria: each staged gate passes before the next is authorized.
- Failure criteria: any stop condition above.
- Registry destination: Windows FEM outbox plus the relevant handover entry.
- Decision: `external review complete; Gate 0 next`; no FEM launch.
