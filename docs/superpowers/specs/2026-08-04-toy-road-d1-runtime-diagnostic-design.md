# Toy-Road D1 Diagnostic-Only Runtime Probe Design v1.1

Date: 2026-08-04

Status: v1.1 review-correction specification and implementation-plan
documentation only.
This document does not authorize implementation, MATLAB execution, FEM
execution, or a new P0 production authorization.

Revision: v1.1 fixes the authorization-field test, thread-setting provenance,
validator filename, complete-versus-partial artifact lifecycle, and MATLAB
unit-test authorization boundary identified in review of v1.

## Decision And Scope

D0 accepted the failed `969d3420` attempt as a zero-execution quarantine
record. It proves that the producer did not start, the production output root
was not created, and FEM cycles remained zero. D0 cannot identify the failed
runtime predicate because the production bridge wrote its measurement receipt
only after all checks passed and all failures converged on one `localRequire`
location.

D1 is a diagnostic-only runtime probe. It measures the same MATLAB runtime,
path precedence, rebuilt MEX overlay, SuiteSparse binary and thread/environment
identity without entering the producer. Its only claim is runtime-diagnostic
evidence. A D1 PASS cannot authorize P0, and a D1 FAIL cannot modify
expectations or trigger a retry.

The family remains blocked:

```text
P0    blocked_pending_D1_diagnosis
P0R   blocked
T1    blocked
T2    blocked
T3    blocked
```

This is a production-entrypoint runtime qualification and observability issue,
not a FEM numerical-convergence or physical-model failure.

## Immutable Boundaries

1. D1 must not call or indirectly reach `main_toy_road_family_case`, recovery,
   `System`, Newton, cycle 1 or any FEM solve. Its cycle count is exactly zero.
2. D1 must not read, validate, copy, create, consume or rename a production
   authorization or `.consumed` marker.
3. The complete `969d3420` quarantine remains read-only. D1 may hash and cite
   the old execution lock but may not write within the quarantine or failed
   production roots.
4. D1 uses fresh diagnostic evidence, work, TEMP, TMP, preference and cache
   roots. It has no production output-root parameter and must reject a path
   equal to or nested beneath any quarantined production root.
5. D1 uses the same MATLAB executable, rebuilt `initial.mexw64`, AMOR,
   AT1-history-fatigue, `cholmod2`, SuiteSparse, MATLAB release/update and
   BLAS/LAPACK identity recorded by the old execution lock. Thread settings do
   not come from that lock. They are independently fixed to
   `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1` and
   `MKL_DYNAMIC=FALSE` from the sealed production launcher
   `producer_handoffs/toy_road_p0_repeatability_20260803/launch_toy_road_family_case.ps1`
   at source commit `eeda43d9faef01622731e877c5048a78f3c5003a`, SHA-256
   `03d415ad96a484e9a98565fced0d6b8d2f90ffb781d48192a445d19ed5d5e728`.
6. Exactly one D1 MATLAB process may be launched after implementation, review
   and resealing. Specification and plan work launch no MATLAB process.
7. D1 PASS remains `diagnostic_only_non_authorizing`; D1 FAIL remains terminal
   until separately reviewed. Neither state invokes, enables or schedules P0.

## Architecture

D1 uses a separate PowerShell launcher and a separate MATLAB probe. It does not
add a diagnostic branch to the production launcher or production runtime
bridge. Separation makes the absence of the producer entrypoint statically and
dynamically auditable.

The components are:

- `new_toy_road_d1_diagnostic_lock.ps1`: derives one immutable diagnostic lock
  from the quarantined execution lock and writes a transformation manifest.
- `launch_toy_road_runtime_diagnostic.ps1`: validates the sealed source,
  diagnostic lock and fresh roots; creates launch provenance before MATLAB;
  starts exactly one diagnostic process; and records process/output/cycle
  absence after it exits.
- `run_toy_road_runtime_diagnostic.m`: creates the diagnostic receipt before
  evaluating runtime predicates, persists every predicate result, and records
  structured exception details on failure.
- `toy_road_d1_protocol.py`: validates lock derivation,
  receipt chronology, predicate completeness, hashes and non-authorizing
  terminal evidence. It has no production launch operation.

