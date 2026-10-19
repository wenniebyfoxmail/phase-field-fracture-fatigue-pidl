# S09-E013 implementation review v1 (ChatGPT Pro, Haofan)

- Reviewed commit: `a79f11d6a1c1f58e89c7a34882e2673171f90f26`
- Conversation: https://chatgpt.com/c/6ad49578-9328-832b-b4ee-bfe121ff38eb
- Account: Haofan
- Verdict: `REVISE_AND_REREVIEW`

## Review transcript

REVISE_AND_REREVIEW

本轮结论针对你声明的 exact candidate a79f11d6a1c1f58e89c7a34882e2673171f90f26。在 E013 新增范围内，我确认了 3 个 blocker：零步准入没有完整落实冻结前置条件、新 local primary 未与保存的 checkpoint 闭合，以及新增计算循环在 deadline 后仍继续启动工作。

局部 observable/loss 的公式、truth-mask 的使用位置、G25 的合并算术及整数分类阈值，没有发现新增数值错误。 以下问题集中在准入和证据闭合；不重开已关闭的 E009–E012 generic producer/core。

独立检查范围与身份边界

本次审核依据你贴出的 protocol、core、producer 和五个 E013 tests。我独立执行了抽取函数的数值与状态机检查：

所贴协议文本还原后的 SHA256 为
2352330a7fd92d61c51feb5932b4a91a125e5e48f0ff763d6ec206c0e2a619ab，与 producer 中的 EXPECTED_PROTOCOL_SHA256 一致。
使用函数 AST、NumPy 数值替身、固定解析 Jacobians、模拟时钟，以及已归档的 exposed-development 场数组检查下述反例。
本环境没有 PyTorch/pytest，因此没有独立重跑提交方的 23 tests，也没有执行真实模型 forward/autograd、optimizer step 或 producer。
ZIP、manifest、Git commit object 的字节身份未复现；本轮没有可供核验的 Git checkout。run_config.json 和入口脚本也未包含在贴出的材料中，其实际字节和 CLI 连接未独立检查。

ZIP 缺失不是本次阻断原因。下面三项均有源码和可执行反例支持。

R1 — 高：零步 admission 缺少 all-eight usability 与独立的 17-pair 保护集合检查

文件 / 函数：
source/s09_e013_producer.py :: zero_step_audit()

协议要求八个初始错误 local pairs 全部 usable、finite，并保护原来的 17 个正确 global pairs。当前 gate 实际检查的是：

Python
len(wrong) == 8
and wrong_positive[ARM_LOCAL] >= 1
and wrong_positive[ARM_LOCAL] > wrong_positive[ARM_GLOBAL]
and correct_flips <= 3
and all(math.isfinite(value) for value in wrong_rank + wrong_control)

这里没有 local contrast usability 检查，也没有：

Python
len(correct_global) == 17
反例 A：六个错误 local contrasts 完全为零，仍然 READY

我用每个 cycle 一份一致的 Jacobian构造反例，避免任意指定互不相容的 pair gradients：

𝐽
58
𝑙
𝑜
𝑐
𝑎
𝑙
=
𝐽
60
𝑙
𝑜
𝑐
𝑎
𝑙
=
𝐽
69
𝑙
𝑜
𝑐
𝑎
𝑙
=
𝐽
3
𝑙
𝑜
𝑐
𝑎
𝑙
=
𝐽
4
𝑙
𝑜
𝑐
𝑎
𝑙
=
(
1
,
0
)
,
𝐽
70
𝑙
𝑜
𝑐
𝑎
𝑙
=
(
1
,
1
)
.
J
58
local
	​

=J
60
local
	​

=J
69
local
	​

=J
3
local
	​

=J
4
local
	​

=(1,0),J
70
local
	​

=(1,1).

令八个初始错误 pairs 为：

{
58
,
60
,
69
,
70
}
×
{
3
,
4
}
.
{58,60,69,70}×{3,4}.

于是其中六个 pair 的 local contrast gradient 严格为零：

58>3、58>4、60>3、60>4、69>3、69>4。

所有 cycle Jacobians 本身均有限且非零。使用当前 merger、ranking chain coefficient、single clip 和 _adamw_displacement()，得到：

