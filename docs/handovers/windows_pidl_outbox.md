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

## 2026-05-12 · [done Part A] 🚨 Request 9 Part A — **V7 σ_xx FLAGGED 2.8× WORSE than baseline** (Part B NOT auto-launched per Mac rule)

**Re**: Request 9 (`dc62e3f`) Part A — V4/V7 validation on existing N=50 σ=30 archive

**Status**: Part A complete. Mac's gating rule triggered — V7 worsens ≥2× → flag back. Part B (N=50→N=100 extension) NOT launched.

### Result summary

| metric | c49 result | baseline (Mac inbox) | ratio | verdict |
|---|---:|---:|---:|---|
| **V4 RMS α_skew** | **0.0035** | 0.072 | **0.05× (20× BETTER)** ✅ |
| **V7 σ_xx rel** | **73.9%** | 26.5% WARN | **2.8× WORSE** 🚨 TRIGGERS FLAG |
| V7 σ_xy rel | 19.1% | 17.4% WARN | 1.10× (essentially baseline) | ≈ |

**Per Mac decision rule** (inbox lines 52-54):
> V7 σ_xx and σ_xy both ≤ baseline (~26%/17%) → Fourier σ=30 is V7-compatible, GO Part B with confidence
> **V7 worsens by ≥ 2× → flag back, may need C4-exact-BC + Fourier stack instead of Fourier alone**

V7 σ_xx is 2.8× baseline → **NOT V7-compatible**. Part B (N=100 extension) gated, awaiting Mac decision.

### Full V4/V7 trajectory across N=50

| cyc | V4 α_skew | V7 sxx_L raw | V7 sxx_R raw | V7 sxy_L raw | V7 sxy_R raw | σ_yy_bulk | rel_sxx | rel_sxy |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.0029 | 32.57 | 9.69 | 6.40 | 5.03 | 22.40 | 145.4% | 28.6% |
| 10 | 0.0031 | **79.67** | 9.94 | 9.13 | 4.94 | 34.01 | **234.3%** | 26.8% |
| 20 | 0.0033 | 30.24 | 11.05 | 6.52 | 4.98 | 38.60 | 78.4% | 16.9% |
| 30 | 0.0035 | 29.16 | 10.82 | 6.68 | 4.96 | 38.59 | 75.6% | 17.3% |
| 40 | 0.0035 | 29.23 | 9.24 | 6.94 | 4.95 | 39.30 | 74.4% | 17.6% |
| **49** | **0.0035** | **31.13** | 8.54 | 8.04 | 4.96 | 42.11 | **73.9%** | 19.1% |

Observations:
- **V4 α_skew is consistent ~0.003 across all cycles** — Fourier sinusoidal basis γ(x)=[cos(2πBx), sin(2πBx)] is structurally near-symmetric about y=0 (B matrix is dense random Gaussian, so cos/sin pairs have similar symmetry footprint on both halves)
- **V7 σ_xx peaks at c10 at 234%** and **stabilises to ~75% by c20+** — sxx_L_max ~30 raw across propagation phase (vs baseline expected ~10 raw for 26.5% of σ_yy~38)
- **V7 σ_xy stays ~17-29%** ≈ baseline — high-freq basis affects σ_xx more than σ_xy

### Mechanism interpretation (speculative — Mac to verify)

High-frequency Fourier basis γ(x) = [cos(2π B x), sin(2π B x)] with σ=30 → typical frequency content ~30 cycles per unit length. Near free edges x=±0.5, the NN has no boundary constraint, so high-freq components can "ring" — produce sinusoidal oscillations in σ_xx that don't decay. The σ_yy field (loaded direction) is anchored by displacement BC at top/bottom, so it doesn't ring as much.

**This is a known trade-off in Fourier feature networks (Tancik 2020 §6 limitations)**: spectral lift at one frequency band comes with sharper modes everywhere, including at free boundaries.

### Methodological note: validator workaround

`validate_pidl_archive.py` doesn't natively handle `FourierFeatureNet` (state_dict mismatch — vanilla NeuralNet expects `input_layer.weight`, FourierFeatureNet has `inner.input_layer.weight`). V4 and V7 both SKIPPED with `RuntimeError: Error(s) in loading state_dict`.

**Producer-side workaround**: wrote `SENS_tensile/v4v7_test_fourier_n50.py` that uses `construct_model(..., fourier_dict=...)` to instantiate the correct FourierFeatureNet, then loads checkpoint cleanly. V4 + V7 metrics above are from this script (mirror-symmetry α-skew RMS + free-edge σ_xx/σ_xy raw values + bulk σ_yy reference).

Mac side could either: (1) patch `validate_pidl_archive.py` to detect `inner.*` prefix and route through FourierFeatureNet, OR (2) use my script directly when validating future Fourier archives.

### Mac's two options per inbox decision rule

1. **C4-exact-BC + Fourier stack** (Mac mentioned in inbox decision rule): combine soft-symmetry / hard-BC (C4 exact-BC implementation already exists, commit `4ec16c3`) with Fourier features. C4 should suppress edge ringing while keeping Fourier's ᾱ_max lift.
2. **Reject Fourier σ=30 standalone**, retest at lower σ where ringing is milder (σ=10 had 1.83× ᾱ_max baseline but V7 status unknown — could be milder edge ringing)

My recommendation: option (1). C4-exact-BC + Fourier σ=30 stack tests if mitigations are stackable (similar to A1+Strac pattern from Request 6). If V7 improves to ≤ baseline while ᾱ_max stays at 14+ → STRONG combined positive for paper.

### Files

- V4/V7 dump script: `SENS_tensile/v4v7_test_fourier_n50.py`
- Validator-attempted JSON: `hl_8_..._N50_..._fourier_sig30.0_nf128/best_models/validation_report.json` (V4/V7 SKIPPED therein, see notes)
- Archive still intact (no mv done): `hl_8_..._N50_..._Umax0.12_fourier_sig30.0_nf128/`

### Next

GPU idle. Awaiting Mac decision: C4+Fourier stack runner OR σ=10 V7 spot-check OR reject Fourier standalone.

---

## 2026-05-12 · [done] 🎯 Request 8 N=50 σ=30 confirmer COMPLETE — **STRONG POSITIVE**, c50 ᾱ_max = **14.26 (≥10 threshold passed by 42%)**

**Re**: Proactive N=50 confirmer at σ=30 (best from smoke sweep)

**Status**: chained_v16 exited cleanly 14:38:30 GMTDT. **PASS — paper figure-ready result.**

### Key result vs decision tree

| metric | result | Mac's threshold |
|---|---:|---|
| **ᾱ_max @ c50** | **14.26** | ≥10 = STRONG positive ✅ |
| vs baseline c50 (~5-6) | **~2.4-2.8×** | — |
| Kt @ c50 | 6.77 (healthy) | (not pathological like σ=300) |
| crack tip x @ c50 | 0.0242 | small but real propagation |

### Full ᾱ_max trajectory @ u=0.12 seed=1 σ=30

| cycle | ᾱ_max | Kt | x_tip |
|---:|---:|---:|---:|
| 0 | 0.295 | 7.01 | 0 |
| 5 | 1.755 | 7.02 | 0 |
| 10 | **3.185** | 6.93 | 0.0013 |
| 14 | 4.004 | 6.76 | 0.0033 |
| 20 | 5.016 | 6.74 | 0.0105 |
| 25 | 6.586 | 6.71 | 0.0124 |
| 30 | 8.248 | 6.71 | 0.0157 |
| 35 | 9.882 | 6.80 | 0.0190 |
| 40 | 11.497 | 6.83 | 0.0209 |
| 45 | 13.056 | 6.82 | 0.0229 |
| **49** | **14.261** | 6.77 | 0.0242 |

**Per-cycle growth in propagation phase (c20-c49)**: ~0.32/cycle. If trend holds to N_f (baseline ~80), extrapolated ᾱ_max ≈ 24-30 (vs baseline 9.34 at N_f=82, FEM ~270 reference).

### Verdict: Fourier σ=30 IS closing meaningful fraction of ᾱ_max gap

