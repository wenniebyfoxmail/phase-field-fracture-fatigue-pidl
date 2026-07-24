# Road Closed-Loop Integration Decision

## Verdict

**The three-agent closed-loop prototype passes the interface, provenance, and
control-flow gate. It does not pass the road-forecast performance or real-road
validation gate.**

The integrated system now executes the intended workflow:

```text
independent observation arrays and masks
  -> hash-locked latent analysis state
  -> direct h1-h3 forecast
  -> model/innovation/OOD trigger
  -> continue, request, or stop
  -> optional re-assimilation
  -> trained risk output or explicit unavailable status
```

## What is proven

- Agent 1's final bundle rebuilds with SHA-256
  `e94027542484431d3a53222d930c81e9ed6c655b86a822ced1452fa8c4c0f253`.
- Markov, TCN, and diagonal SSM receive identical analysis, observation-mask,
  and scenario hashes.
- Their zero-column legacy h1 raw transfer error is exactly `0.0`.
- Latent assimilation attribution creates zero sensor observations.
- Missing node/global observations remain missing end to end.
- A decision-ineligible FEM-oracle packet cannot request or stop an operational
  forecast.
- Maintenance stops field production and requires re-assimilation.
- Primary field output is restricted to h1-h3.
- Untrained hazard and RUL outputs are hidden as `unavailable_untrained`.
- The integrated checkout passes 153 tests and the final no-training audit.

## Trigger result

The model-only trigger requests at c83 while the hidden FEM support audit first
fails at c81. A synthetic crack-image geometry innovation moves the request to
c81, giving zero lead. A one-step positive lead appears only after adding an
oracle-derived raw-energy localization proxy.

Therefore the road-facing conclusion is negative: **the currently available
image-like observation does not provide early warning**. The oracle-assisted
result is an upper bound and cannot be described as strain, FWD, or a road
sensor result.

## What is not proven

- No real image, FWD, strain, WIM, temperature, moisture, or maintenance stream
  has been assimilated.
- No calibrated FEM-cycle-to-road-time mapping exists.
- Observation-aware h2-h3 heads have not been trained or ranked.
- Existing free rollouts do not autonomously predict the c87 transition.
- Uncertainty, hazard, threshold probability, and RUL are not calibrated.
- One FEM trajectory and its repeated windows do not establish road or geometry
  generalisation.

## Next justified gate

Do not launch another architecture sweep. The next evidence-producing task is a
small longitudinal observation package with at least three independent
road/laboratory assets or trajectories. Each asset must align registered crack
imagery, FWD or strain response, traffic/load exposure, environment, and
maintenance provenance. Freeze the observation operator and load-block
vectorizer, then use grouped leave-one-asset/road-section-out validation.

Only after those inputs exist should the predeclared Markov/TCN/SSM producer
experiment compare direct h1-h3 with recursive h1 under matched hashes, seeds,
capacity, and budget. Hazard/RUL training additionally requires independent
event and censor diversity.

## Evidence

- Final audit: `audit/compatibility_smoke_summary.json`
- Per-family audit: `audit/closed_loop_compatibility_smoke.csv`
- Agent 1 bundle decision: `analysis/road_observation_state_bundle_v1_20260724/decision.md`
- Agent 2 trigger decision: `analysis/road_observation_innovation_trigger_20260724/decision.md`
- Agent 3 corrected decision: `docs/road_closed_loop_stage2_20260724/decision.md`
- Completion matrix: `completion_evidence_matrix.md`

