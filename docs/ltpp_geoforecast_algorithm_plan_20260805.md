# LTPP-GeoForecast algorithm decision after dual-blind pairing

Date: 2026-08-05; terminal evaluation 2026-08-06  
Status: `RELIABILITY_NEGATIVE__PERSISTENCE_REMAINS_CONTROL`

## Outcome-led decision

The first non-trivial forecasting algorithm will be a **hierarchical
probabilistic state-space crack-growth model**, not a neural network and not a
PIDL/FEM surrogate. It will model elapsed-time-conditioned crack continuation,
new-crack length, initiation, and branching with section-level partial pooling
and calibrated predictive intervals.

This decision is conditional on completing the bounded adjudication gate. The
current dual-blind pairing has good matched-line placement but insufficient
label agreement for training: geometry F1 `0.6921`, 121 unmatched geometries,
one family disagreement, and failed area metrics.

## Terminal real-data result

The human queue reached `139/139` and the real (not smoke-test) pipeline froze
37 adjudicated states with 249 geometries, including 232 crack geometries. All
37 per-state hashes passed. The leakage-safe join then passed with 31
transitions: 25 development transitions and six frozen final-time tests.

The three frozen controls showed that growth extrapolation was not a credible
replacement for persistence. On the six future-time tests, persistence had
length MAE `7.0543 m`, mean buffered F1 `0.4333`, and new-geometry error
`1.6018 m2`. Local-tip extrapolation changed F1 only to `0.4368` while worsening
length MAE to `7.8401 m` and new-geometry error to `1.6847 m2`.

The predeclared hierarchical probabilistic state-space challenger was therefore
run once without architecture or threshold sweeping. On leave-one-section-out
evaluation it worsened crack-length error by `15.63%` and new-geometry error by
`6.31%` relative to persistence, improved both metrics in `0/6` sections, and
achieved nominal-90% interval coverage `0.9355`. Only the coverage gate passed;
the growth, geometry, and section-win gates failed. Decision SHA-256:
`a71e2c87068fc400e12b6e200a6d34c4719545b71819f6f52cdf82650353ecce`.

**Algorithm decision:** persistence remains the honest point-forecast control.
The state-space model may be retained only as an uncertainty diagnostic; it is
not a reliable spatial crack-growth predictor. No graph neural network, PIDL,
or hyperparameter sweep is authorized as a rescue on these six sections.

## Five-question experiment gate

1. **Mechanism question:** after conditioning on the observed crack graph,
   elapsed survey interval, climate forcing, and declared missingness, is crack
   growth more predictable than persistence without inventing unsupported
   spatial detail?
2. **Claim changed by success/failure:** success supports a small-data,
   observation-conditioned real-road forecast benchmark; failure says the
   present geometry-plus-climate channels are insufficient and does not justify
   a larger architecture.
3. **Cheaper diagnostic first:** adjudicate all annotation disagreements, then
   run persistence, scalar linear growth, and deterministic local-tip
   extrapolation. No training begins before these assets and splits are frozen.
4. **Minimal output asset:** one per-transition prediction table plus a decision
   note containing leave-one-section-out and future-time metrics, interval
   calibration, and worst-section results.
5. **Registry handoff:** the terminal decision updates
   `docs/research_frontier.md` and one bounded experiment record; no orphan run
   or architecture sweep is permitted.

## Representation and model

- Convert each adjudicated map to a crack graph: polylines, endpoints, length,
  orientation, family/severity, and explicitly masked uncertain regions.
- Match only adjudicated continuations across `t -> t+1`; initiation and branch
  events remain separate marked events rather than forced line matches.
- Use interval duration directly. Do not interpolate irregular survey gaps into
  annual pseudo-labels.
- Use a hierarchical Bayesian/state-space transition with section random
  effects (partial pooling), climate summaries, structure identity, and explicit
  missingness indicators. Begin with regularized linear/logistic transition
  components; add nonlinear terms only if a frozen residual diagnostic demands
  them.
- Produce predictive distributions for new length and continuation-tip advance,
  plus probabilities for initiation/branch events. Geometry is reconstructed by
  local tip extension and sampled event placement, never by free-form image
  generation.

## Frozen comparison order

1. persistence;
2. scalar linear growth;
3. deterministic local centreline/tip extrapolation;
4. hierarchical probabilistic state-space growth model.

Only if item 4 passes the locked reliability rule may a graph neural transition
model be proposed. PIDL/FEM may enter later only as a separately labelled prior,
not as LTPP truth.

## Data and evaluation gates

- Input is limited to the six qualified sections, 37 states, and 31 transitions
  from the `0-50 ft` panel.
- Leave-one-section-out is the primary generalization test; final
  climate-complete transitions are frozen future-time tests.
- Confidence intervals cluster by physical section. Panels or dates from a held
  out section never enter fitting or threshold selection.
- The benchmark is reliability-positive only under the four locked rules in
  `ltpp_geoforecast_annotation_forecast_protocol_20260805.md`, including at
  least 10% improvement over persistence on both geometry and growth quantity,
  improvement in at least four of six sections, and 85-95% empirical coverage
  for nominal 90% intervals.

## Immediate no-training plan

1. Build a bounded adjudication queue from the 121 unmatched geometries, one
   family disagreement, and 17 WIM/pumping semantic candidates.
2. Have the human reviewer assign exactly one disposition per item:
   `accept_primary`, `accept_secondary`, `merge`, `reject`, or `uncertain`.
3. Freeze adjudicated GeoJSON and hashes; rerun pairing/quality checks.
4. Export 31 leakage-safe transition rows and freeze the three cheap baselines.
5. Only then implement the state-space challenger on a producer or lightweight
   statistical runtime appropriate to the final implementation; no Mac PIDL
   training is authorized by this plan.

Step 1 is complete: immutable `adjudication_queue_initial.json` contains 139
unique pending items with no prefilled disposition (SHA-256
`bb47898b6e85d128b45a2a91a45a974cd059f5e7ed33d6cf4e2a35c885ce3eeb`).
The reviewed working copy is `adjudication_queue.json`; it is served locally by
`scripts/ltpp_adjudication_server.py` with three aligned full-map panels (clean
source, complete locked AI annotation, and complete locked human annotation),
a gold outline for the current candidate, single-item decisions, and reversible
map-level bulk decisions. Bulk review
reduces the usual interaction count from 139 feature clicks to the 21
asset-dates that contain pairing differences without weakening the per-item
disposition record.

The forcing and downstream execution path are also prepared without crossing
the adjudication gate:

- 178 official monthly temperature/precipitation responses are frozen for the
  six sections;
- all 31 source-exclusive, target-inclusive climate intervals pass coverage;
- adjudicated-label freezing, transition joining, three baselines, and the
  hierarchical state-space challenger each have an explicit exit-42 missing-
  prerequisite guard;
- an ephemeral automatic-disposition fixture passed the software path only and
  was deleted. Its metrics are do-not-cite and do not pre-judge the human queue.
