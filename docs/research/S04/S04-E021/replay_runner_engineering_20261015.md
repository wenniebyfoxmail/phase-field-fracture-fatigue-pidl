# Frozen-model replay implementation preparation — review pending

Date:2026-10-15 Europe/London. Scope:engineering preparation under accepted
next_validation_plan_v1.md atbcb58a6. User said proceed; main chat explicitly
bounded this turn to implementation/generated tests/review draft, NOT real replay.
Task:inference-only replay infrastructure for the closed E021 result, not a
new fitted model or scientific experiment. Sole owner:this main chat.

Dedicated worktree:/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-raw-replay-preparation-20261015
Branch:codex/s04-raw-replay-preparation-20261015; basebcb58a6. New worktree has
NO local_archive links or scientific payloads. Existing E021 primary/result
worktree and its read-only run are untouched; no other chat messaged/triggered.

## Reuse and implementation

Searched existing s04_raw/d0, their guards/checks and the frozen feature module.
Reused causal FeaturePipeline and the old admitted loader (imported lazily
only after real authorization); never call the old fit guard, fit(), fit_blocks,
normalizer estimation or any linear solver. Independent prediction reconstruction
uses sum((X-xm)/xstd*stored_coeff)+intercept, saved target inverse and final map;
native-area MSE divides unnormalized weighted squared-error sum by total area.
This differs in arithmetic order from original einsum/normalized-area code,
not in intended mathematics. Stored outer alpha/scales/coefs are not modified.

| New source | Role |
|---|---|
| SENS_tensile/s04_raw_replay.py | frozen reference metadata/receipt checks; one-cycle inference; full admitted comparisons; scalar ratios and fixed C20 comparison; audit-only graphic/README |
| SENS_tensile/s04_raw_replay_guard.py | separate replay-only consent interlock; one inference worker;300s/2GiB/100MiB attributed monitoring; own-group cleanup; terminal receipt/no retry |
| SENS_tensile/s04_raw_replay_checks.py | generated coefficients/data, no training; production einsum scorer versus independent replay; numeric/guard/policy mocks |

Initial implementation6547907; current review commit includes this record plus
only subsequent plot-label wrapping and additional in-memory consent-policy
checks. Final unit04 ran the exact source bytes committed with this record;
no algorithm change after that test. Existing s04_d0.py, s04_g5_features.py,
s04_raw.py, data lock and next_validation_plan_v1.md are unchanged from base.

## What executed — generated inputs only

Command (final check; no real guard invocation):

```text
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 VECLIB_MAXIMUM_THREADS=4 CUDA_VISIBLE_DEVICES='' /Users/wenxiaofang/miniconda3/bin/python3 SENS_tensile/s04_raw_replay_checks.py --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/engineering/replay_preparation_20261015/unit_04
```

Final evidence:that directory's engineering_receipt.json, generated_reference.csv,
generated_C20.npz, generated_replay/comparison.csv and audit PNG/README, plus
explicitly virtual guard receipts under virtual_guard/. Earlier unit01–03
retained as development history, not real attempts/retries. No full-size or
actual archive/resource test was executed.

| Generated/mock test | Observed | Limits |
|---|---|---|
| Four generated41cycle cases,201 admitted/202 native toy cells, unequal areas; original scorer versus no-fit replay |164 rows, max MSE absdiff6.938893903907228e-18 | not357 real cycles/85112 admitted cells |
| Fixed generated C20 full fields |max absdiff2.220446049250313e-16 | no real snapshot opened |
| MSE diff / (1e-10+1e-10*abs(saved)) |max6.729185628679756e-08 (<1) | numeric comparison only, not physical tolerance |
| std1e-4..1e4, constant feature, stored y inverse, independent fsum |sampled prediction diff0 | small fixture, not a conditioning guarantee |
| Zero residual/fallback/projection/unequal-weight MSE |passed | stored coefficients generated, never fitted |
| NaN/Inf/-Inf/overflow/zero std/tolerance boundary/corrupt saved score |rejected, no fallback/relaxed tolerance | injected small cases only |
| Severe cancellation example |detects an out-of-tolerance difference | explicitly does NOT establish arbitrary cancellation stability |
| Causal missing/future/whitelist checks |original feature sanity passed | no new deployment inputs |
| Missing actual approval |real entry refused before source/output creation | no actual consent file created |
| Positive/mismatch consent policy |in-memory JSON+git mocks pass; false approval/wrong code/action/unreviewed rejected | virtual interlock tests, not human consent |
| Guard success/child failure/three caps/relative approval from non-root cwd |one virtual child each; cap paths kill only own virtual PID; receipts retained | no actual child,2GiB allocation or300s wait; not a resource measurement |

