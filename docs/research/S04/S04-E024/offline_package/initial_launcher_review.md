# D013 offline launcher review — CHANGES_REQUIRED

Launcher SHA256: `69b100e5ea3a3177d147e9272c058679e9039266d0a783087b6ddf5e5be0bf7e`. Science commit: `18d0e7cb1153dc969c1ee0c21c77ada1297b2d89`; code tree: `14f6ba5d4b0107e0655f711622ef51268222221e18666f65426bc11e42813c23`. This focused package/material-change review reuses the existing science Code Ready PASS. The final package manifest is not assembled, so this is not a final frozen-package review.

The default CLI and false authorization stop before preflight/spawn. Source/package/path/human-quote/scope checks, exclusive CONTROL claim, no retry after attempted/ambiguous spawn, source HEAD/clean/tree admission, archive path/link restrictions, input byte identity and detached DISPATCHED_NOT_COMPLETED receipts are coherent. Final Code Ready/nontraining receipts stay outside the immutable science checkout. No scientific execution occurred.

## Required changes

### L1 [P2] Enforce and charge the entire prelaunch phase

Location: `docs/research/S04/S04-E024/offline_package/launch_d013.py:141`.

The300s timer starts after authorization-manifest hashing. validate_package is called without its check callback and environment_admission also runs before any resource guard; a slow hash/git/filesystem/environment operation can exceed the phase ceiling before rejection. Later, runtime_check.wall_seconds is frozen at line167, before writing/hashing the runtime receipts and launch claim, the final guard, and spawn/launch overhead. The detached science parent sees only that earlier number, leaving a gap in cumulative accounting. The final guard can prevent a late start but cannot retroactively enforce or charge the complete prelaunch interval.

Required: Use one absolute prelaunch deadline and resource guard from the start of authorized byte work, including package/environment admission and bounded subprocesses. Bind a conservative, explicitly labelled handoff allowance or another enforceable end-to-end accounting mechanism so all remaining prelaunch/spawn work is charged without borrowing numerical time. Keep the default/false-approval gate before preflight/spawn and preserve one-shot failure semantics. Add artificial clock/blocking-operation tests.

### L2 [P2] Enforce one declared new-archive budget across control and scientific output

Location: `docs/research/S04/S04-E024/offline_package/launch_d013.py:154`.

guard checks only CONTROL against1GiB while the unchanged scientific supervisor checks only OUTPUT against1GiB. The extracted source alone is47,994,968bytes in CONTROL, before receipt/log growth, so an otherwise permitted near1GiB OUTPUT would exceed the frozen single new_archive_bytes=1GiB budget. The launcher two-GiB free-space check does not enforce the stated one-GiB archive cap; the prepared package/source tar adds further storage if it is included in that policy.

Required: Keep the frozen scientific code unchanged and enforce the declared combined archive scope while detached work runs, stopping only task-owned work if total controlled new bytes exceed1GiB. Explicitly identify whether immutable prepared package bytes count, and reserve/account for control/source/log bytes; do not silently turn the single cap into two independent caps. Add a synthetic combined-storage boundary check.

## Checks and limits

- Independently reran16 launcher-only artificial tests: all passed. This suite does not currently test the two accounting gaps above.
- Independently verified exact clean18d0e7cb staging/tree, all1455 regular tar members matching staged bytes, and all88 local input identities (238110147bytes). Only streams/hashes/JSON/git metadata were read; no model or array was deserialized.
- Source tar:33647431bytes, SHA256 `4682bf96f178c4ca6dc9faf56a9f591cb687077e554240d77a997b818681d7b1`; extracted source47994968bytes. Identity check and synthetic logs are recorded in the JSON report and existing package check ledger.

`scientific_execution_authorized=false`. No actual authorization file, numerical preflight, NN/FEM forward, real head solve, training, SSH, upload/push or dependency install was performed. Preserve this review, repair the two packaging resource/accounting issues, then request focused re-review. The final manifest and human-facing approval plan still need final assembly/binding after launcher review.
