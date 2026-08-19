# T3 Evidence and P0–T3 Mechanism Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mirror the immutable 2.76 GiB T3 terminal package to Cambridge OneDrive, publish a compact independently verifiable GitHub evidence package, and produce the predeclared offline P0–T3 field/mechanism comparison.

**Architecture:** A small Python package separates immutable evidence validation, create-once OneDrive mirroring, HDF5 field reductions, and deterministic plotting/reporting. Unit tests use synthetic HDF5 fixtures; production commands operate read-only on P0/T3 and write only to create-once OneDrive/evidence/results directories.

**Tech Stack:** Python 3, pytest, h5py, NumPy, Matplotlib, JSON/CSV/SHA-256, Git, local Cambridge OneDrive sync client.

**Spec:** `docs/superpowers/specs/2026-08-19-t3-evidence-and-p0-t3-mechanism-design.md`

## Global Constraints

- Never rerun, resume, retry, rename, normalize, or modify P0 or T3.
- Never launch FEM, T2-CONT, a relaxation sweep, or a new case.
- Keep the sealed producer, runtime, solver, event definition, and gates unchanged.
- The only physical P0/T3 input change is `loading.blocks`; provenance differences remain separate.
- OneDrive and results destinations are create-once and fail closed if present.
- Git excludes all MAT shards and publishes only compact evidence and results.
- All comparisons use stored peak substep ordinal 4.
- Required nodes are c20, c30, c31, c40, c60, c61, c68, c70, c71, and P0-only c73.
- No artifact may carry execution or follow-on authorization capability.

---

### Task 1: Strict evidence model and compact package

**Files:**
- Create: `analysis/toy_road_t3_mechanism_20260819/__init__.py`
- Create: `analysis/toy_road_t3_mechanism_20260819/evidence.py`
- Create: `analysis/toy_road_t3_mechanism_20260819/verify_compact_evidence.py`
- Create: `tests/test_toy_road_t3_mechanism.py`

**Interfaces:**
- Consumes: T3 authenticated receipt, adjudication receipt, terminal manifest/result/event, c5 artifacts, runtime/input/launch receipts.
- Produces: `sha256_file(path: Path) -> str`, `load_json_strict(path: Path) -> dict`, `validate_t3_bindings(paths: EvidencePaths) -> dict`, `build_compact_evidence(paths: EvidencePaths, destination: Path, onedrive_relative_path: str) -> dict`, and `verify_compact_evidence(root: Path) -> dict`.

- [ ] **Step 1: Write strict JSON and binding tests**

Add tests that construct tiny receipts and assert:

```python
def test_load_json_strict_rejects_duplicate_keys(tmp_path): ...
def test_validate_t3_bindings_requires_71_consecutive_shards(tmp_path): ...
def test_validate_t3_bindings_rejects_hash_tampering(tmp_path): ...
def test_compact_locator_is_portable_and_non_authorizing(tmp_path): ...
def test_verify_compact_evidence_detects_modified_file(tmp_path): ...
```

