# Experiment Record: LTPP-GeoForecast AI Primary Batch 04

**Experiment ID:** `ltpp_geoforecast_ai_primary_batch04_20260805`  
**Status:** completed; bounded continuation qualified  
**Role:** same independent AI primary annotator  
**Scope:** blind IDs `P016-P020` only

## Purpose and boundaries

Continue bounded primary annotation after three qualified batches. Open only primary `P016-P020`; preserve the established semantic and blindness rules; lock only fully disposed maps; stop immediately on workflow, writer-conflict, blindness, or unresolved semantic failure. Do not touch `P021-P037` or shared protocols.

## Pending result

Record per-map geometry counts, locked/unresolved status, negative and uncertain dispositions, QC paths, cumulative primary progress, and the decision to continue or stop.

## Result

| Blind ID | Geometry count | Status | Key disposition |
|---|---:|---|---|
| `P016` | 25 | locked | lower-right bent line retained as low-confidence uncertain |
| `P017` | 21 | locked | two longitudinal and five transverse cracks |
| `P018` | 18 | locked | WIM outline explicitly retained as non-crack boundary |
| `P019` | 9 | locked | non-crack map containing facility boundaries and handwriting |
| `P020` | 7 | locked | one longitudinal and two transverse cracks |

- locked: 5/5;
- new geometries: 80;
- unresolved maps: 0;
- uncertain geometries: 1;
- cumulative primary progress after this batch: 20/37;
- blindness preserved.

Batch record: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/primary/qc_batch_016_020/batch_qualification.md`.

**Decision:** `HAND_OFF_REMAINING_PRIMARY_TO_ISOLATED_CONTEXT`

The parallel annotation task subsequently froze the complete human-secondary role. To preserve independence, `P021-P037` were therefore handed to an isolated AI context that did not inherit the human-label discussion. This thread must not resume primary annotation.

