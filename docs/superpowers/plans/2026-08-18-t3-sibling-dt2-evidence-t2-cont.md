# T3 Sibling, Compact D-T2 Evidence, and T2-CONT Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish compact D-T2 evidence, re-seal and run exactly one independent T3 sibling after the machine becomes idle, and implement—but do not execute—a c5/s4-only adaptive `Gc` continuation diagnostic.

**Architecture:** Keep the original T2 and D-T2 run trees immutable. Build compact evidence by hashing the external D-T2 run, launch T3 from the exact sealed producer identity through a minimal sibling wrapper, and isolate T2-CONT in a diagnostic overlay with its own stage controller and validator. T3 is the only FEM experiment authorized by this plan; T2-CONT stops at tested tooling.

**Tech Stack:** Python 3.12, pytest, MATLAB R2025b, PowerShell, HDF5/h5py, Git/Git LFS, existing toy-road MATLAB producer.

## Global Constraints

- Preserve P0, P0R, T1, original T2, and D-T2 run outputs byte-for-byte.
- Original T2 remains `FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE_AT_C5_S4`; never classify it as Newton failure.
- Run only one MATLAB/FEM experiment at a time; never stop the currently running computation without explicit user approval.
- T3 depends directly on P0/P0R repeatability PASS, not on T1 or T2 success.
- T3 changes only `loading.blocks`; mesh, material, recovery, event, runtime, MEX, threads, solver, and thresholds remain sealed.
- T3 uses fresh, disjoint roots and does not resume or launch a follow-on case.
- T2-CONT uses `Gc(lambda)=0.010-0.002*lambda` at frozen T2 c5/s4; it adds no relaxation, Aitken, mixing, or line search.
- Keep the 1000-stagger cap and four gates exactly at `4e-4`, `4e-4`, `1e-3`, and `1e-12`.
- Do not execute T2-CONT, a relaxation sweep, or a complete T2 trajectory under this plan.

---

### Task 1: Compact D-T2 evidence builder

**Files:**
- Modify: `analysis/toy_road_dt2_diagnostic_20260817/analyze_dt2_c5_iterates.py`
- Create: `analysis/toy_road_dt2_diagnostic_20260817/build_dt2_compact_package.py`
- Modify: `tests/test_toy_road_dt2_diagnostic.py`
- Create: `tests/test_toy_road_dt2_compact_package.py`
- Create at build time: `docs/toy_road_p0_repeatability_20260802/dt2_c5_diagnostic_compact_20260818/`

**Interfaces:**
- Consumes: `analyze(run_root: Path, output_root: Path) -> dict[str, object]` and the immutable external run `C:\q4diag\toy-road-dt2-c5-diagnostic-5629525-run2`.
- Produces: `build_compact_package(run_root: Path, analysis_root: Path, destination: Path) -> dict[str, object]` plus `DIAGNOSTIC_SUMMARY.json`, three CSV tables, `SOURCE_BINDINGS.json`, `DECISION.md`, and `SHA256SUMS.txt`.

- [ ] **Step 1: Write failing analyzer API and compact-package tests**

```python
def test_compact_package_binds_large_iterates_without_copying(tmp_path):
    result = module.build_compact_package(run, analysis, tmp_path / "compact")
    assert result["classification"] == "NONPERIODIC_NONCONTRACTION"
    assert result["completed_rows"] == 1000
    assert result["completed_cycle_shards"] == 4
    assert result["source_bindings"]["DT2_C5_ITERATES.mat"]["sha256"] == sha256(iterates)
    assert not list((tmp_path / "compact").rglob("*.mat"))

def test_analyzer_exposes_callable_api(tmp_path):
    summary = analyzer.analyze(run, tmp_path / "analysis")
    assert summary["definitions"]["tot_en"].startswith("auxiliary")
```

- [ ] **Step 2: Run the focused tests and confirm RED**

Run: `py -3 -m pytest tests/test_toy_road_dt2_diagnostic.py tests/test_toy_road_dt2_compact_package.py -q`

Expected: FAIL because `analyze()` and `build_compact_package()` do not exist.

- [ ] **Step 3: Refactor the existing analyzer and implement the create-once builder**

```python
def analyze(run_root: Path, output_root: Path) -> dict[str, object]:
    # Existing read-only HDF5 analysis body; reject output_root inside run_root.
    # Return the exact summary written to diagnostic_summary.json.

def build_compact_package(run_root: Path, analysis_root: Path,
                          destination: Path) -> dict[str, object]:
    if destination.exists():
        raise FileExistsError(destination)
    # Validate RUN_RESULT, 1000 trace rows, completed_rows, four shards.
    # Copy only compact JSON/CSV/source evidence; hash but never copy .mat files.
```

