# T3-rev Dose-Matched Reversed-Order Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, qualify, launch exactly once, and terminally adjudicate a complete `T3_rev_loading_order` sibling that reverses T3's first two loading blocks without mutating the sealed base producer or changing numerical algorithms.

**Architecture:** Generate a create-once MATLAB/Python extension overlay from the byte-preserved T3 producer, with exact patch-count checks, a composite source manifest, and a classified source-diff inventory. The launcher resolves the extension before the sealed base, binds a new producer identity honestly, retains the qualified runtime/MEX/thread identities, and refuses busy, resume, retry, or follow-on execution. A predeclared offline analyzer compares T3 and T3-rev after the nominally dose-matched c60 boundary.

**Tech Stack:** Python 3, pytest, MATLAB R2025b Update 5, MATLAB Unit Test, canonical JSON, SHA-256, existing Toy Road MATLAB producer and terminal protocol.

**Spec:** `docs/superpowers/specs/2026-08-24-t3-rev-dose-matched-reversed-order-design.md`

## Global Constraints

- Preserve `producer_handoffs/toy_road_p0_repeatability_20260803` and all P0/P0R/T1/T2/T3 outputs byte-for-byte.
- Base producer commit is `7c56ff383187cdee2f45e1b15d707f148f386302` and base source-manifest SHA-256 is `61e12721da19ce37c2f065804d2a151b6bd80981196687f6f3fe292dca48b89e`.
- T3-rev blocks are exactly `[[1,30,0.126],[31,60,0.108],[61,150,0.120]]`.
- The new case id is exactly `T3_rev_loading_order`; relative to P0 and T3, the only physical changed leaf is `loading.blocks`.
- Keep MATLAB R2025b Update 5, PCWIN64, four MEX hashes, runtime lock, mesh, material, recovery, event, Newton, 1000-stagger cap, and all four external c5 gates unchanged.
- No relaxation, continuation, line search, tolerance widening, resume, retry, or automatic follow-on case.
- No MATLAB/FEM experiment may overlap T3-rev. The launcher performs a busy check before creating the run root and a second check immediately before `Popen`.
- Before every MATLAB unit-test command, check `Get-CimInstance Win32_Process` for an existing MATLAB/FEM process and defer the test unchanged while the machine is busy.
- A completed c150 trajectory without confirmed fracture is a valid physical result; numerical and runtime failures remain distinct.
- The Mac review receipt and analysis receipts are non-authorizing.

---

### Task 1: Archive the independent review and qualified trajectory registry

**Files:**
- Create: `docs/toy_road_p0_repeatability_20260802/t3_loading_history_20260818/T3_INDEPENDENT_REVIEW_RECEIPT_20260821.md`
- Create: `docs/toy_road_p0_repeatability_20260802/QUALIFIED_TRAJECTORY_REGISTRY_20260824.json`
- Modify: `docs/artifact_index.md`
- Test: `tests/test_toy_road_t3_rev.py`

**Interfaces:**
- Consumes: Mac receipt text supplied in this task and Git/OneDrive bindings already published at commit `7496f34`.
- Produces: `load_registry(path: Path) -> dict[str, object]` test fixture data and a non-authorizing predecessor record consumed by the seal builder.

- [ ] **Step 1: Write the failing evidence-archive test**

```python
def test_t3_review_and_trajectory_registry_are_non_authorizing() -> None:
    receipt = (ROOT / "docs/toy_road_p0_repeatability_20260802/"
               "t3_loading_history_20260818/"
               "T3_INDEPENDENT_REVIEW_RECEIPT_20260821.md").read_text()
    registry = strict_json(REGISTRY)
    assert "PASS, with one provenance-layer discrepancy disclosed" in receipt
    assert "97/97" in receipt and "2,960,514,298" in receipt
    assert "LOCAL_MIRROR_NOT_YET_BUILT" in receipt
    assert "ONEDRIVE_UPLOAD_VERIFIED" in receipt
    assert registry["authorization_capability"] is None
    assert registry["trajectories"]["P0_parent"]["status"] == "QUALIFIED"
    assert registry["trajectories"]["T1_initial_defect"]["status"] == "QUALIFIED"
    assert registry["trajectories"]["T3_loading_history"]["status"] == "QUALIFIED"
    assert registry["trajectories"]["T2_material_state"]["status"] == \
        "FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE_AT_C5_S4"
```