字段	独立复现结果
初始错误 local pairs	8
其中严格零 local contrast 的 pairs	6
L25 改善的错误 local margins	2
G25 改善的错误 local margins	0
初始正确 global pairs	17
L25 导致的正确 global crossings	3
Model / AdamW state 是否改变	否
当前 admission	ZERO_STEP_DIRECTION_READY

Expected： 八个错误 local pairs 全部 usable 的前置条件未成立，应 STOP。
Observed： 六个错误 pair 没有一阶 local sensitivity，仍然 admission。

“改善了两个 pair”的 directional tier 不能替代“八个 pair 均 usable”的前置条件。

反例 B：保护集合只有 12 对，仍然 READY

第二个 fixture 把八个错误 local contrasts 都改为非零；其最小相对 contrast 为约 0.63246。只改变 global margin 的符号集合，使当前正确 global pairs 为 12，同时保持：

local wrong count = 8；
L25 helpful = 2，G25 helpful = 0；
correct-global crossings = 3；
全部相关数值有限。

当前函数仍返回 ZERO_STEP_DIRECTION_READY。

Expected： 冻结的 17-pair global 保护集合身份不成立，应 STOP。
Observed： 代码只检查这个缩小后的集合中 crossings 不超过三。

这也是 E013 分开使用 local admission observable 与 global protection observable 后需要显式补上的检查：local wrong count=8 已不能推出 global correct count=17。

最小修复：

显式记录并验证协议中的 local-pair usability 条件，再计算 helpful tier；本次审核不替你新增或调整数值阈值。
显式要求 global protected cohort 为冻结的 17 对。
增加上述两个独立回归：six-zero/two-helpful，以及 all-local-usable/global-correct-count=12。
R2 — 高：local primary 可与保存的 checkpoint 和最终场数组矛盾，completion 仍成功

文件 / 函数：
source/s09_e013_producer.py :: _write_evidence()、_local_support_metrics()、_write_required_figures()

当前顺序是：

验证磁盘 arm receipts、logs、global evaluations 和 checkpoint。
从 live runtime models 计算新的 local support metrics。
进行分类并写出 decision_metrics.json。
随后 _write_required_figures() 才重新加载 update-500 checkpoints。
重建检查只核对 global weighted mean absolute increment，没有核对新 local score、local AUC 或 primary delta。

全场平均幅值相同，并不意味着 support-minus-background contrast 相同。

最小反例与完整 writer 复现

反例只改变 receipt 关闭后的 L25 内存预测场，保持磁盘 receipts、logs、hashes 和 checkpoint 不变：

将 growth cycles 的正增量重新分配到 target support；
将 stagnant cycles 的正增量重新分配到 background；
保持每周期全场 weighted |Δd| 不变；
保持 d_pre <= predicted_peak <= 1。

我用已归档场数组构造这个故障注入 fixture，并执行了当前 writer、磁盘验证函数、原 E010 evaluation validator、local observable、classifier，以及 checkpoint field reload / NPZ 写入路径。模型 forward、checkpoint 解码和绘图后端使用替身。

结果如下：

项目	保存的 checkpoint / 最终 NPZ	writer 采用的 live metrics
G25 local counts	14W / 0T / 11L	14W / 0T / 11L
L25 local counts	14W / 0T / 11L	25W / 0T / 0L
G25 local pair score	28	28
L25 local pair score	28	50
Primary delta	0	22
四项 protected ratios	1.0	1.0

每周期 global amplitude 的最大变化仅为 2.168404344971009e-19，因此已有 global-amplitude reconstruction check 全部通过。

Expected： 拒绝 local primary 与保存端点不一致的证据，或直接从重载端点计算判决。
Observed：

纯文本
execution_status = SUCCEEDED
scientific_status = LOCALISED_OBJECTIVE_SIGNAL
tier = ROBUST_LOCAL_OBJECTIVE_REPAIR
reported delta_pair_score = 22
checkpoint/NPZ delta_pair_score = 0

这是证据闭合的反例，不是 E013 实际运行结果。它说明新增 primary 的计算来源没有被当前 endpoint 验证覆盖。

最小修复：