- [ ] **Step 4: Run focused and repository Python tests**

Run: `py -3 -m pytest tests/test_toy_road_dt2_diagnostic.py tests/test_toy_road_dt2_compact_package.py tests/test_toy_road_t2_failure_package.py -q`

Expected: PASS.

- [ ] **Step 5: Build the real compact package and verify source-run immutability**

Run the analyzer into a fresh external root, record SHA-256 for every original run file before and after, then build the repository package. Compare the two inventories byte-for-byte; expected: no changed original-run digest and no `.mat` inside the compact package.

- [ ] **Step 6: Commit and push compact D-T2 evidence**

```powershell
git add analysis/toy_road_dt2_diagnostic_20260817 tests/test_toy_road_dt2_diagnostic.py tests/test_toy_road_dt2_compact_package.py docs/toy_road_p0_repeatability_20260802/dt2_c5_diagnostic_compact_20260818
git commit -m "evidence: publish compact D-T2 diagnostics"
git push origin codex/toy-road-evidence-producer
```

Expected: pushed commit binds the external 3.1 GiB iterate file without adding it.

### Task 2: Sibling graph and T3 seal

**Files:**
- Create: `analysis/toy_road_t3_sibling_20260818/T3_SIBLING_CONTRACT.json`
- Create: `analysis/toy_road_t3_sibling_20260818/build_t3_sibling_seal.py`
- Create: `analysis/toy_road_t3_sibling_20260818/launch_t3_sibling.py`
- Create: `tests/test_toy_road_t3_sibling.py`

**Interfaces:**
- Consumes: P0/P0R adjudication receipt, `CASE_PHYSICS_CONTRACTS.json`, sealed producer source identity `7c56ff383187cdee2f45e1b15d707f148f386302`, runtime lock, and the canonical `launch_toy_road_family_case.ps1`.
- Produces: `build_seal(repo_root: Path, p0r_adjudication_path: Path, destination: Path) -> dict[str, object]`, `matlab_processes() -> list[dict[str, object]]`, and `launch_t3(repo_root: Path, sealed_source_root: Path, seal_path: Path, run_root: Path, writable_roots: dict[str, Path], matlab: Path) -> subprocess.Popen[bytes]`.

- [ ] **Step 1: Write failing sibling-closure tests**

```python
def test_t3_predecessor_is_p0r_not_t2(tmp_path):
    seal = module.build_seal(fixture, tmp_path / "seal")
    assert seal["predecessor_gate"] == "P0_P0R_REPEATABILITY_PASS"
    assert seal["siblings"] == ["T1_initial_defect", "T2_material_state", "T3_loading_history"]
    assert "T2_terminal_manifest_sha256" not in seal

def test_t3_changes_only_loading_blocks(tmp_path):
    assert seal["changed_axes"] == ["loading.blocks"]
    assert seal["case_physics_contract_sha256"] == "fbbe2c46ec394f20589e7c150783a08b5fbd79d13e51ce74eef90930def0146c"

def test_launcher_refuses_busy_matlab_and_existing_roots(monkeypatch, tmp_path):
    monkeypatch.setattr(module, "matlab_processes", lambda: [{"pid": 1}])
    roots = {name: tmp_path / name for name in ("output", "work", "temp", "tmp", "pref", "cache", "matlab_startup_pref")}
    with pytest.raises(module.BusyExperimentError):
        module.launch_t3(tmp_path / "repo", tmp_path / "sealed", tmp_path / "seal.json",
                         tmp_path / "run", roots, tmp_path / "matlab.exe")
```

- [ ] **Step 2: Run the focused tests and confirm RED**

Run: `py -3 -m pytest tests/test_toy_road_t3_sibling.py -q`

Expected: FAIL because the sibling seal and launcher do not exist.

- [ ] **Step 3: Implement strict sibling contract and seal**

The contract must state:

```json
{
  "schema_version": "toy_road_t3_sibling_contract_v1",
  "predecessor_gate": "P0_P0R_REPEATABILITY_PASS",
  "case_id": "T3_loading_history",
  "changed_axes": ["loading.blocks"],
  "resume_allowed": false,
  "follow_on_authorized": false
}
```

`build_seal()` must use strict JSON reads, compare the full T3 physics object to P0 after deleting only `loading.blocks`, bind source/runtime/MEX/thread identities, and create files with exclusive `xb` writes.

- [ ] **Step 4: Implement the minimal one-case launcher**

