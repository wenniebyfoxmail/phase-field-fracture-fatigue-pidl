# S09-E009 runner-integration review — Round 2

Date: 2026-10-17  
Reviewer: Haofan / ChatGPT Pro  
Reviewed exact commit: `af7e79714a72c96f3495470bb84f2b0fbececa79`  
Conversation: <https://chatgpt.com/c/6ad21ed5-b38c-8330-a463-aeee98191c9b>

## Verdict

`REVISE_AND_REREVIEW`

The selected no-training suite reproduced as 69 passed. Supplemental F1/F2
checks produced 62 passes and six expected-rejection failures. The exact files
and repair diff matched the submitted identities. No optimiser update, SSH,
producer access, real packet export or training occurred.

The production base identity, frozen config fields, conditional evidence
manifest and shared identity/replay comparison gates passed. The reviewed
four-arm numerical connection remained unchanged and passed.

## Residual F1 finding

The synthetic branch loaded `TRUSTED_BASE_RUNTIME_CONFIG` by path and compared
against it, but did not first verify that this reference file itself still had
the frozen base SHA256. In an isolated copy the reviewer changed the reference
boundary tolerance, derived the tiny config from that altered file, and still
obtained the no-training PASS.

Required repair: verify the trusted reference file's actual bytes against
`EXPECTED_BASE_RUNTIME_CONFIG_SHA256` before parsing and applying only the
9-node/4-Q4 size substitution.

## Residual F2 findings

The terminal validator accepted four internally inconsistent receipts:

- `COMPLETED` with a nonzero hard-constraint count;
- `METHOD_INAPPLICABLE` with a nonzero hard-constraint count;
- zero completed steps with update 500 recorded as a valid evaluation;
- 127 completed steps with `stop_update=1`.

It also rejected a legitimate late failure in which all 500 updates,
evaluations and the update-500 checkpoint had completed before a later evidence
writer failed. The checkpoint requirement must distinguish “required for
normal completion” from “actually exists before a later failure.”

Required repair: validate all hard-constraint counts as nonnegative integers;
require zero counts for valid completion and method inapplicability; constrain
evaluation updates and stop location by the completed-step count; and allow a
failed receipt to preserve a real update-500 checkpoint and its identity when
the complete 500-update/evaluation state exists.

## Allowed next action

Repair these six dictionary-level counterexamples, freeze a new exact commit,
and request another narrow review. Core formulas, losses, beta values,
thresholds and protocol remain unchanged. This verdict does not authorise an
optimiser update, SSH/transfer, a Taobo launch, or any scientific claim.
