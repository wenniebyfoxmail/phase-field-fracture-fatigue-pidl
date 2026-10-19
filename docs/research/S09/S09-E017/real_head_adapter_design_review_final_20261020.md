# S09-E017 real-head-adapter design review closure

Date: 2026-10-20  
Reviewer: ChatGPT Pro, Haofan account  
Conversation: `https://chatgpt.com/c/6ad6a261-f9ec-8328-863e-ecf482b48e65`  
Final reviewed commit: `06bf5fef693be5321ce7daf9d2384b8fa3953fde`  
Final verdict: `E017_REAL_HEAD_ADAPTER_DESIGN_READY_PASS`

## Review sequence

Round 1 reviewed commit `ad992707b4d9e0197f75b8dfc3e6dfd5acc1b51e`
and returned `E017_REAL_HEAD_ADAPTER_DESIGN_REVISE`. Four blockers covered
checkpoint conversion and storage aliasing, the intentional F_AMP_SHAPE seed
offset, failure-commit semantics, and overbroad representation-readability
claims.

Commit `06bf5fef693be5321ce7daf9d2384b8fa3953fde` applied the design repairs and
received `E017_REAL_HEAD_ADAPTER_DESIGN_READY_PASS`. The reviewer recorded that
B1–B4 were closed in the static design scope.

## Closure by blocker

- **B1 closed:** last-layer rows have independent non-aliasing storage; the old
  full matrix is not registered twice; rows are reconstructed into one original
  three-output `F.linear` path; conversion inventory and branch-boundary
  bitwise tests are explicit; arms and anchors start from one pristine state.
- **B2 closed:** the F_AMP_SHAPE epsilon seed is acknowledged as an intentional
  decoded update-0 difference. Each arm records its true start and B25 offset;
  change and terminal comparisons retain their frozen meanings.
- **B3 closed:** operation-entered, step-returned and complete-committed counters
  are distinct; last-complete advances only after validation and durable write;
  the independent failure writer and non-self-referential retrieval contract
  close the two failure counterexamples.
- **B4 closed:** all arms use the same frozen hidden feature `h_i`; D_DIRECT and
  F_AMP each have `width+1` trainable scalars; F_AMP_SHAPE has `2*width+1`; the
  cancelling shape bias is removed and positive/negative claims are limited to
  the specified adapter and 64-update procedure.

The reviewer confirmed that native-weighted pooling of frozen nonlocal `h_i`
is a defensible P0 function-to-scalar readout, and pointwise linear logits on
the same `h_i` followed by the frozen shape transform are a defensible P0
function-to-field readout. Equal parameter counts are not interpreted as equal
function classes, and nonzero feature variance is not treated as sufficient
causal proof.

## Review limitation and authority

The reviewer recorded the supplied exact commit identity but did not
independently verify repository or byte hashes in this design rereview. This is
a design PASS only. It authorises preparation of a local disabled implementation
candidate and synthetic/no-science tests. It does not authorise real packet or
checkpoint access, model execution, autograd, optimiser construction, producer
or GPU access, training, holdout access or rollout.
