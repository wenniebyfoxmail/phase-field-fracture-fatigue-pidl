# G01-R65-A001 原65项人工回归：一次通过

2026-10-18（Europe/London）。用户批准原执行包唯一命令一次；实际仅执行
一次，无重试、补跑或后续计算。结果65/65通过，无跳过、失败、错误或非预期
警告；外部exit 0。按实验门控仅为synthetic C0/C1工具兼容性，不是DIC反演验证。

## 执行与身份

- 本机：`Wennies-MacBook-Pro-14.local`，Mac轻量人工单元测试。
- 工作目录：`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013`。
- Run ID：`G01-R65-A001`；工具chunk：`c59af2`；同步完成，无运行中session，
  工具未返回PID，不推测PID。
- 执行窗口：2026-10-18 19:59:08–19:59:20 BST（对应UTC18:59:08–18:59:20，
  前后工具时钟界定，非精确启动/结束时间）。
- 运行clean HEAD：`4486d51d72ca9249af2fe2e50afe99b6cfe11674`。
- 数值代码基线：`ecb8b9a9238b035f9a87bf7d4a85deb2455b95e0`；启动前核对
  基线祖先关系和后继仅docs。审查包SHA256
  `6790392991af3de616a7322821532db167370533f6642b54a168af88cae4f073`匹配。
- 外部执行前/后均clean、同HEAD；七源码SHA逐项一致，并与最终JSON一致。
  本收据及storyline在执行后才新增，不参与已结束运行的clean状态。
- 单线程CPU环境、CUDA空、-W error/-B按原命令，原三类容差未变。
- unittest计时0.013秒；脚本stdout前取样0.4939692079788074秒；工具wall
  0.418301041秒。三个口径不同，不相加或混作精确总时长。
  stdout后的最终60秒软预算检查通过，否则不会exit 0。

