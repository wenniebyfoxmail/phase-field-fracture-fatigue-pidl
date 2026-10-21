# D5 R004 scheduled-context control stop and decision — 2026-10-21

## Decision

`STOPPED_ON_SINGLE_R004_ADMISSION__CONTROL_PID_TOPOLOGY_FALSE_NEGATIVE__NO_SCIENTIFIC_LAUNCH__NO_RETRY`

R004 resolved the scientific import uncertainty left by R003: in the bounded child context, `skimage` 0.25.2 and `skimage.morphology` resolved from the frozen dependency directory, both initializer hashes matched, and the task modules resolved from the reviewed target directory. The environment payload itself exited `0` and emitted the expected environment JSON.

The admission nevertheless stopped because the controller required the context PID to equal the PID returned by `subprocess.Popen`. On this Windows virtual-environment launcher, the recorded context process was a direct child instead: controller-owned PID `8572`, context PID `13500`, and context `parent_pid` `8572`. The evidence therefore establishes a valid direct parent-child relationship and refutes the equality assumption. The controller converted the otherwise successful environment child to `CONTEXT_EVIDENCE_INVALID` / exit `125`, so admission and watchdog failed by design.

No scheduled scientific task was registered or started. There was no model output, training, optimisation, checkpoint, epoch or method result. The unique R004 admission was consumed and was not repeated.

## Frozen identity and bounded cost

- Experiment: `HQ-ROAD-CENTERLINE-001`
- Run: `HQ-ROAD-CENTERLINE-001-R004`
- Authority: `HQ-D5-SCHEDULED-CONTEXT-R004-20261020`, delegated through HQ thread `01a14bb9-6cd1-7ee2-9647-5190d786f7ba`
- Producer: `gpu-server`, hostname `D-26-09`, account `xw436`, physical GPU `0`
- Expected and observed GPU UUID: `GPU-2d0f6f7a-f29f-fc3e-0007-7e2a321cadf7`
- Reviewed code snapshot: `64108b2d8248011219b3638489bf5d33ff2e912227d9d627044bc211917a1a0c`
- Data-lock SHA-256: `bae2dd2405877b0116b4cf126c72ea9b77c0b75401dccc7e2f3ff33d91474288`
- Scientific-protocol fingerprint: `a30121cc43bc1572e946baa56f70a993202076a1fdbf2ca388307cd024e1e83a`
- Clean staged archive SHA-256: `45939736b69987d9c9376835fdf391d9b91f552782f317d55197c75e7779b5f3`
- Original package clock preserved: `2026-10-20T21:59:35Z` to `2026-10-21T01:59:35Z`
- R004 cost: one admission, 8.250 seconds wrapper time; no scientific attempt
- GPU state at admission: 97,267 MiB free; listed GPU clients all matched the allowed desktop-background classification
- Training steps: `0`; optimiser steps: `0`; completed epochs: `0`
- Road420 access: `false`; CRACK500 test remained sealed

## Decisive evidence

The scheduled-context receipt recorded:

- status `PASS_SCHEDULED_CONTEXT` and Run ID `HQ-ROAD-CENTERLINE-001-R004`;
- Python `3.12.14` at `C:\Users\xw436\pavetrack_env\Scripts\python.exe`;
- target directory at `sys.path[0]` and frozen dependency root at `sys.path[1]`;
- `skimage` and `skimage.morphology` origins under `C:\Users\xw436\jobs\hq_road_centerline_001_deps_20261020`;
- exact initializer SHA-256 values `7aab19d...` and `313e28fe...`;
- `centerline_core` and `d5_runner` origins under the reviewed R004 target directory;
- context PID `13500` and parent PID `8572`.

The owned environment receipt recorded PID `8572`, child exit `0`, empty stderr and the complete positive context payload. Its only error was `ValueError: scheduled-context Run/status/PID mismatch`, introduced by the equality check in `owned_subprocess.py`. Independent recomputation confirms `context.parent_pid == environment-owned child pid` is true.

The final producer state had no R004 scheduled task, no matching R004 process, no canonical output and no scientific-worker receipt. This independently confirms that the stop preceded scientific execution.

## Claim audit

| Claim | Direct evidence | Audit result | Limit |
|---|---|---|---|
| The frozen dependency binding repaired the R003 import problem in the observed child context. | Positive context receipt, exact `find_spec` origins, initializer hashes and environment JSON reporting scikit-image 0.25.2 from the frozen root. | **SUPPORTED for the bounded environment child.** | No scheduled scientific worker was launched, so scheduled-worker parity was not observed in R004. |
| Task modules were protected from dependency-root shadowing. | `centerline_core` and `d5_runner` specs point to the reviewed target; target precedes dependency root. | **SUPPORTED.** | This is source-resolution evidence, not a model result. |
| R004 failed because the environment child or import failed. | Payload exit `0`, positive context and empty stderr; controller exit `125` was added after the PID equality check. | **REFUTED.** | The admission failed at evidence acceptance. |
| PID equality was a valid ownership requirement on this host. | Owned PID `8572`; context PID `13500`; context parent PID `8572`. | **REFUTED.** | The observed Windows venv launcher uses a parent-child process pair. |
| R004 provides evidence against the centreline/distance-field method. | No task, output, model forward, training, evaluation or score exists. | **NOT SUPPORTED.** | D5 remains scientifically unanswered. |
| The scientific thresholds should be relaxed because R004 failed. | R004 contains no method measurements. | **NOT SUPPORTED.** | Only the PID control criterion is shown to be too strict. |

## Criteria and route decision

The same-PID control criterion was too strict and structurally wrong for the observed Windows launcher. It rejected stronger evidence than it asked for: the context receipt preserved the exact Run, executable, source roots, initializer hashes and a direct parent-child link to the owned process. This criterion should be replaced prospectively by an ownership predicate that accepts either `context.pid == owned_pid` or `context.parent_pid == owned_pid`, while retaining exact Run ID, command, executable, receipt hash and source-origin checks.

Do not lower D5's scientific criteria from this event. They were never evaluated. The constructive route is to modify the current execution control, not change the segmentation method yet:

1. preserve the R004 evidence and consumed admission;
2. prepare a new Run ID whose only substantive control delta is the launcher-aware ownership predicate;
3. test that predicate locally with same-process, direct-child, unrelated-PID and malformed-receipt fixtures;
4. if separately authorised, allow one fresh admission and one scientific attempt under a new package clock;
5. use the frozen CFD/GAPS outcome map only after a complete, interpretable D5 run.

If a valid D5 run later fails on both sources, redirect to the already defined shared evidence field plus source-specific renderers. R004 itself does not justify that method switch.

## Evidence integrity

- Retrieved directory: `retrieved_2026-10-21/HQ-ROAD-CENTERLINE-001-R004/`
- Remote files retrieved and matched: `20/20`
- Remote manifest: `retrieved_2026-10-21/remote_sha256_manifest_2026-10-21.json`
- Independent recomputation: `retrieved_2026-10-21/independent_recomputation_2026-10-21.json`
- Final read-only state: `retrieved_2026-10-21/remote_readonly_final_state_2026-10-21.json`
- Remote originals remain in place.

## Boundary

No R004 retry, second admission, R005, scheduled scientific task, training, remote repair, host/GPU switch, dependency installation, global environment change, Road420 or CRACK500-test access, dataset mutation, scientific-threshold change, publication, external message or public push occurred. This report does not authorise a successor execution.
