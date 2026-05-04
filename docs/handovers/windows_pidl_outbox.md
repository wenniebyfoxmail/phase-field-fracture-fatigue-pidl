# Windows-PIDL Outbox (Windows → Mac)

**Direction**: Windows-PIDL → Mac-PIDL  
**Purpose**: Windows 回传执行状态、结果、blocker、问题。  
**Counterpart**: `windows_pidl_inbox.md` (Mac → Windows, task requests)

---

## Format rules

1. **Append newest at top**
2. Every entry starts with:
   ```
   ## YYYY-MM-DD · <type>: <one-line summary>
   ```
   Types: `[ack]`, `[progress]`, `[done]`, `[blocker]`, `[question]`
3. Entry body:
   - **Re**: 对应 inbox 的 Request # 
   - **Status**: 当前进度
   - **Key numbers**: 关键结果数值（如有）
   - **Next**: Windows 下一步打算做什么
4. Append-only，不修改已有 entry

---

## Entries

[暂无]
