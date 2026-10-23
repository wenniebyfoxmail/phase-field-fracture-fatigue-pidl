# Prospective producer adapter — prepared, not authorized or launched

This directory now contains the single release algorithm and its producer
adapter. Nothing here edits the resident queue, deploys files, submits a job,
loads a future FEM target, or changes source `68291a0a`. The execution template
has `approved: false`; all unknown source-terminal paths/hashes remain absent
until the actual binding step. This preparation is not an execution receipt.

The owner may use it only if the predeclared `d4_c1s2_continue_01` finishes with
a verified **failed float64 C0 terminal endpoint**, and the current fixed-f
operator still identifies blocked feasible damage directions. Success of the
existing continuation makes this repair unnecessary. Technical abort, missing
terminal artifacts or unknown outcome cannot be replaced by an earlier snapshot.

## Files

| File | Role |
|---|---|
| `DESIGN.md` | Mathematical meaning, acceptance and limits of the selected method |
| `release.py` | One transactional node-step/raw-preimage release, with exact rollback |
| `contract.py` | Pure standard-library source/clock/binding validation and frozen constants |
| `bind_source.py` | Pure-I/O discovery and hashing of the actual completed source endpoint |
| `release_config.json` | Frozen c1s2 algorithm and one optional post-release physical continuation |
| `execution_authority.template.json` | Deliberately invalid/unapproved template; never used as authority |
| `run_release.py` | Producer-only entry; original supervisor and actual authority required |

No new supervisor is implemented. Reuse `tools/s04_e036/gpu_watchdog.py` from
the frozen base. Its existing detached supervision, GPU occupancy checks,
ownership checks, process cleanup and 24-hour per-job watchdog remain intact.
There is no cumulative resource limit and no automatic retry.

## Actual late binding, once the source is complete

The binding utility takes the **real source-job directory**, not an inferred
checkpoint path. It discovers the output directory from the actual supervisor
argv, requires the original worker `finished.json` and matching outcome, and
finds exactly one published `lbfgs_final`/float64/C0 completion. It records the
SHA-256 of the actual completion, bundle, fields and network files.

It also binds and cross-checks:

- Original execution/supervisor authority, supervisor attempt/start/finish,
  worker attempt/finish/outcome and their command lines;
- Original physics manifest, original C0 matrix-source manifest and the actual
  `68291a0a` source snapshot/independent implementation lock;
- Source hostname/GPU, zero history commits, scientific stop reason, published
  work counts, source start/end clocks and charged GPU seconds;
- Exact state identity and the clean original producer exit. Source technical
  failure or unknown-reservation records reject binding.

The allowed scientific stops are exactly those already emitted by the frozen
physical L-BFGS: fixed-f stagnation or a bounded line-search stop restoring its
previous state. A new stop reason must be interpreted explicitly by the owner;
it is not automatically added to this list.

The utility has **no torch import, scientific computation or launch call**:

```bash
python3 tools/s04_e036/constraint_release_preparation/bind_source.py \
  --source-job "$E036_SOURCE_JOB" \
  --out "$E036_SOURCE_BINDING"
```

The owner sets those task-specific variables to verified actual producer paths.
`E036_SOURCE_BINDING` must be a fresh file. This command is for the actual
producer filesystem containing the original absolute paths; it does not silently
rewrite a partial local retrieval into a substitute source. It returns a binding
receipt with `approved: false`, `executed: false`. This command has **not** been
run during preparation because the terminal source is still pending.

## Package and authority, without changing the frozen producer

Create a **new** task-owned job directory only after the owner makes the
conditional execution decision. Build its code from the exact original
61-file base snapshot; add only these locked overlay files:

```text
tools/s04_e036/constraint_release_preparation/release.py
tools/s04_e036/constraint_release_preparation/contract.py
tools/s04_e036/constraint_release_preparation/bind_source.py
tools/s04_e036/constraint_release_preparation/run_release.py
tools/s04_e036/constraint_release_preparation/release_config.json
```

Do not copy the current whole worktree into the original source directory. The
adapter requires each base-file hash to equal the real source job's independent
lock, and the new lock's file set to be exactly the base plus these five files.
Use a new `source_snapshot.json` and implementation lock with all actual bytes.
Record the actual committed release-overlay SHA as `release_source_commit`, and
the original SHA as `base_source_commit`; the mixed snapshot is therefore
explicit. The original production files are never overwritten. Documentation
and the unapproved template need not enter the runtime snapshot.

