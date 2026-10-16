# E019-D01-V01-T001 — 获批仅命令A一次的人工测试结果

2026-10-16。用户明确仅批准确切A一次，不启动B/出图/读取report、真实数组
或留出，不改冻结产物，首个非预期失败即停、不自动重试。

## 执行与结果

- 审批正文subspace_display_execution_approval.md字节未变；SHA256：
  8a9fd4ea099a88726ea6122faeba341bd6bb0e981bc6303f7746a2256d79fcff。
- 原样执行A段一次，/bin/bash、exit0，无重试；B及其预检均未运行。
- 代码/测试/设计快照fe190c9260d3a97421606ba96dcfb4df151a7680。
- 实际HEAD5c873aec26f3f9a06ade8a7e3f4ebc2b372b3883；运行前后工作区clean。
- unittest记录11 tests in0.001s，OK；日志无warning/error。
- 收据elapsed_seconds=0.20026437501655892秒/60秒，是写收据前取样值；
  写后读回及最终60秒检查完成、exit0，不称最后一步后的精确总耗时。
- 五线程OMP/OPENBLAS/MKL/VECLIB/NUMEXPR均1，CUDA为空；Python -I -B -Werror，
  unittest failfast，无pytest/conftest/plugin自动运行。
- 四个固定来源的before/after SHA一致，符合fe190c9快照。

测试覆盖人工schema/ratio与原状态直接复制、非法类型/非有限/范围拒绝、
C0不适用与C1精确零、evidence访问哨兵、矩形边界/重叠/完整marker画布范围、
人工文件哈希/拒软链/独占写及图说明。no_plot_stack测试确认Matplotlib、
NumPy、SciPy及原producer未被导入；只使用玩具标量和矩形，无诊断重算或SVD。

## 保存记录

目录：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/code_checks/S03-E019-D01-V01-T001/`。

- tests.log SHA256：a6c715bfc7918fc0e9f27206ce2fe4b268f09345555fd6696d9b9de55b01fb91。
- test_receipt.json SHA256：440148fd0cf5e1d48520edfe188aa68727436cc91ab42ddbe4886326fd19f355。
- receipt status=passed；operation=artificial_view_unit_tests_only；wrapper PID7869。
- receipt UTC起止：2026-10-16T21:35:01.104013+00:00至21:35:01.244395+00:00。
  start_utc写于部分初始化之后，不能用该区间替代elapsed预算记录。

日志SHA与receipt记录相同，receipt可读，来源身份前后不变。
仅对新测试记录做读取/字节核对，没有继续B的预检。

## 结论与下一步边界

人工单元测试通过；不是Matplotlib导入/实际布局/PNG/PDF验收，也不是D01
数值账本或真实E019根因验收。没有新图、report读取、真实数组/留出访问、
原产物写入、源码修改、外发、SSH或push。检查时V01目录仍不存在。

原显示/数值暂停记录保留。下一步可单独审批同一执行包的B一次report渲染，
然后做独立只读显示验收；本轮不启动B、不更改命令或自动串联。
