# PaveTrack_PD registration gate

Audit date: 2026-08-05.

## Decision

The first bounded physical-registration route fails. Five annotated transverse-crack images from location `10` do not form a connected, trustworthy coordinate system. PaveTrack_PD remains useful for scene-level distress tracking and segmentation, but this sample cannot support physical crack-tip, crack-length, initiation-time, or continuous damage-field claims.

This is a route-level decision for the audited sample, not a claim that every PaveTrack location is impossible to register.

## Frozen sample

The five dates were selected before registration:

`2023-06-01`, `2023-07-01`, `2023-08-17`, `2023-09-11`, `2023-10-19`.

All images belong to anonymized location `10` and are annotated as transverse crack observations in `Dataset_PDdescription.xlsx`. The images and SHA-256 list are preserved under:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/pavetrack_pd_v3_registration_sample_20260805/location_10/`

## Registration test

The test used SIFT features in the road ROI (`y >= 250`), Lowe ratio `0.72`, and a RANSAC planar homography with a `3 px` threshold. The reference was `2023-07-01`.

| Source date | Good matches | RANSAC inliers | Crack-center error | bbox IoU | Decision |
|---|---:|---:|---:|---:|---|
| 2023-06-01 | 138 | 80 | 9.42 px | 0.678 | usable |
| 2023-08-17 | 13 | 4 | 1074.89 px | 0.000 | invalid homography |
| 2023-09-11 | 11 | 6 | 1080.34 px | 0.000 | invalid homography |
| 2023-10-19 | 30 | 12 | 4.67 px | 0.912 | geometrically plausible, low support |

An all-pairs graph audit then required at least 30 matches, 20 inliers, inlier ratio `0.3`, median reprojection error at most `3 px`, frame overlap at least `0.2`, and crack-center error at most `40 px`. Only the 2023-06-01 to 2023-07-01 edge passed. The five dates were not connected.

## Interpretation

The location folder is a repeat-scene key, not a supplied physical coordinate frame. Camera position, lane position, traffic occlusion, illumination, and perspective vary substantially. A low RANSAC residual based on four to six inliers is not evidence of registration; the transformed crack position exposes these degenerate solutions.

Manual control points could force these five images into rough alignment, but doing so would not establish a reproducible dataset-scale route. We therefore do not continue to field reconstruction or neural training on this sample.

## Consequence for the active goal

- PaveTrack can still test image-level segmentation, tracking, and annotation persistence.
- It cannot presently validate physical crack tip or initiation timing.
- It contains no traffic, temperature, moisture, structure, or mechanical series, so it cannot validate FTS mechanism selection.
- The next real-road acquisition routes are MnROAD Cell 22 and an exact LTPP section extraction.

Raw pairwise and reference-frame metrics are preserved in `registration_metrics.json` and `pairwise_registration_metrics.json`; the compact receipt is `pavetrack_pd_registration_gate_20260805.json`.
