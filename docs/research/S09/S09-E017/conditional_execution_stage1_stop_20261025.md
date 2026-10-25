---
experiment_id: S09-E017
run_id: S09-E017-R001-factorised-head-p0
attempt_id: s09e017-admissiononly-20261024-r2
status: ADMISSION_ONLY_STOPPED_GPU_COMPUTE_PROCESS_PRESENT_NO_RETRY
scientific_operations: 0
date: 2026-10-25
---

# S09-E017 conditional execution Stage 1 stop

The user approved the exact conditional admission-to-training card. The owner
materialized the fixed Stage 1 authority at
`2026-10-25T16:36:24.448230+00:00`, SHA256
`f171af4b2803e95a9cbeea249228f958248ebfbd8f8ed87e1cc6c64c807cf945`,
and the guard consumed it before networking.

The single connection reached `GPUServer8`. Its read-only precheck reported uid
1010, clean exact commit `2002538d9a30c8d4006ccaff5959cd214958fc82`
and no blocked production path. The repaired local staging layout completed,
so the prior authority-path defect did not recur. The resolver and metadata
admission then reached the frozen GPU metadata check and stopped with the exact
exception `compute process present on frozen GPU`.

The guard returned exit 1 after 12.871 seconds. It preserved authority
consumption, local mechanical check, stdout, stderr and terminal guard
receipts, with no evidence-write error. It did not retry or reconnect, so the
identity of the competing GPU process and the post-stop remote helper/attempt
state were not inspected.

The Stage 2 local evidence root and execution authority remain absent. No final
execution resolver, production admission token, detached session, model,
forward, autograd, optimizer or training update was created. The Stage 1 path
is standard-library metadata control with CUDA disabled; this stop is shared
GPU availability evidence, not a model, physics or scientific failure.

Any future attempt requires a fresh human decision. It must not kill an
unattributed shared-node process, reuse this consumed authority or infer that
GPU 5 is now idle.
