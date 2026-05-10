# Windows 机器 Setup 指南（新工作流）

Mac 已重构工作流文件。Windows 端 `git pull` 后，请按**你的角色**完成本地设置。

适用对象：
- **Windows-PIDL**：跑 PIDL runner / 训练 / 后处理
- **Windows-FEM**：跑 GRIPHFiTH FEM reference / mesh / handoff

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

这些放在 Windows 的 `~/.claude/projects/<repo>/memory/` 里，**不进 git**。

### 2.1 两个角色都必须建的文件

#### `memory/MEMORY.md`（本地 memory 入口）

最小内容建议：

```markdown
# Windows Local Memory

## Role
- Windows-PIDL / Windows-FEM

## Environment
- Python / MATLAB / CUDA / 常用路径

## Current Focus
- 见 `producer_state.md`

## Index
- `producer_state.md` — 当前执行态
- `env_notes.md`（可选）— 环境坑 + 恢复方法
- `run_registry.md`（可选）— 跑过什么 job
```

#### `memory/producer_state.md`（核心：当前执行态）

模板见 `docs/templates/producer_state_template.md`，复制过来后填上**当前正在跑什么、队列里有什么、最近完成了什么、卡点是什么**。

### 2.2 Windows-PIDL 额外建议（可选但推荐）

- `memory/env_notes.md`
  - 记录 Python / CUDA / runner 路径 / archive 路径 / 常见报错修复
- `memory/run_registry.md`
  - 记录跑过的 Request、runner、参数、archive、log、结果一句话

### 2.3 Windows-FEM 额外建议（可选但推荐）

- `memory/env_notes.md`
  - 记录 MATLAB / GRIPHFiTH / mesh 工具 / 数据 handoff 路径
- `memory/run_registry.md`
  - 记录跑过的 FEM Request、INPUT 文件、mesh、输出目录、结果一句话

## 3. Windows-PIDL：你到底要建什么

**必须建**：
1. `memory/MEMORY.md`
2. `memory/producer_state.md`

**共享文件里你要用的**：
1. 读 `docs/handovers/windows_pidl_inbox.md`
2. 写 `docs/handovers/windows_pidl_outbox.md`
3. 读 `docs/research_frontier.md`
4. 只在有长期价值时写 `docs/shared_research_log.md`

### Windows-PIDL session protocol

每个 session：
1. `git pull`
2. 读 `windows_pidl_inbox.md`（有新任务吗？）
3. 读 `research_frontier.md`（主线问题变了吗？）
4. 跑任务 / 检查日志 / 回传结果
5. 结束前更新：
   - `windows_pidl_outbox.md`
   - `producer_state.md`
   - `shared_research_log.md`（仅重要 finding/decision）
6. commit + push 共享变更

## 4. Windows-FEM：你到底要建什么

**必须建**：
1. `memory/MEMORY.md`
2. `memory/producer_state.md`

**共享文件里你要用的**：
1. 读 `docs/handovers/windows_fem_inbox.md`
2. 写 `docs/handovers/windows_fem_outbox.md`
3. 按需读 `docs/research_frontier.md`
4. 只在有长期价值时写 `docs/shared_research_log.md`

### Windows-FEM session protocol

每个 session：
1. `git pull`
2. 读 `windows_fem_inbox.md`（有新 FEM request 吗？）
3. 按 request 跑 mesh / INPUT / main script / handoff
4. 结束前更新：
   - `windows_fem_outbox.md`
   - `producer_state.md`
   - `shared_research_log.md`（仅重要 finding/decision）
5. commit + push 共享变更

## 5. 和之前的区别

| 以前 | 现在 |
|---|---|
| 任务通过 shared_research_log 的 [handoff] tag 接收 | 任务通过 `windows_pidl_inbox.md` 接收 |
| 进度也写在 shared_research_log 里 | 进度写在 `windows_pidl_outbox.md`（log 只放重要结论） |
| 没有接班文件 | `producer_state.md` 让下一个 session 秒懂当前态 |

## 6. 最小检查清单

如果你是 **Windows-PIDL**，完成后应满足：
- 本地有 `memory/MEMORY.md`
- 本地有 `memory/producer_state.md`
- 知道要读 `windows_pidl_inbox.md`
- 知道要写 `windows_pidl_outbox.md`

如果你是 **Windows-FEM**，完成后应满足：
- 本地有 `memory/MEMORY.md`
- 本地有 `memory/producer_state.md`
- 知道要读 `windows_fem_inbox.md`
- 知道要写 `windows_fem_outbox.md`

---

**完成后可以删除此文件，或保留做参考。**
