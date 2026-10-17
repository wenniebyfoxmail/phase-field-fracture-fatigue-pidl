# S01-E001-v7 independent producer-preflight review

Date: 2026-10-09  
Review mode: independent, read-only evidence audit  
Verdict: **PASS**

## Evidence checked

- Producer preflight report:
  `docs/reviews/S01-E001_v7_producer_preflight_20261009.md`
- Frozen v7 code-review bundle:
  `docs/research/S01/S01-E001/code_review_bundle.json`
- Frozen bundle SHA-256:
  `9697be804b0297f9c3595d2b04109b6350ea4b9b3daeca3c867a6f51546e81c8`
- Bound repository base commit:
  `dd738f177b5dbcced537a29497b4df3c38608a66`
- Evidence archive:
  `local_archive/experiments/pavetrack_s01_e001_v7/preflight/S01-E001-v7-preflight-evidence.zip`
- Evidence archive SHA-256:
  `8de089bb1e4d5e5913a90d74b94b830d909da0c8f684ad38503677ca577392c4`
- Frozen workbook SHA-256:
  `72e3cfe6774a45a7e348b6c30a21b5eae30fb7bc111c4859c26744bdc6061e18`

The active bundle was independently rehashed. Its SHA-256 remained unchanged,
and all 16 bound file hashes matched the inventory. The evidence ZIP passed
`unzip -t` without errors.

### Evidence-archive members

| Member | Bytes | SHA-256 |
|---|---:|---|
| `development_download_manifest.json` | 533,345 | `539823729537901391f0c6d4b6619c3ba04fcb053c0d0f374756f9b075b80fd4` |
| `manifest_train_validation.json` | 1,851,414 | `77125b9b292dad55811ce94c61e51181055c073ed657ba4343ce9b95064b7f5f` |
| `audit_receipt.json` | 890 | `db7e196f816daac219e46f274dd48c3562c1ffb903b7bf827237220c9cc7423b` |

The audit receipt's `manifest_sha256` matches the exact prepared manifest in
the ZIP. The prepared manifest's run-config and data-lock hashes match the
current frozen v7 files.

## Blocking findings

None.

## Nonblocking findings

1. The current public-ZIP workbook hash is reported in the producer preflight
   document but is not independently included as an artifact in the evidence
   ZIP. The consequential action is nevertheless verified: the archived frozen
   workbook exists locally at 2,366,362 bytes with SHA-256
   `72e3cfe6774a45a7e348b6c30a21b5eae30fb7bc111c4859c26744bdc6061e18`,
   and the prepared manifest is bound to that exact hash. Future rebuilds must
   continue using this archived workbook rather than silently adopting the
   workbook currently served by the public ZIP.
2. Runtime, semantic-model-load, and 29/29 test results are recorded in the
   producer preflight report rather than as separate raw logs in the evidence
   ZIP. This does not contradict the compact producer-prerequisite contract,
   but preserving machine-readable receipts would strengthen future
   provenance.

## Detailed reconciliation

### Frozen code and producer prerequisite

- The v7 bundle SHA-256 is unchanged and all 16 bound files still match.
- The preflight report records execution of all 29 frozen tests under the
  D-26-09 runtime with 29/29 passing.
- The reported producer identity matches the frozen runtime: `cuda:1`, physical
  GPU index 1, NVIDIA RTX PRO 6000 Blackwell Max-Q Workstation Edition, UUID
  `GPU-3d74ea12-5d84-a619-90b2-c0b1f104599a`, PCI bus ID
  `00000000:F1:00.0`, and NVIDIA driver `616.92`.
- The report records semantic loading of both frozen initialization artifacts,
  including the frozen YOLO architecture and instantiated one-class graph
  hashes, and strict MobileNet state-dict loading.
- No training was started during the preflight.

### Development-data acquisition

- Requested locations equal exactly the union of the 16 frozen train locations
  and 5 frozen validation locations.
- The structured location fields contain no confirmatory-test,
  previously-viewed-excluded, or reserve location.
- The download manifest contains 1,472 unique archive members and 1,472 unique
  target paths.
- Header counts reconcile with the records: 1,472 selected and extracted files,
  1,022,341,170 total extracted bytes, zero failed files, and an empty failures
  list.
- Statuses comprise 300 `already_complete_crc_verified` files and 1,172
  `downloaded_crc_verified` files, totaling 1,472.

### Prepared development dataset

- Protocol is `S01-E001-v7` and splits are exactly `train` and `validation`.
- Manifest locations equal exactly the frozen development-location union.
- Record count reconciles across the manifest and audit receipt: 1,467.
- Split counts reconcile: 1,165 train records from all 16 train locations and
  302 validation records from all 5 validation locations.
- Crack-target count reconciles at 1,442.
- Empty-label negative-image count reconciles at 34.
- Image IDs, prepared-image paths, and prepared-label paths are unique.
- Every recorded prepared-image and prepared-label hash has valid SHA-256
  syntax.
- The audit reports zero prepared-content mismatches, zero source-to-copy image
  mismatches, no unexpected prepared-tree files, and no errors.
- Every prepared source is present in the download manifest. The five
  downloaded-but-unprepared source files are all from location 24, consistent
  with workbook-first exclusion of archive files absent from the frozen
  workbook.
- `test_authorization` and `test_authorization_sha256` are both null, and the
  audit reports `test_directories_present: false`.

### Workbook drift

The public-ZIP workbook drift was handled correctly. The producer did not
substitute the reported current public workbook, whose reported SHA-256 is
`a1032a432e99fff92baa3b8b1a4e72b674dcd6b101acbbe03dba120884a1c475`.
Preparation used the archived frozen workbook instead. Its local byte count and
SHA-256 were independently rechecked, and the prepared manifest records the
same frozen identity. The drift is therefore a reproducibility warning for
future acquisition, not a failure of this development-data preflight.

## Claim boundary

This PASS closes only the S01-E001-v7 producer prerequisite. It establishes
that the frozen code, producer runtime, initialization artifacts, and
development-data preparation are executable and internally consistent on the
authorized producer. Under the road-fracture experiment gate, this is C0/C1
capability and evidence-validity evidence.

It authorizes progression to the preregistered development training and
validation workflow. It does **not** establish detector accuracy, reranker
improvement, a confirmatory-test result, downstream SAM2 justification,
transfer to another road network, physical crack state or growth, persistent
crack identity, fatigue mechanism, or future prediction.
