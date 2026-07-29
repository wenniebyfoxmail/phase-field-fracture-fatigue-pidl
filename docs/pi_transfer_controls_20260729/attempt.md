# Attempt pi_transfer_controls_20260729_v1

- Status: `accepted`
- Created: 2026-07-29T16:04:30+01:00
- Closed: 2026-07-29T16:09:02+01:00
- Type: `framework-validation`
- Human decision required: True

## Motivation
Implement corrected w1 scaling and test complete-Pi dimensional transfer against FEM-centred archived controls.

## Trigger
User approved direct implementation of F1 exact-Pi and F2 categorical negative controls.

## Current Claim Before Attempt
The existing audit supports dimensional similarity only; F1/F2 field controls were not yet executed.

## GPT Pro Advice
- Required: True
- Advice path: `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/road-rescaling-bridge/docs/road_rescaling_bridge_20260724/independent_review.md`
- Advice sha256: `a94e375a22c9a88de1fa916c6823cf1d62da584b0e158bed18c1149f74e4df9b`

Adopt complete dimensionless similarity and categorical model-form gates; reject direct road, plane-state, temperature/rate, and cycle-to-traffic claims.

## Adopted Decision
Run deterministic archived-FEM F1 dimensional replay plus the cleanest available same-mesh BC negative control; do not use the new 2x2 protocol package as primary F2.

## Rejected Or Modified Advice
The hard/soft x 5/8-step package changes initial crack and loading protocol factors and is retained only as auxiliary sensitivity evidence.

## Decision Rationale
This is the smallest evidence set that exercises corrected scaling and independently falsifies scalar-Pi sufficiency without training.

## Success Criteria
- F1 matches every declared Pi/model-form row and normalized FEM field at locked cycles; F2 matches scalar Pi but changes BC and produces an observable consequence.

## Failure Criteria
- Any source/provenance/state/mesh ambiguity
- non-finite field
- hidden imputation
- or complete-Pi mismatch quarantines the affected claim.

## Code Changes
- modify: `source/scaling.py` - Add corrected complete-Pi contract and reusable matched/mismatched/unobservable audit
- add: `SENS_tensile/run_pi_transfer_controls.py` - Run archived-FEM F1 exact-dimensional replay and same-mesh F2 BC negative control
- modify: `tests/test_scaling.py` - Cover corrected Pi groups and observability classification
- add: `tests/test_pi_transfer_controls.py` - Cover F1 identity F2 categorical mismatch and weighted round trip
- add: `tests/test_pi_transfer_package.py` - Validate result claims protected scope and hashes
- add: `docs/pi_transfer_controls_20260729` - Add predeclared gate generated evidence package ledger and decision
- modify: `docs/pidl_experiment_inventory.md` - Register corrected Pi-transfer diagnostic
- modify: `SENS_tensile/run_pi_transfer_controls.py` - Deduplicate exact-replay arrays in the committed normalized NPZ while retaining all locked cycles

## Input Assets
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/road-rescaling-bridge/source/compute_energy.py` (implemented energy convention; exists)
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/extracted/SENS_brittle_base_cyclic_u012_recovery_fatigueon_pidlstop_newtontol4em4/psi_fields/cycle_0089.mat` (F1 locked c89 field; c20/c40/c60 siblings required by runner; exists)
- `/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/u12_cycle_0082_FEM7.mat` (F2 free-lateral event; exists)
- `/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_reverseBC_u12_cyclewise_mechanism_2026-05-28/reverseBC_u12_cyclewise_element_fields_c1_c74.mat` (F2 reverse-BC event; exists)

## Output Assets
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/road-rescaling-bridge/docs/pi_transfer_controls_20260729/decision.md` (terminal decision; exists)
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/road-rescaling-bridge/docs/pi_transfer_controls_20260729/RUN_MANIFEST.json` (provenance manifest; exists)

## Tests
- fail: initial-control-run - Worktree archive root resolved to .codex/worktrees; no scientific outputs were produced. Runner patched to discover project-level local_archive.
- pass: corrected-control-run - F1 complete Pi passed with max normalized field error 1.7764e-15; F2 scalar Pi passed while BC mismatched and event changed c82 to c74.
- pass: focused-tests - 15 focused tests passed.
- pass: full-regression - 167 passed, 1 skipped; one pre-existing Transformer nested-tensor warning.
- pass: package-hashes - All nine generated primary assets and manifest matched SHA-256.
- pass: final-full-regression - 167 passed, 1 skipped after final archive deduplication; one pre-existing Transformer warning.
- pass: final-package-hashes - All nine generated primary assets and manifest match final SHA-256 values.

## Result Interpretation
F1 validates corrected dimensional normalization and archived-field replay. F2 independently shows that scalar Pi matching does not neutralize BC sensitivity; missing F2 raw/active fields remain unobservable.

## Claim After Attempt
Correct w1 scaling and the reusable Pi-transfer gate are validated as diagnostic tooling only. No road, fresh-solver, traffic-cycle, forecast, or inverse claim is supported.

## Next Action
Run a genuinely independent dimensional F1 solver case, then one-factor plane-state/load-form controls before any measured layered-road anchor.