- [ ] **Step 2: Run the archive test and verify the missing files fail**

Run: `py -3 -m pytest tests/test_toy_road_t3_rev.py::test_t3_review_and_trajectory_registry_are_non_authorizing -v`

Expected: FAIL with `FileNotFoundError` for the review receipt.

- [ ] **Step 3: Add the verbatim receipt and strict registry**

Write the supplied receipt without rewriting its two disclosed limitations. Create the registry with this exact outer schema:

```json
{
  "schema_version": "toy_road_qualified_trajectory_registry_v1",
  "status": "PASS",
  "authorization_capability": null,
  "trajectories": {
    "P0_parent": {"status": "QUALIFIED", "first_hit": 70, "confirmed": 73},
    "T1_initial_defect": {"status": "QUALIFIED"},
    "T2_material_state": {"status": "FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE_AT_C5_S4", "cycle": 5, "substep": 4},
    "T3_loading_history": {"status": "QUALIFIED", "first_hit": 68, "confirmed": 71, "terminal_manifest_sha256": "455b149b14276598ad87e4bcea6b6a2916de6e59d3812f791d66e61b1344bb01"}
  }
}
```

Add an `External / Producer Artifacts` row to `docs/artifact_index.md` pointing to the OneDrive manifest directory and the archived review.

- [ ] **Step 4: Run the archive test**

Run: `py -3 -m pytest tests/test_toy_road_t3_rev.py::test_t3_review_and_trajectory_registry_are_non_authorizing -v`

Expected: PASS.

- [ ] **Step 5: Commit the evidence archive**

```powershell
git add docs/artifact_index.md docs/toy_road_p0_repeatability_20260802 tests/test_toy_road_t3_rev.py
git commit -m "docs: archive independent T3 review"
```

### Task 2: Generate the minimal case-definition extension with strict source closure

**Files:**
- Create: `analysis/toy_road_t3_rev_20260824/__init__.py`
- Create: `analysis/toy_road_t3_rev_20260824/T3_REV_CONTRACT.json`
- Create: `analysis/toy_road_t3_rev_20260824/build_t3_rev_extension.py`
- Modify: `tests/test_toy_road_t3_rev.py`

**Interfaces:**
- Consumes: `build_extension(base_root: Path, destination: Path, repo_commit: str) -> dict[str, object]` inputs.
- Produces: a create-once extension root containing patched MATLAB/Python role files, strict family/case contracts, `EXTENSION_SOURCE_MANIFEST.json`, and `SOURCE_DIFF_INVENTORY.json`.

- [ ] **Step 1: Write failing tests for exact loading, role closure, and base preservation**

```python
def test_extension_adds_only_t3_rev_and_preserves_base(tmp_path: Path) -> None:
    module = load_module("build_t3_rev_extension")
    before = module.inventory_tree(BASE)
    result = module.build_extension(BASE, tmp_path / "extension", "a" * 40)
    after = module.inventory_tree(BASE)
    assert before == after
    assert result["case_id"] == "T3_rev_loading_order"
    assert result["loading_blocks"] == [[1, 30, 0.126], [31, 60, 0.108], [61, 150, 0.120]]
    assert result["base_source_manifest_sha256"] == \
        "61e12721da19ce37c2f065804d2a151b6bd80981196687f6f3fe292dca48b89e"
    assert set(result["changed_source_files"]) == set(module.ALLOWED_SHADOW_FILES)

def test_extension_rejects_duplicate_json_and_unexpected_base_text(tmp_path: Path) -> None:
    module = load_module("build_t3_rev_extension")
    bad = tmp_path / "base"
    shutil.copytree(BASE, bad)
    path = bad / "build_toy_road_family_case.m"
    path.write_text(path.read_text().replace("T3_loading_history", "T3_changed", 1))
    with pytest.raises(module.ExtensionError, match="base source identity|exact patch count"):
        module.build_extension(bad, tmp_path / "extension", "a" * 40)

@pytest.mark.parametrize("bad_payload", [
    '{"case_id":"T3_rev_loading_order","case_id":"duplicate"}',
    '{"loading_blocks":NaN}',
    '{"resume_allowed":0}',
])
def test_extension_contract_rejects_noncanonical_json(tmp_path: Path, bad_payload: str) -> None:
    module = load_module("build_t3_rev_extension")
    path = tmp_path / "bad.json"
    path.write_text(bad_payload)
    with pytest.raises(module.ExtensionError):
        module.read_strict_contract(path)
```

