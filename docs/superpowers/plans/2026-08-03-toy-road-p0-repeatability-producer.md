# Toy-to-Road P0/P0R Producer Implementation Plan v1.1

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and seal a fail-closed Windows FEM producer for P0, P0R, T1, T2 and T3 that emits five-substep native-Q4 evidence, independently qualifies every case at c5 peak, and admits T1 only after P0/P0R repeatability passes.

**Architecture:** Preserve `producer_handoffs/toy_to_road_independent_fem_20260731/` as a read-only historical implementation reference and create a new versioned handoff at `producer_handoffs/toy_road_p0_repeatability_20260803/`. MATLAB owns state capture, constitutive validation, same-process c5 qualification and terminal package validation; Python owns canonical JSON digests, repeatability comparison and attempt-ledger/manifest generation; PowerShell owns immutable runtime checks, one-shot process isolation and strict launch ordering. The implementation plan ends at a clean sealed preflight and does not authorize a trajectory solve.

**Tech Stack:** MATLAB R2025b Update 5, GRIPHFiTH Q4 FEM/MEX at `355d4c83fefc2db88c32031a2dd2623b3de85c89`, rebuilt `initial.mexw64` SHA-256 `ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db`, PowerShell 5.1, Python 3 with pytest, JSON/JSONL/CSV/MAT v7.3, Git/SHA-256.

**Revision:** v1.1 incorporates review against plan commit `29d4a2493ac95d38ccb6b04b725e5656cc412660`. This remains a plan-only artifact; implementation and FEM execution are not authorized by this revision.

## Global Constraints

- The approved design is `docs/superpowers/specs/2026-08-02-toy-road-p0-repeatability-design.md` at commit `8c364c14c7ce84a9684d214861813b49d8f442f8`.
- Reuse the accepted Q1 receipt, including its `deterministic_internal_force_probe`; never rename that quantity as a Newton/equilibrium residual and never rerun Q1 between family members.
- Historical Q2 remains `historical_q2_parent_irrecoverable`; no missing active field may be reconstructed or relabelled.
- P0 and P0R are independent executions of identical Hard5 `Umax=0.12`, `R=0`, `eta=0` physics with fresh recovery, clipping to `[0,1]`, and `System` rebuild.
- Fixed parent material/solver values are `E=1`, `nu=0.3`, `Gc=0.01`, `ell=0.01`, `alpha_T=0.5`, `p=2`, plane strain, AMOR split and AT1 history fatigue.
- Fixed tolerances are displacement `1e-6`, phase `4e-4` and staggered `4e-4`; line search and cycle jump are disabled.
- Retained substeps are exactly `[0.25,0.50,0.75,1.00,0.00]`; peak is substep 4; censor cap is c150.
- T1 changes only initial-defect geometry, T2 changes only `Gc`, and T3 changes only loading history, using the already approved case definitions.
- Penetration is evaluated at cycle peak using at least three connected or adjacent right-boundary nodes with `d>=0.95` and `x>=0.48`; confirmation requires three post-hit cycles.
- P0, P0R, T1, T2 and T3 each require a same-process c5 peak gate: displacement residual `<=4e-4`, projected phase KKT `<=4e-4`, consecutive-stagger damage infinity norm `<=1e-3`, and primal feasibility `<=1e-12`.
- `alpha_bar_gp` is post-commit, non-negative and irreversible; `f_alpha_gp` uses the locked Carrara expression with `alpha_T=0.5`, `p=2`; nodal damage satisfies `d_lb<=d<=1`.
- `family_contract_sha256` is shared by all five cases; `case_physics_contract_sha256` is shared only by P0/P0R; `execution_input_lock_sha256` is unique per launch.
- Every case uses a fresh one-shot MATLAB process with isolated writable work, TEMP, TMP, preferences and cache roots, and fixed single-thread BLAS/OpenMP settings.
- Only one MATLAB/FEM experiment may run at a time. The launcher may never stop another process automatically.
- Preserve one primary `decision.md`, one append-only attempt ledger and one `docs/pidl_experiment_inventory.md` row for the family.
- The 2026-07-29 U0.12 trajectory remains an external reference only. Do not claim historical equivalence for `g_gp`, `g_elem`, `psi_active_gp` or `psi_active_elem`, and do not tune P0/P0R using historical fields.
- Dense VTK and unrelated visualization snapshots remain disabled; the compact peak references bytes already present in each cycle shard.
- No implementation task below may start P0/P0R/T1/T2/T3. The only permitted MATLAB invocations are unit tests and preflight API/runtime probes that do not enter recovery, `System`, Newton or cycle 1.

---

### Task 1: Build the Five-Substep State Validator First

