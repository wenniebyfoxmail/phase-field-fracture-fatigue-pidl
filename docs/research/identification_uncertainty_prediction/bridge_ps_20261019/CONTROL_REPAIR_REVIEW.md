# BRIDGE-PS local lifetime-control repair — independent exact difference review

2026-10-19, Europe/London. Independent read-only reviewer `/root/bridge_exact_review`. **REVIEW_PASS, bounded local control-repair readiness.** No blocking discrepancy found in the exact difference reviewed. This is not a scientific rerun, Linux integration validation, or new execution/retry permission. R003's original stop-contract breach and exploratory-evidence limitations remain unchanged.

## Exact snapshot and actual access

- Base commit: `6823b2f395fd5dbd07717f02adbdf6117ea53cd7`.
- Revised commit: `fbdfb0a77529cc940194bc2a29d13b29a082f935`.
- Worktree: `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/mendeley-info-value-20261019`.
- Package: `docs/research/identification_uncertainty_prediction/bridge_ps_20261019`.
- Independently recomputed package digest: `37ebd77995d2201d36692804c9e4c6a6da8a2ff729ae14f30039da83779113d4`; all20 lock-listed hashes matched.
- HEAD resolved to this full commit; tracked working status was clean. Exact difference is eight files: CSV-reader lifetime helper, worker candidate-completion label, new stdlib runtime guard, supervisor/monitor integration, artificial lifetime fixtures, builder/lock, control-repair explanation. Scientific estimator/state/scoring formula, configuration, input/cohort identity, threshold, budgets and no-retry rules are unchanged.
- Read only source/text and hand-authored fixture records. No scientific arrays, native input, raw CSV/XLSX, holdout, saved scientific result aggregation/plots, fit, model forward, SSH, resource check, mailbox action or producer operation occurred. This report is the only authored deliverable; worktree code was not edited.

## Checks independently performed

1. Read complete `runtime_guard.py`, `supervise.py`, `test_runtime_guard.py`, control-repair note and exact `verify.py`/`worker.py` difference; verified lock identity.
2. Independently ran all22 `test_runtime_guard.py` artificial subprocess fixtures under established Miniconda Python3.12:22 passed in5.537 seconds.
3. Independently ran those same22 fixtures under Homebrew Python3.14:22 passed in5.547 seconds. These tests use no NumPy/scientific model/data and actually call the extracted production `monitor_child` with temporary artificial child scripts and CSVs. Each child has the separate8-second test deadline.
4. Read retained artificial trace examples, including a late worker finalizer whose provisional seal already exists but whose fatal event/exit86 still causes rejection; original CSV leakage before seal; controller finalizer during receipt-open rewriting its provisional receipt to STOPPED_NO_RETRY; clean completion with exit0/empty stderr/no event. Unchanged old authority/budget/UTC/rename guards carry forward from the prior review; their owner's four-check log was not represented as a new independent rerun here.

## Decisive findings

### Original leak and scientific invariants

`verify.read_score_rows` now owns the CSV in a `with` block and materializes rows before leaving that block. The artificial fixture exercises this actual helper and finishes with a clean seal and empty stderr. Verification formulas are unchanged. Worker completion status now explicitly means `CANDIDATE_COMPLETE_REQUIRES_CONTROLLER`; it cannot by itself satisfy the supervisor's final acceptance contract.

### Worker lifetime, hooks and persistence

The stdlib wrapper installs warnings-as-errors, `sys.unraisablehook` and `threading.excepthook` before running the target. `runpy.run_path` executes it in the same controller-owned worker PID, preserving the existing worker's immediate-parent controller identity check. An unraisable destructor/callback error or uncaught thread exception emits complete JSON through low-level writes plus file fsync and atomic rename before a fatal-event observer may stop the worker, then exits86. Recursive formatting cannot deadlock: it writes a fallback stderr marker and exits nonzero. Event-write failure similarly has stderr/nonzero fallback, rather than an implicit success path.

The clean seal is provisional. Explicit collection occurs after the target returns and during the earlier-registered final callback, so later target atexit handlers run before that callback's seal. Late module/builtins finalizers can still fail after the seal; the supervisor additionally requires actual process termination, zero exit, no fatal event, completely empty child stderr, and exact-PID clean evidence. The late-finalizer fixture confirms that an existing seal does not overrule the later error. It also rejects direct `os._exit(0)` without a seal, stale PID evidence, and a still-running child.

An ordinary warning raised under warnings-as-errors can terminate through normal exception handling; the guard does not need to mislabel it an unraisable event. If a target replaces the unraisable hook or emits a warning under an `always` filter, the complete stderr fallback causes rejection even with process exit0. No warning category is selectively excused. This is conservative: any stderr text stops this sealed job, not just a regex-selected warning.

### Supervisor completion and its own lifetime

`monitor_child` retains the original wall/RSS/output/archive checks and evaluates fatal events and complete stderr throughout the child lifetime and after actual exit. It does not accept a candidate merely because the worker wrote its JSON or archive. On failure the main controller stops only its owned new child process group; source/run/approval and no-retry checks remain in place.

Before writing COMPLETE, the controller performs a final clean child check, requires the candidate completion status and archive presence, and embeds the exact child's clean-exit evidence and stderr byte count. The new controller hook handles its own unraisable/thread exceptions even during or after its receipt write: it publishes `controller_fatal.jsonl`, stops only its owned child if still running, durably writes STOPPED_NO_RETRY, and exits86. Fixtures cover receipt-open, after-COMPLETE callback, late finalizer and clean return. An open buffered provisional COMPLETE is not flushed after the fatal hook's nonreturning exit overwrites it with STOPPED_NO_RETRY.

An archive made by the worker predates its finalizers and the controller's final outcome. The repair correctly says that future accepted evidence must retrieve the post-exit controller receipt, worker/controller event files, complete stderr and child clean seal separately. An archive or provisional COMPLETE viewed while the controller is still alive is not acceptance. This remains an operational requirement for any later separately authorized launcher/retriever; no such production attempt was performed here.

## Remaining limits and allowed next state

- Actual producer Linux `/proc`/RLIMIT/process-group integration, Python3.10 shutdown behavior, scientific-library imports/finalizers and real-pipeline timing/RSS/storage are unmeasured. Passing local Python3.12/3.14 artificial fixtures does not certify them. No extra smoke/profile/real-data check is silently authorized by this review.
- File-content fsync and atomic event publication protect normal process-failure observation, not universal persistence under filesystem/power failure. If durable evidence or controller rejection persistence itself fails, stderr/nonzero exit is the rejection fallback; absence of a complete rejection JSON must not be read as clean success.
- The guard is not a sandbox against arbitrary target code suppressing warnings, deleting evidence or replacing every hook. It closes the observed unraisable gap and the reviewed target lifetime boundaries. Native crashes remain failed exits; hardware/OS kill cannot promise a full JSON record.
- The old authority chain is historical. The revised digest does not inherit authority to retry R003 or execute a new job. The reused R003 run identity remains protected by existing freshness/no-retry checks. A future specific authorized run would need its exact reviewed source/config/run/authority and must verify actual controller exit before interpreting final receipts; this review neither proposes nor launches one.
- R003's original artifacts, COMPLETE receipts, ResourceWarning, explicit contract breach and caveated numerical conclusions must remain preserved. A local repair cannot retroactively make that run compliant.

**Disposition:** the requested local first-stop repair and its exact independent review are complete. Return the prepared repaired source and this receipt to HQ. No further scientific or producer work follows automatically.
