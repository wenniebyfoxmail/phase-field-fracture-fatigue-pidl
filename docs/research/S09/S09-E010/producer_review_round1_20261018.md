# S09-E010 producer-package review — Round 1

- Reviewer: ChatGPT Pro, Haofan account
- Conversation: https://chatgpt.com/c/6ad49578-9328-832b-b4ee-bfe121ff38eb
- Exact reviewed commit: `ded694d665000ed8db248f2dc96110e062ef07d8`
- Review ZIP SHA256: `075370e624c875f9b3ed7115fa5fee9839d03b5b77e24588edfc06a3c528153d`
- Verdict: `REVISE_AND_REREVIEW`

The reviewer independently verified the 64,193-byte ZIP, all 12 manifest
entries, member byte counts, SHA256 values and CRCs. It found no duplicate,
path-traversal, symlink or undeclared source member.

## Blocking findings

1. `write_shared_evidence()` checked required arm artifacts for existence but
   did not re-read the on-disk termination receipt or compare current artifact
   hashes with the receipt. A required log could therefore change after arm
   close and still reach a `SUCCEEDED` completion receipt.
2. `_unresolved_projection()` replaced the already frozen packet SHA with a
   placeholder. The resulting projection was deterministically rejected by
   the reviewed integration validator as `no-training source identity drift`.
3. If the published update-500 checkpoint remained unreadable during both the
   main hash pass and fallback, the state machine retained
   `checkpoint_present=True` without an artifact identity. The inherited
   receipt validator then rejected the failed receipt before it could be
   written.

The review did not change the loss functions, three arms, 500-update budgets,
evaluation schedule, thresholds or E009 conclusion. It independently checked
the exact replay clauses, integer AUC boundary, protected ratios, conditional
physics interpretation and all-cycle figure structure without executing the
real optimizer or producer.

## Adopted repair scope

The repair preserves the reviewed packet SHA during projection; caches the
checkpoint SHA before atomic publication so a later read failure can still
produce an honest failed receipt; re-reads the disk receipt and re-hashes every
declared arm artifact before shared success evidence; and adds focused
no-training regressions. Additional independently identified fail-stop and
failure-receipt gaps are included in the same narrow repair commit for one
rereview.
