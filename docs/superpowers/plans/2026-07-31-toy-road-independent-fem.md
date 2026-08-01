# Toy-to-Road Independent FEM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Seal and execute three independent, mechanism-resolved Hard5 U0.12 FEM trajectories that vary only initial-defect geometry, fracture toughness, or physical loading history.

**Architecture:** A hash-sealed producer handoff in the integration repository owns three immutable input locks, pure configuration/mesh/event helpers, a read-only cycle-peak exporter, a run-local GRIPHFiTH solver derivative, and one single-case PowerShell launcher. All production cases share one reviewed source commit but receive independent fresh roots, snapshots, provenance, event metadata, state shards, and manifests; execution is strictly sequential.

**Tech Stack:** MATLAB R2025b, GRIPHFiTH Q4 FEM/MEX, SuiteSparse/CHOLMOD, PowerShell 5.1, Python 3 with pytest, JSON/CSV/MAT v7.3, Git/SHA-256.

## Global Constraints

- Parent is the 2026-07-29 Hard5 U0.12 five-step eta0 baseline with `first_hit=83` and `confirmed=86`.
- T1 changes only `a0/L: 0.5 -> 0.625` using the approved conforming coordinate-transfer contract.
- T2 changes only `Gc: 0.01 -> 0.008`; therefore `Gc/(E*ell): 1.0 -> 0.8`.
- T3 uses `Umax_N=0.108` for c1-c30, `0.126` for c31-c60, and `0.120` for c61+ with `R=0` and five retained substeps.
- Every case starts fresh, stops at confirmed penetration, or is right-censored at c150.
- Keep `first_hit` and `confirmed` distinct; confirmation requires three post-hit satisfying cycles.
- Run one computational experiment at a time. Check for MATLAB/FEM processes immediately before every solve.
- No T1/T2/T3 solve may start before the shared producer commit is sealed, pushed, freshly cloned with LF preserved, and verified clean.
- Do not modify archived references, constitutive MEX physics, tolerances, mesh ordering silently, event thresholds, or acceptance gates.
- Latent FEM fields are not road sensors. No PIDL/network training is authorized.

---

### Task 1: Register F1b Blocker and Lock the Parent Evidence

**Files:**
- Modify: `docs/handovers/windows_fem_outbox.md`
- Create: `producer_handoffs/toy_to_road_independent_fem_20260731/PARENT_LOCK.json`
- Test: `tests/test_toy_road_fem_handoff.py`

**Interfaces:**
- Consumes: F1b crash evidence under `C:/q4diag/f1b_outputs_20260731`, parent package `Hard5_eta0_5step_Umax_011_012_013_20260729/u012/SENS_hard5_u012_eta0_formal_pidl_native_q4_v1`, and parent bundle `analysis/fem_multitrajectory_contract_20260729/bundles/hard5_eta0_u012_5step_20260729.json`.
- Produces: `PARENT_LOCK.json` with parent IDs, event cycles, fixed physics/numerics, source file hashes, mesh identity, and state semantics used by every later task.

- [ ] **Step 1: Write the failing parent-lock test**

```python
def test_parent_lock_is_latest_c83_c86_baseline() -> None:
    lock = load_json(HANDOFF / "PARENT_LOCK.json")
    assert lock["parent_reference_id"] == "hard5_eta0_u012_5step_20260729"
    assert lock["event"] == {"first_hit": 83, "confirmed": 86}
    assert lock["physics"]["eta"] == 0.0
    assert lock["physics"]["n_substeps"] == 5
    assert lock["mesh"]["num_elem"] == 86408
    assert lock["state_semantics_id"] == "cycle_peak_coherent_v1"
```

- [ ] **Step 2: Run the test and verify RED**

Run: `python -m pytest tests/test_toy_road_fem_handoff.py::test_parent_lock_is_latest_c83_c86_baseline -q`

Expected: FAIL because `PARENT_LOCK.json` does not exist.

- [ ] **Step 3: Create the immutable parent lock**

Write exact values from the approved design and include SHA-256 values for `initial_state_metadata.mat`, `state0_analysis.mat`, `pre_run_lock.mat`, the c1/c83/c86 cycle shards, and the parent package manifest. Record Windows paths only as producer hints; hashes and IDs are authoritative.

