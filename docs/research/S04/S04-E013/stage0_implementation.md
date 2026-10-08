# S04-E013 Stage 0 implementation

Status: c60 conditional UV reference and paired-control export admitted by independent Evidence review; candidate training not authorized.

## c60 strict UV reference

Runner: `scripts/censor_projection_diagnostic/produce_c60_uv_reference.py`.

The runner admits the exact E010-qualified `c60s3` prior and `c60s4` accepted target by SHA, reconstructs the target trial-fatigue coefficient once, freezes damage/prior/fatigue, and solves displacement only. It requires the common NumPy/Torch native-Q4 assembly to agree and retains `archived_matlab_oracle=NOT_AVAILABLE_C60`. It emits original/polished fields, `rho_u`, BC checks, hard-KKT diagnostic, field-change norms, immutable-state checks, and zero training/damage-solve/history-commit counts. A pass may create only a conditional fixed-damage/frozen-fatigue UV reference; `full_teacher=NOT_QUALIFIED` remains fixed.

Required locked inputs:

- `qualified_fields.npz`: `ecee498054293f66c881a7bcf08a51b1b0315b4e2d11fa20a50c7bbe204f16c5`;
- `c0060_s03.mat`: `b673ac45979882a5b5ac9f8bbb31d293690cb3e9b419b213e948aaee756d81e2`;
- `c0060_s04.mat`: `267ea160d607a374359cd62851fe508a0939bbda4fbba24fc9fd83a15c772b65`.

## Paired exact-native-Q4 eta0 exporter

Runner: `SENS_tensile/export_s04_e013_paired_eta0.py`.

This is read-only post-processing of the completed `aaf13fd` control archive. It uses the recovery-offset mapping

`step = 1 + 5*(cycle-1) + (substep-1)`

and requires:

- c20: steps 97/99/100;
- c60: steps 297/299/300;
- c82: steps 407/409/410;
- c83: steps 412/414/415;
- control own-first-event: c85s4 step 424.

Every state includes its own `step-1` checkpoint as the prior. The exporter writes nodal displacement, accepted/model damage, prior damage, committed/prior fatigue history, accepted/prior/current drivers, degradation, native-Q4 GP strain/damage gradients, and element energies. It asserts the native-Q4 mesh signature, `[86408,4]` history shape, model/checkpoint damage agreement, finite values, and exact state mapping. No FEM state is inserted into the PIDL trajectory.

The old checkpoints do not embed a step number or load. The exporter therefore requires the exact locked producer source snapshot, production log, archive settings, and mesh by SHA. It checks the producer save-order source and configuration, then emits a file-to-step hash manifest. This establishes that `trained_1NN_<step>.pt` and `checkpoint_step_<step>.pt` are the same post-fit accepted state and that `checkpoint_step_<step-1>.pt` is its immediately preceding accepted state.

The frozen control event detector is the production detector: accepted post-fit nodal damage strictly greater than `0.95` in the producer's right-boundary region `x > 0.48`, at least three nodes, first occurrence, followed by three subsequent consecutive confirmation steps. The own-event export is the first occurrence at step 424; confirmation completes at step 427. The exporter requires the locked production log to contain exactly that onset and completion with no reset, and independently rechecks accepted checkpoints 423--427 and their persisted detector metadata.

## Local checks

- Python compilation: PASS.
- `tests/test_s04_e013_stage0.py` plus existing `tests/test_teacher_precision.py`: 7 PASS.
- Real c82s4 Mac/CPU post-processing stopped at the unchanged `5e-6` model/checkpoint consistency guard (`max_abs=1.519918441772461e-05`). A read-only Taobo GPU reconstruction with the original source returned exact zero max/RMS/p99 difference. This is a cross-runtime reconstruction finding; formal export is restricted to the original CUDA producer environment and the guard was not relaxed.
- The exact step408 own-prior was transferred read-only for the diagnostic; no substitute state was used.

## Execution boundary

These runners do not authorize candidate training. The c60 runner was allowed to execute on the approved Windows/Condor producer because the first independent review found no blocker for that byte-identical file. The corrected exporter may run against the existing Taobo archive only after renewed exact-commit Code Ready review. Actual outputs must be hashed, retrieved, independently reviewed, and then reflected in `coverage.csv` before readiness states change.

## c60 producer result

`S04-E013-R001-c60-uv` ended before a scientific output because PowerShell promoted a known PyTorch stderr warning to a terminating `NativeCommandError`. The launcher-only retry `S04-E013-R002-c60-uv` used identical code, inputs, thresholds and resources and completed on D-26-09 as Condor cluster `82.0` with exit code 0.

The retrieved result passed the frozen UV gate: `rho_u` decreased from `1.2857766593003994` to `4.816938699465251e-11`; displacement mass RMS / `Us` was `6.872576107117729e-4`; native-Q4 strain relative L2 was `4.748005459472791e-3`. The solve converged in four iterations with stable active set and normalized residual `7.201357464409995e-15`. Damage, prior and fatigue were fixed, with zero training, damage solves or history commits.

This result does not qualify a full teacher. The damage diagnostic did not improve (`rho_d_common 0.0534045 -> 0.0557919`), and the output explicitly retains `full_teacher=NOT_QUALIFIED`. Independent Evidence review admitted the c60 row only as `CONDITIONAL_UV_REFERENCE_ADMITTED`. The exact receipt is under `local_archive/experiments/S04-E013/runs/S04-E013-R002-c60-uv/`.

## Paired exporter production update

The exact-commit re-review returned `Code Ready PASS` for commit `19a5c13d5dcc2d1888528621dc6ff459c59dbe3d`, with no remaining blocker to read-only production in the original CUDA environment. Formal run `S04-E013-R003-paired-export` then completed remotely on Taobo GPU 0. It produced all 13 declared files: c20/c60/c82/c83 at s2/s4/s5 plus c85s4 own-event, along with CSV/JSON manifests.

Remote verification found 13 rows, 31 arrays per row, finite numerical arrays, matching output hashes and maximum model/checkpoint damage difference `0.0`. The locked event evidence retained first occurrence step 424 and confirmation completion step 427. Training and history-commit counts are zero. All 13 payloads and both manifests were retrieved after resumable transfer; local rechecking reproduced every manifest output hash and finite-array result.

## Independent Evidence review result

The review bound to documentation commit `165afdf` and producer commit `19a5c13d5dcc2d1888528621dc6ff459c59dbe3d` returned `Evidence PASS`, with no blocking correction for reference/control admission. It registered the 12 same-cycle rows and c85s4 own-event row as `PAIRED_CONTROL_ASSETS_READY`, while keeping the own-event row distinct from a same-cycle FEM event comparison.

This is an asset-integrity and comparison-readiness status only. Candidate training, route promotion, Stage 0 scientific closure, `FULL_FEM_REPRODUCTION` and `QUALIFIED_FEM_TEACHER` remain unavailable. See [stage0_evidence_review.md](stage0_evidence_review.md).
