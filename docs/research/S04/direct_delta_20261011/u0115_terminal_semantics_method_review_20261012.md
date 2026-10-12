---
storyline_id: S04
scope: independent_terminal_metadata_and_method_review
date: 2026-10-12
status: g5_hold__matched_projection_and_field_export
execution_owner: source_dialogue_01a1131d-017c-7b03-a95a-ad73ba8fcc9c
---

# U0.115 PINN终态：直接Delta方案的语义继承

结论：终态文档与候选manifest在coverage、event计数和support上相符。原生acquisition完成，
但不是matched data lock，也不是FEM teacher或corrector有效性证据。方法记录的HOLD原因
从“未找到U0.115原生run”更新为“同状态projection/字段导出/输入管线待资格审查”。
本轮是文档/metadata交叉核对；没有独立重算native数值或archive hashes，不替代producer审计。

## 证据身份

只读复核主对话工作树下两份记录：

- `docs/research/S04/S04-E016/u0115_pinn_terminal_audit_20261012.md`
- `docs/research/S04/S04-E016/same_state_asset_manifest_20261012.json`

完整root：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-e016-request31-storage-block-20261009/`。
control evidence位于该root的
`local_archive/experiments/S04-E016/u0115_pinn_acquisition_20261012/terminal_audit/`；
原始输出留在Taobo，本方法工作树不复制或改写。

| 身份/审计 | 主对话终态记录 |
|---|---|
| PINN run | `pf_u0115_acquire_39f8108fe96d406385e4011700cb47f9` |
| 已独立Code Ready审核的source | `b6d56102daa7d45a6c196b72055010170e5f39fb` |
| Archive manifest SHA256 | `ddd2e4f4c247e3b5aeb7bcae409b6a579c6f9a02c1337d0770da94fda48d4326` |
| 封存范围 | 1894 files，4,849,185,351 bytes |
| 终态 | exit0；child stopped；no cleanup errors；2026-10-12 22:51:53 London |
| 实际保存 | 503连续checkpoint，raw steps0--502；matching models与required finite histories通过 |
| 审计边界 | serialization/finite validity；没有forward-field/PDE/paired资格PASS |
| 当前manifest | candidate_manifest_not_admitted_data_lock；projection_qualified=false；paired_admitted=false |

## Raw steps不是physical cycles

冻结producer每个physical cycle有5个substeps；这里的event confirmation计数器每raw loop递减。
事件附近映射为：

| raw training step | physical state | 含义 |
|---|---|---|
| 499 | c100/s4 | 首次检测；不是pre-event s4 target |
| 500 | c100/s5 | 第1个后续raw step；完成c100 |
| 501 | c101/s1 | 第2个后续raw step |
| 502 | c101/s2 | 第3个后续raw step；native stop |

因此不能把log的“cycle502”称为502个physical cycles，不能把3raw-step confirmation等同
FEM的3physical-cycle tail，不能把terminal502当s4/s5。120cycle schedule是上限，非已达覆盖。
已有c1--100完整s4/s5可用于资格审查；own-pre-event s4候选仅c1--99。common-pre-event还需
与声明的FEM event/state mask取交集，不在这里假定最终admitted数量。
FEM有c1--103并不意味着103cycle都存在PINN同状态配对；c101/s2不能补成s4。
event可用于retrospective资格/评分，不作为feature、cycle/lifetime归一化或部署stopping输入。

## 原生支持对Delta标签的约束

| producer | 原生支持 | 不可混同 |
|---|---|---|
| PINN hist_alpha | 45591 nodes | committed max-damage history；不是H，也不是fatigue alpha_bar |
| PINN hist_fat、psi_history_elem、psi_plus_prev | 90000 triangle-element values | 不是FEM Q4 GP原生history |
| FEM | 86756 nodes；86408 Q4 cells；每cell4GP | 不能与PINN node/cell indices逐个相减 |

逐channel锁定source、位置、timing、projection、quadrature/reduction、precision以及共同
contained mask/areas后，才计算声明reduced-field的FEM−PINN Delta。现有centroid sampling
不能默认为cell integration。mapping误差与model error分开，不把投影不足归咎于网络容量。

继承当前s4 reduced-route：d、alpha_bar、raw psi为直接primary输出；matched mean f若获批
可作直接auxiliary head，但不能强制f(mean alpha_bar)。exact active需同状态native joint
parents及先计算后reduction，不用mean-parent product冒充。H缺失保持missing。
checkpoint histories是post-commit；pre-history-refresh gradient diagnostics不得替代。
C0/lag初始化也需要其真实state身份，不从event尾段或未来state填补。

## 下一门与责任边界

主对话只复用现有checkpoint，完成s4+causal history export、projection/containment、
precision、timing/load和deployable-input pipeline审查，然后提交逐字段G5 data lock。
方法对话不执行该export，不修改G5 verdict/共享Obsidian，不新增run、不续跑、不重算D003。

G5通过后仍需D0 runner/protocol审查与唯一执行receipt；最小对照保持B0 Delta0 vs B1直接
多输出closed-form ridge，预算<=5min/2GiB RAM/100MiB outputs，不自动释放NN。
U0.1175 scientific payload继续封存，U0.125继续关闭。原生execution成功不是paired学习成功。
