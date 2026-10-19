# Performance preparation review v1

MODIFY_AND_REREVIEW — preparation static/API scope only.

Commit `1fdf5117efa01dd654fa6542a003c91858272893`; artifact `efebabaa0da61394bb514ef806d80a06e0f888f7308ad143f6c124f3651fa963`; preparation card SHA `23d79fe5c06c9f36a1a63fc8882ff4e6b557988c1a70b38cedf9b84ad329b574`. All37 exact git-object file hashes and canonical artifact identity match. Exported frozen objects:55 artificial unit/interface checks passed in3.17s, exit0. No real arrays/models, Linux admission, SSH/profile, scientific solve, training or retry.

## Required corrections

1. **G1/P2 — queued timely completion can be falsely timed out.** `tools/hybrid_deadline_guard.py:18–25` checks the old active step's deadline before draining IPC. Deterministic controller substitution: started0, queued done.finished119.99, guardian resumes120.01; result is `physical-substep120s deadline` without reading done. Drain ordered IPC before deciding the still-active step's deadline, including exit handling; late finished times must continue to fail. Test timely queued completion/new-start, late/missing completion and exit cases. This is an ordering defect independent of future Linux runtime validation.
2. **G2/P2 — missing peaks still look like measured zero.** `tools/run_hybrid_producer.py:129–178` initializes peaks0 and returns/writes them without observation flags. Artificial already-exited worker returns RAM0/GPU0/storage{} despite no sample. Shared usage fixes loss of measured peaks, but needs null/observed/sample-count/per-resource last-success semantics for absent samples and explicit GPU-not-applicable semantics.

## Scoped nonblocking API correction

**G3/P2:** `source/hybrid_diagnostics.py:26–27` energy integrals omit thickness. Identical artificial one-Q4 fields at thickness1/2 both report total0.09342180668978209; physical integral should scale. Frozen thickness1 card is unaffected. Multiply energy weights by thickness or explicitly label per-unit-thickness energies, and add a nonunit-thickness check. Keep area-based RMS and fractions unchanged.

## Delta accepted subject to those corrections

Warm own-path u/BC projection and trace seeding preserve a releasable mechanical space. Fixed geometry/material tensors and CSR structure are reused; numeric LU is keyed by exact freeDOFs/current CSC bytes, with material-change rejection and no claimed symbolic caching. Independent uncached final mechanics and unchanged fresh force/KKT/history acceptance remain. No scientific benefit follows from these passing artificial checks.

R1 now has a gated stdlib worker startup and independent Linux pidfd/IPC controller; signal-before-report and owned cleanup are present, but G1 prevents declaring closure. R2 preserves measured peaks on exceptions, but G2 remains. R3 is closed for this static scope: classical and neural both must satisfy unchanged quality before joint acceleration. R4 now produces common sealed diagnostics/maps and persistent nested block start/end evidence; no online reference leakage or primary-threshold rescue was introduced. G3 bounds generic energy API accuracy.

The preparation schema/false execution flag/null roots prohibit execution.6h/6h GPU allocation is a proposal within12h, not an approved executable budget. Actual Linux protocol/runtime, real mesh assembly/RAM/cost, complete labels/paths and speed/field outcomes remain unverified. No producer-ready receipt or R1 restart permission is issued. Future review should focus corrected diffs rather than repeat the frozen design.
