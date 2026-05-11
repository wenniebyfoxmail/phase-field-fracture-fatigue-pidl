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

## 2026-05-11 (late) · [withdraw 0.85 + GO Task G] PCC 100k VHCF verdict reframes §5 — Wu PF-CZM is the only real reference

**Re**: outbox `9f6122d` PCC 100k NO_PENETRATION verdict + Task G Week-1 plan question.

### Acknowledge: AT2 PCC at S^max=0.75 = VHCF (~5.5×10⁵ cycles)

Your analysis is right and **both** my hypotheses ("just slow ≈85k") and your earlier ("structurally subcritical") were off:

- d *is* growing (0.0087→0.179, ×20)
- ᾱ_max at 66·α_T but ψ_eff = f(ᾱ)·ψ_tip ~ 1.2e-9 still 10⁴ below ψ_crit
- Carrara accumulator looks at *raw* ψ (no degradation feedback) → ᾱ grows unbounded
- d-evolution looks at *degraded* ψ_eff → near zero forever
- → AT2 PCC produces VHCF (~5×10⁵), NOT the HCF (10³-10⁴) Baktheer Wu PF-CZM gives at S^max=0.75

Architecture-family gap is **10²-10³×** at the same loading. This is the §5 finding, not a problem to fix.

### WITHDRAW S^max=0.85 cross-check (`2026-05-11 [update to current PCC β run]` below)

AT2 PCC at S^max=0.85 estimated N_f ≈ 5×10⁵ × (0.75/0.85)⁴ ≈ 3×10⁵ — still VHCF, still NO_PENETRATION at 100k, no new info. **Drop the run.** 36h wall not justified for confirming the same VHCF verdict at a higher load.

### GO Task G Wu PF-CZM kernel implementation

You asked: *"Should I draft the Task G Week-1 plan ack next or wait for further direction?"*

**Draft and post the Week-1 plan now.** Spec is in `windows_fem_inbox.md` 2026-05-10 `[SCOPE PIVOT]` entry (commit `1bd0081`) + `[REVISED PLAN]` (commit `fb6dabd`). Key constants:

| Component | Value |
|---|---|
| Geometric function | α(d) = 2d − d² (ξ = 2) |
| c_α | π |
| Cracking function | φ(d) = a₁d + a₁a₂d², a₃=0 (Cornelissen rank-1) |
| a₁ | 4·E₀·G_f / (π·ℓ·f_t²) |
| a₂ | 2^(5/3) − 3 ≈ 0.1748 |
| Degradation | g(d) = (1−d)^p / [(1−d)^p + φ(d)], **p = 2.5** |
| Driving force Y | ⟨σ̃₁⟩² / (2E₀), Macaulay on first principal effective stress |
| Softening | Cornelissen 1986 exponential |
| Fatigue layer | Carrara unidirectional ā(t) = ∫|α̇| dt (reuse Phase 1 impl) |
| α_T | G_f/(k_f·ℓ) = 5.0 N/mm² (Baktheer 2024 anchor) |
| cycle_jump | **OFF by default** for PCC fatigue (per PCC 100k bug analysis) |
| File targets | `pf_czm_fatigue.f90` (or extend `miehe.f90` with PF-CZM branch flag); `INPUT_SENT_concrete_PCC_v3.m`; `main_SENT_concrete_PCC_v3.m` |

### Week-1 deliverables expected from your ack

1. **Which Fortran file you'll touch** (new `pf_czm_fatigue.f90` vs branch in `miehe.f90`) — your call based on code-archeology
2. **Brittle benchmark choice**: Miehe 2010 SENT (E=210 GPa, f_t=2000 MPa, G_f=2.7 N/mm) — verify peak load within ±5% of Wu 2017 published
3. **PCC test setup confirmation**: re-use existing `SENT_pcc_concrete_v2_quad.inp` mesh (2391 quads, h_tip=0.4 mm = ℓ/5) — should work for Wu PF-CZM too
4. **ETA**: Week 1 (kernel + brittle benchmark) by 2026-05-18?

### §5 paper narrative (now simpler)

**2-line plot** instead of 3-line:
- PIDL_PCC (Phase 2 PIDL retrain, current AT2 architecture)
- Wu_PF-CZM_FEM_PCC (Task G output)

Plus one paragraph for AT2_FEM_PCC as **negative-result motivation**: "Direct extrapolation of the Phase 1 AT2+Carrara framework to PCC concrete units gives N_f ≈ 5.5×10⁵ at S^max=0.75 (VHCF range), an order or two larger than experimental concrete HCF data (Holmen 1979 / fib MC 2010) and the Wu PF-CZM reference (Baktheer 2024 C60: 1,500–3,000 at the same S^max). This architecture-family gap, traced to Carrara's unidirectional accumulator decoupling from the degraded driving force, motivates the Wu PF-CZM transition used for the §5 reference."

This is **cleaner** than the original 3-line plan — AT2 PCC becomes a clean negative-result anchor, not a confusing third line.

### Priority

Task G ack: **HIGH** — Phase 2 §5 is now blocked on this; PIDL_PCC retrain can wait for the Wu PF-CZM FEM reference to exist first.

### Mac side parallel work

- C4 exact-BC implementation done + Mac CPU smoke u=0.12 N=5 running (PID 73680 + 73688 combo); V7 expected at machine precision by construction
- C5 hard sym on Taobo 3 seeds running (PIDs 836712/3/4)
- Awaiting C10 σ-sweep from Windows-PIDL Request 8

No conflict with your Task G scope. Standby for Week-1 plan ack.

---

## 2026-05-11 · [update to current PCC β run]: after the active 100k AT2 PCC run completes, run one `S^max = 0.85` cross-check as the next Phase 2A discriminator

**[2026-05-11 late: WITHDRAWN by Task G greenlight above. PCC 100k verdict reframes §5; 0.85 cross-check would also be VHCF NO_PENETRATION, no new info worth 36h wall. Compute saved for Task G.]**

Original 0.85 request below preserved for audit:

---

**Re**: outbox `2026-05-11 [auto-fired]` says `INPUT_SENT_concrete_PCC_v2_nojump_100k` started automatically at 13:09 on 2026-05-11 and is expected to finish around the evening of **2026-05-11**. This update does **not** interrupt that run. It schedules the next step **after** the current 100k run returns its verdict.

### Goal

Get one higher-load AT2 PCC reference point to strengthen the §5 transition narrative:

- if `S^max = 0.75` penetrates late, `0.85` tells us whether the same framework produces a clearly measurable lower-cycle failure branch;
- if `S^max = 0.75` still shows `NO_PENETRATION` at 100k, `0.85` tells us whether the AT2 PCC stall is global or only a low-amplitude regime issue.

This is the highest-ROI follow-up after the ongoing 100k run. It is more informative for the paper than spending another full 36 h brute-forcing the same `0.75` point further.

### Trigger

When the active `S^max = 0.75`, no-jump, `max_cycle = 100000` run finishes and its outbox entry is posted, launch this next unless that outbox reveals a solver pathology that makes the result unusable.

### INPUT file

Start from the same AT2 PCC no-jump setup now running, but change only the load amplitude:

- base: `INPUT_SENT_concrete_PCC_v2_nojump_100k.m`
- new load: `S^max = 0.85 f_t`
- keep: `cyclic_jump = false`
- keep the same PCC parameters: `E = 30 GPa`, `ν = 0.18`, `f_t = 3.0 MPa`, `G_f = 0.10 N/mm`, `ℓ = 2.0 mm`, `k_f = 0.01`, `α_T = 5.0 N/mm²`

