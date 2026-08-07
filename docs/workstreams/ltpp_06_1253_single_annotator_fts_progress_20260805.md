# LTPP 06-1253 Single-Annotator Freeze-Then-Select Pilot

**Status:** negative diagnostic workstream; no reliability-positive model selected  
**Scope:** LTPP section 06-1253, 0-50 ft, single primary annotator  
**Date frozen:** 2026-08-05  
**Role:** preserve evidence and next decisions without occupying the shared research frontier

## Current decision

The pilot does not yet support a claim that Freeze-Then-Select improves reliable road-crack forecasting. The main limitation is now the observation-state representation, not a missing sparse-regression term: hand-drawn distress-map geometry is nonmonotone across surveys, the candidate libraries are non-identifiable, trajectory holdout does not beat the null decisively, and a hard-monotone structured adapter fails its predeclared projection gate.

The line channel is the more credible exploratory signal. The polygon/area channel is excluded from the next discriminator because its agreement with official section-level trends is weak and its meaning is less stable.

## Frozen scope and provenance

| Item | Frozen state |
|---|---|
| Official source images | 90 PNG records across 9 survey dates; all downloads returned HTTP 200 and were hashed |
| Annotation | P01-P09 primary pages locked; 88 geometries: 72 LineStrings and 16 Polygons |
| Annotation regime | Single annotator only; secondary annotation explicitly deferred |
| Spatial scope | First 0-50 ft of the mapped section |
| Main dates | Seven primary dates from 1991-2007 |
| Auxiliary dates | 2012 and 2015 retained only as post-Out-of-Study context |
| Label meaning | Human vectorization of visible distress-map marks, not natural-crack ground truth and not a phase-field state label |

Primary manifest: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_blind_vectorization_v1_20260805/primary_locked_v2_manifest_20260805.json`

Source manifest: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_maps_20260805/map_manifest.csv`

Scope decision: `docs/ltpp_06_1253_pilot_scope_decision_20260805.md`

## Checkpoint ledger

| Checkpoint | Result | Decision |
|---|---|---|
| Frozen proxy fields | 9 x 126 x 382 line, area, and combined fields | Qualified only as exploratory observation proxies |
| Freeze-Then-Select v1 | 48 systems; mean support Jaccard 0.5065 versus 0.7528 for single-shot; mean RMSE 0.06570 versus 0.06648 | `NOT_RELIABILITY_POSITIVE` |
| Full candidate library | Severe collinearity and unstable support | Not identifiable |
| Reduced climate families | Maximum median VIF: low temperature 273.8, temperature change 592.2, precipitation 175.9 | None identifiable |
| Climate-free `d + d^2` | Maximum median VIF 141.8 | Not identifiable |
| Climate-free A/B | Strong spatial interpolation gains, but trajectory gains remain small and inconsistent | `NO_DAMAGE_MODEL_CLEARS_NULL` |
| Structured field adapter | Bounds and irreversibility passed; 3/5 leave-one-date-out wins; median improvement 13.9%; projection RMSE 0.221 and max error 0.334 exceed 0.15/0.25 gates | Not qualified |
| Official MON_DIS trend diagnostic | Official full-section crack metrics are also nonmonotone | Hard monotonicity is not justified for the raw observation process |

## Key A/B evidence

Spatial holdout:

- A versus null: 98.75% wins; median improvement 35.66%.
- B versus null: 98.33% wins; median improvement 36.90%.
- B versus A: 71.67% wins; median improvement 1.44%, below the gate.

Trajectory holdout:

- A versus null: 52.27% wins; median improvement 1.78%.
- B versus null: 53.03% wins; median improvement 2.89%.
- B versus A: 65.53% wins; median improvement 0.89%.

If a debugging baseline is required, use A for parsimony. This is not a research winner.

## Official-data external QC

The frozen SDR39 acquisition contains 13 MON_DIS tables, of which three contain 20 relevant rows in total: `MON_DIS_AC_CRACK_INDEX`, `MON_DIS_AC_REV`, and `MON_DIS_PADIAS42_AC`. The section timeline contains 107 events; all nine map dates were located, no explicit reset candidate was found, and the section entered Out-of-Study on 2011-06-01.

The latest trend diagnostic returned `OFFICIAL_SECTION_TRENDS_ALSO_NONMONOTONE`. Negative adjacent transitions occurred in both pilot and official channels. Pilot line mean versus official total line length has Spearman rho 0.892857 and direction agreement 6/6, but this is descriptive only: the pilot covers 50 ft, official metrics cover 500 ft, and only seven paired dates are available. The area channel is materially weaker.

MON_DIS acquisition contract: `docs/ltpp_06_1253_mon_dis_acquisition_contract_20260805.md`

