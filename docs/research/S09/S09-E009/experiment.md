---
storyline_id: S09
experiment_id: S09-E009
protocol_revision: v3-four-arm-damage-separation-screen
status: core-code-ready-runner-integration
primary_storyline: S09
related_experiments: [S09-E006, S09-E008]
---

# Four-arm damage-separation screen for the Stage-0A state operator

## One bounded question

Under one fixed 500-update development budget, does the predeclared
damage-anchor update produce a useful relative repair of S09-E008's
cycle-independent damage template, and what is the incremental effect of adding
the current mechanical-equilibrium physics term inside that same anchor rule?

This experiment compares complete update formulations. It does not identify
grouping, symmetric projection, physics or the decoder as the unique or main
cause of the S09-E008 collapse. A negative result means only that the tested
rules did not recover the required skill within this finite budget.

## Operator and current physics

The fixed development mapping is

`G_theta: (d_s00(x), [H, alpha_bar, q_prev, f]_s00(x_gp), complete s00..s05 prescribed displacement path, frozen mesh/material/boundary data) -> (d_s04(x), [H, alpha_bar, q_prev, f]_s04(x_gp), u_s04(x))`.

It is a discrete field-to-field state operator on one fixed native mesh. The 16
examples come from one development trajectory. There is no cross-trajectory or
cross-mesh generalisation evidence and no s05 output for autonomous rollout.

The physics loss evaluates predicted peak displacement and predicted peak
damage jointly in the native-Q4 AMOR mechanical-equilibrium residual on free
displacement DOFs:

`L_P = mean_free(R_u(u_peak_pred, d_peak_pred)^2) / C_P`.

Predicted damage is not detached, so this gradient may flow through displacement,
damage and shared parameters. The objective does not enforce damage
stationarity, the fatigue-history evolution law or the full incremental
variational inequality. Damage bounds/irreversibility, alpha irreversibility,
the Carrara identity/monotonicity and peak boundary lifting remain hard output
constraints. This is a limited physics-informed state operator, not a full
fracture-evolution PINO.

## Five pre-launch gates

1. **Mechanism.** Compare one complete repair against exact replay and isolate
   the incremental effect of `L_P` within a matched anchor framework.
2. **Claim change.** A nominated `A25` advances only to a separately reviewed
   confirmatory memorisation gate. No nomination directs the next diagnostic
   from component results; it does not prove state or architecture incapacity.
3. **Cheaper diagnostic.** Completed: all 16 inputs are byte-distinct, while the
   final predicted damage fields have pairwise-correlation median 0.999537 and
   predicted growth/stagnant amplitude ratio 0.96685 versus true 181.53. These
   facts locate the symptom but do not prove state sufficiency or its cause.
4. **Minimal asset.** One decision JSON/table/figure with all four arms, every
   cycle, persistence comparison, amplitude and spatial diagnostics, objective
   trajectories, gradient/update geometry, validity and classification.
5. **Registry.** Record `decision.md`, one S09 index row, this attempt ledger,
   and the PINO Obsidian supervision note. Update the research frontier only if
   the next branch changes.

## Common evidence, state and budget

- Same verified S09-E008 packet, 16 examples, information set, architecture,
  float64 dtype, normalisers, hard constraints, evaluator and deterministic
  cycle order.
- Construct one initial model, then copy the complete parameters and buffers to
  all arms. Each arm receives its own newly constructed, empty AdamW state with
  the frozen S09-E008 hyperparameters. A common random seed alone is not enough.
- Normal completion is exactly 500 updates per arm. Total cap: 2,000 optimiser
  updates. Unused budget from a stopped/invalid/inapplicable arm cannot be
  transferred.
- Evaluate the full fixed 16-example set at updates 0, 16, 64, 128, 256, 496
  and 500. Update 500 is the only final decision checkpoint. Update 496 shows
  31 complete epochs but cannot replace update 500.
- Every scorecard component at an evaluation point is computed from that one
  fixed checkpoint over all 16 examples. Averages of training rows from
  different parameter states are prohibited as final metrics.
- Every arm's complete merged gradient receives exactly one frozen E008 global
  L2 clip with norm limit 1.0 before its one AdamW step. `R` uses the clip
  already performed inside the exact replay merger and must not be clipped
  again. `S` clips `grad(L_D+L_U+L_H)` once. `A0/A25` clip `G` once. There is
  no per-objective clipping and no additional averaging.

Five hundred updates are an informed low-cost development screen. They are not
claimed sufficient to rule out capacity or state sufficiency.

## Six atomic losses

Using the exact S09-E008 reductions and scales:

