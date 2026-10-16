# S04-E021-LATE-ENG-R002：新生成核验运行卡 v1（未执行，供审批）

2026-10-16 Europe/London。本卡仅准备；独立代码复审尚未发送／完成，执行尚未获批准。
身份为**生成数据工程尝试**，不是原科学拟合R002或真实晚期分析。不得自动执行本卡命令。
主对话01a1131d-017c-7b03-a95a-ad73ba8fcc9c唯一执行／记录，方法对话仅只读复审。

## 问题、范围与身份

唯一问题：修订监督器及未跑的边界mock，能否在原更小预算内完成全套生成标量核验、
保留失败／清理／回执状态，同时保持9984226分解口径不变？只支持C0工程行为，不是新科学结果。
原失败尝试late-attribution-20261016-9984226和其8文件保留，不删除、解锁、覆盖或续跑。

- Storyline／所属Experiment：S04／S04-E021（已关闭科学结论的工程补充）。
- 新尝试ID：S04-E021-LATE-ENG-R002；仅一次，失败或触限不重试。
- 审核候选代码：2886703ef5762c8956bb2fe74e0f53c0ca8f1670；前次代码复核0f10c6a，
  复核记录13db6f2。本次guard／checks改动必须重新独立审核，不继承旧认可。
- 工作树：`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-late-regression-plan-20261016`。
  分支codex/s04-late-regression-plan-20261016；原base46ca50c，本次修订基于13db6f2。
- 制作方：本Mac，Python `/Users/wenxiaofang/miniconda3/bin/python3`，无GPU，数值线程1。
  主机名、guard／worker PID、UTC开始、代码／checkout身份与命令由实际guard回执记录；目前无运行PID。
- `--expected-commit`绑定候选三源码及方案；后续仅文档提交可以保留，源码／方案差异或脏源码即停止。
  这个参数仅是代码互锁，不是人方批准凭证；批准与复审必须由主对话在启动前核对。

## 输入准备边界

只用checks自己生成的357行六列CSV，四前缀121／99／82／55；focus固定u011 C41–121。
数值来自生成夹具，不取真实表的MSE、场、模型或系数。ratio用生成期望值，不冒充真实已知比值复核。
允许读取三份源码、冻结方案、Git元数据、Python／Matplotlib依赖及系统字体，和本次新目录中自己
产生的生成CSV、mock JSON等。不得导入旧拟合／重放模块，audit hook在新模块导入前安装。

**不读任何真实percycle.csv、四源控制JSON、模型、轨迹、NPZ/MAT/PT、C20或确认数据。**
不增加输入链接、复制旧payload、预热／复用旧缓存或创建真实授权文件。真实适配器仍缺，不能借本卡实现／运行它。
输出路径仅预先声明，本轮未创建；未来开始时由guard独占mkdir，不提前手工mkdir占用它。

固定新输出：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/engineering/late-attribution-20261016-R002`

预期内容：工程log、生成CSV、生成报告CSV／summary／两联图／README、mock子目录与回执、
checks.json、guard_receipt.json、字体缓存。所有这些均计入输出预算，不能只数图或主报告。

## 拟执行精确命令（尚未授权，不在本轮调用）

cwd为上面的专用工作树；唯一一次前台有界调用：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 SENS_tensile/s04_late_attribution_guard.py --attempt S04-E021-LATE-ENG-R002 --expected-commit 2886703ef5762c8956bb2fe74e0f53c0ca8f1670 --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/engineering/late-attribution-20261016-R002
```

不可直接调用checks绕过监督器，不另开预跑／资源探测／参数扫描。若代码变动，重新绑定审核与卡，
不能只改命令SHA继续使用旧许可。实际执行仍需要用户另行批准本卡精确范围，送审许可不等于执行许可。

## 预算、成功口径与停止

| 项 | 上限／执行口径 |
|---|---|
| 时间 | 60秒；guard execute计时覆盖输出预留、Git身份检查、生成计算、全部mock、图、清理及回执；工作阶段58秒停止，留2秒收尾 |
| 内存 | 512MiB聚合采样RSS，guard＋worker及其可见后代；不是OS硬峰值保证，短暂Git调用或采样间瞬时峰值不保证捕获 |
| 新增输出 | 5MiB，含上述log、mock、缓存与receipt；触发前预留16KiB，终态再检查。采样不能保证瞬时写入绝不越界 |
| 线程／GPU | 数值线程1，CUDA_VISIBLE_DEVICES空；不承诺CPU硬亲和性，不开任何求解器／训练 |

正常完成至少须同时核对：启动工具exit0；guard.status=COMPLETED、primary_reason=null、
terminal_caps为空、receipt_persisted=true；真实worker退出0且cleanup确认；checks.json生成核验
完成标记及各mock预期相符；输出主表81行、生成源357行，生成图／README完整；资源记录在预算内。
mock里预期失败的模拟回执不等于本次真实worker失败，但必须明确virtual_only。

覆盖：原分解／排序／分支／无效输入、字节比较、S_plus等于sum_tau不可识别、harm40／41邻界，
原六类guard路径、严格预算边界、旧目录拒绝、来源提交不符／脏源码／Git超时、启动／日志异常、
TERM超时→KILL、KILL后等待仍超时／未知、wait／signal／poll异常及回执不可写、首次原因保留。
新增用例当前均未执行，不能凭静态存在判为通过。

任一异常／触限／缺输出／需要扩大科学读取范围即停止，保留现场，不重试、换目录偷偷补跑或加预算。
清理只针对本次Popen创建的进程组。信号不证明退出：两次0.25秒等待及最终poll仍未确认时，
记EXIT_UNCONFIRMED、worker_exit=null，报告需处理，不再启动作业或误记预算已被完全控制。
若磁盘不可写，回执可能不存在或不完整；结合启动工具stdout／exit核对，不以残留文件声称完成。
收尾写入异常只尽力保存控制证据，不保证故障介质一定落盘；不会更换路径重试。

## 执行后才做的核验与留存

先核对本次工具终态、stdout、回执、worker状态；确认已退出才冻结本次生成输出／控制证据。
随后仅核对本次生成CSV／JSON／PNG，目检两面板正负差额／零线及累计正超额／50%／k50，
标题必须为GENERATED ENGINEERING ONLY，不能写成真实U0.11诊断结果。不追加第二次图形计算。
只按路径、文件数／大小／权限和回执保留，不增科学数据hash。若仍有未退出worker，不把可写现场伪装为已冻结完成。

即便完整通过，也只说明此代码／环境的一次生成工程核验。真实四源绑定、授权交接、真实分析及
独立结果审核均不会自动完成；E021旧科学结论、晚期退化和确认数据隔离不变。
主对话统一记录与Obsidian，不触发方法对话计算或双写。
