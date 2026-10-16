# Frozen-model inference replay — independent code review and reconciliation

Date: 2026-10-15 Europe/London. Owner: residual main chat
01a1131d-017c-7b03-a95a-ad73ba8fcc9c. Scope: engineering C0/C1 only;
E021's closed scientific verdict and its original outputs are unchanged.

## Approved delivery and returned decision

The user approved the exact request in the preceding main-chat response.
Its stored body is in replay_code_review_request_DRAFT_NOT_SENT.md at747e8be;
that filename preserves the original draft and is not current delivery status.
Main chat sent that body once, unchanged, without attachments, to
`多目标优化学习 FEM–PINN Delta` (01a12d15-9b60-7280-8248-18386d6ef741).
The sending tool returned the intended thread with isError=false. The recipient
explicitly acknowledged45d3605 and its final response names the complete SHA.
No resend, follow-up message, other recipient or execution approval is inferred.

- Review channel: existing independent Codex method chat; model not reported.
- Exact code snapshot:45d36055ea10ef1177de342dd01dbfe3c4376ee8.
- Plan:bcb58a6 / next_validation_plan_v1.md; original runtime/model6aa21e3.
- Data lock:cb9f63f8bd4b73afe0bd0f74bc7836018ce2e6bfcbd46edae80e7fef7b07868c.
- Review turn:01a1419d-7bb4-70f2-b751-1185a0e7c290.
- Final message:msg_015d0a19570ed14a016ad14fcaf2dc819185f7cea7938e8fb8.
- Decision:Code Ready; no mandatory blocking change; prepare a separate run
  card and input-staging scope for human approval, do not execute.

Reviewer read source and existing generated/mock receipts, did not execute tests,
open the frozen parent/scientific trajectories/confirmation, or edit files.
Its read-only turn initially inspected the separate da35d7a candidate, then
explicitly switched to the main-chat request; final acceptance covers45d3605
ONLY. The two implementations and their test counts are not interchangeable.

## Main-chat item-by-item reconciliation

| Returned point | Read-only check by main chat | Disposition |
|---|---|---|
| Exact reviewed identity | git diff45d3605 against the three new source files is empty; worktree was clean before adding this record | Accepted for these unchanged source bytes; this documentation commit is not a new code review |
| No refit, solve, scale update or alpha reselection | replay.predict reads stored scales/xm/xstd/ym/ystd/coefficients, indexes the saved alpha; real main calls only the frozen loader, replay and report | Accepted no-fit inference path; no function was executed this turn |
| Independent prediction and output map | replay.py:40–66 uses its own float64 sum, stored target inverse and raw scale; rejects nonfinite values before nonnegative map; V1 damage/history equal V0 | Accepted engineering design, not proof of physical consistency or irreversible evolution |
| Native-area scoring and fixed strata | mse:69–75 divides weighted squared error by total area; replay:99–138 checks saved cycle weights and averages three stratum means equally | Accepted same estimand; all four121/99/82/55cycle prefixes remain the proposed scope |
| Numeric comparison and fail-closed result | mixed1e-10+1e-10*abs(saved), aggregate1e-12, exact verdict; main writes incomplete/failure and exits nonzero on exception | Accepted; no tolerance relaxation or performance fallback on mismatch |
| Separate approval and one attempt | guard.authorize requires replay-specific action, current HEAD, exact destination and clean source/dependencies; fresh output/log/receipt; worker checks parent/run/code binding | Accepted interlock; no real approval file or run exists; future runtime HEAD and unchanged reviewed bytes must be reconciled in its run card |
| Guard ownership and budget | guard starts one worker in a new session, samples guard+live child-tree RSS and output/log/receipt allowance, terminates its own group on failure | Accepted static path;300s/2GiB/100MiB remain proposed caps, not measured actual compliance; real cleanup and SIGKILL branch untested |
| Generated evidence only | read unit_04/engineering_receipt.json:164cycles, MSE6.938893903907228e-18, C20field2.220446049250313e-16; actual_replay/fitting/full_resource_test=false | Matches review; did not rerun generated tests, render or run a resource benchmark |
| Frozen parent identity limitation | reference:144–178 checks exact ten-file set plus three sidecars against recorded read-only mode/size/mtime before and after; no parent-output SHA check | Agreed limitation, not content authentication. Input lock/source hashes remain separate; do not import the other candidate's ten-file SHA requirement or claim |
| Real-path/resource uncertainty | frozen loader reads four complete admitted archives before per-cycle replay; real decoding/I/O/357cycle working set and conditioning not measured here | Code Ready does not establish Run Ready or budget adequacy; stage scope and existing identity evidence must be specified before any approved invocation |
| Scientific boundaries | existing E021 evidence_review.md retains U0.11 late ratio1.01608312895644; no original full fields saved for most cycles | Preserve1.6083% late degradation; a future match is arithmetic consistency, not all-cycle pointwise equality, physical/teacher validity or confirmation generalisation |
| Separate candidate/sole writer | observed da35d7a at the separate S04-E022 worktree and its existing Obsidian entry; reviewer expressly excludes it | Preserve those files/records without merge or deletion;45d3605 is this approved review's sole candidate. Main chat alone updates current summary; no message back or duplicate computation |

No source, model, metric, tolerance, data role or scientific gate changed.
Main chat read source/docs and the existing engineering receipt only; it did
not open the frozen parent outputs, development arrays or confirmation data.
The future S04-E021-REPLAY-R001 output path remains absent.

## Single next step, not an execution order

Prepare one exact S04-E021-REPLAY-R001 run card and minimal input-staging scope
for separate human approval, using only45d3605's reviewed implementation.
Keep CPU4/noGPU,300s/2GiB/100MiB, one invocation, no retry/resume. Do not stage,
decode, launch, hash the real parent, create consent, or perform an actual replay
under this review-only authority. Explain the metadata-based parent binding and
unmeasured real resource peak in that future approval version.

No new fit, SSH, producer work, confirmation access, MOO/NN or S04-E017 work.
No integration of da35d7a and no second candidate launch. Obsidian's existing
candidate entry is preserved, with a newer sole-owner status clarifying which
review actually passed. Tables above are the decision-facing audit visual;
there are no new numerical experiment outputs requiring a new result plot.

## 2026-10-16 run-card preparation only

User approved preparation, not execution. See replay_run_card_v1.md for the
single proposed S04-E021-REPLAY-R001, six leaf-link staging scope, unchanged
data/model identity and300s/2GiB/100MiB accounting. Nine source-file names/sizes
were checked without opening arrays. No staging, actual authorization, real
replay, fit, test rerun or cross-chat message occurred. Reviewed source bytes
remain unchanged. Execution still awaits explicit approval of the card's
final commit; separate da35d7a/S04-E022 remains preserved and excluded.