**Files:**
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/validate_toy_road_cycle_shard.m`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadCycleShardValidatorTest.m`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadShardFixture.m`

**Interfaces:**
- Consumes: `metrics = validate_toy_road_cycle_shard(shard, previous, state0, contract)`, where `previous=[]` only for c1 and `contract` contains mesh/order IDs, three digests, `eta`, `alpha_T`, `p`, range tolerances and expected cycle metadata.
- Produces: a scalar `metrics` struct containing min/max values, maximum identity errors, chronology checks and `is_valid=true`; any violation raises `toyRoadP0:InvalidCycleShard` without clipping or rewriting input.

- [ ] **Step 1: Write the valid synthetic fixture**

```matlab
function [shard, previous, state0, contract] = toyRoadShardFixture(cycle)
nNode = 4; nElem = 1; nGp = 4;
contract = toyRoadFixtureContract();
N = 0.25 * ones(nGp, nNode);
dNode = repmat(linspace(0.10, 0.14, 5) + 0.04*(cycle-1), nNode, 1);
dGp = zeros(nElem, nGp, 5);
for s = 1:5
    dGp(:,:,s) = dNode(:,s).' * N.';
end
alpha = reshape(linspace(0.01, 0.05, 5) + 0.05*(cycle-1), 1, 1, 5) .* ...
    ones(nElem,nGp,5);
f = min(1, (1 - ((alpha - 0.5) ./ (alpha + 0.5))).^2);
raw = ones(nElem,nGp,5) .* reshape(1:5,1,1,5);
g = (1-dGp).^2;
shard = struct('cycle',cycle,'d_node',dNode,'d_gp',dGp, ...
    'alpha_bar_gp',alpha,'f_alpha_gp',f,'psi_raw_gp',raw, ...
    'g_gp',g,'psi_active_gp',g.*raw, ...
    'psi_raw_cyclemax_gp',max(raw,[],3), ...
    'substep_ordinal',1:5,'load_factor',[.25 .5 .75 1 0], ...
    'raw_step_zero_based',5*(cycle-1)+(0:4), ...
    'branch',{{'loading','loading','loading','loading','unloading'}}, ...
    'mesh_sha256',contract.mesh_sha256, ...
    'element_ordering_id',contract.element_ordering_id, ...
    'gp_ordering_id',contract.gp_ordering_id, ...
    'state_semantics_id',contract.state_semantics_id, ...
    'runtime_lock_sha256',contract.runtime_lock_sha256, ...
    'family_contract_sha256',contract.family_contract_sha256, ...
    'case_physics_contract_sha256',contract.case_physics_contract_sha256, ...
    'execution_input_lock_sha256',contract.execution_input_lock_sha256);
state0 = struct('d_node',0.09*ones(nNode,1), ...
    'alpha_bar_gp',zeros(nElem,nGp));
previous = [];
end

function contract = toyRoadFixtureContract()
contract = struct('eta',0,'alpha_T',0.5,'p',2, ...
    'mesh_sha256',repmat('1',1,64), ...
    'element_ordering_id','q4_connectivity_1_based_v1', ...
    'gp_ordering_id','q4_2x2_native_order_v1', ...
    'state_semantics_id','five_substep_post_commit_history_v1', ...
    'runtime_lock_sha256',repmat('2',1,64), ...
    'family_contract_sha256',repmat('3',1,64), ...
    'case_physics_contract_sha256',repmat('4',1,64), ...
    'execution_input_lock_sha256',repmat('5',1,64));
