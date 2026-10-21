# D5 R005 scheduled-import stop and decision — 2026-10-21

## Decision

`FAILED_BEFORE_D5_TARGET__SCHEDULED_SKIMAGE_MORPHOLOGY_IMPORT_MISSING__NO_RETRY`

R005 repaired the launcher-ownership false negative observed in R004. The single admission completed in 25.742 seconds, and its environment and preflight subprocesses were accepted as `DIRECT_CHILD_OF_OWNED_LAUNCHER` with exact Run, interpreter, command, target, source-origin and dependency-hash bindings. Admission therefore passed and registered the one authorised scientific task.

The scheduled scientific worker then stopped after 0.219 seconds, before `d5_runner.py`. Its context recorded the owned controller PID `33348`, interpreter PID `46488` and `context.parent_pid == controller PID`, so the Windows launcher topology was no longer the blocking condition. In that interpreter, however, `skimage` appeared as a namespace package rooted at the frozen dependency directory and `skimage.morphology` was not discoverable. Import raised `ModuleNotFoundError`; the child exited `1`, the controller preserved this as `CONTEXT_EVIDENCE_INVALID` / exit `125`, and the task returned to `Ready` with LastTaskResult `125`.

The frozen dependency files still existed after the stop and retained the expected initializer hashes. This is therefore an unresolved admission-to-scheduled-worker import-parity failure, not evidence that the files were absent and not evidence about the centreline method.

No canonical output directory, model forward, training step, optimiser step, checkpoint, epoch, prediction, metric or figure was produced. Road420 was not in the command and remained sealed; CRACK500 test remained sealed. The single R005 admission and scientific attempt are consumed. No retry or R006 is authorised.

## Frozen identity and bounded cost

- Experiment: `HQ-ROAD-CENTERLINE-001`
- Run: `HQ-ROAD-CENTERLINE-001-R005`
- Authority: `HQ-D5-LAUNCHER-AWARE-R005-20261021`, delegated through HQ thread `01a14bb9-6cd1-7ee2-9647-5190d786f7ba`
- Producer: `gpu-server`, hostname `D-26-09`, account `xw436`, physical GPU `0`
- Expected and observed GPU UUID: `GPU-2d0f6f7a-f29f-fc3e-0007-7e2a321cadf7`
- Reviewed code snapshot: `bb8b7d330812f1c834008c3d38484b5e27d33aeb2e0b6d3a36138ec3c3b62d8f`
- Data-lock SHA-256: `44acdf7ef254091e24fffa3d470efe4ec0abe2f32a50a9f4d807a878f0574b2a`
- Scientific-protocol fingerprint: `a30121cc43bc1572e946baa56f70a993202076a1fdbf2ca388307cd024e1e83a`
- Independent review receipt SHA-256: `1ba134fa494fa2068eb86e2b6ea9db1398abb4fdd528b980b93605c2da7be52f`
- Clean staged archive SHA-256: `d1920ae1ab067b17ea1c38d032d01cf719603202886ef630d0c53626bb913d37`
- Original package clock: `2026-10-20T21:59:35Z` to `2026-10-21T01:59:35Z`; not reset
- Admission: check `1/1`, `PASS_ADMISSION_WATCHDOG`, 25.742 seconds, 97,269 MiB free on GPU 0
- Scientific worker: attempt `1/1`, 0.219 seconds, child exit `1`, controller/task exit `125`, no timeout
- Training steps: `0`; optimiser steps: `0`; completed epochs: `0`
- Road420 access: `false`; CRACK500 test remained sealed

## Decisive evidence