Fixtures must use `substeps/cycle_0001.mat` through
`substeps/cycle_0071.mat`, with recorded size and SHA-256, and must assert the
locator contains neither `C:\Users\` nor credentials/share tokens.

- [ ] **Step 2: Run the new tests and confirm RED**

Run:

```powershell
py -3 -m pytest tests/test_toy_road_t3_mechanism.py -q
```

Expected: collection/import failure because the analysis package does not
exist.

- [ ] **Step 3: Implement strict evidence parsing and closure checks**

Implement duplicate-key rejection with an `object_pairs_hook`, reject
NaN/Infinity via `parse_constant`, require exact case/status/hash/count/event
fields, and verify:

```python
EXPECTED_CASE = "T3_loading_history"
EXPECTED_MANIFEST = "455b149b14276598ad87e4bcea6b6a2916de6e59d3812f791d66e61b1344bb01"
EXPECTED_ADJUDICATION = "9c0a0783bd6c59d825300538336258350df63c294f38f7febf29dae905c00300"
EXPECTED_FIRST_HIT = 68
EXPECTED_CONFIRMED = 71
EXPECTED_SHARDS = 71
```

`build_compact_evidence` must copy only allowlisted compact files, generate a
canonical inventory, record the relative OneDrive path, and set:

```json
{"authorization_capability": null, "follow_on_authorized": false}
```

- [ ] **Step 4: Implement the standalone verifier**

The CLI must accept one compact evidence root, recompute all hashes, validate
the terminal/adjudication bindings, and emit one JSON line with status PASS or
exit nonzero with the first exact mismatch.

- [ ] **Step 5: Run Task 1 tests and confirm GREEN**

Run:

```powershell
py -3 -m pytest tests/test_toy_road_t3_mechanism.py -q
```

Expected: all Task 1 tests pass.

- [ ] **Step 6: Commit Task 1**

```powershell
git add analysis/toy_road_t3_mechanism_20260819 tests/test_toy_road_t3_mechanism.py
git commit -m "feat: add strict T3 compact evidence verification"
```

### Task 2: Create-once OneDrive mirror

**Files:**
- Create: `analysis/toy_road_t3_mechanism_20260819/mirror_to_onedrive.py`
- Modify: `tests/test_toy_road_t3_mechanism.py`

**Interfaces:**
- Consumes: `sha256_file` and `validate_t3_bindings` from Task 1.
- Produces: `validate_source_tree(root: Path) -> list[FileRecord]`, `mirror_verified(source_output: Path, evidence_files: list[Path], destination: Path) -> dict`, and CLI arguments `--output-root`, `--external-evidence-root`, `--destination`.

- [ ] **Step 1: Write mirror failure and success tests**

Add:

```python
def test_mirror_refuses_existing_destination(tmp_path): ...
def test_mirror_rejects_symlink_or_reparse_source(tmp_path): ...
def test_mirror_verifies_every_source_and_destination_byte(tmp_path): ...
def test_mirror_fails_when_copy_is_corrupted(tmp_path, monkeypatch): ...
def test_mirror_writes_locator_only_after_payload_verifies(tmp_path): ...
```

The success fixture must verify destination sizes and SHA-256 values against
source records. The corruption test must leave no PASS locator.

- [ ] **Step 2: Run mirror tests and confirm RED**

Run:

```powershell
py -3 -m pytest tests/test_toy_road_t3_mechanism.py -q -k mirror
```

Expected: import/attribute failure for the missing mirror implementation.

- [ ] **Step 3: Implement the mirror**

Walk source roots without following links, copy in deterministic relative-path
order with `shutil.copyfile`, preserve payload bytes without normalizing
timestamps/content, verify each destination digest immediately, then write:

```text
ONEDRIVE_PACKAGE.json
SHA256SUMS.txt
```

The locator records manifest SHA, file count, total bytes, portable relative
path, and `upload_state: LOCAL_MIRROR_VERIFIED`. It must not claim cloud sync.

- [ ] **Step 4: Run mirror tests and full focused suite**

Run:

```powershell
py -3 -m pytest tests/test_toy_road_t3_mechanism.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 2**

```powershell
git add analysis/toy_road_t3_mechanism_20260819/mirror_to_onedrive.py tests/test_toy_road_t3_mechanism.py
git commit -m "feat: add verified OneDrive T3 mirror"
```

### Task 3: HDF5 trajectory loader and predeclared reductions

**Files:**
- Create: `analysis/toy_road_t3_mechanism_20260819/mechanism.py`
- Modify: `tests/test_toy_road_t3_mechanism.py`

**Interfaces:**
- Consumes: MATLAB 7.3 `mesh_geometry.mat` and `cycle_NNNN.mat` files.
- Produces: `load_mesh(path: Path) -> Mesh`, `load_peak_fields(path: Path, expected_cycle: int) -> PeakFields`, `element_geometry(mesh: Mesh) -> ElementGeometry`, `reduce_field(values, areas, centroids) -> dict`, `process_zone(delta_damage, geometry) -> dict`, `build_comparison_pairs() -> dict`, and `classify_memory(rows: Sequence[dict]) -> str`.

- [ ] **Step 1: Write synthetic HDF5 geometry/field tests**

Create a two-Q4-element fixture with known coordinates, one-based
connectivity, stored substep ordinals `[1,2,3,4,5]`, and deterministic GP/node
fields. Add tests:

