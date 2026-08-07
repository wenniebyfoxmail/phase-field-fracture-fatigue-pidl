# LTPP-GeoForecast annotation and forecast protocol

Status: both blind roles frozen at 37/37. Pairing completed only after the
sealed-map gate opened, but requires adjudication: geometry F1 `0.6921`, line
metrics pass, area metrics fail, 121 geometries are unmatched, and one matched
pair has a family disagreement. See
`ltpp_geoforecast_blind_packet_handoff_20260805.md`. No adjudicated ground truth
or model result is claimed.

## Scientific question

Using only observations available at survey time `t`, can a model predict the
registered crack geometry at the next survey on an unseen physical LTPP
section, with calibrated uncertainty, better than persistence and simple
growth baselines?

## Bounded annotation gate

Use the six sections qualified in
`ltpp_geoforecast_multisection_gate_20260805.md`. The initial protocol proposed
fixed `0-50 ft` and `250-300 ft` panels. The frozen second-panel gate subsequently
failed because five maps lack a qualified automatic transform; see
`ltpp_geoforecast_second_panel_gate_20260805.md`. The first annotation batch is
therefore the qualified `0-50 ft` panel only, giving 37 maps per annotator.

The packet custodian retains source hashes and section/date/panel identifiers
in the sealed asset mapping. Each annotator receives randomized blind IDs,
white-composited rectified maps, and the LTPP distress legend. They do not
receive the other annotator's output, the sealed mapping, automatic crack
candidates, chronological/future maps, or model predictions.

Each geometry must be labelled as one of:

- crack centreline with LTPP type/severity when legible;
- mapped distressed polygon when the source is explicitly areal;
- lane/shoulder/reference boundary;
- handwritten code or calculation;
- uncertain/unresolved.

The reviewed package passes only if every candidate geometry has a disposition,
all unmatched lines are adjudicated, matched mean centreline distance is at
most `0.10 m`, and matched continuation-tip distance is at most `0.20 m`.
Uncertain strokes remain masked rather than forced into crack or non-crack.

Failure stops expansion and returns to source semantics. Passing authorizes a
separate acquisition decision for additional fixed panels. The `250-300 ft`
panel remains excluded until its five failed transforms receive a frozen
printed-border-only manual-corner review; no crack content or future map may
influence that transform.

Current application of this gate: matched line placement passes, with mean
centreline distance `0.0422 m` and mean continuation-tip distance `0.0946 m`.
The complete package does not pass because area metrics fail and 121 crack
geometries remain unmatched. All 121 unmatched geometries and the one family
disagreement must receive a human adjudication disposition before transitions
or training labels are exported.

## Leakage-safe transition table

The primary key is:

`STATE_CODE + SHRP_ID + CONSTRUCTION_NO + panel_start_ft + survey_date`

For every `t -> t+1` transition, freeze:

- registered start and target GeoJSON hashes;
- valid-observation and uncertainty masks;
- elapsed days;
- source-exclusive, target-inclusive monthly temperature and precipitation;
- coverage fractions and raw forcing hashes;
- structure/construction identity;
- maintenance/reset and out-of-study flags;
- explicit missingness for traffic, FWD, humidity, and moisture.

No future map may be used for registration, source-field fitting, candidate
selection, threshold setting, or forcing imputation.

The six-section forcing extraction now passes this contract for all 31
transitions. Monthly temperature and precipitation are read from frozen
official responses, aggregated source-exclusive and target-inclusive with
boundary-month day proration, and have coverage fraction `1.0`. This forcing
pass does not bypass the incomplete annotation-adjudication gate.

## Locked evaluation axes

1. **Unseen-section generalization:** six leave-one-section-out folds. All
   panels from the held-out section remain test-only.
2. **Future-time forecasting:** the final climate-complete transition of each
   section is test-only; earlier transitions form the development set.
3. **Long-horizon stress:** report errors against elapsed interval length; do
   not resample irregular survey gaps into invented annual labels.

The ten panels of one section share section-level forcing and are not ten
independent climate trajectories. Confidence intervals must cluster by
physical section.

## Required baselines before PIDL

- persistence of the last registered geometry;
- scalar linear growth with no spatial invention;
- local centreline/tip extrapolation;
- probabilistic state-space growth model with explicit interval duration.

Only after these are frozen may an observation-conditioned spatial model be
evaluated. PIDL/FEM may later enter as a separately labelled transition prior,
never as observed LTPP truth.

## Primary outputs and metrics

- future crack-centreline buffered IoU and boundary F1;
- new-crack length MAE and total-length MAE;
- continuation-tip error only for adjudicated matched continuations;
- initiation/branch event precision, recall, and timing error;
- CRPS for scalar growth quantities;
- 90% interval coverage and interval width;
- per-section and worst-section results, not only pooled averages.

## Locked success rule

The first benchmark is reliability-positive only if one non-PIDL challenger:

1. improves over persistence by at least 10% on both new-crack geometry error
   and crack-growth quantity error in unseen-section evaluation;
2. improves in at least four of the six held-out sections;
3. achieves empirical 90% interval coverage between 85% and 95%; and
4. does not obtain the gain by excluding severe, uncertain, or long-interval
   targets after the split is frozen.

Otherwise report a negative benchmark result and identify which observation
channel is missing. Do not respond by architecture or threshold sweeping.
