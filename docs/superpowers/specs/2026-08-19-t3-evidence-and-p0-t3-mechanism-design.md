# T3 Evidence Distribution and P0–T3 Mechanism Design

## Status

Approved in chat on 2026-08-19 for implementation on
`codex/toy-road-evidence-producer`.

This is an architectural evidence-and-analysis addition. It does not change
the sealed producer, solver, runtime, convergence thresholds, P0, or T3.

## Objective

Publish the complete, immutable `T3_loading_history` terminal package through
the University of Cambridge OneDrive while keeping GitHub compact, then
perform a predeclared offline P0–T3 mechanism comparison that tests whether
the c31–c60 high-amplitude block leaves persistent history/degradation memory.

The accepted event-level result remains:

- P0: first hit c70, confirmed c73;
- T3: first hit c68, confirmed c71;
- T3 relative to P0: both event markers move by -2 cycles.

The mechanism analysis may describe observed field differences, but it must
not claim a validated physical mechanism from event timing alone.

## Immutable inputs

### P0 reference

- Root: `C:\q4diag\toy-road-p0-production-d17efe6-run1\output`
- Case: `P0_parent`
- Terminal cycles: first hit c70, confirmed c73
- Expected cycle shards: 73
- Terminal manifest SHA-256:
  `91b90c0b682a05908e20b31546ae29732c1fffd9a67418d9b386b6aa5d806893`

### T3 trajectory

- Root: `C:\q4diag\toy-road-t3-production-7c56ff3-run1\output`
- Case: `T3_loading_history`
- Terminal cycles: first hit c68, confirmed c71
- Expected cycle shards: 71
- Terminal manifest SHA-256:
  `455b149b14276598ad87e4bcea6b6a2916de6e59d3812f791d66e61b1344bb01`
- Authenticated terminal receipt SHA-256:
  `e15b0c4f68e17364b9101e5691f8d13cc0a61a3ed60e1c9dbea19bc422927adf`
- Terminal adjudication receipt SHA-256:
  `9c0a0783bd6c59d825300538336258350df63c294f38f7febf29dae905c00300`

All reads are read-only. No file below either run root may be modified,
renamed, normalized, or regenerated.

## Architecture

The work has three isolated units:

1. **OneDrive immutable mirror** copies the complete T3 terminal package and
   the external evidence receipts into a create-once versioned directory,
   then verifies every copied byte.
2. **GitHub compact evidence** publishes manifests, receipts, inventories,
   a OneDrive locator, and an independent verifier without committing the
   multi-gigabyte MAT shards.
3. **Offline mechanism analysis** reads selected P0/T3 shards with `h5py`,
   reduces the same mesh fields under predeclared definitions, and emits
   compact CSV/JSON/PNG/report artifacts.

None of these units imports or invokes the FEM launcher or solver.

## OneDrive package design

### Destination

The create-once destination is:

```text
C:\Users\xw436\OneDrive - University of Cambridge\griphfith\toy-road-evidence\
  T3_loading_history\
  manifest-455b149b14276598ad87e4bcea6b6a2916de6e59d3812f791d66e61b1344bb01\
```

It contains:

```text
output/                 exact T3 terminal package mirror
external_evidence/      authentication, adjudication, shard inventory
ONEDRIVE_PACKAGE.json   immutable package locator and binding
SHA256SUMS.txt          hashes for all mirrored files
```

The copy is direct rather than a tar archive. MAT shards are already large,
single-file compression has little expected benefit, and per-file transfer
allows Mac validation and selective retry without rebuilding one archive.

### Safety and verification

The mirror builder must:

- fail if the destination already exists;
- reject symlinks/reparse-point traversal below source roots;
- require T3 authentication and adjudication receipts to recheck as PASS;
- require exactly 71 consecutive shards;
- calculate source SHA-256 before copy and destination SHA-256 after copy;
- require byte count and SHA-256 equality for every file;
- write locator and checksum files only after all payload files verify;
- never delete, move, or edit source files;
- never expose an execution or follow-on authorization capability.

Local byte equality proves a correct mirror. Upload completion is reported
separately: the OneDrive client must be running and the versioned destination
must reach a non-pending synced state before the package is called uploaded.
If cloud-state confirmation is unavailable, report `LOCAL_MIRROR_VERIFIED` and
do not claim `ONEDRIVE_UPLOAD_VERIFIED`.

