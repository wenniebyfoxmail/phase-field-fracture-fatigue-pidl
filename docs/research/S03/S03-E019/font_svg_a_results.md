# F01-A001 — 40项纯人工内存测试一次通过

2026-10-18（Europe/London）。获批后仅执行确切命令A一次；40/40全部通过，
无skip/error/failure或非预期警告，外部exit0，无重试。D2人工接口能力通过，
不代表B003文件已读取、图器真实输入路径已跑通、视觉或数值验收通过。

## 本次身份与执行记录

- Run ID：F01-A001，复用F01任务；无输出/缓存/临时图目录。
- 主机：`Wennies-MacBook-Pro-14.local`；本地单线程CPU、CUDA空。
- 工作目录：`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013`。
- 数值/显示代码基线：`6514160302be3f654d96bf19ba8d2d747c6bfd26`。
- 运行前后clean HEAD：`8920759fd8716c648b488356758161bd78874435`。
  基线祖先/后继仅docs、三源码SHA及执行包SHA与已审材料匹配；外部执行后
  HEAD和三SHA再次一致。下面完整JSON含三SHA，不改写已审材料。
- 执行包SHA：`ae59387fae5deaa636b728fb3c363ff9cb8832e75eb215b5b863ad3919209b04`。
- 工具chunk：`c0f38f`，同步返回exit0，无运行中session；工具未提供PID。
- 时钟观察窗口UTC21:12:14–21:12:26，即BST22:12:14–22:12:26；仅为围绕
  命令和后查的时间窗口，不冒称精确进程起止。
- unittest 0.012秒；脚本stdout前取样0.16507720801746473秒；工具wall
  0.090743417秒。口径/时钟不同，不混为精确整包时长。stdout后的最终预算
  检查已通过，否则不会exit0；原60秒软预算、零实际分解及原容差未变。