```python
def test_load_mesh_converts_one_based_connectivity_and_computes_area(tmp_path): ...
def test_load_peak_fields_selects_stored_ordinal_four(tmp_path): ...
def test_loader_rejects_missing_s4_nan_and_wrong_identity(tmp_path): ...
def test_reduce_field_matches_known_weighted_integral_and_percentiles(): ...
def test_process_zone_uses_predeclared_threshold(): ...
def test_comparison_pairs_include_p0_only_c73_without_t3_extrapolation(): ...
def test_memory_requires_persistence_and_spatial_colocation(): ...
```

- [ ] **Step 2: Run mechanism tests and confirm RED**

Run:

```powershell
py -3 -m pytest tests/test_toy_road_t3_mechanism.py -q -k "mesh or peak or reduce or process_zone or comparison_pairs or memory"
```

Expected: import/attribute failures for missing mechanism functions.

- [ ] **Step 3: Implement strict HDF5 loading**

Require the exact datasets from the spec, finite float arrays, Q4
connectivity, valid node indices, matching mesh/order/runtime identities, and
exactly one stored ordinal 4. Read only the s4 hyperslabs required for each
field rather than loading every full shard into memory.

- [ ] **Step 4: Implement geometry and reductions**

Compute Q4 polygon areas/centroids, GP arithmetic means, nodal-to-element
means, area-weighted min/max/mean/integral/quantiles/support, degradation
deficits, field centroids/widths, event-consistent crack-tip, and incremental
damage process-zone metrics using:

```python
threshold = max(1e-8, 0.01 * float(delta_damage.max()))
```

- [ ] **Step 5: Implement pair construction and memory classification**

Return exact same-cycle, own-event, and transition pairs. Classify
`PERSISTENT_MEMORY_OBSERVED` only when departure, persistence, and spatial
co-location booleans are all true; otherwise return
`MEMORY_NOT_ESTABLISHED`.

- [ ] **Step 6: Run Task 3 tests and focused suite**

Run:

