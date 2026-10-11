---
storyline_id: S09
experiment_id: S09-E006
protocol_revision: v2-gradient-balanced-pareto-rescue
status: complete
primary_storyline: S09
related_experiments: [S09-E004, S09-E005]
---

# Gradient-balanced Pareto rescue for the fixed-damage equilibrium operator

## v2 amendment before execution

The first independent design review returned `DESIGN_READY FAIL` before any
training.  Revision v2 retains the arms, beta values and 50%/10% criterion but
freezes the global projection scope, degeneracy policy, per-update state
semantics, metric implementation identity, replay comparison and validity
precedence.  No result existed when this amendment was made.

## One bounded question

Can a data-anchored, gradient-balanced update reduce the development-set
fixed-damage equilibrium residual by a practically material amount without
allowing a material loss of displacement accuracy relative to the matched
data-only trajectory?

This is a controlled C0/C1 optimisation-capability experiment in the synthetic
FEM-export evidence domain.  It does not test damage evolution, temporal
forecasting, independent generalisation or road validity.

## Frozen operator, evidence and information set

- Mapping:
  `G_theta: (d_peak(.), Umax) -> u_peak(.)` on the fixed native Q4 mesh.
- Physics: the unchanged free-DOF, fixed-damage AMOR mechanical-equilibrium
  residual used in S09-E004.
- Training packet SHA-256:
  `b37a63ccb0e7129ecc3fbe01fc356c93fccc1877b5f34e68fe93265f335109ed`.
- Common step-300 model/AdamW checkpoint SHA-256:
  `1fc1695a87c41cd4a373fa31535dc99be7d91ad01af9a1e11a2986d83af8029e`.
- E004 training sequence SHA-256:
  `ee1884ae1a81813334641faaacc0e44151d23cb4f36e35948ec656fd20c976f5`;
  only its final 700 matched-update indices are used.
- Immutable E004 reference metrics SHA-256:
  `202be98d2be46c702196a7f05d4571789097a297aea3f99870dd66379ae6e62f`.
- Immutable evaluator and objective implementation: execution commit
  `11fd75d70b18165d6214d50c90adc9c9c9b522a5`, runner
  `SENS_tensile/run_s09_equilibrium_operator.py`, and its imported operator,
  physics and Q4 quadrature modules.  The E006 runner must fail if these paths
  differ from that commit.
- Development units: the same frozen U0.12 c76, c82 and c83 states.  They have
  already been used for method development and cannot support an independent
  generalisation claim.
- One seed and one producer execution on Taobo.  No arm or threshold may be
  added after results are viewed.

## Comparator and arms

All arms load independent deep copies of the exact common model and AdamW
state, use the same 700 indices in the same order, preserve the E004 learning
rate and global gradient clip, and are assessed only from their final state.

1. `data_only_replay`: exact E004 data objective and optimizer path.  It is a
   concurrent validity control and the primary comparator.
2. `balanced_beta_0p25`: data gradient plus a projected physics gradient whose
   norm is 0.25 times the data-gradient norm.
3. `balanced_beta_1p0`: data gradient plus a projected physics gradient whose
   norm equals the data-gradient norm.

For each sampled training state, let `g_d` and `g_p` be the exact E004 data and
physics gradients.  If `g_d dot g_p < 0`, replace the physics gradient by

`g_p_proj = g_p - (g_d dot g_p / ||g_d||^2) g_d`.

Otherwise `g_p_proj = g_p`.  The update direction for balance ratio `beta` is

`g = g_d + beta * ||g_d|| / ||g_p_proj|| * g_p_proj`.

This projection makes the retained physics component orthogonal to the data
gradient when the raw gradients conflict.  It is a first-order data guard, not
a finite-step trust-region guarantee.  A zero/non-finite gradient or a fully
removed physics direction fails closed for the arm rather than silently
changing the method.

