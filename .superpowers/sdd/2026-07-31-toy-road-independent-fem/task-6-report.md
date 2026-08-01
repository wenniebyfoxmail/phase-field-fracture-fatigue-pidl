# Task 6 Report: Immutable Launcher, Provenance, and Package Gates

> Fix round 1/5 was completed on 2026-08-01. The original Task 6 evidence is
> retained below as history; the final section, "Fix Round 1/5", supersedes
> its implementation hashes, lock counts, and verification totals.

## Scope and commit

Task 6 was implemented from base commit
`e3b46c36d7cc1f417254e87edc94dada36365052` and committed as:

```text
e54dbc20de23fd186ea8feab6a6721a9c178233d
feat: seal toy-road FEM producer handoff
```

The implementation commit contains only the six Task 6 source and test files
listed below. The SDD ledger was not modified. No MATLAB trajectory, physical
FEM cycle, equilibrium assembly, MEX computation, or process termination was
performed.

## Files changed

- `producer_handoffs/toy_to_road_independent_fem_20260731/launch_toy_road_case.ps1`
- `producer_handoffs/toy_to_road_independent_fem_20260731/finalize_toy_road_package.m`
- `producer_handoffs/toy_to_road_independent_fem_20260731/README.md`
- `producer_handoffs/toy_to_road_independent_fem_20260731/SHA256SUMS.txt`
- `producer_handoffs/toy_to_road_independent_fem_20260731/tests/toyRoadFinalizeTest.m`
- `tests/test_toy_road_fem_handoff.py`

## Launcher contract

The PowerShell launcher accepts one case from the three sealed case IDs and
requires an explicit full `ExpectedSourceCommit`. Before any MATLAB command is
constructed, it rejects a missing output parent, an existing case output root,
checkpoint/resume environment input, a dirty shared repository, the wrong
shared commit, source-manifest coverage or digest drift, a dirty or wrong
GRIPHFiTH repository, source/runtime/parent hash drift, a running MATLAB/FEM
experiment, and an unsupported output-volume hard-link operation. Its hard-link
probe uses the selected output parent and removes both probe paths.

Production sets exactly the four Task 5 variables
`TOY_ROAD_CASE_ID`, `TOY_ROAD_OUTPUT_ROOT`, `TOY_ROAD_SOURCE_COMMIT`, and
`TOY_ROAD_LOCK_SHA256`. It adds only the handoff, locked GRIPHFiTH Sources, and
the required SuiteSparse MATLAB directories, then invokes exactly one case.
The launcher contains no execution-policy bypass and never kills a process.

`-PreflightOnly` returns after all gates and before MATLAB command construction.
The JSON fixture seam is accepted only together with `-PreflightOnly`, so it
cannot invoke MATLAB. Tests use an outer `-ExecutionPolicy Bypass` only because
the host policy blocks unsigned scripts.

After the case process exits successfully, the launcher requires the existing
Task 5 `RUN_RESULT.json` to be a valid complete marker. A second validation-only
MATLAB process supplies the locked provenance receipt to the finalizer.
`RUN_RESULT.json` remains the sole completion marker.

## Finalizer contract

The finalizer validates the complete marker before publication and then checks:

- the exact case lock, source commit, source-manifest hash, parent-lock hash,
  GRIPHFiTH commit, and exact source/runtime/parent digest sets;
- the full input snapshot against the case configuration and fresh-execution
  settings;
- mesh dimensions, finite values, Q4 connectivity, recomputed centroids and
  areas, quadrature, ordering ID, mesh digest, and T1 transfer audit or exact
  unchanged non-T1 mesh;
- recovered state0 arrays, fatigue-history reset semantics, and initial-state
  metadata;
- every `states/cycle_NNNN.mat` through `validate_toy_road_state`, including
  consecutive state semantics, exact mesh arrays/hash, cycle amplitude, and
  cycle/raw-step mapping;
- every cycle-index row, including strict boolean `event_hit`, and the event
  lifecycle reconstructed with `advance_toy_road_event`;
- terminal event and run metadata for confirmation or right-censoring at c150;
- exact pre-finalization files/directories, with no symlinks, nested state
  directories, duplicate paths, or case-colliding paths.

Only after all validation succeeds does it publish deterministic
`PRODUCER_PROVENANCE.json` and `VALIDATION_SUMMARY.json` through the existing
hard-link no-clobber writer. It preserves the Task 5 authoritative
`EVENT_METADATA.json`. It then publishes a sorted no-clobber output
`SHA256SUMS.txt` covering every output file except itself. Verification mode
rechecks LF manifest bytes, sort order, exact file coverage, and every digest.
Incomplete, malformed, tampered, missing, extra, or pre-existing final output
fails closed.

