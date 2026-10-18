# E019-D03-U01 A002 — 修订后tiny一次通过

2026-10-18（Europe/London）。用户本对话明确批准修订后的确切命令执行一次；
不沿用A001许可、不重写A001失败。仅执行A002，无自动续跑、重试或源码修改。

## 结果与有限结论

- execution_status=succeeded；65/65通过（41项新增人工边界+24项原stub回归），
  exit0，无非预期警告/异常，未跳过或补跑。
- 修正后的三个派发用例、独立Fraction舍入区间/证书、符号零/次正规/正规
  边界、普通分支逐位、原三容差全分量/失败见证及首停守卫均在本次通过。
- 本次只支持已检人工输入和声明binary64模型下的诊断算术实现；不是
  实际全尺寸证书、真实DIC数值复核、B001根因、材料/相场反演或预测证据。
- 实际受控SVD0/QR0，其他分解/求解与np.load/真实读取/同尺寸生成守卫启用；
  原24项QR/SVD为stub，假NPZ容器不打开文件。计数是受控API/守卫及脚本
  报告，不包装成全进程追踪。无真实数组、留出或local_archive读取，无图。

| 检查层 | 本次结果 | 不支持的外推 |
|---|---|---|
| 人工算术与独立参考 | 41项通过 | 未检输入的无条件正确性、B001具体乘积无害 |
| 原小数组/stub回归 | 24项通过 | 实际QR/SVD或原尺寸60秒可行性 |
| 资源/身份/读取保护 | 最终检查通过，无额外计算或数据访问 | 真实D03、物理反演或后续执行许可 |

## 确切执行与身份

- chunk `97939d`，同步完成，无继续轮询的session；只一次exec。
- 工作目录：`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013`。
- 代码基线`ab6f123a0174c7009b5427c0db0b98901ca1e2d3`；起止HEAD
  `c024bfac309f460a700467d349c2853ab4b525b0`，clean，后继仅docs。
- 五源码SHA在运行JSON和外部前后核对一致；详见下方原始JSON及
  underflow_fixture_execution_package.md。A001结果Markdown前后SHA仍为
  `249318483373afd747184c687a1b359a8b1449562eb720dba0b586da6cb29cf0`。
- 单线程CPU，CUDA_VISIBLE_DEVICES空，六类线程环境均1，-W error/-B；
  原容差/派发/五site/异常首停未改。未发送文件或启动B002/C/D。
- 启动前后普通Codex7天used16%/remaining84%，未低于80%停止线。
- 命令未输出PID/hostname/运行期软件版本，本次不从旧运行补填。
  运行环境由既定本地Python绝对路径与上述源码绑定，非新的软件版本核验。

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/test_aa2024_underflow.py --source-commit ab6f123a0174c7009b5427c0db0b98901ca1e2d3
```

## 时间口径

- unittest测试段：0.013秒。
- 脚本`elapsed_before_print=0.4453895419719629`秒，是结果打印前取样，
  不宣称包含完整stdout的精确终点；打印后末次60秒检查通过，否则不应exit0。
- 工具另报`wall_time_seconds=0.369903083`，原样记录，不与脚本计时互相
  替代或拼成“精确总耗时”。两独立报告口径不同，不能解释为同一测量。
- 发起前UTC观察08:58:03、运行后身份保存时UTC08:58:28，均不是
  精确进程起止。整包60秒软完成检查通过，不声称硬杀进程超时保证。

## 下一步与记录边界

A001失败、B001失败及所有冻结产物保持原样。这次已解除“tiny人工实现
尚未通过”的阻断；未证明同尺寸证书生成、序列化/哈希/绘图的预算可行。
下一项最小检验是另获批准的新B002同尺寸人工资源检查，当前不启动；
真实数组/留出及C/D继续关闭。没有因65项通过而新增科研判据或自动放行。
纯单元的最小资产是下方完整终端结果与上表，不生成无意义空间结果图。

## 完整原始终端输出

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
{"status": "tiny_artificial_units_completed_not_B002_or_real_acceptance", "tests": 65, "actual_svd": 0, "actual_qr": 0, "source_commit": "ab6f123a0174c7009b5427c0db0b98901ca1e2d3", "runtime_head": "c024bfac309f460a700467d349c2853ab4b525b0", "source_sha256": {"aa2024_q_recheck.py": "0a7ebbd60d778b8e0cf2171891b68ab928ff73e0092c244f7958174ac9d49acd", "aa2024_q_verify.py": "90755956092e16cb84c0ebedd9907c21a79ea523d1819dc8fb657ec10ae7d873", "test_aa2024_q_recheck.py": "a5b7fc3c1e97132c45df5118d06015baff3a3caf101e66a22137d941f014cedf", "aa2024_dyadic_reference.py": "a492c822d7e06d82ff0c43306b7fdb004e2cb5b987b28bb5fd1646bcb8fd1c36", "test_aa2024_underflow.py": "faec84e6e98c2063f9010e97028eebee52a8c782684640ed0c7e0b1bc124b87f"}, "elapsed_before_print": 0.4453895419719629}
```