The production files `launch_toy_road_family_case.ps1`,
`run_toy_road_runtime_bridge.m`, `main_toy_road_family_case.m` and the
quarantined execution artifacts are not execution dependencies of D1.

## Diagnostic Lock Derivation

The source artifact is the exact quarantined `P0_parent.execution-lock.json`.
The derivation tool reads only that lock, never the authorization or consumed
marker. It writes these fresh artifacts with create-new semantics:

```text
D1_DIAGNOSTIC_LOCK.json
D1_LOCK_TRANSFORMATION.json
```

`D1_DIAGNOSTIC_LOCK.json` has
`schema_version=toy_road_runtime_diagnostic_lock_v1`,
`authorization_scope=diagnostic_only_non_authorizing`, and
`producer_entrypoint_authorized=false`. It retains the MATLAB and binary
runtime expectations from the old execution lock byte-for-value after
canonical normalization. It omits production role, authorization artifact
references, production output root, dynamic predecessor evidence and producer
entrypoint fields. The four thread settings are added from the separately
sealed launcher source identified above, never attributed to the old lock.

The lock validator permits the required `authorization_scope` field. It
precisely forbids `authorization_path`, `authorization_id`,
`authorization_sha256`, `production_authorization_artifact` and
`consumed_marker_path`, plus any path ending in `.consumed`. It must not use a
substring-level ban on the word `authorization`.

Only these path changes are legal:

- the old rebuilt-MEX overlay prefix becomes one fresh D1 overlay prefix;
- writable work, TEMP, TMP, preference and cache roots become fresh D1 roots;
- the diagnostic evidence root is newly introduced.

No MATLAB, MEX, SuiteSparse, compiler, release/update, BLAS/LAPACK or
non-relocated path identity may change. The four fixed thread values must equal
the sealed-launcher values exactly.

`D1_LOCK_TRANSFORMATION.json` records:

- source execution-lock path and SHA-256;
- complete source-lock canonical SHA-256;
- diagnostic-lock path and SHA-256;
- transformation schema and ordered replacement list;
- every old/new path pair and replacement reason;
- unchanged-field digest before and after transformation;
- thread-setting source path, source commit, source-file SHA-256 and four exact
  name/value pairs;
- `authorization_artifact_read=false` and
  `production_output_root_present=false`.

The validator reconstructs the transformation independently and rejects any
undeclared change.

## Launch Provenance Before MATLAB

Before process creation, the launcher writes with create-new semantics:

```text
D1_EXACT_BATCH_COMMAND.txt
D1_LAUNCH_PROVENANCE.json
D1_PROCESS_BEFORE.json
```

The exact batch command is UTF-8 without BOM and is the exact string passed to
`matlab.exe -batch`. The launch provenance records:

- source commit and clean-source result;
- launcher path and SHA-256;
- probe path and SHA-256;
- diagnostic-lock and transformation-manifest SHA-256;
- MATLAB executable path and SHA-256;
- exact ordered `addpath(...,'-begin')` construction;
- complete environment variable names and values used by the child;
- thread-setting provenance path, source commit and source-file SHA-256;
- overlay source/destination paths and hashes;
- all fresh diagnostic roots;
- exact batch-command SHA-256;
- `authorization_path_present=false`;
- `production_output_parameter_present=false`.

`D1_PROCESS_BEFORE.json` records MATLAB/FEM processes by executable name and
PID. The launcher excludes its own PowerShell PID and does not inspect command
lines using solver-name regular expressions. Any pre-existing MATLAB/FEM
process fails closed before MATLAB starts.

## Predicate Receipt

The MATLAB probe creates `D1_RUNTIME_DIAGNOSTIC.json` immediately on entry with
status `IN_PROGRESS`, an empty ordered predicate array and
`producer_entrypoint_authorized=false`. Every completed predicate is persisted
before the next predicate begins. Persistence uses create-new for the initial
file and atomic same-directory replace for later versions. Each replacement is
first written as `.D1_RUNTIME_DIAGNOSTIC.json.<uuid>.tmp`, flushed and then
renamed over the receipt. A successful replace removes its temporary file.
Any temporary file left by interruption is immutable crash evidence: it is
listed by name and SHA-256 in recovery evidence and is never silently deleted
or promoted. Duplicate initial receipt creation fails closed.

