# S04-E036 阶段 A · 2026-10-22（伦敦）

目的：验证共同末态、历史更新和保存读回的实现，再检查真实 MATLAB/Python 同状态数值一致性。本次继续 D2，不执行 P1/P2 训练或阶段 B。

结论：**轻量 Python 检查通过；原生部分在启动准备阶段停止，阶段 A 未完成。** 这是执行准备失败，不是 FEM 数值失败，也没有产生新的已接受场或轨迹。旧结果及两个旧源码锁保留。

## 已执行与未执行

| 项目 | 本次结果 | 证据范围 |
|---|---|---|
| controller、输入、持久化、既有接受/Q4/overlay | 110 passed，pytest 7.95秒；进程8.813秒 | 人工数组、mock、文件保护 |
| 最新冻结场比较器完整小数组检查 | 35 passed，pytest 0.60秒；进程1.868秒 | 人工 Q4、元数据、输入域、读写/篡改保护 |
| 比较器早期检查 | 原19 passed及后续targeted5 passed记录保留 | 不与最新35重复相加 |
| CITPC12源/依赖/输入盘点 | 只读核对完成；输入本地盘点完整 | 不证明MEX由对应源码构建 |
| 隔离源快照 | git archive命令失败，未复制输入/二进制 | 参数解析错误；仅创建空子目录 |
| 新MEX编译、MATLAB checkcode及28个mock | 未执行 | 源码准备/静态复核不能替代执行 |
| U0原生残差、absent/false两个c1s1 | 未执行 | 没有原生入场或disabled identity结果 |
| c1/c20/c60/c83 s4冻结场原生/Python对照 | 未执行 | 没有真实同状态数值一致性结果 |
| NN训练、阶段B、新recovery、历史重建 | 0 | 不在本次授权范围 |

两组最新Python检查均为1线程、CPU小数组，无项目优化循环或全网格装配；运行前后被测字节一致。Python3.12.2、PyTorch2.11.0、pytest7.4.4、NumPy2.2.6、SciPy1.14.1、h5py3.16.0。详细命令、JUnit、版本、SHA和标准输出保留在case，测试版本与最终准备版本分开记录。

早期targeted5的supervisor墙钟字段与pytest/UTC间隔不一致，原记录不改写；该批1.479秒不能当作可靠耗时，具体差异已在该批validation receipt说明。

## 预算与停止

用户本次批准阶段 A 总墙钟3小时、最多4 CPU线程、原生求解串行。两次disabled各1800秒/outer1500；四组冻结场各600秒。没有扩大数值阈值、线程数或预算。

- case：`local_archive/experiments/S04-E036/stage_a_20261021_2142`。
- 本次全局窗口：2026-10-21 21:42:35Z至2026-10-22 00:42:35Z。
- 启动前的`authority.json`另设零启动准备1200秒，截止22:02:35Z。后续23:28:07Z读时已越界，本次原生启动停止，不重新计时。
- 隔离命令失败：PowerShell将`--output=($dst+'\\native_source.zip')`错误传给git，git报`not a valid object name`，退出1；未启动MATLAB、编译器或任何科学求解。该命令的SSH包装实测1.903秒；墙钟读时之间的间隔不是计算耗时，不能计作CPU使用量。
- 23:31:38Z只读终检：新任务目录文件列表为空；MATLAB/Python/ifx进程列表为空。没有进程需要终止。停止记录保存在本地；一次远端写停止记录的自动审批超时后，采用允许的只读重查成功，未发送或重复启动计算。

总3小时是停止上限，不是实际科学计算消耗。原生计算、MEX编译和GPU训练消耗均为0；已运行Python各批的实测时长见receipt。未把空闲/等待时间冒称有效计算，也未把剩余窗口挪给新状态或重试。

## 已准备但尚未运行的代码

`tools/s04_e036_fem/STAGE_A_HARNESS.md`给出接口。新增context从保存E011派生U0及original initial_KK重建支持，不调用recovery；disabled双臂执行原overlay的单步原文，并分别产生1800秒截止记录。导出器使用同圈s3旧前态、s4固定场，仅做一次u和一次d装配。比较器对两种Python float64实现分别检查Ru/Rd、box投影和GP raw/P/A/f，阈值仍为`1e-10 + 1e-8*maxabs(reference)`。

构建helper在全新目录重编源依赖和两个网关，保存配置/对象/MEX来源；不修改全局mex选择或使用旧obj/mod。watchdog先记录attempt，暂停创建子进程并绑定自身Windows Job Object/CPU affinity，核验身份后再恢复；覆盖异常清理、总/局部墙钟、两个独立arm及存储上限。**PowerShell/C#接口、实际Intel构建、MATLAB与MEX兼容性均未执行验证。**

交叉静态复核修正了旧history slot1的使用边界、材料元数据浮点舍入与物理域校验、单臂外部时限、诊断I/O遮蔽主异常，以及最终保存/hash之后漏查时限。旧history保留原样；不能用slot1补写来伪造新kernel来源。

实际producer是CITPC12，源commit`862992a60edc7f59335365beacb5c71fc8592a7a`、当时clean、MATLAB R2025b，Newton实际7输出。AMOR/AT1现有二进制SHA不同于E011旧存档；当前内核显式写slot1，而旧内核未赋该输出。没有构建receipt，因此尚不能声称现有MEX执行了当前源码；此次未偷偷沿用旧二进制推进。

## 下一决定与证据路径

当前仍需实际原生同状态证据，才能决定是否进入阶段B。启动包装的修正仅保留为准备稿；未在本次已停止的准备窗口重试。未来启动须使用新鲜目录、重新核验资源/来源和明确的执行窗口，保留本次失败。先完成受限环境/构建与MATLAB检查；已有U0不合格则disabled不可用，不生成新recovery。随后仍只做原先两控制及四冻结态，不补新状态或调阈值。

权威owner：[experiment.md](experiment.md)；原方案：[FEM_VALIDATION_PLAN.md](FEM_VALIDATION_PLAN.md)；历史检查：[VALIDATION.md](VALIDATION.md)。原`source_lock.json`和准备时的`implementation_lock.json`没有改写；本次新增源码身份另列`stage_a_implementation_lock.json`，不等同于全部文件已通过测试。

本地case的`logs/python_units_01*`、`python_compare_01*`、`python_compare_02*`、`python_compare_03*`保留各批原日志。`logs/stage_snapshot.json`是失败原文；`logs/preflight_stop_readonly.json`是终检；`logs/native_bindings.json`和`remaining_bindings_02.json`保留实际路径/哈希；`analysis/`保存紧凑检查记录及停止摘要。既有前态盘点位于`local_archive/pidl_cyclic_audit_20261021/e036_stage_a_local_data_inventory_20261021/data_manifest.json`，SHA为`ab11ac06aa9241731ccd833464b60ca12d69002df2a9f4a2d1ecf64ac77f335a`。
