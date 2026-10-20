---
experiment_id: S09-E017
planned_run_id: S09-E017-R001-factorised-head-p0
status: PRE_ADMISSION_REPAIR_STOPPED_FROZEN_ARCHIVE_TRANSFER__AUTHORITY_CLOSED__NO_EXECUTION
producer: gpu-taobo / GPUServer8
forbidden_fallback: any other host or GPU
---

# S09-E017 authoritative final run card

This is the only current run card for S09-E017. The historical
`final_run_card_draft_20261019.md` remains as the round-1 REVISE record and must
not be used to launch. This card binds the Code Ready real adapter and the final
execution-control candidate. It does not grant execution authority.

## Frozen scientific action

Run one development-only comparison on the 16 exposed independent
`s00 -> s04 peak` transitions:

```text
(d,H,alpha_bar,q_prev,f)_s00 + prescribed path s00...s05
  + fixed mesh/material/boundary
  -> (d,H,alpha_bar,q_prev,f,u)_s04 peak.
```

The damage readout arms are `D_DIRECT`, `F_AMP` and `F_AMP_SHAPE`. They use the
same frozen hidden field `h_i`. Their trainable counts are respectively
`width+1`, `width+1` and `2*width+1`. The factorised shape arm retains the
reviewed `epsilon=1e-6` update-0 seed offset. Each arm receives exactly 64
AdamW updates; evaluations are fixed at 0, 1, 4, 16, 32 and 64, and only update
64 votes. There is no retry, resume, budget transfer, early selection,
coefficient scan, alternate host/GPU, fresh holdout or autoregressive rollout.

The `P` group is limited to native-Q4 AMOR mechanical equilibrium on free
displacement DOFs with external gradient weight `beta=0.25`. It does not add
damage stationarity, history/KKT complementarity, fatigue-law closure or the
full incremental variational inequality.

## Reviewed identities

| Layer | Exact identity |
|---|---|
| Numerical core | `5ac6b7955b56309ac8ff2fda50b16b2e1669110a` |
| Real-head design | `06bf5fef693be5321ce7daf9d2384b8fa3953fde` |
| Static integration | `3a5a2020c7b16555e9ecd9ec19377bf87a52d5c5` |
| Real adapter | `662005f1fde22cb9a6e8069f4e430b7190f21860` |
| Final execution control | `2002538d9a30c8d4006ccaff5959cd214958fc82` |
| Candidate config SHA256 | `4c1e928274f6fbee134ff540345844260cf16675727d0e996abb0054062ddcf1` |
| Code archive SHA256 | `4ece34be786fc85bb9655c076c13c45d276d08dfde405a8fb1367e4b49ffdd22` |
| Packet manifest SHA256 | `1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6` |
| Frozen package config SHA256 | `46c0cc6b9c5dcc62794845a20502a2eaa98c7ce7dd05b423a6b00a3d1784a2e6` |
| Base runtime config SHA256 | `0cf59c58dfed34b8e333bffde6ca276623c71f45adf787a6f7879498bb088e4b` |
| B25 checkpoint SHA256 | `24bbea271fe3c2df79913f552dde863e495d33df963e0db9586b4920904dcf05` |

The disabled candidate is
`final_execution_candidate_20261020.json`. The tracked authority template is
`NOT_GRANTED`. A later authority receipt must bind the focused-reviewed control
commit, candidate-config SHA256 and exact code-archive SHA256. Hand-editing
`execution_authorized`, status or wrapper fields does not satisfy this gate.
The exact identities and final focused-review verdict are also frozen in
`final_execution_package_manifest_20261020.json`.

## Fixed paths

```text
packet:
  /mnt/data2/drtao/wennie/S09-E008-P1-STAGING-20261016/packet
base package config:
  /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/code/docs/research/S09/S09-E017/final_run_package_config_20261019.json
base config:
  /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/code/docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json
initial B25 checkpoint:
  /mnt/data2/drtao/wennie/S09-E010-R001-support-amplitude-three-arm/B25_support_amplitude_beta0p25/checkpoint_update500.pt
code root:
  /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/code
control root:
  /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control
output root:
  /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/run
archive root:
  /mnt/data2/drtao/pidl_archives/S09-E017-R001-factorised-head-p0
TMPDIR:
  /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/tmp
XDG_CACHE_HOME:
  /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/cache
```

