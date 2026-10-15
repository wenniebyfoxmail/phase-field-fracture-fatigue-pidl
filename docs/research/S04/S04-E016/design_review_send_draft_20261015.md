# Final proposed send — awaits user's per-send approval

Sender: current S04 main chat `探索神经网络学习 FEM-PINN 残差`
(`01a1131d-017c-7b03-a95a-ad73ba8fcc9c`); not an email account.
Recipient: existing chat `多目标优化学习 FEM–PINN Delta`
(`01a12d15-9b60-7280-8248-18386d6ef741`).
Attachments: none. References: local shared worktree documents below only.
Commit binding: design at `410fffc`; prior diagnostic/cause audit at `4167b64`.
Status: DRAFT ONLY; not sent. Approval of sending is not computation authority.

2026-10-15 delivery update (original proposal header/body retained): the user
approved this exact version and it was sent unchanged once to the named chat.
Receipt and completed reviewer response verified; no attachments or resend.
See `design_review_result_410fffc_20261015.md`: direction reasonable, revision
required, not approved for implementation or fitting. No new outbound approval
is implied by this completed send.

## Exact message body

请只读审核这次设计修订，暂不实现、拟合或重复计算。

设计版本：410fffc。工作树：
/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-e016-request31-storage-block-20261009
文件：docs/research/S04/S04-E016/design_revision_raw_physical_v1_20261015.md。
依据是同目录的 d0_R002_readonly_cause_audit_20261015.md；R002旧结果和原始数据不改。

建议先只学raw driver的物理尺度线性残差，并固定非负输出映射；damage/history暂不学习，两组共用有界、非负基线。仍用原四条开发轨迹、因果输入和整Umax留出。主指标为最差留出轨迹的物理RMSE比，另要求C1–20不退化；内层无合格模型才提前选整轨迹基线，禁止根据外层结果补救。后续最小对照只有V0/V1，拟议预算仍为300秒/2GiB/100MiB。

请重点检查：这个单通道范围能否回答下一步问题；输出映射是否公平且未混同逐点合法与时间不可逆；物理指标、早期规则和内层回退有无漏洞；是否有更小且必要的验证。U0.1175/U0.125不打开，不启动NN或多目标训练。

请仅返回设计意见、必须修改项及理由，不修改共享笔记或启动作业。设计通过也不授权计算；实现后仍需独立代码审核和用户另行批准。
