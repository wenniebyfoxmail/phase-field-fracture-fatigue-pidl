# S09-E008 P1 bounded memorisation run analysis — 2026-10-16

## Outcome

The reviewed run completed successfully as an execution:

- Run ID: `S09-E008-P1-R001-stage0a-memorisation`
- exact commit: `f54327490ce8c02f6c042753d36ddcd32ecc5771`
- packet manifest: `1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6`
- authorised config: `8aeec2b6f8c33b9d4efbeae57e4d20dd8f3e056ca9c0f9250e21c7c7466afe4f`
- producer: `GPUServer8`, physical GPU `GPU-980d2e42-c060-c272-b10b-8fbc204fef7f`
- exit code: 0; elapsed: 165.32 s
- optimiser steps: 1,000; fully logged updates: 1,000; final diagnostic: update 1,000
- finite outputs/gradients and projected hard-constraint violations: valid / zero

The formal P1 result is `false`. This is a scientific-performance result for the frozen bounded memorisation question, distinct from the successful execution.

## Frozen decision clauses

| Clause | Initial | Final | Frozen target | Result |
|---|---:|---:|---:|---|
| Capacity, `L_judge` | 0.854137 | 0.705714 | final <= 0.170827 | fail |
| Growth-cycle damage increment MAE | 0.000501735 | 0.000573133 | final < 0.000501735 | fail |
| Near-stagnant false growth | 0 | 0.0000759554 | final <= 0.0000421613 | fail |
| Validity | finite, zero violations | finite, zero violations | finite, zero violations | pass |

`L_judge` improved by 17.38%, but the frozen capacity clause required an 80% reduction. The best scheduled value was 0.695180 at update 500, after which it plateaued near 0.706. The result must remain a formal fail; the threshold is not changed after observing the run.

## What worked

The physics objective learned strongly. Comparing the first and last complete 16-cycle epochs:

| Objective component | First epoch mean | Last epoch mean | Change |
|---|---:|---:|---:|
| equilibrium | 0.991064 | 0.165232 | -83.3% |
| projected nodal state | 0.780135 | 0.640389 | -17.9% |
| projected GP history | 0.995182 | 0.876176 | -12.0% |
| raw GP increment | 0.996231 | 0.777138 | -22.0% |
| raw nodal increment | 0.999867 | 0.999246 | -0.06% |

The model therefore did not simply fail to optimise. It learned the Q4/AMOR equilibrium residual and some projected state/history structure while keeping every hard constraint valid. This establishes architecture wiring and differentiable physics-path viability for this packet.

## Main failure mechanism

The damage response collapsed toward an almost cycle-independent positive increment. A no-optimiser final-checkpoint evaluation found:

- mean predicted absolute damage increment: `7.36e-5` on growth cycles, `7.61e-5` on near-stagnant cycles;
- mean true absolute damage increment: `5.02e-4` on growth cycles, `2.76e-6` on near-stagnant cycles;
- growth cycles therefore mostly suffer missed growth (`5.01e-4` mean), while near-stagnant cycles suffer false growth (`7.60e-5` mean).

Cycle 1 is the clearest case: true mean increment `1.5355e-3`, predicted `8.5638e-5`. For cycles 72–73, true increments are around `3.60e-7` and `1.10e-6`, but predicted increments remain about `7.04e-5`. The operator has learned a positive damage floor rather than the required cycle-conditioned amplitude.

This also explains why growth and near-stagnant criteria move in opposite directions. Increasing the common positive increment helps some growth examples but creates false growth on stagnant examples; reducing it protects stagnant examples but increases missed growth.

## Multi-objective evidence

The frozen gradient merger was active and auditable:

- conflict projection occurred on 584/1,000 updates, with 1,938 individual projections;
- global clipping was active on 719/1,000 updates;
- no whole-objective zero direction occurred;
- nodal-state versus equilibrium raw gradients were negative on 474 updates and had mean cosine 0.0158;
- GP-history versus equilibrium gradients were negative on 371 updates;
- nodal-state versus GP-history gradients were negative on 143 updates.

The equilibrium objective improved much faster than the two data objectives, while the raw nodal increment barely improved. This supports the user's multi-objective concern: a valid compromise update can still allocate effective progress very unevenly. The result does not show that physics-informed training is useless; it shows that the present equalised cyclic-projection rule and damage parameterisation do not recover the damage-regime separation needed by P1.

## Interpretation buckets

| Bucket | Result |
|---|---|
| Execution integrity | strong positive: exact identities, exit 0, 1,000/1,000 logs, no stderr |
| Architecture wiring | positive: forward/backward, native supports and three objectives function end-to-end |
| Physics path | positive but dominant: equilibrium objective fell 83.3% |
| Overall memorisation capacity | partial: `L_judge` fell 17.4%, far short of the frozen 80% target |
| Damage growth skill | negative: large missed growth, especially cycle 1 |
| Near-stagnant control | negative: positive damage floor exceeds `0.25D` |
| Hard constraints | positive: zero projected violations throughout |
| Scientific claim | bounded mechanism evidence only; no rollout, generalisation, FEM-truth or PINO-benefit claim |

## Recommended next gate

Freeze this run as a non-retry formal P1 fail and open a new diagnostic experiment rather than relaxing the P1 decision retrospectively.

The next experiment should isolate two changes:

1. expose damage-regime separation as its own objective and report growth/stagnant Pareto behaviour instead of hiding damage inside the combined nodal objective;
2. compare the current PINO merger against a data-only neural-operator reference and one adaptive multi-objective rule using the same packet, seed and bounded update budget.

Use a graded scorecard during this diagnostic stage: execution/constraints, capacity improvement, growth error, stagnant false growth, equilibrium residual, raw-versus-projected learning and gradient conflict. Formal binary criteria remain unchanged for P1 and are applied only to a newly frozen confirmatory gate.

## Evidence

- local producer output: `local_archive/experiments/S09-E008/runs/S09-E008-P1-R001-stage0a-memorisation/producer_output/`
- 13 producer files were downloaded and matched the remote SHA256 inventory.
- `per_cycle_final.json` is a post-run, no-optimiser diagnostic generated from the frozen final checkpoint; SHA256 `a6020ee48860d33ba0c64d7073f7daea586f8920504e5f9fdcd9eb382f819e0e`.
