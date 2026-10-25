---
experiment_id: S09-E017
run_id: S09-E017-R001-factorised-head-p0
status: FINAL_PRODUCTION_ADMISSION_REACHED_RETRIEVAL_NOT_YET_AUTHORISED
date: 2026-10-25
---

# S09-E017 fresh conditional admission-to-training card (r3)

## Authority and resource snapshot

The user instruction of 2026-10-25, “只要有空出来的显存，就可以推进计算”,
authorises this one fresh attempt subject to the frozen resource conditions. The
read-only Taobo snapshot found `GPUServer8`, uid 1010, GPU 5 UUID
`GPU-5622bd47-1050-3003-246d-3cabe2b4791b`, 24,077 MiB free of 24,564 MiB,
4 MiB used, 0% utilisation and no compute process. `/mnt/data2` had
586,508,099,584 bytes free and all production paths were absent.

The prior r2 authority remains consumed after its GPU-busy stop. This card does
not retry, reconnect to, alter, or remove that evidence. It creates a fresh
helper namespace and fresh attempt IDs:

- Stage 1: `s09e017-admissiononly-20261025-r3`
- Stage 2, only after exact Stage 1 success:
  `s09e017-final-launch-20261025-r2`

## Fixed identities and limits

| item | SHA256 / identity |
|---|---|
| Stage 1 candidate | `c6c9bf73e9a2e9172bf9b42ebbe1ea5502c152cdae1dbc4fa197e515dd6babda` |
| Stage 1 one-connection plan (`s09_e017_admission_only_plan_20261025_r3.sh`) | `7ce0228dd234d3e6f71d4069bfdc98658a0606315911d2995aaaf0b0a615bbc3` |
| Stage 1 guard | `5a97784a3a7a2b002a34dcc17484f0beac4667f082c341502e7116025ec0ba6f` |
| Stage 1 handoff verifier | `c73cf87528fbae9a3c5dfcc65f5e00f5fa25d4bdb9aacf643c89c19737cdbaad` |
| Stage 2 launcher | `f987390e689ac3564c3b085de42ad97d38ee6a909dcf8092a7a17abc098dceba` |
| Stage 2 plan | `7de102c9a37f1c254a2cfb5136a200b65fbea17e95c580146aa7021c7686e229` |
| Stage 2 guard | `d51070a6ab0209d7c3313c771c7333b6569f3a5b4b1fd18df003ef5e5bdaaff7` |
| frozen control commit | `2002538d9a30c8d4006ccaff5959cd214958fc82` |
| frozen archive | `4ece34be786fc85bb9655c076c13c45d276d08dfde405a8fb1367e4b49ffdd22` |

Stage 1 permits exactly one SSH connection and one metadata transfer, with a
300-second local wall. It may only perform metadata admission: no CUDA,
scientific assets, model, forward, optimiser or producer. Any failure stops
the card with no retry, reconnect, resume, cleanup, host/GPU substitution or
parameter change.

Stage 2 can exist only if Stage 1 returns
`ADMISSION_ONLY_METADATA_READY__SCIENTIFIC_IDENTITIES_UNVERIFIED` and the
local verifier confirms every hash, receipt and zero scientific counter. It
then permits one final connection and one frozen three-arm run exactly as in
`final_run_card_20261020.md`: `D_DIRECT`, `F_AMP`, `F_AMP_SHAPE`, 64 updates
per arm, beta=.25. A detached launch is not production admission or a
scientific result. Read-only retrieval after launch is a separate decision.

## 2026-10-25 execution result

Stage 1 consumed authority `215c1a5a...c7e60` once and completed in 13.409 s
with `ADMISSION_ONLY_PLAN_COMPLETED`, no evidence-write errors, no reconnect
and zero scientific operations. Stage 2 then consumed authority
`2261c8ae...c62a8` once and completed its local dispatch guard in 11.287 s.

The one final connection reported `FINAL_PRODUCTION_ADMISSION_REACHED`:
`GPUServer8`, uid 1010, clean control commit, exact archive, the fixed idle GPU
5 and no blocked production paths were revalidated. The detached producer PID
was `2731238`; its admission receipt was `ADMISSION_READY`, while its counters
still showed zero model forwards, optimiser steps and scientific asset reads at
that observation point. This establishes entry to the frozen scientific path;
it is not a completion result or a claim about accuracy, physics or fracture
quality. No third connection or retrieval action was used by this card.
