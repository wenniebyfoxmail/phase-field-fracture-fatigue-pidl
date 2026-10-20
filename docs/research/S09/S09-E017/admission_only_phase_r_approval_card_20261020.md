---
experiment_id: S09-E017
run_id: S09-E017-R001-factorised-head-p0
record_type: admission_only_phase_r_approval_card
status: COMPLETE_REVIEWABLE_PROPOSAL_NOT_GRANTED_NOT_EXECUTED
reviewed_commit: a8bb84f730dccae8b822ca7bd653b428354bf118
remote_actions: 0
scientific_operations: 0
date: 2026-10-20
---

# S09-E017 bounded resolver/admission-only approval card

## Decision proposed

Approve materializing the exact canonical authority payload shown below and
executing the exact command once. This would authorize one control-plane SSH
connection and one metadata transfer for resolver plus admission-only checks.
It would not authorize a producer, training, CUDA initialization, scientific
asset content reads, a production admission token, retry or reconnect.

This card is currently inactive. The executable authority file and its local
evidence directory do not exist. The existing authority template remains
`NOT_GRANTED`; preparing this card consumed no authority and performed no
remote action.

## Bounded task authority

One explicit approval of this complete card covers the admission-only task as
a whole: materializing the authority, one local mechanical consistency pass,
filling machine-derived paths/hashes/receipts, and launching the one guarded
remote attempt when the checks pass. It does not require another approval just
because a hash, environment value or fresh receipt path is mechanically
resolved.

The local mechanical recheck is capped at one pass and 60 seconds before
authority consumption. In-scope implementation defects discovered before
consumption may be repaired and retested automatically; a changed control risk
receives focused review through the already selected independent Codex channel.
Pure hash/path/card instantiation receives consistency checks only. All actual
identities are recorded in the authority and receipts.

The human boundary is a change to the envelope: scientific-content access,
producer/training authority, a different host/GPU, a larger budget, or a retry
after this one-shot authority has been consumed. The explicit one-connection,
no-reconnect and no-scientific-retry limits remain unchanged.

## Exact reviewed identities

| item | frozen identity |
|---|---|
| Code Ready commit | `a8bb84f730dccae8b822ca7bd653b428354bf118` |
| verdict | `E017_ADMISSION_ONLY_CODE_READY_PASS` |
| admission-only candidate | `d8c1748463270ea8dce0fa512ae32920d5018b90b3cfe1499e951dbddd364033` |
| disabled template | `5ca28357236b576000739bfdb9005211dc2706304b8b296ff4a36752a8e90c20` |
| outer guard | `5a97784a3a7a2b002a34dcc17484f0beac4667f082c341502e7116025ec0ba6f` |
| finite plan | `56ced032e9c52cefc355da865efb1dac19d7bd517264f9a57b6b65512bca1f4b` |
| control core | `d45710c7657f8d70cfa8cbced3bb28e7b258f4d7d32b77f0ed9de2894392d98d` |
| resolver | `eacf9e4c961cd474cf6748329f334d14ac4c1ab052f21cbf402f21573276ea1e` |
| runner | `04f73b97de7a66a85a826b6a3b535caa4892d6d47eaf175cf82dcf06b37364ea` |
| accepted archive | 14,359,316 bytes; `4ece34be786fc85bb9655c076c13c45d276d08dfde405a8fb1367e4b49ffdd22` |
| accepted remote commit | `2002538d9a30c8d4006ccaff5959cd214958fc82` |
| planned host | `gpu-taobo` / `GPUServer8` / `drtao` uid 1010 |

## Proposed one-shot authority

Proposed attempt ID:
`s09e017-admissiononly-20261020T190844`.

