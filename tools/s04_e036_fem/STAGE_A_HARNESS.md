# Stage A producer harness · prepared 2026-10-21

**Current configuration update, 2026-10-22:** subsequent explicit user authority
replaced the expired cumulative deadline with a hash-bound authority file and
configurable independent job/arm guards. The current interface is documented
in [Stage B harness, authority section](STAGE_B_HARNESS.md). The old timings and
unapproved-stage statements below describe their historical attempts, not the
latest authority. None of this source preparation establishes an execution pass.

Subsequent same-budget continuation staged the snapshot and code, but its first
PowerShell wrapper exited before a watchdog attempt or MATLAB/build output was
recorded. The producer's effective policy was Restricted; the exact child error
was not captured. No execution-policy change or relaunch occurred. See
`docs/research/S04/S04-E036/STAGE_A_CONTINUATION_20261022.md`. The two new drivers
remain prepared source; neither has MATLAB execution evidence.

**Status update, 2026-10-22:** the root executor stopped this attempt after
the 1,200-second zero-start preflight limit was exceeded. The source-snapshot
command failed before any native computation. No MEX compilation, MATLAB
checkcode/selftest, native assembly, disabled solve or real frozen-state
comparison was started. These helpers remain prepared/unexecuted. This
stopped attempt must not be resumed or retried under the old launch authority.

The original Stage A approval was **3 wall hours total, at most four CPU
threads, one native solve at a time**. B and PIDL remain unapproved. These
new files were written and read statically only by the preparation agent;
they have not been executed, checked by MATLAB, or numerically validated.
The root executor owns the producer operation and one shared clock/watchdog.

The `FEM_VALIDATION_PLAN.md` original proposal remains historical. This entry
prepares its remaining explicit-predecessor disabled control and fixture
checks. No new recovery, full trajectory, retry, input reconstruction, or
replacement state is permitted.

## Inputs and runtime bindings

The reusable U0 is the saved **E011 derived U0**, source
`67942510c38c420c9ebc343e88b781a018cd1c7b`, at
`local_archive/experiments/S04-E011/runs/pf_s04e011_c1_commit_20261016_v4_r1/retrieved/output/c1_commit/common_initial.mat`.
Its SHA-256 is
`59a0f81368d0c46a698f94fdfcb32158e96361714d7547f00deed996d4a7c181`.
It contains common u/d/lower/raw/history, original predictor `initial_KK`,
mesh and free DOFs; it does not contain `sys`. Do not call it an original
Stage0b checkpoint. The paired snapshots use `request28_snapshot`, with
explicit cycle/substep and post-commit flags.

The root's local inventory is
`local_archive/pidl_cyclic_audit_20261021/e036_stage_a_local_data_inventory_20261021/data_manifest.json`.
It records the existing producer copies, hashes, and all four s3/s4 pairs.
Verify the staged bytes against it. The mesh SHA is
`0e6db55abde5880200e2ce01bfe1a7fbb0d4a827362c15afbadbece111fdcb75`.

Before any MATLAB invocation, bind the actual reviewed code, source and loaded
MEX paths/hashes/build provenance, thread controls, external watchdog, and
fresh output root. `e036_stage_a_context` expects those paths already on the
explicitly verified MATLAB path; it does not modify the search path. Its
`binary_checks` includes MATLAB functions as well as binaries. Record `which
-all` separately. A listed source and binary together do not prove that the
binary was built from that source. In particular, the current-output slot-1
raw check belongs to kernel `ea7e0bb9...`; the old E011 kernel `70b01f0b...`
left that output channel unassigned. Do not patch or relabel returned history
to bypass an incompatible binary.

The producer's actual `newton_raphson` was observed to declare seven outputs.
The disabled control checks that signature and retains the original body's
seven-output calls. The older local six-output source is not its authority.

## Invocation interfaces

All operations share the same `budget.total_timer=tic` token, created once by
the root driver. `total_wall_seconds<=10800`, integer `max_threads<=4`, and
nonempty `watchdog_id` are mandatory. Cooperative checks cannot interrupt a
single MEX/CHOLMOD call; external process timeout is required. Set native
thread environment and MATLAB thread cap before code execution, then verify
them in the producer receipt. The helpers do not create worker pools.

```matlab
% Root driver owns approval, source/MEX binding and one overall watchdog.
[sys,par,common,binding] = e036_stage_a_context(cfg,options,budget);

% Run only when binding.u0_admitted is true. Each arm executes once.
identity = e036_stage_a_disabled_pair(sys,par,common,binding, ...
    overlay_solver_path,overlay_solver_sha256,budget,new_identity_directory);

% Four predeclared independent historical pairs, no optimization.
native = e036_stage_a_export_frozen(sys,binding,pair,budget,new_mat_path);

% Mock-only: original 17 cases plus 11 new serialization/transaction cases.
small = e036_stage_a_selftest(new_selftest_directory);
```

`cfg` comes from the actual native locked five-step configuration. Required
fields: `requested_n_step, loading, discretization, u_max, R,
max_iter_displacement, max_iter_phase, max_iter_staggered`. The constructor
requires Umax=.12, phase max250, outer max1500, displacement max1..500 and
checks the actual generated displacements against the locked five loads.
The chosen displacement maximum must match the approved actual configuration;
the allowed range is not permission to increase a frozen solver setting.

