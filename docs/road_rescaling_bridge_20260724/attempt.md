# Attempt road_rescaling_bridge_20260724

- Status: `tested`
- Created: 2026-07-24T21:21:22+01:00
- Closed: 2026-07-24T21:21:23+01:00
- Type: `framework-validation`
- Human decision required: True

## Motivation
Determine whether the normalized toy fracture-fatigue benchmark can be dimensionalized consistently and define the boundary to a real road model.

## Trigger
User requested rescaling while three independent FEM trajectories are produced.

## Current Claim Before Attempt
The formal setting is a toy mechanism benchmark; no real-road scale transfer is established.

## GPT Pro Advice
- Required: True
- Advice path: `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/road-rescaling-bridge/docs/road_rescaling_bridge_20260724/independent_review.md`
- Advice sha256: `a94e375a22c9a88de1fa916c6823cf1d62da584b0e158bed18c1149f74e4df9b`

Adopt exact dimensionless similarity, explicit reality observability, and three staged FEM controls; reject direct cycle-to-traffic and 2D-to-road claims.

## Adopted Decision
Run a no-training dimensional-similarity diagnostic and correct the w1 convention before any producer case.

## Rejected Or Modified Advice
No automatic road parameter preset and no producer run in this attempt.

## Decision Rationale
Existing source and archives are sufficient to falsify an incorrect units map at much lower cost than training.

## Success Criteria
- Exact-Pi physical realizations recover the formal dimensionless vector; code scaling matches the implemented energy; road claim boundaries are explicit.

## Failure Criteria
- Energy scaling is inconsistent or the required dimensionless groups cannot be represented.

## Code Changes
- modify: `source/scaling.py` - Correct w1=G_c/ell and add generic dimensionless scaling contract
- add: `SENS_tensile/analyze_road_rescaling_bridge.py` - Add offline comparison, sensitivity, observation-map, and figure builder
- add: `docs/templates/road_rescaling_contract_v1.schema.json` - Add road rescaling evidence schema
- modify: `SENS_tensile/analyze_road_rescaling_bridge.py` - Finalize similarity gate and package hashes

## Input Assets
- `SENS_tensile/config.py` (formal toy settings; exists)
- `source/compute_energy.py` (implemented energy definition; exists)

## Output Assets
- `docs/road_rescaling_bridge_20260724/decision.md` (primary decision; exists)
- `docs/road_rescaling_bridge_20260724/dimensionless_case_comparison.csv` (comparison table; exists)

## Tests
- pass: scale-unit-tests - 6 tests pass; exact toy realization is invariant and extra c_w factor is rejected.
- pass: offline-package - CSV, JSON, and figure assets generated without training.
- pass: full-regression - 158 passed, 1 skipped; one pre-existing Transformer nested-tensor warning.
- pass: schema-and-hashes - Road contract schema validates and all seven primary package hashes match.

## Result Interpretation
The corrected contract supports dimensional similarity only. Legacy PCC and formal toy occupy different dimensionless fatigue/load regimes.

## Claim After Attempt
A physical realization is equivalent only when the full declared dimensionless vector and model form are preserved; road calibration and cycle-to-traffic mapping remain unproven.

## Next Action
After independent FEM trajectories, run exact-Pi positive control, one-factor negative controls, then a measured layered-road anchor.
