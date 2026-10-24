---
experiment_id: S09-E017
run_id: S09-E017-R001-factorised-head-p0
attempt_id: s09e017-admissiononly-20261024T200408
status: PRE_RESOLVER_STAGING_STOPPED_AUTHORITY_PATH_MISSING_NO_RETRY
scientific_operations: 0
date: 2026-10-24
---

# S09-E017 admission-only attempt stop

The user approved the bounded resolver/admission-only card. A fresh canonical
authority was created at `2026-10-24T20:04:08+01:00`, SHA256
`8bcabe29ed84944b926fe3feb1e29369c9f1cf439b18ff726cdc98e9f2e7ec7a`,
and was consumed once before networking.

The single connection reached `GPUServer8`. The pre-transfer control check
reported uid 1010, clean commit
`2002538d9a30c8d4006ccaff5959cd214958fc82`, and no blocked production paths.
After the only metadata transfer, the staged-byte verifier stopped with
`authority missing`. The guard returned exit code 1 after 7.072 seconds and
wrote complete local consumption, stdout, stderr and guard receipts. It did not
reconnect or retry.

Resolver, remote admission-only attempt token, archive read, packet/checkpoint
metadata checks, CUDA, model, producer and training were never reached. All
scientific counters remain zero. The attempt cannot support a remote admission
or scientific conclusion.

Local rsync reproduction showed that the reviewed macOS rsync preserved the
full absolute `Users/...` authority path despite the `/./` cut-point form,
instead of placing `admission_only_authority.json` at the helper root expected
by the verifier. Repair commit
`500af64b8dbbf6ad0805708e4fda333e5b9e29e5` constructs an exact local staging
tree and transfers that tree once. Its focused benchmark reports 28 passed; it
received the independent verdict `E017_ADMISSION_STAGING_REPAIR_PASS` for exact
commit `500af64b8dbbf6ad0805708e4fda333e5b9e29e5`.

This consumed authority remains closed. Any new remote attempt requires a fresh
authority; the code repair and review do not themselves authorize a retry.
