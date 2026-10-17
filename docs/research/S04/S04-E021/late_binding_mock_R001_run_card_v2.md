# S04-E021-LATE-BINDING-MOCK-R001：针对性人工mock单次运行卡 v2

2026-10-17 Europe/London。**仅修复和静态复审准备，未执行；执行仍待独立复审及用户单次批准。**
替代5bc9160的v1启动配置；v1作为历史快照保留，不再用于启动。原用例、容差、预算和数据限制不变。

## 身份、问题与范围

- S04／S04-E021，C0人工工程检查；只核对显式绑定、RMSE百分数换算、类型拒绝、容差和关闭路径。
  不改变科学结论，不验证真实数值或REAL完整集成。
- 源码：`e7bce635fcdcbdd70abb06140b50f3bdd1064c16`；修复前基线de5d447。
  仅在新guard／worker增加优化模式拒绝、固定子进程环境及回执中的模式字段。
  adapter、旧checks、纯核心、共享预算监督器、9984226方案均未改；REAL_ACQUISITION_ENABLED仍False。
- 分支：`codex/s04-late-regression-plan-20261016`。工作目录：
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-late-regression-plan-20261016`。
- 唯一待批尝试：`S04-E021-LATE-BINDING-MOCK-R001`，此前未执行或消耗；本修复不另开尝试。
- 固定新输出：
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/engineering/late-binding-mock-20261017-R001`。
- 主对话`01a1131d-017c-7b03-a95a-ad73ba8fcc9c`唯一执行／记录；方法对话只读审核、不写共享文件或启动作业。

## 唯一修复与非优化配置

guard和worker均在文档串后先导入sys，用**if／raise而非assert**检查`sys.flags.optimize != 0`；
不满足即拒绝，早于各自依赖导入、参数解析和mock文件操作。`-O`、`-OO`或优化环境不能绕过此检查。
命令固定`PYTHONOPTIMIZE=0`，不加`-O`／`-OO`；guard在调用原监督器前也设置环境值为0，
由原监督器的环境复制传给worker。环境覆盖不声称能撤销一个已经优化启动的解释器，因此两端均检查。
worker成功记录须含`python_optimize=0`、`python_debug=true`；原assert用例保持不变。
若优化启动被拒绝，可能尚未创建输出／回执；不能以缺回执或命令结束冒充完成。

## 冻结人工清单与边界

| 组 | 必须保留的人工用例／判据 |
|---|---|
| selector／单位 | 五项显式selector；0→1、−25→0.75、25→1.25，共3例，身份／counts一致 |
| 类型／缺字段 | Run数字、commit空值、rows布尔、count浮点、百分数布尔／字符串及缺rows，共7例，精确错误拒绝 |
| 非有限 | NaN、−Inf、+Inf共3例，精确nonfinite错误；仅输出标签，不序列化非有限数 |
| 比较路径 | 8探针：reference=0时tau下一浮点／等号／上一浮点3例；Git常量中心上下各inside／outside4例；25%换算桥接1例 |
| 显式关闭 | 人工valid-shape REAL grant的snapshot在metadata/read前、acquire_real在reader构造前拒绝，2入口始终关闭 |

比较仍为原`abs(ratio−expected_ratio) <= 1e-12`；Git常量中心两侧检查相邻可表示数及跨阈值，
不把center+tau的舍入差称为精确tau。原v1第2节的构造和禁止扩大结论完整保留。
ScalarProbe仅提供内存inventory／verification与虚构metadata，无CSV内容；达到summary读取边界即抛指定哨兵。
接受／拒绝和完整调用顺序须匹配；哨兵不是完整snapshot成功，其他异常不得记通过。
只复用旧protect／rejected辅助定义，不调用旧run或旧资源／绘图／fd核验。
所有输入为人工夹具或Git常量；不得打开真实JSON、CSV、数组、轨迹、模型或确认数据。

## 启动前条件与唯一命令（本轮不执行）

须先有绑定此源码／v2卡的独立静态复审认可，再取得用户对本次单次执行的明确批准。
本轮仅AST语法解析／diff检查，不执行mock、优化模式负例、资源核验或项目模块导入。
获批后才核对实际hostname、同名guard／worker不存在、新输出未占用、源码tracked且clean及计划未变；
准备阶段不扫描科学archive、不创建输出或授权。目录存在则拒绝，不删除／覆盖或改名重试。

只限本Mac CPU、无GPU／SSH、数值线程1。工作目录如上；未来唯一命令：

```bash
PYTHONOPTIMIZE=0 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 SENS_tensile/s04_late_binding_guard.py --expected-commit e7bce635fcdcbdd70abb06140b50f3bdd1064c16 --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/engineering/late-binding-mock-20261017-R001
```

六受控源码为SENS_tensile下的s04_late_attribution.py、s04_late_attribution_guard.py、s04_late_adapter.py、
s04_late_adapter_checks.py、s04_late_binding_guard.py、s04_late_binding_checks.py，须与上述源码提交等价。
文档提交可晚于源码，不夹带源码变更。guard传父PID／40位代码env，worker检查固定输出、父PID和代码；
这些调用联锁不代替用户许可。

## 预算、停止与输出

单次**60秒／512MiB聚合采样RSS／5MiB新增输出**，含日志、checks和receipt。原guard未改：
工作58秒、20ms采样、16KiB回执余量；计时从execute开始，不含解释器／import启动，回执落盘有post检查。
不是OS硬峰值或采样间保证。任何异常、身份不符、触限、部分或未知退出均停止且不重试；
不resume、扩预算、换身份／机器或补跑。仅清理本guard创建的进程组，不碰其他用户进程。
保留primary_reason／terminal_caps和实际退出证据；缺回执须报告，信号成功不代表进程已退出。

预期只生成checks.json、engineering.log、guard_receipt.json三文件，不生成CSV、图、缓存、场或授权文件。
须核对上述5组／3换算／7类型／3非有限／8探针及模式字段，并保留real_data_read=false、
fitting_invoked=false、real_acquisition_enabled=false、csv_contents_read=false、full_snapshot_completed=false、
old_suite_run=false。GENERATED_CHECKS_COMPLETED／COMPLETED仅指本工程清单完成，不减少预定清单。
未来核对三文件、总字节、身份和进程退出后只读冻结新目录，不新增常规hash，旧尝试全部保留。

当前未运行、未获本修订静态结论；修复不等于Code Ready或资源验证通过。非数值C0以上表说明决策，不新增图。
下一步只静态复审；认可后申请单次人工mock执行。真实入口、U0.1175／U0.125确认数据仍关闭，
E017／NN／多目标训练暂缓；Obsidian由主对话统一更新，不双写或重复计算。
