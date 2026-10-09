---
storyline_id: S03
experiment_id: S03-E003
protocol_revision: v5
status: closed
started_at: 2026-10-08
closed_at: 2026-10-09
primary_storyline: S03
related_storylines: [S02]
scientific_verdict: BLOCKED_DATASET_CAPABILITY
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

## Frozen protocol v5

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
2. Every untruncated `ZipInfo.orig_filename` is free of NUL/control characters,
   relative, POSIX-style, traversal-free, and unique after lexical normalization
   and case-folding. Counts use only original names that pass this validation.
3. No member is encrypted or a symlink; compression type is supported.
4. Exactly `797` `.txt` files appear below `global_3d_dic/nodemaps/`.
5. Exactly `797` `.txt` files appear below `global_3d_dic/connections/`.
6. Exactly one basename equals
   `local_2d_microscopic_coordinates_by_nodemaps.csv`.
7. Exactly one basename exists for each dictionary:
   `higher_level_metadata_dictionary.json` and
   `timestep_level_metadata_dictionary.json`.

Directory matching is case-insensitive. The three required basenames are exact
and case-sensitive. Filenames are counted from safe canonical central-directory
paths only. Local nodemap count is descriptive and is not a pass criterion in
v5.

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

`qualification_not_established` is the only allowed conclusion when official
metadata, archive identity, or central-directory decoding prevents manifest
inspection. `locked_archive_does_not_meet_declared_manifest_contract` is
allowed only after identity passes, the central directory is readable, and a
manifest safety/count/identity condition fails.

Official API JSON is rejected in full if any object contains a duplicate key;
ordinary JSON last-key-wins behavior is not accepted for this identity receipt.

## Required evidence

- frozen protocol v5;
- independently reviewed exact runner/tests/commit with `PASS_CODE_READY`;
- official API JSON and archive size/MD5 receipt;
- redacted `data_audit.json` and exact execution receipt;
- `decision.md` stating allowed and blocked conclusions;
- independent evidence review bound to the compact output before closure.

## Producer and Run readiness

- **Producer:** Mac-PIDL, data/schema audit only; no optimization loop.
- **Runner:** `scripts/aa2024_value_blind_audit.py`.
- **Tests:** `tests/test_aa2024_value_blind_audit.py`.
- **Run:** S03-E003-R001 executed only after the exact v5 commit received
  `PASS_CODE_READY`. The controlled run completed the frozen audit and returned
  `BLOCKED_DATASET_CAPABILITY`; the result was later independently reviewed.
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

### 2026-10-08 — v4 (before any Run)

The third Code Ready review of `00dee5d` returned `REVISE_CODE`. It reproduced
an embedded-NUL path false pass caused by validating truncated
`ZipInfo.filename`, an uncaught malformed-UTF-8 central-directory failure, and
last-key-wins acceptance of contradictory JSON identity declarations. It also
found that early metadata/archive verification failures emitted a manifest
defect conclusion even though the manifest had not been inspected.

v4 validates untruncated `ZipInfo.orig_filename`, rejects NUL/control and
ambiguous paths before counting, maps filename-decoding failure to the fixed
ZIP reason, rejects duplicate JSON keys, and distinguishes
`qualification_not_established` from an observed manifest-contract failure.
Required basenames are now explicitly exact and case-sensitive. No real audit
had run when this amendment was frozen.

### 2026-10-09 — v5 (before any Run)

The fourth Code Ready review of `53eb40e` returned `REVISE_CODE`. It found that
an output path equal to the allowed audit root was accepted, that the path
safety check omitted DEL and C1 control characters, and that standard-library
JSON parser `ValueError`/`RecursionError` failures could escape the fixed
failure interface before ZIP construction.

v5 requires the output target to be a strict descendant of the frozen audit
root and rejects a directory target before any write. Central-directory names
now reject every Unicode `Cc` control character, including NUL, DEL, and C1.
Official metadata parsing maps `ValueError` and `RecursionError` to
`OFFICIAL_METADATA_INVALID`, preserving the redacted
`qualification_not_established` result without opening the ZIP. Synthetic
regressions cover both root-equality cases, a directory target, DEL/C1 member
names, a 5,000-digit integer, and deeply nested JSON. No real audit had run when
this amendment was frozen.

## Code review

- Round 1: `REVISE_CODE`, bound to `930b6ab` and v1.
- Round 2: `REVISE_CODE`, bound to `c07aa30` and v2.
- Round 3: `REVISE_CODE`, bound to `00dee5d` and v3; recorded in
  `docs/reviews/s03_e003_aa2024_code_review_round3_20261008.md`.
- Round 4: `REVISE_CODE`, bound to `53eb40e` and v4; recorded in
  `docs/reviews/s03_e003_aa2024_code_review_round4_20261009.md`.
- Round 5: `PASS_CODE_READY`, bound to
  `f702a582d183f459234c1e293866d74b883d197b` and v5; recorded in
  `docs/reviews/s03_e003_aa2024_code_review_round5_20261009.md`.
- **Execution rule:** do not run the real archive audit before
  `PASS_CODE_READY`.

## Runs

| Run ID | Purpose | Execution | Retrieval | Receipt |
|---|---|---|---|---|
| S03-E003-R001 | outcome-blind manifest qualification | completed; controlled block | verified local | `data_audit.json`; `execution_receipt.json`; `decision.md`; `evidence_review_receipt.json`; `closure.md` |

## Evidence review

`PASS_EVIDENCE_REVIEW` on 2026-10-09, recorded in
`docs/reviews/s03_e003_aa2024_evidence_review_20261009.md`. The review was bound
to the exact compact output, execution receipt, and decision record; it
independently verified all three SHA-256 hashes and authorized bounded closure.

| Frozen manifest condition | Required | Observed | Result |
|---|---:|---:|---|
| Global connection files | 797 | 342 | fail |
| Global nodemap files | 797 | 342 | fail |
| Exact required mapping basename | 1 | 0 | fail |
| Higher-level metadata dictionary basename | 1 | 1 | pass |
| Timestep-level metadata dictionary basename | 1 | 1 | pass |

This decision table is the minimum visualization for the non-model `C1`
identity/manifest audit. A method-comparison figure is inapplicable because no
model or prediction outcome was evaluated.

## Scientific verdict

`BLOCKED_DATASET_CAPABILITY` for the bounded `C1` question. The immutable
archive passed identity and central-directory readability, then failed the
frozen manifest contract with
`GLOBAL_CONNECTION_COUNT_MISMATCH`, `GLOBAL_NODEMAP_COUNT_MISMATCH`, and
`MAPPING_FILE_IDENTITY_MISMATCH`. The allowed conclusion is only
`locked_archive_does_not_meet_declared_manifest_contract`.

A zero exact-basename count proves failure of the frozen naming requirement;
it does not prove that no differently named or functionally equivalent mapping
asset exists. The experiment does not support header semantics, chronology,
target support, phase-field recovery, material-property identification,
forecasting, broader dataset validity, or road transfer.

## Next action

None within S03-E003. The Experiment and AA2024 header-audit route are closed.
Do not inspect member headers or continue to phase-field/inversion/prediction
from this archive under this contract. Any renewed AA2024 route requires a new
qualified evidence axis and a separately frozen and reviewed Experiment.
