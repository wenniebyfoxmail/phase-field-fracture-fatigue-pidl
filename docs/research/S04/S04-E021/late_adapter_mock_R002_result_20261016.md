# S04-E021-LATE-ADAPTER-MOCK-R002：单次mock完成及冻结核对

2026-10-16 Europe/London。执行COMPLETED，8组工程检查和7类具名fd错误分支走完，
主对话冻结核对完成。**仅mock工程行为，不是真实归档验证或晚期科学分析。**
唯一一次已消耗，未重试、补跑、读取真实CSV／控制JSON／数组／确认数据或拟合。

## 批准、版本与精确执行

用户本轮明确批准b5ac6cd运行卡、fb484ae代码和唯一R002，60秒／512MiB／5MiB，失败或触限不重试。
卡内“未执行／待批准”是准备时快照，保留原文；本记录是本次实际状态。

- 运行卡 `b5ac6cda35453f49dac08d2f3346bafd050ab880`，与启动checkout内容diff为空。
- 源码 `fb484ae8cdd627f062f3cd2864fb335915ba5188`；静态复审结果已在4abfd82记录。
- 启动checkout `4abfd82ad726f1891c6f30b2a89a0927e3ed895c`。五个受控源码、9984226方案
  与指定提交diff为空，源码及工作树干净。本轮没有代码／配置／方案修改。
- Owner：S04主对话01a1131d-017c-7b03-a95a-ad73ba8fcc9c；专用工作树
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-late-regression-plan-20261016`，
  分支codex/s04-late-regression-plan-20261016。
- Mac `Wennies-MacBook-Pro-14.local`，Python `/Users/wenxiaofang/miniconda3/bin/python3`，
  CPU线程1，无GPU／SSH／producer作业。
- UTC开始2026-10-16T22:27:01.624083+00:00，即伦敦23:27:01 BST。
- guard17148→worker17180，退出0；cleanup=ALREADY_EXITED、exit_confirmed=true，signals=[]。
  primary_reason=null，terminal_caps=[]，errors=[]，receipt_persisted=true。真实运行未发清理信号。
- 启动前新目录不存在、匹配Python guard／checks进程为空。初次ps文本筛选命中的是本次shell
  命令自身，随后以Python进程名称及独立argv basename核对为空；没有把shell误认为第二计算。

唯一调用，工作目录为上述专用工作树：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 SENS_tensile/s04_late_adapter_guard.py --expected-commit fb484ae8cdd627f062f3cd2864fb335915ba5188 --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/engineering/late-adapter-mock-20261016-R002
```

## 资源与控制结果

| 项目 | 本次 | 批准上限 |
|---|---:|---:|
| guard计时 | 0.162771916017秒 | 60秒，工作58秒 |
| 聚合采样峰值RSS | 61,227,008 bytes =58.390625MiB | 512MiB |
| 写回执前输出 | 3,683 bytes | 计入5MiB |
| 全部输出含回执 | 5,212 bytes，3文件 | 5MiB |

计时从guard execute开始，含日志／身份检查、worker、核验及终态采样；不含Python解释器与
import启动，回执序列化另受post-receipt时限检查。RSS／输出为采样监督，不保证OS硬峰值，
也不据此保证其他机器或更大工作集。未为测试消耗到资源上限或注入真实OS故障。
console追加final_output_bytes=5212；落盘receipt不含该追加字段，全量由实际三文件stat之和复核。

## 冻结清单及主对话核对

唯一新目录：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/engineering/late-adapter-mock-20261016-R002`。

先核对receipt／checks／log及两个PID均已不存在，确认无符号链接，再仅移除本次文件和目录写权限。
三文件0444，主目录及空mock_caller目录0555，无实际授权文件／子输出。冻结后内容／mtime不改，
不新增hash，不触碰R001、LATE-ENG-R002或旧失败现场。

| 文件 | bytes |
|---|---:|
| checks.json | 1,841 |
| engineering.log | 1,842 |
| guard_receipt.json | 1,529 |

checks与log完成JSON一致，无未捕获Traceback；主对话只读查看保存记录，没有导入runner或重生成夹具。
这是主对话执行后核对，不冒充独立结果复审；既有独立静态复审与本次执行证据分别保存。

| 本次工程判据 | 保存记录／源码断言对应 | 结论边界 |
|---|---|---|
| 四源及覆盖 | 357生成行、三个保存背景副本、仅四个逻辑名称 | 四源是内存键，不是真实源通过 |
| grant／schema先拒绝 | 11种grant漂移、缺binding及未绑定真实入口拒绝 | 机器联锁不是人类许可证明 |
| MOCK/native reader隔离 | ReadOnlyIO和子类均在metadata/read前拒绝，bomb callbacks零调用 | 只验证所提供native reader，不是任意Python代码沙箱 |
| 绝对授权交接 | 跨cwd，5种env错误、相对路径、父PID错误在授权callback前拒绝 | callback纯内存，没有真实授权reader／launcher |
| 元数据／身份／数值拒绝 | 原15种错误及重复／非有限JSON均拒绝 | 未对真实文件或真实内容认证 |
| summary自身身份 | 错Run、错commit、缺Run、缺commit四例均拒绝且CSV尚未read | 两项必改之一在mock覆盖内通过 |
| 只读fd正常路径 | O_RDONLY\|O_NOFOLLOW、token、关闭及白名单／alias拒绝 | 全部fd均为fake，无真实源open／stat |
| fd错误边界 | 具名7分支完整记录，关闭／read／fstat／metadata次数断言走完 | 不是OS故障或压力测试 |

七分支为OPEN_ERROR、FD_MISMATCH、FSTAT_ERROR、READ_ERROR、FD_DRIFT、SIZE_MISMATCH、PATH_DRIFT。
open失败不close；其余已打开fd的异常／漂移路径各close一次。没有真实kill或真实文件故障注入。
checks明确real_data_read=false、fitting_invoked=false、real_verification_binding=UNBOUND、real_ready=false。
无科学图适用：本次是C0工程检查，上表为最小决策表，不增加装饰图或另起计算。

## 当前决定与唯一下一步建议

修订后8组mock在预算内完成，原两项必改和新增fd边界在声明的mock范围内通过；无需再重复本核验。
PIDL闸门使这一工程进展不被扩大为真实数据有效性、真实分析许可、梯度冲突或物理机制结论。
真实verification selector仍UNBOUND，真实授权reader／launcher未具备，不能直接启动晚期分析。

建议下一步仅**申请最小真实schema查看范围**：获单独批准后，读取指定的
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/control/S04-E021-REPLAY-R001_verification.json`，
只为确定已声明身份／rows／counts／late_ratio的字段路径和类型，不扫描其他文件，不读取CSV、数组、
轨迹或确认数据，不重新计算科学量。当前尚未进行该读取，也未准备实际读取命令／授权。
结构确定后才能据此准备绑定及真实launcher／执行范围，仍不自动分析或拟合；不需此时改顶层模型。

方法对话只读分工不变；本轮仅做一次compact状态读取，显示idle、revision36未变，未发任何执行或
写入消息。主对话唯一写本记录、Obsidian及Roadmap，避免双写／重复计算。
确认U0.1175／U0.125关闭，E017／NN／多目标训练暂缓；原E021科学结论不变。
本地分支及工作树保留、未push或移除，所有已有改动完整保留。
