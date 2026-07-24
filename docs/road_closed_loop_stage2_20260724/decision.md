# Decision: Agent 3 closed-loop integration, stage 2

## Verdict

The **interface and legacy compatibility gate passes**. The frozen Agent1 c87
state, Agent2 v1 road contracts, and Agent3 forecaster now execute through one
closed-loop API with strict hashes, explicit masks, irregular time intervals,
trigger handoff, maintenance stop, and optional re-assimilation.

This is not a forecast-performance result. The current Agent1 package is a
single-trajectory FEM-oracle upper bound and explicitly says
`real_road_compatible=false`. Observation uncertainty is unavailable, the
direct h2-h3 road-aware heads are untrained, and hazard/RUL outputs are hidden.

## What is now proven

1. Agent1 `road_assimilated_state_v1` can be consumed without changing its
   source field names. `alpha_bar` is mapped explicitly to Agent3
   `fatigue_history`; graph mismatch is a hard error.
2. The same c87 package, observed mask and scenario hash reach Markov, TCN and
   diagonal SSM.
3. Zero-column legacy transfer preserves the first raw state update exactly:
   maximum absolute error `0.0` for all three seed-1 checkpoints.
4. Missing observations and all-NaN uncertainty stay missing. Nine Agent2
   model-internal trigger signals are unavailable rather than assigned zero.
5. Maintenance/innovation/OOD hard gates can stop field production and request
   a new observation; re-assimilation resets trigger state.
6. The public API cannot return a primary field forecast beyond h3 and cannot
   expose untrained hazard/RUL tensors.

## What is not proven

- No observation-aware model has been trained.
- h2-h3 field values from this smoke are not scientific predictions.
- There is no evidence of improved c87 transition prediction.
- No calibrated road load-block mapping, uncertainty, warning threshold,
  hazard, RUL, real-road transfer, or leave-one-section-out generalisation exists.
- Repeated FEM windows remain one trajectory, not independent road samples.

## Producer decision

Do **not** launch the parameter-matched Markov/TCN/SSM producer run yet. The
code/interface gate is complete, but the minimal scientific asset is missing:
a longitudinal set of hash-locked Agent1 analysis/observation packages and a
frozen Agent2 traffic/environment load-block vectorizer. Hazard/RUL additionally
requires independent event and censor diversity.

When those inputs exist, the smallest justified run is three formal families,
seeds 1/2/3, identical observed origins/masks/scenarios, parameters matched
within 1%, and direct h1-h3 versus recursive h1 evaluation. Exact required
inputs and outputs are frozen in `producer_experiment_manifest.json`.

## Evidence locations

- API: `source/road_closed_loop_forecaster.py`
- Real-package audit: `SENS_tensile/audit_road_closed_loop_stage2.py`
- Contract matrix: `contract_compatibility_matrix.csv`
- Sequence: `end_to_end_sequence.md`
- Smoke metrics: `smoke/closed_loop_compatibility_smoke.csv`
- Smoke summary: `smoke/compatibility_smoke_summary.json`
- Producer gate: `producer_experiment_manifest.json`
