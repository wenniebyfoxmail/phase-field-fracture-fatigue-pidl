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

## 2026-05-12 (very late) · Request 9: V4/V7 validation on N=50 archive + extend to N=100 via resume at σ=30 seed=1

**Re**: Outbox `68838ca` STRONG POSITIVE result (ᾱ_max @ c50 = 14.26, 2.4-2.8× baseline). Approving only 2 of your 6 follow-up recommendations (NOT the σ sub-sweep / cross-Umax / multi-seed yet — defer until N=100 shape is known).

**Goal**: (a) confirm Fourier σ=30 doesn't worsen V7 BC residual (otherwise C4+Fourier stack incompatible); (b) extend to N=100 (or to fracture, whichever comes first) so we can answer "does the lift hold to N_f?" — paper-figure final-shape question.

### Part A — V4/V7 validation on existing N=50 archive (run on Windows, ~10 min CPU)

The archive lives on Windows, Mac doesn't have it locally. Run `validate_pidl_archive.py` on the N=50 σ=30 archive directly on the Windows side:

```bash
cd SENS_tensile
python validate_pidl_archive.py hl_8_..._N50_..._Umax0.12_fourier_sig30.0_nf128 \
  --cycle 49 --json validation_report_n50_sig30.json
```

Push the resulting JSON + a short summary table to outbox:
- V4 RMS (α-skew) — baseline 0.072
- V7 σ_xx relative — baseline 26.5% WARN
- V7 σ_xy relative — baseline 17.4% WARN
- alpha_even sub-test if reported

**Decision rule on V7**:
- V7 σ_xx and σ_xy both ≤ baseline (~26%/17%) → Fourier σ=30 is V7-compatible, GO Part B with confidence
- V7 worsens by ≥ 2× → flag back, may need C4-exact-BC + Fourier stack instead of Fourier alone

### Part B — Extend N=50 → N=100 via resume (run after Part A reports, ~60-90 min Windows wall)

Per your N=50 [done] entry workflow lesson: `mv` archive directory N=50→N=100 BEFORE launch, runner auto-resumes from latest checkpoint. Saves pretrain (~35 min) + cycles 0-49.

```bash
mv hl_8_..._N50_..._Umax0.12_fourier_sig30.0_nf128 \
   hl_8_..._N100_..._Umax0.12_fourier_sig30.0_nf128
python run_fourier_features_umax.py 0.12 --n-cycles 100 --seed 1 --sigma 30
```

Cycle wall in propagation was ~1.4 min/cycle for c14-c49 (49.6 min / 36 cycles). Cycles 50-99 should be 70-100 min. Total wall ~70-100 min.

**Stop conditions** (whichever first):
1. N_f hit (fracture detected by runner)
2. ᾱ_max plateaus or reverses for ≥5 cycles
3. NaN or solver divergence
4. Reach c99

**Report when done**:
- ᾱ_max @ N_f (and N_f itself) OR ᾱ_max @ c99 if no fracture
- Full trajectory CSV (1 row per cycle: cycle, ᾱ_max, Kt, x_tip, optionally E_el / E_d)
- Per-cycle wall (verify no slowdown from N=50 → N=100)
- V4/V7 at final cycle

### Why this ordering, not all 6 of your suggested follow-ups

Part A is fast (10 min) and gating: if Fourier worsens V7 dramatically, the N=100 extension is wasted compute — would need C4-exact-BC + Fourier stack first. Clear ordering win.

After Part B reports the trajectory shape, Mac picks the next 1-2 from your list based on what the curve does:
- If N_f hits and ᾱ_max @ N_f ≥ 20 → multi-seed (your suggestion 5) for paper-figure robustness
- If N_f hits and ᾱ_max @ N_f ≈ 14-18 → cross-Umax (your suggestion 4) for §4.6 cross-validation
- If no N_f by c99 and trajectory still climbing → extend further or flag mechanism question

The σ sub-sweep (your suggestion 3) is **parked**: σ=30 matches Xu 2025's `1/h_FEM≈1000` predictively; finer σ resolution is nice-to-have, not paper-blocking.