- `l_d`: projected damage MSE;
- `l_dr`: raw damage-increment MSE;
- `l_u`: projected displacement MSE;
- `l_h`: projected four-channel history MSE;
- `l_hr`: raw three-channel history-increment MSE;
- `L_P`: predicted-state mechanical-equilibrium residual.

For new arms define `L_D=l_d+l_dr`, `L_U=l_u`, and `L_H=l_h+l_hr`.
Naming `L_D` changes gradient allocation; it does not add a regime label or a
new damage-classification loss.

## Four arms

1. `R_current_pino_replay`: exact S09-E008 objectives and symmetric merger:
   `J_N=(l_d+l_u)/2+l_dr`, `J_H=l_h+l_hr`, `J_P=L_P`. Do not substitute
   `(L_D+L_U)/2`, which would halve `l_dr`.
2. `S_data_only_scalar`: one ordinary AdamW gradient of
   `L_D + L_U + L_H`; `L_P` is evaluated but does not contribute.
3. `A0_damage_anchor_beta0`: the anchor rule below with beta 0. `g_P` is still
   computed and logged from the same forward state, but contributes zero.
4. `A25_damage_anchor_beta0p25`: the identical anchor rule with beta 0.25; this
   is the only PINO repair candidate.

Interpret only these comparisons:

- `S -> A0`: effect of the complete anchor formulation versus scalar data-only;
- `A0 -> A25`: overall incremental effect of adding this physics direction;
- `R -> A25`: overall repair versus the failed formulation.

## Frozen anchor algorithm

Let `a=g_D`, `n=||a||`, `epsilon=1e-12`, and for `j in {U,H,P}`:

`b_j = n*g_j/||g_j||` if `||g_j|| > epsilon`, otherwise `b_j=0`;

`p_j = b_j - min(a^T b_j, 0)/n^2 * a`;

`G = a + p_U + p_H + beta*p_P`.

This equalises before projection and never renormalises the projected residue.
Assign `G` once, apply the one frozen global norm clip, then execute one frozen
AdamW step.

- If `n <= epsilon`, stop that arm as
  `ANCHOR_STATIONARY_OR_INAPPLICABLE`; do not change method or infer no capacity.
- A finite auxiliary gradient with norm at or below epsilon is a valid zero
  contribution. A fully projected finite direction may also become zero. Log
  both; do not fail or silently renormalise them.
- Missing objective records, nonfinite values, block/layout/order mismatch or
  incomplete assignment are execution failures.
- Log raw/scaled/projected/merged/clipped norms, dots, cosines, zero reasons,
  projection counts, parameter order and direction hashes.
- Around each optimiser step, snapshot the flattened parameters and record
  `g_D dot (-delta_theta)` plus its cosine when defined. Pre-Adam
  `g_D dot G >= ||g_D||^2` is a geometric property only; AdamW does not inherit
  a no-harm guarantee for `L_D`.

## Replay validity gate

`R` must match the archived S09-E008 run through update 500:

- exact cycle/update sequence and exactly 500 complete log rows;
- evaluation at update 0 and 500 for `L_judge`, growth MAE, persistence
  baseline, near-stagnant false growth and hard-constraint count;
- each finite scalar must satisfy
  `abs(new-reference) <= 1e-12 + 1e-9*abs(reference)`;
- update-0 reference:
  `L_judge=0.8541368615961056`, growth MAE and persistence
  `0.0005017354462152066`, false growth `0`, violations `0`;
- update-500 reference:
  `L_judge=0.6951799249831218`, growth MAE
  `0.0007363939239267219`, persistence `0.0005017354462152066`, false growth
  `0.00024147322519653153`, violations `0`.

The first 500 archived gradient-log lines have SHA256
`50c746b8f6548f53493c6556b7f7281a4b97d2340c35aad5e9d63c87f9bddfe9`.
New direction hashes are identity diagnostics, not an additional scientific
acceptance condition when every numeric tolerance above passes. Replay failure
makes cross-arm performance comparison inadmissible.

## Scorecard

At every evaluation checkpoint and especially update 500, report:

- growth MAE `G`, near-stagnant false growth `F`, and persistence baseline
  `b0=0.0005017354462152066`;
- predicted growth/stagnant amplitude ratio, AUC with win/tie/loss counts,
  amplitude Pearson and Spearman;
- per-cycle predicted/true amplitude, MAE and spatial correlation;
- predicted-field pairwise correlation distribution and median within-cycle
  predicted/target spatial correlation;
- `L_judge`, all six atomic losses and `L_D/L_U/L_H/L_P`;
- raw/projected damage errors and output saturation/projection counts;
- gradient geometry, effective contribution norms, global clipping frequency,
  and actual AdamW parameter-displacement alignment;
- finite status and every hard-constraint count.

