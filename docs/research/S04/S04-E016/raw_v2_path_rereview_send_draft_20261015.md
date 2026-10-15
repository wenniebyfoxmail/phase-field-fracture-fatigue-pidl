# Exact proposed difference-review request — NOT SENT

Sender:current S04 main chat, not an email account.
Recipient:`多目标优化学习 FEM–PINN Delta`
(`01a12d15-9b60-7280-8248-18386d6ef741`).
Attachments:none. Local code/evidence references only.
Review target:`c883bfd8e4ecd37d2ae32dc3717a63db018f1ae2`, compared with ab34c46.
No new computational commitment. Fresh approval required for this exact send.

## Full message body

请只读复审c883bfd相对ab34c46的授权路径修复，不重审已认可的算法。工作树：
/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-e016-request31-storage-block-20261009

仅改SENS_tensile/s04_raw_guard.py和s04_raw_guard_checks.py：入口按调用目录将授权路径解析为绝对路径，父进程校验、环境变量和子进程参数使用同一路径。设计45b8d32、数据、分组、归一化、选择规则及300秒／2GiB／100MiB预算不变。

新增的最小mock测试已运行一次：从非仓库目录传入相对路径，检查父进程校验、切换目录后的子进程参数，以及fit/report环境中的路径一致。测试通过；未创建真实授权文件、启动真实子进程、读取科学数据或拟合。完整记录和测试receipt位置见docs/research/S04/S04-E016/raw_v2_code_review_result_ab34c46_20261015.md末节。未重跑完整资源核验，既有合成资源证据的限制保留。

请只核对这一处问题是否解决、mock是否覆盖交接，以及有无新增必须修改项。本主对话仍是唯一实现和测试方；请保持只读，不执行测试或拟合、不修改共享笔记，S04-E017和多目标计算继续暂缓。请返回绑定c883bfd的复审结论。真实拟合仍需另行批准，本次不启动。
