# Toy-Road D1 Diagnostic-Only Runtime Probe Implementation Plan v1

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, test and seal a non-authorizing D1 runtime probe that identifies the exact MATLAB/path/binary runtime predicate that blocked P0, while proving zero producer invocations and zero FEM cycles.

**Architecture:** Add a diagnostic-only lock derivation/validator, PowerShell launcher and MATLAB probe beside the existing producer handoff. The D1 path reuses immutable runtime expectations from the quarantined execution lock but has its own schema, fresh roots and evidence lifecycle; it has no production authorization or output parameter. Implementation ends at a reviewed sealed source commit, and a later explicitly authorized one-shot D1 creates a separate evidence-only commit.

**Tech Stack:** MATLAB R2025b Update 5, PowerShell 5.1, Python 3 with pytest, canonical JSON, SHA-256, Git, existing GRIPHFiTH runtime binaries and SuiteSparse/CHOLMOD runtime.

## Global Constraints

- Approved design: `docs/superpowers/specs/2026-08-04-toy-road-d1-runtime-diagnostic-design.md` at commit `9232785134751aaa09ef0cf4e2ea0a02ad2c3b23`.
- D1 is diagnostic only. It must never call or indirectly reach `main_toy_road_family_case`, recovery, `System`, Newton, cycle 1 or a FEM solve.
- D1 must not read, validate, copy, create or consume a production authorization or `.consumed` marker.
- The complete `969d3420` quarantine is immutable and read-only. Tests use copies or synthetic fixtures, never modify the original.
- D1 uses fresh diagnostic evidence/work/TEMP/TMP/preference/cache/overlay roots and has no production output-root parameter.
- Runtime expectations retain the same MATLAB executable, release/update/version/computer, BLAS/LAPACK, rebuilt `initial.mexw64`, AMOR, AT1-history-fatigue, `cholmod2`, SuiteSparse and thread/environment identity.
- Lock transformation may replace only the explicitly declared overlay and fresh writable diagnostic roots. It must record old/new lock SHA-256 and an independently verified unchanged-field digest.
- Exact batch command, environment, path construction, launcher/probe hashes and source commit are persisted before MATLAB starts.
- Every runtime predicate persists `name`, `expected`, `measured_raw`, `measured_normalized` and `pass` before the next predicate.
- D1 PASS cannot authorize or launch P0. D1 FAIL cannot mutate expectations or automatically retry.
- Terminal evidence records pre/post process counts, production-output absence, `producer_invocation_count=0`, `fem_cycle_count=0` and unchanged quarantine hashes.
- Spec, plan, source implementation/seal and D1 evidence are separate commits.
- This specification/plan documentation phase starts no MATLAB process. During
  later Tasks 1-6, MATLAB may be used only for separately authorized unit-test
  processes that are statically proven unable to enter producer/FEM code;
  Task 7 is the only real D1 runtime probe and remains forbidden until a later
  explicit human authorization is recorded.
- Only one MATLAB/FEM experiment may run at a time. No launcher may stop an existing process automatically.

## File Structure

Create or modify only these implementation assets after this plan is approved:

- `producer_handoffs/toy_road_p0_repeatability_20260803/new_toy_road_d1_diagnostic_lock.ps1`: thin sealed entrypoint for diagnostic lock derivation; accepts an old execution lock and fresh D1 root, never an authorization path.
- `producer_handoffs/toy_road_p0_repeatability_20260803/toy_road_d1_protocol.py`: canonical lock transformation, schema validation, terminal-package validation and CLI.
- `producer_handoffs/toy_road_p0_repeatability_20260803/run_toy_road_runtime_diagnostic.m`: incremental runtime measurement and structured failure receipt.
- `producer_handoffs/toy_road_p0_repeatability_20260803/launch_toy_road_runtime_diagnostic.ps1`: pre-MATLAB provenance, isolated environment, one diagnostic process and post-process evidence.
- `producer_handoffs/toy_road_p0_repeatability_20260803/invoke_toy_road_d1_test_process_adapter.ps1`: non-MATLAB process double used only by PowerShell tests.
- `producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadD1RuntimeDiagnosticTest.m`: real MATLAB probe receipt tests with controlled runtime adapters.
- `producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadD1LauncherTest.ps1`: launcher, batch, process and no-production tests.
- `tests/test_toy_road_d1_protocol.py`: canonical transformation, validator and static-call tests.
- `producer_handoffs/toy_road_p0_repeatability_20260803/README.md`: D1 usage and non-authorizing boundary.
- `producer_handoffs/toy_road_p0_repeatability_20260803/SOURCE_MANIFEST.json`: sealed executable-source identities.
- `producer_handoffs/toy_road_p0_repeatability_20260803/SHA256SUMS.txt`: handoff hashes.

