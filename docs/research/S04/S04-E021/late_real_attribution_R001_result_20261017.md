# S04-E021-LATE-ATTR-R001 — completed, verified and frozen

2026-10-17 Europe/London. Diagnostic, viewed synthetic development only.
This is the one approved 9984226/2f0ff22 late-cycle attribution, not a new fit,
producer run, confirmation test or physical-cause result. Original E021 verdict
unchanged. The execution approval is consumed; no retry or follow-on compute.

## Authority and provenance

- Main chat/sole execution and record owner:
  `01a1131d-017c-7b03-a95a-ad73ba8fcc9c`.
- Actual user message `01a14b77-a884-7151-a192-56663074c791`, in turn
  `01a14b77-a86a-7880-854a-4d1078880e1f` (turn started2026-10-17T20:04:55Z;
  separate message timestamp not supplied). Human text read back before launch:

  > 批准按97dd337运行卡、使用ab48965代码执行唯一一次S04-E021-LATE-ATTR-R001四源真实只读归因及报告，批准索引S04-E021-LATE-ATTR-R001-CARD-v1-ab48965。保持60秒／512MiB／5MiB预算，失败或触限不重试。完成后冻结核验并报告下一步，由本对话统一更新Obsidian；不拟合、不打开确认数据，避免双写和重复计算。

- Approval reference:
  `codex-thread:01a1131d-017c-7b03-a95a-ad73ba8fcc9c/approval:S04-E021-LATE-ATTR-R001-CARD-v1-ab48965`.
  Actual approval readback mapped to this index, not inferred from a grant bool.
- Card/launch checkout: `97dd3378a29cf841693103b9dfdbc814d75bc7e9`,
  `late_real_attribution_R001_run_card_v1_20261017.md`.
- Source: `ab489652d4b4bb55c166782c8b9de9645a5f569b`;
  plan `9984226de5eb659b9ed6f82803a22c91a92e5f82`;
  scope `2f0ff22d26818ece7aa02f509451301c0cefb7d2`.
- Independent code review was read back before launch: reviewer chat
  `多目标优化学习 FEM–PINN Delta`, `01a12d15-9b60-7280-8248-18386d6ef741`,
  turn `01a14b70-fb6b-7643-b408-66045fe4a09a`, message
  `msg_015d0a19570ed14a016ad3d35251548191b22c1d021d6e269a`.
  Static acceptance, both fixes closed. No new task/message/compute dispatched
  to that chat during this run; no shared writing or duplicate execution.
