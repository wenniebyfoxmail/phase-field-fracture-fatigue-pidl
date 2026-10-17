# S04-E021-LATE-BINDING-MOCK-R001：针对性人工mock单次运行卡 v1

2026-10-17 Europe/London。状态：**仅准备，未执行；新runner尚未独立静态复审，执行待用户批准**。
本轮批准范围仅是编写人工mock、补数值边界、准备新身份／新目录运行卡和更新Obsidian。
不创建Run输出、授权文件或真实数据副本，不把本卡当成执行许可。

## 1. 唯一问题与身份

仅回答C0工程问题：9824e7f的显式绑定／RMSE百分数换算／类型拒绝及关闭联锁，连同零／负值、
非有限数和原1e-12比较边界，是否按声明的人工用例工作？不改变任何科学判据或结果。

- Storyline／Experiment：S04／S04-E021；唯一执行、核对和记录方为本主对话
  `01a1131d-017c-7b03-a95a-ad73ba8fcc9c`。方法对话只读，不发第二计算／写入任务。
- 新尝试 `S04-E021-LATE-BINDING-MOCK-R001`，不是旧ADAPTER-MOCK-R001／R002或LATE-ENG-R002。
- 源码 `e2a5a94c9e47da015f1db7953a55365e3c1aba64`，基于干净dc43d3f2964f542980a5e67219a75b3fe2126c38。
- 专用分支codex/s04-late-regression-plan-20261016；工作目录：
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-late-regression-plan-20261016`。
- 固定新输出：
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/engineering/late-binding-mock-20261017-R001`。

仅新增`s04_late_binding_checks.py`和`s04_late_binding_guard.py`，原adapter、原checks、纯核心、
预算监督器、9984226方案与9824e7f完全相同。REAL_ACQUISITION_ENABLED始终False，测试也不临时开启。
9824e7f静态认可只覆盖已有组件，**不自动覆盖本次新runner／guard／哨兵检查方法**。

## 2. 准确的覆盖与禁止扩大结论

| 预定检查组 | 预先声明的人工用例与预期 |
|---|---|
| 1. selector／单位 | 五项显式selector必须完全相同；0→1、−25→0.75、25→1.25；输出身份／counts保持人工输入 |
| 2. 类型／缺字段 | Run数字、commit空值、rows布尔、count浮点、百分数布尔／字符串6例及缺rows共7例，须以对应错误原因拒绝 |
| 3. 非有限数 | NaN、−Inf、+Inf共3例，须以nonfinite saved RMSE increase percent拒绝；输出只存用例名，不序列化非有限数 |
| 4. 实际比较路径 | 8探针：tau下一浮点／相等／上一浮点3例，冻结参考常量上下两侧各inside／outside共4例，以及25%换算结果到比较器的1例 |
| 5. 显式关闭 | valid-shape人工REAL grant调用snapshot须在metadata/read前拒绝；acquire_real须在native reader构造前拒绝，共2入口，开关始终False |

所有数字来自手工夹具或Git常量，不取自真实JSON／CSV。零／负百分数检验换算，不代表真实运行
观测到这些值，也不新增允许真实RMSE为负的规则。原单位是RMSE百分比，不平方／开方。

### 容差边界为何这样构造

比较仍调用原`snapshot()`内的`abs(ratio−expected_ratio) <= 1e-12`，不复制一个替代判据来冒充验证。
以人工reference=0构造精确等号及math.nextafter两邻点，避免中心加法舍入遮住`<=`边界；
另以纯Git常量KNOWN_REAL_RATIO为浮点中心，在上下两侧各找跨越阈值的一对**相邻可表示数**，
断言`delta_inside <= 1e-12 < delta_outside`和两点确实相邻。
不能声称`center+1e-12`与center的浮点差恰为1e-12；输出应保留实际delta用于只读核对。
这不是读取或重新核验真实晚期数值，所有探针都为人工工程比较。

### 哨兵探针范围

ScalarProbe只供应内存inventory／verification JSON和虚构metadata，CSV只是大小为1的逻辑token，
没有生成或读取CSV内容。比值判据通过后，在首次索取summary内容的边界抛ReachedAfterRatio；
拒绝用例必须止于比值错误且不达到该边界。逐一断言完整调用顺序，不能把其他异常误记为通过。
**探针达到哨兵不是完整snapshot成功**，不读取summary内容、不进入CSV parse／validate或归因。
换算函数与MOCK比较路径分别及组合检验，不等于REAL域完整集成；真实域始终关闭。

