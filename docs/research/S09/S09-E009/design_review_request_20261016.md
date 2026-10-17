# S09-E009 design review request — damage-regime separation diagnostic

Date: 2026-10-16
Requested reviewer: Haofan / ChatGPT Pro
Requested first-line verdict: `DESIGN_READY_PASS` or `REVISE_AND_REREVIEW`

## Review task

Review the proposed low-cost development-only diagnostic below. Please test the
five experiment-gate questions, causal interpretability of the arms, exact
operator/physics statement, budget, multi-objective update, graded scorecard,
and advancement rule. In particular, decide whether this should remain one
three-arm experiment or be split, and whether 500 matched updates are enough.
Do not treat the failed S09-E008 P1 threshold as a threshold to relax.

## Established evidence

S09-E008 P1 executed correctly on Taobo at exact commit
`f54327490ce8c02f6c042753d36ddcd32ecc5771`, with 1,000/1,000 logged updates,
finite outputs/gradients and zero projected hard-constraint violations. Its
formal frozen capacity/growth/stagnation conjunction failed.

The model did learn some components: first-to-last 16-cycle epoch means fell
83.3% for equilibrium, 17.9% for projected nodal state, 12.0% for projected GP
history, and 22.0% for raw GP increment. Raw nodal increment improved only
0.06%. Conflicts were frequent: 584/1,000 updates had at least one projection;
719/1,000 updates underwent global clipping.

Two post-run, no-optimiser diagnostics now localise the failure:

1. `input_identifiability.json`, SHA256
   `edb83ab16d5a45463972e95595a8e2b24aae58cc7df3e29673e8d484484cb3b7`:
   all 16 input records have unique hashes. The closest pair is c72/c73,
   correctly both near-stagnant. However c1 growth and c4 near-stagnant have a
   relatively small dimensionless five-channel distance 0.0858 while their
   true mean increments differ by 0.001531. The current state may therefore
   encode the distinction subtly, but it is not an exact duplicate/label
   contradiction.
2. `spatial_collapse_final.json`, SHA256
   `fbb35ed723c66ae11f572901e5c9e78cf51c3ee0d919190785ad7f7468978c68`:
   final predicted damage-increment fields have pairwise spatial-correlation
   median 0.999537 (minimum 0.997967), while true-field pairwise median is
   0.000242. Median within-cycle predicted/target spatial correlation is
   0.004443. Predicted growth/stagnant amplitude ratio is 0.96685 versus true
   181.53; growth-vs-stagnant AUC is 0.68. This is strong evidence of an almost
   cycle-independent predicted damage template.

## Exact current operator and physics boundary

The learned development mapping is

`G_theta: (d_s00(x), [H, alpha_bar, q_prev, f]_s00(x_gp), complete s00..s05 prescribed displacement path, frozen mesh/material/boundary data) -> (d_s04(x), [H, alpha_bar, q_prev, f]_s04(x_gp), u_s04(x))`.

This is a pre-cycle-to-peak state operator on one fixed native Q4 mesh, not yet
a rollout operator. The differentiable physics loss currently enforces only
the s04 fixed-damage AMOR mechanical-equilibrium residual on free displacement
DOFs. It does **not** enforce the phase-field damage Euler equation, fatigue
history evolution law, or a full incremental variational inequality. Damage
irreversibility/bounds, alpha irreversibility, the Carrara `f(alpha_bar)`
identity/monotonicity, and peak displacement boundary lifting are hard output
constraints. Damage/history evolution is otherwise teacher-supervised.

Calling this a PINO is therefore defensible only in the limited sense of a
neural state operator trained with one differentiable physics residual and
hard physical constraints; it is not yet a full fracture-evolution PINO.

## The five gate questions

1. **Mechanism question.** Does the S09-E008 damage-template collapse mainly
   arise from the current multi-objective grouping/gradient merge, and can a
   damage-anchored update recover cycle-dependent damage amplitudes without
   losing the already learned mechanical-equilibrium signal?
2. **Claim change.** Either outcome changes only the next engineering branch.
   A positive result nominates one optimiser/objective formulation for a new
   confirmatory memorisation gate. A negative result prioritises state
   sufficiency or architecture/decoder changes. It cannot establish rollout,
   holdout generalisation, FEM truth, full phase-field closure or PINO benefit.
3. **Cheaper diagnostic.** Completed above. Exact duplicate inputs were not
   found, and the final output was confirmed to be a spatial template collapse.
4. **Minimal output asset.** One decision table/figure containing all arms'
   damage discrimination, growth/stagnant errors, equilibrium, overall
   judgement, validity, and gradient diagnostics, plus machine-readable JSON.
5. **Registry path.** `docs/research/S09/S09-E009/decision.md`, S09 index row,
   the shared research frontier only if the next branch changes, and the PINO
   Obsidian supervision note.

## Frozen common conditions proposed