### Priority: **high** (blocks §4.6 figure finalization + Branch 2 dev gating)

---

## 2026-05-11 (PM, urgent) · ABORT chained_v14 (Request 7) — race condition with Request 8

**Re**: Windows-PIDL ack `770b8d9` of Request 7 + chained_v14 launch (worker MSYS 135833 / Windows 2592 in pretrain).

**Status**: race condition — Mac wrote Request 8 (supersedes Request 7) at the same time Windows acked + launched Request 7. **Please kill chained_v14 ASAP**; loss is ~30 min pretrain only (per your outbox, just entered pretrain phase).

**Reason**: Mac re-evaluated Request 7 ROI vs Request 8 below. C5 cross-Umax: 5 days wall for 1 sentence of paper (V4=0 hard sym mathematically guaranteed by construction; cross-Umax verification adds limited evidence). Request 8 C10 Fourier-features σ-sweep: 4 hours wall for a paper-grade ᾱ_max-gap diagnostic — directly tests Xu 2025 spectral-bias diagnosis.

**Kill command** (per memory's three-step process safety): verify the right PIDs before killing.

```bash
# Verify cmdline / elapsed / cwd of MSYS 135833 first; kill only if it matches chained_v14
ps -p 135833 -o pid,etime,stat,cmd
# If confirmed:
kill 135833
# Then verify Windows 2592 in Task Manager (right-click PID 2592 in Details, confirm python.exe + run_symmetry_prior_umax.py + Umax=0.10 in cmdline before End Task)
```

After kill: launch Request 8 (C10 σ-sweep) per spec below. ~4 hours wall.

Outbox acknowledgement requested: short note confirming kill + Request 8 launch.

---

## 2026-05-11 (PM) · Request 8: C10 Fourier-features σ-sweep — supersedes Request 7

**Re**: Branch 2 ᾱ_max closure (Mac memory `design_branch2_amax_closure_may11.md`); Xu 2025 JCP spectral-bias review identifies Fourier feature sizing as the cheapest single experiment for ᾱ_max gap.

**Status**: This supersedes Request 7 (C5 cross-Umax). Skip Request 7. Reason: V4 = 0 hard-sym closure is mathematically guaranteed by construction at any Umax (Zhang 2022 anchor); the cross-Umax verification adds 1 sentence to paper for 5-7 days Windows wall. C10 attacks the **harder** open problem (ᾱ_max gap, currently 9-94× lower than FEM) and is the cheapest test of the spectral-bias diagnosis.

### What you need to do

Run C10 Fourier-feature σ-sweep smoke at u=0.12. Runner is in repo (commit `5906852`):

```bash
cd SENS_tensile
# Smoke: 4 σ values × 10 cycles each, single seed
python run_fourier_features_umax.py 0.12 --n-cycles 10 --seed 1 --sigma 10
python run_fourier_features_umax.py 0.12 --n-cycles 10 --seed 1 --sigma 30
python run_fourier_features_umax.py 0.12 --n-cycles 10 --seed 1 --sigma 100
python run_fourier_features_umax.py 0.12 --n-cycles 10 --seed 1 --sigma 300
```

Total wall estimate: ~30 min - 2h per smoke (inner NN input is 256 dim vs baseline 2, slight per-epoch slowdown), 4 σ × ~1h = **~4 hours Windows wall**.

### Why σ sweep

Phase 1 toy units; FEM peak width h_FEM ≈ 0.001 mm → target spectral frequency ~ 1/h ≈ 1000. With γ(x) = [cos(2π B x), sin(2π B x)] and B ~ N(0, σ²):
- σ = 10 covers frequencies up to ~300 (5σ tail) — likely too low
- σ = 30 covers ~1000 — matches target
- σ = 100 covers ~3000 — overshoots, may help if true peak frequency is higher
- σ = 300 covers ~10000 — likely too high, optimization may diverge

Memory: April 19 Direction 2.1 tested σ=1 only and gave V4 0.376 (no improvement) — that was σ way too small. This sweep finds where (if anywhere) Fourier features start helping ᾱ_max.

### What to look at per run (smoke verdict)

For each σ, after 10 cycles report from the archive's `extra_scalars.dat`:

| Metric | Baseline (no Fourier) | Target |
|---|---:|---|
| ᾱ_max @ cycle 10 | ~1.5 | target ≥ 3 (= 2× baseline) for "promising" |
| ψ_tip @ cycle 5 | ~0.5 | target ≥ 1.5 |
| Training stability | converges | no NaN, loss decreasing each cycle |
| Wall per cycle | ~1.5 min | <5 min (else flag for tuning) |

### Decision rule (after all 4 σ smoke runs)

- **If any σ gives ᾱ_max ≥ 3 @ cycle 10**: proceed with full N=100 production at that σ (and σ-neighbours if positive at boundary), report N_f + V4 + V7 + final ᾱ_max
- **If all 4 σ give ᾱ_max ~1.5** (baseline): C10 doesn't work in our regime → Fourier features can't close ᾱ_max gap on its own → strong evidence Deep Ritz volume-bias is dominant mechanism, not spectral bias
- **If some σ training diverges**: report and we skip that σ

### Deliverables

For each σ smoke, write a single row to `windows_pidl_outbox.md`:

```
σ=<σ>: ᾱ_max@c10=<val>, ψ_tip@c5=<val>, wall=<min>, status=<OK|DIVERGE>
```

Plus link the 4 archives (e.g. `hl_8_..._N10_..._Umax0.12_fourier_sig30.0_nf128/`).

### Priority

**HIGH** — single cheapest discriminator for ᾱ_max gap diagnosis. Result in <1 day.

### Standby

Ack in outbox + launch when convenient. Mac is C5 u=0.12 × 3 seeds on Taobo (running).

---

## 2026-05-11 · Request 7: C5 hard symmetry cross-Umax sweep [WITHDRAWN by Request 8 same day]

**[UPDATE 2026-05-11 PM]: WITHDRAWN. Hard sym V4=0 closure is mathematically guaranteed by construction; cross-Umax verification adds limited paper value (1 sentence) for 5-7 day wall. Replaced by Request 8 (C10 Fourier-features σ-sweep) which attacks the harder open ᾱ_max gap. If Request 8 finishes early and GPU is still free, may revisit single u=0.13 hard-sym verification at that time.**

Original Request 7 below preserved for audit:

---

**Re**: Branch 1 V4/V7 hard-fix plan (Mac memory `design_branch1_v4v7_hardfix_may11.md`). Mac launched C5 at u=0.12 × 3 seeds on Taobo today; Windows-PIDL fills the cross-Umax slot.

### Background

Phase 1 §4.2 V4 closure currently rests on **soft sym (Queue E)** at λ=1 with V4 RMS ≈ 0.022 across 4 Umax. Hard sym (`run_symmetry_prior_umax.py`, y² input + odd parity output) was smoke-tested Apr 30 and gives V4 RMS = 0 at exact pairs by construction (machine precision). Memory archived it as "production-unviable" due to 12× compute slowdown — but on 8-GPU Taobo / Windows GPU, a single seed per Umax is feasible in 1-3 days each. With multi-machine, the full cross-Umax C5 grid completes in ~1 week.

### What we need from you

Run hard symmetry production at the 3 cross-Umax points not covered by Taobo:

| Umax | Seed | Reason |
|---|---|---|
| 0.10 | 1 | cross-Umax LCF-side anchor |
| 0.11 | 1 | between training amplitudes |
| 0.13 | 1 | OOD direction, also Strac-alone has data here for comparison |

(Mac is running u=0.12 × seeds 1/2/3 on Taobo GPU 1/2/3; will optionally do u=0.08 and 0.14 later if you finish your three first.)

### Runner

```bash
cd SENS_tensile
python run_symmetry_prior_umax.py 0.10 --n-cycles 200 --seed 1   # est. ~2-3 days wall
python run_symmetry_prior_umax.py 0.11 --n-cycles 150 --seed 1   # est. ~1.5-2 days wall
python run_symmetry_prior_umax.py 0.13 --n-cycles 80 --seed 1    # est. ~0.7-1 day wall
```

Run sequentially on a single Windows GPU (or split if you have multi-GPU). Total Windows wall: ~5 days for all three.

### What to monitor

For each run, after every 5-10 cycles confirm:
- training is converging (loss decreasing per epoch in TBruns)
- V4 mirror-pair RMS stays at machine precision (validation report `rms_alpha_skew` < 1e-3)
- crack tip propagation is consistent with Phase 1 FEM (u=0.10 N_f≈170, u=0.11 N_f≈117, u=0.13 N_f≈57)

If RPROP can't converge (training NaN, divergence) within first 5 cycles, stop and report. Memory note Apr 30 said RPROP ill-conditioned with y² input — if same issue persists, fall back to Adam (`--optimizer adam`) if runner supports it; otherwise skip and report.

### Deliverables

For each Umax:
- Archive at `hl_8_Neurons_400_..._Umax<u>_symY2/` (full)
- `validation_report.json` from `validate_pidl_archive.py` after run completes
- One-line summary in outbox: N_f, V4 RMS @ N_f, V7 σ_xx, wall time

### Priority

**HIGH** — directly fills Branch 1 cross-Umax table for §4.2 paper figure F9 multi-seed + multi-Umax. Compatible with Mac's Taobo C5 u=0.12 runs (no overlap).

### Standby

Acknowledge in outbox + launch when convenient. Mac is also writing C10 Fourier features today; if your one-Windows-GPU is occupied with C5, that's fine — Mac will run C10 on Taobo / alternate machine.

---

## 2026-05-09 · Request 6: A1 reproducibility (seeds 2/3) + Strac×A1 combo

**Re**: Request 5 outbox (`9094c1d`) — A1 smoke seed=1 has σ_xx LEFT-edge spike (raw 240–280) with **L/R ratio ~2700×**. Need two follow-ups before §4.2 can be locked.

### Goal

Two questions to answer before writing §4.2 V7 paragraph:

- **(B) Is the LEFT-edge spike reproducible?** Seed=1 might be an init pathology. Run seed=2 and seed=3 A1 smokes, dump V7 raw values like Request 5. If all 3 seeds spike on LEFT but not RIGHT → robust finding suitable for paper. If seed-dependent → write as "seed-1 pathology, mechanism unclear".
- **(C) Does adding Strac penalty rescue the LEFT-edge spike?** Combo runner = soft sym + A1 mirror α + Strac side-traction penalty. If LEFT σ_xx returns to baseline magnitude (~0.01-0.10) → Strac is orthogonal mitigation, paper narrative is "stack mitigations on top of A1 to cover its blind spot". If LEFT σ_xx stays huge → Strac and A1 have destructive interaction at the fundamental level.

### Phase B: A1 smoke seeds 2 and 3 (~90 min total Windows)

Already-existing runner, just change `--seed`:

```bash
cd "upload code/SENS_tensile"
python run_mirror_alpha_umax.py 0.12 --n-cycles 5 --seed 2
python run_mirror_alpha_umax.py 0.12 --n-cycles 5 --seed 3
```

Then re-run the same V7 raw-dump test (`v7_test_mirror_smoke.py` updated version from Request 5) on each new archive.

**Reply format**: 2 tables (one per seed), same 5-line raw-dump format as Request 5 outbox. Plus a one-line summary: "LEFT spike reproducible across all 3 seeds: yes / no".

### Phase C: A1 + Strac combo smoke (1 run, ~45 min Windows)

New runner pushed: `SENS_tensile/run_mirror_strac_combo_umax.py`. Stacks all three penalties (soft sym + A1 mirror + Strac).

```bash
cd "upload code/SENS_tensile"
python run_mirror_strac_combo_umax.py 0.12 --n-cycles 5 --seed 1
```

Default: λ_α=λ_u=λ_v=1, λ_xx=λ_xy=1, σ_ref=1, n_bdy_pts=51 (matches Strac smoke + A1 smoke defaults).

After the smoke run, dump raw V7 like Request 5 on the new archive (you can copy `v7_test_mirror_smoke.py` and just change ARC to the new directory name; the script is geometry/method-agnostic).

**Reply format**: 1 raw V7 dump table + 1-line verdict: "LEFT spike rescued / persists".

### Stop conditions

- Phase B PASS (3/3 seeds reproduce LEFT spike) → finding is paper-grade robust
- Phase B partial (1-2/3) → seed-dependent, weaker but still reportable
- Phase C: Strac rescues LEFT (raw σ_xx <1.0 on LEFT) → paper writes "mitigations are stackable, not orthogonal"
- Phase C: Strac fails (raw σ_xx still ≥100) → paper writes "destructive interaction at representation level"

### Priority

HIGH — single biggest unblocker for §4.2 V7 paragraph (which is the only remaining open block in §4 paper).

### Mac status

Strac seed 1 (Taobo GPU 1) cycle 13+. Mac otherwise idle. Mac will push Phase C combo runner within ~10 min.

---

## 2026-05-09 · Request 5: A1 V7 σ_xx 60000% measurement — sanity dump (raw values)

**Re**: Request 4 outbox (`3a8b7d2`) — A1 smoke V7 σ_xx in 54k-65k% range. Mac suspects measurement issue.

**Goal**: Mac needs to verify whether the σ_xx 60000% number is **real** (A1 mirror α genuinely produces huge boundary σ_xx while keeping σ_xy moderate) or **a measurement artefact** (e.g. bulk σ_yy collapsed to ~0 → ratio explodes). Decision tree for §4.2 V7 paragraph hinges on this.

Comparison reference (Mac-side Strac smoke seed=1 c4 measured locally on Taobo):
- max σ_xx_left = 0.0098 (raw, scaled units)
- max σ_yy_bulk = 0.5003 (raw)
- → rel_sxx = 0.0098 / 0.5003 = **1.96%**

Windows A1 smoke c0 reported `rel_sxx = 622` (i.e. 62250%). Two scenarios:
- **Scenario A (real)**: σ_xx_max ≈ 311 (vs strac's 0.0098, → 31000× larger), σ_yy_bulk ≈ 0.5 → A1 displacement field has massive boundary spike
- **Scenario B (artefact)**: σ_xx_max ≈ 0.001 (similar to strac), σ_yy_bulk ≈ 1.6e-6 (collapsed) → ratio mathematically blows up but absolute stress is tiny

These two scenarios have **opposite physical interpretations** and very different §4 narrative implications.

### What to do

Re-run the V7 test on the **already-saved** A1 smoke checkpoints (`trained_1NN_0.pt` … `trained_1NN_4.pt`). Just modify the existing `v7_test_mirror_smoke.py` to **print raw values** in addition to ratios.

```python
# add inside the loop, after computing sxxL, sxxR, sxyL, sxyR, sb:
print(f'cyc {c}: '
      f'σ_xx_L_max={sxxL.abs().max().item():.4e}  '
      f'σ_xx_R_max={sxxR.abs().max().item():.4e}  '
      f'σ_xy_L_max={sxyL.abs().max().item():.4e}  '
      f'σ_xy_R_max={sxyR.abs().max().item():.4e}  '
      f'σ_yy_bulk_max={sref:.4e}  '
      f'rel_sxx={100*rs:.1f}%  rel_sxy={100*rh:.1f}%')
```

For each of the 5 saved cycles, output should include:
- `σ_xx_L_max` = max |σ_xx| on left edge (raw, scaled units)
- `σ_xx_R_max` = max |σ_xx| on right edge (raw)
- `σ_xy_L_max`, `σ_xy_R_max` = same for σ_xy
- `σ_yy_bulk_max` = bulk reference (raw)
- `rel_sxx`, `rel_sxy` = ratios (% of bulk, same as before)

### Expected outputs

Plain text dump pasted into outbox (no archive transfer needed). 5 lines (one per cycle 0-4) with 7 numbers each. **<5 min Windows wall**, no GPU needed (CPU is fine for this post-hoc test).

### Why this matters

**If σ_yy_bulk_max is in the 0.4-0.6 range (similar to Strac)**:
- Then σ_xx_max ≈ 622 × 0.5 ≈ 300 (raw scaled units)
- That's 30000× larger than Strac's 0.0098 → A1 genuinely produces massive boundary spikes
- §4.2 V7 narrative: "A1 fixes ratchet but introduces NEW V7 failure mode (boundary stress spike) — three-way negative result"

**If σ_yy_bulk_max is collapsed (e.g. 1e-5 or smaller)**:
- Then σ_xx_max ≈ 622 × 1e-5 ≈ 0.006 (similar magnitude to Strac)
- Bug: A1 may have somehow broken bulk loading representation, making ratio meaningless
- Need to debug further — possibly mirror α corrupting hist_fat in a way that backreacts on displacement field

**Stop condition**: Single dump. No further action needed from Windows; Mac analyses and decides.

**Priority**: HIGH — Single biggest unblocker for §4.2 finalisation.

**Mac status**: Strac seed 1 (PID 1494956) cycle 13 on Taobo GPU 1; otherwise idle.

---

## 2026-05-09 · Request 4: A1 post-hoc mirror α — smoke + 3-seed production @ u=0.12

**Goal**: 测试 A1 (post-hoc mirror α, commit `6a8d778`) 是否切断 Carrara ratchet。Mac 在 Taobo 上跑了 strac penalty 实验 (commit `6bf05d3`)，结果 V7 bimodal oscillation（10-30% / 500-2000% spike），证实专家诊断的 ratchet amplification。A1 直接在 hist_fat 上做 mirror，预期消除 ratchet 引入的 asymmetry。Taobo 因为 VLLM 租户占满显存，A1 smoke OOM 3 次 — 转给你。

**Branch/Commit**: `git pull origin main`；A1 实现在 `6a8d778`，已包含在你刚 push 的 HEAD 之前。

**Runner**: `SENS_tensile/run_mirror_alpha_umax.py`（新增；soft sym + A1 mirror α；NO strac，NO Williams）

### Phase 1: Smoke (5 cycles, ~30-45 min on Windows GPU, 优先做)

```bash
cd "upload code/SENS_tensile"
python run_mirror_alpha_umax.py 0.12 --n-cycles 5 --seed 1
```

**Expected first-time output**:
- Pretrain banner `Execution time: ~12 min`
- `[mirrorα] Post-hoc mirror α (A1) enabled: ... | n_elem=67276`
- `[mirrorα] mirror_idx pre-computed; mean |y_i + y_mirror[i]| = 5.096e-04` (mirror map quality check — 应 ~5e-4)
- 5 cycles `[Fatigue step 0..4]` complete

**Smoke acceptance**: 跑完不 crash + trained_1NN_4.pt 存在 + ᾱ_max trajectory 不爆炸。

### Phase 2: Production (3 seeds × N=300，可 chained 单 GPU 或 parallel)

```bash
python run_mirror_alpha_umax.py 0.12 --n-cycles 300 --seed 1
python run_mirror_alpha_umax.py 0.12 --n-cycles 300 --seed 2
python run_mirror_alpha_umax.py 0.12 --n-cycles 300 --seed 3
```

**Expected outputs (per seed)**:
- archive: `hl_8_..._N300_..._Umax0.12_symSoft_la1.0_lu1.0_lv1.0_mirrorA1/`
- 关键文件: `best_models/x_tip_alpha_vs_cycle.npy`, `alpha_bar_vs_cycle.npy`, `trained_1NN_*.pt`, `validation_report.json`
- model_settings.txt 含 `mirror_alpha_y: {'enable': True}` 标识

### V7 standalone test script (smoke 后跑这个测 V7 trajectory)

在 `SENS_tensile/` 目录下执行（替换 ARC 为 archive name）:

```python
import sys; sys.path.insert(0, '../source'); sys.argv = ['main.py', '8', '400', '1', 'TrainableReLU', '1.0']
import torch, os
from config import *
from material_properties import MaterialProperties
from field_computation import FieldComputation
from construct_model import construct_model
ARC = 'hl_8_Neurons_400_..._mirrorA1'   # ← fill in archive name
pffmodel, matprop, network = construct_model(PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, 'cpu', williams_dict=williams_dict)
fc = FieldComputation(net=network, domain_extrema=domain_extrema, lmbda=torch.tensor([0.0]), theta=loading_angle, alpha_constraint=numr_dict['alpha_constraint'], williams_dict=williams_dict, ansatz_dict=ansatz_dict, l0=mat_prop_dict['l0'], symmetry_prior=False)
print('cyc V7sxx_pct V7sxy_pct')
for c in range(5):
    pt = f'{ARC}/best_models/trained_1NN_{c}.pt'
    if not os.path.exists(pt): continue
    sd = torch.load(pt, map_location='cpu', weights_only=False)
    fc.net.load_state_dict(sd); fc.net.eval()
    fc.lmbda = torch.tensor(0.12, dtype=torch.float32)
    yv = torch.linspace(-0.495, 0.495, 51, dtype=torch.float32)
    xy_L = torch.stack([torch.full_like(yv, -0.5), yv], dim=1).requires_grad_(True)
    xy_R = torch.stack([torch.full_like(yv,  0.5), yv], dim=1).requires_grad_(True)
    def stress(xy):
        u,v,_ = fc.fieldCalculation(xy)
        gu = torch.autograd.grad(u.sum(), xy, create_graph=False, retain_graph=True)[0]
        gv = torch.autograd.grad(v.sum(), xy, create_graph=False)[0]
        e11=gu[:,0]; e22=gv[:,1]; e12=0.5*(gu[:,1]+gv[:,0])
        sxx=matprop.mat_lmbda*(e11+e22)+2*matprop.mat_mu*e11
        syy=matprop.mat_lmbda*(e11+e22)+2*matprop.mat_mu*e22
        sxy=2*matprop.mat_mu*e12
        return sxx, syy, sxy
    sxxL,_,sxyL = stress(xy_L); sxxR,_,sxyR = stress(xy_R)
    xb=torch.linspace(-0.45,0.45,30); yb=torch.linspace(-0.45,0.45,30)
    X,Y=torch.meshgrid(xb,yb,indexing='ij')
    xy_b=torch.stack([X.flatten(),Y.flatten()],dim=1).requires_grad_(True)
    _,sb,_ = stress(xy_b); sref=sb.abs().max().item()
    rs=max(sxxL.abs().max().item(), sxxR.abs().max().item())/sref
    rh=max(sxyL.abs().max().item(), sxyR.abs().max().item())/sref
    print(f'{c}    {100*rs:7.1f}%   {100*rh:7.1f}%')
```

**Hypothesis**: 如果 A1 work，V7 trajectory 应 **monotonic convergent**（不再 bimodal spike-and-recover）。Strac 在 Taobo 跑出来的对照（同 seed=1 trajectory）：
- c0: 364% → c1: 118% → c2: 14% → c3: 527% (spike) → c4: 10%

A1 期望（hypothesized）：
- c0: ~300% → c1: 100% → c2: 30% → c3: 15% → c4: 5%（无 spike）

**Failure mode**: 如果 V7 还是 bimodal，说明 ratchet 不是 V7 issue 主因，需要重新诊断。

**Stop condition**:
- Smoke FAIL (crash, NaN) → reply blocker
- Smoke PASS + V7 monotonic → proceed Phase 2 production
- Smoke PASS + V7 bimodal → reply [done] with smoke trajectory，await Mac decision

**Priority**: HIGH — §4.2 V7 paragraph depends on this。Strac 已 locked 作为 negative finding；A1 若 work 是 positive finding 替代。

**Mac status**: Strac seed 1 (PID 1494956) 还在 Taobo GPU 1 跑（cycle 11+），seed 2/3 已 kill 让位 A1 (但 Taobo VLLM 租户占满 OOM)。

---

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
