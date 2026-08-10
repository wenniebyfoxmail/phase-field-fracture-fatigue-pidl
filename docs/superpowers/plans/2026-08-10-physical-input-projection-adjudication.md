# Physical-Input Projection and Repeatability Adjudication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a strict, versioned physical-input projection and a non-authorizing external P0/P0R adjudication receipt without modifying or rerunning either package.

**Architecture:** Keep legacy package validation in `toy_road_protocol.py`, add strict JSON primitives there, and place projection/adjudication logic in a focused `toy_road_adjudication.py` module. The projection binds the complete declared `case_physics` tree plus a semantic initial-state hash; the adjudicator separately requires identical producer/runtime/MATLAB/MEX/thread identities and applies the existing event/c5/trajectory tolerances. The receipt is external evidence only; T1 still requires an independent one-shot authorization.

**Tech Stack:** Python 3.12, NumPy, existing MAT readers, pytest, PowerShell launcher tests, canonical JSON, SHA-256.

## Global Constraints

- Preserve all P0/P0R outputs and legacy receipts byte-for-byte.
- Do not rerun P0 or P0R.
- Projection schema is exactly `toy_road_physical_input_projection_v1`.
- Adjudication schema is exactly `toy_road_external_repeatability_adjudication_v1`.
- Existing thresholds remain `1e-12`; observed zero differences are measurements, not thresholds.
- T1 requires adjudication PASS plus a separate one-shot authorization.
- Do not start T2 or T3.

---

### Task 1: Strict JSON decoding

**Files:**
- Modify: `producer_handoffs/toy_road_p0_repeatability_20260803/toy_road_protocol.py`
- Test: `tests/test_toy_road_p0_protocol.py`

**Interfaces:**
- Produces: `_strict_json_loads(payload: bytes, label: str) -> object`
- Consumed by: `_read_json_bytes` and the adjudication module.

- [ ] **Step 1: Write failing tests for forbidden JSON**

Add parametrized tests for duplicate keys, `NaN`, `Infinity`, and `-Infinity`, plus a valid control:

```python
@pytest.mark.parametrize("payload", [
    b'{"case_id":"P0","case_id":"P0R"}',
    b'{"value":NaN}', b'{"value":Infinity}', b'{"value":-Infinity}',
])
def test_strict_json_rejects_ambiguous_or_nonfinite_values(payload: bytes) -> None:
    with pytest.raises(ProtocolError, match="duplicate|finite|JSON"):
        PROTOCOL._read_json_bytes(payload, "strict fixture")
```

- [ ] **Step 2: Run focused tests and verify RED**

Run `python -m pytest tests/test_toy_road_p0_protocol.py -k strict_json -q`.
Expected: duplicate-key and nonfinite cases fail because `json.loads` currently accepts them.

- [ ] **Step 3: Implement strict decoding**

Use `object_pairs_hook` to reject duplicate keys and `parse_constant` to reject nonfinite tokens. Decode UTF-8 strictly and preserve the top-level object requirement.

- [ ] **Step 4: Verify GREEN and regressions**

Run the focused test, then `python -m pytest tests/test_toy_road_p0_protocol.py -q`.

- [ ] **Step 5: Commit**

```powershell
git add producer_handoffs/toy_road_p0_repeatability_20260803/toy_road_protocol.py tests/test_toy_road_p0_protocol.py
git commit -m "fix: reject ambiguous protocol JSON"
```

### Task 2: Versioned projection with initial-state closure

