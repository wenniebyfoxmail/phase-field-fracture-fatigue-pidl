---
experiment_id: S09-E017
run_id: S09-E017-R001-factorised-head-p0
record_type: resolver_admission_only_approval_plan
status: PLAN_ONLY_REQUIRES_LOCAL_SEPARATION_IMPLEMENTATION_AND_REVIEW
remote_actions: 0
scientific_operations: 0
date: 2026-10-20
---

# S09-E017 resolver/admission-only approval plan

## Decision requested

This document is the complete approval design for a bounded
resolver/admission-only control gate. It is not an execution card and does not
contain an active authority. The immediate decision requested is only whether
to implement and independently review the local separation described in Phase
L. A later exact remote command, with real helper/plan hashes, must return for a
second explicit approval before any SSH or remote write.

## Accepted starting state

The user has accepted the deployed archive as current deployment state while
preserving the authorization-provenance incident as invalid. The accepted
identity is:

| item | frozen value |
|---|---|
| planned scientific Run | `S09-E017-R001-factorised-head-p0` |
| archive path | `/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control/code.tar.gz` |
| archive bytes | `14,359,316` |
| archive SHA256 | `4ece34be786fc85bb9655c076c13c45d276d08dfde405a8fb1367e4b49ffdd22` |
| archive/control-code commit | `2002538d9a30c8d4006ccaff5959cd214958fc82` |
| final execution candidate SHA256 | `4c1e928274f6fbee134ff540345844260cf16675727d0e996abb0054062ddcf1` |
| frozen package config SHA256 | `46c0cc6b9c5dcc62794845a20502a2eaa98c7ce7dd05b423a6b00a3d1784a2e6` |
| packet manifest identity, recorded only | `1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6` |
| B25 checkpoint identity, recorded only | `24bbea271fe3c2df79913f552dde863e495d33df963e0db9586b4920904dcf05` |
| expected host | `GPUServer8` via `gpu-taobo` |
| expected remote identity | user `drtao`, uid `1010` |
| expected GPU | index 5, UUID `GPU-5622bd47-1050-3003-246d-3cabe2b4791b` |

The archive observations come from the completed deployment receipt and are not
refreshed by preparing this plan. The accepted state is recorded separately in
`deployment_state_acceptance_20261020.md`.

This control attempt would belong to the same planned E017 scientific Run, but
it would be a separate control-plane attempt. It would use its own
`admission_only_attempt_id` and its own write-once receipt directory. It would
not consume or create the scientific Run's `admission_attempt.json`, would not
create an E017 output tree, and would not make the Run scientifically started.
E010 remains a closed historical input checkpoint source and is not rerun.

## Static separation finding

The reviewed full-run controls cannot be used under the requested scope:

1. `scripts/resolve_s09_e017_execution.py` does no scientific I/O, but it calls
   `validate_execution_authority()`, which accepts only
   `APPROVED_FOR_ONE_ADMISSION_AND_COMPLETE_RUN`, requires
   `execution_authorized=true`, and requires both `LIVE_ADMISSION` and
   `COMPLETE_THREE_ARM_RUN`.
2. `scripts/run_s09_e017_producer.py` creates the exclusive scientific
   `admission_attempt.json`, performs the non-scientific `control_admission()`,
   writes `admission_receipt.json`, then immediately calls
   `resolve_real_bindings()` and `run_reviewed_producer()`. There is no reviewed
   stop-after-admission mode.
3. `control_admission()` checks host, cwd, archive path/size, fresh roots,
   environment and host resource metadata. It does not itself verify packet or
   checkpoint bytes, GPU UUID, model parameter/storage isolation, FAS offset,
   or empty optimizers.
4. The missing checks currently occur in the real adapter. Reaching them imports
   PyTorch/scientific modules, queries CUDA, hashes/loads the checkpoint, builds
   the packet runtime and models, builds the anchor bank with model forwards,
   and later constructs optimizers. Calling that path would exceed an
   admission-only authorization.

Therefore no existing command is eligible for execution under the requested
scope. An admission-only separation must be implemented and independently
reviewed first. This is a control-path revision; it does not change E017 losses,
physics, arms, budgets, thresholds or data.

## Phase L — local implementation and independent review

Phase L is the only action proposed for the next approval. It remains local and
performs no SSH, network probe, authority minting, scientific asset read,
CUDA initialization, runtime build, forward, autograd, optimizer construction
or training.

The implementation must add a self-contained standard-library control path:

- `source/s09_e017_admission_only.py`: canonical schemas, strict validators,
  write-once receipts and metadata-only checks;
- `scripts/resolve_s09_e017_admission_only.py`: create a disabled-for-producer
  resolved control file;
- `scripts/run_s09_e017_admission_only.py`: stop after metadata/control
  admission and never import producer or scientific modules;
- `scripts/s09_e017_admission_only_guard.py`: local one-shot outer guard for a
  later remote attempt, with one connection, one metadata transfer and a hard
  wall cap;
