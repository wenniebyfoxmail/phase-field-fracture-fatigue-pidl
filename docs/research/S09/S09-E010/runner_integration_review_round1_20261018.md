# S09-E010 exact-commit runner-integration review — round 1

## Verdict

`REVISE_AND_REREVIEW`

Actual reviewed candidate:
`c8fac581c91ac859ab4b90c54abb971549d4565d`.

Review channel: ChatGPT Pro, account `Haofan`, in the existing S09-E010
conversation:
<https://chatgpt.com/c/6ad49578-9328-832b-b4ee-bfe121ff38eb>.

The review used the complete manifest and complete candidate diff inline after
the local browser could not attach the ZIP. The locally prepared package was:

- file: `S09-E010-runner-integration-review-c8fac581c91a-20261018.zip`
- bytes: `103,237`
- SHA256: `a20c68a7157f6e9f8dbe6990ff9f76dbad10b840d05be27c3c0e9c2306214b25`
- manifest: 21 content files

The reviewer therefore checked the supplied file contents, hashes and diff,
but did not independently reproduce the ZIP byte identity.

## Blocking findings

### I1 — prompt and manifest named different full commit identities

The review prompt accidentally expanded the candidate to
`c8fac581c91a640dadb401c8226df8692edbe440`, while the manifest correctly
recorded the actual checkout commit
`c8fac581c91ac859ab4b90c54abb971549d4565d`.

This is a submission-identity error rather than a source defect. The focused
rereview must use one full commit read directly from the checkout in every
identity field.

### I2 — terminal stop position was underconstrained

`validate_termination_receipt()` required only
`optimizer_steps_completed <= stop_update <= 500`. A fabricated
`METHOD_INAPPLICABLE` receipt could therefore claim zero completed updates but
place the stop at update 500.

The required constraint is:

```text
optimizer_steps_completed <= stop_update
stop_update <= min(optimizer_steps_completed + 1, 500)
```

It preserves a check at update 0, a failure before the first completed update
reported at update 1, ordinary `63 -> 64` failure reporting and a terminal
`500 -> 500` evidence-write failure.

## Findings that passed review

- The three arms, 500-update per-arm budget, 1,500 total cap and evaluation
  points match the frozen protocol.
- The three models have a shared initial state with disjoint parameter and
  buffer objects; each has a separate AdamW instance with empty state.
- A25, B25 and B0 route to the reviewed core with one global clip and no
  target-derived inference path.
- Exact-A25 replay and shared-identity checks fail closed before cross-arm
  claims; only the literal `True/True` combination is eligible.
- The integer `2W+T` decision rule is unchanged.
- No optimizer step, backward call or producer launch exists in this layer.
- The reviewer cross-checked the inherited manifest identities, all 48 stored
  direction hashes, the initial model hash and the independently reconstructed
  schedule hash.

The reviewer environment lacked PyTorch and pytest, so the 72-test suite and
frozen forward/autograd evidence remained local evidence. Future producer code
should reuse the reviewed E009 A25 path directly and obtain `g_D` separately;
these were non-blocking implementation notes.

## Narrow resolution

The revision tightens only the stop-position inequality and adds rejection and
boundary regressions. The actual frozen 16-cycle packet is then rechecked with
no parameter update. The focused rereview will be bound to the new checkout
commit read directly by Git. It does not add a training or producer path.
