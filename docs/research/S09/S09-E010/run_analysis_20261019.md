---
storyline_id: S09
experiment_id: S09-E010
run_id: S09-E010-R001-support-amplitude-three-arm
status: NO_TARGETED_RANKING_SIGNAL
date: 2026-10-19
---

# S09-E010 support/amplitude producer result

## Question and learned mapping

This experiment asked whether separately balanced damage-support and
per-cycle-amplitude objectives improve growth-versus-stagnant ranking over the
exact E009 `A25` control while preserving its useful component metrics.  The
learned state operator remained

`(d_s00(x), [H, alpha_bar, q_prev, f]_s00(x_gp), prescribed load path, fixed mesh/material/boundary)`

`-> (d_s04(x), [H, alpha_bar, q_prev, f]_s04(x_gp), u_s04(x))`.

The physics direction was the native-Q4 AMOR mechanical-equilibrium residual
on free displacement degrees of freedom at the predicted `s04` peak. It did
not impose damage stationarity, fatigue-history evolution, or the complete
incremental fracture variational inequality. This remains a limited
physics-informed state-operator screen, not a complete fracture-evolution
PINO.

## Execution and retrieval validity

The one authorised Taobo run used reviewed code commit
`010281be8045301f7e56b938de82969982c89bc9`, packet-manifest SHA256
`1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6`,
and resolved-config SHA256
`be399942c28d640da8e61a2f47f680433b546ce502c5791bb88ee7297a9542b4`.
It ran on `GPUServer8`, physical GPU UUID
`GPU-ea68e432-5acb-5488-5be1-4ba9a2053beb`, for 375.83 seconds before evidence
closure.

All three arms completed exactly 500 optimiser updates, 500 gradient rows,
seven frozen evaluations, and one update-500 checkpoint. All outputs were
finite and every hard-constraint count was zero. Shared identity passed, and
the `A25` control passed every exact-replay clause. The run and archive
completion receipts are byte-identical with SHA256
`a5e104e0ec401a8fcbd3d1416f1ab86a85353957ed8e4bd47d90143b458d9be4`.
After retrieval, all 28 files matched the remote SHA256 manifest.

## Frozen update-500 result

| arm | growth MAE `G` | false growth `F` | amplitude AUC | `L_P` | `L_judge` | spatial median |
|---|---:|---:|---:|---:|---:|---:|
| exact `A25` replay | 5.14460e-4 | 1.32370e-5 | 0.68 | 0.720172 | 0.701712 | -0.00798 |
| `B25`, balanced + physics | 5.04627e-4 | 3.07044e-6 | 0.68 | 0.722428 | 0.713208 | -0.00644 |
| `B0`, balanced without physics | 5.53927e-4 | 6.16995e-5 | 0.68 | 2194.52 | 0.652298 | 0.07556 |

The primary pair score was `34` for both `A25` and `B25`; the observed gain
was `0`, below the frozen requirement of `4` (equivalent to an AUC gain of
0.08). All protected `B25/A25` ratios passed: `G=0.98089`, `F=0.23196`,
`L_P=1.00313`, and `L_judge=1.01638`. The frozen classification is therefore
`NO_TARGETED_RANKING_SIGNAL`.

This is a graded result rather than a blanket failure. `B25` reduced false
growth by 76.8% relative to `A25` and slightly reduced growth MAE without
violating the protected metrics. The added support/amplitude objectives did
not improve the target ranking. Within the balanced formulation, beta 0.25
reduced `L_P` from `2194.52` to `0.7224`, `G` by `4.93e-5`, and `F` by
`5.86e-5` relative to `B0`. It raised `L_judge` by `0.0609` and left the AUC
pair score unchanged. The equilibrium term is therefore useful for keeping
the balanced model mechanically controlled, but it did not create
growth-regime discrimination.

## Field evidence

The update-500 checkpoints were replayed locally on the same frozen packet
with zero optimiser steps. Recomputed per-cycle amplitudes matched the frozen
CSV to a maximum absolute difference of `4.07e-20`. Numerical comparisons use
native-node fields; nearest-node rasterisation is display-only.

