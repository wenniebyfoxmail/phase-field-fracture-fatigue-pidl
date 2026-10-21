# S04-E036 FEM validation proposal · 2026-10-21

**Historical proposal below is preserved.** On the subsequent user instruction,
Stage A alone was approved with these limits. Attempt `stage_a_20261021_2142`
completed lightweight Python checks but stopped before native computation after
the isolated-snapshot command failed and its recorded zero-start preparation
window elapsed. See [Stage A result](STAGE_A_RESULT_20261022.md). Stage B and
PIDL execution remain unapproved; no statement below is a new launch authority.

This is a proposed execution envelope, not execution authority. This turn only
prepares code and this plan: **zero tests, zero NN optimization, zero MATLAB/FEM
execution, zero deployment and zero remote operations**. No prior task's budget
is inherited. The older `experiment.md` and `VALIDATION.md` remain historical
records; their completed-check statements do not cover these new files.

The decision is whether the optional common-state acceptance and history update
can be used in an actual PIDL–FEM comparison. The three distinct outcomes are:
the MATLAB adapter works; both implementations evaluate the same discrete
state consistently; paired solved states show an identifiable field-gap change.
The first two alone do not establish the third.

## Frozen identities and inputs before any computation

- Proposed FEM producer: `citpc12-ssh`, in a fresh task-owned isolated source
  and output directory. This is a proposal, not permission to connect. Future
  approval must name the actual producer and budget; no host fallback is
  included. Verify availability and process ownership before consuming it.
- Base reviewed worktree: `b84a0c0af02c2ce60ef238d2b9b14499f2fbee43`.
  The eventual run must bind the **new reviewed commit**, including the newly
  authored, unexecuted predecessor-window harness and readback helper, rather than claim this older
  commit covers them. Do not update `source_lock.json` to imply unperformed checks.
- The overlay builder targets FEM source
  `862992a60edc7f59335365beacb5c71fc8592a7a`; its two input hashes are in
  `tools/s04_e036_fem/build_overlay.py:14–16`. At future execution record actual
  MATLAB version/platform, source commit and dirty status, `which -all` results
  for both assembly functions and the E036 helpers, actual function-handle
  bindings, and the paths/hashes/build provenance of the loaded MEX binaries.
  A source hash alone does not identify the binary MATLAB executes.
- Use the locked ordered Q4 mesh, four GP order, quadrature weights, material,
  prescribed displacement/damage DOFs and common problem JSON. Save the actual
  native arrays used, not merely the filename of the JSON. Keep the same
  `nodal_box_kkt` policy: joint `4e-4`, mechanical `1e-6`, irreversibility
  tolerance `1e-8`, active-bound tolerance `1e-10`, FEM history identity `1e-10`.
- A predecessor needs a checked admission JSON binding its source checkpoint
  SHA, ordered mesh digest, and full physical state key: trajectory/Umax,
  cycle, substep, actual imposed displacement, timing after history commit,
  node/GP order and native fields/history. Use a native step checkpoint or an
  explicitly audited NPZ. Do not infer substep from a cycle-end checkpoint.
- Required predecessors are the existing U0 accepted state for c1s1, c82s5
  for c83s1, c20s3 for c20s4, and c60s3 for c60s4. Their complete availability
  and numerical qualification are **not established** by this plan. A missing,
  differently timed or invalid predecessor is `unavailable`; do not substitute
  another state, reconstruct unseen histories, run a new U0 recovery, or replay
  the entire history to create it. Such work would require a new proposal.

## Stage A — actual MATLAB and same-state validation (proposed cap: 3 hours)

1. **Bindings and small checks.** On the authorized isolated snapshot, inspect
   the actual bindings above, run MATLAB `checkcode` for the helpers/harness and
   the existing 17-case `e036_selftest`. Execute the new readback helper's
   mismatch cases, including missing step metadata, wrong cycle, wrong history,
   proposal-only output and a cycle-end checkpoint offered as a step checkpoint.
   These are software checks, not native-physics results.
