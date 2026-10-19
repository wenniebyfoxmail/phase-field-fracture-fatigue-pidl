# S09-E017 first-principles factorised-head pilot card (draft)

Status: `CORE_AND_STATIC_INTEGRATION_CODE_READY__FINAL_RUN_PACKAGE_NOT_IMPLEMENTED__NO_EXECUTION`
Owner: Mac-PIDL
Date: 2026-10-19

## Decision question

Under one frozen input information set, trunk representation and optimiser
contract, how do a direct damage readout, a factorised amplitude-only readout
and a factorised amplitude-plus-shape readout differ over one fixed short
budget? In particular, does allowing spatial shape to adapt add a measurable
gain over keeping the B25 shape fixed?

E016 answers only the prerequisite question. Its independent result review
returned `E016_RESULT_REVIEW_PASS`. On all 16 exposed cycles the
capacity-aware hazard increment has a finite scalar amplitude `A`, a
weighted-normalised shape `S`, and a stable float64 round trip. It does not say
that B25 learned either quantity. The measured baseline is poor: median
B25/FEM hazard-amplitude ratio `0.01257`, median shape half-L1 `0.99984`, median
shape cosine `3.998e-5`, and median FEM-support capture `0.00151`.

## Operator mapping and physics boundary

The learned transition remains

```text
G_theta:
  (d_s00, H_s00, alpha_bar_s00, q_prev_s00, f_s00,
   prescribed load path s00...s05, mesh, material and boundary data)
    ->
  (d_s04, H_s04, alpha_bar_s04, q_prev_s04, f_s04, u_s04).
```

The proposed damage branch predicts the peak increment through

```text
A_hat >= 0
sum_i wbar_i S_hat_i = 1, S_hat_i >= 0
S_hat_i = 0 whenever c_i = 0
Delta d_hat_i = c_i * (1 - exp(-A_hat * S_hat_i))
c_i = clip(1 - d_pre_i, 0, 1).
```

This enforces irreversibility and `d_peak <= 1` by construction. The only PINO
physics term in this pilot is the existing native-Q4 AMOR mechanical
equilibrium residual on free displacement DOFs, with `beta=0.25`. It does not
include damage stationarity, Kuhn-Tucker/history complementarity, fatigue-law
closure, or the full incremental variational inequality. A positive result is
therefore a limited equilibrium-informed operator result on exposed
development data, not a complete fracture PINO result.

## Mechanism and competing explanations

The intervention is justified by one binding observation: B25 is wrong in both
amplitude and localisation, while E016 shows that those targets can be
represented separately without numerical pathology. Four explanations remain
live:

1. **Coupled-head interference**: a direct nodewise damage head entangles the
   global amount and spatial allocation, so gradients that repair amplitude
   damage localisation and vice versa.
2. **Objective conflict**: the representation is adequate, but reconstruction,
   amplitude, shape and equilibrium gradients point in incompatible directions.
3. **State/trunk insufficiency**: the supplied s00 state and load path do not
   encode the process-zone information required to locate new damage.
4. **Optimisation scale/initialisation**: a useful factorised head exists but a
   short update budget or unmatched zero-step state hides it.

The pilot can compare the three readouts and expose gradient conflicts. It
cannot uniquely identify those four causes. A short negative result remains
compatible with inadequate optimisation, an unsuitable objective or missing
state/trunk information; it is not proof that the trunk lacks information.

## Three matched arms

All arms use the same 16 exposed cycles, s00-to-s04 mapping, shared packet,
normalisation, beta `0.25`, optimiser family, update schedule, evaluation
points, seed, shared trunk and total update budget. P0 freezes the shared trunk
and every non-damage head in all three arms; only the stated damage-head
parameters may update. This makes P0 a head-level mechanism test rather than a
claim about full-operator capacity. No arm receives a target support mask as an
input or output correction.

1. `D_DIRECT`: the existing direct bounded damage-increment head. Its predicted
   field is differentiably factorised after the forward pass. The resulting
   decoded-field amplitude and shape are used by the same common objectives and
   diagnostics as the full factorised arm, with the exact zero/saturation rules
   below. This is a readout comparison, not a change of supervision.
2. `F_AMP`: the capacity-aware `A x S` decoder with an explicit amplitude
   objective, reconstruction and equilibrium objectives. Its `S` is the
   detached, frozen B25 step-0 shape mapping for each input; no shared or shape
   parameter capable of changing `S` may update. Shape metrics and the
   withheld shape-gradient are logged, but not applied. This is the true
   amplitude-only ablation.
