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

2026-10-15 decision: user chooses the recommended existing half-depth observable.
The choice above is no longer pending. [E018 independent computation/location
audit](S03-E018-D01/experiment.md) completed: reproducible computation, with
Beam4 local-correspondence risk selecting the next repair. This resolves the
observable choice, not the human/physical-reference or future-load-availability
gaps; visible-edge width remains a different, unselected target.

## 2026-10-15 read-only refinement — NOT a frozen evaluation protocol

This supplement updates the current plan without rewriting earlier decisions,
E015 scores, annotation answers or used protocols. Snapshot9112e549f15b8afc25628c08911ccfef48930025.
Only existing tracked records/code and the prior read-only memo were inspected;
no raw archive, sealed holdout, private answer key, new source download, script
execution, annotation, fit, registration, diagnostic or scoring in this review.
Shared Obsidian/Roadmap are left to the coordinating chat, unchanged here.

### A. What changed since the earlier review

| Item | Current evidence | What remains open |
|---|---|---|
| Observable choice | User selected retaining E015 point half-depth width; previous “choice pending” is historical | No switch to visible-edge or segment-median target |
| Same-definition computation | E018 independently reproduced all168 profiles/widths and raw-image quantised sampling exactly | Shared geometry/H are not independent physical coordinates or aperture truth |
| Background correspondence | E019 modest proxy improvement, typical paired width sensitivity change0 | Physical position correspondence unqualified |
| Spatial width response | E020 records spatial response and sparse half-level connectivity candidates, not disjoint-band switching | No-event is not physical smoothness or qualified width |
| Short support | E021 fixed4px median: typical paired sensitivity change0; individual stage amplitudes can be reduced | Do not substitute this support into E015 target/score |
| Stage differencing | E022 common offsets lower finite-grid RMS in35/36 original-H pairs | Common-offset assumption not achieved/verified physical correspondence;4pairs still flip |
| Independent human/physical reference | Owning records still human pending, physical false | Not created by AI agreement, independent code or arithmetic precision |

Sources: [E018 summary](S03-E018-D01/evidence/summary.json),
[E019](S03-E019-D01/evidence/summary.json), [E020](S03-E020-D01/evidence/summary.json),
[E021](S03-E021-D01/evidence/summary.json), [E022](S03-E022-D01/evidence/summary.json).
These are record checks, not reruns or fresh independent audits of archived data.

### B. Three different measurement definitions and reference roles

| Quantity | Unit/position/processing | Appropriate reference and allowed use |
|---|---|---|
| E015 half-depth image width, selected primary | Per-beam FIRST-frame native-coordinate pixels. Original fixed transect normal, normal offsets−60..60 at.25; gray values sampled at5 tangent lines−2..2 and median combined. Linear shoulder background, selected deficit peak within±15, interpolated half-depth crossings; width=right−left; original QC/censor rules unchanged | Same-definition future image operator value is the target for forecasting THIS observable. E018 independent recomputation qualifies software reproduction, not physical accuracy. Existing14stages×12=168 values available in records |
| Central-row visible dark-edge width, auxiliary/unselected target | Canonical crop pixel centresx0..120, central rowy24; human/AI visually chooses apparent left/right edges and ambiguity ranges; width=right−left. Display enlargement does not add spatial resolution; no five-line median or half-depth threshold | Independent human repeats/adjudication can qualify repeatability of THIS visual definition. E017 AI labels only auxiliary ambiguity evidence; disagreement with half-depth is not automatically algorithm error |
| Physical crack aperture, not established | Physical unit such asmm at a declared material location/load/acquisition condition | Requires suitable independent physical/calibrated measurement, visibility/geometry and repeatability evidence. A pixel scale alone does not turn the two optical definitions into physical aperture. No such qualified reference currently established |

Definition sources: [profile sampler/measure](../../../scripts/d01_crack_profile_diagnostic.py)
functions `sample_profile` L50–64 and `measure` L67–95;
[E017 definition](S03-E017-D01/experiment.md), [annotation interface](../../../scripts/d01_blind_edge_packet.html)
central row/display; [E018 boundary](S03-E018-D01/experiment.md), Outcome.

