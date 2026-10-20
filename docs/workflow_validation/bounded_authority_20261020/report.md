# 一次授权与自动机械检查：落地核验（2026-10-20）

Owner：research-workflow governance。用户授权更新skill与各HQ活跃卡的管理流程；本轮不派发科学执行。
工作分支 `codex/visual-explanation-contract-20261018`，起点 `e1e6e991`；科学owner各自保存其卡片修订。

## 当前规则

一次有边界的任务批准覆盖实现、测试、必要聚焦复核、部署、自动准入与执行。Agent处理实际版本、兼容性、环境/资源、RunID、路径、哈希与卡片一致性；不逐项索批，不因纯元数据补齐重启Code Ready。

人方只决定真实边界变化：范围、保护数据、producer/费用、预算或未允许的科学重试。仅批准计划仍不能运行；旧首停、已消费许可与签名快照保留。新卡事先给机械重查短上限，GPU忙且确定零启动不算科学失败；未知进程状态先查证，不盲目再次spawn。

## Skill与入口

- `research-decision-core`统一规定一次任务授权及Agent/Reviewer/User分工。
- `research-review-channels`改为任务内一次通道选择；同范围聚焦复核不重复索批，纯元数据自动核验。
- Road适配器、canonical `AGENTS.md`及已安装bootstrap引用同一规则，不再各造审批链。
- 全局审核skill原指向 `exploratory-formal-gate-20261017`；已确认正文与维护版相同、原worktree干净后，将符号链接改指本维护worktree。旧源未覆盖。
- PIDL数值/分析规则不改；运行分析入口继续由现有bootstrap读取核心授权规则。

## 行为检验

独立只读前向检查五种实际情境：

| 情境 | 应执行的决定 |
|---|---|
| 已授权一次执行，缺实际Matplotlib版本/路径/RunID | Agent自动补齐、检查一致性与兼容性，条件满足直接继续，不再请求逐项批准 |
| 仅批准方案，环境字段已齐 | 保持禁用，不将检查通过当执行许可 |
| 唯一科学尝试已失败，日志修复且预算有余 | 保留失败；可准备同范围修复，不自动重启已消费尝试 |
| 已审科学/控制源不变，只实例化卡元数据且JSON哈希改变 | 对照已审模板/权限范围自动校验；哈希变化本身不触发全量复审或人方批准 |
| 兼容性修复拟换数值算法、读新封存数据或改共享系统 | 不伪装机械检查；按改变的风险复核并合并申请所需新权限 |

这检验的是权限决策行为，不是实际launcher/生产机执行。没有SSH、科学数据读取、求解或训练。

## HQ／执行窗口写回

已向13个原窗口送达定点迁移要求，并读回12个当前owner的实际文件。另一个窗口已由用户转为历史窗口，执行归S09，不再制造重复卡。没有活跃卡的HQ只改原入口。共享Roadmap由本任务统一同步。

