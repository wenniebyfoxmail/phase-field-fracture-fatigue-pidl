# Attempt fem_shared_geometry_factorial_audit_v1

- Status: `accepted`
- Created: 2026-07-29T16:13:39+01:00
- Closed: 2026-07-29T16:13:40+01:00
- Type: `framework-validation`
- Human decision required: False

## Motivation
Audit the hard/soft initial-tip x 5/8-step package as a scoped shared-geometry 2x2 numerical gate without inflating road-level readiness.

## Trigger
User clarified that the package genuinely crosses two controlled axes.

## Current Claim Before Attempt
The package may qualify for within-Hard5 leave-one-combination-out only if full mechanism fields, provenance, mesh, step, cycle, and event semantics pass.

## GPT Pro Advice
- Required: False
- Advice path: ``
- Advice sha256: ``

Not recorded.

## Adopted Decision
Maintain two separate readiness gates: allow scoped within-Hard5 factorial LOCO only; keep road-like LOTO blocked.

## Rejected Or Modified Advice
Modified the prior wholesale exclusion of the 2x2 package; rejected counting its cells as independent roads or geometry/material generalization.

## Decision Rationale
The four cells differ in initial-tip state and loading history, but share geometry, mesh, material, Umax, eta, and event rule.

## Success Criteria
- Four unique combinations pass deep source-backed validation and form complete-trajectory LOCO folds with explicit claim boundaries.

## Failure Criteria
- Any missing field
- provenance mismatch
- mesh mismatch
- duplicate factorial cell
- loading-step mismatch
- or road-generalization claim.

## Code Changes
- modify: `SENS_tensile/fem_trajectory_bundle.py` - Add controlled-factorial contracts, VTK mesh evidence, bounded solver overshoot audit, and class-aware whole-trajectory split validation
- modify: `SENS_tensile/build_fem_multitrajectory_contract.py` - Ingest and audit all four factorial cells, separate road LOTO from numerical LOCO, and register duplicate/excluded packages
- modify: `tests/test_fem_trajectory_bundle.py` - Test complete 2x2 coverage, scoped readiness, leakage boundaries, and damage numerical tolerance

## Input Assets
- `/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/griphfith/Umax_012_all_versions_20260729` (shared-geometry 2x2 source package; exists)

## Output Assets
- `analysis/fem_multitrajectory_contract_20260729/within_hard5_factorial_loco_split_lock_v1.json` (scoped split lock; exists)

## Tests
- pass: deep_source_ingestion - 7/7 bundles and 624/624 state shards passed; 4/4 factorial source audits passed; all factorial VTK meshes share one 86408-cell content hash.
- pass: cli_factorial_revalidation - Four source-backed bundles and the four-fold scoped LOCO lock independently revalidated.
- pass: regression_tests - 36 tests passed.

## Result Interpretation
The 2x2 package is ready only for a controlled shared-geometry leave-one-combination-out numerical gate. Road-level readiness remains blocked.

## Claim After Attempt
Four controlled factorial trajectories pass full contract validation, but they are not independent roads and provide no material or geometry generalization evidence.

## Next Action
Wait for the independent FEM handoffs before road-like LOTO; any later factorial training must use the frozen four-fold lock.
