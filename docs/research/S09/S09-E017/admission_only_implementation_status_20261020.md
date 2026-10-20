---
experiment_id: S09-E017
run_id: S09-E017-R001-factorised-head-p0
status: REPAIRED_EXACT_CANDIDATE_UNDER_INDEPENDENT_REREVIEW
candidate_commit: a8bb84f730dccae8b822ca7bd653b428354bf118
remote_actions: 0
scientific_operations: 0
date: 2026-10-20
---

# S09-E017 admission-only separation implementation status

## Implemented boundary

Exact repaired candidate `a8bb84f730dccae8b822ca7bd653b428354bf118` implements the
locally approved Phase L separation. It adds a standard-library-only control
module, a nonexecuting resolver, a stop-after-metadata admission runner, a
finite outer guard, one bounded shell plan and focused synthetic tests.

The resolved control keeps `execution_authorized=false` and
`producer_authorized=false`. It has no `COMPLETE_THREE_ARM_RUN` action or
producer entrypoint. The remote runner stops after an admission-only receipt and
cannot call the real adapter or producer.

## Exact identities

| item | SHA256 |
|---|---|
| admission-only candidate JSON | `d8c1748463270ea8dce0fa512ae32920d5018b90b3cfe1499e951dbddd364033` |
| disabled authority template | `5ca28357236b576000739bfdb9005211dc2706304b8b296ff4a36752a8e90c20` |
| outer guard | `5a97784a3a7a2b002a34dcc17484f0beac4667f082c341502e7116025ec0ba6f` |
| finite shell plan | `56ced032e9c52cefc355da865efb1dac19d7bd517264f9a57b6b65512bca1f4b` |
| standard-library core | `d45710c7657f8d70cfa8cbced3bb28e7b258f4d7d32b77f0ed9de2894392d98d` |
| resolver CLI | `eacf9e4c961cd474cf6748329f334d14ac4c1ab052f21cbf402f21573276ea1e` |
| admission-only runner | `04f73b97de7a66a85a826b6a3b535caa4892d6d47eaf175cf82dcf06b37364ea` |

The candidate also binds the accepted archive path, 14,359,316-byte size and
SHA256 `4ece34be...dd22`, accepted control commit `2002538d...`, full-run
candidate SHA256 `4c1e9282...cf1` and package SHA256 `46c0cc6b...a2e6`.

## Data and computation boundary

Permitted later remote reads are limited to control JSON, Git metadata, host and
filesystem metadata, two `nvidia-smi` metadata queries, and one full sequential
read of the accepted code archive for SHA256. Packet directory, base runtime
config and B25 checkpoint receive only `lstat`/type/size metadata checks. Their
contents are not opened or hashed. A success receipt therefore states
`ADMISSION_ONLY_METADATA_READY__SCIENTIFIC_IDENTITIES_UNVERIFIED`.

The module imports no PyTorch or NumPy. A fresh `python -S` import reported an
empty banned-module set. The control path contains no real-binding resolver,
producer entrypoint, CUDA initialization, runtime/model build, forward,
autograd, optimizer construction or training path.

## Local verification

- focused admission-only suite: `27 passed in 0.20s`;
- adjacent admission-only + existing execution-control + producer-package
  synthetic suite: `68 passed in 0.41s`;
- Ruff: pass;
- Ruff format check: pass;
- `py_compile`: pass;
- `bash -n`: pass;
- `git diff --check`: pass;
- fresh standard-library import: banned scientific modules `[]`.

Tests additionally reproduce the initial review blockers: OpenSSH-style command
concatenation into the stdin shell, one counted 14,359,316-byte archive read
across resolver and admission, no archive content reopen in admission, and
post-consumption process-start/log-write failure receipts.

## Independent review rounds

The first review bound to `982249f9b4d542833fbddc120995c8c7673217e2`
returned `E017_ADMISSION_ONLY_REVISE`. It reproduced three blockers: broken
remote `bash -c` argument binding, two full archive reads, and missing terminal
guard evidence after process-start or log-write failure.

Repair commit `a8bb84f730dccae8b822ca7bd653b428354bf118` replaces the
remote command with an stdin script, carries the resolver's single archive
verification plus before/after stat identity into admission, and writes a
minimal terminal guard receipt after post-consumption failures. The same
reviewer is performing an exact-commit rereview. This is not yet a PASS.

## Not performed and next gate

No granted authority was created. No SSH, DNS/network probe, remote file write,
real packet/checkpoint content read, CUDA, model, optimizer, producer or
training occurred. The repaired exact candidate is under independent read-only
Code Ready rereview. A PASS would make it eligible only for a fully instantiated
Phase R card and a new user approval; it would not itself authorize remote
action.
