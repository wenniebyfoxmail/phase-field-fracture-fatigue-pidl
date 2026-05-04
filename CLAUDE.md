# Claude 工作规则（跨机通用）

**适用范围**：Mac + Windows 所有 Claude agent。此文件随 git 同步，两机自动读到。

Mac-specific 操作细节（绝对路径、定期清理命令等）见项目父目录的 `CLAUDE.md`（Mac 本地仓库，不 push）。

---

## Commit / Push 规则

- **不要在没有明确指令的情况下自动 commit 或 push**
- 代码改完后，提醒用户："改动已完成，需要我帮你 commit + push 吗？"
- Commit message 要写清楚：
  - 第一行：一句话说清楚改了什么（动词开头，如 Fix / Add / Refactor）
  - 正文：列出具体改动点、原因、影响
  - **不加** `Co-Authored-By` 这一行

## 不 commit 结果（只 commit 代码）

核心原则：**代码进 git，结论进 memory**。

- ❌ **不要 commit** 任何"结果类"产物：
  - 论文草稿（paper drafts、manuscript drafts）
  - 实验结论总结（findings summaries、analysis docs）
  - 生成的图、数据文件（已 .gitignore：`*.npy`, `*.pt`, `*.png`, `*.pdf`, `hl_*/`）
  - 非代码的笔记、讨论记录
- ✅ **可以 commit**：
  - 代码（source、tests、configs）
  - 工具脚本（analysis、figure generation、post-processing scripts）
  - 构建/运行说明（README、launch.json）
  - 跨机协调文档（`docs/shared_research_log.md`、`docs/git_workflow.md`）
- ✅ **结论写进**：
  - `~/.claude/projects/<path>/memory/*.md` — 实验数值、物理机制发现、设计决策、未来方向（**每台机器各自的本地 memory，不进 git**）
  - `docs/shared_research_log.md` — 需要跨机共享的发现或决策（**简化版，append-only**）
- 如果 working tree 里出现 `paper_draft/`、`notes/`、`findings.md` 这类文件，要么把内容提炼进 memory 然后删除，要么加进 `.gitignore` 留在本地不进版本控制。

**理由**：代码有版本控制的意义（可 diff、可 bisect、可回滚），结论没有 —— 结论只要"对的那个版本"，旧结论意味着"当时理解错了"，不需要保留在 git 历史里。

## 多机协作 — Mac / Windows Dev/Producer 分工

**完整规则见 `docs/git_workflow.md`**。这里只重申分工和红线。

### 分工

| 机器 | 角色 | 可以做 | 禁止做 |
|---|---|---|---|
| **Mac-PIDL** | **Dev** | 所有 `source/*.py`、`config.py`、脚本、文档改动 | — |
| **Windows-PIDL** | **Producer** | `git pull`；跑 case；加**新的** `run_*.py` runner；`append-only` 写 `docs/shared_research_log.md` | 改 `source/*.py`、改 `config.py` 默认值、refactor、删文件、覆盖他人 log entry |
| **Windows-FEM** | **FEM reference producer** | GRIPHFiTH FEM run；`append-only` 写 shared_research_log；上传 `~/Downloads/_pidl_handoff_*/` 数据 | 同上 |

### 红线（任何机器，任何时候）

- ❌ `git push --force` / `git push -f`
- ❌ `git reset --hard` 到已 push commit
- ❌ `git rebase -i` 改已 push 的 commit
- ❌ `git commit --amend` 已 push 的 commit
- ❌ 覆盖 `docs/shared_research_log.md` 里别人的 entry
- ❌ 在另一台机器 active training 时 push 训练代码路径的改动，**不先在 shared_research_log 开 `[decision]` 协调**

### 通信通道

- **`docs/shared_research_log.md`** —— 两机共享的研究日志，newest-first append。格式、entry 类型、冲突处理见 `docs/git_workflow.md §4`。
- **local memory** —— 各自私有理解，**不进 git**。
- **代码 commit message** —— 训练代码改动必须注明 "safe during running trainings" 或 "needs coordination"。