- [ ] **Step 2: Run the tests and verify the module is absent**

Run: `py -3 -m pytest tests/test_toy_road_t3_rev.py -k "extension" -v`

Expected: FAIL while loading `build_t3_rev_extension.py`.

- [ ] **Step 3: Define the immutable extension contract**

Create `T3_REV_CONTRACT.json` as canonical strict JSON:

```json
{"authorization_capability":null,"base_source_commit":"7c56ff383187cdee2f45e1b15d707f148f386302","base_source_manifest_sha256":"61e12721da19ce37c2f065804d2a151b6bd80981196687f6f3fe292dca48b89e","case_id":"T3_rev_loading_order","changed_axes":["loading.blocks"],"follow_on_authorized":false,"loading_blocks":[[1,30,0.126],[31,60,0.108],[61,150,0.12]],"resume_allowed":false,"schema_version":"toy_road_t3_rev_contract_v1"}
```

- [ ] **Step 4: Implement strict extension generation**

Use exact-match replacements that each require `count == 1`; never use broad regular-expression rewriting. Define the shadow allowlist exactly:

```python
ALLOWED_SHADOW_FILES = (
    "build_toy_road_family_case.m",
    "main_toy_road_family_case.m",
    "private/run_toy_road_driver_core.m",
    "run_toy_road_controlled_driver_harness.m",
    "solve_toy_road_family_case.m",
    "ToyRoadC5Trace.m",
    "toy_road_protocol.py",
    "FAMILY_CONTRACT.json",
    "CASE_PHYSICS_CONTRACTS.json",
)

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise ExtensionError(f"exact patch count differs for {label}")
    return text.replace(old, new, 1)
```

For MATLAB role arrays append `'T3_rev_loading_order'`. In `build_toy_road_family_case.m`, add:

```matlab
elseif strcmp(caseId, 'T3_rev_loading_order')
    loading.blocks = [1 30 0.126; 31 60 0.108; 61 150 0.120];
    changedAxes = {'loading.blocks'};
```

For Python, append `"T3_rev_loading_order"` to `FAMILY_ROLES`, map it to `["loading.blocks"]`, and change the two stale error messages from “exactly five roles” to “exactly six roles”. Generate family/case JSON through parsed mappings, recompute the canonical family SHA-256 and all six case SHA-256 values, and validate them using the generated `toy_road_protocol.py`.

Write `SOURCE_DIFF_INVENTORY.json` with one entry per allowlisted file and one of these classifications only: `case_registration`, `loading_block_definition`, `contract_data`, `role_allowlist`. Write `EXTENSION_SOURCE_MANIFEST.json` using create-new I/O and bind `repo_commit`, base manifest SHA-256, every shadow file SHA-256, contract SHA-256, and diff-inventory SHA-256.

- [ ] **Step 5: Run extension tests**

Run: `py -3 -m pytest tests/test_toy_road_t3_rev.py -k "extension" -v`

Expected: PASS.

- [ ] **Step 6: Commit the extension generator**

```powershell
git add analysis/toy_road_t3_rev_20260824 tests/test_toy_road_t3_rev.py
git commit -m "feat: add audited T3-rev producer extension"
```

### Task 3: Prove MATLAB case equivalence and unchanged numerical formulas

**Files:**
- Create: `analysis/toy_road_t3_rev_20260824/tests/t3RevExtensionTest.m`
- Create: `analysis/toy_road_t3_rev_20260824/verify_extension_diff.py`
- Modify: `tests/test_toy_road_t3_rev.py`