2. **Disabled-mode identity.** From the same admitted c1s1 predecessor and
   configuration, perform exactly two one-substep native controls: option absent
   versus `enabled=false`. Compare final u/d, all four history channels, native
   stop information and saved checkpoint arrays. Exact equality is required on
   the same installation and thread setting. Investigate any mismatch before
   enabling the adapter. Each control has 30 minutes and `max_outer=1500`;
   no new recovery or history replay is included. Use the original overlay's
   native control path for this identity check, not the new enabled-only
   `e036_run_window` entry. An isolated explicit-predecessor invocation of that
   original control still needs preparation/review; the current fresh-U0 runner
   cannot be used as a shortcut because it starts a recovery solve. This is a
   remaining Stage A implementation item, not a check already supplied by the
   new window entry.
3. **Real frozen states, no field optimization.** Evaluate at up to four
   predeclared archived states: c1s4, c20s4, c60s4 and c83s4, each with its
   correct predecessor. The archived final field is only a common evaluation
   input and is not automatically an accepted reference. Both sides evaluate
   the same u/v/d and predecessor arrays. Save full native nodal Ru/Rd, their
   free-DOF and box-projected forms, GP raw energy, active driver, accumulated
   history and f, before any spatial averaging. Confirm exact mesh/DOF/order
   and policy identity first. Compare float64 assembly using element/GP arrays;
   for this cross-implementation float64 check use per-channel
   `max_abs_difference <= 1e-10 + 1e-8 * max_abs_reference`, reviewed and fixed
   before execution. The absolute term prevents division by a zero channel;
   the relative term allows different double-precision assembly summation
   orders. This is a proposed software-equivalence tolerance, not a field
   accuracy or convergence threshold. Do not reuse the production PIDL
   float32-history tolerance as a nodal residual tolerance. A miss stops
   promotion and is investigated; do not relax it after seeing the result.
   Each state has 10 minutes, no Newton solve or NN optimization.
4. **Acceptance/rejection transaction checks.** Use the transaction harness
   with explicit saved fixture fields to exercise one accepted proposal and a
   deliberately infeasible rejected candidate; assert unchanged input history,
   a single accepted assignment, and no assignment on rejection. Preserve the
   rejected input and reason. This is an instrumented control, not evidence
   that a real native solve converged or failed. For actual native acceptance,
   repeat the readback in Stage B's first accepted physical substep. For actual
   rejection during Stage B, preserve before/after checkpoint identity and
   explicit attempted/committed step keys. Do not induce an additional native
   failure or claim receipt-only proof of non-commit.

Stage A maximum allocation: bindings/small checks 30 min, two disabled native
controls 60 min, four frozen-field comparisons 40 min, transaction/readback
checks 30 min, preparation/serialization overhead 20 min. These add to 180 min;
they are ceilings chosen to stop an unexpectedly expensive check, not measured
runtime predictions. If a required input is unavailable, do not spend its
allocation on a replacement solve. Any Stage A failure stops Stage B admission.

## Stage B — twelve physical steps and one independent tightening check

This stage needs separate execution approval, all required inputs, review and
actual validation of the newly authored predecessor harness, and the Stage A
result. The proposed FEM cap is
**7 wall hours**, with no more than four compute threads and one native solve
at a time.

| Unit | States and start | Maximum solves | Per-solve cap |
|---|---|---:|---:|
| Early window | c1s1–c1s5 from the admitted existing U0 state | 5 | 30 min |
| Late conditional window | c83s1–c83s5 from admitted c82s5 | 5 | 30 min |
| Independent endpoints | c20s4 from c20s3; c60s4 from c60s3 | 2 | 30 min |
| Reference sensitivity | c83s4 once, with the **same main-run predecessor**, joint `4e-6` and mechanical `1e-8` | 1 | 60 min |

Main native solves retain `max_outer=1500` and the locked native inner solver
settings. A watchdog enforces the wall-time cap externally in the future
authorized harness; an iteration limit alone is not a wall-time guarantee.
No line search, seed, tolerance, maximum iteration or solver-path changes may
be introduced to rescue a failed state. Twelve main steps at 30 min plus one
tightening check at 60 min give the 420 min ceiling, including their I/O. Any
overhead consumes the same cap; it is not added beyond seven hours.

