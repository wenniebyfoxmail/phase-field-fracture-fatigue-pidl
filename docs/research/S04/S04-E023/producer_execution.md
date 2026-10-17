---
storyline_id: S04
experiment_id: S04-E023
status: dispatcher-running-all-state-preflight
---
# E023 Taobo three-state production preparation — 2026-10-16

Local preparation only, no SSH, transfer, producer preflight or training. User requested a concrete final transfer/start version for approval. Scientific snapshot remains reviewed c4ceb5d27fa8d408be1b9f02dcd6b10308f301a2; deployment28f6aa8 is separate and does not modify that science checkout. Later record commits must not replace the scientific target.

Review [exact action/full transport commands](producer/approval_action.md), [three-row plan and commands](producer/production_plan.json), [two-file identities](producer/package_manifest.json), [local deployment checks](producer/nontraining_checks.json), [full script](producer/prepare_and_dispatch.sh).

## Proposed account, directory and resources

Mac user wenxiaofang → drtao@172.16.100.2 / GPUServer8 through existing Tunnelblick client, ssh -F /dev/null -o BatchMode=yes -o ConnectTimeout=15. Freshroot /mnt/data2/drtao/wennie/S04-E023-head-rms-c4ceb5d-20261016-v1; its absence and live resources are NOTverified. Atomicmkdir must succeed; existing or uncertain state stops for readonly inspection, never reuse. Both transferred SHA256s must match before one detached dispatcher launch, followed by realPID/source/cwd/status verification. SSH loss alone never triggers another launch.

Proposed sharing GPU0 only while free>8192MiB, data2mounted/free>8GiB; log contexts without intervention. Repeat before each row and reject UUID drift/query errors. This is point-in-time availability, not a reservation. No process interference, GPU fallback, package install, global changes, requeue or retry.

## Source and 87 existing inputs

Outgoing files only E023_c4ceb5d.bundle117400bytes and prepare_and_dispatch.sh17889bytes; exact SHA256s in manifest/action. Local source local_archive/experiments/S04-E023/producer_submission_v1. No Mac calibration vectors, raw inputs, checkpoints or outputs uploaded. Bundle requires a540888 committed objects from original E022code; clone without hardlinks, verify/fetch bundle and clean-detach c4ceb5d. All actual input/backbone/E019/E021/E022 bytes copied from their own existing remote roots, no modifications of old runs.

Copy87existing files:3references,15backbone files,15E019files,27E021files,27E022files, reject symlink sources/reused destinations/corruption, hash source before/after plus destination. Actual scientific loaders then admit trusted identity. All3references, maps, initialization and controls must pass before any candidate update.

## Fixed D, actual LR and pairing

Each state independently uses original E017alpha.7seed7backbone and common zero-output residual, preserved E022leak.01. CPUfloat64/two-thread/1024chunk full-mass initial physical features (BC×window×[h,1]/absUs) produce284D/s includingbias; fixedfloor1e-6/zeroD1, finitepositive D. Calibrator excludes target-residual labels and final trained features. Native formal producer computes these values; Mac vectors are not injected. Two fresh initializer passes and the full head-gradient coordinate audit must agree, then CUDA cache, exact zero-output and BC checks pass for allthree. Per-state formal D/s and gradient files with hashes are saved before training.

Every row repeats source/resources and fresh fixed-D/gradient recomputation against those preflight bytes. The unchanged c4runner independently computes D from the same trusted initializer/input and validates its stored buffers every update; it has no new external-D argument or patched build function. Actual row calibration files are compared to all-state preflight after strict row completion and before the next row. Do not describe this as an added in-run external-vector barrier.

Serial c20s4,c60s4,c83s4; correct own E022direct controls and E021/E019common controls, localizedalpha.7seed7,10000NEWupdates each; original backbone/history/fatigue/damage/window/map/BC/full-field target frozen, no old-control retraining. Exact identities and argv in production_plan.json.

Original nativeCosineAnnealingLR(T_max10000,eta_min1e-5); actualLR read before optimizer.step, scheduler.step after. First.001,lastused1.0000024427270673e-5,postfinal1e-5,nextNone/no10001. Entire expected/actual10000vectors must equal formalpreflight and ownE022/E021original used vectors; Macbit exceptions are retained, not waived.

