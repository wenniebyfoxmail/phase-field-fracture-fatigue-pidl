# S04-E036 Stage A 控制修复 v4：追加记录

本记录追加在 3ee4d724 的启动修复记录之后；不覆盖旧锁、code_02、prepare_02
日志或任何历史结果。当前完整 Stage A 尚未成功。本地工作仅为源码/日志阅读、
文档及哈希记录，没有在本地或由本子代理执行 SSH、测试、MATLAB 或 FEM。

## 当前人方分工

case/analysis/continuation_03_division_authority.json 记录人方当前分工：
timing 本窗口只完成阶段 A；整体复现 owner 复用已核验的 A 结果，负责 B、
PIDL 对照、训练及优化与网络表达差距归因。本窗口不再启动 B 或训练。
取消累计预算，但保留显式单任务防挂、最多 4 CPU、原生串行、共享资源检查、
不改全局执行策略；科学阈值与输入/历史边界不变。此前 B 代码只作为已准备材料。

## prepare_02 失败与 v4 最小改动

冻结 watchdog 0f547ac7 在暂停创建子进程后、Resume 之前，因 CIM 身份全等检查
报 “Suspended process identity differs”。native child exit 124，supervisor
exit 1；错误日志捕获和全局策略前后比较已实际工作。旧日志没有保留 CIM 各字段，
因此具体哪项缺失或不同仍未确认，不能用后一次观测倒推旧失败原因。

另存 stage_a_watchdog_v4.ps1 和 stage_a_compare_watchdog_v4.ps1，
不改被冻结的 launcher/watchdog。v4 在恢复前重复核对持有句柄的 PID、
镜像、创建时间及 IsProcessInJob；命令/CWD 绑定明确的 CreateProcess 输入。
CIM 作为补充观测，expected、held_handle、CIM 原值、逐字段匹配、缺失、
非空差异及查询错误在恢复前写入 identity_observation.json，started/final
receipt 绑定其 SHA。诊断写入或权威身份检查失败仍清理本任务 Job。
独立 acceptance_audit 静态复核了完整 diff 和新增 ABI，未发现必然阻断；
这项静态结论没有替代实际执行证据。

## prepare_03 实际控制层结果

- stage_prepare_03.json：06:54:48Z，6 个新文件核验；两个 v4 的 Windows
  PowerShell Parser 错误列表均为空。
- launch_prepare_03.json：06:55:14Z，51 个冻结来源文件匹配，启动前 compute
  列表为空；WMI 返回 0 仅作为包装进程创建证据。
- 首次只读 inspector 在用 ReadAllText 读取仍被 cmd 打开的日志时遇到共享
  冲突。后续 inspector 改为 FileShare.ReadWrite，并分别保存文件读取错误；
  这是观测器修复，没有重启 compute。
- inspect_prepare_03_second.json：暂停身份记录的自有句柄 PID、镜像、创建
  时间匹配且 in_owned_job=true。此次 CIM image=null；PID、command 和
  creation 检查匹配，没有非空相异字段。这只描述 prepare_03。
- MATLAB 本次确已启动并进入准备入口，随后在 e036_sha256_file 第 14 行把
  EOF ferror 当作读取错误而退出。调用点是 prepare driver 第 5 行的初始
  config hash，因此尚未完成该哈希检查，未进入 checkcode/mock、fresh build
  或原生 FEM。watchdog 收到 child exit 1，supervisor 继续传播失败；
  MATLAB stderr/logfile 和两层控制日志均已保存。
- 最后一次本地所读 inspector 时间 06:55:48Z：进程列表为空、output 列表
  为空；global_policy_unchanged=true。

这证明了本次控制身份、日志和失败传播链已工作，不是 Stage A 科学验收通过。
EOF helper 的最小修复由 fem_audit 负责，使用新 code/attempt；本记录不预称
后续修复成功，不改变科学设置，也不触发本窗口的 B/训练。

## 证据与锁

原 case：local_archive/experiments/S04-E036/stage_a_20261021_2142。
本记录使用以下追加证据：analysis/continuation_03_division_authority.json；
logs/inspect_prepare_02_first.json；logs/stage_prepare_03.json；
logs/launch_prepare_03.json；logs/inspect_prepare_03_first.json；
logs/inspect_prepare_03_second.json；run_workspace/prepare_03/prepare_03_deployment.json；
run_workspace/inspect_prepare_03_v2.ps1。
新 stage_a_control_v4_lock.json 固定两份 v4、静态复核记录、本记录、当前分工
及上述证据哈希。旧 stage_a_launch_repair_lock.json 原字节保留，与 3ee4d724 中的历史快照
一致（旧锁自身的 base_commit 仍为 9a763140）；新记录不追改旧运行状态。