3. `F_AMP_SHAPE`: the same factorised decoder with explicit amplitude and
   full-field shape objectives, plus the same reconstruction and equilibrium
   objectives.

The two factorised arms use the same amplitude residual head. At update 0 it is
zero-initialised around the factorised B25 amplitude, so `A_hat=A_B25`. `F_AMP`
uses exactly `S_B25`. For `F_AMP_SHAPE`, freeze `epsilon=1e-6` and define a
target-independent capacity-supported seed

```text
U_i = 1[c_i > 0] / sum_j wbar_j 1[c_j > 0]
S_0 = (1 - epsilon) S_B25 + epsilon U.
```

Thus `U` is strictly positive on every node with remaining capacity, zero where
`c_i=0`, and weighted-normalised. Parameterise the learnable shape as

```text
S_i(z) = 1[c_i>0] S_0_i exp(z_i)
         / sum_j wbar_j 1[c_j>0] S_0_j exp(z_j),  z_i=0 at update 0.
```

This gives every capacity-positive node finite nonzero mass-reallocation
sensitivity, including nodes where B25 increment is zero. Implementation review
must prove `TV_wbar(S_0,S_B25)<=epsilon`, verify nonzero sensitivities, and
bound the decoded-field step-0 difference. Endpoint comparisons are never used
alone: for every primary metric report the initial inter-arm difference, final
inter-arm difference and difference between each arm's update-0-to-64 change.
The full intervention is described as a factorised head with a predeclared
mass-entry seed; it is not called a pure architecture effect.

## Multi-objective update

Keep four loss groups separate. All trainable common losses use observables
recomputed from the decoded increment field with the frozen E016 transform:
`effective_hazard_amplitude` and, only when it is nonzero,
`effective_hazard_shape`. Log the factorised head's latent `head_amplitude` and
conditional latent shape separately. Do not substitute a latent improvement
for decoded-field evidence. Require zero shape mass where `c=0`; report any
remaining head/effective amplitude difference caused by the frozen `q_max`
saturation. If decoded-field amplitude is zero, its common shape is undefined
and `L_S` is inactive for that cycle while `L_A` and `L_R` remain active.

The active-loss matrix is frozen as follows:

| Arm | `L_A` | `L_S` | `L_R` | `L_P` |
|---|---:|---:|---:|---:|
| `D_DIRECT` | train | train through differentiable field factorisation | train | train |
| `F_AMP` | train | diagnostic only; excluded from projection/update | train | train |
| `F_AMP_SHAPE` | train | train | train | train |

Loss definitions are:

- `L_A`: let `z=log1p(effective_hazard_amplitude/A_scale)`. Use equal internal
  weights for mean squared `z-z_target` regression and mean squared pair
  contrast regression. For every frozen pair `(g,s)`, the target is the signed
  FEM contrast `(z_g^*-z_s^*)`; ties therefore target zero. Pair identities are
  unchanged, but the three reverse FEM hazard orderings remain reverse rather
  than inheriting growth-first physical-increment labels;
- `L_S`: support-free weighted shape half-L1 and cosine terms on nonzero FEM
  events; target-support capture, spill and centroid remain evaluation
  diagnostics rather than hidden correction masks;
- `L_R`: bounded increment-field reconstruction, scaled per cycle without
  changing the frozen target;
- `L_P`: native-Q4 free-DOF equilibrium residual. Its external gradient weight
  is `beta=0.25`.

Use the following unique PCGrad contract. For each arm and active group `k`,
compute the raw gradient `g_k` at update 0 and freeze
`scale_k=||g_k||_2` when that norm exceeds `1e-12`, otherwise `scale_k=1` and
record the zero-scale case. At every update compute
`h_k = weight_k * g_k / scale_k`, with weights `(1,1,1,0.25)` for
`(A,S,R,P)`. Weighting occurs after scale normalisation, so beta cannot be
cancelled. Starting from working copy `p_k=h_k`, project `p_k` against the
unmodified `h_j` when `p_k dot h_j < 0`, using a permutation generated from
the frozen seed plus update index. Skip a projection denominator only when
`||h_j||<=1e-12` and record it. Aggregate by the arithmetic mean over the
arm's active groups, then apply exactly one global norm clip at `1.0`.
`F_AMP` uses three active groups in that mean; its withheld shape gradient is
logged but never enters a projection or denominator.