| 窗口／owner | 当前卡或入口 | 写回与边界 |
|---|---|---|
| 梳理近期对话任务与进度 | `/Users/wenxiaofang/.codex/automations/automation-4/HQ_CURRENT_ENTRY.md` | 已读回；当前提示与state同步，托管仍为PAUSED |
| Deep research: independent crack CV… | `crack-route-priorities-20261019/docs/datasets/road_fracture_dataset_inventory_20260827/ROUTE_PRIORITY_DECISION_20261019.md` | 已落盘，owner提交 `878914d3`；无独立执行卡，沿用三个科学owner |
| Astra HQ — Topological Crack Metrology | `research_proposals/macro_crack_identification_20261009/D3_EXECUTION_PACKAGE.md`及`REVIEW_PACKET.md` | 已落盘；取消Agent加上的资源逐项批准，未来最多3次/15分钟机械检查计入原预算；旧0启动停点保留 |
| Astra HQ — Reliable Crack Identification | `hq-road-uq-feas-001-20261011/research_hq/HQ-ROAD-UQ-FEAS-001/target_compatibility_20261020/D5_CENTERLINE_TARGET_PROPOSAL_2026-10-20.md`及README | 已读回，`6ba8b3e1`；D4完成，D5仍为设计，不制造运行许可 |
| Astra HQ — Identification Uncertainty… | `mendeley-info-value-20261019/docs/research/identification_uncertainty_prediction/bridge_ps_20261019/CURRENT_EXECUTION.md` | 已读回，`94f0d1ab`；无active卡，旧C27A25首停与已完成BRIDGE保留 |
| 设计并验核裂缝 Neural Operator | `s09-e007-fixed-damage-holdout-20261012/docs/research/S09/S09-E017/admission_only_phase_r_approval_card_20261020.md`及原plan | 已读回，记录`e2958d68`；Phase L在原独立任务中完成，剩余一次整包admission-only决定，机械字段不再二次审批；producer仍隔离 |
| PIDL 上翘诊断与改善：完整物理场 | `pidl-weight-gradient-fix-20261018/docs/research/S04/hybrid_constrained_design_20261019/authority_amendment_20261020.json`及README | 已读回，`54ff3d1f`；实际Matplotlib版本/渲染检查自动完成，无active启用卡；旧v4哈希不变 |
| PaveTrack 独立研究与 S01-E001 执行 | `s01-e028-target-spatial-qualification-20261019/docs/research/S01/S01-E029/taobo_execution_approval.md` | 已读回，`c625705b`；只保留一次整包迁移/执行与私有输入许可，不逐项审批机械字段 |
| 细化PINN复现FEM算法流程 | `s04-sampling-multiscale-20261012/docs/research/S04/S04-E024/physical_field_budget_taobo_cpu2_approval_v2.md`及experiment | 已读回，`adebf870`；原科学条件/预算/明确删除对象不改，首次整包执行与私有传输尚未批准 |
| 评估 FEM 可微化与反演 | `q4-material-inverse-20261020/docs/research/inverse_fem_A/implementation.md`及`switch_solver_and_path_validation.md` | 已落盘，owner提交 `351fde42`；无active卡，未来机械检查2次/10分钟计原预算；完整路径数值验证未授权 |
| 规划 FEM 模型的 PIDL surrogate | `fem-surrogate-comparison-prep-20261020/docs/research/S04/hybrid_constrained_design_20261019/complete_execution_20261020/current_entry.md` | 已读回，`77119a1d`；原r2已消费，未恢复或新建执行；本次未查询服务器 |
| 跨主线连接与第一性原理突破设计 | `local_archive/hq/cross_track_bridge_20261019/handoff_authorization_20261020.json` | 已落盘；本窗口无active卡，引用原B owner，不重跑R003 |
| 已归档 ｜ 设计并验核裂缝 Neural Operator（主母对话框） | 用户已将旧Delta协调窗口改名为历史窗口；当前执行归上方S09 owner | 不声称本窗口已写回治理文件；其任务被用户改名要求替代，不重启历史窗口、不建立重复authority |

表中命名worktree相对于项目 `.codex/worktrees/`；其他路径相对于项目根。提交为各owner回执中的记录，文件已实际读回；不声称所有owner分支已推送或合并。

各owner的新卡机械重查短上限随原任务预算设置，不新造跨领域统一秒数；明确人方上限优先。S09原方案的分阶段文字、旧签名包与历史停点保留，但当前入口明确指向新规则，不再拿历史行政门阻断已授权机械工作。

## 核验与保留

- 三个修改后的skill通过 `quick_validate.py`；diff空白检查通过。
- 旧PIDL `coupled_repair_card_v4.json` SHA256仍为 `1440a0a609f49fafe033e6b727f58c9e6f9b779dee4ba8bda7999146307886fb`，未把旧禁用卡当新许可。
- 未改科学验收、预算、封存数据或失败回执；未恢复自动化。本轮只实现治理和管理卡迁移。
