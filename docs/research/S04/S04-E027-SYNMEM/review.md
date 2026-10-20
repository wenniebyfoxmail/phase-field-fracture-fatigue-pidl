# Independent preparation review — S04-E027-SYNMEM

Reviewer role: physics_transition_audit. Scope: the new synthetic history input, observation, orchestration, supervisor, plotting and protocol implementation in `/Users/wenxiaofang/phase-field-fracture-with-pidl/worktrees/synthetic-memory-mechanism-20261020`. This reviewer proposed the initial parameter design but did not author the generator, observer, scientific runner, supervisor or plot implementation. On explicit parent request, the reviewer added artificial transaction regression tests only (`tests/test_synthetic_history_transaction.py`).

Final verdict: **REVIEW_PASS for preparation/code scope**, bound to exact implementation commit `95709f9ca50edd6da2377d983ab1f2e994a0b31b` and spec `bff278a41264db2070745a31b90ff742a19b88b1bbc66ad325073ff08f832f23`. HEAD and a clean working tree were independently checked. No remaining blocking implementation/control issue was identified in this scope. This is not execution permission: `authority.json.enabled` remains false, and no native experiment has run. Later review/authority metadata-only changes may follow the explicitly enforced whitelist; scientific/control source or spec changes require a new review.

## Scientific implementation findings

No blocking scientific implementation defect has been identified in the inspected version:

1. **Legal histories.** The raw `AcceptedState` is explicitly an unsettled feasible payload, not an accepted-equilibrium claim. Each branch performs an actual zero-load native solve first, then the two branches' numerical u/d/A/driver/f/opaque arrays must agree. Every later prefix/probe/future state passes the unchanged native solve, envelope binding, atomic StateStore commit, reload and exact expected-context check. The code never edits A/f/d to manufacture a paired origin.
2. **New schedule context is compatible with the original accepted-state envelope.** Required physical keys, settings/coupling hashes, reaction DOF ordering and immutable trajectory identifiers match the existing contract. Extra segment/segment_cycle/phase keys are included in the hashed context. The implementation supplements rather than loosens the old same-problem comparator.
3. **Shared probe/future and source identity.** The pair contract binds source/root/mesh/physics/material/ordered BC identities, common probe, origin phase and future suffix. Distinct prefix/schedule IDs remain distinct. Both arms have 20 prefix cycles and the same probe phase; the step-refined trajectory includes an unloading midpoint and compares on physical future cycles.
4. **No future selection leakage.** All six current masks are generated and the complete-mask equivalence/anchor decision is made before any future suffix is advanced. No-match returns an inconclusive result with future_executed=false. H20 is the sole primary endpoint; H5/H10 and threshold sensitivity cannot rescue it.
5. **Restart control checks every accepted future step.** Both base origin archives are reloaded, the backend/workspace is rebuilt, and each subsequent full AcceptedState fingerprint is compared to its reference at the same original load index. It is a same-state deterministic continuation control, not a fatigue-off counterfactual. Scientific failure is not automatically retried.
6. **Observation claim remains appropriately narrow.** The primary observation is the entire fixed 64x64 Q4-interpolated d>=.5 mask. Native hidden d may differ. A positive result therefore cannot isolate A causally, demonstrate added value over known-load exposure baselines, qualify a physical teacher, or prove road predictability. The protocol explicitly retains these limits.
7. **Resource count is honest.** The frozen schedule has 1846 maximum physical-step attempts including six independent zero-settles and the 200 restart-suffix steps. Four host-hours is a hard truncation cap, not a runtime forecast or completion promise. Direct mechanics preserves the original fresh force/KKT acceptance; safeguarded Anderson remains a guess only.