- focused synthetic/no-network tests proving prohibited imports and calls are
  unreachable.

The new authority schema must be distinct from the one-run schema and require:

```text
schema_version: s09-e017-resolver-admission-only-authority-v1
approval_status: APPROVED_FOR_ONE_RESOLVER_AND_ADMISSION_ONLY
execution_authorized: false
producer_authorized: false
allowed_actions:
  - STAGE_REVIEWED_ADMISSION_ONLY_HELPER
  - RESOLVE_ADMISSION_ONLY_CONTROL
  - RUN_METADATA_ADMISSION_ONLY
maximum_connection_attempts: 1
maximum_metadata_transfers: 1
retry: false
reconnect: false
alternate_host: false
alternate_gpu: false
scientific_asset_content_reads: false
```

It must also bind a unique attempt ID, the accepted archive path/bytes/SHA256,
the final candidate SHA256, accepted control commit `2002538d...`, the exact
reviewed helper and plan hashes, the local and remote receipt paths, all budgets
below, `granted_by=user`, and a timezone-aware grant time. Merely preparing the
schema must not create a granted authority.

The admission-only resolved config must remain
`execution_authorized=false`, `producer_authorized=false`, contain no action
named `COMPLETE_THREE_ARM_RUN`, and have no producer entrypoint. The admission
CLI must fail if `torch`, `numpy`, `s09_e017_real_adapter`, a packet loader,
runtime builder, model, optimizer or CUDA library is imported or invoked.

Independent Code Ready review must bind one exact commit and verify at least:

- full-run authority cannot satisfy the admission-only schema and vice versa;
- exact candidate/archive/helper/plan bindings;
- write-once local consumption before networking;
- exclusive remote attempt token and terminal receipt coverage;
- no scientific token, authority, output or archive-root creation;
- no packet/checkpoint content open, mmap, deserialization or hash read;
- no producer/scientific import, runtime build, forward, autograd, backward,
  optimizer construction or optimizer step;
- first-stop behavior for every identity, resource, GPU metadata, path,
  connection, transfer and receipt failure;
- no retry, reconnect, resume, alternate host/GPU or cleanup.

Only after an exact Code Ready verdict may the owner fill the placeholders in
Phase R and ask the user for the separate remote approval.

## Phase R — proposed one-shot remote resolver/admission-only attempt

Phase R is design only. It is not approved by approval of Phase L.

### Allowed reads

The reviewed helper may read only:

- authority, final candidate and frozen package JSON control files;
- Git `HEAD` and tracked status for the accepted code root;
- archive stat and all 14,359,316 archive bytes solely to recompute SHA256;
- host/platform/uid/cwd/process metadata;
- filesystem existence/type/size metadata for the packet directory, base config
  and B25 checkpoint path, without opening their contents;
- free-disk and control/tmp/cache/output/archive path metadata;
- two `nvidia-smi` metadata queries: GPU identity/usage and compute-process list.

It may not open any packet payload, packet manifest content, base runtime config
content, checkpoint bytes, field, target, FEM array, holdout, model weight or
scientific output. Consequently a pass cannot claim that the recorded packet or
checkpoint SHA256 is still current. Those identities remain explicitly
unverified until a separately authorized producer prelaunch.

It may not import PyTorch/NumPy/scientific modules, initialize CUDA, build a
runtime/model, resolve real bindings, construct an optimizer, or perform a
forward, autograd, backward, evaluation or update.

### Allowed writes

The only remote writes are:

```text
/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control/
  admission_only_helpers/<reviewed-helper-sha-prefix>/...
  admission_only_attempts/<attempt-id>/attempt.json
  admission_only_attempts/<attempt-id>/config_resolved_admission_only.json
  admission_only_attempts/<attempt-id>/resolution_receipt.json
  admission_only_attempts/<attempt-id>/admission_only_receipt.json
  admission_only_attempts/<attempt-id>/admission_only_failure_receipt.json
```

The matching local evidence root is:

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/
  S09-E017/admission_only_attempts/<attempt-id>/
    admission_only_authority.json
    authority_consumption_receipt.json
    guard_receipt.json
    stdout.log
    stderr.log