Within a window, each accepted final history becomes that arm's next input. A
failed/unavailable step stops that window immediately; no reference-history
replacement or continuation through an unaccepted state. The other predeclared
independent window/endpoints may proceed only if the failure was scientific,
not a common implementation/input problem. c83 is a conditional local window,
not a c1-to-c83 prediction. The tightening comparison is eligible only after
the ordinary c83s4 reference is accepted; missing/failed c83s4 means skip it,
not select an easier replacement. A tighter result cannot replace or repair
a failed main reference. Report its u/v/d, history, residual and main field-gap
changes as reference numerical sensitivity, not as a new truth label.

Every accepted step must retain the proposal, exact native step checkpoint and
readback result **before the runner overwrites `step_checkpoint.mat` at the next
step**. Bind the immutable retained copies to a manifest. A verified readback
establishes serialization identity; fresh residual checks establish numerical
acceptance. Neither establishes real-road validity. Also save
`f_last_inner_return` beside fresh FEM `f_solve` and `f_commit`; the first is the
relevant field when asking what the original inner assembly last returned.

## Readback helper and its exact limit

The new helper is `tools/s04_e036_fem/e036_verify_persisted.m`:

```matlab
report = e036_verify_persisted(proposal_file, native_step_checkpoint_file, ...
    struct('cycle',83,'substep',4,'n_step',5));
```

It only loads and compares saved arrays; it performs no assembly, solve,
assignment to solver state, save or overwrite. It requires the native **step**
schema: `displ`, `p_field`, `p_field_old`, `history_vars_old`,
`SOL_CYCL_VAR.n_cycle`, and `i_step_completed`. This schema comes from the
audited source's `solve_fatigue_fracture.m:326–340`; the pinned runner enables
step saves at `run_SENS_hard_recovery_native_q4_capture.m:129–131`.
The cycle-end save at solver lines 628–637 lacks `i_step_completed` and is
deliberately rejected. No current local E036 accepted native checkpoint exists
to verify this helper against. It is prepared source, **not executed or
syntax-checked** this turn.

The helper compares exact serialized fields with the accepted proposal,
checks explicit step/version identity and the exact named policy, and directly
recomputes `A_new=A_old+max(P_new-P_old,0)` and f from the saved GP channels.
It also checks raw/history-channel and solve/commit-history consistency.
The current-output slot-1 raw check is specific to the audited
`fem_live/at1_penalty_fatigue.f90:94–99`, whose SHA-256 is
`ea7e0bb9def96678115627014f53500c1081a5e892554e1120629a5bfd1702e6`:
that source explicitly assigns current undegraded energy to slot 1. It is
not applied to the old predecessor's slot 1 and must not be generalized to
older E011 kernels. Future MEX admission must establish this source binding.
The saved new active driver is an input to this algebra check; without the
mesh/GP interpolation this helper does not establish that P came from u/d.
It does not independently recompute residuals. It does not certify a rejection
path, detect every possible later overwrite, or infer a missing predecessor.
Those claims need the run manifest, protected copies and transaction evidence.

## Newly authored enabled-only native window entry

`tools/s04_e036_fem/e036_run_window.m` is now written but **not executed,
checkcode-checked or numerically validated**. It reuses the E011 c1-arm
predecessor structure and the original native `step.pre_iter_update`,
`newton_raphson`, and `stag.post_iter_update` interfaces. It then calls
`e036_native_candidate` for the common final-state check. It has no new
recovery solve, future-target input, native disabled arm, or implicit resume.

```matlab
result = e036_run_window(sys, native_eq, native_pf, par, predecessor, ...
    request, policy, budget, authority, fresh_output_directory);
```

