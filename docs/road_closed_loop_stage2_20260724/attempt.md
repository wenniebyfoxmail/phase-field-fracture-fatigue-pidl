# Attempt ledger

## Attempt 1: rejected

Commit `f9b2557` consumed legacy `road_assimilated_state_v1` and mapped
`observed_channel_mask` to `node_observation_mask`. Review correctly rejected
this: the former records latent assimilation attribution, not measurement
availability. The original adapter and smoke verdict are superseded.

## Attempt 2: corrected contract

Source: Agent1 commit `d8a7ff3`, canonical bundle
`b9bb52026737ed11a9463051f31e7c05057595ec0e015d8a6dec6127c2a4c86e`,
and Agent3 skeleton
`e482c52ceff47038493c7563a99133f5e6c4017009d482aea8707a1c58d83e74`.

Implemented:

- direct loading of `road_observation_state_bundle_v1` T,N,C arrays;
- canonical state registry with explicit legacy aliases;
- independent node/global observation values and masks;
- latent `observed_channel_mask` retained only for provenance;
- timestamp/equivalent-load/delta-t masks;
- traffic/environment channel registries and masks;
- maintenance declaration, event-id and state-segment validation;
- exclusive std/covariance/ensemble uncertainty handling;
- operational rejection of `decision_eligible=false` evidence;
- independent maintenance/overdue system safety gates;
- regression tests for every review finding.

## Corrected smoke

- Canonical and skeleton hashes verified.
- Agent3 skeleton state and independent observation arrays equal the canonical
  bundle, including NaNs and masks.
- Markov/TCN/diagonal SSM h1 legacy error: 0.0.
- Node observation count equals the independent Agent1 node mask: 8,641.
- No observation is created from latent attribution; leak count: 0.
- Global, traffic and environment missing values remain missing end-to-end.
- Oracle innovation packet is rejected as operational trigger evidence.
- Maintenance still invokes the separate system safety stop.
- No training launched; risk heads remain unavailable.

## Status

`pass_corrected_tooling_only`; the `f9b2557` semantic verdict is invalidated.