**Interfaces:**
- Consumes: generated extension root and sealed base root.
- Produces: `verify_extension_diff(base_root: Path, extension_root: Path) -> dict[str, object]` and MATLAB test results proving old-case equality and new-case blocks.

- [ ] **Step 1: Write failing Python formula-closure tests**

```python
def test_diff_verifier_rejects_algorithm_change(tmp_path: Path) -> None:
    builder = load_module("build_t3_rev_extension")
    verify = load_module("verify_extension_diff")
    ext = tmp_path / "extension"
    builder.build_extension(BASE, ext, "a" * 40)
    solver = ext / "solve_toy_road_family_case.m"
    solver.write_text(solver.read_text().replace("1000", "1001", 1))
    with pytest.raises(verify.DiffError, match="unclassified|numerical"):
        verify.verify_extension_diff(BASE, ext)
```

- [ ] **Step 2: Run the closure test and verify failure**

Run: `py -3 -m pytest tests/test_toy_road_t3_rev.py::test_diff_verifier_rejects_algorithm_change -v`

Expected: FAIL because `verify_extension_diff.py` is absent.

- [ ] **Step 3: Implement token-level classified diff verification**

The verifier must require all changed hunks to match the exact role or loading-block insertions emitted by Task 2. It must also hash-compare the unchanged numerical dependencies recorded by the T3 terminal manifest:

```python
UNCHANGED_IDENTITY_FIELDS = (
    "solver_sha256", "recovery_sha256", "exporter_sha256",
    "numerical_gate_contract_sha256", "event_contract_sha256",
)

def verify_extension_diff(base_root: Path, extension_root: Path) -> dict[str, object]:
    manifest = strict_json(extension_root / "EXTENSION_SOURCE_MANIFEST.json")
    inventory = strict_json(extension_root / "SOURCE_DIFF_INVENTORY.json")
    require_exact_shadow_set(manifest, ALLOWED_SHADOW_FILES)
    require_classified_hunks(base_root, extension_root, inventory)
    return {"status": "PASS", "numerical_algorithm_changed": False,
            "allowed_shadow_files": list(ALLOWED_SHADOW_FILES)}
```

- [ ] **Step 4: Add MATLAB value-equivalence tests**

The MATLAB test generates canonical mesh input once, calls the base builder for each legacy role, removes function handles before comparison, clears the function cache, puts the extension first on `path`, and calls the extension builder:

```matlab
legacy = {'P0_parent','P0R_parent_repeat','T1_initial_defect', ...
    'T2_material_state','T3_loading_history'};
for index = 1:numel(legacy)
    baseCfg = buildFromRoot(baseRoot, legacy{index}, mesh);
    extCfg = buildFromRoot(extensionRoot, legacy{index}, mesh);
    verifyEqual(testCase, stripHandles(extCfg), stripHandles(baseCfg));
end
rev = buildFromRoot(extensionRoot, 'T3_rev_loading_order', mesh);
verifyEqual(testCase, rev.case_physics.loading.blocks, ...
    [1 30 0.126; 31 60 0.108; 61 150 0.120]);
verifyEqual(testCase, rev.changed_axes, {'loading.blocks'});
```

Add tests that construct `ToyRoadC5Trace` for T3-rev and compare its four threshold values/formulas with the base T3 trace.

- [ ] **Step 5: Run Python and MATLAB extension qualification**

Run: `py -3 -m pytest tests/test_toy_road_t3_rev.py -k "diff or equivalence" -v`

Run: `matlab -batch "r=run(testsuite('analysis/toy_road_t3_rev_20260824/tests/t3RevExtensionTest.m')); assertSuccess(r);"`

Expected: both PASS; no FEM trajectory is launched.

- [ ] **Step 6: Commit extension qualification**

```powershell
git add analysis/toy_road_t3_rev_20260824 tests/test_toy_road_t3_rev.py
git commit -m "test: qualify T3-rev case extension"
```

### Task 4: Build the non-reusable T3-rev seal

**Files:**
- Create: `analysis/toy_road_t3_rev_20260824/build_t3_rev_seal.py`
- Modify: `tests/test_toy_road_t3_rev.py`