`launch_t3()` must refuse any MATLAB process, require seven absent/disjoint writable roots, create exactly one execution lock/receipt, and call the unchanged canonical PowerShell launcher with `-Role T3_loading_history`, empty `-ResumeFrom`, and sealed source/runtime arguments. It must not contain T1, T2, T2-CONT, retry, or follow-on launch code.

- [ ] **Step 5: Run tests and static boundary scans**

Run: `py -3 -m pytest tests/test_toy_road_t3_sibling.py tests/test_toy_road_p0_protocol.py -q`

Run: `rg -n "T2-CONT|T2_material_state|resume|retry" analysis/toy_road_t3_sibling_20260818/launch_t3_sibling.py`

Expected: tests PASS; only explicit rejection/empty-resume assertions may match the scan.

- [ ] **Step 6: Commit the T3 sibling seal and launcher**

```powershell
git add analysis/toy_road_t3_sibling_20260818 tests/test_toy_road_t3_sibling.py
git commit -m "feat: seal T3 as independent sibling"
```

### Task 3: T2-CONT diagnostic-only controller (do not execute)

**Files:**
- Create: `analysis/toy_road_t2_cont_20260818/T2_CONT_CONTRACT.json`
- Create: `analysis/toy_road_t2_cont_20260818/continuation_controller.py`
- Create: `analysis/toy_road_t2_cont_20260818/overlay/run_t2_cont_c5_only.m`
- Create: `analysis/toy_road_t2_cont_20260818/overlay/ToyRoadT2ContTrace.m`
- Create: `analysis/toy_road_t2_cont_20260818/validate_t2_cont_stage.py`
- Create: `tests/test_toy_road_t2_cont.py`

**Interfaces:**
- Consumes: frozen T2 c5/s4 entry `(u, d, d_lb, history_pre, traction, active_dofs)` and a stage callback `solve_stage(gc: float, accepted_state: State) -> StageResult`.
- Produces: `run_controller(solve_stage, accepted_state, contract) -> ContinuationResult` and diagnostic-only attempt receipts.

- [ ] **Step 1: Write failing pure-controller tests**

```python
def test_controller_rejects_rolls_back_and_halves():
    result = run_controller(scripted_solver([PASS_250, FAIL, PASS_500, PASS_TARGET]), state, contract)
    assert result.attempts[1].rollback_sha256 == result.attempts[1].start_sha256
    assert result.attempts[2].step == result.attempts[1].step / 2

def test_pass_requires_exact_target_and_original_gates():
    assert classify(stage(gc=0.008, u=4e-4, kkt=4e-4, delta=1e-3, primal=1e-12)) == "PASS_TARGET_C5_S4_ONLY_NEEDS_SEPARATE_FULL_T2_AUTHORIZATION"
    assert classify(stage(gc=0.008, delta=1.000001e-3)).startswith("FAIL_")

def test_no_trajectory_capability():
    text = MATLAB_RUNNER.read_text()
    for forbidden in ("commit_history", "substep_ordinal = 5", "cycle_0005", "advance_toy_road_event", "finalize_toy_road_family_package"):
        assert forbidden not in text
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `py -3 -m pytest tests/test_toy_road_t2_cont.py -q`

Expected: FAIL because the controller, validator, contract, and MATLAB overlay do not exist.

- [ ] **Step 3: Implement the pure adaptive controller**

Use `lambda=0`, `step=1/4`, `min_step=1/128`, `max_attempts=24`, and `gc=0.010-0.002*lambda`. Accept only the unchanged four gates. On PASS with stagger count `<=250`, double; `251..750`, retain; `>750`, halve. On rejection, restore the byte-hashed accepted state and halve. Never use `tot_en` or the offline objective as controller inputs.

- [ ] **Step 4: Implement the isolated MATLAB c5 entry/stage adapter**

The adapter must reproduce T2 only through c5/s3, freeze entry data, solve the `lambda=0` anchor, and expose one stage call without modifying `solve_toy_road_family_case.m` or `ToyRoadC5Trace.m`. Every attempt writes to a create-once `attempt_XXXX` directory and stops before history commit, s5, cycle export, event advancement, or terminal trajectory finalization.

- [ ] **Step 5: Implement the separate stage validator and attempt ledger**

The validator records `lambda`, `Gc`, step, start/end hashes, outcome, stagger rows, raw phase residual, displacement residual, projected KKT, consecutive damage infinity norm, primal feasibility, and rollback integrity. Equality tests must bind its four constants to the sealed `ToyRoadC5Trace` constants.

- [ ] **Step 6: Run focused tests and forbidden-token checks**

Run: `py -3 -m pytest tests/test_toy_road_t2_cont.py tests/test_toy_road_dt2_diagnostic.py -q`

Run: `rg -ni "omega|aitken|relax|line.search|commit_history|cycle_0005" analysis/toy_road_t2_cont_20260818`

Expected: tests PASS; forbidden tokens appear only in contract rejection text/tests, never executable solver logic.

- [ ] **Step 7: Commit tooling without launching MATLAB**

```powershell
git add analysis/toy_road_t2_cont_20260818 tests/test_toy_road_t2_cont.py
git commit -m "diagnostic: add c5-only adaptive Gc continuation"
```

Expected: no T2-CONT run root, PID, MATLAB log, or execution receipt is created.

### Task 4: Idle-gated single T3 launch

**Files:**
- Create outside repository at launch time: `C:\q4diag\toy-road-t3-production-7c56ff3-run1\`
- Create outside repository: one minimal consumed T3 execution receipt and wrapper package.
- Do not modify repository source in this task.

**Interfaces:**
- Consumes: committed/pushed Task 1-2 code, the sibling seal, exact sealed producer worktree/source, and an idle process check.
- Produces: one running T3 MATLAB process or a no-launch busy status.

- [ ] **Step 1: Inspect MATLAB/FEM processes without changing them**

Run: `Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^MATLAB' } | Select-Object ProcessId,Name,CreationDate,CommandLine`