The owner resolves the execution template's remaining fields from actual
artifacts and the existing user authority. Bind `source_binding`, `release_config`,
Stage A reuse references, `owner_scope`, current GPU-5 UUID and the new independent
implementation lock. Set the actual fresh-job command in a new original-format
`s04_e036_gpu_supervisor_v2` authority, label `optimization_probe`, GPU 5,
86400 seconds, cumulative ceiling null. `entry_sha256` is the actual new
`run_release.py` hash. The template itself cannot pass validation.

The worker argv is:

```text
/usr/bin/python3 <new-code>/tools/s04_e036/constraint_release_preparation/run_release.py
  --manifest <the-actual-original-physics-manifest>
  --source-binding <actual-late-binding.json>
  --config <new-code>/tools/s04_e036/constraint_release_preparation/release_config.json
  --authority <new-job>/execution_authority.json
  --supervisor-authority <new-job>/supervisor_authority.json
  --out <new-job>/output
  --device cuda:0
```

These angle-bracket names document required bindings; they are not executable
paths or fabricated metadata. The actual supervisor argv remains its existing
`python3 gpu_watchdog.py --authority <new-supervisor-authority>` form. Preserve
`CUDA_VISIBLE_DEVICES=5` and `CUBLAS_WORKSPACE_CONFIG=:4096:8`. The worker validates
its exact argv against the current real supervisor attempt, checks GPU UUID and
requires the new output to be absent. Direct unsupervised worker invocation is
rejected. Scheduling stays with root; this directory never inserts a queue job.

## What the adapter restores and runs

The existing `run_mechanism_matrix.load_endpoint` is deliberately **not** used:
it only admits a float32 `first_2000` matrix endpoint. Instead this adapter
reuses `score_mechanism_matrix.verify_snapshot` for the four bound terminal
artifacts and exact network/native-field replay. That verifier does not call a
FEM target loader. Importing its definitions does not read target data.

The restored state includes every network parameter, original native old
damage/history/active driver, exact f_solve, dtype, case, common problem and
all actual work counters. The saved source's terminal stop/objective are checked
against its worker outcome. The source clock is preserved as provenance; the
new method gets its own supervised clock measured from the actual new supervisor
attempt. Old charged work is never reset or relabeled as new work.

The adapter computes the saved-f nodal phase force on the restored actual field.
If no blocked feasible direction remains, it records `ineligible`, leaves the
source state intact and ends without calling `attempt_release`. Otherwise:

1. Call exactly one release transaction. Persist the real node proposal/raw
   preimage and the per-proxy-step physical readbacks.
2. If release fails, verify exact restoration to the original source network and
   f_solve. Retain that source state; no physical continuation is attempted.
3. If release succeeds and already passes the original fresh acceptance, stop.
4. Otherwise call the original `lbfgs_phase(..., target=None)` **once**, with a
   new physical optimizer memory. It retains the existing numerical stopping
   rules and fatigue refresh schedule.
5. If that continuation fails scientifically, preserve its actual rejected
   endpoint/trace but restore the verified release candidate's weights and
   f_solve. On an exception/timeout, perform the same restoration and propagate
   the technical failure; no new physical readout is attempted after a deadline.

All snapshots retain arm C0 but have explicit new-method provenance and release
stage/output paths. The outer finished receipt is labeled
`nodal_damage_raw_preimage_release_v1`; it cannot be mistaken for an original
matrix or continuation result. The terminal retained snapshot distinguishes
original source, accepted release candidate and qualified physical continuation.
History commits stay zero throughout. The physical solver does not consume
FEM-target fields or fitted witness parameters.

Proxy steps and closures are recorded separately in `proxy_work`; the existing
engine counters retain original plus new physical work. Proposal evaluations,
readbacks and persisted replay work are visible in the trace and snapshots.
No iteration count is presented as equivalent across node, proxy and physical
solvers.

## Local validation and present status

Only AST syntax, JSON/constant equality, authority-template rejection state and
direct metadata compatibility are checked on Mac. No model import/forward,
native energy assembly, optimization, SSH, deployment or launch is performed.
There is no new test ladder. Actual source binding, saved-network replay,
blocked-direction admission and scientific outcome are still unperformed.

This adapter completes preparation, not the research comparison. Successful
release would show that the measured clamp barrier can be crossed by the same
C0 network; it would not establish F1 agreement, global expressiveness or
trajectory reproduction. The original numerical criteria remain unchanged.
