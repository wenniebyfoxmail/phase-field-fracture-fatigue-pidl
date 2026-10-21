# Conditional P1/P2 comparison support

Prepared on 2026-10-21 under **code/document preparation only**. None of the new
tests, scripts, MATLAB functions, network optimization or deployment was run.
The historical runner, FYR sources, baseline results and original source lock
are retained. The separate `implementation_lock.json` describes this revision;
it is a byte identity, not evidence of execution or numerical correctness.

## What the new entry point does

`run_paired_windows.py` calls the shared trial controller directly, bypassing
the generic runner's new-U0-only initialization. It does not perform recovery,
pretraining or implicit resume. It reuses the network construction used by
the E011 frozen-state work (`make_field`), the existing energy/optimizer and
the E036 common-boundary/fresh-residual implementation. It deliberately does
not reuse E011's target-bearing `LocalProblem` or its smoothed damage mapping.
The free-node mapping remains `legacy_nonsmooth`; the declared 251 crack nodes
are fixed by the common problem. Network: float32, 8 x 400, TrainableReLU,
seed 1, original log-energy objective and weight regularizer `1e-5`.

| Arm | Coefficient used in each optimizer block | Acceptance |
|---|---|---|
| P1 | The same `f(old_history)` for the entire physical substep | Fresh final-field trial-history residual, bounds and BC checks |
| P2 | Refresh from the same frozen old history after each block | The same fresh checks, plus `f_solve/f_commit` consistency |

Both use fresh RPROP instances in blocks of 200 updates, at most ten blocks /
2000 updates per substep. A legacy loss plateau is recorded, not used to
accept or stop the substep. Its detector resets at each optimizer block as in
the old fit call. The snapshot is the post-update network at the stopping
decision; the trigger loss was evaluated before that update and is labelled
as such. The first coefficient fixed point is also only a diagnostic.
P1's coefficient difference is recorded but is not an additional fixed-point
condition: imposing it would change the intended frozen-coefficient control.

Save full fields and weights at each completed block, the first plateau, the
first fixed point and the accepted/exhausted endpoint. A failure during a
partial update retains the actual last network and old state. When time has
expired or the objective is invalid, no extra numerical readout is started;
that failure artifact is explicitly unaccepted and may lack final fields.
Earlier acceptance can make the arms' actual update counts differ. Equal-work
comparisons use the intersection of retained update counts, never an assumed
equality between different terminal counts.

## Explicit inputs, no future targets

`window_inputs.py` accepts exactly four cases: `c1`, `c83`, `c20s4`, `c60s4`.
The windows each contain the five actual displacements
`[.02999988,.05999988,.08999988,.11999988,0]`; the endpoints contain only s4.
The common predecessors are c1s0, c82s5, c20s3 and c60s3 respectively. The
source key includes trajectory, nominal Umax, cycle/substep, actual U,
post-commit timing and GP order. No file-number-based state inference occurs.

The manifest is JSON with exactly these top-level keys:

```text
schema: s04_e036_paired_windows_v1
trajectory: explicit source trajectory identity
mesh: {path, sha256}                       # E011 initial_inputs NPZ
common_problem: {path, sha256}             # frozen common_problem_q4.json
cases:
  c1/c83/c20s4/c60s4:
    predecessor: {path, sha256}            # normalized predecessor NPZ
    admission: {path, sha256}              # real native verification evidence
    network: {path, sha256}                # bare existing float32 state_dict
budget:
  updates_per_block: 200
  max_updates_per_step: 2000
  max_outer: 10
  step_wall_seconds: explicit, at most 3600
  total_wall_seconds: explicit, at most 86400
```

Relative paths resolve against the manifest's directory. The mesh NPZ uses
`node_coords` and zero-based `connectivity`. The predecessor NPZ uses nodal
`u`, `v`, `damage`, native `(element,4)` `history`, `active_driver`, `f_commit`,
plus `state_key_json`, `ordered_mesh_sha256_f32_i64`,
`source_checkpoint_sha256`, and `preparation_json`.

Source coordinates retain their original precision for float64 physical
readback and FEM comparison. The established mesh digest alone serializes
coordinates as float32. Network evaluation and optimization still use float32;
casting those rounded coordinates back to float64 is not a native-mesh replay.

`prepare_predecessor.py` can convert an explicitly identified native v7.3
step checkpoint, a complete saved stage0b initial state, or an audited NPZ.
It checks MATLAB's internal state key, block-ordered displacement `[ux;uy]`,
history channels and array ordering, committed damage, load and boundary.
`state0_analysis.mat` alone is insufficient: its damage field cannot supply
missing histories. Conversion writes a fresh NPZ and is **not admission**.
The original archive is never overwritten.

Admission JSON has schema `s04_e036_predecessor_admission_v1`, explicit true
`accepted`, `native_residual_checked`, `checkpoint_readback_verified`, and
matching `state_key`, `predecessor_sha256`, `ordered_mesh_sha256_f32_i64`.
It also binds `{path,sha256}` for `source_checkpoint`,
`native_residual_evidence` and `checkpoint_readback_evidence`. The source
checkpoint must match the conversion's source. An actual admitted package has
not been fabricated in this preparation turn. Missing/unqualified cases are
recorded unavailable; there is no replacement state or recovery run.