All arms use a fresh empty-state AdamW on their trainable damage-head
parameters only: learning rate `3e-4`, betas `(0.9,0.999)`, epsilon `1e-8`,
weight decay `0`, float64, with no scheduler. Persist raw and scaled group
norms, weights, all pairwise cosines/conflicts, seeded permutations, projected
vectors, aggregate pre/post clip norms, and each raw group's dot product with
the realised update. This is multi-objective optimisation evidence, not proof
that PCGrad caused a result or is optimal.

Hazard-amplitude ranking and weighted-mean absolute-increment ranking remain
separate observables. E016 showed their FEM scores differ (`44` versus `50`),
so they must not be substituted for one another in the loss or verdict.

## Bounded grouped mechanical validation (P0)

P0 uses all 16 representative cycles on every update. It is not a single-cycle
or selected-easy-cycle test. Proposed budget: 64 updates per arm, 192 total,
with evaluations at `0, 1, 4, 16, 32, 64`. No budget transfers, retries,
coefficient sweeps, fresh holdout, new FEM, checkpoint search or A25 node-field
export are allowed. The current packet contains no target zero event; the
strict zero-event branch therefore receives synthetic unit/integration tests
but cannot be reported as a real-data zero-event result.

This is a small predeclared signal probe; static design cannot establish that
64 updates are sufficient to identify a failure cause. Fairness means matched
updates and data exposure. Because head sizes and active groups differ, persist
per-arm wall time, peak memory and forward/backward counts; do not claim equal
FLOPs and do not transfer unused budget.

At every evaluation, report one vector rather than a conjunctive headline:

1. **Amplitude**: median absolute hazard log-ratio and hazard 25-pair `2W+T`;
2. **Spatial shape**: weighted half-L1, cosine, support capture/spill and
   centroid offset over all applicable cycles;
3. **Field reconstruction**: weighted increment error and maximum-increment
   error, including every existing representative cycle;
4. **Limited physics**: equilibrium residual and the existing protected
   `G/F/L_judge` diagnostics;
5. **Constraints and numerics**: nonfinite counts, irreversibility/upper-bound
   violations, zero/nonzero semantics and factorisation round-trip;
6. **Gradient geometry**: group norms, pairwise conflicts and realised
   per-group descent/ascent.

## Graded interpretation and route choice

The pilot has only one hard validity floor: complete identities and scheduled
evidence, finite values, no hard constraint violation, and readable receipts.
The performance decision uses update 64 only; intermediate points remain
descriptive and cannot be selected post hoc.

Convert each primary metric to an error orientation where lower is better:
amplitude uses the median absolute scaled-log error
`abs(log1p(A_eff/A_scale)-log1p(A_FEM/A_scale))` plus exact mismatch count
against the 25 FEM hazard pair outcomes. This decision quantity is finite when
`A_eff=0`; retain the ordinary absolute hazard log-ratio only as a raw
diagnostic with a fixed `predicted_zero` NA reason, and do not let that expected
diagnostic NA trigger `INVALID_EXECUTION`. Shape uses half-L1, `1-cosine`,
`1-capture`, spill and centroid offset; reconstruction and limited physics use
their reported nonnegative errors. For a continuous metric, values tie when
their difference is no larger than
`max(1e-12, 64*eps_float64*max(1,abs(x),abs(y)))`; discrete pair mismatches tie
only exactly.

The current 16-cycle packet has a nonzero FEM hazard amplitude on every cycle.
If a valid prediction has zero decoded amplitude on one of those cycles, its
effective shape remains mathematically undefined. Do not invent a shape or
invalidate the execution. Instead add the discrete lower-is-better component
`predicted_shape_undefined_count` and, for decision aggregation only, assign
that cycle the predeclared maximum error vector `(1,1,1,1,1)` for half-L1,
`1-cosine`, `1-capture`, spill and mesh-diagonal-normalised centroid offset.
Persist the raw values as `NA`, the imputation flag and the decision values so
the penalty cannot be mistaken for an observed shape. A future target-zero
cycle would be excluded from shape aggregation by target semantics and would
require a new card; it is not silently handled here.

