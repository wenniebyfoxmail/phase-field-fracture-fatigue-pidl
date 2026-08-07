# Experiment Record: LTPP-GeoForecast AI Primary Batch 01

**Experiment ID:** `ltpp_geoforecast_ai_primary_batch01_20260805`  
**Status:** completed; workflow qualified for bounded expansion  
**Role:** independent AI primary annotator  
**Scope:** first five currently unlocked blind primary maps  
**Started:** 2026-08-05

## Purpose

Qualify the independent AI-primary annotation workflow on a bounded five-map batch before allowing expansion to all 37 multisection states. The batch tests whether the frozen workbench, distress-family semantics, uncertainty disposition, and map-locking rules can be applied without opening the human secondary labels or sealed asset mapping.

## Frozen boundaries

- Read only the assigned `primary` role images and LTPP legend.
- Do not open `secondary`, `sealed_do_not_open_during_annotation`, chronological maps, automatic crack candidates, pairing results, or model outputs.
- Label every visible candidate as crack centreline, explicit distress polygon, boundary, handwriting/calculation, or uncertain/unresolved.
- Lock a map only when every visible candidate has a disposition.
- Stop after five attempted unlocked maps; this record does not authorize all 37.
- Do not interpret annotation completion as ground truth or model evidence.

## Current progress

The bounded batch completed without a workflow or blindness failure.

| Blind ID | Geometry count | Status |
|---|---:|---|
| `P001` | 24 | locked |
| `P002` | 8 | locked |
| `P003` | 7 | locked |
| `P004` | 20 | locked |
| `P005` | 26 | locked |

Batch totals:

- attempted: 5;
- locked: 5;
- unresolved/unlocked: 0;
- recorded geometries: 85;
- `P006-P037`: untouched and unlocked.

`P002` was retained as a no-crack negative example rather than converting text, arrows, or table lines into cracks. An ambiguous rectangular region in `P004` was explicitly labelled `uncertain`; it was not silently omitted. The primary-only server was closed after the batch. Secondary labels, the sealed mapping, chronological maps, automatic candidates, model outputs, and pairing results were not opened.

The frozen multisection inventory currently contains six sections and 37 qualified `0-50 ft` states. The human role has eight migrated locked maps according to the packet handoff, with the remaining human and AI passes still incomplete. Pairing, adjudication, unseen-section forecasting, and Freeze-Then-Select/PIDL comparison remain downstream.

## Visual checkpoint

- PNG: `docs/figures/ltpp_freeze_select_progress_20260805.png`
- PDF: `docs/figures/ltpp_freeze_select_progress_20260805.pdf`
- Reproduction script: `scripts/plot_ltpp_research_progress_20260805.py`

## Required completion update

When the bounded task returns, append:

- exact blind IDs attempted;
- number locked and unresolved;
- role-local output paths;
- any workbench or semantic failure;
- decision: expand, revise workflow, or stop.

Only a one-line status and decision should be synchronized to `docs/research_frontier.md`.

## Batch decision

**Decision:** `QUALIFY_PRIMARY_WORKFLOW_FOR_BOUNDED_EXPANSION`

The workflow may expand through additional small primary-only batches with the same fail-closed rules. This decision qualifies annotation procedure only; it does not qualify the labels as benchmark truth and does not authorize pairing, forecasting, or model selection.

## Role-local evidence

- Batch record: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/primary/qc_batch_001_005/batch_qualification.md`
- `P001` overlay: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/primary/qc_batch_001_005/P001_locked_overlay.png`
- `P002` overlay: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/primary/qc_batch_001_005/P002_locked_overlay.png`
- `P004` overlay: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/primary/qc_batch_001_005/P004_locked_overlay.png`
- `P005` overlay: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/primary/qc_batch_001_005/P005_locked_overlay.png`

