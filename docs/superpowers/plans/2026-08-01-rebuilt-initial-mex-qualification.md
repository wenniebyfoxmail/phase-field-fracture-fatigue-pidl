# Rebuilt initial MEX Qualification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Admit the approved rebuilt `initial.mexw64` only after immutable runtime provenance, independent Q1 source equivalence, native-parent Q2 cycle-1 equivalence, and fail-closed family-launch qualification all pass.

**Architecture:** Keep the clean GRIPHFiTH source checkout separate from a repository-sealed runtime artifact. A dedicated qualification handoff runs Q1 and Q2 in isolated processes and publishes no-clobber receipts. The existing T1/T2/T3 launcher consumes those receipts and one shared runtime-lock digest before it can invoke MATLAB.

**Tech Stack:** MATLAB R2025b Update 5, pure MATLAB Q4 reference assembly, GRIPHFiTH Fortran MEX, PowerShell 5.1, JSON/MAT v7.3, Python pytest, MATLAB unit tests, Git/SHA-256.

## Global Constraints

- Follow `docs/superpowers/specs/2026-08-01-rebuilt-initial-mex-qualification-design.md` verbatim.
- Run only one MATLAB/FEM computational experiment at a time; Q2 and T1/T2/T3 are strictly serial.
- Never overwrite or delete an existing evidence root.
- Legacy `initial.mexw64` SHA-256 `589f3dc793694ea2916fbb6a21dd030bc4bc04ead3d91705e6e882b2d67ca340` is always rejected.
- The only approved rebuilt SHA-256 is `ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db`.
- Clean source identity is GRIPHFiTH `355d4c83fefc2db88c32031a2dd2623b3de85c89`; runtime binary identity is separate.
- Q1 and Q2 must both pass before any T1/T2/T3 solve.
- Missing true parent `g_elem` or `psi_active_elem` evidence blocks Q2; no element-mean substitute is permitted.
- All three family cases bind to one exact runtime-lock digest and rebuilt-MEX digest.

---

### Task 1: Seal the Independent Runtime Artifact and Lock Schema

**Files:**
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/runtime/initial.mexw64`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/RUNTIME_LOCK.json`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/build/BUILD_COMMAND.txt`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/build/BUILD_LOG.txt`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/build/SOURCE_HASHES.json`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/build/TOOLCHAIN.json`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/validate_runtime_lock.m`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/tests/rebuiltMexRuntimeLockTest.m`

**Interfaces:**
- Consumes: approved diagnostic binary at `C:/q4diag/initial_mex_rebuild_diag/out/initial.mexw64`, clean GRIPHFiTH source checkout, unchanged AMOR/AT1/CHOLMOD binaries.
- Produces: `validate_runtime_lock(lockPath, runtimeRoot, gripfithRoot) -> receipt` and immutable runtime-lock digest for every later task.

- [ ] **Step 1: Write failing runtime-lock tests**

Cover exact acceptance of `ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db`, rejection of `589f3dc793694ea2916fbb6a21dd030bc4bc04ead3d91705e6e882b2d67ca340`, rejection of an arbitrary third hash, missing build command/log, missing compiler fields, missing clean-source receipt, changed source commit, and missing/changed AMOR, AT1, or CHOLMOD hashes.