## GitHub compact evidence

GitHub receives only compact artifacts under:

```text
analysis/toy_road_t3_mechanism_20260819/evidence/
```

Required content:

- `T3_SIBLING_TERMINAL_ADJUDICATION.json`;
- `T3_AUTHENTICATED_TERMINAL.json`;
- `TERMINAL_MANIFEST.json`;
- `TERMINAL_RESULT.json` and `EVENT_METADATA.json`;
- c5 numerical gate receipt and stagger trace;
- runtime measurement, input lock, and launch receipt;
- exact 71-shard path/size/SHA-256 inventory;
- `ONEDRIVE_PACKAGE.json` with the relative Cambridge OneDrive path;
- a compact evidence inventory binding every committed evidence file;
- an independent verification command/script for Windows or macOS.

The compact package must distinguish:

- byte-level serialization and provenance differences;
- numerical-field differences;
- the single declared physical input axis `loading.blocks`.

It must not contain the 2.76 GiB shard payload and must not contain OneDrive
credentials, tokens, private share URLs, absolute user-profile paths in the
portable locator, or production authorization capability.

## Mechanism analysis contract

### Cycles and alignments

The required physical-cycle nodes are:

```text
c20, c30, c31, c40, c60, c61, c68, c70, c71, c73
```

T3 has no c73 shard. Therefore:

- same-cycle comparisons use cycles present in both trajectories:
  c20, c30, c31, c40, c60, c61, c68, c70, c71;
- P0 c73 is included as the P0 confirmed-event endpoint, not fabricated for
  T3;
- own-event comparisons are P0 c70 versus T3 c68 (first hit) and P0 c73
  versus T3 c71 (confirmation);
- block transitions compare within T3 c30→c31 and c60→c61, with the same
  differences also computed for P0 as a constant-loading control.

All field comparisons use peak substep ordinal 4, selected by the stored
`substep_ordinal` dataset rather than by row position.

### Input fields

The analysis reads the following immutable shard fields:

- nodal damage: `d_node`;
- GP damage: `d_gp`;
- history: `alpha_bar_gp`;
- fatigue degradation: `f_alpha_gp`;
- ordinary degradation: `g_gp`;
- raw driver: `psi_raw_gp` and `psi_raw_cyclemax_gp`;
- active driver: `psi_active_gp`;
- loading: `load_factor`;
- mesh: `node_coords` and `connectivity`.

Mesh, ordering, family, runtime, case-contract, and input-lock identities are
validated before any reduction. P0 and T3 must have identical mesh and
ordering identities.

### Geometry and weighting

- Connectivity is converted from stored MATLAB one-based indices to Python
  zero-based indices after strict integer/range validation.
- Q4 element area and centroid are computed from the stored node coordinates.
- GP fields are reduced to element fields by the arithmetic mean over four
  stored Gauss points; domain integrals are element-area weighted.
- Nodal damage is reduced to elements by the arithmetic mean over the four
  connectivity nodes.
- Incremental damage at cycle c is the nonnegative part of
  `d_elem(c,s4) - d_elem(c-1,s4)`.

The process-zone support is predeclared as:

```text
incremental_damage >= max(1e-8, 0.01 * max(incremental_damage))
```

matching the existing D-T2 compact diagnostic convention. Its centroid and
RMS width are incremental-damage × element-area weighted. Support area is the
sum of element areas in the mask.

Crack-tip position is reported from the event-consistent damaged-node graph:
nodes with `d_node(s4) >= 0.95` are connected through Q4 element edges; the
main component intersecting the declared initial damaged support is retained,
and its maximum x coordinate is the crack-tip x. The right-boundary event is
reported separately using the sealed x≥0.48, d≥0.95, three-connected-node
definition. No alternative threshold may replace the sealed event result.

### Reductions

For every available requested cycle and each GP field, emit:

- min, max, area-weighted mean, and area-weighted integral;
- area-weighted p50, p95, and p99;
- positive-support area at an absolute numerical floor of `1e-15` and at
  one percent of the within-field cycle maximum;
- field-weighted centroid and RMS widths in x and y where total weight is
  positive;
- tip and process-zone reductions using the predeclared crack/process-zone
  geometry.

For `alpha_bar_gp`, also emit thresholded support areas at >0. For
`f_alpha_gp` and `g_gp`, emit degradation deficits `1-f` and `1-g` so that
larger values consistently mean greater degradation.

