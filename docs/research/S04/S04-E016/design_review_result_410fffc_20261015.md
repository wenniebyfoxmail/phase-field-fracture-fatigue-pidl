# Independent design review:410fffc — revision required

Date:2026-10-15, Europe/London. Owner:S04 / S04-E016 design follow-up.
Scope this turn: send the exact user-approved request; check returned review;
report next action and update Obsidian. No implementation or fitting.

## Delivery and reviewer identity

- Sender: main chat `探索神经网络学习 FEM-PINN 残差`,
  `01a1131d-017c-7b03-a95a-ad73ba8fcc9c` (not email).
- Recipient: `多目标优化学习 FEM–PINN Delta`,
  `01a12d15-9b60-7280-8248-18386d6ef741`.
- User explicitly approved this exact410fffc request. Sent unchanged from
  `design_review_send_draft_20261015.md`, no attachments or file transfer.
- Send returned the intended thread ID. Reviewer acknowledgement and terminal
  response verify receipt; no resend or further outgoing message.
- Review turn:`01a13f7d-8b31-7bb1-80ff-ece418e29411`, completed normally.
- Final message:`msg_015d0a19570ed14a016ad0c45dd0c08191b3161b789cecf700`.

## Independent conclusion

Direction reasonable; **410fffc is not yet approved**. Revise the design text
and obtain confirmation before implementation. The single-output question can
test physical raw archive imitation, not multi-variable learning or a shared
network/MOO claim. Identical d/history baseline maps are fair and their
pointwise-versus-temporal limitation is stated appropriately. No additional
experimental arm, clipping ablation, NN or confirmation access is needed now.

## Main-chat verification against the unchanged reviewed document

| Required correction | Existing text and check | Assessment / smallest document repair |
|---|---|---|
| Both input scales explicit | §4 lines91-93 specify r_train only; the unchanged32-column feature interface still transforms history using h_train | Valid omission. Specify BOTH training-PIN h/r means with original area/case/stratum weighting, independently within every inner/outer fit; history output removal does not remove history inputs. |
| Numerical errors must not become normal fallback | §5 lines148-149 rejects alpha on finite/bounds failure; outcome table line192 instead classifies such failures as uninterpretable | Valid contradiction. Identity, nonfinite intermediates/pre-map/post-map values, and mapped-output bound failures must terminate as invalid evidence, not candidate ineligibility. Reserve normal eligibility veto/fallback for identified statistical performance conditions; distinguish undefined denominators explicitly. |
| Tolerance and partial fallback explicit | §5 defines1e-10 at129-134, but outcome table lines194-195 uses bare1; partial outer fallback is not explicitly routed | Valid ambiguity. Use Q<1-1e-10 AND every G<=1+1e-10 consistently; list ties separately. Any outer fallback gives that fold R=1 and hence Q>=1, preventing strict all-fold improvement. Include every fold; do not report only nonfallback folds. |

`git diff 410fffc -- <design file>` was empty when checking. Line numbers refer
to `design_revision_raw_physical_v1_20261015.md` at410fffc, not a rewritten
version. The reviewed design and old R002 results are preserved unchanged.

## Additional toy checks recommended for a future implementation

Do not run them in this document-review turn. Add to the already-planned test
contract, without another method arm:

- zero-residual output identity;
- projection onto nonnegative values cannot increase squared error to a
  nonnegative target;
- one partial outer fallback implies failure to establish strict worst-fold
  improvement; all four folds remain visible;
- tolerance boundaries and explicit tie status;
- NaN/nonfinite/mapped-bound errors terminate rather than yielding a normally
  completed V0 fallback;
- physical errors always use final mapped predictions.

The status of any zero-residual learned-fit test must account for standardized
constant target handling; it is not permission to execute a real fit now.

## Unique next action and authority

Prepare a document-only v2 addressing the three corrections and toy-check
specification, keeping only V0/V1 and the existing data/input roles. Then
present a new exact review-request message for the user's per-send approval.
Do not add another experiment group merely to resolve text/logic ambiguity.

This turn does NOT revise the design, implement a runner, allocate a new
Experiment/Run, fit a model, compute counterfactual outputs or contact a
producer. Review approval is absent; code/run approval is also absent.
Any eventual computation still requires a new Experiment/protocol, independent
exact code/resource review and separate explicit user authorization. Proposed
300s/2GiB/100MiB is not an active execution authorization. U0.1175/U0.125,
NN/MOO and teacher/physical qualification remain closed.

Obsidian task note and its single Roadmap entry record the review result and
this next action. No reply or new review request was sent back to the method
chat; that would require renewed human approval of the exact message.