## Source and runtime locks

The source manifest contains 30 ordinal-sorted entries and excludes itself.
It covers all four locks, all recursive producer MATLAB files and MATLAB tests,
the launcher, README, and the Python handoff test. Its exact-byte SHA-256 is:

```text
a04ccf9c5da361d034d552e87ab7b6e70ac02dc060ce8eef96b6e775336c530b
```

Lock digests are:

```text
PARENT_LOCK.json   9d8c9a63243df59731d8daa35775a4f18157ae5078aa8994f4d55e6552b9d43c
T1_INPUT_LOCK.json 0572e7d35a6d49fa3c2ea448a3b1bd650f01a2590a1264095c0e5c0b6d4ccce6
T2_INPUT_LOCK.json 29f35fbef1ce4af005df5f2b026fdd69befeec59413e7e95e43dca977fb6cd56
T3_INPUT_LOCK.json 9af4b33fbc4402aa28005ce69fb9c9ddcd991f8531ea89197de5ce0400d6d483
```

The launcher locks GRIPHFiTH commit
`355d4c83fefc2db88c32031a2dd2623b3de85c89` and seven required source files.
The source digest set is:

```text
ae1aa2ff4114c67b166e39b377e08a0d7e28761bb0afa038a388e1eb026e9252
20afff63d79eeffd3e6a502b996485e47f64a3b550e19b396cd1bf90120ad76d
c9ebc6e87ddc1e6340a6fe077903241656feedea5220488035fb49e3efe55831
3cc4ba07cf4b0d5a556457567b719c633e65a3519e1a734ddea00c608c292353
96365b7f0b6ecf02cd0e2209765310f29122f503b5c2272240f84fb24ea4098d
383fe2566a63652b9287fec3172f4135800e7cb605efcc718e90abf3a54ec5fa
dbf13237939425b61cde93b841ae2c24e7fccd291861df5508a34800bb9f4706
```

The runtime digest set is:

```text
initial.mexw64              589f3dc793694ea2916fbb6a21dd030bc4bc04ead3d91705e6e882b2d67ca340
AMOR.mexw64                 64abee69f2c441730dc2efa4047ac45ab1d1b40e20c4822ed6e992adcd6b19e7
AT1_HISTORY_FATIGUE.mexw64  53e8fd0b229817b7c14c52a5b6afaa957692f475057b79b9a9a10195ccb92e60
cholmod2.mexw64             86a2f15543eda1f7223a1733d935d37e9e2f4f2c2d8db3c4adc2c0f675c27329
```

All seven parent records, including `MANIFEST.csv`, are taken directly from
`PARENT_LOCK.json` and verified before MATLAB can start. The F1b MEX is
hash-gated only as a diagnostic runtime artifact; F1b is not used as parent and
no claim is made that its crash is fixed.

## Strict TDD evidence

Initial Python/static/PowerShell RED, before Task 6 artifacts existed:

```text
Command: py -3 -m pytest tests/test_toy_road_fem_handoff.py -q
Result: 13 failed, 10 passed.
Expected cause: launcher, finalizer, README, manifest, and their contracts were absent.
```

Initial MATLAB finalizer RED after constructing the valid fixture:

```text
Command: focused toyRoadFinalizeTest
Result: 7 failed.
Expected cause: finalize_toy_road_package was undefined.
```

Mutation tests separately demonstrated RED for Task 5 CRLF CSV handling,
non-boolean `event_hit`, malformed provenance hash receipts, and an extra empty
output directory. Each mutation was retained as a regression before its
production fix. Final focused MATLAB finalizer result was 10/10 passed.

Final focused Python GREEN, including launcher gate mutations and fresh
byte-preserving manifest-copy verification:

```text
Command: py -3 -m pytest tests/test_toy_road_fem_handoff.py tests/test_toy_to_road_evidence_gate.py -q
Result: 33 passed in 32.05s, exit 0.
```

Final full Python GREEN used a disposable virtual environment containing the
repository's optional scientific dependencies and UTF-8 mode for the existing
UTF-8 F1b static source:

```text
Command: $env:PYTHONUTF8='1'; .\.task6-test-venv\Scripts\python.exe -m pytest -q
Result: 275 passed, 2 skipped, 1 warning in 43.87s, exit 0.
```

The one warning is the inherited PyTorch nested-tensor warning at
`source/temporal_mesh_operator.py:301`. The temporary environment was removed
after verification.

Every MATLAB invocation was preceded by a process inventory check. Final full
producer MATLAB GREEN was:

```text
Command: runtests('producer_handoffs/toy_to_road_independent_fem_20260731/tests'); assertSuccess
Result: 91 total, 91 passed, 0 failed, 0 incomplete, exit 0.
```

