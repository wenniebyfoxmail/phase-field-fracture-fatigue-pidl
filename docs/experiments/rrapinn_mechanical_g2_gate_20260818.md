# Mechanical residual risk G2 preregistration

Date: 2026-08-18
Status: `PASS / independently reviewed / no training authorization`

## Entry condition

G1b must pass and receive independent review. G2 may implement code before the
review completes, but it cannot be closed or authorize a producer smoke until
that review is accepted.

## Mechanism and single intervention

Candidate B changes Formal PIDL only by adding

`lambda_risk * L_ME85`

for the interior free-node mechanical equilibrium residual. Damage is detached
inside the risk residual construction. Formal energy, irreversibility penalty,
fatigue update, network, optimizer and stopping logic remain unchanged.

## Frozen utility

For nodal dual area `A_i`, fixed scale
`S_mech=E_ref*Umax/L_ref^2`, and interior mask `M`:

`r_i = ||[dE_el/du_i,dE_el/dv_i]|| / (A_i*S_mech)`.

Training threshold:

`q85 = detached area-weighted quantile_0.85(r_i, A_i)`.

Risk utility:

`L_ME85 = sum_(i in M) A_i*relu(r_i-q85) / (0.15*sum_(i in M) A_i)`.

Initial G2 forbids EMA thresholds, adaptive alpha, clipping, epoch-wise RMS
normalization, dynamic lambda, and element masks. The latter require a separately
qualified active-domain dual area and internal-boundary measure. Evaluation
remains mean/p99/CVaR95/CVaR99, not the training utility alone.

`Umax`, `E_ref`, and `L_ref` must be explicit, finite and positive config values;
there is no inferred/default physical scale.

## Risk-off equivalence gate

When the config is absent, `None`, or `enable=false`:

- no mechanical residual is constructed;
- the exact original base-loss tensor is returned;
- parameter gradients are bitwise identical;
- one optimizer update and optimizer state are bitwise identical;
- serialized model/checkpoint bytes are identical in a deterministic toy gate.
- the same check covers the actual project `fit` and
  `fit_with_early_stopping` paths with one LBFGS/RPROP update.

The opt-in argument must be appended with a default and cannot change any
existing caller.

## Risk-on unit gate

- hand-calculated weighted quantile and mean-excess cases, including unequal
  areas and ties;
- permutation and common area-rescaling invariance;
- invalid alpha, non-positive area, empty mask and non-finite input fail closed;
- mechanical residual has finite first and second-order gradients;
- direct gradient to the detached damage tensor is absent;
- top/bottom and free side-boundary nodes are excluded from the primary
  interior population;
- fixed scale is positive and independent of current residual values.
- non-finite scale/lambda values fail closed;
- float32 risk-on LBFGS and two-step RPROP fixtures remain finite; the enabled
  RPROP stopping value is detached between epochs to avoid retaining its graph.

## Implementation boundary

Permitted G2 changes:

- one opt-in helper module;
- unit tests;
- optional argument and disabled branch in `fit` and
  `fit_with_early_stopping`;
- plumbing from `model_train` without changing defaults.

No runner, Taobo command, training smoke, lambda selection or FEM evaluation is
authorized. G2 pass permits only a separately reviewed G3 producer packet.

## Decision

G2 passed 2026-08-18 after independent read-only review. The final gate covered
47 tests when the reviewer included the adjacent damage-conditioned equilibrium
and damage-state inversion regressions, plus `py_compile`, `diff --check`, and
review-time hash stability. The durable review is
`local_archive/.../rrapinn_residual_training_gate_20260818/g2_independent_review.md`.

Promotion is limited to preparing and independently reviewing G3. No producer
run or training is authorized by this decision.
