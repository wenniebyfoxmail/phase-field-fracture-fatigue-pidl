---
storyline_id: S03
experiment_id: S03-E003
protocol_revision: v3
status: ready
started_at: 2026-10-08
closed_at:
primary_storyline: S03
related_storylines: [S02]
scientific_verdict:
---

# AA2024 outcome-blind archive-manifest qualification

## PIDL Experiment Gate

- **Primary claim class:** `observation-validity`.
- **Question:** does the immutable archive for Zenodo record `11945905` match
  the manifest capabilities declared by the official record closely enough to
  justify a later header/semantics audit?
- **Cheaper falsification first:** archive identity and ZIP central directory
  only. No archive member content is read in this revision.
- **Pass claim:** permit design and independent review of a new header audit.
- **Fail claim:** stop this AA2024 route at dataset capability; do not inspect
  outcomes, tune a forecast task, train a model, or start inversion.
- **Smallest output:** one allowlisted `data_audit.json` containing booleans,
  counts, enum decisions, and fixed stop-reason codes.
- **Registry:** S03-E003. Any header audit, forecast, or inverse problem requires
  a later separately frozen and reviewed Experiment or protocol revision.

## Scientific question and claim boundary

This is a dataset-capability audit, not a model-performance experiment. It asks
whether the archive identity and manifest support the official description's
claimed global DIC asset counts and named mapping/dictionary assets.

Blocked regardless of outcome: header semantics, chronology, direct target
support, forecast accuracy, uncertainty calibration, phase-field recovery,
material-property identification, specimen generalisation, road transfer, and
deployment.

## Reuse decision

- **Searched:** Gate 3B screen, S03-E001/E002 audit patterns, project registry,
  the external plan review, official Zenodo metadata, and remote ZIP central
  directory.
- **Reused:** Experiment/Run structure, exact identity locks, fixed decision
  enums, output allowlisting, and immutable raw-data separation.
- **New code:** needed for outcome-blind central-directory validation without
  archive extraction or member reads.

## Frozen protocol v3

### Immutable identity lock

- Record: `https://zenodo.org/records/11945905`
- DOI: `10.5281/zenodo.11945905`
- Record / concept record: `11945905` / `11945904`
- Licence: CC BY 4.0
- Archive: `multiscale_digital_image_correlation.zip`
- Exact size: `1,248,078,255` bytes
- Exact MD5: `e671b804e29401e70043bc1e17f66dd1`
- Raw root:
  `$PROJECT/local_archive/open_data/aa2024_dic_zenodo_11945905_20261008/raw/`
- Audit root:
  `$PROJECT/local_archive/experiments/S03-E003/runs/S03-E003-R001/`

The raw archive and official API JSON are immutable inputs. Audit output must be
inside the frozen audit root, must not alias either input, and must not be
placed in the raw tree.

### Permitted reads

1. Read the official API JSON as an external, untrusted input.
2. Compute the local archive byte size and MD5.
3. Read only the ZIP central directory via `ZipFile.infolist()`.
4. Do not call `ZipFile.open()`, extract members, read headers, inspect mapping
   rows, or parse dictionary contents.

Only boolean checks derived from official metadata may enter output. External
metadata strings and individual member names are not emitted.

### Exact manifest contract

After identity passes, require all of the following:

1. Central directory is readable.
2. Every member path is relative, POSIX-style, traversal-free, and unique after
   lexical normalization and case-folding.
3. No member is encrypted or a symlink; compression type is supported.
4. Exactly `797` `.txt` files appear below `global_3d_dic/nodemaps/`.
5. Exactly `797` `.txt` files appear below `global_3d_dic/connections/`.
6. Exactly one basename equals
   `local_2d_microscopic_coordinates_by_nodemaps.csv`.
7. Exactly one basename exists for each dictionary:
   `higher_level_metadata_dictionary.json` and
   `timestep_level_metadata_dictionary.json`.

