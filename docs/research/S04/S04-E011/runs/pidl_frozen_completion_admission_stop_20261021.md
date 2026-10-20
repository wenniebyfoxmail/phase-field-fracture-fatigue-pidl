# PIDL冻结分支补齐包：机械探测首停，未部署或计算

**目的：** 仅补齐c20s4两个冻结弹性分支控制臂，复用原生两臂，形成同状态2×2机制面板。原native R1的记录错误、27.862862科学／1368.323整包秒及更早112.405科学／1555.63整包、178.813saved-only墙钟和全部UNKNOWN保留。

**本轮结果：** 第一轮只读探测退出1，stderr为`/bin/bash: Argument list too long`，stdout0bytes。调用方按STOPPED_NO_RETRY_MECHANICAL1停止，未进入源码部署或bootstrap控制流，producer_started=false。没有新worker/PID、GPU准入、cache重建、AD、FEM/PIDL求解或frozen结果；当前服务器身份／GPU占用／缓存动态等价检查均未取得回执，不能假设GPU仍空闲或共同输入已经通过。

## 已准备什么，哪些没有执行

新前瞻包HQ-MESH-FROZEN-COMPLETION-20261020，只准缺失frozen_constant/frozen_zero；原生两臂不重算。源`7401442ff63e243459487f9160be004d92d5cf9b`，分支codex/hard5-q4-t3-2x2-20261005，准备时工作树干净；package SHA `e41bafe9caf2c5abdf940fa9ae0772250c80c80a2c8d839cd02d163f1f988e7a`。Run `pf_s04e011_frozen_completion_r1_hq_20261021`，指定目标GPUServer8／drtao@172.16.100.2／GPU5 UUID5622bd47-1050-3003-246d-3cabe2b4791b，本次未取得实时核验。没有第二次SSH、换host、等卡、清理目录、重新提交或干扰进程。

新路径已实现：仅frozen能量／矩阵、native调用硬拒；原h1e-6/seed173/同Phi/T0／原UV/B0/FEMd/PIDL历史与物理head1e-10／内部1e-13／原FD判据不变。至多三个位点重建，并要求派生Phi/qraw与旧缓存逐值相等；旧features本体未存，不声称features已经逐值证明。固定输入、方向、尺度、自由顺序、源trace、运行版本、算子哈希均为必须通过的运行准入，而不是静审通过就视作已经满足。

每个线性求解/逆列调用都有独占begin、H/factor/RHS、x/residual/end；finally索引完整／未完成调用，先前错误保真。唯一臂结果与allfinal一次写入保留。新增只扩原exclusive-writer生命周期单项夹具：两次正常调用与第二次中断的finally索引，1/1通过0.015秒；原8项不重跑。唯一原reviewer静审差量通过，未运行模型/数组/物理/SSH。上述均为准备证据，未获真实执行验证；不会补造旧R1缺失的中间日志。

## 本次输送缺陷与本地修复准备

我沿用了将整份card嵌入`python -c`命令的探测方式。加入371项旧cache/operator身份条目后，单个远端shell命令参数为**152395bytes**，触发参数长度错误，探测Python没有返回任何JSON。没有证据把它归为GPU忙、网络超时或物理解失败。

本地已准备[标准输入修复差量](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-native-mesh-pidl-20260929/docs/research/S04/S04-E011/frozen_completion_20261021/transport_repair/probe_stdin.patch)：远端`json.load(sys.stdin)`，调用方`input=json.dumps(card)`。相同149872bytes JSON元数据通过stdin传递，`-c`参数缩为2525bytes；不删身份条目、不改变数据/接收目标/数学。仅做AST和字节长度检查，未执行新SSH/部署/科学尝试，原失败脚本／包／收据不变，没有新RunID或重试授权。详见[离线长度记录](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-native-mesh-pidl-20260929/docs/research/S04/S04-E011/frozen_completion_20261021/transport_repair/offline_size_check.json)。

输送修复已完成[独立静态复核](../frozen_completion_20261021/transport_repair/static_review.json)，未进行远端验证。

下次若获准确新前瞻授权，应采用该输送修复后重新执行实时只读准入；不得把本次未核GPU、未核动态cache当已通过。之后仍只补两个frozen臂并与不可变native原量合并。当前首停规则明确不准自动第二次，因此这里不继续连接或运行。

## 成本、位置与科学结论

新整包预算1800墙钟秒，2026-10-21英国时间00:34:26开始、01:04:26截止；科学硬300秒、Q≤2/JVP/VJP≤8、field+frozenK≤250/dense≤30/SVD0。实际仅本地准备和机械第1批；新producer科学调用、GPU计算、Q/JVP/VJP/field/K/dense/SVD均**0**，依据是部署／bootstrap从未请求。机械准确耗时、整包CPU、全部读盘bytes及货币费用没有逐项计量，保留UNKNOWN不填零；整包墙钟收口见下方记录。不能把本地准备时间写成GPU运行时间。

本地case [执行收据](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_frozen_completion_r1_hq_20261021/execution_receipt.json)；[stderr](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_frozen_completion_r1_hq_20261021/logs/probe.stderr)、[stdout](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_frozen_completion_r1_hq_20261021/logs/probe.stdout)；准入失败记录和修复差量都在[owner](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-native-mesh-pidl-20260929/docs/research/S04/S04-E011/frozen_completion_20261021/transport_repair)。本次无远端新输出可取回，也没有新场图；继续引用已核旧native两臂图，避免画空数据。原native两臂失配同约7.233倍门，只削弱单纯源重锚解释；frozen两臂仍缺失，完整前向界仍不足，因此分支／共有数值机制仍未区分，FEM与PIDL基准没有改变，未恢复优化。
