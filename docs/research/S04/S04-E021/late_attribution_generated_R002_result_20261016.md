# S04-E021-LATE-ENG-R002：单次生成核验与冻结核对结果

2026-10-16 Europe/London。执行COMPLETED；生成核验GENERATED_CHECKS_COMPLETED；
主对话输出核对完成。**仅生成数据工程结果，不是真实U0.11晚期分析或新科学收益。**
唯一一次已用完，未重试、补跑、读取真实数据／控制JSON／数组／确认数据或拟合。

## 授权、代码与执行回执

- 用户本轮明确批准8cf9cb5运行卡，唯一S04-E021-LATE-ENG-R002，60秒／512MiB／5MiB，
  失败或触限不重试。卡中的“未执行／尚未审批”保留为准备时快照，实际状态以本记录为准。
- 审核代码2886703ef5762c8956bb2fe74e0f53c0ca8f1670；静态复审记录8b69209。
  启动checkout8b69209779f44d18c43145b0efe6d27835480f88，三源码与9984226方案diff为空，
  tracked源码干净；卡与8cf9cb5相同。本轮没有任何代码修改。
- 专用工作树 `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-late-regression-plan-20261016`，
  分支codex/s04-late-regression-plan-20261016，原base46ca50c；工作树无local_archive链接。
- 制作方Wennies-MacBook-Pro-14.local，Python `/Users/wenxiaofang/miniconda3/bin/python3`，
  数值线程1、无GPU。UTC开始2026-10-16T18:56:00.520607+00:00，即伦敦19:56:00 BST。
- guard2654 → worker2674，worker退出0；cleanup=ALREADY_EXITED、exit_confirmed=true，
  primary_reason=null、terminal_caps=[]、errors=[]、receipt_persisted=true。真实运行未发清理信号。
- exec session35374只调用一次；write_stdin只等同一进程。启动前新目录不存在，
  结束后两个PID均不存在，Python进程筛选无本任务guard／checks残留。没有第二计算或跨聊天执行消息。

精确调用与8cf9cb5卡一致：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 SENS_tensile/s04_late_attribution_guard.py --attempt S04-E021-LATE-ENG-R002 --expected-commit 2886703ef5762c8956bb2fe74e0f53c0ca8f1670 --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/engineering/late-attribution-20261016-R002
```

| 资源 | 本次记录 | 批准上限 |
|---|---:|---:|
| guard计时 | 8.784801500秒 | 60秒，工作58秒保留收尾时间 |
| 聚合采样峰值RSS | 244416512 bytes =233.09375MiB | 512MiB |
| receipt写入前输出 | 298799 bytes | 计入5MiB口径 |
| receipt及全部输出 | 300321 bytes =0.286408424MiB，66文件 | 5MiB |

计时含生成计算、mock、图与终态采样，回执序列化在其后，终态未触限；完整文件大小另经主对话核对。
内存／输出为采样监督，不保证OS硬峰值或采样间瞬时写入从不越界。本次实际记录在预算内，
不是所有机器／工作集的资源保证；mock中的虚拟超限数值不是本次真实资源超限。

## 冻结位置与清单

唯一新目录：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/engineering/late-attribution-20261016-R002`。

先确认2654／2674已退出、目录内没有符号链接，再移除本次全部输出及目录写权限。
66文件均只读，文件为0444、目录无写权限；冻结后无可写项，内容与mtime不改，不新增hash。
只改本次生成目录权限，旧失败现场late-attribution-20261016-9984226及科学档案保持原状。

| 主文件（相对新目录） | bytes |
|---|---:|
| guard_receipt.json | 1522 |
| checks.json | 6844 |
| engineering.log | 6908 |
| GENERATED_ONLY.csv | 16494 |
| generated_report/diagnostic.csv | 3578 |
| generated_report/summary.json | 1397 |
| generated_report/diagnostic.png | 80169 |
| generated_report/README_analysis.md | 843 |
| mplcache/fontlist-v390.json | 144769 |

