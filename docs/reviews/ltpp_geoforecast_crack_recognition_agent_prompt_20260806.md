# Agent execution prompt: LTPP distress-map crack recognition v1

Copy everything below this line into the executing agent.

---

You are working in:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code`

Your goal is to qualify a reproducible, human-auditable method for recognizing
crack geometry from scanned LTPP hand-drawn distress maps. This is a new
recognition track. It is not a continuation of the enriched-input forecast or
spatial-registration experiment, and it must not change their results.

## Read first

1. Repository rules:
   `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/AGENTS.md`
2. Background and literature boundary:
   `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/experiments/ltpp_geoforecast_background_knowledge.md`
3. Annotation and forecasting protocol:
   `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/ltpp_geoforecast_annotation_forecast_protocol_20260805.md`
4. Original nine-map semantic-vectorization protocol:
   `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/ltpp_06_1253_semantic_vectorization_protocol_20260805.md`
5. Current scalar track:
   `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/experiments/ltpp_geoforecast_enriched_input_track.md`
6. Current spatial-registration track:
   `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/experiments/ltpp_geoforecast_spatial_registration_track.md`

## Frozen input locations

Raw blind map images:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/primary/images`

Frozen adjudicated GeoJSON labels:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/adjudicated/geojson`

Canonical adjudication manifest:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/adjudicated/adjudicated_manifest.json`