Every predicate row contains exactly:

```text
ordinal
name
expected
measured_raw
measured_normalized
pass
measured_at_utc
```

The required predicate order is:

```text
diagnostic_lock_schema
diagnostic_authorization_scope
producer_entrypoint_not_authorized
matlab_path_length
matlab_path_prefix
matlab_release
matlab_update
matlab_version
matlab_computer
matlab_executable_sha256
matlab_blas
matlab_lapack
binary_initial_resolved
binary_initial_readable
binary_initial_sha256
binary_AMOR_resolved
binary_AMOR_readable
binary_AMOR_sha256
binary_AT1_HISTORY_FATIGUE_resolved
binary_AT1_HISTORY_FATIGUE_readable
binary_AT1_HISTORY_FATIGUE_sha256
binary_cholmod2_resolved
binary_cholmod2_readable
binary_cholmod2_sha256
```

The path section records the complete raw `path`, the complete normalized
actual path array, expected path array, one comparison record per expected
index, extra actual entries, and `first_path_mismatch_index` using one-based
MATLAB indexing or `null` when equal.

For each of `initial`, `AMOR`, `AT1_HISTORY_FATIGUE` and `cholmod2`, the binary
section records the complete `which -all` result, normalized candidate paths,
selected path, selected-file existence/readability, expected SHA-256, measured
SHA-256 and pass status. Missing or unreadable binaries are recorded as
measurements before the predicate fails.

## Failure Semantics

The first failed predicate stops further runtime predicates. Before MATLAB
returns a nonzero exit, the receipt is updated to `FAIL` and records:

- `first_failed_predicate`;
- MATLAB exception identifier;
- exception message;
- structured stack entries containing file, name and line;
- extended exception report;
- completed-predicate count;
- `producer_invocation_count=0` and `fem_cycle_count=0`.

An unexpected exception outside a named predicate uses
`first_failed_predicate=diagnostic_internal_error`. Partial receipt, process
termination before finalization and malformed/duplicate receipt are terminal
FAIL states. The launcher does not repair, delete or rerun them.

## Terminal Evidence

After the MATLAB process exits normally or returns a catchable error, the
launcher writes:

```text
D1_PROCESS_AFTER.json
D1_TERMINAL.json
D1_SHA256SUMS.txt
```

The terminal record includes before/after MATLAB and FEM process counts,
MATLAB exit code, diagnostic receipt status, production output-root absence,
quarantine hash rechecks, `producer_invocation_count=0`,
`fem_cycle_count=0`, `authorization_consumed=false`, and
`automatic_retry_performed=false`.

The terminal validator accepts a diagnostic PASS or diagnostic FAIL as a
complete D1 evidence package only when all non-production invariants hold. It
never maps D1 status to a P0 launch decision. A crash or partial package is
recorded as D1 incomplete/failed and remains non-authorizing.

The launcher has an outermost `try/catch/finally` after evidence-root
reservation. A launcher exception before `D1_TERMINAL.json` creates
`D1_LAUNCHER_RECOVERY.json` with create-new semantics, recording the launcher
exception type/message/stack, PowerShell exit stage, files observed with
SHA-256, outstanding atomic temporary files, child PID/exit status when known,
and explicit unknown values when a postcondition cannot be measured. An
uncatchable PowerShell host termination may leave only the already persisted
subset and captured host exit log; validation classifies it as partial without
inventing a recovery or terminal record.

## Artifact Schema

A complete terminal PASS or FAIL D1 evidence root contains exactly these ten
files:

```text
D1_DIAGNOSTIC_LOCK.json
D1_LOCK_TRANSFORMATION.json
D1_EXACT_BATCH_COMMAND.txt
D1_LAUNCH_PROVENANCE.json
D1_PROCESS_BEFORE.json
D1_RUNTIME_DIAGNOSTIC.json
D1_PROCESS_AFTER.json
D1_TERMINAL.json
D1_SHA256SUMS.txt
MATLAB_STDOUT_STDERR.txt
```

