# Performance preparation review v3

REVIEW_PASS — preparation static/API scope only. No runtime/producer-ready verdict.

Exact commit `5bb172149b94788599cfc351cbe2fe7788710dc8`; artifact `5742e4c79bd136e7dfcdaff4188721823be06073a8e1dac980158783d8198d1d`; actual unchanged preparation card SHA `23d79fe5c06c9f36a1a63fc8882ff4e6b557988c1a70b38cedf9b84ad329b574`. All39 immutable git-object file hashes and canonical artifact identity match. Exact exported package:61 artificial unit/interface checks passed in3.15s, exit0. Prior v1/v2 MODIFY receipts remain preserved.

The remaining G1_EXIT is resolved. `tools/hybrid_deadline_guard.py:57–65` drains IPC again at worker exit, preserves malformed/late-message failures, checks phase deadline, then rejects any unmatched active step with `incomplete step completion at worker exit`. Artificial start1/no-done/exit30 and done1/start2/no-done2/exit cases both fail with the correct outstanding step. Timely completion still passes; late completion still fails;120s and all physical/quality limits are unchanged.

Downstream `run_owned_worker` still rejects any nonnull guardian reason or nonzero return code and always cleans its owned worker. This new terminal reason cannot be promoted into successful phase/pipeline completion. No partial fit/resume path was added. v2 null/observed resource semantics and thickness-correct energy are unchanged; other reviewed mechanics/cache, fresh physical acceptance, matched quality, sealed diagnostics and trace scopes carry forward.

No remaining decisive finding within this focused preparation delta. The card remains execution_enabled=false with null RunID/roots; originalR1 remains stopped. Linux pidfd/runtime, full native mesh operator/cache parity, real memory/IO costs, full-path performance and budget capacity remain unverified. No producer execution or retry authority is granted. No scientific array/model/holdout access, SSH/profile/preflight, real-state solve, training or retry occurred.
