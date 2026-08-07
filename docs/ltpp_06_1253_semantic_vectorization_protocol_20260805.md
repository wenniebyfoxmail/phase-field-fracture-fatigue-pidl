# LTPP 06-1253 independent semantic vectorization protocol

## Purpose

Convert the nine qualified physical-grid drawings into reviewable crack centerlines and mapped distress extents without using future surveys or failed automatic candidates as hidden labels.

This is a label-qualification step, not model training. The automatic candidate packages `v1` through `v5` failed visual semantic QC and are forbidden as primary labels.

## Frozen inputs

Use only `rectified_grid.png` files under:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_rectified_grid_v3_20260805`

The primary annotator must not see:

- the survey date or chronological order;
- another survey map from the section;
- any automatic candidate overlay;
- traffic, climate, FWD, or model output;
- the primary or secondary annotation from another reviewer.

A fixed random seed must assign the nine maps blind IDs. The date mapping stays sealed until both annotation passes are locked.

## What to trace

Trace the visible centreline of each line-type distress stroke and the mapped boundary of each area-type distress that can be distinguished from the printed survey form. Store coordinates in metres in the local road frame:

```text
x_m = x_pixel / 100
y_m = (500 - y_pixel) / 100
```

Use one GeoJSON `LineString` per visible line-type crack branch. Split a network at visible branch junctions. Use one GeoJSON `Polygon` for a mapped area-type distress such as fatigue/alligator or block cracking. A polygon records the surveyor's mapped distress extent, not individual crack branches or natural crack morphology. Do not trace `X` symbols, hatching, labels, or the rectangle stroke itself as crack centrelines. Do not manufacture continuity across an ambiguous annotation or erased region.

Assign one family:

- `transverse_crack`;
- `longitudinal_crack`;
- `fatigue_or_alligator_crack`;
- `block_crack`;
- `other_crack`;
- `uncertain`.

Geometry-family rules:

- `LineString`: `transverse_crack`, `longitudinal_crack`, `other_crack`, or `uncertain`;
- `Polygon`: `fatigue_or_alligator_crack`, `block_crack`, `other_crack`, or `uncertain`.

`uncertain` is a valid and necessary output. It is excluded from confirmatory geometry and support-selection metrics.

## What not to trace

- regular point or solid grid lines;
- the rectangular map frame;
- long lane and shoulder boundaries;
- handwritten labels such as `4BM`, `6L`, or severity notes;
- `X`, hatching, or other fill symbols inside a mapped distress area;
- circles around labels;
- arithmetic, dimensions, dates, or sheet-summary marks;
- a line visible only in a different survey.

Drawn stroke width is not physical crack width. The label package contains centreline geometry only.

## Independent review

1. The primary annotator completes all nine blind maps and locks the GeoJSON files.
2. The second annotator independently repeats the task with a different blind-ID permutation and no access to primary labels.
3. A matching script pairs lines using centreline distance and tip proximity after both sets are locked.
4. Every unmatched or family-disagreed line is adjudicated while dates remain blinded.
5. Automatic v1-v5 overlays may be inspected only after primary and secondary locks, and only as error-analysis aids.
6. The blind-ID/date mapping is unsealed after adjudication.

## Qualification gate

The reviewed package passes only if:

- every primary line has a review decision;
- every unmatched line is adjudicated;
- matched mean centreline distance is at most `0.10 m`;
- matched tip distance is at most `0.20 m`;
- matched mean area IoU is at least `0.65`;
- matched mean area-centroid distance is at most `0.20 m`;
- geometry-level F1 is at least `0.80`;
- uncertain lines are retained but excluded from confirmatory metrics;
- source and output files have SHA-256 manifests.

Failure does not authorize threshold relaxation after viewing dates. The resolution is another blinded annotation pass or explicit reduction of the supported claim.

## Time-series interpretation after unsealing

Crack initiation remains interval-censored. If a centreline is absent at survey `t_i` and present at `t_{i+1}`, the only authorized statement is:

```text
initiation occurred in (t_i, t_{i+1}]
```

The maps may contain redraw and survey inconsistency. Apparent disappearance cannot be silently forced to obey damage irreversibility. Such cases must be flagged before fitting a continuous field.

## Handoff to Freeze-Then-Select

Only the adjudicated, hashed GeoJSON package can enter the field adapter. The next modelling stage must then:

1. rasterize centreline distance fields and area-distress occupancy fields on the common physical grid;
2. freeze leakage-safe temporal folds before fitting;
3. reconstruct and freeze the continuous damage field without equation selection;
4. perform weak selection across seed, time-window, spatial-section, and test-function perturbations;
5. compare against single-shot and joint-training baselines.

Until this vectorization gate passes, the real-road branch has a qualified coordinate carrier but no qualified damage target.

## Local annotation interface

Launch only one role at a time. The server exposes that role's nine blind IDs and does not route the sealed mapping or the other role directory.

Primary pass:

```bash
/Users/wenxiaofang/miniconda3/bin/python3 \
  "/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_vector_annotator_server.py" \
  --packet-root "/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_blind_vectorization_v1_20260805" \
  --role primary --host 127.0.0.1 --port 8765
```

Secondary pass, performed independently and on a separate browser session:

```bash
/Users/wenxiaofang/miniconda3/bin/python3 \
  "/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_vector_annotator_server.py" \
  --packet-root "/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_blind_vectorization_v1_20260805" \
  --role secondary --host 127.0.0.1 --port 8766
```

Open the printed local URL in a browser. Each finished line is stored in physical metres. `Save draft` remains editable; `Lock this map` is irreversible through the interface and causes the server to reject later writes.

The primary interface received a read-only smoke check on 2026-08-05: the page, nine-map API, and `P01` image route returned HTTP 200. No label was written or locked during that check.
