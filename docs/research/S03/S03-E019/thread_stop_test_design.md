# G01 v0.2 — 实现与纯人工子进程测试设计 v1

2026-10-18。用户已确认方案并授权实现/只读代码审查；**暂不执行**任何测试、
语法/导入检查或资源运行。源码比照基线 5e7553887f70c840e02a830f2e5ab8f7553d6869。

## 局部实现

- aa2024_runtime_guard.py：仅标准库；显式 CLI install 前捕获真实退出闭包，
  标准 logging factory 前置 fatal、Thread excepthook、fatal_seen 锁存、
  非阻塞记录权与一次尽力原始事件写入、守卫状态/身份/事件文件检查。
  导入本 helper 不安装全局 hook；退出码70覆盖完成标记，强退出不依赖清理。
- aa2024_q_recheck.py：CLI 在 NumPy 前启用，import 时保留原异常行为；
  guard_point 捕获初始 guard 引用，防止全局引用变 None 静默失效。
  只在原 Budget.check、文件/绘图/元数据阶段增加停止检查，原起点/60秒不改。
  新事件文件在 Budget 启动后绑定、纳入产物哈希；新收据增加 guard 健康快照。
- aa2024_q_verify.py：仅源文件清单及 guard 元数据适配，数值函数不改。
  未来 CLI 必须提供 --producer-exit-code 0 和 --producer-clean-terminal；
  这是调用方须以实际外部执行记录支持的声明，verifier 无法仅靠数值文件
  独立证明进程退出/终端干净，不得把声明本身当证据。旧B002继续隔离。
- 两端源身份清单从5项扩为7项，新增guard和本人工测试；原65项测试和
  aa2024_dyadic_reference.py 字节保持。没有修改 A/Q/投影/容差或原权重。

## 拟运行的一次测试包：26个独立人工子进程 + 两类源码静态断言

父脚本 scripts/test_aa2024_runtime_guard.py 只导入标准库和新 guard，
不导入 producer/verifier/原算术模块/原65项测试。禁用 scientific import 的
meta_path guard 在测试过程中拒绝 NumPy/SciPy/Matplotlib/torch 及上述模块。
这不是全进程系统调用追踪；不把自行报告的零分解计数当追踪证书。

| 子进程组 | case（固定顺序，26项） | 预期 |
|---|---|---|
| 正常/宿主隔离 | normal_main, normal_thread, import_only | exit0，正常哨兵存在；绑定事件为空；首import不更换hook |
| 直接日志 | main_warning, main_error, background_warning, background_error | exit70，故障后哨兵不存在 |
| Thread异常 | thread_exception, thread_systemexit, thread_pythonwarning | exit70，SystemExit(0)也不能成为整体成功 |
| 吞异常/迟到 | swallowed_logging, late_failure | exit70；迟到例保留人工completion但无后续哨兵 |
| 取证/格式化 | write_failure, short_write, hostile_message | exit70；不依赖写入成功，不调用敌意__str__ |
| 旧处理器/锁 | old_raise_handler, locked_handler | exit70；不执行旧handler或等待其默认锁 |
| 身份/状态丢失 | factory_lost, hook_lost, inactive_guard, exit_rebound | exit70，不重装；真实退出闭包不受os._exit全局重绑影响 |
| 竞争/阻塞 | blocked_evidence, simultaneous | exit70；fatal latch先于写入，空文件不等于无故障 |
| 安装/导入阶段 | early_import_warning, unsupported_factory, unsupported_hook | exit70，不猜测或绑定未知输出目录 |

子进程真实调用 os._exit，不 mock 退出。负控均被父进程预登记为 exit70；
它们不是字体日志豁免，也不是允许父脚本忽略新警告。子进程 stdout 必须空，
stderr 只能空或 G01 fatal 原始事件行；其他 traceback/警告即非预期失败。
每项还查本次临时目录中的通过/handler/格式化/恢复/晚到标记，不触碰归档。

两类源码静态断言在未来该命令中才运行（本轮连 AST parse 也不执行）：

1. producer bootstrap 位于 NumPy/SciPy 之前，Budget/draw有guard调用，main记guard元数据。
2. 与上述 Git 基线作 AST/字节比对：producer数值/算子/人工生成/真实加载函数和
   Factors原样，Budget仅多guard调用、原clock/60不变；verifier除main外函数
   原样；原65测试与参考算术文件字节不变。这些静态断言不执行数值代码。

AST断言是结构检查，不是所有控制流已实际接通的证明；CLI时序与guard_point
调用点仍须独立人工代码审查，后续即使人工包通过也不等于原尺寸或真实DIC通过。

## 读写、预算与停止

- 仅读本仓库7个源码、Git源码基线/身份和本次新建临时人工哨兵/事件文本。
  父脚本临时目录用 TemporaryDirectory 创建并解析为真实绝对路径；只清理
  自己创建的该临时目录。无local_archive、真实数组/report/留出读取或新图。
- CPU线程环境六类均1、CUDA空、-W error/-B；测试有意创建Python工作线程
  验证跨线程保护，不等于启用多线程数值库。无SciPy/NumPy、实际QR0/SVD0。
- 父脚本首个time导入后开始整个包60秒软预算，含其余导入/源码身份/26子进程/
  临时文件清理/最终身份和stdout后检查。单个子进程timeout=min(3秒,剩余整包预算)，
  Git调用有min(5秒,剩余预算)上限，不增加整体预算。实际可行性尚未测量。
- 子进程超时由 subprocess.run 终止并等待它自己创建的那个子进程，随后
  作为首个非预期失败退出父包，不重试或继续下一例，不kill其他进程。
  临时取证清理/系统调用可能超时，仍不声称60秒硬杀整个父进程。
- 首个非预期断言/异常/警告/预算或源码身份变化立即停，不自动修补重跑。
  启动/结束HEAD与7源码SHA必须一致，后继仅docs且clean。

## 后续授权边界

本轮只准备/静态审查；通过后展示唯一G01人工测试命令供用户批准。
不附带原65项回归、B002/B003、资源检查或C/D命令；若后续需要另列包再批。
producer仍保留原B002固定路径，现有目录已隔离且不可重用；本轮不通过换
目录悄悄恢复资源运行。任何未来新Run路径须另冻结、审查和获得执行授权。
