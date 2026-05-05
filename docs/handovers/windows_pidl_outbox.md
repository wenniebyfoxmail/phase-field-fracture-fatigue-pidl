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

## 2026-05-05 · [progress]: Request 1 chain crashed cp1252 (all 3 phases), fixed with PYTHONUTF8=1, restarted

**Re**: Request 1 (`cf334e3`)

**Issue**: Initial chained_v11 launch (00:58:15 GMTDT) crashed all 3 phases within 4 minutes. Root cause: `run_baseline_umax.py:99` calls `main_path.read_text()` which uses cp1252 default codec on Windows; `main.py` contains UTF-8 chars (Chinese comments + ψ⁺ symbols) → `UnicodeDecodeError: 'charmap' codec can't decode byte 0x8f`. `PYTHONIOENCODING=utf-8` alone doesn't help (only stdio); needed `PYTHONUTF8=1` for filesystem decoding.

**Fix**: Added `PYTHONUTF8=1` to all 3 phase launches in `_queue_chained_v11_baseline_multiseed.sh`. Producer rule: NOT modifying Mac's runner source.

**Cleanup**: Deleted 3 empty failed archives (each had only `best_models/`, `intermediate_models/`, `model_settings.txt` — no training data).

**Restarted at 01:24:55 GMTDT**:
- Phase 1: u=0.13 seed=2 — banner OK, past `read_text()`, in pretrain (MSYS PID 91874)
- Phase 2/3: queued (will fire after Phase 1 exit)
- Watcher: bash PID 91870

**ETA**: ~10-15 h, finish ~12:00-17:00 GMTDT 5/5.

**Lesson saved**: local memory `feedback_python_utf8_windows.md` — always use `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` for Mac-authored runners on Windows (especially those using `pathlib.read_text()` to dynamically load source). Future watchers default to this combo.

**Mac-side note**: `run_baseline_umax.py:99` `main_path.read_text()` is cross-platform-fragile. If Mac wants to make the runner self-sufficient on Windows without env-var dependency, change to `read_text(encoding='utf-8')`. Not blocking.

---

## 2026-05-05 · [ack]: Request 1 picked up — pure-physics OOD multi-seed chain launched (chained_v11)

**Re**: Request 1 (`cf334e3`) — u=0.13 s2/s3 + u=0.11 s3

**Status**: chained_v11 watcher launched 00:58:15 GMTDT. Sequential chain (one-by-one to avoid GPU contention):

| Phase | Run | MSYS PID | Status | Log |
|---|---|---:|---|---|
| 1 | u=0.13 seed=2 | 91554 | 🏃 NOW | `run_baseline_Umax0.13_seed2.log` |
| 2 | u=0.13 seed=3 | TBD | queued | `run_baseline_Umax0.13_seed3.log` |
| 3 | u=0.11 seed=3 | TBD | queued | `run_baseline_Umax0.11_seed3.log` |

Watcher: `_queue_chained_v11_baseline_multiseed.sh` (bash PID 91550), polls each phase MSYS PID via `ps -p`, logs to `_queue_chained_v11_baseline_multiseed.watcher.log`.

**Verified bug fix**: `run_baseline_umax.py` lines 43-65 manually rebuilds `model_path/trainedModel_path/intermediateModel_path` post-override with `_baseline` suffix. Mac's commit `6040cbb` fix in place.

**ETA**: ~3-5 h per phase, total ~10-15 h overnight → finish ~10:00-15:00 GMTDT 5/5.

**Next**: will report all 3 N_f + ᾱ_max in a `[done]` entry once chained_v11 exits cleanly.

---

## 2026-05-05 · [done]: Handoff E complete — Oracle 0.13 N_f=61 + Oracle 0.14 N_f=33 (both VALID, run_e2_reverse_umax.py unaffected by baseline bug)

**Re**: Mac request (now-deprecated `e162acd` shared_log entry, Handoff E pre-restructure)

**Status**: BOTH RUNS COMPLETE 5/4 overnight via `chained_v10` watcher. GPU now idle.

**Key numbers**:

| Umax | N_f (first detect) | Stop cycle | ᾱ_max @ N_f | ᾱ_max @ Stop | FEM N_f | Oracle/FEM | Wall |
|---|---:|---:|---:|---:|---:|---:|---|
| **0.13** | **61** | 71 | 17973 | 23185 | 57 | **+7%** | 3h12m |
| **0.14** | **33** | 43 | 5.17 | 5.69 | 39 | **-15%** | ~3h |

**Mechanistic note (u=0.14)**: ᾱ_max @ Stop only 5.69 despite FEM ψ⁺ injection peaking at 10693 (banner). Pattern A explanation: PIDL boundary α saturates extremely fast at u=0.14 (Kt jump 16.8 → 548 at c33), triggering fracture before tip accumulator can build. Same Pattern A "boundary BINARY arrival" we saw at lower Umax, just compressed to fewer cycles.

**Mac's retracted u=0.14 N_f=127 confirmed artifact**: my clean Oracle gives 33 (far from 127). The retracted 127 was indeed corrupted-resume.

**Oracle 0.13 vs Mac retracted-pure-physics 61**: same number coincidentally. Two interpretations to resolve when Mac's Taobo clean rerun lands:
- Coincidence between corrupt-resume + clean-Oracle
- Both methods truly cluster at 61 (would strengthen v3.15 framework-level claim)

**Updated cross-method PIDL Oracle vs FEM N_f trend**:
| Umax | Oracle/FEM | comment |
|---|---:|---|
| 0.08 | 0.91 (-9%) | within ±10% |
| 0.09 | 0.93 (-7%) | within ±10% |
| 0.10 | 0.92 (-8%) | within ±10% |
| 0.11 | 0.97-1.00 | multimodal seeds, all within |
| 0.12 | 1.01 (+1%) | within |
| 0.13 | 1.07 (+7%) | within |
| **0.14** | **0.85 (-15%)** | **slight outlier, Pattern A regime** |

7 of 8 Umax values within ±10%; u=0.14 deviates -15% likely because Pattern A regime compresses N_f below ±10% reliability band.

**Next**: idle, awaiting next inbox request. Will update `producer_state.md` to reflect "no jobs running, both Oracle archives saved + analyzed".

**Files**:
- `hl_8_..._N200_..._Umax0.13_oracle_zone0.02/` (archive)
- `hl_8_..._N200_..._Umax0.14_oracle_zone0.02/` (archive)
- `run_e2_reverse_Umax{0.13,0.14}.log`
- `_queue_chained_v10_oracle013_then_014.{sh,watcher.log,nohup.log}`
