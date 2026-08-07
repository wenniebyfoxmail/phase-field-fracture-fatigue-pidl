# Experiment Record: LTPP-GeoForecast AI Primary Batch 02

**Experiment ID:** `ltpp_geoforecast_ai_primary_batch02_20260805`  
**Status:** completed; workflow qualified for bounded continuation  
**Role:** same independent AI primary annotator as Batch 01  
**Scope:** blind IDs `P006-P010` only  
**Started:** 2026-08-05

## Purpose

Continue the qualified primary-only workflow on the next bounded five-map batch while testing whether the Batch 01 annotation semantics remain usable on new blind maps. This is controlled expansion, not authorization for all remaining maps.

## Frozen boundaries

- Open only primary `P006-P010` and the LTPP legend.
- Do not open secondary, sealed mapping, chronological maps, automatic candidates, pairing results, or model outputs.
- Preserve explicit `uncertain` dispositions rather than forcing crack labels.
- Lock only maps with complete candidate-stroke disposition.
- Stop after `P010` or immediately on a workbench, blindness, or unresolved semantic failure.

## Pending outputs

- exact attempted and locked IDs;
- geometry counts by map;
- unresolved and negative-map dispositions;
- role-local QC overlays and batch record;
- decision to expand, revise, or stop.

## Result

| Blind ID | Geometry count | Status | Key disposition |
|---|---:|---|---|
| `P006` | 0 | locked | explicit grid-only negative map |
| `P007` | 1 | locked | sole solid line retained as non-crack reference boundary |
| `P008` | 16 | locked | three fatigue areas and three low/medium-confidence longitudinal lines |
| `P009` | 20 | locked | crack marks separated from WIM facility boundaries |
| `P010` | 15 | locked | seven fatigue areas; no centreline crack invented |

- attempted: 5;
- locked: 5;
- unresolved maps: 0;
- uncertain geometries: 0;
- new geometries: 52;
- cumulative AI-primary progress: 10/37 locked.

Blindness was preserved and the temporary primary server was closed. Batch record: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/primary/qc_batch_006_010/batch_qualification.md`.

**Decision:** `CONTINUE_BOUNDED_PRIMARY_BATCHES`