**Recommended first evaluation:** retain the unchanged half-depth image
observable and originalH as primary, not visible-edge width, segment median or
stage-difference target. Define the claim as prediction of a specified optical
measurement at a later declared observation/condition. For this bounded claim,
the same-definition target operator values plus independent computation checks
are relevant scoring evidence; it is unnecessary and incorrect to demand that
central-row human clicks become the truth for a different operator first.
Human/physical references remain necessary for their own accuracy claims.

This distinction removes a false prerequisite, not the actual limitations:
the eight existing outcomes are viewed DEVELOPMENT cases, not independent
future validation; material correspondence and origin-time load knowledge
remain unresolved. No new computation or rescoring of those eight is justified
merely because their unchanged operator was reproduced. A new visible-width
target would need a separate protocol and same-definition historical inputs,
origins and targets, not relabelling E015 predictions.

### C. Exact eight-pair reference inventory (metadata, not new scoring)

H=the two historical observations actually used by secant; O=current origin.
Every row evaluates T1…T12, not only the four visually checked transects.
“Operator available/reproduced” means E015+E018 software evidence, NOT
independent human/physical truth. AI coverage is crop inclusion, not a claim
that all included tasks are visible or qualified.

| Beam/pair | H (kN) | O→target (kN) | Transects | Same-definition target evidence | Existing AI visual coverage at H/O/target | Still missing for stronger claims |
|---|---|---|---|---|---|---|
| B4-1 | 10,30 | 30→40 | 1…12 | Operator available/reproduced,12target profiles | H10:T3/6/9/12;O30:none;target40:none | Independent coordinate/physical reference; human visual coverage if that definition is evaluated |
| B4-2 | 30,40 | 40→50 | 1…12 | Same,12 | H30/O40:none;target50:T3/6/9/12 only | Same; endpoint inclusion is not12-transect truth |
| B5-1 | 10,20 | 20→30 | 1…12 | Same,12 | H10:T3/6/9/12;O20/target30:none | Same |
| B5-2 | 20,30 | 30→40 | 1…12 | Same,12 | H20/O30/target40:none | Same |
| B5-3 | 30,40 | 40→50 | 1…12 | Same,12 | H30/O40/target50:none | Same |
| B5-4 | 40,50 | 50→60 | 1…12 | Same,12 | H40/O50:none;target60:T3/6/9/12 only | Same |
| B6-1 | 10,20 | 20→30 | 1…12 | Same,12 | H10:T3/6/9/12;O20/target30:none | Same |
| B6-2 | 20,30 | 30→40 | 1…12 | Same,12 | H20/O30:none;target40:T3/6/9/12 only | Same |

Pair/source evidence: [E015 aggregate prediction metadata](S03-E015-D01/evidence/forecast_metrics.csv),
[included stage list](S03-E012-D01/experiment.md) L14–25,
[prediction loop](../../../scripts/d01_crack_profile_diagnostic.py) L225–240;
[E018168-profile check](S03-E018-D01/evidence/summary.json).
Historical rows follow the two-observation slices in the code, not newly fitted
histories. Unique target stages8×12=96 software-reference measurements are
represented within the already reproduced168; no new values read/generated.

Endpoint package:24unique crops+6repeat views, six first/last beam-stage groups,
onlyT3/6/9/12. E01716/24unique representatives visually usable,8uncertain;
all six repeat pairs match quality and four visible pairs have identical
coordinates. These same-context/coarse-coordinate repeats do not establish
independent repeatability, zero noise, all-stage coverage or a half-depth truth.
Five intermediate targets have no AI crop labels; three final targets have
only partial, different-definition AI coverage. Neither fact erases available
same-definition operator values.
Sources: [E016 packet scope](S03-E016-D01/experiment.md),
[E017 protocol](S03-E017-D01/experiment.md), [summary](S03-E017-D01/evidence/summary.json).
No annotation answer table, duplicate key or sealed source was opened here.

