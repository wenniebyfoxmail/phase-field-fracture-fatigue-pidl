# SSH连接诊断：私有连接可用，r1历史原因仍未知

2026-10-20。本轮执行范围为已核实的较新人方要求：只读诊断连接并准备新卡，
不执行r2、不重复计算。r2从未调用控制入口或SSH预检，唯一尝试未消耗；r1
超时终态和缺失输出保持原样。没有GPU/科学数据/部署/求解或共享Obsidian写入。

## 原始证据与实际结果

证据目录：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/preparation/connection_diagnostic_20261020/`。
已有local_checks.json及安全字段ssh_config/route/vpn/proxy输出；本轮只增加一次
probe_claim.json、probe.stdout.txt、probe.stderr.txt、probe.events.jsonl及probe_receipt.json。
stdout/stderr在读取时逐行脱敏并落盘；不是事后重建的阶段日志。

探针2026-10-20 11:05:55–11:06:00 BST（原始日志保留UTC）：

| 真实标记 | 从开始经过秒数 |
|---|---:|
| TCP Connection established | 0.225 |
| Remote protocol version / SSH banner | 0.484 |
| Authenticated using publickey | 3.187 |
| Sending command: hostname | 4.027 |
| Exit status0 / hostname GPUServer8 | 4.356 |

客户端exit0，无需TERM/KILL。总时限35秒（31秒等待+4秒自有客户端清理预留），
ConnectionAttempts1；没有重试、第二连接探针或自动重连。远端命令仅hostname。

连接参数为：ssh -T -vvv、BatchMode=yes、ConnectTimeout15、ControlMaster=no、
ControlPath=none、ControlPersist=no、ClearAllForwardings=yes、PermitLocalCommand=no，
目标仍为同一gpu-taobo alias。未改SSH配置、共享master、VPN/路由、代理、server、
credentials或其他进程。原始输出屏蔽本地home、目标IP和密钥指纹，未记录密钥内容。

## 已知、推测及恢复边界

本地安全字段显示原alias配置启用ControlMaster auto、28800秒ControlPersist和
固定socket。到目标有utun4路由、系统HTTP/HTTPS/SOCKS/PAC代理关闭；列出的
内建IPSec服务为Disconnected，不足以判断第三方VPN是否工作。

本次私有连接实测通过TCP、SSH握手、公钥认证及远端命令，确认当前该连接路径
端到端可用。新卡固定同一私有非复用路径，-v保留阶段日志（探针-vvv仅更详细）。
这是可用的客户端绕行方案，避免依赖共享复用连接，不修改或停止共享master。

r1只保留外层60秒TimeoutExpired，异常内部分输出未留存，因此无法将历史失败
定位到连接/认证/复用/远端shell/资源命令中的一层。旧复用连接可能卡住只是
未证实解释；本轮没有测试旧复用路径，不能用新成功倒推出旧根因或补造r1日志。
当前也没有GPU7资源准入、科学数组或数值可行性证据，成功hostname不能代替它们。

## 后续

按最新只读范围准备全新FN776-r3卡/Run，保留原科学方案与全部预算/停止规则。
新卡仅变更必要私有连接参数与身份/路径，复用已审科学和控制逻辑，做差异静审。
最终精确卡仍待人方审批；不得自动将本次诊断当成r2/r3执行授权或FN776预检通过。