Current manifest status is `PASS_ADJUDICATED_LABELS_FROZEN` with 37 states,
249 total geometries, and 232 crack geometries. Verify these values and hashes
yourself before using them. Do not edit or overwrite anything under the frozen
packet. Write generated payloads to a new directory under:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/`

## Scientific target

Determine whether scanned distress maps can be converted into reliable crack
centerlines and crack-family labels while rejecting printed grids, road/frame
boundaries, handwriting, arrows, dimensions, WIM/patch boxes, area hatching,
and other noncrack marks.

This task recognizes the current map. It does not forecast a future map,
establish physical crack width, identify material points across dates, or repair
the failed spatial-registration gate.

## Required track documents

Before reading any held-out score, create:

1. Canonical track document:
   `docs/experiments/ltpp_geoforecast_crack_recognition_track.md`
2. Dated v1 preregistration:
   `docs/experiments/ltpp_geoforecast_crack_recognition_preregistration_v1_20260806.md`

The canonical track must own the mechanism question, claim boundary, input
hashes, experiment registry, active gate, current status, and next action. Only
after those documents and receipts are updated may you make a short linked
status update in `docs/research_frontier.md`.

## Stage 1: read-only qualification

First perform a read-only inventory and report:

- exact image dimensions, colour modes, hashes, and map count;
- exact GeoJSON coordinate system, families, geometry types, and uncertainty;
- image-to-label mapping and whether any mapping relies on currently sealed or
  unavailable information;
- section membership and the exact six section-level held-out folds;
- whether every adjudicated geometry can be rasterized into the image frame;
- class balance by section and by crack family;
- examples and counts of likely confounders: grid, frame/road boundaries,
  handwriting, arrows/dimensions, WIM/patch boxes, hatching, and other distress;
- whether any data or package is missing, inconsistent, or mutable.

Fail closed if image-label mapping, coordinates, hashes, section membership, or
rasterization cannot be made deterministic. Do not rescue a failed gate by
dropping maps or geometries after seeing performance.

## Stage 2: freeze the experiment

Freeze the following before held-out evaluation:

- row/map set and SHA-256 receipt;
- leave-one-section-out split receipt; random crop-level train/test splits are
  forbidden;
- exact target families and treatment of `uncertain` and noncrack distress;
- exact line-to-mask rasterization width and any distance tolerance;
- input normalization and any grid/text removal rules;
- algorithm implementations, seeds, versions, and model weights;
- hyperparameter-selection procedure confined to training sections;
- primary metric, secondary metrics, baselines, and success rule.

Do not use chronology, survey date, future maps, another held-out map, forecast
outcomes, traffic, climate, FWD, or maintenance information to tune recognition.

## Candidate methods

Evaluate the smallest auditable set under the same frozen folds:

1. `B0`: deterministic document/image-processing baseline using only frozen
   morphology, colour, connected-component, and line/grid-rejection rules.
2. `B1`: a lightweight semantic-segmentation candidate such as U-Net or
   SegFormer, trained only after the split and rasterization rules are frozen.
3. `B2`: SAM or another foundation model used for assisted/pseudo-labelling or
   parameter-efficient adaptation. Generic zero-shot masks must not be called
   ground truth.

Do not run a model zoo or choose whichever architecture looks best on held-out
sections. If compute, dependencies, or sample size make B1/B2 scientifically
invalid, stop with a documented qualification result rather than forcing a
training result. Follow repository machine rules; do not launch PIDL/FEM
training as part of this task.

## Mandatory baselines and audit metrics

Report every metric pooled and separately for each held-out section.

Primary recognition metric:

- centerline precision, recall, and F1 after one preregistered physical-distance
  tolerance, with uncertainty excluded by the frozen rule.

Secondary metrics:

- crack-length MAE and signed bias in metres;
- family-aware geometry precision, recall, and F1;
- endpoint distance for matched line geometries;
- connected-component and branch-count error;
- pixel or buffered-mask precision, recall, F1, IoU, and topology-aware clDice;
- false positives stratified by grid, boundary, handwriting, arrow/dimension,
  WIM/patch, hatching, and other noncrack distress;
- false negatives stratified by crack family and visible stroke quality;
- inference time, parameter count, and any human correction time for assisted
  annotation.

Accuracy alone is forbidden because background pixels dominate. Bounding-box
mAP alone is insufficient because the downstream target is centerline length
and topology.

## Success and claim gate

The v1 route may be called recognition-qualified only if the preregistration
freezes and then the held-out evaluation demonstrates all of:

1. pooled centerline F1 at least 0.80;
2. pooled mean centerline distance at most 0.10 m for matched lines;
3. pooled matched endpoint distance at most 0.20 m;
4. improvement over B0 in at least four of six held-out sections;
5. no held-out section with centerline recall below 0.70;
6. all confounder categories are reported, with no category silently removed;
7. no map, geometry, or difficult family is removed after split freeze; and
8. all inputs, code, split, environment, and output receipts are hashed.

These thresholds qualify recognition on this frozen carrier only. They do not
authorize future spatial prediction, cross-date material-point claims, or use
on ordinary road photographs.

If the gate fails, report the failure and the dominant error modes. Do not
change tolerance, rasterization width, target family, metric, split, or
architecture after seeing held-out results. Any revised route must be a new
dated amendment or experiment.

## Human audit requirements

For every held-out map, generate a reviewable triptych or four-panel view:

1. untouched original map;
2. adjudicated gold geometry;
3. model prediction;
4. error overlay distinguishing TP, FP, and FN.

The original must always remain visible because overlays can obscure the
source stroke. Inspect representative successes and every large-error case.
Record whether the error is caused by the model, ambiguous source semantics,
annotation width, or coordinate/rasterization error. Human review may classify
errors but must not alter the frozen held-out score.

## Deliverables

- canonical track document and v1 preregistration;
- input, split, environment, and code receipts with SHA-256 hashes;
- read-only qualification report;
- implementation and tests, if the preflight authorizes them;
- compact result document with pooled and six-section metrics;
- per-map visual audit artifacts, each with the required research-figure
  sidecar under repository rules;
- concise `docs/research_frontier.md` update only after the track document is
  current;
- final handoff stating exactly one of:
  `BLOCKED_BEFORE_FIT`, `RECOGNITION_GATE_FAILED`, or
  `RECOGNITION_QUALIFIED_ON_FROZEN_CARRIER`.

Preserve all unrelated dirty-worktree changes. Do not commit or push unless the
user separately authorizes it.
