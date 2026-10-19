# S09-E017 first-principles factorised-head pilot card (draft)

Status: `DRAFT_DESIGN_ONLY__NO_TRAINING_OR_FORWARD_AUTHORISED`
Owner: Mac-PIDL
Date: 2026-10-19

## Decision question

Does the present damage decoder fail because one nodewise output must learn two
different things at once—**how much** new damage occurs and **where** its
spatial mass belongs—or because the shared state/operator does not contain the
information needed for either task?

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

The experiment must distinguish these explanations rather than merely produce
one more aggregate loss value.

## Three matched arms

All arms use the same 16 exposed cycles, s00-to-s04 mapping, shared packet,
normalisation, beta `0.25`, optimiser family, update schedule, evaluation
points, seed, shared trunk and total update budget. P0 freezes the shared trunk
and every non-damage head in all three arms; only the stated damage-head
parameters may update. This makes P0 a head-level mechanism test rather than a
claim about full-operator capacity. No arm receives a target support mask as an
input or output correction.

1. `D_DIRECT`: the existing direct bounded damage-increment head. Its predicted
   field is factorised after the forward pass so the same amplitude and shape
   diagnostics can be computed.
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
uses exactly `S_B25`. `F_AMP_SHAPE` starts from the same `S_B25` plus a
predeclared at-most-`1e-6` weighted-mass exploratory component, whose residual
shape head is the only mechanism that can move mass into nodes where B25 has
zero increment. The implementation review must prove the step-0 total-variation
bound and freeze the mass-entry formula before any run. Endpoint comparisons
alone are insufficient; every arm is also compared with its own update-0 state.
No result may be called an architecture effect if zero-step mismatch dominates
the observed change.

## Multi-objective update

Keep four loss groups separate:

- `L_A`: hazard-amplitude regression in the frozen E016 scaled-log coordinate,
  plus the existing 25 growth/stagnant hazard-amplitude pairs;
- `L_S`: support-free weighted shape half-L1 and cosine terms on nonzero FEM
  events; target-support capture, spill and centroid remain evaluation
  diagnostics rather than hidden correction masks;
- `L_R`: bounded increment-field reconstruction, scaled per cycle without
  changing the frozen target;
- `L_P`: native-Q4 free-DOF equilibrium residual with `beta=0.25`.

Use PCGrad across the applicable groups after the existing per-group
normalisation and before one global clip. Freeze the projection order seed.
Persist raw group norms, all pairwise gradient cosines, conflict counts, the
projected update, and each group's dot product with the realised update.
`F_AMP` omits `L_S` from the update, logs it, and keeps `S` bitwise frozen; the
other two arms apply all groups available to their parameterisation. This is multi-objective
optimisation evidence, not proof that PCGrad is optimal.

Hazard-amplitude ranking and weighted-mean absolute-increment ranking remain
separate observables. E016 showed their FEM scores differ (`44` versus `50`),
so they must not be substituted for one another in the loss or verdict.

## Cheapest grouped mechanical validation (P0)

P0 uses all 16 representative cycles on every update. It is not a single-cycle
or selected-easy-cycle test. Proposed budget: 64 updates per arm, 192 total,
with evaluations at `0, 1, 4, 16, 32, 64`. No budget transfers, retries,
coefficient sweeps, fresh holdout, new FEM, checkpoint search or A25 node-field
export are allowed. The current packet contains no target zero event; the
strict zero-event branch therefore receives synthetic unit/integration tests
but cannot be reported as a real-data zero-event result.

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
Performance is classified as a profile, not as all-or-nothing PASS/FAIL:

- `VALID_FACTORISATION_SIGNAL`: `F_AMP_SHAPE` improves both amplitude and shape
  relative to its own start and separates from `D_DIRECT`; reconstruction and
  limited physics remain interpretable. This earns a separately approved
  longer exposed-development run.
- `VALID_SHAPE_OBJECTIVE_SIGNAL`: `F_AMP_SHAPE` improves localisation relative
  to `F_AMP` while amplitude is comparable. Keep the full factorised head and
  refine the amplitude path without changing the information set.
- `VALID_AMPLITUDE_ONLY_SIGNAL`: `F_AMP` repairs amplitude but the full arm loses
  it when `L_S` is applied, with recorded gradient conflict. The next action is
  multi-objective update repair, not another head sweep.
- `VALID_NO_HEAD_SEPARATION`: both factorised arms remain comparable to or worse
  than `D_DIRECT` across the predeclared vector. Stop head-only tuning and test
  state/trunk sufficiency.
- `VALID_MIXED_TRADEOFF`: different components improve and worsen without a
  dominance relation. Preserve the Pareto evidence and choose the next
  intervention from the recorded conflicts; do not relabel it as failure.
- `INVALID_EXECUTION`: identity, evidence, finite-value or hard-constraint
  failure. Repair implementation only; do not interpret optimisation.

No fixed scientific-success threshold is introduced at P0. Directional
changes, per-cycle distributions and Pareto dominance are reported exactly.
Fresh holdout or rollout is considered only after a valid exposed-development
mechanism signal and a new approved card.

## Evidence and current authority

Required outputs are per-update/per-cycle CSVs, loss and gradient-component
logs, three-arm field panels on one shared physical colour scale, amplitude and
shape trajectories, hard-constraint audit, checkpoints, exact config, and a
signed completion receipt. The E016 decision, authoritative table, receipt and
figure are the design inputs.

This draft authorises only design review and local no-training implementation
planning. It does not authorise model forward, autograd, optimiser mutation,
GPU launch, SSH execution, new data access, or holdout access.