- [ ] **Step 4: Append the F1b BLOCKED record**

Record source commit `022938d4066e6ef4152ec4017d58d02966dd6f73`, clean GRIPHFiTH commit `355d4c83fefc2db88c32031a2dd2623b3de85c89`, MATLAB R2025b Update 5, exit `0xc0000005`, failing binary `initial.mexw64`, binary SHA-256 `589F3DC793694EA2916FBB6A21DD030BC4BC04EAD3D91705E6E882B2D67CA340`, and the fact that no cycle completed. Keep Request 26 separate from Request 27.

- [ ] **Step 5: Run the focused test and existing evidence-gate tests**

Run: `python -m pytest tests/test_toy_road_fem_handoff.py tests/test_toy_to_road_evidence_gate.py -q`

Expected: PASS.

- [ ] **Step 6: Commit the parent lock and blocker record**

```powershell
git add docs/handovers/windows_fem_outbox.md tests/test_toy_road_fem_handoff.py producer_handoffs/toy_to_road_independent_fem_20260731/PARENT_LOCK.json
git commit -m "docs: lock latest Hard5 parent and F1b blocker"
```

### Task 2: Seal Single-Axis Case Configurations

**Files:**
- Create: `producer_handoffs/toy_to_road_independent_fem_20260731/FAMILY_INPUT_LOCK.json`
- Create: `producer_handoffs/toy_to_road_independent_fem_20260731/T1_INPUT_LOCK.json`
- Create: `producer_handoffs/toy_to_road_independent_fem_20260731/T2_INPUT_LOCK.json`
- Create: `producer_handoffs/toy_to_road_independent_fem_20260731/T3_INPUT_LOCK.json`
- Create: `producer_handoffs/toy_to_road_independent_fem_20260731/build_toy_road_case_config.m`
- Modify: `tests/test_toy_road_fem_handoff.py`
- Create: `producer_handoffs/toy_to_road_independent_fem_20260731/tests/toyRoadConfigTest.m`

**Interfaces:**
- Consumes: `PARENT_LOCK.json` and a case ID in `{T1_initial_defect,T2_material_state,T3_loading_history}`.
- Produces: `cfg = build_toy_road_case_config(case_id, lock_dir)` with fixed parent fields, exactly one changed axis, cycle amplitude function, c150 cap, and event contract.

- [ ] **Step 1: Add failing Python single-axis lock tests**

```python
@pytest.mark.parametrize(
    ("name", "axis"),
    [("T1_INPUT_LOCK.json", "initial_defect"),
     ("T2_INPUT_LOCK.json", "material_state"),
     ("T3_INPUT_LOCK.json", "loading_history")],
)
def test_case_lock_declares_exactly_one_primary_axis(name: str, axis: str) -> None:
    lock = load_json(HANDOFF / name)
    assert lock["primary_variation_axis"] == axis
    assert lock["changed_parent_fields"] == lock["allowed_changed_parent_fields"]
    assert lock["censor_cap"] == 150
```

Add exact assertions for T1 tip `(0.125,0)`, T2 `Gc=0.008` and Pi ratio `0.8`, and T3 block boundaries/amplitudes.

- [ ] **Step 2: Run Python tests and verify RED**

Run: `python -m pytest tests/test_toy_road_fem_handoff.py -q`

Expected: FAIL because family/case locks do not exist.

- [ ] **Step 3: Write the four JSON locks**

The family lock repeats every fixed parent field. Each case lock contains a machine-readable parent/candidate diff and an explicit allowlist. T3 stores block records `[1,30,0.108]`, `[31,60,0.126]`, and `[61,150,0.120]`.

- [ ] **Step 4: Write failing MATLAB configuration tests**

```matlab
function t3AmplitudeChangesOnlyAtLockedBoundaries(testCase)
cfg = build_toy_road_case_config("T3_loading_history", lockDir());
verifyEqual(testCase, cfg.umax_for_cycle([1 30 31 60 61 150]), ...
    [0.108 0.108 0.126 0.126 0.120 0.120], 'AbsTol', 1e-14);
verifyEqual(testCase, cfg.n_step, 5);
verifyEqual(testCase, cfg.censor_cap, 150);
end
```

Also test that an unknown case ID and any second changed axis raise `toyRoad:InvalidInputLock`.

