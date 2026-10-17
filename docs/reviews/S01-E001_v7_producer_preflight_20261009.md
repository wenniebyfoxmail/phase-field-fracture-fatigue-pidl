# S01-E001-v7 producer preflight

Date: 2026-10-09  
Producer host: `D-26-09` (`gpu-server`)  
Remote staging directory: `C:\Users\xw436\pavetrack_stage\S01-E001-v7-preflight-20261009`  
Decision: **PASS — ready for development training, but training was not started**

## Scope

This preflight checked the exact bundle approved by the independent v7 review.
It did not prepare or inspect the confirmatory test locations. It did not start
proposer or reranker training.

## Frozen bundle

- Protocol: `S01-E001-v7`
- Bundle SHA-256: `9697be804b0297f9c3595d2b04109b6350ea4b9b3daeca3c867a6f51546e81c8`
- Bound files checked: 16/16 matched
- Independent review: `docs/reviews/S01-E001_code_review_v7_result.md`
- Independent review verdict: `PASS`

## Producer runtime and model artifacts

The producer runtime gate passed on the frozen physical GPU:

- Device: `cuda:1`
- GPU: NVIDIA RTX PRO 6000 Blackwell Max-Q Workstation Edition
- GPU UUID: `GPU-3d74ea12-5d84-a619-90b2-c0b1f104599a`
- PCI bus ID: `00000000:F1:00.0`
- NVIDIA driver: `616.92`

The frozen model artifacts were loaded semantically, not only hashed:

- `yolo11n.pt`: SHA-256
  `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1`
- YOLO initial architecture: SHA-256
  `1328d9af277ef6ffff67b626d3a34e57a198b350e022dedd35a963533981e45e`
- Instantiated one-class YOLO graph: SHA-256
  `7ef6dcc31d16e8a42e65b71b7848df0e47976052b74a22f4b0dc37b80fdcb8ae`
- `mobilenet_v3_small_imagenet.pth`: SHA-256
  `047dcff4addef86ea5bc2eff13c9614dc11f47ab1160d0a71a25e7db994f4e1f`
- MobileNet strict state-dict load: all keys matched

## Tests

Command:

```text
C:\Users\xw436\pavetrack_env\Scripts\python.exe -m unittest discover -s tests\pavetrack_cv -p test_*.py -v
```

Result: **29/29 passed**.

## Development-data acquisition

Only the 16 frozen train locations and 5 frozen validation locations were
requested. The four test locations and both excluded pilot locations were not
requested.

- Source archive size: 5,694,108,370 bytes
- Development source images selected: 1,472
- Downloaded or resumed: 1,472/1,472
- Downloaded bytes: 1,022,341,170
- Size and ZIP CRC checks: 1,472/1,472 passed
- Failed files: 0

The first 300 files were acquired before the source server returned HTTP 429.
The resumable extractor then verified those 300 files again and fetched the
remaining files in 31 contiguous byte ranges. This reduced the number of HTTP
requests and completed without damaged files.

Download manifest SHA-256:
`539823729537901391f0c6d4b6619c3ba04fcb053c0d0f374756f9b075b80fd4`.

## Workbook drift found during preflight

The workbook currently stored in the public ZIP is not byte-identical to the
workbook bound by the frozen protocol:

- Current public-ZIP workbook: 1,566,720 bytes; SHA-256
  `a1032a432e99fff92baa3b8b1a4e72b674dcd6b101acbbe03dba120884a1c475`
- Frozen workbook: 2,366,362 bytes; SHA-256
  `72e3cfe6774a45a7e348b6c30a21b5eae30fb7bc111c4859c26744bdc6061e18`

The public workbook was therefore not substituted. The exact frozen workbook
was copied from the local archive and its hash was checked again on D-26-09.
The frozen copy remains at:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/pavetrack_pd_v3_manifest_20260805/Dataset_PDdescription.xlsx`

This is a reproducibility warning, not a failed development-data gate. A future
rebuild must use the archived frozen workbook, not silently use the workbook
currently served by the public ZIP.

## Prepared development dataset

The frozen preparation script passed its runtime and workbook gates. It used
the workbook to remove five extra source images from location 24.

- Prepared records: 1,467
- Train: 1,165 images from 16 locations
- Validation: 302 images from 5 locations
- Crack targets: 1,442
- Empty-label negative images: 34
- Prepared image hash mismatches: 0
- Prepared label hash mismatches: 0
- Source-to-copy image hash mismatches: 0
- Unexpected files in the prepared image or label trees: 0
- Test directories present: false

Prepared manifest SHA-256:
`77125b9b292dad55811ce94c61e51181055c073ed657ba4343ce9b95064b7f5f`.

Independent audit receipt SHA-256:
`db7e196f816daac219e46f274dd48c3562c1ffb903b7bf827237220c9cc7423b`.

## Evidence archive

The download manifest, prepared manifest, and independent audit receipt were
copied back to the Mac in one verified ZIP:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/pavetrack_s01_e001_v7/preflight/S01-E001-v7-preflight-evidence.zip`

ZIP SHA-256:
`8de089bb1e4d5e5913a90d74b94b830d909da0c8f684ad38503677ca577392c4`.

The local ZIP passed `unzip -t` with no errors.

## Claim boundary

This PASS means that the frozen code, runtime, model initialization artifacts,
and development-data preparation are executable and internally consistent on
the authorized producer. It does not show that the detector is accurate, that
the reranker improves it, or that the method transfers to other roads. Those
questions require the preregistered development training and validation run.
