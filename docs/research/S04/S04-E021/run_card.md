# S04-E021-R001 — proposed single V0/V1 execution

Protocol:v1, [experiment.md](experiment.md). Date:2026-10-15 Europe/London.
Status:PREPARED FOR HUMAN APPROVAL / NOT STARTED / NO AUTHORIZATION FILE.

| Item | Exact proposed scope |
|---|---|
| Owner | current main chat only; method chat read-only, no duplicate implementation/fit |
| Producer | this Mac, closed-form CPU analysis only; no PINN training loop, SSH, GPU, Windows or CSD3 |
| Worktree | /Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-e021-physical-raw-20261015 |
| Branch/base | codex/s04-e021-physical-raw-20261015 / c7528d1 |
| Reviewed source | c883bfd8e4ecd37d2ae32dc3717a63db018f1ae2; no source change |
| Runtime commit | exact final commit containing this v1 card/protocol, identified in human approval; compare its seven source paths and lock/design to reviewed versions before launch |
| Attempt count | one guard invocation,total; nested fits/alphas are internal to this one attempt |
| CPU/runtime | 4 threads/noGPU; /Users/wenxiaofang/miniconda3/bin/python3; record actual host/version at launch |
| Budget | combined fit+report300s / aggregate sampled RSS2GiB / generated output100MiB, not per arm/fold |
| Output | /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/runs/S04-E021-R001 |
| Log | same runs directory / S04-E021-R001_guard.log |
| Receipts | same runs directory / S04-E021-R001_fit_guard_receipt.json and S04-E021-R001_guard_receipt.json; output / receipt.json |
| Approval artifact, future only | /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/control/S04-E021-R001_authorization.json |

## Preconditions after explicit execution approval

1. Human approval must name this protocol/card version, final runtime commit,
   one Run ID, machine, input/staging scope and budget. No approval is inferred
   from earlier design/code-review sends. No operational approval artifact now.
2. Confirm HEAD is the approved commit, clean tracked task/source paths, and
   `git diff c883bfd --` the seven files s04_raw.py/s04_raw_guard.py/
   s04_raw_report.py/s04_raw_checks.py/s04_raw_guard_checks.py/s04_d0.py/
   s04_g5_features.py under SENS_tensile is empty. Verify reviewed v2 unchanged
   from45b8d32, and frozen lock unchanged. Docs-only HEAD advancement must be
   recorded as such, not falsely called the review's original SHA.
3. Confirm no other copy of this Run is running/completed and no output/sidecars
   exist. Inspect only this owner's attributed cwd/cmdline; do not touch other
   users/processes. Any prior guard invocation consumes this single attempt,
   even if it fails. No automatic retry or R002.
4. Stage **six leaf symlinks only**, listed below, if missing. Never link a
   whole archive, use a glob, open sealed data, copy payload or change lock.
   Relative destination under new worktree is the same relative path as source
   under old E016 worktree. Refuse nonempty/conflicting destination; do not
   overwrite. Three other PIN paths in lock are already absolute, unchanged.
   Before launch use metadata checks only; frozen source hashes/state/arrays
   are verified inside the bounded loader, not a separate real-data pilot.
5. Create the named approval JSON only AFTER actual approval, with exact fields
   required by unchanged authorization():user_approved_real_fit=true,
   independent_code_review=APPROVED, experiment_id=S04-E021,
   run_id=S04-E021-R001, code_commit=approved runtime full SHA,
   design_commit=45b8d32, lock_sha256=cb9f63f8bd4b73afe0bd0f74bc7836018ce2e6bfcbd46edae80e7fef7b07868c,
   output=the exact absolute output above. Also preserve human approval reference
   and reviewed source commit for provenance. The JSON is an interlock, not
   proof of consent. Do not commit live approval secrets or fabricate approval.

Leaf source base:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-e016-request31-storage-block-20261009/`

| Same relative source/destination path | Role |
|---|---|
| local_archive/experiments/S04-E016/g5_export_20261013/geometry_native64_v4/mapping.npz | admitted geometry |
| local_archive/experiments/S04-E016/g5_export_20261013/fem_v3_retrieved/u011_s4.mat | development FEM |
| local_archive/experiments/S04-E016/g5_export_20261013/fem_v3_retrieved/u0115_s4.mat | development FEM |
| local_archive/experiments/S04-E016/g5_export_20261013/fem_v3_retrieved/u012_s4.mat | development FEM |
| local_archive/experiments/S04-E016/g5_export_20261013/fem_v3_retrieved/u013_s4.mat | development FEM |
| local_archive/experiments/S04-E016/g5_export_20261013/pin_v5_retrieved/hard5_u0115_s4.npz | development PIN |

Sources were checked by filename/size metadata only during card preparation;
no scientific contents read, no links made. No scientific data in new worktree.
No staging choice may include U0.1175/U0.125 or hidden confirmation siblings.

## Proposed one-shot command — DO NOT EXECUTE BEFORE APPROVAL

cwd must be the absolute worktree above. Exact command:

```bash
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 VECLIB_MAXIMUM_THREADS=4 CUDA_VISIBLE_DEVICES='' /Users/wenxiaofang/miniconda3/bin/python3 SENS_tensile/s04_raw_guard.py --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/runs/S04-E021-R001 --authorization /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/control/S04-E021-R001_authorization.json
```

No --synthetic, direct worker call, separate report fit, test, smoke, retry,
additional arm/seed, remote transfer or producer job. The guard launches fit
then report exactly once and records commands/PIDs/exits/hostname/dirty state.
Use its log/receipts; no separate unbounded console transcript file.

## Budget semantics and stop behavior

Unchanged reviewed guard starts timer after parent authorization imports/check,
before source loader and children. Its timer covers loader/hash/decode, nested
fits, full scoring and report; worker has295s internal reserve. Parent startup/
authorization and metadata staging precede the measured timer. This is the
existing guard's accounting, not a promise of ≤300s total shell lifetime.
RSS samples guard plus live child tree about every0.1s, includes real parent
imports after timer start; short peaks are not a hard OS allocation ceiling.
Generated-output accounting includes output tree and own log/stage/final receipt
sidecars with32KiB reserve; approval/control docs and source payloads are not
generated fit outputs. Receipt bytes may differ slightly after terminal write.
No budget or timer code changed for this registration.

At cap or child exception:terminate only attributed spawned process group,
TERM then KILL after0.5s if needed; retain outputs/log/terminal receipt, no
resume/retry. Invalid numerics/identity cannot become V0 fallback. Missing
receipts or incomplete report means incomplete evidence, even with saved
scores. Report failure does not authorize another render/fit invocation.

Prior94.3s/1.60GiB/10.8MiB is generated-data engineering evidence, not actual
decode/I/O, real-parent startup or conditioning guarantee. Mock paths/caps are
not real executions. Runtime can still hit cap:stop and report, do not enlarge.

## Completion and next decision

Freeze existing evidence at either terminal state. Record execution and
retrieval separately; inspect identity, tables/JSON, all357 rows/four folds,
saved fixed fields, warnings and both decision images without refitting.
Synthesize solely by experiment.md outcome table; partials cannot rescue it.
Update experiment record and the existing Obsidian note/Roadmap. Further
evidence review messages require their own preview/approval. No automatic
confirmation opening, S04-E017, NN, MOO or coupled rollout.