At cycle 69, FEM has weighted mean increment `2.564e-4`. `A25`, `B25`, and
`B0` predict `1.276e-5`, `2.749e-6`, and `5.681e-5`, respectively. The
shape-only view shows that `A25/B25` respond mainly at the right boundary,
rather than reproducing the concentrated FEM crack-tip event. At cycle 73,
the total peak fields look similar because the supplied pre-existing crack
dominates them. The increment view reveals that FEM is nearly stagnant
(`1.096e-6`), while `A25`, `B25`, and `B0` predict `1.275e-5`, `2.744e-6`,
and `5.675e-5`.

Across the 16 cycles, the true amplitude coefficient of variation is `1.887`.
It is only `0.040` for `A25`, `0.114` for `B25`, and `0.099` for `B0`.
`B25` therefore lowers the common positive damage floor but still produces a
weakly cycle-dependent response. The support and amplitude gradients were not
absent: `L_S` was active on all 500 updates and `L_A` on 499/500 updates in
both balanced arms. The observed failure is downstream of merely adding those
objectives.

The GIF covers the 16 stored, independently supplied `s00 -> s04` transitions.
The packet does not contain model outputs at `s01/s02/s03/s05`, so the GIF is
not a within-cycle loading-step movie or an autoregressive rollout.

## No-training discriminator and next intervention

The initial SVD audit found that the update-500 predicted increments have a
cycle-centred effective rank of only 1.13--1.34. `L_S` and `L_A` gradients are
also essentially rank one and their growth/stagnant contrast directions align
with `L_D`. Low rank alone, however, does not prove that the head cannot repair
the ordering: a rank-one Jacobian can still move margins if its row
coefficients differ.

A focused B25 update-500 audit therefore computed the direct amplitude
contrast Jacobian for all 25 frozen growth/stagnant pairs. The eight wrong
pairs are exactly `{58,60,69,70} x {3,4}`. All have finite nonzero local repair
sensitivity: median `||J_g-J_s||=2.969e-3`, or 12.10% of the two-row RMS norm.
The first-order minimum parameter displacement required to reach zero margin
is only `5.23e-5` of the observed initial-to-B25 displacement. In contrast,
the current mean B25 descent direction decreases all eight wrong margins and
increases all 17 correct margins; its cosine with each wrong-pair contrast is
approximately `-0.988`.

This evidence prioritises objective repair over head repair. The next minimal
controlled experiment should start both arms from the same B25 update-500
checkpoint, preserve the current operator and beta 0.25 physics term, and
compare a compute-matched B25 continuation against an explicit cross-cycle
pairwise/listwise amplitude-ranking objective. An amplitude-times-support head
is deferred until a same-head ranking objective has usable zero-step gradients
but still cannot repair margins within the protected field and physics costs.

## Claim boundary

This is one fixed 16-cycle synthetic development trajectory. It establishes
execution validity, a useful conditional equilibrium effect, and a negative
targeted-ranking result for the tested support/amplitude rule. It does not
establish rollout, fresh-holdout, cross-trajectory, cross-mesh, FEM-truth,
full-PINO, or real-road generalisation.

The original result package plus its same-run raw-log supplement received
`RESULT_EVIDENCE_READY_PASS`: 48/48 A25 update-500 projection counts matched
the frozen E009 reference and the exact replay gate passed 33/33 clauses.


## 2026-10-20 historical verification addendum

An independent exact-diff review returned `CODE_READY` for historical producer
commit `010281be8045301f7e56b938de82969982c89bc9`. A separate bounded CPU-only
no-training regression then passed 117/117 E009+E010 tests with zero real
optimizer-step or CUDA-init attempts. The strict audit wrapper exited one only
because it rejected three optional dependency probes; pytest itself exited
zero. See `historical_code_review_and_no_training_regression_20261020.md` and
the preserved evidence directory. This addendum does not rerun the producer,
reopen the holdout, or alter `NO_TARGETED_RANKING_SIGNAL`.