The method balances parameter gradients at every update.  It does not minimise
a fixed scalar loss and no post-hoc scalar `lambda` is fitted.

All dots and norms above are global, flatten-equivalent float64 reductions over
every trainable parameter in the unchanged model.  Projection is not performed
per tensor or per layer.  Both losses use the exact E004 reductions and
normalisers.  The two gradients are computed from the same deterministic
forward graph, identical single sampled state and identical pre-update
parameters; the data gradient retains that graph and the physics gradient is
then taken before any parameter or optimizer mutation.  Independent sampling,
loss rescaling and stochastic forward changes are prohibited.  The model must
contain no dropout or batch-normalisation state.

The final combined direction is assigned once to every parameter's `.grad`,
then one unchanged E004 global `clip_grad_norm_(..., 10.0)` is applied to the
combined vector, followed by exactly one AdamW step.  The optimizer retains the
loaded common-checkpoint state, `lr=3e-4`, default E004 AdamW weight decay and
all other defaults; there is no scheduler.  Components are never clipped
separately and the optimizer step is never split.

The exact degeneracy rules use the global float64 reductions before casting
back to parameter dtype:

- a non-finite gradient component, norm, dot, projection coefficient or
  assigned direction invalidates that balanced arm;
- `||g_d|| <= 0` or `||g_p|| <= 0` invalidates that balanced arm;
- after projection, `||g_p,proj|| <= eps64 * ||g_p||`, where
  `eps64 = torch.finfo(torch.float64).eps`, invalidates that balanced arm;
- a clipped combined norm that is non-finite invalidates that balanced arm.

There is no fallback to data-only, skipped update or changed tolerance.  The
failed arm stops at that update with a machine-readable reason and cannot vote;
other arms continue from their own independent common-checkpoint copy.

## Evaluation and primary joint feasibility criterion

For each final arm and each development state, compute exactly the E004:

- displacement error relative to the affine comparator, `R_u(s)`;
- free-force RMS residual relative to affine, `R_f(s)`;
- aggregate displacement `R` from summed area-weighted numerators and
  denominators.

The immutable metric equations are:

- `R_u(s) = weighted_l2(u_pred, u_target, area) /
  weighted_l2(u_affine, u_target, area)`;
- `R_f(s) = sqrt(mean(f_pred[free]^2) / mean(f_affine[free]^2))`;
- `R = sum_s weighted_l2(u_pred, u_target, area) /
  sum_s weighted_l2(u_affine, u_target, area)`.

`weighted_l2` and the affine field are the unchanged E004 implementations.
Every denominator must be finite and strictly positive; otherwise the complete
Experiment is inadmissible.  All primary comparisons use the unrounded float
values written to JSON.

Define the residual summary as the arithmetic mean of the three `R_f(s)`
values.  A balanced arm is jointly feasible only when both clauses hold:

1. `mean_s R_f,arm(s) <= 0.50 * mean_s R_f,data(s)`; and
2. for every development state `s`,
   `R_u,arm(s) <= 1.10 * R_u,data(s)`.

The Experiment supports the bounded rescue claim if at least one of the two
predeclared balanced arms is jointly feasible.  The conjunction is necessary:
the target is a usable accuracy-equilibrium trade-off, so residual-only or
accuracy-only improvement cannot answer the question.

The 50% residual reduction is materially weaker than the 89.8% reduction
already attained by E004's accuracy-damaging physics arm, and therefore tests a
plausible retained benefit rather than exact equilibrium.  The 10% per-state
limit is a development guardrail chosen to prevent a pooled mean from hiding a
large local accuracy loss.  It is not a physical tolerance.

If both balanced arms pass, select the arm with the lower aggregate
displacement `R`; break an exact tie by lower mean residual.  This selection
rule does not change the primary existence verdict.

## Validity controls and stop rules