```powershell
py -3 -m pytest tests/test_toy_road_t3_mechanism.py -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit Task 3**

```powershell
git add analysis/toy_road_t3_mechanism_20260819/mechanism.py tests/test_toy_road_t3_mechanism.py
git commit -m "feat: add P0-T3 mechanism reductions"
```

### Task 4: Deterministic production analysis, plots, and report

**Files:**
- Create: `analysis/toy_road_t3_mechanism_20260819/run_analysis.py`
- Create: `analysis/toy_road_t3_mechanism_20260819/README.md`
- Modify: `tests/test_toy_road_t3_mechanism.py`

**Interfaces:**
- Consumes: Task 3 loader/reduction functions plus P0/T3 terminal roots.
- Produces: `run_analysis(p0_root: Path, t3_root: Path, destination: Path) -> dict` and the CSV/JSON/PNG/Markdown outputs named in the spec.

- [ ] **Step 1: Write orchestration and determinism tests**

Add synthetic trajectory tests that assert:

```python
def test_run_analysis_refuses_existing_results(tmp_path): ...
def test_run_analysis_emits_required_tables_and_summary(tmp_path): ...
def test_report_separates_event_result_from_mechanism_claim(tmp_path): ...
def test_figures_use_common_limits_and_label_missing_t3_c73(tmp_path): ...
def test_analysis_code_does_not_import_or_invoke_fem_launcher(): ...
```

The report test must find both `ΔN_first=-2`, `ΔN_confirmed=-2`, and one of
the two permitted memory classifications.

- [ ] **Step 2: Run orchestration tests and confirm RED**

Run:

```powershell
py -3 -m pytest tests/test_toy_road_t3_mechanism.py -q -k "run_analysis or report or figures or launcher"
```

Expected: missing `run_analysis` failures.

- [ ] **Step 3: Implement production orchestration**

Validate terminal identities and requested shards before creating the results
directory. Emit deterministic CSV column order and canonical JSON. Generate
the seven required figure families with explicit common limits, same-cycle,
own-event, and transition captions. Do not extrapolate T3 c73.

- [ ] **Step 4: Implement the mechanism report and inventories**

Write `P0_T3_MECHANISM_REPORT.md` with sections:

```text
Evidence qualification
Sealed event result
Loading-block transitions
History/degradation persistence
Process-zone and crack-tip response
Same-cycle versus own-event comparison
Mechanism boundary and next discriminator
```

Bind every input shard and every output artifact in JSON/SHA256 inventories.

- [ ] **Step 5: Run all focused tests twice**

Run twice:

```powershell
py -3 -m pytest tests/test_toy_road_t3_mechanism.py -q
```

Expected: identical pass count on both runs.

- [ ] **Step 6: Commit Task 4**

```powershell
git add analysis/toy_road_t3_mechanism_20260819 tests/test_toy_road_t3_mechanism.py
git commit -m "feat: add deterministic P0-T3 mechanism report"
```

### Task 5: Produce, verify, and publish evidence

**Files:**
- Create: `analysis/toy_road_t3_mechanism_20260819/evidence/*`
- Create: `analysis/toy_road_t3_mechanism_20260819/results/*`
- Create externally: `C:\Users\xw436\OneDrive - University of Cambridge\griphfith\toy-road-evidence\T3_loading_history\manifest-455b149b14276598ad87e4bcea6b6a2916de6e59d3812f791d66e61b1344bb01\*`

**Interfaces:**
- Consumes: the verified production P0/T3 packages and Tasks 1–4 CLIs.
- Produces: OneDrive full mirror, compact GitHub evidence, analysis results, commits, and pushed branch.

- [ ] **Step 1: Confirm no MATLAB experiment is active and roots are immutable**

Run:

```powershell
Get-Process -Name MATLAB -ErrorAction SilentlyContinue
git status --short --branch
```

Expected: no MATLAB process and a clean producer branch.

- [ ] **Step 2: Freshly recheck T3 authentication**

Run:

```powershell
py -3 producer_handoffs/toy_road_p0_repeatability_20260803/toy_road_protocol.py --recheck-authentication C:\q4diag\toy-road-t3-sibling-seal-2ff8b5f\T3_AUTHENTICATED_TERMINAL.json
```

Expected: `{"status":"PASS"}`.

- [ ] **Step 3: Build and independently verify compact evidence**

Run the Task 1 builder against the immutable T3 roots and then:

```powershell
py -3 analysis/toy_road_t3_mechanism_20260819/verify_compact_evidence.py analysis/toy_road_t3_mechanism_20260819/evidence
```

Expected: PASS with 71 shards and the bound manifest/adjudication hashes.

- [ ] **Step 4: Build the OneDrive mirror**

Run Task 2 with the exact destination in the spec. Allow the copy to complete
without launching other experiments. Expected: `LOCAL_MIRROR_VERIFIED`, 84
terminal-package files plus external evidence, and zero hash mismatches.

- [ ] **Step 5: Check OneDrive synchronization state**

Confirm the OneDrive client is active and inspect the versioned destination.
If the client exposes a completed non-pending state, update only the external
upload-status receipt to `ONEDRIVE_UPLOAD_VERIFIED`; otherwise retain
`LOCAL_MIRROR_VERIFIED` and report that cloud completion remains unproven.

- [ ] **Step 6: Run the production mechanism analysis**

Run:

```powershell
py -3 analysis/toy_road_t3_mechanism_20260819/run_analysis.py --p0-root C:\q4diag\toy-road-p0-production-d17efe6-run1\output --t3-root C:\q4diag\toy-road-t3-production-7c56ff3-run1\output --destination analysis/toy_road_t3_mechanism_20260819/results
```

Expected: ten requested node records with T3 c73 explicitly unavailable,
sealed ΔN values -2/-2, figures/tables/report, and one permitted memory status.

- [ ] **Step 7: Verify deterministic analysis and full tests**

Run the analysis into a temporary second directory, compare canonical
CSV/JSON hashes, then run:

```powershell
py -3 -m pytest tests/test_toy_road_t3_mechanism.py -q
py -3 -m pytest tests/test_toy_road_p0_protocol.py -q
git diff --check
```

Expected: all tests pass, numeric artifacts match, and no whitespace errors.

- [ ] **Step 8: Commit compact evidence and results**

```powershell
git add analysis/toy_road_t3_mechanism_20260819 tests/test_toy_road_t3_mechanism.py
git commit -m "evidence: publish T3 package and P0-T3 mechanism comparison"
```

- [ ] **Step 9: Push the selected producer branch**

```powershell
git push origin codex/toy-road-evidence-producer
```

Expected: the remote branch advances from `2ff8b5f` through the new design,
implementation, and evidence commits. Do not modify
`codex/toy-road-evidence-integration`.