**Files:**
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/toy_road_adjudication.py`
- Modify: `tests/test_toy_road_p0_protocol.py`

**Interfaces:**
- Produces: `build_physical_input_projection(snapshot_bytes: bytes, state0: Mapping[str, object]) -> dict[str, object]`
- Produces: `physical_input_projection_sha256(projection: Mapping[str, object]) -> str`
- Produces: `semantic_initial_state_sha256(state0: Mapping[str, object]) -> str`

- [ ] **Step 1: Write failing case-id invariance test**

Create a minimal valid snapshot fixture with exact top-level fields and closed `case_physics` subtrees. Build two snapshots differing only in `case_id`; assert identical projections and hashes.

- [ ] **Step 2: Verify RED**

Run `python -m pytest tests/test_toy_road_p0_protocol.py -k physical_input_projection -q`.
Expected: import/function missing.

- [ ] **Step 3: Implement exact projection validation**

Require exact snapshot fields and exact `case_physics` categories: `mesh`, `material`, `loading`, `numerics`, `recovery`, and `event`. Validate every closed subtree against the declared contract shape and exact primitive types. Treat `bool` as invalid where `int` or `float` is required. Reject missing/extra fields and invalid schema/version.

Canonical payload:

```python
{
    "schema_version": "toy_road_physical_input_projection_v1",
    "case_physics": validated_case_physics,
    "initial_state": {
        "schema_version": "toy_road_semantic_initial_state_v1",
        "sha256": semantic_initial_state_sha256(state0),
    },
}
```

The semantic state hash encodes field name, dtype `float64`, shape, and canonical little-endian C-order bytes for exactly `d_node` and `alpha_bar_gp`. Reject nonfinite values, invalid shapes, missing/extra fields, and damage/history domain violations. This closes initial damage, history, and pre-crack identity without relying on MAT serialization bytes.

- [ ] **Step 4: Add leaf-sensitivity tests**

Walk every leaf under the allowlisted `case_physics` fixture. Change each leaf once using the same type and assert the hash changes. Add tests for initial damage/history changes, extra/missing fields, bool/int confusion, nonfinite values, and invalid schema/version.

- [ ] **Step 5: Add actual P0/P0R integration test**

Read immutable snapshots and state0 values through the existing MAT reader. Assert legacy snapshot SHA values differ while v1 projection hashes are identical.

- [ ] **Step 6: Verify and commit**

Run focused tests, then commit the module and tests with `feat: add versioned physical input projection`.

### Task 3: Independent producer and runtime identity closure

**Files:**
- Modify: `producer_handoffs/toy_road_p0_repeatability_20260803/toy_road_adjudication.py`
- Modify: `tests/test_toy_road_p0_protocol.py`

**Interfaces:**
- Produces: `extract_producer_runtime_identity(package, producer_root: Path) -> dict[str, object]`
- Produces: `require_equal_producer_runtime_identity(p0, p0r) -> None`

- [ ] **Step 1: Write failing mismatch tests**

Parametrize source commit, source manifest SHA, physics contract, runtime lock, each MATLAB identity field, each binary hash (`initial`, `AMOR`, `AT1_HISTORY_FATIGUE`, `cholmod2`), and each thread setting (`OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_DYNAMIC=FALSE`). Require fail-closed messages naming the field.

- [ ] **Step 2: Verify RED**

Run focused identity tests and confirm failure due to the missing interface.

- [ ] **Step 3: Implement identity extraction and equality**

Read source/runtime values from each validated execution lock and runtime receipt. Require identical source commit, source manifest SHA, case-physics contract SHA, runtime-lock SHA, MATLAB release/update/version, computer, executable SHA, BLAS, LAPACK, and four binary hashes. Validate the sealed producer source manifest and bind the exact launcher SHA. Extract four thread assignments from the sealed launcher using exact anchored matching; reject duplicates, absence, or alternate values.

- [ ] **Step 4: Verify and commit**

Run focused tests and the full Python suite, then commit with `feat: bind adjudication runtime identities`.

### Task 4: Complete non-authorizing adjudication receipt

**Files:**
- Modify: `producer_handoffs/toy_road_p0_repeatability_20260803/toy_road_adjudication.py`
- Modify: `tests/test_toy_road_p0_protocol.py`

**Interfaces:**
- Produces: `adjudicate_repeatability(p0_root: Path, p0r_root: Path, producer_root: Path, destination: Path) -> dict[str, object]`
- CLI: `toy_road_adjudication.py adjudicate <p0> <p0r> <producer-root> <receipt>`
- CLI: `toy_road_adjudication.py recheck <receipt>`

- [ ] **Step 1: Write failing completeness test**

Require exact receipt fields for both terminal manifest SHAs, both full snapshot SHAs, both projection SHAs, both source/runtime identity objects, c5 receipt SHAs, 73-shard aggregate inventories/counts, adjudicator commit/SHA, terminal-validator commit/SHA, unchanged thresholds, observed maxima, and every excluded provenance difference with exact path/P0/P0R values.

- [ ] **Step 2: Write failing non-authorization test**

Assert `authorization_capability == "none"`, `production_execution_authorized is False`, no authorization ID exists, and the receipt cannot satisfy the T1 one-shot schema.

- [ ] **Step 3: Verify RED**

Run focused adjudication tests and confirm missing behavior.

- [ ] **Step 4: Implement adjudication**

Independently call `_validate_package` for both roots, build both projections, require equal projections and producer/runtime identities, then apply existing event, state0, c5, shard identity, and trajectory checks. Keep `THRESHOLD == 1e-12`; record observed maximum absolute and relative L2 values.

Build each shard inventory as an ordered list of 73 `{path, sha256}` records and bind the aggregate SHA and count. Recursively compare snapshot fields outside the projection allowlist and include actual JSON paths and both values. Publish exclusively. Recheck receipt schema, source identities, code hashes, and immutable package snapshots.

- [ ] **Step 5: Verify tamper rejection and commit**

Test package mutation, receipt mutation, projection mismatch, runtime mismatch, and destination collision. Run the full suite and commit with `feat: adjudicate external repeatability evidence`.

### Task 5: T1 predecessor gate and independent authorization

**Files:**
- Modify: `producer_handoffs/toy_road_p0_repeatability_20260803/launch_toy_road_family_case.ps1`
- Modify: `producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadLauncherTest.ps1`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/new_toy_road_t1_one_shot_wrapper.ps1`
- Create: `producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadT1OneShotWrapperTest.ps1`

