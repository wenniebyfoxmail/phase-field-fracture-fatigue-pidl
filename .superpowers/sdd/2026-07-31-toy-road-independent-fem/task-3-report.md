# Task 3 Report: T1 Mesh Transfer and Event State Machine

## Changed Files

- `producer_handoffs/toy_to_road_independent_fem_20260731/apply_t1_mesh_transfer.m`
- `producer_handoffs/toy_to_road_independent_fem_20260731/advance_toy_road_event.m`
- `producer_handoffs/toy_to_road_independent_fem_20260731/tests/toyRoadConfigTest.m`

The reviewed config builder and all input locks remain unchanged.

## RED Evidence

`matlab -batch "r=runtests('producer_handoffs/toy_to_road_independent_fem_20260731/tests/toyRoadConfigTest.m'); assertSuccess(r)"`

The suite failed as expected because `apply_t1_mesh_transfer` and
`advance_toy_road_event` were undefined. The new mesh, audit-gate, connected
component, c10 first-hit, c13 confirmation, miss-reset, and no-replacement
tests all exercised the absent helper interfaces.

## Implementation

`apply_t1_mesh_transfer` applies the approved map exactly:

```text
x' = -0.5 + 1.25 * (x + 0.5), x <= 0
x' =  0.125 + 0.75 * x,       x > 0
y' = y
```

It preserves Q4 connectivity, validates the fixed external boundaries and
notch-tip identity, evaluates signed Jacobians at all Q4 natural corners,
computes tip-incident edge `h/ell` ratios, and records deterministic parent
and candidate SHA-256 mesh hashes. Any invalid input, inverted Q4 corner, or
out-of-range local ratio raises `toyRoad:MeshTransferGateFailed` before the
function returns. The helper contains no FEM solve call.

`advance_toy_road_event` builds candidate adjacency from Q4 edges only. It
accepts nodes with `x >= 0.48` and peak damage `d >= 0.95`, finds the largest
connected component, requires at least three members, and records hit-node and
component evidence. A hit at c10 records `first_hit = 10`; c11, c12, and c13
are the three post-hit cycles, so `confirmed = 13`. A miss resets only the
post-hit counter and never replaces the original first-hit cycle.

## GREEN Evidence

`matlab -batch "r=runtests('producer_handoffs/toy_to_road_independent_fem_20260731/tests'); assertSuccess(r)"`

Output: `Totals: 17 Passed, 0 Failed, 0 Incomplete.`

## Self-Review

- Confirmed the T1 map fixes `x = -0.5` and `x = 0.5`, maps `(0, 0)` to
  `(0.125, 0)`, and preserves `y`.
- Confirmed both inverted-Q4 and over-large local-edge fixtures fail with the
  required mesh-transfer gate identifier.
- Confirmed the event tests use deliberately non-consecutive node IDs and a
  spatially close but Q4-disconnected counterexample, so coordinate proximity
  and node numbering cannot substitute for edge-derived adjacency.
- Confirmed confirmation occurs at c13 only after c11-c13, and a pre-confirm
  miss resets progress without replacing c10.
- No MATLAB/FEM computational experiment or solve was started.

## Concerns

- This task implements helper-level validation only. The later trajectory
  orchestrator must call `apply_t1_mesh_transfer` before any future solve and
  retain the returned audit with its output provenance.
