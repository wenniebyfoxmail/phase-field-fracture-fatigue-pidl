# S04-E013 Stage 1 Taobo launch record

Record date: 2026-10-09
Reviewed code: `769396f93ae5258eb984e1585d4274f7990afb11`
Current status: `COMPLETED__FRESH_MATRIX_ATTEMPT_B`
Scientific result: `SUPERVISED_CAPACITY_FAIL_FIXED_PROCEDURE`

## Purpose and frozen scope

This execution tests only whether the fixed Stage 1 supervised procedure fits
the admitted c20s4, c60s4, c82s4 and c83s4 conditional UV targets for seeds
1, 7 and 19. It does not test unsupervised physics recovery, a free PIDL
trajectory, full FEM reproduction or FEM-teacher qualification.

All four reference files were transferred to Taobo and checked against the
frozen SHA-256 identities before launch. Four producer-side
`--validate-only` calls passed. The code checkout is detached at the reviewed
commit and clean. GPU 0 was selected explicitly.

## Matrix attempt A: launcher failure

- Root:
  `/mnt/data2/drtao/wennie/S04-E013-stage1-matrix-769396f-20261008T230420Z`
- Unit: `pf_s04e013_stage1_769396f_230420.service`
- Start/end: 2026-10-09 09:31:43--09:31:50 CST
- Disposition: `INCONCLUSIVE`

The first run stopped during the first `loss.backward()` because deterministic
CuBLAS on CUDA >=10.2 requires `CUBLAS_WORKSPACE_CONFIG` to be set before
Python/CUDA initialization. Source order places `optimizer.step()` after the
failing line. No optimizer step, checkpoint, prediction, metrics, receipt or
archive was produced.

The failed run log SHA-256 is
`847b9fe868c88ba59ffa25bde6aaa3c6836f0890870e7db042b38222b33aa678`;
the dispatcher log SHA-256 is
`9ad8ae984468521682667e3d0e12e51f0bd6ce54bfafb8cb573ec2656b71dd16`.
The failed root and log are retained unchanged.

The supplied-incident review in
<https://chatgpt.com/c/6ac816d7-8430-8329-98bb-a23484959fad> returned
`LAUNCHER-ONLY RETRY ALLOWED` and did not require a new exact-commit Code
Ready review. Its permission is restricted to preserving attempt A as
inconclusive, adding `CUBLAS_WORKSPACE_CONFIG=:4096:8` to the external
dispatcher and starting a wholly fresh matrix. The reviewer did not access the
machine or repository independently.

## Matrix attempt B: active run

- Root:
  `/mnt/data2/drtao/wennie/S04-E013-stage1-matrix2-769396f-20261009T013447Z`
- Unit: `pf_s04e013_stage1b_769396f_013447.service`
- Start: 2026-10-09 09:37:19 CST (2026-10-09 01:37:19 UTC)
- Initial MainPID: `3334694`
- Run IDs: `S04-E013-R016-stage1b-c20s4-seed1` through
  `S04-E013-R027-stage1b-c83s4-seed19`
- GPU: physical GPU 0, RTX 4090
- Runtime ceiling: 36 hours
- Dispatcher SHA-256:
  `d910e833e6d47ffa4ee9e27daf5507425ae69c42b5cf0fe8a063e130b616f63a`
- Matrix CSV SHA-256:
  `c2bf740320b49b997ad29d03322de6e32b09cfff84dbf51562ceaf02a0ee56d7`

Attempt B uses fresh run and archive roots. It preserves the code, references,
states, seeds, model, initialization, sampling, optimizer, scheduler, step
budget, thresholds and final-only policy. The only launcher repair is the
required deterministic CuBLAS environment setting.

The initial health check found the service active, the first child command
bound to c20s4 seed 1 and the exact reviewed commit, GPU utilization 95%, and
1,702 MiB attributed to the training process. The run had passed the original
failure point and logged steps 100, 200 and 300; at step 300 the sampled loss
was `3.4893344263762436e-4`. These are health observations only and cannot
select a checkpoint or establish a gate result.

Attempt B subsequently completed all twelve runs and aggregation at
2026-10-09 13:27:55 CST. Twelve runs were valid and complete, no integrity
error or missing row was reported, and zero runs passed the joint gate. See
[stage1_result.md](stage1_result.md) for the field-wise result.

## Evidence disposition

The separate supplied-evidence review returned `EVIDENCE PASS` and required no
numerical rerun. The registered result is
`SUPERVISED_CAPACITY_FAIL_FIXED_PROCEDURE`; architecture representability
remains `UNRESOLVED`. `SUPERVISED_CAPACITY_PASS`, Stage 2, route promotion,
`FULL_FEM_REPRODUCTION` and `QUALIFIED_FEM_TEACHER` remain unavailable. See
[stage1_evidence_review.md](stage1_evidence_review.md).