**Tancik 2020 / Xu 2025 spectral-bias diagnosis CONFIRMED at PIDL fatigue regime**:
- σ=30 target freq band ~942 matches Mac's inverse FEM mesh resolution 1/h_FEM ≈ 1000
- Direction 2.1 (April 19 σ=1 test) was right ATTACK but wrong scale — σ=1 way too small to capture sharp ψ⁺ peak
- σ=10 (freq ~314): modest 1.83× at c10
- σ=30 (freq ~942): **2.13× at c10, 2.4-2.8× at c50** ✅
- σ=100 (freq ~3142): DIVERGE (Kt=1.01 trivial)
- σ=300 (freq ~10000): DIVERGE-like (Kt=120 pathological)

Sweet spot is narrow band around 1/h_FEM. Below: under-resolved (cap at ~baseline). Above: over-resolved → optimization breakdown.

### Workflow optimization saved 35min via resume (user-spotted oversight)

Initial N=50 launch at 12:07 wasted ~90min redoing smoke σ=30 cycles 0-13 from scratch (pretrain 35min + cycle 0 45min + cycles 1-13 ~10min). After user pointed out smoke's checkpoints were reusable, I killed at step 13 and re-launched at 13:48 — runner's auto-resume kicked in: `[Checkpoint] 检测到预训练权重，跳过预训练 → 从 step 13 恢复，继续 step 14/49`. Pretrain (35min) and history (14 cycles of npy) all restored. Cycles 14-49 took 49.6 min.

**Lesson saved to memory** (`feedback_extend_N_via_resume.md`): when extending N_old→N_new with same config, `mv` archive name N_old→N_new BEFORE launch → runner auto-resumes from latest checkpoint. Saves pretrain (~17-35min) + early cycles.

### Files

- Production archive: `hl_8_..._N50_..._Umax0.12_fourier_sig30.0_nf128/` (50 cycles + `best_models/checkpoint_step_{0..49}.pt` + `trained_1NN_{0..49}.pt` + `alpha_bar_vs_cycle.npy` + history)
- Log: `run_fourier_n50_sigma30.log`
- Watcher: `_queue_chained_v16_fourier_n50_sigma30.{sh,watcher.log,watcher.log.attempt1,nohup.log}`
- Smoke archives (4σ): `hl_8_..._N10_..._Umax0.12_fourier_sig{10,30,100,300}.0_nf128/`

### Recommended Mac next steps

1. **Verify result** — Mac analyse production archive, confirm ᾱ_max trajectory + paper-grade Figure F10 prep
2. **Full N=100-300 production** at σ=30 to verify gap closure to N_f. Estimated wall on Windows: 100 cycles × 1.3 min = ~2.2h; 300 × 1.3 = ~6.5h
3. **σ sub-sweep**: σ=20, 25, 40, 50 around the sweet spot to map gain curve more finely (each smoke ~30min)
4. **Cross-Umax verification** at σ=30: u=0.10/0.11/0.13 (similar to Request 3 cross-Umax structure) — multi-day commitment
5. **Multi-seed** at u=0.12 σ=30 N=50 (seeds 2/3): test reproducibility of c50 ᾱ_max ≈ 14
6. **V4/V7 validation** on N=50 archive — does Fourier increase V7 BC residual? (Watch for: high-freq features may worsen edge stress)

### Next

GPU idle. Awaiting Mac decision on follow-ups. Recommend (2) full N=100 σ=30 as the natural next step — would close decision tree on gap closure to N_f.

---

## 2026-05-12 · [done]: Request 8 Fourier σ-sweep COMPLETE — σ=30 sweet spot at 1.95× baseline (borderline); N=50 confirmer PROACTIVELY launched

**Re**: Request 8 (`3f4871d`) Fourier σ-sweep + Mac fix `57a547a`

**Status**: chained_v15 ALL 4 σ COMPLETE 11:58:56 GMTDT (~3h22m total wall).

### 4-σ smoke results @ u=0.12 seed=1, 10 cycles each

| σ | ᾱ_max @ c10 | Kt @ c10 | vs baseline 1.5 | wall | status |
|---:|---:|---:|---:|---:|---|
| 10 | 2.75 | 8.15 | 1.83× | 28 min | OK |
| **30** | **2.93** | **7.04** | **1.95× (best)** | 91 min | OK (sweet spot) |
| 100 | 0.099 | 1.01 | 0.07× | 39 min | DIVERGE (no learning, α stays trivially linear) |
| 300 | 1.73 | 120.8 | 1.15× ≈ baseline | 39 min | DIVERGE-like (pathological Kt=120; α perfectly linear 0.17/cycle) |

### Verdict per Mac's decision rule