## Stops, outputs and scientific boundary

Preflight/source/runtime/identity/map/D/gradient/LR/stream/finite/BC/resource/archive failure stops, preserves logs, no automatic repair/retry/extraupdates/GPUchange. Perrow original strictc4decoder reconstructs calibration from trusted initializer and actual scaled class/buffers, checks all numerical metrics at unchanged tolerances,11outputs and11realarchivecopies before nextrow. End originalaggregate requires3valid rows; primary remains all3finalfullUVRMS<=.001. If all valid but primaryFAIL, execution is completed while scientific target fails. Damage and background preservation against each named control remain separate; no statewinnerstitching or physical-teacher promotion.

Retrieve33rowoutputs plus all logs/resource records, formalbaselinepreflight/nativeLR,6initialheadpreflightfiles,87assetmanifest and originalaggregate; verify and compare E023 vsE022/E021/E019 full/damage/background plus inside/outside/exterior invariance. Update experiment/censor/Roadmap. No next experiment or external send authorised by this preparation.

## Local validation

15deploymenttests passed:87-file copy integrity/reuse/symlink/corruption, actual shell GPU/disk/UUID/query guards and actual row D hash/recomputation refusal. bash-n and four embedded Python blocks compile. Minimal local base22-only reconstruction explicitly lacked c4object before bundle, then reconstructed exact clean c4; bothCLIhelps and all3realvalidate-onlycalls pass. Formal GPU/runtime preflight remains future work. Independent [deployment review](producer/deployment_review.md) reports DEPLOYMENT_PREPARATION_PASS, no blockers, bound to deployment28f6aa8801ad0d24660c08a6711d97383936b752 and unchanged sciencec4ceb5d. It independently verified exact payloads and all15deploymenttests. Await this final version's user approval before remote action.

## Approved action and connectivity stop — 2026-10-17

User explicitly approved the exact two unchanged files, v1 new directory, GPU0sharing only free>8GiB and one conditional launch after all preflights. Local payload sizes/SHA256s reverified against approved manifest. First SSH transport stage failed during banner exchange before authentication (exit255 brokenpipe); one read-only target-state verification also failed during key exchange (exit255 connectionreset). No SCP/dispatcher/formalpreflight/training performed; remote directory remains unverified, not assumed absent or created. This is connectivity loss, not a producer/scientific failure.

Read-only local network inspection: Tunnelblick GUI running but no openvpn process observed; target route uses en0/gateway10.255.255.254. Asked user to reconnect existing Taobo client. After restoration inspect target read-only, then continue this already approved exact action if safe; do not blindly repeat mutation, replace package, changeGPU or launch twice. User approval remains valid for this exact account/files/directory/policy. Local attempt record: local_archive/experiments/S04-E023/producer_execution_v1/connection_attempt.json. No dispatcherPID exists in this record; no training monitor claims a running job.

## Connectivity restored; approved single dispatch — 2026-10-17

User confirmed Tunnelblick connected. Read-only SSH verified drtao/GPUServer8 and TARGET_ABSENT before repeating any directory mutation. Atomic freshmkdir succeeded; SCP transferred exactly the approved twofiles, both remoteSHA256s matched. One nohup dispatch at **2026-10-17T14:50:41Z**, **PID1104872**, adopted byPID1, verified livecwd under exactroot/code, clean scientific HEADc4ceb5d27fa8d408be1b9f02dcd6b10308f301a2. Initial resource guard passed, all87assets copied and verified; all-state formalpreflight running (child1105053), not yet complete at14:51:33Z. No candidate training confirmed at this snapshot. Do not relaunch.

Root/log/command/GPU/archive/immutablepackage follow approved action above. Local launch_receipt.json under local_archive/experiments/S04-E023/producer_execution_v1; finalresults pending. Hourly threadheartbeat **e023** enabled: only read-only monitoring/retrieval/analysis, silent ordinaryprogress, notifycompletion/failure/useraction and disable atterminaloutcome. No retry/newexperiment/sourcechange authorized.
