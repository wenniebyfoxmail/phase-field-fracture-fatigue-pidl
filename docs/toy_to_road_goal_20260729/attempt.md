# Attempt toy_to_road_evidence_goal_20260729

- Status: `active_partial_evidence`
- Created: 2026-07-29T15:41:10+01:00
- Closed: None
- Type: `framework-validation`
- Human decision required: True

## Motivation
Build a leakage-safe evidence chain from corrected dimensionless scaling through independent FEM trajectories and measurable road observations.

## Trigger
User explicitly started Goal mode for tracks 1-4.

## Current Claim Before Attempt
Hard5 is a normalized mechanism benchmark; road transfer, multi-trajectory forecast, and real-observation validity remain unproven.

## GPT Pro Advice
- Required: True
- Advice path: `docs/road_rescaling_bridge_20260724/independent_review.md`
- Advice sha256: `a94e375a22c9a88de1fa916c6823cf1d62da584b0e158bed18c1149f74e4df9b`

Adopted the independent recommendation to treat Hard5 as a dimensionless mechanism benchmark, require exact-Pi positive and model-form negative controls, and keep road measurements distinct from latent fracture fields.

## Adopted Decision
Run four gated tracks in parallel under one versioned FEM/event/observation contract; prohibit forecast training until independent-trajectory readiness passes.

## Rejected Or Modified Advice
Rejected direct toy-to-road unit conversion, Umax-only pseudo-generalization, generic FEM c89 thresholds, latent-to-sensor substitution, and additional temporal architecture sweeps.

## Decision Rationale
Scaling, trajectory generalization, temporal architecture, and observation identifiability answer different questions and must be integrated without allowing one track to compensate silently for another.

## Success Criteria
- F1/F2 transfer controls pass; at least three independent FEM trajectories pass provenance; leave-one-trajectory-out forecast is evaluated; measurable observation interface passes leakage firewall.

## Failure Criteria
- Any track lacks provenance
- mixes event phases
- uses Umax variants as independent roads
- leaks held-out trajectories
- or treats latent fields as direct sensors.

## Code Changes
- modify: `docs/skills/pidl-experiment-gate/SKILL.md` - Replaced universal c89 timing and threshold assumptions with versioned FEM reference and event-phase rules
- add: `docs/toy_to_road_goal_20260729/00_goal_contract.md` - Added shared four-track scientific contract, readiness gates, and final decision classes
- add: `source/toy_to_road_evidence_gate.py` - Added machine gate for corrected scale contract, versioned FEM states, independent-trajectory readiness, forecast freeze, and observation leakage
- add: `analysis/road_measurement_operator_identifiability_v1_20260729/decision.md` - Integrated executable measurement operators and identifiability ladder; real-road evidence remains missing
- add: `docs/pi_transfer_controls_20260729/decision.md` - Integrated corrected scaling, F1a dimensional replay and F2 BC negative control; retained fresh F1b solve as blocker
- add: `analysis/fem_multitrajectory_contract_20260729/decision.md` - Integrated validated 4-cell Hard5 factorial LOCO bundle while keeping road-like LOTO at 0/3
- add: `docs/multi_trajectory_forecast_protocol_20260729/decision.md` - Integrated sealed Markov TCN Transformer protocol and explicit hazard RUL blockers; producer training awaits signed bundle consumption
- add: `docs/multi_trajectory_forecast_protocol_20260729/producer_gate_20260729/producer_experiment_manifest.json` - Accepted signed 4-fold 36-job producer gate with one-percent parameter matching for Markov TCN Transformer
- add: `docs/toy_to_road_goal_20260729/decision.md` - Integrated the four tracks into a terminal blocked-missing-evidence road-transfer verdict
- add: `SENS_tensile/analyze_pavetrack_visual_observation.py` - Added a deterministic visual-only real-road inventory with source hashing and image-space geometry
- add: `analysis/pavetrack_real_observation_pilot_20260731/decision.md` - Sealed 24 observations from three long PaveTrack crack sequences without latent-field leakage
- add: `SENS_tensile/audit_pavetrack_registration_and_split.py` - Reconciled workbook and manifest identity, froze location-level splits and gated pairwise image registration
- add: `analysis/pavetrack_registered_observation_gate_20260731/decision.md` - Accepted provenance and image-space registration only while keeping mechanical assimilation blocked
- modify: `SENS_tensile/analyze_factorial_loco_results.py` - Added strict run/budget checks, absolute model-task and horizon summaries, runtime, and FEM-centred transition/reset figures
- modify: `source/toy_to_road_evidence_gate.py` - Separated completed held-out evaluation from forecast task acceptance