Relevant inspected lines at the reviewed commit:
- `source/synthetic_history_experiment.py:77-128`: initialization, BC, schedule and context binding.
- `source/synthetic_history_experiment.py:133-163`: solve/commit/load/current-context checks and per-step replay identity.
- `source/synthetic_history_experiment.py:170-184`: fresh-backend persisted-origin restart.
- `source/synthetic_history_experiment.py:187-231`: zero-settle equivalence, current-only matching and future admission.
- `source/synthetic_history_experiment.py:232-258`: fixed horizons, diagnostics, restart-before-final-result.
- `source/synthetic_history_inputs.py:214-285`: reconstruction of schedules and explicit pair comparability.
- `source/synthetic_history_observation.py:5-66`: renderer, anchor, full matching and across-variant stable-difference formula.

## Control findings raised to the author

- **Resolved in inspected working code:** tracked-only cleanliness originally omitted untracked/ignored source shadows. The added import-tree audit now rejects unreviewed source/tools files and symlinks, including package-directory symlinks; ordinary generated `__pycache__` bytecode is excluded. This is operational source consistency, not an adversarial Python sandbox.
- **Resolved in inspected working code:** resource checks originally ran only while the child was alive. The supervisor now rechecks wall/storage at child exit and before a clean terminal receipt, with terminal-record storage reserve. Thus a last output cannot silently turn an over-budget run into completed.
- **Resolved in protocol:** the documented authorized command originally lacked `--execute`; the default intentionally only inspects. The launch template must include that explicit flag.
- **Resolved and independently rechecked at the final commit:** cleanup had a poll-to-kill race. `tools/run_synthetic_history.py:88-103` now tolerates only ProcessLookupError around both TERM and KILL, still waits for the worker, and `:232-235` records other cleanup errors instead of skipping the terminal receipt. Two artificial exit-race tests cover immediate exit and the TERM-timeout/KILL path; no real process or producer was launched.
- **Added evidence preservation:** failed native solve now records its accepted predecessor, step, exception and StepFailure.work; persistent native work/iteration trace is retained. Hard-kill partial traces remain partial, never accepted-state evidence.

The supervisor is statically designed to require an enabled exact-spec authority record, independent code-review binding and an eligible clean producer checkout; default inspection and disabled authority do not execute. Worker execution is producer Linux-only, uses a parent-death guard, startup admission pipe, CPU affinity, RLIMIT_AS, hidden CUDA devices, per-step marker watchdog, storage monitoring and whole-run cap. Full Linux process/resource behavior has not been exercised by this review, and must not be described as a scientific run or a measured peak-RSS result.

## Executed lightweight checks

- The default `/opt/homebrew/bin/python3` lacked NumPy: one attempted artificial check stopped during import, before backend construction or solver activity. No dependency installation was performed.
- With the existing project virtual environment, an independent artificial integration used StubBackend and artificial StepProposal objects. It traversed 16 real metadata/StateStore transitions with origin at step 11, then reloaded the origin and replayed five suffix steps; every full-state fingerprint matched. Output: `/private/tmp/synmem-review-artificial-xd30e5zm`. This was not a FEM solve.
- At the parent's explicit request this became `tests/test_synthetic_history_transaction.py`, with **3 tests passed in 0.19 s**: real custom context/StateStore binding plus fresh-backend exact restart; rejection on the first perturbed intermediate replay state even if later artificial steps would reset it; and failure preserving the durable old state and complete artificial work record.
- Final independent targeted rerun on `95709f9ca50edd6da2377d983ab1f2e994a0b31b`: **23 tests passed in 0.19 s** for `tests/test_synthetic_history_experiment.py` and `tests/test_synthetic_history_transaction.py`, covering artificial arrays, disabled authority, untracked/import-symlink rejection, final resource failure, process-exit races, no-future-on-no-match, real StateStore integration and artificial failure preservation. This reviewer did not rerun or independently certify the author's broader test count.
- Exact command: `PYTHONPATH=source:tools OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_implementation_20261019/venv/bin/python -m pytest -q tests/test_synthetic_history_experiment.py tests/test_synthetic_history_transaction.py`.
- Independently ran the default inspection CLI with the frozen spec: returned `maximum_steps=1846`, `trajectories=6`, `restart_suffixes=2`, `primary_horizon=20`, `execution_authorized=false`. The explicit execution template now includes `--execute` (`experiment.md:106`).

