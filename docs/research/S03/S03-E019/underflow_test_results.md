# E019-D03-U01 A001 — 一次tiny人工测试，首失败即停

2026-10-17。按已核实总部人方tiny批准，在Pro PASS_PLAN和独立静态
PASS_STATIC_CODE后，仅执行一次确切A-U01命令。失败后没有重试、改源码、
改容差、运行其他测试或B002/C/D。本页只保存结果和源码/纸面定位。

## 结果

- execution_status=failed；6项实际运行：前5项通过，第6项失败；59项未运行。
  原24项在suite后部，本次全部未运行，不能沿用其历史通过作为新版本通过。
- failfast在`test_direction_and_counts_are_not_underflow_events`的人工计数
  断言停止：actual `(2,1,1,1)`，expected `(3,1,1,1)`。
- exit1，工具chunk `2014df`，同步完成无session；工具wall0.140288292秒，
  unittest显示0.002秒。失败不是超时；由于失败提前exit，成功路径的最终
  身份/60秒回执未运行，不虚构成功收据或完整65项结果。
- 只小数组/位型/Fraction；实际QR0/SVD0，未触及同尺寸生成、求解、
  NPZ/report、真实数组或留出；无图或新数值运行目录，冻结产物未读取/修改。
- 起始和失败后HEAD均`0649c4c61ae8f6a17650519adb3b5879324846ac`，clean；
  五源码SHA前后等于underflow_code_review.md。代码基线
  `b597d38f8d94dc2a69f89935a350859905d1e636`，后继仅docs。
- 执行前后普通Codex7天used7%/remaining93%；未开启新模型/计算重试。
  PID/运行期软件版本未在本次失败输出记录，不能借历史运行补填。

确切命令与环境见[执行包](underflow_execution_package.md)，无变更。
发起前UTC观察21:38:15、失败后只读保存时UTC21:38:43，不作为精确进程起止。

## 源码与纸面定位，不是追加计算

冻结派发定义是frexp指数和≥−1020走普通分支。失败测试第三列输入为
最小正规数2^-1022乘1：frexp分别为(1/2,−1021)和(1/2,1)，指数和−1020，
所以应走普通分支。测试误把它算入整数分支，预期3与实现记录2冲突。
该定位来自已读取源码/已冻结数学定义和本次输出，不读取数组或补跑程序。

这首先定位为测试fixture/分支预期不一致，不能据此认定候选舍入算法错误，
也不能据5项通过认定全部修复成立。启动前的模型探针没有阻止suite开始，
仅说明该组有限探针未报错，不是完整硬件认证。

同类待运行设计还有`test_min_normal_in_integer_branch`及
`test_first_normal_binade_in_integer_branch`：使用接近最小正规的数×1，
也应重新核实分支预期。当前不运行它们、不声称它们实际失败。

## 一个最小后续动作（仅方案，未实施）

只修订人工fixture与相应名称，不改候选helper、原容差、派发界、白名单或
停止规则。例如，若需确实覆盖“首正规binade内的整数分支”，采用可表示
输入(3/2)2^-1022×(3/4)，指数和−1021，精确结果(9/8)2^-1022；最小正规
数×1则明确作为普通分支测试。已有最大次正规到最小正规的可达舍入案例保留。
将此最小差异作独立只读复审，再提交一个新tiny尝试；这次失败不可重标通过。

当前没有实施上述修订或启动新的尝试。原首停/不自动重试规则仍有效，
新测试执行须取得新授权；B002、真实读取和C/D仍关闭。

## 完整原始输出

```text
test_budget_exhaustion_before_product (__main__.UnderflowUnits.test_budget_exhaustion_before_product) ... ok
test_comparison_overflow_stops (__main__.UnderflowUnits.test_comparison_overflow_stops) ... ok
test_comparison_shape_nonfinite_rejected (__main__.UnderflowUnits.test_comparison_shape_nonfinite_rejected) ... ok
test_comparison_unknown_kind_rejected (__main__.UnderflowUnits.test_comparison_unknown_kind_rejected) ... ok
test_direct_criterion_ratio_theorem_without_float_divide (__main__.UnderflowUnits.test_direct_criterion_ratio_theorem_without_float_divide) ... ok
test_direction_and_counts_are_not_underflow_events (__main__.UnderflowUnits.test_direction_and_counts_are_not_underflow_events) ... FAIL

======================================================================
FAIL: test_direction_and_counts_are_not_underflow_events (__main__.UnderflowUnits.test_direction_and_counts_are_not_underflow_events)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013/scripts/test_aa2024_underflow.py", line 262, in test_direction_and_counts_are_not_underflow_events
    self.assertEqual((r['integer_branch_count'], r['subnormal_output_count'], r['nonzero_product_rounded_zero_count'], r['zero_operand_count']), (3, 1, 1, 1))
AssertionError: Tuples differ: (2, 1, 1, 1) != (3, 1, 1, 1)

First differing element 0:
2
3

- (2, 1, 1, 1)
?  ^

+ (3, 1, 1, 1)
?  ^


----------------------------------------------------------------------
Ran 6 tests in 0.002s

FAILED (failures=1)
```
