# S09-E017 real-head-adapter design review round 1

Date: 2026-10-20  
Reviewer: ChatGPT Pro, Haofan account  
Reviewed commit: `ad992707b4d9e0197f75b8dfc3e6dfd5acc1b51e`  
Conversation: `https://chatgpt.com/c/6ad6a261-f9ec-8328-863e-ecf482b48e65`  
Verdict: `E017_REAL_HEAD_ADAPTER_DESIGN_REVISE`

The review was static and design-only. It did not import or execute code, read
scientific assets, run a model or optimiser, use autograd, access the producer,
or train. Four blocking findings were returned.

## B1 — checkpoint conversion did not make storage isolation and bitwise fidelity compatible

A detached row could be registered as a new parameter while still aliasing the
old full output matrix's writable storage. Conversely, computing one-output and
two-output linears separately can change floating-point reduction and therefore
fail the stated bitwise-equivalence claim near `max/clamp` boundaries.

Minimum correction: use independently owned row parameters; do not retain the
old full matrix as a registered parameter; exhaustively record source-to-target
row mapping, shape, dtype, numel, trainability, buffers and aliases; reconstruct
the full three-row tensor and use the original three-output linear arithmetic
path. Build every arm independently from one pristine checkpoint and freeze all
B25 anchors before any arm update.

## B2 — the deterministic F_AMP_SHAPE seed offset was absent from the comparison contract

Zero logits return `S0`, not `S_B25`. With positive B25 amplitude and no decode
saturation, the F_AMP_SHAPE damage field therefore differs at update 0 even
though its amplitude residual is zero. Epsilon `1e-6` alone does not guarantee
that hard counts or profiles are unchanged.

Minimum correction: explicitly treat the third arm's seed offset as a planned
initial difference; record decoded update-0 metrics and B25 offsets per arm;
compute change from each arm's actual start; keep terminal comparisons; separate
checkpoint-conversion equivalence from the intentional seed-difference test.

## B3 — failure semantics did not distinguish operation, step return and committed update

An AdamW step can return and then evidence validation or persistence can fail.
The last durable record would be update `k-1` while the model has executed step
`k`. A required unreadable artifact could also prevent the failure receipt that
is supposed to report it.

Minimum correction: separately count update entered, optimiser step returned
and complete update committed. Advance `last-complete` only after validation and
durable persistence. Write a minimal independent failure receipt containing the
first reason, exact arm/update, counters, last complete state and missing or
unreadable artifacts. Define a non-self-referential receipt/inventory binding;
retrieval failure prevents `completed` without triggering retry.

## B4 — a 64-step result could not by itself support a representation-readability claim

F_AMP may improve through its scalar bias alone without using cycle-varying
features. A negative optimiser trajectory cannot exclude a better parameter in
the same affine class. The reviewed draft also compared D_DIRECT on hidden
feature `h` against factorised heads on pre-decoder feature `z`, with registered
parameter counts `w+1`, `3w+1`, and `6w+2`; the shape bias cancels under
normalisation and is a mathematical null direction.

Minimum correction: state parameter counts, the null direction and feature
coordinate difference, or remove them in the amendment. Limit a positive claim
to the specified frozen representation, anchors, adapter, data and 64-step
procedure. A negative result means only that this procedure did not reach the
profile; it does not exclude a better affine readout, nonlinear head, trunk
adaptation, holdout generalisation or operator capacity.

## Retained positive findings

Native-weighted pooling is a defensible P0 function-to-scalar readout. A
pointwise affine logit over a frozen nonlocal feature is a defensible P0
function-to-field readout. The final-row split, epsilon mass-entry seed and
reviewed numerical core can all be retained after the corrections above.