1. `admission_receipt_remote.json` and `admission_wrapper_receipt_remote.json` bind the positive admission to R005, the reviewed snapshot/data lock, the exact GPU UUID and check `1/1`. Both environment and preflight context receipts passed with the frozen `skimage` 0.25.2 and morphology initializer hashes.
2. `scientific_worker.context.json` binds the failure to the exact R005 interpreter, argv, target and dependency root. It records `skimage` with `origin: null`, the frozen directory as its namespace search location, `skimage.morphology` as not found, and the exact `ModuleNotFoundError`.
3. `scientific_worker.exit.json`, its exclusive claim, stderr and numeric exit sidecar agree on child exit `1`, controller exit `125`, no timeout and a direct parent-child PID relation.
4. `final_task_status.json` records task state `Ready`, LastTaskResult `125`, the expected action and principal. The canonical R005 output directory never appeared.
5. Post-stop read-only inspection found both initializer files still present with SHA-256 `7aab19d...` and `313e28fe...`. The evidence supports an execution-context discrepancy but does not identify its exact cause.

## Claim audit

| Claim | Direct evidence | Audit result | Limit |
|---|---|---|---|
| R005 repaired R004's direct-child ownership rejection. | Positive environment/preflight receipts classified `DIRECT_CHILD_OF_OWNED_LAUNCHER`; their payloads and hashes were accepted. | **SUPPORTED for admission subprocesses.** | The scientific context itself failed before ownership validation because its status was already `FAIL_SCHEDULED_CONTEXT`. |
| The scientific worker was part of the owned launcher chain. | Controller PID `33348`; context PID `46488`; context parent PID `33348`; exclusive claim and exact invocation hashes. | **SUPPORTED.** | Ownership does not make a failed import scientifically usable. |
| The frozen dependency files were missing. | Post-stop directory listing and exact initializer hashes; admission imported the same files seconds earlier. | **REFUTED.** | File presence alone does not explain why the later interpreter resolved a namespace package. |
| The scheduled scientific interpreter had usable morphology imports. | `skimage.morphology` spec not found and import traceback. | **REFUTED.** | Root cause remains unresolved; no post-failure repair probe was run. |
| R005 tested the centreline/distance-field method. | Failure preceded `runpy.run_path(d5_runner.py)`; no output directory or model artifacts. | **NOT SUPPORTED.** | Scientific verdict remains inconclusive. |
| D5's scientific criteria should be relaxed because R005 failed. | No prediction, metric or scientific criterion was evaluated. | **NOT SUPPORTED.** | The failure is execution validity, not a high scientific threshold. |

## Criteria and route decision

The scientific criteria were not too high in R005; they were never reached. The scheduled-context import check is a necessary validity condition because proceeding with a different or partially resolved dependency graph would make the result irreproducible. Relaxing it would not create evidence.

The constructive change is architectural rather than another small ownership patch: any successor package should use one deterministic scientific interpreter and perform the final dependency/source check immediately before entering `d5_runner.py` in that same process. Admission and science should not rely on two independently started Python contexts having identical import state. A self-contained, immutable environment archive or another producer with a verified deterministic environment is the alternative. Either option needs a new package clock, Run ID, focused review and explicit execution authority; R005 authorises neither.

Until then:

- **Run execution:** failed before target entry
- **Run retrieval:** verified
- **Experiment verdict:** inconclusive; D5 remains unanswered
- **Research disposition:** park this Windows scheduled-worker implementation
- **Method route:** unchanged; do not promote Route B or lower D5 criteria based on execution failure

If a future valid D5 run fails on both development sources, follow the existing outcome map and redirect from a common centreline target to the shared latent evidence plus source-specific renderer route. If it succeeds on both, proceed to the bounded selective-ranking comparison. R005 itself selects neither scientific branch.

## Evidence integrity

- Retrieved directory: `retrieved_2026-10-21/HQ-ROAD-CENTERLINE-001-R005/`
- Remote-manifest records retrieved and matched: `34/34`
- Remote manifest SHA-256: `d12d67236277b3e69ee339ab8db0b30b8e937551cf3dcec42aef21ad9417b74b`
- Independent recomputation: `retrieved_2026-10-21/independent_recomputation_2026-10-21.json`
- Remote originals remain in place.

## Boundary

No R005 retry, second admission, R006, shorter schedule, dependency installation, global environment change, host/GPU switch, process intervention, Road420 or CRACK500-test access, dataset mutation, scientific-threshold change, publication, external message or public push occurred. This report does not authorise a successor execution.