确切命令，仅执行一次：

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/test_aa2024_saved_svg.py --source-commit 6514160302be3f654d96bf19ba8d2d747c6bfd26
```

## 结果边界

| 检查 | 本次结果 | 不能推出 |
|---|---|---|
| 人工数组／保存标量／JSON接口 | 命名正控及异常负控通过 | B003实际文件或历史生成有效 |
| 内存XML／共享色标／坐标／转义 | 所有点、面板、保存值与显示规则测试通过 | 浏览器字体、布局或图形独立验收 |
| 读入／分解禁止保护 | np.load禁止真实读取，Fake NPZ只消费六成员；实际QR/SVD为0 | 全进程系统调用追踪或真实数值证书 |
| 命令完整性 | 40项无跳过、exit0、末次身份/预算通过 | 命令B或独立验收已获许可 |

测试只产生内存SVG/XML字符串，无SVG文件、图像或缓存；因此不创建结果图。
G01与导入禁止/数值入口保护保持，未导入Matplotlib/SciPy或旧producer/verifier，
未初始化/预热字体，不豁免日志。预登记的下溢等assertRaises是原测试负控，
不是忽略新异常。受控计数字段不能当全进程审计。
读取仅源码/Git/标准依赖和人工内存；未读B003数值或哈希、真实数组/stage15/
新留出，未改变源码或冻结产物，未重跑B003/B002或旧26/65包。
未启动B、独立数值/图形验收或C/D，未发送文件。

下一步可另备B的最终显示执行包，核对A后代码版本与新目录条件；实际读取
B003合成文件、当前hash和派生SVG运行仍须用户单独批准。B003继续未完成，
其局部值即使以后能显示，也不能被补认证为数值/物理反演结果。

## 完整终端（工具合并stdout/stderr）

```text
test_authority_explicit_and_exact (__main__.Units.test_authority_explicit_and_exact) ... ok
test_authority_wrong_input_before_io (__main__.Units.test_authority_wrong_input_before_io) ... ok
test_colour_endpoints (__main__.Units.test_colour_endpoints) ... ok
test_colour_outside (__main__.Units.test_colour_outside) ... ok
test_colour_zero (__main__.Units.test_colour_zero) ... ok
test_default_shape_is_648_not_test_fixture (__main__.Units.test_default_shape_is_648_not_test_fixture) ... ok
test_degenerate_coordinates (__main__.Units.test_degenerate_coordinates) ... ok
test_display_division_underflow_still_stops (__main__.Units.test_display_division_underflow_still_stops) ... ok
test_display_stack_overflow (__main__.Units.test_display_stack_overflow) ... ok
test_exact_budget_stop (__main__.Units.test_exact_budget_stop) ... ok
test_exact_keys (__main__.Units.test_exact_keys) ... ok
test_factor_entry_is_forbidden_not_actual_factor (__main__.Units.test_factor_entry_is_forbidden_not_actual_factor) ... ok
test_fake_npz_only_selected_members (__main__.Units.test_fake_npz_only_selected_members) ... ok
test_import_fence (__main__.Units.test_import_fence) ... ok
test_inputs_unchanged (__main__.Units.test_inputs_unchanged) ... ok
test_json_duplicate_rejected (__main__.Units.test_json_duplicate_rejected) ... ok
test_json_nan_rejected (__main__.Units.test_json_nan_rejected) ... ok
test_ledger_uses_saved_not_recomputed_values (__main__.Units.test_ledger_uses_saved_not_recomputed_values) ... ok
test_negative_scale (__main__.Units.test_negative_scale) ... ok
test_nonfinite_array (__main__.Units.test_nonfinite_array) ... ok
test_path_relative_and_symlink_rejected (__main__.Units.test_path_relative_and_symlink_rejected) ... ok
test_prepare_display_only (__main__.Units.test_prepare_display_only) ... ok
test_saved_bool_not_number (__main__.Units.test_saved_bool_not_number) ... ok
test_saved_common_floor (__main__.Units.test_saved_common_floor) ... ok
test_saved_negative_scalar (__main__.Units.test_saved_negative_scalar) ... ok
test_saved_nonfinite_scalar (__main__.Units.test_saved_nonfinite_scalar) ... ok
test_saved_row_count (__main__.Units.test_saved_row_count) ... ok
test_saved_row_order (__main__.Units.test_saved_row_order) ... ok
test_saved_schema (__main__.Units.test_saved_schema) ... ok
test_sidecar_scope (__main__.Units.test_sidecar_scope) ... ok
test_source_has_no_forbidden_imports_or_factor_calls (__main__.Units.test_source_has_no_forbidden_imports_or_factor_calls) ... ok
test_svg_all_points_and_panels (__main__.Units.test_svg_all_points_and_panels) ... ok
test_svg_equal_aspect_positive_y (__main__.Units.test_svg_equal_aspect_positive_y) ... ok
test_svg_shared_colour_not_per_panel (__main__.Units.test_svg_shared_colour_not_per_panel) ... ok
test_svg_zero_map_floor_only (__main__.Units.test_svg_zero_map_floor_only) ... ok
test_wrong_dtype (__main__.Units.test_wrong_dtype) ... ok
test_wrong_shape (__main__.Units.test_wrong_shape) ... ok
test_xml_escapes_external_text (__main__.Units.test_xml_escapes_external_text) ... ok
test_zero_ledger_range_only (__main__.Units.test_zero_ledger_range_only) ... ok
test_zero_scale (__main__.Units.test_zero_scale) ... ok

----------------------------------------------------------------------
Ran 40 tests in 0.012s

OK
{"status": "F01_artificial_units_only_not_B003_display_or_acceptance", "tests": 40, "actual_svd": 0, "actual_qr": 0, "runtime_head": "8920759fd8716c648b488356758161bd78874435", "source_commit": "6514160302be3f654d96bf19ba8d2d747c6bfd26", "source_sha256": {"aa2024_saved_svg.py": "625e312c760a9f1685fe9afd4aaeea0cadcf772556eab87999a27e5bec4bdf99", "test_aa2024_saved_svg.py": "6b7a3f4a5fc9588f39f9e034571ee5ec30a12a620d0cb133aa757bf91aaa1d7b", "aa2024_runtime_guard.py": "e7bf15a9a46fa60dcc1ef41cbd3f86c2d41fb44bcda6de1ba9300df8cd76874c"}, "elapsed_before_print": 0.16507720801746473}
```
