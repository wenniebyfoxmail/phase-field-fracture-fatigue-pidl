# S04-E036 Stage A 完成与交接 · 2026-10-22

目的：完成已声明的 FEM 软件一致性基准，提供整体对照 owner 可直接复用的结果。

结论：**Stage A 固定基准全部通过**，最后计算于 07:54:59 UTC 完成。全局 PowerShell 策略未改；本窗口没有训练、阶段 B 或新 recovery。旧 [初次停止结果](STAGE_A_RESULT_20261022.md) 保留原样。

## 实际结果

- disabled c1s1：同一 E011 U0 的 option absent 与 enabled=false 两臂，13项完整状态精确相等，保存检查点逐字段读回一致；两个 native solve、两个 predictor solve、零 recovery。
- c1/c20/c60/c83 s4各自绑定s3前态：原生FEM、NumPy、能量梯度三方比较，每状态27项跨实现通道及2项history identity，**116/116通过**。
- prepare05已完成15项hash fixture、28项事务/mock检查、两份全新MEX构建；未受影响的结果直接复用。保留cleanup warning；后续本地cleanup修复未执行，不算已验证字节。

| 保存状态 | Native对两实现的最差误差/容差 | NumPy对能量梯度最差误差/容差 | 结果 |
|---|---:|---:|---|
| c1s4 | 0.00030038151 | 1.8442492e-06 | 29/29 |
| c20s4 | 0.00033696128 | 2.1171671e-06 | 29/29 |
| c60s4 | 0.00045720438 | 2.8461433e-06 | 29/29 |
| c83s4 | 0.00047722292 | 4.0927172e-06 | 29/29 |

固定标准为 `max_abs_difference <= 1e-10 + 1e-8*max_abs_reference`。最差比值0.00047722292；这不是物理场误差比例。Q4/GP顺序、材料、BC、前态、阈值均未见结果后修改。

## 启动与日志修复

1. 进程级 Bypass、受控 Job Object、真实 handle/PID身份核验，保存 stdout/stderr、MATLAB日志与supervisor终态；四个全局策略scope前后一致。
2. FileChannel哈希修复MATLAB EOF误判；统一manifest键序解决MATLAB files解码为cell。
3. 原始INP与U0完整精度相等；native importer四位舍入导致disabled05入口失败。新overlay03恢复原E011精度处理；严格mesh/DOF比较、U0、native/code04/build05均保留。
4. PowerShell5.1将 `@(...|ConvertFrom-Json)` 的argv嵌成一项；comparison watchdog v5移除外层包裹。compare_c1_06未启动Python；新compare07全部完成。

prepare01–04、disabled05、compare_c1_06等历史失败和原字节均保留；已暂存未运行的 frozen05/compare06 不算结果。过程见 [执行记录](STAGE_A_EXECUTION_20261022.md)。

## 复用文件与实际消耗

- [完整汇总和逐文件SHA](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E036/stage_a_20261021_2142/analysis/stage_a_completed_20261022.json)，SHA256 `fdb9ca05fa8a4b2abb6fdb7652efc9af7618877576415450a5437cff2e871ec1`。
- [逐通道CSV](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E036/stage_a_20261021_2142/analysis/stage_a_channel_comparisons.csv)。
- [误差/容差图](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E036/stage_a_20261021_2142/figures/stage_a_equivalence_20261022.png) / [PDF](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E036/stage_a_20261021_2142/figures/stage_a_equivalence_20261022.pdf)，同名md给出来源和解释。
- 原始结果：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E036/stage_a_20261021_2142/raw_archive/continuation_03/native_06/`。185份成功任务文件共337439194 B均与远端SHA相符；另外保存构建与失败日志。

9个成功原生/比较任务watchdog墙钟合计224.9563秒，prepare05另35.0318秒；不含历史失败、准备、排查或传输，不能当作完整工程耗时或PIDL加速。计算单线程、affinity最多4 CPU、同一producer串行。人方已取消累计预算，单任务防挂仍保留。

## 交接与结论边界

整体对照owner `01a15fd3-ed7b-7122-9ef4-eb5846c4a6c8` 直接复用本批结果，按既有分工承接Stage B、P1/P2和优化/表达归因，不重复A。本窗口不重复启动B/训练。

这证明冻结同状态离散一致性与disabled兼容性；存档终态不自动成为合格FEM F1参考。Stage B仍需原计划fresh共同最终接受，再判断PIDL–FEM场差距及优化/表达原因。不能写成已改善PIDL、网络容量充足或物理预测有效。固定基准通过后交付，不追加全回归、历史重跑、smoke或独立复审。
