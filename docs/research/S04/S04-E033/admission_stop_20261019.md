# E033 资源首停收尾 — 2026-10-19

状态：`ADMISSION_STOPPED_NO_LAUNCH_NO_RETRY`；本 Run 停止。科学诊断未执行，结论 `inconclusive_not_evaluated`。

- 2026-10-19 00:06:50 London（2026-10-18 23:06:50 UTC），GPU5 UUID 符合，但空闲 **18314 MiB < 20480 MiB**，利用率 **87% ≠ 0%**。唯一启动调用在远端 stdin 第12行资源断言停止，早于 exclusive `launch_attempt.json` 创建和 `Popen`。原 traceback 已保留。
- 首停时占用 PID3949516 的 cwd/argv 属于 S09-E011 ranking；没有干预或终止该进程。00:16:55 London 只读复核时该历史 PID 已不存在；这不代表整个 S09 已结束，也不改变本 Run 首停状态。
- 复核：远端 `launch_attempt.json`、`launch_receipt.json`、`worker.log`、archive/output 均不存在；归档根为空。扫描 `/proc` 的 exact run paths / E033 runner 无匹配进程，无读取错误。没有待回收的本次 worker。
- 本次模型加载、梯度行、proxy迭代、候选评价、接受头更新、optimizer/history/FEM计数均 **0**；新增GPU小时 **0**。六个既有运行累计 **1.0917761951371787 GPU小时**，最新科学结果仍为 E032。
- 本地/远端 grant 1167 bytes，SHA256 `ebc017b2d6ab22ecb3ef7c98ce28e8c6cc9230392ebfd497499131c4f25297fd`，逐字节相同；`execution_authorized=true` 保留为原始历史授权，不构成首停后重发许可。源码 clean exact `30ba0572b691b97e9ce272280627bd8bd52f86b4`。
- 启动互斥设计为 `launch_attempt.json` 的 exclusive x-create；资源断言先失败，因此该标记未取得、未留下资源预留。已有 `admission_stop.json` 是停止回执，不是GPU reservation或新增自动执行锁；未改 launcher/grant/远端任何文件。

已取回并按 bytes/SHA 核验：grant、staging_verified、admission_stop；停止回执SHA256 `33b71fc159c2c89b69dadf569b552b9e2f2d446afc0496dd3c3f1f009c50d992`。原启动 stderr/stdout、launcher、bundle、焦点审查、完整只读复核与清单均在本地Case，见 `run_summary.json`。

这是共享资源条件未通过；没有测量完整802维方向，也没有评价单轴校正。不能解释为无共同下降方向、UV头容量不足、优化器或权重失败。只读收尾已结束，不重发、不换卡、不改阈值、不用新编号绕过、不追加实验或审查。后续资源安排由HQ另作决定。