No native notch solve, model forward, autograd, training, SSH, future-data inspection or physical experiment was performed. Test outcomes support preparation/control compatibility only. The frozen small-mesh parameters remain unexecuted, and valid no-match, no-activation, zero robust-difference, failure and budget-limit outcomes remain possible.


---

# S04-E027-SYNMEM — frozen design/observation review

- Reviewer: `/root/observation_state_audit` (independent read-only design/observation reviewer).
- Date: 2026-10-20.
- Reviewed commit: **`95709f9ca50edd6da2377d983ab1f2e994a0b31b`**.
- Worktree: `/Users/wenxiaofang/phase-field-fracture-with-pidl/worktrees/synthetic-memory-mechanism-20261020`.
- Identity check: `git rev-parse HEAD` returned the reviewed commit; `git status --short` was empty at review.
- Verdict: **REVIEW_PASS — design/observation scope only. No blocking finding in this scope.**

This verdict covers the fixed mask, current matching, conditional continuation, H20 robust-pixel decision, hidden-field/A interpretation, and consistency with the written protocol. It is not physical-generator qualification, a runtime/controller review, execution authority, or a scientific result. Those first two review scopes belong to the other reviewer. No tests, notched solve, training, remote action, or future scientific data were run/read by this reviewer.

## Checked conditions and evidence

Paths in this table are relative to the absolute worktree above; each line refers to the frozen commit.

| Condition | Review conclusion | Evidence |
|---|---|---|
| Fixed current observation | 64×64 whole-domain pixel centres, canonical Q4 bilinear interpolation, and d_sample≥0.5 are implemented without crop, morphology, adaptive threshold or full-d matching. Array axes agree with the controlled mesh generator. | `source/synthetic_history_observation.py:5–24`; `source/synthetic_history_inputs.py:69–95`; `source/synthetic_history_experiment.py:84`; `docs/research/S04/S04-E027-SYNMEM/experiment.md:41–47` |
| Exact six-mask matching | `current_match` accepts only Boolean masks of shape `(3,2,64,64)` and compares every pixel across both arms and all three variants. Hidden d/A/r/f and response fields cannot enter this function. The 32-pixel anchor is fixed at rows31:33/cols8:24 and is checked, never painted into a mask. | `source/synthetic_history_observation.py:27–40`; `source/synthetic_history_experiment.py:202–223`; protocol `:43–47` |
| Origin and conditional future | The origin is the final common-probe step. All six prefixes reach their predetermined origins before matching; missing anchor errors and a nonidentical origin returns `inconclusive` with `future_executed=False`. No continuation precedes that decision. Hidden-field/probe diagnostics read only origin/probe states and do not change qualification. | `source/synthetic_history_experiment.py:96–101,187–231`; `tests/test_synthetic_history_experiment.py:132–160` |
| Consistent numerical variants and endpoints | Both arms use the same future and probe within each variant. The same frozen prefix/probe/suffix construction is used for base, space and half-step variants. Half-step construction subdivides unloading as well as loading. Future checkpoints select the unloaded end of the specified future cycle rather than mixing raw load indices. | `source/synthetic_history_experiment.py:27–74,165–168`; `tests/test_synthetic_history_experiment.py:53–62`; protocol `:28–33,51` |
| Robust future difference | For each arm, pixels must be identical across all three variants; then the two arms must differ. The code reports robust count/area, all three full arm-to-arm XOR counts, per-arm unstable counts and the full unstable union map. The Boolean formula matches the written definition. | `source/synthetic_history_observation.py:43–60`; `source/synthetic_history_experiment.py:232–239`; `tests/test_synthetic_history_experiment.py:42–50`; protocol `:55–59` |
| Unique primary decision | `supported` is determined exclusively by H20 robust count > 0, after origin qualification, completed continuations and both base restart calls. H5/H10 and thresholds 0.45/0.55 are diagnostic and do not participate in `supported`. A failed restart raises before any positive result is written. | `source/synthetic_history_experiment.py:240–257`; protocol `:53–66` |
| Same-state null prerequisite | The observation decision is conditional on exact state replay, rather than treating different prefixes as a null. Each base suffix replay compares the full accepted-state fingerprint at every step; the backend is reconstructed. This review checked its use as a prerequisite, not solver correctness. | `source/synthetic_history_experiment.py:156–183,249–254`; protocol `:53` |
| A/hidden-field limit | The protocol explicitly permits hidden d and other fields to differ while I0 matches. Nonzero common-probe response and A/f diagnostics are labelled diagnostics only. A positive result cannot uniquely identify fatigue A, prove usefulness of history conditional on known past loading, establish Q2, or validate a road/physical sensor. | `source/synthetic_history_experiment.py:204–215,252–256`; protocol `:7,41,47,59,66`; `tools/plot_synthetic_history.py:112–115,217–232` |
| Protocol and reporting consistency | Committed spec and code freeze agree on 64 pixels, threshold 0.5, the three variants, the fixed histories/probe/future, and H20. `validate_spec` rejects a changed spec. The saved-output renderer keeps the complete origin masks and robust/unstable H20 maps, shows every declared horizon and distinguishes no-future from a negative future result. | `source/synthetic_history_experiment.py:27–57`; `docs/research/S04/S04-E027-SYNMEM/spec.json:24–132`; `tools/plot_synthetic_history.py:139–237` |