Recursive Code Analyzer results were:

```text
TASK6_CODE_ANALYZER_MESSAGES=0
FULL_PRODUCER_CODE_ANALYZER_MESSAGES=7
```

The seven full-suite findings are inherited and unchanged:
`apply_t1_mesh_transfer.m:14`, `build_toy_road_case_config.m:183`, and
`toyRoadConfigTest.m` lines 77, 94, 111, 123, and 140. The Task 6 finalizer and
its test have zero findings.

The manifest was regenerated mechanically from exact bytes after the last
covered source edit. The tests copied every covered file byte-for-byte to a
fresh temporary directory, parsed the copied manifest, and reverified all 30
digests there. No CRLF normalization was performed.

## Task 7 concerns

- Task 7 must nominate the final clean full source commit explicitly to
  `-ExpectedSourceCommit`; the implementation commit above is the Task 6 code
  identity, while the report is recorded in a following documentation commit.
- Run the launcher from a byte-preserving checkout whose covered files match
  the source manifest. Any edit, including line-ending conversion, requires a
  regenerated manifest and a new sealed commit.
- Recheck both repositories, all parent/runtime hashes, process inventory, the
  empty output location, and hard-link support immediately before each case.
- Execute only one case at a time and use a new output root for every attempt.
  Never resume, repair, or finalize a partially published root.
- Verify the output manifest after finalization and retain `RUN_RESULT.json` as
  the sole completion marker. Do not infer completion from provenance,
  validation summary, or event metadata.
- Keep all three trajectories synthetic and single-axis. Do not expose latent
  FEM fields as road sensors, train PIDL networks, claim road validation, or use
  the separately blocked F1b diagnostic as the parent.

## Fix Round 1/5

### Scope and implementation commit

The critical mesh-binding and exact-provenance review was implemented and
committed as:

```text
d2cba6dc1ac44861b21c16a12c5e68ef2231f4dd
fix: bind toy-road producer evidence identities
```

The commit changes the launcher, finalizer, README, source manifest, parent,
family, and three case locks, and their focused Python/MATLAB tests. The SDD
ledger remains unchanged. No MATLAB trajectory, physical FEM cycle,
equilibrium/MEX solve, or process termination was performed. MATLAB was used
only for producer tests, read-only artifact inspection, and Code Analyzer.

### Canonical parent mesh identity

`PARENT_LOCK.mesh.content_sha256` remains the pre-existing legacy graph hash:

```text
7ea77bf6d4621d746f174eb9c357c4bc554463eea8afb8665b00e918bcd937ab
```

Its exact algorithm is the existing `fem_trajectory_bundle.py` graph-content
algorithm: for `centroids`, `areas`, `connectivity`, and `edge_index`, in that
order, hash the ASCII key, NumPy dtype text, int64 shape bytes, and contiguous
array bytes. `mesh.source_sha256` is separately the raw analysis-graph NPZ
digest:

```text
bd5b731daeb0718368309cd50c44fa7422e49096b495f619eba429d1c6bde419
```

That legacy graph hash is not the Task 4 mesh hash. The additional canonical
Task 4 parent identity is:

```text
4d01985bfe2e80afe7140ab1ead905ddce5843f8495a3558d2d4da3b237df5af
```

It was derived read-only from the already parent-hash-gated
`peak_load_c1.vtk`: hash MATLAB column-major `double(parent_node_coords(:))`
bytes followed by column-major `int64(connectivity(:))` bytes. The source has
exactly 86756 nodes and 86408 Q4 elements. Its raw-byte SHA-256 is
`acdc981269024cbb111f7d468c287f2d1ca09f3735131b56aca7fa2fbaec1615`;
the existing normalized ASCII VTK geometry/topology digest is
`8e865f5eace05992490885c569f5ca8d9d1e37e10a3d2bd8ade176bfcd23ecf2`.
The lock records all four hash semantics explicitly without replacing the
physical parent authority.

Production finalization first validates these real PARENT_LOCK constants.
T2 and T3 must reproduce the sealed parent hash from
`parent_node_coords/connectivity` and keep `node_coords` byte-identical. T1
must first reproduce that same sealed parent identity, then independently
recompute `apply_t1_mesh_transfer` and match its resulting coordinates and
candidate hash. Every state must match the case mesh hash and the exact locked
Q4 quadrature points and weights from `mesh_geometry.mat`. The small test mesh
is available only through the explicit
`toy_road_finalizer_test_dependencies_v1` schema; the production three-argument
launcher invocation uses the real dimensions and hash.

### Exact provenance and launcher receipt