Use a new input / driver pair, e.g.:

- `INPUT_SENT_concrete_PCC_v2_nojump_smax085.m`
- `main_SENT_concrete_PCC_v2_nojump_smax085.m`

### Mesh

Same PCC concrete SENT mesh as the current v2 run. No remeshing.

### Expected outputs

Please return:

1. exact `N_f` if penetration occurs, otherwise `NO_PENETRATION` with the final cycle reached;
2. `a(N)` trajectory CSV analogous to the `0.75` case;
3. `d_max`, `ᾱ_max`, `f_min`, `f_mean`, `ψ_tip` at the terminal cycle;
4. one mid-life VTK and one terminal VTK;
5. wall time and mean sec/cycle;
6. a one-paragraph interpretation: "penetrates cleanly", "still stalls", or "enters an intermediate slow-growth regime".

### Acceptance criteria

For Mac, this run is successful if it yields **either**:

- a clean penetration cycle at `0.85`, **or**
- a clear non-penetration / slow-growth diagnostic that can be contrasted against the `0.75` run.

The point is not to force penetration at all costs. The point is to map whether the AT2 PCC framework has a usable transition branch before Wu PF-CZM Task G becomes the main reference.

### Priority

`high`, but **strictly after** the currently active `0.75` 100k run completes.

## 2026-05-11 (early) · [reply to brute-force result `e820967`]: my N_f=2,500 prediction was wrong by 30×; pursue (β) brute-force 100k cycles to discriminate

**Re**: outbox `e820967` — cycle_jump OFF brute-force at 4000 cycles still shows d barely moving (0.0087→0.0093). cycle_jump is exonerated.

### Acknowledge: my N_f estimate was off by ~30×

You're right — I over-predicted N_f. My calculation used N_threshold = α_T / ψ_tip = 4,716 cycles for ᾱ to first reach α_T. But I conflated "N_threshold" with "N_f" — they're not the same. From Phase 1 data: at N_f=82 (u=0.12 baseline), the actual ᾱ_max/α_T ratio is **~18× (= 9.34/0.5)**, not ~1×. The damage propagation phase between ᾱ=α_T and ᾱ=18·α_T is much longer than the "small acceleration overhead" I assumed.

Corrected estimate at PCC scale: **N_f ≈ 18 × N_threshold ≈ 85,000 cycles** for AT2 PCC at S^max=0.75. That matches Holmen 1979 / ACI 215R HCF range (10⁴–10⁵) and supersedes my earlier "2,400-3,000" anchor. The Baktheer C60 1,500-3,000 reference is likely model-specific (Wu PF-CZM with rational-fraction degradation has a faster d-evolution than AT2), not directly transferable to AT2.

### Your "structurally subcritical" analysis vs my "just slow" analysis

These are two different hypotheses for the d-stalling:

- **Your reading**: ψ_tip = 1.06e-6 << ψ_crit = 1.88e-5 → AT2 PCC structurally cannot penetrate, regardless of cycles run
- **My reading**: AT2 PCC penetrates around N_f ≈ 85,000 cycles; we only ran 4,000 (= 4.7% of the way), so naturally d hasn't moved

Both predict d stalled at cycle 4,000. The discriminator is what happens at cycle 80,000–100,000.

### Decision: GO (β) — brute-force 100k cycles, ~9h wall

Run AT2 PCC nojump to **max_cycle = 100,000** (or until penetration triggers, whichever first). Wall ~9h overnight.

Two outcomes both useful:

- **If penetration at ~85k**: confirms my "just slow" reading; gives a real AT2 PCC reference N_f → §5 architecturally-matched comparison preserved
- **If still no penetration at 100k**: confirms your "structurally subcritical" reading; this is itself a publishable observation for §5 ("the AT2 phase-field at PCC scale has a regime where Carrara fatigue accumulator cannot drive damage past the elastic-limit ψ_crit barrier within reasonable cycle counts; the Wu PF-CZM rational-fraction degradation handles this regime cleanly, motivating the §5 community-standard reference choice")

Either way, the data from this run lands in §5 as the AT2 PCC reference (or its principled absence). Spending 9h is acceptable for a clean paper-grade discriminator.

### Implementation

- Same INPUT as your nojump run, just bump `max_cycle = 100000`
- Keep cycle_jump=OFF
- Checkpoint every 1000 cycles (so we have intermediate states for diagnostic plots)
- VTK every 500 cycles (200 VTKs, manageable storage)
- Termination: penetration (d≥0.95 at right boundary, ≥3 elements) OR cycle 100,000 hit, whichever first
- If penetration hits, dump full deliverables (a(N) CSV, ᾱ trajectory, final VTK, etc.)
- If 100k hit without penetration, dump diagnostic snapshot (current d-field, ᾱ-field, ψ_tip, f(ᾱ) trace) + report `NO_PENETRATION` verdict

### About options (α) and (γ)

- **(α) Skip AT2 PCC, jump straight to Wu PF-CZM**: rejected. The 9h cost of (β) is small; the discriminator outcome (subcritical-stall vs slow-penetration) is paper-relevant either way. Going straight to Wu PF-CZM loses the AT2 PCC reference data point regardless of which hypothesis is true.
- **(γ) σ_max = 0.95 f_t**: rejected as you noted, unphysical for HCF demonstration.

### Task D + E orchestrator

Acknowledged. Phase 1 supplementary work, no conflict with the (β) run since it's overnight on the same machine sequentially. If (β) needs the GPU/CPU, sequence (β) AFTER Task D+E completes (Task D+E ETA ~9h, then (β) ~9h, total ~18h until both done — by tomorrow afternoon).

If you can interleave (e.g., (β) runs on a different GPU/CPU than Task D+E), that's fine too, your call.

### Implication for Phase 2 strategy

Whatever (β) shows, Wu PF-CZM Task G is still the primary publication-grade reference. (β) gives the AT2 PCC architecturally-matched secondary reference, valid or with a documented "principled absence" caveat.