## Test evidence and review method

The implementation owner reports **115 focused cases passed in 9.02 s**, followed by **23 targeted cases passed in 0.21 s** after the controller repair. The committed `docs/research/S04/S04-E027-SYNMEM/validation.md:7–10` records these as separate checks, with artificial arrays/stub states for the new logic, and explicitly says no notched scientific trajectory was run. I inspected the relevant test source; I did not rerun tests and do not describe these results as my independent execution.

Observation-specific coverage inspected includes affine Q4 interpolation/axis order, visibility of the fixed anchor on both grids, whole-mask mismatch detection, within-arm numerical stability versus arm difference, full cycle subdivision, rejection of changed specification, and stopping before future execution on current mismatch (`tests/test_synthetic_history_experiment.py:16–74,132–160`). Plot tests use artificial Boolean fixtures and are not scientific evidence (`tests/test_synthetic_history_plot.py:1–45`).

## Limits retained by this approval

1. A positive result means only that this **prespecified digital geometry observation** aliases reachable histories with different common-load future masks in the tested numerical configuration. One pixel meets an existence criterion; it is not a practical effect-size threshold.
2. The three numerical settings are tested sensitivity checks, not convergence or a discretization-error bound. Unstable pixels remain visible and reported.
3. The renderer is specialized to the controlled canonical structured-mesh generator used by this runner. It is not validated for arbitrary point/cell ordering or unrelated meshes. This is consistent with the frozen scope and is not a blocker.
4. Continuous native d can differ beneath the matched binary images. Therefore a positive result may reflect unresolved current damage, fatigue accumulation, or both; it cannot uniquely identify A as the memory mechanism. A no-match or zero robust difference does not prove that geometry is sufficient.
5. Threshold-margin reporting would be a useful diagnostic, but its absence does not invalidate the declared finite digital criterion. No tolerance, threshold, horizon, region or parameter may be altered retrospectively to rescue the result.

## Frozen file digests

These are SHA-256 hashes of file bytes, **not** the runner's canonical JSON `spec_id`:

