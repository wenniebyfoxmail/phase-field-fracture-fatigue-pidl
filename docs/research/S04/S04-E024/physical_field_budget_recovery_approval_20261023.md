# D013 Mac CPU2 v1首停后的权限修复：待批准单次重投（2026-10-23）

**目的／当前：** 完成已批准的三态物理场预算完整头诊断。用户通过引用原v1审批问句，明确回复“审批请执行，没有预算让上限”；已按其所指Mac本地CPU2 v1记录本次离线分析角色例外，未将许可转给Taobo或神经训练。含糊的预算尾句没有用于扩大原限额；本次首停与预算无关。

## 已发生的唯一尝试（保留原件）

- 原manifest `7c77c4db5448d64d8d9e3f647ce7210615df9506d276a7b86740d46ef866f91a`，source18d0e7cb。包／源码／版本元数据／88文件238,110,147B校验通过；这是字节与环境预检，不是三态真实数值准入。
- 2026-10-23 16:09:55英国夏令时，dispatcher47813；scientific-parent47844。监督器`psutil.children(recursive=True)`被沙箱`sysctl(KERN_PROC_ALL)`拒绝，原启动器按首停SIGTERM parent，exit−15。
- 启动器总墙钟0.757213458s，监督段0.043628166s；数值结果根未创建，0模型／FEM场前向、0输出头solve、0NN更新、0完成profile。12行均未执行，不能计零收益／科学失败／三态完成。两个精确PID已核验不存在。
- [原批准及结果](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_package_20261020_v1/execution_outcome_20261023.json) · [原首停收据](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_launch_20261020_v1/launch_failure.json) · [原完整stderr](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_package_20261020_v1/dispatcher_stderr.log)。原包／claim／失败／批准文件不覆盖、不删、不复用。

## 已准备的最小修复

通过`exec_command`的`require_escalated`执行模式允许操作系统的自有子进程监督；不是sudo／系统配置更改，也不关闭预算／RSS／归档保护。相同只读监督能力检查已通过，未重新启动科学任务。原始沙箱拒绝不是自动审批审阅拒绝。

新准备包[D013-offline-20261023-r2](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_package_20261023_r2/D013-offline-20261023-r2)；仅改新packageID／控制输出地址、累计原成本及把所有保留D013归档纳入同一存储监督。原科学18d0e7cb、source tar、Code Ready、88输入、三态各自E023、12profiles／9主方案、13实际保护、永久原E023预算中心、D／BC／窗口／features／damage／history／fatigue、有限步／solver停止全部不变。无新环境安装、新数据、训练、Taobo或私有文件传输。

|核验项|精确值|
|---|---|
|生产机|当前Wennies-MacBook-Pro-14.local，wenxiaofang，本次用户明确批准的本地CPU2离线分析例外；0GPU／不训练|
|解释器|`/Users/wenxiaofang/miniconda3/bin/python3`，原环境精确检查保留|
|新manifest SHA256|`145130938aff41026c1f011fb6d91f6769351d9663cb2e711f4464b77f46c550`|
|新launcher SHA256|`0752d29e326196d982066bb349bfaa6091f2db177424a38091a99cc1da11017d`|
|原科学源码|`18d0e7cb1153dc969c1ee0c21c77ada1297b2d89`，不改|
|新控制根（未创建）|`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_launch_20261023_r2`|
|新结果根（未创建）|`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_execution_20261023_r2`|
|真实批准文件（不存在）|`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_package_20261023_r2/authorization.json`，模板false／retry_authorized=false|
|累计非训练记账|92.675600791s／300s：原v1保守记账＋v2原10s＋失败监督段＋本次5s预留，不清零、不退还旧handoff预记|
|其余资源|数值1800s／重放900s／绘图120s／总3120s，CPU2／RSS3GiB／原loader2GiB不放宽|
|合并存储|已保留准备归档约518,358,415B；原Mac v1、首停CONTROL、Taobo v2准备包、检查、新包／控制／输出均计同一1GiB|

直接一致性核验已完成：source／输入／科学契约与原件SHA相同，launcher仅上述部署字段不同，语法解析通过；准备实录0.125405s，包含于5s预留。依2026-10-22固定基准规则不重跑旧检查／新smoke或自加独立审查。未来唯一科学基准即这组三态原比较，不另训练或增加状态。

## 批准后的唯一调用

在收到对本修复版的**一次重投许可**后，生成绑定上述manifest及该次原话的external authorization；以`exec_command sandbox_permissions=require_escalated`单次调用：

```text
nohup /Users/wenxiaofang/miniconda3/bin/python3 /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_package_20261023_r2/D013-offline-20261023-r2/launch_d013.py --authorization /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_package_20261023_r2/authorization.json
```

stdout／stderr写新package根外部日志，保持新session／原监督器；预检全通过才单次执行，任何原停止条件生效后不自动再投。已有已选权限模式的能力核验可复用，不再次问版本／地址／哈希。完整运行结束才做既定重放／汇总／图表；不把dispatch当成功。

**本次唯一审批：是否批准按上述修复包与执行模式单次重投？** 原批准是“单次执行、异常不自动重试”，已产生一次真实spawn和首停记录；原authority已消费，所以不能把本次权限修复直接视为尚未用过的首次许可。此限制来自用户批准的[原v1范围与首停规则](physical_field_budget_execution_approval.md)，不是追加Code Ready或机械审批门。


## 已批准并执行：取消资源上限的前瞻修订（2026-10-23）

用户已明确批准“确认批准按修复执行卡单次重投……没有任何资源上限”。本卡不再等待首次重投许可；时间／RSS／归档与legacy2GiB硬限制按该次指令撤销，实际成本仍记录。原r2包未启动，其原快照保留；r3是此次已批准资源修订的执行实例，不另消费第二次重投许可。dispatcher76816、science-parent76846已在允许自有进程监督的权限模式单次运行，原监督权限错误未重现。

manifest `d4a5a5f6dd33d9f385f916450270dc4d4ffcf30184c7583f0ca4a5a9212850df`；独立资源策略 `6685c8061f45a7ded9965a13c0e0c9368d0bb26a527d95a5444d0eadaaa06e68`，原18d0e7cb源文件仍逐字节保留。每个科学进程provenance记录生效策略，不能省略策略而宣称原资源合同仍有效。CPU2是保留的配对数值配置，非开销额度。三态12profiles／13保护／物理Q与原中心／BC及冻结history-fatigue保持；原SLSQP200次、最多3次重新线性化与9有限步属于这次保留的有限求解算法设定，不保证收敛或给出非线性可达性界。

当前执行／完整结果位置：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_execution_20261023_r3`；真实批准／命令／状态：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_package_20261023_r3`。本次只跟进这一已启动任务，不启动后续算法修复或训练，不对外发送。

## 完成记录（2026-10-23）

已批准r3单次重投完成三态12profiles、原生重放与绘图。12个有限SLSQP均未返回代理可行新点，0接受；所有最终场精确保留E023。无资源上限触发，非物理不可行结论。既有c60实际可行头与下一项初始化修复仅作分别标明的证据／提案。见 [完成结果、精确分区表与成本](physical_field_budget_result_20261023.md)。不再标为运行中，未启动下一实验。
