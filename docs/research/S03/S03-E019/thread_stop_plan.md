# E019-D03-G01 — 跨线程故障与停止保护最小修订方案 v0.2

2026-10-18，Europe/London。当前只准备方案和独立静态审查；无实现或测试许可。
源码快照 c1e705096efa0c371ebf8f05fe12d029257d15e3；运行代码仍为 ab6f123a，
生产脚本 SHA 0a7ebbd60d778b8e0cf2171891b68ab928ff73e0092c244f7958174ac9d49acd。
本文件不替代旧方案、执行包、B002 结果或冻结产物。

## 一个问题与事实边界

能否把本次已确认的后台日志/线程故障，提升成整个 CLI 进程的非零失败，
而不是只停止发日志的线程，并防止“exit0 + completion”被误当成功？
这是 C0 运行保护修复，不改变 Q 数值、科学判据、数据语义或真实反演结论。

已知事实（只从源码和 docs/research/S03/S03-E019/underflow_b002_results.md）：
StopLogging.emit 在日志调用线程 raise；Matplotlib font_manager.py:1040
以 threading.Timer(5, ...) 发字体缓存 WARNING；本机 threading.py:1072–1075
在线程边界接住异常并调用 excepthook。主线程没有收到异常，B002 仍 exit0。
该具体因果已由保存 traceback 与源码对应；不是 B001 算术下溢根因。

本轮不读取 local_archive 内容，不重查数值 report、证书或图。

## 推荐最小机制：后台故障升级为进程级失败

不采用“线程里再 raise 一次”或仅 event/checkpoint：它们不能及时终止正在
初始化字体的主线程，也仍可能被库的 except Exception 吞掉。
不把 interrupt_main/signal 回调当硬停止保证；不新增监控子进程框架。

拟为 producer CLI 增加一个仅标准库的 guard（具体代码另批）：

1. 在第三方 NumPy/SciPy/Matplotlib 导入前、旧 raise-only 处理器之前，以
   CLI 显式启用。CLI 路径不再安装旧 StopLogging；非 CLI import 维持原行为，
   不自动更换调用方 factory/excepthook、不启用进程退出。仅本 CLI 使用，
   不建设通用运行框架。先建立状态及保存真实 os._exit 的局部闭包引用，
   再安装入口；安装不完整即非零退出，不能继续导入依赖。
2. 日志 fatal 入口冻结为 **LogRecordFactory 前置检查**：标准 Logger._log
   经 makeRecord 调用 factory 时，原始整数 level>=WARNING 先 fatal，
   不先调用旧 factory、handler/filter/formatter、getMessage、msg.__str__
   或线程信息格式化。这样不经过 Handler.handle 默认阻塞锁，也不受旧
   raise handler 的先后顺序影响。非 fatal 记录才委托已捕获的标准 factory；
   起始 factory 非预期或 level 接口不符则失败，不擅自兼容。主/后台线程相同。
   本契约覆盖标准 Logger._log→makeRecord→factory 路径；不声称覆盖任意
   自定义 makeRecord、直接构造/投递记录或第三方主动绕开标准 logging 的代码。
   对当前字体日志源的标准路径做源码核对，不将未知绕行当作已经受保护。
3. threading.Thread 未处理异常（包括其 SystemExit）进入同一通道。
   warnings.simplefilter('error') 保留：主线程警告仍由既有失败路径处理；
   未处理的后台 Python warning 异常由线程 hook 升级。禁止屏蔽字体日志。
   捕获边界明确为已接入的 logging 通道和 threading.Thread；不宣称覆盖
   被库主动捕获的任意异常、低层 _thread/native 崩溃或所有第三方日志配置。
