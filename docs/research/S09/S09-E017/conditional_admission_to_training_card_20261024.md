---
experiment_id: S09-E017
run_id: S09-E017-R001-factorised-head-p0
status: STAGE1_STOPPED_GPU_BUSY_AUTHORITY_CONSUMED_STAGE2_NOT_CREATED
date: 2026-10-24
---

# S09-E017 repaired admission to conditional training card

## Decision requested

Authorize one fresh repaired admission-only attempt and, only if that attempt
returns the exact success state
`ADMISSION_ONLY_METADATA_READY__SCIENTIFIC_IDENTITIES_UNVERIFIED`, authorize one
separate final-run connection that writes one exact execution authority and
starts the already frozen three-arm run. A failure in either stage stops the
whole card. There is no retry, reconnect, resume, alternate host/GPU, parameter
change or cleanup action after a terminal failure.

This card is prepared but not granted. It does not reactivate the consumed
attempt `s09e017-admissiononly-20261024T200408`.

The independent focused verdict is
`E017_CONDITIONAL_LAUNCH_CODE_READY_PASS`, bound to exact commit
`593b05cdd04bfeb0e6d833f9bdb23c9aa0bcd29c`. The verdict covers the handoff,
detached launcher, finite guard and tests; it is not execution authority.

The two fixed new attempt IDs are
`s09e017-admissiononly-20261024-r2` and
`s09e017-final-launch-20261024-r1`. Their local evidence roots are respectively
`local_archive/experiments/S09-E017/admission_only_attempts/s09e017-admissiononly-20261024-r2`
and
`local_archive/experiments/S09-E017/final_launch_attempts/s09e017-final-launch-20261024-r1`.
The first remote attempt root is
`control/admission_only_attempts/s09e017-admissiononly-20261024-r2`; the final
launch uses the already frozen production control paths.

## Why a fresh decision is needed

The approved 2026-10-24 attempt consumed a one-shot authority that explicitly
set `retry=false` and `reconnect=false`. It reached the exact remote commit but
stopped before the resolver because the authority file was staged at the wrong
relative path. Repair and review cannot restore that consumed authority.

## Stage 1: repaired admission-only attempt

The owner will create one fresh attempt directory and authority bound to:

| item | exact identity |
|---|---|
| repair commit | `500af64b8dbbf6ad0805708e4fda333e5b9e29e5` |
| review verdict | `E017_ADMISSION_STAGING_REPAIR_PASS` |
| candidate SHA256 | `152fa2036e90d04d6aa3f7ae15b7f2c9cfebab4dabfd9d3f73be492d6771f702` |
| plan SHA256 | `df8805680dcf710e65d389165fd317933debcdf449db36436fffb44617e8105e` |
| guard SHA256 | `5a97784a3a7a2b002a34dcc17484f0beac4667f082c341502e7116025ec0ba6f` |
| accepted remote commit | `2002538d9a30c8d4006ccaff5959cd214958fc82` |
| accepted archive SHA256 | `4ece34be786fc85bb9655c076c13c45d276d08dfde405a8fb1367e4b49ffdd22` |

Limits remain: one connection attempt, one metadata transfer, 300 seconds,
1 GiB host RSS, one 14,359,316-byte sequential archive read, no packet or
checkpoint content read, no CUDA, model, forward, optimizer, producer or
training. The guard must first consume the fresh local authority and retain all
local evidence. The handoff verifier requires all of the following before the
execution authority can be consumed:

- guard state `ADMISSION_ONLY_PLAN_COMPLETED`, process exit 0, no first reason
  and no evidence-write errors;
- published stdout whose recorded SHA256 matches its bytes;
- exactly one precheck JSON record followed by one metadata receipt;
- matching attempt ID plus authority, candidate and plan hashes across the
  authority, consumption receipt, guard and metadata receipt;
- metadata state
  `ADMISSION_ONLY_METADATA_READY__SCIENTIFIC_IDENTITIES_UNVERIFIED`, exact
  archive hash/read count, and zero scientific counters.

Any mismatch stops this card before Stage 2. The reviewed handoff verifier is
`scripts/verify_s09_e017_admission_handoff.py`, SHA256
`fe9909e005518bf2af16aa460a20bc7f6b56949fa24b9c5e9c19500b77655d1a`.

## Stage 2: conditional final-run launch

Only after Stage 1 success, the owner will materialize one execution authority
with:

```json
{
  "schema_version": "s09-e017-one-run-authority-v1",
  "run_id": "S09-E017-R001-factorised-head-p0",
  "approval_status": "APPROVED_FOR_ONE_ADMISSION_AND_COMPLETE_RUN",
  "execution_authorized": true,
  "allowed_actions": ["LIVE_ADMISSION", "COMPLETE_THREE_ARM_RUN"],
  "reviewed_adapter_commit": "662005f1fde22cb9a6e8069f4e430b7190f21860",
  "reviewed_control_commit": "2002538d9a30c8d4006ccaff5959cd214958fc82",
  "candidate_config_sha256": "4c1e928274f6fbee134ff540345844260cf16675727d0e996abb0054062ddcf1",
  "code_archive_sha256": "4ece34be786fc85bb9655c076c13c45d276d08dfde405a8fb1367e4b49ffdd22",
  "maximum_launches": 1,
  "retry": false,
  "alternate_host": false,
  "alternate_gpu": false,
  "network_recovery_confirmed": true,
  "granted_by": "user",
  "granted_at": "<ISO-8601 timestamp with timezone filled after approval>"
}
```

