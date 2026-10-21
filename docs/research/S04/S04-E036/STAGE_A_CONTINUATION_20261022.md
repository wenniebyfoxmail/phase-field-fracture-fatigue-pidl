# S04-E036 阶段 A 同范围续接 · 2026-10-22（伦敦）

**结论：隔离快照修复成功；第一次实际启动包装失败，仍未进入 MATLAB/MEX/FEM。** 原110项实现检查与35项比较器检查保持原证据范围。本次没有新的科学数值结果。

目的仍是D2：先验证原生同状态实现一致性，再决定是否进入阶段B。此次依据原直接人方阶段A授权和HQ前瞻机械修复准入包，在原3小时余量内续接；没有重新开始3小时或20分钟时钟。HQ包为`local_archive/research_hq/portfolio_takeover_20261021_evening/timing_stage_a_preflight_repair_authority_20261021T2346Z.json`。其中只允许一次≤300秒修正快照，首个控制启动/IO故障后停止，不再次修复重启。原`authority.json`、首次快照失败、20分钟停止与`analysis/closure.json`全部保留。

## 实际覆盖

| 环节 | 结果 |
|---|---|
| 零进程/自有空目录检查 | 通过后才复制；没有重复科学worker |
| 正确git archive参数 | 一次成功；producer复制及记录8.493秒，SSH包装10.825秒 |
| 原生源 | `862992a60edc7f59335365beacb5c71fc8592a7a`、clean；独立snapshot，不修改共享checkout |
| 保存输入 | 共同U0、mesh及4组s3/s4，共10文件SHA全匹配此前盘点 |
| 代码包 | commit `962f7340120f9deff9c924c0a56675448dc9cd07` 的36文件在producer展开并逐项核验；115366 bytes |
| MATLAB准备driver | 单独加入SHA manifest/config/entry，计划仅checkcode→28 mock→fresh build |
| 启动包装 | WMI返回0，创建wrapper PID42620；这不是MATLAB启动成功证明 |
| watchdog / MATLAB / build | 没有attempt/start/finish/wrapper日志；MATLAB输出为空、build目录不存在 |
| U0、disabled、四组真实冻结场、checkpoint实测 | 全部未执行；没有新recovery、NN或阶段B |

共同输入复制发生在原任务独立根`C:\Users\xw436\jobs\E036_A_20261021_2142`。初始MEX只作为明确标记的既有文件复制；两个审计核心仍要求fresh build的源到二进制来源证明。没有因为构建未开始而降级使用旧MEX推进。

## 启动失败的证据与不确定性

- 23:48:07Z（伦敦00:48:07）WMI记录`ReturnValue=0`、wrapper42620。
- 23:48:59Z未观察到MATLAB/ifx/link进程，也没有watchdog或MATLAB日志。
- 23:49:48Z wrapper已不存在；任务日志只有`prepare_01_launch.json`，未出现attempt/start/finish。
- 23:51:52Z只读诊断：有效PowerShell策略为 **Restricted**；脚本文本解析错误列表为空；watchdog SHA为`ef4e2e1c123398984d8b23edfecb671179353703ef2f5daf066b9d4f66d893ea`，与已审源码相同；wrapper及子进程、原生进程均空，output空，build目录不存在。

启动命令使用`-NoProfile -EncodedCommand`，内部再调用`.ps1`，未预检该脚本入口与执行策略的兼容性。此静态缺陷和现场Restricted策略支持“脚本入口被阻断”的解释；**该PID实际退出码/异常文本未留存，不能声称直接捕获了具体异常**。启动器只在内部流水线下游用Out-File，没有PowerShell进程级stdout/stderr捕获，因而丢失了早期失败诊断。UTF-16LE Base64往返、路径、引号和重定向未发现静态问题。

watchdog必须先持久化attempt，才创建MATLAB；无attempt且无任何输出/存活进程，与未进入计算路径一致。没有把WMI成功回执当作软件检查或求解通过。按照本次明确的首次控制故障停止条件，未更改执行策略、未修改全局MEX、未安装软件、未重发或改用其他producer。

## 预算与保留

原窗口仍为2026-10-21 21:42:35Z至2026-10-22 00:42:35Z（伦敦01:42:35截止）；原4CPU/串行原生、5GiB新输出/free10GiB不变。展开代码时C盘可用64467374080 bytes。机械复制和各SSH包装的实测时长分别保留；首次wrapper实际CPU、退出码未知。全局等待间隔不是CPU使用量。没有新的MATLAB、MEX编译、FEM或训练计算证据。

本地case仍为`local_archive/experiments/S04-E036/stage_a_20261021_2142`：

- `analysis/continuation_01_authority.json`、`continuation_01_snapshot_verified.json`、`continuation_01_result.json`：本次前瞻范围、10文件核验和最终覆盖。
- `logs/stage_snapshot_continuation_01.json`、`expand_verify_code.json`、`launch_prepare_01.json`、`inspect_prepare_01_a.json`、`inspect_wrapper_42620.json`、`diagnose_control_stop.json`：原始调用与观察。
- `raw_archive/continuation_01/`：取回的producer原始快照、代码展开、启动请求和包manifest。
- `run_workspace/`：准确传输包、manifest、config、entry和启动脚本。首次失败文件及上次closure没有改写。

两个新driver只作为准备源码保存；prepare driver已部署但没有执行证据，native driver未部署。原80文件锁仍指向962f7340的历史版本；本次driver与payload身份单列`stage_a_continuation_lock.json`。

下一具体缺项是可靠的PowerShell进程级错误捕获、脚本执行策略的明确兼容处理，以及一次有可观察退出状态的受限启动。只有这些完成并在有效执行范围内，才继续原28 mock/构建/U0/两个控制/四个冻结态；不扩大状态、阈值、producer或训练范围。[原owner](experiment.md) · [前次停止记录](STAGE_A_RESULT_20261022.md)。