---

### Task 1: Canonical Diagnostic Lock And Transformation Validator

**Files:**
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/toy_road_d1_protocol.py`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/new_toy_road_d1_diagnostic_lock.ps1`
- Create: `tests/test_toy_road_d1_protocol.py`

**Interfaces:**
- Consumes: quarantined execution-lock JSON, one absent D1 root, explicit old-overlay/new-overlay mapping and fresh writable diagnostic roots.
- Produces: `D1_DIAGNOSTIC_LOCK.json` with schema `toy_road_runtime_diagnostic_lock_v1` and `D1_LOCK_TRANSFORMATION.json` with independently reproducible SHA-256 fields.
- Python API: `derive_diagnostic_lock(source_lock: dict, relocation: dict) -> tuple[dict, dict]`, `validate_diagnostic_lock(source_lock: dict, diagnostic_lock: dict, transformation: dict) -> None`, and CLI commands `--derive-lock` and `--validate-lock`.

- [ ] **Step 1: Write failing canonical transformation tests**

Add fixtures with one production lock and explicit overlay/writable-root replacements. Assert:

```python
diagnostic["schema_version"] == "toy_road_runtime_diagnostic_lock_v1"
diagnostic["authorization_scope"] == "diagnostic_only_non_authorizing"
diagnostic["producer_entrypoint_authorized"] is False
"authorization" not in json.dumps(diagnostic).lower()
"production_authorized" not in json.dumps(diagnostic)
transformation["authorization_artifact_read"] is False
transformation["production_output_root_present"] is False
transformation["source_execution_lock_sha256"] == sha256(source_bytes)
transformation["diagnostic_lock_sha256"] == sha256(diagnostic_bytes)
transformation["unchanged_fields_sha256_before"] == transformation["unchanged_fields_sha256_after"]
```