**Interfaces:**
- Launcher consumes adjudication PASS as T1 predecessor evidence only.
- Wrapper consumes a separate `T1_INITIAL_DEFECT_EXECUTION_AUTHORIZED` one-shot artifact.

- [ ] **Step 1: Write failing gate tests**

Require T1 to reject absent/FAIL/tampered adjudication and reject using adjudication as execution authorization. Require valid adjudication without separate T1 authorization to remain non-executable.

- [ ] **Step 2: Verify RED**

Run the existing launcher test and the new T1 wrapper test. Expected: missing predecessor and wrapper behavior.

- [ ] **Step 3: Implement minimal gates**

For T1 only, authenticate/recheck adjudication as predecessor evidence. Keep execution authorization separate. The wrapper validates role, sealed source commit, unique authorization ID, no-resume, no-retry, dedicated process gate, and consumes once before invoking the unchanged numerical driver.

- [ ] **Step 4: Verify and commit**

Run PowerShell and Python suites, then commit with `feat: gate T1 on adjudicated repeatability`.

### Task 6: Real P0/P0R adjudication and T1 readiness boundary

**Files:**
- Create externally: `C:\q4diag\toy-road-p0r-production-d17efe6-run1\P0R_EXTERNAL_REPEATABILITY_ADJUDICATION_V1.json`
- Update: `producer_handoffs/toy_road_p0_repeatability_20260803/SOURCE_MANIFEST.json`
- Update: `producer_handoffs/toy_road_p0_repeatability_20260803/SHA256SUMS.txt`

**Interfaces:**
- Consumes immutable P0/P0R packages and sealed producer source.
- Produces PASS/FAIL predecessor evidence with no execution authority.

- [ ] **Step 1: Snapshot legacy hashes**

Record both complete package inventories and legacy external receipt hashes before adjudication. Rehash afterward and require byte identity.

- [ ] **Step 2: Run adjudicator once**

Use actual package roots and sealed `d17efe6` producer root. Expected PASS includes identical projections, c70/c73, c5 PASS, 73 shards, observed max absolute `0`, observed relative L2 `0`, thresholds still `1e-12`.

- [ ] **Step 3: Recheck independently**

Run the recheck CLI, verify exact fields and no authorization capability, and compare before/after legacy inventories.

- [ ] **Step 4: Run full verification**

```powershell
python -m pytest tests/test_toy_road_p0_protocol.py -q
powershell -NoProfile -ExecutionPolicy Bypass -File producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadLauncherTest.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File producer_handoffs/toy_road_p0_repeatability_20260803/tests/toyRoadT1OneShotWrapperTest.ps1
git diff --check
git status --short
```

- [ ] **Step 5: Commit evidence integration**

Commit source manifests and adjudication metadata only; do not add or modify P0/P0R bytes.

- [ ] **Step 6: Stop at T1 authorization boundary**

Confirm zero MATLAB/FEM processes. Start T1 only after a distinct one-shot T1 authorization is issued for the newly sealed source commit. Do not start T2 or T3.
