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

## User-authorized localized repair — 2026-10-15

Code snapshot:`c883bfd8e4ecd37d2ae32dc3717a63db018f1ae2`.
Only `SENS_tensile/s04_raw_guard.py` and `s04_raw_guard_checks.py` changed.
Guard entry now resolves non-None authorization against caller cwd once,
before parent validation; parent validator, environment and child argv use
that same absolute Path. None remains None, preserving missing-approval refusal.
No model/data/feature/design/selection/report/budget changes.

One new lightweight mock-only test executed once and exited0:

```text
/Users/wenxiaofang/miniconda3/bin/python3 SENS_tensile/s04_raw_guard_checks.py --authorization-handoff-only --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E016/engineering/raw_v2_20261015/auth_handoff_01
```

Receipt:`auth_handoff_01/authorization_handoff_receipt.json` under the same
engineering archive root as earlier checks. Test ran on base2a9366a with the
exact source patch subsequently committed as c883bfd; no source edit between
test and commit. Git commands, validator, Popen and RSS reader are mocked.

| Check | Observed |
|---|---|
| Caller cwd differs from repository root | asserted with contextlib.chdir |
| Relative approval path before child cwd change | parent validator receives expected absolute Path |
| Child argv after cwd=root | same absolute path; root/path resolves to caller's expected path |
| Fit/report environment | RAW_AUTHORIZATION identical to parent path in both virtual phases |
| Real authorization artifact/source/child/fitting | artifact never exists; real source module replaced by stub; Popen intercepted; all false/0 in wrapper receipt |
| Scope | one handoff scenario only; no cap tests, toy model fit or full resource rerun |

The virtual guard's own receipts exercise real-mode plumbing and therefore
carry mode=real, but are **mock artifacts, not real execution or consent**;
the wrapper explicitly labels virtual_guard_receipts_only=true and records
zero real child processes/inputs/fits/scores. They provide no resource evidence.
This test checks path handoff, not real validator policy or scientific I/O.
Existing synthetic resource and cap evidence retains all previous limitations.

Current status:local repair/test complete, independent difference review pending.
Exact request prepared in `raw_v2_path_rereview_send_draft_20261015.md`, NOT SENT.
Main chat remains sole executor; method chat receives no new work until this
exact request is approved. No actual-run authorization or new experiment/run
created; no producer access, confirmation read or real fitting. Obsidian and
Roadmap updated. Style check used the user's direct approval-request wording
in this chat; no claim of exact author imitation or external style retrieval.
