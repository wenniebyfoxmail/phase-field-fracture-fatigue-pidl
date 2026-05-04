# Workflow Rules（详细版）

本文件是 `CLAUDE.md` 铁律的展开。低频查看，不需要每个 session 都读。
协作分工和 git 操作细节见 `git_workflow.md`。

---

## 通信通道职责边界

| 通道 | 写什么 | 不写什么 |
|---|---|---|
| `*_inbox.md` | 任务请求、优先级变更、取消 | 研究叙事、长篇分析 |
| `*_outbox.md` | ack / progress / done / blocker / question | 长期结论（那些去 log） |
| `shared_research_log.md` | 重要 finding / decision / retraction / blocker with lasting impact | 日常 request / ack / progress / done |
| `research_frontier.md` | 当前问题、活跃分支、parking lot | 历史、执行细节 |

**判断标准**：一条信息半个月后还有人会回看吗？
- 是 → `shared_research_log.md`
- 否 → `*_outbox.md`

---

## Worktree 使用规则

- **默认不勾 worktree**，直接在主工作目录工作
- 只有在需要并行跑多个独立的代码实验时才勾 worktree
- 会话结束时如果 Claude 提示 "keep or remove"，默认选 remove
- 如果保留了某个 worktree，在 memory 里记一条说明用途和对应分支名

### Worktree 命名规则

- 总是给 worktree 起有意义的名字，不用默认随机名
- 命名约定（用 `/` 分段）：
  - `exp/<描述>` — 实验性改动
  - `fix/<bug描述>` — 修 bug
  - `refactor/<模块>` — 重构
  - `compare/<对比维度>` — 参数对比
- 限制：只允许字母、数字、`.`、`_`、`-`、`/`；总长度 ≤ 64 字符

---

## 工作目录一致性

- 只在 `upload code/` 这一层启动 Claude
- 理由：Claude 的 memory 按工作目录绝对路径分隔，换目录 = 换 memory
- 例外：`GRIPHFiTH/` 是独立项目

---

## 跨 worktree / 跨窗口的进程安全

**默认假设其他人的进程也在跑。**

### 杀进程前必须三重验证

1. **完整 cmdline**（含所有 flag）
2. **ELAPSED time**（`ps -o etime`）— 比你刚启动的长 → 不是你的
3. **CWD**（`lsof -p <PID> | grep cwd`）— 两个 worktree CWD 不同

### worktree 窗口的默认假设

- 默认假设主窗口也在跑长任务
- 看到"孤儿进程"，默认它是主窗口的
- kill 之前先问用户
- 宁可漏杀也不可错杀

### 启动长任务的规范

- ✅ `nohup python ... > log 2>&1 &`（单层 backgrounding）
- ❌ 不要叠加 `run_in_background=true` + `nohup ... &`
- 启动后立刻确认 PID，记下来
- log 文件名带时间/参数

---

## Session 对话记录保护

- `~/.claude/projects/...` 里的 `.jsonl` 是原始对话记录，不是临时文件
- 清理 worktree 时，默认只清 worktree 目录和 git 分支
- 不清 session 目录（除非用户明确要求且先备份）
- 原则：分支可重建，对话记录删了就没了

---

## 不 commit 结果（详细版）

核心原则：代码进 git，结论进 memory。

不 commit：论文草稿、实验结论总结、生成的图/数据（已 .gitignore）、非代码笔记。

可 commit：代码、工具脚本、构建说明、跨机协调文档。

结论写进：local memory（实验数值、物理机制、设计决策）或 shared_research_log（需跨机共享的发现）。

---

## Successor Handoff（接班协议）

每台机器在 `~/.claude/projects/<repo>/memory/` 下维护接班文件：
- **Mac**: `successor_handoff.md` — 模板见 `docs/templates/successor_handoff_template.md`
- **Windows**: `producer_state.md` — 模板见 `docs/templates/producer_state_template.md`

### 什么时候写/更新

- session 快结束时
- 上下文将满时
- 需要换 agent 时

### Successor 阅读顺序（Mac）

1. `memory/successor_handoff.md`
2. `docs/research_frontier.md`
3. `docs/handovers/windows_pidl_outbox.md`（如果和 Windows 相关）
4. `memory/MEMORY.md`
5. `docs/shared_research_log.md`（只在需要追历史时）

### Successor 阅读顺序（Windows）

1. `memory/producer_state.md`
2. `docs/handovers/windows_pidl_inbox.md`
3. `docs/research_frontier.md`
4. `memory/MEMORY.md`