```matlab
legacyRoot = makeRuntimeFixture(testCase, 'initial_sha256', ...
    '589f3dc793694ea2916fbb6a21dd030bc4bc04ead3d91705e6e882b2d67ca340');
verifyError(testCase, @() validate_runtime_lock( ...
    fullfile(legacyRoot, 'RUNTIME_LOCK.json'), ...
    fullfile(legacyRoot, 'runtime'), fullfile(legacyRoot, 'griphfith')), ...
    'rebuiltMex:LegacyRuntimeRejected');
unknownRoot = makeRuntimeFixture(testCase, 'initial_sha256', repmat('a', 1, 64));
verifyError(testCase, @() validate_runtime_lock( ...
    fullfile(unknownRoot, 'RUNTIME_LOCK.json'), ...
    fullfile(unknownRoot, 'runtime'), fullfile(unknownRoot, 'griphfith')), ...
    'rebuiltMex:UnknownRuntimeRejected');
acceptedRoot = makeRuntimeFixture(testCase, 'initial_sha256', ...
    'ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db');
accepted = validate_runtime_lock(fullfile(acceptedRoot, 'RUNTIME_LOCK.json'), ...
    fullfile(acceptedRoot, 'runtime'), fullfile(acceptedRoot, 'griphfith'));
verifyEqual(testCase, accepted.initial_sha256, ...
    'ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db');
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run the new MATLAB test file. Expected: failure because the lock and validator do not exist.

- [ ] **Step 3: Add the runtime artifact and provenance**

Copy the already-approved exact binary without rebuilding it. Record the exact successful MATLAB `mex` command and `/free /fpp` flags, successful build output, MATLAB/compiler/linker identities, old crash dump identity, old/new hashes, GRIPHFiTH status/commit, and hashes of every consumed Fortran gateway/module. Compare the actual clean-checkout `.m/.c/.cpp/.h` inventory against hashes derived from the locked Git tree and require equality; the build output directory must remain outside the source checkout.

- [ ] **Step 4: Implement strict runtime-lock validation**

Reject duplicate paths, malformed SHA-256, absent fields, non-clean source receipt, changed source identities, unexpected runtime hash, and runtime/source identity conflation. Return canonical normalized records for receipts.

- [ ] **Step 5: Run focused tests and verify GREEN**

Expected: all runtime-lock positive and negative tests pass.

- [ ] **Step 6: Commit Task 1**

Commit only the runtime artifact, provenance, lock, validator, and focused tests.

---

### Task 2: Implement Q1 Independent MATLAB Assembly

**Files:**
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/assemble_initial_reference_q4.m`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/build_q1_native_input.m`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/compare_q1_initial_outputs.m`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/run_q1_initial_mex_qualification.m`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/tests/rebuiltMexQ1ReferenceTest.m`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/tests/rebuiltMexQ1GateTest.m`

**Interfaces:**
- Consumes: validated runtime receipt from Task 1 and clean GRIPHFiTH native SENS initialization APIs.
- Produces: `Q1_RESULT.json`, `Q1_METRICS.mat`, and a no-clobber `Q1_RECEIPT.json` bound to runtime/source/input hashes.

- [ ] **Step 1: Write RED tests for a small controlled Q4 mesh**

Use hand-computable one-element and two-element Q4 fixtures to assert Jacobians, blocked DOF ordering, damage interpolation, K triplets, M triplets, strain/stress operators, all six index arrays, and positive-Jacobian rejection.

- [ ] **Step 2: Run Q1 reference tests and verify RED**

Expected: missing `assemble_initial_reference_q4` failure.

- [ ] **Step 3: Implement pure MATLAB Q4 reference assembly**

Translate the locked Fortran formulas without calling equilibrium MEX functions. Preserve all 12 original column-vector shapes/orderings. Validate mesh/material/quadrature/connectivity before assembly and never densify the global native matrix.

- [ ] **Step 4: Run reference tests and verify GREEN**

Expected: controlled fixtures pass, including malformed input negatives.

- [ ] **Step 5: Write RED tests for the Q1 comparator**

Require exact index equality, relative L2/Frobenius `1e-12`, identically-zero max absolute `1e-14`, finite/shape/range checks, and the fixed top-y `0.03` probe. Verify that published names contain only `deterministic_internal_force_probe` and reject residual terminology.

- [ ] **Step 6: Implement the Q1 comparator and isolated runner**

Build the unrecovered native hard-crack field, call the rebuilt runtime artifact directly, compare all 12 outputs, assemble sparse K, compute the fixed probe, and publish receipts only after every gate passes.

- [ ] **Step 7: Run Q1 focused tests and verify GREEN**

Expected: all Q1 tests pass without launching a trajectory solve.

- [ ] **Step 8: Commit Task 2**

Commit Q1 implementation and tests.

---

### Task 3: Implement Q2 Parent Evidence and Metric Gates

**Files:**
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/Q2_INPUT_LOCK.json`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/validate_q2_parent_fields.m`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/build_q2_parent_masks.m`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/compare_q2_cycle1_fields.m`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/tests/rebuiltMexQ2ParentTest.m`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/tests/rebuiltMexQ2MetricsTest.m`

**Interfaces:**
- Consumes: eight locked parent artifacts plus an optional separately sealed parent GP/active supplement.
- Produces: pre-candidate parent mask artifact or an authoritative `blocked_missing_parent_damage_degradation_field` / `blocked_missing_parent_active_field` result.

- [ ] **Step 1: Write RED tests for parent field identity**

Assert exact field mapping, reject `f_alpha_elem` as active, reject `(1-d_elem)^2.*psi_raw_elem`, reject products of element means, and require true `g_elem` and `psi_active_elem` or sufficient sealed GP evidence.

- [ ] **Step 2: Run parent tests and verify RED**

Expected: missing validator failure.

- [ ] **Step 3: Implement fail-closed parent validation**

Verify parent file hashes, mesh/order identity, field semantics, shapes, and supplement provenance before reading candidate data. Publish the exact blocker without running Q2 when g/active evidence is unavailable.

- [ ] **Step 4: Write RED metric/mask tests**

Freeze `L(q)=log10(max(q,0)+1e-14)`, parent-only support, outside-mask absolute gates, negative-value rejection before clipping, zero-variance classification, and all specified damage/history/raw/active/f/g thresholds.

- [ ] **Step 5: Implement masks and comparator**

Make masks immutable and hash-addressed. Encode undefined zero-variance correlation as the literal string `not_applicable_zero_variance`, never numeric one.

- [ ] **Step 6: Run Q2 field/metric tests and verify GREEN**

Expected: complete fixture passes; current eight-file parent returns the required blocker; every prohibited substitute fails.

- [ ] **Step 7: Commit Task 3**

Commit Q2 locks, validators, metric code, and tests.

---

### Task 4: Add the Isolated One-Cycle Q2 Replay

**Files:**
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/run_q2_parent_cycle1_replay.m`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/solve_q2_parent_cycle1.m`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/export_q2_cycle1_fields.m`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/tests/rebuiltMexQ2ReplayContractTest.m`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/recover_q2_parent_initial_state.m`

