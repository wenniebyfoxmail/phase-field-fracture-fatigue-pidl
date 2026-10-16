# S04-E021-LATE-ADAPTER-MOCK-R002：单次运行卡 v1（未执行，待批准）

2026-10-16 Europe/London。用户本轮仅批准两项局部修订、差异mock／fd错误边界编写、直接静态
复审及新运行卡准备；**没有批准补跑**。本卡不创建输出／授权文件，不复用R001，不自动执行。

## 身份与范围

- Owner：S04主对话01a1131d-017c-7b03-a95a-ad73ba8fcc9c；Storyline／Experiment：S04／S04-E021。
- 尝试：S04-E021-LATE-ADAPTER-MOCK-R002。C0工程检查，仅生成／内存mock；不是实际归档或科学分析。
- 源码 `fb484ae8cdd627f062f3cd2864fb335915ba5188`，基于6697eb1558e7146ea75d4824256787dc7e7d57ef。
  分支codex/s04-late-regression-plan-20261016，专用工作树
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-late-regression-plan-20261016`。
- 仅两项适配逻辑修改：summary自身Run／commit；MOCK域在源IO前拒绝ReadOnlyIO及其子类。
  追加4种summary身份拒绝、2类native reader拒绝和7类fake-fd错误／漂移用例。
- 除固定新尝试／新目录身份外，监督器及其预算逻辑不改；纯核心、9984226计划、四源名、原数据
  角色、分组、归一化不改。没有真实schema绑定、真实launcher或实际授权reader。

## 精确调用（供审批，当前不得执行）

制作方仅本Mac CPU，Python `/Users/wenxiaofang/miniconda3/bin/python3`，GPU不可用／不使用，
guard固定数值线程1。启动前另查实际hostname，启动后由回执记录hostname、PID、UTC及command。
本轮不为准备卡调用runner、创建输出或占用尝试。

工作目录：上述专用工作树。

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 SENS_tensile/s04_late_adapter_guard.py --expected-commit fb484ae8cdd627f062f3cd2864fb335915ba5188 --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/engineering/late-adapter-mock-20261016-R002
```

`--out`只能为以上新固定目录；存在即尝试已占用，拒绝覆盖、删除或换名重试。
启动checkout可包含之后的文档提交，但5个guard受控源码与frozen计划必须与指定代码提交相同、
源码clean，且已有绑定本提交的独立静态复审和用户对此卡的明确单次执行许可。缺一项均不运行。
同时核对没有同名guard／worker进程，不向其他对话发执行任务。

## 预算与停止规则

一次 **60秒／512MiB聚合采样RSS／5MiB新增输出**，包括worker、日志、checks、receipt。
guard工作58秒保留清理时间，复用20ms采样／16KiB输出回执余量；不是OS硬限额或采样间峰值保证。
预算计时从guard execute开始，日志／身份／worker／检查与终态采样纳入；Python解释器与import
启动不计入该guard时钟，回执序列化时间另受post-receipt 60秒检查。未来报告须保留此口径。

失败、异常、触限或部分输出立即停止并保存原原因／终态，不能自动重试、resume、扩预算、转机器
或换Run。只允许清理本次guard创建的worker进程组；不能把信号成功当退出。需结合console JSON、
进程退出码和receipt_persisted核对；缺receipt不声称完成。未知退出先报告，不碰其他用户进程。

## 预期覆盖与最小输出（全部尚未运行）

沿用现有5组内存适配检查并追加3组，预期8组；不是重跑旧数值归因／绘图／22类监督器资源mock。
所有四源名只是内存键，保护hook禁止真实源open，但不是任意Python对象的OS沙箱。

| 修订目标 | 新差异mock判据 |
|---|---|
| summary自身身份 | 错Run、错commit、缺Run、缺commit全部拒绝，且CSV尚未read |
| MOCK与native reader隔离 | ReadOnlyIO和子类均在metadata/read之前拒绝；bomb callbacks零调用 |
| fd错误边界 | OPEN_ERROR不close；FD_MISMATCH、FSTAT_ERROR、READ_ERROR、FD_DRIFT、SIZE_MISMATCH、PATH_DRIFT已开fd各close恰一次；read／fstat／metadata调用数量与预定分支相符 |

fd层所有open／fstat／read／close均为fake；不对真实源进行故障注入或OS压力测试。
R001的mock结果不能证明本修订已通过；本轮仅ast.parse和git diff检查，没有导入任务模块或执行用例。

最小输出：`checks.json`、`engineering.log`、`guard_receipt.json`及空mock_caller目录。
COMPLETED／GENERATED_CHECKS_COMPLETED、无触限／异常、退出确认、8组及7个具名fd错误分支记录
是预期工程完成口径；如检查不能走完则保留失败，不放宽。无科学图适用，以上目标—判据表为C0决策表。
结束后只读核对本次三文件、完整字节量与进程终态，再只读冻结本次新目录；不增常规hash。
原R001、LATE-ENG-R002和旧失败现场均不动。

## 完成后的边界

即使通过，也仅支持修订后mock工程行为，不等于真实verification selector、真实授权交接、
科学有效性或真实运行批准。确认U0.1175／U0.125保持关闭，E017／NN／多目标训练暂缓。
结果与Obsidian由主对话单写，方法对话只读复审，不并行实现／测试／拟合。
