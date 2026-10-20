# D5 R003 scientific import stop and final decision — 2026-10-21

## Decision

`STOPPED_ON_FIRST_SCIENTIFIC_FAILURE__UNINTERPRETABLE_FOR_METHOD__NO_RETRY`

R003 repaired the R002 lifecycle-control defect: the environment probe, zero-step preflight and outer admission child all produced atomic, identity-bound receipts with numeric exit code `0`; the sole admission completed in 28.179 seconds and the unique scheduled scientific attempt was dispatched once. The scientific worker then exited with code `1` after 4.313 seconds while importing `skimage.morphology`, before `main`, output creation, training or optimisation.

This is a real scientific-worker environment failure under the frozen contract, not a result for the centreline/distance-field method. The unique R003 scientific attempt is consumed. No retry, remote repair, second admission, shortened schedule, host/GPU switch or new Run ID occurred.

## Frozen identity and cost

- Experiment: `HQ-ROAD-CENTERLINE-001`
- Run: `HQ-ROAD-CENTERLINE-001-R003`
- Authority: `HQ-D5-R003-20261020`, delegated through HQ thread `01a14bb9-6cd1-7ee2-9647-5190d786f7ba`
- Producer: `gpu-server`, hostname `D-26-09`, physical GPU `0`
- Expected and admitted GPU UUID: `GPU-2d0f6f7a-f29f-fc3e-0007-7e2a321cadf7`
- Code snapshot: `36bbd0109dc2319714669b9c24c77e6dd1a44fc33a304a9b71d041589d945736`
- Data-lock SHA-256: `8751d519d869ac3f2ead4334d8146e9e99deedd1c9c01b96db1f506b2286dcd5`
- Scientific-protocol fingerprint: `a30121cc43bc1572e946baa56f70a993202076a1fdbf2ca388307cd024e1e83a`
- Staged archive SHA-256: `6c2c4c8b9328e2dc4a7a962a9cd4f50876aafd414f001e2f66186a83d92fadbe`
- Original package clock: `2026-10-20T21:59:35Z` to `2026-10-21T01:59:35Z`; not reset
- R001 preserved cost: three zero-start checks, approximately 45.544 seconds, zero science
- R002 preserved cost: one zero-start check, 12.359 seconds wrapper time, zero science
- R003 cost: one 28.179-second admission and one 4.313-second scientific-worker attempt
- Training steps: `0`; optimiser steps: `0`; completed epochs: `0`
- Road420 access: `false`; CRACK500 test remained sealed

## What completed successfully

The sole R003 admission returned `PASS_ADMISSION_READY_TO_LAUNCH` and the watchdog returned `PASS_ADMISSION_WATCHDOG`. It verified the exact host, GPU UUID, 97,267 MiB aggregate free GPU memory, data lock and code snapshot. The environment, preflight and admission-child controls all recorded `COMPLETE_ZERO`, matching child/controller exit code `0`, no timeout and empty stderr.

The zero-step preflight imported `d5_runner`, which itself imports the same `centerline_core` and `skimage.morphology` path later used by the scientific worker. It verified Python 3.12.14, PyTorch 2.11.0+cu128, scikit-image 0.25.2, the locked ten input identities, 1,860 train pairs in 245 groups, 341 validation pairs in 49 groups, 118 CFD labels, 384 GAPS labels, a CUDA forward pass and the synthetic centreline metric contract. It performed no training or optimisation.

The launch receipt returned `LAUNCH_DISPATCHED_VERIFIED`, bound the scientific invocation SHA-256 `bb017140c83514bebee1ce9ca57480cc4a60ec07af9af7d4400fca48e70f7448`, recorded one scientific attempt, 8,870.839 seconds remaining in the original package clock and an 8,755-second scheduled-task limit.

These facts establish that the R003 exit-sidecar repair and launch chain worked. They do not establish model training, centreline-target feasibility or uncertainty quality.

## Scientific-worker stop

The scientific-worker receipt records `COMPLETE_NONZERO`, child and controller exit code `1`, no timeout, exact code/data identities, empty stdout and stderr SHA-256 `875b4fa9e42c95e3af0901dbf83ad5d32e5c9d5bc07223dd84334ec0cc461487`. The traceback is:

```text
File "...\d5_runner.py", line 29, in <module>
  from centerline_core import (...)
File "...\centerline_core.py", line 10, in <module>
  from skimage.morphology import skeletonize
ModuleNotFoundError: No module named 'skimage.morphology'
```

The failure occurred during module import, before the runner could enter `main` or create the canonical output. The final read-only producer snapshot found the task in `Ready` state with last result `1`, no matching R003/d5 runner process, no canonical output and the preflight cache preserved.