**Interfaces:**
- Consumes: passing Task 1 runtime, passing Task 3 parent evidence, parent Umax `.12` solver snapshot.
- Produces: one-cycle replay state and Q2 result; never a family trajectory.

- [ ] **Step 1: Write RED controlled replay tests**

Require unmapped mesh, eta zero, Umax `.12`, exact parent recovery behavior, exact five retained effective factors, one cycle only, complete solver APIs, GP-product active export, and a Q2-only c1 terminal marker.

- [ ] **Step 2: Run replay tests and verify RED**

Expected: missing Q2 replay implementation.

- [ ] **Step 3: Implement the dedicated replay path**

Keep it separate from T1/T2/T3 config and terminal rules. Implement historical parent recovery in `recover_q2_parent_initial_state.m`; do not modify family recovery. Export damage, history, fatigue degradation, raw GP driver, GP damage degradation, and GP-product active driver with exact element ordering.

- [ ] **Step 4: Run replay tests and verify GREEN**

Expected: controlled replay contract passes without a real FEM run.

- [ ] **Step 5: Commit Task 4**

Commit Q2 replay implementation and tests.

---

### Task 5: Orchestrate Qualification and Gate the Family Launcher

**Files:**
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/launch_rebuilt_mex_qualification.ps1`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/validate_qualification_receipts.m`
- Create: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/tests/rebuiltMexQualificationLauncherTest.ps1`
- Modify: `producer_handoffs/toy_to_road_independent_fem_20260731/launch_toy_road_case.ps1`
- Modify: `producer_handoffs/toy_to_road_independent_fem_20260731/finalize_toy_road_package.m`
- Modify: `producer_handoffs/toy_to_road_independent_fem_20260731/tests/toyRoadLauncherTest.ps1`
- Modify: `producer_handoffs/toy_to_road_independent_fem_20260731/tests/toyRoadFinalizeTest.m`

**Interfaces:**
- Consumes: Q1/Q2 receipts and one runtime-lock digest.
- Produces: a family runtime receipt reused without change by T1/T2/T3.

- [ ] **Step 1: Write RED launcher negatives**

Cover missing Q1, failed Q1, missing/blocked/failed Q2, mismatched source/parent/runtime identities, legacy/unknown hashes, missing provenance, changed runtime between cases, and previous family-member failure.

- [ ] **Step 2: Run launcher tests and verify RED**

Expected: current launcher accepts no qualification root and therefore fails the new tests.

- [ ] **Step 3: Implement qualification orchestration**

Run Q1 and Q2 in separate MATLAB processes, publish no-clobber receipts, stop before Q2 solve when parent evidence is blocked, and never continue after a failure.

- [ ] **Step 4: Implement family qualification checks**

Require the same runtime-lock/qualification digests in preflight, launch receipt, finalizer, and all three case outputs. Put the rebuilt runtime overlay before clean GRIPHFiTH sources while recording both identities separately.

- [ ] **Step 5: Run focused launcher/finalizer tests and verify GREEN**

Expected: all fail-closed cases pass and only a complete matching Q1+Q2 fixture authorizes launch.

- [ ] **Step 6: Commit Task 5**

Commit orchestration and family-gate changes.

---

### Task 6: Documentation, Full Verification, Seal, and Runtime Execution

**Files:**
- Modify: `producer_handoffs/rebuilt_initial_mex_qualification_20260801/README.md`
- Modify: `producer_handoffs/toy_to_road_independent_fem_20260731/README.md`
- Modify: `producer_handoffs/toy_to_road_independent_fem_20260731/SHA256SUMS.txt`
- Modify: `docs/handovers/windows_fem_outbox.md`
- Create/update: qualification evidence under a fresh `C:/q4diag` root; do not commit mutable run outputs.

**Interfaces:**
- Consumes: reviewed Tasks 1-5.
- Produces: sealed producer commit/tag and, only if Q1/Q2 pass, serial T1/T2/T3 packages.

- [ ] **Step 1: Run all static/unit suites**

Run complete Python tests, complete MATLAB tests, PowerShell launcher tests, source manifest verification, runtime/API `which` checks, and all source/runtime hashes.

- [ ] **Step 2: Independently review implementation and evidence contracts**

Require clean spec and quality reviews before sealing.

- [ ] **Step 3: Regenerate manifest and seal/push qualification source**

Preserve LF-sensitive files, verify from a fresh clone, push without force, and create a durable evidence tag.

- [ ] **Step 4: Run Q1 from a fresh root**

If Q1 fails, publish failure and stop. Do not run Q2 or any family case.

- [ ] **Step 5: Validate parent g/active evidence and run Q2**

If parent evidence is absent, publish `blocked_missing_parent_damage_degradation_field` and/or `blocked_missing_parent_active_field` and stop without a cycle solve. If evidence is valid, run one Q2 cycle and apply every locked metric.

- [ ] **Step 6: Reseal final evidence binding if required**

Bind immutable Q1/Q2 receipt hashes to the final launcher contract, rerun all tests, verify fresh clone, push, and update the durable evidence tag.

- [ ] **Step 7: Run the family only after complete qualification**

Verify no MATLAB/FEM experiment is active. Use fresh roots and run strictly:

```text
T1 -> terminal validation
T2 -> terminal validation
T3 -> terminal validation
```

Stop immediately on any failure. Never change runtime between cases.

- [ ] **Step 8: Publish final outbox status**

Record exact commits, tags, runtime/source hashes, Q1/Q2 metrics or blocker, family terminal results, and paths without relabelling the legacy crash.