**Interfaces:**
- Consumes: `build_seal(repo_root: Path, extension_root: Path, t3_adjudication: Path, review_receipt: Path, registry: Path, destination: Path) -> dict[str, object]`.
- Produces: create-once `T3_REV_SEAL.json` binding predecessor evidence, composite source identity, exact physics, runtime identities, and exactly one launch capability.

- [ ] **Step 1: Write failing seal tests**

```python
def test_seal_binds_extension_and_exactly_one_case(tmp_path: Path) -> None:
    seal = build_test_seal(tmp_path)
    assert seal["case_id"] == "T3_rev_loading_order"
    assert seal["authorization_capability"] == "exactly_one_T3_rev_loading_order_execution"
    assert seal["resume_allowed"] is False
    assert seal["follow_on_authorized"] is False
    assert seal["extension_identity"]["base_source_commit"] == \
        "7c56ff383187cdee2f45e1b15d707f148f386302"
    assert seal["physics_closure"]["only_loading_blocks_differ"] is True
    assert seal["physics_closure"]["first_60_histogram_equal_to_t3"] is True

def test_seal_rejects_authorizing_review_receipt(tmp_path: Path) -> None:
    with pytest.raises(SealError, match="review receipt is non-authorizing"):
        build_test_seal(tmp_path, injected_review_authorization=True)
```

- [ ] **Step 2: Run seal tests and verify failure**

Run: `py -3 -m pytest tests/test_toy_road_t3_rev.py -k "seal" -v`

Expected: FAIL while loading `build_t3_rev_seal.py`.

- [ ] **Step 3: Implement strict predecessor and identity binding**

Require T3 adjudication `PASS_T3_LOADING_HISTORY_SIBLING_TERMINAL_PACKAGE`, terminal manifest `455b149b14276598ad87e4bcea6b6a2916de6e59d3812f791d66e61b1344bb01`, registry statuses from Task 1, extension verifier PASS, clean repository commit, and exact runtime/MEX/thread identities from T3. The seal payload must include:

```python
seal = {
    "schema_version": "toy_road_t3_rev_seal_v1",
    "status": "PASS",
    "case_id": "T3_rev_loading_order",
    "authorization_capability": "exactly_one_T3_rev_loading_order_execution",
    "resume_allowed": False,
    "follow_on_authorized": False,
    "extension_identity": extension_identity,
    "predecessor_evidence": predecessor_evidence,
    "physics_closure": physics_closure,
    "runtime_identity": runtime_identity,
}
```

- [ ] **Step 4: Run seal tests**

Run: `py -3 -m pytest tests/test_toy_road_t3_rev.py -k "seal" -v`

Expected: PASS.

- [ ] **Step 5: Commit the seal builder**

```powershell
git add analysis/toy_road_t3_rev_20260824/build_t3_rev_seal.py tests/test_toy_road_t3_rev.py
git commit -m "feat: seal one T3-rev execution"
```

### Task 5: Add the one-case launcher with two busy checks

**Files:**
- Create: `analysis/toy_road_t3_rev_20260824/launch_t3_rev.py`
- Modify: `tests/test_toy_road_t3_rev.py`

**Interfaces:**
- Consumes: `launch_t3_rev(repo_root: Path, run_root: Path, seal_path: Path, extension_root: Path, template_run: Path, griphfith_root: Path, input_assets_root: Path, matlab: Path) -> dict[str, object]`.
- Produces: one fresh run root, `T3_REV_EXECUTION_INPUT_LOCK.json`, `T3_REV_LAUNCH_RECEIPT.json`, logs, and one hidden MATLAB process.

- [ ] **Step 1: Write failing launcher-boundary tests**

```python
def test_busy_refusal_precedes_root_creation(monkeypatch, tmp_path: Path) -> None:
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [{"ProcessId": 1}])
    run = tmp_path / "run"
    with pytest.raises(module.BusyExperimentError):
        call_launcher(module, run, tmp_path)
    assert not run.exists()

def test_second_busy_check_prevents_popen(monkeypatch, tmp_path: Path) -> None:
    module = load_module("launch_t3_rev")
    checks = iter([[], [{"ProcessId": 2}]])
    monkeypatch.setattr(module, "matlab_processes", lambda: next(checks))
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    with pytest.raises(module.BusyExperimentError, match="final process check"):
        call_launcher(module, tmp_path / "run", tmp_path)
```