### D. Human repeatability/adjudication plan — design only

1. Keep the existing24+6 endpoint packet and answers untouched. It can pilot
   visible-boundary ambiguity/repeatability; it is not the scoring set for all
   eight forecasts. Do not select clearer duplicates to replace uncertainties.
2. If human visible-edge evaluation is pursued, plan two independent readers
   with exposure recorded, identical definition/display and no algorithm or
   prediction overlay. Each first pass is frozen before comparison; no score
   feedback. Confirm actual availability, workload and identity before dispatch.
3. Use hidden repeats and a separated/re-randomised second reading to measure
   within-reader coordinate/quality differences; independent readers measure
   between-reader disagreement. Same-image rereads are not acquisition noise
   or material correspondence. Repeat count/spacing must be fixed before use;
   existing six pairs are only a small pilot, not a tolerance estimate.
4. Branch/spall/occlusion/indeterminate cases receive explicit reason and
   subjective endpoint ranges, not forced precise endpoints. A third expert
   adjudicates after initial annotations are frozen, blind to forecast scores;
   save original readings and adjudication separately. Unresolved stays missing.
5. Future same-definition human target coverage must match the declared
   T1…T12/needed-stage set; if visible width becomes the target, include all
   required histories/origins too. E018 independently verified half-depth
   values do not fill missing human visible-width observations, or vice versa.
6. Report denominator, quality agreement, paired repeat differences, drift
   and unresolved fraction before deriving any physically/decision-relevant
   tolerance. Do not infer tolerance0 from E017 identical answers. No numerical
   acceptance margin is prescribed without adequate reference evidence.

### E. Next-load availability: what is and is not established

| Evidence type | What inspected records support | What they do not establish |
|---|---|---|
| Released stop labels/workbook-derived mapping | Ordered included nominal stages and retrospectively matched image identities | A dated loading/photography plan available at each prediction origin |
| E012/E015 protocol calling next_load “scheduled” | An analyst-declared conditional problem | Proof that the researcher/operator actually knew that next included load/image stop beforehand |
| E015 forecast call | `loads[current+1]` comes from the complete selected-stage vector | Origin-time availability; absence of future image inputs alone does not prove this metadata was known |
| Filtered measured force/time tables, as reported by E004 | Recorded measurements,25Hz; nominal joins for nonfinal stops | Future actual force as an allowed input; exact synchronization or matching-error bounds |

Code provenance: [stage selection](../../../scripts/d01_stage_forecast_diagnostic.py)
L105–127 reads `load_stop_mapping.csv`, filters numeric/available labels and
sorts filename times; [forecast](../../../scripts/d01_crack_profile_diagnostic.py)
L98–104 and L225–236 passes the NEXT retrospective nominal label.
[E004](S03-E004/experiment.md) Evidence result records unsynchronised acquisition,
manual alignment and unavailable quantitative matching bounds; its old verdict
is unchanged. [E012](S03-E012-D01/experiment.md) narrows the question to nominal
stages, not exact force/seconds.

**Conclusion within this read-only scope:** no original, origin-available
load/photography schedule was located in the inspected local records/code.
This is not a claim that no such document exists anywhere in the full release;
original archived PDFs/tables were not reopened and nothing new was downloaded.
Need a source/page/field explicitly documenting intended load AND observation
stops, applicability per beam and availability before each origin. The next
included image stage after filtering is not automatically the next planned stop.

Until that provenance exists, separate two candidate questions:

- **Retrospective condition-query diagnostic:** estimate optical width at an
  explicitly supplied nominal loadL*. It is valid to state the condition is
  supplied retrospectively/hypothetically; do not call that verified deployable
  next-load knowledge. Preserve old eight-pair interpretation in this category.
- **No-known-next-load continuation:** target the next declared observation
  event without a next-load input; retain persistence. A stage-index increment
  rule may be a separately designed comparator, not the load-normalised E015
  secant. Unequal Beam4 gaps preclude silently assuming equal kN increments.
  No seconds/cycles/actual-future-force horizon is invented.

