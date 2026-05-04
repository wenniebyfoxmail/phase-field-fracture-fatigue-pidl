# Windows-FEM Inbox (Mac → Windows-FEM)

**Direction**: Mac-PIDL → Windows-FEM (GRIPHFiTH)  
**Purpose**: Mac 派发 FEM reference run 任务给 Windows-FEM。  
**Counterpart**: `windows_fem_outbox.md` (Windows-FEM → Mac, status + results + questions)

---

## Format rules

1. **Append newest at top** of "Active Requests" section
2. Every request starts with:
   ```
   ## YYYY-MM-DD · Request <N>: <one-line summary>
   ```
3. Request body must contain:
   - **Goal**: 一句话说明这个 FEM run 要证明/测量什么
   - **INPUT file**: 哪个 .m 文件，关键参数
   - **Mesh**: 用哪个 mesh / 需要新生成
   - **Expected outputs**: 输出放哪、回传什么（VTK/mat/log）
   - **Acceptance criteria**: Mac 如何判断 pass/fail
   - **Priority**: high / medium / low
4. 取消或修改已有 request：append `### [update] YYYY-MM-DD` 子条目
5. 完成的 request 移到底部 "Archive" 区

---

## Active Requests

[暂无]

---

## Archive

[暂无]