- [ ] **Step 2: Run launcher tests and verify failure**

Run: `py -3 -m pytest tests/test_toy_road_t3_rev.py -k "busy or launcher" -v`

Expected: FAIL while loading `launch_t3_rev.py`.

- [ ] **Step 3: Implement fresh-root and identity validation**

Adapt the T3 launcher without importing its T3-specific case constants. Validate the extension/composite manifest and seal, require clean `git status --porcelain`, reject an existing run root, and set MATLAB path order to:

```python
matlab_paths = [
    runtime_overlay,
    extension_root,
    sealed_base_root,
    griphfith_root / "Sources",
    suite / "CHOLMOD" / "MATLAB",
    suite / "AMD" / "MATLAB",
    suite / "COLAMD" / "MATLAB",
    suite / "CCOLAMD" / "MATLAB",
    suite / "CAMD" / "MATLAB",
]
```

Set `TOY_ROAD_CASE_ROLE=T3_rev_loading_order`, the new family/case hashes, the new repository source commit, and the unchanged runtime lock/MEX/thread variables. Perform the second `matlab_processes()` check after all files are prepared but immediately before opening logs and calling `Popen`. On second-check refusal, write `BUSY_NO_LAUNCH.json` and do not invoke MATLAB; never delete the create-once run root automatically.

- [ ] **Step 4: Assert no retry or follow-on entrypoint exists**

```python
def test_launcher_has_single_nonresume_case_scope() -> None:
    text = (ANALYSIS / "launch_t3_rev.py").read_text()
    assert '"TOY_ROAD_CASE_ROLE": "T3_rev_loading_order"' in text
    assert '"resume_allowed": False' in text
    for forbidden in ("T2-CONT", "T2_material_state", "retry_experiment", "follow_on_case"):
        assert forbidden not in text
```

- [ ] **Step 5: Run launcher tests**

Run: `py -3 -m pytest tests/test_toy_road_t3_rev.py -k "busy or launcher" -v`

Expected: PASS without starting MATLAB.

- [ ] **Step 6: Commit the launcher**

```powershell
git add analysis/toy_road_t3_rev_20260824/launch_t3_rev.py tests/test_toy_road_t3_rev.py
git commit -m "feat: add single T3-rev launcher"
```

### Task 6: Predeclare terminal validation and T3/T3-rev outcome analysis

**Files:**
- Create: `analysis/toy_road_t3_rev_20260824/validate_t3_rev_terminal.py`
- Create: `analysis/toy_road_t3_rev_20260824/analyze_t3_rev.py`
- Modify: `tests/test_toy_road_t3_rev.py`

**Interfaces:**
- Consumes: qualified T3 package, terminal T3-rev package, extension contracts/manifests, and unchanged tolerance contract.
- Produces: `validate_terminal(...) -> dict[str, object]`, `classify_order_effect(rows: Sequence[Mapping[str, float]], tolerances: Mapping[str, float]) -> str`, terminal adjudication, CSV reductions, figures, and a non-authorizing mechanism summary.

- [ ] **Step 1: Write failing outcome-classification tests**

```python
def test_predeclared_order_effect_classes() -> None:
    module = load_module("analyze_t3_rev")
    tol = {"max_abs": 1e-12, "relative_l2": 1e-12}
    assert module.classify_order_effect(equal_after_c60(), tol) == \
        "ORDER_EFFECT_NOT_RESOLVED_WITHIN_TOLERANCE"
    assert module.classify_order_effect(persistent_after_c60(), tol) == \
        "PERSISTENT_LOADING_ORDER_DEPENDENCE_OBSERVED"
    assert module.classify_order_effect(transient_then_converged(), tol) == \
        "TRANSIENT_ORDER_EFFECT_TERMINAL_TRAJECTORY_INSENSITIVE"
```

- [ ] **Step 2: Write failing terminal-class tests**