The launcher now rejects non-canonical case spelling, dirty shared or
GRIPHFiTH repositories, wrong commits, source/runtime/parent byte drift,
existing output, resume input, running MATLAB/FEM inventory, and hard-link
preflight failure before MATLAB. Its completion check requires JSON boolean
`true`, exact case and status, an integral cycle in 1..150, exact terminal
reason, and the matching canonical state path; right-censoring is valid only at
c150. Both test seams return under `-PreflightOnly` and cannot invoke MATLAB.

After that strict completion check, production creates the canonical
`<output>/LAUNCH_RECEIPT.json` with `FileMode.CreateNew`. The receipt binds the
launcher-verified source commit and roots, source manifest, case and parent
locks, GRIPHFiTH commit, and exact normalized relative-path-to-SHA256 mappings
for source, GRIPHFiTH, runtime, and all eight parent records. The finalizer
accepts only that canonical receipt path. It rejects digest multisets,
renamed/swapped mappings, duplicate and case-colliding paths, unsafe paths,
missing/extra entries, all-one-character commits, symlinks/reparse points, and
pre-existing final outputs. `RUN_RESULT.json` remains the sole completion
marker.

The source manifest deliberately excludes itself and contains no Git commit.
Covered source is committed first; an evidence-report-only commit may follow
without changing the manifest. Task 7 must pass the final clean HEAD as
`-ExpectedSourceCommit`; the no-clobber launch receipt records that exact
launcher-verified commit, avoiding a self-referential source hash.

### Final hashes

The 30-entry ordinal path-sorted, LF-only source manifest SHA-256 is:

```text
695ba35d6feb65361346f835e97ba4c01f07b7159ec9ef74a880e712f2f0097b
```

Current lock digests are:

```text
FAMILY_INPUT_LOCK.json 7891e343870b6f6b75a7e7649eb09fd071c5e29da6f567a013d3509b83453b70
PARENT_LOCK.json       f34cbfe1bc4fe2178aff590cbed3d4d65547e2a8a9ff300a9b2c5f70cc00f954
T1_INPUT_LOCK.json     7365488aab7de8fbbf7b846972b8d4a15a63226b1f7ae917c3409b5743084d60
T2_INPUT_LOCK.json     e9eeddd072afefa8fa0d9833a861b5dc97bb362d16c9979f6f7a0da9d0c2a35c
T3_INPUT_LOCK.json     581f446f9e82b329dbaf96eab2d68721bb66487524c9f4c17436e4e05c8d4f4b
```

### Strict TDD evidence

The round began with failing tests before production changes:

```text
Python RED: 14 failed, 24 passed in 64.30s
MATLAB RED after valid fixture: 17 failed, 3 incomplete
```

The failures covered missing real-lock mesh dimensions/identity, T1 map and
quadrature checks, exact receipt mappings, canonical receipt binding,
reparse-point rejection, strict completion parsing, and new launcher hash and
case gates. Intermediate failures were debugged without executing a trajectory.

Final verification on the committed covered bytes:

```text
Focused Python: 49 passed in 74.46s
Full Python: 291 passed, 2 skipped, 1 inherited warning in 99.49s
Full producer MATLAB: 98 passed, 0 failed, 0 incomplete
Code Analyzer: 22 files, 7 inherited findings, 0 changed Task 6 findings
Fresh byte-preserving copy: 30/30 source entries verified
```

The inherited analyzer findings remain in `apply_t1_mesh_transfer.m`,
`build_toy_road_case_config.m`, and `toyRoadConfigTest.m`. The inherited Python
warning remains the PyTorch nested-tensor warning in
`source/temporal_mesh_operator.py:301`. The disposable full-suite virtual
environment was removed after verification.

### Task 7 concerns after fix round 1

- Seal and record the final clean HEAD after the evidence-report commit, then
  use that exact commit for every `-ExpectedSourceCommit` invocation.
- Run the non-solving preflight again immediately before each physical case;
  do not reuse its output root and do not run cases concurrently.
- Preserve LF-sensitive covered bytes. Any covered edit or line-ending change
  requires a regenerated manifest and a new source commit.
- Retain `LAUNCH_RECEIPT.json` and verify the final output manifest. Never infer
  completion from provenance, summary, or event metadata instead of
  `RUN_RESULT.json`.
- Keep the parent VTK, graph hashes, Task 4 mesh identity, GRIPHFiTH commit,
  runtime hashes, and eight parent path mappings unchanged unless a later
  approved design explicitly reseals them.
- Do not resume, repair, or finalize partial roots; never auto-terminate an
  existing experiment; preserve the synthetic-only, no-PIDL-training,
  no-road-validation claim boundary.
