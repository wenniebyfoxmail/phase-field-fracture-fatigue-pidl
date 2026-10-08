# S04-E013 Stage 0 implementation

Status: implementation prepared; producer execution awaits exact-commit Code Ready review.

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

The frozen control event detector is the production detector: accepted post-fit nodal damage strictly greater than `0.95` on the right boundary, at least three nodes, first occurrence, with three confirmation cycles. The own-event export is the first occurrence at step 424; confirmation remains context and does not replace it.

## Local checks

- Python compilation: PASS.
- `tests/test_s04_e013_stage0.py` plus existing `tests/test_teacher_precision.py`: 5 PASS.
- Real c82s4 Q4 post-processing smoke: pending transfer of the exact step408 own-prior checkpoint; the first attempt stopped on that missing prior rather than substituting another state.

## Execution boundary

These runners do not authorize candidate training. After Code Ready review, c60 runs on the approved Windows/Condor producer and the exporter runs against the existing Taobo archive. Actual outputs must be hashed, retrieved, independently reviewed, and then reflected in `coverage.csv` before readiness states change.