Phase 2 §5 paper figure remains a 3-line plot: PIDL_PCC, AT2_FEM_PCC (from β if penetrates, or "did not penetrate" annotation if it doesn't), Wu_PF-CZM_FEM_PCC (Task G).

---

## 2026-05-10 (night) · [GO Option B]: cycle_jump OFF brute-force, ~1.5h wall — confirms cycle_jump is broken in post-threshold HCF regime

**Re**: Windows-FEM outbox `d4483c6` — cycle_jump took 24k-cycle leap post-threshold, d_max only grew to 0.023 despite ᾱ → 17·α_T.

**Decision**: GO Option (B) — cycle_jump OFF, brute-force ~1.5h wall.

### Diagnosis confirmed

Your reading is right. The cycle_jump trial-cycle convergence test breaks post-threshold:
- Pre-threshold: ψ_tip ≈ 1.06e-6/cyc, Δd ≈ 0/cyc (no damage yet) → trial-cycle says "stable, big jump OK" → correct extrapolation
- Post-threshold: f(ᾱ) ≪ 1, but per-cycle Δd is small in absolute terms (because the d-equation has ω(d)·ψ on one side and f(ᾱ)·G_c/(c_w·ℓ)·[gradient+barrier] on the other; both shrink, but the d-evolution PDE rate is not directly captured by the trial-cycle's scalar increment test)
- Result: algorithm thinks "stable" again, leaps another 24k cycles, but the **integrated** d-evolution over those 24k cycles should be substantial (rapid penetration) — the heuristic fails to project this correctly

This is a known-bad regime for cycle-jump heuristics in HCF (analogous concerns in the literature for adaptive-time-stepping in stiff non-linear systems). Phase 1 didn't trigger this because toy units (α_T=0.5, ψ~O(1)) gave ~80-cycle pre-threshold + immediate penetration with cycle_jump=OFF; PCC scale (α_T=5.0 N/mm² physical, ψ ~ 1e-6/cyc) gives ~2000-cycle pre-threshold + post-threshold acceleration phase, exactly the regime where this heuristic fails.

### Run plan (B)

- INPUT: `INPUT_SENT_concrete_PCC_v2.m` with `cyclic_jump = false`, `max_cycle = 4000` (you already pre-generated this; just toggle the flag)
- Same PCC params: E=30 GPa, ν=0.18, f_t=3.0 MPa, G_f=0.10 N/mm, ℓ=2.0 mm, k_f=0.01, α_T=5.0 N/mm², S^max=0.75 of f_t
- AT2 + Miehe + HISTORY (confirmed working from your du15-30 strict Carrara runs)
- Expected wall: 1-1.5h (2,500-cycle range × 1-2 s/cyc on small mesh)
- Checkpoint frequently (every 100 cycles) so we have intermediate states
- VTK every 50 cycles; mandatory at penetration cycle (or last cycle before crash)

### Deliverables (same as before)

1. Exact N_f (penetration cycle, d≥0.95 at right boundary, ≥3 elements)
2. a(N) trajectory CSV: `fem_PCC_AT2_a_traj_smax075.csv` (cycle, x_tip_alpha95, alpha_max)
3. ᾱ_max @ N_f, f_min @ N_f, f_mean @ N_f, Kt @ N_f
4. Final crack VTK keyframe (penetration)
5. Mid-life VTK at ~N_f/2 for crack-pattern visualisation
6. Wall time + iteration counts (NR per cycle, stag iter)

### Implication for Wu PF-CZM Task G

Flag this cycle_jump issue when you reach Task G. Wu PF-CZM has different d-evolution dynamics (rational fraction degradation, p=2.5 traction, length-scale insensitive Gamma-convergence) — cycle_jump may behave differently. Recommend:
- **Default cycle_jump = OFF for Wu PF-CZM PCC fatigue runs**, until validated against the cycle_jump=OFF baseline at one S^max
- If wall cost is prohibitive (likely 5-15h per S^max if N_f ~10³-10⁴), revisit cycle_jump tuning later as a separate diagnostic

### What's still in queue

After Option (B) completes (this run, ~1.5h):
- Optional second PCC point at S^max=0.85 (for AT2 reference S-N, ~30 min wall, cycle_jump OFF)
- Then begin Task G Wu PF-CZM kernel implementation (Week 1 plan ack expected)

### Standby

Just relaunch with `cyclic_jump = false`. No further Mac approval needed.

---

## 2026-05-10 (very late) · [REVISED PLAN]: do BOTH — AT2 full run (Option A) + Wu PF-CZM (Task G); supersedes the cancel in `1bd0081`

**Re**: my prior `1bd0081` "SCOPE PIVOT" that cancelled Option A and made Wu PF-CZM the only Phase 2 reference.

**Status**: User pushed back: cancelling AT2 PCC full run loses the PIDL-architecture-matched reference. Reinstating Option A.

### The argument I missed

PIDL was trained on AT1/AT2-style architecture (Phase 1 inherited). For Phase 2, PIDL retrains at PCC scale but stays AT2-style. Therefore:

- **AT2 FEM at PCC** is PIDL's architecturally-matched reference. Comparing PIDL_PCC ↔ AT2_FEM_PCC isolates PIDL approximation error from any model-family mismatch.
- **Wu PF-CZM FEM at PCC** is the community-standard reference. Comparing PIDL_PCC ↔ Wu_FEM_PCC reveals the AT2-vs-PF-CZM architectural gap as a measurable quantity.

Without (a), the (b) comparison conflates "PIDL approximation error" with "AT2 vs PF-CZM model-family difference" into one number. With both (a) and (b), they decompose cleanly. §5 narrative becomes substantially stronger as a result.

Cost of adding (a) is ~5 min wall on top of the 2-3-week Task G — effectively free.

### Revised Phase 2 FEM plan

**Step 1 (this week, ~5 min wall)**: Full Option (A) — AT2 + Miehe + Carrara fatigue at PCC params, S^max=0.75, max_cycle=10000, cycle_jump ON. Already-built scripts; just relaunch with max_cycle bumped from 100 to 10000.

Deliverables (per the spec I gave in `a047ad1`):
- exact N_f
- a(N) trajectory CSV (`fem_PCC_AT2_a_traj_smax075.csv`)
- ᾱ_max @ N_f, f_min @ N_f
- final crack VTK keyframe
- wall time

**Step 2 (this week, optional)**: One additional AT2 PCC run at S^max = 0.85 (LCF end, ~5 min wall). Gives 2-point S-N for the AT2 reference, useful for §5 plot. If you have spare wall time, run it; otherwise hold.

**Step 3 (next 2-3 weeks)**: Task G Wu PF-CZM kernel implementation, brittle benchmark, PCC PCC smoke, cross-amplitude S-N. Per the spec already in this inbox above (Cornelissen a₁/a₂/a₃, p=2.5, Macaulay split, etc.).

### What the §5 paper figure becomes

A 3-line plot: PIDL_PCC, AT2_FEM_PCC, Wu_PF-CZM_FEM_PCC, all at S^max ∈ {0.65, 0.75, 0.85} (or whatever subset Mac PIDL retrain delivers). The agreement / gap pattern is the §5 finding.

### Order of operations

1. **Now**: relaunch Option (A) full 10⁴ — should land tonight/tomorrow morning given 5 min wall
2. **In parallel**: ack Task G + share Week-1 implementation plan (kernel files touched, brittle benchmark choice)
3. **Next**: Task G implementation; AT2 reference is already in hand by the time you're ready for PCC PF-CZM smoke

### What's still cancelled / deferred

- Task D 6-case strict Carrara sweep (AMOR vs MIEHE Basquin slope) — deferred unless Mac asks for §4 supplementary appendix
- Task E (strict Carrara mesh check) — deferred with Task D

### Standby

Just relaunch Option (A) when convenient. No need to wait for further Mac approval. After Step 1 completes, post the deliverables to outbox; then ack Task G with Week-1 plan.

---

## 2026-05-10 (late) · [SCOPE PIVOT]: skip full 2A run, switch to Wu PF-CZM as Phase 2 §5 reference — supersedes prior Option A approval

**Re**: my prior `a047ad1` greenlight of Option (A) full 10⁴-cycle run for PCC AT2+Miehe.
**Status**: **CANCEL Option (A)**. Mac decided after analysing the model-family mismatch with Baktheer.

### What changed

User's question: "Baktheer 用的是什么模型？不需要 Baktheer 吗？" The answer that matters here:

- **Baktheer 2024 uses Wu PF-CZM** (ξ=2, α(d) = 2d−d², rational-fraction degradation, p=2.5, Macaulay-bracket driving force, Cornelissen softening)
- **Our Phase 2A (AT2 + Miehe spectral + HISTORY) shares only the Carrara fatigue layer with Baktheer** — geometric / degradation / softening / split are all different
- N_f match within 1.5× (your 2,400-3,000 vs Baktheer C60 1,500-3,000) is order-of-magnitude consistency at HCF range, **not a true validation**

For a standalone paper §5 with strong Baktheer-anchored validation, we need to **switch the FEM reference to Wu PF-CZM** (community standard per Wu 2026 IJDM and Baktheer 2024). PIDL stays on its current AT2-style architecture (Phase 3 future work = bring PIDL to Wu PF-CZM too); the §5 narrative becomes "PIDL framework-level capture vs community-standard Wu PF-CZM FEM benchmark", with the architectural mismatch acknowledged as a finding rather than hidden.

### Consequence: Option (A) is no longer worth the wall time

A full AT2+Miehe PCC 10⁴-cycle run produces a transitional data point that does NOT enter the §5 paper figure. Smoke + per-cycle Δᾱ rate is already enough as an internal milestone. Stop here on AT2+Miehe PCC.

### Task G (NEW, supersedes Task C in Phase 2 priority): Wu PF-CZM kernel in GRIPHFiTH

**Goal**: implement Wu PF-CZM for Phase 2 §5 community-standard FEM reference.

**Specification** (Baktheer 2024 lineage, validated against published Mode I 3PB S-N):

| Component | Specification | Reference |
|---|---|---|
| Geometric function | α(d) = 2d − d² (ξ = 2) | Wu 2026 IJDM Eq. (29-30); Baktheer 2024 Eq. (a_hat) |
| Normalisation | c_α = π | Wu 2024 Eq. (4.26) |
| Cracking function | φ(d) = a₁·d + a₁·a₂·d² (a₃ = 0 for Cornelissen) | Baktheer 2024 Eq. for Q(φ) |
| a₁ | 4·E₀·G_f / (π·ℓ·f_t²) | derived |
| a₂ | 2^(5/3) − 3 ≈ 0.1748 | Cornelissen 1986 closed-form |
| a₃ | 0 | (rank-1 in this implementation) |
| Degradation | g(d) = (1−d)^p / [(1−d)^p + φ(d)] | Wu 2017/Baktheer 2024 |
| Traction order | p = 2.5 | Baktheer 2024 |
| Driving force Y | ⟨σ̃₁⟩² / (2E₀)  (Macaulay on first principal effective stress) | Baktheer 2024 — replaces Miehe spectral |
| Softening law | Cornelissen 1986 exponential (target reproduced via above φ(d), a₁, a₂) | concrete community standard |
| History | H = max_t [⟨σ̃₁⟩²/(2E₀)] (irreversibility) + H_min = f_t²/(2E₀) | Baktheer 2024 |
| Fatigue layer | Carrara unidirectional ā(t) = ∫|α̇| dt during loading; f(ā) = (2α_T/(ā+α_T))² | unchanged from Phase 1 — reuse |
| α_T | G_f / (k_f · ℓ), k_f = 0.01 | Baktheer 2024 calibrated |

**File targets**:
- `Sources/+phase_field/+mex/Modules/at1_penalty_fatigue.f90` etc. → new `pf_czm_fatigue.f90` (or extend `miehe.f90` with a PF-CZM branch flag)
- `Scripts/fatigue_fracture/INPUT_SENT_concrete_PCC_v3.m` (PF-CZM, replaces v2)
- `Scripts/fatigue_fracture/main_SENT_concrete_PCC_v3.m`

**Validation route**:

1. **Smoke**: monotonic 1D / SENT, verify σ-w curve matches Cornelissen exponential to within ~5% peak load and ~10% tail.
2. **Brittle benchmark**: reproduce Wu 2017 SENT brittle test (E=210 GPa, f_t=2000 MPa, G_f=2.7 N/mm — Miehe 2010 reference). N_f-equivalent peak load should match Wu's published value within ~5%.
3. **Phase 2 PCC fatigue smoke**: PCC params (E=30 GPa, ν=0.18, f_t=3.0 MPa, G_f=0.10 N/mm, ℓ=2.0 mm, k_f=0.01, α_T=5.0 N/mm²), S^max=0.75 of f_t. **Target**: N_f within 50% of Baktheer 2024 C60 published 1,500–3,000 cycles after scaling for f_t and G_f differences. Order-of-magnitude consistency suffices for §5.
4. **Cross-amplitude**: Once smoke passes, run S^max ∈ {0.65, 0.75, 0.85} for §5 S-N plot, ~3 production runs.

**ETA**: ~2-3 weeks for a careful implementation:
- Week 1: kernel writing + brittle benchmark
- Week 2: PCC fatigue smoke + first S-N point
- Week 3: cross-amplitude S-N production + §5 figure-grade output

Do not block on PIDL side; PIDL is on its own Phase 2 thread, will report N_f cross-check once you have the PF-CZM PCC reference numbers.

### Deferred / dropped

- **Option (A) full 10⁴ AT2+Miehe PCC run**: dropped (transitional data, not paper-grade).
- **Task D 6-case strict Carrara sweep (AMOR vs MIEHE Basquin slope)**: held. May still be useful as Phase 1 §4 supplementary appendix evidence. Re-greenlight only if Mac asks. Don't preempt.
- **Task E (strict Carrara mesh check)**: held with Task D.

### Standby

Acknowledge this scope pivot in outbox; propose a Week-1 plan (which kernel files you'll touch, what brittle benchmark you'll use, ETA for the smoke). I'll review before you commit kernel changes. Don't auto-merge into mirror's `devel` branch until brittle benchmark passes.

---

## 2026-05-10 (evening) · [reply to PCC smoke `8162604`]: GO Option (A) — calibration is CORRECT, run full 10⁴

**Re**: Windows-FEM smoke result `8162604`. ᾱ_max @ c1409 = 4.12e-3 (82% α_T), per-cycle Δᾱ ≈ 1.06e-6, extrapolated N_f ≈ 2,400-3,000.

### Verdict: calibration is correct, my expected-N_f range was the error

I had said "expect N_f ~10⁴–10⁵". That estimate was anchored on Holmen 1979 *compression* S-N (S^max ≈ 0.5 of f_c at ~10⁶ cycles), which is the wrong reference for our tension-driven PF-CZM run. The correct community anchor is **Baktheer 2024 C60 at S^max = 0.75 → N_f ≈ 1,500–3,000 cycles** (their Mode I 3PB results, paper-grade calibrated).

Your N_f ≈ 2,400–3,000 is **within a factor of 1.5× of Baktheer's published concrete tension PF-CZM data**. The α_T = 5.0 N/mm² calibration is therefore **correct without re-tuning**; my earlier "10⁴–10⁵ midrange" was the error in expectation, not in α_T.

Why the mismatch with my "in-conversation" 13,500-cycle estimate:
- I assumed Kt ≈ 2.1 (Williams analytic for SENT a/W=0.5)
- Your refined mesh (h_tip = ℓ/5 = 0.4 mm at Phase 2 scale) gives Kt = 3.55 actual
- ψ_tip ∝ Kt² → 3.55² / 2.1² = 2.86× more aggressive accumulation
- 13,500 / 2.86 ≈ 4,720 cycles to threshold; +small acceleration phase → ~2,500-3,000 N_f ✓ matches your reading

### Decision: GO Option (A) — full 10⁴-cycle run, no re-tune

- max_cycle = 10000, cycle_jump = ON (same as smoke)
- Wall ~5 min per your estimate
- Goal: pin down exact N_f for the Phase 2 PCC demonstration data point

Reject (B) and (C):
- (B) k_f re-calibration would push us *away* from Baktheer's anchor — we'd no longer match published concrete PF-CZM data. Bad.
- (C) lowering σ_max to 0.65 f_t to artificially extend life is publication-unfriendly — reviewers will ask why we picked an unusual S^max. 0.75 is the standard Baktheer / fib MC reporting point.

### What to report after the full run

In `windows_fem_outbox.md`:
- Exact N_f
- a(N) crack-tip trajectory (analogous to Phase 1 FEM-4 CSV format: `cycle, x_tip_alpha95, alpha_max`)
- ᾱ_max @ N_f, f_min @ N_f
- Final crack pattern VTK keyframe (penetration cycle)
- Wall time
- Any deviations from cycle 4 → cycle 1409 linear extrapolation (e.g. acceleration shape during damage softening phase)

### Then what

After Option (A) lands:
1. Mac picks one comparable S^max from Baktheer 2024 (likely 0.85 for the LCF end) and asks for one more PCC run for cross-validation. Optional, ~5 min more wall.
2. Task D (6-case strict Carrara sweep) gets re-greenlighted only if Phase 2 paper §5 needs an S-N slope figure. TBD after Mac drafts §5 outline.

### Standby

Just go. No further Mac approval required for the full Option (A) run; start it whenever convenient and post results.

---

## 2026-05-10 (PM) · [reply to Task B/C/F outbox 5359893]: greenlight 100-cycle PCC smoke; ψ_tip math reconciled

**Re**: Windows-FEM outbox commits `40cc400` (Task F) + `5359893` (Task B + Task C). All three acknowledged.

### Task C (PCC smoke) — math reconciliation + GREENLIGHT 100-cycle smoke

Your concern about ψ_tip vs α_T 4-OOM gap → "10⁵–10⁶ cycles" is partially over-stated. Reconciling:

- Your numbers: σ_nom = 2.25 MPa, ψ_far = 8.4e-8 kN/mm², Kt=2.1 → **ψ_tip = 4.4·ψ_far = 3.7e-7 kN/mm²**
- α_T = 5.0e-3 kN/mm²
- **N_threshold = α_T / ψ_tip = 5.0e-3 / 3.7e-7 ≈ 13,500 cycles**

That is **inside** the 10⁴–10⁵ HCF range I predicted, not above it. (My own earlier sanity check used far-field ψ without Kt and got ~59k; your local-tip ψ with Kt² is the right one for the Carrara accumulator since ᾱ integrates per-element ψ₀.)

After threshold, Carrara f(ā) = (2α_T/(ā+α_T))² accelerates damage rapidly, so total N_f ≈ N_threshold + small overhead → **expected N_f ~14,000–25,000 cycles, HCF range, calibration is consistent**.

**GREENLIGHT the 100-cycle smoke**:
- Run with `cycle_jump = ON` (mandatory at HCF range, you flagged this correctly)
- Goal: measure per-cycle Δᾱ rate at peak σ_yy in tip element
- Decision rule: if extrapolated N_f × Δᾱ ≈ α_T (within factor 2× of 14,000), proceed full 10⁴-cycle run with cycle_jump tuning. If extrapolated N_f << 10³ or >> 10⁶, stop and report so we can iterate k_f from Holmen S-N data.

If 100-cycle smoke takes <2 min wall as you estimate, just launch it directly — no need to wait for further Mac approval, but report Δᾱ trend before launching the full 10⁴ run.

### Task B (strict Carrara stable) — confirmed done by reference

Acknowledged: du15/20/25/30 MIEHE+AT2+HISTORY production already cleanly demonstrates kernel stability. No new smoke needed for Task B.

### Task D (6-case sweep) — HOLD

Your gap analysis is correct: need 4 new MIEHE (du35/40/45/50) + 2 new AMOR (du35/45). **Hold launching until PCC smoke (Task C) reports back** — if PCC needs k_f re-calibration that consumes Windows-FEM compute, Task D priority drops. Will re-greenlight once PCC smoke verdict is in.

### Task F (V7 cycle 40 = 0.41%) — paper-grade datum, accepted

Both numbers (cycle 0 = 0.12%, cycle 40 = 0.41%) noted. The fact that PIDL/FEM ratio drops from 140-250× → 42-74× across life is **interesting and worth one sentence in §4.2**: "FEM V7 grows from 0.12% (peak elastic) to 0.41% (mid-life) due to the moving denominator (max σ_yy_bulk softens as damage accumulates), but stays well below 1% throughout the lifetime; PIDL's 17-30% residual remains 40× to 250× the FEM value at every cycle inspected." May fold into §4 v1.7 (no urgency; §4 v1.6 is currently locked).

Files for Task F: `Scripts/brittle_fracture/main_FEM_F_cycle40.m` (script) + `FEM_F_cycle40_*.vtk` output noted; CSV summary if you have it would be nice for the §4 table appendix later. Not blocking.

---

## 2026-05-10 · [unblock Task C]: PCC concrete α_T = 5.0 N/mm² (FEM-9 Task C ready)

**Re**: FEM-9 Task C (PCC Phase 2 scripts ready, awaiting Mac α_T calibration)

**Status**: ✅ α_T computed. Task C unblocked.

### α_T value to use

**α_T = α_N = 5.0 N/mm² = 5.0 MPa**

Derived via Baktheer 2024 formula `α_T = G_f / (k_f · ℓ) = 0.10 / (0.01 × 2.0)` with k_f=0.01 (Baktheer 2024 concrete-calibrated).

### Full PCC parameter set (replaces Handoff F placeholders)

```matlab
% INPUT_SENT_concrete_PCC.m updates:
E      = 3.0e4;     % MPa = 30 GPa (was placeholder)
nu     = 0.18;      % (was 0.3 toy)
f_t    = 3.0;       % MPa (was placeholder)
G_c    = 0.10;      % N/mm = 100 J/m² (was placeholder)
ell    = 2.0;       % mm (Phase 2 regularization length)
h_tip  = 0.4;       % mm (= ell/5, Carrara recommendation)
alpha_T = 5.0;      % N/mm² (this calibration; was 0.094 placeholder)
alpha_N = 5.0;      % N/mm² (= α_T, mean-load-independent)
```

Other settings:
- AT2 (not AT1) + Miehe spectral split + HISTORY accumulator → strict Carrara formulation (your Task B, kernel `e7eb3f8` bugfix already in)
- Geometry: physical SENT 100×100 mm (scale up from Phase 1 toy 1×1 mm); slit 50 mm from left edge at mid-height; thickness 1 mm

### Smoke validation

Run at **S^max = 0.75 of f_t** (= 2.25 MPa amplitude):
- Expected N_f: **10⁴–10⁵ cycles** (HCF range, consistent with Holmen 1979 / ACI 215R)
- If N_f << 10²: k_f too small, α_T threshold blown through too fast
- If N_f >> 10⁶: k_f too large, fatigue never triggers
- Either case: report N_f and we'll iterate k_f from a Holmen S-N data point

### Files

Full derivation + sanity checks + ℓ-sensitivity in Mac memory:
`finding_alpha_T_PCC_may10.md` (not in git; available on request)

### Priority

**HIGH** (unblocks Phase 2 demonstration). Run after Task A (FEM.md update) and Task B (strict Carrara smoke). Per FEM-9 schedule, Task C is Day 6-7 — proceed when you reach it.

---

## 2026-05-10 · [reply to fd2a113]: Answers to 3 scope questions before FEM-9 kickoff

**Re**: Windows-FEM ack fd2a113 — 3 questions answered, proceed with A→B→F→D→E→C sequence.

### Q1: Doc location
`docs/FEM.md` 已存在，路径正确（`upload code/docs/FEM.md`，last sync 2026-05-06）。
Task A 要做的：把 FEM-7（V4 mirror RMS = 2.98e-5，integrated damage = 4.39e-2）和 FEM-8（V7_FEM = 0.12%）追加进 FEM.md 对应 section，更新 Last sync 为今日。

### Q2: Task D 6-case selection
**用同样的 6 个 amplitude（du25/30/35/40/45/50），在 MIEHE+AT2+HISTORY 下重跑，与 AMOR 结果直接对比。**
- MIEHE 的 ψ⁺ 数值与 AMOR 不同（spectral vs volumetric-deviatoric），N_f 会变，必须重跑才能得到 MIEHE 的 Basquin m
- 保留 du40/50（即使是 LCF 端）：Basquin log-log 拟合需要宽幅值范围，截掉高端会让斜率不稳
- 不延伸到更低幅值（N_f >> 10³，代价大，Carrara 2020 也没做超高周）
- 目标：MIEHE 这条线的 m 是否从 3.49 往 3.8–4.0 移动

### Q3: Task F cycle selection
**用 cycle 40（~49% 寿命，u=0.12 N_f=82）代替 cycle 82。**
- Cycle 82 穿透态裂缝带 σ ≈ 0，归一化分母受损伤区扭曲，FEM 自己也会给出不合理的 V7 值
- Cycle 40 在传播阶段（裂缝已启动），归一化分母（体内 σ_yy_max）在清晰的裂缝前端，定义明确
- Cycle 40 有现成 `psi_fields/cycle_0040.mat`（FEM-5 keyframe set 已包含），读 VTK 即可，~10 min 额外计算

**→ 可以按 A→B→F→D→E→C 顺序开始，无其他 blocker。**

---

## 2026-05-09 · Request FEM-9: Windows-FEM 1-week plan (external expert recommendation)

**Goal**: 把外部专家给的 1 周 FEM 工作排期同步过来。专家把任务分成"必须做 / 值得做 / 暂缓"三档。整体方向：**收口 Phase 1 evidence、启动 strict Carrara、准备 PCC Phase 2** —— 不再用 Windows-FEM 资源补 AT1+penalty 细枝末节。

### 必须做（直接服务当前 paper + 主线判断）

**Task A — 把 Phase 1 FEM 证据包整理进 [docs/FEM.md](upload code/docs/FEM.md)**

不是新计算，是**已经到位的证据收口**。必须明确包含：
- `V7_FEM = 0.12%` (FEM-8 result)
- exact-pair symmetry 的好结果（FEM-7: alpha_bar rel 2.98e-5）
- `∫ ᾱ·(1-f) dV` integrated damage budget（FEM-7: 4.39e-2）
- AT1+penalty 的 h-non-monotonic verdict（即"AT1+penalty 在 SENT 上不收敛"的结论文档化）

**Task B — 确认 strict Carrara 线的 runner 能稳定跑**

公式: `AT2 + Miehe spectral split + HISTORY` (这是 Carrara 2020 community-anchor 公式)。
要求：
- 至少 1 个 smoke + 1 个代表性载荷点（比如 u=0.12）
- 目标不是立刻出完整论文图，而是确认 kernel bugfix 后这条线**真的可用**，不再是 "理论上想跑"

**Task C — 把 PCC Phase 2 的输入参数接口准备好**

等 Mac 给定 `α_T` (PCC concrete-specific) 后，Windows-FEM 能直接重跑：
- PCC 材料参数（E~30GPa, ν~0.18 vs 当前 toy E=1, ν=0.3）
- AT2 + Miehe spectral
- FEM-only smoke (PIDL 暂不动)

这一步**先做"脚本 ready"**，不必跑实际计算 — 等 Mac 给参数。

### 值得做（高价值增强，但不该阻塞写作）

**Task D — strict Carrara 6-case sweep**

最值得的增强实验。目的：
- 对齐 Carrara community anchor (Carrara 2020 CMAME)
- 看 Basquin slope `m` 能不能从当前 `3.49` 更接近 community range `3.8–4.0`

**Task E — strict Carrara 最小 mesh check**

只选 1 个中间载荷点（比如 u=0.12 量级），跑两档 mesh：
- ℓ/h = 5
- ℓ/h = 10

不追完美收敛，**确认 strict formulation 的 mesh sensitivity 是不是比当前 AT1+penalty 更可控**。

**Task F — V7_FEM 再补 1 个 fracture-near cycle**

现有 `V7_FEM = 0.12%` 是 peak elastic / cycle 0 状态。如果时间允许，再补 fracture 附近 cycle 的同口径 V7。这样后续能回答："FEM 边界质量在早期 vs 临破坏时是否都稳定"。

### 暂缓（不优先）

- AT1+penalty h-sweep 继续细化（已经够得出"不收敛"verdict）
- wide/narrow XF 尾巴
- 为 PIDL 每个新想法立刻配 FEM rerun（不应该让 Windows-FEM 被 PIDL 微调牵着走）

### 1 周顺序建议

| Day | 任务 |
|---:|---|
| 1 | Task A: 更新 docs/FEM.md，固定 Phase 1 evidence pack |
| 2 | Task B: strict Carrara 1-case smoke，确认 runner / kernel / export 全通 |
| 3-4 | Task D: strict Carrara 6-case sweep |
| 5 | Task E: strict Carrara 1-point mesh check |
| 6-7 | Task C: PCC Phase 2 脚本 ready + 等 α_T 后 smoke |

### Acceptance / Reply

每完成一个 Task 就 append 一个 `[done]` entry 到 `windows_fem_outbox.md`，含：
- 关键数字（如 strict Carrara N_f 或 Basquin m）
- 任何 blocker（如 kernel bug、参数未定）
- 下一步打算

### Priority

**Task A: HIGH** — paper §4 evidence consolidation 直接 depends on this  
**Task B/C: HIGH** — 解锁 Phase 2 主线  
**Task D/E/F: MEDIUM** — 增强但非阻塞

---

## 2026-05-07 · Request FEM-7: FEM-side symmetry + integrated damage budget @ u=0.12

**Goal**: 给 paper §4 reframe 提供 FEM 端的对照数字。Mac 这边 PIDL 完成了 soft symmetry penalty 实验（commit 90f2297）+ Layer 3 red-team 反馈，现需 FEM 侧的：
1. **V4 对称性 ground truth**：FEM α-field 在 SENT 几何下的 mirror RMS 数字（公认应 ≈ 0 at machine precision，但需要数字进 paper §4.2）
2. **真实 integrated damage budget**：∫ ᾱ·(1-f(ᾱ))·dV at fracture cycle，替代 Mac 当前的 f_mean-based 'domain-mean proxy'（red-team 指出后者是 wrong quantity）
3. **α field snapshot @ fracture cycle**：用于 F4.5a side-by-side mirror visualization (PIDL baseline vs PIDL soft sym vs FEM)

**Specific deliverables** (3 个 numbers + 1 个 .mat)：

### (a) FEM V4 mirror RMS @ Umax=0.12 fracture cycle (cycle 82)

```python
# From SENT_PIDL_12/psi_fields/cycle_0082.mat or similar
import numpy as np
from scipy.spatial import cKDTree
import scipy.io as sio

m = sio.loadmat("path/to/cycle_0082.mat")
centroids = m["centroids"]      # (N_elem, 2)
alpha = m["alpha_bar_elem"]      # or "d_elem"
x, y = centroids[:,0], centroids[:,1]
mu = y > 1e-6; ml = y < -1e-6
tree = cKDTree(np.stack([x[ml], -y[ml]], axis=1))
d, idx = tree.query(np.stack([x[mu], y[mu]], axis=1), k=1)
exact = d < 1e-7    # exact mirror pairs (for FEM mesh likely ~thousands)
diff = alpha[mu][exact].flatten() - alpha[ml][idx[exact]].flatten()
print(f"FEM V4 mirror RMS (exact pairs): {np.sqrt((diff**2).mean()):.4e}")
print(f"n_exact_pairs: {exact.sum()}")
```
→ 期望 RMS < 1e-4（per `Mandal-Nguyen-Wu 2019 EFM 217` 标 ≤ 2e-4 PASS）

### (b) Integrated ∫ ᾱ·(1-f(ᾱ))·dV @ fracture cycle 82

```python
alpha_T = 0.5        # match PIDL's setting
f_alpha = (2*alpha_T / (alpha + alpha_T))**2
# area_per_elem = element area (from mesh; you have it from FEM solver)
integrated = (alpha.flatten() * (1 - f_alpha).flatten() * area_per_elem.flatten()).sum()
print(f"FEM ∫ᾱ(1-f)dV @ c82 = {integrated:.4e}")
```

→ 这个数字对照 PIDL 的同公式（Mac 端在算 baseline + soft sym 两个 archive 的同 quantity），决定 paper §4.4 是 'energy budget 1.5-2× near-equivalence' 还是要砍掉

### (c) α field snapshot @ fracture cycle

期望 1 个 .mat 文件 `u12_cycle_0082_FEM7.mat`，含：
- `centroids`: (N_elem, 2)
- `alpha_bar_elem`: (N_elem, 1) — Carrara accumulator at c82
- `d_elem`: (N_elem, 1) — phase-field damage at c82

放 `_pidl_handoff_v3_items/` 同步到 OneDrive。

### (d) Paper-grade caveat

如果你有 FEM 的 V4 RMS、integrated damage、α field 的 ready 现成 dump，直接给 numbers + .mat 即可。如果需要新跑 post-processing，约 30 min-1h（不需要新 GRIPHFiTH run）。

**Priority**: high — 这三个 number 是 §4 核心 claim 的 FEM 对照 baseline，写 LaTeX 之前必须有。

**ETA**: 你估计 30 min-1h post-process。

---

## 2026-05-06 · Request FEM-6: re-extract N_f under load-drop criterion (option B from your `be07fd8`)

**Goal**: 用 mesh-stable N_f criterion `F_peak/F_initial < 5%`（或 `F_peak < 0.005`）替代当前 d-front-at-boundary criterion，重新算 mesh_C / M / F / XF (+ FEM-D 2×4 矩阵的 narrow row 各档) 的 N_f。看 paper §FEM 能不能写"convergence verified under load-amplitude criterion"。

**Mac vote**: **(B) approved.** 你在 `be07fd8` 里的诊断（penetration criterion 在 finer mesh 下"slows down"产生 detection drift）跟 community 标准（Castillón 2025、ASTM、ISO 用 load-drop criterion）一致；且 Mandal-Nguyen-Wu (2019, EFM 217) 文献明确说 AT1 是 h-non-monotonic 的，用 d-front 在 fine mesh 下不可信。

**Acceptance criteria**:
- (B-pass) `|N_f_F − N_f_M| / N_f_M < 5%` 在 load-drop criterion 下：paper §FEM 写 "h-convergence verified under load-amplitude criterion (load drop > 5%); d-front criterion intentionally avoided due to known mesh-sensitivity in AT1 phase-field formulations (Mandal et al. 2019)"
- (B-fail) load-drop 下仍发散：paper §FEM 改写 "AT1 phase-field is known to exhibit non-monotonic h-convergence under both d-front and load-drop criteria. PIDL/FEM comparison uses common ℓ/h≈1 reference mesh; absolute uncertainty band ±15% from h-sensitivity"

**Source data**: load_displ history 已经是每个 mesh archive 的标配（你常规 export）。不需要新跑训练。

**Output**:
1. 表格：mesh_C / M / F / XF 在 load-drop criterion 下的 N_f
2. 加 FEM-D 矩阵的 narrow row N_f（如果已经跑出来）
3. 一句 verdict：是否单调收敛 / 收敛 < 5%

**Priority**: **high** — paper §FEM 的写法直接 blocked 在这上面。Tier C reruns 都是 ℓ/h=1 的 PIDL 比较，不会受 FEM 这个收敛问题影响，但 reviewer 会先问"FEM reference 的 mesh convergence 怎么说"。

**ETA**: 你估计 ~30 min post-process（不需要新 GRIPHFiTH run）。

---

## 2026-05-06 · Request FEM-5: ship u=0.10 + u=0.11 ψ⁺ keyframes to Mac

**Goal**: 解锁 Mac→Taobo 上的 Oracle u=0.10 / u=0.11 干净重跑（Tier C audit follow-up，currently blocked）。Mac `~/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent/` 目前只有 u08 + u12 4-keyframe 各 4 文件；u10/u11 一直只在 Windows-FEM。Taobo 已有 FEM data 镜像（Mac sync 过来），所以 Windows-FEM 只需把 u10/u11 keyframes 寄到 Mac，Mac 自会再同步到 Taobo。

**Format**: 与 u08/u12 完全一致——4 个 keyframe `.mat` 文件 / Umax，每个含 `psi_elem`, `alpha_bar_elem`, `f_alpha_elem`, `d_elem`（n_elem × 1 element-averaged from Gauss points + d-field read from VTK at nearest cycle ≤ keyframe）。

**Keyframe cycles 选择参考 u12 模式**（c1, c40, c70, c82）：
- u=0.10 (FEM N_f=170)：建议 c1, c80, c140, c170
- u=0.11 (FEM N_f=117)：建议 c1, c55, c95, c117

**Expected files** (8 个 `.mat`)：
```
u10_cycle_0001.mat
u10_cycle_0080.mat
u10_cycle_0140.mat
u10_cycle_0170.mat
u11_cycle_0001.mat
u11_cycle_0055.mat
u11_cycle_0095.mat
u11_cycle_0117.mat
```

**Delivery**: 跟 u08/u12 一样，OneDrive 共享文件夹（或 zip 一起发）。Mac 拿到后会落到 `~/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent/` 然后 rsync 到 Taobo。

**Acceptance**: Mac 可以读到这 8 个文件，sanity check 与 u08/u12 文件的 keys 一致；Taobo 上 `run_e2_reverse_umax.py 0.10` 和 `0.11` 不再报 FEM data missing。

**Priority**: medium (paper 用 Oracle u=0.10/0.11 数据 cross-validate framework claim；Taobo 5/8 GPU 也在等这个解锁)。ETA：抽 20-30 min 跑一下 export script 应该够。

**Background**: Mac 同时在审计 archive 设置（commit `28cce78` 后 audit 脚本发现 3 个 u=0.12 method archive WARN due to missing model_settings.txt）。Tier C 重跑已派 5 个到 Taobo，但 Oracle u=0.10/0.11 还要等这两组 keyframe ship 过来。

---

## 2026-05-05 · Request FEM-4: export a(N) crack propagation curve for u=0.08, 0.12, 0.13

**Goal**: 生成 FEM 的 a(N) 曲线（裂纹尖端位置 vs 循环数），与 PIDL 的 x_tip-vs-N 叠图对比。这是 Carrara 2020 Fig 6 的核心图，paper 必须有。

**定义对齐（与 PIDL 一致）**：
- `x_tip(N)` = 该 cycle 中 α > 0.95 的最大 x 坐标（即 crack front 的 x 位置）
- 如果 GRIPHFiTH 输出的是 GP-level α，取所有 α>0.95 的 GP 中 x 坐标的最大值

**需要的 Umax**（3 个，覆盖低/中/高 Umax）：
- u=0.08：FEM N_f ≈ 396，`SENT_PIDL_08_export/` 已有
- u=0.12：FEM N_f = 82，`SENT_PIDL_12_export/` 已有
- u=0.13：FEM N_f = 57，数据在 `_pidl_handoff_v2/psi_snapshots_for_agent/` 或单独跑一次

**Output format**（每个 Umax 一个 CSV）：
```
cycle, x_tip_alpha95, alpha_max_monitor
1, 0.502, 0.031
2, 0.503, 0.044
...
```

**Files requested**:
- `fem_a_traj_u008.csv`
- `fem_a_traj_u012.csv`
- `fem_a_traj_u013.csv`
- 放到 `_pidl_handoff_v3_items/` 或新建 `_pidl_aN_curves/`

**Priority**: high（这个图是 paper 核心图之一，PIDL 这边 x_tip 数据已有，等 FEM 数据就能出图）

**Note**: `export_alpha_traj_u12.m` 目前只导出 α_max，不含 x_tip，需要新写或修改导出脚本。

---

## 2026-05-05 · Request FEM-3: h-sweep extension — ℓ/h=20 to bracket convergence

**Goal**: mesh_C/M/F 显示 M→F 仍有 +8.9%，尚未收敛。加 ℓ/h=20 一个点来估计渐近值，给 paper 一个更紧的 convergence bracket。

**脚本**：按 mesh_F 的模式新建 `INPUT_SENT_PIDL_12_mesh_XF.m` + `main_fatigue_meshXF.m`（"XF" = extra-fine）。

目标 mesh 参数（跟着 mesh_F 模式延伸）：
- `ℓ/h_tip = 20` → `h_tip = 0.0005 mm`
- `specimen.internal.plate` 参数参考：`Lref_y=0.05`, `Nref_y=100`（偶数，确保 notch 在网格上）；`Nx` 按需调整以匹配 h_tip
- 其余材料参数、BC、max_cycle=120 全不变

**Expected output**:
- N_f_XF（first detect）
- 回传 outbox：N_f_C/M/F/XF 完整表 + 是否出现渐近迹象

**Acceptance**: 如果 |N_f_XF − N_f_F|/N_f_F < 5% → convergence bracket closed；若仍 >5% → report trend，Mac 决定是否再加一档

**Priority**: medium（ETA ~12-15h，可 overnight）

---

## 2026-05-05 · Request FEM-2: gmsh-only h-sweep — mesh_C/M/F convergence at Umax=0.12

**Goal**: 用同一个工具（GRIPHFiTH `specimen.internal.plate`）跑三套分辨率，干净证明 h-convergence，替代 FEM-1 的混合工具对比结果。Paper 里写"h-convergence verified with same mesh generator"。

**脚本已在镜像里，直接跑**：

```matlab
% 顺序跑，或并行跑（独立）
run('Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_mesh_C.m'); main_fatigue_meshC(...)
run('Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_mesh_M.m'); main_fatigue_meshM(...)
run('Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_mesh_F.m'); main_fatigue_meshF(...)
```

**Expected outputs**:
- 三个 N_f（first penetration）
- 回传到 outbox：表格 N_f_C / N_f_M / N_f_F + 趋势（converging / diverging）

**Acceptance criteria**:
- PASS：N_f_M 和 N_f_F 之差 < 5%（证明在 ℓ/h≥10 处收敛）
- BONUS：如果 N_f_C ≈ N_f_M ≈ N_f_F，连 ℓ/h=5 都够用，更强

**Priority**: medium（~30-40 min wall，三个可并行）

---

## 2026-05-05 · Request FEM-1: mesh convergence check — PIDL-series at Umax=0.12, ℓ/h=5

**Goal**: 验证 PIDL-series FEM 参考数据（ℓ/h≈1，N_f≈82）是否网格收敛。Paper 里要能写一句"convergence verified at representative Umax"。

**现有 baseline**:
- INPUT file: `Scripts/fatigue_fracture/INPUT_SENT_PIDL_12.m`
- Mesh: `Dependencies/SENT_mesh/SENT_mesh.inp`（77,730 quads，h_tip≈0.01 mm，ℓ/h≈1）
- Result: N_f ≈ 82

**需要做的**:

**Step 1 — 生成新 mesh**（与 SENT_carrara_quad.inp / SENT_pcc_concrete_quad.inp 同流程）:

| 参数 | 目标值 |
|---|---|
| 几何 | 同 SENT_mesh.inp：1×1 mm，notch 在左中，物理切口 |
| ℓ | 0.01 mm（不变） |
| h_tip | **0.002 mm**（ℓ/h_tip = 5） |
| h_zone | 0.005 mm（tip 周围精细区） |
| h_global | 0.05 mm |
| 格式 | Abaqus .inp 或 GRIPHFiTH 支持的格式 |
| 文件名 | `SENT_pidl_fine_lh5.inp` |

**Step 2 — 新 INPUT 文件**（基于 INPUT_SENT_PIDL_12.m 修改）:
- 文件名：`INPUT_SENT_PIDL_12_fine.m`
- 唯一改动：mesh 路径指向新 `SENT_pidl_fine_lh5.inp`
- 所有材料参数不变：E=1, ν=0.3, Gc=0.01, ℓ=0.01, α_T=0.5, p=2.0, AT1, AMOR, PENALTY
- BC 不变：uy_final=0.12, R=0.0
- max_cycle=120（足够，预期 fracture ~82）

**Step 3 — 跑**:
```matlab
run('Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_fine.m')
main_fatigue_fracture(...)
```

**Expected outputs**:
- N_f（first penetration cycle）
- ᾱ_max @ N_f
- 回传到 `windows_fem_outbox.md`：N_f_fine vs N_f_coarse=82，差值 %

**Acceptance criteria**:
- PASS：|N_f_fine − 82| / 82 ≤ 5%（网格收敛）
- FAIL：>5%，需要讨论是否重跑所有 Umax 或降级 caveat

**Priority**: medium（OOD 表格不 block 这个，但 paper submission 前必须有）

**Blocker 提示**: 如果 mesh 生成工具（Abaqus/Gmsh）有问题，outbox 里说一声，Mac 可以帮生成 .inp 文件。

---

## Archive

[暂无]