The task ran as `xw436` with the reviewed `cmd.exe /d /c ...\launch_gpu_server.cmd` action. A read-only path check after failure found the dependency root, `skimage`, `skimage\morphology` and `skimage\morphology\__init__.py` all present. The preflight had imported the same runner successfully only seconds earlier. Therefore “scikit-image was not installed” is not supported. The unresolved issue is scheduled-worker import resolution or environment parity; the present evidence does not identify which path/environment mechanism differed.

## Claim audit

| Claim | Direct evidence | Audit result | Limit |
|---|---|---|---|
| R003 fixed the R002 numeric-exit evidence defect. | Environment, preflight and admission-child receipts all preserve parseable child/controller exit code `0`; the scientific-worker receipt preserves exit code `1`. | **SUPPORTED.** | This validates the bounded lifecycle control, not the model. |
| Admission was valid and the unique scientific attempt was dispatched once. | Positive child/wrapper receipts, `LAUNCH_DISPATCHED_VERIFIED`, one exclusive scientific claim and one worker receipt. | **SUPPORTED.** | A launch is execution evidence only. |
| The worker stopped before model training. | Import-time traceback before `main`, empty stdout, absent output directory, 4.313-second lifetime and no remaining process. | **SUPPORTED.** | No per-batch training receipt exists because the runner never reached its receipt-writing path. |
| The failure proves scikit-image was absent from the machine. | Preflight reports scikit-image 0.25.2 from the task dependency directory; the morphology package and `__init__.py` exist after failure. | **REFUTED.** | Import visibility in the scheduled child still failed. |
| The exact cause was loss of `PYTHONPATH` in the scheduled task. | The task action and launch script intend the dependency path, but no scheduled-child `sys.path`/environment snapshot was emitted before the import failure. | **NOT ESTABLISHED.** | It remains a leading testable explanation, not a result. |
| R003 decides whether the common centreline target works on CFD/GAPS. | No training, checkpoint, evaluation rows, score table or figure exists. | **NOT SUPPORTED.** | D5 remains scientifically unanswered. |
| R003 justifies lowering performance criteria or switching to the source-specific-renderer route. | No method evidence was produced. | **NOT SUPPORTED.** | The D4 rationale and frozen D5 criteria remain unchanged. |

## Method and criteria decision

Do not alter the centreline method, the dual-source decision rule or its scientific thresholds on the basis of R003. R003 reached the scientific process but not the scientific computation. Treating it as another negative model result would mix execution validity with measurement feasibility.

The active route therefore remains **centreline/distance-field D5 unanswered**, rather than `NO-GO`. The alternative shared evidence field plus source-specific renderers remains the conditional redirect only after an interpretable D5 result, not the response to this import stop.

## Constructive next action

Any continuation needs new human/HQ authority because the sole R003 scientific attempt and original package clock are consumed. The next package should use a new Run ID and first prove scheduled-context parity through the same task mechanism before scientific execution. Its pre-import launcher should atomically preserve:

1. `sys.executable`, `sys.prefix`, `sys.path`, working directory and the exact `PYTHONPATH` value;
2. `importlib.util.find_spec` results for `skimage`, `skimage.morphology` and the task modules;
3. file existence and SHA-256 for the resolved `skimage` and morphology initialisers;
4. the scheduled-task principal/action and child exit evidence.

Only an exact positive scheduled-context result can precede one newly authorised scientific attempt. If the parity check fails, stop before GPU/model work and repair the environment contract prospectively. If a later valid D5 run produces CFD/GAPS scores, use the frozen method outcome map to retain the common centreline route, repair it, or redirect to source-specific renderers. This document authorises none of those executions.

## Evidence integrity

- Retrieved remote directory: `remote_evidence_2026-10-21/`
- Remote files retrieved: `30/30`
- Retrieval verification: every local byte count and SHA-256 matches the remote final-state inventory
- Manifest: `remote_evidence_2026-10-21/R003_EVIDENCE_SHA256_2026-10-21.json`
- Final task/process/output snapshot: `remote_evidence_2026-10-21/remote_readonly_final_state_2026-10-21.json`
- Dependency/task-context snapshot: `remote_evidence_2026-10-21/remote_dependency_and_task_context_2026-10-21.json`
- Remote originals remain in place; the preflight cache remains in place

## Boundary

No retry, second R003 admission, remote fix, Python import probe, new Run ID, host/GPU switch, shorter training, threshold/UQ search, Road420 or CRACK500-test access, dataset mutation, existing-route/log rewrite, publication, external message or public push occurred.
