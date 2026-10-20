---
experiment_id: S09-E017
run_id: S09-E017-R001-factorised-head-p0
status: EXACT_CANDIDATE_UNDER_INDEPENDENT_CODE_REVIEW
candidate_commit: 982249f9b4d542833fbddc120995c8c7673217e2
remote_actions: 0
scientific_operations: 0
date: 2026-10-20
---

# S09-E017 admission-only separation implementation status

## Implemented boundary

Exact candidate `982249f9b4d542833fbddc120995c8c7673217e2` implements the
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
| admission-only candidate JSON | `5dae58ab39502f0b9af9c055b1d2a7470980f4ddc46b5d72a05a799bd7e8ed2b` |
| disabled authority template | `727f81c95082e115b174c46ee97478da3bd014dedcaa6d6e1efcb649ba216793` |
| outer guard | `a7c4f2768dcf124369e7cc0ed02c214397b75dd17c084db79c01f536d55d10a7` |
| finite shell plan | `7b7dec1d63c8aff65dbcb3325512cea816e5ef252daa030cb228eb412173ea1c` |
| standard-library core | `838b557aa289c6163a1eb313286b793e44b0ab9dc817e54f6f6de3d31143e7d4` |
| resolver CLI | `1858ce5e9fbd5ba744e5cb7cd5af1b5b4d3c3337e69bcf3a56b5f99bf30191a5` |
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

- focused admission-only suite: `23 passed in 0.04s`;
- adjacent admission-only + existing execution-control + producer-package
  synthetic suite: `64 passed in 0.22s`;
- Ruff: pass;
- Ruff format check: pass;
- `py_compile`: pass;
- `bash -n`: pass;
- `git diff --check`: pass;
- fresh standard-library import: banned scientific modules `[]`.

Tests cover disabled/full-run authority rejection, scope expansions, exact
hashes, nonexecuting resolved config, scientific-file metadata without open,
GPU UUID/free-memory/process conditions, exclusive attempt token, guard
single-consumption/replay conflict, nonzero terminal stop, explicit enable flag,
prohibited imports/calls, one connection/one rsync and authority-swap rejection.

## Not performed and next gate

No granted authority was created. No SSH, DNS/network probe, remote file write,
real packet/checkpoint content read, CUDA, model, optimizer, producer or
training occurred. The exact candidate is under independent read-only Code
Ready review. A PASS would make it eligible only for a fully instantiated Phase
R card and a new user approval; it would not itself authorize remote action.