| File | SHA-256 |
|---|---|
| `docs/research/S04/S04-E027-SYNMEM/spec.json` | `32de468443668dae55d90f1722f3cce667c53d05ddccae9e1b468039f96632fd` |
| `source/synthetic_history_observation.py` | `f417409017d2c2ea011cc712d13699638d0442c3ca966018f8c5fa7d1c0e4d18` |
| `source/synthetic_history_experiment.py` | `d624018113ac8c5291070baa524d2d0c15fc1abd20b8b558b4288a52288f1c99` |
| `docs/research/S04/S04-E027-SYNMEM/experiment.md` | `08c52f77222b9f7989085b69af65563f3e9f0007785f4d2def30ceef52eb30e9` |

This scoped review does not enable `authority.json` or authorize any producer run. Claim-changing edits to these scientific/observation rules require a new version-specific review.


## 2026-10-20 Execution authority and producer mapping correction

The human user approved one CPU execution and then explicitly clarified: “按方案写出的 GPUServer8，使用陶博服务器的 CPU”. The physical producer remains the reviewed Linux GPUServer8 at drtao@172.16.100.2, with the same owner root and budget. The historical frozen producer.alias `gpu-server` was an erroneous mapping: the local SSH alias actually targets Cambridge D-26-09. It will not be used for dispatch. This preparation error was caught before any scientific launch. The actual SSH target and exact user approval are recorded in authority.json, outside the unchanged producer object. Independent read-only control reviewer physics_transition_audit confirmed alias is not used by the runner and no scientific/control change is needed. The original code-only reviews remain historical; execution authority comes from the user's new approval.


---

# R002 accepted-prefix recovery: independent implementation review

2026-10-20. Reviewer: `/root/physics_transition_audit`.

**Verdict: REVIEW_PASS for the control/recovery implementation at `bc334c0c5650b3632e7d3eb76848995091113a7e`, and the disabled R002 authority draft identified below.** No blocking implementation issue was found for the exact, previously audited R001 inputs. This verdict does not assert that original-producer admission has occurred, enable execution, reset a consumed permission, or establish a scientific result. The required original-producer zero-solver strict admission and storage-footprint measurement are still pending at this review.

This was a read-only implementation review with local artificial tests. No FEM solve, model call, SSH, remote action, source edit, or change to R001 raw was performed. The reviewer authored three original artificial transaction tests at the parent's explicit request; the recovery implementation and its added tests were written by the parent. That test contribution does not constitute authorship of the implementation reviewed here.

## Exact versions and authority

- Reviewed checkout: `/Users/wenxiaofang/phase-field-fracture-with-pidl/worktrees/synthetic-memory-mechanism-20261020`; HEAD is `bc334c0c5650b3632e7d3eb76848995091113a7e`. No uncommitted source/tools difference existed during review. The sole tracked working-tree difference was the new disabled authority metadata.
- Frozen scientific spec remains `bff278a41264db2070745a31b90ff742a19b88b1bbc66ad325073ff08f832f23`; current saved spec and immutable R001 saved spec compare exactly as JSON objects. No equation, material, schedule, mesh, solver tolerance, camera/matcher, primary horizon, or replay criterion changed in this control commit.
- Disabled authority draft SHA-256: `9351dee431191e1750fd1ef15fa90450c65f59289c8bc326f29e59133b68a29e`. It names reviewed commit `bc334c0c...`, exact R002 root, physical GPUServer8 CPU producer, new conditional HQ authority, original task deadline, 253 prior attempts, and a conservative 1 GiB prior/storage-stage debit.
- Parent verified the actual human message in HQ thread `01a14bb9-6cd1-7ee2-9647-5190d786f7ba`, turn `01a15b4c-1031-7981-a37c-7800235e5843`, delegating coordination including compute until 2026-10-21 09:00 UK; HQ subsequently gave one conditional revised recovery attempt within the original cumulative limits. This review relies on that parent-verified human authorization record, not on an agent manufacturing authority. The direct human machine clarification remains GPUServer8 CPU. The mistaken frozen alias `gpu-server` is historical metadata, not a connection instruction; endpoint is `drtao@172.16.100.2` with SSH config `/dev/null`.
- The old R001 receipt remains consumed and immutable. The new authority is disabled at review. Before enabling it, the parent must bind the new review receipt and commit the permitted metadata-only changes; the current old `review.json` still refers to `95709f9c` and cannot admit this implementation. Existing `verify_authority` rejects mismatched review/authority, dirty tracked source, unreviewed code deltas, and untracked/symlink import-tree changes.

