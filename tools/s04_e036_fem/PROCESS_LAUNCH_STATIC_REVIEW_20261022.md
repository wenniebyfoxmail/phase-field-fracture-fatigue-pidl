# E036 PowerShell 启动静态审查

本记录只覆盖本地源码阅读、编辑、diff 和哈希；没有执行 PowerShell、C#、
MATLAB、FEM 或 SSH。WMI ReturnValue=0 仅证明包装进程创建。

| 文件 | 源码 SHA256 |
|---|---|
| stage_a_launcher.ps1 | 23212cbccc3bf18a7f6b722ba12045c22e6416913d14ebcebbea82eaeed24416 |
| stage_a_watchdog.ps1 | 0f547ac79b23204f207bce663e6847772f876e962d0b7c5a2effd32be200a1c8 |
| stage_a_compare_watchdog.ps1 | d9ac606f2980794432bd04ac99c284d07f3a24bfdb7b59304429caf7fc1c56ae |
| stage_b_launcher.ps1 | e42db4a111d295abca2ab704611391b98cbcb56009726bfefb74e646b1a4ab2a |
| stage_b_watchdog.ps1 | 948da07a23b2131d8fe46db7549b2f36aef3181e29725efd8ba74e93dea5fe55 |

## 入口与日志

外层 detached caller 先独占保存 launch attempt，再用完整 x64 PowerShell 路径、
-NoProfile -NonInteractive -ExecutionPolicy Bypass -File 启动 launcher，
并在 OS 层捕获 launcher 自身 stdout/stderr。采用 cmd 重定向时，必须在
WMI 创建前拒绝已存在的同名日志，避免截断旧记录。结果未知不重用同一 label。

共同参数：Root、Label、Entry、AuthorityFile、AuthoritySha256、WatchdogFile、
WatchdogSha256。A 另有 Kind、PythonExecutable、ArgumentsFile、RequireArms；
B 只允许一个 MATLAB window。launcher 会等待 watchdog，须由外层 detached 创建。

launcher 在启动 child 前保存不可覆盖的 supervisor attempt；两条并行 .NET
stream task 读取 OS stdout/stderr，避免顺序读管道死锁。最后保存退出码、
异常、清理结果及四个持久 execution-policy scope 的前后值。
Bypass 仅作用于进程，没有 Set-ExecutionPolicy。自身解析前错误由外层日志捕获。

watchdog 暂停创建 native child，核对 OS handle、镜像、创建时间、命令行和
显式启动目录后再恢复。新 Job Object 的 kill-on-close 覆盖该 child 及后代；
不按用户名或进程名称杀任务。A/B 共用当前任务目录排他锁。

## 授权与限制

A/B 分别使用 e036-stage-a-authority-v1 和 e036-stage-b-authority-v1，
绑定 producer、root、精确 label、authority ID、授权引用和 SHA。
global_deadline_utc:null 表示无累计截止，没有旧日期/三小时 fallback。
per_job_wall_seconds 是显式的独立防挂时限，必须有限且为正。
MATLAB 保留 -singleCompThread、线程环境 1，Job affinity 不超过允许的 1–4 CPU。

A 两臂记录绑定 authority ID/SHA、各自时限，并核对 false 开始不早于已验证的
absent 完成。比较器变体仅允许 compare_frozen_states.py；
--wall-seconds 必须有限正数且数值精确等于 authority 的 per-job 时限。
已部署 A 文件没有为此改写。

B 另需 request、step 时限、Stage A evidence SHA、implementation review 引用。
PS 验证基本结构；完整 A 成果验收、实际 evidence 文件哈希、请求语义和前态连续性
仍由 B MATLAB driver 检查。B 删除任务目录 5 GB 累计配额，保留 C 盘剩余至少
10 GB 的保护；A 的原 5 GB 配额按 owner 决定保留。

## 复核边界

acceptance_audit 已独立只读审查上述 A launcher/watchdog、比较器差异及 B
launcher/watchdog，未发现新的确定 PS 语法或 ABI 阻断；没有执行 PS。
B 的 step_wall_seconds 仅由 MATLAB cooperative clock 检查，外部硬限是 per-job。
B MATLAB evidence 的角色及真实 attempt 绑定属于另一项审查，不由本记录认定通过。
本记录不宣称 Windows 5.1、Add-Type、Job Object 或生产运行已通过。
进程创建、操作完成和科学验收须分别取得真实证据。

## prepare_02 实际失败后的 v4 控制补丁

本地保存的 inspect_prepare_02_first.json 显示：watchdog 在 Resume 之前因
“Suspended process identity differs”退出，native child exit 124，监督器
exit 1，持久策略前后相同。旧日志没有保存 CIM 各字段，因此不能确定究竟哪项
缺失或相异；不得将其描述为 MATLAB 计算、MEX 编译或科学验收失败。

新增文件，不覆盖已部署字节：

| 文件 | 源码 SHA256 |
|---|---|
| stage_a_watchdog_v4.ps1 | c627b12276107a5577e1b372ba4fbe22f2ae2fabda77935e4ecae70d2dddc880 |
| stage_a_compare_watchdog_v4.ps1 | c38a6dde4fd7c1b5b2c2b808057bff6be79579e0c86cfbd4bf61e7613d983bf4 |

v4 强制核对持有句柄的 PID、镜像、创建时间及 IsProcessInJob。
CreateProcess 的命令/CWD 是明确的输入绑定；CIM 改为补充观测。
恢复执行前保存 identity_observation.json，含 expected、held_handle、
CIM 原值、逐字段匹配、缺失、非空相异和查询错误；started/final receipt
绑定其 SHA。日志写入失败或权威句柄检查失败仍终止本任务 Job。
补丁只经本地静态审查，不由本记录宣称新版本已执行。
acceptance_audit 已对两份 v4 的完整 diff 和新增 C# ABI 独立只读复核，
确认上述 SHA，未发现此次改动范围内的必然 PS/Win32 阻断；未执行或改写文件。
