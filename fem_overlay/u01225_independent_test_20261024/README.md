# U0.1225 independent Hard5 FEM overlay

**Status:** prepared locally only on 2026-10-24. This package has not been copied to Windows, MATLAB has not been invoked, and no FEM output directory has been created. It is not strict-test eligible: it cannot run until an independently reviewed, hash-bound prelaunch custody-evidence receipt and `STRICT_TEST_CUSTODY_READY` policy state exist.

`run_hard5_u01225_independent_test.m` is a small launcher outside the frozen producer snapshot. It calls the snapshot's existing `run_hard5_stage0b_case(cfg, options)` and `run_SENS_hard_recovery_native_q4_capture(cfg, options)` interfaces. It does not alter either source file.

## Frozen binding

| Item | Value |
| --- | --- |
| New run ID | `hard5_u01225_stage0b_597465a720694a6ea7001a8792de4189` |
| Case identity | `hard5_u01225_stage0b` |
| Protected custody parent | `C:\q4runs\fixed_weight_custody` |
| Custody root | `C:\q4runs\fixed_weight_custody\u01225_independent_test_20261024_v1` |
| FEM output root | `C:\q4runs\fixed_weight_custody\u01225_independent_test_20261024_v1\archive_root` |
| Snapshot | `C:\q4runs\request31_phaseA_snapshots\hard5_stage0b_862992a60edc7f59_b5c39464cd4091f6` |
| Required snapshot commit | `862992a60edc7f59335365beacb5c71fc8592a7a`, clean |
| Qualification authority | `C:\q4runs\stage0b_hard5_qualification_20260829_v5\hard5_u012_stage0b_qualification` |
| Qualification manifest hash | `b5c39464cd4091f67abff3944b23acf11a6d2cf7ada4be0e78c2de4c375fa33e` |
| Qualification run ID | `hard5_u012_stage0b_qualification_203f921c-4911-4a9a-bdd1-8f34c7d91d7c` |

The launcher verifies the snapshot commit, clean status, four source-file hashes, the U0.12 qualification receipt/provenance, and five qualification artifact hashes before it creates the archive root. It rejects an existing archive root, overlapping source/output paths, and another MATLAB process. It also rejects direct invocation: `FW_U01225_CUSTODY_LOCK_PATH` must name an immutable lock in the custody root and the launcher itself must be executing from that protected root.

The U0.12 receipt is used only to bind the unchanged solver controls. It is not set as `reference_dir`, so no prior trajectory, checkpoint, or target field enters the U0.1225 solver.

## Frozen load contract

`Umax = 0.1225`; the retained nominal factors are `[0.25, 0.5, 0.75, 1.0, 0.0]` and the effective factors are `[0.249999, 0.499999, 0.749999, 0.999999, 0.0]`. The resulting nominal displacements are `[0.030625, 0.06125, 0.091875, 0.1225, 0]`; the effective displacements are `[0.0306248775, 0.0612498775, 0.0918748775, 0.1224998775, 0]`.

The configuration retains the qualified Hard5 controls: hard crack, separate zero-load recovery, clipped recovery projection, fatigue reset, cyclic loading, loading discretisation, `n_step=5` from `requested_n_step=8`, `R=0`, `res_stiff=0`, `alpha_T=0.5`, the existing tolerances/iteration caps, and the right-layer penetration detector with three confirmation cycles. It is a fresh `production_new` run with a hard `max_cycle=163`: the frozen production validator requires a first detector hit in c1--c160 and confirmation exactly three cycles later. If there is no qualifying hit by c163, the producer reports validation failure rather than sealing a trajectory; those raw files, if any, are not an admissible independent-test archive and will not be extended or rerun. An archive with a later first hit is likewise rejected and never extended. The inherited `requested_cycles=1` field only selects the legacy peak-capture list, which remains disabled in this Stage 0b path; it does not limit the five-substep producer to c1.

## Custody-gated deployment — do not run from this package

`run_u01225_custodian.ps1` is the only intended remote entry point. It requires an already-existing protected custody parent with the policy's exact non-development owner and only the custodian, `SYSTEM`, and local administrators in its ACL. It verifies copied payload hashes, a hash-bound [`prelaunch_custody_evidence.json`](prelaunch_custody_evidence.json), fixed splits, role separation, parent owner/ACL, scoring controls, and readiness state before it atomically creates a fresh child custody root. It records one permanent launch lock, redirects MATLAB output into that root, and writes a hash-bound terminal receipt outside the archive. It exposes neither target arrays nor event values to the development caller.

The committed [`custody_policy.json`](custody_policy.json) and evidence receipt deliberately contain placeholders, so the wrapper rejects them before any remote directory or MATLAB process is created. [`run_u01225_scoring_release.ps1`](run_u01225_scoring_release.ps1) is a later custodian-only, hash-bound one-way archive handoff to the separately protected scorer root; before recording a handoff it verifies the source and transferred archive manifests and every listed member, and it does not score or train. The exact pre-result amendment, bootstrap verification, release order, and limits are in [`CUSTODY_PROTOCOL.md`](CUSTODY_PROTOCOL.md). No direct `matlab -batch` command is valid for this condition.

On success the existing Stage 0b runner is expected to create and seal `C:\q4runs\fixed_weight_custody\u01225_independent_test_20261024_v1\archive_root\hard5_u01225_stage0b`, including native-Q4 static data, initial `pre_cycle_committed` state, five retained states per cycle, per-state convergence metadata, provenance receipts, validation receipt, and SHA256 manifest. That archive remains custodian-only until the separately frozen scoring release.

## Unresolved before execution

The prepared overlay and custody wrappers have not been executed even in validation-only mode, so their contracts are source-inspected rather than runtime-proven. An immutable reviewed Git anchor, custodian/scorer appointment, complete development roster, protected-parent and scoring-parent owner/ACL evidence, non-observable custodian process, remote launcher copy, producer preflight, actual FEM launch, scorer transfer, and independent scoring all remain separate actions. A common Windows identity or a development administrator cannot establish blindness; without the documented role/ACL/process separation this condition remains **prepared, not eligible** as a strict independent test. No U0.1175 archive or target array is referenced by this package.