4. fatal 最外层 try/finally 在取线程信息、格式化或 I/O **之前**建立；
   首先锁存不可清除的 fatal_seen，再尽力记录，finally 用已捕获的真实
   exit 引用执行退出码 70。状态不能通过重装、清事件或捕获异常恢复。
   fatal 路径不依赖 logging、NumPy、json/任意对象 repr、flush、join 或
   atexit。故障文本仅接受原生字符串有限前缀，其他对象写固定占位字节，
   不调用任意对象 __str__、异常格式化或参数展开；固定字节后备事件始终可用。
   仅尽力一次小型原始写入，格式化/写入失败或短写仍必须退出；无补写重试。
   首故障记录权采用非阻塞争用，拿不到锁也直接真实退出，不能等失败线程。
   fatal_seen 的锁存不得先等待该取证锁。主线程的 guard 检查见下一节，
   即使后台卡在写入且事件文件仍空，也不能继续接纳成功。
5. 新 Run 的输出目录经既有权限/新鲜性预检后才绑定事件文件描述符。
   之前的导入故障仅尽力写 stderr 并非零退出，不猜测目录、不创建真实
   输入路径。事件文件固定名 runtime_guard_events.log，初始空，只属于新 Run。
   CLI 整个进程生命周期 guard 持续启用，main 返回后不恢复旧 hook，防止
   延迟线程在写 completion 后才出故障被漏掉。

停止是将已进入 guard 的故障升级为进程失败，不伪称把异常 magically throw
进主线程。前置日志入口与 thread hook 均须有不返回的退出后备；真正实现后
必须用子进程证明，mock/纸面推演不能证明实际停止。

os._exit 会绕过 finally/atexit 与缓冲区清理，所以不能依赖 main 的 except
补写 failure_receipt；允许只留下 fatal 事件/终端和部分文件。诊断可能不全，
但必须非零退出。若磁盘/系统调用阻塞，不声称有硬实时停止延迟保证；
60 秒仍是原软完成检查，而不是增加一个更宽的等待或重试预算。

## 完成标记不能单独放行

增加独立 guard.check：先检查 fatal_seen，再核对 active、已安装 factory、
threading.excepthook、退出闭包等受控身份/启用状态。发现 fatal 或守卫丢失
直接用保存的退出函数非零退出，不依赖取证文件、不自动重装或清状态。
在现有 Budget.check/阶段切换，以及导入绘图、创建下一图、每次 savefig/
sidecar/数值写出、哈希、execution_receipt、completion、成功 stdout 前后
均检查。只加停止检查，不改图内容、数值或预算起点，故障后不启动下一阶段。
尤其 completion 前后与最终 stdout 后须检查；新成功收据记载 guard 健康快照。

未来新 Run 的协议成功条件必须同时满足：外部观察进程 exit0、没有任何
后台异常/警告终端事件、guard 事件文件为空、原身份/数值/预算检查通过，
guard 健康且从未 fatal，并有互相绑定的 receipt/completion。缺退出状态、
guard 身份/状态不符或事件文件不可读即未确认。
guard 版本与事件文件空内容哈希进入新收据；不将 guard 事件当独立算术证书。

若故障发生于 completion 写入之后、进程退出之前，非零退出/fatal 事件
优先于旧标记；**不要求 fatal 回调删除或覆盖文件**。新目录局部产物只作取证。
不得通过 shell 管道丢失 producer exit code，也不得仅查 completion 判断成功。
这是外部观察与收据联合协议，非声称线程与文件写入能够原子提交。
故障模型不包含恶意任意篡改 Python 运行时；阶段检查之间不声称持续身份
监控。守卫检测范围、延迟/OS I/O 阻塞与不完整取证限制必须随新收据保留，
不能把这次局部保护写成“任意线程/原生库所有故障均保证瞬时硬停”。

B002 已生成的完成标记、缓存、证书、图和收据不动，继续隔离；不使用本次
未来修复追认它，也不因缓存现已生成便绕开字体警告进行重试。

## 未来最小改动边界（本轮不实现）

- 新标准库 guard、小范围 producer CLI 接线与新的人工 guard 测试。
  producer 原数值函数、A/Lr/Vr/U/p/r、五个参考乘积站点及操作数不变。
- 源码身份清单须覆盖新增 guard；依赖该源码清单的 verifier 仅作身份/guard
  元数据契约适配，独立数值实现不改、不运行，C/D 仍关闭。
  原 tiny 的 import 行为/65 项判据保留，新增保护不能让正常测试进程意外退出。