AUC ties count one half and its 5x5 growth/stagnant comparison is reported as
win/tie/loss; the 25 pairs are not treated as independent experiments.
Constant-field correlations are JSON `null` with status `NA`.

The predicted growth/stagnant amplitude ratio has its own denominator rules.
If the stagnant-group mean is positive, report ordinary division. If both
group means are zero, report JSON `null` with
`ZERO_AMPLITUDE_BOTH_GROUPS`. If the stagnant mean is zero and the growth mean
is positive, report JSON `null` with `ZERO_STAGNANT_AMPLITUDE`. These are
descriptive states, not execution failures and not automatic nomination
failures.

The primary median spatial correlation always has the same fixed 16-cycle
support. If any cycle correlation is undefined, report the primary median as
JSON `null`/`NA`, plus the valid count and exact valid-cycle membership. A
valid-subset median may be reported separately but cannot replace the fixed
support comparison. If either candidate or replay primary median is `NA`, set
the spatial axis to `SPATIAL_COMPARISON_NA`; do not interpret it as improvement
or absence of improvement.

For any ratio against replay: if reference and candidate are both zero, ratio
is 1; if reference is zero and candidate is positive, the ratio is `null` with
status `REFERENCE_ZERO_CANDIDATE_POSITIVE` and cannot pass. Do not insert a
post-hoc epsilon or emit Infinity. Any undefined ratio used by `Q_damage`
propagates an undefined `Q_damage` state; multiplication by zero cannot convert
it into a passing value.

## Graded decision states

Validity and method applicability precede performance:

1. `EXECUTION_INVALID`: identity, replay, finite, layout, update-count or hard
   constraint failure. Performance does not vote.
2. `METHOD_INAPPLICABLE`: the predeclared anchor-stationary condition. This is
   separate from execution failure and capacity.
3. `NO_REPAIR_SIGNAL`: execution is valid and the method is applicable, but
   the complete relative-repair filter is not met and no component improvement
   exceeds the frozen numeric tolerance. This includes numeric invariance and
   all-worse outcomes and does not establish architecture incapacity.
4. `COMPONENT_SIGNAL_OR_MIXED_TRADEOFF`: at least one component improvement
   exceeds the frozen numeric tolerance but the complete relative-repair
   filter is not met. Record every gain and cost instead of a generic failure.
5. `RELATIVE_REPAIR_SIGNAL`: valid `A25` satisfies all of:
   - `Q_damage=sqrt((G_A25/G_R)*(F_A25/F_R)) <= 0.80`;
   - each component ratio `<=1.05`;
   - amplitude AUC `>=0.80`;
   - `L_P,A25/L_P,R <=1.10`;
   - `L_judge,A25/L_judge,R <=1.05`.
6. `NOMINATE_CONFIRMATORY_P1`: all relative-repair clauses plus
   `G_A25 <= b0 - tau`, where `tau=1e-12+1e-9*abs(b0)`. This nominates a new
   gate; it is not P1 success.

The original E008 capacity, growth, near-stagnant and validity clauses remain
unchanged and are reported only as references. No E009 result rewrites E008.

For component movement, define `tol(x)=1e-12+1e-9*abs(x)` from the replay
reference. A finite decrease exceeding `tol(reference)` in any listed
loss/error (`G`, `F`, `L_judge`, `L_P`, or one of the six atomic losses), or an
AUC increase exceeding the same formula, is an improvement; all opposite
movements and their magnitudes are still reported. Choose the highest applicable
performance state in this order: nomination, relative repair, component signal,
then no repair. `S` and `A0` are diagnostic arms and cannot be PINO nominees.

Spatial capability is a separate descriptive axis. Use the already frozen
`AUC >= 0.80` as the unambiguous amplitude-separation condition. If it holds
but the primary median within-cycle predicted/target correlation is defined and
does not exceed replay under the same fixed checkpoint, label the outcome
`AMPLITUDE_SEPARATION_ONLY__TEMPLATE_UNRESOLVED`. Do not nominate spatial skill
from reduced pairwise prediction correlation alone.

## Minimum evidence and stop rules

- Exact code/config/packet/producer identities, per-arm model/optimiser start
  hashes, full incremental logs and structured failure/inapplicability receipts.
- Update-500 checkpoints for every completed arm, all evaluation JSON, one
  decision table/figure, per-cycle spatial/amplitude export and `decision.md`.
- Stop the affected arm on a frozen failure; shared identity or replay failure
  invalidates all comparisons. Do not add seeds, arms, budgets, thresholds or
  choose checkpoints after viewing results.

## Blocked conclusions

No outcome establishes autonomous rollout, cross-trajectory or cross-mesh
generalisation, FEM truth, state sufficiency, architecture incapacity, unique
collapse causation, phase-field damage-equation satisfaction, full PINO
validity or real-road applicability.
