---
storyline_id: S09
experiment_id: S09-E014
protocol_revision: v1-common-global-primary-nullspace-local-secondary
status: design-draft-awaiting-independent-review
primary_storyline: S09
related_experiments: [S09-E010, S09-E011, S09-E012, S09-E013]
---

# One shared global-primary direction with a constrained local secondary

## Mechanism question

From the frozen E010 B25 model and AdamW state, can one **shared** parameter
direction, built from an all-25-pair global-ranking primary and an all-25-pair
local-support secondary constrained to the primary nullspace, produce a
one-step local-ranking gain over the matching common-global control without
erasing the global-ranking signal?

The same parameter direction must be cross-evaluated on all 25 pairs.  This is
the discriminator missing from E013, whose zero-step directions were
pair-specific.

## Fixed mapping and physics

The operator remains

`G_theta: (d_s00, H_s00, alpha_bar_s00, q_prev_s00, f_s00, prescribed s00..s05 load path, mesh/material/BC data) -> (d_s04, H_s04, alpha_bar_s04, q_prev_s04, f_s04, u_s04)`.

Architecture, information set, projection rules, clip, optimiser state,
development packet, evaluator, and `beta=0.25` remain frozen.  The physics term
is the native-Q4 AMOR free-displacement equilibrium residual.  It is not full
damage stationarity, history complementarity, or the incremental variational
inequality.

## Frozen assets

| asset | identity |
|---|---|
| 16-cycle development packet | manifest `1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6` |
| B25 update-500 checkpoint | SHA256 `24bbea271fe3c2df79913f552dde863e495d33df963e0db9586b4920904dcf05` |
| B25 model state | `4d353f6ed1f0c3ce097d15ec61b078c34554e794ee264f44fcc0f5e8aaab684f` |
| B25 AdamW state | `c7a4b497e6d51089fc386c0868c7a33a867f21f60d4c6d3753788016b08b1e64` |
| pair set | `{1,58,60,69,70} x {3,4,71,72,73}` |
| rank normaliser / temperature / coefficient | `D=1.6864539921617467e-4`, `tau=.01`, `gamma=4096` |

No fresh holdout may be opened.

## One unique direction construction

At the common B25 state, define the six base losses as the mean of each
per-cycle loss across all 16 development cycles:

`L_D, L_S, L_A, L_U, L_H, L_P`.

For the fixed 25 pairs, define

`L_RG = mean_p softplus(-m_global,p/(D*tau))`,

`L_RL = mean_p softplus(-m_local,p/(D*tau))`.

Compute the flattened gradients once at the shared B25 state.  Apply the
existing B25 balancing to the six base gradients.  Let `a` be the balanced
`L_D` anchor and

`b = q_D + q_S + q_A + q_U + q_H + 0.25 q_P`.

Construct the common global primary component `q_G` by norm-matching
`grad(L_RG)` to `a`, removing only its negative projection on `a`, exactly as
the existing ranking merge does.

Construct a balanced local vector

`l_0 = ||a|| grad(L_RL) / ||grad(L_RL)||`.

The unique local secondary is the orthogonal projection of `l_0` onto the
orthogonal complement of `span(a, grad(L_RG))`:

`q_L = (I - A^T (A A^T)^+ A) l_0`,

where the rows of `A` are `a` and `grad(L_RG)`, and the Moore-Penrose inverse
uses fixed relative tolerance `1e-12`.  This removes the secondary's direct
first-order component along both the damage anchor and aggregate global-ranking
gradient.  If `||q_L|| <= NORM_EPSILON`, record
`NO_COMMON_NULLSPACE_SECONDARY` and do not take a step.

The two compared common directions are

`g_control = clip(b + 4096 q_G)`,

`g_candidate = clip(b + 4096 q_G + 4096 q_L)`.

Each direction is converted through a clone of the same frozen AdamW state to
one parameter displacement.  There is no scalar sweep, per-pair direction, or
adaptive coefficient.

## Why one new computation is required

E012 persisted norms, cosines, group energies, and pairwise scalar derivatives,
but not the full flattened gradient vectors.  E013 persisted pair-specific
inner products and displacement norms, not shared vectors.  They are
insufficient to reconstruct `grad(L_RG)`, `grad(L_RL)`, `q_G`, or `q_L`.

E014 therefore requires one new authorised B25 forward/autograd collection on
the already exposed 16-cycle packet.  It does not require new FEM data or a
holdout.

## Zero-step cross-effect audit

Before any optimiser step, use the **same** `delta_control` or
`delta_candidate` for all 25 pair Jacobians and record:

- global and local margin change for every pair;
- old eight global-loss directional improvements and predicted crossings;
- old 17 global-win directional regressions and predicted crossings;
- local-loss improvements and local-win regressions under the corrected local
  cohort definition;
- aggregate `L_D`, `L_P`, and all six base-loss changes;
- direction, component, model, optimiser, and parameter-order hashes.

These are diagnostics and tier evidence, not an all-8/all-17 admission gate.

## Minimal finite-step validation

If both common directions are finite, identity-valid, and the candidate has a
nonzero `q_L`, clone the B25 model/AdamW state and take exactly one AdamW step
per arm.  Strictly reload each step-1 checkpoint before evaluation.

Save all 16 cycle fields at step 0 and step 1.  Render `Delta d` for FEM target,
B25 step 0, common-global control step 1, and constrained candidate step 1 with
one shared physical colour scale.  The numerical table must include weighted
amplitude, local-support contrast, support/background means, `G`, `F`, `L_P`,
`L_judge`, hard constraints, and global/local pair scores.

## Staged result definition

The experiment does not use an all-or-nothing eight-pair/17-pair gate.

1. `EXECUTION_INVALID`: identity, common-direction, finite, reload, or hard
   constraint contract fails.
2. `NO_COMMON_NULLSPACE_SECONDARY`: the unique constrained `q_L` is at or
   below numerical epsilon.  This rejects this construction, not the operator.
3. `COMMON_SECONDARY_AVAILABLE`: `q_L` is finite/nonzero and produces a
   candidate displacement distinct from control.
4. `ONE_STEP_LOCAL_COMPONENT_SIGNAL`: after strict step-1 reload, candidate
   local pair score `2W+T` exceeds control by at least one point.
5. `BALANCED_ONE_STEP_SIGNAL`: level 4 plus candidate global pair score no lower
   than control, no hard violations, and contemporaneous candidate/control
   ratios for `G`, `F`, `L_P`, and `L_judge` each no greater than 1.10.

Continuous margin changes and fields remain visible when no discrete pair
score changes.  They may explain a result but cannot promote it to level 4.

## Budget and stop rules

- Producer: Taobo GPU5, exact UUID required.
- GPU budget: at most 0.5 GPU-hour.
- Absolute wall cap: 30 minutes, including zero-step and step-1 evaluation.
- Optimiser cap: one step per arm, two total.
- One run, no retry, restart, coefficient scan, unused-budget transfer, or
  alternate GPU.
- First failure stops the run and preserves partial evidence.
- Fresh holdout remains sealed.

## Claim boundary

A positive result supports only a common-direction, one-step component signal
on the exposed development trajectory.  A negative result rejects only this
nullspace-projected secondary construction.  Neither result establishes
finite-training repair, rollout stability, unseen-cycle generalisation,
physical-teacher truth, real-road validity, or a complete fracture PINO.
