# D01 reference interface — working proposal, 2026-10-14

Status: local proposal and existing-output coverage audit; not a frozen new prediction experiment. E015/E016/E017 definitions, scores, annotations and human-preparation UI remain unchanged. No new annotator dispatch or external transmission.

## Decision to make

Recommended route: retain E015's **five-line-median transverse half-depth image width**, in first-frame native pixels within each beam. Treat central-row visible-edge AI/human annotation as a separate ambiguity/localisation check, not the truth for that width. This preserves the informative development signal without changing its meaning.

Alternative: predict central-row visible dark-boundary width. That requires a new protocol with the SAME definition at history, origin and target stages; old E015 predictions cannot silently become predictions of this new variable. User choice is pending. Neither route claims physical aperture in mm, fatigue state or phase-field damage.

## Existing data and exact missing work

Inventory sources: E015-D01-R001 `profile_measurements.csv` and `individual_forecasts.csv`; E017-D01-R001 `unique_task_comparison.csv`. No private answer key is needed. Supplemental audit: `S03-REFCOV-20261014-R001`, archive under `local_archive/diagnostics/`.

| Beam | Fixed-camera stages (kN) | Existing next-stage targets | AI crop-labelled stages | Targets without AI labels |
|---|---|---|---|---|
| 4 | 10, 30, 40, 50 | 40, 50 | 10, 50 | 40 |
| 5 | 10, 20, 30, 40, 50, 60 | 30, 40, 50, 60 | 10, 60 | 30, 40, 50 |
| 6 | 10, 20, 30, 40 | 30, 40 | 10, 40 | 30 |

All 14 stages already have 12 measured transects each. The current AI package checks only transects 3/6/9/12 at six first/last stages; its 24 unique crops include 16 visible and eight uncertain. Its three labelled final target stages therefore do NOT supply complete or same-definition reference coverage. Five intermediate target stages have no AI labels at all. For a visible-width route, history/origin coverage must also be added. Human reference in these owning records remains pending; no physical width reference is established.

## Minimal state interface to freeze before further prediction scoring

| Field | Current/proposed interpretation |
|---|---|
| `specimen_id`, `stage_index`, `nominal_stage_kN`, `transect_id`, `view_id` | Beam-stage-transect identity; fixed IB view only for this route |
| `measurement_definition_id`, `value`, `unit`, `valid`, `missing_reason` | E015 half-depth observable OR new visible-edge observable, never implicitly interchangeable; pixel unit per beam |
| `source_role` | observation / prediction / AI auxiliary / human auxiliary / qualified reference; region role crack/control stays separate |
| `available_through_stage` | Maximum input stage; origin-time eligibility must not use target visibility |
| `reference_available`, `reference_definition_id`, `reference_exposure` | Separate reference scoring support from deployment eligibility; uncertain is not zero |
| `next_load_availability`, `schedule_source` | Old code uses retrospectively indexed next nominal load. Origin-time schedule availability is assumed, not yet independently documented |
| `coordinate_frame`, `registration_source` | Per-beam first-frame native coordinates; retain stored registration provenance and its limitation |
| `evaluation_role` | All already-viewed beams are development; same-beam future continuation differs from new-beam generalisation |

These are proposed interface fields, not fields claimed already present in every old CSV. No synthetic timestamps, physical scale or qualified reference values may be invented.

## Smallest executable repair after choosing the observable

1. **Keep half-depth width (recommended):** first arrange an independent implementation/definition check on the unchanged native profiles and stored transforms, alongside blind visual ambiguity checks. This can establish reproducible computation of an image-defined observable, NOT physical width accuracy. Freeze origin-only eligibility and retrospective conditional-load semantics. Any new diagnostic rescore remains development evidence; physical/reference accuracy needs a separate matched measurement source.
2. **Choose visible-edge width:** prepare a new all-needed-stage blind package from unchanged first-frame transects, preserving uncertainties and no algorithm overlays. Freeze labels before joining outputs. New-context AI repeat reading is a procedural check only; qualified human/reference measurements and same-definition histories remain necessary for measurement or forecast validation. No new agent is dispatched by this draft.
3. **Future evaluation:** persistence versus secant, last two observed widths only, next declared nominal load conditional. One-step observation-updated predictions, not autonomous rollout. One primary comparison: beam-equal paired MAE difference on predeclared common support. Calibrate a meaningful margin from qualified reference/repeatability before formal acceptance; otherwise report descriptive differences, not a pass/fail threshold.

Do not add a neural model to solve a missing-reference problem. Preserve components separately: existing temporal signal, localisation robustness, annotation ambiguity, reference coverage and acquisition-time information. A missing reference limits what can be concluded, not whether the pipeline work was useful.

## Delivery and verification

The coverage script only counts existing outputs and validates their joins. It does not access pixels, detect boundaries, annotate, train, tune, read the private key or recompute forecast scores. Table and coverage figure are generated from the same rows; input SHA-256 hashes and code identity are recorded in `audit_receipt.json`. Generated data and figures remain local; compact summary may be copied to this directory after verification.

Completed 2026-10-14: the inventory assertions passed for 14 stages / 168 measured profiles, 24 unique AI crops, and eight existing forecast pairs. The PNG was visually inspected; PNG/PDF share a validated explanatory sidecar. Runtime 0.53 s on Mac (lightweight inventory only). All reference-qualification zeros are protocol/status assessments from these inspected records, not estimated numerical errors. No forecast score was recomputed. This script has not received independent code review and is not new measurement qualification.

- [Coverage figure](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/diagnostics/S03-REFCOV-20261014-R001/stage_reference_coverage.png)
- [Exact stage ledger](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/diagnostics/S03-REFCOV-20261014-R001/stage_reference_coverage.csv)
- [Source hashes and audit receipt](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/diagnostics/S03-REFCOV-20261014-R001/audit_receipt.json)
