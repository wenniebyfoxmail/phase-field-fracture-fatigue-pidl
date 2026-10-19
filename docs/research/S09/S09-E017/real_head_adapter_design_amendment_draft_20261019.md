# S09-E017 real-head-adapter design amendment (draft)

Date: 2026-10-19  
Status: `DESIGN_READY__NO_IMPLEMENTATION__NO_EXECUTION`

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
joint node decoder and the existing frozen hidden feature:

```text
z_i = concat(encoded_i, local_i, coarse[cluster_i]) in R^(3*width).
h_i = GELU(W0 z_i + b0) in R^width.
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
last decoder row into three independently owned parameter/buffer objects. It
does not retain the old full matrix as a registered parameter and rejects any
writable storage overlap. At forward time, concatenate the three rows and three
biases in the original order and apply one three-output `F.linear` call with the
same float64 dtype, contiguous layout and arithmetic path as the old decoder.

The conversion manifest exhaustively records every source and target key, row
mapping, shape, dtype, numel, trainability, buffer status, storage identity and
alias relation, including the zero initialisation of new factorised heads. A
synthetic equivalence test must show bitwise-equal float64 `raw_d`, `raw_ux`,
`raw_uy`, `d_peak`, `u_peak` and history outputs before any update, including
inputs on both sides of the `max/clamp` branch boundaries. The loader rejects
missing, unexpected, shape-mismatched, nonfinite or aliased tensors.

## Arm-specific trainable parameters

### D_DIRECT

Train only the independently owned damage-row module `(W1[0,:], b1[0])`. Freeze `W0,b0`,
both displacement rows, all trunk parameters, all GP/history parameters and all
buffers. This preserves the existing direct bounded damage proposal while
making the damage parameter objects disjoint from displacement parameters.

### F_AMP

Use the same frozen `h_i` consumed by the old last decoder layer. Define the
cycle representation
as the normalised native-Q4 nodal weighted mean

```text
h_bar = sum_i wbar_i h_i.
```

The amplitude residual is a single affine scalar

```text
r_A = v_A^T h_bar + b_A,
A_hat = A_B25 * exp(r_A).
```

Initialise `v_A=0`, `b_A=0`, giving exact update-0 `A_hat=A_B25`. Train only
`v_A,b_A`. Use the detached per-input `S_B25` exactly; no shape-capable
parameter is present in the optimiser.

### F_AMP_SHAPE

Use the same amplitude head definition and initialisation as F_AMP. Add a
pointwise linear shape-logit head without a bias, because a spatially constant
logit cancels exactly under weighted normalisation:

```text
zeta_i = v_S^T h_i,
```

with `v_S=0` at update 0. Apply the already reviewed
`learnable_shape(S0,zeta,d_pre,w)` transform, where
`S0=(1-epsilon)S_B25+epsilon*U`, `epsilon=1e-6`. Train only the two independent
head parameter sets `(v_A,b_A)` and `v_S`.

This affine P0 readout is intentionally small. `D_DIRECT` and `F_AMP` each have
`width+1` trainable scalars on the same frozen `h_i` coordinate; the full
factorised arm has `2*width+1`, because it adds one spatial direction. The pilot
compares the behaviour of these specified readouts under one fixed procedure.
It does not, by result alone, establish general linear readability or operator
capacity.

Every arm is created independently from the same pristine checkpoint before
any update. B25 amplitude and shape anchors for all 16 cycles are computed once
from that pristine state and then frozen; a completed earlier arm cannot change
the anchors or starting state of a later arm.

F_AMP_SHAPE intentionally starts from `S0`, not exactly `S_B25`. Its decoded
update-0 field can therefore differ from the other two arms even when the
amplitude residual and logits are zero. Record every arm's decoded update-0
metrics and its offset from B25. Compute update-0-to-64 change from each arm's
own actual start, retain the frozen terminal comparisons, and keep checkpoint
conversion equivalence separate from the required nonzero epsilon-seed test.

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
5. keep three monotone update counters: operation entered, optimiser step
   returned and complete update committed. Validate and durably persist all
   required records before advancing the last-complete boundary; otherwise
   retain the prior complete state;
6. on any failure, use an independent minimal writer to preserve the first
   reason, exact arm/update, all three counters, last-complete state and every
   missing or unreadable artifact. A bad artifact must not prevent the failure
   receipt or other writable evidence from closing;
7. bind receipt and inventory without a self-reference cycle, reread every
   available artifact and verify retrieval before declaring completion.
   Retrieval failure prevents `completed` and does not trigger retry;
8. include the minimal transitive internal source and frozen config dependencies
   in the next review archive.

The full ordered trainable-parameter vector is fixed before update 0 and used
without reordering for raw gradients, PCGrad, clipping and optimiser groups.
`D_DIRECT` contains only the independent damage row and bias; `F_AMP` contains
only `v_A,b_A`; `F_AMP_SHAPE` contains only `v_A,b_A,v_S`. Each arm has a fresh
empty AdamW state. Log `||v_A||`, the per-cycle variance of `v_A^T h_bar`, and
the nonconstant spatial variance of `v_S^T h_i` so a bias-only amplitude shift
is not misdescribed as use of cycle-varying features.

## Required design-review questions

1. Does splitting only the final node-decoder row preserve the B25 function and
   give D_DIRECT true damage-only parameter isolation?
2. Is weighted pooling of the frozen `h_i` a defensible function-to-scalar
   amplitude readout for this P0 mechanism test?
3. Is the pointwise linear logit head a fair function-to-field shape readout,
   given the frozen nonlocal trunk and the epsilon mass-entry seed?
4. Are update-0 equivalence and inter-arm differences sufficiently controlled
   for the frozen change/terminal comparisons?
5. Do these choices keep the claim at the behaviour of this frozen
   representation, adapter and 64-update procedure, and avoid a general
   readability, full PINO or operator-capacity claim?

## Result claim boundary

A positive profile supports only this statement: the specified frozen
representation, pristine B25 anchors, adapter, 16 exposed cycles and fixed
64-update procedure produced the reported changes. Evidence of cycle-varying
amplitude use additionally requires nonzero `v_A` and nonzero across-cycle
variance of `v_A^T h_bar`; a bias-only gain is reported as global calibration.

A negative profile means only that this procedure did not reach that profile
within its budget. It does not exclude a better point in the same affine class,
a nonlinear head, trunk adaptation, holdout generalisation, full operator
capacity, or a more complete phase-field physics closure.

## Authority boundary

No source implementation, scientific-asset access, checkpoint load, model
forward, optimiser construction, autograd, producer/GPU access or training is
authorised by this draft. The amendment must receive an independent design
verdict before implementation.

## Independent review closure

ChatGPT Pro on the Haofan account returned
`E017_REAL_HEAD_ADAPTER_DESIGN_READY_PASS` for exact commit
`06bf5fef693be5321ce7daf9d2384b8fa3953fde`. The review closed round-1 B1–B4
in the static design scope. The next admissible action is a disabled local
implementation candidate with synthetic and no-science tests; all execution
prohibitions above remain in force.
