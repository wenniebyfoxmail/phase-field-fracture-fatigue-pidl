# Decision: signed factorial LOCO producer gate

## Readiness verdict

The scoped producer gate passes for a controlled **within-Hard5 numerical
factorial** experiment. It does not pass for roads.

- Agent2 producer commit: `90cf8a3703d03609ad7daf066d04ab051c2f7500`
- Contract file SHA: `c32b594559362bf7b7a7b4892e74f8d1001bb8d5ac88c3a3776a8e8333aa57df`
- Internal LOCO lock: `5904af500cde315d8ee9f9087d3f5088c03b59b76cf23f8fbf7b80f6c3fb1691`
- Eligible inventory: four factorial trajectories, 348 cycle-peak states
- Split: four complete-trajectory folds; no node, cycle or window crossing
- Field and deterministic transition-warning training: ready
- Calibrated hazard/RUL: blocked

The producer package contains 624 states in total, but 276 belong to three Umax
sensitivity trajectories. They are excluded from LOCO and do not count as new
factorial trajectories.

## Matched model gate

Only Markov graph, TCN and Transformer are ranking eligible. They share the same
graph encoder (`local_dim=49`, `token_dim=50`), two forecast-time loading
schedule channels, loss, optimizer, three-step exposure, 3000 steps and seeds
1/2/3. Temporal widths are fixed before training.

| Model | Context | Width | Parameters | Error from 329k |
|---|---:|---:|---:|---:|
| Markov | 1 | 463 | 328818 | 0.055% |
| TCN | 3 | 334 | 328745 | 0.078% |
| Transformer | 3 | 124 | 328863 | 0.042% |

This is a 4 fold x 3 model x 3 seed matrix: 36 fixed jobs. No architecture,
context or checkpoint selection is permitted on a held-out combination.

## Sealed evaluation

Each held-out trajectory is evaluated separately on:

1. observed-state same-regime rolling h1-h3;
2. autonomous pre-transition warning using the producer's physical penetration
   criterion on predicted fields;
3. true-observation reset at first hit followed by conditional h1-h3.

Metrics remain FEM eta0 centred: damage linear residuals; history, raw and
active log residuals; absolute/own p99 support; area ratio; centroid and width;
and deterministic missed/false transition warnings. Results are paired against
the same-fold, same-seed Markov control.

## Claim boundary

Passing this run can support only held-out-combination performance within one
shared geometry, mesh, material, Umax and synthetic FEM family. It cannot
support road-like LOTO, independent roads, real-road validation, geometry or
material generalisation.

Hazard/RUL remains unavailable because all four trajectories terminate in an
event and uncertainty is uncalibrated. Unlimited recursive rollout is not a
road long-horizon forecast.
