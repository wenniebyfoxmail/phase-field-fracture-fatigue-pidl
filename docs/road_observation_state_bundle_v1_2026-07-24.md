# Road Observation-State Bundle v1

## Purpose

`road_observation_state_bundle_v1` is the frozen Agent1 handoff consumed by the Agent2 trigger/time formulation and the Agent3 temporal forecast input contract. It is an interface adapter, not an inverse model.

The final downstream locks are Agent2 commit `19ca9c73a36a4fb80119a49c9234d6ee11501052` and Agent3 commit `e55070e4b29a1da39262e0138e2c4efc7240c195`. Consumed files are additionally pinned by SHA-256; commit identity never replaces content verification.

The final rebuild changed the bundle/history hashes because the downstream source hashes and packet semantics are embedded in provenance. The legacy c87 state payload remains locked at `276bca62f3955c0948bd23891aa10dcca209f3e562605303b61b263d53759ffe`; no field training or numerical state change occurred.

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
- Agent2 receives `agent2_observation_innovation_packet.json` using `observation_innovation_packet_v1`. Its three frozen channels are `registered_crack_geometry_image`, `fwd_deflection_basin`, and `strain_localization`; unavailable entries use `null + mask=false` and the oracle packet remains `decision_eligible=false`.

Both consumers must verify the source bundle SHA-256 and must use the same bundle and prior for every compared model.

The Agent3 adapter reads node/global observation arrays directly. It is forbidden to map `observed_channel_mask` into `node_observation_mask`, because the former records latent assimilation attribution rather than measurement availability.

The builder prefers final contract files present in its own checkout, so it works after the Agent1/2/3 branches are merged. Optional `--agent2-root` and `--agent3-root` arguments support isolated-worktree development. A clean integration checkout reproduction produced byte-identical bundle and history payloads.

## Evidence boundary

Passing this interface gate does not establish real-road state inversion, uncertainty calibration, material identification, FEM-cycle-to-road-time mapping, or road-section generalization. Those remain blocked on registered physical observations and independent asset/trajectory holdouts.