| Reviewed implementation | SHA-256 |
|---|---|
| `source/synthetic_history_recovery.py` | `f5f6a56b25a0c0ee685177760358430f9dd37ea72c69b906ed29ab3c8f1b7788` |
| `source/synthetic_history_experiment.py` | `02702e17b18dd088bf9b18553eaaae34787664fa77bc42fef678d21b6b7078bc` |
| `tools/run_synthetic_history.py` | `824bf09cf7821b26e4ece05139f3f41ae1b86492e9f4eac9e8c2d29ef4f0e502` |

## What was checked

1. **Exact immutable source admission.** `synthetic_history_recovery.py:29–74` fixes the reviewed R001 source/R002 output, old source identity, 253 debit, four prefix counts, one revision, and absolute deadline. It checks the exact manifest path and digest, all member hashes/sizes, safe relative paths, complete file set, member/ancestor/extra symlinks, original spec/receipt/progress/control-stop identity, absence of prior result/match/failure, and absence of the old producer PIDs. Manifest SHA-256 independently matches the local retrieved file: `0b76d4704cb25e4db7c763332d58104fb655f68d5ffb987af3e18e95e2b32df5`. A reused PID can conservatively reject admission; it does not permit an unsafe restart.
2. **Whole accepted chains, not iteration candidates.** `synthetic_history_recovery.py:77–154` compares pair/schedule/mesh/ordered BC identities, all snapshots from declared initial through accepted terminal, expected envelopes and transitions, version increments, original certificate thresholds, d/A irreversibility, opaque fields, exact applied boundary values, and saved-psi history recurrence. Pair comparison uses canonical object hashing, avoiding the earlier tuple-versus-JSON-list false failure. Only a missing final snapshot/ledger row may be reconciled; interior gaps and differing latest are rejected. The extra version and symlink checks are present in this exact commit.
3. **All four chains before new work.** `synthetic_history_recovery.py:157–188` validates base_low106, base_high106, space_low40 and space_high1 before copying any recovered accepted prefix or admitting a solver step. Accepted NPZ payloads are copied, not rebuilt from numerical fields. `space_low/latest.npz` supplies snapshot0040 and the missing event, whose whole-step wall time is explicitly null and whose recovery provenance states zero new solve. The source is neither modified nor unlocked. Each restored latest is loaded and checked again.
4. **No repeated settle or prefix.** `synthetic_history_experiment.py:187–211` first constructs fresh declared contexts, restores all four chains, and advances by the loaded `load_index`. `advance(1)` is an empty slice for already accepted prefixes; the equality check explicitly loads state0001 rather than comparing low/high history endpoints. New load-step branches still get their own lawful zero-settle. Common probe, six-current-mask equality before any future, common future, and both base every-substep exact-state replays retain their original behavior. Source identity remains the original `e8ac73f6...`; actual new control commit is recorded separately.
5. **Cumulative resources and one revised identity.** `tools/run_synthetic_history.py:97–105,153–187,208–221,254–294` charges prior storage, fixes the original epoch deadline, starts the attempted-step counter at253, and applies the original 1846 ceiling. `253 + 1593 = 1846`; there is no spare scientific step. Remaining work is base future/replay400 + space remaining-prefix/future371 + two load-step full trajectories822. No old accepted step or additional scout may be re-solved. Four CPU affinity/threads, hidden CUDA, 8 GiB RLIMIT_AS, 120 s step cap, 20 s cleanup margin, no automatic retry, fresh R002 directory, parent-death guard, and process-group cleanup remain in force.
6. **Narrow filesystem repair.** The storage scan now calls stat once per entry, counts regular files, and ignores FileNotFoundError only for known disappearing `.json-*`, `latest.npz.trial-*` or `latest.npz.lock` entries. Other missing/permission/IO failures still stop. Original polling/final checks and 64 KiB terminal reserve remain. Prospective supervisor exception traceback/filename are recorded. The R001 original error lacked those details; the exact original pathname remains unknown, although the symptoms agree with the independently reproduced atomic-file race.

