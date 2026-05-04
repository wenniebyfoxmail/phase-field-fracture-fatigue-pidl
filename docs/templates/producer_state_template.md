# Producer State (Windows-PIDL)

**用途**：Windows 当前执行态摘要。相当于 Windows 版的 successor handoff。
**规则**：保持 ≤ 30 行，只反映当前态。

---

## Currently Running

| Job | Runner | Started | Log | ETA |
|---|---|---|---|---|
| [描述] | `run_xxx.py` | YYYY-MM-DD HH:MM | `runs_xxx.log` | ~Xh |

## Queue (from inbox)

- Request #N: [summary] — priority: [H/M/L]

## Recently Completed

- Request #N: [one-line result] — see outbox entry YYYY-MM-DD

## Blockers

- [如有]
