# S09-E009 runner-integration review — Round 1

Date: 2026-10-17  
Reviewer: Haofan / ChatGPT Pro  
Reviewed exact commit: `77ab15254e8b444a37ae9f11c9a91791f2e1d906`  
Conversation: <https://chatgpt.com/c/6ad21ed5-b38c-8330-a463-aeee98191c9b>

## Verdict

`REVISE_AND_REREVIEW`

The reviewer independently reproduced the selected suite as 59 passed. Its
supplemental checks produced 40 passes and four expected-rejection failures.
It also compiled 25 reconstructed Python files and confirmed that the new CLI
returned zero for `--help`. No optimiser update, SSH access, producer access or
real packet export occurred.

## Findings that passed

- The exact 500-update schedule is 31 complete repetitions of the 16-cycle
  order followed by cycles 1--4; each arm has 500 updates, the total cap is
  2,000, and evaluation updates are 0/16/64/128/256/496/500.
- Parameters and buffers are byte-identical at initialisation and have
  disjoint storage. Each empty AdamW instance binds only its own arm.
- Runner directions matched the reviewed core exactly in 12 tiny-Q4 cases and
  four high-norm clipping cases. Replay uses the frozen merger once and does
  not apply a second clip.
- The saved damage gradient is the exact same-forward gradient of
  `l_d + l_dr`; no second forward is used and the saved tensor is independent
  of later parameter changes.
- The integration exposes no optimiser-step or producer-launch route.

## Blocking findings

### F1 — frozen configuration identity was not fully fail-closed

The base-config check compared a caller-supplied declared hash with the same
caller-supplied file. A caller could change both. The reviewer demonstrated
this by changing `peak_boundary_lifting.atol` from `1e-12` to `1.0`, updating
the declared hash, and still obtaining `NO_TRAINING_INTEGRATION_PASS`.

The validator also accepted drift in:

- `budget.unused_budget_transfer`;
- `source.protocol_revision`;
- `producer.resolved_environment`.

Required repair: bind the production path to an independently frozen base
identity, retain only an explicit narrow synthetic size adapter, and validate
the frozen protocol, budget-transfer and unresolved-producer fields.

### F2 — evidence outputs were not conditional on terminal state

The manifest required `checkpoint_update500.pt` from every arm, although the
protocol requires it only from a normally completed arm. The declaration must
separate common evidence from completed-only evidence and freeze structured
receipts for `COMPLETED`, `EXECUTION_FAILED` and `METHOD_INAPPLICABLE`.
Failure receipts must retain the partial step/log counts and last valid
evaluation without fabricating a final checkpoint. Method-inapplicable anchor
arms must preserve the stationary reason and stop location without being
reclassified as execution failures. Shared identity or replay failure must
make cross-arm performance comparison ineligible even if files exist.

## Allowed next action

Repair F1 and F2, add no-training regression tests, freeze a new exact commit,
and request a narrow runner-integration rereview. The reviewed core, losses,
beta values, thresholds and protocol remain unchanged. This verdict does not
authorise training, SSH/transfer, a Taobo launch, or a scientific claim.