Let `E_k^a(t)` be arm `a`'s lower-is-better vector for group `k` in
`{A,S,R,P}` at update `t`, including the discrete shape-undefined count in
`S`. Define `Delta_k^a = E_k^a(64)-E_k^a(0)`, terminal gap
`T_k^{a,b}=E_k^a(64)-E_k^b(64)`, and change gap
`C_k^{a,b}=Delta_k^a-Delta_k^b`. A vector `x` Pareto-improves zero when at
least one component is below zero beyond its tie rule and none is above zero;
`x` Pareto-dominates `y` when `x-y` Pareto-improves zero. `x` is no worse than
`y` when no component of `x-y` is positive beyond tie. Pareto-worsening is the
reverse rule. Every arm reports `E(0)`, `E(64)`, `Delta`, every terminal gap
and every change gap; the flags below state exactly which quantities vote.

Profiles are deterministic multi-label flags, except `INVALID_EXECUTION`,
which is exclusive:

- `VALID_FACTORISATION_SIGNAL`: `Delta_A^FAS` and `Delta_S^FAS` each
  Pareto-improve zero; concatenated `Delta_(A,S,R)^FAS` Pareto-dominates
  `Delta_(A,S,R)^D`; terminal `E_(A,S,R)^FAS(64)` is no worse than
  `E_(A,S,R)^D(64)`; and both `Delta_P^FAS` and `E_P^FAS(64)` are no worse
  than the corresponding `D_DIRECT` quantities. Here `FAS=F_AMP_SHAPE` and
  `D=D_DIRECT`.
- `VALID_SHAPE_OBJECTIVE_SIGNAL`: `Delta_S^FAS` Pareto-dominates
  `Delta_S^FA`, terminal `E_S^FAS(64)` is no worse than `E_S^FA(64)`, and
  both the amplitude change and terminal amplitude of `FAS` are no worse than
  `FA`. Here `FA=F_AMP`.
- `VALID_AMPLITUDE_ONLY_SIGNAL`: `Delta_A^FA` Pareto-improves zero and
  Pareto-dominates `Delta_A^FAS`, while terminal `E_A^FA(64)` is no worse than
  `E_A^FAS(64)`. Gradient conflicts may be reported as associated geometry,
  never as the proven cause.
- `VALID_NO_HEAD_SEPARATION`: for each factorised arm `a` in `{FA,FAS}`, it is
  false that both (i) `Delta_(A,S,R)^a` Pareto-dominates
  `Delta_(A,S,R)^D` and (ii) terminal `E_(A,S,R)^a(64)` is no worse than
  `E_(A,S,R)^D(64)`. This means no predeclared separation signal was observed
  within 64 updates; it does not imply state/trunk insufficiency.
- `VALID_MIXED_TRADEOFF`: at least one arm both improves and worsens primary
  components in its concatenated `Delta_(A,S,R,P)`, or at least one pair of
  valid arms has a concatenated change-gap vector with at least one component
  strictly below zero and at least one component strictly above zero under the
  frozen component comparator. This is genuine incomparability and excludes
  all-tie change vectors. Terminal gaps are reported but do not vote for this
  descriptive flag. Preserve the Pareto evidence and do not relabel it as
  failure.
- `INVALID_EXECUTION`: identity, evidence, finite-value or hard-constraint
  failure. Repair implementation only; do not interpret optimisation.

No fixed scientific-success threshold is introduced at P0. Directional
changes, per-cycle distributions and Pareto relations are reported exactly.
Only `VALID_FACTORISATION_SIGNAL` or `VALID_SHAPE_OBJECTIVE_SIGNAL` may motivate
a separately reviewed longer exposed-development card; neither automatically
earns it. Fresh holdout or rollout still requires a new approved card.

## Evidence and current authority

Required outputs are per-update/per-cycle CSVs, loss and gradient-component
logs, three-arm field panels on one shared physical colour scale, amplitude and
shape trajectories, hard-constraint audit, checkpoints, exact config, and a
signed completion receipt. The E016 decision, authoritative table, receipt and
figure are the design inputs.

The isolated numerical core received `E017_CORE_CODE_READY_PASS` at exact
commit `5ac6b7955b56309ac8ff2fda50b16b2e1669110a`.  The static
runner/config/evidence integration received
`E017_RUNNER_INTEGRATION_CODE_READY_PASS` at exact commit
`3a5a2020c7b16555e9ecd9ec19377bf87a52d5c5`.  Current authority extends only
to preparation of one final, separately reviewable run package.  It does not
authorise scientific packet access, model forward, autograd, optimiser
construction or mutation, GPU/SSH work, training, new data or holdout access.
