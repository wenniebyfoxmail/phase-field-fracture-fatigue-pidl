# 当前B owner入口：治理前瞻修订（2026-10-20）

**当前无活跃科学执行卡。** BRIDGE-PS六臂比较已完成并复用探索结果；C27-A25旧15组及四组补齐的首停链保留，未恢复；下一科学方向是已有SCB方案内的加载匹配/独立裂长参考，仍属方案准备。下方2026-10-19运行卡及2026-10-20复用记录是历史证据，不是当前启动命令。此处为唯一当前入口，不新造执行卡或禁用模板。

## 已采用：一次有边界授权，机械工作自动完成

规则来源：安装版 [research-decision-core — Bounded Task Authority](/Users/wenxiaofang/.codex/skills/research-decision-core/SKILL.md:158)、[agent_bootstrap 2026-10-20更新](/Users/wenxiaofang/.codex/skills/research-decision-core/references/agent_bootstrap.md:36)及 [research-review-channels](/Users/wenxiaofang/.codex/skills/research-review-channels/SKILL.md)。本修订只承接往后仍有效的有界任务授权，不修改已签名源码/包、历史回执、已消费authority或旧失败。

- 已获授权包络内，实现、同范围修复、相关测试、已选独立只读Codex通道的必要聚焦复审、部署准备、版本/环境/资源核对、命令/RunID/路径/哈希及回执补齐，由Agent连续完成。条件式“检查实现和运行包，确认无误后启动”不拆成实现后、复审后、版本已知后、包已落地后四次批准。
- 纯身份/元数据实例化和辅助库版本记录只做自动一致性检查，不重启Code Ready；不变科学/控制部分复用既有审阅。改变数值语义、数据解释或执行安全风险时，对实际改变作必要复核，不另把已选通道再次交用户选择。共享/系统环境操作仍遵守原机器权限，不包装为普通依赖修复。
- 取消本owner曾增加的“每个新commit/精确哈希/命令/RunID/路径须人方再签”“同范围机械修复完成还须单独批准部署”“元数据变化需全量复审”等通用行政门。旧实例中对应文字保持历史原貌，不能由此推定用户逐字规定了这些门。

## 人方边界、旧条款来源与机械重查上限

原直接人方四组指令为“准备仅补剩余四组的续算方案，检查实现和运行包，确认没问题后启动运算，结果更新到Obsidian”；原话给出任务范围和条件式执行，并未逐字要求每次哈希/版本/RunID再批准。旧R003实例的max_attempts=1、精确包绑定及首停实现来自当时冻结执行合同；保留其已消费/停止事实，**不将Agent填写的字段扩写成用户对所有未来机械修复的普遍禁令**，也不以本治理消息撤销旧停止或再次消费旧authority。用户明确规定的连接/尝试上限和科学停止/科学重试限制继续有效；来源不明时标注不明，不冒称人方原话。

未来确有执行授权、需要实例化新卡时，在首次尝试前记一份任务包络：原目标、允许的数据与实现变化、producer、**总**预算、科学判据、停止/重试限制、结果要求。机械重查默认候选上限为**最多2次、累计不超过60秒，并计入已批准总预算**；只有包络允许、剩余预算足够且不违反人方明确连接/尝试上限时才可采用，否则取更严上限。当前无新卡，此数值不授权任何重查或恢复旧任务。

机械重查仅包括已知未启动科学计算的环境/资源等待或零启动修复，不能把新数据访问、模型前向或求解称为环境检查。等待本身不记为科学失败；未知是否启动先核进程与回执，不直接重发；真实科学异常/非有限/身份或重放不符/预算触发仍按对应合同停止，不换机器、不换ID绕过。真正科学重试若不在原许可中，仍需人方决定。

**仍需人方决定的唯一类别：超出现有有效任务包络的科学执行变更**（新科学范围/受保护数据、未许可producer或支出、扩大总预算、未获准的科学重试；外部发送另按既有逐次审批规则）。现有BRIDGE结果不重算，C27四组不重开，SCB从方案进入新的物理执行也不因规则迁移获得许可。

本次同步授权仅为本地文档迁移：不SSH、不安装/探针/传输、不训练/求解/重启、不新审核、不恢复自动化、不建对话/子代理、不编辑其他owner；共享Roadmap由发起HQ统一同步。本owner无须为此次管理文字作Code Ready复审。

---

## 历史运行与复用记录（保持原文）

# Current authorised BRIDGE-PS execution, 2026-10-19

Historical preparation documents remain retained. AUTHORITY_AMENDMENT_20261019.md supersedes their preparation-only boundary for this one run. This is HQ-delegated authority under verified direct user takeover/connection requests; no final-package human approval is claimed. See the sealed hq_authority_chain.json, independent_review_v3_authority.md and execution_manifest.json.

Exact executed runtime source 0faf16f8c7e9872956d3db89a3ced42505e4a9a4, package 7baafbd0f6da859022eae098509601fa280c6d87eb1845eb11ca6c33884bf295. Scientific/controller code and config remain byte-identical to d67f0ac6; only the authority contract and tests changed. 33 artificial tests pass in the established Miniconda environment, with Mac BLAS warnings retained; Homebrew Python lacked NumPy and its failed import is preserved locally.

Resource admission passed on GPUServer8: 64 CPUs, 1.16 initial load, 408.4 GB available memory, 653.9 GB free on /mnt/data2, fresh run root. Versions: Python3.10.12, NumPy1.24.4, Torch2.7.0, Matplotlib3.10.3. No GPU used. These are admission observations, not scientific validation. One detached controller started 2026-10-19T18:24:31Z, PID1314694; full command/paths in run_receipt_R003.json. The unchanged 1800s/1thread/8GiB/4GiB+4GiB and first-stop/no-retry limits apply. No separate scientific smoke occurred.

Actual evidence is stored in /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/IU-BRIDGE-PS-20261019-R003. The full 169,912,269-byte archive has been retrieved and hash verified. Independent saved-output and four-figure review found no numerical inconsistency. H_INNOV loss0.823602 improves B*8.11%, fixed C_RAW6.45%, donor5.53%;15/19 groups improve B*, with all three C30 groups adverse. A CSV-read-handle ResourceWarning escaped first-stop as an unraisable destructor exception. This is a real frozen stop-contract breach, not clean acceptance; original COMPLETE receipts and warning log remain untouched. Only explicitly caveated exploratory component evidence is retained. No repeat/repair-run occurred. See run_receipt_R003.json, evidence_receipt_R003.json and warning_contract_audit.json; the full README_analysis.md, independent review and Obsidian synchronization receipt are in the local evidence root.


## 2026-10-20 新批准后的科学复用决定

原B owner核对569cc865 BRIDGE-PS-v1.0与现有R003：同19组/1144起点/2288起点×H、同六臂与派生控制、同数据SHA、912+76 solves已经完成并取回。选择reuse，不重复模型工作或全量审阅，不新建RunID/授权/SSH。原ResourceWarning首停违约及探索证据边界保留，不因新批准改写旧接受状态。

保留H_INNOV候选：Δ=0.072689，H10/H40均正，逐组删一均正，优于对应donor；但C30/H40双通道失效和有限估计/选择敏感性阻止物理状态充分性或稳定局部演化主张。下一承重比较为已有SCB方案内加载匹配/独立裂长参考的自身vs替换历史干预，非rich/权重扫描；数据未确认不虚构运行准备。C27-A25四组单独冻结，未获本次重跑权限。

[科学判断、完整38单元表及下一完整验证](scientific_continuation_20261020/README.md) · [复用回执](scientific_continuation_20261020/reuse_receipt.json)。
