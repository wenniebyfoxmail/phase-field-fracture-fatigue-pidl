# Windows-PIDL Inbox (Mac → Windows)

**Direction**: Mac-PIDL → Windows-PIDL  
**Purpose**: Mac 派发具体训练/实验任务给 Windows。  
**Counterpart**: `windows_pidl_outbox.md` (Windows → Mac, status + results + questions)

---

## Format rules

1. **Append newest at top** of "Active Requests" section
2. Every request starts with:
   ```
   ## YYYY-MM-DD · Request <N>: <one-line summary>
   ```
3. Request body must contain:
   - **Goal**: 一句话说明这个 run 要证明/测量什么
   - **Branch/Commit**: `git pull` 到哪个 commit
   - **Runner**: 用哪个脚本，什么参数
   - **Expected outputs**: 预期结果放哪、回传什么
   - **Stop condition**: 什么时候算完成/失败
   - **Priority**: high / medium / low
4. 取消或修改已有 request：append `### [update] YYYY-MM-DD` 子条目
5. 完成的 request 移到底部 "Archive" 区

---

## Active Requests

[暂无]

---

## Archive

[暂无]