Seeking author/source clarification would be a separate proposed action; this
review sends no message, form or file externally.

### F. Minimal evaluation contract to freeze later

| Item | Proposed definition (unfrozen) |
|---|---|
| Claim | Single-step, observation-updated prediction of the declared half-depth optical width, not physical aperture/road transfer/autonomous rollout |
| Origin and horizon | Per eight-pair ledger, only past/current observations available; known-plan next nominal stage only with source proof, otherwise explicit retrospective condition-query or separate next-observation question |
| Information | Original first-image geometry and admitted past/current transforms/widths; no target pixels/transforms/visibility, future measured force or reference labels in predictor/eligibility |
| Target/reference | Frozen original operator and evaluation-only target transform; software-reproduced target values. Human visible width is auxiliary unless a new target is explicitly chosen; physical truth is a separate claim |
| Baselines | Persistence and unchanged load-secant only for an admissible specified-load condition; half-secant stays secondary diagnostic, not selected post hoc. For unknown next load, do not reuse load-normalised secant under a renamed interface |
| Evaluation unit | Per-transect errors averaged per forecast pair, within beam, then beams equally; disclose all denominators/three beam results. Existing beams/outcomes remain development; new same-beam states test continuation, new specimens assess transfer |
| Primary | Paired loss difference versus persistence on predeclared common scoring support; no acceptance threshold until a meaningful comparator/uncertainty/decision margin exists. Without one, descriptive result only |
| Origin eligibility | Derive before target access: fixed origin-selected transect, both historical widths finite/QC-admissible, allowed coordinate/information support. Generate/store every eligible prediction BEFORE testing future reference availability |
| Future scoring support | Independently flag target identity/operator validity/reference availability after prediction freeze. Score all arms on the same support; missing not zero, no best-variant or clear-case replacement. Report eligible, predicted, reference-available and scored counts/reasons separately |
| Prediction missing | Retain failure/abstention counts, not only conditional loss. Predeclare any selective/deployment penalty policy if needed; do not invent a target value or risk score for unobservable targets |
| Validation role | Existing8cases may audit a new bounded development repair, not become fresh holdout. Prospective frozen predictions/new unseen evaluation data needed for independent validation; no reusing inspected outcomes as confirmation |

One code-level issue for a FUTURE implementation: current E015 L226 computes
support over `widths[current-1:current+2]`, including target measurability,
before calling the prefix-only predictor. Existing168/168valid and96/96scored
records mean no observed support loss in that run, but this structure must not
be described as origin-only deployment eligibility. Split origin eligibility
from scoring support in a new reviewed implementation; this review changes no
code or old result.

### G. Dependency-ordered next work

1. Approve the narrowly bounded image-observable claim and reference roles;
   do not reopen the selected target solely because auxiliary visual labels differ.
2. Resolve whether load/observation plan is provably known at origin. If not,
   explicitly choose retrospective condition-query or a new no-known-load
   formulation before defining the final predictor interface.
3. Freeze/qualify relative-position correspondence support or its uncertainty;
   E022 gives a controllable lever, not proof it is already achieved. Keep
   cases sensitive even under common offsets in the evaluation population.
4. In parallel, prepare human visible-edge repeatability/adjudication only
   for its declared ambiguity/physical-measurement questions. It is not a
   substitute half-depth truth and not a mandatory relabelling of all images
   for a purely operator-defined forecast.
5. Specify new evaluation identity/exposure, origin mask, post-prediction
   reference mask, same-support baselines and primary comparison. Independent
   validation requires genuinely uninspected/prospective targets; all eight
   existing cases are development. Freeze any meaningful acceptance margin
   only once justified; otherwise retain a descriptive diagnostic.
6. Obtain reviewed final protocol/code and exact single-run approval before
   any new implementation execution. This document dispatches no annotator,
   creates no packet, accesses no sealed data and launches no calculation.