Expected while busy: report the existing process and do not create any T3 root.

- [ ] **Step 2: At idle, verify committed code and exact sealed identities**

Run the complete Python test subset from Tasks 1-3, `git diff --check`, `git status --porcelain`, source-manifest verification, P0/P0R adjudication validation, and T3 physics projection comparison. Expected: all PASS and clean worktree.

- [ ] **Step 3: Perform final process check immediately before launch**

Repeat the CIM query in the same launcher call. If any MATLAB process appears, return `BUSY_NO_LAUNCH` and leave all T3 roots absent.

- [ ] **Step 4: Launch exactly one T3**

Call `launch_t3_sibling.py` once with fresh roots under `C:\q4diag\toy-road-t3-production-7c56ff3-run1`. Expected: one MATLAB parent/worker pair, `case_id=T3_loading_history`, empty stderr at startup, and no T2-CONT process.

- [ ] **Step 5: Record launch state and create a progress monitor**

Monitor process identity, completed cycle-shard count, stdout/stderr, c5 receipt, first-hit/confirmation state, and terminal files. Do not retry automatically and do not start any other experiment.

### Task 5: T3 terminal validation and seal

**Files:**
- Create after termination: `docs/toy_road_p0_repeatability_20260802/t3_loading_history_terminal_20260818/`
- Create: `analysis/toy_road_t3_sibling_20260818/build_t3_terminal_package.py`
- Modify: `tests/test_toy_road_t3_sibling.py`

**Interfaces:**
- Consumes: the completed T3 run and existing terminal/package validator.
- Produces: immutable T3 terminal dossier and PASS/FAIL classification; no authorization capability.

- [ ] **Step 1: Write failing terminal-package closure tests**

Test complete and failed synthetic T3 runs for create-once output, manifest/SHA closure, sibling predecessor binding, exact shard inventory, c5 receipt, event state, runtime/source identities, and absence of follow-on authorization.

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `py -3 -m pytest tests/test_toy_road_t3_sibling.py -q`

Expected: FAIL because `build_t3_terminal_package()` does not exist.

- [ ] **Step 3: Implement terminal builder and external validation call**

The builder copies T3-owned terminal evidence only, rehashes after copy, invokes the existing terminal/package validator, records whether the result is event-confirmed or right-censored, and never writes an execution authorization field.

- [ ] **Step 4: After MATLAB exits, validate and build the real package**

Expected: terminal validator PASS for structural/runtime/package integrity even if the scientific trajectory is right-censored; scientific outcome reported separately from runtime/validation status.

- [ ] **Step 5: Run regression tests, commit, and push**

```powershell
py -3 -m pytest tests/test_toy_road_t3_sibling.py tests/test_toy_road_p0_protocol.py -q
git add analysis/toy_road_t3_sibling_20260818 tests/test_toy_road_t3_sibling.py docs/toy_road_p0_repeatability_20260802/t3_loading_history_terminal_20260818
git commit -m "evidence: seal T3 loading-history sibling"
git push origin codex/toy-road-evidence-producer
```

Expected: remote branch contains compact D-T2 evidence, sibling contract, non-executed T2-CONT tooling, and the sealed T3 result.
