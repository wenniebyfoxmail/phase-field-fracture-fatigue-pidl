# FN776-r4：本机网络权限修订后的新身份，执行待批

2026-10-24。r3 的本地包核验和真实对话重复检查完成后，受控预检的 SSH 客户端在
本机 TCP 连接之前被执行沙箱拒绝：exit 255、`Operation not permitted`、耗时
0.01175 秒。没有远端 shell、GPU/进程/路径状态、部署、五文件读取或科学计算；r3
的 terminal 回执保持原样，不能维修、重发或当成远端故障。

r4 是独立的新 Run 准备包，唯一新增的控制面条件是：未来的精确控制器必须在允许
网络连接的执行上下文中启动。它不修改 SSH 配置、共享 master、VPN、主机、凭据、
GPU 服务或科学代码，也不在准备阶段额外试连。r2 仍从未调用控制入口；共享
Obsidian/Roadmap仍由主 S04 统一维护。

## 连接证据与 r4 的最窄变化

只做过一次独立诊断连接，远端命令仅hostname，没有查GPU、读科学数据或部署。
探针在2026-10-20 11:05:55至11:06:00 BST完成：TCP0.225秒、SSH banner0.484秒、
公钥认证3.187秒、hostname GPUServer8及exit0共4.356秒。完整脱敏逐阶段输出在
`local_archive/experiments/S04-E011/preparation/connection_diagnostic_20261020/`。

此前已验证的私有连接方式为：BatchMode、ConnectionAttempts1、ConnectTimeout15，
禁用ControlMaster/ControlPath/ControlPersist、TTY、转发和LocalCommand。没有修改
~/.ssh/config、共享master、路由/VPN、server、凭据或任何其他进程。
卡中-v用于阶段日志，探针-vvv用于细节；两者连接参数相同。

现有配置确为ControlMaster auto、ControlPersist28800及既定socket路径，路由指向
utun4、系统代理开关关闭。这些与r1的无阶段日志不足以证明具体原因；“旧复用
连接卡住”仅为未证实解释。该探针不能倒推r1原因，也不证明未来连接或GPU准入。
r3 的本机权限拒绝也不构成 Taobo 连通性或资源状态证据；没有第二次探针或旧尝试
重发。

## 必要差异与不变部分

相对已终止r3，仅更新Run/Card/批准索引/活动契约路径及本机控制器的允许网络执行
前提；执行计划仍固定上述私有SSH参数。控制逻辑、超时日志/SIGTERM清理、
guard/worker退出后报告冻结、一次性claim和失败terminal联锁复用不变。控制工具
沿用control_r2.py等既有文件名，名字表示实现来源，实际常量与计划全部绑定r4；
不创建第二套控制/科学实现。
worker、square_root和source/SENS力学不变；五源完整路径/大小/hash/解码键不变。

Card：S04-E011-UVH-C1-FN776-CARD-r4。
批准索引：S04-E011-FN776-r4-A1。
Run：pf_s04e011_uvh_c1_fn776_r4_20261024。
root：/mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r4_20261024。
archive：/mnt/data2/drtao/pidl_archives/pf_s04e011_uvh_c1_fn776_r4_20261024。
活动契约仅inputs_fn776_r4.json；最终计划及卡在源码包之外独立hash绑定。

保留完整776坐标、固定c1s4/damage/隐藏基底、z=0、同E/E0与原z双读回<=1e-8。
25424分账、16步/32trial、guard900秒及600/840/890+10秒、RSS/CUDA各8GiB、
总100MiB=98MiB正常producer+1MiB控制+1MiB终止回执、4GiB运行显存余量均不变。
GPU7 UUID及共享服务身份/阈值原样沿用，尚未检查现况；任何失败或触限不重试、
不自动重连、不换GPU/目标主机、不加预算、不修依赖或启动替代科学计算。

## 审批后的阶段（本轮未执行）

沿用r2同一阶段：local_package30秒；preflight60秒单列；upload60；deployment60；
launch30；成功monitor后可下一次观测（最多16次、间隔>=60秒、各15秒）；
manifest/archive各60秒；verify_retrieval30秒。各控制阶段内留4秒本地自有客户端
清理，预检等待至56秒停止；guard另有独立900秒。每步只执行最终hash计划中
字面argv/stdin，非执行模式默认拒绝，不自动串行继续或重发失败步骤。

需先保存实际批准文本及真实对话重复检查（<=60秒），紧邻launch再核对一次；
一次私有只读预检通过才建新root。仅传精确bundle，空Git物化/完整性检查后，
一次detached guard，guard重复准入才允许五源读取与唯一求解。未知过程/路径冲突/
资源身份漂移均终止，不重新加白。只清理自有本地客户端和guard自有worker组。

取回需guard及已知worker身份已退出且有终态；未知worker身份或SSH失联不能写成
已停止或重新启动。只复制既有自有报告并校验，不解码数组补算。SIGKILL、断电或
不能写盘仍不能保证终态落盘，缺失保持unknown。源码排他claim不替代真实状态。

本轮新静审只覆盖身份与连接参数及联锁差异，沿用既有科学/控制审查。除上述
一次hostname探针，未运行控制入口、资源预检、mock、数值测试或科学求解。
本轮仅做本地准备与静审；r4 仍需对其精确卡和计划的人方新批准。获批后，控制器
从允许网络的上下文启动一次；任一阶段失败仍停止且不重试。
