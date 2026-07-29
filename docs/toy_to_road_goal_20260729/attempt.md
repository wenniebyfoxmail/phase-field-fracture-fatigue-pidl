# Attempt toy_to_road_evidence_goal_20260729

- Status: `tested`
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

## Input Assets
- `docs/road_rescaling_bridge_20260724/independent_review.md` (independent scale-transfer review; exists)
- `docs/hard5_eta0_umax_reaudit_20260729/decision.md` (event-phase and scaling reaudit; exists)

## Output Assets
- `docs/toy_to_road_goal_20260729/decision.md` (integrated final verdict; missing)
- `docs/toy_to_road_goal_20260729/evidence_matrix.csv` (track-level evidence status; exists)

## Tests
- pass: integration_contract_tests - 31 passed and 1 optional dependency test skipped; gate rejects Umax-only readiness, premature forecast training, missing event phase, latent sensor leakage, and unapproved architectures.

## Result Interpretation
Not recorded.

## Claim After Attempt
Not recorded.

## Next Action
Not recorded.