P1/P2 start from independent copies of the same predecessor and initial network.
Subsequent states use each arm's own verified history. Thus later steps of a
window measure coupled history propagation, not identical-predecessor solves.
Failure stops that arm; no cross-arm state substitution is available.

## Persistence and continuation

`source/cyclic_persistence.py` writes one bundle containing weights, field
mapping/common problem, old predecessor, final fields, committed history,
both coefficients, state key, provenance and acceptance records. It reloads
with `weights_only=True`, checks exact saved values, reconstructs the network
and common mapping, and repeats the final physical checks using the saved
**old** predecessor. Only then is `completion.json` published.

The next substep uses that returned loaded bundle. A proposal, snapshot or
accepted in-memory result alone cannot advance the window. Failed writes and
failed readbacks remain incomplete; an existing directory cannot be reused.
The exact field replay is intended for the original runtime/device. A later
different-device replay must be treated as unverified if it differs; the code
does not silently relax the equality requirement.

## Independent scoring of saved results

`score_paired_windows.py` reads a completed run and separately admitted F1
targets. It never supplies targets to optimization. It reconstructs saved PIDL
fields and checks each arm's predecessor chain; the first FEM predecessor
must bind the same original checkpoint, while later FEM states must follow
their own verified history and source-checkpoint chain. Missing/rejected F1
states terminate that F1 window's scoring chain. PIDL persistence can still
be checked independently. The native coefficient identity uses absolute
`1e-10`; it does not inherit the PIDL float32 coefficient tolerance.

The separate scoring manifest has this schema:

```text
schema: s04_e036_scoring_v1
training_manifest: {path, sha256}
run_receipt: {path, sha256}
callback_lock: {path, sha256}               # same implementation lock as producer
scorer_sha256: SHA of score_paired_windows.py
q4_geometry_sha256: SHA of run_multicycle_cross_replay.py
targets:
  c1/s1 ... c1/s5, c83/s1 ... c83/s5, c20s4/s4, c60s4/s4:
    snapshot: {path, sha256}
    admission: {path, sha256}
```

Each missing target is explicit `null`. A target NPZ contains nodal `u,v,d`,
`old_damage`, GP `history,active_driver,f_solve,f_commit,old_history,old_active_driver`,
`state_key_json`, `predecessor_key_json`, `ordered_mesh_sha256_f32_i64`, and
`source_checkpoint_sha256,predecessor_checkpoint_sha256`. Its admission schema
is `s04_e036_target_admission_v1`, with explicit true `accepted`,
`native_residual_checked`, `checkpoint_readback_verified`; matching
`snapshot_sha256`, `state_key`, `predecessor_key`, ordered mesh digest; and
bound files for `source_checkpoint`, `predecessor_checkpoint`,
`native_residual_evidence`, `checkpoint_readback_evidence`.

The score is the Q4 lumped-area normalized primitive-field gap
`J=sqrt(mean_area(((u-uF)/.12)^2+((v-vF)/.12)^2+(d-dF)^2)/3)`.
Accepted endpoints retain their actual work counts; equal-update comparisons
use the arms' common completed-block snapshots and remain diagnostics. The
fixed twelve-state aggregate is absent if any pair is missing or unverified;
there is no reduced-denominator result obtained by discarding failed states.
Output is JSON to stdout; source archives are not rewritten. Running the
scorer performs numerical replay and is also deferred in this turn.

## FEM window and readback interfaces

`tools/s04_e036_fem/e036_run_window.m` accepts an explicitly bound native
system and admitted predecessor, applies the declared windows/endpoints,
and uses the original Newton/staggered interfaces plus fresh common-state
acceptance. Its next state comes only from the exact payload returned by
`e036_verify_persisted.m`. Native loading/binary binding, the separate disabled
identity control and producer resource enforcement still need preparation and
review before an execution request. The detailed plan names these outstanding
items; the written MATLAB interfaces have not been executed or syntax-checked.

## Future execution and review

The runner requires `--manifest`, `--authority`, `--out` and an explicitly
selected single CUDA GPU (`CUDA_VISIBLE_DEVICES`, device `cuda:0`). Mac network
optimization is rejected. The authority JSON must be created only after user
approval; it names `schema=s04_e036_execution_authority_v1`, `approved=true`,
the actual `approval_reference`, producer `hostname`, `cuda_visible_devices`,
`manifest_sha256`, `implementation_lock={path,sha256}`, and
`fem_validation={path,sha256}`. That completed validation report must use
`schema=s04_e036_fem_validation_v1`, explicit `accepted=true`, and match
`implementation_lock_sha256`. It summarizes real Stage A evidence; no such
result is generated during preparation. A boolean in a file
does not itself supply human authorization. No such authority is supplied here.

Code uses cooperative wall checks before/after optimizer and residual work.
A future approved launcher must additionally enforce the wall cap externally;
a running native/GPU operation cannot be preempted by a Python time check.
Final diagnostic I/O does not authorize further numerical work. Reserve at
least 20 GiB output space. No retries, D4 probes, LBFGS, changed seed, new
recovery or full-trajectory replay are included in this entry point.

Before execution, review and then run the pending controller, persistence and
input tests; validate the actual producer numerical stack and FEM same-state
checks. See `docs/research/S04/S04-E036/FEM_VALIDATION_PLAN.md` for the proposed
FEM envelope. All test execution and computational budgets remain unapproved
in this turn.