- Same verified 16-example S09-E008 packet and information set.
- Same `Stage0ATransitionOperator`, float64, width/rank, seed and deterministic
  cycle order; every arm starts from the same initial model state.
- Same hard constraints and evaluator; no architecture or input changes.
- One Taobo GPU producer execution; development-only.
- Exactly 500 matched single-example updates per arm (31 complete 16-cycle
  epochs plus c1–c4), because the prior run's best scheduled overall judgement
  occurred at update 500 and later plateaued. Evaluate at 0, 16, 64, 128, 256,
  and 500. No best-checkpoint substitution.
- One global norm clip after each arm's combined gradient. No post-result seed,
  arm or threshold addition.

For all arms, split the existing scaled terms into four named blocks:

- `D`: projected damage MSE plus raw damage-increment MSE;
- `U`: projected displacement MSE;
- `H`: projected four-channel GP-history MSE plus raw three-channel GP-history
  increment MSE;
- `P`: fixed-damage s04 mechanical-equilibrium residual.

Use the exact existing normalisers, reductions, output projection and raw heads.
The split changes optimisation bookkeeping but not the evaluator.

## Proposed arms

1. `current_pino_replay`: exact S09-E008 three-objective grouping and symmetric
   median-equalised cyclic projection, truncated at 500 matched updates. It is
   the replay and causal comparator; its scheduled update-500 metrics and
   logged direction diagnostics must reproduce the prior run within frozen
   numerical tolerances or the experiment is inadmissible.
2. `data_only_scalar`: standard AdamW on the scalar `D + U + H`; no `P`. This
   tests whether this unchanged operator and information set can learn damage
   discrimination when the physics gradient and symmetric merger are absent.
3. `damage_anchor_pino_beta0p25`: treat `g_D` as the immutable anchor. Project
   each of `g_U`, `g_H`, and `g_P` against `g_D` only when its dot product with
   `g_D` is negative. Rescale retained directions to `||g_D||`; combine
   `g_D + g_U_proj_scaled + g_H_proj_scaled + 0.25*g_P_proj_scaled`, then apply
   one global clip and one unchanged AdamW step. The 0.25 physics ratio reuses
   the successful bounded value from S09-E006, but this new application still
   requires review. Zero/non-finite or fully removed required directions fail
   that arm; no silent fallback.

This design does not fully factorially separate objective splitting from
anchoring. The replay and data-only arms locate whether the current physics /
merger combination is necessary for collapse; the third arm tests the smallest
preselected repair. Please decide if that causal resolution is sufficient.

## Graded scorecard and proposed advancement rule

Report every value, trajectory and uncertainty limitation. Do not reduce the
experiment to the old P1 pass/fail conjunction.

Primary damage score for each candidate arm relative to concurrent replay:

`Q_damage = sqrt((growth_MAE_arm / growth_MAE_replay) * (stagnant_false_growth_arm / stagnant_false_growth_replay))`.

Also report each ratio separately so an apparent geometric-mean gain cannot
hide sacrifice of one regime. Report:

- growth increment MAE and near-stagnant false growth;
- predicted growth/stagnant amplitude ratio and pairwise AUC;
- amplitude Pearson/Spearman and within-cycle spatial correlation;
- `L_judge`, `D/U/H/P` trajectories and final values;
- raw-versus-projected damage errors and saturation counts;
- pairwise gradient cosines, projection counts, effective contribution norms,
  and clipping frequency;
- finite values and every hard-constraint violation.

Proposed candidate-advancement rule, intended as a directional filter rather
than scientific success:

- valid execution and zero hard-constraint violations;
- `Q_damage <= 0.80` versus replay;
- neither component ratio exceeds 1.05;
- damage amplitude AUC is at least 0.80;
- final equilibrium objective is no more than 1.10 times replay;
- final `L_judge` is no more than 1.05 times replay.

The data-only arm is diagnostic and cannot advance as the PINO candidate, but
its result distinguishes optimisation/physics interference from basic
operator capacity. If no candidate advances, retain the full component-level
result and choose the next repair from the observed bottleneck; do not call all
useful partial movement a generic failure.

## Requested reviewer checks

1. Is the mapping and limited physics statement accurate and sufficiently
   honest?
2. Are the three arms causal enough, or must split-objective data-only and
   damage-anchor-without-physics controls be added/split into another stage?
3. Is 500 matched updates defensible for this diagnostic?
4. Is the damage-anchor rule mathematically specified and safe enough to
   implement, especially with zero/fully projected gradients and global clip?
5. Does `Q_damage` plus component guards avoid masking trade-offs? Are 0.80,
   1.05, AUC 0.80, equilibrium 1.10 and `L_judge` 1.05 defensible as a low-bar
   advancement filter?
6. Which conclusions must remain blocked even if the candidate advances?
7. Return concrete amendments required before implementation.