- [ ] **Step 5: Run MATLAB tests and verify RED**

Run: `matlab -batch "r=runtests('producer_handoffs/toy_to_road_independent_fem_20260731/tests/toyRoadConfigTest.m'); assertSuccess(r)"`

Expected: FAIL because `build_toy_road_case_config` is undefined.

- [ ] **Step 6: Implement the configuration builder**

Use `jsondecode(fileread(...))`, validate exact field values, and return a function handle for `umax_for_cycle`. Reject non-integer cycles outside `1:150` and any lock whose parent hash differs from `PARENT_LOCK.json`.

- [ ] **Step 7: Run Python and MATLAB tests and verify GREEN**

Run both commands from Steps 2 and 5. Expected: PASS.

- [ ] **Step 8: Commit the case locks and builder**

```powershell
git add producer_handoffs/toy_to_road_independent_fem_20260731 tests/test_toy_road_fem_handoff.py
git commit -m "feat: lock independent FEM case configurations"
```

### Task 3: Implement T1 Mesh Transfer and Event State Machine

**Files:**
- Create: `producer_handoffs/toy_to_road_independent_fem_20260731/apply_t1_mesh_transfer.m`
- Create: `producer_handoffs/toy_to_road_independent_fem_20260731/advance_toy_road_event.m`
- Modify: `producer_handoffs/toy_to_road_independent_fem_20260731/tests/toyRoadConfigTest.m`

**Interfaces:**
- Consumes: parent `node_coords`, Q4 `connectivity`, `ell`, event-state struct, cycle number, and current peak damage.
- Produces: transferred coordinates plus mesh audit, and an event-state struct containing `first_hit`, `confirmed`, consecutive post-hit count, hit-node IDs, and connected-component evidence.

- [ ] **Step 1: Write failing mesh-transfer tests**

```matlab
function t1MapMovesTipAndFixesBoundaries(testCase)
[mapped, audit] = apply_t1_mesh_transfer(parentCoords(), parentConn(), 0.01);
verifyEqual(testCase, min(mapped(:,1)), -0.5, 'AbsTol', 1e-14);
verifyEqual(testCase, max(mapped(:,1)),  0.5, 'AbsTol', 1e-14);
verifyEqual(testCase, mapped(parentTipNode(),:), [0.125 0], 'AbsTol', 1e-14);
verifyTrue(testCase, audit.all_positive_jacobians);
verifyGreaterThanOrEqual(testCase, audit.mapped_over_parent_edge_ratio_min, 0.75);
verifyLessThanOrEqual(testCase, audit.mapped_over_parent_edge_ratio_max, 1.25);
end
```

- [ ] **Step 2: Write failing event tests**

Use a synthetic right-boundary chain. Verify no hit for two nodes, `first_hit=10` for three adjacent nodes, `confirmed=13` only after c11-c13 also hit, reset of confirmation progress after a miss, and no replacement of the original `first_hit`.

- [ ] **Step 3: Run MATLAB tests and verify RED**

Expected: FAIL because both helpers are undefined.

- [ ] **Step 4: Implement the piecewise-affine map and quality audit**

Map x coordinates exactly as approved, preserve y and connectivity, compute signed Q4 corner/Jacobian checks, boundary invariants, notch-node identity, mesh hashes, and deterministic mapped/parent incident-edge length ratios. Gate only the relative ratios in `[0.75, 1.25]`; export parent and mapped absolute `h/ell` ranges as audit-only values. Raise `toyRoad:MeshTransferGateFailed` before any solve when a gate fails.

- [ ] **Step 5: Implement connected event advancement**

Build adjacency from shared Q4 edges, restrict candidates to `x>=0.48` and `d>=0.95`, require a connected component of at least three nodes, and store evidence. Count three complete post-hit satisfying cycles, matching c83-to-c86 parent semantics.

- [ ] **Step 6: Run all MATLAB helper tests and verify GREEN**

Run: `matlab -batch "r=runtests('producer_handoffs/toy_to_road_independent_fem_20260731/tests'); assertSuccess(r)"`

Expected: PASS.

- [ ] **Step 7: Commit mesh/event helpers**

```powershell
git add producer_handoffs/toy_to_road_independent_fem_20260731
git commit -m "feat: add geometry transfer and event confirmation"
```