`options` requires `execution_approved,producer_hostname,source_root,
mesh_file,mesh_sha256,common_file,common_sha256,source_checks,binary_checks,
thread_controls_verified,provenance`. Source entries contain `path,sha256`;
runtime binding entries contain `name,path,sha256`. `provenance` carries the
actual run/code/build receipt identifiers, not inferred provenance.

Context reconstruction copies the known mesh/material/BC/native `System`
setup and retains the archived predictor tangent. Accessing native stiffness
indices performs one initial assembly, but no linear/Newton solve. It never
calls `init_fatigue_fracture` or an old runner, both of which can initialize
recovery/resume behavior. It then evaluates the existing U0 with the current
adapter. A numerical U0 miss returns `u0_admitted=false`; disabled controls
must be marked unavailable and cannot consume a replacement recovery. A
binding/schema/nonfinite error is an implementation/input failure to retain
and investigate, not permission to continue solving.

The disabled pair takes the exact text between the unique native predictor
statement and `STEP POST-PROCESSING` marker in the hash-bound overlay solver.
It writes that segment and its source receipt, executes it without numerical
edits, and excludes the outer cycle/step loops and postprocessing. Each arm
has c1s1 only, max1500 outer iterations, <=1800s; pair <=3600s including I/O.
It resets the original cached tangent and the same stored U0 for each arm.
It compares exact final fields, all four history channels, native staggered
table/stop values, raw energy, last inner history, and tangent. Native
acceptance is preserved; this check does not claim fresh common-state
acceptance. Each saved step checkpoint contains the six native field/key
variables, with explicit metadata that it is not a full native resume file.
Failure of the first arm prevents launching the second; neither arm retries.

For disabled controls the root must set
`budget.arm_deadline_dir=<Root>/logs/<Label>_arms` and
`budget.watchdog_id=<Label>`, exactly matching `stage_a_watchdog.ps1`.
Do not create the directory beforehand. The pair creates it exclusively,
then publishes immutable `{absent,false}_started.json` records before each
arm's native work, with schema `e036-stage-a-arm-v1`, MATLAB PID, watchdog
ID, mode, UTC start/deadline and 1800 seconds. After all that arm's output
I/O and clock checks, it publishes the corresponding `_finished.json` with
UTC finish. Both publications use a temporary file then rename. The watchdog
must enforce each unfinished arm's deadline, check finished timestamps and
immutable record hashes, and reject missing/mismatched/out-of-order records.
This supplements the pair's 3600-second/global 10800-second bounds; it is
needed because cooperative checks cannot stop a blocking native call.

`pair` contains `cycle,target_path,target_sha256,predecessor_path,
predecessor_sha256,trajectory`, with trajectory `S04_E011_FEM_Q4_C120`.
Only c1/c20/c60/c83 s4 and the same cycle's archived s3 are accepted. Frozen
export takes one equilibrium and one phase assembly, each with the same
saved old lower/history and actual final field, under <=600s including I/O.
The MAT schema is `e036_frozen_native_v1`: root nodes/cells, blocked `[X;Y]`
u/d, old_lower/history, raw/Ru/Rd/trial_history, traction, active/fixed DOFs,
fixed values, quadrature/material and physical/provenance JSON strings.
Cells and DOFs are one-based; MAT v7.3 reverses HDF5 dimensions. Its companion
`compare_frozen_states.py` owns the independent float64 comparison. Nothing
in this export labels the archived target a newly accepted reference.

The new selftest checks the SHA-256 `abc` known answer, one mock accepted
assignment after readback, zero assignments for an infeasible mock candidate,
cycle-end/missing step metadata, wrong cycle, mismatched history,
proposal-only files, wrong version, unapproved policy, a self-consistent
receipt with wrong history algebra, and rejected receipt misuse. These checks
exercise software guard behavior only. Root should first `checkcode` the new
files and record the actual results; the prepared case count is not a pass.

## 2026-10-22 prepare_03 file-hash repair (prepared only)

The producer reached MATLAB but stopped before mock/build/native work because
the old `fread` loop's final `ferror` reported `At end-of-file.`. The replacement
`e036_sha256_file` uses a Java FileChannel and the new `e036_sha256_stream`
core: only a read count of -1 means EOF; read exceptions, zero progress,
inconsistent counts, premature EOF and growth fail without publishing a digest.
It retains the existing JVM dependency and checks byte count, opened-file size,
and path size/mtime before returning. These metadata checks are a drift screen,
not an immutable snapshot guarantee: same-size concurrent rewrites may evade
them. Existing expected-digest comparisons and publication-time rechecks remain
necessary.

The preparation driver now runs a separate `e036_sha256_selftest` before the
unchanged 28-case transaction suite. Its 15 cases cover empty/abc/binary/million-a
known answers, four one-MiB boundary/multi-block payloads checked against a
one-shot payload digest, missing/non-file paths, short reads, a simulated
exception after a partial read, zero progress, truncation and growth. The fault
cases use the stream core's reader callback; they do not claim a real OS I/O
fault or concurrent-writer validation. New receipts are recorded under
`hash_selftest/` and `prepare_result.hash_selftest`. These sources have only been
edited and statically reviewed locally; producer execution is still required.