确切执行命令：

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/test_aa2024_underflow.py --source-commit ecb8b9a9238b035f9a87bf7d4a85deb2455b95e0
```

## 结果与边界

| 受控检查 | 本次结果 | 可支持范围 |
|---|---|---|
| 原41人工算术＋24 stub单元 | 65/65，全部ok，无跳过 | 当前G01源码下原测试兼容 |
| 外部退出、末次身份/预算 | exit0；七源码和HEAD不变 | 本次按包完成 |
| 实际QR/SVD受控路径 | 0/0；真实入口禁止，stub不算实际分解 | 人工测试口径，不是系统调用追踪 |
| 真实/留出、producer和资源运行 | 未启动、未读取 | 不产生真实数值或物理结论 |

这是测试状态表，没有物理场或预测曲线，故不生成数值结果图。
原41+24测试和参考算术未改；G01以import模式加载，未安装CLI停止守卫。
本次不会替代已完成G01子进程测试，也没有验证完整producer或真实字体初始化。
允许NumPy/SciPy导入；Fake NPZ为内存替身，CST只构造源码网格和人工观测。
原预登记下溢/警告等负控按预期通过，不是豁免新警告。

未重跑B002、未读取local_archive/report/真实数组或留出、未启动C/D、未发文件，
未改源码或冻结产物。B002继续隔离。本次没有另行启动独立运行验收。
下一步可以另备G01保护下的新同尺寸纯合成资源包，使用新Run ID、原容差和
停止规则；需要新方案及确切命令审批，不能自动重跑或恢复旧B002。

## 完整终端原文（stdout/stderr工具合并流）

```text
test_budget_exhaustion_before_product (__main__.UnderflowUnits.test_budget_exhaustion_before_product) ... ok
test_comparison_overflow_stops (__main__.UnderflowUnits.test_comparison_overflow_stops) ... ok
test_comparison_shape_nonfinite_rejected (__main__.UnderflowUnits.test_comparison_shape_nonfinite_rejected) ... ok
test_comparison_unknown_kind_rejected (__main__.UnderflowUnits.test_comparison_unknown_kind_rejected) ... ok
test_direct_criterion_ratio_theorem_without_float_divide (__main__.UnderflowUnits.test_direct_criterion_ratio_theorem_without_float_divide) ... ok
test_direction_and_counts_are_not_underflow_events (__main__.UnderflowUnits.test_direction_and_counts_are_not_underflow_events) ... ok
test_exact_subnormal_not_flushed (__main__.UnderflowUnits.test_exact_subnormal_not_flushed) ... ok
test_failure_witness_not_max_absolute_error (__main__.UnderflowUnits.test_failure_witness_not_max_absolute_error) ... ok
test_first_normal_binade_in_integer_branch (__main__.UnderflowUnits.test_first_normal_binade_in_integer_branch) ... ok
test_fixed_column_axis_and_sites (__main__.UnderflowUnits.test_fixed_column_axis_and_sites) ... ok
test_fraction_certificate_tamper_rejected (__main__.UnderflowUnits.test_fraction_certificate_tamper_rejected) ... ok
test_fraction_oracle_rejects_wrong_rounding (__main__.UnderflowUnits.test_fraction_oracle_rejects_wrong_rounding) ... ok
test_fraction_oracle_rejects_wrong_zero_sign (__main__.UnderflowUnits.test_fraction_oracle_rejects_wrong_zero_sign) ... ok
test_half_quantum_adjacent_below_above (__main__.UnderflowUnits.test_half_quantum_adjacent_below_above) ... ok
test_half_quantum_tie_to_zero (__main__.UnderflowUnits.test_half_quantum_tie_to_zero) ... ok
test_inclusive_limit_and_adjacent_outside (__main__.UnderflowUnits.test_inclusive_limit_and_adjacent_outside) ... ok
test_input_bit_mutation_rejected (__main__.UnderflowUnits.test_input_bit_mutation_rejected) ... ok
test_largest_subnormal_exact (__main__.UnderflowUnits.test_largest_subnormal_exact) ... ok
test_min_normal_in_ordinary_branch (__main__.UnderflowUnits.test_min_normal_in_ordinary_branch) ... ok
test_model_daz_behavior_rejected_stub (__main__.UnderflowUnits.test_model_daz_behavior_rejected_stub) ... ok
test_model_supported_probes (__main__.UnderflowUnits.test_model_supported_probes) ... ok
test_model_wrong_rounding_rejected (__main__.UnderflowUnits.test_model_wrong_rounding_rejected) ... ok
test_no_ratio_and_json_safe_summary (__main__.UnderflowUnits.test_no_ratio_and_json_safe_summary) ... ok
test_nonfinite_checked_before_zero (__main__.UnderflowUnits.test_nonfinite_checked_before_zero) ... ok
test_normal_matches_original_bits (__main__.UnderflowUnits.test_normal_matches_original_bits) ... ok
test_only_ordinary_operands_multiplied (__main__.UnderflowUnits.test_only_ordinary_operands_multiplied) ... ok
test_ordinary_overflow_stops (__main__.UnderflowUnits.test_ordinary_overflow_stops) ... ok
test_original_underflow_expected_negative_control (__main__.UnderflowUnits.test_original_underflow_expected_negative_control) ... ok
test_pack_only_unreachable_upper_boundary (__main__.UnderflowUnits.test_pack_only_unreachable_upper_boundary) ... ok
test_pack_rejects_invalid_range (__main__.UnderflowUnits.test_pack_rejects_invalid_range) ... ok
test_reachable_integer_branch_upper_pair (__main__.UnderflowUnits.test_reachable_integer_branch_upper_pair) ... ok
test_reachable_subnormal_to_normal_rounding (__main__.UnderflowUnits.test_reachable_subnormal_to_normal_rounding) ... ok
test_repeat_site_rejected (__main__.UnderflowUnits.test_repeat_site_rejected) ... ok
test_signed_zero_all_signs (__main__.UnderflowUnits.test_signed_zero_all_signs) ... ok
test_subnormal_input_normal_output (__main__.UnderflowUnits.test_subnormal_input_normal_output) ... ok
test_three_half_quantum_tie_to_even (__main__.UnderflowUnits.test_three_half_quantum_tie_to_even) ... ok
test_threshold_dispatch_fraction_reference (__main__.UnderflowUnits.test_threshold_dispatch_fraction_reference) ... ok
test_unlisted_arithmetic_underflow_still_stops (__main__.UnderflowUnits.test_unlisted_arithmetic_underflow_still_stops) ... ok
test_wrong_column_shape_rejected (__main__.UnderflowUnits.test_wrong_column_shape_rejected) ... ok
test_wrong_dtype_rejected (__main__.UnderflowUnits.test_wrong_dtype_rejected) ... ok
test_wrong_site_rejected_before_multiply (__main__.UnderflowUnits.test_wrong_site_rejected_before_multiply) ... ok
test_budget_exact_stop (test_aa2024_q_recheck.Units.test_budget_exact_stop) ... ok
test_candidate_inputs_not_overwritten (test_aa2024_q_recheck.Units.test_candidate_inputs_not_overwritten) ... ok
test_clean_projection (test_aa2024_q_recheck.Units.test_clean_projection) ... ok
test_cst_affine_and_component_order (test_aa2024_q_recheck.Units.test_cst_affine_and_component_order) ... ok
test_eta_boundary_exact (test_aa2024_q_recheck.Units.test_eta_boundary_exact) ... ok
test_eta_no_tolerance (test_aa2024_q_recheck.Units.test_eta_no_tolerance) ... ok
test_eta_row_sum_not_max_element (test_aa2024_q_recheck.Units.test_eta_row_sum_not_max_element) ... ok
test_given_leak_removed_before_stub_qr (test_aa2024_q_recheck.Units.test_given_leak_removed_before_stub_qr) ... ok
test_independent_reference_full_vector (test_aa2024_q_recheck.Units.test_independent_reference_full_vector) ... ok
test_logging_warning_stops (test_aa2024_q_recheck.Units.test_logging_warning_stops) ... ok
test_no_second_qr (test_aa2024_q_recheck.Units.test_no_second_qr) ... ok
test_nonfinite_qr_stops (test_aa2024_q_recheck.Units.test_nonfinite_qr_stops) ... ok
test_one_svd_fixed_driver_stub_only (test_aa2024_q_recheck.Units.test_one_svd_fixed_driver_stub_only) ... ok
test_opaque_permission_before_any_read (test_aa2024_q_recheck.Units.test_opaque_permission_before_any_read) ... ok
test_python_warning_stops (test_aa2024_q_recheck.Units.test_python_warning_stops) ... ok
test_qr_signs_coupled (test_aa2024_q_recheck.Units.test_qr_signs_coupled) ... ok
test_reference_failure_not_ratio_scalar_equality (test_aa2024_q_recheck.Units.test_reference_failure_not_ratio_scalar_equality) ... ok
test_roi_boundary_excluded (test_aa2024_q_recheck.Units.test_roi_boundary_excluded) ... ok
test_runtime_code_change_rejected_stub (test_aa2024_q_recheck.Units.test_runtime_code_change_rejected_stub) ... ok
test_selective_npz_keys_no_other_decode (test_aa2024_q_recheck.Units.test_selective_npz_keys_no_other_decode) ... ok
test_square_unit_threshold (test_aa2024_q_recheck.Units.test_square_unit_threshold) ... ok
test_symlink_ancestor_rejected_without_IO (test_aa2024_q_recheck.Units.test_symlink_ancestor_rejected_without_IO) ... ok
test_vector_vs_matrix_units (test_aa2024_q_recheck.Units.test_vector_vs_matrix_units) ... ok
test_zero_qr_diag_stops (test_aa2024_q_recheck.Units.test_zero_qr_diag_stops) ... ok