### Task 4: Implement Coherent Cycle-Peak Mechanism Export

**Files:**
- Create: `producer_handoffs/toy_to_road_independent_fem_20260731/export_toy_road_peak_state.m`
- Create: `producer_handoffs/toy_to_road_independent_fem_20260731/validate_toy_road_state.m`
- Create: `producer_handoffs/toy_to_road_independent_fem_20260731/tests/toyRoadExportTest.m`

**Interfaces:**
- Consumes: converged peak `displ`, `p_field`, GP history, raw GP driver, mesh/quadrature, reactions/residual, cycle metadata, and output path.
- Produces: one `states/cycle_NNNN.mat` with coherent nodal/element fields and one cycle-index row; validator returns field-range and semantic metrics.

- [ ] **Step 1: Write failing active-driver and field-shape tests**

```matlab
function activeDriverUsesGpProductBeforeMean(testCase)
gp_g = [1 0 1 0; 0.25 0.25 0.25 0.25];
gp_raw = [2 100 4 100; 8 4 2 2];
state = export_toy_road_peak_state(syntheticInput(gp_g, gp_raw), tempname);
verifyEqual(testCase, state.psi_active_elem, mean(gp_g .* gp_raw, 2));
verifyNotEqual(testCase, state.psi_active_elem, mean(gp_g,2).*mean(gp_raw,2));
end
```

Add assertions for explicit node/element semantics, finite arrays, threshold masks, reaction resultants, cycle/raw-step mapping, and mesh hash.

- [ ] **Step 2: Run exporter tests and verify RED**

Expected: FAIL because exporter/validator are undefined.

- [ ] **Step 3: Implement the exporter**

Interpolate `d_gp`, calculate `g_gp=(1-d_gp).^2`, calculate active GP values, then average GP fields by element. Split displacement into nodal u/v, derive element strain summaries using the existing Q4 operator, calculate top/bottom reaction resultants from the converged residual/reaction vector, derive crack masks `[0.50,0.75,0.90,0.95]`, and save MAT v7.3 atomically via a temporary file and rename.

- [ ] **Step 4: Implement state validation**

Use declared tolerances for range checks, verify `psi_active_elem` against recomputation, enforce consecutive cycle/raw-step metadata, and return a struct suitable for package summaries. Never clip fields in the validator.

- [ ] **Step 5: Run exporter tests and verify GREEN**

Run: `matlab -batch "r=runtests('producer_handoffs/toy_to_road_independent_fem_20260731/tests/toyRoadExportTest.m'); assertSuccess(r)"`

Expected: PASS.

- [ ] **Step 6: Commit the mechanism exporter**

```powershell
git add producer_handoffs/toy_to_road_independent_fem_20260731
git commit -m "feat: export coherent FEM mechanism states"
```

### Task 5: Build the Run-Local Solver and Fresh Case Driver

**Files:**
- Create: `producer_handoffs/toy_to_road_independent_fem_20260731/main_toy_to_road_case.m`
- Create: `producer_handoffs/toy_to_road_independent_fem_20260731/solve_toy_to_road_case.m`
- Create: `producer_handoffs/toy_to_road_independent_fem_20260731/write_toy_road_json.m`
- Create: `producer_handoffs/toy_to_road_independent_fem_20260731/tests/toyRoadDriverContractTest.m`

**Interfaces:**
- Consumes: environment variables `TOY_ROAD_CASE_ID`, `TOY_ROAD_OUTPUT_ROOT`, `TOY_ROAD_SOURCE_COMMIT`, `TOY_ROAD_LOCK_SHA256`, plus a clean GRIPHFiTH root on MATLAB path.
- Produces: fresh state0, `INPUT_SNAPSHOT.json`, `mesh_geometry.mat`, cycle peaks c1-terminal, `cycle_index.csv`, `EVENT_METADATA.json`, and terminal run result without resuming checkpoints.

- [ ] **Step 1: Write failing static driver-contract tests**

Verify the driver requires all environment variables, sets `eta=0`, preserves `1e-6/4e-4/4e-4`, disables line search/cycle jump, uses fresh hard recovery, clips recovered damage to `[0,1]`, resets fatigue state, calls the T1 map only for T1, calls `umax_for_cycle` once per physical cycle, exports only converged peaks, and stops only at confirmed or c150.