```python
@pytest.mark.parametrize("terminal, expected", [
    ({"terminal_reason": "confirmed", "confirmed_cycle": 80}, "PASS_CONFIRMED_FRACTURE_TRAJECTORY"),
    ({"terminal_reason": "right_censored", "terminal_cycle": 150}, "PASS_NO_CONFIRMED_FRACTURE_BY_C150"),
    ({"terminal_reason": "coupled_fixed_point_nonconvergence", "cycle": 64, "substep": 4}, "FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE"),
    ({"terminal_reason": "newton_nonconvergence", "cycle": 64, "substep": 4}, "FAIL_NEWTON_NONCONVERGENCE"),
])
def test_terminal_classes_remain_distinct(terminal, expected) -> None:
    assert load_module("validate_t3_rev_terminal").classify_terminal(terminal) == expected
```

- [ ] **Step 3: Run tests and verify missing analyzers fail**

Run: `py -3 -m pytest tests/test_toy_road_t3_rev.py -k "order_effect or terminal_classes" -v`

Expected: FAIL while loading the two modules.

- [ ] **Step 4: Implement strict terminal validation**

Load the generated extension `toy_road_protocol.py`, call its exact package validator for `T3_rev_loading_order`, verify sequential `cycle_0001.mat` through terminal cycle, c5 four-gate receipt, event/terminal binding, composite source identity, unchanged runtime/MEX/thread identities, and sealed base pre/post inventories. Emit a create-once adjudication with `authorization_capability: null` and `follow_on_authorized: false`.

- [ ] **Step 5: Implement deterministic mechanism analysis**

Reuse the published HDF5 reduction functions from `analysis/toy_road_t3_mechanism_20260819` without changing their tolerances. Compare c20, c30, c31, c40, c60, c61, all common post-c60 cycles, and each case's own first-hit/confirmation. Return `UNAVAILABLE` instead of extrapolating missing cycles. The summary must contain:

```python
summary = {
    "schema_version": "toy_road_t3_t3rev_mechanism_summary_v1",
    "status": "PASS_OFFLINE_ANALYSIS",
    "order_effect_classification": classification,
    "nominal_dose_match": "same prescribed amplitude histogram and cycle count through c60",
    "mechanism_claim_boundary": "Order sensitivity under the qualified kernel and declared extension is not unique proof of physical mechanism.",
    "authorization_capability": None,
    "follow_on_authorized": False,
}
```

- [ ] **Step 6: Run analyzer and terminal tests**

Run: `py -3 -m pytest tests/test_toy_road_t3_rev.py -k "order_effect or terminal" -v`

Expected: PASS.

- [ ] **Step 7: Commit validators and analyzer**

```powershell
git add analysis/toy_road_t3_rev_20260824 tests/test_toy_road_t3_rev.py
git commit -m "feat: predeclare T3-rev adjudication"
```

### Task 7: Qualify, seal, and launch exactly one T3-rev

**Files:**
- Generated externally: PowerShell `$extensionRoot`, assigned from the exact implementation commit in Step 4.
- Generated externally: PowerShell `$sealRoot\T3_REV_SEAL.json`, assigned in Step 4.
- Generated externally: PowerShell `$runRoot`, assigned in Step 4.

**Interfaces:**
- Consumes: committed clean repository, qualified T3 evidence, sealed base, T3 runtime template, GRIPHFiTH runtime, and recorded input-assets root.
- Produces: exactly one launched MATLAB PID or a non-launching busy/preflight failure. It never retries.

- [ ] **Step 1: Run focused Python tests**

Run: `py -3 -m pytest tests/test_toy_road_t3_rev.py tests/test_toy_road_t3_sibling.py tests/test_toy_road_t3_mechanism.py tests/test_toy_road_t2_cont.py -v`

Expected: PASS.

- [ ] **Step 2: Run the full P0 protocol regression suite**

Run: `py -3 -m pytest tests/test_toy_road_p0_protocol.py -v`

Expected: PASS with the existing P0/P0R/T1/T2/T3 expectations unchanged.

- [ ] **Step 3: Run MATLAB extension tests**