Source-path audit hook forbids opening actual E016 payload/lock, E021 frozen
run/control and confirmation patterns during tests. Loaders, fit/fit_blocks,
solve/lstsq are patched to reject throughout generated checks. These assertions
support the narrow reported test scope; they are not a system sandbox guarantee.
No real approval artifact, scientific replay, fitting, export or SSH performed.

Generated audit figure visibly checked:nonblank, readable labels (wrapped to
avoid clipping), four toy cases and tolerance reference1; title explicitly
GENERATED FIXTURE / ENGINEERING ONLY. Dots near0 indicate arithmetic agreement
on generated fixtures, not scientific improvement. No frozen E021 PNG rerendered.

## Real-path safeguards and unverified parts

Future actual entry requires a separate exact replay approval JSON, independent
review=APPROVED, exact clean code commit, unchanged plan/dependencies/lock,
and fresh S04-E021-REPLAY-R001 under the fixed replay_runs destination. No such
approval or actual output is created now. Old fit approval cannot pass the new
action/schema. Relative authorization is resolved once before parent/child use.

Worker requires parent/run/code environment binding, checks the saved13-file
read-only size/mtime inventory and original successful receipt/child identities,
then loads only admitted development data through the frozen loader. The
reference check is metadata-based, not cryptographic proof of ordinary outputs.
It checks percycle MSE/ranges/coverage/weights, aggregate R/G/Q and classification,
and available C20 fields; it cannot compare other-cycle fields never saved.
Invalid values/mismatch fail without fit, selection, clipping rescue or retry.

Caps retain proposed accounting:guard timer begins before child source/reference
loading and covers worker inference/summary/plot, not prior parent authorization.
RSS sampled about0.1s across guard+live child tree; not an OS hard peak ceiling.
Output includes child tree/log/guard receipt with32KiB reserve; final receipt
written after measured pre-write bytes. Termination can require0.5s cleanup.

Not yet tested:actual frozen-reference metadata/load/decode, full spatial/cycle
working set, real conditioning/warnings, actual policy file+HEAD roundtrip, real
process-group cleanup or genuine caps. Generated checks do NOT guarantee actual
300s/2GiB/100MiB compliance. Independent code review must assess these limits;
any needed extra check is proposed first, not silently executed.

## Readiness and sole next action

Implementation/generated checks complete; independent Code Ready pending.
Prepare exact read-only review request for per-send human approval; NOT SENT.
After code acceptance, actual replay still needs a fresh run card/staging and
explicit execution approval. No actual replay/fit authorized by this document.
E021's accepted development conclusion and U0.11 late1.6083% warning unchanged;
confirmation, S04-E017/MOO/NN held. Main chat sole writer/executor, method chat
review-only, other coordination chat not triggered. Obsidian/Roadmap updated.
Outgoing draft uses the user's supplied concise instructions as style reference;
no claim of exact author imitation or unrelated writing-account retrieval.

## 2026-10-15 independent code review received

User approved the exact45d3605 request; main chat sent it once unchanged.
Independent method chat accepted45d36055ea10ef1177de342dd01dbfe3c4376ee8
as Code Ready with no mandatory blocking changes, not execution authority.
Main-chat reconciliation is in replay_code_review_result_45d3605_20261015.md.
Next:prepare one exact run card/input-staging scope for separate approval;
no real replay, fitting, scientific payload read or additional test this turn.
Separate da35d7a/S04-E022 files and records are preserved, not covered by this
review or merged. Main chat remains the sole current-record/Obsidian writer.
