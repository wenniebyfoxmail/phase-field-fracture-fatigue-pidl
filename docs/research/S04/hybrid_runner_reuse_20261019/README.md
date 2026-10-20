# 当前状态（2026-10-20）

已按用户批准发送四项修复协调消息；继续复用唯一 owner，无重复 producer。本轮核验新冻结包 `ee49dc0e` 的 53 个文件与输入 7 个资产，原 solver 字典与首版完全相同；准备卡禁用、无运行 ID。独立差异复审通过（仅静态准备包范围），四项修复及新耦合路径的证据顺序问题已关闭，不执行训练、新 FEM 或补充 FP64。

Matplotlib 尚未固定版本并纳入运行准入，旧实机成本失败保留；当前不能称 producer-ready。

见 [本轮完整交付](update_20261020.md)、[准备卡 v2](preparation_card_v2.json)、[核验收据 v2](reuse_verification_v2.json)。下文保留 2026-10-19 首版及当时待发送状态的历史快照；当前发送状态以本段和新收据为准。

---

# 完整混合 runner 复用交付（准备阶段）

本对话权限：**仅准备与复审；训练、新增 FEM、补充 FP64 均未执行，也未获本对话执行许可。**

唯一实现 owner 为「PIDL 上翘诊断与改善：完整物理场」（01a14bbc-c8fd-7bd2-85fe-e0d6cbadc85d）。不复制开发另一套 producer。原 owner 对话的执行权限不继承到本记录。

首版完整包已冻结到 `d05fd5834468f04e200d70e7f4dce7873241af6d`；artifact `73f617acd9d23fc6706c6493665e3d92035d29f4e317bc3e3b3566a43c62d276`。本对话逐字节核对清单内 25 个文件与该提交一致，并核对输入 manifest。独立代码复审结论为 **MODIFY_AND_REREVIEW**；旧 a76825eb 库/API 通过不自动证明新 runner 可执行。

## 运行包要回答的问题

| 项目 | 拟复用合同及必须核实的依据 |
|---|---|
| 初态 | 复用已见 c1 common_initial；u=0、完整给定 d、lower=d、A/r=0、f=1；opaque 保留。该初态是共同预设条件，不是认证训练标签。|
| 原生对齐 | blocked 位移/力显式转交错排列；四 GP 顺序、自由/固定 DOF、网格与输入 SHA 一并核对。五个保存态回放不求新状态。|
| 物理尺度 | AT1/Amor，E=1、nu=.3、Gc=.01、ell=.01、thickness=1、eta=0、alpha_T=.5、p=2；force/gradient 固定标度的来源须在卡中说明。|
| 接受与提交 | 原容差保留；final 同一 u/d/f fresh 审计后单次 CAS。trial 从不可变接受前态重建，节点下界不在 inner 更新。|
| 失败恢复 | 首次失败停整包；不重试、不改容差/eta/加载步。replace 后不确定写入只读核对持久版本、指纹、日志与累计成本，锁不自动删除。|
| 三组 | 同问题直接受约束 FEM、经典可行外推、冻结 NN 初值；各自推进自己的历史，共同后端/精度/接受标准。|
| 数据与训练 | train .8/1.2、validation 1.0、test .9；各轨迹 120×5；单 fit/seed、最多 20000 updates。先标签、再训练/冻结、后测试，无 test 选模。|
| 完整成本 | 六条数值轨迹最多 3600 子步；12 GPUh、136 host 墙钟小时/2176 核小时、16 核共享池；RAM 64GiB、VRAM 24GiB、主/归档各 128GiB。含 setup、IO、失败、终止及评分。|

当前已核实的缺口：已见五个 c1 保存态没有形成符合新合同的完整标签轨迹；没有可复用的已训练模型。未来完整比较需要标签生成及训练阶段，不能把它们藏在“复用”一词之下。本对话只准备该流程。

## 确切文件与权限绑定

- [本对话准备卡](preparation_card.json)：保留整套数值计划，但 schema 为 `hybrid-preparation-card-v1`、`execution_enabled=false`。runner 不接受该 schema；未生成启动许可。
- [逐字节复用核验](reuse_verification.json)：源提交、25 文件 SHA、卡/清单/输入 SHA，以及本对话 0 次科学求解、0 次训练、未做补充 FP64。
- 原 owner [完整方案](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/pidl-weight-gradient-fix-20261018/docs/research/S04/hybrid_constrained_design_20261019/execution_plan_v1.md)、[精确源卡](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/pidl-weight-gradient-fix-20261018/docs/research/S04/hybrid_constrained_design_20261019/execution_card_v1.json)。源卡含另一对话的条件执行授权，不能在本对话直接使用。
- 原 owner [runner](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/pidl-weight-gradient-fix-20261018/tools/run_hybrid_producer.py)、[worker](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/pidl-weight-gradient-fix-20261018/tools/hybrid_producer_worker.py)、[恢复只读检查](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/pidl-weight-gradient-fix-20261018/tools/inspect_hybrid_run.py)。未另写 producer。

原数值容差不放宽：自由力 L2≤1e-8、KKT/投影≤1e-7、边界/界≤1e-10、疲劳 fixed-point≤1e-8、QP eps=1e-10，保留旧严格联合残差 4e-6；每步最多 100 outer/50 mechanics/200000 QP/120s。新方法的字段质量和时间目标为事前工程目标，不能覆盖旧实验容差或作为物理真值证明。

源卡训练与测试为未来完整计划：train .8/1.2 各 600 接受步、validation 1.0 为 600 步，随后单次训练及冻结，再 test .9 下三组各 600 步。模型不存在时不使用随机 NN 代替。生产机预设 GPUServer8/GPU5，精确 UUID、依赖和输入均在卡中；资源、依赖、可达性须未来现场重新核实，旧快照不是预留。已见远端快照缺 OSQP1.0.4；本对话未安装、未 SSH、未传输、未启动。

初态指纹 `3a0d14f7a8ca7ab6f81619b338f84e1acf4bcbd20aab61f821cbbf28b269c2e5`；输入 manifest SHA `2ecb2c68041ac128b5cdfa706536933c10fee2ceb888ddcf3392169cd832f754`。保存态算子回放与轻量 mock 检查复用原 owner 的记录，不重复跑新状态。

原 owner 已记录 41 项轻量检查通过，范围仅人工数据、代数 mock、良性自有子进程 watchdog；不是 41 项科学验证。独立复审的 [原文](hybrid_producer_d05fd583_review.md)、[机器收据](hybrid_producer_d05fd583_review.json) 及 [材料记录](hybrid_producer_d05fd583_review_materials.json) 已归档。

详细核对范围见 [requirements.md](requirements.md)。


## 当前结论与下一步

首版尚不能称完整 producer 就绪。四个实质问题是：硬 deadline/子进程清理，失败资源峰值记账，经典对照质量与提速口径，及预定完整场/分量/回退输出。见 [中文位置与修复方向](review_findings_v1.md)。需要唯一 owner 修复并冻结实际 launcher 在内的新包，再对差异及下游影响复审；本对话不编辑 owner 源码或复制另一套 runner。

发送给 owner 的精确修复协调消息已准备并展示，按用户逐次消息审批规则等候批准。本地代码/卡审核与文档工作已完成到本快照；未将尚在修改的工作树当作通过结论。原 owner 自己的复审修复过程和后续执行不属于本对话的运行行为，也不改变本对话禁止训练/新增 FEM/FP64 的边界。
