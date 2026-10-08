# Request 31 CITPC12 storage recovery audit

Date: 2026-10-09  
Mode: read-only inventory and cross-machine verification  
Execution status: `BLOCKED_STORAGE_PREFLIGHT`

## Scope and claim boundary

This audit identifies possible storage-recovery targets for the already
authorised single fresh U0.1175 Request 31 run. It did not delete, move,
compress, overwrite, or modify any Windows data, and it did not start MATLAB or
FEM. A reclaim candidate is not deletion authority.

The Request 31 scientific scope remains unchanged: one exact-family U0.1175
trajectory, c160 first-hit search with at most three confirmation cycles and an
absolute c163 ceiling, using both frozen Contract A and Contract B exports. No
U0.115 replay, U0.125 inspection, alternative amplitude, reduced reserve, or
training is authorised.

## Current live preflight

Read-only CITPC12 check at `2026-10-09T00:19:36+01:00`:

| Item | Result |
|---|---:|
| C: free | 23,636,746,240 bytes = 22.013 GiB |
| frozen c163 output estimate | 13.750 GiB |
| required post-run reserve | 15.000 GiB |
| total required before launch | 28.750 GiB |
| current deficit | 6.737 GiB |
| MATLAB processes | 0 |
| intended U0.1175 output root | absent |

The free-space value is a live quantity and must be rechecked immediately
before any launch. The original failed preflight recorded a deficit of
8.556 GiB; the present deficit is smaller, but the unchanged gate still fails.

## A/B/C inventory

### A — disposable or superseded diagnostics

| Windows directory | GiB | Basis |
|---|---:|---|
| `hard5_native_q4_qualification_20260824_v1` | 0.006908 | unsealed predecessor; no receipt |
| `hard5_native_q4_qualification_20260824_v2` | 0.006908 | unsealed predecessor; no receipt |
| `hard5_native_q4_qualification_20260824_v3` | 0.204371 | explicit validation failure |
| failed Request 28 validator root | 0.100413 | failed attempt superseded by passed export |
| failed exact-peak `red1` root | 0.071239 | failed attempt superseded by v2/v2.1 |
| `request28_capture_smoke_20260817_v1` | 0.225542 | smoke superseded by full replay and accepted handoff |
| **A subtotal** | **0.615381** | insufficient by itself |

Exact deletion targets must still be resolved and approved before any action;
this table is classification only.

### B — recoverable, but preserve or verify a second copy first

| Windows directory | GiB | Risk/evidence |
|---|---:|---|
| `hard5_umax_20260729_v1` | 6.285335 | U0.11/U0.13 July canonical raw output; fully mirrored below |
| `hard5_formal_20260727_v1` | 3.389859 | U0.12 July canonical raw output; fully mirrored below |
| `request28_first_detect_20260817_v1` | 9.289879 | final handoff verified, but handoff contains selected states rather than the complete raw replay |
| `request29_fixed_calendar_20260819_v2` | 4.053294 | final handoff verified, but raw replay has additional artifacts |
| qualification v4 | 0.204382 | passed predecessor; current v5 should be retained |

The preferred minimum-risk pair is the two July canonical directories:

The per-directory rounded values sum to 9.675194 GiB; the exact combined byte
count is 10,388,657,995 bytes = **9.675192 GiB**.

They are mirrored at:

`/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/griphfith/Hard5_eta0_5step_Umax_011_012_013_20260729`

Complete cross-machine verification covered all 459 files and
10,388,657,995 bytes. Both sides produced the same deterministic tree digest
under the schema `sorted UTF-8 lines: case/relative_path|bytes|file_sha256 + LF`:

`52d546a498c946eb9c0edbb568e5a962c3261159aea1d7762509bdde58a4468f`

This upgrades the pair from sampled evidence to a complete file-by-file
content check. It remains a reclaim candidate, not an authorised deletion.

The Request 28 final handoff was also independently verified against its
manifest on Mac/OneDrive (manifest SHA256
`691e090fffa3d1e946eb0ad41befde7e67bb32d9d191ab6f255c89dcae78454a`).
However, deleting its Windows raw replay would discard full intermediate
trajectory/checkpoint artifacts that are not present in the selected-state
handoff, so it is a higher-risk alternative.

The Request 29 final handoff was likewise verified (manifest SHA256
`a3961933114b3648689a0a60700f7cdb898b640c61a030e4f5897a65e424186b`),
but the same raw-versus-selected-artifact distinction applies.

### C — retain or currently uncertain

- `hard5_native_q4_existing_u011_u012_u013_20260827_v1` (28.275914 GiB):
  current three-trajectory Stage0b corpus.
- `hard5_new_runs_u0115_u0125_20260827_v1` (18.401537 GiB): U0.115 reuse
  source plus closed U0.125 payload; do not inspect or remove.
- current qualification v5 (0.204387 GiB): present authority.
- `request31_phaseA_snapshots` (0.380085 GiB): required source snapshot for
  the authorised U0.1175 launch.
- Request 31 Phase A c1 and current audit/control/preflight evidence: retain
  until the acquisition closes.
- Any synthetic-DIC/in-progress output without a completed lineage audit:
  uncertain, therefore retain.

## Recommendation and next gate

The lowest-risk sufficient recovery candidate is:

1. `C:\q4runs\hard5_umax_20260729_v1`
2. `C:\q4runs\hard5_formal_20260727_v1`

Together they would recover approximately 9.675 GiB. At the current live free
space this would nominally raise C: to about 31.689 GiB, above the frozen
28.750 GiB launch requirement. This projection is not a launch pass: after an
explicit human approval and any recoverable removal/migration, Windows must
rerun the unchanged free-space, process, source-identity, and output-root
preflight. Only that fresh receipt can authorise MATLAB start.

No storage mutation or FEM execution was performed by this audit.
