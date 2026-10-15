---
storyline_id: S04
experiment_id: S04-E021
status: awaiting-user-approval
---
# E021 Taobo production preparation — 2026-10-15

**Local preparation only. No SSH, transfer, remote preflight or training has occurred.** No producer PID/start time exists. The exact source and deployment package are ready for final human approval; this record is not a run receipt.

Scientific source: `98c620637b2b2ef06ec86983220a4e7f9f1053b7`, independently Code Ready PASS (162 nontraining checks). Deployment source: `540632738c080773b22aec65a46dbd2ea1bdd420`, separate from science; subsequent documentation commits must not replace the science checkout. The dispatcher remains outside the clean detached science checkout.

## Proposed exact action

Sender: local Mac userwenxiaofang. Recipient: `drtao@172.16.100.2`, expected hostnameGPUServer8, existing Tunnelblickclient and public-keySSH. Use `ssh -F /dev/null -o BatchMode=yes -o ConnectTimeout=15`; no alternative producer or GitHubpush. Fresh task root `/mnt/data2/drtao/wennie/S04-E021-coordinate-98c6206-20261015-v1` must not already exist.

Only two files proposed for upload:

| File | Bytes | SHA256 |
|---|---:|---|
| E021_98c6206.bundle | 160346 | 14507c08858bb9bd624bfaaf2ce9ccd834f78fbc9313c1703bfc85da066e9268 |
| prepare_and_dispatch.sh | 11845 | 52399cd89b2f5ad5633bbaaa6f0736d92c70c43f0bf183ffc4d11c5c1f8c5a8c |

Local package and complete approval preview: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/producer_submission_v1/approval_request.md`. That document contains full transfer/start commands, commitments and exact script. `producer/production_plan.json` enumerates full commands/reference/backbone/control/runtime identities. `producer/package_manifest.json` identifies package/review records. Raw FEM/model data is not uploaded:33existingproducerfiles are copied read-only from original E019root and verified independently. Incremental bundle requires exact originalE019sourceae238713.

## Execution after explicit approval only

One detached dispatcher; atomic DISPATCH_ONCE rejects repeat invocation. Mount/account/host/source/freshpaths first; data2free>8GiB and GPU0free>8GiB with no reported GPU0computeapps. Record GPUUUID and recheck resources before every row; no exclusive reservation is claimed. TMPDIR, XDG/Torch/extensions caches, code/logs/results all under the freshdata2taskroot.

All-state preflight before any candidateupdate: pinned Torch2.7.0+cu126/NumPy1.24.4/CUDA12.6/RTX4090/GPUServer8/visibleGPU0/CUBLAS:4096:8; actual reference/backbone/control loads, coordinate map and initial digests, CUDA-backbone versus savedUV<=1e-12 and fullRMS<=1e-14, zero-output candidate equal to actualbackbone exactly, finite/BCchecks. No parameterupdate in preflight. Save all-state native10000used-LR metadata profile.

Three sequential rows: rootbasename-R001-c20s4-localized-s7, R002-c60s4-localized-s7, R003-c83s4-localized-s7. Every rowalpha.7seed7,16384batch(11469damage/4915background),10000freshoptimizerupdates; immutableE017backbones and E019localizedR002/R004/R006controls. No residual/optimizerresume or controlretraining. Backbone/damage/history/fatigue/physicalwindow/BC frozen.

Original E019nativeCosineAnnealingLR(T_max10000,eta_min1e-5). ActualLR is observed before optimizerstep, scheduler advances after. Update1=.001; update10000approximately1.0000024427e-5 USED, post-final schedulerLR1e-5, no update10001. Formalruntime generates exactbinaryvector; Macapproximation does not impose portablebits. Per-row expectedvector/map/PRE_UPDATE recorded before firstupdate; all10000actualLRs checked, finally bitwiseequal to all-state preflightvector.

Every candidate must finish and pass original strict numericaldecoder, archive8payloads+receipt and nativeLRvectorverification before nextrow. Any source/resource/runtime/identity/finiteness/LR/BC/copy/archive/numericalintegrityerror stopsdispatcher; no automaticretry/resume/extra10001/GPUfallback/codechange or unrelatedprocessintervention. SSHloss is only visibilityloss; inspect existingPID/markers/logs before any further action.

After all3verifiedrows use exactscienceaggregate; primary all3finalfullUVRMS<=.001, damage improvement/backgroundpreservation vs inherited and E019separately, inside/outside-windowbackground and exteriordrift separately. No bestcheckpoint or per-state schedulechoice. Complete scientificFAIL is not an executionerror and never triggers retry. Strictcross-platformrhoexception/tolerances unchanged. Expectedninefilesperrow (27total) plus logs/assetcopy/preflight/LRprofile/originalaggregate must be retrieved and verified, then produce exactcomparison/decisionfigure/README and updatecensor/Roadmap. Actualresultinterpretation remains futurework.

## Local checks and independent deployment review

Bundle verified and a clean98c6206 was reconstructed locally from a repository containing only the E019basecommit plus the incrementalbundle. Selected source/lock bytes match Git exactly. All3reconstructedCLIrealasset validations passed (trainingfalse, formal_runtime_checkedfalse). Bashsyntax and3embeddedPythonblocks compile. Six meaningful operationaltests pass:33filemanifest, no destinationoverwrite, no sourcesymlink, corruptcopyrejection, platformguard and missingmountstopbeforewrites.

Independent Codexsubagentdeployment review of exact5406327: readyforfinalhumanapproval, no blockers;6independenttests passed0.56s, script/bundle/plan exactbytesandidentitiesverified. Raw report/log/result in localpackage/deployment_review; hashes inmanifest. SourcecodeReadyPASS remains bound98c6206. LiveGPU/runtime/mountavailability, actualtraining/archives/scientificefficacy untested.

Next: user approves exactaccount/files/root/action version in approval_request.md. Any changed bytes, recipient, destination, budget or commitments require a new approval version.