### Required figures

1. Loading amplitude and sealed event trajectory versus cycle.
2. P0/T3 trajectories for damage, history, degradation deficit, raw driver,
   and active driver.
3. History support area and active-driver support area versus cycle.
4. Crack-tip x, incremental process-zone centroid, support area, and RMS
   width versus cycle.
5. T3 c30→c31 and c60→c61 transition panels with P0 transition controls.
6. Same-cycle field maps at c20, c30, c31, c40, c60, c61, c68, c70, c71.
7. Own-event field maps: P0 c70/T3 c68 and P0 c73/T3 c71.

Figures use common color limits within each compared field/panel and label
missing T3 c73 explicitly rather than extrapolating it.

### Memory discriminator

The analysis reports evidence for persistent high-block memory only if all
three statements are directly supported by reductions:

1. T3 departs from P0 during or immediately after c31–c60 in stored history
   and/or degradation fields;
2. the departure remains at c61 and at least one later pre-event node;
3. the persistent difference is spatially co-located with subsequent
   process-zone or crack-tip advance.

Failure of any item is reported as `MEMORY_NOT_ESTABLISHED`. Passing all
items is reported as `PERSISTENT_MEMORY_OBSERVED`, not as proof that the
constitutive mechanism is correct.

## Output artifacts

The analysis writes only beneath:

```text
analysis/toy_road_t3_mechanism_20260819/results/
```

Required outputs:

- `cycle_field_reductions.csv`;
- `same_cycle_differences.csv`;
- `own_event_differences.csv`;
- `block_transition_differences.csv`;
- `process_zone_trajectory.csv`;
- `mechanism_summary.json`;
- `P0_T3_MECHANISM_REPORT.md`;
- the seven figure families above;
- `ANALYSIS_INPUT_INVENTORY.json` and `SHA256SUMS.txt`.

The report must state the sealed event timing separately from the mechanism
assessment and identify every metric definition used.

## Failure handling

- Missing, duplicate, or nonconsecutive shards: fail before analysis.
- Any manifest/checksum/identity mismatch: fail closed and write no PASS
  summary.
- Missing required dataset, wrong shape, NaN/Inf, invalid connectivity, or
  absent s4: fail with the exact case/cycle/dataset.
- Missing T3 c73: expected and explicitly represented as unavailable.
- Existing OneDrive destination or results directory: fail without overwrite.
- OneDrive pending/unknown cloud state: retain verified local mirror but do
  not claim upload completion.

## Tests

Tests use synthetic HDF5 fixtures and temporary directories; they never copy
the production 2.76 GiB package during unit tests.

They must prove:

- create-once and no-clobber behavior;
- symlink/reparse-point rejection;
- source/destination size and hash equality;
- exactly 71 consecutive T3 inventory entries;
- tampering of any payload or receipt fails verification;
- portable OneDrive locator excludes credentials and absolute profile paths;
- MATLAB one-based connectivity conversion and geometry calculations;
- s4 selection by stored ordinal;
- field/area reductions and process-zone thresholds on known fixtures;
- same-cycle, own-event, and transition pair construction;
- c73 is P0-only without T3 extrapolation;
- memory classification requires all three predeclared conditions;
- no FEM/launcher imports or execution authorization capability appear in
  the evidence or analysis modules.

Production acceptance additionally requires:

- a fresh terminal authentication recheck;
- a full post-copy hash verification of all mirrored T3 files;
- compact evidence self-verification from a clean checkout;
- deterministic rerun of offline analysis with identical numeric CSV/JSON
  outputs and byte-stable figure inventory (PNG metadata excluded if needed
  and documented).

## Non-goals

- No P0 or T3 rerun, resume, or retry.
- No T2-CONT execution or relaxation sweep.
- No T3-reversed-order FEM launch in this change.
- No change to solver, runtime, producer, event definition, or gates.
- No causal or constitutive-mechanism claim from event timing alone.
- No production authorization embedded in evidence or analysis receipts.

## Future discriminator

After this analysis is independently reviewed, a separate authorization may
define a dose-matched reversed-order sibling:

```text
T3:     c1–30 0.108, c31–60 0.126, then 0.120
T3-rev: c1–30 0.126, c31–60 0.108, then 0.120
```

That future case is outside this implementation and requires its own sealed
contract and one-shot execution authorization.