- Host `Wennies-MacBook-Pro-14.local`, CPU only, numeric threads1; no GPU/SSH.
- Branch `codex/s04-late-regression-plan-20261016`; cwd
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-late-regression-plan-20261016`.
- Prelaunch: clean tracked source/contracts, exact accepted-source equivalence,
  unchanged card, fixed output absent and no same-worker/guard process found.
  No scientific source opened by the preflight.

Exact approved command issued once, from the cwd above:

```bash
PYTHONOPTIMIZE=0 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -B /Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-late-regression-plan-20261016/SENS_tensile/s04_late_real_attribution_guard.py --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/late_attribution_runs/S04-E021-LATE-ATTR-R001 --expected-commit ab489652d4b4bb55c166782c8b9de9645a5f569b --approval-ref 'codex-thread:01a1131d-017c-7b03-a95a-ad73ba8fcc9c/approval:S04-E021-LATE-ATTR-R001-CARD-v1-ab48965' --review-ref 'codex-thread:01a12d15-9b60-7280-8248-18386d6ef741/message:msg_015d0a19570ed14a016ad3d35251548191b22c1d021d6e269a' --allow-real-attribution
```

## Execution, budget and access

- Start `2026-10-17T20:05:43.080995+00:00` (London21:05:43 BST).
- Guard66697 → worker66720; both exits observed, worker0, shell0.
  Cleanup ALREADY_EXITED, exit_confirmed=true, no signals/errors.
- Guard COMPLETED, primary_reason=null, terminal_caps=[], errors=[],
  receipt_persisted=true; worker READONLY_ATTRIBUTION_REPORTED, error=null.
- Measured execute elapsed8.805456208996475s; aggregate sampled peakRSS
  243662848bytes =232.375MiB; final8files253398bytes including cache/receipt.
  Within60s/512MiB/5MiB; sampled, not OS hard peak guarantees. Parent interpreter
  startup excluded as in card. No resume/retry, new mock or budget extension.
- Version-2 four_source_readonly_attribution grant, actual refs/Run/output/code
  identical across grant/worker/guard; dirty_source_status empty; optimize0,
  debug=true. Source_metadata_accessed/real_data_read/attribution/plotting=true;
  fitting/confirmation=false; original scientific verdict unchanged=true.
- Exactly4 scientific read attempts,16 metadata attempts,79377 returned bytes:
  CSV68796, replay summary2496, replay verification2941, saved inventory5144.
  These are the four fixed paths in the card; logs show no extra scientific
  path. Snapshot validated357rows and original counts/weights, used only late81
  for decomposition and saved three-case background without recomputation.
- Log30lines, including one font-cache notice, one attribution entry, one plot
  entry and one worker terminal record. No traceback/crash or worker failure.
  Font cache was created inside the Run and included in the output budget.

## Saved diagnostic results (not recomputed after execution)

Unit: one U0.11 trajectory's81 related cycles C41–C121, s4 post-history,
horizon0. D=V1 physical-raw MSE−V0 physical-raw MSE, raw archive units squared;
not a network Delta/PDE residual. These are copied from this Run's summary.

| Saved quantity | Result |
|---|---:|
| k50 /81 | 22 /81 =0.2716049382716049 |
| harm / improve / tie | 54 /27 /0 |
| harm / improve / tie fractions | 0.6666666666666666 /0.3333333333333333 /0 |
| S_plus | 22108.36003035686 |
| S_minus (positive improvement offset) | 10890.802912713394 |
| S_net | 11217.557117643466 |
| late mean MSE difference | 138.48835947707983 |
| sum_tau | 3.460357596477092e-05 |
| late RMSE ratio / frozen reference | 1.0160831289564438 /1.0160831289564436 |
| maximum positive D | cycle101,556.3880211814458 |
| analysis status | DESCRIPTIVE_ONLY |
| branch | PROPOSE_PHASE_OBJECTIVE_REPRESENTATION_QUESTIONS |
| C121 in k50 contribution set | false |

Saved ranked k50 cycle IDs (not time order):
101,90,100,94,102,89,99,98,95,103,97,91,96,88,93,104,109,117,92,87,110,105.
They supply half **positive excess**, not half the net error. Improvement offsets
must remain visible. k50>1 and harm>=41 select the predeclared phase/objective/
representation question branch, not single-state provenance as the first branch.
No threshold/window/tolerance was changed after viewing results.

## Integrity, figure and freeze

Only this Run's own controls, diagnostic table, log and README were opened for
terminal verification. CSV contains81 ordered cycle IDs41–121 and the expected
seven report fields. Receipt/inventory sizes and identities agree, references
match, four source-byte counters agree, log has one attribution/plot invocation.
Checked saved numerical fields and table/figure scope; **did not re-run describe,
recalculate the81-cycle attribution, or reopen the four scientific sources**.
The authorised engine's arithmetic checks passed; this is not an independent
numerical re-derivation or independent result review.

| Frozen file (relative to Run root) | Bytes |
|---|---:|
| authorization.json | 1606 |
| diagnostic.csv | 8278 |
| summary.json | 5617 |
| diagnostic.png | 82271 |
| README_analysis.md | 2115 |
| analysis.log | 5456 |
| guard_receipt.json | 3286 |
| cache/matplotlib/fontlist-v390.json | 144769 |

Raw/asset endpoint:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/late_attribution_runs/S04-E021-LATE-ATTR-R001`.
All8files regular, nlink1, no symlinks/special files; all0444, Run/cache
directories0555, observed frozen by2026-10-17T20:06:34Z after both PIDs gone.
No source/old-run permission changed, output rewritten, extra archive file or
routine hash added. Seven core files plus the actual font cache are preserved.

Viewed this exact diagnostic.png: two nonblank readable panels, signed bars and
zero line retained, physical cycle labels, rank cumulative curve/.5 line/k50=22,
Run/synthetic-development/s4/horizon0/units and non-causal labels visible. The
visual pattern and k50 label agree with the saved descriptive result. No rerender.
Copied this existing PNG byte-identically to Obsidian only:
`/Users/wenxiaofang/obsidian/attachments/S04/2026-10-17/S04-E021-LATE-ATTR-R001_diagnostic.png`;
embed in the existing residual-correction task note, not a second analysis.

## Facts, inference, uncertainty and only next step

Facts: this bounded access/attribution/report completed under the sampled caps,
passed its declared checks and produced a complete frozen diagnostic.54/81
cycles have positive beyond-tolerance MSE differences,27 improve; k50=22.

Bounded inference (wording narrowed after independent read-only result review):
The saved k50=22 means that 22 ranked cycles are needed to reach half the
positive excess MSE. Together with saved n_harm=54, this selects the predeclared
phase/objective/representation-question branch. It does not identify or rule
out a shared upstream cause or provenance anomaly affecting multiple cycles,
and does not justify excluding any cycle. The figure shows structured temporal
sign variation, not physical cause. No exclusion of C121 or post-hoc change of
the old verdict is warranted.

Uncertainty: one already-viewed synthetic trajectory/window, correlated cycles,
scalar reductions only. Cannot identify physical causes, gradient conflict,
spatial support, driver/history coupling, NN necessity, a correct new loss or
confirmation generalisation. Other three case values remain saved background.
No independent result review had occurred at execution closure; the subsequent
bounded review is recorded in `late_real_attribution_R001_result_review_20261017.md`.
It accepted record/visual consistency with the above wording correction, not
independent arithmetic re-derivation/source authentication or physical validity.
Execution health is not mechanism validity. No frozen artifact was rewritten.

**Only next proposed action after that review:** prepare a minimal phase-objective/
representation design-question proposal for human approval, not a selected
loss, implementation, source reopening or new fit. The later review did not
perform/recommend an additional calculation, and this amendment adds none.
Main chat alone updates Obsidian; U0.1175/U0.125 remain closed and S04-E017/NN/
multi-objective fits remain deferred.