- Packet, checkpoint, sequence and expected commit hashes must match.
- Producer checkout must be clean, Taobo-only and explicitly GPU-bound.
- `data_only_replay` must reproduce E004's three per-state displacement ratios
  and residual ratios plus aggregate displacement `R` from the hash-bound
  E004 `metrics.json`.  Each of these seven unrounded values is compared
  independently using
  `abs(replay-reference) <= 1e-6 + 1e-5*abs(reference)`; otherwise the complete
  Experiment is inadmissible and balanced arms do not vote.  After this replay
  gate passes, primary feasibility compares balanced arms against the
  concurrent replay's unrounded values.
- All parameters must receive finite data and physics gradients.  Gradient
  assignment coverage, projection metadata, raw and clipped norms and AdamW
  step counts are recorded.
- Exactly 700 optimizer updates per arm are allowed.  Final checkpoints, final
  metrics and fields are mandatory.  Best intermediate checkpoints are
  diagnostic and cannot rescue the final criterion.
- Stop the run on a non-finite value, identity mismatch, update-count mismatch
  or data-only replay mismatch.  A balanced-arm degeneracy stops only that arm
  under the exact arm-local policy above.  Do not add a beta, retry a seed or
  change the threshold inside S09-E006 after viewing results.

Validity precedes the scientific verdict:

1. any identity, common evaluator, denominator or data-only replay failure
   makes the entire Experiment inadmissible;
2. an invalid balanced arm cannot vote, while another independently completed
   balanced arm may vote if all shared validity gates pass;
3. at least one valid balanced arm passing both clauses supports the bounded
   existence claim, even if the other balanced arm is invalid;
4. one or more valid balanced arms but none passing both clauses gives a
   negative verdict for the predeclared candidate set;
5. no valid balanced arm gives an inconclusive intervention result, not a
   negative scientific result.

Every update records arm, matched step, exact sequence index and cycle.  Every
balanced update also records raw data/physics/projected/combined norms, dot,
conflict flag, projection coefficient, clipping norm and AdamW step before and
after.  Model and optimizer state hashes are recorded at start and finish.

## Component milestones and repair map

- Residual clause passes but displacement clause fails: projection is
  insufficient as a finite-step accuracy guard; the next repair may test an
  explicit displacement trust region in a new Experiment.
- Displacement clause passes but residual clause fails: the balanced physics
  contribution is too weak or the selected direction is ineffective; use the
  recorded trajectory diagnostics before choosing a new intervention.
- Both clauses fail: discontinue this gradient-balanced formulation under the
  fixed budget and reconsider the objective/interface.
- At least one arm passes: advance only to a separately reviewed fixed-damage
  holdout test before any damage-evolution PINO work.

## Minimum evidence

- producer receipt and final metric JSON;
- per-assessment history with gradient/projection metadata;
- final checkpoints and final development fields;
- one decision figure showing both primary clauses for all three development
  states and every arm against data-only;
- analysis README, decision note, independent Evidence Ready review, dated S09
  claim-impact entry and Obsidian update.

## Blocked conclusions

No outcome may establish exact equilibrium, FEM truth, damage or fatigue
evolution, temporal forecasting, independent generalisation, superiority over
PINO alternatives, or real-road applicability.  E004's recorded failure and
E005's diagnostic scope remain unchanged.

## Execution record — 2026-10-12

Independent design and Code Ready reviews passed protocol v2 and exact commit
`ae01790c10c644657fe9a8aea2f1087505144959`.  R001 stopped at the clean-checkout
preflight before any optimizer update because audit-created caches were
untracked.  The independently authorised replacement R002 completed all three
700-update arms on Taobo.  The seven-value data-only replay gate passed and the
predeclared `beta=0.25` arm passed both joint-feasibility clauses.  The result
and claim boundaries are recorded in `decision.md`; final closure remains
conditional on independent Evidence Ready review.  The review subsequently
returned `EVIDENCE_READY PASS` after recomputing all primary and update-level
checks from the raw evidence archive.
