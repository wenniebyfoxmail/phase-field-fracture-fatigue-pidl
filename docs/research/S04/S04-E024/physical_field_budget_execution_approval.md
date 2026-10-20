> **2026-10-20 当前状态：Mac v1因生产机角色未闭合而暂停。以下v1原文仅作历史保留，不要执行。当前以[生产机角色修订卡r2](physical_field_budget_execution_approval_r2.md)为准；原字节副本在machine_role_alignment/v1_original_physical_field_budget_execution_approval.md，v1 zip/manifest不变。**

# D013-offline-20261020-v1 最终执行审批

2026-10-20。**待批准；未运行。** 此次审批只涵盖下述本地CPU固定模型离线校正，不授权神经训练、SSH、传输、push、依赖安装、重试或新实验。Mac依旧不训练。

- 科学源码：`18d0e7cb1153dc969c1ee0c21c77ada1297b2d89`；科学树：`14f6ba5d4b0107e0655f711622ef51268222221e18666f65426bc11e42813c23`。
- 启动器独审：PACKAGE_READY_PASS，SHA256 `56825d5b72b49e2f6c3887ac251085e4e8df276baa7345f31d859950ade78e5f`；此前科学Code Ready保持有效。初审问题和修复记录保留。
- **最终manifest SHA256：`7c77c4db5448d64d8d9e3f647ce7210615df9506d276a7b86740d46ef866f91a`**。
- 可审批完整附件：[D013_offline_18d0e7cb_v1.zip](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_package_20261020_v1/D013_offline_18d0e7cb_v1.zip)，33784589 bytes；SHA256 `e6e11df3ef2e86676dcafa06a648a7d3a19e1253a07ee21781a7dffdcbdd91d1`。
- 源码tar SHA256：`4682bf96f178c4ca6dc9faf56a9f591cb687077e554240d77a997b818681d7b1`。
- 实际包目录：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_package_20261020_v1/D013-offline-20261020-v1`；88份既有输入只读，238,110,147 bytes，不复制进包。

## 具体操作与承诺

1. 在当前Mac用精确Python/依赖版本，只读统一核验包／科学源码／88输入／环境／最终收据／fresh目录与容量；不得把它称真实三态数值预检。
2. 三态c20s4→c60s4→c83s4，各自原E023 joint10000 seed7；每态三档strict η=.1/.3/1加中央档旧七消融，共12profiles。D、BC、窗口、features、damage/history/fatigue冻结；568头坐标、无2%参数球/ridge。13实际误差保护、累计预算中心和零分母规则见包内README／已审原契约，均不改变。
3. 获批后真实数值准入只在每态独立进程开始时执行。每profile≤3代理、每次≤9顺序有限步；最多36次代理求解/324实际候选，不重训旧对照，不新探holdout。所有实际评价从量化后raw重建场取得；后来状态失败会停止余下任务，已完成行保留为部分证据。
4. CPU2／0GPU；数值1800s、重放/汇总900s、绘图120s、检查总300s；总≤3120s，各阶段不互借。检查已记录66.937549s，最终绑定保守预记5s，当前预算记账71.937549s，启动时字节预检及另5s交接仍在300s里扣。RSS每进程3GiB、原2GiB loader不改。包／旧D013检查／控制／数值输出合计1GiB，由持续运行的启动器和原parent共同监督。保留3条NNLS警告及原Mac可移植性例外。
5. 无代理可行返回、solver异常或九步全拒绝只停该profile并保留最后合格头；身份、非有限、映射、资源或全局监督异常停止余下任务。不换solver/加预算/重试，只终止本任务自己的新进程组。目录领取后不复用；未知spawn先核验PID/日志，不能盲重发。
6. 科学parent完成后重放全部已访问头、完整T/谱/秩、实际13保护/Q/分支/停止；完整三态齐全后再输出48行分区比较表、成本及真实场图。没有新候选优化的独立重放。`.001`仅历史诊断；damage/crack/fatigue应用与history耦合仍未获资格。

## 获批后唯一命令（当前不要运行）

执行者只在收到本包明确批准后，另存`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_package_20261020_v1/authorization.json`：准确manifest SHA、批准原文、source/路径、scope和禁止项；当前该文件不存在，包内模板为false。该授权不是从Code Ready或本页推断出来。

```bash
nohup /Users/wenxiaofang/miniconda3/bin/python3 \
  /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_package_20261020_v1/D013-offline-20261020-v1/launch_d013.py \
  --authorization /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_package_20261020_v1/authorization.json \
  > /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_package_20261020_v1/dispatcher_stdout.log \
  2> /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_package_20261020_v1/dispatcher_stderr.log < /dev/null &
```

以上nohup只运行一次，启动器留在后台持续监督自己的science parent；其CONTROL/PID/argv/host/UTC/stdout/stderr用于核验，不把dispatch视为完成。结果根：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_execution_20261020_v1`；控制根：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_launch_20261020_v1`。两目录当前不存在。

你若批准这份v1，将授权这一次完整的只读离线数值校正、真实场重建和规定汇总／绘图，**不授权神经训练或其他实验**。本次暂停执行的依据是你本轮明确要求“把最终执行方案展示给我审批”；Code Ready不代替该次批准。

[包内完整算法／预检／保护说明](</Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_package_20261020_v1/D013-offline-20261020-v1/README.md>)。
