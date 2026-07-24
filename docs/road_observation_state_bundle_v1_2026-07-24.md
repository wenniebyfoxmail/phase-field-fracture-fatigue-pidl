# Road Observation-State Bundle v1

## Purpose

`road_observation_state_bundle_v1` is the frozen Agent1 handoff consumed by the Agent2 trigger/time formulation and the Agent3 temporal forecast input contract. It is an interface adapter, not an inverse model.

The canonical schema is in `docs/templates/road_observation_state_bundle_v1.schema.json`. The deterministic offline builder is `SENS_tensile/build_road_observation_state_bundle_v1.py`.

## Canonical semantics

- `state_mean[T,N,C]` contains `damage`, `fatigue_history`, `fatigue_degradation`, and `log10_psi_raw`.
- Exactly one uncertainty representation is allowed: standard deviation, covariance, or ensemble.
- All-NaN standard deviation means explicitly uncalibrated uncertainty. Zero is not accepted as missing uncertainty.
- `observed_channel_mask[T,N,C]` records which latent channels were constrained during assimilation.
- `node_observation_mask` and `global_observation_mask` independently record measurement availability.
- Missing numeric observations, load history, environment, equivalent load, and delta-t use `NaN + mask=false`.
- Missing timestamps use an empty string plus `timestamp_mask=false`.
- Maintenance reset requires a declared event id and a new state segment.
- Oracle, synthetic, and real evidence remain distinct.

## Current c87 adapter

The current c87 package is still a FEM eta0 oracle upper bound. The legacy fields are renamed without changing values:

- `alpha_bar -> fatigue_history`
- `log10_psi_raw` remains canonical for Agent2 and the current Agent3 contract.

The 8,641 directly constrained raw-energy nodes are exposed only as `log10_psi_raw_oracle`. Agent2 receives their count for audit, not their values. Image, FWD, strain, WIM, temperature, moisture, road timestamp, equivalent load, and maintenance remain missing.

## Consumer outputs

- Agent3 receives `agent3_history_sequence_skeleton.npz`, preserving raw NaNs and all masks before model-specific normalization.
- Agent2 receives `agent2_observation_innovation_packet.json`, with unavailable road innovations represented by `null`, `available=false`, and `mask=false`.

Both consumers must verify the source bundle SHA-256 and must use the same bundle and prior for every compared model.

## Evidence boundary

Passing this interface gate does not establish real-road state inversion, uncertainty calibration, material identification, FEM-cycle-to-road-time mapping, or road-section generalization. Those remain blocked on registered physical observations and independent asset/trajectory holdouts.
