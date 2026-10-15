# Physical-raw code review: revision required

Date:2026-10-15 Europe/London. Scope:read-only review and record update only.
Reviewed snapshot:`ab34c460ec9998197c3f7a1879e979278721e67f`.
Design:`45b8d32`; paired lock unchanged
`cb9f63f8bd4b73afe0bd0f74bc7836018ce2e6bfcbd46edae80e7fef7b07868c`.

## Delivery and response

User explicitly approved the exact saved request in
`raw_v2_code_review_send_draft_20261015.md`; sent once, unchanged, with no
attachments to `多目标优化学习 FEM–PINN Delta`
(`01a12d15-9b60-7280-8248-18386d6ef741`). Delivery returned the intended thread
and isError=false; recipient acknowledged and returned a final review.
Review turn:`01a1401b-ce08-71d1-ba00-297d5b8b30f3`;
final message:`msg_015d0a19570ed14a016ad0edcfba448191b848369964b9eb1d`.
Compact wait omits inline code comments; full final-message text was retrieved
to check the mandatory finding. Other S04-E017 material in the same turn is not
approval for this route.

## Item-by-item main-chat verification

| Review item | Source check at ab34c46 | Main-chat conclusion |
|---|---|---|
| Training-only h/r scales | s04_raw.py:87–103,155–158 compute scales per training keys, using full admitted PIN area/cycle weights | Consistent with v2; no heldout scale statistics introduced |
| Physical residual and nonnegative final raw | s04_raw.py:115,57–65,231–234 fit physical residual/r and score the final mapped output | Consistent; d/history remain common V0/V1 controls, not learned heads |
| Numerical errors versus performance fallback | finite/require checks, ratios:170–178, select:181–192, terminal main:318–323 | Invalid/unidentified paths terminate; normal fallback belongs to model selection |
| Four-fold and tolerance decision | s04_raw.py:195–210,261–272 | All four folds retained, early guard first; fallback must have R=G=1 |
| **P2 mandatory: relative authorization path** | s04_raw_guard.py:25–26 reads auth_path relative to caller cwd;36 resolves only env value;79 still passes str(auth_path);84 launches with cwd=root | **Confirmed.** A valid caller-relative path can fail in the child after cwd changes. This is a failed-execution risk, not demonstrated consent bypass or scientific-design failure |
| Coverage/resource limitations | raw_v2_runner_engineering_20261015.md and existing receipts | Retain: generated pipeline is not actual NPZ/MAT decode/I/O, conditioning or real-parent import evidence; mock caps are not measured extreme resource tests |

The five reviewed source files have no working-tree difference from ab34c46.
No new tests, mock execution, real archive reads, real fitting/scoring or
producer access occurred during this response. Reviewer also reports read-only
inspection, with no tests/fitting/confirmation access.

## Decision and unique next step

Independent code status:NEEDS REVISION, not Code Ready or Run Ready. No top-level
scientific design revision is indicated by this review. Existing R002 results,
design45b8d32, source/feature/data identities and budgets remain unchanged.

Proposed next work, requiring user direction: normalize authorization path once
at guard entry, before validation, and pass that same absolute path to parent
validation, environment and child argv; add one non-repository-cwd mocked
handoff regression test without a real approval artifact or scientific source.
Then prepare a new exact request for difference-only independent review and
minimal mock evidence, for per-send user approval. Reviewer says no full-size
resource rerun is needed for this localized repair. No code change or test was
performed here.

Real fitting would still need accepted exact code plus a new Experiment/Run
protocol and separate human execution approval; none is created or implied.
Main chat remains sole implementation/execution owner; method chat read-only,
S04-E017/MOO held, U0.1175/U0.125 closed, no Delta NN. Shared records and Obsidian
are updated locally; no unapproved follow-up message was sent.