The grant timestamp is filled only after approval. The authority is copied once
with exclusive-create semantics to `control/execution_authority.json`. Its
SHA256 is recorded in the local consumption and guard receipts, outside the
strict authority schema. The second and final connection requires `GPUServer8`,
uid 1010, clean commit `2002538d...`, absent production authority, resolution,
admission, output and scientific archive-root paths, an existing 14,359,316-byte
`control/code.tar.gz` with SHA256 `4ece34be...dd22`, at least 20 GiB free disk,
and an idle fixed GPU 5 with UUID
`GPU-5622bd47-1050-3003-246d-3cabe2b4791b`. Any mismatch stops before launch.

The reviewed dispatch is frozen as:

| item | SHA256 |
|---|---|
| handoff verifier | `fe9909e005518bf2af16aa460a20bc7f6b56949fa24b9c5e9c19500b77655d1a` |
| detached resolver-to-producer launcher | `f987390e689ac3564c3b085de42ad97d38ee6a909dcf8092a7a17abc098dceba` |
| one-connection launch plan | `7de102c9a37f1c254a2cfb5136a200b65fbea17e95c580146aa7021c7686e229` |
| finite local launch guard | `942921b08d5e6cfa1c2ad244909cf172853bf6b4ba98b9b1afbd4d77f95d96f0` |

Stage 2 permits one connection attempt, one metadata transfer of at most
65,536 bytes, a 20-second connect timeout and a 120-second local dispatch wall
cap. The SSH master forbids proxy fallback and is closed after the launch
return. No third connection is included. Run-completion polling and artifact
retrieval require a later read-only decision after this card has returned.

The remote command creates one detached tmux session named
`pf_s09_e017_r001_factorised_head_p0`, records its PID, start time, log path and
exact command, runs the frozen resolver, and only on resolver success executes
`scripts/run_s09_e017_producer.py --execute-reviewed-run`. The producer creates
the exclusive production admission token before scientific asset reads. Its
own admission validates packet, configuration, checkpoint, GPU, model and
cross-arm state. Admission failure writes its terminal receipt and does not
train.

Creating the detached control process is called **launch started**. It is not
production admission. Within the same connection, the plan waits up to 30
seconds for either the production admission receipt, an admission/launcher
failure receipt, or a still-live session. Only
`FINAL_PRODUCTION_ADMISSION_REACHED` shows that the producer crossed production
admission and began the scientific path.
`FINAL_LAUNCH_STARTED_ADMISSION_PENDING` means the process is live but training
entry is not yet verified. The 1,830-second detached timeout covers resolver
plus the frozen 1,800-second producer envelope; resolver failure is recorded
and cannot invoke the producer.

If local communication with the dispatch process fails after start, the guard
kills and reaps the process group it created, records
`FINAL_LAUNCH_PROCESS_IO_FAILED`, and sets
`remote_detached_state_unknown=true`. It does not reconnect or retry, because a
remote tmux session might already have detached before the communication loss.

## Frozen scientific run after production admission

- arms: `D_DIRECT`, `F_AMP`, `F_AMP_SHAPE`;
- 64 AdamW updates per arm, 192 total;
- evaluations at updates 0, 1, 4, 16, 32 and 64; only update 64 votes;
- cycles: 1, 2, 3, 4, 21, 29, 41, 46, 48, 58, 60, 69, 70, 71, 72, 73;
- physics term: native-Q4 AMOR mechanical equilibrium on free displacement
  DOFs with external gradient weight `beta=0.25`;
- no fresh holdout, autoregressive rollout, coefficient scan, early selection,
  budget transfer, retry or resume;
- whole-run wall cap 1,800 seconds, CUDA reserved-memory cap 20 GiB, host RSS
  cap 16 GiB, output cap 10 GiB, temporary cap 4 GiB.

The full command, paths, first-stop rules and scientific interpretation remain
those in `final_run_card_20261020.md`; this card changes no model, data, loss,
metric or budget.

## Evidence and stopping rule

Local evidence records both authority consumptions, exact stdout/stderr and
guard/launch receipts. Remote evidence records admission-only receipts,
execution resolution, production admission and one of `ADMISSION_STOPPED`,
`EXECUTION_FAILED` or `COMPLETED`. Launch success means the detached producer
is verifiably running; it is not a scientific result. Training completion is
reported only after registered artifacts are retrieved and hash-checked.

Approval of this exact card authorizes both stages in this order. It does not
authorize any action after the first terminal failure or any new experiment.

## 2026-10-25 execution result

The user granted this card. Stage 1 authority SHA256
`f171af4b2803e95a9cbeea249228f958248ebfbd8f8ed87e1cc6c64c807cf945`
was materialized at `2026-10-25T16:36:24.448230+00:00` and consumed once.
The single connection reached `GPUServer8`, uid 1010 and clean exact commit
`2002538d...`; the blocked production-path set was empty. The repaired helper
staging completed and the metadata admission reached its GPU check, then
stopped with `compute process present on frozen GPU`.

The local guard returned exit 1 after 12.871 seconds with complete stdout,
stderr, consumption and guard evidence. It did not retry or reconnect. The
Stage 2 evidence root and execution authority were not created, so the final
resolver, production admission, detached session, model and training were not
entered. This is a shared-resource admission stop, not a scientific result.
