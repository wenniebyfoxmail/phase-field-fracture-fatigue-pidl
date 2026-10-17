# S04-E024 v1 producer preparation — 2026-10-17

Status: PREPARED_AWAITING_EXACT_VERSION_APPROVAL. Local preparation only; no SSH, transfer, producer preflight or training. Scientific commit `231fe4be83e26ef4054a2a6a567da51229185837` is independently Code Ready. Deployment code stays separate from the exact clean scientific checkout and cannot patch it.

## Exact production action

[Approval version](producer/approval_action.md) contains account/host, two immutable files/bytes/SHA256, full transport/one-shot detached commands, resource policy and stopping rules. [Machine-readable plan](producer/production_plan.json) contains every state-specific argv, ID, reference/backbone digest and paired controls. [Manifest](producer/package_manifest.json) binds outgoing files. Approve this version before any transfer or conditional launch.

New root `/mnt/data2/drtao/wennie/S04-E024-head-tail-231fe4b-20261017-v1`, sender Mac wenxiaofang, target `drtao@172.16.100.2 / GPUServer8`. Bundle prerequisite existing E023 c4ceb5d; exact local delta rebuilds reviewed231fe4b. Proposed GPU0 sharing only when current free memory strictly>8192MiB, mounted data2 free>8GiB; initial and each-row telemetry/UUID logged. No alternate GPU, resource reservation, other-process intervention or automatic wait/retry. SSH always `-F /dev/null -o BatchMode=yes -o ConnectTimeout=15`; drops mean visibility loss only.

## Preflight, identity, LR and stages

Read-only old roots E019v1/E021v2/E022v1/E023v1 supply120verifiedcopies:3references+15backbone+15E019+27E021+27E022+33E023. Reject absent/symlink sources, reused destinations or byte drift; pinned loaders qualify every identity. Scientific clean HEAD/runtime/native10000LR/map/BC/window/leak/cache/zero residual and full10000/prefix8000sampler checks pass for allthree before any candidate update. Formal freshly calculated D/gradient must exactly equal own original E023 files and fresh repeat; Mac D is not transferred. Each row repeats these initialization checks before training.

Serial c20s4/c60s4/c83s4 localized alpha.7seed7 from each own E017backbone/zero residual, direct own-state E023 and E022/E021/E019 historical comparisons; no prior-control retraining or final-checkpoint resume. Original full-field objective and frozen backbone/damage/history/fatigue/physicalwindow/BC/map/D/leak retained. First8000joint then2000headonly, sameAdamW/headmoments/paramgroup. Hidden parameters and activationcoeff frozen with gradNone, no subsequentdecay; finalhead10000/hidden8000.

ActualLR nativeCosineAnnealingLR(T_max10000,eta_min1e-5), readbefore optimizer then schedulerafter: first.001,8000=.00010462801334558331,8001=.00010453658778440045,lastused1.0000024427270673e-5,postfinal1e-5/no10001. Formal replay and actualused vectors equal ownE023/E022/E021nativefiles; platform bit exceptions not waived.

Immutable PRE_UPDATE beforeupdate1; separate step_8000.pt actualmodel/optimizer snapshot and HEAD_ONLY_STAGE_ENTRY before8001, binding initialprehash/actualD/gradient/source/run/state/prefix/LR/counters/weights/moments/time. Finalcheckpoint holds actualoptimizerstate plus stagehashes. Frozen decoder checks stage/finalidentity, hiddenweights/moments exactinvariance, headcounts, masks, sampling, fullvectorLR, initial0..8000controltrace, recomputedUV and archives.13files/row,39outputs plus39trueproducerarchivecopies; successfulrowvalidation required before nextstate.

## Stops and evaluation

Any resource/source/runtime/identity/D/nativeLR/stage/sampler/counter/frozenweightmoment/finite/BC/exterior/archive failure stops and preserves logs; no repair/retry/newbudget/seed/GPU/source or next experiment. The final frozen aggregate must contain3validrows and48pairedregionalcomparisons without errors/missing states. Descriptive completion is not a success claim: .001 remains historicaldiagnostic only, route/backgroundacceptability/applicationspecifictolerance stayundefined. Report eachstatefull/damage/background/inside-backgroundeffect vsownE023 andE022/E021/E019, inheritedbackbone andexteriorinvariance, plusobservedwall/memory/update/storagecost. No statewinnerstitching or damage/crack/fatiguequalification fromUVfit.

Retrieve39rowfiles/alllogs/assetmanifest/baselinepreflight/usedLR/preflightDgradient/resourceandstageJSON/snapshots/originalaggregate to `local_archive/experiments/S04-E024/producer_execution_v1`, verify and generate exacttables/decisionfigures/README before updatingcensor/Roadmap. Current application priority isdamage/crack/fatigue; futurecoupled/historyvalidation isstillrequired.

## Local preparation checks

22deploymentchecks passed:120-copy integrity and early-stop paths, actualshellresources, own-E023Dguard andsummarysemantics. bash-n andfiveembeddedPythonblockscompile; deployedhelpercallaritycheckedagainstactualfunctions. Minimal localc4-onlyobjectstore initially lacked231fe4b, verifiedbundle reconstructed exactclean231fe4b; bothCLIhelps andallthree realassetvalidate-onlycalls passed. No optimizerparameterstep/training or formalnativeCUDAqualification. Details in producer/nontraining_checks.json and local producer_submission_v1. Independent [deployment review](producer/deployment_review.md) returned DEPLOYMENT_PREPARATION_PASS, no blockers, bound to deployment`a091ad744af1f642ec9ae185b7e8fa34d9de359e` and science`231fe4b`; independently22checks pass (2.74s). The exact two payloads are unchanged. Await finalversionuserapproval; no remoteavailability/directoryabsence claim.
