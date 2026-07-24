# Decision: corrected Agent 3 closed-loop integration

## Supersession notice

Commit `f9b2557` **did not pass semantic review and is superseded**. Its adapter
incorrectly mapped Agent1 `observed_channel_mask` into Agent3
`node_observation_mask`, which could represent latent assimilation attribution
as sensor availability. No scientific or operational claim may use that
adapter or its original smoke package.

## Corrected verdict

The corrected interface/legacy smoke passes against Agent1 commit `d8a7ff3`
and frozen `road_observation_state_bundle_v1`.

- Canonical bundle SHA: `b9bb52026737ed11a9463051f31e7c05057595ec0e015d8a6dec6127c2a4c86e`.
- Agent3 skeleton SHA: `e482c52ceff47038493c7563a99133f5e6c4017009d482aea8707a1c58d83e74`.
- Agent2 innovation packet: `decision_eligible=false`.
- No training was launched.

This remains tooling-only. The bundle is an FEM-oracle upper bound,
`real_road_compatible=false`, with unavailable uncertainty and no calibrated
road time/load mapping.

## Corrected semantic boundary

1. `state_mean[T,N,C]` supplies the analysis-state origin only.
2. `observed_channel_mask[T,N,C]` remains latent assimilation provenance and
   never enters a model observation tensor.
3. Node/global measurements come only from independent
   `*_observation_values` and `*_observation_mask` arrays.
4. Missing observations, timestamp, equivalent load, delta-t, traffic and
   environment remain NaN/empty plus `mask=false` until masked feature preparation.
5. Exactly one uncertainty representation is accepted: std, covariance, or
   ensemble. Derived uncertainty reaches a trigger only when calibrated and
   decision-eligible.
6. A maintenance reset requires a declaration, event id and new state segment.
7. An ineligible observation packet cannot request or stop operationally.
   Independent maintenance and inspection-overdue safety gates still stop.

## Corrected real-package smoke

Markov, TCN and diagonal SSM used one canonical state hash, independent
observation-mask hash and scenario hash.

- Legacy h1 raw transfer error: `0.0` for all three models.
- Independent node observations: 8,641 available oracle-audit values from the
  Agent1 observation arrays.
- Latent attribution values: 8,641, retained separately; verified leak count: 0.
- Global observations: all unavailable and remain NaN plus false masks.
- Uncertainty: unavailable and not trigger-eligible.
- Packet trigger status: `rejected_ineligible_operational_evidence`.
- Maintenance scenario: fields withheld and observation requested by the
  independent system safety gate.
- Hazard/RUL: `unavailable_untrained`.

The equal counts of independent oracle observations and latent attributions do
not establish identity: the audit verifies exact equality to the independent
Agent1 node arrays and contains a regression test preventing the latent mask
from creating measurements.

## What is and is not proven

Proven: schema/hash/graph compatibility, independent observation transport,
missingness preservation, eligibility rejection, maintenance segmentation,
legacy h1 equivalence and h1-h3/risk API boundaries.

Not proven: observation benefit, autonomous transition prediction, calibrated
uncertainty, operational warning thresholds, hazard/RUL, real-road inversion or
road-section generalisation.

## Producer decision

Do not launch training. The next producer gate still requires longitudinal
Agent1 bundles at matched observed origins, a frozen Agent2 road load/time
vectorizer, independent physical trajectories/road sections, and event/censor
diversity for risk heads.
