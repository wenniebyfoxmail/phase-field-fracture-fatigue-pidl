# D21 下一次执行审批内容

当前仅准备，不代表许可或已提交。科学源 `fee87bac`，完整commit及38文件SHA见[source_manifest.json](source_manifest.json)。准确禁用[execution_card.json](execution_card.json)、[实现方案](plan.md)、[检查记录](checks.json)与[独立模板代码复核](execution_review.json)共同定义本版。

**收件／执行对象：** SSH账号`drtao@172.16.100.2`，需实际hostname为`GPUServer8`；不使用新服务器。原R008不恢复。

**待批准的文件与动作：**

1. 一次只读准入：发送并执行当前 `tools/preflight_hybrid_cpu_v12.py`（源码在38文件manifest中），核对原R3输入／公共OSQP文件、原自有失败运行终态、新目录不存在及CPU/RAM/磁盘；不导入科学模型／读项目场数组／查询GPU。
2. 仅准入通过后，发送当前 `tools/receive_hybrid_cpu_v12.py`及小型源码控制包。包内容为source_manifest所列38文件（包括求解器和reviewed worker/guardian/supervisor）、准确卡、源manifest、独立review；上限压缩2MiB／展开4MiB。完整逐文件内容可从manifest对应仓库路径审阅；**没有私有输入或FEM数组附件**。只在服务器内部将原R3的98个公共OSQP文件980049B复制至新目录，R3 inputs只读使用，不修改旧运行。
3. 新目录 `/mnt/data2/drtao/wennie/pf_hybrid_solver_v12_20261021_r9` 与归档 `/mnt/data2/drtao/pidl_archives/pf_hybrid_solver_v12_20261021_r9`。调用reviewed `run_hybrid_cpu_v12_budgeted.py --launch`，完成runtime版本／原输入／源绑定及resource准入后，最多启动一次脱离SSH的原train_A600轨迹。每case保留elapsed；首个科学／资源／身份／IO失败停，不自动重试／resume。其他case、训练与GPU均不在本次。
4. 在同总包内只读监测、终态进程身份确认、全部已落盘文件取回size/SHA核验、保存结果分析／图／既定独审／Obsidian／费用收尾。缺项或超限如实PARTIAL，不为补齐而重跑。

**预算与承诺：** 新提案4墙钟小时、4CPU／0GPU（最多16分配core小时），RSS和AS进程树32GiB，输出remote8GiB+localreturn8GiB共16GiB。至少30分钟预留完整取回与收尾，45秒终止余量，最多2次机械动作合计120秒。原单步300秒／100fresh／8outer／每outer100charged actions与16updates不变。成功不保证：小矩阵工程检查不能预测原FEM收敛和600步可负担性。

**时间边界：** 总包保守从本次准备首次核查`2026-10-21 10:44:03 UTC`计，含准备／等待批准；硬截止`14:44:03 UTC`（英国15:44:03）。过期即park，不能用同卡自动换起点。旧已知／保守成本19079.395674秒及新准备实记照保留，不重置旧预算、CPU未知项不填零。

**批准后唯一允许的卡变化：** `execution_enabled=false→true`；`execution_authority=null→{kind:direct_user_approval, proposal_id:FEM-BOX-KRYLOV-D21-20261021, message_id:本次真实批准消息ID, approved_text:该消息原文}`。规范化template ID只排除这两项，源／模型／容差／数据／预算／时钟／目录等均保持所审版本；实际启用卡SHA及传输包SHA在发送前机械绑定记录。此次批准若未覆盖这些动作，则保持禁用。任何其他内容变化须重新审查／审批，不借元数据修订扩预算或重试。