The caller must first load and bind the actual native system/functions and the
admitted predecessor. The helper does not fabricate that admission or serve as
the source-file/NPZ importer. `request` contains only `cycle`, `substeps` and
`role`: main c1/c83 complete five-step windows, main c20/c60 step 4, or the
separately authorized c83 step-4 tightening check. It checks actual cumulative
`par.step.uy_increment` against the five locked displacements, the full native
node/GP support against the bound arrays, hard-crack and displacement masks,
material, predecessor version/load/history and exact named acceptance policy.

`par` explicitly contains `solver`, `stag`, `step`, and
`regularize_pf_newton=true`. Native inner parameters are the verified interface
fields `max_iter_displ`, `tol_displ`, `max_iter_pf`, `tol_p_field`; no guessed
parameter names or implicit defaults. The prospective displacement/phase inner
ceilings are 500/250, and the outer cap is at most 1500. The actual reviewed
values must also match `authority.solver/stag`. The ordinary inner tolerances
are `1e-6`/`4e-4`; the separate tightening call uses `1e-8`/`4e-6`.

`budget` contains a shared caller-created `total_timer` and
`total_wall_seconds` for the whole Stage B, plus `window_wall_seconds`,
`step_wall_seconds`, `max_outer`, and `max_threads`. Do not reset the total
timer between windows. The authority record binds the exact request, solver,
policy, admitted predecessor identity and support arrays, actual native handle
names, reviewed source/input identities, Windows producer identity, thread
controls and an external watchdog identity. Those supplied records are
preconditions; setting a boolean is not human execution authorization or proof
of a runtime preflight.

Each substep rebuilds the predecessor stiffness before the native predictor
(the predictor itself includes one CHOLMOD solve), freezes the old history
through all native iterations, and retains the last inner f separately from
fresh f. It saves a proposal and native **field-schema** checkpoint in a new
step directory, then calls `[report, loaded]=e036_verify_persisted(...)`.
The second return is the very checkpoint payload that was just verified;
only that payload may advance the in-memory accepted state once. These window
checkpoints contain the six native fields needed for readback, with explicit
cycle/substep metadata; they do not claim to contain the original solver's
complete cycle-monitor/event/resume metadata.

Readback hashes proposal/checkpoint bytes before loading and again after its
checks. The completion record binds those hashes and the saved readback-file
hash; all three are checked again after writing the temporary completion and
immediately before publishing it. Later consumers must verify the recorded
hashes rather than trust a completion filename. This does not make multiple
files an atomic operating-system transaction; the task-owned directory and
future verified-loader contract remain necessary.

The new local `e036_sha256_file.m` is an explicit dependency, using MATLAB's
JVM `java.security.MessageDigest` and binary chunked reads. No actual
`phase_field.audit.sha256_file` implementation was available in the inspected
local source (only older callers), so that unverified dependency is not assumed.
The new helper has not been executed. Future Stage A must include `checkcode`,
known-byte SHA comparison, missing/read-error behavior and simulated artifact
drift between readback and completion publication.

Failures stop the window and preserve its predecessor, last returned candidate,
last native assembly input (labelled separately when an inner call did not
return), fresh audit/proposal, trace and committed version. There is no retry.
Time is checked around native assemblies and solves; a single long native call
can only be interrupted by the separately approved external watchdog. Further
required preparation remains: admitted inputs and a verified native-system
loader, the original-control disabled-identity invocation, transaction fixtures,
and the actual producer watchdog/thread/storage integration. Written interfaces
are not a claim that these dependencies or MATLAB execution already work.

## Proposed resource envelope, storage and stopping rules

| Resource | Stage A | Stage B | Combined maximum if both are approved |
|---|---:|---:|---:|
| FEM/native wall time including checks and I/O | 3 h | 7 h | 10 h |
| Threads / concurrent native solves | 4 / 1 | 4 / 1 | at most 4 CPU threads, one solve |
| Conservative thread-hours | 12 | 28 | 40 |
| Native transition solves | 2 disabled controls | 12 main + 1 tightening | 15 |
| Frozen-field assembly-only states | up to 4 | none additional | 4 |
| Additional NN optimization / GPU allocation | 0 | 0 | 0 |