If this card is explicitly approved and the bounded mechanical recheck leaves
the current identities unchanged, the owner would materialize the following
single canonical JSON line at
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S09-E017/admission_only_attempts/s09e017-admissiononly-20261020T190844/admission_only_authority.json`.
Its SHA256 would be
`53659e52e815c6801fda6e2be811f6c873da5053938d09e2f48dcdf5b8be0c86`.
If only machine-derived identity fields change during the permitted recheck,
the owner records the new canonical payload and SHA in the same task without a
new management approval; the scientific and execution envelope may not change.

```json
{"accepted_archive_bytes":14359316,"accepted_archive_path":"/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control/code.tar.gz","accepted_archive_sha256":"4ece34be786fc85bb9655c076c13c45d276d08dfde405a8fb1367e4b49ffdd22","accepted_control_commit":"2002538d9a30c8d4006ccaff5959cd214958fc82","admission_only_attempt_id":"s09e017-admissiononly-20261020T190844","allowed_actions":["STAGE_REVIEWED_ADMISSION_ONLY_HELPER","RESOLVE_ADMISSION_ONLY_CONTROL","RUN_METADATA_ADMISSION_ONLY"],"alternate_gpu":false,"alternate_host":false,"approval_status":"APPROVED_FOR_ONE_RESOLVER_AND_ADMISSION_ONLY","budgets":{"archive_read_bytes":14359316,"cpu_threads":1,"cuda_bytes":0,"cuda_initializations":0,"host_rss_bytes":1073741824,"metadata_transfer_bytes":1048576,"minimum_free_disk_bytes":21474836480,"packet_checkpoint_content_bytes":0,"remote_control_tree_bytes":2097152,"remote_cpu_seconds":60,"scientific_output_bytes":0,"wall_seconds":300},"candidate_sha256":"d8c1748463270ea8dce0fa512ae32920d5018b90b3cfe1499e951dbddd364033","execution_authorized":false,"granted_at":"2026-10-20T19:08:44+01:00","granted_by":"user","guard_sha256":"5a97784a3a7a2b002a34dcc17484f0beac4667f082c341502e7116025ec0ba6f","helper_manifest":{"scripts/resolve_s09_e017_admission_only.py":"eacf9e4c961cd474cf6748329f334d14ac4c1ab052f21cbf402f21573276ea1e","scripts/run_s09_e017_admission_only.py":"04f73b97de7a66a85a826b6a3b535caa4892d6d47eaf175cf82dcf06b37364ea","source/s09_e017_admission_only.py":"d45710c7657f8d70cfa8cbced3bb28e7b258f4d7d32b77f0ed9de2894392d98d"},"local_evidence_root":"/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S09-E017/admission_only_attempts/s09e017-admissiononly-20261020T190844","maximum_connection_attempts":1,"maximum_metadata_transfers":1,"plan_sha256":"56ced032e9c52cefc355da865efb1dac19d7bd517264f9a57b6b65512bca1f4b","producer_authorized":false,"reconnect":false,"remote_attempt_root":"/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control/admission_only_attempts/s09e017-admissiononly-20261020T190844","retry":false,"run_id":"S09-E017-R001-factorised-head-p0","schema_version":"s09-e017-resolver-admission-only-authority-v1","scientific_asset_content_reads":false}
```

## Exact command proposed

```bash
cd /Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s09-e007-fixed-damage-holdout-20261012

PYTHONPATH=source python3 scripts/s09_e017_admission_only_guard.py \
  --candidate docs/research/S09/S09-E017/s09_e017_admission_only_candidate_20261020.json \
  --candidate-sha256 d8c1748463270ea8dce0fa512ae32920d5018b90b3cfe1499e951dbddd364033 \
  --authority /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S09-E017/admission_only_attempts/s09e017-admissiononly-20261020T190844/admission_only_authority.json \
  --plan scripts/s09_e017_admission_only_plan.sh \
  --plan-sha256 56ced032e9c52cefc355da865efb1dac19d7bd517264f9a57b6b65512bca1f4b \
  --execute-authorised-admission-only
```

## Reads, writes and budget

The attempt may read control JSON, Git identity/status, host/filesystem
metadata, one full 14,359,316-byte archive stream for SHA256, and two
`nvidia-smi` metadata views. Packet, base-runtime and B25 checkpoint contents
remain unopened; only their path/type/size metadata may be read.

Remote writes are limited to the reviewed helper tree and the unique
`control/admission_only_attempts/s09e017-admissiononly-20261020T190844/`
receipts. Local writes are limited to the matching evidence directory. It must
not create or alter the production admission token, run output, scientific
archive, accepted code archive, packet or checkpoint.

The caps are one connection, one transfer no larger than 1 MiB, 300 seconds
wall time, 60 remote CPU-seconds, one CPU thread, 1 GiB RSS, 2 MiB helper plus
receipt tree, at least 20 GiB free disk, zero scientific content bytes, zero
CUDA bytes/initializations, zero model forwards/autograd/optimizers/steps and
zero scientific output bytes.

## First-stop and result interpretation

Any connection, transfer, identity, path, resource, archive, GPU metadata,
prohibited operation, receipt or wall-time failure stops the attempt. There is
no retry, reconnect, resume, fallback host/GPU or cleanup. Partial evidence is
preserved, and unknown remote state remains unknown without a new approval.

The only success terminal state is
`ADMISSION_ONLY_METADATA_READY__SCIENTIFIC_IDENTITIES_UNVERIFIED`. It proves a
bounded metadata/control preflight at that moment. It does not verify packet or
checkpoint hashes, reserve the GPU, authorize producer work or start the
scientific run.