Trend diagnostic contract: `docs/ltpp_06_1253_mon_dis_trend_diagnostic_contract_20260805.md`

Trend diagnostic result: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_mon_dis_trend_diagnostic_v1_20260805/trend_diagnostic_result.json`

## Evidence boundaries

- This is a single-section, single-annotator exploratory pilot.
- The 0-50 ft annotation cannot quantitatively validate 500-ft official metrics.
- No true joint-training checkpoint or provenance-matched joint baseline exists.
- Official nonmonotonicity does not prove physical crack healing; it shows that survey observations cannot be equated directly with an irreversible latent damage field.
- Missing maintenance events in the viewer do not prove that no unrecorded intervention occurred.
- VIF runtime warnings mean individual extreme VIF values should not be overinterpreted; the qualitative non-identifiability conclusion is the usable result.
- No downstream forecasting or mechanism claim should be made from this branch yet.

## Main artifacts

- Frozen fields: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_single_annotator_fields_v1_20260805/frozen_observation_fields.npz`
- FTS script: `SENS_tensile/run_ltpp_06_1253_single_annotator_freeze_select.py`
- FTS result: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_single_annotator_fts_v1_20260805/result.json`
- Identifiability gate: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_identifiability_gate_v4_scipy_pinvh_20260805`
- Reduced-library result: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_post_v1_reduced_library_identifiability_v1_20260805/reduced_library_identifiability_result.json`
- Climate-free gate: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_climate_free_baseline_gate_v1_20260805/climate_free_baseline_gate_result.json`
- Climate-free A/B contract: `docs/ltpp_06_1253_climate_free_ab_contract_20260805.md`
- Climate-free A/B result: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_climate_free_ab_v1_20260805/climate_free_ab_result.json`
- Structured-adapter contract: `docs/ltpp_06_1253_structured_field_adapter_v1_contract_20260805.md`
- Structured-adapter result: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_structured_field_adapter_v1_20260805/qualification_result.json`
- Section event ledger: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_section_event_ledger_v1_20260805/event_ledger.csv`

## Next discriminator for this workstream

Before any new training or equation-term tuning, compare three explicit observation-state models on the line channel under leave-one-date-out evaluation:

1. Persistence or last-observation baseline.
2. Smooth nonmonotone state-space model.
3. Latent irreversible state plus an explicit noisy survey-observation model.

Predeclare the scoring and rejection gates before running. Continue only if the latent-state model improves temporal holdout materially without requiring the observed geometry itself to be monotone. Keep the area channel out of this gate.

## Coordination with parallel work

The multisection LTPP benchmark and dual-blind annotation route is a separate active workstream and owns the shared frontier's next-discriminator slot. This `06-1253` branch remains a frozen negative diagnostic and method-design sandbox. Secondary annotation can be added later, but it is not a blocker for documenting or closing the present single-annotator result.

## Observation-State Gate v1 result

The predeclared rolling-origin gate was executed on the first seven `line_damage` surveys and returned `FAIL_L_NOT_QUALIFIED`.

- L median balanced-MAE improvement versus persistence: 7.57%, below the frozen 10% gate.
- L median balanced-MAE improvement versus smooth nonmonotone trend: 11.80%.
- L won 3/4 folds versus persistence and 4/4 versus the smooth model.
- L median balanced-CRPS improvement: 8.21% versus persistence and 13.86% versus smooth.
- Cluster-bootstrap 90% lower bounds for CRPS improvement were positive: 4.22% versus persistence and 7.87% versus smooth.
- Soft Dice, finite metrics, informative-fold count, interval width, nondegeneracy, and worst-fold regression gates passed.
- The coverage gate failed because F4 achieved 68.90% coverage, below the frozen 70% lower bound.
- Inner selection chose latent drift factor 0.0 in all four folds. The useful component was therefore persistence of a denoised irreversible latent history, not learned forward crack growth.

This is a near-negative diagnostic, not a promotion. It shows that explicit observation semantics are useful, but the present latent model does not clear the qualification bar and provides no evidence for a predictive crack-growth mechanism.

Contract: `docs/ltpp_06_1253_observation_state_gate_v1_contract_20260805.md`

Decision: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_observation_state_gate_v1_20260805/decision.md`

Full result: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_observation_state_gate_v1_20260805/result.json`

### Decision after v1

Do not relax the v1 thresholds and do not promote L as the next field adapter. Do not tune another `06-1253`-only model. The next evidence-bearing action belongs to the independent multisection route: test whether the denoised latent-history advantage reproduces across sections under the already separated annotation protocol. Until that cross-section evidence exists, the total Freeze-Then-Select goal remains blocked at observation-state qualification.