`D1_SHA256SUMS.txt` contains exactly nine sorted entries and validates the
other nine files; it never lists or validates itself.

A crash or partial D1 root contains a declared subset of the ten files above
and may additionally contain `D1_LAUNCHER_RECOVERY.json` plus immutable
`.D1_RUNTIME_DIAGNOSTIC.json.<uuid>.tmp` files. The recovery record inventories
every observed regular or temporary file and its SHA-256. A partial package is
never padded to ten files and cannot be reported as terminal PASS or FAIL.

No file is named as a production authorization, production launch receipt,
cycle shard, checkpoint or terminal FEM package. No `.consumed` file is
permitted anywhere under the D1 root.

## Test Matrix

The implementation must pass these tests before D1 execution is considered:

| Test | Required result |
|---|---|
| Static launcher/probe call scan | No producer, recovery, solver, cycle or production wrapper call |
| Batch command scan | Exactly one diagnostic probe call; no producer call |
| Authorization isolation | Authorization and `.consumed` paths are rejected and never opened |
| Lock transformation | Only declared fresh overlay/root substitutions; unchanged digest equal |
| Old quarantine protection | All old evidence hashes unchanged before and after fixtures |
| Initial receipt | `IN_PROGRESS` exists before first runtime predicate |
| Partial predicate failure | Completed rows persist; first failure is named |
| Crash fixture | Declared subset plus recovery/temp inventory; no padding or retry |
| Duplicate receipt | Create-new rejection; existing bytes unchanged |
| Path mismatch | Full paths and first mismatching index persisted |
| Binary missing | `which -all`, selected path and unreadable state persisted |
| Binary hash mismatch | Expected/measured hash and binary predicate persisted |
| MATLAB identity mismatch | Exact identity predicate named and measured |
| Dynamic process adapter | One diagnostic invocation, zero producer invocations, zero cycles |
| Production-output absence | No production output root before or after |
| PASS non-authorization | PASS receipt rejected as production authorization/predecessor evidence |
| FAIL non-mutation | No expectation change, retry or second process launch |
| Package validation | Hashes, chronology, schemas and non-production invariants verified |

Tests must cover both the PowerShell launcher boundary and the real MATLAB
probe logic. A simulated adapter alone is insufficient for the per-predicate
receipt behavior. Implementation authorization does not authorize MATLAB.
After the MATLAB source and tests are written and pass static review, a
separate `test_only_non_authorizing_matlab_unit_test` authorization is required.
It may invoke only the named unit-test file directly; it must reject and never
run the real D1 launcher, producer or FEM. Failure consumes that test
authorization and does not permit an automatic rerun.

## Explicit Non-Production Proof

D1 cannot authorize or enter production only if all of these independent
proofs pass:

1. The D1 lock scope is exactly `diagnostic_only_non_authorizing`, has
   `producer_entrypoint_authorized=false`, and contains no authorization path.
2. The launcher parameter surface has no production authorization or output
   parameter and rejects production-scope locks.
3. Static source and generated-batch scans contain exactly one D1 probe call
   and no producer/solver/recovery/cycle entrypoint.
4. The D1 MATLAB probe has no dynamic dispatch (`eval`, `feval`,
   `str2func`, `run`) and no function handle supplied from external input.
5. Dynamic test instrumentation records one diagnostic invocation, zero
   producer invocations and zero FEM cycles.
6. The production launcher rejects D1 lock, receipt and terminal schemas.
7. D1 terminal validation always emits `production_authorized=false` and has
   no operation that launches or schedules P0.

Any failed proof blocks D1 execution and leaves all five family cases blocked.

## Commit And Authorization Sequence

The work is separated into immutable commits:

1. this D1 v1.1 specification commit;
2. a D1 v1.1 implementation-plan commit;
3. later source/test implementation commits followed by one clean sealed
   source commit;
4. only after review, one D1 execution and a separate evidence-only commit.

Diagnostic evidence must never be added to the sealed source commit. Sealing
and review do not authorize MATLAB by themselves. The single D1 execution
requires a separate explicit human decision after the implementation and
sealed source are reviewed. A future P0 execution requires a new, separately
issued one-shot production authorization after D1 evidence is reviewed.