Parametrize undeclared changes to MATLAB identity, binary hashes, thread values,
non-overlay paths and source-lock digest; each must raise `D1ProtocolError`.
Verify a relocation targeting the quarantine, failed production root, or a
non-absent D1 root is rejected.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
py -3 -m pytest tests/test_toy_road_d1_protocol.py -q
```

Expected: collection/import failure because `toy_road_d1_protocol.py` and its
interfaces do not exist.

- [ ] **Step 3: Implement canonical derivation and validation**

Use sorted-key compact UTF-8 JSON with no BOM/newline. Deep-copy the allowed
runtime/environment fields, remove all production-role/authorization/output
fields, apply only declared path replacements, and calculate both unchanged
digests from canonical projections that exclude the declared replacements.
Write outputs using exclusive create. The PowerShell wrapper accepts no
authorization argument and delegates canonical emission to the approved Python
executable after checking its path and SHA-256.

- [ ] **Step 4: Add fail-closed filesystem tests**

Prove duplicate output creation leaves existing bytes unchanged, source lock is
opened read-only, and no `.consumed` or authorization-shaped file is created.
Patch the test fixture's source lock after derivation and require validation to
fail on the source SHA mismatch.

- [ ] **Step 5: Run Task 1 tests and commit**

Run:

```powershell
py -3 -m pytest tests/test_toy_road_d1_protocol.py -q
git diff --check
```

Expected: all D1 protocol tests pass and no whitespace errors.

Commit:

```powershell
git add tests/test_toy_road_d1_protocol.py producer_handoffs/toy_road_p0_repeatability_20260803/toy_road_d1_protocol.py producer_handoffs/toy_road_p0_repeatability_20260803/new_toy_road_d1_diagnostic_lock.ps1
git commit -m "feat: derive non-authorizing D1 runtime lock"
```

---

### Task 2: Incremental MATLAB Predicate Receipt

**Files:**
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/run_toy_road_runtime_diagnostic.m`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadD1RuntimeDiagnosticTest.m`

**Interfaces:**
- Consumes: diagnostic-lock path, initially absent receipt path and an optional sealed test-only measurement adapter accepted only under MATLAB unit-test scope.
- Produces: one incrementally persisted `D1_RUNTIME_DIAGNOSTIC.json` with ordered predicates, full path/binary diagnostics and structured terminal exception fields.
- MATLAB API: `run_toy_road_runtime_diagnostic(diagnosticLockPath, receiptPath)` for sealed D1, with test measurement injection isolated in a package-private helper that cannot be selected from the production command line.

- [ ] **Step 1: Write failing initial/duplicate receipt tests**

Assert that the first observable write is:

```matlab
receipt.schema_version = 'toy_road_runtime_diagnostic_v1';
receipt.status = 'IN_PROGRESS';
receipt.authorization_scope = 'diagnostic_only_non_authorizing';
receipt.producer_entrypoint_authorized = false;
receipt.predicates = struct([]);
receipt.producer_invocation_count = 0;
receipt.fem_cycle_count = 0;
```

Precreate the receipt with sentinel bytes and verify duplicate invocation fails
without changing those bytes.

- [ ] **Step 2: Run focused MATLAB tests and verify RED**

Run MATLAB unit tests only; do not run the real diagnostic launcher:

```powershell
matlab -batch "r=testsuite('producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadD1RuntimeDiagnosticTest.m');assertSuccess(run(r));"
```

Expected: tests fail because the D1 probe does not exist. Confirm the test suite
contains no producer/FEM call before invoking MATLAB.

- [ ] **Step 3: Implement append-before-next-predicate persistence**

Create the initial receipt using Java `CREATE_NEW`. For every predicate, measure
raw data, normalize separately, append exactly one row with ordinal/name/
expected/measured_raw/measured_normalized/pass/timestamp, then atomically replace
the receipt in the same directory before continuing. Stop at the first failed
predicate.

- [ ] **Step 4: Add path mismatch and binary hash mismatch tests**

Use controlled measurement fixtures to assert:

- full raw and normalized paths are retained;
- every expected prefix index has a comparison row;
- `first_path_mismatch_index` is one-based and stable;
- each binary stores complete `which -all`, selected path, readability and hash;
- missing/unreadable and hash-mismatch predicates persist expected/measured data.

- [ ] **Step 5: Add partial/crash/structured exception tests**

Inject failures after selected predicate ordinals and assert completed rows
remain. Require `first_failed_predicate`, identifier, message, stack entries and
extended report. An unclassified fixture exception must become
`diagnostic_internal_error`. Assert `producer_invocation_count=0` and
`fem_cycle_count=0` in every terminal state.

- [ ] **Step 6: Add static dynamic-dispatch prohibitions**

The Python test suite reads the MATLAB source and rejects `eval`, `evalin`,
`feval`, `str2func`, `run(`, function handles supplied by JSON, and all producer,
recovery, solver, `System`, Newton and cycle entrypoints.

- [ ] **Step 7: Run Task 2 tests and commit**

Run:

```powershell
matlab -batch "r=testsuite('producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadD1RuntimeDiagnosticTest.m');assertSuccess(run(r));"
py -3 -m pytest tests/test_toy_road_d1_protocol.py -q
git diff --check
```

Expected: all focused MATLAB and Python D1 tests pass; no FEM process or cycle
artifact is created.

Commit:

```powershell
git add producer_handoffs/toy_road_p0_repeatability_20260803/run_toy_road_runtime_diagnostic.m producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadD1RuntimeDiagnosticTest.m tests/test_toy_road_d1_protocol.py
git commit -m "feat: record incremental D1 runtime predicates"
```

---

### Task 3: Diagnostic-Only PowerShell Launcher

**Files:**
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/launch_toy_road_runtime_diagnostic.ps1`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/invoke_toy_road_d1_test_process_adapter.ps1`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadD1LauncherTest.ps1`
- Modify: `tests/test_toy_road_d1_protocol.py`

**Interfaces:**
- Consumes: sealed source root/commit, diagnostic lock and transformation manifest, absent diagnostic roots, approved Python/MATLAB executable paths and hashes, and test adapter arguments accepted only under `-TestOnlyNonAuthorizing`.
- Produces: prelaunch batch/provenance/process files, captured stdout/stderr, post-process/terminal files and sorted SHA-256 package.
- Does not accept: production authorization, `.consumed`, role, predecessor, resume, checkpoint or production output-root parameters.

- [ ] **Step 1: Write failing parameter-surface and static-call tests**

Assert the launcher has no production authorization/output/resume parameter,
contains no producer/solver/recovery/cycle call, and generates a batch with
exactly one `run_toy_road_runtime_diagnostic(...)` call. Assert the adapter
rejects a batch containing `main_toy_road_family_case` or more than one probe.

- [ ] **Step 2: Run PowerShell and Python tests and verify RED**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadD1LauncherTest.ps1
py -3 -m pytest tests/test_toy_road_d1_protocol.py -q
```

Expected: fail because the launcher and adapter do not exist.

- [ ] **Step 3: Implement pre-MATLAB provenance**

Before process launch, write with exclusive create:

```text
D1_EXACT_BATCH_COMMAND.txt
D1_LAUNCH_PROVENANCE.json
D1_PROCESS_BEFORE.json
```

Record source HEAD/clean status, source-manifest verification, launcher/probe/
lock/transformation/MATLAB hashes, exact ordered path commands, all child
environment values, overlay source/destination, fresh roots and exact batch
SHA-256. Capture the exact UTF-8 batch bytes that are passed to `-batch`.

- [ ] **Step 4: Implement safe process and path gates**

Inventory processes by executable/process name, exclude current PowerShell
`$PID`, and do not search command lines with solver-name regexes. Reject any
existing MATLAB/FEM process without terminating it. Reject reparse-point chains,
non-absent roots, quarantine descendants and production-output-shaped paths.
Create only fresh D1 overlay and writable roots.

- [ ] **Step 5: Implement one-process terminal evidence**

Capture combined MATLAB stdout/stderr without truncation. After process exit,
write `D1_PROCESS_AFTER.json`, validate zero producer/cycles and production
output absence, rehash quarantine files, then write `D1_TERMINAL.json` and
`D1_SHA256SUMS.txt`. A PASS or FAIL diagnostic receipt completes D1 evidence;
partial/crash states remain non-authorizing failures. Never retry.

- [ ] **Step 6: Test partial/crash/duplicate/path/binary outcomes through adapter**

The adapter records `diagnostic_invocation_count=1`,
`producer_invocation_count=0`, and `fem_cycle_count=0`. Exercise successful,
failed, partial, crash and duplicate-receipt fixtures. Assert one process launch
maximum, no automatic mutation/retry and exact old-quarantine hashes before and
after.

- [ ] **Step 7: Run Task 3 tests and commit**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadD1LauncherTest.ps1
py -3 -m pytest tests/test_toy_road_d1_protocol.py -q
git diff --check
```

Expected: launcher/adapter tests pass without starting MATLAB and record zero
producer invocations/cycles.

Commit:

```powershell
git add producer_handoffs/toy_road_p0_repeatability_20260803/launch_toy_road_runtime_diagnostic.ps1 producer_handoffs/toy_road_p0_repeatability_20260803/invoke_toy_road_d1_test_process_adapter.ps1 producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadD1LauncherTest.ps1 tests/test_toy_road_d1_protocol.py
git commit -m "feat: add fail-closed D1 diagnostic launcher"
```

---

### Task 4: Cross-Boundary Non-Production Proof And Terminal Validator

**Files:**
- Modify: `producer_handoffs/toy_road_p0_repeatability_20260803/toy_road_d1_protocol.py`
- Modify: `producer_handoffs/toy_road_p0_repeatability_20260803/toy_road_protocol.py`
- Modify: `tests/test_toy_road_d1_protocol.py`
- Modify: `tests/test_toy_road_p0_protocol.py`
- Modify: `producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadLauncherTest.ps1`

**Interfaces:**
- Consumes: complete D1 package or one D1 schema presented to a production validator/launcher.
- Produces: `validate_d1_package(root: Path) -> dict` for diagnostic evidence and explicit rejection of all D1 schemas by production admission.

- [ ] **Step 1: Write failing D1 package and production-rejection tests**

Build synthetic complete PASS and FAIL packages with canonical hashes. Require
both to validate only as diagnostic evidence. Pass D1 lock, runtime receipt and
terminal records to existing production validators and require rejection.

- [ ] **Step 2: Verify RED**

Run:

```powershell
py -3 -m pytest tests/test_toy_road_d1_protocol.py tests/test_toy_road_p0_protocol.py -q
powershell -NoProfile -ExecutionPolicy Bypass -File producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadLauncherTest.ps1
```

Expected: D1 package validator is absent and production does not yet explicitly
reject D1 schemas.

- [ ] **Step 3: Implement package chronology and non-production validation**

Validate create order, hashes, lock transformation, exact batch hash, process
counts, quarantine rehashes, no `.consumed`, production-output absence, zero
producer/cycles and no retry. Return only:

```python
{
    "status": "D1_DIAGNOSTIC_EVIDENCE_ACCEPTED",
    "diagnostic_result": "PASS" | "FAIL",
    "production_authorized": False,
}
```

- [ ] **Step 4: Harden production rejection**

Reject `toy_road_runtime_diagnostic_lock_v1`,
`toy_road_runtime_diagnostic_v1` and D1 terminal records at every production
lock/measurement/predecessor/authorization boundary. Do not add any conversion
from D1 PASS to production PASS.

- [ ] **Step 5: Add source-graph proof**

Parse MATLAB and PowerShell sources for direct calls and forbidden dynamic
dispatch. Verify the generated fixture batch has exactly one diagnostic probe,
and that the D1 files have no dependency edge to producer, solver, recovery or
cycle code. Verify production launch files do not import or invoke the D1
launcher.

- [ ] **Step 6: Run Task 4 tests and commit**

Run:

```powershell
py -3 -m pytest tests/test_toy_road_d1_protocol.py tests/test_toy_road_p0_protocol.py -q
powershell -NoProfile -ExecutionPolicy Bypass -File producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadLauncherTest.ps1
git diff --check
```

Commit:

```powershell
git add producer_handoffs/toy_road_p0_repeatability_20260803/toy_road_d1_protocol.py producer_handoffs/toy_road_p0_repeatability_20260803/toy_road_protocol.py tests/test_toy_road_d1_protocol.py tests/test_toy_road_p0_protocol.py producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadLauncherTest.ps1
git commit -m "test: prove D1 cannot enter production"
```

---

### Task 5: Handoff Documentation And Source Identities

**Files:**
- Modify: `producer_handoffs/toy_road_p0_repeatability_20260803/README.md`
- Modify: `producer_handoffs/toy_road_p0_repeatability_20260803/SOURCE_MANIFEST.json`
- Modify: `producer_handoffs/toy_road_p0_repeatability_20260803/SHA256SUMS.txt`
- Modify: `tests/test_toy_road_fem_handoff.py`

**Interfaces:**
- Consumes: all reviewed D1 executable/test files from Tasks 1-4.
- Produces: documented D1 artifact schema, exact invocation boundary and updated source/hash manifests.

- [ ] **Step 1: Write failing manifest and README contract tests**

Require every new executable D1 source in `SOURCE_MANIFEST.json` with exact
SHA-256, every handoff file in sorted `SHA256SUMS.txt`, and README text that
states diagnostic-only scope, zero cycles, no production authorization,
one-shot/no-retry behavior and the ten artifact names.

- [ ] **Step 2: Verify RED**

Run:

```powershell
py -3 -m pytest tests/test_toy_road_fem_handoff.py -q
```

Expected: missing D1 manifest/hash/documentation assertions fail.

- [ ] **Step 3: Update README and regenerate hashes deterministically**

Document the derivation command, launcher parameter surface, artifact schema,
terminal interpretation and explicit statement that D1 PASS does not unblock
P0. Regenerate source and handoff SHA-256 using LF-preserving bytes. Do not add
any D1 runtime evidence to the handoff.

- [ ] **Step 4: Run Task 5 tests and commit**

Run:

```powershell
py -3 -m pytest tests/test_toy_road_fem_handoff.py -q
git diff --check
```

Commit:

```powershell
git add producer_handoffs/toy_road_p0_repeatability_20260803/README.md producer_handoffs/toy_road_p0_repeatability_20260803/SOURCE_MANIFEST.json producer_handoffs/toy_road_p0_repeatability_20260803/SHA256SUMS.txt tests/test_toy_road_fem_handoff.py
git commit -m "docs: seal D1 diagnostic handoff contract"
```

---

### Task 6: Full Regression, Independent Review And Clean Seal

**Files:**
- Modify only if tests or review find a defect: files already listed in Tasks 1-5.
- Do not create: D1 runtime evidence, production authorization or `.consumed`.

**Interfaces:**
- Consumes: reviewed Task 1-5 commits.
- Produces: one clean source commit fixed by a source manifest, a review report and a proposed non-authorizing D1 invocation; it does not launch MATLAB.

- [ ] **Step 1: Run full Python, PowerShell and MATLAB unit suites**

Run the repository's complete Python tests, both launcher suites and all
handoff MATLAB unit tests. MATLAB tests must be unit fixtures only and must be
preceded/followed by process and cycle-artifact checks.

```powershell
py -3 -m pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadD1LauncherTest.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadLauncherTest.ps1
matlab -batch "r=testsuite('producer_handoffs/toy_road_p0_repeatability_20260803/tests');assertSuccess(run(r));"
```

Require no production output, cycle shard, checkpoint, authorization or
`.consumed` artifact from tests.

- [ ] **Step 2: Run immutable-boundary audits**

Recompute the entire `969d3420` D0 checksum list and require 10/10 equality.
Verify the failed production root remains unchanged, sealed production source
is clean, and no MATLAB/FEM process remains. Run `git diff --check`, source-
manifest verification and SHA256SUMS verification.

- [ ] **Step 3: Request independent read-only review**

The reviewer checks every frozen requirement, the exact source graph, batch
generation, authorization isolation, old-evidence protection, receipt atomicity,
test matrix and source hashes. Changes requested by review follow fresh TDD
cycles and separate commits; do not amend reviewed commits silently.

- [ ] **Step 4: Create and push the sealed source commit**

After all reviews/tests pass, update only source manifests/hashes needed to fix
the final executable bytes, commit, push and verify a clean worktree. Record:

```text
sealed_source_commit
source_manifest_sha256
handoff_sha256s_sha256
Python/MATLAB/PowerShell test totals
review_commit_or_receipt
```

- [ ] **Step 5: Stop before D1 execution**

Report the sealed commit, test matrix, artifact schema and seven-part explicit
non-production proof from the design. State:

```text
D1 MATLAB execution: NOT AUTHORIZED
P0/P0R/T1/T2/T3: BLOCKED
```

Do not create a D1 root and do not launch MATLAB until a new human authorization
explicitly names the sealed source commit and permits exactly one D1 run.

---

### Task 7: Future One-Shot D1 Evidence Run (Explicit Authorization Required)

**Files:**
- Create after authorization: one external fresh D1 evidence root containing the ten artifacts defined by the design.
- Later create in Git: one evidence-only directory under `docs/toy_road_p0_repeatability_20260802/`.
- Do not modify: sealed source commit or `969d3420` quarantine.

**Interfaces:**
- Consumes: reviewed sealed source commit and a later explicit D1-only human authorization that is not a P0 production authorization.
- Produces: one PASS/FAIL/partial D1 evidence package and one separate evidence-only commit; never a production decision.

- [ ] **Step 1: Verify authorization and zero-process boundary**

Confirm the authorization names the sealed source commit, allows exactly one D1
diagnostic process and does not authorize P0. Verify zero existing MATLAB/FEM
processes without terminating any process.

- [ ] **Step 2: Derive and independently validate the D1 lock**

Run the sealed derivation tool against the read-only quarantined execution lock
and fresh D1 root. Validate both old/new SHA-256, replacement list and unchanged
digest before process launch.

- [ ] **Step 3: Launch exactly one D1 diagnostic**

Use only the sealed D1 launcher. Do not pass production authorization/output
arguments. Whether D1 returns PASS or FAIL, do not modify expectations and do
not rerun.

- [ ] **Step 4: Validate and quarantine D1 evidence**

Validate artifact hashes/chronology, structured first predicate, zero
producer/cycles, process counts, production-output absence and unchanged old
quarantine. If the process crashes or package is partial, preserve all files
and classify D1 as failed/incomplete without repair.

- [ ] **Step 5: Commit evidence separately and stop**

Copy exact evidence bytes into a new evidence-only directory with local binary
Git attributes where needed. Verify staged blobs equal external originals,
commit only evidence/governance files, push, and report the first failed
predicate or diagnostic PASS. Keep P0 blocked pending independent D1 review and
a future new P0 one-shot authorization.

## Execution Handoff

After this plan is committed, implementation remains blocked pending explicit
implementation authorization. Once authorized, Task 1 source implementation
uses test-driven development and per-task review; any MATLAB unit-test process
also requires the authorization boundary stated above. Task 7 remains
separately blocked even if Tasks 1-6 complete successfully.
