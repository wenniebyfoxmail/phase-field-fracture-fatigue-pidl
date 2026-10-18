# S09-E010 focused design rereview request

The first independent review returned `DESIGN_BLOCKED` with one minimal
protocol ambiguity. It found no design-level blocker in the operator/physics
boundary, losses, target-use boundary, projected multi-objective direction,
three-arm comparison, thresholds, budget, exact-replay gate or evidence
contract.

## Exact repair

The prospective protocol is now revision v2. Level 6 now states that
`NOMINATE_CONFIRMATORY_P1` requires **all** conditions of Level 5
`ORIGINAL_RELATIVE_REPAIR_SIGNAL`, explicitly including the primary criterion
and all four contemporaneous-`A25` protected ratios, before the persistence
improvement inequality is considered.

The review also identified a boundary implementation detail. The unchanged
`Delta_AUC >= 0.08` threshold is now evaluated by the exactly equivalent
integer pair-count condition
`(2*W_B25 + T_B25) - (2*W_A25 + T_A25) >= 4`, avoiding floating-point rejection
of a mathematically exact boundary result. No threshold or outcome meaning was
changed.

No loss, coefficient, arm, update budget, dataset, reference value or E009
criterion changed. No model, gradient or optimiser was run.

Please perform a focused rereview of only these changes and return:

- `DESIGN_READY_PASS` if the single blocker is closed, allowing only local
  implementation, deterministic no-step preflight and exact-commit review; or
- `DESIGN_BLOCKED` with the remaining precise ambiguity.

Do not authorize training.
