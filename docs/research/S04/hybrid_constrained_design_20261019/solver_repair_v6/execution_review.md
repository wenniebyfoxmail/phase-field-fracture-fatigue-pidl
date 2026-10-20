# 当前冻结包：2026-10-20，含缺测费用控制预留

独立最终结论 **PREPARATION_ONLY**；以下旧1181记录保留作沿革，当前准确身份为：

- 源提交 `4ca8d56df129b11c7a4e3c03534cfab3af05a4dd`，98个文件均与提交逐字节一致。
- artifact `605443be64260f0fdcf6d9f454f605551dd73075b698702190191b30d9eae55b`。
- card SHA `321f36ba8a17da667ab35f01f69932ef1b4e75d0c5c59a19a372a9a055ba85d8`。
- manifest SHA `d4945ad6690858f369a67a843f927be7f4ca63e7f07a13ac8ed4e18760ec47d8`。
- budget receipt SHA `e8515061fa412363609666730de7a2ed6c044b4d3353f3aa95c513a964f7dcb4`。

旧缺测控制预算条件已闭合：card与receipt都绑定600秒预留；外层GNU timeout确实再扣600秒，legacy默认0；拒绝负值/NaN/inf/bool/字符串。实际费用仍809.8447466738289秒，预留没有伪装成actual；可用保守余额135.60837645925727hosth。独立预算差量3项定向测试通过0.57秒；最终主执行者143项人工回归通过3.62秒。数值/历史核心沿用已通过复核。

独立审核者最终只读复核98文件snapshot/hash/git show与卡/receipt/预算一致性；card false、receipt complete=false，disabled guard实际拒绝spawn。最终外层期限488100.1552533262秒，再扣launcher实际耗时；后续真实stage耗时仍需加入。没有远端、数组读取或科学重跑。剩余：具体stage动作人方确认、实际stage/cost、最终启用卡/审核/提交bundle绑定。不能把此结论改写为REVIEW_PASS启动。

---

# v6准确本地准备包独立复核

结论：**PREPARATION_REVIEW_PASS_ONLY**，不是启动通过。独立审核者 `/root/hybrid_readiness_review`，2026-10-20；只读核验，没有SSH、数组解码或文件修改。

98个源文件既与快照逐字节核验，也与`git show 1181c979dcf8a4035a643e2d6aa803e9b58f734a:<file>`逐一一致。

| 身份 | 值 |
|---|---|
| artifact | `67cced2c9611e309b20f084f3fcda046ed6c93fb48b89661811d22dcdfa5d2d0` |
| source_manifest SHA | `794dff2e148c8ff8101552d01099c82647b7a66b2e4638dc478df4f78e0ac0d6` |
| 禁用card SHA | `b7f6dfd198d7a444851e495c86222eab5b3babb4452b0f289b6ce520cade9ce7` |
| budget receipt SHA | `74dd605299567a12e9aeda3b65cd765595f18a15be2b6b9168f8462ac32051d2` |

物理阈值、D13历史合同、三臂、phase、training与判据均不变；300秒工程保护及策略明确版本化。旧尝试保留，新一次3600步权限有用户原话。代码发现三项已关闭：动态deadline reason；未观测pivot用None；cache domain回退断言。主执行者142项人工回归通过3.70秒；独立26项聚焦复跑通过0.75秒。

累计生产/先前研究费用797.0785519238561秒，加已测dispatch/query控制工作12.766194749972783秒，总809.8447466738289秒，一个prior entry计入且没有重复展开旧R1/validation费用。CPU已观测833.547614秒、GPU0、numerical497.477721337229秒、fit0。部分控制CPU和3次旧monitor墙钟为缺测；已知余额135.77504312592393hosth只是基于现有读数的余额，不是完整精确的实际可用时间。最终启用前必须对缺测明确保守预留并在原136h内真正执行扣减，或补回可验证实际读数；不得只改complete=true、填假零或把预留伪装为实际消耗。该控制条件与stage实际成本均尚未完成，不允许启动。

卡false、reconciliation.complete=false；准入函数实际在spawn前拒绝该卡。准备脚本仅本地JSON/字节操作，没有enable选项。具体远端动作仍受自动审批拦截：标准库脚本目标原GPUServer8，R2→R3输入/OSQP同机复制；技术审查不替代或解除该拦截。

下一项：用户确认已展示具体动作后，一次stage；加入真实成本和缺测保守控制，完成准确启用卡/包的独立绑定复核再提交一次完整比较。不能把此准备结论写为`REVIEW_PASS`用于receiver启动。

本审核记录与packet_check只记录独立结论，不进入已审核源manifest，避免自引用与追溯改写。科学源码未因本记录变化。