- [ ] **Step 2: Run the contract test and verify RED**

Expected: FAIL because the driver files do not exist.

- [ ] **Step 3: Implement the main driver**

Load the standard SENS Q4 problem, apply T1 coordinates before constructing `System`, apply only the selected material diff, construct the locked five-step solver, perform fresh zero-load hard recovery, reset fatigue history, write snapshot/mesh files, and invoke the run-local solver.

- [ ] **Step 4: Implement the solver derivative**

Start from the exact parent solver snapshot. At each cycle, set `uy_final` from the predeclared amplitude while preserving five normalized substeps. Capture the converged peak before unload, export read-only fields, advance the event state, append cycle index/event trace, and stop at confirmed/c150. Do not assign exporter-derived quantities back to physical state.

- [ ] **Step 5: Run all MATLAB unit/contract tests and verify GREEN**

Run: `matlab -batch "r=runtests('producer_handoffs/toy_to_road_independent_fem_20260731/tests'); assertSuccess(r)"`

Expected: all tests PASS without launching a computational trajectory.

- [ ] **Step 6: Run MATLAB Code Analyzer on producer files**

Run `checkcode` over every new `.m` file and resolve actionable errors. Script-workspace warnings inherited by the run-local solver must be documented, not suppressed globally.

- [ ] **Step 7: Commit the driver and solver**

```powershell
git add producer_handoffs/toy_to_road_independent_fem_20260731
git commit -m "feat: add fresh independent FEM trajectory driver"
```

### Task 6: Build Immutable Launch, Provenance, and Package Gates

**Files:**
- Create: `producer_handoffs/toy_to_road_independent_fem_20260731/launch_toy_road_case.ps1`
- Create: `producer_handoffs/toy_to_road_independent_fem_20260731/finalize_toy_road_package.m`
- Create: `producer_handoffs/toy_to_road_independent_fem_20260731/README.md`
- Create: `producer_handoffs/toy_to_road_independent_fem_20260731/SHA256SUMS.txt`
- Modify: `tests/test_toy_road_fem_handoff.py`

**Interfaces:**
- Consumes: `-SharedRepo`, `-GripfithRoot`, `-ParentRoot`, `-OutputParent`, and `-CaseId`.
- Produces: one immutable case output and, after success, `PRODUCER_PROVENANCE.json`, validation summary, and complete `SHA256SUMS.txt`.

- [ ] **Step 1: Add failing launcher/manifest tests**

```python
def test_launcher_is_single_case_and_refuses_resume() -> None:
    text = (HANDOFF / "launch_toy_road_case.ps1").read_text()
    assert "ValidateSet('T1_initial_defect','T2_material_state','T3_loading_history')" in text
    assert "status --porcelain" in text
    assert "Refusing to overwrite" in text
    assert "checkpoint" in text.lower()
```

Also verify every locked source appears exactly once in the source manifest and that the README states synthetic-only/no-training/no-road-validation.

- [ ] **Step 2: Run Python tests and verify RED**

Expected: FAIL because launcher/finalizer/manifest are absent.

- [ ] **Step 3: Implement the PowerShell launcher**

Verify LF-sensitive hashes, exact clean source commit, clean GRIPHFiTH source hashes, parent hashes, runtime MEX/SuiteSparse existence and hashes, no MATLAB/FEM process, non-existing output root, and no resume files. Set environment variables and invoke one case with process-level execution-policy bypass only at the outer calling layer when Windows policy requires it.

- [ ] **Step 4: Implement final package validation**

Load every state, verify dimensions/ranges/active identity/mesh hashes/consecutive cycles/event targets, write `PRODUCER_PROVENANCE.json`, `EVENT_METADATA.json`, and `VALIDATION_SUMMARY.json`, then generate a sorted SHA-256 manifest covering every file except the manifest itself.

- [ ] **Step 5: Generate the source manifest**

Hash exact bytes of all locks, MATLAB files, tests, README, and the parent solver snapshots. Verify from a fresh temporary copy without altering line endings.

- [ ] **Step 6: Run Python, MATLAB, and manifest tests and verify GREEN**

Expected: all unit/static tests PASS. Do not start a trajectory solve in this task.

- [ ] **Step 7: Commit launcher and package gates**