Directory matching is case-insensitive; filenames are counted from canonical
central-directory paths only. Local nodemap count is descriptive and is not a
pass criterion in v3.

### Primary decision and stop rule

`QUALIFIED_FOR_HEADER_AUDIT` requires every official-metadata, local-identity,
path-safety, member-safety, and exact-manifest check to pass.

Any failure yields `BLOCKED_DATASET_CAPABILITY` with one or more fixed codes:

- `OFFICIAL_METADATA_INVALID`
- `ARCHIVE_IDENTITY_MISMATCH`
- `ZIP_CENTRAL_DIRECTORY_INVALID`
- `UNSAFE_OR_AMBIGUOUS_MEMBER_PATH`
- `UNSUPPORTED_OR_ENCRYPTED_MEMBER`
- `GLOBAL_NODEMAP_COUNT_MISMATCH`
- `GLOBAL_CONNECTION_COUNT_MISMATCH`
- `MAPPING_FILE_IDENTITY_MISMATCH`
- `METADATA_DICTIONARY_IDENTITY_MISMATCH`

Identity failure stops before central-directory inspection. A central-directory
failure stops before asset-count qualification. No mismatch may be repaired by
changing the expected count/name after viewing the archive.

## Required evidence

- frozen protocol v3;
- independently reviewed exact runner/tests/commit with `PASS_CODE_READY`;
- official API JSON and archive size/MD5 receipt;
- redacted `data_audit.json` and exact execution receipt;
- `decision.md` stating allowed and blocked conclusions;
- independent evidence review bound to the compact output before closure.

## Producer and Run readiness

- **Producer:** Mac-PIDL, data/schema audit only; no optimization loop.
- **Runner:** `scripts/aa2024_value_blind_audit.py`.
- **Tests:** `tests/test_aa2024_value_blind_audit.py`.
- **Run:** S03-E003-R001, pending Code Ready PASS and complete archive MD5.
- **Safety:** read-only raw inputs; no extraction, training, inversion, FEM, or
  remote compute.

## Amendments

### 2026-10-08 — v2 (never executed)

The first Code Ready review of commit `930b6ab` returned `REVISE_CODE`. It found
missing episode/timestep identity, direct-target validity, strict parsing,
manifest-first stopping, output redaction verification, and collision guards.
The runner was strengthened at commit `c07aa30`; no real audit was executed.

### 2026-10-08 — v3 (before any Run)

The second Code Ready review of `c07aa30` returned `REVISE_CODE`: bounded header
reading could false-fail large members; dictionary units/semantics and local
synchronization were not qualified; “episode” and candidate horizons exceeded
implemented evidence; output and malformed-input firewalls were incomplete.

Separately, an outcome-blind remote central-directory check found only 342
global nodemap files and a released mapping basename containing an additional
`coordinates_` token, while the official description and frozen v2 contract
expected 797 files and the documented basename. Because manifest structure is
the cheaper falsification, v3 removes all header, chronology, target, horizon,
and episode claims. The observation is not yet the Experiment result: the
official full archive must pass exact MD5 and the reviewed v3 runner must
reproduce it locally.

## Code review

- Round 1: `REVISE_CODE`, bound to `930b6ab` and v1.
- Round 2: `REVISE_CODE`, bound to `c07aa30` and v2.
- Round 3: pending, to be bound to the v3 commit, runner, tests, identity lock,
  and this protocol.
- **Execution rule:** do not run the real archive audit before
  `PASS_CODE_READY`.

## Runs

| Run ID | Purpose | Execution | Retrieval | Receipt |
|---|---|---|---|---|
| S03-E003-R001 | outcome-blind manifest qualification | prepared | pending | pending |

## Evidence review

Pending S03-E003-R001 and an independent review of the compact evidence.

## Scientific verdict

Pending. No claim changes before closure.

## Next action

Complete immutable archive verification, commit the v3 runner/tests/protocol,
obtain independent Code Ready review, then execute exactly S03-E003-R001 only
if the review passes.
