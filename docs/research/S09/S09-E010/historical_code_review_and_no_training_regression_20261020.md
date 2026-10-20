---
experiment_id: S09-E010
run_id: S09-E010-R001-support-amplitude-three-arm
record_type: historical_exact_commit_review_and_no_training_regression
status: HISTORICAL_RECORD_VERIFIED_NO_SCIENCE_CHANGE
reviewed_commit: 010281be8045301f7e56b938de82969982c89bc9
date: 2026-10-20
---

# S09-E010 historical exact-commit review and no-training regression

## Purpose

Close the owner record for the exact historical producer commit without opening
scientific arrays, rerunning the producer, reading a fresh holdout, or changing
the frozen E010 result. This addendum records an independent source-diff review
and a bounded no-training regression rerun only.

## Independent source-diff review

An independent Codex review examined the exact diff from
`ded694d665000ed8db248f2dc96110e062ef07d8` to
`010281be8045301f7e56b938de82969982c89bc9` and returned `CODE_READY` for that
historical commit. The review confirmed closure of the four original producer
blockers:

1. resolved projection preserves the frozen packet SHA;
2. any arm-level `EXECUTION_FAILED` produces a global first stop;
3. the producer identity binds `s09_e009_four_arm.py`;
4. the full replay trace and per-arm/cumulative update counts are preserved
   before a stop.

It also checked strict persisted-receipt validation, counting the current arm
when receipt close fails, and shared-identity priority over method status. The
empty scientific-input diff confirmed that losses, protocol, thresholds and
scientific inputs did not change; those elements were not re-reviewed. This
verdict does not cover later E015 changes to the shared `evaluate_arm` helper.

## No-training regression evidence

The approved regression used a Git-exported snapshot of the exact historical
commit. All 63 exported source, test and small contract files were byte-compared
with Git before testing. A single CPU-only, single-thread pytest invocation
covered six files:

- E010 support/amplitude core: 17 passed;
- E010 runner integration: 14 passed;
- E010 producer: 16 passed;
- E009 four-arm core: 20 passed;
- E009 runner integration: 25 passed;
- E009 producer: 25 passed.

The total was **117 passed in 5.21 seconds**, with zero failed and zero skipped.
Real optimiser-step attempts and CUDA-initialisation attempts were both zero.
The suite used only generated 9-node/4-element fixtures, toy tensors and mocks;
it did not open a real packet, weights, scientific arrays or holdout data and
did not start a producer.

Pytest exited zero. The deliberately strict audit wrapper exited one because it
blocked three optional dependency probes: `/proc/self/maps`, `uname -p`, and
`system_profiler -xml SPFontsDataType`. An import-only reproduction observed
exactly those three events. The allowlist was not relaxed and the suite was not
rerun. This wrapper status is an audit-boundary result, not a pytest failure.

The exact preserved evidence is in
`evidence/no_training_regression_010281be_20261020/`. Its source-file SHA256
values are:

- `README_regression.md`: `0d40bc005a221243f6a3265f3de37660d729b2857e323477e2df15f60824fffe`;
- `regression_receipt.json`: `8f4c005be61aefb98f433d012248deb2ccd731fd3451713d99badd97b7352508`.

## Old Run status and disposition

The original `S09-E010-R001-support-amplitude-three-arm` execution remains a
completed, retrieved and independently reviewed historical Run:

- all three arms completed 500 updates, for 1,500 total optimiser steps;
- shared identity and the exact A25 replay gate passed;
- all 28 retrieved files matched the remote manifest;
- the result-evidence package received `RESULT_EVIDENCE_READY_PASS`;
- the frozen scientific status remains `NO_TARGETED_RANKING_SIGNAL`.

The graded conclusion is unchanged: B25 preserved the protected metrics and
beta 0.25 supplied conditional equilibrium control, but B25 did not improve
the target amplitude ranking over A25. The old Run is closed and must not be
reused as authority for any new execution.

## Current route

Do not rerun E010. The research route has already advanced through E011--E016
to the E017 factorised amplitude-times-shape pilot. This historical code review
and regression strengthen the provenance of the old implementation; they do
not change its scientific conclusion and do not authorize any producer,
holdout or rollout action.