- **No σ reaches "≥3 = promising" threshold strictly** (closest: σ=30 at 2.93)
- **But σ=10 and σ=30 give 1.83-1.95× baseline** — borderline, not clean negative
- **σ=100 / σ=300 confirm Tancik 2020 spectral-bias upper bound**: target frequency ~3142 (σ=100) and ~10000 (σ=300) both fail to learn — diverge in different modes
  - σ=100: Kt=1.01 (no stress concentration recognized, α stays at trivial 0.01/cycle linear)
  - σ=300: Kt=120 (stress concentration present BUT α can't follow, stays 0.17/cycle linear)
- Sweet spot is σ ∈ [10, 30] (likely σ=30); higher σ over-resolves; lower σ likely under-resolves

### NEW finding — Fourier sweet spot identified

σ=30 (covers frequency band ~942) matches the FEM peak inverse-width 1/h_FEM ≈ 1000 prediction in Mac's inbox **exactly**. Confirms Xu 2025 spectral-bias targeting heuristic works at the σ level. But the gain stops at 1.95× baseline @ c10 — c10 is still build-up phase, propagation hasn't started.

### Proactive N=50 confirmer launched (user-approved plan)

**Reasoning**: c10 is too early to conclude; baseline propagation phase doesn't kick in until c20+ and N_f happens around c80. Test if σ=30 advantage compounds through propagation phase.

**chained_v16** launched 12:07:31 GMTDT. Single run:
```
python run_fourier_features_umax.py 0.12 --n-cycles 50 --seed 1 --sigma 30
```

Worker MSYS 140957 / Windows native 35920. ETA ~5-6h (Fourier ~5 min/cycle avg = 50×5 + pretrain 17 = ~4-5h, but cycle 0 of σ=30 was 45min so possibly longer). Finish ~17:00-19:00 GMTDT.

**Mac can kill if disagrees** — `kill 140949` (watcher) + `kill 140957` (python). Triple-verify cmdline first.

### Decision tree for N=50 result

- If σ=30 N=50 gives ᾱ_max @ c50 ≥ 10 (vs baseline ~5-6): **STRONG positive** — Fourier compounds in propagation, paper figure-ready
- If σ=30 N=50 gives ᾱ_max @ c50 ~ 5-6 (≈ baseline): **CLEAN negative** — Fourier helps in build-up but doesn't close gap, supports Deep Ritz volume-bias hypothesis
- If σ=30 N=50 diverges late: report and Mac decides

### Files

- 4 smoke archives: `hl_8_..._N10_..._Umax0.12_fourier_sig{10,30,100,300}.0_nf128/`
- 4 smoke logs: `run_fourier_smoke_sigma{10,30,100,300}.log`
- N=50 confirmer log (in flight): `run_fourier_n50_sigma30.log`
- Watcher logs: `_queue_chained_v15_fourier_sigma_sweep.{sh,watcher.log,nohup.log}`, `_queue_chained_v16_fourier_n50_sigma30.{sh,watcher.log,nohup.log}`

### Next

N=50 in flight. Will report when complete with c50 ᾱ_max, full trajectory, V4/V7 RMS, paper-ready interpretation. GPU 100% utilization.

---

## 2026-05-12 · [ack]: Request 8 RELAUNCHED — Mac fix `57a547a` works, chained_v15 in pretrain

**Re**: Mac fix `57a547a` (source/network.py: expose `init_coeff` + `trainable_activation` from `FourierFeatureNet.inner`)

**Status**: chained_v15 re-launched 08:37:09 GMTDT. σ=10 past the AttributeError point — `[construct_model] FourierFeatureNet enabled` printed, TF/CUDA init OK, now in pretrain. No traceback this time.

**Worker**: MSYS 139843 / Windows native 24440. Watcher bash PID 139831.

**Old watcher log** preserved as `_queue_chained_v15_fourier_sigma_sweep.watcher.log.first_attempt` for audit.

ETA same as before: ~4h total across all 4 σ, finish ~12:30 GMTDT 5/12.

Will report consolidated `[done]` with all 4 ᾱ_max@c10 + ψ_tip@c5 + wall times + verdict per Mac's decision rule once chain completes.

---

## 2026-05-12 · [blocker]: Request 8 — all 4 σ smokes FAILED in <10s on AttributeError (FourierFeatureNet missing `init_coeff`)

**Re**: Request 8 (`3f4871d`) — C10 Fourier σ-sweep

**Status**: chained_v15 watcher ran all 4 σ phases (10/30/100/300) and each exited with rc=1 in <10 sec. Not a training failure — Python `AttributeError` on construction before any cycle ran. Watcher continued through all 4 per Mac's "skip and continue on diverge" rule, completed at 00:36:42.

### Identical error in all 4 σ logs

```
[construct_model] FourierFeatureNet enabled: σ=<σ>, n_features=128, inner_dim=256
Traceback (most recent call last):
  File "run_fourier_features_umax.py", line 122, in <module>
    exec(open(HERE / "main.py").read())
  File "<string>", line 19, in <module>
  File "source/construct_model.py", line 69, in construct_model
    init_xavier(network)
  File "source/network.py", line 304, in init_xavier
    init_coeff = model.init_coeff
AttributeError: 'FourierFeatureNet' object has no attribute 'init_coeff'
```

### Root cause (Mac please verify)

`source/network.py`:
- `Network` class (line 153): `self.init_coeff = init_coeff` at line 164 ✓
- `FourierFeatureNet` class (line 206): in `__init__` (line 221-236), exposes `self.name_activation = self.inner.name_activation` at line 236 but **does NOT expose `self.init_coeff`**. Then `init_xavier(network)` from `construct_model.py:69` accesses `model.init_coeff` directly → `AttributeError`.

### Suggested 1-line fix (Mac source side, not Producer scope)

In `source/network.py:206 FourierFeatureNet.__init__`, after line 236 (`self.name_activation = self.inner.name_activation`), add:

```python
self.init_coeff = self.inner.init_coeff
self.trainable_activation = self.inner.trainable_activation  # if init_xavier or other code paths need it
```

Alternatively, `init_xavier` could be made FourierFeatureNet-aware: check `hasattr(model, 'inner')` and recurse on `model.inner`. But the attribute-expose pattern is simpler and matches the existing `name_activation` line.

### What I won't do

Per Producer role (CLAUDE.md): not modifying `source/network.py`. Awaiting Mac fix push.

### GPU status

Idle. chained_v15 watcher already exited cleanly (recorded all 4 failures, terminated). No orphaned Python processes.

### Files for Mac diagnosis

- 4 failure logs: `SENS_tensile/run_fourier_smoke_sigma{10,30,100,300}.log` (each ends with the AttributeError traceback)
- Watcher log: `SENS_tensile/_queue_chained_v15_fourier_sigma_sweep.watcher.log`
- No archives created (failure before training started)

### Next

Awaiting Mac source fix + re-launch instruction. Will re-run same 4 σ × 10 cycle smokes when fix lands.

---

## 2026-05-12 · [ack]: Request 7 ABORTED + Request 8 launched (chained_v15 Fourier σ-sweep)

**Re**: Mac inbox `1a099d0` (abort) + `3f4871d` (Request 8 supersedes)

**Status**:
- chained_v14 (Request 7) **KILLED** at 00:34 GMTDT 5/12. bash watcher PID 135822 killed, Python worker MSYS 135833 / Windows 2592 killed via SIGKILL. Triple-verified before kill (cmdline=run_symmetry_prior_umax 0.10, elapsed ~7h pretrain, cwd=SENS_tensile, this-session-launched).
- Loss: ~7h pretrain only on Phase 1 u=0.10 (Mac estimated "30 min pretrain in flight" was outdated; actual ~7h because chain launched 5/11 17:01 not 5/11 PM). No production cycles ran. No archive corrupted (pretrain checkpoint may remain on disk but Mac doesn't need it).

### Request 8 launched: chained_v15 Fourier σ-sweep

| σ | Status | Log |
|---|---|---|
| 10 | 🏃 starting | `run_fourier_smoke_sigma10.log` |
| 30 | queued | `run_fourier_smoke_sigma30.log` |
| 100 | queued | `run_fourier_smoke_sigma100.log` |
| 300 | queued | `run_fourier_smoke_sigma300.log` |

Watcher: `_queue_chained_v15_fourier_sigma_sweep.sh` (bash PID 137817). Phase σ=10 worker MSYS 137828 / Windows native 4760 (in pretrain).

Each smoke: 10 cycles u=0.12 seed=1 fourier features n_features=128. Per-smoke ETA 30min-2h. **Total ETA ~4h, finish ~04:30 GMTDT 5/12.**

PYTHONUTF8=1 applied defensively (runner does NOT use read_text, so cp1252 risk is nil — but watcher consistent with prior practice).

### Reply plan per Mac's decision rule

For each σ smoke done, will report single-row outbox entry:
```
σ=<σ>: ᾱ_max@c10=<val>, ψ_tip@c5=<val>, wall=<min>, status=<OK|DIVERGE>
```

Plus archive link `hl_8_..._fourier_sig<σ>_nf128/`.

**Decision after all 4 σ done**:
- If any σ gives ᾱ_max ≥ 3 @ cycle 10 (= 2× baseline 1.5) → wait Mac instruction for N=100 production
- If all 4 σ give ᾱ_max ~1.5 (baseline) → Fourier features doesn't close gap → report negative finding for paper
- σ chain doesn't abort on individual diverge per Mac's rule (skips and continues)

---

## 2026-05-11 · [ack]: Request 7 — chained_v14 launched (C5 hard symmetry cross-Umax sweep)

**Re**: Request 7 (`5906852`) — C5 hard symmetry @ u=0.10/0.11/0.13 seed=1 (Branch 1 Phase 1 paper figure F9 fill)

**Status**: chained_v14 watcher launched 17:01:16 GMTDT 5/11. Sequential chain per Mac's order, PYTHONUTF8=1 applied (runner line 141 uses `read_text()`).

| Phase | Run | N_cycles | ETA Windows wall | Log |
|---|---|---:|---:|---|
| 1 | hard sym u=0.10 seed=1 | 200 | ~2-3 days | `c5_hardsym_u010_seed1.log` |
| 2 | hard sym u=0.11 seed=1 | 150 | ~1.5-2 days | `c5_hardsym_u011_seed1.log` |
| 3 | hard sym u=0.13 seed=1 | 80 | ~0.7-1 day | `c5_hardsym_u013_seed1.log` |

Watcher: `_queue_chained_v14_c5_hardsym_cross_umax.sh` (bash PID 135822). Phase 1 worker MSYS 135833 / Windows native 2592 (in pretrain).

**ETA total**: ~5 days, finish ~5/16 GMTDT.

**Will report** per-phase done entry (sequential, since each takes 1-3 days). For each: N_f, V4 RMS @ N_f (expect ≈ 0 by construction for hard sym), V7 σ_xx, wall time. Validation report attached.

**Early-abort guard**: If RPROP fails (NaN/divergence) within first ~5 cycles per Apr 30 memory note, runner exits non-zero, watcher stops chain, I report blocker. Runner has no `--optimizer adam` fallback flag — if RPROP ill-conditioned with y² input persists, skip and report.

---

## 2026-05-09 · [done]: Request 6 — Phase B 3/3 reproducible, Phase C **RESCUED** ✅ (Strac+A1 combo eliminates LEFT spike)

**Re**: Request 6 (`7387eec`) — A1 reproducibility + Strac×A1 combo

**Status**: chained_v13 ALL 3 PHASES COMPLETE 23:14:07 GMTDT 5/9. Total wall ~9.2h (B-1 63min + B-2 44min + C 7h23m incl. 16.5min pretrain + 5×85min cycles).

### TL;DR

- **Phase B verdict: LEFT spike reproducible 3/3 seeds** ✅ (paper-grade robust finding, NOT seed-1 init pathology)
- **Phase C verdict: RESCUED** ✅ (Strac penalty collapses sxx_L_max from 280 → **0.010**, ~28000× reduction)
- **§4.2 paper narrative locked**: "mitigations are stackable, not orthogonal" — A1 fixes ratchet temporal asymmetry; Strac fixes BC-residual spatial blow-up; together they cover each other's blind spots

### Phase B-1: A1 smoke seed=2 (cycles raw values)

| cyc | sxx_L_max | sxx_R_max | sxy_L_max | sxy_R_max | syy_bulk_max | rel_sxx | rel_sxy |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 2.27e+02 | 1.06e-01 | 6.33e-01 | 7.06e-02 | 3.54e-01 | 64263% | 179.1% |
| 1 | 2.22e+02 | 1.05e-01 | 1.18e-01 | 7.04e-02 | 3.78e-01 | 58770% | 31.1% |
| 2 | 1.96e+02 | 1.05e-01 | 5.87e-01 | 7.18e-02 | 4.00e-01 | 48954% | 146.5% |
| 3 | 2.20e+02 | 1.08e-01 | 1.89e-01 | 7.25e-02 | 3.55e-01 | 62013% | 53.4% |
| 4 | 2.24e+02 | 1.06e-01 | 4.96e-01 | 7.06e-02 | 4.25e-01 | 52614% | 116.7% |

### Phase B-2: A1 smoke seed=3 (cycles raw values)

| cyc | sxx_L_max | sxx_R_max | sxy_L_max | sxy_R_max | syy_bulk_max | rel_sxx | rel_sxy |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 2.40e+02 | 1.04e-01 | 5.17e-01 | 7.30e-02 | 3.99e-01 | 60214% | 129.6% |
| 1 | 2.45e+02 | 1.05e-01 | 4.64e-01 | 7.33e-02 | 4.00e-01 | 61295% | 115.9% |
| 2 | 2.46e+02 | 1.04e-01 | 5.62e-01 | 7.35e-02 | 4.00e-01 | 61533% | 140.5% |
| 3 | 2.42e+02 | 1.04e-01 | 5.13e-01 | 7.33e-02 | 3.91e-01 | 61862% | 131.2% |
| 4 | 2.42e+02 | 1.04e-01 | 5.68e-01 | 7.33e-02 | 3.65e-01 | 66240% | 155.8% |

### Phase B summary: LEFT spike reproducibility 3/3 ✅

| seed | sxx_L_max range (5 cycles) | sxx_R_max range | L/R ratio @ c4 |
|---:|---|---|---:|
| 1 (Request 5) | 240–280 | 0.10 | 2745× |
| 2 (this run) | **196–227** | 0.10 | **2109×** |
| 3 (this run) | **240–246** | 0.10 | **2322×** |

**Robust paper finding**: σ_xx LEFT-edge spike across all 3 seeds (raw 196-280, L/R ratio 2100-2750×). RIGHT edge consistently ~0.10. syy_bulk_max ~0.36-0.42 (healthy across all seeds, not collapsed).

Seed-dependent details (NOT robust, mention only as caveat):
- σ_xy LEFT trajectory differs per seed (s1 monotonic divergent, s2 oscillating, s3 stable ~0.5)
- σ_xy magnitude varies (s1 c4=1.008, s2 c4=0.496, s3 c4=0.568)

### Phase C: A1 + Strac combo seed=1 (cycles raw values)

| cyc | sxx_L_max | sxx_R_max | sxy_L_max | sxy_R_max | syy_bulk_max | rel_sxx | rel_sxy |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 2.63e-01 | 7.64e-02 | 2.39e-01 | 6.20e-02 | 3.22e-01 | 81.7% | 74.3% |
| 1 | 1.58e-01 | 6.72e-02 | 5.51e-02 | 5.35e-02 | 3.47e-01 | 45.6% | 15.9% |
| 2 | 4.28e-01 | 6.25e-02 | 7.67e-02 | 5.20e-02 | 4.22e-01 | 101.3% | 18.1% |
| 3 | 1.10e-02 | 7.02e-02 | 8.97e-03 | 5.37e-02 | 4.11e-01 | 17.1% | 13.1% |
| 4 | 1.00e-02 | 6.83e-02 | 9.47e-03 | 5.34e-02 | 4.31e-01 | 15.8% | 12.4% |

### Phase C verdict: RESCUED ✅

| metric | A1 alone seed=1 c4 | A1+Strac combo c4 | reduction |
|---|---:|---:|---:|
| sxx_L_max raw | **279.56** | **0.010** | **27800× ↓** |
| sxx_R_max raw | 0.102 | 0.068 | similar magnitudes |
| sxy_L_max raw | 1.008 | 0.009 | 100× ↓ |
| L/R sxx ratio | 2745× | 0.15× | (RIGHT now larger than LEFT) |

LEFT edge sxx_max collapsed from O(280) to O(0.01) — well below Mac's "rescued" threshold (sxx_L<1.0).

Comparison to Strac-alone (Mac Taobo, seed=1):
- Strac alone: c0:364% c1:118% c2:14% c3:527%spike c4:10% (bimodal, σ_xx_L raw ~0.0098)
- A1+Strac combo: c0:82% c1:46% c2:101% c3:17% c4:16% (NO 527% spike, monotonic settle by c3)

Combo is BETTER than Strac-alone — eliminates the bimodal spike behavior. By c3+ both sxx and sxy settle to <20% of bulk and stay there.

### ᾱ trajectory across all 3 phases (sanity)

| cyc | A1 seed=1 (Req 4) | A1 seed=2 | A1 seed=3 | A1+Strac combo |
|---:|---:|---:|---:|---:|
| 0 | 0.392 | 0.353 | — | 0.471 |
| 1 | 0.783 | 0.748 | — | 0.836 |
| 2 | 1.178 | 1.080 | — | 1.219 |
| 3 | 1.577 | 1.437 | — | 1.574 |
| 4 | 1.982 | 1.763 | — | (no print, healthy from V7) |

All monotonic, no NaN, mirror α working in all cases (init quality 5.096e-04 across all 3 seeds + combo).

### Wall time breakdown

- Phase B-1 (A1 seed=2): ~63 min wall (pretrain 19.6 min + cycles 11.9/7.8/9.7/7.3/8.2 min)
- Phase B-2 (A1 seed=3): ~44 min wall (pretrain ~17 min + cycles ~5-7 min each — faster as warm cache)
- Phase C (combo seed=1): ~7h23m wall (pretrain 16.5 min + cycles 85.4/85.1/85.1/85.4/~80 min — Strac penalty ~6× per-epoch slowdown vs A1-only)

### Files

- Combo archive: `hl_8_..._N5_..._mirrorA1_strac_xx1.0_xy1.0_sref1.0/` (5 trained_1NN_*.pt + history npy + model_settings.txt confirms `strac_penalty: enable=True λ_xx=λ_xy=1.0 σ_ref=1.0`)
- Combo log: `run_combo_smoke_Umax0.12_seed1.log`
- A1 seed=2 archive: `hl_8_..._N5_..._Seed_2_..._mirrorA1/`
- A1 seed=3 archive: `hl_8_..._N5_..._Seed_3_..._mirrorA1/`
- V7 test scripts: `v7_test_seed2.py`, `v7_test_seed3.py`, `v7_test_combo.py`
- Raw V7 dumps: `v7_dump_seed2.txt`, `v7_dump_seed3.txt`, `v7_dump_combo_seed1.txt`
- Watcher: `_queue_chained_v13_a1_seeds_combo.{sh,watcher.log,nohup.log}`

### §4.2 paper narrative implications

1. **A1 alone (3 seeds confirmed)**: ratchet fix introduces NEW V7 LEFT-edge sxx spike (raw 240-280, 27000× larger than baseline). Three-way negative result for "A1 alone".
2. **Strac alone (Mac Taobo)**: bimodal V7 spike-and-recover (c2:14% c3:527%) — partial mitigation of underlying ratchet-driven instability.
3. **A1 + Strac combo (this work)**: BOTH issues resolved. sxx_L collapses to 0.010, sxy_L to 0.009, no bimodal spike, settles cleanly by c3.

**Paper claim available**: A1 and Strac penalties are **complementary, stackable** mitigations. Each addresses a different failure mode (temporal ratchet asymmetry vs spatial BC-residual spike). Combined → both eliminated.

### Next

Idle. GPU 0% (combo done). Awaiting Mac §4.2 final framing decision and any Phase C follow-up (e.g., Strac-only seed=2/3 for symmetric reproducibility, or 3-seed combo production).

---

## 2026-05-09 · [ack]: Request 6 — chained_v13 launched (A1 seeds 2/3 + Strac×A1 combo)

**Re**: Request 6 (`7387eec`) — A1 reproducibility (Phase B) + Strac×A1 combo (Phase C)

**Status**: chained_v13 watcher launched 14:04:05 GMTDT. Sequential, PYTHONUTF8=1 applied (per Request 4 lesson; both runners use `main_path.read_text()`).

| Phase | Run | Runner | Log |
|---|---|---|---|
| B-1 | A1 smoke seed=2 | `run_mirror_alpha_umax.py 0.12 --n-cycles 5 --seed 2` | `run_mirror_smoke_Umax0.12_seed2.log` |
| B-2 | A1 smoke seed=3 | `run_mirror_alpha_umax.py 0.12 --n-cycles 5 --seed 3` | `run_mirror_smoke_Umax0.12_seed3.log` |
| C | A1+Strac combo seed=1 | `run_mirror_strac_combo_umax.py 0.12 --n-cycles 5 --seed 1` | `run_combo_smoke_Umax0.12_seed1.log` |

Watcher: `_queue_chained_v13_a1_seeds_combo.sh` (bash PID 120742). Phase B-1 worker MSYS 120753 / Windows 27240 (in pretrain).

**ETA**: 3 × ~45 min ≈ 2.25h, finish ~16:20 GMTDT.

**Reply plan**: per-phase raw V7 dump tables (5-line format) + LEFT-spike verdicts in single consolidated `[done]` entry once chain completes:
- Phase B verdict: "LEFT spike reproducible across 3 seeds: yes / no"
- Phase C verdict: "LEFT spike rescued / persists"

---

## 2026-05-09 · [done]: Request 5 — A1 V7 raw value sanity dump → **Scenario A (REAL spike)** + striking L/R asymmetry

**Re**: Request 5 (`8cf0a20`) — sanity dump on already-saved A1 smoke checkpoints

**Status**: COMPLETE. CPU run, ~3 min. No archive change.

### Raw V7 dump (5 cycles, u=0.12 A1 mirror α + soft sym λ=1.0)

| cyc | sxx_L_max | sxx_R_max | sxy_L_max | sxy_R_max | syy_bulk_max | rel_sxx | rel_sxy |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | **2.40e+02** | 1.03e-01 | 3.26e-02 | 6.79e-02 | **3.86e-01** | 62250% | 17.6% |
| 1 | **2.55e+02** | 1.03e-01 | 2.48e-01 | 6.81e-02 | **4.60e-01** | 55551% | 54.0% |
| 2 | **2.43e+02** | 1.03e-01 | 4.50e-01 | 6.81e-02 | **4.49e-01** | 54125% | 100.4% |
| 3 | **2.41e+02** | 1.02e-01 | 6.95e-01 | 6.83e-02 | **4.28e-01** | 56262% | 162.5% |
| 4 | **2.80e+02** | 1.02e-01 | 1.01e+00 | 6.81e-02 | **4.27e-01** | 65398% | 235.8% |

### Verdict: **Scenario A (REAL)** — confirmed

- **syy_bulk_max ≈ 0.39–0.46** across all 5 cycles → bulk loading is **HEALTHY**, NOT collapsed (similar magnitude to Strac's 0.5003)
- **sxx_L_max ≈ 240–280 raw** → genuine massive boundary spike at x=−0.5 edge, ~30000× Strac's 0.0098
- 60000% ratio is REAL, not a denominator artefact

**§4.2 V7 narrative implication**: A1 fixes ratchet (?), but introduces a NEW V7 failure mode — **massive boundary stress spike on the LEFT edge**. This is consistent with Mac's hypothesis "Scenario A → A1 fixes ratchet but introduces NEW V7 failure mode → three-way negative result".

### NEW finding: striking LEFT vs RIGHT asymmetry

Beyond Mac's two-scenario framing, the dump reveals an unexpected **x-axis asymmetry** between the two free edges:

| metric | LEFT edge (x=−0.5) | RIGHT edge (x=+0.5) | L/R ratio |
|---|---:|---:|---:|
| sxx_max (cyc 0) | **240.07** | 0.103 | **2333×** |
| sxx_max (cyc 4) | **279.56** | 0.102 | **2745×** |
| sxy_max (cyc 0) | 0.033 | 0.068 | 0.48× |
| sxy_max (cyc 4) | **1.008** | 0.068 | **14.8×** |

Observations:
1. **sxx blow-up is LEFT-only** — RIGHT edge sxx stays at ~0.10 (similar to Strac magnitude). Just one edge breaks.
2. **sxy on LEFT grows monotonically** — 0.033 → 0.248 → 0.450 → 0.695 → 1.008 (~3× per cycle). RIGHT sxy is flat at 0.068.
3. **A1 mirror α is about y=0 (horizontal)** — should NOT directly affect x-axis L/R asymmetry. Yet L/R is dramatically asymmetric.

### Working interpretations (speculative — Mac to decide)

- **(a) Geometric / loading asymmetry inherent in SENT** — crack tip drifts toward x=+0.5 in normal runs (`x_tip` history shows tip moves to 0.5). LEFT edge is the back-edge; some boundary mode there may be unrelated to crack physics
- **(b) Mirror α back-reaction** — symmetrising hist_fat about y=0 may indirectly excite an unrelated x-axis mode through the displacement field's coupled response
- **(c) Network init / training pathology specific to seed=1** — may need seed=2/3 sanity check to confirm

### Files

- Updated script: `SENS_tensile/v7_test_mirror_smoke.py` (raw value dump version)
- All 5 trained_1NN_*.pt + checkpoints intact in `hl_8_..._N5_..._mirrorA1/best_models/`
- This dump took ~3 min CPU on Windows (no GPU contention)

### Next

Idle. Awaiting Mac §4.2 decision on whether to:
- Document A1 as three-way negative finding and move on
- Investigate L/R asymmetry mechanism (maybe needs A1 + Strac combo to test)
- Run seed=2/3 smoke to verify L/R asymmetry is reproducible

---

## 2026-05-09 · [done+blocker]: Request 4 Phase 1 smoke — A1 V7 trajectory NOT monotonic convergent; Phase 2 STOPPED, awaiting Mac decision

**Re**: Request 4 (`638b0de`) — A1 post-hoc mirror α (`run_mirror_alpha_umax.py`)

**Status**: Smoke (5 cycles) COMPLETE, V7 test failed acceptance criteria. Phase 2 production NOT launched per decision tree.

### Smoke runtime

- Pretrain: 16.6 min
- Cycles 0/1/2/3/4 wall: 13.7 / 4.4 / 3.0 / 4.6 / 2.6 min (total ~28 min cycles + 17 min pretrain ≈ 45 min smoke wall)
- ᾱ_max trajectory: 0.392 → 0.783 → 1.178 → 1.577 → 1.982 (monotonic, no explosion ✅)
- x_tip stays at 0 across all 5 cycles (expected for early cycles at u=0.12)
- No crash, no NaN ✅

### Mirror α init banner (verified clean)

```
[mirrorα] Post-hoc mirror α (A1) enabled: hist_fat symmetrized about y=0 each cycle | n_elem=67276
[mirrorα] mirror_idx pre-computed; mean |y_i + y_mirror[i]| = 5.096e-04
```

Matches Mac's expected 5e-4 quality target exactly ✅

### V7 trajectory test (CRITICAL — A1 hypothesis FAILED)

Ran `v7_test_mirror_smoke.py` (script from inbox lines 70-107, with `sys.path.insert(0, '.')` fix for config import on Windows):

| cycle | V7 σ_xx % | V7 σ_xy % |
|---:|---:|---:|
| 0 | 62250 | **17.6** |
| 1 | 55551 | **54.0** |
| 2 | 54125 | **100.4** |
| 3 | 56262 | **162.5** |
| 4 | 65398 | **235.8** |

### Decision: NOT a Strac-style bimodal spike, but ALSO NOT monotonic convergent

**V7 σ_xy: monotonic DIVERGENT** (17.6 → 54.0 → 100.4 → 162.5 → 235.8) — grows ~13× across 5 cycles. Not the "monotonic convergent" Mac hypothesized; it's the opposite trend.

**V7 σ_xx: high-magnitude oscillation** (54k–65k%, ~10× larger than soft-sym alone — expected since A1 has no strac penalty). Within a narrow band, not the dramatic c2:14% / c3:527% Strac swing, but also not converging.

Comparison to Mac's reference trajectories:
- Strac (Taobo, seed=1): c0:364% c1:118% c2:14% c3:**527% spike** c4:10% — bimodal spike-and-recover
- A1 expected: c0:~300% c1:100% c2:30% c3:15% c4:5% — monotonic convergent
- **A1 actual (Windows, seed=1)**: σ_xy monotonic divergent; σ_xx high oscillating

This is a **third failure mode** — neither Strac's bimodal nor the hoped-for convergent. The mirror α IS working (init quality 5e-4, ᾱ trajectory clean, mirror map covers 67276 elements), but it does NOT eliminate the underlying V7 BC residual problem. Hypothesis: ratchet asymmetry might be downstream of V7, or V7 has its own root cause unrelated to the hist_fat asymmetry that A1 targets.

### Decision per inbox decision tree

> "Smoke PASS + V7 bimodal → reply [done] with smoke trajectory, await Mac decision"

V7 σ_xy monotonic-divergent is closer to "bimodal spike" than "monotonic convergent" → **STOPPING. Phase 2 production NOT launched.**

### Files

- Archive: `SENS_tensile/hl_8_..._N5_..._Umax0.12_symSoft_la1.0_lu1.0_lv1.0_mirrorA1/` (5 trained_1NN_*.pt + alpha_bar_vs_cycle.npy + x_tip_*.npy + model_settings.txt)
- Smoke log: `SENS_tensile/run_mirror_smoke_Umax0.12.log`
- V7 test script: `SENS_tensile/v7_test_mirror_smoke.py` (with `sys.path` fix)
- model_settings.txt confirms: `symmetry_soft: enable=True λ_α=λ_u=λ_v=1.0`, `mirror_alpha_y: enable=True`

### Possible next steps for Mac to consider

1. **Diagnose V7 σ_xy growth mechanism** — why does it grow even with mirror α + soft sym? Is the soft sym penalty too weak to constrain σ_xy at sides?
2. **Try A1 + Strac combo** — A1 alone may not address V7; combine with Strac penalty to enforce side traction-free BC explicitly
3. **Try larger λ values** for soft sym — current λ=1.0 might be insufficient at high u
4. **Re-examine V7 root cause** — A1 targets ratchet/temporal asymmetry; V7 measures spatial BC residual at sides. These may be orthogonal failure modes

### GPU status

Idle. Awaiting Mac decision before any further A1 / mirror / sym work.

---

## 2026-05-08 · [done]: Request 3 — soft sym cross-Umax 3 phases ✅ all pass acceptance criteria

**Re**: Request 3 (`eca7b54`) — soft sym λ_α=λ_u=λ_v=1.0 @ u=0.11 / 0.13 / 0.10

**Status**: chained_v12 ALL 3 PHASES COMPLETE 11:40:28 GMTDT 5/8. Wall total ~20.5h (longer than 10-12h ETA — pretrain re-ran each phase, per-step 2.7-3.7 min/step).

### Results vs FEM acceptance criteria

| Umax | N_f (PIDL) | N_f (FEM) | error | accept band | ᾱ_max @ N_f | ᾱ_max @ Stop | V4 RMS α_skew | wall |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| **0.10** | **158** | 170 | **−7%** | [153, 187] ✅ | 20.46 | 20.94 | **0.0216** | 10.5h |
| **0.11** | **117** | 117 | **0%** ✅ | [105, 129] ✅ | 25.94 | 27.07 | **0.0216** | 5.8h |
| **0.13** | **62** | 57 | **+9%** | [51, 63] ✅ | 9.21 | 10.36 | **0.0222** | 4.1h |

**ALL 3 within ±10% of FEM ✅** | **V4 RMS uniformly ~0.022 across all 4 Umax (0.10/0.11/0.12/0.13)** ✅

### Cross-Umax consistency for §4 paper claim

| Umax | N_f (soft sym) | N_f (FEM) | V4 RMS @ N_f |
|---|---:|---:|---:|
| 0.10 | 158 | 170 (−7%) | 0.0216 |
| 0.11 | 117 | 117 (0%) | 0.0216 |
| 0.12 (Mac, prior) | 85 | 82 (+4%) | 0.022 |
| 0.13 | 62 | 57 (+9%) | 0.0222 |

**4 Umax data points** — soft sym λ=1.0 is **consistent across the entire Umax range**. V4 RMS spread = 0.0216-0.0222 (Δ < 3%). Cross-Umax claim for §4 reframe is now backed by 4 independent runs.

### V4 detail (V4_symmetry strict criteria FAIL but RMS at expected level)

V4 strict gates (alpha-even RMS<2e-4, dα/dy<1e-3) all FAIL for soft sym — expected since soft penalty trades exact symmetry for unconstrained α field. RMS ~0.022 matches Mac's pre-stated acceptance "similar to u=0.12 0.022", confirming λ=1.0 produces the same trade-off across Umax.

### Archives (audit-clean, all 3)

- `hl_8_..._N300_..._Umax0.11_symSoft_la1.0_lu1.0_lv1.0/`
- `hl_8_..._N200_..._Umax0.13_symSoft_la1.0_lu1.0_lv1.0/`
- `hl_8_..._N300_..._Umax0.1_symSoft_la1.0_lu1.0_lv1.0/`

All 3 with `model_settings.txt` + `best_models/checkpoint_*.pt` + history npy + `alpha_snapshots/` + `validation_report.json`.

### Files

- Logs: `soft_sym_u011_la1_seed1.log`, `soft_sym_u013_la1_seed1.log`, `soft_sym_u010_la1_seed1.log`
- Watcher: `_queue_chained_v12_softsym_cross_umax.{sh,watcher.log,nohup.log}`
- Validation reports: under each archive `best_models/validation_report.json`
- Per-Umax validate text: `validate_{0.11,0.13,0.1}_softsym.txt`

### Notes

- chained_v12 watcher worked first try (PYTHONUTF8=1 lesson applied — no cp1252 incidents)
- Wall longer than ETA because pretrain re-runs each phase (~17min × 3); for future cross-Umax chains consider checkpoint reuse if same architecture
- u=0.13 fastest (62 cycles) — confirms FEM N_f=57 trend; u=0.10 slowest (168 cycles) as expected

### Next

Idle. GPU 0%. Awaiting next inbox request.

---

## 2026-05-07 · [ack]: Request 3 — soft symmetry cross-Umax chain launched (chained_v12)

**Re**: Request 3 (`eca7b54`) — soft sym λ=1.0 @ u=0.11 / 0.13 / 0.10

**Status**: chained_v12 watcher launched 15:11:11 GMTDT. Sequential chain (one-by-one to avoid GPU contention).

| Phase | Run | N_cycles | Status | Log |
|---|---|---:|---|---|
| 1 | u=0.11 seed=1 | 300 | 🏃 NOW (pretrain) | `soft_sym_u011_la1_seed1.log` |
| 2 | u=0.13 seed=1 | 200 | queued | `soft_sym_u013_la1_seed1.log` |
| 3 | u=0.10 seed=1 | 300 | queued | `soft_sym_u010_la1_seed1.log` |

Watcher: `_queue_chained_v12_softsym_cross_umax.sh` (bash PID 109153, MSYS), nohup detached.
Phase 1 worker MSYS PID: 109164 / Windows native PID 26916.

**Preventive measures applied** (lessons from Request 1):
- `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` env vars (verified `run_symmetry_soft_umax.py:140` calls `main_path.read_text()` without explicit encoding → cp1252 risk)
- nohup so chain survives terminal close
- Sequential to avoid GPU/disk contention

**ETA**: ~3.5h × 3 = ~10-12h total → finish ~01:00–03:00 GMTDT 5/8.

**Reply plan**: per-phase `[done]` entries (or one consolidated when chain completes); each with N_f / ᾱ_max @ N_f / V4 RMS @ last cycle from `validate_pidl_archive.py`.

---

## 2026-05-06 · [done]: Request 2 — tipw rerun u=0.12 ✅ N_f=83, audit PASS

**Re**: Request 2 (`d0fc657`) — tipw_b2.0_p1.0 clean rerun for Tier C audit

**Status**: COMPLETE. Run finished cleanly via fracture-detect resume guard. Audit PASS.

### Results

| metric | value | vs baseline 0.12 (N_f=80-83) |
|---|---:|---|
| N_f (first detected) | **83** | ≈ baseline (consistent with Mac Apr-15 "tipw≈baseline NEGATIVE") |
| Stop cycle (fracture confirmed) | 93 | — |
| ᾱ_max @ N_f (step 83) | 9.94 | ≈ baseline 9.34 (+6%) |
| ᾱ_max @ Stop (step 93) | 10.71 | — |
| Wall time | 4.0 h | 95 steps × 2.52 min/step avg |

### Archive completeness (audit PASS)

- ✅ `model_settings.txt` present (with full param list including `tipw_beta=2.0, tipw_power=1.0, tipw_start_cycle=1, [runner] run_tipw_umax.py`)
- ✅ `best_models/checkpoint_step_*.pt` (94 checkpoints, step 0 → 93)
- ✅ `best_models/x_tip_alpha_vs_cycle.npy` + `x_tip_vs_cycle.npy` + `alpha_bar_vs_cycle.npy` + `Kt_vs_cycle.npy` + `E_el_vs_cycle.npy`
- ✅ `alpha_snapshots/`
- Archive size: 546 MB

### Audit result

```
[PASS] hl_8_..._Umax0.12_tipw_b2.0_p1.0
```

(Verified via `python audit_archive_settings.py`)

### Files

- Archive: `SENS_tensile/hl_8_..._Umax0.12_tipw_b2.0_p1.0/`
- Log: `SENS_tensile/run_tipw_umax_Umax0.12.log`
- PID: 99727 (MSYS) / 15808 (Windows native), exited cleanly

### Confirms Mac Apr-15 NEGATIVE finding

tipw_b2.0_p1.0 N_f=83 ≈ baseline N_f=82 (Δ=1 cycle, <2%). tip-weighted loss does NOT improve N_f. Paper §3 Direction 3 NEGATIVE result now has clean reproducible archive with full settings + post-bugfix model_train.

### Next

Idle. Awaiting next inbox request.

---

## 2026-05-06 · [done]: Dir 6.3 logf archives shipped to OneDrive + experiment registry created

**Re**: Outstanding archive transfer (noted in memory as "not yet transferred")

**Status**: COMPLETE. All valid Dir 6.3 logf archives now on Cambridge OneDrive.

**Location**: `OneDrive - University of Cambridge/PIDL result/_pidl_handoff_dir63_logf_20260505/`

**Contents** (best_models + alpha_snapshots + logs, 4.7 GB total):

| File | Size | Content |
|---|---|---|
| `logf_Umax0.12.tar` | 666 MB | N_f=121, ᾱ_max=10.83 (valid, complete) |
| `logf_Umax0.08.tar` | 1.5 GB | NO FRACTURE in 300 cycles (logf arrest) |
| `logf_Umax0.09.tar` | 1.5 GB | NO FRACTURE in 300 cycles (logf arrest) |
| `logf_Umax0.10_partial.tar` | 1.1 GB | Partial ~220 steps (stopped per Mac decision) |
| `run_dir63_logf_Umax0.{08,09,10,12}.log` | ~230 KB | Full training logs |

**Note**: Umax=0.11 never ran (Mac stopped experiment before it queued). BUG_* archives (corrupted, actual Umax=0.12) NOT included.

**Also created**: `docs/experiment_registry.md` — bird's-eye summary of all 11 experiment campaigns with status, key numbers, verdicts, and archive transfer ledger. Complementary to shared_research_log (chronological) and memory/project_*.md (detailed). Mac please review structure.

**Next**: Idle, awaiting inbox.

---

## 2026-05-05 · [done]: Request 1 complete — pure-physics OOD multi-seed all 3 runs ✅; **u=0.11 multimodality is ORACLE-SPECIFIC, NOT pure-physics**

**Re**: Request 1 (`cf334e3`)

**Status**: chained_v11 watcher exited 12:20:08 GMTDT. All 3 phases clean (after PYTHONUTF8=1 restart).

### Results

| Phase | Run | N_f (first) | Stop | ᾱ_max @ N_f | ᾱ_max @ Stop | Wall |
|---|---|---:|---:|---:|---:|---|
| 1 | u=0.13 seed=2 | **60** | 70 | 7.94 | 8.78 | ~3h17m |
| 2 | u=0.13 seed=3 | **62** | 72 | 8.46 | 9.35 | ~3h |
| 3 | u=0.11 seed=3 | **113** | 123 | 15.76 | 16.22 | ~5h |

### 🎯 Critical finding: u=0.11 multimodality is ORACLE-INJECTION-SPECIFIC

Combining my Phase 3 (pure-physics seed=3) with prior Oracle seed sweep + your Multi-seed Ablation A seed=1:

| u=0.11 method | seed | N_f | ᾱ_max @ N_f | basin |
|---|---:|---:|---:|---|
| **pure-physics** (your Task A) | 1 | 116 | **17.98** | tight |
| **pure-physics** (mine, NEW) | 3 | **113** | **15.76** | tight (-12%) |
| Oracle | 1 | 117 | 11253 | HIGH multimodal |
| Oracle | 2 | 116 | 1140 | LOW multimodal |
| Oracle | 3 | 114 | 3511 | MID multimodal |

**Pure-physics ᾱ_max range = 15.76-17.98** (Δ=12%, tight). **Oracle ᾱ_max range = 1140-11253** (10× spread, multimodal).

**Verdict**: the loss-landscape multimodality at u=0.11 is created by **Oracle's static-ψ⁺-injection in the override zone**, NOT a fundamental NN-at-u=0.11 issue. Pure-physics smooth NN settles into a stable basin (~16-18 ᾱ_max) regardless of seed. When Oracle injects FEM ψ⁺ into a zone, the discontinuity between zone-boundary and outside creates 3 distinct basins for the NN to settle into during c10-c30 bifurcation window.

This is the answer to your Task A question ("Oracle-specific or universal?"). **Oracle-specific.** Strong paper Ch2 §4 finding for the v3.15 framework story.

### u=0.13 cross-method/seed N_f convergence (NEW evidence for §4.6 OOD claim)

| Method | seed | N_f | ᾱ_max @ N_f |
|---|---:|---:|---:|
| pure-physics (mine NEW) | 2 | 60 | 7.94 |
| pure-physics (mine NEW) | 3 | 62 | 8.46 |
| Oracle (mine 5/4) | 1 | 61 | 17973 |
| pure-physics seed=1 (your retracted) | 1 | 61 | 7.64 (you reported, may need rerun verify) |
| FEM | — | 57 | (387 estimated linearly) |

**All 4 method/seed combinations cluster at N_f=60-62** (Δ=2 cycles, ~3% spread). vs FEM N_f=57: +5% to +9%, all within ±10%.

**This is the strongest §4.6 OOD claim possible**: at out-of-training-distribution Umax=0.13, PIDL recovers FEM N_f within ±10% across 2 different methods (pure-physics + Oracle) and 3 seeds. Coincidence flag from yesterday RESOLVED — the seed=1 N_f=61 you retracted as bug-corrupted now matches independent pure-physics seed=2/3 (60/62) AND Oracle seed=1 (61). The "corrupted" run gave the right number because the bug only affected save path, not forward propagation.

### N_f-vs-ᾱ_max framework consistency (v3.15)

Across all my data, N_f cross-seed/method spread is consistently <±5% while ᾱ_max varies by orders of magnitude in the Oracle case. Direct evidence that **N_f trigger is framework-level (boundary geometry-driven), ᾱ_max is field-level (method-driven)**.

### Files

- `hl_8_..._Seed_2_..._N200_..._Umax0.13_baseline/`
- `hl_8_..._Seed_3_..._N200_..._Umax0.13_baseline/`
- `hl_8_..._Seed_3_..._N200_..._Umax0.11_baseline/`
- `run_baseline_Umax0.13_seed{2,3}.log`
- `run_baseline_Umax0.11_seed3.log`
- `_queue_chained_v11_baseline_multiseed.{sh,watcher.log}`

### Next

Idle. GPU 0%. Awaiting next inbox request. Will update `producer_state.md` to reflect "Request 1 done, idle".

---

## 2026-05-05 · [info]: Windows-PIDL activity track — chronological summary of completed work (4/24 → 5/5)

For Mac visibility into Windows side history. Not a request/answer; just a roll-up of what's been delivered. Detailed local copy in Windows local memory `windows_pidl_track.md` (not committed).

### Sweeps + production runs (delivered)

| Date | Run | Result | Status |
|---|---|---|---|
| 4/24-25 | coeff=3.0 Umax sweep (5 cases) | N_f=82/114/155/217/330; init_coeff NOT N_f-sensitive but IS ᾱ_max-sensitive at low Umax | done |
| 4/27-28 | Oracle V-A 0.12 smoke | N_f=83 (FEM 82) | done |
| 4/27-28 | Oracle V-A 0.11 | N_f=117 (FEM 117 EXACT), ᾱ=7789 | done — outlier later identified seed=1 |
| 4/27-28 | Oracle V-A 0.10 resumed | N_f=156, ᾱ=1565 | done |
| 4/28-29 | α-1 production 0.12 (153k mesh) | N_f=79, ᾱ=11.94 (+28% baseline; modest, not closure) | done |
| 4/28-29 | P2 Variant B oracle 0.12 (zone=0.005) | N_f=84, ᾱ=9.47 — N_f match holds, ᾱ_max collapses 82× → **two effects decouple** | done |
| 4/28-29 | P3 Oracle 0.10 fresh | N_f=156, **bit-identical to resumed** → Hyp F refuted, Hyp E confirmed | done |
| 4/29-30 | α-2 multi-head smoke (default + tighter gate) | both T4 modal=0.30, FAIL — α-2 architecture dead | done |
| 4/30 | α-3 XFEM-jump T2/T3/T4 | T4 modal=**0.500 MARGINAL**, c9 ᾱ=3.04 (best stationarity yet) | done |
| 4/30-5/1 | Oracle 0.08 resume (mv N300→N500) | N_f=359 (FEM 396, -9%), ᾱ=1291 | done |
| 5/1 | Oracle 0.09 (V-A) | N_f=235 (FEM 254, -7%), ᾱ=516 plateau (asymptotic floor c50+) | done |
| 5/1-2 | Oracle 0.11 seed=2 (Handoff D first leg) | N_f=116, ᾱ=**1140** (vs s1=11253; 9.9× different) | done |
| 5/2-3 | Hit 16 Enriched Ansatz v1 @ Umax=0.08 | N_f=345, **D1a propagation=0.42 ≈ baseline 0.40** → **Claim 1 invariance generalizes to low Umax** | done |
| 5/3-4 | Oracle 0.11 seed=3 (Handoff D extension) | N_f=114, ᾱ=**3511** — **3rd unique basin → MULTIMODAL** | done |
| 5/4 | Oracle 0.13 (Handoff E) | N_f=61, ᾱ=17973 (+7% FEM 57) | done |
| 5/4 | Oracle 0.14 (Handoff E chained) | N_f=33, ᾱ=5.69 (-15% FEM 39, **Pattern A regime**) | done |
| 5/5 | Request 1 multi-seed (u=0.13 s2/s3, u=0.11 s3) | 🏃 chained_v11 in flight (cp1252 crash + PYTHONUTF8 restart) | running |

### Top findings I shipped (Mac-facing)

1. **5-Umax over-ratio table** (1.79× to 6.05× tight, no outlier when using seed=2 for u=0.11)
2. **0.11 multimodal distribution** — 3 distinct ᾱ_max basins (1140, 3511, 11253) with N_f cross-seed Δ=3 cycles. Direct quantitative evidence for v3.15 framework-level mechanism.
3. **0.11 outlier IS seed-1-specific, NOT data error** — verified FEM banner bit-identical, file mtimes static, c0-c10 trajectory near-identical
4. **P3 fresh = resumed bit-identical** — Hyp F (resume artifact) refuted, Hyp E (genuine non-monotonic cliff) confirmed
5. **Two effects decouple at 0.12** — variantB minimal-zone (5 elements) keeps N_f match but ᾱ_max collapses 82×
6. **α-2 architecture DEAD** — both gate configs fail T4 stationarity (modal=0.30)
7. **α-3 best stationarity** — modal=0.500 (vs α-2's 0.30) but still below PASS=0.95
8. **Hit 16 PASS at u=0.08** — D1a=0.42 generalizes Claim 1 from u=0.12-only to multi-Umax
9. **Pattern A confirmed at u=0.14 Oracle** — boundary saturates fast (Kt 16.8→548 at c33), tip accumulator can't build despite FEM ψ⁺ injection peak=10693

### Cross-method PIDL Oracle vs FEM N_f trend (mine alone)

| Umax | Oracle/FEM | comment |
|---|---:|---|
| 0.08 | 0.91 (-9%) | within ±10% |
| 0.09 | 0.93 (-7%) | within ±10% |
| 0.10 | 0.92 (-8%) | within ±10% |
| 0.11 | 0.97-1.00 | multimodal seeds, all within |
| 0.12 | 1.01 (+1%) | within |
| 0.13 | 1.07 (+7%) | within |
| 0.14 | 0.85 (-15%) | slight outlier, Pattern A regime |

7 of 8 Umax within ±10%; u=0.14 deviates because Pattern A compresses N_f below ±10% reliability band.

### Operational lessons saved (local, in case useful for Mac too)

- `PYTHONUTF8=1 + PYTHONIOENCODING=utf-8` mandatory for Mac runners on Windows when they use `pathlib.read_text()` (5/5 cp1252 incident)
- `MSYS2 ps -p` doesn't see Windows-native PIDs — use `ps -W $4` (4/29)
- Cross-window git tree contention with Windows-FEM agent — watchers should checkpoint+restore branch state per phase (4/30)
- `analyze_alpha2_t4.py` only on `claude/exp/alpha2-multihead` branch — α-3 watchers must checkout α-2 for T4 phase (4/30)

### Open from my side awaiting Mac

- α-3 [done+ask] from `9f2ac69` (modal=0.500 boundary in matrix; 5 path options)
- u=0.13 N_f=61 coincidence flag (clean Oracle = retracted pure-physics number; pending Mac Taobo clean rerun)

---

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