```powershell
git add producer_handoffs/toy_to_road_independent_fem_20260731 tests/test_toy_road_fem_handoff.py
git commit -m "feat: seal independent FEM producer handoff"
```

### Task 7: Seal, Push, and Verify the Producer Commit

**Files:**
- Modify only if verification finds a defect: files under `producer_handoffs/toy_to_road_independent_fem_20260731/` and their tests.

**Interfaces:**
- Consumes: completed handoff and passing tests.
- Produces: one pushed immutable producer commit and a fresh LF-preserving Windows checkout at exactly that commit.

- [ ] **Step 1: Run the full relevant test suite**

Run Python handoff/evidence tests and all MATLAB handoff tests. Expected: zero failures/incomplete tests.

- [ ] **Step 2: Verify source hashes and clean status**

Run `git diff --check`, verify `SHA256SUMS.txt`, and require empty `git status --porcelain` after committing any final test-driven fix.

- [ ] **Step 3: Push the integration branch**

```powershell
git push origin codex/toy-road-evidence-integration
```

Record the resulting full commit as `SEALED_COMMIT`.

- [ ] **Step 4: Create a fresh LF-preserving producer clone**

```powershell
git -c core.autocrlf=false clone --branch codex/toy-road-evidence-integration --single-branch `
  https://github.com/wenniebyfoxmail/phase-field-fracture-fatigue-pidl.git `
  C:\q4diag\phase-field-fracture-fatigue-pidl-toy-road-producer
```

Require `HEAD==SEALED_COMMIT`, empty status, and zero manifest failures.

- [ ] **Step 5: Perform runtime preflight without solving**

Use MATLAB `which` for every required MEX/helper and load/validate all locks. Check the exact approved MEX hashes. A crash or missing runtime blocks production; do not substitute binaries or relax gates.

### Task 8: Execute and Verify T1, T2, and T3 Sequentially

**Files:**
- Create outputs only: `toy_to_road_independent_fem_20260731/T1_initial_defect/`, `T2_material_state/`, `T3_loading_history/`, and final `family_manifest.json`/family `SHA256SUMS.txt`.
- Modify after completion: `docs/handovers/windows_fem_outbox.md`.

**Interfaces:**
- Consumes: fresh producer clone at `SEALED_COMMIT`, clean GRIPHFiTH runtime, parent root, and approved launcher.
- Produces: three independent terminal trajectories and one verified family package.

- [ ] **Step 1: Launch T1 after a fresh source/process gate**

Fetch/fast-forward the producer branch, require `HEAD==SEALED_COMMIT`, verify both repositories clean, verify no MATLAB/FEM process, then invoke the launcher for only `T1_initial_defect`. Wait for completion. Do not launch T2 while T1 is active.

- [ ] **Step 2: Validate T1 before continuing**

Require package gate PASS, exact T1 single-axis diff, mesh-transfer audit PASS, terminal `confirmed` or c150 censor, and a verified manifest. If invalid, stop the family and report; do not tune and rerun.

- [ ] **Step 3: Launch and validate T2 sequentially**

Repeat the fresh fetch/commit/clean/process gate, run only `T2_material_state`, wait, and require exact `Gc=0.008`, unchanged mesh/loading, terminal event/censor metadata, and manifest PASS.

- [ ] **Step 4: Launch and validate T3 sequentially**

Repeat the gate, run only `T3_loading_history`, wait, and require exact amplitudes at c1/c30/c31/c60/c61/terminal, unchanged mesh/material, terminal event/censor metadata, and manifest PASS.

- [ ] **Step 5: Build and verify the family manifest**

Record parent ID, exact case diffs, shared sealed commit, runtime/MEX hashes, per-case mesh and manifest hashes, ordering, units, plane state, BC, degradation/history ordering, event results, and explicit synthetic-only claim. Verify all hashes from a clean copy.

- [ ] **Step 6: Register the result without merging old archives**

Append Request 27 paths, sizes, hashes, first-hit/confirmed/censor results, and gate status to `windows_fem_outbox.md`. Keep the F1b BLOCKED record separate. Do not update Mac registry fields directly; Mac performs the contract adapter.

- [ ] **Step 7: Run final verification**

Invoke `superpowers:verification-before-completion`; confirm no MATLAB process remains, all manifests pass, and no required work is still running before reporting completion.