The code, control, output, archive, temporary and cache roots are attributable
to this Run ID. Output and archive roots must be absent at admission. The
control, temporary and cache directories are created once during authorised
staging. The code checkout/archive must resolve to the focused-reviewed control
commit; no dirty execution file is allowed.

## Finite resource envelope

| Resource | Cap/floor |
|---|---:|
| Whole-run wall time | 1,800 s |
| CUDA reserved memory | 20 GiB |
| Host maximum RSS | 16 GiB |
| Free `/mnt/data2` space | at least 20 GiB throughout |
| Output tree | at most 10 GiB |
| Temporary tree | at most 4 GiB |
| Immutable code archive | at most 100 MiB |

Wall/CUDA checks and host RSS/disk/output/temp checks run at the existing
resource-guard boundaries. Any cap/floor violation stops the whole run. The
launcher records PID, PPID, UID, cwd and command line. Shared-account ownership
is additionally fixed by the Run-ID paths and `pf_` session naming; no process
may be killed without cmdline, elapsed-time and cwd attribution.

## Authority and current network block

`execution_authority_template_20261020.json` is deliberately disabled. A later
authority receipt is valid only if it records:

- `APPROVED_FOR_ONE_ADMISSION_AND_COMPLETE_RUN` and `execution_authorized=true`;
- the same Run ID, reviewed adapter and focused-reviewed control commit;
- the exact candidate-config and code-archive hashes;
- only `LIVE_ADMISSION` and `COMPLETE_THREE_ARM_RUN`;
- one launch, no retry, no alternate host/GPU;
- explicit external confirmation that the connection condition recovered;
- `granted_by=user` and a grant timestamp.

Current global evidence is blocking: the first owner SSH connection to
`172.16.100.2:22` stopped with exit 255; no remote shell, deployment, data read,
solve or training occurred. The local route uses default `en0`, the VPN service
was not connected and no recovery evidence exists. This package must therefore
remain parked. Preparing or reviewing it is not permission to probe SSH, retry
the prior connection, change networking or create a new S09 attempt.

## Ordered live admission

After both network recovery and exact user authority exist, the single live
admission performs these checks in order and stops on the first failure:

1. exclusive creation of the one-attempt token;
2. authority schema, exact reviewed control commit, candidate hash and code
   archive hash;
3. Linux, `GPUServer8`, exact code-root cwd and task-owned process identity;
4. fresh output/archive roots, expected control/tmp/cache roots and fixed env;
5. disk/RSS/temp/archive budgets and tracked execution-file cleanliness;
6. packet/base-config/B25-checkpoint identities without changing them;
7. visible GPU 5 and UUID `GPU-5622bd47-1050-3003-246d-3cabe2b4791b`;
8. pristine cross-arm state, parameter/storage isolation, exact trainable
   counts, FAS seed offset and empty optimizers;
9. zero model-forward/autograd/optimizer-step counters before the first
   scientific operation.

The launcher first creates `control/admission_attempt.json` with exclusive
create semantics. Its existence consumes the only admission, including when a
later check fails or the process stops unexpectedly. Admission success writes
`control/admission_receipt.json` before scientific binding resolution.
Admission failure writes
`control/admission_failure_receipt.json` when the control root is writable,
with zero scientific counters and no retry.

## Exact resolver and launch commands

The following commands are frozen text for a later authorised staging. They are
not authorised now.

