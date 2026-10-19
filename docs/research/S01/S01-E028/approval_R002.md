# S01-E028 R001 stop retrieval and exact R002 repair approval version

Prepared2026-10-19, not transmitted/pushed/executed. Only the prior GPU0 R001 was authorised and has stopped; a new Run requires explicit human approval under the frozen first-stop/no-automatic-retry rule.

## Exact objects and destinations

- From: Wenxiaofang's Mac task worktree; SSH account ad\xw436 on gpu-server / hostname D-26-09. Public Git remote git@github.com:wenniebyfoxmail/phase-field-fracture-fatigue-pidl.git, only branch codex/s01-e028-target-spatial-qualification-20261019; no force-push.
- Retrieve the existing fixed R001 stop archive C:\Users\xw436\pavetrack_runs\S01-E028-R001-fixed-stop-v1.tar.gz to owner local_archive/experiments/S01-E028/runs/S01-E028-R001/. It has12members/6669bytes, SHA256595a20414628a91d940a3cfd360a4d5c2ad13c08fcdff9b7840cefba7069cace. Check receipt, archive integrity, every file and archive locally; there are no real result images to accept because0forward/0source-image/reference decode.
- Transmit Mac-prepared source S01-E028-R002-source-a5a8f465.tar.gz,68981bytes/32members/31bindings, SHA256b1b93f44cfd15b8278b3e9e9804a034b3d459fbceda68a34bd2d0d96064d5e99. Source commit a5a8f46510885f585fc1b84f004662e09309413d; manifestSHA256 eba54f07032bc8fa03ef00b02ecf51074b08290254db2ad5db692468a1cefff3. Fresh server stage C:\Users\xw436\pavetrack_stage\S01-E028-R002-v1. Do not overwrite original R001 stages or outputs.
- Transmit only the prepared Pillow wheel pillow-12.3.0-cp312-cp312-win_amd64.whl,7227137bytes/SHA256a2b55dd6b2a4c4b7d87ffa56bdb33fdc5fdb9a462173861a7bc097f17d91cb09. Store under stage/runtime_wheels/ and extract with prepare_runtime.ps1 into fresh C:\Users\xw436\pavetrack_runtime\S01-E028-Pillow-12.3.0-v1. No shared package or machine configuration change.
- Reuse the identical nine private inputs from server S01-E028-R001-gpu0-v2/private_inputs via private server copy and reverify data_lock.json. Keep private inputs and wheel out of public branch; no new annotations, images, models or sites. The338 native source images remain at their exact identity-locked paths.
- Update only the designated public branch with the reviewed code and compact R001 stop / R002 repair / review / approval records. No raw data, checkpoints, wheel or outputs published.

## Execution and commitments

After authorisation, inspect no concurrent shared Python/CPU<50%/RAM>=8GiB/disk>=16GiB/GPU0 exactUUID+desktop identities+util0/free>=8GiB. Qualify the isolated runtime and existing synthetic raster fixture before any producer Run. Unknown state or qualification failure stops; do not launch, loosen a check or silently overwrite a partial runtime.

Then execute **one S01-E028-R002 only** on physicalGPU0 UUID GPU-2d0f6f7a-f29f-fc3e-0007-7e2a321cadf7 / logicalcuda:0 / CUDA_VISIBLE_DEVICES=0. Run directory C:\Users\xw436\pavetrack_runs\S01-E028-R002; logs same-stem-wrapper-logs. Exact runner:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\xw436\pavetrack_stage\S01-E028-R002-v1\scripts\pavetrack_target_spatial\producer.ps1" -Source "C:\Users\xw436\pavetrack_stage\S01-E028-R002-v1" -ReviewedCommit "a5a8f46510885f585fc1b84f004662e09309413d" -ManifestSha256 "eba54f07032bc8fa03ef00b02ecf51074b08290254db2ad5db692468a1cefff3"
```

Producer cap3590seconds, CPU1, aggregateRSS/GPUallocated/GPUreserved each4GiB; outputs/archive each6GiB. R001 guard2.218seconds + R002<=3590seconds < original3600seconds; reserve10seconds conservatively for R001. At first stop preserve logs and do not retry or fall back.

Science unchanged:338 old qualification images,12238 existing contexts,25758 frozen-model forwards,0fitting/updates; originaleightcombinations/sixcomparators/mainnative-max-.5-any/qualificationpair/fullyfrozenpredictions-before-reference unchanged. First prove target localisation; no selector or OOF. E003,1/image3/group capacity,abstention,positiveintersection,nointersectionsweep and sealed new sites remain unchanged. No localisation or detection gain is claimed from this repair.

Independent gpt-6.1-sol / High **Code Ready REVIEW_PASS** on a5a8f465;51-Werror1.13seconds andPillow12.3syntheticfixture passed. Wheel and121 original library files checked against frozen hashes. Actual Windows overlay qualification is still pending and must pass after approval. This review does not authorise sending or executing.
