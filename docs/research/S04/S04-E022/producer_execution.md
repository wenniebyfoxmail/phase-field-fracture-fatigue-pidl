---
storyline_id: S04
experiment_id: S04-E022
status: production-package-prepared-awaiting-approval
---
# E022 Taobo three-state production proposal — 2026-10-16

Prepared locally only: no SSH, transfer, preflight onTaobo or training. User requested the final transfer/start plan for explicit approval. Scientific source stays a540888497d1838a6aa202f59a884e6930e50fb4 (independent CodeReady); deployment84a6cda is separate. Later doc commits must not replace science checkout.

Review [exact approval action](producer/approval_action.md), [machine-readable plan](producer/production_plan.json), [file identities](producer/package_manifest.json), [local nontraining checks](producer/nontraining_checks.json). Only two outgoing files: E022_a540888.bundle (100718bytes) and prepare_and_dispatch.sh (13255bytes). Both final SHA256s and paths in approvalaction/manifest; transfer from local_archive/experiments/S04-E022/producer_submission_v1/. No rawoutputs/data/checkpoints sent from Mac.

## Recipient and proposed action

Mac userwenxiaofang → drtao@172.16.100.2/GPUServer8 via ssh -F /dev/null -o BatchMode=yes -o ConnectTimeout=15 and currentTunnelblickclient. New root /mnt/data2/drtao/wennie/S04-E022-last-leak-a540888-20261016-v1; currentabsence NOTverified. Atomicmkdir must succeed; existingroot/uncertainoutcome stops for readonlyinspection. Verify bothbytes remotely, single detached bashdispatcher, capturePID and validate realstatus/cwd/source. No retries or alternateproducer.

Proposed GPU0 sharing only with >8192MiBfree, >8GiBfreedisk on mounted/mnt/data2, stableGPUUUID; log othercontexts without intervention. Repeat resource/source checks beforeeach row. Anyquery/condition failure stops. No waitloop/GPUfallback/processkill/envinstall/globalchanges. This sharingpolicy is explicitly part of this newapproval scope, not inheritedpermission.

## Before any training

Verify exactLinux/account/host/mount/newpaths and bundlehash. Clone existingE02198c6206 committedobjects without hardlinks, verifydelta bundle, fetchsnapshotref, clean detachscientific a540888. Copy60existingremote files:3references+15backbone+15E019controls from approvedE019root,27E021controls from completedE021v2root. Refusemissing/symlink/reuseddestination and comparebefore/after source/destinationSHA; real loaders then checkpinnedidentities.

All3states must pass formalruntime(Torch2.7.0+cu126,NumPy1.24.4,CUDA12.6,RTX4090,GPUServer8,GPU0,CUBLAS:4096:8), exactcurrentnative10000LRprofilevsownE021actualvector, ownreference/backbone/control/map/activation, CUDAcacheUV<=1e-12/fullRMS<=1e-14, zero-outputUVexactequalbase andfinite/BCchecks. Writebaseline_preflight.json,preflight_learning_rates.npy,asset_copy_manifest.json before candidateupdate1. Derive maps onlyfrom exactsavedE017backbonearrays, never CPU-reload substitutes. Localchecks do not qualifythisformalpreflight.

## Fixed three-row matrix

SerialR001c20s4,R002c60s4,R003c83s4; localized,alpha.7seed7,10000NEWupdates each. OwnE021direct andE019common comparator; oldcontrols not retrained. Onlylast hidden fixedleak.01 differs; otherarchitecture/coefficients/counts,initialization,E021coordinates/window/BC,backbone anddamage/history/fatigue frozen. Actualcommands, identities, output/archive/log paths in production_plan.json.

Original nativeCosineAnnealingLR(T_max10000,eta_min1e-5), actualLR read BEFOREoptimizer.step; native scheduler.step AFTER. First .001,lastactual~1.0000024427270673e-5,post-final1e-5,nextactualNone,no10001. PRE_UPDATE frozenbeforeupdate1,expected/usedvectors exactequal andreceipt-bound. NativeMacbits differ fromformal: preserveexception andstop ifformalprofiledoesnotmatch, never injectMacvector.

Aftereach row: originalstrictE022decoder checksreal trainedleakyUVreload, allnumericalmetrics/manifest/LR/sampling/BC/baseline/PRE_UPDATE, verifyall9separateactualarchivecopies; actualLRmustmatchglobalformalpreflight. Failurestopsbefore nextrow. Afterall3 originalaggregatewritesverdict; all3fullUV<=.001 is primary, damage/backgroundvsbothcontrols andinside/outsidebg separate. CompleteprimaryFAIL still means executioncompleted, notscientificsuccess. ExistingE019/E021primaryfail andstrictMacnativeLR/reference-rho exceptions preserved.

Any preflight/resource/runtime/source/identity/finite/activation/map/LR/stream/archive/strictnumerical failure stops row+dispatcher. Noresume/retry/extra update/bestcheckpoint/seed/state/GPUchange. SSHlossmeansvisibilityloss, firstinspectreadonly rather thanrestart.

## Verification and next boundary

Shellsyntax and threePythonblockscompile,12deploymenttests passed(noGPU), bundlefreshreconstructionfrom98c6206→exactcleana540888 andbothCLIhelps passed. Independentdeploymentreview recorded separately whencomplete. This is localpreparation, not RunReady or scientificoutput. Approvalrequested only after finalversionfixed; currenttaskmust nottransfer/start beforeuserapproval. Afterapproval andexecution, trackPID/source/runtime/GPU/status; retrieve27rowfiles pluslogs/preflights/manifest/aggregate, verify andcomparethenupdatecensor/Roadmap. Newfailureattempt/packagechange requires anotherconcreteplan.

## Final local deployment review

Independent CodexsubagentreviewPASS bindsdeployment84a6cda, sameexacttwofiles, sciencea540888. Independent12tests passed, no blockers; proposedGPUsharing remains point-in-timefree-memorycheck, notareservation. [Review](producer/deployment_review.md). Bothpayloads unchanged afterreview; noSSH/transfer/training. Finalapprovalaction isreadyforuserdecision.