先重载经过验证的 update-500 checkpoints，再从同一份重建场数组计算 local support means、background means、25 个 pair counts 和分类。随后写 decision 与 figures。若保留 live-runtime 计算，应逐周期验证它与保存端点的 local observable 一致，不能只验证 global amplitude。

增加“global amplitude 保持不变、local distribution 改变”的回归即可覆盖这个缺口，无需修改 loss 或 criteria。

R3 — 中：新增 audit / local-metric 循环会在 wall deadline 后继续启动计算

文件 / 函数：
source/s09_e013_producer.py :: zero_step_audit()、_local_support_metrics() 及其调用位置。

这两个 helper 都没有收到 deadline。外层检查只能在整个循环结束后发现超时。

模拟时钟最小复现

设冻结 deadline 为 3600 s，阶段开始于 3599 s，每个独立 collection fixture 消耗 2 s：

新增路径	第一次工作结束	到期后仍启动的工作	最终到达的位置
zero_step_audit()，25 pairs × 2 arms	3601 s	49 次 pair/arm collection	3699 s 先写 READY audit，随后外层才抛超时
两臂 _local_support_metrics()，各 16 cycles	3601 s	31 次 cycle collection	3663 s 才到 classifier 入口

Expected： 当前独立工作返回后检测超时，停止启动下一个 arm/pair/cycle 的 forward 或 gradient collection。
Observed： 两个循环都会继续完成剩余独立工作。

现有外层检查最终会阻止继续训练，已有 pre-step deadline guard 也仍在；这个反例没有发生 deadline 后的 optimizer step。阻断点是新增计算阶段不满足墙时上限及及时停止要求。

最小修复：

把同一个绝对 deadline 传入新增 helper，在每个独立 pair/arm collection、cycle forward 前后检查。超时后保留已完成的诊断进度并进入失败收尾；READY admission 的发布应在有效的 deadline 检查之后。

已确认正确的新增连接
审核项	独立检查结论
Local observable	与冻结公式一致：truth Δd > 1e-15 mask；对正预测增量分别计算 support/background 加权均值后相减。
Ranking chain rule	D、temperature、margin 与 softplus 连接一致；对八个 field entries 的独立有限差分检查，最大相对误差约 9.90e-11。
Truth-mask boundary	mask 在取得模型输出后进入 loss 和 exposed-development 指标计算；未发现作为 operator input、conditioning channel 或 output correction 的新增路径。
G25 merge replay	对 64 套相同 flattened gradients、两臂共 128 次算术比较，与已审 E011 ranking-arm merge 的最大逐元素差为 0。包括零 rank、同向、反向、低于 epsilon 和零 amplitude-gradient 情形。
Projection / coefficient / clip	两臂均使用冻结的 4096*q_R、beta=.25，每个完整方向一次 global clip。
Pair compute matching	_pair_objectives() 两臂均做两次 atomic-loss/forward，均计算 global/local observables；六个 pair-mean base objectives 相同，只有选入 L_R 的 scalar 不同。
Budget / schedule	25 个固定顺序 pairs 重复 20 次，每臂 500；七个 evaluation points 与总上限 1000 保持。
Scalar classification	2W+T 的 primary gain≥2、robust gain≥4 加四项 ratio≤1.10 实现符合协议。四项 ratio 的精确边界及其下一可表示浮点值检查通过。
优化路径	新 core 没有 optimizer/I/O 路径；audit 使用解析 saved-state displacement；训练仍通过既有单次 step 入口。未发现新增隐藏 step 路径。

这些数值比较使用抽取函数和 NumPy 替身，不等同于 GPU 上完整的 E011/G25 500-update replay。

Optional improvement

e011_decision 当前只被核对 SHA256，没有被解析成数值 replay comparison。建议在结果证据中明确区分“reference 身份已绑定”和“执行轨迹或端点已比较”。

所贴协议没有冻结额外 replay gate 的字段及容差，而 G25 的合并连接检查已经通过，所以我不把这一点列为第四个 blocker。

本次需要修复的是 R1 admission、R2 local-primary checkpoint closure、R3 新增循环 deadline，并补充对应的 no-training 回归。修复前，本轮不授予该 E013 producer 执行许可。
