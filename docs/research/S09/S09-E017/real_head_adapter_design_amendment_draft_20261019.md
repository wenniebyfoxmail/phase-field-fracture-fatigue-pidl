# S09-E017 real-head-adapter design amendment (draft)

Date: 2026-10-19  
Status: `DESIGN_CANDIDATE__NO_IMPLEMENTATION__NO_EXECUTION`

## Purpose

Close final-package review blocker B1 without reopening the operator mapping,
three arms, data, physics, budget or result profiles. This document specifies a
checkpoint-preserving real damage-head adapter for independent review. It is not
implementation or execution authority.

## Frozen operator map

For each independent exposed cycle,

```text
(d_s00(x), [H, alpha_bar, q_prev, f]_s00(x_gp),
 prescribed path s00...s05, mesh, material, BC)
    ->
(d_s04(x), [H, alpha_bar, q_prev, f]_s04(x_gp), u_s04(x)).
```

The E017 intervention changes only how the nodal damage increment is read from
the frozen Stage0A representation. The shared trunk, GP/history decoder and
displacement readout remain fixed. Physics remains native-Q4 AMOR free-DOF
mechanical equilibrium with external weight `beta=0.25`.

## Proposed checkpoint-preserving feature boundary

Expose the existing tensor immediately before `Stage0ATransitionOperator`'s
joint node decoder:

```text
z_i = concat(encoded_i, local_i, coarse[cluster_i]) in R^(3*width).
```

Refactor the existing `node_decoder = Linear(3w,w) -> GELU -> Linear(w,3)`
without changing its function at load time:

```text
h_i = GELU(W0 z_i + b0)
raw_d_i  = W1[0,:] h_i + b1[0]
raw_ux_i = W1[1,:] h_i + b1[1]
raw_uy_i = W1[2,:] h_i + b1[2]
```

The strict checkpoint converter copies every tensor exactly and splits only the
last decoder row. A synthetic equivalence test must show bitwise-equal float64
`raw_d`, `raw_ux`, `raw_uy`, `d_peak`, `u_peak` and history outputs before any
update. The checkpoint loader rejects missing, unexpected, shape-mismatched or
nonfinite tensors.

## Arm-specific trainable parameters

### D_DIRECT

Train only the detached damage-row module `(W1[0,:], b1[0])`. Freeze `W0,b0`,
both displacement rows, all trunk parameters, all GP/history parameters and all
buffers. This preserves the existing direct bounded damage proposal while
making the damage parameter objects disjoint from displacement parameters.

### F_AMP

Use frozen `z_i` from the checkpointed trunk. Define the cycle representation
as the normalised native-Q4 nodal weighted mean

```text
z_bar = sum_i wbar_i z_i.
```

The amplitude residual is a single affine scalar

```text
r_A = v_A^T z_bar + b_A,
A_hat = A_B25 * exp(r_A).
```

Initialise `v_A=0`, `b_A=0`, giving exact update-0 `A_hat=A_B25`. Train only
`v_A,b_A`. Use the detached per-input `S_B25` exactly; no shape-capable
parameter is present in the optimiser.

### F_AMP_SHAPE

Use the same amplitude head definition and initialisation as F_AMP. Add a
pointwise affine shape-logit head

```text
zeta_i = v_S^T z_i + b_S,
```

with `v_S=0`, `b_S=0` at update 0. Apply the already reviewed
`learnable_shape(S0,zeta,d_pre,w)` transform, where
`S0=(1-epsilon)S_B25+epsilon*U`, `epsilon=1e-6`. Train only the two independent
head parameter sets `(v_A,b_A)` and `(v_S,b_S)`.

This affine P0 readout is intentionally small: the pilot tests whether the
frozen operator representation contains linearly readable amplitude and
localisation information. A negative result cannot establish that nonlinear or
trunk-adapted operators fail.

## Runtime and evidence obligations

A later implementation candidate must:

1. map the E017 config into the existing Stage0A runtime without weakening the
   old packet/config/hash validation;
2. enumerate all model parameters and buffers, require an exhaustive partition
   into trainable and frozen sets, bind parameter object identities to optimiser
   groups, and reject extra trainable objects;
3. compute the active A/S/R/P losses from decoded fields, collect raw gradients,
   freeze update-0 scales, replay the reviewed PCGrad order and perform exactly
   one AdamW step per scheduled update;
4. collect forward, autograd and optimiser counters at the real operation
   boundaries, assert evaluation causes no mutation, and rehash all frozen
   state after every update;
5. stream validated metrics, gradients and last-complete state at explicit
   completion boundaries; preserve the first stop reason and exact arm/update;
6. bind the completion receipt to the closed inventory digest, reread every
   artifact and verify retrieval before declaring completion;
7. include the minimal transitive internal source and frozen config dependencies
   in the next review archive.

## Required design-review questions

1. Does splitting only the final node-decoder row preserve the B25 function and
   give D_DIRECT true damage-only parameter isolation?
2. Is weighted pooling of the frozen `z_i` a defensible function-to-scalar
   amplitude readout for this P0 mechanism test?
3. Is the pointwise affine logit head a fair function-to-field shape readout,
   given the frozen nonlocal trunk and the epsilon mass-entry seed?
4. Are update-0 equivalence and inter-arm differences sufficiently controlled
   for the frozen change/terminal comparisons?
5. Do these choices keep the claim at “frozen-representation head readability”
   and avoid a full PINO or operator-capacity claim?

## Authority boundary

No source implementation, scientific-asset access, checkpoint load, model
forward, optimiser construction, autograd, producer/GPU access or training is
authorised by this draft. The amendment must receive an independent design
verdict before implementation.
