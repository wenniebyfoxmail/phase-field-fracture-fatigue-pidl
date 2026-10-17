# E019-D03-A001 — 命令A一次人工单元结果

2026-10-17；用户明确批准仅运行执行包命令A一次。记录时间21:04:28 UTC
（不是另行测量的进程开始时间）。运行于Mac本地；没有启动B/C/D或另派验收。

## 执行身份与结果

- 代码基线 `a3352a6954543f965d559a1f1a6452cf9e58b2fb`。
- 实际HEAD `7fb49598c7f25269739846f1987f2b15f4602bde`，执行前后均干净；
  基线之后仅docs变动。脚本末次代码/HEAD/clean检查通过后退出。
- 工具执行chunk `40a3dd`，退出码0；一次执行，没有失败、修正或重试。
- 24/24通过，unittest报告0.005s；工具报告命令wall 0.144729417s。
  两者不是同一个计时器。脚本最终60秒预算检查通过，没有超预算。
- 环境按确切命令：CUDA空、六项线程变量均1，`-W error -B`、不写pycache。
- QR/SVD只用人工stub；实际分解接口由禁止守卫替代，零实际QR/SVD。
  这是受控测试路径内的检查，不是独立的整进程历史审计。
- 未读取report、NPZ数值产物、真实数组、stage15响应或新留出；selective
  loader单元用假容器，不打开NPZ。源码/规则/版本及哈希的读取不属数值读取。
- 源码与冻结产物未改，未出图、未求解、未训练或调参；没有对外发送。
- 命令未单独输出PID/进程起始UTC，不能事后补造；进程已正常结束。

## 已批准并原样执行的命令

工作目录：`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013`。

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/test_aa2024_q_recheck.py --source-commit a3352a6954543f965d559a1f1a6452cf9e58b2fb
```

## 24项输出（每项均ok）

```text
test_budget_exact_stop
test_candidate_inputs_not_overwritten
test_clean_projection
test_cst_affine_and_component_order
test_eta_boundary_exact
test_eta_no_tolerance
test_eta_row_sum_not_max_element
test_given_leak_removed_before_stub_qr
test_independent_reference_full_vector
test_logging_warning_stops
test_no_second_qr
test_nonfinite_qr_stops
test_one_svd_fixed_driver_stub_only
test_opaque_permission_before_any_read
test_python_warning_stops
test_qr_signs_coupled
test_reference_failure_not_ratio_scalar_equality
test_roi_boundary_excluded
test_runtime_code_change_rejected_stub
test_selective_npz_keys_no_other_decode
test_square_unit_threshold
test_symlink_ancestor_rejected_without_IO
test_vector_vs_matrix_units
test_zero_qr_diag_stops

Ran 24 tests in 0.005s
OK
Command A: 24 artificial units; zero actual QR/SVD, no report/real-array reads; not production acceptance; source=a3352a6954543f965d559a1f1a6452cf9e58b2fb
```

## 执行前后源码SHA256

| 文件 | 未改变的SHA256 |
|---|---|
| aa2024_q_recheck.py | 06fd574663eb7d7b740b26f77f9dd50d479f992bc707808cb30ccb52fa4765b0 |
| aa2024_q_verify.py | d378b5cbc8d446c624d14917fd3b3bfa75ca6f29be67726590d794b4c01d26a0 |
| test_aa2024_q_recheck.py | a5b7fc3c1e97132c45df5118d06015baff3a3caf101e66a22137d941f014cedf |

## 有限结论与下一步

仅支持这24项人工单元及停止/读取保护分支按受审实现通过；不能证明真实
QR/SVD、1296×1482全流程60秒预算、真实资产就绪、真实Q证书、反演或预测。
没有生成场图或数值报告，本轮图形验收不适用。
下一项候选是执行包B同尺寸人工资源检查，须另获确切命令批准；本轮停止，
不自动运行B，不提前读取任何真实输入或留出。