### 紧急 escape hatch

- **Windows 阻塞 bug**：shared_log 开 `[blocker]` → 做最小 hotfix → commit message 前缀 `HOTFIX:` → push → log 标记 "pushed hotfix <SHA>"
- **Mac 改 training-loop 语义**：shared_log 开 `[decision]` → 等 Windows ack → 再 push → commit message 前缀 `BREAKING:`

**详细 session template 和各类 entry 格式见 `docs/git_workflow.md`。**

## Worktree 使用规则

- **默认不勾 worktree**，直接在主工作目录工作
- 只有在需要**并行跑多个独立的代码实验**时才勾 worktree
- 会话结束时如果 Claude 提示 "keep or remove"，**默认选 `remove`**（除非明确要保留那个分支做后续对比）
- 如果保留了某个 worktree，在 memory 里记一条说明用途和对应分支名，否则几天后就忘了

### Worktree 命名规则

- **总是给 worktree 起有意义的名字**，不要用默认的随机名字（`condescending-herschel` 这种无法辨认）
- 用户可以在提示里直接指定，如："开一个叫 `exp/williams-kt` 的 worktree"
- Claude 调用 `EnterWorktree(name="...")` 时必须使用用户指定或有语义的名字
- 命名约定（用 `/` 分段便于分类）：
  - `exp/<描述>` — 实验性改动（如 `exp/williams-kt`、`exp/fourier-feature`）
  - `fix/<bug描述>` — 修 bug（如 `fix/e-el-runaway`、`fix/x-tip-freeze`）
  - `refactor/<模块>` — 重构（如 `refactor/field-calc`）
  - `compare/<对比维度>` — 参数对比（如 `compare/coeff-1.0-vs-3.0`）
- 限制：只允许字母、数字、`.`、`_`、`-`、`/`；总长度 ≤ 64 字符

## 工作目录一致性

- **只在 `upload code/` 这一层启动 Claude**，不要在 `upload code/SENS_tensile/`、上一级父目录或 `fem/` 分别启动
- 理由：Claude 的 memory 按工作目录的绝对路径分隔，换目录 = 换一份独立 memory，上下文会断开
- 例外：`GRIPHFiTH/` 是独立项目，有自己的 memory，不混用

## 跨 worktree / 跨窗口的进程安全

**背景**：多个 Claude 窗口/worktree 可能同时在同一台机器上跑实验。默认假设其他人的进程也在跑。

### 铁律：杀 Python 训练进程前必须三重验证

不能只看 cmdline 开头匹配就 kill。必须全部核实：
1. **完整 cmdline**（含 `-u`、`-O`、`-X` 等 flag，不同启动方式 flag 不同）
2. **ELAPSED time**（`ps -o etime` on Mac/Linux；`tasklist /V` on Windows）—— 如果比你刚启动的时间长，不是你的
3. **CWD**（`lsof -p <PID> | grep cwd` on Mac/Linux；`handle.exe` or PowerShell on Windows）—— 两个 worktree 跑同名脚本 CWD 不同

Mac 侧详细技术指引见 `~/.claude/projects/.../memory/feedback_process_kill_safety.md`。

### worktree 窗口的默认假设

当你在 **worktree 里**（`.claude/worktrees/<name>/`）工作：
- **默认假设主窗口（main 分支）也在跑长任务**（训练、实验、数据处理）
- 看到一个 "孤儿进程" / "没人认领的 python 训练"，**默认它是主窗口的**
- 在 kill 之前先问用户，而不是事后报告
- 宁可漏杀（孤儿进程稍后人工清理）也不可错杀（误杀用户的实验 = 丢数据 + 丢时间）

### 启动长任务的规范