- 如最小实现需要改公共数值框架、计时起点或其他数据权限，先报告，不顺延。

## 预算、容差、测试设计（仅纸面，不运行）

原 rtol=1e-12，matrix/vector/square atol=1e-12/1e-15 mm/1e-18 mm²，
谱截断、eta<=0.5 及所有原检查不变。未来资源检查仍单线程 CPU，整包原
60 秒软完成计时口径不变，新增 guard 元数据工作放在原计时区间相应阶段内，
不为保护或取证额外续时。分解若未来另批仍仅 1 SVD/2 薄 QR，不增 q/求解。

最便宜的决定性测试是**后续另批的标准库-only 人工子进程负控**，无需真实
字体扫描、Matplotlib 导入、NumPy/SciPy、同尺寸资产、SVD/QR 或 report：

| 人工情形 | 必须观察到的行为 |
|---|---|
| 正常主线程/正常短工作线程 | exit0，事件空，正常标记仅在预期位置出现 |
| 主线程和后台线程 WARNING/ERROR | exit70；故障后的哨兵动作不执行 |
| 后台未处理 RuntimeError/SystemExit/Python warning | exit70，而非只打印 traceback 后 exit0 |
| 外层库式 except Exception 尝试吞日志异常 | 仍 exit70，不能继续 |
| completion 后的延迟线程故障 | 非零退出覆盖成功标记，原文件保留为取证 |
| 故障格式化/事件写入失败、并发故障 | 仍非零退出，不等待故障锁或重入 logging |
| 旧 handler 会 raise/持默认锁、恶意格式化对象 | factory 前置即 fatal，不进入 handler 或对象格式化 |
| factory/hook 丢失、禁用或被替换 | 下一既定检查非零退出，不重装或宣称通过 |
| 后台取证写入被人工阻塞、事件文件尚空 | 主线程看到 fatal_seen 即非零退出，不继续写成功标记 |
| 导入阶段/尚无合法输出目录 | 非零退出，不猜测/写其他目录 |
| 非 CLI import 及已有失败路径 | 不劫持宿主退出；原正常 API/单位判据保持 |

负控只在隔离子进程中触发真实 os._exit；父测试存活并判退出码/小型临时
哨兵文件，不能只 mock exit 然后声称进程确已停止。父测试整个未来命令
单线程 CPU、60 秒总软预算，子进程等待有上限且计入总预算；超时/不符即
该包首个非预期失败，停止，不自动补跑。确切测试数量/命令在实现审查后再批。

## 独立审查与本轮交付

独立只读 Codex 只看本方案、冻结源码、B002 文档及本机 stdlib/Matplotlib
源文件。重点挑战：最小性、os._exit 的代价、安装顺序、吞异常/晚到故障、
取证失败仍退出、守卫与宿主隔离、完成标记优先级及预算未被放宽。
不按本方案实现，不执行 Python/导入/测试/语法检查或任何数值计算，不读
archive/真实数组/留出，不写文件、联系外部、启动 C/D 或验收。

本轮最小资产为方案与独立审查回执，回到 S03 storyline；无意义结果图。
静态通过仅表示方案可进入用户确认，不是 Code Ready、执行许可或科学通过。
用户确认后才考虑实现/人工测试设计/代码审查及确切命令，测试和新 Run 另批。

## v0.2 对首轮只读意见的采纳

首轮 MODIFY_AND_REREVIEW 绑定 clean d8fd7573、方案 SHA a7a4d00070b2ce5feb5c4d0abbda2df8723aac15db04798b1e7e362e823df46a。
两项阻断均采纳：日志入口前置到 factory，明确不经 handler 锁/旧 raise/
任意格式化；先锁存 fatal、检查守卫身份与状态、防止空事件误放行，并保留
真实退出闭包/固定字节后备。增加相应纸面子进程负控，待焦点静态复审。
首轮与本版都没有运行或实现，静态意见不能追认 B002。