另57文件来自本次22类mock子目录，全部计入300321-byte总量。mock的RECEIPT_WRITE_FAILED
故意没有落盘回执，由worker捕获的控制台JSON断言；这是预期虚拟分支，不是本次真实guard回执缺失。
日志含一次正常字体缓存建立提示与完成JSON；其中Error／异常状态名属于预期mock描述，无未捕获Traceback。

## 核验内容与主对话只读复核

checks.json记录8组检查及8个具名数值夹具，全部走完；包括旧换行字节比较、分解闭合、k50
并列与固定分支、无效输入拒绝、S_plus==sum_tau不可识别、harm40／41邻界、C121仅提核查，
以及只读生成CSV保持和图表产出。它们均为人为生成数值，绝不作为真实数据诊断。

主对话冻结后只读检查本次新文件，未导入runner、重新生成夹具／图或执行第二次测试：

| 核对项 | 结果与边界 |
|---|---|
| 主guard控制回执 | COMPLETED、退出0、无primary／terminal cap／异常；代码及checkout与批准身份相符 |
| 生成源覆盖 | 357行，u011／u0115／u012／u013分别121／99／82／55；u011晚期81行 |
| 报告表 | C41…C121连续81行；逐行D=m1−m0；正负分解与保存summary一致 |
| 生成示例汇总 | S_plus=41、S_minus=20、S_net=21，k50=21，harm41／improve40；仅核对工程示例，不是实际U0.11结果 |
| 22类虚拟guard分支 | 21份落盘mock回执与各expected_status一致；1份故意不落盘回执的分支按缺失预期及worker控制台断言核对 |
| 关键清理分支 | 两次超时／信号失败均记录EXIT_UNCONFIRMED、worker_exit=null；TERM超时后KILL确认退出分支正确；全部real_child_processes=0 |
| 首次原因保留 | CHILD_FAILED_WITH_FINAL_CAP保留CHILD_FAILED，并另列WALL_CAP；不覆盖成笼统终态失败 |
| 冻结与总量 | 无符号链接、无可写项，66文件合计300321 bytes；两个真实PID均不在 |

22类mock没有真正等待60秒、占用512MiB、写满5MiB或向真实进程发TERM／KILL。
因此本次验证的是逻辑与回执分支，不是对真实OS故障／硬资源限制的压力测试。
主对话保存表核对不是另一位审核者的独立结果复审；独立静态代码复审与本次执行证据分别保留。

## 生成图目检

两联图源于本次generated_report/diagnostic.csv：A保留全部81周期正负MSE差与零线，
B累计正超额并标50%和k50。已打开PNG目检，面板非空、标签可读、无重叠，
标题醒目标为GENERATED ENGINEERING ONLY及非物理归因。图内k50=21只是生成例子。
README给出单位、读图顺序、加总口径和禁止结论；未重画或修改冻结输出。
research-figure-workflow用于标注和可视QA；PIDL闸门使工程完成与科学结论分开。

## 决策与唯一下一步建议

本次单次生成工程核验完成并经主对话核对，不需要再跑同一核验。旧失败记录不删除或洗成成功。
代码／生成证据补齐了工程行为，但真实四源读取、路径／metadata校验、背景摘录与执行批准
交接仍未实现；不能直接运行真实晚期分析，不能从生成图推断实际退化分布或顶层模型成因。

建议下一步只准备这层**最小只读适配器与mock交接**，先依据Git内字段声明列清输入／元数据／
授权合同及缺口，再独立审核；涉及实际源记录读取或真实分析时另行明确批准范围。
本轮不实施适配器、不扩读、不拟合，不打开确认数据或自动发送新审核任务。
现有材料足以记录本次工程结论，暂不增加第二项资源核验或额外模型比较。

原主对话唯一写入本记录及Obsidian／Roadmap，其他对话已有改动不动，方法对话未触发新任务。
旧E021科学判定与晚期退化不变，U0.1175／U0.125确认数据关闭，S04-E017／NN／多目标训练暂缓。
记录提交保存在本地专用分支，未push或移除工作树；实际生成证据仍在上述只读目录。
