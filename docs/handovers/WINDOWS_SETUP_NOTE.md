# Windows 机器 Setup 指南（新工作流）

Mac 已重构工作流文件。Windows 端 `git pull` 后请按以下步骤完成本地设置。

---

## 1. 你会 pull 到的新共享文件

这些文件已在 git 里，pull 即可用：

| 文件 | 你的角色 |
|---|---|
| `CLAUDE.md` | 读（瘦身版，铁律+protocol） |
| `docs/workflow_rules.md` | 读（详细规则，含 successor 协议） |
| `docs/research_frontier.md` | 读（当前研究前线，Mac 主写） |
| `docs/handovers/windows_pidl_inbox.md` | **读** — Mac 给你的任务在这里 |
| `docs/handovers/windows_pidl_outbox.md` | **写** — 你的 ack/progress/done 写这里 |
| `docs/handovers/windows_fem_inbox.md` | **读**（Windows-FEM 用） |
| `docs/handovers/windows_fem_outbox.md` | **写**（Windows-FEM 用） |
| `docs/shared_research_log.md` | append-only（只写有长期价值的 finding） |

## 2. 你需要在本地创建的文件

这些放在 Windows 的 `~/.claude/projects/<repo>/memory/` 里，**不进 git**：

### 2.1 `memory/MEMORY.md`（本地 memory 入口）

```markdown
# Windows-PIDL Local Memory

## 环境
- Python: ...
- CUDA: ...
- 常用 runner 路径: ...

## 当前关注
- 见 `producer_state.md`

## 索引
- `producer_state.md` — 当前执行态
- `env_notes.md`（可选）— 环境坑 + 恢复方法
```

### 2.2 `memory/producer_state.md`（核心：你的执行态）

模板见 `docs/templates/producer_state_template.md`，复制过来填上当前状态即可。

## 3. 新的 Session Protocol（Windows 版）

每个 session：
1. **开场**：`git pull` → 读 `windows_pidl_inbox.md`（有新任务吗？）→ 读 `research_frontier.md`（大方向有变化吗？）
2. **执行中**：按 inbox request 跑任务
3. **结束前更新**：
   - `windows_pidl_outbox.md` — 写 ack/progress/done/blocker
   - `producer_state.md` — 更新当前执行态
   - `shared_research_log.md` — 只有重要 finding/decision 才写
   - commit + push outbox 和 log（如有）

## 4. 和之前的区别

| 以前 | 现在 |
|---|---|
| 任务通过 shared_research_log 的 [handoff] tag 接收 | 任务通过 `windows_pidl_inbox.md` 接收 |
| 进度也写在 shared_research_log 里 | 进度写在 `windows_pidl_outbox.md`（log 只放重要结论） |
| 没有接班文件 | `producer_state.md` 让下一个 session 秒懂当前态 |

## 5. Windows-FEM 额外说明

Windows-FEM 用对应的 `windows_fem_inbox/outbox`，其余同理。

---

**完成后可以删除此文件，或保留做参考。**