These are proposed upper limits, not elapsed-time estimates and not presently
approved consumption. Future PIDL P1/P2 optimization is a separate envelope
specified in the addendum below. No 48 GPU-hour recommendation or older
permission is carried forward here.
The four-thread ceiling applies across MATLAB, MEX/BLAS and any concurrent
Python assembly comparison; do not run two four-thread processes together.
Record the actual runtime thread controls. If the native backend's thread cap
cannot be enforced or verified, stop for a revised resource proposal.

For the declared mesh (86,756 nodes, 86,408 Q4 elements, four GP), one float64
nodal scalar is about 0.66 MiB; one GP scalar is about 2.64 MiB; a four-channel
history is about 10.55 MiB. A proposal containing old/solve/commit histories,
u/d/raw/residuals, plus its retained native checkpoint is approximately
60–100 MiB before MAT/HDF5 metadata and duplication. This is array-count
arithmetic, not a measured MAT file size. Reserving 16 records at 150 MiB gives
about 2.4 GiB; four same-state comparison exports at 100 MiB give about 0.4 GiB.
Budget **5 GiB new task output** for records, inputs, manifests and compact logs,
and require **10 GiB free space above the isolated source/build installation**.
Existing build/runtime storage must be measured separately before approval;
this plan does not estimate a new MATLAB/MEX installation. Do not dump full
fields every staggered iteration. Keep compact iteration traces and final/failure
arrays. Stop before a write would cross the 5 GiB task limit; no automatic
cleanup of old archives is authorized.

Stop on an unverified function/MEX binding, unavailable predecessor, state-key
or mesh mismatch, nonfinite values, invalid boundary/history identity, failed
native or common-state acceptance, exhausted per-state/total time, storage cap,
or resource conflict. Preserve the failure once; no automatic retry, larger
budget, replacement state, new recovery, full-trajectory reconstruction or
producer fallback. A lost connection creates an unknown execution state;
verify the exact process/output before any restart. Routine zero-start
inspection may be repeated only within a future approved envelope; it must
not launch a solve. This preparation turn authorizes none of those operations.

## Evidence needed for the final statement

- After Stage A only: the reviewed adapter can execute and evaluate matching
  frozen states consistently within the declared numerical comparison.
- After accepted Stage B references and separately authorized PIDL comparison:
  report per-state primitive-field gap and its components, equal-work P1/P2
  comparison, reference sensitivity and failures. Preserve the comparison's
  conditional-window scope.
- No stage permits attributing all change to update timing: common crack BC,
  penalties, final residual acceptance and work spent are separate changes.
  Until the paired results exist, the correct meeting statement remains:
  “The timing change is implemented, but its effect on the PIDL–FEM field gap
  has not yet been demonstrated.”

## Addendum — separate PIDL comparison proposal, not authorized

The proposed PIDL comparison is at most **24 GPU-hours on one GPU**, covering
24 physical substeps: P1 and P2 on each of the twelve predeclared main states.
Each substep has a 3,600-second wall limit and at most 2,000 RPROP updates,
organized as at most ten 200-update blocks. Enforce the per-step wall limit,
update limit and total wall limit together; time spent on observers, residual
assembly, snapshots, persistence and readback consumes the same envelope.
Unused allocation from a failed/unavailable state cannot fund retries or a
larger allocation to another state. These caps are prospective stopping limits,
not measured estimates or a promise that a state will converge within an hour.

The eventual approval must bind an explicitly available GPU producer and one
GPU ID, the reviewed source commit and input manifest, storage allocation,
and stop rules. **Do not start PIDL optimization unless the required FEM
validation has succeeded and the needed FEM reference/predecessor has been
admitted.** Frozen-field assembly comparisons in Stage A are not permission
for NN optimization. The new proposal excludes D4 optimization/expression
probes, LBFGS, additional seeds, new U0 recovery and complete-trajectory replay.
The FEM 10 wall-hour ceiling and PIDL 24 GPU-hour ceiling are separate proposed
resources; neither has been approved or consumed by this preparation turn.