## Input Assets
- `docs/road_rescaling_bridge_20260724/independent_review.md` (independent scale-transfer review; exists)
- `docs/hard5_eta0_umax_reaudit_20260729/decision.md` (event-phase and scaling reaudit; exists)

## Output Assets
- `docs/toy_to_road_goal_20260729/decision.md` (integrated final verdict; missing)
- `docs/toy_to_road_goal_20260729/evidence_matrix.csv` (track-level evidence status; exists)

## Tests
- pass: integration_contract_tests - 31 passed and 1 optional dependency test skipped; gate rejects Umax-only readiness, premature forecast training, missing event phase, latent sensor leakage, and unapproved architectures.
- pass: observation_interface_integration - 48 passed and 1 optional dependency test skipped; identifiability blocker cleared while real-road-data blocker remains.
- pass: scaling_control_integration - 41 passed; F2 blocker cleared, but exact-Pi positive control remains blocked because F1 used archived dimensional replay rather than a fresh solver run.
- pass: fem_bundle_and_scope_gate - 43 passed; within-Hard5 factorial training is ready, road-like training remains false, and the gate preserves a separate fewer_than_three_road_like_trajectories blocker.
- pass: forecast_protocol_integration - 66 passed and 2 optional fixture tests skipped; no training result is claimed yet.
- pass: signed_forecast_producer_gate - 61 passed; within-Hard5 producer gate released, road-like and hazard/RUL gates remain closed.
- pass: external_blocker_reporting - 71 passed; the machine gate preserves within-benchmark training readiness while separately reporting inaccessible F1b and forecast producers.
- pass: factorial_loco_execution - Taobo completed 36/36 fixed jobs; 254/254 downloaded files match the remote SHA-256 manifest.
- pass: factorial_loco_analysis_tests - 30 focused tests passed; no temporal candidate met the locked promotion rule.
- pass: final_full_regression - 249 passed, 2 skipped, 1 pre-existing Transformer nested-tensor warning.
- pass: producer_runtime_audit - VPN and Taobo are healthy, but sealed F1b remains Windows-MATLAB-only because Mac and Taobo lack MATLAB, GRIPHFiTH MEX and SuiteSparse.
- pass: wider_trajectory_inventory - Hard5 factorial remains the only complete unified mechanism corpus; strict independent road-like count is 0/3.
- pass: real_observation_inventory - PaveTrack_PD contains 8,928 unique real image-mask pairs across 165 locations, but lacks physical scale, timezone, cross-visit registration and paired mechanical/load/environment channels.
- pass: pavetrack_visual_pilot - 4 tests passed; 24/24 selected image-mask pairs were hashed and all six package assets passed SHA-256 verification.
- pass: pavetrack_registration_gate - 3 focused tests passed; count discrepancy reconciled, 118/23/24 location split locked and 18/21 registrations passed without imputing failures.

## Result Interpretation
The four-track evidence contract is valid and the Hard5 factorial LOCO matrix
is complete. This is not road readiness. F1b still needs a fresh Windows-FEM
solve; road-like trajectories remain 0/3; and no real-road dataset has passed
the measurement interface. TCN and Transformer are not promoted; all models
miss transition warning and fail post-reset active-support localization.

## Claim After Attempt
Corrected scaling, factorial trajectory provenance, completed held-out forecast
performance, and the measurement firewall are implemented and verified.
Exact-Pi solver invariance, road-trajectory generalization, and real-road
identifiability remain unproven.

## Next Action
Run the unchanged F1b input on the approved Windows-FEM producer when available;
acquire three road-like trajectories and a registered real-road observation
dataset. Do not launch a new temporal architecture or claim road validation
while these blockers remain.

Resumption audit: after explicit VPN authorization, Tunnelblick connected and
Taobo completed the sealed forecast matrix. CSD3 credentials and Windows-FEM
F1b remain unavailable, but Taobo is no longer an active blocker.