复用旧checks文件中audit hook／拒绝辅助函数的定义，不调用旧run或旧数值、绘图、fd、资源mock。
保护hook禁止自身新输出目录以外的archive／科学数组open及旧producer导入；不是任意Python的OS沙箱。
本轮和未来该mock均不得打开真实verification、其他控制JSON、CSV、独立数组、模型、轨迹或确认数据。

## 3. 未来启动前条件与精确命令（供审批，本轮不执行）

必须先有绑定上述精确源码、新runner及本卡的独立静态代码复审，并有用户对本次单次执行的明确批准。
任一缺失均不启动。本轮只有AST语法解析／diff检查，所有新用例、边界数值和资源均未实际验证。
新输出目录是否未占用、是否有同名guard／worker、实际hostname、clean及代码等价性均在获批启动前再查；
本轮不为准备卡扫描科学archive、创建输出或占用尝试。目录存在就拒绝，不删除／覆盖或改名重试。

制作方只限本Mac CPU；Python `/Users/wenxiaofang/miniconda3/bin/python3`，无GPU、无SSH、数值线程1。
从第1节工作目录运行以下**唯一命令**，当前不得调用：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 SENS_tensile/s04_late_binding_guard.py --expected-commit e2a5a94c9e47da015f1db7953a55365e3c1aba64 --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/engineering/late-binding-mock-20261017-R001
```

固定guard仅配置ATTEMPT、OUTPUT_NAME、worker及六源码列表，复用未改的预算／异常回执／清理逻辑。
六源码为s04_late_attribution.py、s04_late_attribution_guard.py、s04_late_adapter.py、
s04_late_adapter_checks.py、s04_late_binding_guard.py、s04_late_binding_checks.py（均在SENS_tensile）。
独立复审或启动时还须核对这六文件与源码提交一致、tracked且clean，以及9984226计划不变。
文档提交可以晚于源码提交，不能夹带源码变更。guard传递自身PID和expected_commit两个进程内env标记，
worker检查父PID、固定输出及40位代码标记；这是调用联锁，不是用户许可证明。

## 4. 预算与停止规则

一次 **60秒／512MiB聚合采样RSS／5MiB新增输出**，含日志、checks、receipt；工作58秒保留清理时间，
20ms采样、16KiB回执余量。沿用原口径，不是OS硬峰值约束或采样间资源保证。
计时从guard execute开始，含身份／日志／worker／检查与终态采样；不含解释器和import启动，
回执序列化另受post-receipt时限检查。未来实际资源以回执及文件核对为准，准备阶段不声称已测。

任何断言／异常、部分输出、代码身份不符、预算触限或未知退出立即停并保留现场，失败或触限不重试；
不resume、扩预算、换Run／机器、补跑或转真实数据。仅允许清理本次guard创建的进程组，不触碰其他进程。
first primary_reason与terminal_caps分列，信号成功不是退出证明；receipt落盘失败须结合stdout和非零退出报告，
不得把缺回执、未知退出或部分mock包装成完成。

## 5. 最小输出及未来核对

预期仅checks.json、engineering.log、guard_receipt.json三文件，不生成CSV、图、场、缓存或授权文件。
checks需记录5组、3个换算例、7个类型／缺字段拒绝、3个非有限拒绝及8个带实际delta的探针，
并明确real_data_read=false、fitting_invoked=false、real_acquisition_enabled=false、
csv_contents_read=false、full_snapshot_completed=false、old_suite_run=false。
GENERATED_CHECKS_COMPLETED／COMPLETED仅指本工程清单走完；所有预定断言须满足，不能事后减少清单。
未来主对话仅核对新三文件、完整字节量、代码身份及进程已退出，再只读冻结该新目录；不新增常规hash。
所有旧成功／失败目录、回执和科学结论保留，不写入其他对话已有产物。
这是非科学数值的C0工程检查，上述覆盖表即最小决策表，不增加装饰图或另起计算。

## 6. 当前交付与下一步

新worker／固定guard和本卡已备，未执行、未独立复审，不能宣称Code Ready或预算验证通过。
下一步先提交本次新代码／运行卡的独立静态审核，认可后再批准本卡单次执行；本轮未发审核／执行消息。
不增加真实授权reader／launcher、真实输入核验或真实分析。真实入口及U0.1175／U0.125确认数据关闭，
E017／NN／多目标训练暂缓。主对话统一更新Obsidian和Roadmap，不双写、不重复计算。
