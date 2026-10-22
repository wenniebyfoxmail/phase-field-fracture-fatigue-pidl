# 固定基准规则：活跃入口同步（2026-10-22）

范围：11个已加载的科研总HQ/执行owner，另通知1个文献启示窗口。只清理管理环节；不派新审核、测试或科研运行，不恢复HQ托管。已有独立科研任务的计算不归本次治理启动。

已读回下列原文件。表中路径以项目根为基准；命名worktree均写出相对位置。额外文献窗口已送达但未返回有效迁移回执，不计入已核对的11项。

| 当前窗口 | 原入口／当前卡 | 实际处理／管理提交 |
|---|---|---|
| 科研总HQ｜机制验证、跨路线协调与论文主线 | `/Users/wenxiaofang/.codex/automations/automation-4/automation.toml`、`hq_state.json` | 删除自动必要独审；仍PAUSED，无active卡；Git外本地配置 |
| PIDL 加载步间参数复用与计算效率 | `worktrees/s04-e039-rprop-state-20261022/docs/research/S04/S04-E039/experiment.md` | 原卡无多余审核门；补固定两臂三圈基准、不重跑已完臂；本治理直接提交`9c9c2233`，不改运行源码或进程 |
| 标准0.12 PIDL：去掉L2正则的对照求解 | `worktrees/s04-e038-rprop-cap-20261022/docs/research/S04/S04-E038/experiment.md` | 基准已完成、卡已结束；删默认全回归/历史重跑/逐commit及结果后审核；`ef80ed1f` |
| 共同有界模型：静态剪切 FEM/PIDL 与等幅 45° 对比 | `worktrees/fem-pidl-shear-20261020/docs/research/S04/S04-E035/descent_safeguard_proposal_20261022.md`及`experiment.md` | 删除重复旧fixtures、额外SPD小测阶梯和复审；保留原24态主比较；`f659e3d3` |
| 检查标准 0.12 PIDL loss 量级 | `worktrees/pidl-u012-primal-dual-20261022/docs/research/S04/S04-E037/experiment.md` | 删除默认CodeReady/evidence复审；复用已完原臂，只处理失败新臂；`9109d356` |
| PIDL 不可逆约束替代路线 | `worktrees/pidl-irreversibility-alternatives-20261021/docs/research/S04/irreversibility_alternatives_20261021.md` | 删除重复微测/每commit及默认结果后审核；保留用户明确要求的该次计算前复查，已完成不再派；`752997f3` |
| 参数化 PIDL 与疲劳状态转移模型实现 | `worktrees/fixed-weight-learning-20261021/docs/fixed_weight_learning.md` | 已完成、无active卡；旧测试仅历史，不列未来重复清单；`549cd59c` |
| 核查 PIDL–FEM 疲劳更新 timing 的实现与验证状态 | `worktrees/s04-stage-a-launch-20261022/docs/research/S04/S04-E036/experiment.md` | 固定原Stage A disabled/四冻结态；复用构建，删交叉复审/全回归阶梯；`f009d022`；活跃`fem_audit`已同步 |
| 排查循环加载下 PIDL 复现偏差 | `worktrees/s04-gap-attribution-20261022/docs/research/S04/S04-E036/experiment.md` | 固定原实现基准及既定科学对照；复用已过47项，不重跑T3/旧历史或独审；`c27c02ed` |
| 反演｜几何对齐与图证验收 | `.codex/worktrees/s03-e016-geometry-alignment-20261013/docs/research/S03/storyline.md`及`S03-E019/preparation/f01_v002_layout/README.md` | 已交付、无active卡；旧24/40/65项不改名新基准，保留已完成的用户指定V1–V3；`10fa2f78` |
| ISTRUST 复现｜第六轮权重与 RUL 基线 | `/Users/wenxiaofang/phase-field-fracture-with-pidl-worktrees/s02-e007-istrust-replay-20261020/docs/research/S02/S02-E007/README_analysis.md`及`scripts/istrust_replay/README.md` | 已完成、无active卡；清过时待执行/自动复审，不重跑R004–R006；`2f580efa` |

## 同步与保留

- 现有活跃helper由其owner转交规则；timing的`fem_audit`已确认接收。总HQ的5个、参数化的3个、不可逆的3个旧helper均已结束，不唤醒。没有为治理新建agent或复审。
- 用户明确要求过的具体审核与原科学比较保留；旧签名、失败、费用、保护数据、预算及实际启动/重试许可不改。规则更新不是重启失败科学尝试的许可。
- 本轮只读回文字/路径和Git状态；不另建行为模拟、回归或独立审核链。

## GitHub追踪：实查不是全部已同步

2026-10-22通过`git ls-remote --heads origin`读取真实远端分支，不只看本地upstream。规则分支在查询时精确为`42524ed2`；多条近期科研分支没有同名远端，包括E039、剪切、参数化和ISTRUST。缺同名分支不等于所有代码必然未出现在其他ref；本次不作这种推断。

各owner上述管理提交大多仅在本地。共享混合checkout相对同名远端领先24提交且仍有dirty paths；Stage A处于detached HEAD且有未提交实现/记录，E037分析脚本和E036评分工具也尚在工作中。它们不因此自动具备GitHub交付状态。本轮不批量推送未知/未完成代码，不重置或合并混合checkout。

当前代码链：独立任务worktree/branch → 固定任务基准（文档仅一致性）→ 有意义的scoped commit → push任务分支 → 科研Run记录确切源码commit。推送即能在GitHub分支追踪，不必等合并main；本地commit与已push必须分开报告。详细规则见`docs/git_workflow.md`和`docs/task_worktree_archive_protocol.md`。