## Strict history recomputation versus immutable copying

The local Mac dry validation failed `array_equal` when reconstructing accepted history from the saved psi and Q4 interpolation. The retained `recovery_cross_platform_roundoff.json` reports maximum A difference `4.336808689942018e-19`, driver difference `1.3552527156068805e-19`, no f difference, and maximum discrepancy about `10.478 × eps × whole-field scale`. This is distinct from payload/hash corruption: original states and exact copies remain byte-preserved.

Keeping strict production comparison is appropriate for this particular recovery. The reviewed recomputation uses the same map as `hybrid_incremental.py:129–134` and `hybrid_history.trial_history`; no accepted fields or original acceptance thresholds were changed. A zero-solver admission on the original GPUServer8 numerical runtime and four-thread settings must establish whether strict equality holds there. Package versions are checked again in the worker. If strict admission fails, stop and retain that result; do not silently add tolerance or recompute consumed prefixes.

The proposed prelaunch admission may build declared geometry/contexts and copy verified accepted payloads into stage scratch, but it must not call `run_experiment`, `Trajectory.advance`, any solver, or write the R001 source. Its receipt must establish zero new physical attempts, complete 253-state validation/copy fidelity, and original runtime identity. This review has **not** observed or certified that producer receipt.

## Independent local validation and remaining operational conditions

Executed only the artificial/control suite with the existing local venv, `PYTHONPATH=source:tools`, bytecode/cache writes disabled, and one BLAS/OpenMP thread:

`tests/test_synthetic_history_experiment.py` + `tests/test_synthetic_history_transaction.py`: **36 passed in 0.25 s**.

These checks exercise mocked orchestration, synthetic arrays, filesystem races, original contract/store with artificial proposals, absent terminal-event recovery, changed schedule/interior-gap rejection, cumulative resource limits, and process-exit races. They do not establish real prefix strict admission, convergence, runtime benefit, or a scientific Q1 outcome. The separate earlier independent archive audit remains the evidence for the 253 real accepted states.

Before the one revised dispatch, retain evidence of: original processes absent; exact source manifest still unchanged; original-producer strict zero-solver admission; measured R001 plus old/new stages and admission scratch footprint at most the declared 1 GiB debit; remaining absolute deadline capacity; and the final exact metadata-bound authority/review. The 1 GiB figure is a conservative reservation, not a measured scientific-output quantity. Current R002 output plus that debit must remain within8 GiB. Original deadline is `1792547320`; it is never four fresh hours from R002. Subsequent retrieval/analysis still consumes the task envelope.

R001 remains an incomplete control failure, not a scientific negative. Two base masks happen to agree, but the full six-mask current test and common future have not been evaluated. Q1 is restricted to the declared synthetic observation; any eventual positive cannot isolate fatigue A from all hidden continuous fields or validate real-road prediction. A current no-match must still stop before future. A further failure is preserved and stops; this review grants no third attempt.

## Original-producer admission, 2026-10-20

On GPUServer8 with the original Python package versions, strict zero-solver recovery admitted all 253 accepted states; source hashes, parent chains and saved history recurrences passed without relaxed tolerances. Source was not modified and original processes had exited. Staging plus R001 occupied 203,085,780 bytes, within the conservative 1 GiB cumulative debit. Receipt: `/mnt/data2/drtao/wennie/pf_synmem_recovery_bc334c0c_20261020/preflight.json`. This records a mechanical admission; R002 execution rests on the fresh bounded HQ authorization documented in authority.json. The original R001 authority remains consumed.