----------------------------------------------------------------------
Ran 65 tests in 0.013s

OK
{"status": "tiny_artificial_units_completed_not_B002_or_real_acceptance", "tests": 65, "actual_svd": 0, "actual_qr": 0, "source_commit": "ecb8b9a9238b035f9a87bf7d4a85deb2455b95e0", "runtime_head": "4486d51d72ca9249af2fe2e50afe99b6cfe11674", "source_sha256": {"aa2024_q_recheck.py": "fc35d2c2a85780228468417613eb194ac95e6ca8b77d37f76f4ac1eba3bb8fcf", "aa2024_q_verify.py": "db48c03ccd5b4972663e10b31f54cbbc3562b9d78d994852f10b69190c85af09", "test_aa2024_q_recheck.py": "a5b7fc3c1e97132c45df5118d06015baff3a3caf101e66a22137d941f014cedf", "aa2024_dyadic_reference.py": "a492c822d7e06d82ff0c43306b7fdb004e2cb5b987b28bb5fd1646bcb8fd1c36", "test_aa2024_underflow.py": "faec84e6e98c2063f9010e97028eebee52a8c782684640ed0c7e0b1bc124b87f", "aa2024_runtime_guard.py": "e7bf15a9a46fa60dcc1ef41cbd3f86c2d41fb44bcda6de1ba9300df8cd76874c", "test_aa2024_runtime_guard.py": "2eb8663fea0a31a9bf88802dc9ac9bdd609934f8ab415a557a8ed6b6d6922e54"}, "elapsed_before_print": 0.4939692079788074}
```
