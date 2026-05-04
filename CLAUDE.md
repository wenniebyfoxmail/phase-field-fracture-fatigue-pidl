# Claude 工作规则（跨机通用）

适用范围：Mac + Windows 所有 Claude agent。此文件只放铁律和 session protocol。
详细协作规则见 `docs/workflow_rules.md`。

---

## Session Protocol

1. **开场**：先读 `docs/research_frontier.md`，用一句话声明本 session 的唯一主问题
2. **聚焦**：只追一个 active branch；其他想法放 frontier 的 Parking Lot
3. **Checkpoint**：每完成一个关键动作，问自己——它回答了什么？是否改变了分支优先级？
4. **结束前必须更新**（按需）：
   - `docs/research_frontier.md` — 如果研究状态变了
   - `docs/handovers/windows_pidl_inbox.md` 或 `csd3_inbox.md` — 如果要派新任务
   - local `memory/successor_handoff.md` — 如果需要接班

---

## 通信边界（2026-05-05 起）

- 跨机任务通信走 `docs/handovers/*_inbox.md` / `*_outbox.md`
- `shared_research_log.md` 只写长期保留的 finding / decision / retraction
- 日常 request / ack / progress / done 不写 shared_research_log

---

## 红线（任何机器、任何时候）

- **不自动 commit/push**。改完后提醒用户确认。
- **不 force push / reset --hard / rebase -i / amend** 已 push 的 commit。
- **代码进 git，结论进 memory**。不 commit 论文草稿、实验结论、生成数据。
- **不覆盖** 别人的 shared_research_log entry。
- **杀进程前三重验证**（cmdline + elapsed + cwd），默认假设其他窗口也在跑。

---

## 机器分工（一句话版）

| 机器 | 角色 | 权限边界 |
|---|---|---|
| Mac-PIDL | Dev | 可改所有 source/config/docs |
| Windows-PIDL | Producer | 只跑 case + 加新 runner + append log |
| CSD3 | HPC Producer | GPU 训练 + append log |

详见 `docs/workflow_rules.md`。

---

## 文件职责与 Owner

| 文件 | 职责 | Owner | Update trigger |
|---|---|---|---|
| `CLAUDE.md` | 铁律 + protocol | Mac | 规则变更时 |
| `docs/workflow_rules.md` | 详细协作协议 | Mac | 低频 |
| `docs/research_frontier.md` | 当前研究前线（≤50行） | Mac | 每个 research session 结束 |
| `docs/shared_research_log.md` | 长期公共历史 | Mac+Win+CSD3 | 只写有长期价值的 finding/decision/retraction |
| `docs/handovers/windows_pidl_inbox.md` | Mac→Windows 任务队列 | Mac | 派任务/改优先级/取消时 |
| `docs/handovers/windows_pidl_outbox.md` | Windows→Mac 回传 | Windows | ack/progress/done/blocker |
| `docs/handovers/windows_fem_inbox.md` | Mac→Windows-FEM 任务队列 | Mac | 派 FEM run 时 |
| `docs/handovers/windows_fem_outbox.md` | Windows-FEM→Mac 回传 | Windows-FEM | ack/progress/done/blocker |
| `docs/handovers/csd3_inbox.md` | Mac→CSD3 任务队列 | Mac | 同上 |
| `docs/handovers/csd3_outbox.md` | CSD3→Mac 回传 | CSD3 | 同上 |
| local `successor_handoff.md` | 接班摘要 | 各机器 | session 结束/上下文将满 |
| local `producer_state.md` | 执行态摘要 | Windows/CSD3 | 启动/完成 job 或遇 blocker |

---

## Commit Message 规范

- 第一行：动词开头，一句话说清改了什么
- 正文：列改动点、原因、影响
- 训练代码改动注明 "safe during running trainings" 或 "needs coordination"
- 不加 `Co-Authored-By`

---

## Related docs

- `docs/workflow_rules.md` — 详细协作规则（worktree、进程安全、session保护等）
- `docs/research_frontier.md` — 当前研究状态
- `docs/shared_research_log.md` — 公共研究历史
- `docs/handovers/` — 跨机任务通信