end
```

- [ ] **Step 2: Write failing validator tests**

Add separate tests that mutate one fact at a time: wrong `[n_elem,4,5]` shape, non-finite value, `d_node<d_lb`, `d_node>1`, negative/decreasing `alpha_bar_gp`, `f_alpha_gp` outside `[0,1]`, Carrara mismatch, negative raw/active driver, incorrect `g_gp`, incorrect `psi_active_gp`, incorrect cycle maximum, wrong substep order, wrong raw-step mapping, wrong mesh/order ID, and each of the three wrong digests.

```matlab
function testRejectsCarraraMismatch(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.f_alpha_gp(1,1,3) = shard.f_alpha_gp(1,1,3) + 2e-12;
verifyError(testCase, ...
    @() validate_toy_road_cycle_shard(shard,previous,state0,contract), ...
    'toyRoadP0:InvalidCycleShard');
end

function testRejectsCrossCycleHistoryDecrease(testCase)
[previous,~,state0,contract] = toyRoadShardFixture(1);
[shard,~,~,~] = toyRoadShardFixture(2);
shard.alpha_bar_gp(:,:,1) = previous.alpha_bar_gp(:,:,5) - 2e-12;
verifyError(testCase, ...
    @() validate_toy_road_cycle_shard(shard,previous,state0,contract), ...
    'toyRoadP0:InvalidCycleShard');
end
```

- [ ] **Step 3: Run the validator tests and verify RED**

Run:

```powershell
matlab -batch "r=runtests('producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadCycleShardValidatorTest.m'); assertSuccess(r)"
```

Expected: FAIL because `validate_toy_road_cycle_shard` is undefined.

- [ ] **Step 4: Implement the minimal validator**

Use vectorized `(:)` comparisons. Recompute, rather than trust exporter intermediates:

```matlab
fExpected = min(1, ...
    (1 - ((shard.alpha_bar_gp-contract.alpha_T) ./ ...
          (shard.alpha_bar_gp+contract.alpha_T))).^contract.p);
gExpected = (1-shard.d_gp).^2 + contract.eta;
activeExpected = shard.g_gp .* shard.psi_raw_gp;
cyclemaxExpected = max(shard.psi_raw_gp,[],3);
```

For c1/substep 1 use `state0.d_node` and `state0.alpha_bar_gp` as predecessors; otherwise walk c1s1, c1s2, ..., cNs5 chronologically. Enforce nodal primal feasibility `<=1e-12`, history tolerance `1e-12`, fatigue range tolerance `1e-12`, damage/driver range tolerance `1e-10`, and identity maximum absolute error `<=1e-12`.

- [ ] **Step 5: Run the focused tests and verify GREEN**

Run the command from Step 3. Expected: every valid fixture passes and every one-field mutation fails closed.

- [ ] **Step 6: Commit the validator slice**

```powershell
git add producer_handoffs/toy_road_p0_repeatability_20260803
git commit -m "test: define toy-road five-step state legality"
```

### Task 2: Build Package and Repeatability Validators

**Files:**
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/validate_toy_road_terminal_package.m`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadTerminalPackageValidatorTest.m`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/toy_road_protocol.py`
- Create: `tests/test_toy_road_p0_protocol.py`

**Interfaces:**
- Consumes: `summary = validate_toy_road_terminal_package(root, case_id, contract_path)` and Python `compare_repeatability(p0_root: Path, p0r_root: Path) -> dict[str, object]`.
- Produces: terminal validation metrics and `P0_REPEATABILITY_EVIDENCE_LOCK.json` only when both immutable packages and all trajectory fields pass exact identity plus relative-L2/max-absolute gates `<=1e-12`.

- [ ] **Step 1: Write failing MATLAB package tests**

Create no-clobber synthetic packages with c1-c5 shards and assert rejection for a missing cycle, extra cycle, wrong case-local mesh hash, mismatched event metadata, terminal cycle mismatch, missing c5 trace/receipt, failed c5 receipt, mutable manifest and an execution-lock digest inconsistent with its own manifest.

The test file defines local `makeTerminalPackage(testCase,caseId)` by writing five valid shards from `toyRoadShardFixture`, a PASS c5 trace/receipt, terminal event/result files and a sorted manifest under `testCase.applyFixture`; `contractPath()` writes the matching scalar contract to that fixture root and returns its path.

```matlab
function testEveryCaseRequiresOwnC5Receipt(testCase)
root = makeTerminalPackage(testCase,"T1_initial_defect");
delete(fullfile(root,'qualification','C5_NUMERICAL_GATE_RECEIPT.json'));
verifyError(testCase, ...
    @() validate_toy_road_terminal_package(root,"T1_initial_defect",contractPath()), ...
    'toyRoadP0:InvalidTerminalPackage');
end
```

- [ ] **Step 2: Write failing Python repeatability tests**

```python
def test_relative_l2_vectorizes_nd_fields() -> None:
    reference = np.arange(24, dtype=np.float64).reshape((2, 3, 4), order="F")
    candidate = reference.copy()
    candidate[1, 2, 3] += 5e-13 * max(np.linalg.norm(reference.reshape(-1, order="F")), 1e-30)
    assert relative_l2(candidate, reference) <= 1e-12

def test_repeatability_rejects_equal_bad_c5_receipts(tmp_path: Path) -> None:
    p0, p0r = make_repeatability_packages(tmp_path, c5_passed=False)
    with pytest.raises(ProtocolError, match="case-local c5 gate"):
        compare_repeatability(p0, p0r)
```

Also cover matrix/3-D arrays, identically zero fields, shape mismatch, source/runtime/family/case digest mismatch, event mismatch, P0/P0R execution-lock inequality being permitted, and any threshold just above `1e-12` failing.

In `tests/test_toy_road_p0_protocol.py`, define `ProtocolError` in the production module and `make_repeatability_packages` as a test helper that materializes two c1-c5 valid fixture packages with different execution locks. Do not mutate a finalized shard to test numerical thresholds: that would invalidate the constitutive identities and manifest before repeatability is reached. Threshold arithmetic is tested directly through `relative_l2`; package-level tests use independently finalized, internally consistent packages.

- [ ] **Step 3: Run both test files and verify RED**

```powershell
python -m pytest tests/test_toy_road_p0_protocol.py -q
matlab -batch "r=runtests('producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadTerminalPackageValidatorTest.m'); assertSuccess(r)"
```

Expected: FAIL because both validators are absent.

- [ ] **Step 4: Implement terminal validation and repeatability comparison**

In Python, use exactly:

```python
def relative_l2(candidate: np.ndarray, reference: np.ndarray) -> float:
    delta = np.asarray(candidate, dtype=np.float64).reshape(-1, order="F") - \
        np.asarray(reference, dtype=np.float64).reshape(-1, order="F")
    ref = np.asarray(reference, dtype=np.float64).reshape(-1, order="F")
    return float(np.linalg.norm(delta) / max(np.linalg.norm(ref), 1e-30))
```

Require exact package identities before numerical comparison. Write the evidence lock through a temporary file plus exclusive rename; include both package manifest hashes, both c5 receipt hashes, all field metrics, runtime lock, source commit, exporter hash and protocol version.

- [ ] **Step 5: Run both focused suites and verify GREEN**

Run Step 3 commands. Expected: PASS.

- [ ] **Step 6: Commit the admission validators**

```powershell
git add producer_handoffs/toy_road_p0_repeatability_20260803 tests/test_toy_road_p0_protocol.py
git commit -m "feat: validate toy-road packages and repeatability"
```

### Task 3: Implement the Five-Substep Exporter

**Files:**
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/init_toy_road_cycle_capture.m`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/capture_toy_road_substep.m`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/export_toy_road_cycle_shard.m`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadCycleExporterTest.m`

**Interfaces:**
- Consumes: converged nodal damage, instantaneous `psi_raw_gp`, post-commit history, Q4 connectivity/shape functions and immutable metadata after each retained substep.
- Produces: one in-memory capture with five immutable slices and one `substeps/cycle_NNNN.mat` shard published after substep 5 using MAT v7.3 and no-clobber rename.

- [ ] **Step 1: Write failing exporter tests**

Verify that capture rejects reordered/duplicate ordinals, captures `psi_raw_gp` before history mutation, captures `alpha_bar_gp`/`f_alpha_gp` after exactly one normal commit, computes peak active from substep 4, computes cycle maximum separately, and refuses to serialize until all five slices exist.

The test-local `fixtureContract()` returns the same exact scalar fields as `toyRoadFixtureContract`. `filledCaptureWithNonCommutingGpMeans()` calls `init_toy_road_cycle_capture`, then `capture_toy_road_substep` five times with GP arrays chosen so `mean(g.*raw,2)` differs from `mean(g,2).*mean(raw,2)`.

```matlab
function testPeakActiveUsesSimultaneousSubstepFourProduct(testCase)
capture = filledCaptureWithNonCommutingGpMeans();
shard = export_toy_road_cycle_shard(capture,tempname,fixtureContract());
verifyEqual(testCase,shard.psi_active_gp(:,:,4), ...
    shard.g_gp(:,:,4).*shard.psi_raw_gp(:,:,4),'AbsTol',1e-12);
verifyNotEqual(testCase,mean(shard.psi_active_gp(:,:,4),2), ...
    mean(shard.g_gp(:,:,4),2).*mean(shard.psi_raw_gp(:,:,4),2));
end
```

- [ ] **Step 2: Run exporter tests and verify RED**

```powershell
matlab -batch "r=runtests('producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadCycleExporterTest.m'); assertSuccess(r)"
```

- [ ] **Step 3: Implement capture and no-clobber export**

`capture_toy_road_substep` must accept both `history_pre` and `history_post`, assert that the supplied exported history is `history_post`, and store no references to mutable solver arrays. `export_toy_road_cycle_shard` calls `validate_toy_road_cycle_shard` before writing, saves to a fresh temporary path using `save(...,'-v7.3')`, hashes it, then atomically renames it to `substeps/cycle_%04d.mat` only when the destination is absent.

- [ ] **Step 4: Keep the compact peak state as a byte reference**

Write peak metadata containing `cycle_shard_sha256`, `peak_substep_ordinal=4` and field slice descriptors. Do not serialize duplicate GP arrays and do not retain dense VTK output.

- [ ] **Step 5: Run validator and exporter suites and verify GREEN**

```powershell
matlab -batch "r=runtests('producer_handoffs/toy_road_p0_repeatability_20260803/tests'); assertSuccess(r)"
```

- [ ] **Step 6: Commit the exporter**

```powershell
git add producer_handoffs/toy_road_p0_repeatability_20260803
git commit -m "feat: export five-step native Q4 cycle shards"
```

### Task 4: Implement and Integrate the Same-Process C5 Gate

**Files:**
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/begin_toy_road_c5_trace.m`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/append_toy_road_c5_stagger_row.m`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/finalize_toy_road_c5_gate.m`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadC5GateTest.m`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/solve_toy_road_family_case.m`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadSolverControlledTest.m`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/tests/ToyRoadP0SolverDouble.m`

**Interfaces:**
- Consumes: `trace = begin_toy_road_c5_trace(entry_input, output_root)` at c5/substep-4 entry; `trace = append_toy_road_c5_stagger_row(trace, row_input)` immediately after every completed stagger update; and `receipt = finalize_toy_road_c5_gate(trace)` only after the normal solver reports stagger convergence.
- Produces: one same-process reassembly row per completed stagger in `qualification/C5_STAGGER_TRACE.csv`, followed by `qualification/C5_NUMERICAL_GATE_RECEIPT.json`; any append/finalize failure throws before c5 history commit and before any c6 work.

- [ ] **Step 1: Write failing numerical-gate tests**

Use controlled operators to place each metric exactly below, at and above its threshold. Verify that raw phase residual is recorded but is not substituted for projected KKT, and that post-process/fixed-count/teacher/replay receipts are rejected.

The test-local `gateFixture()` creates a fresh output root, two active displacement/phase DOFs, converged `u/d`, `d_lb`, `d_prev_stag`, `history_pre`, traction and deterministic reassembly handles returning the declared `r_u/r_d`; no GRIPHFiTH MEX is loaded by this fixture.

```matlab
function testProjectedKktUsesIrreversibilityBox(testCase)
input = gateFixture();
input.d = [0.4;0.8]; input.d_lb = [0.4;0.2];
input.r_d = [1e-4;-1e-4];
trace = begin_toy_road_c5_trace(input,testCase.TestData.root);
trace = append_toy_road_c5_stagger_row(trace,input);
receipt = finalize_toy_road_c5_gate(trace);
expected = norm(input.d-max(input.d_lb,min(1,input.d-input.r_d)),inf);
verifyEqual(testCase,receipt.projected_phase_kkt,expected,'AbsTol',1e-15);
verifyEqual(testCase,receipt.primal_feasibility,0,'AbsTol',0);
end
```

- [ ] **Step 2: Run gate tests and verify RED**

```powershell
matlab -batch "r=runtests('producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadC5GateTest.m'); assertSuccess(r)"
```

- [ ] **Step 3: Implement the begin/append/finalize lifecycle**

`begin_toy_road_c5_trace` snapshots `d_lb`, `history_pre`, active DOFs, traction, trace path and the accepted substep-entry damage; it creates the CSV header exclusively and writes no metric row. Every `append_toy_road_c5_stagger_row` performs fresh same-process reassembly of `r_u` and `r_d` using that immutable entry snapshot plus the just-completed stagger `(u,d)`, then computes:

```matlab
du = norm(r_u(active_u_dofs),2);
kkt = norm(d(active_d_dofs) - max(d_lb(active_d_dofs), ...
    min(1,d(active_d_dofs)-r_d(active_d_dofs))),inf);
stag = norm(d-d_prev_stag,inf);
primal = max([0;d_lb(:)-d(:);d(:)-1]);
```

Append exactly one row containing stagger ordinal, displacement residual, raw phase residual, projected phase KKT, consecutive-stagger delta and primal feasibility. Update `d_prev_stag` only after the row is durably appended. `finalize_toy_road_c5_gate` requires at least one row, requires the final row to be the converged stagger, applies all four gates, and binds row count, reassembly count and trace hash into the receipt.

- [ ] **Step 4: Integrate the gate into the controlled cycle loop**

Start from the sealed logic in `solve_toy_to_road_case.m`, but instrument all five substeps and set the solver template to exactly five steps. At c5/substep-4 entry call `begin_toy_road_c5_trace`. After every completed stagger update, including non-converged ones, call `append_toy_road_c5_stagger_row` before deciding whether to continue. Once the same appended row is declared converged, call `finalize_toy_road_c5_gate`; only PASS permits the normal history commit. On failure, publish a failed run receipt and never continue to unload or c6.

- [ ] **Step 5: Verify the call ordering with a solver double**

Configure the solver double for three completed staggers and assert this trace:

```text
c5_trace_begin
c5_stagger_1_update
c5_stagger_1_reassembly_append
c5_stagger_2_update
c5_stagger_2_reassembly_append
c5_stagger_3_update_converged
c5_stagger_3_reassembly_append
c5_gate_receipt_passed
c5_s4_history_committed
c5_s5_unload
```

Assert `trace_row_count=3`, `same_process_reassembly_count=3`, exact ordinal order `[1,2,3]`, and one append for every completed stagger. Also assert that P0, P0R, T1, T2 and T3 all take the identical gate path and that no case can inject a parent receipt.

- [ ] **Step 6: Run all MATLAB tests and verify GREEN**

```powershell
matlab -batch "r=runtests('producer_handoffs/toy_road_p0_repeatability_20260803/tests'); assertSuccess(r)"
```

- [ ] **Step 7: Commit the c5 gate and instrumented solver**

```powershell
git add producer_handoffs/toy_road_p0_repeatability_20260803
git commit -m "feat: gate every toy-road case at c5 peak"
```

### Task 5: Implement Recovery, Case Construction and Producer Driver

**Files:**
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/build_toy_road_family_case.m`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/recover_toy_road_family_state.m`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/main_toy_road_family_case.m`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadCaseBuilderTest.m`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadRecoveryTest.m`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadDriverContractTest.m`

**Interfaces:**
- Consumes: one validated case role and its case-physics contract plus the approved Q1 runtime.
- Produces: independently reconstructed state0, case-declared mesh, fixed solver context and fresh output structure; `main_toy_road_family_case` is callable only after launcher authorization.

- [ ] **Step 1: Write failing construction and recovery tests**

Assert P0/P0R byte-identical physical configuration, T1-only mapped mesh, T2-only `Gc=0.008`, T3-only loading schedule, `eta=0`, Hard5 cadence, no line search/jump/resume, recovery clipping followed by `System` rebuild, and reset post-recovery fatigue history.

```matlab
function testRecoveryClipsThenRebuildsSystem(testCase)
[~,d,dOld,history,details] = recover_toy_road_family_state(fixtureInput());
verifyGreaterThanOrEqual(testCase,min(d),0);
verifyLessThanOrEqual(testCase,max(d),1);
verifyEqual(testCase,details.system_factory_phase_field,d);
verifyTrue(testCase,details.system_rebuilt_after_projection);
verifyEqual(testCase,history(:,:,2:3),zeros(size(history,1),4,2));
end
```

`fixtureInput()` supplies a recording system factory and recovery Newton double. The factory stores its constructor phase field in `details.system_factory_phase_field`, allowing the test to verify rebuild input without reading GRIPHFiTH `System` private properties.

- [ ] **Step 2: Run focused tests and verify RED**

```powershell
matlab -batch "r=runtests('producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadCaseBuilderTest.m'); r=[r;runtests('producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadRecoveryTest.m')]; assertSuccess(r)"
```

- [ ] **Step 3: Implement exact case construction**

Reuse the tested coordinate map, event state machine and Q4 mesh hash semantics from the 20260731 handoff by copying their reviewed logic into the new versioned handoff and testing the new bytes. Do not import executable source from the old handoff at runtime. Set `SOL_STEP_PAR.n_step=5` directly and assert it before recovery.

- [ ] **Step 4: Implement the fresh driver**

Require environment variables for role, source commit, runtime lock, all three digests and fresh roots. Build state0 independently, publish `INPUT_SNAPSHOT.json`, `mesh_geometry.mat`, `state0_analysis.mat` and runtime receipt, then call `solve_toy_road_family_case`. No checkpoint/resume path exists.

- [ ] **Step 5: Run all MATLAB tests and static contract checks**

```powershell
matlab -batch "r=runtests('producer_handoffs/toy_road_p0_repeatability_20260803/tests'); assertSuccess(r)"
```

Run `checkcode` on every new `.m` file and resolve new actionable diagnostics.

- [ ] **Step 6: Commit the producer driver**

```powershell
git add producer_handoffs/toy_road_p0_repeatability_20260803
git commit -m "feat: build fresh P0 family FEM cases"
```

### Task 6: Implement Three-Layer Locks and the Fail-Closed Launcher

**Files:**
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/FAMILY_CONTRACT.json`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/CASE_PHYSICS_CONTRACTS.json`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/HISTORICAL_Q2_CLOSURE.json`
- Modify: `producer_handoffs/toy_road_p0_repeatability_20260803/toy_road_protocol.py`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/launch_toy_road_family_case.ps1`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadLauncherTest.ps1`
- Modify: `tests/test_toy_road_p0_protocol.py`

**Interfaces:**
- Consumes: role in `{P0_parent,P0R_parent_repeat,T1_initial_defect,T2_material_state,T3_loading_history}`, clean source/runtime roots, Q1 qualification root, fresh output/work/TEMP/cache roots and prior immutable evidence.
- Produces: canonical three-layer digests and one no-clobber execution lock. Production mode may authorize exactly one fresh `matlab -batch` process after dynamic predecessor evidence passes. `-PreflightOnly` checks only static contract/runtime/path isolation, emits `authorization_scope=preflight_only_non_authorizing` with `dynamic_chain_status=not_evaluated_no_execution`, and never invokes `main_toy_road_family_case`.

- [ ] **Step 1: Write failing digest tests**

```python
def test_contract_digest_layers_are_correct() -> None:
    contracts = load_contracts()
    assert len({c.family_sha256 for c in contracts.values()}) == 1
    assert contracts["P0_parent"].case_sha256 == contracts["P0R_parent_repeat"].case_sha256
    assert contracts["T1_initial_defect"].case_sha256 != contracts["P0_parent"].case_sha256
    assert contracts["T2_material_state"].changed_axes == ["material.Gc"]
    assert contracts["T3_loading_history"].changed_axes == ["loading.blocks"]
```

Add mutation tests for any shared-family mismatch, P0/P0R physics mismatch, and every T1/T2/T3 second-axis change.

- [ ] **Step 2: Write failing launcher tests**

Test static rejection of the legacy crashing MEX hash, unknown MEX hash, missing Q1 receipt, absent source/compiler/runtime provenance, dirty source, wrong commit, wrong case mesh, shared writable roots, non-empty output root, existing MATLAB/FEM process and resume input. In production-mode fixtures, separately test out-of-order role, previous family failure, missing predecessor terminal/c5 evidence and runtime replacement between family members. The launcher must not require the current case's c5 receipt before launch; that receipt is created during the solve and checked by the current case terminal validator.

Add explicit tests that all five preflight-only receipts contain `authorization_scope=preflight_only_non_authorizing` and `dynamic_chain_status=not_evaluated_no_execution`, and that passing any such receipt to production authorization is rejected.

- [ ] **Step 3: Run Python and PowerShell tests and verify RED**

```powershell
python -m pytest tests/test_toy_road_p0_protocol.py -q
powershell -NoProfile -ExecutionPolicy Bypass -File producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadLauncherTest.ps1
```

- [ ] **Step 4: Implement canonical digest construction**

Use UTF-8 canonical JSON:

```python
def canonical_json_sha256(value: Mapping[str, object]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

The family payload includes all shared runtime/environment/cadence/exporter/gate/event/state semantics and the complete predeclared case-axis table. Each case payload contains the family digest plus canonical mesh/recovery/material/loading fields. Role and writable paths belong only to the execution lock.

- [ ] **Step 5: Implement the launcher authorization chain**

The strict chain is:

```text
P0 -> terminal validation
P0R -> terminal validation -> P0/P0R repeatability evidence lock
T1 -> own c5 receipt -> terminal validation
T2 -> validated T1 including T1 c5 receipt -> own validation
T3 -> validated T1+T2 including both c5 receipts -> own validation
```

In production mode, the launcher checks only already completed predecessors: P0 has none; P0R requires validated P0; T1 requires the P0/P0R repeatability evidence lock; T2 requires T1 terminal plus T1 c5 PASS; T3 requires T1 and T2 terminal plus both c5 PASS receipts. The current case's terminal validator later checks its newly produced case-local c5 receipt. A preflight-only receipt is never accepted as predecessor or launch authorization.

Before any production call, require no matching MATLAB/Octave process, exact rebuilt-MEX/Q1 identity, fixed machine/CPU/MATLAB/BLAS/thread provenance, isolated roots and a non-existing output root. Set `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_DYNAMIC=FALSE`. Preflight performs these same static checks but deliberately skips the dynamic chain and records why it was not evaluated.

- [ ] **Step 6: Run launcher/digest tests and verify GREEN**

Run Step 3 commands. Expected: PASS without invoking a real MATLAB solve. Unit fixtures carry `authorization_scope=test_only_non_authorizing`; real preflight receipts carry `authorization_scope=preflight_only_non_authorizing`. Both scopes are explicitly rejected by production mode.

- [ ] **Step 7: Commit locks and launcher**

```powershell
git add producer_handoffs/toy_road_p0_repeatability_20260803 tests/test_toy_road_p0_protocol.py
git commit -m "feat: lock and authorize the P0 family fail closed"
```

### Task 7: Add Result Governance and Immutable Package Finalization

**Files:**
- Create: `docs/toy_road_p0_repeatability_20260802/decision.md`
- Create: `docs/toy_road_p0_repeatability_20260802/_pidl_attempt_ledger/attempts.jsonl`
- Create: `docs/toy_road_p0_repeatability_20260802/attempt.md`
- Modify: `docs/pidl_experiment_inventory.md`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/finalize_toy_road_family_package.m`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/README.md`
- Modify: `producer_handoffs/toy_road_p0_repeatability_20260803/toy_road_protocol.py`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadFinalizeTest.m`
- Modify: `tests/test_toy_road_p0_protocol.py`

**Interfaces:**
- Consumes: one terminal package, execution lock, c5 receipt and canonical attempt record.
- Produces: `TERMINAL_MANIFEST.json`, sorted `SHA256SUMS.txt`, validation summary, append-only attempt ledger/rendered view, and exactly one family registry row.

- [ ] **Step 1: Write failing governance tests**

Assert exactly one primary decision path, exactly one inventory row with case ID `toy_road_p0_repeatability_family_20260802`, append-only ledger behavior, and that P0/P0R are labelled producer qualification rather than independent training/LOTO trajectories.

```python
def test_family_has_one_primary_asset_and_registry_row() -> None:
    assert PRIMARY_DECISION.is_file()
    rows = [line for line in INVENTORY.read_text().splitlines()
            if "toy_road_p0_repeatability_family_20260802" in line]
    assert len(rows) == 1
    assert "synthetic" in rows[0].lower()
```

- [ ] **Step 2: Write failing finalizer tests**

Verify no-clobber behavior, complete shard coverage c1-terminal, exact manifest closure, terminal reason/event consistency, same runtime across family, case-local c5 binding and rejection of an extra unmanifested file.

- [ ] **Step 3: Run governance/finalizer tests and verify RED**

```powershell
python -m pytest tests/test_toy_road_p0_protocol.py -q
matlab -batch "r=runtests('producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadFinalizeTest.m'); assertSuccess(r)"
```

- [ ] **Step 4: Implement finalization and append-only attempt handling**

Use `docs/skills/pidl-experiment-gate/scripts/pidl_attempt_ledger.py` for ledger append/render semantics. Record attempt ID, role, source commit, all three digests, runtime digest, roots, environment fingerprint, start/end state and immutable receipt links. Never rewrite an existing JSONL record.

- [ ] **Step 5: Create the blocked primary decision and single registry row**

Set the initial decision status to `BLOCKED_PENDING_SEALED_PREFLIGHT`; state that execution is not authorized and this is a synthetic FEM transfer family, not real-road validation. Link future case receipts from this one asset rather than creating per-case decisions.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run Step 3 commands. Expected: PASS.

- [ ] **Step 7: Commit result governance**

```powershell
git add docs/toy_road_p0_repeatability_20260802 docs/pidl_experiment_inventory.md producer_handoffs/toy_road_p0_repeatability_20260803 tests/test_toy_road_p0_protocol.py
git commit -m "feat: govern P0 family evidence as one asset"
```

### Task 8: Seal and Run Clean Preflight Without FEM Execution

**Files:**
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/SHA256SUMS.txt`
- Create: `docs/toy_road_p0_repeatability_20260802/preflight_evidence.json`
- Modify: `docs/handovers/windows_fem_outbox.md`
- Modify only when a test exposes a defect: files and tests created in Tasks 1-7.

**Interfaces:**
- Consumes: completed implementation, clean approved runtime and all unit/static tests.
- Produces: one immutable sealed-source commit, then a separate post-preflight evidence commit/tag that references the sealed-source commit without changing sealed handoff bytes; it does not produce P0/P0R/T1/T2/T3 outputs.

- [ ] **Step 1: Run all Python tests**

```powershell
python -m pytest -q
```

Expected: zero failures; record pass/skip counts in the preflight receipt.

- [ ] **Step 2: Run all MATLAB unit tests**

```powershell
matlab -batch "r=runtests('producer_handoffs/toy_road_p0_repeatability_20260803/tests'); assertSuccess(r)"
```

Expected: zero failed or incomplete tests. Controlled doubles must be the only solver calls.

- [ ] **Step 3: Run PowerShell fail-closed tests**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadLauncherTest.ps1
```

Expected: PASS; the test fixture remains `test_only_non_authorizing`.

- [ ] **Step 4: Generate and verify the source manifest**

Hash every consumed source/lock/test/README byte exactly once, excluding `SHA256SUMS.txt` itself. Verify from an LF-preserving temporary clone and require `git diff --check` plus a clean `git status --porcelain` after the manifest commit.

- [ ] **Step 5: Commit and push the sealed source, then verify a fresh checkout**

```powershell
git add producer_handoffs/toy_road_p0_repeatability_20260803
git commit -m "build: seal P0 family producer source"
git push origin HEAD:codex/toy-road-evidence-integration
git -c core.autocrlf=false clone --branch codex/toy-road-evidence-integration --single-branch `
  https://github.com/wenniebyfoxmail/phase-field-fracture-fatigue-pidl.git `
  C:\q4diag\phase-field-fracture-fatigue-pidl-p0-sealed
```

Record this full commit as `SEALED_SOURCE_COMMIT`. Require fresh-checkout `HEAD==SEALED_SOURCE_COMMIT`, empty status and complete source-manifest verification. All preflight probes in Step 6 run from this checkout.

- [ ] **Step 6: Execute preflight-only runtime qualification**

Invoke `launch_toy_road_family_case.ps1 -PreflightOnly` for each role using distinct absent output/work/TEMP/cache paths. It may call `which`, hash files, validate Q1 receipts and load contracts, but it must not call recovery, construct `System`, enter Newton or create a cycle shard. Require five static-preflight PASS receipts with one shared family digest, P0=P0R case digest, three declared variant digests, unique execution-lock digests, `authorization_scope=preflight_only_non_authorizing` and `dynamic_chain_status=not_evaluated_no_execution`. Do not require repeatability or predecessor terminal evidence during preflight.

- [ ] **Step 7: Publish and push a separate post-preflight evidence commit/tag**

Write `preflight_evidence.json` with `SEALED_SOURCE_COMMIT`, runtime/API hashes, Python/MATLAB/PowerShell results, five receipt hashes and the two non-authorizing status fields. Append the same evidence summary to `windows_fem_outbox.md`. Do not modify any byte under `producer_handoffs/toy_road_p0_repeatability_20260803/`.

```powershell
git add docs/toy_road_p0_repeatability_20260802/preflight_evidence.json `
  docs/handovers/windows_fem_outbox.md
git commit -m "docs: record P0 producer sealed preflight"
git tag toy-road-p0-producer-preflight-20260803
git push origin HEAD:codex/toy-road-evidence-integration
git push origin toy-road-p0-producer-preflight-20260803
git status --porcelain
```

Require the final status output to be empty and remote branch/tag hashes to match local values. Keep `decision.md` at `BLOCKED_PENDING_EXECUTION_AUTHORIZATION`. The production launcher remains locked to `SEALED_SOURCE_COMMIT`, not the later evidence commit, and must reject every preflight-only receipt as authorization. Do not launch P0; execution requires a separate explicit approval after this sealed preflight is reviewed.