```

The outer guard writes its receipt and captured stdout/stderr even when the
remote token was never created. All five local paths and all remote receipt
paths must be fresh and bound by the later authority.

The helper/authority metadata transfer is capped at 1 MiB. Writes use
no-overwrite or exclusive-create semantics. The verified archive, code root,
packet, checkpoint, production `admission_attempt.json`, execution authority,
run output root and scientific archive root are read-only or untouched.

### Resource envelope

| resource | admission-only limit |
|---|---:|
| connection attempts | 1 |
| metadata transfer invocations | 1 |
| reconnect/retry/resume | 0 |
| total wall time | 300 s |
| remote helper CPU time | 60 CPU-s |
| CPU threads | 1 |
| host RSS | 1 GiB |
| metadata transfer | 1 MiB |
| remote control receipts/helper tree | 2 MiB |
| archive bytes read | exactly 14,359,316 |
| packet/checkpoint content bytes read | 0 |
| required free `/mnt/data2` | at least 20 GiB |
| CUDA initializations | 0 |
| CUDA reserved/allocated bytes | 0 |
| model forwards/autograd/backward | 0 |
| optimizer constructions/steps | 0 |
| scientific output bytes | 0 |

`nvidia-smi` is allowed only for metadata. GPU UUID mismatch stops. GPU free
memory and compute-process rows are recorded; the proposed pass condition is
at least 20 GiB free and no compute process on the frozen UUID. This is a
point-in-time availability gate, not a reservation and not evidence that the
GPU will remain free.

### Ordered actions

Within the single guarded connection:

1. consume the local one-shot authority before networking;
2. establish one SSH control connection to `gpu-taobo`; no fallback;
3. stage only the reviewed admission-only helper and canonical authority under
   the allowed control helper/attempt paths;
4. exclusive-create the remote admission-only attempt token;
5. verify Linux, host `GPUServer8`, uid/user, exact code-root cwd, clean
   `2002538d...` checkout and the absence of production authority/resolution/
   admission/output/scientific archive paths;
6. verify the accepted archive path, exact size and SHA256;
7. validate the candidate/package control JSON identities;
8. check control/tmp/cache paths, free disk, CPU/RSS/tree caps and environment;
9. record packet/checkpoint/base-config path metadata without opening contents;
10. query and validate GPU5 UUID and record point-in-time availability;
11. write exactly one admission-only success receipt, or the earliest writable
    failure receipt;
12. close the connection and stop.

A success terminal state is
`ADMISSION_ONLY_METADATA_READY__SCIENTIFIC_IDENTITIES_UNVERIFIED`. It is not
`ADMISSION_READY`, does not consume the production admission token, and does
not authorize or launch producer work.

### Intended exact command interface after Phase L review

The final command must preserve this interface; the owner will replace the
angle-bracket placeholders only with independently reviewed exact identities
before seeking Phase R approval:

```bash
cd /Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s09-e007-fixed-damage-holdout-20261012

PYTHONPATH=source python3 scripts/s09_e017_admission_only_guard.py \
  --candidate docs/research/S09/S09-E017/final_execution_candidate_20261020.json \
  --candidate-sha256 4c1e928274f6fbee134ff540345844260cf16675727d0e996abb0054062ddcf1 \
  --accepted-control-commit 2002538d9a30c8d4006ccaff5959cd214958fc82 \
  --accepted-archive-path /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control/code.tar.gz \
  --accepted-archive-bytes 14359316 \
  --accepted-archive-sha256 4ece34be786fc85bb9655c076c13c45d276d08dfde405a8fb1367e4b49ffdd22 \
  --authority <NEW_CANONICAL_ADMISSION_ONLY_AUTHORITY.json> \
  --helper <EXACT_REVIEWED_ADMISSION_ONLY_HELPER> \
  --helper-sha256 <EXACT_REVIEWED_HELPER_SHA256> \
  --plan scripts/s09_e017_admission_only_plan.sh \
  --plan-sha256 <EXACT_REVIEWED_PLAN_SHA256> \
  --receipt <NEW_WRITE_ONCE_LOCAL_GUARD_RECEIPT.json> \
  --execute-authorised-admission-only
```

The command is deliberately non-executable now because the required separation
implementation, independent verdict, hashes and a fresh user authority do not
exist. No placeholder may be inferred or filled opportunistically.

## First-stop and post-failure rules

The first connection, transfer, identity, path, resource, archive, GPU metadata,
prohibited-read/import/call, receipt or wall-time failure stops the whole
attempt. The guard terminates only its task-owned process group on wall expiry.
It does not retry, reconnect, resume, choose another host/GPU, enter producer,
clean remote paths, delete partial helper files or alter the accepted archive.

Local and remote attempt/receipt files are preserved. A partial helper transfer
is marked `PRE_ADMISSION_ONLY_STAGING_STOPPED`; a token followed by failure is
`ADMISSION_ONLY_STOPPED`; success is the bounded metadata state above. Unknown
post-failure remote state remains unknown until separately authorized; no
follow-up probe is implied.

## Approval sequence

1. **Approval L, requested now:** implement and independently review the local
   admission-only separation. No remote action or scientific I/O.
2. **Approval R, requested later:** after exact Code Ready commit/helper/plan
   hashes are available, display a fully instantiated command and canonical
   one-shot authority for explicit user approval. Only then may the single
   remote metadata/control attempt occur.
3. Any producer, scientific-asset content read, production admission token,
   CUDA initialization, runtime/model/optimizer construction, forward/autograd,
   update, holdout or training remains a separate later decision.
