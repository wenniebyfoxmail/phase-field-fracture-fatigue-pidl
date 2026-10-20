---
experiment_id: S09-E017
run_id: S09-E017-R001-factorised-head-p0
review_scope: resolver_admission_only_separation
verdict: E017_ADMISSION_ONLY_CODE_READY_PASS
reviewed_commit: a8bb84f730dccae8b822ca7bd653b428354bf118
remote_actions: 0
scientific_operations: 0
date: 2026-10-20
---

# S09-E017 admission-only final code review

The independent reviewer returned `E017_ADMISSION_ONLY_CODE_READY_PASS` for
exact commit `a8bb84f730dccae8b822ca7bd653b428354bf118`.

The first review of `982249f9b4d542833fbddc120995c8c7673217e2`
returned `E017_ADMISSION_ONLY_REVISE`. The repaired exact commit closes all
three reproduced blockers:

1. the remote runner is invoked through an stdin shell whose argument, cwd and
   environment binding survives OpenSSH-style command concatenation;
2. the archive is content-read exactly once in the resolver for 14,359,316
   bytes, with before/after file identity carried into admission; admission
   performs only `lstat` and does not reopen the archive content;
3. after local authority consumption, process start, communication and log
   persistence failures preserve first-stop evidence and attempt a minimal
   write-once guard receipt with `retry=false` and `reconnect=false`.

The reviewer independently ran 27 focused tests and additional injected
communication plus stdout-write failure cases. Candidate, helper, guard and
plan identities match; the disabled authority remains canonical. Execution,
producer and scientific-content-read permissions remain false.

This verdict is Code Ready only. No SSH, remote metadata check, scientific
asset read, CUDA initialization, producer or training was performed. It does
not grant Phase R or validate current remote state.
