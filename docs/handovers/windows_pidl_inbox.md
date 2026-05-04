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

## 2026-05-05 · Request 1: pure-physics OOD multi-seed — u=0.13 seeds 2&3 + u=0.11 seed3

**Goal**: 补齐 OOD 泛化表格缺失的 seed。u=0.13 seed1 给出 N_f=71（first=61），需确认 seed 间方差；u=0.11 补 seed3 凑足 3-seed set。

**Branch/Commit**: `git pull origin main`，HEAD = `a365598`

**Runner**: `run_baseline_umax.py`（已含 bug fix，safe to use）

按顺序跑（一个接一个，用 `&&` chain）：
```
python3 run_baseline_umax.py 0.13 --n-cycles 200 --seed 2
python3 run_baseline_umax.py 0.13 --n-cycles 200 --seed 3
python3 run_baseline_umax.py 0.11 --n-cycles 200 --seed 3
```

**Expected outputs**:
- 3 个 archive 目录（命名含 `Seed_2/3`，`Umax0.13/0.11`，`baseline`）
- 回传每个 run 的 N_f（first detect）+ ᾱ_max @ N_f
- 回传到 `windows_pidl_outbox.md`

**Stop condition**: 所有 3 个 run 完成（fracture 或 200 cycles），archive 保存完整。

**Priority**: high（OOD 表格必须有多 seed 才能写误差 bar）

---

## Archive

[暂无]
