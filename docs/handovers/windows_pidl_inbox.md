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

## 2026-05-07 · Request 3: soft symmetry cross-Umax verification @ u=0.10 / 0.11 / 0.13

**Goal**: 验证 soft symmetry penalty (commit 90f2297) 在非 training Umax 下也保持 N_f match within ±10%。Phase 1 paper §4 reframe 的 "framework consistency cross-Umax" claim 需要 cross-Umax 的 soft sym 数据点（目前只有 u=0.12 N_f=85 一个点）。Mac 已派 seed=2/3 to Taobo (Queue E) 做 multi-seed evidence；你这边可以并行做 cross-Umax evidence。

**Branch/Commit**: `git pull origin main`，HEAD 包含 commit `90f2297` (soft sym 实现) 即可。

**Runner**: `SENS_tensile/run_symmetry_soft_umax.py`（已存在；λ_α=λ_u=λ_v=1.0 for paper consistency）

**3 个 run，按顺序跑（chained，~3.5h × 3 = ~10-12h）**:

```bash
cd SENS_tensile

PYTHONIOENCODING=utf-8 python -u run_symmetry_soft_umax.py 0.11 \
    --n-cycles 300 --seed 1 --lam-alpha 1.0 --lam-u 1.0 --lam-v 1.0 \
    > soft_sym_u011_la1_seed1.log 2>&1

PYTHONIOENCODING=utf-8 python -u run_symmetry_soft_umax.py 0.13 \
    --n-cycles 200 --seed 1 --lam-alpha 1.0 --lam-u 1.0 --lam-v 1.0 \
    > soft_sym_u013_la1_seed1.log 2>&1

PYTHONIOENCODING=utf-8 python -u run_symmetry_soft_umax.py 0.10 \
    --n-cycles 300 --seed 1 --lam-alpha 1.0 --lam-u 1.0 --lam-v 1.0 \
    > soft_sym_u010_la1_seed1.log 2>&1
```

> u=0.13 用 N=200 因为 FEM N_f=57，预期 PIDL ~60-70 cycles 就 fracture
> u=0.11 FEM N_f=117 → N=300 充裕；u=0.10 FEM N_f=170 → N=300 也够

**Expected outputs**:
- 3 个 archive `hl_8_..._Umax{0.10,0.11,0.13}_symSoft_la1.0_lu1.0_lv1.0/`
- 3 个 log file 含 N_f
- 回传 outbox：N_f 比对 FEM 表 + V4 RMS (last cycle)

**Acceptance criteria** (per paper §4 cross-Umax claim)：
- N_f within ±10% of FEM N_f at each Umax
  - u=0.10: FEM=170, PIDL acceptable [153, 187]
  - u=0.11: FEM=117, PIDL acceptable [105, 129]
  - u=0.13: FEM=57, PIDL acceptable [51, 63]
- V4 RMS at fracture cycle ~ 0.02 (similar to u=0.12 0.022)

**Background**: Mac 完成 soft sym λ=1.0 production @ u=0.12 seed=1 (commit 90f2297, Taobo PID 2888934 already done; N_f=85 vs baseline 82, V4 RMS 0.022, wall 3.76h). Layer 3 red-team flagged "single-seed at single Umax" 是 §4 弱点。Mac 派 multi-seed (seed=2/3 @ u=0.12) 到 Taobo Queue E；Windows 这边做 cross-Umax 是 orthogonal evidence。

**Reply expected**:
- ack 时附 PID + log paths
- 每 run done 时附 N_f + ᾱ_max @ N_f + V4 RMS @ last cycle (用 `python validate_pidl_archive.py` 即可)

**Priority**: medium-high — 3 个 cross-Umax 数据点是 §4 cross-Umax claim 的 robustness evidence，写 LaTeX 之前 nice-to-have。Tier C 全完，K=40 retry 还在 Taobo 跑（不抢你 GPU）。

**ETA**: 10-12h sequential (Windows GPU)。无需赶夜，正常工作时段跑也行。

---

## 2026-05-06 · Request 2: tipw rerun @ u=0.12 (Tier C audit follow-up)

**Goal**: 重新生成干净的 tipw_b2.0_p1.0 archive（带 model_settings.txt + 经过 May-4 fracture-detect resume guard 的 model_train），让它在 `audit_archive_settings.py` 下 PASS。原 Mac Apr-15 archive 没写 settings，且早于 bugfix。

**Branch/Commit**: `git pull origin main` 即可（含新写的 `run_tipw_umax.py`）

**Runner**: 新写的 `SENS_tensile/run_tipw_umax.py`，已仿 `run_psi_hack_umax.py` 的模式（含 `rebuild_disp_cyclic` + 手动 path rebuild + `model_settings.txt` 写出）

```bash
cd SENS_tensile
PYTHONIOENCODING=utf-8 python -u run_tipw_umax.py 0.12 \
    --beta 2.0 --power 1.0 --start-cycle 1 --n-cycles 300 \
    > run_tipw_umax_Umax0.12.log 2>&1 &
```

**Expected output**:
- archive：`hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_tipw_b2.0_p1.0/`
- 含 `best_models/checkpoint_step_*.pt`, `best_models/x_tip_alpha_vs_cycle.npy`, `model_settings.txt`, `alpha_snapshots/`
- log file
- N_f, ᾱ_max @ N_f, ᾱ_max @ stop 数字

**Stop condition**: fracture detected by model_train guard，archive 落盘完整；或 N=300 跑完都未断裂（也是有效结果）。ETA ~3-4h Windows GPU。

**Why retry**: tipw 是 Direction 3 的 NEGATIVE result（Apr-15 N_f≈baseline），paper §3 仍要列。原 archive 缺 `model_settings.txt` + x_tip history，audit FAIL。

**Reply expected**:
- ack 时附上 PID + log path
- done 时附 N_f / ᾱ_max @ N_f 表 + archive 路径

**Priority**: low — Tier C 其余 5 个 method rerun 在 Taobo GPU 1+7 跑（11-14h overnight），这个并不卡 paper main results；先做完更重要的 oracle u=0.10/0.11 ship 等再做。

**Background**: Mac 5/6 用 audit_archive_settings.py 扫了 SENS_tensile/ 全部 46 个 archive，发现 3 个 known-bad（已标 `_failed`/`_incomplete` 等），1 个 psiHack warm-start（Apr-23, paper caveat 即可），剩下 17 个 WARN 大多是 missing settings.txt。tipw 是其中之一。

---

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
