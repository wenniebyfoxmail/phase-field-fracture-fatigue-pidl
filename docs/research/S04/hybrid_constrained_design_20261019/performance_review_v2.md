# Performance preparation review v2

MODIFY_AND_REREVIEW — exact preparation static/API scope only.

Commit `7862d9a3f725703d8a3629bcc7f3667db2274b53`; artifact `c197cdbccada83734524bbbf4f191912f2402ec427bb2672b94435e355c7ac3e`; actual preparation card SHA `23d79fe5c06c9f36a1a63fc8882ff4e6b557988c1a70b38cedf9b84ad329b574`. All38 manifest hashes and canonical artifact verified from immutable git objects. Exact export:59 artificial unit/interface checks passed in4.14s, exit0. Original v1 review is retained.

The original queued timely-done ordering fix works: pending IPC is validated before active deadline judgment;119.99 completion passes and120.02 completion fails under the retained120s limit. Resource unknown/observed semantics now distinguish null peaks and sample counts from measured zero, preserve per-resource timestamps, and identify GPU not-applicable. Energy integrals now include thickness, with the artificial3x regression passing; thickness1 frozen contract is unchanged.

**Remaining G1_EXIT/P2:** `tools/hybrid_deadline_guard.py:57–62` accepts worker exit with `reason=None` while `active` remains unmatched if its deadline is still future. `run_owned_worker` checks reason/returncode only, so the incomplete IPC transcript is marked guard-success. This is the missing-done/worker-exit case already requested by v1 G1, not a new research criterion.

Independent artificial controls (stdlib/pidfd/socket/time replacements only): start1@0 then exit@30 without done produces reasonNone/active1; timely done1@119.99 plus start2@120 then exit@120.01 produces reasonNone/active2. Both should fail as incomplete completion. Missing done with exit@121 correctly fails the120s deadline. Require no outstanding active step after final IPC drain before clean worker-exit certification, with explicit negative regressions. Do not change timing thresholds.

No new blocker found in the three numerical/resource fixes themselves. Unchanged mechanics/physical acceptance, R3/R4 and preparation-only authority findings carry forward from v1. No actual Linux capability, full-grid parity, performance or scientific outcome was validated. No SSH/profile/preflight/real arrays/models/holdouts, scientific solve, training or retry occurred. This review grants no producer execution or R1 restart authority.
