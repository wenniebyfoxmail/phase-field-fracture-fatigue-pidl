# FN776-r2：控制记录修订，执行待审批

本次权限来源为主S04转交的人方准备要求：补齐控制端超时定位记录，准备新Run
与单次卡，仅静审实际变化；不SSH/连接测试/部署/GPU/科学数组读取/数值测试，
不重启r1，不跑mock，不写共享Obsidian。r1及98e060d9终止记录保持原样。

新CardID：S04-E011-UVH-C1-FN776-CARD-r2。
批准索引：S04-E011-FN776-r2-A1，绑定最终计划SHA256、Dev、Producer、bundle。
新RunID：pf_s04e011_uvh_c1_fn776_r2_20261019。
新root：/mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r2_20261019。
新archive：/mnt/data2/drtao/pidl_archives/pf_s04e011_uvh_c1_fn776_r2_20261019。

## 不变与实际变化

科学worker与square_root.py逐字节复用已审f1ed1ed9；source/SENS力学逐blob不变。
五输入完整路径/大小/hash/解码字段、数学设计、同776坐标z=0、能量及判据不变。
保留旧protocol_fn776.md作为科学设计记录；其中r1身份/权限是历史状态，r2仅以
本说明、inputs_fn776_r2.json及最终卡/执行计划作为当前操作身份，不将旧输入
清单当作可选契约。Guard的唯一活动CONTRACT指向r2清单。

Guard差异为新Run/Card/清单路径、控制日志预留及worker PID/start_ticks/启动请求
记录；PID写入放入自有child的try/finally，保护启动后回执失败时的清理。原25424分账、16*32、900秒、
600/840/890+10秒、RSS/CUDA各8GiB、GPU7 UUID/共享服务身份、4GiB运行余量、
12GiB准入余量及失败不重试均不变。总100MiB内保留1MiB控制诊断，producer
采样阈值从99MiB收紧为98MiB，再留1MiBproducer终止回执。无额外产物额度；
取回副本不重复计算原产物字节。控制日志也采用采样限制，不承诺OS硬峰值。

新增control_r2.py只执行最终计划指定的一条argv，不解释shell字符串、不断线
重连、不自动继续下一步；计划、stdin代码/包的SHA256/字节数、阶段顺序和本地
逐阶段排他claim受核验。stdout/stderr自Popen起直接写入文件，持续保留部分字节，
并保存异常自带的非空或已知空缓冲、开始/结束/时间/子PID/exit/超时/清理记录。
只清理start_new_session建立的自有本地子进程组，不动共享SSH master或其他进程。
批准绑定后、任何Popen前安装SIGTERM处理，将其转为异常，和SIGINT一样走清理及
终态路径。SIGKILL、断电或无法写盘不能保证回执落盘；缺回执时状态未知，不能
把它当作未启动并自动重发。现有排他claim也不能冒充断电后的完整状态证据。
任一失败落terminal.json，后续阶段拒绝执行；未知远端完成状态不写成“已停止”。

新增remote_control_r2.py作为未来固定SSH stdin：输出阶段及每个子命令begin/end，
记录stderr、exit和TimeoutExpired可能的部分缓冲。预检的GPU/身份helper AST与
既有guard相同；不增加资源准入条件或重加白名单。预检仅OS/NVML/路径/旧终态
记录读取。部署/启动/状态/报告复制是分立显式阶段；没有科学替代实现或额外求解。

## 未来阶段与时限（本轮一项也不执行）

最终计划放在代码包之外，由最终卡绑定SHA256，避免源码/包哈希自引用。
每个计划步骤给出字面argv、cwd、stdin大小/hash、超时、前置成功与允许结果。
唯一入口为物化Producer源码中的control_r2.py，必须同时提供execute-approved、
CardID、批准索引与计划hash；无这些精确参数不执行。未来操作人先记录实际人方
批准文本及两次真实对话重复核对，不以固定JSON模板冒充实际核对。

1. local_package：标准库精确物化验证，30秒；代码身份失败即停止。
2. preflight：一次只读SSH，总60秒单列，包含连接/检查；56秒等待上限加4秒本地
   TERM/KILL/reap清理预留。SSH仍BatchMode、ConnectTimeout15，ConnectionAttempts1，
   加-v仅记录连接/认证/复用/远端exec阶段，不预断r1原因，不改共享连接配置。
   需要<=60秒前的真实thread_duplicate_check.json，no_duplicate为true。
3. upload：一次新root创建与bundle流传输，60秒；root不存在才mkdir，写source.bundle
   使用独占模式。每个创建/写入边界留stderr事件；不碰r1路径。
4. deployment：一次空Git物化、bundle核验及标准库verifier，60秒；无基础对象/远程
   补取，文件闭包/锁定solver/洁净状态检查失败即停。
5. launch：一次30秒调用；紧邻启动重新真实核对对话并记录<=60秒的
   launch_duplicate_check.json，再查远端重复worker，排他创建guard.log并detached
   Popen同一/usr/bin/python3 -B guard，CARD-r2与精确Producer写入argv。Guard自行
   重复准入后才读五个科学输入，单次900秒钟从guard开始。连接丢失后状态未知，
   不能重发launch或自动重连。
6. monitor：仅成功读取后的后续观测，最多16次，每次15秒，名义间隔>=60秒；
   无自动调度或失败重连。成功状态中guard终态/错误由原样回执表示，且确认guard及已知worker的PID/start_ticks
   身份已退出才开放报告冻结；worker启动已请求但身份缺失则保持unknown，不取回
   live集合，避免末尾回执写入竞态；不因数值失败
   自动重跑。任何SSH控制失败停止并报告未知状态。
7. manifest、archive、verify_retrieval：确认终态后各一次60/60/30秒，只处理自有
   已有产物，逐大小/hash验证，不解码科学数组或补算。缺回执如实报告；不可因为
   “补齐报告”重启求解。代码包/日志/回执在原产物预算中；取回是副本。

阶段总时限均预留4秒自有客户端清理；不借此延长预检或guard。采样与进程调度
不提供硬实时保证。子命令各有显式上限；外层阶段时限先到即停止。成功的计划
步骤之间可等待/只读查看本地日志，不能用新的SSH来补跑失败阶段。

## r1诚实边界与本轮交付

r1只知道控制端60秒TimeoutExpired；未保留的异常部分stdout/stderr不可恢复，
远端只读脚本执行位置与根因继续未知。不据新代码、AST或人为示例追造r1轨迹。
新控制逻辑尚未运行，不声称已经复现、定位或修复连接故障；这次是可观测性补齐。

本轮仅做实际文件AST/文本/Git差异和源码包空目录完整性核对；不执行控制入口、
远端程序、mock、网络、子进程超时测试、资源预检或科学夹具。仅一次独立差异
静审，复用不变科学代码既有结论。最终卡需人方另行明确批准后才能进入任何SSH
或producer阶段。本对话仅交付本地卡与回执，主S04统一维护Obsidian。
