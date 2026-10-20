# v5 独立只读代码与准备方案审核

日期：2026-10-20。结论：**Code Ready，仅限本地准备；无剩余阻断缺陷。** 不构成执行许可或科学通过。

审核源码：`91d500c22bd4e086e4542971da6ecfb138706708`。最终owner为`fem-surrogate-comparison-prep-20261020`，接入基线为`77119a1d31bc56560fe8607c331b560ec6afc13b`。本审核只新增这份记录和同名JSON，不修改源码或已消费R2记录。

## 已核实

- `f_solve_gp`直接取最后实际求解QP的输入`q.fatigue`；`f_commit`仍取最终u/d、固定旧接受态的fresh trial。两者分开保存，并核对原fatigue residual，未放宽求解阈值。
- 接受态、字段证据和父状态同一NPZ原子提交；保留CAS、fsync/rename及替换后CommitUncertain语义。拒绝非法契约前不再先打开临时文件。
- 物理键绑定共同初态、输入清单、mesh/physics、settings/coupling、schedule/边界、载荷相位和反力顺序；训练与评分核当前card及各自父链。
- 标签特征从封存旧态及共同预测器重算，d_target仅作输出；完整顺序、字段顺序、数组摘要和模型收据均核对。旧档可读，但不自动成为新合同标签。
- 两个launcher及supervisor在实际启动前拒绝disabled/未对账卡。未来启用还须核真实相对路径对账收据SHA、R2结清和次数余量，并将同一来源计入实际prior_costs。
- 新准备包使用最新owner基线及null RunID；不复用已消费R2身份。v5完整方案、数据缺口和预算区分计划上限与未知当前剩余额度。

## 独立验证

85文件源清单与86文件准备包逐文件SHA均吻合；artifact分别为`38715de982999692ebadcb097dfb5bc3321602c1549c3fc48675f3ab2c55d9e8`、`2a7819cbd7bb0865a78d224bc447123fc7f140376033cc0a55d39068d6a002dc`。准备卡SHA为`d5af9ff99ff25b62ae9a23af4e6257ecbb35dcd1937fdb3cfa8db73c35358c52`，确为execution_enabled=false、run_id=null、budget reconciliation未完成。

独立运行最终契约人工测试：**36 passed，0.96秒**。另核原owner完整测试日志SHA和末行，确为**130 passed，3.57秒**；未重复完整套件。测试覆盖字段证据破坏、父链/物理键/反力错配、特征未来信息与目标错配、旧档升级、disabled启动、假对账SHA、未知运行、已耗fit、步数不足、未绑定费用及重用RunID。

本审核未解码真实项目科学数组，未SSH、部署、启动producer、训练或执行真实项目FEM。人工数组/故障注入结果只支持实现行为。

## 保留的边界

R2只有2026-10-20 19:06:47英国时间的本地快照；当前状态、完整费用、已耗fit/步数未知。不能重置额度、热换远端代码或追认旧输出缺失的真实f_solve。生产Matplotlib 3.10.3有旧实测记录，未来仍需检查环境漂移。

新增证据约18.54GiB/3600步已计入存储估算；原128GiB单份硬上限不变。实际IO/速度、完整新合同标签、f<1反馈、同质量整轨迹收益仍缺。旧负结果、判据与停机记录保持原解释。

**本记录的verdict刻意不是可被启动器当作执行审核使用的REVIEW_PASS。** 任何未来执行须在原owner完成真实对账及精确任务授权，不由本地Code Ready自动产生。