```bash
cd /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/code

python3 scripts/resolve_s09_e017_execution.py \
  --base-package-config docs/research/S09/S09-E017/final_run_package_config_20261019.json \
  --execution-candidate docs/research/S09/S09-E017/final_execution_candidate_20261020.json \
  --execution-authority /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control/execution_authority.json \
  --code-archive /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control/code.tar.gz \
  --output-config /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control/config_resolved.json \
  --output-receipt /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control/resolution_receipt.json \
  --resolve-authorised-config

CUDA_VISIBLE_DEVICES=5 \
TMPDIR=/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/tmp \
XDG_CACHE_HOME=/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/cache \
python3 scripts/run_s09_e017_producer.py \
  --resolved-config /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control/config_resolved.json \
  --base-package-config /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/code/docs/research/S09/S09-E017/final_run_package_config_20261019.json \
  --execution-candidate docs/research/S09/S09-E017/final_execution_candidate_20261020.json \
  --execution-authority /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control/execution_authority.json \
  --code-archive /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control/code.tar.gz \
  --control-dir /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control \
  --packet-dir /mnt/data2/drtao/wennie/S09-E008-P1-STAGING-20261016/packet \
  --base-runtime-config /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/code/docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json \
  --initial-checkpoint /mnt/data2/drtao/wennie/S09-E010-R001-support-amplitude-three-arm/B25_support_amplitude_beta0p25/checkpoint_update500.pt \
  --output-dir /mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/run \
  --execute-reviewed-run
```

The eventual launcher must use a detached `pf_` session and separately record
session name, PID, start time, log path and exact command. It may launch only
after admission success and must not substitute another machine, card, Run ID,
path or command.

## Whole-run first stop and terminal receipts

The first admission, identity, resource, scientific, constraint or evidence
failure stops all arms. Do not retry, resume, select another checkpoint, move
unused updates or use an alternate producer. Preserve the first reason,
artifact identity, active arm, attempted update, operation/step/commit counters,
last complete update, process identity and resource snapshot.

Terminal evidence is exactly one of:

- `ADMISSION_STOPPED`: control failure, zero scientific operations;
- `EXECUTION_FAILED`: real adapter failure with last-complete evidence;
- `COMPLETED`: all 192 updates, scheduled evaluations, fields/figures, audit,
  inventory and final retrieval verification completed.

Every failure receipt includes `retry=false` and `alternate_gpu=false`.
`COMPLETED` is published only after all registered artifacts and the inventory
are reread and hash-verified. Completion establishes execution and evidence
availability only; the frozen multi-objective profiles determine the bounded
scientific interpretation.

## Sole remaining decision

The prior one-run authority is now closed by the pre-admission network stop.
The next decision is whether to issue a new explicit authority after the
connection is independently stable. Any such action must begin with a read-only
inspection of the preserved remote RunID paths and process state; it must not
assume a fresh task root, overwrite the partial staging evidence, resume a
transfer or launch the runner automatically.

## 2026-10-20 authorised dispatch receipt

The later exact authority did establish a real SSH connection and verified the
frozen host, GPU5, disk floor, fresh RunID roots, packet manifest and B25
checkpoint identities. Staging then stopped when the thin Git bundle transfer
returned `lost connection`. The command chain never wrote the remote authority,
reached the target execution commit, generated the bound remote code archive,
invoked the resolver/runner or created the exclusive admission token.

The terminal state is
`PRE_ADMISSION_STAGING_STOPPED__NETWORK_TRANSFER_LOST_CONNECTION__NO_EXECUTION`.
There were zero scientific forwards, autograd collections, optimizers, steps
and completed updates. No reconnect, retry, resume, cleanup or alternate route
was performed after the terminal error. This authority is closed. Any future
action requires new explicit authority and must first inspect the preserved
remote RunID staging paths without assuming they are fresh.

## 2026-10-20 deployment-repair receipt

A later user authority permitted read-only residual inspection, task-owned
staging repair and then the unchanged one-run attempt. The thin bundle was
completed and verified, and the clean remote checkout reached the exact
reviewed control commit. The remote compressor did not reproduce the frozen
archive bytes, so the exact locally reproduced archive was transferred under a
30-minute hard limit. That transfer stopped at approximately 93% before the
archive hash could close.

The partial archive was isolated as
`control/code.tar.gz.partial_frozen_transfer_stopped_20261020`; the expected
archive path is absent. No authority, resolver, admission token, runner, output
or scientific operation was created. The complete receipt is in
`final_execution_repair_stop_20261020.md` and
`final_execution_repair_stop_receipt_20261020.json`.
