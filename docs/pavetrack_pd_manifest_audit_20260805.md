# PaveTrack_PD V3 manifest audit

Audit date: 2026-08-05.

## Decision

PaveTrack_PD now passes the **asset identity, exact observation time, repeated future observation, and annotated crack geometry** checks. It does not yet pass the registered-field check, and it cannot support traffic-temperature-moisture mechanism selection because those forcing streams are absent.

Therefore:

- Authorized: geometry-only reconstruction and forecasting feasibility after a registration/censoring audit.
- Not authorized: complete real-road Freeze-Then-Select validation or environmental mechanism claims.

## Publisher record

- DOI: [10.57760/sciencedb.20383](https://doi.org/10.57760/sciencedb.20383)
- ScienceDB dataset ID: `e9ffbca43e6e4a5ebdd25663d0de9ad1`
- Public version: `V3`
- License: `CC0`
- `PaveTrack_PD.zip`: `5,694,108,370` bytes
- Publisher-provided MD5: `7fc53a04a6260a26b3ac39f489511adf`
- Full archive was not downloaded, so the publisher MD5 was not independently recomputed.

The official server supports byte ranges. The audit read the ZIP central directory and selectively extracted only the small description workbook and four XML records; no JPG was downloaded.

## File-level findings

| Item | Finding |
|---|---:|
| ZIP entries | 9,107 |
| Location directories | 165 |
| JPG files | 8,936 |
| JPG files matching the timestamp convention | 8,918 |
| XML files | 4 |
| XLSX files | 1 |
| Earliest parsed image timestamp | `2022-04-18 06:55:03.885` |
| Latest parsed image timestamp | `2023-12-31 13:03:09.030` |
| Observations per location | min 4, median 50, max 124 |

Image names encode date and time to milliseconds, for example `2023-10-19_13-41-33-278-n00088.jpg`. The enclosing folder is the stable anonymized location key.

## Annotation schema

`Dataset_PDdescription.xlsx` contains one sheet with declared dimension `A1:F9448` and columns:

`reid`, `date`, `category`, `img_name`, `segmentation`, `bbox`.

The `segmentation` field contains polygon coordinates in image-pixel space; `bbox` contains an image-space bounding box. This proves that future geometry targets exist. It does **not** prove that pixels at two dates share a physical coordinate system. Camera/source suffixes vary and no calibration, homography, control points, or registration transform was found in the manifest.

The four XML files describe `plate` bounding boxes with `segmented=0`; they are desensitization annotations, not crack masks.

## Remaining geometry gate

Before training a field adapter on PaveTrack_PD:

1. Select a small set of long trajectories, preferably locations with at least 50 observations.
2. Download only those location images by HTTP range or a bounded archive extraction.
3. Test whether static pavement texture supports cross-date homography or dense registration.
4. Quantify registration residuals against crack width and tip displacement.
5. Detect maintenance/disappearance and distinguish repair, occlusion, missed annotation, and terminal censoring.
6. Freeze a chronological split and a separate location holdout before model fitting.

If registration residuals are too large or maintenance semantics cannot be reconstructed, PaveTrack_PD remains a detection/tracking dataset and must not be used for physical crack-tip or initiation-time claims.

## Preserved evidence

The selectively extracted workbook, four XML files, raw ScienceDB version response, and SHA-256 list are stored under:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/pavetrack_pd_v3_manifest_20260805/`

The machine-readable receipt is `pavetrack_pd_manifest_audit_20260805.json`.
