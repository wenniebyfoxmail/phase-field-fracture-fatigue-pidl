---
storyline_id: S04
experiment_id: S04-E019
protocol_revision: 20261013-r1-frozen-base-residual
status: plan-pass-implementation-pending
---
# Preserve the E017 global fit while correcting damage residual

## Mechanism, scope and cheap check

Can a compact residual on an immutable E017 backbone improve damaged-region displacement without background deterioration? E018 damage improvement/background regression supports this next bounded repair. Exact outside-support squared errors imply RMS lower bounds .00022221/.00024724/.00014483, below desired .001. This excludes only the immutable outside-domain impossibility, not inside/taper attainability or successful training. Baselines are exact E017 alpha.7 seed7 final checkpoints from backbone_locks.json. No inherited optimizer state.

User requests solution progression across early/middle/transition states. External combined Evidence/PLAN review PASS recommends six matched residual arms. Next gate is implementation/checkpoint admission/tests and independent exact-commit Code Ready; not producer launch yet.

## Frozen minimum matrix

c20s4/c60s4/c83s4 × unrestricted/localized residual, seed7. Plus three no-new-training exact backbone evaluations. Same admitted UV references and native-Q4 evaluator; fixed FEM damage/history/fatigue. c40 is E017 sentinel, not part of this frozen six-run screen; any broader success validation must include it.

Backbone eval mode, all parameters requires_grad=False, immutable state/hash before/after. Cache only if checked against exact frozen checkpoint inference. Residual is 8x283 TrainableReLU float64, both arms identically seeded hidden Xavier initialization and zero output projection weights/bias. Do not zero every layer. Both arms start at exact inherited UV; same trainable parameter count and fresh independent optimizers.

Both residual arms use the SAME anchored coordinate transform (xy-center)/scale. Only candidate applies existing r2 C2 window; unrestricted uses1. This resolves the review's window-only mechanism control without introducing a coordinate confound. Geometry unique active>.1 Q4-edge initial-notch anchor, padding.02, frozen target-independent geometry. Predict uv=backbone_uv + (y+.5)(.5-y) * window * residual. BC factor homogeneous on correction; do not apply affine load twice. All islands stay in objective and metrics.

Same full mass-weighted MSE/Us², unbiased conditional mass sampling with replacement, alpha.7 (11469/4915), PCG64(seed+1000003), damage then background no shuffle; same sampled indices across matched arms. AdamW lr1e-3, unchanged E017 options, cosine10000 eta_min1e-5. Exactly10000 NEW residual-only steps, fixed passive monitoring0/1000/...10000, final-only. No warmstarting residual arms or choosing viewed checkpoints.

## Budget and metrics

Each pipeline inherits10000 backbone steps plus10000 residual steps. Existing3 backbones shared sunk compute; six residual runs cost60000 NEW optimizer steps. Report elapsed GPU time and parameter counts. No same-total-budget/from-scratch superiority against E017/E018. Matched E019 arms have equal new budget.

Primary candidate gate max3state full RMS/|Us|<=.001. All6 valid required. FROZEN_BASE_LOCAL_RESIDUAL_SCREEN_PASS/FAIL; missing interrupted=>INCONCLUSIVE, integrity=>INADMISSIBLE precedence. Secondary diagnostics never rescue primary miss.

Component designation only if all3 damage conditional RMS decrease (strict improvement beyond atol1e-14) AND all3 total background conditional RMS do not increase vs exact inherited baseline beyond atol1e-14. Also report matched-control regional ratios. Outside-support candidate delta must be zero within evaluation atol1e-12 in physical UV; verify baseline/full metric cache agreement atol1e-14. These are numerical checks, not cross-seed statistical claims. Report support-inside/background-outside contributions and damage islands. Do not equate regional RMS with weighted contributions.

Nonfinite outputs, identity/BC/frozen-weight/geometry failure or execution resource failure stop safely; no scientific retry. No adaptive lr/early stopping/budget extension/padding/activation/alpha sweep. Late tails don't prove convergence.

## Mandatory code checks and evidence

Tests: paired initialization/parameter count; zero initial correction; nonzero output-projection gradients despite zero projection; frozen weights absent from optimizer; exact outside-window preservation with arbitrary residual parameters; homogeneous BC; geometry/state locks; cache-to-checkpoint output agreement; same sampler indices/unbiased estimator; final-step/checkpoint/receipt/archive admission; complete6matrix and independent saved-array regional recomputation, fail-closed verdicts.

Minimum package: locks, six fresh receipts, inherited checkpoint identities, final predictions/residual checkpoints, passive full/regional/support traces, native strain/rho secondary, compact table/decision figure, result and external Evidence review. Nontraining code success isn't scientific success. No Stage2 or coupled FEM/teacher promotion.