Run: `matlab -batch "r=run(testsuite('analysis/toy_road_t3_rev_20260824/tests/t3RevExtensionTest.m')); assertSuccess(r);"`

Expected: PASS and no production output root.

- [ ] **Step 4: Commit any final test-only corrections and require a clean tree**

Run: `git status --porcelain`

Expected: no output. Then assign exact create-once roots:

```powershell
$implCommit = (git rev-parse HEAD).Trim()
$extensionRoot = "C:\q4diag\toy-road-t3-rev-extension-$implCommit"
$sealRoot = "C:\q4diag\toy-road-t3-rev-seal-$implCommit"
$runRoot = "C:\q4diag\toy-road-t3-rev-production-$implCommit-run1"
```

- [ ] **Step 5: Build and verify the real create-once extension**

```powershell
py -3 analysis/toy_road_t3_rev_20260824/build_t3_rev_extension.py `
  --base-root producer_handoffs/toy_road_p0_repeatability_20260803 `
  --destination $extensionRoot `
  --repo-commit $implCommit
```

Run `verify_extension_diff.py` against `$extensionRoot` and require `status=PASS`.

- [ ] **Step 6: Build the one-run seal**

Run `build_t3_rev_seal.py` with the generated extension, archived Mac receipt, qualified trajectory registry, and `analysis/toy_road_t3_mechanism_20260819/evidence/T3_SIBLING_TERMINAL_ADJUDICATION.json`. Require `status=PASS` and `authorization_capability=exactly_one_T3_rev_loading_order_execution`.

- [ ] **Step 7: Perform the final idle and target checks**

Run:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^MATLAB' }
Test-Path -LiteralPath $runRoot
git status --porcelain
```

Expected: no MATLAB process, `False`, and no Git output. If any expectation fails, do not launch and preserve the failure evidence.

- [ ] **Step 8: Launch once**

Invoke `launch_t3_rev.py` with the exact extension and seal roots, T3 template run `C:\q4diag\toy-road-t3-production-7c56ff3-run1`, GRIPHFiTH root `C:\q4diag\griphfith-pf-rebuild-355d4c83`, and the T3-recorded input-assets root. Require one `LAUNCHED` receipt. Do not call the launcher again regardless of the subsequent result.

### Task 8: Monitor, terminally validate, and stop

**Files:**
- Generated in run root: stdout/stderr, runtime measurement, cycle shards, c5 gate, event/terminal artifacts.
- Generated externally: terminal adjudication, complete inventory, T3/T3-rev reductions, figures, and mechanism summary.

**Interfaces:**
- Consumes: the already-running single T3-rev PID and immutable run root.
- Produces: one terminal classification and sealed evidence package; no follow-on execution.

- [ ] **Step 1: Monitor without modifying the run**

Check at 30-minute intervals: MATLAB process, stdout/stderr growth, runtime receipt, shard count, c5 trace/receipt, and terminal artifacts. Do not start, resume, or retry anything.

- [ ] **Step 2: Preserve and classify the process exit**

When MATLAB exits, hash the run tree before offline processing and classify startup/runtime, Newton, coupled fixed-point, confirmed-fracture, or c150 right-censored outcome. Keep `tot_en` auxiliary.

- [ ] **Step 3: Run strict terminal validation**

Run `validate_t3_rev_terminal.py` and require the package inventory, extension/composite identity, base pre/post inventory, runtime/MEX/thread identity, c5 gates, event binding, and sequential shards to agree. A validation failure remains `FAIL_TERMINAL_PACKAGE_VALIDATION` and does not trigger a retry.

- [ ] **Step 4: Run deterministic T3/T3-rev analysis**

Run `analyze_t3_rev.py` twice into separate fresh analysis roots. Compare numeric CSV/JSON hashes exactly and record any PNG metadata exclusion explicitly. Publish the predeclared order-effect class and claim boundary.

- [ ] **Step 5: Seal terminal evidence and finish**

Write a create-once checksum inventory and terminal adjudication with `authorization_capability: null` and `follow_on_authorized: false`. Do not launch T2-CONT, full T2, another T3-rev, or any downstream case.