- ✅ 直接 shell 里 `nohup python ... > log 2>&1 &`（单层 backgrounding，清晰；Windows 用 `Start-Process` 或 `pythonw ... &`）
- ❌ **不要**把 Claude 的 `run_in_background=true` 和 shell 的 `nohup ... &` 叠加（双层 backgrounding 会让 Claude wrapper 重复 spawn）
- 启动后立刻 `ps -p $! -o pid,etime`（或 Windows 等效）确认 PID 真的在跑，记下来
- 在 log 文件名里带时间/参数（例如 `runs_williams_d4_v3_8x400_coeff1_seed1.log`）方便识别

### 跨窗口协调（推荐）

当你开多个窗口工作时，有个简单协调方案：
- **主窗口**：长任务 / 主线实验（不轻易 kill）
- **worktree 窗口**：新代码 / 探索性实验（失败了可以 kill）
- 两边都更新 memory，让后来的会话能 grep 看到"谁跑什么"
- 主窗口的 PID 写在 memory / MEMORY.md 里（带时间戳 + 参数），worktree 看到能识别

## Session 对话记录保护

- **`~/.claude/projects/...` 目录里的 `.jsonl` 是宝贵的原始对话记录，不是临时文件**
- 清理 worktree 时，**默认只清**：
  - `<repo>/.claude/worktrees/<name>/` 磁盘目录
  - `claude/<name>` git 分支
- **默认不清** `~/.claude/projects/<path>--claude-worktrees-<name>/` 里的 session 目录
- 如果用户明确说要清 session 目录，执行前必须问："要先备份里面的 .jsonl 对话记录吗？"
- 备份位置建议：`~/Documents/claude_archive/<日期>/`（或 Windows 用户的等效位置）
- 原则：**分支和 worktree 可重建，对话记录删了就没了**

## 输出长度控制

- **默认简短**：状态更新一句话，技术细节进 commit message 或 memory，不在对话里展开
- 用户问"做了什么"→ 列 bullet，不写段落
- 用户问"为什么"→ 给原因，不给背景故事
- 只有用户明确要求"详细解释"才展开

## Runner 脚本编写规则（May-5 2026 教训）

**教训 1：config.py 路径在 import 时构建，post-import 改 dict 是 no-op**

- `config.model_path` 在 `import config` 时就已经用默认值固化
- 任何 runner 覆盖 `fatigue_dict`（umax / n_cycles 等）后，**必须手动重建**：
  ```python
  config.model_path             = HERE / Path(_dir_name)
  config.trainedModel_path      = config.model_path / "best_models/"
  config.intermediateModel_path = config.model_path / "intermediate_models/"
  ```
- 参考模板：`run_baseline_umax.py`（main branch，May-4 2026 bugfix 版）
- ❌ 禁止用 `config.savefolder_name = arch`——该变量从未被 config.py 读取

**教训 2：Producer 端的 runner 脚本必须与 Dev 同步**

- Producer（Taobo / Windows）在本地加的 `run_*.py` 必须同步到 Dev（Mac）并 commit 进 branch
- Dev 修了某个 runner → 必须显式通知 Producer pull 或就地覆写
- 判断是否同步的最简检查：`grep "BUGFIXED\|May-[0-9]" run_*.py`

**教训 3：Checkpoint resume 必须做防御检查**

- `source/model_train.py` 已内置两层防御（commit `427ebe7` + `87f3c0e`）：
  1. 恢复 `_x_tip_history` 后检查 crack_length >= right boundary → ABORT
  2. 保存/恢复 `_frac_detected / _frac_cycle / _frac_confirm_remaining`
- 新写的 training loop 或 runner 若需要 resume，必须复现这两层

## Related docs

- `docs/git_workflow.md` — 完整多机协作规则（本文件的 authoritative 展开）
- `docs/shared_research_log.md` — 跨机研究日志（通信通道）
- 各机器 `~/.claude/projects/<path>/memory/` — 各自本地 memory（不进 git）
- **Mac only**: 项目父目录 `CLAUDE.md` — Mac-specific 绝对路径 + 定期清理命令
